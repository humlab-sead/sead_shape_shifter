"""Configuration service for managing entity configurations."""

from pathlib import Path
from typing import Any

from loguru import logger

from backend.app.core.config import settings
from backend.app.core.state_manager import ApplicationStateManager, get_app_state_manager
from backend.app.mappers.config_mapper import ConfigMapper
from backend.app.models.config import ConfigMetadata, Configuration
from backend.app.models.entity import Entity
from backend.app.services.yaml_service import YamlLoadError, YamlSaveError, YamlService, get_yaml_service


class ConfigurationServiceError(Exception):
    """Base exception for configuration service errors."""


class ConfigurationNotFoundError(ConfigurationServiceError):
    """Raised when configuration file is not found."""


class EntityNotFoundError(ConfigurationServiceError):
    """Raised when entity is not found."""


class EntityAlreadyExistsError(ConfigurationServiceError):
    """Raised when trying to add entity that already exists."""


class InvalidConfigurationError(ConfigurationServiceError):
    """Raised when configuration is invalid."""


class ConfigConflictError(ConfigurationServiceError):
    """Raised when optimistic lock fails due to concurrent modification."""


class ConfigurationYamlSpecification:
    """Specification for configuration files."""

    def is_satisfied_by(self, data: dict[str, Any]) -> bool:
        return "entities" in (data or {})


