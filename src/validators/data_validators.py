"""Pure domain validators for data quality - no infrastructure dependencies.

These validators receive DataFrames and configurations as input and return validation issues.
They contain only business logic and can be used in Core, Backend, or CLI contexts.
"""

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass
class ValidationIssue:
    """Domain representation of a validation issue."""

    severity: str  # "error", "warning", "info"
    entity: str | None
    field: str | None
    message: str
    code: str
    suggestion: str | None = None
    category: str = "data"
    priority: str = "medium"
    auto_fixable: bool = False


class ColumnExistsValidator:
    """Validate that configured columns exist in DataFrame."""

    @staticmethod
    def validate(
        df: pd.DataFrame,
        configured_columns: list[str],
        entity_name: str,
        entity_config: dict[str, Any] | None = None,
    ) -> list[ValidationIssue]:
        """
        Check that all configured columns exist in DataFrame.

        For entities with unnest configuration:
        - id_vars columns MUST exist (they survive the melt)
        - var_name and value_name columns MUST exist (created by melt)
        - value_vars columns should NOT be validated (they're melted into rows)

        For entities without unnest: all configured columns must exist.

        Args:
            df: DataFrame to validate
            configured_columns: List of column names that should exist
            entity_name: Entity name for error reporting
            entity_config: Full entity configuration (optional, used to check for unnest)

        Returns:
            List of validation issues for missing columns
        """
        if not configured_columns or df.empty:
            return []

        # Get unnest configuration if present
        unnest_config = entity_config.get("unnest", {}) if entity_config else {}

        if unnest_config:
            # For unnested entities, check:
            # 1. id_vars (columns that survive melt)
            # 2. var_name and value_name (created by melt)
            # Skip value_vars (they're melted into rows)
            id_vars = unnest_config.get("id_vars", [])
            var_name = unnest_config.get("var_name")
            value_name = unnest_config.get("value_name")
            value_vars = unnest_config.get("value_vars", [])

            # Expected columns after unnest: id_vars + var_name + value_name
            expected_after_unnest = set(id_vars)
            if var_name:
                expected_after_unnest.add(var_name)
            if value_name:
                expected_after_unnest.add(value_name)

            # Only validate columns that should exist after unnest
            # (exclude value_vars from configured_columns)
            columns_to_check = [col for col in configured_columns if col not in value_vars]
        else:
            # No unnest: validate all configured columns
            columns_to_check = configured_columns

        actual_columns = set(df.columns)
        configured_set = set(columns_to_check)
        missing_columns = configured_set - actual_columns

        return [
            ValidationIssue(
                severity="error",
                entity=entity_name,
                field="columns",
                message=f"Column '{col}' is configured but does not exist in data",
                code="COLUMN_NOT_FOUND",
                suggestion=f"Remove '{col}' from columns list or fix the data source. "
                f"Available columns: {', '.join(sorted(actual_columns))}",
                category="data",
                priority="high",
                auto_fixable=False,
            )
            for col in sorted(missing_columns)
        ]


class NaturalKeyUniquenessValidator:
    """Validate that natural keys are unique in DataFrame."""

    @staticmethod
    def validate(df: pd.DataFrame, key_columns: list[str], entity_name: str) -> list[ValidationIssue]:
        """
        Check that natural keys are unique.

        Args:
            df: DataFrame to validate
            key_columns: List of column names forming the natural key
            entity_name: Entity name for error reporting

        Returns:
            List of validation issues for duplicate keys
        """
        if not key_columns or len(df) < 2:
            return []

        # Check if all key columns exist
        missing_keys = set(key_columns) - set(df.columns)
        if missing_keys:
            # Don't report here - ColumnExistsValidator will catch this
            return []

        # Check for duplicates
        duplicates = df[df.duplicated(subset=key_columns, keep=False)]

        if duplicates.empty:
            return []

        # Count unique duplicate rows
        duplicate_count = len(duplicates[key_columns].drop_duplicates())

        # Get sample duplicate values
        sample_duplicates = duplicates[key_columns].drop_duplicates().head(5)
        sample_str = ", ".join([str(tuple(row)) for _, row in sample_duplicates.iterrows()])

        return [
            ValidationIssue(
                severity="error",
                entity=entity_name,
                field="keys",
                message=f"Natural keys are not unique: {duplicate_count} duplicate key(s) found",
                code="NON_UNIQUE_KEYS",
                suggestion=f"Fix data source to ensure uniqueness. Sample duplicates: {sample_str}",
                category="data",
                priority="high",
                auto_fixable=False,
            )
        ]


