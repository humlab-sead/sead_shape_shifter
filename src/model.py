import copy
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
        """Get all key columns including system_id and public_id."""
        key_columns = set(self.keys or [])
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
        - done: User explicitly marked as complete (requires validation + preview)
        - todo: Not marked done (derived)
        - ignored: User explicitly excluded from project

    Derived Signals:
        - blocked: Has validation errors or dependency issues
        - in_progress: Entity exists but not done
        - pending: Entity doesn't exist yet
    """

    def __init__(self, data: dict[str, Any] | None = None) -> None:
        """Initialize task list from configuration data.

        Args:
            data: Dictionary containing task list configuration with keys:
                - required_entities: List of entity names that must be completed
                - completed: List of entity names marked as done by user
                - ignored: List of entity names explicitly excluded
        """
        self.data: dict[str, Any] = data or {}

    @property
    def required_entities(self) -> list[str]:
        """Get list of required entity names."""
        return self.data.get("required_entities", []) or []

    @property
    def completed(self) -> list[str]:
        """Get list of completed entity names."""
        return self.data.get("completed", []) or []

    @property
    def ignored(self) -> list[str]:
        """Get list of ignored entity names."""
        return self.data.get("ignored", []) or []

    def is_required(self, entity_name: str) -> bool:
        """Check if entity is required."""
        return entity_name in self.required_entities

    def is_completed(self, entity_name: str) -> bool:
        """Check if entity is marked as completed."""
        return entity_name in self.completed

    def is_ignored(self, entity_name: str) -> bool:
        """Check if entity is marked as ignored."""
        return entity_name in self.ignored

    def mark_completed(self, entity_name: str) -> None:
        """Mark entity as completed.

        Args:
            entity_name: Name of entity to mark as done

        Note:
            This only updates in-memory state. Caller must persist to project file.
        """
        # Ensure completed list exists in data
        if "completed" not in self.data:
            self.data["completed"] = []

        # Add to completed list if not already there
        if entity_name not in self.data["completed"]:
            self.data["completed"].append(entity_name)

        # Remove from ignored if present
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

        # Remove from completed if present
        if "completed" in self.data and entity_name in self.data["completed"]:
            self.data["completed"] = [e for e in self.data["completed"] if e != entity_name]

    def reset_status(self, entity_name: str) -> None:
        """Reset entity status to todo.

        Args:
            entity_name: Name of entity to reset

        Note:
            This only updates in-memory state. Caller must persist to project file.
        """
        # Remove from completed if present
        if "completed" in self.data and entity_name in self.data["completed"]:
            self.data["completed"] = [e for e in self.data["completed"] if e != entity_name]

        # Remove from ignored if present
        if "ignored" in self.data and entity_name in self.data["ignored"]:
            self.data["ignored"] = [e for e in self.data["ignored"] if e != entity_name]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {}
        if self.required_entities:
            result["required_entities"] = self.required_entities
        if self.completed:
            result["completed"] = self.completed
        if self.ignored:
            result["ignored"] = self.ignored
        return result

    @property
    def is_empty(self) -> bool:
        """Check if task list has no configuration."""
        return not (self.required_entities or self.completed or self.ignored)


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
