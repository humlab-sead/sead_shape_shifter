from abc import ABC, abstractmethod
from typing import Any

import pandas as pd

from src.model import ForeignKeyConfig, ShapeShiftProject, TableConfig

# pylint: disable=line-too-long


class ForeignKeyConfigSpecification:
    """Specification that tests if a foreign key relationship is resolveble.
    Returns True if all local and remote keys exist, False if any are missing,
    or None if resolvable after unnesting some local keys are in unnest columns.
    """

    def __init__(self, cfg: "ShapeShiftProject") -> None:
        self.cfg: ShapeShiftProject = cfg
        self.error: str = ""
        self.deferred: bool = False

    def clear(self) -> None:
        self.error = ""
        self.deferred = False

    def is_satisfied_by(self, *, fk_cfg: ForeignKeyConfig) -> bool | None:
        self.clear()
        missing_fields: set[str]
        cfg_local_table: TableConfig = self.cfg.get_table(fk_cfg.local_entity)
        cfg_remote_table: TableConfig = self.cfg.get_table(fk_cfg.remote_entity)

        if fk_cfg.how == "cross":
            if fk_cfg.local_keys or fk_cfg.remote_keys:
                self.error = (
                    f"{fk_cfg.local_entity}[linking] -> {fk_cfg.remote_entity}: 'cross' join should not specify local_keys or remote_keys"
                )
                return False
            return True

        if len(fk_cfg.local_keys) == 0 or len(fk_cfg.remote_keys) == 0:
            self.error = f"{fk_cfg.local_entity}[linking] -> {fk_cfg.remote_entity}: local_keys and remote_keys must be specified for non-cross joins"  # noqa: E501
            return False

        if len(fk_cfg.local_keys) != len(fk_cfg.remote_keys):
            self.error = f"{fk_cfg.local_entity}[linking] -> {fk_cfg.remote_entity}: number of local_keys ({len(fk_cfg.local_keys)}) does not match number of remote_keys ({len(fk_cfg.remote_keys)})"  # noqa: E501
            return False

        missing_fields = self.get_missing_fields(
            required_fields=set(fk_cfg.local_keys),
            available_fields=set(cfg_local_table.keys_columns_and_fks) | set(cfg_local_table.unnest_columns),
        )

        if missing_fields:
            self.error = f"{fk_cfg.local_entity}[linking] -> {fk_cfg.remote_entity}: local keys {missing_fields} not found in local entity '{fk_cfg.local_entity}'"  # noqa: E501
            return False

        missing_fields: set[str] = self.get_missing_fields(
            required_fields=set(fk_cfg.remote_keys), available_fields=set(cfg_remote_table.get_columns())
        )

        if missing_fields:
            self.error = f"{fk_cfg.local_entity}[linking] -> {fk_cfg.remote_entity}: remote keys {missing_fields} not found in remote entity '{fk_cfg.remote_entity}'"  # noqa: E501
            return False

        return True

    def get_missing_fields(self, *, required_fields: set[str], available_fields: set[str]) -> set[str]:
        """Return the set of required keys that are missing from found keys."""
        return {key for key in required_fields if key not in available_fields}