class NonEmptyResultValidator:
    """Validate that DataFrame contains data."""

    @staticmethod
    def validate(df: pd.DataFrame, entity_name: str) -> list[ValidationIssue]:
        """
        Check that DataFrame is not empty.

        Args:
            df: DataFrame to validate
            entity_name: Entity name for error reporting

        Returns:
            List of validation issues if DataFrame is empty
        """
        if not df.empty:
            return []

        return [
            ValidationIssue(
                severity="warning",
                entity=entity_name,
                field=None,
                message=f"Entity '{entity_name}' returns no data",
                code="EMPTY_RESULT",
                suggestion="Check data source query or filters to ensure data is available",
                category="data",
                priority="medium",
                auto_fixable=False,
            )
        ]


class DuplicateKeysValidator:
    """Validate that configured keys don't have duplicates."""

    @staticmethod
    def validate(df: pd.DataFrame, key_columns: list[str], entity_name: str) -> list[ValidationIssue]:
        """
        Alias for NaturalKeyUniquenessValidator for backward compatibility.

        Args:
            df: DataFrame to validate
            key_columns: List of column names forming the key
            entity_name: Entity name for error reporting

        Returns:
            List of validation issues for duplicate keys
        """
        return NaturalKeyUniquenessValidator.validate(df, key_columns, entity_name)


class ForeignKeyDataValidator:
    """Validate foreign key column existence."""

    @staticmethod
    def validate(df: pd.DataFrame, fk_config: dict[str, Any], entity_name: str) -> list[ValidationIssue]:
        """
        Check that foreign key columns exist in DataFrame.

        Args:
            df: Local DataFrame to validate
            fk_config: Foreign key configuration dict with 'local_keys' and 'remote_keys'
            entity_name: Entity name for error reporting

        Returns:
            List of validation issues for missing FK columns
        """
        issues = []

        local_keys = fk_config.get("local_keys", [])
        if not local_keys:
            return []

        actual_columns = set(df.columns)
        missing_local = set(local_keys) - actual_columns

        if missing_local:
            issues.append(
                ValidationIssue(
                    severity="error",
                    entity=entity_name,
                    field="foreign_keys[].local_keys",
                    message=f"Local foreign key columns not found in data: {', '.join(sorted(missing_local))}",
                    code="FK_LOCAL_COLUMN_MISSING",
                    suggestion=f"Add missing columns to entity or fix foreign_keys configuration. "
                    f"Available columns: {', '.join(sorted(actual_columns))}",
                    category="data",
                    priority="high",
                    auto_fixable=False,
                )
            )

        return issues


