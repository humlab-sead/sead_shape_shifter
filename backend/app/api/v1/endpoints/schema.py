"""
Schema Introspection API Endpoints

Provides REST API for database schema inspection, table browsing, and data preview.
"""

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger

from backend.app.utils.error_handlers import handle_endpoint_errors
from backend.app.utils.exceptions import BadRequestError, NotFoundError

from backend.app.api.dependencies import get_schema_service
from backend.app.models.data_source import TableMetadata, TableSchema
from backend.app.models.entity_import import EntityImportRequest, EntityImportResult
from backend.app.services.schema_service import SchemaIntrospectionService, SchemaServiceError
from backend.app.services.type_mapping_service import TypeMappingService

router = APIRouter(prefix="/data-sources", tags=["schema"])


@router.get("/{name}/tables", response_model=list[TableMetadata], summary="List tables in data source")
@handle_endpoint_errors
async def list_tables(
    name: str,
    schema: Optional[str] = Query(None, description="Schema name (PostgreSQL only)"),
    service: SchemaIntrospectionService = Depends(get_schema_service),
) -> list[TableMetadata]:
    """
    List all tables in a data source.

    **Path Parameters**:
    - `name`: Data source identifier

    **Query Parameters**:
    - `schema`: Optional schema name (PostgreSQL only, defaults to 'public')

    **Supported Drivers**:
    - PostgreSQL: Queries information_schema.tables
    - MS Access: Queries INFORMATION_SCHEMA or MSysObjects
    - SQLite: Queries sqlite_master

    **Returns**: List of table metadata with name, schema (if applicable), and comment

    **Caching**: Results cached for 5 minutes

    **Errors**:
    - 404: Data source not found
    - 400: Schema introspection not supported for this driver
    - 500: Database query failed
    """
    try:
        logger.info(f"Listing tables for data source: {name} (schema: {schema or 'default'})")
        tables = await service.get_tables(name, schema)
        logger.info(f"Found {len(tables)} tables in {name}")
        return tables
    except SchemaServiceError as e:
        if "not found" in str(e).lower():
            raise NotFoundError(str(e)) from e
        if "not supported" in str(e).lower():
            raise BadRequestError(str(e)) from e
        raise


@router.get("/{name}/tables/{table_name}/schema", response_model=TableSchema, summary="Get table schema")
@handle_endpoint_errors
async def get_table_schema(
    name: str,
    table_name: str,
    schema: Optional[str] = Query(None, description="Schema name (PostgreSQL only)"),
    service: SchemaIntrospectionService = Depends(get_schema_service),
) -> TableSchema:
    """
    Get detailed schema information for a specific table.

    **Path Parameters**:
    - `name`: Data source identifier
    - `table_name`: Name of the table

    **Query Parameters**:
    - `schema`: Optional schema name (PostgreSQL only, defaults to 'public')

    **Returns**:
    - `table_name`: Table name
    - `columns`: List of column metadata (name, type, nullable, default, is_primary_key)
    - `primary_keys`: List of primary key column names
    - `indexes`: List of index names (if available)
    - `row_count`: Approximate number of rows

    **Column Information**:
    - `name`: Column name
    - `data_type`: SQL data type
    - `nullable`: Whether column accepts NULL values
    - `default`: Default value expression
    - `is_primary_key`: Whether column is part of primary key
    - `max_length`: Maximum character length (for string types)

    **Caching**: Results cached for 5 minutes

    **Errors**:
    - 404: Data source or table not found
    - 400: Schema introspection not supported
    - 500: Database query failed
    """
    try:
        logger.info(f"Getting schema for table {table_name} in {name}")
        table_schema = await service.get_table_schema(name, table_name, schema)
        logger.info(f"Retrieved schema for {table_name} with {len(table_schema.columns)} columns")
        return table_schema
    except SchemaServiceError as e:
        if "not found" in str(e).lower():
            raise NotFoundError(str(e)) from e
        if "not supported" in str(e).lower():
            raise BadRequestError(str(e)) from e
        raise


@router.get("/{name}/tables/{table_name}/preview", summary="Preview table data")
@handle_endpoint_errors
async def preview_table_data(
    name: str,
    table_name: str,
    schema: Optional[str] = Query(None, description="Schema name (PostgreSQL only)"),
    limit: int = Query(50, ge=1, le=100, description="Maximum rows to return (1-100)"),
    offset: int = Query(0, ge=0, description="Number of rows to skip"),
    service: SchemaIntrospectionService = Depends(get_schema_service),
) -> dict[str, Any]:
    """
    Get a preview of table data.

    **Path Parameters**:
    - `name`: Data source identifier
    - `table_name`: Name of the table

    **Query Parameters**:
    - `schema`: Optional schema name (PostgreSQL only)
    - `limit`: Maximum rows to return (1-100, default 50)
    - `offset`: Number of rows to skip (default 0)

    **Returns**:
    ```json
    {
      "columns": ["col1", "col2", "col3"],
      "rows": [
        {"col1": "value1", "col2": 123, "col3": true},
        {"col1": "value2", "col2": 456, "col3": false}
      ],
      "total_rows": 1000,
      "limit": 50,
      "offset": 0
    }
    ```

    **Query Execution**:
    - Uses `SELECT * FROM table LIMIT x OFFSET y`
    - 30-second timeout protection
    - Results not cached (live data)

    **Pagination**:
    - Use `offset` to skip rows
    - Use `limit` to control page size
    - `total_rows` shows approximate total count

    **Errors**:
    - 404: Data source or table not found
    - 400: Invalid parameters or unsupported driver
    - 500: Query execution failed or timeout
    """
    try:
        logger.info(f"Previewing table {table_name} in {name} (limit={limit}, offset={offset})")
        preview = await service.preview_table_data(name, table_name, schema, limit, offset)
        logger.info(f"Retrieved {len(preview['rows'])} rows from {table_name}")
        return preview
    except SchemaServiceError as e:
        if "not found" in str(e).lower():
            raise NotFoundError(str(e)) from e
        if "not supported" in str(e).lower() or "timed out" in str(e).lower():
            raise BadRequestError(str(e)) from e
        raise


