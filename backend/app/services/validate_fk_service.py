"""Service for previewing entity data with transformations."""

import time

import pandas as pd

from backend.app.core.state_manager import ApplicationState, get_app_state
from backend.app.mappers.config_mapper import ConfigMapper
from backend.app.models import Configuration
from backend.app.models import CardinalityInfo, JoinStatistics, JoinTestResult, UnmatchedRow
from backend.app.models import PreviewResult
from backend.app.services.preview_service import PreviewService
from src.model import ForeignKeyConfig, ShapeShiftConfig, TableConfig

class ValidateForeignKeyService:
    """Service for previewing entity data with ShapeShiftConfig caching."""

    def __init__(self, preview_service: PreviewService):
        """Initialize preview service."""
        self.preview_service: PreviewService = preview_service

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
            app_state: ApplicationState = get_app_state()
            api_cfg: Configuration | None = app_state.get_configuration(config_name)
            assert api_cfg is not None
            core_cfg_dict: dict = ConfigMapper.to_core_dict(api_cfg)
            config: ShapeShiftConfig = ShapeShiftConfig(cfg=core_cfg_dict)
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
        local_preview: PreviewResult = await self.preview_service.preview_entity(config_name, entity_name, limit=sample_size)
        remote_preview: PreviewResult = await self.preview_service.preview_entity(config_name, remote_entity_name, limit=1000)

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

