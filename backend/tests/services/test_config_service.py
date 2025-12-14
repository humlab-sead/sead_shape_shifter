"""Tests for configuration service."""

import pytest
from app.models.entity import Entity
from app.services.config_service import (
    ConfigurationNotFoundError,
    ConfigurationService,
    ConfigurationServiceError,
    EntityAlreadyExistsError,
    EntityNotFoundError,
    InvalidConfigurationError,
)


@pytest.fixture
def config_service(tmp_path, monkeypatch):
    """Create ConfigurationService with temporary directory."""
    from app.core.config import settings

    # Override settings to use temp directory
    monkeypatch.setattr(settings, "CONFIGURATIONS_DIR", tmp_path)
    return ConfigurationService()


@pytest.fixture
def sample_config_file(tmp_path):
    """Create a sample configuration file."""
    config_path = tmp_path / "test_config.yml"
    content = """
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


class TestConfigurationServiceList:
    """Tests for listing configurations."""

    def test_list_configurations_empty(self, config_service, tmp_path):
        """Test listing when no configurations exist."""
        configs = config_service.list_configurations()
        assert configs == []

    def test_list_configurations(self, config_service, sample_config_file):
        """Test listing configurations."""
        configs = config_service.list_configurations()
        assert len(configs) == 1
        assert configs[0].name == "test_config"
        assert configs[0].entity_count == 2
        assert configs[0].is_valid is True

    def test_list_includes_invalid_configs(self, config_service, tmp_path):
        """Test that invalid configs are included with is_valid=False."""
        invalid_path = tmp_path / "invalid.yml"
        invalid_path.write_text("invalid: yaml: syntax:")

        configs = config_service.list_configurations()
        assert len(configs) == 1
        assert configs[0].name == "invalid"
        assert configs[0].is_valid is False


class TestConfigurationServiceLoad:
    """Tests for loading configurations."""

    def test_load_configuration(self, config_service, sample_config_file):
        """Test loading valid configuration."""
        config = config_service.load_configuration("test_config")

        assert config.metadata.name == "test_config"
        assert len(config.entities) == 2
        assert "sample" in config.entities
        assert "site" in config.entities
        assert config.options["verbose"] is True

    def test_load_nonexistent_configuration(self, config_service):
        """Test loading non-existent configuration raises error."""
        with pytest.raises(ConfigurationNotFoundError):
            config_service.load_configuration("nonexistent")

    def test_load_configuration_metadata(self, config_service, sample_config_file):
        """Test that metadata is populated correctly."""
        config = config_service.load_configuration("test_config")

        assert config.metadata.entity_count == 2
        assert config.metadata.created_at > 0
        assert config.metadata.modified_at > 0
        assert config.metadata.is_valid is True


class TestConfigurationServiceSave:
    """Tests for saving configurations."""

    def test_save_configuration(self, config_service, sample_config_file):
        """Test saving configuration."""
        config = config_service.load_configuration("test_config")
        config.entities["new_entity"] = {"type": "data", "keys": ["id"]}

        updated = config_service.save_configuration(config)

        assert updated.metadata.entity_count == 3

        # Reload and verify
        reloaded = config_service.load_configuration("test_config")
        assert "new_entity" in reloaded.entities

    def test_save_without_metadata_raises_error(self, config_service):
        """Test saving configuration without metadata raises error."""
        from app.models.config import Configuration

        config = Configuration(entities={}, options={})

        with pytest.raises(InvalidConfigurationError, match="must have metadata"):
            config_service.save_configuration(config)


class TestConfigurationServiceCreate:
    """Tests for creating configurations."""

    def test_create_configuration(self, config_service, tmp_path):
        """Test creating new configuration."""
        config = config_service.create_configuration("new_config")

        assert config.metadata.name == "new_config"
        assert len(config.entities) == 0
        assert (tmp_path / "new_config.yml").exists()

    def test_create_configuration_with_entities(self, config_service):
        """Test creating configuration with initial entities."""
        entities = {"sample": {"type": "data", "keys": ["id"]}}
        config = config_service.create_configuration("new_config", entities)

        assert len(config.entities) == 1
        assert "sample" in config.entities

    def test_create_duplicate_configuration_raises_error(self, config_service, sample_config_file):
        """Test creating duplicate configuration raises error."""
        with pytest.raises(ConfigurationServiceError, match="already exists"):
            config_service.create_configuration("test_config")


class TestConfigurationServiceDelete:
    """Tests for deleting configurations."""

    def test_delete_configuration(self, config_service, sample_config_file, tmp_path):
        """Test deleting configuration."""
        config_service.delete_configuration("test_config")
        assert not (tmp_path / "test_config.yml").exists()

    def test_delete_nonexistent_raises_error(self, config_service):
        """Test deleting non-existent configuration raises error."""
        with pytest.raises(ConfigurationNotFoundError):
            config_service.delete_configuration("nonexistent")


class TestConfigurationServiceEntity:
    """Tests for entity operations."""

    def test_add_entity(self, config_service, sample_config_file):
        """Test adding entity to configuration."""
        config = config_service.load_configuration("test_config")

        entity = Entity(name="new_entity", surrogate_id="new_entity_id", keys=["id"])
        updated = config_service.add_entity(config, "new_entity", entity)

        assert "new_entity" in updated.entities
        assert updated.entities["new_entity"]["surrogate_id"] == "new_entity_id"

    def test_add_duplicate_entity_raises_error(self, config_service, sample_config_file):
        """Test adding duplicate entity raises error."""
        config = config_service.load_configuration("test_config")
        entity = Entity(name="sample", surrogate_id="sample_id", keys=["id"])

        with pytest.raises(EntityAlreadyExistsError):
            config_service.add_entity(config, "sample", entity)

    def test_update_entity(self, config_service, sample_config_file):
        """Test updating entity."""
        config = config_service.load_configuration("test_config")

        entity = Entity(name="sample", surrogate_id="sample_id", keys=["id"], columns=["new_column"])
        updated = config_service.update_entity(config, "sample", entity)

        assert updated.entities["sample"]["columns"] == ["new_column"]

    def test_update_nonexistent_entity_raises_error(self, config_service, sample_config_file):
        """Test updating non-existent entity raises error."""
        config = config_service.load_configuration("test_config")
        entity = Entity(name="nonexistent", surrogate_id="nonexistent_id", keys=["id"])

        with pytest.raises(EntityNotFoundError):
            config_service.update_entity(config, "nonexistent", entity)

    def test_delete_entity(self, config_service, sample_config_file):
        """Test deleting entity."""
        config = config_service.load_configuration("test_config")
        updated = config_service.delete_entity(config, "sample")

        assert "sample" not in updated.entities
        assert len(updated.entities) == 1

    def test_delete_nonexistent_entity_raises_error(self, config_service, sample_config_file):
        """Test deleting non-existent entity raises error."""
        config = config_service.load_configuration("test_config")

        with pytest.raises(EntityNotFoundError):
            config_service.delete_entity(config, "nonexistent")

    def test_get_entity(self, config_service, sample_config_file):
        """Test getting entity."""
        config = config_service.load_configuration("test_config")
        entity = config_service.get_entity(config, "sample")

        assert entity["type"] == "data"
        assert entity["keys"] == ["sample_id"]

    def test_get_nonexistent_entity_raises_error(self, config_service, sample_config_file):
        """Test getting non-existent entity raises error."""
        config = config_service.load_configuration("test_config")

        with pytest.raises(EntityNotFoundError):
            config_service.get_entity(config, "nonexistent")


class TestConfigurationServiceRoundtrip:
    """Tests for load-modify-save roundtrip."""

    def test_roundtrip(self, config_service, sample_config_file):
        """Test load-modify-save-reload cycle."""
        # Load
        config = config_service.load_configuration("test_config")
        original_entity_count = len(config.entities)

        # Modify
        entity = Entity(name="new_entity", surrogate_id="new_entity_id", keys=["id"])
        config = config_service.add_entity(config, "new_entity", entity)

        # Save
        config_service.save_configuration(config)

        # Reload
        reloaded = config_service.load_configuration("test_config")

        assert len(reloaded.entities) == original_entity_count + 1
        assert "new_entity" in reloaded.entities
