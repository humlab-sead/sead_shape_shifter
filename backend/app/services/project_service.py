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
    """Base exception for configuration service errors."""


class ProjectNotFoundError(ProjectServiceError):
    """Raised when configuration file is not found."""


class EntityNotFoundError(ProjectServiceError):
    """Raised when entity is not found."""


class EntityAlreadyExistsError(ProjectServiceError):
    """Raised when trying to add entity that already exists."""


class InvalidProjectError(ProjectServiceError):
    """Raised when configuration is invalid."""


class ProjectConflictError(ProjectServiceError):
    """Raised when optimistic lock fails due to concurrent modification."""


class ProjectYamlSpecification:
    """Specification for configuration files."""

    def is_satisfied_by(self, data: dict[str, Any]) -> bool:
        return "entities" in (data or {})


class ProjectService:
    """Service for managing configuration files and entities."""

    def __init__(self, projects_dir: Path | None = None, state: ApplicationStateManager | None = None) -> None:
        """Initialize configuration service."""
        self.yaml_service: YamlService = get_yaml_service()
        self.projects_dir: Path = projects_dir or settings.PROJECTS_DIR
        self.specification = ProjectYamlSpecification()
        self.state: ApplicationStateManager = state or get_app_state_manager()

    def list_projects(self) -> list[ProjectMetadata]:
        """
        List all available configuration files.

        Returns:
            List of configuration metadata
        """
        if not self.projects_dir.exists():
            logger.warning(f"Projects directory does not exist: {self.projects_dir}")
            return []

        configs: list[ProjectMetadata] = []

        for yaml_file in self.projects_dir.glob("*.yml"):
            try:
                data: dict[str, Any] = self.yaml_service.load(yaml_file)

                if not self.specification.is_satisfied_by(data):
                    logger.debug(f"Skipping {yaml_file.name} - does not satisfy configuration specification")
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
                logger.warning(f"Failed to load configuration {yaml_file}: {e}")

        logger.debug(f"Found {len(configs)} configuration(s) satisfying specification")
        return configs

    def load_project(self, name: str) -> Project:
        """
        Load configuration by name.

        If the configuration is currently active in ApplicationState,
        loads from there to ensure consistency with editing session.

        Args:
            name: Project name (without .yml extension)

        Returns:
            Project object

        Raises:
            ProjectNotFoundError: If configuration not found
            InvalidProjectError: If configuration is invalid
        """
        # Check application state if this is the active configuration
        active_config: Project | None = self.state.get(name)
        if active_config:
            logger.debug(f"Loading active configuration '{name}' from ApplicationState")
            return active_config

        filename: Path = self.projects_dir / (f"{name.rstrip('.yml')}.yml")
        if not filename.exists():
            raise ProjectNotFoundError(f"Project not found: {name}")

        try:
            data: dict[str, Any] = self.yaml_service.load(filename)

            if not self.specification.is_satisfied_by(data):
                raise InvalidProjectError(f"Invalid configuration file '{name}': missing required 'entities' key")

            config: Project = ProjectMapper.to_api_config(data, name)

            assert config.metadata is not None  # For mypy

            config.metadata.file_path = str(filename)
            config.metadata.created_at = filename.stat().st_ctime
            config.metadata.modified_at = filename.stat().st_mtime
            config.metadata.entity_count = len(config.entities or {})
            config.metadata.is_valid = True

            logger.info(f"Loaded configuration '{name}' with {len(config.entities)} entities")
            return config

        except YamlLoadError as e:
            raise InvalidProjectError(f"Invalid YAML in configuration '{name}': {e}") from e
        except Exception as e:
            logger.error(f"Failed to load configuration '{name}': {e}")
            raise InvalidProjectError(f"Failed to load configuration '{name}': {e}") from e

    def save_project(self, config: Project, create_backup: bool = True) -> Project:
        """
        Save configuration to file.

        Updates ApplicationState if this is the active configuration.

        Args:
            config: Project to save
            create_backup: Whether to create backup before saving

        Returns:
            Updated configuration with new metadata

        Raises:
            InvalidProjectError: If save fails
        """
        if not config.metadata or not config.metadata.name:
            raise InvalidProjectError("Project must have metadata with name")

        file_path: Path = self.projects_dir / f"{config.metadata.name.rstrip(".yml")}.yml"

        try:
            # Convert to core dict for saving (sparse structure)
            cfg_dict: dict[str, Any] = ProjectMapper.to_core_dict(config)

            logger.debug(
                f"Saving configuration '{config.metadata.name}' with {len(config.entities)} entities: {list(config.entities.keys())}"
            )

            self.yaml_service.save(cfg_dict, file_path, create_backup=create_backup)

            config.metadata.modified_at = file_path.stat().st_mtime
            config.metadata.entity_count = len(config.entities)

            logger.info(f"Saved configuration '{config.metadata.name}'")

            self.state.update(config)

            return config

        except YamlSaveError as e:
            raise InvalidProjectError(f"Failed to save configuration: {e}") from e
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            raise InvalidProjectError(f"Failed to save configuration: {e}") from e

    def create_project(self, name: str, entities: dict[str, Any] | None = None) -> Project:
        """
        Create new configuration.

        Args:
            name: Project name
            entities: Optional initial entities

        Returns:
            New configuration

        Raises:
            ProjectConflictError: If configuration already exists
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
        )

        config: Project = Project(entities=entities or {}, options={}, metadata=metadata)

        return self.save_project(config, create_backup=False)

    def delete_project(self, name: str) -> None:
        """
        Delete configuration file.

        Args:
            name: Project name

        Raises:
            ProjectNotFoundError: If configuration not found
        """
        file_path: Path = self.projects_dir / f"{name}.yml"

        if not file_path.exists():
            raise ProjectNotFoundError(f"Project not found: {name}")

        try:
            self.yaml_service.create_backup(file_path)
            file_path.unlink()
            logger.info(f"Deleted configuration '{name}'")

        except Exception as e:
            logger.error(f"Failed to delete configuration '{name}': {e}")
            raise ProjectServiceError(f"Failed to delete configuration: {e}") from e

    def update_metadata(
        self,
        name: str,
        new_name: str | None = None,
        description: str | None = None,
        version: str | None = None,
        default_entity: str | None = None,
    ) -> Project:
        """
        Update configuration metadata.

        Args:
            name: Current configuration name
            new_name: New configuration name (optional)
            description: Project description (optional)
            version: Project version (optional)
            default_entity: Default entity name (optional)

        Returns:
            Updated configuration

        Raises:
            ProjectNotFoundError: If configuration not found
            ProjectConflictError: If new name conflicts with existing configuration
        """
        # Load current configuration
        config: Project = self.load_project(name)

        if not config.metadata:
            raise InvalidProjectError(f"Project '{name}' has no metadata")

        # Handle rename if requested
        old_file_path: Path = self.projects_dir / f"{name}.yml"
        new_file_path: Path | None = None

        if new_name and new_name != name:
            new_file_path = self.projects_dir / f"{new_name}.yml"
            if new_file_path.exists():
                raise ProjectConflictError(f"Project '{new_name}' already exists")

        # Update metadata fields (only if provided)
        if new_name:
            config.metadata.name = new_name
        if description is not None:
            config.metadata.description = description
        if version is not None:
            config.metadata.version = version
        if default_entity is not None:
            config.metadata.default_entity = default_entity

        # Save configuration
        saved_config: Project = self.save_project(config, create_backup=True)

        # Rename file if needed
        if new_file_path and new_name != name:
            old_file_path.rename(new_file_path)
            if saved_config.metadata:
                saved_config.metadata.file_path = str(new_file_path)
            logger.info(f"Renamed configuration from '{name}' to '{new_name}'")

            # Update application state with new name by activating the renamed config
            self.state.activate(saved_config, new_name)

        return saved_config

    def add_entity(self, config: Project, entity_name: str, entity: Entity) -> Project:
        """
        Add entity to configuration.

        Args:
            config: Project to modify
            entity_name: Entity name
            entity: Entity data

        Returns:
            Updated configuration

        Raises:
            EntityAlreadyExistsError: If entity already exists
        """
        if entity_name in config.entities:
            raise EntityAlreadyExistsError(f"Entity '{entity_name}' already exists")

        config.entities[entity_name] = entity.model_dump(exclude_none=True, mode="json")

        logger.debug(f"Added entity '{entity_name}'")
        return config

    def update_entity(self, config: Project, entity_name: str, entity: Entity) -> Project:
        """
        Update entity in configuration.

        Args:
            config: Project to modify
            entity_name: Entity name
            entity: Updated entity data

        Returns:
            Updated configuration

        Raises:
            EntityNotFoundError: If entity not found
        """
        if entity_name not in config.entities:
            raise EntityNotFoundError(f"Entity '{entity_name}' not found")

        config.entities[entity_name] = entity.model_dump(exclude_none=True, mode="json")

        logger.debug(f"Updated entity '{entity_name}'")
        return config

    def delete_entity(self, config: Project, entity_name: str) -> Project:
        """
        Delete entity from configuration.

        Args:
            config: Project to modify
            entity_name: Entity name

        Returns:
            Updated configuration

        Raises:
            EntityNotFoundError: If entity not found
        """
        if entity_name not in config.entities:
            raise EntityNotFoundError(f"Entity '{entity_name}' not found")

        del config.entities[entity_name]

        logger.debug(f"Deleted entity '{entity_name}'")
        return config

    def get_entity(self, config: Project, entity_name: str) -> dict[str, Any]:
        """
        Get entity from configuration.

        Args:
            config: Project
            entity_name: Entity name

        Returns:
            Entity data

        Raises:
            EntityNotFoundError: If entity not found
        """
        if entity_name not in config.entities:
            raise EntityNotFoundError(f"Entity '{entity_name}' not found")

        return config.entities[entity_name]

    # Convenience wrapper methods for entity operations by config name

    def add_entity_by_name(self, project_name: str, entity_name: str, entity_data: dict[str, Any]) -> None:
        """
        Add entity to configuration by config name.

        Args:
            project_name: Project name
            entity_name: Entity name
            entity_data: Entity data as dict

        Raises:
            ProjectNotFoundError: If configuration not found
            EntityAlreadyExistsError: If entity already exists
        """
        config: Project = self.load_project(project_name)

        if entity_name in config.entities:
            raise EntityAlreadyExistsError(f"Entity '{entity_name}' already exists")

        # Use the model's add_entity method to ensure proper handling
        config.add_entity(entity_name, entity_data)
        self.save_project(config)
        logger.info(f"Added entity '{entity_name}' to configuration '{project_name}'")

    def update_entity_by_name(self, project_name: str, entity_name: str, entity_data: dict[str, Any]) -> None:
        """
        Update entity in configuration by config name.

        Args:
            project_name: Project name
            entity_name: Entity name
            entity_data: Updated entity data as dict

        Raises:
            ProjectNotFoundError: If configuration not found
            EntityNotFoundError: If entity not found
        """
        config: Project = self.load_project(project_name)

        if entity_name not in config.entities:
            raise EntityNotFoundError(f"Entity '{entity_name}' not found")

        # Use the model's add_entity method to ensure proper handling
        config.add_entity(entity_name, entity_data)
        self.save_project(config)
        logger.info(f"Updated entity '{entity_name}' in configuration '{project_name}'")

    def delete_entity_by_name(self, project_name: str, entity_name: str) -> None:
        """
        Delete entity from configuration by config name.

        Args:
            project_name: Project name
            entity_name: Entity name

        Raises:
            ProjectNotFoundError: If configuration not found
            EntityNotFoundError: If entity not found
        """
        config: Project = self.load_project(project_name)

        if entity_name not in config.entities:
            raise EntityNotFoundError(f"Entity '{entity_name}' not found")

        del config.entities[entity_name]
        self.save_project(config)
        logger.info(f"Deleted entity '{entity_name}' from configuration '{project_name}'")

    def get_entity_by_name(self, project_name: str, entity_name: str) -> dict[str, Any]:
        """
        Get entity from configuration by config name.

        Args:
            project_name: Project name
            entity_name: Entity name

        Returns:
            Entity data as dict

        Raises:
            ProjectNotFoundError: If configuration not found
            EntityNotFoundError: If entity not found
        """
        config: Project = self.load_project(project_name)

        if entity_name not in config.entities:
            raise EntityNotFoundError(f"Entity '{entity_name}' not found")

        return config.entities[entity_name]

    def activate_configuration(self, name: str) -> Project:
        """
        Activate a configuration for editing.

        Loads the configuration into ApplicationState as the active editing session.

        Args:
            name: Project name to activate

        Returns:
            The activated configuration

        Raises:
            ProjectNotFoundError: If configuration not found
        """

        config: Project = self.load_project(name)

        self.state.activate(config)

        return config

    def get_active_configuration_metadata(self) -> ProjectMetadata:
        """
        Get the name of the currently active editing configuration.

        Returns:
            Project name or None if no configuration is active
        """

        return self.state.get_active_metadata()

    def save_with_version_check(
        self,
        config: Project,
        expected_version: str,
        create_backup: bool = True,
    ) -> Project:
        """
        Save configuration with optimistic concurrency control.

        Args:
            config: Project to save
            expected_version: Client's expected version number
            create_backup: Whether to create backup before saving

        Returns:
            Updated configuration

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

        return self.save_project(config, create_backup=create_backup)


# Singleton instance
_project_service: ProjectService | None = None  # pylint: disable=invalid-name


def get_project_service() -> ProjectService:
    """Get singleton ProjectService instance."""
    global _project_service  # pylint: disable=global-statement
    if _project_service is None:
        _project_service = ProjectService()
    return _project_service
