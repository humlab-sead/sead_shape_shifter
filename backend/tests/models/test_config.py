"""Tests for configuration models."""

from backend.app.models.project import Project, ProjectMetadata


class TestConfiguration:
    """Tests for Configuration model."""

    def test_empty_configuration(self):
        """Test creating empty configuration."""
        config = Project()
        assert config.entities == {}
        assert not config.entity_names

    def test_add_entity(self):
        """Test adding entity to configuration."""
        config = Project()
        entity_data = {"type": "data", "keys": ["id"]}
        config.add_entity("sample", entity_data)
        assert "sample" in config.entities
        assert config.entity_names == ["sample"]

    def test_get_entity(self):
        """Test getting entity by name."""
        config = Project()
        entity_data = {"type": "data", "keys": ["id"]}
        config.add_entity("sample", entity_data)

        retrieved = config.get_entity("sample")
        assert retrieved is not None
        assert retrieved["type"] == "data"

        missing = config.get_entity("nonexistent")
        assert missing is None

    def test_remove_entity(self):
        """Test removing entity from configuration."""
        config = Project()
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
        metadata = ProjectMetadata(
            name="test_project",
            entity_count=5,
            is_valid=True,
        )
        config = Project(metadata=metadata)
        assert config.metadata is not None
        assert config.metadata.name == "test_project"  # pylint: disable=no-member


class TestProjectMetadata:
    """Tests for ProjectMetadata model."""

    def test_valid_metadata(self):
        """Test valid metadata creation."""
        metadata = ProjectMetadata(
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
        metadata = ProjectMetadata(name="test", entity_count=0)
        assert metadata.is_valid is True
