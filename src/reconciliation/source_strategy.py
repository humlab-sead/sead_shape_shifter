"""Domain logic for reconciliation source resolution.

This module contains business logic for determining which data source to use
for reconciliation, separated from infrastructure concerns.
"""

from enum import Enum
from typing import Protocol

from src.reconciliation.model import EntityResolutionSet, ResolutionSource


class SourceStrategyType(Enum):
    """Types of reconciliation data sources (domain concept)."""

    TARGET_ENTITY = "target_entity"
    ANOTHER_ENTITY = "another_entity"
    SQL_QUERY = "sql_query"


class ReconciliationDataProvider(Protocol):
    """Protocol for loading reconciliation source data (domain interface).

    Application layer implements this protocol with actual I/O operations.
    """

    async def load_entity_data(self, entity_name: str, limit: int = 1000) -> list[dict]:
        """Load data from an entity.

        Args:
            entity_name: Name of entity to load
            limit: Maximum rows to load

        Returns:
            List of row dictionaries
        """
        ...

    async def execute_query(self, data_source: str, query: str, query_type: str = "sql") -> list[dict]:
        """Execute a custom query against a data source.

        Args:
            data_source: Data source identifier
            query: SQL query to execute
            query_type: Type of query (e.g., "sql")

        Returns:
            List of row dictionaries
        """
        ...


class ReconciliationSourceStrategy:
    """Domain service for reconciliation source resolution strategy.

    Contains pure business logic for determining which data source to use,
    without any infrastructure dependencies.
    """

    @staticmethod
    def determine_strategy(entity_name: str, source: str | ResolutionSource | None) -> SourceStrategyType:
        """Determine which source strategy to use (pure business logic).

        Business rules:
        - No source or source = entity name → use target entity
        - Source is another entity name → use that entity
        - Source is custom query spec → use custom SQL query

        Args:
            entity_name: Target entity being reconciled
            source: Source specification from entity mapping

        Returns:
            Strategy type to use

        Raises:
            ValueError: If source specification is invalid
        """
        if not source or (isinstance(source, str) and source == entity_name):
            return SourceStrategyType.TARGET_ENTITY

        if isinstance(source, str):
            return SourceStrategyType.ANOTHER_ENTITY

        if isinstance(source, ResolutionSource):
            return SourceStrategyType.SQL_QUERY

        raise ValueError(f"Invalid source specification: {source}")

    @staticmethod
    def get_source_entity_name(entity_name: str, entity_mapping: EntityResolutionSet) -> str:
        """Get the entity name to use for data (business logic).

        Args:
            entity_name: Target entity being reconciled
            entity_mapping: Entity mapping configuration

        Returns:
            Entity name to load data from
        """
        strategy = ReconciliationSourceStrategy.determine_strategy(entity_name, entity_mapping.metadata.source)

        if strategy == SourceStrategyType.TARGET_ENTITY:
            return entity_name
        if strategy == SourceStrategyType.ANOTHER_ENTITY:
            assert isinstance(entity_mapping.metadata.source, str)
            return entity_mapping.metadata.source
        return ""

    @staticmethod
    def get_resolution_source(mapping: EntityResolutionSet) -> ResolutionSource | None:
        """Extract resolution source if present.

        Args:
            entity_mapping: Entity mapping configuration

        Returns:
            Query specification or None
        """
        if isinstance(mapping.metadata.source, ResolutionSource):
            return mapping.metadata.source
        return None
