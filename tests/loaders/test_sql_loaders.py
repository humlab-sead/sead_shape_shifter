"""
Tests for Database Loaders

Tests the vendor-specific database introspection methods in database loaders.
"""

from unittest.mock import AsyncMock, patch

import pandas as pd
import pytest

from src.config_model import DataSourceConfig
from src.loaders.sql_loaders import (
    CoreSchema,
    PostgresSqlLoader,
    SqliteLoader,
    UCanAccessSqlLoader,
)

# pylint: disable=redefined-outer-name, unused-argument, protected-access


class TestPostgresSqlLoader:
    """Tests for PostgreSQL loader introspection."""

    @pytest.fixture
    def postgres_config(self):
        """PostgreSQL data source config."""
        return DataSourceConfig(
            name="test_postgres",
            cfg={
                "driver": "postgres",
                "options": {
                    "host": "localhost",
                    "port": 5432,
                    "database": "testdb",
                    "username": "testuser",
                },
            },
        )

    @pytest.fixture
    def loader(self, postgres_config):
        """Create PostgresSqlLoader instance."""
        return PostgresSqlLoader(data_source=postgres_config)

    @pytest.mark.asyncio
    async def test_get_tables(self, loader):
        """Should get tables from PostgreSQL."""
        # Mock query result
        tables_data = pd.DataFrame(
            {
                "table_name": ["users", "orders"],
                "schema": ["public", "public"],
                "comment": [None, "Order records"],
            }
        )

        with patch.object(loader, "read_sql", new_callable=AsyncMock) as mock_read_sql:
            mock_read_sql.return_value = tables_data

            tables = await loader.get_tables(schema="public")

            assert len(tables) == 2
            assert "users" in tables
            assert "orders" in tables
            assert tables["users"].name == "users"
            assert tables["users"].schema == "public"
            assert tables["orders"].name == "orders"
            assert tables["orders"].comment == "Order records"

            # Verify SQL was called
            mock_read_sql.assert_called_once()
            call_args = mock_read_sql.call_args[0][0]
            assert "information_schema.tables" in call_args
            assert "public" in call_args

    @pytest.mark.asyncio
    async def test_get_table_schema(self, loader):
        """Should get table schema from PostgreSQL."""
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

        # Mock foreign keys query
        fk_data = pd.DataFrame(columns=["column_name", "foreign_table_name", "foreign_column_name"])

        # Mock row count query
        count_result = 42

        call_count = 0

        async def mock_read_sql(query):
            nonlocal call_count
            call_count += 1
            if "information_schema.columns" in query:
                return columns_data
            if "pg_index" in query and "indisprimary" in query:
                return pk_data
            if "pg_constraint" in query or "contype = 'f'" in query:
                return fk_data
            return pd.DataFrame()

        async def mock_get_row_count(table_name, schema):
            return count_result

        with patch.object(loader, "read_sql", side_effect=mock_read_sql):
            with patch.object(loader, "get_table_row_count", side_effect=mock_get_row_count):
                schema = await loader.get_table_schema("users", schema="public")

                assert schema.table_name == "users"
                assert len(schema.columns) == 3
                assert schema.columns[0].name == "id"
                assert schema.columns[0].is_primary_key is True
                assert schema.columns[1].name == "name"
                assert schema.columns[1].nullable is False
                assert schema.columns[2].name == "email"
                assert schema.columns[2].nullable is True
                assert schema.row_count == 42
                assert schema.primary_keys == ["id"]

    @pytest.mark.asyncio
    async def test_get_tables_with_default_schema(self, loader):
        """Should use 'public' schema by default."""
        tables_data = pd.DataFrame(
            {
                "table_name": ["users"],
                "schema": ["public"],
                "comment": [None],
            }
        )

        with patch.object(loader, "read_sql", new_callable=AsyncMock) as mock_read_sql:
            mock_read_sql.return_value = tables_data

            tables = await loader.get_tables()

            # Should default to 'public' schema
            call_args = mock_read_sql.call_args[0][0]
            assert "public" in call_args
            assert tables is not None


