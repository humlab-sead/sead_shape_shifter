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
    monkeypatch.setenv("SHAPE_SHIFTER_GLOBAL_DATA_PROVIDER_DIR", "./data/shared/data-providers")
    monkeypatch.setenv("SHAPE_SHIFTER_GLOBAL_TARGET_MODEL_DIR", "./data/shared/target-models")

    settings = Settings()

    assert settings.PROJECTS_DIR == settings.APPLICATION_ROOT / "data/projects"
    assert settings.LOG_DIR == settings.APPLICATION_ROOT / "data/logs"
    assert settings.GLOBAL_DATA_DIR == settings.APPLICATION_ROOT / "data/shared/shared-data"
    assert settings.GLOBAL_DATA_SOURCE_DIR == settings.APPLICATION_ROOT / "data/shared/data-sources"
    assert settings.GLOBAL_DATA_PROVIDER_DIR == settings.APPLICATION_ROOT / "data/shared/data-providers"
    assert settings.GLOBAL_TARGET_MODEL_DIR == settings.APPLICATION_ROOT / "data/shared/target-models"


def test_shared_target_model_directory_defaults_under_application_root(tmp_path) -> None:
    """The shared target model directory should use the configured default path."""
    settings = Settings(APPLICATION_ROOT=tmp_path)

    assert settings.GLOBAL_TARGET_MODEL_DIR == tmp_path / "shared/target-models"
    assert settings.GLOBAL_TARGET_MODEL_DIR.is_dir()


def test_global_data_provider_directory_defaults_under_application_root(tmp_path) -> None:
    """The curated provider registry should default below the application root and exist."""
    settings = Settings(APPLICATION_ROOT=tmp_path)

    assert settings.GLOBAL_DATA_PROVIDER_DIR == tmp_path / "shared/data-providers"
    assert settings.global_data_provider_dir == settings.GLOBAL_DATA_PROVIDER_DIR
    assert settings.GLOBAL_DATA_PROVIDER_DIR.is_dir()


def test_ingester_output_directory_resolves_under_application_root(tmp_path) -> None:
    """The project-ingester output directory is optional and resolves under the application root."""
    settings = Settings(APPLICATION_ROOT=tmp_path, INGEST_OUTPUT_DIR=Path("artifacts"))

    assert settings.INGEST_OUTPUT_DIR == tmp_path / "artifacts"


def test_blank_ingester_output_directory_is_unconfigured(tmp_path) -> None:
    """A blank project-ingester output directory must not become the current directory."""
    settings = Settings(APPLICATION_ROOT=tmp_path, INGEST_OUTPUT_DIR=" ")

    assert settings.INGEST_OUTPUT_DIR is None


def test_ingester_target_port_is_validated() -> None:
    """The project-ingester target port must be a valid TCP port."""
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Settings(INGEST_TARGET_PORT=0)
