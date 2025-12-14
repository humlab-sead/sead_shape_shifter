"""
Tests for Schema Introspection Service

Tests schema discovery for PostgreSQL, MS Access, and SQLite databases.
"""

from unittest.mock import AsyncMock, Mock, patch

import pandas as pd
import pytest
from app.models.data_source import (
    ColumnMetadata,
    DataSourceConfig,
    DataSourceType,
    TableMetadata,
    TableSchema,
)
from app.services.schema_service import (
    SchemaCache,
    SchemaIntrospectionService,
    SchemaServiceError,
)


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
    def service(self, mock_config):
        """Create service with mock config."""
        return SchemaIntrospectionService(mock_config)

    @pytest.fixture
    def postgres_config(self):
        """PostgreSQL data source config."""
        return DataSourceConfig(
            name="test_postgres",
            driver=DataSourceType.POSTGRESQL,
            host="localhost",
            port=5432,
            database="testdb",
            username="testuser",
        )

    @pytest.fixture
    def access_config(self):
        """MS Access data source config."""
        return DataSourceConfig(
            name="test_access",
            driver=DataSourceType.ACCESS,
            filename="test.mdb",
        )

    @pytest.fixture
    def sqlite_config(self):
        """SQLite data source config."""
        return DataSourceConfig(
            name="test_sqlite",
            driver=DataSourceType.SQLITE,
            filename="test.db",
        )

    @pytest.mark.asyncio
    async def test_get_tables_not_found(self, service):
        """Should raise error when data source not found."""
        service.data_source_service.get_data_source = Mock(return_value=None)

        with pytest.raises(SchemaServiceError, match="not found"):
            await service.get_tables("nonexistent")

    @pytest.mark.asyncio
    async def test_get_tables_unsupported_driver(self, service):
        """Should raise error for unsupported driver."""
        csv_config = DataSourceConfig(
            name="test_csv",
            driver=DataSourceType.CSV,
            filename="test.csv",
        )
        service.data_source_service.get_data_source = Mock(return_value=csv_config)

        with pytest.raises(SchemaServiceError, match="not supported"):
            await service.get_tables("test_csv")

    @pytest.mark.asyncio
    async def test_get_postgresql_tables(self, service, postgres_config):
        """Should get tables from PostgreSQL."""
        service.data_source_service.get_data_source = Mock(return_value=postgres_config)

        # Mock query result
        tables_data = pd.DataFrame(
            {
                "table_name": ["users", "orders"],
                "schema": ["public", "public"],
                "comment": [None, "Order records"],
            }
        )

        service._execute_query = AsyncMock(return_value=tables_data)

        tables = await service.get_tables("test_postgres")

        assert len(tables) == 2
        assert tables[0].name == "users"
        assert tables[0].schema == "public"
        assert tables[1].name == "orders"
        assert tables[1].comment == "Order records"

    @pytest.mark.asyncio
    async def test_get_postgresql_table_schema(self, service, postgres_config):
        """Should get table schema from PostgreSQL."""
        service.data_source_service.get_data_source = Mock(return_value=postgres_config)

        # Mock columns query
        columns_data = pd.DataFrame(
            {
                "column_name": ["id", "name", "email"],
                "data_type": ["integer", "character varying", "character varying"],
                "is_nullable": ["NO", "NO", "YES"],
                "column_default": ["nextval(...)", None, None],
                "character_maximum_length": [None, 100, 255],
            }
        )

        # Mock primary keys query
        pk_data = pd.DataFrame(
            {
                "column_name": ["id"],
            }
        )

        # Mock row count query
        count_data = pd.DataFrame(
            {
                "count": [42],
            }
        )

        async def mock_execute(config, query):
            if "information_schema.columns" in query:
                return columns_data
            elif "pg_index" in query:
                return pk_data
            elif "COUNT(*)" in query:
                return count_data
            return pd.DataFrame()

        service._execute_query = mock_execute

        schema = await service.get_table_schema("test_postgres", "users")

        assert schema.table_name == "users"
        assert len(schema.columns) == 3
        assert schema.columns[0].name == "id"
        assert schema.columns[0].is_primary_key is True
        assert schema.columns[1].name == "name"
        assert schema.columns[1].nullable is False
        assert schema.columns[2].name == "email"
        assert schema.columns[2].nullable is True
        assert schema.row_count == 42

    @pytest.mark.asyncio
    async def test_get_access_tables(self, service, access_config):
        """Should get tables from MS Access."""
        service.data_source_service.get_data_source = Mock(return_value=access_config)

        # Mock query result
        tables_data = pd.DataFrame(
            {
                "TABLE_NAME": ["Customers", "Products"],
            }
        )

        service._execute_query = AsyncMock(return_value=tables_data)

        tables = await service.get_tables("test_access")

        assert len(tables) == 2
        assert tables[0].name == "Customers"
        assert tables[1].name == "Products"

    @pytest.mark.asyncio
    async def test_get_sqlite_tables(self, service, sqlite_config):
        """Should get tables from SQLite."""
        service.data_source_service.get_data_source = Mock(return_value=sqlite_config)

        # Mock query result
        tables_data = pd.DataFrame(
            {
                "table_name": ["users", "posts"],
            }
        )

        service._execute_query = AsyncMock(return_value=tables_data)

        tables = await service.get_tables("test_sqlite")

        assert len(tables) == 2
        assert tables[0].name == "users"
        assert tables[1].name == "posts"

    @pytest.mark.asyncio
    async def test_preview_table_data(self, service, postgres_config):
        """Should preview table data."""
        service.data_source_service.get_data_source = Mock(return_value=postgres_config)

        # Mock preview data
        preview_data = pd.DataFrame(
            {
                "id": [1, 2, 3],
                "name": ["Alice", "Bob", "Charlie"],
                "active": [True, True, False],
            }
        )

        # Mock count data
        count_data = pd.DataFrame({"count": [100]})

        async def mock_execute(config, query):
            if "COUNT(*)" in query:
                return count_data
            else:
                return preview_data

        service._execute_query = mock_execute

        result = await service.preview_table_data("test_postgres", "users", limit=50, offset=0)

        assert result["columns"] == ["id", "name", "active"]
        assert len(result["rows"]) == 3
        assert result["rows"][0]["name"] == "Alice"
        assert result["total_rows"] == 100
        assert result["limit"] == 50
        assert result["offset"] == 0

    @pytest.mark.asyncio
    async def test_preview_table_data_limit_constraint(self, service, postgres_config):
        """Should enforce maximum limit of 100 rows."""
        service.data_source_service.get_data_source = Mock(return_value=postgres_config)
        service._execute_query = AsyncMock(return_value=pd.DataFrame())

        # Request 150 rows, should be capped at 100
        result = await service.preview_table_data("test_postgres", "users", limit=150)

        assert result["limit"] == 100

    @pytest.mark.asyncio
    async def test_cache_hit(self, service, postgres_config):
        """Should return cached results on subsequent calls."""
        service.data_source_service.get_data_source = Mock(return_value=postgres_config)

        tables_data = pd.DataFrame(
            {
                "table_name": ["users"],
                "schema": ["public"],
                "comment": [None],
            }
        )

        service._execute_query = AsyncMock(return_value=tables_data)

        # First call
        tables1 = await service.get_tables("test_postgres")

        # Second call (should hit cache)
        tables2 = await service.get_tables("test_postgres")

        # Query should only be executed once
        service._execute_query.assert_called_once()
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
            schema="public",
            row_count=100,
            comment="User accounts",
        )

        assert table.name == "users"
        assert table.schema == "public"
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
        columns = [
            ColumnMetadata(
                name="id",
                data_type="integer",
                nullable=False,
                is_primary_key=True,
            ),
            ColumnMetadata(
                name="name",
                data_type="varchar",
                nullable=False,
                is_primary_key=False,
            ),
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
