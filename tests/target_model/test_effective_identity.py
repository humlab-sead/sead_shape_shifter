"""Tests for the shared effective identity resolver."""

from __future__ import annotations

import pytest

from src.target_model.documentation import SimsDocumentGenerator
from src.target_model.effective_identity import resolve_effective_identity
from src.target_model.models import EntitySpec
from src.target_model.spec_validator import TargetModelSpecValidator


def _spec(**kwargs) -> EntitySpec:
    return EntitySpec.model_validate(kwargs)


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
        effective = resolve_effective_identity(
            _spec(role="bridge", identity_tracking="tracked", reconciliation="allocate")
        )

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
