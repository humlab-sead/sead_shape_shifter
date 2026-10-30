"""Tests for reconciliation specification management API endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml

from backend.app import models as dto
from backend.app.core.config import settings
from backend.app.models.reconciliation import ReconciliationRemote
from backend.app.services import project_service, validation_service, yaml_service
from backend.app.services.reconciliation.mapping_manager import EntityMappingManager
from src.reconciliation.mapping_manager import MappingManager, MappingVersionConflictError

# pylint: disable=redefined-outer-name, unused-argument


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
async def sample_project(tmp_path, monkeypatch, authorized_client):
    """Create a sample project through the API so it is registered as an authorized resource.

    Returns:
        Path to the on-disk project file written by the API create endpoint.
    """
    monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

    project_entities = {
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
    }

    response = await authorized_client.post(
        "/api/v1/projects",
        json={
            "name": "test_project",
            "data_provider_code": "test-provider",
            "provider_schema": "schema-one",
            "entities": project_entities,
        },
    )
    assert response.status_code == 201, response.text

    return tmp_path / "test_project" / "shapeshifter.yml"


@pytest.fixture
def sample_recon_config(tmp_path):
    """Create sample reconciliation configuration."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir(exist_ok=True)

    config = dto.EntityResolutionCatalog(
        version="3.0",
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
                        dto.ResolvedEntityPair(
                            local_key_value="site-1", source_value="test1", status="accepted", target_id=1, confidence=0.98,
                        ),
                        dto.ResolvedEntityPair(
                            local_key_value="site-2", source_value="test2", status="accepted", target_id=2, confidence=0.85
                        ),
                    ],
                ),
            }
        },
    )

    config_file = project_dir / "test_project-reconciliation.yml"
    with open(config_file, "w", encoding="utf-8") as f:
        yaml.dump(config.model_dump(exclude_none=True), f)

    return config_file


def _write_mapping_sidecar(tmp_path, links: dict[str, dict]) -> None:
    project_dir = tmp_path / "test_project"
    sidecar = {
        "version": "2.0",
        "metadata": {
            "project": "test_project",
            "created_at": "2026-06-15T00:00:00Z",
            "updated_at": "2026-06-15T00:00:00Z",
        },
        "entities": {
            "site": {
                "local_key": "site_code",
                "public_id": "site_id",
                "entity_type": "primary",
                "links": links,
            }
        },
    }
    (project_dir / "test_project-mapping.yml").write_text(yaml.safe_dump(sidecar, sort_keys=False), encoding="utf-8")


def _owned_link(owner: str, field: str, target_id: int = 101) -> dict:
    return {
        "target_id": target_id,
        "source": "reconciliation",
        "created_at": "2026-06-15T00:00:00Z",
        "committed_at": "2026-06-15T00:00:00Z",
        "owner": {"entity_name": owner, "target_field": field},
        "verified_at": None,
        "created_by": "reconciliation",
    }


