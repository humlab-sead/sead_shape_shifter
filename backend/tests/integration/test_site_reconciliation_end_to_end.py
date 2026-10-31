"""Exercise reviewed site links against the disposable Authority Service and SIMS."""

from __future__ import annotations

import os
import subprocess
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
import pandas as pd
import psycopg
import pytest
import yaml

from backend.app.clients.reconciliation_client import ReconciliationClient, ReconciliationQuery
from backend.app.core.config import settings
from backend.app.models.reconciliation import CandidateVerificationRequestItem
from backend.app.services import project_service, validation_service, yaml_service
from src.normalizer import ShapeShifter

pytestmark = pytest.mark.integration
_RUN_LIVE = os.getenv("SIMS_INTEGRATION_DB") == "1"
_SITE_LABEL = "org.sead-shape-shifter.sims-candidate-verification"


@pytest.fixture(autouse=True)
def isolate_project_services() -> Iterator[None]:
    project_service._project_service = None
    validation_service._validation_service = None
    yaml_service._yaml_service = None
    yield
    project_service._project_service = None
    validation_service._validation_service = None
    yaml_service._yaml_service = None


def _require_disposable_settings(monkeypatch, tmp_path: Path) -> dict[str, object]:
    """Require the helper-owned loopback database and point both clients at it."""
    host = os.getenv("SEAD_DISPOSABLE_POSTGRES_HOST")
    port = os.getenv("SEAD_DISPOSABLE_POSTGRES_PORT")
    dbname = os.getenv("SEAD_DISPOSABLE_POSTGRES_DB")
    user = os.getenv("SEAD_DISPOSABLE_POSTGRES_USER")
    service_url = os.getenv("SEAD_DISPOSABLE_AUTHORITY_URL")
    assert (host, port, dbname, user) == (
        "127.0.0.1",
        "55432",
        "sead_staging",
        "postgres",
    ), "Set SEAD_DISPOSABLE_POSTGRES_{HOST,PORT,DB,USER} to the helper-owned 127.0.0.1:55432/sead_staging database."
    assert (
        service_url and urlsplit(service_url).hostname in {"localhost", "127.0.0.1"} and urlsplit(service_url).port
    ), "SEAD_DISPOSABLE_AUTHORITY_URL must point to a running loopback Authority Service."
    container = subprocess.run(
        ["podman", "inspect", "--format", f'{{{{ index .Config.Labels "{_SITE_LABEL}" }}}}', "sead-sims-candidate-verification"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert container.stdout.strip() == "true", "The disposable database must belong to the Authority Service helper."
    parameters: dict[str, object] = {"host": host, "port": int(port), "dbname": dbname, "user": user, "connect_timeout": 5}
    monkeypatch.setattr(settings, "RECONCILIATION_SERVICE_URL", service_url)
    monkeypatch.setattr(settings, "SIMS_SERVICE_URL", service_url)
    monkeypatch.setattr(settings, "INGEST_TARGET_HOST", host)
    monkeypatch.setattr(settings, "INGEST_TARGET_PORT", int(port))
    monkeypatch.setattr(settings, "INGEST_TARGET_DBNAME", dbname)
    monkeypatch.setattr(settings, "INGEST_TARGET_USER", user)
    monkeypatch.setattr(settings, "INGEST_OUTPUT_DIR", tmp_path / "bundles")
    return parameters


async def _require_readiness(client: httpx.AsyncClient) -> None:
    """Reject metadata-only services before sending reconciliation requests."""
    response = await client.get("/reconcile/readiness", params={"type": "site"})
    assert response.status_code == 200, f"Site readiness failed: HTTP {response.status_code}"
    result = response.json()
    assert result.get("ready") is True and result.get("type") == "site", f"Site readiness failed: {result.get('reason')}"


@pytest.fixture
async def adopted_site(monkeypatch, tmp_path: Path) -> AsyncIterator[tuple[int, str, str, int, str]]:
    if not _RUN_LIVE:
        pytest.skip("Set SIMS_INTEGRATION_DB=1 for the helper-owned disposable database run")
    parameters = _require_disposable_settings(monkeypatch, tmp_path)
    async with await psycopg.AsyncConnection.connect(**parameters) as connection:
        async with connection.cursor() as cursor:
            await cursor.execute("SELECT to_regprocedure('authority.fuzzy_site(text,integer)')")
            assert (await cursor.fetchone())[0] is not None, "Install the site match function before Phase 7."
            await cursor.execute(
                """
                SELECT s.site_id, s.label
                FROM authority.site s
                JOIN sead_identity.tracked_identities t ON t.entity_type = 'site' AND t.aggregate_id = s.site_id
                WHERE t.lifecycle_state = 'materialized' AND s.label IS NOT NULL AND btrim(s.label) <> ''
                ORDER BY s.site_id LIMIT 20
                """
            )
            sites = await cursor.fetchall()
            assert sites, "Bootstrap existing sites into SIMS as materialized before Phase 7."
            await cursor.execute("SELECT next_internal_id FROM sead_identity.internal_id_allocators WHERE entity_type = 'site'")
            allocator = await cursor.fetchone()
            await cursor.execute("SELECT max(site_id) FROM authority.site")
            maximum = (await cursor.fetchone())[0]
            assert allocator is not None and allocator[0] > maximum, "The site allocator must exceed existing SEAD site IDs."

    url = settings.RECONCILIATION_SERVICE_URL.rstrip("/")
    async with httpx.AsyncClient(base_url=url, timeout=15) as client:
        await _require_readiness(client)
    reconciliation = ReconciliationClient(base_url=url, timeout=15)
    try:
        matched_site: tuple[int, str, str] | None = None
        for site_id, label in sites:
            matches = await reconciliation.reconcile_batch({"q0": ReconciliationQuery(query=label, entity_type="site", limit=20)})
            for candidate in matches["q0"]:
                checked = await reconciliation.verify_candidates([CandidateVerificationRequestItem(type="site", id=candidate.id)])
                if checked[0].outcome == "exists" and checked[0].aggregate_id == site_id:
                    matched_site = int(site_id), str(label), candidate.id
                    break
            if matched_site is not None:
                break
        assert matched_site is not None, "No adopted site among the first 20 labeled rows passed the real match and candidate check."
    finally:
        await reconciliation.close()

    provider_code = f"phase7-{uuid4().hex[:12]}"
    async with await psycopg.AsyncConnection.connect(**parameters) as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(
                """
                INSERT INTO public.tbl_data_providers (data_provider_id, data_provider_code, data_provider_name)
                SELECT COALESCE(MAX(data_provider_id), 0) + 1, %s, 'Phase 7 disposable test provider'
                FROM public.tbl_data_providers
                RETURNING data_provider_id
                """,
                (provider_code,),
            )
            provider_id = int((await cursor.fetchone())[0])
    registry_path = Path(settings.GLOBAL_DATA_PROVIDER_DIR) / f"{provider_code}.yml"
    registry_path.write_text(
        yaml.safe_dump(
            {
                "code": provider_code,
                "name": "Disposable test provider",
                "schemas": [{"provider_schema": "schema-one", "scope_name": f"provider://{provider_code}/schema-one"}],
            }
        ),
        encoding="utf-8",
    )
    try:
        yield (matched_site[0], matched_site[1], matched_site[2], provider_id, provider_code)
    finally:
        async with await psycopg.AsyncConnection.connect(**parameters) as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(
                    "DELETE FROM public.tbl_data_providers WHERE data_provider_id = %s AND data_provider_code = %s",
                    (provider_id, provider_code),
                )
                assert cursor.rowcount == 1, "The disposable provider fixture was not removed."


async def _create_project(
    client: httpx.AsyncClient,
    name: str,
    label: str,
    *,
    keys: tuple[str, ...] = ("accepted", "local", "rejected", "undecided"),
    child: bool = True,
    provider: tuple[int, str] | None = None,
) -> Path:
    """Create an authorized, isolated site project with a child Core link."""
    entities: dict[str, dict] = {
        "site": {
            "type": "fixed",
            "public_id": "site_id",
            "keys": ["national_site_identifier"],
            "columns": ["system_id", "site_id", "national_site_identifier", "site_name"],
            "values": [[index + 10000, None, key, label] for index, key in enumerate(keys, 1)],
        }
    }
    if child:
        entities["sample_group"] = {
            "type": "fixed",
            "public_id": "sample_group_id",
            "keys": ["sample_group_name"],
            "columns": ["system_id", "sample_group_id", "sample_group_name"],
            "values": [[1, None, "child"]],
            "depends_on": ["site"],
            "extra_columns": {"site_ref": 10001},
            "foreign_keys": [{"entity": "site", "local_keys": ["site_ref"], "remote_keys": ["system_id"]}],
        }
    if provider is not None:
        entities["data_provider"] = {
            "type": "fixed",
            "public_id": "data_provider_id",
            "keys": ["data_provider_code"],
            "columns": ["system_id", "data_provider_id", "data_provider_code"],
            "values": [[1, provider[0], provider[1]]],
        }
    response = await client.post(
        "/api/v1/projects",
        json={
            "name": name,
            "data_provider_code": provider[1] if provider is not None else "test-provider",
            "provider_schema": "schema-one",
            "entities": entities,
        },
    )
    assert response.status_code == 201, response.text
    return Path(settings.PROJECTS_DIR) / name


async def _decision(client: httpx.AsyncClient, path: str, key: str, status: str, site_id: int = 0, uri: str = "") -> None:
    payload: dict[str, object] = {"local_key_value": key, "status": status}
    if status == "accepted":
        payload.update(target_id=site_id, candidate_id=uri)
    response = await client.post(f"{path}/mapping", json=payload)
    assert response.status_code == 200, response.text


async def _export(client: httpx.AsyncClient, path: str) -> dict:
    response = await client.post(f"{path}/export-to-mapping")
    assert response.status_code == 200, response.text
    return response.json()


def _sidecar(directory: Path, name: str) -> dict:
    return yaml.safe_load((directory / f"{name}-mapping.yml").read_text(encoding="utf-8"))


async def _register_site_reconciliation(client: httpx.AsyncClient, name: str) -> str:
    path = f"/api/v1/projects/{name}/reconciliation/site/site_name"
    response = await client.post(
        f"/api/v1/projects/{name}/reconciliation/mapping-registry",
        json={"entity_name": "site", "target_field": "site_name", "spec": {"remote": {"service_type": "site"}}},
    )
    assert response.status_code == 201, response.text
    response = await client.post(f"{path}/auto-reconcile-sync")
    assert response.status_code == 200, response.text
    return path


async def _attach_target_model(client: httpx.AsyncClient, directory: Path, name: str) -> None:
    target_model = {
        "model": {"name": "Phase 7 disposable sites", "version": "1.0.0"},
        "constraints": [],
        "entities": {
            "site": {
                "role": "lookup",
                "public_id": "site_id",
                "target_table": "tbl_sites",
                "identity_tracking": "reconciled",
                "reconciliation": "reconcile-exact",
            },
            "data_provider": {"role": "lookup", "public_id": "data_provider_id", "target_table": "tbl_data_providers"},
        },
    }
    (directory / "target-model.yml").write_text(yaml.safe_dump(target_model), encoding="utf-8")
    response = await client.patch(f"/api/v1/projects/{name}/metadata", json={"target_model": "@load: target-model.yml"})
    assert response.status_code == 200, response.text


def _submission(name: str, *, run_id: str | None = None) -> dict:
    return {
        "project_name": name,
        "submission_context": {
            "submission_name": name,
            "timestamp": "2026-10-31T12:00:00",
            "datatype": "mal",
            "identifier": name.upper().replace("-", "_"),
            "run_id": run_id or uuid4().hex,
        },
    }


@pytest.mark.asyncio
async def test_review_export_offline_normalization_and_transitions(authorized_client, adopted_site) -> None:
    site_id, label, uri, _, _ = adopted_site
    name = f"phase7-{uuid4().hex[:12]}"
    directory = await _create_project(authorized_client, name, label)
    path = await _register_site_reconciliation(authorized_client, name)
    proposed = await authorized_client.post(f"{path}/auto-reconcile-sync")
    assert proposed.status_code == 200, proposed.text
    assert proposed.json()["total"] == 4
    assert any(item["id"] == uri for item in proposed.json()["candidates"]["accepted"])
    await _decision(authorized_client, path, "accepted", "accepted", site_id, uri)
    await _decision(authorized_client, path, "local", "local-only")
    await _decision(authorized_client, path, "rejected", "rejected")
    first = await _export(authorized_client, path)
    assert first["outcomes"] == [{"local_key_value": "accepted", "outcome": "verified", "reason": None}]
    entity = _sidecar(directory, name)["entities"]["site"]
    assert entity["links"]["accepted"]["target_id"] == site_id
    assert entity["links"]["accepted"]["owner"] == {"entity_name": "site", "target_field": "site_name"}
    assert entity["links"]["accepted"]["verified_at"]
    assert entity["local_only_approvals"]["local"]["owner"] == {"entity_name": "site", "target_field": "site_name"}
    assert set(entity["links"]) == {"accepted"}
    assert set(entity["local_only_approvals"]) == {"local"}
    sidecar_bytes = (directory / f"{name}-mapping.yml").read_bytes()
    rerun = await authorized_client.post(f"{path}/auto-reconcile-sync")
    assert rerun.status_code == 200, rerun.text
    assert rerun.json()["proposed"] == 1
    catalog = yaml.safe_load((directory / f"{name}-reconciliation.yml").read_text(encoding="utf-8"))
    assert {item["local_key_value"]: item["status"] for item in catalog["entities"]["site"]["site_name"]["mapping"]} == {
        "accepted": "accepted",
        "local": "local-only",
        "rejected": "rejected",
        "undecided": "proposed",
    }
    unchanged = await _export(authorized_client, path)
    assert unchanged["exported"] == unchanged["removed"] == unchanged["exported_local_only_approvals"] == 0
    assert (directory / f"{name}-mapping.yml").read_bytes() == sidecar_bytes

    with pytest.MonkeyPatch.context() as no_network:
        no_network.setattr(httpx.AsyncClient, "request", lambda *_args, **_kwargs: pytest.fail("Normalization used HTTP"))
        results = []
        for _ in range(2):
            normalizer = ShapeShifter(project=str(directory / "shapeshifter.yml"))
            await normalizer.normalize()
            sites = normalizer.table_store["site"].set_index("national_site_identifier")
            ids = {key: None if pd.isna(value) else int(value) for key, value in sites["site_id"].items()}
            child_fk = int(normalizer.table_store["sample_group"]["site_id"].iloc[0])
            results.append((ids, child_fk))
    assert results == [({"accepted": site_id, "local": None, "rejected": None, "undecided": None}, 10001)] * 2
    print(f"Phase 7 site IDs: accepted={site_id}, local/rejected/undecided=none; Core child site_id={results[0][1]}")

    await _decision(authorized_client, path, "accepted", "rejected")
    rejected = await _export(authorized_client, path)
    assert rejected["removed"] == 1
    assert "accepted" not in _sidecar(directory, name)["entities"]["site"]["links"]
    await _decision(authorized_client, path, "accepted", "local-only")
    await _export(authorized_client, path)
    assert "accepted" in _sidecar(directory, name)["entities"]["site"]["local_only_approvals"]
    await _decision(authorized_client, path, "accepted", "accepted", site_id, uri)
    await _export(authorized_client, path)
    assert "accepted" not in _sidecar(directory, name)["entities"]["site"]["local_only_approvals"]

    missing_id = site_id + 1000000000
    absent_uri = uri.rsplit("/", 1)[0] + f"/{missing_id}"
    await _decision(authorized_client, path, "accepted", "accepted", missing_id, absent_uri)
    absent = await _export(authorized_client, path)
    assert absent["outcomes"][0]["outcome"] == "not_found"
    assert "accepted" not in _sidecar(directory, name)["entities"]["site"]["links"]


@pytest.mark.asyncio
async def test_unreviewed_and_rejected_rows_block_ingestion(authorized_client, adopted_site) -> None:
    site_id, label, uri, provider_id, provider_code = adopted_site
    name = f"phase7-block-{uuid4().hex[:12]}"
    directory = await _create_project(
        authorized_client, name, label, keys=("accepted", "rejected", "undecided"), child=False, provider=(provider_id, provider_code)
    )
    await _attach_target_model(authorized_client, directory, name)
    path = await _register_site_reconciliation(authorized_client, name)
    await _decision(authorized_client, path, "accepted", "accepted", site_id, uri)
    await _decision(authorized_client, path, "rejected", "rejected")
    await _export(authorized_client, path)
    request = _submission(name)
    endpoint = "/api/v1/ingesters/sead_change_request/from-project"
    validated = await authorized_client.post(f"{endpoint}/validate", json=request)
    assert validated.status_code == 200, validated.text
    assert validated.json()["is_valid"] is False
    assert validated.json()["errors"]
    ingested = await authorized_client.post(f"{endpoint}/ingest", json=request)
    assert ingested.status_code == 200, ingested.text
    assert ingested.json()["success"] is False
    assert ingested.json()["deploy_artifact"] is None
    assert ingested.json()["output_path"] is None


@pytest.mark.asyncio
async def test_adopted_binding_and_local_only_allocation(authorized_client, adopted_site) -> None:
    site_id, label, uri, provider_id, provider_code = adopted_site
    name = f"phase7-bind-{uuid4().hex[:12]}"
    directory = await _create_project(
        authorized_client, name, label, keys=("accepted", "local"), child=False, provider=(provider_id, provider_code)
    )
    await _attach_target_model(authorized_client, directory, name)
    path = await _register_site_reconciliation(authorized_client, name)
    await _decision(authorized_client, path, "accepted", "accepted", site_id, uri)
    await _decision(authorized_client, path, "local", "local-only")
    exported = await _export(authorized_client, path)
    assert exported["exported"] == exported["exported_local_only_approvals"] == 1
    request = _submission(name)
    endpoint = "/api/v1/ingesters/sead_change_request/from-project"
    validated = await authorized_client.post(f"{endpoint}/validate", json=request)
    assert validated.status_code == 200 and validated.json()["is_valid"], validated.text
    ingested = await authorized_client.post(f"{endpoint}/ingest", json=request)
    assert ingested.status_code == 200 and ingested.json()["success"], ingested.text
    result = ingested.json()
    assert result["deploy_artifact"] is not None
    assert result["output_path"] and Path(result["output_path"]).is_relative_to(settings.INGEST_OUTPUT_DIR)
    assert str(site_id) in result["deploy_artifact"]["deploy_sql"]
    print(f"Phase 7 SIMS adopted site ID: {site_id}; artifact: {result['output_path']}")


@pytest.mark.asyncio
async def test_health_only_service_cannot_pass_site_readiness() -> None:
    def health_only(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/reconcile":
            return httpx.Response(200, json={"name": "Health only"})
        return httpx.Response(404, json={"detail": "No database-backed readiness check"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(health_only), base_url="http://localhost") as client:
        health = await client.get("/reconcile")
        assert health.status_code == 200 and health.json()["name"] == "Health only"
        with pytest.raises(AssertionError, match="Site readiness failed: HTTP 404"):
            await _require_readiness(client)
