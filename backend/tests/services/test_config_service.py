"""Tests for configuration service."""

import pytest

from backend.app.core.config import settings
from backend.app.models.entity import Entity
from backend.app.models.project import Project
from backend.app.services.project_service import (
    EntityAlreadyExistsError,
    EntityNotFoundError,
    InvalidProjectError,
    ProjectNotFoundError,
    ProjectService,
    ProjectServiceError,
)

# pylint: disable=redefined-outer-name, unused-argument


@pytest.fixture
def project_service(tmp_path, monkeypatch):
    """Create ProjectService with temporary directory."""

    # Override settings to use temp directory
    monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
    return ProjectService()


@pytest.fixture
def sample_config_file(tmp_path):
    """Create a sample configuration file."""
    config_path = tmp_path / "test_project.yml"
    content = """

metadata:
  type: shapeshifter-project
  name: test_project
  description: A test project
  version: 1.0.0

entities:
  sample:
    type: data
    keys: [sample_id]
    columns: [name, value]

  site:
    type: data
    keys: [site_id]
    columns: [name, location]

options:
  verbose: true
"""
    config_path.write_text(content)
    return config_path


class TestProjectServiceList:
    """Tests for listing configurations."""

    def test_list_configurations_empty(self, project_service, tmp_path):
        """Test listing when no configurations exist."""
        configs = project_service.list_projects()
        assert configs == []

    def test_list_configurations(self, project_service, sample_config_file):
        """Test listing configurations."""
        configs = project_service.list_projects()
        assert len(configs) == 1
        assert configs[0].name == "test_project"
        assert configs[0].entity_count == 2
        assert configs[0].is_valid is True


class TestProjectServiceLoad:
    """Tests for loading configurations."""

    def test_load_configuration(self, project_service, sample_config_file):
        """Test loading valid configuration."""
        config = project_service.load_project("test_project")

        assert config.metadata.name == "test_project"
        assert len(config.entities) == 2
        assert "sample" in config.entities
        assert "site" in config.entities
        assert config.options["verbose"] is True

    def test_load_nonexistent_configuration(self, project_service):
        """Test loading non-existent configuration raises error."""
        with pytest.raises(ProjectNotFoundError):
            project_service.load_project("nonexistent")

    def test_load_configuration_metadata(self, project_service, sample_config_file):
        """Test that metadata is populated correctly."""
        config = project_service.load_project("test_project")

        assert config.metadata.entity_count == 2
        assert config.metadata.created_at > 0
        assert config.metadata.modified_at > 0
        assert config.metadata.is_valid is True


class TestProjectServiceSave:
    """Tests for saving configurations."""

    def test_save_configuration(self, project_service, sample_config_file):
        """Test saving configuration."""
        config = project_service.load_project("test_project")
        config.entities["new_entity"] = {"type": "data", "keys": ["id"]}

        updated = project_service.save_project(config)

        assert updated.metadata.entity_count == 3

        # Reload and verify
        reloaded = project_service.load_project("test_project")
        assert "new_entity" in reloaded.entities

    def test_save_without_metadata_raises_error(self, project_service):
        """Test saving configuration without metadata raises error."""

        config = Project(entities={}, options={})

        with pytest.raises(InvalidProjectError, match="must have metadata"):
            project_service.save_project(config)


class TestProjectServiceCreate:
    """Tests for creating configurations."""

    def test_create_configuration(self, project_service, tmp_path):
        """Test creating new configuration."""
        config = project_service.create_project("new_config")

        assert config.metadata.name == "new_config"
        assert len(config.entities) == 0
        assert (tmp_path / "new_config.yml").exists()

    def test_create_configuration_with_entities(self, project_service):
        """Test creating configuration with initial entities."""
        entities = {"sample": {"type": "data", "keys": ["id"]}}
        config = project_service.create_project("new_config", entities)

        assert len(config.entities) == 1
        assert "sample" in config.entities

    def test_create_duplicate_configuration_raises_error(self, project_service, sample_config_file):
        """Test creating duplicate configuration raises error."""
        with pytest.raises(ProjectServiceError, match="already exists"):
            project_service.create_project("test_project")


