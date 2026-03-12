"""Service for managing entity task status and progress tracking."""

from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd
from loguru import logger

from backend.app.exceptions import ResourceNotFoundError
from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.mappers.project_name_mapper import ProjectNameMapper
from backend.app.models.project import Project
from backend.app.models.task import EntityTaskStatus, ProjectTaskStatus, TaskPriority, TaskStatus
from backend.app.models.validation import ValidationError, ValidationResult
from backend.app.services.dependency_service import get_dependency_service
from backend.app.services.project_service import ProjectService, get_project_service
from backend.app.services.shapeshift_service import ShapeShiftService, get_shapeshift_service
from backend.app.services.task_list_sidecar_manager import TaskListSidecarManager
from backend.app.services.validation_service import ValidationService, get_validation_service
from src.model import ShapeShiftProject, TableConfig, TaskList


class TaskService:
    """Service for managing entity task status and progress tracking."""

    def __init__(
        self,
        project_service: ProjectService | None = None,
        validation_service: ValidationService | None = None,
        shapeshift_service: ShapeShiftService | None = None,
        sidecar_manager: TaskListSidecarManager | None = None,
    ):
        """Initialize task service with dependencies."""

        self.project_service: ProjectService = project_service or get_project_service()
        self.validation_service: ValidationService = validation_service or get_validation_service()
        self.shapeshift_service: ShapeShiftService = shapeshift_service or get_shapeshift_service()
        self.sidecar_manager: TaskListSidecarManager = sidecar_manager or TaskListSidecarManager()

    def _refresh_project_task_list(self, project_name: str, project: ShapeShiftProject) -> None:
        """Refresh task state from sidecar without touching cached project state.

        Task workflow is stored in a sidecar file and should remain independent from the
        main project editing flow. This method overlays the latest sidecar task_list onto
        the core project used for task computations only.
        """
        try:
            project_file_path = self._get_project_file_path(project_name)
        except Exception as exc:  # pylint: disable=broad-except
            logger.debug(f"Skipping task sidecar refresh for '{project_name}': {exc}")
            return

        if not self.sidecar_manager.sidecar_exists(project_file_path):
            return

        project.cfg["task_list"] = self.sidecar_manager.load_task_list(project_file_path)
        project.__dict__.pop("task_list", None)

    def _get_project_file_path(self, project_name: str) -> Path:
        """
        Get shapeshifter.yml file path from project name.

        Args:
            project_name: Name of the project

        Returns:
            Path to project file

        Raises:
            ResourceNotFoundError: If project file doesn't exist
        """
        project_file_path = self.project_service.projects_dir / ProjectNameMapper.to_path(project_name) / "shapeshifter.yml"

        # Validate project file exists
        if not project_file_path.exists():
            raise ResourceNotFoundError(
                message=f"Project '{project_name}' not found",
                resource_type="project",
                resource_id=project_name,
            )

        return project_file_path

    async def compute_status(self, project_name: str) -> ProjectTaskStatus:
        """
        Compute full task status for all entities in project.

        Combines stored task list state with derived state from validation
        and preview availability to provide complete status for each entity.

        Args:
            project_name: Name of the project

        Returns:
            ProjectTaskStatus with all entity statuses and completion stats

        Raises:
            ValueError: If project not found
        """
        # Load project (API layer)
        api_project: Project = self.project_service.load_project(project_name)

        # Convert to core layer for task_list access
        project: ShapeShiftProject = ProjectMapper.to_core(api_project)
        self._refresh_project_task_list(project_name, project)

        # Get validation results for all entities
        validation_result: ValidationResult = await self.validation_service.validate_project_data(project_name)

        # Build status for all entities (existing + required but missing)
        entity_statuses: dict[str, EntityTaskStatus] = {}

        # Track all entity names we need to consider (existing + todo/done/ongoing)
        all_entity_names: set[str] = (
            set(project.table_names)
            | set(project.task_list.todo)
            | set(project.task_list.done)
            | set(project.task_list.ongoing)
            | set(project.task_list.ignored)
        )

        for entity_name in all_entity_names:
            entity_status = await self._compute_entity_status(
                project=project,
                project_name=project_name,
                entity_name=entity_name,
                validation_result=validation_result,
            )
            entity_statuses[entity_name] = entity_status

        # Calculate completion statistics
        stats = self._calculate_stats(entity_statuses, project.task_list.required_entities)

        return ProjectTaskStatus(entities=entity_statuses, completion_stats=stats)

    async def _compute_entity_status(
        self,
        project: ShapeShiftProject,
        project_name: str,
        entity_name: str,
        validation_result: ValidationResult,
    ) -> EntityTaskStatus:
        """Compute status for a single entity."""

        # Check if entity exists
        exists: bool = project.has_table(entity_name)

        # Determine base status (from task_list)
        # Priority order: done > ongoing > ignored > todo (explicit or implicit)
        if project.task_list.is_done(entity_name):
            status: TaskStatus = TaskStatus.DONE
        elif project.task_list.is_ongoing(entity_name):
            status = TaskStatus.ONGOING
        elif project.task_list.is_ignored(entity_name):
            status = TaskStatus.IGNORED
        elif project.task_list.is_todo(entity_name):
            # Explicitly marked as todo
            status = TaskStatus.TODO
        elif exists:
            # Entity exists but not explicitly marked - default to ONGOING
            status = TaskStatus.ONGOING
        else:
            # Entity doesn't exist and not marked - default to TODO
            status = TaskStatus.TODO

        # Check if required
        required: bool = project.task_list.is_required(entity_name)

        # Get validation status
        validation_passed: bool = True
        validation_issues: list[str] = []

        if exists:
            # Check for structural errors
            entity_errors: list[ValidationError] = [err for err in validation_result.errors if err.entity == entity_name]
            if entity_errors:
                validation_passed = False
                validation_issues = [err.message for err in entity_errors]
        else:
            validation_passed = False
            validation_issues = ["Entity not created yet"]

        # Check preview availability (only if entity exists and passes validation)
        preview_available = False
        if exists and validation_passed:
            try:
                # Check if preview is cached (fast check without triggering normalization)
                # Use 4-tier fallback strategy to avoid false negatives from version mismatches
                # that can occur if ApplicationState gets initialized between preview generation
                # and task status check.
                table_cfg: TableConfig = project.get_table(entity_name)
                project_version: int = self.shapeshift_service.get_project_version(project_name)

                entity_hash_str = table_cfg.hash()[:8] if table_cfg else "N/A"
                logger.trace(
                    f"[CACHE_LOOKUP_STRICT] {project_name}/{entity_name}: project_version={project_version}, "
                    f"entity_hash={entity_hash_str}"
                )

                # Tier 1: Strict lookup with version + hash
                cached_df: pd.DataFrame | None = self.shapeshift_service.cache.get_dataframe(
                    project_name=project_name,
                    entity_name=entity_name,
                    project_version=project_version,
                    entity_config=table_cfg,
                    strict_version=True,
                )

                if cached_df is None:
                    # Tier 2: Skip entity hash (config might differ between code paths)
                    logger.trace(
                        f"[CACHE_LOOKUP_FALLBACK_HASH] {project_name}/{entity_name}: " f"project_version={project_version} (no entity hash)"
                    )
                    cached_df = self.shapeshift_service.cache.get_dataframe(
                        project_name=project_name,
                        entity_name=entity_name,
                        project_version=project_version,
                        strict_version=True,
                    )

                if cached_df is None:
                    # Tier 3: Skip version check (might differ if ApplicationState initialized between calls)
                    logger.trace(
                        f"[CACHE_LOOKUP_FALLBACK_VERSION] {project_name}/{entity_name}: "
                        f"skipping version check (ApplicationState timing sensitivity)"
                    )
                    cached_df = self.shapeshift_service.cache.get_dataframe(
                        project_name=project_name,
                        entity_name=entity_name,
                        project_version=None,
                        entity_config=None,
                        strict_version=False,
                    )

                if cached_df is not None:
                    # Cache exists and is valid
                    preview_available = True
                    logger.trace(f"[CACHE_HIT] {project_name}/{entity_name}: preview available from cache")
                else:
                    # Cache miss or stale - skip expensive preview generation for task status
                    # Task status endpoint should be fast; preview will be generated on-demand when user views entity
                    preview_available = False
                    logger.trace(f"[CACHE_MISS] {project_name}/{entity_name}: skipping preview generation (cache miss)")
            except Exception as e:  # pylint: disable=broad-except
                logger.trace(f"[CACHE_ERROR] {project_name}/{entity_name}: {e}")
                preview_available = False

        # Determine blocked_by (dependencies that aren't done)
        blocked_by: list[str] = []
        if exists:
            table_cfg: TableConfig = project.get_table(entity_name)

            # Check depends_on entities
            for dep_name in table_cfg.depends_on:
                if not project.task_list.is_completed(dep_name):
                    # Check if dependency has issues
                    dep_errors: list[ValidationError] = [err for err in validation_result.errors if err.entity == dep_name]
                    if dep_errors or not project.has_table(dep_name):
                        blocked_by.append(dep_name)

            # Check foreign key parent entities
            for fk in table_cfg.foreign_keys:
                remote_entity = fk.remote_entity
                if not project.task_list.is_completed(remote_entity):
                    remote_errors: list[ValidationError] = [err for err in validation_result.errors if err.entity == remote_entity]
                    if remote_errors or not project.has_table(remote_entity):
                        blocked_by.append(remote_entity)

        # Determine priority
        priority: TaskPriority = self._determine_priority(
            required=required,
            validation_passed=validation_passed,
            preview_available=preview_available,
            blocked_by=blocked_by,
            exists=exists,
            status=status,
        )

        # Get flagged status
        flagged: bool = project.task_list.is_flagged(entity_name)

        return EntityTaskStatus(
            status=status,
            priority=priority,
            required=required,
            exists=exists,
            validation_passed=validation_passed,
            preview_available=preview_available,
            flagged=flagged,
            blocked_by=list(set(blocked_by)),  # Remove duplicates
            issues=validation_issues,
        )

    def _determine_priority(
        self,
        required: bool,
        validation_passed: bool,
        preview_available: bool,
        blocked_by: list[str],
        exists: bool,
        status: TaskStatus,
    ) -> TaskPriority:
        """Determine priority based on entity state."""

        # Ignored entities are always optional priority
        if status == TaskStatus.IGNORED:
            return TaskPriority.OPTIONAL

        # Critical: Required entity with problems
        if required:
            if not exists:
                return TaskPriority.CRITICAL
            if not validation_passed or not preview_available:
                return TaskPriority.CRITICAL

        # Ready: All dependencies met, validation passes
        if exists and validation_passed and preview_available and not blocked_by:
            return TaskPriority.READY

        # Waiting: Has incomplete dependencies
        if blocked_by:
            return TaskPriority.WAITING

        # Optional: Everything else
        return TaskPriority.OPTIONAL

    def _calculate_stats(
        self,
        entity_statuses: dict[str, EntityTaskStatus],
        required_entities: list[str],
    ) -> dict[str, int | float]:
        """Calculate completion statistics."""
        total = len(entity_statuses)
        done = sum(1 for s in entity_statuses.values() if s.status == TaskStatus.DONE)
        ongoing = sum(1 for s in entity_statuses.values() if s.status == TaskStatus.ONGOING)
        ignored = sum(1 for s in entity_statuses.values() if s.status == TaskStatus.IGNORED)
        todo = total - done - ongoing - ignored
        flagged = sum(1 for s in entity_statuses.values() if s.flagged)
        completion_percentage = (done / total * 100.0) if total > 0 else 0.0

        required_total = len(required_entities)
        required_done = sum(1 for name in required_entities if name in entity_statuses and entity_statuses[name].status == TaskStatus.DONE)
        required_ongoing = sum(
            1 for name in required_entities if name in entity_statuses and entity_statuses[name].status == TaskStatus.ONGOING
        )
        required_todo = required_total - required_done - required_ongoing

        return {
            "total": total,
            "done": done,
            "ongoing": ongoing,
            "todo": todo,
            "ignored": ignored,
            "flagged": flagged,
            "completion_percentage": completion_percentage,
            "required_total": required_total,
            "required_done": required_done,
            "required_ongoing": required_ongoing,
            "required_todo": required_todo,
        }

    async def mark_complete(self, project_name: str, entity_name: str) -> dict[str, Any]:
        """
        Mark entity as complete.

        Validates that entity passes validation and has preview data before
        marking as done.

        Args:
            project_name: Name of the project
            entity_name: Name of entity to mark as done

        Returns:
            Dict with success status and message

        Raises:
            ValueError: If entity doesn't exist or fails validation
        """
        # Quick validation: check entity exists (load project for this check only)
        api_project: Project = self.project_service.load_project(project_name)
        project: ShapeShiftProject = ProjectMapper.to_core(api_project)

        if not project.has_table(entity_name):
            raise ValueError(f"Entity '{entity_name}' does not exist in project")

        # Validate entity
        validation_result: ValidationResult = await self.validation_service.validate_project_data(project_name, entity_names=[entity_name])

        if not validation_result.is_valid:
            error_messages: list[str] = [err.message for err in validation_result.errors]
            raise ValueError(
                f"Cannot mark entity as done: validation failed with {len(error_messages)} error(s): " + "; ".join(error_messages[:3])
            )

        # Check preview availability
        try:
            await self.shapeshift_service.preview_entity(project_name=project_name, entity_name=entity_name, limit=1)
        except Exception as e:
            raise ValueError(f"Cannot mark entity as done: preview generation failed: {str(e)}") from e

        # Update task_list in sidecar directly (no need to save entire project)
        project_file_path = self._get_project_file_path(project_name)
        task_list_data = self.sidecar_manager.load_task_list(project_file_path)
        task_list = TaskList(task_list_data or {})
        task_list.mark_completed(entity_name)
        self.sidecar_manager.save_task_list(project_file_path, task_list)

        return {
            "success": True,
            "entity_name": entity_name,
            "status": "done",
            "message": "Entity marked as completed",
        }

    async def mark_ignored(self, project_name: str, entity_name: str) -> dict[str, Any]:
        """
        Mark entity as ignored.

        Args:
            project_name: Name of the project
            entity_name: Name of entity to ignore

        Returns:
            Dict with success status and message
        """
        # Update task_list in sidecar directly
        project_file_path = self._get_project_file_path(project_name)
        task_list_data = self.sidecar_manager.load_task_list(project_file_path)
        task_list = TaskList(task_list_data or {})
        task_list.mark_ignored(entity_name)
        self.sidecar_manager.save_task_list(project_file_path, task_list)

        return {
            "success": True,
            "entity_name": entity_name,
            "status": "ignored",
            "message": "Entity marked as ignored",
        }

    async def reset_status(self, project_name: str, entity_name: str) -> dict[str, Any]:
        """
        Reset entity status to todo.

        Args:
            project_name: Name of the project
            entity_name: Name of entity to reset

        Returns:
            Dict with success status and message
        """
        # Update task_list in sidecar directly
        project_file_path = self._get_project_file_path(project_name)
        task_list_data = self.sidecar_manager.load_task_list(project_file_path)
        task_list = TaskList(task_list_data or {})
        task_list.reset_status(entity_name)
        self.sidecar_manager.save_task_list(project_file_path, task_list)

        return {
            "success": True,
            "entity_name": entity_name,
            "status": "todo",
            "message": "Entity status reset to todo",
        }

    async def mark_ongoing(self, project_name: str, entity_name: str) -> dict[str, Any]:
        """
        Mark entity as ongoing.

        Args:
            project_name: Name of the project
            entity_name: Name of entity to mark as ongoing

        Returns:
            Dict with success status and message
        """
        # Update task_list in sidecar directly
        project_file_path = self._get_project_file_path(project_name)
        task_list_data = self.sidecar_manager.load_task_list(project_file_path)
        task_list = TaskList(task_list_data or {})
        task_list.mark_ongoing(entity_name)
        self.sidecar_manager.save_task_list(project_file_path, task_list)

        return {
            "success": True,
            "entity_name": entity_name,
            "status": "ongoing",
            "message": "Entity marked as ongoing",
        }

    async def mark_todo(self, project_name: str, entity_name: str) -> dict[str, Any]:
        """
        Mark entity as todo (planned but not yet created).

        Args:
            project_name: Name of the project
            entity_name: Name of entity to mark as todo

        Returns:
            Dict with success status and message
        """
        # Update task_list in sidecar directly
        project_file_path = self._get_project_file_path(project_name)
        task_list_data = self.sidecar_manager.load_task_list(project_file_path)
        task_list = TaskList(task_list_data or {})
        task_list.mark_todo(entity_name)
        self.sidecar_manager.save_task_list(project_file_path, task_list)

        return {
            "success": True,
            "entity_name": entity_name,
            "status": "todo",
            "message": "Entity marked as todo",
        }

    async def toggle_flagged(self, project_name: str, entity_name: str) -> dict[str, Any]:
        """
        Toggle flagged status for an entity.

        Args:
            project_name: Name of the project
            entity_name: Name of entity to toggle

        Returns:
            Dict with success status and new flagged state
        """
        # Update task_list in sidecar directly
        project_file_path = self._get_project_file_path(project_name)
        task_list_data = self.sidecar_manager.load_task_list(project_file_path)
        task_list = TaskList(task_list_data or {})
        new_state = task_list.toggle_flagged(entity_name)
        self.sidecar_manager.save_task_list(project_file_path, task_list)

        return {
            "success": True,
            "entity_name": entity_name,
            "flagged": new_state,
            "message": f"Entity {'flagged' if new_state else 'unflagged'}",
        }

    async def initialize_task_list(
        self,
        project_name: str,
        strategy: str = "dependency-order",
    ) -> dict[str, Any]:
        """
        Initialize task list based on project structure.

        Args:
            project_name: Name of the project
            strategy: Initialization strategy:
                - "all": Include all entities
                - "required-only": Include only entities with foreign keys (derived data)
                - "dependency-order": Include all, sorted by dependency order (default)

        Returns:
            Dict with success status and initialized task list details

        Raises:
            ValueError: If project not found or invalid strategy
        """

        valid_strategies = {"all", "required-only", "dependency-order"}
        if strategy not in valid_strategies:
            raise ValueError(f"Invalid strategy '{strategy}'. Must be one of: {valid_strategies}")

        # Load project (API layer)
        api_project: Project = self.project_service.load_project(project_name)

        # Convert to core layer
        project: ShapeShiftProject = ProjectMapper.to_core(api_project)

        entity_names = list(project.tables.keys())
        required_entities: list[str] = []

        if strategy == "all":
            required_entities = entity_names

        elif strategy == "required-only":
            # Include only entities with foreign keys (derived from other data)
            for name, table in project.tables.items():
                if table.foreign_keys:
                    required_entities.append(name)

        elif strategy == "dependency-order":
            # Get topologically sorted entities from dependency graph
            try:
                dep_service = get_dependency_service()
                graph = dep_service.analyze_dependencies(api_project)

                # Use topological order if available
                if graph.get("topological_order"):
                    required_entities = graph["topological_order"]
                else:
                    # Fallback to all entities
                    required_entities = entity_names
            except Exception as e:  # pylint: disable=broad-except
                logger.warning(f"Failed to get dependency order: {e}. Using all entities.")
                required_entities = entity_names

        # Initialize task list
        project.cfg["task_list"] = {
            "required_entities": required_entities,
            "completed": [],
            "ignored": [],
        }

        # Convert back to API layer and save
        updated_api_project: Project = ProjectMapper.to_api_config(project.cfg, project_name)
        self.project_service.save_project(updated_api_project)

        logger.info(
            f"Initialized task list for '{project_name}' with strategy '{strategy}': " f"{len(required_entities)} required entities"
        )

        return {
            "success": True,
            "strategy": strategy,
            "required_entities": required_entities,
            "message": f"Task list initialized with {len(required_entities)} entities",
        }


@lru_cache
def get_task_service() -> TaskService:
    """Get singleton task service instance."""
    return TaskService()
