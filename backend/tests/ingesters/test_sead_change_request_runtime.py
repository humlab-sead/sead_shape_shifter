"""Tests for backend runtime adapters used by the SEAD change request ingester."""

import os
from datetime import datetime
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import httpx
import pandas as pd
import psycopg
import pytest
from psycopg import sql
from psycopg.rows import TupleRow

from backend.app.clients.sims_client import SimsClient
from backend.app.ingesters.protocol import IngesterConfig
from backend.app.models.sims import RegisterScopeContractsRequest, ResolveRequest, ResolveResponse
from backend.app.services.ingester_runtime import (
    SeadChangeRequestSimsAdapter,
    SeadChangeRequestTargetCollisionChecker,
)
from ingesters.sead_change_request import ChangeRowState, orchestrate_identity_assignments, plan_table
from ingesters.sead_change_request.contracts import (
    DatabaseSequenceReservationError,
    PlannedRowAction,
    PlannedTable,
    SimsResolveItem,
    SubmissionContext,
)
from ingesters.sead_change_request.input_resolution import SubmissionContextError, resolve_inputs
from src.reconciliation.mapping_model import encode_local_key
from src.target_model.models import EntitySpec

# pylint: disable=unused-argument

TEST_SCOPE_NAME = "provider://mal/test-pilot"
"""Provider-schema scope used by adapter tests instead of a project-name fallback."""


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
        contract_error: httpx.HTTPStatusError | None = None,
    ) -> None:
        self.binding_set_uuid = binding_set_uuid
        self.lifecycle_state = lifecycle_state
        self.target_id = target_id
        self.resolve_error = resolve_error
        self.contract_error = contract_error
        self.resolve_requests: list[ResolveRequest] = []
        self.contract_requests: list[RegisterScopeContractsRequest] = []
        self.call_order: list[str] = []
        self.associated_change_requests: list[tuple[UUID, str]] = []

    async def register_scope_contracts(self, request: RegisterScopeContractsRequest) -> SimpleNamespace:
        self.call_order.append("register")
        self.contract_requests.append(request)
        if self.contract_error is not None:
            raise self.contract_error
        return SimpleNamespace(scope_name=request.scope_name, entities=[SimpleNamespace(state="existing")])

    async def resolve(self, request: ResolveRequest) -> FakeResolveResponse:
        self.call_order.append("resolve")
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
        scope_name=TEST_SCOPE_NAME,
    )


