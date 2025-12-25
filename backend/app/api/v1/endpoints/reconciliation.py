"""API endpoints for entity reconciliation."""

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger

from backend.app.clients.reconciliation_client import ReconciliationClient
from backend.app.core.config import settings
from backend.app.models.reconciliation import (
    AutoReconcileResult,
    EntityReconciliationSpec,
    ReconciliationCandidate,
    ReconciliationConfig,
)
from backend.app.services.reconciliation_service import ReconciliationService

router = APIRouter()


async def get_reconciliation_service() -> ReconciliationService:
    """Dependency to get reconciliation service instance."""

    # Get reconciliation service URL from settings or use default
    service_url = getattr(settings, "RECONCILIATION_SERVICE_URL", "http://localhost:8000")

    recon_client = ReconciliationClient(base_url=service_url)

    return ReconciliationService(config_dir=Path(settings.CONFIGURATIONS_DIR), reconciliation_client=recon_client)


@router.get("/configurations/{config_name}/reconciliation")
async def get_reconciliation_config(
    config_name: str, service: ReconciliationService = Depends(get_reconciliation_service)
) -> ReconciliationConfig:
    """
    Get reconciliation configuration for a configuration.

    Returns the reconciliation spec including entity mappings and settings.
    """
    try:
        return service.load_reconciliation_config(config_name)
    except Exception as e:
        logger.error(f"Failed to load reconciliation config: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.put("/configurations/{config_name}/reconciliation")
async def update_reconciliation_config(
    config_name: str,
    recon_config: ReconciliationConfig,
    service: ReconciliationService = Depends(get_reconciliation_service),
) -> ReconciliationConfig:
    """Update entire reconciliation configuration."""
    try:
        service.save_reconciliation_config(config_name, recon_config)
        return recon_config
    except Exception as e:
        logger.error(f"Failed to save reconciliation config: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/configurations/{config_name}/reconciliation/{entity_name}/auto-reconcile")
async def auto_reconcile_entity(
    config_name: str,
    entity_name: str,
    threshold: float = Query(0.95, ge=0.0, le=1.0),
    service: ReconciliationService = Depends(get_reconciliation_service),
) -> AutoReconcileResult:
    """
    Automatically reconcile entity using OpenRefine service.

    Args:
        config_name: Configuration name
        entity_name: Entity to reconcile
        threshold: Auto-accept threshold (default 0.95 = 95%)

    Returns:
        AutoReconcileResult with counts and candidates
    """
    try:
        # Load reconciliation config
        recon_config: ReconciliationConfig = service.load_reconciliation_config(config_name)

        if entity_name not in recon_config.entities:
            raise HTTPException(
                status_code=404,
                detail=f"No reconciliation spec for entity '{entity_name}'",
            )

        entity_spec: EntityReconciliationSpec = recon_config.entities[entity_name]

        # Update threshold if provided
        if threshold != entity_spec.auto_accept_threshold:
            entity_spec.auto_accept_threshold = threshold

        logger.info(f"Starting auto-reconciliation for {entity_name} with threshold {threshold}")

        result: AutoReconcileResult = await service.auto_reconcile_entity(
            config_name=config_name,
            entity_name=entity_name,
            entity_spec=entity_spec,
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Auto-reconciliation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/configurations/{config_name}/reconciliation/{entity_name}/suggest")
async def suggest_entities(
    config_name: str,
    entity_name: str,
    query: str = Query(..., min_length=2),
    service: ReconciliationService = Depends(get_reconciliation_service),
) -> list[ReconciliationCandidate]:
    """
    Get entity suggestions for autocomplete.

    Args:
        config_name: Configuration name
        entity_name: Entity type
        query: Search query (minimum 2 characters)

    Returns:
        list of matching candidates with scores
    """
    try:
        # Get entity spec to resolve service type
        recon_config: ReconciliationConfig = service.load_reconciliation_config(config_name)

        if entity_name not in recon_config.entities:
            raise HTTPException(
                status_code=404,
                detail=f"No reconciliation spec for entity '{entity_name}'",
            )

        entity_spec: EntityReconciliationSpec = recon_config.entities[entity_name]

        # Get service type from entity spec
        if not entity_spec.remote.service_type:
            raise HTTPException(
                status_code=400,
                detail=f"Entity '{entity_name}' has no service_type configured",
            )

        candidates: list[ReconciliationCandidate] = await service.recon_client.suggest_entities(
            prefix=query, entity_type=entity_spec.remote.service_type.lower(), limit=10
        )

        return candidates

    except Exception as e:
        logger.error(f"Entity suggestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/configurations/{config_name}/reconciliation/{entity_name}/mapping")
async def update_mapping(
    config_name: str,
    entity_name: str,
    source_values: list[Any],
    sead_id: int | None = None,
    notes: str | None = None,
    service: ReconciliationService = Depends(get_reconciliation_service),
) -> ReconciliationConfig:
    """
    Update or remove a single mapping entry.

    Args:
        config_name: Configuration name
        entity_name: Entity name
        source_values: Source key values
        sead_id: SEAD entity ID (null to remove mapping)
        notes: Optional notes

    Returns:
        Updated reconciliation configuration
    """
    try:
        return service.update_mapping(
            config_name=config_name,
            entity_name=entity_name,
            source_values=source_values,
            sead_id=sead_id,
            notes=notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to update mapping: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/configurations/{config_name}/reconciliation/{entity_name}/mapping")
async def delete_mapping(
    config_name: str,
    entity_name: str,
    source_values: list[Any] = Query(...),
    service: ReconciliationService = Depends(get_reconciliation_service),
) -> ReconciliationConfig:
    """
    Delete a mapping entry.

    Args:
        config_name: Configuration name
        entity_name: Entity name
        source_values: Source key values to delete

    Returns:
        Updated reconciliation configuration
    """
    try:
        return service.update_mapping(
            config_name=config_name,
            entity_name=entity_name,
            source_values=source_values,
            sead_id=None,  # None = delete
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to delete mapping: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
