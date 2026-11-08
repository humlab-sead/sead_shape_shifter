"""API endpoint for read-only foreign-key integrity inspection."""

from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, HTTPException

from backend.app.authorization.dependencies import require_project
from backend.app.authorization.models import Action, AuthorizedResource
from backend.app.models.integrity_troubleshooter import (
    IntegrityTroubleshootPageRequest,
    IntegrityTroubleshootRequest,
    IntegrityTroubleshootResponse,
)
from backend.app.services.integrity_troubleshooter_service import (
    IntegrityTroubleshooterContextResult,
    IntegrityTroubleshooterService,
)
from backend.app.utils.error_handlers import handle_endpoint_errors

router = APIRouter()


def get_integrity_troubleshooter_service() -> IntegrityTroubleshooterService:
    """Create the integrity troubleshooter service for one request."""
    return IntegrityTroubleshooterService()


@router.post("/projects/{project_name}/integrity-troubleshooter", response_model=IntegrityTroubleshootResponse)
@handle_endpoint_errors
async def run_integrity_troubleshooter(
    project_name: str,  # pylint: disable=unused-argument
    request: IntegrityTroubleshootRequest,
    authorized_project: Annotated[AuthorizedResource, Depends(require_project(Action.READ))],
    service: Annotated[IntegrityTroubleshooterService, Depends(get_integrity_troubleshooter_service)],
) -> IntegrityTroubleshootResponse:
    """Inspect the current unmatched values behind one integrity warning."""
    return await service.inspect(
        project_name=authorized_project.resource.locator,
        issue_type=request.issue_type,
        local_entity=request.local_entity,
        metadata=request.metadata,
        selected_value_token=request.selected_value_token,
        owner_principal_id=authorized_project.principal.principal_id,
        project_locator=authorized_project.resource.locator,
    )


@router.post(
    "/projects/{project_name}/integrity-troubleshooter/{context_id}/page",
    response_model=IntegrityTroubleshootResponse,
)
@handle_endpoint_errors
async def read_integrity_troubleshooter_page(
    project_name: str,  # pylint: disable=unused-argument
    context_id: str,
    request: IntegrityTroubleshootPageRequest,
    authorized_project: Annotated[AuthorizedResource, Depends(require_project(Action.READ))],
    service: Annotated[IntegrityTroubleshooterService, Depends(get_integrity_troubleshooter_service)],
) -> IntegrityTroubleshootResponse:
    """Read the complete inspection from an owned integrity context."""
    result: IntegrityTroubleshooterContextResult = await service.read_context(
        context_id=context_id,
        owner_principal_id=authorized_project.principal.principal_id,
        project_locator=authorized_project.resource.locator,
        selected_value_token=request.selected_value_token,
    )
    if result.state == "expired":
        _raise_context_expired()
    if result.response is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    return result.response


@router.delete("/projects/{project_name}/integrity-troubleshooter/{context_id}", status_code=204)
@handle_endpoint_errors
async def close_integrity_troubleshooter_context(
    project_name: str,  # pylint: disable=unused-argument
    context_id: str,
    authorized_project: Annotated[AuthorizedResource, Depends(require_project(Action.READ))],
    service: Annotated[IntegrityTroubleshooterService, Depends(get_integrity_troubleshooter_service)],
) -> None:
    """Release one owned integrity inspection."""
    closed: bool = await service.close_context(
        context_id=context_id,
        owner_principal_id=authorized_project.principal.principal_id,
        project_locator=authorized_project.resource.locator,
    )
    if not closed:
        raise HTTPException(status_code=404, detail="Resource not found")


def _raise_context_expired() -> NoReturn:
    """Raise the explicit expiry result shared by integrity context routes."""
    raise HTTPException(
        status_code=410,
        detail={
            "error_type": "IntegrityTroubleshooterContextExpired",
            "message": "The integrity inspection expired. Reopen the troubleshooter to read current data.",
            "reason": "context_expired",
            "recoverable": True,
        },
    )
