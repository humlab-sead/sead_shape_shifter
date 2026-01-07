"""Tests for entity preview service."""

import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from backend.app.models.shapeshift import ColumnInfo, PreviewResult
from backend.app.services.shapeshift_service import PreviewResultBuilder, ShapeShiftCache, ShapeShiftService
from src.model import ShapeShiftProject, TableConfig

# pylint: disable=redefined-outer-name, attribute-defined-outside-init


@pytest.fixture
def project_service() -> MagicMock:
    """Create mock ProjectService."""
    service = MagicMock()
    service.get_project_path.return_value = Path("test_project.yml")
    service.load_project = MagicMock()
    return service


@pytest.fixture
def shapeshift_service(project_service: MagicMock) -> ShapeShiftService:
    """Create ShapeShiftService instance."""
    return ShapeShiftService(project_service=project_service)


@pytest.fixture
def sample_project() -> ShapeShiftProject:
    """Create a sample project."""
    cfg = {
        "metadata": {
            "name": "test_project",
            "description": "A test project",
            "version": "1.0.0",
        },
        "entities": {
            "users": {
                "name": "users",
                "type": "sql",
                "data_source": "test_db",
                "query": "SELECT * FROM users",
                "surrogate_id": "user_id",
                "keys": ["username"],
                "columns": ["user_id", "username", "email"],
            },
            "orders": {
                "name": "orders",
                "type": "sql",
                "data_source": "test_db",
                "query": "SELECT * FROM orders",
                "source": "users",
                "surrogate_id": "order_id",
                "columns": ["order_id", "user_id", "total"],
                "foreign_keys": [
                    {
                        "entity": "users",
                        "local_keys": ["user_id"],
                        "remote_keys": ["user_id"],
                        "how": "left",
                    }
                ],
            },
        },
        "options": {},
    }

    return ShapeShiftProject(cfg=cfg, filename="test-project.yml")


@pytest.fixture
def sample_dataframe() -> pd.DataFrame:
    """Create a sample DataFrame."""
    return pd.DataFrame(
        {
            "user_id": [1, 2, 3, 4, 5],
            "username": ["alice", "bob", "charlie", "david", "eve"],
            "email": ["alice@example.com", "bob@example.com", None, "david@example.com", "eve@example.com"],
        }
    )


@pytest.fixture
def sample_entity_config() -> TableConfig:
    """Create sample entity configuration."""
    cfg = {
        "test_entity": {
            "source": "test_table",
            "columns": ["id", "name"],
            "keys": ["id"],
        }
    }
    return TableConfig(entities_cfg=cfg, entity_name="test_entity")


