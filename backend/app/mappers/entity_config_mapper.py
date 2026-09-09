"""Strategy pattern for entity configuration mapping between API and Core layers.

This provides type-specific transformations for different entity types:
- File-based entities (CSV, Excel, Fixed Width) -> filename/location resolution
- Database entities (SQL) -> no-op
- Fixed entities -> fixed-value type coercion

Architecture:
- EntityConfigMapper: Protocol defining the interface
- DefaultEntityConfigMapper: No-op for entities that don't need transformation
- FileBasedEntityConfigMapper: Handles filename/location bidirectional mapping
- EntityConfigMapperFactory: Returns appropriate mapper based on driver type
"""

import abc
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from loguru import logger

from backend.app.core.config import Settings
from backend.app.utils.file_path_resolver import FilePathResolver
from src.types.fixed_entity_types import FixedEntityTypeCoercer, FixedEntityTypeConvention, normalize_fixed_entity_type_conventions

# p pylint: disable=too-few-public-methods


@dataclass(frozen=True)
class EntityMapperContext:
    """Per-call context shared by entity mappers."""

    project_name: str
    project_options: dict[str, Any] | None = None


class EntityConfigMapper(abc.ABC):
    """Strategy protocol for transforming entity configurations between API and Core layers."""

    def __init__(self, settings: Settings) -> None:
        self.settings: Settings = settings

    @abc.abstractmethod
    def to_api(self, entity_cfg: dict[str, Any], context: EntityMapperContext) -> dict[str, Any]:
        """Transform Core entity config to API format.

        Args:
            entity_cfg: Entity configuration from Core layer
            context: Per-call mapper context

        Returns:
            Transformed configuration for API layer
        """
        ...

    @abc.abstractmethod
    def to_core(self, entity_cfg: dict[str, Any], context: EntityMapperContext) -> dict[str, Any]:
        """Transform API entity config to Core format.

        Args:
            entity_cfg: Entity configuration from API layer
            context: Per-call mapper context

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

    def to_api(self, entity_cfg: dict[str, Any], context: EntityMapperContext) -> dict[str, Any]:
        """Return config unchanged (no transformation needed)."""
        return entity_cfg

    def to_core(self, entity_cfg: dict[str, Any], context: EntityMapperContext) -> dict[str, Any]:
        """Return config unchanged (no transformation needed)."""
        return entity_cfg


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

    def to_api(self, entity_cfg: dict[str, Any], context: EntityMapperContext) -> dict[str, Any]:
        """Decompose absolute file paths to (filename, location) for API.

        Args:
            config: Entity config with absolute paths in options.filename
            context: Per-call mapper context

        Returns:
            Config with filename and location fields populated
        """
        options: dict[str, Any] | None = entity_cfg.get("options")
        if not options or not isinstance(options, dict):
            return entity_cfg

        filename_str: str | None = options.get("filename")
        if not filename_str:
            return entity_cfg

        # Decompose absolute path into location + filename
        result = self.path_resolver.decompose(Path(filename_str), context.project_name)
        if result:
            relative_filename, location = result
            options["filename"] = relative_filename
            options["location"] = location
            logger.debug(f"[FileBasedMapper] Decomposed {filename_str} -> {relative_filename} ({location})")
        # else: keep absolute path if outside managed directories

        return entity_cfg

    def to_core(self, entity_cfg: dict[str, Any], context: EntityMapperContext) -> dict[str, Any]:
        """Resolve (filename, location) to absolute paths for Core.

        Args:
            entity_cfg: Entity config with filename and location fields
            context: Per-call mapper context

        Returns:
            Config with resolved absolute paths in options.filename
        """
        options: dict[str, Any] | None = entity_cfg.get("options")
        if not options or not isinstance(options, dict):
            return entity_cfg

        filename_str: str | None = options.get("filename")

        if not filename_str:
            return entity_cfg

        # Get location (explicit field or extract from legacy format)
        location: str | None = options.get("location")
        if not location:
            # Support legacy format: "${GLOBAL_DATA_DIR}/file.xlsx"
            filename_str, location = self.path_resolver.extract_location(filename_str)
            if not location:
                logger.warning(f"No location specified for file '{filename_str}', defaulting to global")
                location = "global"

        # Resolve to absolute path
        absolute_path: Path = self.path_resolver.resolve(filename_str, location, context.project_name)  # type: ignore
        options["filename"] = str(absolute_path)

        # Remove location field (Core doesn't use it)
        if "location" in options:
            del options["location"]

        logger.debug(f"[FileBasedMapper] Resolved ({filename_str}, {location}) -> {absolute_path}")

        return entity_cfg


class FixedEntityConfigMapper(EntityConfigMapper):
    """Mapper for fixed entities with load-time type coercion."""

    def to_api(self, entity_cfg: dict[str, Any], context: EntityMapperContext) -> dict[str, Any]:
        """Return config unchanged for API serialization."""
        return entity_cfg

    def to_core(self, entity_cfg: dict[str, Any], context: EntityMapperContext) -> dict[str, Any]:
        """Coerce fixed entity values to their inferred in-memory types."""
        columns = entity_cfg.get("columns", [])
        if not isinstance(columns, list) or not columns:
            return entity_cfg

        entity_name = str(entity_cfg.get("name") or "<unknown>")
        conventions: list[FixedEntityTypeConvention] = normalize_fixed_entity_type_conventions(context.project_options)
        entity_cfg["values"] = FixedEntityTypeCoercer.coerce_fixed_entity_values(
            entity_cfg,
            columns,
            entity_name=entity_name,
            conventions=conventions,
        )
        return entity_cfg


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
        self._fixed_mapper = FixedEntityConfigMapper(settings)
        self._default_mapper = DefaultEntityConfigMapper(settings)
        self._mapper_cache: dict[str, EntityConfigMapper] = {
            "csv": self._file_mapper,
            "xlsx": self._file_mapper,
            "openpyxl": self._file_mapper,
            "fixed": self._fixed_mapper,
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
