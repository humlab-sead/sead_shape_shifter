"""Service for previewing entity data with transformations."""

import hashlib
import time

import pandas as pd
from loguru import logger
from pandas.api.types import (
    CategoricalDtype,
    is_bool_dtype,
    is_datetime64_any_dtype,
    is_float_dtype,
    is_integer_dtype,
    is_string_dtype,
    is_timedelta64_dtype,
)

from backend.app.core.state_manager import get_app_state
from backend.app.models.join_test import CardinalityInfo, JoinStatistics, JoinTestResult, UnmatchedRow
from backend.app.models.preview import ColumnInfo, PreviewResult
from backend.app.services.config_service import ConfigurationService
from src.model import ForeignKeyConfig, ShapeShiftConfig, TableConfig
from src.normalizer import ShapeShifter


class PreviewCache:
    """Simple in-memory cache for preview results with TTL."""

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
        """Get cached preview result if not expired."""
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
        """Cache preview result with current timestamp."""
        key = self._generate_key(config_name, entity_name, limit)
        self._cache[key] = (result, time.time(), config_name, entity_name, limit)
        logger.debug(f"Cached preview for {entity_name}")

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


class PreviewService:
    """Service for previewing entity data."""

    def __init__(self, config_service: ConfigurationService):
        """Initialize preview service."""
        self.config_service: ConfigurationService = config_service
        self.cache = PreviewCache(ttl_seconds=300)  # 5 minute cache

    async def preview_entity(self, config_name: str, entity_name: str, limit: int = 50) -> PreviewResult:
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
        start_time: float = time.time()

        # Check cache first
        cached = self.cache.get(config_name, entity_name, limit)
        if cached:
            return cached

        # Load config - try ApplicationState first (production), fall back to ShapeShiftConfig.resolve (tests)
        try:
            app_state = get_app_state()
            config_store = app_state.config_store
            
            # Ensure config is loaded
            if not config_store.is_loaded(config_name):
                config_store.load_config(config_name)
            
            config_like = config_store.get_config(config_name)
            config: ShapeShiftConfig = ShapeShiftConfig(cfg=config_like.data)
        except RuntimeError:
            # Fallback for tests - use ShapeShiftConfig.resolve which uses the mocked provider
            config = ShapeShiftConfig.resolve(cfg=config_name)

        if entity_name not in config.tables:
            raise ValueError(f"Entity '{entity_name}' not found in configuration")

        entity_config: TableConfig = config.tables[entity_name]

        try:
            result: PreviewResult = await self._preview_with_normalizer(
                config=config, entity_name=entity_name, entity_config=entity_config, limit=limit
            )

            execution_time_ms: int = int((time.time() - start_time) * 1000)
            result.execution_time_ms = execution_time_ms

            self.cache.set(config_name=config_name, entity_name=entity_name, limit=limit, result=result)

            return result

        except Exception as e:
            logger.error(f"Failed to preview entity {entity_name}: {e}", exc_info=True)
            raise RuntimeError(f"Preview failed: {str(e)}") from e

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

            # Determine which transformations were applied
            transformations = []
            if entity_config.filters:
                transformations.append("filter")
            if entity_config.unnest:
                transformations.append("unnest")
            if entity_config.foreign_keys:
                transformations.append("foreign_key_joins")
            # if entity_config.translate:
            #     transformations.append("column_mapping")
            if not transformations:
                transformations = ["raw_data"]

            # Build column info
            columns: list[ColumnInfo] = self._build_column_info(preview_df, entity_config)

            # Convert to records for JSON response
            rows: list[dict] = preview_df.to_dict("records")

            # Get dependencies
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
                transformations_applied=transformations,
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

    async def preview_with_transformations(self, config_name: str, entity_name: str, limit: int = 50) -> PreviewResult:
        """
        Preview entity with transformations applied.

        This is an alias for preview_entity for backward compatibility.
        """
        return await self.preview_entity(config_name, entity_name, limit)

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

    async def test_foreign_key(
        self, config_name: str, entity_name: str, foreign_key_index: int, sample_size: int = 100
    ) -> "JoinTestResult":
        """
        Test a foreign key join to validate the relationship.

        Args:
            config_name: Name of the configuration
            entity_name: Name of the entity with the foreign key
            foreign_key_index: Index of the foreign key in the entity's foreign_keys list
            sample_size: Number of rows to test (default 100)

        Returns:
            JoinTestResult with statistics and unmatched rows
        """

        start_time: float = time.time()

        # Load config - try ApplicationState first (production), fall back to ShapeShiftConfig.resolve (tests)
        try:
            app_state = get_app_state()
            config_store = app_state.config_store
            
            # Ensure config is loaded
            if not config_store.is_loaded(config_name):
                config_store.load_config(config_name)
            
            config_like = config_store.get_config(config_name)
            config: ShapeShiftConfig = ShapeShiftConfig(cfg=config_like.data)
        except RuntimeError:
            # Fallback for tests - use ShapeShiftConfig.resolve which uses the mocked provider
            config = ShapeShiftConfig.resolve(cfg=config_name)

        # Get entity and foreign key config
        if entity_name not in config.tables:
            raise ValueError(f"Entity '{entity_name}' not found")

        entity_config: TableConfig = config.tables[entity_name]

        if not entity_config.foreign_keys or foreign_key_index >= len(entity_config.foreign_keys):
            raise ValueError(f"Foreign key index {foreign_key_index} out of range")

        fk_config: ForeignKeyConfig = entity_config.foreign_keys[foreign_key_index]
        remote_entity_name: str = fk_config.remote_entity

        if remote_entity_name not in config.tables:
            raise ValueError(f"Remote entity '{remote_entity_name}' not found")

        # remote_entity_config = config.tables[remote_entity_name]

        # Load sample data for both entities
        local_preview: PreviewResult = await self.preview_entity(config_name, entity_name, limit=sample_size)
        remote_preview: PreviewResult = await self.preview_entity(config_name, remote_entity_name, limit=1000)

        local_df = pd.DataFrame(local_preview.rows)
        remote_df = pd.DataFrame(remote_preview.rows)

        # Perform join analysis
        local_keys: list[str] = fk_config.local_keys
        remote_keys: list[str] = fk_config.remote_keys
        join_type = fk_config.how or "left"

        # Check if keys exist in dataframes
        missing_local: list[str] = [k for k in local_keys if k not in local_df.columns]
        missing_remote: list[str] = [k for k in remote_keys if k not in remote_df.columns]

        if missing_local or missing_remote:
            error_parts = []
            if missing_local:
                error_parts.append(f"Local keys not found: {missing_local} (available: {list(local_df.columns)})")
            if missing_remote:
                error_parts.append(f"Remote keys not found: {missing_remote} (available: {list(remote_df.columns)})")
            raise ValueError(". ".join(error_parts))

        # Count nulls in local keys
        null_key_rows: int = local_df[local_keys].isnull().any(axis=1).sum()

        # Perform the join
        merged: pd.DataFrame = local_df.merge(
            remote_df, left_on=local_keys, right_on=remote_keys, how="left", indicator=True, suffixes=("", "_remote")
        )

        # Calculate statistics
        total_rows: int = len(local_df)
        matched_rows: int = (merged["_merge"] == "both").sum()
        unmatched_rows: int = total_rows - matched_rows
        match_percentage: float = (matched_rows / total_rows * 100) if total_rows > 0 else 0.0

        # Check for duplicate matches
        duplicate_matches: int = len(merged) - total_rows

        # Get unmatched samples
        unmatched_df: pd.DataFrame = merged[merged["_merge"] == "left_only"].head(10)
        unmatched_sample: list[UnmatchedRow] = [
            UnmatchedRow(
                row_data={str(k): v for k, v in row.items() if k != "_merge" and not str(k).endswith("_remote")},
                local_key_values=[row[k] for k in local_keys],
                reason="No matching row in remote entity",
            )
            for _, row in unmatched_df.iterrows()
        ]

        # Determine actual cardinality
        if duplicate_matches > 0:
            actual_cardinality = "one_to_many"
        elif matched_rows == total_rows and len(merged) == total_rows:
            actual_cardinality = "one_to_one"
        else:
            actual_cardinality = "many_to_one"

        # Get expected cardinality from constraints
        expected_cardinality: str = "many_to_one"  # default
        if fk_config.constraints:
            if hasattr(fk_config.constraints, "cardinality"):
                expected_cardinality = fk_config.constraints.cardinality or "many_to_one"

        cardinality_matches = expected_cardinality == actual_cardinality

        # Generate recommendations
        recommendations = []
        warnings = []

        if match_percentage < 100:
            warnings.append(f"{unmatched_rows} rows ({100-match_percentage:.1f}%) failed to match")
            recommendations.append("Review the unmatched rows to identify data quality issues")

        if null_key_rows > 0:
            warnings.append(f"{null_key_rows} rows have null values in join keys")
            recommendations.append("Consider whether null keys should be allowed")

        if duplicate_matches > 0:
            warnings.append(f"Join created {duplicate_matches} duplicate rows (one-to-many relationship)")
            if expected_cardinality != "one_to_many":
                recommendations.append("Update cardinality constraint to 'one_to_many' or fix data")

        if not cardinality_matches:
            recommendations.append(f"Update cardinality from '{expected_cardinality}' to '{actual_cardinality}'")

        execution_time_ms = int((time.time() - start_time) * 1000)

        return JoinTestResult(
            entity_name=entity_name,
            remote_entity=remote_entity_name,
            local_keys=local_keys,
            remote_keys=remote_keys,
            join_type=join_type,
            statistics=JoinStatistics(
                total_rows=total_rows,
                matched_rows=matched_rows,
                unmatched_rows=unmatched_rows,
                match_percentage=match_percentage,
                null_key_rows=null_key_rows,
                duplicate_matches=duplicate_matches,
            ),
            cardinality=CardinalityInfo(
                expected=expected_cardinality,
                actual=actual_cardinality,
                matches=cardinality_matches,
                explanation=f"Join produced {len(merged)} rows from {total_rows} input rows",
            ),
            unmatched_sample=unmatched_sample,
            execution_time_ms=execution_time_ms,
            success=match_percentage >= 95 and cardinality_matches,
            warnings=warnings,
            recommendations=recommendations,
        )


def friendly_dtype(dtype):

    if is_integer_dtype(dtype):
        return "integer"
    if is_float_dtype(dtype):
        return "decimal number"
    if is_bool_dtype(dtype):
        return "boolean"
    if is_datetime64_any_dtype(dtype):
        return "date/time"
    if is_timedelta64_dtype(dtype):
        return "duration"
    if isinstance(dtype, CategoricalDtype):
        return "category"
    if is_string_dtype(dtype):
        return "text"
    return "other"
