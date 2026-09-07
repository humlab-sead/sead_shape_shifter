"""Tests for project authorization integration helpers."""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, call
from uuid import uuid4

import pytest
import yaml
from fastapi import HTTPException

from backend.app.api.v1.endpoints import projects
from backend.app.api.v1.endpoints.projects import ProjectCreateRequest
from backend.app.authorization.models import Action, AuthorizedResource, Grant, Principal, ResourceRecord, ResourceType
from backend.app.authorization.repository import SQLiteAuthorizationRepository
from backend.app.authorization.service import AuthorizationService
from backend.app.services.project_service import ProjectService


def _principal(principal_id: str = "alice") -> Principal:
    return Principal(principal_id, "test", datetime.now(UTC))


def _write_project(projects_dir: Path, name: str) -> None:
    project_dir = projects_dir / name
    project_dir.mkdir(parents=True)
    (project_dir / "shapeshifter.yml").write_text(
        yaml.dump(
            {
                "metadata": {"type": "shapeshifter-project", "name": name},
                "entities": {},
                "options": {},
            }
        ),
        encoding="utf-8",
    )


def test_list_authorized_projects_filters_unreadable_projects(tmp_path) -> None:
    _write_project(tmp_path, "project-a")
    _write_project(tmp_path, "project-b")
    repository = SQLiteAuthorizationRepository(tmp_path / "authorization.sqlite3")
    project_a = ResourceRecord(uuid4(), ResourceType.PROJECT, "project-a")
    project_b = ResourceRecord(uuid4(), ResourceType.PROJECT, "project-b")
    repository.create_resource(project_a)
    repository.create_resource(project_b)
    repository.add_grant(Grant("alice", project_a.resource_id, "viewer", datetime.now(UTC), "admin"))

    projects = ProjectService(projects_dir=tmp_path).list_authorized_projects(_principal(), AuthorizationService(repository))

    assert [project.name for project in projects] == ["project-a"]
    repository.close()


def test_assign_project_owner_creates_resource_and_owner_grant(tmp_path) -> None:
    repository = SQLiteAuthorizationRepository(tmp_path / "authorization.sqlite3")

    resource = ProjectService(projects_dir=tmp_path).assign_project_owner("project-a", _principal(), AuthorizationService(repository))

    assert repository.get_resource_by_locator(ResourceType.PROJECT, "project-a") == resource
    grants = repository.list_grants("alice")
    assert len(grants) == 1
    assert grants[0].resource_id == resource.resource_id
    assert grants[0].role == "owner"
    repository.close()


def test_users_are_isolated_between_projects_project_children_and_shared_sources(tmp_path) -> None:
    repository = SQLiteAuthorizationRepository(tmp_path / "authorization.sqlite3")
    project_a = ResourceRecord(uuid4(), ResourceType.PROJECT, "project-a")
    project_b = ResourceRecord(uuid4(), ResourceType.PROJECT, "project-b")
    output_a = ResourceRecord(uuid4(), ResourceType.PROJECT_CHILD, "output-a", parent_resource_id=project_a.resource_id)
    backup_a = ResourceRecord(uuid4(), ResourceType.PROJECT_CHILD, "backup-a", parent_resource_id=project_a.resource_id)
    source_b = ResourceRecord(uuid4(), ResourceType.SHARED_DATA_SOURCE, "source-b")
    for resource in (project_a, project_b, output_a, backup_a, source_b):
        repository.create_resource(resource)
    repository.add_grant(Grant("alice", project_a.resource_id, "owner", datetime.now(UTC), "admin"))
    repository.add_grant(Grant("bob", project_b.resource_id, "owner", datetime.now(UTC), "admin"))
    repository.add_grant(Grant("bob", source_b.resource_id, "reader", datetime.now(UTC), "admin"))
    service = AuthorizationService(repository)

    assert service.is_allowed(_principal("alice"), Action.READ, project_a)
    assert service.is_allowed(_principal("alice"), Action.READ, output_a)
    assert service.is_allowed(_principal("alice"), Action.READ, backup_a)
    assert not service.is_allowed(_principal("alice"), Action.READ, project_b)
    assert not service.is_allowed(_principal("alice"), Action.READ, source_b)
    assert service.is_allowed(_principal("bob"), Action.READ, project_b)
    assert service.is_allowed(_principal("bob"), Action.READ, source_b)
    assert not service.is_allowed(_principal("bob"), Action.READ, project_a)
    assert not service.is_allowed(_principal("bob"), Action.READ, output_a)
    assert not service.is_allowed(_principal("bob"), Action.READ, backup_a)
    repository.close()


@pytest.mark.asyncio
async def test_project_creation_removes_filesystem_project_when_owner_registration_fails(monkeypatch) -> None:
    project_service = MagicMock()
    project_service.create_project.return_value = MagicMock()
    project_service.assign_project_owner.side_effect = ValueError("Authorization resource already exists")
    monkeypatch.setattr(projects, "get_project_service", lambda: project_service)

    with pytest.raises(HTTPException) as error:
        await projects.create_project(ProjectCreateRequest(name="project-a"), _principal(), MagicMock())

    assert error.value.status_code == 500
    project_service.delete_project.assert_called_once_with("project-a")


@pytest.mark.asyncio
async def test_project_deletion_restores_authorization_when_filesystem_delete_fails(monkeypatch) -> None:
    project_service = MagicMock()
    project_service.delete_project.side_effect = RuntimeError("filesystem failure")
    monkeypatch.setattr(projects, "get_project_service", lambda: project_service)

    resource = ResourceRecord(uuid4(), ResourceType.PROJECT, "project-a")
    authorized_project = AuthorizedResource(_principal(), Action.DELETE, resource)
    authorization_service = MagicMock()

    with pytest.raises(HTTPException) as error:
        await projects.delete_project("project-a", authorized_project, authorization_service)

    assert error.value.status_code == 500
    authorization_service.transition_resource.assert_has_calls(
        [
            call(resource, "deleting"),
            call(resource, "active"),
        ]
    )
