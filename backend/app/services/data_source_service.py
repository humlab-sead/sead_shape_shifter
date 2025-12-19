"""Data source service for managing database connections and file sources."""

import time
from pathlib import Path
from typing import Any, Optional

import yaml
from loguru import logger

from backend.app.mappers.data_source_mapper import DataSourceMapper
from backend.app.models.data_source import DataSourceConfig, DataSourceStatus, DataSourceTestResult
from src.config_model import DataSourceConfig as CoreDataSourceConfig
from src.configuration.interface import ConfigLike
from src.loaders.base_loader import ConnectTestResult, DataLoader, DataLoaders


class DataSourceService:
    """Service for managing data source connections within a configuration."""

    def __init__(self, config: ConfigLike):
        """Initialize the data source service.

        Args:
            config: Application configuration containing data sources
        """
        self.config: ConfigLike = config
        self._connections: dict[str, Any] = {}  # Connection pool (future)

    def _get_raw_data_sources_from_yaml(self) -> dict[str, Any]:
        """Get raw data sources from YAML without env var resolution.

        This method reads data sources configuration directly from the YAML file(s)
        to preserve environment variable references like ${SEAD_HOST}.

        Returns:
            Dictionary of data source configurations with unresolved env vars
        """
        try:
            # Get the main config file path from the config object
            config_path = getattr(self.config, "filename", None) or getattr(self.config, "source", None)

            if not config_path:
                # Fallback to looking in default locations
                possible_paths = [
                    Path("input/arbodat.yml"),
                    Path("input/arbodat-database.yml"),
                    Path("config.yml"),
                ]
                config_path = next((p for p in possible_paths if p.exists()), None)

            if not config_path:
                logger.warning("Could not find config file to read raw data sources")
                return {}

            config_path = Path(config_path)
            if not config_path.exists():
                logger.warning(f"Config file not found: {config_path}")
                return {}

            # Read raw YAML
            with open(config_path, "r", encoding="utf-8") as f:
                raw_config = yaml.safe_load(f)

            if not raw_config or not isinstance(raw_config, dict):
                return {}

            # Extract data sources from options section
            options = raw_config.get("options", {})
            data_sources = options.get("data_sources", {})

            # Handle @include directives by reading referenced files
            resolved_sources = {}
            for name, source_config in data_sources.items():
                if isinstance(source_config, str) and source_config.startswith("@include:"):
                    # Load from included file
                    include_path = source_config.replace("@include:", "").strip()
                    include_file = config_path.parent / include_path
                    if include_file.exists():
                        with open(include_file, "r", encoding="utf-8") as f:
                            resolved_sources[name] = yaml.safe_load(f)
                    else:
                        logger.warning(f"Included file not found: {include_file}")
                else:
                    resolved_sources[name] = source_config

            return resolved_sources

        except Exception as e:
            logger.warning(f"Failed to read raw data sources from YAML: {e}")
            return {}

    def list_data_sources(self) -> list[DataSourceConfig]:
        """List all configured data sources.

        Returns:
            List of data source configurations with unresolved env vars (as they appear in config)

        Note:
            Environment variables are NOT resolved here. They remain as ${VAR_NAME} so that
            the UI can display and edit them. Resolution happens only when testing connections.
        """
        # Try to get raw data sources from YAML first (preserves env vars)
        data_sources_dict = self._get_raw_data_sources_from_yaml()

        # Fallback to config object if YAML reading failed
        if not data_sources_dict:
            data_sources_dict = self.config.get("options:data_sources") or {}

        result: list[DataSourceConfig] = []
        for name, config_dict in data_sources_dict.items():
            if not isinstance(config_dict, dict):
                logger.warning(f"Data source '{name}' config is not a dict, skipping")
                continue
            try:
                if "name" not in config_dict:
                    config_dict["name"] = name
                # Don't resolve env vars - keep them as ${VAR_NAME} for UI editing
                ds_config = DataSourceConfig(**config_dict)
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
            config = config.resolve_config_env_vars()
            core_ds_cfg: CoreDataSourceConfig = DataSourceMapper().to_core_config(config)
            loader: DataLoader = DataLoaders.get(core_ds_cfg.driver)
            result: ConnectTestResult = await loader.test_connection()
            return DataSourceTestResult.from_core_result(result)
        except Exception as e:  # pylint: disable=broad-except
            elapsed_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Connection test failed for '{config.name}': {e}")
            return DataSourceTestResult.create_failure(message=f"Connection failed: {str(e)}", connection_time_ms=elapsed_ms)

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
