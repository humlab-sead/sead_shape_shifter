"""Tests for backend settings path resolution."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from pydantic import ValidationError

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


def test_resolver_directory_vars_exported_to_environment(tmp_path, monkeypatch) -> None:
    """Constructing Settings publishes the approved directory variables to os.environ.

    The Core directive resolver expands ${GLOBAL_DATA_SOURCE_DIR} and friends from
    os.environ, which pydantic-settings does not populate from .env. Without the
    export step, a directory configured only in .env expands to an empty string.
    """
    for name in ("APPLICATION_ROOT", "GLOBAL_DATA_DIR", "GLOBAL_DATA_SOURCE_DIR", "GLOBAL_TARGET_MODEL_DIR"):
        monkeypatch.delenv(name, raising=False)

    settings = Settings(APPLICATION_ROOT=tmp_path)

    assert os.environ["APPLICATION_ROOT"] == str(settings.APPLICATION_ROOT)
    assert os.environ["GLOBAL_DATA_DIR"] == str(settings.GLOBAL_DATA_DIR)
    assert os.environ["GLOBAL_DATA_SOURCE_DIR"] == str(settings.GLOBAL_DATA_SOURCE_DIR)
    assert os.environ["GLOBAL_TARGET_MODEL_DIR"] == str(settings.GLOBAL_TARGET_MODEL_DIR)


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
    # The blank-string before-validator accepts raw strings, which the declared Path type rejects.
    settings = Settings(APPLICATION_ROOT=tmp_path, INGEST_OUTPUT_DIR=" ")  # pyright: ignore[reportArgumentType]

    assert settings.INGEST_OUTPUT_DIR is None


def test_ingester_target_port_is_validated() -> None:
    """The project-ingester target port must be a valid TCP port."""

    with pytest.raises(ValidationError):
        Settings(INGEST_TARGET_PORT=0)


def test_link_trial_output_row_limit_defaults_to_one_million(tmp_path) -> None:
    """The link-trial output-row limit defaults to one million."""
    settings = Settings(_env_file=None, APPLICATION_ROOT=tmp_path)  # pyright: ignore[reportCallIssue]

    assert settings.LINK_TRIAL_MAX_OUTPUT_ROWS == 1_000_000


def test_link_trial_output_row_limit_reads_environment_override(monkeypatch, tmp_path) -> None:
    """The link-trial output-row limit can be overridden with its prefixed environment variable."""
    monkeypatch.setenv("SHAPE_SHIFTER_LINK_TRIAL_MAX_OUTPUT_ROWS", "250")
    settings = Settings(_env_file=None, APPLICATION_ROOT=tmp_path)  # pyright: ignore[reportCallIssue]

    assert settings.LINK_TRIAL_MAX_OUTPUT_ROWS == 250


@pytest.mark.parametrize("limit", [0, -1])
def test_link_trial_output_row_limit_must_be_positive(limit: int, tmp_path) -> None:
    """The link-trial output-row limit must be greater than zero."""
    with pytest.raises(ValidationError):
        Settings(_env_file=None, APPLICATION_ROOT=tmp_path, LINK_TRIAL_MAX_OUTPUT_ROWS=limit)  # pyright: ignore[reportCallIssue]


def test_link_experiment_memory_limit_defaults_to_one_hundred_mib(tmp_path) -> None:
    """The link-experiment memory limit defaults to 100 MiB."""
    settings = Settings(_env_file=None, APPLICATION_ROOT=tmp_path)  # pyright: ignore[reportCallIssue]

    assert settings.LINK_EXPERIMENT_MAX_MEMORY_MB == 100


def test_link_experiment_memory_limit_reads_environment_override(monkeypatch, tmp_path) -> None:
    """The link-experiment memory limit can be overridden with its prefixed environment variable."""
    monkeypatch.setenv("SHAPE_SHIFTER_LINK_EXPERIMENT_MAX_MEMORY_MB", "250")
    settings = Settings(_env_file=None, APPLICATION_ROOT=tmp_path)  # pyright: ignore[reportCallIssue]

    assert settings.LINK_EXPERIMENT_MAX_MEMORY_MB == 250


@pytest.mark.parametrize("limit", [0, -1])
def test_link_experiment_memory_limit_must_be_positive(limit: int, tmp_path) -> None:
    """The link-experiment memory limit must be greater than zero."""
    with pytest.raises(ValidationError):
        Settings(_env_file=None, APPLICATION_ROOT=tmp_path, LINK_EXPERIMENT_MAX_MEMORY_MB=limit)  # pyright: ignore[reportCallIssue]


def test_link_experiment_group_row_cap_defaults_to_one_hundred(tmp_path) -> None:
    """The exception-group row cap defaults to 100 rows."""
    settings = Settings(_env_file=None, APPLICATION_ROOT=tmp_path)  # pyright: ignore[reportCallIssue]

    assert settings.LINK_EXPERIMENT_GROUP_ROW_CAP == 100


def test_link_experiment_group_row_cap_reads_environment_override(monkeypatch, tmp_path) -> None:
    """The exception-group row cap can be overridden with its prefixed environment variable."""
    monkeypatch.setenv("SHAPE_SHIFTER_LINK_EXPERIMENT_GROUP_ROW_CAP", "250")
    settings = Settings(_env_file=None, APPLICATION_ROOT=tmp_path)  # pyright: ignore[reportCallIssue]

    assert settings.LINK_EXPERIMENT_GROUP_ROW_CAP == 250


@pytest.mark.parametrize("limit", [0, 1001])
def test_link_experiment_group_row_cap_stays_within_bounds(limit: int, tmp_path) -> None:
    """The exception-group row cap must be between 1 and 1000 rows."""
    with pytest.raises(ValidationError):
        Settings(_env_file=None, APPLICATION_ROOT=tmp_path, LINK_EXPERIMENT_GROUP_ROW_CAP=limit)  # pyright: ignore[reportCallIssue]
