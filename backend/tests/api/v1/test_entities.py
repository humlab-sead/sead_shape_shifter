"""Tests for entity API endpoints."""

import pandas as pd
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
    return {"type": "entity", "keys": ["id"], "columns": ["name", "value"]}


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
        assert entity["entity_data"]["type"] == "entity"
        assert entity["entity_data"]["keys"] == ["id"]

    def test_get_nonexistent_entity(self, tmp_path, monkeypatch, reset_services):
        """Test getting non-existent entity."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create empty config
        client.post("/api/v1/projects", json={"name": "test_project", "entities": {}})

        # Try to get non-existent entity
        response = client.get("/api/v1/projects/test_project/entities/nonexistent")
        assert response.status_code == 404

    def test_get_fixed_entity_includes_authoritative_fixed_schema(self, tmp_path, monkeypatch, reset_services):
        """Fixed entities should expose backend-owned schema metadata."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        entity_data = {
            "type": "fixed",
            "public_id": "location_id",
            "keys": ["name"],
            "columns": ["system_id", "location_id", "name", "country"],
            "values": [[1, 100, "Uppsala", "Sweden"]],
        }

        client.post(
            "/api/v1/projects",
            json={"name": "test_project", "entities": {"location": entity_data}},
        )

        response = client.get("/api/v1/projects/test_project/entities/location")
        assert response.status_code == 200
        payload = response.json()
        assert payload["fixed_schema"] == {
            "full_columns": ["system_id", "location_id", "name", "country"],
            "editable_columns": ["country"],
            "identity_columns": ["system_id", "location_id"],
            "key_columns": ["name"],
            "order_source": "stored",
        }


