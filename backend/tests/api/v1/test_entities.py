"""Tests for entity API endpoints."""

import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import settings
from backend.app.main import app
from backend.app.services import project_service, validation_service, yaml_service

client = TestClient(app)

# pylint: disable=redefined-outer-name, unused-argument


@pytest.fixture
def sample_entity_data():
    """Sample entity data for tests."""
    return {"type": "data", "keys": ["id"], "columns": ["name", "value"]}


@pytest.fixture
def reset_services():
    """Reset service singletons between tests."""
    # Clear service instances BEFORE each test

    project_service._project_service = None
    validation_service._validation_service = None
    yaml_service._yaml_service = None

    yield

    # Clear again after test
    project_service._project_service = None
    validation_service._validation_service = None
    yaml_service._yaml_service = None


class TestEntitiesList:
    """Tests for listing entities."""

    def test_list_entities(self, tmp_path, monkeypatch, reset_services, sample_entity_data):
        """Test listing entities in configuration."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create config with entities
        client.post(
            "/api/v1/projects",
            json={
                "name": "test_project",
                "entities": {"entity1": sample_entity_data, "entity2": sample_entity_data},
            },
        )

        # List entities
        response = client.get("/api/v1/projects/test_project/entities")
        assert response.status_code == 200
        entities = response.json()
        assert len(entities) == 2
        assert any(e["name"] == "entity1" for e in entities)
        assert any(e["name"] == "entity2" for e in entities)

    def test_list_entities_empty(self, tmp_path, monkeypatch, reset_services):
        """Test listing entities in empty configuration."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create empty config
        client.post("/api/v1/projects", json={"name": "test_project", "entities": {}})

        # List entities
        response = client.get("/api/v1/projects/test_project/entities")
        assert response.status_code == 200
        entities = response.json()
        assert len(entities) == 0

    def test_list_entities_nonexistent_config(self, tmp_path, monkeypatch, reset_services):
        """Test listing entities in non-existent configuration."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        response = client.get("/api/v1/projects/nonexistent/entities")
        assert response.status_code == 404


class TestEntitiesGet:
    """Tests for getting specific entity."""

    def test_get_entity(self, tmp_path, monkeypatch, reset_services, sample_entity_data):
        """Test getting specific entity."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create config with entity
        client.post(
            "/api/v1/projects",
            json={"name": "test_project", "entities": {"test_entity": sample_entity_data}},
        )

        # Get entity
        response = client.get("/api/v1/projects/test_project/entities/test_entity")
        assert response.status_code == 200
        entity = response.json()
        assert entity["name"] == "test_entity"
        assert entity["entity_data"]["type"] == "data"
        assert entity["entity_data"]["keys"] == ["id"]

    def test_get_nonexistent_entity(self, tmp_path, monkeypatch, reset_services):
        """Test getting non-existent entity."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create empty config
        client.post("/api/v1/projects", json={"name": "test_project", "entities": {}})

        # Try to get non-existent entity
        response = client.get("/api/v1/projects/test_project/entities/nonexistent")
        assert response.status_code == 404


class TestEntitiesCreate:
    """Tests for creating entities."""

    def test_create_entity(self, tmp_path, monkeypatch, reset_services, sample_entity_data):
        """Test creating new entity."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create config
        client.post("/api/v1/projects", json={"name": "test_project", "entities": {}})

        # Add entity
        response = client.post(
            "/api/v1/projects/test_project/entities",
            json={"name": "new_entity", "entity_data": sample_entity_data},
        )
        assert response.status_code == 201
        entity = response.json()
        assert entity["name"] == "new_entity"
        assert entity["entity_data"]["type"] == "data"

        # Verify entity was added
        get_response = client.get("/api/v1/projects/test_project/entities/new_entity")
        assert get_response.status_code == 200

    def test_create_duplicate_entity(self, tmp_path, monkeypatch, reset_services, sample_entity_data):
        """Test creating duplicate entity returns 409 Conflict."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create config with entity
        client.post(
            "/api/v1/projects",
            json={"name": "test_project", "entities": {"existing": sample_entity_data}},
        )

        # Try to add duplicate entity
        response = client.post(
            "/api/v1/projects/test_project/entities",
            json={"name": "existing", "entity_data": sample_entity_data},
        )
        assert response.status_code == 409

    def test_create_entity_nonexistent_config(self, tmp_path, monkeypatch, reset_services, sample_entity_data):
        """Test creating entity in non-existent configuration fails."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        response = client.post(
            "/api/v1/projects/nonexistent/entities",
            json={"name": "entity", "entity_data": sample_entity_data},
        )
        assert response.status_code == 404


class TestEntitiesUpdate:
    """Tests for updating entities."""

    def test_update_entity(self, tmp_path, monkeypatch, reset_services, sample_entity_data):
        """Test updating existing entity."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create config with entity
        client.post(
            "/api/v1/projects",
            json={"name": "test_project", "entities": {"test_entity": sample_entity_data}},
        )

        # Update entity
        updated_data = {"type": "data", "keys": ["id"], "columns": ["updated", "fields"]}
        response = client.put(
            "/api/v1/projects/test_project/entities/test_entity",
            json={"entity_data": updated_data},
        )
        assert response.status_code == 200
        entity = response.json()
        assert entity["entity_data"]["columns"] == ["updated", "fields"]

        # Verify update
        get_response = client.get("/api/v1/projects/test_project/entities/test_entity")
        assert get_response.json()["entity_data"]["columns"] == ["updated", "fields"]

    def test_update_nonexistent_entity(self, tmp_path, monkeypatch, reset_services, sample_entity_data):
        """Test updating non-existent entity fails."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create empty config
        client.post("/api/v1/projects", json={"name": "test_project", "entities": {}})

        # Try to update non-existent entity
        response = client.put(
            "/api/v1/projects/test_project/entities/nonexistent",
            json={"entity_data": sample_entity_data},
        )
        assert response.status_code == 404


class TestEntitiesDelete:
    """Tests for deleting entities."""

    def test_delete_entity(self, tmp_path, monkeypatch, reset_services, sample_entity_data):
        """Test deleting entity."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create config with entity
        client.post(
            "/api/v1/projects",
            json={"name": "test_project", "entities": {"test_entity": sample_entity_data}},
        )

        # Delete entity
        response = client.delete("/api/v1/projects/test_project/entities/test_entity")
        assert response.status_code == 204

        # Verify deletion
        get_response = client.get("/api/v1/projects/test_project/entities/test_entity")
        assert get_response.status_code == 404

    def test_delete_nonexistent_entity(self, tmp_path, monkeypatch, reset_services):
        """Test deleting non-existent entity fails."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create empty config
        client.post("/api/v1/projects", json={"name": "test_project", "entities": {}})

        # Try to delete non-existent entity
        response = client.delete("/api/v1/projects/test_project/entities/nonexistent")
        assert response.status_code == 404
