"""
Tests for Schema Introspection Service

Tests schema discovery for PostgreSQL, MS Access, and SQLite databases.
"""

from unittest.mock import AsyncMock, Mock, patch

import pandas as pd
import pytest

from backend.app.core.config import Settings
from backend.app.models.data_source import (
    ColumnMetadata,
    DataSourceConfig,
    TableMetadata,
    TableSchema,
)
from backend.app.services.schema_service import (
    SchemaCache,
    SchemaIntrospectionService,
    SchemaServiceError,
)
from src.loaders.sql_loaders import CoreSchema

# pylint: disable=redefined-outer-name, unused-argument


class TestSchemaCache:
    """Tests for SchemaCache."""

    def test_cache_set_and_get(self):
        """Should store and retrieve values."""
        cache = SchemaCache(ttl_seconds=60)
        cache.set("key1", "value1")

        assert cache.get("key1") == "value1"

    def test_cache_get_nonexistent(self):
        """Should return None for nonexistent keys."""
        cache = SchemaCache(ttl_seconds=60)

        assert cache.get("nonexistent") is None

    def test_cache_invalidate(self):
        """Should remove cached values."""
        cache = SchemaCache(ttl_seconds=60)
        cache.set("key1", "value1")
        cache.invalidate("key1")

        assert cache.get("key1") is None

    def test_cache_clear(self):
        """Should clear all cached values."""
        cache = SchemaCache(ttl_seconds=60)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()

        assert cache.get("key1") is None
        assert cache.get("key2") is None


class TestSchemaIntrospectionService:
    """Tests for SchemaIntrospectionService."""

    @pytest.fixture
    def mock_config(self):
        """Mock configuration."""
        config = Mock()
        config.get.return_value = {}
        return config

    @pytest.fixture
    def service(self, mock_config, settings: Settings) -> SchemaIntrospectionService:
        """Create service with mock config."""
        return SchemaIntrospectionService(settings.CONFIGURATIONS_DIR)

    @pytest.fixture
    def postgres_config(self):
        """PostgreSQL data source config."""
        return DataSourceConfig(
            name="test_postgres",
            driver="postgresql",
            host="localhost",
            port=5432,
            database="testdb",
            username="testuser",
            **{},
        )

    @pytest.fixture
    def access_config(self):
        """MS Access data source config."""
        return DataSourceConfig(name="test_access", driver="ucanaccess", filename="test.mdb", **{})

    @pytest.fixture
    def sqlite_config(self):
        """SQLite data source config."""
        return DataSourceConfig(name="test_sqlite", driver="sqlite", filename="test.db", **{})

    @pytest.mark.asyncio
    async def test_get_tables_not_found(self, service: SchemaIntrospectionService):
        """Should raise error when data source not found."""
        service.data_source_service.get_data_source = Mock(return_value=None)

        with pytest.raises(SchemaServiceError, match="not found"):
            await service.get_tables("nonexistent")

    @pytest.mark.asyncio
    async def test_get_tables_unsupported_driver(self, service):
        """Should raise error for unsupported driver."""
        csv_config = DataSourceConfig(name="test_csv", driver="csv", filename="test.csv", **{})
        service.data_source_service.get_data_source = Mock(return_value=csv_config)

        with pytest.raises(SchemaServiceError, match="not supported"):
            await service.get_tables("test_csv")

    def mock_read_sql(self, test_df: pd.DataFrame, mock_get_loader: Mock) -> AsyncMock:
        """Mock the loader's read_sql method."""
        mock_read_sql: AsyncMock = AsyncMock(return_value=test_df)
        mock_loader_instance = Mock()
        mock_loader_instance.read_sql = mock_read_sql
        mock_loader_class = Mock(return_value=mock_loader_instance)
        mock_get_loader.return_value = mock_loader_class
        return mock_read_sql

    @pytest.mark.asyncio
    async def test_preview_table_data(self, service: SchemaIntrospectionService, postgres_config: DataSourceConfig):
        """Should preview table data."""

        # Mock preview data
        preview_data: pd.DataFrame = pd.DataFrame(
            {
                "id": [1, 2, 3],
                "name": ["Alice", "Bob", "Charlie"],
                "active": [True, True, False],
            }
        )

        service.data_source_service.get_data_source = Mock(return_value=postgres_config)

        # Mock the loader with both read_sql and get_table_row_count methods
        mock_loader_instance = Mock()
        mock_loader_instance.read_sql = AsyncMock(return_value=preview_data)
        mock_loader_instance.get_table_row_count = AsyncMock(return_value=100)
        mock_loader_class = Mock(return_value=mock_loader_instance)

        with patch("backend.app.services.schema_service.DataLoaders.get") as mock_get_loader:
            mock_get_loader.return_value = mock_loader_class

            result = await service.preview_table_data("test_postgres", "users", limit=50, offset=0)

            assert result["columns"] == ["id", "name", "active"]
            assert len(result["rows"]) == 3
            assert result["rows"][0]["name"] == "Alice"
            assert result["total_rows"] == 100
            assert result["limit"] == 50
            assert result["offset"] == 0

    @pytest.mark.asyncio
    async def test_preview_table_data_limit_constraint(self, service: SchemaIntrospectionService, postgres_config: DataSourceConfig):
        """Should enforce maximum limit of 100 rows."""
        service.data_source_service.get_data_source = Mock(return_value=postgres_config)

        mock_loader_instance = Mock(read_sql=AsyncMock(return_value=pd.DataFrame()), get_table_row_count=AsyncMock(return_value=100))
        mock_loader_class = Mock(return_value=mock_loader_instance)

        with patch("backend.app.services.schema_service.DataLoaders.get") as mock_get_loader:
            mock_get_loader.return_value = mock_loader_class

            result = await service.preview_table_data("test_postgres", "users", limit=150)

        assert result["limit"] == 100

    @pytest.mark.asyncio
    async def test_cache_hit(self, service, postgres_config):
        """Should return cached results on subsequent calls."""

        service.data_source_service.get_data_source = Mock(return_value=postgres_config)

        # Mock core tables response
        core_tables = {
            "users": CoreSchema.TableMetadata(
                name="users",
                schema="public",
                row_count=None,
                comment=None,
            )
        }

        # Mock the loader
        with patch("backend.app.services.schema_service.DataLoaders.get") as mock_get_loader:
            with patch("backend.app.services.schema_service.isinstance") as mock_isinstance:
                # Make isinstance return True for SqlLoader check
                mock_isinstance.return_value = True

                mock_loader_instance = AsyncMock()
                mock_loader_instance.get_tables = AsyncMock(return_value=core_tables)
                mock_loader_class = Mock(return_value=mock_loader_instance)
                mock_get_loader.return_value = mock_loader_class

                # First call
                tables1 = await service.get_tables("test_postgres")

                # Second call (should hit cache)
                tables2 = await service.get_tables("test_postgres")

                # Loader should only be called once
                mock_loader_instance.get_tables.assert_called_once()
                assert len(tables1) == 1
                assert len(tables2) == 1

    def test_invalidate_cache_for_data_source(self, service):
        """Should invalidate cache entries for specific data source."""
        # Add some cache entries
        service.cache.set("tables:ds1:default", ["table1"])
        service.cache.set("schema:ds1:default:table1", {})
        service.cache.set("tables:ds2:default", ["table2"])

        # Invalidate ds1
        service.invalidate_cache("ds1")

        # ds1 entries should be gone
        assert service.cache.get("tables:ds1:default") is None
        assert service.cache.get("schema:ds1:default:table1") is None

        # ds2 entries should remain
        assert service.cache.get("tables:ds2:default") == ["table2"]


