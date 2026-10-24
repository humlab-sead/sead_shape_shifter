"""Tests for configuration API endpoints."""

import pytest

from backend.app.authorization.models import ResourceType
from backend.app.authorization.repository import SQLiteAuthorizationRepository
from backend.app.core.config import settings
from backend.app.services import project_service, validation_service, yaml_service

# pylint: disable=redefined-outer-name, unused-argument


@pytest.fixture
def sample_project_data():
    """Sample project data for tests."""
    return {
        "data_provider_code": "test-provider",
        "provider_schema": "schema-one",
        "entities": {
            "sample": {
                "type": "entity",
                "keys": ["sample_id"],
                "columns": ["name", "value"],
            }
        },
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
            "/api/v1/projects",
            json={
                "name": "test_project",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": sample_project_data["entities"],
            },
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
        await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "test_project",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": sample_project_data["entities"],
            },
        )

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

    async def test_list_target_models_includes_distinct_local_and_shared_references(
        self, tmp_path, monkeypatch, reset_services, authorized_client
    ):
        """The target model picker should distinguish same-named local and shared files."""
        projects_dir = tmp_path / "projects"
        target_models_dir = tmp_path / "shared" / "target-models"
        monkeypatch.setattr(settings, "PROJECTS_DIR", projects_dir)
        monkeypatch.setattr(settings, "GLOBAL_TARGET_MODEL_DIR", target_models_dir)

        create_response = await authorized_client.post(
            "/api/v1/projects",
            json={"name": "test_project", "data_provider_code": "test-provider", "provider_schema": "schema-one"},
        )
        assert create_response.status_code == 201
        (projects_dir / "test_project" / "model.yml").write_text("model: {}\nentities: {}\n", encoding="utf-8")
        target_models_dir.mkdir(parents=True)
        (target_models_dir / "model.yml").write_text("model: {}\nentities: {}\n", encoding="utf-8")

        response = await authorized_client.get("/api/v1/projects/test_project/target-models")

        assert response.status_code == 200
        options = response.json()
        assert [(option["location"], option["value"]) for option in options] == [
            ("project", "@load: model.yml"),
            ("shared", "@load: ${GLOBAL_TARGET_MODEL_DIR}/model.yml"),
        ]
        assert [option["label"] for option in options] == ["Project-local: model.yml", "Shared: model.yml"]

    async def test_shared_target_model_yaml_cannot_be_read_or_updated_in_project_editor(
        self, tmp_path, monkeypatch, reset_services, authorized_client
    ):
        """Shared model references should not expose the project YAML editor endpoints."""
        projects_dir = tmp_path / "projects"
        target_models_dir = tmp_path / "shared" / "target-models"
        monkeypatch.setattr(settings, "PROJECTS_DIR", projects_dir)
        monkeypatch.setattr(settings, "GLOBAL_TARGET_MODEL_DIR", target_models_dir)
        target_models_dir.mkdir(parents=True)
        (target_models_dir / "model.yml").write_text("model: {}\nentities: {}\n", encoding="utf-8")

        create_response = await authorized_client.post(
            "/api/v1/projects",
            json={"name": "test_project", "data_provider_code": "test-provider", "provider_schema": "schema-one"},
        )
        assert create_response.status_code == 201
        local_model = projects_dir / "test_project" / "local-model.yml"
        local_model.write_text("model: {name: Local Model}\nentities: {}\n", encoding="utf-8")
        local_metadata_response = await authorized_client.patch(
            "/api/v1/projects/test_project/metadata",
            json={"target_model": "@load: local-model.yml"},
        )
        assert local_metadata_response.status_code == 200

        local_read_response = await authorized_client.get("/api/v1/projects/test_project/target-model-yaml")
        local_update_response = await authorized_client.put(
            "/api/v1/projects/test_project/target-model-yaml",
            json={"yaml_content": "model: {name: Updated Local Model}\nentities: {}\n"},
        )
        assert local_read_response.status_code == 200
        assert local_read_response.json()["yaml_content"] == "model: {name: Local Model}\nentities: {}\n"
        assert local_update_response.status_code == 200

        metadata_response = await authorized_client.patch(
            "/api/v1/projects/test_project/metadata",
            json={"target_model": "@load: ${GLOBAL_TARGET_MODEL_DIR}/model.yml"},
        )
        assert metadata_response.status_code == 200

        read_response = await authorized_client.get("/api/v1/projects/test_project/target-model-yaml")
        update_response = await authorized_client.put(
            "/api/v1/projects/test_project/target-model-yaml",
            json={"yaml_content": "model: {}\nentities: {}\n"},
        )

        assert read_response.status_code == 403
        assert update_response.status_code == 403


