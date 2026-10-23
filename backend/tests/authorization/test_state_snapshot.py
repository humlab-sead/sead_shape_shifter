"""Tests for complete authorization state snapshots.

These cover the roundtrip that ``export-manifest`` does not provide: resource
UUIDs, project and shared-source children, inactive resource generations, every
deployment role, and optionally the audit history.
"""

import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
import yaml
from click.testing import CliRunner

from backend.app.authorization.models import (
    Grant,
    GrantSubjectType,
    ResourceRecord,
    ResourceType,
)
from backend.app.authorization.operations import export_state, import_state, inspect_state, plan_state_import
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
    repository.add_application_role("carol", "admin", "bootstrap")
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
    assert counts == {"resources": 4, "grants": 4, "application_roles": 3, "audit_events": 0}

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


def test_import_state_rejects_unknown_role_before_writing(tmp_path) -> None:
    database = tmp_path / "authorization.sqlite3"
    _populate(database)
    snapshot = tmp_path / "state.json"
    export_state(snapshot, database)
    document = json.loads(snapshot.read_text(encoding="utf-8"))
    document["grants"][0]["role"] = "viewr"
    snapshot.write_text(json.dumps(document), encoding="utf-8")

    result = CliRunner().invoke(
        cli,
        ["import-state", str(snapshot), "--database", str(database), "--actor", "restorer", "--dry-run"],
    )

    assert result.exit_code != 0
    assert "Snapshot grant" in result.output
    assert "Invalid role 'viewr'" in result.output
    assert "allowed roles:" in result.output
    repository = SQLiteAuthorizationRepository(database)
    try:
        assert len(repository.list_all_grants()) == 4
    finally:
        repository.close()


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
    assert counts["application_roles"] == 3
    assert counts["audit_events_replaced"] is False


def test_export_state_command_writes_a_restorable_snapshot(tmp_path) -> None:
    source_database = tmp_path / "source.sqlite3"
    target_database = tmp_path / "target.sqlite3"
    _populate(source_database)
    snapshot = tmp_path / "state.yaml"
    runner = CliRunner()

    exported = runner.invoke(cli, ["export-state", str(snapshot), "--database", str(source_database)])
    assert exported.exit_code == 0, exported.output
    assert "4 resources, 4 grants, 3 application roles" in exported.output

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
    # The target database is empty, so every snapshot record is an addition.
    assert "11 record change(s)" in result.output
    assert "+ resource" in result.output
    assert "+ grant" in result.output
    assert "+ application_role" in result.output
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


# --- Record-level diff and destructive-change guards -----------------------


def test_plan_state_import_reports_no_changes_for_an_unchanged_snapshot(tmp_path) -> None:
    database = tmp_path / "authorization.sqlite3"
    _populate(database)
    snapshot = tmp_path / "state.yaml"
    export_state(snapshot, database)

    plan = plan_state_import(snapshot, database)

    assert plan.changes == ()
    assert not plan.is_destructive
    assert plan.administrators == ("carol",)


def test_plan_state_import_lists_added_removed_and_changed_grants(tmp_path) -> None:
    database = tmp_path / "authorization.sqlite3"
    _populate(database)
    snapshot = tmp_path / "state.yaml"
    export_state(snapshot, database)

    document = yaml.safe_load(snapshot.read_text(encoding="utf-8"))
    alice_grant = next(grant for grant in document["grants"] if grant["subject_id"] == "alice")
    alice_grant["role"] = "editor"
    document["grants"] = [grant for grant in document["grants"] if grant["subject_id"] != "editors"]
    snapshot.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")

    changes = plan_state_import(snapshot, database).changes
    rendered = [(change.action, change.record_type, change.detail) for change in changes]

    assert ("remove", "grant", "principal:alice owner on project:project-a") in rendered
    assert ("add", "grant", "principal:alice editor on project:project-a") in rendered
    assert ("remove", "grant", "group:editors viewer on project:project-a") in rendered
    assert all(change.record_type == "grant" for change in changes)


def test_plan_state_import_lists_resource_additions_and_removals(tmp_path) -> None:
    database = tmp_path / "authorization.sqlite3"
    _populate(database)
    snapshot = tmp_path / "state.yaml"
    export_state(snapshot, database)

    document = yaml.safe_load(snapshot.read_text(encoding="utf-8"))
    removed = next(resource for resource in document["resources"] if resource["locator"] == "sead-options")
    document["resources"] = [resource for resource in document["resources"] if resource["locator"] != "sead-options"]
    document["grants"] = [grant for grant in document["grants"] if grant["resource_id"] != removed["resource_id"]]
    document["resources"].append(
        {
            "resource_id": str(uuid4()),
            "resource_type": "project",
            "locator": "new-project",
            "lifecycle_state": "active",
            "parent_resource_id": None,
        }
    )
    snapshot.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")

    rendered = {(change.action, change.record_type) for change in plan_state_import(snapshot, database).changes}
    assert ("add", "resource") in rendered
    assert ("remove", "resource") in rendered


def test_import_state_refuses_a_snapshot_without_an_administrator(tmp_path) -> None:
    database = tmp_path / "authorization.sqlite3"
    _populate(database)
    snapshot = tmp_path / "state.yaml"
    export_state(snapshot, database)
    _rewrite(snapshot, lambda document: document.update({"application_roles": []}))

    with pytest.raises(ValueError, match="without an administrator"):
        import_state(snapshot, database, "restorer")

    repository = SQLiteAuthorizationRepository(database)
    try:
        assert repository.list_application_roles("carol") == ["admin"]
    finally:
        repository.close()


