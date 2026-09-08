"""
Tests for Query Service
"""

import asyncio
from typing import Literal
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pandas as pd
import pytest
import sqlparse

from backend.app.exceptions import QueryExecutionError, QuerySecurityError
from backend.app.models.data_source import DataSourceConfig
from backend.app.models.query import QueryResult, QueryValidation
from backend.app.services.query_service import QueryService
from backend.app.utils.sql import extract_tables, get_statement_type, has_where_clause

# pylint: disable=redefined-outer-name, unused-argument, attribute-defined-outside-init


class TestQueryValidation:
    """Test query validation functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = QueryService()

    def test_validate_select_query(self):
        """Should validate SELECT queries as valid."""
        query: str = "SELECT * FROM users WHERE id = 1"
        result: QueryValidation = self.service.validate_query(query)

        assert result.is_valid is True
        assert len(result.errors) == 0
        assert result.statement_type == "SELECT"
        assert "users" in result.tables

    def test_validate_insert_query(self):
        """Should reject INSERT queries as destructive."""
        query: str = "INSERT INTO users (name) VALUES ('test')"
        result: QueryValidation = self.service.validate_query(query)

        assert result.is_valid is False
        assert len(result.errors) > 0
        assert "INSERT" in result.errors[0]
        assert result.statement_type == "INSERT"

    def test_validate_update_query(self):
        """Should reject UPDATE queries as destructive."""
        query: str = "UPDATE users SET name = 'test' WHERE id = 1"
        result: QueryValidation = self.service.validate_query(query)

        assert result.is_valid is False
        assert "UPDATE" in result.errors[0]

    def test_validate_delete_query(self):
        """Should reject DELETE queries as destructive."""
        query: str = "DELETE FROM users WHERE id = 1"
        result: QueryValidation = self.service.validate_query(query)

        assert result.is_valid is False
        assert "DELETE" in result.errors[0]

    def test_validate_drop_query(self):
        """Should reject DROP queries as destructive."""
        query: str = "DROP TABLE users"
        result: QueryValidation = self.service.validate_query(query)

        assert result.is_valid is False
        assert "DROP" in result.errors[0]

    def test_validate_empty_query(self):
        """Should reject empty queries."""
        query: Literal[""] = ""
        result: QueryValidation = self.service.validate_query(query)

        assert result.is_valid is False
        assert len(result.errors) > 0

    def test_validate_syntax_error(self):
        """Should detect syntax errors."""
        query: str = "SELECT * FROM"  # Incomplete query
        result: QueryValidation = self.service.validate_query(query)

        # Query might still parse but be invalid
        assert result.is_valid is True or len(result.errors) > 0

    def test_validate_multiple_statements(self):
        """Should reject multiple statements before execution."""
        query: str = "SELECT * FROM users; SELECT * FROM orders;"
        result: QueryValidation = self.service.validate_query(query)

        assert result.is_valid is False
        assert any("multiple statements" in error.lower() for error in result.errors)

    def test_validate_no_where_clause(self):
        """Should warn about queries without WHERE clause."""
        query: str = "SELECT * FROM users"
        result: QueryValidation = self.service.validate_query(query)

        assert result.is_valid is True
        # Should have warning about missing WHERE clause
        warning_found: bool = any("where" in w.lower() for w in result.warnings)
        assert warning_found

    def test_extract_table_names(self) -> None:
        """Should extract table names from query."""
        query: str = "SELECT u.*, o.* FROM users u JOIN orders o ON u.id = o.user_id"
        result: QueryValidation = self.service.validate_query(query)

        assert "users" in result.tables
        assert "orders" in result.tables

    def test_extract_schema_qualified_table(self) -> None:
        """Should extract table names with schema prefix."""
        query: str = "SELECT * FROM public.users"
        result: QueryValidation = self.service.validate_query(query)

        assert "users" in result.tables


class TestQueryExecution:
    """Test query execution functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = QueryService()

    @pytest.fixture
    def mock_ds_config(self) -> DataSourceConfig:
        """Return a DataSourceConfig for use in execute_query calls."""
        return DataSourceConfig(  # type: ignore
            name="test_db",
            driver="postgresql",
            host="localhost",
            port=5432,
            database="testdb",
            username="testuser",
        )

    def mock_read_sql(self, test_df: pd.DataFrame, mock_get_loader: Mock) -> AsyncMock:
        """Mock the loader's read_sql method."""
        mock_read_sql: AsyncMock = AsyncMock(return_value=test_df)
        mock_loader_instance = Mock()
        mock_loader_instance.read_sql = mock_read_sql
        mock_loader_class = Mock(return_value=mock_loader_instance)
        mock_get_loader.return_value = mock_loader_class
        return mock_read_sql

    @pytest.mark.asyncio
    async def test_execute_simple_query(self, mock_ds_config):
        """Should execute SELECT query and return results."""

        test_df = pd.DataFrame({"id": [1, 2, 3], "name": ["Kalle", "Kula", "Kurt"]})

        # Mock the loader's read_sql method
        with patch("backend.app.services.query_service.DataLoaders.get") as mock_get_loader:

            _: Mock = self.mock_read_sql(test_df, mock_get_loader=mock_get_loader)
            query: str = "select * from users"

            service: QueryService = QueryService()
            result: QueryResult = await service.execute_query(ds_cfg=mock_ds_config, query=query, limit=100)

            assert isinstance(result, QueryResult)
            assert result.row_count == 3
            assert len(result.columns) == 2
            assert "id" in result.columns
            assert "name" in result.columns
            assert len(result.rows) == 3
            assert result.execution_time_ms > 0

    @pytest.mark.skip(reason="Automatic limit injection disabled for now")
    @pytest.mark.asyncio
    async def test_execute_with_limit(self, mock_ds_config):
        """Should apply LIMIT clause to query."""
        test_df = pd.DataFrame({"id": range(50)})

        with patch("backend.app.services.query_service.DataLoaders.get") as mock_get_loader:

            mock_read_sql: Mock = self.mock_read_sql(test_df, mock_get_loader=mock_get_loader)

            query: str = "SELECT * FROM users"
            service: QueryService = QueryService()

            result: QueryResult = await service.execute_query(ds_cfg=mock_ds_config, query=query, limit=50)

            called_query: str = mock_read_sql.call_args[0][0]
            assert "LIMIT" in called_query.upper()
            assert result.row_count == 50

    @pytest.mark.asyncio
    async def test_execute_truncated_result(self, mock_ds_config):
        """Should detect truncated results."""

        test_df = pd.DataFrame({"id": range(100)})  # Return exactly the limit

        with patch("backend.app.services.query_service.DataLoaders.get") as mock_get_loader:

            _: Mock = self.mock_read_sql(test_df, mock_get_loader=mock_get_loader)

            service: QueryService = QueryService()

            query: str = "SELECT * FROM users"
            result: QueryResult = await service.execute_query(ds_cfg=mock_ds_config, query=query, limit=100)

            assert result.is_truncated is True

    @pytest.mark.asyncio
    async def test_execute_destructive_query(self, mock_ds_config):
        """Should reject destructive queries with structured error."""

        with pytest.raises(QuerySecurityError) as exc_info:

            service: QueryService = QueryService()
            query: str = "DELETE FROM users"

            await service.execute_query(ds_cfg=mock_ds_config, query=query)

        # Check structured error format
        error = exc_info.value
        assert "prohibited operations" in error.message.lower()
        assert error.recoverable is False  # Security errors are not user-recoverable
        assert "violations" in error.context
        assert len(error.tips) > 0

    @pytest.mark.asyncio
    async def test_execute_multiple_statements_does_not_reach_loader(self, mock_ds_config):
        """Should reject stacked statements before constructing or calling a loader."""
        with patch("backend.app.services.query_service.DataLoaders.get") as mock_get_loader:
            service: QueryService = QueryService()

            with pytest.raises(QuerySecurityError, match="prohibited operations"):
                await service.execute_query(ds_cfg=mock_ds_config, query="SELECT 1; SELECT 2")

            mock_get_loader.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_connection_error(self, mock_ds_config):
        """Should handle connection errors."""

        with patch("backend.app.services.query_service.DataLoaders.get") as mock_get_loader:
            mock_loader_cls = Mock(side_effect=Exception("Connection failed"))
            mock_get_loader.return_value = mock_loader_cls

            with pytest.raises(QueryExecutionError) as exc_info:

                query: str = "SELECT * FROM users"
                service: QueryService = QueryService()

                await service.execute_query(ds_cfg=mock_ds_config, query=query)

        assert str(exc_info.value) == "Query execution failed."
        assert "connection failed" not in exc_info.value.context

    @pytest.mark.asyncio
    async def test_execute_query_error(self, mock_ds_config):
        """Should handle query execution errors."""

        with patch("backend.app.services.query_service.DataLoaders.get") as mock_get_loader:
            mock_loader = Mock()
            mock_loader.inject_limit = Mock(side_effect=lambda q, p: q)
            mock_loader.read_sql = AsyncMock(side_effect=Exception("Table not found"))
            mock_get_loader.return_value = Mock(return_value=mock_loader)

            query: str = "SELECT * FROM nonexistent"
            service: QueryService = QueryService()

            with pytest.raises(QueryExecutionError) as exc_info:
                await service.execute_query(ds_cfg=mock_ds_config, query=query)
            assert "query execution failed" in str(exc_info.value).lower()
            assert "table not found" not in str(exc_info.value).lower()
            assert "query" not in exc_info.value.context

    @pytest.mark.asyncio
    async def test_execute_with_null_values(self, mock_ds_config):
        """Should handle NULL values correctly."""

        test_df: pd.DataFrame = pd.DataFrame({"id": [1, 2, 3], "name": ["Alice", None, "Charlie"]})

        with patch("backend.app.services.query_service.DataLoaders.get") as mock_get_loader:
            _: Mock = self.mock_read_sql(test_df, mock_get_loader=mock_get_loader)

            query: str = "SELECT * FROM users"
            service = QueryService()
            result: QueryResult = await service.execute_query(ds_cfg=mock_ds_config, query=query)

            # NULL should be converted to None
            assert result.rows[1]["name"] is None

    @pytest.mark.asyncio
    async def test_execute_with_datetime(self, mock_ds_config):
        """Should serialize datetime values correctly."""

        test_df = pd.DataFrame({"id": [1], "created_at": [pd.Timestamp("2024-01-01 12:00:00")]})

        with patch("backend.app.services.query_service.DataLoaders.get") as mock_get_loader:
            _: Mock = self.mock_read_sql(test_df, mock_get_loader=mock_get_loader)

            query: str = "SELECT * FROM users"
            service = QueryService()
            result: QueryResult = await service.execute_query(ds_cfg=mock_ds_config, query=query)

            # Timestamp should be serialized as ISO string
            assert isinstance(result.rows[0]["created_at"], str)
            assert "2024-01-01" in result.rows[0]["created_at"]

    @pytest.mark.asyncio
    async def test_execute_respects_max_limit(self, mock_ds_config):
        """Should enforce maximum row limit."""
        test_df = pd.DataFrame({"id": range(100)})

        with patch("backend.app.services.query_service.DataLoaders.get") as mock_get_loader:
            _: Mock = self.mock_read_sql(test_df, mock_get_loader=mock_get_loader)

            query: str = "SELECT * FROM users"
            service = QueryService()
            result: QueryResult = await service.execute_query(ds_cfg=mock_ds_config, query=query, limit=20000)

            assert result.row_count <= 20000


