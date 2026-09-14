"""Security regression tests for public errors and server log values."""

from unittest.mock import patch

import pytest
from starlette.requests import Request

from backend.app.main import global_exception_handler
from backend.app.middleware.correlation import correlation_id_var
from backend.app.utils.public_errors import public_error_detail
from backend.app.utils.safe_logging import sanitize_log_value


def _request(path: str = "/api/v1/test") -> Request:
    return Request({"type": "http", "method": "GET", "path": path, "headers": [], "query_string": b""})


@pytest.mark.asyncio
async def test_global_exception_handler_returns_stable_redacted_response() -> None:
    token = correlation_id_var.set("corr-redaction")
    try:
        response = await global_exception_handler(
            _request(),
            RuntimeError(
                "password=super-secret connection=postgresql://user:db-secret@db.internal/app " "SELECT * FROM users /srv/private/file.txt"
            ),
        )
    finally:
        correlation_id_var.reset(token)

    body = response.body.decode()
    assert response.status_code == 500
    assert "super-secret" not in body
    assert "db-secret" not in body
    assert "SELECT * FROM users" not in body
    assert "/srv/private/file.txt" not in body
    assert "corr-redaction" in body
    assert "InternalServerError" in body


def test_log_values_redact_credentials_and_escape_newlines() -> None:
    value = "password=secret\nFORGED level=ERROR postgres://user:db-pass@host/path"

    sanitized = sanitize_log_value(value)

    assert "secret" not in sanitized
    assert "db-pass" not in sanitized
    assert "\n" not in sanitized
    assert "\\n" in sanitized
    assert "[REDACTED]" in sanitized


@pytest.mark.asyncio
async def test_data_source_connection_failure_has_public_message() -> None:
    from backend.app.models.data_source import DataSourceConfig
    from backend.app.services.data_source_service import DataSourceService

    service = DataSourceService(data_sources_dir="/tmp")
    config = DataSourceConfig(name="private", driver="postgresql", host="db.internal", database="app", username="user")

    with (
        patch("backend.app.services.data_source_service.DataSourceMapper.to_core_config", side_effect=RuntimeError("password=secret")),
        patch("backend.app.services.data_source_service.logger.error") as log_error,
    ):
        result = await service.test_connection(config)

    assert result.success is False
    assert result.message == public_error_detail("Connection failed")
    assert "secret" not in result.message
    assert "password" not in log_error.call_args.args[0]
