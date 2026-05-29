from __future__ import annotations

from dataclasses import dataclass

from src.issues import CoreIssue
from src.target_model.models import EntitySpec, TargetModel


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

            for identity_column in entity_spec.identity_columns:
                if identity_column not in column_names:
                    issues.append(
                        SpecValidationIssue(
                            code="UNKNOWN_IDENTITY_COLUMN",
                            message=f"Entity '{entity_name}' references unknown identity column '{identity_column}'",
                            entity=entity_name,
                        )
                    )

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

            issues.extend(self._validate_aggregate_parent(target_model, entity_name, entity_spec))
            issues.extend(self._validate_identity_rules(entity_name, entity_spec))

        return issues

    @staticmethod
    def _resolve_effective_sims(spec: EntitySpec) -> tuple[str | None, str | None]:
        identity_tracking: str | None = spec.identity_tracking
        reconciliation: str | None = spec.reconciliation

        if identity_tracking is None:
            if spec.aggregate_parent:
                identity_tracking = "child"
            elif spec.role == "fact":
                identity_tracking = "tracked"
            elif spec.role in ("lookup", "classifier"):
                identity_tracking = "reconciled"
            elif spec.role == "bridge":
                identity_tracking = "derived"

        if reconciliation is None:
            if identity_tracking == "tracked":
                reconciliation = "allocate"
            elif spec.role == "lookup":
                reconciliation = "reconcile-exact"
            elif spec.role == "classifier":
                reconciliation = "lookup-only"
            elif identity_tracking == "derived":
                reconciliation = "derive"

        return identity_tracking, reconciliation

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

    def _validate_identity_rules(self, entity_name: str, entity_spec: EntitySpec) -> list[SpecValidationIssue]:
        issues: list[SpecValidationIssue] = []
        identity_tracking, reconciliation = self._resolve_effective_sims(entity_spec)

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
