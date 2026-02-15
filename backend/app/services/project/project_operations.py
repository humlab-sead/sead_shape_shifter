"""Project operations: create, copy, delete, update metadata."""

import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Any

from loguru import logger

from backend.app.exceptions import ConfigurationError, ResourceConflictError, ResourceNotFoundError
from backend.app.middleware.correlation import get_correlation_id
from backend.app.models.project import Project, ProjectMetadata

if TYPE_CHECKING:
    from backend.app.core.state_manager import ApplicationStateManager
    from backend.app.services.yaml_service import YamlService


class ProjectServiceError(Exception):
    """Generic exception for unexpected project service errors."""


class ProjectOperations:
    """Handles project-level operations: create, delete, copy, update metadata.
    
    This component is responsible for managing the lifecycle of entire projects,
    as opposed to individual entities within projects.
    """

    def __init__(
        self,
        yaml_service: "YamlService",
        projects_dir: Path,
        state: "ApplicationStateManager",
        project_lock_getter,  # Callable[[str], threading.Lock]
        project_lock_remover,  # Callable[[str], None]
        save_project_callback,  # Callable to save project
        load_project_callback,  # Callable to load project
        cache_invalidator,  # Callable[[str, str], None]
    ):
        """Initialize project operations.
        
        Args:
            yaml_service: YAML service for config management
            projects_dir: Base directory for all projects
            state: Application state manager
            project_lock_getter: Function to get per-project lock
            project_lock_remover: Function to remove per-project lock
            save_project_callback: Function to save project
            load_project_callback: Function to load project
            cache_invalidator: Function to invalidate all caches
        """
        self.yaml_service = yaml_service
        self.projects_dir = projects_dir
        self.state = state
        self._get_lock = project_lock_getter
        self._remove_lock = project_lock_remover
        self._save_project = save_project_callback
        self._load_project = load_project_callback
        self._invalidate_all_caches = cache_invalidator

    def create_project(
        self, name: str, entities: dict[str, Any] | None = None, task_list: dict[str, Any] | None = None
    ) -> Project:
        """
        Create new project.

        Args:
            name: Project name (can include path separators for nested projects, e.g., 'arbodat/new-test')
            entities: Optional initial entities
            task_list: Optional task list configuration

        Returns:
            New project

        Raises:
            ResourceConflictError: If project already exists
        """
        corr: str = get_correlation_id()
        # New structure: projects_dir/name/shapeshifter.yml
        file_path: Path = self.projects_dir / name / "shapeshifter.yml"

        if file_path.exists():
            raise ResourceConflictError(resource_type="project", resource_id=name, message=f"Project '{name}' already exists")

        # Defensive: clear any stale caches for this name (e.g. after delete+recreate)
        self._invalidate_all_caches(name, corr)
        logger.info("[{}] create_project: '{}'", corr, name)

        metadata: ProjectMetadata = ProjectMetadata(
            name=name,
            description=f"Project for {name}",
            version="1.0.0",
            file_path=str(file_path),
            entity_count=len(entities) if entities else 0,
            created_at=0,
            modified_at=0,
            is_valid=True,
            type="shapeshifter-project",
        )

        project: Project = Project(entities=entities or {}, options={}, task_list=task_list, metadata=metadata)

        return self._save_project(project, create_backup=False)

    def delete_project(self, name: str) -> None:
        """
        Delete project directory and all its contents.

        Clears ALL caches (ApplicationState, ShapeShiftCache, ShapeShiftProjectCache)
        to prevent ghost entities when a new project is created with the same name.

        Args:
            name: Project name (can include path separators for nested projects)

        Raises:
            ResourceNotFoundError: If project not found
        """
        corr: str = get_correlation_id()
        # Structure: projects_dir/name/shapeshifter.yml
        project_dir: Path = self.projects_dir / name
        file_path: Path = project_dir / "shapeshifter.yml"

        if not file_path.exists():
            raise ResourceNotFoundError(resource_type="project", resource_id=name, message=f"Project not found: {name}")

        lock = self._get_lock(name)
        logger.info("[{}] delete_project: ACQUIRING lock for '{}'", corr, name)

        with lock:
            logger.info("[{}] delete_project: ACQUIRED lock for '{}'", corr, name)
            try:
                # Backup the main config file before deletion
                self.yaml_service.create_backup(file_path)
                # Delete entire project directory
                shutil.rmtree(project_dir)
                logger.info("[{}] delete_project: directory deleted for '{}'", corr, name)

            except Exception as e:
                logger.error("[{}] delete_project: failed to delete file for '{}': {}", corr, name, e)
                raise ProjectServiceError(f"Failed to delete project: {e}") from e

            # CRITICAL FIX: Clear ALL caches to prevent ghost entities
            self._invalidate_all_caches(name, corr)

        # Clean up the lock after releasing it
        self._remove_lock(name)
        logger.info("[{}] delete_project: completed for '{}'", corr, name)

    def copy_project(self, source_name: str, target_name: str) -> Project:
        """
        Copy a project and its entire directory to a new name.

        Copies entire project directory including:
        - shapeshifter.yml with updated metadata.name
        - reconciliation.yml (if exists)
        - translations.tsv (if exists)
        - backups/ (if exists)
        - Any other project-specific files

        Args:
            source_name: Source project name (can include path separators)
            target_name: Target project name (can include path separators)

        Returns:
            New project with updated metadata

        Raises:
            ResourceNotFoundError: If source project not found
            ResourceConflictError: If target project already exists
            ProjectServiceError: If copy fails
        """
        # New structure: projects_dir/name/shapeshifter.yml
        source_dir: Path = self.projects_dir / source_name
        target_dir: Path = self.projects_dir / target_name
        source_file: Path = source_dir / "shapeshifter.yml"
        target_file: Path = target_dir / "shapeshifter.yml"

        # Validate source exists
        if not source_file.exists():
            raise ResourceNotFoundError(
                resource_type="project", resource_id=source_name, message=f"Source project not found: {source_name}"
            )

        # Validate target doesn't exist
        if target_file.exists():
            raise ResourceConflictError(
                resource_type="project", resource_id=target_name, message=f"Target project already exists: {target_name}"
            )

        try:
            # Load source project
            source_project: Project = self._load_project(source_name)

            # Copy entire project directory
            logger.info(f"Copying project directory from {source_dir} to {target_dir}")
            shutil.copytree(source_dir, target_dir)

            # Update metadata for target
            if source_project.metadata:
                # Extract just the final part of the name for description update
                source_simple_name: str = source_name.split("/")[-1]
                target_simple_name: str = target_name.split("/")[-1]
                updated_description: str | None = (
                    source_project.metadata.description.replace(source_simple_name, target_simple_name)
                    if source_project.metadata.description
                    else None
                )
                source_project.metadata = source_project.metadata.model_copy(
                    update={"name": target_name, "description": updated_description}
                )

            # Save updated metadata to target project
            logger.info(f"Updating metadata for copied project '{target_name}'")
            new_project: Project = self._save_project(source_project, create_backup=False, original_file_path=target_file)

            logger.info(f"Successfully copied project '{source_name}' to '{target_name}'")
            return new_project

        except (ResourceNotFoundError, ResourceConflictError, ConfigurationError):
            # Re-raise domain exceptions as-is
            raise
        except Exception as e:
            # Clean up partial copies on failure
            logger.error(f"Failed to copy project '{source_name}' to '{target_name}': {e}")

            if target_dir.exists():
                shutil.rmtree(target_dir)

            raise ProjectServiceError(f"Failed to copy project: {e}") from e

    def update_metadata(
        self,
        name: str,
        new_name: str | None = None,  # pylint: disable=unused-argument
        description: str | None = None,
        version: str | None = None,
        default_entity: str | None = None,
    ) -> Project:
        """
        Update project metadata.

        Note: new_name parameter is ignored - use rename_project() instead.
        The filename is the authoritative source for project name.

        Args:
            name: Current project name (derived from filename)
            new_name: Ignored (use rename_project instead)
            description: Project description (optional)
            version: Project version (optional)
            default_entity: Default entity name (optional)

        Returns:
            Updated project

        Raises:
            ProjectNotFoundError: If project not found
        """
        # Load current project
        project: Project = self._load_project(name)

        if not project.metadata:
            raise ConfigurationError(message=f"Project '{name}' has no metadata")

        # Determine original file path to preserve filename
        original_file_path: Path = self.projects_dir / name / "shapeshifter.yml"

        # Update metadata fields (only if provided, ignore new_name)
        if description is not None:
            project.metadata.description = description
        if version is not None:
            project.metadata.version = version
        if default_entity is not None:
            project.metadata.default_entity = default_entity

        # Ensure metadata.name matches filename (filename is source of truth)
        project.metadata.name = name

        # Save project using original file path to prevent duplicate files
        saved_config: Project = self._save_project(project, create_backup=True, original_file_path=original_file_path)

        return saved_config
