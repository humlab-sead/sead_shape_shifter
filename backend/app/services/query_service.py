"""
SQL Query execution service for the Shape Shifter Configuration Editor.
"""

import asyncio
import time

import pandas as pd
import sqlparse
from sqlparse.sql import Statement

import backend.app.models.data_source as api
import src.model as core
from backend.app.exceptions import QueryExecutionError, QuerySecurityError
from backend.app.mappers.data_source_mapper import DataSourceMapper
from backend.app.models.query import QueryResult, QueryValidation
from backend.app.utils.sql import extract_select_columns, extract_tables, get_statement_type, has_where_clause, has_wildcard_select
from src.loaders.base_loader import DataLoaders
from src.loaders.sql_loaders import SqlLoader

INTERNAL_DATA_SOURCE = "@internal"

def is_internal_data_source(name: str) -> bool:
    """Check if a data source name refers to the internal virtual data source."""
    return name == INTERNAL_DATA_SOURCE

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
        statement_type: str | None = get_statement_type(statement, self.FORBIDDEN_KEYWORDS)

        if statement_type and statement_type.upper() in self.FORBIDDEN_KEYWORDS:
            errors.append(f"Destructive SQL operation '{statement_type}' is not allowed. " f"Only SELECT queries are permitted.")

        tables: list[str] = extract_tables(query)

        # if not statement_type:
        #     errors.append("Could not determine SQL statement type.")

        # Block non-SELECT statements for now
        if statement_type and statement_type.upper() != "SELECT":
            errors.append(f"Only SELECT queries are allowed. Found '{statement_type}' statement.")

        # Check for multiple statements
        if len(parsed) > 1:
            warnings.append("Query contains multiple statements. Only the first will be executed.")

        # Check for missing WHERE clause on large tables (heuristic warning)
        if statement_type == "SELECT" and not has_where_clause(statement):
            warnings.append("Query has no WHERE clause. This may return a large result set.")

        # For @internal DuckDB queries, wildcard SELECT is not allowed because column
        # names cannot be inferred without executing the query at runtime.
        if data_source_name == INTERNAL_DATA_SOURCE and statement_type == "SELECT" and has_wildcard_select(query):
            errors.append("SELECT * is not allowed for @internal queries — list column names explicitly.")

        is_valid: bool = len(errors) == 0

        return QueryValidation(is_valid=is_valid, errors=errors, warnings=warnings, statement_type=statement_type, tables=tables)

    async def execute_query(self, ds_cfg: api.DataSourceConfig, query: str, limit: int | None = 100, timeout: int = 30) -> QueryResult:
        """
        Execute a SQL query against a data source.

        Args:
            ds_cfg: Resolved data source configuration
            query: SQL query to execute
            limit: Maximum number of rows to return (default 100)
            timeout: Query timeout in seconds (default 30)

        Returns:
            QueryResult with query results

        Raises:
            QuerySecurityError: If query contains destructive operations
            QueryExecutionError: If query execution fails
        """

        validation: QueryValidation = self.validate_query(query, ds_cfg.name)
        if not validation.is_valid:
            raise QuerySecurityError(message="Query contains prohibited operations", query=query, violations=validation.errors)

        timeout = min(timeout, 300)  # Max 5 minutes

        core_config: core.DataSourceConfig = DataSourceMapper.to_core_config(ds_cfg)
        loader_cls: type[SqlLoader] = DataLoaders.get(core_config.driver)

        start_time: float = time.time()

        try:
            loader: SqlLoader = loader_cls(data_source=core_config)

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
                message=f"Query execution failed due to missing configuration: {str(e)}", data_source=ds_cfg.name, query=query
            ) from e
        except asyncio.TimeoutError as e:
            raise QueryExecutionError(
                message=f"Query execution timed out after {timeout} seconds", data_source=ds_cfg.name, query=query
            ) from e
        except Exception as e:
            raise QueryExecutionError(message=f"Query execution failed: {str(e)}", data_source=ds_cfg.name, query=query) from e

    async def introspect_query_columns(self, ds_cfg: api.DataSourceConfig | None, query: str) -> list[str]:
        """
        Introspect column names from a SQL query without fetching data.

        Executes the query with LIMIT 0 to get only column metadata.
        Pass ``ds_cfg=None`` to introspect an ``@internal`` DuckDB query — column names
        are parsed directly from the SQL text without executing.

        Args:
            ds_cfg: Resolved data source configuration, or None for @internal queries.
            query: SQL query to introspect.

        Returns:
            List of column names that would be returned by the query.

        Raises:
            QuerySecurityError: If query contains destructive operations.
            QueryExecutionError: If query execution fails.
        """
        data_source_name: str = INTERNAL_DATA_SOURCE if ds_cfg is None else ds_cfg.name

        validation: QueryValidation = self.validate_query(query, data_source_name)
        if not validation.is_valid:
            raise QuerySecurityError(message="Query contains prohibited operations", query=query, violations=validation.errors)

        # For @internal (DuckDB table store), parse column names directly from the SQL text.
        # The internal store is only available at pipeline runtime, so we cannot execute
        # a LIMIT 0 probe here — sqlparse gives us the column names for free.
        if ds_cfg is None:
            try:
                return extract_select_columns(query)
            except ValueError as exc:
                raise QuerySecurityError(message=str(exc), query=query, violations=[str(exc)]) from exc

        core_config: core.DataSourceConfig = DataSourceMapper.to_core_config(ds_cfg)
        loader_cls: type[SqlLoader] = DataLoaders.get(core_config.driver)
        loader: SqlLoader = loader_cls(data_source=core_config)

        try:
            limited_query = loader.inject_limit(query, 0)
            df: pd.DataFrame = await asyncio.wait_for(loader.read_sql(limited_query), timeout=10)
            return df.columns.tolist()

        except asyncio.TimeoutError as e:
            raise QueryExecutionError(
                message="Column introspection timed out after 10 seconds", data_source=ds_cfg.name, query=query
            ) from e
        except Exception as e:
            raise QueryExecutionError(message=f"Column introspection failed: {str(e)}", data_source=ds_cfg.name, query=query) from e
