"""Tests for scripts/validate_project.py."""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

from src.model import ShapeShiftProject

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
        """load_project should pass through the file, env file, and env prefix."""
        validate_project = load_validate_project_module()
        expected_project = MagicMock(spec=ShapeShiftProject)
        from_file = MagicMock(return_value=expected_project)

        monkeypatch.setattr(validate_project.ShapeShiftProject, "from_file", from_file)

        result = validate_project.load_project("/tmp/project.yml", "/tmp/.env")

        assert result is expected_project
        from_file.assert_called_once_with(
            filename="/tmp/project.yml",
            env_file="/tmp/.env",
            env_prefix="SHAPE_SHIFTER",
        )


class TestExecute:
    """Tests for execute()."""

    def test_execute_returns_2_when_project_file_is_missing(self, tmp_path: Path):
        """execute should stop early when the project file does not exist."""
        validate_project = load_validate_project_module()
        validate_project.setup_logging = MagicMock()
        validate_project.click.echo = MagicMock()

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

    def test_execute_returns_1_when_project_load_fails(self, tmp_path: Path):
        """execute should report project-load failures to stderr and return 1."""
        validate_project = load_validate_project_module()
        validate_project.setup_logging = MagicMock()
        validate_project.click.echo = MagicMock()
        validate_project.logger.exception = MagicMock()
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