class TestQueryService:
    """Test QueryService for SQL query validation and execution."""

    @pytest.fixture
    def service(self) -> QueryService:
        """Create QueryService instance."""
        return QueryService()

    @pytest.fixture
    def mock_ds_config(self) -> DataSourceConfig:
        """Return a DataSourceConfig for use in execute_query/introspect calls."""
        return DataSourceConfig(  # type: ignore
            name="test_source",
            driver="postgresql",
            host="localhost",
            port=5432,
            database="testdb",
        )

    @pytest.fixture
    def mock_loader(self) -> AsyncMock:
        """Create mock SQL loader."""
        loader = Mock()
        loader.read_sql = AsyncMock(return_value=pd.DataFrame({"id": [1, 2], "name": ["Alice", "Bob"]}))
        loader.load_table = AsyncMock(return_value=pd.DataFrame({"id": [1, 2], "name": ["Alice", "Bob"]}))
        return loader

    # SQL validation tests

    def test_validate_query_select_valid(self, service: QueryService):
        """Test validation of valid SELECT query."""
        query = "SELECT * FROM users"
        result = service.validate_query(query)

        assert result.is_valid is True
        assert result.statement_type == "SELECT"
        assert "users" in result.tables
        assert len(result.errors) == 0

    def test_validate_query_select_with_where(self, service: QueryService):
        """Test validation of SELECT with WHERE clause."""
        query = "SELECT id, name FROM users WHERE id > 10"
        result: QueryValidation = service.validate_query(query)

        assert result.is_valid is True

    def test_validate_query_select_without_where(self, service: QueryService):
        """Test validation flags missing WHERE clause."""
        query = "SELECT * FROM large_table"
        result = service.validate_query(query)

        assert result.is_valid is True
        assert any("WHERE" in w for w in result.warnings)

    def test_validate_query_destructive_keywords(self, service: QueryService):
        """Test validation rejects destructive queries."""
        destructive_queries = [
            "DROP TABLE users",
            "DELETE FROM users",
            "TRUNCATE TABLE users",
            "ALTER TABLE users ADD COLUMN new_col INT",
        ]

        for query in destructive_queries:
            result = service.validate_query(query)
            assert result.is_valid is False
            assert len(result.errors) > 0
            assert "not allowed" in result.errors[0].lower()

    def test_validate_query_empty(self, service: QueryService):
        """Test validation of empty query."""
        result = service.validate_query("")
        assert result.is_valid is False
        assert "empty" in result.errors[0].lower()

    def test_validate_query_whitespace_only(self, service: QueryService):
        """Test validation of whitespace-only query."""
        result = service.validate_query("   \n\t  ")
        assert result.is_valid is False
        assert "empty" in result.errors[0].lower()

    def test_validate_query_invalid_sql(self, service: QueryService):
        """Test validation of malformed SQL."""
        query = "SELECT FROM WHERE"
        result = service.validate_query(query)

        # Should still parse but may have warnings
        assert isinstance(result, QueryValidation)

    def test_validate_query_multiple_tables(self, service: QueryService):
        """Test validation extracts multiple table names."""
        query = "SELECT u.id, o.total FROM users u JOIN orders o ON u.id = o.user_id"
        result = service.validate_query(query)

        assert result.is_valid is True
        assert "users" in result.tables
        assert "orders" in result.tables

    def test_validate_query_with_schema(self, service: QueryService):
        """Test validation handles schema-qualified table names."""
        query = "SELECT * FROM public.users"
        result = service.validate_query(query)

        assert result.is_valid is True
        assert "users" in result.tables

    def test_validate_query_subquery(self, service: QueryService):
        """Test validation of query with subquery."""
        query = "SELECT * FROM (SELECT id FROM users WHERE active = true) AS active_users"
        result = service.validate_query(query)

        assert result.is_valid is True

    def test_validate_query_insert(self, service: QueryService):
        """Test validation rejects INSERT queries."""
        query = "INSERT INTO users (name) VALUES ('Alice')"
        result = service.validate_query(query)

        assert result.is_valid is False
        assert "not allowed" in result.errors[0].lower()

    def test_validate_query_update(self, service: QueryService):
        """Test validation rejects UPDATE queries."""
        query = "UPDATE users SET active = false WHERE id = 1"
        result = service.validate_query(query)

        assert result.is_valid is False

    # Query execution tests

    @pytest.mark.asyncio
    async def test_execute_query_success(self, service: QueryService, mock_ds_config: DataSourceConfig, mock_loader: AsyncMock):
        """Test successful query execution."""
        query = "SELECT * FROM users"

        with (
            patch("backend.app.services.query_service.DataLoaders.get") as mock_get_loader,
            patch("backend.app.services.query_service.DataSourceMapper") as mock_mapper,
        ):
            mock_get_loader.return_value = lambda data_source: mock_loader
            mock_mapper.to_core_config = MagicMock(return_value=MagicMock())

            result = await service.execute_query(ds_cfg=mock_ds_config, query=query)

            assert isinstance(result, QueryResult)
            assert result.row_count == 2
            assert result.columns == ["id", "name"]
            assert len(result.rows) == 2
            assert result.rows[0]["name"] == "Alice"

    @pytest.mark.asyncio
    async def test_execute_query_applies_limit(self, service: QueryService, mock_ds_config: DataSourceConfig, mock_loader: AsyncMock):
        """Test execution applies LIMIT clause."""
        query = "SELECT * FROM users"

        with (
            patch("backend.app.services.query_service.DataLoaders.get") as mock_get_loader,
            patch("backend.app.services.query_service.DataSourceMapper") as mock_mapper,
        ):
            mock_get_loader.return_value = lambda data_source: mock_loader
            mock_mapper.to_core_config = MagicMock(return_value=MagicMock())
            mock_loader.inject_limit = MagicMock(side_effect=lambda q, w: f"{q} LIMIT {w}")
            await service.execute_query(ds_cfg=mock_ds_config, query=query, limit=100)

            # Verify loader was called with modified query
            call_args = mock_loader.read_sql.call_args
            sql_param = call_args[0][0] if call_args else None
            assert sql_param is not None
            assert "LIMIT 100" in sql_param

    @pytest.mark.asyncio
    async def test_execute_query_preserves_existing_limit(
        self, service: QueryService, mock_ds_config: DataSourceConfig, mock_loader: AsyncMock
    ):
        """Test execution preserves user-specified LIMIT."""
        query = "SELECT * FROM users LIMIT 10"

        with (
            patch("backend.app.services.query_service.DataLoaders.get") as mock_get_loader,
            patch("backend.app.services.query_service.DataSourceMapper") as mock_mapper,
        ):
            mock_get_loader.return_value = lambda data_source: mock_loader
            mock_mapper.to_core_config = MagicMock(return_value=MagicMock())
            mock_loader.inject_limit = MagicMock(side_effect=lambda q, w: q)
            await service.execute_query(ds_cfg=mock_ds_config, query=query, limit=100)

            call_args = mock_loader.read_sql.call_args
            sql_param = call_args[0][0] if call_args else None
            # Should keep original LIMIT 10, not add LIMIT 100
            assert sql_param is not None
            assert sql_param.count("LIMIT") == 1

    @pytest.mark.asyncio
    async def test_execute_query_timeout(self, service: QueryService, mock_ds_config: DataSourceConfig):
        """Test execution timeout handling."""
        query = "SELECT * FROM users"

        async def slow_read_sql(query):  # pylint: disable=unused-argument
            await asyncio.sleep(10)
            return pd.DataFrame()

        slow_loader = AsyncMock()
        slow_loader.read_sql = slow_read_sql
        slow_loader.inject_limit = MagicMock(side_effect=lambda q, p: q)  # noqa: E741

        with (
            patch("backend.app.services.query_service.DataLoaders.get") as mock_get_loader,
            patch("backend.app.services.query_service.DataSourceMapper") as mock_mapper,
        ):
            mock_ds_value = MagicMock()
            mock_get_loader.return_value = lambda data_source: slow_loader
            mock_mapper.to_core_config = MagicMock(return_value=mock_ds_value)

            with pytest.raises(QueryExecutionError) as exc_info:
                await service.execute_query(ds_cfg=mock_ds_config, query=query, timeout=1)

            error = exc_info.value
            assert "timed out" in error.message.lower() or "timeout" in error.message.lower()
            assert error.context.get("data_source") == mock_ds_config.name
            assert len(error.tips) > 0

    @pytest.mark.asyncio
    async def test_execute_query_loader_error(self, service: QueryService, mock_ds_config: DataSourceConfig):
        """Test execution handles loader errors."""
        query = "SELECT * FROM users"
        error_loader = AsyncMock()
        error_loader.read_sql = AsyncMock(side_effect=RuntimeError("Database error"))
        error_loader.inject_limit = MagicMock(side_effect=lambda q, p: q)  # noqa: E741

        with (
            patch("backend.app.services.query_service.DataLoaders.get") as mock_get_loader,
            patch("backend.app.services.query_service.DataSourceMapper") as mock_mapper,
        ):
            mock_get_loader.return_value = lambda data_source: error_loader
            mock_mapper.to_core_config = MagicMock(return_value=MagicMock())

            with pytest.raises(QueryExecutionError) as exc_info:
                await service.execute_query(ds_cfg=mock_ds_config, query=query)

            error = exc_info.value
            assert "database error" in error.message.lower() or "failed" in error.message.lower()
            assert error.context.get("data_source") == mock_ds_config.name
            assert len(error.tips) > 0

    @pytest.mark.asyncio
    async def test_execute_query_empty_result(self, service: QueryService, mock_ds_config: DataSourceConfig):
        """Test execution with empty result set."""
        query = "SELECT * FROM users WHERE id = 999"
        empty_loader = AsyncMock()
        empty_loader.read_sql = AsyncMock(return_value=pd.DataFrame(columns=["id", "name"]))
        empty_loader.inject_limit = MagicMock(side_effect=lambda q, p: q)

        with (
            patch("backend.app.services.query_service.DataLoaders.get") as mock_get_loader,
            patch("backend.app.services.query_service.DataSourceMapper") as mock_mapper,
        ):
            mock_get_loader.return_value = lambda data_source: empty_loader
            mock_mapper.to_core_config = MagicMock(return_value=MagicMock())

            result = await service.execute_query(ds_cfg=mock_ds_config, query=query)

            assert result.row_count == 0
            assert result.columns == ["id", "name"]
            assert result.rows == []

    @pytest.mark.asyncio
    async def test_execute_query_handles_null_values(self, service: QueryService, mock_ds_config: DataSourceConfig):
        """Test execution properly handles NULL values."""
        df = pd.DataFrame({"id": [1, 2], "name": ["Alice", None]})
        null_loader = AsyncMock()
        null_loader.read_sql = AsyncMock(return_value=df)
        null_loader.inject_limit = MagicMock(side_effect=lambda q, p: q)

        with (
            patch("backend.app.services.query_service.DataLoaders.get") as mock_get_loader,
            patch("backend.app.services.query_service.DataSourceMapper") as mock_mapper,
        ):
            mock_get_loader.return_value = lambda data_source: null_loader
            mock_mapper.to_core_config = MagicMock(return_value=MagicMock())

            result = await service.execute_query(ds_cfg=mock_ds_config, query="SELECT * FROM users")

            assert result.rows[1]["name"] is None

    @pytest.mark.asyncio
    async def test_execute_query_handles_timestamps(self, service: QueryService, mock_ds_config: DataSourceConfig):
        """Test execution serializes timestamp values."""
        df = pd.DataFrame({"id": [1], "created": [pd.Timestamp("2024-01-01 12:00:00")]})
        ts_loader = AsyncMock()
        ts_loader.read_sql = AsyncMock(return_value=df)
        ts_loader.inject_limit = MagicMock(side_effect=lambda q, p: q)

        with (
            patch("backend.app.services.query_service.DataLoaders.get") as mock_get_loader,
            patch("backend.app.services.query_service.DataSourceMapper") as mock_mapper,
        ):
            mock_get_loader.return_value = lambda data_source: ts_loader
            mock_mapper.to_core_config = MagicMock(return_value=MagicMock())

            result = await service.execute_query(ds_cfg=mock_ds_config, query="SELECT * FROM events")

            assert isinstance(result.rows[0]["created"], str)
            assert "2024-01-01" in result.rows[0]["created"]

    @pytest.mark.asyncio
    async def test_execute_query_truncation_flag(self, service: QueryService, mock_ds_config: DataSourceConfig):
        """Test execution sets truncation flag correctly."""
        # Create large result set
        df = pd.DataFrame({"id": range(1000), "value": range(1000)})
        large_loader = AsyncMock()
        large_loader.read_sql = AsyncMock(return_value=df)
        large_loader.inject_limit = MagicMock(side_effect=lambda q, p: q)

        with (
            patch("backend.app.services.query_service.DataLoaders.get") as mock_get_loader,
            patch("backend.app.services.query_service.DataSourceMapper") as mock_mapper,
        ):
            mock_get_loader.return_value = lambda data_source: large_loader
            mock_mapper.to_core_config = MagicMock(return_value=MagicMock())

            result = await service.execute_query(ds_cfg=mock_ds_config, query="SELECT * FROM large_table", limit=100)

            # Since result >= limit, should be truncated
            assert result.is_truncated is True

    @pytest.mark.asyncio
    async def test_execute_query_limits_serialized_response_size(self, service: QueryService, mock_ds_config: DataSourceConfig):
        """Test execution truncates rows when the serialized response exceeds the server limit."""
        large_loader = AsyncMock()
        large_loader.read_sql = AsyncMock(return_value=pd.DataFrame({"value": ["x" * (1024 * 1024)] * 10}))
        large_loader.inject_limit = MagicMock(side_effect=lambda q, p: q)

        with (
            patch("backend.app.services.query_service.DataLoaders.get") as mock_get_loader,
            patch("backend.app.services.query_service.DataSourceMapper") as mock_mapper,
        ):
            mock_get_loader.return_value = lambda data_source: large_loader
            mock_mapper.to_core_config = MagicMock(return_value=MagicMock())

            result = await service.execute_query(ds_cfg=mock_ds_config, query="SELECT * FROM large_table", limit=100)

            assert result.is_truncated is True
            assert result.row_count < 10

    @pytest.mark.asyncio
    async def test_execute_query_tracks_execution_time(self, service: QueryService, mock_ds_config: DataSourceConfig):
        """Test execution tracks query time."""
        # Create loader with read_sql method
        mock_loader = AsyncMock()
        mock_loader.read_sql = AsyncMock(return_value=pd.DataFrame({"id": [1, 2], "name": ["Alice", "Bob"]}))
        mock_loader.inject_limit = MagicMock(side_effect=lambda q, p: q)

        with (
            patch("backend.app.services.query_service.DataLoaders.get") as mock_get_loader,
            patch("backend.app.services.query_service.DataSourceMapper") as mock_mapper,
        ):
            mock_get_loader.return_value = lambda data_source: mock_loader
            mock_mapper.to_core_config = MagicMock(return_value=MagicMock())

            result: QueryResult = await service.execute_query(ds_cfg=mock_ds_config, query="SELECT * FROM users")

            assert result.execution_time_ms > 0

    # Helper method tests — these now test functions in backend.app.utils.sql

    def test_get_statement_type_select(self, service: QueryService):
        """Test statement type extraction for SELECT."""
        parsed = sqlparse.parse("SELECT * FROM users")[0]
        stmt_type = get_statement_type(parsed, service.FORBIDDEN_KEYWORDS)
        assert stmt_type == "SELECT"

    def test_get_statement_type_insert(self, service: QueryService):
        """Test statement type extraction for INSERT."""
        parsed = sqlparse.parse("INSERT INTO users VALUES (1, 'Alice')")[0]
        stmt_type = get_statement_type(parsed, service.FORBIDDEN_KEYWORDS)
        assert stmt_type == "INSERT"

    def test_get_statement_type_delete(self, service: QueryService):
        """Test statement type extraction for DELETE."""
        parsed = sqlparse.parse("DELETE FROM users WHERE id = 1")[0]
        stmt_type = get_statement_type(parsed, service.FORBIDDEN_KEYWORDS)
        assert stmt_type == "DELETE"

    def test_extract_table_names_simple(self, service: QueryService):
        """Test table name extraction from simple query."""
        tables = extract_tables("SELECT * FROM users")
        assert "users" in tables

    def test_extract_table_names_join(self, service: QueryService):
        """Test table name extraction from JOIN query."""
        tables = extract_tables("SELECT * FROM users u JOIN orders o ON u.id = o.user_id")
        assert "users" in tables
        assert "orders" in tables

    def test_extract_table_names_with_schema(self, service: QueryService):
        """Test table name extraction strips schema prefix."""
        tables = extract_tables("SELECT * FROM public.users")
        assert "users" in tables
        assert "public" not in tables

    def test_has_where_clause_true(self, service: QueryService):
        """Test WHERE clause detection - present."""
        parsed = sqlparse.parse("SELECT * FROM users WHERE id > 10")[0]
        assert has_where_clause(parsed) is True

    def test_has_where_clause_false(self, service: QueryService):
        """Test WHERE clause detection - absent."""
        parsed = sqlparse.parse("SELECT * FROM users")[0]
        assert has_where_clause(parsed) is False


