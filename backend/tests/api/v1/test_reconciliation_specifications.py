"""Tests for reconciliation specification management API endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml
from fastapi.testclient import TestClient

from backend.app import models as dto
from backend.app.core.config import settings
from backend.app.main import app
from backend.app.models.reconciliation import ReconciliationRemote
from backend.app.services import project_service, validation_service, yaml_service

# pylint: disable=redefined-outer-name, unused-argument

client = TestClient(app)


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


@pytest.fixture
def sample_project(tmp_path):
    """Create sample project configuration."""
    project_data = {
        "metadata": {
            "type": "shapeshifter-project",
            "name": "test_project",
            "description": "A test project",
            "version": "1.0.0",
        },
        "entities": {
            "site": {
                "type": "sql",
                "data_source": "test_db",
                "keys": ["site_code"],
                "columns": ["site_name", "latitude", "longitude"],
            },
            "sample": {
                "type": "sql",
                "data_source": "test_db",
                "keys": ["sample_code"],
                "columns": ["sample_type"],
            },
        },
    }

    project_file = tmp_path / "test_project.yml"
    with open(project_file, "w", encoding="utf-8") as f:
        yaml.dump(project_data, f)

    return project_file


@pytest.fixture
def sample_recon_config(tmp_path):
    """Create sample reconciliation configuration."""
    config = dto.EntityResolutionCatalog(
        version="2.0",
        service_url="http://localhost:8000",
        entities={
            "site": {
                "site_code": dto.EntityResolutionSet(
                    source=None,
                    property_mappings={"latitude": "latitude", "longitude": "longitude"},
                    remote=ReconciliationRemote(service_type="site"),
                    auto_accept_threshold=0.95,
                    review_threshold=0.70,
                    mapping=[],
                ),
                "site_name": dto.EntityResolutionSet(
                    source="another_entity",
                    property_mappings={},
                    remote=ReconciliationRemote(service_type="taxon"),
                    auto_accept_threshold=0.85,
                    review_threshold=0.60,
                    mapping=[
                        dto.ResolvedEntityPair(source_value="test1", target_id=1, confidence=0.98, notes="Auto-matched", **{}),
                        dto.ResolvedEntityPair(source_value="test2", target_id=2, confidence=0.85, notes="Auto-matched", **{}),
                    ],
                ),
            }
        },
    )

    config_file = tmp_path / "test_project-reconciliation.yml"
    with open(config_file, "w", encoding="utf-8") as f:
        yaml.dump(config.model_dump(exclude_none=True), f)

    return config_file


class TestListSpecifications:
    """Tests for GET /api/v1/reconcile/specifications endpoint."""

    def test_list_specifications_success(self, tmp_path, monkeypatch, reset_services, sample_project, sample_recon_config):
        """Test listing specifications successfully."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        response = client.get("/api/v1/projects/test_project/reconciliation/mapping-registry")

        assert response.status_code == 200
        specs = response.json()
        assert len(specs) == 2

        # Check site.site_code spec
        site_code = next(s for s in specs if s["target_field"] == "site_code")
        assert site_code["entity_name"] == "site"
        assert site_code["mapping_count"] == 0
        assert site_code["property_mapping_count"] == 2
        assert site_code["remote"]["service_type"] == "site"

        # Check site.site_name spec
        site_name = next(s for s in specs if s["target_field"] == "site_name")
        assert site_name["mapping_count"] == 2
        assert site_name["source"] == "another_entity"

    def test_list_specifications_empty(self, tmp_path, monkeypatch, reset_services, sample_project):
        """Test listing when no specifications exist."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create empty recon config
        config = dto.EntityResolutionCatalog(version="2.0", service_url="http://localhost:8000", entities={})
        config_file = tmp_path / "test_project-reconciliation.yml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config.model_dump(exclude_none=True), f)

        response = client.get("/api/v1/projects/test_project/reconciliation/mapping-registry")

        assert response.status_code == 200
        assert response.json() == []

    def test_list_specifications_no_config(self, tmp_path, monkeypatch, reset_services, sample_project):
        """Test listing when no reconciliation config exists."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        response = client.get("/api/v1/projects/test_project/reconciliation/mapping-registry")

        # Service auto-creates empty config when none exists
        assert response.status_code == 200
        assert response.json() == []


