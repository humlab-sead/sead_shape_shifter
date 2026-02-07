"""API endpoints for entity reconciliation."""

import asyncio
import json
from pathlib import Path
from typing import Any

import yaml as pyyaml
from fastapi import APIRouter, Body, Depends, Query
from fastapi.responses import StreamingResponse
from loguru import logger
from pydantic import ValidationError

from backend.app.clients.reconciliation_client import ReconciliationClient
from backend.app.core.config import settings
from backend.app.core.operation_manager import OperationProgress, operation_manager
from backend.app.core.state_manager import get_app_state_manager
from backend.app.models.reconciliation import (
    AutoReconcileResult,
    EntityMapping,
    ReconciliationCandidate,
    EntityMappingRegistry,
    EntityMappingCreateRequest,
    EntityMappingListItem,
    EntityMappingUpdateRequest,
)
from backend.app.services.reconciliation import ReconciliationService
from backend.app.utils.error_handlers import handle_endpoint_errors
from backend.app.utils.exceptions import BadRequestError, NotFoundError

router = APIRouter()


async def get_reconciliation_service() -> ReconciliationService:
    """Dependency to get reconciliation service instance."""

    # Get reconciliation service URL from settings or use default
    service_url = getattr(settings, "RECONCILIATION_SERVICE_URL", "http://localhost:8000")

    recon_client = ReconciliationClient(base_url=service_url)

    return ReconciliationService(config_dir=Path(settings.PROJECTS_DIR), reconciliation_client=recon_client)


@router.get("/reconciliation/health")
@handle_endpoint_errors
async def check_reconciliation_service_health(service: ReconciliationService = Depends(get_reconciliation_service)) -> dict:
    """
    Check if the reconciliation service is available.

    Returns:
        Status information about the reconciliation service
    """
    return await service.recon_client.check_health()


@router.get("/reconciliation/manifest")
@handle_endpoint_errors
async def get_reconciliation_service_manifest(service: ReconciliationService = Depends(get_reconciliation_service)) -> dict:
    """
    Get reconciliation service manifest.

    Returns:
        Full service manifest including available entity types, properties, and configuration
    """
    return await service.recon_client.get_service_manifest()


@router.get("/projects/{project_name}/reconciliation")
@handle_endpoint_errors
async def get_entity_mapping_registry(
    project_name: str, service: ReconciliationService = Depends(get_reconciliation_service)
) -> EntityMappingRegistry:
    """
    Get entity mapping registry for a project.

    Returns the entity mapping registry including entity mappings and settings.
    """
    return service.mapping_manager.load_registry(project_name)


@router.put("/projects/{project_name}/reconciliation")
@handle_endpoint_errors
async def update_entity_mapping_registry(
    project_name: str,
    recon_config: EntityMappingRegistry,
    service: ReconciliationService = Depends(get_reconciliation_service),
) -> EntityMappingRegistry:
    """Update entire entity mapping registry."""
    service.mapping_manager.save_registry(project_name, recon_config)
    return recon_config


@router.put("/projects/{project_name}/reconciliation/raw")
@handle_endpoint_errors
async def update_entity_mapping_registry_raw(
    project_name: str,
    yaml_content: str = Body(..., media_type="text/plain"),
    service: ReconciliationService = Depends(get_reconciliation_service),
) -> EntityMappingRegistry:
    """
    Update entity mapping registry from raw YAML content.

    Parses the YAML content, validates it, and saves to the project's reconciliation file.
    """

    try:
        # Parse YAML
        config_dict = pyyaml.safe_load(yaml_content)

        # Validate against model
        recon_config = EntityMappingRegistry(**config_dict)

        # Save
        service.mapping_manager.save_registry(project_name, recon_config)

        return recon_config
    except pyyaml.YAMLError as e:
        raise BadRequestError(f"Invalid YAML: {str(e)}") from e
    except ValidationError as e:
        raise BadRequestError(f"Invalid entity mapping registry: {str(e)}") from e


