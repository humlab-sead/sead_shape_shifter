"""
Schema Introspection Service

Provides database schema introspection capabilities for PostgreSQL and MS Access.
Discovers tables, columns, data types, and relationships.
"""

import asyncio
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import pandas as pd
from loguru import logger

import backend.app.models.data_source as api
from backend.app.exceptions import SchemaIntrospectionError
from backend.app.mappers.data_source_mapper import DataSourceMapper
from backend.app.mappers.table_schema_mapper import TableSchemaMapper
from backend.app.models.entity_import import KeySuggestion
from backend.app.services.data_source_service import DataSourceService
from src.loaders.base_loader import DataLoaders
from src.loaders.sql_loaders import CoreSchema, SqlLoader
from src.model import DataSourceConfig as CoreDataSourceConfig


def safe_str_or_none(value: Any) -> str | None:
    """Convert value to string or None, handling pandas NaN.

    Args:
        value: Value to convert (may be str, None, float NaN, etc.)

    Returns:
        String value or None
    """
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return str(value) if value else None


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

    def exists(self, key: str) -> bool:
        """Check if a valid cache entry exists."""
        return self.get(key) is not None

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

    def compute_hash(self, data_source: str | dict[str, Any]) -> str:
        return str(data_source) if isinstance(data_source, str) else str(hash(frozenset(data_source.items())))

    def compute_key(self, data_source: str | dict[str, Any], prefix: str, suffix: str) -> str:
        return f"{prefix}:{self.compute_hash(data_source)}:{suffix}"

    def invalidate_by_name(self, data_source_name: str) -> None:
        """Invalidate all cached data for a data source."""
        # Remove all cache entries starting with data_source_name
        keys_to_remove: list[str] = [
            key for key in self._cache if key.startswith(f"tables:{data_source_name}") or key.startswith(f"schema:{data_source_name}")
        ]
        for key in keys_to_remove:
            self.invalidate(key)
        logger.info(f"Invalidated {len(keys_to_remove)} cache entries for {data_source_name}")


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
            raise SchemaIntrospectionError(f"Schema introspection not supported for driver: {core_config.driver}")

        loader: SqlLoader = loader_cls(data_source=core_config)

        if not isinstance(loader, SqlLoader):
            raise SchemaIntrospectionError(f"Schema introspection not supported for driver: {core_config.driver}")

        return loader

    async def get_tables(self, data_source: str | dict[str, Any], schema: Optional[str] = None) -> list[api.TableMetadata]:
        """
        Get list of tables in a data source.

        Args:
            data_source: Either a filename/name string or a resolved config dict
            schema: Optional schema name (PostgreSQL)

        Returns:
            List of table metadata

        Raises:
            SchemaIntrospectionError: If introspection fails
        """
        ds_name: str = data_source if isinstance(data_source, str) else data_source.get("name", "unknown")

        hash_key: str = self.cache.compute_key(data_source, "tables", schema or "default")
        if (cached_table := self.cache.get(hash_key)) is not None:
            return cached_table

        try:
            ds_config: api.DataSourceConfig | None = self.data_source_service.load_data_source(data_source)
            if ds_config is None:
                raise SchemaIntrospectionError(message=f"Data source '{ds_name}'not found", data_source=ds_name, operation="get_tables")

            ds_config = ds_config.resolve_config_env_vars()
            loader: SqlLoader = self.create_loader_for_data_source(ds_config)

            core_tables: dict[str, CoreSchema.TableMetadata] = await loader.get_tables(schema_name=schema)

            # Convert core tables to API models, handling pandas NaN in optional fields
            tables: list[api.TableMetadata] = [
                api.TableMetadata(
                    name=table.name, schema_name=table.schema, comment=safe_str_or_none(table.comment), row_count=table.row_count
                )
                for table in core_tables.values()
            ]

            self.cache.set(hash_key, tables)
            return tables

        except SchemaIntrospectionError:
            raise
        except Exception as e:
            logger.error(f"Error getting tables: {e}")
            raise SchemaIntrospectionError(message="Failed to get tables from data source", operation="get_tables") from e

    async def get_table_schema(self, data_source: str | dict[str, Any], table_name: str, schema: Optional[str] = None) -> api.TableSchema:
        """
        Get detailed schema for a specific table.

        Args:
            data_source: Either a filename/name string or a resolved config dict
            table_name: Name of the table
            schema: Optional schema name (PostgreSQL)

        Returns:
            Detailed table schema

        Raises:
            SchemaIntrospectionError: If introspection fails
        """
        ds_name: str = data_source if isinstance(data_source, str) else data_source.get("name", "unknown")

        hash_key: str = self.cache.compute_key(data_source, "schema", f"{schema or 'default'}:{table_name}")
        if (cached_schema := self.cache.get(hash_key)) is not None:
            return cached_schema

        try:
            ds_config: api.DataSourceConfig | None = self.data_source_service.load_data_source(data_source)
            if ds_config is None:
                raise SchemaIntrospectionError(message=f"Data source '{ds_name}' not found", data_source=ds_name, operation="get_columns")

            loader: SqlLoader = self.create_loader_for_data_source(ds_config)
            core_schema: CoreSchema.TableSchema = await loader.get_table_schema(table_name, schema=schema)
            api_schema: api.TableSchema = TableSchemaMapper.to_api_schema(core_schema)

            self.cache.set(hash_key, api_schema)
            return api_schema

        except SchemaIntrospectionError:
            raise
        except Exception as e:
            logger.error(f"Error getting schema for {table_name}: {e}")
            ds_name = data_source if isinstance(data_source, str) else data_source.get("name", "unknown")
            raise SchemaIntrospectionError(
                message=f"Failed to get schema for table '{table_name}'", data_source=ds_name, operation="get_columns"
            ) from e

    async def preview_table_data(
        self,
        data_source_cfg: str | dict[str, Any],
        table_name: str,
        schema: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """
        Get preview of table data.

        Args:
            data_source_cfg: Either a filename/name string or a resolved config dict
            table_name: Name of the table
            schema: Optional schema name (PostgreSQL)
            limit: Maximum number of rows (default 50, max 100)
            offset: Number of rows to skip (default 0)

        Returns:
            dict with 'columns' (list of column names) and 'rows' (list of row dicts)

        Raises:
            SchemaIntrospectionError: If preview fails
        """

        limit = min(limit, 100)
        offset = max(offset, 0)

        ds_name: str = data_source_cfg if isinstance(data_source_cfg, str) else data_source_cfg.get("name", "unknown")

        try:
            ds_config: api.DataSourceConfig | None = self.data_source_service.load_data_source(data_source_cfg)
            if ds_config is None:
                raise SchemaIntrospectionError(message=f"Data source '{ds_name}' not found", data_source=ds_name, operation="preview_table")

            data_source: CoreDataSourceConfig = DataSourceMapper.to_core_config(ds_config)

            loader: SqlLoader = DataLoaders.get(data_source.driver)(data_source=data_source)

            # qualified_table: str = loader.qualify_name(schema=schema, table=table_name)  # --- IGNORE ---
            data: pd.DataFrame = await asyncio.wait_for(loader.load_table(table_name=table_name, limit=limit, offset=offset), timeout=30.0)

            if data.empty:
                return {"columns": [], "rows": [], "total_rows": 0, "limit": limit, "offset": offset}

            row_count: int | None = await loader.get_table_row_count(table_name, schema)

            return {
                "columns": data.columns.tolist(),
                "rows": data.to_dict(orient="records"),  # type: ignore
                "total_rows": row_count or 0,  # Use 0 if row count unavailable
                "limit": limit,
                "offset": offset,
            }

        except asyncio.TimeoutError as e:
            raise SchemaIntrospectionError(
                message="Query execution timed out after 30 seconds", data_source=ds_name, operation="preview_table"
            ) from e
        except Exception as e:
            logger.error(f"Error previewing table {table_name}: {e}")
            raise SchemaIntrospectionError(
                message=f"Failed to preview table data: {str(e)}", data_source=ds_name, operation="preview_table"
            ) from e

    def invalidate_cache(self, data_source_name: str) -> None:
        """Invalidate all cached data for a data source."""
        self.cache.invalidate_by_name(data_source_name)

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
        schema: api.TableSchema = await self.get_table_schema(data_source_name, table_name)

        # Generate entity name (convert to snake_case if not provided)
        if not entity_name:
            entity_name = table_name.lower().replace(" ", "_").replace("-", "_")

        # Determine columns to include
        if selected_columns:
            columns: list[str] = [col.name for col in schema.columns if col.name in selected_columns]
        else:
            columns = [col.name for col in schema.columns]

        query: str = f'SELECT {", ".join(f'"{col}"' for col in columns)} FROM {table_name}'

        public_id_suggestion: KeySuggestion | None = None
        for col in schema.columns:
            if col.is_primary_key:
                # Use primary key as surrogate if it's an integer
                if "int" in col.data_type.lower():
                    public_id_suggestion = KeySuggestion(
                        columns=[col.name], reason=f"Primary key column with integer type ({col.data_type})", confidence=0.95
                    )
                    break

        if not public_id_suggestion:
            # Look for columns ending with _id
            for col in schema.columns:
                if col.name.lower().endswith("_id") and "int" in col.data_type.lower():
                    public_id_suggestion = KeySuggestion(
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
        column_types: dict[str, str] = {col.name: col.data_type for col in schema.columns if col.name in columns}

        return {
            "entity_name": entity_name,
            "type": "sql",
            "data_source": data_source_name,
            "query": query,
            "columns": columns,
            "public_id_suggestion": public_id_suggestion,
            "natural_key_suggestions": natural_key_suggestions[:3],  # Limit to top 3
            "column_types": column_types,
        }
