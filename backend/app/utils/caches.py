import hashlib
import time
from dataclasses import dataclass

import pandas as pd
from loguru import logger

from backend.app.core.state_manager import get_app_state
from backend.app.mappers.config_mapper import ConfigMapper
from backend.app.models.config import Configuration
from backend.app.services.config_service import ConfigurationService
from src.model import ShapeShiftConfig, TableConfig


@dataclass
class CacheMetadata:
    """Metadata for cached entity DataFrame."""

    timestamp: float
    config_name: str
    entity_name: str
    config_version: int
    entity_hash: str  # Hash of entity configuration


class ShapeShiftCache:
    """Cache for ShapeShifter results with individual entity storage.

    Caches individual DataFrames per entity, enabling better cache efficiency
    and granular invalidation. Dependencies are stored separately and reused
    across multiple entities.

    Uses 3-tier cache validation:
    1. TTL (time-to-live) - Expire after fixed duration
    2. Config version - Invalidate on configuration file changes
    3. Entity hash - Invalidate on entity-specific configuration changes
    """

    def __init__(self, ttl_seconds: int = 300):
        """Initialize cache with TTL in seconds (default 5 minutes)."""
        # Store individual DataFrames: key -> DataFrame
        self._dataframes: dict[str, pd.DataFrame] = {}
        # Store metadata: key -> CacheMetadata
        self._metadata: dict[str, CacheMetadata] = {}
        self._ttl: int = ttl_seconds

    def _generate_key(self, config_name: str, entity_name: str) -> str:
        """Generate cache key from config and entity name."""
        key_str = f"{config_name}:{entity_name}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def get_dataframe(
        self,
        config_name: str,
        entity_name: str,
        config_version: int | None = None,
        entity_config: TableConfig | None = None,
    ) -> pd.DataFrame | None:
        """Get cached DataFrame for entity with 3-tier validation.

        Validation order:
        1. TTL - Check if cache entry has expired
        2. Config version - Validate against ApplicationState version
        3. Entity hash - Validate against entity configuration hash

        Args:
            config_name: Configuration name
            entity_name: Entity name
            config_version: Optional config version for validation (from ApplicationState)
            entity_config: Optional entity configuration for hash validation

        Returns:
            DataFrame if cached and valid, None otherwise
        """
        key = self._generate_key(config_name, entity_name)
        if key not in self._dataframes or key not in self._metadata:
            return None

        metadata = self._metadata[key]

        # Tier 1: Check TTL
        if time.time() - metadata.timestamp >= self._ttl:
            del self._dataframes[key]
            del self._metadata[key]
            logger.debug(f"Cache expired for {entity_name} (TTL)")
            return None

        # Tier 2: Check config version if provided
        if config_version is not None and metadata.config_version != config_version:
            del self._dataframes[key]
            del self._metadata[key]
            logger.debug(f"Cache invalidated for {entity_name} (version mismatch: {metadata.config_version} != {config_version})")
            return None

        # Tier 3: Check entity hash if entity_config provided
        if entity_config is not None:
            current_hash = entity_config.hash()
            if metadata.entity_hash != current_hash:
                del self._dataframes[key]
                del self._metadata[key]
                logger.debug(
                    f"Cache invalidated for {entity_name} (entity config changed: {metadata.entity_hash[:8]} != {current_hash[:8]})"
                )
                return None

        logger.debug(f"Cache hit for {entity_name} (valid: TTL + version + hash)")
        return self._dataframes[key].copy()  # Return copy to prevent modifications

    def set_dataframe(
        self,
        config_name: str,
        entity_name: str,
        dataframe: pd.DataFrame,
        config_version: int = 0,
        entity_config: TableConfig | None = None,
    ) -> None:
        """Cache DataFrame for entity with metadata including entity hash.

        Args:
            config_name: Configuration name
            entity_name: Entity name
            dataframe: DataFrame to cache
            config_version: Configuration version from ApplicationState
            entity_config: Entity configuration for hash computation
        """
        key: str = self._generate_key(config_name, entity_name)
        self._dataframes[key] = dataframe.copy()  # Store copy to prevent external modifications

        # Compute entity hash if config provided, otherwise use empty hash
        entity_hash = entity_config.hash() if entity_config else ""

        self._metadata[key] = CacheMetadata(
            timestamp=time.time(),
            config_name=config_name,
            entity_name=entity_name,
            config_version=config_version,
            entity_hash=entity_hash,
        )
        logger.debug(f"Cached DataFrame for {entity_name} (version {config_version}, hash {entity_hash[:8]}, {len(dataframe)} rows)")

    def set_table_store(
        self,
        config_name: str,
        table_store: dict[str, pd.DataFrame],
        target_entity: str,
        config_version: int = 0,
        entity_configs: dict[str, TableConfig] | None = None,
    ) -> None:
        """Cache all entities from table_store individually with entity hashes.

        Args:
            config_name: Configuration name
            table_store: Dict of entity_name -> DataFrame
            target_entity: Target entity name (for logging)
            config_version: Configuration version from ApplicationState
            entity_configs: Optional dict of entity_name -> TableConfig for hash computation
        """
        for entity_name, df in table_store.items():
            entity_config = entity_configs.get(entity_name) if entity_configs else None
            self.set_dataframe(config_name, entity_name, df, config_version, entity_config)
        logger.debug(f"Cached {len(table_store)} entities from {target_entity} execution")

    def gather_cached_dependencies(
        self,
        config_name: str,
        entity_config: TableConfig,
        config_version: int | None = None,
        shapeshift_config: ShapeShiftConfig | None = None,
    ) -> dict[str, pd.DataFrame]:
        """Gather all cached dependencies for an entity with hash validation.

        Args:
            config_name: Configuration name
            entity_config: Target entity configuration
            config_version: Optional config version for validation
            shapeshift_config: Optional ShapeShiftConfig for dependency hash validation

        Returns:
            Dict of cached entity DataFrames
        """
        cached_deps: dict[str, pd.DataFrame] = {}
        for dep_name in entity_config.depends_on:
            # Get dependency config for hash validation if available
            dep_config = shapeshift_config.get_table(dep_name) if shapeshift_config else None
            cached_df = self.get_dataframe(config_name, dep_name, config_version, dep_config)
            if cached_df is not None:
                cached_deps[dep_name] = cached_df

        if cached_deps:
            logger.debug(f"Found {len(cached_deps)} cached dependencies for {entity_config.entity_name}: {list(cached_deps.keys())}")

        return cached_deps

    def get_available_entities(self, config_name: str) -> set[str]:
        """Get all entity names available in cache for a configuration."""
        available = set()
        current_time = time.time()
        for key, metadata in list(self._metadata.items()):
            if metadata.config_name == config_name and (current_time - metadata.timestamp) < self._ttl:
                if key in self._dataframes:
                    available.add(metadata.entity_name)
        return available

    def invalidate(self, config_name: str, entity_name: str | None = None) -> None:
        """Invalidate cache entries for a configuration or specific entity.

        Args:
            config_name: Configuration name
            entity_name: Optional entity name to invalidate specific entity,
                        None to invalidate all entities for config
        """
        keys_to_remove = []
        for key, metadata in list(self._metadata.items()):
            if metadata.config_name == config_name:
                if entity_name is None or metadata.entity_name == entity_name:
                    keys_to_remove.append(key)

        for key in keys_to_remove:
            if key in self._dataframes:
                del self._dataframes[key]
            if key in self._metadata:
                del self._metadata[key]
        logger.debug(f"Invalidated {len(keys_to_remove)} cache entries for {config_name}:{entity_name or 'all'}")