class TestShapeShiftCache:
    """Tests for preview cache."""

    def test_cache_miss(self):
        """Test cache miss returns None."""
        cache = ShapeShiftCache(ttl_seconds=60)
        result = cache.get_dataframe("config1", "entity1")
        assert result is None

    def test_cache_hit(self):
        """Test cache hit returns cached result."""

        cache = ShapeShiftCache(ttl_seconds=60)
        df1 = pd.DataFrame({"id": [1, 2, 3], "name": ["a", "b", "c"]})
        df2 = pd.DataFrame({"id": [4, 5], "value": [10, 20]})

        cache.set_dataframe(project_name="config1", entity_name="entity1", dataframe=df1)
        cache.set_dataframe(project_name="config1", entity_name="entity2", dataframe=df2)

        result1 = cache.get_dataframe("config1", "entity1")
        result2 = cache.get_dataframe("config1", "entity2")

        assert result1 is not None
        assert result2 is not None
        assert len(result1) == 3
        assert len(result2) == 2

    def test_cache_expiry(self):
        """Test cache entries expire after TTL."""

        cache = ShapeShiftCache(ttl_seconds=1)  # 1 second TTL
        df = pd.DataFrame({"id": [1]})
        cache.set_dataframe(project_name="config1", entity_name="entity1", dataframe=df)

        time.sleep(1.1)  # Wait for expiry

        result = cache.get_dataframe("config1", "entity1")
        assert result is None

    def test_cache_invalidate_specific(self):
        """Test invalidating specific entity cache."""

        cache = ShapeShiftCache(ttl_seconds=60)
        df1 = pd.DataFrame({"id": [1]})
        df2 = pd.DataFrame({"id": [2]})

        cache.set_dataframe("config1", "entity1", df1)
        cache.set_dataframe("config1", "entity2", df2)

        cache.invalidate("config1", "entity1")

        assert cache.get_dataframe("config1", "entity1") is None
        assert cache.get_dataframe("config1", "entity2") is not None

    def test_cache_invalidate_all(self):
        """Test invalidating all cache entries for a config."""

        cache = ShapeShiftCache(ttl_seconds=60)
        df1 = pd.DataFrame({"id": [1]})
        df2 = pd.DataFrame({"id": [2]})

        cache.set_dataframe("config1", "entity1", df1)
        cache.set_dataframe("config1", "entity2", df2)

        cache.invalidate("config1")

        assert cache.get_dataframe("config1", "entity1") is None
        assert cache.get_dataframe("config1", "entity2") is None

    def test_cache_hash_invalidation(self, sample_project):
        """Test hash-based cache invalidation when entity config changes."""

        cache = ShapeShiftCache(ttl_seconds=60)
        df = pd.DataFrame({"user_id": [1, 2, 3], "username": ["alice", "bob", "charlie"]})

        # Get original entity config
        entity_config = sample_project.get_table("users")

        # Cache with original config
        cache.set_dataframe("config1", "users", df, project_version=1, entity_config=entity_config)

        # Verify cache hit with same config
        assert cache.get_dataframe("config1", "users", 1, entity_config) is not None

        # Modify entity configuration (simulate editing)
        modified_cfg = {
            "users": {
                "name": "users",
                "type": "sql",
                "data_source": "test_db",
                "query": "SELECT * FROM users WHERE active = 1",  # Changed query
                "surrogate_id": "user_id",
                "keys": ["username"],
                "columns": ["user_id", "username", "email"],
            }
        }
        modified_entity_config = TableConfig(entities_cfg=modified_cfg, entity_name="users")

        # Cache should be invalidated due to hash mismatch
        result = cache.get_dataframe("config1", "users", 1, modified_entity_config)
        assert result is None


