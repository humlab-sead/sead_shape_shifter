"""Specifications for validating entity configurations."""

from typing import Any

from src.model import TableConfig
from src.transforms.dsl import FormulaEngine, extract_column_references
from src.transforms.extra_columns import ExtraColumnEvaluator
from src.transforms.filter import Filters, normalize_filter_stage
from src.utility import Registry, dotget

from .base import ProjectSpecification


class EntitySpecificationRegistry(Registry[type[ProjectSpecification]]):
    """Registry for field validators."""

    items: dict[str, type[ProjectSpecification]] = {}


class EntityTypeSpecificationRegistry(Registry[type[ProjectSpecification]]):
    """Registry for entity type validators."""

    items: dict[str, type[ProjectSpecification]] = {}


ENTITY_SPECIFICATION = EntitySpecificationRegistry()
ENTITY_TYPE_SPECIFICATION = EntityTypeSpecificationRegistry()


@ENTITY_TYPE_SPECIFICATION.register(key="other")
class EntityFieldsBaseSpecification(ProjectSpecification):
    """Validates that fields are present for a single entity."""

    def is_satisfied_by(self, *, entity_name: str = "unknown", **kwargs) -> bool:
        """Check that fields are for the entity."""
        self.clear()

        for field in ["keys", "columns"]:
            self.check_fields(entity_name, [field], "exists/E")
            if self.field_exists(f"entities.{entity_name}.{field}"):
                self.check_fields(entity_name, [field], "is_string_list/E")

        # Validate that keys are a subset of columns
        # self.check_fields(entity_name, ["keys"], "keys_subset_of_columns/E")

        self.check_fields(entity_name, ["type"], "exists/E")
        if self.field_exists(f"entities.{entity_name}.type"):
            self.check_fields(entity_name, ["type"], "of_type/E", expected_types=(str,))

        if self.field_exists(f"entities.{entity_name}.surrogate_name"):
            self.check_fields(entity_name, ["surrogate_name"], "is_in_columns/E")

        return not self.has_errors()


@ENTITY_TYPE_SPECIFICATION.register(key="entity")
class DataEntityFieldsSpecification(EntityFieldsBaseSpecification):
    """Validates that fields are present for a data entity."""

    def is_satisfied_by(self, *, entity_name: str = "unknown", **kwargs) -> bool:
        """Check that fields are for the data entity."""
        super().is_satisfied_by(entity_name=entity_name, **kwargs)
        self.check_fields(
            entity_name,
            ["data_source", "query"],
            "is_absent/E",
            message="Non-sql data entities should not have data_source or query fields",
        )
        return not self.has_errors()


@ENTITY_TYPE_SPECIFICATION.register(key="fixed")
class FixedEntityFieldsSpecification(DataEntityFieldsSpecification):

    def is_satisfied_by(self, *, entity_name: str = "unknown", **kwargs) -> bool:
        """Check that fields are for the fixed entity."""
        super().is_satisfied_by(entity_name=entity_name, **kwargs)

        table: TableConfig = self.get_entity(entity_name)

        if table.type != "fixed":
            self.add_error(f"Entity '{entity_name}' is not of type 'fixed'", entity=entity_name, field="type")

        # Validate required identity fields
        entity_cfg = self.get_entity_cfg(entity_name)

        # Check for public_id (required for fixed entities)
        public_id = entity_cfg.get("public_id") or entity_cfg.get("surrogate_id")
        if not public_id:
            self.add_error(f"Entity '{entity_name}': Field 'public_id' is required but missing.", entity=entity_name, field="public_id")
            return not self.has_errors()  # Can't proceed without public_id

        # Note: system_id is always "system_id" (standardized name, auto-generated)

        self.check_fields(entity_name, ["values"], "exists/E,not_empty/W")
        self.check_fields(entity_name, ["type"], "has_value/E", expected_value="fixed")
        self.check_fields(entity_name, ["source", "data_source", "query"], "is_empty/W")
        self.check_fields(entity_name, ["values"], "of_type/E", expected_types=(list,))

        columns: list[str] = table.safe_columns
        raw_values: list[Any] | None = table.values if isinstance(table.values, list) else None
        dict_rows = raw_values is not None and len(raw_values) > 0 and all(isinstance(row, dict) for row in raw_values)
        values: list[Any] = raw_values if dict_rows and raw_values is not None else table.safe_values

        if dict_rows:
            row_keys = set().union(*(row.keys() for row in raw_values)) if raw_values else set()
            missing_columns = set(columns) - row_keys
            if missing_columns:
                self.add_error(
                    f"Fixed data entity '{entity_name}' has externally loaded rows missing columns {sorted(missing_columns)}",
                    entity=entity_name,
                    field="values",
                )
                return not self.has_errors()
        elif not all(isinstance(row, list) for row in values):
            self.add_error(f"Fixed data entity '{entity_name}' must have values as a list of lists", entity=entity_name, field="values")

        # Check for empty columns with non-empty values (mixed format error)
        if not columns and values:
            self.add_error(
                f"Fixed data entity '{entity_name}' has values but no columns defined. "
                f"Either specify column names in 'columns' field or use dict-style values.",
                entity=entity_name,
                field="columns",
            )
            return not self.has_errors()  # Cannot proceed with further validation

        # Validate values array length
        # Two valid formats:
        # 1. Old format: values match columns exactly (backward compatibility)
        # 2. New format: values include identity columns (system_id, public_id)
        #    Using set union elegantly deduplicates if identity columns are mistakenly in columns
        if values and not dict_rows:
            expected_with_identity: int = len(set(columns) | {public_id, "system_id"})
            expected_without_identity: int = len(columns)
            values_length: int = len(values[0]) if values else 0

            # Check all rows have consistent length
            if not all(len(row) == values_length for row in values):
                self.add_error(
                    f"Fixed data entity '{entity_name}' has inconsistent row lengths in values",
                    entity=entity_name,
                    field="values",
                )
            # Accept either old format (data only) or new format (with identity columns)
            elif values_length not in (expected_without_identity, expected_with_identity):
                self.add_error(
                    f"Fixed data entity '{entity_name}' has mismatched number of columns and values "
                    f"(got {values_length} values per row, expected {expected_without_identity} for data-only "
                    f"or {expected_with_identity} with identity columns)",
                    entity=entity_name,
                    field="values",
                )

        return not self.has_errors()


