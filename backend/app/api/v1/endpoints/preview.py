"""API endpoints for entity data preview."""

from typing import Any, NoReturn, Optional

from fastapi import APIRouter, Body, Depends, Path, Query
from loguru import logger

from backend.app.exceptions import ValidationError
from backend.app.models.join_test import JoinTestResult
from backend.app.models.shapeshift import PreviewResult
from backend.app.services.project_service import ProjectService
from backend.app.services.shapeshift_service import ShapeShiftService, get_shapeshift_service
from backend.app.services.validate_fk_service import ValidateForeignKeyService
from backend.app.utils.error_handlers import handle_endpoint_errors
from backend.app.utils.exceptions import BadRequestError, NotFoundError
from src.exceptions import FunctionalDependencyError

router = APIRouter()


def _find_fd_error(error: BaseException) -> FunctionalDependencyError | None:
    """Find wrapped FunctionalDependencyError in exception cause/context chain."""
    seen: set[int] = set()
    current: BaseException | None = error

    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, FunctionalDependencyError):
            return current
        current = current.__cause__ or current.__context__

    return None


def _raise_fd_validation_error(error: FunctionalDependencyError, entity_name: str) -> NoReturn:
    """Raise a structured ValidationError for typed FD failures."""
    tips: list[str] = [
        "This error is related to Functional Dependency (FD) validation during duplicate handling.",
        "If this check is not required, disable 'Check Functional Dependency' for this entity.",
        "Otherwise, review deduplication keys so each keyset maps to consistent values.",
    ]

    raise ValidationError(
        message=error.message,
        error_code="VALIDATION_FAILED",
        tips=tips,
        context={
            "entity": entity_name,
            "validation": "functional_dependency",
            "determinant_columns": error.determinant_columns,
            "details": error.details,
        },
        recoverable=True,
    ) from error


def get_project_service() -> ProjectService:
    """Dependency to get config service instance."""
    return ProjectService()


def get_preview_service() -> ShapeShiftService:
    """Dependency to get preview service instance (singleton)."""
    return get_shapeshift_service()


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
    body: Optional[dict[str, Any]] = Body(None, description="Request body with optional entity_config"),
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
    - Optionally accepts unsaved entity configuration to preview changes

    Set limit=null to retrieve all rows (use with caution for large datasets).
    If no limit is specified in the request, defaults to 50 rows.

    To preview unsaved changes, include entity_config in the request body:
    - The entity_config parameter allows previewing entities before saving
    - Cache is bypassed when entity_config is provided
    - Useful for iterative development and immediate feedback
    """
    try:
        # Extract entity_config from body if present
        # Frontend sends: {"entity_config": {...}}
        entity_config = body.get("entity_config") if body else None

        result: PreviewResult = await preview_service.preview_entity(project_name, entity_name, limit, override_config=entity_config)
        return result
    except FunctionalDependencyError as e:
        _raise_fd_validation_error(e, entity_name)
    except RuntimeError as e:
        fd_error = _find_fd_error(e)
        if fd_error is not None:
            _raise_fd_validation_error(fd_error, entity_name)
        raise
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
    except FunctionalDependencyError as e:
        _raise_fd_validation_error(e, entity_name)
    except RuntimeError as e:
        fd_error = _find_fd_error(e)
        if fd_error is not None:
            _raise_fd_validation_error(fd_error, entity_name)
        raise
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
