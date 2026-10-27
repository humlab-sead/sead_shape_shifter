"""Tests for scripts/validate_project.py."""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Literal
from unittest.mock import AsyncMock, MagicMock

import pandas as pd
import pytest

from backend.app.models.validation import ValidationError
from src.model import ShapeShiftProject
from src.specifications.constraints import ValidationIssue as LinkerValidationIssue
from src.table_store import TableStore

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "validate_project.py"


def load_validate_project_module() -> ModuleType:
    """Load the validate_project script as a module for unit testing."""
    module_name = "tests.validate_project_script_module"
    spec = importlib.util.spec_from_file_location(module_name, MODULE_PATH)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    sys.modules.pop(module_name, None)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class TestLoadProject:
    """Tests for load_project()."""

    def test_load_project_delegates_to_shapeshift_project_from_file(self, monkeypatch):
        """load_project should use the repository target models directory as a fallback."""
        validate_project = load_validate_project_module()
        expected_project = MagicMock(spec=ShapeShiftProject)
        from_file = MagicMock(return_value=expected_project)

        monkeypatch.delenv("GLOBAL_TARGET_MODEL_DIR", raising=False)
        monkeypatch.setattr(validate_project.ShapeShiftProject, "from_file", from_file)

        result = validate_project.load_project("/tmp/project.yml", "/tmp/.env")

        assert result is expected_project
        assert validate_project.os.environ["GLOBAL_TARGET_MODEL_DIR"] == str(validate_project.PROJECT_ROOT / "resources" / "target_models")
        from_file.assert_called_once_with(
            filename="/tmp/project.yml",
            env_file="/tmp/.env",
            env_prefix="SHAPE_SHIFTER",
        )

    def test_load_project_preserves_configured_target_model_dir(self, tmp_path: Path, monkeypatch):
        """load_project should not replace a target-model directory set in the environment."""
        validate_project = load_validate_project_module()
        configured_dir = str(tmp_path / "configured-models")
        monkeypatch.setenv("GLOBAL_TARGET_MODEL_DIR", configured_dir)
        monkeypatch.setattr(validate_project.ShapeShiftProject, "from_file", MagicMock())

        validate_project.load_project("/tmp/project.yml", str(tmp_path / ".env"))

        assert validate_project.os.environ["GLOBAL_TARGET_MODEL_DIR"] == configured_dir

    def test_load_project_uses_target_model_dir_from_env_file(self, tmp_path: Path, monkeypatch):
        """load_project should load a configured target-model directory before applying the fallback."""
        validate_project = load_validate_project_module()
        configured_dir = str(tmp_path / "configured-models")
        env_file = tmp_path / ".env"
        env_file.write_text(f"GLOBAL_TARGET_MODEL_DIR={configured_dir}\n", encoding="utf-8")
        monkeypatch.delenv("GLOBAL_TARGET_MODEL_DIR", raising=False)
        monkeypatch.setattr(validate_project.ShapeShiftProject, "from_file", MagicMock())

        validate_project.load_project("/tmp/project.yml", str(env_file))

        assert validate_project.os.environ["GLOBAL_TARGET_MODEL_DIR"] == configured_dir

    def test_load_project_does_not_set_default_when_target_model_dir_is_missing(self, tmp_path: Path, monkeypatch):
        """load_project should leave the variable unset if the repository target-model directory is missing."""
        validate_project = load_validate_project_module()
        monkeypatch.setattr(validate_project, "PROJECT_ROOT", tmp_path)
        monkeypatch.delenv("GLOBAL_TARGET_MODEL_DIR", raising=False)
        monkeypatch.setattr(validate_project.ShapeShiftProject, "from_file", MagicMock())

        validate_project.load_project("/tmp/project.yml", str(tmp_path / ".env"))

        assert "GLOBAL_TARGET_MODEL_DIR" not in validate_project.os.environ


