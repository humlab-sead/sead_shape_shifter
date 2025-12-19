"""Data source service for managing database connections and file sources."""

import time
from pathlib import Path
from typing import Any, Optional

import yaml
from loguru import logger

from backend.app.core.config import settings
from backend.app.mappers.data_source_mapper import DataSourceMapper
from backend.app.models.data_source import DataSourceConfig, DataSourceStatus, DataSourceTestResult
from src.config_model import DataSourceConfig as CoreDataSourceConfig
from src.loaders.base_loader import ConnectTestResult, DataLoader, DataLoaders


class DataSourceService:
    """
    Service for managing global data source files.

    Data sources are stored as separate YAML files in the input/ directory
    (e.g., sead-options.yml, arbodat-data-options.yml) and referenced by
    configurations using @include directives.
    """

    def __init__(self):
        """Initialize the data source service."""
        self.data_sources_dir: Path = settings.CONFIGURATIONS_DIR  # Same as input/
        self._connections: dict[str, Any] = {}  # Connection pool (future)

    def _list_data_source_files(self) -> list[Path]:
        """List all data source YAML files in the input directory.

        Looks for files matching patterns like *-options.yml, *-datasource.yml, etc.

        Returns:
            List of data source file paths
        """
        if not self.data_sources_dir.exists():
            return []

        # Look for data source files (exclude main configuration files)
        # TODO: Consider making patterns configurable, or to probe content for "driver" key
        patterns = ["*-options.yml", "*-datasource.yml", "*-source.yml"]
        files = []
        for pattern in patterns:
            files.extend(self.data_sources_dir.glob(pattern))

        return sorted(files)

    def _read_data_source_file(self, file_path: Path) -> dict[str, Any]:
        """Read a data source file preserving environment variables.

        Args:
            file_path: Path to data source YAML file

        Returns:
            Data source configuration dict with unresolved env vars
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if not isinstance(data, dict):
                logger.warning(f"Data source file {file_path} is not a dict")
                return {}

            return data
        except Exception as e:  # pylint: disable=broad-except
            logger.error(f"Failed to read data source file {file_path}: {e}")
            return {}

    def _write_data_source_file(self, file_path: Path, data: dict[str, Any]) -> None:
        """Write data source configuration to file.

        Args:
            file_path: Path to data source YAML file
            data: Data source configuration dict
        """
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            logger.debug(f"Wrote data source file: {file_path}")
        except Exception as e:  # pylint: disable=broad-except
            logger.error(f"Failed to write data source file {file_path}: {e}")
            raise

    def list_data_sources(self) -> list[DataSourceConfig]:
        """List all global data source files.

        Returns:
            List of data source configurations with unresolved env vars

        Note:
            Data sources are loaded from separate YAML files in input/ directory.
            The filename (without extension) serves as the file identifier.
            Environment variables remain as ${VAR_NAME} for UI editing.
        """
        result: list[DataSourceConfig] = []

        for file_path in self._list_data_source_files():
            try:
                data = self._read_data_source_file(file_path)
                if not data:
                    continue

                # Use filename (without extension) as the identifier
                filename: str = file_path.stem  # e.g., "sead-options"

                # Add filename to config for reference
                data["filename"] = file_path.name

                # Create DataSourceConfig (name will be assigned when connecting to config)
                ds_config = DataSourceConfig(name=filename, **data)
                result.append(ds_config)

            except Exception as e:  # pylint: disable=broad-except
                logger.warning(f"Failed to load data source from {file_path}: {e}")
                continue

        return result

    def get_data_source(self, filename: str) -> Optional[DataSourceConfig]:
        """Get a specific data source by filename.

        Args:
            filename: Data source filename (with or without .yml extension)

        Returns:
            Data source configuration or None if not found
        """
        # Normalize filename
        if not filename.endswith(".yml"):
            filename = f"{filename}.yml"

        file_path = self.data_sources_dir / filename
        if not file_path.exists():
            return None

        try:
            data = self._read_data_source_file(file_path)
            if not data:
                return None

            data["filename"] = file_path.name
            return DataSourceConfig(name=file_path.stem, **data)
        except Exception as e:  # pylint: disable=broad-except
            logger.error(f"Failed to get data source {filename}: {e}")
            return None

    def create_data_source(self, filename: str, config: DataSourceConfig) -> DataSourceConfig:
        """Create a new global data source file.

        Args:
            filename: Filename for the data source (e.g., "my-database-options.yml")
            config: Data source configuration

        Returns:
            Created data source configuration

        Raises:
            ValueError: If data source file already exists
        """
        # Normalize filename
        if not filename.endswith(".yml"):
            filename = f"{filename}.yml"

        file_path = self.data_sources_dir / filename

        if file_path.exists():
            raise ValueError(f"Data source file '{filename}' already exists")

        # Prepare config dict (exclude name and filename - those are external)
        config_dict = config.model_dump(exclude_none=True, exclude={"name", "filename"})

        # Handle SecretStr password
        if config.password:
            config_dict["password"] = config.password.get_secret_value()

        # Write to file
        self._write_data_source_file(file_path, config_dict)

        logger.info(f"Created data source file '{filename}' (driver: {config.driver})")

        # Return with filename set
        result = config.model_copy()
        result.filename = filename
        result.name = file_path.stem
        return result

    def update_data_source(self, filename: str, config: DataSourceConfig) -> DataSourceConfig:
        """Update an existing data source file.

        Args:
            filename: Current filename (with or without .yml)
            config: New configuration

        Returns:
            Updated data source configuration

        Raises:
            ValueError: If data source file not found
        """
        # Normalize filename
        if not filename.endswith(".yml"):
            filename = f"{filename}.yml"

        file_path = self.data_sources_dir / filename

        if not file_path.exists():
            raise ValueError(f"Data source file '{filename}' not found")

        # Prepare config dict
        config_dict = config.model_dump(exclude_none=True, exclude={"name", "filename"})

        # Handle SecretStr password
        if config.password:
            config_dict["password"] = config.password.get_secret_value()

        # Write to file
        self._write_data_source_file(file_path, config_dict)

        logger.info(f"Updated data source file '{filename}' (driver: {config.driver})")

        # Return with filename set
        result = config.model_copy()
        result.filename = filename
        result.name = file_path.stem
        return result

    def delete_data_source(self, filename: str) -> None:
        """Delete a data source file.

        Args:
            filename: Data source filename (with or without .yml)

        Raises:
            ValueError: If data source file not found
        """
        # Normalize filename
        if not filename.endswith(".yml"):
            filename = f"{filename}.yml"

        file_path = self.data_sources_dir / filename

        if not file_path.exists():
            raise ValueError(f"Data source file '{filename}' not found")

        # Delete the file
        file_path.unlink()

        logger.info(f"Deleted data source file '{filename}'")

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
            loader_cls: type[DataLoader] = DataLoaders.get(core_ds_cfg.driver)
            loader: DataLoader = loader_cls(core_ds_cfg)
            result: ConnectTestResult = await loader.test_connection()
            return DataSourceTestResult.from_core_result(result)
        except Exception as e:  # pylint: disable=broad-except
            elapsed_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Connection test failed for '{config.name}': {e}")
            return DataSourceTestResult.create_failure(message=f"Connection failed: {str(e)}", connection_time_ms=elapsed_ms)

    def get_status(self, filename: str) -> DataSourceStatus:
        """Get current status of a data source.

        Args:
            filename: Data source filename

        Returns:
            Current status
        """
        config: DataSourceConfig | None = self.get_data_source(filename)
        if not config:
            raise ValueError(f"Data source file '{filename}' not found")

        return DataSourceStatus(
            name=config.name,
            is_connected=False,  # No persistent connections yet
            in_use_by_entities=[],  # Would need to scan all configs
            last_test_result=None,
        )
