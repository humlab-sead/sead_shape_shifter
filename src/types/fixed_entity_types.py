"""Type coercion and validation for fixed-value entities.

Fixed entities require strict type handling to prevent silent FK merge failures.
This module implements the coercion policy and validation rules for `_id` columns.

Key rules:
- Columns ending with '_id' must be integers (foreign keys)
- Shape validation (row count) is a hard gate before any coercion
- Coercible values are normalized in memory; non-coercible raise errors
- Booleans are never treated as integers
"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from pandas import isna

FixedEntityColumnTypeName = str
ALLOWED_FIXED_ENTITY_COLUMN_TYPES: frozenset[str] = frozenset({"int", "string", "float", "bool", "date"})


def build_fixed_entity_full_columns(columns: list[str], key_columns: list[str], public_id: str | None) -> list[str]:
    """Build the canonical full column order for fixed entities."""
    full_columns: list[str] = ["system_id"]

    if public_id and public_id not in full_columns:
        full_columns.append(public_id)

    for key in key_columns:
        if key not in full_columns:
            full_columns.append(key)

    for column in columns:
        if column not in full_columns:
            full_columns.append(column)

    return full_columns


class FixedEntityColumnTypeDeclarationError(ValueError):
    """Raised when fixed-entity column_types contains invalid declarations."""

    def __init__(self, *, entity_name: str, column_name: str, message: str) -> None:
        self.entity_name = entity_name
        self.column_name = column_name
        super().__init__(message)


def infer_fixed_entity_column_type(column_name: str) -> type:
    """Infer Python type from column name based on naming conventions.

    Columns ending with '_id' are foreign keys and must be integers.
    All other columns default to string.

    Args:
        column_name: Column name to infer type for

    Returns:
        int or str type
    """
    if column_name.endswith("_id"):
        return int
    return str


def normalize_fixed_entity_column_types(
    entity_name: str,
    columns: list[str],
    column_types: dict[str, Any] | None,
) -> dict[str, FixedEntityColumnTypeName]:
    """Validate and normalize explicit fixed-entity column type declarations."""
    if column_types is None:
        return {}

    normalized_column_types: dict[str, FixedEntityColumnTypeName] = {}

    for column_name, declared_type in column_types.items():
        normalized_type: str = str(declared_type).strip().lower()
        if normalized_type not in ALLOWED_FIXED_ENTITY_COLUMN_TYPES:
            allowed_types: str = ", ".join(sorted(ALLOWED_FIXED_ENTITY_COLUMN_TYPES))
            raise FixedEntityColumnTypeDeclarationError(
                entity_name=entity_name,
                column_name=column_name,
                message=(
                    f"Entity '{entity_name}' column '{column_name}' declares unsupported type '{declared_type}'; "
                    f"allowed types: {allowed_types}"
                ),
            )

        if columns and column_name not in columns:
            raise FixedEntityColumnTypeDeclarationError(
                entity_name=entity_name,
                column_name=column_name,
                message=f"Entity '{entity_name}' column_types declares unknown column '{column_name}'",
            )

        normalized_column_types[column_name] = normalized_type

    return normalized_column_types


def resolve_fixed_entity_column_type(
    column_name: str,
    column_types: dict[str, str] | None = None,
) -> FixedEntityColumnTypeName:
    """Resolve the effective fixed-entity type name for a column."""
    if column_types and column_name in column_types:
        return column_types[column_name]

    inferred_type: type = infer_fixed_entity_column_type(column_name)
    return "int" if inferred_type is int else "string"


def resolve_fixed_entity_runtime_type(
    column_name: str,
    column_types: dict[str, str] | None = None,
) -> FixedEntityColumnTypeName | None:
    """Resolve the runtime type to enforce for a fixed-entity column.

    Runtime coercion and validation are strict for `_id` columns by default and
    for any non-`_id` column explicitly declared via `column_types`.
    Undeclared non-`_id` columns preserve their incoming scalar types.
    """
    if column_types and column_name in column_types:
        return column_types[column_name]

    inferred_type: type = infer_fixed_entity_column_type(column_name)
    return "int" if inferred_type is int else None


def is_missing_fixed_entity_value(value: Any) -> bool:
    """Return True for null-like scalar values that should normalize to None."""
    if value is None:
        return True

    if isinstance(value, str):
        return value.strip() == ""

    try:
        missing = isna(value)
    except Exception:  # pylint: disable=broad-except
        return False

    return isinstance(missing, (bool,)) and missing


def is_valid_fixed_entity_value(value: Any, target_type_name: str) -> bool:
    """Validate an already-materialized value against a fixed-entity type."""
    if is_missing_fixed_entity_value(value):
        return True

    if target_type_name == "int":
        # Intentional exact-type check: fixed `_id` validation accepts only normalized
        # plain Python ints, not bool (a subclass of int) or other int subclasses.
        return type(value) is int  # pylint: disable=unidiomatic-typecheck

    if target_type_name == "string":
        return isinstance(value, str)

    if target_type_name == "float":
        # Intentional exact-type check: float columns accept only normalized plain
        # Python float/int scalars, not bool or numeric subclasses.
        return type(value) in {float, int}  # pylint: disable=unidiomatic-typecheck

    if target_type_name == "bool":
        # Intentional exact-type check: bool columns accept only plain Python bool.
        return type(value) is bool  # pylint: disable=unidiomatic-typecheck

    if target_type_name == "date":
        if isinstance(value, datetime):
            return True
        if isinstance(value, date):
            return True
        if isinstance(value, str):
            try:
                date.fromisoformat(value)
                return True
            except ValueError:
                return False
        return False

    return False


class FixedEntityTypeValidationError(ValueError):
    """Raised when fixed-entity type coercion finds non-empty invalid values."""

    def __init__(self, *, entity_name: str, issues: list["FixedEntityTypeCoercer.CoercionIssue"]) -> None:
        self.entity_name: str = entity_name
        self.issues = issues
        msg: str = f"Entity '{entity_name}' has {len(issues)} invalid typed value(s) during coercion"
        super().__init__(msg)


class FixedEntityShapeValidationError(ValueError):
    """Raised when fixed-entity rows do not match declared column count."""


@dataclass(frozen=True)
class FixedEntityNormalizationWarning:
    """Represents a successful in-memory normalization for a fixed entity value."""

    entity_name: str
    row_index: int
    column_index: int
    column_name: str
    raw_value: Any
    normalized_value: Any
    expected_type: str


def format_fixed_entity_normalization_warning(warning: FixedEntityNormalizationWarning) -> str:
    """Format a user-facing warning for a successful fixed-entity normalization."""
    return (
        f"Entity '{warning.entity_name}', row {warning.row_index + 1}, column '{warning.column_name}': "
        f"normalized {warning.raw_value!r} to {warning.normalized_value!r} ({warning.expected_type})"
    )


class FixedEntityTypeCoercer:
    """Coerces fixed entity values to correct types based on column naming conventions."""

    @dataclass
    class CoercionIssue:
        """Represents a single type coercion failure."""

        row_index: int
        column_index: int
        column_name: str
        raw_value: Any
        expected_type: str
        reason: str

    @staticmethod
    def _was_normalized(raw_value: Any, normalized_value: Any) -> bool:
        """Check whether coercion changed either the value or its type."""
        return type(raw_value) is not type(normalized_value) or raw_value != normalized_value

    @staticmethod
    def coerce_value(value: Any, target_type: type | str) -> tuple[Any, str | None]:
        """Coerce a value to target type using strict rules.

        Returns:
            (coerced_value, error_reason)

        Coercion policy for target_type=int:
        - `None` → `None` (no error)
        - Empty string `""` → `None` (no error)
        - Integer `53` → `53` (no error)
        - String `"53"` → `53` with normalization warning possible
        - String `"53.0"` → error (reject float-like strings)
        - String `"abc"` → error (invalid format)
        - Boolean `True` or `False` → error (reject bool, even though bool is subclass of int)
        - Float `53.0` → error (reject floats)

        For target_type=str:
        - Any value is converted to string
        """
        if is_missing_fixed_entity_value(value):
            return None, None

        target_type_name = target_type if isinstance(target_type, str) else ("int" if target_type is int else "string")

        if target_type_name == "int":
            # Reject booleans first (important: bool is subclass of int in Python)
            if isinstance(value, bool):
                return value, "invalid_integer_bool_not_allowed"

            # Accept integers
            if isinstance(value, int):
                return value, None

            # Try to coerce strings
            if isinstance(value, str):
                text = value.strip()
                # Accept strings that are valid integer representations
                if text.lstrip("-").isdigit():
                    return int(text), None
                # Reject strings with decimal points
                if "." in text:
                    return value, "invalid_integer_float_format"
                return value, "invalid_integer_format"

            # Reject floats explicitly
            if isinstance(value, float):
                return value, "invalid_integer_float_not_allowed"

            # Try generic conversion for other numeric types
            try:
                return int(value), None
            except (ValueError, TypeError):
                return value, "invalid_integer"

        if target_type_name == "float":
            if isinstance(value, bool):
                return value, "invalid_float_bool_not_allowed"

            if isinstance(value, (int, float)):
                return float(value), None

            if isinstance(value, str):
                text = value.strip()
                try:
                    return float(text), None
                except ValueError:
                    return value, "invalid_float_format"

            return value, "invalid_float"

        if target_type_name == "bool":
            if isinstance(value, bool):
                return value, None

            if isinstance(value, str):
                text = value.strip().lower()
                if text == "true":
                    return True, None
                if text == "false":
                    return False, None
                return value, "invalid_bool_format"

            return value, "invalid_bool"

        if target_type_name == "date":
            if isinstance(value, datetime):
                return value.date().isoformat(), None
            if isinstance(value, date):
                return value.isoformat(), None
            if isinstance(value, str):
                text = value.strip()
                try:
                    return date.fromisoformat(text).isoformat(), None
                except ValueError:
                    return value, "invalid_date_format"

            return value, "invalid_date"

        # For string type, just convert
        return str(value), None

    @staticmethod
    def coerce_fixed_entity_values(
        entity_data: dict[str, Any],
        columns: list[str],
        entity_name: str,
    ) -> list[list[Any]]:
        """Coerce all values in a fixed entity to correct types."""
        coerced_values, _warnings = FixedEntityTypeCoercer.coerce_fixed_entity_values_with_warnings(
            entity_data,
            columns,
            entity_name,
        )
        return coerced_values

    @staticmethod
    def coerce_fixed_entity_values_with_warnings(
        entity_data: dict[str, Any],
        columns: list[str],
        entity_name: str,
    ) -> tuple[list[list[Any]], list[FixedEntityNormalizationWarning]]:
        """Coerce all values in a fixed entity to correct types.

        Implements strict precedence:
        1. Shape validation runs first (hard gate)
        2. Type coercion runs second on shape-valid rows
        3. Non-coercible non-empty values raise error

        Args:
            entity_data: Entity configuration dict (must contain 'values' key)
            columns: List of column names (defines expected column count)
            entity_name: Entity name (for error messages)

        Returns:
            Tuple of coerced values and successful normalization warnings

        Raises:
            FixedEntityShapeValidationError: If rows don't match column count
            FixedEntityTypeValidationError: If non-empty values are invalid types
        """
        values = entity_data.get("values")
        if not values or not isinstance(values, list):
            return values or [], []

        normalized_values: list[list[Any]] = []
        for row_idx, row in enumerate(values):
            if isinstance(row, list):
                normalized_values.append(row)
                continue

            if len(columns) == 1:
                normalized_values.append([row])
                continue

            raise FixedEntityShapeValidationError(
                f"Entity '{entity_name}' row {row_idx} is scalar-valued; expected a list with {len(columns)} values "
                f"based on declared columns"
            )

        # Phase 1: Shape validation (hard gate)
        for row_idx, row in enumerate(normalized_values):
            if len(row) != len(columns):
                raise FixedEntityShapeValidationError(
                    f"Entity '{entity_name}' row {row_idx} has {len(row)} values; " f"expected {len(columns)} based on declared columns"
                )

        normalized_column_types = normalize_fixed_entity_column_types(
            entity_name,
            columns,
            entity_data.get("column_types"),
        )

        # Phase 2: Type coercion
        coerced: list[list[Any]] = []
        issues: list[FixedEntityTypeCoercer.CoercionIssue] = []
        warnings: list[FixedEntityNormalizationWarning] = []

        for row_idx, row in enumerate(normalized_values):
            coerced_row: list[Any] = []
            for col_idx, value in enumerate(row):
                col_name = columns[col_idx]
                target_type_name = resolve_fixed_entity_runtime_type(col_name, normalized_column_types)

                if target_type_name is None:
                    coerced_row.append(None if is_missing_fixed_entity_value(value) else value)
                    continue

                coerced_value, error_reason = FixedEntityTypeCoercer.coerce_value(value, target_type_name)
                coerced_row.append(coerced_value)

                if error_reason is not None:
                    issues.append(
                        FixedEntityTypeCoercer.CoercionIssue(
                            row_index=row_idx,
                            column_index=col_idx,
                            column_name=col_name,
                            raw_value=value,
                            expected_type=target_type_name,
                            reason=error_reason,
                        )
                    )
                elif FixedEntityTypeCoercer._was_normalized(value, coerced_value):
                    warnings.append(
                        FixedEntityNormalizationWarning(
                            entity_name=entity_name,
                            row_index=row_idx,
                            column_index=col_idx,
                            column_name=col_name,
                            raw_value=value,
                            normalized_value=coerced_value,
                            expected_type=target_type_name,
                        )
                    )

            coerced.append(coerced_row)

        # Phase 3: Raise if any non-coercible values
        if issues:
            raise FixedEntityTypeValidationError(entity_name=entity_name, issues=issues)

        return coerced, warnings
