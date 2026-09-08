"""Tests for log endpoint authorization responses."""

from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.api.v1.endpoints import logs
from backend.app.authorization.dependencies import get_authorization_service
from backend.app.authorization.repository import SQLiteAuthorizationRepository
from backend.app.authorization.service import AuthorizationService
from backend.app.main import app


@pytest.fixture
def authorization_repository(tmp_path):
    """Create an isolated authorization store with one administrator."""
    repository = SQLiteAuthorizationRepository(tmp_path / "authorization.sqlite3")
    repository.add_application_role("alice", "admin", "bootstrap")
    yield repository
    repository.close()


@pytest.fixture
def log_dependencies(tmp_path, monkeypatch, authorization_repository: SQLiteAuthorizationRepository):
    """Provide temporary log files while retaining real authorization checks."""
    (tmp_path / "app.log").write_text("2026-09-07 | INFO     | Application started\n", encoding="utf-8")
    (tmp_path / "error.log").write_text("2026-09-07 | ERROR    | Request failed\n", encoding="utf-8")
    monkeypatch.setattr(logs, "get_settings", lambda: SimpleNamespace(LOG_DIR=tmp_path))

    async def override_get_authorization_service():
        repository = SQLiteAuthorizationRepository(authorization_repository.path)
        try:
            yield AuthorizationService(repository)
        finally:
            repository.close()

    app.dependency_overrides[get_authorization_service] = override_get_authorization_service
    yield
    app.dependency_overrides.clear()


def _client_for_principal(principal_id: str | None) -> AsyncClient:
    """Create a client that optionally supplies a trusted-proxy identity."""

    async def authenticated_app(scope, receive, send) -> None:
        if scope["type"] == "http" and principal_id is not None:
            scope.setdefault("state", {})["authenticated_user"] = principal_id
        await app(scope, receive, send)

    return AsyncClient(transport=ASGITransport(app=authenticated_app), base_url="http://testserver")


@pytest.mark.parametrize("path", ["/api/v1/logs/app", "/api/v1/logs/app/download"])
@pytest.mark.asyncio
async def test_log_endpoints_require_authentication(log_dependencies, path: str) -> None:
    async with _client_for_principal(None) as client:
        response = await client.get(path)

    assert response.status_code == 401


@pytest.mark.parametrize("path", ["/api/v1/logs/app", "/api/v1/logs/app/download"])
@pytest.mark.asyncio
async def test_log_endpoints_reject_non_administrators(log_dependencies, path: str) -> None:
    async with _client_for_principal("bob") as client:
        response = await client.get(path)

    assert response.status_code == 403
    assert response.json() == {"detail": "Insufficient authorization"}


@pytest.mark.asyncio
async def test_administrator_can_read_and_download_logs(log_dependencies) -> None:
    async with _client_for_principal("alice") as client:
        read_response = await client.get("/api/v1/logs/app")
        download_response = await client.get("/api/v1/logs/error/download")

    assert read_response.status_code == 200
    assert read_response.json() == {"lines": ["2026-09-07 | INFO     | Application started"], "total": 1}
    assert download_response.status_code == 200
    assert download_response.json() == {"content": "2026-09-07 | ERROR    | Request failed\n", "filename": "error.log"}
