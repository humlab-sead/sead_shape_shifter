"""Service for entity materialization operations."""

from datetime import datetime
from typing import Any, Literal

import pandas as pd
from loguru import logger
from pandas.api.types import is_bool_dtype, is_datetime64_any_dtype, is_float_dtype, is_integer_dtype

from backend.app.core.config import Settings
from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.models.materialization import (
    MaterializationResult,
    UnmaterializationResult,
)
from backend.app.models.project import Project
from backend.app.services.entity_values_service import EntityValuesService
from backend.app.services.project.entity_persistence_strategies import EntityPersistenceStrategyRegistry
from backend.app.services.project_service import ProjectService
from src.model import ShapeShiftProject, TableConfig
from src.normalizer import ShapeShifter
from src.specifications.materialize import CanMaterializeSpecification
from src.types.fixed_entity_types import (
    FixedEntityTypeCoercer,
    FixedEntityTypeConvention,
    is_missing_fixed_entity_value,
    resolve_fixed_entity_column_type,
)

# pylint: disable=redefined-builtin


class MaterializationError(Exception):
    """Custom exception for materialization errors."""


class MaterializationService:
    """Service for materializing and unmaterializing entities."""

    def __init__(
        self,
        project_service: ProjectService,
        persistence_strategy_registry: EntityPersistenceStrategyRegistry | None = None,
    ):
        """Initialize service with project service dependency."""
        self.project_service: ProjectService = project_service
        self.entity_values_service: EntityValuesService = EntityValuesService(project_service)
        self._persistence_strategy_registry = persistence_strategy_registry or EntityPersistenceStrategyRegistry()

    def _get_materialized_file_path(self, project_name: str, entity_name: str, format: str) -> str:  # pylint: disable=unused-argument
        """Get relative path for materialized file (relative to project folder)."""
        extension = "parquet" if format == "parquet" else "csv"
        return f"materialized/{entity_name}.{extension}"

    @staticmethod
    def _sanitize_materialized_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """Drop temporary helper columns and duplicate labels before freezing entity data."""
        sanitized_df = df.copy()

        helper_columns: list[str] = [
            column for column in sanitized_df.columns if isinstance(column, str) and column.startswith("_merge_indicator_")
        ]
        if helper_columns:
            sanitized_df = sanitized_df.drop(columns=helper_columns, errors="ignore")

        if sanitized_df.columns.has_duplicates:
            sanitized_df = sanitized_df.loc[:, ~sanitized_df.columns.duplicated()].copy()

        return sanitized_df

    def _normalize_materialized_dataframe(self, table: TableConfig, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize materialized data to canonical fixed-entity columns."""
        strategy = self._persistence_strategy_registry.get_strategy_for_type("fixed")
        return strategy.normalize_materialized_dataframe(table.entity_name, df, table.public_id, list(table.keys))

    @staticmethod
    def _infer_materialized_column_type(
        column_name: str,
        series: pd.Series,
        conventions: list[FixedEntityTypeConvention] | None = None,
    ) -> str:
        """Infer the fixed-entity column type needed to preserve a materialized series."""
        default_type = resolve_fixed_entity_column_type(column_name, conventions=conventions)
        non_missing = [value for value in series.tolist() if not is_missing_fixed_entity_value(value)]

        if not non_missing:
            return default_type

        if is_bool_dtype(series.dtype) or all(type(value) is bool for value in non_missing):  # pylint: disable=unidiomatic-typecheck
            return "bool"

        if column_name.endswith("_id"):
            return "int"

        if is_datetime64_any_dtype(series.dtype):
            return "date"

        if is_integer_dtype(series.dtype) or all(type(value) is int for value in non_missing):  # pylint: disable=unidiomatic-typecheck
            return "int"

        if is_float_dtype(series.dtype):
            if all(float(value).is_integer() for value in non_missing):
                return "int"
            return "float"

        if all(isinstance(value, (datetime, pd.Timestamp)) for value in non_missing):
            return "date"

        if all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in non_missing):
            if all(float(value).is_integer() for value in non_missing):
                return "int"
            return "float"

        return "string"

    def _infer_materialized_column_types(
        self,
        df: pd.DataFrame,
        conventions: list[FixedEntityTypeConvention] | None = None,
    ) -> dict[str, str]:
        """Infer explicit fixed column types needed to preserve materialized values."""
        inferred_types: dict[str, str] = {}

        for column in df.columns:
            inferred_type = self._infer_materialized_column_type(str(column), df[column], conventions)
            if inferred_type != resolve_fixed_entity_column_type(str(column), conventions=conventions):
                inferred_types[str(column)] = inferred_type

        return inferred_types

    @staticmethod
    def _serialize_materialized_values(
        entity_name: str,
        df: pd.DataFrame,
        column_types: dict[str, str],
        conventions: list[FixedEntityTypeConvention] | None = None,
    ) -> list[list[Any]]:
        """Convert a materialized dataframe to fixed-safe Python row values."""
        columns = [str(column) for column in df.columns.tolist()]
        records = df.to_dict(orient="records")
        values = [[record.get(column) for column in columns] for record in records]

        return FixedEntityTypeCoercer.coerce_fixed_entity_values(
            {
                "values": values,
                "column_types": column_types,
            },
            columns,
            entity_name,
            conventions,
        )

    @staticmethod
    def _build_materialized_storage_column_types(
        columns: list[str],
        explicit_column_types: dict[str, str],
        conventions: list[FixedEntityTypeConvention] | None = None,
    ) -> dict[str, str]:
        """Build effective column types for stable sidecar storage without bloating YAML."""
        return {column: resolve_fixed_entity_column_type(column, explicit_column_types, conventions) for column in columns}

    def _prepare_materialized_values(
        self,
        table: TableConfig,
        df: pd.DataFrame,
    ) -> tuple[pd.DataFrame, list[list[Any]], dict[str, str], dict[str, str]]:
        """Normalize, type, and serialize a materialized dataframe for fixed persistence."""
        normalized_df = self._normalize_materialized_dataframe(table, self._sanitize_materialized_dataframe(df))
        conventions = table.fixed_entity_type_conventions
        column_types = self._infer_materialized_column_types(normalized_df, conventions)
        values = self._serialize_materialized_values(table.entity_name, normalized_df, column_types, conventions)
        storage_column_types = self._build_materialized_storage_column_types(normalized_df.columns.tolist(), column_types, conventions)
        return normalized_df, values, column_types, storage_column_types

    async def materialize_entity(
        self,
        project_name: str,
        entity_name: str,
        storage_format: Literal["csv", "parquet", "inline"] = "parquet",
    ) -> MaterializationResult:
        """
        Materialize an entity to fixed values.

        Steps:
        1. Validate entity can be materialized
        2. Run full normalization pipeline for entity
        3. Extract DataFrame result
        4. Save DataFrame to storage (parquet/csv/inline)
        5. Snapshot current entity config to saved_state
        6. Update entity config: type=fixed, add materialized section
        7. Save updated project config
        """
        try:
            store_inline_threshold: int = Settings().MATERIALIZATION_INLINE_THRESHOLD
            api_project: Project = self.project_service.load_project(project_name)
            core_project: ShapeShiftProject = ProjectMapper.to_core(api_project)
            table_cfg: TableConfig = core_project.get_table(entity_name)

            specification: CanMaterializeSpecification = CanMaterializeSpecification(core_project)
            if not specification.is_satisfied_by(entity=table_cfg):
                return MaterializationResult(success=False, errors=[str(issue) for issue in specification.errors], entity_name=entity_name)

            logger.info(f"Materializing entity '{entity_name}' in project '{project_name}'")

            shapeshifter = ShapeShifter(project=core_project, target_entities={entity_name})
            await shapeshifter.normalize()

            if entity_name not in shapeshifter.table_store:
                raise MaterializationError(f"Entity '{entity_name}' not found in normalization results")

            df, serialized_values, column_types, storage_column_types = self._prepare_materialized_values(
                table_cfg,
                shapeshifter.table_store[entity_name],
            )

            # Determine storage strategy
            data_file: str | None = None
            values_inline: list[list[Any]] | str
            actual_format: str = storage_format

            # Always honor explicit user choice for inline
            if storage_format == "inline":
                values_inline = serialized_values
                logger.info(f"Storing {len(df)} rows inline in YAML (explicit choice)")
            # Auto-optimize small datasets to inline
            elif len(df) < store_inline_threshold:
                values_inline = serialized_values
                actual_format = "inline"
                logger.info(f"Auto-storing {len(df)} rows inline in YAML (below threshold)")
            else:
                # Construct file path and update entity config with @load: directive
                data_file = self._get_materialized_file_path(project_name, entity_name, storage_format)
                values_inline = f"@load:{data_file}"

                # Update entity config with @load: directive first
                api_project.entities[entity_name] = self._create_materialized_entity(table_cfg, df, values_inline, column_types)
                self._store_project(api_project)

                # Now write the actual data file using EntityValuesService
                self.entity_values_service.update_values(
                    project_name=project_name,
                    entity_name=entity_name,
                    columns=df.columns.tolist(),
                    values=serialized_values,
                    format_type=storage_format,
                    column_types=storage_column_types,
                )

            api_project.entities[entity_name] = self._create_materialized_entity(table_cfg, df, values_inline, column_types)

            # Save project config (only if not already saved above for external storage)
            if storage_format == "inline" or len(df) < store_inline_threshold:
                self._store_project(api_project)

            logger.info(f"Successfully materialized entity '{entity_name}' with {len(df)} rows")

            return MaterializationResult(
                success=True,
                entity_name=entity_name,
                rows_materialized=len(df),
                storage_file=data_file,
                storage_format=actual_format,
            )

        except MaterializationError as e:
            logger.error(f"Materialization error for entity '{entity_name}': {e}")
            return MaterializationResult(success=False, errors=[str(e)], entity_name=entity_name)

        except Exception as e:  # pylint: disable=broad-except
            logger.exception(f"Failed to materialize entity '{entity_name}': {e}")
            return MaterializationResult(success=False, errors=[str(e)], entity_name=entity_name)

    def _create_materialized_entity(
        self,
        table: TableConfig,
        df: pd.DataFrame,
        values_inline: list[list[Any]] | str,
        column_types: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Create the new entity config dict for the materialized entity, including saved state for unmaterialization."""
        df = self._normalize_materialized_dataframe(table, self._sanitize_materialized_dataframe(df))

        saved_state: dict[str, Any] = {}
        for k, v in table.entity_cfg.items():
            if k not in ["materialized", "values"]:
                # Skip empty/null values
                if v is None or v == "" or (isinstance(v, str) and not v.strip()):
                    continue
                saved_state[k] = v

        if not saved_state:
            logger.warning(f"Entity '{table.entity_name}' has no config to save - unmaterialization may not be possible")

        new_config = {
            "type": "fixed",
            "public_id": table.public_id,
            "keys": list(table.keys),
            "columns": list(df.columns),
            "values": values_inline if values_inline else None,
            "materialized": {
                "enabled": True,
                "source_state": saved_state,
                "materialized_at": datetime.now().isoformat(),
            },
        }

        if column_types:
            new_config["column_types"] = column_types

        return new_config

    async def unmaterialize_entity(self, project_name: str, entity_name: str, cascade: bool = False) -> UnmaterializationResult:
        """
        Restore entity to dynamic state.

        Steps:
        1. Check if entity is materialized
        2. Find dependent materialized entities (warn user)
        3. If cascade=True, unmaterialize dependents first
        4. Restore saved_state config
        5. Remove materialized section
        6. Delete data file (optional - keep for backup)
        7. Save project
        """
        try:
            api_project: Project = self.project_service.load_project(project_name)
            entity_cfg = api_project.entities.get(entity_name)

            if not isinstance(entity_cfg, dict):
                return UnmaterializationResult(
                    success=False,
                    errors=[f"Entity '{entity_name}' not found"],
                    entity_name=entity_name,
                )

            materialized_cfg = entity_cfg.get("materialized")
            if not isinstance(materialized_cfg, dict) or not materialized_cfg.get("enabled", False):
                return UnmaterializationResult(
                    success=False, errors=[f"Entity '{entity_name}' is not materialized"], entity_name=entity_name
                )

            dependents: list[str] = self._find_materialized_dependents_from_project(api_project, entity_name)

            if dependents and not cascade:
                return UnmaterializationResult(
                    success=False,
                    errors=[f"Cannot unmaterialize: entities {dependents} depend on this entity"],
                    requires_cascade=True,
                    affected_entities=dependents,
                    entity_name=entity_name,
                )

            # Cascade unmaterialize
            unmaterialized_entities: list[str] = [entity_name]
            if cascade:
                for dep in dependents:
                    result: UnmaterializationResult = await self.unmaterialize_entity(project_name, dep, cascade=True)
                    if not result.success:
                        return result
                    unmaterialized_entities.extend(result.unmaterialized_entities)

            # Restore config from saved state (includes original public_id, keys, columns, etc.)
            saved_state = materialized_cfg.get("source_state")
            if not isinstance(saved_state, dict):
                saved_state = {}
            restored_entity: dict[str, Any] = {**saved_state}

            api_project.entities[entity_name] = restored_entity

            self._store_project(api_project)

            logger.info(f"Successfully unmaterialized entity '{entity_name}'")

            return UnmaterializationResult(success=True, entity_name=entity_name, unmaterialized_entities=unmaterialized_entities)

        except MaterializationError as e:
            logger.error(f"Materialization error for entity '{entity_name}': {e}")
            return UnmaterializationResult(success=False, errors=[str(e)], entity_name=entity_name)

        except Exception as e:  # pylint: disable=broad-except
            logger.exception(f"Failed to unmaterialize entity '{entity_name}': {e}")
            return UnmaterializationResult(success=False, errors=[str(e)], entity_name=entity_name)

    @staticmethod
    def _entity_depends_on(entity_name: str, entity_cfg: dict[str, Any], dependency_name: str) -> bool:  # pylint: disable=unused-argument
        """Return True when an entity config references another entity by dependency."""
        if entity_cfg.get("source") == dependency_name:
            return True

        depends_on: list[str] = entity_cfg.get("depends_on", []) or []
        if dependency_name in depends_on:
            return True

        foreign_keys: list[dict[str, Any]] = entity_cfg.get("foreign_keys", []) or []
        for fk in foreign_keys:
            if fk.get("entity") == dependency_name:
                return True

        return False

    def _find_materialized_dependents_from_project(self, api_project: Project, entity_name: str) -> list[str]:
        """Find materialized entities whose frozen source_state depends on the given entity."""
        dependents: list[str] = []

        for candidate_name, candidate_cfg in api_project.entities.items():
            if candidate_name == entity_name or not isinstance(candidate_cfg, dict):
                continue

            materialized_cfg = candidate_cfg.get("materialized")
            if not isinstance(materialized_cfg, dict) or not materialized_cfg.get("enabled", False):
                continue

            source_state = materialized_cfg.get("source_state")
            if not isinstance(source_state, dict):
                continue

            if self._entity_depends_on(candidate_name, source_state, entity_name):
                dependents.append(candidate_name)

        return dependents

    def _find_materialized_dependents(self, core_project: ShapeShiftProject, table: TableConfig) -> list[str]:
        """Find all materialized entities that depend on the given table."""
        dependents = []
        for entity_name in table.dependent_entities():
            dep_table = core_project.get_table(entity_name)
            if dep_table and dep_table.is_materialized:
                dependents.append(entity_name)
        return dependents

    def _store_project(self, api_project: Project) -> None:
        """Save project configuration with proper error handling."""
        try:
            self.project_service.save_project(api_project)
        except Exception as e:  # pylint: disable=broad-except
            raise MaterializationError(f"Failed to save project configuration: {e}") from e
