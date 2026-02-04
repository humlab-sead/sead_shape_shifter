"""
Domain Exception Hierarchy for Shape Shifter.

This module defines the exception hierarchy that captures domain knowledge
and provides more actionable error information to users.

Architecture Principles:
- Exceptions flow from core layer → API layer → frontend
- Each exception carries metadata (message, tips, recoverable flag)
- HTTP layer maps exception types to status codes
- Frontend receives JSON for consistent display of error information

Exception Hierarchy:
    DomainException (base)
    ├── DataIntegrityError          - Corrupted or invalid data structures
    │   ├── ForeignKeyError         - Invalid FK definitions or references
    │   └── SchemaValidationError   - Entity schema validation failures
    ├── DependencyError             - Entity dependency/graph issues
    │   ├── CircularDependencyError - Cyclic entity relationships
    │   └── MissingDependencyError  - Referenced entity doesn't exist
    ├── ValidationError             - Business rule violations
    │   ├── ConstraintViolationError - Failed constraint checks
    │   └── ConfigurationError      - Invalid project configuration
    └── ResourceError               - Resource access/availability issues
        ├── ResourceNotFoundError   - Entity/project not found
        └── ResourceConflictError   - Name collision, already exists
"""

from typing import Any, ClassVar

from backend.app.error_tips import get_tips


class DomainException(Exception):
    """
    Base class for all domain exceptions.

    Attributes:
        message: Human-readable error message
        code: Unique error code for tip lookup (resolved from class default or override)
        tips: List of actionable troubleshooting steps
        recoverable: Whether user can fix without developer intervention
        context: Additional context data (entity names, values, etc.)
    """

    # Subclasses should override this with a unique error code
    error_code: ClassVar[str] = "UNKNOWN_ERROR"

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        tips: list[str] | None = None,
        recoverable: bool = True,
        context: dict[str, Any] | None = None,
    ):
        """
        Initialize domain exception.

        Args:
            message: Clear description of what went wrong
            error_code: Optional override for error code (uses class default if not provided)
            tips: Optional override for tips (uses registry if not provided)
            recoverable: True if user can fix, False if requires code changes
            context: Additional debugging context (entities, values, etc.)
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}

        # Store resolved error code in instance attribute (avoid ClassVar conflict)
        self.code = error_code or self.__class__.error_code

        # Auto-load tips from registry with context-based template formatting
        self.tips = tips if tips is not None else get_tips(self.code, self.context)

        self.recoverable = recoverable

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to structured dictionary for API responses."""
        return {
            "error_type": self.__class__.__name__,
            "error_code": self.code,
            "message": self.message,
            "tips": self.tips,
            "recoverable": self.recoverable,
            "context": self.context,
        }


# ============================================================================
# Data Integrity Errors
# ============================================================================


class DataIntegrityError(DomainException):
    """Base class for data integrity violations."""

    error_code = "DATA_INTEGRITY_VIOLATION"

    pass


class ForeignKeyError(DataIntegrityError):
    """
    Invalid foreign key definition or reference.

    Common causes:
    - Keys not formatted as lists of strings
    - Dict structures instead of string values
    - Mismatched local_keys/remote_keys
    - Referenced entity doesn't exist
    """

    error_code = "FOREIGN_KEY_INVALID"

    def __init__(
        self,
        message: str,
        entity: str | None = None,
        foreign_key: dict[str, Any] | None = None,
        **kwargs: Any,
    ):
        """
        Initialize foreign key error.

        Args:
            message: Error description
            entity: Entity with invalid FK
            foreign_key: The problematic FK definition
            **kwargs: Additional DomainException arguments
        """
        context = kwargs.pop("context", {})
        if entity:
            context["entity"] = entity
        if foreign_key:
            context["foreign_key"] = foreign_key

        super().__init__(message, context=context, **kwargs)


