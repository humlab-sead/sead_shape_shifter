from typing import TYPE_CHECKING, Any

import pandas as pd
from loguru import logger

from src.loaders.base_loader import ConnectTestResult
from src.transforms.utility import add_system_id
from src.types.fixed_entity_types import FixedEntityTypeCoercer

from .base_loader import DataLoader, DataLoaders, LoaderType

if TYPE_CHECKING:
    from src.model import TableConfig


@DataLoaders.register(key=["fixed"])
class FixedLoader(DataLoader):
    """Loader for fixed data entities."""

    @classmethod
    def loader_type(cls) -> LoaderType:
        """Get the loader type."""
        return LoaderType.VALUE

    async def load(self, entity_name: str, table_cfg: "TableConfig") -> pd.DataFrame:
        """Create a fixed data entity based on configuration."""

        self.validate(entity_name, table_cfg)

        data: pd.DataFrame
        raw_values: list[Any] | None = table_cfg.values if isinstance(table_cfg.values, list) else None

        if raw_values and isinstance(raw_values[0], dict):
            # Values came from @load: directive - normalize to fixed-safe row values first.
            resolved_columns: list[str] = table_cfg.columns or list(raw_values[0].keys())
            values = [[row.get(column) for column in resolved_columns] for row in raw_values]
            coerced_values = self._coerce_loaded_values(entity_name, table_cfg, resolved_columns, values)
            data = pd.DataFrame(coerced_values, columns=resolved_columns)
        else:
            values: list[list[Any]] = table_cfg.safe_values
            columns: list[str] = table_cfg.columns

            if len(columns) == 0 and len(values) == 0:
                logger.warning(f"Fixed data entity '{entity_name}' has no columns or values defined, returning empty DataFrame")
                return pd.DataFrame()

            resolved_columns: list[str] = self._resolve_columns_for_values(entity_name, table_cfg, columns, values)
            coerced_values = self._coerce_loaded_values(entity_name, table_cfg, resolved_columns, values)

            try:
                data = pd.DataFrame(coerced_values, columns=resolved_columns)
            except ValueError as exc:
                raise ValueError(f"Fixed data entity '{entity_name}' failed to build DataFrame: {exc}") from exc

        # Add system_id if configured (always "system_id" column name)
        if table_cfg.system_id and table_cfg.system_id not in data.columns:
            data = add_system_id(data, table_cfg.system_id)

        return data

    @staticmethod
    def _coerce_loaded_values(
        entity_name: str,
        table_cfg: "TableConfig",
        columns: list[str],
        values: list[list[Any]],
    ) -> list[list[Any]]:
        """Normalize loaded fixed values before building the DataFrame."""
        if not values:
            return values

        return FixedEntityTypeCoercer.coerce_fixed_entity_values(
            {
                "values": values,
                "column_types": table_cfg.column_types,
            },
            columns,
            entity_name,
            table_cfg.fixed_entity_type_conventions,
        )

    def validate(self, entity_name: str, table_cfg: "TableConfig") -> None:
        """Validate the fixed data entity configuration."""
        from src.specifications.entity import FixedEntityFieldsSpecification  # pylint: disable=import-outside-toplevel

        spec = FixedEntityFieldsSpecification({"metadata": {}, "entities": table_cfg.entities_cfg, "options": table_cfg.project_options})
        is_valid: bool = spec.is_satisfied_by(entity_name=table_cfg.entity_name)

        if not is_valid:
            raise ValueError(f"Table '{entity_name}' failed validation {spec.get_report()}.")

    @staticmethod
    def _resolve_columns_for_values(
        entity_name: str,
        table_cfg: "TableConfig",
        columns: list[str],
        values: list[list[Any]],
    ) -> list[str]:
        """Resolve effective fixed-value columns and validate shape with entity-aware errors."""

        if not values:
            return columns

        row_length: int = len(values[0])
        if not all(len(row) == row_length for row in values):
            raise ValueError(f"Fixed data entity '{entity_name}' has inconsistent row lengths in values")

        identity_columns: list[str] = []
        if table_cfg.system_id not in columns:
            identity_columns.append(table_cfg.system_id)
        if table_cfg.public_id and table_cfg.public_id not in columns:
            identity_columns.append(table_cfg.public_id)

        columns_with_identity: list[str] = identity_columns + columns

        if row_length == len(columns):
            return columns

        if row_length == len(columns_with_identity):
            return columns_with_identity

        raise ValueError(
            f"Fixed data entity '{entity_name}' has mismatched number of values per row "
            f"(got {row_length}, expected {len(columns)} for data-only rows or {len(columns_with_identity)} with identity columns)"
        )

    async def test_connection(self) -> ConnectTestResult:
        return ConnectTestResult.create_empty(success=True)