class TestListSpecifications:
    """Tests for GET /api/v1/reconcile/specifications endpoint."""

    async def test_list_specifications_success(
        self, tmp_path, monkeypatch, reset_services, sample_project, sample_recon_config, authorized_client
    ):
        """Test listing specifications successfully."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        response = await authorized_client.get("/api/v1/projects/test_project/reconciliation/mapping-registry")

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

    async def test_list_specifications_empty(self, tmp_path, monkeypatch, reset_services, sample_project, authorized_client):
        """Test listing when no specifications exist."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        # Create empty recon config in nested project structure
        config = dto.EntityResolutionCatalog(version="3.0", service_url="http://localhost:8000", entities={})
        config_file = tmp_path / "test_project" / "test_project-reconciliation.yml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config.model_dump(exclude_none=True), f)

        response = await authorized_client.get("/api/v1/projects/test_project/reconciliation/mapping-registry")

        assert response.status_code == 200
        assert response.json() == []

    async def test_list_specifications_no_config(self, tmp_path, monkeypatch, reset_services, sample_project, authorized_client):
        """Test listing when no reconciliation config exists."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        response = await authorized_client.get("/api/v1/projects/test_project/reconciliation/mapping-registry")

        # Service auto-creates empty config when none exists
        assert response.status_code == 200
        assert response.json() == []


class TestCreateSpecification:
    """Tests for POST /api/v1/reconcile/specifications endpoint."""

    @patch("backend.app.services.reconciliation.service.ProjectMapper")
    async def test_create_specification_success(
        self, mock_mapper, tmp_path, monkeypatch, reset_services, sample_project, sample_recon_config, authorized_client
    ):
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

        response = await authorized_client.post("/api/v1/projects/test_project/reconciliation/mapping-registry", json=payload)

        assert response.status_code == 201
        config = response.json()
        assert "sample" in config["entities"]
        assert "sample_type" in config["entities"]["sample"]

    @patch("backend.app.services.reconciliation.service.ProjectMapper")
    async def test_create_specification_duplicate(
        self, mock_mapper, tmp_path, monkeypatch, reset_services, sample_project, sample_recon_config, authorized_client
    ):
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

        response = await authorized_client.post("/api/v1/projects/test_project/reconciliation/mapping-registry", json=payload)

        assert response.status_code == 409, response.text
        detail = response.json()["detail"]
        assert "already exists" in detail["message"]

    @patch("backend.app.services.reconciliation.service.ProjectMapper")
    async def test_create_specification_invalid_entity(
        self, mock_mapper, tmp_path, monkeypatch, reset_services, sample_project, sample_recon_config, authorized_client
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

        response = await authorized_client.post("/api/v1/projects/test_project/reconciliation/mapping-registry", json=payload)

        assert response.status_code == 400
        detail = response.json()["detail"]
        assert "does not exist" in detail["message"]


class TestUpdateSpecification:
    """Tests for PUT /api/v1/reconcile/specifications/{entity_name}/{target_field} endpoint."""

    async def test_update_specification_success(
        self, tmp_path, monkeypatch, reset_services, sample_project, sample_recon_config, authorized_client
    ):
        """Test updating specification."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        payload = {
            "source": "other_source",
            "property_mappings": {"new_prop": "new_col"},
            "remote": {"service_type": "taxon"},
            "auto_accept_threshold": 0.80,
            "review_threshold": 0.60,
        }

        response = await authorized_client.put("/api/v1/projects/test_project/reconciliation/mapping-registry/site/site_code", json=payload)

        assert response.status_code == 200
        config = response.json()
        spec = config["entities"]["site"]["site_code"]
        assert spec["auto_accept_threshold"] == 0.80
        assert spec["review_threshold"] == 0.60
        assert spec["source"] == "other_source"
        assert spec["property_mappings"] == {"new_prop": "new_col"}

    async def test_update_specification_preserves_mapping(
        self, tmp_path, monkeypatch, reset_services, sample_project, sample_recon_config, authorized_client
    ):
        """Test that updating preserves existing mappings."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        payload = {
            "source": None,
            "property_mappings": {},
            "remote": {"service_type": "taxon"},
            "auto_accept_threshold": 0.90,
            "review_threshold": 0.75,
        }

        response = await authorized_client.put("/api/v1/projects/test_project/reconciliation/mapping-registry/site/site_name", json=payload)

        assert response.status_code == 200
        spec = response.json()["entities"]["site"]["site_name"]
        # Original spec had 2 mappings
        assert len(spec["mapping"]) == 2

    async def test_update_specification_not_found(
        self, tmp_path, monkeypatch, reset_services, sample_project, sample_recon_config, authorized_client
    ):
        """Test updating non-existent specification fails."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        payload = {
            "source": None,
            "property_mappings": {},
            "remote": {"service_type": "site"},
            "auto_accept_threshold": 0.95,
            "review_threshold": 0.70,
        }

        response = await authorized_client.put(
            "/api/v1/projects/test_project/reconciliation/mapping-registry/site/nonexistent", json=payload
        )

        assert response.status_code == 404


