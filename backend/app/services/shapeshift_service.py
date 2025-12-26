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
    """Simple in-memory cache for shapeshift/preview results with TTL."""

    def __init__(self, ttl_seconds: int = 300):
        """Initialize cache with TTL in seconds (default 5 minutes)."""
        # Cache maps key -> (result, timestamp, config_name, entity_name, limit)
        self._cache: dict[str, tuple[PreviewResult, float, str, str, int]] = {}
        self._ttl: int = ttl_seconds

    def _generate_key(self, config_name: str, entity_name: str, limit: int) -> str:
        """Generate cache key from parameters."""
        key_str = f"{config_name}:{entity_name}:{limit}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def get(self, config_name: str, entity_name: str, limit: int) -> PreviewResult | None:
        """Get cached shapeshift/preview result if not expired."""
        key = self._generate_key(config_name, entity_name, limit)
        if key in self._cache:
            result, timestamp, _, _, _ = self._cache[key]
            if time.time() - timestamp < self._ttl:
                logger.debug(f"Cache hit for {entity_name}")
                result.cache_hit = True
                return result
            # Remove expired entry
            del self._cache[key]
            logger.debug(f"Cache expired for {entity_name}")
        return None

    def set(self, config_name: str, entity_name: str, limit: int, result: PreviewResult) -> None:
        """Cache shapeshift/preview result with current timestamp."""
        key = self._generate_key(config_name, entity_name, limit)
        self._cache[key] = (result, time.time(), config_name, entity_name, limit)
        logger.debug(f"Cached shapeshift/preview for {entity_name}")

    def invalidate(self, config_name: str, entity_name: str | None = None) -> None:
        """Invalidate cache entries for a configuration or specific entity."""
        keys_to_remove = []
        for key, (_, _, cached_config, cached_entity, _) in list(self._cache.items()):
            if cached_config == config_name:
                if entity_name is None or cached_entity == entity_name:
                    keys_to_remove.append(key)

        for key in keys_to_remove:
            del self._cache[key]
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

        Uses cached ShapeShiftConfig with version tracking for optimal performance.

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

        # Check cache first
        cached: PreviewResult | None = self.cache.get(config_name, entity_name, limit)
        if cached:
            return cached

        # Get ShapeShiftConfig (cached with version tracking)
        shapeshift_config: ShapeShiftConfig = await self._get_shapeshift_config(config_name)

        if entity_name not in shapeshift_config.tables:
            raise ValueError(f"Entity '{entity_name}' not found in configuration")

        entity_config: TableConfig = shapeshift_config.tables[entity_name]

        try:
            result: PreviewResult = await self._preview_with_normalizer(
                config=shapeshift_config, entity_name=entity_name, entity_config=entity_config, limit=limit
            )

            execution_time_ms: int = int((time.time() - start_time) * 1000)
            result.execution_time_ms = execution_time_ms

            self.cache.set(config_name=config_name, entity_name=entity_name, limit=limit, result=result)

            return result

        except Exception as e:
            logger.error(f"Failed to preview entity {entity_name}: {e}", exc_info=True)
            raise RuntimeError(f"Preview failed: {str(e)}") from e

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
                cfg_dict = ConfigMapper.to_core_dict(api_config)
                shapeshift = ShapeShiftConfig(cfg=cfg_dict)
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
        cfg_dict = ConfigMapper.to_core_dict(api_config)
        shapeshift = ShapeShiftConfig(cfg=cfg_dict)

        # Cache it (version 0 since not in active editing)
        self._shapeshift_cache[config_name] = shapeshift
        self._shapeshift_versions[config_name] = 0

        return shapeshift

    async def _preview_with_normalizer(
        self,
        config: ShapeShiftConfig | str,
        entity_name: str,
        entity_config: TableConfig,
        limit: int,
    ) -> PreviewResult:
        """Preview entity data using the normalizer to shape shifting."""
        try:

            if isinstance(config, str):
                raise ValueError("Config must be ShapeShiftConfig instance, not str")

            # Determine the default source entity from the target entity config
            default_source: str | None = entity_config.source if entity_config.source else None

            normalizer: ShapeShifter = ShapeShifter(
                config=config,
                table_store={},
                default_entity=default_source,
                target_entities={entity_name},
            )

            await normalizer.normalize()

            if entity_name not in normalizer.table_store:
                raise RuntimeError(f"Entity {entity_name} was not produced by normalizer")

            df: pd.DataFrame = normalizer.table_store[entity_name]

            estimated_total: int = len(df)

            preview_df: pd.DataFrame = df.head(limit)

            columns: list[ColumnInfo] = self._build_column_info(preview_df, entity_config)

            rows: list[dict] = preview_df.to_dict("records")

            dependencies_loaded: list[str] = list(entity_config.depends_on)

            return PreviewResult(
                entity_name=entity_name,
                rows=rows,
                columns=columns,
                total_rows_in_preview=len(rows),
                estimated_total_rows=estimated_total,
                execution_time_ms=0,  # Will be set by caller
                has_dependencies=len(dependencies_loaded) > 0,
                dependencies_loaded=dependencies_loaded,
                cache_hit=False,
            )

        except Exception as e:
            logger.error(f"Preview failed for {entity_name}: {e}", exc_info=True)
            raise

    def _build_column_info(self, df: pd.DataFrame, entity_config: TableConfig) -> list[ColumnInfo]:
        """Build column information from DataFrame and entity config."""
        key_columns: set[str] = entity_config.get_key_columns()
        columns: list[ColumnInfo] = [
            ColumnInfo(
                name=col_name,
                data_type=friendly_dtype(df[col_name].dtype),
                nullable=bool(df[col_name].isnull().any()),
                is_key=col_name in key_columns,
            )
            for col_name in df.columns
        ]
        return columns

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
