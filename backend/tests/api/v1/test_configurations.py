"""Tests for configuration API endpoints."""

import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import settings
from backend.app.main import app
from backend.app.services import project_service, validation_service, yaml_service

# pylint: disable=redefined-outer-name, unused-argument

client = TestClient(app)


@pytest.fixture
def sample_config_data():
    """Sample configuration data for tests."""
    return {
        "entities": {
            "sample": {
                "type": "entity",
                "keys": ["sample_id"],
                "columns": ["name", "value"],
            }
        }
    }


@pytest.fixture
def reset_services():
    """Reset service singletons between tests."""

    project_service._project_service = None
    validation_service._validation_service = None
    yaml_service._yaml_service = None

    yield

    # Clear again after test
    project_service._project_service = None
    validation_service._validation_service = None
    yaml_service._yaml_service = None


class TestConfigurationsList:
    """Tests for listing configurations."""

    def test_list_configurations_empty(self, tmp_path, monkeypatch, reset_services):
        """Test listing when no configurations exist."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        response = client.get("/api/v1/projects")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_configurations(self, tmp_path, monkeypatch, reset_services, sample_config_data):
        """Test listing configurations."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create test config via API
        create_response = client.post("/api/v1/projects", json={"name": "test_project", "entities": sample_config_data["entities"]})
        assert create_response.status_code == 201

        # List configs
        response = client.get("/api/v1/projects")
        assert response.status_code == 200
        configs = response.json()
        assert len(configs) == 1
        assert configs[0]["name"] == "test_project"
        assert configs[0]["entity_count"] == 1


class TestConfigurationsGet:
    """Tests for getting configuration."""

    def test_get_configuration(self, tmp_path, monkeypatch, reset_services, sample_config_data):
        """Test getting existing configuration."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create config
        client.post("/api/v1/projects", json={"name": "test_project", "entities": sample_config_data["entities"]})

        # Get config
        response = client.get("/api/v1/projects/test_project")
        assert response.status_code == 200
        data = response.json()
        assert data["metadata"]["name"] == "test_project"
        assert "sample" in data["entities"]

    def test_get_nonexistent_configuration(self, tmp_path, monkeypatch, reset_services):
        """Test getting non-existent configuration returns 404."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        response = client.get("/api/v1/projects/nonexistent")
        assert response.status_code == 404


class TestConfigurationsCreate:
    """Tests for creating configurations."""

    def test_create_configuration(self, tmp_path, monkeypatch, reset_services, sample_config_data):
        """Test creating new configuration."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        response = client.post("/api/v1/projects", json={"name": "new_config", "entities": sample_config_data["entities"]})

        assert response.status_code == 201
        data = response.json()
        assert data["metadata"]["name"] == "new_config"
        assert data["metadata"]["entity_count"] == 1

    def test_create_duplicate_configuration(self, tmp_path, monkeypatch, reset_services, sample_config_data):
        """Test creating duplicate configuration returns 409 Conflict."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create first config
        client.post("/api/v1/projects", json={"name": "test_project", "entities": sample_config_data["entities"]})

        # Try to create duplicate
        response = client.post("/api/v1/projects", json={"name": "test_project", "entities": sample_config_data["entities"]})
        assert response.status_code == 409