class TestDeleteSpecification:
    """Tests for DELETE /api/v1/reconcile/specifications/{entity_name}/{target_field} endpoint."""

    async def test_delete_specification_success(
        self, tmp_path, monkeypatch, reset_services, sample_project, sample_recon_config, authorized_client
    ):
        """Test deleting specification without mappings."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        response = await authorized_client.delete("/api/v1/projects/test_project/reconciliation/mapping-registry/site/site_code")

        assert response.status_code == 200
        config = response.json()
        # site_code should be removed, but site_name should remain
        assert "site_code" not in config["entities"]["site"]
        assert "site_name" in config["entities"]["site"]
        assert set(config) == {"version", "service_url", "entities", "removed_owned_links"}
        assert config["removed_owned_links"] == 0

    async def test_delete_specification_with_mappings_no_force(
        self, tmp_path, monkeypatch, reset_services, sample_project, sample_recon_config, authorized_client
    ):
        """Test deleting specification with mappings fails without force."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        response = await authorized_client.delete("/api/v1/projects/test_project/reconciliation/mapping-registry/site/site_name")

        assert response.status_code == 400
        detail = response.json()["detail"]
        assert "Cannot delete existing mapping" in detail["message"]
        assert "from catalog" in detail["message"]

    async def test_delete_specification_with_mappings_force(
        self, tmp_path, monkeypatch, reset_services, sample_project, sample_recon_config, authorized_client
    ):
        """Test force deleting specification with mappings succeeds."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        response = await authorized_client.delete("/api/v1/projects/test_project/reconciliation/mapping-registry/site/site_name?force=true")

        assert response.status_code == 200
        config = response.json()
        assert "site_name" not in config["entities"]["site"]

    async def test_delete_removes_only_links_owned_by_the_specification(
        self, tmp_path, monkeypatch, reset_services, sample_project, sample_recon_config, authorized_client
    ):
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        _write_mapping_sidecar(
            tmp_path,
            {
                "owned-name": _owned_link("site", "site_name"),
                "owned-code": _owned_link("site", "site_code"),
                "other-owner": _owned_link("sample", "sample_code"),
                "manual": {"target_id": 202, "source": "manual", "created_by": "operator"},
                "unowned": {"target_id": 303, "source": "reconciliation", "created_by": "legacy"},
            },
        )

        response = await authorized_client.delete("/api/v1/projects/test_project/reconciliation/mapping-registry/site/site_name?force=true")

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["removed_owned_links"] == 1
        assert set(body) == {"version", "service_url", "entities", "removed_owned_links"}
        assert "site_name" not in body["entities"]["site"]
        sidecar = yaml.safe_load((tmp_path / "test_project" / "test_project-mapping.yml").read_text(encoding="utf-8"))
        links = sidecar["entities"]["site"]["links"]
        assert "owned-name" not in links
        assert {"owned-code", "other-owner", "manual", "unowned"} <= links.keys()

    async def test_empty_specification_delete_cleans_previously_owned_links(
        self, tmp_path, monkeypatch, reset_services, sample_project, sample_recon_config, authorized_client
    ):
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        _write_mapping_sidecar(tmp_path, {"owned-code": _owned_link("site", "site_code")})

        response = await authorized_client.delete("/api/v1/projects/test_project/reconciliation/mapping-registry/site/site_code")

        assert response.status_code == 200, response.text
        assert response.json()["removed_owned_links"] == 1
        sidecar = yaml.safe_load((tmp_path / "test_project" / "test_project-mapping.yml").read_text(encoding="utf-8"))
        assert sidecar["entities"]["site"]["links"] == {}

    async def test_sidecar_version_conflict_keeps_specification_and_sidecar(
        self, tmp_path, monkeypatch, reset_services, sample_project, sample_recon_config, authorized_client
    ):
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        _write_mapping_sidecar(tmp_path, {"owned-code": _owned_link("site", "site_code")})
        sidecar_path = tmp_path / "test_project" / "test_project-mapping.yml"
        original_sidecar = sidecar_path.read_bytes()

        def fail_save(*_args, **_kwargs):
            raise MappingVersionConflictError("external write")

        monkeypatch.setattr(MappingManager, "save", fail_save)
        response = await authorized_client.delete("/api/v1/projects/test_project/reconciliation/mapping-registry/site/site_code")

        assert response.status_code == 409
        assert "changed during specification removal" in response.json()["detail"]["message"]
        assert sidecar_path.read_bytes() == original_sidecar
        catalog = yaml.safe_load((tmp_path / "test_project" / "test_project-reconciliation.yml").read_text(encoding="utf-8"))
        assert "site_code" in catalog["entities"]["site"]

    async def test_sidecar_write_failure_keeps_specification(
        self, tmp_path, monkeypatch, reset_services, sample_project, sample_recon_config, authorized_client
    ):
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        _write_mapping_sidecar(tmp_path, {"owned-code": _owned_link("site", "site_code")})
        sidecar_path = tmp_path / "test_project" / "test_project-mapping.yml"
        original_sidecar = sidecar_path.read_bytes()

        def fail_save(*_args, **_kwargs):
            raise OSError("sidecar write failed")

        monkeypatch.setattr(MappingManager, "save", fail_save)
        response = await authorized_client.delete("/api/v1/projects/test_project/reconciliation/mapping-registry/site/site_code")

        assert response.status_code == 500
        assert sidecar_path.read_bytes() == original_sidecar
        catalog = yaml.safe_load((tmp_path / "test_project" / "test_project-reconciliation.yml").read_text(encoding="utf-8"))
        assert "site_code" in catalog["entities"]["site"]

    async def test_catalog_write_failure_reports_partial_cleanup(
        self, tmp_path, monkeypatch, reset_services, sample_project, sample_recon_config, authorized_client
    ):
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        _write_mapping_sidecar(
            tmp_path,
            {
                "owned-code": _owned_link("site", "site_code"),
                "manual": {"target_id": 202, "source": "manual", "created_by": "operator"},
            },
        )

        def fail_save_catalog(*_args, **_kwargs):
            raise OSError("catalog write failed")

        monkeypatch.setattr(EntityMappingManager, "save_catalog", fail_save_catalog)
        response = await authorized_client.delete("/api/v1/projects/test_project/reconciliation/mapping-registry/site/site_code")

        assert response.status_code == 500
        assert "still present" in response.json()["detail"]["message"]
        assert "1 owned mapping link(s) were already removed" in response.json()["detail"]["message"]
        catalog = yaml.safe_load((tmp_path / "test_project" / "test_project-reconciliation.yml").read_text(encoding="utf-8"))
        assert "site_code" in catalog["entities"]["site"]
        sidecar = yaml.safe_load((tmp_path / "test_project" / "test_project-mapping.yml").read_text(encoding="utf-8"))
        assert set(sidecar["entities"]["site"]["links"]) == {"manual"}

    async def test_delete_specification_not_found(
        self, tmp_path, monkeypatch, reset_services, sample_project, sample_recon_config, authorized_client
    ):
        """Test deleting non-existent specification fails."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        response = await authorized_client.delete("/api/v1/projects/test_project/reconciliation/mapping-registry/site/nonexistent")

        assert response.status_code == 404


