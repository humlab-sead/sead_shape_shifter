"""Tests for authorization-related application settings."""

import pytest

from backend.app.core.config import Settings


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
