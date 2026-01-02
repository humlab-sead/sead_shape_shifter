"""API endpoints for entity data preview."""

from typing import Optional

from fastapi import APIRouter, Depends, Path, Query
from loguru import logger

from backend.app.models.join_test import JoinTestResult
from backend.app.models.shapeshift import PreviewResult
from backend.app.services.project_service import ProjectService
from backend.app.services.shapeshift_service import ShapeShiftService
from backend.app.services.validate_fk_service import ValidateForeignKeyService
from backend.app.utils.error_handlers import handle_endpoint_errors
from backend.app.utils.exceptions import BadRequestError, NotFoundError

router = APIRouter()


def get_project_service() -> ProjectService:
    """Dependency to get config service instance."""
    return ProjectService()


def get_preview_service(
    project_service: ProjectService = Depends(get_project_service),
) -> ShapeShiftService:
    """Dependency to get preview service instance."""
    return ShapeShiftService(project_service=project_service)


def get_validate_fk_service(
    preview_service: ShapeShiftService = Depends(get_preview_service),
) -> ValidateForeignKeyService:
    """Dependency to get validate foreign key service instance."""
    return ValidateForeignKeyService(preview_service=preview_service)


@router.post(
    "/projects/{project_name}/entities/{entity_name}/preview",
    response_model=PreviewResult,
    summary="Preview entity data",
    description="Get a preview of entity data with all transformations applied",
    responses={
        200: {"description": "Preview data retrieved successfully"},
        404: {"description": "Project or entity not found"},
        500: {"description": "Preview generation failed"},
    },
)
@handle_endpoint_errors
async def preview_entity(
    project_name: str = Path(..., description="Name of the configuration"),
    entity_name: str = Path(..., description="Name of the entity to preview"),
    limit: Optional[int] = Query(None, ge=1, le=10000, description="Maximum number of rows to return. None for all rows."),
    preview_service: ShapeShiftService = Depends(get_preview_service),
) -> PreviewResult:
    """
    Preview entity data with transformations.

    This endpoint:
    - Loads the entity and its dependencies
    - Applies all configured transformations (filters, unnest, foreign keys)
    - Returns a limited number of rows with metadata
    - Caches results for 5 minutes

    Set limit=null to retrieve all rows (use with caution for large datasets).
    If no limit is specified in the request, defaults to 50 rows.
    """
    try:
        result = await preview_service.preview_entity(project_name, entity_name, limit)
        return result
    except ValueError as e:
        logger.warning(f"Preview request failed: {e}")
        raise NotFoundError(str(e)) from e


@router.post(
    "/projects/{project_name}/entities/{entity_name}/sample",
    response_model=PreviewResult,
    summary="Get entity data sample",
    description="Get a larger sample of entity data for validation or testing",
    responses={
        200: {"description": "Sample data retrieved successfully"},
        404: {"description": "Project or entity not found"},
        500: {"description": "Sample generation failed"},
    },
)
@handle_endpoint_errors
async def get_entity_sample(
    project_name: str = Path(..., description="Name of the configuration"),
    entity_name: str = Path(..., description="Name of the entity"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of rows (default 100)"),
    preview_service: ShapeShiftService = Depends(get_preview_service),
) -> PreviewResult:
    """
    Get a larger sample of entity data.

    Useful for:
    - Data validation (checking foreign key integrity)
    - Testing transformations
    - Statistical analysis
    """
    try:
        result = await preview_service.get_entity_sample(project_name, entity_name, limit)
        return result
    except ValueError as e:
        logger.warning(f"Sample request failed: {e}")
        raise NotFoundError(str(e)) from e


@router.delete(
    "/projects/{project_name}/preview-cache",
    summary="Invalidate preview cache",
    description="Clear cached preview data for a configuration",
    responses={
        200: {"description": "Cache invalidated successfully"},
    },
)
@handle_endpoint_errors
async def invalidate_preview_cache(
    project_name: str = Path(..., description="Name of the configuration"),
    entity_name: Optional[str] = Query(None, description="Optional entity name to clear specific cache"),
    preview_service: ShapeShiftService = Depends(get_preview_service),
) -> dict:
    """
    Invalidate preview cache.

    Use this after:
    - Modifying entity configuration
    - Changing data source data
    - Updating transformations
    """
    preview_service.invalidate_cache(project_name, entity_name)
    message = f"Cache cleared for {project_name}"
    if entity_name:
        message += f":{entity_name}"
    return {"message": message, "project_name": project_name, "entity_name": entity_name}


@router.post(
    "/projects/{project_name}/entities/{entity_name}/foreign-keys/{fk_index}/test",
    response_model=JoinTestResult,
    summary="Test foreign key join",
    description="Test a foreign key relationship to validate the join",
    responses={
        200: {"description": "Join test completed successfully"},
        404: {"description": "Project, entity, or foreign key not found"},
        400: {"description": "Invalid request parameters"},
    },
)
@handle_endpoint_errors
async def test_foreign_key_join(
    project_name: str = Path(..., description="Name of the configuration"),
    entity_name: str = Path(..., description="Name of the entity with the foreign key"),
    fk_index: int = Path(..., description="Index of the foreign key to test", ge=0),
    sample_size: int = Query(100, description="Number of rows to test", ge=10, le=1000),
    validate_fk_service: ValidateForeignKeyService = Depends(get_validate_fk_service),
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
        result = await validate_fk_service.test_foreign_key(
            project_name=project_name, entity_name=entity_name, foreign_key_index=fk_index, sample_size=sample_size
        )
        return result
    except ValueError as e:
        logger.error(f"Join test validation error: {e}")
        raise BadRequestError(str(e)) from e