class TestSqliteLoader:
    """Tests for SQLite loader introspection."""

    @pytest.fixture
    def sqlite_config(self):
        """SQLite data source config."""
        return DataSourceConfig(
            name="test_sqlite",
            cfg={
                "driver": "sqlite",
                "options": {"filename": "test.db"},
            },
        )

    @pytest.fixture
    def loader(self, sqlite_config):
        """Create SqliteLoader instance."""
        return SqliteLoader(data_source=sqlite_config)

    @pytest.mark.asyncio
    async def test_get_tables(self, loader):
        """Should get tables from SQLite."""
        # Mock query result
        tables_data = pd.DataFrame(
            {
                "table_name": ["users", "posts"],
            }
        )

        with patch.object(loader, "read_sql", new_callable=AsyncMock) as mock_read_sql:
            mock_read_sql.return_value = tables_data

            tables = await loader.get_tables()

            assert len(tables) == 2
            assert "users" in tables
            assert "posts" in tables
            assert tables["users"].name == "users"
            assert tables["users"].schema is None  # SQLite doesn't have schemas
            assert tables["posts"].name == "posts"

            # Verify SQL was called
            mock_read_sql.assert_called_once()
            call_args = mock_read_sql.call_args[0][0]
            assert "sqlite_master" in call_args

    @pytest.mark.asyncio
    async def test_get_table_schema(self, loader):
        """Should get table schema from SQLite."""
        # Mock pragma table_info result
        pragma_data = pd.DataFrame(
            {
                "COLUMN_NAME": ["id", "username", "email"],
                "DATA_TYPE": ["INTEGER", "TEXT", "TEXT"],
                "IS_NULLABLE": ["NO", "NO", "YES"],
                "COLUMN_DEFAULT": [None, None, None],
                "CHARACTER_MAXIMUM_LENGTH": [None, 100, 100],
            }
        )
        count_result = 15

        with patch.object(loader, "read_sql", new_callable=AsyncMock) as mock_read_sql:
            mock_read_sql.return_value = pragma_data

            with patch.object(loader, "get_table_row_count", new_callable=AsyncMock) as mock_count:
                mock_count.return_value = count_result

                schema = await loader.get_table_schema("users")

                assert schema.table_name == "users"
                assert len(schema.columns) == 3
                assert schema.columns[0].name == "id"
                assert schema.columns[0].is_primary_key is True
                assert schema.columns[1].name == "username"
                assert schema.columns[1].nullable is False
                assert schema.columns[2].name == "email"
                assert schema.columns[2].nullable is True
                assert schema.row_count == 15

                # Verify pragma was called
                mock_read_sql.assert_called()
                call_args = mock_read_sql.call_args[0][0]
                assert "KEY_COLUMN_USAGE" in call_args
                assert "users" in call_args


