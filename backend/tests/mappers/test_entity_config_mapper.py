"""Tests for entity config mapper strategy pattern."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from backend.app.core.config import Settings
from backend.app.mappers.entity_config_mapper import (
    DefaultEntityConfigMapper,
    EntityConfigMapperFactory,
    FileBasedEntityConfigMapper,
)


class TestEntityConfigMapperFactory:
    """Test entity config mapper factory."""

    @pytest.fixture
    def mock_settings(self, tmp_path: Path) -> Settings:
        """Create mock settings."""
        settings = Mock(spec=Settings)
        settings.GLOBAL_DATA_DIR = tmp_path / "shared/shared-data"
        settings.PROJECTS_DIR = tmp_path / "projects"
        settings.APPLICATION_ROOT = tmp_path
        settings.GLOBAL_DATA_DIR.mkdir(parents=True, exist_ok=True)
        settings.PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
        return settings

    @pytest.fixture
    def factory(self, mock_settings: Settings) -> EntityConfigMapperFactory:
        """Create mapper factory."""
        return EntityConfigMapperFactory(mock_settings)

    def test_get_mapper_for_csv_returns_file_based_mapper(self, factory: EntityConfigMapperFactory) -> None:
        """Test that CSV driver returns file-based mapper."""
        mapper = factory.get_mapper("csv")
        assert isinstance(mapper, FileBasedEntityConfigMapper)

    def test_get_mapper_for_excel_returns_file_based_mapper(self, factory: EntityConfigMapperFactory) -> None:
        """Test that Excel driver returns file-based mapper."""
        mapper = factory.get_mapper("xlsx")
        assert isinstance(mapper, FileBasedEntityConfigMapper)

    def test_get_mapper_for_postgresql_returns_default_mapper(self, factory: EntityConfigMapperFactory) -> None:
        """Test that PostgreSQL driver returns default (no-op) mapper."""
        mapper = factory.get_mapper("postgresql")
        assert isinstance(mapper, DefaultEntityConfigMapper)

    def test_get_mapper_for_fixed_returns_default_mapper(self, factory: EntityConfigMapperFactory) -> None:
        """Test that fixed values driver returns default (no-op) mapper."""
        mapper = factory.get_mapper("fixed")
        assert isinstance(mapper, DefaultEntityConfigMapper)


class TestDefaultEntityConfigMapper:
    """Test default (no-op) entity config mapper."""

    @pytest.fixture
    def mapper(self) -> DefaultEntityConfigMapper:
        """Create default mapper."""
        settings = Mock(spec=Settings)
        return DefaultEntityConfigMapper(settings)

    def test_to_api_returns_unchanged_config(self, mapper: DefaultEntityConfigMapper) -> None:
        """Test that to_api returns config unchanged."""
        config = {"name": "test", "data_source": {"driver": "postgresql"}}
        result = mapper.to_api(config, "project")
        assert result is config  # Same object
        assert result == {"name": "test", "data_source": {"driver": "postgresql"}}

    def test_to_core_returns_unchanged_config(self, mapper: DefaultEntityConfigMapper) -> None:
        """Test that to_core returns config unchanged."""
        config = {"name": "test", "data_source": {"driver": "fixed"}}
        result = mapper.to_core(config, "project")
        assert result is config  # Same object
        assert result == {"name": "test", "data_source": {"driver": "fixed"}}


class TestFileBasedEntityConfigMapper:
    """Test file-based entity config mapper."""

    @pytest.fixture
    def mock_settings(self, tmp_path: Path) -> Settings:
        """Create mock settings."""
        settings = Mock(spec=Settings)
        settings.GLOBAL_DATA_DIR = tmp_path / "shared/shared-data"
        settings.global_data_dir = settings.GLOBAL_DATA_DIR  # For property access
        settings.PROJECTS_DIR = tmp_path / "projects"
        settings.projects_root = settings.PROJECTS_DIR  # For property access
        settings.APPLICATION_ROOT = tmp_path
        settings.application_root = settings.APPLICATION_ROOT  # For property access
        settings.global_data_dir.mkdir(parents=True, exist_ok=True)
        settings.projects_root.mkdir(parents=True, exist_ok=True)
        return settings

    @pytest.fixture
    def factory(self, mock_settings: Settings) -> EntityConfigMapperFactory:
        """Create mapper factory."""
        return EntityConfigMapperFactory(mock_settings)

    def test_to_core_resolves_global_file(self, factory: EntityConfigMapperFactory, mock_settings: Settings) -> None:
        """Test that to_core resolves global file paths."""
        config = {"options": {"filename": "data.csv", "location": "global"}}
        mapper = factory.get_mapper("csv")

        result = mapper.to_core(config, "test_project")

        expected_path = str(mock_settings.global_data_dir / "data.csv")
        assert result["options"]["filename"] == expected_path
        assert "location" not in result["options"]  # Removed for Core

    def test_to_core_resolves_local_file(self, factory: EntityConfigMapperFactory, mock_settings: Settings) -> None:
        """Test that to_core resolves local file paths."""
        config = {"options": {"filename": "data.csv", "location": "local"}}
        mapper = factory.get_mapper("csv")

        result = mapper.to_core(config, "test_project")

        expected_path = str(mock_settings.projects_root / "test_project" / "data.csv")
        assert result["options"]["filename"] == expected_path
        assert "location" not in result["options"]  # Removed for Core

    def test_to_api_decomposes_global_path(self, factory: EntityConfigMapperFactory, mock_settings: Settings) -> None:
        """Test that to_api decomposes global absolute paths."""
        absolute_path = str(mock_settings.global_data_dir / "data.csv")
        config = {"options": {"filename": absolute_path}}
        mapper = factory.get_mapper("csv")

        result = mapper.to_api(config, "test_project")

        assert result["options"]["filename"] == "data.csv"
        assert result["options"]["location"] == "global"

    def test_to_api_decomposes_local_path(self, factory: EntityConfigMapperFactory, mock_settings: Settings) -> None:
        """Test that to_api decomposes local absolute paths."""
        absolute_path = str(mock_settings.projects_root / "test_project" / "data.csv")
        config = {"options": {"filename": absolute_path}}
        mapper = factory.get_mapper("csv")

        result = mapper.to_api(config, "test_project")

        assert result["options"]["filename"] == "data.csv"
        assert result["options"]["location"] == "local"

    def test_to_core_handles_legacy_format(self, factory: EntityConfigMapperFactory, mock_settings: Settings) -> None:
        """Test that to_core handles legacy ${GLOBAL_DATA_DIR}/file format."""
        config = {"options": {"filename": "${GLOBAL_DATA_DIR}/data.csv"}}
        mapper = factory.get_mapper("csv")

        result = mapper.to_core(config, "test_project")

        expected_path = str(mock_settings.global_data_dir / "data.csv")
        assert result["options"]["filename"] == expected_path
        assert "location" not in result["options"]  # Removed for Core

    def test_to_core_no_op_when_no_filename(self, factory: EntityConfigMapperFactory) -> None:
        """Test that to_core is no-op when no filename present."""
        config = {"options": {"other_field": "value"}}
        mapper = factory.get_mapper("csv")

        result = mapper.to_core(config, "test_project")

        assert result == config

    def test_to_api_no_op_when_no_filename(self, factory: EntityConfigMapperFactory) -> None:
        """Test that to_api is no-op when no filename present."""
        config = {"options": {"other_field": "value"}}
        mapper = factory.get_mapper("csv")

        result = mapper.to_api(config, "test_project")

        assert result == config
