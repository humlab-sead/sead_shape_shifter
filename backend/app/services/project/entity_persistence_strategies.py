"""Entity persistence strategies for type-specific validation and normalization."""

from __future__ import annotations

from typing import Any, Protocol

import pandas as pd

from backend.app.exceptions import SchemaValidationError
from backend.app.utils.fixed_schema import build_fixed_full_columns, normalize_fixed_entity
from src.types.fixed_entity_types import (
    FixedEntityColumnTypeDeclarationError,
    FixedEntityTypeConventionDeclarationError,
    build_fixed_entity_full_columns,
    is_valid_fixed_entity_value,
    normalize_fixed_entity_column_types,
    normalize_fixed_entity_type_conventions,
    resolve_fixed_entity_runtime_type,
)


class EntityPersistenceStrategy(Protocol):
    """Strategy interface for preparing entities for persistence."""

    def prepare_for_persistence(
        self,
        entity_name: str,
        entity_data: dict[str, Any],
        project_options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:  # type: ignore[override]
        """Validate and normalize entity data before persistence."""

    def normalize_materialized_dataframe(
        self,
        entity_name: str,
        df: pd.DataFrame,
        public_id: str | None,
        keys: list[str],
    ) -> pd.DataFrame:  # type: ignore[override]
        """Normalize a materialized dataframe before fixed-entity persistence."""


class DefaultEntityPersistenceStrategy:
    """Default persistence strategy with no type-specific behavior."""

    def prepare_for_persistence(
        self,
        entity_name: str,
        entity_data: dict[str, Any],
        project_options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:  # pylint: disable=unused-argument
        return entity_data

    def normalize_materialized_dataframe(
        self,
        entity_name: str,  # pylint: disable=unused-argument
        df: pd.DataFrame,
        public_id: str | None,  # pylint: disable=unused-argument
        keys: list[str],  # pylint: disable=unused-argument
    ) -> pd.DataFrame:
        return df


class FixedEntityPersistenceStrategy:
    """Persistence strategy for fixed entities."""

    @staticmethod
    def _validate_types(entity_name: str, entity_data: dict[str, Any], project_options: dict[str, Any] | None = None) -> None:
        """Ensure fixed-entity values match declared or inferred backend types before persisting."""
        columns = entity_data.get("columns")
        if not isinstance(columns, list):
            return

        values = entity_data.get("values")
        if not isinstance(values, list) or not values:
            return

        try:
            column_types = normalize_fixed_entity_column_types(entity_name, columns, entity_data.get("column_types"))
        except FixedEntityColumnTypeDeclarationError as exc:
            raise SchemaValidationError(message=str(exc), entity=entity_name, field="column_types") from exc

        try:
            conventions = normalize_fixed_entity_type_conventions(project_options)
        except FixedEntityTypeConventionDeclarationError as exc:
            raise SchemaValidationError(message=str(exc), entity=entity_name, field="options.fixed_entity_types") from exc

        raw_keys = entity_data.get("keys")
        keys: list[str] = [key for key in raw_keys if isinstance(key, str)] if isinstance(raw_keys, list) else []
        public_id = entity_data.get("public_id") if isinstance(entity_data.get("public_id"), str) else None
        full_columns = build_fixed_entity_full_columns(columns, keys, public_id)

        for row_idx, row in enumerate(values):
            row_columns = columns if len(row) == len(columns) else full_columns

            for col_idx, value in enumerate(row):
                if value is None:
                    continue

                col_name = row_columns[col_idx]
                expected_type_name = resolve_fixed_entity_runtime_type(col_name, column_types, conventions)

                if expected_type_name is None:
                    continue

                if not is_valid_fixed_entity_value(value, expected_type_name):
                    raise SchemaValidationError(
                        message=(
                            f"Column '{col_name}' row {row_idx}: expected {expected_type_name} or null, " f"got {type(value).__name__}"
                        ),
                        entity=entity_name,
                        field="values",
                    )

    @staticmethod
    def _validate_fixed_entity_shape(
        entity_name: str,
        entity_data: dict[str, Any],
        project_options: dict[str, Any] | None = None,
    ) -> None:
        """Reject malformed fixed entities before they reach YAML persistence."""
        columns = entity_data.get("columns")
        if not isinstance(columns, list):
            return

        duplicate_columns = sorted({column for column in columns if columns.count(column) > 1})
        if duplicate_columns:
            raise SchemaValidationError(
                message=f"Fixed data entity '{entity_name}' has duplicate columns {duplicate_columns}",
                entity=entity_name,
                field="columns",
            )

        values = entity_data.get("values")
        if values is None or isinstance(values, str):
            return

        if not isinstance(values, list) or not all(isinstance(row, list) for row in values):
            raise SchemaValidationError(
                message=f"Fixed data entity '{entity_name}' must have values as a list of lists",
                entity=entity_name,
                field="values",
            )

        if not values:
            return

        row_lengths = {len(row) for row in values}
        if len(row_lengths) != 1:
            raise SchemaValidationError(
                message=f"Fixed data entity '{entity_name}' has inconsistent row lengths in values",
                entity=entity_name,
                field="values",
            )

        values_length = next(iter(row_lengths))
        public_id = entity_data.get("public_id")
        identity_columns = {"system_id"}
        if isinstance(public_id, str) and public_id:
            identity_columns.add(public_id)

        expected_without_identity = len(columns)
        expected_with_identity = len(set(columns) | identity_columns)

        if values_length not in (expected_without_identity, expected_with_identity):
            raise SchemaValidationError(
                message=(
                    f"Fixed data entity '{entity_name}' has mismatched number of columns and values "
                    f"(got {values_length} values per row, expected {expected_without_identity} for data-only "
                    f"or {expected_with_identity} with identity columns)"
                ),
                entity=entity_name,
                field="values",
            )

        FixedEntityPersistenceStrategy._validate_types(entity_name, entity_data, project_options)

    def prepare_for_persistence(
        self,
        entity_name: str,
        entity_data: dict[str, Any],
        project_options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._validate_fixed_entity_shape(entity_name, entity_data, project_options)
        return normalize_fixed_entity(entity_data)

    def normalize_materialized_dataframe(
        self,
        entity_name: str,  # pylint: disable=unused-argument
        df: pd.DataFrame,
        public_id: str | None,
        keys: list[str],
    ) -> pd.DataFrame:
        normalized_df = df.copy()

        if "system_id" not in normalized_df.columns:
            normalized_df.insert(0, "system_id", range(1, len(normalized_df) + 1))

        if public_id and public_id not in normalized_df.columns:
            normalized_df[public_id] = [None] * len(normalized_df)

        for key in keys:
            if key not in normalized_df.columns:
                normalized_df[key] = [None] * len(normalized_df)

        full_columns = build_fixed_full_columns(normalized_df.columns.tolist(), keys, public_id)
        return normalized_df.loc[:, full_columns]


class EntityPersistenceStrategyRegistry:
    """Registry for entity persistence strategies keyed by entity type."""

    def __init__(self) -> None:
        self._default_strategy: EntityPersistenceStrategy = DefaultEntityPersistenceStrategy()
        self._strategies: dict[str, EntityPersistenceStrategy] = {
            "fixed": FixedEntityPersistenceStrategy(),
        }

    def get_strategy(self, entity_data: dict[str, Any]) -> EntityPersistenceStrategy:
        entity_type = entity_data.get("type")
        return self.get_strategy_for_type(entity_type)

    def get_strategy_for_type(self, entity_type: str | None) -> EntityPersistenceStrategy:
        """Resolve a strategy directly from an entity type."""
        if isinstance(entity_type, str):
            return self._strategies.get(entity_type, self._default_strategy)
        return self._default_strategy
