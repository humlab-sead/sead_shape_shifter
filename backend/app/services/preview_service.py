"""Service for previewing entity data with transformations."""

import asyncio
import hashlib
import time
from typing import Any, Dict, List, Optional

import pandas as pd
from loguru import logger

from app.models.preview import ColumnInfo, PreviewResult
from app.services.config_service import ConfigurationService
from src.config_model import TableConfig, TablesConfig
from src.normalizer import ArbodatSurveyNormalizer


class PreviewCache:
    """Simple in-memory cache for preview results with TTL."""

    def __init__(self, ttl_seconds: int = 300):
        """Initialize cache with TTL in seconds (default 5 minutes)."""
        # Cache maps key -> (result, timestamp, config_name, entity_name, limit)
        self._cache: Dict[str, tuple[PreviewResult, float, str, str, int]] = {}
        self._ttl = ttl_seconds

    def _generate_key(self, config_name: str, entity_name: str, limit: int) -> str:
        """Generate cache key from parameters."""
        key_str = f"{config_name}:{entity_name}:{limit}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def get(self, config_name: str, entity_name: str, limit: int) -> Optional[PreviewResult]:
        """Get cached preview result if not expired."""
        key = self._generate_key(config_name, entity_name, limit)
        if key in self._cache:
            result, timestamp, _, _, _ = self._cache[key]
            if time.time() - timestamp < self._ttl:
                logger.debug(f"Cache hit for {entity_name}")
                result.cache_hit = True
                return result
            else:
                # Remove expired entry
                del self._cache[key]
                logger.debug(f"Cache expired for {entity_name}")
        return None

    def set(self, config_name: str, entity_name: str, limit: int, result: PreviewResult) -> None:
        """Cache preview result with current timestamp."""
        key = self._generate_key(config_name, entity_name, limit)
        self._cache[key] = (result, time.time(), config_name, entity_name, limit)
        logger.debug(f"Cached preview for {entity_name}")

    def invalidate(self, config_name: str, entity_name: Optional[str] = None) -> None:
        """Invalidate cache entries for a configuration or specific entity."""
        keys_to_remove = []
        for key, (_, _, cached_config, cached_entity, _) in list(self._cache.items()):
            if cached_config == config_name:
                if entity_name is None or cached_entity == entity_name:
                    keys_to_remove.append(key)

        for key in keys_to_remove:
            del self._cache[key]
        logger.debug(f"Invalidated {len(keys_to_remove)} cache entries for {config_name}:{entity_name or 'all'}")


class PreviewService:
    """Service for previewing entity data."""

    def __init__(self, config_service: ConfigurationService):
        """Initialize preview service."""
        self.config_service = config_service
        self.cache = PreviewCache(ttl_seconds=300)  # 5 minute cache

    async def preview_entity(
        self, config_name: str, entity_name: str, limit: int = 50
    ) -> PreviewResult:
        """
        Preview entity data with all transformations applied.

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
        start_time = time.time()

        # Check cache first
        cached = self.cache.get(config_name, entity_name, limit)
        if cached:
            return cached

        # Load configuration
        config_path = self.config_service.get_config_path(config_name)
        config = TablesConfig.from_yaml(str(config_path))

        # Get entity config
        if entity_name not in config.entities:
            raise ValueError(f"Entity '{entity_name}' not found in configuration")

        entity_config = config.entities[entity_name]

        # Preview with transformations
        try:
            result = await self._preview_with_normalizer(
                config, config_name, entity_name, entity_config, limit
            )

            # Calculate execution time
            execution_time_ms = int((time.time() - start_time) * 1000)
            result.execution_time_ms = execution_time_ms

            # Cache result
            self.cache.set(config_name, entity_name, limit, result)

            return result

        except Exception as e:
            logger.error(f"Failed to preview entity {entity_name}: {e}", exc_info=True)
            raise RuntimeError(f"Preview failed: {str(e)}") from e

    async def _preview_with_normalizer(
        self,
        config: TablesConfig,
        config_name: str,
        entity_name: str,
        entity_config: TableConfig,
        limit: int,
    ) -> PreviewResult:
        """Preview entity using the normalizer to apply transformations."""
        # Create normalizer instance
        normalizer = ArbodatSurveyNormalizer(config)

        # Process entity and its dependencies
        try:
            # Run normalization to get the entity data
            await normalizer.normalize()

            # Get the processed data from table_store
            if entity_name not in normalizer.table_store:
                raise RuntimeError(f"Entity '{entity_name}' was not processed")

            df = normalizer.table_store[entity_name]

            # Limit rows
            preview_df = df.head(limit)

            # Get actual row count if available
            estimated_total = len(df) if df is not None else None

            # Determine which transformations were applied
            transformations = []
            if entity_config.filters:
                transformations.append("filter")
            if entity_config.unnest:
                transformations.append("unnest")
            if entity_config.foreign_keys:
                transformations.append("foreign_key_joins")

            # Build column info
            columns = self._build_column_info(preview_df, entity_config)

            # Convert to records for JSON response
            rows = preview_df.to_dict("records")

            # Get dependencies
            dependencies_loaded = []
            if entity_config.source:
                dependencies_loaded.append(entity_config.source)
            if entity_config.depends_on:
                dependencies_loaded.extend(entity_config.depends_on)

            return PreviewResult(
                entity_name=entity_name,
                rows=rows,
                columns=columns,
                total_rows_in_preview=len(rows),
                estimated_total_rows=estimated_total,
                execution_time_ms=0,  # Will be set by caller
                has_dependencies=len(dependencies_loaded) > 0,
                dependencies_loaded=dependencies_loaded,
                transformations_applied=transformations,
                cache_hit=False,
            )

        except Exception as e:
            logger.error(f"Normalizer preview failed for {entity_name}: {e}", exc_info=True)
            raise

    def _build_column_info(self, df: pd.DataFrame, entity_config: TableConfig) -> List[ColumnInfo]:
        """Build column information from DataFrame and entity config."""
        columns = []
        key_columns = set(entity_config.keys or [])
        if entity_config.surrogate_id:
            key_columns.add(entity_config.surrogate_id)

        for col_name in df.columns:
            # Infer data type
            dtype = str(df[col_name].dtype)
            # Map pandas types to more user-friendly names
            if "int" in dtype:
                data_type = "integer"
            elif "float" in dtype:
                data_type = "float"
            elif "bool" in dtype:
                data_type = "boolean"
            elif "datetime" in dtype:
                data_type = "datetime"
            elif "object" in dtype:
                data_type = "string"
            else:
                data_type = dtype

            # Check if column has null values
            nullable = df[col_name].isnull().any()

            columns.append(
                ColumnInfo(
                    name=col_name,
                    data_type=data_type,
                    nullable=nullable,
                    is_key=col_name in key_columns,
                )
            )

        return columns

    async def preview_with_transformations(
        self, config_name: str, entity_name: str, limit: int = 50
    ) -> PreviewResult:
        """
        Preview entity with transformations applied.

        This is an alias for preview_entity for backward compatibility.
        """
        return await self.preview_entity(config_name, entity_name, limit)

    async def get_entity_sample(
        self, config_name: str, entity_name: str, limit: int = 100
    ) -> PreviewResult:
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

    def invalidate_cache(self, config_name: str, entity_name: Optional[str] = None) -> None:
        """
        Invalidate preview cache for a configuration or specific entity.

        Args:
            config_name: Name of the configuration
            entity_name: Optional entity name to invalidate specific entity
        """
        self.cache.invalidate(config_name, entity_name)
        logger.info(f"Invalidated preview cache for {config_name}:{entity_name or 'all'}")
