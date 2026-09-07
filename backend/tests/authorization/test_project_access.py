"""Tests for project authorization integration helpers."""

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import yaml

from backend.app.authorization.models import Grant, Principal, ResourceRecord, ResourceType
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