class TestSchemaEndpoints:
    """Integration-style tests for schema endpoints (would use TestClient in real scenario)."""

    def test_table_metadata_model(self):
        """Should create TableMetadata model."""
        table = TableMetadata(
            name="users",
            schema_name="public",
            row_count=100,
            comment="User accounts",
        )

        assert table.name == "users"
        assert table.schema_name == "public"
        assert table.row_count == 100
        assert table.comment == "User accounts"

    def test_column_metadata_model(self):
        """Should create ColumnMetadata model."""
        column = ColumnMetadata(
            name="id",
            data_type="integer",
            nullable=False,
            default="nextval('users_id_seq'::regclass)",
            is_primary_key=True,
            max_length=None,
        )

        assert column.name == "id"
        assert column.data_type == "integer"
        assert column.nullable is False
        assert column.is_primary_key is True

    def test_table_schema_model(self):
        """Should create TableSchema model."""
        columns: list[ColumnMetadata] = [
            ColumnMetadata(name="id", data_type="integer", nullable=False, is_primary_key=True, default=None, max_length=None),
            ColumnMetadata(name="name", data_type="varchar", nullable=False, is_primary_key=False, default=None, max_length=None),
        ]

        schema = TableSchema(
            table_name="users",
            columns=columns,
            primary_keys=["id"],
            indexes=["idx_name"],
            row_count=42,
        )

        assert schema.table_name == "users"
        assert len(schema.columns) == 2
        assert schema.primary_keys == ["id"]
        assert schema.row_count == 42