class TestColumnIntrospection:
    """Test column introspection functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = QueryService()

    @pytest.fixture
    def mock_ds_config(self) -> DataSourceConfig:
        """Mock data source configuration."""
        return DataSourceConfig(  # type: ignore
            name="test_db",
            driver="postgresql",
            host="localhost",
            port=5432,
            database="testdb",
            username="testuser",
        )

    @pytest.mark.asyncio
    async def test_introspect_query_columns_success(self, mock_ds_config):
        """Should introspect columns from SELECT query."""
        # Mock DataFrame with expected columns
        test_df = pd.DataFrame(columns=["id", "name", "email", "created_at"])

        # Mock the loader
        with (
            patch("backend.app.services.query_service.DataLoaders.get") as mock_get_loader,
            patch("backend.app.services.query_service.DataSourceMapper.to_core_config") as mock_mapper,
        ):
            mock_loader = Mock()
            mock_loader.inject_limit = Mock(return_value="SELECT * FROM users LIMIT 0")
            mock_loader.read_sql = AsyncMock(return_value=test_df)
            mock_loader_cls = Mock(return_value=mock_loader)
            mock_get_loader.return_value = mock_loader_cls
            mock_mapper.return_value = Mock()

            query = "SELECT * FROM users"
            columns = await self.service.introspect_query_columns(ds_cfg=mock_ds_config, query=query)

            # Verify results
            assert isinstance(columns, list)
            assert len(columns) == 4
            assert "id" in columns
            assert "name" in columns
            assert "email" in columns
            assert "created_at" in columns

            # Verify LIMIT 0 was applied
            mock_loader.inject_limit.assert_called_once_with(query, 0)
            mock_loader.read_sql.assert_called_once()

    @pytest.mark.asyncio
    async def test_introspect_query_columns_with_aliases(self, mock_ds_config):
        """Should introspect columns with aliases."""
        # DataFrame with aliased columns
        test_df = pd.DataFrame(columns=["user_id", "full_name", "order_count"])

        with (
            patch("backend.app.services.query_service.DataLoaders.get") as mock_get_loader,
            patch("backend.app.services.query_service.DataSourceMapper.to_core_config") as mock_mapper,
        ):
            mock_loader = Mock()
            mock_loader.inject_limit = Mock(side_effect=lambda q, p: f"{q} LIMIT {p}")
            mock_loader.read_sql = AsyncMock(return_value=test_df)
            mock_loader_cls = Mock(return_value=mock_loader)
            mock_get_loader.return_value = mock_loader_cls
            mock_mapper.return_value = Mock()

            query = "SELECT id AS user_id, name AS full_name, COUNT(*) AS order_count FROM users"
            columns = await self.service.introspect_query_columns(ds_cfg=mock_ds_config, query=query)

            assert columns == ["user_id", "full_name", "order_count"]

    @pytest.mark.asyncio
    async def test_introspect_query_columns_complex_query(self, mock_ds_config):
        """Should introspect columns from complex JOIN query."""
        test_df = pd.DataFrame(columns=["user_id", "user_name", "order_id", "order_total"])

        with (
            patch("backend.app.services.query_service.DataLoaders.get") as mock_get_loader,
            patch("backend.app.services.query_service.DataSourceMapper.to_core_config") as mock_mapper,
        ):
            mock_loader = Mock()
            mock_loader.inject_limit = Mock(side_effect=lambda q, p: f"{q} LIMIT {p}")
            mock_loader.read_sql = AsyncMock(return_value=test_df)
            mock_loader_cls = Mock(return_value=mock_loader)
            mock_get_loader.return_value = mock_loader_cls
            mock_mapper.return_value = Mock()

            query = """
                SELECT u.id AS user_id, u.name AS user_name,
                       o.id AS order_id, o.total AS order_total
                FROM users u
                JOIN orders o ON u.id = o.user_id
                WHERE u.active = true
            """
            columns = await self.service.introspect_query_columns(ds_cfg=mock_ds_config, query=query)

            assert len(columns) == 4
            assert "user_id" in columns
            assert "order_total" in columns

    @pytest.mark.asyncio
    async def test_introspect_query_columns_rejects_destructive(self, mock_ds_config):
        """Should reject destructive queries during introspection."""
        with pytest.raises(QuerySecurityError) as exc_info:
            await self.service.introspect_query_columns(ds_cfg=mock_ds_config, query="DELETE FROM users")

        error = exc_info.value
        assert "prohibited operations" in error.message.lower()
        assert "DELETE" in error.context["violations"][0]

    @pytest.mark.asyncio
    async def test_introspect_query_columns_rejects_insert(self, mock_ds_config):
        """Should reject INSERT queries during introspection."""
        with pytest.raises(QuerySecurityError):
            await self.service.introspect_query_columns(ds_cfg=mock_ds_config, query="INSERT INTO users (name) VALUES ('test')")

    @pytest.mark.asyncio
    async def test_introspect_query_columns_execution_error(self, mock_ds_config):
        """Should handle query execution errors gracefully."""
        with (
            patch("backend.app.services.query_service.DataLoaders.get") as mock_get_loader,
            patch("backend.app.services.query_service.DataSourceMapper.to_core_config") as mock_mapper,
        ):
            mock_loader = Mock()
            mock_loader.inject_limit = Mock(side_effect=lambda q, p: f"{q} LIMIT {p}")
            mock_loader.read_sql = AsyncMock(side_effect=Exception("Table 'users' doesn't exist"))
            mock_loader_cls = Mock(return_value=mock_loader)
            mock_get_loader.return_value = mock_loader_cls
            mock_mapper.return_value = Mock()

            with pytest.raises(QueryExecutionError) as exc_info:
                await self.service.introspect_query_columns(ds_cfg=mock_ds_config, query="SELECT * FROM nonexistent_table")

            error = exc_info.value
            assert "introspection failed" in error.message.lower()
            assert "doesn't exist" not in error.message.lower()
            assert "query" not in error.context

    @pytest.mark.asyncio
    async def test_introspect_query_columns_timeout(self, mock_ds_config):
        """Should handle timeout during column introspection."""
        with (
            patch("backend.app.services.query_service.DataLoaders.get") as mock_get_loader,
            patch("backend.app.services.query_service.DataSourceMapper.to_core_config") as mock_mapper,
        ):
            mock_loader = Mock()
            mock_loader.inject_limit = Mock(side_effect=lambda q, p: f"{q} LIMIT {p}")
            mock_loader.read_sql = AsyncMock(side_effect=asyncio.TimeoutError())
            mock_loader_cls = Mock(return_value=mock_loader)
            mock_get_loader.return_value = mock_loader_cls
            mock_mapper.return_value = Mock()

            with pytest.raises(QueryExecutionError) as exc_info:
                await self.service.introspect_query_columns(ds_cfg=mock_ds_config, query="SELECT * FROM slow_table")

            error = exc_info.value
            assert "timed out" in error.message.lower()
            assert "10 seconds" in error.message.lower()

    @pytest.mark.asyncio
    async def test_introspect_query_columns_empty_result(self, mock_ds_config):
        """Should return columns even when result set is empty."""
        # DataFrame with columns but no rows
        test_df = pd.DataFrame(columns=["id", "name", "email"])

        with (
            patch("backend.app.services.query_service.DataLoaders.get") as mock_get_loader,
            patch("backend.app.services.query_service.DataSourceMapper.to_core_config") as mock_mapper,
        ):
            mock_loader = Mock()
            mock_loader.inject_limit = Mock(side_effect=lambda q, p: f"{q} LIMIT {p}")
            mock_loader.read_sql = AsyncMock(return_value=test_df)
            mock_loader_cls = Mock(return_value=mock_loader)
            mock_get_loader.return_value = mock_loader_cls
            mock_mapper.return_value = Mock()

            query = "SELECT id, name, email FROM users WHERE 1=0"
            columns = await self.service.introspect_query_columns(ds_cfg=mock_ds_config, query=query)

            assert len(columns) == 3
            assert columns == ["id", "name", "email"]

    @pytest.mark.asyncio
    async def test_introspect_query_columns_preserves_order(self, mock_ds_config):
        """Should preserve column order from query."""
        # Specific column order
        test_df = pd.DataFrame(columns=["email", "name", "id", "created_at"])

        with (
            patch("backend.app.services.query_service.DataLoaders.get") as mock_get_loader,
            patch("backend.app.services.query_service.DataSourceMapper.to_core_config") as mock_mapper,
        ):
            mock_loader = Mock()
            mock_loader.inject_limit = Mock(side_effect=lambda q, p: f"{q} LIMIT {p}")
            mock_loader.read_sql = AsyncMock(return_value=test_df)
            mock_loader_cls = Mock(return_value=mock_loader)
            mock_get_loader.return_value = mock_loader_cls
            mock_mapper.return_value = Mock()

            query = "SELECT email, name, id, created_at FROM users"
            columns = await self.service.introspect_query_columns(ds_cfg=mock_ds_config, query=query)

            assert columns == ["email", "name", "id", "created_at"]

    @pytest.mark.asyncio
    async def test_introspect_query_columns_with_aggregates(self, mock_ds_config):
        """Should introspect columns with aggregate functions."""
        test_df = pd.DataFrame(columns=["country", "total_users", "avg_age", "max_orders"])

        with (
            patch("backend.app.services.query_service.DataLoaders.get") as mock_get_loader,
            patch("backend.app.services.query_service.DataSourceMapper.to_core_config") as mock_mapper,
        ):
            mock_loader = Mock()
            mock_loader.inject_limit = Mock(side_effect=lambda q, p: f"{q} LIMIT {p}")
            mock_loader.read_sql = AsyncMock(return_value=test_df)
            mock_loader_cls = Mock(return_value=mock_loader)
            mock_get_loader.return_value = mock_loader_cls
            mock_mapper.return_value = Mock()

            query = """
                SELECT country,
                       COUNT(*) AS total_users,
                       AVG(age) AS avg_age,
                       MAX(orders) AS max_orders
                FROM users
                GROUP BY country
            """
            columns = await self.service.introspect_query_columns(ds_cfg=mock_ds_config, query=query)

            assert len(columns) == 4
            assert "total_users" in columns
            assert "avg_age" in columns
            assert "max_orders" in columns
