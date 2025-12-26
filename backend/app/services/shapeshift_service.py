"""Service for previewing entity data with transformations."""

import hashlib
import time

import pandas as pd
from loguru import logger

from backend.app.core.state_manager import ApplicationState, get_app_state
from backend.app.core.utility import friendly_dtype
from backend.app.mappers.config_mapper import ConfigMapper
from backend.app.models.config import Configuration
from backend.app.models.shapeshift import ColumnInfo, PreviewResult
from backend.app.services.config_service import ConfigurationService
from src.model import ShapeShiftConfig, TableConfig
from src.normalizer import ShapeShifter


class ShapeShiftCache:
    """Cache for ShapeShifter table_store results with TTL.

    Caches complete DataFrames produced by ShapeShifter, including all dependencies.
    This allows reusing dependency results in subsequent ShapeShifter calls.
    """

    def __init__(self, ttl_seconds: int = 300):
        """Initialize cache with TTL in seconds (default 5 minutes)."""
        # Store complete table_stores: key -> dict[entity_name, DataFrame]
        self._table_stores: dict[str, dict[str, pd.DataFrame]] = {}
        # Store metadata separately: key -> (timestamp, config_name, entity_name)
        self._metadata: dict[str, tuple[float, str, str]] = {}
        self._ttl: int = ttl_seconds

    def _generate_key(self, config_name: str, entity_name: str) -> str:
        """Generate cache key from config and entity name (no limit - we cache full DataFrames)."""
        key_str = f"{config_name}:{entity_name}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def get_table_store(self, config_name: str, entity_name: str) -> dict[str, pd.DataFrame] | None:
        """Get cached table_store if not expired."""
        key = self._generate_key(config_name, entity_name)
        if key in self._table_stores and key in self._metadata:
            timestamp, _, _ = self._metadata[key]
            if time.time() - timestamp < self._ttl:
                logger.debug(f"Cache hit for {entity_name} ({len(self._table_stores[key])} entities)")
                return self._table_stores[key].copy()  # Return copy to prevent modifications
            # Remove expired entry
            del self._table_stores[key]
            del self._metadata[key]
            logger.debug(f"Cache expired for {entity_name}")
        return None

    def set_table_store(self, config_name: str, entity_name: str, table_store: dict[str, pd.DataFrame]) -> None:
        """Cache table_store with current timestamp."""
        key = self._generate_key(config_name, entity_name)
        self._table_stores[key] = table_store.copy()  # Store copy to prevent external modifications
        self._metadata[key] = (time.time(), config_name, entity_name)
        logger.debug(f"Cached table_store for {entity_name} ({len(table_store)} entities)")

    def get_available_entities(self, config_name: str) -> set[str]:
        """Get all entity names available in cache for a configuration."""
        available = set()
        current_time = time.time()
        for key, (timestamp, cached_config, _) in list(self._metadata.items()):
            if cached_config == config_name and (current_time - timestamp) < self._ttl:
                if key in self._table_stores:
                    available.update(self._table_stores[key].keys())
        return available

    def invalidate(self, config_name: str, entity_name: str | None = None) -> None:
        """Invalidate cache entries for a configuration or specific entity."""
        keys_to_remove = []
        for key, (_, cached_config, cached_entity) in list(self._metadata.items()):
            if cached_config == config_name:
                if entity_name is None or cached_entity == entity_name:
                    keys_to_remove.append(key)

        for key in keys_to_remove:
            if key in self._table_stores:
                del self._table_stores[key]
            if key in self._metadata:
                del self._metadata[key]
        logger.debug(f"Invalidated {len(keys_to_remove)} cache entries for {config_name}:{entity_name or 'all'}")


class ShapeShiftService:
    """Service for previewing entity data with caching."""

    def __init__(self, config_service: ConfigurationService, ttl_seconds: int = 300):
        """Initialize shapeshift/preview service."""
        self.config_service: ConfigurationService = config_service
        self.cache = ShapeShiftCache(ttl_seconds=ttl_seconds)  # 5 minute cache

        # Cache ShapeShiftConfig instances for performazznce
        self._shapeshift_cache: dict[str, ShapeShiftConfig] = {}
        self._shapeshift_versions: dict[str, int] = {}

    async def preview_entity(self, config_name: str, entity_name: str, limit: int = 50) -> PreviewResult:
        """
        Preview entity data with all transformations applied.

        Uses cached table_store to reuse dependencies from previous runs.

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

        # Get ShapeShiftConfig (always needed for entity_config)
        shapeshift_config: ShapeShiftConfig = await self._get_shapeshift_config(config_name)

        if entity_name not in shapeshift_config.tables:
            raise ValueError(f"Entity '{entity_name}' not found in configuration")

        entity_config: TableConfig = shapeshift_config.tables[entity_name]

        # Check cache for existing table_store
        cached_table_store: dict[str, pd.DataFrame] | None = self.cache.get_table_store(config_name, entity_name)

        # If cache hit and target entity exists, use cached data
        if cached_table_store and entity_name in cached_table_store:
            logger.debug(f"Building preview from cached table_store for {entity_name}")
            cache_hit = True
            table_store = cached_table_store
        else:
            # Cache miss or incomplete - run ShapeShifter
            try:
                # Pass cached entities as initial table_store to reuse dependencies
                initial_table_store: dict[str, pd.DataFrame] = cached_table_store or {}

                table_store = await self._shapeshift(
                    config=shapeshift_config,
                    entity_name=entity_name,
                    entity_config=entity_config,
                    initial_table_store=initial_table_store,
                )

                # Cache the resulting table_store
                self.cache.set_table_store(config_name, entity_name, table_store)

            except Exception as e:
                logger.error(f"Failed to preview entity {entity_name}: {e}", exc_info=True)
                raise RuntimeError(f"Preview failed: {str(e)}") from e

        # Build PreviewResult from table_store (apply limit here)
        result = PreviewResultBuilder().build(
            entity_name=entity_name,
            entity_config=entity_config,
            table_store=table_store,
            limit=limit,
            cache_hit=cache_hit,
        )

        execution_time_ms: int = int((time.time() - start_time) * 1000)
        result.execution_time_ms = execution_time_ms

        return result

    async def _get_shapeshift_config(self, config_name: str) -> ShapeShiftConfig:
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
            cached_version: int = self._shapeshift_versions.get(config_name, -1)

            # Check if cached version is still valid
            if config_name in self._shapeshift_cache and cached_version == current_version:
                logger.debug(f"ShapeShiftConfig cache hit for '{config_name}' (version {current_version})")
                return self._shapeshift_cache[config_name]

            # Version mismatch or no cache - reload
            logger.debug(f"ShapeShiftConfig cache miss/invalid for '{config_name}' (cached: {cached_version}, current: {current_version})")
            api_config: Configuration | None = app_state.get_configuration(config_name)

            if api_config:
                # Convert from active API Configuration
                shapeshift: ShapeShiftConfig = ConfigMapper.to_core(api_config)
                self._shapeshift_cache[config_name] = shapeshift
                self._shapeshift_versions[config_name] = current_version
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
        self._shapeshift_cache[config_name] = shapeshift
        self._shapeshift_versions[config_name] = 0

        return shapeshift

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
            raise

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
