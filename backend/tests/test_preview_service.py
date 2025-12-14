"""Tests for entity preview service."""

import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from backend.app.models.preview import PreviewResult
from backend.app.services.preview_service import PreviewCache, PreviewService
from src.config_model import TablesConfig

# pylint: disable=redefined-outer-name, unused-argument, attribute-defined-outside-init


@pytest.fixture
def config_service():
    """Mock config service."""
    service = MagicMock()
    service.get_config_path.return_value = Path("test_config.yml")
    return service


@pytest.fixture
def preview_service(config_service):
    """Create preview service instance."""
    return PreviewService(config_service)


@pytest.fixture
def sample_config():
    """Create a sample configuration."""
    entities_cfg = {
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
    }

    return TablesConfig(
        entities_cfg=entities_cfg,
        options={},
    )


@pytest.fixture
def sample_dataframe():
    """Create a sample DataFrame."""
    return pd.DataFrame(
        {
            "user_id": [1, 2, 3, 4, 5],
            "username": ["alice", "bob", "charlie", "david", "eve"],
            "email": ["alice@example.com", "bob@example.com", None, "david@example.com", "eve@example.com"],
        }
    )


class TestPreviewCache:
    """Tests for preview cache."""

    def test_cache_miss(self):
        """Test cache miss returns None."""
        cache = PreviewCache(ttl_seconds=60)
        result = cache.get("config1", "entity1", 50)
        assert result is None

    def test_cache_hit(self):
        """Test cache hit returns cached result."""
        cache = PreviewCache(ttl_seconds=60)
        preview_result = PreviewResult(
            entity_name="entity1",
            rows=[],
            columns=[],
            total_rows_in_preview=0,
            execution_time_ms=100,
        )
        cache.set("config1", "entity1", 50, preview_result)

        result = cache.get("config1", "entity1", 50)
        assert result is not None
        assert result.entity_name == "entity1"
        assert result.cache_hit is True

    def test_cache_expiry(self):
        """Test cache entries expire after TTL."""
        cache = PreviewCache(ttl_seconds=0)  # Immediate expiry
        preview_result = PreviewResult(
            entity_name="entity1",
            rows=[],
            columns=[],
            total_rows_in_preview=0,
            execution_time_ms=100,
        )
        cache.set("config1", "entity1", 50, preview_result)

        time.sleep(0.1)  # Wait for expiry

        result = cache.get("config1", "entity1", 50)
        assert result is None

    def test_cache_invalidate_specific(self):
        """Test invalidating specific entity cache."""
        cache = PreviewCache(ttl_seconds=60)
        preview1 = PreviewResult(entity_name="entity1", rows=[], columns=[], total_rows_in_preview=0, execution_time_ms=100)
        preview2 = PreviewResult(entity_name="entity2", rows=[], columns=[], total_rows_in_preview=0, execution_time_ms=100)

        cache.set("config1", "entity1", 50, preview1)
        cache.set("config1", "entity2", 50, preview2)

        cache.invalidate("config1", "entity1")

        assert cache.get("config1", "entity1", 50) is None
        assert cache.get("config1", "entity2", 50) is not None

    def test_cache_invalidate_all(self):
        """Test invalidating all cache entries for a config."""
        cache = PreviewCache(ttl_seconds=60)
        preview1 = PreviewResult(entity_name="entity1", rows=[], columns=[], total_rows_in_preview=0, execution_time_ms=100)
        preview2 = PreviewResult(entity_name="entity2", rows=[], columns=[], total_rows_in_preview=0, execution_time_ms=100)

        cache.set("config1", "entity1", 50, preview1)
        cache.set("config1", "entity2", 50, preview2)

        cache.invalidate("config1")

        assert cache.get("config1", "entity1", 50) is None
        assert cache.get("config1", "entity2", 50) is None


