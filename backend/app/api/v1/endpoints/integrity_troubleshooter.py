"""API endpoint for read-only foreign-key integrity inspection."""

from typing import Annotated

from fastapi import APIRouter, Depends

from backend.app.authorization.dependencies import require_project
from backend.app.authorization.models import Action, AuthorizedResource
from backend.app.models.integrity_troubleshooter import IntegrityTroubleshootRequest, IntegrityTroubleshootResponse
from backend.app.services.integrity_troubleshooter_service import IntegrityTroubleshooterService
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
        page=request.page,
        selected_value_token=request.selected_value_token,
    )
