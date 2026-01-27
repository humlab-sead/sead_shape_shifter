"""Tests for ProjectService."""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import yaml

from backend.app.core.config import settings
from backend.app.models.entity import Entity
from backend.app.models.project import Project, ProjectMetadata
from backend.app.services.project_service import (
    EntityAlreadyExistsError,
    EntityNotFoundError,
    InvalidProjectError,
    ProjectConflictError,
    ProjectNotFoundError,
    ProjectService,
    get_project_service,
)

# pylint: disable=redefined-outer-name, unused-argument


class TestProjectService:
    """Test ProjectService for managing entity configurations."""

    @pytest.fixture
    def temp_config_dir(self, tmp_path: Path) -> Path:
        """Create temporary configurations directory."""
        config_dir = tmp_path / "configurations"
        config_dir.mkdir()
        return config_dir

    @pytest.fixture
    def mock_metadata(self) -> dict[str, Any]:
        """Create mock ProjectMetadata."""
        return {
            "type": "shapeshifter-project",
            "name": "test",
            "description": "Test configuration",
            "version": "1.0.0",
            "default_entity": "sample",
            "file_path": "test.yml",
            "entity_count": 1,
            "created_at": 0,
            "modified_at": 0,
            "is_valid": True,
        }

    @pytest.fixture
    def service(self, temp_config_dir: Path, mock_metadata: dict[str, Any]) -> ProjectService:
        """Create service instance with temporary directory."""
        with patch("backend.app.services.project_service.settings") as mock_settings:
            mock_settings.PROJECTS_DIR = temp_config_dir
            mock_state = MagicMock()
            mock_state.update = MagicMock()
            mock_state.activate = MagicMock()
            mock_state.get_active_metadata = MagicMock(return_value=ProjectMetadata(**mock_metadata))

            service = ProjectService(state=mock_state)
            return service

    @pytest.fixture
    def simple_service(self, tmp_path: Path, monkeypatch):
        """Create ProjectService with temporary directory (simpler setup)."""
        # Override settings to use temp directory
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        return ProjectService()

    @pytest.fixture
    def sample_yaml_dict(self, mock_metadata: dict[str, Any]) -> dict[str, Any]:
        """Sample YAML dictionary for configuration."""
        return {
            "metadata": mock_metadata,
            "entities": {
                "sample": {
                    "source": "test_table",
                    "columns": ["id", "name"],
                }
            },
            "options": {},
        }

    @pytest.fixture
    def sample_config(self, sample_yaml_dict) -> Project:
        """Create sample configuration."""
        return Project(**sample_yaml_dict)

    @pytest.fixture
    def sample_config_file(self, tmp_path):
        """Create a sample configuration file with multiple entities."""
        config_path = tmp_path / "test_project.yml"
        content = """
metadata:
  type: shapeshifter-project
  name: test_project
  description: A test project
  version: 1.0.0

entities:
  sample:
    type: entity
    keys: [sample_id]
    columns: [name, value]

  site:
    type: entity
    keys: [site_id]
    columns: [name, location]

options:
  verbose: true
"""
        config_path.write_text(content)
        return config_path

    # List configurations tests

    def test_list_configurations_empty(self, service: ProjectService):
        """Test listing with no configurations."""
        configs = service.list_projects()
        assert configs == []

    def test_list_configurations_with_files(self, service: ProjectService, temp_config_dir: Path, sample_yaml_dict: dict):
        """Test listing existing configurations."""
        (temp_config_dir / "config1.yml").write_text(yaml.dump(sample_yaml_dict))
        (temp_config_dir / "config2.yml").write_text(yaml.dump(sample_yaml_dict))

        configs = service.list_projects()
        assert len(configs) == 2
        assert all(isinstance(m, ProjectMetadata) for m in configs)

    def test_list_configurations_sets_metadata(self, service: ProjectService, temp_config_dir: Path, sample_yaml_dict: dict):
        """Test list sets correct metadata."""
        file_path = temp_config_dir / "myconfig.yml"
        file_path.write_text(yaml.dump(sample_yaml_dict))

        configs = service.list_projects()
        assert len(configs) == 1
        assert configs[0].name == "myconfig"
        assert configs[0].entity_count == 1
        assert configs[0].created_at > 0
        assert configs[0].modified_at > 0

    def test_list_configurations_skips_non_yml(self, service: ProjectService, temp_config_dir: Path, sample_yaml_dict: dict):
        """Test list ignores non-YAML files."""
        (temp_config_dir / "valid.yml").write_text(yaml.dump(sample_yaml_dict))
        (temp_config_dir / "readme.txt").write_text("not yaml")

        configs = service.list_projects()
        assert len(configs) == 1

    def test_list_configurations_validates_files(self, service: ProjectService, temp_config_dir: Path, sample_yaml_dict: dict):
        """Test list sets is_valid based on validation."""
        (temp_config_dir / "valid.yml").write_text(yaml.dump(sample_yaml_dict))

        configs = service.list_projects()
        assert len(configs) == 1
        # is_valid should be set (True or False depending on validation)
        assert isinstance(configs[0].is_valid, bool)

    # Load configuration tests

    def test_load_configuration_success(self, service: ProjectService, temp_config_dir: Path, sample_yaml_dict: dict):
        """Test loading existing configuration."""
        (temp_config_dir / "test.yml").write_text(yaml.dump(sample_yaml_dict))

        with patch.object(service, "state") as mock_state:
            mock_state.get.return_value = None
            config: Project = service.load_project("test")
            assert config.metadata
            assert config.metadata.name == "test"
            assert "sample" in config.entities

    def test_load_configuration_not_found(self, service: ProjectService):
        """Test loading non-existent configuration raises error."""
        with patch.object(service, "state") as mock_state:
            mock_state.get.return_value = None
            with pytest.raises(ProjectNotFoundError, match="not found"):
                service.load_project("nonexistent")

    def test_load_configuration_with_yml_extension(self, service: ProjectService, temp_config_dir: Path, sample_yaml_dict: dict):
        """Test loading with .yml extension."""
        (temp_config_dir / "test.yml").write_text(yaml.dump(sample_yaml_dict))
        service.projects_dir = temp_config_dir
        config = service.load_project("test.yml")
        assert config.metadata
        assert config.metadata.name.startswith("test")

    def test_load_configuration_invalid_yaml(self, service: ProjectService, temp_config_dir: Path):
        """Test loading invalid YAML raises error."""
        (temp_config_dir / "invalid.yml").write_text("{ invalid yaml")
        with patch.object(service, "state") as mock_state:
            mock_state.get.return_value = None
            with pytest.raises(InvalidProjectError):
                service.load_project("invalid")

    def test_load_configuration_sets_metadata(self, service: ProjectService, temp_config_dir: Path, sample_yaml_dict: dict):
        """Test load sets file metadata."""
        file_path = temp_config_dir / "test.yml"
        file_path.write_text(yaml.dump(sample_yaml_dict))
        with patch.object(service, "state") as mock_state:
            mock_state.get.return_value = None

            config = service.load_project("test")
            assert config.metadata
            assert config.metadata.file_path == str(file_path)
            assert config.metadata.entity_count == 1

    def test_load_configuration_multiple_entities(self, simple_service: ProjectService, sample_config_file):
        """Test loading valid configuration with multiple entities."""
        config = simple_service.load_project("test_project")

        assert config.metadata.name == "test_project"
        assert len(config.entities) == 2
        assert "sample" in config.entities
        assert "site" in config.entities
        assert config.options["verbose"] is True

    # Save configuration tests

    def test_save_configuration_success(self, service: ProjectService, sample_config: Project):
        """Test saving configuration."""
        result = service.save_project(sample_config, create_backup=False)

        assert result.metadata
        assert result.metadata.name == "test"
        file_path = service.projects_dir / "test.yml"
        assert file_path.exists()

    def test_save_configuration_updates_metadata(self, service: ProjectService, sample_config: Project):
        """Test save updates metadata timestamps."""
        assert sample_config.metadata
        original_modified = sample_config.metadata.modified_at
        config = service.save_project(sample_config, create_backup=False)

        # Modified timestamp should be updated
        assert config.metadata
        assert config.metadata.modified_at >= original_modified

    def test_save_configuration_without_metadata(self, service: ProjectService):
        """Test save without metadata raises error."""
        config = Project(entities={}, options={})

        with pytest.raises(InvalidProjectError, match="must have metadata"):
            service.save_project(config, create_backup=False)

    def test_save_configuration_without_name(self, service: ProjectService):
        """Test save without name raises error."""
        config = Project(
            entities={},
            options={},
            metadata=ProjectMetadata(
                name="",
                description="",
                version="1.0.0",
                file_path="",
                entity_count=0,
                created_at=0,
                modified_at=0,
                is_valid=True,
            ),
        )

        with pytest.raises(InvalidProjectError, match="must have metadata"):
            service.save_project(config, create_backup=False)

    def test_save_configuration_creates_backup(self, service: ProjectService, temp_config_dir: Path, sample_config: Project):
        """Test save with backup option."""
        # Create existing file
        file_path = temp_config_dir / "test.yml"
        file_path.write_text("old content")

        with patch("backend.app.services.YamlService") as mock_yaml:
            mock_yaml.return_value.save = MagicMock()
            service.yaml_service = mock_yaml.return_value

            service.save_project(sample_config, create_backup=True)

            # Verify backup was requested
            mock_yaml.return_value.save.assert_called_once()
            call_kwargs = mock_yaml.return_value.save.call_args[1]
            assert call_kwargs.get("create_backup") is True

    def test_save_configuration_updates_app_state(self, service: ProjectService, sample_config: Project):
        """Test save updates ApplicationState."""
        mock_state = MagicMock()
        service.state = mock_state

        service.save_project(sample_config, create_backup=False)

        mock_state.update.assert_called_once()
        # Verify it was called with a Configuration object
        args = mock_state.update.call_args[0]
        assert len(args) > 0
        assert isinstance(args[0], Project)

    # Create configuration tests

    def test_create_configuration_success(self, service: ProjectService):
        """Test creating new configuration."""
        config = service.create_project("newconfig")

        assert config.metadata
        assert config.metadata.name == "newconfig"
        assert (service.projects_dir / "newconfig.yml").exists()

    def test_create_configuration_with_entities(self, service: ProjectService):
        """Test creating configuration with initial entities."""
        entities = {"entity1": {"source": "table1"}}
        config = service.create_project("newconfig", entities=entities)

        assert "entity1" in config.entities
        assert config.metadata
        assert config.metadata.entity_count == 1

    def test_create_configuration_already_exists(self, service: ProjectService, temp_config_dir: Path):
        """Test creating configuration that already exists raises error."""
        (temp_config_dir / "existing.yml").touch()

        with pytest.raises(ProjectConflictError, match="already exists"):
            service.create_project("existing")

    def test_create_configuration_sets_metadata(self, service: ProjectService):
        """Test create sets proper metadata."""
        config = service.create_project("test")
        assert config.metadata
        assert config.metadata.version == "1.0.0"
        assert config.metadata.entity_count == 0
        assert config.metadata.is_valid is True

    def test_create_configuration_name_ending_in_yml_chars(self, service: ProjectService):
        """Test creating configuration with name ending in 'l', 'y', 'm', or '.' doesn't truncate.

        Regression test for bug where .rstrip('.yml') would remove trailing characters
        that happened to be in the set {'.', 'y', 'm', 'l'}.
        """
        # Test various problematic endings
        test_names = [
            "test_config_manual",  # ends with 'l'
            "data_file_final",  # ends with 'l'
            "my_query",  # ends with 'y'
            "system_memory",  # ends with 'y'
            "algorithm",  # ends with 'm'
            "test.name",  # contains '.'
        ]

        for name in test_names:
            config = service.create_project(name)

            # Verify filename is correct (not truncated)
            expected_file = service.projects_dir / f"{name}.yml"
            assert expected_file.exists(), f"File for '{name}' was truncated to {list(service.projects_dir.glob('*.yml'))}"

            # Verify metadata.name matches
            assert config.metadata
            assert config.metadata.name == name, f"Metadata name '{config.metadata.name}' doesn't match expected '{name}'"

            # Verify we can load it back with correct name
            # Mock state.get to return None so it loads from disk
            with patch.object(service.state, "get", return_value=None):
                loaded = service.load_project(name)
                assert loaded.metadata
                assert loaded.metadata.name == name

            # Clean up for next iteration
            service.delete_project(name)

    # Delete configuration tests

    def test_delete_configuration_success(self, service: ProjectService, temp_config_dir: Path):
        """Test deleting existing configuration."""
        file_path = temp_config_dir / "test.yml"
        file_path.touch()

        service.delete_project("test")
        assert not file_path.exists()

    def test_delete_configuration_not_found(self, service: ProjectService):
        """Test deleting non-existent configuration raises error."""
        with pytest.raises(ProjectNotFoundError, match="not found"):
            service.delete_project("nonexistent")

    def test_delete_configuration_creates_backup(self, service: ProjectService, temp_config_dir: Path):
        """Test delete creates backup before removing file."""
        file_path = temp_config_dir / "test.yml"
        file_path.write_text("content")

        with patch("backend.app.services.project_service.YamlService") as mock_yaml:
            mock_backup = MagicMock()
            mock_yaml.return_value.create_backup = mock_backup
            service.yaml_service = mock_yaml.return_value

            service.delete_project("test")

            mock_backup.assert_called_once_with(file_path)

    # Add entity tests

    def test_add_entity_success(self, service: ProjectService, sample_config: Project):
        """Test adding entity to configuration."""
        entity = Entity(source="new_table", name="new_entity", type="entity", columns=["id", "name"])
        config = service.add_entity(sample_config, "new_entity", entity)

        assert "new_entity" in config.entities
        assert config.entities["new_entity"]["source"] == "new_table"

    def test_add_entity_already_exists(self, service: ProjectService, sample_config: Project):
        """Test adding duplicate entity raises error."""
        entity = Entity(source="table", name="sample", type="entity")

        with pytest.raises(EntityAlreadyExistsError, match="already exists"):
            service.add_entity(sample_config, "sample", entity)

    def test_add_entity_serializes_model(self, service: ProjectService, sample_config: Project):
        """Test entity is serialized as dict."""
        entity = Entity(source="table", name="new", type="entity", columns=["id"])
        config = service.add_entity(sample_config, "new", entity)

        assert isinstance(config.entities["new"], dict)

    # Update entity tests

    def test_update_entity_success(self, service: ProjectService, sample_config: Project):
        """Test updating existing entity."""
        entity = Entity(source="updated_table", name="sample", type="entity", columns=["id", "name", "value"])
        config = service.update_entity(sample_config, "sample", entity)

        assert config.entities["sample"]["source"] == "updated_table"
        assert len(config.entities["sample"]["columns"]) == 3

    def test_update_entity_not_found(self, service: ProjectService, sample_config: Project):
        """Test updating non-existent entity raises error."""
        entity = Entity(source="table", name="new", type="entity", columns=[])

        with pytest.raises(EntityNotFoundError, match="not found"):
            service.update_entity(sample_config, "nonexistent", entity)

    # Delete entity tests

    def test_delete_entity_success(self, service: ProjectService, sample_config: Project):
        """Test deleting entity from configuration."""
        config = service.delete_entity(sample_config, "sample")

        assert "sample" not in config.entities

    def test_delete_entity_not_found(self, service: ProjectService, sample_config: Project):
        """Test deleting non-existent entity raises error."""
        with pytest.raises(EntityNotFoundError, match="not found"):
            service.delete_entity(sample_config, "nonexistent")

    # Get entity tests

    def test_get_entity_success(self, service: ProjectService, sample_config: Project):
        """Test getting entity from configuration."""
        entity = service.get_entity(sample_config, "sample")

        assert entity["source"] == "test_table"
        assert "columns" in entity

    def test_get_entity_not_found(self, service: ProjectService, sample_config: Project):
        """Test getting non-existent entity raises error."""
        with pytest.raises(EntityNotFoundError, match="not found"):
            service.get_entity(sample_config, "nonexistent")

    # Entity operations by name tests

    def test_add_entity_by_name(self, service: ProjectService, temp_config_dir: Path, sample_yaml_dict: dict):
        """Test adding entity by configuration name."""
        (temp_config_dir / "test.yml").write_text(yaml.dump(sample_yaml_dict))

        entity_data = {"source": "new_table", "columns": ["id"]}
        mock_state = MagicMock()
        mock_state.get.return_value = None
        service.state = mock_state

        service.add_entity_by_name("test", "new_entity", entity_data)

        config = service.load_project("test")
        assert "new_entity" in config.entities

    def test_add_entity_by_name_already_exists(self, service: ProjectService, temp_config_dir: Path, sample_yaml_dict: dict):
        """Test adding duplicate entity by name raises error."""
        (temp_config_dir / "test.yml").write_text(yaml.dump(sample_yaml_dict))

        mock_state = MagicMock()
        mock_state.get.return_value = None
        service.state = mock_state

        with pytest.raises(EntityAlreadyExistsError):
            service.add_entity_by_name("test", "sample", {"source": "table"})

    def test_update_entity_by_name(self, service: ProjectService, temp_config_dir: Path, sample_yaml_dict: dict):
        """Test updating entity by configuration name."""
        (temp_config_dir / "test.yml").write_text(yaml.dump(sample_yaml_dict))

        mock_state = MagicMock()
        mock_state.get.return_value = None
        service.state = mock_state

        entity_data = {"source": "updated_table", "columns": ["id", "name"]}
        service.update_entity_by_name("test", "sample", entity_data)

        config = service.load_project("test")
        assert config.entities["sample"]["source"] == "updated_table"

    def test_update_entity_by_name_not_found(self, service: ProjectService, temp_config_dir: Path, sample_yaml_dict: dict):
        """Test updating non-existent entity by name raises error."""
        (temp_config_dir / "test.yml").write_text(yaml.dump(sample_yaml_dict))

        with pytest.raises(EntityNotFoundError):
            service.update_entity_by_name("test", "nonexistent", {"source": "table"})

    def test_delete_entity_by_name(self, service: ProjectService, temp_config_dir: Path, sample_yaml_dict: dict):
        """Test deleting entity by configuration name."""
        (temp_config_dir / "test.yml").write_text(yaml.dump(sample_yaml_dict))

        mock_state = MagicMock()
        mock_state.get.return_value = None
        service.state = mock_state

        service.delete_entity_by_name("test", "sample")

        config = service.load_project("test")
        assert "sample" not in config.entities

    def test_delete_entity_by_name_not_found(self, service: ProjectService, temp_config_dir: Path, sample_yaml_dict: dict):
        """Test deleting non-existent entity by name raises error."""
        (temp_config_dir / "test.yml").write_text(yaml.dump(sample_yaml_dict))

        with pytest.raises(EntityNotFoundError):
            service.delete_entity_by_name("test", "nonexistent")

    def test_get_entity_by_name(self, service: ProjectService, temp_config_dir: Path, sample_yaml_dict: dict):
        """Test getting entity by configuration name."""
        (temp_config_dir / "test.yml").write_text(yaml.dump(sample_yaml_dict))

        mock_state = MagicMock()
        mock_state.get.return_value = None
        service.state = mock_state

        entity = service.get_entity_by_name("test", "sample")
        assert entity["source"] == "test_table"

    def test_get_entity_by_name_not_found(self, service: ProjectService, temp_config_dir: Path, sample_yaml_dict: dict):
        """Test getting non-existent entity by name raises error."""
        (temp_config_dir / "test.yml").write_text(yaml.dump(sample_yaml_dict))

        with pytest.raises(EntityNotFoundError):
            service.get_entity_by_name("test", "nonexistent")

    # Activate configuration tests

    def test_activate_project(self, service: ProjectService, temp_config_dir: Path, sample_yaml_dict: dict):
        """Test activating configuration."""
        (temp_config_dir / "test.yml").write_text(yaml.dump(sample_yaml_dict))

        mock_state = MagicMock()
        mock_state.get.return_value = None
        service.state = mock_state

        config = service.activate_project("test")

        mock_state.activate.assert_called_once()
        assert config.metadata
        assert config.metadata.name.startswith("test")

    def test_activate_project_not_found(self, service: ProjectService):
        """Test activating non-existent configuration raises error."""
        mock_state = MagicMock()
        mock_state.get.return_value = None
        service.state = mock_state

        with pytest.raises(ProjectNotFoundError):
            service.activate_project("nonexistent")

    # Version check tests

    def test_save_with_version_check_success(self, service: ProjectService, sample_config: Project):
        """Test save with matching version."""
        mock_state = MagicMock()
        mock_state.get_active_metadata.return_value = ProjectMetadata(
            name="test",
            description="Test",
            version="1.0.0",
            file_path="test.yml",
            entity_count=0,
            created_at=0,
            modified_at=0,
            is_valid=True,
        )
        service.state = mock_state

        config = service.save_with_version_check(sample_config, "1.0.0", create_backup=False)
        assert config.metadata
        assert config.metadata.name == "test"

    def test_save_with_version_check_conflict(self, service: ProjectService, sample_config: Project):
        """Test save with version mismatch raises conflict error."""
        mock_state = MagicMock()
        mock_state.get_active_metadata.return_value = ProjectMetadata(
            name="test",
            description="Test",
            version="2.0.0",
            file_path="test.yml",
            entity_count=0,
            created_at=0,
            modified_at=0,
            is_valid=True,
        )
        service.state = mock_state

        with pytest.raises(ProjectConflictError, match="modified by another user"):
            service.save_with_version_check(sample_config, "1.0.0")

    # Roundtrip tests

    def test_roundtrip(self, simple_service: ProjectService, sample_config_file):
        """Test load-modify-save-reload cycle."""
        # Load
        config = simple_service.load_project("test_project")
        original_entity_count = len(config.entities)

        # Modify
        entity = Entity(name="new_entity", surrogate_id="new_entity_id", keys=["id"])
        config = simple_service.add_entity(config, "new_entity", entity)

        # Save
        simple_service.save_project(config)

        # Reload
        reloaded = simple_service.load_project("test_project")

        assert len(reloaded.entities) == original_entity_count + 1
        assert "new_entity" in reloaded.entities

    # Singleton instance tests

    def test_get_project_service_singleton(self):
        """Test get_project_service returns singleton instance."""

        with (
            patch("backend.app.core.config.get_settings") as mock_settings,
            patch("backend.app.services.project_service.get_app_state_manager") as mock_state,
        ):
            mock_settings.return_value.projects_dir = Path("/tmp/configs")
            mock_state.return_value.update = MagicMock()

            service1 = get_project_service()
            service2 = get_project_service()

            assert service1 is service2
