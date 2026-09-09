"""Tests for backend settings path resolution."""

from __future__ import annotations

from pathlib import Path

from backend.app.core.config import Settings


def test_relative_paths_resolve_against_repository_root(monkeypatch) -> None:
    """Relative config paths should not depend on the current working directory."""
    monkeypatch.chdir(Path("/home/roger/source/sead_shape_shifter/data/projects/arbodat"))
    monkeypatch.setenv("SHAPE_SHIFTER_PROJECTS_DIR", "./data/projects")
    monkeypatch.setenv("SHAPE_SHIFTER_LOG_DIR", "./data/logs")
    monkeypatch.setenv("SHAPE_SHIFTER_GLOBAL_DATA_DIR", "./data/shared/shared-data")
    monkeypatch.setenv("SHAPE_SHIFTER_GLOBAL_DATA_SOURCE_DIR", "./data/shared/data-sources")

    settings = Settings()

    assert settings.PROJECTS_DIR == settings.APPLICATION_ROOT / "data/projects"
    assert settings.LOG_DIR == settings.APPLICATION_ROOT / "data/logs"
    assert settings.GLOBAL_DATA_DIR == settings.APPLICATION_ROOT / "data/shared/shared-data"
    assert settings.GLOBAL_DATA_SOURCE_DIR == settings.APPLICATION_ROOT / "data/shared/data-sources"
