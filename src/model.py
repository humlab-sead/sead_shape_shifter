import copy
from functools import cached_property
from typing import Any, Generator, Literal, Self

import pandas as pd
import xxhash
from loguru import logger

from src.configuration import ConfigFactory, ConfigLike
from src.configuration.config import Config, is_config_path
from src.loaders.base_loader import DataLoader, DataLoaders
from src.utility import dotget, unique


# pylint: disable=line-too-long
class UnnestConfig:
    """Configuration for unnesting a column. Wraps unnest setting from table config."""

    def __init__(self, *, data: dict[str, Any]) -> None:
        self.data = data.get("unnest", {})

        if not self.var_name or not self.value_name:
            raise ValueError(f"Invalid unnest configuration (missing var_name or value_name): {data}")

    @property
    def id_vars(self) -> list[str]:
        return self.data.get("id_vars", []) or []

    @property
    def value_vars(self) -> list[str]:
        return self.data.get("value_vars", []) or []

    @property
    def var_name(self) -> str:
        return self.data.get("var_name", "") or ""

    @property
    def value_name(self) -> str:
        return self.data.get("value_name", "") or ""


class ForeignKeyConstraints:
    """Constraints for foreign key relationships. Read-Only. Wraps constraints setting from foreign key config."""

    def __init__(self, data: dict[str, Any] | None = None) -> None:
        """Initialize constraints from configuration data."""
        self.data: dict[str, Any] = data or {}

    @property
    def cardinality(self) -> Literal["one_to_one", "many_to_one", "one_to_many", "many_to_many"] | None:
        """Get cardinality constraint."""
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
    """Configuration for a foreign key. Read-Only. Wraps foreign key setting from table config."""

    def __init__(self, *, local_entity: str, fk_cfg: dict[str, Any]) -> None:
        """Initialize ForeignKeyConfig with configuration data.
        Args:
            local_entity (str): Name of the local entity/table.
            fk_cfg (dict): Foreign key configuration data.
        Raises:
            ValueError: If required fields are missing or invalid."""
        self.fk_cfg: dict[str, Any] = fk_cfg
        self.local_entity: str = local_entity

    @property
    def local_keys(self) -> list[str]:
        return unique(self.fk_cfg.get("local_keys"))

    @property
    def extra_columns(self) -> dict[str, Any]:
        """Get extra columns {"new-column-name" -> value } mapping from configuration."""
        return self.fk_cfg.get("extra_columns", {}) or {}

    @property
    def drop_remote_id(self) -> bool:
        return self.fk_cfg.get("drop_remote_id", False)

    @property
    def remote_entity(self) -> str:
        return self.fk_cfg.get("entity", "")

    @cached_property
    def remote_keys(self) -> list[str]:
        return unique(self.fk_cfg.get("remote_keys"))

    @cached_property
    def how(self) -> Literal["left", "inner", "outer", "right", "cross"]:
        return self.fk_cfg.get("how", "inner")

    @cached_property
    def constraints(self) -> ForeignKeyConstraints:
        return ForeignKeyConstraints(self.fk_cfg.get("constraints"))

    def resolved_extra_columns(self) -> dict[str, str]:
        """Resolve extra columns for the foreign key configuration.

        The mapping returned by `extra_columns` is defined as "ExtraColumn": "ExistingColumn" in the configuration.
        This function inverts that mapping to "ExistingColumn": "ExtraColumn" for easier lookup during processing.

        Args:
            data (dict): Foreign key configuration data.
        Returns:
            dict: Resolved extra columns mapping local column names to remote column names.
        """

        cfg_value: str | list[str] | dict[str, str] = self.extra_columns

        if not cfg_value:
            return {}

        if isinstance(cfg_value, str):
            cfg_value = {str(cfg_value): cfg_value}

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
        extra_columns: dict[str, str] = self.resolved_extra_columns()
        columns: list[str] = unique(self.remote_keys + list(extra_columns.keys()))
        missing_columns: list[str] = [col for col in columns if col not in df.columns]
        if missing_columns:
            logger.warning(
                f"{self.local_entity}[linking]: Skipping extra link columns for entity "
                f"'{self.local_entity}' to '{self.remote_entity}': missing remote columns {missing_columns} in remote table"
            )
            columns = [col for col in columns if col in df.columns]
        return columns

    def has_foreign_key_link(self, remote_id: str, table: pd.DataFrame) -> bool:
        """Check if the foreign key linking has already been added to the table."""
        if remote_id in table.columns:
            return True
        extra_columns: dict[str, str] = self.resolved_extra_columns()
        if extra_columns and all(col in table.columns for col in extra_columns.values()):
            return True
        return False


