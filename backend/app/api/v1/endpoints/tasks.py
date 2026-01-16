"""API endpoints for entity task management and progress tracking."""

from typing import Any

from fastapi import APIRouter, HTTPException
from loguru import logger

from backend.app.models.task import ProjectTaskStatus, TaskUpdateResponse
from backend.app.services.task_service import get_task_service
from backend.app.utils.error_handlers import handle_endpoint_errors

router = APIRouter()


@router.get("/projects/{name}/tasks", response_model=ProjectTaskStatus)
@handle_endpoint_errors
async def get_project_task_status(name: str) -> ProjectTaskStatus:
    """
    Get task status for all entities in project.

    Computes full task status by combining:
    - Stored task list state (completed, ignored, required)
    - Derived state (validation results, preview availability)
    - Dependency analysis (blocked_by)

    Returns priority-based guidance and completion statistics.

    Args:
        name: Project name

    Returns:
        ProjectTaskStatus with all entity statuses and stats

    Example:
        GET /api/v1/projects/my-project/tasks

        Response:
        {
          "entities": {
            "location": {
              "status": "done",
              "priority": "ready",
              "required": true,
              "exists": true,
              "validation_passed": true,
              "preview_available": true,
              "blocked_by": [],
              "issues": []
            },
            "site": {
              "status": "todo",
              "priority": "ready",
              "required": true,
              "exists": true,
              "validation_passed": true,
              "preview_available": true,
              "blocked_by": [],
              "issues": []
            }
          },
          "completion_stats": {
            "total": 2,
            "done": 1,
            "todo": 1,
            "ignored": 0,
            "required_total": 2,
            "required_done": 1,
            "required_todo": 1
          }
        }
    """
    task_service = get_task_service()
    result = await task_service.compute_status(name)

    logger.info(
        f"Task status for '{name}': "
        f"{result.completion_stats['done']}/{result.completion_stats['total']} done, "
        f"{result.completion_stats['required_done']}/{result.completion_stats['required_total']} required done"
    )

    return result


@router.post("/projects/{name}/tasks/initialize")
@handle_endpoint_errors
async def initialize_task_list(
    name: str,
    strategy: str = "dependency-order",
) -> dict[str, Any]:
    """
    Initialize task list for the project.

    Auto-generates task list based on project structure and entity dependencies.

    Args:
        name: Project name
        strategy: Initialization strategy:
            - "all": Include all entities as required
            - "required-only": Include only entities with foreign keys
            - "dependency-order": Order by dependency graph (default)

    Returns:
        Dict with initialization results including list of required entities

    Example:
        POST /api/v1/projects/my-project/tasks/initialize?strategy=dependency-order

        Response:
        {
          "success": true,
          "strategy": "dependency-order",
          "required_entities": ["location", "site", "sample"],
          "message": "Task list initialized with 3 entities"
        }
    """
    task_service = get_task_service()

    result = await task_service.initialize_task_list(name, strategy)

    logger.info(f"Initialized task list for '{name}' with strategy '{strategy}'")

    return result


@router.post("/projects/{name}/tasks/{entity_name}/complete", response_model=TaskUpdateResponse)
@handle_endpoint_errors
async def mark_task_complete(name: str, entity_name: str) -> TaskUpdateResponse:
    """
    Mark entity task as complete.

    Validates that entity:
    - Exists in project
    - Passes validation
    - Has preview data available

    If validation or preview fails, returns error.

    Args:
        name: Project name
        entity_name: Entity name to mark as done

    Returns:
        TaskUpdateResponse with success status

    Raises:
        HTTPException 400: If entity fails validation or preview
        HTTPException 404: If entity doesn't exist

    Example:
        POST /api/v1/projects/my-project/tasks/location/complete

        Response:
        {
          "success": true,
          "entity_name": "location",
          "new_status": "done",
          "message": "Entity marked as completed"
        }
    """
    task_service = get_task_service()

    try:
        result = await task_service.mark_complete(name, entity_name)

        logger.info(f"Marked '{entity_name}' as complete in project '{name}'")

        return TaskUpdateResponse(
            success=result["success"],
            entity_name=result["entity_name"],
            new_status=result["status"],
            message=result.get("message"),
        )

    except ValueError as e:
        logger.warning(f"Failed to mark '{entity_name}' as complete: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/projects/{name}/tasks/{entity_name}/ignore", response_model=TaskUpdateResponse)
@handle_endpoint_errors
async def mark_task_ignored(name: str, entity_name: str) -> TaskUpdateResponse:
    """
    Mark entity task as ignored.

    Excludes entity from project completion tracking.
    Does not require validation or preview.

    Args:
        name: Project name
        entity_name: Entity name to mark as ignored

    Returns:
        TaskUpdateResponse with success status

    Example:
        POST /api/v1/projects/my-project/tasks/optional_entity/ignore

        Response:
        {
          "success": true,
          "entity_name": "optional_entity",
          "new_status": "ignored",
          "message": "Entity marked as ignored"
        }
    """
    task_service = get_task_service()
    result = await task_service.mark_ignored(name, entity_name)

    logger.info(f"Marked '{entity_name}' as ignored in project '{name}'")

    return TaskUpdateResponse(
        success=result["success"],
        entity_name=result["entity_name"],
        new_status=result["status"],
        message=result.get("message"),
    )


@router.delete("/projects/{name}/tasks/{entity_name}", response_model=TaskUpdateResponse)
@handle_endpoint_errors
async def reset_task_status(name: str, entity_name: str) -> TaskUpdateResponse:
    """
    Reset entity task status to todo.

    Removes completed or ignored status, returning entity to todo state.

    Args:
        name: Project name
        entity_name: Entity name to reset

    Returns:
        TaskUpdateResponse with success status

    Example:
        DELETE /api/v1/projects/my-project/tasks/location

        Response:
        {
          "success": true,
          "entity_name": "location",
          "new_status": "todo",
          "message": "Entity status reset to todo"
        }
    """
    task_service = get_task_service()
    result = await task_service.reset_status(name, entity_name)

    logger.info(f"Reset '{entity_name}' status in project '{name}'")

    return TaskUpdateResponse(
        success=result["success"],
        entity_name=result["entity_name"],
        new_status=result["status"],
        message=result.get("message"),
    )