@ENTITY_TYPE_SPECIFICATION.register(key="sql")
class SqlEntityFieldsSpecification(EntityFieldsBaseSpecification):
    """Validates that fields are present for a SQL entity."""

    def is_satisfied_by(self, *, entity_name: str = "unknown", **kwargs) -> bool:
        """Check that fields are for the SQL entity."""
        super().is_satisfied_by(entity_name=entity_name, **kwargs)
        self.check_fields(entity_name, ["data_source", "query"], "not_empty_string/E")
        return not self.has_errors()


@ENTITY_SPECIFICATION.register(key="sql_column_configuration")
class SqlColumnConfigurationSpecification(ProjectSpecification):
    """Validates SQL column configuration that can be checked without executing the query."""

    def is_satisfied_by(self, *, entity_name: str = "unknown", **kwargs) -> bool:
        self.clear()

        table: TableConfig = self.get_entity(entity_name)
        if table.type != "sql":
            return True

        entity_cfg: dict[str, Any] = self.get_entity_cfg(entity_name)
        raw_columns = entity_cfg.get("columns") or []
        configured_columns: list[str] = table.safe_columns
        auto_detect_columns: bool = True if table.auto_detect_columns is None else bool(table.auto_detect_columns)

        if isinstance(raw_columns, list) and len(raw_columns) != len(set(raw_columns)):
            self.add_error(
                f"Entity '{entity_name}': configured columns contain duplicates, which is not allowed.",
                entity=entity_name,
                field="columns",
            )

        if not auto_detect_columns and not configured_columns:
            self.add_error(
                f"Entity '{entity_name}': no columns specified in configuration, and auto-detect is disabled.",
                entity=entity_name,
                field="columns",
            )

        if not auto_detect_columns:
            missing_keys: list[str] = [key for key in table.keys if key not in configured_columns]
            if missing_keys:
                self.add_error(
                    f"Entity '{entity_name}': key column(s) {missing_keys} must be included in the "
                    "specified columns when auto-detect is disabled.",
                    entity=entity_name,
                    field="columns",
                )

        return not self.has_errors()


@ENTITY_SPECIFICATION.register(key="non_fixed_identity_columns")
class NonFixedIdentityColumnsSpecification(ProjectSpecification):
    """Validates that non-fixed entities do not declare derived system_id columns in `columns`."""

    def is_satisfied_by(self, *, entity_name: str = "unknown", **kwargs) -> bool:
        self.clear()

        table: TableConfig = self.get_entity(entity_name)
        if table.type == "fixed":
            return True

        configured_columns: set[str] = set(table.safe_columns)
        forbidden_columns: list[str] = sorted(configured_columns & {table.system_id})

        if forbidden_columns:
            self.add_error(
                f"Entity '{entity_name}': non-fixed entities must not include derived system_id columns in 'columns': {forbidden_columns}. "
                "These columns are added later in the pipeline.",
                entity=entity_name,
                field="columns",
            )

        return not self.has_errors()


@ENTITY_SPECIFICATION.register(key="fixed_entity_system_id")
class FixedEntitySystemIdSpecification(ProjectSpecification):
    """Validates system_id integrity for fixed entities.

    Ensures that fixed entities have valid, stable system_id values:
    - All system_id values must be present (no nulls)
    - All system_id values must be unique
    - All system_id values must be positive integers

    This is critical for FK relationship stability when rows are added/deleted/reordered.
    """

    def is_satisfied_by(self, *, entity_name: str = "unknown", **kwargs) -> bool:
        """Check that system_id values are valid for fixed entity."""
        self.clear()

        table: TableConfig = self.get_entity(entity_name)

        # Only validate fixed entities
        if table.type != "fixed":
            return True

        columns: list[str] = table.safe_columns
        raw_values: list[Any] | None = table.values if isinstance(table.values, list) else None
        dict_rows = raw_values is not None and len(raw_values) > 0 and all(isinstance(row, dict) for row in raw_values)
        values: list[list[Any]] = table.safe_values

        # Check if system_id column exists
        if "system_id" not in columns:
            # system_id is optional, but if missing it will be auto-generated
            return True

        if dict_rows and raw_values is not None:
            system_id_values = [row.get("system_id") for row in raw_values]
        else:
            system_id_index = columns.index("system_id")
            system_id_values = [row[system_id_index] for row in values]

        # Validate: No null/None values
        null_count = sum(
            1
            for val in system_id_values
            if val is None or (isinstance(val, float) and val != val)  # pylint: disable=comparison-with-itself
        )
        if null_count > 0:
            self.add_error(
                f"Entity '{entity_name}': system_id column has {null_count} null value(s). All system_id values must be present.",
                entity=entity_name,
                field="values",
                code="SYSTEM_ID_NULL_VALUES",
            )

        # Filter out nulls for uniqueness/type checks
        non_null_values = [
            val
            for val in system_id_values
            if val is not None and not (isinstance(val, float) and val != val)  # pylint: disable=comparison-with-itself
        ]

        if non_null_values:
            # Validate: All values are positive integers
            for i, val in enumerate(non_null_values):
                try:
                    int_val = int(val)
                    if int_val <= 0:
                        self.add_error(
                            f"Entity '{entity_name}': system_id value '{val}' at row {i} must be a positive integer.",
                            entity=entity_name,
                            field="values",
                            code="SYSTEM_ID_INVALID_VALUE",
                        )
                except (ValueError, TypeError):
                    self.add_error(
                        f"Entity '{entity_name}': system_id value '{val}' at row {i} is not a valid integer.",
                        entity=entity_name,
                        field="values",
                        code="SYSTEM_ID_INVALID_TYPE",
                    )

            # Validate: All values are unique
            seen = set()
            duplicates = set()
            for val in non_null_values:
                if val in seen:
                    duplicates.add(val)
                seen.add(val)

            if duplicates:
                dup_list = ", ".join(str(d) for d in sorted(duplicates))
                self.add_error(
                    f"Entity '{entity_name}': system_id has duplicate values: {dup_list}. All system_id values must be unique.",
                    entity=entity_name,
                    field="values",
                    code="SYSTEM_ID_DUPLICATE_VALUES",
                )

        return not self.has_errors()


