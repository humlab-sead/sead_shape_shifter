"""Service for entity materialization operations."""

from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from loguru import logger
from pandas import DataFrame

from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.models.materialization import (
    MaterializationResult,
    UnmaterializationResult,
)
from backend.app.models.project import Project
from backend.app.services.project_service import ProjectService
from backend.app.utils import convert_ruamel_types
from src.specifications.materialize import CanMaterializeSpecification
from src.model import ShapeShiftProject, TableConfig
from src.normalizer import ShapeShifter

STORE_INLINE_THRESHOLD = 20  # Rows below which data is stored inline in YAML


class MaterializationService:
    """Service for materializing and unmaterializing entities."""

    def __init__(self, project_service: ProjectService):
        """Initialize service with project service dependency."""
        self.project_service: ProjectService = project_service

    async def materialize_entity(
        self,
        project_name: str,
        entity_name: str,
        user_email: str | None = None,
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
            # Load project
            api_project: Project = self.project_service.load_project(project_name)
            core_project: ShapeShiftProject = ProjectMapper.to_core(api_project)

            # Validate
            table: TableConfig = core_project.get_table(entity_name)
            specification: CanMaterializeSpecification = CanMaterializeSpecification(core_project)
            if not specification.is_satisfied_by(entity=table):
                return MaterializationResult(
                    success=False,
                    errors=[str(issue) for issue in specification.errors],
                    entity_name=entity_name,
                )

            # Run normalization (dependencies + target entity)
            logger.info(f"Materializing entity '{entity_name}' in project '{project_name}'")
            shapeshifter = ShapeShifter(project=core_project, target_entities={entity_name})
            await shapeshifter.normalize()

            # Get result DataFrame
            if entity_name not in shapeshifter.table_store:
                return MaterializationResult(
                    success=False,
                    errors=[f"Entity '{entity_name}' not found in normalization results"],
                    entity_name=entity_name,
                )

            df: DataFrame = shapeshifter.table_store[entity_name]

            # Determine storage strategy
            data_file: str = ""
            values_inline = None

            if storage_format == "inline" or len(df) < STORE_INLINE_THRESHOLD:
                # Inline: convert DataFrame to list of lists
                try:
                    values_inline = df.values.tolist()
                    logger.info(f"Storing {len(df)} rows inline in YAML")
                except Exception as e:  # pylint: disable=broad-except
                    return MaterializationResult(
                        success=False,
                        errors=[f"Failed to convert data to inline format: {e}"],
                        entity_name=entity_name,
                    )
            else:
                # External file storage
                data_dir = Path(f"projects/{project_name}/materialized")

                try:
                    data_dir.mkdir(parents=True, exist_ok=True)
                except OSError as e:
                    return MaterializationResult(
                        success=False,
                        errors=[f"Failed to create materialized directory: {e}"],
                        entity_name=entity_name,
                    )

                try:
                    if storage_format == "parquet":
                        data_file: str = f"materialized/{entity_name}.parquet"
                        full_path: Path = data_dir / f"{entity_name}.parquet"
                        df.to_parquet(full_path, index=False)
                        logger.info(f"Saved {len(df)} rows to {full_path}")
                    else:  # csv
                        data_file = f"materialized/{entity_name}.csv"
                        full_path = data_dir / f"{entity_name}.csv"
                        df.to_csv(full_path, index=False)
                        logger.info(f"Saved {len(df)} rows to {full_path}")
                except (OSError, PermissionError) as e:
                    return MaterializationResult(
                        success=False,
                        errors=[f"Failed to write data file: {e}"],
                        entity_name=entity_name,
                    )
                except Exception as e:  # pylint: disable=broad-except
                    return MaterializationResult(
                        success=False,
                        errors=[f"Unexpected error saving data: {e}"],
                        entity_name=entity_name,
                    )

            # Snapshot current config (exclude identity and structural fields)
            # Convert ruamel.yaml types to plain Python types to avoid serialization issues
            saved_state: dict[str, Any] = {}
            for k, v in table.entity_cfg.items():
                if k not in ["materialized", "values"]:
                    # Skip empty/null values
                    if v is None or v == "" or (isinstance(v, str) and not v.strip()):
                        continue
                    # Recursively convert ruamel.yaml types to plain Python types
                    saved_state[k] = convert_ruamel_types(v)

            # Build new config (convert all ruamel.yaml types)
            new_config = {
                "type": "fixed",
                "public_id": convert_ruamel_types(table.public_id),
                "keys": convert_ruamel_types(list(table.keys)),
                "columns": convert_ruamel_types(list(df.columns)),
                "materialized": {
                    "enabled": True,
                    "source_state": saved_state,
                    "materialized_at": datetime.now().isoformat(),
                    "materialized_by": user_email,
                    "data_file": data_file,
                },
            }

            if values_inline:
                new_config["values"] = convert_ruamel_types(values_inline)
            elif data_file:
                new_config["values"] = f"@file:{data_file}"

            # Update project (entities are stored as raw dicts)
            api_project.entities[entity_name] = new_config

            try:
                self.project_service.save_project(api_project)
            except Exception as e:  # pylint: disable=broad-except
                return MaterializationResult(
                    success=False,
                    errors=[f"Failed to save project configuration: {e}"],
                    entity_name=entity_name,
                )

            logger.info(f"Successfully materialized entity '{entity_name}' with {len(df)} rows")

            return MaterializationResult(
                success=True,
                entity_name=entity_name,
                rows_materialized=len(df),
                storage_file=data_file,
                storage_format=storage_format if data_file else "inline",
            )

        except Exception as e:  # pylint: disable=broad-except
            logger.exception(f"Failed to materialize entity '{entity_name}': {e}")
            return MaterializationResult(success=False, errors=[str(e)], entity_name=entity_name)

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
            # Load project
            api_project: Project = self.project_service.load_project(project_name)
            core_project: ShapeShiftProject = ProjectMapper.to_core(api_project)

            # Validate
            table = core_project.get_table(entity_name)

            if not table.is_materialized:
                return UnmaterializationResult(
                    success=False, errors=[f"Entity '{entity_name}' is not materialized"], entity_name=entity_name
                )

            # Find materialized dependents
            dependents = self._find_materialized_dependents(core_project, entity_name)

            if dependents and not cascade:
                return UnmaterializationResult(
                    success=False,
                    errors=[f"Cannot unmaterialize: entities {dependents} depend on this entity"],
                    requires_cascade=True,
                    affected_entities=dependents,
                    entity_name=entity_name,
                )

            # Cascade unmaterialize
            unmaterialized_entities = [entity_name]
            if cascade:
                for dep in dependents:
                    result = await self.unmaterialize_entity(project_name, dep, cascade=True)
                    if not result.success:
                        return result
                    unmaterialized_entities.extend(result.unmaterialized_entities)

            # Restore config
            saved_state = table.materialized.source_state or {}
            restored_config = {
                **saved_state,
                "public_id": table.public_id,
                "keys": list(table.keys),
            }

            # Update project (entities are stored as raw dicts)
            api_project.entities[entity_name] = restored_config

            try:
                self.project_service.save_project(api_project)
            except Exception as e:  # pylint: disable=broad-except
                return UnmaterializationResult(
                    success=False,
                    errors=[f"Failed to save project configuration: {e}"],
                    entity_name=entity_name,
                )

            logger.info(f"Successfully unmaterialized entity '{entity_name}'")

            return UnmaterializationResult(success=True, entity_name=entity_name, unmaterialized_entities=unmaterialized_entities)

        except Exception as e:  # pylint: disable=broad-except
            logger.error(f"Failed to unmaterialize entity '{entity_name}': {e}")
            return UnmaterializationResult(success=False, errors=[str(e)], entity_name=entity_name)

    def _find_materialized_dependents(self, core_project, table):
        return [t for t in table.dependent_entities() if core_project.get_table(t).is_materialized]
