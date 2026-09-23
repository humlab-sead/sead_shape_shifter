"""Centralized authorization primitives and policy services."""

from backend.app.authorization.authentication import AuthenticationAdapter
from backend.app.authorization.models import (
    Action,
    ApplicationRole,
    AuditEvent,
    AuthorizedResource,
    Grant,
    Principal,
    ResourceRecord,
    ResourceReference,
    ResourceType,
)
from backend.app.authorization.policy import AuthorizationPolicy
from backend.app.authorization.repository import AuthorizationRepository, SQLiteAuthorizationRepository
from backend.app.authorization.service import AuthorizationService

__all__ = [
    "Action",
    "AuthenticationAdapter",
    "ApplicationRole",
    "AuditEvent",
    "AuthorizedResource",
    "AuthorizationPolicy",
    "AuthorizationRepository",
    "AuthorizationService",
    "Grant",
    "Principal",
    "ResourceRecord",
    "ResourceReference",
    "ResourceType",
    "SQLiteAuthorizationRepository",
]
