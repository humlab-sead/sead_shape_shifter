"""Deterministic workflow test for a property-bearing ``location`` reconciliation.

The Authority Service contract, candidate batch, and candidate verification are
replaced by fixed mocks. The project is created through the API so the test
exercises the protected routes, and normalization runs offline against the
temporary project files.

The fixture columns are test-only. ``fixture_location_code`` identifies local
rows, ``location_name`` is the shared search label, and ``fixture_place_name``
supplies the manifest-declared ``place_name`` property. They show that property
values come from their own source column and that review decisions stay keyed
by the business key; they are not a provider schema recommendation, and the
mocked candidate proves client behavior only, not Authority Service match
quality.
"""

from pathlib import Path
from typing import Any

import httpx
import pandas as pd
import yaml

from backend.app.clients.reconciliation_client import ReconciliationClient
from backend.app.core.config import settings
from backend.app.models.reconciliation import CandidateVerificationResult, ReconciliationCandidate
from backend.app.services import project_service, validation_service, yaml_service
from src.normalizer import ShapeShifter

PROJECT_NAME = "phase4_location_workflow"
ENTITY_NAME = "location"
CHILD_ENTITY_NAME = "sample"
TARGET_FIELD = "location_name"
LOCAL_KEY = "fixture_location_code"
PROPERTY_ID = "place_name"
PROPERTY_SOURCE = "fixture_place_name"
PUBLIC_ID = "location_id"
TARGET_ID = 4233
CANDIDATE_URI = f"https://w3id.org/sead/id/location/{TARGET_ID}"
PATH = f"/api/v1/projects/{PROJECT_NAME}/reconciliation/{ENTITY_NAME}/{TARGET_FIELD}"

# Two fixed rows share the search label "Trench" but keep distinct business keys
# and distinct property source values.
_ENTITIES: dict[str, dict[str, Any]] = {
    ENTITY_NAME: {
        "type": "fixed",
        "public_id": PUBLIC_ID,
        "keys": [LOCAL_KEY],
        "columns": ["system_id", PUBLIC_ID, LOCAL_KEY, TARGET_FIELD, PROPERTY_SOURCE],
        "values": [
            [20001, None, "LOC-001", "Trench", "Trench One"],
            [20002, None, "LOC-002", "Trench", "Trench Two"],
        ],
    },
    CHILD_ENTITY_NAME: {
        "type": "fixed",
        "public_id": "sample_id",
        "keys": ["sample_code"],
        "columns": ["system_id", "sample_id", "sample_code"],
        "values": [[1, 500, "S-1"]],
        "depends_on": [ENTITY_NAME],
        "extra_columns": {"location_ref": 20001},
        "foreign_keys": [{"entity": ENTITY_NAME, "local_keys": ["location_ref"], "remote_keys": ["system_id"]}],
    },
}

# The manifest declares exactly one property for the mocked location type.
_MANIFEST: dict[str, Any] = {
    "defaultTypes": [{"id": ENTITY_NAME, "name": "Location"}],
    "reconciliation": {"supportedTypes": [ENTITY_NAME]},
    "extend": {"property_settings": [{"name": PROPERTY_ID, "entity_types": [ENTITY_NAME]}]},
}


def _reset_singletons() -> None:
    project_service._project_service = None
    validation_service._validation_service = None
    yaml_service._yaml_service = None


def _project_file(tmp_path: Path) -> Path:
    return tmp_path / PROJECT_NAME / "shapeshifter.yml"


def _catalog_path(tmp_path: Path) -> Path:
    return tmp_path / PROJECT_NAME / f"{PROJECT_NAME}-reconciliation.yml"


def _sidecar_path(tmp_path: Path) -> Path:
    return tmp_path / PROJECT_NAME / f"{PROJECT_NAME}-mapping.yml"


def _read_catalog_decisions(tmp_path: Path) -> dict[str, tuple[str, int | None, str | None]]:
    """Return ``local key -> (status, target ID, search label)`` from the saved catalog."""
    catalog = yaml.safe_load(_catalog_path(tmp_path).read_text(encoding="utf-8"))
    decisions = catalog["entities"][ENTITY_NAME][TARGET_FIELD]["mapping"]
    return {item["local_key_value"]: (item["status"], item.get("target_id"), item.get("source_value")) for item in decisions}