class TableConfig:
    """Configuration for a database table. Read-Only. Wraps table setting from entities config."""

    def __init__(self, *, entities_cfg: dict[str, dict[str, Any]], entity_name: str) -> None:

        self.entities_cfg: dict[str, dict[str, Any]] = entities_cfg
        self.entity_name: str = entity_name
        self.entity_cfg: dict[str, Any] = entities_cfg[entity_name]

        assert self.entity_cfg, f"No configuration found for entity '{entity_name}'"

    @property
    def type(self) -> Literal["fixed", "sql", "table"] | None:
        return self.entity_cfg.get("type", None)

    @property
    def surrogate_name(self) -> str:
        return self.entity_cfg.get("surrogate_name", "")

    @property
    def source(self) -> str | None:
        return self.entity_cfg.get("source", None)

    @property
    def values(self) -> str | list[Any] | None:
        return self.entity_cfg.get("values", None)

    @property
    def safe_values(self) -> list[list[Any]]:
        """Returns values as a list of lists."""
        values: str | list[Any] = self.values if isinstance(self.values, list) else []
        if all(isinstance(row, list) for row in values):
            return values
        return [[v] for v in values]

    @property
    def sql_query(self) -> str | None:
        return self.entity_cfg.get("query", None)

    @property
    def surrogate_id(self) -> str:
        return self.entity_cfg.get("surrogate_id", "")

    @property
    def check_column_names(self) -> bool:
        return self.entity_cfg.get("check_column_names", True)

    @property
    def auto_detect_columns(self) -> bool:
        return self.entity_cfg.get("auto_detect_columns", False)

    @property
    def data_source(self) -> str | None:
        return self.entity_cfg.get("data_source", None)

    @property
    def keys(self) -> set[str]:
        return set(self.entity_cfg.get("keys", []) or [])

    @property
    def columns(self) -> list[str]:
        return unique(self.entity_cfg.get("columns"))

    @property
    def safe_columns(self) -> list[str]:
        """Return the list of columns converting to a list if necessary."""
        columns: str | list[Any] = self.columns or []
        if isinstance(columns, str):
            columns = [columns]
        return columns

    @columns.setter
    def columns(self, value: list[str]) -> None:
        """Set columns list. Used to update columns after auto-detection. Not persistent."""
        self.entity_cfg["columns"] = value

    @property
    def extra_columns(self) -> dict[str, Any]:
        return self.entity_cfg.get("extra_columns", {}) or {}

    @property
    def extra_column_names(self) -> list[str]:
        return list(self.extra_columns.keys())

    @property
    def drop_duplicates(self) -> bool | list[str]:
        return self.entity_cfg.get("drop_duplicates") or False

    @property
    def drop_empty_rows(self) -> bool | list[str] | dict[str, Any]:
        return self.entity_cfg.get("drop_empty_rows", False)

    @property
    def unnest(self) -> UnnestConfig | None:
        return UnnestConfig(data=self.entity_cfg) if self.entity_cfg.get("unnest") else None

    @cached_property
    def depends_on(self) -> set[str]:
        """Get set of entities this table depends on."""
        append_sources: set[str] = set()
        for append_cfg in self.append_configs:
            if isinstance(append_cfg.get("source"), str):
                append_sources.add(append_cfg["source"])

        return (
            set(self.entity_cfg.get("depends_on", []) or [])
            | ({self.source} if self.source else set())
            | {fk.remote_entity for fk in self.foreign_keys}
            | append_sources
        )

    @cached_property
    def foreign_keys(self) -> list[ForeignKeyConfig]:
        return [
            ForeignKeyConfig(local_entity=self.entity_name, fk_cfg=fk_data) for fk_data in self.entity_cfg.get("foreign_keys", []) or []
        ]

    @cached_property
    def append_configs(self) -> list[dict[str, Any]]:
        # Parse append configuration for union operations
        value: list[dict[str, Any]] = self.entity_cfg.get("append", []) or []
        if value and isinstance(value, dict):
            value = [value]
        return value

    @property
    def query(self) -> None | str:
        """Get the SQL query string for fixed data, if applicable."""
        if self.type == "sql":
            if self.sql_query:
                return self.sql_query
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

    @property
    def append_mode(self) -> str:
        return self.entity_cfg.get("append_mode", "all")  # "all" or "distinct"

    @property
    def replacements(self) -> dict[str, dict[Any, Any]]:
        return self.entity_cfg.get("replacements", {}) or {}

    @property
    def filters(self) -> list[dict[str, Any]]:
        return self.entity_cfg.get("filters", []) or []

    @property
    def options(self) -> dict[str, Any]:
        return self.entity_cfg.get("options", {}) or {}

    def is_unnested(self, table: pd.DataFrame) -> bool:
        """Check if the table has been unnested based on the presence of unnest columns."""
        if not self.unnest:
            return False
        return all(col in table.columns for col in self.unnest_columns)

    @property
    def fk_columns(self) -> set[str]:
        """Get set of all foreign key columns."""
        return {col for fk in self.foreign_keys or [] for col in fk.local_keys}

    @cached_property
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
        """Add a `system_id` column to `table` with the same values as the `surrogate_id` column, then set `surrogate_id` to None."""
        surrogate_id: str = self.surrogate_id
        if surrogate_id and surrogate_id in table.columns:
            # If system_id already exists, do not overwrite, it is assumed to be set correctly
            if "system_id" not in table.columns:
                table["system_id"] = table[surrogate_id]
                table[surrogate_id] = None
        return table

    def is_drop_duplicate_dependent_on_unnesting(self) -> bool:
        """Check if `drop_duplicates` is dependent on columns created during unnesting."""
        if not self.drop_duplicates or not self.unnest:
            return False
        if isinstance(self.drop_duplicates, list):
            return any(col in self.unnest_columns for col in self.drop_duplicates)
        return False

    def create_append_config(self, append_data: dict[str, Any]) -> dict[str, Any]:
        """Create a merged configuration for an append item, inheriting parent properties."""
        merged: dict[str, Any] = {}
        non_inheritable_keys: set[str] = {"foreign_keys", "unnest", "append", "append_mode", "depends_on"}
        all_keys: set[str] = set(self.entity_cfg.keys()) | set(append_data.keys())
        special_conversions = {
            "keys": lambda v: list(v) if isinstance(v, set) else v,
        }

        for key in all_keys:

            if key in non_inheritable_keys:
                continue

            value = append_data[key] if key in append_data else self.entity_cfg[key]

            if key in special_conversions and value:
                value = special_conversions[key](value)

            merged[key] = value

        return merged

    def get_sub_table_configs(self) -> Generator[Self | "TableConfig", Any, None]:
        """Yield a sequence of TableConfig objects for processing.

        Yields self first (the base configuration), then creates and yields
        a TableConfig for each append item with inherited properties.

        This allows the shapeshifter to treat the base table and append items
        uniformly through the same processing pipeline.

        Yields:
            TableConfig: Base config first, then one per append item
        """
        yield self

        for idx, append_data in enumerate(self.append_configs):
            append_entity_name: str = f"{self.entity_name}__append_{idx}"
            self.entities_cfg[append_entity_name] = self.create_append_config(append_data)
            yield TableConfig(entities_cfg=self.entities_cfg, entity_name=append_entity_name)
            del self.entities_cfg[append_entity_name]

    def get_key_columns(self) -> set[str]:
        key_columns = set(self.keys or [])
        if self.surrogate_id:
            key_columns.add(self.surrogate_id)
        return key_columns

    def hash(self) -> str:
        """Compute a hash of the metadata for change detection."""
        metadata_str = str(sorted(self.entity_cfg.items()))
        return xxhash.xxh64(metadata_str.encode()).hexdigest()


