"""Configuration service for managing entity configurations."""

from pathlib import Path
from typing import Any

from loguru import logger

from backend.app.core.config import settings
from backend.app.models.config import ConfigMetadata, Configuration
from backend.app.models.entity import Entity
from backend.app.services.yaml_service import YamlLoadError, YamlSaveError, get_yaml_service
from src.configuration.config import ConfigFactory
from src.configuration.interface import ConfigLike
from src.configuration.provider import ConfigStore


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


class ConfigurationService:
    """Service for managing configuration files and entities."""

    def __init__(self) -> None:
        """Initialize configuration service."""
        self.yaml_service = get_yaml_service()
        self.configurations_dir = settings.CONFIGURATIONS_DIR

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
                data = self.yaml_service.load(yaml_file)

                # Only include files that have 'entities' key (configuration files)
                if "entities" not in data:
                    logger.debug(f"Skipping {yaml_file.name} - missing 'entities' key")
                    continue

                entity_count = len(data.get("entities", {}))

                metadata = ConfigMetadata(
                    name=yaml_file.stem,
                    file_path=str(yaml_file),
                    entity_count=entity_count,
                    created_at=yaml_file.stat().st_ctime,
                    modified_at=yaml_file.stat().st_mtime,
                    is_valid=True,  # Basic check - more validation available via validation service
                )
                configs.append(metadata)

            except Exception as e:  # pylint: disable=broad-except
                logger.warning(f"Failed to load configuration {yaml_file}: {e}")
                # Skip invalid configs - don't include them in the list

        logger.debug(f"Found {len(configs)} configuration(s)")
        return configs

    def load_configuration(self, name: str) -> Configuration:
        """
        Load configuration by name.

        Args:
            name: Configuration name (without .yml extension)

        Returns:
            Configuration object

        Raises:
            ConfigurationNotFoundError: If configuration not found
            InvalidConfigurationError: If configuration is invalid
        """
        file_path = self.configurations_dir / f"{name}.yml"

        if not file_path.exists():
            raise ConfigurationNotFoundError(f"Configuration not found: {name}")

        try:
            data = self.yaml_service.load(file_path)

            # Validate that 'entities' key exists (required for configuration files)
            if "entities" not in data:
                raise InvalidConfigurationError(f"Invalid configuration file '{name}': missing required 'entities' key")

            # Extract entities and options
            entities_data = data.get("entities", {})
            options_data = data.get("options", {})

            # Create metadata
            metadata = ConfigMetadata(
                name=name,
                file_path=str(file_path),
                entity_count=len(entities_data),
                created_at=file_path.stat().st_ctime,
                modified_at=file_path.stat().st_mtime,
                is_valid=True,
            )

            # Build configuration
            config = Configuration(entities=entities_data, options=options_data, metadata=metadata)

            logger.info(f"Loaded configuration '{name}' with {len(entities_data)} entities")
            return config

        except YamlLoadError as e:
            raise InvalidConfigurationError(f"Invalid YAML in configuration '{name}': {e}") from e
        except Exception as e:
            logger.error(f"Failed to load configuration '{name}': {e}")
            raise InvalidConfigurationError(f"Failed to load configuration '{name}': {e}") from e

    def save_configuration(self, config: Configuration, create_backup: bool = True) -> Configuration:
        """
        Save configuration to file.

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

        file_path = self.configurations_dir / f"{config.metadata.name}.yml"

        try:
            # Build YAML data
            data: dict[str, Any] = {}

            # Always include 'entities' key to mark this as a configuration file
            data["entities"] = config.entities if config.entities else {}

            logger.debug(
                f"Saving configuration '{config.metadata.name}' with {len(config.entities)} entities: {list(config.entities.keys())}"
            )

            if config.options:
                data["options"] = config.options

            # Save with backup
            self.yaml_service.save(data, file_path, create_backup=create_backup)

            # Update metadata
            config.metadata.modified_at = file_path.stat().st_mtime
            config.metadata.entity_count = len(config.entities)

            logger.info(f"Saved configuration '{config.metadata.name}'")
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
            ConfigurationServiceError: If configuration already exists
        """
        file_path = self.configurations_dir / f"{name}.yml"

        if file_path.exists():
            raise ConfigurationServiceError(f"Configuration '{name}' already exists")

        # Create metadata
        metadata = ConfigMetadata(
            name=name,
            file_path=str(file_path),
            entity_count=len(entities) if entities else 0,
            created_at=0,
            modified_at=0,
            is_valid=True,
        )

        # Create configuration
        config = Configuration(entities=entities or {}, options={}, metadata=metadata)

        # Save to file
        return self.save_configuration(config, create_backup=False)

    def delete_configuration(self, name: str) -> None:
        """
        Delete configuration file.

        Args:
            name: Configuration name

        Raises:
            ConfigurationNotFoundError: If configuration not found
        """
        file_path = self.configurations_dir / f"{name}.yml"

        if not file_path.exists():
            raise ConfigurationNotFoundError(f"Configuration not found: {name}")

        try:
            # Create backup before deleting
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

        # Add entity (Pydantic model will be serialized to dict)
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

        # Update entity
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
        config = self.load_configuration(config_name)

        if entity_name not in config.entities:
            raise EntityNotFoundError(f"Entity '{entity_name}' not found")

        return config.entities[entity_name]

    def get_active_configuration_name(self) -> str | None:
        """
        Get the currently active (loaded) configuration name.

        The active configuration is the one loaded into the backend's ConfigStore,
        which determines which data sources are available.

        Returns:
            Configuration name (without .yml extension) or None if no config is loaded
        """

        try:
            store: ConfigStore = ConfigStore.get_instance()
            if not store.is_configured():
                return None

            config: ConfigLike | None = store.config()
            if config is None:
                return None

            # Get filename from config
            filename = getattr(config, "filename", None) or getattr(config, "source", None)
            if not filename:
                return None

            # Extract name from filename (remove .yml extension and path)

            return Path(filename).stem

        except Exception as e:  # pylint: disable=broad-except
            logger.warning(f"Failed to get active configuration name: {e}")
            return None

    def activate_configuration(self, name: str) -> Configuration:
        """
        Activate (load) a configuration into the backend context.

        This makes the configuration's data sources available and sets it
        as the active configuration.

        Args:
            name: Configuration name to activate

        Returns:
            The activated configuration

        Raises:
            ConfigurationNotFoundError: If configuration not found
        """

        # Build file path
        file_path = self.configurations_dir / f"{name}.yml"

        if not file_path.exists():
            raise ConfigurationNotFoundError(f"Configuration not found: {name}")

        try:
            # Load configuration using ConfigFactory
            loaded_config = ConfigFactory().load(source=str(file_path), context="default")

            # Set as active in ConfigStore
            ConfigStore.get_instance().set_config(cfg=loaded_config, context="default")

            logger.info(f"Activated configuration '{name}' from {file_path}")

            # Return as Configuration model for API response
            return self.load_configuration(name)

        except Exception as e:
            logger.error(f"Failed to activate configuration '{name}': {e}")
            raise ConfigurationServiceError(f"Failed to activate configuration: {e}") from e

    def save_with_version_check(
        self,
        config: Configuration,
        expected_version: int,
        current_version: int,
        create_backup: bool = True,
    ) -> Configuration:
        """
        Save configuration with optimistic concurrency control.

        Args:
            config: Configuration to save
            expected_version: Client's expected version number
            current_version: Current server version number
            create_backup: Whether to create backup before saving

        Returns:
            Updated configuration

        Raises:
            ConfigConflictError: If version mismatch (concurrent edit detected)
            InvalidConfigurationError: If save fails
        """
        # Check version match (optimistic lock)
        if expected_version != current_version:
            raise ConfigConflictError(
                f"Configuration was modified by another user. "
                f"Expected version {expected_version}, current version {current_version}. "
                f"Reload and merge changes."
            )

        # Save to disk
        return self.save_configuration(config, create_backup=create_backup)


# Singleton instance
_config_service: ConfigurationService | None = None  # pylint: disable=invalid-name


def get_config_service() -> ConfigurationService:
    """Get singleton ConfigurationService instance."""
    global _config_service  # pylint: disable=global-statement
    if _config_service is None:
        _config_service = ConfigurationService()
    return _config_service
