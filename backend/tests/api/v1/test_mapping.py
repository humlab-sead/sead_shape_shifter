"""Tests for mapping sidecar CRUD API endpoints."""

from pathlib import Path

import yaml
from httpx import ASGITransport, AsyncClient

from backend.app.core.config import settings
from backend.app.main import app
from backend.app.services import project_service, validation_service, yaml_service

# pylint: disable=redefined-outer-name, unused-argument


# Fixed entity used by the tests. Projects are created through the API so the
# backend registers them as authorization resources (see authorized_client).
_SITE_ENTITY = {
    "type": "fixed",
    "public_id": "site_id",
    "keys": ["site_code"],
    "columns": ["system_id", "site_id", "site_code"],
    "values": [[1, 10, "A"], [2, 20, "B"]],
}


async def _create_project(client) -> None:
    """Create the test project through the API (registers it as an authorized resource)."""
    response = await client.post(
        "/api/v1/projects",
        json={
            "name": "test_project",
            "data_provider_code": "test-provider",
            "provider_schema": "schema-one",
            "entities": {"site": _SITE_ENTITY},
        },
    )
    assert response.status_code == 201, response.text


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


class TestMappingApi:
    """CRUD tests for mapping sidecar endpoints."""

    def setup_method(self) -> None:
        _reset_singletons()

    def teardown_method(self) -> None:
        _reset_singletons()

    async def test_get_entity_mapping_returns_default_metadata_when_sidecar_missing(
        self, tmp_path: Path, monkeypatch, authorized_client
    ) -> None:
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        await _create_project(authorized_client)

        response = await authorized_client.get("/api/v1/projects/test_project/mapping/site")

        assert response.status_code == 200
        body = response.json()
        assert body["entity_name"] == "site"
        assert body["local_key"] == "site_code"
        assert body["public_id"] == "site_id"
        assert body["links"] == {}

    async def test_get_entity_mapping_returns_404_for_missing_entity(self, tmp_path: Path, monkeypatch, authorized_client) -> None:
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        await _create_project(authorized_client)

        response = await authorized_client.get("/api/v1/projects/test_project/mapping/missing")

        assert response.status_code == 404
        body = response.json()["detail"]
        assert body["message"] == "Entity 'missing' not found"
        assert body["context"]["resource_type"] == "entity"
        assert body["context"]["resource_id"] == "missing"

    async def test_get_single_mapping_link_returns_saved_link(self, tmp_path: Path, monkeypatch, authorized_client) -> None:
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        await _create_project(authorized_client)
        _write_mapping_sidecar(tmp_path)

        response = await authorized_client.get("/api/v1/projects/test_project/mapping/site/A")

        assert response.status_code == 200
        body = response.json()
        assert body["entity_name"] == "site"
        assert body["local_key_value"] == "A"
        assert body["link"]["target_id"] == 10
        assert body["link"]["source"] == "manual"

    async def test_get_single_mapping_link_returns_404_for_missing_entity(self, tmp_path: Path, monkeypatch, authorized_client) -> None:
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        await _create_project(authorized_client)
        _write_mapping_sidecar(tmp_path)

        response = await authorized_client.get("/api/v1/projects/test_project/mapping/missing/A")

        assert response.status_code == 404
        body = response.json()["detail"]
        assert body["message"] == "Entity 'missing' not found"
        assert body["context"]["resource_type"] == "entity"
        assert body["context"]["resource_id"] == "missing"

    async def test_put_mapping_link_creates_or_updates_manual_link(self, tmp_path: Path, monkeypatch, authorized_client) -> None:
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        await _create_project(authorized_client)

        response = await authorized_client.put(
            "/api/v1/projects/test_project/mapping/site/B",
            json={"target_id": 20, "confidence": 0.99, "notes": "Manual override"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["local_key_value"] == "B"
        assert body["link"]["target_id"] == 20
        assert body["link"]["source"] == "manual"
        assert body["link"]["confidence"] == 0.99
        assert body["link"]["notes"] == "Manual override"

        with open(tmp_path / "test_project" / "test_project-mapping.yml", "r", encoding="utf-8") as handle:
            sidecar = yaml.safe_load(handle)
        assert sidecar["entities"]["site"]["links"]["B"]["target_id"] == 20

    async def test_put_mapping_link_returns_404_for_missing_entity(self, tmp_path: Path, monkeypatch, authorized_client) -> None:
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        await _create_project(authorized_client)

        response = await authorized_client.put(
            "/api/v1/projects/test_project/mapping/missing/B",
            json={"target_id": 20, "confidence": 0.99, "notes": "Manual override"},
        )

        assert response.status_code == 404
        body = response.json()["detail"]
        assert body["message"] == "Entity 'missing' not found"
        assert body["context"]["resource_type"] == "entity"
        assert body["context"]["resource_id"] == "missing"

    async def test_delete_mapping_link_removes_saved_link(self, tmp_path: Path, monkeypatch, authorized_client) -> None:
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        await _create_project(authorized_client)
        _write_mapping_sidecar(tmp_path)

        response = await authorized_client.delete("/api/v1/projects/test_project/mapping/site/A")

        assert response.status_code == 200
        assert response.json() == {"entity_name": "site", "local_key_value": "A", "deleted": True}

        with open(tmp_path / "test_project" / "test_project-mapping.yml", "r", encoding="utf-8") as handle:
            sidecar = yaml.safe_load(handle)
        assert sidecar["entities"]["site"]["links"] == {}

    async def test_delete_mapping_link_returns_404_for_missing_entity(self, tmp_path: Path, monkeypatch, authorized_client) -> None:
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        await _create_project(authorized_client)

        response = await authorized_client.delete("/api/v1/projects/test_project/mapping/missing/A")

        assert response.status_code == 404
        body = response.json()["detail"]
        assert body["message"] == "Entity 'missing' not found"
        assert body["context"]["resource_type"] == "entity"
        assert body["context"]["resource_id"] == "missing"


# ---------------------------------------------------------------------------
# Fixed-entity pending mapping retry
# ---------------------------------------------------------------------------

_RETRY_SITE_ENTITY = {
    "type": "fixed",
    "public_id": "site_id",
    "keys": ["site_code"],
    "columns": ["system_id", "site_id", "site_code"],
    "values": [[1, 11, "A"], [2, 20, "B"]],
}


async def _create_retry_project(client, entity: dict | None = None) -> None:
    response = await client.post(
        "/api/v1/projects",
        json={
            "name": "test_project",
            "data_provider_code": "test-provider",
            "provider_schema": "schema-one",
            "entities": {"site": entity or _RETRY_SITE_ENTITY},
        },
    )
    assert response.status_code == 201, response.text


def _write_bare_sidecar(tmp_path: Path, links: dict | None = None) -> None:
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
                "links": links or {},
            }
        },
    }
    with open(tmp_path / "test_project" / "test_project-mapping.yml", "w", encoding="utf-8") as handle:
        yaml.dump(sidecar, handle, sort_keys=False)


