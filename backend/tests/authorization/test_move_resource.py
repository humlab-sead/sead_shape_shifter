"""Tests for moving an authorization resource to a new locator."""

import json
from datetime import UTC, datetime
from uuid import uuid4

from click.testing import CliRunner

from backend.app.authorization.models import Grant, ResourceRecord, ResourceType
from backend.app.authorization.repository import SQLiteAuthorizationRepository
from backend.app.scripts.authorization import cli


def _project(repository: SQLiteAuthorizationRepository, locator: str, *, owner: str = "alice") -> ResourceRecord:
    resource = ResourceRecord(uuid4(), ResourceType.PROJECT, locator)
    repository.create_resource(resource)
    repository.add_grant(Grant(owner, resource.resource_id, "owner", datetime.now(UTC), owner))
    return resource


def test_update_resource_locator_keeps_uuid_and_grants_and_audits(tmp_path) -> None:
    repository = SQLiteAuthorizationRepository(tmp_path / "authorization.sqlite3")
    resource = _project(repository, "arbodat:old-name")

    repository.update_resource_locator(resource.resource_id, "arbodat:new-name", "operator")

    assert repository.get_resource_by_locator(ResourceType.PROJECT, "arbodat:old-name") is None
    moved = repository.get_resource_by_locator(ResourceType.PROJECT, "arbodat:new-name")
    assert moved is not None
    assert moved.resource_id == resource.resource_id
    grants = repository.list_grants("alice")
    assert len(grants) == 1
    assert grants[0].resource_id == resource.resource_id
    assert grants[0].role == "owner"

    event = repository.list_audit_events()[-1]
    assert event.event_type == "resource_locator_changed"
    assert event.actor_principal_id == "operator"
    assert event.resource_id == resource.resource_id
    assert json.loads(event.details or "{}") == {"from_locator": "arbodat:old-name", "to_locator": "arbodat:new-name"}
    repository.close()


def test_update_resource_locator_rejects_unknown_resource(tmp_path) -> None:
    repository = SQLiteAuthorizationRepository(tmp_path / "authorization.sqlite3")

    try:
        repository.update_resource_locator(uuid4(), "nowhere", "operator")
    except ValueError as error:
        assert "Resource not found" in str(error)
    else:
        raise AssertionError("Expected ValueError for an unknown resource")
    repository.close()


def test_move_resource_command_moves_locator_and_keeps_grants(tmp_path) -> None:
    database = tmp_path / "authorization.sqlite3"
    repository = SQLiteAuthorizationRepository(database)
    resource = _project(repository, "P")
    repository.close()

    result = CliRunner().invoke(
        cli,
        [
            "move-resource",
            "--database",
            str(database),
            "--resource-type",
            "project",
            "--from-locator",
            "P",
            "--to-locator",
            "arbodat:P",
            "--actor",
            "operator",
            "--yes",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "resource_id" in result.output
    verify = SQLiteAuthorizationRepository(database)
    assert verify.get_resource_by_locator(ResourceType.PROJECT, "P") is None
    moved = verify.get_resource_by_locator(ResourceType.PROJECT, "arbodat:P")
    assert moved is not None
    assert moved.resource_id == resource.resource_id
    assert verify.list_grants("alice")[0].resource_id == resource.resource_id
    verify.close()


def test_move_resource_dry_run_makes_no_change(tmp_path) -> None:
    database = tmp_path / "authorization.sqlite3"
    repository = SQLiteAuthorizationRepository(database)
    _project(repository, "P")
    repository.close()

    result = CliRunner().invoke(
        cli,
        [
            "move-resource",
            "--database",
            str(database),
            "--resource-type",
            "project",
            "--from-locator",
            "P",
            "--to-locator",
            "arbodat:P",
            "--actor",
            "operator",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Dry run" in result.output
    verify = SQLiteAuthorizationRepository(database)
    assert verify.get_resource_by_locator(ResourceType.PROJECT, "P") is not None
    verify.close()


def test_move_resource_rejects_missing_source_locator(tmp_path) -> None:
    database = tmp_path / "authorization.sqlite3"
    SQLiteAuthorizationRepository(database).close()

    result = CliRunner().invoke(
        cli,
        [
            "move-resource",
            "--database",
            str(database),
            "--resource-type",
            "project",
            "--from-locator",
            "missing",
            "--to-locator",
            "arbodat:missing",
            "--actor",
            "operator",
            "--yes",
        ],
    )

    assert result.exit_code != 0
    assert "Active resource not found" in result.output


def test_move_resource_rejects_occupied_target_locator(tmp_path) -> None:
    database = tmp_path / "authorization.sqlite3"
    repository = SQLiteAuthorizationRepository(database)
    _project(repository, "P")
    _project(repository, "arbodat:P", owner="bob")
    repository.close()

    result = CliRunner().invoke(
        cli,
        [
            "move-resource",
            "--database",
            str(database),
            "--resource-type",
            "project",
            "--from-locator",
            "P",
            "--to-locator",
            "arbodat:P",
            "--actor",
            "operator",
            "--yes",
        ],
    )

    assert result.exit_code != 0
    assert "already uses locator" in result.output


def test_move_resource_rejects_identical_locators(tmp_path) -> None:
    database = tmp_path / "authorization.sqlite3"
    SQLiteAuthorizationRepository(database).close()

    result = CliRunner().invoke(
        cli,
        [
            "move-resource",
            "--database",
            str(database),
            "--resource-type",
            "project",
            "--from-locator",
            "P",
            "--to-locator",
            "P",
            "--actor",
            "operator",
            "--yes",
        ],
    )

    assert result.exit_code != 0
    assert "must differ" in result.output
