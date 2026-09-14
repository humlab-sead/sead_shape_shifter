"""Typed values used by the authorization system."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class Action(StrEnum):
    """Operations that can be authorized."""

    READ = "read"
    EDIT = "edit"
    EXECUTE = "execute"
    DELETE = "delete"
    MANAGE_GRANTS = "manage_grants"
    CREATE_PROJECT = "create_project"
    READ_LOGS = "read_logs"
    MANAGE_SHARED_SOURCES = "manage_shared_sources"
    READ_ALL_SHARED_SOURCES = "read_all_shared_sources"
    RUN_INGESTERS = "run_ingesters"
    MANAGE_ALL_GRANTS = "manage_all_grants"
    MANAGE_APPLICATION_ROLES = "manage_application_roles"
    CONFIGURE_INGESTERS = "configure_ingesters"


class ResourceType(StrEnum):
    """Protected resource categories."""

    PROJECT = "project"
    SHARED_DATA_SOURCE = "shared_data_source"
    PROJECT_CHILD = "project_child"
    SHARED_DATA_SOURCE_CHILD = "shared_data_source_child"


class ApplicationRole(StrEnum):
    """Deployment-wide roles."""

    PROJECT_CREATOR = "project_creator"
    OPERATOR = "operator"
    ADMIN = "admin"


class GrantSubjectType(StrEnum):
    """Kinds of subjects that can receive a resource grant."""

    PRINCIPAL = "principal"
    GROUP = "group"
    EVERYONE = "everyone"


@dataclass(frozen=True, slots=True)
class Principal:
    """Stable identity used for grant lookup."""

    principal_id: str
    authentication_provider: str
    authenticated_at: datetime
    group_ids: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class ResourceReference:
    """Stable resource identity used in authorization checks."""

    resource_id: UUID
    resource_type: ResourceType


@dataclass(frozen=True, slots=True)
class ResourceRecord:
    """Server-owned resource record and current locator."""

    resource_id: UUID
    resource_type: ResourceType
    locator: str
    lifecycle_state: str = "active"
    parent_resource_id: UUID | None = None

    def reference(self) -> ResourceReference:
        """Return the stable identity without exposing its locator."""
        return ResourceReference(self.resource_id, self.resource_type)


@dataclass(frozen=True, slots=True)
class ApplicationRoleAssignment:
    """Application role assigned to a principal."""

    principal_id: str
    role: ApplicationRole
    created_at: datetime
    created_by: str


@dataclass(frozen=True, slots=True)
class Grant:
    """Role assigned to a typed subject for a resource."""

    subject_id: str
    resource_id: UUID
    role: str
    created_at: datetime
    created_by: str
    subject_type: GrantSubjectType = GrantSubjectType.PRINCIPAL

    @property
    def principal_id(self) -> str:
        """Return the subject ID for compatibility with direct-principal callers."""
        return self.subject_id


@dataclass(frozen=True, slots=True)
class AuditEvent:
    """Durable record of an authorization-sensitive mutation."""

    event_id: UUID
    occurred_at: datetime
    actor_principal_id: str
    event_type: str
    resource_id: UUID | None
    action: str | None
    outcome: str
    correlation_id: str | None
    subject_type: GrantSubjectType | None = None
    subject_id: str | None = None
    provider: str | None = None
    details: str | None = None


@dataclass(frozen=True, slots=True)
class AuthorizedResource:
    """Resource returned after a successful authorization decision."""

    principal: Principal
    action: Action
    resource: ResourceRecord
