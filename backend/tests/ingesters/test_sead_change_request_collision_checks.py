"""Tests for SEAD change request target-side collision checks."""

import pandas as pd
import pytest

from ingesters.sead_change_request import ChangeRowState, check_projected_collisions
from ingesters.sead_change_request.contracts import (
    IdentityResolutionResult,
    ProjectedTable,
    ResolvedIdentityTable,
    TargetProjectionResult,
)
from ingesters.sead_change_request.staging_eligibility import PendingDeploymentMap
from src.target_model.models import TargetModel


def minimal_target_model(**extra_entities: dict) -> TargetModel:
    return TargetModel.model_validate(
        {
            "model": {"name": "SEAD Test Model", "version": "0.1.0"},
            "entities": extra_entities,
            "constraints": [],
        }
    )


class FakeCollisionChecker:
    """Minimal async collision checker for pure ingester tests."""

    def __init__(
        self, *, target_ids: set[tuple[str, str, int]] | None = None, rows: set[tuple[str, tuple[tuple[str, object], ...]]] | None = None
    ) -> None:
        self.target_ids = target_ids or set()
        self.rows = rows or set()

    async def target_id_exists(self, table_name: str, public_id_column: str, target_id: int) -> bool:
        return (table_name, public_id_column, target_id) in self.target_ids

    async def row_exists(self, table_name: str, filters: dict[str, object]) -> bool:
        return (table_name, tuple(sorted(filters.items()))) in self.rows


class TestCheckProjectedCollisions:
    """Tests for MVP Delivery target-side collision checks."""

    @pytest.mark.asyncio
    async def test_reports_entity_target_id_collision(self):
        frame = pd.DataFrame({"system_id": [1], "sample_id": [501], "sample_name": ["A"]})
        identity_result = IdentityResolutionResult(
            tables={
                "sample": ResolvedIdentityTable(
                    entity_name="sample",
                    frame=frame.copy(),
                    row_states=pd.Series([ChangeRowState.NEWLY_ALLOCATED_ENTITY], index=frame.index, name="_row_state"),
                    resolved_target_ids=pd.Series([501], index=frame.index, dtype="Int64", name="_target_id"),
                )
            }
        )
        projection_result = TargetProjectionResult(tables={"sample": ProjectedTable(entity_name="sample", frame=frame.copy())})

        result = await check_projected_collisions(
            projection_result,
            identity_result,
            minimal_target_model(sample={"role": "fact", "public_id": "sample_id", "target_table": "tbl_sample"}),
            FakeCollisionChecker(target_ids={("tbl_sample", "sample_id", 501)}),
        )

        assert result.has_conflicts is True
        assert result.diagnostics == ["Entity 'sample' row '0' collides with existing target ID 501 in 'tbl_sample.sample_id'"]

    @pytest.mark.asyncio
    async def test_reports_bridge_unique_set_collision(self):
        frame = pd.DataFrame({"sample_taxon_id": [5001], "sample_id": [101], "taxon_id": [9001]})
        identity_result = IdentityResolutionResult(
            tables={
                "sample_taxon": ResolvedIdentityTable(
                    entity_name="sample_taxon",
                    frame=frame.copy(),
                    row_states=pd.Series([ChangeRowState.DERIVED_BRIDGE_ROW], index=frame.index, name="_row_state"),
                    resolved_target_ids=pd.Series([5001], index=frame.index, dtype="Int64", name="_target_id"),
                )
            }
        )
        projection_result = TargetProjectionResult(tables={"sample_taxon": ProjectedTable(entity_name="sample_taxon", frame=frame.copy())})

        result = await check_projected_collisions(
            projection_result,
            identity_result,
            minimal_target_model(sample_taxon={"role": "bridge", "unique_sets": [["sample_id", "taxon_id"]]}),
            FakeCollisionChecker(rows={("sample_taxon", (("sample_id", 101), ("taxon_id", 9001)))}),
        )

        assert result.has_conflicts is True
        assert result.diagnostics == [
            "Bridge entity 'sample_taxon' row '0' collides with an existing "
            "target row in 'sample_taxon' on unique_set ['sample_id', 'taxon_id']"
        ]

    @pytest.mark.asyncio
    async def test_reports_missing_bridge_uniqueness_metadata(self):
        frame = pd.DataFrame({"sample_taxon_id": [5001], "sample_id": [101], "taxon_id": [9001]})
        identity_result = IdentityResolutionResult(
            tables={
                "sample_taxon": ResolvedIdentityTable(
                    entity_name="sample_taxon",
                    frame=frame.copy(),
                    row_states=pd.Series([ChangeRowState.DERIVED_BRIDGE_ROW], index=frame.index, name="_row_state"),
                    resolved_target_ids=pd.Series([5001], index=frame.index, dtype="Int64", name="_target_id"),
                )
            }
        )
        projection_result = TargetProjectionResult(tables={"sample_taxon": ProjectedTable(entity_name="sample_taxon", frame=frame.copy())})

        result = await check_projected_collisions(
            projection_result,
            identity_result,
            minimal_target_model(sample_taxon={"role": "bridge"}),
            FakeCollisionChecker(),
        )

        assert result.has_conflicts is True
        assert result.diagnostics == ["Bridge entity 'sample_taxon' cannot run collision checks because unique_sets metadata is missing"]

    @pytest.mark.asyncio
    async def test_tracked_allocated_bridge_checks_its_public_id(self):
        frame = pd.DataFrame({"analysis_entity_id": [223430], "physical_sample_id": [63876], "dataset_id": [91925]})
        identity_result = IdentityResolutionResult(
            tables={
                "analysis_entity": ResolvedIdentityTable(
                    entity_name="analysis_entity",
                    frame=frame.copy(),
                    row_states=pd.Series([ChangeRowState.NEWLY_ALLOCATED_ENTITY], index=frame.index, name="_row_state"),
                    resolved_target_ids=pd.Series([223430], index=frame.index, dtype="Int64", name="_target_id"),
                )
            }
        )
        projection_result = TargetProjectionResult(
            tables={"analysis_entity": ProjectedTable(entity_name="analysis_entity", frame=frame.copy())}
        )

        result = await check_projected_collisions(
            projection_result,
            identity_result,
            minimal_target_model(
                analysis_entity={
                    "role": "bridge",
                    "identity_tracking": "tracked",
                    "reconciliation": "allocate",
                    "public_id": "analysis_entity_id",
                    "target_table": "tbl_analysis_entities",
                }
            ),
            FakeCollisionChecker(target_ids={("tbl_analysis_entities", "analysis_entity_id", 223430)}),
        )

        assert result.has_conflicts is True
        assert result.diagnostics == [
            "Entity 'analysis_entity' row '0' collides with existing target ID 223430 in 'tbl_analysis_entities.analysis_entity_id'"
        ]


