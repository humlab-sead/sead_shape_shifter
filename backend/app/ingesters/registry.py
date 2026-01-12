"""Registry for data ingesters.

This module provides a registry for auto-discovering and managing available ingesters.
Uses the same Registry pattern as Shape Shifter's Dispatchers with added dynamic discovery.
"""

import importlib
import sys
from pathlib import Path
from typing import Type

from loguru import logger

from backend.app.ingesters.protocol import Ingester, IngesterMetadata
from src.utility import Registry


class IngesterRegistry(Registry[type[Ingester]]):
    """Registry for data ingesters.

    Ingesters register themselves using the @Ingesters.register() decorator.
    The registry can also dynamically discover ingesters from configured paths.

    Example:
        @Ingesters.register(key="sead")
        class SeadIngester:
            @classmethod
            def get_metadata(cls) -> IngesterMetadata:
                return IngesterMetadata(
                    key="sead",
                    name="SEAD Clearinghouse",
                    description="Ingest data into SEAD database",
                    version="1.0.0",
                    supported_formats=["xlsx"],
                    requires_config=True,
                )

            async def validate(self, excel_file: Path | str) -> ValidationResult:
                ...

            async def ingest(self, excel_file: Path | str, validate_first: bool = True) -> IngestionResult:
                ...
    """

    items: dict[str, type[Ingester]] = {}
    _initialized: bool = False

    @classmethod
    def get(cls, key: str) -> None | type[Ingester]:  # type: ignore[override]
        """Get ingester by key, returning None if not found (overrides Registry.get)."""
        if key not in cls.items:
            return None
        return cls.items[key]

    def discover(self, search_paths: list[str] | None = None, enabled_only: list[str] | None = None) -> None:
        """Discover and load ingesters from configured paths.

        This method scans directories for ingester implementations and dynamically
        imports them. Ingesters register themselves via the @Ingesters.register()
        decorator during import.

        Args:
            search_paths: List of paths to search for ingesters (default: ["ingesters"])
            enabled_only: List of ingester names to load (None = load all discovered)

        Example:
            Ingesters.discover(search_paths=["ingesters"], enabled_only=["sead"])
        """
        if self._initialized:
            logger.debug("Ingester discovery already completed, skipping")
            return

        search_paths = search_paths or ["ingesters"]

        logger.info(f"Discovering ingesters from paths: {', '.join(search_paths)}")

        for search_path in search_paths:
            path = Path(search_path)
            if not path.exists():
                logger.warning(f"Ingester search path does not exist: {path}")
                continue

            if not path.is_dir():
                logger.warning(f"Ingester search path is not a directory: {path}")
                continue

            for ingester_dir in path.iterdir():
                if not ingester_dir.is_dir():
                    continue
                
                # Skip special directories
                if ingester_dir.name.startswith(("_", ".")):
                    continue

                ingester_name = ingester_dir.name

                # Skip if not in enabled list
                if enabled_only and ingester_name not in enabled_only:
                    logger.debug(f"Skipping disabled ingester: {ingester_name}")
                    continue

                # Skip if already loaded
                if ingester_name in self.items:
                    logger.debug(f"Ingester '{ingester_name}' already registered, skipping")
                    continue

                # Try to load ingester module
                try:
                    self._load_ingester(search_path, ingester_name)
                except Exception as e:  # pylint: disable=broad-except
                    logger.error(f"Failed to load ingester '{ingester_name}': {e}")
                    logger.exception(e)

        self._initialized = True
        logger.info(f"Ingester discovery complete. Loaded {len(self.items)} ingester(s): {', '.join(self.items.keys())}")

    def _load_ingester(self, base_path: str, name: str) -> None:
        """Load a single ingester from directory.

        Args:
            base_path: Base path where ingester directories are located
            name: Name of the ingester (directory name)

        Raises:
            ImportError: If ingester module cannot be imported
            ValueError: If ingester doesn't register itself properly
        """
        module_path = f"{base_path}.{name}.ingester"

        logger.debug(f"Loading ingester module: {module_path}")

        # Ensure base path is in Python path
        workspace_root = Path.cwd()
        if str(workspace_root) not in sys.path:
            sys.path.insert(0, str(workspace_root))

        # Dynamic import
        try:
            module = importlib.import_module(module_path)
        except ImportError as e:
            raise ImportError(f"Failed to import {module_path}: {e}") from e

        # Verify ingester registered itself
        if name not in self.items:
            raise ValueError(
                f"Ingester module '{module_path}' loaded but class not registered. "
                f"Ensure class is decorated with @Ingesters.register(key='{name}')"
            )

        logger.info(f"Successfully loaded ingester: {name}")

    def get_metadata_list(self) -> list[IngesterMetadata]:
        """Get metadata for all registered ingesters.

        Returns:
            List of IngesterMetadata for all registered ingesters
        """
        return [cls.get_metadata() for cls in self.items.values()]


# Global registry instance
Ingesters = IngesterRegistry()  # pylint: disable=invalid-name
