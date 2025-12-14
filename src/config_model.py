from functools import cached_property
from typing import Any, Generator, Literal, Self

import pandas as pd
from loguru import logger

from src.configuration.resolve import ConfigValue
from src.utility import unique

from .loaders import DataLoader, DataLoaders


# pylint: disable=line-too-long
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


class ForeignKeyConstraints:
    """Constraints for foreign key relationships."""

    def __init__(self, data: dict[str, Any] | None = None) -> None:
        """Initialize constraints from configuration data."""
        self.data: dict[str, Any] = data or {}

    @property
    def cardinality(self) -> Literal["one_to_one", "many_to_one", "one_to_many", "many_to_many"] | None:
        """Get cardinality constraint."""
        # Cardinality constraints
        return self.data.get("cardinality")

    @property
    def allow_unmatched_left(self) -> bool | None:
        return self.data.get("allow_unmatched_left")

    @property
    def allow_unmatched_right(self) -> bool | None:
        return self.data.get("allow_unmatched_right")

    @property
    def allow_row_decrease(self) -> bool | None:
        return self.data.get("allow_row_decrease")

    @property
    def require_unique_left(self) -> bool:
        return self.data.get("require_unique_left", False)

    @property
    def require_unique_right(self) -> bool:
        return self.data.get("require_unique_right", False)

    @property
    def allow_null_keys(self) -> bool:
        return self.data.get("allow_null_keys", True)

    @property
    def is_empty(self) -> bool:
        """Check if no constraints are set."""
        return bool(self.data) is False

    @property
    def has_constraints(self) -> bool:
        return not self.is_empty

    def has_match_constraints(self) -> bool:
        return self.allow_unmatched_left is not None or self.allow_unmatched_right is not None


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
        self.config: dict[str, dict[str, Any]] = cfg  # config for all tables
        self.local_entity: str = local_entity  # name of the local entity/table
        self.local_keys: list[str] = unique(data.get("local_keys"))
        self.remote_extra_columns: dict[str, str] = self.resolve_extra_columns(data) or {}
        self.drop_remote_id: bool = data.get("drop_remote_id", False)
        self.remote_entity: str = data.get("entity", "")
        self.remote_keys: list[str] = unique(data.get("remote_keys"))
        self.how: Literal["left", "inner", "outer", "right", "cross"] = data.get("how", "inner")
        self.constraints: ForeignKeyConstraints = ForeignKeyConstraints(data.get("constraints"))

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

    @property
    def has_constraints(self) -> bool:
        return self.constraints and self.constraints.has_constraints

    def get_valid_remote_columns(self, df: pd.DataFrame) -> Any | list[str]:
        columns: list[str] = unique(self.remote_keys + list(self.remote_extra_columns.keys()))
        missing_columns: list[str] = [col for col in columns if col not in df.columns]
        if missing_columns:
            logger.warning(
                f"{self.local_entity}[linking]: Skipping extra link columns for entity '{self.local_entity}' to '{self.remote_entity}': missing remote columns {missing_columns} in remote table"
            )
            columns = [col for col in columns if col in df.columns]
        return columns

    def has_foreign_key_link(self, remote_id: str, table: pd.DataFrame) -> bool:
        """Check if the foreign key linking has already been added to the table."""
        if remote_id in table.columns:
            return True
        # FIXME: This smells like a fix for a bug elsewhere, why should we check extra columns here?
        if self.remote_extra_columns and all(col in table.columns for col in self.remote_extra_columns.values()):
            return True
        return False


