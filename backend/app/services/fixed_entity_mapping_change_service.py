"""Read-only preparation of fixed-row mapping changes before rows are saved.

Compares the previously saved fixed rows with the rows about to be written and
returns the mapping changes a later phase will apply. It reads the mapping
sidecar entry but never writes the sidecar or the row files.

Two callers use this service:

- The inline entity-update flow compares the previously loaded project entity
  (before-image) with the normalized incoming fixed rows (after-image).
- The external values flow compares the previously stored ``@load:`` file with
  the normalized request rows before the file is written.

Both paths translate :class:`FixedEntityMappingChangeError` into their own
error type so existing HTTP status mapping is preserved.
"""

from __future__ import annotations

from typing import Any, Mapping

from backend.app.utils.fixed_schema import derive_fixed_schema
from src.reconciliation.fixed_entity_mapping_changes import (
    FixedRowChangeSet,
    RowSnapshot,
    compute_fixed_row_change_set,
    not_eligible_change_set,
)
from src.reconciliation.mapping_manager import MappingManager
from src.reconciliation.mapping_model import EntityMapping, MappingCatalog


class FixedEntityMappingChangeService:
    """Prepare fixed-row mapping change sets without writing any file."""

    def __init__(self, mapping_manager: MappingManager | None = None) -> None:
        """Initialize the service with an optional mapping manager."""
        self.manager: MappingManager = mapping_manager or MappingManager()

    def prepare_inline_change_set(
        self,
        *,
        entity_name: str,
        project_path: str | None,
        previous_entity: Mapping[str, Any] | None,
        current_entity: Mapping[str, Any],
        mapping_catalog: MappingCatalog | None = None,
    ) -> FixedRowChangeSet:
        """Prepare the change set for an inline fixed-row save.

        Returns a not-eligible change set for non-fixed entities and for
        ``@load:``-backed entities, whose rows are saved through the external
        values path. The before-image and after-image are aligned to the
        canonical fixed column order derived from their own entity config.
        """
        if not _is_fixed_entity(current_entity):
            return not_eligible_change_set(entity_name)

        current_values = _inline_values(current_entity)
        if current_values is None:
            return not_eligible_change_set(entity_name)

        previous_values = _inline_values(previous_entity)
        previous_columns, previous_rows = _align_inline_rows(previous_entity, previous_values)
        current_columns, current_rows = _align_inline_rows(current_entity, current_values)

        return self.compute_change_set(
            entity_name=entity_name,
            project_path=project_path,
            entity_config=current_entity,
            previous_columns=previous_columns,
            previous_values=previous_rows,
            current_columns=current_columns,
            current_values=current_rows,
            mapping_catalog=mapping_catalog,
        )

    def compute_change_set(
        self,
        *,
        entity_name: str,
        project_path: str | None,
        entity_config: Mapping[str, Any] | None,
        previous_columns: list[str] | None,
        previous_values: list[list[Any]] | None,
        current_columns: list[str] | None,
        current_values: list[list[Any]] | None,
        mapping_catalog: MappingCatalog | None = None,
    ) -> FixedRowChangeSet:
        """Return the mapping changes implied by two aligned row snapshots.

        The existing sidecar entry, when present, is read without being
        written so its stored ``local_key`` and ``public_id`` remain the
        authoritative mapping configuration.
        """
        config: Mapping[str, Any] = entity_config or {}
        existing_entry: EntityMapping | None = self._load_entry(project_path, entity_name, mapping_catalog)
        entity_type: str | None = config.get("type") if isinstance(config.get("type"), str) else None
        public_id: str | None = config.get("public_id") if isinstance(config.get("public_id"), str) else None

        return compute_fixed_row_change_set(
            entity_name=entity_name,
            entity_type=entity_type,
            materialized=_is_materialized(config),
            keys=config.get("keys"),
            public_id=public_id,
            existing_entry=existing_entry,
            previous=_snapshot(previous_columns, previous_values),
            current=_snapshot(current_columns, current_values),
        )

    def _load_entry(
        self,
        project_path: str | None,
        entity_name: str,
        mapping_catalog: MappingCatalog | None = None,
    ) -> EntityMapping | None:
        """Read the existing sidecar entry for *entity_name*, if any."""
        if mapping_catalog is not None:
            return mapping_catalog.entities.get(entity_name)
        if not isinstance(project_path, str) or not project_path:
            return None
        snapshot = self.manager.load_snapshot(project_path)
        return snapshot.catalog.entities.get(entity_name)


def get_fixed_entity_mapping_change_service() -> FixedEntityMappingChangeService:
    """Return a fixed-entity mapping change service instance."""
    return FixedEntityMappingChangeService()


def _is_fixed_entity(entity_config: Mapping[str, Any] | None) -> bool:
    """Return ``True`` when the entity config declares the fixed type."""
    return isinstance(entity_config, Mapping) and entity_config.get("type") == "fixed"


def _is_materialized(entity_config: Mapping[str, Any]) -> bool:
    """Return ``True`` when the entity config enables materialization."""
    materialized = entity_config.get("materialized")
    return isinstance(materialized, Mapping) and bool(materialized.get("enabled", False))


def _inline_values(entity_config: Mapping[str, Any] | None) -> list[list[Any]] | None:
    """Return inline row values when a fixed entity stores rows in the config."""
    if not isinstance(entity_config, Mapping):
        return None
    values = entity_config.get("values")
    if isinstance(values, list):
        return values
    return None


def _align_inline_rows(
    entity_config: Mapping[str, Any] | None,
    values: list[list[Any]] | None,
) -> tuple[list[str], list[list[Any]]]:
    """Return inline rows with their positional column names.

    Stored inline fixed rows use the canonical full order while the entity
    ``columns`` field lists produced data fields only. A row whose width equals
    the produced-field count is returned with those columns so the comparison
    can report the missing identity column.
    """
    config: Mapping[str, Any] = entity_config or {}
    fixed_schema = derive_fixed_schema(dict(config))
    if not fixed_schema:
        return [], []

    full_columns: list[str] = list(fixed_schema["full_columns"])
    if not values:
        return full_columns, []

    row_width: int = len(values[0])
    if row_width == len(full_columns):
        return full_columns, values

    produced_columns: list[str] = [column for column in (config.get("columns") or []) if isinstance(column, str)]
    if row_width == len(produced_columns):
        return produced_columns, values

    return full_columns, values


def _snapshot(columns: list[str] | None, values: list[list[Any]] | None) -> RowSnapshot | None:
    """Build a row snapshot, or ``None`` when no snapshot is supplied."""
    if columns is None and values is None:
        return None
    return RowSnapshot(columns=list(columns or []), values=list(values or []))
