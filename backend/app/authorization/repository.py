"""Persistence contract and SQLite implementation for authorization data."""

import sqlite3
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
from uuid import UUID, uuid4

from backend.app.authorization.models import AuditEvent, Grant, ResourceRecord, ResourceType


class AuthorizationRepository(Protocol):
    """Storage operations required by authorization policy evaluation."""

    def get_resource(self, resource_id: UUID) -> ResourceRecord | None: ...

    def get_resource_by_locator(self, resource_type: ResourceType, locator: str) -> ResourceRecord | None: ...

    def create_resource(self, resource: ResourceRecord) -> None: ...

    def add_grant(self, grant: Grant) -> None: ...

    def list_grants(self, principal_id: str) -> list[Grant]: ...

    def list_application_roles(self, principal_id: str) -> list[str]: ...

    def update_resource_lifecycle(self, resource_id: UUID, lifecycle_state: str) -> None: ...

    def remove_grant(self, principal_id: str, resource_id: UUID, role: str, actor_principal_id: str) -> None: ...

    def remove_application_role(self, principal_id: str, role: str, actor_principal_id: str) -> None: ...

    def list_audit_events(self) -> list[AuditEvent]: ...

    def bootstrap_admins(self, principal_ids: Sequence[str]) -> bool: ...


class SQLiteAuthorizationRepository:
    """Store authorization records in a dedicated SQLite database."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.path)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("PRAGMA journal_mode = WAL")
        self._connection.execute("PRAGMA busy_timeout = 5000")
        self._migrate()

    def close(self) -> None:
        """Close the SQLite connection."""
        self._connection.close()

    def _migrate(self) -> None:
        with self._connection:
            self._connection.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)")
            current = self._connection.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] or 0
            if current < 1:
                self._connection.executescript(
                    """
                    CREATE TABLE resource (
                        resource_id TEXT PRIMARY KEY,
                        resource_type TEXT NOT NULL,
                        locator TEXT NOT NULL,
                        parent_resource_id TEXT REFERENCES resource(resource_id),
                        lifecycle_state TEXT NOT NULL
                    );
                    CREATE UNIQUE INDEX active_resource_locator
                        ON resource(resource_type, locator)
                        WHERE lifecycle_state = 'active';
                    CREATE TABLE grant_record (
                        principal_id TEXT NOT NULL,
                        resource_id TEXT NOT NULL REFERENCES resource(resource_id),
                        role TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        created_by TEXT NOT NULL,
                        PRIMARY KEY(principal_id, resource_id, role)
                    );
                    CREATE TABLE application_role (
                        principal_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        created_by TEXT NOT NULL,
                        PRIMARY KEY(principal_id, role)
                    );
                    CREATE TABLE audit_event (
                        event_id TEXT PRIMARY KEY,
                        occurred_at TEXT NOT NULL,
                        actor_principal_id TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        resource_id TEXT,
                        action TEXT,
                        outcome TEXT NOT NULL,
                        correlation_id TEXT
                    );
                    INSERT INTO schema_version(version, applied_at) VALUES (1, CURRENT_TIMESTAMP);
                    """
                )

    def create_resource(self, resource: ResourceRecord) -> None:
        """Persist a server-owned resource record."""
        with self._connection:
            self._connection.execute(
                "INSERT INTO resource(resource_id, resource_type, locator, parent_resource_id, lifecycle_state) " "VALUES (?, ?, ?, ?, ?)",
                (
                    str(resource.resource_id),
                    resource.resource_type.value,
                    resource.locator,
                    _uuid(resource.parent_resource_id),
                    resource.lifecycle_state,
                ),
            )

    def add_grant(self, grant: Grant) -> None:
        """Persist a resource grant."""
        with self._connection:
            self._connection.execute(
                "INSERT INTO grant_record(principal_id, resource_id, role, created_at, created_by) VALUES (?, ?, ?, ?, ?)",
                (grant.principal_id, str(grant.resource_id), grant.role, grant.created_at.isoformat(), grant.created_by),
            )
            self._record_audit(
                actor_principal_id=grant.created_by,
                event_type="grant_created",
                resource_id=grant.resource_id,
                action=grant.role,
                outcome="allowed",
            )

    def add_application_role(self, principal_id: str, role: str, created_by: str) -> None:
        """Persist an application role assignment."""
        with self._connection:
            self._connection.execute(
                "INSERT INTO application_role(principal_id, role, created_at, created_by) VALUES (?, ?, ?, ?)",
                (principal_id, role, datetime.now(UTC).isoformat(), created_by),
            )
            self._record_audit(
                actor_principal_id=created_by,
                event_type="application_role_created",
                action=role,
                outcome="allowed",
            )

    def update_resource_lifecycle(self, resource_id: UUID, lifecycle_state: str) -> None:
        """Change the lifecycle state of a server-owned resource."""
        with self._connection:
            self._connection.execute(
                "UPDATE resource SET lifecycle_state = ? WHERE resource_id = ?",
                (lifecycle_state, str(resource_id)),
            )
            self._record_audit(
                actor_principal_id="system",
                event_type="resource_lifecycle_changed",
                resource_id=resource_id,
                action=lifecycle_state,
                outcome="allowed",
            )

    def remove_grant(self, principal_id: str, resource_id: UUID, role: str, actor_principal_id: str) -> None:
        """Remove a grant unless it would leave a project without an owner."""
        with self._connection:
            if role == "owner":
                owner_count = self._connection.execute(
                    "SELECT COUNT(*) FROM grant_record WHERE resource_id = ? AND role = 'owner'",
                    (str(resource_id),),
                ).fetchone()[0]
                if owner_count <= 1:
                    raise ValueError("The final project owner cannot be removed")
            deleted = self._connection.execute(
                "DELETE FROM grant_record WHERE principal_id = ? AND resource_id = ? AND role = ?",
                (principal_id, str(resource_id), role),
            ).rowcount
            if deleted != 1:
                raise ValueError("Grant does not exist")
            self._record_audit(
                actor_principal_id=actor_principal_id,
                event_type="grant_revoked",
                resource_id=resource_id,
                action=role,
                outcome="allowed",
            )

    def remove_application_role(self, principal_id: str, role: str, actor_principal_id: str) -> None:
        """Remove an application role unless it is the final administrator."""
        with self._connection:
            if role == "admin":
                admin_count = self._connection.execute(
                    "SELECT COUNT(*) FROM application_role WHERE role = 'admin'",
                ).fetchone()[0]
                if admin_count <= 1:
                    raise ValueError("The final application administrator cannot be removed")
            deleted = self._connection.execute(
                "DELETE FROM application_role WHERE principal_id = ? AND role = ?",
                (principal_id, role),
            ).rowcount
            if deleted != 1:
                raise ValueError("Application role does not exist")
            self._record_audit(
                actor_principal_id=actor_principal_id,
                event_type="application_role_revoked",
                action=role,
                outcome="allowed",
            )

    def bootstrap_admins(self, principal_ids: Sequence[str]) -> bool:
        """Create initial administrators only while no application roles exist."""
        normalized_ids = tuple(dict.fromkeys(principal_id.strip() for principal_id in principal_ids if principal_id.strip()))
        if not normalized_ids:
            raise ValueError("At least one bootstrap administrator is required")
        with self._connection:
            existing_roles = self._connection.execute("SELECT 1 FROM application_role LIMIT 1").fetchone()
            if existing_roles:
                return False
            occurred_at = datetime.now(UTC).isoformat()
            for principal_id in normalized_ids:
                self._connection.execute(
                    "INSERT INTO application_role(principal_id, role, created_at, created_by) VALUES (?, 'admin', ?, 'bootstrap')",
                    (principal_id, occurred_at),
                )
                self._record_audit(
                    actor_principal_id="bootstrap",
                    event_type="bootstrap_admin_created",
                    action="admin",
                    outcome="allowed",
                )
            return True

    def get_resource(self, resource_id: UUID) -> ResourceRecord | None:
        """Load a resource by its generation-specific UUID."""
        row = self._connection.execute("SELECT * FROM resource WHERE resource_id = ?", (str(resource_id),)).fetchone()
        return _resource(row) if row else None

    def get_resource_by_locator(self, resource_type: ResourceType, locator: str) -> ResourceRecord | None:
        """Load the active resource currently using a locator."""
        row = self._connection.execute(
            "SELECT * FROM resource WHERE resource_type = ? AND locator = ? AND lifecycle_state = 'active'",
            (resource_type.value, locator),
        ).fetchone()
        return _resource(row) if row else None

    def list_grants(self, principal_id: str) -> list[Grant]:
        """Load all resource grants for a principal."""
        rows = self._connection.execute("SELECT * FROM grant_record WHERE principal_id = ?", (principal_id,)).fetchall()
        return [_grant(row) for row in rows]

    def list_application_roles(self, principal_id: str) -> list[str]:
        """Load all application roles for a principal."""
        rows = self._connection.execute("SELECT role FROM application_role WHERE principal_id = ?", (principal_id,)).fetchall()
        return [row["role"] for row in rows]

    def list_audit_events(self) -> list[AuditEvent]:
        """Load durable authorization mutation events in occurrence order."""
        rows = self._connection.execute("SELECT * FROM audit_event ORDER BY occurred_at, event_id").fetchall()
        return [_audit_event(row) for row in rows]

    def _record_audit(
        self,
        *,
        actor_principal_id: str,
        event_type: str,
        resource_id: UUID | None = None,
        action: str | None = None,
        outcome: str,
        correlation_id: str | None = None,
    ) -> None:
        self._connection.execute(
            "INSERT INTO audit_event(event_id, occurred_at, actor_principal_id, event_type, resource_id, action, outcome, correlation_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                str(uuid4()),
                datetime.now(UTC).isoformat(),
                actor_principal_id,
                event_type,
                _uuid(resource_id),
                action,
                outcome,
                correlation_id,
            ),
        )


def _uuid(value: UUID | None) -> str | None:
    return str(value) if value else None


def _resource(row: sqlite3.Row) -> ResourceRecord:
    return ResourceRecord(
        resource_id=UUID(row["resource_id"]),
        resource_type=ResourceType(row["resource_type"]),
        locator=row["locator"],
        parent_resource_id=UUID(row["parent_resource_id"]) if row["parent_resource_id"] else None,
        lifecycle_state=row["lifecycle_state"],
    )


def _grant(row: sqlite3.Row) -> Grant:
    return Grant(
        principal_id=row["principal_id"],
        resource_id=UUID(row["resource_id"]),
        role=row["role"],
        created_at=datetime.fromisoformat(row["created_at"]),
        created_by=row["created_by"],
    )


def _audit_event(row: sqlite3.Row) -> AuditEvent:
    return AuditEvent(
        event_id=UUID(row["event_id"]),
        occurred_at=datetime.fromisoformat(row["occurred_at"]),
        actor_principal_id=row["actor_principal_id"],
        event_type=row["event_type"],
        resource_id=UUID(row["resource_id"]) if row["resource_id"] else None,
        action=row["action"],
        outcome=row["outcome"],
        correlation_id=row["correlation_id"],
    )
