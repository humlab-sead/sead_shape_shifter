"""Centralized file path resolution for entity file handling.

This module provides a single source of truth for resolving file paths across
all layers of the application. It handles the translation between:
- API layer: location field ("global"|"local") + relative filename
- Core layer: absolute paths only
- Legacy format: ${GLOBAL_DATA_DIR}/filename

Architecture:
- API → Core: resolve() converts location + filename → absolute path
- Core → API: decompose() extracts location from absolute path
- Backward compatibility: extract_location() parses legacy format

All path resolution logic is centralized here, eliminating scattered
implementations across endpoints, services, and mappers.
"""

from pathlib import Path
from typing import Any, Literal

from loguru import logger

from backend.app.core.config import Settings
from backend.app.mappers.project_name_mapper import ProjectNameMapper


class FilePathResolver:
    """Centralized file path resolution for entity file handling.
    
    This class is the single source of truth for all file path resolution in the application.
    It provides bidirectional conversion between API layer (location + filename) and 
    Core layer (absolute paths).
    """

    def __init__(self, settings: Settings) -> None:
        """Initialize resolver with application settings.
        
        Args:
            settings: Application settings containing data directory paths
        """
        self.settings = settings

    def resolve(
        self,
        filename: str,
        location: Literal["global", "local"],
        project_name: str | None = None,
    ) -> Path:
        """Resolve filename to absolute path based on location.
        
        This is the primary method for API → Core resolution. It converts a location
        field and relative filename into an absolute path that Core can use directly.
        
        Args:
            filename: Relative filename (e.g., "data.xlsx" or "subdir/data.xlsx")
            location: File location - "global" (GLOBAL_DATA_DIR) or "local" (project-specific)
            project_name: Project name required for location="local" (e.g., "dendro:sites")
        
        Returns:
            Absolute path to the file
        
        Raises:
            ValueError: If location is invalid or project_name missing for local files
        
        Examples:
            >>> resolver.resolve("specimens.csv", "global")
            Path("/app/shared/shared-data/specimens.csv")
            
            >>> resolver.resolve("data/sites.xlsx", "local", "dendro:sites")
            Path("/app/projects/dendro/sites/data/sites.xlsx")
        """
        if location not in ["global", "local"]:
            raise ValueError(f"Invalid location: {location}. Must be 'global' or 'local'")

        if location == "global":
            resolved_path = self.settings.GLOBAL_DATA_DIR / filename
            logger.debug(f"Resolved global file: {filename} -> {resolved_path}")
            return resolved_path

        if location == "local":
            if not project_name:
                raise ValueError(f"project_name required for local file resolution: {filename}")

            # Convert project name (e.g., "dendro:sites") to path ("dendro/sites")
            project_path = ProjectNameMapper.to_path(project_name)
            resolved_path = self.settings.PROJECTS_DIR / project_path / filename
            logger.debug(f"Resolved local file: {filename} ({project_name}) -> {resolved_path}")
            return resolved_path

        # Unreachable due to validation above, but for type safety
        raise ValueError(f"Unexpected location value: {location}")

    def decompose(self, absolute_path: Path, project_name: str | None = None) -> tuple[str, Literal["global", "local"]] | None:
        """Decompose absolute path into (filename, location) for API layer.
        
        This is the reverse operation of resolve() - it takes an absolute path from Core
        and extracts the location semantics for the API layer. This enables round-tripping
        Core → API → Core without losing information.
        
        Args:
            absolute_path: Absolute file path from Core layer
            project_name: Project name for local path resolution (e.g., "dendro:sites")
        
        Returns:
            Tuple of (relative_filename, location) or None if path is outside managed directories
        
        Examples:
            >>> resolver.decompose(Path("/app/shared/shared-data/specimens.csv"))
            ("specimens.csv", "global")
            
            >>> resolver.decompose(Path("/app/projects/dendro/sites/data.xlsx"), "dendro:sites")
            ("data.xlsx", "local")
            
            >>> resolver.decompose(Path("/external/file.csv"))
            None  # Outside managed directories
        """
        # Try global directory first
        try:
            relative_path = absolute_path.relative_to(self.settings.GLOBAL_DATA_DIR)
            return (str(relative_path), "global")
        except ValueError:
            pass  # Not in global directory

        # Try project-specific directory
        if project_name:
            try:
                project_path = ProjectNameMapper.to_path(project_name)
                project_dir = self.settings.PROJECTS_DIR / project_path
                relative_path = absolute_path.relative_to(project_dir)
                return (str(relative_path), "local")
            except ValueError:
                pass  # Not in project directory

        # Path is outside both managed directories
        logger.warning(f"File path outside managed directories: {absolute_path}")
        return None

    def extract_location(self, filename: str) -> tuple[str, Literal["global", "local"]]:
        """Extract location from legacy filename format.
        
        Supports backward compatibility with old YAML files using the ${GLOBAL_DATA_DIR}/
        prefix format. This allows gradual migration from legacy format to explicit
        location field.
        
        Args:
            filename: Filename that may contain ${GLOBAL_DATA_DIR}/ prefix
        
        Returns:
            Tuple of (clean_filename, location)
        
        Examples:
            >>> resolver.extract_location("${GLOBAL_DATA_DIR}/data.xlsx")
            ("data.xlsx", "global")
            
            >>> resolver.extract_location("data.xlsx")
            ("data.xlsx", "local")
        """
        if filename.startswith("${GLOBAL_DATA_DIR}/"):
            clean_filename = filename.replace("${GLOBAL_DATA_DIR}/", "")
            return (clean_filename, "global")

        # Default to local for files without prefix
        return (filename, "local")

    def to_legacy_format(self, filename: str, location: Literal["global", "local"]) -> str:
        """Convert filename + location to legacy format for YAML storage.
        
        This provides backward compatibility when saving YAML files, allowing older
        versions of the application to read the files.
        
        Args:
            filename: Relative filename
            location: File location
        
        Returns:
            Filename in legacy format (with ${GLOBAL_DATA_DIR}/ prefix for global files)
        
        Examples:
            >>> resolver.to_legacy_format("data.xlsx", "global")
            "${GLOBAL_DATA_DIR}/data.xlsx"
            
            >>> resolver.to_legacy_format("data.xlsx", "local")
            "data.xlsx"
        """
        if location == "global":
            return f"${{GLOBAL_DATA_DIR}}/{filename}"
        return filename

    def resolve_in_entity_config(self, entity_config: dict[str, Any], project_name: str) -> None:
        """Resolve file paths in entity config dictionary.
        
        Modifies entity_config in-place to convert filename to absolute path.
        This is useful when processing entity configurations that bypass the
        normal ProjectMapper.to_core() flow (e.g., preview overrides).
        
        Args:
            entity_config: Entity configuration dictionary (modified in-place)
            project_name: Project name for resolving local paths
        
        Examples:
            >>> config = {"options": {"filename": "data.csv", "location": "global"}}
            >>> resolver.resolve_in_entity_config(config, "my_project")
            >>> config["options"]["filename"]
            "/app/shared/shared-data/data.csv"
        """
        options = entity_config.get("options")
        if not options or not isinstance(options, dict):
            return

        filename = options.get("filename")
        if not filename:
            return

        # Get location (explicit field or extract from legacy format)
        location: str | None = options.get("location")
        if not location:
            # Support legacy format: "${GLOBAL_DATA_DIR}/file.xlsx"
            filename, location = self.extract_location(filename)

        if location not in ["global", "local"]:
            logger.warning(f"Unknown location '{location}' for file '{filename}', defaulting to global")
            location = "global"

        # Resolve to absolute path using centralized resolver
        try:
            resolved_path = self.resolve(filename, location, project_name)  # type: ignore
            options["filename"] = str(resolved_path)
            # Remove location from Core (Core doesn't need location awareness)
            options.pop("location", None)
            logger.debug(f"Resolved {location} file in config: {filename} -> {resolved_path}")
        except ValueError as e:
            logger.warning(f"Failed to resolve path in config: {e}")
            # Keep original filename if resolution fails
