"""Exercise reviewed site links against the disposable Authority Service and SIMS."""

from __future__ import annotations

import os
import re
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
from src.business_keys import business_id_for_row
from src.normalizer import ShapeShifter

pytestmark = pytest.mark.integration
_RUN_LIVE = os.getenv("SIMS_INTEGRATION_DB") == "1"
_SITE_LABEL = "org.sead-shape-shifter.sims-candidate-verification"


@pytest.fixture(autouse=True, name="isolate_project_services")
def _isolate_project_services() -> Iterator[None]:
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
    port = os.getenv("SEAD_DISPOSABLE_POSTGRES_PORT") or "55432"
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


async def _site_allocator_snapshot(parameters: dict[str, object]) -> tuple[int, int]:
    """Return the site allocator value and tracked-identity count."""
    async with await psycopg.AsyncConnection.connect(**parameters) as connection:
        async with connection.cursor() as cursor:
            await cursor.execute("SELECT next_internal_id FROM sead_identity.internal_id_allocators WHERE entity_type = 'site'")
            allocator = await cursor.fetchone()
            await cursor.execute("SELECT count(*) FROM sead_identity.tracked_identities WHERE entity_type = 'site'")
            tracked_count = await cursor.fetchone()
    assert allocator is not None and tracked_count is not None, "The site SIMS allocator must be initialized."
    return int(allocator[0]), int(tracked_count[0])


async def _site_identity_evidence(parameters: dict[str, object], scope_name: str) -> list[tuple[str, int | None, str | None, str | None]]:
    """Read site business keys and any SIMS bindings in one provider scope."""
    async with await psycopg.AsyncConnection.connect(**parameters) as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(
                """
                SELECT identity_key.key_value, tracked.aggregate_id, binding.method, tracked.lifecycle_state
                FROM sead_identity.source_scopes AS scope
                JOIN sead_identity.source_identities AS source_identity USING (scope_uuid)
                JOIN sead_identity.source_identity_keys AS identity_key USING (source_identity_uuid)
                LEFT JOIN sead_identity.bindings AS binding USING (source_identity_uuid)
                LEFT JOIN sead_identity.tracked_identities AS tracked USING (tracked_identity_uuid)
                WHERE scope.scope_name = %s
                  AND source_identity.entity_type = 'site'
                  AND identity_key.key_type = 'business_key'
                """,
                (scope_name,),
            )
            rows = await cursor.fetchall()
    return [
        (
            str(key_value),
            int(aggregate_id) if aggregate_id is not None else None,
            str(method) if method is not None else None,
            str(lifecycle_state) if lifecycle_state is not None else None,
        )
        for key_value, aggregate_id, method, lifecycle_state in rows
    ]


async def _first_existing_method_id(parameters: dict[str, object]) -> int:
    """Return an existing method ID for the required sample-group target row."""
    async with await psycopg.AsyncConnection.connect(**parameters) as connection:
        async with connection.cursor() as cursor:
            await cursor.execute("SELECT method_id FROM public.tbl_methods ORDER BY method_id LIMIT 1")
            row = await cursor.fetchone()
    assert row is not None, "The disposable target database must contain a method row."
    return int(row[0])


