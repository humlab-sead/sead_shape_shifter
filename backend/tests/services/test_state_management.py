"""Tests for ProjectService state management robustness.

Tests cover the Phase 1 fixes:
- Per-project locking infrastructure
- Copy-on-read behavior (mutation isolation)
- Save verification (_verify_save)
- Cache invalidation (_invalidate_all_caches)
- Concurrency regression tests for the original bugs
"""

import threading
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import yaml

from backend.app.models.project import Project, ProjectMetadata
from backend.app.services.project_service import ProjectService

# pylint: disable=redefined-outer-name, unused-argument, broad-exception-caught


# ─── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    """Create temporary project directory."""
    project_dir = tmp_path / "projects"
    project_dir.mkdir()
    return project_dir


@pytest.fixture
def mock_state() -> MagicMock:
    """Create mock ApplicationStateManager."""
    state = MagicMock()
    state.get = MagicMock(return_value=None)  # No cache by default
    state.update = MagicMock()
    state.activate = MagicMock()
    state.invalidate = MagicMock()
    state.get_active_metadata = MagicMock(return_value=ProjectMetadata(name="", entity_count=0, created_at=0, modified_at=0, is_valid=True))
    return state


@pytest.fixture
def service(temp_dir: Path, mock_state: MagicMock) -> ProjectService:
    """Create ProjectService with temp dir and mock state."""
    with patch("backend.app.services.project_service.settings") as mock_settings:
        mock_settings.PROJECTS_DIR = temp_dir
        svc = ProjectService(projects_dir=temp_dir, state=mock_state)
        return svc


@pytest.fixture(autouse=True)
def reset_locks():
    """Reset class-level locks between tests to avoid contamination."""
    original_locks = ProjectService._project_locks.copy()
    yield
    ProjectService._project_locks = original_locks


def _write_project_yaml(project_dir: Path, name: str, entities: dict[str, Any]) -> Path:
    """Write a project YAML file to disk."""
    file_path = project_dir / name / "shapeshifter.yml"
    data = {
        "metadata": {
            "type": "shapeshifter-project",
            "name": name,
            "description": f"Test project {name}",
            "version": "1.0.0",
        },
        "entities": entities,
        "options": {},
    }
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f)
    return file_path


def _make_project(name: str, entities: dict[str, Any] | None = None) -> Project:
    """Create an in-memory Project model."""
    return Project(
        metadata=ProjectMetadata(
            name=name,
            description=f"Test project {name}",
            version="1.0.0",
            entity_count=len(entities or {}),
            created_at=0,
            modified_at=0,
            is_valid=True,
            type="shapeshifter-project",
        ),
        entities=entities or {},
        options={},
    )


# ─── Per-Project Locking ────────────────────────────────────────────────────


