"""Tests for backend runtime adapters used by the SEAD change request ingester."""

import os
from datetime import datetime
from types import SimpleNamespace
from typing import Any, cast
from uuid import UUID, uuid4

import httpx
import pandas as pd
import psycopg
import pytest
from psycopg import sql

from backend.app.clients.sims_client import SimsClient
from backend.app.models.reconciliation import ReconciliationCandidate
from backend.app.models.sims import ResolveRequest, ResolveResponse
from backend.app.services.ingester_runtime import (
    SeadChangeRequestReconciliationAdapter,
    SeadChangeRequestSimsAdapter,
    SeadChangeRequestTargetCollisionChecker,
)
from ingesters.sead_change_request import ChangeRowState, orchestrate_identity_assignments
from ingesters.sead_change_request.contracts import PlannedRowAction, PlannedTable, SubmissionContext

# pylint: disable=unused-argument


class FakeBackendReconciliationClient:
    """Minimal fake backend reconciliation client."""

    def __init__(self, results: dict[str, list[ReconciliationCandidate]]) -> None:
        self.results = results

    async def reconcile_batch(self, queries: dict[str, object]) -> dict[str, list[ReconciliationCandidate]]:
        return self.results


class FakeBindingSetResponse:
    """Minimal binding set response double."""

    def __init__(self, binding_set_uuid: str, lifecycle_state: str) -> None:
        self.binding_set_uuid = UUID(binding_set_uuid)
        self.lifecycle_state = SimpleNamespace(value=lifecycle_state)


class FakeResolveResponse:
    """Minimal resolve response double."""

    def __init__(self, binding_set_uuid: str, lifecycle_state: str, *, target_id: int | None = None) -> None:
        self.binding_set = FakeBindingSetResponse(binding_set_uuid, lifecycle_state)
        self.outcomes = [SimpleNamespace(tracked_identity_uuid=UUID("12345678-1234-5678-1234-567812345678"), target_id=target_id)]


class FakeBackendSimsClient:
    """Minimal fake backend SIMS client."""

    def __init__(
        self,
        binding_set_uuid: str = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        lifecycle_state: str = "confirmed",
        *,
        target_id: int | None = None,
        resolve_error: httpx.HTTPStatusError | None = None,
    ) -> None:
        self.binding_set_uuid = binding_set_uuid
        self.lifecycle_state = lifecycle_state
        self.target_id = target_id
        self.resolve_error = resolve_error
        self.resolve_requests: list[object] = []
        self.associated_change_requests: list[tuple[UUID, str]] = []

    async def resolve(self, request: object) -> FakeResolveResponse:
        self.resolve_requests.append(request)
        if self.resolve_error is not None:
            raise self.resolve_error
        return FakeResolveResponse(self.binding_set_uuid, self.lifecycle_state, target_id=self.target_id)

    async def get_binding_set(self, binding_set_uuid: UUID) -> FakeBindingSetResponse:
        return FakeBindingSetResponse(str(binding_set_uuid), self.lifecycle_state)

    async def confirm_binding_set(self, binding_set_uuid: UUID) -> FakeBindingSetResponse:
        self.lifecycle_state = "confirmed"
        return FakeBindingSetResponse(str(binding_set_uuid), self.lifecycle_state)

    async def associate_change_request(self, binding_set_uuid: UUID, change_request_name: str) -> FakeBindingSetResponse:
        self.associated_change_requests.append((binding_set_uuid, change_request_name))
        return FakeBindingSetResponse(str(binding_set_uuid), self.lifecycle_state)


def minimal_submission_context() -> SubmissionContext:
    return SubmissionContext(
        submission_name="test-submission",
        project_name="test-project",
        timestamp=datetime.fromisoformat("2026-05-23T23:10:00"),
    )


