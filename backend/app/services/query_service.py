"""
SQL Query execution service for the Shape Shifter Configuration Editor.
"""

import asyncio
import time
from typing import Optional

import pandas as pd
import sqlparse
from sqlparse.sql import Identifier, Statement
from sqlparse.tokens import DDL, DML, Keyword

import backend.app.models.data_source as api
import src.model as core
from backend.app.exceptions import QueryExecutionError, QuerySecurityError
from backend.app.mappers.data_source_mapper import DataSourceMapper
from backend.app.models.query import QueryResult, QueryValidation
from backend.app.services.data_source_service import DataSourceService
from src.loaders.base_loader import DataLoaders
from src.loaders.sql_loaders import SqlLoader


class QueryService:
    """Service for executing and validating SQL queries."""

    FORBIDDEN_KEYWORDS: set[str] = {
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "CREATE",
        "ALTER",
        "TRUNCATE",
        "REPLACE",
        "MERGE",
        "GRANT",
        "REVOKE",
    }

    def __init__(self, data_source_service: DataSourceService):
        """
        Initialize query service.

        Args:
            data_source_service: Service for managing data source connections
        """
        self.data_source_service: DataSourceService = data_source_service

    def validate_query(self, query: str, data_source_name: str | None = None) -> QueryValidation:  #  pylint: disable=unused-argument
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

        try:
            parsed = sqlparse.parse(query)
            if not parsed:
                return QueryValidation(is_valid=False, errors=["Empty or invalid SQL query"], warnings=[], statement_type=None)
        except Exception as e:  # pylint: disable=broad-except
            return QueryValidation(is_valid=False, errors=[f"SQL syntax error: {str(e)}"], warnings=[], statement_type=None)

        statement: Statement = parsed[0]
        statement_type: str | None = self._get_statement_type(statement)

        if statement_type and statement_type.upper() in self.FORBIDDEN_KEYWORDS:
            errors.append(f"Destructive SQL operation '{statement_type}' is not allowed. " f"Only SELECT queries are permitted.")

        tables: list[str] = self._extract_table_names(statement)

        # if not statement_type:
        #     errors.append("Could not determine SQL statement type.")

        # Block non-SELECT statements for now
        if statement_type and statement_type.upper() != "SELECT":
            errors.append(f"Only SELECT queries are allowed. Found '{statement_type}' statement.")

        # Check for multiple statements
        if len(parsed) > 1:
            warnings.append("Query contains multiple statements. Only the first will be executed.")

        # Check for missing WHERE clause on large tables (heuristic warning)
        if statement_type == "SELECT" and not self._has_where_clause(statement):
            warnings.append("Query has no WHERE clause. This may return a large result set.")

        is_valid: bool = len(errors) == 0

        return QueryValidation(is_valid=is_valid, errors=errors, warnings=warnings, statement_type=statement_type, tables=tables)

    async def execute_query(self, data_source_name: str, query: str, limit: int | None = 100, timeout: int = 30) -> QueryResult:
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

        validation: QueryValidation = self.validate_query(query, data_source_name)
        if not validation.is_valid:
            raise QuerySecurityError(message="Query contains prohibited operations", query=query, violations=validation.errors)

        timeout = min(timeout, 300)  # Max 5 minutes

        ds_cfg: api.DataSourceConfig | None = self.data_source_service.load_data_source(data_source_name)

        if ds_cfg is None:
            raise QueryExecutionError(message=f"Data source '{data_source_name}' not found", data_source=data_source_name)

        core_config: core.DataSourceConfig = DataSourceMapper.to_core_config(ds_cfg)
        loader_cls: type[SqlLoader] = DataLoaders.get(core_config.driver)
        loader: SqlLoader = loader_cls(data_source=core_config)

        start_time: float = time.time()

        try:

            if limit is not None:
                query = loader.inject_limit(query, limit)

            df: pd.DataFrame = await asyncio.wait_for(loader.read_sql(query), timeout=timeout)

            execution_time_ms: int = max(1, int((time.time() - start_time) * 1000))

            is_truncated: bool = limit is not None and len(df) >= limit
            rows: list[dict] = df.to_dict("records")
            columns: list[str] = df.columns.tolist()

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
        except KeyError as e:
            raise QueryExecutionError(
                message=f"Query execution failed due to missing configuration: {str(e)}", data_source=data_source_name, query=query
            ) from e
        except asyncio.TimeoutError as e:
            raise QueryExecutionError(
                message=f"Query execution timed out after {timeout} seconds", data_source=data_source_name, query=query
            ) from e
        except Exception as e:
            raise QueryExecutionError(message=f"Query execution failed: {str(e)}", data_source=data_source_name, query=query) from e

    async def introspect_query_columns(
        self, data_source_name: str, query: str, project_name: str | None = None, project_service=None
    ) -> list[str]:
        """
        Introspect column names from a SQL query without fetching data.

        Executes the query with LIMIT 0 to get only column metadata.

        Args:
            data_source_name: Name of the data source (or key from project's data_sources)
            query: SQL query to introspect
            project_name: Optional project name to resolve data source from project context
            project_service: Optional project service for resolving data sources from projects

        Returns:
            List of column names that would be returned by the query

        Raises:
            QuerySecurityError: If query contains destructive operations
            QueryExecutionError: If query execution fails
        """
        # Validate query for safety
        validation: QueryValidation = self.validate_query(query, data_source_name)
        if not validation.is_valid:
            raise QuerySecurityError(message="Query contains prohibited operations", query=query, violations=validation.errors)

        # Resolve data source configuration
        ds_cfg: api.DataSourceConfig | None = None
        
        if project_name and project_service:
            # Resolve from project context
            from backend.app.mappers.project_mapper import ProjectMapper
            
            api_project = project_service.load_project(project_name)
            if not api_project:
                raise QueryExecutionError(message=f"Project '{project_name}' not found", data_source=data_source_name)
            
            # Check if data source key exists in project's data_sources
            if data_source_name not in api_project.data_sources:
                raise QueryExecutionError(
                    message=f"Data source '{data_source_name}' not found in project '{project_name}'",
                    data_source=data_source_name
                )
            
            # Convert to core to resolve @include directives
            core_project = ProjectMapper.to_core(api_project)
            
            # Get the resolved data source value from core project
            # In core, data_sources are under cfg['options']['data_sources']
            ds_value = core_project.cfg.get("options", {}).get("data_sources", {}).get(data_source_name)
            
            if ds_value is None:
                raise QueryExecutionError(
                    message=f"Data source '{data_source_name}' not found in resolved project '{project_name}'",
                    data_source=data_source_name
                )
            
            # ds_value is already resolved (no @include directives) thanks to ProjectMapper.to_core()
            if isinstance(ds_value, dict):
                # Inline data source configuration
                ds_cfg = api.DataSourceConfig(name=data_source_name, **ds_value)
            elif isinstance(ds_value, str):
                # Should be a filename - load from global data sources
                ds_cfg = self.data_source_service.load_data_source(ds_value)
            else:
                raise QueryExecutionError(
                    message=f"Invalid data source configuration for '{data_source_name}' in project '{project_name}'",
                    data_source=data_source_name
                )
        else:
            # Load from global data sources directory (backward compatibility)
            ds_cfg = self.data_source_service.load_data_source(data_source_name)
        
        if ds_cfg is None:
            raise QueryExecutionError(message=f"Data source '{data_source_name}' not found", data_source=data_source_name)

        # Convert to core config and get loader
        core_config: core.DataSourceConfig = DataSourceMapper.to_core_config(ds_cfg)
        loader_cls: type[SqlLoader] = DataLoaders.get(core_config.driver)
        loader: SqlLoader = loader_cls(data_source=core_config)

        try:
            # Execute query with LIMIT 0 to get only column structure
            limited_query = loader.inject_limit(query, 0)
            df: pd.DataFrame = await asyncio.wait_for(loader.read_sql(limited_query), timeout=10)
            
            # Return column names
            columns: list[str] = df.columns.tolist()
            return columns

        except asyncio.TimeoutError as e:
            raise QueryExecutionError(
                message=f"Column introspection timed out after 10 seconds", data_source=data_source_name, query=query
            ) from e
        except Exception as e:
            raise QueryExecutionError(message=f"Column introspection failed: {str(e)}", data_source=data_source_name, query=query) from e

    def _get_statement_type(self, statement: Statement) -> Optional[str]:
        """Extract the statement type (SELECT, INSERT, etc.) from parsed SQL."""
        for token in statement.tokens:
            if token.ttype is DML:
                return token.value.upper()
            if token.ttype is DDL:
                return token.value.upper()
            if token.ttype is Keyword and token.value.upper() in self.FORBIDDEN_KEYWORDS:
                return token.value.upper()
        return None

    def _extract_table_names(self, statement: Statement) -> list[str]:
        """Extract table names from a SQL statement."""
        tables: list[str] = []
        from_seen = False

        def extract_name(identifier: Identifier | str) -> str:
            """Extract table name from identifier, handling schema.table format."""
            name: str = identifier.get_real_name() if isinstance(identifier, Identifier) else str(identifier).strip()
            name = name.strip('`"[]')
            if "." in name:
                name = name.split(".")[-1]
            return name

        for token in statement.tokens:

            if token.is_whitespace:
                continue

            if token.ttype is Keyword and token.value.upper() in ("FROM", "JOIN"):
                from_seen = True
                continue

            if not from_seen:
                continue

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
        return any(t.ttype is Keyword and t.value.upper() == "WHERE" for t in statement.flatten())
