"""API endpoints for entity reconciliation."""

import asyncio
import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from loguru import logger

from backend.app.clients.reconciliation_client import ReconciliationClient
from backend.app.core.config import settings
from backend.app.core.operation_manager import operation_manager
from backend.app.core.state_manager import get_app_state_manager
from backend.app.models.reconciliation import (
    AutoReconcileResult,
    EntityReconciliationSpec,
    ReconciliationCandidate,
    ReconciliationConfig,
)
from backend.app.services.reconciliation_service import ReconciliationService
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


@router.get("/projects/{project_name}/reconciliation")
@handle_endpoint_errors
async def get_reconciliation_config(
    project_name: str, service: ReconciliationService = Depends(get_reconciliation_service)
) -> ReconciliationConfig:
    """
    Get reconciliation configuration for a project.

    Returns the reconciliation spec including entity mappings and settings.
    """
    return service.load_reconciliation_config(project_name)


@router.put("/projects/{project_name}/reconciliation")
@handle_endpoint_errors
async def update_reconciliation_config(
    project_name: str,
    recon_config: ReconciliationConfig,
    service: ReconciliationService = Depends(get_reconciliation_service),
) -> ReconciliationConfig:
    """Update entire reconciliation configuration."""
    service.save_reconciliation_config(project_name, recon_config)
    return recon_config


@router.get("/projects/{project_name}/reconciliation/{entity_name}/preview")
@handle_endpoint_errors
async def get_reconciliation_preview(
    project_name: str,
    entity_name: str,
    service: ReconciliationService = Depends(get_reconciliation_service),
) -> list[dict[str, Any]]:
    """
    Get preview data for an entity with reconciliation mappings applied.

    Returns source data enriched with reconciliation status (sead_id, confidence, etc.)
    """
    return await service.get_reconciliation_preview(project_name, entity_name)


