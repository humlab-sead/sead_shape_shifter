"""Tests for validation and dependency API endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture
def reset_services():
    """Reset service singletons between tests."""
    from app.services import config_service, dependency_service, validation_service, yaml_service

    config_service._config_service = None
    dependency_service._dependency_service = None
    validation_service._validation_service = None
    yaml_service._yaml_service = None

    yield

    config_service._config_service = None
    dependency_service._dependency_service = None
    validation_service._validation_service = None
    yaml_service._yaml_service = None


@pytest.fixture
def sample_entity_data():
    """Sample entity data for tests."""
    return {"type": "data", "keys": ["id"], "columns": ["name", "value"]}


class TestEntityValidation:
    """Tests for entity validation endpoint."""

    def test_validate_entity(self, tmp_path, monkeypatch, reset_services, sample_entity_data):
        """Test validating specific entity."""
        from app.core.config import settings

        monkeypatch.setattr(settings, "CONFIGURATIONS_DIR", tmp_path)

        # Create config
        client.post(
            "/api/v1/configurations",
            json={"name": "test_config", "entities": {"sample": sample_entity_data}},
        )

        # Validate entity
        response = client.post("/api/v1/configurations/test_config/entities/sample/validate")
        assert response.status_code == 200
        data = response.json()
        assert "is_valid" in data
        assert "errors" in data
        assert "warnings" in data

    def test_validate_nonexistent_entity(
        self, tmp_path, monkeypatch, reset_services, sample_entity_data
    ):
        """Test validating non-existent entity."""
        from app.core.config import settings

        monkeypatch.setattr(settings, "CONFIGURATIONS_DIR", tmp_path)

        # Create config
        client.post(
            "/api/v1/configurations",
            json={"name": "test_config", "entities": {"sample": sample_entity_data}},
        )

        # Validate non-existent entity - returns validation result with no entity-specific errors
        response = client.post(
            "/api/v1/configurations/test_config/entities/nonexistent/validate"
        )
        assert response.status_code == 200
        data = response.json()
        # Since the entity doesn't exist, there are no errors specific to it
        assert "is_valid" in data
        assert "errors" in data

    def test_validate_entity_nonexistent_config(self, tmp_path, monkeypatch, reset_services):
        """Test validating entity in non-existent configuration."""
        from app.core.config import settings

        monkeypatch.setattr(settings, "CONFIGURATIONS_DIR", tmp_path)

        # Validate entity in non-existent config
        response = client.post("/api/v1/configurations/nonexistent/entities/sample/validate")
        assert response.status_code == 404


class TestDependencies:
    """Tests for dependency analysis endpoints."""

    def test_get_dependencies_simple(
        self, tmp_path, monkeypatch, reset_services, sample_entity_data
    ):
        """Test getting dependency graph with simple dependencies."""
        from app.core.config import settings

        monkeypatch.setattr(settings, "CONFIGURATIONS_DIR", tmp_path)

        # Create config with dependencies
        entities = {
            "base": sample_entity_data,
            "derived": {**sample_entity_data, "source": "base"},
        }
        client.post("/api/v1/configurations", json={"name": "test_config", "entities": entities})

        # Get dependencies
        response = client.get("/api/v1/configurations/test_config/dependencies")
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert "edges" in data
        assert "has_cycles" in data
        assert "topological_order" in data
        assert len(data["nodes"]) == 2
        assert len(data["edges"]) == 1

    def test_get_dependencies_no_deps(
        self, tmp_path, monkeypatch, reset_services, sample_entity_data
    ):
        """Test getting dependency graph with no dependencies."""
        from app.core.config import settings

        monkeypatch.setattr(settings, "CONFIGURATIONS_DIR", tmp_path)

        # Create config without dependencies
        entities = {"entity1": sample_entity_data, "entity2": sample_entity_data}
        client.post("/api/v1/configurations", json={"name": "test_config", "entities": entities})

        # Get dependencies
        response = client.get("/api/v1/configurations/test_config/dependencies")
        assert response.status_code == 200
        data = response.json()
        assert len(data["nodes"]) == 2
        assert len(data["edges"]) == 0
        assert data["has_cycles"] is False

    def test_get_dependencies_with_cycles(self, tmp_path, monkeypatch, reset_services):
        """Test getting dependency graph with circular dependencies."""
        from app.core.config import settings

        monkeypatch.setattr(settings, "CONFIGURATIONS_DIR", tmp_path)

        # Create config with circular dependencies
        entities = {
            "entity1": {"type": "data", "keys": ["id"], "source": "entity2"},
            "entity2": {"type": "data", "keys": ["id"], "source": "entity1"},
        }
        client.post("/api/v1/configurations", json={"name": "test_config", "entities": entities})

        # Get dependencies
        response = client.get("/api/v1/configurations/test_config/dependencies")
        assert response.status_code == 200
        data = response.json()
        assert data["has_cycles"] is True
        assert len(data["cycles"]) > 0

    def test_get_dependencies_nonexistent_config(self, tmp_path, monkeypatch, reset_services):
        """Test getting dependencies for non-existent configuration."""
        from app.core.config import settings

        monkeypatch.setattr(settings, "CONFIGURATIONS_DIR", tmp_path)

        # Get dependencies for non-existent config
        response = client.get("/api/v1/configurations/nonexistent/dependencies")
        assert response.status_code == 404


class TestCircularDependencyCheck:
    """Tests for circular dependency check endpoint."""

    def test_check_no_cycles(self, tmp_path, monkeypatch, reset_services, sample_entity_data):
        """Test checking for circular dependencies when none exist."""
        from app.core.config import settings

        monkeypatch.setattr(settings, "CONFIGURATIONS_DIR", tmp_path)

        # Create config without cycles
        entities = {
            "base": sample_entity_data,
            "derived": {**sample_entity_data, "source": "base"},
        }
        client.post("/api/v1/configurations", json={"name": "test_config", "entities": entities})

        # Check dependencies
        response = client.post("/api/v1/configurations/test_config/dependencies/check")
        assert response.status_code == 200
        data = response.json()
        assert data["has_cycles"] is False
        assert data["cycle_count"] == 0
        assert len(data["cycles"]) == 0

    def test_check_with_cycles(self, tmp_path, monkeypatch, reset_services):
        """Test checking for circular dependencies when they exist."""
        from app.core.config import settings

        monkeypatch.setattr(settings, "CONFIGURATIONS_DIR", tmp_path)

        # Create config with circular dependencies
        entities = {
            "entity1": {"type": "data", "keys": ["id"], "source": "entity2"},
            "entity2": {"type": "data", "keys": ["id"], "source": "entity1"},
        }
        client.post("/api/v1/configurations", json={"name": "test_config", "entities": entities})

        # Check dependencies
        response = client.post("/api/v1/configurations/test_config/dependencies/check")
        assert response.status_code == 200
        data = response.json()
        assert data["has_cycles"] is True
        assert data["cycle_count"] > 0
        assert len(data["cycles"]) > 0

    def test_check_dependencies_nonexistent_config(self, tmp_path, monkeypatch, reset_services):
        """Test checking dependencies for non-existent configuration."""
        from app.core.config import settings

        monkeypatch.setattr(settings, "CONFIGURATIONS_DIR", tmp_path)

        # Check dependencies for non-existent config
        response = client.post("/api/v1/configurations/nonexistent/dependencies/check")
        assert response.status_code == 404
