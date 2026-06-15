"""Tests for exporting reconciliation links into the mapping sidecar."""

from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from backend.app.core.config import settings
from backend.app.main import app
from backend.app.services import project_service, validation_service, yaml_service
from src.normalizer import ShapeShifter

client = TestClient(app)


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


def _write_project_with_blank_public_ids(tmp_path: Path) -> Path:
    project_dir = tmp_path / "test_project"
    project_dir.mkdir(exist_ok=True)
    project_path = project_dir / "shapeshifter.yml"
    project_data = {
        "metadata": {
            "type": "shapeshifter-project",
            "name": "test_project",
            "description": "A test project",
            "version": "1.0.0",
        },
        "entities": {
            "sample": {
                "type": "fixed",
                "public_id": "sample_id",
                "keys": ["sample_code"],
                "columns": ["system_id", "sample_id", "sample_code"],
                "values": [[1, None, "A"], [2, None, "B"]],
            }
        },
    }
    with open(project_path, "w", encoding="utf-8") as handle:
        yaml.dump(project_data, handle)
    return project_path


def _write_reconciliation_catalog(tmp_path: Path) -> None:
    catalog = {
        "version": "2.0",
        "service_url": "http://localhost:8000",
        "entities": {
            "site": {
                "site_code": {
                    "source": None,
                    "property_mappings": {},
                    "remote": {"service_type": "site", "columns": []},
                    "auto_accept_threshold": 0.95,
                    "review_threshold": 0.7,
                    "mapping": [
                        {
                            "source_value": "A",
                            "target_id": 101,
                            "confidence": 0.98,
                            "notes": "Matched by reconciliation",
                        },
                        {
                            "source_value": "B",
                            "target_id": 202,
                            "confidence": 0.88,
                        },
                        {
                            "source_value": "C",
                            "target_id": None,
                            "will_not_match": True,
                            "notes": "No SEAD match",
                        },
                    ],
                }
            }
        },
    }
    with open(tmp_path / "test_project" / "test_project-reconciliation.yml", "w", encoding="utf-8") as handle:
        yaml.dump(catalog, handle, sort_keys=False)


def _write_sample_reconciliation_catalog(tmp_path: Path) -> None:
    catalog = {
        "version": "2.0",
        "service_url": "http://localhost:8000",
        "entities": {
            "sample": {
                "sample_code": {
                    "source": None,
                    "property_mappings": {},
                    "remote": {"service_type": "sample", "columns": []},
                    "auto_accept_threshold": 0.95,
                    "review_threshold": 0.7,
                    "mapping": [
                        {
                            "source_value": "A",
                            "target_id": 101,
                            "confidence": 0.98,
                            "notes": "Matched by reconciliation",
                        },
                        {
                            "source_value": "B",
                            "target_id": 202,
                            "confidence": 0.88,
                        },
                    ],
                }
            }
        },
    }
    with open(tmp_path / "test_project" / "test_project-reconciliation.yml", "w", encoding="utf-8") as handle:
        yaml.dump(catalog, handle, sort_keys=False)


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


class TestReconciliationExportApi:
    """Route tests for exporting reconciliation links to the mapping sidecar."""

    def setup_method(self) -> None:
        _reset_singletons()

    def teardown_method(self) -> None:
        _reset_singletons()

    def test_export_to_mapping_writes_reconciliation_links(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        _write_project(tmp_path)
        _write_reconciliation_catalog(tmp_path)

        response = client.post("/api/v1/projects/test_project/reconciliation/site/site_code/export-to-mapping")

        assert response.status_code == 200
        assert response.json() == {
            "exported": 2,
            "skipped_manual": 0,
            "entity": "site",
            "field": "site_code",
        }

        with open(tmp_path / "test_project" / "test_project-mapping.yml", "r", encoding="utf-8") as handle:
            sidecar = yaml.safe_load(handle)

        links = sidecar["entities"]["site"]["links"]
        assert links["A"]["target_id"] == 101
        assert links["A"]["source"] == "reconciliation"
        assert links["A"]["confidence"] == 0.98
        assert links["A"]["created_by"] == "reconciliation-service"
        assert links["A"]["committed_at"] is not None
        assert links["B"]["target_id"] == 202
        assert "C" not in links

    def test_export_to_mapping_skips_existing_manual_links(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        _write_project(tmp_path)
        _write_reconciliation_catalog(tmp_path)
        _write_mapping_sidecar(tmp_path)

        response = client.post("/api/v1/projects/test_project/reconciliation/site/site_code/export-to-mapping")

        assert response.status_code == 200
        assert response.json() == {
            "exported": 1,
            "skipped_manual": 1,
            "entity": "site",
            "field": "site_code",
        }

        with open(tmp_path / "test_project" / "test_project-mapping.yml", "r", encoding="utf-8") as handle:
            sidecar = yaml.safe_load(handle)

        links = sidecar["entities"]["site"]["links"]
        assert links["A"]["target_id"] == 10
        assert links["A"]["source"] == "manual"
        assert links["B"]["target_id"] == 202
        assert links["B"]["source"] == "reconciliation"

    def test_export_to_mapping_returns_404_when_reconciliation_catalog_is_missing(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        _write_project(tmp_path)

        response = client.post("/api/v1/projects/test_project/reconciliation/site/site_code/export-to-mapping")

        assert response.status_code == 404
        assert response.json()["detail"] == "No reconciliation registry for entity 'site' target 'site_code'"

    def test_exported_links_are_applied_during_normalization(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        project_path = _write_project_with_blank_public_ids(tmp_path)
        _write_sample_reconciliation_catalog(tmp_path)

        response = client.post("/api/v1/projects/test_project/reconciliation/sample/sample_code/export-to-mapping")

        assert response.status_code == 200

        normalizer = ShapeShifter(project=str(project_path))

        import asyncio

        asyncio.run(normalizer.normalize())

        sample_table = normalizer.table_store["sample"]
        assert sample_table["sample_id"].tolist() == [101, 202]
