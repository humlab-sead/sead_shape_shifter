"""Data source service for managing database connections and file sources."""

import time
from pathlib import Path
from typing import Any, Optional

import pandas as pd
from loguru import logger
from src.config_model import DataSourceConfig as LegacyDataSourceConfig
from src.config_model import TableConfig
from src.configuration.interface import ConfigLike
from src.loaders.base_loader import DataLoader, DataLoaders
from src.utility import replace_env_vars

from app.models.data_source import (
    DataSourceConfig,
    DataSourceStatus,
    DataSourceTestResult,
    DataSourceType,
)


class DataSourceService:
    """Service for managing data source connections.

    This service provides:
    - CRUD operations for data source configurations
    - Connection testing
    - Connection pooling (future)
    - Integration with existing loader system
    """

    def __init__(self, config: ConfigLike):
        """Initialize the data source service.

        Args:
            config: Application configuration containing data sources
        """
        self.config = config
        self._connections: dict[str, Any] = {}  # Connection pool (future)

    def list_data_sources(self) -> list[DataSourceConfig]:
        """List all configured data sources.

        Returns:
            List of data source configurations
        """
        data_sources_dict: dict[str, Any] = self.config.get("options:data_sources") or {}

        result: list[DataSourceConfig] = []
        for name, config_dict in data_sources_dict.items():
            if not isinstance(config_dict, dict):
                logger.warning(f"Data source '{name}' config is not a dict, skipping")
                continue

            try:
                # Add name to config if not present
                if "name" not in config_dict:
                    config_dict["name"] = name

                # Resolve environment variables
                resolved_config = self._resolve_env_vars(config_dict)

                ds_config = DataSourceConfig(**resolved_config)
                result.append(ds_config)
            except Exception as e:  # pylint: disable=broad-except
                logger.warning(f"Failed to parse data source '{name}': {e}")
                continue

        return result

    def get_data_source(self, name: str) -> Optional[DataSourceConfig]:
        """Get a specific data source configuration.

        Args:
            name: Data source name

        Returns:
            Data source configuration or None if not found
        """
        data_sources = self.list_data_sources()
        for ds in data_sources:
            if ds.name == name:
                return ds
        return None

    def create_data_source(self, config: DataSourceConfig) -> DataSourceConfig:
        """Create a new data source.

        Args:
            config: Data source configuration

        Returns:
            Created data source configuration

        Raises:
            ValueError: If data source with same name already exists
        """
        existing = self.get_data_source(config.name)
        if existing:
            raise ValueError(f"Data source '{config.name}' already exists")

        # Add to config
        data_sources_dict: dict[str, Any] = self.config.get("options:data_sources") or {}
        config_dict = config.model_dump(exclude_none=True, exclude={"name"})

        # Handle SecretStr password
        if config.password:
            config_dict["password"] = config.password.get_secret_value()

        data_sources_dict[config.name] = config_dict
        self.config.update({"options:data_sources": data_sources_dict})

        logger.info(f"Created data source '{config.name}' (driver: {config.driver})")
        return config

    def update_data_source(self, name: str, config: DataSourceConfig) -> DataSourceConfig:
        """Update an existing data source.

        Args:
            name: Current data source name
            config: New configuration

        Returns:
            Updated data source configuration

        Raises:
            ValueError: If data source doesn't exist
        """
        existing = self.get_data_source(name)
        if not existing:
            raise ValueError(f"Data source '{name}' not found")

        # Remove old config if name changed
        data_sources_dict: dict[str, Any] = self.config.get("options:data_sources") or {}
        if name != config.name:
            del data_sources_dict[name]

        # Add updated config
        config_dict = config.model_dump(exclude_none=True, exclude={"name"})

        # Handle SecretStr password
        if config.password:
            config_dict["password"] = config.password.get_secret_value()

        data_sources_dict[config.name] = config_dict
        self.config.update({"options:data_sources": data_sources_dict})

        logger.info(f"Updated data source '{name}' -> '{config.name}'")
        return config

    def delete_data_source(self, name: str) -> None:
        """Delete a data source.

        Args:
            name: Data source name

        Raises:
            ValueError: If data source doesn't exist or is in use
        """
        existing = self.get_data_source(name)
        if not existing:
            raise ValueError(f"Data source '{name}' not found")

        # Check if in use by entities
        entities_using = self._get_entities_using_data_source(name)
        if entities_using:
            raise ValueError(f"Cannot delete data source '{name}': in use by entities: {', '.join(entities_using)}")

        # Remove from config
        data_sources_dict: dict[str, Any] = self.config.get("options:data_sources") or {}
        del data_sources_dict[name]
        self.config.update({"options:data_sources": data_sources_dict})

        logger.info(f"Deleted data source '{name}'")

    async def test_connection(self, config: DataSourceConfig) -> DataSourceTestResult:
        """Test a data source connection.

        Args:
            config: Data source configuration to test

        Returns:
            Test result with success/failure and timing
        """
        start_time = time.time()

        try:
            if config.is_database_source():
                result = await self._test_database_connection(config)
            elif config.is_file_source():
                result = await self._test_file_connection(config)
            else:
                result = DataSourceTestResult(
                    success=False,
                    message=f"Unsupported data source type: {config.driver}",
                    connection_time_ms=0,
                )
        except Exception as e:  # pylint: disable=broad-except
            elapsed_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Connection test failed for '{config.name}': {e}")
            result = DataSourceTestResult(
                success=False,
                message=f"Connection failed: {str(e)}",
                connection_time_ms=elapsed_ms,
            )

        return result

    async def _test_database_connection(self, config: DataSourceConfig) -> DataSourceTestResult:
        """Test database connection by attempting to load a simple query.

        Args:
            config: Database data source configuration

        Returns:
            Test result
        """
        start_time = time.time()

        try:
            # Create a mock TableConfig for testing

            # Create legacy data source config for loader
            legacy_opts = {
                "driver": config.get_loader_driver(),
            }

            if config.driver in (DataSourceType.POSTGRESQL, DataSourceType.POSTGRES):
                legacy_opts.update(
                    {
                        "host": config.host or "localhost",
                        "port": config.port or 5432,
                        "dbname": config.effective_database,
                        "username": config.username,
                    }
                )
                if config.password:
                    legacy_opts["password"] = config.password.get_secret_value()

            elif config.driver in (DataSourceType.ACCESS, DataSourceType.UCANACCESS):
                if not config.effective_file_path:
                    raise ValueError("Access database requires 'filename' or 'file_path'")
                legacy_opts["filename"] = config.effective_file_path
                if config.options and "ucanaccess_dir" in config.options:
                    legacy_opts["ucanaccess_dir"] = config.options["ucanaccess_dir"]

            elif config.driver == DataSourceType.SQLITE:
                if not config.effective_file_path:
                    raise ValueError("SQLite database requires 'filename' or 'file_path'")
                legacy_opts["filename"] = config.effective_file_path

            # Merge with additional options
            if config.options:
                legacy_opts.update(config.options)

            legacy_data_source = LegacyDataSourceConfig(
                driver=legacy_opts.pop("driver"),
                options=legacy_opts,
            )

            # Get loader and test with simple query
            loader_class = DataLoaders.items.get(legacy_data_source.driver)
            if not loader_class:
                raise ValueError(f"No loader found for driver: {legacy_data_source.driver}")

            loader: DataLoader = loader_class(data_source=legacy_data_source)

            # Create mock table config with simple test query
            test_table_cfg = TableConfig(
                surrogate_id="test_id",
                keys=[],
                columns=[],
                source=None,
                query="SELECT 1 as test",  # Simple test query
            )

            # Try to load (this will test the connection)
            df = await loader.load(entity_name="test", table_cfg=test_table_cfg)

            elapsed_ms = int((time.time() - start_time) * 1000)

            # Get metadata if possible
            metadata = {}
            try:
                if hasattr(loader, "get_tables"):
                    tables = await loader.get_tables()
                    metadata["table_count"] = len(tables)
            except:
                pass

            return DataSourceTestResult(
                success=True,
                message=f"Connected successfully (returned {len(df)} rows)",
                connection_time_ms=elapsed_ms,
                metadata=metadata if metadata else None,
            )

        except Exception as e:  # pylint: disable=broad-except
            elapsed_ms = int((time.time() - start_time) * 1000)
            # Sanitize error message (don't expose passwords, etc.)
            error_msg = str(e)
            if config.password:
                error_msg = error_msg.replace(config.password.get_secret_value(), "***")

            return DataSourceTestResult(
                success=False,
                message=f"Connection failed: {error_msg}",
                connection_time_ms=elapsed_ms,
            )

    async def _test_file_connection(self, config: DataSourceConfig) -> DataSourceTestResult:
        """Test file-based connection (CSV).

        Args:
            config: CSV data source configuration

        Returns:
            Test result
        """
        start_time = time.time()

        try:
            file_path = config.effective_file_path
            if not file_path:
                raise ValueError("CSV source requires 'filename' or 'file_path'")

            # Check if file exists
            path = Path(file_path)
            if not path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")

            # Try to read first few rows
            read_opts = config.options or {}
            df = pd.read_csv(file_path, nrows=5, **read_opts)

            elapsed_ms = int((time.time() - start_time) * 1000)

            metadata = {
                "file_size_bytes": path.stat().st_size,
                "columns": list(df.columns),
                "column_count": len(df.columns),
            }

            return DataSourceTestResult(
                success=True,
                message=f"File accessible ({len(df.columns)} columns detected)",
                connection_time_ms=elapsed_ms,
                metadata=metadata,
            )

        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            return DataSourceTestResult(
                success=False,
                message=f"File access failed: {str(e)}",
                connection_time_ms=elapsed_ms,
            )

    def get_status(self, name: str) -> DataSourceStatus:
        """Get current status of a data source.

        Args:
            name: Data source name

        Returns:
            Current status including entities using it
        """
        config = self.get_data_source(name)
        if not config:
            raise ValueError(f"Data source '{name}' not found")

        entities_using = self._get_entities_using_data_source(name)

        return DataSourceStatus(
            name=name,
            is_connected=name in self._connections,
            in_use_by_entities=entities_using,
        )

    def _get_entities_using_data_source(self, data_source_name: str) -> list[str]:
        """Find all entities using a specific data source.

        Args:
            data_source_name: Name of data source

        Returns:
            List of entity names
        """
        entities_dict: dict[str, Any] = self.config.get("entities") or {}
        using_entities: list[str] = []

        for entity_name, entity_config in entities_dict.items():
            if not isinstance(entity_config, dict):
                continue

            # Check if entity uses this data source
            entity_data_source = entity_config.get("data_source")
            if entity_data_source == data_source_name:
                using_entities.append(entity_name)

        return using_entities

    def _resolve_env_vars(self, config_dict: dict[str, Any]) -> dict[str, Any]:
        """Resolve environment variables in configuration.

        Args:
            config_dict: Configuration dictionary

        Returns:
            Dictionary with env vars resolved
        """
        resolved = {}
        for key, value in config_dict.items():
            if isinstance(value, str):
                resolved[key] = replace_env_vars(value)
            elif isinstance(value, dict):
                resolved[key] = self._resolve_env_vars(value)
            else:
                resolved[key] = value
        return resolved
