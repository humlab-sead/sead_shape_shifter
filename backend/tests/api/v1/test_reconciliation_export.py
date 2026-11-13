"""Tests for exporting reconciliation links into the mapping sidecar."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pandas as pd
import pytest
import yaml

from backend.app.clients.reconciliation_client import CandidateVerificationUnavailableError, ReconciliationClient
from backend.app.core.config import settings
from backend.app.models.reconciliation import CandidateVerificationResult
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
                            "candidate_id": "https://w3id.org/sead/id/site/101",
                            "confidence": 0.98,
                            "notes": "Matched by reconciliation",
                        },
                        {
                            "local_key_value": "B",
                            "source_value": "B",
                            "status": "accepted",
                            "target_id": 202,
                            "candidate_id": "https://w3id.org/sead/id/site/202",
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
    with open(tmp_path / "test_project" / "shapeshifter.reconciliation.yml", "w", encoding="utf-8") as handle:
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
                            "candidate_id": "https://w3id.org/sead/id/sample/101",
                            "confidence": 0.98,
                            "notes": "Matched by reconciliation",
                        },
                        {
                            "local_key_value": "B",
                            "source_value": "B",
                            "status": "accepted",
                            "target_id": 202,
                            "candidate_id": "https://w3id.org/sead/id/sample/202",
                            "confidence": 0.88,
                        },
                    ],
                }
            }
        },
    }
    with open(tmp_path / "test_project" / "shapeshifter.reconciliation.yml", "w", encoding="utf-8") as handle:
        yaml.dump(catalog, handle, sort_keys=False)


def _write_mapping_sidecar(
    tmp_path: Path,
    local_only_approvals: dict[str, dict] | None = None,
    links: dict[str, dict] | None = None,
) -> None:
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
                "links": (
                    links
                    if links is not None
                    else {
                        "A": {
                            "target_id": 10,
                            "source": "manual",
                            "created_at": "2026-06-15T00:00:00Z",
                            "committed_at": "2026-06-15T00:00:00Z",
                            "created_by": "user",
                        }
                    }
                ),
                "local_only_approvals": local_only_approvals or {},
            }
        },
    }
    with open(tmp_path / "test_project" / "shapeshifter.mapping.yml", "w", encoding="utf-8") as handle:
        yaml.dump(sidecar, handle, sort_keys=False)


def _read_reconciliation_catalog(tmp_path: Path) -> dict:
    path = tmp_path / "test_project" / "shapeshifter.reconciliation.yml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _write_reconciliation_catalog_data(tmp_path: Path, catalog: dict) -> None:
    path = tmp_path / "test_project" / "shapeshifter.reconciliation.yml"
    path.write_text(yaml.safe_dump(catalog, sort_keys=False), encoding="utf-8")


def _reset_singletons() -> None:
    project_service._project_service = None
    validation_service._validation_service = None
    yaml_service._yaml_service = None


@pytest.fixture(autouse=True)
def verify_existing_candidates(monkeypatch):
    async def verify(_client, items):
        results = []
        for item in items:
            try:
                aggregate_id = int(item.id.rsplit("/", 1)[-1])
            except ValueError:
                results.append(
                    CandidateVerificationResult(
                        type=item.type,
                        id=item.id,
                        outcome="invalid_candidate",
                        aggregate_id=None,
                    )
                )
            else:
                if aggregate_id <= 0:
                    results.append(
                        CandidateVerificationResult(
                            type=item.type,
                            id=item.id,
                            outcome="invalid_candidate",
                            aggregate_id=None,
                        )
                    )
                else:
                    results.append(
                        CandidateVerificationResult(
                            type=item.type,
                            id=item.id,
                            outcome="exists",
                            aggregate_id=aggregate_id,
                        )
                    )
        return results

    monkeypatch.setattr(ReconciliationClient, "verify_candidates", verify)


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
        sidecar_path = tmp_path / "test_project" / "shapeshifter.mapping.yml"

        response = await authorized_client.post("/api/v1/projects/test_project/reconciliation/site/site_code/export-to-mapping")

        assert response.status_code == 200, response.text
        assert response.json() == {
            "exported": 1,
            "removed": 0,
            "exported_local_only_approvals": 1,
            "removed_local_only_approvals": 0,
            "skipped_manual": 1,
            "entity": "site",
            "field": "site_code",
            "outcomes": [{"local_key_value": "B", "outcome": "verified", "reason": None}],
        }
        sidecar = yaml.safe_load(sidecar_path.read_text(encoding="utf-8"))
        assert sidecar["entities"]["site"]["links"]["A"]["source"] == "manual"
        assert sidecar["entities"]["site"]["links"]["B"]["target_id"] == 202
        assert sidecar["entities"]["site"]["links"]["B"]["owner"] == {"entity_name": "site", "target_field": "site_code"}
        assert sidecar["entities"]["site"]["links"]["B"]["verified_at"] is not None
        approval = sidecar["entities"]["site"]["local_only_approvals"]["C"]
        assert approval["owner"] == {"entity_name": "site", "target_field": "site_code"}
        assert approval["committed_at"]
        original = sidecar_path.read_bytes()

        response = await authorized_client.post("/api/v1/projects/test_project/reconciliation/site/site_code/export-to-mapping")

        assert response.status_code == 200, response.text
        assert response.json()["exported"] == 0
        assert response.json()["removed"] == 0
        assert response.json()["exported_local_only_approvals"] == 0
        assert response.json()["removed_local_only_approvals"] == 0
        assert response.json()["skipped_manual"] == 1
        assert sidecar_path.read_bytes() == original

    async def test_manual_legacy_link_needs_no_candidate_verification(self, tmp_path: Path, monkeypatch, authorized_client) -> None:
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        await _create_project(authorized_client, "site", _SITE_ENTITY)
        _write_reconciliation_catalog(tmp_path)
        catalog = _read_reconciliation_catalog(tmp_path)
        decision = catalog["entities"]["site"]["site_code"]["mapping"][0]
        decision.pop("candidate_id")
        catalog["entities"]["site"]["site_code"]["mapping"] = [decision]
        _write_reconciliation_catalog_data(tmp_path, catalog)
        _write_mapping_sidecar(tmp_path)
        sidecar_path = tmp_path / "test_project" / "shapeshifter.mapping.yml"
        original = sidecar_path.read_bytes()

        with patch.object(ReconciliationClient, "verify_candidates", new=AsyncMock()) as verify:
            response = await authorized_client.post("/api/v1/projects/test_project/reconciliation/site/site_code/export-to-mapping")

        assert response.status_code == 200, response.text
        assert response.json()["skipped_manual"] == 1
        assert response.json()["outcomes"] == []
        verify.assert_not_awaited()
        assert sidecar_path.read_bytes() == original

    async def test_legacy_accepted_decision_requires_reacceptance_before_export(
        self, tmp_path: Path, monkeypatch, authorized_client
    ) -> None:
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        await _create_project(authorized_client, "site", _SITE_ENTITY)
        _write_reconciliation_catalog(tmp_path)
        catalog = _read_reconciliation_catalog(tmp_path)
        decision = catalog["entities"]["site"]["site_code"]["mapping"][0]
        decision.pop("candidate_id")
        catalog["entities"]["site"]["site_code"]["mapping"] = [decision]
        _write_reconciliation_catalog_data(tmp_path, catalog)

        with patch.object(ReconciliationClient, "verify_candidates", new=AsyncMock()) as verify:
            response = await authorized_client.post("/api/v1/projects/test_project/reconciliation/site/site_code/export-to-mapping")

        assert response.status_code == 400
        assert "re-accepted" in response.json()["detail"]["message"]
        verify.assert_not_awaited()
        assert not (tmp_path / "test_project" / "shapeshifter.mapping.yml").exists()

    async def test_verification_outage_exports_unverified_then_retry_verifies_link(
        self, tmp_path: Path, monkeypatch, authorized_client
    ) -> None:
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        await _create_project(authorized_client, "site", _SITE_ENTITY)
        _write_reconciliation_catalog(tmp_path)
        path = "/api/v1/projects/test_project/reconciliation/site/site_code/export-to-mapping"

        with patch.object(
            ReconciliationClient,
            "verify_candidates",
            new=AsyncMock(side_effect=CandidateVerificationUnavailableError("offline")),
        ):
            unavailable = await authorized_client.post(path)

        assert unavailable.status_code == 200, unavailable.text
        assert {item["outcome"] for item in unavailable.json()["outcomes"]} == {"unverified"}
        sidecar_path = tmp_path / "test_project" / "shapeshifter.mapping.yml"
        sidecar = yaml.safe_load(sidecar_path.read_text(encoding="utf-8"))
        assert all(link["verified_at"] is None for link in sidecar["entities"]["site"]["links"].values())

        retried = await authorized_client.post(path)

        assert retried.status_code == 200, retried.text
        assert {item["outcome"] for item in retried.json()["outcomes"]} == {"verified"}
        sidecar = yaml.safe_load(sidecar_path.read_text(encoding="utf-8"))
        assert all(link["verified_at"] is not None for link in sidecar["entities"]["site"]["links"].values())

    async def test_not_found_and_invalid_candidates_remove_only_their_owned_links(
        self, tmp_path: Path, monkeypatch, authorized_client
    ) -> None:
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        await _create_project(authorized_client, "site", _SITE_ENTITY)
        _write_reconciliation_catalog(tmp_path)
        path = "/api/v1/projects/test_project/reconciliation/site/site_code/export-to-mapping"
        first = await authorized_client.post(path)
        assert first.status_code == 200, first.text

        async def reject_candidates(_client, items):
            return [
                CandidateVerificationResult(
                    type=item.type,
                    id=item.id,
                    outcome="not_found" if item.id.endswith("/101") else "invalid_candidate",
                    aggregate_id=None,
                )
                for item in items
            ]

        with patch.object(ReconciliationClient, "verify_candidates", new=reject_candidates):
            response = await authorized_client.post(path)

        assert response.status_code == 200, response.text
        assert response.json()["exported"] == 0
        assert response.json()["removed"] == 2
        assert [item["outcome"] for item in response.json()["outcomes"]] == ["not_found", "invalid_candidate"]
        sidecar = yaml.safe_load((tmp_path / "test_project" / "shapeshifter.mapping.yml").read_text(encoding="utf-8"))
        assert sidecar["entities"]["site"]["links"] == {}

    async def test_mismatched_verified_target_id_does_not_write_links(self, tmp_path: Path, monkeypatch, authorized_client) -> None:
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        await _create_project(authorized_client, "site", _SITE_ENTITY)
        _write_reconciliation_catalog(tmp_path)

        async def mismatch(_client, items):
            return [
                CandidateVerificationResult(
                    type=item.type,
                    id=item.id,
                    outcome="exists",
                    aggregate_id=int(item.id.rsplit("/", 1)[-1]) + 1,
                )
                for item in items
            ]

        with patch.object(ReconciliationClient, "verify_candidates", new=mismatch):
            response = await authorized_client.post("/api/v1/projects/test_project/reconciliation/site/site_code/export-to-mapping")

        assert response.status_code == 500
        assert "different target ID" in response.json()["detail"]["message"]
        assert not (tmp_path / "test_project" / "shapeshifter.mapping.yml").exists()

    @pytest.mark.parametrize("changed_input", ["catalog", "project", "sidecar"])
    async def test_export_rejects_inputs_changed_during_verification(
        self, changed_input, tmp_path: Path, monkeypatch, authorized_client
    ) -> None:
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        await _create_project(authorized_client, "site", _SITE_ENTITY)
        _write_reconciliation_catalog(tmp_path)
        _write_mapping_sidecar(tmp_path)
        project_dir = tmp_path / "test_project"
        input_paths = {
            "catalog": project_dir / "shapeshifter.reconciliation.yml",
            "project": _project_path(tmp_path),
            "sidecar": project_dir / "shapeshifter.mapping.yml",
        }
        changed_path = input_paths[changed_input]
        original_changed_bytes = changed_path.read_bytes()
        sidecar_path = input_paths["sidecar"]
        original_sidecar_bytes = sidecar_path.read_bytes()

        async def change_input_during_verification(_client, items):
            changed_path.write_bytes(original_changed_bytes + b"\n# concurrent edit\n")
            return [
                CandidateVerificationResult(
                    type=item.type,
                    id=item.id,
                    outcome="exists",
                    aggregate_id=int(item.id.rsplit("/", 1)[-1]),
                )
                for item in items
            ]

        with patch.object(ReconciliationClient, "verify_candidates", new=change_input_during_verification):
            response = await authorized_client.post("/api/v1/projects/test_project/reconciliation/site/site_code/export-to-mapping")

        assert response.status_code == 409, response.text
        assert "changed during candidate verification" in response.json()["detail"]["message"]
        assert changed_path.read_bytes() == original_changed_bytes + b"\n# concurrent edit\n"
        expected_sidecar = original_sidecar_bytes + b"\n# concurrent edit\n" if changed_input == "sidecar" else original_sidecar_bytes
        assert sidecar_path.read_bytes() == expected_sidecar

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
        decision["candidate_id"] = "https://w3id.org/sead/id/site/303"
        _write_reconciliation_catalog_data(tmp_path, catalog)

        response = await authorized_client.post("/api/v1/projects/test_project/reconciliation/site/site_code/export-to-mapping")

        assert response.status_code == 200, response.text
        assert response.json()["exported"] == 1
        assert response.json()["removed"] == 0
        sidecar = yaml.safe_load((tmp_path / "test_project" / "shapeshifter.mapping.yml").read_text(encoding="utf-8"))
        assert sidecar["entities"]["site"]["links"]["B"]["target_id"] == 303

    async def test_export_records_local_only_approvals_without_creating_id_links(
        self, tmp_path: Path, monkeypatch, authorized_client
    ) -> None:
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
        assert response.json()["exported_local_only_approvals"] == 1
        assert response.json()["removed_local_only_approvals"] == 0
        sidecar = yaml.safe_load((tmp_path / "test_project" / "shapeshifter.mapping.yml").read_text(encoding="utf-8"))
        assert set(sidecar["entities"]["site"]["links"]) == {"A", "B"}
        approval = sidecar["entities"]["site"]["local_only_approvals"]["C"]
        assert approval["owner"] == {"entity_name": "site", "target_field": "site_code"}
        assert approval["committed_at"] is not None
        assert "target_id" not in approval

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
        decision["candidate_id"] = None
        local_only_decision = next(item for item in catalog["entities"]["site"]["site_code"]["mapping"] if item["local_key_value"] == "C")
        local_only_decision["status"] = "rejected"
        _write_reconciliation_catalog_data(tmp_path, catalog)

        response = await authorized_client.post("/api/v1/projects/test_project/reconciliation/site/site_code/export-to-mapping")

        assert response.status_code == 200, response.text
        assert response.json()["exported"] == 0
        assert response.json()["removed"] == 1
        assert response.json()["removed_local_only_approvals"] == 1
        sidecar = yaml.safe_load((tmp_path / "test_project" / "shapeshifter.mapping.yml").read_text(encoding="utf-8"))
        assert "B" not in sidecar["entities"]["site"]["links"]
        assert "C" not in sidecar["entities"]["site"]["local_only_approvals"]

    async def test_export_does_not_write_an_invalid_candidate_for_a_compound_key(
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
                "candidate_id": "https://w3id.org/sead/id/site/0",
            }
        ]
        _write_reconciliation_catalog_data(tmp_path, catalog)

        response = await authorized_client.post("/api/v1/projects/test_project/reconciliation/site/site_code/export-to-mapping")

        assert response.status_code == 200, response.text
        assert response.json() == {
            "exported": 0,
            "removed": 0,
            "exported_local_only_approvals": 0,
            "removed_local_only_approvals": 0,
            "skipped_manual": 0,
            "entity": "site",
            "field": "site_code",
            "outcomes": [
                {
                    "local_key_value": encoded_key,
                    "outcome": "invalid_candidate",
                    "reason": "The selected candidate URI is invalid for this entity type.",
                }
            ],
        }
        assert not (tmp_path / "test_project" / "shapeshifter.mapping.yml").exists()

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
        sidecar_path = tmp_path / "test_project" / "shapeshifter.mapping.yml"
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

    @pytest.mark.parametrize(
        ("claim_status", "target_id"),
        [("accepted", 303), ("local-only", None)],
    )
    async def test_export_conflicts_with_another_claim_before_any_write(
        self, tmp_path: Path, monkeypatch, authorized_client, claim_status: str, target_id: int | None
    ) -> None:
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        await _create_project(authorized_client, "site", _SITE_ENTITY)
        _write_reconciliation_catalog(tmp_path)
        catalog = _read_reconciliation_catalog(tmp_path)
        other_spec = dict(catalog["entities"]["site"]["site_code"])
        other_spec["mapping"] = [
            {
                "local_key_value": "B",
                "source_value": "B",
                "status": claim_status,
                "target_id": target_id,
            },
        ]
        catalog["entities"]["site"]["other_field"] = other_spec
        _write_reconciliation_catalog_data(tmp_path, catalog)

        response = await authorized_client.post("/api/v1/projects/test_project/reconciliation/site/site_code/export-to-mapping")

        assert response.status_code == 409
        assert "claim for key" in response.json()["detail"]["message"]
        assert not (tmp_path / "test_project" / "shapeshifter.mapping.yml").exists()

    async def test_local_only_export_conflicts_with_protected_link_or_other_owner_approval(
        self, tmp_path: Path, monkeypatch, authorized_client
    ) -> None:
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        await _create_project(authorized_client, "site", _SITE_ENTITY)
        _write_reconciliation_catalog(tmp_path)
        protected_link = {
            "target_id": 909,
            "source": "manual",
            "created_at": "2026-06-15T00:00:00Z",
            "committed_at": "2026-06-15T00:00:00Z",
            "created_by": "operator",
        }
        _write_mapping_sidecar(tmp_path, links={"C": protected_link})
        sidecar_path = tmp_path / "test_project" / "shapeshifter.mapping.yml"
        original = sidecar_path.read_bytes()

        response = await authorized_client.post("/api/v1/projects/test_project/reconciliation/site/site_code/export-to-mapping")

        assert response.status_code == 409
        assert "protected link" in response.json()["detail"]["message"]
        assert sidecar_path.read_bytes() == original

        other_owner_approval = {
            "owner": {"entity_name": "sample", "target_field": "sample_code"},
            "committed_at": "2026-06-15T00:00:00Z",
        }
        _write_mapping_sidecar(tmp_path, local_only_approvals={"C": other_owner_approval})
        original = sidecar_path.read_bytes()

        response = await authorized_client.post("/api/v1/projects/test_project/reconciliation/site/site_code/export-to-mapping")

        assert response.status_code == 409
        assert "local-only approval owned by sample.sample_code" in response.json()["detail"]["message"]
        assert sidecar_path.read_bytes() == original

    async def test_export_rejects_mismatched_sidecar_metadata_without_mutating_it(
        self, tmp_path: Path, monkeypatch, authorized_client
    ) -> None:
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        await _create_project(authorized_client, "site", _SITE_ENTITY)
        _write_reconciliation_catalog(tmp_path)
        _write_mapping_sidecar(tmp_path)
        sidecar_path = tmp_path / "test_project" / "shapeshifter.mapping.yml"
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
        sidecar_path = tmp_path / "test_project" / "shapeshifter.mapping.yml"
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
                "values": [[1, 10, "A"], [2, 20, "B"], [3, 30, "C"], [4, 40, "D"], [5, None, "E"]],
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
        decision_c = next(item for item in catalog["entities"]["site"]["site_code"]["mapping"] if item["local_key_value"] == "C")
        decision_c["status"] = "rejected"
        decision_e = dict(decision_c)
        decision_e["local_key_value"] = "E"
        decision_e["source_value"] = "E"
        decision_e["status"] = "local-only"
        catalog["entities"]["site"]["site_code"]["mapping"].append(decision_e)
        catalog["entities"]["site"]["site_code"]["mapping"].append(
            {
                "local_key_value": "D",
                "source_value": "D",
                "status": "accepted",
                "target_id": 404,
                "candidate_id": "https://w3id.org/sead/id/site/404",
            }
        )
        _write_reconciliation_catalog_data(tmp_path, catalog)
        _write_mapping_sidecar(tmp_path)
        sidecar_path = tmp_path / "test_project" / "shapeshifter.mapping.yml"
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
        assert response.json()["exported_local_only_approvals"] == 1
        assert response.json()["removed_local_only_approvals"] == 0
        exported_sidecar = yaml.safe_load(sidecar_path.read_text(encoding="utf-8"))
        assert "E" not in exported_sidecar["entities"]["site"]["links"]
        assert exported_sidecar["entities"]["site"]["local_only_approvals"]["E"]["committed_at"]
        with patch("httpx.AsyncClient.request", side_effect=AssertionError("Normalization must not make network requests")):
            results = []
            for _ in range(2):
                normalizer = ShapeShifter(project=str(_project_path(tmp_path)))
                await normalizer.normalize()
                sites = normalizer.table_store["site"].set_index("site_code")["site_id"]
                child_site_ids = normalizer.table_store["sample"]["site_id"].tolist()
                results.append(
                    (
                        {key: None if bool(pd.isna(value)) else int(value) for key, value in sites.items()},
                        [int(value) for value in child_site_ids],
                    )
                )

        assert results == [
            ({"A": 111, "B": 202, "C": 30, "D": 444, "E": None}, [2]),
            ({"A": 111, "B": 202, "C": 30, "D": 444, "E": None}, [2]),
        ]
