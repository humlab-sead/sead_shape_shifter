import copy
from dataclasses import dataclass
from functools import cached_property
from typing import Any, Generator, Literal, Self

import pandas as pd
import xxhash
from loguru import logger

from src.configuration import ConfigFactory, ConfigLike
from src.configuration.config import Config, is_config_path
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
        return self.data.get("allow_null_keys", False)

    @property
    def allow_null_keys_is_explicit(self) -> bool:
        return "allow_null_keys" in self.data

    @property
    def is_empty(self) -> bool:
        """Check if no constraints are set."""
        return bool(self.data) is False

    @property
    def has_constraints(self) -> bool:
        return not self.is_empty

    def has_match_constraints(self) -> bool:
        return self.allow_unmatched_left is not None or self.allow_unmatched_right is not None


@dataclass
class ForeignKeyMergeSetup:
    """Setup configuration for foreign key merge operation.

    Attributes:
        remote_columns: Filtered list of remote columns to select (excludes duplicate targets)
        rename_map: Column renaming dictionary (source -> target)
    """

    remote_columns: list[str]
    rename_map: dict[str, str]


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
    def defer_dependency(self) -> bool:
        """Whether to defer hard dependency on the remote entity.

        When True, the FK target is not treated as a hard dependency during
        topological sorting, allowing circular references. The FK will be linked
        in a final linking pass after all entities are processed.

        Default: False (safe, backward compatible)
        Use with caution: Only enable when circular references are unavoidable.
        """
        return self.fk_cfg.get("defer_dependency", False)

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

    def get_valid_remote_columns(self, candidate_columns: list[str]) -> list[str]:
        """Get list of valid remote columns to select from the remote dataframe based on the
        foreign key configuration and the dataframe's columns.
        Valid remote columns include the remote keys and any extra columns that exist in the dataframe.
        """
        extra_columns: dict[str, str] = self.resolved_extra_columns()
        columns: list[str] = unique(self.remote_keys + list(extra_columns.keys()))
        missing_columns: list[str] = [col for col in columns if col not in candidate_columns]
        if missing_columns:
            logger.warning(
                f"{self.local_entity}[linking]: Skipping extra link columns for entity "
                f"'{self.local_entity}' to '{self.remote_entity}': missing remote columns {missing_columns} in remote table"
            )
            columns = [col for col in columns if col in candidate_columns]
        return columns

    def generate_link_setup(self, remote_columns: list[str], remote_cfg: "TableConfig") -> "ForeignKeyMergeSetup":
        """Generate the setup for linking based on the foreign key configuration.

        Determines which remote columns to select and how to rename them, avoiding duplicate
        columns from non-identity renames.

        We need to rename remote `system_id` to value of remote `public_id` before the merge.
        The local FK will hence be named after the remote public id, but it will contain the remote `system_id`s.

        Edge case: When a fixed entity has its public_id as a column name (e.g., master_dataset
        with public_id="master_dataset_id" AND columns=["master_dataset_id", ...]), we would
        create duplicate columns if we select both system_id and master_dataset_id, then rename
        system_id -> master_dataset_id. Solution: Filter out columns that will be created by
        non-identity renames (allow identity renames like {'name': 'name'}).

        Args:
            remote_columns: List of columns available in the remote dataframe
            remote_cfg: Configuration of the remote table

        Returns:
            ForeignKeyMergeSetup with columns to select and rename mappings
        """

        # Generate default renames: remote system_id -> remote public_id and extra columns
        default_renames: dict[str, str] = {remote_cfg.system_id: remote_cfg.public_id} | self.resolved_extra_columns()

        # Identify rename targets that aren't identity renames
        rename_targets: set[str] = {target for source, target in default_renames.items() if source != target}

        # Filter remote columns to select based on configuration and avoid duplicates
        remote_extra_cols: list[str] = self.get_valid_remote_columns(remote_columns)

        # Build final list of remote columns to select, excluding those that would create duplicates
        remote_cols_to_select: list[str] = [col for col in remote_extra_cols if col not in rename_targets]

        return ForeignKeyMergeSetup(remote_columns=remote_cols_to_select, rename_map=default_renames)

    def has_foreign_key_link(self, remote_id: str, table: pd.DataFrame) -> bool:
        """Check if the foreign key linking has already been added to the table."""
        if remote_id in table.columns:
            return True
        extra_columns: dict[str, str] = self.resolved_extra_columns()
        if extra_columns and all(col in table.columns for col in extra_columns.values()):
            return True
        return False


class MaterializationConfig:
    """Configuration for materialized entity state. Read-Only."""

    def __init__(self, data: dict[str, Any] | None = None) -> None:
        """Initialize materialization config from data."""
        self.data: dict[str, Any] = data or {}

    @property
    def enabled(self) -> bool:
        """Check if entity is materialized."""
        return self.data.get("enabled", False)

    @property
    def source_state(self) -> dict[str, Any] | None:
        """Get saved pre-materialization entity config."""
        return self.data.get("source_state")

    @property
    def materialized_at(self) -> str | None:
        """Get materialization timestamp (ISO format)."""
        return self.data.get("materialized_at")


