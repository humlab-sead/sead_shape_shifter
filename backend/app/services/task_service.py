"""Service for managing entity task status and progress tracking."""

from functools import lru_cache
from typing import Any

import pandas as pd
from loguru import logger

from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.models.project import Project
from backend.app.models.task import EntityTaskStatus, ProjectTaskStatus, TaskPriority, TaskStatus
from backend.app.models.validation import ValidationError, ValidationResult
from backend.app.services.dependency_service import get_dependency_service
from backend.app.services.project_service import ProjectService, get_project_service
from backend.app.services.shapeshift_service import ShapeShiftService, get_shapeshift_service
from backend.app.services.validation_service import ValidationService, get_validation_service
from src.model import ShapeShiftProject, TableConfig


class TaskService:
    """Service for managing entity task status and progress tracking."""

    def __init__(
        self,
        project_service: ProjectService | None = None,
        validation_service: ValidationService | None = None,
        shapeshift_service: ShapeShiftService | None = None,
    ):
        """Initialize task service with dependencies."""

        self.project_service: ProjectService = project_service or get_project_service()
        self.validation_service: ValidationService = validation_service or get_validation_service()
        self.shapeshift_service: ShapeShiftService = shapeshift_service or get_shapeshift_service()

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

        # Get validation results for all entities
        validation_result: ValidationResult = await self.validation_service.validate_project_data(project_name)

        # Build status for all entities (existing + required but missing)
        entity_statuses: dict[str, EntityTaskStatus] = {}

        # Track all entity names we need to consider
        all_entity_names: set[str] = set(project.table_names) | set(project.task_list.required_entities)

        for entity_name in all_entity_names:
            entity_status = await self._compute_entity_status(
                project=project,
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
        entity_name: str,
        validation_result: ValidationResult,
    ) -> EntityTaskStatus:
        """Compute status for a single entity."""

        # Check if entity exists
        exists: bool = project.has_table(entity_name)

        # Determine base status (from task_list)
        if project.task_list.is_completed(entity_name):
            status: TaskStatus = TaskStatus.DONE
        elif project.task_list.is_ignored(entity_name):
            status = TaskStatus.IGNORED
        else:
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
                # Use get_dataframe which does TTL + version + hash validation but doesn't generate data
                table_cfg: TableConfig = project.get_table(entity_name)
                project_version: int = self.shapeshift_service.get_project_version(project.filename)
                cached_df: pd.DataFrame | None = self.shapeshift_service.cache.get_dataframe(
                    project_name=project.filename,
                    entity_name=entity_name,
                    project_version=project_version,
                    entity_config=table_cfg,
                )

                if cached_df is not None:
                    # Cache exists and is valid
                    preview_available = True
                    logger.debug(f"Preview available for {entity_name} (from cache)")
                else:
                    # Cache miss or stale - skip expensive preview generation for task status
                    # Task status endpoint should be fast; preview will be generated on-demand when user views entity
                    preview_available = False
                    logger.debug(f"Skipping preview generation for {entity_name} in task status (cache miss)")
            except Exception as e:  # pylint: disable=broad-except
                logger.debug(f"Preview check failed for {entity_name}: {e}")
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

        return EntityTaskStatus(
            status=status,
            priority=priority,
            required=required,
            exists=exists,
            validation_passed=validation_passed,
            preview_available=preview_available,
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
    ) -> dict[str, int]:
        """Calculate completion statistics."""
        total = len(entity_statuses)
        done = sum(1 for s in entity_statuses.values() if s.status == TaskStatus.DONE)
        ignored = sum(1 for s in entity_statuses.values() if s.status == TaskStatus.IGNORED)
        todo = total - done - ignored

        required_total = len(required_entities)
        required_done = sum(1 for name in required_entities if name in entity_statuses and entity_statuses[name].status == TaskStatus.DONE)
        required_todo = required_total - required_done

        return {
            "total": total,
            "done": done,
            "todo": todo,
            "ignored": ignored,
            "required_total": required_total,
            "required_done": required_done,
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
        # Load project (API layer)
        api_project: Project = self.project_service.load_project(project_name)

        # Convert to core layer for task_list access
        project: ShapeShiftProject = ProjectMapper.to_core(api_project)

        # Check entity exists
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
            await self.shapeshift_service.preview_entity(project_name=project.filename, entity_name=entity_name, limit=1)
        except Exception as e:
            raise ValueError(f"Cannot mark entity as done: preview generation failed: {str(e)}") from e

        # Mark as completed (modifies core model)
        project.task_list.mark_completed(entity_name)

        # Convert back to API layer and save
        updated_api_project: Project = ProjectMapper.to_api_config(project.cfg, project_name)
        self.project_service.save_project(updated_api_project)

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
        # Load project (API layer)
        api_project: Project = self.project_service.load_project(project_name)

        # Convert to core layer for task_list access
        project: ShapeShiftProject = ProjectMapper.to_core(api_project)

        # Mark as ignored (doesn't require validation)
        project.task_list.mark_ignored(entity_name)

        # Convert back to API layer and save
        updated_api_project: Project = ProjectMapper.to_api_config(project.cfg, project_name)
        self.project_service.save_project(updated_api_project)

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
        # Load project (API layer)
        api_project: Project = self.project_service.load_project(project_name)

        # Convert to core layer for task_list access
        project: ShapeShiftProject = ProjectMapper.to_core(api_project)

        # Reset status
        project.task_list.reset_status(entity_name)

        # Convert back to API layer and save
        updated_api_project: Project = ProjectMapper.to_api_config(project.cfg, project_name)
        self.project_service.save_project(updated_api_project)

        return {
            "success": True,
            "entity_name": entity_name,
            "status": "todo",
            "message": "Entity status reset to todo",
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
