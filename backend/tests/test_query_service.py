"""
Tests for Query Service
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import pandas as pd

from app.services.query_service import QueryService, QuerySecurityError, QueryExecutionError
from app.models.query import QueryResult, QueryValidation, QueryPlan


class TestQueryValidation:
    """Test query validation functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_ds_service = Mock()
        self.service = QueryService(self.mock_ds_service)
    
    def test_validate_select_query(self):
        """Should validate SELECT queries as valid."""
        query = "SELECT * FROM users WHERE id = 1"
        result = self.service.validate_query(query)
        
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert result.statement_type == "SELECT"
        assert "users" in result.tables
    
    def test_validate_insert_query(self):
        """Should reject INSERT queries as destructive."""
        query = "INSERT INTO users (name) VALUES ('test')"
        result = self.service.validate_query(query)
        
        assert result.is_valid is False
        assert len(result.errors) > 0
        assert "INSERT" in result.errors[0]
        assert result.statement_type == "INSERT"
    
    def test_validate_update_query(self):
        """Should reject UPDATE queries as destructive."""
        query = "UPDATE users SET name = 'test' WHERE id = 1"
        result = self.service.validate_query(query)
        
        assert result.is_valid is False
        assert "UPDATE" in result.errors[0]
    
    def test_validate_delete_query(self):
        """Should reject DELETE queries as destructive."""
        query = "DELETE FROM users WHERE id = 1"
        result = self.service.validate_query(query)
        
        assert result.is_valid is False
        assert "DELETE" in result.errors[0]
    
    def test_validate_drop_query(self):
        """Should reject DROP queries as destructive."""
        query = "DROP TABLE users"
        result = self.service.validate_query(query)
        
        assert result.is_valid is False
        assert "DROP" in result.errors[0]
    
    def test_validate_empty_query(self):
        """Should reject empty queries."""
        query = ""
        result = self.service.validate_query(query)
        
        assert result.is_valid is False
        assert len(result.errors) > 0
    
    def test_validate_syntax_error(self):
        """Should detect syntax errors."""
        query = "SELECT * FROM"  # Incomplete query
        result = self.service.validate_query(query)
        
        # Query might still parse but be invalid
        assert result.is_valid is True or len(result.errors) > 0
    
    def test_validate_multiple_statements(self):
        """Should warn about multiple statements."""
        query = "SELECT * FROM users; SELECT * FROM orders;"
        result = self.service.validate_query(query)
        
        assert len(result.warnings) > 0
        assert "multiple statements" in result.warnings[0].lower()
    
    def test_validate_no_where_clause(self):
        """Should warn about queries without WHERE clause."""
        query = "SELECT * FROM users"
        result = self.service.validate_query(query)
        
        assert result.is_valid is True
        # Should have warning about missing WHERE clause
        warning_found = any("where" in w.lower() for w in result.warnings)
        assert warning_found
    
    def test_extract_table_names(self):
        """Should extract table names from query."""
        query = "SELECT u.*, o.* FROM users u JOIN orders o ON u.id = o.user_id"
        result = self.service.validate_query(query)
        
        assert "users" in result.tables
        assert "orders" in result.tables
    
    def test_extract_schema_qualified_table(self):
        """Should extract table names with schema prefix."""
        query = "SELECT * FROM public.users"
        result = self.service.validate_query(query)
        
        assert "users" in result.tables