@router.get("/{name}/tables/{table_name}/type-mappings", response_model=dict[str, dict[str, Any]], summary="Get type mapping suggestions")
@handle_endpoint_errors
async def get_type_mappings(
    name: str,
    table_name: str,
    schema: Optional[str] = None,
    service: SchemaIntrospectionService = Depends(get_schema_service),
):
    """
    Get Shape Shifter type suggestions for all columns in a table.

    **Path Parameters**:
    - `name`: Data source identifier
    - `table_name`: Table name

    **Query Parameters**:
    - `schema`: PostgreSQL schema name (defaults to 'public')

    **Returns**: Dictionary mapping column names to type suggestions with:
    - `suggested_type`: Recommended Shape Shifter type
    - `confidence`: Confidence score (0.0-1.0)
    - `reason`: Explanation for suggestion
    - `alternatives`: Alternative type options

    **Example Response**:
    ```json
    {
      "user_id": {
        "sql_type": "integer",
        "suggested_type": "integer",
        "confidence": 1.0,
        "reason": "Standard integer type",
        "alternatives": ["string", "float"]
      },
      "email": {
        "sql_type": "character varying",
        "suggested_type": "string",
        "confidence": 1.0,
        "reason": "Variable length string",
        "alternatives": ["text"]
      }
    }
    ```
    """
    try:

        logger.info(f"Getting type mappings for {table_name} in {name}")

        # Get table schema
        table_schema = await service.get_table_schema(name, table_name, schema)

        # Convert columns to dict format
        columns = [
            {
                "name": col.name,
                "data_type": col.data_type,
                "is_primary_key": col.is_primary_key,
                "max_length": col.max_length,
            }
            for col in table_schema.columns
        ]

        # Get type mappings
        type_service = TypeMappingService()
        mappings = type_service.get_mappings_for_table(columns)

        # Convert to dict for JSON response
        result = {col_name: mapping.model_dump() for col_name, mapping in mappings.items()}

        logger.info(f"Generated {len(result)} type mappings for {table_name}")
        return result

    except SchemaServiceError as e:
        if "not found" in str(e).lower():
            raise NotFoundError(str(e)) from e
        raise


@router.post("/{name}/tables/{table_name}/import", summary="Import entity from table")
@handle_endpoint_errors
async def import_entity_from_table(
    name: str,
    table_name: str,
    request: "EntityImportRequest | None" = None,
    service: SchemaIntrospectionService = Depends(get_schema_service),
):
    """
    Generate entity configuration from a database table.

    **Path Parameters**:
    - `name`: Data source identifier
    - `table_name`: Table name to import

    **Request Body** (optional):
    - `entity_name`: Custom entity name (defaults to table name)
    - `selected_columns`: Specific columns to include (defaults to all)

    **Returns**: Entity configuration with suggestions

    **Features**:
    - Auto-generates SQL query
    - Suggests surrogate_id from primary keys
    - Suggests natural keys from column names
    - Provides column type information
    """

    if request is None:
        request = EntityImportRequest(**{})

    try:
        logger.info(f"Importing entity from table {table_name} in {name}")

        result = await service.import_entity_from_table(
            data_source_name=name, table_name=table_name, entity_name=request.entity_name, selected_columns=request.selected_columns
        )

        return EntityImportResult(**result)

    except SchemaServiceError as e:
        logger.error(f"Error importing entity from {table_name}: {e}")
        if "not found" in str(e).lower():
            raise NotFoundError(str(e)) from e
        raise


@router.post("/{name}/cache/invalidate", status_code=status.HTTP_204_NO_CONTENT, summary="Invalidate schema cache")
@handle_endpoint_errors
async def invalidate_cache(
    name: str,
    service: SchemaIntrospectionService = Depends(get_schema_service),
):
    """
    Invalidate cached schema data for a data source.

    **Path Parameters**:
    - `name`: Data source identifier

    **Use Cases**:
    - After database schema changes
    - After table modifications
    - When cached data is stale

    **Returns**: 204 No Content

    **Note**: Cache automatically expires after 5 minutes
    """
    logger.info(f"Invalidating schema cache for {name}")
    service.invalidate_cache(name)
    logger.info(f"Cache invalidated for {name}")
