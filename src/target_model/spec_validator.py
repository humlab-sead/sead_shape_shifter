from __future__ import annotations

from dataclasses import dataclass

from src.issues import CoreIssue
from src.target_model.effective_identity import resolve_aggregate_chain, resolve_effective_identity
from src.target_model.models import EntitySpec, ForeignKeySpec, TargetModel

CHAIN_ISSUE_CODES: frozenset[str] = frozenset(
    {
        "AGGREGATE_PARENT_CYCLE",
        "INVALID_AGGREGATE_ROOT_IDENTITY",
        "AGGREGATE_CHILD_MISSING_PUBLIC_ID",
        "AGGREGATE_ROOT_MISSING_PUBLIC_ID",
    }
)
"""Chain-level issue codes that immediate-parent checks cannot report.

Other chain issue codes repeat diagnostics that ``_validate_aggregate_parent``
already emits for the broken link, so validation drops them to avoid duplicates.
"""


@dataclass(slots=True, kw_only=True, repr=False)
class SpecValidationIssue(CoreIssue):
    """Issue emitted when validating the structure of a target-model specification."""

    severity: str = "error"
    category: str | None = "structural"

    def __post_init__(self) -> None:
        """Ensure target-model spec issues always carry a machine-readable code."""
        if self.code is None:
            raise ValueError("SpecValidationIssue requires a non-empty code")