@router.post("/projects/{project_name}/reconciliation/{entity_name}/auto-reconcile")
@handle_endpoint_errors
async def auto_reconcile_entity(
    project_name: str,
    entity_name: str,
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
        threshold: Auto-accept threshold (default 0.95 = 95%)
        review_threshold: Review threshold (default uses entity spec value)

    Returns:
        Dictionary with operation_id for tracking progress
    """
    # Load reconciliation config
    recon_config: ReconciliationConfig = service.load_reconciliation_config(project_name)

    if entity_name not in recon_config.entities:
        raise NotFoundError(f"No reconciliation spec for entity '{entity_name}'")

    entity_spec: EntityReconciliationSpec = recon_config.entities[entity_name]

    # Update threshold if provided
    if threshold != entity_spec.auto_accept_threshold:
        entity_spec.auto_accept_threshold = threshold
    if review_threshold is not None and review_threshold != entity_spec.review_threshold:
        entity_spec.review_threshold = review_threshold

    # Persist updated thresholds even if reconciliation is blocked/fails.
    service.save_reconciliation_config(project_name, recon_config)

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
                entity_spec=entity_spec,
                operation_id=operation_id,
            )
        except Exception as e:
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
    progress = operation_manager.get_progress(operation_id)
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
    progress = operation_manager.get_progress(operation_id)
    if not progress:
        raise NotFoundError(f"Operation {operation_id} not found")

    async def event_generator():
        """Generate SSE events for operation progress."""
        try:
            while True:
                progress = operation_manager.get_progress(operation_id)
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
    success = operation_manager.cancel_operation(operation_id)
    if not success:
        raise NotFoundError(f"Operation {operation_id} not found")

    return {"operation_id": operation_id, "status": "cancelled", "message": "Cancellation requested"}


# Keep the original endpoint for backward compatibility (synchronous version)
@router.post("/projects/{project_name}/reconciliation/{entity_name}/auto-reconcile-sync")
@handle_endpoint_errors
async def auto_reconcile_entity_sync(
    project_name: str,
    entity_name: str,
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
        threshold: Auto-accept threshold (default 0.95 = 95%)
        review_threshold: Review threshold (default uses entity spec value)

    Returns:
        AutoReconcileResult with counts and candidates
    """
    # Load reconciliation config
    recon_config: ReconciliationConfig = service.load_reconciliation_config(project_name)

    if entity_name not in recon_config.entities:
        raise NotFoundError(f"No reconciliation spec for entity '{entity_name}'")

    entity_spec: EntityReconciliationSpec = recon_config.entities[entity_name]

    # Update threshold if provided
    if threshold != entity_spec.auto_accept_threshold:
        entity_spec.auto_accept_threshold = threshold
    if review_threshold is not None and review_threshold != entity_spec.review_threshold:
        entity_spec.review_threshold = review_threshold

    # Persist updated thresholds even if reconciliation is blocked/fails.
    service.save_reconciliation_config(project_name, recon_config)

    if get_app_state_manager().is_dirty(project_name):
        raise BadRequestError(f"Project '{project_name}' has unsaved changes. Save or discard changes before starting reconciliation.")

    logger.info(f"Starting auto-reconciliation for {entity_name} with threshold {threshold}")
    result: AutoReconcileResult = await service.auto_reconcile_entity(
        project_name=project_name,
        entity_name=entity_name,
        entity_spec=entity_spec,
        operation_id=None,  # No progress tracking for sync version
    )

    return result


@router.get("/projects/{project_name}/reconciliation/{entity_name}/suggest")
@handle_endpoint_errors
async def suggest_entities(
    project_name: str,
    entity_name: str,
    query: str = Query(..., min_length=2),
    service: ReconciliationService = Depends(get_reconciliation_service),
) -> list[ReconciliationCandidate]:
    """
    Get entity suggestions for autocomplete.

    Args:
        project_name: Project name
        entity_name: Entity type
        query: Search query (minimum 2 characters)

    Returns:
        list of matching candidates with scores
    """
    # Get entity spec to resolve service type
    recon_config: ReconciliationConfig = service.load_reconciliation_config(project_name)

    if entity_name not in recon_config.entities:
        raise NotFoundError(f"No reconciliation spec for entity '{entity_name}'")

    entity_spec: EntityReconciliationSpec = recon_config.entities[entity_name]

    # Get service type from entity spec
    if not entity_spec.remote.service_type:
        raise BadRequestError(f"Entity '{entity_name}' has no service_type configured")

    candidates: list[ReconciliationCandidate] = await service.recon_client.suggest_entities(
        prefix=query, entity_type=entity_spec.remote.service_type.lower(), limit=10
    )

    return candidates


@router.post("/projects/{project_name}/reconciliation/{entity_name}/mapping")
@handle_endpoint_errors
async def update_mapping(
    project_name: str,
    entity_name: str,
    source_values: list[Any],
    sead_id: int | None = None,
    notes: str | None = None,
    service: ReconciliationService = Depends(get_reconciliation_service),
) -> ReconciliationConfig:
    """
    Update or remove a single mapping entry.

    Args:
        project_name: Project name
        entity_name: Entity name
        source_values: Source key values
        sead_id: SEAD entity ID (null to remove mapping)
        notes: Optional notes

    Returns:
        Updated reconciliation configuration
    """
    return service.update_mapping(
        project_name=project_name,
        entity_name=entity_name,
        source_values=source_values,
        sead_id=sead_id,
        notes=notes,
    )


@router.delete("/projects/{project_name}/reconciliation/{entity_name}/mapping")
@handle_endpoint_errors
async def delete_mapping(
    project_name: str,
    entity_name: str,
    source_values: list[Any] = Query(...),
    service: ReconciliationService = Depends(get_reconciliation_service),
) -> ReconciliationConfig:
    """
    Delete a mapping entry.

    Args:
        project_name: Project name
        entity_name: Entity name
        source_values: Source key values to delete

    Returns:
        Updated reconciliation configuration
    """
    return service.update_mapping(
        project_name=project_name,
        entity_name=entity_name,
        source_values=source_values,
        sead_id=None,  # None = delete
    )


@router.post("/projects/{project_name}/reconciliation/{entity_name}/mark-unmatched")
@handle_endpoint_errors
async def mark_as_unmatched(
    project_name: str,
    entity_name: str,
    source_values: list[Any],
    notes: str | None = None,
    service: ReconciliationService = Depends(get_reconciliation_service),
) -> ReconciliationConfig:
    """
    Mark an entity as "will not match" - local-only entity with no SEAD mapping.

    Args:
        project_name: Project name
        entity_name: Entity name
        source_values: Source key values
        notes: Optional reason/notes for why it won't match

    Returns:
        Updated reconciliation configuration
    """
    return service.mark_as_unmatched(
        project_name=project_name,
        entity_name=entity_name,
        source_values=source_values,
        notes=notes,
    )
