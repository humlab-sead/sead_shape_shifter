"""Tests for exporting reconciliation links into the mapping sidecar."""

from pathlib import Path
from unittest.mock import patch

import yaml

from backend.app.core.config import settings
from backend.app.services import project_service, validation_service, yaml_service
from src.normalizer import ShapeShifter
from src.reconciliation.mapping_manager import MappingManager, MappingVersionConflictError
from src.reconciliation.mapping_model import encode_local_key

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
    await _create_project_with_entities(client, {entity_name: entity})


async def _create_project_with_entities(client, entities: dict[str, dict]) -> None:
    """Create a test project containing the supplied entities."""
    response = await client.post(
        "/api/v1/projects",
        json={
            "name": "test_project",
            "data_provider_code": "test-provider",
            "provider_schema": "schema-one",
            "entities": entities,
        },
    )
    assert response.status_code == 201, response.text


def _project_path(tmp_path: Path) -> Path:
    """Return the on-disk project file path written by the API create endpoint."""
    return tmp_path / "test_project" / "shapeshifter.yml"


def _write_reconciliation_catalog(tmp_path: Path) -> None:
    catalog = {
        "version": "3.0",
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
                            "local_key_value": "A",
                            "source_value": "A",
                            "status": "accepted",
                            "target_id": 101,
                            "confidence": 0.98,
                            "notes": "Matched by reconciliation",
                        },
                        {
                            "local_key_value": "B",
                            "source_value": "B",
                            "status": "accepted",
                            "target_id": 202,
                            "confidence": 0.88,
                        },
                        {
                            "local_key_value": "C",
                            "source_value": "C",
                            "status": "local-only",
                            "target_id": None,
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
        "version": "3.0",
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
                            "local_key_value": "A",
                            "source_value": "A",
                            "status": "accepted",
                            "target_id": 101,
                            "confidence": 0.98,
                            "notes": "Matched by reconciliation",
                        },
                        {
                            "local_key_value": "B",
                            "source_value": "B",
                            "status": "accepted",
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


def _read_reconciliation_catalog(tmp_path: Path) -> dict:
    path = tmp_path / "test_project" / "test_project-reconciliation.yml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _write_reconciliation_catalog_data(tmp_path: Path, catalog: dict) -> None:
    path = tmp_path / "test_project" / "test_project-reconciliation.yml"
    path.write_text(yaml.safe_dump(catalog, sort_keys=False), encoding="utf-8")


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

    async def test_export_counts_created_and_protected_links_and_skips_noop_writes(
        self, tmp_path: Path, monkeypatch, authorized_client
    ) -> None:
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        await _create_project(authorized_client, "site", _SITE_ENTITY)
        _write_reconciliation_catalog(tmp_path)
        _write_mapping_sidecar(tmp_path)
        sidecar_path = tmp_path / "test_project" / "test_project-mapping.yml"

        response = await authorized_client.post("/api/v1/projects/test_project/reconciliation/site/site_code/export-to-mapping")

        assert response.status_code == 200, response.text
        assert response.json() == {
            "exported": 1,
            "removed": 0,
            "skipped_manual": 1,
            "entity": "site",
            "field": "site_code",
        }
        sidecar = yaml.safe_load(sidecar_path.read_text(encoding="utf-8"))
        assert sidecar["entities"]["site"]["links"]["A"]["source"] == "manual"
        assert sidecar["entities"]["site"]["links"]["B"]["target_id"] == 202
        assert sidecar["entities"]["site"]["links"]["B"]["owner"] == {"entity_name": "site", "target_field": "site_code"}
        assert sidecar["entities"]["site"]["links"]["B"]["verified_at"] is None
        original = sidecar_path.read_bytes()

        response = await authorized_client.post("/api/v1/projects/test_project/reconciliation/site/site_code/export-to-mapping")

        assert response.status_code == 200, response.text
        assert response.json()["exported"] == 0
        assert response.json()["removed"] == 0
        assert response.json()["skipped_manual"] == 1
        assert sidecar_path.read_bytes() == original

    async def test_export_updates_an_owned_link_when_its_accepted_target_changes(
        self, tmp_path: Path, monkeypatch, authorized_client
    ) -> None:
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        await _create_project(authorized_client, "site", _SITE_ENTITY)
        _write_reconciliation_catalog(tmp_path)
        first_response = await authorized_client.post("/api/v1/projects/test_project/reconciliation/site/site_code/export-to-mapping")
        assert first_response.status_code == 200, first_response.text
        assert first_response.json()["exported"] == 2

        catalog = _read_reconciliation_catalog(tmp_path)
        decision = next(item for item in catalog["entities"]["site"]["site_code"]["mapping"] if item["local_key_value"] == "B")
        decision["target_id"] = 303
        _write_reconciliation_catalog_data(tmp_path, catalog)

        response = await authorized_client.post("/api/v1/projects/test_project/reconciliation/site/site_code/export-to-mapping")

        assert response.status_code == 200, response.text
        assert response.json()["exported"] == 1
        assert response.json()["removed"] == 0
        sidecar = yaml.safe_load((tmp_path / "test_project" / "test_project-mapping.yml").read_text(encoding="utf-8"))
        assert sidecar["entities"]["site"]["links"]["B"]["target_id"] == 303

    async def test_export_ignores_proposed_and_local_only_decisions(self, tmp_path: Path, monkeypatch, authorized_client) -> None:
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        await _create_project(authorized_client, "site", _SITE_ENTITY)
        _write_reconciliation_catalog(tmp_path)
        catalog = _read_reconciliation_catalog(tmp_path)
        catalog["entities"]["site"]["site_code"]["mapping"].append(
            {
                "local_key_value": "D",
                "source_value": "D",
                "status": "proposed",
                "target_id": None,
            }
        )
        _write_reconciliation_catalog_data(tmp_path, catalog)

        response = await authorized_client.post("/api/v1/projects/test_project/reconciliation/site/site_code/export-to-mapping")

        assert response.status_code == 200, response.text
        assert response.json()["exported"] == 2
        sidecar = yaml.safe_load((tmp_path / "test_project" / "test_project-mapping.yml").read_text(encoding="utf-8"))
        assert set(sidecar["entities"]["site"]["links"]) == {"A", "B"}

    async def test_export_removes_owned_links_when_decision_is_rejected(self, tmp_path: Path, monkeypatch, authorized_client) -> None:
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        await _create_project(authorized_client, "site", _SITE_ENTITY)
        _write_reconciliation_catalog(tmp_path)
        first_response = await authorized_client.post("/api/v1/projects/test_project/reconciliation/site/site_code/export-to-mapping")
        assert first_response.status_code == 200, first_response.text

        catalog = _read_reconciliation_catalog(tmp_path)
        decision = next(item for item in catalog["entities"]["site"]["site_code"]["mapping"] if item["local_key_value"] == "B")
        decision["status"] = "rejected"
        decision["target_id"] = None
        _write_reconciliation_catalog_data(tmp_path, catalog)

        response = await authorized_client.post("/api/v1/projects/test_project/reconciliation/site/site_code/export-to-mapping")

        assert response.status_code == 200, response.text
        assert response.json()["exported"] == 0
        assert response.json()["removed"] == 1
        sidecar = yaml.safe_load((tmp_path / "test_project" / "test_project-mapping.yml").read_text(encoding="utf-8"))
        assert "B" not in sidecar["entities"]["site"]["links"]

    async def test_export_uses_encoded_compound_keys_and_accepts_target_id_zero(
        self, tmp_path: Path, monkeypatch, authorized_client
    ) -> None:
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        entity = {
            "type": "fixed",
            "public_id": "site_id",
            "keys": ["region", "site_code"],
            "columns": ["system_id", "site_id", "region", "site_code"],
            "values": [[1, 10, "SE|AD", "A/B"]],
        }
        await _create_project(authorized_client, "site", entity)
        _write_reconciliation_catalog(tmp_path)
        encoded_key = encode_local_key(["region", "site_code"], ["SE|AD", "A/B"])
        catalog = _read_reconciliation_catalog(tmp_path)
        catalog["entities"]["site"]["site_code"]["mapping"] = [
            {
                "local_key_value": encoded_key,
                "source_value": "A/B",
                "status": "accepted",
                "target_id": 0,
            }
        ]
        _write_reconciliation_catalog_data(tmp_path, catalog)

        response = await authorized_client.post("/api/v1/projects/test_project/reconciliation/site/site_code/export-to-mapping")

        assert response.status_code == 200, response.text
        assert response.json() == {
            "exported": 1,
            "removed": 0,
            "skipped_manual": 0,
            "entity": "site",
            "field": "site_code",
        }
        sidecar = yaml.safe_load((tmp_path / "test_project" / "test_project-mapping.yml").read_text(encoding="utf-8"))
        site_mapping = sidecar["entities"]["site"]
        assert site_mapping["local_key"] == ["region", "site_code"]
        assert site_mapping["links"][encoded_key]["target_id"] == 0
        assert site_mapping["links"][encoded_key]["owner"] == {"entity_name": "site", "target_field": "site_code"}

    async def test_export_to_mapping_returns_404_when_reconciliation_catalog_is_missing(
        self, tmp_path: Path, monkeypatch, authorized_client
    ) -> None:
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        await _create_project(authorized_client, "site", _SITE_ENTITY)

        response = await authorized_client.post("/api/v1/projects/test_project/reconciliation/site/site_code/export-to-mapping")

        assert response.status_code == 404
        detail = response.json()["detail"]
        assert detail["error_type"] == "ResourceNotFoundError"
        assert detail["message"] == "No reconciliation registry for entity 'site' target 'site_code'"

    async def test_export_conflicts_with_another_owner_without_mutating_sidecar(
        self, tmp_path: Path, monkeypatch, authorized_client
    ) -> None:
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        await _create_project(authorized_client, "site", _SITE_ENTITY)
        _write_reconciliation_catalog(tmp_path)
        _write_mapping_sidecar(tmp_path)
        sidecar_path = tmp_path / "test_project" / "test_project-mapping.yml"
        sidecar = yaml.safe_load(sidecar_path.read_text(encoding="utf-8"))
        sidecar["entities"]["site"]["links"]["B"] = {
            "target_id": 303,
            "source": "reconciliation",
            "created_at": "2026-06-15T00:00:00Z",
            "committed_at": "2026-06-15T00:00:00Z",
            "owner": {"entity_name": "sample", "target_field": "sample_code"},
            "verified_at": None,
            "created_by": "reconciliation",
        }
        sidecar_path.write_text(yaml.safe_dump(sidecar, sort_keys=False), encoding="utf-8")
        original = sidecar_path.read_bytes()

        response = await authorized_client.post("/api/v1/projects/test_project/reconciliation/site/site_code/export-to-mapping")

        assert response.status_code == 409
        assert "owned by" in response.json()["detail"]["message"]
        assert sidecar_path.read_bytes() == original

    async def test_export_conflicts_with_another_accepted_claim_before_any_write(
        self, tmp_path: Path, monkeypatch, authorized_client
    ) -> None:
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        await _create_project(authorized_client, "site", _SITE_ENTITY)
        _write_reconciliation_catalog(tmp_path)
        catalog = _read_reconciliation_catalog(tmp_path)
        other_spec = dict(catalog["entities"]["site"]["site_code"])
        other_spec["mapping"] = [
            {"local_key_value": "B", "source_value": "B", "status": "accepted", "target_id": 303},
        ]
        catalog["entities"]["site"]["other_field"] = other_spec
        _write_reconciliation_catalog_data(tmp_path, catalog)

        response = await authorized_client.post("/api/v1/projects/test_project/reconciliation/site/site_code/export-to-mapping")

        assert response.status_code == 409
        assert "accepted claim" in response.json()["detail"]["message"]
        assert not (tmp_path / "test_project" / "test_project-mapping.yml").exists()

    async def test_export_rejects_mismatched_sidecar_metadata_without_mutating_it(
        self, tmp_path: Path, monkeypatch, authorized_client
    ) -> None:
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        await _create_project(authorized_client, "site", _SITE_ENTITY)
        _write_reconciliation_catalog(tmp_path)
        _write_mapping_sidecar(tmp_path)
        sidecar_path = tmp_path / "test_project" / "test_project-mapping.yml"
        sidecar = yaml.safe_load(sidecar_path.read_text(encoding="utf-8"))
        sidecar["entities"]["site"]["public_id"] = "wrong_id"
        sidecar_path.write_text(yaml.safe_dump(sidecar, sort_keys=False), encoding="utf-8")
        original = sidecar_path.read_bytes()

        response = await authorized_client.post("/api/v1/projects/test_project/reconciliation/site/site_code/export-to-mapping")

        assert response.status_code == 409
        assert "does not match" in response.json()["detail"]["message"]
        assert sidecar_path.read_bytes() == original

    async def test_export_reports_stale_sidecar_version_without_mutating_it(self, tmp_path: Path, monkeypatch, authorized_client) -> None:
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        await _create_project(authorized_client, "site", _SITE_ENTITY)
        _write_reconciliation_catalog(tmp_path)
        _write_mapping_sidecar(tmp_path)
        sidecar_path = tmp_path / "test_project" / "test_project-mapping.yml"
        original = sidecar_path.read_bytes()

        def fail_save(*_args, **_kwargs):
            raise MappingVersionConflictError("external write")

        monkeypatch.setattr(MappingManager, "save", fail_save)
        response = await authorized_client.post("/api/v1/projects/test_project/reconciliation/site/site_code/export-to-mapping")

        assert response.status_code == 409
        assert "changed during reconciliation export" in response.json()["detail"]["message"]
        assert sidecar_path.read_bytes() == original

    async def test_exported_links_normalize_offline_with_stable_parent_ids_and_child_foreign_keys(
        self, tmp_path: Path, monkeypatch, authorized_client
    ) -> None:
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        entities = {
            "site": {
                "type": "fixed",
                "public_id": "site_id",
                "keys": ["site_code"],
                "columns": ["system_id", "site_id", "site_code"],
                "values": [[1, 10, "A"], [2, 20, "B"], [3, 30, "C"], [4, 40, "D"]],
            },
            "sample": {
                "type": "fixed",
                "public_id": "sample_id",
                "keys": ["sample_code"],
                "columns": ["system_id", "sample_id", "sample_code"],
                "values": [[1, 500, "S-B"]],
                "depends_on": ["site"],
                "extra_columns": {"site_ref": 2},
                "foreign_keys": [{"entity": "site", "local_keys": ["site_ref"], "remote_keys": ["system_id"]}],
            },
        }
        await _create_project_with_entities(authorized_client, entities)
        _write_reconciliation_catalog(tmp_path)
        catalog = _read_reconciliation_catalog(tmp_path)
        catalog["entities"]["site"]["site_code"]["mapping"].append(
            {"local_key_value": "D", "source_value": "D", "status": "accepted", "target_id": 404}
        )
        _write_reconciliation_catalog_data(tmp_path, catalog)
        _write_mapping_sidecar(tmp_path)
        sidecar_path = tmp_path / "test_project" / "test_project-mapping.yml"
        sidecar = yaml.safe_load(sidecar_path.read_text(encoding="utf-8"))
        sidecar["entities"]["site"]["links"]["A"]["target_id"] = 111
        sidecar["entities"]["site"]["links"]["C"] = {
            "target_id": 303,
            "source": "import",
            "created_at": "2026-06-15T00:00:00Z",
            "created_by": "legacy",
        }
        sidecar["entities"]["site"]["links"]["D"] = {
            "target_id": 444,
            "source": "reconciliation",
            "created_at": "2026-06-15T00:00:00Z",
            "committed_at": "2026-06-15T00:00:00Z",
            "created_by": "legacy",
        }
        sidecar_path.write_text(yaml.safe_dump(sidecar, sort_keys=False), encoding="utf-8")

        response = await authorized_client.post("/api/v1/projects/test_project/reconciliation/site/site_code/export-to-mapping")

        assert response.status_code == 200, response.text
        assert response.json()["exported"] == 1
        assert response.json()["removed"] == 0
        assert response.json()["skipped_manual"] == 2
        with patch("httpx.AsyncClient.request", side_effect=AssertionError("Normalization must not make network requests")):
            results = []
            for _ in range(2):
                normalizer = ShapeShifter(project=str(_project_path(tmp_path)))
                await normalizer.normalize()
                sites = normalizer.table_store["site"].set_index("site_code")["site_id"]
                child_site_ids = normalizer.table_store["sample"]["site_id"].tolist()
                results.append(({key: int(value) for key, value in sites.items()}, [int(value) for value in child_site_ids]))

        assert results == [
            ({"A": 111, "B": 202, "C": 30, "D": 444}, [2]),
            ({"A": 111, "B": 202, "C": 30, "D": 444}, [2]),
        ]
