"""Tests for mandatory output expectation declaration checks during execution."""

from datetime import UTC, datetime
from typing import Any, Literal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from backend.app.authorization.models import Action, AuthorizedResource, Principal, ResourceRecord, ResourceType
from backend.app.models.execute import DispatcherMetadata, ExecuteRequest
from backend.app.models.project import Project, ProjectMetadata
from backend.app.services.execute_service import ExecuteService
from src.output_expectations import OutputExpectationEvaluation, OutputExpectationResult


class FakeProjectService:
    """Return one API project for execution tests."""

    def __init__(self, project: Project) -> None:
        self.project = project

    def load_project(self, project_name: str) -> Project:
        assert project_name == "pilot"
        return self.project


def api_project(*, output_expectations: list[dict] | None) -> Project:
    """Build a project that passes the existing structural checks."""
    options: dict[str, Any] = {"data_sources": {"db1": {"driver": "postgresql"}}}
    if output_expectations is not None:
        options["output_expectations"] = output_expectations or []
    return Project(
        metadata=ProjectMetadata(name="pilot", entity_count=1),
        entities={
            "site": {
                "type": "sql",
                "columns": ["site_key", "site_name"],
                "keys": ["site_key"],
                "data_source": "db1",
                "query": "SELECT 1",
            }
        },
        options=options,
    )


def authorized_project() -> AuthorizedResource:
    """Build an active project execution authorization."""
    principal = Principal("operator", "test", datetime.now(UTC))
    resource = ResourceRecord(uuid4(), ResourceType.PROJECT, "pilot", "active")
    return AuthorizedResource(principal, Action.EXECUTE, resource)


def request(*, run_validation: bool) -> ExecuteRequest:
    """Build one dispatcher request."""
    return ExecuteRequest(dispatcher_key="csv", target="site.csv", run_validation=run_validation)


def output_result(
    name: str,
    *,
    entity: str = "site",
    metric: str = "row_count",
    group_value: Any | None = None,
    measured_value: int | None = 1,
    expected_limit: dict[str, int] | None = None,
    status: Literal["pass", "fail"] = "pass",
    failure_reason: str | None = None,
) -> OutputExpectationResult:
    """Build one Core output expectation result for service tests."""
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


def configure_execution_mocks(monkeypatch: pytest.MonkeyPatch, service: ExecuteService, workflow: AsyncMock) -> list[str]:
    """Stub output-path and workflow side effects, recording target resolution."""
    resolved_targets: list[str] = []
    monkeypatch.setattr(
        service,
        "get_dispatchers",
        lambda: [DispatcherMetadata(key="csv", target_type="file", description="CSV", extension=".csv")],
    )
    monkeypatch.setattr(
        service,
        "resolve_output_target",
        lambda project_name, target, target_type: resolved_targets.append(target) or "/managed/site.csv",
    )
    monkeypatch.setattr(service, "_add_timestamp_to_file_target", lambda target, target_type: target)
    monkeypatch.setattr(service, "_output_identifier", lambda project_name, target, target_type: target)
    monkeypatch.setattr(service, "_build_download_path", lambda project_name, target, target_type: None)
    monkeypatch.setattr("backend.app.services.execute_service.workflow", workflow)
    return resolved_targets


@pytest.mark.asyncio
@pytest.mark.parametrize(("run_validation", "expected_validation"), [(False, None), (True, False)])
async def test_invalid_expectations_fail_before_output_target_or_workflow(
    monkeypatch: pytest.MonkeyPatch,
    run_validation: bool,
    expected_validation: bool | None,
) -> None:
    """Declaration errors stop output setup whether optional validation is enabled or not."""
    service = ExecuteService(
        project_service=FakeProjectService(  # type: ignore
            api_project(output_expectations=[{"name": "missing-site", "entity": "missing", "metric": "row_count", "equals": 0}])
        )
    )
    workflow = AsyncMock()
    resolved_targets = configure_execution_mocks(monkeypatch, service, workflow)

    result = await service.execute_workflow(authorized_project(), request(run_validation=run_validation))

    assert result.success is False
    assert result.validation_passed is expected_validation
    assert "options.output_expectations" in (result.error_details or "")
    assert not resolved_targets
    workflow.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("expectations", "run_validation", "expected_validation"),
    [
        (None, False, None),
        (None, True, True),
        ([{"name": "site-count", "entity": "site", "metric": "row_count", "equals": 1}], False, None),
        ([{"name": "site-count", "entity": "site", "metric": "row_count", "equals": 1}], True, True),
    ],
)
async def test_valid_or_absent_expectations_preserve_execution_validation_behavior(
    monkeypatch: pytest.MonkeyPatch,
    expectations: list[dict] | None,
    run_validation: bool,
    expected_validation: bool | None,
) -> None:
    """Valid declarations do not alter normal execution or optional validation status."""
    service = ExecuteService(project_service=FakeProjectService(api_project(output_expectations=expectations)))  # type: ignore
    workflow = AsyncMock()
    workflow.return_value = None
    resolved_targets = configure_execution_mocks(monkeypatch, service, workflow)

    result = await service.execute_workflow(authorized_project(), request(run_validation=run_validation))

    assert result.success is True
    assert result.validation_passed is expected_validation
    assert result.output_expectation_results == []
    assert resolved_targets == ["site.csv"]
    workflow.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(("run_validation", "expected_validation"), [(False, None), (True, True)])
