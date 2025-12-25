"""API endpoints for validation and dependency analysis."""

from typing import Any

from fastapi import APIRouter, HTTPException, status
from loguru import logger

from backend.app.utils.error_handlers import handle_endpoint_errors

from backend.app.models.validation import ValidationError, ValidationResult
from backend.app.services.auto_fix_service import AutoFixService
from backend.app.services.config_service import ConfigurationNotFoundError, get_config_service
from backend.app.services.dependency_service import get_dependency_service
from backend.app.services.validation_service import get_validation_service

router = APIRouter()


@router.post("/configurations/{name}/validate/data", response_model=ValidationResult)
@handle_endpoint_errors
async def validate_configuration_data(name: str, entity_names: list[str] | None = None) -> ValidationResult:
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
    # Run data validation
    result = await validation_service.validate_configuration_data(name, entity_names)

    logger.info(
        f"Data validation for '{name}' completed: "
        f"valid={result.is_valid}, errors={result.error_count}, warnings={result.warning_count}"
    )
    return result


@router.post("/configurations/{name}/entities/{entity_name}/validate", response_model=ValidationResult)
@handle_endpoint_errors
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

    # Load configuration
    config = config_service.load_configuration(name)

    # Validate specific entity
    result = validation_service.validate_entity(config, entity_name)

    logger.info(f"Validated entity '{entity_name}' in configuration '{name}': " f"valid={result.is_valid}, errors={result.error_count}")
    return result


@router.get("/configurations/{name}/dependencies")
@handle_endpoint_errors
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

    # Load configuration
    config = config_service.load_configuration(name)

    # Analyze dependencies
    graph = dependency_service.analyze_dependencies(config)

    logger.debug(f"Retrieved dependency graph for '{name}': " f"{len(graph['nodes'])} nodes, {len(graph['edges'])} edges")
    return dict(graph)


@router.post("/configurations/{name}/dependencies/check")
@handle_endpoint_errors
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

    # Load configuration
    config = config_service.load_configuration(name)

    # Check for circular dependencies
    result = dependency_service.check_circular_dependencies(config)

    logger.info(f"Checked circular dependencies for '{name}': " f"has_cycles={result['has_cycles']}, cycles={result['cycle_count']}")
    return result


@router.post("/configurations/{name}/fixes/preview")
@handle_endpoint_errors
async def preview_fixes(name: str, errors: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Preview automatic fixes for validation errors.

    Args:
        name: Configuration name
        errors: List of validation errors to generate fixes for

    Returns:
        Preview of fixes that would be applied
    """

    config_service = get_config_service()
    auto_fix_service = AutoFixService(config_service)

    # Convert dicts to ValidationError objects
    validation_errors = [ValidationError(**error) for error in errors]

    # Generate fix suggestions
    suggestions = auto_fix_service.generate_fix_suggestions(validation_errors)

    # Preview fixes
    preview = await auto_fix_service.preview_fixes(name, suggestions)

    return preview


@router.post("/configurations/{name}/fixes/apply")
@handle_endpoint_errors
async def apply_fixes(name: str, errors: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Apply automatic fixes to configuration.

    This will:
    1. Create a backup of the configuration
    2. Apply suggested fixes
    3. Save the updated configuration
    4. Return the result

    Args:
        name: Configuration name
        errors: List of validation errors to fix

    Returns:
        Result of applying fixes including backup path
    """

    config_service = get_config_service()
    auto_fix_service = AutoFixService(config_service)

    # Convert dicts to ValidationError objects
    validation_errors = [ValidationError(**error) for error in errors]

    # Generate fix suggestions
    suggestions = auto_fix_service.generate_fix_suggestions(validation_errors)

    # Apply fixes
    result = await auto_fix_service.apply_fixes(name, suggestions)

    if result.success:
        logger.info(f"Applied {result.fixes_applied} fixes to '{name}', backup at {result.backup_path}")
    else:
        logger.warning(f"Failed to apply fixes to '{name}': {result.errors}")

    return result.model_dump()