@pytest.mark.parametrize("raw", [False, True], ids=["json", "raw-yaml"])
async def test_whole_catalog_update_cleans_removed_spec_owned_links(
    raw, tmp_path, monkeypatch, reset_services, sample_project, sample_recon_config, authorized_client
):
    monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
    _write_mapping_sidecar(
        tmp_path,
        {
            "owned-name": _owned_link("site", "site_name"),
            "owned-code": _owned_link("site", "site_code"),
            "manual": {"target_id": 202, "source": "manual", "created_by": "operator"},
        },
    )
    config_path = sample_recon_config
    catalog = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    del catalog["entities"]["site"]["site_name"]

    if raw:
        response = await authorized_client.put(
            "/api/v1/projects/test_project/reconciliation/raw",
            content=yaml.safe_dump(catalog, sort_keys=False),
            headers={"Content-Type": "text/plain"},
        )
    else:
        response = await authorized_client.put("/api/v1/projects/test_project/reconciliation", json=catalog)

    assert response.status_code == 200, response.text
    body = response.json()
    assert "site_name" not in body["entities"]["site"]
    sidecar = yaml.safe_load((tmp_path / "test_project" / "test_project-mapping.yml").read_text(encoding="utf-8"))
    links = sidecar["entities"]["site"]["links"]
    assert "owned-name" not in links
    assert {"owned-code", "manual"} <= links.keys()


