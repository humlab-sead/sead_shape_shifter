"""Tests for atomic batch decision saves.

These cover the Phase 2 save contract: first-time accepted and local-only drafts,
one save per batch, source-row change detection, local reference validation, and
repairable legacy catalog entries.
"""

from unittest.mock import patch

import pytest
import yaml

from backend.app.core.config import settings
from backend.app.services import project_service, validation_service, yaml_service
from backend.app.services.reconciliation.mapping_manager import EntityMappingManager


def _reset_services() -> None:
    project_service._project_service = None
    validation_service._validation_service = None
    yaml_service._yaml_service = None


async def _create_project(client, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
    response = await client.post(
        "/api/v1/projects",
        json={
            "name": "batch",
            "data_provider_code": "test-provider",
            "provider_schema": "schema-one",
            "entities": {
                "site": {
                    "type": "fixed",
                    "public_id": "site_id",
                    "keys": ["site_code"],
                    "columns": ["system_id", "site_id", "site_code", "site_name"],
                    "values": [[1, None, "A", "Same"], [2, None, "B", "Same"]],
                }
            },
        },
    )
    assert response.status_code == 201, response.text


def _catalog_path(tmp_path):
    return tmp_path / "batch" / "shapeshifter.reconciliation.yml"


def _write_catalog(tmp_path, mapping: list[dict] | None = None) -> None:
    catalog = {
        "version": "3.0",
        "service_url": "http://localhost:8000",
        "entities": {
            "site": {
                "site_name": {
                    "remote": {"service_type": "site"},
                    "mapping": mapping or [],
                }
            }
        },
    }
    _catalog_path(tmp_path).write_text(yaml.safe_dump(catalog, sort_keys=False), encoding="utf-8")


def _write_sidecar(tmp_path, links: dict[str, dict]) -> None:
    sidecar = {
        "version": "2.0",
        "metadata": {
            "project": "batch",
            "created_at": "2026-06-15T00:00:00Z",
            "updated_at": "2026-06-15T00:00:00Z",
        },
        "entities": {
            "site": {
                "local_key": "site_code",
                "public_id": "site_id",
                "entity_type": "primary",
                "links": links,
                "local_only_approvals": {},
            }
        },
    }
    (tmp_path / "batch" / "shapeshifter.mapping.yml").write_text(yaml.safe_dump(sidecar, sort_keys=False), encoding="utf-8")


def _accepted_draft(key: str = "A", target_id: int = 101, candidate_id: str | None = None, **extra) -> dict:
    return {
        "local_key_value": key,
        "displayed_values": {"site_name": "Same"},
        "status": "accepted",
        "target_id": target_id,
        "candidate_id": candidate_id or f"https://w3id.org/sead/id/site/{target_id}",
        **extra,
    }


def _local_only_draft(key: str = "B", **extra) -> dict:
    return {
        "local_key_value": key,
        "displayed_values": {"site_name": "Same"},
        "status": "local-only",
        "notes": "No SEAD match",
        **extra,
    }


def _read_decisions(tmp_path) -> dict[str, dict]:
    catalog = yaml.safe_load(_catalog_path(tmp_path).read_text(encoding="utf-8"))
    return {item["local_key_value"]: item for item in catalog["entities"]["site"]["site_name"]["mapping"]}


class TestDecisionBatchRoutes:
    """Route tests for POST /reconciliation/{entity}/{field}/decisions."""

    def setup_method(self) -> None:
        _reset_services()

    def teardown_method(self) -> None:
        _reset_services()

    async def test_batch_saves_first_time_accepted_and_local_only_decisions(self, authorized_client, tmp_path, monkeypatch) -> None:
        await _create_project(authorized_client, tmp_path, monkeypatch)
        _write_catalog(tmp_path)
        path = "/api/v1/projects/batch/reconciliation/site/site_name/decisions"

        response = await authorized_client.post(path, json={"drafts": [_accepted_draft("A"), _local_only_draft("B")]})

        assert response.status_code == 200, response.text
        body = response.json()
        assert [item["local_key_value"] for item in body["saved"]] == ["A", "B"]
        assert [item["status"] for item in body["saved"]] == ["accepted", "local-only"]
        assert body["saved"][0]["candidate_id"] == "https://w3id.org/sead/id/site/101"
        assert body["saved"][0]["last_modified"]
        assert body["counts"] == {
            "saved": 2,
            "accepted": 1,
            "local_only": 1,
            "specification": {"accepted": 1, "local_only": 1, "proposed": 0, "rejected": 0, "total": 2},
        }
        decisions = _read_decisions(tmp_path)
        assert decisions["A"]["status"] == "accepted"
        assert decisions["A"]["source_value"] == "Same"
        assert decisions["A"]["created_by"] == "user"
        assert decisions["B"]["status"] == "local-only"
        assert "candidate_id" not in decisions["B"]

    async def test_batch_rejects_changed_rows_and_leaves_the_catalog_unchanged(self, authorized_client, tmp_path, monkeypatch) -> None:
        await _create_project(authorized_client, tmp_path, monkeypatch)
        _write_catalog(tmp_path)
        original = _catalog_path(tmp_path).read_bytes()
        path = "/api/v1/projects/batch/reconciliation/site/site_name/decisions"

        response = await authorized_client.post(
            path,
            json={"drafts": [_accepted_draft("A", displayed_values={"site_name": "Different"})]},
        )

        assert response.status_code == 400, response.text
        detail = response.json()["detail"]
        assert detail["issues"][0]["local_key_value"] == "A"
        assert detail["issues"][0]["field"] == "site_name"
        assert detail["issues"][0]["code"] == "row_changed"
        assert _catalog_path(tmp_path).read_bytes() == original

    async def test_batch_rejects_duplicate_and_missing_rows(self, authorized_client, tmp_path, monkeypatch) -> None:
        await _create_project(authorized_client, tmp_path, monkeypatch)
        _write_catalog(tmp_path)
        original = _catalog_path(tmp_path).read_bytes()
        path = "/api/v1/projects/batch/reconciliation/site/site_name/decisions"

        response = await authorized_client.post(
            path,
            json={"drafts": [_accepted_draft("A"), _accepted_draft("A"), _local_only_draft("Z")]},
        )

        assert response.status_code == 400, response.text
        codes = {(issue["local_key_value"], issue["code"]) for issue in response.json()["detail"]["issues"]}
        assert ("A", "duplicate_draft") in codes
        assert ("Z", "row_not_found") in codes
        assert _catalog_path(tmp_path).read_bytes() == original

    async def test_batch_reports_every_invalid_reference(self, authorized_client, tmp_path, monkeypatch) -> None:
        await _create_project(authorized_client, tmp_path, monkeypatch)
        _write_catalog(tmp_path)
        original = _catalog_path(tmp_path).read_bytes()
        path = "/api/v1/projects/batch/reconciliation/site/site_name/decisions"

        response = await authorized_client.post(
            path,
            json={
                "drafts": [
                    _accepted_draft("A", target_id=0, candidate_id="https://w3id.org/sead/id/site/0"),
                    _accepted_draft("B", target_id=101, candidate_id="https://w3id.org/sead/id/location/101"),
                ]
            },
        )

        assert response.status_code == 400, response.text
        issues = response.json()["detail"]["issues"]
        assert {issue["local_key_value"] for issue in issues} == {"A", "B"}
        assert {issue["code"] for issue in issues} == {"invalid_reference"}
        assert _catalog_path(tmp_path).read_bytes() == original

    async def test_batch_returns_404_for_unknown_specification(self, authorized_client, tmp_path, monkeypatch) -> None:
        await _create_project(authorized_client, tmp_path, monkeypatch)

        response = await authorized_client.post(
            "/api/v1/projects/batch/reconciliation/site/site_name/decisions",
            json={"drafts": [_accepted_draft("A")]},
        )

        assert response.status_code == 404

    async def test_batch_rejects_empty_and_blank_drafts(self, authorized_client, tmp_path, monkeypatch) -> None:
        await _create_project(authorized_client, tmp_path, monkeypatch)
        _write_catalog(tmp_path)
        original = _catalog_path(tmp_path).read_bytes()
        path = "/api/v1/projects/batch/reconciliation/site/site_name/decisions"

        empty = await authorized_client.post(path, json={"drafts": []})
        assert empty.status_code == 400, empty.text
        assert empty.json()["detail"]["issues"][0]["code"] == "invalid_draft"

        blank = await authorized_client.post(path, json={"drafts": [_local_only_draft("")]})
        assert blank.status_code == 400, blank.text
        assert blank.json()["detail"]["issues"][0]["code"] == "invalid_draft"
        assert _catalog_path(tmp_path).read_bytes() == original

    async def test_batch_preserves_existing_decision_metadata(self, authorized_client, tmp_path, monkeypatch) -> None:
        await _create_project(authorized_client, tmp_path, monkeypatch)
        _write_catalog(
            tmp_path,
            [
                {
                    "local_key_value": "A",
                    "source_value": "Same",
                    "status": "proposed",
                    "created_at": "2024-01-01T00:00:00+00:00",
                    "created_by": "system",
                    "candidates": [
                        {
                            "id": "https://w3id.org/sead/id/site/101",
                            "name": "Same",
                            "score": 90,
                            "type": [],
                        }
                    ],
                }
            ],
        )
        path = "/api/v1/projects/batch/reconciliation/site/site_name/decisions"

        response = await authorized_client.post(path, json={"drafts": [_accepted_draft("A")]})

        assert response.status_code == 200, response.text
        decision = _read_decisions(tmp_path)["A"]
        assert decision["created_at"] == "2024-01-01T00:00:00+00:00"
        assert decision["created_by"] == "system"
        assert decision["candidates"][0]["id"] == "https://w3id.org/sead/id/site/101"
        assert decision["confidence"] == pytest.approx(0.9)
        assert decision["last_modified"]

    async def test_batch_rejects_local_only_over_a_protected_manual_link(self, authorized_client, tmp_path, monkeypatch) -> None:
        await _create_project(authorized_client, tmp_path, monkeypatch)
        _write_catalog(tmp_path)
        _write_sidecar(
            tmp_path,
            {"A": {"target_id": 999, "source": "manual", "created_at": "2026-06-15T00:00:00Z", "created_by": "operator"}},
        )
        original = _catalog_path(tmp_path).read_bytes()
        path = "/api/v1/projects/batch/reconciliation/site/site_name/decisions"

        response = await authorized_client.post(path, json={"drafts": [_local_only_draft("A")]})

        assert response.status_code == 400, response.text
        assert response.json()["detail"]["issues"][0]["code"] == "protected_link"
        assert _catalog_path(tmp_path).read_bytes() == original

    async def test_batch_saves_once_and_leaves_the_catalog_on_write_failure(self, authorized_client, tmp_path, monkeypatch) -> None:
        await _create_project(authorized_client, tmp_path, monkeypatch)
        _write_catalog(tmp_path)
        path = "/api/v1/projects/batch/reconciliation/site/site_name/decisions"
        saves: list[str] = []
        original_save = EntityMappingManager.save_catalog

        def counting_save(self, project_name, catalog, filename=None):
            saves.append(project_name)
            return original_save(self, project_name, catalog, filename)

        with patch.object(EntityMappingManager, "save_catalog", counting_save):
            response = await authorized_client.post(path, json={"drafts": [_accepted_draft("A"), _local_only_draft("B")]})

        assert response.status_code == 200, response.text
        assert saves == ["batch"]

        after_first_batch = _catalog_path(tmp_path).read_bytes()

        def failing_save(self, project_name, catalog, filename=None):
            raise OSError("catalog write failed")

        with patch.object(EntityMappingManager, "save_catalog", failing_save):
            failed = await authorized_client.post(path, json={"drafts": [_accepted_draft("A")]})

        assert failed.status_code == 500, failed.text
        assert _catalog_path(tmp_path).read_bytes() == after_first_batch

    async def test_batch_runs_its_catalog_write_under_the_project_lock(self, authorized_client, tmp_path, monkeypatch) -> None:
        await _create_project(authorized_client, tmp_path, monkeypatch)
        _write_catalog(tmp_path)
        path = "/api/v1/projects/batch/reconciliation/site/site_name/decisions"
        lock = project_service.ProjectService._get_lock("batch")
        observed: list[bool] = []
        original_save = EntityMappingManager.save_catalog

        def locked_save(self, project_name, catalog, filename=None):
            observed.append(lock.locked())
            return original_save(self, project_name, catalog, filename)

        with patch.object(EntityMappingManager, "save_catalog", locked_save):
            response = await authorized_client.post(path, json={"drafts": [_accepted_draft("A")]})

        assert response.status_code == 200, response.text
        assert observed == [True]
