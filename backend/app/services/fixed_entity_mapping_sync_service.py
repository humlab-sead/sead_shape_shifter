"""Apply prepared fixed-row mapping changes to a versioned sidecar snapshot."""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

from src.reconciliation.fixed_entity_mapping_changes import FixedRowChangeSet, apply_fixed_row_change_set
from src.reconciliation.mapping_manager import MappingManager, MappingSnapshot, MappingVersionConflictError


@dataclass(frozen=True)
class FixedEntityMappingSyncResult:
    """Internal result for one row-to-sidecar synchronization attempt.

    ``error`` is set only when rows were already persisted and the sidecar write
    did not happen. ``version_conflict`` distinguishes a stale expected version
    from a general write failure so the retry operation can re-read and recheck.
    """

    change_set: FixedRowChangeSet
    row_version: str
    sidecar_version: str
    changed: bool
    error: str | None = None
    version_conflict: bool = False

    @property
    def succeeded(self) -> bool:
        """Return ``True`` when no post-row sidecar write failure occurred."""
        return self.error is None


class FixedEntityMappingSyncService:
    """Apply recorded mapping operations without acquiring the project lock."""

    def __init__(self, mapping_manager: MappingManager | None = None) -> None:
        """Initialize with an optional shared mapping manager."""
        self.manager = mapping_manager or MappingManager()

    def load_snapshot(self, project_path: str | Path) -> MappingSnapshot:
        """Read a fresh sidecar snapshot for a caller that holds the project lock."""
        return self.manager.load_snapshot(project_path)

    def apply_change_set(
        self,
        *,
        change_set: FixedRowChangeSet,
        snapshot: MappingSnapshot,
        project_path: str | Path,
        row_version: str,
        created_by: str,
        raise_on_error: bool = False,
    ) -> FixedEntityMappingSyncResult:
        """Apply exact operations and save only when the catalog changes.

        When *raise_on_error* is ``False`` (the save path), a sidecar write
        failure after the rows are persisted returns a result with ``error`` set
        instead of raising. When it is ``True`` (the retry path), the write
        failure is re-raised so the caller can re-read and recheck.
        """
        if change_set.is_empty:
            return FixedEntityMappingSyncResult(
                change_set=change_set,
                row_version=row_version,
                sidecar_version=snapshot.content_version,
                changed=False,
            )

        changed = apply_fixed_row_change_set(
            snapshot.catalog,
            change_set,
            created_by=created_by,
            committed_at=datetime.now(timezone.utc),
        )
        if not changed:
            return FixedEntityMappingSyncResult(
                change_set=change_set,
                row_version=row_version,
                sidecar_version=snapshot.content_version,
                changed=False,
            )

        try:
            sidecar_version = self.manager.save(snapshot.catalog, project_path, expected_version=snapshot.content_version)
        except MappingVersionConflictError as exc:
            if raise_on_error:
                raise
            logger.warning(f"Mapping sidecar version conflict after row save: {exc}")
            return FixedEntityMappingSyncResult(
                change_set=change_set,
                row_version=row_version,
                sidecar_version=snapshot.content_version,
                changed=False,
                error=str(exc),
                version_conflict=True,
            )
        except OSError as exc:
            if raise_on_error:
                raise
            logger.error(f"Mapping sidecar write failed after row save: {exc}")
            return FixedEntityMappingSyncResult(
                change_set=change_set,
                row_version=row_version,
                sidecar_version=snapshot.content_version,
                changed=False,
                error=str(exc),
            )

        return FixedEntityMappingSyncResult(
            change_set=change_set,
            row_version=row_version,
            sidecar_version=sidecar_version,
            changed=True,
        )
