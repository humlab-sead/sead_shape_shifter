"""Service for previewing entity data with transformations."""

import contextlib
import time

import pandas as pd
from loguru import logger

from backend.app.core.config import Settings, settings
from backend.app.core.state_manager import ApplicationState, get_app_state
from backend.app.core.utility import friendly_dtype
from backend.app.models.shapeshift import ColumnInfo, PreviewResult
from backend.app.services.project_service import ProjectService, get_project_service
from backend.app.utils.caches import ShapeShiftCache, ShapeShiftProjectCache
from src.model import ShapeShiftProject, TableConfig
from src.normalizer import ShapeShifter


class ShapeShiftService:
    """Service for previewing entity data with caching."""

    def __init__(self, project_service: ProjectService, ttl_seconds: int = 300):
        self.project_service: ProjectService = project_service
        self.cache: ShapeShiftCache = ShapeShiftCache(ttl_seconds=ttl_seconds)  # 5 minute cache
        self.project_cache = ShapeShiftProjectCache(project_service)
        self.settings: Settings = settings

    async def preview_entity(self, project_name: str, entity_name: str, limit: int | None = 50) -> PreviewResult:
        """
        Preview entity data with all transformations applied.

        Uses cached DataFrames to reuse dependencies and target entity from previous runs.

        Args:
            project_name: Name of the project file
            entity_name: Name of the entity to preview
            limit: Maximum number of rows to return (default 50). Use None for all rows.

        Returns:
            PreviewResult with data and metadata

        Raises:
            ValueError: If project or entity not found
            RuntimeError: If preview fails
        """
        start_time: float = time.time()

        project: ShapeShiftProject = await self.project_cache.get_project(project_name)
        project_version: int = self.get_project_version(project_name)

        if entity_name not in project.tables:
            raise ValueError(f"Entity '{entity_name}' not found in project")

        entity_cfg: TableConfig = project.tables[entity_name]

        cached_data: ShapeShiftCache.CacheCheckResult = self.cache.fetch_cached_entity_data(
            project_name, entity_name, project_version, entity_cfg, project
        )

        table_store: dict[str, pd.DataFrame]
        if cached_data.data is not None:
            table_store = {entity_name: cached_data.data} | cached_data.dependencies
        else:
            resolved_cfg: ShapeShiftProject = project.clone().resolve(filename=project.filename, **self.settings.env_opts)
            table_store = await self.shapeshift(
                project=resolved_cfg,
                entity_name=entity_name,
                initial_table_store=cached_data.dependencies,
            )

            entities: dict[str, TableConfig] = {name: project.get_table(name) for name in table_store.keys()}
            self.cache.set_table_store(project_name, table_store, entity_name, project_version, entities)

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
        project: ShapeShiftProject,
        entity_name: str,
        initial_table_store: dict[str, pd.DataFrame],
    ) -> dict[str, pd.DataFrame]:
        """
        Run ShapeShifter to produce entity data.

        Args:
            project: ShapeShiftProject instance
            entity: Target entity name
            initial_table_store: Pre-existing cached entities to reuse

        Returns:
            Complete table_store with target entity and all dependencies
        """
        try:
            shapeshifter: ShapeShifter = ShapeShifter(
                project=project,
                table_store=initial_table_store,
                default_entity=project.metadata.default_entity,
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

    async def get_entity_sample(self, project_name: str, entity_name: str, limit: int = 100) -> PreviewResult:
        """
        Get a sample of entity data (larger limit for validation/testing).

        Args:
            project_name: Name of the project file
            entity_name: Name of the entity
            limit: Maximum number of rows (default 100, max 1000)

        Returns:
            PreviewResult with sample data
        """
        return await self.preview_entity(project_name, entity_name, limit)

    def invalidate_cache(self, project_name: str, entity_name: str | None = None) -> None:
        """Invalidate preview cache for a project or specific entity."""
        self.cache.invalidate(project_name, entity_name)
        logger.info(f"Invalidated preview cache for {project_name}:{entity_name or 'all'}")

    def get_project_version(self, project_name: str) -> int:
        """Get the current version of a project from ApplicationState."""
        with contextlib.suppress(RuntimeError):
            app_state: ApplicationState = get_app_state()
            return app_state.get_version(project_name)
        return 0  # ApplicationState not initialized


class PreviewResultBuilder:

    def build(
        self,
        entity_name: str,
        entity_cfg: TableConfig,
        table_store: dict[str, pd.DataFrame],
        limit: int | None,
        cache_hit: bool,
    ) -> PreviewResult:
        """Build PreviewResult from table_store with limit applied.

        Args:
            entity_name: Name of the entity
            entity_cfg: Entity project
            table_store: Dictionary of DataFrames
            limit: Maximum rows to return, or None for all rows
            cache_hit: Whether result came from cache
        """
        if entity_name not in table_store:
            raise RuntimeError(f"Entity {entity_name} not found in table_store")

        preview_df: pd.DataFrame = table_store[entity_name].head(limit) if limit is not None else table_store[entity_name]

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


# Singleton instance
_shapeshift_service: ShapeShiftService | None = None  # pylint: disable=invalid-name


def get_shapeshift_service() -> ShapeShiftService:
    """Get singleton ShapeShiftService instance."""
    global _shapeshift_service  # pylint: disable=global-statement
    if _shapeshift_service is None:

        _shapeshift_service = ShapeShiftService(project_service=get_project_service())
    return _shapeshift_service
