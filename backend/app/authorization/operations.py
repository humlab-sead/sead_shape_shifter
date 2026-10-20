"""Operational helpers for the authorization SQLite database."""

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from backend.app.authorization.models import (
    ApplicationRole,
    ApplicationRoleAssignment,
    AuditEvent,
    AuthorizationState,
    Grant,
    GrantSubjectType,
    ResourceRecord,
    ResourceType,
)
from backend.app.authorization.repository import CURRENT_SCHEMA_VERSION, SQLiteAuthorizationRepository


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


def export_manifest(path: Path, database: Path) -> dict[str, int]:
    """Export active top-level authorization resources and grants as a manifest."""
    repository = SQLiteAuthorizationRepository(database)
    try:
        administrators = sorted(
            {assignment.principal_id for assignment in repository.list_all_application_roles() if assignment.role == ApplicationRole.ADMIN}
        )
        grants_by_resource = {}
        for grant in repository.list_all_grants():
            grants_by_resource.setdefault(grant.resource_id, []).append(grant)

        resources = []
        for resource in repository.list_resources():
            if resource.lifecycle_state != "active" or resource.resource_type not in {
                ResourceType.PROJECT,
                ResourceType.SHARED_DATA_SOURCE,
            }:
                continue
            grants = sorted(
                grants_by_resource.get(resource.resource_id, []),
                key=lambda grant: (grant.subject_type.value, grant.subject_id, grant.role),
            )
            resources.append(
                {
                    "resource_type": resource.resource_type.value,
                    "locator": resource.locator,
                    "grants": [
                        {
                            "subject_type": grant.subject_type.value,
                            "subject_id": grant.subject_id,
                            "role": grant.role,
                        }
                        for grant in grants
                    ],
                }
            )
    finally:
        repository.close()

    manifest = {"administrators": administrators, "resources": resources}
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        if path.suffix.lower() in {".yaml", ".yml"}:
            yaml = YAML()
            yaml.default_flow_style = False
            with path.open("w", encoding="utf-8") as output:
                yaml.dump(manifest, output)
        else:
            path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    except (OSError, YAMLError) as exc:
        raise ValueError(f"Unable to write authorization manifest: {exc}") from exc
    return {"resources": len(resources), "administrators": len(administrators), "grants": sum(len(r["grants"]) for r in resources)}


def export_state(path: Path, database: Path, *, include_audit: bool = False) -> dict[str, int]:
    """Write the complete stored authorization state to a JSON or YAML snapshot.

    The snapshot keeps resource UUIDs, inactive resource generations, every
    deployment role, and each record's ``created_at`` and ``created_by``, so
    ``import_state`` can recreate the same records. Resources, grants, and roles
    are sorted and timestamps are written as ISO strings, so a committed
    snapshot changes only when a record changes.

    Audit events are left out unless ``include_audit`` is true, because they
    change on every authorization operation and would dominate a diff. A restore
    from a snapshot without them keeps the existing audit history.
    """
    repository = SQLiteAuthorizationRepository(database)
    try:
        state = AuthorizationState(
            schema_version=repository.schema_version(),
            resources=tuple(sorted(repository.list_resources(), key=_resource_order)),
            grants=tuple(sorted(repository.list_all_grants(), key=_grant_order)),
            application_roles=tuple(sorted(repository.list_all_application_roles(), key=_application_role_order)),
            audit_events=(tuple(sorted(repository.list_audit_events(), key=_audit_event_order)) if include_audit else None),
        )
    finally:
        repository.close()

    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        _write_document(path, _state_to_document(state))
    except (OSError, YAMLError) as exc:
        raise ValueError(f"Unable to write authorization snapshot: {exc}") from exc
    return _state_counts(state)


def inspect_state(path: Path) -> dict[str, Any]:
    """Validate a snapshot and report what a restore would write."""
    state = _load_state(path)
    counts: dict[str, Any] = _state_counts(state)
    counts["audit_events_replaced"] = state.audit_events is not None
    return counts


def import_state(snapshot: Path, database: Path, actor_principal_id: str) -> dict[str, int]:
    """Replace stored authorization records with a validated snapshot.

    The snapshot is validated before anything is written, and the replacement
    runs in one transaction, so a rejected or failed restore leaves the previous
    records in place.
    """
    if not actor_principal_id.strip():
        raise ValueError("An actor principal ID is required")
    state = _load_state(snapshot)
    repository = SQLiteAuthorizationRepository(database)
    try:
        repository.replace_state(state, actor_principal_id.strip())
    finally:
        repository.close()
    return _state_counts(state)


