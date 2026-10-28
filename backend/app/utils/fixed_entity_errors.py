"""Map fixed-entity shape errors to API validation errors."""

from backend.app.exceptions import ValidationError as DomainValidationError
from src.types.fixed_entity_types import (
    FixedEntityColumnTypeDeclarationError,
    FixedEntityShapeValidationError,
    FixedEntityTypeConventionDeclarationError,
    FixedEntityTypeValidationError,
)


def map_fixed_entity_shape_error(error: FixedEntityShapeValidationError, entity_name: str) -> DomainValidationError:
    """Convert a fixed-entity row-shape error to an actionable API validation error."""
    return map_fixed_entity_error(error, entity_name)


def map_fixed_entity_error(
    error: (
        FixedEntityColumnTypeDeclarationError
        | FixedEntityShapeValidationError
        | FixedEntityTypeConventionDeclarationError
        | FixedEntityTypeValidationError
    ),
    entity_name: str | None,
) -> DomainValidationError:
    """Convert fixed-entity configuration errors to actionable domain errors."""
    if isinstance(error, FixedEntityShapeValidationError):
        error_code = "FIXED_ENTITY_SHAPE_INVALID"
        tip = "Check that each fixed-entity row matches its declared columns and supported identity-inclusive format."
        validation_type = "fixed_entity_shape"
        message = str(error)
        context: dict[str, object] = {"entity": entity_name, "validation": validation_type}
    elif isinstance(error, FixedEntityColumnTypeDeclarationError):
        error_code = "FIXED_ENTITY_COLUMN_TYPE_INVALID"
        tip = "Use a supported type name for each fixed-entity column in column_types."
        validation_type = "fixed_entity_column_type"
        message = str(error)
        context = {"entity": entity_name, "column": error.column_name, "validation": validation_type}
    elif isinstance(error, FixedEntityTypeConventionDeclarationError):
        error_code = "FIXED_ENTITY_TYPE_CONVENTION_INVALID"
        tip = "Correct fixed_entity_types.conventions and declare a supported type for each convention."
        validation_type = "fixed_entity_type_convention"
        message = str(error)
        context = {"entity": entity_name, "validation": validation_type}
    else:
        error_code = "FIXED_ENTITY_VALUE_INVALID"
        tip = "Correct the invalid fixed-entity values or change the declared column types."
        validation_type = "fixed_entity_value"
        details = "; ".join(
            f"row {issue.row_index + 1}, column '{issue.column_name}': {issue.reason} (expected {issue.expected_type})"
            for issue in error.issues
        )
        message = f"{error}: {details}" if details else str(error)
        context = {"entity": entity_name, "validation": validation_type}

    return DomainValidationError(
        message=message,
        error_code=error_code,
        tips=[tip],
        context=context,
        recoverable=True,
    )