@ENTITY_SPECIFICATION.register(key="entity_fields")
class EntityFieldsSpecification(ProjectSpecification):
    """Validates that all required fields are present in all entities."""

    def get_specification(self, *, entity_type: str) -> ProjectSpecification:
        """Get the appropriate specification based on entity type."""
        spec_cls: type[ProjectSpecification] = (
            ENTITY_TYPE_SPECIFICATION.get(entity_type)
            if ENTITY_TYPE_SPECIFICATION.is_registered(entity_type)
            else EntityFieldsBaseSpecification
        )

        return spec_cls(self.project_cfg)

    def is_satisfied_by(self, *, entity_name: str = "unknown", **kwargs) -> bool:
        """Check that entity's fields are valid (based on entity type)."""
        self.clear()
        entity: TableConfig = self.get_entity(entity_name)
        specification: ProjectSpecification = self.get_specification(entity_type=str(entity.type))
        specification.is_satisfied_by(entity_name=entity_name)
        self.merge(specification)
        return not self.has_errors()


@ENTITY_SPECIFICATION.register(key="unnest")
class UnnestSpecification(ProjectSpecification):
    """Validates unnest setups."""

    def is_satisfied_by(self, *, entity_name: str = "unknown", **kwargs) -> bool:
        """Check that entity's unnest setups are valid."""
        self.clear()

        unnest_cfgs = self.get_entity_cfg(entity_name).get("unnest", []) or []
        if not unnest_cfgs:
            return True

        self.check_fields(entity_name, ["unnest.value_vars", "unnest.var_name", "unnest.value_name"], "exists/E")
        self.check_fields(entity_name, ["unnest.id_vars"], "exists/W")
        self.check_fields(entity_name, ["unnest.value_vars"], "is_string_list/E")
        self.check_fields(entity_name, ["unnest.var_name", "unnest.value_name"], "not_empty_string/E")

        return not self.has_errors()


@ENTITY_SPECIFICATION.register(key="drop_duplicates")
class DropDuplicatesSpecification(ProjectSpecification):
    """Validates drop_duplicates configurations."""

    def is_satisfied_by(self, *, entity_name: str = "unknown", **kwargs) -> bool:
        """Check that drop_duplicates configurations are valid."""
        self.clear()

        entity_cfg: dict[str, Any] = self.get_entity_cfg(entity_name)
        drop_dup = entity_cfg.get("drop_duplicates")

        if drop_dup is None:
            return True

        # Can be bool, string (include directive), list, or dict
        self.check_fields(entity_name, ["drop_duplicates"], "of_type/E", expected_types=(bool, str, list, dict))

        if isinstance(drop_dup, list):
            self.check_fields(entity_name, ["drop_duplicates"], "is_string_list/E")
        elif isinstance(drop_dup, dict):
            # Dict format must have a "columns" key
            if "columns" not in drop_dup:
                self.add_error("dict format requires 'columns' key", entity=entity_name, field="drop_duplicates")
            else:
                columns = drop_dup["columns"]
                # Columns must be bool, string, or list
                if not isinstance(columns, (bool, str, list)):
                    self.add_error(
                        f"must be bool, string, or list[string], got {type(columns).__name__}",
                        entity=entity_name,
                        field="drop_duplicates.columns",
                    )
                elif isinstance(columns, list):
                    # If list, all items must be strings
                    non_strings = [item for item in columns if not isinstance(item, str)]
                    if non_strings:
                        self.add_error("list items must all be strings", entity=entity_name, field="drop_duplicates.columns")
            # Optional functional dependency settings
            for opt_key in ["check_functional_dependency", "strict_functional_dependency"]:
                if opt_key in drop_dup and not isinstance(drop_dup[opt_key], bool):
                    self.add_error(
                        f"must be bool, got {type(drop_dup[opt_key]).__name__}",
                        entity=entity_name,
                        field=f"drop_duplicates.{opt_key}",
                    )
        return not self.has_errors()


@ENTITY_SPECIFICATION.register(key="foreign_keys")
class ForeignKeySpecification(ProjectSpecification):
    """Validates foreign key setups."""

    def is_satisfied_by(self, *, entity_name: str = "unknown", **kwargs) -> bool:
        """Check that foreign key configurations are valid."""
        self.clear()

        entity_cfg = self.get_entity_cfg(entity_name)

        fk_cfgs = entity_cfg.get("foreign_keys", []) or []

        for idx, fk in enumerate(fk_cfgs):
            fk_id: str = f"Entity '{entity_name}', foreign key #{idx + 1}"

            self.check_fields(entity_name, ["entity", "local_keys", "remote_keys"], "exists/E", target_cfg=fk, message=fk_id)
            self.check_fields(entity_name, ["local_keys", "remote_keys"], "is_string_list/E", target_cfg=fk, message=fk_id)

            if fk.get("how") is not None:
                self.check_fields(
                    entity_name,
                    ["how"],
                    "is_of_categorical_values/E",
                    categories=["inner", "left", "right", "outer", "cross"],
                    target_cfg=fk,
                    message=fk_id,
                )

            if fk.get("how") == "cross":
                self.check_fields(
                    entity_name,
                    ["local_keys", "remote_keys"],
                    "is_empty/E",
                    target_cfg=fk,
                    message=f"{fk_id}: 'cross' join should not specify local_keys or remote_keys",
                )

            self.same_number_of_join_keys(entity_name, fk, fk_id)

            if fk.get("extra_columns") is not None:
                self.check_fields(
                    entity_name, ["extra_columns"], "of_type/E", expected_types=(str, list, dict), target_cfg=fk, message=fk_id
                )

        return not self.has_errors()

    def same_number_of_join_keys(self, entity_name: str, fk: dict[str, Any], fk_id: str):
        """Check that local_keys and remote_keys have the same length."""
        local_keys: list[str] = fk.get("local_keys", []) or []
        remote_keys: list[str] = fk.get("remote_keys", []) or []

        if isinstance(local_keys, list) and isinstance(remote_keys, list):

            if len(local_keys) != len(remote_keys):
                self.add_error(
                    f"{fk_id}: 'local_keys' length ({len(local_keys)}) does not match 'remote_keys' length ({len(remote_keys)})",
                    entity=entity_name,
                    foreign_key=fk_id,
                )


