from functools import cached_property
from typing import Any, Literal

import pandas as pd

from src.configuration.resolve import ConfigValue
from src.utility import dotget


class UnnestConfig:
    """Configuration for unnesting a column."""

    def __init__(self, *, cfg: dict[str, dict[str, Any]], data: dict[str, Any]) -> None:
        unnest_data = data.get("unnest", {})
        self.config: dict[str, dict[str, Any]] = cfg
        self.id_vars: list[str] = unnest_data.get("id_vars", []) or []
        self.value_vars: list[str] = unnest_data.get("value_vars", []) or []
        self.var_name: str = unnest_data.get("var_name", "") or ""
        self.value_name: str = unnest_data.get("value_name", "") or ""

        if not self.var_name or not self.value_name:
            raise ValueError(f"Invalid unnest configuration: {data}")


class ForeignKeyConfig:
    """Configuration for a foreign key."""

    def __init__(self, *, cfg: dict[str, dict[str, Any]], local_entity: str, data: dict[str, Any]) -> None:
        """Initialize ForeignKeyConfig with configuration data.
        Args:
            cfg (dict): Full configuration dictionary.
            local_entity (str): Name of the local entity/table.
            data (dict): Foreign key configuration data.
        Raises:
            ValueError: If required fields are missing or invalid."""
        self.config: dict[str, dict[str, Any]] = cfg  # full config
        self.local_entity: str = local_entity
        self.local_keys: list[str] = data.get("local_keys", []) or []
        self.remote_extra_columns: dict[str, str] = self.resolve_extra_columns(data) or {}
        self.drop_remote_id: bool = data.get("drop_remote_id", False)
        self.remote_entity: str = data.get("entity", "")
        self.remote_keys: list[str] = data.get("remote_keys", []) or []
        self.how: Literal["left", "inner", "outer", "right", "cross"] = data.get("how", "inner")

        if not self.remote_entity:
            raise ValueError(f"Invalid foreign key configuration for entity '{local_entity}': missing remote entity")

        if self.remote_entity not in cfg:
            raise ValueError(f"Foreign key references unknown entity '{self.remote_entity}' from '{local_entity}'")

        self.remote_surrogate_id: str = cfg[self.remote_entity].get("surrogate_id", "")

        if self.how != "cross":
            if not self.local_keys or not self.remote_keys:
                raise ValueError(f"Invalid foreign key configuration for entity '{local_entity}': missing local and/or remote keys")
            if len(self.local_keys) != len(self.remote_keys):
                raise ValueError(
                    f"Foreign key configuration mismatch for entity '{local_entity}': number of local keys ({len(self.local_keys)}) does not match number of remote keys ({len(self.remote_keys)})"
                )

    def resolve_extra_columns(self, data: dict[str, Any]) -> dict[str, str]:
        """Resolve extra columns for the foreign key configuration.

        The mapping is defined as "ExtraColumn": "SurveyColumn" in the configuration.
        This function inverts that mapping to "SurveyColumn": "ExtraColumn" for easier lookup during processing.

        Args:
            data (dict): Foreign key configuration data.
        Returns:
            dict: Resolved extra columns mapping local column names to remote column names.
        """
        cfg_value: str | list[str] | dict[str, str] = data.get("extra_columns", {}) or {}

        if not cfg_value:
            return {}

        if isinstance(cfg_value, str):
            cfg_value = {cfg_value: cfg_value}

        if isinstance(cfg_value, list):
            # Use an identity mapping
            cfg_value = {col: col for col in cfg_value}

        if not isinstance(cfg_value, dict):
            raise ValueError(f"Invalid extra_columns format in FK config for '{self.local_entity}'")

        return {v: k for k, v in cfg_value.items()}  # invert mapping