class TestShapeShiftService:
    """Tests for preview service."""

    @pytest.mark.asyncio
    async def test_preview_entity_not_found(self, shapeshift_service, sample_project):
        """Test preview with non-existent entity."""

        # Mock ApplicationState
        mock_app_state = MagicMock()
        mock_app_state.get_version.return_value = 1
        mock_api_config = MagicMock()
        mock_api_config.metadata.name = "test_project"
        mock_app_state.get_project.return_value = mock_api_config

        with (
            patch("backend.app.services.shapeshift_service.get_app_state", return_value=mock_app_state),
            patch("backend.app.utils.caches.get_app_state", return_value=mock_app_state),
            patch("backend.app.utils.caches.ProjectMapper.to_core_dict", return_value=sample_project.cfg),
        ):
            with pytest.raises(ValueError, match="Entity 'nonexistent' not found"):
                await shapeshift_service.preview_entity("test_project", "nonexistent", 50)

    @pytest.mark.asyncio
    async def test_preview_entity_entity_not_found(self, shapeshift_service: ShapeShiftService, project_service: MagicMock):
        """Test preview with non-existent entity raises error."""
        mock_api_config = MagicMock()
        project_service.load_project = MagicMock(return_value=mock_api_config)

        with (
            patch("backend.app.utils.caches.ProjectMapper") as mock_mapper,
            patch("backend.app.services.shapeshift_service.ShapeShiftProject") as mock_cfg,
        ):
            mock_mapper.to_core_dict = MagicMock(return_value={})
            mock_cfg.return_value.tables = {}

            with pytest.raises(ValueError, match="Entity .* not found"):
                await shapeshift_service.preview_entity("test_project", "nonexistent", limit=10)

    @pytest.mark.asyncio
    async def test_preview_entity_success(self, shapeshift_service, sample_project):
        """Test successful entity preview."""

        users_df = pd.DataFrame(
            {
                "user_id": [1, 2, 3, 4, 5],
                "username": ["alice", "bob", "charlie", "david", "eve"],
                "email": ["alice@example.com", "bob@example.com", None, "david@example.com", "eve@example.com"],
            }
        )

        mock_normalizer = MagicMock()
        mock_normalizer.normalize = AsyncMock()
        mock_normalizer.table_store = {"users": users_df}

        with (
            patch("backend.app.services.shapeshift_service.ShapeShifter") as mock_shifter,
            patch.object(shapeshift_service.project_cache, "get_project", return_value=sample_project),
        ):
            mock_shifter.return_value = mock_normalizer

            result = await shapeshift_service.preview_entity("test_project", "users", 50)

            assert result.entity_name == "users"
            assert result.total_rows_in_preview == 5
            assert result.estimated_total_rows == 5
            assert len(result.rows) == 5
            assert len(result.columns) == 3
            assert result.execution_time_ms > 0

            # Check column info
            user_id_col = next(c for c in result.columns if c.name == "user_id")
            assert user_id_col.is_key is True  # It's the surrogate_id
            assert user_id_col.data_type == "integer"

            email_col = next(c for c in result.columns if c.name == "email")
            assert email_col.nullable is True  # Has None value

    @pytest.mark.asyncio
    async def test_preview_with_limit(self, shapeshift_service, sample_project):
        """Test preview respects limit parameter."""
        large_df = pd.DataFrame({"col1": range(100), "col2": range(100, 200)})

        # Mock ApplicationState
        mock_app_state = MagicMock()
        mock_app_state.get_version.return_value = 1
        mock_api_config = MagicMock()
        mock_api_config.metadata.name = "test_project"
        mock_app_state.get_project.return_value = mock_api_config

        with (
            patch("backend.app.services.shapeshift_service.get_app_state", return_value=mock_app_state),
            patch("backend.app.utils.caches.ProjectMapper.to_core_dict", return_value=sample_project.cfg),
            patch("backend.app.services.shapeshift_service.ShapeShifter") as mock_normalizer_class,
        ):
            mock_normalizer = MagicMock()
            mock_normalizer.normalize = AsyncMock()
            mock_normalizer.table_store = {"users": large_df}
            mock_normalizer_class.return_value = mock_normalizer

            result = await shapeshift_service.preview_entity("test_project", "users", limit=10)

            assert result.total_rows_in_preview == 10
            assert result.estimated_total_rows == 100

    @pytest.mark.asyncio
    async def test_preview_with_transformations(self, shapeshift_service: ShapeShiftService, sample_project: ShapeShiftProject):
        """Test preview detects applied transformations."""
        # Modify entity to have filters and unnest
        config_with_transforms: ShapeShiftProject = sample_project.clone()
        config_with_transforms.entities["users"]["filters"] = [{"type": "exists_in", "entity": "orders"}]
        config_with_transforms.entities["users"]["unnest"] = {
            "id_vars": ["user_id"],
            "value_vars": ["col1", "col2"],
            "var_name": "variable",
            "value_name": "value",
        }

        # Mock ApplicationState
        mock_app_state = MagicMock()
        mock_app_state.get_version.return_value = 1
        mock_api_config = MagicMock()
        mock_api_config.metadata.name = "test_project"
        mock_app_state.get_project.return_value = mock_api_config

        with (
            patch("backend.app.services.shapeshift_service.get_app_state", return_value=mock_app_state),
            patch("backend.app.utils.caches.ProjectMapper.to_core_dict", return_value=sample_project.cfg),
            patch("backend.app.services.shapeshift_service.ShapeShifter") as mock_normalizer_class,
        ):
            mock_normalizer = MagicMock()
            mock_normalizer.normalize = AsyncMock()
            mock_normalizer.table_store = {"users": pd.DataFrame({"user_id": [1]})}
            mock_normalizer_class.return_value = mock_normalizer

            result: PreviewResult = await shapeshift_service.preview_entity("test_project", "users", 50)

            assert result is not None

    @pytest.mark.asyncio
    async def test_preview_with_dependencies(
        self, shapeshift_service: ShapeShiftService, sample_project: ShapeShiftProject, sample_dataframe: pd.DataFrame
    ):
        """Test preview loads dependencies correctly."""
        # Mock ApplicationState
        mock_app_state = MagicMock()
        mock_app_state.get_version.return_value = 1
        mock_api_config = MagicMock()
        mock_api_config.metadata.name = "test_project"
        mock_app_state.get_project.return_value = mock_api_config

        with (
            patch("backend.app.services.shapeshift_service.get_app_state", return_value=mock_app_state),
            patch("backend.app.utils.caches.ProjectMapper.to_core_dict", return_value=sample_project.cfg),
            patch("backend.app.services.shapeshift_service.ShapeShifter") as mock_normalizer_class,
        ):
            mock_normalizer = MagicMock()
            mock_normalizer.normalize = AsyncMock()
            # table_store now contains target + dependencies
            mock_normalizer.table_store = {
                "orders": sample_dataframe,
                "users": pd.DataFrame({"user_id": [1, 2], "username": ["alice", "bob"]}),
            }
            mock_normalizer_class.return_value = mock_normalizer

            result = await shapeshift_service.preview_entity("test_project", "orders", 50)

            assert result.has_dependencies is True
            assert "users" in result.dependencies_loaded

    @pytest.mark.asyncio
    async def test_preview_caching(
        self, shapeshift_service: ShapeShiftService, sample_project: ShapeShiftProject, sample_dataframe: pd.DataFrame
    ):
        """Test preview results are cached."""
        # Mock ApplicationState
        mock_app_state = MagicMock()
        mock_app_state.get_version.return_value = 1
        mock_api_config = MagicMock()
        mock_api_config.metadata.name = "test_project"
        mock_app_state.get_project.return_value = mock_api_config

        with (
            patch("backend.app.services.shapeshift_service.get_app_state", return_value=mock_app_state),
            patch("backend.app.utils.caches.ProjectMapper.to_core_dict", return_value=sample_project.cfg),
            patch("backend.app.services.shapeshift_service.ShapeShifter") as mock_normalizer_class,
        ):
            mock_normalizer = MagicMock()
            mock_normalizer.normalize = AsyncMock()
            mock_normalizer.table_store = {"users": sample_dataframe}
            mock_normalizer_class.return_value = mock_normalizer

            # First call - should hit shapeshifter
            result1 = await shapeshift_service.preview_entity("test_project", "users", 50)
            assert result1.cache_hit is False

            # Second call - should hit cache
            result2 = await shapeshift_service.preview_entity("test_project", "users", 50)
            assert result2.cache_hit is True

            # Verify shapeshifter was only called once
            assert mock_normalizer.normalize.call_count == 1

    @pytest.mark.asyncio
    async def test_get_entity_sample(
        self, shapeshift_service: ShapeShiftService, sample_project: ShapeShiftProject, sample_dataframe: pd.DataFrame
    ):
        """Test get_entity_sample with higher limit."""
        # Mock ApplicationState
        mock_app_state = MagicMock()
        mock_app_state.get_version.return_value = 1
        mock_api_project = MagicMock()
        mock_api_project.metadata.name = "test_project"
        mock_app_state.get_project.return_value = mock_api_project

        with (
            patch("backend.app.services.shapeshift_service.get_app_state", return_value=mock_app_state),
            patch("backend.app.utils.caches.ProjectMapper.to_core_dict", return_value=sample_project.cfg),
            patch("backend.app.services.shapeshift_service.ShapeShifter") as mock_normalizer_class,
        ):
            mock_normalizer = MagicMock()
            mock_normalizer.normalize = AsyncMock()
            mock_normalizer.table_store = {"users": sample_dataframe}
            mock_normalizer_class.return_value = mock_normalizer

            result = await shapeshift_service.get_entity_sample("test_project", "users", limit=100)

            assert result.entity_name == "users"
            assert result.total_rows_in_preview == 5  # Sample df only has 5 rows

    def test_invalidate_cache(self, shapeshift_service: ShapeShiftService):
        """Test cache invalidation."""

        # Add something to cache
        df = pd.DataFrame({"id": [1, 2, 3]})
        shapeshift_service.cache.set_dataframe("config1", "entity1", df)

        # Verify it's cached
        assert shapeshift_service.cache.get_dataframe("config1", "entity1") is not None

        # Invalidate
        shapeshift_service.invalidate_cache("config1", "entity1")

        # Verify it's gone
        assert shapeshift_service.cache.get_dataframe("config1", "entity1") is None

    # Possibly redundant with previous tests, but included for completeness

    @pytest.mark.asyncio
    async def test_preview_entity_success2(
        self,
        shapeshift_service: ShapeShiftService,
        sample_entity_config: TableConfig,
        sample_dataframe: pd.DataFrame,
    ):
        """Test successful entity preview."""
        # Mock ShapeShifter
        mock_normalizer = MagicMock()
        mock_normalizer.table_store = {"test_entity": sample_dataframe}
        mock_normalizer.normalize = AsyncMock()

        # Mock ShapeShiftProject with the entity
        mock_shapeshift_project = MagicMock()
        mock_shapeshift_project.tables = {"test_entity": sample_entity_config}

        with (
            patch("backend.app.services.shapeshift_service.ShapeShifter") as mock_shifter,
            patch.object(shapeshift_service.project_cache, "get_project", return_value=mock_shapeshift_project),
        ):
            mock_shifter.return_value = mock_normalizer

            result = await shapeshift_service.preview_entity("test_project", "test_entity", limit=10)

            assert result.entity_name == "test_entity"
            assert result.total_rows_in_preview == 5
            assert len(result.rows) == 5
            assert result.cache_hit is False

    @pytest.mark.asyncio
    async def test_preview_entity_applies_limit(self, shapeshift_service: ShapeShiftService, sample_entity_config: TableConfig):
        """Test preview applies row limit."""
        large_df = pd.DataFrame({"id": range(100), "name": [f"User{i}" for i in range(100)]})

        mock_normalizer = MagicMock()
        mock_normalizer.table_store = {"test_entity": large_df}
        mock_normalizer.normalize = AsyncMock()

        # Mock ShapeShiftProject with the entity
        mock_shapeshift_project = MagicMock()
        mock_shapeshift_project.tables = {"test_entity": sample_entity_config}

        with (
            patch("backend.app.services.shapeshift_service.ShapeShifter") as mock_shifter,
            patch.object(shapeshift_service.project_cache, "get_project", return_value=mock_shapeshift_project),
        ):
            mock_shifter.return_value = mock_normalizer

            result = await shapeshift_service.preview_entity("test_project", "test_entity", limit=10)

            assert result.total_rows_in_preview == 10
            assert result.estimated_total_rows == 100

    @pytest.mark.asyncio
    async def test_preview_entity_with_dependencies(self, shapeshift_service: ShapeShiftService, sample_dataframe: pd.DataFrame):
        """Test preview detects entity dependencies."""
        cfg = {
            "test_entity": {
                "source": "test_table",
                "columns": ["id", "name"],
                "keys": ["id"],
                "depends_on": ["parent_entity"],
            }
        }
        entity_config = TableConfig(entities_cfg=cfg, entity_name="test_entity")

        mock_normalizer = MagicMock()
        mock_normalizer.table_store = {"test_entity": sample_dataframe, "parent_entity": sample_dataframe}
        mock_normalizer.normalize = AsyncMock()

        # Mock ShapeShiftProject with the entity
        mock_shapeshift_project = MagicMock()
        mock_shapeshift_project.tables = {"test_entity": entity_config}

        with (
            patch("backend.app.services.shapeshift_service.ShapeShifter") as mock_shifter,
            patch.object(shapeshift_service.project_cache, "get_project", return_value=mock_shapeshift_project),
        ):
            mock_shifter.return_value = mock_normalizer

            result = await shapeshift_service.preview_entity("test_project", "test_entity", limit=10)

            assert result.has_dependencies is True
            assert "parent_entity" in result.dependencies_loaded

    @pytest.mark.asyncio
    async def test_preview_entity_shapeshifter_error(self, shapeshift_service: ShapeShiftService, sample_entity_config: TableConfig):
        """Test preview handles shapeshifter errors."""
        mock_shapeshifter = MagicMock()
        mock_shapeshifter.normalize = AsyncMock(side_effect=RuntimeError("Normalization failed"))

        # Mock ShapeShiftProject with the entity
        mock_shapeshift_project = MagicMock()
        mock_shapeshift_project.tables = {"test_entity": sample_entity_config}

        with (
            patch("backend.app.services.shapeshift_service.ShapeShifter") as mock_shifter,
            patch.object(shapeshift_service.project_cache, "get_project", return_value=mock_shapeshift_project),
        ):
            mock_shifter.return_value = mock_shapeshifter

            with pytest.raises(RuntimeError, match="ShapeShift failed"):
                await shapeshift_service.preview_entity("test_project", "test_entity", limit=10)

    @pytest.mark.asyncio
    async def test_get_entity_sample_default_limit(
        self,
        shapeshift_service: ShapeShiftService,
        sample_entity_config: TableConfig,
        sample_dataframe: pd.DataFrame,
    ):
        """Test get_entity_sample uses default limit of 100."""
        mock_shapeshifter = MagicMock()
        mock_shapeshifter.table_store = {"test_entity": sample_dataframe}
        mock_shapeshifter.normalize = AsyncMock()

        # Mock ShapeShiftProject with the entity
        mock_shapeshift_project = MagicMock()
        mock_shapeshift_project.tables = {"test_entity": sample_entity_config}

        with (
            patch("backend.app.services.shapeshift_service.ShapeShifter") as mock_shifter,
            patch.object(shapeshift_service.project_cache, "get_project", return_value=mock_shapeshift_project),
        ):
            mock_shifter.return_value = mock_shapeshifter

            result = await shapeshift_service.get_entity_sample("test_project", "test_entity")

            assert result.total_rows_in_preview <= 100


