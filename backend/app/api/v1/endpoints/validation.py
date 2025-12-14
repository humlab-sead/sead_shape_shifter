"""API endpoints for validation and dependency analysis."""

from typing import Any

from fastapi import APIRouter, HTTPException, status
from loguru import logger

from app.models.validation import ValidationResult
from app.services.config_service import ConfigurationNotFoundError, get_config_service
from app.services.dependency_service import get_dependency_service
from app.services.validation_service import get_validation_service

router = APIRouter()


@router.post("/configurations/{name}/validate/data", response_model=ValidationResult)
async def validate_configuration_data(
    name: str, entity_names: list[str] | None = None
) -> ValidationResult:
    """
    Run data-aware validation on configuration.

    This validates actual data (not just configuration structure):
    - Checks configured columns exist in data
    - Verifies natural keys are unique
    - Confirms entities return data
    - Validates foreign key data integrity

    Args:
        name: Configuration name
        entity_names: Optional list of entity names to validate (None = all entities)

    Returns:
        Validation result with data-specific errors and warnings
    """
    validation_service = get_validation_service()

    try:
        # Run data validation
        result = await validation_service.validate_configuration_data(name, entity_names)

        logger.info(
            f"Data validation for '{name}' completed: "
            f"valid={result.is_valid}, errors={result.error_count}, warnings={result.warning_count}"
        )
        return result

    except ConfigurationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to validate data for '{name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate data: {str(e)}",
        ) from e


@router.post("/configurations/{name}/entities/{entity_name}/validate", response_model=ValidationResult)
async def validate_entity(name: str, entity_name: str) -> ValidationResult:
    """
    Validate specific entity within a configuration (structural validation only).

    Args:
        name: Configuration name
        entity_name: Entity name to validate

    Returns:
        Validation result with entity-specific errors and warnings
    """
    config_service = get_config_service()
    validation_service = get_validation_service()

    try:
        # Load configuration
        config = config_service.load_configuration(name)

        # Validate specific entity
        result = validation_service.validate_entity(config, entity_name)

        logger.info(
            f"Validated entity '{entity_name}' in configuration '{name}': "
            f"valid={result.is_valid}, errors={result.error_count}"
        )
        return result

    except ConfigurationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to validate entity '{entity_name}' in '{name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate entity: {str(e)}",
        ) from e


@router.get("/configurations/{name}/dependencies")
async def get_dependencies(name: str) -> dict[str, Any]:
    """
    Get dependency graph for configuration.

    Analyzes entity dependencies including:
    - Source dependencies
    - Explicit depends_on declarations
    - Foreign key relationships

    Args:
        name: Configuration name

    Returns:
        Dependency graph with nodes, edges, cycles, and topological order
    """
    config_service = get_config_service()
    dependency_service = get_dependency_service()

    try:
        # Load configuration
        config = config_service.load_configuration(name)

        # Analyze dependencies
        graph = dependency_service.analyze_dependencies(config)

        logger.debug(
            f"Retrieved dependency graph for '{name}': "
            f"{len(graph['nodes'])} nodes, {len(graph['edges'])} edges"
        )
        return dict(graph)

    except ConfigurationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to get dependencies for '{name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dependencies: {str(e)}",
        ) from e


@router.post("/configurations/{name}/dependencies/check")
async def check_dependencies(name: str) -> dict[str, Any]:
    """
    Check for circular dependencies in configuration.

    Args:
        name: Configuration name

    Returns:
        Dictionary with has_cycles flag, list of cycles, and cycle count
    """
    config_service = get_config_service()
    dependency_service = get_dependency_service()

    try:
        # Load configuration
        config = config_service.load_configuration(name)

        # Check for circular dependencies
        result = dependency_service.check_circular_dependencies(config)

        logger.info(
            f"Checked circular dependencies for '{name}': "
            f"has_cycles={result['has_cycles']}, cycles={result['cycle_count']}"
        )
        return result

    except ConfigurationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to check dependencies for '{name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check dependencies: {str(e)}",
        ) from e
