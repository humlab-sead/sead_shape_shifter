"""Operational helpers for the authorization SQLite database."""

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from backend.app.authorization.models import Grant, GrantSubjectType, ResourceRecord, ResourceType
from backend.app.authorization.repository import SQLiteAuthorizationRepository


def integrity_check(path: Path) -> bool:
    """Return whether SQLite reports an intact authorization database."""
    try:
        with sqlite3.connect(path) as connection:
            result = connection.execute("PRAGMA integrity_check").fetchone()
    except sqlite3.DatabaseError:
        return False
    return bool(result and result[0] == "ok")


def backup_database(source: Path, destination: Path) -> None:
    """Create a consistent SQLite backup without copying a live file directly."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(source) as source_connection, sqlite3.connect(destination) as destination_connection:
        source_connection.backup(destination_connection)


def restore_database(source: Path, destination: Path) -> None:
    """Restore a SQLite backup into the configured authorization database."""
    if not integrity_check(source):
        raise ValueError("Authorization backup failed integrity check")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(source) as source_connection, sqlite3.connect(destination) as destination_connection:
        source_connection.backup(destination_connection)


def inspect_manifest(path: Path, *, allow_authenticated_everyone: bool = False) -> dict[str, int]:
    """Validate and summarize a migration manifest without changing the database."""
    manifest = _load_validated_manifest(path, allow_authenticated_everyone=allow_authenticated_everyone)
    resources = manifest["resources"]
    administrators = manifest["administrators"]
    return {"resources": len(resources), "administrators": len(set(administrators))}


def apply_manifest(
    path: Path,
    database: Path,
    actor_principal_id: str = "migration",
    *,
    allow_authenticated_everyone: bool = False,
) -> dict[str, int]:
    """Apply reviewed initial administrators, resources, and grants."""
    manifest = _load_validated_manifest(path, allow_authenticated_everyone=allow_authenticated_everyone)
    repository = SQLiteAuthorizationRepository(database)
    try:
        administrators_created = _apply_administrators(repository, manifest["administrators"], actor_principal_id)
        resources_by_locator = _apply_resources(repository, manifest["resources"])
        grants_created = _apply_grants(repository, manifest["resources"], resources_by_locator, actor_principal_id)
        return {
            "administrators": administrators_created,
            "resources": len(resources_by_locator),
            "grants": grants_created,
        }
    finally:
        repository.close()


def reconcile_manifest(path: Path, database: Path, *, allow_authenticated_everyone: bool = False) -> dict[str, int]:
    """Compare a reviewed migration manifest with authorization storage."""
    manifest = _load_validated_manifest(path, allow_authenticated_everyone=allow_authenticated_everyone)
    repository = SQLiteAuthorizationRepository(database)
    try:
        missing_administrators = sum(
            1 for principal_id in manifest["administrators"] if "admin" not in repository.list_application_roles(principal_id)
        )
        missing_resources = 0
        missing_grants = 0
        for resource in manifest["resources"]:
            resource_type = ResourceType(resource["resource_type"])
            record = repository.get_resource_by_locator(resource_type, resource["locator"].strip())
            if record is None:
                missing_resources += 1
                missing_grants += len(resource.get("grants", []))
                continue
            for grant in resource.get("grants", []):
                subject_type, subject_id = _manifest_subject(grant)
                if not repository.grant_exists(subject_type, subject_id, record.resource_id, grant["role"].strip()):
                    missing_grants += 1
        return {
            "missing_administrators": missing_administrators,
            "missing_resources": missing_resources,
            "missing_grants": missing_grants,
        }
    finally:
        repository.close()


def initialize_database(path: Path) -> None:
    """Create or migrate the authorization database schema."""
    repository = SQLiteAuthorizationRepository(path)
    repository.close()


def _load_manifest(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid authorization manifest: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("Authorization manifest must contain a JSON object")
    return value


def _load_validated_manifest(path: Path, *, allow_authenticated_everyone: bool = False) -> dict[str, Any]:
    manifest = _load_manifest(path)
    resources = manifest.get("resources", [])
    administrators = manifest.get("administrators", [])
    if not isinstance(resources, list) or not isinstance(administrators, list):
        raise ValueError("Manifest resources and administrators must be lists")
    normalized_administrators = _validate_administrators(administrators)
    for resource in resources:
        _validate_resource(resource, allow_authenticated_everyone=allow_authenticated_everyone)
    return {"administrators": normalized_administrators, "resources": resources}


def _validate_administrators(administrators: list[Any]) -> list[str]:
    normalized = []
    for principal_id in administrators:
        if not isinstance(principal_id, str) or not principal_id.strip():
            raise ValueError("Manifest administrators must be non-empty strings")
        normalized.append(principal_id.strip())
    return list(dict.fromkeys(normalized))


def _validate_resource(resource: Any, *, allow_authenticated_everyone: bool = False) -> None:
    if not isinstance(resource, dict) or not resource.get("resource_type") or not resource.get("locator"):
        raise ValueError("Each manifest resource needs resource_type and locator")
    if not isinstance(resource["resource_type"], str) or not isinstance(resource["locator"], str) or not resource["locator"].strip():
        raise ValueError("Each manifest resource needs resource_type and locator")
    try:
        ResourceType(resource["resource_type"])
    except ValueError as exc:
        raise ValueError(f"Unknown manifest resource_type: {resource['resource_type']}") from exc
    grants = resource.get("grants", [])
    if not isinstance(grants, list):
        raise ValueError("Manifest resource grants must be a list")
    for grant in grants:
        if not isinstance(grant, dict):
            raise ValueError("Each manifest grant must be an object")
        if "principal_id" in grant and (not isinstance(grant["principal_id"], str) or not grant["principal_id"].strip()):
            raise ValueError("Manifest principal_id must be a non-empty string")
        if "principal_id" not in grant and (not isinstance(grant.get("subject_id"), str) or not grant["subject_id"].strip()):
            raise ValueError("Each typed manifest grant needs a non-empty subject_id")
        try:
            subject_type, subject_id = _manifest_subject(grant)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc
        if subject_type == GrantSubjectType.EVERYONE and subject_id != "authenticated":
            raise ValueError("Everyone grants must use subject_id 'authenticated'")
        if subject_type == GrantSubjectType.EVERYONE and not allow_authenticated_everyone:
            raise ValueError("Authenticated everyone grants are disabled by deployment configuration")
        if not isinstance(grant.get("role"), str) or not grant["role"].strip():
            raise ValueError("Each manifest grant needs a non-empty role")


def _apply_administrators(
    repository: SQLiteAuthorizationRepository,
    administrators: list[str],
    actor_principal_id: str,
) -> int:
    created = 0
    for principal_id in administrators:
        if "admin" not in repository.list_application_roles(principal_id):
            repository.add_application_role(principal_id, "admin", actor_principal_id)
            created += 1
    return created


def _apply_resources(
    repository: SQLiteAuthorizationRepository,
    resources: list[dict[str, Any]],
) -> dict[tuple[ResourceType, str], ResourceRecord]:
    resources_by_locator: dict[tuple[ResourceType, str], ResourceRecord] = {}
    for resource in resources:
        resource_type = ResourceType(resource["resource_type"])
        locator = resource["locator"].strip()
        existing = repository.get_resource_by_locator(resource_type, locator)
        record = existing or ResourceRecord(uuid4(), resource_type, locator)
        if existing is None:
            repository.create_resource(record)
        resources_by_locator[(resource_type, locator)] = record
    return resources_by_locator


def _apply_grants(
    repository: SQLiteAuthorizationRepository,
    resources: list[dict[str, Any]],
    resources_by_locator: dict[tuple[ResourceType, str], ResourceRecord],
    actor_principal_id: str,
) -> int:
    created = 0
    created_at = datetime.now(UTC)
    for resource in resources:
        resource_type = ResourceType(resource["resource_type"])
        record = resources_by_locator[(resource_type, resource["locator"].strip())]
        for grant in resource.get("grants", []):
            subject_type, subject_id = _manifest_subject(grant)
            role = grant["role"].strip()
            if repository.grant_exists(subject_type, subject_id, record.resource_id, role):
                continue
            repository.add_grant(Grant(subject_id, record.resource_id, role, created_at, actor_principal_id, subject_type=subject_type))
            created += 1
    return created


def _manifest_subject(grant: dict[str, Any]) -> tuple[GrantSubjectType, str]:
    """Normalize legacy principal and typed manifest subject fields."""
    if "principal_id" in grant:
        if "subject_type" in grant and grant["subject_type"] != GrantSubjectType.PRINCIPAL.value:
            raise ValueError("principal_id grants must use subject_type 'principal'")
        return GrantSubjectType.PRINCIPAL, grant["principal_id"].strip()
    try:
        subject_type = GrantSubjectType(grant.get("subject_type"))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Unknown manifest subject_type: {grant.get('subject_type')}") from exc
    return subject_type, grant["subject_id"].strip()