@ENTITY_SPECIFICATION.register(key="public_id")
class PublicIdSpecification(ProjectSpecification):
    """Validates public_id configurations (target system PK and FK column pattern)."""

    def is_satisfied_by(self, *, entity_name: str = "unknown", **kwargs) -> bool:
        """Check that public_id follows naming conventions (must end with _id)."""
        self.clear()

        entity_cfg: dict[str, Any] = self.get_entity_cfg(entity_name)
        public_id = entity_cfg.get("public_id", "")

        self.check_fields(entity_name, ["public_id"], "exists/W")
        if public_id:
            self.check_fields(entity_name, ["public_id"], "of_type/E", expected_types=(str,))
            self.check_fields(entity_name, ["public_id"], "ends_with_id/E")

            source_entity_name = entity_cfg.get("source")
            if isinstance(source_entity_name, str) and source_entity_name:
                source_entity_cfg: dict[str, Any] = self.get_entity_cfg(source_entity_name)
                source_public_id = source_entity_cfg.get("public_id")
                if isinstance(source_public_id, str) and source_public_id == public_id:
                    self.add_error(
                        f"Entity '{entity_name}': public_id '{public_id}' conflicts with source entity '{source_entity_name}'. "
                        "A derived entity cannot use the same public_id as its source because that name is reserved "
                        "for the parent reference column.",
                        entity=entity_name,
                        field="public_id",
                    )

        return not self.has_errors()


@ENTITY_SPECIFICATION.register(key="extra_columns_expressions")
class ExtraColumnsExpressionSpecification(ProjectSpecification):
    """Preflight validation for entity-level extra_columns expressions.

    This validates expression syntax and impossible references before runtime while
    tolerating references that may resolve later through prior extra_columns,
    foreign-key linking, or unnesting.
    """

    def __init__(self, project_cfg: dict[str, Any]) -> None:
        super().__init__(project_cfg)
        self.formula_engine = FormulaEngine()

    def is_satisfied_by(self, *, entity_name: str = "unknown", **kwargs) -> bool:
        """Check that extra_columns expressions are structurally valid."""
        self.clear()

        entity_cfg: dict[str, Any] = self.get_entity_cfg(entity_name)
        extra_columns: Any = entity_cfg.get("extra_columns")

        if extra_columns is None:
            return True

        if not isinstance(extra_columns, dict):
            self.add_error(
                "'extra_columns' must be a dictionary mapping new column names to expressions or constants.",
                entity=entity_name,
                field="extra_columns",
            )
            return False

        current_available: set[str] = self.get_entity_columns(entity_name, include_types={"columns", "keys"})
        eventual_available: set[str] = self.get_entity_columns(entity_name, include_types={"columns", "keys", "foreign_keys", "unnest"})
        eventual_available.update(extra_columns.keys())

        for new_col, value in extra_columns.items():
            field_name = f"extra_columns.{new_col}"

            if not isinstance(value, str):
                current_available.add(new_col)
                continue

            if ExtraColumnEvaluator.is_escaped_equals_literal(value):
                current_available.add(new_col)
                continue

            if ExtraColumnEvaluator.is_dsl_formula(value):
                self._validate_formula_expression(entity_name, field_name, new_col, value, current_available, eventual_available)
                current_available.add(new_col)
                continue

            if ExtraColumnEvaluator.is_interpolated_string(value):
                self._validate_interpolated_expression(entity_name, field_name, new_col, value, current_available, eventual_available)
                current_available.add(new_col)
                continue

            current_available.add(new_col)

        return not self.has_errors()

    def _validate_formula_expression(
        self,
        entity_name: str,
        field_name: str,
        new_col: str,
        expression: str,
        current_available: set[str],
        eventual_available: set[str],
    ) -> None:
        try:
            ast = self.formula_engine.parse(expression)
        except Exception as exc:
            self.add_error(
                f"Invalid formula for extra_columns '{new_col}': {exc}. Expression: {expression!r}",
                entity=entity_name,
                field=field_name,
                expression=expression,
            )
            return

        references: set[str] = extract_column_references(ast)
        impossible: list[str] = sorted(reference for reference in references if reference not in eventual_available)

        if impossible:
            self.add_error(
                f"Formula for extra_columns '{new_col}' references columns that are never available in this entity: {impossible}. "
                f"Expression: {expression!r}",
                entity=entity_name,
                field=field_name,
                expression=expression,
            )
            return

        stage_order = sorted(reference for reference in references if reference not in current_available)
        if stage_order:
            self.add_warning(
                f"Formula for extra_columns '{new_col}' depends on columns not available at initial extraction time: {stage_order}. "
                f"This will rely on deferred evaluation after prior extra_columns, foreign keys, or unnesting. "
                f"Expression: {expression!r}",
                entity=entity_name,
                field=field_name,
                expression=expression,
            )

        try:
            self.formula_engine.validate(ast, eventual_available)
        except Exception as exc:
            self.add_error(
                f"Invalid formula for extra_columns '{new_col}': {exc}. Expression: {expression!r}",
                entity=entity_name,
                field=field_name,
                expression=expression,
            )

    def _validate_interpolated_expression(
        self,
        entity_name: str,
        field_name: str,
        new_col: str,
        expression: str,
        current_available: set[str],
        eventual_available: set[str],
    ) -> None:
        references = ExtraColumnEvaluator.extract_column_dependencies(expression)
        impossible = sorted(reference for reference in references if reference not in eventual_available)

        if impossible:
            self.add_error(
                f"Interpolated extra_columns '{new_col}' references columns that are never available in this entity: {impossible}. "
                f"Expression: {expression!r}",
                entity=entity_name,
                field=field_name,
                expression=expression,
            )
            return

        stage_order = sorted(reference for reference in references if reference not in current_available)
        if stage_order:
            self.add_warning(
                f"Interpolated extra_columns '{new_col}' depends on columns not available at initial extraction time: {stage_order}. "
                f"This will rely on deferred evaluation after prior extra_columns, foreign keys, or unnesting. "
                f"Expression: {expression!r}",
                entity=entity_name,
                field=field_name,
                expression=expression,
            )


