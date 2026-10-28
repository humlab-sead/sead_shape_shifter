"""Collect load-time issues for fixed entities."""

from typing import Any

from loguru import logger

from backend.app.mappers.project_load_issue_collector import ProjectLoadIssues
from backend.app.models.validation import ValidationCategory
from backend.app.models.validation import ValidationError as APIValidationError
from backend.app.utils.fixed_entity_errors import map_fixed_entity_error
from src.types.fixed_entity_types import (
    FixedEntityColumnTypeDeclarationError,
    FixedEntityNormalizationWarning,
    FixedEntityShapeValidationError,
    FixedEntityTypeCoercer,
    FixedEntityTypeConvention,
    FixedEntityTypeConventionDeclarationError,
    FixedEntityTypeValidationError,
    format_fixed_entity_normalization_warning,
    normalize_fixed_entity_type_conventions,
)


class FixedEntityLoadIssueCollector:
    """Collect fixed-entity normalization warnings and configuration errors."""

    def collect(self, cfg_dict: dict[str, Any], project_name: str, filename: str | None = None) -> ProjectLoadIssues:
        warnings: list[str] = []
        errors: list[APIValidationError] = []
        source_name = filename or project_name

        try:
            conventions: list[FixedEntityTypeConvention] = normalize_fixed_entity_type_conventions(cfg_dict.get("options", {}))
        except FixedEntityTypeConventionDeclarationError as error:
            fixed_entity_names = [
                entity_name
                for entity_name, entity_dict in cfg_dict.get("entities", {}).items()
                if isinstance(entity_dict, dict) and entity_dict.get("type") == "fixed"
            ]
            if fixed_entity_names:
                for entity_name in fixed_entity_names:
                    self._log_load_error(project_name, source_name, entity_name, error)
                    errors.append(self._load_error_issue(error, entity_name))
            else:
                self._log_load_error(project_name, source_name, None, error)
                errors.append(self._load_error_issue(error, None))
            return ProjectLoadIssues(warnings=warnings, errors=errors)

        for entity_name, entity_dict in cfg_dict.get("entities", {}).items():
            if not isinstance(entity_dict, dict) or entity_dict.get("type") != "fixed":
                continue

            columns = entity_dict.get("columns")
            if not isinstance(columns, list) or not columns:
                continue

            try:
                _coerced_values, normalization_warnings = FixedEntityTypeCoercer.coerce_fixed_entity_values_with_warnings(
                    entity_dict,
                    columns,
                    entity_name,
                    conventions,
                )
            except (
                FixedEntityColumnTypeDeclarationError,
                FixedEntityShapeValidationError,
                FixedEntityTypeValidationError,
            ) as error:
                self._log_load_error(project_name, source_name, entity_name, error)
                errors.append(self._load_error_issue(error, entity_name))
                continue

            for warning in normalization_warnings:
                warnings.append(format_fixed_entity_normalization_warning(warning))
                self._log_load_warning(project_name, source_name, warning)

        return ProjectLoadIssues(warnings=warnings, errors=errors)

    @staticmethod
    def _load_error_issue(
        error: (
            FixedEntityColumnTypeDeclarationError
            | FixedEntityTypeConventionDeclarationError
            | FixedEntityShapeValidationError
            | FixedEntityTypeValidationError
        ),
        entity_name: str | None,
    ) -> APIValidationError:
        """Convert a fixed-entity load error to a user-facing validation issue."""
        domain_error = map_fixed_entity_error(error, entity_name)
        context = domain_error.context
        return APIValidationError(
            severity="error",
            entity=entity_name,
            field=context.get("column") if isinstance(context.get("column"), str) else None,
            message=domain_error.message,
            code=domain_error.code,
            suggestion=" ".join(domain_error.tips) or None,
            category=ValidationCategory.STRUCTURAL,
            metadata=context,
        )

    @staticmethod
    def _log_load_error(
        project_name: str,
        source_name: str,
        entity_name: str | None,
        error: (
            FixedEntityColumnTypeDeclarationError
            | FixedEntityTypeConventionDeclarationError
            | FixedEntityShapeValidationError
            | FixedEntityTypeValidationError
        ),
    ) -> None:
        """Log a fixed-entity validation error without preventing project editing."""
        reason = str(error)
        if isinstance(error, FixedEntityTypeValidationError):
            issue_details = "; ".join(
                f"row {issue.row_index + 1}, column '{issue.column_name}': {issue.reason} "
                f"(value {issue.raw_value!r}, expected {issue.expected_type})"
                for issue in error.issues
            )
            reason = f"{reason}: {issue_details}"

        entity_detail = f" entity='{entity_name}'" if entity_name is not None else ""
        logger.error(
            "Fixed-entity validation error on load: project='{}' source='{}'{} error_type='{}' reason={!r}",
            project_name,
            source_name,
            entity_detail,
            type(error).__name__,
            reason,
        )

    @staticmethod
    def _log_load_warning(project_name: str, source_name: str, warning: FixedEntityNormalizationWarning) -> None:
        """Log a fixed-entity normalization warning."""
        logger.warning(
            "Fixed entity normalization on load: project='{}' source='{}' entity='{}' row={} "
            "column='{}' raw_value={!r} normalized_value={!r} target_type='{}'",
            project_name,
            source_name,
            warning.entity_name,
            warning.row_index + 1,
            warning.column_name,
            warning.raw_value,
            warning.normalized_value,
            warning.expected_type,
        )
