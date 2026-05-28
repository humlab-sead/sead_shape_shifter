from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from src.issues import CoreIssue
from src.model import ShapeShiftProject, TableConfig
from src.target_model.models import EntitySpec, GlobalConstraint, SeverityLevel, TargetModel
from src.utility import Registry


@dataclass(slots=True, kw_only=True, repr=False)
class ConformanceIssue(CoreIssue):
    """Target-model conformance issue emitted by core conformance validators."""

    severity: str = "error"
    category: str | None = "conformance"

    def __post_init__(self) -> None:
        """Ensure conformance issues always carry a machine-readable code."""
        if self.code is None:
            raise ValueError("ConformanceIssue requires a non-empty code")


class ConformanceValidator(ABC):

    def get_default_severity(self, target_model: TargetModel, project: ShapeShiftProject) -> SeverityLevel:  # pylint: disable=unused-argument
        """Return the default severity for issues emitted by this validator."""
        return "error"

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


def has_target_facing_foreign_key_path(source_entity: str, target_entity: str, project: ShapeShiftProject) -> bool:
    """Return whether the project's target-facing FK graph reaches the target entity from the source entity."""
    if source_entity == target_entity:
        return True
    if not project.has_table(source_entity) or not project.has_table(target_entity):
        return False

    visited: set[str] = {source_entity}
    queue: list[str] = sorted(project.get_table(source_entity).get_target_facing_foreign_key_targets())

    while queue:
        current_entity = queue.pop(0)
        if current_entity in visited:
            continue
        if current_entity == target_entity:
            return True
        visited.add(current_entity)

        if not project.has_table(current_entity):
            continue

        queue.extend(sorted(project.get_table(current_entity).get_target_facing_foreign_key_targets() - visited))

    return False


def get_append_column_rename_map(parent_table_cfg: TableConfig, append_table_cfg: TableConfig) -> dict[str, str]:
    """Return the static column rename map applied to an append branch, if any."""
    column_mapping = append_table_cfg.entity_cfg.get("column_mapping")
    if isinstance(column_mapping, dict):
        return {src: tgt for src, tgt in column_mapping.items() if isinstance(src, str) and isinstance(tgt, str)}

    if not append_table_cfg.entity_cfg.get("align_by_position", False):
        return {}

    parent_columns = [
        column for column in parent_table_cfg.columns if column not in {parent_table_cfg.system_id, parent_table_cfg.public_id}
    ]
    source_columns = [
        column
        for column in append_table_cfg.columns
        if column not in {append_table_cfg.system_id, append_table_cfg.public_id, append_table_cfg.get_source_public_id()}
    ]

    if len(parent_columns) != len(source_columns):
        return {}

    return dict(zip(source_columns, parent_columns))


def get_effective_append_target_facing_columns(parent_table_cfg: TableConfig, append_table_cfg: TableConfig) -> set[str]:
    """Return the append branch's target-facing columns after static append renaming is applied."""
    rename_map = get_append_column_rename_map(parent_table_cfg, append_table_cfg)
    return {rename_map.get(column, column) for column in append_table_cfg.get_target_facing_columns()}


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
                    message=f"Entity '{entity_name}' is missing required public_id '{entity_spec.public_id}'",
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
                    if foreign_key.entity not in project_targets and not has_target_facing_foreign_key_path(entity_name, foreign_key.entity, project):
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
                                f"Bridge entity '{bridge_name}' (between '{entity_name}' -> '{foreign_key.entity}') "
                                f"does not have a foreign key to target entity '{foreign_key.entity}'"
                            ),
                            entity=bridge_name,
                        )
                    )

        return issues


