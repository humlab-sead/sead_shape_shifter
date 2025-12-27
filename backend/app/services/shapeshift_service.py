"""Service for previewing entity data with transformations."""

import hashlib
import time
from dataclasses import dataclass

import pandas as pd
import xxhash
from loguru import logger

from backend.app.core.state_manager import ApplicationState, get_app_state
from backend.app.core.utility import friendly_dtype
from backend.app.mappers.config_mapper import ConfigMapper
from backend.app.models.config import Configuration
from backend.app.models.shapeshift import ColumnInfo, PreviewResult
from backend.app.services.config_service import ConfigurationService
from src.model import ShapeShiftConfig, TableConfig
from src.normalizer import ShapeShifter


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

    def _compute_entity_hash(self, entity_config: TableConfig) -> str:
        """Compute hash of entity configuration.

        Uses xxhash for fast hashing of entity configuration dict.
        This detects changes to entity-specific settings like columns,
        filters, transformations, foreign keys, etc.

        Args:
            entity_config: Entity configuration

        Returns:
            Hexadecimal hash string
        """
        # Serialize entity config to stable string representation
        # Use sorted dict representation for deterministic hashing
        config_str = str(sorted(entity_config.data.items()))
        return xxhash.xxh64(config_str.encode()).hexdigest()

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
            logger.debug(
                f"Cache invalidated for {entity_name} (version mismatch: {metadata.config_version} != {config_version})"
            )
            return None

        # Tier 3: Check entity hash if entity_config provided
        if entity_config is not None:
            current_hash = self._compute_entity_hash(entity_config)
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
        key = self._generate_key(config_name, entity_name)
        self._dataframes[key] = dataframe.copy()  # Store copy to prevent external modifications

        # Compute entity hash if config provided, otherwise use empty hash
        entity_hash = self._compute_entity_hash(entity_config) if entity_config else ""

        self._metadata[key] = CacheMetadata(
            timestamp=time.time(),
            config_name=config_name,
            entity_name=entity_name,
            config_version=config_version,
            entity_hash=entity_hash,
        )
        logger.debug(
            f"Cached DataFrame for {entity_name} (version {config_version}, hash {entity_hash[:8]}, {len(dataframe)} rows)"
        )

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
            logger.debug(
                f"Found {len(cached_deps)} cached dependencies for {entity_config.entity_name}: {list(cached_deps.keys())}"
            )

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

    def __init__(self, config_service: ConfigurationService):
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
            app_state: ApplicationState = get_app_state()
            current_version: int = app_state.get_version(config_name)
            cached_version: int = self._versions.get(config_name, -1)

            # Check if cached version is still valid
            if config_name in self._cache and cached_version == current_version:
                logger.debug(f"ShapeShiftConfig cache hit for '{config_name}' (version {current_version})")
                return self._cache[config_name]

            # Version mismatch or no cache - reload
            logger.debug(f"ShapeShiftConfig cache miss/invalid for '{config_name}' (cached: {cached_version}, current: {current_version})")
            api_config: Configuration | None = app_state.get_configuration(config_name)

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


