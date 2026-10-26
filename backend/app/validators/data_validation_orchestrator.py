"""Backend orchestrator for data validation - handles data fetching and coordination.

This orchestrator:
1. Fetches data using injected strategy (preview, full, or table_store)
2. Calls pure domain validators from src/validators/
3. Returns domain ValidationIssues (consumer decides how to transform)
"""

from abc import ABC, abstractmethod
from typing import Any

import pandas as pd
from loguru import logger

from backend.app import models as api
from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.mappers.validation_mapper import ValidationMapper
from backend.app.models.validation import (
    DataValidationStatus,
    EntityDataValidationResult,
    EntityDataValidationStatus,
)
from backend.app.services.project_service import ProjectService
from backend.app.services.shapeshift_service import ShapeShiftService
from src.model import ShapeShiftProject
from src.normalizer import ShapeShifter
from src.specifications.constraints import ValidationIssue as LinkerValidationIssue
from src.table_store import TableStore
from src.target_model.data_validators import (
    AllowedValuesConformanceValidator,
    FKReferentialIntegrityConformanceValidator,
    NullabilityConformanceValidator,
    TypeCompatibilityConformanceValidator,
)
from src.target_model.models import TargetModel
from src.validators.data_validators import (
    BusinessKeyProducedValidator,
    ColumnExistsValidator,
    DataTypeCompatibilityValidator,
    ForeignKeyDataValidator,
    ForeignKeyIntegrityValidator,
    NaturalKeyUniquenessValidator,
    NonEmptyResultValidator,
    UnresolvedExtraColumnsValidator,
    ValidationIssue,
)


class DataFetchStrategy(ABC):
    """Strategy interface for fetching entity data."""

    @abstractmethod
    async def fetch(self, project_name: str, entity_name: str) -> pd.DataFrame:
        """Fetch data for an entity."""
        raise NotImplementedError

    async def get_additional_issues(self, project_name: str, entity_name: str) -> list[ValidationIssue]:  # pylint: disable=unused-argument
        """Return strategy-specific validation issues for an entity."""
        return []

    async def prepare(self, _project_name: str) -> None:
        """Prepare data for validation before any entity checks run."""
        return None


class PreviewDataFetchStrategy(DataFetchStrategy):
    """Strategy for fetching preview sample data."""

    def __init__(self, preview_service: ShapeShiftService, limit: int = 1000) -> None:
        self.preview_service: ShapeShiftService = preview_service
        self.limit: int = limit
        self._preview_issues: dict[tuple[str, str], list[ValidationIssue]] = {}

    async def fetch(self, project_name: str, entity_name: str) -> pd.DataFrame:
        """Fetch preview sample data."""
        preview_result: api.PreviewResult = await self.preview_service.preview_entity(
            project_name=project_name,
            entity_name=entity_name,
            limit=self.limit,
        )

        self._preview_issues[(project_name, entity_name)] = [
            ValidationMapper.from_preview_issue_payload(issue) for issue in preview_result.validation_issues
        ]

        if not preview_result.rows:
            return pd.DataFrame()

        return pd.DataFrame(preview_result.rows)

    async def get_additional_issues(self, project_name: str, entity_name: str) -> list[ValidationIssue]:
        """Return structured issues found while producing the entity preview."""
        return list(self._preview_issues.get((project_name, entity_name), []))


