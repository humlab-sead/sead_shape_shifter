"""Service for previewing entity data with transformations."""

import contextlib
import itertools
import time
from dataclasses import dataclass
from typing import Any

import pandas as pd
from loguru import logger

from backend.app.core.config import Settings, settings
from backend.app.core.state_manager import ApplicationState, get_app_state
from backend.app.core.utility import friendly_dtype
from backend.app.mappers.entity_config_mapper import EntityConfigMapper, EntityConfigMapperFactory, EntityMapperContext
from backend.app.models.shapeshift import ColumnInfo, PreviewResult
from backend.app.services.project_service import ProjectService, get_project_service
from backend.app.utils.caches import ShapeShiftCache, ShapeShiftProjectCache
from src.exceptions import FunctionalDependencyError, MissingBusinessKeyError
from src.model import ShapeShiftProject, TableConfig
from src.normalizer import ShapeShifter
from src.specifications.constraints import ForeignKeyConstraintViolation, ForeignKeyNullConstraintViolation, ValidationIssue
from src.table_store import TableStore
from src.validation_messages import format_validation_message_with_context


@dataclass
class ProjectNormalizationResult:
    """Result of one project-wide normalization pass.

    Attributes:
        table_store: Every entity produced by the pass.
        validation_issues_by_entity: Normalization issues grouped per produced entity.
        incomplete_entities: Entity name to failure reason for entities that were not produced.
        normalizer: Finished ``ShapeShifter`` instance, used to read extra-column and linker issues.
        project_version: Project version the data was produced from.
    """

    table_store: TableStore
    validation_issues_by_entity: dict[str, list[dict[str, Any]]]
    incomplete_entities: dict[str, str]
    normalizer: ShapeShifter
    project_version: int


