"""Tests for applying prepared fixed-row mapping changes."""

from datetime import datetime, timezone

from backend.app.services.fixed_entity_mapping_sync_service import FixedEntityMappingSyncService
from src.reconciliation.fixed_entity_mapping_changes import FixedRowChangeSet, LinkUpsert
from src.reconciliation.mapping_manager import MISSING_CONTENT_VERSION, MappingManager
from src.reconciliation.mapping_model import EntityMapping, EntityType, Link, LinkSource, MappingCatalog, Metadata

CREATED = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _catalog() -> MappingCatalog:
    return MappingCatalog(metadata=Metadata(project="test", created_at=CREATED, updated_at=CREATED))


def test_sync_service_applies_recorded_upsert_and_returns_versions(tmp_path) -> None:
    project_dir = tmp_path / "test"
    project_dir.mkdir()
    manager = MappingManager()
    snapshot = manager.load_snapshot(project_dir)
    entry = EntityMapping(local_key="code", public_id="target_id", entity_type=EntityType.PRIMARY)
    changes = FixedRowChangeSet(
        entity_name="sample",
        eligible=True,
        local_key="code",
        public_id="target_id",
        proposed_entry=entry,
        upserts=(
            LinkUpsert(
                key="A",
                target_id=0,
                previous_saved_id=None,
                new_saved_id=0,
                previous_link=None,
            ),
        ),
    )

    result = FixedEntityMappingSyncService(manager).apply_change_set(
        change_set=changes,
        snapshot=snapshot,
        project_path=project_dir,
        row_version="rows-v1",
        created_by="test-user",
    )

    saved_snapshot = manager.load_snapshot(project_dir)
    link = saved_snapshot.catalog.entities["sample"].links["A"]
    assert result.changed is True
    assert result.row_version == "rows-v1"
    assert result.sidecar_version == saved_snapshot.content_version
    assert result.sidecar_version != MISSING_CONTENT_VERSION
    assert link.target_id == 0
    assert link.source == LinkSource.MANUAL
    assert link.created_by == "test-user"


def test_sync_service_noop_preserves_sidecar_bytes_and_metadata(tmp_path) -> None:
    project_dir = tmp_path / "test"
    project_dir.mkdir()
    manager = MappingManager()
    catalog = _catalog()
    catalog.entities["sample"] = EntityMapping(local_key="code", public_id="target_id", entity_type=EntityType.PRIMARY)
    catalog.entities["sample"].links["A"] = Link(
        target_id=5,
        source=LinkSource.MANUAL,
        created_at=CREATED,
        committed_at=CREATED,
        created_by="original",
    )
    manager.save(catalog, project_dir)
    before_bytes = (project_dir / "test-mapping.yml").read_bytes()
    before_updated_at = catalog.metadata.updated_at
    snapshot = manager.load_snapshot(project_dir)
    changes = FixedRowChangeSet(entity_name="sample", eligible=True)

    result = FixedEntityMappingSyncService(manager).apply_change_set(
        change_set=changes,
        snapshot=snapshot,
        project_path=project_dir,
        row_version="rows-v2",
        created_by="test-user",
    )

    assert result.changed is False
    assert result.sidecar_version == snapshot.content_version
    assert (project_dir / "test-mapping.yml").read_bytes() == before_bytes
    assert snapshot.catalog.metadata.updated_at == before_updated_at
