"""Tests for protected authorization mutations and audit records."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from backend.app.authorization.models import Grant, GrantSubjectType, ResourceRecord, ResourceType
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
    assert events[-1].subject_type == GrantSubjectType.PRINCIPAL
    assert events[-1].subject_id == "alice"
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
    assert repository.list_grants("alice")[0].role == "owner"
    assert repository.list_application_roles("alice") == ["admin"]
    repository.close()


def test_broad_subject_cannot_receive_owner_role(tmp_path) -> None:
    repository = SQLiteAuthorizationRepository(tmp_path / "authorization.sqlite3")
    resource = ResourceRecord(uuid4(), ResourceType.PROJECT, "project-a")
    repository.create_resource(resource)

    with pytest.raises(ValueError, match="Only a principal"):
        repository.add_grant(Grant("editors", resource.resource_id, "owner", datetime.now(UTC), "admin", GrantSubjectType.GROUP))

    repository.close()


def test_broad_subject_can_be_revoked(tmp_path) -> None:
    repository = SQLiteAuthorizationRepository(tmp_path / "authorization.sqlite3")
    resource = ResourceRecord(uuid4(), ResourceType.PROJECT, "project-a")
    repository.create_resource(resource)
    repository.add_grant(Grant("editors", resource.resource_id, "editor", datetime.now(UTC), "admin", GrantSubjectType.GROUP))

    assert repository.list_audit_events()[-1].subject_type == GrantSubjectType.GROUP
    assert repository.list_audit_events()[-1].subject_id == "editors"

    repository.remove_grant("editors", resource.resource_id, "editor", "admin", GrantSubjectType.GROUP)

    assert repository.list_audit_events()[-1].subject_type == GrantSubjectType.GROUP
    assert repository.list_audit_events()[-1].subject_id == "editors"

    assert repository.list_all_grants() == []
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
    assert repository.list_application_roles("bob") == ["admin"]
    assert repository.list_application_roles("charlie") == []
    assert len(repository.list_audit_events()) == 2
    repository.close()


def test_concurrent_repository_connections_preserve_independent_grants(tmp_path) -> None:
    database = tmp_path / "authorization.sqlite3"
    repository = SQLiteAuthorizationRepository(database)
    resource = ResourceRecord(uuid4(), ResourceType.PROJECT, "project-a")
    repository.create_resource(resource)
    repository.close()

    def add_viewer(principal_id: str) -> None:
        connection = SQLiteAuthorizationRepository(database)
        try:
            assert connection.get_resource_by_locator(ResourceType.PROJECT, "project-a") == resource
            connection.add_grant(_grant(principal_id, resource.resource_id, "viewer"))
        finally:
            connection.close()

    principal_ids = [f"user-{index}" for index in range(8)]
    with ThreadPoolExecutor(max_workers=len(principal_ids)) as executor:
        list(executor.map(add_viewer, principal_ids))

    repository = SQLiteAuthorizationRepository(database)
    assert {grant.principal_id for principal_id in principal_ids for grant in repository.list_grants(principal_id)} == set(principal_ids)
    repository.close()
