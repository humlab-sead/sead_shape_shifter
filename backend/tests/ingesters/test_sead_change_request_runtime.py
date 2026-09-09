"""Tests for backend runtime adapters used by the SEAD change request ingester."""

from datetime import datetime
from types import SimpleNamespace
from typing import Any, cast
from uuid import UUID

import pytest

from backend.app.models.reconciliation import ReconciliationCandidate
from backend.app.services.ingester_runtime import SeadChangeRequestReconciliationAdapter, SeadChangeRequestSimsAdapter
from ingesters.sead_change_request.contracts import SubmissionContext

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
    ) -> None:
        self.binding_set_uuid = binding_set_uuid
        self.lifecycle_state = lifecycle_state
        self.target_id = target_id
        self.resolve_requests: list[object] = []
        self.associated_change_requests: list[tuple[UUID, str]] = []

    async def resolve(self, request: object) -> FakeResolveResponse:
        self.resolve_requests.append(request)
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
        assert "does not expose a target-facing integer ID" in allocation["note"]

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
