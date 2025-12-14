"""API endpoints for entity data preview."""

from typing import Optional

from app.models.join_test import JoinTestResult
from app.models.preview import PreviewResult
from app.services.config_service import ConfigurationService
from app.services.preview_service import PreviewService
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from loguru import logger

router = APIRouter()


def get_config_service() -> ConfigurationService:
    """Dependency to get config service instance."""
    return ConfigurationService()


def get_preview_service(
    config_service: ConfigurationService = Depends(get_config_service),
) -> PreviewService:
    """Dependency to get preview service instance."""
    return PreviewService(config_service)


@router.post(
    "/configurations/{config_name}/entities/{entity_name}/preview",
    response_model=PreviewResult,
    summary="Preview entity data",
    description="Get a preview of entity data with all transformations applied",
    responses={
        200: {"description": "Preview data retrieved successfully"},
        404: {"description": "Configuration or entity not found"},
        500: {"description": "Preview generation failed"},
    },
)
async def preview_entity(
    config_name: str = Path(..., description="Name of the configuration"),
    entity_name: str = Path(..., description="Name of the entity to preview"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of rows to return"),
    preview_service: PreviewService = Depends(get_preview_service),
) -> PreviewResult:
    """
    Preview entity data with transformations.

    This endpoint:
    - Loads the entity and its dependencies
    - Applies all configured transformations (filters, unnest, foreign keys)
    - Returns a limited number of rows with metadata
    - Caches results for 5 minutes
    """
    try:
        result = await preview_service.preview_entity(config_name, entity_name, limit)
        return result
    except ValueError as e:
        logger.warning(f"Preview request failed: {e}")
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Preview generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Preview generation failed: {str(e)}") from e


@router.post(
    "/configurations/{config_name}/entities/{entity_name}/sample",
    response_model=PreviewResult,
    summary="Get entity data sample",
    description="Get a larger sample of entity data for validation or testing",
    responses={
        200: {"description": "Sample data retrieved successfully"},
        404: {"description": "Configuration or entity not found"},
        500: {"description": "Sample generation failed"},
    },
)
async def get_entity_sample(
    config_name: str = Path(..., description="Name of the configuration"),
    entity_name: str = Path(..., description="Name of the entity"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of rows (default 100)"),
    preview_service: PreviewService = Depends(get_preview_service),
) -> PreviewResult:
    """
    Get a larger sample of entity data.

    Useful for:
    - Data validation (checking foreign key integrity)
    - Testing transformations
    - Statistical analysis
    """
    try:
        result = await preview_service.get_entity_sample(config_name, entity_name, limit)
        return result
    except ValueError as e:
        logger.warning(f"Sample request failed: {e}")
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Sample generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Sample generation failed: {str(e)}") from e


@router.delete(
    "/configurations/{config_name}/preview-cache",
    summary="Invalidate preview cache",
    description="Clear cached preview data for a configuration",
    responses={
        200: {"description": "Cache invalidated successfully"},
    },
)
async def invalidate_preview_cache(
    config_name: str = Path(..., description="Name of the configuration"),
    entity_name: Optional[str] = Query(None, description="Optional entity name to clear specific cache"),
    preview_service: PreviewService = Depends(get_preview_service),
) -> dict:
    """
    Invalidate preview cache.

    Use this after:
    - Modifying entity configuration
    - Changing data source data
    - Updating transformations
    """
    try:
        preview_service.invalidate_cache(config_name, entity_name)
        message = f"Cache cleared for {config_name}"
        if entity_name:
            message += f":{entity_name}"
        return {"message": message, "config_name": config_name, "entity_name": entity_name}
    except Exception as e:
        logger.error(f"Cache invalidation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Cache invalidation failed: {str(e)}") from e


@router.post(
    "/configurations/{config_name}/entities/{entity_name}/foreign-keys/{fk_index}/test",
    response_model=JoinTestResult,
    summary="Test foreign key join",
    description="Test a foreign key relationship to validate the join",
    responses={
        200: {"description": "Join test completed successfully"},
        404: {"description": "Configuration, entity, or foreign key not found"},
        400: {"description": "Invalid request parameters"},
    },
)
async def test_foreign_key_join(
    config_name: str = Path(..., description="Name of the configuration"),
    entity_name: str = Path(..., description="Name of the entity with the foreign key"),
    fk_index: int = Path(..., description="Index of the foreign key to test", ge=0),
    sample_size: int = Query(100, description="Number of rows to test", ge=10, le=1000),
    preview_service: PreviewService = Depends(get_preview_service),
) -> JoinTestResult:
    """
    Test a foreign key join relationship.

    Returns statistics about:
    - Match percentage
    - Unmatched rows
    - Cardinality validation
    - Null key counts
    - Duplicate matches

    Use this to:
    - Validate foreign key configurations
    - Identify data quality issues
    - Verify cardinality constraints
    - Preview join behavior
    """
    try:
        result = await preview_service.test_foreign_key(
            config_name=config_name, entity_name=entity_name, foreign_key_index=fk_index, sample_size=sample_size
        )
        return result
    except ValueError as e:
        logger.error(f"Join test validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Join test failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Join test failed: {str(e)}") from e