class ShapeShiftConfigCache:
    """Cache for ShapeShiftConfig instances with version tracking."""

    def __init__(self,  config_service: ConfigurationService):
        """Initialize ShapeShiftConfig cache."""
        self.config_service: ConfigurationService = config_service
        self._cache: dict[str, ShapeShiftConfig] = {}
        self._versions: dict[str, int] = {}

    async def get_config(self, config_name: str) -> ShapeShiftConfig:
        """
        Get ShapeShiftConfig with caching and version tracking.

        Uses ApplicationState version tracking to invalidate cache when
        configuration is edited.

        Args:
            config_name: Configuration name

        Returns:
            ShapeShiftConfig instance
        """
        # Get current version from ApplicationState
        try:
            current_version: int = get_app_state().get_version(config_name)
            cached_version: int = self._versions.get(config_name, -1)

            # Check if cached version is still valid
            if config_name in self._cache and cached_version == current_version:
                logger.debug(f"ShapeShiftConfig cache hit for '{config_name}' (version {current_version})")
                return self._cache[config_name]

            # Version mismatch or no cache - reload
            logger.debug(f"ShapeShiftConfig cache miss/invalid for '{config_name}' (cached: {cached_version}, current: {current_version})")
            api_config: Configuration | None = get_app_state().get_configuration(config_name)

            if api_config:
                # Convert from active API Configuration
                shapeshift: ShapeShiftConfig = ConfigMapper.to_core(api_config)
                self._cache[config_name] = shapeshift
                self._versions[config_name] = current_version
                logger.debug(f"Loaded ShapeShiftConfig from ApplicationState for '{config_name}'")
                return shapeshift

        except RuntimeError:
            # ApplicationState not initialized
            pass

        # Fallback: Load from disk
        logger.debug(f"Loading ShapeShiftConfig from disk for '{config_name}'")
        api_config = self.config_service.load_configuration(config_name)
        shapeshift: ShapeShiftConfig = ConfigMapper.to_core(api_config)

        # Cache it (version 0 since not in active editing)
        self._cache[config_name] = shapeshift
        self._versions[config_name] = 0

        return shapeshift