def _install_mocked_service(monkeypatch) -> dict[str, list[Any]]:
    """Replace manifest, batch matching, and verification with deterministic results."""
    captured: dict[str, list[Any]] = {"queries": [], "verifications": []}

    async def get_service_manifest(_client: ReconciliationClient) -> dict[str, Any]:
        return _MANIFEST

    async def reconcile_batch(_client: ReconciliationClient, queries: dict[str, Any]) -> dict[str, list[ReconciliationCandidate]]:
        captured["queries"].append({query_id: query.to_dict() for query_id, query in queries.items()})
        return {query_id: [ReconciliationCandidate(id=CANDIDATE_URI, name="Trench", score=100.0)] for query_id in queries}

    async def verify_candidates(_client: ReconciliationClient, items: list[Any]) -> list[CandidateVerificationResult]:
        captured["verifications"].append(list(items))
        return [CandidateVerificationResult(type=item.type, id=item.id, outcome="exists", aggregate_id=TARGET_ID) for item in items]

    monkeypatch.setattr(ReconciliationClient, "get_service_manifest", get_service_manifest)
    monkeypatch.setattr(ReconciliationClient, "reconcile_batch", reconcile_batch)
    monkeypatch.setattr(ReconciliationClient, "verify_candidates", verify_candidates)
    return captured


async def _create_project(client) -> None:
    response = await client.post(
        "/api/v1/projects",
        json={
            "name": PROJECT_NAME,
            "data_provider_code": "test-provider",
            "provider_schema": "schema-one",
            "entities": _ENTITIES,
        },
    )
    assert response.status_code == 201, response.text


async def _register_property_specification(client) -> None:
    response = await client.post(
        f"/api/v1/projects/{PROJECT_NAME}/reconciliation/mapping-registry",
        json={
            "entity_name": ENTITY_NAME,
            "target_field": TARGET_FIELD,
            "spec": {
                "remote": {"service_type": ENTITY_NAME},
                "property_mappings": {PROPERTY_ID: PROPERTY_SOURCE},
            },
        },
    )
    assert response.status_code == 201, response.text


def _query_property_values(queries: dict[str, dict[str, Any]]) -> set[str]:
    """Return the single property value sent with each candidate query."""
    values: set[str] = set()
    for query in queries.values():
        properties = query.get("properties")
        assert isinstance(properties, list) and len(properties) == 1, properties
        property_entry = properties[0]
        assert property_entry["pid"] == PROPERTY_ID, property_entry
        values.add(property_entry["v"])
    return values


