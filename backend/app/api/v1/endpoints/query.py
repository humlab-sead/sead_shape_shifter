"""
Query execution API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException

from backend.app.api.dependencies import get_data_source_service
from backend.app.models.query import QueryExecution, QueryResult, QueryValidation
from backend.app.services.data_source_service import DataSourceService
from backend.app.services.query_service import QueryExecutionError, QuerySecurityError, QueryService

router = APIRouter()


def get_query_service(data_source_service: DataSourceService = Depends(get_data_source_service)) -> QueryService:
    """Dependency to get query service instance."""
    return QueryService(data_source_service)


@router.post(
    "/data-sources/{data_source_name}/query/execute",
    response_model=QueryResult,
    summary="Execute SQL query",
    description="""
    Execute a SQL query against a data source.

    Only SELECT queries are allowed. Destructive operations (INSERT, UPDATE, DELETE,
    DROP, etc.) are blocked for safety.

    Results are automatically limited to prevent excessive memory usage.
    """,
    responses={
        200: {
            "description": "Query executed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "rows": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}],
                        "columns": ["id", "name"],
                        "row_count": 2,
                        "execution_time_ms": 45,
                        "is_truncated": False,
                        "total_rows": 2,
                    }
                }
            },
        },
        400: {"description": "Invalid query (syntax error or security violation)"},
        404: {"description": "Data source not found"},
        500: {"description": "Query execution failed"},
    },
)
async def execute_query(
    data_source_name: str, execution: QueryExecution, query_service: QueryService = Depends(get_query_service)
) -> QueryResult:
    """
    Execute a SQL query against a data source.

    Args:
        data_source_name: Name of the data source to query
        execution: Query execution parameters
        query_service: Query service instance

    Returns:
        QueryResult with query results and metadata

    Raises:
        HTTPException: If query is invalid or execution fails
    """
    try:
        result: QueryResult = await query_service.execute_query(
            data_source_name=data_source_name, query=execution.query, limit=execution.limit, timeout=execution.timeout
        )
        return result
    except QuerySecurityError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except QueryExecutionError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}") from e


@router.post(
    "/data-sources/{data_source_name}/query/validate",
    response_model=QueryValidation,
    summary="Validate SQL query",
    description="""
    Validate a SQL query without executing it.

    Checks for:
    - Syntax errors
    - Security violations (destructive operations)
    - Potential issues (missing WHERE clause, etc.)

    Returns validation result with errors and warnings.
    """,
    responses={
        200: {
            "description": "Validation completed",
            "content": {
                "application/json": {
                    "example": {
                        "is_valid": True,
                        "errors": [],
                        "warnings": ["Query has no WHERE clause. This may return a large result set."],
                        "statement_type": "SELECT",
                        "tables": ["users"],
                    }
                }
            },
        }
    },
)
async def validate_query(
    data_source_name: str, execution: QueryExecution, query_service: QueryService = Depends(get_query_service)
) -> QueryValidation:
    """
    Validate a SQL query without executing it.

    Args:
        data_source_name: Name of the data source (used for dialect-specific validation)
        execution: Query to validate
        query_service: Query service instance

    Returns:
        QueryValidation with validation results
    """
    return query_service.validate_query(execution.query, data_source_name)