class ShapeShiftService:
    """Service for previewing entity data with caching."""

    def __init__(self, config_service: ConfigurationService, ttl_seconds: int = 300):
        """Initialize shapeshift/preview service."""
        self.config_service: ConfigurationService = config_service
        self.cache = ShapeShiftCache(ttl_seconds=ttl_seconds)  # 5 minute cache

        # Cache ShapeShiftConfig instances for performance
        self._config_cache = ShapeShiftConfigCache(config_service)

    async def preview_entity(self, config_name: str, entity_name: str, limit: int = 50) -> PreviewResult:
        """
        Preview entity data with all transformations applied.

        Uses cached DataFrames to reuse dependencies and target entity from previous runs.

        Args:
            config_name: Name of the configuration file
            entity_name: Name of the entity to preview
            limit: Maximum number of rows to return (default 50)

        Returns:
            PreviewResult with data and metadata

        Raises:
            ValueError: If configuration or entity not found
            RuntimeError: If preview fails
        """
        start_time: float = time.time()
        cache_hit: bool = False

        # Get ShapeShiftConfig and version (always needed for entity_config)
        shapeshift_config: ShapeShiftConfig = await self._config_cache.get_config(config_name)

        # Get current version from ApplicationState if available
        config_version: int = 0
        try:
            app_state: ApplicationState = get_app_state()
            config_version = app_state.get_version(config_name)
        except RuntimeError:
            pass  # ApplicationState not initialized

        if entity_name not in shapeshift_config.tables:
            raise ValueError(f"Entity '{entity_name}' not found in configuration")

        entity_config: TableConfig = shapeshift_config.tables[entity_name]

        # Check if target entity is cached (with hash validation)
        cached_target: pd.DataFrame | None = self.cache.get_dataframe(
            config_name, entity_name, config_version, entity_config
        )

        if cached_target is not None:
            # Full cache hit - target entity is cached
            logger.debug(f"Building preview from cached DataFrame for {entity_name}")
            cache_hit = True
            table_store: dict[str, pd.DataFrame] = {entity_name: cached_target}

            # Also gather any cached dependencies for dependency tracking (with hash validation)
            cached_deps = self.cache.gather_cached_dependencies(
                config_name, entity_config, config_version, shapeshift_config
            )
            table_store.update(cached_deps)
        else:
            # Cache miss - gather cached dependencies and run ShapeShifter
            initial_table_store: dict[str, pd.DataFrame] = self.cache.gather_cached_dependencies(
                config_name, entity_config, config_version, shapeshift_config
            )

            table_store = await self._shapeshift(
                config=shapeshift_config,
                entity_name=entity_name,
                entity_config=entity_config,
                initial_table_store=initial_table_store,
            )

            # Cache all entities from the result individually (with entity configs for hashing)
            entity_configs = {name: shapeshift_config.get_table(name) for name in table_store.keys()}
            self.cache.set_table_store(config_name, table_store, entity_name, config_version, entity_configs)

        # Build PreviewResult from table_store (apply limit here)
        result: PreviewResult = PreviewResultBuilder().build(
            entity_name=entity_name,
            entity_config=entity_config,
            table_store=table_store,
            limit=limit,
            cache_hit=cache_hit,
        )

        execution_time_ms: int = int((time.time() - start_time) * 1000)
        result.execution_time_ms = execution_time_ms

        return result

    async def _shapeshift(
        self,
        config: ShapeShiftConfig,
        entity_name: str,
        entity_config: TableConfig,
        initial_table_store: dict[str, pd.DataFrame],
    ) -> dict[str, pd.DataFrame]:
        """
        Run ShapeShifter to produce entity data.

        Args:
            config: ShapeShiftConfig instance
            entity_name: Target entity name
            entity_config: Target entity configuration
            initial_table_store: Pre-existing cached entities to reuse

        Returns:
            Complete table_store with target entity and all dependencies
        """
        try:
            # Determine the default source entity from the target entity config
            default_source: str | None = entity_config.source if entity_config.source else None

            normalizer: ShapeShifter = ShapeShifter(
                config=config,
                table_store=initial_table_store,  # Pass cached entities
                default_entity=default_source,
                target_entities={entity_name},
            )

            await normalizer.normalize()

            if entity_name not in normalizer.table_store:
                raise RuntimeError(f"Entity {entity_name} was not produced by normalizer")

            # Return the complete table_store (includes target + all dependencies)
            return normalizer.table_store

        except Exception as e:
            logger.error(f"ShapeShift failed for {entity_name}: {e}", exc_info=True)
            raise RuntimeError(f"ShapeShift failed for {entity_name}: {str(e)}") from e

    async def get_entity_sample(self, config_name: str, entity_name: str, limit: int = 100) -> PreviewResult:
        """
        Get a sample of entity data (larger limit for validation/testing).

        Args:
            config_name: Name of the configuration file
            entity_name: Name of the entity
            limit: Maximum number of rows (default 100, max 1000)

        Returns:
            PreviewResult with sample data
        """
        # Clamp limit to max 1000
        limit = min(limit, 1000)
        return await self.preview_entity(config_name, entity_name, limit)

    def invalidate_cache(self, config_name: str, entity_name: str | None = None) -> None:
        """
        Invalidate preview cache for a configuration or specific entity.

        Args:
            config_name: Name of the configuration
            entity_name: Optional entity name to invalidate specific entity
        """
        self.cache.invalidate(config_name, entity_name)
        logger.info(f"Invalidated preview cache for {config_name}:{entity_name or 'all'}")


class PreviewResultBuilder:

    def build(
        self,
        entity_name: str,
        entity_config: TableConfig,
        table_store: dict[str, pd.DataFrame],
        limit: int,
        cache_hit: bool,
    ) -> PreviewResult:
        """Build PreviewResult from table_store with limit applied."""
        if entity_name not in table_store:
            raise RuntimeError(f"Entity {entity_name} not found in table_store")

        df: pd.DataFrame = table_store[entity_name]
        estimated_total: int = len(df)
        preview_df: pd.DataFrame = df.head(limit)

        key_columns: set[str] = entity_config.get_key_columns()

        columns: list[ColumnInfo] = [
            ColumnInfo(
                name=col_name,
                data_type=friendly_dtype(preview_df[col_name].dtype),
                nullable=bool(preview_df[col_name].isnull().any()),
                is_key=col_name in key_columns,
            )
            for col_name in preview_df.columns
        ]

        rows: list[dict] = preview_df.to_dict("records")

        # Dependencies are other entities in table_store
        dependencies_loaded: list[str] = [name for name in table_store.keys() if name != entity_name]

        return PreviewResult(
            entity_name=entity_name,
            rows=rows,
            columns=columns,
            total_rows_in_preview=len(rows),
            estimated_total_rows=estimated_total,
            execution_time_ms=0,  # Will be set by caller
            has_dependencies=len(dependencies_loaded) > 0,
            dependencies_loaded=dependencies_loaded,
            cache_hit=cache_hit,
        )
