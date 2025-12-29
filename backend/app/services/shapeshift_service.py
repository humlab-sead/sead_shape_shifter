"""Service for previewing entity data with transformations."""

import contextlib
import time

import pandas as pd
from loguru import logger
from numpy import add

from backend.app.core.config import Settings, settings
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
        self.config_service: ConfigurationService = config_service
        self.cache: ShapeShiftCache = ShapeShiftCache(ttl_seconds=ttl_seconds)  # 5 minute cache
        self.config_cache = ShapeShiftConfigCache(config_service)
        self.settings: Settings = settings

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

        shapeshift_cfg: ShapeShiftConfig = await self.config_cache.get_config(config_name)
        config_version: int = self.get_config_version(config_name)

        if entity_name not in shapeshift_cfg.tables:
            raise ValueError(f"Entity '{entity_name}' not found in configuration")

        entity_cfg: TableConfig = shapeshift_cfg.tables[entity_name]

        cached_data: ShapeShiftCache.CacheCheckResult = self.cache.fetch_cached_entity_data(
            config_name, entity_name, config_version, entity_cfg, shapeshift_cfg
        )

        table_store: dict[str, pd.DataFrame]
        if cached_data.data is not None:
            table_store = {entity_name: cached_data.data} | cached_data.dependencies
        else:
            resolved_cfg: ShapeShiftConfig = shapeshift_cfg.clone().resolve(filename=shapeshift_cfg.filename, **self.settings.env_opts)
            table_store = await self.shapeshift(
                config=resolved_cfg,
                entity_name=entity_name,
                initial_table_store=cached_data.dependencies,
            )

            entity_configs: dict[str, TableConfig] = {name: shapeshift_cfg.get_table(name) for name in table_store.keys()}
            self.cache.set_table_store(config_name, table_store, entity_name, config_version, entity_configs)

        result: PreviewResult = PreviewResultBuilder().build(
            entity_name=entity_name,
            entity_cfg=entity_cfg,
            table_store=table_store,
            limit=limit,
            cache_hit=cached_data.found,
        )

        execution_time_ms: int = int((time.time() - start_time) * 1000)
        result.execution_time_ms = execution_time_ms

        return result

    async def shapeshift(
        self,
        config: ShapeShiftConfig,
        entity_name: str,
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
            shapeshifter: ShapeShifter = ShapeShifter(
                config=config,
                table_store=initial_table_store,
                default_entity=config.metadata.default_entity,
                target_entities={entity_name},
            )

            (await shapeshifter.normalize())
            shapeshifter.add_system_id_columns()
            shapeshifter.move_keys_to_front()

            if entity_name not in shapeshifter.table_store:
                raise RuntimeError(f"Entity {entity_name} was not produced by normalizer")

            return shapeshifter.table_store

        except Exception as e:
            logger.exception(f"ShapeShift failed for {entity_name}: {e}", exc_info=True)
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
        return await self.preview_entity(config_name, entity_name, limit)

    def invalidate_cache(self, config_name: str, entity_name: str | None = None) -> None:
        """Invalidate preview cache for a configuration or specific entity."""
        self.cache.invalidate(config_name, entity_name)
        logger.info(f"Invalidated preview cache for {config_name}:{entity_name or 'all'}")

    def get_config_version(self, config_name: str) -> int:
        """Get the current version of a configuration from ApplicationState."""
        with contextlib.suppress(RuntimeError):
            app_state: ApplicationState = get_app_state()
            return app_state.get_version(config_name)
        return 0  # ApplicationState not initialized


class PreviewResultBuilder:

    def build(
        self,
        entity_name: str,
        entity_cfg: TableConfig,
        table_store: dict[str, pd.DataFrame],
        limit: int,
        cache_hit: bool,
    ) -> PreviewResult:
        """Build PreviewResult from table_store with limit applied."""
        if entity_name not in table_store:
            raise RuntimeError(f"Entity {entity_name} not found in table_store")

        preview_df: pd.DataFrame = table_store[entity_name].head(limit)

        key_columns: set[str] = entity_cfg.get_key_columns()

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
            estimated_total_rows=len(table_store[entity_name]),
            execution_time_ms=0,
            has_dependencies=len(dependencies_loaded) > 0,
            dependencies_loaded=dependencies_loaded,
            cache_hit=cache_hit,
        )