class TestUCanAccessLoader:
    """Tests for MS Access loader introspection."""

    @pytest.fixture
    def access_config(self):
        """MS Access data source config."""
        return DataSourceConfig(
            name="test_access",
            cfg={
                "driver": "access",
                "options": {"filename": "test.mdb"},
            },
        )

    @pytest.fixture
    def loader(self, access_config):
        """Create UCanAccessSqlLoader instance."""
        return UCanAccessSqlLoader(data_source=access_config)

    @pytest.mark.asyncio
    async def test_get_tables(self, loader):
        """Should get tables from MS Access."""
        # Mock query result
        tables_data = pd.DataFrame(
            {
                "TABLE_NAME": ["Customers", "Products"],
            }
        )

        with patch.object(loader, "read_sql", new_callable=AsyncMock) as mock_read_sql:
            mock_read_sql.return_value = tables_data

            tables = await loader.get_tables()

            assert len(tables) == 2
            assert "Customers" in tables
            assert "Products" in tables
            assert tables["Customers"].name == "Customers"
            assert tables["Customers"].schema is None  # Access doesn't have schemas
            assert tables["Products"].name == "Products"

            # Verify SQL was called
            mock_read_sql.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_tables_fallback(self, loader):
        """Should try fallback query if first query fails."""
        tables_data = pd.DataFrame(
            {
                "TABLE_NAME": ["Customers"],
            }
        )

        call_count = 0

        async def mock_read_sql(query):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First query fails
                raise Exception("Query failed")  # pylint: disable=broad-exception-raised
            # Second query succeeds
            return tables_data

        with patch.object(loader, "read_sql", side_effect=mock_read_sql):
            tables = await loader.get_tables()

            assert len(tables) == 1
            assert "Customers" in tables
            assert call_count == 2  # Both queries were attempted

    @pytest.mark.asyncio
    async def test_get_table_schema(self, loader):
        """Should get table schema from MS Access."""
        # Mock columns query
        columns_data = pd.DataFrame(
            {
                "COLUMN_NAME": ["ID", "Name", "Email"],
                "DATA_TYPE": ["INTEGER", "VARCHAR", "VARCHAR"],
                "IS_NULLABLE": ["NO", "NO", "YES"],
                "COLUMN_DEFAULT": [None, None, None],
                "CHARACTER_MAXIMUM_LENGTH": [None, 50, 100],
            }
        )

        # Mock primary keys query
        pk_data = pd.DataFrame(
            {
                "COLUMN_NAME": ["ID"],
            }
        )

        count_result = 25

        call_count = 0

        async def mock_read_sql(query):
            nonlocal call_count
            call_count += 1
            if "INFORMATION_SCHEMA.COLUMNS" in query:
                return columns_data
            if "KEY_COLUMN_USAGE" in query:
                return pk_data
            return pd.DataFrame()

        with patch.object(loader, "read_sql", side_effect=mock_read_sql):
            with patch.object(loader, "get_table_row_count", new_callable=AsyncMock) as mock_count:
                mock_count.return_value = count_result

                schema = await loader.get_table_schema("Customers")

                assert schema.table_name == "Customers"
                assert len(schema.columns) == 3
                assert schema.columns[0].name == "ID"
                assert schema.columns[0].is_primary_key is True
                assert schema.columns[1].name == "Name"
                assert schema.columns[1].nullable is False
                assert schema.columns[2].name == "Email"
                assert schema.columns[2].nullable is True
                assert schema.row_count == 25

    @pytest.mark.asyncio
    async def test_get_table_schema_no_primary_keys(self, loader):
        """Should handle tables without primary keys."""
        columns_data = pd.DataFrame(
            {
                "COLUMN_NAME": ["Field1", "Field2"],
                "DATA_TYPE": ["VARCHAR", "INTEGER"],
                "IS_NULLABLE": ["YES", "YES"],
                "COLUMN_DEFAULT": [None, None],
                "CHARACTER_MAXIMUM_LENGTH": [50, None],
            }
        )

        call_count = 0

        async def mock_read_sql(query):
            nonlocal call_count
            call_count += 1
            if "INFORMATION_SCHEMA.COLUMNS" in query:
                return columns_data
            if "KEY_COLUMN_USAGE" in query:
                # Primary key query fails
                raise Exception("No primary key info")  # pylint: disable=broad-exception-raised
            return pd.DataFrame()

        with patch.object(loader, "read_sql", side_effect=mock_read_sql):
            with patch.object(loader, "get_table_row_count", new_callable=AsyncMock) as mock_count:
                mock_count.return_value = 0

                schema = await loader.get_table_schema("NoKeys")

                assert schema.table_name == "NoKeys"
                assert len(schema.columns) == 2
                # No primary keys
                assert all(not col.is_primary_key for col in schema.columns)
                assert schema.primary_keys == []


