"""Data source service for managing database connections and file sources."""

import time
from pathlib import Path
from typing import Any, Optional

import pandas as pd
from loguru import logger

from backend.app.mappers.data_source_mapper import DataSourceMapper
from backend.app.models.data_source import DataSourceConfig, DataSourceStatus, DataSourceTestResult
from src.config_model import DataSourceConfig as CoreDataSourceConfig
from src.config_model import TableConfig
from src.configuration.interface import ConfigLike
from src.loaders.base_loader import DataLoader, DataLoaders
from src.loaders.sql_loaders import CoreSchema, SqlLoader
from src.utility import replace_env_vars


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
                if "name" not in config_dict:
                    config_dict["name"] = name
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
        """
        return next((ds for ds in self.list_data_sources() if ds.name == name), None)

    def create_data_source(self, config: DataSourceConfig) -> DataSourceConfig:
        """Create a new data source.

        Args:
            config: Data source configuration

        Returns:
            Created data source configuration

        Raises:
            ValueError: If data source with same name already exists
        """
        existing: DataSourceConfig | None = self.get_data_source(config.name)
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
        existing: DataSourceConfig | None = self.get_data_source(name)
        if not existing:
            raise ValueError(f"Data source '{name}' not found")

        data_sources_dict: dict[str, Any] = self.config.get("options:data_sources") or {}
        if name != config.name:
            del data_sources_dict[name]

        config_dict: dict[str, Any] = config.model_dump(exclude_none=True, exclude={"name"})

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
        existing: DataSourceConfig | None = self.get_data_source(name)
        if not existing:
            raise ValueError(f"Data source '{name}' not found")

        # Check if in use by entities
        entities_using: list[str] = self._get_entities_using_data_source(name)
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
        start_time: float = time.time()

        try:
            if config.is_database_source():
                return await self._test_database_connection(config)
            if config.is_file_source():
                return await self._test_file_connection(config)
            return DataSourceTestResult(
                success=False, message=f"Unsupported data source type: {config.driver}", connection_time_ms=0, metadata={}
            )
        except Exception as e:  # pylint: disable=broad-except
            elapsed_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Connection test failed for '{config.name}': {e}")
            return DataSourceTestResult(success=False, message=f"Connection failed: {str(e)}", connection_time_ms=elapsed_ms, metadata={})

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
            core_ds_cfg: CoreDataSourceConfig = DataSourceMapper().to_core_config(config)
            # Create legacy data source config for loader

            # Get loader and test with simple query
            loader_class: type[DataLoader] | None = DataLoaders.items.get(core_ds_cfg.driver)
            if not loader_class:
                raise ValueError(f"No loader found for driver: {core_ds_cfg.driver}")

            loader: DataLoader = loader_class(data_source=core_ds_cfg)

            # Create mock table config with simple test query
            test_table_cfg = TableConfig(
                cfg={
                    core_ds_cfg.name: {"surrogate_id": "test_id", "keys": [], "columns": [], "source": None, "query": "SELECT 1 as test"}
                },  # Simple test query
                entity_name=core_ds_cfg.name,
            )

            # Try to load (this will test the connection)
            df: pd.DataFrame = await loader.load(entity_name="test", table_cfg=test_table_cfg)

            elapsed_ms = int((time.time() - start_time) * 1000)

            # Get metadata if possible
            metadata = {}
            try:
                if hasattr(loader, "get_tables"):
                    assert isinstance(loader, SqlLoader)
                    tables: dict[str, CoreSchema.TableMetadata] = await loader.get_tables()
                    metadata["table_count"] = len(tables)
            except:  # pylint: disable=bare-except
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
                success=False, message=f"Connection failed: {error_msg}", connection_time_ms=elapsed_ms, metadata={}
            )

    async def _test_file_connection(self, config: DataSourceConfig) -> DataSourceTestResult:
        """Test file-based connection (CSV).

        Args:
            config: CSV data source configuration

        Returns:
            Test result
        """
        start_time: float = time.time()

        try:
            file_path: str | None = config.effective_file_path
            if not file_path:
                raise ValueError("CSV source requires 'filename' or 'file_path'")

            # Check if file exists
            path: Path = Path(file_path)
            if not path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")

            # Try to read first few rows
            read_opts: dict[str, Any] = config.options or {}
            df: pd.DataFrame = pd.read_csv(file_path, nrows=5, **read_opts)

            elapsed_ms: int = int((time.time() - start_time) * 1000)

            metadata: dict[str, Any] = {
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

        except Exception as e:  # pylint: disable=broad-except
            elapsed_ms = int((time.time() - start_time) * 1000)
            return DataSourceTestResult(success=False, message=f"File access failed: {str(e)}", connection_time_ms=elapsed_ms, metadata={})

    def get_status(self, name: str) -> DataSourceStatus:
        """Get current status of a data source.

        Args:
            name: Data source name

        Returns:
            Current status including entities using it
        """
        config: DataSourceConfig | None = self.get_data_source(name)
        if not config:
            raise ValueError(f"Data source '{name}' not found")

        entities_using: list[str] = self._get_entities_using_data_source(name)

        return DataSourceStatus(name=name, is_connected=name in self._connections, in_use_by_entities=entities_using, last_test_result=None)

    def _get_entities_using_data_source(self, data_source_name: str) -> list[str]:
        """Find all entities using a specific data source.

        Args:
            data_source_name: Name of data source

        Returns:
            List of entity names
        """

        return [
            entity_name
            for entity_name, entity_config in (self.config.get("entities") or {}).items()
            if isinstance(entity_config, dict) and entity_config.get("data_source") == data_source_name
        ]

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
