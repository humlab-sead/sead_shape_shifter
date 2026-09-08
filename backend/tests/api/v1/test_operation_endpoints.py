"""Tests for operation endpoint authorization responses."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.authorization.dependencies import get_authorization_service
from backend.app.authorization.models import Grant, ResourceRecord, ResourceType
from backend.app.authorization.repository import SQLiteAuthorizationRepository
from backend.app.authorization.service import AuthorizationService
from backend.app.core.operation_manager import operation_manager
from backend.app.main import app


@pytest.fixture
def authorization_repository(tmp_path):
    """Create an isolated store with the project that owns an operation."""
    repository = SQLiteAuthorizationRepository(tmp_path / "authorization.sqlite3")
    project = ResourceRecord(uuid4(), ResourceType.PROJECT, "project-a")
    repository.create_resource(project)
    yield repository, project
    repository.close()


@pytest.fixture
def operation_dependencies(authorization_repository):
    """Create an operation and retain the real authorization dependency."""
    repository, project = authorization_repository
    operation_id = operation_manager.create_operation(
        operation_type="test",
        owner_principal_id="alice",
        project_resource_id=str(project.resource_id),
        total=1,
    )

    async def override_get_authorization_service():
        request_repository = SQLiteAuthorizationRepository(repository.path)
        try:
            yield AuthorizationService(request_repository)
        finally:
            request_repository.close()

    app.dependency_overrides[get_authorization_service] = override_get_authorization_service
    yield operation_id, repository, project
    app.dependency_overrides.clear()
    operation_manager.cleanup_operation(operation_id)


def _client_for_principal(principal_id: str | None) -> AsyncClient:
    """Create a client that optionally supplies a trusted-proxy identity."""

    async def authenticated_app(scope, receive, send) -> None:
        if scope["type"] == "http" and principal_id is not None:
            scope.setdefault("state", {})["authenticated_user"] = principal_id
        await app(scope, receive, send)

    return AsyncClient(transport=ASGITransport(app=authenticated_app), base_url="http://testserver")


@pytest.mark.parametrize("method, suffix", [("get", "progress"), ("get", "stream"), ("post", "cancel")])
@pytest.mark.asyncio
async def test_operation_endpoints_require_authentication(operation_dependencies, method: str, suffix: str) -> None:
    operation_id, _, _ = operation_dependencies
    async with _client_for_principal(None) as client:
        response = await getattr(client, method)(f"/api/v1/operations/{operation_id}/{suffix}")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_operation_endpoints_conceal_operations_from_non_owners(operation_dependencies) -> None:
    operation_id, repository, project = operation_dependencies
    repository.add_grant(Grant("bob", project.resource_id, "editor", datetime.now(UTC), "admin"))

    async with _client_for_principal("bob") as client:
        progress_response = await client.get(f"/api/v1/operations/{operation_id}/progress")
        cancel_response = await client.post(f"/api/v1/operations/{operation_id}/cancel")

    assert progress_response.status_code == 404
    assert cancel_response.status_code == 404


@pytest.mark.asyncio
async def test_operation_endpoints_require_current_project_access_from_owner(operation_dependencies) -> None:
    operation_id, _, _ = operation_dependencies

    async with _client_for_principal("alice") as client:
        response = await client.get(f"/api/v1/operations/{operation_id}/progress")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_editor_owner_can_access_and_cancel_operation(operation_dependencies) -> None:
    operation_id, repository, project = operation_dependencies
    repository.add_grant(Grant("alice", project.resource_id, "editor", datetime.now(UTC), "admin"))

    async with _client_for_principal("alice") as client:
        progress_response = await client.get(f"/api/v1/operations/{operation_id}/progress")
        cancel_response = await client.post(f"/api/v1/operations/{operation_id}/cancel")

    assert progress_response.status_code == 200
    assert progress_response.json()["operation_id"] == operation_id
    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_editor_owner_can_stream_completed_operation(operation_dependencies) -> None:
    operation_id, repository, project = operation_dependencies
    repository.add_grant(Grant("alice", project.resource_id, "editor", datetime.now(UTC), "admin"))
    operation_manager.complete_operation(operation_id)

    async with _client_for_principal("alice") as client:
        response = await client.get(f"/api/v1/operations/{operation_id}/stream")

    assert response.status_code == 200
    assert f'"operation_id": "{operation_id}"' in response.text
