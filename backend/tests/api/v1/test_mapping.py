"""Tests for mapping sidecar CRUD API endpoints."""

from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from backend.app.core.config import settings
from backend.app.main import app
from backend.app.services import project_service, validation_service, yaml_service


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client


def _write_project(tmp_path: Path) -> None:
    project_dir = tmp_path / "test_project"
    project_dir.mkdir(exist_ok=True)
    project_data = {
        "metadata": {
            "type": "shapeshifter-project",
            "name": "test_project",
            "description": "A test project",
            "version": "1.0.0",
        },
        "entities": {
            "site": {
                "type": "fixed",
                "public_id": "site_id",
                "keys": ["site_code"],
                "columns": ["system_id", "site_id", "site_code"],
                "values": [[1, 10, "A"], [2, 20, "B"]],
            }
        },
    }
    with open(project_dir / "shapeshifter.yml", "w", encoding="utf-8") as handle:
        yaml.dump(project_data, handle)


def _write_mapping_sidecar(tmp_path: Path) -> None:
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
                "links": {
                    "A": {
                        "target_id": 10,
                        "source": "manual",
                        "created_at": "2026-06-15T00:00:00Z",
                        "committed_at": "2026-06-15T00:00:00Z",
                        "created_by": "user",
                    }
                },
            }
        },
    }
    with open(tmp_path / "test_project" / "test_project-mapping.yml", "w", encoding="utf-8") as handle:
        yaml.dump(sidecar, handle, sort_keys=False)


def _reset_singletons() -> None:
    project_service._project_service = None
    validation_service._validation_service = None
    yaml_service._yaml_service = None


class TestMappingApi:
    """CRUD tests for mapping sidecar endpoints."""

    def setup_method(self) -> None:
        _reset_singletons()

    def teardown_method(self) -> None:
        _reset_singletons()

    def test_get_entity_mapping_returns_default_metadata_when_sidecar_missing(self, tmp_path: Path, monkeypatch, client) -> None:
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        _write_project(tmp_path)

        response = client.get("/api/v1/projects/test_project/mapping/site")

        assert response.status_code == 200
        body = response.json()
        assert body["entity_name"] == "site"
        assert body["local_key"] == "site_code"
        assert body["public_id"] == "site_id"
        assert body["links"] == {}

    def test_get_entity_mapping_returns_404_for_missing_entity(self, tmp_path: Path, monkeypatch, client) -> None:
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        _write_project(tmp_path)

        response = client.get("/api/v1/projects/test_project/mapping/missing")

        assert response.status_code == 404
        body = response.json()["detail"]
        assert body["message"] == "Entity 'missing' not found"
        assert body["context"]["resource_type"] == "entity"
        assert body["context"]["resource_id"] == "missing"

    def test_get_single_mapping_link_returns_saved_link(self, tmp_path: Path, monkeypatch, client) -> None:
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        _write_project(tmp_path)
        _write_mapping_sidecar(tmp_path)

        response = client.get("/api/v1/projects/test_project/mapping/site/A")

        assert response.status_code == 200
        body = response.json()
        assert body["entity_name"] == "site"
        assert body["local_key_value"] == "A"
        assert body["link"]["target_id"] == 10
        assert body["link"]["source"] == "manual"

    def test_get_single_mapping_link_returns_404_for_missing_entity(self, tmp_path: Path, monkeypatch, client) -> None:
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        _write_project(tmp_path)
        _write_mapping_sidecar(tmp_path)

        response = client.get("/api/v1/projects/test_project/mapping/missing/A")

        assert response.status_code == 404
        body = response.json()["detail"]
        assert body["message"] == "Entity 'missing' not found"
        assert body["context"]["resource_type"] == "entity"
        assert body["context"]["resource_id"] == "missing"

    def test_put_mapping_link_creates_or_updates_manual_link(self, tmp_path: Path, monkeypatch, client) -> None:
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        _write_project(tmp_path)

        response = client.put(
            "/api/v1/projects/test_project/mapping/site/B",
            json={"target_id": 20, "confidence": 0.99, "notes": "Manual override"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["local_key_value"] == "B"
        assert body["link"]["target_id"] == 20
        assert body["link"]["source"] == "manual"
        assert body["link"]["confidence"] == 0.99
        assert body["link"]["notes"] == "Manual override"

        with open(tmp_path / "test_project" / "test_project-mapping.yml", "r", encoding="utf-8") as handle:
            sidecar = yaml.safe_load(handle)
        assert sidecar["entities"]["site"]["links"]["B"]["target_id"] == 20

    def test_put_mapping_link_returns_404_for_missing_entity(self, tmp_path: Path, monkeypatch, client) -> None:
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        _write_project(tmp_path)

        response = client.put(
            "/api/v1/projects/test_project/mapping/missing/B",
            json={"target_id": 20, "confidence": 0.99, "notes": "Manual override"},
        )

        assert response.status_code == 404
        body = response.json()["detail"]
        assert body["message"] == "Entity 'missing' not found"
        assert body["context"]["resource_type"] == "entity"
        assert body["context"]["resource_id"] == "missing"

    def test_delete_mapping_link_removes_saved_link(self, tmp_path: Path, monkeypatch, client) -> None:
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        _write_project(tmp_path)
        _write_mapping_sidecar(tmp_path)

        response = client.delete("/api/v1/projects/test_project/mapping/site/A")

        assert response.status_code == 200
        assert response.json() == {"entity_name": "site", "local_key_value": "A", "deleted": True}

        with open(tmp_path / "test_project" / "test_project-mapping.yml", "r", encoding="utf-8") as handle:
            sidecar = yaml.safe_load(handle)
        assert sidecar["entities"]["site"]["links"] == {}

    def test_delete_mapping_link_returns_404_for_missing_entity(self, tmp_path: Path, monkeypatch, client) -> None:
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        _write_project(tmp_path)

        response = client.delete("/api/v1/projects/test_project/mapping/missing/A")

        assert response.status_code == 404
        body = response.json()["detail"]
        assert body["message"] == "Entity 'missing' not found"
        assert body["context"]["resource_type"] == "entity"
        assert body["context"]["resource_id"] == "missing"