class TestConfigurationsUpdate:
    """Tests for updating configurations."""

    def test_update_configuration(self, tmp_path, monkeypatch, reset_services, sample_config_data):
        """Test updating existing configuration (options only, not entities)."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create config
        client.post("/api/v1/projects", json={"name": "test_project", "entities": sample_config_data["entities"]})

        # Update config options (entities are ignored by update endpoint)
        updated_options = {"some_option": "value", "another_option": 123}
        response = client.put("/api/v1/projects/test_project", json={"entities": {}, "options": updated_options})

        assert response.status_code == 200
        data = response.json()
        # Verify entities are preserved from disk
        assert "sample" in data["entities"]
        assert data["entities"]["sample"]["columns"] == ["name", "value"]
        # Verify options were updated
        assert data["options"]["some_option"] == "value"
        assert data["options"]["another_option"] == 123

    def test_update_nonexistent_configuration(self, tmp_path, monkeypatch, reset_services):
        """Test updating non-existent configuration returns 404."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        response = client.put(
            "/api/v1/projects/nonexistent",
            json={"entities": {"sample": {"type": "entity"}}, "options": {}},
        )
        assert response.status_code == 404

    def test_update_metadata(self, tmp_path, monkeypatch, reset_services, sample_config_data):
        """Test updating configuration metadata."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create config
        client.post("/api/v1/projects", json={"name": "test_project", "entities": sample_config_data["entities"]})

        # Update metadata
        metadata_update = {
            "description": "Updated description",
            "version": "2.0.1",
            "default_entity": "sample",
        }
        response = client.patch("/api/v1/projects/test_project/metadata", json=metadata_update)

        assert response.status_code == 200
        data = response.json()
        assert data["metadata"]["description"] == "Updated description"
        assert data["metadata"]["version"] == "2.0.1"
        assert data["metadata"]["default_entity"] == "sample"
        # Verify entities are preserved
        assert "sample" in data["entities"]

    def test_update_metadata_rename(self, tmp_path, monkeypatch, reset_services, sample_config_data):
        """Test that renaming via metadata update is ignored (filename is source of truth)."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create config
        client.post("/api/v1/projects", json={"name": "old_name", "entities": sample_config_data["entities"]})

        # Attempt rename via metadata (should be ignored)
        metadata_update = {"name": "new_name"}
        response = client.patch("/api/v1/projects/old_name/metadata", json=metadata_update)

        assert response.status_code == 200
        data = response.json()
        # Name should remain old_name (filename is source of truth)
        assert data["metadata"]["name"] == "old_name"

        # Verify old name still exists
        get_old = client.get("/api/v1/projects/old_name")
        assert get_old.status_code == 200

        # Verify new name was NOT created
        get_new = client.get("/api/v1/projects/new_name")
        assert get_new.status_code == 404

    def test_update_metadata_rename_conflict(self, tmp_path, monkeypatch, reset_services, sample_config_data):
        """Test that attempting to rename via metadata doesn't cause conflicts (ignored)."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create two configs
        client.post("/api/v1/projects", json={"name": "config1", "entities": sample_config_data["entities"]})
        client.post("/api/v1/projects", json={"name": "config2", "entities": sample_config_data["entities"]})

        # Try to rename config1 to config2 (should be ignored, no conflict)
        metadata_update = {"name": "config2"}
        response = client.patch("/api/v1/projects/config1/metadata", json=metadata_update)

        # Should succeed (200) because rename is ignored
        assert response.status_code == 200
        # config1 name should remain unchanged
        data = response.json()
        assert data["metadata"]["name"] == "config1"


class TestConfigurationsDelete:
    """Tests for deleting configurations."""

    def test_delete_configuration(self, tmp_path, monkeypatch, reset_services, sample_config_data):
        """Test deleting configuration."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create config
        client.post("/api/v1/projects", json={"name": "test_project", "entities": sample_config_data["entities"]})

        # Delete config
        response = client.delete("/api/v1/projects/test_project")
        assert response.status_code == 204

        # Verify deleted
        get_response = client.get("/api/v1/projects/test_project")
        assert get_response.status_code == 404

    def test_delete_nonexistent_configuration(self, tmp_path, monkeypatch, reset_services):
        """Test deleting non-existent configuration returns 404."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        response = client.delete("/api/v1/projects/nonexistent")
        assert response.status_code == 404


class TestConfigurationsValidate:
    """Tests for configuration validation."""

    def test_validate_valid_configuration(self, tmp_path, monkeypatch, reset_services):
        """Test validating valid configuration."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create a fully valid configuration with all required fields
        valid_entities = {
            "sample": {"type": "entity", "keys": ["sample_id"], "columns": ["name", "value"], "depends_on": []}  # Required field
        }

        payload = {"name": "test_project", "entities": valid_entities}

        # Create config
        client.post("/api/v1/projects", json=payload)

        # Validate
        response = client.post("/api/v1/projects/test_project/validate")
        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] is True
        assert data["error_count"] == 0

    def test_validate_invalid_configuration(self, tmp_path, monkeypatch, reset_services):
        """Test validating invalid configuration."""

        # Use unique name to avoid collision with valid test
        project_name = "invalid_test_project"
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create config with invalid entity (missing keys)
        invalid_entities = {"sample": {"type": "entity"}}
        client.post("/api/v1/projects", json={"name": project_name, "entities": invalid_entities})

        # Validate
        response = client.post(f"/api/v1/projects/{project_name}/validate")
        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] is False
        assert data["error_count"] > 0

    def test_validate_configuration_resolves_include_relative_to_project(self, tmp_path, monkeypatch, reset_services):
        """Test @include resolves relative to the project YAML file path."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        valid_entities = {"sample": {"type": "entity", "keys": ["sample_id"], "columns": ["name"], "depends_on": []}}

        payload = {
            "name": "test_project",
            "entities": valid_entities,
            "options": {
                "data_sources": {
                    "digidiggie-options": "@include: digidiggie-options.yml",
                }
            },
        }

        client.post("/api/v1/projects", json=payload)

        # Create the included file next to the project YAML.
        (tmp_path / "digidiggie-options.yml").write_text(
            "driver: ucanaccess\noptions:\n  filename: ./projects/digidiggie_dev.accdb\n  ucanaccess_dir: lib/ucanaccess\n",
            encoding="utf-8",
        )

        response = client.post("/api/v1/projects/test_project/validate")
        assert response.status_code == 200
        data = response.json()

        # Ensure validation did not fail due to missing include file.
        assert not any("configuration file not found" in e["message"].lower() for e in data.get("errors", []))

    def test_validate_configuration_missing_include_returns_error_result(self, tmp_path, monkeypatch, reset_services):
        """Test missing @include file returns ValidationResult (not HTTP 500)."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        valid_entities = {"sample": {"type": "entity", "keys": ["sample_id"], "columns": ["name"], "depends_on": []}}

        # Create project (create endpoint does not accept `options`)
        client.post("/api/v1/projects", json={"name": "test_project", "entities": valid_entities})

        # Update options (PUT endpoint updates options only; entities are ignored but required by schema)
        client.put(
            "/api/v1/projects/test_project",
            json={
                "entities": {},
                "options": {"data_sources": {"missing": "@include: definitely-missing.yml"}},
            },
        )

        response = client.post("/api/v1/projects/test_project/validate")
        assert response.status_code == 200

        data = response.json()
        assert data["is_valid"] is False
        assert data["error_count"] > 0
        assert any("configuration file not found" in e["message"].lower() for e in data.get("errors", []))


