"""API endpoints for entity management within configurations."""

from typing import Any

from fastapi import APIRouter, HTTPException, status
from loguru import logger
from pydantic import BaseModel, Field

from backend.app.utils.error_handlers import handle_endpoint_errors

from backend.app.utils.error_handlers import handle_endpoint_errors

from backend.app.models.config import Configuration
from backend.app.services.config_service import (
    ConfigurationNotFoundError,
    ConfigurationService,
    EntityAlreadyExistsError,
    EntityNotFoundError,
    get_config_service,
)

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
@router.get("/configurations/{config_name}/entities", response_model=list[EntityResponse])
@handle_endpoint_errors
async def list_entities(config_name: str) -> list[EntityResponse]:
    """
    List all entities in configuration.

    Args:
        config_name: Configuration name

    Returns:
        List of entities with their data
    """
    config_service: ConfigurationService = get_config_service()
    config: Configuration = config_service.load_configuration(config_name)
    entities = [EntityResponse(name=name, entity_data=data) for name, data in config.entities.items()]
    logger.debug(f"Listed {len(entities)} entities in '{config_name}'")
    return entities


@router.get("/configurations/{config_name}/entities/{entity_name}", response_model=EntityResponse)
@handle_endpoint_errors
async def get_entity(config_name: str, entity_name: str) -> EntityResponse:
    """
    Get specific entity from configuration.

    Args:
        config_name: Configuration name
        entity_name: Entity name

    Returns:
        Entity data
    """
    config_service: ConfigurationService = get_config_service()
    entity_data: dict[str, Any] = config_service.get_entity_by_name(config_name, entity_name)
    logger.info(f"Retrieved entity '{entity_name}' from '{config_name}'")
    return EntityResponse(name=entity_name, entity_data=entity_data)


@router.post(
    "/configurations/{config_name}/entities",
    response_model=EntityResponse,
    status_code=status.HTTP_201_CREATED,
)
@handle_endpoint_errors
async def create_entity(config_name: str, request: EntityCreateRequest) -> EntityResponse:
    """
    Add new entity to configuration.

    Args:
        config_name: Configuration name
        request: Entity creation request

    Returns:
        Created entity data
    """
    config_service: ConfigurationService = get_config_service()
    config_service.add_entity_by_name(config_name, request.name, request.entity_data)
    logger.info(f"Added entity '{request.name}' to '{config_name}'")
    return EntityResponse(name=request.name, entity_data=request.entity_data)


@router.put("/configurations/{config_name}/entities/{entity_name}", response_model=EntityResponse)
@handle_endpoint_errors
async def update_entity(config_name: str, entity_name: str, request: EntityUpdateRequest) -> EntityResponse:
    """
    Update existing entity in configuration.

    Args:
        config_name: Configuration name
        entity_name: Entity name
        request: Entity update request

    Returns:
        Updated entity data
    """
    config_service: ConfigurationService = get_config_service()
    config_service.update_entity_by_name(config_name, entity_name, request.entity_data)
    logger.info(f"Updated entity '{entity_name}' in '{config_name}'")
    return EntityResponse(name=entity_name, entity_data=request.entity_data)


@router.delete(
    "/configurations/{config_name}/entities/{entity_name}",
    status_code=status.HTTP_204_NO_CONTENT,
)
@handle_endpoint_errors
async def delete_entity(config_name: str, entity_name: str) -> None:
    """
    Delete entity from configuration.

    Args:
        config_name: Configuration name
        entity_name: Entity name
    """
    config_service: ConfigurationService = get_config_service()
    config_service.delete_entity_by_name(config_name, entity_name)
    logger.info(f"Deleted entity '{entity_name}' from '{config_name}'")
