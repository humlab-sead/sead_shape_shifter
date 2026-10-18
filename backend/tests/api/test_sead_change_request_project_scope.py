"""Tests for the authorized, provider-scoped SEAD Change Request path.

These tests drive the real HTTP route and the real ingester preparation flow. Only the
SIMS client and the target-database checker are replaced, so a failed check shows whether
an external effect happened.
"""

import json
from types import SimpleNamespace
from typing import Any
from uuid import UUID

import pandas as pd
import pytest
from httpx import AsyncClient

from backend.app.api.v1.endpoints import ingesters as ingester_endpoints
from backend.app.core.config import settings
from backend.app.models.sims import CapabilitiesResponse, EntityCapabilityResponse
from backend.app.services import ingester_runtime, project_service, yaml_service
from backend.app.services.data_provider_service import DataProviderService
from backend.app.services.ingester_service import IngesterService
from backend.app.services.project_data_provider_service import ProjectDataProviderService
from backend.app.services.project_provider_binding_service import ProjectProviderBindingService

# pylint: disable=redefined-outer-name, unused-argument

VALIDATE_PATH = "/api/v1/ingesters/sead_change_request/validate"
INGEST_PATH = "/api/v1/ingesters/sead_change_request/ingest"

TARGET_MODEL: dict[str, Any] = {
    "model": {"name": "Scope Test Model", "version": "0.1.0"},
    "entities": {
        "data_provider": {"role": "lookup", "public_id": "data_provider_id", "target_table": "tbl_data_providers"},
        "submission_state": {"role": "classifier", "public_id": "submission_state_id", "target_table": "tbl_submission_states"},
        "submission": {
            "role": "fact",
            "identity_tracking": "tracked",
            "reconciliation": "allocate",
            "public_id": "submission_id",
            "target_table": "tbl_submissions",
            "foreign_keys": [{"entity": "submission_state"}, {"entity": "data_provider"}],
        },
        "site": {"role": "fact", "public_id": "site_id", "target_table": "tbl_sites"},
    },
    "constraints": [],
}


class RecordingSimsClient:
    """Record SIMS resolve requests instead of calling the service."""

    instances: list["RecordingSimsClient"] = []

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = base_url
        self.scope_names: list[str] = []
        self.run_ids: list[str | None] = []
        self.associated_change_requests: list[tuple[str, str]] = []
        RecordingSimsClient.instances.append(self)

    async def resolve(self, request: Any) -> Any:
        """Record the request scope and run ID and return one outcome per row."""
        self.scope_names.append(request.scope_name)
        self.run_ids.append(request.run_id)
        return SimpleNamespace(
            binding_set=SimpleNamespace(
                binding_set_uuid=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
                lifecycle_state=SimpleNamespace(value="confirmed"),
            ),
            outcomes=[
                SimpleNamespace(target_id=500 + index, tracked_identity_uuid=None) for index, _ in enumerate(request.requests, start=1)
            ],
        )

    async def associate_change_request(self, binding_set_uuid: str, change_request_name: str) -> None:  # pragma: no cover
        self.associated_change_requests.append((binding_set_uuid, change_request_name))

    async def get_capabilities(self) -> CapabilitiesResponse:
        """Return a permissive capability set for the entities used by these tests."""
        return CapabilitiesResponse(
            version="1.0",
            entities=[
                EntityCapabilityResponse(
                    entity_type=entity_type,
                    entity_subtype="shared_metadata",
                    bind_existing=True,
                    allocate_new=True,
                    auto_confirm=True,
                    accept_uuid=False,
                )
                for entity_type in ("site", "submission", "data_provider", "submission_state")
            ],
        )


class RecordingCollisionChecker:
    """Record target-database provider checks instead of connecting."""

    instances: list["RecordingCollisionChecker"] = []

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.row_exists_calls: list[tuple[str, dict[str, object]]] = []
        self.matched = True
        RecordingCollisionChecker.instances.append(self)

    async def row_exists(self, table_name: str, filters: dict[str, object]) -> bool:
        self.row_exists_calls.append((table_name, dict(filters)))
        return self.matched

    async def target_id_exists(self, table_name: str, public_id_column: str, target_id: int) -> bool:
        return False

    async def reserve_target_id(self, table_name: str, public_id_column: str) -> int | None:
        return None


