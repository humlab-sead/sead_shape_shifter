"""Tests for configuration API endpoints."""

import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import settings
from backend.app.main import app
from backend.app.services import config_service, validation_service, yaml_service

# pylint: disable=redefined-outer-name, unused-argument

client = TestClient(app)


@pytest.fixture
def sample_config_data():
    """Sample configuration data for tests."""
    return {
        "entities": {
            "sample": {
                "type": "data",
                "keys": ["sample_id"],
                "columns": ["name", "value"],
            }
        }
    }


@pytest.fixture
def reset_services():
    """Reset service singletons between tests."""

    config_service._config_service = None
    validation_service._validation_service = None
    yaml_service._yaml_service = None

    yield

    # Clear again after test
    config_service._config_service = None
    validation_service._validation_service = None
    yaml_service._yaml_service = None


class TestConfigurationsList:
    """Tests for listing configurations."""

    def test_list_configurations_empty(self, tmp_path, monkeypatch, reset_services):
        """Test listing when no configurations exist."""

        monkeypatch.setattr(settings, "CONFIGURATIONS_DIR", tmp_path)

        response = client.get("/api/v1/configurations")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_configurations(self, tmp_path, monkeypatch, reset_services, sample_config_data):
        """Test listing configurations."""

        monkeypatch.setattr(settings, "CONFIGURATIONS_DIR", tmp_path)

        # Create test config via API
        create_response = client.post("/api/v1/configurations", json={"name": "test_config", "entities": sample_config_data["entities"]})
        assert create_response.status_code == 201

        # List configs
        response = client.get("/api/v1/configurations")
        assert response.status_code == 200
        configs = response.json()
        assert len(configs) == 1
        assert configs[0]["name"] == "test_config"
        assert configs[0]["entity_count"] == 1


class TestConfigurationsGet:
    """Tests for getting configuration."""

    def test_get_configuration(self, tmp_path, monkeypatch, reset_services, sample_config_data):
        """Test getting existing configuration."""

        monkeypatch.setattr(settings, "CONFIGURATIONS_DIR", tmp_path)

        # Create config
        client.post("/api/v1/configurations", json={"name": "test_config", "entities": sample_config_data["entities"]})

        # Get config
        response = client.get("/api/v1/configurations/test_config")
        assert response.status_code == 200
        data = response.json()
        assert data["metadata"]["name"] == "test_config"
        assert "sample" in data["entities"]

    def test_get_nonexistent_configuration(self, tmp_path, monkeypatch, reset_services):
        """Test getting non-existent configuration returns 404."""

        monkeypatch.setattr(settings, "CONFIGURATIONS_DIR", tmp_path)

        response = client.get("/api/v1/configurations/nonexistent")
        assert response.status_code == 404


class TestConfigurationsCreate:
    """Tests for creating configurations."""

    def test_create_configuration(self, tmp_path, monkeypatch, reset_services, sample_config_data):
        """Test creating new configuration."""

        monkeypatch.setattr(settings, "CONFIGURATIONS_DIR", tmp_path)

        response = client.post("/api/v1/configurations", json={"name": "new_config", "entities": sample_config_data["entities"]})

        assert response.status_code == 201
        data = response.json()
        assert data["metadata"]["name"] == "new_config"
        assert data["metadata"]["entity_count"] == 1

    def test_create_duplicate_configuration(self, tmp_path, monkeypatch, reset_services, sample_config_data):
        """Test creating duplicate configuration returns 400."""

        monkeypatch.setattr(settings, "CONFIGURATIONS_DIR", tmp_path)

        # Create first config
        client.post("/api/v1/configurations", json={"name": "test_config", "entities": sample_config_data["entities"]})

        # Try to create duplicate
        response = client.post("/api/v1/configurations", json={"name": "test_config", "entities": sample_config_data["entities"]})
        assert response.status_code == 400


class TestConfigurationsUpdate:
    """Tests for updating configurations."""

    def test_update_configuration(self, tmp_path, monkeypatch, reset_services, sample_config_data):
        """Test updating existing configuration (options only, not entities)."""

        monkeypatch.setattr(settings, "CONFIGURATIONS_DIR", tmp_path)

        # Create config
        client.post("/api/v1/configurations", json={"name": "test_config", "entities": sample_config_data["entities"]})

        # Update config options (entities are ignored by update endpoint)
        updated_options = {"some_option": "value", "another_option": 123}
        response = client.put("/api/v1/configurations/test_config", json={"entities": {}, "options": updated_options})

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

        monkeypatch.setattr(settings, "CONFIGURATIONS_DIR", tmp_path)

        response = client.put(
            "/api/v1/configurations/nonexistent",
            json={"entities": {"sample": {"type": "data"}}, "options": {}},
        )
        assert response.status_code == 404


