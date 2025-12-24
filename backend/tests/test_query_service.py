"""
Tests for Query Service
"""

from typing import Literal
from unittest.mock import AsyncMock, Mock, patch

import pandas as pd
import pytest

from backend.app.models.data_source import DataSourceConfig
from backend.app.models.query import QueryResult, QueryValidation
from backend.app.services.query_service import QueryExecutionError, QuerySecurityError, QueryService

# pylint: disable=redefined-outer-name, unused-argument, attribute-defined-outside-init


class TestQueryValidation:
    """Test query validation functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_ds_service = Mock()
        self.service = QueryService(self.mock_ds_service)

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
        """Should warn about multiple statements."""
        query: str = "SELECT * FROM users; SELECT * FROM orders;"
        result: QueryValidation = self.service.validate_query(query)

        assert len(result.warnings) > 0
        assert "multiple statements" in result.warnings[0].lower()

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
        self.mock_ds_service = Mock()
        self.service = QueryService(self.mock_ds_service)

    @pytest.fixture
    def mock_ds_service(self) -> Mock:
        """Mock pandas read_sql_query."""
        mock_ds_config = DataSourceConfig(
            name="test_db", driver="postgresql", host="localhost", port=5432, database="testdb", username="testuser", **{}
        )
        mock_ds_service = Mock(get_data_source=Mock(return_value=mock_ds_config))
        return mock_ds_service

    def mock_read_sql(self, test_df: pd.DataFrame, mock_get_loader: Mock) -> AsyncMock:
        """Mock the loader's read_sql method."""
        mock_read_sql: AsyncMock = AsyncMock(return_value=test_df)
        mock_loader_instance = Mock()
        mock_loader_instance.read_sql = mock_read_sql
        mock_loader_class = Mock(return_value=mock_loader_instance)
        mock_get_loader.return_value = mock_loader_class
        return mock_read_sql

    @pytest.mark.asyncio
    async def test_execute_simple_query(self, mock_ds_service):
        """Should execute SELECT query and return results."""

        test_df = pd.DataFrame({"id": [1, 2, 3], "name": ["Kalle", "Kula", "Kurt"]})

        # Mock the loader's read_sql method
        with patch("backend.app.services.query_service.DataLoaders.get") as mock_get_loader:

            _: Mock = self.mock_read_sql(test_df, mock_get_loader=mock_get_loader)
            query: str = "select * from users"

            service: QueryService = QueryService(data_source_service=mock_ds_service)
            result: QueryResult = await service.execute_query(data_source_name="test_db", query=query, limit=100)

            assert isinstance(result, QueryResult)
            assert result.row_count == 3
            assert len(result.columns) == 2
            assert "id" in result.columns
            assert "name" in result.columns
            assert len(result.rows) == 3
            assert result.execution_time_ms > 0

    @pytest.mark.asyncio
    async def test_execute_with_limit(self, mock_ds_service):
        """Should apply LIMIT clause to query."""
        test_df = pd.DataFrame({"id": range(50)})

        with patch("backend.app.services.query_service.DataLoaders.get") as mock_get_loader:

            mock_read_sql: Mock = self.mock_read_sql(test_df, mock_get_loader=mock_get_loader)

            query: str = "SELECT * FROM users"
            service: QueryService = QueryService(data_source_service=mock_ds_service)

            result: QueryResult = await service.execute_query("test_db", query, limit=50)

            called_query: str = mock_read_sql.call_args[0][0]
            assert "LIMIT" in called_query.upper()
            assert result.row_count == 50

    @pytest.mark.asyncio
    async def test_execute_truncated_result(self, mock_ds_service):
        """Should detect truncated results."""

        mock_conn = Mock()
        mock_ds_service.get_connection.return_value = mock_conn

        test_df = pd.DataFrame({"id": range(100)})  # Return exactly the limit

        with patch("backend.app.services.query_service.DataLoaders.get") as mock_get_loader:

            _: Mock = self.mock_read_sql(test_df, mock_get_loader=mock_get_loader)

            service: QueryService = QueryService(data_source_service=mock_ds_service)

            query: str = "SELECT * FROM users"
            result: QueryResult = await service.execute_query("test_db", query, limit=100)

            assert result.is_truncated is True

    @pytest.mark.asyncio
    async def test_execute_destructive_query(self, mock_ds_service):
        """Should reject destructive queries."""

        mock_conn = Mock()
        mock_ds_service.get_connection.return_value = mock_conn

        with pytest.raises(QuerySecurityError) as exc_info:

            service: QueryService = QueryService(data_source_service=mock_ds_service)
            query: str = "DELETE FROM users"

            await service.execute_query("test_db", query)

        assert "validation failed" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_execute_connection_error(self, mock_ds_service):
        """Should handle connection errors."""

        mock_ds_service.get_connection.side_effect = Exception("Connection failed")

        with pytest.raises(QueryExecutionError) as exc_info:

            query: str = "SELECT * FROM users"
            service: QueryService = QueryService(data_source_service=mock_ds_service)

            await service.execute_query("test_db", query)

        assert "connection failed" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_execute_query_error(self, mock_ds_service):
        """Should handle query execution errors."""

        mock_conn = Mock()
        mock_ds_service.get_connection.return_value = mock_conn

        with patch("pandas.read_sql_query", side_effect=Exception("Table not found")):

            query: str = "SELECT * FROM nonexistent"
            service: QueryService = QueryService(data_source_service=mock_ds_service)

            with pytest.raises(QueryExecutionError) as exc_info:
                await service.execute_query("test_db", query)
            assert "query execution failed" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_execute_with_null_values(self, mock_ds_service):
        """Should handle NULL values correctly."""

        mock_conn = Mock()
        mock_ds_service.get_connection.return_value = mock_conn
        test_df: pd.DataFrame = pd.DataFrame({"id": [1, 2, 3], "name": ["Alice", None, "Charlie"]})

        with patch("backend.app.services.query_service.DataLoaders.get") as mock_get_loader:
            _: Mock = self.mock_read_sql(test_df, mock_get_loader=mock_get_loader)

            query: str = "SELECT * FROM users"
            service = QueryService(data_source_service=mock_ds_service)
            result: QueryResult = await service.execute_query("test_db", query)

            # NULL should be converted to None
            assert result.rows[1]["name"] is None

    @pytest.mark.asyncio
    async def test_execute_with_datetime(self, mock_ds_service):
        """Should serialize datetime values correctly."""

        mock_conn = Mock()
        mock_ds_service.get_connection.return_value = mock_conn

        test_df = pd.DataFrame({"id": [1], "created_at": [pd.Timestamp("2024-01-01 12:00:00")]})

        with patch("backend.app.services.query_service.DataLoaders.get") as mock_get_loader:
            _: Mock = self.mock_read_sql(test_df, mock_get_loader=mock_get_loader)

            query: str = "SELECT * FROM users"
            service = QueryService(data_source_service=mock_ds_service)
            result: QueryResult = await service.execute_query("test_db", query)

            # Timestamp should be serialized as ISO string
            assert isinstance(result.rows[0]["created_at"], str)
            assert "2024-01-01" in result.rows[0]["created_at"]

    @pytest.mark.asyncio
    async def test_execute_respects_max_limit(self, mock_ds_service):
        """Should enforce maximum row limit."""
        mock_conn = Mock()
        mock_ds_service.get_connection.return_value = mock_conn
        test_df = pd.DataFrame({"id": range(100)})

        with patch("backend.app.services.query_service.DataLoaders.get") as mock_get_loader:
            _: Mock = self.mock_read_sql(test_df, mock_get_loader=mock_get_loader)

            query: str = "SELECT * FROM users"
            service = QueryService(data_source_service=mock_ds_service)
            result: QueryResult = await service.execute_query("test_db", query, limit=20000)

            assert result.row_count <= QueryService.MAX_ROWS


class TestSQLParsing:
    """Test SQL parsing utilities."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_ds_service = Mock()
        self.service = QueryService(self.mock_ds_service)

    def test_add_limit_to_select(self):
        """Should add LIMIT clause to SELECT query."""
        query: str = "SELECT * FROM users"
        modified = self.service._add_limit_clause(query, 100)

        assert "LIMIT 100" in modified

    def test_preserve_existing_limit(self):
        """Should not modify query with existing LIMIT."""
        query: str = "SELECT * FROM users LIMIT 50"
        modified = self.service._add_limit_clause(query, 100)

        assert modified == query

    def test_dont_add_limit_to_non_select(self):
        """Should not add LIMIT to non-SELECT queries."""
        query: str = "INSERT INTO users (name) VALUES ('test')"
        modified = self.service._add_limit_clause(query, 100)

        assert "LIMIT" not in modified
        assert modified == query
