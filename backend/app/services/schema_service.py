"""
Schema Introspection Service

Provides database schema introspection capabilities for PostgreSQL and MS Access.
Discovers tables, columns, data types, and relationships.
"""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import pandas as pd
from loguru import logger

import backend.app.models.data_source as api
from backend.app.mappers.data_source_mapper import DataSourceMapper
from backend.app.mappers.table_schema_mapper import TableSchemaMapper
from backend.app.models.entity_import import KeySuggestion
from backend.app.services.data_source_service import DataSourceService
from src.model import DataSourceConfig as CoreDataSourceConfig
from src.configuration.interface import ConfigLike
from src.loaders.base_loader import DataLoaders
from src.loaders.sql_loaders import CoreSchema, SqlLoader


class SchemaServiceError(Exception):
    """Base exception for schema service errors."""


class SchemaCache:
    """Simple in-memory cache for schema data."""

    def __init__(self, ttl_seconds: int = 300):
        self._cache: dict[str, tuple[Any, datetime]] = {}
        self._ttl = timedelta(seconds=ttl_seconds)

    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired."""
        if key in self._cache:
            value, timestamp = self._cache[key]
            if datetime.now() - timestamp < self._ttl:
                return value
            # Expired, remove
            del self._cache[key]
        return None

    def set(self, key: str, value: Any) -> None:
        """Cache a value with current timestamp."""
        self._cache[key] = (value, datetime.now())

    def invalidate(self, key: str) -> None:
        """Remove a cached value."""
        if key in self._cache:
            del self._cache[key]

    def clear(self) -> None:
        """Clear entire cache."""
        self._cache.clear()


class SchemaIntrospectionService:
    """Service for introspecting database schemas."""

    def __init__(self, data_source_dir: str | Path):
        self.data_source_dir: Path = Path(data_source_dir)
        self.data_source_service: DataSourceService = DataSourceService(data_source_dir)
        self.cache: SchemaCache = SchemaCache(ttl_seconds=300)  # 5 minute cache

    def create_loader_for_data_source(self, ds_config: api.DataSourceConfig) -> SqlLoader:
        core_config: CoreDataSourceConfig = DataSourceMapper.to_core_config(ds_config)

        loader_cls: type[SqlLoader] | None = DataLoaders.get(core_config.driver)
        if not loader_cls:
            raise SchemaServiceError(f"Schema introspection not supported for driver: {core_config.driver}")
        loader: SqlLoader = loader_cls(data_source=core_config)
        if not isinstance(loader, SqlLoader):
            raise SchemaServiceError(f"Schema introspection not supported for driver: {core_config.driver}")

        return loader

    async def get_tables(self, data_source_name: str, schema: Optional[str] = None) -> list[api.TableMetadata]:
        """
        Get list of tables in a data source.

        Args:
            data_source_name: Name of the data source
            schema: Optional schema name (PostgreSQL)

        Returns:
            List of table metadata

        Raises:
            SchemaServiceError: If introspection fails
        """
        cache_key: str = f"tables:{data_source_name}:{schema or 'default'}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            logger.debug(f"Returning cached tables for {data_source_name}")
            return cached

        try:
            # Get data source config
            ds_config: api.DataSourceConfig | None = self.data_source_service.get_data_source(data_source_name)
            if ds_config is None:
                raise SchemaServiceError(f"Data source '{data_source_name}' not found")

            # Resolve environment variables before creating loader
            ds_config = ds_config.resolve_config_env_vars()
            loader: SqlLoader = self.create_loader_for_data_source(ds_config)

            core_tables: dict[str, CoreSchema.TableMetadata] = await loader.get_tables(schema_name=schema)

            # Convert CoreSchema.TableMetadata to API TableMetadata
            tables: list[api.TableMetadata] = [
                api.TableMetadata(name=table.name, schema_name=table.schema, comment=table.comment, row_count=table.row_count)
                for table in core_tables.values()
            ]

            # Cache and return
            self.cache.set(cache_key, tables)
            return tables

        except Exception as e:
            logger.error(f"Error getting tables for {data_source_name}: {e}")
            raise SchemaServiceError(f"Failed to get tables: {str(e)}") from e

    async def get_table_schema(self, data_source_name: str, table_name: str, schema: Optional[str] = None) -> api.TableSchema:
        """
        Get detailed schema for a specific table.

        Args:
            data_source_name: Name of the data source
            table_name: Name of the table
            schema: Optional schema name (PostgreSQL)

        Returns:
            Detailed table schema

        Raises:
            SchemaServiceError: If introspection fails
        """
        cache_key = f"schema:{data_source_name}:{schema or 'default'}:{table_name}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            logger.debug(f"Returning cached schema for {table_name}")
            return cached

        try:
            # Get data source config
            ds_config: api.DataSourceConfig | None = self.data_source_service.get_data_source(data_source_name)
            if ds_config is None:
                raise SchemaServiceError(f"Data source '{data_source_name}' not found")

            # Environment variable resolution happens in the mapper
            loader: SqlLoader = self.create_loader_for_data_source(ds_config)
            core_schema: CoreSchema.TableSchema = await loader.get_table_schema(table_name, schema=schema)
            api_schema: api.TableSchema = TableSchemaMapper.to_api_schema(core_schema)

            # Cache and return
            self.cache.set(cache_key, api_schema)
            return api_schema

        except Exception as e:
            logger.error(f"Error getting schema for {table_name}: {e}")
            raise SchemaServiceError(f"Failed to get table schema: {str(e)}") from e

    async def preview_table_data(
        self,
        data_source_name: str,
        table_name: str,
        schema: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """
        Get preview of table data.

        Args:
            data_source_name: Name of the data source
            table_name: Name of the table
            schema: Optional schema name (PostgreSQL)
            limit: Maximum number of rows (default 50, max 100)
            offset: Number of rows to skip (default 0)

        Returns:
            dict with 'columns' (list of column names) and 'rows' (list of row dicts)

        Raises:
            SchemaServiceError: If preview fails
        """

        limit = min(limit, 100)
        offset = max(offset, 0)

        try:
            ds_config: api.DataSourceConfig | None = self.data_source_service.get_data_source(data_source_name)
            if ds_config is None:
                raise SchemaServiceError(f"Data source '{data_source_name}' not found")

            # Environment variable resolution happens in the mapper
            data_source: CoreDataSourceConfig = DataSourceMapper.to_core_config(ds_config)
            qualified_table: str = f'"{schema}"."{table_name}"' if schema else f'"{table_name}"'
            query: str = f"SELECT * FROM {qualified_table} LIMIT {limit} OFFSET {offset}"
            loader: SqlLoader = DataLoaders.get(data_source.driver)(data_source=data_source)

            data: pd.DataFrame = await asyncio.wait_for(loader.read_sql(query), timeout=30.0)

            if data.empty:
                return {"columns": [], "rows": [], "total_rows": 0, "limit": limit, "offset": offset}

            row_count: int | None = await loader.get_table_row_count(table_name, schema)

            return {
                "columns": data.columns.tolist(),
                "rows": data.to_dict(orient="records"),  # type: ignore
                "total_rows": row_count,
                "limit": limit,
                "offset": offset,
            }

        except asyncio.TimeoutError as e:
            raise SchemaServiceError("Query execution timed out after 30 seconds") from e
        except Exception as e:
            logger.error(f"Error previewing table {table_name}: {e}")
            raise SchemaServiceError(f"Failed to preview table data: {str(e)}") from e

    def invalidate_cache(self, data_source_name: str) -> None:
        """Invalidate all cached data for a data source."""
        # Remove all cache entries starting with data_source_name
        keys_to_remove = [
            key for key in self.cache._cache if key.startswith(f"tables:{data_source_name}") or key.startswith(f"schema:{data_source_name}")
        ]
        for key in keys_to_remove:
            self.cache.invalidate(key)
        logger.info(f"Invalidated {len(keys_to_remove)} cache entries for {data_source_name}")

    async def import_entity_from_table(
        self, data_source_name: str, table_name: str, entity_name: Optional[str] = None, selected_columns: Optional[list[str]] = None
    ) -> dict[str, Any]:
        """
        Generate entity configuration from a database table.

        Args:
            data_source_name: Name of the data source
            table_name: Name of the table to import
            entity_name: Optional custom entity name (defaults to table_name)
            selected_columns: Optional list of columns to include (defaults to all)

        Returns:
            Dictionary with entity configuration
        """

        # Get table schema
        schema = await self.get_table_schema(data_source_name, table_name)

        # Generate entity name (convert to snake_case if not provided)
        if not entity_name:
            entity_name = table_name.lower().replace(" ", "_").replace("-", "_")

        # Determine columns to include
        if selected_columns:
            columns = [col.name for col in schema.columns if col.name in selected_columns]
        else:
            columns = [col.name for col in schema.columns]

        # Generate SQL query
        column_list = ", ".join(f'"{col}"' for col in columns)
        query = f'SELECT {column_list} FROM "{table_name}"'

        # Suggest surrogate ID
        surrogate_id_suggestion = None
        for col in schema.columns:
            if col.is_primary_key:
                # Use primary key as surrogate if it's an integer
                if "int" in col.data_type.lower():
                    surrogate_id_suggestion = KeySuggestion(
                        columns=[col.name], reason=f"Primary key column with integer type ({col.data_type})", confidence=0.95
                    )
                    break

        if not surrogate_id_suggestion:
            # Look for columns ending with _id
            for col in schema.columns:
                if col.name.lower().endswith("_id") and "int" in col.data_type.lower():
                    surrogate_id_suggestion = KeySuggestion(
                        columns=[col.name], reason=f"Column name ends with '_id' and has integer type ({col.data_type})", confidence=0.7
                    )
                    break

        # Suggest natural keys
        natural_key_suggestions = []

        # Look for columns with "code", "name", "number" in the name
        for col in schema.columns:
            col_lower = col.name.lower()
            if any(keyword in col_lower for keyword in ["code", "name", "number", "key"]):
                if not col.nullable or col.is_primary_key:
                    confidence = 0.8 if col.is_primary_key else 0.6
                    natural_key_suggestions.append(
                        KeySuggestion(columns=[col.name], reason=f"Column name suggests identifier ('{col.name}')", confidence=confidence)
                    )

        # Build column types dictionary
        column_types = {col.name: col.data_type for col in schema.columns if col.name in columns}

        return {
            "entity_name": entity_name,
            "type": "sql",
            "data_source": data_source_name,
            "query": query,
            "columns": columns,
            "surrogate_id_suggestion": surrogate_id_suggestion,
            "natural_key_suggestions": natural_key_suggestions[:3],  # Limit to top 3
            "column_types": column_types,
        }
