"""Tests for the shared effective identity resolver."""

from __future__ import annotations

import pytest

from src.target_model.documentation import SimsDocumentGenerator
from src.target_model.effective_identity import (
    resolve_aggregate_chain,
    resolve_effective_identity,
)
from src.target_model.models import EntitySpec, TargetModel
from src.target_model.spec_validator import TargetModelSpecValidator


def _spec(**kwargs) -> EntitySpec:
    return EntitySpec.model_validate(kwargs)


def _model(entities: dict) -> TargetModel:
    return TargetModel.model_validate({"model": {"name": "Test Model", "version": "1.0.0"}, "entities": entities})


class TestResolveEffectiveIdentity:
    """Default resolution from role and aggregate parent."""

    def test_fact_defaults_to_tracked_allocate(self) -> None:
        effective = resolve_effective_identity(_spec(role="fact"))

        assert effective.identity_tracking == "tracked"
        assert effective.reconciliation == "allocate"
        assert effective.aggregate_parent is None

    def test_lookup_defaults_to_reconciled_reconcile_exact(self) -> None:
        effective = resolve_effective_identity(_spec(role="lookup"))

        assert effective.identity_tracking == "reconciled"
        assert effective.reconciliation == "reconcile-exact"
        assert effective.aggregate_parent is None

    def test_classifier_defaults_to_reconciled_lookup_only(self) -> None:
        effective = resolve_effective_identity(_spec(role="classifier"))

        assert effective.identity_tracking == "reconciled"
        assert effective.reconciliation == "lookup-only"
        assert effective.aggregate_parent is None

    def test_bridge_defaults_to_derived_derive(self) -> None:
        effective = resolve_effective_identity(_spec(role="bridge"))

        assert effective.identity_tracking == "derived"
        assert effective.reconciliation == "derive"
        assert effective.aggregate_parent is None

    def test_aggregate_parent_implies_child_without_reconciliation(self) -> None:
        effective = resolve_effective_identity(_spec(role="fact", aggregate_parent="sample"))

        assert effective.identity_tracking == "child"
        assert effective.reconciliation is None
        assert effective.aggregate_parent == "sample"

    def test_explicit_values_override_role_defaults(self) -> None:
        # analysis_entity: bridge role but explicitly tracked/allocate.
        effective = resolve_effective_identity(_spec(role="bridge", identity_tracking="tracked", reconciliation="allocate"))

        assert effective.identity_tracking == "tracked"
        assert effective.reconciliation == "allocate"
        assert effective.aggregate_parent is None

    def test_does_not_mutate_input_spec(self) -> None:
        spec = _spec(role="fact")

        resolve_effective_identity(spec)

        assert spec.identity_tracking is None
        assert spec.reconciliation is None


class TestResolverAgreement:
    """The shared resolver, validator, and documentation generator must agree."""

    @pytest.mark.parametrize(
        ("role", "identity_tracking", "reconciliation", "aggregate_parent", "expected_tracking", "expected_reconciliation"),
        [
            ("fact", None, None, None, "tracked", "allocate"),
            ("lookup", None, None, None, "reconciled", "reconcile-exact"),
            ("classifier", None, None, None, "reconciled", "lookup-only"),
            ("bridge", None, None, None, "derived", "derive"),
            ("fact", None, None, "sample", "child", None),
            ("bridge", "tracked", "allocate", None, "tracked", "allocate"),
        ],
    )
    def test_three_resolvers_agree(
        self,
        role: str,
        identity_tracking: str | None,
        reconciliation: str | None,
        aggregate_parent: str | None,
        expected_tracking: str | None,
        expected_reconciliation: str | None,
    ) -> None:
        spec = _spec(
            role=role,
            identity_tracking=identity_tracking,
            reconciliation=reconciliation,
            aggregate_parent=aggregate_parent,
        )

        shared = resolve_effective_identity(spec)
        validator_tuple = TargetModelSpecValidator._resolve_effective_sims(spec)
        documentation_dict = SimsDocumentGenerator._resolve_effective_sims(spec)

        assert shared.identity_tracking == expected_tracking
        assert shared.reconciliation == expected_reconciliation
        assert shared.aggregate_parent == aggregate_parent

        assert validator_tuple == (expected_tracking, expected_reconciliation)

        assert documentation_dict == {
            "identity_tracking": expected_tracking,
            "reconciliation": expected_reconciliation,
            "aggregate_parent": aggregate_parent,
        }