@pytest.fixture(autouse=True)
def recording_clients(monkeypatch) -> None:
    """Replace the SIMS client and target-database checker for every test."""
    RecordingSimsClient.instances = []
    RecordingCollisionChecker.instances = []
    monkeypatch.setattr(ingester_runtime, "SimsClient", RecordingSimsClient)
    monkeypatch.setattr(ingester_runtime, "SeadChangeRequestTargetCollisionChecker", RecordingCollisionChecker)


@pytest.fixture(autouse=True)
def reset_services() -> None:
    """Reset cached services so each test reads the isolated project and registry paths."""
    project_service._project_service = None
    yaml_service._yaml_service = None
    yield
    project_service._project_service = None
    yaml_service._yaml_service = None


@pytest.fixture(autouse=True)
def ingester_service(monkeypatch) -> IngesterService:
    """Build an ingester service that reads the current provider registry."""
    provider_service = DataProviderService(settings.global_data_provider_dir)
    binding_service = ProjectProviderBindingService(provider_service)
    service = IngesterService(ProjectDataProviderService(provider_service, binding_service))
    monkeypatch.setattr(ingester_endpoints, "get_ingester_service", lambda: service)
    return service


def _project_payload(name: str, *, provider_id: int = 51, provider_code: str = "test-provider") -> dict[str, Any]:
    """Build a project creation payload with one fixed provider row."""
    return {
        "name": name,
        "data_provider_code": provider_code,
        "provider_schema": "schema-one",
        "entities": {
            "data_provider": {
                "type": "fixed",
                "public_id": "data_provider_id",
                "keys": ["data_provider_code"],
                "columns": ["data_provider_id", "data_provider_code"],
                "values": [[provider_id, provider_code]],
            },
            "site": {
                "type": "entity",
                "public_id": "site_id",
                "keys": ["site_code"],
                "columns": ["site_code"],
            },
        },
    }


def _write_source_workbook(tmp_path, name: str = "submission.xlsx"):
    """Write a minimal workbook with one site sheet."""
    path = tmp_path / name
    with pd.ExcelWriter(path) as writer:
        pd.DataFrame({"site_id": [None], "site_code": ["S1"]}).to_excel(writer, sheet_name="site", index=False)
    return path


def _validate_payload(project_name: str, source_path, *, nested_project_name: str | None = None) -> dict[str, Any]:
    """Build one validate request body."""
    return {
        "source": str(source_path),
        "project_name": project_name,
        "config": {
            "target_model": TARGET_MODEL,
            "database": {"host": "localhost", "port": 5432, "dbname": "test_db", "user": "test_user"},
        },
        "submission_context": {
            "submission_name": "scope_delivery_1",
            "project_name": nested_project_name or project_name,
            "timestamp": "2026-10-18T09:00:00",
            "datatype": "mal",
            "identifier": "SCOPE_DELIVERY",
        },
    }


def _ingest_payload(
    project_name: str,
    source_path,
    output_folder,
    *,
    deploy_strategy: str = "inline_insert",
    staging_target_schema: str | None = "public",
) -> dict[str, Any]:
    """Build one Change Request ingest body with an isolated artifact directory."""
    payload = _validate_payload(project_name, source_path)
    payload.update(
        {
            "submission_name": "scope_delivery_1",
            "data_types": "mal",
            "output_folder": str(output_folder),
            "deploy_strategy": deploy_strategy,
        }
    )
    if deploy_strategy == "inline_staging" and staging_target_schema is not None:
        payload["config"]["staging_target_schema"] = staging_target_schema
    return payload


async def _create_project(client: AsyncClient, payload: dict[str, Any]) -> None:
    response = await client.post("/api/v1/projects", json=payload)
    assert response.status_code == 201, response.text


@pytest.mark.asyncio
async def test_validate_uses_the_authorized_project_scope_and_provider_row(tmp_path, monkeypatch, authorized_client):
    """The saved pair selects the SIMS scope and the fixed row supplies the provider ID."""
    monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
    await _create_project(authorized_client, _project_payload("scope_alpha"))
    source_path = _write_source_workbook(tmp_path)

    response = await authorized_client.post(VALIDATE_PATH, json=_validate_payload("scope_alpha", source_path))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["is_valid"] is True, body["errors"]

    sims_client = RecordingSimsClient.instances[-1]
    assert sims_client.scope_names == ["provider://test-provider/schema-one"]
    assert sims_client.run_ids and sims_client.run_ids[0]

    collision_checker = RecordingCollisionChecker.instances[-1]
    assert collision_checker.row_exists_calls == [("tbl_data_providers", {"data_provider_id": 51, "data_provider_code": "test-provider"})]