class TableConfig:
    """Configuration for a database table. Read-Only. Wraps table setting from entities config."""

    def __init__(self, *, entities_cfg: dict[str, dict[str, Any]], entity_name: str) -> None:

        self.entities_cfg: dict[str, dict[str, Any]] = entities_cfg
        self.entity_name: str = entity_name
        self.entity_cfg: dict[str, Any] = entities_cfg[entity_name]

        assert self.entity_cfg, f"No configuration found for entity '{entity_name}'"

    @property
    def type(self) -> Literal["entity", "sql", "fixed", "csv", "xlsx", "openpyxl"] | None:
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
        """Deprecated: Use system_id instead. Kept for backward compatibility."""
        return self.system_id

    @property
    def system_id(self) -> str:
        """Get system_id column name (always 'system_id')."""
        return self.entity_cfg.get("system_id") or "system_id"

    @property
    def public_id(self) -> str:
        """Get public_id column name (defines FK column names in child tables)."""
        return self.entity_cfg.get("public_id") or ""

    @property
    def materialized(self) -> MaterializationConfig:
        """Get materialization configuration."""
        return MaterializationConfig(self.entity_cfg.get("materialized", {}))

    @property
    def is_materialized(self) -> bool:
        """Check if entity is materialized."""
        return self.materialized.enabled

    @property
    def check_column_names(self) -> bool:
        return self.entity_cfg.get("check_column_names", True)

    @property
    def auto_detect_columns(self) -> None | bool:
        return self.entity_cfg.get("auto_detect_columns")

    @property
    def data_source(self) -> str | None:
        return self.entity_cfg.get("data_source", None)

    @property
    def keys(self) -> set[str]:
        return set(self.entity_cfg.get("keys", []) or [])

    @property
    def safe_keys(self) -> list[str]:
        """Return keys as an ordered list, converting scalar values if necessary."""
        keys: str | list[Any] = self.entity_cfg.get("keys", []) or []
        if isinstance(keys, str):
            return [keys]
        return [key for key in keys if isinstance(key, str)]

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
        value = self.entity_cfg.get("drop_duplicates")
        if isinstance(value, dict):
            return value.get("columns") or False
        return value or False

    @property
    def check_functional_dependency(self) -> bool:
        return dotget(self.entity_cfg, "check_functional_dependency,drop_duplicates.check_functional_dependency", True)

    @property
    def strict_functional_dependency(self) -> bool:
        return dotget(self.entity_cfg, "strict_functional_dependency,drop_duplicates.strict_functional_dependency", True)

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

        # Collect entities referenced in filters via 'other_entity'
        filter_dependencies: set[str] = set()
        for filter_cfg in self.filters:
            if isinstance(filter_cfg.get("other_entity"), str):
                filter_dependencies.add(filter_cfg["other_entity"])

        return (
            set(self.entity_cfg.get("depends_on", []) or [])
            | ({self.source} if self.source else set())
            | {fk.remote_entity for fk in self.foreign_keys if not fk.defer_dependency}
            | append_sources
            | filter_dependencies
        )

    @cached_property
    def foreign_keys(self) -> list[ForeignKeyConfig]:
        return [
            ForeignKeyConfig(local_entity=self.entity_name, fk_cfg=fk_data) for fk_data in self.entity_cfg.get("foreign_keys", []) or []
        ]

    def dependent_entities(self) -> Generator[str, None, None]:
        """Yield names of entities that depend on this entity."""
        for entity_name, entity_cfg in self.entities_cfg.items():
            try:
                # Check source
                if entity_cfg.get("source") == self.entity_name:
                    yield entity_name
                    continue

                # Check depends_on
                depends_on: list[str] = entity_cfg.get("depends_on", []) or []
                if self.entity_name in depends_on:
                    yield entity_name
                    continue

                # Check foreign keys
                foreign_keys: list[dict[str, Any]] = entity_cfg.get("foreign_keys", []) or []
                for fk in foreign_keys:
                    if fk.get("entity") == self.entity_name:
                        yield entity_name
                        break

                # Check append sources
                append_raw = entity_cfg.get("append", []) or []
                # Normalize to list (append can be: string, dict, or list of dicts)
                if isinstance(append_raw, str):
                    # Skip string format - not a valid dependency check
                    continue

                if isinstance(append_raw, dict):
                    append_cfgs = [append_raw]
                else:
                    append_cfgs = append_raw

                for append_cfg in append_cfgs:
                    if isinstance(append_cfg, dict) and append_cfg.get("source") == self.entity_name:
                        yield entity_name
                        break
            except KeyError:
                continue

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
    def identity_columns(self) -> list[str]:
        """Get list of identifier columns (system_id + public_id). Business "keys" from source excluded."""
        return ["system_id"] + ([self.public_id] if self.public_id else [])

    @property
    def values_column_order(self) -> list[str]:
        """Get canonical column order for fixed values: system_id → public_id → keys → data columns.

        This defines the expected order for the 'values' field in fixed entities,
        following the three-tier identity system:
        1. system_id (local sequential identity)
        2. public_id (target schema identity, if defined)
        3. keys (business keys)
        4. columns (data columns, excluding identity columns)

        Returns:
            Ordered list of column names

        Example:
            entity_cfg:
              public_id: sample_type_id
              keys: [type_code]
              columns: [type_name, description]

            Returns: ["system_id", "sample_type_id", "type_code", "type_name", "description"]
        """
        result: list[str] = []

        # 1. system_id (always first)
        result.append(self.system_id)

        # 2. public_id (if defined)
        if self.public_id:
            result.append(self.public_id)

        # 3. keys (business identifiers)
        result.extend(sorted(self.keys))

        # 4. data columns (excluding system_id and public_id to avoid duplicates)
        identity_cols = {self.system_id, self.public_id} if self.public_id else {self.system_id}
        data_cols = [c for c in self.safe_columns if c not in identity_cols and c not in self.keys]
        result.extend(data_cols)

        return result

    @property
    def unnest_columns(self) -> set[str]:
        """Get set of columns that are pending (e.g., from unnesting)."""
        if not self.unnest:
            return set()

        return {self.unnest.var_name, self.unnest.value_name}

    @property
    def surviving_unnest_columns(self) -> set[str]:
        """Return the columns that remain immediately after unnest."""

        if not self.unnest:
            return set()

        return (set(self.unnest.id_vars) - {self.system_id}) | self.unnest_columns

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
        """Add 'system_id' column with auto-incrementing values if not already present.
        Returns:
            pd.DataFrame: DataFrame with 'system_id' column added if it was missing.
        Note: In the new identity model, system_id is always named 'system_id' and contains
        local sequence numbers (1, 2, 3...). The public_id column (if present) contains
        target system identifiers and is used for FK column naming.
        """
        system_id_col: str = self.system_id

        if system_id_col and system_id_col not in table.columns:
            # Add auto-incrementing system_id
            table = table.reset_index(drop=True).copy()
            table[system_id_col] = range(1, len(table) + 1)

        return table

    def add_public_id_column(self, table: pd.DataFrame) -> pd.DataFrame:
        """Add public_id column with None values if not already present.

        For entities with append configurations, the public_id column is excluded
        from append source extractions and added after concatenation.
        This allows the entity to have a proper public_id column structure
        even when building from heterogeneous sources.

        Returns:
            pd.DataFrame: DataFrame with public_id column added if it was missing.
        """
        public_id_col: str = self.public_id

        if public_id_col and public_id_col not in table.columns:
            # Add public_id column initialized to None
            table = table.copy()
            table[public_id_col] = None

        return table

    def apply_column_renaming(self, table: pd.DataFrame, parent_columns: list[str] | None = None) -> pd.DataFrame:
        """Apply column renaming based on align_by_position or column_mapping.

        This is used for append items to rename columns from the source entity
        to match the parent entity's column names.

        Args:
            table: DataFrame to rename
            parent_columns: Parent entity's column names (required for align_by_position)

        Supports two strategies:
        1. align_by_position: Rename columns by position to match parent's columns
        2. column_mapping: Explicit mapping {source_col: target_col}

        Returns:
            pd.DataFrame: DataFrame with renamed columns
        """
        align_by_position: bool = self.entity_cfg.get("align_by_position", False)
        column_mapping: dict[str, str] | None = self.entity_cfg.get("column_mapping")

        if not align_by_position and not column_mapping:
            return table

        table = table.copy()

        if align_by_position:
            if not parent_columns:
                raise ValueError(f"parent_columns required for align_by_position in {self.entity_name}")

            # Position-based renaming: map current columns to parent's columns by position
            current_columns: list[str] = list(table.columns)

            # Filter out system_id and identity/public_id columns from both lists for alignment.
            # For source-based append, the source entity may have a different public_id than the target.
            system_id_col: str = self.system_id
            target_public_id_col: str = self.public_id
            source_public_id_col: str = self.get_source_public_id()

            parent_exclude_cols: set[str] = {system_id_col}
            current_exclude_cols: set[str] = {system_id_col}

            if target_public_id_col:
                parent_exclude_cols.add(target_public_id_col)
                current_exclude_cols.add(target_public_id_col)

            if source_public_id_col:
                current_exclude_cols.add(source_public_id_col)

            parent_cols_filtered: list[str] = [c for c in parent_columns if c not in parent_exclude_cols]
            current_cols_filtered: list[str] = [c for c in current_columns if c not in current_exclude_cols]

            if len(parent_cols_filtered) != len(current_cols_filtered):
                raise ValueError(
                    f"Column count mismatch for align_by_position in {self.entity_name}: "
                    f"parent has {len(parent_cols_filtered)} columns {parent_cols_filtered}, "
                    f"append has {len(current_cols_filtered)} columns {current_cols_filtered}"
                )

            # Create rename mapping
            rename_map: dict[str, str] = dict(zip(current_cols_filtered, parent_cols_filtered))
            table = table.rename(columns=rename_map)

        elif column_mapping:
            # Explicit column mapping
            missing_cols: set[str] = set(column_mapping.keys()) - set(table.columns)
            if missing_cols:
                raise ValueError(f"Columns specified in column_mapping not found in {self.entity_name}: {missing_cols}")
            table = table.rename(columns=column_mapping)

        return table

    def get_source_public_id(self) -> str:
        """Get the public_id of the source entity, if this config references one."""
        source_entity: str | None = self.source
        if not source_entity or source_entity not in self.entities_cfg:
            return ""
        source_cfg = self.entities_cfg[source_entity] or {}
        return source_cfg.get("public_id") or ""

    def is_drop_duplicate_dependent_on_unnesting(self) -> bool:
        """Check if `drop_duplicates` is dependent on columns created during unnesting."""
        if not self.drop_duplicates or not self.unnest:
            return False
        if isinstance(self.drop_duplicates, list):
            return any(col in self.unnest_columns for col in self.drop_duplicates)
        return False

    def create_append_config(self, append_data: dict[str, Any]) -> dict[str, Any]:
        """Create a merged configuration for an append item, inheriting parent properties.

        Special handling:
        - Source-based append (when 'source' is present) blocks inheritance of loader-driving fields
        - Filters out public_id from columns list (will be added after concatenation)
        - Inherits most properties except foreign_keys, unnest, append, append_mode, depends_on
        - Passes through align_by_position and column_mapping from append item
        - When using align_by_position or column_mapping with entity source, columns come from source entity
        """
        merged: dict[str, Any] = {}
        non_inheritable_keys: set[str] = {"foreign_keys", "unnest", "append", "append_mode", "depends_on"}
        append_only_keys: set[str] = {"align_by_position", "column_mapping"}  # Don't inherit from parent
        all_keys: set[str] = set(self.entity_cfg.keys()) | set(append_data.keys())
        special_conversions = {
            "keys": lambda v: list(v) if isinstance(v, set) else v,
        }

        # Check if we're using column renaming with entity source
        has_source: bool = "source" in append_data and append_data["source"] is not None
        has_align: bool = append_data.get("align_by_position", False)
        has_mapping: bool = "column_mapping" in append_data
        use_source_columns: bool = has_source and (has_align or has_mapping) and "columns" not in append_data
        use_source_keys: bool = has_source and (has_align or has_mapping) and "keys" not in append_data

        # Source-based append shouldn't inherit loader-related fields from parent
        if has_source:
            non_inheritable_keys |= {"type", "values", "query", "data_source", "sql"}

        for key in all_keys:

            if key in non_inheritable_keys:
                continue

            # For append-only keys, only use value from append_data, don't inherit
            if key in append_only_keys:
                if key in append_data:
                    merged[key] = append_data[key]
                continue

            # When using column renaming with entity source and no explicit columns/keys,
            # get them from the source entity instead of parent
            if (key == "columns" and use_source_columns) or (key == "keys" and use_source_keys):
                source_entity: str | None = append_data.get("source")
                if source_entity and source_entity in self.entities_cfg:
                    source_value: list[Any] = self.entities_cfg[source_entity].get(key, [])
                    if source_value:
                        merged[key] = source_value
                    continue

            value = append_data[key] if key in append_data else self.entity_cfg[key]

            if key in special_conversions and value:
                value = special_conversions[key](value)

            merged[key] = value

        # Filter out public_id from columns list for append sources
        # The public_id column will be added after concatenation with None values
        if "columns" in merged and self.public_id:
            columns = merged["columns"]
            if isinstance(columns, list) and self.public_id in columns:
                merged["columns"] = [col for col in columns if col != self.public_id]

        return merged

    def get_target_facing_foreign_key_targets(self) -> set[str]:
        """Return FK target entities that contribute to target-facing output."""

        if self.unnest:
            targets: list[str] = []
            avaliable_columns: list[str] = sorted(self.surviving_unnest_columns)
            for foreign_key in self.foreign_keys:
                if not set(foreign_key.local_keys).issubset(avaliable_columns):
                    continue

                targets.append(foreign_key.remote_entity)
                # Add FK remote extra columns to available columns for subsequent FKs in case of chaining
                avaliable_columns.extend(foreign_key.resolved_extra_columns().values())
            return set(targets)

        return {foreign_key.remote_entity for foreign_key in self.foreign_keys if foreign_key.remote_entity}

    def get_target_facing_columns(self) -> list[str]:
        """Return the columns this entity presents to a target model.

        Contract in v1:
        - without unnest: includes business keys, explicit `columns`, `public_id`,
        configured `extra_columns`, and generated FK-facing columns
        - with unnest: first collapse the current table shape the same way `pd.melt`
        does, so only surviving `id_vars`, `var_name`, and `value_name` count as
        direct outputs from that stage
        - with unnest: FK-generated columns only count if the FK local keys still
        exist after unnest, allowing the post-unnest relink pass to recreate them
        - append branches do not widen the target-facing schema; they must conform
        to the parent entity's output contract rather than add new columns

        It intentionally excludes the internal `system_id` column unless it is exposed
        explicitly through some other target-facing mechanism.
        """

        target_columns: list[str] = []

        if self.unnest:
            target_columns.extend(sorted(self.surviving_unnest_columns))
        else:
            system_id: str = self.system_id
            target_columns.extend(column for column in self.safe_keys if column != system_id)
            target_columns.extend(column for column in self.safe_columns if column != system_id)
            target_columns.extend(self.extra_column_names)

        if self.public_id:
            target_columns.append(self.public_id)

        for foreign_key in self.foreign_keys:
            if self.unnest and not set(foreign_key.local_keys).issubset(target_columns):
                continue

            remote_cfg: TableConfig = TableConfig(entities_cfg=self.entities_cfg, entity_name=foreign_key.remote_entity)
            target_columns.append(remote_cfg.public_id)

            target_columns.extend(foreign_key.resolved_extra_columns().values())

        return unique([column for column in target_columns if column])

    def get_sub_table_configs(self) -> Generator[Self | "TableConfig", Any, None]:
        """Yield a sequence of resolved TableConfig objects.

        Each item orginates from the base entity and its append configurations.

        Yields self first (the base configuration), then creates and yields
        a TableConfig for each append item, if any, with inherited properties.

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
        """Get all key columns including system_id and public_id."""
        key_columns: set[str] = set(self.keys or [])
        if self.system_id:
            key_columns.add(self.system_id)
        if self.public_id:
            key_columns.add(self.public_id)
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


class LayoutPosition:
    """Position of a node in custom graph layout."""

    def __init__(self, data: dict[str, Any]) -> None:
        """Initialize layout position from configuration data.

        Args:
            data: Dictionary containing 'x' and 'y' coordinates

        Raises:
            ValueError: If x or y coordinates are missing
        """
        if "x" not in data or "y" not in data:
            raise ValueError("Layout position must have x and y coordinates")
        self.x: float = float(data["x"])
        self.y: float = float(data["y"])

    def to_dict(self) -> dict[str, float]:
        """Convert position to dictionary for serialization."""
        return {"x": self.x, "y": self.y}


class CustomLayoutConfig:
    """Custom graph layout configuration."""

    def __init__(self, data: dict[str, Any]) -> None:
        """Initialize custom layout from configuration data.

        Args:
            data: Dictionary mapping entity names to position dictionaries
        """
        self.positions: dict[str, LayoutPosition] = {}
        for entity_name, pos_data in data.items():
            if entity_name.startswith("_"):  # Skip metadata keys
                continue
            try:
                self.positions[entity_name] = LayoutPosition(pos_data)
            except ValueError as e:
                logger.warning(f"Invalid position for entity '{entity_name}': {e}, skipping")

    def get_position(self, entity_name: str) -> tuple[float, float] | None:
        """Get (x, y) position for entity, or None if not set.

        Args:
            entity_name: Name of the entity

        Returns:
            Tuple of (x, y) coordinates, or None if entity has no saved position
        """
        pos = self.positions.get(entity_name)
        return (pos.x, pos.y) if pos else None

    def set_position(self, entity_name: str, x: float, y: float) -> None:
        """Set position for entity.

        Args:
            entity_name: Name of the entity
            x: X coordinate
            y: Y coordinate
        """
        self.positions[entity_name] = LayoutPosition({"x": x, "y": y})

    def remove_position(self, entity_name: str) -> None:
        """Remove position for entity.

        Args:
            entity_name: Name of the entity to remove
        """
        self.positions.pop(entity_name, None)

    def to_dict(self) -> dict[str, dict[str, float]]:
        """Convert to dictionary for serialization."""
        return {name: pos.to_dict() for name, pos in self.positions.items()}

    @property
    def is_empty(self) -> bool:
        """Check if no positions are configured."""
        return len(self.positions) == 0


class LayoutOptions:
    """Layout options for dependency graph visualization."""

    def __init__(self, data: dict[str, Any]) -> None:
        """Initialize layout options from configuration data.

        Args:
            data: Dictionary containing layout configuration
        """
        self.data = data
        self._custom: CustomLayoutConfig | None = None

    @property
    def custom(self) -> CustomLayoutConfig:
        """Get custom layout configuration."""
        if self._custom is None:
            custom_data = self.data.get("custom", {})
            self._custom = CustomLayoutConfig(custom_data)
        return self._custom

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {}
        if self._custom and not self._custom.is_empty:
            result["custom"] = self._custom.to_dict()
        return result


class TaskList:
    """Task list configuration for tracking entity progress.

    This class provides a lightweight, non-enforcing progress tracking system
    for entities in a Shape Shifter project. It combines user-declared statuses
    with derived state (validation, preview availability) to guide workflow.

    Status Model:
        - todo: Entity planned but not yet created (yellowish color)
        - ongoing: Entity exists and is being worked on (bluish color)
        - done: User explicitly marked as complete (greenish color)
        - ignored: User explicitly excluded from project (greyish color)

    Derived Signals:
        - blocked: Has validation errors or dependency issues
        - flagged: User flagged for attention or action needed
        - critical: Required entity missing or has errors
        - ready: All dependencies done, validation passes
    """

    def __init__(self, data: dict[str, Any] | None = None) -> None:
        """Initialize task list from configuration data.

        Args:
            data: Dictionary containing task list configuration with keys:
                - todo: List of entity names that are planned but not yet created
                - ongoing: List of entity names marked as in-progress by user
                - done: List of entity names marked as complete by user
                - ignored: List of entity names explicitly excluded
                - flagged: Dictionary mapping entity names to flagged status

        Note:
            Automatically migrates old format (required_entities/completed) to new format (todo/done).
        """
        self.data: dict[str, Any] = data or {}
        self._migrate_legacy_format()

    def _migrate_legacy_format(self) -> None:
        """Migrate old format (required_entities/completed) to new format (todo/done).

        Old format:
            required_entities: [location, site, sample]
            completed: [location, site]

        New format:
            todo: [sample]
            done: [location, site]

        Migration logic:
            - done = completed
            - todo = required_entities - completed - ongoing
            - Remove old keys after migration
        """
        if "required_entities" in self.data or "completed" in self.data:
            # Get old values
            required = set(self.data.get("required_entities", []) or [])
            completed_old = set(self.data.get("completed", []) or [])
            ongoing_existing = set(self.data.get("ongoing", []) or [])

            # Migrate to new format
            if completed_old:
                self.data.setdefault("done", []).extend(sorted(completed_old))

            # Calculate todo: entities in required but not completed and not ongoing
            todo_entities = required - completed_old - ongoing_existing
            if todo_entities:
                self.data.setdefault("todo", []).extend(sorted(todo_entities))

            # Remove old keys
            self.data.pop("required_entities", None)
            self.data.pop("completed", None)

    @property
    def todo(self) -> list[str]:
        """Get list of todo entity names (planned but not yet created)."""
        return self.data.get("todo", []) or []

    @property
    def done(self) -> list[str]:
        """Get list of completed entity names."""
        return self.data.get("done", []) or []

    @property
    def required_entities(self) -> list[str]:
        """Get list of required entity names (for backward compatibility).

        Returns union of todo and done entities.
        """
        return sorted(set(self.todo) | set(self.done))

    @property
    def completed(self) -> list[str]:
        """Get list of completed entity names (for backward compatibility).

        Alias for done property.
        """
        return self.done

    @property
    def ongoing(self) -> list[str]:
        """Get list of ongoing entity names."""
        return self.data.get("ongoing", []) or []

    @property
    def ignored(self) -> list[str]:
        """Get list of ignored entity names."""
        return self.data.get("ignored", []) or []

    @property
    def flagged(self) -> dict[str, bool]:
        """Get mapping of flagged entity statuses."""
        return self.data.get("flagged", {}) or {}

    def is_required(self, entity_name: str) -> bool:
        """Check if entity is required (in todo or done lists)."""
        return entity_name in self.todo or entity_name in self.done

    def is_todo(self, entity_name: str) -> bool:
        """Check if entity is marked as todo."""
        return entity_name in self.todo

    def is_completed(self, entity_name: str) -> bool:
        """Check if entity is marked as completed."""
        return entity_name in self.done

    def is_done(self, entity_name: str) -> bool:
        """Check if entity is marked as done (alias for is_completed)."""
        return entity_name in self.done

    def is_ongoing(self, entity_name: str) -> bool:
        """Check if entity is marked as ongoing."""
        return entity_name in self.ongoing

    def is_ignored(self, entity_name: str) -> bool:
        """Check if entity is marked as ignored."""
        return entity_name in self.ignored

    def is_flagged(self, entity_name: str) -> bool:
        """Check if entity is flagged."""
        return self.flagged.get(entity_name, False)

    def mark_completed(self, entity_name: str) -> None:
        """Mark entity as completed.

        Args:
            entity_name: Name of entity to mark as done

        Note:
            This only updates in-memory state. Caller must persist to project file.
        """
        # Ensure done list exists in data
        if "done" not in self.data:
            self.data["done"] = []

        # Add to done list if not already there
        if entity_name not in self.data["done"]:
            self.data["done"].append(entity_name)

        # Remove from todo, ongoing, and ignored if present
        if "todo" in self.data and entity_name in self.data["todo"]:
            self.data["todo"] = [e for e in self.data["todo"] if e != entity_name]
        if "ongoing" in self.data and entity_name in self.data["ongoing"]:
            self.data["ongoing"] = [e for e in self.data["ongoing"] if e != entity_name]
        if "ignored" in self.data and entity_name in self.data["ignored"]:
            self.data["ignored"] = [e for e in self.data["ignored"] if e != entity_name]

    def mark_ongoing(self, entity_name: str) -> None:
        """Mark entity as ongoing.

        Args:
            entity_name: Name of entity to mark as ongoing

        Note:
            This only updates in-memory state. Caller must persist to project file.
        """
        # Ensure ongoing list exists in data
        if "ongoing" not in self.data:
            self.data["ongoing"] = []

        # Add to ongoing list if not already there
        if entity_name not in self.data["ongoing"]:
            self.data["ongoing"].append(entity_name)

        # Remove from todo, done, and ignored if present
        if "todo" in self.data and entity_name in self.data["todo"]:
            self.data["todo"] = [e for e in self.data["todo"] if e != entity_name]
        if "done" in self.data and entity_name in self.data["done"]:
            self.data["done"] = [e for e in self.data["done"] if e != entity_name]
        if "ignored" in self.data and entity_name in self.data["ignored"]:
            self.data["ignored"] = [e for e in self.data["ignored"] if e != entity_name]

    def mark_ignored(self, entity_name: str) -> None:
        """Mark entity as ignored.

        Args:
            entity_name: Name of entity to ignore

        Note:
            This only updates in-memory state. Caller must persist to project file.
        """
        # Ensure ignored list exists in data
        if "ignored" not in self.data:
            self.data["ignored"] = []

        # Add to ignored list if not already there
        if entity_name not in self.data["ignored"]:
            self.data["ignored"].append(entity_name)

        # Remove from todo, done, and ongoing if present
        if "todo" in self.data and entity_name in self.data["todo"]:
            self.data["todo"] = [e for e in self.data["todo"] if e != entity_name]
        if "done" in self.data and entity_name in self.data["done"]:
            self.data["done"] = [e for e in self.data["done"] if e != entity_name]
        if "ongoing" in self.data and entity_name in self.data["ongoing"]:
            self.data["ongoing"] = [e for e in self.data["ongoing"] if e != entity_name]

    def toggle_flagged(self, entity_name: str) -> bool:
        """Toggle flagged status for an entity.

        Args:
            entity_name: Name of entity to toggle

        Returns:
            New flagged status after toggle

        Note:
            This only updates in-memory state. Caller must persist to project file.
        """
        if "flagged" not in self.data:
            self.data["flagged"] = {}

        current = self.data["flagged"].get(entity_name, False)
        new_status = not current
        self.data["flagged"][entity_name] = new_status
        return new_status

    def mark_todo(self, entity_name: str) -> None:
        """Mark entity as todo (planned but not yet created).

        Args:
            entity_name: Name of entity to mark as todo

        Note:
            This only updates in-memory state. Caller must persist to project file.
        """
        # Ensure todo list exists in data
        if "todo" not in self.data:
            self.data["todo"] = []

        # Add to todo list if not already there
        if entity_name not in self.data["todo"]:
            self.data["todo"].append(entity_name)

        # Remove from done, ongoing, and ignored if present
        if "done" in self.data and entity_name in self.data["done"]:
            self.data["done"] = [e for e in self.data["done"] if e != entity_name]
        if "ongoing" in self.data and entity_name in self.data["ongoing"]:
            self.data["ongoing"] = [e for e in self.data["ongoing"] if e != entity_name]
        if "ignored" in self.data and entity_name in self.data["ignored"]:
            self.data["ignored"] = [e for e in self.data["ignored"] if e != entity_name]

    def reset_status(self, entity_name: str) -> None:
        """Reset entity status to todo.

        Args:
            entity_name: Name of entity to reset

        Note:
            This only updates in-memory state. Caller must persist to project file.
        """
        # Use mark_todo to add to todo list and remove from others
        self.mark_todo(entity_name)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization (uses new format)."""
        result = {}
        if self.todo:
            result["todo"] = self.todo
        if self.ongoing:
            result["ongoing"] = self.ongoing
        if self.done:
            result["done"] = self.done
        if self.ignored:
            result["ignored"] = self.ignored
        if self.flagged:
            result["flagged"] = self.flagged
        return result

    @property
    def is_empty(self) -> bool:
        """Check if task list has no configuration."""
        return not (self.todo or self.done or self.ongoing or self.ignored)


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

    @property
    def ingesters(self) -> dict[str, dict[str, Any]]:
        """Get ingester configurations from project options."""
        return self.options.get("ingesters", {}) or {}

    @cached_property
    def layout_options(self) -> LayoutOptions:
        """Get layout options for dependency graph visualization."""
        layout_data = self.options.get("layout", {})
        return LayoutOptions(layout_data)

    @cached_property
    def task_list(self) -> TaskList:
        """Get task list configuration for entity progress tracking."""
        task_data = self.cfg.get("task_list", {})
        return TaskList(task_data)

    def get_ingester_config(self, ingester_name: str) -> dict[str, Any] | None:
        """Get configuration for a specific ingester."""
        return self.ingesters.get(ingester_name)

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

    def clone(self) -> "ShapeShiftProject":
        """Create a deep copy of the ShapeShiftProject."""
        return ShapeShiftProject(cfg=copy.deepcopy(self.cfg), filename=self.filename)

    def resolve(self, strict: bool = False, **context) -> "ShapeShiftProject":
        """Resolve and return a new ShapeShiftProject instance."""
        return ShapeShiftProject(
            cfg=Config.resolve_references(
                self.cfg,
                env_filename=dotget(context, "env_filename, env_file"),
                env_prefix=dotget(context, "env_prefix"),
                source_path=dotget(context, "filename, file_path") or self.filename,
                inplace=False,
                strict=strict,
            ),
            filename=context.get("filename") or self.filename,
        )

    def is_resolved(self) -> bool:
        """Check if the configuration has any unresolved references."""
        return not Config.find_unresolved_directives(self.cfg)

    def unresolved_directives(self) -> list[str]:
        """Check if the configuration has any unresolved references."""
        return Config.find_unresolved_directives(self.cfg)

    @cached_property
    def table_names(self) -> list[str]:
        return list(self.tables.keys())

    def get_sorted_columns(self, entity_name: str) -> list[str]:
        """Return a list of columns with system_id and FK columns first, then other columns.

        FK columns are named after the parent entity's public_id.
        """
        table: TableConfig = self.get_table(entity_name)
        # Start with system_id and public_id, then add FK columns (named after parent's public_id)
        cols_to_move: list[str] = (
            [table.system_id]
            + ([table.public_id] if table.public_id else [])
            + [self.get_table(fk.remote_entity).public_id for fk in table.foreign_keys]
        )
        existing_cols_to_move: list[str] = [col for col in cols_to_move if col in table.columns]
        other_cols: list[str] = [col for col in table.columns if col not in existing_cols_to_move]
        new_column_order: list[str] = existing_cols_to_move + other_cols
        return unique(new_column_order)

    def reorder_columns(self, table_cfg: str | TableConfig, table: pd.DataFrame) -> pd.DataFrame:
        """Reorder columns in the DataFrame to have system_id, public_id, FK columns, extra columns, then others.

        Returns:
            pd.DataFrame: DataFrame with columns reordered.

        FK columns are named after the parent entity's public_id.
        """
        if isinstance(table_cfg, str):
            table_cfg = self.get_table(entity_name=table_cfg)

        # Build ordered list: system_id (if present), public_id, FK columns (parent's public_id), extra columns
        cols_to_move: list[str] = []

        # Add system_id if present in dataframe
        if "system_id" in table.columns:
            cols_to_move.append("system_id")

        # Add entity's own public_id
        if table_cfg.public_id:
            cols_to_move.append(table_cfg.public_id)

        # Add FK columns (use parent's public_id)
        cols_to_move.extend(sorted([self.get_table(fk.remote_entity).public_id for fk in table_cfg.foreign_keys]))

        # Add extra columns
        cols_to_move.extend(sorted(table_cfg.extra_column_names))

        # Remove duplicates while preserving order
        existing_cols_to_move: list[str] = []
        seen: set[str] = set()
        for col in cols_to_move:
            if col in table.columns and col not in seen:
                existing_cols_to_move.append(col)
                seen.add(col)

        other_cols: list[str] = [col for col in table.columns if col not in existing_cols_to_move]
        new_column_order: list[str] = existing_cols_to_move + sorted(other_cols)
        table = table[new_column_order]
        return table

    @staticmethod
    def from_file(filename: str, env_file: str = ".env", env_prefix: str = "SHAPE_SHIFTER") -> "ShapeShiftProject":
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

    def resolve_target_entities(self, target_entities: set[str] | None = None) -> set[str]:
        """Resolve target entities including all dependencies. If no target entities are provided, return all entities in the project."""
        if target_entities:
            all_required: set[str] = set()
            for entity in target_entities:
                all_required.update(self.get_required_entities(entity))
            return all_required
        return set(self.tables.keys())

    def get_required_entities(self, entity_name: str) -> set[str]:
        """Get all entities required to process the given entity (including the entity itself)."""
        required_entities: set[str] = {entity_name}
        unprocessed: list[str] = [entity_name]

        while unprocessed:
            current: str = unprocessed.pop()
            if current not in self.tables:
                continue
            for dep in self.get_table(entity_name=current).depends_on:
                if dep in required_entities:
                    continue
                required_entities.add(dep)
                unprocessed.append(dep)

        return required_entities


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
