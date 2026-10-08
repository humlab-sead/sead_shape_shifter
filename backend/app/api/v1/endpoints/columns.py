"""API endpoints for column introspection."""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.app.authorization.dependencies import require_project
from backend.app.authorization.models import Action, AuthorizedResource
from backend.app.models.column_availability import ColumnAvailabilityRequest, ColumnAvailabilityResponse
from backend.app.services.column_introspection_service import ColumnAvailability, ColumnIntrospectionService
from backend.app.services.project_service import ProjectService
from backend.app.services.stage_aware_column_service import StageAwareColumnService
from backend.app.utils.error_handlers import handle_endpoint_errors

router = APIRouter()


@router.post(
    "/projects/{project_name}/entities/{entity_name}/column-availability",
    response_model=ColumnAvailabilityResponse,
)
@handle_endpoint_errors
async def get_stage_aware_column_availability(
    project_name: str,  # pylint: disable=unused-argument
    entity_name: str,
    request: ColumnAvailabilityRequest,
    authorized_project: Annotated[AuthorizedResource, Depends(require_project(Action.READ))],
) -> ColumnAvailabilityResponse:
    """Return operation-specific candidates for the submitted entity draft."""
    service = StageAwareColumnService()
    return service.get_column_availability(
        authorized_project.resource.locator,
        entity_name,
        request.entity_draft,
        source_columns=request.source_columns,
    )


@router.get("/projects/{project_name}/entities/{entity_name}/columns", response_model=dict[str, ColumnAvailability])
async def get_available_columns(
    project_name: str,
    entity_name: str,
    authorized_project: Annotated[AuthorizedResource, Depends(require_project(Action.READ))],
    remote_entity: Optional[str] = Query(None, description="Remote entity name for FK relationship"),
):
    """
    Get available columns for FK editing.

    Returns categorized columns for the local entity and optionally for a remote entity.
    Categories include: explicit, keys, extra, unnested, foreign_key, system, directives.

    Args:
        project_name: Project name
        entity_name: Local entity (child in FK)
        remote_entity: Optional remote entity (parent in FK)

    Returns:
        Dict with 'local_columns' and optionally 'remote_columns' containing ColumnAvailability
    """
    try:
        project_service = ProjectService()
        introspection_service = ColumnIntrospectionService(project_service)

        result = introspection_service.get_available_columns(authorized_project.resource.locator, entity_name, remote_entity)

        return result

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Project '{project_name}' not found")  # pylint: disable=raise-missing-from
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
