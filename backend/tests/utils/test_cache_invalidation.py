"""Tests for ShapeShiftCache.invalidate_project and ShapeShiftProjectCache.invalidate_project."""

from unittest.mock import MagicMock

import pandas as pd
import pytest

# Import via shapeshift_service to avoid circular import
from backend.app.services.shapeshift_service import ShapeShiftCache, ShapeShiftProjectCache

# pylint: disable=redefined-outer-name


class TestShapeShiftCacheInvalidateProject:
    """Test ShapeShiftCache.invalidate_project method."""

    @pytest.fixture
    def cache(self) -> ShapeShiftCache:
        """Create empty cache with long TTL so entries don't expire during tests."""
        return ShapeShiftCache(ttl_seconds=3600)

    def _populate_cache(self, cache: ShapeShiftCache, project_name: str, entity_names: list[str]) -> None:
        """Helper to populate cache with test data."""
        for entity_name in entity_names:
            df = pd.DataFrame({"col": [1, 2, 3]})
            cache.set_dataframe(project_name, entity_name, df, project_version=1)

    def test_invalidate_removes_all_entries_for_project(self, cache):
        """invalidate_project removes all entries for the given project."""
        self._populate_cache(cache, "project_a", ["entity_1", "entity_2", "entity_3"])

        cache.invalidate_project("project_a")

        for entity in ["entity_1", "entity_2", "entity_3"]:
            assert cache.get_dataframe("project_a", entity) is None

    def test_invalidate_does_not_affect_other_projects(self, cache):
        """invalidate_project only removes entries for the specified project."""
        self._populate_cache(cache, "project_a", ["entity_1"])
        self._populate_cache(cache, "project_b", ["entity_1"])

        cache.invalidate_project("project_a")

        # project_a entry removed
        assert cache.get_dataframe("project_a", "entity_1") is None
        # project_b entry preserved
        assert cache.get_dataframe("project_b", "entity_1") is not None

    def test_invalidate_nonexistent_project_is_noop(self, cache):
        """invalidate_project for unknown project does not raise."""
        self._populate_cache(cache, "project_a", ["entity_1"])

        cache.invalidate_project("nonexistent")  # Should not raise

        # Original entries unaffected
        assert cache.get_dataframe("project_a", "entity_1") is not None

    def test_invalidate_clears_both_dataframes_and_metadata(self, cache):
        """invalidate_project removes both _dataframes and _metadata entries."""
        self._populate_cache(cache, "project_a", ["entity_1"])

        assert len(cache._dataframes) == 1
        assert len(cache._metadata) == 1

        cache.invalidate_project("project_a")

        assert len(cache._dataframes) == 0
        assert len(cache._metadata) == 0

    def test_invalidate_multiple_entities(self, cache):
        """invalidate_project handles projects with many cached entities."""
        entities = [f"entity_{i}" for i in range(20)]
        self._populate_cache(cache, "big_project", entities)

        assert len(cache._dataframes) == 20

        cache.invalidate_project("big_project")

        assert len(cache._dataframes) == 0
        assert len(cache._metadata) == 0

    def test_get_available_entities_empty_after_invalidation(self, cache):
        """After invalidation, get_available_entities returns empty set."""
        self._populate_cache(cache, "project_a", ["e1", "e2"])

        assert cache.get_available_entities("project_a") == {"e1", "e2"}

        cache.invalidate_project("project_a")

        assert cache.get_available_entities("project_a") == set()


class TestShapeShiftProjectCacheInvalidateProject:
    """Test ShapeShiftProjectCache.invalidate_project method."""

    @pytest.fixture
    def project_cache(self) -> ShapeShiftProjectCache:
        """Create cache with mocked project service."""
        mock_service = MagicMock()
        return ShapeShiftProjectCache(project_service=mock_service)

    def test_invalidate_removes_cached_project(self, project_cache):
        """invalidate_project removes the ShapeShiftProject from cache."""
        mock_project = MagicMock()
        project_cache._cache["test_project"] = mock_project
        project_cache._versions["test_project"] = 5

        project_cache.invalidate_project("test_project")

        assert "test_project" not in project_cache._cache
        assert "test_project" not in project_cache._versions

    def test_invalidate_does_not_affect_other_projects(self, project_cache):
        """invalidate_project only removes the specified project."""
        project_cache._cache["keep_me"] = MagicMock()
        project_cache._versions["keep_me"] = 1
        project_cache._cache["remove_me"] = MagicMock()
        project_cache._versions["remove_me"] = 2

        project_cache.invalidate_project("remove_me")

        assert "keep_me" in project_cache._cache
        assert "keep_me" in project_cache._versions
        assert "remove_me" not in project_cache._cache
        assert "remove_me" not in project_cache._versions

    def test_invalidate_nonexistent_project_is_noop(self, project_cache):
        """invalidate_project for unknown project does not raise."""
        project_cache._cache["existing"] = MagicMock()
        project_cache._versions["existing"] = 1

        project_cache.invalidate_project("nonexistent")  # Should not raise

        assert "existing" in project_cache._cache

    def test_invalidate_clears_both_cache_and_versions(self, project_cache):
        """Both _cache and _versions are cleared."""
        project_cache._cache["test"] = MagicMock()
        project_cache._versions["test"] = 3

        project_cache.invalidate_project("test")

        assert len(project_cache._cache) == 0
        assert len(project_cache._versions) == 0
