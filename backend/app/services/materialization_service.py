"""Service for entity materialization operations."""

from datetime import datetime
from typing import Any, Literal

import pandas as pd
from loguru import logger

from backend.app.core.config import Settings
from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.models.materialization import (
    MaterializationResult,
    UnmaterializationResult,
)
from backend.app.models.project import Project
from backend.app.services.entity_values_service import EntityValuesService
from backend.app.services.project_service import ProjectService
from src.model import ShapeShiftProject, TableConfig
from src.normalizer import ShapeShifter
from src.specifications.materialize import CanMaterializeSpecification

# pylint: disable=redefined-builtin


class MaterializationError(Exception):
    """Custom exception for materialization errors."""


class MaterializationService:
    """Service for materializing and unmaterializing entities."""

    def __init__(self, project_service: ProjectService):
        """Initialize service with project service dependency."""
        self.project_service: ProjectService = project_service
        self.entity_values_service: EntityValuesService = EntityValuesService(project_service)

    def _get_materialized_file_path(self, project_name: str, entity_name: str, format: str) -> str:
        """Get relative path for materialized file (relative to project folder)."""
        extension = "parquet" if format == "parquet" else "csv"
        return f"materialized/{entity_name}.{extension}"

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

            df: pd.DataFrame = shapeshifter.table_store[entity_name]

            # Determine storage strategy
            data_file: str | None = None
            values_inline: list[list[Any]] | str
            actual_format: str = storage_format

            # Always honor explicit user choice for inline
            if storage_format == "inline":
                values_inline = df.values.tolist()
                logger.info(f"Storing {len(df)} rows inline in YAML (explicit choice)")
            # Auto-optimize small datasets to inline
            elif len(df) < store_inline_threshold:
                values_inline = df.values.tolist()
                actual_format = "inline"
                logger.info(f"Auto-storing {len(df)} rows inline in YAML (below threshold)")
            else:
                # Construct file path and update entity config with @load: directive
                data_file = self._get_materialized_file_path(project_name, entity_name, storage_format)
                values_inline = f"@load:{data_file}"

                # Update entity config with @load: directive first
                api_project.entities[entity_name] = self._create_materialized_entity(table_cfg, df, values_inline)
                self._store_project(api_project)

                # Now write the actual data file using EntityValuesService
                self.entity_values_service.update_values(
                    project_name=project_name,
                    entity_name=entity_name,
                    columns=df.columns.tolist(),
                    values=df.values.tolist(),
                    format_type=storage_format,
                )

            api_project.entities[entity_name] = self._create_materialized_entity(table_cfg, df, values_inline)

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

    def _create_materialized_entity(self, table: TableConfig, df: pd.DataFrame, values_inline: list[list[Any]] | str) -> dict[str, Any]:
        """Create the new entity config dict for the materialized entity, including saved state for unmaterialization."""
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
            core_project: ShapeShiftProject = ProjectMapper.to_core(api_project)
            table_cfg: TableConfig = core_project.get_table(entity_name)

            if not table_cfg.is_materialized:
                return UnmaterializationResult(
                    success=False, errors=[f"Entity '{entity_name}' is not materialized"], entity_name=entity_name
                )

            dependents: list[str] = self._find_materialized_dependents(core_project, table_cfg)

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
            saved_state: dict[str, Any] = table_cfg.materialized.source_state or {}
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