@pytest.mark.asyncio
async def test_nested_project_name_cannot_switch_the_scope(tmp_path, monkeypatch, authorized_client):
    """A nested submission context naming another project is rejected before SIMS runs."""
    monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
    await _create_project(authorized_client, _project_payload("scope_alpha"))
    await _create_project(authorized_client, _project_payload("scope_beta"))
    source_path = _write_source_workbook(tmp_path)

    response = await authorized_client.post(
        VALIDATE_PATH,
        json=_validate_payload("scope_alpha", source_path, nested_project_name="scope_beta"),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["is_valid"] is False
    assert any("conflicts with the authorized project" in error for error in body["errors"])
    assert all(not client.scope_names for client in RecordingSimsClient.instances)
    assert all(not checker.row_exists_calls for checker in RecordingCollisionChecker.instances)


@pytest.mark.asyncio
async def test_unregistered_saved_pair_fails_before_any_side_effect(tmp_path, monkeypatch, authorized_client):
    """An out-of-band pair change fails closed before SIMS, target, or file work."""
    monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
    await _create_project(authorized_client, _project_payload("scope_gamma"))
    project_file = tmp_path / "scope_gamma" / "shapeshifter.yml"
    project_file.write_text(
        project_file.read_text(encoding="utf-8").replace("provider_schema: schema-one", "provider_schema: ghost-schema"),
        encoding="utf-8",
    )
    source_path = _write_source_workbook(tmp_path)

    response = await authorized_client.post(VALIDATE_PATH, json=_validate_payload("scope_gamma", source_path))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["is_valid"] is False
    assert any("not registered" in error for error in body["errors"])
    assert all(not client.scope_names for client in RecordingSimsClient.instances)
    assert all(not checker.row_exists_calls for checker in RecordingCollisionChecker.instances)


@pytest.mark.asyncio
async def test_unknown_project_is_rejected_without_metadata(tmp_path, monkeypatch, authorized_client):
    """A project locator the caller cannot use returns a concealed 404."""
    monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
    source_path = _write_source_workbook(tmp_path)

    response = await authorized_client.post(VALIDATE_PATH, json=_validate_payload("missing_project", source_path))

    assert response.status_code == 404
    assert "missing_project" not in response.text
    assert all(not client.scope_names for client in RecordingSimsClient.instances)


@pytest.mark.parametrize("operation", ["validate", "ingest"])
@pytest.mark.parametrize("locator", [None, "inaccessible_project"])
@pytest.mark.asyncio
async def test_change_request_routes_require_a_top_level_authorized_project(
    tmp_path, monkeypatch, authorized_client, operation: str, locator: str | None
):
    """Nested project, provider, and scope values cannot authorize either route."""
    monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
    source_path = _write_source_workbook(tmp_path)
    output_folder = tmp_path / "rejected-output"
    payload = (
        _validate_payload(locator or "scope_alpha", source_path)
        if operation == "validate"
        else _ingest_payload(locator or "scope_alpha", source_path, output_folder)
    )
    if locator is None:
        payload.pop("project_name")
    else:
        payload["project_name"] = locator
    payload["submission_context"].update(
        {
            "project_name": "scope_alpha",
            "data_provider_code": "test-provider",
            "scope_name": "provider://test-provider/schema-one",
        }
    )
    payload["config"]["sims_scope_name"] = "provider://spoofed/schema"
    payload["config"]["data_provider_code"] = "test-provider"
    path = VALIDATE_PATH if operation == "validate" else INGEST_PATH

    response = await authorized_client.post(path, json=payload)

    assert response.status_code == 404
    assert "scope_alpha" not in response.text
    assert all(not client.scope_names for client in RecordingSimsClient.instances)
    assert all(not checker.row_exists_calls for checker in RecordingCollisionChecker.instances)
    assert not output_folder.exists()


@pytest.mark.parametrize("operation", ["validate", "ingest"])
@pytest.mark.parametrize("pair_state", ["missing", "unregistered"])
@pytest.mark.asyncio
async def test_unresolved_saved_pair_fails_both_routes_before_side_effects(
    tmp_path, monkeypatch, authorized_client, operation: str, pair_state: str
):
    """An incomplete or unregistered saved pair cannot reach external services or artifact writing."""
    monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
    await _create_project(authorized_client, _project_payload("scope_gamma"))
    project_file = tmp_path / "scope_gamma" / "shapeshifter.yml"
    project_yaml = project_file.read_text(encoding="utf-8")
    if pair_state == "missing":
        project_yaml = project_yaml.replace("  provider_schema: schema-one\n", "", 1)
    else:
        project_yaml = project_yaml.replace("provider_schema: schema-one", "provider_schema: ghost-schema", 1)
    project_file.write_text(project_yaml, encoding="utf-8")

    source_path = _write_source_workbook(tmp_path)
    output_folder = tmp_path / "unresolved-output"
    payload = (
        _validate_payload("scope_gamma", source_path)
        if operation == "validate"
        else _ingest_payload("scope_gamma", source_path, output_folder)
    )
    path = VALIDATE_PATH if operation == "validate" else INGEST_PATH

    response = await authorized_client.post(path, json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    if operation == "validate":
        assert body["is_valid"] is False
        assert body["errors"]
    else:
        assert body["success"] is False
        assert body["error_details"]
    assert all(not client.scope_names for client in RecordingSimsClient.instances)
    assert all(not checker.row_exists_calls for checker in RecordingCollisionChecker.instances)
    assert not output_folder.exists()


@pytest.mark.parametrize("deploy_strategy", ["inline_insert", "copy_csv", "inline_staging"])
@pytest.mark.asyncio
async def test_ingest_response_artifact_manifest_and_sims_request_share_scope_and_run(
    tmp_path, monkeypatch, authorized_client, deploy_strategy: str
):
    """All supported strategies write the same effective scope and run ID to every output."""
    monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
    monkeypatch.chdir(tmp_path)
    await _create_project(authorized_client, _project_payload(f"project_{deploy_strategy}"))
    source_path = _write_source_workbook(tmp_path, f"{deploy_strategy}.xlsx")
    output_folder = tmp_path / f"output_{deploy_strategy}"
    payload = _ingest_payload(
        f"project_{deploy_strategy}",
        source_path,
        output_folder,
        deploy_strategy=deploy_strategy,
    )

    response = await authorized_client.post(INGEST_PATH, json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True, body.get("error_details")
    scope_name = body["scope_name"]
    run_id = body["run_id"]
    assert scope_name == "provider://test-provider/schema-one"
    assert run_id

    artifact = body["deploy_artifact"]
    assert artifact["metadata"]["scope_name"] == scope_name
    assert artifact["metadata"]["run_id"] == run_id
    assert artifact["metadata_artifact"]["scope_name"] == scope_name
    assert artifact["metadata_artifact"]["run_id"] == run_id

    manifest_paths = list((tmp_path / "output").rglob("manifest.json"))
    assert len(manifest_paths) == 1
    manifest = json.loads(manifest_paths[0].read_text(encoding="utf-8"))
    assert manifest["scope_name"] == scope_name
    assert manifest["run_id"] == run_id

    sims_client = RecordingSimsClient.instances[-1]
    assert sims_client.scope_names
    assert set(sims_client.scope_names) == {scope_name}
    assert sims_client.run_ids
    assert set(sims_client.run_ids) == {run_id}


@pytest.mark.asyncio
async def test_inline_staging_without_schema_fails_without_writing_artifact(tmp_path, monkeypatch, authorized_client):
    """A missing staging schema fails before an artifact bundle is written."""
    monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
    await _create_project(authorized_client, _project_payload("scope_staging"))
    source_path = _write_source_workbook(tmp_path)
    output_folder = tmp_path / "missing-staging-schema"
    payload = _ingest_payload(
        "scope_staging",
        source_path,
        output_folder,
        deploy_strategy="inline_staging",
        staging_target_schema=None,
    )

    response = await authorized_client.post(INGEST_PATH, json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is False
    assert body["deploy_artifact"] is None
    assert "staging_target_schema" in (body["error_details"] or "")
    assert not output_folder.exists()
