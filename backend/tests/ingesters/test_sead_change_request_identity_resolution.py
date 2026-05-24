"""Tests for SEAD change request identity resolution."""

import pandas as pd

from ingesters.sead_change_request import ChangeRowState, IdentityAssignment, PlannedRowAction, PlannedTable, resolve_planned_tables
from src.target_model.models import TargetModel


def minimal_target_model(**extra_entities: dict) -> TargetModel:
    """Build a minimal TargetModel for identity-resolution tests."""
    return TargetModel.model_validate(
        {
            "model": {"name": "SEAD Test Model", "version": "0.1.0"},
            "entities": extra_entities,
            "constraints": [],
        }
    )


class TestResolvePlannedTables:
    """Tests for resolving planned rows into Delivery 1 states."""

    def test_existing_rows_resolve_from_public_id(self):
        """Reference-existing rows should resolve directly from the public_id column."""
        frame = pd.DataFrame({"sample_id": [101], "sample_name": ["A"]})
        planned_table = PlannedTable(
            entity_name="sample",
            frame=frame,
            planned_actions=pd.Series([PlannedRowAction.REFERENCE_EXISTING], index=frame.index, name="_planned_action"),
        )

        result = resolve_planned_tables(
            [planned_table],
            minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
        )

        resolved = result.tables["sample"]
        assert resolved.row_states.tolist() == [ChangeRowState.EXISTING_ENTITY]
        assert resolved.resolved_target_ids.tolist() == [101]
        assert result.blocked_rows == 0

    def test_assigned_rows_resolve_to_delivery1_states(self):
        """Allocated, reconciled, and bridge rows should take their states from injected assignments."""
        classifier_frame = pd.DataFrame({"class_id": [None], "name": ["A"]})
        bridge_frame = pd.DataFrame({"sample_id": [1], "taxon_id": [2]})
        planned_tables = [
            PlannedTable(
                entity_name="abundance_class",
                frame=classifier_frame,
                planned_actions=pd.Series([PlannedRowAction.RECONCILE], index=classifier_frame.index, name="_planned_action"),
            ),
            PlannedTable(
                entity_name="sample_taxon",
                frame=bridge_frame,
                planned_actions=pd.Series([PlannedRowAction.EVALUATE_BRIDGE], index=bridge_frame.index, name="_planned_action"),
            ),
        ]
        target_model = minimal_target_model(
            abundance_class={"role": "classifier", "public_id": "class_id"},
            sample_taxon={"role": "bridge"},
        )

        result = resolve_planned_tables(
            planned_tables,
            target_model,
            assignments={
                "abundance_class": {0: IdentityAssignment(state=ChangeRowState.RECONCILED_CLASSIFIER, target_id=77)},
                "sample_taxon": {0: IdentityAssignment(state=ChangeRowState.DERIVED_BRIDGE_ROW, target_id=5001)},
            },
        )

        assert result.tables["abundance_class"].row_states.tolist() == [ChangeRowState.RECONCILED_CLASSIFIER]
        assert result.tables["abundance_class"].resolved_target_ids.tolist() == [77]
        assert result.tables["sample_taxon"].row_states.tolist() == [ChangeRowState.DERIVED_BRIDGE_ROW]
        assert result.tables["sample_taxon"].resolved_target_ids.tolist() == [5001]
        assert result.blocked_rows == 0

    def test_missing_assignments_block_rows(self):
        """Rows without assignments should become blocked_unresolved until orchestration fills them in."""
        frame = pd.DataFrame({"sample_id": [None], "sample_name": ["A"]})
        planned_table = PlannedTable(
            entity_name="sample",
            frame=frame,
            planned_actions=pd.Series([PlannedRowAction.ALLOCATE], index=frame.index, name="_planned_action"),
        )

        result = resolve_planned_tables(
            [planned_table],
            minimal_target_model(sample={"role": "fact", "public_id": "sample_id"}),
        )

        resolved = result.tables["sample"]
        assert resolved.row_states.tolist() == [ChangeRowState.BLOCKED_UNRESOLVED]
        assert resolved.resolved_target_ids.isna().tolist() == [True]
        assert result.blocked_rows == 1
        assert result.diagnostics == ["Entity 'sample' row '0' is missing an identity assignment for planned action 'allocate'"]
