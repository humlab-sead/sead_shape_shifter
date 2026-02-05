"""
Entity Generator Service

Provides functionality to generate entity configurations from database tables.
Automatically detects primary keys, data types, and other metadata.
"""

from typing import Any

from loguru import logger

from backend.app.exceptions import ResourceConflictError, ResourceNotFoundError
from backend.app.services.project_service import ProjectService, get_project_service
from backend.app.services.schema_service import SchemaIntrospectionService
from backend.app.core.config import settings


class EntityGeneratorService:
    """Service for generating entity configurations from database tables."""

    def __init__(self, schema_service: SchemaIntrospectionService | None = None, project_service: ProjectService | None = None):
        """Initialize entity generator service."""
        self.schema_service = schema_service or SchemaIntrospectionService(settings.DATA_SOURCE_FILES_DIR)
        self.project_service = project_service or get_project_service()

    async def generate_from_table(
        self, project_name: str, data_source: str, table_name: str, entity_name: str | None = None, schema: str | None = None
    ) -> dict[str, Any]:
        """
        Generate entity configuration from a database table.

        Args:
            project_name: Name of the project to add entity to
            data_source: Name of the data source
            table_name: Name of the table in the database
            entity_name: Optional entity name (defaults to table_name)
            schema: Optional schema name for PostgreSQL databases

        Returns:
            Generated entity configuration dict

        Raises:
            ResourceNotFoundError: If project or data source not found
            ResourceConflictError: If entity name already exists in project
        """
        # 1. Validate project exists
        try:
            project = self.project_service.load_project(project_name)
        except ResourceNotFoundError as e:
            raise ResourceNotFoundError(f"Project '{project_name}' not found") from e

        # 2. Determine entity name (default to table name)
        entity_name = entity_name or table_name

        # 3. Check for entity name conflicts
        if entity_name in project.entities:
            raise ResourceConflictError(f"Entity '{entity_name}' already exists in project '{project_name}'")

        # 4. Get table schema metadata
        logger.info(f"Fetching schema for table '{table_name}' from data source '{data_source}'")
        table_schema = await self.schema_service.get_table_schema(data_source, table_name, schema=schema)

        # 5. Extract primary keys
        primary_keys = [col.name for col in table_schema.columns if col.is_primary_key]
        logger.debug(f"Detected primary keys for '{table_name}': {primary_keys}")

        # 6. Build query (preserve schema prefix if present)
        full_table_name = f"{schema}.{table_name}" if schema else table_name
        query = f"SELECT * FROM {full_table_name}"

        # 7. Generate entity configuration
        entity_config = {
            "type": "sql",
            "data_source": data_source,
            "query": query,
            "keys": primary_keys,  # Empty list if no PKs
            "public_id": f"{table_name}_id",
        }

        # 8. Add entity to project
        logger.info(f"Adding entity '{entity_name}' to project '{project_name}'")
        self.project_service.add_entity_by_name(project_name, entity_name, entity_config)

        logger.success(f"Successfully generated entity '{entity_name}' from table '{table_name}'")
        return entity_config


def get_entity_generator_service() -> EntityGeneratorService:
    """Get entity generator service instance."""
    return EntityGeneratorService()
