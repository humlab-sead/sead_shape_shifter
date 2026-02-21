"""API endpoints for column introspection."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from backend.app.services.column_introspection_service import ColumnAvailability, ColumnIntrospectionService
from backend.app.services.project_service import ProjectService

router = APIRouter()


@router.get("/projects/{project_name}/entities/{entity_name}/columns", response_model=dict[str, ColumnAvailability])
async def get_available_columns(
    project_name: str,
    entity_name: str,
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

        result = introspection_service.get_available_columns(project_name, entity_name, remote_entity)

        return result

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Project '{project_name}' not found")  # pylint: disable=raise-missing-from
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
