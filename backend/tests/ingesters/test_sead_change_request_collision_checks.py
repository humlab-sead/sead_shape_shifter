"""Tests for SEAD change request target-side collision checks."""

import pandas as pd
import pytest

from ingesters.sead_change_request import ChangeRowState, check_materialized_collisions
from ingesters.sead_change_request.contracts import (
    IdentityResolutionResult,
    MaterializationResult,
    MaterializedTable,
    ResolvedIdentityTable,
)
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


class TestCheckMaterializedCollisions:
    """Tests for Delivery 1 target-side collision checks."""

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
        materialization_result = MaterializationResult(tables={"sample": MaterializedTable(entity_name="sample", frame=frame.copy())})

        result = await check_materialized_collisions(
            materialization_result,
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
        materialization_result = MaterializationResult(
            tables={"sample_taxon": MaterializedTable(entity_name="sample_taxon", frame=frame.copy())}
        )

        result = await check_materialized_collisions(
            materialization_result,
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
        materialization_result = MaterializationResult(
            tables={"sample_taxon": MaterializedTable(entity_name="sample_taxon", frame=frame.copy())}
        )

        result = await check_materialized_collisions(
            materialization_result,
            identity_result,
            minimal_target_model(sample_taxon={"role": "bridge"}),
            FakeCollisionChecker(),
        )

        assert result.has_conflicts is True
        assert result.diagnostics == ["Bridge entity 'sample_taxon' cannot run collision checks because unique_sets metadata is missing"]
