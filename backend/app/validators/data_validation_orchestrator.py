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
from backend.app.services.project_service import ProjectService
from backend.app.services.shapeshift_service import ShapeShiftService
from src.model import ShapeShiftProject
from src.normalizer import ShapeShifter
from src.validators.data_validators import (
    ColumnExistsValidator,
    DataTypeCompatibilityValidator,
    DuplicateKeysValidator,
    ForeignKeyDataValidator,
    ForeignKeyIntegrityValidator,
    NaturalKeyUniquenessValidator,
    NonEmptyResultValidator,
    ValidationIssue,
)


class DataFetchStrategy(ABC):
    """Strategy interface for fetching entity data."""

    @abstractmethod
    async def fetch(self, project_name: str, entity_name: str) -> pd.DataFrame:
        """Fetch data for an entity."""
        pass


class PreviewDataFetchStrategy(DataFetchStrategy):
    """Strategy for fetching preview sample data."""

    def __init__(self, preview_service: ShapeShiftService, limit: int = 1000) -> None:
        self.preview_service: ShapeShiftService = preview_service
        self.limit: int = limit

    async def fetch(self, project_name: str, entity_name: str) -> pd.DataFrame:
        """Fetch preview sample data."""
        preview_result: api.PreviewResult = await self.preview_service.preview_entity(
            project_name=project_name,
            entity_name=entity_name,
            limit=self.limit,
        )

        if not preview_result.rows:
            return pd.DataFrame()

        return pd.DataFrame(preview_result.rows)


class FullDataFetchStrategy(DataFetchStrategy):
    """Strategy for fetching full normalized datasets."""

    def __init__(self, project_service: ProjectService) -> None:
        self.project_service: ProjectService = project_service
        self._normalizer_cache: dict[str, ShapeShifter] = {}

    async def fetch(self, project_name: str, entity_name: str) -> pd.DataFrame:
        """Fetch full normalized dataset."""
        # Get or create normalizer for this project
        if project_name not in self._normalizer_cache:
            project: api.Project = self.project_service.load_project(project_name)
            core_project: ShapeShiftProject = ProjectMapper.to_core(project)
            normalizer = ShapeShifter(core_project)
            await normalizer.normalize()
            self._normalizer_cache[project_name] = normalizer

        normalizer: ShapeShifter = self._normalizer_cache[project_name]

        if entity_name not in normalizer.table_store:
            return pd.DataFrame()

        return normalizer.table_store[entity_name]


class TableStoreDataFetchStrategy(DataFetchStrategy):
    """Strategy for fetching from pre-existing table store (already normalized)."""

    def __init__(self, table_store: dict[str, pd.DataFrame]) -> None:
        self.table_store: dict[str, pd.DataFrame] = table_store

    async def fetch(self, project_name: str, entity_name: str) -> pd.DataFrame:
        """Fetch from existing table store."""
        return self.table_store.get(entity_name, pd.DataFrame())


class DataValidationOrchestrator:
    """
    Orchestrator for data validation operations.

    Responsibilities:
    - Fetch data using injected strategy
    - Coordinate domain validators
    - Return domain ValidationIssues (consumer transforms as needed)
    """

    def __init__(self, fetch_strategy: DataFetchStrategy) -> None:
        """
        Initialize orchestrator with data fetch strategy.

        Args:
            fetch_strategy: Strategy for fetching entity data (preview, full, or table_store)
        """
        self.fetch_strategy: DataFetchStrategy = fetch_strategy

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

        # Get resolved entity configurations from core project
        resolved_entities: dict[str, Any] = core_project.cfg.get("entities", {})

        # Filter entities if specified
        if entity_names:
            resolved_entities = {name: cfg for name, cfg in resolved_entities.items() if name in entity_names}

        # Run data validation for each entity
        for entity_name, entity_cfg in resolved_entities.items():
            entity_issues: list[ValidationIssue] = await self._validate_entity(
                project_name=project_name,
                entity_name=entity_name,
                entity_cfg=entity_cfg,
            )
            issues.extend(entity_issues)

        return issues

    async def _validate_entity(
        self,
        project_name: str,
        entity_name: str,
        entity_cfg: dict[str, Any],
    ) -> list[ValidationIssue]:
        """
        Validate a single entity.

        Args:
            project_name: Project name
            entity_name: Entity name
            entity_cfg: Resolved entity configuration

        Returns:
            List of domain validation issues for this entity
        """
        issues: list[ValidationIssue] = []

        try:
            # Fetch data using injected strategy
            df: pd.DataFrame = await self.fetch_strategy.fetch(project_name, entity_name)

            # Run basic validators
            issues.extend(NonEmptyResultValidator.validate(df, entity_name))

            if not df.empty:
                return issues  # Skip further validation if no data to validate

            # Validate columns
            columns: list[str] = entity_cfg.get("columns", [])
            if columns:
                issues.extend(ColumnExistsValidator.validate(df, columns, entity_name, entity_cfg))

            # Validate natural keys
            keys: list[str] = entity_cfg.get("keys", [])
            if keys:
                issues.extend(NaturalKeyUniquenessValidator.validate(df, keys, entity_name))
                issues.extend(DuplicateKeysValidator.validate(df, keys, entity_name))

            # Validate foreign keys
            fk_configs: list[dict[str, Any]] = entity_cfg.get("foreign_keys", [])
            for fk_config in fk_configs:
                # Validate FK columns exist
                issues.extend(ForeignKeyDataValidator.validate(df, fk_config, entity_name))

                # Validate FK integrity (requires remote data)
                remote_entity: str | None = fk_config.get("entity")
                if remote_entity:
                    try:
                        remote_df: pd.DataFrame = await self.fetch_strategy.fetch(project_name, remote_entity)

                        issues.extend(ForeignKeyIntegrityValidator.validate(df, remote_df, fk_config, entity_name))
                        issues.extend(DataTypeCompatibilityValidator.validate(df, remote_df, fk_config, entity_name))
                    except Exception as e:
                        logger.warning(f"Could not validate FK integrity for {entity_name} -> {remote_entity}: {e}")

        except Exception as e:
            logger.warning(f"Could not validate entity {entity_name}: {e}")
            issues.append(
                ValidationIssue(
                    severity="warning",
                    entity=entity_name,
                    field=None,
                    message=f"Could not validate entity: {str(e)}",
                    code="VALIDATION_FAILED",
                    suggestion="Check data source configuration and connectivity",
                    category="data",
                    priority="low",
                )
            )

        return issues
