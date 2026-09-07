"""Tests for configuration API endpoints."""

import pytest

from backend.app.core.config import settings
from backend.app.services import project_service, validation_service, yaml_service

# pylint: disable=redefined-outer-name, unused-argument


@pytest.fixture
def sample_project_data():
    """Sample project data for tests."""
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


class TestProjectsList:
    """Tests for listing projects."""

    async def test_list_projects_empty(self, tmp_path, monkeypatch, reset_services, authorized_client):
        """Test listing when no projects exist."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        response = await authorized_client.get("/api/v1/projects")
        assert response.status_code == 200
        assert response.json() == []

    async def test_list_projects(self, tmp_path, monkeypatch, reset_services, sample_project_data, authorized_client):
        """Test listing projects."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create test project via API
        create_response = await authorized_client.post(
            "/api/v1/projects", json={"name": "test_project", "entities": sample_project_data["entities"]}
        )
        assert create_response.status_code == 201

        # List projects
        response = await authorized_client.get("/api/v1/projects")
        assert response.status_code == 200
        configs = response.json()
        assert len(configs) == 1
        assert configs[0]["name"] == "test_project"
        assert configs[0]["entity_count"] == 1


class TestProjectsGet:
    """Tests for getting projects."""

    async def test_get_project(self, tmp_path, monkeypatch, reset_services, sample_project_data, authorized_client):
        """Test getting existing project."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create project
        await authorized_client.post("/api/v1/projects", json={"name": "test_project", "entities": sample_project_data["entities"]})

        # Get project
        response = await authorized_client.get("/api/v1/projects/test_project")
        assert response.status_code == 200
        data = response.json()
        assert data["metadata"]["name"] == "test_project"
        assert "sample" in data["entities"]

    async def test_get_nonexistent_project(self, tmp_path, monkeypatch, reset_services, authorized_client):
        """Test getting non-existent project returns 404."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        response = await authorized_client.get("/api/v1/projects/nonexistent")
        assert response.status_code == 404


class TestProjectsCreate:
    """Tests for creating projects."""

    async def test_create_project(self, tmp_path, monkeypatch, reset_services, sample_project_data, authorized_client):
        """Test creating a new project."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        response = await authorized_client.post(
            "/api/v1/projects", json={"name": "new_config", "entities": sample_project_data["entities"]}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["metadata"]["name"] == "new_project"
        assert data["metadata"]["entity_count"] == 1

    async def test_create_duplicate_project(self, tmp_path, monkeypatch, reset_services, sample_project_data, authorized_client):
        """Test creating duplicate project returns 409 Conflict."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create first project
        await authorized_client.post("/api/v1/projects", json={"name": "test_project", "entities": sample_project_data["entities"]})

        # Try to create duplicate project
        response = await authorized_client.post(
            "/api/v1/projects", json={"name": "test_project", "entities": sample_project_data["entities"]}
        )
        assert response.status_code == 409


