"""Tests for SEAD change request in-memory package building."""

import pandas as pd

from ingesters.sead_change_request import (
    ChangeRowState,
    PlannedRowAction,
    PlannedTable,
    build_change_request_package,
    project_target_ids,
)
from ingesters.sead_change_request.contracts import (
    IdentityResolutionResult,
    ProjectedTable,
    ResolvedIdentityTable,
    TargetProjectionResult,
)
from ingesters.sead_change_request.package_builder import build_staging_package
from src.target_model.models import TargetModel


def conditional_location_target_model() -> TargetModel:
    """Build a target model with a conditional location -> location_type foreign key."""
    return TargetModel.model_validate(
        {
            "model": {"name": "SEAD Test Model", "version": "0.1.0"},
            "entities": {
                "location_type": {"role": "lookup", "public_id": "location_type_id"},
                "location": {
                    "role": "fact",
                    "public_id": "location_id",
                    "columns": {"location_type_id": {"type": "integer", "nullable": False}},
                    "foreign_keys": [{"entity": "location_type", "required_when": {"has_new_rows": "location"}}],
                },
            },
            "constraints": [],
        }
    )


class TestBuildChangeRequestPackage:
    """Tests for selecting insertable rows into the first in-memory package."""

    def test_includes_only_insertable_row_states(self):
        """Only newly allocated entities and derived bridge rows should enter the MVP Delivery package."""
        sample_frame = pd.DataFrame(
            {
                "system_id": [1, 2, 3],
                "sample_id": [101, 102, 103],
                "sample_name": ["existing", "new", "classifier"],
            }
        )
        bridge_frame = pd.DataFrame({"sample_taxon_id": [5001], "sample_id": [101], "taxon_id": [9001]})
        identity_result = IdentityResolutionResult(
            tables={
                "sample": ResolvedIdentityTable(
                    entity_name="sample",
                    frame=sample_frame,
                    row_states=pd.Series(
                        [
                            ChangeRowState.EXISTING_ENTITY,
                            ChangeRowState.NEWLY_ALLOCATED_ENTITY,
                            ChangeRowState.RECONCILED_CLASSIFIER,
                        ],
                        index=sample_frame.index,
                        name="_row_state",
                    ),
                    resolved_target_ids=pd.Series([101, 102, 103], index=sample_frame.index, dtype="Int64", name="_target_id"),
                ),
                "sample_taxon": ResolvedIdentityTable(
                    entity_name="sample_taxon",
                    frame=bridge_frame,
                    row_states=pd.Series([ChangeRowState.DERIVED_BRIDGE_ROW], index=bridge_frame.index, name="_row_state"),
                    resolved_target_ids=pd.Series([5001], index=bridge_frame.index, dtype="Int64", name="_target_id"),
                ),
            }
        )
        projection_result = TargetProjectionResult(
            tables={
                "sample": ProjectedTable(entity_name="sample", frame=sample_frame.copy()),
                "sample_taxon": ProjectedTable(entity_name="sample_taxon", frame=bridge_frame.copy()),
            }
        )
        planned_tables = [
            PlannedTable(
                entity_name="sample",
                frame=sample_frame,
                planned_actions=pd.Series(
                    [PlannedRowAction.REFERENCE_EXISTING, PlannedRowAction.ALLOCATE, PlannedRowAction.RECONCILE],
                    index=sample_frame.index,
                    name="_planned_action",
                ),
            ),
            PlannedTable(
                entity_name="sample_taxon",
                frame=bridge_frame,
                planned_actions=pd.Series(
                    [PlannedRowAction.EVALUATE_BRIDGE],
                    index=bridge_frame.index,
                    name="_planned_action",
                ),
            ),
        ]

        package = build_change_request_package(projection_result, identity_result, planned_tables)

        assert set(package.tables) == {"sample", "sample_taxon"}
        assert package.tables["sample"].frame["sample_name"].tolist() == ["new"]
        assert package.tables["sample"].row_states.tolist() == [ChangeRowState.NEWLY_ALLOCATED_ENTITY]
        assert package.tables["sample"].planned_actions is not None
        assert package.tables["sample"].planned_actions.tolist() == [PlannedRowAction.ALLOCATE]
        assert package.tables["sample_taxon"].frame["sample_taxon_id"].tolist() == [5001]
        assert package.tables["sample_taxon"].row_states.tolist() == [ChangeRowState.DERIVED_BRIDGE_ROW]

    def test_skips_tables_without_insertable_rows(self):
        """Reference-only or reconciled-only tables should not enter the package."""
        frame = pd.DataFrame({"site_id": [101], "site_name": ["existing"]})
        identity_result = IdentityResolutionResult(
            tables={
                "site": ResolvedIdentityTable(
                    entity_name="site",
                    frame=frame,
                    row_states=pd.Series([ChangeRowState.EXISTING_ENTITY], index=frame.index, name="_row_state"),
                    resolved_target_ids=pd.Series([101], index=frame.index, dtype="Int64", name="_target_id"),
                )
            }
        )
        projection_result = TargetProjectionResult(tables={"site": ProjectedTable(entity_name="site", frame=frame.copy())})

        package = build_change_request_package(projection_result, identity_result)

        assert not package.tables

    def test_includes_update_candidates_when_planned_tables_are_provided(self):
        """Accepted existing-row update candidates should be included alongside insertable rows."""
        frame = pd.DataFrame(
            {
                "system_id": [1, 2],
                "sample_id": [101, 102],
                "sample_name": ["existing", "changed"],
                "sample_name__existing": ["existing", "old"],
            }
        )
        identity_result = IdentityResolutionResult(
            tables={
                "sample": ResolvedIdentityTable(
                    entity_name="sample",
                    frame=frame,
                    row_states=pd.Series(
                        [ChangeRowState.EXISTING_ENTITY, ChangeRowState.EXISTING_ENTITY], index=frame.index, name="_row_state"
                    ),
                    resolved_target_ids=pd.Series([101, 102], index=frame.index, dtype="Int64", name="_target_id"),
                )
            }
        )
        projection_result = TargetProjectionResult(tables={"sample": ProjectedTable(entity_name="sample", frame=frame.copy())})
        planned_tables = [
            PlannedTable(
                entity_name="sample",
                frame=frame,
                planned_actions=pd.Series(
                    [PlannedRowAction.REFERENCE_EXISTING, PlannedRowAction.UPDATE_EXISTING_CANDIDATE],
                    index=frame.index,
                    name="_planned_action",
                ),
            )
        ]

        package = build_change_request_package(projection_result, identity_result, planned_tables)

        assert package.tables["sample"].frame["sample_name"].tolist() == ["changed"]
        assert package.tables["sample"].planned_actions is not None
        assert package.tables["sample"].planned_actions.tolist() == [PlannedRowAction.UPDATE_EXISTING_CANDIDATE]

    def test_update_candidate_keeps_projected_conditional_foreign_key_value(self):
        """An accepted update candidate should carry its projected conditional FK value into the package."""
        frame = pd.DataFrame({"system_id": [10, 11], "location_id": [None, None], "location_type_id": [99, 1]})
        identity_result = IdentityResolutionResult(
            tables={
                "location": ResolvedIdentityTable(
                    entity_name="location",
                    frame=frame,
                    row_states=pd.Series(
                        [ChangeRowState.EXISTING_ENTITY, ChangeRowState.EXISTING_ENTITY], index=frame.index, name="_row_state"
                    ),
                    resolved_target_ids=pd.Series([501, 502], index=frame.index, dtype="Int64", name="_target_id"),
                ),
                "location_type": ResolvedIdentityTable(
                    entity_name="location_type",
                    frame=pd.DataFrame({"system_id": [1], "location_type_id": [None]}),
                    row_states=pd.Series([ChangeRowState.NEWLY_ALLOCATED_ENTITY], index=[0], name="_row_state"),
                    resolved_target_ids=pd.Series([901], index=[0], dtype="Int64", name="_target_id"),
                ),
            }
        )
        planned_tables = [
            PlannedTable(
                entity_name="location",
                frame=frame,
                planned_actions=pd.Series(
                    [PlannedRowAction.REFERENCE_EXISTING, PlannedRowAction.UPDATE_EXISTING_CANDIDATE],
                    index=frame.index,
                    name="_planned_action",
                ),
            )
        ]

        projection_result = project_target_ids(identity_result, conditional_location_target_model(), planned_tables)
        package = build_change_request_package(projection_result, identity_result, planned_tables)

        assert set(package.tables) == {"location"}
        assert package.tables["location"].frame["location_id"].tolist() == [502]
        assert package.tables["location"].frame["location_type_id"].tolist() == [901]
        assert package.tables["location"].planned_actions is not None
        assert package.tables["location"].planned_actions.tolist() == [PlannedRowAction.UPDATE_EXISTING_CANDIDATE]


