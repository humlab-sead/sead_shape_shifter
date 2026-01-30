"""API endpoints for entity materialization."""

from fastapi import APIRouter, HTTPException

from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.models.materialization import (
    CanMaterializeResponse,
    MaterializationResult,
    MaterializeRequest,
    UnmaterializationResult,
    UnmaterializeRequest,
)
from backend.app.models.project import Project
from backend.app.services.materialization_service import MaterializationService
from backend.app.services.project_service import ProjectService
from src.model import ShapeShiftProject, TableConfig

router = APIRouter()
project_service = ProjectService()
materialization_service = MaterializationService(project_service)


@router.get("/projects/{project_name}/entities/{entity_name}/can-materialize", response_model=CanMaterializeResponse)
async def can_materialize(project_name: str, entity_name: str) -> CanMaterializeResponse:
    """
    Check if an entity can be materialized.

    Returns validation errors and estimated row count.
    """
    try:
        # Load project
        api_project: Project = project_service.load_project(project_name)
        core_project: ShapeShiftProject = ProjectMapper.to_core(api_project)

        # Get entity
        try:
            table: TableConfig = core_project.get_table(entity_name)
        except KeyError as e:
            raise HTTPException(status_code=404, detail=f"Entity '{entity_name}' not found") from e

        # Validate
        can_mat, errors = table.can_materialize(core_project)

        # TODO: Estimate row count (would require running normalization)
        # For now, return None
        estimated_rows = None

        return CanMaterializeResponse(can_materialize=can_mat, errors=errors, estimated_rows=estimated_rows)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/projects/{project_name}/entities/{entity_name}/materialize", response_model=MaterializationResult)
async def materialize_entity(project_name: str, entity_name: str, request: MaterializeRequest) -> MaterializationResult:
    """
    Materialize an entity to fixed values.

    Process:
    1. Validates entity can be materialized
    2. Runs normalization pipeline
    3. Saves DataFrame to storage (parquet/csv/inline)
    4. Updates entity config with materialized section
    5. Saves project
    """
    result: MaterializationResult = await materialization_service.materialize_entity(
        project_name=project_name,
        entity_name=entity_name,
        user_email=request.user_email,
        storage_format=request.storage_format,
    )

    if not result.success:
        raise HTTPException(status_code=400, detail=result.errors[0] if result.errors else "Materialization failed")

    return result


@router.post("/projects/{project_name}/entities/{entity_name}/unmaterialize", response_model=UnmaterializationResult)
async def unmaterialize_entity(project_name: str, entity_name: str, request: UnmaterializeRequest) -> UnmaterializationResult:
    """
    Restore entity to dynamic state.

    Process:
    1. Checks if entity is materialized
    2. Finds dependent materialized entities
    3. If cascade=True, unmaterializes dependents first
    4. Restores saved_state config
    5. Saves project
    """
    result: UnmaterializationResult = await materialization_service.unmaterialize_entity(
        project_name=project_name, entity_name=entity_name, cascade=request.cascade
    )

    if not result.success:
        # Check if cascade required
        if result.requires_cascade:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": result.errors[0] if result.errors else "Cascade required",
                    "requires_cascade": True,
                    "affected_entities": result.affected_entities,
                },
            )

        raise HTTPException(status_code=400, detail=result.errors[0] if result.errors else "Unmaterialization failed")

    return result
