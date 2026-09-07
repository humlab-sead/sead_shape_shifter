"""Tests for FastAPI authorization dependencies."""

import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import HTTPException, Request
from fastapi.routing import APIRoute

from backend.app.api.v1.api import api_router
from backend.app.api.v1.endpoints.logs import router as logs_router
from backend.app.api.v1.endpoints.projects import (
    _authorize_referenced_shared_data_sources,
)
from backend.app.api.v1.endpoints.projects import router as projects_router
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


def _json_request(payload: dict[str, str]) -> Request:
    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": json.dumps(payload).encode(), "more_body": False}

    return Request({"type": "http", "method": "POST", "headers": []}, receive=receive)


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

    result = await dependency(_json_request({}), _principal(), AuthorizationService(repository), filename="source-a.yml")

    assert result.resource.resource_id == resource.resource_id
    assert dependency.authorization_requirement == {"resource_type": "shared_data_source", "action": "read"}
    repository.close()


@pytest.mark.asyncio
async def test_shared_data_source_dependency_authorizes_source_filename_from_request_body(tmp_path) -> None:
    repository = SQLiteAuthorizationRepository(tmp_path / "authorization.sqlite3")
    resource = ResourceRecord(uuid4(), ResourceType.SHARED_DATA_SOURCE, "source-a")
    repository.create_resource(resource)
    repository.add_grant(Grant("alice", resource.resource_id, "reader", datetime.now(UTC), "admin"))
    dependency = require_shared_data_source(Action.READ)

    result = await dependency(_json_request({"source_filename": "source-a.yml"}), _principal(), AuthorizationService(repository))

    assert result.resource.resource_id == resource.resource_id
    repository.close()


@pytest.mark.asyncio
async def test_shared_data_source_dependency_conceals_unknown_or_unauthorized_resources(tmp_path) -> None:
    repository = SQLiteAuthorizationRepository(tmp_path / "authorization.sqlite3")
    resource = ResourceRecord(uuid4(), ResourceType.SHARED_DATA_SOURCE, "source-a")
    repository.create_resource(resource)
    dependency = require_shared_data_source(Action.READ)

    with pytest.raises(HTTPException) as error:
        await dependency(_json_request({}), _principal("bob"), AuthorizationService(repository), name="source-a")

    assert error.value.status_code == 404
    repository.close()


def test_project_source_references_require_access_to_every_shared_source(tmp_path) -> None:
    repository = SQLiteAuthorizationRepository(tmp_path / "authorization.sqlite3")
    readable_resource = ResourceRecord(uuid4(), ResourceType.SHARED_DATA_SOURCE, "readable-source")
    unavailable_resource = ResourceRecord(uuid4(), ResourceType.SHARED_DATA_SOURCE, "unavailable-source")
    repository.create_resource(readable_resource)
    repository.create_resource(unavailable_resource)
    repository.add_grant(Grant("alice", readable_resource.resource_id, "reader", datetime.now(UTC), "admin"))
    service = AuthorizationService(repository)

    _authorize_referenced_shared_data_sources({"readable": "@include: readable-source.yml"}, _principal(), service)

    with pytest.raises(HTTPException) as error:
        _authorize_referenced_shared_data_sources(
            {"readable": "@include: readable-source.yml", "unavailable": "@include: unavailable-source.yml"},
            _principal(),
            service,
        )

    assert error.value.status_code == 404
    repository.close()


def test_project_data_source_connection_requires_project_and_shared_source_access() -> None:
    route = next(
        route
        for route in projects_router.routes
        if isinstance(route, APIRoute) and route.path == "/projects/{name}/data-sources" and "POST" in route.methods
    )

    requirements = {
        tuple(sorted(dependency.call.authorization_requirement.items()))
        for dependency in route.dependant.dependencies
        if hasattr(dependency.call, "authorization_requirement")
    }

    assert requirements == {
        (("action", "edit"), ("resource_type", "project")),
        (("action", "read"), ("resource_type", "shared_data_source")),
    }


def test_log_routes_require_administrator_access() -> None:
    log_routes = [
        route
        for route in logs_router.routes
        if isinstance(route, APIRoute) and route.path in {"/logs/{log_type}", "/logs/{log_type}/download"}
    ]

    assert len(log_routes) == 2
    for route in log_routes:
        requirements = {
            tuple(sorted(dependency.call.authorization_requirement.items()))
            for dependency in route.dependant.dependencies
            if hasattr(dependency.call, "authorization_requirement")
        }
        assert requirements == {(("action", "read_logs"), ("resource_type", "application"))}


def test_sensitive_locator_routes_declare_authorization_requirements() -> None:
    """Report registered resource routes that can bypass authorization dependencies."""
    missing_requirements: list[str] = []

    for route in api_router.routes:
        if not isinstance(route, APIRoute):
            continue
        is_sensitive_locator = (
            route.path.startswith("/projects/{")
            or route.path.startswith("/operations/{")
            or (route.path.startswith("/data-sources/{") and "/{" in route.path)
        )
        if not is_sensitive_locator:
            continue
        requirements = [
            dependency.call.authorization_requirement
            for dependency in route.dependant.dependencies
            if hasattr(dependency.call, "authorization_requirement")
        ]
        if not requirements:
            methods = ",".join(sorted(route.methods))
            missing_requirements.append(f"{methods} {route.path}")

    assert not missing_requirements, "Sensitive routes without authorization declarations:\n" + "\n".join(missing_requirements)


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