@ENTITY_SPECIFICATION.register(key="extra_columns_conflicts")
class ExtraColumnsConflictsSpecification(ProjectSpecification):
    """Validates that extra_columns don't conflict with existing columns.

    Checks that extra_column names don't conflict with:
    - Columns from "columns" field
    - Business keys from "keys" field
    - Public ID from "public_id" field
    - System column "system_id"
    - Unnest columns (value_name, var_name)
    """

    def is_satisfied_by(self, *, entity_name: str = "unknown", **kwargs) -> bool:
        """Check that extra_columns don't conflict with existing columns.

        Note: Keys can be a mix of source columns and extra_columns. Only prevent
        overriding columns that actually exist in the source data or are system-generated.
        """
        self.clear()

        entities_cfg: dict[str, Any] = self.project_cfg.get("entities", {})
        table_cfg = TableConfig(entities_cfg=entities_cfg, entity_name=entity_name)

        if not table_cfg.extra_columns:
            return True

        # Only check actual source columns, not keys (keys can be added via extra_columns)
        existing_columns: set[str] = set(
            table_cfg.get_columns(include_keys=False, include_fks=False, include_extra=False, include_unnest=True)
        )
        existing_columns.add(table_cfg.system_id)
        if table_cfg.public_id:
            existing_columns.add(table_cfg.public_id)

        conflicts: set[str] = set(table_cfg.extra_columns.keys()) & existing_columns

        if conflicts:
            for conflict in sorted(conflicts):
                self.add_error(
                    f"extra_columns '{conflict}' conflicts with an existing result column in entity '{entity_name}'. "
                    "Rename the derived column instead of overriding source, system_id, public_id, or unnest output columns.",
                    entity=entity_name,
                    field="extra_columns",
                    expression=table_cfg.extra_columns.get(conflict),
                )

        return not self.has_errors()


@ENTITY_SPECIFICATION.register(key="append")
class AppendSpecification(ProjectSpecification):
    """Validates append configuration settings."""

    @staticmethod
    def _get_alignable_columns(columns: list[str] | None, public_id: str | None) -> tuple[list[str], list[str]]:
        """Split columns into alignable payload columns and excluded identity columns."""
        excluded_names = {"system_id"}
        if public_id:
            excluded_names.add(public_id)

        alignable: list[str] = []
        excluded: list[str] = []
        for column in columns or []:
            if column in excluded_names:
                excluded.append(column)
            else:
                alignable.append(column)
        return alignable, excluded

    def is_satisfied_by(self, *, entity_name: str = "unknown", **kwargs) -> bool:
        """Check that append configurations are valid."""
        self.clear()

        entity_cfg: dict[str, Any] = self.get_entity_cfg(entity_name)

        append_configs: list[dict[str, Any]] = entity_cfg.get("append", []) or []
        if append_configs and not isinstance(append_configs, list):
            append_configs = [append_configs]

        if not append_configs:
            return True

        self.check_fields(
            entity_name,
            ["append_mode"],
            "is_of_categorical_values/E",
            categories=["all", "distinct"],
            message="append_mode must be 'all' or 'distinct'",
        )

        # Validate each append configuration
        for idx, append_cfg in enumerate(append_configs):
            append_id = f"Entity '{entity_name}', append item #{idx + 1}"

            append_type = append_cfg.get("type")
            append_source = append_cfg.get("source")
            align_by_position = append_cfg.get("align_by_position", False)
            column_mapping = append_cfg.get("column_mapping")

            self.check_fields(
                entity_name, ["type", "source"], "of_type/E", expected_types=(str, None), target_cfg=append_cfg, message=append_id
            )

            # Validate append form: either type-only, source-only, or type+source
            if not append_type and not append_source:
                self.add_error(f"{append_id}: must specify either 'type' or 'source'", entity=entity_name, field="append")
                continue

            # If both type and source are specified, type MUST be "entity"
            if append_type and append_source:
                if append_type != "entity":
                    self.add_error(
                        f"{append_id}: when both 'type' and 'source' are specified, type must be 'entity' (got '{append_type}')",
                        entity=entity_name,
                        field="append",
                    )
                    continue

            # Validate type-based append (fixed, sql)
            if append_type and not append_source:
                self.check_fields(
                    entity_name,
                    ["type"],
                    "is_of_categorical_values/E",
                    categories=["fixed", "sql"],
                    target_cfg=append_cfg,
                    message=append_id,
                )
                if append_type == "fixed":
                    self.check_fields(entity_name, ["values"], "exists/E", target_cfg=append_cfg, message=append_id)
                    self.check_fields(
                        entity_name, ["values"], "of_type/E", expected_types=(list,), target_cfg=append_cfg, message=append_id
                    )
                    if isinstance(append_cfg.get("values"), list):
                        if len(append_cfg.get("values") or []) == 0:
                            self.add_warning(f"{append_id}: 'values' is empty", entity=entity_name, field="append")
                elif append_type == "sql":
                    self.check_fields(
                        entity_name, ["query"], "exists/E,of_type/E", expected_types=(str,), target_cfg=append_cfg, message=append_id
                    )

            # Validate source-based append (source alone or type: entity + source)
            if append_source:
                self.check_fields(entity_name, ["source"], "of_type/E", expected_types=(str,), target_cfg=append_cfg, message=append_id)
                self.check_fields(entity_name, ["source"], "is_existing_entity/E", target_cfg=append_cfg, message=append_id)
                self.check_fields(entity_name, ["columns"], "exists/W", target_cfg=append_cfg, message=append_id)

                source_entity_cfg = self.project_cfg.get("entities", {}).get(append_source, {}) if isinstance(append_source, str) else {}
                target_columns, target_excluded = self._get_alignable_columns(
                    entity_cfg.get("columns", []) or [], entity_cfg.get("public_id")
                )

                source_columns_cfg = append_cfg.get("columns")
                if not isinstance(source_columns_cfg, list):
                    source_columns_cfg = source_entity_cfg.get("columns", []) or []

                source_columns, source_excluded = self._get_alignable_columns(source_columns_cfg, source_entity_cfg.get("public_id"))

                if align_by_position and len(target_columns) != len(source_columns):
                    self.add_error(
                        f"{append_id}: align_by_position requires equal payload column counts after excluding identity columns "
                        f"(target={target_columns}, source={source_columns}, excluded_target={target_excluded}, excluded_source={source_excluded})",
                        entity=entity_name,
                        field="append",
                    )

                if not align_by_position and not column_mapping:
                    missing_columns = [column for column in target_columns if column not in source_columns]
                    if missing_columns:
                        self.add_error(
                            f"{append_id}: match-by-name is not possible because source entity '{append_source}' is missing target columns "
                            f"{missing_columns}; use column_mapping or align_by_position",
                            entity=entity_name,
                            field="append",
                        )

            # Validate column renaming options
            if align_by_position and column_mapping:
                self.add_error(
                    f"{append_id}: cannot specify both 'align_by_position' and 'column_mapping'",
                    entity=entity_name,
                    field="append",
                )

            if align_by_position:
                self.check_fields(
                    entity_name, ["align_by_position"], "of_type/E", expected_types=(bool,), target_cfg=append_cfg, message=append_id
                )

            if column_mapping:
                self.check_fields(
                    entity_name, ["column_mapping"], "of_type/E", expected_types=(dict,), target_cfg=append_cfg, message=append_id
                )
                if isinstance(column_mapping, dict):
                    # Validate that all keys and values are strings
                    for src_col, tgt_col in column_mapping.items():
                        if not isinstance(src_col, str) or not isinstance(tgt_col, str):
                            self.add_error(
                                f"{append_id}: column_mapping keys and values must be strings",
                                entity=entity_name,
                                field="append",
                            )

        return not self.has_errors()


