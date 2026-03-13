"""API endpoints for entity management within configurations."""

from typing import Any

from fastapi import APIRouter, Header, HTTPException, Query, status
from loguru import logger
from pydantic import BaseModel, Field

from backend.app.models.project import Project
from backend.app.services.entity_generator_service import (
    EntityGeneratorService,
    get_entity_generator_service,
)
from backend.app.services.entity_values_service import (
    EntityValuesService,
    get_entity_values_service,
)
from backend.app.services.project_service import (
    ProjectService,
    get_project_service,
)
from backend.app.utils.error_handlers import handle_endpoint_errors
from backend.app.utils.fixed_schema import FixedSchema, derive_fixed_schema

router = APIRouter()

# pylint: disable=no-member, redefined-builtin


# Request/Response Models
class EntityCreateRequest(BaseModel):
    """Request to create new entity."""

    name: str = Field(..., description="Entity name")
    entity_data: dict[str, Any] = Field(..., description="Entity configuration data")


class EntityUpdateRequest(BaseModel):
    """Request to update entity."""

    entity_data: dict[str, Any] = Field(..., description="Updated entity configuration data")


class EntityResponse(BaseModel):
    """Response containing entity data."""

    name: str = Field(..., description="Entity name")
    entity_data: dict[str, Any] = Field(..., description="Entity configuration data")
    materialized: dict[str, Any] | None = Field(default=None, description="Materialization metadata (if entity is materialized)")
    fixed_schema: FixedSchema | None = Field(default=None, description="Authoritative fixed-schema metadata for fixed entities")


def _build_entity_response(name: str, entity_data: dict[str, Any]) -> EntityResponse:
    """Build a consistent entity response payload."""
    return EntityResponse(
        name=name,
        entity_data=entity_data,
        materialized=entity_data.get("materialized"),
        fixed_schema=derive_fixed_schema(entity_data),
    )


class GenerateFromTableRequest(BaseModel):
    """Request to generate entity from database table."""

    data_source: str = Field(..., description="Name of the data source")
    table_name: str = Field(..., description="Name of the table in the database")
    entity_name: str | None = Field(None, description="Entity name (defaults to table_name if not provided)")
    schema_name: str | None = Field(
        None, alias="schema", description="Optional schema name (if database supports schemas, e.g. PostgreSQL)"
    )


class EntityValuesResponse(BaseModel):
    """Response containing entity values data."""

    columns: list[str] = Field(..., description="Column names")
    values: list[list[Any]] = Field(..., description="Row data")
    format: str = Field(..., description="Storage format (parquet/csv)")
    row_count: int = Field(..., description="Number of rows")
    etag: str = Field(..., description="Entity tag for optimistic locking (based on file mtime+size)")


class EntityValuesUpdateRequest(BaseModel):
    """Request to update entity values."""

    columns: list[str] = Field(..., description="Column names")
    values: list[list[Any]] = Field(..., description="Row data")
    format: str | None = Field(None, description="Preferred storage format (parquet/csv, defaults to existing)")


# Endpoints
@router.get("/projects/{project_name}/entities", response_model=list[EntityResponse])
@handle_endpoint_errors
async def list_entities(project_name: str) -> list[EntityResponse]:
    """
    List all entities in configuration.

    Args:
        project_name: Project name

    Returns:
        List of entities with their data
    """
    project_service: ProjectService = get_project_service()
    config: Project = project_service.load_project(project_name)
    entities = [_build_entity_response(name, data) for name, data in config.entities.items()]
    logger.debug(f"Listed {len(entities)} entities in '{project_name}'")
    return entities


@router.get("/projects/{project_name}/entities/{entity_name}", response_model=EntityResponse)
@handle_endpoint_errors
async def get_entity(project_name: str, entity_name: str) -> EntityResponse:
    """
    Get specific entity from configuration.

    Args:
        project_name: Project name
        entity_name: Entity name

    Returns:
        Entity data
    """
    project_service: ProjectService = get_project_service()
    entity_data: dict[str, Any] = project_service.get_entity_by_name(project_name, entity_name)
    logger.info(f"Retrieved entity '{entity_name}' from '{project_name}'")
    return _build_entity_response(entity_name, entity_data)


@router.post(
    "/projects/{project_name}/entities",
    response_model=EntityResponse,
    status_code=status.HTTP_201_CREATED,
)
@handle_endpoint_errors
async def create_entity(project_name: str, request: EntityCreateRequest) -> EntityResponse:
    """
    Add new entity to configuration.

    Args:
        project_name: Project name
        request: Entity creation request

    Returns:
        Created entity data
    """
    project_service: ProjectService = get_project_service()
    project_service.add_entity_by_name(project_name, request.name, request.entity_data)
    logger.info(f"Added entity '{request.name}' to '{project_name}'")
    return _build_entity_response(request.name, request.entity_data)


@router.put("/projects/{project_name}/entities/{entity_name}", response_model=EntityResponse)
@handle_endpoint_errors
async def update_entity(project_name: str, entity_name: str, request: EntityUpdateRequest) -> EntityResponse:
    """
    Update existing entity in configuration.

    Args:
        project_name: Project name
        entity_name: Entity name
        request: Entity update request

    Returns:
        Updated entity data
    """
    project_service: ProjectService = get_project_service()
    project_service.update_entity_by_name(project_name, entity_name, request.entity_data)
    logger.info(f"Updated entity '{entity_name}' in '{project_name}'")
    return _build_entity_response(entity_name, request.entity_data)