def _state_counts(state: AuthorizationState) -> dict[str, int]:
    return {
        "resources": len(state.resources),
        "grants": len(state.grants),
        "application_roles": len(state.application_roles),
        "audit_events": len(state.audit_events or ()),
    }


def _resource_order(resource: ResourceRecord) -> tuple[str, str, str]:
    return resource.resource_type.value, resource.locator, str(resource.resource_id)


def _grant_order(grant: Grant) -> tuple[str, str, str, str]:
    return str(grant.resource_id), grant.subject_type.value, grant.subject_id, grant.role


def _application_role_order(assignment: ApplicationRoleAssignment) -> tuple[str, str]:
    return assignment.principal_id, assignment.role.value


def _audit_event_order(event: AuditEvent) -> tuple[str, str]:
    return event.occurred_at.isoformat(), str(event.event_id)


def _state_to_document(state: AuthorizationState) -> dict[str, Any]:
    document: dict[str, Any] = {
        "schema_version": state.schema_version,
        "resources": [
            {
                "resource_id": str(resource.resource_id),
                "resource_type": resource.resource_type.value,
                "locator": resource.locator,
                "lifecycle_state": resource.lifecycle_state,
                "parent_resource_id": str(resource.parent_resource_id) if resource.parent_resource_id else None,
            }
            for resource in state.resources
        ],
        "grants": [
            {
                "subject_type": grant.subject_type.value,
                "subject_id": grant.subject_id,
                "resource_id": str(grant.resource_id),
                "role": grant.role,
                "created_at": grant.created_at.isoformat(),
                "created_by": grant.created_by,
            }
            for grant in state.grants
        ],
        "application_roles": [
            {
                "principal_id": assignment.principal_id,
                "role": assignment.role.value,
                "created_at": assignment.created_at.isoformat(),
                "created_by": assignment.created_by,
            }
            for assignment in state.application_roles
        ],
    }
    if state.audit_events is not None:
        document["audit_events"] = [
            {
                "event_id": str(event.event_id),
                "occurred_at": event.occurred_at.isoformat(),
                "actor_principal_id": event.actor_principal_id,
                "event_type": event.event_type,
                "resource_id": str(event.resource_id) if event.resource_id else None,
                "action": event.action,
                "outcome": event.outcome,
                "correlation_id": event.correlation_id,
                "subject_type": event.subject_type.value if event.subject_type else None,
                "subject_id": event.subject_id,
                "provider": event.provider,
                "details": event.details,
            }
            for event in state.audit_events
        ]
    return document


def _write_document(path: Path, document: dict[str, Any]) -> None:
    if path.suffix.lower() in {".yaml", ".yml"}:
        yaml = YAML()
        yaml.default_flow_style = False
        with path.open("w", encoding="utf-8") as output:
            yaml.dump(document, output)
    else:
        path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


def _load_state(path: Path) -> AuthorizationState:
    """Read a snapshot and check that it can be restored as a whole."""
    document = _load_document(path, label="authorization snapshot")
    schema_version = document.get("schema_version")
    if not isinstance(schema_version, int) or schema_version <= 0:
        raise ValueError("Authorization snapshot needs a positive integer schema_version")
    if schema_version > CURRENT_SCHEMA_VERSION:
        raise ValueError(
            f"Authorization snapshot schema version {schema_version} is newer than the supported version "
            f"{CURRENT_SCHEMA_VERSION}; upgrade the application before restoring it"
        )
    resources = _snapshot_resources(document.get("resources", []))
    grants = _snapshot_grants(document.get("grants", []), {resource.resource_id for resource in resources})
    application_roles = _snapshot_application_roles(document.get("application_roles", []))
    audit_events = _snapshot_audit_events(document["audit_events"]) if "audit_events" in document else None
    return AuthorizationState(schema_version, resources, grants, application_roles, audit_events)