class TestBuildStagingPackage:
    """Tests for the pre-projection staging package and its reference mappings."""

    def _staging_model(self) -> TargetModel:
        return TargetModel.model_validate(
            {
                "model": {"name": "SEAD Test Model", "version": "0.1.0"},
                "entities": {
                    "site": {"role": "lookup", "public_id": "site_id", "target_table": "tbl_sites"},
                    "dataset": {
                        "role": "lookup",
                        "identity_tracking": "tracked",
                        "reconciliation": "allocate",
                        "public_id": "dataset_id",
                        "target_table": "tbl_datasets",
                        "foreign_keys": [{"entity": "site", "required": True}],
                    },
                    "analysis_entity": {
                        "role": "fact",
                        "public_id": "analysis_entity_id",
                        "target_table": "tbl_analysis_entities",
                        "aggregate_parent": "dataset",
                        "foreign_keys": [{"entity": "dataset", "required": True}],
                    },
                },
                "constraints": [],
            }
        )

    def test_staging_rows_keep_local_keys_and_known_reference_mappings(self):
        """Staged rows keep local values while reference-only parents become mappings."""
        site_frame = pd.DataFrame({"system_id": [1], "site_id": [7001]})
        dataset_frame = pd.DataFrame({"system_id": [10], "dataset_id": [None], "site_id": [1]})
        analysis_frame = pd.DataFrame({"system_id": [100], "analysis_entity_id": [None], "dataset_id": [10]})
        identity_result = IdentityResolutionResult(
            tables={
                "site": ResolvedIdentityTable(
                    entity_name="site",
                    frame=site_frame,
                    row_states=pd.Series([ChangeRowState.EXISTING_ENTITY], index=site_frame.index),
                    resolved_target_ids=pd.Series([7001], index=site_frame.index, dtype="Int64"),
                ),
                "dataset": ResolvedIdentityTable(
                    entity_name="dataset",
                    frame=dataset_frame,
                    row_states=pd.Series([ChangeRowState.NEWLY_ALLOCATED_ENTITY], index=dataset_frame.index),
                    resolved_target_ids=pd.Series([900], index=dataset_frame.index, dtype="Int64"),
                ),
                "analysis_entity": ResolvedIdentityTable(
                    entity_name="analysis_entity",
                    frame=analysis_frame,
                    row_states=pd.Series([ChangeRowState.PENDING_DEPLOYMENT_ID], index=analysis_frame.index),
                    resolved_target_ids=pd.Series([pd.NA], index=analysis_frame.index, dtype="Int64"),
                ),
            }
        )
        planned_tables = [
            PlannedTable(
                entity_name=name,
                frame=identity_result.tables[name].frame,
                planned_actions=pd.Series([PlannedRowAction.DEFER_TO_DEPLOYMENT] * len(identity_result.tables[name].frame.index)),
            )
            for name in ("site", "dataset", "analysis_entity")
        ]

        package = build_staging_package(identity_result, planned_tables, self._staging_model(), "public")

        assert package.is_staging is True
        assert package.target_schema == "public"
        assert set(package.tables) == {"dataset", "analysis_entity"}
        assert package.tables["analysis_entity"].frame["dataset_id"].tolist() == [10]
        assert package.tables["analysis_entity"].frame["system_id"].tolist() == [100]
        assert {(mapping.entity_name, mapping.system_id, mapping.target_id) for mapping in package.known_id_mappings} == {
            ("site", 1, 7001),
            ("dataset", 10, 900),
        }

    def test_direct_package_has_no_staging_fields(self):
        """A direct package carries no target schema and no mappings."""
        frame = pd.DataFrame({"sample_taxon_id": [5001], "sample_id": [101], "taxon_id": [9001]})
        identity_result = IdentityResolutionResult(
            tables={
                "sample_taxon": ResolvedIdentityTable(
                    entity_name="sample_taxon",
                    frame=frame,
                    row_states=pd.Series([ChangeRowState.DERIVED_BRIDGE_ROW], index=frame.index),
                    resolved_target_ids=pd.Series([5001], index=frame.index, dtype="Int64"),
                )
            }
        )
        projection_result = TargetProjectionResult(tables={"sample_taxon": ProjectedTable(entity_name="sample_taxon", frame=frame.copy())})
        planned_tables = [
            PlannedTable(
                entity_name="sample_taxon",
                frame=frame,
                planned_actions=pd.Series([PlannedRowAction.EVALUATE_BRIDGE], index=frame.index),
            )
        ]

        package = build_change_request_package(projection_result, identity_result, planned_tables)

        assert package.is_staging is False
        assert not package.known_id_mappings