@ENTITY_SPECIFICATION.register(key="depends_on")
class DependsOnSpecification(ProjectSpecification):
    """Validates depends_on configurations."""

    def is_satisfied_by(self, *, entity_name: str = "unknown", **kwargs) -> bool:
        """Check that depends_on references are valid."""
        self.clear()

        entity_cfg: dict[str, Any] = self.get_entity_cfg(entity_name)

        if not entity_cfg.get("depends_on"):
            return True

        self.check_fields(entity_name, ["depends_on"], "is_string_list/W")

        if isinstance(entity_cfg.get("depends_on"), list):
            for dep in entity_cfg.get("depends_on", []):
                if not self.entity_exists(dep):
                    self.add_error(f"Entity '{entity_name}': depends on non-existent entity '{dep}'", entity=entity_name, depends_on=dep)

        return not self.has_errors()


@ENTITY_SPECIFICATION.register(key="depends_on_resolved")
class DependsOnResolvedSpecification(ProjectSpecification):
    """Validates that all dependent entities exist in the project."""

    def is_satisfied_by(self, *, entity_name: str = "unknown", **kwargs) -> bool:
        """Check that depends_on references are valid."""
        self.clear()

        entity: TableConfig = self.get_entity(entity_name)

        for dep in entity.depends_on:
            if not self.entity_exists(dep):
                self.add_error(f"Entity '{entity_name}': depends on non-existent entity '{dep}'", entity=entity_name, depends_on=dep)

        return not self.has_errors()


@ENTITY_SPECIFICATION.register(key="entity_references_exist")
class EntityReferencesExistSpecification(ProjectSpecification):
    """Validates that all referenced entities exist in the configuration.
    Note: The checks in this specification are most likely redundant with other specifications.
    """

    def is_satisfied_by(self, *, entity_name: str = "unknown", **kwargs) -> bool:
        self.clear()
        entity_names: set[str] = set(self.project_cfg.get("entities", {}).keys())
        entity_cfg: dict[str, Any] = dotget(self.project_cfg, f"entities.{entity_name}", {})

        self.is_satisfied_by_foreign_keys(entity_name, entity_names, entity_cfg)
        self.is_satisfied_by_dependencies(entity_name, entity_names, entity_cfg)
        self.is_satisfied_by_source(entity_name, entity_names, entity_cfg)

        return not self.has_errors()

    def is_satisfied_by_source(self, entity_name: str, entity_names: set[str], entity_cfg: dict[str, Any]):
        source: str | None = entity_cfg.get("source", None)
        if source and isinstance(source, str) and source not in entity_names:
            self.add_error(f"Entity '{entity_name}': references non-existent source entity '{source}'", entity=entity_name, source=source)

    def is_satisfied_by_dependencies(self, entity_name: str, entity_names: set[str], entity_cfg: dict[str, Any]):
        depends_on: list[str] = entity_cfg.get("depends_on", []) or []
        for dep in depends_on:
            if dep not in entity_names:
                self.add_error(f"Entity '{entity_name}': depends on non-existent entity '{dep}'", entity=entity_name, depends_on=dep)

    def is_satisfied_by_foreign_keys(self, entity_name: str, entity_names: set[str], entity_cfg: dict[str, Any]):
        foreign_keys: list[dict[str, Any]] = entity_cfg.get("foreign_keys", []) or []
        for fk in foreign_keys:
            remote_entity: str | None = fk.get("entity", None)
            if not remote_entity:
                self.add_error(f"Entity '{entity_name}': foreign key missing 'entity' field", entity=entity_name)
            elif remote_entity not in entity_names:
                self.add_error(
                    f"Entity '{entity_name}': references non-existent entity '{remote_entity}' in foreign key",
                    entity=entity_name,
                )