@router.get("/projects/{project_name}/reconciliation/{entity_name}/{target_field}/preview")
@handle_endpoint_errors
async def get_reconciliation_preview(
    project_name: str,
    entity_name: str,
    target_field: str,
    service: ReconciliationService = Depends(get_reconciliation_service),
) -> list[dict[str, Any]]:
    """
    Get preview data for an entity with reconciliation mappings applied.

    Returns source data enriched with reconciliation status (sead_id, confidence, etc.)
    """
    return await service.get_reconciliation_preview(project_name, entity_name, target_field)


@router.post("/projects/{project_name}/reconciliation/{entity_name}/{target_field}/auto-reconcile")
@handle_endpoint_errors
async def auto_reconcile_entity(
    project_name: str,
    entity_name: str,
    target_field: str,
    threshold: float = Query(0.95, ge=0.0, le=1.0),
    review_threshold: float | None = Query(None, ge=0.0, le=1.0),
    service: ReconciliationService = Depends(get_reconciliation_service),
) -> dict[str, str]:
    """
    Start automatic reconciliation for an entity (async with progress tracking).

    Returns an operation_id that can be used to track progress via SSE.

    Args:
        project_name: Project name
        entity_name: Entity to reconcile
        target_field: Target field to reconcile
        threshold: Auto-accept threshold (default 0.95 = 95%)
        review_threshold: Review threshold (default uses entity spec value)

    Returns:
        Dictionary with operation_id for tracking progress
    """
    # Load reconciliation config
    mapping_registry: EntityMappingRegistry = service.mapping_manager.load_registry(project_name)

    if entity_name not in mapping_registry.entities or target_field not in mapping_registry.entities[entity_name]:
        raise NotFoundError(f"No reconciliation registry for entity '{entity_name}' target '{target_field}'")

    entity_mapping: EntityMapping = mapping_registry.entities[entity_name][target_field]

    # Update threshold if provided
    if threshold != entity_mapping.auto_accept_threshold:
        entity_mapping.auto_accept_threshold = threshold
    if review_threshold is not None and review_threshold != entity_mapping.review_threshold:
        entity_mapping.review_threshold = review_threshold

    # Persist updated thresholds even if reconciliation is blocked/fails.
    service.mapping_manager.save_registry(project_name, mapping_registry)

    if get_app_state_manager().is_dirty(project_name):
        raise BadRequestError(f"Project '{project_name}' has unsaved changes. Save or discard changes before starting reconciliation.")

    # Create operation for progress tracking
    operation_id = operation_manager.create_operation(
        operation_type="auto_reconcile",
        total=0,  # Will be updated once we know query count
        message=f"Starting reconciliation for {entity_name}...",
        metadata={"project": project_name, "entity": entity_name, "threshold": threshold},
    )

    # Start reconciliation in background task
    async def run_reconciliation():
        try:
            await service.auto_reconcile_entity(
                project_name=project_name,
                entity_name=entity_name,
                target_field=target_field,
                entity_mapping=entity_mapping,
                operation_id=operation_id,
            )
        except Exception as e:  # pylint: disable=broad-except
            logger.error(f"Reconciliation failed: {e}")
            operation_manager.fail_operation(operation_id, str(e))

    # Run in background
    asyncio.create_task(run_reconciliation())

    logger.info(f"Started auto-reconciliation operation {operation_id} for {entity_name}")
    return {"operation_id": operation_id, "message": f"Reconciliation started for {entity_name}"}


@router.get("/operations/{operation_id}/progress")
async def get_operation_progress(operation_id: str) -> dict[str, Any]:
    """
    Get current progress for an operation.

    Args:
        operation_id: Operation ID

    Returns:
        Progress information
    """
    progress: OperationProgress | None = operation_manager.get_progress(operation_id)
    if not progress:
        raise NotFoundError(f"Operation {operation_id} not found")

    return progress.to_dict()