class TestProjectLocking:
    """Test the per-project locking infrastructure."""

    def test_get_lock_returns_same_lock_for_same_project(self):
        """_get_lock returns the same Lock instance for the same project name."""
        lock1 = ProjectService._get_lock("project_a")
        lock2 = ProjectService._get_lock("project_a")
        assert lock1 is lock2

    def test_get_lock_returns_different_locks_for_different_projects(self):
        """_get_lock returns different Lock instances for different project names."""
        lock_a = ProjectService._get_lock("project_a")
        lock_b = ProjectService._get_lock("project_b")
        assert lock_a is not lock_b

    def test_remove_lock_cleans_up(self):
        """_remove_lock removes the lock entry from the dict."""
        ProjectService._get_lock("to_delete")
        assert "to_delete" in ProjectService._project_locks

        ProjectService._remove_lock("to_delete")
        assert "to_delete" not in ProjectService._project_locks

    def test_remove_nonexistent_lock_is_noop(self):
        """_remove_lock for unknown project does not raise."""
        ProjectService._remove_lock("nonexistent")  # Should not raise

    def test_get_lock_after_remove_creates_new_lock(self):
        """After removing a lock, _get_lock creates a fresh one."""
        lock1 = ProjectService._get_lock("project_c")
        ProjectService._remove_lock("project_c")
        lock2 = ProjectService._get_lock("project_c")
        assert lock1 is not lock2

    def test_get_lock_is_thread_safe(self):
        """Multiple threads calling _get_lock for the same project get the same lock."""
        results = []
        barrier = threading.Barrier(10)

        def get_lock():
            barrier.wait()
            results.append(ProjectService._get_lock("concurrent_project"))

        threads = [threading.Thread(target=get_lock) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All threads should have gotten the same lock
        assert all(r is results[0] for r in results)


# ─── Copy-on-Read ────────────────────────────────────────────────────────────


class TestCopyOnRead:
    """Test that load_project returns independent deep copies."""

    def test_cache_hit_returns_deep_copy(self, service, mock_state, temp_dir):
        """When loading from cache, modifying one copy does not affect the other."""
        cached = _make_project("test", {"entity_a": {"source": "table_a"}})
        mock_state.get.return_value = cached

        copy1 = service.load_project("test")
        copy2 = service.load_project("test")

        # Verify they are different objects
        assert copy1 is not copy2
        assert copy1 is not cached

        # Mutate copy1
        copy1.entities["new_entity"] = {"source": "new_table"}

        # copy2 and original should be unaffected
        assert "new_entity" not in copy2.entities
        assert "new_entity" not in cached.entities

    def test_cache_hit_preserves_entity_data(self, service, mock_state):
        """Deep copy preserves all entity data correctly."""
        entities = {
            "sample": {
                "source": "samples",
                "columns": ["id", "name", "value"],
                "foreign_keys": [{"entity": "parent", "local_keys": ["parent_id"], "remote_keys": ["id"]}],
            }
        }
        cached: Project = _make_project("test", entities)
        mock_state.get.return_value = cached

        loaded = service.load_project("test")

        assert loaded.entities["sample"]["source"] == "samples"
        assert loaded.entities["sample"]["columns"] == ["id", "name", "value"]
        assert loaded.entities["sample"]["foreign_keys"][0]["entity"] == "parent"

    def test_disk_load_not_affected_by_copy_on_read(self, service, mock_state, temp_dir: Path):
        """When loading from disk (cache miss), returns original load."""
        name: str = "from_disk"
        _write_project_yaml(temp_dir, name, {"entity_x": {"source": "table_x"}})
        mock_state.get.return_value = None  # Cache miss

        project = service.load_project("from_disk")

        assert "entity_x" in project.entities


# ─── Save Verification ──────────────────────────────────────────────────────


class TestVerifySave:
    """Test the _verify_save read-back verification."""

    def test_verify_save_passes_on_matching_entities(self, service, temp_dir):
        """_verify_save succeeds when disk matches expected entities."""
        _write_project_yaml(temp_dir, "good", {"a": {}, "b": {}, "c": {}})
        file_path = temp_dir / "good.yml"

        # Should not raise or log error
        service._verify_save("good", ["a", "b", "c"], file_path, "test-corr")

    def test_verify_save_detects_missing_entities(self, service, temp_dir):
        """_verify_save logs an error when disk has fewer entities than expected."""
        file_path = _write_project_yaml(temp_dir, "bad", {"a": {}})

        # Should log error but not raise (it's a defensive check)
        with patch("backend.app.services.project_service.logger") as mock_logger:
            service._verify_save("bad", ["a", "b", "c"], file_path, "test-corr")
            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args
            assert "SAVE VERIFICATION FAILED" in call_args[0][0]

    def test_verify_save_skips_empty_projects(self, service, temp_dir):
        """_verify_save skips verification for projects with no entities."""
        with patch("backend.app.services.project_service.logger") as mock_logger:
            service._verify_save("empty", [], temp_dir / "empty.yml", "test-corr")
            mock_logger.error.assert_not_called()

    def test_verify_save_handles_missing_file_gracefully(self, service, temp_dir):
        """_verify_save handles file read errors without crashing."""
        nonexistent = temp_dir / "nonexistent.yml"

        with patch("backend.app.services.project_service.logger") as mock_logger:
            service._verify_save("missing", ["a"], nonexistent, "test-corr")
            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args
            assert "verification read-back failed" in call_args[0][0]


# ─── Cache Invalidation ─────────────────────────────────────────────────────


class TestInvalidateAllCaches:
    """Test _invalidate_all_caches clears all cache layers."""

    def test_invalidates_application_state(self, service, mock_state):
        """_invalidate_all_caches calls state.invalidate."""
        service._invalidate_all_caches("test_project", "test-corr")
        mock_state.invalidate.assert_called_once_with("test_project")

    def test_invalidates_shapeshift_caches(self, service, mock_state):
        """_invalidate_all_caches clears ShapeShiftCache and ShapeShiftProjectCache."""
        mock_shapeshift_service = MagicMock()
        mock_cache = MagicMock()
        mock_project_cache = MagicMock()
        mock_shapeshift_service.cache = mock_cache
        mock_shapeshift_service.project_cache = mock_project_cache

        with patch(
            "backend.app.services.shapeshift_service.get_shapeshift_service",
            return_value=mock_shapeshift_service,
        ):
            service._invalidate_all_caches("my_project", "test-corr")

        mock_cache.invalidate_project.assert_called_once_with("my_project")
        mock_project_cache.invalidate_project.assert_called_once_with("my_project")

    def test_handles_shapeshift_service_error_gracefully(self, service, mock_state):
        """_invalidate_all_caches does not raise if ShapeShift service is unavailable."""
        with patch(
            "backend.app.services.shapeshift_service.get_shapeshift_service",
            side_effect=RuntimeError("Not initialized"),
        ):
            # Should not raise
            service._invalidate_all_caches("test_project", "test-corr")

        # ApplicationState should still be invalidated
        mock_state.invalidate.assert_called_once()


# ─── Concurrency Regression Tests ───────────────────────────────────────────


class TestConcurrencyRegressions:
    """Regression tests for the original bugs:

    Bug 1: Creating 3 entities sequentially results in only the last entity persisting.
    Bug 2: Deleting and recreating project shows ghost entities.
    """

    def test_sequential_entity_creation_preserves_all_entities(self, service, mock_state, temp_dir):
        """Bug 1 regression: Creating 3 entities sequentially should preserve all 3.

        The fix ensures:
        - load_project returns deep copies (no shared mutable reference)
        - add_entity_by_name is serialized with per-project lock
        """
        # Create initial project on disk
        service.create_project("test")

        # Simulate cache returning the current state each time
        # (mock_state.get returns None, so each load_project reads from disk)
        mock_state.get.return_value = None

        # Add 3 entities sequentially
        service.add_entity_by_name("test", "entity_a", {"source": "table_a"})
        service.add_entity_by_name("test", "entity_b", {"source": "table_b"})
        service.add_entity_by_name("test", "entity_c", {"source": "table_c"})

        # Verify all 3 entities persisted to disk
        file_path = temp_dir / "test" / "shapeshifter.yml"
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        assert len(data["entities"]) == 3
        assert "entity_a" in data["entities"]
        assert "entity_b" in data["entities"]
        assert "entity_c" in data["entities"]

    def test_concurrent_entity_creation_preserves_all_entities(self, service, mock_state, temp_dir):
        """Bug 1 regression: Concurrent entity creation should also preserve all entities.

        Uses threads to simulate concurrent requests hitting the backend.
        """
        service.create_project("concurrent_test")
        mock_state.get.return_value = None

        errors = []
        barrier = threading.Barrier(3)

        def add_entity(entity_name: str):
            try:
                barrier.wait(timeout=5)
                service.add_entity_by_name("concurrent_test", entity_name, {"source": f"table_{entity_name}"})
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=add_entity, args=(f"entity_{i}",)) for i in range(3)]

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Errors during concurrent creation: {errors}"

        # Verify all 3 entities on disk
        file_path = temp_dir / "concurrent_test" / "shapeshifter.yml"
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        assert len(data["entities"]) == 3

    def test_delete_and_recreate_project_no_ghost_entities(self, service, mock_state, temp_dir):
        """Bug 2 regression: Delete + recreate with same name should have zero entities.

        The fix ensures _invalidate_all_caches is called on both
        delete_project and create_project.
        """
        # Create project with entities
        service.create_project("ghost_test")
        mock_state.get.return_value = None
        service.add_entity_by_name("ghost_test", "old_entity", {"source": "old_table"})

        # Delete the project
        service.delete_project("ghost_test")

        # Verify caches were invalidated
        assert mock_state.invalidate.called

        # Recreate project with same name
        project = service.create_project("ghost_test")

        # Should have zero entities (no ghosts)
        assert len(project.entities) == 0

        # Verify disk is clean
        file_path = temp_dir / "ghost_test" / "shapeshifter.yml"
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        assert len(data.get("entities", {})) == 0

    def test_mutation_through_reference_isolated(self, service, mock_state, temp_dir):
        """Copy-on-read regression: Mutating a loaded project does not corrupt cache.

        Without model_copy(deep=True), two callers sharing the same cached
        reference would see each other's mutations.
        """
        cached_project = _make_project("shared", {"original": {"source": "original_table"}})
        mock_state.get.return_value = cached_project

        # Caller 1 loads and mutates
        copy1 = service.load_project("shared")
        copy1.entities["added_by_copy1"] = {"source": "new_table"}

        # Caller 2 loads — should NOT see copy1's mutation
        copy2 = service.load_project("shared")
        assert "added_by_copy1" not in copy2.entities

        # Original cached object should also be untouched
        assert "added_by_copy1" not in cached_project.entities