class ForeignKeyDataSpecification(ForeignKeyConfigSpecification):
    """Checks if local and remote keys are present in the actual table data (pandas.DataFrames)."""

    def __init__(self, table_store: dict[str, pd.DataFrame], cfg: "ShapeShiftProject") -> None:
        super().__init__(cfg)
        self.table_store: dict[str, pd.DataFrame] = table_store

    def is_satisfied_by(self, *, fk_cfg: ForeignKeyConfig) -> bool:
        missing_fields: set[str]

        assert fk_cfg.local_entity in self.table_store, f"Local DataFrame for entity '{fk_cfg.local_entity}' not found"
        assert fk_cfg.remote_entity in self.table_store, f"Remote DataFrame for entity '{fk_cfg.remote_entity}' not found"

        is_config_ok: bool | None = super().is_satisfied_by(fk_cfg=fk_cfg)
        if is_config_ok is not True:
            return False

        if missing_fields := self.get_missing_local_fields(fk_cfg=fk_cfg):
            if missing_fields == self.cfg.get_table(fk_cfg.local_entity).unnest_columns:
                self.deferred = True
            else:
                self.error = f"{fk_cfg.local_entity}[linking] -> {fk_cfg.remote_entity}: local keys {missing_fields} not found in local entity data '{fk_cfg.local_entity}'"  # noqa: E501
                return False

        if self.get_missing_pending_fields(fk_cfg=fk_cfg):
            self.deferred = True
            return True

        if missing_fields := self.get_missing_remote_fields(fk_cfg=fk_cfg):
            self.error = f"{fk_cfg.local_entity}[linking]: -> {fk_cfg.remote_entity}: remote keys {missing_fields} not found in remote entity data '{fk_cfg.remote_entity}'"  # noqa: E501
            return False

        return True

    def get_missing_local_fields(self, *, fk_cfg: ForeignKeyConfig) -> set[str]:
        """Check for missing local keys in the local entity data."""
        table: pd.DataFrame = self.table_store[fk_cfg.local_entity]
        return self.get_missing_fields(
            required_fields=set(fk_cfg.local_keys),
            available_fields=set(table.columns).union(self.cfg.get_table(fk_cfg.local_entity).unnest_columns),
        )

    def get_missing_pending_fields(self, *, fk_cfg: ForeignKeyConfig) -> set[str]:
        """Check for missing pending keys in the local entity data."""
        return self.get_missing_fields(
            required_fields=set(self.cfg.get_table(fk_cfg.local_entity).unnest_columns),
            available_fields=set(self.table_store[fk_cfg.local_entity].columns),
        )

    def get_missing_remote_fields(self, *, fk_cfg: ForeignKeyConfig) -> set[str]:
        """Check for missing remote keys in the remote entity data."""
        return self.get_missing_fields(
            required_fields=set(fk_cfg.remote_keys), available_fields=set(self.table_store[fk_cfg.remote_entity].columns)
        )


# ============================================================================
# Configuration Validation Specifications
# ============================================================================


class SpecificationIssue:
    """Custom exception for specification validation errors/warnings."""

    def __init__(self, *, severity: str, message: str, entity: str | None = None, **kwargs) -> None:
        self.severity: str = severity
        self.message: str = message
        self.entity_name: str | None = entity
        self.entity_field: str | None = kwargs.get("field")
        self.column_name: str | None = kwargs.get("column")
        self.kwargs = kwargs


class ProjectSpecification(ABC):
    """Base specification for project validation."""

    def __init__(self) -> None:
        self.errors: list[SpecificationIssue] = []
        self.warnings: list[SpecificationIssue] = []

    def clear(self) -> None:
        """Clear all errors and warnings."""
        self.errors = []
        self.warnings = []

    @abstractmethod
    def is_satisfied_by(self, config: dict[str, Any]) -> bool:
        """Check if the configuration satisfies this specification.

        Args:
            config: The configuration dictionary to validate.

        Returns:
            True if valid, False otherwise.
        """

    def add_error(self, error: str, entity: str | None, **kwargs) -> None:
        """Add an error message."""
        self.errors.append(SpecificationIssue(severity="error", message=error, entity=entity, **kwargs))

    def add_warning(self, warning: str, entity: str | None, **kwargs) -> None:
        """Add a warning message."""
        self.warnings.append(SpecificationIssue(severity="warning", message=warning, entity=entity, **kwargs))

    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0


class EntityExistsSpecification(ProjectSpecification):
    """Validates that all referenced entities exist in the configuration."""

    def is_satisfied_by(self, config: dict[str, Any]) -> bool:
        """Check if all entities referenced in foreign keys and dependencies exist."""
        self.clear()
        valid = True

        entities_config = config.get("entities", {})
        if not entities_config:
            self.add_error("Configuration must contain 'entities' section", entity="configuration", field="entities")
            return False

        entity_names = set(entities_config.keys())

        for entity_name, entity_data in entities_config.items():
            # Check foreign key references
            foreign_keys = entity_data.get("foreign_keys", []) or []
            for fk in foreign_keys:
                remote_entity = fk.get("entity", "")
                if not remote_entity:
                    self.add_error(f"Entity '{entity_name}': foreign key missing 'entity' field", entity=entity_name)
                    valid = False
                elif remote_entity not in entity_names:
                    self.add_error(
                        f"Entity '{entity_name}': references non-existent entity '{remote_entity}' in foreign key",
                        entity=entity_name,
                    )
                    valid = False

            # Check depends_on references
            depends_on = entity_data.get("depends_on", []) or []
            for dep in depends_on:
                if dep not in entity_names:
                    self.add_error(f"Entity '{entity_name}': depends on non-existent entity '{dep}'", entity=entity_name, depends_on=dep)
                    valid = False

            # Check source references (for derived tables)
            source = entity_data.get("source", None)
            if source and isinstance(source, str) and source not in entity_names:
                self.add_error(
                    f"Entity '{entity_name}': references non-existent source entity '{source}'", entity=entity_name, source=source
                )
                valid = False

        return valid


