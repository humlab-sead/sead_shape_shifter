"""Tests for authorization-related application settings."""

import pytest
from loguru import logger

from backend.app.core.config import Settings, settings
from backend.app.main import _log_development_authorization_bootstrap_hint


def test_authorization_database_defaults_to_application_state(tmp_path) -> None:
    config = Settings(APPLICATION_ROOT=tmp_path)

    assert config.AUTHORIZATION_DATABASE_PATH == tmp_path / "state/authorization.sqlite3"


def test_authorization_database_cannot_be_stored_in_project_data(tmp_path) -> None:
    with pytest.raises(ValueError, match="AUTHORIZATION_DATABASE_PATH"):
        Settings(
            APPLICATION_ROOT=tmp_path,
            AUTHORIZATION_DATABASE_PATH=tmp_path / "projects/authorization.sqlite3",
        )


def test_development_principal_is_rejected_in_production(tmp_path) -> None:
    with pytest.raises(ValueError, match="DEVELOPMENT_PRINCIPAL_ID"):
        Settings(
            APPLICATION_ROOT=tmp_path,
            ENVIRONMENT="production",
            TRUSTED_PROXY_AUTH_ENABLED=True,
            DEVELOPMENT_PRINCIPAL_ID="developer",
        )


def test_production_requires_bootstrap_administrator(tmp_path) -> None:
    with pytest.raises(ValueError, match="AUTHORIZATION_BOOTSTRAP_ADMIN_PRINCIPALS"):
        Settings(
            APPLICATION_ROOT=tmp_path,
            ENVIRONMENT="production",
            TRUSTED_PROXY_AUTH_ENABLED=True,
        )


def test_production_accepts_configured_bootstrap_administrator(tmp_path) -> None:
    config = Settings(
        APPLICATION_ROOT=tmp_path,
        ENVIRONMENT="production",
        TRUSTED_PROXY_AUTH_ENABLED=True,
        AUTHORIZATION_BOOTSTRAP_ADMIN_PRINCIPALS=["alice"],
    )

    assert config.AUTHORIZATION_BOOTSTRAP_ADMIN_PRINCIPALS == ["alice"]


def test_debug_startup_logs_bootstrap_command_only_when_opted_in(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(settings, "TRUSTED_PROXY_AUTH_ENABLED", False)
    monkeypatch.setattr(settings, "AUTHORIZATION_DEV_BOOTSTRAP_HINT_ENABLED", False)
    monkeypatch.setattr(settings, "DEVELOPMENT_PRINCIPAL_ID", "local developer")
    monkeypatch.setattr(settings, "APPLICATION_ROOT", tmp_path)
    monkeypatch.setattr(settings, "AUTHORIZATION_DATABASE_PATH", tmp_path / "state" / "authorization-dev.sqlite3")
    monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path / "projects")
    monkeypatch.setattr(settings, "GLOBAL_DATA_SOURCE_DIR", tmp_path / "shared" / "data-sources")
    settings.PROJECTS_DIR.mkdir(parents=True)
    settings.GLOBAL_DATA_SOURCE_DIR.mkdir(parents=True)

    messages: list[str] = []
    sink_id = logger.add(
        lambda message: messages.append(str(message)),
        filter=lambda record: record["level"].name == "WARNING",
    )
    try:
        _log_development_authorization_bootstrap_hint()
        assert messages == []

        monkeypatch.setattr(settings, "AUTHORIZATION_DEV_BOOTSTRAP_HINT_ENABLED", True)
        _log_development_authorization_bootstrap_hint()
    finally:
        logger.remove(sink_id)

    assert len(messages) == 1
    assert "uv run sead-authorization dev-bootstrap" in messages[0]
    assert "SHAPE_SHIFTER_DEVELOPMENT_PRINCIPAL_ID='local developer'" in messages[0]
    assert "SHAPE_SHIFTER_TRUSTED_PROXY_AUTH_ENABLED=false \\\nSHAPE_SHIFTER_DEVELOPMENT_PRINCIPAL_ID=" in messages[0]
    assert "+SHAPE_SHIFTER_" not in messages[0]
    assert not settings.AUTHORIZATION_DATABASE_PATH.exists()
