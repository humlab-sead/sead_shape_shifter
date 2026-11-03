"""API endpoint for read-only foreign-key link diagnostics."""

from typing import Annotated

from fastapi import APIRouter, Depends

from backend.app.authorization.dependencies import require_project
from backend.app.authorization.models import Action, AuthorizedResource
from backend.app.models.link_troubleshooter import LinkTroubleshootRequest, LinkTroubleshootResponse
from backend.app.services.link_troubleshooter_service import LinkTroubleshooterService
from backend.app.utils.error_handlers import handle_endpoint_errors

router = APIRouter()


def get_link_troubleshooter_service() -> LinkTroubleshooterService:
    """Create the link troubleshooter service for one request."""
    return LinkTroubleshooterService()


@router.post("/projects/{project_name}/link-troubleshooter", response_model=LinkTroubleshootResponse)
@handle_endpoint_errors
async def run_link_troubleshooter(
    project_name: str,  # pylint: disable=unused-argument
    request: LinkTroubleshootRequest,
    authorized_project: Annotated[AuthorizedResource, Depends(require_project(Action.READ))],
    service: Annotated[LinkTroubleshooterService, Depends(get_link_troubleshooter_service)],
) -> LinkTroubleshootResponse:
    """Compare saved-link behavior with optional alternative key selections."""
    return await service.run(
        project_name=authorized_project.resource.locator,
        issue_type=request.issue_type,
        local_entity=request.local_entity,
        metadata=request.metadata,
        local_keys=request.local_keys,
        remote_keys=request.remote_keys,
        page=request.page,
        page_size=request.page_size,
        row_filter=request.row_filter,
    )
