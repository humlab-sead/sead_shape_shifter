"""Tests for protected authorization mutations and audit records."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from backend.app.authorization.models import Grant, ResourceRecord, ResourceType
from backend.app.authorization.repository import SQLiteAuthorizationRepository


def _grant(principal_id: str, resource_id, role: str, created_by: str = "admin") -> Grant:
    return Grant(principal_id, resource_id, role, datetime.now(UTC), created_by)


def test_grant_mutation_writes_audit_event_atomically(tmp_path) -> None:
    repository = SQLiteAuthorizationRepository(tmp_path / "authorization.sqlite3")
    resource = ResourceRecord(uuid4(), ResourceType.PROJECT, "project-a")
    repository.create_resource(resource)
    repository.add_grant(_grant("alice", resource.resource_id, "owner"))

    events = repository.list_audit_events()

    assert events[-1].event_type == "grant_created"
    assert events[-1].resource_id == resource.resource_id
    repository.close()


def test_final_owner_and_admin_are_protected(tmp_path) -> None:
    repository = SQLiteAuthorizationRepository(tmp_path / "authorization.sqlite3")
    resource = ResourceRecord(uuid4(), ResourceType.PROJECT, "project-a")
    repository.create_resource(resource)
    repository.add_grant(_grant("alice", resource.resource_id, "owner"))
    repository.add_application_role("alice", "admin", "bootstrap")

    with pytest.raises(ValueError, match="final project owner"):
        repository.remove_grant("alice", resource.resource_id, "owner", "alice")
    with pytest.raises(ValueError, match="final application administrator"):
        repository.remove_application_role("alice", "admin", "alice")
    assert len(repository.list_audit_events()) == 2
    repository.close()


def test_multiple_owners_and_administrators_can_be_revoked(tmp_path) -> None:
    repository = SQLiteAuthorizationRepository(tmp_path / "authorization.sqlite3")
    resource = ResourceRecord(uuid4(), ResourceType.PROJECT, "project-a")
    repository.create_resource(resource)
    repository.add_grant(_grant("alice", resource.resource_id, "owner"))
    repository.add_grant(_grant("bob", resource.resource_id, "owner"))
    repository.add_application_role("alice", "admin", "bootstrap")
    repository.add_application_role("bob", "admin", "bootstrap")

    repository.remove_grant("alice", resource.resource_id, "owner", "bob")
    repository.remove_application_role("alice", "admin", "bob")

    assert repository.list_audit_events()[-1].event_type == "application_role_revoked"
    repository.close()


def test_bootstrap_admins_is_idempotent_and_records_events(tmp_path) -> None:
    repository = SQLiteAuthorizationRepository(tmp_path / "authorization.sqlite3")

    assert repository.bootstrap_admins([" alice ", "bob", "alice"]) is True
    assert repository.bootstrap_admins(["charlie"]) is False
    assert repository.list_application_roles("alice") == ["admin"]
    assert repository.list_application_roles("charlie") == []
    assert len(repository.list_audit_events()) == 2
    repository.close()