async def _normalize_twice(project_file: Path, monkeypatch) -> list[tuple[dict[str, tuple[int, int | None]], list[int]]]:
    """Normalize twice offline and collect parent identities plus child foreign keys."""

    def deny_network(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("Normalization must not make network requests")

    monkeypatch.setattr(httpx.AsyncClient, "request", deny_network)
    results: list[tuple[dict[str, tuple[int, int | None]], list[int]]] = []
    for _ in range(2):
        normalizer = ShapeShifter(project=str(project_file))
        await normalizer.normalize()
        parents = normalizer.table_store[ENTITY_NAME].set_index(LOCAL_KEY)
        identities = {
            str(key): (
                int(row["system_id"]),
                None if pd.isna(row[PUBLIC_ID]) else int(row[PUBLIC_ID]),
            )
            for key, row in parents.iterrows()
        }
        child_links = sorted(int(value) for value in normalizer.table_store[CHILD_ENTITY_NAME][PUBLIC_ID].tolist())
        results.append((identities, child_links))
    return results


class TestLocationReconciliationWorkflow:
    """Review, export, and offline normalization for a property-bearing remote type."""

    def setup_method(self) -> None:
        _reset_singletons()

    def teardown_method(self) -> None:
        _reset_singletons()

    async def test_location_review_export_and_unchanged_rerun(self, authorized_client, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        captured = _install_mocked_service(monkeypatch)
        await _create_project(authorized_client)
        await _register_property_specification(authorized_client)

        matched = await authorized_client.post(f"{PATH}/auto-reconcile-sync")

        assert matched.status_code == 200, matched.text
        assert matched.json()["total"] == 2
        assert matched.json()["proposed"] == 2
        assert set(matched.json()["candidates"]) == {"LOC-001", "LOC-002"}
        assert all(item["id"] == CANDIDATE_URI for items in matched.json()["candidates"].values() for item in items)
        queries = captured["queries"][0]
        assert len(queries) == 2
        assert all(query["type"] == ENTITY_NAME and query["query"] == "Trench" for query in queries.values())
        # Each row sends its own property source value, not the shared label.
        assert _query_property_values(queries) == {"Trench One", "Trench Two"}
        # A high-scoring candidate is proposed, not accepted, and no link exists yet.
        assert not _sidecar_path(tmp_path).exists()
        assert _read_catalog_decisions(tmp_path) == {
            "LOC-001": ("proposed", None, "Trench"),
            "LOC-002": ("proposed", None, "Trench"),
        }

        accepted = await authorized_client.post(
            f"{PATH}/mapping",
            json={"local_key_value": "LOC-001", "status": "accepted", "target_id": TARGET_ID, "candidate_id": CANDIDATE_URI},
        )
        assert accepted.status_code == 200, accepted.text
        rejected = await authorized_client.post(f"{PATH}/mapping", json={"local_key_value": "LOC-002", "status": "rejected"})
        assert rejected.status_code == 200, rejected.text
        assert _read_catalog_decisions(tmp_path) == {
            "LOC-001": ("accepted", TARGET_ID, "Trench"),
            "LOC-002": ("rejected", None, "Trench"),
        }

        preview = await authorized_client.get(f"{PATH}/preview")
        assert preview.status_code == 200, preview.text
        assert {row["local_key_value"]: (row["status"], row["target_id"]) for row in preview.json()} == {
            "LOC-001": ("accepted", TARGET_ID),
            "LOC-002": ("rejected", None),
        }

        exported = await authorized_client.post(f"{PATH}/export-to-mapping")

        assert exported.status_code == 200, exported.text
        assert exported.json()["exported"] == 1
        assert exported.json()["removed"] == 0
        assert exported.json()["outcomes"] == [{"local_key_value": "LOC-001", "outcome": "verified", "reason": None}]
        assert [(item.type, item.id) for item in captured["verifications"][-1]] == [(ENTITY_NAME, CANDIDATE_URI)]

        sidecar = yaml.safe_load(_sidecar_path(tmp_path).read_text(encoding="utf-8"))
        entity = sidecar["entities"][ENTITY_NAME]
        assert entity["local_key"] == LOCAL_KEY
        assert entity["public_id"] == PUBLIC_ID
        assert entity["entity_type"] == "primary"
        assert set(entity["links"]) == {"LOC-001"}
        assert "Trench" not in entity["links"]
        link = entity["links"]["LOC-001"]
        assert link["target_id"] == TARGET_ID
        assert link["owner"] == {"entity_name": ENTITY_NAME, "target_field": TARGET_FIELD}
        assert link["committed_at"]
        assert link["verified_at"]
        assert entity["local_only_approvals"] == {}
        sidecar_bytes = _sidecar_path(tmp_path).read_bytes()

        rerun = await authorized_client.post(f"{PATH}/auto-reconcile-sync")

        assert rerun.status_code == 200, rerun.text
        assert rerun.json()["total"] == 2
        assert rerun.json()["proposed"] == 0
        assert _read_catalog_decisions(tmp_path) == {
            "LOC-001": ("accepted", TARGET_ID, "Trench"),
            "LOC-002": ("rejected", None, "Trench"),
        }

        unchanged = await authorized_client.post(f"{PATH}/export-to-mapping")

        assert unchanged.status_code == 200, unchanged.text
        assert unchanged.json()["exported"] == 0
        assert unchanged.json()["removed"] == 0
        assert _sidecar_path(tmp_path).read_bytes() == sidecar_bytes

        results = await _normalize_twice(_project_file(tmp_path), monkeypatch)

        assert results == [
            ({"LOC-001": (20001, TARGET_ID), "LOC-002": (20002, None)}, [20001]),
            ({"LOC-001": (20001, TARGET_ID), "LOC-002": (20002, None)}, [20001]),
        ]
