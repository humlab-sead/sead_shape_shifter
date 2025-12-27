"""Service for previewing entity data with transformations."""

import time

import pandas as pd
from loguru import logger

from backend.app.core.state_manager import ApplicationState, get_app_state
from backend.app.core.utility import friendly_dtype
from backend.app.models.shapeshift import ColumnInfo, PreviewResult
from backend.app.services.config_service import ConfigurationService
from backend.app.utils.caches import ShapeShiftCache, ShapeShiftConfigCache
from src.model import ShapeShiftConfig, TableConfig
from src.normalizer import ShapeShifter


class ShapeShiftService:
    """Service for previewing entity data with caching."""

    def __init__(self, config_service: ConfigurationService, ttl_seconds: int = 300):
        """Initialize shapeshift/preview service."""
        self.config_service: ConfigurationService = config_service
        self.cache: ShapeShiftCache = ShapeShiftCache(ttl_seconds=ttl_seconds)  # 5 minute cache
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
        cached_target: pd.DataFrame | None = self.cache.get_dataframe(config_name, entity_name, config_version, entity_config)

        if cached_target is not None:
            # Full cache hit - target entity is cached
            logger.debug(f"Building preview from cached DataFrame for {entity_name}")
            cache_hit = True
            table_store: dict[str, pd.DataFrame] = {entity_name: cached_target}

            # Also gather any cached dependencies for dependency tracking (with hash validation)
            cached_deps = self.cache.gather_cached_dependencies(config_name, entity_config, config_version, shapeshift_config)
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
        self, entity_name: str, entity_config: TableConfig, table_store: dict[str, pd.DataFrame], limit: int, cache_hit: bool
    ) -> PreviewResult:
        """Build PreviewResult from table_store with limit applied."""
        if entity_name not in table_store:
            raise RuntimeError(f"Entity {entity_name} not found in table_store")

        estimated_total: int = len(table_store[entity_name])
        preview_df: pd.DataFrame = table_store[entity_name].head(limit)

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
