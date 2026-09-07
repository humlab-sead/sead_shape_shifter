"""Tests for exporting reconciliation links into the mapping sidecar."""

from pathlib import Path

import yaml

from backend.app.core.config import settings
from backend.app.services import project_service, validation_service, yaml_service
from src.normalizer import ShapeShifter

# Fixed entities used by the tests. Projects are created through the API so the
# backend registers them as authorization resources (see authorized_client).
_SITE_ENTITY = {
    "type": "fixed",
    "public_id": "site_id",
    "keys": ["site_code"],
    "columns": ["system_id", "site_id", "site_code"],
    "values": [[1, 10, "A"], [2, 20, "B"]],
}

_SAMPLE_ENTITY_BLANK_IDS = {
    "type": "fixed",
    "public_id": "sample_id",
    "keys": ["sample_code"],
    "columns": ["system_id", "sample_id", "sample_code"],
    "values": [[1, None, "A"], [2, None, "B"]],
}


async def _create_project(client, entity_name: str, entity: dict) -> None:
    """Create the test project through the API (registers it as an authorized resource)."""
    response = await client.post("/api/v1/projects", json={"name": "test_project", "entities": {entity_name: entity}})
    assert response.status_code == 201, response.text


def _project_path(tmp_path: Path) -> Path:
    """Return the on-disk project file path written by the API create endpoint."""
    return tmp_path / "test_project" / "shapeshifter.yml"


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

    async def test_export_to_mapping_writes_reconciliation_links(self, tmp_path: Path, monkeypatch, authorized_client) -> None:
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        await _create_project(authorized_client, "site", _SITE_ENTITY)
        _write_reconciliation_catalog(tmp_path)

        response = await authorized_client.post("/api/v1/projects/test_project/reconciliation/site/site_code/export-to-mapping")

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

    async def test_export_to_mapping_skips_existing_manual_links(self, tmp_path: Path, monkeypatch, authorized_client) -> None:
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        await _create_project(authorized_client, "site", _SITE_ENTITY)
        _write_reconciliation_catalog(tmp_path)
        _write_mapping_sidecar(tmp_path)

        response = await authorized_client.post("/api/v1/projects/test_project/reconciliation/site/site_code/export-to-mapping")

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

    async def test_export_to_mapping_returns_404_when_reconciliation_catalog_is_missing(
        self, tmp_path: Path, monkeypatch, authorized_client
    ) -> None:
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        await _create_project(authorized_client, "site", _SITE_ENTITY)

        response = await authorized_client.post("/api/v1/projects/test_project/reconciliation/site/site_code/export-to-mapping")

        assert response.status_code == 404
        assert response.json()["detail"] == "No reconciliation registry for entity 'site' target 'site_code'"

    async def test_exported_links_are_applied_during_normalization(self, tmp_path: Path, monkeypatch, authorized_client) -> None:
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        await _create_project(authorized_client, "sample", _SAMPLE_ENTITY_BLANK_IDS)
        _write_sample_reconciliation_catalog(tmp_path)

        response = await authorized_client.post("/api/v1/projects/test_project/reconciliation/sample/sample_code/export-to-mapping")

        assert response.status_code == 200

        normalizer = ShapeShifter(project=str(_project_path(tmp_path)))

        await normalizer.normalize()

        sample_table = normalizer.table_store["sample"]
        assert sample_table["sample_id"].tolist() == [101, 202]