class TestConfigurationsBackups:
    """Tests for backup operations."""

    def test_list_backups(self, tmp_path, monkeypatch, reset_services, sample_config_data):
        """Test listing backups."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        monkeypatch.setattr(settings, "BACKUPS_DIR", tmp_path / "backups")

        # Create config
        client.post("/api/v1/projects", json={"name": "test_project", "entities": sample_config_data["entities"]})

        # Update to create backup
        updated_entities = {"sample": {"type": "entity", "keys": ["id"], "columns": ["name"]}}
        client.put("/api/v1/projects/test_project", json={"entities": updated_entities, "options": {}})

        # List backups
        response = client.get("/api/v1/projects/test_project/backups")
        assert response.status_code == 200
        backups = response.json()
        assert len(backups) >= 1
        assert "test_project" in backups[0]["file_name"]

    def test_restore_backup(self, reset_services, tmp_path, monkeypatch, sample_config_data):
        """Test restoring from backup."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        monkeypatch.setattr(settings, "BACKUPS_DIR", tmp_path / "backups")

        # Create config
        create_response = client.post("/api/v1/projects", json={"name": "test_project", "entities": sample_config_data["entities"]})
        assert create_response.status_code == 201, f"Failed to create config: {create_response.json()}"
        original_data = create_response.json()

        # Update to create backup
        updated_entities = {"sample": {"type": "entity", "keys": ["id"], "columns": ["modified"]}}
        client.put("/api/v1/projects/test_project", json={"entities": updated_entities, "options": {}})

        # Get backup path
        backups_response = client.get("/api/v1/projects/test_project/backups")
        backups = backups_response.json()
        backup_path = backups[0]["file_path"]

        # Restore
        response = client.post("/api/v1/projects/test_project/restore", json={"backup_path": backup_path})
        assert response.status_code == 200
        restored_data = response.json()

        # Verify restoration - both should be Configuration models with same structure
        assert "entities" in original_data
        assert "entities" in restored_data
        assert "sample" in original_data["entities"]
        assert "sample" in restored_data["entities"]
        assert restored_data["entities"]["sample"]["columns"] == original_data["entities"]["sample"]["columns"]
