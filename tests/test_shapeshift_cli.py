"""Tests for full-run CLI output expectation reporting."""

from pathlib import Path
from typing import Literal
from unittest.mock import AsyncMock

import pytest
from click.testing import CliRunner

from src.output_expectations import OutputExpectationEvaluation, OutputExpectationResult
from src.shapeshift import main

FAILURE = "Measured value 0 does not satisfy the expected value 2."


def expect_result(
    *,
    name: str,
    entity: str = "site",
    metric: str = "row_count",
    group_value: object | None = None,
    measured_value: int | None = 1,
    expected_limit: dict[str, int] | None = None,
    status: Literal["pass", "fail"] = "pass",
    failure_reason: str | None = None,
) -> OutputExpectationResult:
    """Build one output expectation result for CLI tests."""
    return OutputExpectationResult(
        name=name,
        entity=entity,
        metric=metric,
        group_value=group_value,
        measured_value=measured_value,
        expected_limit=expected_limit or {"equals": 1},
        status=status,
        failure_reason=failure_reason,
    )


@pytest.fixture(name="project_file")
def _project_file(tmp_path: Path) -> Path:
    """Create a project path that satisfies the CLI existence check."""
    project = tmp_path / "shapeshifter.yml"
    project.write_text("metadata:\n  name: cli-test\nentities: {}\n", encoding="utf-8")
    return project


@pytest.fixture(name="cli_runner")
def _cli_runner() -> CliRunner:
    """Provide a Click runner."""
    return CliRunner()


def _quiet_logging(**_: object) -> None:
    """Disable log setup during CLI tests."""


def invoke_cli(
    runner: CliRunner,
    project_file: Path,
    monkeypatch: pytest.MonkeyPatch,
    evaluation: OutputExpectationEvaluation | None,
    *extra_args: str,
):
    """Invoke the CLI with a mocked workflow and quiet logging."""
    monkeypatch.setattr("src.shapeshift.setup_logging", _quiet_logging)
    run = AsyncMock(return_value=evaluation)
    monkeypatch.setattr("src.shapeshift.workflow", run)
    result = runner.invoke(main, ["out", "--project", str(project_file), "--mode", "csv", *extra_args])
    return result, run


def test_reports_all_results_and_fails_on_mismatch(cli_runner: CliRunner, project_file: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Two failures and a passing grouped check print in order before a nonzero exit."""
    evaluation = OutputExpectationEvaluation(
        results=[
            expect_result(name="parent-count", measured_value=0, status="fail", failure_reason=FAILURE),
            expect_result(name="child-count", entity="child", measured_value=0, status="fail", failure_reason=FAILURE),
            expect_result(
                name="children-by-name",
                entity="child",
                metric="grouped_row_count",
                group_value="first",
                measured_value=1,
            ),
        ],
        passed=False,
    )

    result, run = invoke_cli(cli_runner, project_file, monkeypatch, evaluation)

    assert result.exit_code != 0
    assert "parent-count" in result.output
    assert "child-count" in result.output
    assert "children-by-name" in result.output
    assert result.output.index("parent-count") < result.output.index("child-count") < result.output.index("children-by-name")
    assert FAILURE in result.output
    assert "Successfully written" not in result.output
    run.assert_awaited_once()


def test_reports_results_and_succeeds_when_all_pass(cli_runner: CliRunner, project_file: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Passing checks print and the normal success message remains."""
    evaluation = OutputExpectationEvaluation(
        results=[
            expect_result(name="site-count", measured_value=2, expected_limit={"min": 1, "max": 3}),
            expect_result(
                name="sites-by-project",
                metric="grouped_row_count",
                group_value="north",
                measured_value=2,
            ),
        ],
        passed=True,
    )

    result, run = invoke_cli(cli_runner, project_file, monkeypatch, evaluation)

    assert result.exit_code == 0
    assert "site-count" in result.output
    assert "sites-by-project" in result.output
    assert "north" in result.output
    assert "Successfully written normalized workbook" in result.output
    run.assert_awaited_once()


def test_renders_explicit_null_group(cli_runner: CliRunner, project_file: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """An explicitly configured null group prints as a JSON null value."""
    evaluation = OutputExpectationEvaluation(
        results=[
            expect_result(
                name="sites-without-project",
                metric="grouped_row_count",
                group_value=None,
                measured_value=0,
            )
        ],
        passed=True,
    )

    result, _ = invoke_cli(cli_runner, project_file, monkeypatch, evaluation)

    assert result.exit_code == 0
    assert "sites-without-project" in result.output
    assert "group=null" in result.output


def test_no_expectations_retains_success_output(cli_runner: CliRunner, project_file: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A run without configured expectations keeps its existing success behavior."""
    result, run = invoke_cli(cli_runner, project_file, monkeypatch, None)

    assert result.exit_code == 0
    assert "Output expectation results" not in result.output
    assert "Successfully written normalized workbook" in result.output
    run.assert_awaited_once()


def test_validate_then_exit_does_not_run_output_checks(cli_runner: CliRunner, project_file: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Validation-only mode does not invoke the full workflow."""
    monkeypatch.setattr("src.shapeshift.setup_logging", _quiet_logging)
    monkeypatch.setattr("src.shapeshift.validate_project", lambda _: True)
    run = AsyncMock()
    monkeypatch.setattr("src.shapeshift.workflow", run)

    result = cli_runner.invoke(main, ["out", "--project", str(project_file), "--validate-then-exit"])

    assert result.exit_code == 0
    run.assert_not_awaited()
