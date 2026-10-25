"""Pure fixed-entity mapping change calculation for save-time mapping sync.

Compares the previously saved fixed rows with the rows about to be written and
returns the mapping-link changes needed to keep the sidecar entry in step with
deliberate row edits. The module performs no file or sidecar writes.

Reuse policy:

- :func:`is_missing_fixed_entity_value` is the single "blank ID" rule for both
  snapshots.
- :func:`is_valid_fixed_entity_value` plus integer conversion validates a
  changed or new non-blank ID before it becomes a mapping target.
- :func:`encode_local_key` produces the key used to group rows and links.
- :func:`default_local_key` shares the ordered ``safe_keys`` default with the
  mapping API and materialization entry-creation paths.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Sequence

from src.reconciliation.mapping_model import EntityMapping, EntityType, Link, LinkSource, MappingCatalog, encode_local_key
from src.types.fixed_entity_types import is_missing_fixed_entity_value, is_valid_fixed_entity_value

FIXED_ENTITY_TYPE = "fixed"
MAPPING_TARGET_TYPE_NAME = "int"


class FixedEntityMappingChangeError(ValueError):
    """Raised when fixed-row mapping changes cannot be computed from saved rows.

    Carries the entity, field, row index, and column of the offending input so
    the inline path can report a schema error and the external path can report
    an unprocessable-values error.
    """

    def __init__(
        self,
        message: str,
        *,
        entity_name: str,
        field: str = "values",
        row_index: int | None = None,
        column: str | None = None,
    ) -> None:
        super().__init__(message)
        self.entity_name: str = entity_name
        self.field: str = field
        self.row_index: int | None = row_index
        self.column: str | None = column


def default_local_key(keys: str | Sequence[str] | None) -> str | list[str]:
    """Return the mapping default local key from ordered key columns.

    A single key column is returned as a scalar string; multiple key columns
    are returned as an ordered list preserving declaration order. An empty or
    absent key list returns an empty list so the caller can raise its own
    configuration error.
    """
    if keys is None:
        ordered: list[str] = []
    elif isinstance(keys, str):
        ordered = [keys]
    else:
        ordered = [key for key in keys if isinstance(key, str)]

    if len(ordered) == 1:
        return ordered[0]
    return ordered


def ordered_key_columns(keys: str | Sequence[str] | None) -> list[str]:
    """Return key columns as an ordered list, mirroring ``TableConfig.safe_keys``."""
    if keys is None:
        return []
    if isinstance(keys, str):
        return [keys]
    return [key for key in keys if isinstance(key, str)]


@dataclass(frozen=True)
class RowSnapshot:
    """Columns and rows for one fixed-entity values state."""

    columns: list[str]
    values: list[list[Any]]


@dataclass(frozen=True)
class LinkUpsert:
    """A mapping link to add or replace at one encoded key.

    Records the prior and new saved ID values and the existing link state so a
    later phase can apply or retry the exact change without re-reading rows.
    """

    key: str
    target_id: int
    previous_saved_id: Any | None
    new_saved_id: Any
    previous_link: Link | None
    row_index: int | None = None


@dataclass(frozen=True)
class LinkDelete:
    """A mapping link to remove at one encoded key.

    ``row_removed`` distinguishes a deleted row from a row whose ID became
    blank, so a later phase can re-check the affected key before applying the
    change.
    """

    key: str
    previous_saved_id: Any | None
    new_saved_id: Any | None
    row_removed: bool
    previous_link: Link | None
    row_index: int | None = None


@dataclass(frozen=True)
class FixedRowChangeSet:
    """Deterministic mapping changes produced from two saved-row snapshots.

    ``eligible`` is ``False`` when the entity is not a configured fixed entity,
    or when no sidecar entry can be created for it. ``proposed_entry`` is set
    only when a materialized fixed entity needs a new sidecar entry.
    """

    entity_name: str
    eligible: bool
    local_key: str | list[str] | None = None
    public_id: str | None = None
    proposed_entry: EntityMapping | None = None
    upserts: tuple[LinkUpsert, ...] = ()
    deletes: tuple[LinkDelete, ...] = ()

    @property
    def creates_entry(self) -> bool:
        """Return ``True`` when the change set proposes a new sidecar entry."""
        return self.proposed_entry is not None

    @property
    def is_empty(self) -> bool:
        """Return ``True`` when there is no work to apply."""
        return not self.creates_entry and not self.upserts and not self.deletes


def not_eligible_change_set(entity_name: str) -> FixedRowChangeSet:
    """Return a change set that carries no sync work for *entity_name*."""
    return FixedRowChangeSet(entity_name=entity_name, eligible=False)


def compute_fixed_row_change_set(
    *,
    entity_name: str,
    entity_type: str | None,
    materialized: bool,
    keys: str | Sequence[str] | None,
    public_id: str | None,
    existing_entry: EntityMapping | None,
    previous: RowSnapshot | None,
    current: RowSnapshot | None,
) -> FixedRowChangeSet:
    """Return the mapping changes implied by two saved-row snapshots.

    Only configured fixed entities qualify. A materialized fixed entity with no
    entry proposes a new entry using the ordered ``safe_keys`` default; if no
    business keys are configured, it returns no sync work. Any other fixed
    entity with no entry also returns no sync work. When an entry exists, its
    stored ``local_key`` and ``public_id`` remain authoritative.

    Raises:
        FixedEntityMappingChangeError: When a required stored column is absent,
            a key component is blank, two rows share an encoded key, or a
            proposed non-blank ID is not a valid integer mapping target.
    """
    if entity_type != FIXED_ENTITY_TYPE:
        return not_eligible_change_set(entity_name)

    proposed_entry: EntityMapping | None = None
    if existing_entry is None:
        if not materialized:
            return not_eligible_change_set(entity_name)
        key_columns = ordered_key_columns(keys)
        if not key_columns:
            return not_eligible_change_set(entity_name)
        if not public_id:
            raise FixedEntityMappingChangeError(
                f"Fixed entity '{entity_name}' has no public_id configuration for mapping operations.",
                entity_name=entity_name,
                field="public_id",
            )
        local_key: str | list[str] = default_local_key(key_columns)
        proposed_entry = EntityMapping(local_key=local_key, public_id=public_id, entity_type=EntityType.PRIMARY)
        existing_entry = proposed_entry

    local_key = existing_entry.local_key
    stored_public_id = existing_entry.public_id

    previous_index = build_row_index(entity_name, previous, local_key, stored_public_id)
    current_index = build_row_index(entity_name, current, local_key, stored_public_id)

    ordered_keys: list[str] = list(previous_index.keys())
    ordered_keys.extend(key for key in current_index if key not in previous_index)

    upserts: list[LinkUpsert] = []
    deletes: list[LinkDelete] = []

    for key in ordered_keys:
        link: Link | None = existing_entry.links.get(key)
        previous_row = previous_index.get(key)
        current_row = current_index.get(key)

        if current_row is None:
            # Row removed: drop any link at the key.
            if link is not None:
                deletes.append(
                    LinkDelete(
                        key=key,
                        previous_saved_id=_record_saved_id(previous_row.saved_id) if previous_row is not None else None,
                        new_saved_id=None,
                        row_removed=True,
                        previous_link=link,
                        row_index=previous_row.row_index if previous_row is not None else None,
                    )
                )
            continue

        if is_missing_fixed_entity_value(current_row.saved_id):
            # New ID is blank. A non-blank -> blank transition clears the link;
            # a blank -> blank save cannot express an intent to clear a link.
            if previous_row is not None and not is_missing_fixed_entity_value(previous_row.saved_id):
                if link is not None:
                    deletes.append(
                        LinkDelete(
                            key=key,
                            previous_saved_id=_record_saved_id(previous_row.saved_id),
                            new_saved_id=None,
                            row_removed=False,
                            previous_link=link,
                            row_index=current_row.row_index,
                        )
                    )
            continue

        if previous_row is not None and not is_missing_fixed_entity_value(previous_row.saved_id):
            if _saved_ids_equal(previous_row.saved_id, current_row.saved_id):
                # Unchanged key and ID: retain the existing link, but add one
                # when the saved ID has no link yet.
                if link is None:
                    target_id = _validate_target_id(entity_name, current_row.saved_id, stored_public_id)
                    upserts.append(
                        LinkUpsert(
                            key=key,
                            target_id=target_id,
                            previous_saved_id=_record_saved_id(previous_row.saved_id),
                            new_saved_id=current_row.saved_id,
                            previous_link=None,
                            row_index=current_row.row_index,
                        )
                    )
                continue

        # New row, previously blank row, or deliberate non-blank ID edit. A
        # deliberate edit replaces any link at the key with a manual link.
        if link is not None and link.source == LinkSource.MANUAL and link.target_id == as_mapping_target_id(current_row.saved_id):
            # Already-correct manual link: retain its metadata.
            continue

        target_id = _validate_target_id(entity_name, current_row.saved_id, stored_public_id)
        upserts.append(
            LinkUpsert(
                key=key,
                target_id=target_id,
                previous_saved_id=_record_saved_id(previous_row.saved_id) if previous_row is not None else None,
                new_saved_id=current_row.saved_id,
                previous_link=link,
                row_index=current_row.row_index,
            )
        )

    return FixedRowChangeSet(
        entity_name=entity_name,
        eligible=True,
        local_key=local_key,
        public_id=stored_public_id,
        proposed_entry=proposed_entry,
        upserts=tuple(upserts),
        deletes=tuple(deletes),
    )


def apply_fixed_row_change_set(
    catalog: MappingCatalog,
    change_set: FixedRowChangeSet,
    *,
    created_by: str,
    committed_at: datetime,
) -> bool:
    """Apply only the recorded affected-key changes to a mapping catalog."""
    if not change_set.eligible:
        return False

    entity = catalog.entities.get(change_set.entity_name)
    changed = False
    if entity is None and change_set.proposed_entry is not None:
        entity = change_set.proposed_entry.model_copy(deep=True)
        catalog.entities[change_set.entity_name] = entity
        changed = True

    if entity is None:
        return False

    for operation in change_set.deletes:
        if operation.key in entity.links:
            del entity.links[operation.key]
            changed = True

    for operation in change_set.upserts:
        existing_link = entity.links.get(operation.key)
        if existing_link is not None and existing_link.source == LinkSource.MANUAL and existing_link.target_id == operation.target_id:
            continue

        entity.links[operation.key] = Link(
            target_id=operation.target_id,
            source=LinkSource.MANUAL,
            created_at=committed_at,
            committed_at=committed_at,
            created_by=created_by,
        )
        changed = True

    return changed


@dataclass(frozen=True)
class IndexedRow:
    """A row's saved ID value and original row index."""

    saved_id: Any
    row_index: int