def _snapshot_resources(items: Any) -> tuple[ResourceRecord, ...]:
    if not isinstance(items, list):
        raise ValueError("Snapshot resources must be a list")
    resources: list[ResourceRecord] = []
    seen_ids: set[UUID] = set()
    active_locators: set[tuple[str, str]] = set()
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Each snapshot resource must be an object")
        try:
            resource_id = UUID(str(item["resource_id"]))
            resource_type = ResourceType(str(item["resource_type"]))
        except (KeyError, ValueError) as exc:
            raise ValueError(f"Invalid snapshot resource: {exc}") from exc
        locator = item.get("locator")
        if not isinstance(locator, str) or not locator.strip():
            raise ValueError(f"Snapshot resource {resource_id} needs a non-empty locator")
        if resource_id in seen_ids:
            raise ValueError(f"Duplicate snapshot resource_id: {resource_id}")
        seen_ids.add(resource_id)
        lifecycle_state = item.get("lifecycle_state") or "active"
        if lifecycle_state == "active":
            key = (resource_type.value, locator)
            if key in active_locators:
                raise ValueError(f"Duplicate active snapshot resource: {resource_type.value}:{locator}")
            active_locators.add(key)
        parent = item.get("parent_resource_id")
        try:
            parent_resource_id = UUID(str(parent)) if parent else None
        except ValueError as exc:
            raise ValueError(f"Invalid parent_resource_id on snapshot resource {resource_id}") from exc
        if parent_resource_id == resource_id:
            raise ValueError(f"Snapshot resource {resource_id} names itself as its parent")
        resources.append(ResourceRecord(resource_id, resource_type, locator, lifecycle_state, parent_resource_id))
    for resource in resources:
        if resource.parent_resource_id is not None and resource.parent_resource_id not in seen_ids:
            raise ValueError(f"Snapshot resource {resource.resource_id} references an unknown parent")
    return tuple(resources)


def _snapshot_grants(items: Any, resource_ids: set[UUID]) -> tuple[Grant, ...]:
    if not isinstance(items, list):
        raise ValueError("Snapshot grants must be a list")
    grants: list[Grant] = []
    seen: set[tuple[str, str, UUID, str]] = set()
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Each snapshot grant must be an object")
        try:
            subject_type = GrantSubjectType(str(item["subject_type"]))
            resource_id = UUID(str(item["resource_id"]))
        except (KeyError, ValueError) as exc:
            raise ValueError(f"Invalid snapshot grant: {exc}") from exc
        subject_id = item.get("subject_id")
        role = item.get("role")
        if not isinstance(subject_id, str) or not subject_id.strip():
            raise ValueError("Each snapshot grant needs a non-empty subject_id")
        if not isinstance(role, str) or not role.strip():
            raise ValueError("Each snapshot grant needs a non-empty role")
        if subject_type == GrantSubjectType.EVERYONE and subject_id != "authenticated":
            raise ValueError("Everyone grants must use subject_id 'authenticated'")
        if subject_type != GrantSubjectType.PRINCIPAL and role == "owner":
            raise ValueError("Only a principal may receive the owner role")
        if resource_id not in resource_ids:
            raise ValueError(f"Snapshot grant references an unknown resource: {resource_id}")
        key = (subject_type.value, subject_id, resource_id, role)
        if key in seen:
            raise ValueError(f"Duplicate snapshot grant: {subject_type.value}:{subject_id} {role} {resource_id}")
        seen.add(key)
        try:
            created_at = datetime.fromisoformat(str(item["created_at"]))
        except (KeyError, ValueError) as exc:
            raise ValueError(f"Invalid created_at on snapshot grant {subject_type.value}:{subject_id}") from exc
        created_by = item.get("created_by")
        if not isinstance(created_by, str) or not created_by.strip():
            raise ValueError(f"Snapshot grant {subject_type.value}:{subject_id} needs created_by")
        grants.append(Grant(subject_id, resource_id, role, created_at, created_by, subject_type))
    return tuple(grants)


