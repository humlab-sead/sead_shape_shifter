"""Reconciliation source data resolvers.

Application-layer implementations for loading reconciliation source data
based on domain strategy types.
"""

import abc
from typing import Any

import pandas as pd
from loguru import logger

from backend.app.models.shapeshift import PreviewResult
from backend.app.services import ProjectService, ShapeShiftService
from backend.app.utils.exceptions import NotFoundError
from src.loaders import DataLoader, DataLoaders
from src.model import DataSourceConfig, ShapeShiftProject, TableConfig
from src.reconciliation.model import EntityMappingDomain, ReconciliationSourceDomain
from src.reconciliation.source_strategy import SourceStrategyType


class ReconciliationSourceResolver(abc.ABC):
    """Base resolver for reconciliation source data.
    
    Application-layer implementations of domain data loading strategy.
    """

    def __init__(self, project_name: str, project: ShapeShiftProject, project_service: ProjectService):
        """Initialize resolver with core project.
        
        Args:
            project_name: Project name (for logging/preview service)
            project: Core domain project (already loaded)
            project_service: Project service (needed for preview service only)
        """
        self.project_name: str = project_name
        self.project: ShapeShiftProject = project
        self.preview_service: ShapeShiftService = ShapeShiftService(project_service)

    @abc.abstractmethod
    async def resolve(self, entity_name: str, entity_mapping: EntityMappingDomain) -> list[dict]:
        """Resolve source data based on entity spec source project."""

    @staticmethod
    def get_resolver_cls_for_strategy(
        strategy: SourceStrategyType,
    ) -> "type[ReconciliationSourceResolver]":
        """Get resolver class for the given strategy type.
        
        Maps domain strategy to application-layer resolver implementation.
        """
        resolver_map = {
            SourceStrategyType.TARGET_ENTITY: TargetEntityReconciliationSourceResolver,
            SourceStrategyType.ANOTHER_ENTITY: AnotherEntityReconciliationSourceResolver,
            SourceStrategyType.SQL_QUERY: SqlQueryReconciliationSourceResolver,
        }
        return resolver_map[strategy]


class TargetEntityReconciliationSourceResolver(ReconciliationSourceResolver):
    """Loads data from the target entity itself (implements SourceStrategyType.TARGET_ENTITY)."""

    async def resolve(self, entity_name: str, entity_mapping: EntityMappingDomain) -> list[dict]:
        logger.debug(f"Using preview data from entity '{entity_name}'")
        preview_result: PreviewResult = await self.preview_service.preview_entity(self.project_name, entity_name, limit=1000)
        return preview_result.rows


class AnotherEntityReconciliationSourceResolver(ReconciliationSourceResolver):
    """Loads data from a different entity (implements SourceStrategyType.ANOTHER_ENTITY)."""

    async def resolve(self, entity_name: str, entity_mapping: EntityMappingDomain) -> list[dict]:

        assert isinstance(entity_mapping.source, str)

        source: str = entity_mapping.source

        logger.info(f"Fetching preview data from entity '{source}' for reconciliation of '{entity_name}'")

        if source not in self.project.tables:
            raise NotFoundError(f"Source entity '{source}' not found in project")

        preview_result: PreviewResult = await self.preview_service.preview_entity(self.project_name, source, limit=1000)
        source_data = preview_result.rows

        logger.debug(f"Fetched {len(source_data)} rows from entity '{source}'")
        return source_data


class SqlQueryReconciliationSourceResolver(ReconciliationSourceResolver):
    """Executes custom SQL query (implements SourceStrategyType.SQL_QUERY)."""

    async def resolve(self, entity_name: str, entity_mapping: EntityMappingDomain) -> list[dict]:

        assert isinstance(entity_mapping.source, ReconciliationSourceDomain)

        source: str | ReconciliationSourceDomain = entity_mapping.source
        logger.info(f"Executing custom query for reconciliation of '{entity_name}'")

        # Get data source config from ShapeShiftProject
        if source.data_source not in self.project.data_sources:
            raise NotFoundError(f"Data source '{source.data_source}' not found in project")

        data_source_config: DataSourceConfig = self.project.get_data_source(source.data_source)

        loader: DataLoader = DataLoaders.get(data_source_config.driver)(data_source_config)
        sql_cfg_dict: dict[str, Any] = {
            "source": None,
            "type": source.type,
            "keys": [],
            "columns": [],
            "data_source": source.data_source,
            "query": source.query,
        }
        table_cfg: TableConfig = TableConfig(entities_cfg=sql_cfg_dict, entity_name="recon_temp")
        custom_data: pd.DataFrame = await loader.load(entity_name=entity_name, table_cfg=table_cfg)
        logger.debug(f"Custom query returned {len(custom_data)} rows")
        return custom_data.to_dict(orient="records")
