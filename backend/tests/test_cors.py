"""Tests for the backend CORS configuration."""

from pydantic import ValidationError

from backend.app.core.config import Settings


def test_cors_defaults_are_local_only() -> None:
    """The default CORS policy trusts only local development origins."""
    settings = Settings(_env_file=None)

    assert settings.ALLOWED_ORIGINS == [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]
    assert settings.ALLOWED_ORIGIN_REGEX is None


def test_cors_remote_origins_can_be_configured_explicitly() -> None:
    """A deployment can provide an exact trusted frontend origin."""
    settings = Settings(
        _env_file=None,
        ALLOWED_ORIGINS=["https://shape-shifter.sead.se"],
        ALLOWED_ORIGIN_REGEX=None,
    )

    assert settings.ALLOWED_ORIGINS == ["https://shape-shifter.sead.se"]
    assert settings.ALLOWED_ORIGIN_REGEX is None


def test_production_requires_trusted_proxy_authentication() -> None:
    """Production settings fail closed when proxy authentication is not enabled."""
    try:
        Settings(_env_file=None, ENVIRONMENT="production", TRUSTED_PROXY_AUTH_ENABLED=False)
    except ValidationError as exc:
        assert "TRUSTED_PROXY_AUTH_ENABLED must be true in production" in str(exc)
    else:
        raise AssertionError("Production settings must require trusted-proxy authentication")
