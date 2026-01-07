"""API endpoints for entity management within configurations."""

from typing import Any

from fastapi import APIRouter, status
from loguru import logger
from pydantic import BaseModel, Field

from backend.app.models.project import Project
from backend.app.services.project_service import (
    ProjectService,
    get_project_service,
)
from backend.app.utils.error_handlers import handle_endpoint_errors

router = APIRouter()

# pylint: disable=no-member


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
    entities = [EntityResponse(name=name, entity_data=data) for name, data in config.entities.items()]
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
    return EntityResponse(name=entity_name, entity_data=entity_data)


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
    return EntityResponse(name=request.name, entity_data=request.entity_data)


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
    return EntityResponse(name=entity_name, entity_data=request.entity_data)


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