class FullDataFetchStrategy(DataFetchStrategy):
    """Strategy for fetching full normalized datasets."""

    def __init__(self, project_service: ProjectService) -> None:
        self.project_service: ProjectService = project_service
        self._normalizer_cache: dict[str, ShapeShifter] = {}
        self._normalization_errors: dict[str, Exception] = {}
        self._normalization_attempted: set[str] = set()
        self.failed_entity: str | None = None

    async def prepare(self, project_name: str) -> None:
        """Normalize the full project once and fail before exposing partial tables."""
        if project_name in self._normalization_attempted:
            if project_name in self._normalization_errors:
                raise self._normalization_errors[project_name]
            normalizer = self._normalizer_cache[project_name]
            if normalizer.incomplete_entities:
                entity_name, reason = next(iter(normalizer.incomplete_entities.items()))
                self.failed_entity = entity_name
                error = RuntimeError(f"Entity '{entity_name}' is incomplete: {reason}")
                self._normalization_errors[project_name] = error
                raise error
            return

        self._normalization_attempted.add(project_name)
        normalizer: ShapeShifter | None = None
        try:
            project: api.Project = self.project_service.load_project(project_name)
            core_project: ShapeShiftProject = ProjectMapper.to_core(project)
            normalizer = ShapeShifter(core_project)
            self._normalizer_cache[project_name] = normalizer
            await normalizer.normalize()
        except Exception as e:
            self.failed_entity = getattr(e, "entity_name", None)
            if self.failed_entity is None and normalizer is not None:
                self.failed_entity = next(iter(normalizer.incomplete_entities), None)
            self._normalization_errors[project_name] = e
            raise

        if normalizer.incomplete_entities:
            entity_name, reason = next(iter(normalizer.incomplete_entities.items()))
            self.failed_entity = entity_name
            error = RuntimeError(f"Entity '{entity_name}' is incomplete: {reason}")
            self._normalization_errors[project_name] = error
            raise error

    async def fetch(self, project_name: str, entity_name: str) -> pd.DataFrame:
        """Fetch full normalized dataset."""
        await self.prepare(project_name)

        normalizer: ShapeShifter = self._normalizer_cache[project_name]

        if entity_name not in normalizer.table_store:
            raise KeyError(f"Entity '{entity_name}' was not produced by full normalization")

        return normalizer.table_store[entity_name]

    async def get_additional_issues(self, project_name: str, entity_name: str) -> list[ValidationIssue]:
        """Return validation issues discovered only after full normalization."""
        normalizer = self._normalizer_cache.get(project_name)
        if normalizer is None:
            return []

        issues: list[ValidationIssue] = []
        unresolved_extra_columns = normalizer.unresolved_extra_columns.get(entity_name, {})
        issues.extend(UnresolvedExtraColumnsValidator.validate(unresolved_extra_columns, entity_name))

        for validator in normalizer.linker.validators:
            for issue in getattr(validator, "issues", []):
                if isinstance(issue, LinkerValidationIssue) and issue.local_entity == entity_name:
                    issues.append(ValidationMapper.from_linker_issue(issue))

        return issues


class TableStoreDataFetchStrategy(DataFetchStrategy):
    """Strategy for fetching from pre-existing table store (already normalized)."""

    def __init__(self, table_store: TableStore) -> None:
        self.table_store: TableStore = table_store

    async def fetch(self, project_name: str, entity_name: str) -> pd.DataFrame:
        """Fetch from existing table store."""
        if entity_name not in self.table_store:
            raise KeyError(f"Entity '{entity_name}' is not available in the table store")
        return self.table_store[entity_name]