class CircularDependencySpecification(ProjectSpecification):
    """Validates that there are no circular dependencies between entities."""

    def is_satisfied_by(self, config: dict[str, Any]) -> bool:
        """Check for circular dependencies in the entity graph."""
        self.clear()

        entities_config = config.get("entities", {})
        if not entities_config:
            return True  # EntityExistsSpecification will catch this

        # Build dependency graph
        dependencies: dict[str, set[str]] = {}
        for entity_name, entity_data in entities_config.items():
            deps = set(entity_data.get("depends_on", []) or [])

            # Add source as dependency
            source = entity_data.get("source", None)
            if source and isinstance(source, str):
                deps.add(source)

            dependencies[entity_name] = deps

        # Check for cycles using DFS
        visited: set[str] = set()
        rec_stack: set[str] = set()
        path: list[str] = []

        def has_cycle(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in dependencies.get(node, set()):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    cycle_path = " -> ".join(path[cycle_start:] + [neighbor])
                    self.add_error(f"Circular dependency detected: {cycle_path}", entity="configuration")
                    return True

            path.pop()
            rec_stack.remove(node)
            return False

        valid = True
        for entity in dependencies:
            if entity not in visited:
                if has_cycle(entity):
                    valid = False

        return valid


class RequiredFieldsSpecification(ProjectSpecification):
    """Validates that all required fields are present in all entities."""

    def is_satisfied_by(self, config: dict[str, Any]) -> bool:
        """Check that required fields are present for each entity."""
        self.clear()
        valid = True

        entities_config = config.get("entities", {})
        if not entities_config:
            return True  # EntityExistsSpecification will catch this

        for entity_name, entity_data in entities_config.items():
            is_fixed = entity_data.get("type", "data") == "fixed"

            if is_fixed:
                # Fixed data tables require: surrogate_id, columns, values (or source)
                if not entity_data.get("surrogate_id"):
                    self.add_error(
                        f"Entity '{entity_name}': fixed data table missing required 'surrogate_id'",
                        entity=entity_name,
                        column="surrogate_id",
                    )
                    valid = False

                if not entity_data.get("columns"):
                    self.add_error(
                        f"Entity '{entity_name}': fixed data table missing required 'columns'", entity=entity_name, field="columns"
                    )
                    valid = False

                if not entity_data.get("values"):
                    self.add_error(
                        f"Entity '{entity_name}': fixed data table missing required 'values'", entity=entity_name, field="values"
                    )
                    valid = False
            else:
                # Regular data tables require: columns (or keys)
                if not entity_data.get("columns") and not entity_data.get("keys"):
                    self.add_error(
                        f"Entity '{entity_name}': data table must have 'columns' or 'keys'", entity=entity_name, field="columns/keys"
                    )
                    valid = False

        return valid


class ForeignKeySpecification(ProjectSpecification):
    """Validates foreign key setups."""

    def is_satisfied_by(self, config: dict[str, Any]) -> bool:
        """Check that foreign key configurations are valid."""
        self.clear()
        valid: bool = True

        entities_config = config.get("entities", {})
        if not entities_config:
            return True

        for entity_name, entity_data in entities_config.items():
            foreign_keys = entity_data.get("foreign_keys", []) or []

            for idx, fk in enumerate(foreign_keys):
                fk_id: str = f"Entity '{entity_name}', foreign key #{idx + 1}"

                # Check required fields
                if not fk.get("entity"):
                    self.add_error(f"{fk_id}: missing required field 'entity'", entity=entity_name, foreign_key=fk_id)
                    valid = False
                    continue

                if not fk.get("local_keys"):
                    self.add_error(f"{fk_id}: missing required field 'local_keys'", entity=entity_name, foreign_key=fk_id)
                    valid = False

                if not fk.get("remote_keys"):
                    self.add_error(f"{fk_id}: missing required field 'remote_keys'", entity=entity_name, foreign_key=fk_id)
                    valid = False

                # Check that local_keys and remote_keys have same length
                local_keys = fk.get("local_keys", []) or []
                remote_keys = fk.get("remote_keys", []) or []

                if len(local_keys) != len(remote_keys):
                    self.add_error(
                        f"{fk_id}: 'local_keys' length ({len(local_keys)}) does not match 'remote_keys' length ({len(remote_keys)})",
                        entity=entity_name,
                        foreign_key=fk_id,
                    )
                    valid = False

                # Validate extra_columns format
                extra_columns = fk.get("extra_columns")
                if extra_columns is not None:
                    if not isinstance(extra_columns, (str, list, dict)):
                        self.add_error(f"{fk_id}: 'extra_columns' must be string, list, or dict", entity=entity_name, foreign_key=fk_id)
                        valid = False

        return valid


class UnnestSpecification(ProjectSpecification):
    """Validates unnest setups."""

    def is_satisfied_by(self, config: dict[str, Any]) -> bool:
        """Check that unnest setups are valid."""
        self.clear()
        valid = True

        entities_cfg = config.get("entities", {})
        if not entities_cfg:
            return True

        for entity_name, entity_data in entities_cfg.items():
            unnest = entity_data.get("unnest")

            if unnest:
                # Check required fields
                if not unnest.get("value_vars"):
                    self.add_error(
                        f"Entity '{entity_name}': unnest configuration missing required 'value_vars'",
                        entity=entity_name,
                        field="value_vars",
                    )
                    valid = False

                if not unnest.get("var_name"):
                    self.add_error(
                        f"Entity '{entity_name}': unnest configuration missing required 'var_name'", entity=entity_name, field="var_name"
                    )
                    valid = False

                if not unnest.get("value_name"):
                    self.add_error(
                        f"Entity '{entity_name}': unnest configuration missing required 'value_name'",
                        entity=entity_name,
                        field="value_name",
                    )
                    valid = False

                # Warn if id_vars is missing (it's optional but usually needed)
                if not unnest.get("id_vars"):
                    self.add_warning(
                        f"Entity '{entity_name}': unnest configuration missing 'id_vars' (may cause issues)",
                        entity=entity_name,
                        field="id_vars",
                    )

        return valid


class DropDuplicatesSpecification(ProjectSpecification):
    """Validates drop_duplicates configurations."""

    def is_satisfied_by(self, config: dict[str, Any]) -> bool:
        """Check that drop_duplicates configurations are valid."""
        self.clear()
        valid = True

        entities_config = config.get("entities", {})
        if not entities_config:
            return True

        for entity_name, entity_data in entities_config.items():
            drop_dup = entity_data.get("drop_duplicates")

            if drop_dup is not None:
                # Can be bool, string (include directive), or list
                if not isinstance(drop_dup, (bool, str, list)):
                    self.add_error(
                        f"Entity '{entity_name}': 'drop_duplicates' must be boolean, string, or list of columns",
                        entity=entity_name,
                        field="drop_duplicates",
                    )
                    valid = False

        return valid


class SurrogateIdSpecification(ProjectSpecification):
    """Validates surrogate ID configurations."""

    def is_satisfied_by(self, config: dict[str, Any]) -> bool:
        """Check that surrogate IDs follow naming conventions and are unique."""
        self.clear()
        valid = True

        entities_config = config.get("entities", {})
        if not entities_config:
            return True

        surrogate_ids: dict[str, list[str]] = {}  # id -> list of entities using it

        for entity_name, entity_data in entities_config.items():
            surrogate_id = entity_data.get("surrogate_id", "")

            if surrogate_id:
                # Check naming convention (should end with _id)
                if not surrogate_id.endswith("_id"):
                    self.add_warning(
                        f"Entity '{entity_name}': surrogate_id '{surrogate_id}' does not follow convention (should end with '_id')",
                        entity=entity_name,
                        field="surrogate_id",
                    )

                # Track for uniqueness check
                if surrogate_id not in surrogate_ids:
                    surrogate_ids[surrogate_id] = []
                surrogate_ids[surrogate_id].append(entity_name)

        # Check for duplicate surrogate IDs
        for surrogate_id, entities in surrogate_ids.items():
            if len(entities) > 1:
                self.add_error(
                    f"Surrogate ID '{surrogate_id}' is used by multiple entities: {', '.join(entities)}",
                    entity="configuration",
                    surrogate_id=surrogate_id,
                )
                valid = False

        return valid


class SqlDataSpecification(ProjectSpecification):
    """Validates SQL-type entity configurations."""

    def is_satisfied_by(self, config: dict[str, Any]) -> bool:
        """Check that SQL data configurations are valid."""
        self.clear()
        valid = True

        entities_config = config.get("entities", {})
        if not entities_config:
            return True

        for entity_name, entity_data in entities_config.items():
            is_sql = entity_data.get("type") == "sql"

            if is_sql:
                # Check required fields for SQL type
                if not entity_data.get("data_source"):
                    self.add_error(
                        f"Entity '{entity_name}': type 'sql' requires 'data_source' field", entity=entity_name, field="data_source"
                    )
                    valid = False

                query = entity_data.get("query")
                if not query:
                    self.add_error(f"Entity '{entity_name}': type 'sql' requires 'query' field", entity=entity_name, field="query")
                    valid = False
                elif isinstance(query, str) and not query.strip():
                    self.add_error(f"Entity '{entity_name}': 'query' field is empty", entity=entity_name, field="query")
                    valid = False

                # Warn if source is not None (SQL entities should load directly from database)
                if entity_data.get("source") is not None:
                    self.add_warning(
                        f"Entity '{entity_name}': SQL entity has 'source' field (should be null for direct SQL queries)",
                        entity=entity_name,
                        field="source",
                    )

        return valid


class FixedDataSpecification(ProjectSpecification):
    """Validates fixed data table configurations."""

    def is_satisfied_by(self, config: dict[str, Any]) -> bool:
        """Check that fixed data configurations are valid."""
        self.clear()
        valid = True

        entities_config = config.get("entities", {})
        if not entities_config:
            return True

        for entity_name, entity_data in entities_config.items():
            is_fixed = entity_data.get("type") == "fixed"

            if is_fixed:
                values = entity_data.get("values")

                if not values:
                    self.add_error(f"Entity '{entity_name}': type 'fixed' requires 'values' field", entity=entity_name, field="values")
                    valid = False
                    continue

                # Check if it's a list of values
                if isinstance(values, list):
                    columns = entity_data.get("columns", [])

                    if not columns:
                        self.add_error(
                            f"Entity '{entity_name}': type 'fixed' requires 'columns' field", entity=entity_name, field="columns"
                        )
                        valid = False
                        continue

                    # Each value should be a list matching columns length
                    for idx, value_row in enumerate(values):
                        if isinstance(value_row, list):
                            if len(value_row) != len(columns):
                                self.add_error(
                                    f"Entity '{entity_name}': value row {idx + 1} has {len(value_row)} items but {len(columns)} columns defined",  # noqa: E501
                                    entity=entity_name,
                                    field="values",
                                )
                                valid = False
                        else:
                            self.add_warning(
                                f"Entity '{entity_name}': value row {idx + 1} is not a list", entity=entity_name, field="values"
                            )

                # Warn if source is not None (shouldn't be used for fixed data)
                if entity_data.get("source") is not None:
                    self.add_warning(
                        f"Entity '{entity_name}': fixed data table has 'source' field (should be null)", entity=entity_name, field="source"
                    )
        return valid


class DataSourceExistsSpecification(ProjectSpecification):
    """Validates that all referenced data sources exist in options.data_sources."""

    def is_satisfied_by(self, config: dict[str, Any]) -> bool:
        """Check if all referenced data sources exist."""
        self.clear()
        valid = True

        entities_config = config.get("entities", {})
        options = config.get("options", {})
        data_sources = options.get("data_sources", {})

        if not entities_config:
            return True

        for entity_name, entity_data in entities_config.items():
            # Check entity data_source
            data_source = entity_data.get("data_source")
            if data_source and isinstance(data_source, str):
                if data_source not in data_sources:
                    self.add_error(
                        f"Entity '{entity_name}': references non-existent data source '{data_source}'",
                        entity=entity_name,
                        field="data_source",
                    )
                    valid = False

            # Check append configurations
            append_configs = entity_data.get("append", []) or []
            if append_configs and not isinstance(append_configs, list):
                append_configs = [append_configs]

            for idx, append_cfg in enumerate(append_configs):
                append_data_source = append_cfg.get("data_source")
                if append_data_source and isinstance(append_data_source, str):
                    if append_data_source not in data_sources:
                        self.add_error(
                            f"Entity '{entity_name}', append item #{idx + 1}: references non-existent data source '{append_data_source}'",
                            entity=entity_name,
                            field="append",
                        )
                        valid = False

        return valid


class AppendConfigurationSpecification(ProjectSpecification):
    """Validates append configuration settings."""

    def is_satisfied_by(self, config: dict[str, Any]) -> bool:
        """Check that append configurations are valid."""
        self.clear()
        valid = True

        entities_config = config.get("entities", {})
        if not entities_config:
            return True

        for entity_name, entity_data in entities_config.items():
            append_configs = entity_data.get("append", []) or []
            if append_configs and not isinstance(append_configs, list):
                append_configs = [append_configs]

            append_mode = entity_data.get("append_mode", "all")

            # Validate append_mode if present
            if append_configs:
                if append_mode not in ["all", "distinct"]:
                    self.add_error(
                        f"Entity '{entity_name}': invalid append_mode '{append_mode}'. Must be 'all' or 'distinct'",
                        entity=entity_name,
                        field="append_mode",
                    )
                    valid = False

            # Validate each append configuration
            for idx, append_cfg in enumerate(append_configs):
                append_id = f"Entity '{entity_name}', append item #{idx + 1}"

                append_type = append_cfg.get("type")
                append_source = append_cfg.get("source")

                # Must have either type or source, but not both
                if not append_type and not append_source:
                    self.add_error(f"{append_id}: must specify either 'type' or 'source'", entity=entity_name, field="append")
                    valid = False
                    continue

                if append_type and append_source:
                    self.add_error(f"{append_id}: cannot specify both 'type' and 'source'", entity=entity_name, field="append")
                    valid = False
                    continue

                # Validate type-based append
                if append_type:
                    if append_type not in ["fixed", "sql"]:
                        self.add_error(
                            f"{append_id}: invalid type '{append_type}'. Must be 'fixed' or 'sql'", entity=entity_name, field="append"
                        )
                        valid = False

                    if append_type == "fixed":
                        # Fixed type requires values
                        if not append_cfg.get("values"):
                            self.add_error(f"{append_id}: type 'fixed' requires 'values' field", entity=entity_name, field="append")
                            valid = False
                        else:
                            values = append_cfg.get("values", [])
                            if not isinstance(values, list):
                                self.add_error(f"{append_id}: 'values' must be a list", entity=entity_name, field="append")
                                valid = False
                            elif len(values) == 0:
                                self.add_warning(f"{append_id}: 'values' is empty", entity=entity_name, field="append")

                    elif append_type == "sql":
                        # SQL type requires query
                        if not append_cfg.get("query"):
                            self.add_error(f"{append_id}: type 'sql' requires 'query' field", entity=entity_name, field="append")
                            valid = False

                # Validate source-based append
                if append_source:
                    # Check if source entity exists
                    if append_source not in entities_config:
                        self.add_error(f"{append_id}: source entity '{append_source}' does not exist", entity=entity_name, field="append")
                        valid = False

                    # Source-based append should have columns mapping
                    if not append_cfg.get("columns"):
                        self.add_warning(
                            f"{append_id}: source-based append should specify 'columns' mapping for clarity",
                            entity=entity_name,
                            field="append",
                        )

        return valid


class CompositeProjectSpecification(ProjectSpecification):
    """Composite specification that runs multiple validation specifications."""

    def __init__(self, specifications: list[ProjectSpecification] | None = None) -> None:
        super().__init__()
        self.specifications = specifications or [
            RequiredFieldsSpecification(),
            EntityExistsSpecification(),
            CircularDependencySpecification(),
            DataSourceExistsSpecification(),
            SqlDataSpecification(),
            FixedDataSpecification(),
            ForeignKeySpecification(),
            UnnestSpecification(),
            DropDuplicatesSpecification(),
            SurrogateIdSpecification(),
            AppendConfigurationSpecification(),
        ]

    def is_satisfied_by(self, config: dict[str, Any]) -> bool:
        """Run all specifications and aggregate results."""
        self.clear()
        all_valid = True

        for spec in self.specifications:
            is_valid = spec.is_satisfied_by(config)

            if not is_valid:
                all_valid = False

            # Aggregate errors and warnings
            self.errors.extend(spec.errors)
            self.warnings.extend(spec.warnings)

        return all_valid

    def get_report(self) -> str:
        """Generate a human-readable validation report."""
        lines = []

        if not self.has_errors() and not self.has_warnings():
            lines.append("✓ Configuration is valid")
            return "\n".join(lines)

        if self.has_errors():
            lines.append(f"✗ Configuration has {len(self.errors)} error(s):")
            for idx, error in enumerate(self.errors, 1):
                lines.append(f"  {idx}. {error}")

        if self.has_warnings():
            lines.append(f"\n⚠ Configuration has {len(self.warnings)} warning(s):")
            for idx, warning in enumerate(self.warnings, 1):
                lines.append(f"  {idx}. {warning}")

        return "\n".join(lines)
