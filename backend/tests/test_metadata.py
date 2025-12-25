"""Tests for metadata handling in configurations."""

from pathlib import Path

import pytest

from backend.app.mappers.config_mapper import ConfigMapper
from backend.app.models.config import ConfigMetadata, Configuration
from src.model import Metadata, ShapeShiftConfig

# pylint: disable=no-member


class TestMetadataHandling:
    """Tests for metadata section in configuration files."""

    def test_api_metadata_has_description_and_version(self):
        """Test that ConfigMetadata has description and version fields."""
        metadata = ConfigMetadata(
            name="Test Config",
            description="A test configuration",
            version="1.2.3",
            entity_count=5,
        )

        assert metadata.name == "Test Config"
        assert metadata.description == "A test configuration"
        assert metadata.version == "1.2.3"
        assert metadata.entity_count == 5

    def test_metadata_optional_fields(self):
        """Test that description and version are optional."""
        metadata = ConfigMetadata(
            name="Minimal Config",
            entity_count=0,
        )

        assert metadata.name == "Minimal Config"
        assert metadata.description is None
        assert metadata.version is None

    def test_core_metadata_class(self):
        """Test that ShapeShiftConfig has Metadata class."""

        metadata_data = {
            "name": "Core Config",
            "description": "Core test",
            "version": "2.0.0",
        }

        metadata = Metadata(metadata_data)

        assert metadata.name == "Core Config"
        assert metadata.description == "Core test"
        assert metadata.version == "2.0.0"

    def test_core_config_metadata_property(self):
        """Test that ShapeShiftConfig has metadata property."""
        cfg_dict = {
            "metadata": {
                "name": "Test Config",
                "description": "Testing metadata",
                "version": "1.0.0",
            },
            "entities": {
                "sample": {
                    "type": "data",
                    "keys": ["id"],
                }
            },
        }

        config = ShapeShiftConfig(cfg=cfg_dict)

        assert config.metadata.name == "Test Config"
        assert config.metadata.description == "Testing metadata"
        assert config.metadata.version == "1.0.0"

    def test_mapper_preserves_metadata(self):
        """Test that mapper preserves metadata section in round-trip."""
        core_dict = {
            "metadata": {
                "name": "Mapper Test",
                "description": "Testing mapper metadata preservation",
                "version": "3.1.4",
            },
            "entities": {
                "users": {
                    "type": "data",
                    "keys": ["user_id"],
                    "columns": ["name", "email"],
                }
            },
            "options": {},
        }

        # Core -> API
        api_config = ConfigMapper.to_api_config(core_dict, "mapper-test")

        assert api_config.metadata is not None
        assert api_config.metadata.name == "Mapper Test"
        assert api_config.metadata.description == "Testing mapper metadata preservation"
        assert api_config.metadata.version == "3.1.4"

        # API -> Core
        restored_dict = ConfigMapper.to_core_dict(api_config)

        assert "metadata" in restored_dict
        assert restored_dict["metadata"]["name"] == "Mapper Test"
        assert restored_dict["metadata"]["description"] == "Testing mapper metadata preservation"
        assert restored_dict["metadata"]["version"] == "3.1.4"

    def test_mapper_uses_metadata_name_over_filename(self):
        """Test that mapper prefers metadata.name over filename parameter."""
        core_dict = {
            "metadata": {
                "name": "Official Name",
                "description": "This name should be used",
            },
            "entities": {},
        }

        api_config: Configuration = ConfigMapper.to_api_config(core_dict, "filename-name")

        assert api_config.metadata is not None
        assert api_config.metadata.name == "Official Name"

    def test_mapper_falls_back_to_filename_if_no_metadata_name(self):
        """Test that mapper uses filename if metadata.name is missing."""
        core_dict = {
            "metadata": {
                "description": "No name in metadata",
            },
            "entities": {},
        }

        api_config: Configuration = ConfigMapper.to_api_config(core_dict, "fallback-name")

        assert api_config.metadata is not None
        assert api_config.metadata.name == "fallback-name"

    def test_real_arbodat_config_metadata(self):
        """Test that real arbodat config metadata is loaded correctly."""
        config_path = Path(__file__).parent / "test_data" / "configurations" / "arbodat-database.yml"
        if not config_path.exists():
            pytest.skip("Test config file not found")

        config: ShapeShiftConfig = ShapeShiftConfig.from_file(str(config_path))

        # Check metadata from YAML
        assert config.metadata.name == "ArboDat Database Configuration"
        assert config.metadata.description == "Configuration for importing data from ArboDat database into SEAD."
        assert config.metadata.version == "1.0.0"