def test_catalog_save_uses_atomic_replace_and_preserves_old_file_on_failure(tmp_path, monkeypatch, sample_project, sample_recon_config):
    manager = EntityMappingManager(project_service=MagicMock(), config_dir=tmp_path)
    catalog = manager.load_catalog("test_project")
    original = sample_recon_config.read_bytes()

    def fail_replace(_source, _destination):
        raise OSError("replace failed")

    monkeypatch.setattr("backend.app.services.reconciliation.mapping_manager.os.replace", fail_replace)
    with pytest.raises(OSError, match="replace failed"):
        manager.save_catalog("test_project", catalog)

    assert sample_recon_config.read_bytes() == original
    assert not list(sample_recon_config.parent.glob(".test_project-reconciliation.yml.*.tmp"))


class TestGetAvailableFields:
    """Tests for GET /api/v1/reconcile/available-fields/{entity_name} endpoint."""

    @patch("backend.app.services.shapeshift_service.get_shapeshift_service")
    async def test_get_available_fields_success(
        self, mock_get_shapeshift_service, tmp_path, monkeypatch, reset_services, sample_project, sample_recon_config, authorized_client
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
        mock_get_shapeshift_service.return_value = mock_service_instance

        response = await authorized_client.get("/api/v1/projects/test_project/reconciliation/available-fields/site")

        assert response.status_code == 200
        fields = response.json()
        assert fields == ["site_code", "site_name", "latitude", "longitude"]


class TestGetMappingCount:
    """Tests for GET /api/v1/reconcile/specifications/{entity_name}/{target_field}/mapping-count endpoint."""

    async def test_get_mapping_count_success(
        self, tmp_path, monkeypatch, reset_services, sample_project, sample_recon_config, authorized_client
    ):
        """Test getting mapping count."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        response = await authorized_client.get("/api/v1/projects/test_project/reconciliation/mapping-registry/site/site_name/mapping-count")

        assert response.status_code == 200
        result = response.json()
        assert result["count"] == 2

    async def test_get_mapping_count_zero(
        self, tmp_path, monkeypatch, reset_services, sample_project, sample_recon_config, authorized_client
    ):
        """Test getting mapping count when no mappings exist."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        response = await authorized_client.get("/api/v1/projects/test_project/reconciliation/mapping-registry/site/site_code/mapping-count")

        assert response.status_code == 200
        result = response.json()
        assert result["count"] == 0

    async def test_get_mapping_count_not_found(
        self, tmp_path, monkeypatch, reset_services, sample_project, sample_recon_config, authorized_client
    ):
        """Test getting mapping count for non-existent specification."""
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

        response = await authorized_client.get(
            "/api/v1/projects/test_project/reconciliation/mapping-registry/site/nonexistent/mapping-count"
        )

        assert response.status_code == 404