@router.get("/operations/{operation_id}/stream")
async def stream_operation_progress(operation_id: str) -> StreamingResponse:
    """
    Stream real-time progress updates via Server-Sent Events (SSE).

    Args:
        operation_id: Operation ID

    Returns:
        SSE stream of progress updates
    """
    progress: OperationProgress | None = operation_manager.get_progress(operation_id)
    if not progress:
        raise NotFoundError(f"Operation {operation_id} not found")

    async def event_generator():
        """Generate SSE events for operation progress."""
        try:
            while True:
                progress: OperationProgress | None = operation_manager.get_progress(operation_id)
                if not progress:
                    break

                # Send progress update as SSE event
                data = json.dumps(progress.to_dict())
                yield f"data: {data}\n\n"

                # Check if operation is complete
                if progress.status in ("completed", "failed", "cancelled"):
                    break

                # Wait before next update
                await asyncio.sleep(0.5)

        except asyncio.CancelledError:
            logger.debug(f"SSE stream cancelled for operation {operation_id}")
        finally:
            # Cleanup operation after stream ends
            operation_manager.cleanup_operation(operation_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.post("/operations/{operation_id}/cancel")
@handle_endpoint_errors
async def cancel_operation(operation_id: str) -> dict[str, str]:
    """
    Cancel a running operation.

    Args:
        operation_id: Operation ID to cancel

    Returns:
        Cancellation status
    """
    success: bool = operation_manager.cancel_operation(operation_id)
    if not success:
        raise NotFoundError(f"Operation {operation_id} not found")

    return {"operation_id": operation_id, "status": "cancelled", "message": "Cancellation requested"}


# Keep the original endpoint for backward compatibility (synchronous version)
@router.post("/projects/{project_name}/reconciliation/{entity_name}/{target_field}/auto-reconcile-sync")
@handle_endpoint_errors
async def auto_reconcile_entity_sync(
    project_name: str,
    entity_name: str,
    target_field: str,
    threshold: float = Query(0.95, ge=0.0, le=1.0),
    review_threshold: float | None = Query(None, ge=0.0, le=1.0),
    service: ReconciliationService = Depends(get_reconciliation_service),
) -> AutoReconcileResult:
    """
    Automatically reconcile entity (synchronous - blocks until complete).

    This is the original endpoint kept for backward compatibility.
    For progress tracking, use POST /auto-reconcile instead.

    Args:
        project_name: Project name
        entity_name: Entity to reconcile
        target_field: Target field to reconcile
        threshold: Auto-accept threshold (default 0.95 = 95%)
        review_threshold: Review threshold (default uses entity spec value)

    Returns:
        AutoReconcileResult with counts and candidates
    """
    # Load reconciliation config
    mapping_registry: EntityMappingRegistry = service.mapping_manager.load_registry(project_name)

    if entity_name not in mapping_registry.entities or target_field not in mapping_registry.entities[entity_name]:
        raise NotFoundError(f"No reconciliation registry for entity '{entity_name}' target '{target_field}'")

    entity_mapping: EntityMapping = mapping_registry.entities[entity_name][target_field]

    # Update threshold if provided
    if threshold != entity_mapping.auto_accept_threshold:
        entity_mapping.auto_accept_threshold = threshold
    if review_threshold is not None and review_threshold != entity_mapping.review_threshold:
        entity_mapping.review_threshold = review_threshold

    # Persist updated thresholds even if reconciliation is blocked/fails.
    service.mapping_manager.save_registry(project_name, mapping_registry)

    if get_app_state_manager().is_dirty(project_name):
        raise BadRequestError(f"Project '{project_name}' has unsaved changes. Save or discard changes before starting reconciliation.")

    logger.info(f"Starting auto-reconciliation for {entity_name}.{target_field} with threshold {threshold}")
    result: AutoReconcileResult = await service.auto_reconcile_entity(
        project_name=project_name,
        entity_name=entity_name,
        target_field=target_field,
        entity_mapping=entity_mapping,
        operation_id=None,  # No progress tracking for sync version
    )

    return result


@router.get("/projects/{project_name}/reconciliation/{entity_name}/{target_field}/suggest")
@handle_endpoint_errors
async def suggest_entities(
    project_name: str,
    entity_name: str,
    target_field: str,
    query: str = Query(..., min_length=2),
    service: ReconciliationService = Depends(get_reconciliation_service),
) -> list[ReconciliationCandidate]:
    """
    Get entity suggestions for autocomplete.

    Args:
        project_name: Project name
        entity_name: Entity type
        target_field: Target field to reconcile
        query: Search query (minimum 2 characters)

    Returns:
        list of matching candidates with scores
    """
    # Get entity spec to resolve service type
    mapping_registry: EntityMappingRegistry = service.mapping_manager.load_registry(project_name)

    if entity_name not in mapping_registry.entities or target_field not in mapping_registry.entities[entity_name]:
        raise NotFoundError(f"No reconciliation registry for entity '{entity_name}' target '{target_field}'")

    entity_mapping: EntityMapping = mapping_registry.entities[entity_name][target_field]

    # Get service type from entity spec
    if not entity_mapping.remote.service_type:
        raise BadRequestError(f"Entity '{entity_name}' has no service_type configured")

    candidates: list[ReconciliationCandidate] = await service.recon_client.suggest_entities(
        prefix=query, entity_type=entity_mapping.remote.service_type.lower(), limit=10
    )

    return candidates


@router.post("/projects/{project_name}/reconciliation/{entity_name}/{target_field}/mapping")
@handle_endpoint_errors
async def update_mapping(
    project_name: str,
    entity_name: str,
    target_field: str,
    source_value: Any,
    sead_id: int | None = None,
    notes: str | None = None,
    service: ReconciliationService = Depends(get_reconciliation_service),
) -> EntityMappingRegistry:
    """
    Update or remove a single mapping entry.

    Args:
        project_name: Project name
        entity_name: Entity name
        target_field: Target field to reconcile
        source_value: Source value (single value, not list)
        sead_id: SEAD entity ID (null to remove mapping)
        notes: Optional notes

    Returns:
        Updated entity mapping in reconciliation registry
    """
    return service.update_mapping(
        project_name=project_name,
        entity_name=entity_name,
        target_field=target_field,
        source_value=source_value,
        sead_id=sead_id,
        notes=notes,
    )


@router.delete("/projects/{project_name}/reconciliation/{entity_name}/{target_field}/mapping")
@handle_endpoint_errors
async def delete_mapping(
    project_name: str,
    entity_name: str,
    target_field: str,
    source_value: Any = Query(...),
    service: ReconciliationService = Depends(get_reconciliation_service),
) -> EntityMappingRegistry:
    """
    Delete a mapping entry.

    Args:
        project_name: Project name
        entity_name: Entity name
        target_field: Target field to reconcile
        source_value: Source value to delete (single value, not list)

    Returns:
        Updated reconciliation configuration
    """
    return service.update_mapping(
        project_name=project_name,
        entity_name=entity_name,
        target_field=target_field,
        source_value=source_value,
        sead_id=None,  # None = delete
    )


@router.post("/projects/{project_name}/reconciliation/{entity_name}/{target_field}/mark-unmatched")
@handle_endpoint_errors
async def mark_as_unmatched(
    project_name: str,
    entity_name: str,
    target_field: str,
    source_value: Any,
    notes: str | None = None,
    service: ReconciliationService = Depends(get_reconciliation_service),
) -> EntityMappingRegistry:
    """
    Mark an entity as "will not match" - local-only entity with no SEAD mapping.

    Args:
        project_name: Project name
        entity_name: Entity name
        target_field: Target field to reconcile
        source_value: Source value (single value, not list)
        notes: Optional reason/notes for why it won't match

    Returns:
        Updated reconciliation configuration
    """
    return service.mark_as_unmatched(
        project_name=project_name,
        entity_name=entity_name,
        target_field=target_field,
        source_value=source_value,
        notes=notes,
    )


# Specification management endpoints


@router.get("/projects/{project_name}/reconciliation/mapping-registry")
@handle_endpoint_errors
async def list_entity_mappings(
    project_name: str,
    service: ReconciliationService = Depends(get_reconciliation_service),
) -> list[EntityMappingListItem]:
    """
    List all entity mappings for a project.

    Returns a flattened list where each item represents an entity + target field combination.

    Args:
        project_name: Project name

    Returns:
        List of entity mapping items with metadata
    """

    return service.mapping_manager.list_entity_mappings(project_name)


@router.post("/projects/{project_name}/reconciliation/mapping-registry", status_code=201)
@handle_endpoint_errors
async def create_registry(
    project_name: str,
    request: EntityMappingCreateRequest,
    service: ReconciliationService = Depends(get_reconciliation_service),
) -> EntityMappingRegistry:
    """
    Create a new entity mapping registry for this project.

    Args:
        project_name: Project name
        request: Mapping registry create request containing entity, target field, and spec

    Returns:
        Updated reconciliation registry

    Raises:
        BadRequestError: If mapping registry already exists or entity doesn't exist
    """

    return service.mapping_manager.create_registry(
        project_name=project_name,
        entity_name=request.entity_name,
        target_field=request.target_field,
        entity_mapping=request.spec,
    )


@router.put("/projects/{project_name}/reconciliation/mapping-registry/{entity_name}/{target_field}")
@handle_endpoint_errors
async def update_registry(
    project_name: str,
    entity_name: str,
    target_field: str,
    request: "EntityMappingUpdateRequest",
    service: ReconciliationService = Depends(get_reconciliation_service),
) -> EntityMappingRegistry:
    """
    Update an existing reconciliation registry.

    Note: Entity name, target field, and existing mappings are preserved.

    Args:
        project_name: Project name
        entity_name: Entity name (from URL, cannot be changed)
        target_field: Target field name (from URL, cannot be changed)
        request: Entity mapping registry update request with editable fields

    Returns:
        Updated reconciliation registry

    Raises:
        NotFoundError: If registry doesn't exist
    """

    return service.mapping_manager.update_registry(
        project_name=project_name,
        entity_name=entity_name,
        target_field=target_field,
        source=request.source,
        property_mappings=request.property_mappings,
        remote=request.remote,
        auto_accept_threshold=request.auto_accept_threshold,
        review_threshold=request.review_threshold,
    )


@router.delete("/projects/{project_name}/reconciliation/mapping-registry/{entity_name}/{target_field}")
@handle_endpoint_errors
async def delete_registry(
    project_name: str,
    entity_name: str,
    target_field: str,
    force: bool = Query(False, description="Force delete even if mappings exist"),
    service: ReconciliationService = Depends(get_reconciliation_service),
) -> EntityMappingRegistry:
    """
    Delete a entity mappings from reconciliation registry.

    Args:
        project_name: Project name
        entity_name: Entity name
        target_field: Target field name
        force: If True, delete even if registry has mappings for entity

    Returns:
        Updated reconciliation registry

    Raises:
        NotFoundError: If registry doesn't exist
        BadRequestError: If registry has mappings and force=False
    """
    return service.mapping_manager.delete_registry(
        project_name=project_name,
        entity_name=entity_name,
        target_field=target_field,
        force=force,
    )


@router.get("/projects/{project_name}/reconciliation/available-fields/{entity_name}")
@handle_endpoint_errors
async def get_available_target_fields(
    project_name: str,
    entity_name: str,
    service: ReconciliationService = Depends(get_reconciliation_service),
) -> list[str]:
    """
    Get available target fields for an entity (from entity preview schema).

    Args:
        project_name: Project name
        entity_name: Entity name

    Returns:
        List of column names available in the entity

    Raises:
        NotFoundError: If entity doesn't exist
    """
    return await service.get_available_target_fields(project_name, entity_name)


@router.get("/projects/{project_name}/reconciliation/mapping-registry/{entity_name}/{target_field}/mapping-count")
@handle_endpoint_errors
async def get_mapping_count(
    project_name: str,
    entity_name: str,
    target_field: str,
    service: ReconciliationService = Depends(get_reconciliation_service),
) -> dict[str, int]:
    """
    Get the number of mappings for an entity in the mapping registry.

    Args:
        project_name: Project name
        entity_name: Entity name
        target_field: Target field name

    Returns:
        Dictionary with mapping count

    Raises:
        NotFoundError: If registry doesn't exist
    """
    count: int = service.get_mapping_count(project_name, entity_name, target_field)
    return {"count": count}
