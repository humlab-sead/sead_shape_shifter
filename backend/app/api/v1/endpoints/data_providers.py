"""Data Provider API Endpoints.

Exposes the curated provider-schema registry for provider and schema selection. The
registry is reviewed data, so this module offers a read-only list and no mutation route.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger

from backend.app.api.dependencies import get_data_provider_service
from backend.app.authorization.dependencies import get_principal
from backend.app.authorization.models import Principal
from backend.app.models.data_provider import DataProvider
from backend.app.services.data_provider_service import DataProviderRegistryError, DataProviderService

router = APIRouter(prefix="/data-providers", tags=["data-providers"])
data_provider_principal_dependency = get_principal()


@router.get("", response_model=list[DataProvider], summary="List curated data providers")
async def list_data_providers(
    service: Annotated[DataProviderService, Depends(get_data_provider_service)],
    _principal: Annotated[Principal, Depends(data_provider_principal_dependency)],
) -> list[DataProvider]:
    """Return registered providers and their schema scopes.

    Requires an authenticated principal. The response is sorted by provider code and
    schema code. A registry that cannot be read or validated returns a server error
    with a fixed message, so host paths and file content stay out of the response.
    """
    try:
        return service.list_providers()
    except DataProviderRegistryError as exc:
        logger.error(f"Data provider registry is unavailable: {exc}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Data provider registry is unavailable") from exc