class FakeReconciliationClient:
    """Return a configured target ID or a reconciliation miss."""

    def __init__(self, target_id: int | None = 77) -> None:
        self.target_id = target_id
        self.calls = 0

    async def reconcile_entity(self, entity_name: str, row: dict[str, Any]) -> int | None:
        self.calls += 1
        return self.target_id


class RecordingSimsClient(SimsClient):
    """Record responses from the real SIMS HTTP client."""

    def __init__(self, base_url: str) -> None:
        super().__init__(base_url)
        self.resolve_responses: list[ResolveResponse] = []

    async def resolve(self, request: ResolveRequest) -> ResolveResponse:
        response = await super().resolve(request)
        self.resolve_responses.append(response)
        return response


class TestSeadChangeRequestReconciliationAdapter:
    """Tests for the backend reconciliation adapter."""

    @pytest.mark.asyncio
    async def test_reconcile_entity_extracts_numeric_target_id(self):
        adapter = SeadChangeRequestReconciliationAdapter(
            cast(
                Any,
                FakeBackendReconciliationClient(
                    {
                        "row-0": [
                            ReconciliationCandidate(
                                id="https://example.org/entity/77",
                                name="Class A",
                                score=99.0,
                                distance_km=None,
                                description=None,
                                match=True,
                            )
                        ]
                    }
                ),
            )
        )

        target_id = await adapter.reconcile_entity("abundance_class", {"name": "Class A", "class_id": None})

        assert target_id == 77