def _inserted_column_value(deploy_sql: str, table_name: str, column_name: str) -> str:
    """Return one value from a generated single-row INSERT statement."""
    pattern = re.compile(
        rf'INSERT\s+INTO\s+(?:(?:"?[A-Za-z_][A-Za-z_0-9]*"?)\.)?"?{re.escape(table_name)}"?'
        rf"\s*\((?P<columns>[^)]*)\)\s*VALUES\s*\((?P<values>[^)]*)\)",
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(deploy_sql)
    assert match is not None, f"No INSERT statement for '{table_name}' was found in the generated artifact."
    columns = [column.strip().strip('"') for column in match.group("columns").split(",")]
    values = [value.strip() for value in match.group("values").split(",")]
    assert len(columns) == len(values), f"INSERT column/value count differs for '{table_name}'."
    assert column_name in columns, f"Column '{column_name}' is absent from the '{table_name}' INSERT."
    return values[columns.index(column_name)].strip("'")


@pytest.fixture(name="adopted_site")
async def _adopted_site(monkeypatch, tmp_path: Path) -> AsyncIterator[tuple[int, str, str, int, str]]:
    if not _RUN_LIVE:
        pytest.skip("Set SIMS_INTEGRATION_DB=1 for the helper-owned disposable database run")
    parameters = _require_disposable_settings(monkeypatch, tmp_path)
    async with await psycopg.AsyncConnection.connect(**parameters) as connection:
        async with connection.cursor() as cursor:
            await cursor.execute("SELECT to_regprocedure('authority.fuzzy_site(text,integer)')")
            data = await cursor.fetchone()
            assert data is not None, "The site match function must exist."
            assert data[0] is not None, "Install the site match function before Phase 7."
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
            data = await cursor.fetchone()
            assert data is not None, "Failed to fetch the maximum site_id."
            maximum = data[0]
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
            data = await cursor.fetchone()
            assert data is not None, "Failed to fetch the provider_id."
            provider_id = int(data[0])
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
    method_id: int | None = None,
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
        sample_group: dict = {
            "type": "fixed",
            "public_id": "sample_group_id",
            "keys": ["sample_group_name"],
            "columns": ["system_id", "sample_group_id", "sample_group_name"],
            "values": [[1, None, "child"]],
            "depends_on": ["site"],
            "extra_columns": {"site_ref": 10001},
            "foreign_keys": [{"entity": "site", "local_keys": ["site_ref"], "remote_keys": ["system_id"]}],
        }
        if method_id is not None:
            sample_group["extra_columns"] = {"site_ref": 10001, "method_id": method_id}
            sample_group["foreign_key_value_sources"] = {"method": "public_id"}
        entities["sample_group"] = sample_group
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
            "method": {"role": "lookup", "public_id": "method_id", "target_table": "tbl_methods"},
            "sample_group": {
                "role": "fact",
                "public_id": "sample_group_id",
                "public_id_generation": "database_sequence",
                "target_table": "tbl_sample_groups",
                "identity_tracking": "child",
                "aggregate_parent": "site",
                "columns": {
                    "site_id": {"required": True, "type": "integer", "nullable": False},
                    "method_id": {"required": True, "type": "integer", "nullable": False},
                    "sample_group_name": {"required": True, "type": "string", "nullable": True},
                },
                "foreign_keys": [{"entity": "site", "required": True}, {"entity": "method", "required": True}],
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
async def test_unreviewed_and_rejected_rows_block_ingestion(authorized_client, adopted_site, monkeypatch, tmp_path: Path) -> None:
    site_id, label, uri, provider_id, provider_code = adopted_site
    parameters = _require_disposable_settings(monkeypatch, tmp_path)
    allocator_before = await _site_allocator_snapshot(parameters)
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
    assert await _site_allocator_snapshot(parameters) == allocator_before
    scope_name = f"provider://{provider_code}/schema-one"
    business_keys = {record[0] for record in await _site_identity_evidence(parameters, scope_name)}
    for key in ("rejected", "undecided"):
        expected_key = business_id_for_row(["national_site_identifier"], {"national_site_identifier": key})
        assert expected_key not in business_keys, f"Blocked '{key}' row was sent to SIMS."


@pytest.mark.asyncio
async def test_adopted_binding_and_local_only_allocation(authorized_client, adopted_site, monkeypatch, tmp_path: Path) -> None:
    site_id, label, uri, provider_id, provider_code = adopted_site
    parameters = _require_disposable_settings(monkeypatch, tmp_path)
    method_id = await _first_existing_method_id(parameters)
    allocator_before = await _site_allocator_snapshot(parameters)
    name = f"phase7-bind-{uuid4().hex[:12]}"
    directory = await _create_project(
        authorized_client,
        name,
        label,
        keys=("accepted", "local"),
        child=True,
        method_id=method_id,
        provider=(provider_id, provider_code),
    )
    await _attach_target_model(authorized_client, directory, name)
    path = await _register_site_reconciliation(authorized_client, name)
    await _decision(authorized_client, path, "accepted", "accepted", site_id, uri)
    await _decision(authorized_client, path, "local", "local-only")
    exported = await _export(authorized_client, path)
    assert exported["exported"] == exported["exported_local_only_approvals"] == 1
    with pytest.MonkeyPatch.context() as no_network:
        no_network.setattr(httpx.AsyncClient, "request", lambda *_args, **_kwargs: pytest.fail("Normalization used HTTP"))
        normalization_results = []
        for _ in range(2):
            normalizer = ShapeShifter(project=str(directory / "shapeshifter.yml"))
            await normalizer.normalize()
            sites = normalizer.table_store["site"].set_index("national_site_identifier")
            site_ids = {key: None if pd.isna(value) else int(value) for key, value in sites["site_id"].items()}
            child = normalizer.table_store["sample_group"].iloc[0]
            normalization_results.append((site_ids, int(child["site_id"]), int(child["method_id"])))
    assert normalization_results == [
        ({"accepted": site_id, "local": None}, 10001, method_id),
        ({"accepted": site_id, "local": None}, 10001, method_id),
    ]
    request = _submission(name)
    endpoint = "/api/v1/ingesters/sead_change_request/from-project"
    validated = await authorized_client.post(f"{endpoint}/validate", json=request)
    assert validated.status_code == 200 and validated.json()["is_valid"], validated.text
    ingested = await authorized_client.post(f"{endpoint}/ingest", json=request)
    assert ingested.status_code == 200 and ingested.json()["success"], ingested.text
    result = ingested.json()
    assert result["deploy_artifact"] is not None
    assert result["output_path"] and Path(result["output_path"]).is_relative_to(settings.INGEST_OUTPUT_DIR)
    deploy_artifact = result["deploy_artifact"]
    direct_foreign_keys = deploy_artifact["metadata_artifact"]["direct_target_id_foreign_keys"]
    assert direct_foreign_keys == [{"source_entity": "sample_group", "target_entity": "method", "column": "method_id"}]
    package_child_id = _inserted_column_value(deploy_artifact["deploy_sql"], "tbl_sample_groups", "sample_group_id")
    assert package_child_id.isdigit()
    package_child_site_id = _inserted_column_value(deploy_artifact["deploy_sql"], "tbl_sample_groups", "site_id")
    assert package_child_site_id == str(site_id)
    assert package_child_site_id != str(normalization_results[0][1])
    package_child_method_id = _inserted_column_value(deploy_artifact["deploy_sql"], "tbl_sample_groups", "method_id")
    assert package_child_method_id == str(method_id)
    async with await psycopg.AsyncConnection.connect(**parameters) as connection:
        async with connection.cursor() as cursor:
            await cursor.execute("SELECT EXISTS (SELECT 1 FROM public.tbl_sites WHERE site_id = %s)", (site_id,))
            data = await cursor.fetchone()
            assert data is not None, "Failed to fetch site existence."
            assert data[0] is True
            await cursor.execute("SELECT EXISTS (SELECT 1 FROM public.tbl_methods WHERE method_id = %s)", (method_id,))
            data = await cursor.fetchone()
            assert data is not None, "Failed to fetch method existence."
            assert data[0] is True

    allocated_site_id = allocator_before[0]
    allocator_after = await _site_allocator_snapshot(parameters)
    assert allocator_after == (allocator_before[0] + 1, allocator_before[1] + 1)
    scope_name = f"provider://{provider_code}/schema-one"
    identity_evidence = await _site_identity_evidence(parameters, scope_name)
    accepted_business_key = business_id_for_row(["national_site_identifier"], {"national_site_identifier": "accepted"})
    local_business_key = business_id_for_row(["national_site_identifier"], {"national_site_identifier": "local"})
    assert any(
        key_value == accepted_business_key and aggregate_id == site_id and lifecycle_state == "materialized"
        for key_value, aggregate_id, _, lifecycle_state in identity_evidence
    )
    assert any(
        key_value == local_business_key and aggregate_id == allocated_site_id and method == "allocated"
        for key_value, aggregate_id, method, _ in identity_evidence
    )
    print(
        f"Phase 7 IDs: adopted site={site_id}, local-only site={allocated_site_id}, "
        f"sample_group={package_child_id}, method={method_id}; "
        f"Core child site_id={normalization_results[0][1]}, "
        f"package child site_id={package_child_site_id}, "
        f"package child method_id={package_child_method_id}"
    )


@pytest.mark.asyncio
async def test_export_outage_recovery_preserves_manual_and_unowned_links(
    authorized_client, adopted_site, monkeypatch, tmp_path: Path
) -> None:
    site_id, label, uri, _, _ = adopted_site
    live_service_url = settings.RECONCILIATION_SERVICE_URL
    name = f"phase7-outage-{uuid4().hex[:12]}"
    directory = await _create_project(authorized_client, name, label, keys=("accepted",), child=False)
    path = await _register_site_reconciliation(authorized_client, name)
    await _decision(authorized_client, path, "accepted", "accepted", site_id, uri)
    await _export(authorized_client, path)

    sidecar_path = directory / f"{name}-mapping.yml"
    sidecar = _sidecar(directory, name)
    protected_links = {
        "manual-protected": {
            "target_id": site_id,
            "source": "manual",
            "created_at": "2026-10-31T12:00:00Z",
            "committed_at": "2026-10-31T12:00:00Z",
            "created_by": "phase7-manual",
        },
        "unowned-protected": {
            "target_id": site_id,
            "source": "reconciliation",
            "created_at": "2026-10-31T12:00:00Z",
            "committed_at": "2026-10-31T12:00:00Z",
            "created_by": "phase7-unowned",
        },
    }
    sidecar["entities"]["site"]["links"].update(protected_links)
    sidecar_path.write_text(yaml.safe_dump(sidecar, sort_keys=False), encoding="utf-8")

    await _decision(authorized_client, path, "accepted", "rejected")
    removed = await _export(authorized_client, path)
    assert removed["removed"] == 1
    links = _sidecar(directory, name)["entities"]["site"]["links"]
    assert set(links) == set(protected_links)
    for key, expected in protected_links.items():
        assert links[key]["target_id"] == expected["target_id"]
        assert links[key]["source"] == expected["source"]
        assert links[key].get("owner") is None

    await _decision(authorized_client, path, "accepted", "accepted", site_id, uri)
    monkeypatch.setattr(settings, "RECONCILIATION_SERVICE_URL", "http://127.0.0.1:1")
    unavailable = await _export(authorized_client, path)
    assert unavailable["outcomes"] == [
        {
            "local_key_value": "accepted",
            "outcome": "unverified",
            "reason": "The Authority Service is unavailable; this link was exported without verification. "
            "Retry export when it is available.",
        }
    ]
    unverified_sidecar = _sidecar(directory, name)["entities"]["site"]
    assert unverified_sidecar["links"]["accepted"]["verified_at"] is None
    assert unverified_sidecar["links"]["accepted"]["owner"] == {"entity_name": "site", "target_field": "site_name"}
    assert set(unverified_sidecar["links"]) == {"accepted", *protected_links}

    monkeypatch.setattr(settings, "RECONCILIATION_SERVICE_URL", live_service_url)
    retried = await _export(authorized_client, path)
    assert retried["outcomes"] == [{"local_key_value": "accepted", "outcome": "verified", "reason": None}]
    verified_sidecar = _sidecar(directory, name)["entities"]["site"]
    assert verified_sidecar["links"]["accepted"]["verified_at"]
    for key, expected in protected_links.items():
        assert verified_sidecar["links"][key]["target_id"] == expected["target_id"]
        assert verified_sidecar["links"][key]["source"] == expected["source"]
        assert verified_sidecar["links"][key].get("owner") is None


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