class TestProjectServiceDelete:
    """Tests for deleting configurations."""

    def test_delete_configuration(self, project_service, sample_config_file, tmp_path):
        """Test deleting configuration."""
        project_service.delete_project("test_project")
        assert not (tmp_path / "test_project.yml").exists()

    def test_delete_nonexistent_raises_error(self, project_service):
        """Test deleting non-existent configuration raises error."""
        with pytest.raises(ProjectNotFoundError):
            project_service.delete_project("nonexistent")


class TestProjectServiceEntity:
    """Tests for entity operations."""

    def test_add_entity(self, project_service, sample_config_file):
        """Test adding entity to configuration."""
        config = project_service.load_project("test_project")

        entity = Entity(name="new_entity", surrogate_id="new_entity_id", keys=["id"])
        updated = project_service.add_entity(config, "new_entity", entity)

        assert "new_entity" in updated.entities
        assert updated.entities["new_entity"]["surrogate_id"] == "new_entity_id"

    def test_add_duplicate_entity_raises_error(self, project_service, sample_config_file):
        """Test adding duplicate entity raises error."""
        config = project_service.load_project("test_project")
        entity = Entity(name="sample", surrogate_id="sample_id", keys=["id"])

        with pytest.raises(EntityAlreadyExistsError):
            project_service.add_entity(config, "sample", entity)

    def test_update_entity(self, project_service, sample_config_file):
        """Test updating entity."""
        config = project_service.load_project("test_project")

        entity = Entity(name="sample", surrogate_id="sample_id", keys=["id"], columns=["new_column"])
        updated = project_service.update_entity(config, "sample", entity)

        assert updated.entities["sample"]["columns"] == ["new_column"]

    def test_update_nonexistent_entity_raises_error(self, project_service, sample_config_file):
        """Test updating non-existent entity raises error."""
        config = project_service.load_project("test_project")
        entity = Entity(name="nonexistent", surrogate_id="nonexistent_id", keys=["id"])

        with pytest.raises(EntityNotFoundError):
            project_service.update_entity(config, "nonexistent", entity)

    def test_delete_entity(self, project_service, sample_config_file):
        """Test deleting entity."""
        config = project_service.load_project("test_project")
        updated = project_service.delete_entity(config, "sample")

        assert "sample" not in updated.entities
        assert len(updated.entities) == 1

    def test_delete_nonexistent_entity_raises_error(self, project_service, sample_config_file):
        """Test deleting non-existent entity raises error."""
        config = project_service.load_project("test_project")

        with pytest.raises(EntityNotFoundError):
            project_service.delete_entity(config, "nonexistent")

    def test_get_entity(self, project_service, sample_config_file):
        """Test getting entity."""
        config = project_service.load_project("test_project")
        entity = project_service.get_entity(config, "sample")

        assert entity["type"] == "data"
        assert entity["keys"] == ["sample_id"]

    def test_get_nonexistent_entity_raises_error(self, project_service, sample_config_file):
        """Test getting non-existent entity raises error."""
        config = project_service.load_project("test_project")

        with pytest.raises(EntityNotFoundError):
            project_service.get_entity(config, "nonexistent")


class TestProjectServiceRoundtrip:
    """Tests for load-modify-save roundtrip."""

    def test_roundtrip(self, project_service, sample_config_file):
        """Test load-modify-save-reload cycle."""
        # Load
        config = project_service.load_project("test_project")
        original_entity_count = len(config.entities)

        # Modify
        entity = Entity(name="new_entity", surrogate_id="new_entity_id", keys=["id"])
        config = project_service.add_entity(config, "new_entity", entity)

        # Save
        project_service.save_project(config)

        # Reload
        reloaded = project_service.load_project("test_project")

        assert len(reloaded.entities) == original_entity_count + 1
        assert "new_entity" in reloaded.entities
