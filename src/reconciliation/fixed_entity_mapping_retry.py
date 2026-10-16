"""Pure retry comparison for pending fixed-entity mapping changes.

When a fixed-row save persists its rows but the mapping sidecar write does not
happen, the save result records the exact operations together with each
affected key's post-save row state and pre-write link state. The client submits
that record to the retry operation. This module decides, from the current saved
rows and a fresh sidecar snapshot, which operations are already applied, which
can still be applied safely, and which affected keys changed and require review.

The module performs no file or sidecar writes and never infers a new change set
from the current rows. It shares the encoded-key and missing-value rules from
:mod:`src.reconciliation.fixed_entity_mapping_changes`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Sequence

from src.reconciliation.fixed_entity_mapping_changes import (
    FixedEntityMappingChangeError,
    IndexedRow,
    LinkDelete,
    LinkUpsert,
    RowSnapshot,
    as_mapping_target_id,
    build_row_index,
)
from src.reconciliation.mapping_model import EntityMapping, Link, LinkSource, MappingCatalog
from src.types.fixed_entity_types import is_missing_fixed_entity_value


@dataclass(frozen=True)
class FixedMappingRetryPlan:
    """Outcome of comparing recorded mapping operations with current state.

    ``conflict_keys`` holds affected keys whose saved row or link state no
    longer matches the recorded precondition. ``entry_conflict`` and
    ``config_conflict`` record an entry or stored-configuration mismatch that
    cannot be expressed as a link key. When no conflict is present, the
    remaining operations and optional entry creation describe the work to apply.
    """

    conflict_keys: tuple[str, ...] = ()
    entry_conflict: bool = False
    config_conflict: bool = False
    upserts_to_apply: tuple[LinkUpsert, ...] = ()
    deletes_to_apply: tuple[LinkDelete, ...] = ()
    create_entry: bool = False

    @property
    def has_conflicts(self) -> bool:
        """Return ``True`` when the retry must stop for review."""
        return bool(self.conflict_keys) or self.entry_conflict or self.config_conflict

    @property
    def is_no_op(self) -> bool:
        """Return ``True`` when every requested change is already present."""
        return not self.has_conflicts and not self.create_entry and not self.upserts_to_apply and not self.deletes_to_apply


def plan_fixed_entity_mapping_retry(
    *,
    entity_name: str,
    local_key: str | list[str],
    public_id: str,
    current_rows: RowSnapshot | None,
    catalog: MappingCatalog,
    upserts: Sequence[LinkUpsert],
    deletes: Sequence[LinkDelete],
    proposed_entry: EntityMapping | None,
) -> FixedMappingRetryPlan:
    """Decide which recorded mapping operations still need to be applied.

    Unrelated edits elsewhere in the row file or sidecar do not block the retry.
    Only affected-key differences produce conflict keys. Already-applied
    operations are dropped so a repeated retry does not write the sidecar again.
    """
    affected_keys: tuple[str, ...] = tuple(sorted({operation.key for operation in (*upserts, *deletes)}))
    entity: EntityMapping | None = catalog.entities.get(entity_name)

    entry_conflict: bool = False
    config_conflict: bool = False
    create_entry: bool = False

    if proposed_entry is not None:
        if entity is None:
            create_entry = True
        elif not _entry_matches(entity, proposed_entry):
            entry_conflict = True
    elif entity is None:
        # Operations expect an existing entry; a deleted entry needs review.
        config_conflict = True
    elif not _stored_config_matches(entity, local_key, public_id):
        config_conflict = True

    if entry_conflict or config_conflict:
        return FixedMappingRetryPlan(
            conflict_keys=affected_keys,
            entry_conflict=entry_conflict,
            config_conflict=config_conflict,
        )

    try:
        index: dict[str, IndexedRow] = build_row_index(entity_name, current_rows, local_key, public_id)
    except FixedEntityMappingChangeError:
        # Unusable current rows cannot be matched to the recorded preconditions.
        return FixedMappingRetryPlan(conflict_keys=affected_keys)

    links: dict[str, Link] = entity.links if entity is not None else {}
    conflicts: set[str] = set()
    upserts_to_apply: list[LinkUpsert] = []
    deletes_to_apply: list[LinkDelete] = []

    for delete in deletes:
        if not _row_matches_delete(index.get(delete.key), delete):
            conflicts.add(delete.key)
            continue
        current_link = links.get(delete.key)
        if current_link is None:
            # Already deleted; a repeated retry needs no further write.
            continue
        if not _link_matches(current_link, delete.previous_link):
            conflicts.add(delete.key)
            continue
        deletes_to_apply.append(delete)

    for upsert in upserts:
        if not _row_matches_upsert(index.get(upsert.key), upsert):
            conflicts.add(upsert.key)
            continue
        current_link = links.get(upsert.key)
        if current_link is not None and current_link.source == LinkSource.MANUAL and current_link.target_id == upsert.target_id:
            # Already applied; retain the existing link and its metadata.
            continue
        if not _link_matches(current_link, upsert.previous_link):
            conflicts.add(upsert.key)
            continue
        upserts_to_apply.append(upsert)

    if conflicts:
        return FixedMappingRetryPlan(conflict_keys=tuple(sorted(conflicts)))

    return FixedMappingRetryPlan(
        upserts_to_apply=tuple(upserts_to_apply),
        deletes_to_apply=tuple(deletes_to_apply),
        create_entry=create_entry,
    )


def _row_matches_delete(row: IndexedRow | None, delete: LinkDelete) -> bool:
    """Return ``True`` when the current saved row matches the recorded delete state."""
    if delete.row_removed:
        return row is None
    if row is None:
        return False
    return is_missing_fixed_entity_value(row.saved_id)


def _row_matches_upsert(row: IndexedRow | None, upsert: LinkUpsert) -> bool:
    """Return ``True`` when the current saved row matches the recorded post-write target."""
    if row is None:
        return False
    return as_mapping_target_id(row.saved_id) == upsert.target_id


def _link_matches(current: Link | None, previous: Link | None) -> bool:
    """Return ``True`` when the current link equals the recorded pre-write link."""
    if current is None or previous is None:
        return current is None and previous is None
    return _link_equal(current, previous)


def _link_equal(first: Link, second: Link) -> bool:
    """Return ``True`` when two links carry identical target, source, and metadata."""
    return (
        first.target_id == second.target_id
        and first.source == second.source
        and first.confidence == second.confidence
        and first.notes == second.notes
        and first.created_by == second.created_by
        and first.reviewed_by == second.reviewed_by
        and _datetime_key(first.created_at) == _datetime_key(second.created_at)
        and _datetime_key(first.committed_at) == _datetime_key(second.committed_at)
    )


def _datetime_key(value: datetime | None) -> str | None:
    """Return a comparable ISO string for a datetime, normalizing naive values to UTC."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _entry_matches(entity: EntityMapping, proposed: EntityMapping) -> bool:
    """Return ``True`` when an existing entry already matches the proposed entry."""
    return _local_key_equal(entity.local_key, proposed.local_key) and entity.public_id == proposed.public_id


def _stored_config_matches(entity: EntityMapping, local_key: str | list[str], public_id: str) -> bool:
    """Return ``True`` when the stored mapping configuration matches the pending request."""
    return _local_key_equal(entity.local_key, local_key) and entity.public_id == public_id


def _local_key_equal(first: Any, second: Any) -> bool:
    """Return ``True`` when two local-key declarations describe the same ordered columns."""
    return _normalized_key(first) == _normalized_key(second)


def _normalized_key(value: Any) -> list[Any]:
    """Normalize a single-column key to a one-item list for comparison."""
    if isinstance(value, str):
        return [value]
    return list(value or [])