def _snapshot_application_roles(items: Any) -> tuple[ApplicationRoleAssignment, ...]:
    if not isinstance(items, list):
        raise ValueError("Snapshot application_roles must be a list")
    assignments: list[ApplicationRoleAssignment] = []
    seen: set[tuple[str, str]] = set()
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Each snapshot application role must be an object")
        principal_id = item.get("principal_id")
        if not isinstance(principal_id, str) or not principal_id.strip():
            raise ValueError("Each snapshot application role needs a non-empty principal_id")
        try:
            role = ApplicationRole(str(item["role"]))
        except (KeyError, ValueError) as exc:
            raise ValueError(f"Invalid snapshot application role: {exc}") from exc
        key = (principal_id, role.value)
        if key in seen:
            raise ValueError(f"Duplicate snapshot application role: {principal_id} {role.value}")
        seen.add(key)
        try:
            created_at = datetime.fromisoformat(str(item["created_at"]))
        except (KeyError, ValueError) as exc:
            raise ValueError(f"Invalid created_at on snapshot application role {principal_id}") from exc
        created_by = item.get("created_by")
        if not isinstance(created_by, str) or not created_by.strip():
            raise ValueError(f"Snapshot application role {principal_id} needs created_by")
        assignments.append(ApplicationRoleAssignment(principal_id, role, created_at, created_by))
    return tuple(assignments)


def _snapshot_audit_events(items: Any) -> tuple[AuditEvent, ...]:
    if not isinstance(items, list):
        raise ValueError("Snapshot audit_events must be a list")
    events: list[AuditEvent] = []
    seen: set[UUID] = set()
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Each snapshot audit event must be an object")
        try:
            event_id = UUID(str(item["event_id"]))
            occurred_at = datetime.fromisoformat(str(item["occurred_at"]))
        except (KeyError, ValueError) as exc:
            raise ValueError(f"Invalid snapshot audit event: {exc}") from exc
        if event_id in seen:
            raise ValueError(f"Duplicate snapshot audit event: {event_id}")
        seen.add(event_id)
        subject_type = item.get("subject_type")
        events.append(
            AuditEvent(
                event_id=event_id,
                occurred_at=occurred_at,
                actor_principal_id=str(item.get("actor_principal_id") or ""),
                event_type=str(item.get("event_type") or ""),
                resource_id=UUID(str(item["resource_id"])) if item.get("resource_id") else None,
                action=item.get("action"),
                outcome=str(item.get("outcome") or ""),
                correlation_id=item.get("correlation_id"),
                subject_type=GrantSubjectType(str(subject_type)) if subject_type else None,
                subject_id=item.get("subject_id"),
                provider=item.get("provider"),
                details=item.get("details"),
            )
        )
    return tuple(events)


def initialize_database(path: Path) -> None:
    """Create or migrate the authorization database schema."""
    repository = SQLiteAuthorizationRepository(path)
    repository.close()


def development_bootstrap_required(
    database: Path,
    principal_id: str,
    project_locators: set[str],
    shared_data_source_locators: set[str],
) -> bool:
    """Return whether a read-only check finds missing development authorization records."""
    if not database.is_file():
        return True

    database_uri = f"{database.resolve().as_uri()}?mode=ro"
    with sqlite3.connect(database_uri, uri=True) as connection:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        if not {"application_role", "resource"}.issubset(tables):
            return True

        has_development_admin = connection.execute(
            "SELECT 1 FROM application_role WHERE principal_id = ? AND role = 'admin'",
            (principal_id,),
        ).fetchone()
        if has_development_admin is None:
            return True

        registered_resources = {  # pylint: disable=unnecessary-comprehension
            (resource_type, locator)
            for resource_type, locator in connection.execute("SELECT resource_type, locator FROM resource WHERE lifecycle_state = 'active'")
        }

    expected_resources = {("project", locator) for locator in project_locators}
    expected_resources.update(("shared_data_source", locator) for locator in shared_data_source_locators)
    return not expected_resources.issubset(registered_resources)


def _load_document(path: Path, *, label: str) -> dict[str, Any]:
    """Read a JSON or YAML file and check that it holds an object."""
    try:
        content = path.read_text(encoding="utf-8")
        suffix = path.suffix.lower()
        if suffix in {".yaml", ".yml"}:
            value = YAML(typ="safe").load(content)
        elif suffix == ".json":
            value = json.loads(content)
        else:
            # A document can arrive through a pipe, for example as
            # --manifest /dev/stdin. Such a path carries no extension, so choose
            # the parser from the content instead of the name.
            try:
                value = json.loads(content)
            except json.JSONDecodeError:
                value = YAML(typ="safe").load(content)
    except (OSError, json.JSONDecodeError, YAMLError) as exc:
        raise ValueError(f"Invalid {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label.capitalize()} must contain an object")
    return value


def _load_validated_manifest(path: Path, *, allow_authenticated_everyone: bool = False) -> dict[str, Any]:
    manifest = _load_document(path, label="authorization manifest")
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
