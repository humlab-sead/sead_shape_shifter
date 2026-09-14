"""Tests for authorization database operations."""

import json
import sqlite3
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from click.testing import CliRunner

from backend.app.authorization.models import Grant, GrantSubjectType, ResourceRecord, ResourceType
from backend.app.authorization.operations import (
    apply_manifest,
    backup_database,
    initialize_database,
    inspect_manifest,
    integrity_check,
    reconcile_manifest,
    restore_database,
)
from backend.app.authorization.repository import SQLiteAuthorizationRepository
from backend.app.scripts.authorization import cli


def test_backup_restore_and_integrity_check(tmp_path) -> None:
    database = tmp_path / "authorization.sqlite3"
    backup = tmp_path / "backup.sqlite3"
    restored = tmp_path / "restored.sqlite3"
    initialize_database(database)

    backup_database(database, backup)
    restore_database(backup, restored)

    assert integrity_check(database)
    assert integrity_check(backup)
    assert integrity_check(restored)


def test_backup_and_restore_preserve_authorization_records(tmp_path) -> None:
    database = tmp_path / "authorization.sqlite3"
    backup = tmp_path / "backup.sqlite3"
    restored = tmp_path / "restored.sqlite3"
    repository = SQLiteAuthorizationRepository(database)
    resource = ResourceRecord(uuid4(), ResourceType.PROJECT, "project-a")
    repository.create_resource(resource)
    repository.add_grant(Grant("alice", resource.resource_id, "owner", datetime.now(UTC), "admin"))
    repository.close()

    backup_database(database, backup)
    restore_database(backup, restored)

    restored_repository = SQLiteAuthorizationRepository(restored)
    assert restored_repository.get_resource_by_locator(ResourceType.PROJECT, "project-a") == resource
    assert restored_repository.list_grants("alice")[0].resource_id == resource.resource_id
    restored_repository.close()


def test_initialize_database_is_idempotent_and_preserves_schema(tmp_path) -> None:
    database = tmp_path / "authorization.sqlite3"

    initialize_database(database)
    repository = SQLiteAuthorizationRepository(database)
    repository.add_application_role("alice", "admin", "bootstrap")
    repository.close()

    initialize_database(database)

    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] == 4
        assert connection.execute("SELECT role FROM application_role WHERE principal_id = 'alice'").fetchone()[0] == "admin"


def test_failed_grant_insert_rolls_back_without_audit_event(tmp_path) -> None:
    repository = SQLiteAuthorizationRepository(tmp_path / "authorization.sqlite3")
    resource = ResourceRecord(uuid4(), ResourceType.PROJECT, "project-a")
    grant = Grant("alice", resource.resource_id, "owner", datetime.now(UTC), "admin")
    repository.create_resource(resource)
    repository.add_grant(grant)

    with pytest.raises(sqlite3.IntegrityError):
        repository.add_grant(grant)

    assert repository.list_grants("alice") == [grant]
    assert len(repository.list_audit_events()) == 1
    repository.close()


def test_integrity_check_returns_false_for_invalid_sqlite_file(tmp_path) -> None:
    database = tmp_path / "corrupt.sqlite3"
    database.write_bytes(b"not a sqlite database")

    assert integrity_check(database) is False


def test_manifest_inspection_and_dry_run_do_not_create_database(tmp_path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({"administrators": ["alice", "alice"], "resources": [{"resource_type": "project", "locator": "project-a"}]}),
        encoding="utf-8",
    )
    database = tmp_path / "authorization.sqlite3"

    assert inspect_manifest(manifest) == {"resources": 1, "administrators": 1}
    result = CliRunner().invoke(cli, ["migrate", "--database", str(database), "--manifest", str(manifest), "--dry-run"])

    assert result.exit_code == 0
    assert not database.exists()


