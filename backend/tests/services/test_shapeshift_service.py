"""Tests for entity preview service."""

import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from backend.app.models.shapeshift import ColumnInfo, PreviewResult
from backend.app.services.shapeshift_service import PreviewResultBuilder, ShapeShiftCache, ShapeShiftService
from src.model import ShapeShiftConfig, TableConfig


from backend.app.services.shapeshift_service import ShapeShiftCache, ShapeShiftService

# pylint: disable=redefined-outer-name, unused-argument


# pylint: disable=redefined-outer-name, unused-argument, attribute-defined-outside-init


@pytest.fixture
def config_service() -> MagicMock:
    """Mock config service."""
    service = MagicMock()
    service.get_config_path.return_value = Path("test_config.yml")
    return service


@pytest.fixture
def shapeshift_service(config_service: MagicMock) -> ShapeShiftService:
    """Create preview service instance."""
    return ShapeShiftService(config_service)


@pytest.fixture
def sample_config() -> ShapeShiftConfig:
    """Create a sample configuration."""
    cfg = {
        "metadata": {
            "name": "test_config",
            "description": "A test configuration",
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

    return ShapeShiftConfig(cfg=cfg)


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


class TestShapeShiftCache:
    """Tests for preview cache."""

    def test_cache_miss(self):
        """Test cache miss returns None."""
        cache = ShapeShiftCache(ttl_seconds=60)
        result = cache.get_table_store("config1", "entity1")
        assert result is None

    def test_cache_hit(self):
        """Test cache hit returns cached result."""
        import pandas as pd

        cache = ShapeShiftCache(ttl_seconds=60)
        table_store = {
            "entity1": pd.DataFrame({"id": [1, 2, 3], "name": ["a", "b", "c"]}),
            "entity2": pd.DataFrame({"id": [4, 5], "value": [10, 20]}),
        }
        cache.set_table_store(config_name="config1", entity_name="entity1", table_store=table_store)

        result = cache.get_table_store("config1", "entity1")
        assert result is not None
        assert "entity1" in result
        assert "entity2" in result
        assert len(result["entity1"]) == 3

    def test_cache_expiry(self):
        """Test cache entries expire after TTL."""
        import time

        import pandas as pd

        cache = ShapeShiftCache(ttl_seconds=1)  # 1 second TTL
        table_store = {"entity1": pd.DataFrame({"id": [1]})}
        cache.set_table_store(config_name="config1", entity_name="entity1", table_store=table_store)

        time.sleep(1.1)  # Wait for expiry

        result = cache.get_table_store("config1", "entity1")
        assert result is None

    def test_cache_invalidate_specific(self):
        """Test invalidating specific entity cache."""
        import pandas as pd

        cache = ShapeShiftCache(ttl_seconds=60)
        table_store1 = {"entity1": pd.DataFrame({"id": [1]})}
        table_store2 = {"entity2": pd.DataFrame({"id": [2]})}

        cache.set_table_store("config1", "entity1", table_store1)
        cache.set_table_store("config1", "entity2", table_store2)

        cache.invalidate("config1", "entity1")

        assert cache.get_table_store("config1", "entity1") is None
        assert cache.get_table_store("config1", "entity2") is not None

    def test_cache_invalidate_all(self):
        """Test invalidating all cache entries for a config."""
        import pandas as pd

        cache = ShapeShiftCache(ttl_seconds=60)
        table_store1 = {"entity1": pd.DataFrame({"id": [1]})}
        table_store2 = {"entity2": pd.DataFrame({"id": [2]})}

        cache.set_table_store("config1", "entity1", table_store1)
        cache.set_table_store("config1", "entity2", table_store2)

        cache.invalidate("config1")

        assert cache.get_table_store("config1", "entity1") is None
        assert cache.get_table_store("config1", "entity2") is None


class TestShapeShiftService:
    """Tests for preview service."""

    @pytest.mark.asyncio
    async def test_preview_entity_not_found(self, shapeshift_service, sample_config):
        """Test preview with non-existent entity."""

        # Mock ApplicationState
        mock_app_state = MagicMock()
        mock_app_state.get_version.return_value = 1
        mock_api_config = MagicMock()
        mock_api_config.metadata.name = "test_config"
        mock_app_state.get_configuration.return_value = mock_api_config

        with patch("backend.app.services.shapeshift_service.get_app_state", return_value=mock_app_state):
            with patch("backend.app.services.shapeshift_service.ConfigMapper.to_core_dict", return_value=sample_config.cfg):
                with pytest.raises(ValueError, match="Entity 'nonexistent' not found"):
                    await shapeshift_service.preview_entity("test_config", "nonexistent", 50)

    @pytest.mark.asyncio
    async def test_preview_entity_success(self, shapeshift_service, sample_config, sample_dataframe):
        """Test successful entity preview."""

        # Mock ApplicationState to return our sample config
        mock_app_state = MagicMock()
        mock_app_state.get_version.return_value = 1
        mock_api_config = MagicMock()
        mock_api_config.metadata.name = "test_config"
        mock_app_state.get_configuration.return_value = mock_api_config

        with patch("backend.app.services.shapeshift_service.get_app_state", return_value=mock_app_state):
            with patch("backend.app.services.shapeshift_service.ConfigMapper.to_core_dict", return_value=sample_config.cfg):
                with patch("backend.app.services.shapeshift_service.ShapeShifter") as mock_normalizer_class:
                    # Setup mock normalizer
                    mock_normalizer = MagicMock()
                    mock_normalizer.normalize = AsyncMock()
                    mock_normalizer.table_store = {"users": sample_dataframe}
                    mock_normalizer.config = sample_config
                    mock_normalizer_class.return_value = mock_normalizer

                    result = await shapeshift_service.preview_entity("test_config", "users", 50)

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
    async def test_preview_with_limit(self, shapeshift_service, sample_config):
        """Test preview respects limit parameter."""
        large_df = pd.DataFrame({"col1": range(100), "col2": range(100, 200)})

        # Mock ApplicationState
        mock_app_state = MagicMock()
        mock_app_state.get_version.return_value = 1
        mock_api_config = MagicMock()
        mock_api_config.metadata.name = "test_config"
        mock_app_state.get_configuration.return_value = mock_api_config

        with patch("backend.app.services.shapeshift_service.get_app_state", return_value=mock_app_state):
            with patch("backend.app.services.shapeshift_service.ConfigMapper.to_core_dict", return_value=sample_config.cfg):
                with patch("backend.app.services.shapeshift_service.ShapeShifter") as mock_normalizer_class:
                    mock_normalizer = MagicMock()
                    mock_normalizer.normalize = AsyncMock()
                    mock_normalizer.table_store = {"users": large_df}
                    mock_normalizer_class.return_value = mock_normalizer

                    result = await shapeshift_service.preview_entity("test_config", "users", limit=10)

                assert result.total_rows_in_preview == 10
                assert result.estimated_total_rows == 100

    @pytest.mark.asyncio
    async def test_preview_with_transformations(self, shapeshift_service: ShapeShiftService, sample_config: ShapeShiftConfig):
        """Test preview detects applied transformations."""
        # Modify config to have filters and unnest
        config_with_transforms: ShapeShiftConfig = sample_config.clone()
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
        mock_api_config.metadata.name = "test_config"
        mock_app_state.get_configuration.return_value = mock_api_config

        with patch("backend.app.services.shapeshift_service.get_app_state", return_value=mock_app_state):
            with patch("backend.app.services.shapeshift_service.ConfigMapper.to_core_dict", return_value=config_with_transforms.cfg):
                with patch("backend.app.services.shapeshift_service.ShapeShifter") as mock_normalizer_class:
                    mock_normalizer = MagicMock()
                    mock_normalizer.normalize = AsyncMock()
                    mock_normalizer.table_store = {"users": pd.DataFrame({"user_id": [1]})}
                    mock_normalizer_class.return_value = mock_normalizer

                    result: PreviewResult = await shapeshift_service.preview_entity("test_config", "users", 50)

                    assert result is not None

    @pytest.mark.asyncio
    async def test_preview_with_dependencies(
        self, shapeshift_service: ShapeShiftService, sample_config: ShapeShiftConfig, sample_dataframe: pd.DataFrame
    ):
        """Test preview loads dependencies correctly."""
        # Mock ApplicationState
        mock_app_state = MagicMock()
        mock_app_state.get_version.return_value = 1
        mock_api_config = MagicMock()
        mock_api_config.metadata.name = "test_config"
        mock_app_state.get_configuration.return_value = mock_api_config

        with patch("backend.app.services.shapeshift_service.get_app_state", return_value=mock_app_state):
            with patch("backend.app.services.shapeshift_service.ConfigMapper.to_core", return_value=sample_config):
                with patch("backend.app.services.shapeshift_service.ShapeShifter") as mock_normalizer_class:
                    mock_normalizer = MagicMock()
                    mock_normalizer.normalize = AsyncMock()
                    # table_store now contains target + dependencies
                    mock_normalizer.table_store = {
                        "orders": sample_dataframe,
                        "users": pd.DataFrame({"user_id": [1, 2], "username": ["alice", "bob"]}),
                    }
                    mock_normalizer_class.return_value = mock_normalizer

                    result = await shapeshift_service.preview_entity("test_config", "orders", 50)

                assert result.has_dependencies is True
                assert "users" in result.dependencies_loaded

    @pytest.mark.asyncio
    async def test_preview_caching(
        self, shapeshift_service: ShapeShiftService, sample_config: ShapeShiftConfig, sample_dataframe: pd.DataFrame
    ):
        """Test preview results are cached."""
        # Mock ApplicationState
        mock_app_state = MagicMock()
        mock_app_state.get_version.return_value = 1
        mock_api_config = MagicMock()
        mock_api_config.metadata.name = "test_config"
        mock_app_state.get_configuration.return_value = mock_api_config

        with patch("backend.app.services.shapeshift_service.get_app_state", return_value=mock_app_state):
            with patch("backend.app.services.shapeshift_service.ConfigMapper.to_core_dict", return_value=sample_config.cfg):
                with patch("backend.app.services.shapeshift_service.ShapeShifter") as mock_normalizer_class:
                    mock_normalizer = MagicMock()
                    mock_normalizer.normalize = AsyncMock()
                    mock_normalizer.table_store = {"users": sample_dataframe}
                    mock_normalizer_class.return_value = mock_normalizer

                    # First call - should hit normalizer
                    result1 = await shapeshift_service.preview_entity("test_config", "users", 50)
                    assert result1.cache_hit is False

                    # Second call - should hit cache
                    result2 = await shapeshift_service.preview_entity("test_config", "users", 50)
                    assert result2.cache_hit is True

                    # Verify normalizer was only called once
                    assert mock_normalizer.normalize.call_count == 1

    @pytest.mark.asyncio
    async def test_get_entity_sample(
        self, shapeshift_service: ShapeShiftService, sample_config: ShapeShiftConfig, sample_dataframe: pd.DataFrame
    ):
        """Test get_entity_sample with higher limit."""
        # Mock ApplicationState
        mock_app_state = MagicMock()
        mock_app_state.get_version.return_value = 1
        mock_api_config = MagicMock()
        mock_api_config.metadata.name = "test_config"
        mock_app_state.get_configuration.return_value = mock_api_config

        with patch("backend.app.services.shapeshift_service.get_app_state", return_value=mock_app_state):
            with patch("backend.app.services.shapeshift_service.ConfigMapper.to_core_dict", return_value=sample_config.cfg):
                with patch("backend.app.services.shapeshift_service.ShapeShifter") as mock_normalizer_class:
                    mock_normalizer = MagicMock()
                    mock_normalizer.normalize = AsyncMock()
                    mock_normalizer.table_store = {"users": sample_dataframe}
                    mock_normalizer_class.return_value = mock_normalizer

                    result = await shapeshift_service.get_entity_sample("test_config", "users", limit=100)

                assert result.entity_name == "users"
                assert result.total_rows_in_preview == 5  # Sample df only has 5 rows

    def test_invalidate_cache(self, shapeshift_service: ShapeShiftService):
        """Test cache invalidation."""
        import pandas as pd

        # Add something to cache
        table_store = {"entity1": pd.DataFrame({"id": [1, 2, 3]})}
        shapeshift_service.cache.set_table_store("config1", "entity1", table_store)

        # Verify it's cached
        assert shapeshift_service.cache.get_table_store("config1", "entity1") is not None

        # Invalidate
        shapeshift_service.invalidate_cache("config1", "entity1")

        # Verify it's gone
        assert shapeshift_service.cache.get_table_store("config1", "entity1") is None

    def test_build_preview_result(
        self, shapeshift_service: ShapeShiftService, sample_dataframe: pd.DataFrame, sample_config: ShapeShiftConfig
    ):
        """Test _build_preview_result correctly builds PreviewResult from table_store."""
        entity_config: TableConfig = sample_config.get_table("users")
        table_store = {"users": sample_dataframe, "orders": pd.DataFrame({"order_id": [1, 2], "user_id": [1, 2]})}

        builder: PreviewResultBuilder = PreviewResultBuilder()
        result: PreviewResult = builder.build(
            entity_name="users", entity_config=entity_config, table_store=table_store, limit=50, cache_hit=False
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


@pytest.mark.skip(reason="These tests must be consolidated with above tests!")
class TestPreviewService:
    """Test ShapeShiftService for entity data preview."""

    @pytest.fixture
    def mock_config_service(self) -> MagicMock:
        """Create mock ConfigurationService."""
        service = MagicMock()
        service.load_configuration = MagicMock()
        return service

    @pytest.fixture
    def service(self, mock_config_service: MagicMock) -> ShapeShiftService:
        """Create ShapeShiftService instance."""
        return ShapeShiftService(config_service=mock_config_service)

    @pytest.fixture
    def sample_entity_config(self) -> TableConfig:
        """Create sample entity configuration."""
        cfg = {
            "test_entity": {
                "source": "test_table",
                "columns": ["id", "name"],
                "keys": ["id"],
            }
        }
        return TableConfig(cfg=cfg, entity_name="test_entity")

    @pytest.fixture
    def sample_dataframe(self) -> pd.DataFrame:
        """Create sample DataFrame."""
        return pd.DataFrame({"id": [1, 2, 3], "name": ["Alice", "Bob", "Charlie"]})

    # Preview entity tests

    @pytest.mark.asyncio
    async def test_preview_entity_success(
        self, service: ShapeShiftService, mock_config_service: MagicMock, sample_entity_config: TableConfig, sample_dataframe: pd.DataFrame
    ):
        """Test successful entity preview."""
        # Mock ShapeShifter
        mock_normalizer = MagicMock()
        mock_normalizer.table_store = {"test_entity": sample_dataframe}
        mock_normalizer.normalize = AsyncMock()

        # Mock config loading
        mock_api_config = MagicMock()
        mock_config_service.load_configuration = MagicMock(return_value=mock_api_config)

        with (
            patch("backend.app.services.shapeshift_service.ShapeShifter") as mock_shifter,
            patch("backend.app.services.shapeshift_service.ConfigMapper") as mock_mapper,
            patch("backend.app.services.shapeshift_service.ShapeShiftConfig") as mock_cfg,
        ):
            mock_shifter.return_value = mock_normalizer
            mock_mapper.to_core_dict = MagicMock(return_value={})
            mock_cfg.return_value.tables = {"test_entity": sample_entity_config}

            result = await service.preview_entity("test_config", "test_entity", limit=10)

            assert result.entity_name == "test_entity"
            assert result.total_rows_in_preview == 3
            assert len(result.rows) == 3
            assert result.cache_hit is False

    @pytest.mark.asyncio
    async def test_preview_entity_entity_not_found(self, service: ShapeShiftService, mock_config_service: MagicMock):
        """Test preview with non-existent entity raises error."""
        mock_api_config = MagicMock()
        mock_config_service.load_configuration = MagicMock(return_value=mock_api_config)

        with (
            patch("backend.app.services.shapeshift_service.ConfigMapper") as mock_mapper,
            patch("backend.app.services.shapeshift_service.ShapeShiftConfig") as mock_cfg,
        ):
            mock_mapper.to_core_dict = MagicMock(return_value={})
            mock_cfg.return_value.tables = {}

            with pytest.raises(ValueError, match="Entity .* not found"):
                await service.preview_entity("test_config", "nonexistent", limit=10)

    @pytest.mark.asyncio
    async def test_preview_entity_applies_limit(
        self, service: ShapeShiftService, mock_config_service: MagicMock, sample_entity_config: TableConfig
    ):
        """Test preview applies row limit."""
        large_df = pd.DataFrame({"id": range(100), "name": [f"User{i}" for i in range(100)]})

        mock_normalizer = MagicMock()
        mock_normalizer.table_store = {"test_entity": large_df}
        mock_normalizer.normalize = AsyncMock()

        mock_api_config = MagicMock()
        mock_config_service.load_configuration = MagicMock(return_value=mock_api_config)

        with (
            patch("backend.app.services.shapeshift_service.ShapeShifter") as mock_shifter,
            patch("backend.app.services.shapeshift_service.ConfigMapper") as mock_mapper,
            patch("backend.app.services.shapeshift_service.ShapeShiftConfig") as mock_cfg,
        ):
            mock_shifter.return_value = mock_normalizer
            mock_mapper.to_core_dict = MagicMock(return_value={})
            mock_cfg.return_value.tables = {"test_entity": sample_entity_config}

            result = await service.preview_entity("test_config", "test_entity", limit=10)

            assert result.total_rows_in_preview == 10
            assert result.estimated_total_rows == 100

    @pytest.mark.asyncio
    async def test_preview_entity_with_dependencies(
        self, service: ShapeShiftService, mock_config_service: MagicMock, sample_dataframe: pd.DataFrame
    ):
        """Test preview detects entity dependencies."""
        cfg = {
            "test_entity": {
                "source": "test_table",
                "columns": ["id", "name"],
                "keys": ["id"],
                "depends_on": ["parent_entity"],
            }
        }
        entity_config = TableConfig(cfg=cfg, entity_name="test_entity")

        mock_normalizer = MagicMock()
        mock_normalizer.table_store = {"test_entity": sample_dataframe}
        mock_normalizer.normalize = AsyncMock()

        mock_api_config = MagicMock()
        mock_config_service.load_configuration = MagicMock(return_value=mock_api_config)

        with (
            patch("backend.app.services.shapeshift_service.ShapeShifter") as mock_shifter,
            patch("backend.app.services.shapeshift_service.ConfigMapper") as mock_mapper,
            patch("backend.app.services.shapeshift_service.ShapeShiftConfig") as mock_cfg,
        ):
            mock_shifter.return_value = mock_normalizer
            mock_mapper.to_core_dict = MagicMock(return_value={})
            mock_cfg.return_value.tables = {"test_entity": entity_config}

            result = await service.preview_entity("test_config", "test_entity", limit=10)

            assert result.has_dependencies is True
            assert "parent_entity" in result.dependencies_loaded

    @pytest.mark.asyncio
    async def test_preview_entity_normalizer_error(
        self, service: ShapeShiftService, mock_config_service: MagicMock, sample_entity_config: TableConfig
    ):
        """Test preview handles normalizer errors."""
        mock_normalizer = MagicMock()
        mock_normalizer.normalize = AsyncMock(side_effect=RuntimeError("Normalization failed"))

        mock_api_config = MagicMock()
        mock_config_service.load_configuration = MagicMock(return_value=mock_api_config)

        with (
            patch("backend.app.services.shapeshift_service.ShapeShifter") as mock_shifter,
            patch("backend.app.services.shapeshift_service.ConfigMapper") as mock_mapper,
            patch("backend.app.services.shapeshift_service.ShapeShiftConfig") as mock_cfg,
        ):
            mock_shifter.return_value = mock_normalizer
            mock_mapper.to_core_dict = MagicMock(return_value={})
            mock_cfg.return_value.tables = {"test_entity": sample_entity_config}

            with pytest.raises(RuntimeError, match="Normalization failed"):
                await service.preview_entity("test_config", "test_entity", limit=10)

    # Get entity sample tests

    @pytest.mark.asyncio
    async def test_get_entity_sample_default_limit(
        self, service: ShapeShiftService, mock_config_service: MagicMock, sample_entity_config: TableConfig, sample_dataframe: pd.DataFrame
    ):
        """Test get_entity_sample uses default limit of 100."""
        mock_normalizer = MagicMock()
        mock_normalizer.table_store = {"test_entity": sample_dataframe}
        mock_normalizer.normalize = AsyncMock()

        mock_api_config = MagicMock()
        mock_config_service.load_configuration = MagicMock(return_value=mock_api_config)

        with (
            patch("backend.app.services.shapeshift_service.ShapeShifter") as mock_shifter,
            patch("backend.app.services.shapeshift_service.ConfigMapper") as mock_mapper,
            patch("backend.app.services.shapeshift_service.ShapeShiftConfig") as mock_cfg,
        ):
            mock_shifter.return_value = mock_normalizer
            mock_mapper.to_core_dict = MagicMock(return_value={})
            mock_cfg.return_value.tables = {"test_entity": sample_entity_config}

            result = await service.get_entity_sample("test_config", "test_entity")

            assert result.total_rows_in_preview <= 100

    @pytest.mark.asyncio
    async def test_get_entity_sample_clamps_limit(
        self, service: ShapeShiftService, mock_config_service: MagicMock, sample_entity_config: TableConfig
    ):
        """Test get_entity_sample clamps limit to max 1000."""
        # Create large dataframe with more than 1000 rows
        large_df = pd.DataFrame({"id": range(2000), "name": [f"User{i}" for i in range(2000)]})

        mock_normalizer = MagicMock()
        mock_normalizer.table_store = {"test_entity": large_df}
        mock_normalizer.normalize = AsyncMock()

        # Mock ShapeShiftConfig with the entity
        mock_shapeshift_config = MagicMock()
        mock_shapeshift_config.tables = {"test_entity": sample_entity_config}

        with (
            patch("backend.app.services.shapeshift_service.ShapeShifter") as mock_shifter,
            patch.object(service, "_get_shapeshift_config", return_value=mock_shapeshift_config) as _,
        ):
            mock_shifter.return_value = mock_normalizer

            # Request more than max
            result = await service.get_entity_sample("test_config", "test_entity", limit=5000)

            # Should be clamped to 1000
            assert result.total_rows_in_preview == 1000
            assert result.estimated_total_rows == 2000

    @pytest.mark.asyncio
    async def test_get_shapeshift_config_from_app_state(self, service: ShapeShiftService):
        """Test loading ShapeShift config from ApplicationState."""
        mock_api_config = MagicMock()

        with (
            patch("backend.app.services.shapeshift_service.get_app_state") as mock_state,
            patch("backend.app.services.shapeshift_service.ConfigMapper") as mock_mapper,
            patch("backend.app.services.shapeshift_service.ShapeShiftConfig") as mock_cfg,
        ):
            mock_state.return_value.get_version = MagicMock(return_value=1)
            mock_state.return_value.get_configuration = MagicMock(return_value=mock_api_config)
            mock_mapper.to_core_dict = MagicMock(return_value={})
            mock_cfg.return_value = MagicMock()

            result = await service._get_shapeshift_config("test_config")

            assert result is not None
            mock_state.return_value.get_configuration.assert_called_once_with("test_config")

    @pytest.mark.asyncio
    async def test_get_shapeshift_config_from_disk(self, service: ShapeShiftService, mock_config_service: MagicMock):
        """Test loading ShapeShift config from disk when not in app state."""
        mock_api_config = MagicMock()
        mock_config_service.load_configuration = MagicMock(return_value=mock_api_config)

        with (
            patch("backend.app.services.shapeshift_service.get_app_state") as mock_state,
            patch("backend.app.services.shapeshift_service.ConfigMapper") as mock_mapper,
            patch("backend.app.services.shapeshift_service.ShapeShiftConfig") as mock_cfg,
        ):
            mock_state.side_effect = RuntimeError("Not initialized")
            mock_mapper.to_core_dict = MagicMock(return_value={})
            mock_cfg.return_value = MagicMock()

            result = await service._get_shapeshift_config("test_config")

            assert result is not None
            mock_config_service.load_configuration.assert_called_once_with("test_config")

    @pytest.mark.asyncio
    async def test_get_shapeshift_config_caching(self, service: ShapeShiftService):
        """Test ShapeShift config is cached."""
        mock_api_config = MagicMock()

        with (
            patch("backend.app.services.shapeshift_service.get_app_state") as mock_state,
            patch("backend.app.services.shapeshift_service.ConfigMapper") as mock_mapper,
            patch("backend.app.services.shapeshift_service.ShapeShiftConfig") as mock_cfg,
        ):
            mock_state.return_value.get_version = MagicMock(return_value=1)
            mock_state.return_value.get_configuration = MagicMock(return_value=mock_api_config)
            mock_mapper.to_core_dict = MagicMock(return_value={})
            mock_cfg_instance = MagicMock()
            mock_cfg.return_value = mock_cfg_instance

            result1 = await service._get_shapeshift_config("test_config")
            result2 = await service._get_shapeshift_config("test_config")

            # Should return same cached instance
            assert result1 is result2
            # Should only load once
            assert mock_state.return_value.get_configuration.call_count == 1

    @pytest.mark.asyncio
    async def test_get_shapeshift_config_version_tracking(self, service: ShapeShiftService):
        """Test config cache is invalidated when version changes."""
        mock_api_config = MagicMock()

        with (
            patch("backend.app.services.shapeshift_service.get_app_state") as mock_state,
            patch("backend.app.services.shapeshift_service.ConfigMapper") as mock_mapper,
            patch("backend.app.services.shapeshift_service.ShapeShiftConfig") as mock_cfg,
        ):
            # First call with version 1
            mock_state.return_value.get_version = MagicMock(return_value=1)
            mock_state.return_value.get_configuration = MagicMock(return_value=mock_api_config)
            mock_mapper.to_core_dict = MagicMock(return_value={})
            mock_cfg.return_value = MagicMock()

            await service._get_shapeshift_config("test_config")

            # Second call with version 2
            mock_state.return_value.get_version = MagicMock(return_value=2)

            await service._get_shapeshift_config("test_config")

            # Should reload due to version change
            assert mock_state.return_value.get_configuration.call_count == 2