@CONFORMANCE_VALIDATORS.register(key="no_orphan_facts")
class NoOrphanFactsConformanceValidator(ConformanceValidator):
    """Fact entities must reach at least one required lookup or classifier when the constraint is declared."""

    PARENT_ROLES: frozenset[str] = frozenset({"lookup", "classifier"})

    def get_default_severity(self, target_model: TargetModel, project: ShapeShiftProject) -> SeverityLevel:  # pylint: disable=unused-argument
        constraint = self.get_constraint(target_model)
        if constraint and constraint.required in {True, "strict"}:
            return "error"
        return "warning"

    @staticmethod
    def get_constraint(target_model: TargetModel) -> GlobalConstraint | None:
        """Return the declared orphan-fact constraint, if present."""
        return next((constraint for constraint in target_model.constraints if constraint.type == "no_orphan_facts"), None)

    def validate(self, target_model: TargetModel, project: ShapeShiftProject) -> list[ConformanceIssue]:
        if self.get_constraint(target_model) is None:
            return []

        parent_entities = {
            entity_name
            for entity_name, entity_spec in target_model.entities.items()
            if entity_spec.role in self.PARENT_ROLES
        }
        if not parent_entities:
            return []

        issues: list[ConformanceIssue] = []
        for entity_name, entity_spec in target_model.entities.items():
            if entity_spec.role != "fact" or not project.has_table(entity_name):
                continue

            if any(has_target_facing_foreign_key_path(entity_name, parent_entity, project) for parent_entity in parent_entities):
                continue

            issues.append(
                ConformanceIssue(
                    code="ORPHAN_FACT_ENTITY",
                    message=(
                        f"Fact entity '{entity_name}' does not reach any lookup or classifier entity "
                        f"declared by the target model ({', '.join(sorted(parent_entities))})"
                    ),
                    entity=entity_name,
                )
            )

        return issues