class ConfigurationService:
    """Service for managing configuration files and entities."""

    def __init__(self, configurations_dir: Path | None = None, state: ApplicationStateManager | None = None) -> None:
        """Initialize configuration service."""
        self.yaml_service: YamlService = get_yaml_service()
        self.configurations_dir: Path = configurations_dir or settings.CONFIGURATIONS_DIR
        self.specification = ConfigurationYamlSpecification()
        self.state: ApplicationStateManager = state or get_app_state_manager()

    def list_configurations(self) -> list[ConfigMetadata]:
        """
        List all available configuration files.

        Returns:
            List of configuration metadata
        """
        if not self.configurations_dir.exists():
            logger.warning(f"Configurations directory does not exist: {self.configurations_dir}")
            return []

        configs: list[ConfigMetadata] = []

        for yaml_file in self.configurations_dir.glob("*.yml"):
            try:
                data: dict[str, Any] = self.yaml_service.load(yaml_file)

                if not self.specification.is_satisfied_by(data):
                    logger.debug(f"Skipping {yaml_file.name} - does not satisfy configuration specification")
                    continue

                entity_count = len(data.get("entities", {}))

                metadata = ConfigMetadata(
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

    def load_configuration(self, name: str) -> Configuration:
        """
        Load configuration by name.

        If the configuration is currently active in ApplicationState,
        loads from there to ensure consistency with editing session.

        Args:
            name: Configuration name (without .yml extension)

        Returns:
            Configuration object

        Raises:
            ConfigurationNotFoundError: If configuration not found
            InvalidConfigurationError: If configuration is invalid
        """
        # Check application state if this is the active configuration
        active_config: Configuration | None = self.state.get(name)
        if active_config:
            logger.debug(f"Loading active configuration '{name}' from ApplicationState")
            return active_config

        filename: Path = self.configurations_dir / (f"{name.rstrip('.yml')}.yml")
        if not filename.exists():
            raise ConfigurationNotFoundError(f"Configuration not found: {name}")

        try:
            data: dict[str, Any] = self.yaml_service.load(filename)

            if not self.specification.is_satisfied_by(data):
                raise InvalidConfigurationError(f"Invalid configuration file '{name}': missing required 'entities' key")

            config: Configuration = ConfigMapper.to_api_config(data, name)

            assert config.metadata is not None  # For mypy

            config.metadata.file_path = str(filename)
            config.metadata.created_at = filename.stat().st_ctime
            config.metadata.modified_at = filename.stat().st_mtime
            config.metadata.entity_count = len(config.entities or {})
            config.metadata.is_valid = True

            logger.info(f"Loaded configuration '{name}' with {len(config.entities)} entities")
            return config

        except YamlLoadError as e:
            raise InvalidConfigurationError(f"Invalid YAML in configuration '{name}': {e}") from e
        except Exception as e:
            logger.error(f"Failed to load configuration '{name}': {e}")
            raise InvalidConfigurationError(f"Failed to load configuration '{name}': {e}") from e

    def save_configuration(self, config: Configuration, create_backup: bool = True) -> Configuration:
        """
        Save configuration to file.

        Updates ApplicationState if this is the active configuration.

        Args:
            config: Configuration to save
            create_backup: Whether to create backup before saving

        Returns:
            Updated configuration with new metadata

        Raises:
            InvalidConfigurationError: If save fails
        """
        if not config.metadata or not config.metadata.name:
            raise InvalidConfigurationError("Configuration must have metadata with name")

        file_path: Path = self.configurations_dir / f"{config.metadata.name.rstrip(".yml")}.yml"

        try:
            # Convert to core dict for saving (sparse structure)
            cfg_dict: dict[str, Any] = ConfigMapper.to_core_dict(config)

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
            raise InvalidConfigurationError(f"Failed to save configuration: {e}") from e
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            raise InvalidConfigurationError(f"Failed to save configuration: {e}") from e

    def create_configuration(self, name: str, entities: dict[str, Any] | None = None) -> Configuration:
        """
        Create new configuration.

        Args:
            name: Configuration name
            entities: Optional initial entities

        Returns:
            New configuration

        Raises:
            ConfigConflictError: If configuration already exists
        """
        file_path: Path = self.configurations_dir / f"{name}.yml"

        if file_path.exists():
            raise ConfigConflictError(f"Configuration '{name}' already exists")

        metadata: ConfigMetadata = ConfigMetadata(
            name=name,
            description=f"Configuration for {name}",
            version="1.0.0",
            file_path=str(file_path),
            entity_count=len(entities) if entities else 0,
            created_at=0,
            modified_at=0,
            is_valid=True,
        )

        config: Configuration = Configuration(entities=entities or {}, options={}, metadata=metadata)

        return self.save_configuration(config, create_backup=False)

    def delete_configuration(self, name: str) -> None:
        """
        Delete configuration file.

        Args:
            name: Configuration name

        Raises:
            ConfigurationNotFoundError: If configuration not found
        """
        file_path: Path = self.configurations_dir / f"{name}.yml"

        if not file_path.exists():
            raise ConfigurationNotFoundError(f"Configuration not found: {name}")

        try:
            self.yaml_service.create_backup(file_path)
            file_path.unlink()
            logger.info(f"Deleted configuration '{name}'")

        except Exception as e:
            logger.error(f"Failed to delete configuration '{name}': {e}")
            raise ConfigurationServiceError(f"Failed to delete configuration: {e}") from e

    def add_entity(self, config: Configuration, entity_name: str, entity: Entity) -> Configuration:
        """
        Add entity to configuration.

        Args:
            config: Configuration to modify
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

    def update_entity(self, config: Configuration, entity_name: str, entity: Entity) -> Configuration:
        """
        Update entity in configuration.

        Args:
            config: Configuration to modify
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

    def delete_entity(self, config: Configuration, entity_name: str) -> Configuration:
        """
        Delete entity from configuration.

        Args:
            config: Configuration to modify
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

    def get_entity(self, config: Configuration, entity_name: str) -> dict[str, Any]:
        """
        Get entity from configuration.

        Args:
            config: Configuration
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

    def add_entity_by_name(self, config_name: str, entity_name: str, entity_data: dict[str, Any]) -> None:
        """
        Add entity to configuration by config name.

        Args:
            config_name: Configuration name
            entity_name: Entity name
            entity_data: Entity data as dict

        Raises:
            ConfigurationNotFoundError: If configuration not found
            EntityAlreadyExistsError: If entity already exists
        """
        config: Configuration = self.load_configuration(config_name)

        if entity_name in config.entities:
            raise EntityAlreadyExistsError(f"Entity '{entity_name}' already exists")

        # Use the model's add_entity method to ensure proper handling
        config.add_entity(entity_name, entity_data)
        self.save_configuration(config)
        logger.info(f"Added entity '{entity_name}' to configuration '{config_name}'")

    def update_entity_by_name(self, config_name: str, entity_name: str, entity_data: dict[str, Any]) -> None:
        """
        Update entity in configuration by config name.

        Args:
            config_name: Configuration name
            entity_name: Entity name
            entity_data: Updated entity data as dict

        Raises:
            ConfigurationNotFoundError: If configuration not found
            EntityNotFoundError: If entity not found
        """
        config: Configuration = self.load_configuration(config_name)

        if entity_name not in config.entities:
            raise EntityNotFoundError(f"Entity '{entity_name}' not found")

        # Use the model's add_entity method to ensure proper handling
        config.add_entity(entity_name, entity_data)
        self.save_configuration(config)
        logger.info(f"Updated entity '{entity_name}' in configuration '{config_name}'")

    def delete_entity_by_name(self, config_name: str, entity_name: str) -> None:
        """
        Delete entity from configuration by config name.

        Args:
            config_name: Configuration name
            entity_name: Entity name

        Raises:
            ConfigurationNotFoundError: If configuration not found
            EntityNotFoundError: If entity not found
        """
        config: Configuration = self.load_configuration(config_name)

        if entity_name not in config.entities:
            raise EntityNotFoundError(f"Entity '{entity_name}' not found")

        del config.entities[entity_name]
        self.save_configuration(config)
        logger.info(f"Deleted entity '{entity_name}' from configuration '{config_name}'")

    def get_entity_by_name(self, config_name: str, entity_name: str) -> dict[str, Any]:
        """
        Get entity from configuration by config name.

        Args:
            config_name: Configuration name
            entity_name: Entity name

        Returns:
            Entity data as dict

        Raises:
            ConfigurationNotFoundError: If configuration not found
            EntityNotFoundError: If entity not found
        """
        config: Configuration = self.load_configuration(config_name)

        if entity_name not in config.entities:
            raise EntityNotFoundError(f"Entity '{entity_name}' not found")

        return config.entities[entity_name]

    def activate_configuration(self, name: str) -> Configuration:
        """
        Activate a configuration for editing.

        Loads the configuration into ApplicationState as the active editing session.

        Args:
            name: Configuration name to activate

        Returns:
            The activated configuration

        Raises:
            ConfigurationNotFoundError: If configuration not found
        """

        config: Configuration = self.load_configuration(name)

        self.state.activate(config)

        return config

    def get_active_configuration_metadata(self) -> ConfigMetadata:
        """
        Get the name of the currently active editing configuration.

        Returns:
            Configuration name or None if no configuration is active
        """

        return self.state.get_active_metadata()

    def save_with_version_check(
        self,
        config: Configuration,
        expected_version: str,
        create_backup: bool = True,
    ) -> Configuration:
        """
        Save configuration with optimistic concurrency control.

        Args:
            config: Configuration to save
            expected_version: Client's expected version number
            create_backup: Whether to create backup before saving

        Returns:
            Updated configuration

        Raises:
            ConfigConflictError: If version mismatch (concurrent edit detected)
            InvalidConfigurationError: If save fails
        """

        current_version: str = self.state.get_active_metadata().version or expected_version
        if expected_version != current_version:
            raise ConfigConflictError(
                f"Configuration was modified by another user. "
                f"Expected version {expected_version}, current version {current_version}. "
                f"Reload and merge changes."
            )

        return self.save_configuration(config, create_backup=create_backup)


# Singleton instance
_config_service: ConfigurationService | None = None  # pylint: disable=invalid-name


def get_config_service() -> ConfigurationService:
    """Get singleton ConfigurationService instance."""
    global _config_service  # pylint: disable=global-statement
    if _config_service is None:
        _config_service = ConfigurationService()
    return _config_service
