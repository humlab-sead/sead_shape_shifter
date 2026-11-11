"""Grouped parity test for manifest-driven reconciliation across three remote types.

The same workflow runs for the ``site`` MVP type and both pilots, ``feature_type``
and ``location``. The Authority Service contract, candidate batch, and candidate
verification are replaced by fixed mocks; the project is created through the API
and normalization runs offline against the temporary project files.

The fixture keys and property columns are test-only. They show that review
decisions stay keyed by the local business key, that property values come from
their own source column, and that parent target IDs land on ``public_id`` while
child Core links keep the parent's local ``system_id``. The mocked candidates
prove client behavior only, not Authority Service match quality.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import pandas as pd
import pytest
import yaml

from backend.app.clients.reconciliation_client import ReconciliationClient
from backend.app.core.config import settings
from backend.app.models.reconciliation import CandidateVerificationResult, ReconciliationCandidate
from backend.app.services import project_service, validation_service, yaml_service
from src.normalizer import ShapeShifter

CHILD_ENTITY_NAME = "sample"
SEARCH_LABEL = "Trench"
PARENT_SYSTEM_IDS = (30001, 30002)
PROPERTY_ID = "place_name"


@dataclass(frozen=True)
class CaseConfig:
    """One remote type and the fixture columns that exercise it."""

    entity_name: str
    project_name: str
    local_key: str
    local_keys: tuple[str, str]
    target_field: str
    public_id: str
    target_id: int
    property_source: str | None = None
    property_values: tuple[str, str] = ("", "")

    @property
    def candidate_uri(self) -> str:
        return f"https://w3id.org/sead/id/{self.entity_name}/{self.target_id}"

    @property
    def path(self) -> str:
        return f"/api/v1/projects/{self.project_name}/reconciliation/{self.entity_name}/{self.target_field}"

    @property
    def sidecar_path(self) -> str:
        return f"{self.project_name}-mapping.yml"

    @property
    def catalog_path(self) -> str:
        return f"{self.project_name}-reconciliation.yml"


CASES: list[CaseConfig] = [
    CaseConfig(
        entity_name="site",
        project_name="phase5_grouped_site",
        local_key="fixture_site_code",
        local_keys=("SITE-001", "SITE-002"),
        target_field="site_name",
        public_id="site_id",
        target_id=101,
        property_source="fixture_place_name",
        property_values=("Trench One", "Trench Two"),
    ),
    CaseConfig(
        entity_name="feature_type",
        project_name="phase5_grouped_feature_type",
        local_key="fixture_feature_code",
        local_keys=("FT-001", "FT-002"),
        target_field="feature_type_name",
        public_id="feature_type_id",
        target_id=25,
    ),
    CaseConfig(
        entity_name="location",
        project_name="phase5_grouped_location",
        local_key="fixture_location_code",
        local_keys=("LOC-001", "LOC-002"),
        target_field="location_name",
        public_id="location_id",
        target_id=4233,
        property_source="fixture_place_name",
        property_values=("Trench One", "Trench Two"),
    ),
]


def _entities(case: CaseConfig) -> dict[str, dict[str, Any]]:
    """Build the fixed parent and child entities for one case."""
    columns = ["system_id", case.public_id, case.local_key, case.target_field]
    rows: list[list[Any]] = [
        [PARENT_SYSTEM_IDS[0], None, case.local_keys[0], SEARCH_LABEL],
        [PARENT_SYSTEM_IDS[1], None, case.local_keys[1], SEARCH_LABEL],
    ]
    if case.property_source:
        columns.append(case.property_source)
        for row, value in zip(rows, case.property_values, strict=True):
            row.append(value)
    reference_column = f"{case.entity_name}_ref"
    return {
        case.entity_name: {
            "type": "fixed",
            "public_id": case.public_id,
            "keys": [case.local_key],
            "columns": columns,
            "values": rows,
        },
        CHILD_ENTITY_NAME: {
            "type": "fixed",
            "public_id": "sample_id",
            "keys": ["sample_code"],
            "columns": ["system_id", "sample_id", "sample_code"],
            "values": [[1, 500, "S-1"]],
            "depends_on": [case.entity_name],
            "extra_columns": {reference_column: PARENT_SYSTEM_IDS[0]},
            "foreign_keys": [{"entity": case.entity_name, "local_keys": [reference_column], "remote_keys": ["system_id"]}],
        },
    }


def _manifest(case: CaseConfig) -> dict[str, Any]:
    """Build a manifest where only the case type is supported for reconciliation."""
    property_settings = [{"name": PROPERTY_ID, "entity_types": [case.entity_name]}] if case.property_source is not None else []
    return {
        # ``taxon`` is listed for OpenRefine only and is not a supported reconciliation type.
        "defaultTypes": [{"id": "taxon", "name": "Taxon"}, {"id": case.entity_name, "name": case.entity_name.title()}],
        "reconciliation": {"supportedTypes": [case.entity_name]},
        "extend": {"property_settings": property_settings},
    }


def _reset_singletons() -> None:
    project_service._project_service = None
    validation_service._validation_service = None
    yaml_service._yaml_service = None


def _project_file(tmp_path: Path, case: CaseConfig) -> Path:
    return tmp_path / case.project_name / "shapeshifter.yml"


def _catalog_path(tmp_path: Path, case: CaseConfig) -> Path:
    return tmp_path / case.project_name / case.catalog_path


def _sidecar_path(tmp_path: Path, case: CaseConfig) -> Path:
    return tmp_path / case.project_name / case.sidecar_path


def _read_catalog_decisions(tmp_path: Path, case: CaseConfig) -> dict[str, tuple[str, int | None, str | None]]:
    """Return ``local key -> (status, target ID, search label)`` from the saved catalog."""
    catalog = yaml.safe_load(_catalog_path(tmp_path, case).read_text(encoding="utf-8"))
    decisions = catalog["entities"][case.entity_name][case.target_field]["mapping"]
    return {item["local_key_value"]: (item["status"], item.get("target_id"), item.get("source_value")) for item in decisions}


def _install_mocked_service(monkeypatch, case: CaseConfig) -> dict[str, list[Any]]:
    """Replace manifest, batch matching, and verification with deterministic results."""
    captured: dict[str, list[Any]] = {"manifests": [], "queries": [], "verifications": []}

    async def get_service_manifest(_client: ReconciliationClient) -> dict[str, Any]:
        captured["manifests"].append(True)
        return _manifest(case)

    async def reconcile_batch(_client: ReconciliationClient, queries: dict[str, Any]) -> dict[str, list[ReconciliationCandidate]]:
        captured["queries"].append({query_id: query.to_dict() for query_id, query in queries.items()})
        return {query_id: [ReconciliationCandidate(id=case.candidate_uri, name=SEARCH_LABEL, score=100.0)] for query_id in queries}

    async def verify_candidates(_client: ReconciliationClient, items: list[Any]) -> list[CandidateVerificationResult]:
        captured["verifications"].append(list(items))
        return [CandidateVerificationResult(type=item.type, id=item.id, outcome="exists", aggregate_id=case.target_id) for item in items]

    monkeypatch.setattr(ReconciliationClient, "get_service_manifest", get_service_manifest)
    monkeypatch.setattr(ReconciliationClient, "reconcile_batch", reconcile_batch)
    monkeypatch.setattr(ReconciliationClient, "verify_candidates", verify_candidates)
    return captured


async def _create_project(client, case: CaseConfig) -> None:
    response = await client.post(
        "/api/v1/projects",
        json={
            "name": case.project_name,
            "data_provider_code": "test-provider",
            "provider_schema": "schema-one",
            "entities": _entities(case),
        },
    )
    assert response.status_code == 201, response.text


async def _register_specification(client, case: CaseConfig) -> None:
    spec: dict[str, Any] = {"remote": {"service_type": case.entity_name}}
    if case.property_source is not None:
        spec["property_mappings"] = {PROPERTY_ID: case.property_source}
    response = await client.post(
        f"/api/v1/projects/{case.project_name}/reconciliation/mapping-registry",
        json={"entity_name": case.entity_name, "target_field": case.target_field, "spec": spec},
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


def _assert_queries(captured: dict[str, list[Any]], case: CaseConfig) -> None:
    """Assert the query shape for the case, including property presence."""
    queries = captured["queries"][0]
    assert len(queries) == 2
    for query in queries.values():
        assert query["type"] == case.entity_name
        assert query["query"] == SEARCH_LABEL
    if case.property_source is None:
        assert all("properties" not in query for query in queries.values())
    else:
        # Each row sends its own property source value, not the shared search label.
        assert _query_property_values(queries) == set(case.property_values)


def _assert_sidecar(tmp_path: Path, case: CaseConfig) -> bytes:
    """Assert one committed link keyed by the accepted local key and return the sidecar bytes."""
    sidecar = yaml.safe_load(_sidecar_path(tmp_path, case).read_text(encoding="utf-8"))
    entity = sidecar["entities"][case.entity_name]
    accepted_key = case.local_keys[0]
    assert entity["local_key"] == case.local_key
    assert entity["public_id"] == case.public_id
    assert entity["entity_type"] == "primary"
    assert set(entity["links"]) == {accepted_key}
    assert SEARCH_LABEL not in entity["links"]
    link = entity["links"][accepted_key]
    assert link["target_id"] == case.target_id
    assert link["owner"] == {"entity_name": case.entity_name, "target_field": case.target_field}
    assert link["committed_at"]
    assert link["verified_at"]
    assert entity["local_only_approvals"] == {}
    return _sidecar_path(tmp_path, case).read_bytes()


async def _normalize_twice(project_file: Path, case: CaseConfig, monkeypatch) -> list[tuple[dict[str, tuple[int, int | None]], list[int]]]:
    """Normalize twice offline and collect parent identities plus child foreign keys."""

    def deny_network(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("Normalization must not make network requests")

    monkeypatch.setattr(httpx.AsyncClient, "request", deny_network)
    results: list[tuple[dict[str, tuple[int, int | None]], list[int]]] = []
    for _ in range(2):
        normalizer = ShapeShifter(project=str(project_file))
        await normalizer.normalize()
        parents = normalizer.table_store[case.entity_name].set_index(case.local_key)
        identities = {
            str(key): (
                int(row["system_id"]),
                None if pd.isna(row[case.public_id]) else int(row[case.public_id]),
            )
            for key, row in parents.iterrows()
        }
        child_links = sorted(int(value) for value in normalizer.table_store[CHILD_ENTITY_NAME][case.public_id].tolist())
        results.append((identities, child_links))
    return results


class TestManifestDrivenGroupedParity:
    """Review, keyed export, unchanged rerun, and offline identity for each remote type."""

    def setup_method(self) -> None:
        _reset_singletons()

    def teardown_method(self) -> None:
        _reset_singletons()

    @pytest.mark.parametrize("case", CASES, ids=[case.entity_name for case in CASES])
    async def test_grouped_review_export_and_unchanged_rerun(
        self, authorized_client, tmp_path: Path, monkeypatch, case: CaseConfig
    ) -> None:
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        captured = _install_mocked_service(monkeypatch, case)
        await _create_project(authorized_client, case)
        await _register_specification(authorized_client, case)
        accepted_key, rejected_key = case.local_keys

        matched = await authorized_client.post(f"{case.path}/auto-reconcile-sync")

        assert matched.status_code == 200, matched.text
        assert captured["manifests"], "The manifest must be read before matching"
        assert matched.json()["total"] == 2
        assert matched.json()["proposed"] == 2
        assert set(matched.json()["candidates"]) == set(case.local_keys)
        assert all(item["id"] == case.candidate_uri for items in matched.json()["candidates"].values() for item in items)
        _assert_queries(captured, case)
        # A 100% mocked candidate is proposed, never accepted automatically.
        assert not _sidecar_path(tmp_path, case).exists()
        assert _read_catalog_decisions(tmp_path, case) == {
            accepted_key: ("proposed", None, SEARCH_LABEL),
            rejected_key: ("proposed", None, SEARCH_LABEL),
        }

        accepted = await authorized_client.post(
            f"{case.path}/mapping",
            json={
                "local_key_value": accepted_key,
                "status": "accepted",
                "target_id": case.target_id,
                "candidate_id": case.candidate_uri,
            },
        )
        assert accepted.status_code == 200, accepted.text
        rejected = await authorized_client.post(f"{case.path}/mapping", json={"local_key_value": rejected_key, "status": "rejected"})
        assert rejected.status_code == 200, rejected.text
        assert _read_catalog_decisions(tmp_path, case) == {
            accepted_key: ("accepted", case.target_id, SEARCH_LABEL),
            rejected_key: ("rejected", None, SEARCH_LABEL),
        }

        preview = await authorized_client.get(f"{case.path}/preview")
        assert preview.status_code == 200, preview.text
        assert {row["local_key_value"]: (row["status"], row["target_id"]) for row in preview.json()} == {
            accepted_key: ("accepted", case.target_id),
            rejected_key: ("rejected", None),
        }

        exported = await authorized_client.post(f"{case.path}/export-to-mapping")

        assert exported.status_code == 200, exported.text
        assert exported.json()["exported"] == 1
        assert exported.json()["removed"] == 0
        assert exported.json()["outcomes"] == [{"local_key_value": accepted_key, "outcome": "verified", "reason": None}]
        assert [(item.type, item.id) for item in captured["verifications"][-1]] == [(case.entity_name, case.candidate_uri)]
        sidecar_bytes = _assert_sidecar(tmp_path, case)

        rerun = await authorized_client.post(f"{case.path}/auto-reconcile-sync")

        assert rerun.status_code == 200, rerun.text
        assert rerun.json()["total"] == 2
        assert rerun.json()["proposed"] == 0
        assert _read_catalog_decisions(tmp_path, case) == {
            accepted_key: ("accepted", case.target_id, SEARCH_LABEL),
            rejected_key: ("rejected", None, SEARCH_LABEL),
        }

        unchanged = await authorized_client.post(f"{case.path}/export-to-mapping")

        assert unchanged.status_code == 200, unchanged.text
        assert unchanged.json()["exported"] == 0
        assert unchanged.json()["removed"] == 0
        assert _sidecar_path(tmp_path, case).read_bytes() == sidecar_bytes

        results = await _normalize_twice(_project_file(tmp_path, case), case, monkeypatch)

        expected = (
            {accepted_key: (PARENT_SYSTEM_IDS[0], case.target_id), rejected_key: (PARENT_SYSTEM_IDS[1], None)},
            [PARENT_SYSTEM_IDS[0]],
        )
        assert results == [expected, expected]