class TableConfig:
    """Configuration for a database table."""

    def __init__(self, *, cfg: dict[str, dict[str, Any]], entity_name: str) -> None:
        self.config: dict[str, dict[str, Any]] = cfg
        self.entity_name: str = entity_name
        self.data: dict[str, Any] = cfg[entity_name]
        assert self.data, f"No configuration found for entity '{entity_name}'"

    @property
    def source(self) -> str | None:
        return self.data.get("source", None)

    @property
    def surrogate_id(self) -> str:
        return self.data.get("surrogate_id", "")

    @property
    def surrogate_name(self) -> str:
        """Specifies name field for surrogate id, if any. Ony used for fixed data tables."""
        return self.data.get("surrogate_name", "")

    @property
    def is_fixed_data(self) -> bool:
        """Checks if the table is of fixed data type.
        The fixed data type is specified by setting 'type' to 'fixed' in the table configuration.
        This data type indicates that the table contains fixed values rather than dynamic data fetched from source.
        The values are specified in the 'source' field of the configuration.
        The columns of the table are defined in the 'columns' field.
        The surrogate_id field specifies the primary key for the table.
        """
        return self.data.get("type", "data") == "fixed"

    @property
    def is_sql_data(self) -> bool:
        return self.data.get("type", "data") == "sql"

    @property
    def fixed_sql(self) -> None | str:
        """Get the SQL query string for fixed data, if applicable."""
        if self.is_sql_data:
            assert isinstance(self.values, str)
            return self.values.lstrip("sql:").strip()
        return None

    @property
    def data_source(self) -> str | None:
        """Get the data source name for SQL data tables."""
        return self.data.get("data_source", None)

    @property
    def values(self) -> str | None:
        """The fixed values for the table, if it is of fixed data type.
        These values are specified in the 'values' field of the configuration.
        The values will be used to populate the table (pd.DataFrame).
        """
        return self.data.get("values", None)

    @cached_property
    def foreign_keys(self) -> list["ForeignKeyConfig"]:
        return [ForeignKeyConfig(cfg=self.config, local_entity=self.entity_name, data=fk_data) for fk_data in self.data.get("foreign_keys", []) or []]

    def get_foreign_key_names(self) -> list[str]:
        return [self.config[fk.remote_entity].get("surrogate_id", "") for fk in self.foreign_keys]

    @property
    def keys(self) -> list[str]:
        return self.data.get("keys", []) or []

    @property
    def columns(self) -> list[str]:
        return self.data.get("columns", []) or []

    @property
    def extra_columns(self) -> dict[str, Any]:
        return self.data.get("extra_columns", {}) or {}

    @property
    def extra_column_names(self) -> list[str]:
        return list(self.extra_columns.keys())

    @property
    def columns2(self) -> list[str]:
        """Get columns with keys first, followed by other columns."""
        return self.keys + [col for col in self.columns if col not in self.keys]

    @property
    def data_columns(self) -> list[str]:
        """Get data columns excluding keys, foreign keys, and extra columns."""
        return [col for col in self.columns if col not in self.keys and col not in self.fk_column_set and not col in self.extra_columns]

    @property
    def drop_duplicates(self) -> bool | list[str]:
        value = self.data.get("drop_duplicates", False)
        return value if value else False

    @property
    def drop_empty_rows(self) -> bool:
        return self.data.get("drop_empty_rows", False)

    @property
    def unnest(self) -> UnnestConfig | None:
        """Get unnest configuration if it exists."""
        if "unnest" in self.data:
            return UnnestConfig(cfg=self.config, data=self.data)
        return None

    @property
    def pending_columns(self) -> set[str]:
        """Get set of columns that are pending (e.g., from unnesting)."""
        if self.unnest:
            return {self.unnest.var_name}
        return set()

    @property
    def depends_on(self) -> list[str]:
        return (self.data.get("depends_on", []) or []) + ([self.source] if self.source else [])

    @property
    def fk_column_set(self) -> set[str]:
        """Get set of all foreign key columns."""
        return {col for fk in self.foreign_keys or [] for col in fk.local_keys}

    @property
    def extra_fk_columns(self) -> set[str]:
        # FIXME: remove since only used by tests
        """Get set of foreign key columns not in columns or keys."""
        extra_columns: set[str] = set()
        for fk in self.foreign_keys:
            extra_columns = extra_columns.union(set(fk.local_keys))
        return self.fk_column_set - (set(self.columns2))

    @property
    def usage_columns(self) -> list[str]:
        """Get set of all columns used in keys, columns, and foreign keys, pending unnesting columns excluded)."""
        keys_and_data_columns: list[str] = self.columns2
        return keys_and_data_columns + list(x for x in self.fk_column_set if x not in keys_and_data_columns and x not in self.pending_columns)

    def drop_fk_columns(self, table: pd.DataFrame) -> pd.DataFrame:
        """Drop foreign key columns used for linking that are no longer needed after linking. Keep if in columns list."""
        columns: list[str] = self.columns or []
        foreign_keys: list[ForeignKeyConfig] = self.foreign_keys or []
        fk_columns: set[str] = set()
        for fk in foreign_keys:
            local_keys: list[str] = fk.local_keys or []
            fk_columns.update(key for key in local_keys if key not in columns)
        if fk_columns:
            table = table.drop(columns=fk_columns, errors="ignore")
        return table

    def add_system_id_column(self, table: pd.DataFrame) -> pd.DataFrame:
        """Add a 'system_id' column with the same values as the surrogate_id column, then set surrogate_id to None."""
        surrogate_id: str = self.surrogate_id
        if surrogate_id and surrogate_id in table.columns:
            table["system_id"] = table[surrogate_id]
            table[surrogate_id] = None
        return table


