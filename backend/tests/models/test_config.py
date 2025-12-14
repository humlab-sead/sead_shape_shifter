"""Tests for configuration models."""

from app.models.config import ConfigMetadata, Configuration
from app.models.entity import Entity


class TestConfiguration:
    """Tests for Configuration model."""

    def test_empty_configuration(self):
        """Test creating empty configuration."""
        config = Configuration()
        assert config.entities == {}
        assert config.entity_names == []

    def test_add_entity(self):
        """Test adding entity to configuration."""
        config = Configuration()
        entity_data = {"type": "data", "keys": ["id"]}
        config.add_entity("sample", entity_data)
        assert "sample" in config.entities
        assert config.entity_names == ["sample"]

    def test_get_entity(self):
        """Test getting entity by name."""
        config = Configuration()
        entity_data = {"type": "data", "keys": ["id"]}
        config.add_entity("sample", entity_data)

        retrieved = config.get_entity("sample")
        assert retrieved is not None
        assert retrieved["type"] == "data"

        missing = config.get_entity("nonexistent")
        assert missing is None

    def test_remove_entity(self):
        """Test removing entity from configuration."""
        config = Configuration()
        entity_data = {"type": "data", "keys": ["id"]}
        config.add_entity("sample", entity_data)

        result = config.remove_entity("sample")
        assert result is True
        assert "sample" not in config.entities

        # Try removing again
        result = config.remove_entity("sample")
        assert result is False

    def test_with_metadata(self):
        """Test configuration with metadata."""
        metadata = ConfigMetadata(
            name="test_config",
            entity_count=5,
            is_valid=True,
        )
        config = Configuration(metadata=metadata)
        assert config.metadata is not None
        assert config.metadata.name == "test_config"


class TestConfigMetadata:
    """Tests for ConfigMetadata model."""

    def test_valid_metadata(self):
        """Test valid metadata creation."""
        metadata = ConfigMetadata(
            name="arbodat",
            file_path="/path/to/config.yml",
            entity_count=67,
            is_valid=True,
        )
        assert metadata.name == "arbodat"
        assert metadata.entity_count == 67
        assert metadata.is_valid is True

    def test_default_is_valid(self):
        """Test is_valid defaults to True."""
        metadata = ConfigMetadata(name="test", entity_count=0)
        assert metadata.is_valid is True