class ShapeShiftService:
    """Service for previewing entity data with caching."""

    def __init__(self, project_service: ProjectService, ttl_seconds: int = 300):
        self.project_service: ProjectService = project_service
        self.cache: ShapeShiftCache = ShapeShiftCache(ttl_seconds=ttl_seconds)  # 5 minute cache
        self.project_cache = ShapeShiftProjectCache(project_service)
        self.settings: Settings = settings
        # Optional warm table_store populated by a project-wide run to short-circuit later preview calls
        self._warm_table_store: TableStore | None = None
        self._warm_validation_issues: dict[str, list[dict[str, Any]]] = {}
        self._warm_project_name: str | None = None
        self._warm_project_version: int | None = None
        self._warm_timestamp: float = 0.0
        self._warm_incomplete_entities: dict[str, str] = {}
        self._warm_normalizer: ShapeShifter | None = None
        # Initialize entity config mapper factory for type-specific transformations
        self._mapper_factory = EntityConfigMapperFactory(self.settings)

    def _resolve_entity_config(self, entity_config: dict[str, Any], context: EntityMapperContext, entity_name: str) -> None:
        """Apply type-specific transformations to entity config using strategy pattern.

        For file-based entities: resolves (filename, location) to absolute path.
        For other entities: no-op (returns config unchanged).

        This is needed when override_config bypasses ProjectMapper.to_core().

        Args:
            entity_config: Entity configuration dictionary (modified in-place)
            context: Context for entity mapping, including project name and options
        """
        # Get appropriate mapper based on entity type
        mapper: EntityConfigMapper = self._mapper_factory.get_mapper_for_entity(entity_config)
        # Apply transformation (API → Core: resolve paths)
        transformed: dict[str, Any] = mapper.to_core(dict(entity_config), context, entity_name=entity_name)
        entity_config.update(transformed)

    async def preview_entity(
        self, project_name: str, entity_name: str, limit: int | None = 50, override_config: dict[str, Any] | None = None
    ) -> PreviewResult:
        """
        Preview entity data with all transformations applied.

        Uses cached DataFrames to reuse dependencies and target entity from previous runs.
        Supports previewing unsaved entity configurations via override_config.

        Args:
            project_name: Name of the project file
            entity_name: Name of the entity to preview
            limit: Maximum number of rows to return (default 50). Use None for all rows.
            override_config: Optional entity configuration dict to preview (bypasses cache)

        Returns:
            PreviewResult with data and metadata

        Raises:
            ValueError: If project or entity not found
            RuntimeError: If preview fails
        """
        start_time: float = time.time()

        project: ShapeShiftProject = await self.project_cache.get_project(project_name)
        project_version: int = self.get_project_version(project_name)

        override_indicator = "yes" if override_config else "no"
        logger.trace(
            f"[PREVIEW_START] {project_name}/{entity_name}: project_version={project_version}, " f"override_config={override_indicator}"
        )

        # If override_config provided, temporarily replace entity config
        using_override: bool = override_config is not None
        if using_override:
            # Apply type-specific transformation to override_config
            # (override bypasses ProjectMapper.to_core(), so we must transform here)
            context = EntityMapperContext(project_name=project_name, project_options=project.options)
            self._resolve_entity_config(override_config, context, entity_name)

            # Clone project and replace entity config
            project = project.clone()
            project.cfg["entities"][entity_name] = override_config
            # Clear cached tables property to force rebuild with new config
            if "tables" in project.__dict__:
                del project.__dict__["tables"]
            logger.debug(f"Preview using override config for entity '{entity_name}'")

        if entity_name not in project.tables:
            raise ValueError(f"Entity '{entity_name}' not found in project")

        entity_cfg: TableConfig = project.tables[entity_name]

        # Fast path: reuse the warm table_store from a project-wide run, but only while it
        # matches the current project version and has not outlived the cache TTL.
        if (
            not using_override
            and self._warm_table_store
            and entity_name in self._warm_table_store
            and self._warm_project_name == project_name
            and self._warm_project_version == project_version
            and time.time() - self._warm_timestamp < self.cache.ttl_seconds
        ):
            table_store = TableStore({entity_name: self._warm_table_store[entity_name]})
            validation_issues = self._warm_validation_issues.get(entity_name, [])
            cached_hit = True
        else:
            # Skip cache lookup when using override config
            if using_override:
                cached_data = ShapeShiftCache.CacheCheckResult(found=False, data=None, dependencies=TableStore())
                cached_hit = False
            else:
                cached_data: ShapeShiftCache.CacheCheckResult = self.cache.fetch_cached_entity_data(
                    project_name, entity_name, project_version, entity_cfg, project
                )
                cached_hit = cached_data.data is not None

            table_store: TableStore
            validation_issues: list[dict] = []

            if cached_data.data is not None:
                table_store = TableStore({entity_name: cached_data.data} | cached_data.dependencies)
                cached_dependency_issues = [
                    issue for dependency_issues in cached_data.dependency_validation_issues.values() for issue in dependency_issues
                ]
                validation_issues = self._deduplicate_validation_issues(cached_data.validation_issues + cached_dependency_issues)
            else:
                resolved_cfg: ShapeShiftProject = project.clone().resolve(filename=project.filename, strict=True, **self.settings.env_opts)
                table_store, validation_issues = await self.shapeshift(
                    project=resolved_cfg,
                    entity_name=entity_name,
                    initial_table_store=cached_data.dependencies,
                )
                cached_dependency_issues = [
                    issue for dependency_issues in cached_data.dependency_validation_issues.values() for issue in dependency_issues
                ]
                validation_issues = self._deduplicate_validation_issues(cached_dependency_issues + validation_issues)

                # Only cache if not using override config
                if not using_override:
                    entities: dict[str, TableConfig] = {name: project.get_table(name) for name in table_store.keys()}
                    hashes = [(name, cfg.hash()[:8]) for name, cfg in entities.items()]
                    logger.trace(f"[CACHE_SET] {project_name}/{entity_name}: project_version={project_version}, hashes={hashes}")
                    validation_issues_by_entity = self._validation_issues_by_entity(
                        validation_issues,
                        project,
                        list(table_store.keys()),
                    )
                    self.cache.set_table_store(
                        project_name,
                        table_store,
                        entity_name,
                        project_version,
                        entities,
                        validation_issues_by_entity,
                    )

        result: PreviewResult = PreviewResultBuilder().build(
            entity_name=entity_name,
            entity_cfg=entity_cfg,
            table_store=table_store,
            limit=limit,
            cache_hit=cached_hit,
            validation_issues=validation_issues,
        )

        execution_time_ms: int = int((time.time() - start_time) * 1000)
        result.execution_time_ms = execution_time_ms

        return result

    async def shapeshift_batch(
        self,
        project: ShapeShiftProject,
        entity_names: list[str],
        initial_table_store: TableStore,
        *,
        continue_on_error: bool = False,
    ) -> tuple[TableStore, list[dict]]:
        """
        Run ShapeShifter to produce multiple entities in one pass.

        Args:
            project: ShapeShiftProject instance
            entity_names: List of target entity names to process
            initial_table_store: Pre-existing cached entities to reuse
            continue_on_error: When True, one failing entity does not abort the whole run.
                Entities that fail, and entities that depend on them, are reported in
                ``ShapeShifter.incomplete_entities`` instead.

        Returns:
            Tuple of (Complete table_store with target entities and all dependencies, validation issues)
        """
        shapeshifter: ShapeShifter = await self._normalize_batch(
            project=project,
            entity_names=entity_names,
            initial_table_store=initial_table_store,
            continue_on_error=continue_on_error,
        )

        return shapeshifter.table_store, self._collect_validation_issues(shapeshifter)

    async def _normalize_batch(
        self,
        project: ShapeShiftProject,
        entity_names: list[str],
        initial_table_store: TableStore,
        *,
        continue_on_error: bool,
    ) -> ShapeShifter:
        """Run one ShapeShifter pass and return the finished normalizer."""
        try:
            shapeshifter: ShapeShifter = ShapeShifter(
                project=project,
                table_store=initial_table_store,
                default_entity=project.metadata.default_entity,
                target_entities=set(entity_names),
            )

            await shapeshifter.normalize(continue_on_error=continue_on_error)
            shapeshifter.add_system_id_columns()
            shapeshifter.move_keys_to_front()

            return shapeshifter

        except (
            FunctionalDependencyError,
            ForeignKeyConstraintViolation,
            ForeignKeyNullConstraintViolation,
            MissingBusinessKeyError,
        ):
            raise

        except Exception as e:
            logger.exception(f"ShapeShift batch failed for {len(entity_names)} entities: {e}", exc_info=True)
            raise RuntimeError(f"ShapeShift batch failed: {str(e)}") from e

    async def normalize_project(
        self,
        project_name: str,
        entity_names: list[str] | None = None,
    ) -> ProjectNormalizationResult:
        """Normalize every requested entity in a single ShapeShifter pass.

        One pass replaces the per-entity preview calls used by sample data validation.
        Entities that fail to normalize, and entities that depend on them, are reported in
        ``incomplete_entities`` instead of aborting the run.

        Produced entities are written to the shared cache and kept as the warm table store,
        so later preview requests and validation runs reuse them instead of recomputing.

        Args:
            project_name: Name of the project file.
            entity_names: Entities to produce. None produces every configured entity.

        Returns:
            ProjectNormalizationResult with the produced data, validation issues per entity,
            and the reason for every entity that could not be produced.

        Raises:
            ValueError: If a requested entity is not configured in the project.
            RuntimeError: If the normalization pass cannot complete.
        """
        start_time: float = time.time()
        project: ShapeShiftProject = await self.project_cache.get_project(project_name)
        project_version: int = self.get_project_version(project_name)

        names: list[str] = list(entity_names) if entity_names is not None else list(project.table_names)
        missing_entities: list[str] = [name for name in names if name not in project.tables]
        if missing_entities:
            raise ValueError(f"Entities not found in project '{project_name}': {', '.join(missing_entities)}")

        reusable: ProjectNormalizationResult | None = self._reusable_warm_result(project_name, project_version, set(names))
        if reusable is not None:
            logger.info(f"Reusing normalized data for {project_name} (version {project_version})")
            return reusable

        resolved_project: ShapeShiftProject = project
        if not project.is_resolved():
            resolved_project = project.clone().resolve(filename=project.filename, strict=True, **self.settings.env_opts)

        shapeshifter: ShapeShifter = await self._normalize_batch(
            project=resolved_project,
            entity_names=names,
            initial_table_store=TableStore(),
            continue_on_error=True,
        )

        table_store: TableStore = shapeshifter.table_store
        validation_issues: list[dict] = self._deduplicate_validation_issues(self._collect_validation_issues(shapeshifter))
        validation_issues_by_entity: dict[str, list[dict[str, Any]]] = self._validation_issues_by_entity(
            validation_issues, project, list(table_store.keys())
        )

        entity_configs: dict[str, TableConfig] = {name: project.get_table(name) for name in table_store.keys() if project.has_table(name)}
        self.cache.set_table_store(
            project_name=project_name,
            table_store=table_store,
            target_entity="project",
            project_version=project_version,
            entity_configs=entity_configs,
            validation_issues_by_entity=validation_issues_by_entity,
        )

        incomplete_entities: dict[str, str] = dict(shapeshifter.incomplete_entities)

        self._warm_table_store = table_store
        self._warm_validation_issues = validation_issues_by_entity
        self._warm_project_name = project_name
        self._warm_project_version = project_version
        self._warm_timestamp = time.time()
        self._warm_incomplete_entities = incomplete_entities
        self._warm_normalizer = shapeshifter

        elapsed_ms: int = int((time.time() - start_time) * 1000)
        logger.info(
            f"Normalized {len(table_store)} of {len(names)} entities for {project_name} in {elapsed_ms}ms "
            f"({len(incomplete_entities)} incomplete)"
        )
        if incomplete_entities:
            logger.warning(f"Incomplete entities for {project_name}: {sorted(incomplete_entities)}")

        return ProjectNormalizationResult(
            table_store=table_store,
            validation_issues_by_entity=validation_issues_by_entity,
            incomplete_entities=incomplete_entities,
            normalizer=shapeshifter,
            project_version=project_version,
        )

    def _reusable_warm_result(
        self, project_name: str, project_version: int, requested_entity_names: set[str]
    ) -> ProjectNormalizationResult | None:
        """Return a fresh warm result when it covers the requested project entities."""
        if self._warm_table_store is None or self._warm_normalizer is None:
            return None
        if self._warm_project_name != project_name:
            return None
        if self._warm_incomplete_entities:
            return None
        if self._warm_project_version != project_version:
            return None
        if not requested_entity_names.issubset(self._warm_table_store.keys()):
            return None
        if time.time() - self._warm_timestamp >= self.cache.ttl_seconds:
            return None

        return ProjectNormalizationResult(
            table_store=self._warm_table_store,
            validation_issues_by_entity=self._warm_validation_issues,
            incomplete_entities={},
            normalizer=self._warm_normalizer,
            project_version=project_version,
        )

    async def shapeshift(
        self,
        project: ShapeShiftProject,
        entity_name: str,
        initial_table_store: TableStore,
    ) -> tuple[TableStore, list[dict]]:
        """
        Run ShapeShifter to produce entity data.

        Args:
            project: ShapeShiftProject instance
            entity_name: Target entity name
            initial_table_store: Pre-existing cached entities to reuse

        Returns:
            Tuple of (Complete table_store with target entity and all dependencies, validation issues)
        """
        try:
            target_entities: set[str] = {entity_name}

            logger.info(f"ShapeShift preview for entity: {entity_name}")
            logger.debug(f"Initial table_store contains: {list(initial_table_store.keys())}")

            shapeshifter: ShapeShifter = ShapeShifter(
                project=project,
                table_store=initial_table_store,
                default_entity=project.metadata.default_entity,
                target_entities=target_entities,
            )

            # Log which entities will be processed
            required_entities = project.get_required_entities(entity_name)
            logger.info(f"Required entities for '{entity_name}': {sorted(required_entities)}")

            (await shapeshifter.normalize())
            shapeshifter.add_system_id_columns()
            shapeshifter.move_keys_to_front()

            if entity_name not in shapeshifter.table_store:
                raise RuntimeError(f"Entity {entity_name} was not produced by normalizer")

            # Collect validation issues from the linker
            validation_issues = self._collect_validation_issues(shapeshifter)

            return shapeshifter.table_store, validation_issues

        except (
            FunctionalDependencyError,
            ForeignKeyConstraintViolation,
            ForeignKeyNullConstraintViolation,
            MissingBusinessKeyError,
        ):
            raise

        except Exception as e:
            logger.exception(f"ShapeShift failed for {entity_name}: {e}", exc_info=True)

            # Provide more detailed error for KeyErrors (often FK dependency issues)
            if isinstance(e, KeyError):
                missing_entity = str(e).strip("'\"")
                raise RuntimeError(
                    f"ShapeShift failed for '{entity_name}': Missing dependency '{missing_entity}'. "
                    f"This entity may have a foreign key referencing '{missing_entity}', but '{missing_entity}' "
                    f"was not processed. Check your entity configuration for unexpected foreign key references."
                ) from e

            raise RuntimeError(f"ShapeShift failed for {entity_name}: {str(e)}") from e

    def _collect_validation_issues(self, shapeshifter: ShapeShifter) -> list[dict]:
        """Collect validation issues from the linker's constraint validators."""

        all_issues: list[dict] = []

        # Access the linker's validators to collect issues
        # The linker stores validators that have been run during linking
        linker_issues = itertools.chain.from_iterable(getattr(validator, "issues", []) for validator in shapeshifter.linker.validators)

        for issue in linker_issues:
            if isinstance(issue, ValidationIssue):
                all_issues.append(
                    {
                        "type": issue.issue_type,
                        "severity": issue.severity,
                        "local_entity": issue.local_entity,
                        "remote_entity": issue.remote_entity,
                        "message": issue.message,
                        "metadata": issue.metadata,
                    }
                )

        for entity_name, unresolved_columns in shapeshifter.unresolved_extra_columns.items():
            for column_name, details in sorted(unresolved_columns.items()):
                missing_dependencies = details.get("missing_dependencies", [])
                expression = details.get("expression")
                field_name: str = f"extra_columns.{column_name}"

                message: str = f"Derived column '{column_name}' could not be resolved during preview"
                if missing_dependencies:
                    message = f"{message} because these referenced columns are still missing: " f"{', '.join(missing_dependencies)}"
                message = format_validation_message_with_context(
                    message=message, entity=entity_name, field=field_name, expression=expression
                )

                all_issues.append(
                    {
                        "type": "extra_column_unresolved",
                        "severity": "error",
                        "local_entity": entity_name,
                        "remote_entity": None,
                        "message": message,
                        "metadata": {
                            "field": field_name,
                            "expression": expression,
                            "missing_dependencies": missing_dependencies,
                        },
                    }
                )

        return all_issues

    @staticmethod
    def _deduplicate_validation_issues(issues: list[dict]) -> list[dict]:
        """Remove repeated normalization issues while preserving their original order."""
        unique_issues: list[dict] = []
        for issue in issues:
            entity_name = issue.get("local_entity")
            if not isinstance(entity_name, str):
                raise ValueError("Normalization issue must include a string 'local_entity'")
            if issue not in unique_issues:
                unique_issues.append(issue)
        return unique_issues

    @staticmethod
    def _validation_issues_by_entity(
        issues: list[dict],
        project: ShapeShiftProject,
        entity_names: list[str],
    ) -> dict[str, list[dict]]:
        """Assign each normalization issue to requested entities that depend on its local entity."""
        issues_by_entity: dict[str, list[dict]] = {}
        for entity_name in entity_names:
            required_entities = set(project.get_required_entities(entity_name))
            required_entities.add(entity_name)
            issues_by_entity[entity_name] = [issue for issue in issues if issue["local_entity"] in required_entities]
        return issues_by_entity

    async def preview_entities_batch(self, project_name: str, entity_names: list[str]) -> TableStore:
        """
        Process multiple entities in one ShapeShifter run to populate cache efficiently.

        This method processes all requested entities plus their dependencies in a single
        normalization pass, then caches all results. This is much more efficient than
        processing entities individually when validating multiple entities.

        Args:
            project_name: Name of the project file
            entity_names: List of entity names to process

        Returns:
            Dictionary mapping entity names to DataFrames

        Raises:
            ValueError: If project not found
            RuntimeError: If processing fails
        """
        start_time: float = time.time()
        logger.info(f"Batch processing {len(entity_names)} entities for {project_name}")

        project: ShapeShiftProject = await self.project_cache.get_project(project_name)
        project_version: int = self.get_project_version(project_name)

        # Validate all entities exist
        missing_entities: list[str] = [name for name in entity_names if name not in project.tables]
        if missing_entities:
            raise ValueError(f"Entities not found in project '{project_name}': {', '.join(missing_entities)}")

        # Run single ShapeShifter normalization for all target entities
        resolved_project: ShapeShiftProject = project
        if not project.is_resolved():
            resolved_project = project.clone().resolve(filename=project.filename, strict=True, **self.settings.env_opts)

        table_store, validation_issues = await self.shapeshift_batch(
            project=resolved_project,
            entity_names=entity_names,  # Pass actual target entities
            initial_table_store=TableStore(),
        )

        validation_issues = self._deduplicate_validation_issues(validation_issues)
        validation_issues_by_entity = self._validation_issues_by_entity(validation_issues, project, list(table_store.keys()))

        # Cache all processed entities (target entities + dependencies) in one call
        entities: dict[str, TableConfig] = {name: project.get_table(name) for name in table_store.keys()}
        self.cache.set_table_store(
            project_name=project_name,
            table_store=table_store,
            target_entity="batch",  # Just for logging
            project_version=project_version,
            entity_configs=entities,
            validation_issues_by_entity=validation_issues_by_entity,
        )

        # Preserve warm table_store for subsequent preview calls in this service instance
        self._warm_table_store = table_store
        self._warm_validation_issues = validation_issues_by_entity
        self._warm_project_name = project_name
        self._warm_project_version = project_version
        self._warm_timestamp = time.time()
        self._warm_incomplete_entities = {}
        self._warm_normalizer = None

        elapsed_ms: int = int((time.time() - start_time) * 1000)
        logger.info(f"Batch processed {len(table_store)} entities in {elapsed_ms}ms (cache populated)")

        return table_store

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
        self._warm_table_store = None
        self._warm_validation_issues = {}
        self._warm_project_name = None
        self._warm_project_version = None
        self._warm_timestamp = 0.0
        self._warm_incomplete_entities = {}
        self._warm_normalizer = None
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
        table_store: TableStore,
        limit: int | None,
        cache_hit: bool,
        validation_issues: list[dict] | None = None,
    ) -> PreviewResult:
        """Build PreviewResult from table_store with limit applied.

        Args:
            entity_name: Name of the entity
            entity_cfg: Entity project
            table_store: Dictionary of DataFrames
            limit: Maximum rows to return, or None for all rows
            cache_hit: Whether result came from cache
            validation_issues: Validation issues from linking
        """
        if entity_name not in table_store:
            raise RuntimeError(f"Entity {entity_name} not found in table_store")

        preview_df: pd.DataFrame = table_store[entity_name].head(limit) if limit is not None else table_store[entity_name]

        key_columns: set[str] = entity_cfg.get_key_columns()
        # Columns produced independently of extra_columns. Unnest id_vars are
        # passthrough inputs, not outputs, so an extra_columns entry may supply one.
        existing_result_columns: set[str] = set(entity_cfg.columns)
        existing_result_columns.add(entity_cfg.system_id)
        if entity_cfg.public_id:
            existing_result_columns.add(entity_cfg.public_id)
        existing_result_columns.update(entity_cfg.unnest_columns)

        derived_columns: set[str] = {
            column_name
            for column_name in (entity_cfg.extra_columns or {}).keys()
            if column_name not in existing_result_columns and column_name in preview_df.columns
        }

        columns: list[ColumnInfo] = [
            ColumnInfo(
                name=col_name,
                data_type=friendly_dtype(preview_df[col_name].dtype),
                nullable=bool(preview_df[col_name].isnull().any()),
                is_key=col_name in key_columns,
                is_derived=col_name in derived_columns,
                derived_from="extra_columns" if col_name in derived_columns else None,
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
            validation_issues=validation_issues or [],
        )


# Singleton instance
_shapeshift_service: ShapeShiftService | None = None  # pylint: disable=invalid-name


def get_shapeshift_service() -> ShapeShiftService:
    """Get singleton ShapeShiftService instance."""
    global _shapeshift_service  # pylint: disable=global-statement
    if _shapeshift_service is None:

        _shapeshift_service = ShapeShiftService(project_service=get_project_service())
    return _shapeshift_service