class TestConformanceValidationExecutor:
    """Tests for conformance issue severity handling."""

    @pytest.mark.parametrize(
        ("severity", "expected_passed"),
        [
            ("info", True),
            ("warning", True),
            ("error", False),
        ],
    )
    def test_execute_preserves_severity_and_fails_only_for_errors(
        self, severity: Literal["info", "warning", "error"], expected_passed: bool, monkeypatch
    ):
        """Conformance issues retain their severity, and only errors fail the workflow."""
        validate_project = load_validate_project_module()
        project = SimpleNamespace(metadata=SimpleNamespace(target_model={"entities": {}}))
        validation_issue = ValidationError(
            severity=severity,
            entity="dataset",
            field="data_type_id",
            message="Target ID check is pending.",
            code="DIRECT_FK_TARGET_CHECK_PENDING",
        )
        target_model_validator = MagicMock()
        target_model_validator.validate.return_value = [validation_issue]
        monkeypatch.setattr(validate_project, "TargetModelValidator", MagicMock(return_value=target_model_validator))

        result = validate_project.ConformanceValidationExecutor()._execute(project, ignores=set())

        assert result.passed is expected_passed
        assert [issue.severity for issue in result.issues] == [severity]


class TestDataValidationExecutor:
    """Tests for structured findings produced during normalization."""

    def test_execute_includes_normalizer_linker_issues_in_csv_results(self, monkeypatch, capsys):
        """The CLI data workflow should return structured linker findings from its normalizer."""
        validate_project = load_validate_project_module()
        project = ShapeShiftProject(
            cfg={
                "metadata": {"name": "cli_test"},
                "entities": {
                    "orders": {
                        "type": "fixed",
                        "public_id": "order_id",
                        "keys": ["value"],
                        "columns": ["value"],
                        "values": [[1]],
                    }
                },
            }
        )
        linker_issue = LinkerValidationIssue(
            issue_type="row_count_mismatch",
            severity="warning",
            local_entity="orders",
            remote_entity="customers",
            message="orders -> customers: join changed the row count",
            metadata={"row_count_before": 4, "row_count_after": 2},
        )
        normalizer = SimpleNamespace(
            table_store=TableStore({"orders": pd.DataFrame({"value": [1]})}),
            unresolved_extra_columns={},
            linker=SimpleNamespace(validators=[SimpleNamespace(issues=[linker_issue])]),
            normalize=AsyncMock(),
        )
        monkeypatch.setattr(validate_project, "ShapeShifter", lambda _project: normalizer)

        result = validate_project.DataValidationExecutor()._execute(project, ignores=set())

        assert result.passed is True
        assert [issue.code for issue in result.issues] == ["ROW_COUNT_MISMATCH"]

        validate_project.print_workflow_results({"data": result})

        assert (
            "data;warning;orders;None;None;ROW_COUNT_MISMATCH;" "orders -> customers: join changed the row count"
        ) in capsys.readouterr().out


class TestExecute:
    """Tests for execute()."""

    def test_execute_returns_2_when_project_file_is_missing(self, tmp_path: Path, monkeypatch):
        """execute should stop early when the project file does not exist."""
        validate_project = load_validate_project_module()
        validate_project.setup_logging = MagicMock()
        # validate_project.click is the shared click module, so restore it after the test.
        monkeypatch.setattr(validate_project.click, "echo", MagicMock())

        missing_file = tmp_path / "missing.yml"

        result = validate_project.execute(
            str(missing_file),
            workflow="all",
            env_file=tmp_path / ".env",
            verbose=False,
            log_level="INFO",
            log_file=None,
            ignore="",
        )

        assert result == 2
        validate_project.click.echo.assert_called_once_with(f"Project file not found: {missing_file.resolve()}", err=True)

    def test_execute_returns_1_when_project_load_fails(self, tmp_path: Path, monkeypatch):
        """execute should report project-load failures to stderr and return 1."""
        validate_project = load_validate_project_module()
        validate_project.setup_logging = MagicMock()
        # validate_project.click and .logger are the shared click and loguru modules.
        monkeypatch.setattr(validate_project.click, "echo", MagicMock())
        monkeypatch.setattr(validate_project.logger, "exception", MagicMock())
        validate_project.load_project = MagicMock(side_effect=ValueError("broken project"))

        project_file = tmp_path / "project.yml"
        project_file.write_text("name: broken\n", encoding="utf-8")

        result = validate_project.execute(
            str(project_file),
            workflow="all",
            env_file=tmp_path / ".env",
            verbose=False,
            log_level="INFO",
            log_file=None,
            ignore="",
        )

        assert result == 1
        validate_project.logger.exception.assert_called_once_with("Failed to load project file {}", project_file.resolve())
        validate_project.click.echo.assert_called_once_with("Failed to load project file: broken project", err=True)
