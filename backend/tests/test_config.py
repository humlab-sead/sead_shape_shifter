"""Tests for backend settings path resolution."""

from __future__ import annotations

from pathlib import Path

from backend.app.core.config import Settings


def test_relative_paths_resolve_against_repository_root(monkeypatch) -> None:
    """Relative config paths should not depend on the current working directory."""
    monkeypatch.chdir(Path("/tmp"))
    monkeypatch.setenv("SHAPE_SHIFTER_PROJECTS_DIR", "./data/projects")
    monkeypatch.setenv("SHAPE_SHIFTER_LOG_DIR", "./data/logs")
    monkeypatch.setenv("SHAPE_SHIFTER_GLOBAL_DATA_DIR", "./data/shared/shared-data")
    monkeypatch.setenv("SHAPE_SHIFTER_GLOBAL_DATA_SOURCE_DIR", "./data/shared/data-sources")
    monkeypatch.setenv("SHAPE_SHIFTER_GLOBAL_TARGET_MODEL_DIR", "./data/shared/target-models")

    settings = Settings()

    assert settings.PROJECTS_DIR == settings.APPLICATION_ROOT / "data/projects"
    assert settings.LOG_DIR == settings.APPLICATION_ROOT / "data/logs"
    assert settings.GLOBAL_DATA_DIR == settings.APPLICATION_ROOT / "data/shared/shared-data"
    assert settings.GLOBAL_DATA_SOURCE_DIR == settings.APPLICATION_ROOT / "data/shared/data-sources"
    assert settings.GLOBAL_TARGET_MODEL_DIR == settings.APPLICATION_ROOT / "data/shared/target-models"


def test_shared_target_model_directory_defaults_under_application_root(tmp_path) -> None:
    """The shared target model directory should use the configured default path."""
    settings = Settings(APPLICATION_ROOT=tmp_path)

    assert settings.GLOBAL_TARGET_MODEL_DIR == tmp_path / "shared/target-models"
    assert settings.GLOBAL_TARGET_MODEL_DIR.is_dir()
