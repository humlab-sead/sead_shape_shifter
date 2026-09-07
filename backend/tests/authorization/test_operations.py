"""Tests for authorization database operations."""

import json

import pytest
from click.testing import CliRunner

from backend.app.authorization.models import ResourceType
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