class TestShapeShiftProject:

    @pytest.mark.asyncio
    async def test_get_shapeshift_config_from_app_state(self, shapeshift_service: ShapeShiftService):
        """Test loading ShapeShift config from ApplicationState."""
        mock_api_config = MagicMock()

        with (
            patch("backend.app.utils.caches.get_app_state") as mock_state,
            patch("backend.app.utils.caches.ProjectMapper") as mock_mapper,
            patch("backend.app.services.shapeshift_service.ShapeShiftProject") as mock_cfg,
        ):
            mock_state.return_value.get_version = MagicMock(return_value=1)
            mock_state.return_value.get_project = MagicMock(return_value=mock_api_config)
            mock_mapper.to_core_dict = MagicMock(return_value={})
            mock_cfg.return_value = MagicMock()

            result = await shapeshift_service.project_cache.get_project("test_project")

            assert result is not None
            mock_state.return_value.get_project.assert_called_once_with("test_project")

    @pytest.mark.asyncio
    async def test_get_shapeshift_config_from_disk(self, shapeshift_service: ShapeShiftService, project_service: MagicMock):
        """Test loading ShapeShift config from disk when not in app state."""
        mock_api_config = MagicMock()
        project_service.load_project = MagicMock(return_value=mock_api_config)

        with (
            patch("backend.app.utils.caches.get_app_state") as mock_state,
            patch("backend.app.utils.caches.ProjectMapper") as mock_mapper,
            patch("backend.app.services.shapeshift_service.ShapeShiftProject") as mock_cfg,
        ):
            mock_state.side_effect = RuntimeError("Not initialized")
            mock_mapper.to_core_dict = MagicMock(return_value={})
            mock_cfg.return_value = MagicMock()

            result = await shapeshift_service.project_cache.get_project("test_project")

            assert result is not None
            project_service.load_project.assert_called_once_with("test_project")

    @pytest.mark.asyncio
    async def test_get_shapeshift_config_caching(self, shapeshift_service: ShapeShiftService):
        """Test ShapeShift config is cached."""
        mock_api_config = MagicMock()

        with (
            patch("backend.app.utils.caches.get_app_state") as mock_state,
            patch("backend.app.utils.caches.ProjectMapper") as mock_mapper,
            patch("backend.app.services.shapeshift_service.ShapeShiftProject") as mock_cfg,
        ):
            mock_state.return_value.get_version = MagicMock(return_value=1)
            mock_state.return_value.get_project = MagicMock(return_value=mock_api_config)
            mock_mapper.to_core_dict = MagicMock(return_value={})
            mock_cfg_instance = MagicMock()
            mock_cfg.return_value = mock_cfg_instance

            result1 = await shapeshift_service.project_cache.get_project("test_project")
            result2 = await shapeshift_service.project_cache.get_project("test_project")

            # Should return same cached instance
            assert result1 is result2
            # Should only load once
            assert mock_state.return_value.get_project.call_count == 1

    @pytest.mark.asyncio
    async def test_get_shapeshift_config_version_tracking(self, shapeshift_service: ShapeShiftService):
        """Test config cache is invalidated when version changes."""
        mock_api_config = MagicMock()

        with (
            patch("backend.app.utils.caches.get_app_state") as mock_state,
            patch("backend.app.utils.caches.ProjectMapper") as mock_mapper,
            patch("backend.app.services.shapeshift_service.ShapeShiftProject") as mock_cfg,
        ):
            # First call with version 1
            mock_state.return_value.get_version = MagicMock(return_value=1)
            mock_state.return_value.get_project = MagicMock(return_value=mock_api_config)
            mock_mapper.to_core_dict = MagicMock(return_value={})
            mock_cfg.return_value = MagicMock()

            await shapeshift_service.project_cache.get_project("test_project")

            # Second call with version 2
            mock_state.return_value.get_version = MagicMock(return_value=2)

            await shapeshift_service.project_cache.get_project("test_project")

            # Should reload due to version change
            assert mock_state.return_value.get_project.call_count == 2


