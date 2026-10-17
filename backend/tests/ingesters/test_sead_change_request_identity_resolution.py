"""Tests for SEAD change request identity resolution."""

import pandas as pd

from ingesters.sead_change_request import ChangeRowState, IdentityAssignment, PlannedRowAction, PlannedTable, resolve_planned_tables
from ingesters.sead_change_request.staging_eligibility import resolve_staged_children
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


def _sample_chain_model() -> TargetModel:
    """Build a sample -> sample_note aggregate chain for staging tests."""
    return minimal_target_model(
        sample={"role": "fact", "public_id": "physical_sample_id", "target_table": "tbl_physical_samples"},
        sample_note={
            "role": "fact",
            "public_id": "sample_note_id",
            "target_table": "tbl_sample_notes",
            "aggregate_parent": "sample",
            "foreign_keys": [{"entity": "sample", "required": True}],
        },
    )


def _planned(entity_name: str, frame: pd.DataFrame, action: PlannedRowAction) -> PlannedTable:
    """Build one planned table whose rows all share a planned action."""
    return PlannedTable(
        entity_name=entity_name,
        frame=frame,
        planned_actions=pd.Series([action] * len(frame.index), index=frame.index, name="_planned_action"),
    )


class TestResolveStagedChildren:
    """Root-row rules applied to rows whose target ID is allocated at deployment."""

    def _resolve(self, planned_tables, assignments):
        return resolve_staged_children(planned_tables, _sample_chain_model(), assignments)

    def test_inserted_tracked_root_allows_a_pending_child(self):
        sample = _planned("sample", pd.DataFrame({"system_id": [1], "physical_sample_id": [None]}), PlannedRowAction.ALLOCATE)
        note = _planned(
            "sample_note",
            pd.DataFrame({"system_id": [10], "sample_note_id": [None], "physical_sample_id": [1]}),
            PlannedRowAction.DEFER_TO_DEPLOYMENT,
        )
        assignments = {"sample": {0: IdentityAssignment(state=ChangeRowState.NEWLY_ALLOCATED_ENTITY, target_id=501)}}

        result = self._resolve([sample, note], assignments)

        assert result.assignments["sample_note"][0].state == ChangeRowState.PENDING_DEPLOYMENT_ID
        assert result.assignments["sample_note"][0].target_id is None
        assert any("allocated at deployment" in diagnostic for diagnostic in result.diagnostics)

    def test_existing_tracked_root_blocks_a_new_child(self):
        sample = _planned("sample", pd.DataFrame({"system_id": [1], "physical_sample_id": [501]}), PlannedRowAction.REFERENCE_EXISTING)
        note = _planned(
            "sample_note",
            pd.DataFrame({"system_id": [10], "sample_note_id": [None], "physical_sample_id": [1]}),
            PlannedRowAction.DEFER_TO_DEPLOYMENT,
        )

        result = self._resolve([sample, note], {})

        assignment = result.assignments["sample_note"][0]
        assert assignment.state == ChangeRowState.BLOCKED_UNRESOLVED
        assert "existing tracked root" in str(assignment.note)

    def test_missing_local_parent_reference_blocks_the_child(self):
        sample = _planned("sample", pd.DataFrame({"system_id": [1], "physical_sample_id": [None]}), PlannedRowAction.ALLOCATE)
        note = _planned(
            "sample_note",
            pd.DataFrame({"system_id": [10], "sample_note_id": [None], "physical_sample_id": [None]}),
            PlannedRowAction.DEFER_TO_DEPLOYMENT,
        )
        assignments = {"sample": {0: IdentityAssignment(state=ChangeRowState.NEWLY_ALLOCATED_ENTITY, target_id=501)}}

        result = self._resolve([sample, note], assignments)

        assignment = result.assignments["sample_note"][0]
        assert assignment.state == ChangeRowState.BLOCKED_UNRESOLVED
        assert "has no local reference" in str(assignment.note)

    def test_unsubmitted_parent_blocks_the_child(self):
        note = _planned(
            "sample_note",
            pd.DataFrame({"system_id": [10], "sample_note_id": [None], "physical_sample_id": [7]}),
            PlannedRowAction.DEFER_TO_DEPLOYMENT,
        )

        result = self._resolve([note], {})

        assignment = result.assignments["sample_note"][0]
        assert assignment.state == ChangeRowState.BLOCKED_UNRESOLVED
        assert "not part of the submitted tables" in str(assignment.note)

    def test_invalid_aggregate_chain_blocks_the_child(self):
        model = minimal_target_model(
            alpha={"role": "fact", "public_id": "alpha_id", "aggregate_parent": "beta"},
            beta={"role": "fact", "public_id": "beta_id", "aggregate_parent": "alpha"},
        )
        alpha = _planned(
            "alpha",
            pd.DataFrame({"system_id": [1], "alpha_id": [None], "beta_id": [2]}),
            PlannedRowAction.DEFER_TO_DEPLOYMENT,
        )

        result = resolve_staged_children([alpha], model, {})

        assignment = result.assignments["alpha"][0]
        assert assignment.state == ChangeRowState.BLOCKED_UNRESOLVED
        assert "AGGREGATE_PARENT_CYCLE" in str(assignment.note)

    def test_pending_middle_row_still_reaches_a_tracked_root(self):
        model = minimal_target_model(
            sample={"role": "fact", "public_id": "physical_sample_id", "target_table": "tbl_physical_samples"},
            sample_dimension={
                "role": "fact",
                "public_id": "sample_dimension_id",
                "target_table": "tbl_sample_dimensions",
                "aggregate_parent": "sample",
                "foreign_keys": [{"entity": "sample", "required": True}],
            },
            sample_dimension_note={
                "role": "fact",
                "public_id": "sample_dimension_note_id",
                "target_table": "tbl_sample_dimension_notes",
                "aggregate_parent": "sample_dimension",
                "foreign_keys": [{"entity": "sample_dimension", "required": True}],
            },
        )
        sample = _planned("sample", pd.DataFrame({"system_id": [1], "physical_sample_id": [None]}), PlannedRowAction.ALLOCATE)
        dimension = _planned(
            "sample_dimension",
            pd.DataFrame({"system_id": [10], "sample_dimension_id": [None], "physical_sample_id": [1]}),
            PlannedRowAction.DEFER_TO_DEPLOYMENT,
        )
        note = _planned(
            "sample_dimension_note",
            pd.DataFrame({"system_id": [20], "sample_dimension_note_id": [None], "sample_dimension_id": [10]}),
            PlannedRowAction.DEFER_TO_DEPLOYMENT,
        )

        assignments = {"sample": {0: IdentityAssignment(ChangeRowState.NEWLY_ALLOCATED_ENTITY, 501)}}

        result = resolve_staged_children([sample, dimension, note], model, assignments)

        assert result.assignments["sample_dimension"][0].state == ChangeRowState.PENDING_DEPLOYMENT_ID
        assert result.assignments["sample_dimension_note"][0].state == ChangeRowState.PENDING_DEPLOYMENT_ID

    def test_reconciled_root_with_known_id_allows_a_pending_child(self):
        model = minimal_target_model(
            site={"role": "lookup", "public_id": "site_id", "target_table": "tbl_sites"},
            site_property={
                "role": "fact",
                "public_id": "site_property_id",
                "target_table": "tbl_site_properties",
                "aggregate_parent": "site",
                "foreign_keys": [{"entity": "site", "required": True}],
            },
        )
        site = _planned("site", pd.DataFrame({"system_id": [1], "site_id": [7001]}), PlannedRowAction.REFERENCE_EXISTING)
        prop = _planned(
            "site_property",
            pd.DataFrame({"system_id": [10], "site_property_id": [None], "site_id": [1]}),
            PlannedRowAction.DEFER_TO_DEPLOYMENT,
        )

        result = resolve_staged_children([site, prop], model, {})

        assert result.assignments["site_property"][0].state == ChangeRowState.PENDING_DEPLOYMENT_ID

    def test_unresolved_reconciled_root_blocks_the_child(self):
        model = minimal_target_model(
            site={"role": "lookup", "public_id": "site_id", "target_table": "tbl_sites"},
            site_property={
                "role": "fact",
                "public_id": "site_property_id",
                "target_table": "tbl_site_properties",
                "aggregate_parent": "site",
                "foreign_keys": [{"entity": "site", "required": True}],
            },
        )
        site = _planned("site", pd.DataFrame({"system_id": [1], "site_id": [None]}), PlannedRowAction.RECONCILE)
        prop = _planned(
            "site_property",
            pd.DataFrame({"system_id": [10], "site_property_id": [None], "site_id": [1]}),
            PlannedRowAction.DEFER_TO_DEPLOYMENT,
        )

        result = resolve_staged_children([site, prop], model, {})

        assignment = result.assignments["site_property"][0]
        assert assignment.state == ChangeRowState.BLOCKED_UNRESOLVED
        assert "has no resolved target ID" in str(assignment.note)

    def test_new_value_type_root_is_rejected(self):
        model = minimal_target_model(
            value_type={"role": "classifier", "public_id": "value_type_id", "target_table": "tbl_value_types"},
            value_type_item={
                "role": "classifier",
                "public_id": "value_type_item_id",
                "target_table": "tbl_value_type_items",
                "aggregate_parent": "value_type",
                "foreign_keys": [{"entity": "value_type", "required": True}],
            },
        )
        value_type = _planned("value_type", pd.DataFrame({"system_id": [1], "value_type_id": [None]}), PlannedRowAction.RECONCILE)
        item = _planned(
            "value_type_item",
            pd.DataFrame({"system_id": [10], "value_type_item_id": [None], "value_type_id": [1]}),
            PlannedRowAction.DEFER_TO_DEPLOYMENT,
        )
        assignments = {"value_type": {0: IdentityAssignment(ChangeRowState.NEWLY_ALLOCATED_ENTITY, 400)}}

        result = resolve_staged_children([value_type, item], model, assignments)

        assignment = result.assignments["value_type_item"][0]
        assert assignment.state == ChangeRowState.BLOCKED_UNRESOLVED
        assert "outside the deployment-time staging scope" in str(assignment.note)

    def test_non_deferred_rows_keep_their_assignments(self):
        sample = _planned("sample", pd.DataFrame({"system_id": [1], "physical_sample_id": [None]}), PlannedRowAction.ALLOCATE)

        result = self._resolve([sample], {})

        assert result.assignments == {}
        assert result.diagnostics == []

class TestResolvePlannedTables:
    """Tests for resolving planned rows into MVP Delivery states."""

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
