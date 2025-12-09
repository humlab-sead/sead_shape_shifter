from typing import Any
import pandas as pd

from src.arbodat.config_model import TableConfig
from src.arbodat.extract import add_surrogate_id

from .interface import DataLoader


class FixedLoader(DataLoader):
    """Loader for fixed data entities."""

    async def load(self, entity_name: str, table_cfg: TableConfig) -> pd.DataFrame:
        """Create a fixed data entity based on configuration."""

        if not table_cfg.is_fixed_data:
            raise ValueError(f"Entity '{entity_name}' is not configured as fixed data")

        if not table_cfg.values:
            raise ValueError(f"Fixed data entity '{entity_name}' has no values defined")

        data: pd.DataFrame

        if len(table_cfg.columns or []) <= 1:
            surrogate_name: str = table_cfg.surrogate_name
            if not surrogate_name:

                if len(table_cfg.columns or []) == 0:
                    raise ValueError(f"Fixed data entity '{entity_name}' must have a surrogate_name or one column defined")

                surrogate_name = table_cfg.columns[0]
            data: pd.DataFrame = pd.DataFrame({surrogate_name: table_cfg.values})
        else:
            # Multiple columns, values is a list of rows, all having the same length as columns
            if not isinstance(table_cfg.values, list) or not all(isinstance(row, list) for row in table_cfg.values):
                raise ValueError(f"Fixed data entity '{entity_name}' with multiple columns must have values as a list of lists")

            if not all(len(row) == len(table_cfg.columns) for row in table_cfg.values):
                raise ValueError(f"Fixed data entity '{entity_name}' has mismatched number of columns and values")

            data = pd.DataFrame(table_cfg.values, columns=table_cfg.columns)

        if table_cfg.surrogate_id:
            data = add_surrogate_id(data, table_cfg.surrogate_id)

        return data


class FixedLoader2(DataLoader):
    """Loader for fixed data entities."""

    def _resolve_column_names(self, table_cfg: TableConfig) -> list[str]:
        """Determine the column names for the fixed data entity."""
        if isinstance(table_cfg.columns, list):
            return table_cfg.columns
        if isinstance(table_cfg.columns, str):
            return [table_cfg.columns]
        if table_cfg.surrogate_name:
            return [table_cfg.surrogate_name]
        if table_cfg.values and isinstance(table_cfg.values, dict):
            return list(table_cfg.values.keys())
        raise ValueError("Cannot resolve column names from fixed table configuration")
    
    def _resolve_values_dict(self, columns: list[str], values: Any) -> dict[str, list[Any]]:
        """Convert the values into a dictionary mapping column names to lists of values."""
        if isinstance(values, dict):
            # Ensure all columns are present in the dict
            for col in columns:
                if col not in values:
                    raise ValueError(f"Fixed data entity is missing values for column '{col}'")
            return values
        elif isinstance(values, list):
            if len(columns) == 1:
                return {columns[0]: values}
            else:
                raise ValueError("For multiple columns, values must be provided as a dict mapping column names to lists")
        raise ValueError("Values must be either a dict or a list")
        
    async def load(self, entity_name: str, table_cfg: TableConfig) -> pd.DataFrame:
        """Create a fixed data entity based on configuration."""

        if not table_cfg.is_fixed_data:
            raise ValueError(f"Entity '{entity_name}' is not configured as fixed data")

        if not table_cfg.values:
            raise ValueError(f"Fixed data entity '{entity_name}' has no values defined")

        data: pd.DataFrame

        # Alternative implementation
        # For each specified columns ["a", "b"], values must be a dict[str, list]
        # e.g. {"a": [1, 3], "b": [2, 4]}
        # If a single column is specified, values can be a simple list or a dict[str, list] with only that column

        columns: list[str] = self._resolve_column_names(table_cfg)

        values = self._resolve_values_dict(columns, table_cfg.values)

        if len(table_cfg.columns or []) <= 1:
            surrogate_name: str = table_cfg.surrogate_name
            if not surrogate_name:

                if len(table_cfg.columns or []) == 0:
                    raise ValueError(f"Fixed data entity '{entity_name}' must have a surrogate_name or one column defined")

                surrogate_name = table_cfg.columns[0]
            data: pd.DataFrame = pd.DataFrame({surrogate_name: table_cfg.values})
        else:
            # Multiple columns, values is a list of rows, all having the same length as columns
            if not isinstance(table_cfg.values, list) or not all(isinstance(row, list) for row in table_cfg.values):
                raise ValueError(f"Fixed data entity '{entity_name}' with multiple columns must have values as a list of lists")

            if not all(len(row) == len(table_cfg.columns) for row in table_cfg.values):
                raise ValueError(f"Fixed data entity '{entity_name}' has mismatched number of columns and values")

            data = pd.DataFrame(table_cfg.values, columns=table_cfg.columns)

        if table_cfg.surrogate_id:
            data = add_surrogate_id(data, table_cfg.surrogate_id)

        return data