class TestProjectsCreate:
    """Tests for creating projects."""

    async def test_create_project(self, tmp_path, monkeypatch, reset_services, sample_project_data, authorized_client):
        """Test creating a new project."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        response = await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "new_project",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": sample_project_data["entities"],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["metadata"]["name"] == "new_project"
        assert data["metadata"]["entity_count"] == 1
        assert data["metadata"]["data_provider_code"] == "test-provider"
        assert data["metadata"]["provider_schema"] == "schema-one"

    async def test_create_requires_registered_pair_before_project_creation(self, tmp_path, monkeypatch, reset_services, authorized_client):
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        missing_pair = await authorized_client.post("/api/v1/projects", json={"name": "missing-pair"})
        unknown_pair = await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "unknown-pair",
                "data_provider_code": "test-provider",
                "provider_schema": "unknown-schema",
            },
        )

        assert missing_pair.status_code == 422
        assert unknown_pair.status_code == 400
        assert not (tmp_path / "missing-pair").exists()
        assert not (tmp_path / "unknown-pair").exists()

    async def test_create_duplicate_project(self, tmp_path, monkeypatch, reset_services, sample_project_data, authorized_client):
        """Test creating duplicate project returns 409 Conflict."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create first project
        await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "test_project",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": sample_project_data["entities"],
            },
        )

        # Try to create duplicate project
        response = await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "test_project",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": sample_project_data["entities"],
            },
        )
        assert response.status_code == 409


