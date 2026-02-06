"""
Entity Generator Service

Provides functionality to generate entity configurations from database tables.
Automatically detects primary keys, data types, and other metadata.
"""

from typing import Any

from loguru import logger

from backend.app.api.v1.endpoints import columns
from backend.app.core.config import settings
from backend.app.exceptions import ResourceConflictError, ResourceNotFoundError
from backend.app.models.data_source import DataSourceConfig, TableSchema
from backend.app.models.project import Project
from backend.app.services.data_source_service import DataSourceService
from backend.app.services.project_service import ProjectService, get_project_service
from backend.app.services.schema_service import SchemaIntrospectionService
from loaders.sql_loaders import SqlLoader


class EntityGeneratorService:
    """Service for generating entity configurations from database tables."""

    def __init__(self, schema_service: SchemaIntrospectionService | None = None, project_service: ProjectService | None = None):
        """Initialize entity generator service."""
        self.schema_service: SchemaIntrospectionService = schema_service or SchemaIntrospectionService(settings.PROJECTS_DIR)
        self.project_service: ProjectService = project_service or get_project_service()
        self.data_source_service: DataSourceService = self.schema_service.data_source_service

    async def generate_from_table(
        self, project_name: str, data_source_key: str, table_name: str, entity_name: str | None = None, schema: str | None = None
    ) -> dict[str, Any]:
        """
        Generate entity configuration from a database table.

        Args:
            project_name: Name of the project to add entity to
            data_source_key: Name of the data source
            table_name: Name of the table in the database
            entity_name: Optional entity name (defaults to table_name)
            schema: Optional schema name if the database supports schemas (e.g. PostgreSQL)

        Returns:
            Generated entity configuration dict

        Raises:
            ResourceNotFoundError: If project or data source not found
            ResourceConflictError: If entity name already exists in project
        """
        # 1. Validate project exists
        project: Project = self.project_service.load_project(project_name)

        # Resolve project data_source key → actual data source identifier/config for schema introspection
        data_source_cfg: str | dict[str, Any] = self._resolve_data_source(project, project_name, data_source_key)
        data_source: DataSourceConfig | None = self.data_source_service.load_data_source(data_source_cfg)

        # 2. Determine entity name (default to table name)
        entity_name = entity_name or table_name

        # 3. Check for entity name conflicts
        if entity_name in project.entities:
            raise ResourceConflictError(f"Entity '{entity_name}' already exists in project '{project_name}'")

        # 4. Get table schema metadata
        logger.info(f"Fetching schema for table '{table_name}' from project data source '{data_source_key}'")

        table_schema: TableSchema = await self.schema_service.get_table_schema(data_source_cfg, table_name, schema=schema)

        # 5. Extract primary keys
        primary_keys: list[str] = [col.name for col in table_schema.columns if col.is_primary_key]
        logger.debug(f"Detected primary keys for '{table_name}': {primary_keys}")

        # 6. Build query (preserve schema prefix if present)
        query: str = self.generate_sql_select(data_source, table_schema)

        # 7. Generate entity configuration
        entity_config = {
            "type": "sql",
            "system_id": "system_id",
            "data_source": data_source_key,
            "query": query,
            "keys": primary_keys,  # Empty list if no PKs
            "public_id": f"{table_name}_id",
        }

        # 8. Add entity to project
        logger.info(f"Adding entity '{entity_name}' to project '{project_name}'")
        self.project_service.add_entity_by_name(project_name, entity_name, entity_config)

        logger.success(f"Successfully generated entity '{entity_name}' from table '{table_name}'")
        return entity_config

    def generate_sql_select(self, data_source: DataSourceConfig | None, table_schema: TableSchema) -> str:

        full_table_name: str = (
            f"{table_schema.schema_name}.{table_schema.table_name}" if table_schema.schema_name else table_schema.table_name
        )

        if data_source is None:
            return f"SELECT * FROM {full_table_name}"  # Fallback if data source config is missing

        loader: SqlLoader = self.schema_service.create_loader_for_data_source(data_source)
        columns: str = ", ".join(loader.quote_name(col.name) for col in table_schema.columns)
        query: str = f"SELECT {columns} FROM {loader.qualify_name(schema=table_schema.schema_name, table=table_schema.table_name)}"
        return query

    def _resolve_data_source(self, project: Project, project_name: str, ds_key: str) -> str | dict[str, Any]:

        if ds_key not in project.data_sources:
            raise ResourceNotFoundError(
                message=f"Data source '{ds_key}' not found in project '{project_name}'",
                resource_type="data_source",
                resource_id=ds_key,
                context={"project": project_name, "available_data_sources": sorted(project.data_sources.keys())},
            )

        value: Any = project.data_sources[ds_key]

        if isinstance(value, dict):
            return value

        if isinstance(value, str):

            ref: str = value.strip()

            if not ref.startswith("@include:"):
                return ref

            filename: str = ref.split(":", 1)[1].strip()

            if filename:
                return filename

        raise ResourceNotFoundError(
            message=f"Data source '{ds_key}' in project '{project_name}' has an unsupported configuration type",
            resource_type="data_source",
            resource_id=ds_key,
            context={"project": project_name, "value_type": type(value).__name__},
        )


def get_entity_generator_service() -> EntityGeneratorService:
    """Get entity generator service instance."""
    return EntityGeneratorService()
