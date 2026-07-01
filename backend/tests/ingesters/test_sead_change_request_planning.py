"""Tests for SEAD change request row planning."""

import numpy as np
import pandas as pd
import pytest

from ingesters.sead_change_request import PlannedRowAction, plan_table
from ingesters.sead_change_request.contracts import (
    ChangeRowState,
    IdentityResolutionResult,
    ResolvedIdentityTable,
    classify_submission_outcomes,
)
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

        assert not plan.diagnostics
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

    def test_fact_rows_treat_numpy_missing_public_ids_as_missing(self):
        """NumPy-backed missing public_id values should not be treated as existing references."""
        frame = pd.DataFrame(
            {
                "sample_id": pd.Series([np.int64(101), np.float64(np.nan), np.int64(104)], dtype="object"),
                "sample_name": ["A", "B", "C"],
            }
        )
        entity_spec = EntitySpec(role="fact", public_id="sample_id")

        plan = plan_table("sample", frame, entity_spec)

        assert plan.planned_actions.tolist() == [
            PlannedRowAction.REFERENCE_EXISTING,
            PlannedRowAction.ALLOCATE,
            PlannedRowAction.REFERENCE_EXISTING,
        ]

    def test_bridge_rows_plan_for_bridge_evaluation(self):
        """Bridge rows should be evaluated independently from public_id presence."""
        frame = pd.DataFrame({"sample_id": [1], "taxon_id": [2]})
        entity_spec = EntitySpec(role="bridge", unique_sets=[["sample_id", "taxon_id"]])

        plan = plan_table("sample_taxon", frame, entity_spec)

        assert plan.planned_actions.tolist() == [PlannedRowAction.EVALUATE_BRIDGE]
        assert not plan.diagnostics

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

    def test_existing_rows_route_to_update_candidate_when_mutable_field_changes(self):
        """Existing rows should become update candidates when configured mutable fields differ from baseline."""
        frame = pd.DataFrame(
            {
                "sample_id": [101, 102],
                "sample_name": ["A", "B updated"],
                "sample_name__existing": ["A", "B"],
            }
        )
        entity_spec = EntitySpec(role="fact", public_id="sample_id")

        plan = plan_table("sample", frame, entity_spec, mutable_fields=["sample_name"])

        assert plan.planned_actions.tolist() == [
            PlannedRowAction.REFERENCE_EXISTING,
            PlannedRowAction.UPDATE_EXISTING_CANDIDATE,
        ]
        assert plan.diagnostics == []

    def test_existing_rows_blocked_when_mutable_baseline_columns_are_missing(self):
        """Existing-row update planning should block rows when configured mutable baseline columns are missing."""
        frame = pd.DataFrame(
            {
                "sample_id": [101],
                "sample_name": ["A changed"],
            }
        )
        entity_spec = EntitySpec(role="fact", public_id="sample_id")

        plan = plan_table("sample", frame, entity_spec, mutable_fields=["sample_name"])

        assert plan.planned_actions.tolist() == [PlannedRowAction.BLOCK_EXISTING_UPDATE]
        assert any("blocked existing-row update planning" in diagnostic for diagnostic in plan.diagnostics)

    def test_existing_rows_blocked_outside_first_slice_scope(self):
        """Entities outside the first-slice allowlist should keep existing-row updates blocked."""
        frame = pd.DataFrame(
            {
                "sample_id": [101],
                "sample_name": ["A changed"],
                "sample_name__existing": ["A"],
            }
        )
        entity_spec = EntitySpec(role="fact", public_id="sample_id")

        plan = plan_table(
            "sample",
            frame,
            entity_spec,
            mutable_fields=["sample_name"],
            existing_row_update_entities={"other_entity"},
        )

        assert plan.planned_actions.tolist() == [PlannedRowAction.BLOCK_EXISTING_UPDATE]
        assert any("outside the first existing-row update slice" in diagnostic for diagnostic in plan.diagnostics)

    def test_existing_rows_outside_first_slice_keep_no_op_rows_unblocked(self):
        """Unchanged rows outside the first-slice allowlist should remain reference-only."""
        frame = pd.DataFrame(
            {
                "sample_id": [101],
                "sample_name": ["A"],
                "sample_name__existing": ["A"],
            }
        )
        entity_spec = EntitySpec(role="fact", public_id="sample_id")

        plan = plan_table(
            "sample",
            frame,
            entity_spec,
            mutable_fields=["sample_name"],
            existing_row_update_entities={"other_entity"},
        )

        assert plan.planned_actions.tolist() == [PlannedRowAction.REFERENCE_EXISTING]
        assert not plan.diagnostics