class TableConfig:
    """Configuration for a database table."""

    def __init__(self, *, cfg: dict[str, dict[str, Any]], entity_name: str) -> None:
        self.config: dict[str, dict[str, Any]] = cfg
        self.entity_name: str = entity_name
        self._data: dict[str, Any] = cfg[entity_name]
        assert self._data, f"No configuration found for entity '{entity_name}'"

        self.type: Literal["fixed", "sql", "table"] | None = self._data.get("type", None)
        self.surrogate_name: str = self._data.get("surrogate_name", "")
        self.source: str | None = self._data.get("source", None)
        self.values: str | None = self._data.get("values", None)
        self.sql_query: str | None = self._data.get("query", None)
        self.surrogate_id: str = self._data.get("surrogate_id", "")
        self.check_column_names: bool = self._data.get("check_column_names", True)

        """Get the data source name for SQL data tables."""
        self.data_source: str | None = self._data.get("data_source", None)
        self.foreign_keys: list["ForeignKeyConfig"] = [
            ForeignKeyConfig(cfg=self.config, local_entity=self.entity_name, data=fk_data)
            for fk_data in self._data.get("foreign_keys", []) or []
        ]
        self.keys: set[str] = set(self._data.get("keys", []) or [])
        self.columns: list[str] = unique(self._data.get("columns"))
        self.extra_columns: dict[str, Any] = self._data.get("extra_columns", {}) or {}
        self.extra_column_names: list[str] = list(self.extra_columns.keys())
        self.drop_duplicates: bool | list[str] = self._data.get("drop_duplicates") or False
        self.drop_empty_rows: bool | list[str] | dict[str, Any] = self._data.get("drop_empty_rows", False)
        self.unnest: UnnestConfig | None = UnnestConfig(cfg=self.config, data=self._data) if self._data.get("unnest") else None

        # Parse append configuration for union operations
        self.append_configs: list[dict[str, Any]] = self._data.get("append", []) or []
        if self.append_configs and isinstance(self.append_configs, dict):
            self.append_configs = [self.append_configs]

        self.append_mode: str = self._data.get("append_mode", "all")  # "all" or "distinct"

        # Extract append source dependencies
        append_sources: set[str] = set()
        for append_cfg in self.append_configs:
            if isinstance(append_cfg.get("source"), str):
                append_sources.add(append_cfg["source"])

        self.depends_on: set[str] = (
            set(self._data.get("depends_on", []) or [])
            | ({self.source} if self.source else set())
            | {fk.remote_entity for fk in self.foreign_keys}
            | append_sources
        )
        self.replacements: dict[str, dict[Any, Any]] = self._data.get("replacements", {}) or {}
        self.filters: list[dict[str, Any]] = self._data.get("filters", []) or []
        self.options: dict[str, Any] = self._data.get("options", {}) or {}

    @property
    def query(self) -> None | str:
        """Get the SQL query string for fixed data, if applicable."""
        if self.type == "sql":
            if self.sql_query:
                return self.sql_query
            if self.values:
                # This will be deprecated, prefer 'query' over 'values' for SQL data.
                return self.values.lstrip("sql:").strip()
        return None

    @property
    def has_append(self) -> bool:
        """Check if entity has append configurations."""
        return bool(self.append_configs)

    @property
    def keys_and_columns(self) -> list[str]:
        """Get columns with keys first, followed by other columns."""
        return list(self.keys) + [col for col in self.columns if col not in self.keys]

    @property
    def unnest_columns(self) -> set[str]:
        """Get set of columns that are pending (e.g., from unnesting)."""
        if self.unnest:
            return {self.unnest.var_name, self.unnest.value_name}
        return set()

    def is_unnested(self, table: pd.DataFrame) -> bool:
        """Check if the table has been unnested based on the presence of unnest columns."""
        if not self.unnest:
            return False
        return all(col in table.columns for col in self.unnest_columns)

    @property
    def fk_columns(self) -> set[str]:
        """Get set of all foreign key columns."""
        return {col for fk in self.foreign_keys or [] for col in fk.local_keys}

    @property
    def extra_fk_columns(self) -> set[str]:
        """Get set of foreign key columns not in columns or keys."""
        extra_columns: set[str] = set()
        for fk in self.foreign_keys:
            extra_columns = extra_columns.union(set(fk.local_keys))
        return self.fk_columns - (set(self.keys_and_columns))

    @property
    def keys_columns_and_fks(self) -> list[str]:
        """Get set of all columns used in keys, columns, and foreign keys, pending unnesting columns excluded)."""
        keys_and_data_columns: list[str] = self.keys_and_columns
        return keys_and_data_columns + unique(
            list(x for x in self.fk_columns if x not in keys_and_data_columns and x not in self.unnest_columns)
        )

    def get_columns(
        self, include_keys: bool = True, include_fks: bool = True, include_extra: bool = True, include_unnest: bool = True
    ) -> list[str]:
        """Get list of columns based on inclusion criteria."""
        cols: list[str] = []
        if include_keys:
            cols.extend(list(self.keys))
        cols.extend(self.columns)
        if include_fks:
            cols.extend(list(self.fk_columns))
        if include_extra:
            cols.extend(list(self.extra_columns.keys()))
        if include_unnest and self.unnest:
            cols.extend([self.unnest.var_name, self.unnest.value_name])
        return unique(cols)

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
            # If system_id already exists, do not overwrite, it is assumed to be set correctly
            if "system_id" not in table.columns:
                table["system_id"] = table[surrogate_id]
                table[surrogate_id] = None
        return table

    def is_drop_duplicate_dependent_on_unnesting(self) -> bool:
        """Check if drop_duplicates is dependent on columns created during unnesting."""
        if not self.drop_duplicates or not self.unnest:
            return False
        if isinstance(self.drop_duplicates, list):
            return any(col in self.unnest_columns for col in self.drop_duplicates)
        return False

    def create_append_config(self, append_data: dict[str, Any]) -> dict[str, Any]:
        """Create a merged configuration for an append item, inheriting parent properties."""
        merged: dict[str, Any] = {}
        non_inheritable_keys: set[str] = {"foreign_keys", "unnest", "append", "append_mode", "depends_on"}
        all_keys: set[str] = set(self._data.keys()) | set(append_data.keys())
        special_conversions = {
            "keys": lambda v: list(v) if isinstance(v, set) else v,
        }

        for key in all_keys:

            if key in non_inheritable_keys:
                continue

            value = append_data[key] if key in append_data else self._data[key]

            if key in special_conversions and value:
                value = special_conversions[key](value)

            merged[key] = value

        return merged

    def get_sub_table_configs(self) -> Generator[Self | "TableConfig", Any, None]:
        """Yield a sequence of TableConfig objects for processing.

        Yields self first (the base configuration), then creates and yields
        a TableConfig for each append item with inherited properties.

        This allows the normalizer to treat the base table and append items
        uniformly through the same processing pipeline.

        Yields:
            TableConfig: Base config first, then one per append item
        """
        yield self

        for idx, append_data in enumerate(self.append_configs):
            append_entity_name: str = f"{self.entity_name}__append_{idx}"
            self.config[append_entity_name] = self.create_append_config(append_data)
            yield TableConfig(cfg=self.config, entity_name=append_entity_name)
            del self.config[append_entity_name]