@ENTITY_SPECIFICATION.register(key="filters")
class FilterSpecification(ProjectSpecification):
    """Validates staged filter configuration and basic stage-aware column availability."""

    def is_satisfied_by(self, *, entity_name: str = "unknown", **kwargs) -> bool:
        self.clear()

        entity_cfg: dict[str, Any] = self.get_entity_cfg(entity_name)
        filters: list[dict[str, Any]] | None = entity_cfg.get("filters")
        if not filters:
            return True

        if not isinstance(filters, list):
            self.add_error("filters must be a list", entity=entity_name, field="filters")
            return False

        for idx, filter_cfg in enumerate(filters):
            filter_id = f"Entity '{entity_name}', filter #{idx + 1}"

            if not isinstance(filter_cfg, dict):
                self.add_error(f"{filter_id}: must be a mapping", entity=entity_name, field=f"filters[{idx}]")
                continue

            filter_type = filter_cfg.get("type")
            if not filter_type:
                self.add_error(f"{filter_id}: missing required 'type' field", entity=entity_name, field=f"filters[{idx}].type")
                continue

            if Filters.get(filter_type) is None:
                self.add_error(
                    f"{filter_id}: unknown filter type '{filter_type}'",
                    entity=entity_name,
                    field=f"filters[{idx}].type",
                )
                continue

            try:
                stage = normalize_filter_stage(filter_cfg)
            except ValueError as exc:
                self.add_error(str(exc), entity=entity_name, field=f"filters[{idx}].stage")
                continue

            available_local_columns = self._get_filter_stage_columns(entity_name, stage)
            explicit_local_column = filter_cfg.get("column")
            if filter_type != "query" and isinstance(explicit_local_column, str) and explicit_local_column not in available_local_columns:
                self.add_error(
                    f"{filter_id}: column '{explicit_local_column}' is not available at stage '{stage}'. "
                    f"Available columns: {sorted(available_local_columns)}.",
                    entity=entity_name,
                    field=f"filters[{idx}].column",
                )

            if filter_type == "exists_in":
                self._validate_exists_in_filter(entity_name, idx, filter_cfg, stage)

        return not self.has_errors()

    def _validate_exists_in_filter(self, entity_name: str, idx: int, filter_cfg: dict[str, Any], stage: str) -> None:
        filter_id = f"Entity '{entity_name}', filter #{idx + 1}"
        column = filter_cfg.get("column")
        other_entity = filter_cfg.get("other_entity") or filter_cfg.get("entity")
        other_column = filter_cfg.get("other_column") or filter_cfg.get("remote_column") or column

        if not isinstance(column, str) or not column:
            self.add_error(
                f"{filter_id}: exists_in filter requires 'column'",
                entity=entity_name,
                field=f"filters[{idx}].column",
            )
            return

        if not isinstance(other_entity, str) or not other_entity:
            self.add_error(
                f"{filter_id}: exists_in filter requires 'other_entity'",
                entity=entity_name,
                field=f"filters[{idx}].other_entity",
            )
            return

        if not self.entity_exists(other_entity):
            self.add_error(
                f"{filter_id}: references non-existent entity '{other_entity}'",
                entity=entity_name,
                field=f"filters[{idx}].other_entity",
            )
            return

        available_local_columns = self._get_filter_stage_columns(entity_name, stage)
        if column not in available_local_columns:
            self.add_error(
                f"{filter_id}: column '{column}' is not available at stage '{stage}'. "
                f"Available columns: {sorted(available_local_columns)}.",
                entity=entity_name,
                field=f"filters[{idx}].column",
            )

        if isinstance(other_column, str) and other_column:
            available_remote_columns = self.get_entity_columns(other_entity)
            if other_column not in available_remote_columns:
                self.add_error(
                    f"{filter_id}: other_column '{other_column}' not found in entity '{other_entity}'. "
                    f"Available columns: {sorted(available_remote_columns)}.",
                    entity=entity_name,
                    field=f"filters[{idx}].other_column",
                )

    def _get_filter_stage_columns(self, entity_name: str, stage: str) -> set[str]:
        if stage == "extract":
            return self.get_entity_columns(entity_name, exclude_types={"unnest", "foreign_keys"})
        if stage == "after_link":
            return self.get_entity_columns(entity_name, exclude_types={"unnest"})
        return self.get_entity_columns(entity_name)


@ENTITY_SPECIFICATION.register(key="materialization")
class MaterializationSpecification(ProjectSpecification):
    """Validates materialized entity configurations."""

    def is_satisfied_by(self, *, entity_name: str = "unknown", **kwargs) -> bool:
        """Check that materialized entity is properly configured."""
        self.clear()

        entity_cfg: dict[str, Any] = self.get_entity_cfg(entity_name)
        materialized_cfg = entity_cfg.get("materialized")

        if materialized_cfg is None or not materialized_cfg.get("enabled"):
            return True

        # Materialized entities must be fixed type
        entity_type = entity_cfg.get("type")
        if entity_type != "fixed":
            self.add_error(
                f"Materialized entity '{entity_name}' must have type='fixed', got '{entity_type}'",
                entity=entity_name,
                field="type",
            )

        # Must have values (inline or @file: directive)
        has_values = bool(entity_cfg.get("values"))

        if not has_values:
            self.add_error(
                "Materialized entity must have 'values' field (inline data or @file: directive)",
                entity=entity_name,
                field="values",
            )

        # Must have source_state (snapshot of original config)
        if not materialized_cfg.get("source_state"):
            self.add_error(
                "Materialized entity must have 'materialized.source_state' to allow unmaterialization",
                entity=entity_name,
                field="materialized.source_state",
            )

        # Validate required metadata fields
        if not materialized_cfg.get("materialized_at"):
            self.add_warning(
                "Materialized entity should have 'materialized_at' metadata",
                entity=entity_name,
                field="materialized.materialized_at",
            )

        return not self.has_errors()


