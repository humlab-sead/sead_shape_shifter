"""Project service for managing entities."""

from pathlib import Path
from typing import Any

from loguru import logger

from backend.app.core.config import settings
from backend.app.core.state_manager import ApplicationStateManager, get_app_state_manager
from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.models.entity import Entity
from backend.app.models.project import Project, ProjectMetadata
from backend.app.services.yaml_service import YamlLoadError, YamlSaveError, YamlService, get_yaml_service


class ProjectServiceError(Exception):
    """Base exception for project service errors."""


class ProjectNotFoundError(ProjectServiceError):
    """Raised when project file is not found."""


class EntityNotFoundError(ProjectServiceError):
    """Raised when entity is not found."""


class EntityAlreadyExistsError(ProjectServiceError):
    """Raised when trying to add entity that already exists."""


class InvalidProjectError(ProjectServiceError):
    """Raised when project is invalid."""


class ProjectConflictError(ProjectServiceError):
    """Raised when optimistic lock fails due to concurrent modification."""


class ProjectYamlSpecification:
    """Specification for project files."""

    def is_satisfied_by(self, data: dict[str, Any]) -> bool:
        metadata = (data or {}).get("metadata", {})
        return "type" in metadata


class ProjectService:
    """Service for managing project files and entities."""

    def __init__(self, projects_dir: Path | None = None, state: ApplicationStateManager | None = None) -> None:
        """Initialize project service."""
        self.yaml_service: YamlService = get_yaml_service()
        self.projects_dir: Path = projects_dir or settings.PROJECTS_DIR
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

    def load_project(self, name: str) -> Project:
        """
        Load project by name.

        If the project is currently active in ApplicationState,
        loads from there to ensure consistency with editing session.

        Args:
            name: Project name (without .yml extension)

        Returns:
            Project object

        Raises:
            ProjectNotFoundError: If project not found
            InvalidProjectError: If project is invalid
        """
        # Check application state if this is the active project
        active_project: Project | None = self.state.get(name)
        if active_project:
            logger.debug(f"Loading active project '{name}' from ApplicationState")
            return active_project

        filename: Path = self.projects_dir / (f"{name.rstrip('.yml')}.yml")
        if not filename.exists():
            raise ProjectNotFoundError(f"Project not found: {name}")

        try:
            data: dict[str, Any] = self.yaml_service.load(filename)

            if not self.specification.is_satisfied_by(data):
                raise InvalidProjectError(f"Invalid project file '{name}': missing required 'entities' key")

            project: Project = ProjectMapper.to_api_config(data, name)

            assert project.metadata is not None  # For mypy

            project.metadata.file_path = str(filename)
            project.metadata.created_at = filename.stat().st_ctime
            project.metadata.modified_at = filename.stat().st_mtime
            project.metadata.entity_count = len(project.entities or {})
            project.metadata.is_valid = True

            logger.info(f"Loaded project '{name}' with {len(project.entities)} entities")
            return project

        except YamlLoadError as e:
            raise InvalidProjectError(f"Invalid YAML in project '{name}': {e}") from e
        except Exception as e:
            logger.error(f"Failed to load project '{name}': {e}")
            raise InvalidProjectError(f"Failed to load project '{name}': {e}") from e

    def save_project(self, project: Project, create_backup: bool = True, original_file_path: Path | None = None) -> Project:
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
            InvalidProjectError: If save fails
        """
        if not project.metadata or not project.metadata.name:
            raise InvalidProjectError("Project must have metadata with name")

        # Use original file path if provided, otherwise derive from metadata.name
        file_path: Path = original_file_path or (self.projects_dir / f"{project.metadata.name.rstrip(".yml")}.yml")

        try:
            # Convert to core dict for saving (sparse structure)
            cfg_dict: dict[str, Any] = ProjectMapper.to_core_dict(project)

            logger.debug(f"Saving project '{project.metadata.name}' with {len(project.entities)} entities: {list(project.entities.keys())}")

            self.yaml_service.save(cfg_dict, file_path, create_backup=create_backup)

            project.metadata.modified_at = file_path.stat().st_mtime
            project.metadata.entity_count = len(project.entities)

            logger.info(f"Saved project '{project.metadata.name}'")

            self.state.update(project)

            return project

        except YamlSaveError as e:
            raise InvalidProjectError(f"Failed to save project: {e}") from e
        except Exception as e:
            logger.error(f"Failed to save project: {e}")
            raise InvalidProjectError(f"Failed to save project: {e}") from e

    def create_project(self, name: str, entities: dict[str, Any] | None = None) -> Project:
        """
        Create new project.

        Args:
            name: Project name
            entities: Optional initial entities

        Returns:
            New project

        Raises:
            ProjectConflictError: If project already exists
        """
        file_path: Path = self.projects_dir / f"{name}.yml"

        if file_path.exists():
            raise ProjectConflictError(f"Project '{name}' already exists")

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

        project: Project = Project(entities=entities or {}, options={}, metadata=metadata)

        return self.save_project(project, create_backup=False)

    def delete_project(self, name: str) -> None:
        """
        Delete project file.

        Args:
            name: Project name

        Raises:
            ProjectNotFoundError: If project not found
        """
        file_path: Path = self.projects_dir / f"{name}.yml"

        if not file_path.exists():
            raise ProjectNotFoundError(f"Project not found: {name}")

        try:
            self.yaml_service.create_backup(file_path)
            file_path.unlink()
            logger.info(f"Deleted project '{name}'")

        except Exception as e:
            logger.error(f"Failed to delete project '{name}': {e}")
            raise ProjectServiceError(f"Failed to delete project: {e}") from e

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
            raise InvalidProjectError(f"Project '{name}' has no metadata")

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
            EntityAlreadyExistsError: If entity already exists
        """
        if entity_name in project.entities:
            raise EntityAlreadyExistsError(f"Entity '{entity_name}' already exists")

        project.entities[entity_name] = entity.model_dump(exclude_none=True, mode="json")

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
            EntityNotFoundError: If entity not found
        """
        if entity_name not in project.entities:
            raise EntityNotFoundError(f"Entity '{entity_name}' not found")

        project.entities[entity_name] = entity.model_dump(exclude_none=True, mode="json")

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
            EntityNotFoundError: If entity not found
        """
        if entity_name not in project.entities:
            raise EntityNotFoundError(f"Entity '{entity_name}' not found")

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
            EntityNotFoundError: If entity not found
        """
        if entity_name not in project.entities:
            raise EntityNotFoundError(f"Entity '{entity_name}' not found")

        return project.entities[entity_name]

    # Convenience wrapper methods for entity operations by project name

    def add_entity_by_name(self, project_name: str, entity_name: str, entity_data: dict[str, Any]) -> None:
        """
        Add entity to project by project name.

        Args:
            project_name: Project name
            entity_name: Entity name
            entity_data: Entity data as dict

        Raises:
            ProjectNotFoundError: If project not found
            EntityAlreadyExistsError: If entity already exists
        """
        project: Project = self.load_project(project_name)

        if entity_name in project.entities:
            raise EntityAlreadyExistsError(f"Entity '{entity_name}' already exists")

        # Use the model's add_entity method to ensure proper handling
        project.add_entity(entity_name, entity_data)
        self.save_project(project)
        logger.info(f"Added entity '{entity_name}' to project '{project_name}'")

    def update_entity_by_name(self, project_name: str, entity_name: str, entity_data: dict[str, Any]) -> None:
        """
        Update entity in project by project name.

        Args:
            project_name: Project name
            entity_name: Entity name
            entity_data: Updated entity data as dict

        Raises:
            ProjectNotFoundError: If project not found
            EntityNotFoundError: If entity not found
        """
        project: Project = self.load_project(project_name)

        if entity_name not in project.entities:
            raise EntityNotFoundError(f"Entity '{entity_name}' not found")

        # Use the model's add_entity method to ensure proper handling
        project.add_entity(entity_name, entity_data)
        self.save_project(project)
        logger.info(f"Updated entity '{entity_name}' in project '{project_name}'")

    def delete_entity_by_name(self, project_name: str, entity_name: str) -> None:
        """
        Delete entity from project by project name.

        Args:
            project_name: Project name
            entity_name: Entity name

        Raises:
            ProjectNotFoundError: If project not found
            EntityNotFoundError: If entity not found
        """
        project: Project = self.load_project(project_name)

        if entity_name not in project.entities:
            raise EntityNotFoundError(f"Entity '{entity_name}' not found")

        del project.entities[entity_name]
        self.save_project(project)
        logger.info(f"Deleted entity '{entity_name}' from project '{project_name}'")

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
            EntityNotFoundError: If entity not found
        """
        project: Project = self.load_project(project_name)

        if entity_name not in project.entities:
            raise EntityNotFoundError(f"Entity '{entity_name}' not found")

        return project.entities[entity_name]

    def activate_project(self, name: str) -> Project:
        """
        Activate a project for editing.

        Loads the project into ApplicationState as the active editing session.

        Args:
            name: Project name to activate

        Returns:
            The activated project

        Raises:
            ProjectNotFoundError: If project not found
        """

        project: Project = self.load_project(name)

        self.state.activate(project)

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
            ProjectConflictError: If version mismatch (concurrent edit detected)
            InvalidProjectError: If save fails
        """

        current_version: str = self.state.get_active_metadata().version or expected_version
        if expected_version != current_version:
            raise ProjectConflictError(
                f"Project was modified by another user. "
                f"Expected version {expected_version}, current version {current_version}. "
                f"Reload and merge changes."
            )

        return self.save_project(project, create_backup=create_backup)


# Singleton instance
_project_service: ProjectService | None = None  # pylint: disable=invalid-name


def get_project_service() -> ProjectService:
    """Get singleton ProjectService instance."""
    global _project_service  # pylint: disable=global-statement
    if _project_service is None:
        _project_service = ProjectService()
    return _project_service