class ForeignKeyIntegrityValidator:
    """Validate referential integrity of foreign keys."""

    @staticmethod
    def validate(local_df: pd.DataFrame, remote_df: pd.DataFrame, fk_config: dict[str, Any], entity_name: str) -> list[ValidationIssue]:
        """
        Check that all local FK values exist in remote entity.

        Args:
            local_df: Local DataFrame with foreign key columns
            remote_df: Remote DataFrame with referenced key columns
            fk_config: Foreign key configuration with 'local_keys', 'remote_keys', 'entity'
            entity_name: Local entity name for error reporting

        Returns:
            List of validation issues for orphaned FK values
        """
        local_keys = fk_config.get("local_keys", [])
        remote_keys = fk_config.get("remote_keys", [])
        remote_entity = fk_config.get("entity", "unknown")

        if not local_keys or not remote_keys:
            return []

        # Check columns exist
        if not all(k in local_df.columns for k in local_keys):
            return []  # FK column validator will catch this
        if not all(k in remote_df.columns for k in remote_keys):
            return []  # Remote column issue

        # Get unique local FK values (excluding nulls)
        local_fk_values = local_df[local_keys].dropna()
        if local_fk_values.empty:
            return []

        # Get unique remote key values
        remote_key_values = remote_df[remote_keys].dropna()
        if remote_key_values.empty:
            return [
                ValidationIssue(
                    severity="warning",
                    entity=entity_name,
                    field="foreign_keys[].entity",
                    message=f"Referenced entity '{remote_entity}' has no data",
                    code="FK_REMOTE_EMPTY",
                    suggestion=f"Ensure '{remote_entity}' entity returns data before validation",
                    category="data",
                    priority="medium",
                )
            ]

        # Create composite keys for comparison
        local_composite = local_fk_values.apply(tuple, axis=1) if len(local_keys) > 1 else local_fk_values[local_keys[0]]
        remote_composite = remote_key_values.apply(tuple, axis=1) if len(remote_keys) > 1 else remote_key_values[remote_keys[0]]

        # Find orphaned values
        orphaned = set(local_composite.unique()) - set(remote_composite.unique())

        if not orphaned:
            return []

        orphan_count = len(orphaned)
        sample_orphans = list(orphaned)[:5]
        sample_str = ", ".join(str(v) for v in sample_orphans)

        return [
            ValidationIssue(
                severity="warning",
                entity=entity_name,
                field="foreign_keys[].entity",
                message=f"{orphan_count} foreign key value(s) not found in '{remote_entity}'",
                code="FK_DATA_INTEGRITY",
                suggestion=f"Ensure all foreign key values exist in referenced entity. Sample missing: {sample_str}",
                category="data",
                priority="medium",
                auto_fixable=False,
            )
        ]


class DataTypeCompatibilityValidator:
    """Validate data type compatibility between foreign keys."""

    @staticmethod
    def validate(local_df: pd.DataFrame, remote_df: pd.DataFrame, fk_config: dict[str, Any], entity_name: str) -> list[ValidationIssue]:
        """
        Check that local and remote FK columns have compatible data types.

        Args:
            local_df: Local DataFrame with foreign key columns
            remote_df: Remote DataFrame with referenced key columns
            fk_config: Foreign key configuration
            entity_name: Local entity name for error reporting

        Returns:
            List of validation issues for type mismatches
        """
        issues = []

        local_keys = fk_config.get("local_keys", [])
        remote_keys = fk_config.get("remote_keys", [])
        remote_entity = fk_config.get("entity", "unknown")

        if not local_keys or not remote_keys or len(local_keys) != len(remote_keys):
            return []

        # Check columns exist
        if not all(k in local_df.columns for k in local_keys):
            return []
        if not all(k in remote_df.columns for k in remote_keys):
            return []

        for local_col, remote_col in zip(local_keys, remote_keys):
            local_dtype = str(local_df[local_col].dtype)
            remote_dtype = str(remote_df[remote_col].dtype)

            # Simple compatibility check - pandas is flexible but warn on obvious mismatches
            # int64 vs float64 is OK, but int64 vs object might be problematic
            local_numeric = "int" in local_dtype or "float" in local_dtype
            remote_numeric = "int" in remote_dtype or "float" in remote_dtype

            if local_numeric != remote_numeric:
                issues.append(
                    ValidationIssue(
                        severity="warning",
                        entity=entity_name,
                        field="foreign_keys[].local_keys",
                        message=f"Type mismatch: '{local_col}' ({local_dtype}) vs '{remote_entity}.{remote_col}' ({remote_dtype})",
                        code="FK_TYPE_MISMATCH",
                        suggestion="Consider converting data types to match or verify join will work correctly",
                        category="data",
                        priority="low",
                        auto_fixable=False,
                    )
                )

        return issues