class TablesConfig:
    """Configuration for database tables."""

    def __init__(self, *, entities_cfg: None | dict[str, dict[str, Any]] = None, options: dict[str, Any] | None = None) -> None:

        self.entities_cfg: dict[str, dict[str, Any]] = (
            entities_cfg or ConfigValue[dict[str, dict[str, Any]]]("entities", default={}).resolve() or {}
        )
        self.options: dict[str, Any]
        if options is None:
            self.options = ConfigValue[dict[str, Any]]("options", default={}).resolve() or {}
        else:
            self.options = options or {}

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

    def resolve_loader(self, table_cfg: TableConfig) -> DataLoader | None:
        """Resolve the DataLoader, if any, for the given TableConfig."""
        if table_cfg.data_source:
            data_source: DataSourceConfig = self.get_data_source(table_cfg.data_source)
            return DataLoaders.get(key=data_source.driver)(data_source=data_source)

        if table_cfg.type and table_cfg.type in DataLoaders.items:
            return DataLoaders.get(key=table_cfg.type)(data_source=None)

        return None

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
        return unique(new_column_order)

    def reorder_columns(self, table_cfg: str | TableConfig, table: pd.DataFrame) -> pd.DataFrame:
        """Reorder columns in the DataFrame to have keys first, then extra columns, then other columns."""
        if isinstance(table_cfg, str):
            table_cfg = self.get_table(entity_name=table_cfg)
        cols_to_move: list[str] = (
            (["system_id"] if "system_id" in table.columns else [])
            + [table_cfg.surrogate_id]
            + sorted([self.get_table(fk.remote_entity).surrogate_id for fk in table_cfg.foreign_keys])
            + sorted(table_cfg.extra_column_names)
        )
        existing_cols_to_move: list[str] = [col for col in cols_to_move if col in table.columns]
        other_cols: list[str] = [col for col in table.columns if col not in existing_cols_to_move]
        new_column_order: list[str] = existing_cols_to_move + sorted(other_cols)
        table = table[new_column_order]
        return table


class DataSourceConfig:
    """Configuration for data sources."""

    def __init__(self, *, cfg: None | dict[str, Any], name: str) -> None:
        self.name: str = name
        self.data_source_cfg: dict[str, Any] = cfg or {}

    @property
    def driver(self) -> str:
        return self.data_source_cfg.get("driver", "")

    @property
    def options(self) -> dict[str, Any]:
        return self.data_source_cfg.get("options", {})
