"""Specifications for validating entity configurations."""

from typing import Any

from src.utility import Registry, dotget

from .base import ProjectSpecification


class EntitySpecificationRegistry(Registry[type[ProjectSpecification]]):
    """Registry for field validators."""

    items: dict[str, type[ProjectSpecification]] = {}


ENTITY_SPECIFICATION = EntitySpecificationRegistry()


class EntityFieldsBaseSpecification(ProjectSpecification):
    """Validates that fields are present for a single entity."""

    def is_satisfied_by(self, *, entity_name: str = "unknown", **kwargs) -> bool:
        """Check that fields are for the entity."""
        self.clear()

        for field in ["keys", "columns"]:
            self.check_fields(entity_name, [field], "exists/E")
            if self.field_exists(f"entities.{entity_name}.{field}"):
                self.check_fields(entity_name, [field], "is_string_list/E")

        return not self.has_errors()


class FixedEntityFieldsSpecification(EntityFieldsBaseSpecification):

    def is_satisfied_by(self, *, entity_name: str = "unknown", **kwargs) -> bool:
        """Check that fields are for the fixed entity."""
        super().is_satisfied_by(entity_name=entity_name, **kwargs)
        self.check_fields(entity_name, ["surrogate_id", "values"], "exists/E")
        return not self.has_errors()


class FixedDataSpecification(ProjectSpecification):
    """Validates fixed data table configurations."""

    def is_satisfied_by(self, *, entity_name: str = "unknown", **kwargs) -> bool:
        """Check that fixed data configurations are valid."""
        self.clear()
        entity_cfg: dict[str, Any] = self.get_entity_cfg(entity_name)

        if entity_cfg.get("type") != "fixed":
            return True

        self.check_fields(entity_name, ["values"], "not_empty/E", message="Fixed entity requires 'values' field")
        self.check_fields(entity_name, ["columns"], "not_empty/E,is_string_list/E", message="Fixed entity requires 'columns' field")

        values = entity_cfg.get("values")
        columns = entity_cfg.get("columns", [])

        if isinstance(values, list) and isinstance(columns, list):

            is_primitive_list = all(not isinstance(row, (list, dict)) for row in values)
            if is_primitive_list:
                if len(columns) != 1:
                    self.add_error(
                        f"Entity '{entity_name}': 'values' appear to be a single-column list but 'columns' has length {len(columns)}",
                        entity=entity_name,
                        field="values",
                    )
                # self.add_warning(
                #     f"Entity '{entity_name}': 'values' appear to be a single-column list; consider wrapping each value in a list",
                #     entity=entity_name,
                #     field="values",
                # )
            else:
                for idx, value_row in enumerate(values):
                    if isinstance(value_row, list):
                        if len(value_row) != len(columns):
                            self.add_error(
                                f"Entity '{entity_name}': column/row length mismatch at row {idx + 1}", entity=entity_name, field="values"
                            )
                    else:
                        self.add_warning(f"Entity '{entity_name}': value row {idx + 1} is not a list", entity=entity_name, field="values")

        self.check_fields(entity_name, ["source", "data_source", "query"], "is_empty/W")

        return not self.has_errors()


class SqlEntityFieldsSpecification(EntityFieldsBaseSpecification):
    """Validates that fields are present for a SQL entity."""

    def is_satisfied_by(self, *, entity_name: str = "unknown", **kwargs) -> bool:
        """Check that fields are for the SQL entity."""
        super().is_satisfied_by(entity_name=entity_name, **kwargs)
        self.check_fields(entity_name, ["data_source", "query"], "not_empty_string/E")
        return not self.has_errors()


@ENTITY_SPECIFICATION.register(key="entity_fields")
class EntityFieldsSpecification(ProjectSpecification):
    """Validates that all required fields are present in all entities."""

    def get_specification(self, *, entity_type: str) -> EntityFieldsBaseSpecification:
        if entity_type == "fixed":
            return FixedEntityFieldsSpecification(self.project_cfg)
        if entity_type == "sql":
            return SqlEntityFieldsSpecification(self.project_cfg)
        if entity_type == "data":
            return EntityFieldsBaseSpecification(self.project_cfg)
        return EntityFieldsBaseSpecification(self.project_cfg)

    def is_satisfied_by(self, *, entity_name: str = "unknown", **kwargs) -> bool:
        """Check that entity's fields are valid (based on entity type)."""
        self.clear()
        entity_type: str = self.get_entity_cfg(entity_name).get("type", "data")
        specification: EntityFieldsBaseSpecification = self.get_specification(entity_type=entity_type)
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

        # Can be bool, string (include directive), or list
        self.check_fields(entity_name, ["drop_duplicates"], "of_type/E", expected_types=(bool, str, list))

        if isinstance(drop_dup, list):
            self.check_fields(entity_name, ["drop_duplicates"], "is_string_list/E")
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


@ENTITY_SPECIFICATION.register(key="surrogate_id")
class SurrogateIdSpecification(ProjectSpecification):
    """Validates surrogate ID configurations."""

    def is_satisfied_by(self, *, entity_name: str = "unknown", **kwargs) -> bool:
        """Check that surrogate IDs follow naming conventions and are unique."""
        self.clear()

        entity_cfg: dict[str, Any] = self.get_entity_cfg(entity_name)
        surrogate_id = entity_cfg.get("surrogate_id", "")

        self.check_fields(entity_name, ["surrogate_id"], "exists/W")
        if surrogate_id:
            self.check_fields(entity_name, ["surrogate_id"], "of_type/E", expected_types=(str,))
            self.check_fields(entity_name, ["surrogate_id"], "ends_with_id/W")

        return not self.has_errors()


@ENTITY_SPECIFICATION.register(key="append")
class AppendSpecification(ProjectSpecification):
    """Validates append configuration settings."""

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

            self.check_fields(
                entity_name, ["type", "source"], "of_type/E", expected_types=(str, None), target_cfg=append_cfg, message=append_id
            )

            # Must have either type or source, but not both
            if not append_type and not append_source:
                self.add_error(f"{append_id}: must specify either 'type' or 'source'", entity=entity_name, field="append")
                continue

            if append_type and append_source:
                self.add_error(f"{append_id}: cannot specify both 'type' and 'source'", entity=entity_name, field="append")
                continue

            # Validate type-based append
            if append_type:
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

            # Validate source-based append
            if append_source:
                self.check_fields(entity_name, ["source"], "of_type/E", expected_types=(str,), target_cfg=append_cfg, message=append_id)
                self.check_fields(entity_name, ["source"], "is_existing_entity/E", target_cfg=append_cfg, message=append_id)
                self.check_fields(entity_name, ["columns"], "exists/W", target_cfg=append_cfg, message=append_id)

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