@CONFORMANCE_VALIDATORS.register(key="schema_aware_append")
class SchemaAwareAppendConformanceValidator(EntityConformanceValidator):
    """Append branches must also satisfy the target-model column contract for their parent entity."""

    def guard(self, target_model: TargetModel, project: ShapeShiftProject, entity_name) -> bool:
        return project.has_table(entity_name) and project.get_table(entity_name).has_append

    def validate_entity(self, entity_name: str, entity_spec: EntitySpec, table_cfg: TableConfig) -> list[ConformanceIssue]:
        issues: list[ConformanceIssue] = []
        parent_columns = set(table_cfg.get_target_facing_columns())
        required_columns = {
            column_name
            for column_name, column_spec in entity_spec.columns.items()
            if column_spec.required and not column_spec.generated and column_name in parent_columns
        }
        if not required_columns:
            return issues

        for append_index, append_table_cfg in enumerate(list(table_cfg.get_sub_table_configs())[1:], start=1):
            effective_columns = get_effective_append_target_facing_columns(table_cfg, append_table_cfg)
            missing_columns = sorted(required_columns - effective_columns)

            for column_name in missing_columns:
                issues.append(
                    ConformanceIssue(
                        code="APPEND_MISSING_REQUIRED_COLUMN",
                        field=f"append[{append_index - 1}]",
                        message=(
                            f"Entity '{entity_name}' append item #{append_index} does not provide required target column '{column_name}'"
                        ),
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
            if column_spec.required and not column_spec.generated and column_name not in declared_columns:
                issues.append(
                    ConformanceIssue(
                        code="MISSING_REQUIRED_COLUMN",
                        message=f"Entity '{entity_name}' is missing required target column '{column_name}'",
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

    def get_default_severity(self, target_model: TargetModel, project: ShapeShiftProject) -> SeverityLevel:  # pylint: disable=unused-argument
        return "warning"

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

    VALID_SEVERITIES: frozenset[str] = frozenset({"error", "warning", "info"})

    @staticmethod
    def get_validation_options(project: ShapeShiftProject) -> dict:
        """Return the project's validation options as a dict."""
        validation_options = project.options.get("validation", {}) or {}
        return validation_options if isinstance(validation_options, dict) else {}

    def get_disabled_rule_keys(self, project: ShapeShiftProject) -> set[str]:
        """Read disabled conformance rule keys from project options."""
        validation_options = self.get_validation_options(project)
        raw_disabled_rules = validation_options.get("disabled_rules", [])

        if raw_disabled_rules is None:
            return set()
        if isinstance(raw_disabled_rules, str):
            return {raw_disabled_rules} if raw_disabled_rules else set()
        if isinstance(raw_disabled_rules, (list, tuple, set)):
            return {rule_key for rule_key in raw_disabled_rules if isinstance(rule_key, str) and rule_key}

        return set()

    def get_severity_overrides(self, project: ShapeShiftProject) -> dict[str, str]:
        """Read conformance severity overrides keyed by validator registry key."""
        validation_options = self.get_validation_options(project)
        raw_severity_overrides = validation_options.get("severity_overrides", {})

        if not isinstance(raw_severity_overrides, dict):
            return {}

        return {
            rule_key: severity
            for rule_key, severity in raw_severity_overrides.items()
            if isinstance(rule_key, str) and rule_key and isinstance(severity, str) and severity
        }

    def validate_disabled_rule_keys(self, disabled_rule_keys: set[str]) -> list[ConformanceIssue]:
        """Return warning issues for unknown disabled rule keys."""
        known_rule_keys = set(CONFORMANCE_VALIDATORS.items.keys())
        unknown_rule_keys = sorted(disabled_rule_keys - known_rule_keys)

        return [
            ConformanceIssue(
                severity="warning",
                code="UNKNOWN_DISABLED_CONFORMANCE_RULE",
                field="options.validation.disabled_rules",
                message=(
                    f"Project disables unknown conformance rule '{rule_key}'. "
                    "Remove it or use a registered conformance validator key."
                ),
            )
            for rule_key in unknown_rule_keys
        ]

    def validate_severity_overrides(self, severity_overrides: dict[str, str]) -> list[ConformanceIssue]:
        """Return warning issues for unknown or invalid severity overrides."""
        known_rule_keys = set(CONFORMANCE_VALIDATORS.items.keys())
        issues: list[ConformanceIssue] = []

        for rule_key in sorted(severity_overrides):
            if rule_key not in known_rule_keys:
                issues.append(
                    ConformanceIssue(
                        severity="warning",
                        code="UNKNOWN_CONFORMANCE_SEVERITY_OVERRIDE",
                        field="options.validation.severity_overrides",
                        message=(
                            f"Project overrides severity for unknown conformance rule '{rule_key}'. "
                            "Remove it or use a registered conformance validator key."
                        ),
                    )
                )

        for rule_key, severity in sorted(severity_overrides.items()):
            if severity in self.VALID_SEVERITIES:
                continue
            issues.append(
                ConformanceIssue(
                    severity="warning",
                    code="INVALID_CONFORMANCE_SEVERITY_OVERRIDE",
                    field=f"options.validation.severity_overrides.{rule_key}",
                    message=(
                        f"Project overrides conformance rule '{rule_key}' with unsupported severity '{severity}'. "
                        "Use one of: error, warning, info."
                    ),
                )
            )

        return issues

    def resolve_rule_severity(
        self,
        rule_key: str,
        validator: ConformanceValidator,
        target_model: TargetModel,
        project: ShapeShiftProject,
        severity_overrides: dict[str, str],
    ) -> SeverityLevel:
        """Resolve the effective severity for a registered conformance rule."""
        override = severity_overrides.get(rule_key)
        if override in self.VALID_SEVERITIES:
            return override  # type: ignore[return-value]
        return validator.get_default_severity(target_model, project)

    def validate(self, target_model: TargetModel, project: ShapeShiftProject) -> list[ConformanceIssue]:
        disabled_rule_keys = self.get_disabled_rule_keys(project)
        severity_overrides = self.get_severity_overrides(project)
        issues: list[ConformanceIssue] = self.validate_disabled_rule_keys(disabled_rule_keys)
        issues.extend(self.validate_severity_overrides(severity_overrides))

        for rule_key, validator_cls in CONFORMANCE_VALIDATORS.items.items():
            if rule_key in disabled_rule_keys:
                continue
            validator: ConformanceValidator = validator_cls()
            issue_severity = self.resolve_rule_severity(rule_key, validator, target_model, project, severity_overrides)
            rule_issues = validator.validate(target_model, project)
            for issue in rule_issues:
                issue.severity = issue_severity
            issues.extend(rule_issues)
        return issues
