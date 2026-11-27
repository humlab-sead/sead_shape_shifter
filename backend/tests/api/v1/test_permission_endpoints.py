"""Tests for the endpoint that tells the UI what the current user may do."""

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.authorization.models import ApplicationRole
from backend.app.authorization.repository import SQLiteAuthorizationRepository
from backend.app.core.config import settings as application_settings
from backend.app.main import app

PATH = "/api/v1/me/permissions"


@pytest.fixture(name="role_database")
def _role_database(tmp_path, monkeypatch) -> None:
    """Provide an authorization database with one administrator and one operator."""
    database = tmp_path / "authorization.sqlite3"
    monkeypatch.setattr(application_settings, "AUTHORIZATION_DATABASE_PATH", database)
    repository = SQLiteAuthorizationRepository(database)
    repository.add_application_role("alice", ApplicationRole.ADMIN.value, "test")
    repository.add_application_role("olivia", ApplicationRole.OPERATOR.value, "test")
    repository.close()


def _client_for_principal(principal_id: str | None) -> AsyncClient:
    """Create a client that optionally supplies a trusted-proxy identity."""

    async def authenticated_app(scope, receive, send) -> None:
        if scope["type"] == "http" and principal_id is not None:
            scope.setdefault("state", {})["authenticated_user"] = principal_id
        await app(scope, receive, send)

    return AsyncClient(transport=ASGITransport(app=authenticated_app), base_url="http://testserver")


@pytest.mark.parametrize(("principal_id", "can_read_logs"), [("alice", True), ("olivia", False), ("bob", False)])
@pytest.mark.asyncio
async def test_permissions_report_whether_the_user_can_read_logs(
    role_database,  # pylint: disable=unused-argument
    principal_id: str,
    can_read_logs: bool,
) -> None:
    async with _client_for_principal(principal_id) as client:
        response = await client.get(PATH)

    assert response.status_code == 200
    assert response.json() == {"can_read_logs": can_read_logs}


@pytest.mark.asyncio
async def test_permissions_require_authentication(role_database) -> None:  # pylint: disable=unused-argument
    async with _client_for_principal(None) as client:
        response = await client.get(PATH)

    assert response.status_code == 401