def build_row_index(
    entity_name: str,
    snapshot: RowSnapshot | None,
    local_key: str | list[str],
    public_id: str,
) -> dict[str, IndexedRow]:
    """Return a mapping of encoded key to saved ID for a non-empty snapshot.

    Shared by save-time change calculation and retry comparison so both use the
    same encoded-key and missing-value rules. Raises
    :class:`FixedEntityMappingChangeError` when a required stored column is
    absent, a key component is blank, or two rows share an encoded key.
    """
    if snapshot is None or not snapshot.values:
        return {}

    columns: list[str] = list(snapshot.columns)
    key_columns: list[str] = [local_key] if isinstance(local_key, str) else list(local_key)
    required_columns: list[str] = key_columns + [public_id]
    missing_columns: list[str] = [column for column in required_columns if column not in columns]
    if missing_columns:
        raise FixedEntityMappingChangeError(
            f"Fixed entity '{entity_name}' rows are missing stored mapping column(s) {missing_columns}; " f"available columns: {columns}",
            entity_name=entity_name,
            field="columns",
        )

    key_positions: list[int] = [columns.index(column) for column in key_columns]
    id_position: int = columns.index(public_id)

    index: dict[str, IndexedRow] = {}
    for row_index, row in enumerate(snapshot.values):
        if len(row) != len(columns):
            raise FixedEntityMappingChangeError(
                f"Fixed entity '{entity_name}' row {row_index} has {len(row)} values but {len(columns)} columns.",
                entity_name=entity_name,
                row_index=row_index,
            )

        key_values = [row[position] for position in key_positions]
        for column, value in zip(key_columns, key_values):
            if is_missing_fixed_entity_value(value):
                raise FixedEntityMappingChangeError(
                    f"Fixed entity '{entity_name}' row {row_index} has a missing key value for column '{column}'.",
                    entity_name=entity_name,
                    field="keys",
                    row_index=row_index,
                    column=column,
                )

        encoded_values = key_values[0] if isinstance(local_key, str) else key_values
        encoded_key: str = encode_local_key(local_key, encoded_values)
        existing = index.get(encoded_key)
        if existing is not None:
            raise FixedEntityMappingChangeError(
                f"Fixed entity '{entity_name}' rows {existing.row_index} and {row_index} share the same encoded key {encoded_key!r}.",
                entity_name=entity_name,
                field="keys",
                row_index=row_index,
            )

        index[encoded_key] = IndexedRow(saved_id=row[id_position], row_index=row_index)

    return index


def _record_saved_id(value: Any) -> Any:
    """Return the recorded saved-ID state, normalizing missing values to ``None``."""
    return None if is_missing_fixed_entity_value(value) else value


def as_mapping_target_id(value: Any) -> int | None:
    """Return an integer mapping target for *value*, or ``None`` when unusable."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _saved_ids_equal(previous_id: Any, current_id: Any) -> bool:
    """Return ``True`` when two non-blank saved IDs represent the same target."""
    previous_target = as_mapping_target_id(previous_id)
    current_target = as_mapping_target_id(current_id)
    if previous_target is not None and current_target is not None:
        return previous_target == current_target
    return previous_id == current_id


def _validate_target_id(entity_name: str, saved_id: Any, public_id: str) -> int:
    """Return the integer mapping target for *saved_id*, or raise when invalid."""
    if not is_valid_fixed_entity_value(saved_id, MAPPING_TARGET_TYPE_NAME):
        raise FixedEntityMappingChangeError(
            f"Fixed entity '{entity_name}' has invalid mapping target {saved_id!r} in column '{public_id}'; " f"expected an integer ID.",
            entity_name=entity_name,
            column=public_id,
        )
    return int(saved_id)
