"""Map fixed-entity shape errors to API validation errors."""

from backend.app.exceptions import ValidationError
from src.types.fixed_entity_types import FixedEntityShapeValidationError


def map_fixed_entity_shape_error(error: FixedEntityShapeValidationError, entity_name: str) -> ValidationError:
    """Convert a fixed-entity row-shape error to an actionable API validation error."""
    return ValidationError(
        message=str(error),
        error_code="FIXED_ENTITY_SHAPE_INVALID",
        context={"entity": entity_name, "validation": "fixed_entity_shape"},
        recoverable=True,
    )
