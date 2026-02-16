"""Project service for managing entities."""

import threading
from pathlib import Path
from typing import Any, Iterable

from fastapi import UploadFile
from loguru import logger

from backend.app.core.config import settings
from backend.app.core.state_manager import ApplicationStateManager, get_app_state_manager
from backend.app.exceptions import ConfigurationError, ResourceConflictError, ResourceNotFoundError
from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.middleware.correlation import get_correlation_id
from backend.app.models.entity import Entity
from backend.app.models.project import Project, ProjectFileInfo, ProjectMetadata
from backend.app.services.project.entity_operations import EntityOperations
from backend.app.services.project.file_manager import FileManager
from backend.app.services.project.project_operations import ProjectOperations
from backend.app.services.project.project_utils import ProjectUtils
from backend.app.services.yaml_service import YamlLoadError, YamlSaveError, YamlService, get_yaml_service


class ProjectYamlSpecification:
    """Specification for project files."""

    def is_satisfied_by(self, data: dict[str, Any]) -> bool:
        metadata = (data or {}).get("metadata", {})
        return "type" in metadata


class ProjectService:
    """Service for managing project files and entities.

    Thread safety:
        All mutating operations (add/update/delete entity, save/delete project)
        are serialized per-project using threading.Lock to prevent lost-update
        race conditions when concurrent requests modify the same project.

    Cache consistency:
        load_project() returns deep copies of cached projects to prevent
        mutation-through-reference bugs.
    """

    # Class-level locks for per-project serialization
    _project_locks: dict[str, threading.Lock] = {}
    _locks_lock: threading.Lock = threading.Lock()

    @classmethod
    def _get_lock(cls, project_name: str) -> threading.Lock:
        """Get or create a per-project lock. Thread-safe."""
        with cls._locks_lock:
            if project_name not in cls._project_locks:
                cls._project_locks[project_name] = threading.Lock()
            return cls._project_locks[project_name]

    @classmethod
    def _remove_lock(cls, project_name: str) -> None:
        """Remove a project's lock (called after project deletion)."""
        with cls._locks_lock:
            cls._project_locks.pop(project_name, None)

    def __init__(self, projects_dir: Path | None = None, state: ApplicationStateManager | None = None) -> None:
        """Initialize project service."""
        self.yaml_service: YamlService = get_yaml_service()
        self.projects_dir: Path = Path(projects_dir or settings.PROJECTS_DIR)
        self.specification = ProjectYamlSpecification()
        self.state: ApplicationStateManager = state or get_app_state_manager()

        # Initialize project utilities component
        self.utils = ProjectUtils(projects_dir=self.projects_dir)

        # Initialize project operations component
        self.operations = ProjectOperations(
            yaml_service=self.yaml_service,
            projects_dir=self.projects_dir,
            state=self.state,
            project_lock_getter=self._get_lock,
            project_lock_remover=self._remove_lock,
            save_project_callback=self.save_project,
            load_project_callback=self.load_project,
            cache_invalidator=self._invalidate_all_caches,
        )

        # Initialize entity operations component
        self.entities = EntityOperations(
            project_lock_getter=self._get_lock,
            load_project_callback=self.load_project,
            save_project_callback=self.save_project,
        )

        # Initialize file manager component
        self.files = FileManager(
            projects_dir=self.projects_dir,
            sanitize_project_name_callback=self.utils.sanitize_project_name,
            ensure_project_exists_callback=self.utils.ensure_project_exists,
        )

    @staticmethod
    def _name_to_path(name: str) -> str:
        """Convert API project name to filesystem path.

        Replaces ':' with '/' to support nested projects in API while
        using standard directory separators on disk.

        Example: 'arbodat:arbodat-copy' -> 'arbodat/arbodat-copy'
        """
        return name.replace(":", "/")

    @staticmethod
    def _path_to_name(path: str) -> str:
        """Convert filesystem path to API project name.

        Replaces '/' with ':' to avoid URL path parsing issues.

        Example: 'arbodat/arbodat-copy' -> 'arbodat:arbodat-copy'
        """
        return path.replace("/", ":")

    def list_projects(self) -> list[ProjectMetadata]:
        """
        List all available project files.

        Recursively discovers shapeshifter.yml files in the projects directory.
        Project names are derived from relative paths (e.g., 'arbodat/arbodat-test').

        Returns:
            List of project metadata
        """
        if not self.projects_dir.exists():
            logger.warning(f"Projects directory does not exist: {self.projects_dir}")
            return []

        configs: list[ProjectMetadata] = []

        # Recursively find all shapeshifter.yml files
        for yaml_file in self.projects_dir.rglob("shapeshifter.yml"):
            try:
                data: dict[str, Any] = self.yaml_service.load(yaml_file)

                if not self.specification.is_satisfied_by(data):
                    logger.debug(f"Skipping {yaml_file} - does not satisfy project specification")
                    continue

                entity_count: int = len(data.get("entities", {}))

                # Derive project name from relative path, converting / to : (e.g., "arbodat:arbodat-test")
                relative_path: Path = yaml_file.relative_to(self.projects_dir)
                path_str: str = str(relative_path.parent) if relative_path.parent != Path(".") else yaml_file.parent.name
                project_name: str = self._path_to_name(path_str)

                metadata = ProjectMetadata(
                    name=project_name,
                    file_path=str(yaml_file),
                    entity_count=entity_count,
                    created_at=yaml_file.stat().st_ctime,
                    modified_at=yaml_file.stat().st_mtime,
                    is_valid=True,
                )
                configs.append(metadata)

            except Exception as e:  # pylint: disable=broad-except
                logger.warning(f"Failed to load project {yaml_file}: {e}")

        logger.debug(f"Found {len(configs)} project(s) satisfying specification")
        return configs

    def load_project(self, name: str, force_reload: bool = False) -> Project:
        """
        Load project by name.

        Checks ApplicationState cache first (for active editing sessions).
        Falls back to disk load if not in cache or not actively edited.
        Updates version tracking in ApplicationState for cache invalidation.

        Args:
            name: Project name - either simple name (e.g., 'aDNA-pilot') or
                  nested path (e.g., 'arbodat/arbodat-test')
            force_reload: If True, invalidate cache and reload from disk (default: False)

        Returns:
            Project object

        Raises:
            ResourceNotFoundError: If project not found
            ConfigurationError: If project is invalid
        """
        # Force reload: invalidate cache before loading
        if force_reload:
            self.state.invalidate(name)
            logger.info(f"Force reload requested for '{name}', cache invalidated")

        corr: str = get_correlation_id()

        # Check ApplicationState cache first (actively edited projects)
        cached_project: Project | None = self.state.get(name)
        if cached_project:
            # CRITICAL FIX: Return deep copy to prevent mutation-through-reference.
            # Without this, two concurrent callers mutating the same cached object
            # cause lost-update race conditions.
            copy: Project = cached_project.model_copy(deep=True)
            entity_count: int = len(copy.entities or {})
            entity_names: list[str] = sorted((copy.entities or {}).keys())
            logger.info(
                "[{}] load_project: '{}' from CACHE (deep copy) entities={} names={}",
                corr,
                name,
                entity_count,
                entity_names,
            )
            return copy

        # Load from disk - convert API name to path (arbodat:arbodat-test -> arbodat/arbodat-test)
        filename: Path = self.projects_dir / self._name_to_path(name) / "shapeshifter.yml"

        if not filename.exists():
            raise ResourceNotFoundError(resource_type="project", resource_id=name, message=f"Project not found: {name}")

        try:
            data: dict[str, Any] = self.yaml_service.load(filename)

            if not self.specification.is_satisfied_by(data):
                raise ConfigurationError(
                    message=f"Invalid project file '{name}': missing required 'entities' key",
                )

            project: Project = ProjectMapper.to_api_config(data, name)

            assert project.metadata is not None  # For mypy

            project.metadata.file_path = str(filename)
            project.metadata.created_at = filename.stat().st_ctime
            project.metadata.modified_at = filename.stat().st_mtime
            project.metadata.entity_count = len(project.entities or {})
            project.metadata.is_valid = True

            # Cache in ApplicationState for subsequent requests (multiple projects can be cached)
            self.state.activate(project)

            entity_names = sorted((project.entities or {}).keys())
            logger.info("[{}] load_project: '{}' from DISK entities={} names={}", corr, name, len(project.entities), entity_names)
            return project

        except ConfigurationError:
            raise
        except YamlLoadError as e:
            raise ConfigurationError(message=f"Invalid YAML in project '{name}': {e}") from e
        except Exception as e:
            logger.error(f"Failed to load project '{name}': {e}")
            raise ConfigurationError(message=f"Failed to load project '{name}': {e}") from e

    def save_project(self, project: Project, *, create_backup: bool = True, original_file_path: Path | None = None) -> Project:
        """
        Save project to file.

        Updates ApplicationState if this is the active project.

        Args:
            project: Project to save
            create_backup: Whether to create backup before saving
            original_file_path: Optional original file path to preserve filename (default: derive from metadata.name)

        Returns:
            Updated project with new metadata

        Raises:
            ConfigurationError: If save fails
        """
        if not project.metadata or not project.metadata.name:
            raise ConfigurationError(message="Project must have metadata with name")

        # Use original file path if provided, otherwise derive from metadata.name
        # Example: projects_dir/project-name/shapeshifter.yml
        file_path: Path = original_file_path or (self.projects_dir / project.metadata.name / "shapeshifter.yml")

        # Ensure project directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        corr: str = get_correlation_id()
        name: str = project.metadata.name
        entity_count: int = len(project.entities or {})
        entity_names: list[str] = sorted((project.entities or {}).keys())

        try:
            # Convert to core dict for saving (sparse structure)
            cfg_dict: dict[str, Any] = ProjectMapper.to_core_dict(project)

            logger.info(
                "[{}] save_project: '{}' writing entities={} names={}",
                corr,
                name,
                entity_count,
                entity_names,
            )

            self.yaml_service.save(cfg_dict, file_path, create_backup=create_backup)

            # DEFENSIVE: Verify what was actually written to disk
            self._verify_save(name, entity_names, file_path, corr)

            project.metadata.modified_at = file_path.stat().st_mtime
            project.metadata.entity_count = len(project.entities)

            logger.info("[{}] save_project: '{}' saved and verified OK", corr, name)

            self.state.update(project)

            return project

        except ConfigurationError:
            raise
        except YamlSaveError as e:
            raise ConfigurationError(message=f"Failed to save project: {e}") from e
        except Exception as e:
            logger.error(f"Failed to save project: {e}")
            raise ConfigurationError(message=f"Failed to save project: {e}") from e

    def _verify_save(self, name: str, expected_entities: list[str], file_path: Path, corr: str) -> None:
        """Read back the saved file and verify entity count matches.

        This is a defensive measure to detect silent data loss during
        serialization (e.g., if ProjectMapper.to_core_dict drops entities).
        """
        import yaml  # pylint: disable=import-outside-toplevel

        expected_count: int = len(expected_entities)
        if expected_count == 0:
            return  # Nothing to verify for empty projects

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                written_data = yaml.safe_load(f)

            actual_entities = sorted((written_data or {}).get("entities", {}).keys())
            actual_count: int = len(actual_entities)

            if actual_count != expected_count:
                logger.error(
                    "[{}] SAVE VERIFICATION FAILED: project='{}'" + " expected={} expected_names={} actual={} on_disk={}",
                    corr,
                    name,
                    expected_count,
                    expected_entities,
                    actual_count,
                    actual_entities,
                )
            else:
                logger.debug(
                    "[{}] save_project: verification OK for '{}' ({} entities)",
                    corr,
                    name,
                    actual_count,
                )
        except Exception as e:  # pylint: disable=broad-except
            logger.error(
                "[{}] save_project: verification read-back failed for '{}': {}",
                corr,
                name,
                str(e),
            )

    def _invalidate_all_caches(self, project_name: str, corr: str) -> None:
        """Invalidate ALL caches for a project.

        This MUST be called on project deletion to prevent ghost entities
        when a new project is created with the same name.
        Clears: ApplicationState, ShapeShiftCache, ShapeShiftProjectCache.
        """
        # ApplicationState
        self.state.invalidate(project_name)

        # ShapeShift caches (lazy import to avoid circular dependency)
        try:
            from backend.app.services.shapeshift_service import get_shapeshift_service  # pylint: disable=import-outside-toplevel

            shapeshift_service = get_shapeshift_service()
            shapeshift_service.cache.invalidate_project(project_name)
            shapeshift_service.project_cache.invalidate_project(project_name)
            logger.info(
                "[{}] _invalidate_all_caches: all caches invalidated for '{}'",
                corr,
                project_name,
            )
        except Exception as e:  # pylint: disable=broad-except
            logger.warning(
                "[{}] _invalidate_all_caches: failed to access ShapeShift caches for '{}': {}",
                corr,
                project_name,
                str(e),
            )

    def create_project(self, name: str, entities: dict[str, Any] | None = None, task_list: dict[str, Any] | None = None) -> Project:
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
        return self.operations.create_project(name, entities, task_list)

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
        return self.operations.delete_project(name)

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
        return self.operations.copy_project(source_name, target_name)

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
        return self.operations.update_metadata(name, new_name, description, version, default_entity)

    @staticmethod
    def _serialize_entity(entity: Entity) -> dict[str, Any]:
        """
        Serialize entity to dict, preserving public_id field even when None.

        This ensures the three-tier identity model (system_id, keys, public_id)
        is always complete in YAML files, while avoiding bloat from other None fields.

        Args:
            entity: Entity to serialize

        Returns:
            Entity dict with public_id preserved
        """
        return EntityOperations._serialize_entity(entity)

    def add_entity(self, project: Project, entity_name: str, entity: Entity) -> Project:
        """
        Add entity to project.

        Args:
            project: Project to modify
            entity_name: Entity name
            entity: Entity data

        Returns:
            Updated project

        Raises:
            ResourceConflictError: If entity already exists
        """
        return self.entities.add_entity(project, entity_name, entity)

    def update_entity(self, project: Project, entity_name: str, entity: Entity) -> Project:
        """
        Update entity in project.

        Args:
            project: Project to modify
            entity_name: Entity name
            entity: Updated entity data

        Returns:
            Updated project

        Raises:
            ResourceNotFoundError: If entity not found
        """
        return self.entities.update_entity(project, entity_name, entity)

    def delete_entity(self, project: Project, entity_name: str) -> Project:
        """
        Delete entity from project.

        Args:
            project: Project to modify
            entity_name: Entity name

        Returns:
            Updated project

        Raises:
            ResourceNotFoundError: If entity not found
        """
        return self.entities.delete_entity(project, entity_name)

    def get_entity(self, project: Project, entity_name: str) -> dict[str, Any]:
        """
        Get entity from project.

        Args:
            project: Project
            entity_name: Entity name

        Returns:
            Entity data

        Raises:
            ResourceNotFoundError: If entity not found
        """
        return self.entities.get_entity(project, entity_name)

    # Convenience wrapper methods for entity operations by project name

    def add_entity_by_name(self, project_name: str, entity_name: str, entity_data: dict[str, Any]) -> None:
        """
        Add entity to project by project name.

        Serialized per-project to prevent lost-update race conditions.

        Args:
            project_name: Project name
            entity_name: Entity name
            entity_data: Entity data as dict

        Raises:
            ProjectNotFoundError: If project not found
            ResourceConflictError: If entity already exists
        """
        return self.entities.add_entity_by_name(project_name, entity_name, entity_data)

    def update_entity_by_name(self, project_name: str, entity_name: str, entity_data: dict[str, Any]) -> None:
        """
        Update entity in project by project name.

        Serialized per-project to prevent lost-update race conditions.

        Args:
            project_name: Project name
            entity_name: Entity name
            entity_data: Updated entity data as dict

        Raises:
            ProjectNotFoundError: If project not found
            ResourceNotFoundError: If entity not found
        """
        return self.entities.update_entity_by_name(project_name, entity_name, entity_data)

    def delete_entity_by_name(self, project_name: str, entity_name: str) -> None:
        """
        Delete entity from project by project name.

        Serialized per-project to prevent lost-update race conditions.

        Args:
            project_name: Project name
            entity_name: Entity name

        Raises:
            ProjectNotFoundError: If project not found
            ResourceNotFoundError: If entity not found
        """
        return self.entities.delete_entity_by_name(project_name, entity_name)

    def get_entity_by_name(self, project_name: str, entity_name: str) -> dict[str, Any]:
        """
        Get entity from project by project name.

        Args:
            project_name: Project name
            entity_name: Entity name

        Returns:
            Entity data as dict

        Raises:
            ProjectNotFoundError: If project not found
            ResourceNotFoundError: If entity not found
        """
        return self.entities.get_entity_by_name(project_name, entity_name)

    def activate_project(self, name: str) -> Project:
        """
        Activate a project for editing.

        Loads the project into ApplicationState as the active editing session.
        Uses mark_active() instead of state.activate() to avoid overwriting
        cached project data with a stale deep copy — load_project() already
        handles caching (activate on disk load, deep copy on cache hit).

        Args:
            name: Project name to activate

        Returns:
            The activated project

        Raises:
            ProjectNotFoundError: If project not found
        """

        project: Project = self.load_project(name)

        # Only set active project name; do NOT overwrite _active_projects[name]
        # because load_project() already stored the project when loading from
        # disk, and for cached projects a redundant state.activate() would
        # replace the up-to-date cached version with a stale deep copy.
        self.state.mark_active(name)

        return project

    def get_active_project_metadata(self) -> ProjectMetadata:
        """
        Get the name of the currently active editing project.

        Returns:
            Project name or None if no project is active
        """

        return self.state.get_active_metadata()

    def save_with_version_check(
        self,
        project: Project,
        expected_version: str,
        create_backup: bool = True,
    ) -> Project:
        """
        Save project with optimistic concurrency control.

        Args:
            project: Project to save
            expected_version: Client's expected version number
            create_backup: Whether to create backup before saving

        Returns:
            Updated project

        Raises:
            ResourceConflictError: If version mismatch (concurrent edit detected)
            ConfigurationError: If save fails
        """

        current_version: str = self.state.get_active_metadata().version or expected_version
        if expected_version != current_version:
            raise ResourceConflictError(
                resource_type="project",
                resource_id=project.metadata.name if project.metadata else "unknown",
                message=(
                    f"Project was modified by another user. "
                    f"Expected version {expected_version}, current version {current_version}. "
                    f"Reload and merge changes."
                ),
            )

        return self.save_project(project, create_backup=create_backup)

    # File management helpers

    def _sanitize_project_name(self, name: str) -> str:
        """Validate project name for new directory structure.

        Allows nested paths like 'arbodat/arbodat-test' but prevents directory traversal.

        Args:
            name: Project name (can be nested path like 'parent/child')

        Returns:
            Sanitized project name

        Raises:
            BadRequestError: If name is invalid or contains directory traversal
        """
        return self.utils.sanitize_project_name(name)

    def _ensure_project_exists(self, name: str) -> Path:
        """Ensure project exists in new directory structure.

        Returns:
            Path to the project's shapeshifter.yml file
        """
        return self.utils.ensure_project_exists(name)

    def _get_project_upload_dir(self, project_name: str) -> Path:  # pylint: disable=unused-argument
        """Get upload directory for a project."""
        return self.files._get_project_upload_dir(project_name)

    def _to_public_path(self, path: Path) -> str:
        """Convert absolute path to public relative path."""
        return self.files._to_public_path(path)

    def _resolve_path(self, path_str: str) -> Path:
        """Resolve a user-supplied path relative to project root (or projects dir) and validate existence."""
        return self.files._resolve_path(path_str)

    def _sanitize_filename(self, filename: str | None) -> str:
        """Sanitize uploaded filename to prevent path traversal."""
        return self.files._sanitize_filename(filename)

    def list_project_files(self, project_name: str, extensions: Iterable[str] | None = None) -> list[ProjectFileInfo]:
        """List files stored under a project's uploads directory.

        Args:
            project_name: Project name
            extensions: Optional file extensions to filter

        Returns:
            List of file information
        """
        return self.files.list_project_files(project_name, extensions)

    def save_project_file(
        self,
        project_name: str,
        upload: UploadFile,
        *,
        allowed_extensions: set[str] | None = None,
        max_size_mb: int = 50,  # FileManager.MAX_PROJECT_UPLOAD_SIZE_MB
    ) -> ProjectFileInfo:
        """Save an uploaded file into the project's uploads directory.

        Args:
            project_name: Project name
            upload: Uploaded file
            allowed_extensions: Allowed file extensions
            max_size_mb: Maximum file size in megabytes

        Returns:
            File information for the saved file
        """
        return self.files.save_project_file(project_name, upload, allowed_extensions=allowed_extensions, max_size_mb=max_size_mb)

    # Global data source file management

    def list_data_source_files(self, extensions: Iterable[str] | None = None) -> list[ProjectFileInfo]:
        """List files available for data source configuration in the projects directory.

        Args:
            extensions: Optional file extensions to filter

        Returns:
            List of file information
        """
        return self.files.list_data_source_files(extensions)

    def get_excel_metadata(
        self, file_path: str, sheet_name: str | None = None, cell_range: str | None = None
    ) -> tuple[list[str], list[str]]:
        """Return available sheets and columns for an Excel file.

        Args:
            file_path: Path (absolute or relative to project root) to the Excel file
            sheet_name: Optional sheet to inspect for columns
            cell_range: Optional cell range (e.g., 'A1:H30') to limit columns

        Returns:
            Tuple of (sheet_names, column_names)

        Raises:
            BadRequestError: If file is missing/unsupported or sheet is not found
        """
        return self.files.get_excel_metadata(file_path, sheet_name, cell_range)

    def save_data_source_file(
        self,
        upload: UploadFile,
        *,
        allowed_extensions: set[str] | None = None,
        max_size_mb: int = 50,  # FileManager.MAX_PROJECT_UPLOAD_SIZE_MB
    ) -> ProjectFileInfo:
        """Save an uploaded file into the projects directory (global data source).

        Args:
            upload: Uploaded file
            allowed_extensions: Allowed file extensions
            max_size_mb: Maximum file size in megabytes

        Returns:
            File information for the saved file
        """
        return self.files.save_data_source_file(upload, allowed_extensions=allowed_extensions, max_size_mb=max_size_mb)


# Singleton instance
_project_service: ProjectService | None = None  # pylint: disable=invalid-name


def get_project_service() -> ProjectService:
    """Get singleton ProjectService instance."""
    global _project_service  # pylint: disable=global-statement
    if _project_service is None:
        _project_service = ProjectService()
    return _project_service
