from abc import ABC, abstractmethod
from typing import Any

import pandas as pd

from src.arbodat.config_model import ForeignKeyConfig, TableConfig, TablesConfig


class ForeignKeyConfigSpecification:
    """Specification that tests if a foreign key relationship is resolveble.
    Returns True if all local and remote keys exist, False if any are missing,
    or None if resolvable after unnesting some local keys are in unnest columns.
    """

    def __init__(self, cfg: "TablesConfig") -> None:
        self.cfg: TablesConfig = cfg
        self.error: str = ""
        self.deferred: bool = False

    def clear(self) -> None:
        self.error = ""
        self.deferred = False

    def is_satisfied_by(self, *, fk_cfg: ForeignKeyConfig) -> bool | None:
        self.clear()
        missing_keys: set[str]
        cfg_local_table: TableConfig = self.cfg.get_table(fk_cfg.local_entity)
        cfg_remote_table: TableConfig = self.cfg.get_table(fk_cfg.remote_entity)

        if fk_cfg.how == "cross":
            if fk_cfg.local_keys or fk_cfg.remote_keys:
                self.error = f"Linking {fk_cfg.local_entity} -> {fk_cfg.remote_entity}: 'cross' join should not specify local_keys or remote_keys"
                return False
            return True

        if len(fk_cfg.local_keys) == 0 or len(fk_cfg.remote_keys) == 0:
            self.error = f"Linking {fk_cfg.local_entity} -> {fk_cfg.remote_entity}: local_keys and remote_keys must be specified for non-cross joins"
            return False

        if len(fk_cfg.local_keys) != len(fk_cfg.remote_keys):
            self.error = f"Linking {fk_cfg.local_entity} -> {fk_cfg.remote_entity}: number of local_keys ({len(fk_cfg.local_keys)}) does not match number of remote_keys ({len(fk_cfg.remote_keys)})"
            return False

        missing_keys = self.get_missing_keys(
            required_keys=set(fk_cfg.local_keys), columns=set(cfg_local_table.usage_columns) | set(cfg_local_table.pending_columns), pending_columns=set()
        )

        if missing_keys:
            self.error = f"Linking {fk_cfg.local_entity} -> {fk_cfg.remote_entity}: local keys {missing_keys} not found in local entity '{fk_cfg.local_entity}'"
            return False

        missing_keys: set[str] = self.get_missing_keys(
            required_keys=set(fk_cfg.remote_keys), columns=set(cfg_remote_table.usage_columns), pending_columns=set()
        )

        if missing_keys:
            self.error = (
                f"Linking {fk_cfg.local_entity} -> {fk_cfg.remote_entity}: remote keys {missing_keys} not found in remote entity '{fk_cfg.remote_entity}'"
            )
            return False

        return True

    def get_missing_keys(self, *, required_keys: set[str], columns: set[str], pending_columns) -> set[str]:

        missing_keys: set[str] = {key for key in required_keys if key not in columns.union(pending_columns)}

        return missing_keys


class ForeignKeyDataSpecification(ForeignKeyConfigSpecification):
    """Checks if local and remote keys are present in the actual table data (pandas.DataFrames)."""

    def __init__(self, table_store: dict[str, pd.DataFrame], cfg: "TablesConfig") -> None:
        super().__init__(cfg)
        self.table_store: dict[str, pd.DataFrame] = table_store

    def is_satisfied_by(self, *, fk_cfg: ForeignKeyConfig) -> bool:
        missing_keys: set[str]

        assert fk_cfg.local_entity in self.table_store, f"Local DataFrame for entity '{fk_cfg.local_entity}' not found"
        assert fk_cfg.remote_entity in self.table_store, f"Remote DataFrame for entity '{fk_cfg.remote_entity}' not found"

        is_config_ok: bool | None = super().is_satisfied_by(fk_cfg=fk_cfg)
        if is_config_ok is not True:
            return False

        table: pd.DataFrame = self.table_store[fk_cfg.local_entity]

        missing_keys = self.get_missing_keys(
            required_keys=set(fk_cfg.local_keys),
            columns=set(table.columns),
            pending_columns=set(self.cfg.get_table(fk_cfg.local_entity).pending_columns),
        )
        if missing_keys:
            if missing_keys == self.cfg.get_table(fk_cfg.local_entity).pending_columns:
                self.deferred = True
            else:
                self.error = (
                    f"Linking {fk_cfg.local_entity} -> {fk_cfg.remote_entity}: local keys {missing_keys} not found in local entity data '{fk_cfg.local_entity}'"
                )
                return False

        missing_pending_keys: set[str] = self.get_missing_keys(
            required_keys=self.cfg.get_table(fk_cfg.local_entity).pending_columns,
            columns=set(table.columns),
            pending_columns=set(),
        )

        if missing_pending_keys:
            self.deferred = True
            return True

        missing_keys = self.get_missing_keys(
            required_keys=set(fk_cfg.remote_keys), columns=set(self.table_store[fk_cfg.remote_entity].columns), pending_columns=set()
        )
        if missing_keys:
            self.error = (
                f"Linking {fk_cfg.local_entity} -> {fk_cfg.remote_entity}: remote keys {missing_keys} not found in remote entity data '{fk_cfg.remote_entity}'"
            )
            return False

        return True