class TestSeadChangeRequestSimsAdapter:
    """Tests for the backend SIMS adapter."""

    @pytest.mark.asyncio
    async def test_allocate_entity_returns_binding_set_metadata_and_blocks_target_id(self):
        sims_client = FakeBackendSimsClient(lifecycle_state="confirmed")
        adapter = SeadChangeRequestSimsAdapter(cast(Any, sims_client))

        allocation = await adapter.allocate_entity(
            "sample",
            {"sample_id": None, "name": "Sample A"},
            SubmissionContext(
                submission_name="test-submission",
                project_name="test-project",
                timestamp=datetime.fromisoformat("2026-05-23T23:10:00"),
            ),
        )

        assert allocation["target_id"] is None
        assert allocation["binding_set_uuid"] == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        assert allocation["binding_set_state"] == "confirmed"
        assert "does not expose a SIMS aggregate ID" in allocation["note"]

    @pytest.mark.asyncio
    async def test_allocate_entity_uses_target_id_when_backend_response_provides_it(self):
        sims_client = FakeBackendSimsClient(lifecycle_state="confirmed", target_id=501)
        adapter = SeadChangeRequestSimsAdapter(cast(Any, sims_client))

        allocation = await adapter.allocate_entity(
            "sample",
            {"sample_id": None, "name": "Sample A"},
            SubmissionContext(
                submission_name="test-submission",
                project_name="test-project",
                timestamp=datetime.fromisoformat("2026-05-23T23:10:00"),
            ),
        )

        assert allocation["target_id"] == 501
        assert allocation["binding_set_uuid"] == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        assert allocation["binding_set_state"] == "confirmed"
        assert allocation["note"] == "SIMS resolved 'sample' into Binding Set 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'"

    @pytest.mark.asyncio
    async def test_reconciliation_result_flows_through_adapter_into_sims_request(self):
        sims_client = FakeBackendSimsClient(target_id=77)
        adapter = SeadChangeRequestSimsAdapter(cast(Any, sims_client))
        frame = pd.DataFrame({"site_name": ["Approved site"]})
        planned_table = PlannedTable(
            entity_name="site",
            frame=frame,
            planned_actions=pd.Series([PlannedRowAction.RECONCILE], index=frame.index, name="_planned_action"),
        )

        result = await orchestrate_identity_assignments(
            [planned_table],
            minimal_submission_context(),
            sims_client=adapter,
            reconciliation_client=FakeReconciliationClient(),
        )

        assignment = result.assignments["site"][0]
        resolve_request = sims_client.resolve_requests[0]
        assert assignment.state == ChangeRowState.RECONCILED_CLASSIFIER
        assert assignment.target_id == 77
        assert result.binding_set_uuid == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        assert resolve_request.requests[0].approved_aggregate_id == 77
        assert resolve_request.model_dump(mode="json")["requests"][0]["approved_aggregate_id"] == 77

    @pytest.mark.asyncio
    async def test_reconciliation_conflict_blocks_row_without_using_approved_id(self):
        request = httpx.Request("POST", "http://sims.test/identity/resolve")
        response = httpx.Response(409, request=request, text="approved aggregate ID is already bound elsewhere")
        conflict = httpx.HTTPStatusError("409 Conflict", request=request, response=response)
        sims_client = FakeBackendSimsClient(resolve_error=conflict)
        adapter = SeadChangeRequestSimsAdapter(cast(Any, sims_client))
        frame = pd.DataFrame({"site_name": ["Approved site"]})
        planned_table = PlannedTable(
            entity_name="site",
            frame=frame,
            planned_actions=pd.Series([PlannedRowAction.RECONCILE], index=frame.index, name="_planned_action"),
        )

        result = await orchestrate_identity_assignments(
            [planned_table],
            minimal_submission_context(),
            sims_client=adapter,
            reconciliation_client=FakeReconciliationClient(),
        )

        assignment = result.assignments["site"][0]
        assert assignment.state == ChangeRowState.BLOCKED_UNRESOLVED
        assert assignment.target_id is None
        assert "HTTP 409" in (assignment.note or "")
        assert "already bound elsewhere" in (assignment.note or "")

    @pytest.mark.asyncio
    async def test_derive_bridge_row_returns_bridge_state_without_target_id(self):
        adapter = SeadChangeRequestSimsAdapter(cast(Any, FakeBackendSimsClient(lifecycle_state="confirmed")))

        bridge = await adapter.derive_bridge_row(
            "sample_taxon",
            {"sample_id": 101, "taxon_id": 9001, "abundance": 3},
            minimal_submission_context(),
        )

        assert bridge["state"] == "derived_bridge_row"
        assert bridge["target_id"] is None
        assert "projected from resolved parent IDs" in bridge["note"]

    @pytest.mark.asyncio
    async def test_get_binding_set_state_reads_backend_client(self):
        adapter = SeadChangeRequestSimsAdapter(cast(Any, FakeBackendSimsClient(lifecycle_state="proposed")))

        state = await adapter.get_binding_set_state("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")

        assert state == "proposed"

    @pytest.mark.asyncio
    async def test_confirm_binding_set_returns_updated_state(self):
        adapter = SeadChangeRequestSimsAdapter(cast(Any, FakeBackendSimsClient(lifecycle_state="proposed")))

        state = await adapter.confirm_binding_set("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")

        assert state == "confirmed"

    @pytest.mark.asyncio
    async def test_associate_change_request_calls_backend_client(self):
        sims_client = FakeBackendSimsClient(lifecycle_state="confirmed")
        adapter = SeadChangeRequestSimsAdapter(cast(Any, sims_client))

        await adapter.associate_change_request("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "deploy/test-change")

        assert sims_client.associated_change_requests == [(UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"), "deploy/test-change")]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_approved_site_match_through_real_sims_service():
    """Send an approved site ID through Shape Shifter to a disposable SIMS service."""
    base_url = os.getenv("SIMS_DISPOSABLE_INTEGRATION_URL")
    approved_aggregate_id = os.getenv("SIMS_DISPOSABLE_APPROVED_SITE_AGGREGATE_ID")
    conflicting_aggregate_id = os.getenv("SIMS_DISPOSABLE_CONFLICT_SITE_AGGREGATE_ID")
    if not all((base_url, approved_aggregate_id, conflicting_aggregate_id)):
        pytest.skip("Set the three SIMS_DISPOSABLE_* variables for the disposable service test")

    approved_id = int(approved_aggregate_id)
    conflicting_id = int(conflicting_aggregate_id)
    assert approved_id > 0
    assert conflicting_id > 0
    assert conflicting_id != approved_id

    source_key = f"shape-shifter-approved-site-{uuid4().hex}"
    scope_name = f"sead://test-integration/shape-shifter/{uuid4().hex}"
    sims_client = RecordingSimsClient(base_url)
    adapter = SeadChangeRequestSimsAdapter(sims_client, scope_name=scope_name, created_by="local-disposable-verification")

    async def resolve_site(submission_name: str, target_id: int):
        frame = pd.DataFrame({"site_name": [source_key]})
        planned_table = PlannedTable(
            entity_name="site",
            frame=frame,
            planned_actions=pd.Series([PlannedRowAction.RECONCILE], index=frame.index, name="_planned_action"),
        )
        context = SubmissionContext(
            submission_name=submission_name,
            project_name="shape-shifter-disposable-verification",
            timestamp=datetime.now(),
        )
        return await orchestrate_identity_assignments(
            [planned_table],
            context,
            sims_client=adapter,
            reconciliation_client=FakeReconciliationClient(target_id),
        )

    try:
        first_result = await resolve_site(f"first-{source_key}", approved_id)
        first_assignment = first_result.assignments["site"][0]
        first_outcome = sims_client.resolve_responses[-1].outcomes[0]
        assert first_assignment.state == ChangeRowState.RECONCILED_CLASSIFIER
        assert first_assignment.target_id == approved_id
        assert first_outcome.target_id == approved_id
        assert first_outcome.tracked_identity_uuid is not None
        assert sims_client.resolve_responses[-1].binding_set.lifecycle_state.value == "confirmed"

        second_result = await resolve_site(f"second-{source_key}", approved_id)
        second_assignment = second_result.assignments["site"][0]
        second_outcome = sims_client.resolve_responses[-1].outcomes[0]
        assert second_assignment.state == ChangeRowState.RECONCILED_CLASSIFIER
        assert second_assignment.target_id == approved_id
        assert second_outcome.source_identity_uuid == first_outcome.source_identity_uuid
        assert second_outcome.tracked_identity_uuid == first_outcome.tracked_identity_uuid
        assert second_outcome.target_id == first_outcome.target_id
        assert sims_client.resolve_responses[-1].binding_set.lifecycle_state.value == "confirmed"

        conflict_result = await resolve_site(f"conflict-{source_key}", conflicting_id)
        conflict_assignment = conflict_result.assignments["site"][0]
        assert conflict_assignment.state == ChangeRowState.BLOCKED_UNRESOLVED
        assert conflict_assignment.target_id is None
        assert "HTTP 409" in (conflict_assignment.note or "")
    finally:
        await sims_client.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_reconciliation_miss_allocates_site_through_real_sims_service():
    """Allocate a synthetic site after a mocked reconciliation miss."""
    base_url = os.getenv("SIMS_DISPOSABLE_INTEGRATION_URL")
    if not base_url:
        pytest.skip("Set SIMS_DISPOSABLE_INTEGRATION_URL for the disposable service test")

    source_key = f"ss-verify-site-{uuid4().hex}"
    scope_name = f"sead://test-integration/shape-shifter/{uuid4().hex}"
    sims_client = RecordingSimsClient(base_url)
    adapter = SeadChangeRequestSimsAdapter(sims_client, scope_name=scope_name, created_by="local-disposable-verification")
    reconciliation_client = FakeReconciliationClient(target_id=None)

    async def resolve_site(submission_name: str):
        frame = pd.DataFrame({"site_name": [source_key]})
        planned_table = PlannedTable(
            entity_name="site",
            frame=frame,
            planned_actions=pd.Series([PlannedRowAction.RECONCILE], index=frame.index, name="_planned_action"),
        )
        context = SubmissionContext(
            submission_name=submission_name,
            project_name="shape-shifter-disposable-verification",
            timestamp=datetime.now(),
        )
        return await orchestrate_identity_assignments(
            [planned_table],
            context,
            sims_client=adapter,
            reconciliation_client=reconciliation_client,
        )

    try:
        first_result = await resolve_site(f"first-{source_key}")
        first_assignment = first_result.assignments["site"][0]
        first_response = sims_client.resolve_responses[-1]
        first_outcome = first_response.outcomes[0]
        assert reconciliation_client.calls == 1
        assert first_assignment.state == ChangeRowState.NEWLY_ALLOCATED_ENTITY
        assert first_assignment.target_id is not None
        assert first_outcome.outcome == "new"
        assert first_outcome.target_id == first_assignment.target_id
        assert first_outcome.tracked_identity_uuid is not None
        assert first_response.binding_set.lifecycle_state.value == "confirmed"

        retry_result = await resolve_site(f"retry-{source_key}")
        retry_assignment = retry_result.assignments["site"][0]
        retry_response = sims_client.resolve_responses[-1]
        retry_outcome = retry_response.outcomes[0]
        assert reconciliation_client.calls == 2
        assert retry_assignment.state == ChangeRowState.NEWLY_ALLOCATED_ENTITY
        assert retry_assignment.target_id == first_assignment.target_id
        assert retry_outcome.outcome == "matched"
        assert retry_outcome.source_identity_uuid == first_outcome.source_identity_uuid
        assert retry_outcome.tracked_identity_uuid == first_outcome.tracked_identity_uuid
        assert retry_outcome.target_id == first_outcome.target_id
        assert retry_response.binding_set.lifecycle_state.value == "confirmed"
    finally:
        await sims_client.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_target_sequence_reservation_uses_loopback_disposable_postgres():
    """Reserve submission_id from the helper-owned local PostgreSQL sequence."""
    host = os.getenv("SEAD_DISPOSABLE_POSTGRES_HOST")
    port = os.getenv("SEAD_DISPOSABLE_POSTGRES_PORT")
    dbname = os.getenv("SEAD_DISPOSABLE_POSTGRES_DB")
    user = os.getenv("SEAD_DISPOSABLE_POSTGRES_USER")
    if not all((host, port, dbname, user)):
        pytest.skip("Set SEAD_DISPOSABLE_POSTGRES_* variables for the loopback disposable database test")
    if host not in {"localhost", "127.0.0.1", "::1"}:
        pytest.fail("The disposable PostgreSQL integration test only accepts a loopback host")

    connection_kwargs: dict[str, Any] = {
        "host": host,
        "port": int(port),
        "dbname": dbname,
        "user": user,
    }
    password = os.getenv("SEAD_DISPOSABLE_POSTGRES_PASSWORD")
    if password:
        connection_kwargs["password"] = password

    async with await psycopg.AsyncConnection.connect(**connection_kwargs) as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(
                "SELECT pg_get_serial_sequence(%s, %s)",
                ("public.tbl_submissions", "submission_id"),
            )
            sequence_name = (await cursor.fetchone())[0]
            assert sequence_name is not None
            sequence_identifier = sql.Identifier(*(part.strip('"') for part in sequence_name.split(".")))
            await cursor.execute(sql.SQL("SELECT last_value, is_called FROM {}").format(sequence_identifier))
            previous_value, was_called = await cursor.fetchone()

    checker = SeadChangeRequestTargetCollisionChecker(**connection_kwargs)
    reserved_id = await checker.reserve_target_id("tbl_submissions", "submission_id")

    async with await psycopg.AsyncConnection.connect(**connection_kwargs) as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(sql.SQL("SELECT last_value, is_called FROM {}").format(sequence_identifier))
            current_value, is_called = await cursor.fetchone()

    expected_id = previous_value + 1 if was_called else previous_value
    assert reserved_id == expected_id
    assert current_value == reserved_id
    assert is_called is True
