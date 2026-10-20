"""Tests for complete authorization state snapshots.

These cover the roundtrip that ``export-manifest`` does not provide: resource
UUIDs, project and shared-source children, inactive resource generations, every
deployment role, and optionally the audit history.
"""

import json
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from click.testing import CliRunner

from backend.app.authorization.models import (
    ApplicationRole,
    ApplicationRoleAssignment,
    AuditEvent,
    Grant,
    GrantSubjectType,
    ResourceRecord,
    ResourceType,
)
from backend.app.authorization.operations import export_state, import_state, inspect_state
from backend.app.authorization.repository import CURRENT_SCHEMA_VERSION, SQLiteAuthorizationRepository
from backend.app.scripts.authorization import cli


def _populate(database) -> dict[str, UUID]:
    """Store a state that exercises every record shape."""
    repository = SQLiteAuthorizationRepository(database)
    project = ResourceRecord(uuid4(), ResourceType.PROJECT, "project-a")
    child = ResourceRecord(uuid4(), ResourceType.PROJECT_CHILD, "project-a:site", parent_resource_id=project.resource_id)
    source = ResourceRecord(uuid4(), ResourceType.SHARED_DATA_SOURCE, "sead-options")
    retired = ResourceRecord(uuid4(), ResourceType.PROJECT, "retired-project", lifecycle_state="deleted")
    for resource in (project, child, source, retired):
        repository.create_resource(resource)

    created = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
    repository.add_application_role("alice", "project_maintainer", "bootstrap")
    repository.add_application_role("bob", "operator", "bootstrap")
    repository.add_grant(Grant("alice", project.resource_id, "owner", created, "bootstrap"))
    repository.add_grant(Grant("editors", project.resource_id, "viewer", created, "bootstrap", GrantSubjectType.GROUP))
    repository.add_grant(Grant("authenticated", source.resource_id, "reader", created, "bootstrap", GrantSubjectType.EVERYONE))
    repository.add_grant(Grant("bob", child.resource_id, "editor", created, "bootstrap"))
    repository.close()
    return {"project": project.resource_id, "child": child.resource_id, "source": source.resource_id, "retired": retired.resource_id}


def test_export_state_roundtrips_every_record_shape(tmp_path) -> None:
    source_database = tmp_path / "source.sqlite3"
    target_database = tmp_path / "target.sqlite3"
    _populate(source_database)

    snapshot = tmp_path / "state.yaml"
    counts = export_state(snapshot, source_database)
    assert counts == {"resources": 4, "grants": 4, "application_roles": 2, "audit_events": 0}

    import_state(snapshot, target_database, "restorer")

    reexported = tmp_path / "state-again.yaml"
    export_state(reexported, target_database)
    assert reexported.read_text(encoding="utf-8") == snapshot.read_text(encoding="utf-8")


def test_export_state_keeps_records_that_export_manifest_drops(tmp_path) -> None:
    database = tmp_path / "authorization.sqlite3"
    _populate(database)

    snapshot = tmp_path / "state.json"
    export_state(snapshot, database)
    text = snapshot.read_text(encoding="utf-8")

    assert "project-a:site" in text, "child resources are part of the state"
    assert "retired-project" in text, "inactive resource generations are part of the state"
    assert "project_maintainer" in text, "non-admin deployment roles are part of the state"
    assert "operator" in text


def test_export_state_is_sorted_and_uses_iso_timestamps(tmp_path) -> None:
    database = tmp_path / "authorization.sqlite3"
    _populate(database)
    snapshot = tmp_path / "state.json"

    export_state(snapshot, database)
    document = json.loads(snapshot.read_text(encoding="utf-8"))

    assert document["schema_version"] == CURRENT_SCHEMA_VERSION
    resource_keys = [(resource["resource_type"], resource["locator"], resource["resource_id"]) for resource in document["resources"]]
    assert resource_keys == sorted(resource_keys)
    grant_keys = [(grant["resource_id"], grant["subject_type"], grant["subject_id"], grant["role"]) for grant in document["grants"]]
    assert grant_keys == sorted(grant_keys)
    assert document["grants"][0]["created_at"].startswith("2026-01-02T03:04:05")


