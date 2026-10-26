"""Tests for the fixed-entity mapping retry service.

Covers applying remaining changes, no-op repeated retries, unrelated edits,
affected-key conflicts, one version race, and both inline and external storage.
"""

from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from unittest.mock import Mock

import pandas as pd
import pytest
import yaml

from backend.app.exceptions import ResourceConflictError, ValidationError
from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.models.mapping_sync import MappingSyncPending
from backend.app.services.fixed_entity_mapping_retry_service import FixedEntityMappingRetryService
from backend.app.services.fixed_entity_mapping_sync_service import FixedEntityMappingSyncService
from src.reconciliation.fixed_entity_mapping_changes import FixedRowChangeSet, LinkUpsert
from src.reconciliation.mapping_manager import MappingManager, MappingVersionConflictError
from src.reconciliation.mapping_model import EntityMapping, EntityType, Link

CREATED = datetime(2026, 1, 1, tzinfo=timezone.utc)
PROJECT = "test_project"
ENTITY = "site"
FULL_COLUMNS = ["system_id", "site_id", "site_code", "name"]


class _RacingManager(MappingManager):
    """Mapping manager that reports one stale-version conflict before saving."""

    def __init__(self, failures: int = 1) -> None:
        super().__init__()
        self.remaining = failures

    def save(self, catalog, project_path, expected_version=None):
        if self.remaining > 0:
            self.remaining -= 1
            raise MappingVersionConflictError("sidecar changed under the writer")
        return super().save(catalog, project_path, expected_version=expected_version)


class _FailingManager(MappingManager):
    """Mapping manager whose save always fails with a write error."""

    def save(self, catalog, project_path, expected_version=None):
        raise OSError("sidecar write failed")


def _sidecar_path(tmp_path: Path) -> Path:
    return tmp_path / f"{tmp_path.name}-mapping.yml"


def _write_sidecar(tmp_path: Path, links: dict[str, dict], *, local_key="site_code", public_id="site_id") -> None:
    sidecar = {
        "version": "2.0",
        "metadata": {
            "project": PROJECT,
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        },
        "entities": {
            ENTITY: {
                "local_key": local_key,
                "public_id": public_id,
                "entity_type": "primary",
                "links": links,
            }
        },
    }
    _sidecar_path(tmp_path).write_text(yaml.safe_dump(sidecar), encoding="utf-8")


def _link_dict(target_id: int, source: str = "manual") -> dict:
    return {
        "target_id": target_id,
        "source": source,
        "created_at": "2026-01-01T00:00:00+00:00",
        "committed_at": "2026-01-01T00:00:00+00:00",
        "created_by": "tester",
    }


def _inline_entity(values: list[list[object]], *, entity_type: str = "fixed") -> dict:
    return {
        "type": entity_type,
        "public_id": "site_id",
        "keys": ["site_code"],
        "columns": ["site_code", "name"],
        "values": values,
    }


def _mock_project_service(tmp_path: Path, entity_data: dict) -> Mock:
    config_path = tmp_path / "shapeshifter.yml"
    config_path.write_text("metadata:\n  type: shapeshifter\n", encoding="utf-8")
    service = Mock()
    service._get_lock.return_value = Lock()
    service.get_entity_by_name.return_value = entity_data
    project = Mock()
    project.filename = str(config_path)
    project.folder = tmp_path
    service.load_project.return_value = project
    return service


def _upsert_pending(
    target_id: int,
    *,
    storage_kind: str = "inline",
    key: str = "A",
    prior: Link | None = None,
    create_entry: bool = False,
) -> MappingSyncPending:
    proposed_entry = None
    if create_entry:
        proposed_entry = EntityMapping(local_key="site_code", public_id="site_id", entity_type=EntityType.PRIMARY)
    change_set = FixedRowChangeSet(
        entity_name=ENTITY,
        eligible=True,
        local_key="site_code",
        public_id="site_id",
        proposed_entry=proposed_entry,
        upserts=(LinkUpsert(key=key, target_id=target_id, previous_saved_id=None, new_saved_id=target_id, previous_link=prior),),
    )
    return ProjectMapper.fixed_change_set_to_pending(
        change_set,
        project=PROJECT,
        entity=ENTITY,
        storage_kind=storage_kind,
        row_version="rows-v1",
        sidecar_version="sidecar-v1",
    )


def _make_service(tmp_path: Path, entity_data: dict, *, manager: MappingManager | None = None) -> FixedEntityMappingRetryService:
    manager = manager or MappingManager()
    sync_service = FixedEntityMappingSyncService(manager)
    return FixedEntityMappingRetryService(
        _mock_project_service(tmp_path, entity_data),
        mapping_manager=manager,
        sync_service=sync_service,
    )


