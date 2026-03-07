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
                        "completion_percentage": 50.0,
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


@router.post("/projects/{name}/tasks/{entity_name}/ongoing", response_model=TaskUpdateResponse)
@handle_endpoint_errors
async def mark_task_ongoing(name: str, entity_name: str) -> TaskUpdateResponse:
    """
    Mark entity task as ongoing (in progress).

    Indicates that work has started on the entity but is not yet complete.
    Does not require validation or preview.

    Args:
        name: Project name
        entity_name: Entity name to mark as ongoing

    Returns:
        TaskUpdateResponse with success status

    Example:
        POST /api/v1/projects/my-project/tasks/site/ongoing

        Response:
        {
          "success": true,
          "entity_name": "site",
          "new_status": "ongoing",
          "message": "Entity marked as ongoing"
        }
    """
    task_service = get_task_service()
    result = await task_service.mark_ongoing(name, entity_name)

    logger.info(f"Marked '{entity_name}' as ongoing in project '{name}'")

    return TaskUpdateResponse(
        success=result["success"],
        entity_name=result["entity_name"],
        new_status=result["status"],
        message=result.get("message"),
    )


@router.post("/projects/{name}/tasks/{entity_name}/flag", response_model=dict[str, Any])
@handle_endpoint_errors
async def toggle_task_flagged(name: str, entity_name: str) -> dict[str, Any]:
    """
    Toggle flagged status for an entity task.

    Marks entity for special attention or review without changing its status.
    Can be combined with any task status (done, ongoing, todo, ignored).

    Args:
        name: Project name
        entity_name: Entity name to toggle flag

    Returns:
        Dict with success status and new flagged state

    Example:
        POST /api/v1/projects/my-project/tasks/location/flag

        Response:
        {
          "success": true,
          "entity_name": "location",
          "flagged": true,
          "message": "Entity flagged"
        }
    """
    task_service = get_task_service()
    result = await task_service.toggle_flagged(name, entity_name)

    logger.info(f"Toggled flag for '{entity_name}' in project '{name}': {result['flagged']}")

    return result


