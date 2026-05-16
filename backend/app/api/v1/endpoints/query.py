"""\nQuery execution API endpoints.\n"""

from fastapi import APIRouter, Depends, HTTPException

import backend.app.models.data_source as api
from backend.app.api.dependencies import get_data_source_service
from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.models.project import Project
from backend.app.models.query import QueryExecution, QueryIntrospection, QueryResult, QueryValidation
from backend.app.services.data_source_service import DataSourceService
from backend.app.services.project_service import ProjectService, get_project_service
from backend.app.services.query_service import is_internal_data_source, QueryExecutionError, QuerySecurityError, QueryService
from src.model import DataSourceConfig, ShapeShiftProject

router = APIRouter()


def get_query_service() -> QueryService:
    """Dependency to get query service instance."""
    return QueryService()


def _resolve_data_source_config(
    data_source_name: str,
    data_source_service: DataSourceService,
    project_name: str | None = None,
    project_service: ProjectService | None = None,
) -> api.DataSourceConfig | None:
    """Resolve a data source from a project or the global data source directory.

    Returns None for the ``@internal`` virtual data source.
    Raises QueryExecutionError when the named source cannot be found.
    """
    if is_internal_data_source(data_source_name):
        return None

    try:
        if not (project_name and project_service):
            return data_source_service.load_data_source(data_source_name, strict=True)

        api_project: Project = project_service.load_project(project_name)
        core_project: ShapeShiftProject = ProjectMapper.to_core(api_project)

        raw_source = core_project.data_sources.get(data_source_name)
        if raw_source is None:
            raise ValueError(f"Data source '{data_source_name}' not found in project '{project_name}'")

        if isinstance(raw_source, str):
            return data_source_service.load_data_source(raw_source, strict=True)

        core_ds: DataSourceConfig = core_project.get_data_source(data_source_name)
        return api.DataSourceConfig(name=data_source_name, **core_ds.data_source_cfg)
    except Exception as e:
        raise QueryExecutionError(
            message=f"Failed to resolve data source '{data_source_name}': {str(e)}",
            data_source=data_source_name,
        ) from e


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
    data_source_name: str,
    execution: QueryExecution,
    query_service: QueryService = Depends(get_query_service),
    data_source_service: DataSourceService = Depends(get_data_source_service),
) -> QueryResult:
    """
    Execute a SQL query against a data source.

    Args:
        data_source_name: Name of the data source to query
        execution: Query execution parameters
        query_service: Query service instance
        data_source_service: Data source service for config resolution

    Returns:
        QueryResult with query results and metadata

    Raises:
        HTTPException: If query is invalid or execution fails
    """
    try:
        ds_cfg = _resolve_data_source_config(data_source_name, data_source_service)
        if ds_cfg is None:
            raise HTTPException(status_code=400, detail=f"Data source '{data_source_name}' cannot be queried directly")
        result: QueryResult = await query_service.execute_query(
            ds_cfg=ds_cfg, query=execution.query, limit=execution.limit, timeout=execution.timeout
        )
        return result
    except QuerySecurityError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except QueryExecutionError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except HTTPException:
        raise
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


@router.post(
    "/data-sources/{data_source_name}/query/columns",
    response_model=dict,
    summary="Introspect SQL query columns",
    description="""
    Introspect column names from a SQL query without fetching all data.

    Executes the query with LIMIT 0 (or equivalent) to get column metadata only.
    Useful for populating column dropdowns in the UI.

    Returns column names that would be returned by the query.
    """,
    responses={
        200: {
            "description": "Column introspection successful",
            "content": {
                "application/json": {
                    "example": {
                        "columns": ["id", "name", "created_at"],
                    }
                }
            },
        },
        400: {"description": "Invalid query (syntax error or security violation)"},
        404: {"description": "Data source not found"},
        500: {"description": "Query execution failed"},
    },
)
async def introspect_query_columns(
    data_source_name: str,
    introspection: QueryIntrospection,
    project_name: str | None = None,
    query_service: QueryService = Depends(get_query_service),
    data_source_service: DataSourceService = Depends(get_data_source_service),
    project_service: ProjectService = Depends(get_project_service),
) -> dict:
    """
    Introspect column names from a SQL query.

    Args:
        data_source_name: Name of the data source (or key from project's data_sources)
        introspection: Query introspection parameters (only query field is used)
        project_name: Optional project name to resolve data_source_name from project context
        query_service: Query service instance
        data_source_service: Data source service for config resolution
        project_service: Project service instance

    Returns:
        Dictionary with 'columns' key containing list of column names

    Raises:
        HTTPException: If query is invalid or execution fails
    """
    try:
        ds_cfg = _resolve_data_source_config(data_source_name, data_source_service, project_name, project_service)
        columns: list[str] = await query_service.introspect_query_columns(ds_cfg=ds_cfg, query=introspection.query)
        return {"columns": columns}
    except QuerySecurityError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except QueryExecutionError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}") from e
