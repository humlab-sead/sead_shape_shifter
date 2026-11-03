"""Tests for SEAD change request client orchestration."""

import pandas as pd
import pytest

from ingesters.sead_change_request import ChangeRowState, SubmissionContext, orchestrate_identity_assignments, plan_table
from ingesters.sead_change_request.contracts import (
    DatabaseSequenceReservationError,
    PlannedRowAction,
    PlannedTable,
    SimsResolveItem,
)
from ingesters.sead_change_request.orchestration import SIMS_AGGREGATE_ID_CAPABILITY_NOTE
from src.reconciliation.mapping_model import encode_local_key
from src.target_model.models import EntitySpec

# pylint: disable=unused-argument


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
        self.batch_calls: list[list[SimsResolveItem]] = []
        self.confirm_calls: list[str] = []
        self.events: list[str] = []

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

    async def resolve_batch(self, items: list[SimsResolveItem], submission_context: SubmissionContext) -> dict:
        self.events.append("sims")
        self.batch_calls.append(list(items))
        outcomes = []
        for item in items:
            if item.approved_aggregate_id is not None:
                self.approved_aggregate_ids.append(item.approved_aggregate_id)
                outcomes.append({"target_id": item.approved_aggregate_id, "tracked_identity_uuid": None})
            else:
                self.allocated_entities.append(item.entity_name)
                outcomes.append({"target_id": self.target_id, "tracked_identity_uuid": None})
        return {
            "outcomes": outcomes,
            "binding_set_uuid": self.binding_set_uuid,
            "binding_set_state": self.binding_set_state,
        }

    async def confirm_binding_set(self, binding_set_uuid: str) -> str:
        self.confirm_calls.append(binding_set_uuid)
        self.binding_set_state = self.confirmed_binding_set_state
        return self.binding_set_state

    async def associate_change_request(self, binding_set_uuid: str, change_request_name: str) -> None:
        return None


class FakeDatabaseSequenceReserver:
    """Reserve fake target IDs and record reservation order."""

    def __init__(
        self,
        events: list[str],
        *,
        target_id: int = 9001,
        error: DatabaseSequenceReservationError | None = None,
    ) -> None:
        self.events = events
        self.target_id = target_id
        self.error = error
        self.calls: list[tuple[str, str]] = []

    async def reserve_database_id(self, table_name: str, public_id_column: str) -> int:
        self.events.append("sequence")
        self.calls.append((table_name, public_id_column))
        if self.error is not None:
            raise self.error
        return self.target_id


def minimal_submission_context() -> SubmissionContext:
    return SubmissionContext(
        submission_name="test-submission",
        project_name="test-project",
        timestamp=pd.Timestamp("2026-05-23T23:10:00").to_pydatetime(),
    )


