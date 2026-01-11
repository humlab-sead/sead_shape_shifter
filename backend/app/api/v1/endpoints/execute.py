"""API endpoints for executing full workflow."""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from loguru import logger

from backend.app.models.execute import DispatcherMetadata, ExecuteRequest, ExecuteResult
from backend.app.services.execute_service import ExecuteService, get_execute_service
from backend.app.utils.error_handlers import handle_endpoint_errors

router = APIRouter()


@router.get("/dispatchers", response_model=list[DispatcherMetadata])
@handle_endpoint_errors
async def get_dispatchers() -> list[DispatcherMetadata]:
    """
    Get list of available dispatchers.

    Returns list of dispatchers with metadata including:
    - key: Registered dispatcher key
    - target_type: Type of target (file, folder, database)
    - description: Human-readable description

    Returns:
        List of dispatcher metadata
    """
    execute_service: ExecuteService = get_execute_service()
    dispatchers = execute_service.get_dispatchers()

    logger.info(f"Retrieved {len(dispatchers)} dispatchers")
    return dispatchers


@router.post("/projects/{name}/execute", response_model=ExecuteResult)
@handle_endpoint_errors
async def execute_workflow(name: str, request: ExecuteRequest) -> ExecuteResult:
    """
    Execute full Shape Shifter workflow for a project.

    Performs the complete normalization workflow:
    1. Optional validation
    2. Load and normalize all entities
    3. Apply optional transformations (translate, drop FKs)
    4. Dispatch to target using selected dispatcher

    Args:
        name: Project name
        request: Execution parameters including:
            - dispatcher_key: Which dispatcher to use (csv, xlsx, db, etc.)
            - target: Output location (file path, folder path, or data source name)
            - run_validation: Whether to validate before execution (default: True)
            - translate: Apply translations (default: False)
            - drop_foreign_keys: Drop FK columns (default: False)
            - default_entity: Optional default entity

    Returns:
        ExecuteResult with success status, message, and execution details
    """
    execute_service: ExecuteService = get_execute_service()

    logger.info(f"Executing workflow for project '{name}' with dispatcher '{request.dispatcher_key}' to target '{request.target}'")

    result = await execute_service.execute_workflow(name, request)

    if result.success:
        logger.info(f"Workflow execution completed successfully: {result.message}")
    else:
        logger.error(f"Workflow execution failed: {result.message}")
        if result.error_details:
            logger.error(f"Error details: {result.error_details}")

    return result


@router.get("/projects/{name}/execute/download")
@handle_endpoint_errors
async def download_execution_output(
    name: str, target: str = Query(..., description="Absolute path to the dispatched file")
) -> FileResponse:
    """
    Download a file produced by a successful execution.

    Args:
        name: Project name (for logging)
        target: Absolute filesystem path to the generated file (should match ExecuteResult.target)
    """
    file_path = Path(target)
    if not file_path.is_file():
        logger.error("Requested download target not found: %s", target)
        raise HTTPException(status_code=404, detail="Execution output file not found")

    logger.info("Providing execution output download for project '%s': %s", name, target)
    return FileResponse(path=str(file_path), filename=file_path.name)