class TestInlineRetry:
    def test_applies_remaining_upsert(self, tmp_path: Path) -> None:
        _write_sidecar(tmp_path, {})
        service = _make_service(tmp_path, _inline_entity([[1, 10, "A", "Alpha"]]))

        result = service.retry(PROJECT, ENTITY, _upsert_pending(10))

        assert result.status == "applied"
        assert result.changed is True
        sidecar = yaml.safe_load(_sidecar_path(tmp_path).read_text(encoding="utf-8"))
        assert sidecar["entities"][ENTITY]["links"]["A"]["target_id"] == 10
        assert sidecar["entities"][ENTITY]["links"]["A"]["source"] == "manual"

    def test_repeated_retry_is_noop_and_byte_identical(self, tmp_path: Path) -> None:
        _write_sidecar(tmp_path, {})
        service = _make_service(tmp_path, _inline_entity([[1, 10, "A", "Alpha"]]))
        pending = _upsert_pending(10)

        first = service.retry(PROJECT, ENTITY, pending)
        after_first = _sidecar_path(tmp_path).read_bytes()
        second = service.retry(PROJECT, ENTITY, pending)

        assert first.changed is True
        assert second.status == "noop"
        assert second.changed is False
        assert _sidecar_path(tmp_path).read_bytes() == after_first

    def test_unrelated_edits_do_not_block(self, tmp_path: Path) -> None:
        _write_sidecar(tmp_path, {"Other": _link_dict(999, source="import")})
        entity = _inline_entity([[1, 10, "A", "Alpha"], [2, 55, "Other", "Renamed"]])
        service = _make_service(tmp_path, entity)

        result = service.retry(PROJECT, ENTITY, _upsert_pending(10))

        assert result.changed is True
        sidecar = yaml.safe_load(_sidecar_path(tmp_path).read_text(encoding="utf-8"))
        assert sidecar["entities"][ENTITY]["links"]["A"]["target_id"] == 10
        assert sidecar["entities"][ENTITY]["links"]["Other"]["target_id"] == 999

    def test_affected_row_edit_returns_conflict(self, tmp_path: Path) -> None:
        _write_sidecar(tmp_path, {})
        service = _make_service(tmp_path, _inline_entity([[1, 99, "A", "Alpha"]]))

        with pytest.raises(ResourceConflictError) as excinfo:
            service.retry(PROJECT, ENTITY, _upsert_pending(10))

        assert excinfo.value.context["changed_keys"] == ["A"]
        assert yaml.safe_load(_sidecar_path(tmp_path).read_text(encoding="utf-8"))["entities"][ENTITY]["links"] == {}

    def test_version_race_is_retried_once(self, tmp_path: Path) -> None:
        _write_sidecar(tmp_path, {"Other": _link_dict(1, source="import")})
        manager = _RacingManager(failures=1)
        service = _make_service(tmp_path, _inline_entity([[1, 10, "A", "Alpha"]]), manager=manager)

        result = service.retry(PROJECT, ENTITY, _upsert_pending(10))

        assert result.changed is True
        sidecar = yaml.safe_load(_sidecar_path(tmp_path).read_text(encoding="utf-8"))
        assert sidecar["entities"][ENTITY]["links"]["A"]["target_id"] == 10
        assert sidecar["entities"][ENTITY]["links"]["Other"]["source"] == "import"

    def test_non_fixed_entity_is_rejected(self, tmp_path: Path) -> None:
        _write_sidecar(tmp_path, {})
        service = _make_service(tmp_path, _inline_entity([[1, 10, "A", "Alpha"]], entity_type="entity"))

        with pytest.raises(ValidationError):
            service.retry(PROJECT, ENTITY, _upsert_pending(10))

    def test_missing_entry_creates_entry(self, tmp_path: Path) -> None:
        config_path = tmp_path / "shapeshifter.yml"
        config_path.write_text("metadata:\n  type: shapeshifter\n", encoding="utf-8")
        entity = _inline_entity([[1, 10, "A", "Alpha"]])
        entity["materialized"] = {"enabled": True}
        service = _make_service(tmp_path, entity)
        pending = _upsert_pending(10, create_entry=True)

        result = service.retry(PROJECT, ENTITY, pending)

        assert result.changed is True
        sidecar = yaml.safe_load(_sidecar_path(tmp_path).read_text(encoding="utf-8"))
        assert sidecar["entities"][ENTITY]["links"]["A"]["target_id"] == 10


class TestExternalRetry:
    def test_applies_remaining_upsert_for_external_rows(self, tmp_path: Path) -> None:
        config_path = tmp_path / "shapeshifter.yml"
        config_path.write_text("metadata:\n  type: shapeshifter\n", encoding="utf-8")
        entity = {
            "type": "fixed",
            "public_id": "site_id",
            "keys": ["site_code"],
            "columns": ["site_code", "name"],
            "values": "@load:materialized/site.parquet",
            "materialized": {"enabled": True},
        }
        materialized = tmp_path / "materialized"
        materialized.mkdir()
        pd.DataFrame({"system_id": [1], "site_id": [10], "site_code": ["A"], "name": ["Alpha"]}).to_parquet(
            materialized / "site.parquet", index=False
        )
        _write_sidecar(tmp_path, {})
        service = _make_service(tmp_path, entity)

        result = service.retry(PROJECT, ENTITY, _upsert_pending(10, storage_kind="external"))

        assert result.changed is True
        sidecar = yaml.safe_load(_sidecar_path(tmp_path).read_text(encoding="utf-8"))
        assert sidecar["entities"][ENTITY]["links"]["A"]["target_id"] == 10

    def test_external_storage_kind_mismatch_is_a_conflict(self, tmp_path: Path) -> None:
        _write_sidecar(tmp_path, {})
        service = _make_service(tmp_path, _inline_entity([[1, 10, "A", "Alpha"]]))

        with pytest.raises(ResourceConflictError) as excinfo:
            service.retry(PROJECT, ENTITY, _upsert_pending(10, storage_kind="external"))

        assert excinfo.value.context["config_conflict"] is True
