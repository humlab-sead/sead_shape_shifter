"""API endpoints for entity management within configurations."""

from typing import Any

from fastapi import APIRouter, HTTPException, status
from loguru import logger
from pydantic import BaseModel, Field

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
async def list_entities(config_name: str) -> list[EntityResponse]:
    """
    List all entities in configuration.

    Args:
        config_name: Configuration name

    Returns:
        List of entities with their data
    """
    config_service: ConfigurationService = get_config_service()
    try:
        config: Configuration = config_service.load_configuration(config_name)
        entities = [EntityResponse(name=name, entity_data=data) for name, data in config.entities.items()]
        logger.debug(f"Listed {len(entities)} entities in '{config_name}'")
        return entities
    except ConfigurationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to list entities in '{config_name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list entities: {str(e)}",
        ) from e


@router.get("/configurations/{config_name}/entities/{entity_name}", response_model=EntityResponse)
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
    try:
        entity_data: dict[str, Any] = config_service.get_entity_by_name(config_name, entity_name)
        logger.info(f"Retrieved entity '{entity_name}' from '{config_name}'")
        return EntityResponse(name=entity_name, entity_data=entity_data)
    except (ConfigurationNotFoundError, EntityNotFoundError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to get entity '{entity_name}' from '{config_name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get entity: {str(e)}",
        ) from e


@router.post(
    "/configurations/{config_name}/entities",
    response_model=EntityResponse,
    status_code=status.HTTP_201_CREATED,
)
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
    try:
        config_service.add_entity_by_name(config_name, request.name, request.entity_data)
        logger.info(f"Added entity '{request.name}' to '{config_name}'")
        return EntityResponse(name=request.name, entity_data=request.entity_data)
    except ConfigurationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except EntityAlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to add entity '{request.name}' to '{config_name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add entity: {str(e)}",
        ) from e


@router.put("/configurations/{config_name}/entities/{entity_name}", response_model=EntityResponse)
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
    try:
        config_service.update_entity_by_name(config_name, entity_name, request.entity_data)
        logger.info(f"Updated entity '{entity_name}' in '{config_name}'")
        return EntityResponse(name=entity_name, entity_data=request.entity_data)
    except (ConfigurationNotFoundError, EntityNotFoundError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to update entity '{entity_name}' in '{config_name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update entity: {str(e)}",
        ) from e


@router.delete(
    "/configurations/{config_name}/entities/{entity_name}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_entity(config_name: str, entity_name: str) -> None:
    """
    Delete entity from configuration.

    Args:
        config_name: Configuration name
        entity_name: Entity name
    """
    config_service: ConfigurationService = get_config_service()
    try:
        config_service.delete_entity_by_name(config_name, entity_name)
        logger.info(f"Deleted entity '{entity_name}' from '{config_name}'")
    except (ConfigurationNotFoundError, EntityNotFoundError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to delete entity '{entity_name}' from '{config_name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete entity: {str(e)}",
        ) from e