# ============================================================================
# Configuration Validation Specifications
# ============================================================================


class ConfigSpecification(ABC):
    """Base specification for configuration validation."""

    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

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
        pass

    def add_error(self, error: str) -> None:
        """Add an error message."""
        self.errors.append(error)

    def add_warning(self, warning: str) -> None:
        """Add a warning message."""
        self.warnings.append(warning)

    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0


class EntityExistsSpecification(ConfigSpecification):
    """Validates that all referenced entities exist in the configuration."""

    def is_satisfied_by(self, config: dict[str, Any]) -> bool:
        """Check if all entities referenced in foreign keys and dependencies exist."""
        self.clear()
        valid = True

        entities_config = config.get("entities", {})
        if not entities_config:
            self.add_error("Configuration must contain 'entities' section")
            return False

        entity_names = set(entities_config.keys())

        for entity_name, entity_data in entities_config.items():
            # Check foreign key references
            foreign_keys = entity_data.get("foreign_keys", []) or []
            for fk in foreign_keys:
                remote_entity = fk.get("entity", "")
                if not remote_entity:
                    self.add_error(f"Entity '{entity_name}': foreign key missing 'entity' field")
                    valid = False
                elif remote_entity not in entity_names:
                    self.add_error(f"Entity '{entity_name}': references non-existent entity '{remote_entity}' in foreign key")
                    valid = False

            # Check depends_on references
            depends_on = entity_data.get("depends_on", []) or []
            for dep in depends_on:
                if dep not in entity_names:
                    self.add_error(f"Entity '{entity_name}': depends on non-existent entity '{dep}'")
                    valid = False

            # Check source references (for derived tables)
            source = entity_data.get("source", None)
            if source and isinstance(source, str) and source not in entity_names:
                self.add_error(f"Entity '{entity_name}': references non-existent source entity '{source}'")
                valid = False

        return valid


class CircularDependencySpecification(ConfigSpecification):
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
                    self.add_error(f"Circular dependency detected: {cycle_path}")
                    return True

            path.pop()
            rec_stack.remove(node)
            return False

        valid = True
        for entity in dependencies.keys():
            if entity not in visited:
                if has_cycle(entity):
                    valid = False

        return valid


class RequiredFieldsSpecification(ConfigSpecification):
    """Validates that all required fields are present in entity configurations."""

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
                    self.add_error(f"Entity '{entity_name}': fixed data table missing required 'surrogate_id'")
                    valid = False

                if not entity_data.get("columns"):
                    self.add_error(f"Entity '{entity_name}': fixed data table missing required 'columns'")
                    valid = False

                if not entity_data.get("values"):
                    self.add_error(f"Entity '{entity_name}': fixed data table missing required 'values'")
                    valid = False
            else:
                # Regular data tables require: columns (or keys)
                if not entity_data.get("columns") and not entity_data.get("keys"):
                    self.add_error(f"Entity '{entity_name}': data table must have 'columns' or 'keys'")
                    valid = False

        return valid


