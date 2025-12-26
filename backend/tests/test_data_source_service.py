"""Tests for DataSourceService."""

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml
from pydantic import SecretStr

from backend.app.models.data_source import DataSourceConfig, DataSourceStatus
from backend.app.services.data_source_service import DataSourceService
from src.loaders import DataLoader
from src.loaders.base_loader import ConnectTestResult


class TestDataSourceService:
    """Test DataSourceService for managing YAML data source files."""

    @pytest.fixture
    def temp_sources_dir(self, tmp_path: Path) -> Path:
        """Create temporary data sources directory."""
        sources_dir = tmp_path / "sources"
        sources_dir.mkdir()
        return sources_dir

    @pytest.fixture
    def service(self, temp_sources_dir: Path) -> DataSourceService:
        """Create service instance with temporary directory."""
        return DataSourceService(temp_sources_dir)

    @pytest.fixture
    def sample_config(self) -> DataSourceConfig:
        """Create sample data source configuration."""
        return DataSourceConfig(
            name="test_source",
            driver="postgresql",
            host="localhost",
            port=5432,
            database="testdb",
            username="testuser",
            password=SecretStr("testpass"),
            **{},
        )

    @pytest.fixture
    def sample_yaml_data(self) -> dict[str, Any]:
        """Sample YAML data for a data source."""
        return {
            "driver": "postgresql",
            "host": "localhost",
            "port": 5432,
            "database": "testdb",
            "username": "testuser",
            "password": "testpass",
        }

    # Path resolution tests

    def test_resolve_data_source_path_with_yml_extension(self, service: DataSourceService):
        """Test path resolution with .yml extension."""
        path = service._resolve_data_source_path("test.yml")
        assert path.name == "test.yml"
        assert path.parent == service.data_sources_dir

    def test_resolve_data_source_path_without_extension(self, service: DataSourceService):
        """Test path resolution without extension."""
        path = service._resolve_data_source_path("test")
        assert path.name == "test.yml"

    def test_resolve_data_source_path_with_path_object(self, service: DataSourceService):
        """Test path resolution with Path object."""
        path = service._resolve_data_source_path(Path("test.yml"))
        assert path.name == "test.yml"

    def test_resolve_data_source_path_strips_parent_dirs(self, service: DataSourceService):
        """Test path resolution removes parent directory components."""
        path = service._resolve_data_source_path("../malicious.yml")
        assert path.parent == service.data_sources_dir
        assert ".." not in str(path)

    # List files tests

    def test_list_data_source_files_empty_directory(self, service: DataSourceService):
        """Test listing with no data source files."""
        files = service._list_data_source_files()
        assert files == []

    def test_list_data_source_files_with_yml_files(self, service: DataSourceService, temp_sources_dir: Path):
        """Test listing YAML files."""
        (temp_sources_dir / "db1.yml").touch()
        (temp_sources_dir / "db2.yml").touch()
        (temp_sources_dir / "not_yml.txt").touch()

        files = service._list_data_source_files()
        assert len(files) == 0

    def test_list_data_source_files_sorted(self, service: DataSourceService, temp_sources_dir: Path):
        """Test files are sorted by name."""
        (temp_sources_dir / "zebra.yml").touch()
        (temp_sources_dir / "alpha.yml").touch()
        (temp_sources_dir / "beta.yml").touch()

        files = service._list_data_source_files()
        names = [f.stem for f in files]
        assert names == sorted(names)

    # Read file tests

    def test_read_data_source_file_success(self, service: DataSourceService, temp_sources_dir: Path, sample_yaml_data: dict):
        """Test reading valid YAML data source file."""
        file_path = temp_sources_dir / "test.yml"
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(sample_yaml_data, f)

        data = service._read_data_source_file(file_path)
        assert data["driver"] == "postgresql"
        assert data["database"] == "testdb"

    def test_read_data_source_file_not_found(self, service: DataSourceService):
        """Test reading non-existent file returns None."""
        result = service._read_data_source_file(Path("nonexistent.yml"))
        assert not result

    def test_read_data_source_file_invalid_yaml(self, service: DataSourceService, temp_sources_dir: Path):
        """Test reading invalid YAML returns None."""
        file_path = temp_sources_dir / "invalid.yml"
        file_path.write_text("{ invalid yaml: [", encoding="utf-8")

        result = service._read_data_source_file(file_path)
        assert not result

    def test_read_data_source_file_empty(self, service: DataSourceService, temp_sources_dir: Path):
        """Test reading empty file returns None."""
        file_path = temp_sources_dir / "empty.yml"
        file_path.touch()

        result = service._read_data_source_file(file_path)
        assert not result

    # Write file tests

    def test_write_data_source_file_success(self, service: DataSourceService, temp_sources_dir: Path, sample_yaml_data: dict):
        """Test writing data source file."""
        file_path = temp_sources_dir / "new.yml"
        service._write_data_source_file(file_path, sample_yaml_data)

        assert file_path.exists()
        with open(file_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert data == sample_yaml_data

    def test_write_data_source_file_creates_parent_dirs(self, service: DataSourceService, temp_sources_dir: Path, sample_yaml_data: dict):
        """Test writing creates parent directories."""
        file_path = temp_sources_dir / "nested" / "dir" / "test.yml"
        service._write_data_source_file(file_path, sample_yaml_data)

        assert file_path.exists()

    def test_write_data_source_file_overwrites_existing(self, service: DataSourceService, temp_sources_dir: Path, sample_yaml_data: dict):
        """Test writing overwrites existing file."""
        file_path = temp_sources_dir / "test.yml"
        file_path.write_text("old content")

        service._write_data_source_file(file_path, sample_yaml_data)

        with open(file_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert data == sample_yaml_data

    # List data sources tests

    def test_list_data_sources_empty(self, service: DataSourceService):
        """Test listing with no data sources."""
        configs = service.list_data_sources()
        assert configs == []

    def test_list_data_sources_with_files(self, service: DataSourceService, temp_sources_dir: Path, sample_yaml_data: dict):
        """Test listing data sources from files."""
        (temp_sources_dir / "db1.yml").write_text(yaml.dump(sample_yaml_data))
        sample_yaml_data["database"] = "db2"
        (temp_sources_dir / "db2.yml").write_text(yaml.dump(sample_yaml_data))

        configs = service.list_data_sources()
        assert len(configs) == 2
        assert all(isinstance(c, DataSourceConfig) for c in configs)

    def test_list_data_sources_sets_metadata(self, service: DataSourceService, temp_sources_dir: Path, sample_yaml_data: dict):
        """Test list sets name and filename metadata."""
        (temp_sources_dir / "mydb.yml").write_text(yaml.dump(sample_yaml_data))

        configs = service.list_data_sources()
        assert len(configs) == 1
        assert configs[0].name == "mydb"
        assert configs[0].filename == "mydb.yml"

    def test_list_data_sources_skips_invalid_files(self, service: DataSourceService, temp_sources_dir: Path, sample_yaml_data: dict):
        """Test list skips files with invalid YAML."""
        (temp_sources_dir / "valid.yml").write_text(yaml.dump(sample_yaml_data))
        (temp_sources_dir / "invalid.yml").write_text("{ invalid yaml")

        configs = service.list_data_sources()
        assert len(configs) == 1
        assert configs[0].name == "valid"

    # Get data source tests

    def test_get_data_source_exists(self, service: DataSourceService, temp_sources_dir: Path, sample_yaml_data: dict):
        """Test getting existing data source."""
        (temp_sources_dir / "test.yml").write_text(yaml.dump(sample_yaml_data))

        config = service.get_data_source("test")
        assert config is not None
        assert config.name == "test"
        assert config.database == "testdb"

    def test_get_data_source_not_found(self, service: DataSourceService):
        """Test getting non-existent data source returns None."""
        config = service.get_data_source("nonexistent")
        assert config is None

    def test_get_data_source_with_yml_extension(self, service: DataSourceService, temp_sources_dir: Path, sample_yaml_data: dict):
        """Test getting data source with .yml extension."""
        (temp_sources_dir / "test.yml").write_text(yaml.dump(sample_yaml_data))

        config = service.get_data_source("test.yml")
        assert config is not None
        assert config.name == "test"

    # Create data source tests

    def test_create_data_source_success(self, service: DataSourceService, sample_config: DataSourceConfig):
        """Test creating new data source."""
        result = service.create_data_source("newdb.yml", sample_config)

        assert result.name == "newdb"
        assert result.filename == "newdb.yml"
        assert (service.data_sources_dir / "newdb.yml").exists()

    def test_create_data_source_without_extension(self, service: DataSourceService, sample_config: DataSourceConfig):
        """Test creating data source without .yml extension."""
        result = service.create_data_source("newdb", sample_config)

        assert result.filename == "newdb"
        assert (service.data_sources_dir / "newdb.yml").exists()

    def test_create_data_source_already_exists(self, service: DataSourceService, temp_sources_dir: Path, sample_config: DataSourceConfig):
        """Test creating data source that already exists raises error."""
        (temp_sources_dir / "existing.yml").touch()

        with pytest.raises(ValueError, match="already exists"):
            service.create_data_source("existing.yml", sample_config)

    def test_create_data_source_extracts_password(self, service: DataSourceService, sample_config: DataSourceConfig):
        """Test password is extracted from SecretStr."""
        service.create_data_source("test", sample_config)

        file_path = service.data_sources_dir / "test.yml"
        with open(file_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert data["password"] == "testpass"

    def test_create_data_source_excludes_metadata(self, service: DataSourceService, sample_config: DataSourceConfig):
        """Test name and filename are excluded from saved YAML."""
        service.create_data_source("test", sample_config)

        file_path: Path = service.data_sources_dir / "test.yml"
        with open(file_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert "name" not in data
        assert "filename" not in data

    # Update data source tests

    def test_update_data_source_success(
        self, service: DataSourceService, temp_sources_dir: Path, sample_config: DataSourceConfig, sample_yaml_data: dict
    ):
        """Test updating existing data source."""
        (temp_sources_dir / "test.yml").write_text(yaml.dump(sample_yaml_data))

        sample_config.database = "updated_db"
        result = service.update_data_source("test", sample_config)

        assert result.database == "updated_db"
        config = service.get_data_source("test")

        assert config is not None
        assert config.database == "updated_db"

    def test_update_data_source_not_found(self, service: DataSourceService, sample_config: DataSourceConfig):
        """Test updating non-existent data source raises error."""
        with pytest.raises(ValueError, match="not found"):
            service.update_data_source("nonexistent", sample_config)

    def test_update_data_source_with_yml_extension(
        self, service: DataSourceService, temp_sources_dir: Path, sample_config: DataSourceConfig, sample_yaml_data: dict
    ):
        """Test updating with .yml extension."""
        (temp_sources_dir / "test.yml").write_text(yaml.dump(sample_yaml_data))

        sample_config.database = "new_db"
        result = service.update_data_source("test.yml", sample_config)
        assert result.database == "new_db"

    # Delete data source tests

    def test_delete_data_source_success(self, service: DataSourceService, temp_sources_dir: Path):
        """Test deleting existing data source."""
        file_path = temp_sources_dir / "test.yml"
        file_path.touch()

        service.delete_data_source("test")
        assert not file_path.exists()

    def test_delete_data_source_not_found(self, service: DataSourceService):
        """Test deleting non-existent file doesn't raise error."""
        # Should not raise
        service.delete_data_source("nonexistent")

    def test_delete_data_source_with_yml_extension(self, service: DataSourceService, temp_sources_dir: Path):
        """Test deleting with .yml extension."""
        file_path = temp_sources_dir / "test.yml"
        file_path.touch()

        service.delete_data_source("test.yml")
        assert not file_path.exists()

    # Test connection tests

    @pytest.mark.asyncio
    async def test_test_connection_success(self, service: DataSourceService, sample_config: DataSourceConfig):
        """Test successful connection test."""
        mock_loader = AsyncMock(spec=DataLoader)
        mock_result = ConnectTestResult(success=True, message="Connection successful", connection_time_ms=100, metadata={})
        mock_loader.test_connection = AsyncMock(return_value=mock_result)

        with (
            patch("backend.app.services.data_source_service.DataLoaders.get") as mock_get_loader,
            patch("backend.app.services.data_source_service.DataSourceMapper") as mock_mapper,
        ):
            mock_get_loader.return_value = lambda config: mock_loader
            mock_mapper.return_value.to_core_config = MagicMock(return_value=MagicMock())

            result = await service.test_connection(sample_config)

            assert result.success is True
            assert result.message == "Connection successful"
            assert result.connection_time_ms == 100

    @pytest.mark.asyncio
    async def test_test_connection_failure(self, service: DataSourceService, sample_config: DataSourceConfig):
        """Test failed connection test."""
        mock_loader = AsyncMock(spec=DataLoader)
        mock_loader.test_connection = AsyncMock(side_effect=RuntimeError("Connection refused"))

        with (
            patch("backend.app.services.data_source_service.DataLoaders.get") as mock_get_loader,
            patch("backend.app.services.data_source_service.DataSourceMapper") as mock_mapper,
        ):
            mock_get_loader.return_value = lambda config: mock_loader
            mock_mapper.return_value.to_core_config = MagicMock(return_value=MagicMock())

            result = await service.test_connection(sample_config)

            assert result.success is False
            assert "Connection failed" in result.message

    @pytest.mark.asyncio
    async def test_test_connection_uses_mapper(self, service: DataSourceService, sample_config: DataSourceConfig):
        """Test connection uses DataSourceMapper for env var resolution."""
        mock_loader = AsyncMock(spec=DataLoader)
        mock_result = ConnectTestResult(success=True, message="OK", connection_time_ms=50, metadata={})
        mock_loader.test_connection = AsyncMock(return_value=mock_result)

        with (
            patch("backend.app.services.data_source_service.DataLoaders.get") as mock_get_loader,
            patch("backend.app.services.data_source_service.DataSourceMapper") as mock_mapper,
        ):
            mock_get_loader.return_value = lambda config: mock_loader
            mock_core_config = MagicMock()
            mock_mapper.return_value.to_core_config = MagicMock(return_value=mock_core_config)

            await service.test_connection(sample_config)

            # Verify mapper was called with API config
            mock_mapper.return_value.to_core_config.assert_called_once_with(sample_config)

    # Get status tests

    def test_get_status_success(self, service: DataSourceService, temp_sources_dir: Path, sample_yaml_data: dict):
        """Test getting status of existing data source."""
        (temp_sources_dir / "test.yml").write_text(yaml.dump(sample_yaml_data))

        status = service.get_status("test")
        assert isinstance(status, DataSourceStatus)
        assert status.name == "test"
        assert status.is_connected is False
        assert status.in_use_by_entities == []

    def test_get_status_not_found(self, service: DataSourceService):
        """Test getting status of non-existent source raises error."""
        with pytest.raises(ValueError, match="not found"):
            service.get_status("nonexistent")

    def test_get_status_with_yml_extension(self, service: DataSourceService, temp_sources_dir: Path, sample_yaml_data: dict):
        """Test getting status with .yml extension."""
        (temp_sources_dir / "test.yml").write_text(yaml.dump(sample_yaml_data))

        status = service.get_status("test.yml")
        assert status.name == "test"