@router.post("/projects/{name}/tasks/migrate-to-sidecar", response_model=dict[str, Any])
@handle_endpoint_errors
async def migrate_tasks_to_sidecar(name: str) -> dict[str, Any]:
    """
    Migrate task list from main project file to sidecar file.

    One-time migration: moves task_list from shapeshifter.yml to shapeshifter.tasks.yml
    and removes it from the main project file.

    If sidecar already exists or main file has no task_list, returns success
    without making changes.

    Args:
        name: Project name

    Returns:
        Dict with success status and migration results

    Example:
        POST /api/v1/projects/my-project/tasks/migrate-to-sidecar

        Response:
        {
          "success": true,
          "project_name": "my-project",
          "sidecar_path": "/path/to/shapeshifter.tasks.yml",
          "migrated": true,
          "message": "Task list migrated to sidecar"
        }
    """
    from pathlib import Path  # pylint: disable=import-outside-toplevel

    from backend.app.core.config import settings  # pylint: disable=import-outside-toplevel
    from backend.app.mappers.project_name_mapper import ProjectNameMapper  # pylint: disable=import-outside-toplevel
    from backend.app.services.project_service import get_project_service  # pylint: disable=import-outside-toplevel
    from backend.app.services.task_list_sidecar_manager import TaskListSidecarManager  # pylint: disable=import-outside-toplevel
    from backend.app.services.yaml_service import get_yaml_service  # pylint: disable=import-outside-toplevel

    try:
        # Get project file path
        projects_dir = Path(settings.PROJECTS_DIR)
        filename = projects_dir / ProjectNameMapper.to_path(name) / "shapeshifter.yml"

        if not filename.exists():
            raise HTTPException(status_code=404, detail=f"Project not found: {name}")

        # Initialize sidecar manager
        yaml_service = get_yaml_service()
        sidecar_manager = TaskListSidecarManager(yaml_service)

        # Check if sidecar already exists
        if sidecar_manager.sidecar_exists(filename):
            logger.info(f"Sidecar already exists for '{name}' - skipping migration")
            return {
                "success": True,
                "project_name": name,
                "sidecar_path": str(sidecar_manager.get_sidecar_path(filename)),
                "migrated": False,
                "message": "Sidecar already exists - no migration needed",
            }

        # Load project data
        yaml_service = get_yaml_service()
        project_data = yaml_service.load(filename)

        # Check if task_list exists in main file
        if "task_list" not in project_data:
            logger.info(f"No task_list in main file for '{name}' - skipping migration")
            return {
                "success": True,
                "project_name": name,
                "sidecar_path": str(sidecar_manager.get_sidecar_path(filename)),
                "migrated": False,
                "message": "No task_list in main file - no migration needed",
            }

        # Perform migration
        sidecar_manager.save_task_list(filename, __import__("src.model", fromlist=["TaskList"]).TaskList(project_data.get("task_list", {})))

        # Update main project file (remove task_list)
        project_data_updated = dict(project_data)
        del project_data_updated["task_list"]
        yaml_service.save(project_data_updated, filename, create_backup=True)

        # Invalidate cache to force reload
        project_service = get_project_service()
        project_service.state.invalidate(name)

        logger.info(f"Successfully migrated task_list to sidecar for '{name}'")

        return {
            "success": True,
            "project_name": name,
            "sidecar_path": str(sidecar_manager.get_sidecar_path(filename)),
            "migrated": True,
            "message": "Task list successfully migrated to sidecar",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Migration failed for '{name}': {e}")
        raise HTTPException(status_code=500, detail=f"Migration failed: {str(e)}") from e


@router.get("/projects/{name}/tasks/sidecar/status", response_model=dict[str, Any])
@handle_endpoint_errors
async def get_sidecar_status(name: str) -> dict[str, Any]:
    """
    Get current sidecar status for task list.

    Checks whether task_list is stored in main project file or in separate sidecar file.
    Useful for monitoring migration state and determining next steps.

    Args:
        name: Project name

    Returns:
        Dict with sidecar status information

    Example:
        GET /api/v1/projects/my-project/tasks/sidecar/status

        Response (sidecar exists):
        {
          "success": true,
          "project_name": "my-project",
          "sidecar_exists": true,
          "sidecar_path": "/path/to/shapeshifter.tasks.yml",
          "task_list_location": "sidecar",
          "message": "Task list stored in sidecar file"
        }

        Response (in main file):
        {
          "success": true,
          "project_name": "my-project",
          "sidecar_exists": false,
          "task_list_location": "main_file",
          "message": "Task list stored in main project file"
        }
    """
    from pathlib import Path  # pylint: disable=import-outside-toplevel

    from backend.app.core.config import settings  # pylint: disable=import-outside-toplevel
    from backend.app.mappers.project_name_mapper import ProjectNameMapper  # pylint: disable=import-outside-toplevel
    from backend.app.services.task_list_sidecar_manager import TaskListSidecarManager  # pylint: disable=import-outside-toplevel
    from backend.app.services.yaml_service import get_yaml_service  # pylint: disable=import-outside-toplevel

    try:
        # Get project file path
        projects_dir = Path(settings.PROJECTS_DIR)
        filename = projects_dir / ProjectNameMapper.to_path(name) / "shapeshifter.yml"

        if not filename.exists():
            raise HTTPException(status_code=404, detail=f"Project not found: {name}")

        # Initialize sidecar manager
        yaml_service = get_yaml_service()
        sidecar_manager = TaskListSidecarManager(yaml_service)

        # Check sidecar status
        sidecar_path = sidecar_manager.get_sidecar_path(filename)
        sidecar_exists = sidecar_manager.sidecar_exists(filename)

        # Check main file for task_list
        project_data = yaml_service.load(filename)
        has_task_list_in_main = "task_list" in project_data

        # Determine current location
        if sidecar_exists:
            location = "sidecar"
            message = "Task list stored in sidecar file"
        elif has_task_list_in_main:
            location = "main_file"
            message = "Task list stored in main project file (migration recommended)"
        else:
            location = "none"
            message = "No task list found"

        logger.info(f"Sidecar status for '{name}': {location}")

        return {
            "success": True,
            "project_name": name,
            "sidecar_exists": sidecar_exists,
            "sidecar_path": str(sidecar_path),
            "task_list_location": location,
            "has_task_list_in_main": has_task_list_in_main,
            "message": message,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get sidecar status for '{name}': {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get sidecar status: {str(e)}") from e
