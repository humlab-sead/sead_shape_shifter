"""Tests for FastAPI authorization dependencies."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import HTTPException

from backend.app.authorization.dependencies import (
    require_application_action,
    require_operation,
    require_project,
    require_shared_data_source,
)
from backend.app.authorization.models import Action, Grant, Principal, ResourceRecord, ResourceType
from backend.app.authorization.repository import SQLiteAuthorizationRepository
from backend.app.authorization.service import AuthorizationService
from backend.app.core.operation_manager import operation_manager


def _principal(principal_id: str = "alice") -> Principal:
    return Principal(principal_id, "test", datetime.now(UTC))


@pytest.mark.asyncio
async def test_project_dependency_returns_authorized_resource(tmp_path) -> None:
    repository = SQLiteAuthorizationRepository(tmp_path / "authorization.sqlite3")
    resource = ResourceRecord(uuid4(), ResourceType.PROJECT, "project-a")
    repository.create_resource(resource)
    repository.add_grant(Grant("alice", resource.resource_id, "viewer", datetime.now(UTC), "admin"))
    dependency = require_project(Action.READ)

    result = await dependency(_principal(), AuthorizationService(repository), project_name="project-a")

    assert result.resource.resource_id == resource.resource_id
    assert dependency.authorization_requirement == {"resource_type": "project", "action": "read"}
    repository.close()


@pytest.mark.asyncio
async def test_project_dependency_conceals_unknown_or_unauthorized_resources(tmp_path) -> None:
    repository = SQLiteAuthorizationRepository(tmp_path / "authorization.sqlite3")
    resource = ResourceRecord(uuid4(), ResourceType.PROJECT, "project-a")
    repository.create_resource(resource)
    dependency = require_project(Action.READ)

    with pytest.raises(HTTPException) as error:
        await dependency(_principal("bob"), AuthorizationService(repository), project_name="project-a")

    assert error.value.status_code == 404
    repository.close()


@pytest.mark.asyncio
async def test_project_dependency_accepts_name_route_parameter(tmp_path) -> None:
    repository = SQLiteAuthorizationRepository(tmp_path / "authorization.sqlite3")
    resource = ResourceRecord(uuid4(), ResourceType.PROJECT, "project-a")
    repository.create_resource(resource)
    repository.add_grant(Grant("alice", resource.resource_id, "viewer", datetime.now(UTC), "admin"))
    dependency = require_project(Action.READ)

    result = await dependency(_principal(), AuthorizationService(repository), name="project-a")

    assert result.resource.resource_id == resource.resource_id
    repository.close()


@pytest.mark.asyncio
async def test_application_dependency_rejects_principal_without_role(tmp_path) -> None:
    repository = SQLiteAuthorizationRepository(tmp_path / "authorization.sqlite3")
    dependency = require_application_action(Action.READ_LOGS)

    with pytest.raises(HTTPException) as error:
        await dependency(_principal(), AuthorizationService(repository))

    assert error.value.status_code == 403
    repository.close()


@pytest.mark.asyncio
async def test_shared_data_source_dependency_returns_authorized_resource(tmp_path) -> None:
    repository = SQLiteAuthorizationRepository(tmp_path / "authorization.sqlite3")
    resource = ResourceRecord(uuid4(), ResourceType.SHARED_DATA_SOURCE, "source-a")
    repository.create_resource(resource)
    repository.add_grant(Grant("alice", resource.resource_id, "reader", datetime.now(UTC), "admin"))
    dependency = require_shared_data_source(Action.READ)

    result = await dependency(_principal(), AuthorizationService(repository), filename="source-a.yml")

    assert result.resource.resource_id == resource.resource_id
    assert dependency.authorization_requirement == {"resource_type": "shared_data_source", "action": "read"}
    repository.close()


@pytest.mark.asyncio
async def test_shared_data_source_dependency_conceals_unknown_or_unauthorized_resources(tmp_path) -> None:
    repository = SQLiteAuthorizationRepository(tmp_path / "authorization.sqlite3")
    resource = ResourceRecord(uuid4(), ResourceType.SHARED_DATA_SOURCE, "source-a")
    repository.create_resource(resource)
    dependency = require_shared_data_source(Action.READ)

    with pytest.raises(HTTPException) as error:
        await dependency(_principal("bob"), AuthorizationService(repository), name="source-a")

    assert error.value.status_code == 404
    repository.close()


@pytest.mark.asyncio
async def test_operation_dependency_requires_owner_and_current_project_access(tmp_path) -> None:
    repository = SQLiteAuthorizationRepository(tmp_path / "authorization.sqlite3")
    resource = ResourceRecord(uuid4(), ResourceType.PROJECT, "project-a")
    repository.create_resource(resource)
    repository.add_grant(Grant("alice", resource.resource_id, "viewer", datetime.now(UTC), "admin"))
    operation_id = operation_manager.create_operation(
        operation_type="test",
        owner_principal_id="alice",
        project_resource_id=str(resource.resource_id),
    )
    dependency = require_operation(Action.READ)

    result = await dependency(operation_id, _principal(), AuthorizationService(repository))
    assert result.operation_id == operation_id

    with pytest.raises(HTTPException) as error:
        await dependency(operation_id, _principal("bob"), AuthorizationService(repository))

    assert error.value.status_code == 404
    operation_manager.cleanup_operation(operation_id)
    repository.close()
