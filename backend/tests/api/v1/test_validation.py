"""Tests for validation and dependency API endpoints."""

import pytest
import yaml

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

    async def test_data_validation_returns_fixed_entity_load_errors(
        self, tmp_path, monkeypatch, reset_services, sample_entity_data, authorized_client
    ):
        """Data validation returns load-time coercion errors instead of an empty successful result."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        create_response = await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "test_project",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": {"sample": sample_entity_data},
            },
        )
        assert create_response.status_code == 201, create_response.text

        project_file = tmp_path / "test_project" / "shapeshifter.yml"
        project_yaml = yaml.safe_load(project_file.read_text(encoding="utf-8"))
        project_yaml["entities"]["method"] = {
            "type": "fixed",
            "keys": ["method_id"],
            "columns": ["method_id"],
            "column_types": {"method_id": "int"},
            "values": [["not-an-integer"]],
        }
        project_file.write_text(yaml.safe_dump(project_yaml, sort_keys=False), encoding="utf-8")

        reload_response = await authorized_client.post("/api/v1/projects/test_project/refresh")
        assert reload_response.status_code == 200, reload_response.text
        assert reload_response.json()["load_errors"][0]["code"] == "FIXED_ENTITY_VALUE_INVALID"

        response = await authorized_client.post("/api/v1/projects/test_project/validate/data")

        assert response.status_code == 200, response.text
        result = response.json()
        assert result["is_valid"] is False
        assert result["status"] == "failed"
        assert any(issue["code"] == "FIXED_ENTITY_VALUE_INVALID" for issue in result["errors"])
        assert any(issue["suggestion"] for issue in result["errors"])

    async def test_missing_target_model_reference_is_not_reported_as_valid(
        self, tmp_path, monkeypatch, reset_services, sample_entity_data, authorized_client
    ):
        """Conformance validation reports missing configured files as errors."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        create_response = await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "test_project",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": {"sample": sample_entity_data},
            },
        )
        assert create_response.status_code == 201, create_response.text

        project_file = tmp_path / "test_project" / "shapeshifter.yml"
        project_yaml = yaml.safe_load(project_file.read_text(encoding="utf-8"))
        project_yaml["metadata"]["target_model"] = "@load: missing-target-model.yml"
        project_file.write_text(yaml.safe_dump(project_yaml, sort_keys=False), encoding="utf-8")

        reload_response = await authorized_client.post("/api/v1/projects/test_project/refresh")
        assert reload_response.status_code == 200, reload_response.text

        response = await authorized_client.post("/api/v1/projects/test_project/validate/target-model")

        assert response.status_code == 200, response.text
        result = response.json()
        assert result["is_valid"] is False
        assert result["errors"][0]["code"] == "TARGET_MODEL_LOAD_FAILED"
        assert result["errors"][0]["suggestion"]

    async def test_incomplete_target_entity_reports_remaining_gaps(self, tmp_path, monkeypatch, reset_services, authorized_client):
        """Structural validation accepts the saved entity while target validation reports its missing requirements."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        create_response = await authorized_client.post(
            "/api/v1/projects",
            json={
                "name": "test_project",
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": {
                    "sample": {
                        "type": "fixed",
                        "public_id": "sample_id",
                        "keys": ["sample_name"],
                        "columns": ["sample_name"],
                        "values": [["Sample"]],
                    }
                },
            },
        )
        assert create_response.status_code == 201, create_response.text

        raw_yaml_response = await authorized_client.get("/api/v1/projects/test_project/raw-yaml")
        assert raw_yaml_response.status_code == 200, raw_yaml_response.text
        project_yaml = yaml.safe_load(raw_yaml_response.json()["yaml_content"])
        project_yaml["metadata"]["target_model"] = {
            "model": {"name": "Test Target Model", "version": "1.0.0"},
            "entities": {
                "sample": {
                    "required": True,
                    "public_id": "sample_id",
                    "columns": {"target_name": {"required": True}},
                    "foreign_keys": [{"entity": "lookup", "required": True}],
                },
                "lookup": {"public_id": "lookup_id"},
            },
        }
        update_response = await authorized_client.put(
            "/api/v1/projects/test_project/raw-yaml",
            json={"yaml_content": yaml.safe_dump(project_yaml, sort_keys=False)},
        )
        assert update_response.status_code == 200, update_response.text

        structural_response = await authorized_client.post("/api/v1/projects/test_project/entities/sample/validate")
        assert structural_response.status_code == 200, structural_response.text
        structural_result = structural_response.json()
        assert structural_result["is_valid"] is True
        assert structural_result["errors"] == []

        target_model_response = await authorized_client.post("/api/v1/projects/test_project/validate/target-model")
        assert target_model_response.status_code == 200, target_model_response.text
        target_model_result = target_model_response.json()
        assert target_model_result["is_valid"] is False
        assert {(error["entity"], error["code"]) for error in target_model_result["errors"]} >= {
            ("sample", "MISSING_REQUIRED_COLUMN"),
            ("sample", "MISSING_REQUIRED_FOREIGN_KEY_TARGET"),
        }

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