def test_import_state_replaces_existing_records(tmp_path) -> None:
    database = tmp_path / "authorization.sqlite3"
    _populate(database)
    snapshot = tmp_path / "state.yaml"
    export_state(snapshot, database)

    repository = SQLiteAuthorizationRepository(database)
    stale = ResourceRecord(uuid4(), ResourceType.PROJECT, "stale-project")
    repository.create_resource(stale)
    repository.add_grant(Grant("mallory", stale.resource_id, "owner", datetime.now(UTC), "test"))
    repository.close()

    import_state(snapshot, database, "restorer")

    repository = SQLiteAuthorizationRepository(database)
    try:
        assert repository.get_resource_by_locator(ResourceType.PROJECT, "stale-project") is None
        assert repository.list_grants("mallory") == []
        assert {grant.subject_id for grant in repository.list_all_grants()} == {"alice", "editors", "authenticated", "bob"}
    finally:
        repository.close()


def test_import_state_records_a_restore_audit_event(tmp_path) -> None:
    source_database = tmp_path / "source.sqlite3"
    target_database = tmp_path / "target.sqlite3"
    _populate(source_database)
    snapshot = tmp_path / "state.yaml"
    export_state(snapshot, source_database)

    import_state(snapshot, target_database, "restorer")

    repository = SQLiteAuthorizationRepository(target_database)
    try:
        restored = [event for event in repository.list_audit_events() if event.event_type == "state_restored"]
    finally:
        repository.close()
    assert len(restored) == 1
    assert restored[0].actor_principal_id == "restorer"
    assert json.loads(restored[0].details or "{}")["resources"] == 4


def test_export_state_omits_audit_events_by_default_and_keeps_history_on_restore(tmp_path) -> None:
    source_database = tmp_path / "source.sqlite3"
    target_database = tmp_path / "target.sqlite3"
    _populate(source_database)
    snapshot = tmp_path / "state.yaml"
    export_state(snapshot, source_database)
    assert "audit_events" not in snapshot.read_text(encoding="utf-8")

    repository = SQLiteAuthorizationRepository(target_database)
    existing = ResourceRecord(uuid4(), ResourceType.PROJECT, "target-only")
    repository.create_resource(existing)
    repository.close()

    import_state(snapshot, target_database, "restorer")

    repository = SQLiteAuthorizationRepository(target_database)
    try:
        event_types = [event.event_type for event in repository.list_audit_events()]
    finally:
        repository.close()
    # The target's own history survives, and the restore adds exactly one event.
    assert "resource_lifecycle_changed" not in event_types
    assert event_types[-1] == "state_restored"


def test_export_state_with_audit_events_restores_the_history(tmp_path) -> None:
    source_database = tmp_path / "source.sqlite3"
    target_database = tmp_path / "target.sqlite3"
    _populate(source_database)

    repository = SQLiteAuthorizationRepository(source_database)
    original_ids = {event.event_id for event in repository.list_audit_events()}
    repository.close()

    snapshot = tmp_path / "state.yaml"
    counts = export_state(snapshot, source_database, include_audit=True)
    assert counts["audit_events"] == len(original_ids)
    assert "audit_events" in snapshot.read_text(encoding="utf-8")

    import_state(snapshot, target_database, "restorer")

    repository = SQLiteAuthorizationRepository(target_database)
    try:
        restored_ids = {event.event_id for event in repository.list_audit_events()}
    finally:
        repository.close()
    assert original_ids <= restored_ids
    assert original_ids != restored_ids, "the restore itself is recorded"


def test_import_state_rejects_a_newer_schema_version(tmp_path) -> None:
    snapshot = tmp_path / "state.json"
    snapshot.write_text(
        json.dumps({"schema_version": CURRENT_SCHEMA_VERSION + 1, "resources": [], "grants": [], "application_roles": []}),
        encoding="utf-8",
    )
    database = tmp_path / "authorization.sqlite3"

    with pytest.raises(ValueError, match="newer than the supported version"):
        import_state(snapshot, database, "restorer")
    assert not database.exists()


def test_import_state_rejects_a_grant_for_an_unknown_resource(tmp_path) -> None:
    snapshot = tmp_path / "state.json"
    snapshot.write_text(
        json.dumps(
            {
                "schema_version": CURRENT_SCHEMA_VERSION,
                "resources": [],
                "grants": [
                    {
                        "subject_type": "principal",
                        "subject_id": "alice",
                        "resource_id": str(uuid4()),
                        "role": "owner",
                        "created_at": "2026-01-02T03:04:05+00:00",
                        "created_by": "test",
                    }
                ],
                "application_roles": [],
            }
        ),
        encoding="utf-8",
    )
    database = tmp_path / "authorization.sqlite3"

    with pytest.raises(ValueError, match="unknown resource"):
        import_state(snapshot, database, "restorer")


