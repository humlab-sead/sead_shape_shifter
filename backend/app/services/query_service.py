"""
Query execution service for the Shape Shifter Configuration Editor.

Provides secure SQL query execution with validation, timeout protection,
and result size limiting.
"""

import asyncio
import time
from multiprocessing.dummy import connection
from typing import List, Optional

import pandas as pd
import sqlparse
from sqlparse.sql import Identifier, Statement
from sqlparse.tokens import DDL, DML, Keyword

from backend.app.models.query import QueryPlan, QueryResult, QueryValidation
from backend.app.services.data_source_service import DataSourceService
from src.config_model import DataSourceConfig as CoreDataSourceConfig
from src.loaders.base_loader import DataLoaders


class QueryExecutionError(Exception):
    """Raised when query execution fails."""


class QuerySecurityError(Exception):
    """Raised when query contains destructive operations."""


class QueryService:
    """Service for executing and validating SQL queries."""

    # Destructive SQL keywords that should be blocked
    DESTRUCTIVE_KEYWORDS = {"INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", "TRUNCATE", "REPLACE", "MERGE", "GRANT", "REVOKE"}

    # Maximum result size in bytes (100 MB)
    MAX_RESULT_SIZE_BYTES = 100 * 1024 * 1024

    # Maximum number of rows (safety limit)
    MAX_ROWS = 10000

    def __init__(self, data_source_service: DataSourceService):
        """
        Initialize query service.

        Args:
            data_source_service: Service for managing data source connections
        """
        self.data_source_service = data_source_service

    def validate_query(
        self,
        query: str,
        data_source_name: Optional[str] = None,  #  pylint: disable=unused-argument
    ) -> QueryValidation:
        """
        Validate a SQL query for safety and syntax.

        Args:
            query: SQL query to validate
            data_source_name: Optional data source name for dialect-specific validation

        Returns:
            QueryValidation with validation results
        """
        errors: list[str] = []
        warnings: list[str] = []

        # Parse query
        try:
            parsed = sqlparse.parse(query)
            if not parsed:
                return QueryValidation(is_valid=False, errors=["Empty or invalid SQL query"], warnings=[], statement_type=None, tables=[])
        except Exception as e:  # pylint: disable=broad-except
            return QueryValidation(is_valid=False, errors=[f"SQL syntax error: {str(e)}"], warnings=[], statement_type=None, tables=[])

        # Get first statement
        statement = parsed[0]

        # Detect statement type
        statement_type = self._get_statement_type(statement)

        # Check for destructive operations
        if statement_type and statement_type.upper() in self.DESTRUCTIVE_KEYWORDS:
            errors.append(f"Destructive SQL operation '{statement_type}' is not allowed. " f"Only SELECT queries are permitted.")

        # Extract table names
        tables = self._extract_table_names(statement)

        # Check for multiple statements
        if len(parsed) > 1:
            warnings.append("Query contains multiple statements. Only the first will be executed.")

        # Check for missing WHERE clause on large tables (heuristic warning)
        if statement_type == "SELECT" and not self._has_where_clause(statement):
            warnings.append("Query has no WHERE clause. This may return a large result set.")

        is_valid = len(errors) == 0

        return QueryValidation(is_valid=is_valid, errors=errors, warnings=warnings, statement_type=statement_type, tables=tables)

    async def execute_query(self, data_source_name: str, query: str, limit: int = 100, timeout: int = 30) -> QueryResult:
        """
        Execute a SQL query against a data source.

        Args:
            data_source_name: Name of the data source
            query: SQL query to execute
            limit: Maximum number of rows to return (default 100)
            timeout: Query timeout in seconds (default 30)

        Returns:
            QueryResult with query results

        Raises:
            QuerySecurityError: If query contains destructive operations
            QueryExecutionError: If query execution fails
        """
        # Validate query
        validation = self.validate_query(query, data_source_name)
        if not validation.is_valid:
            raise QuerySecurityError(f"Query validation failed: {', '.join(validation.errors)}")

        # Enforce limits
        limit = min(limit, self.MAX_ROWS)
        timeout = min(timeout, 300)  # Max 5 minutes

        # Get data source config
        try:
            ds_config = self.data_source_service.get_data_source(data_source_name)
        except Exception as e:
            raise QueryExecutionError(f"Data source not found: {str(e)}") from e

        # Build config dict for core system
        config_dict = {
            "driver": ds_config.get_loader_driver(),
            "host": ds_config.host,
            "port": ds_config.port,
            "database": ds_config.effective_database,
            "username": ds_config.username,
            "password": ds_config.password.get_secret_value() if ds_config.password else None,
            "filename": ds_config.effective_file_path,
            "options": ds_config.options or {},
        }

        # Create core config instance
        core_config = CoreDataSourceConfig(cfg=config_dict, name=data_source_name)

        # Get appropriate loader
        try:
            loader = DataLoaders.get(core_config.driver)(data_source=core_config)
        except Exception as e:
            raise QueryExecutionError(f"Failed to get data loader: {str(e)}") from e

        # Execute query with timeout
        start_time = time.time()

        try:
            # Add LIMIT clause if not present (for SELECT queries)
            modified_query = self._add_limit_clause(query, limit)

            # Execute query using loader
            df = await asyncio.wait_for(loader.read_sql(modified_query), timeout=timeout)

            execution_time_ms = max(1, int((time.time() - start_time) * 1000))

            # Check result size
            is_truncated = len(df) >= limit

            # Convert to list of dicts
            rows = df.to_dict("records")
            columns = df.columns.tolist()

            # Handle datetime serialization
            for row in rows:
                for key, value in row.items():
                    if pd.isna(value):
                        row[key] = None
                    elif isinstance(value, pd.Timestamp):
                        row[key] = value.isoformat()

            return QueryResult(
                rows=rows,
                columns=columns,
                row_count=len(rows),
                execution_time_ms=execution_time_ms,
                is_truncated=is_truncated,
                total_rows=len(rows) if not is_truncated else None,
            )

        except asyncio.TimeoutError:
            raise QueryExecutionError(f"Query execution timed out after {timeout} seconds") from e
        except Exception as e:
            raise QueryExecutionError(f"Query execution failed: {str(e)}") from e

    async def explain_query(self, data_source_name: str, query: str) -> QueryPlan:
        """
        Get the execution plan for a query.

        Args:
            data_source_name: Name of the data source
            query: SQL query to explain

        Returns:
            QueryPlan with execution plan

        Raises:
            QueryExecutionError: If explain fails
        """
        # Get data source config
        try:
            ds_config = self.data_source_service.get_data_source(data_source_name)
        except Exception as e:
            raise QueryExecutionError(f"Data source not found: {str(e)}") from e

        # Build config dict for core system
        config_dict = {
            "driver": ds_config.get_loader_driver(),
            "host": ds_config.host,
            "port": ds_config.port,
            "database": ds_config.effective_database,
            "username": ds_config.username,
            "password": ds_config.password.get_secret_value() if ds_config.password else None,
            "filename": ds_config.effective_file_path,
            "options": ds_config.options or {},
        }

        # Create core config instance
        core_config = CoreDataSourceConfig(cfg=config_dict, name=data_source_name)

        # Get appropriate loader
        try:
            loader = DataLoaders.get(core_config.driver)(data_source=core_config)
        except Exception as e:
            raise QueryExecutionError(f"Failed to get data loader: {str(e)}") from e

        try:
            # Different databases have different EXPLAIN syntax
            explain_query = f"EXPLAIN {query}"

            df = await loader.read_sql(explain_query)

            # Format the plan
            plan_text = "\n".join(df.iloc[:, 0].astype(str).tolist())

            return QueryPlan(plan_text=plan_text, estimated_cost=None, estimated_rows=None)  # Would need to parse EXPLAIN output

        except Exception as e:
            raise QueryExecutionError(f"Failed to get query plan: {str(e)}") from e
        finally:
            if hasattr(connection, "close"):
                try:
                    connection.close()
                except:  # pylint: disable=bare-except
                    pass

    def _get_statement_type(self, statement: Statement) -> Optional[str]:
        """Extract the statement type (SELECT, INSERT, etc.) from parsed SQL."""
        for token in statement.tokens:
            if token.ttype is DML:
                return token.value.upper()
            if token.ttype is DDL:
                return token.value.upper()
            if token.ttype is Keyword and token.value.upper() in self.DESTRUCTIVE_KEYWORDS:
                return token.value.upper()
        return None

    def _extract_table_names(self, statement: Statement) -> List[str]:
        """Extract table names from a SQL statement."""
        tables = []
        from_seen = False

        def extract_name(identifier):
            """Extract table name from identifier, handling schema.table format."""
            if isinstance(identifier, Identifier):
                name = identifier.get_real_name()
            else:
                name = str(identifier).strip()

            # Remove quotes and brackets
            name = name.strip('`"[]')

            # Handle schema.table format
            if "." in name:
                name = name.split(".")[-1]

            return name

        for token in statement.tokens:
            if token.ttype is Keyword:
                keyword = token.value.upper()
                if keyword in ("FROM", "JOIN"):
                    from_seen = True
            elif from_seen and not token.is_whitespace:
                if isinstance(token, Identifier):
                    table_name = extract_name(token)
                    if table_name and table_name.upper() not in ("SELECT", "WHERE", "ON"):
                        tables.append(table_name)
                        from_seen = False
                elif token.ttype is None:
                    # Simple name
                    table_name = token.value.strip('`"[]')
                    if "." in table_name:
                        table_name = table_name.split(".")[-1]
                    if table_name and not any(c in table_name for c in "(),"):
                        tables.append(table_name)
                        from_seen = False

        return tables

    def _has_where_clause(self, statement: Statement) -> bool:
        """Check if statement contains a WHERE clause."""
        for token in statement.tokens:
            if token.ttype is Keyword and token.value.upper() == "WHERE":
                return True
        return False

    def _add_limit_clause(self, query: str, limit: int) -> str:
        """
        Add LIMIT clause to query if not present.

        Args:
            query: Original SQL query
            limit: Maximum number of rows

        Returns:
            Modified query with LIMIT clause
        """
        query_upper = query.upper().strip()

        # Check if LIMIT already exists
        if "LIMIT" in query_upper:
            return query

        # Check if it's a SELECT query
        parsed = sqlparse.parse(query)
        if not parsed:
            return query

        statement = parsed[0]
        statement_type = self._get_statement_type(statement)

        if statement_type != "SELECT":
            return query

        # Add LIMIT clause
        query = query.rstrip(";").strip()
        return f"{query} LIMIT {limit}"