class TablesConfig:
    """Configuration for database tables."""

    def __init__(self, *, entities_cfg: None | dict[str, dict[str, Any]] = None, options: dict[str, Any] | None = None) -> None:

        self.entities_cfg: dict[str, dict[str, Any]] = entities_cfg or ConfigValue[dict[str, dict[str, Any]]]("entities", default={}).resolve() or {}
        self.options: dict[str, Any] = options or ConfigValue[dict[str, Any]]("options", default={}).resolve() or {}

        self.tables: dict[str, TableConfig] = {key: TableConfig(cfg=self.entities_cfg, entity_name=key) for key in self.entities_cfg.keys()}
        self.data_sources: dict[str, Any] = self.options.get("data_sources", {})

    def get_table(self, entity_name: str) -> "TableConfig":
        return self.tables[entity_name]

    def has_table(self, entity_name: str) -> bool:
        return entity_name in self.tables

    def get_data_source(self, name: str) -> "DataSourceConfig":
        if name not in self.data_sources:
            raise ValueError(f"Data source 'options.data_sources.{name}' not found in configuration")
        return DataSourceConfig(cfg=self.data_sources[name], name=name)

    @cached_property
    def table_names(self) -> list[str]:
        return list(self.tables.keys())

    def get_sorted_columns(self, entity_name: str) -> list[str]:
        """Return a list of columns with all keys in front of other columns."""
        table: TableConfig = self.get_table(entity_name)
        cols_to_move: list[str] = [table.surrogate_id] + [self.get_table(fk.remote_entity).surrogate_id for fk in table.foreign_keys]
        existing_cols_to_move: list[str] = [col for col in cols_to_move if col in table.columns]
        other_cols: list[str] = [col for col in table.columns if col not in existing_cols_to_move]
        new_column_order: list[str] = existing_cols_to_move + other_cols
        return new_column_order

    def reorder_columns(self, table_cfg: str | TableConfig, table: pd.DataFrame) -> pd.DataFrame:
        """Reorder columns in the DataFrame to have keys first, then extra columns, then other columns."""
        if isinstance(table_cfg, str):
            table_cfg = self.get_table(entity_name=table_cfg)
        cols_to_move: list[str] = (
            (["system_id"] if "system_id" in table.columns else [])
            + [table_cfg.surrogate_id]
            + [self.get_table(fk.remote_entity).surrogate_id for fk in table_cfg.foreign_keys]
            + table_cfg.extra_column_names
        )
        existing_cols_to_move: list[str] = [col for col in cols_to_move if col in table.columns]
        other_cols: list[str] = [col for col in table.columns if col not in existing_cols_to_move]
        new_column_order: list[str] = existing_cols_to_move + other_cols
        table = table[new_column_order]
        return table


class DataSourceConfig:
    """Configuration for data sources."""

    def __init__(self, *, cfg: None | dict[str, Any], name: str) -> None:
        self.data_source_cfg: dict[str, Any] = cfg or {}

    @property
    def driver(self) -> str:
        return self.data_source_cfg.get("driver", "")

    @property
    def options(self) -> dict[str, Any]:
        return self.data_source_cfg.get("options", {})