@router.delete(
    "/projects/{project_name}/entities/{entity_name}",
    status_code=status.HTTP_204_NO_CONTENT,
)
@handle_endpoint_errors
async def delete_entity(project_name: str, entity_name: str) -> None:
    """
    Delete entity from configuration.

    Args:
        project_name: Project name
        entity_name: Entity name
    """
    project_service: ProjectService = get_project_service()
    project_service.delete_entity_by_name(project_name, entity_name)
    logger.info(f"Deleted entity '{entity_name}' from '{project_name}'")


@router.post(
    "/projects/{project_name}/entities/generate-from-table",
    response_model=EntityResponse,
    status_code=status.HTTP_201_CREATED,
)
@handle_endpoint_errors
async def generate_entity_from_table(project_name: str, request: GenerateFromTableRequest) -> EntityResponse:
    """
    Generate a new entity configuration from a database table.

    Automatically extracts table schema, primary keys, and generates entity configuration.

    Args:
        project_name: Project name
        request: Entity generation request

    Returns:
        Created entity with generated configuration

    Raises:
        ResourceNotFoundError: If project or data source not found
        ResourceConflictError: If entity name already exists
    """
    generator_service: EntityGeneratorService = get_entity_generator_service()
    entity_config = await generator_service.generate_from_table(
        project_name=project_name,
        data_source_key=request.data_source,
        table_name=request.table_name,
        entity_name=request.entity_name,
        schema=request.schema_name,
    )

    entity_name = request.entity_name or request.table_name
    logger.info(f"Generated entity '{entity_name}' from table '{request.table_name}' in '{project_name}'")
    return _build_entity_response(entity_name, entity_config)


@router.get("/projects/{project_name}/entities/{entity_name}/values", response_model=EntityValuesResponse)
@handle_endpoint_errors
async def get_entity_values(
    project_name: str,
    entity_name: str,
    format: str | None = Query(None, description="Preferred format (parquet/csv) for format conversion"),
) -> EntityValuesResponse:
    """
    Get external values for entity with @load: directive.

    This endpoint fetches the actual data from external storage (parquet/csv files)
    for entities that use @load: directives instead of inline values.

    Supports format negotiation via query parameter for on-the-fly conversion.

    Args:
        project_name: Project name
        entity_name: Entity name
        format: Preferred format (parquet/csv) - returns data as if stored in this format

    Returns:
        Entity values data (columns, values, format, row_count, etag)

    Raises:
        HTTPException 422: If entity doesn't have @load: directive
        HTTPException 404: If values file not found
    """

    values_service: EntityValuesService = get_entity_values_service()
    try:
        result = values_service.get_values(project_name, entity_name)
    except ValueError as e:
        # Entity doesn't have @load: directive - return 422 Unprocessable Entity
        raise HTTPException(status_code=422, detail=str(e)) from e
    except FileNotFoundError as e:
        # Values file not found - return 404
        raise HTTPException(status_code=404, detail=str(e)) from e

    # Handle format negotiation (response always includes actual storage format)
    response_format = format or result.format

    logger.info(f"Retrieved {result.row_count} rows for entity '{entity_name}' from '{project_name}' (format: {response_format})")
    return EntityValuesResponse(
        columns=result.columns,
        values=result.values,
        format=response_format,
        row_count=result.row_count,
        etag=result.etag,
    )


@router.put("/projects/{project_name}/entities/{entity_name}/values", response_model=EntityValuesResponse)
@handle_endpoint_errors
async def update_entity_values(
    project_name: str,
    entity_name: str,
    request: EntityValuesUpdateRequest,
    if_match: str | None = Header(None, description="Etag for optimistic locking"),
) -> EntityValuesResponse:
    """
    Update external values for entity with @load: directive.

    This endpoint writes the data to external storage (parquet/csv files)
    for entities that use @load: directives. The entity configuration
    should be updated separately via PUT /entities/{entity_name}.

    Supports optimistic locking via If-Match header containing etag from GET response.

    Args:
        project_name: Project name
        entity_name: Entity name
        request: Entity values update request
        if_match: Expected etag for optimistic locking (optional)

    Returns:
        Updated entity values confirmation with new etag

    Raises:
        HTTPException 422: If entity doesn't have @load: directive
        HTTPException 409: If etag mismatch (concurrent update detected)
    """

    values_service: EntityValuesService = get_entity_values_service()
    try:
        result = values_service.update_values(
            project_name=project_name,
            entity_name=entity_name,
            columns=request.columns,
            values=request.values,
            format_type=request.format,
            if_match=if_match,
        )
    except ValueError as e:
        # Check if it's an etag mismatch (409) or missing @load: (422)
        if "409 Conflict" in str(e):
            raise HTTPException(status_code=409, detail=str(e)) from e
        raise HTTPException(status_code=422, detail=str(e)) from e

    logger.info(f"Updated {result.row_count} rows for entity '{entity_name}' in '{project_name}'")
    return EntityValuesResponse(
        columns=result.columns,
        values=result.values,
        format=result.format,
        row_count=result.row_count,
        etag=result.etag,
    )
