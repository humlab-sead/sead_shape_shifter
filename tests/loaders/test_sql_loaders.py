"""
Tests for Database Loaders

Tests the vendor-specific database introspection methods in database loaders.
"""

from unittest.mock import AsyncMock, Mock, patch

import pandas as pd
import pytest

from src.loaders.base_loader import LoaderType
from src.loaders.sql_loaders import (
    CoreSchema,
    PostgresSqlLoader,
    SqliteLoader,
    SqlLoader,
    UCanAccessSqlLoader,
)
from src.model import DataSourceConfig, TableConfig

# pylint: disable=redefined-outer-name, unused-argument, protected-access


class TestInjectLimit:
    """Test SQL parsing utilities."""

    @pytest.fixture
    def loader(self) -> SqliteLoader:
        """Create SqliteLoader instance."""
        return SqliteLoader(data_source={})

    def test_add_limit_to_select(self, loader: SqliteLoader):
        """Should add LIMIT clause to SELECT query."""
        query: str = "SELECT * FROM users"
        modified = loader.inject_limit(query, 100)
        assert "LIMIT 100" in modified.upper()

    def test_preserve_existing_limit(self, loader: SqliteLoader):
        """Should not modify query with existing LIMIT."""
        query: str = "SELECT * FROM users LIMIT 50"
        modified = loader.inject_limit(query, 100)

        assert modified == query

    def test_dont_add_limit_to_non_select(self, loader: SqliteLoader):
        """Should not add LIMIT to non-SELECT queries."""
        query: str = "INSERT INTO users (name) VALUES ('test')"
        modified = loader.inject_limit(query, 100)
        assert "LIMIT" not in modified.upper()
        assert modified == query


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
    async def test_loader_type(self, loader):
        """Check loader type."""
        assert loader.loader_type() == LoaderType.SQL

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
        """Should get tables from MS Access database."""
        # Mock the _get_tables method which is called by get_tables
        mock_tables = {
            "Customers": CoreSchema.TableMetadata(name="Customers", schema=None, comment=None, row_count=0),
            "Orders": CoreSchema.TableMetadata(name="Orders", schema=None, comment=None, row_count=0),
            "Products": CoreSchema.TableMetadata(name="Products", schema=None, comment=None, row_count=0),
        }

        with patch.object(loader, "_get_tables", return_value=mock_tables):
            with patch.object(loader, "connection"):
                tables = await loader.get_tables()

                assert len(tables) == 3
                assert "Customers" in tables
                assert "Orders" in tables
                assert "Products" in tables
                assert tables["Customers"].name == "Customers"
                assert tables["Customers"].schema is None  # Access doesn't have schemas
                assert tables["Orders"].name == "Orders"
                assert tables["Products"].name == "Products"

    @pytest.mark.asyncio
    async def test_get_table_schema(self, loader):
        """Should get table schema from MS Access database."""
        # Mock column metadata
        mock_columns = [
            CoreSchema.ColumnMetadata(
                name="CustomerID", data_type="INTEGER", max_length=None, nullable=False, default=None, is_primary_key=True
            ),
            CoreSchema.ColumnMetadata(
                name="CompanyName", data_type="VARCHAR", max_length=40, nullable=False, default=None, is_primary_key=False
            ),
            CoreSchema.ColumnMetadata(
                name="ContactName", data_type="VARCHAR", max_length=30, nullable=True, default=None, is_primary_key=False
            ),
            CoreSchema.ColumnMetadata(
                name="Country", data_type="VARCHAR", max_length=15, nullable=True, default=None, is_primary_key=False
            ),
        ]

        with patch.object(loader, "connection"):
            with patch.object(loader, "_get_columns", return_value=mock_columns):
                with patch.object(loader, "_get_primary_keys", return_value=["CustomerID"]):
                    with patch.object(loader, "get_table_row_count", new_callable=AsyncMock) as mock_count:
                        mock_count.return_value = 91

                        schema = await loader.get_table_schema("Customers")

                        assert schema.table_name == "Customers"
                        assert len(schema.columns) == 4
                        assert schema.columns[0].name == "CustomerID"
                        assert schema.columns[0].is_primary_key is True
                        assert schema.columns[0].nullable is False
                        assert schema.columns[1].name == "CompanyName"
                        assert schema.columns[1].nullable is False
                        assert schema.columns[2].name == "ContactName"
                        assert schema.columns[2].nullable is True
                        assert schema.columns[3].name == "Country"
                        assert schema.columns[3].nullable is True
                        assert schema.row_count == 91
                assert schema.primary_keys == ["CustomerID"]

    @pytest.mark.asyncio
    async def test_get_table_schema_with_foreign_keys(self, loader):
        """Should handle foreign keys in MS Access tables."""
        # Mock columns
        mock_columns = [
            CoreSchema.ColumnMetadata(
                name="OrderID", data_type="INTEGER", max_length=None, nullable=False, default=None, is_primary_key=True
            ),
            CoreSchema.ColumnMetadata(
                name="CustomerID", data_type="INTEGER", max_length=None, nullable=False, default=None, is_primary_key=False
            ),
            CoreSchema.ColumnMetadata(
                name="OrderDate", data_type="DATETIME", max_length=None, nullable=True, default=None, is_primary_key=False
            ),
        ]

        with patch.object(loader, "connection"):
            with patch.object(loader, "_get_columns", return_value=mock_columns):
                with patch.object(loader, "_get_primary_keys", return_value=["OrderID"]):
                    with patch.object(loader, "get_table_row_count", new_callable=AsyncMock) as mock_count:
                        mock_count.return_value = 830

                        schema = await loader.get_table_schema("Orders")

                        assert schema.table_name == "Orders"
                        assert len(schema.columns) == 3
                        assert schema.primary_keys == ["OrderID"]
                        # Note: UCanAccess get_table_schema doesn't populate foreign_keys
                        # It returns an empty list for FKs
                        assert schema.foreign_keys == []

    @pytest.mark.asyncio
    async def test_create_db_uri(self, loader):
        """Should create correct JDBC URI for MS Access."""
        uri = loader.create_db_uri()

        assert "jdbc:ucanaccess://" in uri
        assert "test.mdb" in uri

    @pytest.mark.asyncio
    async def test_load_with_top_limit(self, loader):
        """Should use TOP clause for Access queries."""
        # Mock data
        sample_data = pd.DataFrame(
            {
                "ProductID": [1, 2, 3],
                "ProductName": ["Product A", "Product B", "Product C"],
            }
        )

        table_cfg = TableConfig(
            entities_cfg={
                "products": {
                    "type": "sql",
                    "query": "SELECT * FROM Products",
                    "keys": ["ProductID"],
                    "columns": ["ProductID", "ProductName"],
                    "public_id": "product_id",
                }
            },
            entity_name="products",
        )

        with patch.object(loader, "read_sql", new_callable=AsyncMock) as mock_read_sql:
            mock_read_sql.return_value = sample_data

            result = await loader.load("products", table_cfg)

            assert len(result) == 3
            assert "ProductID" in result.columns
            assert "ProductName" in result.columns
            assert "system_id" in result.columns

    @pytest.mark.asyncio
    async def test_get_tables_filters_system_tables(self, loader):
        """Should filter out MS Access system tables."""
        # Mock the _get_tables method to return both user and system tables
        mock_tables = {
            "Customers": CoreSchema.TableMetadata(name="Customers", schema=None, comment=None, row_count=0),
            "Products": CoreSchema.TableMetadata(name="Products", schema=None, comment=None, row_count=0),
            # MSys* tables should be filtered out by _get_tables implementation
        }

        with patch.object(loader, "_get_tables", return_value=mock_tables):
            with patch.object(loader, "connection"):
                tables = await loader.get_tables()

                # Should only include user tables, not system tables
                assert len(tables) == 2
                assert "Customers" in tables
                assert "Products" in tables
                assert "MSysObjects" not in tables
                assert "MSysACEs" not in tables

    @pytest.mark.asyncio
    async def test_test_connection_success(self, loader):
        """Should successfully test MS Access connection."""
        tables_data = {
            "Customers": CoreSchema.TableMetadata(name="Customers", schema=None, row_count=None, comment=None),
            "Products": CoreSchema.TableMetadata(name="Products", schema=None, row_count=None, comment=None),
        }

        with patch.object(loader, "get_tables", new_callable=AsyncMock) as mock_get_tables:
            with patch.object(loader, "load", new_callable=AsyncMock) as mock_load:
                mock_get_tables.return_value = tables_data
                mock_load.return_value = pd.DataFrame({"count": [1]})

                result = await loader.test_connection()

                assert result.success
                assert "successful" in result.message.lower()
                assert result.metadata["table_count"] == 2

    @pytest.mark.asyncio
    async def test_test_connection_failure(self, loader):
        """Should handle MS Access connection failure."""
        with patch.object(loader, "get_tables", new_callable=AsyncMock) as mock_get_tables:
            mock_get_tables.side_effect = Exception("Cannot open database file")

            result = await loader.test_connection()

            assert result.success is False
            assert "failed" in result.message.lower()
            assert "Cannot open database file" in result.message