class RecordingSimsClient(SimsClient):
    """Record responses from the real SIMS HTTP client."""

    def __init__(self, base_url: str) -> None:
        super().__init__(base_url)
        self.resolve_responses: list[ResolveResponse] = []

    async def resolve(self, request: ResolveRequest) -> ResolveResponse:
        response = await super().resolve(request)
        self.resolve_responses.append(response)
        return response


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
                scope_name=TEST_SCOPE_NAME,
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
                scope_name=TEST_SCOPE_NAME,
            ),
        )

        assert allocation["target_id"] == 501
        assert allocation["binding_set_uuid"] == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        assert allocation["binding_set_state"] == "confirmed"
        assert allocation["note"] == "SIMS resolved 'sample' into Binding Set 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'"

    @pytest.mark.asyncio
    async def test_resolve_batch_submits_one_request_with_run_id(self):
        sims_client = FakeBackendSimsClient(lifecycle_state="confirmed", target_id=501)
        adapter = SeadChangeRequestSimsAdapter(cast(Any, sims_client))
        context = SubmissionContext(
            submission_name="test-submission",
            project_name="test-project",
            timestamp=datetime.fromisoformat("2026-05-23T23:10:00"),
            run_id="run-123",
            scope_name=TEST_SCOPE_NAME,
        )

        result = await adapter.resolve_batch(
            [
                SimsResolveItem(entity_name="sample", row={"sample_id": None, "name": "A"}),
                SimsResolveItem(entity_name="sample", row={"sample_id": None, "name": "B"}),
            ],
            context,
        )

        assert len(sims_client.resolve_requests) == 1
        request = sims_client.resolve_requests[0]
        assert hasattr(request, "run_id")
        assert request.run_id == "run-123"  # type: ignore
        assert len(request.requests) == 2  # type: ignore
        assert result["binding_set_uuid"] == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        assert result["binding_set_state"] == "confirmed"

    @pytest.mark.asyncio
    async def test_resolve_batch_mints_run_id_when_context_has_none(self):
        sims_client = FakeBackendSimsClient(lifecycle_state="confirmed", target_id=501)
        adapter = SeadChangeRequestSimsAdapter(cast(Any, sims_client))
        context = SubmissionContext(
            submission_name="test-submission",
            project_name="test-project",
            timestamp=datetime.fromisoformat("2026-05-23T23:10:00"),
            scope_name=TEST_SCOPE_NAME,
        )

        await adapter.resolve_batch([SimsResolveItem(entity_name="sample", row={"name": "A"})], context)

        request = sims_client.resolve_requests[0]
        assert request.run_id  # type: ignore

    @pytest.mark.asyncio
    async def test_unapproved_reconciled_row_never_reaches_sims(self):
        sims_client = FakeBackendSimsClient(target_id=77)
        adapter = SeadChangeRequestSimsAdapter(cast(Any, sims_client))
        frame = pd.DataFrame({"site_id": [None], "site_name": ["Unreviewed site"]})
        planned_table = PlannedTable(
            entity_name="site",
            frame=frame,
            planned_actions=pd.Series([PlannedRowAction.BLOCK_RECONCILIATION], index=frame.index, name="_planned_action"),
            blocked_row_reasons={0: "No exported local-only approval authorizes allocation for this business key"},
        )

        result = await orchestrate_identity_assignments(
            [planned_table],
            minimal_submission_context(),
            sims_client=adapter,
        )

        assignment = result.assignments["site"][0]
        assert assignment.state == ChangeRowState.BLOCKED_UNRESOLVED
        assert not sims_client.resolve_requests

    @pytest.mark.asyncio
    async def test_allocation_conflict_blocks_row(self):
        request = httpx.Request("POST", "http://sims.test/identity/resolve")
        response = httpx.Response(409, request=request, text="approved aggregate ID is already bound elsewhere")
        conflict = httpx.HTTPStatusError("409 Conflict", request=request, response=response)
        sims_client = FakeBackendSimsClient(resolve_error=conflict)
        adapter = SeadChangeRequestSimsAdapter(cast(Any, sims_client))
        frame = pd.DataFrame({"site_id": [None], "site_name": ["Approved site"]})
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
            approved_local_only_keys={encode_local_key("site_name", "Approved site")},
        )

        result = await orchestrate_identity_assignments(
            [planned_table],
            minimal_submission_context(),
            sims_client=adapter,
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
async def test_exported_local_only_approval_allocates_site_through_real_sims_service():
    """Allocate a synthetic site when its trusted business key has an exported approval."""
    base_url = os.getenv("SIMS_DISPOSABLE_INTEGRATION_URL")
    if not base_url:
        pytest.skip("Set SIMS_DISPOSABLE_INTEGRATION_URL for the disposable service test")

    source_key = f"ss-verify-site-{uuid4().hex}"
    scope_name = f"sead://test-integration/shape-shifter/{uuid4().hex}"
    sims_client = RecordingSimsClient(base_url)
    adapter = SeadChangeRequestSimsAdapter(sims_client, created_by="local-disposable-verification")

    async def resolve_site(submission_name: str):
        frame = pd.DataFrame({"site_id": [None], "site_name": [source_key]})
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
            approved_local_only_keys={encode_local_key("site_name", source_key)},
        )
        context = SubmissionContext(
            submission_name=submission_name,
            project_name="shape-shifter-disposable-verification",
            timestamp=datetime.now(),
            scope_name=scope_name,
        )
        return await orchestrate_identity_assignments(
            [planned_table],
            context,
            sims_client=adapter,
        )

    try:
        first_result = await resolve_site(f"first-{source_key}")
        first_assignment = first_result.assignments["site"][0]
        first_response = sims_client.resolve_responses[-1]
        first_outcome = first_response.outcomes[0]
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
async def test_target_verification_reads_do_not_advance_database_sequence():
    """Target verification reads leave the submission sequence unchanged."""
    host = os.getenv("SEAD_DISPOSABLE_POSTGRES_HOST")
    port = os.getenv("SEAD_DISPOSABLE_POSTGRES_PORT")
    dbname = os.getenv("SEAD_DISPOSABLE_POSTGRES_DB")
    user = os.getenv("SEAD_DISPOSABLE_POSTGRES_USER")
    if not (host and port and dbname and user):
        pytest.skip("Set SEAD_DISPOSABLE_POSTGRES_* variables for the loopback disposable database test")
    if host not in {"localhost", "127.0.0.1", "::1"}:
        pytest.fail("The disposable PostgreSQL integration test only accepts a loopback host")
    assert port is not None
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
            data: TupleRow | None = await cursor.fetchone()
            assert data is not None
            sequence_name = data[0]
            assert sequence_name is not None
            sequence_identifier = sql.Identifier(*(part.strip('"') for part in sequence_name.split(".")))
            await cursor.execute(sql.SQL("SELECT last_value, is_called FROM {}").format(sequence_identifier))
            data: TupleRow | None = await cursor.fetchone()
            assert data is not None
            previous_value, was_called = data

    checker = SeadChangeRequestTargetCollisionChecker(**connection_kwargs)
    await checker.target_id_exists("tbl_submissions", "submission_id", previous_value)
    await checker.row_exists("tbl_submissions", {"submission_id": previous_value})

    async with await psycopg.AsyncConnection.connect(**connection_kwargs) as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(sql.SQL("SELECT last_value, is_called FROM {}").format(sequence_identifier))
            data: TupleRow | None = await cursor.fetchone()
            assert data is not None
            current_value, is_called = data

    assert (current_value, is_called) == (previous_value, was_called)