def test_import_state_rejects_broad_ownership_and_duplicate_records(tmp_path) -> None:
    resource_id = uuid4()
    base_resource = {
        "resource_id": str(resource_id),
        "resource_type": "project",
        "locator": "project-a",
        "lifecycle_state": "active",
        "parent_resource_id": None,
    }
    grant = {
        "subject_type": "group",
        "subject_id": "editors",
        "resource_id": str(resource_id),
        "role": "owner",
        "created_at": "2026-01-02T03:04:05+00:00",
        "created_by": "test",
    }
    snapshot = tmp_path / "state.json"
    snapshot.write_text(
        json.dumps(
            {
                "schema_version": CURRENT_SCHEMA_VERSION,
                "resources": [base_resource],
                "grants": [grant],
                "application_roles": [],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Only a principal may receive the owner role"):
        import_state(snapshot, tmp_path / "authorization.sqlite3", "restorer")

    snapshot.write_text(
        json.dumps(
            {
                "schema_version": CURRENT_SCHEMA_VERSION,
                "resources": [base_resource, base_resource],
                "grants": [],
                "application_roles": [],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Duplicate snapshot resource_id"):
        import_state(snapshot, tmp_path / "authorization-2.sqlite3", "restorer")


def test_import_state_leaves_existing_records_when_validation_fails(tmp_path) -> None:
    database = tmp_path / "authorization.sqlite3"
    _populate(database)

    broken = tmp_path / "broken.json"
    broken.write_text(json.dumps({"schema_version": CURRENT_SCHEMA_VERSION, "resources": "not-a-list"}), encoding="utf-8")

    with pytest.raises(ValueError, match="must be a list"):
        import_state(broken, database, "restorer")

    repository = SQLiteAuthorizationRepository(database)
    try:
        assert repository.get_resource_by_locator(ResourceType.PROJECT, "project-a") is not None
        assert len(repository.list_all_grants()) == 4
    finally:
        repository.close()


def test_inspect_state_reports_counts_without_writing(tmp_path) -> None:
    database = tmp_path / "authorization.sqlite3"
    _populate(database)
    snapshot = tmp_path / "state.yaml"
    export_state(snapshot, database)

    counts = inspect_state(snapshot)
    assert counts["resources"] == 4
    assert counts["grants"] == 4
    assert counts["application_roles"] == 2
    assert counts["audit_events_replaced"] is False


def test_export_state_command_writes_a_restorable_snapshot(tmp_path) -> None:
    source_database = tmp_path / "source.sqlite3"
    target_database = tmp_path / "target.sqlite3"
    _populate(source_database)
    snapshot = tmp_path / "state.yaml"
    runner = CliRunner()

    exported = runner.invoke(cli, ["export-state", str(snapshot), "--database", str(source_database)])
    assert exported.exit_code == 0, exported.output
    assert "4 resources, 4 grants, 2 application roles" in exported.output

    imported = runner.invoke(
        cli,
        ["import-state", str(snapshot), "--database", str(target_database), "--actor", "restorer", "--yes"],
    )
    assert imported.exit_code == 0, imported.output
    assert "Imported: 4 resources" in imported.output


def test_import_state_command_dry_run_does_not_create_the_database(tmp_path) -> None:
    source_database = tmp_path / "source.sqlite3"
    target_database = tmp_path / "target.sqlite3"
    _populate(source_database)
    snapshot = tmp_path / "state.yaml"
    export_state(snapshot, source_database)

    result = CliRunner().invoke(
        cli,
        ["import-state", str(snapshot), "--database", str(target_database), "--actor", "restorer", "--dry-run"],
    )

    assert result.exit_code == 0, result.output
    assert "would import 4 resources" in result.output
    assert not target_database.exists()


def test_import_state_command_requires_an_explicit_confirmation(tmp_path) -> None:
    source_database = tmp_path / "source.sqlite3"
    target_database = tmp_path / "target.sqlite3"
    _populate(source_database)
    snapshot = tmp_path / "state.yaml"
    export_state(snapshot, source_database)

    result = CliRunner().invoke(
        cli,
        ["import-state", str(snapshot), "--database", str(target_database), "--actor", "restorer"],
        input="n\n",
    )

    assert result.exit_code != 0
    assert not target_database.exists()
