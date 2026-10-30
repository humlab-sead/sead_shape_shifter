"""Tests for keyed reconciliation review actions."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
import yaml

from backend.app.core.config import settings
from backend.app.core.operation_manager import operation_manager
from backend.app.models.reconciliation import AutoReconcileResult, ReconciliationCandidate
from backend.app.services import project_service, validation_service, yaml_service
from backend.app.services.reconciliation.service import ReconciliationService


def _reset_services() -> None:
    project_service._project_service = None
    validation_service._validation_service = None
    yaml_service._yaml_service = None


async def _create_project(client, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
    response = await client.post(
        "/api/v1/projects",
        json={
            "name": "review",
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


def _write_catalog(tmp_path) -> None:
    catalog = {
        "version": "3.0",
        "service_url": "http://localhost:8000",
        "entities": {
            "site": {
                "site_name": {
                    "remote": {"service_type": "site"},
                    "mapping": [
                        {
                            "local_key_value": key,
                            "source_value": "Same",
                            "status": "proposed",
                            "notes": "Keep these notes" if key == "A" else None,
                            "candidates": (
                                [
                                    {
                                        "id": "https://w3id.org/sead/id/site/101",
                                        "name": "Same",
                                        "score": 82,
                                        "type": [],
                                    },
                                    {
                                        "id": "https://w3id.org/sead/id/site/102",
                                        "name": "Score unavailable",
                                        "score": None,
                                        "type": [],
                                    },
                                    {
                                        "id": "https://w3id.org/sead/id/site/103",
                                        "name": "Zero score",
                                        "score": 0,
                                        "type": [],
                                    },
                                    {
                                        "id": "https://w3id.org/sead/id/site/104",
                                        "name": "Full score",
                                        "score": 100,
                                        "type": [],
                                    },
                                ]
                                if key == "A"
                                else []
                            ),
                        }
                        for key in ("A", "B")
                    ],
                }
            }
        },
    }
    (tmp_path / "review" / "review-reconciliation.yml").write_text(yaml.safe_dump(catalog), encoding="utf-8")


class TestReconciliationDecisionRoutes:
    def setup_method(self) -> None:
        _reset_services()

    def teardown_method(self) -> None:
        _reset_services()

    async def test_duplicate_labels_have_independent_review_actions(self, authorized_client, tmp_path, monkeypatch) -> None:
        await _create_project(authorized_client, tmp_path, monkeypatch)
        _write_catalog(tmp_path)
        path = "/api/v1/projects/review/reconciliation/site/site_name"

        accepted = await authorized_client.post(f"{path}/mapping", json={"local_key_value": "A", "status": "accepted", "target_id": 101})
        assert accepted.status_code == 200, accepted.text
        rejected = await authorized_client.post(f"{path}/mapping", json={"local_key_value": "B", "status": "rejected"})
        assert rejected.status_code == 200, rejected.text
        decisions = rejected.json()["entities"]["site"]["site_name"]["mapping"]
        assert {item["local_key_value"]: (item["status"], item["target_id"]) for item in decisions} == {
            "A": ("accepted", 101),
            "B": ("rejected", None),
        }

        preview = await authorized_client.get(f"{path}/preview")
        assert preview.status_code == 200, preview.text
        preview_rows = {row["local_key_value"]: row for row in preview.json()}
        assert {key: row["status"] for key, row in preview_rows.items()} == {"A": "accepted", "B": "rejected"}
        assert preview_rows["A"]["confidence"] == 0.82
        assert preview_rows["A"]["notes"] == "Keep these notes"
        assert preview_rows["A"]["candidates"][0]["score"] == 82
        assert preview_rows["B"]["confidence"] is None

    async def test_accepting_candidate_without_score_does_not_invent_confidence(self, authorized_client, tmp_path, monkeypatch) -> None:
        await _create_project(authorized_client, tmp_path, monkeypatch)
        _write_catalog(tmp_path)
        path = "/api/v1/projects/review/reconciliation/site/site_name"

        accepted = await authorized_client.post(
            f"{path}/mapping",
            json={"local_key_value": "A", "status": "accepted", "target_id": 102},
        )

        assert accepted.status_code == 200, accepted.text
        decisions = accepted.json()["entities"]["site"]["site_name"]["mapping"]
        decision = next(item for item in decisions if item["local_key_value"] == "A")
        assert decision["confidence"] is None
        assert decision["notes"] == "Keep these notes"
        assert len(decision["candidates"]) == 4

    @pytest.mark.parametrize(("target_id", "expected_confidence"), [(103, 0.0), (104, 1.0)])
    async def test_accepting_candidate_preserves_zero_and_full_scores_as_confidence(
        self, target_id, expected_confidence, authorized_client, tmp_path, monkeypatch
    ) -> None:
        await _create_project(authorized_client, tmp_path, monkeypatch)
        _write_catalog(tmp_path)
        path = "/api/v1/projects/review/reconciliation/site/site_name"

        accepted = await authorized_client.post(
            f"{path}/mapping",
            json={"local_key_value": "A", "status": "accepted", "target_id": target_id},
        )

        assert accepted.status_code == 200, accepted.text
        decisions = accepted.json()["entities"]["site"]["site_name"]["mapping"]
        decision = next(item for item in decisions if item["local_key_value"] == "A")
        assert decision["confidence"] == expected_confidence

    async def test_label_only_and_invalid_edits_are_rejected(self, authorized_client, tmp_path, monkeypatch) -> None:
        await _create_project(authorized_client, tmp_path, monkeypatch)
        _write_catalog(tmp_path)
        path = "/api/v1/projects/review/reconciliation/site/site_name"
        for payload in (
            {"source_value": "Same", "target_id": 101},
            {"local_key_value": "A", "status": "accepted"},
            {"local_key_value": "A", "status": "rejected", "target_id": 101},
        ):
            response = await authorized_client.post(f"{path}/mapping", json=payload)
            assert response.status_code == 422, response.text
        unknown = await authorized_client.post(f"{path}/mapping", json={"local_key_value": "X", "status": "local-only"})
        assert unknown.status_code == 400, unknown.text
        old_delete = await authorized_client.delete(f"{path}/mapping", params={"source_value": "Same"})
        assert old_delete.status_code == 422, old_delete.text

    async def test_old_catalog_is_ignored_and_recreated(self, authorized_client, tmp_path, monkeypatch) -> None:
        await _create_project(authorized_client, tmp_path, monkeypatch)
        path = tmp_path / "review" / "review-reconciliation.yml"
        path.write_text("version: '2.0'\nservice_url: http://localhost\nentities: {site: {site_name: {mapping: []}}}\n", encoding="utf-8")
        original = path.read_bytes()
        response = await authorized_client.get("/api/v1/projects/review/reconciliation")
        assert response.status_code == 200, response.text
        assert response.json()["version"] == "3.0"
        assert response.json()["entities"] == {}
        assert path.read_bytes() == original

        created = await authorized_client.post(
            "/api/v1/projects/review/reconciliation/mapping-registry",
            json={"entity_name": "site", "target_field": "site_name", "spec": {"remote": {"service_type": "site"}}},
        )
        assert created.status_code == 201, created.text
        assert yaml.safe_load(path.read_text(encoding="utf-8"))["version"] == "3.0"

    async def test_invalid_catalogs_return_clear_errors_without_rewriting(self, authorized_client, tmp_path, monkeypatch) -> None:
        await _create_project(authorized_client, tmp_path, monkeypatch)
        path = tmp_path / "review" / "review-reconciliation.yml"
        for contents, message in (
            ("version: '4.0'\nentities: {}\n", "Unsupported reconciliation catalog version"),
            ("version: [\n", "Malformed reconciliation catalog"),
            ("version: '3.0'\nentities: []\n", "Invalid reconciliation catalog"),
        ):
            path.write_text(contents, encoding="utf-8")
            response = await authorized_client.get("/api/v1/projects/review/reconciliation")
            assert response.status_code == 400, response.text
            assert message in response.json()["detail"]["message"]
            assert path.read_text(encoding="utf-8") == contents

    async def test_export_is_disabled_without_modifying_sidecar(self, authorized_client, tmp_path, monkeypatch) -> None:
        await _create_project(authorized_client, tmp_path, monkeypatch)
        _write_catalog(tmp_path)
        sidecar = tmp_path / "review" / "review-mapping.yml"
        sidecar.write_text("manual-link-data: intact\n", encoding="utf-8")
        original = sidecar.read_bytes()
        response = await authorized_client.post("/api/v1/projects/review/reconciliation/site/site_name/export-to-mapping")
        assert response.status_code == 400, response.text
        assert sidecar.read_bytes() == original

    async def test_sync_and_async_routes_use_keyed_candidate_matching(self, authorized_client, tmp_path, monkeypatch) -> None:
        await _create_project(authorized_client, tmp_path, monkeypatch)
        _write_catalog(tmp_path)
        result = AutoReconcileResult(
            proposed=1,
            unmatched=0,
            total=2,
            candidates={"A": [ReconciliationCandidate(id="site/101", name="Same", score=100.0)]},
            errors=[],
        )

        async def run(**kwargs):
            if kwargs["operation_id"]:
                operation_manager.complete_operation(kwargs["operation_id"], "Complete")
            return result

        path = "/api/v1/projects/review/reconciliation/site/site_name"
        with patch.object(ReconciliationService, "auto_reconcile_entity", new=AsyncMock(side_effect=run)) as reconcile:
            sync_response = await authorized_client.post(f"{path}/auto-reconcile-sync")
            async_response = await authorized_client.post(f"{path}/auto-reconcile")
            await asyncio.sleep(0)

        assert sync_response.status_code == 200, sync_response.text
        assert sync_response.json()["proposed"] == 1
        assert sync_response.json()["candidates"]["A"][0]["score"] == 100.0
        assert async_response.status_code == 200, async_response.text
        assert async_response.json()["operation_id"]
        assert reconcile.await_count == 2
        assert all(call.kwargs["entity_mapping"].links[0].local_key_value == "A" for call in reconcile.await_args_list)
        operation_manager.cleanup_operation(async_response.json()["operation_id"])
