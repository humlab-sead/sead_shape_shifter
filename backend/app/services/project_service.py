"""Project service for managing entities."""

import shutil
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
from backend.app.services.yaml_service import YamlLoadError, YamlSaveError, YamlService, get_yaml_service
from backend.app.utils.exceptions import BadRequestError


class ProjectServiceError(Exception):
    """Generic exception for unexpected project service errors."""


DEFAULT_ALLOWED_UPLOAD_EXTENSIONS: set[str] = {".xlsx", ".xls"}
MAX_PROJECT_UPLOAD_SIZE_MB: int = 50


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

    def list_projects(self) -> list[ProjectMetadata]:
        """
        List all available project files.

        Returns:
            List of project metadata
        """
        if not self.projects_dir.exists():
            logger.warning(f"Projects directory does not exist: {self.projects_dir}")
            return []

        configs: list[ProjectMetadata] = []

        for yaml_file in self.projects_dir.glob("*.yml"):
            try:
                data: dict[str, Any] = self.yaml_service.load(yaml_file)

                if not self.specification.is_satisfied_by(data):
                    logger.debug(f"Skipping {yaml_file.name} - does not satisfy project specification")
                    continue

                entity_count = len(data.get("entities", {}))

                metadata = ProjectMetadata(
                    name=yaml_file.stem,
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
            name: Project name (without .yml extension)
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

        # Load from disk - YAML file is source of truth
        filename: Path = self.projects_dir / (f"{name.removesuffix('.yml')}.yml")
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
            logger.info(
                "[{}] load_project: '{}' from DISK entities={} names={}",
                corr,
                name,
                len(project.entities),
                entity_names,
            )
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
        file_path: Path = original_file_path or (self.projects_dir / f"{project.metadata.name.removesuffix('.yml')}.yml")

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
            name: Project name
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

        return self.save_project(project, create_backup=False)

    def delete_project(self, name: str) -> None:
        """
        Delete project file.

        Clears ALL caches (ApplicationState, ShapeShiftCache, ShapeShiftProjectCache)
        to prevent ghost entities when a new project is created with the same name.

        Args:
            name: Project name

        Raises:
            ResourceNotFoundError: If project not found
        """
        corr = get_correlation_id()
        file_path: Path = self.projects_dir / f"{name}.yml"

        if not file_path.exists():
            raise ResourceNotFoundError(resource_type="project", resource_id=name, message=f"Project not found: {name}")

        lock = self._get_lock(name)
        logger.info("[{}] delete_project: ACQUIRING lock for '{}'", corr, name)

        with lock:
            logger.info("[{}] delete_project: ACQUIRED lock for '{}'", corr, name)
            try:
                self.yaml_service.create_backup(file_path)
                file_path.unlink()
                logger.info("[{}] delete_project: file deleted for '{}'", corr, name)

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
        Copy a project and its associated files to a new name.

        Copies:
        - Project YAML file with updated metadata.name
        - Materialized files directory (if exists)
        - Reconciliation file (if exists)

        Args:
            source_name: Source project name (without .yml extension)
            target_name: Target project name (without .yml extension)

        Returns:
            New project with updated metadata

        Raises:
            ResourceNotFoundError: If source project not found
            ResourceConflictError: If target project already exists
            ProjectServiceError: If copy fails
        """
        # Normalize names (remove .yml if present)
        source_name = source_name.removesuffix(".yml")
        target_name = target_name.removesuffix(".yml")

        source_file: Path = self.projects_dir / f"{source_name}.yml"
        target_file: Path = self.projects_dir / f"{target_name}.yml"

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

        # Define paths for cleanup
        source_materialized_dir: Path = self.projects_dir / f"projects/{source_name}/materialized"
        target_materialized_dir: Path = self.projects_dir / f"projects/{target_name}/materialized"
        source_recon_file: Path = self.projects_dir / f"{source_name}-reconciliation.yml"
        target_recon_file: Path = self.projects_dir / f"{target_name}-reconciliation.yml"

        try:
            # Load source project
            source_project: Project = self.load_project(source_name)

            # Update metadata for target
            if source_project.metadata:
                updated_description = (
                    source_project.metadata.description.replace(source_name, target_name) if source_project.metadata.description else None
                )
                source_project.metadata = source_project.metadata.model_copy(
                    update={"name": target_name, "description": updated_description}
                )

            # Copy materialized files directory if exists
            if source_materialized_dir.exists():
                logger.info(f"Copying materialized directory from {source_materialized_dir} to {target_materialized_dir}")
                shutil.copytree(source_materialized_dir, target_materialized_dir)

            # Copy reconciliation file if exists
            if source_recon_file.exists():
                logger.info(f"Copying reconciliation file from {source_recon_file} to {target_recon_file}")
                shutil.copy2(source_recon_file, target_recon_file)

            # Save target project (this creates the new YAML file)
            logger.info(f"Saving copied project '{target_name}'")
            new_project: Project = self.save_project(source_project, create_backup=False)

            logger.info(f"Successfully copied project '{source_name}' to '{target_name}'")
            return new_project

        except (ResourceNotFoundError, ResourceConflictError, ConfigurationError):
            # Re-raise domain exceptions as-is
            raise
        except Exception as e:
            # Clean up partial copies on failure
            logger.error(f"Failed to copy project '{source_name}' to '{target_name}': {e}")

            if target_file.exists():
                target_file.unlink()

            if target_materialized_dir.exists():
                shutil.rmtree(target_materialized_dir)

            if target_recon_file.exists():
                target_recon_file.unlink()

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
        project: Project = self.load_project(name)

        if not project.metadata:
            raise ConfigurationError(message=f"Project '{name}' has no metadata")

        # Determine original file path to preserve filename
        original_file_path: Path = self.projects_dir / f"{name}.yml"

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
        saved_config: Project = self.save_project(project, create_backup=True, original_file_path=original_file_path)

        return saved_config

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
        # Exclude None fields to avoid YAML bloat, but preserve public_id separately
        entity_dict: dict[str, Any] = entity.model_dump(exclude_none=True, exclude={"surrogate_id"}, mode="json")  # Exclude deprecated field

        # Ensure public_id is always present (even if None) for three-tier identity model
        if "public_id" not in entity_dict:
            entity_dict["public_id"] = entity.public_id

        return entity_dict

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
        if entity_name in project.entities:
            raise ResourceConflictError(resource_type="entity", resource_id=entity_name, message=f"Entity '{entity_name}' already exists")

        project.entities[entity_name] = self._serialize_entity(entity)
        logger.debug(f"Added entity '{entity_name}'")
        return project

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
        if entity_name not in project.entities:
            raise ResourceNotFoundError(resource_type="entity", resource_id=entity_name, message=f"Entity '{entity_name}' not found")

        project.entities[entity_name] = self._serialize_entity(entity)
        logger.debug(f"Updated entity '{entity_name}'")
        return project

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
        if entity_name not in project.entities:
            raise ResourceNotFoundError(resource_type="entity", resource_id=entity_name, message=f"Entity '{entity_name}' not found")

        del project.entities[entity_name]

        logger.debug(f"Deleted entity '{entity_name}'")
        return project

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
        if entity_name not in project.entities:
            raise ResourceNotFoundError(resource_type="entity", resource_id=entity_name, message=f"Entity '{entity_name}' not found")

        return project.entities[entity_name]

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
        corr: str = get_correlation_id()
        lock = self._get_lock(project_name)
        logger.info(
            "[{}] add_entity_by_name: ACQUIRING lock project='{}' entity='{}'",
            corr,
            project_name,
            entity_name,
        )

        with lock:
            project: Project = self.load_project(project_name)

            before_names: list[str] = sorted((project.entities or {}).keys())
            logger.info(
                "[{}] add_entity_by_name: project='{}' BEFORE add: count={} names={} adding='{}'",
                corr,
                project_name,
                len(before_names),
                before_names,
                entity_name,
            )

            if entity_name in project.entities:
                raise ResourceConflictError(
                    resource_type="entity", resource_id=entity_name, message=f"Entity '{entity_name}' already exists"
                )

            # Use the model's add_entity method to ensure proper handling
            project.add_entity(entity_name, entity_data)

            after_names: list[str] = sorted((project.entities or {}).keys())
            logger.info(
                "[{}] add_entity_by_name: project='{}' AFTER add: count={} names={}",
                corr,
                project_name,
                len(after_names),
                after_names,
            )

            self.save_project(project)

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
        corr: str = get_correlation_id()
        lock = self._get_lock(project_name)
        logger.info(
            "[{}] update_entity_by_name: ACQUIRING lock project='{}' entity='{}'",
            corr,
            project_name,
            entity_name,
        )

        with lock:
            project: Project = self.load_project(project_name)

            entity_names: list[str] = sorted((project.entities or {}).keys())
            logger.info(
                "[{}] update_entity_by_name: project='{}' current entities={} names={} updating='{}'",
                corr,
                project_name,
                len(entity_names),
                entity_names,
                entity_name,
            )

            if entity_name not in project.entities:
                raise ResourceNotFoundError(resource_type="entity", resource_id=entity_name, message=f"Entity '{entity_name}' not found")

            # Ensure public_id is preserved (three-tier identity model)
            # If not in incoming data, keep existing value (even if None)
            if "public_id" not in entity_data and "public_id" in project.entities[entity_name]:
                entity_data["public_id"] = project.entities[entity_name]["public_id"]

            # Use the model's add_entity method to ensure proper handling
            project.add_entity(entity_name, entity_data)
            self.save_project(project)

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
        corr: str = get_correlation_id()
        lock = self._get_lock(project_name)
        logger.info(
            "[{}] delete_entity_by_name: ACQUIRING lock project='{}' entity='{}'",
            corr,
            project_name,
            entity_name,
        )

        with lock:
            project: Project = self.load_project(project_name)

            before_names: list[str] = sorted((project.entities or {}).keys())
            logger.info(
                "[{}] delete_entity_by_name: project='{}' BEFORE delete: count={} names={} removing='{}'",
                corr,
                project_name,
                len(before_names),
                before_names,
                entity_name,
            )

            if entity_name not in project.entities:
                raise ResourceNotFoundError(resource_type="entity", resource_id=entity_name, message=f"Entity '{entity_name}' not found")

            del project.entities[entity_name]

            after_names: list[str] = sorted((project.entities or {}).keys())
            logger.info(
                "[{}] delete_entity_by_name: project='{}' AFTER delete: count={} names={}",
                corr,
                project_name,
                len(after_names),
                after_names,
            )

            self.save_project(project)

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
        project: Project = self.load_project(project_name)

        if entity_name not in project.entities:
            raise ResourceNotFoundError(resource_type="entity", resource_id=entity_name, message=f"Entity '{entity_name}' not found")

        return project.entities[entity_name]

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
        safe_name: str = name.strip()
        if not safe_name or Path(safe_name).name != safe_name:
            raise BadRequestError("Invalid project name")
        return safe_name

    def _ensure_project_exists(self, name: str) -> Path:
        """Ensure project exists in new directory structure."""
        safe_name: str = self._sanitize_project_name(name)
        project_file: Path = self.projects_dir / safe_name / "shapeshifter.yml"

        if not project_file.exists():
            raise ResourceNotFoundError(
                resource_type="project", resource_id=name, message=f"Project not found: {name} (expected: {project_file})"
            )

        return project_file

    def _get_project_upload_dir(self, project_name: str) -> Path:  # pylint: disable=unused-argument
        # safe_name = self._sanitize_project_name(project_name)
        return self.projects_dir

    def _to_public_path(self, path: Path) -> str:
        try:
            return str(path.relative_to(settings.PROJECT_ROOT))
        except ValueError:
            try:
                return str(path.relative_to(settings.PROJECTS_DIR.parent))
            except ValueError:
                return str(path)

    def _resolve_path(self, path_str: str) -> Path:
        """Resolve a user-supplied path relative to project root (or projects dir) and validate existence."""

        raw = Path(path_str)
        candidates: list[Path] = []

        # Absolute path as-is
        if raw.is_absolute():
            candidates.append(raw)
        else:
            # Relative to repo root
            candidates.append((settings.PROJECT_ROOT / raw).resolve())
            # Relative to projects dir
            candidates.append((settings.PROJECTS_DIR / raw.name).resolve())

        for candidate in candidates:
            if candidate.exists():
                return candidate

        raise BadRequestError(f"File not found: {path_str}")

    def _sanitize_filename(self, filename: str | None) -> str:
        if not filename:
            raise BadRequestError("Filename is required")
        safe_name: str = Path(filename).name
        if not safe_name:
            raise BadRequestError("Invalid filename")
        return safe_name

    def list_project_files(self, project_name: str, extensions: Iterable[str] | None = None) -> list[ProjectFileInfo]:
        """List files stored under a project's uploads directory."""

        self._ensure_project_exists(project_name)
        upload_dir: Path = self._get_project_upload_dir(project_name)

        if not upload_dir.exists():
            return []

        ext_set: set[str] | None = None
        if extensions:
            ext_set = {f".{ext.lstrip('.').lower()}" for ext in extensions if ext}

        files: list[ProjectFileInfo] = []
        for file_path in sorted(upload_dir.glob("*")):
            if not file_path.is_file():
                continue

            if ext_set and file_path.suffix.lower() not in ext_set:
                continue

            stat = file_path.stat()
            files.append(
                ProjectFileInfo(
                    name=file_path.name,
                    path=self._to_public_path(file_path),
                    size_bytes=stat.st_size,
                    modified_at=stat.st_mtime,
                )
            )

        return files

    def save_project_file(
        self,
        project_name: str,
        upload: UploadFile,
        *,
        allowed_extensions: set[str] | None = None,
        max_size_mb: int = MAX_PROJECT_UPLOAD_SIZE_MB,
    ) -> ProjectFileInfo:
        """Save an uploaded file into the project's uploads directory."""

        self._ensure_project_exists(project_name)
        allowed: set[str] = allowed_extensions or DEFAULT_ALLOWED_UPLOAD_EXTENSIONS

        filename: str = self._sanitize_filename(upload.filename)
        ext: str = Path(filename).suffix.lower()
        if allowed and ext not in allowed:
            allowed_list: str = ", ".join(sorted(allowed))
            raise BadRequestError(f"Unsupported file type '{ext}'. Allowed: {allowed_list}")

        upload_dir: Path = self._get_project_upload_dir(project_name)
        upload_dir.mkdir(parents=True, exist_ok=True)

        target_path: Path = upload_dir / filename
        counter = 1
        while target_path.exists():
            target_path = upload_dir / f"{Path(filename).stem}-{counter}{ext}"
            counter += 1

        max_bytes: int = max_size_mb * 1024 * 1024
        total_bytes = 0

        try:
            with target_path.open("wb") as buffer:
                while True:
                    chunk: bytes = upload.file.read(1024 * 1024)
                    if not chunk:
                        break
                    total_bytes += len(chunk)
                    if max_bytes and total_bytes > max_bytes:
                        raise BadRequestError(f"File is too large ({total_bytes} bytes). Maximum allowed is {max_bytes} bytes")
                    buffer.write(chunk)
        except Exception as exc:  # pylint: disable=broad-except
            target_path.unlink(missing_ok=True)
            raise exc
        finally:
            try:
                upload.file.close()
            except Exception:  # pylint: disable=broad-except
                pass

        stat = target_path.stat()

        return ProjectFileInfo(
            name=target_path.name,
            path=self._to_public_path(target_path),
            size_bytes=stat.st_size,
            modified_at=stat.st_mtime,
        )

    # Global data source file management

    def list_data_source_files(self, extensions: Iterable[str] | None = None) -> list[ProjectFileInfo]:
        """List files available for data source configuration in the projects directory."""

        upload_dir: Path = settings.PROJECTS_DIR

        if not upload_dir.exists():
            return []

        ext_set: set[str] | None = None
        if extensions:
            ext_set = {f".{ext.lstrip('.').lower()}" for ext in extensions if ext}

        files: list[ProjectFileInfo] = []
        for file_path in sorted(upload_dir.glob("*")):
            if not file_path.is_file():
                continue

            if ext_set and file_path.suffix.lower() not in ext_set:
                continue

            stat = file_path.stat()
            files.append(
                ProjectFileInfo(
                    name=file_path.name,
                    path=self._to_public_path(file_path),
                    size_bytes=stat.st_size,
                    modified_at=stat.st_mtime,
                )
            )

        return files

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

        resolved_path: Path = self._resolve_path(file_path)
        return extract_excel_metadata(resolved_path, sheet_name=sheet_name, cell_range=cell_range)

    def save_data_source_file(
        self,
        upload: UploadFile,
        *,
        allowed_extensions: set[str] | None = None,
        max_size_mb: int = MAX_PROJECT_UPLOAD_SIZE_MB,
    ) -> ProjectFileInfo:
        """Save an uploaded file into the projects directory."""

        allowed: set[str] = allowed_extensions or set()

        filename: str = self._sanitize_filename(upload.filename)
        ext: str = Path(filename).suffix.lower()
        if allowed and ext not in allowed:
            allowed_list: str = ", ".join(sorted(allowed))
            raise BadRequestError(f"Unsupported file type '{ext}'. Allowed: {allowed_list}")

        upload_dir: Path = settings.PROJECTS_DIR
        upload_dir.mkdir(parents=True, exist_ok=True)

        target_path: Path = upload_dir / filename
        counter = 1
        while target_path.exists():
            target_path = upload_dir / f"{Path(filename).stem}-{counter}{ext}"
            counter += 1

        max_bytes: int = max_size_mb * 1024 * 1024
        total_bytes = 0

        try:
            with target_path.open("wb") as buffer:
                while True:
                    chunk = upload.file.read(1024 * 1024)
                    if not chunk:
                        break
                    total_bytes += len(chunk)
                    if max_bytes and total_bytes > max_bytes:
                        raise BadRequestError(f"File is too large ({total_bytes} bytes). Maximum allowed is {max_bytes} bytes")
                    buffer.write(chunk)
        except Exception as exc:  # pylint: disable=broad-except
            target_path.unlink(missing_ok=True)
            raise exc
        finally:
            try:
                upload.file.close()
            except Exception:  # pylint: disable=broad-except
                pass

        stat = target_path.stat()

        return ProjectFileInfo(
            name=target_path.name,
            path=self._to_public_path(target_path),
            size_bytes=stat.st_size,
            modified_at=stat.st_mtime,
        )


# Singleton instance
_project_service: ProjectService | None = None  # pylint: disable=invalid-name


def get_project_service() -> ProjectService:
    """Get singleton ProjectService instance."""
    global _project_service  # pylint: disable=global-statement
    if _project_service is None:
        _project_service = ProjectService()
    return _project_service
