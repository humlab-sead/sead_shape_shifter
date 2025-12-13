"""
Schema Introspection Service

Provides database schema introspection capabilities for PostgreSQL and MS Access.
Discovers tables, columns, data types, and relationships.
"""

import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from loguru import logger
import pandas as pd

from src.configuration.interface import ConfigLike
from src.loaders.base_loader import DataLoaders
from app.models.data_source import (
    TableMetadata,
    ColumnMetadata,
    TableSchema,
    ForeignKeyMetadata,
    DataSourceConfig,
)
from app.services.data_source_service import DataSourceService


class SchemaServiceError(Exception):
    """Base exception for schema service errors."""


class SchemaCache:
    """Simple in-memory cache for schema data."""

    def __init__(self, ttl_seconds: int = 300):
        self._cache: Dict[str, tuple[Any, datetime]] = {}
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

    def __init__(self, config: ConfigLike):
        self.config = config
        self.data_source_service = DataSourceService(config)
        self.cache = SchemaCache(ttl_seconds=300)  # 5 minute cache

    async def get_tables(
        self, data_source_name: str, schema: Optional[str] = None
    ) -> List[TableMetadata]:
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
        cache_key = f"tables:{data_source_name}:{schema or 'default'}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            logger.debug(f"Returning cached tables for {data_source_name}")
            return cached

        try:
            # Get data source config
            ds_config = self.data_source_service.get_data_source(data_source_name)
            if ds_config is None:
                raise SchemaServiceError(f"Data source '{data_source_name}' not found")

            # Route to appropriate introspection method
            driver = ds_config.driver.lower()
            if driver in ('postgresql', 'postgres'):
                tables = await self._get_postgresql_tables(ds_config, schema)
            elif driver in ('access', 'ucanaccess'):
                tables = await self._get_access_tables(ds_config)
            elif driver == 'sqlite':
                tables = await self._get_sqlite_tables(ds_config)
            else:
                raise SchemaServiceError(f"Schema introspection not supported for driver: {driver}")

            # Cache and return
            self.cache.set(cache_key, tables)
            return tables

        except Exception as e:
            logger.error(f"Error getting tables for {data_source_name}: {e}")
            raise SchemaServiceError(f"Failed to get tables: {str(e)}")

    async def get_table_schema(
        self, data_source_name: str, table_name: str, schema: Optional[str] = None
    ) -> TableSchema:
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
            ds_config = self.data_source_service.get_data_source(data_source_name)
            if ds_config is None:
                raise SchemaServiceError(f"Data source '{data_source_name}' not found")

            # Route to appropriate introspection method
            driver = ds_config.driver.lower()
            if driver in ('postgresql', 'postgres'):
                table_schema = await self._get_postgresql_table_schema(ds_config, table_name, schema)
            elif driver in ('access', 'ucanaccess'):
                table_schema = await self._get_access_table_schema(ds_config, table_name)
            elif driver == 'sqlite':
                table_schema = await self._get_sqlite_table_schema(ds_config, table_name)
            else:
                raise SchemaServiceError(f"Schema introspection not supported for driver: {driver}")

            # Cache and return
            self.cache.set(cache_key, table_schema)
            return table_schema

        except Exception as e:
            logger.error(f"Error getting schema for {table_name}: {e}")
            raise SchemaServiceError(f"Failed to get table schema: {str(e)}")

    async def preview_table_data(
        self,
        data_source_name: str,
        table_name: str,
        schema: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Get preview of table data.

        Args:
            data_source_name: Name of the data source
            table_name: Name of the table
            schema: Optional schema name (PostgreSQL)
            limit: Maximum number of rows (default 50, max 100)
            offset: Number of rows to skip (default 0)

        Returns:
            Dict with 'columns' (list of column names) and 'rows' (list of row dicts)

        Raises:
            SchemaServiceError: If preview fails
        """
        # Limit constraints
        limit = min(limit, 100)
        offset = max(offset, 0)

        try:
            # Get data source config
            ds_config = self.data_source_service.get_data_source(data_source_name)
            if ds_config is None:
                raise SchemaServiceError(f"Data source '{data_source_name}' not found")

            # Build qualified table name
            if schema and ds_config.driver.lower() in ('postgresql', 'postgres'):
                qualified_table = f'"{schema}"."{table_name}"'
            else:
                qualified_table = f'"{table_name}"'

            # Build query
            query = f"SELECT * FROM {qualified_table} LIMIT {limit} OFFSET {offset}"

            # Execute query using loader
            data = await self._execute_query(ds_config, query)

            if data.empty:
                return {
                    "columns": [],
                    "rows": [],
                    "total_rows": 0,
                    "limit": limit,
                    "offset": offset,
                }

            # Convert to response format
            columns = data.columns.tolist()
            rows = data.to_dict(orient='records')

            # Get approximate row count (cached if possible)
            row_count = await self._get_table_row_count(ds_config, table_name, schema)

            return {
                "columns": columns,
                "rows": rows,
                "total_rows": row_count,
                "limit": limit,
                "offset": offset,
            }

        except Exception as e:
            logger.error(f"Error previewing table {table_name}: {e}")
            raise SchemaServiceError(f"Failed to preview table data: {str(e)}")

    async def _get_postgresql_tables(
        self, ds_config: DataSourceConfig, schema: Optional[str] = None
    ) -> List[TableMetadata]:
        """Get tables from PostgreSQL database."""
        schema_filter = schema or 'public'

        query = f"""
            SELECT 
                table_name,
                table_schema as schema,
                obj_description((quote_ident(table_schema) || '.' || quote_ident(table_name))::regclass) as comment
            FROM information_schema.tables
            WHERE table_schema = '{schema_filter}'
                AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """

        data = await self._execute_query(ds_config, query)

        tables = []
        for _, row in data.iterrows():
            tables.append(
                TableMetadata(
                    name=row['table_name'],
                    schema=row['schema'],
                    comment=row.get('comment'),
                )
            )

        return tables

    async def _get_postgresql_table_schema(
        self, ds_config: DataSourceConfig, table_name: str, schema: Optional[str] = None
    ) -> TableSchema:
        """Get detailed schema for PostgreSQL table."""
        schema_filter = schema or 'public'

        # Get columns
        columns_query = f"""
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default,
                character_maximum_length
            FROM information_schema.columns
            WHERE table_schema = '{schema_filter}'
                AND table_name = '{table_name}'
            ORDER BY ordinal_position
        """

        columns_data = await self._execute_query(ds_config, columns_query)

        # Get primary keys
        pk_query = f"""
            SELECT a.attname as column_name
            FROM pg_index i
            JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
            WHERE i.indrelid = (
                SELECT oid FROM pg_class 
                WHERE relname = '{table_name}' 
                AND relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = '{schema_filter}')
            )
            AND i.indisprimary
        """

        pk_data = await self._execute_query(ds_config, pk_query)
        primary_keys = pk_data['column_name'].tolist() if not pk_data.empty else []

        # Build columns list
        columns = []
        for _, row in columns_data.iterrows():
            max_length = row.get('character_maximum_length')
            # Convert pandas NaN to None for Pydantic
            if pd.isna(max_length):
                max_length = None
            
            columns.append(
                ColumnMetadata(
                    name=row['column_name'],
                    data_type=row['data_type'],
                    nullable=row['is_nullable'] == 'YES',
                    default=row.get('column_default'),
                    is_primary_key=row['column_name'] in primary_keys,
                    max_length=max_length,
                )
            )

        # Get row count
        row_count = await self._get_table_row_count(ds_config, table_name, schema)

        return TableSchema(
            table_name=table_name,
            columns=columns,
            primary_keys=primary_keys,
            row_count=row_count,
        )

    async def _get_access_tables(self, ds_config: DataSourceConfig) -> List[TableMetadata]:
        """Get tables from MS Access database."""
        # UCanAccess doesn't provide standard information_schema
        # Use JDBC metadata instead
        query = """
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_TYPE = 'TABLE'
            ORDER BY TABLE_NAME
        """

        try:
            data = await self._execute_query(ds_config, query)
        except Exception:
            # Fallback: try to get from system tables
            logger.warning("Standard query failed, using fallback method for Access")
            query = "SELECT Name as TABLE_NAME FROM MSysObjects WHERE Type = 1 AND Flags = 0 ORDER BY Name"
            data = await self._execute_query(ds_config, query)

        tables = []
        for _, row in data.iterrows():
            tables.append(
                TableMetadata(
                    name=row['TABLE_NAME'],
                    schema=None,
                    comment=None,
                )
            )

        return tables

    async def _get_access_table_schema(
        self, ds_config: DataSourceConfig, table_name: str
    ) -> TableSchema:
        """Get detailed schema for MS Access table."""
        # Get columns using information schema
        columns_query = f"""
            SELECT 
                COLUMN_NAME,
                DATA_TYPE,
                IS_NULLABLE,
                COLUMN_DEFAULT,
                CHARACTER_MAXIMUM_LENGTH
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = '{table_name}'
            ORDER BY ORDINAL_POSITION
        """

        columns_data = await self._execute_query(ds_config, columns_query)

        # Get primary keys
        # UCanAccess may not support this reliably, so we try
        try:
            pk_query = f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE WHERE TABLE_NAME = '{table_name}'"
            pk_data = await self._execute_query(ds_config, pk_query)
            primary_keys = pk_data['COLUMN_NAME'].tolist() if not pk_data.empty else []
        except Exception:
            logger.warning(f"Could not determine primary keys for {table_name}")
            primary_keys = []

        # Build columns list
        columns = []
        for _, row in columns_data.iterrows():
            columns.append(
                ColumnMetadata(
                    name=row['COLUMN_NAME'],
                    data_type=row['DATA_TYPE'],
                    nullable=row['IS_NULLABLE'] == 'YES',
                    default=row.get('COLUMN_DEFAULT'),
                    is_primary_key=row['COLUMN_NAME'] in primary_keys,
                    max_length=row.get('CHARACTER_MAXIMUM_LENGTH'),
                )
            )

        # Get row count
        row_count = await self._get_table_row_count(ds_config, table_name, None)

        return TableSchema(
            table_name=table_name,
            columns=columns,
            primary_keys=primary_keys,
            row_count=row_count,
        )

    async def _get_sqlite_tables(self, ds_config: DataSourceConfig) -> List[TableMetadata]:
        """Get tables from SQLite database."""
        query = """
            SELECT name as table_name
            FROM sqlite_master
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """

        data = await self._execute_query(ds_config, query)

        tables = []
        for _, row in data.iterrows():
            tables.append(
                TableMetadata(
                    name=row['table_name'],
                    schema=None,
                    comment=None,
                )
            )

        return tables

    async def _get_sqlite_table_schema(
        self, ds_config: DataSourceConfig, table_name: str
    ) -> TableSchema:
        """Get detailed schema for SQLite table."""
        # Get columns using PRAGMA
        columns_query = f"PRAGMA table_info({table_name})"

        columns_data = await self._execute_query(ds_config, columns_query)

        # Build columns and primary keys
        columns = []
        primary_keys = []

        for _, row in columns_data.iterrows():
            is_pk = row['pk'] > 0
            if is_pk:
                primary_keys.append(row['name'])

            columns.append(
                ColumnMetadata(
                    name=row['name'],
                    data_type=row['type'],
                    nullable=row['notnull'] == 0,
                    default=row.get('dflt_value'),
                    is_primary_key=is_pk,
                    max_length=None,
                )
            )

        # Get row count
        row_count = await self._get_table_row_count(ds_config, table_name, None)

        return TableSchema(
            table_name=table_name,
            columns=columns,
            primary_keys=primary_keys,
            row_count=row_count,
        )

    async def _get_table_row_count(
        self, ds_config: DataSourceConfig, table_name: str, schema: Optional[str] = None
    ) -> Optional[int]:
        """Get approximate row count for a table."""
        try:
            # Build qualified table name
            if schema and ds_config.driver.lower() in ('postgresql', 'postgres'):
                qualified_table = f'"{schema}"."{table_name}"'
            else:
                qualified_table = f'"{table_name}"'

            query = f"SELECT COUNT(*) as count FROM {qualified_table}"
            data = await self._execute_query(ds_config, query)

            if not data.empty:
                return int(data.iloc[0]['count'])
        except Exception as e:
            logger.warning(f"Could not get row count for {table_name}: {e}")

        return None

    async def _execute_query(self, ds_config: DataSourceConfig, query: str):
        """Execute a query using the appropriate data loader."""
        # Import here to avoid circular dependency
        from src.config_model import DataSourceConfig as LegacyDataSourceConfig

        # Convert to legacy config
        legacy_config = LegacyDataSourceConfig(
            driver=ds_config.get_loader_driver(),
            host=ds_config.host,
            port=ds_config.port,
            database=ds_config.effective_database,
            username=ds_config.username,
            password=ds_config.password.get_secret_value() if ds_config.password else None,
            filename=ds_config.effective_file_path,
            options=ds_config.options,
        )

        # Get appropriate loader
        loader = DataLoaders.get(legacy_config.driver, legacy_config)

        # Execute query with timeout
        try:
            data = await asyncio.wait_for(loader.load(query=query), timeout=30.0)
            return data
        except asyncio.TimeoutError:
            raise SchemaServiceError("Query execution timed out after 30 seconds")
        except Exception as e:
            raise SchemaServiceError(f"Query execution failed: {str(e)}")

    def invalidate_cache(self, data_source_name: str) -> None:
        """Invalidate all cached data for a data source."""
        # Remove all cache entries starting with data_source_name
        keys_to_remove = [key for key in self.cache._cache.keys() if key.startswith(f"tables:{data_source_name}") or key.startswith(f"schema:{data_source_name}")]
        for key in keys_to_remove:
            self.cache.invalidate(key)
        logger.info(f"Invalidated {len(keys_to_remove)} cache entries for {data_source_name}")