def test_migrate_manifest_applies_initial_admin_resources_and_grants(tmp_path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "administrators": ["alice"],
                "resources": [
                    {
                        "resource_type": "project",
                        "locator": "project-a",
                        "grants": [{"principal_id": "alice", "role": "owner"}],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    database = tmp_path / "authorization.sqlite3"

    result = CliRunner().invoke(cli, ["migrate", "--database", str(database), "--manifest", str(manifest)])

    assert result.exit_code == 0
    assert "Applied: 1 resources, 1 administrators, 1 grants" in result.output
    repository = SQLiteAuthorizationRepository(database)
    resource = repository.get_resource_by_locator(ResourceType.PROJECT, "project-a")
    assert resource is not None
    assert repository.list_application_roles("alice") == ["admin"]
    assert repository.list_grants("alice")[0].resource_id == resource.resource_id
    repository.close()


def test_apply_manifest_is_idempotent(tmp_path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "administrators": ["alice"],
                "resources": [
                    {
                        "resource_type": "project",
                        "locator": "project-a",
                        "grants": [{"principal_id": "alice", "role": "owner"}],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    database = tmp_path / "authorization.sqlite3"

    assert apply_manifest(manifest, database) == {"administrators": 1, "resources": 1, "grants": 1}
    assert apply_manifest(manifest, database) == {"administrators": 0, "resources": 1, "grants": 0}


def test_typed_manifest_applies_and_reconciles_broad_grants(tmp_path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "resources": [
                    {
                        "resource_type": "project",
                        "locator": "project-a",
                        "grants": [
                            {"subject_type": "group", "subject_id": "editors", "role": "editor"},
                            {"subject_type": "everyone", "subject_id": "authenticated", "role": "viewer"},
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    database = tmp_path / "authorization.sqlite3"

    assert apply_manifest(manifest, database, allow_authenticated_everyone=True)["grants"] == 2
    assert reconcile_manifest(manifest, database, allow_authenticated_everyone=True)["missing_grants"] == 0
    repository = SQLiteAuthorizationRepository(database)
    assert {grant.subject_type for grant in repository.list_matching_grants("alice", ["editors"])} == {
        GrantSubjectType.GROUP,
        GrantSubjectType.EVERYONE,
    }
    repository.close()


def test_everyone_manifest_is_rejected_when_disabled(tmp_path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "resources": [
                    {
                        "resource_type": "project",
                        "locator": "project-a",
                        "grants": [{"subject_type": "everyone", "subject_id": "authenticated", "role": "viewer"}],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="disabled by deployment configuration"):
        inspect_manifest(manifest)


def test_typed_grant_cli_supports_dry_run_and_revoke(tmp_path) -> None:
    database = tmp_path / "authorization.sqlite3"
    repository = SQLiteAuthorizationRepository(database)
    resource = ResourceRecord(uuid4(), ResourceType.PROJECT, "project-a")
    repository.create_resource(resource)
    repository.close()

    runner = CliRunner()
    dry_run = runner.invoke(
        cli,
        [
            "grant",
            "--database",
            str(database),
            "--resource-type",
            "project",
            "--locator",
            "project-a",
            "--subject-type",
            "group",
            "--subject-id",
            "editors",
            "--role",
            "editor",
            "--actor",
            "admin",
            "--dry-run",
        ],
    )
    assert dry_run.exit_code == 0

    applied = runner.invoke(
        cli,
        [
            "grant",
            "--database",
            str(database),
            "--resource-type",
            "project",
            "--locator",
            "project-a",
            "--subject-type",
            "group",
            "--subject-id",
            "editors",
            "--role",
            "editor",
            "--actor",
            "admin",
        ],
    )
    assert applied.exit_code == 0
    revoked = runner.invoke(
        cli,
        [
            "revoke",
            "--database",
            str(database),
            "--resource-type",
            "project",
            "--locator",
            "project-a",
            "--subject-type",
            "group",
            "--subject-id",
            "editors",
            "--role",
            "editor",
            "--actor",
            "admin",
            "--yes",
        ],
    )
    assert revoked.exit_code == 0


def test_authorization_inventory_and_application_role_cli(tmp_path) -> None:
    database = tmp_path / "authorization.sqlite3"
    repository = SQLiteAuthorizationRepository(database)
    resource = ResourceRecord(uuid4(), ResourceType.PROJECT, "project-a")
    repository.create_resource(resource)
    repository.add_application_role("alice", "admin", "bootstrap")
    repository.close()

    runner = CliRunner()
    resources = runner.invoke(cli, ["list-resources", "--database", str(database), "--json"])
    roles = runner.invoke(cli, ["list-application-roles", "--database", str(database), "--json"])
    events = runner.invoke(cli, ["list-audit-events", "--database", str(database), "--json"])

    assert resources.exit_code == 0
    assert json.loads(resources.output)[0]["locator"] == "project-a"
    assert roles.exit_code == 0
    assert json.loads(roles.output)[0]["role"] == "admin"
    assert events.exit_code == 0
    assert json.loads(events.output)[0]["actor_principal_id"] == "bootstrap"

    dry_run = runner.invoke(
        cli,
        [
            "grant-application-role",
            "--database",
            str(database),
            "--principal-id",
            "bob",
            "--role",
            "operator",
            "--actor",
            "alice",
            "--dry-run",
        ],
    )
    assert dry_run.exit_code == 0
    check_repository = SQLiteAuthorizationRepository(database)
    assert check_repository.list_application_roles("bob") == []
    check_repository.close()

    granted = runner.invoke(
        cli,
        [
            "grant-application-role",
            "--database",
            str(database),
            "--principal-id",
            "bob",
            "--role",
            "operator",
            "--actor",
            "alice",
        ],
    )
    assert granted.exit_code == 0

    revoked = runner.invoke(
        cli,
        [
            "revoke-application-role",
            "--database",
            str(database),
            "--principal-id",
            "bob",
            "--role",
            "operator",
            "--actor",
            "alice",
            "--yes",
        ],
    )
    assert revoked.exit_code == 0

    final_admin = runner.invoke(
        cli,
        [
            "revoke-application-role",
            "--database",
            str(database),
            "--principal-id",
            "alice",
            "--role",
            "admin",
            "--actor",
            "alice",
            "--yes",
        ],
    )
    assert final_admin.exit_code != 0
    assert "final application administrator" in final_admin.output


def test_reconcile_manifest_reports_missing_and_clean_records(tmp_path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "administrators": ["alice"],
                "resources": [
                    {
                        "resource_type": "project",
                        "locator": "project-a",
                        "grants": [{"principal_id": "alice", "role": "owner"}],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    database = tmp_path / "authorization.sqlite3"

    assert reconcile_manifest(manifest, database) == {
        "missing_administrators": 1,
        "missing_resources": 1,
        "missing_grants": 1,
    }
    apply_manifest(manifest, database)
    assert reconcile_manifest(manifest, database) == {
        "missing_administrators": 0,
        "missing_resources": 0,
        "missing_grants": 0,
    }


def test_reconcile_command_fails_when_manifest_records_are_missing(tmp_path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"administrators": ["alice"], "resources": []}), encoding="utf-8")
    database = tmp_path / "authorization.sqlite3"
    initialize_database(database)

    result = CliRunner().invoke(cli, ["reconcile", str(manifest), "--database", str(database)])

    assert result.exit_code != 0
    assert "Missing: 0 resources, 1 administrators, 0 grants" in result.output


def test_manifest_rejects_missing_resource_locator(tmp_path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"resources": [{"resource_type": "project"}]}), encoding="utf-8")

    with pytest.raises(ValueError, match="resource_type and locator"):
        inspect_manifest(manifest)
