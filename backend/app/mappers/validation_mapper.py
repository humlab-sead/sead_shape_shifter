"""Mapper for translating between domain validation models and API validation models."""

from backend.app import models as api
from src.issues import CoreIssue
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
    def from_conformance_issue(issue: ConformanceIssue) -> api.ValidationError:
        """
        Convert a core ConformanceIssue to an API ValidationError.

        Conformance issues are structural by category and high priority by default.
        Severity is always 'error' — conformance violations are hard requirements.

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
