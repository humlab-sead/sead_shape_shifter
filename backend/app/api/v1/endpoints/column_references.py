"""Authorized read endpoints for draft-aware @value column references."""

from typing import Annotated

from fastapi import APIRouter, Depends

from backend.app.authorization.dependencies import require_project
from backend.app.authorization.models import Action, AuthorizedResource
from backend.app.models.column_reference import (
    ColumnReferenceCompleteRequest,
    ColumnReferenceCompleteResponse,
    ColumnReferenceResolveRequest,
    ColumnReferenceResolveResponse,
)
from backend.app.services.column_reference_service import ColumnReferenceService
from backend.app.utils.error_handlers import handle_endpoint_errors

router = APIRouter()


@router.post(
    "/projects/{project_name}/entities/{entity_name}/column-references/resolve",
    response_model=ColumnReferenceResolveResponse,
    response_model_exclude_none=True,
)
@handle_endpoint_errors
async def resolve_column_reference(
    project_name: str,  # pylint: disable=unused-argument
    entity_name: str,
    request: ColumnReferenceResolveRequest,
    authorized_project: Annotated[AuthorizedResource, Depends(require_project(Action.READ))],
) -> ColumnReferenceResolveResponse:
    """Return ordered columns or a local reason for one draft reference."""
    return ColumnReferenceService().resolve_reference(
        authorized_project.resource.locator,
        entity_name,
        request.entity_draft,
        request.directive,
    )


@router.post(
    "/projects/{project_name}/entities/{entity_name}/column-references/complete",
    response_model=ColumnReferenceCompleteResponse,
)
@handle_endpoint_errors
async def complete_column_references(
    project_name: str,  # pylint: disable=unused-argument
    entity_name: str,
    request: ColumnReferenceCompleteRequest,
    authorized_project: Annotated[AuthorizedResource, Depends(require_project(Action.READ))],
) -> ColumnReferenceCompleteResponse:
    """Return eligible entity-property references matching the typed prefix."""
    return ColumnReferenceService().complete_references(
        authorized_project.resource.locator,
        entity_name,
        request.entity_draft,
        request.prefix,
        edited_field_path=request.edited_field_path,
        preferred_entity=request.preferred_entity,
    )