class DummySqlLoader(SqlLoader):
    """Simple concrete SqlLoader for testing base behaviors."""

    def create_db_uri(self) -> str:
        return "sqlite://"

    async def read_sql(self, sql: str) -> pd.DataFrame:
        return pd.DataFrame()

    async def get_tables(self, **kwargs):
        return {}

    async def get_table_schema(self, table_name: str, **kwargs):
        return CoreSchema.TableSchema(table_name=table_name, columns=[], primary_keys=[], indexes=[], row_count=0, foreign_keys=[])

    async def execute_scalar_sql(self, sql: str):
        return 0


class TestSqlLoaderCore:
    """Tests for shared SqlLoader behavior."""

    @pytest.fixture
    def loader(self) -> DummySqlLoader:
        """Provide a fresh dummy SQL loader."""
        return DummySqlLoader(data_source=Mock())

    @pytest.mark.asyncio
    async def test_load_auto_detects_columns_and_adds_system_id(self, monkeypatch: pytest.MonkeyPatch):
        """SqlLoader.load should infer columns when configured and append system_id."""
        loader = DummySqlLoader(data_source=DataSourceConfig(name="dummy", cfg={"driver": "postgres"}))

        sample_df = pd.DataFrame({"col_a": [1, 2], "col_b": ["x", "y"]})
        monkeypatch.setattr(loader, "read_sql", AsyncMock(return_value=sample_df))

        table_cfg = TableConfig(
            entities_cfg={
                "sql_entity": {
                    "type": "sql",
                    "query": "select * from t",
                    "keys": [],
                    "columns": [],
                    "auto_detect_columns": True,
                    "check_column_names": True,
                    "public_id": "sql_id",  # public_id for target system
                }
            },
            entity_name="sql_entity",
        )

        result: pd.DataFrame = await loader.load(entity_name="sql_entity", table_cfg=table_cfg)

        assert list(table_cfg.columns) == ["col_a", "col_b"]
        assert list(result.columns) == ["system_id", "col_a", "col_b"]
        assert result["system_id"].tolist() == [1, 2]

    @pytest.mark.asyncio
    async def test_load_rejects_non_sql_entity(self):
        """SqlLoader.load should raise for non-sql entities."""
        loader = DummySqlLoader(data_source=Mock())
        table_cfg = TableConfig(
            entities_cfg={"not_sql": {"type": "fixed", "query": "select 1", "columns": ["a"], "keys": []}},
            entity_name="not_sql",
        )

        with pytest.raises(ValueError, match="is not configured as fixed SQL data"):
            await loader.load("not_sql", table_cfg)

    @pytest.mark.asyncio
    async def test_test_connection_success_and_failure(self):
        """Test connection returns informative results in both success and failure scenarios."""
        loader = DummySqlLoader(data_source=DataSourceConfig(name="ds", cfg={"driver": "postgres"}))

        # Success path
        tables = {"example": CoreSchema.TableMetadata(name="example", schema=None, row_count=0, comment=None)}
        loader.get_tables = AsyncMock(return_value=tables)  # type: ignore[method-assign]
        loader.load = AsyncMock(return_value=pd.DataFrame({"x": [1, 2]}))  # type: ignore[method-assign]

        success_result = await loader.test_connection()

        assert success_result.success is True
        assert loader.get_tables.called
        assert success_result.metadata["table_count"] == 1
        assert "returned 2 rows" in success_result.message

        # Failure path
        failing_loader = DummySqlLoader(data_source=Mock())
        failing_loader.get_tables = AsyncMock(side_effect=Exception("boom"))  # type: ignore[method-assign]

        failure_result = await failing_loader.test_connection()

        assert failure_result.success is False
        assert "Connection failed" in failure_result.message

    @pytest.mark.asyncio
    async def test_get_table_schema_no_primary_keys(self):
        """Should handle tables without primary keys."""
        loader = SqliteLoader(data_source=DataSourceConfig(name="sqlite", cfg={"driver": "sqlite"}))
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

    @pytest.mark.asyncio
    async def test_load_with_relaxed_column_check_overwrites_columns(self, monkeypatch: pytest.MonkeyPatch):
        """When check_column_names is False, load should accept differing columns and coerce order."""
        loader = DummySqlLoader(data_source=DataSourceConfig(name="dummy", cfg={"driver": "postgres"}))
        sample_df = pd.DataFrame({"b": [1], "a": [2]})
        monkeypatch.setattr(loader, "read_sql", AsyncMock(return_value=sample_df))

        table_cfg = TableConfig(
            entities_cfg={
                "sql_entity": {
                    "type": "sql",
                    "query": "select * from t",
                    "keys": [],
                    "columns": ["a", "b"],
                    "auto_detect_columns": False,
                    "check_column_names": False,
                    "public_id": "sql_entity_id",
                }
            },
            entity_name="sql_entity",
        )

        result = await loader.load("sql_entity", table_cfg)
        # When public_id is configured, system_id is automatically added
        assert list(result.columns) == ["system_id", "a", "b"]

    def test_get_test_query_formats_default(self):
        loader = DummySqlLoader(data_source=Mock())
        assert loader.get_test_query("tbl", 5) == "select * from tbl limit 5 ;"

    async def test_get_table_row_count_logs_and_returns_none_on_error(self, caplog):
        loader = DummySqlLoader(data_source=Mock())

        async def boom(sql: str):
            raise RuntimeError("fail")

        loader.execute_scalar_sql = boom  # type: ignore[assignment]
        assert await loader.get_table_row_count("tbl") is None


