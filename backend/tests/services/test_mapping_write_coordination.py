"""Tests for serialized mapping-sidecar writers."""

from threading import Event, Lock, Thread, current_thread
from types import SimpleNamespace
from typing import Any

from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.services.mapping_service import MappingService
from src.model import TableConfig
from src.reconciliation.mapping_manager import MappingManager


class _ObservedLock:
    """Expose lock acquisition attempts to a deterministic writer test."""

    def __init__(self, second_attempted: Event) -> None:
        self._lock = Lock()
        self._second_attempted = second_attempted

    def __enter__(self) -> "_ObservedLock":
        if current_thread().name == "writer-two":
            self._second_attempted.set()
        self._lock.acquire()
        return self

    def __exit__(self, *_args: Any) -> None:
        self._lock.release()


def test_mapping_services_serialize_sidecar_updates(tmp_path, monkeypatch) -> None:
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    project_file = project_dir / "shapeshifter.yml"
    project_file.write_text("metadata:\n  type: shapeshifter-project\n", encoding="utf-8")

    second_lock_attempted = Event()
    first_snapshot_loaded = Event()
    second_snapshot_loaded = Event()
    allow_first_save = Event()
    lock = _ObservedLock(second_lock_attempted)
    table = TableConfig(
        entities_cfg={
            "site": {
                "type": "fixed",
                "public_id": "site_id",
                "keys": ["site_code"],
                "columns": ["system_id", "site_id", "site_code"],
                "values": [[1, 10, "A"]],
            }
        },
        entity_name="site",
    )
    project_service = SimpleNamespace(
        _get_lock=lambda _project_name: lock,
        load_project=lambda _project_name: SimpleNamespace(filename=str(project_file)),
    )
    first_service = MappingService(project_service)
    second_service = MappingService(project_service)
    original_load_snapshot = MappingManager.load_snapshot

    def controlled_load_snapshot(manager: MappingManager, path: str):
        snapshot = original_load_snapshot(manager, path)
        if current_thread().name == "writer-one":
            first_snapshot_loaded.set()
            assert allow_first_save.wait(timeout=5)
        elif current_thread().name == "writer-two":
            second_snapshot_loaded.set()
        return snapshot

    def write_link(service: MappingService, key: str, target_id: int) -> None:
        service.put_link("test_project", "site", key, target_id=target_id, created_by="test")

    monkeypatch.setattr(ProjectMapper, "to_core", lambda _project: SimpleNamespace(get_table=lambda _name: table))
    monkeypatch.setattr(MappingManager, "load_snapshot", controlled_load_snapshot)

    first_thread = Thread(target=write_link, args=(first_service, "A", 101), name="writer-one")
    second_thread = Thread(target=write_link, args=(second_service, "B", 202), name="writer-two")
    first_thread.start()
    assert first_snapshot_loaded.wait(timeout=5)
    second_thread.start()
    assert second_lock_attempted.wait(timeout=5)
    assert not second_snapshot_loaded.is_set()

    allow_first_save.set()
    first_thread.join(timeout=5)
    second_thread.join(timeout=5)

    assert not first_thread.is_alive()
    assert not second_thread.is_alive()
    assert second_snapshot_loaded.is_set()

    catalog = MappingManager().load_snapshot(project_file).catalog
    assert catalog.entities["site"].links["A"].target_id == 101
    assert catalog.entities["site"].links["B"].target_id == 202
