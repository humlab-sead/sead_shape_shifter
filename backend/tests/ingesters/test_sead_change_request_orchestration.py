"""Tests for SEAD change request client orchestration."""

import pandas as pd
import pytest

from ingesters.sead_change_request import ChangeRowState, SubmissionContext, orchestrate_identity_assignments, plan_table
from ingesters.sead_change_request.contracts import PlannedRowAction, PlannedTable
from ingesters.sead_change_request.orchestration import SIMS_AGGREGATE_ID_CAPABILITY_NOTE
from src.target_model.models import EntitySpec

# pylint: disable=unused-argument


class FakeReconciliationClient:
    """Simple fake reconciliation client for ingester tests."""

    def __init__(self, target_id: int | None) -> None:
        self.target_id = target_id

    async def reconcile_entity(self, entity_name: str, row: dict) -> int | None:
        return self.target_id


class FakeTargetIdAllocator:
    """Return a target sequence value and record the target column requested."""

    def __init__(self, target_id: int | None) -> None:
        self.target_id = target_id
        self.requests: list[tuple[str, str]] = []

    async def reserve_target_id(self, table_name: str, public_id_column: str) -> int | None:
        self.requests.append((table_name, public_id_column))
        return self.target_id


class FakeSimsClient:
    """Simple fake SIMS client for ingester tests."""

    def __init__(
        self,
        *,
        binding_set_uuid: str = "binding-123",
        binding_set_state: str = "confirmed",
        confirmed_binding_set_state: str | None = None,
        target_id: int | None = 501,
    ) -> None:
        self.binding_set_uuid = binding_set_uuid
        self.binding_set_state = binding_set_state
        self.confirmed_binding_set_state = confirmed_binding_set_state or binding_set_state
        self.target_id = target_id
        self.approved_aggregate_ids: list[int] = []
        self.allocated_entities: list[str] = []

    async def allocate_entity(self, entity_name: str, row: dict, submission_context: SubmissionContext) -> dict:
        self.allocated_entities.append(entity_name)
        return {
            "target_id": self.target_id,
            "binding_set_uuid": self.binding_set_uuid,
            "binding_set_state": self.binding_set_state,
            "note": f"Allocated {entity_name}",
        }

    async def bind_existing_entity(
        self,
        entity_name: str,
        row: dict,
        approved_aggregate_id: int,
        submission_context: SubmissionContext,
    ) -> dict:
        self.approved_aggregate_ids.append(approved_aggregate_id)
        return {
            "target_id": approved_aggregate_id,
            "binding_set_uuid": self.binding_set_uuid,
            "binding_set_state": self.binding_set_state,
            "note": f"Bound {entity_name} to approved aggregate ID {approved_aggregate_id}",
        }

    async def derive_bridge_row(self, entity_name: str, row: dict, submission_context: SubmissionContext) -> dict:
        return {
            "state": ChangeRowState.DERIVED_BRIDGE_ROW.value,
            "target_id": None,
            "binding_set_uuid": self.binding_set_uuid,
            "binding_set_state": self.binding_set_state,
            "note": f"Derived {entity_name}",
        }

    async def get_binding_set_state(self, binding_set_uuid: str) -> str:
        return self.binding_set_state

    async def confirm_binding_set(self, binding_set_uuid: str) -> str:
        self.binding_set_state = self.confirmed_binding_set_state
        return self.binding_set_state

    async def associate_change_request(self, binding_set_uuid: str, change_request_name: str) -> None:
        return None


def minimal_submission_context() -> SubmissionContext:
    return SubmissionContext(
        submission_name="test-submission",
        project_name="test-project",
        timestamp=pd.Timestamp("2026-05-23T23:10:00").to_pydatetime(),
    )