class DataValidationOrchestrator:
    """
    Orchestrator for data validation operations.

    Responsibilities:
    - Fetch data using injected strategy
    - Coordinate domain validators
    - Return domain ValidationIssues (consumer transforms as needed)
    """

    def __init__(self, fetch_strategy: DataFetchStrategy, target_model: TargetModel | None = None) -> None:
        """
        Initialize orchestrator with data fetch strategy.

        Args:
            fetch_strategy: Strategy for fetching entity data (preview, full, or table_store)
            target_model: Optional resolved target model for data conformance checks
                          (nullability, type compatibility, FK referential integrity).
        """
        self.fetch_strategy: DataFetchStrategy = fetch_strategy
        self.target_model: TargetModel | None = target_model
        self.status: DataValidationStatus = DataValidationStatus.COMPLETED
        self.status_reason: str | None = None
        self.entity_statuses: dict[str, EntityDataValidationResult] = {}
        self._reported_additional_issues: list[ValidationIssue] = []

    async def validate_all_entities(
        self,
        core_project: ShapeShiftProject,
        project_name: str,
        entity_names: list[str] | None = None,
    ) -> list[ValidationIssue]:
        """
        Validate all or specified entities.

        Args:
            core_project: Resolved core project (with directives expanded)
            project_name: Name of project (for data fetching)
            entity_names: Optional list of entities to validate (None = all)

        Returns:
            List of domain validation issues (consumer converts to API models if needed)
        """
        issues: list[ValidationIssue] = []
        self.status = DataValidationStatus.COMPLETED
        self.status_reason = None
        self.entity_statuses = {}
        self._reported_additional_issues = []

        # Get resolved entity configurations from core project
        resolved_entities: dict[str, Any] = core_project.cfg.get("entities", {})

        # Filter entities if specified
        if entity_names:
            resolved_entities = {name: cfg for name, cfg in resolved_entities.items() if name in entity_names}

        ordered_names = self._dependency_order(core_project, list(resolved_entities))

        try:
            await self.fetch_strategy.prepare(project_name)
        except Exception as e:  # pylint: disable=broad-exception-caught
            self._record_full_run_failure(ordered_names, e)
            return issues

        for entity_name in ordered_names:
            entity_cfg = resolved_entities[entity_name]
            failed_dependencies = [
                dependency
                for dependency in self._dependencies(core_project, entity_name)
                if dependency in self.entity_statuses and self.entity_statuses[dependency].status != EntityDataValidationStatus.COMPLETED
            ]
            if failed_dependencies:
                dependency = failed_dependencies[0]
                dependency_status = self.entity_statuses[dependency]
                reason = dependency_status.reason or f"Entity '{dependency}' could not be validated"
                self.entity_statuses[entity_name] = EntityDataValidationResult(
                    status=EntityDataValidationStatus.SKIPPED,
                    reason=f"Skipped because prerequisite entity '{dependency}' was {dependency_status.status.value}: {reason}",
                )
                continue

            try:
                entity_issues: list[ValidationIssue] = []
                try:
                    await self._validate_entity(
                        project_name=project_name,
                        entity_name=entity_name,
                        entity_cfg=entity_cfg,
                        issues=entity_issues,
                        reported_additional_issues=self._reported_additional_issues,
                    )
                finally:
                    issues.extend(entity_issues)
            except Exception as e:  # pylint: disable=broad-exception-caught
                reason = str(e)
                logger.warning(f"Data validation for entity '{entity_name}' failed: {reason}")
                self.entity_statuses[entity_name] = EntityDataValidationResult(
                    status=EntityDataValidationStatus.FAILED,
                    reason=reason,
                )
            else:
                self.entity_statuses[entity_name] = EntityDataValidationResult(status=EntityDataValidationStatus.COMPLETED)

        self._set_overall_status()

        return issues

    def _dependencies(self, core_project: ShapeShiftProject, entity_name: str) -> set[str]:
        """Return the configured dependencies for an entity."""
        if not isinstance(core_project, ShapeShiftProject) or not core_project.has_table(entity_name):
            return set()
        return core_project.get_table(entity_name).depends_on

    def _dependency_order(self, core_project: ShapeShiftProject, entity_names: list[str]) -> list[str]:
        """Order entity checks so prerequisite previews run before dependent previews."""
        allowed = set(entity_names)
        ordered: list[str] = []
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(entity_name: str) -> None:
            if entity_name in visited or entity_name in visiting:
                return
            visiting.add(entity_name)
            for dependency in self._dependencies(core_project, entity_name):
                if dependency in allowed:
                    visit(dependency)
            visiting.remove(entity_name)
            visited.add(entity_name)
            ordered.append(entity_name)

        for name in entity_names:
            visit(name)
        return ordered

    def _record_full_run_failure(self, entity_names: list[str], error: Exception) -> None:
        """Record a normalization failure without running dataframe validators."""
        reason = str(error)
        logger.error(f"Full normalization failed; data validation was not run: {reason}")
        error_entity = getattr(error, "entity_name", None) or getattr(self.fetch_strategy, "failed_entity", None)
        if error_entity is None:
            self.entity_statuses = {
                name: EntityDataValidationResult(status=EntityDataValidationStatus.FAILED, reason=reason) for name in entity_names
            }
        else:
            self.entity_statuses = {
                name: EntityDataValidationResult(
                    status=EntityDataValidationStatus.FAILED if name == error_entity else EntityDataValidationStatus.SKIPPED,
                    reason=reason if name == error_entity else f"Skipped because full normalization failed for '{error_entity}': {reason}",
                )
                for name in entity_names
            }
            if error_entity not in self.entity_statuses:
                self.entity_statuses[error_entity] = EntityDataValidationResult(
                    status=EntityDataValidationStatus.FAILED,
                    reason=reason,
                )
        self.status = DataValidationStatus.FAILED
        self.status_reason = reason

    def _set_overall_status(self) -> None:
        """Set the run status from entity execution statuses."""
        if all(status.status == EntityDataValidationStatus.COMPLETED for status in self.entity_statuses.values()):
            self.status = DataValidationStatus.COMPLETED
            return

        has_completed = any(status.status == EntityDataValidationStatus.COMPLETED for status in self.entity_statuses.values())
        self.status = DataValidationStatus.PARTIAL if has_completed else DataValidationStatus.FAILED
        self.status_reason = "One or more entity checks failed or were skipped."

    async def _validate_entity(
        self,
        project_name: str,
        entity_name: str,
        entity_cfg: dict[str, Any],
        issues: list[ValidationIssue],
        reported_additional_issues: list[ValidationIssue],
    ) -> None:
        """
        Validate a single entity.

        Args:
            project_name: Project name
            entity_name: Entity name
            entity_cfg: Resolved entity configuration

        Returns:
            List of domain validation issues for this entity
        """
        df: pd.DataFrame = await self.fetch_strategy.fetch(project_name, entity_name)
        for issue in await self.fetch_strategy.get_additional_issues(project_name, entity_name):
            if issue not in reported_additional_issues:
                issues.append(issue)
                reported_additional_issues.append(issue)
        issues.extend(NonEmptyResultValidator.validate(df, entity_name))

        if df.empty:
            return

        columns: list[str] = entity_cfg.get("columns", [])
        if columns:
            issues.extend(ColumnExistsValidator.validate(df, columns, entity_name, entity_cfg))

        keys: list[str] = entity_cfg.get("keys", [])
        if keys:
            issues.extend(BusinessKeyProducedValidator.validate(df, keys, entity_name))
            issues.extend(NaturalKeyUniquenessValidator.validate(df, keys, entity_name))

        fk_configs: list[dict[str, Any]] = entity_cfg.get("foreign_keys", [])
        for fk_config in fk_configs:
            issues.extend(ForeignKeyDataValidator.validate(df, fk_config, entity_name))

            remote_entity: str | None = fk_config.get("entity")
            if remote_entity:
                remote_df: pd.DataFrame = await self.fetch_strategy.fetch(project_name, remote_entity)
                issues.extend(ForeignKeyIntegrityValidator.validate(df, remote_df, fk_config, entity_name))
                issues.extend(DataTypeCompatibilityValidator.validate(df, remote_df, fk_config, entity_name))

        if self.target_model is not None:
            entity_spec = self.target_model.entities.get(entity_name)
            if entity_spec is not None:
                issues.extend(NullabilityConformanceValidator.validate(df, entity_spec, entity_name))
                issues.extend(TypeCompatibilityConformanceValidator.validate(df, entity_spec, entity_name))
                issues.extend(AllowedValuesConformanceValidator.validate(df, entity_spec, entity_name))

                for fk_spec in entity_spec.foreign_keys:
                    if not fk_spec.required or fk_spec.via:
                        continue
                    target_entity_spec = self.target_model.entities.get(fk_spec.entity)
                    if target_entity_spec is None or not target_entity_spec.public_id:
                        continue
                    target_df: pd.DataFrame = await self.fetch_strategy.fetch(project_name, fk_spec.entity)
                    issues.extend(
                        FKReferentialIntegrityConformanceValidator.validate(df, fk_spec, target_df, target_entity_spec, entity_name)
                    )