class TestSubmissionOutcomeClassification:
    """Tests for phase-2 submission outcome classification."""

    def test_classification_reports_all_outcome_classes(self):
        """Classification should count new/no-op/allowed/pending-review/blocked rows."""
        planned = [
            plan_table(
                "sample",
                pd.DataFrame(
                    {
                        "sample_id": [101, 102],
                        "sample_name": ["A", "B"],
                        "sample_name__existing": ["A", "B-old"],
                    }
                ),
                EntitySpec(role="fact", public_id="sample_id"),
            ),
            plan_table(
                "sample_taxon",
                pd.DataFrame({"sample_id": [1], "taxon_id": [2]}),
                EntitySpec(role="bridge", unique_sets=[["sample_id", "taxon_id"]]),
            ),
            plan_table(
                "abundance_class",
                pd.DataFrame({"class_id": [None]}),
                EntitySpec(role="classifier", public_id="class_id"),
            ),
            plan_table(
                "sample_missing",
                pd.DataFrame({"sample_id": [None]}),
                EntitySpec(role="fact", public_id="sample_id"),
            ),
        ]

        identity_result = IdentityResolutionResult(
            tables={
                "sample": ResolvedIdentityTable(
                    entity_name="sample",
                    frame=planned[0].frame,
                    row_states=pd.Series(
                        [ChangeRowState.EXISTING_ENTITY, ChangeRowState.EXISTING_ENTITY],
                        index=planned[0].frame.index,
                        name="_row_state",
                    ),
                    resolved_target_ids=pd.Series([101, 102], index=planned[0].frame.index, dtype="Int64", name="_target_id"),
                ),
                "sample_taxon": ResolvedIdentityTable(
                    entity_name="sample_taxon",
                    frame=planned[1].frame,
                    row_states=pd.Series(
                        [ChangeRowState.DERIVED_BRIDGE_ROW],
                        index=planned[1].frame.index,
                        name="_row_state",
                    ),
                    resolved_target_ids=pd.Series([pd.NA], index=planned[1].frame.index, dtype="Int64", name="_target_id"),
                ),
                "abundance_class": ResolvedIdentityTable(
                    entity_name="abundance_class",
                    frame=planned[2].frame,
                    row_states=pd.Series(
                        [ChangeRowState.RECONCILED_CLASSIFIER],
                        index=planned[2].frame.index,
                        name="_row_state",
                    ),
                    resolved_target_ids=pd.Series([501], index=planned[2].frame.index, dtype="Int64", name="_target_id"),
                ),
                "sample_missing": ResolvedIdentityTable(
                    entity_name="sample_missing",
                    frame=planned[3].frame,
                    row_states=pd.Series(
                        [ChangeRowState.BLOCKED_UNRESOLVED],
                        index=planned[3].frame.index,
                        name="_row_state",
                    ),
                    resolved_target_ids=pd.Series([pd.NA], index=planned[3].frame.index, dtype="Int64", name="_target_id"),
                ),
            }
        )

        summary = classify_submission_outcomes(planned, identity_result, has_pending_review=True)

        assert summary.new_data_rows == 2
        assert summary.no_op_rows == 1
        assert summary.allowed_update_rows == 1
        assert summary.pending_review_rows == 1
        assert summary.blocked_rows == 0
        assert any("Outcome classification:" in diagnostic for diagnostic in summary.diagnostics)

    def test_classification_uses_configured_mutable_fields_scope(self):
        """Configured mutable fields should control no-op detection for existing rows."""
        planned = [
            plan_table(
                "sample",
                pd.DataFrame(
                    {
                        "sample_id": [101],
                        "sample_name": ["A"],
                        "sample_name__existing": ["A"],
                        "sample_note": ["changed"],
                        "sample_note__existing": ["old"],
                    }
                ),
                EntitySpec(role="fact", public_id="sample_id"),
            )
        ]
        identity_result = IdentityResolutionResult(
            tables={
                "sample": ResolvedIdentityTable(
                    entity_name="sample",
                    frame=planned[0].frame,
                    row_states=pd.Series([ChangeRowState.EXISTING_ENTITY], index=planned[0].frame.index, name="_row_state"),
                    resolved_target_ids=pd.Series([101], index=planned[0].frame.index, dtype="Int64", name="_target_id"),
                )
            }
        )

        summary = classify_submission_outcomes(
            planned,
            identity_result,
            has_pending_review=False,
            mutable_fields_by_entity={"sample": ["sample_name"]},
        )

        assert summary.no_op_rows == 1
        assert summary.allowed_update_rows == 0

    def test_classification_treats_row_as_allowed_update_when_configured_mutable_field_differs(self):
        """Configured mutable fields should mark existing rows as allowed_update when any scoped field changes."""
        planned = [
            plan_table(
                "sample",
                pd.DataFrame(
                    {
                        "sample_id": [101],
                        "sample_name": ["A changed"],
                        "sample_name__existing": ["A"],
                    }
                ),
                EntitySpec(role="fact", public_id="sample_id"),
            )
        ]
        identity_result = IdentityResolutionResult(
            tables={
                "sample": ResolvedIdentityTable(
                    entity_name="sample",
                    frame=planned[0].frame,
                    row_states=pd.Series([ChangeRowState.EXISTING_ENTITY], index=planned[0].frame.index, name="_row_state"),
                    resolved_target_ids=pd.Series([101], index=planned[0].frame.index, dtype="Int64", name="_target_id"),
                )
            }
        )

        summary = classify_submission_outcomes(
            planned,
            identity_result,
            has_pending_review=False,
            mutable_fields_by_entity={"sample": ["sample_name"]},
        )

        assert summary.no_op_rows == 0
        assert summary.allowed_update_rows == 1

    def test_classification_reports_missing_baseline_columns_when_existing_rows_cannot_be_compared(self):
        """Classification should explain when existing rows have no mutable baseline columns."""
        planned = [
            plan_table(
                "sample",
                pd.DataFrame({"sample_id": [101], "sample_name": ["A"]}),
                EntitySpec(role="fact", public_id="sample_id"),
            )
        ]
        identity_result = IdentityResolutionResult(
            tables={
                "sample": ResolvedIdentityTable(
                    entity_name="sample",
                    frame=planned[0].frame,
                    row_states=pd.Series([ChangeRowState.EXISTING_ENTITY], index=planned[0].frame.index, name="_row_state"),
                    resolved_target_ids=pd.Series([101], index=planned[0].frame.index, dtype="Int64", name="_target_id"),
                )
            }
        )

        summary = classify_submission_outcomes(planned, identity_result, has_pending_review=False)

        assert summary.no_op_rows == 0
        assert summary.allowed_update_rows == 1
        assert any("No mutable baseline columns were provided" in diagnostic for diagnostic in summary.diagnostics)
