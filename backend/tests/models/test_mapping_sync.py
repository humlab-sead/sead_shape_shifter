"""Tests for the pending fixed-entity mapping API models and mapper round-trip.

Covers add, edit, clear, remove, and key-change operations, zero and missing
IDs, entry-only creation, and pre-existing reconciliation/import links. Also
asserts the payload is JSON-safe (no NaN) and that malformed payloads fail
validation.
"""

import json
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.models.mapping_sync import MappingSyncOperation, MappingSyncPending
from src.reconciliation.fixed_entity_mapping_changes import FixedRowChangeSet, LinkDelete, LinkUpsert
from src.reconciliation.mapping_model import EntityMapping, EntityType, Link, LinkSource

CREATED = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _link(target_id: int, source: LinkSource, *, created_by: str = "tester", reviewed_by: str | None = None) -> Link:
    return Link(
        target_id=target_id,
        source=source,
        created_by=created_by,
        created_at=CREATED,
        committed_at=CREATED,
        reviewed_by=reviewed_by,
        confidence=0.9,
        notes="prior",
    )


def _change_set(
    *,
    upserts: tuple[LinkUpsert, ...] = (),
    deletes: tuple[LinkDelete, ...] = (),
    proposed_entry: EntityMapping | None = None,
) -> FixedRowChangeSet:
    return FixedRowChangeSet(
        entity_name="site",
        eligible=True,
        local_key="site_code",
        public_id="site_id",
        proposed_entry=proposed_entry,
        upserts=upserts,
        deletes=deletes,
    )


def _to_pending(change_set: FixedRowChangeSet, storage_kind: str = "inline") -> MappingSyncPending:
    return ProjectMapper.fixed_change_set_to_pending(
        change_set,
        project="test_project",
        entity="site",
        storage_kind=storage_kind,
        row_version="rows-v1",
        sidecar_version="sidecar-v1",
    )


class TestPendingRoundTrip:
    def test_upsert_with_missing_prior_link_round_trips(self) -> None:
        change_set = _change_set(upserts=(LinkUpsert(key="A", target_id=11, previous_saved_id=None, new_saved_id=11, previous_link=None),))

        pending = _to_pending(change_set)
        restored = ProjectMapper.pending_to_fixed_change_set(pending)

        assert pending.status == "pending"
        assert pending.rows_saved is True
        assert pending.storage_kind == "inline"
        assert pending.operations[0].op == "upsert"
        assert pending.operations[0].target_id == 11
        assert pending.operations[0].expected_row_present is True
        assert pending.operations[0].expected_saved_id == 11
        assert pending.operations[0].prior_link is None
        assert restored.upserts[0].key == "A"
        assert restored.upserts[0].target_id == 11
        assert restored.upserts[0].previous_link is None
        assert restored.local_key == "site_code"
        assert restored.public_id == "site_id"

    def test_upsert_with_prior_reconciliation_link_keeps_metadata(self) -> None:
        prior = _link(99, LinkSource.RECONCILIATION, created_by="reconciler", reviewed_by="reviewer")
        change_set = _change_set(upserts=(LinkUpsert(key="B", target_id=5, previous_saved_id=10, new_saved_id=5, previous_link=prior),))

        pending = _to_pending(change_set)
        restored = ProjectMapper.pending_to_fixed_change_set(pending)

        assert pending.operations[0].prior_link is not None
        assert pending.operations[0].prior_link.source == "reconciliation"
        assert pending.operations[0].prior_link.reviewed_by == "reviewer"
        restored_link = restored.upserts[0].previous_link
        assert restored_link is not None
        assert restored_link.source == LinkSource.RECONCILIATION
        assert restored_link.target_id == 99
        assert restored_link.notes == "prior"

    def test_zero_target_id_is_recorded(self) -> None:
        change_set = _change_set(upserts=(LinkUpsert(key="Z", target_id=0, previous_saved_id=None, new_saved_id=0, previous_link=None),))

        pending = _to_pending(change_set)
        assert pending.operations[0].target_id == 0
        assert pending.operations[0].expected_saved_id == 0

    def test_removed_row_delete_records_absent_row(self) -> None:
        prior = _link(7, LinkSource.IMPORT, created_by="importer")
        change_set = _change_set(
            deletes=(LinkDelete(key="C", previous_saved_id=7, new_saved_id=None, row_removed=True, previous_link=prior),)
        )

        pending = _to_pending(change_set)
        restored = ProjectMapper.pending_to_fixed_change_set(pending)

        assert pending.operations[0].op == "delete"
        assert pending.operations[0].expected_row_present is False
        assert pending.operations[0].expected_saved_id is None
        assert restored.deletes[0].row_removed is True
        assert restored.deletes[0].previous_link is not None
        assert restored.deletes[0].previous_link.source == LinkSource.IMPORT

    def test_cleared_id_delete_records_present_blank_row(self) -> None:
        prior = _link(3, LinkSource.MANUAL)
        change_set = _change_set(
            deletes=(LinkDelete(key="D", previous_saved_id=3, new_saved_id=None, row_removed=False, previous_link=prior),)
        )

        pending = _to_pending(change_set)
        restored = ProjectMapper.pending_to_fixed_change_set(pending)

        assert pending.operations[0].expected_row_present is True
        assert pending.operations[0].expected_saved_id is None
        assert restored.deletes[0].row_removed is False

    def test_entry_only_creation_round_trips(self) -> None:
        entry = EntityMapping(local_key="site_code", public_id="site_id", entity_type=EntityType.PRIMARY)
        change_set = _change_set(proposed_entry=entry)

        pending = _to_pending(change_set)
        restored = ProjectMapper.pending_to_fixed_change_set(pending)

        assert pending.entry is not None
        assert pending.entry.public_id == "site_id"
        assert pending.entry.prior_entry_exists is False
        assert pending.operations == []
        assert restored.proposed_entry is not None
        assert restored.proposed_entry.local_key == "site_code"

    def test_compound_key_change_round_trips(self) -> None:
        change_set = FixedRowChangeSet(
            entity_name="site",
            eligible=True,
            local_key=["country", "name"],
            public_id="site_id",
            upserts=(
                LinkUpsert(key="SE|A", target_id=1, previous_saved_id=None, new_saved_id=1, previous_link=None),
                LinkUpsert(key="SE|B", target_id=2, previous_saved_id=None, new_saved_id=2, previous_link=None),
            ),
        )

        pending = _to_pending(change_set)
        restored = ProjectMapper.pending_to_fixed_change_set(pending)

        assert pending.local_key == ["country", "name"]
        assert {operation.key for operation in pending.operations} == {"SE|A", "SE|B"}
        assert restored.local_key == ["country", "name"]

    def test_payload_is_json_safe(self) -> None:
        change_set = _change_set(upserts=(LinkUpsert(key="A", target_id=11, previous_saved_id=None, new_saved_id=11, previous_link=None),))
        payload = json.dumps(_to_pending(change_set).model_dump(mode="json"), allow_nan=False)
        assert "NaN" not in payload


