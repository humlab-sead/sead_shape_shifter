"""Mapper for translating between domain validation models and API validation models."""

from backend.app import models as api
from src.target_model.conformance import ConformanceIssue
from src.validators.data_validators import ValidationIssue


class ValidationMapper:
    """Mapper for validation layer boundaries (Domain ↔ API)."""

    @staticmethod
    def to_api_error(issue: ValidationIssue) -> api.ValidationError:
        """
        Convert domain ValidationIssue to API ValidationError.

        Args:
            issue: Domain validation issue

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
        }
        category: api.ValidationCategory = category_map.get(issue.category, api.ValidationCategory.DATA)

        # Map priority string to enum
        priority_map: dict[str, api.ValidationPriority] = {
            "high": api.ValidationPriority.HIGH,
            "medium": api.ValidationPriority.MEDIUM,
            "low": api.ValidationPriority.LOW,
        }
        priority: api.ValidationPriority = priority_map.get(issue.priority, api.ValidationPriority.MEDIUM)

        return api.ValidationError(
            severity=severity,  # type: ignore[arg-type]
            entity=issue.entity,
            field=issue.field,
            message=issue.message,
            code=issue.code,
            suggestion=issue.suggestion,
            category=category,
            priority=priority,
            auto_fixable=issue.auto_fixable,
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
        return api.ValidationError(
            severity="error",
            entity=issue.entity,
            field=None,
            message=issue.message,
            code=issue.code,
            suggestion=None,
            category=api.ValidationCategory.CONFORMANCE,
            priority=api.ValidationPriority.HIGH,
            auto_fixable=False,
        )