class TestProjectsUpdate:
    """Tests for updating projects."""

    async def test_update_project(self, tmp_path, monkeypatch, reset_services, sample_project_data, authorized_client):
        """Test updating existing project (options only, not entities)."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create project
        await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "test_project",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": sample_project_data["entities"],
            },
        )

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
        await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "test_project",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": sample_project_data["entities"],
            },
        )

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

    async def test_metadata_assigns_pair_once_and_rejects_change_or_removal(
        self, tmp_path, monkeypatch, reset_services, sample_project_data, authorized_client
    ):
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        created = await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "legacy-project",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": sample_project_data["entities"],
            },
        )
        assert created.status_code == 201

        project_path = tmp_path / "legacy-project" / "shapeshifter.yml"
        project_yaml = project_path.read_text(encoding="utf-8")
        project_path.write_text(
            project_yaml.replace("  data_provider_code: test-provider\n", "").replace("  provider_schema: schema-one\n", ""),
            encoding="utf-8",
        )
        await authorized_client.post("/api/v1/projects/legacy-project/refresh")

        assigned = await authorized_client.patch(
            "/api/v1/projects/legacy-project/metadata",
            json={"data_provider_code": "test-provider", "provider_schema": "schema-two"},
        )
        assert assigned.status_code == 200
        assert assigned.json()["metadata"]["data_provider_code"] == "test-provider"
        assert assigned.json()["metadata"]["provider_schema"] == "schema-two"

        original = project_path.read_bytes()
        changed = await authorized_client.patch(
            "/api/v1/projects/legacy-project/metadata",
            json={"provider_schema": "schema-one"},
        )
        removed = await authorized_client.patch(
            "/api/v1/projects/legacy-project/metadata",
            json={"provider_schema": None},
        )
        assert changed.status_code == 400
        assert removed.status_code == 400
        assert project_path.read_bytes() == original

    async def test_update_metadata_rename(self, tmp_path, monkeypatch, reset_services, sample_project_data, authorized_client):
        """Test that renaming a project via metadata update is ignored (filename is source of truth)."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create project
        await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "old_name",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": sample_project_data["entities"],
            },
        )

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
        await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "config1",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": sample_project_data["entities"],
            },
        )
        await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "config2",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": sample_project_data["entities"],
            },
        )

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
        await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "test_project",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": sample_project_data["entities"],
            },
        )

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

    async def test_validate_saved_reference_keeps_original_text_and_does_not_change_project(
        self, tmp_path, monkeypatch, reset_services, authorized_client
    ):
        """Return a located saved-reference error and leave the saved entity unchanged."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        project_name = "reference_project"
        created = await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": project_name,
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": {
                    "source": {"type": "entity", "keys": ["source_id"], "columns": ["source_id"]},
                    "sample": {"type": "entity", "keys": ["sample_id"], "columns": ["sample_id"]},
                },
            },
        )
        assert created.status_code == 201

        saved_reference = "@value: entities.missing.keys"
        updated = await authorized_client.put(
            f"/api/v1/projects/{project_name}/entities/sample",
            json={"entity_data": {"type": "entity", "keys": ["sample_id"], "columns": saved_reference}},
        )
        assert updated.status_code == 200

        response = await authorized_client.post(f"/api/v1/projects/{project_name}/validate")
        assert response.status_code == 200
        data = response.json()

        reference_errors = [error for error in data["errors"] if error["code"] == "COLUMN_REFERENCE_MISSING_PATH"]
        assert len(reference_errors) == 1
        assert reference_errors[0]["entity"] == "sample"
        assert reference_errors[0]["field"] == "columns"
        assert saved_reference in reference_errors[0]["message"]
        assert data["error_count"] == len(data["errors"])

        saved = await authorized_client.get(f"/api/v1/projects/{project_name}/entities/sample")
        assert saved.status_code == 200
        assert saved.json()["entity_data"]["columns"] == saved_reference

    async def test_validate_saved_reference_when_project_resolution_fails(self, tmp_path, monkeypatch, reset_services, authorized_client):
        """Return both saved-reference and project-resolution errors as HTTP 200."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        project_name = "reference_resolution_failure"
        created = await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": project_name,
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": {
                    "source": {"type": "entity", "keys": ["source_id"], "columns": ["source_id"]},
                    "sample": {"type": "entity", "keys": ["sample_id"], "columns": ["sample_id"]},
                },
            },
        )
        assert created.status_code == 201

        saved_reference = "@value: entities.missing.keys"
        reference_update = await authorized_client.put(
            f"/api/v1/projects/{project_name}/entities/sample",
            json={"entity_data": {"type": "entity", "keys": ["sample_id"], "columns": saved_reference}},
        )
        include_update = await authorized_client.put(
            f"/api/v1/projects/{project_name}/entities/source",
            json={"entity_data": {"type": "entity", "keys": ["source_id"], "columns": "@include: absent.yml"}},
        )
        assert reference_update.status_code == 200
        assert include_update.status_code == 200

        response = await authorized_client.post(f"/api/v1/projects/{project_name}/validate")

        assert response.status_code == 200
        data = response.json()
        codes = [error["code"] for error in data["errors"]]
        assert "COLUMN_REFERENCE_MISSING_PATH" in codes
        assert "CONFIG_INCLUDE_NOT_FOUND" in codes
        assert saved_reference in next(error["message"] for error in data["errors"] if error["code"] == "COLUMN_REFERENCE_MISSING_PATH")

    async def test_validate_valid_configuration(self, tmp_path, monkeypatch, reset_services, authorized_client):
        """Test validating a valid project."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create a fully valid configuration with all required fields
        valid_entities = {
            "data_provider": {
                "type": "fixed",
                "public_id": "data_provider_id",
                "keys": ["data_provider_code"],
                "columns": ["data_provider_id", "data_provider_code"],
                "values": [[51, "test-provider"]],
            },
            "sample": {
                "type": "entity",
                "keys": ["sample_id"],
                "columns": ["name", "value", "sample_id"],
                "depends_on": [],
            },  # Required field
        }

        payload = {
            "name": "test_project",
            "data_provider_code": "test-provider",
            "provider_schema": "schema-one",
            "entities": valid_entities,
        }

        # Create project
        await authorized_client.post("/api/v1/projects", json=payload)

        # Validate
        response = await authorized_client.post("/api/v1/projects/test_project/validate")
        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] is True
        assert data["error_count"] == 0

    async def test_validate_missing_provider_pair_returns_metadata_errors(self, tmp_path, monkeypatch, reset_services, authorized_client):
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        created = await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "unbound_project",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": {},
            },
        )
        assert created.status_code == 201

        project_path = tmp_path / "unbound_project" / "shapeshifter.yml"
        project_yaml = project_path.read_text(encoding="utf-8")
        project_path.write_text(
            project_yaml.replace("  data_provider_code: test-provider\n", "").replace("  provider_schema: schema-one\n", ""),
            encoding="utf-8",
        )
        await authorized_client.post("/api/v1/projects/unbound_project/refresh")

        response = await authorized_client.post("/api/v1/projects/unbound_project/validate")

        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] is False
        assert {error["field"] for error in data["errors"]} >= {
            "metadata.data_provider_code",
            "metadata.provider_schema",
        }

    async def test_validate_invalid_configuration(self, tmp_path, monkeypatch, reset_services, authorized_client):
        """Test validating an invalid project."""

        # Use unique name to avoid collision with valid test
        project_name = "invalid_test_project"
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create project with invalid entity (missing keys)
        invalid_entities = {"sample": {"type": "entity"}}
        await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": project_name,
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": invalid_entities,
            },
        )

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
            "data_provider_code": "test-provider",
            "provider_schema": "schema-one",
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
        await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "test_project",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": valid_entities,
            },
        )

        # Update options (PUT endpoint updates options only; entities are ignored but required by schema)
        await authorized_client.put(
            "/api/v1/projects/test_project",
            json={
                "entities": {},
                "options": {"missing": "@include: definitely-missing.yml"},
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
        await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "test_project",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": sample_project_data["entities"],
            },
        )

        # Update to create backup
        updated_entities = {"sample": {"type": "entity", "keys": ["id"], "columns": ["name"]}}
        await authorized_client.put("/api/v1/projects/test_project", json={"entities": updated_entities, "options": {}})

        task_sidecar = tmp_path / "test_project" / "shapeshifter.tasks.yml"
        task_sidecar.write_text("task_list: {}\n", encoding="utf-8")
        yaml_service.get_yaml_service().create_backup(task_sidecar)

        # List backups
        response = await authorized_client.get("/api/v1/projects/test_project/backups")
        assert response.status_code == 200
        backups = response.json()
        assert len(backups) >= 1
        assert "shapeshifter" in backups[0]["file_name"]
        assert all(".tasks.backup." not in backup["file_name"] for backup in backups)

    async def test_restore_backup(self, reset_services, tmp_path, monkeypatch, sample_project_data, authorized_client):
        """Test restoring from backup."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create project
        create_response = await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "test_project",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": sample_project_data["entities"],
            },
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

    @pytest.mark.parametrize(
        ("old_value", "new_value"),
        [
            ("provider_schema: schema-one", "provider_schema: schema-two"),
            ("data_provider_code: test-provider", "data_provider_code: another-provider"),
            ("  provider_schema: schema-one\n", ""),
        ],
    )
    async def test_restore_rejects_backup_with_changed_pair_before_writing(
        self, reset_services, tmp_path, monkeypatch, sample_project_data, authorized_client, old_value, new_value
    ):
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        created = await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "test_project",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": sample_project_data["entities"],
            },
        )
        assert created.status_code == 201

        project_path = tmp_path / "test_project" / "shapeshifter.yml"
        original = project_path.read_bytes()
        backup_dir = project_path.parent / "backups"
        backup_dir.mkdir()
        changed_backup = backup_dir / "shapeshifter.backup.20261018_120000.yml"
        changed_backup.write_text(
            original.decode("utf-8").replace(old_value, new_value),
            encoding="utf-8",
        )

        response = await authorized_client.post(
            "/api/v1/projects/test_project/restore",
            json={"backup_name": changed_backup.name},
        )

        assert response.status_code == 400
        assert project_path.read_bytes() == original
        assert [path.name for path in backup_dir.iterdir()] == [changed_backup.name]

    async def test_restore_rejects_malformed_backup_before_writing(
        self, reset_services, tmp_path, monkeypatch, sample_project_data, authorized_client
    ):
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        created = await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "test_project",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": sample_project_data["entities"],
            },
        )
        assert created.status_code == 201

        project_path = tmp_path / "test_project" / "shapeshifter.yml"
        original = project_path.read_bytes()
        backup_dir = project_path.parent / "backups"
        backup_dir.mkdir()
        malformed_backup = backup_dir / "shapeshifter.backup.20261018_120001.yml"
        malformed_backup.write_text("metadata: [", encoding="utf-8")

        response = await authorized_client.post(
            "/api/v1/projects/test_project/restore",
            json={"backup_name": malformed_backup.name},
        )

        assert response.status_code == 400
        assert project_path.read_bytes() == original
        assert [path.name for path in backup_dir.iterdir()] == [malformed_backup.name]

    async def test_restore_rejects_task_list_sidecar_backup(
        self, reset_services, tmp_path, monkeypatch, sample_project_data, authorized_client
    ):
        """Restoring a task-list backup must not replace the project configuration."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        create_response = await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "test_project",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": sample_project_data["entities"],
            },
        )
        assert create_response.status_code == 201

        config_path = tmp_path / "test_project" / "shapeshifter.yml"
        original_config = config_path.read_text(encoding="utf-8")
        task_sidecar = tmp_path / "test_project" / "shapeshifter.tasks.yml"
        task_sidecar.write_text("task_list:\n  todo: [sample]\n", encoding="utf-8")
        task_backup = yaml_service.get_yaml_service().create_backup(task_sidecar)

        response = await authorized_client.post(
            "/api/v1/projects/test_project/restore",
            json={"backup_name": task_backup.name},
        )

        assert response.status_code == 404
        assert config_path.read_text(encoding="utf-8") == original_config

    async def test_restore_rejects_backup_from_another_project(
        self, reset_services, tmp_path, monkeypatch, sample_project_data, authorized_client
    ):
        """Restore accepts only a backup name returned for the authorized project."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        for project_name in ("project_a", "project_b"):
            response = await authorized_client.post(
                "/api/v1/projects",
                json={
                    "name": project_name,
                    "data_provider_code": "test-provider",
                    "provider_schema": "schema-one",
                    "entities": sample_project_data["entities"],
                },
            )
            assert response.status_code == 201

        project_b_backup = tmp_path / "project_b" / "backups" / "cross-project.yml"
        project_b_backup.parent.mkdir()
        project_b_backup.write_text("entities: {}\n", encoding="utf-8")

        response = await authorized_client.post(
            "/api/v1/projects/project_a/restore",
            json={"backup_name": "../project_b/backups/cross-project.yml"},
        )

        assert response.status_code == 404

    async def test_list_backups_skips_symlink_outside_project(
        self, reset_services, tmp_path, monkeypatch, sample_project_data, authorized_client
    ):
        """Backup listings do not expose backups through an outside symlink."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        response = await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "project_a",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": sample_project_data["entities"],
            },
        )
        assert response.status_code == 201

        outside_backup = tmp_path / "outside.yml"
        outside_backup.write_text("entities: {}\n", encoding="utf-8")
        backup_dir = tmp_path / "project_a" / "backups"
        backup_dir.mkdir()
        (backup_dir / "outside.yml").symlink_to(outside_backup)

        response = await authorized_client.get("/api/v1/projects/project_a/backups")

        assert response.status_code == 200
        assert response.json() == []


class TestProjectFileManagement:
    """Tests for uploading, sharing, listing, and deleting project files."""

    async def test_upload_project_file_overwrites_when_requested(self, reset_services, tmp_path, monkeypatch, authorized_client):
        """The upload endpoint replaces a same-named file only when requested."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        create_response = await authorized_client.post(
            "/api/v1/projects",
            json={"name": "test_project", "data_provider_code": "test-provider", "provider_schema": "schema-one"},
        )
        assert create_response.status_code == 201

        first_response = await authorized_client.post(
            "/api/v1/projects/test_project/files",
            files={"file": ("data.xlsx", b"old content", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        replace_response = await authorized_client.post(
            "/api/v1/projects/test_project/files",
            files={"file": ("data.xlsx", b"new content", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            data={"overwrite": "true"},
        )

        assert first_response.status_code == 200
        assert replace_response.status_code == 200
        assert replace_response.json()["name"] == "data.xlsx"
        assert (tmp_path / "test_project" / "data.xlsx").read_bytes() == b"new content"

    async def test_share_project_file_registers_global_copy_and_lists_it(self, reset_services, tmp_path, monkeypatch, authorized_client):
        """Sharing copies a project file through the global file store and registers it."""
        projects_dir = tmp_path / "projects"
        global_data_dir = tmp_path / "shared-data"
        monkeypatch.setattr(settings, "PROJECTS_DIR", projects_dir)
        monkeypatch.setattr(settings, "GLOBAL_DATA_DIR", global_data_dir)

        create_response = await authorized_client.post(
            "/api/v1/projects",
            json={"name": "test_project", "data_provider_code": "test-provider", "provider_schema": "schema-one"},
        )
        assert create_response.status_code == 201
        upload_response = await authorized_client.post(
            "/api/v1/projects/test_project/files",
            files={"file": ("data.csv", b"col\nvalue\n", "text/csv")},
        )
        assert upload_response.status_code == 200

        response = await authorized_client.post("/api/v1/projects/test_project/files/data.csv/share")

        assert response.status_code == 201
        assert response.json()["location"] == "global"
        assert response.json()["name"] == "data.csv"
        assert (global_data_dir / "data.csv").read_bytes() == b"col\nvalue\n"

        files_response = await authorized_client.get("/api/v1/projects/test_project/files")
        assert files_response.status_code == 200
        assert {(file["name"], file["location"]) for file in files_response.json()} == {
            ("data.csv", "local"),
            ("data.csv", "global"),
        }

        capabilities_response = await authorized_client.get("/api/v1/projects/test_project/files/capabilities")
        assert capabilities_response.status_code == 200
        assert capabilities_response.json() == {"can_share_with_all_projects": True}

        repository = SQLiteAuthorizationRepository(settings.AUTHORIZATION_DATABASE_PATH)
        try:
            resource = repository.get_resource_by_locator(ResourceType.SHARED_DATA_SOURCE, "data.csv")
        finally:
            repository.close()
        assert resource is not None

    async def test_share_project_file_uses_global_collision_handling(self, reset_services, tmp_path, monkeypatch, authorized_client):
        """A promoted file with a name already in shared data receives a new name."""
        projects_dir = tmp_path / "projects"
        global_data_dir = tmp_path / "shared-data"
        global_data_dir.mkdir()
        (global_data_dir / "data.csv").write_bytes(b"existing\n")
        monkeypatch.setattr(settings, "PROJECTS_DIR", projects_dir)
        monkeypatch.setattr(settings, "GLOBAL_DATA_DIR", global_data_dir)

        create_response = await authorized_client.post(
            "/api/v1/projects",
            json={"name": "test_project", "data_provider_code": "test-provider", "provider_schema": "schema-one"},
        )
        assert create_response.status_code == 201
        await authorized_client.post(
            "/api/v1/projects/test_project/files",
            files={"file": ("data.csv", b"col\nvalue\n", "text/csv")},
        )

        response = await authorized_client.post("/api/v1/projects/test_project/files/data.csv/share")

        assert response.status_code == 201
        assert response.json()["name"] == "data-1.csv"
        assert (global_data_dir / "data.csv").read_bytes() == b"existing\n"
        assert (global_data_dir / "data-1.csv").read_bytes() == b"col\nvalue\n"

    async def test_share_project_file_rejects_missing_source(self, reset_services, tmp_path, monkeypatch, authorized_client):
        """The share endpoint returns not found for a missing project file."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path / "projects")
        create_response = await authorized_client.post(
            "/api/v1/projects",
            json={"name": "test_project", "data_provider_code": "test-provider", "provider_schema": "schema-one"},
        )
        assert create_response.status_code == 201

        response = await authorized_client.post("/api/v1/projects/test_project/files/missing.csv/share")

        assert response.status_code == 404

    async def test_delete_project_file_rejects_local_entity_references(self, reset_services, tmp_path, monkeypatch, authorized_client):
        """A project file referenced by a local entity cannot be deleted."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        create_response = await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "test_project",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": {
                    "source_data": {
                        "type": "csv",
                        "options": {"filename": "data.csv", "location": "local"},
                    }
                },
            },
        )
        assert create_response.status_code == 201
        file_response = await authorized_client.post(
            "/api/v1/projects/test_project/files",
            files={"file": ("data.csv", b"col\nvalue\n", "text/csv")},
        )
        assert file_response.status_code == 200

        response = await authorized_client.delete("/api/v1/projects/test_project/files/data.csv")

        assert response.status_code == 409
        assert "source_data" in response.json()["detail"]["message"]
        assert (tmp_path / "test_project" / "data.csv").exists()

    async def test_delete_unused_project_file(self, reset_services, tmp_path, monkeypatch, authorized_client):
        """An unreferenced project file can be deleted."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        create_response = await authorized_client.post(
            "/api/v1/projects",
            json={"name": "test_project", "data_provider_code": "test-provider", "provider_schema": "schema-one"},
        )
        assert create_response.status_code == 201
        file_response = await authorized_client.post(
            "/api/v1/projects/test_project/files",
            files={"file": ("unused.csv", b"col\nvalue\n", "text/csv")},
        )
        assert file_response.status_code == 200

        response = await authorized_client.delete("/api/v1/projects/test_project/files/unused.csv")

        assert response.status_code == 204
        assert not (tmp_path / "test_project" / "unused.csv").exists()