class TestDeleteProjectCacheCleanup:
    """Test that delete_project properly clears all caches."""

    def test_delete_calls_invalidate_all_caches(self, service: ProjectService, mock_state, temp_dir):
        """delete_project must call _invalidate_all_caches."""
        _write_project_yaml(temp_dir, "to_delete", {"e1": {}})

        with patch.object(service.operations, "_invalidate_all_caches") as mock_invalidate:
            service.delete_project("to_delete")
            mock_invalidate.assert_called_once()
            assert mock_invalidate.call_args[0][0] == "to_delete"

    def test_delete_removes_lock(self, service: ProjectService, mock_state, temp_dir):
        """delete_project removes the per-project lock after completion."""
        _write_project_yaml(temp_dir, "locktest", {"e1": {}})

        # Ensure lock exists
        ProjectService._get_lock("locktest")
        assert "locktest" in ProjectService._project_locks

        service.delete_project("locktest")

        assert "locktest" not in ProjectService._project_locks

    def test_create_after_delete_clears_stale_caches(self, service: ProjectService, mock_state, temp_dir):
        """create_project defensively clears caches (handles delete+recreate race)."""
        with patch.object(service.operations, "_invalidate_all_caches") as mock_invalidate:
            service.create_project("fresh")
            mock_invalidate.assert_called_once()
            assert mock_invalidate.call_args[0][0] == "fresh"
