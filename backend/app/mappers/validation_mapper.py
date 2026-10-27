"""Mapper for translating between domain validation models and API validation models."""

from typing import Any

from backend.app import models as api
from src.issues import CoreIssue
from src.specifications.constraints import ValidationIssue as LinkerValidationIssue
from src.target_model.conformance import ConformanceIssue
from src.validators.data_validators import ValidationIssue


class ValidationMapper:
    """Mapper for validation layer boundaries (Domain ↔ API)."""

    @staticmethod
    def from_core_issue(
        issue: CoreIssue,
        *,
        default_category: api.ValidationCategory = api.ValidationCategory.STRUCTURAL,
        default_priority: api.ValidationPriority = api.ValidationPriority.MEDIUM,
        default_suggestion: str | None = None,
        default_auto_fixable: bool = False,
    ) -> api.ValidationError:
        """
        Convert any CoreIssue subclass to an API ValidationError.

        Args:
            issue: Domain/core issue object.
            default_category: Category to use when the issue does not define one.
            default_priority: Priority to use when the issue does not define one.
            default_suggestion: Suggestion to use when the issue does not define one.
            default_auto_fixable: Auto-fixable flag to use when the issue does not define one.

        Returns:
            API validation error model
        """
        # Map severity string to enum
        severity_map: dict[str, str] = {
            "error": "error",
            "warning": "warning",
            "info": "info",
        }
        severity: str = severity_map.get(issue.severity, "warning")

        # Map category string to enum
        category_map: dict[str, api.ValidationCategory] = {
            "data": api.ValidationCategory.DATA,
            "structural": api.ValidationCategory.STRUCTURAL,
            "structure": api.ValidationCategory.STRUCTURAL,
            "performance": api.ValidationCategory.PERFORMANCE,
            "conformance": api.ValidationCategory.CONFORMANCE,
        }
        category: api.ValidationCategory = category_map.get(issue.category or "", default_category)

        # Map priority string to enum
        priority_map: dict[str, api.ValidationPriority] = {
            "critical": api.ValidationPriority.CRITICAL,
            "high": api.ValidationPriority.HIGH,
            "medium": api.ValidationPriority.MEDIUM,
            "low": api.ValidationPriority.LOW,
        }
        raw_priority = getattr(issue, "priority", None)
        priority: api.ValidationPriority = priority_map.get(raw_priority or "", default_priority)

        suggestion = getattr(issue, "suggestion", None)
        if suggestion is None:
            suggestion = default_suggestion

        auto_fixable = getattr(issue, "auto_fixable", default_auto_fixable)
        metadata = issue.metadata or {}
        field_name = issue.field or issue.column

        return api.ValidationError(
            severity=severity,  # type: ignore[arg-type]
            entity=issue.entity,
            branch_name=metadata.get("branch_name"),
            branch_source=metadata.get("branch_source"),
            field=field_name,
            message=issue.message,
            code=issue.code,
            suggestion=suggestion,
            category=category,
            priority=priority,
            auto_fixable=auto_fixable,
            metadata=issue.metadata,
        )

    @staticmethod
    def to_api_error(issue: ValidationIssue) -> api.ValidationError:
        """Convert a domain ValidationIssue to an API ValidationError."""
        return ValidationMapper.from_core_issue(
            issue,
            default_category=api.ValidationCategory.DATA,
            default_priority=api.ValidationPriority.MEDIUM,
            default_auto_fixable=False,
        )

    @staticmethod
    def from_linker_issue(issue: LinkerValidationIssue) -> ValidationIssue:
        """Convert a foreign-key linker issue to a data validation issue."""
        return ValidationMapper._from_normalization_issue(
            issue_type=issue.issue_type,
            severity=issue.severity,
            local_entity=issue.local_entity,
            remote_entity=issue.remote_entity,
            message=issue.message,
            metadata=issue.metadata,
        )

    @staticmethod
    def from_preview_issue_payload(issue: dict[str, Any]) -> ValidationIssue:
        """Convert a structured preview issue to a data validation issue."""
        issue_type = issue.get("type")
        severity = issue.get("severity")
        local_entity = issue.get("local_entity")
        remote_entity = issue.get("remote_entity")
        message = issue.get("message")
        metadata = issue.get("metadata", {})

        if not isinstance(issue_type, str):
            raise ValueError("Preview validation issue must include a string 'type'")
        if severity not in {"error", "warning", "info"}:
            raise ValueError(f"Preview validation issue '{issue_type}' has unsupported severity: {severity!r}")
        if not isinstance(local_entity, str):
            raise ValueError(f"Preview validation issue '{issue_type}' must include a string 'local_entity'")
        if remote_entity is not None and not isinstance(remote_entity, str):
            raise ValueError(f"Preview validation issue '{issue_type}' has an invalid 'remote_entity'")
        if not isinstance(message, str):
            raise ValueError(f"Preview validation issue '{issue_type}' must include a string 'message'")
        if not isinstance(metadata, dict):
            raise ValueError(f"Preview validation issue '{issue_type}' must include object 'metadata'")

        return ValidationMapper._from_normalization_issue(
            issue_type=issue_type,
            severity=severity,
            local_entity=local_entity,
            remote_entity=remote_entity,
            message=message,
            metadata=metadata,
        )

    @staticmethod
    def _from_normalization_issue(
        issue_type: str,
        severity: str,
        local_entity: str,
        remote_entity: str | None,
        message: str,
        metadata: dict[str, Any],
    ) -> ValidationIssue:
        issue_metadata = dict(metadata)
        issue_metadata.setdefault("issue_type", issue_type)
        if remote_entity is not None:
            issue_metadata.setdefault("remote_entity", remote_entity)

        return ValidationIssue(
            severity=severity,
            entity=local_entity,
            message=message,
            code=issue_type.upper(),
            category="data",
            metadata=issue_metadata,
        )

    @staticmethod
    def from_conformance_issue(issue: ConformanceIssue) -> api.ValidationError:
        """
        Convert a core ConformanceIssue to an API ValidationError.

        Conformance issues are structural by category and high priority by default.
        Severity is preserved from the core conformance issue.

        Args:
            issue: Core conformance issue from TargetModelConformanceValidator

        Returns:
            API validation error model
        """
        return ValidationMapper.from_core_issue(
            issue,
            default_category=api.ValidationCategory.CONFORMANCE,
            default_priority=api.ValidationPriority.HIGH,
            default_auto_fixable=False,
        )
