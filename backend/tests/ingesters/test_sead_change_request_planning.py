"""Tests for SEAD change request row planning."""

import pandas as pd
import pytest

from ingesters.sead_change_request import PlannedRowAction, plan_table
from src.target_model.models import EntitySpec


class TestPlanTable:
    """Tests for deterministic Delivery 1 work planning."""

    def test_fact_rows_split_between_reference_and_allocate(self):
        """Fact rows should use public_id presence to separate reference-only rows from allocation candidates."""
        frame = pd.DataFrame(
            {
                "sample_id": [101, None, "", 104],
                "sample_name": ["A", "B", "C", "D"],
            }
        )
        entity_spec = EntitySpec(role="fact", public_id="sample_id")

        plan = plan_table("sample", frame, entity_spec)

        assert plan.diagnostics == []
        assert plan.planned_actions.tolist() == [
            PlannedRowAction.REFERENCE_EXISTING,
            PlannedRowAction.ALLOCATE,
            PlannedRowAction.ALLOCATE,
            PlannedRowAction.REFERENCE_EXISTING,
        ]

    def test_classifier_rows_missing_public_id_plan_for_reconciliation(self):
        """Classifier rows without public_id should plan for reconciliation first."""
        frame = pd.DataFrame({"class_id": [None, ""], "name": ["A", "B"]})
        entity_spec = EntitySpec(role="classifier", public_id="class_id")

        plan = plan_table("abundance_class", frame, entity_spec)

        assert plan.planned_actions.tolist() == [PlannedRowAction.RECONCILE, PlannedRowAction.RECONCILE]

    def test_bridge_rows_plan_for_bridge_evaluation(self):
        """Bridge rows should be evaluated independently from public_id presence."""
        frame = pd.DataFrame({"sample_id": [1], "taxon_id": [2]})
        entity_spec = EntitySpec(role="bridge", unique_sets=[["sample_id", "taxon_id"]])

        plan = plan_table("sample_taxon", frame, entity_spec)

        assert plan.planned_actions.tolist() == [PlannedRowAction.EVALUATE_BRIDGE]
        assert plan.diagnostics == []

    def test_bridge_rows_report_missing_uniqueness_metadata(self):
        """Bridge rows should surface missing uniqueness metadata as an early diagnostic."""
        frame = pd.DataFrame({"sample_id": [1], "taxon_id": [2]})
        entity_spec = EntitySpec(role="bridge")

        plan = plan_table("sample_taxon", frame, entity_spec)

        assert plan.planned_actions.tolist() == [PlannedRowAction.EVALUATE_BRIDGE]
        assert plan.diagnostics == [
            "Bridge entity 'sample_taxon' has no unique_sets metadata; Delivery 1 uniqueness checks will be blocked"
        ]

    def test_non_bridge_entities_require_public_id_metadata(self):
        """Non-bridge planning should fail when the target model does not expose public_id metadata."""
        frame = pd.DataFrame({"sample_name": ["A"]})
        entity_spec = EntitySpec(role="fact")

        with pytest.raises(ValueError, match="missing target-model public_id metadata"):
            plan_table("sample", frame, entity_spec)

    def test_non_bridge_entities_require_public_id_column_in_frame(self):
        """Non-bridge planning should fail when the source bundle is missing the declared public_id column."""
        frame = pd.DataFrame({"sample_name": ["A"]})
        entity_spec = EntitySpec(role="fact", public_id="sample_id")

        with pytest.raises(ValueError, match="missing public_id column 'sample_id'"):
            plan_table("sample", frame, entity_spec)