class TestPreviewService:
    """Tests for preview service."""

    @pytest.mark.asyncio
    async def test_preview_entity_not_found(self, preview_service, sample_config):
        """Test preview with non-existent entity."""
        with patch("backend.app.services.preview_service.TablesConfig.from_yaml", return_value=sample_config):
            with pytest.raises(ValueError, match="Entity 'nonexistent' not found"):
                await preview_service.preview_entity("test_config", "nonexistent", 50)

    @pytest.mark.asyncio
    async def test_preview_entity_success(self, preview_service, sample_config, sample_dataframe):
        """Test successful entity preview."""
        with patch("backend.app.services.preview_service.TablesConfig.from_yaml", return_value=sample_config):
            with patch("backend.app.services.preview_service.ArbodatSurveyNormalizer") as mock_normalizer_class:
                # Setup mock normalizer
                mock_normalizer = MagicMock()
                mock_normalizer.normalize = AsyncMock()
                mock_normalizer.table_store = {"users": sample_dataframe}
                mock_normalizer_class.return_value = mock_normalizer

                result = await preview_service.preview_entity("test_config", "users", 50)

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
    async def test_preview_with_limit(self, preview_service, sample_config):
        """Test preview respects limit parameter."""
        large_df = pd.DataFrame({"col1": range(100), "col2": range(100, 200)})

        with patch("backend.app.services.preview_service.TablesConfig.from_yaml", return_value=sample_config):
            with patch("backend.app.services.preview_service.ArbodatSurveyNormalizer") as mock_normalizer_class:
                mock_normalizer = MagicMock()
                mock_normalizer.normalize = AsyncMock()
                mock_normalizer.table_store = {"users": large_df}
                mock_normalizer_class.return_value = mock_normalizer

                result = await preview_service.preview_entity("test_config", "users", limit=10)

                assert result.total_rows_in_preview == 10
                assert result.estimated_total_rows == 100

    @pytest.mark.asyncio
    async def test_preview_with_transformations(self, preview_service, sample_config):
        """Test preview detects applied transformations."""
        # Modify config to have filters and unnest
        config_with_transforms = sample_config.model_copy(deep=True)
        config_with_transforms.entities["users"].filters = [{"type": "exists_in", "entity": "orders"}]
        config_with_transforms.entities["users"].unnest = {
            "id_vars": ["user_id"],
            "value_vars": ["col1", "col2"],
        }

        with patch("backend.app.services.preview_service.TablesConfig.from_yaml", return_value=config_with_transforms):
            with patch("backend.app.services.preview_service.ArbodatSurveyNormalizer") as mock_normalizer_class:
                mock_normalizer = MagicMock()
                mock_normalizer.normalize = AsyncMock()
                mock_normalizer.table_store = {"users": pd.DataFrame({"user_id": [1]})}
                mock_normalizer_class.return_value = mock_normalizer

                result = await preview_service.preview_entity("test_config", "users", 50)

                assert "filter" in result.transformations_applied
                assert "unnest" in result.transformations_applied

    @pytest.mark.asyncio
    async def test_preview_with_dependencies(self, preview_service, sample_config, sample_dataframe):
        """Test preview loads dependencies correctly."""
        with patch("backend.app.services.preview_service.TablesConfig.from_yaml", return_value=sample_config):
            with patch("backend.app.services.preview_service.ArbodatSurveyNormalizer") as mock_normalizer_class:
                mock_normalizer = MagicMock()
                mock_normalizer.normalize = AsyncMock()
                mock_normalizer.table_store = {"orders": sample_dataframe}
                mock_normalizer_class.return_value = mock_normalizer

                result = await preview_service.preview_entity("test_config", "orders", 50)

                assert result.has_dependencies is True
                assert "users" in result.dependencies_loaded
                assert "foreign_key_joins" in result.transformations_applied

    @pytest.mark.asyncio
    async def test_preview_caching(self, preview_service, sample_config, sample_dataframe):
        """Test preview results are cached."""
        with patch("backend.app.services.preview_service.TablesConfig.from_yaml", return_value=sample_config):
            with patch("backend.app.services.preview_service.ArbodatSurveyNormalizer") as mock_normalizer_class:
                mock_normalizer = MagicMock()
                mock_normalizer.normalize = AsyncMock()
                mock_normalizer.table_store = {"users": sample_dataframe}
                mock_normalizer_class.return_value = mock_normalizer

                # First call - should hit normalizer
                result1 = await preview_service.preview_entity("test_config", "users", 50)
                assert result1.cache_hit is False

                # Second call - should hit cache
                result2 = await preview_service.preview_entity("test_config", "users", 50)
                assert result2.cache_hit is True

                # Verify normalizer was only called once
                assert mock_normalizer.normalize.call_count == 1

    @pytest.mark.asyncio
    async def test_get_entity_sample(self, preview_service, sample_config, sample_dataframe):
        """Test get_entity_sample with higher limit."""
        with patch("backend.app.services.preview_service.TablesConfig.from_yaml", return_value=sample_config):
            with patch("backend.app.services.preview_service.ArbodatSurveyNormalizer") as mock_normalizer_class:
                mock_normalizer = MagicMock()
                mock_normalizer.normalize = AsyncMock()
                mock_normalizer.table_store = {"users": sample_dataframe}
                mock_normalizer_class.return_value = mock_normalizer

                result = await preview_service.get_entity_sample("test_config", "users", limit=100)

                assert result.entity_name == "users"
                assert result.total_rows_in_preview == 5  # Sample df only has 5 rows

    def test_invalidate_cache(self, preview_service):
        """Test cache invalidation."""
        # Add something to cache
        preview_result = PreviewResult(entity_name="entity1", rows=[], columns=[], total_rows_in_preview=0, execution_time_ms=100)
        preview_service.cache.set("config1", "entity1", 50, preview_result)

        # Verify it's cached
        assert preview_service.cache.get("config1", "entity1", 50) is not None

        # Invalidate
        preview_service.invalidate_cache("config1", "entity1")

        # Verify it's gone
        assert preview_service.cache.get("config1", "entity1", 50) is None

    def test_build_column_info(self, preview_service, sample_dataframe, sample_config):
        """Test _build_column_info correctly identifies column types."""
        entity_config = sample_config.entities["users"]
        columns = preview_service._build_column_info(sample_dataframe, entity_config)

        assert len(columns) == 3

        # Check user_id (key column)
        user_id_col = next(c for c in columns if c.name == "user_id")
        assert user_id_col.is_key is True
        assert user_id_col.data_type == "integer"

        # Check username (natural key)
        username_col = next(c for c in columns if c.name == "username")
        assert username_col.is_key is True
        assert username_col.nullable is False

        # Check email (nullable)
        email_col = next(c for c in columns if c.name == "email")
        assert email_col.is_key is False
        assert email_col.nullable is True