class TestOrchestrateIdentityAssignments:
    """Tests for the thin client orchestration layer."""

    @pytest.mark.asyncio
    async def test_reconciliation_match_creates_reconciled_assignment(self):
        frame = pd.DataFrame({"class_id": [None], "name": ["A"]})
        planned_table = plan_table("abundance_class", frame, EntitySpec(role="classifier", public_id="class_id"))

        result = await orchestrate_identity_assignments(
            [planned_table],
            minimal_submission_context(),
            reconciliation_client=FakeReconciliationClient(target_id=77),
        )

        assignment = result.assignments["abundance_class"][0]
        assert assignment.state == ChangeRowState.RECONCILED_CLASSIFIER
        assert assignment.target_id == 77

    @pytest.mark.asyncio
    async def test_reconciliation_match_binds_approved_aggregate_id_with_sims(self):
        frame = pd.DataFrame({"site_name": ["A"]})
        planned_table = PlannedTable(
            entity_name="site",
            frame=frame,
            planned_actions=pd.Series([PlannedRowAction.RECONCILE], index=frame.index, name="_planned_action"),
        )
        sims_client = FakeSimsClient()

        result = await orchestrate_identity_assignments(
            [planned_table],
            minimal_submission_context(),
            sims_client=sims_client,
            reconciliation_client=FakeReconciliationClient(target_id=77),
        )

        assignment = result.assignments["site"][0]
        assert sims_client.approved_aggregate_ids == [77]
        assert assignment.state == ChangeRowState.RECONCILED_CLASSIFIER
        assert assignment.target_id == 77
        assert result.binding_set_uuid == "binding-123"
        assert result.binding_set_state == "confirmed"

    @pytest.mark.asyncio
    async def test_sims_allocation_creates_allocated_assignment(self):
        frame = pd.DataFrame({"sample_id": [None]})
        planned_table = plan_table("sample", frame, EntitySpec(role="fact", public_id="sample_id"))

        result = await orchestrate_identity_assignments(
            [planned_table],
            minimal_submission_context(),
            sims_client=FakeSimsClient(binding_set_state="confirmed", target_id=501),
        )

        assignment = result.assignments["sample"][0]
        assert assignment.state == ChangeRowState.NEWLY_ALLOCATED_ENTITY
        assert assignment.target_id == 501
        assert result.binding_set_uuid == "binding-123"
        assert result.binding_set_state == "confirmed"

    @pytest.mark.asyncio
    async def test_tracked_submission_id_is_allocated_by_sims(self):
        frame = pd.DataFrame({"submission_id": [None], "submission_uuid": ["submission-uuid"]})
        entity_spec = EntitySpec(
            role="fact",
            public_id="submission_id",
            identity_tracking="tracked",
            reconciliation="allocate",
        )
        planned_table = plan_table("submission", frame, entity_spec)
        target_id_allocator = FakeTargetIdAllocator(702)
        sims_client = FakeSimsClient(target_id=703)

        result = await orchestrate_identity_assignments(
            [planned_table],
            minimal_submission_context(),
            sims_client=sims_client,
            target_id_allocator=target_id_allocator,
            target_model_entities={"submission": entity_spec},
        )

        assignment = result.assignments["submission"][0]
        assert assignment.state == ChangeRowState.NEWLY_ALLOCATED_ENTITY
        assert assignment.target_id == 703
        assert sims_client.allocated_entities == ["submission"]
        assert target_id_allocator.requests == []

    @pytest.mark.asyncio
    async def test_explicitly_non_tracked_database_sequence_does_not_call_sims(self):
        frame = pd.DataFrame({"submission_id": [None], "submission_name": ["Submission A"]})
        entity_spec = EntitySpec(
            role="fact",
            public_id="submission_id",
            public_id_generation="database_sequence",
            target_table="tbl_submissions",
            identity_tracking="derived",
            reconciliation="derive",
        )
        planned_table = plan_table("submission", frame, entity_spec)
        target_id_allocator = FakeTargetIdAllocator(702)
        sims_client = FakeSimsClient()

        result = await orchestrate_identity_assignments(
            [planned_table],
            minimal_submission_context(),
            sims_client=sims_client,
            target_id_allocator=target_id_allocator,
            target_model_entities={"submission": entity_spec},
        )

        assignment = result.assignments["submission"][0]
        assert assignment.state == ChangeRowState.NEWLY_ALLOCATED_ENTITY
        assert assignment.target_id == 702
        assert "database sequence" in (assignment.note or "")
        assert target_id_allocator.requests == [("tbl_submissions", "submission_id")]
        assert not sims_client.allocated_entities

    @pytest.mark.asyncio
    async def test_database_sequence_reservation_blocks_when_target_sequence_is_missing(self):
        frame = pd.DataFrame({"submission_id": [None]})
        entity_spec = EntitySpec(
            role="fact",
            public_id="submission_id",
            public_id_generation="database_sequence",
            target_table="tbl_submissions",
            identity_tracking="derived",
            reconciliation="derive",
        )
        planned_table = plan_table("submission", frame, entity_spec)

        result = await orchestrate_identity_assignments(
            [planned_table],
            minimal_submission_context(),
            target_id_allocator=FakeTargetIdAllocator(None),
            target_model_entities={"submission": entity_spec},
        )

        assignment = result.assignments["submission"][0]
        assert assignment.state == ChangeRowState.BLOCKED_UNRESOLVED
        assert "No database sequence is associated" in (assignment.note or "")

    @pytest.mark.asyncio
    async def test_database_sequence_reservation_blocks_when_allocator_is_not_configured(self):
        frame = pd.DataFrame({"submission_id": [None]})
        entity_spec = EntitySpec(
            role="fact",
            public_id="submission_id",
            public_id_generation="database_sequence",
            target_table="tbl_submissions",
            identity_tracking="derived",
            reconciliation="derive",
        )
        planned_table = plan_table("submission", frame, entity_spec)

        result = await orchestrate_identity_assignments(
            [planned_table],
            minimal_submission_context(),
            target_model_entities={"submission": entity_spec},
        )

        assignment = result.assignments["submission"][0]
        assert assignment.state == ChangeRowState.BLOCKED_UNRESOLVED
        assert "reservation is not configured" in (assignment.note or "")

    @pytest.mark.asyncio
    async def test_proposed_binding_set_blocks_sims_rows(self):
        frame = pd.DataFrame({"sample_id": [None]})
        planned_table = plan_table("sample", frame, EntitySpec(role="fact", public_id="sample_id"))

        result = await orchestrate_identity_assignments(
            [planned_table],
            minimal_submission_context(),
            sims_client=FakeSimsClient(binding_set_state="proposed", confirmed_binding_set_state="proposed", target_id=501),
        )

        assignment = result.assignments["sample"][0]
        assert assignment.state == ChangeRowState.BLOCKED_UNRESOLVED
        assert "must be confirmed" in (assignment.note or "")
        assert result.binding_set_state == "proposed"

    @pytest.mark.asyncio
    async def test_proposed_binding_set_is_confirmed_when_sims_supports_confirmation(self):
        frame = pd.DataFrame({"sample_id": [None]})
        planned_table = plan_table("sample", frame, EntitySpec(role="fact", public_id="sample_id"))

        result = await orchestrate_identity_assignments(
            [planned_table],
            minimal_submission_context(),
            sims_client=FakeSimsClient(binding_set_state="proposed", confirmed_binding_set_state="confirmed", target_id=501),
        )

        assignment = result.assignments["sample"][0]
        assert assignment.state == ChangeRowState.NEWLY_ALLOCATED_ENTITY
        assert result.binding_set_state == "confirmed"

    @pytest.mark.asyncio
    async def test_missing_target_id_blocks_sims_rows(self):
        frame = pd.DataFrame({"sample_id": [None]})
        planned_table = plan_table("sample", frame, EntitySpec(role="fact", public_id="sample_id"))

        result = await orchestrate_identity_assignments(
            [planned_table],
            minimal_submission_context(),
            sims_client=FakeSimsClient(binding_set_state="confirmed", target_id=None),
        )

        assignment = result.assignments["sample"][0]
        assert assignment.state == ChangeRowState.BLOCKED_UNRESOLVED
        assert SIMS_AGGREGATE_ID_CAPABILITY_NOTE in (assignment.note or "")

    @pytest.mark.asyncio
    async def test_bridge_rows_can_be_derived_without_target_id(self):
        frame = pd.DataFrame({"sample_id": [2], "taxon_id": [11], "abundance": [3]})
        planned_table = plan_table(
            "sample_taxon",
            frame,
            EntitySpec(role="bridge", unique_sets=[["sample_id", "taxon_id"]]),
        )

        result = await orchestrate_identity_assignments(
            [planned_table],
            minimal_submission_context(),
            sims_client=FakeSimsClient(binding_set_state="confirmed", target_id=501),
        )

        assignment = result.assignments["sample_taxon"][0]
        assert assignment.state == ChangeRowState.DERIVED_BRIDGE_ROW
        assert assignment.target_id is None
        assert assignment.note == "Derived sample_taxon"

    @pytest.mark.asyncio
    async def test_block_existing_update_action_creates_blocked_assignment(self):
        frame = pd.DataFrame({"sample_id": [101], "sample_name": ["A changed"]})
        planned_table = PlannedTable(
            entity_name="sample",
            frame=frame,
            planned_actions=pd.Series([PlannedRowAction.BLOCK_EXISTING_UPDATE], index=frame.index, name="_planned_action"),
        )

        result = await orchestrate_identity_assignments([planned_table], minimal_submission_context())

        assignment = result.assignments["sample"][0]
        assert assignment.state == ChangeRowState.BLOCKED_UNRESOLVED
        assert "blocked until mutable-field boundaries are complete" in (assignment.note or "")
