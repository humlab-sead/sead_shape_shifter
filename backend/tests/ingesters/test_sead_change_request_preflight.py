"""Tests for SIMS capability preflight."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pandas as pd
import pytest

from backend.app.models.sims import CapabilitiesResponse, EntityCapabilityResponse
from ingesters.sead_change_request.capability_preflight import preflight_capabilities
from ingesters.sead_change_request.contracts import PlannedRowAction, PlannedTable
from ingesters.sead_change_request.preparation import _run_capability_preflight
from src.target_model.models import TargetModel


def _model(**entities: dict) -> TargetModel:
    return TargetModel.model_validate(
        {
            "model": {"name": "SEAD Test Model", "version": "2.0.0"},
            "entities": entities,
            "constraints": [],
        }
    )


def _planned(*entity_names: str, action: PlannedRowAction = PlannedRowAction.ALLOCATE) -> list[PlannedTable]:
    tables: list[PlannedTable] = []
    for name in entity_names:
        frame = pd.DataFrame()
        actions = pd.Series([action], index=[0], dtype="object")
        tables.append(PlannedTable(entity_name=name, frame=frame, planned_actions=actions))
    return tables


def _capability(entity_type: str, *, bind_existing: bool, allocate_new: bool) -> EntityCapabilityResponse:
    return EntityCapabilityResponse(
        entity_type=entity_type,
        entity_subtype="shared_metadata",
        bind_existing=bind_existing,
        allocate_new=allocate_new,
        auto_confirm=True,
        accept_uuid=False,
    )


def _capabilities(*entities: EntityCapabilityResponse) -> CapabilitiesResponse:
    return CapabilitiesResponse(version="1.0", entities=list(entities))


class TestPreflightCapabilities:
    """Tests for capability comparison and fail-closed diagnostics."""

    def test_records_model_name_and_version(self):
        result = preflight_capabilities(
            _planned("site"),
            _model(site={"role": "lookup", "public_id": "site_id"}),
            _capabilities(_capability("site", bind_existing=True, allocate_new=True)),
        )

        assert result.model_name == "SEAD Test Model"
        assert result.model_version == "2.0.0"
        assert not result.has_blockers

    def test_tracked_entity_requires_allocate_new(self):
        result = preflight_capabilities(
            _planned("sample"),
            _model(sample={"role": "fact", "public_id": "sample_id", "identity_tracking": "tracked", "reconciliation": "allocate"}),
            _capabilities(_capability("sample", bind_existing=False, allocate_new=False)),
        )

        assert result.has_blockers
        assert "Operation 'allocate_new' is not supported for entity type 'sample'" in result.diagnostics

    def test_tracked_entity_with_allocate_new_passes(self):
        result = preflight_capabilities(
            _planned("sample"),
            _model(sample={"role": "fact", "public_id": "sample_id", "identity_tracking": "tracked", "reconciliation": "allocate"}),
            _capabilities(_capability("sample", bind_existing=False, allocate_new=True)),
        )

        assert not result.has_blockers

    def test_lookup_only_approved_row_does_not_require_allocation(self):
        result = preflight_capabilities(
            _planned("taxa_tree_master", action=PlannedRowAction.BLOCK_RECONCILIATION),
            _model(
                taxa_tree_master={
                    "role": "classifier",
                    "public_id": "taxa_tree_master_id",
                    "identity_tracking": "reconciled",
                    "reconciliation": "lookup-only",
                }
            ),
            _capabilities(_capability("taxa_tree_master", bind_existing=True, allocate_new=False)),
        )

        assert not result.has_blockers
        assert not result.diagnostics

    def test_allocate_row_requires_allocate_new(self):
        result = preflight_capabilities(
            _planned("site"),
            _model(site={"role": "lookup", "public_id": "site_id"}),
            _capabilities(_capability("site", bind_existing=True, allocate_new=False)),
        )

        assert result.has_blockers
        assert "Operation 'allocate_new' is not supported for entity type 'site'" in result.diagnostics

    @pytest.mark.asyncio
    @pytest.mark.parametrize("bind_existing", [False, True])
    async def test_verified_existing_link_checks_bind_existing_capability(self, bind_existing: bool):
        planned = _planned("site", action=PlannedRowAction.REFERENCE_EXISTING)
        capabilities = _capabilities(_capability("site", bind_existing=bind_existing, allocate_new=False))
        sims_client = SimpleNamespace(get_capabilities=AsyncMock(return_value=capabilities))

        result = await _run_capability_preflight(
            planned,
            _model(site={"role": "lookup", "public_id": "site_id"}),
            sims_client,
            approved_existing_target_ids={"site": {0: 101}},
        )

        assert result is not None
        assert result.has_blockers is (not bind_existing)
        assert ("Operation 'bind_existing' is not supported for entity type 'site'" in result.diagnostics) is (not bind_existing)
        sims_client.get_capabilities.assert_awaited_once()

    def test_existing_row_without_verified_link_does_not_require_binding(self):
        result = preflight_capabilities(
            _planned("site", action=PlannedRowAction.REFERENCE_EXISTING),
            _model(site={"role": "lookup", "public_id": "site_id"}),
            _capabilities(_capability("site", bind_existing=False, allocate_new=False)),
        )

        assert not result.has_blockers
        assert not result.diagnostics

    def test_unlisted_entity_is_unsupported(self):
        result = preflight_capabilities(
            _planned("sample"),
            _model(sample={"role": "fact", "public_id": "sample_id", "identity_tracking": "tracked", "reconciliation": "allocate"}),
            _capabilities(),
        )

        assert result.has_blockers
        assert "Entity 'sample' is not configured in SIMS capabilities" in result.diagnostics

    def test_child_and_derived_entities_require_no_sims_operation(self):
        result = preflight_capabilities(
            _planned("sample_dimension", "sample_taxon"),
            _model(
                sample_dimension={"role": "fact", "public_id": "sample_dimension_id", "aggregate_parent": "sample"},
                sample_taxon={"role": "bridge", "unique_sets": [["sample_id", "taxon_id"]]},
            ),
            _capabilities(),
        )

        assert not result.has_blockers
        assert result.checked_entities == ["sample_dimension", "sample_taxon"]

    def test_unapproved_reconciled_row_does_not_request_capabilities(self):
        result = preflight_capabilities(
            _planned("taxa_tree_master", action=PlannedRowAction.BLOCK_RECONCILIATION),
            _model(
                taxa_tree_master={
                    "role": "classifier",
                    "public_id": "taxa_tree_master_id",
                    "identity_tracking": "reconciled",
                    "reconciliation": "lookup-only",
                }
            ),
            _capabilities(_capability("taxa_tree_master", bind_existing=False, allocate_new=False)),
        )

        assert not result.has_blockers
        assert not result.diagnostics

    @pytest.mark.parametrize(
        "entity_spec",
        [
            {"role": "fact", "public_id": "sample_id"},
            {"role": "lookup", "public_id": "site_id"},
            {"role": "classifier", "public_id": "class_id"},
            {"role": "bridge", "unique_sets": [["a", "b"]]},
            {"role": "fact", "public_id": "child_id", "aggregate_parent": "sample"},
        ],
    )
    def test_version_mismatch_is_not_a_failure(self, entity_spec):
        # A different model version must not itself block preflight.
        result = preflight_capabilities(
            _planned("site"),
            _model(site=entity_spec),
            _capabilities(_capability("site", bind_existing=True, allocate_new=True)),
        )

        assert result.model_version == "2.0.0"
        # Blocking is driven by capability support, never by version equality.
        assert "version" not in " ".join(result.diagnostics)
