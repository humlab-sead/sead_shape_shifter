"""Tests for ShapeShiftService (ShapeShift service)."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from backend.app.models.shapeshift import ColumnInfo, PreviewResult
from backend.app.services.shapeshift_service import ShapeShiftCache, ShapeShiftService
from src.model import TableConfig

# pylint: disable=redefined-outer-name, unused-argument


class TestPreviewCache:
    """Test PreviewCache for TTL-based caching."""

    @pytest.fixture
    def cache(self) -> ShapeShiftCache:
        """Create cache with short TTL for testing."""
        return ShapeShiftCache(ttl_seconds=1)

    def test_cache_miss_on_empty(self, cache: ShapeShiftCache):
        """Test cache miss when cache is empty."""
        result = cache.get("config", "entity", 10)
        assert result is None

    def test_cache_hit_after_set(self, cache: ShapeShiftCache):
        """Test cache hit after setting value."""
        preview = PreviewResult(
            entity_name="test",
            rows=[{"id": 1}],
            columns=[ColumnInfo(name="id", data_type="int64", nullable=False, is_key=True)],
            total_rows_in_preview=1,
            estimated_total_rows=1,
            execution_time_ms=10,
            has_dependencies=False,
            dependencies_loaded=[],
            cache_hit=False,
        )

        cache.set("config", "entity", 10, preview)
        result = cache.get(
            "config",
            "entity",
            10,
        )

        assert result is not None
        assert result.entity_name == "test"

    def test_cache_expiration(self, cache: ShapeShiftCache):
        """Test cache entries expire after TTL."""
        preview = PreviewResult(
            entity_name="test",
            rows=[],
            columns=[],
            total_rows_in_preview=0,
            estimated_total_rows=0,
            execution_time_ms=0,
            has_dependencies=False,
            dependencies_loaded=[],
            cache_hit=False,
        )

        cache.set("config", "entity", 10, preview)

        # Wait for expiration
        time.sleep(1.1)

        result = cache.get("config", "entity", 10)
        assert result is None

    def test_cache_invalidate_specific_entity(self, cache: ShapeShiftCache):
        """Test invalidating specific entity cache."""
        preview = PreviewResult(
            entity_name="test",
            rows=[],
            columns=[],
            total_rows_in_preview=0,
            estimated_total_rows=0,
            execution_time_ms=0,
            has_dependencies=False,
            dependencies_loaded=[],
            cache_hit=False,
        )

        cache.set("config", "entity1", 10, preview)
        cache.set("config", "entity2", 10, preview)

        cache.invalidate("config", "entity1")

        assert cache.get("config", "entity1", 10) is None
        assert cache.get("config", "entity2", 10) is not None

    def test_cache_invalidate_all_entities(self, cache: ShapeShiftCache):
        """Test invalidating all entities for a config."""
        preview = PreviewResult(
            entity_name="test",
            rows=[],
            columns=[],
            total_rows_in_preview=0,
            estimated_total_rows=0,
            execution_time_ms=0,
            has_dependencies=False,
            dependencies_loaded=[],
            cache_hit=False,
        )

        cache.set("config", "entity1", 10, preview)
        cache.set("config", "entity2", 10, preview)

        cache.invalidate("config")

        assert cache.get("config", "entity1", 10) is None
        assert cache.get("config", "entity2", 10) is None

    def test_cache_key_generation(self, cache: ShapeShiftCache):
        """Test cache key is generated correctly."""
        key1 = cache._generate_key("config1", "entity1", 10)
        key2 = cache._generate_key("config1", "entity2", 10)
        key3 = cache._generate_key("config2", "entity1", 10)

        assert key1 != key2
        assert key1 != key3
        assert key2 != key3

    def test_cache_isolation_between_configs(self, cache: ShapeShiftCache):
        """Test cache entries are isolated by config name."""
        preview1 = PreviewResult(
            entity_name="entity1",
            rows=[{"id": 1}],
            columns=[],
            total_rows_in_preview=1,
            estimated_total_rows=1,
            execution_time_ms=10,
            has_dependencies=False,
            dependencies_loaded=[],
            cache_hit=False,
        )
        preview2 = PreviewResult(
            entity_name="entity2",
            rows=[{"id": 2}],
            columns=[],
            total_rows_in_preview=1,
            estimated_total_rows=1,
            execution_time_ms=10,
            has_dependencies=False,
            dependencies_loaded=[],
            cache_hit=False,
        )

        cache.set("config1", "entity", 10, preview1)
        cache.set("config2", "entity", 10, preview2)

        result1 = cache.get("config1", "entity", 10)
        result2 = cache.get("config2", "entity", 10)
        assert result1 is not None
        assert result2 is not None
        assert result1.entity_name == "entity1"
        assert result2.entity_name == "entity2"


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
    async def test_preview_entity_cache_hit(
        self, service: ShapeShiftService, mock_config_service: MagicMock, sample_entity_config: TableConfig, sample_dataframe: pd.DataFrame
    ):
        """Test preview returns cached result."""
        # Set up cache
        cached_result = PreviewResult(
            entity_name="test_entity",
            rows=[{"id": 1}],
            columns=[ColumnInfo(name="id", data_type="int64", nullable=False, is_key=True)],
            total_rows_in_preview=1,
            estimated_total_rows=1,
            execution_time_ms=10,
            has_dependencies=False,
            dependencies_loaded=[],
            cache_hit=False,
        )
        service.cache.set("test_config", "test_entity", 10, cached_result)

        # Mock config to return cached version
        with patch("backend.app.services.shapeshift_service.get_app_state") as mock_state:
            mock_state.return_value.get_version = MagicMock(return_value=1)

            result = await service.preview_entity("test_config", "test_entity", limit=10)

            assert result.cache_hit is True
            assert result.total_rows_in_preview == 1

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

    # Build column info tests

    def test_build_column_info_basic(self, service: ShapeShiftService, sample_dataframe: pd.DataFrame, sample_entity_config: TableConfig):
        """Test building column info from DataFrame."""
        columns = service._build_column_info(sample_dataframe, sample_entity_config)

        assert len(columns) == 2
        assert columns[0].name == "id"
        assert columns[0].is_key is True
        assert columns[1].name == "name"
        assert columns[1].is_key is False

    def test_build_column_info_nullable(self, service: ShapeShiftService, sample_entity_config: TableConfig):
        """Test nullable column detection."""
        df = pd.DataFrame({"id": [1, 2], "name": ["Alice", None]})
        columns = service._build_column_info(df, sample_entity_config)

        id_col = next(c for c in columns if c.name == "id")
        name_col = next(c for c in columns if c.name == "name")

        assert id_col.nullable is False
        assert name_col.nullable is True

    def test_build_column_info_data_types(self, service: ShapeShiftService):
        """Test data type detection."""
        df = pd.DataFrame({"int_col": [1, 2], "float_col": [1.5, 2.5], "str_col": ["a", "b"], "bool_col": [True, False]})

        cfg = {"table": {"source": "table", "columns": list(df.columns)}}
        entity_config = TableConfig(cfg=cfg, entity_name="table")
        columns = service._build_column_info(df, entity_config)

        type_map = {c.name: c.data_type for c in columns}
        assert "int" in type_map["int_col"].lower()
        assert "decimal" in type_map["float_col"].lower()
        assert "text" in type_map["str_col"].lower()
        assert "bool" in type_map["bool_col"].lower()

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

    # Cache invalidation tests

    def test_invalidate_cache_specific_entity(self, service: ShapeShiftService):
        """Test invalidating cache for specific entity."""
        # Pre-populate cache
        preview = PreviewResult(
            entity_name="entity1",
            rows=[],
            columns=[],
            total_rows_in_preview=0,
            estimated_total_rows=0,
            execution_time_ms=0,
            has_dependencies=False,
            dependencies_loaded=[],
            cache_hit=False,
        )
        service.cache.set("config", "entity1", 10, result=preview)
        service.cache.set("config", "entity2", 10, result=preview)

        service.invalidate_cache("config", "entity1")

        assert service.cache.get("config", "entity1", 10) is None
        assert service.cache.get("config", "entity2", 10) is not None

    def test_invalidate_cache_all_entities(self, service: ShapeShiftService):
        """Test invalidating all entities for a config."""
        preview = PreviewResult(
            entity_name="test",
            rows=[],
            columns=[],
            total_rows_in_preview=0,
            estimated_total_rows=0,
            execution_time_ms=0,
            has_dependencies=False,
            dependencies_loaded=[],
            cache_hit=False,
        )
        service.cache.set("config", "entity1", 10, result=preview)
        service.cache.set("config", "entity2", 10, result=preview)

        service.invalidate_cache("config")

        assert service.cache.get("config", "entity1", 10) is None
        assert service.cache.get("config", "entity2", 10) is None

    # ShapeShift config loading tests

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