class SchemaValidationError(DataIntegrityError):
    """
    Entity schema validation failure.

    Common causes:
    - Missing required fields
    - Invalid data types
    - Malformed YAML structure
    """

    error_code = "SCHEMA_VALIDATION_FAILED"

    def __init__(
        self,
        message: str,
        entity: str | None = None,
        field: str | None = None,
        **kwargs: Any,
    ):
        """
        Initialize schema validation error.

        Args:
            message: Error description
            entity: Entity with schema issue
            field: Specific field that failed validation
            **kwargs: Additional DomainException arguments
        """
        context = kwargs.pop("context", {})
        if entity:
            context["entity"] = entity
        if field:
            context["field"] = field

        super().__init__(message, context=context, **kwargs)


# ============================================================================
# Dependency Errors
# ============================================================================


class DependencyError(DomainException):
    """Base class for entity dependency graph errors."""

    error_code = "DEPENDENCY_ERROR"


class CircularDependencyError(DependencyError):
    """
    Circular dependency detected in entity relationships.

    Occurs when entities have cyclic foreign key references (A→B→C→A).
    """

    error_code = "CIRCULAR_DEPENDENCY"

    def __init__(
        self,
        message: str,
        cycle: list[str] | None = None,
        **kwargs: Any,
    ):
        """
        Initialize circular dependency error.

        Args:
            message: Error description
            cycle: List of entity names forming the cycle
            **kwargs: Additional DomainException arguments
        """
        context = kwargs.pop("context", {})
        if cycle:
            context["cycle"] = cycle
            # Format cycle for display: A → B → C → A
            cycle_str = " → ".join(cycle + [cycle[0]])
            message = f"{message}\n\nDetected cycle: {cycle_str}"

        super().__init__(message, context=context, **kwargs)


class MissingDependencyError(DependencyError):
    """
    Referenced entity does not exist in project.

    Occurs when FK references non-existent entity.
    """

    error_code = "MISSING_DEPENDENCY"

    def __init__(
        self,
        message: str,
        entity: str | None = None,
        missing_entity: str | None = None,
        **kwargs: Any,
    ):
        """
        Initialize missing dependency error.

        Args:
            message: Error description
            entity: Entity with FK reference
            missing_entity: Referenced entity that doesn't exist
            **kwargs: Additional DomainException arguments
        """
        context = kwargs.pop("context", {})
        if entity:
            context["entity"] = entity
        if missing_entity:
            context["missing_entity"] = missing_entity

        super().__init__(message, context=context, **kwargs)


# ============================================================================
# Validation Errors
# ============================================================================


class ValidationError(DomainException):
    """Base class for business rule validation errors."""

    error_code = "VALIDATION_FAILED"


class ConstraintViolationError(ValidationError):
    """
    Constraint validation failed.

    Occurs when data violates cardinality, uniqueness, or other constraints.
    """

    error_code = "CONSTRAINT_VIOLATION"

    def __init__(
        self,
        message: str,
        constraint_type: str | None = None,
        entity: str | None = None,
        **kwargs: Any,
    ):
        """
        Initialize constraint violation error.

        Args:
            message: Error description
            constraint_type: Type of constraint (cardinality, unique, etc.)
            entity: Entity with constraint violation
            **kwargs: Additional DomainException arguments
        """
        context = kwargs.pop("context", {})
        if constraint_type:
            context["constraint_type"] = constraint_type
        if entity:
            context["entity"] = entity

        super().__init__(message, context=context, **kwargs)


class ConfigurationError(ValidationError):
    """
    Invalid project configuration.

    Occurs when project structure violates specifications.
    """

    error_code = "CONFIG_INVALID"

    def __init__(
        self,
        message: str,
        specification: str | None = None,
        **kwargs: Any,
    ):
        """
        Initialize configuration error.

        Args:
            message: Error description
            specification: Name of violated specification
            **kwargs: Additional DomainException arguments
        """
        context = kwargs.pop("context", {})
        if specification:
            context["specification"] = specification

        super().__init__(message, context=context, **kwargs)


# ============================================================================
# Resource Errors
# ============================================================================


class ResourceError(DomainException):
    """Base class for resource access/availability errors."""

    error_code = "RESOURCE_ERROR"


