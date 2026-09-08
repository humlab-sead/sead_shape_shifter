"""Regression tests for cross-resource authorization at HTTP boundaries."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.authorization.dependencies import get_authorization_service
from backend.app.authorization.models import Action, Grant, GrantSubjectType, Principal, ResourceRecord, ResourceType
from backend.app.authorization.repository import SQLiteAuthorizationRepository
from backend.app.authorization.service import AuthorizationService
from backend.app.core.config import settings as application_settings
from backend.app.main import app
from backend.app.middleware.proxy_auth import ProxyAuthenticationMiddleware


@pytest.mark.asyncio
async def test_authenticated_principal_cannot_cross_user_resource_boundaries(tmp_path, monkeypatch) -> None:
    """Reject Bob's access to Alice's project, source, schema, query, and tasks."""
    authorization_database = tmp_path / "state" / "authorization.sqlite3"
    monkeypatch.setattr(application_settings, "AUTHORIZATION_DATABASE_PATH", authorization_database)

    repository = SQLiteAuthorizationRepository(authorization_database)
    project = ResourceRecord(uuid4(), ResourceType.PROJECT, "alice-project")
    source = ResourceRecord(uuid4(), ResourceType.SHARED_DATA_SOURCE, "alice-source")
    repository.create_resource(project)
    repository.create_resource(source)
    repository.add_grant(Grant("alice", project.resource_id, "owner", datetime.now(UTC), "bootstrap"))
    repository.add_grant(Grant("alice", source.resource_id, "reader", datetime.now(UTC), "bootstrap"))
    authorization_service = AuthorizationService(repository)
    previous_overrides = app.dependency_overrides.copy()

    async def override_authorization_service() -> AuthorizationService:
        return authorization_service

    app.dependency_overrides[get_authorization_service] = override_authorization_service
    protected_app = ProxyAuthenticationMiddleware(
        app,
        enabled=True,
        header_name=application_settings.TRUSTED_PROXY_AUTH_HEADER,
        public_paths={"/api/v1/health"},
    )

    cases = (
        ("GET", "/api/v1/projects/alice-project", None, 404),
        ("GET", "/api/v1/projects/alice-project/tasks", None, 404),
        ("GET", "/api/v1/data-sources/alice-source.yml", None, 404),
        ("GET", "/api/v1/data-sources/alice-source/tables/sites/schema", None, 404),
        ("POST", "/api/v1/data-sources/alice-source/query/validate", {"query": "SELECT 1"}, 404),
    )

    try:
        async with AsyncClient(
            transport=ASGITransport(app=protected_app),
            base_url="http://testserver",
            headers={application_settings.TRUSTED_PROXY_AUTH_HEADER: "bob"},
        ) as client:
            for method, path, payload, expected_status in cases:
                response = await client.request(method, path, json=payload)
                assert response.status_code == expected_status, f"{method} {path}: {response.text}"
                assert response.json() == {"detail": "Resource not found"}
    finally:
        app.dependency_overrides = previous_overrides
        repository.close()


@pytest.mark.asyncio
async def test_authenticated_principal_without_log_role_cannot_read_logs(tmp_path, monkeypatch) -> None:
    """Reject a principal without the application log role before reading files."""
    authorization_database = tmp_path / "state" / "authorization.sqlite3"
    monkeypatch.setattr(application_settings, "AUTHORIZATION_DATABASE_PATH", authorization_database)

    repository = SQLiteAuthorizationRepository(authorization_database)
    authorization_service = AuthorizationService(repository)
    previous_overrides = app.dependency_overrides.copy()

    async def override_authorization_service() -> AuthorizationService:
        return authorization_service

    app.dependency_overrides[get_authorization_service] = override_authorization_service
    protected_app = ProxyAuthenticationMiddleware(
        app,
        enabled=True,
        header_name=application_settings.TRUSTED_PROXY_AUTH_HEADER,
        public_paths={"/api/v1/health"},
    )

    try:
        async with AsyncClient(
            transport=ASGITransport(app=protected_app),
            base_url="http://testserver",
            headers={application_settings.TRUSTED_PROXY_AUTH_HEADER: "bob"},
        ) as client:
            response = await client.get("/api/v1/logs/app")

        assert response.status_code == 403
        assert response.json() == {"detail": "Insufficient authorization"}
    finally:
        app.dependency_overrides = previous_overrides
        repository.close()


def test_group_grants_do_not_cross_team_boundaries(tmp_path) -> None:
    """Allow a team grant only to members of that team."""
    repository = SQLiteAuthorizationRepository(tmp_path / "authorization.sqlite3")
    resource = ResourceRecord(uuid4(), ResourceType.PROJECT, "team-project")
    repository.create_resource(resource)
    repository.add_grant(Grant("team-a", resource.resource_id, "viewer", datetime.now(UTC), "bootstrap", GrantSubjectType.GROUP))
    service = AuthorizationService(repository)

    team_a_member = Principal("alice", "test", datetime.now(UTC), frozenset({"team-a"}))
    team_b_member = Principal("bob", "test", datetime.now(UTC), frozenset({"team-b"}))

    assert service.authorize(team_a_member, Action.READ, resource) is not None
    assert service.authorize(team_b_member, Action.READ, resource) is None
    repository.close()