class TestOrchestrateIdentityAssignments:
    """Tests for the thin client orchestration layer."""

    @pytest.mark.asyncio
    async def test_unapproved_reconciled_row_blocks_without_sims_work(self):
        frame = pd.DataFrame({"class_id": [None], "name": ["A"]})
        planned_table = plan_table("abundance_class", frame, EntitySpec(role="classifier", public_id="class_id"))
        sims_client = FakeSimsClient()

        result = await orchestrate_identity_assignments(
            [planned_table],
            minimal_submission_context(),
            sims_client=sims_client,  # type: ignore
        )

        assignment = result.assignments["abundance_class"][0]
        assert assignment.state == ChangeRowState.BLOCKED_UNRESOLVED
        assert "No exported local-only approval" in (assignment.note or "")
        assert not sims_client.batch_calls

    @pytest.mark.asyncio
    async def test_approved_reconciled_row_uses_new_allocation_without_candidate_binding(self):
        frame = pd.DataFrame({"site_id": [None], "site_name": ["A"]})
        entity_spec = EntitySpec(
            role="lookup",
            public_id="site_id",
            identity_tracking="reconciled",
            reconciliation="reconcile-exact",
        )
        planned_table = plan_table(
            "site",
            frame,
            entity_spec,
            local_key_columns=("site_name",),
            approved_local_only_keys={encode_local_key("site_name", "A")},
        )
        sims_client = FakeSimsClient()

        result = await orchestrate_identity_assignments(
            [planned_table],
            minimal_submission_context(),
            sims_client=sims_client,  # type: ignore
        )

        assignment = result.assignments["site"][0]
        assert not sims_client.approved_aggregate_ids
        assert assignment.state == ChangeRowState.NEWLY_ALLOCATED_ENTITY
        assert assignment.target_id == 501
        assert sims_client.allocated_entities == ["site"]
        assert result.binding_set_uuid == "binding-123"
        assert result.binding_set_state == "confirmed"

    @pytest.mark.asyncio
    async def test_verified_existing_reconciliation_link_is_bound_to_approved_id(self):
        frame = pd.DataFrame({"site_id": [501], "national_site_identifier": ["accepted"]})
        entity_spec = EntitySpec(
            role="lookup",
            public_id="site_id",
            identity_tracking="reconciled",
            reconciliation="reconcile-exact",
        )
        planned_table = plan_table("site", frame, entity_spec)
        sims_client = FakeSimsClient(target_id=999)

        result = await orchestrate_identity_assignments(
            [planned_table],
            minimal_submission_context(),
            sims_client=sims_client,  # type: ignore
            target_model_entities={"site": entity_spec},
            approved_existing_target_ids={"site": {0: 501}},
        )

        assignment = result.assignments["site"][0]
        assert sims_client.approved_aggregate_ids == [501]
        assert sims_client.batch_calls[0][0].approved_aggregate_id == 501
        assert assignment.state == ChangeRowState.RECONCILED_CLASSIFIER
        assert assignment.target_id == 501

    @pytest.mark.asyncio
    async def test_sims_allocation_creates_allocated_assignment(self):
        frame = pd.DataFrame({"sample_id": [None]})
        planned_table = plan_table("sample", frame, EntitySpec(role="fact", public_id="sample_id"))

        result = await orchestrate_identity_assignments(
            [planned_table],
            minimal_submission_context(),
            sims_client=FakeSimsClient(binding_set_state="confirmed", target_id=501),  # type: ignore
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
        sims_client = FakeSimsClient(target_id=703)

        result = await orchestrate_identity_assignments(
            [planned_table],
            minimal_submission_context(),
            sims_client=sims_client,  # type: ignore
            target_model_entities={"submission": entity_spec},
        )

        assignment = result.assignments["submission"][0]
        assert assignment.state == ChangeRowState.NEWLY_ALLOCATED_ENTITY
        assert assignment.target_id == 703
        assert sims_client.allocated_entities == ["submission"]

    @pytest.mark.asyncio
    async def test_unresolved_database_sequence_id_is_blocked_without_sims_allocation(self):
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
        sims_client = FakeSimsClient()

        result = await orchestrate_identity_assignments(
            [planned_table],
            minimal_submission_context(),
            sims_client=sims_client,  # type: ignore
            target_model_entities={"submission": entity_spec},
        )

        assignment = result.assignments["submission"][0]
        assert assignment.state == ChangeRowState.BLOCKED_UNRESOLVED
        assert "database sequence reservation is unavailable" in (assignment.note or "")
        assert not sims_client.allocated_entities

    @pytest.mark.asyncio
    async def test_unresolved_database_sequence_id_is_blocked_even_with_valid_target_metadata(self):
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
        assert "database sequence reservation is unavailable" in (assignment.note or "")

    @pytest.mark.asyncio
    async def test_database_sequence_ids_are_reserved_before_sims_allocation(self):
        site_frame = pd.DataFrame({"site_id": [None], "national_site_identifier": ["new-site"]})
        sequence_frame = pd.DataFrame({"submission_id": [None], "submission_name": ["Submission A"]})
        site_spec = EntitySpec(
            role="lookup",
            public_id="site_id",
            identity_tracking="tracked",
            reconciliation="allocate",
        )
        sequence_spec = EntitySpec(
            role="fact",
            public_id="submission_id",
            public_id_generation="database_sequence",
            target_table="tbl_submissions",
            identity_tracking="derived",
            reconciliation="derive",
        )
        planned_tables = [
            plan_table("site", site_frame, site_spec),
            plan_table("submission", sequence_frame, sequence_spec),
        ]
        sims_client = FakeSimsClient(target_id=703)
        sequence_reserver = FakeDatabaseSequenceReserver(sims_client.events, target_id=902)

        result = await orchestrate_identity_assignments(
            planned_tables,
            minimal_submission_context(),
            sims_client=sims_client,  # type: ignore
            database_sequence_reserver=sequence_reserver,
            target_model_entities={"site": site_spec, "submission": sequence_spec},
        )

        assert sims_client.events == ["sequence", "sims"]
        assert sequence_reserver.calls == [("tbl_submissions", "submission_id")]
        assert result.assignments["submission"][0].state == ChangeRowState.NEWLY_ALLOCATED_ENTITY
        assert result.assignments["submission"][0].target_id == 902
        assert result.assignments["site"][0].state == ChangeRowState.NEWLY_ALLOCATED_ENTITY
        assert result.assignments["site"][0].target_id == 703

    @pytest.mark.asyncio
    async def test_failed_database_sequence_reservation_stops_sims_allocations(self):
        site_frame = pd.DataFrame({"site_id": [None], "national_site_identifier": ["new-site"]})
        sequence_frame = pd.DataFrame({"submission_id": [None], "submission_name": ["Submission A"]})
        site_spec = EntitySpec(
            role="lookup",
            public_id="site_id",
            identity_tracking="tracked",
            reconciliation="allocate",
        )
        sequence_spec = EntitySpec(
            role="fact",
            public_id="submission_id",
            public_id_generation="database_sequence",
            target_table="tbl_submissions",
            identity_tracking="derived",
            reconciliation="derive",
        )
        planned_tables = [
            plan_table("site", site_frame, site_spec),
            plan_table("submission", sequence_frame, sequence_spec),
        ]
        sims_client = FakeSimsClient()
        sequence_reserver = FakeDatabaseSequenceReserver(
            sims_client.events,
            error=DatabaseSequenceReservationError("sequence unavailable"),
        )

        result = await orchestrate_identity_assignments(
            planned_tables,
            minimal_submission_context(),
            sims_client=sims_client,  # type: ignore
            database_sequence_reserver=sequence_reserver,
            target_model_entities={"site": site_spec, "submission": sequence_spec},
        )

        sequence_assignment = result.assignments["submission"][0]
        site_assignment = result.assignments["site"][0]
        assert sequence_assignment.state == ChangeRowState.BLOCKED_UNRESOLVED
        assert "sequence unavailable" in (sequence_assignment.note or "")
        assert site_assignment.state == ChangeRowState.BLOCKED_UNRESOLVED
        assert "SIMS allocation was skipped" in (site_assignment.note or "")
        assert sims_client.events == ["sequence"]
        assert not sims_client.allocated_entities

    @pytest.mark.asyncio
    async def test_proposed_binding_set_blocks_sims_rows(self):
        frame = pd.DataFrame({"sample_id": [None]})
        planned_table = plan_table("sample", frame, EntitySpec(role="fact", public_id="sample_id"))

        result = await orchestrate_identity_assignments(
            [planned_table],
            minimal_submission_context(),
            sims_client=FakeSimsClient(  # type: ignore
                binding_set_state="proposed",
                confirmed_binding_set_state="proposed",
                target_id=501,
            ),
        )

        assignment = result.assignments["sample"][0]
        assert assignment.state == ChangeRowState.BLOCKED_UNRESOLVED
        assert "must be confirmed" in (assignment.note or "")
        assert result.binding_set_state == "proposed"

    @pytest.mark.asyncio
    async def test_proposed_binding_set_is_not_auto_confirmed(self):
        """The ingester must not auto-confirm; a proposed set stays proposed and blocks."""
        frame = pd.DataFrame({"sample_id": [None]})
        planned_table = plan_table("sample", frame, EntitySpec(role="fact", public_id="sample_id"))
        sims_client = FakeSimsClient(binding_set_state="proposed", confirmed_binding_set_state="confirmed", target_id=501)

        result = await orchestrate_identity_assignments(
            [planned_table],
            minimal_submission_context(),
            sims_client=sims_client,  # type: ignore
        )

        assignment = result.assignments["sample"][0]
        assert assignment.state == ChangeRowState.BLOCKED_UNRESOLVED
        assert "must be confirmed" in (assignment.note or "")
        assert result.binding_set_state == "proposed"
        assert not sims_client.confirm_calls

    @pytest.mark.asyncio
    async def test_confirmed_binding_set_proceeds_without_confirm_call(self):
        """A confirmed set proceeds and the ingester never confirms it."""
        frame = pd.DataFrame({"sample_id": [None]})
        planned_table = plan_table("sample", frame, EntitySpec(role="fact", public_id="sample_id"))
        sims_client = FakeSimsClient(binding_set_state="confirmed", target_id=501)

        result = await orchestrate_identity_assignments(
            [planned_table],
            minimal_submission_context(),
            sims_client=sims_client,  # type: ignore
        )

        assignment = result.assignments["sample"][0]
        assert assignment.state == ChangeRowState.NEWLY_ALLOCATED_ENTITY
        assert result.binding_set_state == "confirmed"
        assert not sims_client.confirm_calls

    @pytest.mark.asyncio
    async def test_missing_target_id_blocks_sims_rows(self):
        frame = pd.DataFrame({"sample_id": [None]})
        planned_table = plan_table("sample", frame, EntitySpec(role="fact", public_id="sample_id"))

        result = await orchestrate_identity_assignments(
            [planned_table],
            minimal_submission_context(),
            sims_client=FakeSimsClient(binding_set_state="confirmed", target_id=None),  # type: ignore
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
            sims_client=FakeSimsClient(binding_set_state="confirmed", target_id=501),  # type: ignore
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

    @pytest.mark.asyncio
    async def test_multiple_allocations_are_collected_into_one_batch(self):
        """Two allocate rows should submit exactly one SIMS resolve batch."""
        frame = pd.DataFrame({"sample_id": [None, None], "sample_name": ["A", "B"]})
        planned_table = plan_table("sample", frame, EntitySpec(role="fact", public_id="sample_id"))
        sims_client = FakeSimsClient(binding_set_state="confirmed", target_id=501)

        result = await orchestrate_identity_assignments(
            [planned_table],
            minimal_submission_context(),
            sims_client=sims_client,  # type: ignore
        )

        assert len(sims_client.batch_calls) == 1
        assert len(sims_client.batch_calls[0]) == 2
        assert result.assignments["sample"][0].target_id == 501
        assert result.assignments["sample"][1].target_id == 501

    @pytest.mark.asyncio
    async def test_outcomes_map_to_rows_by_request_order(self):
        """Outcomes must correlate to rows by request order, not by entity name."""
        frame = pd.DataFrame({"sample_id": [None, None], "sample_name": ["A", "B"]})
        planned_table = plan_table("sample", frame, EntitySpec(role="fact", public_id="sample_id"))
        sims_client = FakeSimsClient(binding_set_state="confirmed", target_id=501)

        async def ordered_resolve_batch(items, submission_context):
            sims_client.batch_calls.append(list(items))
            return {
                "outcomes": [
                    {"target_id": 1001, "tracked_identity_uuid": None},
                    {"target_id": 1002, "tracked_identity_uuid": None},
                ],
                "binding_set_uuid": sims_client.binding_set_uuid,
                "binding_set_state": sims_client.binding_set_state,
            }

        sims_client.resolve_batch = ordered_resolve_batch

        result = await orchestrate_identity_assignments(
            [planned_table],
            minimal_submission_context(),
            sims_client=sims_client,  # type: ignore
        )

        assert result.assignments["sample"][0].target_id == 1001
        assert result.assignments["sample"][1].target_id == 1002

    @pytest.mark.asyncio
    async def test_lookup_only_approval_does_not_allocate(self):
        """A local-only approval cannot allocate in lookup-only mode."""
        frame = pd.DataFrame({"taxa_tree_master_id": [None], "taxon_name": ["Taxon A"]})
        entity_spec = EntitySpec(
            role="classifier",
            public_id="taxa_tree_master_id",
            identity_tracking="reconciled",
            reconciliation="lookup-only",
        )
        planned_table = plan_table(
            "taxa_tree_master",
            frame,
            entity_spec,
            local_key_columns=("taxon_name",),
            approved_local_only_keys={encode_local_key("taxon_name", "Taxon A")},
        )
        sims_client = FakeSimsClient(binding_set_state="confirmed", target_id=501)

        result = await orchestrate_identity_assignments(
            [planned_table],
            minimal_submission_context(),
            sims_client=sims_client,  # type: ignore
            target_model_entities={"taxa_tree_master": entity_spec},
        )

        assignment = result.assignments["taxa_tree_master"][0]
        assert assignment.state == ChangeRowState.BLOCKED_UNRESOLVED
        assert "cannot allocate in reconciliation mode" in (assignment.note or "")
        assert not sims_client.batch_calls

    @pytest.mark.asyncio
    async def test_reconcile_exact_approval_allocates(self):
        """A reconcile-exact row with an exported approval may request allocation."""
        frame = pd.DataFrame({"site_id": [None], "site_name": ["Nordic Site"]})
        entity_spec = EntitySpec(role="lookup", public_id="site_id")
        planned_table = plan_table(
            "site",
            frame,
            entity_spec,
            local_key_columns=("site_name",),
            approved_local_only_keys={encode_local_key("site_name", "Nordic Site")},
        )
        sims_client = FakeSimsClient(binding_set_state="confirmed", target_id=501)

        result = await orchestrate_identity_assignments(
            [planned_table],
            minimal_submission_context(),
            sims_client=sims_client,  # type: ignore
            target_model_entities={"site": entity_spec},
        )

        assignment = result.assignments["site"][0]
        assert assignment.state == ChangeRowState.NEWLY_ALLOCATED_ENTITY
        assert assignment.target_id == 501
        assert sims_client.allocated_entities == ["site"]
