"""Pure domain validators for target-model-aware data conformance.

These validators check produced DataFrames against EntitySpec declarations from a target model.
They are pure functions: receive DataFrames and specs, return ValidationIssues.
No infrastructure dependencies.
"""

import pandas as pd

from src.target_model.models import EntitySpec, ForeignKeySpec
from src.validators.data_validators import ValidationIssue

# Maps target model logical types to substrings that must appear in the pandas dtype string.
_DTYPE_FAMILIES: dict[str, tuple[str, ...]] = {
    "integer": ("int",),
    "float": ("int", "float"),
    "number": ("int", "float"),
    "string": ("object", "string"),
    "text": ("object", "string"),
    "boolean": ("bool",),
    "date": ("datetime",),
    "datetime": ("datetime",),
}


class NullabilityConformanceValidator:
    """Required, non-nullable columns declared in the target model must have no nulls in produced data."""

    @staticmethod
    def validate(df: pd.DataFrame, entity_spec: EntitySpec, entity_name: str) -> list[ValidationIssue]:
        """Check that required, non-nullable columns contain no null values.

        A column is checked when its ColumnSpec has ``required=True`` and ``nullable`` is
        ``False`` or ``None`` (unspecified — required implies not-null by default).
        Columns absent from the DataFrame are skipped (structural conformance covers them).

        Args:
            df: Produced entity DataFrame.
            entity_spec: EntitySpec from the target model.
            entity_name: Entity name for error reporting.

        Returns:
            List of ValidationIssue for columns that contain nulls.
        """
        if df.empty:
            return []

        issues: list[ValidationIssue] = []
        for col_name, col_spec in entity_spec.columns.items():
            if not col_spec.required or col_spec.nullable is True:
                continue
            if col_name not in df.columns:
                continue  # structural conformance will report this separately

            null_count = int(df[col_name].isna().sum())
            if null_count > 0:
                issues.append(
                    ValidationIssue(
                        severity="error",
                        entity=entity_name,
                        field=col_name,
                        message=(
                            f"Column '{col_name}' in entity '{entity_name}' is declared required and non-nullable "
                            f"in the target model but contains {null_count} null value(s)"
                        ),
                        code="NULL_IN_REQUIRED_COLUMN",
                        suggestion=f"Fix the source data or mapping so '{col_name}' is never null.",
                        category="conformance",
                        priority="high",
                        auto_fixable=False,
                    )
                )

        return issues


class TypeCompatibilityConformanceValidator:
    """Column values must be compatible with the declared logical type in the target model."""

    @staticmethod
    def validate(df: pd.DataFrame, entity_spec: EntitySpec, entity_name: str) -> list[ValidationIssue]:
        """Check that column dtypes are compatible with declared logical types.

        Supported declared types: ``integer``, ``float``, ``number``, ``string``, ``text``,
        ``boolean``, ``date``, ``datetime``. Unknown types are silently skipped.
        Columns absent from the DataFrame are skipped (structural conformance covers them).

        Args:
            df: Produced entity DataFrame.
            entity_spec: EntitySpec from the target model.
            entity_name: Entity name for error reporting.

        Returns:
            List of ValidationIssue for columns whose dtype is incompatible with the declared type.
        """
        if df.empty:
            return []

        issues: list[ValidationIssue] = []
        for col_name, col_spec in entity_spec.columns.items():
            if not col_spec.type or col_name not in df.columns:
                continue

            declared_type = col_spec.type.lower()
            expected_families = _DTYPE_FAMILIES.get(declared_type)
            if expected_families is None:
                continue  # unknown type — skip rather than false-positive

            actual_dtype = str(df[col_name].dtype)
            if not any(family in actual_dtype for family in expected_families):
                issues.append(
                    ValidationIssue(
                        severity="warning",
                        entity=entity_name,
                        field=col_name,
                        message=(
                            f"Column '{col_name}' in entity '{entity_name}' has dtype '{actual_dtype}' "
                            f"which is incompatible with declared target model type '{col_spec.type}'"
                        ),
                        code="TYPE_INCOMPATIBLE",
                        suggestion=(
                            f"Cast '{col_name}' to a {col_spec.type}-compatible type "
                            f"in transforms or the source data."
                        ),
                        category="conformance",
                        priority="medium",
                        auto_fixable=False,
                    )
                )

        return issues


class FKReferentialIntegrityConformanceValidator:
    """FK values in produced data must exist in the parent entity's output.

    Uses target model FK specs to identify which FK relationships to check.
    The FK column name is derived from the target entity's ``public_id`` — this follows
    the Shape Shifter convention: the FK column in a child entity is named after the
    parent entity's public_id.

    Bridge-mediated FKs (``via`` attribute) are skipped: the source entity has no direct
    FK column to the ultimate target in that pattern.
    """

    @staticmethod
    def validate(
        df: pd.DataFrame,
        fk_spec: ForeignKeySpec,
        target_df: pd.DataFrame,
        target_entity_spec: EntitySpec,
        entity_name: str,
    ) -> list[ValidationIssue]:
        """Check that FK values in df exist in target_df's public_id column.

        Args:
            df: Produced source entity DataFrame.
            fk_spec: ForeignKeySpec describing the FK relationship.
            target_df: Produced target entity DataFrame.
            target_entity_spec: EntitySpec of the target entity (provides public_id column name).
            entity_name: Source entity name for error reporting.

        Returns:
            List of ValidationIssue for orphaned FK values.
        """
        if df.empty or target_df.empty:
            return []

        fk_col = target_entity_spec.public_id
        if not fk_col:
            return []  # no public_id declared — cannot infer FK column

        if fk_col not in df.columns or fk_col not in target_df.columns:
            return []  # missing columns reported elsewhere

        source_values: set = set(df[fk_col].dropna().unique())
        target_values: set = set(target_df[fk_col].dropna().unique())
        orphaned = source_values - target_values

        if not orphaned:
            return []

        sample = sorted(str(v) for v in list(orphaned)[:5])
        return [
            ValidationIssue(
                severity="warning",
                entity=entity_name,
                field=fk_col,
                message=(
                    f"{len(orphaned)} value(s) in '{entity_name}.{fk_col}' "
                    f"have no matching row in '{fk_spec.entity}.{fk_col}'"
                ),
                code="FK_REFERENTIAL_INTEGRITY",
                suggestion=(
                    f"Ensure all '{fk_col}' values in '{entity_name}' exist in '{fk_spec.entity}'. "
                    f"Sample orphaned: {', '.join(sample)}"
                ),
                category="conformance",
                priority="medium",
                auto_fixable=False,
            )
        ]