class TestPreviewBuilder:
    """Tests for PreviewResultBuilder."""

    def test_build_preview_result_with_dependencies(self, sample_dataframe: pd.DataFrame, sample_project: ShapeShiftProject):
        """Test _build_preview_result correctly identifies dependencies."""
        entity_cfg: TableConfig = sample_project.get_table("orders")
        table_store: dict[str, pd.DataFrame] = {
            "orders": sample_dataframe,
            "users": pd.DataFrame({"user_id": [1, 2], "username": ["alice", "bob"]}),
        }
        builder: PreviewResultBuilder = PreviewResultBuilder()
        result: PreviewResult = builder.build(
            entity_name="orders", entity_cfg=entity_cfg, table_store=table_store, limit=50, cache_hit=False
        )

        assert result.entity_name == "orders"
        assert len(result.columns) == 3

        # Check user_id (foreign key column)
        user_id_col: ColumnInfo = next(c for c in result.columns if c.name == "user_id")
        # assert user_id_col.is_key is True
        assert user_id_col.data_type == "integer"

        # Check dependencies
        assert result.has_dependencies is True
        assert "users" in result.dependencies_loaded

    def test_build_preview_result(self, sample_dataframe: pd.DataFrame, sample_project: ShapeShiftProject):
        """Test _build_preview_result correctly builds PreviewResult from table_store."""
        entity_cfg: TableConfig = sample_project.get_table("users")
        table_store: dict[str, pd.DataFrame] = {"users": sample_dataframe, "orders": pd.DataFrame({"order_id": [1, 2], "user_id": [1, 2]})}

        builder: PreviewResultBuilder = PreviewResultBuilder()
        result: PreviewResult = builder.build(
            entity_name="users", entity_cfg=entity_cfg, table_store=table_store, limit=50, cache_hit=False
        )

        assert result.entity_name == "users"
        assert len(result.columns) == 3

        # Check user_id (key column)
        user_id_col: ColumnInfo = next(c for c in result.columns if c.name == "user_id")
        assert user_id_col.is_key is True
        assert user_id_col.data_type == "integer"

        # Check username (natural key)
        username_col: ColumnInfo = next(c for c in result.columns if c.name == "username")
        assert username_col.is_key is True
        assert username_col.nullable is False

        # Check email (nullable)
        email_col: ColumnInfo = next(c for c in result.columns if c.name == "email")
        assert email_col.is_key is False
        assert email_col.nullable is True

        # Check dependencies
        assert result.has_dependencies is True
        assert "orders" in result.dependencies_loaded
