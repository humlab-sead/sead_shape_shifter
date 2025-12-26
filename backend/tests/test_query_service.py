"""Tests for QueryService."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest
import sqlparse

from backend.app.models.query import QueryResult, QueryValidation
from backend.app.services.query_service import QueryExecutionError, QueryService


class TestQueryService:
    """Test QueryService for SQL query validation and execution."""

    @pytest.fixture
    def service(self) -> QueryService:
        """Create QueryService instance."""
        with patch("backend.app.services.query_service.DataSourceService") as mock_ds_service:
            mock_ds_service.return_value.get_data_source = MagicMock(return_value=MagicMock())
            return QueryService(data_source_service=mock_ds_service)

    @pytest.fixture
    def mock_loader(self) -> AsyncMock:
        """Create mock SQL loader."""
        loader = AsyncMock()
        loader.read_sql = AsyncMock(return_value=pd.DataFrame({"id": [1, 2], "name": ["Alice", "Bob"]}))
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
    async def test_execute_query_success(self, service: QueryService, mock_loader: AsyncMock):
        """Test successful query execution."""
        query = "SELECT * FROM users"

        with (
            patch("backend.app.services.query_service.DataSourceService") as mock_ds,
            patch("backend.app.services.query_service.DataLoaders.get") as mock_get_loader,
            patch("backend.app.services.query_service.DataSourceMapper") as mock_mapper,
        ):
            mock_ds.return_value.get_data_source = MagicMock(return_value=MagicMock())
            mock_get_loader.return_value = lambda data_source: mock_loader
            mock_mapper.to_core_config = MagicMock(return_value=MagicMock())

            result = await service.execute_query(query, "test_source")

            assert isinstance(result, QueryResult)
            assert result.row_count == 2
            assert result.columns == ["id", "name"]
            assert len(result.rows) == 2
            assert result.rows[0]["name"] == "Alice"

    @pytest.mark.asyncio
    async def test_execute_query_applies_limit(self, service: QueryService, mock_loader: AsyncMock):
        """Test execution applies LIMIT clause."""
        query = "SELECT * FROM users"

        with (
            patch("backend.app.services.query_service.DataSourceService") as mock_ds,
            patch("backend.app.services.query_service.DataLoaders.get") as mock_get_loader,
            patch("backend.app.services.query_service.DataSourceMapper") as mock_mapper,
        ):
            mock_ds.return_value.get_data_source = MagicMock(return_value=MagicMock())
            mock_get_loader.return_value = lambda data_source: mock_loader
            mock_mapper.to_core_config = MagicMock(return_value=MagicMock())

            await service.execute_query(data_source_name="test_source", query=query, limit=100)

            # Verify loader was called with modified query
            call_args = mock_loader.read_sql.call_args
            sql_param = call_args[0][0] if call_args else None
            assert sql_param is not None
            assert "LIMIT 100" in sql_param

    @pytest.mark.asyncio
    async def test_execute_query_preserves_existing_limit(self, service: QueryService, mock_loader: AsyncMock):
        """Test execution preserves user-specified LIMIT."""
        query = "SELECT * FROM users LIMIT 10"

        with (
            patch("backend.app.services.query_service.DataSourceService") as mock_ds,
            patch("backend.app.services.query_service.DataLoaders.get") as mock_get_loader,
            patch("backend.app.services.query_service.DataSourceMapper") as mock_mapper,
        ):
            mock_ds.return_value.get_data_source = MagicMock(return_value=MagicMock())
            mock_get_loader.return_value = lambda data_source: mock_loader
            mock_mapper.to_core_config = MagicMock(return_value=MagicMock())

            await service.execute_query(data_source_name="test_source", query=query, limit=100)

            call_args = mock_loader.read_sql.call_args
            sql_param = call_args[0][0] if call_args else None
            # Should keep original LIMIT 10, not add LIMIT 100
            assert sql_param is not None
            assert sql_param.count("LIMIT") == 1

    @pytest.mark.asyncio
    async def test_execute_query_data_source_not_found(self, service: QueryService):
        """Test execution with non-existent data source."""
        # Patch the service's data_source_service directly
        service.data_source_service.get_data_source = MagicMock(return_value=None)

        with pytest.raises(QueryExecutionError, match="does not exist"):
            await service.execute_query(data_source_name="nonexistent", query="SELECT 1")

    @pytest.mark.asyncio
    async def test_execute_query_timeout(self, service: QueryService):
        """Test execution timeout handling."""
        query = "SELECT * FROM users"

        async def slow_read_sql(query):  # pylint: disable=unused-argument
            await asyncio.sleep(10)
            return pd.DataFrame()

        slow_loader = AsyncMock()
        slow_loader.read_sql = slow_read_sql

        with (
            patch("backend.app.services.query_service.DataSourceService") as mock_ds,
            patch("backend.app.services.query_service.DataLoaders.get") as mock_get_loader,
            patch("backend.app.services.query_service.DataSourceMapper") as mock_mapper,
        ):
            mock_ds.return_value.get_data_source = MagicMock(return_value=MagicMock())
            mock_get_loader.return_value = lambda data_source: slow_loader
            mock_mapper.to_core_config = MagicMock(return_value=MagicMock())

            with pytest.raises(QueryExecutionError, match="timed out"):
                await service.execute_query(data_source_name="test_source", query=query, timeout=1)

    @pytest.mark.asyncio
    async def test_execute_query_loader_error(self, service: QueryService):
        """Test execution handles loader errors."""
        query = "SELECT * FROM users"
        error_loader = AsyncMock()
        error_loader.read_sql = AsyncMock(side_effect=RuntimeError("Database error"))

        with (
            patch("backend.app.services.query_service.DataSourceService") as mock_ds,
            patch("backend.app.services.query_service.DataLoaders.get") as mock_get_loader,
            patch("backend.app.services.query_service.DataSourceMapper") as mock_mapper,
        ):
            mock_ds.return_value.get_data_source = MagicMock(return_value=MagicMock())
            mock_get_loader.return_value = lambda data_source: error_loader
            mock_mapper.to_core_config = MagicMock(return_value=MagicMock())

            with pytest.raises(QueryExecutionError, match="Database error"):
                await service.execute_query(data_source_name="test_source", query=query)

    @pytest.mark.asyncio
    async def test_execute_query_empty_result(self, service: QueryService):
        """Test execution with empty result set."""
        query = "SELECT * FROM users WHERE id = 999"
        empty_loader = AsyncMock()
        empty_loader.read_sql = AsyncMock(return_value=pd.DataFrame(columns=["id", "name"]))

        with (
            patch("backend.app.services.query_service.DataSourceService") as mock_ds,
            patch("backend.app.services.query_service.DataLoaders.get") as mock_get_loader,
            patch("backend.app.services.query_service.DataSourceMapper") as mock_mapper,
        ):
            mock_ds.return_value.get_data_source = MagicMock(return_value=MagicMock())
            mock_get_loader.return_value = lambda data_source: empty_loader
            mock_mapper.to_core_config = MagicMock(return_value=MagicMock())

            result = await service.execute_query(data_source_name="test_source", query=query)

            assert result.row_count == 0
            assert result.columns == ["id", "name"]
            assert result.rows == []

    @pytest.mark.asyncio
    async def test_execute_query_handles_null_values(self, service: QueryService):
        """Test execution properly handles NULL values."""
        df = pd.DataFrame({"id": [1, 2], "name": ["Alice", None]})
        null_loader = AsyncMock()
        null_loader.read_sql = AsyncMock(return_value=df)

        with (
            patch("backend.app.services.query_service.DataSourceService") as mock_ds,
            patch("backend.app.services.query_service.DataLoaders.get") as mock_get_loader,
            patch("backend.app.services.query_service.DataSourceMapper") as mock_mapper,
        ):
            mock_ds.return_value.get_data_source = MagicMock(return_value=MagicMock())
            mock_get_loader.return_value = lambda data_source: null_loader
            mock_mapper.to_core_config = MagicMock(return_value=MagicMock())

            result = await service.execute_query(data_source_name="test_source", query="SELECT * FROM users")

            assert result.rows[1]["name"] is None

    @pytest.mark.asyncio
    async def test_execute_query_handles_timestamps(self, service: QueryService):
        """Test execution serializes timestamp values."""
        df = pd.DataFrame({"id": [1], "created": [pd.Timestamp("2024-01-01 12:00:00")]})
        ts_loader = AsyncMock()
        ts_loader.read_sql = AsyncMock(return_value=df)

        with (
            patch("backend.app.services.query_service.DataSourceService") as mock_ds,
            patch("backend.app.services.query_service.DataLoaders.get") as mock_get_loader,
            patch("backend.app.services.query_service.DataSourceMapper") as mock_mapper,
        ):
            mock_ds.return_value.get_data_source = MagicMock(return_value=MagicMock())
            mock_get_loader.return_value = lambda data_source: ts_loader
            mock_mapper.to_core_config = MagicMock(return_value=MagicMock())

            result = await service.execute_query(data_source_name="test_source", query="SELECT * FROM events")

            assert isinstance(result.rows[0]["created"], str)
            assert "2024-01-01" in result.rows[0]["created"]

    @pytest.mark.asyncio
    async def test_execute_query_truncation_flag(self, service: QueryService):
        """Test execution sets truncation flag correctly."""
        # Create large result set
        df = pd.DataFrame({"id": range(1000), "value": range(1000)})
        large_loader = AsyncMock()
        large_loader.read_sql = AsyncMock(return_value=df)

        with (
            patch("backend.app.services.query_service.DataSourceService") as mock_ds,
            patch("backend.app.services.query_service.DataLoaders.get") as mock_get_loader,
            patch("backend.app.services.query_service.DataSourceMapper") as mock_mapper,
        ):
            mock_ds.return_value.get_data_source = MagicMock(return_value=MagicMock())
            mock_get_loader.return_value = lambda data_source: large_loader
            mock_mapper.to_core_config = MagicMock(return_value=MagicMock())

            result = await service.execute_query(data_source_name="test_source", query="SELECT * FROM large_table", limit=100)

            # Since result >= limit, should be truncated
            assert result.is_truncated is True

    @pytest.mark.asyncio
    async def test_execute_query_tracks_execution_time(self, service: QueryService):
        """Test execution tracks query time."""
        # Create loader with read_sql method
        mock_loader = AsyncMock()
        mock_loader.read_sql = AsyncMock(return_value=pd.DataFrame({"id": [1, 2], "name": ["Alice", "Bob"]}))

        with (
            patch("backend.app.services.query_service.DataSourceService") as mock_ds,
            patch("backend.app.services.query_service.DataLoaders.get") as mock_get_loader,
            patch("backend.app.services.query_service.DataSourceMapper") as mock_mapper,
        ):
            mock_ds.return_value.get_data_source = MagicMock(return_value=MagicMock())
            mock_get_loader.return_value = lambda data_source: mock_loader
            mock_mapper.to_core_config = MagicMock(return_value=MagicMock())

            result: QueryResult = await service.execute_query(data_source_name="test_source", query="SELECT * FROM users")

            assert result.execution_time_ms > 0

    # Helper method tests

    def test_get_statement_type_select(self, service: QueryService):
        """Test statement type extraction for SELECT."""
        parsed = sqlparse.parse("SELECT * FROM users")[0]
        stmt_type = service._get_statement_type(parsed)
        assert stmt_type == "SELECT"

    def test_get_statement_type_insert(self, service: QueryService):
        """Test statement type extraction for INSERT."""
        parsed = sqlparse.parse("INSERT INTO users VALUES (1, 'Alice')")[0]
        stmt_type = service._get_statement_type(parsed)
        assert stmt_type == "INSERT"

    def test_get_statement_type_delete(self, service: QueryService):
        """Test statement type extraction for DELETE."""
        parsed = sqlparse.parse("DELETE FROM users WHERE id = 1")[0]
        stmt_type = service._get_statement_type(parsed)
        assert stmt_type == "DELETE"

    def test_extract_table_names_simple(self, service: QueryService):
        """Test table name extraction from simple query."""
        parsed = sqlparse.parse("SELECT * FROM users")[0]
        tables = service._extract_table_names(parsed)
        assert "users" in tables

    def test_extract_table_names_join(self, service: QueryService):
        """Test table name extraction from JOIN query."""
        parsed = sqlparse.parse("SELECT * FROM users u JOIN orders o ON u.id = o.user_id")[0]
        tables = service._extract_table_names(parsed)
        assert "users" in tables
        assert "orders" in tables

    def test_extract_table_names_with_schema(self, service: QueryService):
        """Test table name extraction strips schema prefix."""
        parsed = sqlparse.parse("SELECT * FROM public.users")[0]
        tables = service._extract_table_names(parsed)
        assert "users" in tables
        assert "public" not in tables

    def test_has_where_clause_true(self, service: QueryService):
        """Test WHERE clause detection - present."""
        parsed = sqlparse.parse("SELECT * FROM users WHERE id > 10")[0]
        has_where = service._has_where_clause(parsed)
        assert has_where is True

    def test_has_where_clause_false(self, service: QueryService):
        """Test WHERE clause detection - absent."""
        parsed = sqlparse.parse("SELECT * FROM users")[0]
        has_where = service._has_where_clause(parsed)
        assert has_where is False

    def test_add_limit_clause_adds_limit(self, service: QueryService):
        """Test LIMIT clause is added when missing."""
        query = "SELECT * FROM users"
        modified = service._add_limit_clause(query, 100)
        assert "LIMIT 100" in modified

    def test_add_limit_clause_preserves_existing(self, service: QueryService):
        """Test existing LIMIT clause is preserved."""
        query = "SELECT * FROM users LIMIT 50"
        modified = service._add_limit_clause(query, 100)
        assert modified.count("LIMIT") == 1
        assert "LIMIT 50" in modified

    def test_add_limit_clause_only_for_select(self, service: QueryService):
        """Test LIMIT only added to SELECT queries."""
        query = "INSERT INTO users VALUES (1, 'Alice')"
        modified = service._add_limit_clause(query, 100)
        assert "LIMIT" not in modified

    def test_add_limit_clause_strips_semicolon(self, service: QueryService):
        """Test LIMIT added before trailing semicolon."""
        query = "SELECT * FROM users;"
        modified = service._add_limit_clause(query, 100)
        assert modified.endswith("LIMIT 100")
        assert modified.count(";") == 0