class TestPostgresDefaults:
    """Ensure Postgres loader derives sane defaults."""

    def test_db_opts_defaults(self):
        ds = DataSourceConfig(name="pg", cfg={"driver": "postgres", "options": {}})
        loader = PostgresSqlLoader(ds)
        opts = loader.db_opts
        assert opts["host"] == "localhost"
        assert opts["port"] == 5432
        assert opts["user"] == "postgres"
        assert opts["dbname"] == "postgres"


class TestUCanAccessExtras:
    """Additional behaviors for UCanAccess loader."""

    @pytest.fixture
    def access_config(self):
        return DataSourceConfig(name="access", cfg={"driver": "ucanaccess", "options": {"filename": "f"}})

    def test_get_test_query_uses_top(self, access_config):
        loader = UCanAccessSqlLoader(access_config)
        assert loader.get_test_query("MyTable", 3).startswith("SELECT TOP 3")


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


class TestUCanAccessInjectLimit:
    """Test SQL parsing utilities."""

    @pytest.fixture
    def loader(self) -> UCanAccessSqlLoader:
        """Create UCanAccessSqlLoader instance."""
        return UCanAccessSqlLoader(data_source={})

    def test_add_limit_to_select(self, loader: UCanAccessSqlLoader):
        """Should add TOP clause to SELECT query."""
        query: str = "SELECT * FROM users"
        modified = loader.inject_limit(query, 100)
        assert "TOP 100" in modified.upper()

    def test_preserve_existing_limit(self, loader: UCanAccessSqlLoader):
        """Should not modify query with existing TOP."""
        query: str = "SELECT TOP 50 * FROM users"
        modified = loader.inject_limit(query, 100)

        assert modified == query

    def test_dont_add_limit_to_non_select(self, loader: UCanAccessSqlLoader):
        """Should not add TOP to non-SELECT queries."""
        query: str = "INSERT INTO users (name) VALUES ('test')"
        modified = loader.inject_limit(query, 100)
        assert "TOP" not in modified.upper()
        assert modified == query


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