async def test_expectation_mismatch_returns_failed_execution_with_all_results(
    monkeypatch: pytest.MonkeyPatch,
    run_validation: bool,
    expected_validation: bool | None,
) -> None:
    """A failed check reports every result, no download path, and unchanged validation status."""
    service = ExecuteService(
        project_service=FakeProjectService(  # type: ignore
            api_project(output_expectations=[{"name": "site-count", "entity": "site", "metric": "row_count", "equals": 1}])
        )
    )
    workflow = AsyncMock()
    workflow.return_value = OutputExpectationEvaluation(
        results=[
            output_result(
                "site-count",
                measured_value=0,
                status="fail",
                failure_reason="Measured value 0 does not satisfy the expected value 1.",
            ),
            output_result("sites-by-project", metric="grouped_row_count", group_value="north", measured_value=0, status="fail"),
            output_result("sites-by-active", metric="grouped_row_count", group_value=True, measured_value=1),
            output_result("sites-by-rank", metric="grouped_row_count", group_value=3, measured_value=1),
            output_result("sites-without-project", metric="grouped_row_count", group_value=None, measured_value=1),
            output_result(
                "missing-site-count",
                entity="missing",
                measured_value=None,
                status="fail",
                failure_reason="Expected entity 'missing' is missing from completed output.",
            ),
        ],
        passed=False,
    )
    resolved_targets = configure_execution_mocks(monkeypatch, service, workflow)

    result = await service.execute_workflow(authorized_project(), request(run_validation=run_validation))

    assert result.success is False
    assert result.validation_passed is expected_validation
    assert result.target == ""
    assert result.download_path is None
    assert [item.name for item in result.output_expectation_results] == [
        "site-count",
        "sites-by-project",
        "sites-by-active",
        "sites-by-rank",
        "sites-without-project",
        "missing-site-count",
    ]
    assert [item.group_value for item in result.output_expectation_results] == [None, "north", True, 3, None, None]
    assert result.output_expectation_results[0].status == "fail"
    assert result.output_expectation_results[-1].measured_value is None
    assert result.output_expectation_results[-1].failure_reason is not None
    assert "Measured value 0" in (result.error_details or "")
    assert resolved_targets == ["site.csv"]
    workflow.assert_awaited_once()


@pytest.mark.asyncio
async def test_passing_expectations_return_results_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """A passing run still returns every result with its measurement and limit."""
    service = ExecuteService(
        project_service=FakeProjectService(  # type: ignore
            api_project(output_expectations=[{"name": "site-count", "entity": "site", "metric": "row_count", "min": 1, "max": 3}])
        )
    )
    workflow = AsyncMock()
    workflow.return_value = OutputExpectationEvaluation(
        results=[
            output_result("site-count", measured_value=2, expected_limit={"min": 1, "max": 3}),
            output_result("sites-by-project", metric="grouped_row_count", group_value="north", measured_value=2),
        ],
        passed=True,
    )
    configure_execution_mocks(monkeypatch, service, workflow)

    result = await service.execute_workflow(authorized_project(), request(run_validation=False))

    assert result.success is True
    assert result.validation_passed is None
    assert [item.status for item in result.output_expectation_results] == ["pass", "pass"]
    assert result.output_expectation_results[0].measured_value == 2
    assert result.output_expectation_results[0].expected_limit == {"min": 1, "max": 3}
    assert result.output_expectation_results[1].group_value == "north"
    workflow.assert_awaited_once()