class TestFixedSchemaDerivation:
    """Tests for derived fixed-schema metadata."""

    def test_create_fixed_entity_derives_schema_when_identity_columns_not_stored(self, tmp_path, monkeypatch, reset_services):
        """Backend should derive full fixed schema when only editable columns are stored."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        client.post("/api/v1/projects", json={"name": "test_project", "entities": {}})

        entity_data = {
            "type": "fixed",
            "public_id": "feature_type_id",
            "keys": ["name"],
            "columns": ["description"],
            "values": [],
        }

        response = client.post(
            "/api/v1/projects/test_project/entities",
            json={"name": "feature_type", "entity_data": entity_data},
        )
        assert response.status_code == 201
        payload = response.json()
        assert payload["fixed_schema"] == {
            "full_columns": ["system_id", "feature_type_id", "name", "description"],
            "editable_columns": ["description"],
            "identity_columns": ["system_id", "feature_type_id"],
            "key_columns": ["name"],
            "order_source": "derived",
        }


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
        assert entity["entity_data"]["type"] == "entity"

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
        updated_data = {"type": "entity", "keys": ["id"], "columns": ["updated", "fields"]}
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


class TestEntityValues:
    """Tests for entity external values endpoints."""

    def test_get_entity_values_parquet(self, tmp_path, monkeypatch, reset_services):
        """Test getting entity values from parquet file."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create project folder structure
        project_folder = tmp_path / "test_project"
        project_folder.mkdir()
        materialized_folder = project_folder / "materialized"
        materialized_folder.mkdir()

        # Create parquet file with test data
        df = pd.DataFrame({"id": [1, 2, 3], "name": ["A", "B", "C"], "value": [10, 20, 30]})
        parquet_file = materialized_folder / "test_entity.parquet"
        df.to_parquet(parquet_file, index=False)

        # Create project with entity that has @load: directive
        entity_data = {
            "type": "fixed",
            "columns": ["id", "name", "value"],
            "values": "@load:materialized/test_entity.parquet",
            "public_id": "id",
            "keys": ["id"],
        }
        client.post(
            "/api/v1/projects",
            json={"name": "test_project", "entities": {"test_entity": entity_data}},
        )

        # Get entity values
        response = client.get("/api/v1/projects/test_project/entities/test_entity/values")
        assert response.status_code == 200

        data = response.json()
        assert data["columns"] == ["id", "name", "value"]
        assert data["row_count"] == 3
        assert data["format"] == "parquet"
        assert data["values"] == [[1, "A", 10], [2, "B", 20], [3, "C", 30]]

    def test_get_entity_values_csv(self, tmp_path, monkeypatch, reset_services):
        """Test getting entity values from CSV file."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create project folder structure
        project_folder = tmp_path / "test_project"
        project_folder.mkdir()
        materialized_folder = project_folder / "materialized"
        materialized_folder.mkdir()

        # Create CSV file with test data
        df = pd.DataFrame({"id": [1, 2], "name": ["X", "Y"]})
        csv_file = materialized_folder / "test_entity.csv"
        df.to_csv(csv_file, index=False)

        # Create project with entity that has @load: directive
        entity_data = {
            "type": "fixed",
            "columns": ["id", "name"],
            "values": "@load:materialized/test_entity.csv",
            "public_id": "id",
            "keys": ["id"],
        }
        client.post(
            "/api/v1/projects",
            json={"name": "test_project", "entities": {"test_entity": entity_data}},
        )

        # Get entity values
        response = client.get("/api/v1/projects/test_project/entities/test_entity/values")
        assert response.status_code == 200

        data = response.json()
        assert data["columns"] == ["id", "name"]
        assert data["row_count"] == 2
        assert data["format"] == "csv"

    def test_get_entity_values_no_load_directive(self, tmp_path, monkeypatch, reset_services):
        """Test error when entity has no @load: directive."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create project with entity that has inline values
        entity_data = {"type": "fixed", "columns": ["id", "name"], "values": [[1, "A"], [2, "B"]], "public_id": "id", "keys": ["id"]}
        client.post(
            "/api/v1/projects",
            json={"name": "test_project", "entities": {"test_entity": entity_data}},
        )

        # Try to get entity values
        response = client.get("/api/v1/projects/test_project/entities/test_entity/values")
        assert response.status_code == 422
        assert "does not have @load: directive" in response.json()["detail"]

    def test_update_entity_values(self, tmp_path, monkeypatch, reset_services):
        """Test updating fixed entity values with authoritative columns."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create project folder structure
        project_folder = tmp_path / "test_project"
        project_folder.mkdir()
        materialized_folder = project_folder / "materialized"
        materialized_folder.mkdir()

        # Create project with entity that has @load: directive
        entity_data = {
            "type": "fixed",
            "columns": ["id", "name"],
            "values": "@load:materialized/test_entity.parquet",
            "public_id": "id",
            "keys": ["id"],
        }
        client.post(
            "/api/v1/projects",
            json={"name": "test_project", "entities": {"test_entity": entity_data}},
        )

        # Update entity values
        update_data = {"columns": ["system_id", "id", "name"], "values": [[1, 10, "A"], [2, 20, "B"], [3, 30, "C"]]}
        response = client.put("/api/v1/projects/test_project/entities/test_entity/values", json=update_data)
        assert response.status_code == 200

        data = response.json()
        assert data["columns"] == ["system_id", "id", "name"]
        assert data["row_count"] == 3
        assert data["format"] == "parquet"

        # Verify file was created
        parquet_file = materialized_folder / "test_entity.parquet"
        assert parquet_file.exists()

        # Verify we can read it back

        df = pd.read_parquet(parquet_file)
        assert df.columns.tolist() == ["system_id", "id", "name"]
        assert len(df) == 3

    def test_update_entity_values_no_load_directive(self, tmp_path, monkeypatch, reset_services):
        """Test error when trying to update entity without @load: directive."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create project with entity that has inline values
        entity_data = {"type": "fixed", "columns": ["id", "name"], "values": [[1, "A"]], "public_id": "id", "keys": ["id"]}
        client.post(
            "/api/v1/projects",
            json={"name": "test_project", "entities": {"test_entity": entity_data}},
        )

        # Try to update entity values
        update_data = {"columns": ["id", "name"], "values": [[1, "X"], [2, "Y"]]}
        response = client.put("/api/v1/projects/test_project/entities/test_entity/values", json=update_data)
        assert response.status_code == 422
        assert "does not have @load: directive" in response.json()["detail"]

    def test_get_entity_values_returns_etag(self, tmp_path, monkeypatch, reset_services):
        """Test GET returns etag for optimistic locking."""

        # Setup temp data directory
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create project with external values
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        values_dir = project_dir / "materialized"
        values_dir.mkdir()

        # Create parquet file
        df = pd.DataFrame({"col1": [1, 2]})
        values_file = values_dir / "test.parquet"
        df.to_parquet(values_file, index=False)

        # Create project
        entity_data = {
            "type": "fixed",
            "columns": ["col1"],
            "values": "@load:materialized/test.parquet",
            "public_id": "col1",
            "keys": ["col1"],
        }
        client.post(
            "/api/v1/projects",
            json={"name": "test_project", "entities": {"test_entity": entity_data}},
        )

        # Get values
        response = client.get("/api/v1/projects/test_project/entities/test_entity/values")
        assert response.status_code == 200

        data = response.json()
        assert "etag" in data
        assert isinstance(data["etag"], str)
        assert len(data["etag"]) == 32  # MD5 hex

    def test_update_entity_values_with_matching_etag(self, tmp_path, monkeypatch, reset_services):
        """Test PUT succeeds with matching If-Match etag."""

        # Setup temp data directory
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create project with external values
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        values_dir = project_dir / "materialized"
        values_dir.mkdir()

        # Create parquet file
        df = pd.DataFrame({"col1": [1, 2]})
        values_file = values_dir / "test.parquet"
        df.to_parquet(values_file, index=False)

        # Create project
        entity_data = {
            "type": "fixed",
            "columns": ["col1"],
            "values": "@load:materialized/test.parquet",
            "public_id": "col1",
            "keys": ["col1"],
        }
        client.post(
            "/api/v1/projects",
            json={"name": "test_project", "entities": {"test_entity": entity_data}},
        )

        # Get current etag
        get_response = client.get("/api/v1/projects/test_project/entities/test_entity/values")
        current_etag = get_response.json()["etag"]

        # Update with matching etag
        update_data = {"columns": ["system_id", "col1"], "values": [[1, 10], [2, 20]]}
        response = client.put(
            "/api/v1/projects/test_project/entities/test_entity/values", json=update_data, headers={"If-Match": current_etag}
        )
        assert response.status_code == 200

        data = response.json()
        assert data["row_count"] == 2
        assert data["etag"] != current_etag  # New etag after update

    def test_update_entity_values_with_mismatched_etag(self, tmp_path, monkeypatch, reset_services):
        """Test PUT fails with 409 when If-Match etag doesn't match."""

        # Setup temp data directory
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create project with external values
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        values_dir = project_dir / "materialized"
        values_dir.mkdir()

        # Create parquet file
        df = pd.DataFrame({"col1": [1, 2]})
        values_file = values_dir / "test.parquet"
        df.to_parquet(values_file, index=False)

        # Create project
        entity_data = {
            "type": "fixed",
            "columns": ["col1"],
            "values": "@load:materialized/test.parquet",
            "public_id": "col1",
            "keys": ["col1"],
        }
        client.post(
            "/api/v1/projects",
            json={"name": "test_project", "entities": {"test_entity": entity_data}},
        )

        # Update with wrong etag
        update_data = {"columns": ["system_id", "col1"], "values": [[1, 10], [2, 20]]}
        response = client.put(
            "/api/v1/projects/test_project/entities/test_entity/values",
            json=update_data,
            headers={"If-Match": "wrong_etag_12345678901234567890"},
        )
        assert response.status_code == 409
        assert "409 Conflict" in response.json()["detail"]

    def test_get_entity_values_with_format_negotiation(self, tmp_path, monkeypatch, reset_services):
        """Test GET with format query parameter (format negotiation)."""

        # Setup temp data directory
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create project with external values
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        values_dir = project_dir / "materialized"
        values_dir.mkdir()

        # Create parquet file
        df = pd.DataFrame({"col1": [1, 2]})
        values_file = values_dir / "test.parquet"
        df.to_parquet(values_file, index=False)

        # Create project
        entity_data = {
            "type": "fixed",
            "columns": ["col1"],
            "values": "@load:materialized/test.parquet",
            "public_id": "col1",
            "keys": ["col1"],
        }
        client.post(
            "/api/v1/projects",
            json={"name": "test_project", "entities": {"test_entity": entity_data}},
        )

        # Get values without format param (should return parquet)
        response = client.get("/api/v1/projects/test_project/entities/test_entity/values")
        assert response.status_code == 200
        assert response.json()["format"] == "parquet"

        # Get values with format=csv (should return csv in format field)
        response = client.get("/api/v1/projects/test_project/entities/test_entity/values?format=csv")
        assert response.status_code == 200
        assert response.json()["format"] == "csv"
        assert response.json()["columns"] == ["col1"]  # Data unchanged