class TestResolveAggregateChain:
    """Full aggregate-parent chain resolution to a tracked or reconciled root."""

    def test_root_entity_resolves_to_itself(self) -> None:
        model = _model({"sample": {"role": "fact", "public_id": "physical_sample_id"}})

        chain = resolve_aggregate_chain(model, "sample")

        assert chain.entity_chain == ("sample",)
        assert chain.root_entity == "sample"
        assert chain.root_identity_tracking == "tracked"
        assert chain.root_reconciliation == "allocate"
        assert chain.is_valid

    def test_fact_role_child_resolves_through_one_parent_to_tracked_root(self) -> None:
        model = _model(
            {
                "sample": {"role": "fact", "public_id": "physical_sample_id"},
                "sample_note": {"role": "fact", "public_id": "sample_note_id", "aggregate_parent": "sample"},
            }
        )

        chain = resolve_aggregate_chain(model, "sample_note")

        assert chain.parent_chain == ("sample",)
        assert chain.root_entity == "sample"
        assert chain.root_identity_tracking == "tracked"
        assert chain.is_valid

    def test_bridge_role_child_resolves_to_reconciled_root(self) -> None:
        model = _model(
            {
                "sample_group": {"role": "fact", "public_id": "sample_group_id"},
                "sample_group_reference": {
                    "role": "bridge",
                    "public_id": "sample_group_reference_id",
                    "aggregate_parent": "sample_group",
                },
            }
        )

        chain = resolve_aggregate_chain(model, "sample_group_reference")

        assert chain.parent_chain == ("sample_group",)
        assert chain.root_identity_tracking == "tracked"

    def test_multi_level_chain_ends_at_reconciled_root(self) -> None:
        model = _model(
            {
                "value_type": {"role": "classifier", "public_id": "value_type_id"},
                "value_class": {
                    "role": "classifier",
                    "public_id": "value_class_id",
                },
                "analysis_value": {
                    "role": "fact",
                    "public_id": "analysis_value_id",
                    "aggregate_parent": "value_class",
                },
                "analysis_note": {
                    "role": "fact",
                    "public_id": "analysis_note_id",
                    "aggregate_parent": "analysis_value",
                },
            }
        )

        chain = resolve_aggregate_chain(model, "analysis_note")

        assert chain.parent_chain == ("analysis_value", "value_class")
        assert chain.root_entity == "value_class"
        assert chain.root_identity_tracking == "reconciled"
        assert chain.root_reconciliation == "lookup-only"
        assert chain.is_valid

    def test_missing_parent_reports_issue_without_a_chain(self) -> None:
        model = _model({"orphan": {"role": "fact", "public_id": "orphan_id", "aggregate_parent": "missing"}})

        chain = resolve_aggregate_chain(model, "orphan")

        assert chain.parent_chain == ()
        assert chain.root_entity is None
        assert [issue.code for issue in chain.issues] == ["UNKNOWN_AGGREGATE_PARENT"]

    def test_derived_root_is_not_a_supported_aggregate_root(self) -> None:
        model = _model(
            {
                "abundance_ident_level": {"role": "bridge", "public_id": "abundance_ident_level_id"},
                "child": {"role": "fact", "public_id": "child_id", "aggregate_parent": "abundance_ident_level"},
            }
        )

        chain = resolve_aggregate_chain(model, "child")

        assert chain.root_entity == "abundance_ident_level"
        assert chain.root_identity_tracking == "derived"
        assert [issue.code for issue in chain.issues] == ["INVALID_AGGREGATE_ROOT_IDENTITY"]

    def test_two_entity_cycle_reports_canonical_members_for_each_member(self) -> None:
        model = _model(
            {
                "alpha": {"role": "fact", "public_id": "alpha_id", "aggregate_parent": "beta"},
                "beta": {"role": "fact", "public_id": "beta_id", "aggregate_parent": "alpha"},
            }
        )

        alpha_chain = resolve_aggregate_chain(model, "alpha")
        beta_chain = resolve_aggregate_chain(model, "beta")

        assert [issue.code for issue in alpha_chain.issues] == ["AGGREGATE_PARENT_CYCLE"]
        assert [issue.code for issue in beta_chain.issues] == ["AGGREGATE_PARENT_CYCLE"]
        assert alpha_chain.issues[0].cycle == ("alpha", "beta")
        assert beta_chain.issues[0].cycle == ("alpha", "beta")
        assert alpha_chain.issues[0].message == beta_chain.issues[0].message

    def test_three_entity_cycle_reports_each_member_cycle(self) -> None:
        model = _model(
            {
                "alpha": {"role": "fact", "public_id": "alpha_id", "aggregate_parent": "beta"},
                "beta": {"role": "fact", "public_id": "beta_id", "aggregate_parent": "gamma"},
                "gamma": {"role": "fact", "public_id": "gamma_id", "aggregate_parent": "alpha"},
            }
        )

        chain = resolve_aggregate_chain(model, "beta")

        assert chain.issues[0].cycle == ("alpha", "beta", "gamma")
        assert chain.issues[0].message == "Aggregate parents form a cycle: alpha -> beta -> gamma -> alpha"

    def test_self_reference_reports_issue(self) -> None:
        model = _model({"recursive": {"role": "fact", "public_id": "recursive_id", "aggregate_parent": "recursive"}})

        chain = resolve_aggregate_chain(model, "recursive")

        assert [issue.code for issue in chain.issues] == ["SELF_REFERENTIAL_AGGREGATE_PARENT"]

    def test_explicit_child_without_parent_reports_issue(self) -> None:
        model = _model({"child": {"role": "fact", "public_id": "child_id", "identity_tracking": "child"}})

        chain = resolve_aggregate_chain(model, "child")

        assert [issue.code for issue in chain.issues] == ["CHILD_IDENTITY_MISSING_AGGREGATE_PARENT"]

    def test_missing_child_and_root_public_id_are_reported(self) -> None:
        model = _model(
            {
                "root": {"role": "fact"},
                "child": {"role": "fact", "aggregate_parent": "root"},
            }
        )

        chain = resolve_aggregate_chain(model, "child")

        assert [issue.code for issue in chain.issues] == [
            "AGGREGATE_CHILD_MISSING_PUBLIC_ID",
            "AGGREGATE_ROOT_MISSING_PUBLIC_ID",
        ]

    def test_unknown_entity_reports_issue(self) -> None:
        model = _model({"sample": {"role": "fact", "public_id": "physical_sample_id"}})

        chain = resolve_aggregate_chain(model, "missing")

        assert [issue.code for issue in chain.issues] == ["UNKNOWN_AGGREGATE_CHILD"]
        assert chain.root_entity is None

    def test_resolution_does_not_mutate_the_model(self) -> None:
        model = _model(
            {
                "sample": {"role": "fact", "public_id": "physical_sample_id"},
                "sample_note": {"role": "fact", "public_id": "sample_note_id", "aggregate_parent": "sample"},
            }
        )

        resolve_aggregate_chain(model, "sample_note")

        assert model.entities["sample_note"].aggregate_parent == "sample"
        assert model.entities["sample_note"].identity_tracking is None
