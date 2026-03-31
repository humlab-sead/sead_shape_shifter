"""Tests for merged entity API support."""

import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import settings
from backend.app.main import app
from backend.app.services import project_service, validation_service, yaml_service

client = TestClient(app)

# pylint: disable=redefined-outer-name, unused-argument


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


@pytest.fixture
def merged_entity_project():
    """Sample project configuration with merged entity."""
    return {
        "name": "test_merged_api",
        "entities": {
            # Branch source 1: dendro
            "dendro": {
                "type": "entity",
                "public_id": "dendro_id",
                "keys": ["sample_name"],
                "columns": ["sample_name", "dendro_date"],
            },
            # Branch source 2: ceramics
            "ceramics": {
                "type": "entity",
                "public_id": "ceramics_id",
                "keys": ["sample_name"],
                "columns": ["sample_name", "ceramic_type"],
            },
            # Merged parent entity
            "analysis_entity": {
                "type": "merged",
                "public_id": "analysis_entity_id",
                "branches": [
                    {"name": "dendro", "source": "dendro", "keys": ["sample_name"]},
                    {"name": "ceramics", "source": "ceramics", "keys": ["sample_name"]},
                ],
            },
        },
    }


def test_get_merged_entity(tmp_path, monkeypatch, reset_services, merged_entity_project):
    """Test retrieving a merged entity via API."""
    monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

    # Create project with merged entity
    client.post("/api/v1/projects", json=merged_entity_project)

    # Get merged entity
    response = client.get("/api/v1/projects/test_merged_api/entities/analysis_entity")

    assert response.status_code == 200
    data = response.json()

    assert data["name"] == "analysis_entity"
    assert data["entity_data"]["type"] == "merged"
    assert data["entity_data"]["public_id"] == "analysis_entity_id"
    assert "branches" in data["entity_data"]
    assert len(data["entity_data"]["branches"]) == 2

    # Verify branch structure
    branches = data["entity_data"]["branches"]
    branch_names = {b["name"] for b in branches}
    assert "dendro" in branch_names
    assert "ceramics" in branch_names


def test_list_entities_includes_merged(tmp_path, monkeypatch, reset_services, merged_entity_project):
    """Test listing entities includes merged entity."""
    monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

    # Create project with merged entity
    client.post("/api/v1/projects", json=merged_entity_project)

    # List entities
    response = client.get("/api/v1/projects/test_merged_api/entities")

    assert response.status_code == 200
    entities = response.json()

    entity_names = {e["name"] for e in entities}
    assert "analysis_entity" in entity_names

    # Find merged entity and verify
    merged_entity = next(e for e in entities if e["name"] == "analysis_entity")
    assert merged_entity["entity_data"]["type"] == "merged"
    assert "branches" in merged_entity["entity_data"]


def test_update_merged_entity(tmp_path, monkeypatch, reset_services, merged_entity_project):
    """Test updating a merged entity via API."""
    monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

    # Create project
    client.post("/api/v1/projects", json=merged_entity_project)

    # Get current entity
    response = client.get("/api/v1/projects/test_merged_api/entities/analysis_entity")
    assert response.status_code == 200
    entity = response.json()

    # Modify branches (update first branch's keys)
    updated_entity_data = entity["entity_data"].copy()
    updated_entity_data["branches"][0]["keys"] = ["sample_name", "sample_id"]

    # Update entity
    response = client.put(
        "/api/v1/projects/test_merged_api/entities/analysis_entity",
        json={"entity_data": updated_entity_data},
    )

    assert response.status_code == 200
    updated = response.json()

    # Verify update
    assert updated["entity_data"]["branches"][0]["keys"] == ["sample_name", "sample_id"]


def test_create_merged_entity(tmp_path, monkeypatch, reset_services):
    """Test creating a new merged entity via API."""
    monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

    # Create base project with source entities
    base_project = {
        "name": "test_project",
        "entities": {
            "source1": {
                "type": "entity",
                "public_id": "source1_id",
                "keys": ["id"],
                "columns": ["id", "value"],
            },
        },
    }
    client.post("/api/v1/projects", json=base_project)

    # Create merged entity
    new_entity = {
        "type": "merged",
        "public_id": "merged_id",
        "branches": [
            {"name": "branch1", "source": "source1", "keys": ["id"]},
        ],
    }

    response = client.post(
        "/api/v1/projects/test_project/entities",
        json={"name": "new_merged", "entity_data": new_entity},
    )

    assert response.status_code == 201
    created = response.json()

    assert created["name"] == "new_merged"
    assert created["entity_data"]["type"] == "merged"
    assert len(created["entity_data"]["branches"]) == 1


def test_validation_detects_merged_errors(tmp_path, monkeypatch, reset_services):
    """Test that validation endpoint detects merged entity errors."""
    monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

    # Create project with invalid merged entity (missing public_id)
    invalid_project = {
        "name": "test_validation",
        "entities": {
            "source": {
                "type": "entity",
                "public_id": "source_id",
                "keys": ["id"],
                "columns": ["id"],
            },
            "invalid_merged": {
                "type": "merged",
                # Missing public_id - should fail validation
                "branches": [
                    {"name": "branch1", "source": "source", "keys": []},
                ],
            },
        },
    }

    client.post("/api/v1/projects", json=invalid_project)

    # Validate project - should catch missing public_id
    response = client.post(
        "/api/v1/projects/test_validation/validate",
        json={"entity_names": ["invalid_merged"]},
    )

    assert response.status_code == 200
    validation_result = response.json()

    # Should have errors for missing public_id
    if "errors" in validation_result:
        errors = validation_result["errors"]
        error_messages = [e.get("message", "") for e in errors]
        assert any("public_id" in msg.lower() for msg in error_messages)
    elif "results" in validation_result:
        # Check if any result has errors
        results = validation_result["results"]
        has_public_id_error = any(
            "public_id" in str(r.get("errors", [])).lower() for r in results
        )
        assert has_public_id_error

