from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from src.model import ShapeShiftProject, TableConfig
from src.target_model.models import EntitySpec, TargetModel
from src.utility import Registry


@dataclass(slots=True)
class ConformanceIssue:
    code: str
    message: str
    entity: str | None = None


class ConformanceValidator(ABC):

    @abstractmethod
    def validate(self, target_model: TargetModel, project: ShapeShiftProject) -> list[ConformanceIssue]:
        pass


class ConformanceValidatorRegistry(Registry[type[ConformanceValidator]]):
    """Registry for entity type validators."""

    items: dict[str, type[ConformanceValidator]] = {}


CONFORMANCE_VALIDATORS = ConformanceValidatorRegistry()


class EntityConformanceValidator(ConformanceValidator):

    @abstractmethod
    def validate_entity(self, entity_name: str, entity_spec: EntitySpec, table_cfg: TableConfig) -> list[ConformanceIssue]:
        pass

    def guard(self, target_model: TargetModel, project: ShapeShiftProject, entity_name) -> bool:
        """Determine whether this validator should be applied to the given entity."""
        return project.has_table(entity_name)

    def validate(self, target_model: TargetModel, project: ShapeShiftProject) -> list[ConformanceIssue]:
        """Validate that entities in the project conform to public_id expectations declared in the target model."""
        issues: list[ConformanceIssue] = []
        for entity_name, entity_spec in target_model.entities.items():
            if not self.guard(target_model, project, entity_name):
                continue
            table_cfg: TableConfig = project.get_table(entity_name)
            issues.extend(self.validate_entity(entity_name, entity_spec, table_cfg))
        return issues


@CONFORMANCE_VALIDATORS.register(key="public_id")
class PublicIdConformanceValidator(EntityConformanceValidator):

    def validate_entity(self, entity_name: str, entity_spec: EntitySpec, table_cfg: TableConfig) -> list[ConformanceIssue]:
        """Validate that entities in the project conform to public_id expectations declared in the target model."""
        if entity_spec.public_id is None:
            return []

        if not table_cfg.public_id:
            return [
                ConformanceIssue(
                    code="MISSING_PUBLIC_ID",
                    message=f"Entity '{entity_name}' is missing expected public_id '{entity_spec.public_id}'",
                    entity=entity_name,
                )
            ]

        if table_cfg.public_id != entity_spec.public_id:
            return [
                ConformanceIssue(
                    code="UNEXPECTED_PUBLIC_ID",
                    message=(
                        f"Entity '{entity_name}' declares public_id '{table_cfg.public_id}' "
                        f"but target model expects '{entity_spec.public_id}'"
                    ),
                    entity=entity_name,
                )
            ]

        return []


@CONFORMANCE_VALIDATORS.register(key="foreign_key")
class ForeignKeyConformanceValidator(EntityConformanceValidator):

    def validate_entity(self, entity_name: str, entity_spec: EntitySpec, table_cfg: TableConfig) -> list[ConformanceIssue]:
        issues: list[ConformanceIssue] = []
        project_targets: set[str] = table_cfg.get_target_facing_foreign_key_targets()

        for foreign_key in entity_spec.foreign_keys:
            if foreign_key.required and foreign_key.entity not in project_targets:
                issues.append(
                    ConformanceIssue(
                        code="MISSING_REQUIRED_FOREIGN_KEY_TARGET",
                        message=f"Entity '{entity_name}' is missing required foreign key target '{foreign_key.entity}'",
                        entity=entity_name,
                    )
                )

        return issues


@CONFORMANCE_VALIDATORS.register(key="required_columns")
class RequiredColumnsConformanceValidator(EntityConformanceValidator):

    def validate_entity(self, entity_name: str, entity_spec: EntitySpec, table_cfg: TableConfig) -> list[ConformanceIssue]:
        issues: list[ConformanceIssue] = []
        declared_columns: set[str] = set(table_cfg.get_target_facing_columns())
        for column_name, column_spec in entity_spec.columns.items():
            if column_spec.required and column_name not in declared_columns:
                issues.append(
                    ConformanceIssue(
                        code="MISSING_REQUIRED_COLUMN",
                        message=f"Entity '{entity_name}' is missing required target-facing column '{column_name}'",
                        entity=entity_name,
                    )
                )
        return issues


@CONFORMANCE_VALIDATORS.register(key="required_entity")
class RequiredEntityConformanceValidator(ConformanceValidator):

    def validate(self, target_model: TargetModel, project: ShapeShiftProject) -> list[ConformanceIssue]:
        issues: list[ConformanceIssue] = []
        for entity_name, entity_spec in target_model.entities.items():
            if not project.has_table(entity_name) and entity_spec.required:
                issues.append(
                    ConformanceIssue(
                        code="MISSING_REQUIRED_ENTITY",
                        message=f"Target model requires entity '{entity_name}'",
                        entity=entity_name,
                    )
                )
        return issues


@CONFORMANCE_VALIDATORS.register(key="naming_convention")
class NamingConventionConformanceValidator(ConformanceValidator):
    """Validate that project entity public_id values conform to the target model naming conventions."""

    def validate(self, target_model: TargetModel, project: ShapeShiftProject) -> list[ConformanceIssue]:
        if not target_model.naming or not target_model.naming.public_id_suffix:
            return []

        suffix = target_model.naming.public_id_suffix
        issues: list[ConformanceIssue] = []

        for entity_name in target_model.entities:
            if not project.has_table(entity_name):
                continue
            table_cfg: TableConfig = project.get_table(entity_name)
            if not table_cfg.public_id:
                continue
            if not table_cfg.public_id.endswith(suffix):
                issues.append(
                    ConformanceIssue(
                        code="PUBLIC_ID_NAMING_VIOLATION",
                        message=(
                            f"Entity '{entity_name}' has public_id '{table_cfg.public_id}' "
                            f"which does not end with naming convention suffix '{suffix}'"
                        ),
                        entity=entity_name,
                    )
                )

        return issues


class TargetModelConformanceValidator(ConformanceValidator):
    """Validate a resolved Shape Shifter project against a target model."""

    def validate(self, target_model: TargetModel, project: ShapeShiftProject) -> list[ConformanceIssue]:
        issues: list[ConformanceIssue] = []
        for validator_cls in CONFORMANCE_VALIDATORS.items.values():
            validator: ConformanceValidator = validator_cls()
            issues.extend(validator.validate(target_model, project))
        return issues