class TestPendingDeploymentCollisions:
    """Collision checks defer values that only exist after deployment."""

    @pytest.mark.asyncio
    async def test_pending_rows_are_deferred(self):
        """A row with a pending target ID is not checked for an ID collision."""
        frame = pd.DataFrame({"system_id": [1], "analysis_entity_id": [None]})
        identity_result = IdentityResolutionResult(
            tables={
                "analysis_entity": ResolvedIdentityTable(
                    entity_name="analysis_entity",
                    frame=frame.copy(),
                    row_states=pd.Series([ChangeRowState.PENDING_DEPLOYMENT_ID], index=frame.index),
                    resolved_target_ids=pd.Series([pd.NA], index=frame.index, dtype="Int64"),
                )
            }
        )
        projection_result = TargetProjectionResult(
            tables={"analysis_entity": ProjectedTable(entity_name="analysis_entity", frame=frame.copy())}
        )
        pending = PendingDeploymentMap(pending_row_mask={"analysis_entity": pd.Series([True], index=frame.index)})

        result = await check_projected_collisions(
            projection_result,
            identity_result,
            minimal_target_model(
                analysis_entity={"role": "fact", "public_id": "analysis_entity_id", "target_table": "tbl_analysis_entities"}
            ),
            FakeCollisionChecker(),
            pending=pending,
        )

        assert result.has_conflicts is False

    @pytest.mark.asyncio
    async def test_bridge_set_with_a_pending_foreign_key_is_deferred(self):
        """An incomplete set caused only by a pending foreign key waits for deployment."""
        frame = pd.DataFrame({"system_id": [1], "abundance_id": [None], "identification_level_id": [9]})
        identity_result = IdentityResolutionResult(
            tables={
                "abundance_ident_level": ResolvedIdentityTable(
                    entity_name="abundance_ident_level",
                    frame=frame.copy(),
                    row_states=pd.Series([ChangeRowState.DERIVED_BRIDGE_ROW], index=frame.index),
                    resolved_target_ids=pd.Series([pd.NA], index=frame.index, dtype="Int64"),
                )
            }
        )
        projection_result = TargetProjectionResult(
            tables={"abundance_ident_level": ProjectedTable(entity_name="abundance_ident_level", frame=frame.copy())}
        )
        pending = PendingDeploymentMap(
            pending_fk_mask={"abundance_ident_level": {"abundance_id": pd.Series([True], index=frame.index)}}
        )

        result = await check_projected_collisions(
            projection_result,
            identity_result,
            minimal_target_model(
                abundance_ident_level={
                    "role": "bridge",
                    "public_id": "abundance_ident_level_id",
                    "target_table": "tbl_abundance_ident_levels",
                    "unique_sets": [["abundance_id", "identification_level_id"]],
                }
            ),
            FakeCollisionChecker(),
            pending=pending,
        )

        assert result.has_conflicts is False

    @pytest.mark.asyncio
    async def test_missing_unique_sets_metadata_is_still_reported(self):
        """Deferral does not hide a missing unique_sets declaration."""
        frame = pd.DataFrame({"system_id": [1], "abundance_id": [None], "identification_level_id": [9]})
        identity_result = IdentityResolutionResult(
            tables={
                "abundance_ident_level": ResolvedIdentityTable(
                    entity_name="abundance_ident_level",
                    frame=frame.copy(),
                    row_states=pd.Series([ChangeRowState.DERIVED_BRIDGE_ROW], index=frame.index),
                    resolved_target_ids=pd.Series([pd.NA], index=frame.index, dtype="Int64"),
                )
            }
        )
        projection_result = TargetProjectionResult(
            tables={"abundance_ident_level": ProjectedTable(entity_name="abundance_ident_level", frame=frame.copy())}
        )

        result = await check_projected_collisions(
            projection_result,
            identity_result,
            minimal_target_model(
                abundance_ident_level={
                    "role": "bridge",
                    "public_id": "abundance_ident_level_id",
                    "target_table": "tbl_abundance_ident_levels",
                }
            ),
            FakeCollisionChecker(),
            pending=PendingDeploymentMap(),
        )

        assert result.diagnostics == [
            "Bridge entity 'abundance_ident_level' cannot run collision checks because unique_sets metadata is missing"
        ]