class TestCoreSchemaModels:
    """Tests for CoreSchema dataclasses."""

    def test_table_metadata_creation(self):
        """Should create TableMetadata."""
        table = CoreSchema.TableMetadata(
            name="users",
            schema="public",
            row_count=100,
            comment="User accounts",
        )

        assert table.name == "users"
        assert table.schema == "public"
        assert table.comment == "User accounts"

    def test_table_metadata_from_dataframe(self):
        """Should create TableMetadata dict from DataFrame."""
        df = pd.DataFrame(
            {
                "table_name": ["users", "orders"],
                "schema": ["public", "public"],
                "comment": ["User data", None],
            }
        )

        tables = CoreSchema.TableMetadata.from_dataframe(df)

        assert len(tables) == 2
        assert "users" in tables
        assert tables["users"].name == "users"
        assert tables["users"].comment == "User data"
        assert "orders" in tables
        assert tables["orders"].comment is None

    def test_column_metadata_creation(self):
        """Should create ColumnMetadata."""
        column = CoreSchema.ColumnMetadata(
            name="id",
            data_type="integer",
            nullable=False,
            default="nextval(...)",
            is_primary_key=True,
            max_length=None,
        )

        assert column.name == "id"
        assert column.data_type == "integer"
        assert column.nullable is False
        assert column.is_primary_key is True

    def test_table_schema_creation(self):
        """Should create TableSchema."""
        columns = [
            CoreSchema.ColumnMetadata(
                name="id",
                data_type="integer",
                nullable=False,
                default=None,
                is_primary_key=True,
                max_length=None,
            ),
            CoreSchema.ColumnMetadata(
                name="name",
                data_type="varchar",
                nullable=False,
                default=None,
                is_primary_key=False,
                max_length=None,
            ),
        ]

        schema = CoreSchema.TableSchema(
            table_name="users",
            columns=columns,
            primary_keys=["id"],
            row_count=42,
            foreign_keys=[],
            indexes=[],
        )

        assert schema.table_name == "users"
        assert len(schema.columns) == 2
        assert schema.primary_keys == ["id"]
        assert schema.row_count == 42

    def test_foreign_key_metadata_creation(self):
        """Should create ForeignKeyMetadata."""
        fk = CoreSchema.ForeignKeyMetadata(
            column="user_id",
            referenced_schema=None,
            referenced_table="users",
            referenced_column="id",
            constraint_name="fk_user_id",
        )

        assert fk.column == "user_id"
        assert fk.referenced_table == "users"
        assert fk.referenced_column == "id"