class TestPendingValidation:
    def test_upsert_requires_target_id(self) -> None:
        with pytest.raises(ValidationError):
            MappingSyncOperation(
                op="upsert",
                key="A",
                target_id=None,
                expected_row_present=True,
                expected_saved_id=1,
            )

    def test_upsert_requires_matching_expected_saved_id(self) -> None:
        with pytest.raises(ValidationError):
            MappingSyncOperation(
                op="upsert",
                key="A",
                target_id=5,
                expected_row_present=True,
                expected_saved_id=6,
            )

    def test_delete_rejects_target_id(self) -> None:
        with pytest.raises(ValidationError):
            MappingSyncOperation(
                op="delete",
                key="A",
                target_id=5,
                expected_row_present=False,
                expected_saved_id=None,
            )

    def test_delete_rejects_expected_saved_id(self) -> None:
        with pytest.raises(ValidationError):
            MappingSyncOperation(
                op="delete",
                key="A",
                target_id=None,
                expected_row_present=True,
                expected_saved_id=5,
            )

    def test_duplicate_operation_keys_are_rejected(self) -> None:
        with pytest.raises(ValidationError, match="duplicate keys"):
            MappingSyncPending(
                project="test_project",
                entity="site",
                storage_kind="inline",
                local_key="site_code",
                public_id="site_id",
                operations=[
                    MappingSyncOperation(
                        op="upsert",
                        key="A",
                        target_id=1,
                        expected_row_present=True,
                        expected_saved_id=1,
                    ),
                    MappingSyncOperation(
                        op="upsert",
                        key="A",
                        target_id=2,
                        expected_row_present=True,
                        expected_saved_id=2,
                    ),
                ],
                expected_row_version="rows-v1",
                expected_sidecar_version="sidecar-v1",
            )

    def test_empty_local_key_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            MappingSyncPending(
                project="test_project",
                entity="site",
                storage_kind="inline",
                local_key=[],
                public_id="site_id",
                expected_row_version="rows-v1",
                expected_sidecar_version="sidecar-v1",
            )

    def test_ineligible_change_set_cannot_build_pending(self) -> None:
        change_set = FixedRowChangeSet(entity_name="site", eligible=False)
        with pytest.raises(ValueError, match="ineligible"):
            _to_pending(change_set)