def _pending_payload(**overrides) -> dict:
    payload = {
        "status": "pending",
        "rows_saved": True,
        "project": "test_project",
        "entity": "site",
        "storage_kind": "inline",
        "local_key": "site_code",
        "public_id": "site_id",
        "operations": [
            {
                "op": "upsert",
                "key": "A",
                "target_id": 11,
                "expected_row_present": True,
                "expected_saved_id": 11,
                "prior_link": None,
                "row_index": 0,
            }
        ],
        "entry": None,
        "expected_row_version": "rows-v1",
        "expected_sidecar_version": "sidecar-v1",
    }
    payload.update(overrides)
    return payload


def _retry_url(entity: str = "site") -> str:
    return f"/api/v1/projects/test_project/mapping/retry-fixed-entity/{entity}"


class TestRetryFixedEntityMapping:
    """Retry endpoint behavior for pending fixed-entity mapping changes."""

    def setup_method(self) -> None:
        _reset_singletons()

    def teardown_method(self) -> None:
        _reset_singletons()

    async def test_retry_applies_pending_upsert(self, tmp_path: Path, monkeypatch, authorized_client) -> None:
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        await _create_retry_project(authorized_client)
        _write_bare_sidecar(tmp_path)

        response = await authorized_client.patch(_retry_url(), json=_pending_payload())

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["status"] == "applied"
        assert body["changed"] is True
        with open(tmp_path / "test_project" / "test_project-mapping.yml", encoding="utf-8") as handle:
            sidecar = yaml.safe_load(handle)
        assert sidecar["entities"]["site"]["links"]["A"]["target_id"] == 11
        assert sidecar["entities"]["site"]["links"]["A"]["source"] == "manual"

    async def test_repeated_retry_is_noop(self, tmp_path: Path, monkeypatch, authorized_client) -> None:
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        await _create_retry_project(authorized_client)
        _write_bare_sidecar(tmp_path)

        first = await authorized_client.patch(_retry_url(), json=_pending_payload())
        sidecar_path = tmp_path / "test_project" / "test_project-mapping.yml"
        after_first = sidecar_path.read_bytes()
        second = await authorized_client.patch(_retry_url(), json=_pending_payload())

        assert first.json()["status"] == "applied"
        assert second.status_code == 200
        assert second.json()["status"] == "noop"
        assert second.json()["changed"] is False
        assert sidecar_path.read_bytes() == after_first

    async def test_unrelated_edits_do_not_block_retry(self, tmp_path: Path, monkeypatch, authorized_client) -> None:
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        await _create_retry_project(authorized_client)
        _write_bare_sidecar(
            tmp_path,
            links={
                "B": {
                    "target_id": 99,
                    "source": "import",
                    "created_at": "2026-06-15T00:00:00Z",
                    "committed_at": "2026-06-15T00:00:00Z",
                    "created_by": "importer",
                }
            },
        )

        response = await authorized_client.patch(_retry_url(), json=_pending_payload())

        assert response.status_code == 200
        with open(tmp_path / "test_project" / "test_project-mapping.yml", encoding="utf-8") as handle:
            sidecar = yaml.safe_load(handle)
        assert sidecar["entities"]["site"]["links"]["A"]["target_id"] == 11
        assert sidecar["entities"]["site"]["links"]["B"]["target_id"] == 99
        assert sidecar["entities"]["site"]["links"]["B"]["source"] == "import"

    async def test_changed_affected_key_returns_409_with_keys(self, tmp_path: Path, monkeypatch, authorized_client) -> None:
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        changed_entity = dict(_RETRY_SITE_ENTITY)
        changed_entity["values"] = [[1, 99, "A"], [2, 20, "B"]]
        await _create_retry_project(authorized_client, changed_entity)
        _write_bare_sidecar(tmp_path)

        response = await authorized_client.patch(_retry_url(), json=_pending_payload())

        assert response.status_code == 409
        body = response.json()["detail"]
        assert body["context"]["changed_keys"] == ["A"]
        with open(tmp_path / "test_project" / "test_project-mapping.yml", encoding="utf-8") as handle:
            sidecar = yaml.safe_load(handle)
        assert sidecar["entities"]["site"]["links"] == {}

    async def test_body_path_mismatch_returns_422(self, tmp_path: Path, monkeypatch, authorized_client) -> None:
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        await _create_retry_project(authorized_client)
        _write_bare_sidecar(tmp_path)

        response = await authorized_client.patch(_retry_url("other"), json=_pending_payload())

        assert response.status_code == 422

    async def test_malformed_payload_returns_422(self, tmp_path: Path, monkeypatch, authorized_client) -> None:
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        await _create_retry_project(authorized_client)
        _write_bare_sidecar(tmp_path)

        payload = _pending_payload()
        payload["operations"] = [{"op": "upsert", "key": "A", "expected_row_present": True, "expected_saved_id": 11}]
        response = await authorized_client.patch(_retry_url(), json=payload)

        assert response.status_code == 422

    async def test_non_fixed_entity_returns_error_without_writing(self, tmp_path: Path, monkeypatch, authorized_client) -> None:
        monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
        entity = {"type": "entity", "keys": ["site_code"], "columns": ["name"]}
        await _create_retry_project(authorized_client, entity)
        _write_bare_sidecar(tmp_path)

        response = await authorized_client.patch(_retry_url(), json=_pending_payload())

        assert response.status_code in (400, 409)
        with open(tmp_path / "test_project" / "test_project-mapping.yml", encoding="utf-8") as handle:
            sidecar = yaml.safe_load(handle)
        assert sidecar["entities"]["site"]["links"] == {}


async def test_retry_fixed_entity_mapping_requires_authentication(tmp_path: Path, monkeypatch) -> None:
    """The retry route rejects an unauthenticated request before touching any file."""
    monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)

    async def anonymous_app(scope, receive, send) -> None:
        await app(scope, receive, send)

    async with AsyncClient(transport=ASGITransport(app=anonymous_app), base_url="http://testserver") as client:
        response = await client.patch(_retry_url(), json=_pending_payload())

    assert response.status_code == 401
