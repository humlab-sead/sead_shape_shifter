"""Strategy pattern for entity configuration mapping between API and Core layers.

This provides type-specific transformations for different entity types:
- File-based entities (CSV, Excel, Fixed Width) -> filename/location resolution
- Database entities (SQL) -> no-op
- Fixed entities -> no-op

Architecture:
- EntityConfigMapper: Protocol defining the interface
- DefaultEntityConfigMapper: No-op for entities that don't need transformation
- FileBasedEntityConfigMapper: Handles filename/location bidirectional mapping
- EntityConfigMapperFactory: Returns appropriate mapper based on driver type
"""

import abc
from pathlib import Path
from typing import Any

from loguru import logger

from backend.app.core.config import Settings
from backend.app.utils.file_path_resolver import FilePathResolver

# p pylint: disable=too-few-public-methods


class EntityConfigMapper(abc.ABC):
    """Strategy protocol for transforming entity configurations between API and Core layers."""

    def __init__(self, settings: Settings) -> None:
        self.settings: Settings = settings

    @abc.abstractmethod
    def to_api(self, config: dict[str, Any], project_name: str) -> dict[str, Any]:
        """Transform Core entity config to API format.

        Args:
            config: Entity configuration from Core layer
            project_name: Project name for path resolution

        Returns:
            Transformed configuration for API layer
        """
        ...

    @abc.abstractmethod
    def to_core(self, config: dict[str, Any], project_name: str) -> dict[str, Any]:
        """Transform API entity config to Core format.

        Args:
            config: Entity configuration from API layer
            project_name: Project name for path resolution

        Returns:
            Transformed configuration for Core layer
        """
        ...


class DefaultEntityConfigMapper(EntityConfigMapper):
    """No-op mapper for entities that don't need layer-specific transformations.

    Used for:
    - Fixed value entities
    - SQL-based entities (PostgreSQL, SQLite, MS Access)
    - Any entity without file path dependencies
    """

    def to_api(self, config: dict[str, Any], project_name: str) -> dict[str, Any]:
        """Return config unchanged (no transformation needed)."""
        return config

    def to_core(self, config: dict[str, Any], project_name: str) -> dict[str, Any]:
        """Return config unchanged (no transformation needed)."""
        return config


class FileBasedEntityConfigMapper(EntityConfigMapper):
    """Mapper for file-based entities (CSV, Excel, Fixed Width).

    Handles bidirectional transformation of file paths:
    - API → Core: Resolve (filename, location) → absolute path
    - Core → API: Decompose absolute path → (filename, location)
    """

    def __init__(self, settings: Settings):
        """Initialize with settings.

        Args:
            settings: Application settings
        """
        super().__init__(settings)
        self.path_resolver = FilePathResolver(settings)

    def to_api(self, config: dict[str, Any], project_name: str) -> dict[str, Any]:
        """Decompose absolute file paths to (filename, location) for API.

        Args:
            config: Entity config with absolute paths in options.filename
            project_name: Project name for path decomposition

        Returns:
            Config with filename and location fields populated
        """
        options = config.get("options")
        if not options or not isinstance(options, dict):
            return config

        filename_str: str | None = options.get("filename")
        if not filename_str:
            return config

        # Decompose absolute path into location + filename
        result = self.path_resolver.decompose(Path(filename_str), project_name)
        if result:
            relative_filename, location = result
            options["filename"] = relative_filename
            options["location"] = location
            logger.debug(f"[FileBasedMapper] Decomposed {filename_str} -> {relative_filename} ({location})")
        # else: keep absolute path if outside managed directories

        return config

    def to_core(self, config: dict[str, Any], project_name: str) -> dict[str, Any]:
        """Resolve (filename, location) to absolute paths for Core.

        Args:
            config: Entity config with filename and location fields
            project_name: Project name for path resolution

        Returns:
            Config with resolved absolute paths in options.filename
        """
        options = config.get("options")
        if not options or not isinstance(options, dict):
            return config

        filename_str: str | None = options.get("filename")

        if not filename_str:
            return config

        # Get location (explicit field or extract from legacy format)
        location: str | None = options.get("location")
        if not location:
            # Support legacy format: "${GLOBAL_DATA_DIR}/file.xlsx"
            filename_str, location = self.path_resolver.extract_location(filename_str)
            if not location:
                logger.warning(f"No location specified for file '{filename_str}', defaulting to global")
                location = "global"

        # Resolve to absolute path
        absolute_path = self.path_resolver.resolve(filename_str, location, project_name)  # type: ignore
        options["filename"] = str(absolute_path)

        # Remove location field (Core doesn't use it)
        if "location" in options:
            del options["location"]

        logger.debug(f"[FileBasedMapper] Resolved ({filename_str}, {location}) -> {absolute_path}")

        return config


class EntityConfigMapperFactory:
    """Factory for creating appropriate entity config mappers based on entity type.

    Maintains registry of file-based drivers and returns specialized mappers.
    """

    # File-based drivers that need path resolution
    FILE_BASED_DRIVERS: set[str] = {"csv", "xlsx", "openpyxl"}

    def __init__(self, settings: Settings):
        """Initialize factory with settings.

        Args:
            settings: Application settings for path resolution
        """
        self._file_mapper = FileBasedEntityConfigMapper(settings)
        self._default_mapper = DefaultEntityConfigMapper(settings)
        self._mapper_cache: dict[str, EntityConfigMapper] = {
            "csv": self._file_mapper,
            "xlsx": self._file_mapper,
            "openpyxl": self._file_mapper,
        }

    def get_mapper(self, entity_type: str) -> EntityConfigMapper:
        """Get appropriate mapper based on entity type.

        Args:
            entity_type: Entity type (e.g., "csv", "xlsx", "openpyxl", "fixed", "sql")

        Returns:
            EntityConfigMapper instance (either file-based or default)
        """
        return self._mapper_cache.get(entity_type, self._default_mapper)

    def get_mapper_for_entity(self, entity_config: dict[str, Any]) -> EntityConfigMapper:
        """Get mapper based on entity's type.

        Args:
            entity_config: Entity configuration dictionary

        Returns:
            EntityConfigMapper instance appropriate for this entity
        """

        entity_type: str = entity_config.get("type") or ""

        return self.get_mapper(entity_type)