class TestTargetCollisionCheckerDatabaseSequenceReservation:
    """Tests for target IDs reserved from database-owned sequences."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("table_name", "default_schema", "expected_table"),
        [
            ("tbl_submissions", "public", "public.tbl_submissions"),
            ("archive.tbl_submissions", "public", "archive.tbl_submissions"),
        ],
    )
    async def test_reserves_id_from_the_column_sequence(self, table_name, default_schema, expected_table):
        cursor = MagicMock()
        cursor.execute = AsyncMock()
        cursor.fetchone = AsyncMock(return_value=(902,))
        cursor.__aenter__ = AsyncMock(return_value=cursor)
        cursor.__aexit__ = AsyncMock(return_value=None)
        connection = MagicMock()
        connection.cursor = MagicMock(return_value=cursor)
        connection.__aenter__ = AsyncMock(return_value=connection)
        connection.__aexit__ = AsyncMock(return_value=None)
        checker = SeadChangeRequestTargetCollisionChecker(
            host="localhost",
            port=5432,
            dbname="test_db",
            user="test_user",
            default_schema=default_schema,
        )

        with patch(
            "backend.app.services.ingester_runtime.psycopg.AsyncConnection.connect",
            AsyncMock(return_value=connection),
        ):
            target_id = await checker.reserve_database_id(table_name, "submission_id")

        assert target_id == 902
        assert cursor.execute.await_args.args[1] == (expected_table, "submission_id")

    @pytest.mark.asyncio
    async def test_missing_column_sequence_raises_reservation_error(self):
        cursor = MagicMock()
        cursor.execute = AsyncMock()
        cursor.fetchone = AsyncMock(return_value=(None,))
        cursor.__aenter__ = AsyncMock(return_value=cursor)
        cursor.__aexit__ = AsyncMock(return_value=None)
        connection = MagicMock()
        connection.cursor = MagicMock(return_value=cursor)
        connection.__aenter__ = AsyncMock(return_value=connection)
        connection.__aexit__ = AsyncMock(return_value=None)
        checker = SeadChangeRequestTargetCollisionChecker(host="localhost", port=5432, dbname="test_db", user="test_user")

        with patch(
            "backend.app.services.ingester_runtime.psycopg.AsyncConnection.connect",
            AsyncMock(return_value=connection),
        ):
            with pytest.raises(DatabaseSequenceReservationError, match="no associated database sequence"):
                await checker.reserve_database_id("tbl_submissions", "submission_id")

    @pytest.mark.asyncio
    async def test_database_errors_are_reported_as_reservation_errors(self):
        checker = SeadChangeRequestTargetCollisionChecker(host="localhost", port=5432, dbname="test_db", user="test_user")

        with patch(
            "backend.app.services.ingester_runtime.psycopg.AsyncConnection.connect",
            AsyncMock(side_effect=psycopg.OperationalError("connection refused")),
        ):
            with pytest.raises(DatabaseSequenceReservationError, match="Could not reserve a database-sequence ID"):
                await checker.reserve_database_id("tbl_submissions", "submission_id")


class TestTrustedScopeAndBusinessKeys:
    """Tests for the trusted scope input and declared-key identity values."""

    @pytest.mark.asyncio
    async def test_adapter_requires_the_trusted_scope_instead_of_a_project_fallback(self):
        sims_client = FakeBackendSimsClient(lifecycle_state="confirmed", target_id=501)
        adapter = SeadChangeRequestSimsAdapter(cast(Any, sims_client))

        with pytest.raises(ValueError, match="provider-schema pair must supply it"):
            await adapter.allocate_entity(
                "sample",
                {"name": "A"},
                SubmissionContext(
                    submission_name="test-submission",
                    project_name="test-project",
                    timestamp=datetime.fromisoformat("2026-05-23T23:10:00"),
                ),
            )

        assert not sims_client.resolve_requests

    def test_caller_scope_override_is_rejected_before_any_source_read(self, tmp_path):
        config = IngesterConfig(
            host="localhost",
            port=5432,
            dbname="",
            user="",
            extra={
                "target_model": {"model": {"name": "Test", "version": "1"}, "entities": {}, "constraints": []},
                "submission_context": {
                    "submission_name": "test-submission",
                    "project_name": "test-project",
                    "timestamp": "2026-05-23T23:10:00",
                    "datatype": "mal",
                    "identifier": "TEST_SUBMISSION",
                },
                "sims_scope_name": "provider://other/scope",
            },
        )

        with pytest.raises(SubmissionContextError, match="cannot select the Change Request scope"):
            resolve_inputs(config, {"site": pd.DataFrame({"site_id": [1]})})

    @pytest.mark.asyncio
    async def test_declared_business_keys_serialize_the_identity_value(self):
        sims_client = FakeBackendSimsClient(lifecycle_state="confirmed", target_id=501)
        adapter = SeadChangeRequestSimsAdapter(cast(Any, sims_client), business_keys={"site": ("site_name", "site_code")})

        await adapter.allocate_entity(
            "site",
            {"site_name": "A", "site_code": 7, "unrelated": "ignored"},
            minimal_submission_context(),
        )
        assert sims_client.resolve_requests is not None
        assert len(sims_client.resolve_requests) > 0
        identity_value = sims_client.resolve_requests[0].requests[0].primary_signal.identity_value  # type: ignore
        assert identity_value == '[1,[["site_name","string","A"],["site_code","number","7"]]]'

    @pytest.mark.asyncio
    async def test_adapter_registers_the_ordered_contract_before_resolve(self):
        sims_client = FakeBackendSimsClient(lifecycle_state="confirmed", target_id=501)
        adapter = SeadChangeRequestSimsAdapter(
            cast(Any, sims_client),
            business_keys={"site": ("site_name", "site_code"), "bridge": ()},
        )

        await adapter.allocate_entity("site", {"site_name": "A", "site_code": 7}, minimal_submission_context())

        assert sims_client.call_order == ["register", "resolve"]
        registration = sims_client.contract_requests[0]
        assert registration.scope_name == TEST_SCOPE_NAME
        assert [(declaration.entity_type, declaration.business_keys) for declaration in registration.entities] == [
            ("site", ["site_name", "site_code"])
        ]

    @pytest.mark.asyncio
    async def test_rejected_scope_contract_stops_the_batch_before_resolve(self):
        request = httpx.Request("POST", "http://sims.test/identity/scope-contracts")
        response = httpx.Response(
            409,
            request=request,
            json={
                "detail": {
                    "message": "Business-key contract conflict for scope 'provider://mal/test-pilot'",
                    "conflicts": [
                        {
                            "entity_type": "site",
                            "registered": ["site_name", "country"],
                            "submitted": ["site_name"],
                        }
                    ],
                }
            },
        )
        contract_conflict = httpx.HTTPStatusError("409 Conflict", request=request, response=response)
        sims_client = FakeBackendSimsClient(contract_error=contract_conflict)
        adapter = SeadChangeRequestSimsAdapter(cast(Any, sims_client), business_keys={"site": ("site_name",)})
        frame = pd.DataFrame({"site_id": [None], "site_name": ["A"]})
        planned_table = PlannedTable(
            entity_name="site",
            frame=frame,
            planned_actions=pd.Series([PlannedRowAction.ALLOCATE], index=frame.index, name="_planned_action"),
        )

        result = await orchestrate_identity_assignments(
            [planned_table],
            minimal_submission_context(),
            sims_client=adapter,
        )

        assignment = result.assignments["site"][0]
        assert assignment.state == ChangeRowState.BLOCKED_UNRESOLVED
        note = assignment.note or ""
        assert "HTTP 409" in note
        assert "registered ['site_name', 'country'], submitted ['site_name']" in note
        assert not sims_client.resolve_requests
        assert sims_client.call_order == ["register"]

    @pytest.mark.asyncio
    async def test_declared_business_key_reuses_target_identity_across_runs(self):
        class StatefulBackendSimsClient(FakeBackendSimsClient):
            """Return the same target ID for a provider scope and business-key identity."""

            def __init__(self) -> None:
                super().__init__()
                self.identity_ids: dict[tuple[str, str], int] = {}

            async def resolve(self, request: ResolveRequest) -> FakeResolveResponse:
                self.resolve_requests.append(request)
                scope_name = request.scope_name  # type: ignore
                identity_value = request.requests[0].primary_signal.identity_value  # type: ignore
                identity_key = (scope_name, identity_value)
                target_id = self.identity_ids.setdefault(identity_key, 500 + len(self.identity_ids))
                return FakeResolveResponse(self.binding_set_uuid, self.lifecycle_state, target_id=target_id)

        sims_client = StatefulBackendSimsClient()
        adapter = SeadChangeRequestSimsAdapter(
            cast(Any, sims_client),
            business_keys={"site": ("site_name", "site_code")},
        )
        row = {"site_name": "A", "site_code": "7"}

        first = await adapter.allocate_entity(
            "site",
            row,
            SubmissionContext(
                submission_name="test-submission",
                project_name="test-project",
                timestamp=datetime.fromisoformat("2026-05-23T23:10:00"),
                scope_name=TEST_SCOPE_NAME,
                run_id="first-run",
            ),
        )
        second = await adapter.allocate_entity(
            "site",
            row,
            SubmissionContext(
                submission_name="test-submission",
                project_name="test-project",
                timestamp=datetime.fromisoformat("2026-05-23T23:10:00"),
                scope_name=TEST_SCOPE_NAME,
                run_id="second-run",
            ),
        )
        different_key = await adapter.allocate_entity(
            "site",
            {"site_name": "B", "site_code": "8"},
            SubmissionContext(
                submission_name="test-submission",
                project_name="test-project",
                timestamp=datetime.fromisoformat("2026-05-23T23:10:00"),
                scope_name=TEST_SCOPE_NAME,
                run_id="third-run",
            ),
        )
        different_scope = await adapter.allocate_entity(
            "site",
            row,
            SubmissionContext(
                submission_name="test-submission",
                project_name="test-project",
                timestamp=datetime.fromisoformat("2026-05-23T23:10:00"),
                scope_name="provider://mal/other-project",
                run_id="fourth-run",
            ),
        )

        assert first["target_id"] == second["target_id"]
        assert different_key["target_id"] != first["target_id"]
        assert different_scope["target_id"] != first["target_id"]
        assert [request.run_id for request in sims_client.resolve_requests] == [  # type: ignore
            "first-run",
            "second-run",
            "third-run",
            "fourth-run",
        ]
        assert {request.scope_name for request in sims_client.resolve_requests} == {  # type: ignore
            TEST_SCOPE_NAME,
            "provider://mal/other-project",
        }
        assert (
            sims_client.resolve_requests[0].requests[0].primary_signal.identity_value  # type: ignore
            == sims_client.resolve_requests[1].requests[0].primary_signal.identity_value  # type: ignore
        )

    @pytest.mark.asyncio
    async def test_invalid_declared_business_key_fails_before_sims_request(self):
        sims_client = FakeBackendSimsClient(lifecycle_state="confirmed", target_id=501)
        adapter = SeadChangeRequestSimsAdapter(cast(Any, sims_client), business_keys={"site": ("site_name", "site_code")})

        with pytest.raises(ValueError, match="Cannot serialize declared business key for entity 'site'"):
            await adapter.allocate_entity("site", {"site_name": "A"}, minimal_submission_context())

        assert not sims_client.resolve_requests

    @pytest.mark.asyncio
    async def test_entity_without_declared_keys_keeps_the_field_based_identity(self):
        sims_client = FakeBackendSimsClient(lifecycle_state="confirmed", target_id=501)
        adapter = SeadChangeRequestSimsAdapter(cast(Any, sims_client), business_keys={})

        await adapter.allocate_entity("sample", {"sample_id": None, "name": "A"}, minimal_submission_context())

        identity_value = sims_client.resolve_requests[0].requests[0].primary_signal.identity_value  # type: ignore
        assert identity_value == "sample:name=A"


class TestTargetCollisionCheckerColumnType:
    """Tests for read-only target public-ID type lookup."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("table_name", "default_schema", "expected_schema", "expected_table"),
        [
            ("tbl_locations", "sead", "sead", "tbl_locations"),
            ("archive.tbl_locations", "sead", "archive", "tbl_locations"),
        ],
    )
    async def test_type_lookup_uses_qualified_or_default_schema(self, table_name, default_schema, expected_schema, expected_table):
        cursor = MagicMock()
        cursor.execute = AsyncMock()
        cursor.fetchone = AsyncMock(return_value=("integer",))
        cursor.__aenter__ = AsyncMock(return_value=cursor)
        cursor.__aexit__ = AsyncMock(return_value=None)
        connection = MagicMock()
        connection.cursor = MagicMock(return_value=cursor)
        connection.__aenter__ = AsyncMock(return_value=connection)
        connection.__aexit__ = AsyncMock(return_value=None)
        checker = SeadChangeRequestTargetCollisionChecker(
            host="localhost",
            port=5432,
            dbname="test_db",
            user="test_user",
            default_schema=default_schema,
        )

        with patch(
            "backend.app.services.ingester_runtime.psycopg.AsyncConnection.connect",
            AsyncMock(return_value=connection),
        ):
            result = await checker.target_id_column_type(table_name, "location_id")

        assert result == "integer"
        assert cursor.execute.await_args.args[1] == (expected_schema, expected_table, "location_id")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("row, expected", [("text", "text"), (None, None)])
    async def test_type_lookup_returns_text_type_or_missing_column(self, row, expected):
        cursor = MagicMock()
        cursor.execute = AsyncMock()
        cursor.fetchone = AsyncMock(return_value=(row,) if row is not None else None)
        cursor.__aenter__ = AsyncMock(return_value=cursor)
        cursor.__aexit__ = AsyncMock(return_value=None)
        connection = MagicMock()
        connection.cursor = MagicMock(return_value=cursor)
        connection.__aenter__ = AsyncMock(return_value=connection)
        connection.__aexit__ = AsyncMock(return_value=None)
        checker = SeadChangeRequestTargetCollisionChecker(host="localhost", port=5432, dbname="test_db", user="test_user")

        with patch(
            "backend.app.services.ingester_runtime.psycopg.AsyncConnection.connect",
            AsyncMock(return_value=connection),
        ):
            result = await checker.target_id_column_type("tbl_locations", "location_id")

        assert result == expected

    @pytest.mark.asyncio
    async def test_type_lookup_surfaces_catalog_query_errors(self):
        cursor = MagicMock()
        cursor.execute = AsyncMock(side_effect=RuntimeError("catalog unavailable"))
        cursor.__aenter__ = AsyncMock(return_value=cursor)
        cursor.__aexit__ = AsyncMock(return_value=None)
        connection = MagicMock()
        connection.cursor = MagicMock(return_value=cursor)
        connection.__aenter__ = AsyncMock(return_value=connection)
        connection.__aexit__ = AsyncMock(return_value=None)
        checker = SeadChangeRequestTargetCollisionChecker(host="localhost", port=5432, dbname="test_db", user="test_user")

        with patch(
            "backend.app.services.ingester_runtime.psycopg.AsyncConnection.connect",
            AsyncMock(return_value=connection),
        ):
            with pytest.raises(RuntimeError, match="catalog unavailable"):
                await checker.target_id_column_type("tbl_locations", "location_id")
