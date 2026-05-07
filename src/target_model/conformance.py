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

    def guard(self, target_model: TargetModel, project: ShapeShiftProject, entity_name) -> bool:  # pylint: disable=unused-argument
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
    """Validate that required FK targets are present, with support for bridge-mediated relationships.

    When a FK spec includes 'via: bridge_entity', the validator checks that:
    1. The bridge entity exists as its own entity in the project (not as a FK target on the source).
       Bridge entities are join tables — the source entity never has a direct FK to the bridge.
    2. The bridge entity has a FK to the ultimate target entity.

    Example: site -> location (via: site_location)
    - Checks that 'site_location' is present in the project (project.has_table)
    - Checks that 'site_location' has a FK to 'location'
    """

    def validate_entity(self, entity_name: str, entity_spec: EntitySpec, table_cfg: TableConfig) -> list[ConformanceIssue]:
        """Legacy single-entity validation (no project access for bridge checks)."""
        # This method is still called by the base class, but we override validate() below
        # for full bridge-aware logic. Keep this simple for backward compatibility.
        return []

    def validate(self, target_model: TargetModel, project: ShapeShiftProject) -> list[ConformanceIssue]:
        """Validate FK targets with bridge entity support (requires project access)."""
        issues: list[ConformanceIssue] = []

        for entity_name, entity_spec in target_model.entities.items():
            if not self.guard(target_model, project, entity_name):
                continue

            table_cfg: TableConfig = project.get_table(entity_name)
            project_targets: set[str] = table_cfg.get_target_facing_foreign_key_targets()

            for foreign_key in entity_spec.foreign_keys:
                if not foreign_key.required:
                    continue

                # Direct FK target (no bridge)
                if not foreign_key.via:
                    if foreign_key.entity not in project_targets:
                        issues.append(
                            ConformanceIssue(
                                code="MISSING_REQUIRED_FOREIGN_KEY_TARGET",
                                message=f"Entity '{entity_name}' is missing required foreign key target '{foreign_key.entity}'",
                                entity=entity_name,
                            )
                        )
                    continue

                # Bridge-mediated FK target
                bridge_name = foreign_key.via

                # Check 1: Bridge entity must exist as its own entity in the project.
                # The source entity (entity_name) will never have a direct FK to bridge_name —
                # the bridge is a join table, not a FK target on the source side.
                if not project.has_table(bridge_name):
                    issues.append(
                        ConformanceIssue(
                            code="MISSING_BRIDGE_ENTITY",
                            message=(
                                f"Entity '{entity_name}' requires foreign key to '{foreign_key.entity}' "
                                f"via bridge '{bridge_name}', but bridge entity is not present in the project"
                            ),
                            entity=entity_name,
                        )
                    )
                    continue

                # Check 2: Bridge entity should have a FK to the ultimate target entity.
                bridge_cfg: TableConfig = project.get_table(bridge_name)
                bridge_targets: set[str] = bridge_cfg.get_target_facing_foreign_key_targets()

                if foreign_key.entity not in bridge_targets:
                    issues.append(
                        ConformanceIssue(
                            code="BRIDGE_MISSING_TARGET_FK",
                            message=(
                                f"Bridge entity '{bridge_name}' (mediating '{entity_name}' -> '{foreign_key.entity}') "
                                f"does not have a foreign key to target entity '{foreign_key.entity}'"
                            ),
                            entity=bridge_name,
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


@CONFORMANCE_VALIDATORS.register(key="induced_requirements")
class InducedRequirementConformanceValidator(ConformanceValidator):
    """If entity X is present in the project and has a required FK to Y, then Y is required — transitively.

    Uses BFS (Breadth-First Search) over the required-FK graph starting from all present,
    non-globally-required entities. Each induced missing entity is reported once; BFS continues
    through absent entities so that their own required FK targets are also induced.
    Globally required entities are skipped (the ``required_entity`` validator covers them).

    Example: X (present) → Y (absent) → Z (absent).  Both Y and Z are reported.
    """

    def validate(self, target_model: TargetModel, project: ShapeShiftProject) -> list[ConformanceIssue]:
        """Validate that if entity X is present and has a required FK to Y, then Y is also present (transitively)."""

        # Seed the queue with every present, non-globally-required entity.
        visited: set[str] = set()
        queue: list[tuple[str, str]] = self.get_optional_entities(target_model, project, visited)

        issues: list[ConformanceIssue] = []
        while queue:
            entity_name, inducer = queue.pop(0)
            entity_spec: EntitySpec | None = target_model.entities.get(entity_name)
            if entity_spec is None:
                continue

            for fk in entity_spec.foreign_keys:
                if not fk.required or fk.entity in visited:
                    continue
                visited.add(fk.entity)

                fk_target_spec: EntitySpec | None = target_model.entities.get(fk.entity)
                # Skip globally required targets — handled by required_entity validator.
                if fk_target_spec and fk_target_spec.required:
                    continue

                if not project.has_table(fk.entity):
                    is_direct: bool = entity_name == inducer
                    via: str = "" if is_direct else f" (via induced requirement on '{entity_name}')"
                    issues.append(
                        ConformanceIssue(
                            code="MISSING_INDUCED_REQUIRED_ENTITY",
                            message=(
                                f"Entity '{fk.entity}' is required because "
                                f"entity '{inducer}' is present and has a required "
                                f"foreign key chain to '{fk.entity}'{via}"
                            ),
                            entity=fk.entity,
                        )
                    )

                # Add fk.entity (even if absent) for transitive closure.
                queue.append((fk.entity, inducer))

        return issues

    def get_optional_entities(self, target_model, project, visited):
        queue: list[tuple[str, str]] = []  # (entity_to_explore, direct_inducer_name)
        for entity_name, entity_spec in target_model.entities.items():
            if project.has_table(entity_name) and not entity_spec.required:
                visited.add(entity_name)
                queue.append((entity_name, entity_name))
        return queue


@CONFORMANCE_VALIDATORS.register(key="source_type_appropriateness")
class SourceTypeAppropriatenessConformanceValidator(EntityConformanceValidator):
    """Classifiers should use type: fixed or type: sql, not type: entity.

    An entity with ``role: classifier`` in the target model is expected to be
    a pre-loaded lookup table (``type: fixed`` or ``type: sql``).  Using
    ``type: entity`` (row-extraction) for a classifier is almost always a
    modelling mistake and produces a warning so the author can decide whether
    to correct it.

    Issue code: ``CLASSIFIER_WRONG_SOURCE_TYPE``
    """

    ALLOWED_TYPES: frozenset[str] = frozenset({"fixed", "sql"})

    def validate_entity(self, entity_name: str, entity_spec: EntitySpec, table_cfg: TableConfig) -> list[ConformanceIssue]:
        if entity_spec.role != "classifier":
            return []
        entity_type: str | None = table_cfg.type
        if entity_type is not None and entity_type not in self.ALLOWED_TYPES:
            return [
                ConformanceIssue(
                    code="CLASSIFIER_WRONG_SOURCE_TYPE",
                    message=(
                        f"Entity '{entity_name}' has role 'classifier' but uses " f"source type '{entity_type}'; expected 'fixed' or 'sql'"
                    ),
                    entity=entity_name,
                )
            ]
        return []


class TargetModelConformanceValidator(ConformanceValidator):
    """Validate a resolved Shape Shifter project against a target model."""

    def validate(self, target_model: TargetModel, project: ShapeShiftProject) -> list[ConformanceIssue]:
        issues: list[ConformanceIssue] = []
        for validator_cls in CONFORMANCE_VALIDATORS.items.values():
            validator: ConformanceValidator = validator_cls()
            issues.extend(validator.validate(target_model, project))
        return issues
