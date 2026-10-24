"""Tests for validation and dependency API endpoints."""

import pytest

from backend.app.core.config import settings
from backend.app.services import dependency_service, project_service, validation_service, yaml_service

# pylint: disable=redefined-outer-name, unused-argument


@pytest.fixture
def reset_services():
    """Reset service singletons between tests."""

    project_service._project_service = None
    dependency_service._dependency_service = None
    validation_service._validation_service = None
    yaml_service._yaml_service = None

    yield

    project_service._project_service = None
    dependency_service._dependency_service = None
    validation_service._validation_service = None
    yaml_service._yaml_service = None


@pytest.fixture
def sample_entity_data():
    """Sample entity data for tests."""
    return {"type": "entity", "keys": ["id"], "columns": ["name", "value"]}


class TestEntityValidation:
    """Tests for entity validation endpoint."""

    async def test_validate_entity(self, tmp_path, monkeypatch, reset_services, sample_entity_data, authorized_client):
        """Test validating specific entity."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create config
        await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "test_project",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": {"sample": sample_entity_data},
            },
        )

        # Validate entity
        response = await authorized_client.post("/api/v1/projects/test_project/entities/sample/validate")
        assert response.status_code == 200
        data = response.json()
        assert "is_valid" in data
        assert "errors" in data
        assert "warnings" in data

    async def test_validate_entity_draft_uses_nested_draft_references_and_does_not_save(
        self, tmp_path, monkeypatch, reset_services, authorized_client
    ):
        """Validate nested references from the submitted entity and preserve the saved entity."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        project_name = "draft_validation"
        created = await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": project_name,
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": {
                    "site": {"type": "entity", "keys": ["site_id"], "columns": ["site_id"]},
                    "source": {
                        "type": "entity",
                        "keys": "@value: entities.site.keys",
                        "columns": ["site_id", "shared"],
                    },
                    "sample": {"type": "entity", "keys": ["saved"], "columns": ["saved"]},
                },
            },
        )
        assert created.status_code == 201

        response = await authorized_client.post(
            f"/api/v1/projects/{project_name}/entities/sample/validate-draft",
            json={
                "entity_draft": {
                    "type": "entity",
                    "keys": ["draft_missing"],
                    "columns": "@value: entities.source.keys",
                    "unnest": {
                        "id_vars": ["shared"],
                        "value_vars": ["shared"],
                        "var_name": "kind",
                        "value_name": "value",
                    },
                }
            },
        )

        assert response.status_code == 200
        result = response.json()
        missing_key = next(error for error in result["errors"] if error["code"] == "BUSINESS_KEY_NOT_PRODUCED")
        overlap = next(warning for warning in result["warnings"] if warning["code"] == "UNNEST_VARIABLE_OVERLAP")
        assert missing_key["entity"] == "sample"
        assert missing_key["related_columns"] == ["draft_missing"]
        assert overlap["entity"] == "sample"
        assert overlap["related_columns"] == ["shared"]

        saved = await authorized_client.get(f"/api/v1/projects/{project_name}/entities/sample")
        assert saved.status_code == 200
        assert saved.json()["entity_data"]["keys"] == ["saved"]
        assert saved.json()["entity_data"]["columns"] == ["saved"]

    async def test_validate_entity_draft_rename_keeps_saved_entity(self, tmp_path, monkeypatch, reset_services, authorized_client):
        """Apply the draft under its new name in the copied project only."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        project_name = "draft_validation_rename"
        created = await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": project_name,
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": {"sample": {"type": "entity", "keys": ["saved"], "columns": ["saved"]}},
            },
        )
        assert created.status_code == 201

        response = await authorized_client.post(
            f"/api/v1/projects/{project_name}/entities/renamed/validate-draft",
            json={
                "original_entity_name": "sample",
                "entity_draft": {"type": "entity", "keys": ["draft_missing"], "columns": ["present"]},
            },
        )

        assert response.status_code == 200
        missing_key = next(error for error in response.json()["errors"] if error["code"] == "BUSINESS_KEY_NOT_PRODUCED")
        assert missing_key["entity"] == "renamed"
        assert missing_key["related_columns"] == ["draft_missing"]
        saved = await authorized_client.get(f"/api/v1/projects/{project_name}/entities/sample")
        assert saved.status_code == 200
        assert saved.json()["entity_data"]["keys"] == ["saved"]
        missing_renamed_entity = await authorized_client.get(f"/api/v1/projects/{project_name}/entities/renamed")
        assert missing_renamed_entity.status_code == 404

    async def test_validate_entity_draft_reports_reference_and_mapping_errors(
        self, tmp_path, monkeypatch, reset_services, authorized_client
    ):
        """Keep unresolved draft references and mapper failures in the validation response."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        project_name = "draft_validation_errors"
        created = await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": project_name,
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": {"sample": {"type": "entity", "keys": ["saved"], "columns": ["saved"]}},
            },
        )
        assert created.status_code == 201

        unresolved = await authorized_client.post(
            f"/api/v1/projects/{project_name}/entities/sample/validate-draft",
            json={
                "entity_draft": {
                    "type": "entity",
                    "keys": ["sample_id"],
                    "columns": "@value: entities.missing.keys",
                }
            },
        )
        assert unresolved.status_code == 200
        assert any(error["code"] == "COLUMN_REFERENCE_MISSING_PATH" for error in unresolved.json()["errors"])

        from backend.app.services import validation_service as validation_service_module

        monkeypatch.setattr(validation_service_module.ProjectMapper, "to_core", lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("mapping failed")))
        mapping_failure = await authorized_client.post(
            f"/api/v1/projects/{project_name}/entities/sample/validate-draft",
            json={"entity_draft": {"type": "entity", "keys": ["sample_id"], "columns": ["sample_id"]}},
        )
        assert mapping_failure.status_code == 200
        assert any(error["code"] == "PROJECT_RESOLUTION_FAILED" for error in mapping_failure.json()["errors"])

    async def test_validate_entity_draft_requires_read_access_and_documents_contract(
        self, tmp_path, monkeypatch, reset_services, authorized_client
    ):
        """Require project read access and publish the request and response models."""
        from backend.app.main import app

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        created = await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "draft_validation_access",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": {"sample": {"type": "entity", "keys": ["sample_id"], "columns": ["sample_id"]}},
            },
        )
        assert created.status_code == 201

        from backend.app.authorization.service import AuthorizationService

        monkeypatch.setattr(AuthorizationService, "authorize", lambda *_args, **_kwargs: None)

        denied = await authorized_client.post(
            "/api/v1/projects/draft_validation_access/entities/sample/validate-draft",
            json={"entity_draft": {"type": "entity", "keys": [], "columns": []}},
        )
        assert denied.status_code == 404
        missing = await authorized_client.post(
            "/api/v1/projects/missing_project/entities/sample/validate-draft",
            json={"entity_draft": {"type": "entity", "keys": [], "columns": []}},
        )
        assert missing.status_code == 404

        operation = app.openapi()["paths"]["/api/v1/projects/{name}/entities/{entity_name}/validate-draft"]["post"]
        request_schema = operation["requestBody"]["content"]["application/json"]["schema"]["$ref"]
        response_schema = operation["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
        assert request_schema.endswith("/DraftEntityValidationRequest")
        assert response_schema.endswith("/ValidationResult")

    async def test_validate_entity_preserves_raw_reference_when_mapping_fails(
        self, tmp_path, monkeypatch, reset_services, authorized_client
    ):
        """Return the raw reference and include failure through the existing entity route."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        project_name = "entity_reference_failure"
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

        response = await authorized_client.post(f"/api/v1/projects/{project_name}/entities/sample/validate")

        assert response.status_code == 200
        data = response.json()
        codes = [error["code"] for error in data["errors"]]
        assert "COLUMN_REFERENCE_MISSING_PATH" in codes
        assert "CONFIG_INCLUDE_NOT_FOUND" in codes
        reference_error = next(error for error in data["errors"] if error["code"] == "COLUMN_REFERENCE_MISSING_PATH")
        assert reference_error["entity"] == "sample"
        assert reference_error["field"] == "columns"
        assert saved_reference in reference_error["message"]

    async def test_validate_data_skips_row_checks_for_saved_reference_errors(
        self, tmp_path, monkeypatch, reset_services, authorized_client
    ):
        """Return structural reference errors from the existing data-validation route."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        project_name = "data_reference_failure"
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

        response = await authorized_client.post(f"/api/v1/projects/{project_name}/validate/data")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "skipped"
        assert data["error_count"] > 0
        assert any(error["code"] == "COLUMN_REFERENCE_MISSING_PATH" and saved_reference in error["message"] for error in data["errors"])

    async def test_validate_nonexistent_entity(self, tmp_path, monkeypatch, reset_services, sample_entity_data, authorized_client):
        """Test validating non-existent entity."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create config
        await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "test_project",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": {"sample": sample_entity_data},
            },
        )

        # Validate non-existent entity - returns validation result with no entity-specific errors
        response = await authorized_client.post("/api/v1/projects/test_project/entities/nonexistent/validate")
        assert response.status_code == 200
        data = response.json()
        # Since the entity doesn't exist, there are no errors specific to it
        assert "is_valid" in data
        assert "errors" in data

    async def test_validate_entity_nonexistent_config(self, tmp_path, monkeypatch, reset_services, authorized_client):
        """Test validating entity in non-existent configuration."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Validate entity in non-existent config
        response = await authorized_client.post("/api/v1/projects/nonexistent/entities/sample/validate")
        assert response.status_code == 404


class TestDependencies:
    """Tests for dependency analysis endpoints."""

    async def test_get_dependencies_simple(self, tmp_path, monkeypatch, reset_services, sample_entity_data, authorized_client):
        """Test getting dependency graph with simple dependencies."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create config with dependencies
        entities = {
            "base": {**sample_entity_data, "type": "sql", "data_source": "test_db", "table": "base_table"},
            "derived": {
                **sample_entity_data,
                "type": "sql",
                "data_source": "test_db",
                "source": "base",
                "foreign_keys": [{"entity": "base", "local_keys": ["base_id"], "remote_keys": ["id"]}],
            },
        }
        expected_graph = {
            "nodes": [
                # Two nodes: base and derived
                {"name": "base", "depends_on": [], "depth": 1, "type": "sql", "materialized": False},
                {"name": "derived", "depends_on": ["base"], "depth": 0, "type": "sql", "materialized": False},
            ],
            "edges": [
                # FK dependency from derived to base
                {"source": "base", "target": "derived", "type": "provides", "label": "provides"},
                {"source": "derived", "target": "base", "local_keys": ["base_id"], "remote_keys": ["id"], "label": "base_id → id"},
            ],
            "has_cycles": False,
            "cycles": [],
            "topological_order": ["derived", "base"],
            "source_nodes": [
                {"name": "source:test_db", "source_type": "database", "type": "datasource", "metadata": {"datasource": "test_db"}}
            ],
            "source_edges": [],
        }

        await authorized_client.post(
            "/api/v1/projects",
            json={"name": "test_project", "data_provider_code": "test-provider", "provider_schema": "schema-one", "entities": entities},
        )

        # Get dependencies
        response = await authorized_client.get("/api/v1/projects/test_project/dependencies")
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert "edges" in data
        assert "has_cycles" in data
        assert "topological_order" in data
        assert data["nodes"] == expected_graph["nodes"]
        assert data["edges"] == expected_graph["edges"]

    async def test_get_dependencies_no_deps(self, tmp_path, monkeypatch, reset_services, sample_entity_data, authorized_client):
        """Test getting dependency graph with no dependencies."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create config without dependencies
        entities = {"entity1": sample_entity_data, "entity2": sample_entity_data}
        await authorized_client.post(
            "/api/v1/projects",
            json={"name": "test_project", "data_provider_code": "test-provider", "provider_schema": "schema-one", "entities": entities},
        )

        # Get dependencies
        response = await authorized_client.get("/api/v1/projects/test_project/dependencies")
        assert response.status_code == 200
        data = response.json()
        assert len(data["nodes"]) == 2
        assert len(data["edges"]) == 0
        assert data["has_cycles"] is False

    async def test_get_dependencies_with_cycles(self, tmp_path, monkeypatch, reset_services, authorized_client):
        """Test getting dependency graph with circular dependencies."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create config with circular dependencies
        entities = {
            "entity1": {"type": "entity", "keys": ["id"], "source": "entity2"},
            "entity2": {"type": "entity", "keys": ["id"], "source": "entity1"},
        }
        await authorized_client.post(
            "/api/v1/projects",
            json={"name": "test_project", "data_provider_code": "test-provider", "provider_schema": "schema-one", "entities": entities},
        )

        # Get dependencies
        response = await authorized_client.get("/api/v1/projects/test_project/dependencies")
        assert response.status_code == 200
        data = response.json()
        assert data["has_cycles"] is True
        assert len(data["cycles"]) > 0

    async def test_get_dependencies_nonexistent_config(self, tmp_path, monkeypatch, reset_services, authorized_client):
        """Test getting dependencies for non-existent configuration."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Get dependencies for non-existent config
        response = await authorized_client.get("/api/v1/projects/nonexistent/dependencies")
        assert response.status_code == 404


class TestCircularDependencyCheck:
    """Tests for circular dependency check endpoint."""

    async def test_check_no_cycles(self, tmp_path, monkeypatch, reset_services, sample_entity_data, authorized_client):
        """Test checking for circular dependencies when none exist."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create config without cycles
        entities = {
            "base": sample_entity_data,
            "derived": {**sample_entity_data, "source": "base"},
        }
        await authorized_client.post(
            "/api/v1/projects",
            json={"name": "test_project", "data_provider_code": "test-provider", "provider_schema": "schema-one", "entities": entities},
        )

        # Check dependencies
        response = await authorized_client.post("/api/v1/projects/test_project/dependencies/check")
        assert response.status_code == 200
        data = response.json()
        assert data["has_cycles"] is False
        assert data["cycle_count"] == 0
        assert len(data["cycles"]) == 0

    async def test_check_with_cycles(self, tmp_path, monkeypatch, reset_services, authorized_client):
        """Test checking for circular dependencies when they exist."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create config with circular dependencies
        entities = {
            "entity1": {"type": "entity", "keys": ["id"], "source": "entity2"},
            "entity2": {"type": "entity", "keys": ["id"], "source": "entity1"},
        }
        await authorized_client.post(
            "/api/v1/projects",
            json={"name": "test_project", "data_provider_code": "test-provider", "provider_schema": "schema-one", "entities": entities},
        )

        # Check dependencies
        response = await authorized_client.post("/api/v1/projects/test_project/dependencies/check")
        assert response.status_code == 200
        data = response.json()
        assert data["has_cycles"] is True
        assert data["cycle_count"] > 0
        assert len(data["cycles"]) > 0

    async def test_check_dependencies_nonexistent_config(self, tmp_path, monkeypatch, reset_services, authorized_client):
        """Test checking dependencies for non-existent configuration."""

        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Check dependencies for non-existent config
        response = await authorized_client.post("/api/v1/projects/nonexistent/dependencies/check")
        assert response.status_code == 404