class TestConfigurationsDelete:
    """Tests for deleting configurations."""

    def test_delete_configuration(self, tmp_path, monkeypatch, reset_services, sample_config_data):
        """Test deleting configuration."""

        monkeypatch.setattr(settings, "CONFIGURATIONS_DIR", tmp_path)

        # Create config
        client.post("/api/v1/configurations", json={"name": "test_config", "entities": sample_config_data["entities"]})

        # Delete config
        response = client.delete("/api/v1/configurations/test_config")
        assert response.status_code == 204

        # Verify deleted
        get_response = client.get("/api/v1/configurations/test_config")
        assert get_response.status_code == 404

    def test_delete_nonexistent_configuration(self, tmp_path, monkeypatch, reset_services):
        """Test deleting non-existent configuration returns 404."""

        monkeypatch.setattr(settings, "CONFIGURATIONS_DIR", tmp_path)

        response = client.delete("/api/v1/configurations/nonexistent")
        assert response.status_code == 404


class TestConfigurationsValidate:
    """Tests for configuration validation."""

    def test_validate_valid_configuration(self, tmp_path, monkeypatch, reset_services, sample_config_data):
        """Test validating valid configuration."""

        monkeypatch.setattr(settings, "CONFIGURATIONS_DIR", tmp_path)

        # Create config
        client.post("/api/v1/configurations", json={"name": "test_config", "entities": sample_config_data["entities"]})

        # Validate
        response = client.post("/api/v1/configurations/test_config/validate")
        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] is True
        assert data["error_count"] == 0

    def test_validate_invalid_configuration(self, tmp_path, monkeypatch, reset_services):
        """Test validating invalid configuration."""

        # Use unique name to avoid collision with valid test
        config_name = "invalid_test_config"
        monkeypatch.setattr(settings, "CONFIGURATIONS_DIR", tmp_path)

        # Create config with invalid entity (missing keys)
        invalid_entities = {"sample": {"type": "data"}}
        client.post("/api/v1/configurations", json={"name": config_name, "entities": invalid_entities})

        # Validate
        response = client.post(f"/api/v1/configurations/{config_name}/validate")
        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] is False
        assert data["error_count"] > 0


class TestConfigurationsBackups:
    """Tests for backup operations."""

    def test_list_backups(self, tmp_path, monkeypatch, reset_services, sample_config_data):
        """Test listing backups."""

        monkeypatch.setattr(settings, "CONFIGURATIONS_DIR", tmp_path)
        monkeypatch.setattr(settings, "BACKUPS_DIR", tmp_path / "backups")

        # Create config
        client.post("/api/v1/configurations", json={"name": "test_config", "entities": sample_config_data["entities"]})

        # Update to create backup
        updated_entities = {"sample": {"type": "data", "keys": ["id"], "columns": ["name"]}}
        client.put("/api/v1/configurations/test_config", json={"entities": updated_entities, "options": {}})

        # List backups
        response = client.get("/api/v1/configurations/test_config/backups")
        assert response.status_code == 200
        backups = response.json()
        assert len(backups) >= 1
        assert "test_config" in backups[0]["file_name"]

    def test_restore_backup(self, reset_services, tmp_path, monkeypatch, sample_config_data):
        """Test restoring from backup."""

        monkeypatch.setattr(settings, "CONFIGURATIONS_DIR", tmp_path)
        monkeypatch.setattr(settings, "BACKUPS_DIR", tmp_path / "backups")

        # Create config
        create_response = client.post("/api/v1/configurations", json={"name": "test_config", "entities": sample_config_data["entities"]})
        assert create_response.status_code == 201, f"Failed to create config: {create_response.json()}"
        original_data = create_response.json()

        # Update to create backup
        updated_entities = {"sample": {"type": "data", "keys": ["id"], "columns": ["modified"]}}
        client.put("/api/v1/configurations/test_config", json={"entities": updated_entities, "options": {}})

        # Get backup path
        backups_response = client.get("/api/v1/configurations/test_config/backups")
        backups = backups_response.json()
        backup_path = backups[0]["file_path"]

        # Restore
        response = client.post("/api/v1/configurations/test_config/restore", json={"backup_path": backup_path})
        assert response.status_code == 200
        restored_data = response.json()

        # Verify restoration - both should be Configuration models with same structure
        assert "entities" in original_data
        assert "entities" in restored_data
        assert "sample" in original_data["entities"]
        assert "sample" in restored_data["entities"]
        assert restored_data["entities"]["sample"]["columns"] == original_data["entities"]["sample"]["columns"]