class ForeignKeySpecification(ConfigSpecification):
    """Validates foreign key configurations."""

    def is_satisfied_by(self, config: dict[str, Any]) -> bool:
        """Check that foreign key configurations are valid."""
        self.clear()
        valid = True

        entities_config = config.get("entities", {})
        if not entities_config:
            return True

        for entity_name, entity_data in entities_config.items():
            foreign_keys = entity_data.get("foreign_keys", []) or []

            for idx, fk in enumerate(foreign_keys):
                fk_id = f"Entity '{entity_name}', foreign key #{idx + 1}"

                # Check required fields
                if not fk.get("entity"):
                    self.add_error(f"{fk_id}: missing required field 'entity'")
                    valid = False
                    continue

                if not fk.get("local_keys"):
                    self.add_error(f"{fk_id}: missing required field 'local_keys'")
                    valid = False

                if not fk.get("remote_keys"):
                    self.add_error(f"{fk_id}: missing required field 'remote_keys'")
                    valid = False

                # Check that local_keys and remote_keys have same length
                local_keys = fk.get("local_keys", []) or []
                remote_keys = fk.get("remote_keys", []) or []

                if len(local_keys) != len(remote_keys):
                    self.add_error(f"{fk_id}: 'local_keys' length ({len(local_keys)}) does not match 'remote_keys' length ({len(remote_keys)})")
                    valid = False

                # Validate extra_columns format
                extra_columns = fk.get("extra_columns")
                if extra_columns is not None:
                    if not isinstance(extra_columns, (str, list, dict)):
                        self.add_error(f"{fk_id}: 'extra_columns' must be string, list, or dict")
                        valid = False

        return valid


class UnnestSpecification(ConfigSpecification):
    """Validates unnest configurations."""

    def is_satisfied_by(self, config: dict[str, Any]) -> bool:
        """Check that unnest configurations are valid."""
        self.clear()
        valid = True

        entities_config = config.get("entities", {})
        if not entities_config:
            return True

        for entity_name, entity_data in entities_config.items():
            unnest = entity_data.get("unnest")

            if unnest:
                # Check required fields
                if not unnest.get("value_vars"):
                    self.add_error(f"Entity '{entity_name}': unnest configuration missing required 'value_vars'")
                    valid = False

                if not unnest.get("var_name"):
                    self.add_error(f"Entity '{entity_name}': unnest configuration missing required 'var_name'")
                    valid = False

                if not unnest.get("value_name"):
                    self.add_error(f"Entity '{entity_name}': unnest configuration missing required 'value_name'")
                    valid = False

                # Warn if id_vars is missing (it's optional but usually needed)
                if not unnest.get("id_vars"):
                    self.add_warning(f"Entity '{entity_name}': unnest configuration missing 'id_vars' (may cause issues)")

        return valid


class DropDuplicatesSpecification(ConfigSpecification):
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
                    self.add_error(f"Entity '{entity_name}': 'drop_duplicates' must be boolean, string, or list of columns")
                    valid = False

        return valid


class SurrogateIdSpecification(ConfigSpecification):
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
                    self.add_warning(f"Entity '{entity_name}': surrogate_id '{surrogate_id}' does not follow convention (should end with '_id')")

                # Track for uniqueness check
                if surrogate_id not in surrogate_ids:
                    surrogate_ids[surrogate_id] = []
                surrogate_ids[surrogate_id].append(entity_name)

        # Check for duplicate surrogate IDs
        for surrogate_id, entities in surrogate_ids.items():
            if len(entities) > 1:
                self.add_error(f"Surrogate ID '{surrogate_id}' is used by multiple entities: {', '.join(entities)}")
                valid = False

        return valid


class FixedDataSpecification(ConfigSpecification):
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
                    continue  # RequiredFieldsSpecification will catch this

                # Check if it's SQL
                if isinstance(values, str) and values.strip().startswith("sql:"):
                    sql = values.strip()[4:].strip()
                    if not sql:
                        self.add_error(f"Entity '{entity_name}': empty SQL query in 'values'")
                        valid = False
                    continue

                # Check if it's a list of values
                if isinstance(values, list):
                    columns = entity_data.get("columns", [])

                    if not columns:
                        continue  # RequiredFieldsSpecification will catch this

                    # Each value should be a list matching columns length
                    for idx, value_row in enumerate(values):
                        if isinstance(value_row, list):
                            if len(value_row) != len(columns):
                                self.add_error(f"Entity '{entity_name}': value row {idx + 1} has {len(value_row)} items but {len(columns)} columns defined")
                                valid = False

                # Warn if source is not None (shouldn't be used for fixed data)
                if entity_data.get("source") is not None:
                    self.add_warning(f"Entity '{entity_name}': fixed data table has 'source' field (should be null)")

        return valid


class CompositeConfigSpecification(ConfigSpecification):
    """Composite specification that runs multiple validation specifications."""

    def __init__(self, specifications: list[ConfigSpecification] | None = None) -> None:
        super().__init__()
        self.specifications = specifications or [
            RequiredFieldsSpecification(),
            EntityExistsSpecification(),
            CircularDependencySpecification(),
            ForeignKeySpecification(),
            UnnestSpecification(),
            DropDuplicatesSpecification(),
            SurrogateIdSpecification(),
            FixedDataSpecification(),
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