class TestCreateSpecification:
    """Tests for POST /api/v1/reconcile/specifications endpoint."""

    @patch("backend.app.services.reconciliation.service.ProjectMapper")
    def test_create_specification_success(self, mock_mapper, tmp_path, monkeypatch, reset_services, sample_project, sample_recon_config):
        """Test creating new specification."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Mock entity validation
        mock_mapper_instance = MagicMock()
        mock_mapper_instance.to_core_config.return_value = MagicMock(entities={"site": MagicMock(), "sample": MagicMock()})
        mock_mapper.return_value = mock_mapper_instance

        payload = {
            "entity_name": "sample",
            "target_field": "sample_type",
            "spec": {
                "source": None,
                "property_mappings": {"name": "type_name"},
                "remote": {"service_type": "location"},
                "auto_accept_threshold": 0.90,
                "review_threshold": 0.75,
                "mapping": [],
            },
        }

        response = client.post("/api/v1/projects/test_project/reconciliation/mapping-registry", json=payload)

        assert response.status_code == 201
        config = response.json()
        assert "sample" in config["entities"]
        assert "sample_type" in config["entities"]["sample"]

    @patch("backend.app.services.reconciliation.service.ProjectMapper")
    def test_create_specification_duplicate(self, mock_mapper, tmp_path, monkeypatch, reset_services, sample_project, sample_recon_config):
        """Test creating duplicate specification fails."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        mock_mapper_instance = MagicMock()
        mock_mapper_instance.to_core_config.return_value = MagicMock(entities={"site": MagicMock()})
        mock_mapper.return_value = mock_mapper_instance

        payload = {
            "entity_name": "site",
            "target_field": "site_code",
            "spec": {
                "source": None,
                "property_mappings": {},
                "remote": {"service_type": "site"},
                "auto_accept_threshold": 0.95,
                "review_threshold": 0.70,
                "mapping": [],
            },
        }

        response = client.post("/api/v1/projects/test_project/reconciliation/mapping-registry", json=payload)

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    @patch("backend.app.services.reconciliation.service.ProjectMapper")
    def test_create_specification_invalid_entity(
        self, mock_mapper, tmp_path, monkeypatch, reset_services, sample_project, sample_recon_config
    ):
        """Test creating specification for non-existent entity fails."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        mock_mapper_instance = MagicMock()
        mock_mapper_instance.to_core_config.return_value = MagicMock(entities={"site": MagicMock()})
        mock_mapper.return_value = mock_mapper_instance

        payload = {
            "entity_name": "invalid_entity",
            "target_field": "some_field",
            "spec": {
                "source": None,
                "property_mappings": {},
                "remote": {"service_type": "site"},
                "auto_accept_threshold": 0.95,
                "review_threshold": 0.70,
                "mapping": [],
            },
        }

        response = client.post("/api/v1/projects/test_project/reconciliation/mapping-registry", json=payload)

        assert response.status_code == 400
        assert "does not exist" in response.json()["detail"]


class TestUpdateSpecification:
    """Tests for PUT /api/v1/reconcile/specifications/{entity_name}/{target_field} endpoint."""

    def test_update_specification_success(self, tmp_path, monkeypatch, reset_services, sample_project, sample_recon_config):
        """Test updating specification."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        payload = {
            "source": "other_source",
            "property_mappings": {"new_prop": "new_col"},
            "remote": {"service_type": "taxon"},
            "auto_accept_threshold": 0.80,
            "review_threshold": 0.60,
        }

        response = client.put("/api/v1/projects/test_project/reconciliation/mapping-registry/site/site_code", json=payload)

        assert response.status_code == 200
        config = response.json()
        spec = config["entities"]["site"]["site_code"]
        assert spec["auto_accept_threshold"] == 0.80
        assert spec["review_threshold"] == 0.60
        assert spec["source"] == "other_source"
        assert spec["property_mappings"] == {"new_prop": "new_col"}

    def test_update_specification_preserves_mapping(self, tmp_path, monkeypatch, reset_services, sample_project, sample_recon_config):
        """Test that updating preserves existing mappings."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        payload = {
            "source": None,
            "property_mappings": {},
            "remote": {"service_type": "taxon"},
            "auto_accept_threshold": 0.90,
            "review_threshold": 0.75,
        }

        response = client.put("/api/v1/projects/test_project/reconciliation/mapping-registry/site/site_name", json=payload)

        assert response.status_code == 200
        spec = response.json()["entities"]["site"]["site_name"]
        # Original spec had 2 mappings
        assert len(spec["mapping"]) == 2

    def test_update_specification_not_found(self, tmp_path, monkeypatch, reset_services, sample_project, sample_recon_config):
        """Test updating non-existent specification fails."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        payload = {
            "source": None,
            "property_mappings": {},
            "remote": {"service_type": "site"},
            "auto_accept_threshold": 0.95,
            "review_threshold": 0.70,
        }

        response = client.put("/api/v1/projects/test_project/reconciliation/mapping-registry/site/nonexistent", json=payload)

        assert response.status_code == 404


