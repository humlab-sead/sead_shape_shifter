"""Backend adapter for target-model conformance validation.

Bridges the core conformance engine (src/target_model/conformance.py) and the backend
API layer.  It accepts a resolved target-model dict (already expanded from any
@include: directive by Config.resolve_references) and a resolved ShapeShiftProject,
runs all registered conformance validators, and returns API ValidationError objects.

Follows the pure-domain-validator pattern: the core engine receives data, this adapter
handles the API boundary conversion.
"""

from typing import Any

from loguru import logger

from backend.app.mappers.validation_mapper import ValidationMapper
from backend.app.models.validation import ValidationError
from src.model import ShapeShiftProject
from src.target_model.conformance import ConformanceIssue, TargetModelConformanceValidator
from src.target_model.models import TargetModel


class TargetModelValidator:
    """Thin adapter between the core conformance engine and the backend API layer.

    Usage::

        validator = TargetModelValidator()
        errors = validator.validate(target_model_dict, core_project)
    """

    def validate(self, target_model_data: dict[str, Any], project: ShapeShiftProject) -> list[ValidationError]:
        """
        Run target-model conformance checks against a resolved core project.

        Args:
            target_model_data: Resolved target-model configuration dict (already
                expanded from any @include: reference).  Must be parseable into
                ``TargetModel``.
            project: Fully resolved core ``ShapeShiftProject`` instance.

        Returns:
            List of ``ValidationError`` objects (API layer).  Empty list means the
            project conforms to the target model.
        """
        try:
            target_model: TargetModel = TargetModel.model_validate(target_model_data)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning(f"Could not parse target model: {exc}")
            return [
                ValidationError(
                    severity="error",
                    entity=None,
                    field="metadata.target_model",
                    message=f"Target model specification could not be parsed: {exc}",
                    code="INVALID_TARGET_MODEL",
                    suggestion="Ensure the target model YAML matches the TargetModel schema.",
                )
            ]

        issues: list[ConformanceIssue] = TargetModelConformanceValidator().validate(target_model, project)
        errors: list[ValidationError] = [ValidationMapper.from_conformance_issue(issue) for issue in issues]

        logger.debug(f"Target-model conformance: {len(errors)} issue(s) found")
        return errors