class TestProjectsUpdate:
    """Tests for updating projects."""

    async def test_update_project(self, tmp_path, monkeypatch, reset_services, sample_project_data, authorized_client):
        """Test updating existing project (options only, not entities)."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create project
        await authorized_client.post("/api/v1/projects", json={"name": "test_project", "entities": sample_project_data["entities"]})

        # Update project options (entities are ignored by update endpoint)
        updated_options = {"some_option": "value", "another_option": 123}
        response = await authorized_client.put("/api/v1/projects/test_project", json={"entities": {}, "options": updated_options})

        assert response.status_code == 200
        data = response.json()
        # Verify project entities are preserved from disk
        assert "sample" in data["entities"]
        assert data["entities"]["sample"]["columns"] == ["name", "value"]
        # Verify options were updated
        assert data["options"]["some_option"] == "value"
        assert data["options"]["another_option"] == 123

    async def test_update_nonexistent_project(self, tmp_path, monkeypatch, reset_services, authorized_client):
        """Test updating non-existent project returns 404."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        response = await authorized_client.put(
            "/api/v1/projects/nonexistent",
            json={"entities": {"sample": {"type": "entity"}}, "options": {}},
        )
        assert response.status_code == 404

    async def test_update_metadata(self, tmp_path, monkeypatch, reset_services, sample_project_data, authorized_client):
        """Test updating existing project metadata."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create project
        await authorized_client.post("/api/v1/projects", json={"name": "test_project", "entities": sample_project_data["entities"]})

        # Update metadata
        metadata_update = {
            "description": "Updated description",
            "version": "2.0.1",
            "default_entity": "sample",
        }
        response = await authorized_client.patch("/api/v1/projects/test_project/metadata", json=metadata_update)

        assert response.status_code == 200
        data = response.json()
        assert data["metadata"]["description"] == "Updated description"
        assert data["metadata"]["version"] == "2.0.1"
        assert data["metadata"]["default_entity"] == "sample"
        # Verify entities are preserved
        assert "sample" in data["entities"]

    async def test_update_metadata_rename(self, tmp_path, monkeypatch, reset_services, sample_project_data, authorized_client):
        """Test that renaming a project via metadata update is ignored (filename is source of truth)."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create project
        await authorized_client.post("/api/v1/projects", json={"name": "old_name", "entities": sample_project_data["entities"]})

        # Attempt rename via metadata (should be ignored)
        metadata_update = {"name": "new_name"}
        response = await authorized_client.patch("/api/v1/projects/old_name/metadata", json=metadata_update)

        assert response.status_code == 200
        data = response.json()
        # Name should remain old_name (filename is source of truth)
        assert data["metadata"]["name"] == "old_name"

        # Verify old name still exists
        get_old = await authorized_client.get("/api/v1/projects/old_name")
        assert get_old.status_code == 200

        # Verify new name was NOT created
        get_new = await authorized_client.get("/api/v1/projects/new_name")
        assert get_new.status_code == 404

    async def test_update_metadata_rename_conflict(self, tmp_path, monkeypatch, reset_services, sample_project_data, authorized_client):
        """Test that attempting to rename a project via metadata doesn't cause conflicts (ignored)."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create two projects
        await authorized_client.post("/api/v1/projects", json={"name": "config1", "entities": sample_project_data["entities"]})
        await authorized_client.post("/api/v1/projects", json={"name": "config2", "entities": sample_project_data["entities"]})

        # Try to rename config1 to config2 (should be ignored, no conflict)
        metadata_update = {"name": "config2"}
        response = await authorized_client.patch("/api/v1/projects/config1/metadata", json=metadata_update)

        # Should succeed (200) because rename is ignored
        assert response.status_code == 200
        # config1 name should remain unchanged
        data = response.json()
        assert data["metadata"]["name"] == "config1"


class TestProjectsDelete:
    """Tests for deleting projects."""

    async def test_delete_configuration(self, tmp_path, monkeypatch, reset_services, sample_project_data, authorized_client):
        """Test deleting existing project."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create project
        await authorized_client.post("/api/v1/projects", json={"name": "test_project", "entities": sample_project_data["entities"]})

        # Delete project
        response = await authorized_client.delete("/api/v1/projects/test_project")
        assert response.status_code == 204

        # Verify deleted
        get_response = await authorized_client.get("/api/v1/projects/test_project")
        assert get_response.status_code == 404

    async def test_delete_nonexistent_project(self, tmp_path, monkeypatch, reset_services, authorized_client):
        """Test deleting non-existent project returns 404."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        response = await authorized_client.delete("/api/v1/projects/nonexistent")
        assert response.status_code == 404


class TestProjectsValidate:
    """Tests for project validation."""

    async def test_validate_valid_configuration(self, tmp_path, monkeypatch, reset_services, authorized_client):
        """Test validating a valid project."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create a fully valid configuration with all required fields
        valid_entities = {
            "sample": {"type": "entity", "keys": ["sample_id"], "columns": ["name", "value"], "depends_on": []}  # Required field
        }

        payload = {"name": "test_project", "entities": valid_entities}

        # Create project
        await authorized_client.post("/api/v1/projects", json=payload)

        # Validate
        response = await authorized_client.post("/api/v1/projects/test_project/validate")
        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] is True
        assert data["error_count"] == 0

    async def test_validate_invalid_configuration(self, tmp_path, monkeypatch, reset_services, authorized_client):
        """Test validating an invalid project."""

        # Use unique name to avoid collision with valid test
        project_name = "invalid_test_project"
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create project with invalid entity (missing keys)
        invalid_entities = {"sample": {"type": "entity"}}
        await authorized_client.post("/api/v1/projects", json={"name": project_name, "entities": invalid_entities})

        # Validate
        response = await authorized_client.post(f"/api/v1/projects/{project_name}/validate")
        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] is False
        assert data["error_count"] > 0

    async def test_validate_project_resolves_include_relative_to_project(self, tmp_path, monkeypatch, reset_services, authorized_client):
        """Test @include in project resolves relative to the project file path."""

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

        await authorized_client.post("/api/v1/projects", json=payload)

        # Create the included file next to the project YAML file.
        (tmp_path / "digidiggie-options.yml").write_text(
            "driver: ucanaccess\noptions:\n  filename: ./projects/digidiggie_dev.accdb\n  ucanaccess_dir: lib/ucanaccess\n",
            encoding="utf-8",
        )

        response = await authorized_client.post("/api/v1/projects/test_project/validate")
        assert response.status_code == 200
        data = response.json()

        # Ensure validation did not fail due to missing include file.
        assert not any("configuration file not found" in e["message"].lower() for e in data.get("errors", []))

    async def test_validate_project_missing_include_returns_error_result(self, tmp_path, monkeypatch, reset_services, authorized_client):
        """Test missing @include file in project returns project validation result (not HTTP 500)."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        valid_entities = {"sample": {"type": "entity", "keys": ["sample_id"], "columns": ["name"], "depends_on": []}}

        # Create project (create endpoint does not accept `options`)
        await authorized_client.post("/api/v1/projects", json={"name": "test_project", "entities": valid_entities})

        # Update options (PUT endpoint updates options only; entities are ignored but required by schema)
        await authorized_client.put(
            "/api/v1/projects/test_project",
            json={
                "entities": {},
                "options": {"data_sources": {"missing": "@include: definitely-missing.yml"}},
            },
        )

        response = await authorized_client.post("/api/v1/projects/test_project/validate")
        assert response.status_code == 200

        data = response.json()
        assert data["is_valid"] is False
        assert data["error_count"] > 0
        assert any("YAML file not found" in e["message"] for e in data.get("errors", []))


class TestProjectsBackups:
    """Tests for project backup operations."""

    async def test_list_backups(self, tmp_path, monkeypatch, reset_services, sample_project_data, authorized_client):
        """Test listing backups."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create project
        await authorized_client.post("/api/v1/projects", json={"name": "test_project", "entities": sample_project_data["entities"]})

        # Update to create backup
        updated_entities = {"sample": {"type": "entity", "keys": ["id"], "columns": ["name"]}}
        await authorized_client.put("/api/v1/projects/test_project", json={"entities": updated_entities, "options": {}})

        # List backups
        response = await authorized_client.get("/api/v1/projects/test_project/backups")
        assert response.status_code == 200
        backups = response.json()
        assert len(backups) >= 1
        assert "shapeshifter" in backups[0]["file_name"]

    async def test_restore_backup(self, reset_services, tmp_path, monkeypatch, sample_project_data, authorized_client):
        """Test restoring from backup."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create project
        create_response = await authorized_client.post(
            "/api/v1/projects", json={"name": "test_project", "entities": sample_project_data["entities"]}
        )
        assert create_response.status_code == 201, f"Failed to create project: {create_response.json()}"
        original_data = create_response.json()

        # Update to create backup
        updated_entities = {"sample": {"type": "entity", "keys": ["id"], "columns": ["modified"]}}
        await authorized_client.put("/api/v1/projects/test_project", json={"entities": updated_entities, "options": {}})

        # Get backup path
        backups_response = await authorized_client.get("/api/v1/projects/test_project/backups")
        backups = backups_response.json()
        backup_name = backups[0]["file_name"]

        # Restore
        response = await authorized_client.post("/api/v1/projects/test_project/restore", json={"backup_name": backup_name})
        assert response.status_code == 200
        restored_data = response.json()

        # Verify restoration - both should be Configuration models with same structure
        assert "entities" in original_data
        assert "entities" in restored_data
        assert "sample" in original_data["entities"]
        assert "sample" in restored_data["entities"]
        assert restored_data["entities"]["sample"]["columns"] == original_data["entities"]["sample"]["columns"]
