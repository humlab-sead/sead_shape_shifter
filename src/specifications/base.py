from abc import ABC, abstractmethod
from typing import Any

from loguru import logger

from src.utility import Registry, dotget

# pylint: disable=line-too-long


class SpecificationIssue:
    """Custom exception for specification validation errors/warnings."""

    def __init__(self, *, severity: str, message: str, entity: str | None = None, **kwargs) -> None:
        self.severity: str = severity
        self.message: str = message
        self.entity_name: str | None = entity
        self.entity_field: str | None = kwargs.get("field")
        self.column_name: str | None = kwargs.get("column")
        self.kwargs = kwargs

    def __str__(self) -> str:
        """Return string representation of the issue."""
        parts = [f"[{self.severity.upper()}]"]
        if self.entity_name:
            parts.append(f"Entity '{self.entity_name}':")
        parts.append(self.message)
        if self.entity_field:
            parts.append(f"(field: {self.entity_field})")
        if self.column_name:
            parts.append(f"(column: {self.column_name})")
        return " ".join(parts)

    def __repr__(self) -> str:
        """Return representation of the issue."""
        return self.__str__()


class ProjectSpecification(ABC):
    """Base specification for project validation."""

    def __init__(self, project_cfg: dict[str, Any]) -> None:
        self.errors: list[SpecificationIssue] = []
        self.warnings: list[SpecificationIssue] = []
        self.project_cfg: dict[str, Any] = project_cfg

    def clear(self) -> None:
        """Clear all errors and warnings."""
        self.errors = []
        self.warnings = []

    def merge(self, other: "ProjectSpecification") -> "ProjectSpecification":
        """Merge another FieldValidator's issues into this one."""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        return self

    def get_entity_cfg(self, entity_name: str) -> dict[str, Any]:
        """Get the configuration for a specific entity."""
        return dotget(self.project_cfg, f"entities.{entity_name}", {})

    def exists(self, entity_name: str) -> bool:
        """Check if a specific entity exists in the configuration."""
        return dotget(self.project_cfg, f"entities.{entity_name}", None) is not None

    @abstractmethod
    def is_satisfied_by(self, **kwargs) -> bool:
        """Check if the configuration satisfies this specification.

        Implementations should accept specific named parameters appropriate
        to their validation scope (e.g., entity_name, fk_cfg) via **kwargs.

        Returns:
            True if valid, False otherwise.
        """

    def add_error(self, error: str, entity: str | None, **kwargs) -> None:
        """Add an error message."""
        self.errors.append(SpecificationIssue(severity="error", message=error, entity=entity, **kwargs))

    def add_warning(self, warning: str, entity: str | None, **kwargs) -> None:
        """Add a warning message."""
        self.warnings.append(SpecificationIssue(severity="warning", message=warning, entity=entity, **kwargs))

    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0

    def check_fields(self, entity_name: str, fields: list[str], keys: str, message: str | None = None, **kwargs) -> None:
        """Check fields based on the specified check type.

        Args:
            entity_name: Name of the entity being validated
            fields: List of field names to check
            keys: Comma-separated validator keys with optional severity (/E or /W)
            message: Optional custom message to append to validation failures
            **kwargs: Additional arguments passed to validators (e.g., target_cfg, expected_types)
        """
        message = message or ""
        for key in keys.split(","):
            key: str = key.strip()
            severity: str = "E"
            if "/" in key:
                # Severity level is specified at end of string "/W" or "/E"
                key, severity = key.rsplit("/", 1)
                if severity not in ("E", "W"):
                    logger.info(f"Unknown severity '{severity}' specified in check type '{key}'. Skipping.")
                    continue
            if key not in FIELD_VALIDATORS.items:
                logger.info(f"Unknown field check type '{key}' specified. Skipping.")
                continue
            specification = FIELD_VALIDATORS.get(key.strip())(self.project_cfg, severity=severity)
            specification.is_satisfied_by(entity_name=entity_name, fields=fields, message=message, **kwargs)
            self.merge(specification)


class FieldValidator(ProjectSpecification):

    def __init__(self, project_cfg: dict[str, Any], *, severity: str = "E") -> None:
        super().__init__(project_cfg)
        self.severity: str = severity

    def is_satisfied_by(self, *, entity_name: str = "", fields: list[str] | None = None, **kwargs) -> bool:
        self.clear()
        for field_name in fields or []:
            self.is_satisfied_by_field(entity_name, field_name, **kwargs)
        return True

    def is_satisfied_by_field(self, entity_name: str, field: str, *, target_cfg: dict[str, Any] | None = None, **kwargs) -> None:
        """Validate a specific field in the entity configuration, or target_cfg if provided."""
        target_cfg = target_cfg or self.get_entity_cfg(entity_name) or {}
        if not self.rule_predicate(target_cfg, entity_name, field, **kwargs):
            self.rule_fail(target_cfg, entity_name, field, **kwargs)

    @abstractmethod
    def rule_predicate(self, target_cfg: dict[str, Any], entity_name: str, field: str, **kwargs) -> bool:
        """Apply the validation rule to the specified field."""

    @abstractmethod
    def rule_fail(self, target_cfg: dict[str, Any], entity_name: str, field: str, **kwargs) -> None:
        """Log the failure of the validation rule."""

    @property
    def rule_handler(self):
        """Return the appropriate method to log based on severity."""
        return self.add_error if self.severity == "E" else self.add_warning


class FieldValidatorRegistry(Registry):
    """Registry for field validators."""

    items: dict[str, FieldValidator] = {}


FIELD_VALIDATORS = FieldValidatorRegistry()
