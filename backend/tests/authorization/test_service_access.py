"""Tests for authorization enforcement at sensitive service boundaries."""

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from backend.app.authorization.models import Action, AuthorizedResource, Principal, ResourceRecord, ResourceType
from backend.app.models.execute import ExecuteRequest
from backend.app.services.execute_service import ExecuteService


def _principal(principal_id: str = "alice") -> Principal:
    return Principal(principal_id, "test", datetime.now(UTC))


def _resource(action: Action = Action.EXECUTE, resource_type: ResourceType = ResourceType.PROJECT) -> AuthorizedResource:
    return AuthorizedResource(_principal(), action, ResourceRecord(uuid4(), resource_type, "project-a"))


def _request() -> ExecuteRequest:
    return ExecuteRequest(dispatcher_key="csv", target="output.csv")


@pytest.mark.asyncio
async def test_execute_service_rejects_missing_authorization_before_loading_project() -> None:
    project_service = MagicMock()
    service = ExecuteService(project_service=project_service)

    with pytest.raises(PermissionError, match="not authorized"):
        await service.execute_workflow(None, _request())

    project_service.load_project.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "authorized_project",
    [
        _resource(Action.READ),
        _resource(Action.EXECUTE, ResourceType.PROJECT_CHILD),
        AuthorizedResource(_principal(), Action.EXECUTE, ResourceRecord(uuid4(), ResourceType.PROJECT, "project-a", "deleted")),
    ],
)
async def test_execute_service_rejects_unchecked_project_work(authorized_project: AuthorizedResource) -> None:
    project_service = MagicMock()
    service = ExecuteService(project_service=project_service)

    with pytest.raises(PermissionError, match="not authorized"):
        await service.execute_workflow(authorized_project, _request())

    project_service.load_project.assert_not_called()


@pytest.mark.asyncio
async def test_execute_service_uses_authorized_project_locator() -> None:
    project_service = MagicMock()
    project_service.load_project.side_effect = RuntimeError("stop before workflow")
    service = ExecuteService(project_service=project_service)

    result = await service.execute_workflow(_resource(), _request())

    assert result.success is False
    project_service.load_project.assert_called_once_with("project-a")