class TestSqlLoaderConnectionTest:
    """Tests for SQL loader test_connection method."""

    @pytest.mark.asyncio
    async def test_sqlite_connection_success(self):
        """Should successfully test SQLite connection."""
        config = DataSourceConfig(
            name="test_sqlite",
            cfg={
                "driver": "sqlite",
                "options": {
                    "database": ":memory:",
                },
            },
        )

        loader = SqliteLoader(data_source=config)

        # Mock get_tables to return some tables
        tables_data = {"users": CoreSchema.TableMetadata(name="users", schema=None, row_count=None, comment=None)}

        with patch.object(loader, "get_tables", new_callable=AsyncMock) as mock_get_tables:
            with patch.object(loader, "load", new_callable=AsyncMock) as mock_load:
                mock_get_tables.return_value = tables_data
                mock_load.return_value = pd.DataFrame({"count": [1]})

                result = await loader.test_connection()

                assert result.success
                assert "successful" in result.message.lower()
                assert result.connection_time_ms >= 0
                assert result.metadata["table_count"] == 1

                # Verify get_tables was called
                mock_get_tables.assert_called_once()

    @pytest.mark.asyncio
    async def test_postgres_connection_success(self):
        """Should successfully test PostgreSQL connection."""
        config = DataSourceConfig(
            name="test_postgres",
            cfg={
                "driver": "postgres",
                "options": {
                    "host": "localhost",
                    "port": 5432,
                    "database": "testdb",
                    "username": "testuser",
                },
            },
        )

        loader = PostgresSqlLoader(data_source=config)

        tables_data = {
            "users": CoreSchema.TableMetadata(name="users", schema="public", row_count=None, comment=None),
            "orders": CoreSchema.TableMetadata(name="orders", schema="public", row_count=None, comment=None),
        }

        with patch.object(loader, "get_tables", new_callable=AsyncMock) as mock_get_tables:
            with patch.object(loader, "load", new_callable=AsyncMock) as mock_load:
                mock_get_tables.return_value = tables_data
                mock_load.return_value = pd.DataFrame({"result": [1]})

                result = await loader.test_connection()

                assert result.success
                assert result.connection_time_ms >= 0
                assert result.metadata["table_count"] == 2

    @pytest.mark.asyncio
    async def test_ucanaccess_connection_success(self):
        """Should successfully test UCanAccess connection."""
        config = DataSourceConfig(
            name="test_access",
            cfg={
                "driver": "ucanaccess",
                "options": {
                    "database": "/path/to/database.accdb",
                },
            },
        )

        loader = UCanAccessSqlLoader(data_source=config)

        tables_data = {
            "Products": CoreSchema.TableMetadata(name="Products", schema=None, row_count=None, comment=None),
        }

        with patch.object(loader, "get_tables", new_callable=AsyncMock) as mock_get_tables:
            with patch.object(loader, "load", new_callable=AsyncMock) as mock_load:
                mock_get_tables.return_value = tables_data
                mock_load.return_value = pd.DataFrame({"test": [1]})

                result = await loader.test_connection()

                assert result.success
                assert result.metadata["table_count"] == 1

    @pytest.mark.asyncio
    async def test_sqlite_connection_failure_no_tables(self):
        """Should handle connection failure when no tables found."""
        config = DataSourceConfig(
            name="test_sqlite",
            cfg={
                "driver": "sqlite",
                "options": {
                    "database": ":memory:",
                },
            },
        )

        loader = SqliteLoader(data_source=config)

        with patch.object(loader, "get_tables", new_callable=AsyncMock) as mock_get_tables:
            mock_get_tables.return_value = {}  # No tables

            result = await loader.test_connection()

            # Should still succeed even with no tables
            assert result.success
            assert result.metadata["table_count"] == 0

    @pytest.mark.asyncio
    async def test_sqlite_connection_failure_exception(self):
        """Should handle connection exception gracefully."""
        config = DataSourceConfig(
            name="test_sqlite",
            cfg={
                "driver": "sqlite",
                "options": {
                    "database": "/invalid/path/database.db",
                },
            },
        )

        loader = SqliteLoader(data_source=config)

        with patch.object(loader, "get_tables", new_callable=AsyncMock) as mock_get_tables:
            mock_get_tables.side_effect = Exception("Connection failed")

            result = await loader.test_connection()

            assert not result.success
            assert "failed" in result.message.lower()
            assert result.connection_time_ms >= 0

    @pytest.mark.asyncio
    async def test_postgres_connection_failure_exception(self):
        """Should handle PostgreSQL connection exception."""
        config = DataSourceConfig(
            name="test_postgres",
            cfg={
                "driver": "postgres",
                "options": {
                    "host": "invalid-host",
                    "port": 5432,
                    "database": "testdb",
                    "username": "testuser",
                },
            },
        )

        loader = PostgresSqlLoader(data_source=config)

        with patch.object(loader, "get_tables", new_callable=AsyncMock) as mock_get_tables:
            mock_get_tables.side_effect = Exception("Could not connect to database")

            result = await loader.test_connection()

            assert not result.success
            assert "connect" in result.message.lower() or "failed" in result.message.lower()