class TargetModelSpecValidator:
    def validate(self, target_model: TargetModel) -> list[SpecValidationIssue]:
        issues: list[SpecValidationIssue] = []
        suffix = target_model.naming.public_id_suffix if target_model.naming else None
        reported_cycles: set[tuple[str, ...]] = set()

        for entity_name, entity_spec in target_model.entities.items():
            column_names = set(entity_spec.columns)

            if suffix and entity_spec.public_id and not entity_spec.public_id.endswith(suffix):
                issues.append(
                    SpecValidationIssue(
                        code="INVALID_PUBLIC_ID_SUFFIX",
                        message=(f"Entity '{entity_name}' has public_id '{entity_spec.public_id}' " f"which does not end with '{suffix}'"),
                        entity=entity_name,
                    )
                )

            for foreign_key in entity_spec.foreign_keys:
                if foreign_key.entity not in target_model.entities:
                    issues.append(
                        SpecValidationIssue(
                            code="UNKNOWN_FOREIGN_KEY_ENTITY",
                            message=f"Entity '{entity_name}' references unknown foreign key target '{foreign_key.entity}'",
                            entity=entity_name,
                        )
                    )

                if foreign_key.required_when is not None:
                    issues.extend(self._validate_required_when(target_model, entity_name, foreign_key))

            for unique_set in entity_spec.unique_sets:
                for column_name in unique_set:
                    if column_name not in column_names:
                        issues.append(
                            SpecValidationIssue(
                                code="UNKNOWN_UNIQUE_SET_COLUMN",
                                message=f"Entity '{entity_name}' references unknown unique-set column '{column_name}'",
                                entity=entity_name,
                            )
                        )

            for column_name, column_spec in entity_spec.columns.items():
                if column_spec.allowed_values and column_spec.type not in {None, "enum"}:
                    issues.append(
                        SpecValidationIssue(
                            code="ALLOWED_VALUES_REQUIRE_ENUM_TYPE",
                            message=(
                                f"Entity '{entity_name}' column '{column_name}' declares allowed_values but uses type "
                                f"'{column_spec.type}' instead of 'enum'"
                            ),
                            entity=entity_name,
                            field=column_name,
                        )
                    )

                if column_spec.type == "enum" and not column_spec.allowed_values:
                    issues.append(
                        SpecValidationIssue(
                            code="ENUM_MISSING_ALLOWED_VALUES",
                            message=(f"Entity '{entity_name}' column '{column_name}' uses type 'enum' but does not declare allowed_values"),
                            entity=entity_name,
                            field=column_name,
                        )
                    )

            aggregate_parent_issues = self._validate_aggregate_parent(target_model, entity_name, entity_spec)
            issues.extend(aggregate_parent_issues)
            issues.extend(self._validate_aggregate_chain(target_model, entity_name, entity_spec, aggregate_parent_issues, reported_cycles))
            issues.extend(self._validate_identity_rules(entity_name, entity_spec))

        return issues

    @staticmethod
    def _validate_required_when(target_model: TargetModel, entity_name: str, foreign_key: ForeignKeySpec) -> list[SpecValidationIssue]:
        """Validate that a conditional FK names its owning source and a target with a public ID."""
        issues: list[SpecValidationIssue] = []
        source_entity = foreign_key.required_when.has_new_rows

        if "required" in foreign_key.model_fields_set:
            issues.append(
                SpecValidationIssue(
                    code="CONFLICTING_FOREIGN_KEY_REQUIREMENTS",
                    message=(
                        f"Entity '{entity_name}' foreign key to '{foreign_key.entity}' cannot declare both "
                        "'required' and 'required_when'"
                    ),
                    entity=entity_name,
                )
            )

        if source_entity not in target_model.entities:
            issues.append(
                SpecValidationIssue(
                    code="UNKNOWN_CONDITIONAL_FOREIGN_KEY_SOURCE",
                    message=(f"Entity '{entity_name}' foreign key condition references unknown source entity '{source_entity}'"),
                    entity=entity_name,
                )
            )
        elif source_entity != entity_name:
            issues.append(
                SpecValidationIssue(
                    code="CONDITIONAL_FOREIGN_KEY_SOURCE_MISMATCH",
                    message=(f"Entity '{entity_name}' foreign key condition must name its owning source entity, " f"not '{source_entity}'"),
                    entity=entity_name,
                )
            )

        if foreign_key.via:
            issues.append(
                SpecValidationIssue(
                    code="CONDITIONAL_FOREIGN_KEY_VIA_UNSUPPORTED",
                    message=(
                        f"Entity '{entity_name}' foreign key condition cannot use bridge '{foreign_key.via}'; "
                        "conditional foreign keys must be direct"
                    ),
                    entity=entity_name,
                )
            )

        target_spec = target_model.entities.get(foreign_key.entity)
        if target_spec is not None and not target_spec.public_id:
            issues.append(
                SpecValidationIssue(
                    code="CONDITIONAL_FOREIGN_KEY_TARGET_MISSING_PUBLIC_ID",
                    message=(f"Entity '{entity_name}' conditional foreign key target '{foreign_key.entity}' " "must declare public_id"),
                    entity=entity_name,
                )
            )

        return issues

    @staticmethod
    def _resolve_effective_sims(spec: EntitySpec) -> tuple[str | None, str | None]:
        effective = resolve_effective_identity(spec)
        return effective.identity_tracking, effective.reconciliation

    def _validate_aggregate_parent(self, target_model: TargetModel, entity_name: str, entity_spec: EntitySpec) -> list[SpecValidationIssue]:
        issues: list[SpecValidationIssue] = []
        aggregate_parent = entity_spec.aggregate_parent

        if aggregate_parent is None:
            if entity_spec.identity_tracking == "child":
                issues.append(
                    SpecValidationIssue(
                        code="CHILD_IDENTITY_MISSING_AGGREGATE_PARENT",
                        message=f"Entity '{entity_name}' declares identity_tracking 'child' but has no aggregate_parent",
                        entity=entity_name,
                    )
                )
            return issues

        if aggregate_parent == entity_name:
            issues.append(
                SpecValidationIssue(
                    code="SELF_REFERENTIAL_AGGREGATE_PARENT",
                    message=f"Entity '{entity_name}' cannot use itself as aggregate_parent",
                    entity=entity_name,
                )
            )
            return issues

        if aggregate_parent not in target_model.entities:
            issues.append(
                SpecValidationIssue(
                    code="UNKNOWN_AGGREGATE_PARENT",
                    message=f"Entity '{entity_name}' references unknown aggregate_parent '{aggregate_parent}'",
                    entity=entity_name,
                )
            )
            return issues

        if entity_spec.identity_tracking is not None and entity_spec.identity_tracking != "child":
            issues.append(
                SpecValidationIssue(
                    code="AGGREGATE_PARENT_CONFLICTS_WITH_IDENTITY_TRACKING",
                    message=(
                        f"Entity '{entity_name}' uses aggregate_parent '{aggregate_parent}' but declares "
                        f"identity_tracking '{entity_spec.identity_tracking}' instead of 'child'"
                    ),
                    entity=entity_name,
                )
            )

        foreign_key_targets = {foreign_key.entity for foreign_key in entity_spec.foreign_keys}
        if aggregate_parent not in foreign_key_targets:
            issues.append(
                SpecValidationIssue(
                    code="MISSING_AGGREGATE_PARENT_FOREIGN_KEY",
                    message=(f"Entity '{entity_name}' uses aggregate_parent '{aggregate_parent}' but does not declare a foreign key to it"),
                    entity=entity_name,
                )
            )

        return issues

    @staticmethod
    def _validate_aggregate_chain(
        target_model: TargetModel,
        entity_name: str,
        entity_spec: EntitySpec,
        aggregate_parent_issues: list[SpecValidationIssue],
        reported_cycles: set[tuple[str, ...]],
    ) -> list[SpecValidationIssue]:
        """Report chain-level aggregate failures that immediate-parent checks cannot see.

        Skips entities whose immediate parent link is already reported, because a
        broken first link makes the rest of the chain unresolvable. Reports each
        canonical cycle once, on the alphabetically first member entity.
        """
        if aggregate_parent_issues:
            return []
        if entity_spec.aggregate_parent is None and entity_spec.identity_tracking != "child":
            return []

        chain = resolve_aggregate_chain(target_model, entity_name)
        issues: list[SpecValidationIssue] = []
        for chain_issue in chain.issues:
            if chain_issue.code not in CHAIN_ISSUE_CODES:
                continue
            if chain_issue.code == "AGGREGATE_PARENT_CYCLE":
                if chain_issue.cycle is None or chain_issue.cycle in reported_cycles:
                    continue
                reported_cycles.add(chain_issue.cycle)
            issues.append(
                SpecValidationIssue(
                    code=chain_issue.code,
                    message=chain_issue.message,
                    entity=chain_issue.entity,
                )
            )
        return issues

    def _validate_identity_rules(self, entity_name: str, entity_spec: EntitySpec) -> list[SpecValidationIssue]:
        issues: list[SpecValidationIssue] = []
        identity_tracking, reconciliation = self._resolve_effective_sims(entity_spec)

        if entity_spec.public_id_generation == "database_sequence" and (
            entity_spec.identity_tracking is None or entity_spec.identity_tracking == "tracked"
        ):
            issues.append(
                SpecValidationIssue(
                    code="DATABASE_SEQUENCE_REQUIRES_EXPLICIT_NON_TRACKED_IDENTITY",
                    message=(
                        f"Entity '{entity_name}' uses database_sequence public ID generation but must explicitly declare "
                        "a non-tracked identity_tracking value; tracked identities must be allocated by SIMS"
                    ),
                    entity=entity_name,
                )
            )

        if entity_spec.synchronize_sequence_after_insert:
            if not entity_spec.target_table or not entity_spec.public_id:
                issues.append(
                    SpecValidationIssue(
                        code="SEQUENCE_SYNC_REQUIRES_TARGET_ID",
                        message=(
                            f"Entity '{entity_name}' synchronizes a database sequence after insert but must declare "
                            "target_table and public_id"
                        ),
                        entity=entity_name,
                    )
                )
            if identity_tracking != "tracked":
                issues.append(
                    SpecValidationIssue(
                        code="SEQUENCE_SYNC_REQUIRES_TRACKED_IDENTITY",
                        message=(
                            f"Entity '{entity_name}' synchronizes a database sequence after insert but does not use "
                            "tracked identity allocation"
                        ),
                        entity=entity_name,
                    )
                )
            if entity_spec.public_id_generation == "database_sequence":
                issues.append(
                    SpecValidationIssue(
                        code="CONFLICTING_PUBLIC_ID_SEQUENCE_RULES",
                        message=(
                            f"Entity '{entity_name}' cannot reserve IDs from a database sequence and synchronize "
                            "that sequence after insert"
                        ),
                        entity=entity_name,
                    )
                )

        if identity_tracking == "child":
            if entity_spec.reconciliation is not None:
                issues.append(
                    SpecValidationIssue(
                        code="INVALID_IDENTITY_RECONCILIATION_COMBINATION",
                        message=(
                            f"Entity '{entity_name}' uses child identity via aggregate_parent and must not declare "
                            f"reconciliation '{entity_spec.reconciliation}'"
                        ),
                        entity=entity_name,
                    )
                )
            return issues

        if identity_tracking == "tracked" and reconciliation != "allocate":
            issues.append(
                SpecValidationIssue(
                    code="INVALID_IDENTITY_RECONCILIATION_COMBINATION",
                    message=(
                        f"Entity '{entity_name}' uses tracked identity and must resolve to reconciliation 'allocate', "
                        f"not '{reconciliation}'"
                    ),
                    entity=entity_name,
                )
            )
            return issues

        if identity_tracking == "derived" and reconciliation != "derive":
            issues.append(
                SpecValidationIssue(
                    code="INVALID_IDENTITY_RECONCILIATION_COMBINATION",
                    message=(
                        f"Entity '{entity_name}' uses derived identity and must resolve to reconciliation 'derive', "
                        f"not '{reconciliation}'"
                    ),
                    entity=entity_name,
                )
            )
            return issues

        if identity_tracking == "reconciled" and reconciliation not in {
            "reconcile-exact",
            "reconcile-fuzzy",
            "lookup-only",
            "lookup-extensible",
        }:
            issues.append(
                SpecValidationIssue(
                    code="INVALID_IDENTITY_RECONCILIATION_COMBINATION",
                    message=(
                        f"Entity '{entity_name}' uses reconciled identity and must resolve to a lookup or reconcile strategy, "
                        f"not '{reconciliation}'"
                    ),
                    entity=entity_name,
                )
            )

        return issues