class Metadata:
    """Configuration metadata. Read-Only. Wraps metadata section from configuration."""

    def __init__(self, data: dict[str, Any] | None = None) -> None:
        """Initialize metadata from configuration data."""
        self.data: dict[str, Any] = data or {}

    @property
    def name(self) -> str:
        """Configuration name."""
        return self.data.get("name", "Unnamed Configuration")

    @property
    def description(self) -> str:
        """Configuration description."""
        return self.data.get("description", "")

    @property
    def version(self) -> str:
        """Configuration version."""
        return self.data.get("version", "1.0.0")

    @property
    def default_entity(self) -> str | None:
        """Configuration version."""
        return self.data.get("default_entity")  # e.g. "survey"


class ShapeShiftProject:
    """Project configuration for database tables. Read-Only. Wraps overall project configuration."""

    def __init__(self, *, cfg: dict[str, dict[str, Any]], filename: str | None = None) -> None:

        if "entities" not in cfg or not isinstance(cfg["entities"], dict):
            raise ValueError("Invalid project configuration: 'entities' section is missing or not a dictionary.")

        self.cfg: dict[str, dict[str, Any]] = cfg
        self.filename: str = filename or "in-memory-config.yml"

    @cached_property
    def tables(self) -> dict[str, TableConfig]:
        return {key: TableConfig(entities_cfg=self.entities, entity_name=key) for key in self.entities.keys()}

    @property
    def metadata(self) -> Metadata:
        """Get configuration metadata."""
        return Metadata(self.cfg.get("metadata", {}))

    @property
    def entities(self) -> dict[str, dict[str, Any]]:
        return self.cfg.get("entities", {}) or {}

    @property
    def options(self) -> dict[str, Any]:
        return self.cfg.get("options", {}) or {}

    @property
    def data_sources(self) -> dict[str, dict[str, Any]]:
        return self.options.get("data_sources", {}) or {}

    @property
    def translations(self) -> dict[str, dict[str, str]]:
        return self.options.get("translations", {}) or {}

    @property
    def mappings(self) -> dict[str, dict[str, str]]:
        return self.options.get("mappings", {}) or {}

    def get_table(self, entity_name: str) -> "TableConfig":
        if entity_name not in self.tables:
            raise KeyError(f"Table 'entities.{entity_name}' not found in configuration")
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

    def clone(self) -> "ShapeShiftProject":
        """Create a deep copy of the ShapeShiftProject."""
        return ShapeShiftProject(cfg=copy.deepcopy(self.cfg), filename=self.filename)

    def resolve(self, **context) -> "ShapeShiftProject":
        """Resolve and return a new ShapeShiftProject instance."""
        return ShapeShiftProject(
            cfg=Config.resolve_references(
                self.cfg,
                env_filename=dotget(context, "env_filename, env_file"),
                env_prefix=dotget(context, "env_prefix"),
                source_path=dotget(context, "filename, file_path") or self.filename,
                inplace=False,
            ),
            filename=context.get("filename") or self.filename,
        )

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

    @staticmethod
    def from_file(filename: str, env_file: str = ".env", env_prefix: str = "SEAD_NORMALIZER") -> "ShapeShiftProject":
        """Load ShapeShiftProject from a YAML project file."""

        cfg: ConfigLike = ConfigFactory().load(
            source=filename,
            context="shape_shifter",
            env_filename=env_file,
            env_prefix=env_prefix,
        )

        return ShapeShiftProject(cfg=cfg.data, filename=filename)

    @staticmethod
    def from_source(source: "ShapeShiftProject | str | None") -> "ShapeShiftProject":
        """Resolve and return the ShapeShiftProject for the given project name."""

        if isinstance(source, ShapeShiftProject):
            return source

        if isinstance(source, str):
            if is_config_path(source, raise_if_missing=False):
                return ShapeShiftProject.from_file(source)

        raise ValueError("ShapeShiftProject source must be a ShapeShiftProject instance or a valid project file path")
        # return ShapeShiftProject.from_context(source)

    # @staticmethod
    # def from_context(source: str | None) -> "ShapeShiftProject":
    #     """Resolve and return the ShapeShiftProject for the given context name."""

    #     context: str = source or "default"

    #     logger.warning(f"[deprecation warning] Resolving ShapeShiftProject from global context '{context}'")

    #     provider: ConfigProvider = get_config_provider()

    #     if not provider.is_configured(context):
    #         raise ValueError(f"Failed to resolve ShapeShiftProject for context '{context}'")

    #     if context == "default":
    #         logger.warning("Using configuration from default context")

    #     config = ShapeShiftProject(cfg=provider.get_config(context).data)

    #     return config


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