def test_import_state_refuses_a_snapshot_that_leaves_a_project_unowned(tmp_path) -> None:
    database = tmp_path / "authorization.sqlite3"
    _populate(database)
    snapshot = tmp_path / "state.yaml"
    export_state(snapshot, database)
    _rewrite(snapshot, lambda document: document.update({"grants": [grant for grant in document["grants"] if grant["role"] != "owner"]}))

    with pytest.raises(ValueError, match="without an owner"):
        import_state(snapshot, database, "restorer")

    repository = SQLiteAuthorizationRepository(database)
    try:
        assert [grant.role for grant in repository.list_grants("alice")] == ["owner"]
    finally:
        repository.close()


def test_import_state_accepts_destructive_snapshots_when_allowed(tmp_path) -> None:
    database = tmp_path / "authorization.sqlite3"
    _populate(database)
    snapshot = tmp_path / "state.yaml"
    export_state(snapshot, database)
    _rewrite(
        snapshot,
        lambda document: document.update(
            {
                "application_roles": [],
                "grants": [grant for grant in document["grants"] if grant["role"] != "owner"],
            }
        ),
    )

    counts = import_state(
        snapshot,
        database,
        "restorer",
        allow_no_admin=True,
        allow_unowned_project=True,
    )

    assert counts["application_roles"] == 0
    repository = SQLiteAuthorizationRepository(database)
    try:
        assert repository.list_all_application_roles() == []
    finally:
        repository.close()


def test_import_state_ignores_inactive_projects_when_checking_ownership(tmp_path) -> None:
    """A deleted project keeps its resource record but needs no owner."""
    database = tmp_path / "authorization.sqlite3"
    _populate(database)
    snapshot = tmp_path / "state.yaml"
    export_state(snapshot, database)

    # _populate stores retired-project with no grant; the import must still pass.
    counts = import_state(snapshot, database, "restorer")

    assert counts["resources"] == 4


def test_import_state_command_prints_a_record_level_diff_on_dry_run(tmp_path) -> None:
    database = tmp_path / "authorization.sqlite3"
    _populate(database)
    snapshot = tmp_path / "state.yaml"
    export_state(snapshot, database)
    _rewrite(
        snapshot,
        lambda document: document.update(
            {
                # Drop the group grant and add a viewer grant, keeping the owner.
                "grants": [grant for grant in document["grants"] if grant["subject_id"] != "editors"]
                + [
                    {
                        "subject_type": "principal",
                        "subject_id": "dave",
                        "resource_id": document["resources"][0]["resource_id"],
                        "role": "viewer",
                        "created_at": "2026-01-02T03:04:05+00:00",
                        "created_by": "restorer",
                    }
                ]
            }
        ),
    )

    result = CliRunner().invoke(
        cli,
        ["import-state", str(snapshot), "--database", str(database), "--actor", "restorer", "--dry-run"],
    )

    assert result.exit_code == 0, result.output
    assert "2 record change(s)" in result.output
    assert "- grant            group:editors viewer on project:project-a" in result.output
    assert "+ grant            principal:dave viewer on project:project-a" in result.output
    assert "Administrators after import: carol" in result.output
    assert "nothing written" in result.output


def test_import_state_command_dry_run_reports_no_changes(tmp_path) -> None:
    database = tmp_path / "authorization.sqlite3"
    _populate(database)
    snapshot = tmp_path / "state.yaml"
    export_state(snapshot, database)

    result = CliRunner().invoke(
        cli,
        ["import-state", str(snapshot), "--database", str(database), "--actor", "restorer", "--dry-run"],
    )

    assert result.exit_code == 0, result.output
    assert "no record would change" in result.output


def test_import_state_command_refuses_a_destructive_plan_without_opt_in(tmp_path) -> None:
    database = tmp_path / "authorization.sqlite3"
    _populate(database)
    snapshot = tmp_path / "state.yaml"
    export_state(snapshot, database)
    _rewrite(snapshot, lambda document: document.update({"application_roles": []}))

    dry_run = CliRunner().invoke(
        cli,
        ["import-state", str(snapshot), "--database", str(database), "--actor", "restorer", "--dry-run"],
    )
    assert dry_run.exit_code != 0
    assert "--allow-no-admin" in dry_run.output

    applied = CliRunner().invoke(
        cli,
        ["import-state", str(snapshot), "--database", str(database), "--actor", "restorer", "--yes"],
    )
    assert applied.exit_code != 0
    assert "--allow-no-admin" in applied.output

    repository = SQLiteAuthorizationRepository(database)
    try:
        assert repository.list_application_roles("carol") == ["admin"]
    finally:
        repository.close()


def test_import_state_command_allows_a_destructive_plan_with_opt_in(tmp_path) -> None:
    database = tmp_path / "authorization.sqlite3"
    _populate(database)
    snapshot = tmp_path / "state.yaml"
    export_state(snapshot, database)
    _rewrite(snapshot, lambda document: document.update({"application_roles": []}))

    result = CliRunner().invoke(
        cli,
        [
            "import-state",
            str(snapshot),
            "--database",
            str(database),
            "--actor",
            "restorer",
            "--yes",
            "--allow-no-admin",
        ],
    )

    assert result.exit_code == 0, result.output
    repository = SQLiteAuthorizationRepository(database)
    try:
        assert repository.list_all_application_roles() == []
    finally:
        repository.close()


def _rewrite(snapshot, mutate) -> None:
    """Apply one change to snapshot document and write it back as YAML."""
    document = yaml.safe_load(snapshot.read_text(encoding="utf-8"))
    mutate(document)
    snapshot.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