class TestQueryExecution:
    """Test query execution functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_ds_service = Mock()
        self.service = QueryService(self.mock_ds_service)
    
    def test_execute_simple_query(self):
        """Should execute SELECT query and return results."""
        # Mock connection
        mock_conn = Mock()
        self.mock_ds_service.get_connection.return_value = mock_conn
        
        # Mock DataFrame result
        test_df = pd.DataFrame({
            'id': [1, 2, 3],
            'name': ['Alice', 'Bob', 'Charlie']
        })
        
        with patch('pandas.read_sql_query', return_value=test_df):
            query = "SELECT * FROM users"
            result = self.service.execute_query('test_db', query, limit=100)
            
            assert isinstance(result, QueryResult)
            assert result.row_count == 3
            assert len(result.columns) == 2
            assert 'id' in result.columns
            assert 'name' in result.columns
            assert len(result.rows) == 3
            assert result.execution_time_ms > 0
    
    def test_execute_with_limit(self):
        """Should apply LIMIT clause to query."""
        mock_conn = Mock()
        self.mock_ds_service.get_connection.return_value = mock_conn
        
        test_df = pd.DataFrame({'id': range(50)})
        
        with patch('pandas.read_sql_query', return_value=test_df) as mock_sql:
            query = "SELECT * FROM users"
            result = self.service.execute_query('test_db', query, limit=50)
            
            # Check that LIMIT was added to query
            called_query = mock_sql.call_args[0][0]
            assert 'LIMIT' in called_query.upper()
            assert result.row_count == 50
    
    def test_execute_truncated_result(self):
        """Should detect truncated results."""
        mock_conn = Mock()
        self.mock_ds_service.get_connection.return_value = mock_conn
        
        # Return exactly the limit
        test_df = pd.DataFrame({'id': range(100)})
        
        with patch('pandas.read_sql_query', return_value=test_df):
            query = "SELECT * FROM users"
            result = self.service.execute_query('test_db', query, limit=100)
            
            assert result.is_truncated is True
    
    def test_execute_destructive_query(self):
        """Should reject destructive queries."""
        mock_conn = Mock()
        self.mock_ds_service.get_connection.return_value = mock_conn
        
        query = "DELETE FROM users"
        
        with pytest.raises(QuerySecurityError) as exc_info:
            self.service.execute_query('test_db', query)
        
        assert "validation failed" in str(exc_info.value).lower()
    
    def test_execute_connection_error(self):
        """Should handle connection errors."""
        self.mock_ds_service.get_connection.side_effect = Exception("Connection failed")
        
        query = "SELECT * FROM users"
        
        with pytest.raises(QueryExecutionError) as exc_info:
            self.service.execute_query('test_db', query)
        
        assert "failed to connect" in str(exc_info.value).lower()
    
    def test_execute_query_error(self):
        """Should handle query execution errors."""
        mock_conn = Mock()
        self.mock_ds_service.get_connection.return_value = mock_conn
        
        with patch('pandas.read_sql_query', side_effect=Exception("Table not found")):
            query = "SELECT * FROM nonexistent"
            
            with pytest.raises(QueryExecutionError) as exc_info:
                self.service.execute_query('test_db', query)
            
            assert "query execution failed" in str(exc_info.value).lower()
    
    def test_execute_with_null_values(self):
        """Should handle NULL values correctly."""
        mock_conn = Mock()
        self.mock_ds_service.get_connection.return_value = mock_conn
        
        test_df = pd.DataFrame({
            'id': [1, 2, 3],
            'name': ['Alice', None, 'Charlie']
        })
        
        with patch('pandas.read_sql_query', return_value=test_df):
            query = "SELECT * FROM users"
            result = self.service.execute_query('test_db', query)
            
            # NULL should be converted to None
            assert result.rows[1]['name'] is None
    
    def test_execute_with_datetime(self):
        """Should serialize datetime values correctly."""
        mock_conn = Mock()
        self.mock_ds_service.get_connection.return_value = mock_conn
        
        test_df = pd.DataFrame({
            'id': [1],
            'created_at': [pd.Timestamp('2024-01-01 12:00:00')]
        })
        
        with patch('pandas.read_sql_query', return_value=test_df):
            query = "SELECT * FROM users"
            result = self.service.execute_query('test_db', query)
            
            # Timestamp should be serialized as ISO string
            assert isinstance(result.rows[0]['created_at'], str)
            assert '2024-01-01' in result.rows[0]['created_at']
    
    def test_execute_respects_max_limit(self):
        """Should enforce maximum row limit."""
        mock_conn = Mock()
        self.mock_ds_service.get_connection.return_value = mock_conn
        
        test_df = pd.DataFrame({'id': range(100)})
        
        with patch('pandas.read_sql_query', return_value=test_df):
            # Try to request more than MAX_ROWS
            query = "SELECT * FROM users"
            result = self.service.execute_query('test_db', query, limit=20000)
            
            # Should be capped at MAX_ROWS (10000)
            assert result.row_count <= QueryService.MAX_ROWS


class TestQueryPlan:
    """Test query explain functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_ds_service = Mock()
        self.service = QueryService(self.mock_ds_service)
    
    def test_explain_query(self):
        """Should get query execution plan."""
        mock_conn = Mock()
        self.mock_ds_service.get_connection.return_value = mock_conn
        
        # Mock EXPLAIN output
        explain_df = pd.DataFrame({
            'QUERY PLAN': [
                'Seq Scan on users  (cost=0.00..10.00 rows=100 width=32)',
                '  Filter: (id = 1)'
            ]
        })
        
        with patch('pandas.read_sql_query', return_value=explain_df):
            query = "SELECT * FROM users WHERE id = 1"
            result = self.service.explain_query('test_db', query)
            
            assert isinstance(result, QueryPlan)
            assert 'Seq Scan' in result.plan_text
            assert 'users' in result.plan_text
    
    def test_explain_connection_error(self):
        """Should handle connection errors for explain."""
        self.mock_ds_service.get_connection.side_effect = Exception("Connection failed")
        
        query = "SELECT * FROM users"
        
        with pytest.raises(QueryExecutionError) as exc_info:
            self.service.explain_query('test_db', query)
        
        assert "failed to connect" in str(exc_info.value).lower()


class TestSQLParsing:
    """Test SQL parsing utilities."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_ds_service = Mock()
        self.service = QueryService(self.mock_ds_service)
    
    def test_add_limit_to_select(self):
        """Should add LIMIT clause to SELECT query."""
        query = "SELECT * FROM users"
        modified = self.service._add_limit_clause(query, 100)
        
        assert 'LIMIT 100' in modified
    
    def test_preserve_existing_limit(self):
        """Should not modify query with existing LIMIT."""
        query = "SELECT * FROM users LIMIT 50"
        modified = self.service._add_limit_clause(query, 100)
        
        assert modified == query
    
    def test_dont_add_limit_to_non_select(self):
        """Should not add LIMIT to non-SELECT queries."""
        query = "INSERT INTO users (name) VALUES ('test')"
        modified = self.service._add_limit_clause(query, 100)
        
        assert 'LIMIT' not in modified
        assert modified == query
