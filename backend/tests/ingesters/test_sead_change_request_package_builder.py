"""Tests for SEAD change request in-memory package building."""

import pandas as pd

from ingesters.sead_change_request import ChangeRowState, build_change_request_package
from ingesters.sead_change_request.contracts import (
    IdentityResolutionResult,
    MaterializationResult,
    MaterializedTable,
    ResolvedIdentityTable,
)


class TestBuildChangeRequestPackage:
    """Tests for selecting insertable rows into the first in-memory package."""

    def test_includes_only_insertable_row_states(self):
        """Only newly allocated entities and derived bridge rows should enter the Delivery 1 package."""
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
        materialization_result = MaterializationResult(
            tables={
                "sample": MaterializedTable(entity_name="sample", frame=sample_frame.copy()),
                "sample_taxon": MaterializedTable(entity_name="sample_taxon", frame=bridge_frame.copy()),
            }
        )

        package = build_change_request_package(materialization_result, identity_result)

        assert set(package.tables) == {"sample", "sample_taxon"}
        assert package.tables["sample"].frame["sample_name"].tolist() == ["new"]
        assert package.tables["sample"].row_states.tolist() == [ChangeRowState.NEWLY_ALLOCATED_ENTITY]
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
        materialization_result = MaterializationResult(tables={"site": MaterializedTable(entity_name="site", frame=frame.copy())})

        package = build_change_request_package(materialization_result, identity_result)

        assert not package.tables
