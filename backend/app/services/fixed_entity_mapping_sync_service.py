"""Apply prepared fixed-row mapping changes to a versioned sidecar snapshot."""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from src.reconciliation.fixed_entity_mapping_changes import FixedRowChangeSet, apply_fixed_row_change_set
from src.reconciliation.mapping_manager import MappingManager, MappingSnapshot


@dataclass(frozen=True)
class FixedEntityMappingSyncResult:
    """Internal result for one successful row-to-sidecar synchronization."""

    change_set: FixedRowChangeSet
    row_version: str
    sidecar_version: str
    changed: bool


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
    ) -> FixedEntityMappingSyncResult:
        """Apply exact operations and save only when the catalog changes."""
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

        sidecar_version = self.manager.save(snapshot.catalog, project_path, expected_version=snapshot.content_version)
        return FixedEntityMappingSyncResult(
            change_set=change_set,
            row_version=row_version,
            sidecar_version=sidecar_version,
            changed=True,
        )
