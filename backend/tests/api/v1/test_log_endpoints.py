"""Tests for log endpoint authorization responses."""

from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.api.v1.endpoints import logs
from backend.app.authorization.models import ApplicationRole
from backend.app.authorization.repository import SQLiteAuthorizationRepository
from backend.app.core.config import settings as application_settings
from backend.app.main import app

LOG_PATHS = ["/api/v1/logs/app", "/api/v1/logs/app/download"]


@pytest.fixture(name="log_dependencies")
def _log_dependencies(tmp_path, monkeypatch):
    """Provide temporary log files, one administrator (alice) and one principal per other deployment role."""
    (tmp_path / "app.log").write_text("2026-09-07 | INFO     | Application started\n", encoding="utf-8")
    (tmp_path / "error.log").write_text("2026-09-07 | ERROR    | Request failed\n", encoding="utf-8")
    monkeypatch.setattr(logs, "get_settings", lambda: SimpleNamespace(LOG_DIR=tmp_path))

    database = tmp_path / "authorization.sqlite3"
    monkeypatch.setattr(application_settings, "AUTHORIZATION_DATABASE_PATH", database)
    repository = SQLiteAuthorizationRepository(database)
    repository.add_application_role("alice", ApplicationRole.ADMIN.value, "test")
    for role in ApplicationRole:
        if role != ApplicationRole.ADMIN:
            repository.add_application_role(role.value, role.value, "test")
    repository.close()
    return tmp_path


def _client_for_principal(principal_id: str | None) -> AsyncClient:
    """Create a client that optionally supplies a trusted-proxy identity."""

    async def authenticated_app(scope, receive, send) -> None:
        if scope["type"] == "http" and principal_id is not None:
            scope.setdefault("state", {})["authenticated_user"] = principal_id
        await app(scope, receive, send)

    return AsyncClient(transport=ASGITransport(app=authenticated_app), base_url="http://testserver")


@pytest.mark.parametrize("path", LOG_PATHS)
@pytest.mark.asyncio
async def test_log_endpoints_require_authentication(
    log_dependencies,  # pylint: disable=unused-argument
    path: str,
) -> None:
    async with _client_for_principal(None) as client:
        response = await client.get(path)

    assert response.status_code == 401


@pytest.mark.parametrize("path", LOG_PATHS)
@pytest.mark.parametrize("principal_id", ["bob", "project_creator", "operator", "project_maintainer"])
@pytest.mark.asyncio
async def test_log_endpoints_deny_principals_who_are_not_administrators(
    log_dependencies,  # pylint: disable=unused-argument
    principal_id: str,
    path: str,
) -> None:
    """Deny a principal with no role and a principal with any role other than admin."""
    async with _client_for_principal(principal_id) as client:
        response = await client.get(path)

    assert response.status_code == 403
    assert response.json() == {"detail": "Insufficient authorization"}


@pytest.mark.asyncio
async def test_administrator_can_read_and_download_logs(
    log_dependencies,  # pylint: disable=unused-argument
) -> None:
    async with _client_for_principal("alice") as client:
        read_response = await client.get("/api/v1/logs/app")
        download_response = await client.get("/api/v1/logs/error/download")

    assert read_response.status_code == 200
    assert read_response.json() == {"lines": ["2026-09-07 | INFO     | Application started"], "total": 1}
    assert download_response.status_code == 200
    assert download_response.json() == {"content": "2026-09-07 | ERROR    | Request failed\n", "filename": "error.log"}


@pytest.mark.parametrize("path", LOG_PATHS)
@pytest.mark.asyncio
async def test_log_read_failure_does_not_return_the_error_text(log_dependencies, path: str) -> None:
    """Return a general message with a correlation ID instead of the file error and its path."""
    log_file = log_dependencies / "app.log"
    log_file.unlink()
    log_file.mkdir()  # Opening a directory raises an OSError that names the full path.

    async with _client_for_principal("alice") as client:
        response = await client.get(path, headers={"X-Correlation-ID": "abc12345"})

    assert response.status_code == 500
    assert response.json() == {"detail": "Failed to read log file. Correlation ID: abc12345"}
