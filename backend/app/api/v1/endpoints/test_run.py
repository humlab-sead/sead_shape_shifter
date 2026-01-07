"""API endpoints for configuration test runs."""

from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Path
from loguru import logger

from backend.app.models.test_run import (
    TestProgress,
    TestRunRequest,
    TestRunResult,
)
from backend.app.services.project_service import ProjectService
from backend.app.services.test_run_service import TestRunService

router = APIRouter()

# Singleton instance to persist test runs across requests
_test_run_service_instance: Optional[TestRunService] = None  # pylint: disable=invalid-name


def get_project_service() -> ProjectService:
    """Dependency to get config service instance."""
    return ProjectService()


def get_test_run_service(
    project_service: ProjectService = Depends(get_project_service),
) -> TestRunService:
    """Dependency to get test run service instance (singleton)."""
    global _test_run_service_instance  # pylint: disable=global-statement
    if _test_run_service_instance is None:
        _test_run_service_instance = TestRunService(project_service)
    return _test_run_service_instance


@router.post(
    "/test-runs",
    response_model=TestRunResult,
    summary="Start a configuration test run",
    description="Run a configuration test with sample data to validate the configuration",
    responses={
        200: {"description": "Test run started successfully (returns immediately with PENDING status)"},
        400: {"description": "Invalid request parameters"},
        404: {"description": "Project not found"},
    },
)
async def start_test_run(
    request: TestRunRequest,
    background_tasks: BackgroundTasks,
    test_run_service: TestRunService = Depends(get_test_run_service),
) -> TestRunResult:
    """
    Start a configuration test run in the background.

    The test run will:
    - Process entities in dependency order
    - Limit rows per entity to prevent timeouts
    - Validate foreign keys and constraints
    - Return preview of results

    Returns immediately with PENDING status.
    Use GET /test-runs/{run_id} to check progress and results.
    """
    try:
        # Initialize test run and return immediately
        result = test_run_service.init_test_run(project_name=request.project_name, options=request.options)

        # Schedule actual execution in background
        background_tasks.add_task(test_run_service.execute_test_run, result.run_id)

        return result

    except ValueError as e:
        logger.error(f"Test run validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Test run failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Test run failed: {str(e)}") from e


@router.get(
    "/test-runs/{run_id}",
    response_model=TestRunResult,
    summary="Get test run result",
    description="Get the result of a test run by ID",
    responses={
        200: {"description": "Test run result returned"},
        404: {"description": "Test run not found"},
    },
)
async def get_test_run(
    run_id: str = Path(..., description="Test run ID"),
    test_run_service: TestRunService = Depends(get_test_run_service),
) -> TestRunResult:
    """
    Get test run result by ID.

    Returns complete results including:
    - Processing status for each entity
    - Validation issues
    - Preview of output data
    - Execution times
    """
    result = test_run_service.get_test_result(run_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Test run {run_id} not found")
    return result


@router.get(
    "/test-runs/{run_id}/progress",
    response_model=TestProgress,
    summary="Get test run progress",
    description="Get progress information for a running test",
    responses={
        200: {"description": "Progress information returned"},
        404: {"description": "Test run not found"},
    },
)
async def get_test_progress(
    run_id: str = Path(..., description="Test run ID"),
    test_run_service: TestRunService = Depends(get_test_run_service),
) -> TestProgress:
    """
    Get test run progress.

    Useful for:
    - Showing progress bar in UI
    - Estimating time remaining
    - Identifying current entity being processed
    """
    progress = test_run_service.get_test_progress(run_id)
    if not progress:
        raise HTTPException(status_code=404, detail=f"Test run {run_id} not found")
    return progress


@router.delete(
    "/test-runs/{run_id}",
    summary="Cancel or delete a test run",
    description="Cancel a running test or delete a completed test result",
    responses={
        200: {"description": "Test run cancelled or deleted"},
        404: {"description": "Test run not found"},
    },
)
async def delete_test_run(
    run_id: str = Path(..., description="Test run ID"),
    test_run_service: TestRunService = Depends(get_test_run_service),
) -> dict:
    """
    Cancel a running test or delete a completed test result.

    If the test is running, it will be cancelled.
    If the test is completed, the result will be deleted.
    """
    # Try to cancel first
    if test_run_service.cancel_test(run_id):
        return {"message": f"Test run {run_id} cancelled", "run_id": run_id}

    # If not running, try to delete
    if test_run_service.delete_test_result(run_id):
        return {"message": f"Test run {run_id} deleted", "run_id": run_id}

    raise HTTPException(status_code=404, detail=f"Test run {run_id} not found")


@router.get(
    "/test-runs",
    response_model=list[TestRunResult],
    summary="List all test runs",
    description="Get a list of all test runs (active and completed)",
    responses={
        200: {"description": "List of test runs returned"},
    },
)
async def list_test_runs(
    test_run_service: TestRunService = Depends(get_test_run_service),
) -> list[TestRunResult]:
    """
    List all test runs.

    Returns both active and completed test runs.
    Use this to show test run history.
    """
    return test_run_service.list_test_runs()