class ResourceNotFoundError(ResourceError):
    """
    Requested resource does not exist.

    Used for projects, entities, files, etc.
    """

    error_code = "RESOURCE_NOT_FOUND"

    def __init__(
        self,
        message: str,
        resource_type: str | None = None,
        resource_id: str | None = None,
        **kwargs: Any,
    ):
        """
        Initialize resource not found error.

        Args:
            message: Error description
            resource_type: Type of resource (project, entity, etc.)
            resource_id: ID/name of missing resource
            **kwargs: Additional DomainException arguments
        """
        context = kwargs.pop("context", {})
        if resource_type:
            context["resource_type"] = resource_type
        if resource_id:
            context["resource_id"] = resource_id

        super().__init__(message, recoverable=True, context=context, **kwargs)


class ResourceConflictError(ResourceError):
    """
    Resource already exists with same identifier.

    Used for duplicate names, ID collisions, etc.
    """

    error_code = "RESOURCE_CONFLICT"

    def __init__(
        self,
        message: str,
        resource_type: str | None = None,
        resource_id: str | None = None,
        **kwargs: Any,
    ):
        """
        Initialize resource conflict error.

        Args:
            message: Error description
            resource_type: Type of resource (project, entity, etc.)
            resource_id: Conflicting ID/name
            **kwargs: Additional DomainException arguments
        """
        context = kwargs.pop("context", {})
        if resource_type:
            context["resource_type"] = resource_type
        if resource_id:
            context["resource_id"] = resource_id

        super().__init__(message, recoverable=True, context=context, **kwargs)


# ============================================================================
# Query Execution Errors
# ============================================================================


class QueryExecutionError(DomainException):
    """
    Query execution failed.

    Common causes:
    - Data source connection issues
    - Invalid SQL syntax
    - Query timeout
    - Missing permissions
    """

    error_code = "QUERY_EXEC_FAILED"

    def __init__(
        self,
        message: str,
        data_source: str | None = None,
        query: str | None = None,
        **kwargs: Any,
    ):
        """
        Initialize query execution error.

        Args:
            message: Error description
            data_source: Data source name
            query: SQL query that failed
            **kwargs: Additional DomainException arguments
        """
        context = kwargs.pop("context", {})
        if data_source:
            context["data_source"] = data_source
        if query:
            # Truncate long queries for context
            context["query"] = query[:500] + "..." if len(query) > 500 else query

        super().__init__(message, recoverable=True, context=context, **kwargs)


class QuerySecurityError(DomainException):
    """
    Query contains prohibited operations.

    Occurs when query attempts destructive operations (DELETE, DROP, etc.)
    """

    error_code = "QUERY_SECURITY_VIOLATION"

    def __init__(
        self,
        message: str,
        query: str | None = None,
        violations: list[str] | None = None,
        **kwargs: Any,
    ):
        """
        Initialize query security error.

        Args:
            message: Error description
            query: Prohibited query
            violations: List of security violations detected
            **kwargs: Additional DomainException arguments
        """
        context = kwargs.pop("context", {})
        if query:
            context["query"] = query[:500] + "..." if len(query) > 500 else query
        if violations:
            context["violations"] = violations

        # Security errors are not recoverable by user - need permission changes
        super().__init__(message, recoverable=False, context=context, **kwargs)


# ============================================================================
# Schema Introspection Errors
# ============================================================================


class SchemaIntrospectionError(DomainException):
    """
    Schema introspection failed.

    Common causes:
    - Data source not connected
    - Driver doesn't support introspection
    - Insufficient permissions
    - Table/database doesn't exist
    """

    error_code = "SCHEMA_INTROSPECT_FAILED"

    def __init__(
        self,
        message: str,
        data_source: str | None = None,
        operation: str | None = None,
        **kwargs: Any,
    ):
        """
        Initialize schema introspection error.

        Args:
            message: Error description
            data_source: Data source name
            operation: Introspection operation (get_tables, get_columns, etc.)
            **kwargs: Additional DomainException arguments
        """
        context = kwargs.pop("context", {})
        if data_source:
            context["data_source"] = data_source
        if operation:
            context["operation"] = operation

        super().__init__(message, recoverable=True, context=context, **kwargs)
