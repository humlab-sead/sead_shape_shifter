"""Tests for SEAD change request identity work partitioning."""

import pandas as pd

from ingesters.sead_change_request import PlannedRowAction, PlannedTable, build_identity_work_plan


class TestBuildIdentityWorkPlan:
    """Tests for partitioning planned rows into identity work queues."""

    def test_partitions_rows_by_planned_action(self):
        """Rows should be split into the Delivery 1 queues without re-deriving actions."""
        sample_frame = pd.DataFrame({"sample_id": [1, None], "sample_name": ["A", "B"]})
        sample_actions = pd.Series(
            [PlannedRowAction.REFERENCE_EXISTING, PlannedRowAction.ALLOCATE],
            index=sample_frame.index,
            name="_planned_action",
        )
        classifier_frame = pd.DataFrame({"class_id": [None], "name": ["class-a"]})
        classifier_actions = pd.Series([PlannedRowAction.RECONCILE], index=classifier_frame.index, name="_planned_action")
        bridge_frame = pd.DataFrame({"sample_id": [1], "taxon_id": [2]})
        bridge_actions = pd.Series([PlannedRowAction.EVALUATE_BRIDGE], index=bridge_frame.index, name="_planned_action")

        work_plan = build_identity_work_plan(
            [
                PlannedTable(entity_name="sample", frame=sample_frame, planned_actions=sample_actions),
                PlannedTable(entity_name="abundance_class", frame=classifier_frame, planned_actions=classifier_actions),
                PlannedTable(entity_name="sample_taxon", frame=bridge_frame, planned_actions=bridge_actions),
            ]
        )

        assert work_plan.total_existing_rows == 1
        assert work_plan.total_allocation_rows == 1
        assert work_plan.total_reconciliation_rows == 1
        assert work_plan.total_bridge_rows == 1
        assert work_plan.existing_rows["sample"]["sample_name"].tolist() == ["A"]
        assert work_plan.allocation_rows["sample"]["sample_name"].tolist() == ["B"]
        assert work_plan.reconciliation_rows["abundance_class"]["name"].tolist() == ["class-a"]
        assert work_plan.bridge_rows["sample_taxon"]["taxon_id"].tolist() == [2]