class TestDeleteSpecification:
    """Tests for DELETE /api/v1/reconcile/specifications/{entity_name}/{target_field} endpoint."""

    def test_delete_specification_success(self, tmp_path, monkeypatch, reset_services, sample_project, sample_recon_config):
        """Test deleting specification without mappings."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        response = client.delete("/api/v1/projects/test_project/reconciliation/mapping-registry/site/site_code")

        assert response.status_code == 200
        config = response.json()
        # site_code should be removed, but site_name should remain
        assert "site_code" not in config["entities"]["site"]
        assert "site_name" in config["entities"]["site"]

    def test_delete_specification_with_mappings_no_force(self, tmp_path, monkeypatch, reset_services, sample_project, sample_recon_config):
        """Test deleting specification with mappings fails without force."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        response = client.delete("/api/v1/projects/test_project/reconciliation/mapping-registry/site/site_name")

        assert response.status_code == 400
        assert "Cannot delete existing mapping" in response.json()["detail"]
        assert "from catalog" in response.json()["detail"]

    def test_delete_specification_with_mappings_force(self, tmp_path, monkeypatch, reset_services, sample_project, sample_recon_config):
        """Test force deleting specification with mappings succeeds."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        response = client.delete("/api/v1/projects/test_project/reconciliation/mapping-registry/site/site_name?force=true")

        assert response.status_code == 200
        config = response.json()
        assert "site_name" not in config["entities"]["site"]

    def test_delete_specification_not_found(self, tmp_path, monkeypatch, reset_services, sample_project, sample_recon_config):
        """Test deleting non-existent specification fails."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        response = client.delete("/api/v1/projects/test_project/reconciliation/mapping-registry/site/nonexistent")

        assert response.status_code == 404


class TestGetAvailableFields:
    """Tests for GET /api/v1/reconcile/available-fields/{entity_name} endpoint."""

    @patch("backend.app.services.reconciliation.service.ShapeShiftService")
    async def test_get_available_fields_success(
        self, mock_shapeshift, tmp_path, monkeypatch, reset_services, sample_project, sample_recon_config
    ):
        """Test getting available fields."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Mock preview service
        mock_preview_result = MagicMock()
        mock_preview_result.columns = [
            MagicMock(name="site_code"),
            MagicMock(name="site_name"),
            MagicMock(name="latitude"),
            MagicMock(name="longitude"),
        ]

        mock_service_instance = MagicMock()
        mock_service_instance.preview_entity = AsyncMock(return_value=mock_preview_result)
        mock_shapeshift.return_value = mock_service_instance

        response = client.get("/api/v1/projects/test_project/reconciliation/available-fields/site")

        assert response.status_code == 200
        fields = response.json()
        assert fields == ["site_code", "site_name", "latitude", "longitude"]


class TestGetMappingCount:
    """Tests for GET /api/v1/reconcile/specifications/{entity_name}/{target_field}/mapping-count endpoint."""

    def test_get_mapping_count_success(self, tmp_path, monkeypatch, reset_services, sample_project, sample_recon_config):
        """Test getting mapping count."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        response = client.get("/api/v1/projects/test_project/reconciliation/mapping-registry/site/site_name/mapping-count")

        assert response.status_code == 200
        result = response.json()
        assert result["count"] == 2

    def test_get_mapping_count_zero(self, tmp_path, monkeypatch, reset_services, sample_project, sample_recon_config):
        """Test getting mapping count when no mappings exist."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        response = client.get("/api/v1/projects/test_project/reconciliation/mapping-registry/site/site_code/mapping-count")

        assert response.status_code == 200
        result = response.json()
        assert result["count"] == 0

    def test_get_mapping_count_not_found(self, tmp_path, monkeypatch, reset_services, sample_project, sample_recon_config):
        """Test getting mapping count for non-existent specification."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        response = client.get("/api/v1/projects/test_project/reconciliation/mapping-registry/site/nonexistent/mapping-count")

        assert response.status_code == 404