@ENTITY_SPECIFICATION.register(key="unnest_columns")
class UnnestColumnsSpecification(ProjectSpecification):
    """Validates that unnest configuration references existing columns.

    Unnest happens after FK linking, so id_vars can reference:
    - Static columns (columns, keys)
    - Extra columns (extra_columns)
    - FK-added columns (remote entity's public_id + FK extra_columns)
    """

    def is_satisfied_by(self, *, entity_name: str = "unknown", **kwargs) -> bool:
        """Check that unnest configuration is valid."""
        self.clear()

        entity_cfg: dict[str, Any] = self.get_entity_cfg(entity_name)
        if not entity_cfg:
            return True

        unnest_cfg: dict[str, Any] | None = entity_cfg.get("unnest")
        if not unnest_cfg:
            # No unnest configuration
            return True

        # Get id_vars (columns to keep) and value_vars (columns to melt)
        id_vars: list[str] | None = unnest_cfg.get("id_vars")
        value_vars: list[str] | None = unnest_cfg.get("value_vars")

        # Get all columns available when unnest runs (after FK linking)
        all_columns: set[str] = self.get_entity_columns(entity_name, exclude_types={"unnest"})

        # Check that id_vars exist
        if id_vars and isinstance(id_vars, list):
            missing_id_vars: set[str] = set(id_vars) - all_columns
            if missing_id_vars:
                self.add_error(
                    f"Unnest configuration references missing id_vars columns: {sorted(missing_id_vars)}. "
                    f"Available columns: {sorted(all_columns)}. "
                    f"These columns must be in 'columns', 'keys', 'extra_columns', or added by foreign keys.",
                    entity=entity_name,
                    field="unnest.id_vars",
                )

        # Check that value_vars exist
        if value_vars and isinstance(value_vars, list):
            missing_value_vars: set[str] = set(value_vars) - all_columns
            if missing_value_vars:
                self.add_error(
                    f"Unnest configuration references missing value_vars columns: {sorted(missing_value_vars)}. "
                    f"Available columns: {sorted(all_columns)}. "
                    f"These columns must be in 'columns', 'keys', 'extra_columns', or added by foreign keys.",
                    entity=entity_name,
                    field="unnest.value_vars",
                )

        return not self.has_errors()


@ENTITY_SPECIFICATION.register(key="foreign_key_columns")
class ForeignKeyColumnsSpecification(ProjectSpecification):
    """Validates that foreign key local_keys exist in entity columns.

    FK linking happens after load, so local_keys can reference:
    - Static columns (columns, keys)
    - Extra columns (extra_columns)
    - Columns added by previous FKs in the chain (public_id + extra_columns)

    FKs are processed sequentially, so each FK can reference columns added
    by any FK that appears before it in the foreign_keys list.
    """

    def is_satisfied_by(self, *, entity_name: str = "unknown", **kwargs) -> bool:
        """Check that foreign key configurations reference valid columns."""
        self.clear()

        entity_cfg: dict[str, Any] = self.get_entity_cfg(entity_name)
        if not entity_cfg:
            return True

        foreign_keys: list[dict[str, Any]] | None = entity_cfg.get("foreign_keys")
        if not foreign_keys:
            # No foreign keys
            return True

        # Start with columns available before any FK linking
        # (columns, keys, extra_columns, system_id, public_id, unnest result columns)
        available_columns: set[str] = self.get_entity_columns(entity_name, exclude_types={"foreign_keys"})

        # Check each foreign key sequentially, accumulating columns as we go
        for idx, fk_cfg in enumerate(foreign_keys):
            local_keys: list[str] | str | None = fk_cfg.get("local_keys")
            remote_entity: str | None = fk_cfg.get("entity")

            if not local_keys:
                self.add_error(
                    "Foreign key configuration is missing 'local_keys'",
                    entity=entity_name,
                    field=f"foreign_keys[{idx}].local_keys",
                )
                continue

            # Check that local_keys exist in columns available at this FK's processing time
            missing_local_keys: set[str] = set(local_keys) - available_columns
            if missing_local_keys:
                self.add_error(
                    f"Foreign key to '{remote_entity}' references missing local_keys: {missing_local_keys}. "
                    f"These columns must be in 'columns', 'keys', 'extra_columns', or added by prior foreign keys.",
                    entity=entity_name,
                    field=f"foreign_keys[{idx}].local_keys",
                )

            # After validating this FK, add columns it will contribute for subsequent FKs
            # 1. Add the remote entity's public_id (FK column)
            if remote_entity:
                remote_entity_cfg: dict[str, Any] = self.get_entity_cfg(remote_entity) or {}
                remote_public_id: str | None = remote_entity_cfg.get("public_id")
                if remote_public_id:
                    available_columns.add(remote_public_id)

            # 2. Add any extra_columns from this FK
            extra_columns: dict[str, Any] | list[str] | str | None = fk_cfg.get("extra_columns")
            if isinstance(extra_columns, dict):
                available_columns.update(extra_columns.keys())
            elif isinstance(extra_columns, list):
                available_columns.update(extra_columns)
            elif isinstance(extra_columns, str):
                available_columns.add(extra_columns)

        return not self.has_errors()


class EntitySpecification(ProjectSpecification):
    """Validates that entities are properly configured.

    Composite specification that runs all entity-level validations.
    To extend with custom validators, override get_specifications()
    or add new specifications to the ENTITY_SPECIFICATION registry.
    """

    def get_specifications(self) -> list[ProjectSpecification]:
        """Get the list of specifications to run for entity validation.

        Override this method to customize or extend entity validation rules.

        Returns:
            List of specification instances to execute
        """
        return [spec_cls(self.project_cfg) for spec_cls in ENTITY_SPECIFICATION.items.values()]

    def is_satisfied_by(self, *, entity_name: str = "unknown", **kwargs) -> bool:
        """Check that entities are properly configured."""

        self.clear()
        for spec in self.get_specifications():
            spec.is_satisfied_by(entity_name=entity_name)
            self.merge(spec)

        return not self.has_errors()
