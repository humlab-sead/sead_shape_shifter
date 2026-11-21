"""Route tests for authorized record selection during reconciliation review.

These cover the Phase 3 selection bridge: versioned capability discovery, bounded
ranked search, type-scoped exact-ID lookup, and complete-or-error browse lists.
The Authority Service is replaced by a controllable fake, so the tests assert the
request shapes, the adapted responses, and the distinguishable error codes without
contacting a service or writing target data.
"""

from pathlib import Path
from typing import Any

import httpx
import pytest
import yaml

from backend.app.api.v1.endpoints import reconciliation as reconciliation_endpoints
from backend.app.clients.reconciliation_client import (
    RecordSelectionInvalidRequestError,
    RecordSelectionNotFoundError,
    RecordSelectionProtocolError,
    RecordSelectionTooLargeError,
    RecordSelectionUnavailableError,
    RecordSelectionUnsupportedError,
)
from backend.app.core.config import settings
from backend.app.main import app
from backend.app.models.reconciliation import (
    ReconciliationCandidate,
    ReconciliationRecord,
    RecordDisplayFieldDescriptor,
    RecordFieldFilterDescriptor,
    RecordSelectionTypeCapabilities,
)
from backend.app.services import project_service, validation_service, yaml_service
from backend.app.services.reconciliation import ReconciliationService

ID_BASE = "https://w3id.org/sead/id/"
PROJECT = "selection"
CATALOG_PATH = ("shapeshifter.reconciliation.yml",)


def _reset_services() -> None:
    project_service._project_service = None
    validation_service._validation_service = None
    yaml_service._yaml_service = None


def _capabilities(**overrides: Any) -> RecordSelectionTypeCapabilities:
    payload: dict[str, Any] = {
        "type": "feature_type",
        "search_supported": True,
        "identifier_search_supported": True,
        "browse_supported": True,
        "details_supported": True,
        "export_verification_supported": True,
        "id_base": ID_BASE,
        "id_path": "feature_type",
        "browse_max_rows": 500,
        "browse_max_bytes": 1_048_576,
        "interactive_search_max_results": 25,
        "display_fields": [
            RecordDisplayFieldDescriptor(name="name", source="record", label="Name", value_type="string", display=True),
            RecordDisplayFieldDescriptor(name="target_id", source="record", label="ID", value_type="integer", display=True),
        ],
        "text_filter_fields": ["name"],
        "sort_fields": ["name", "target_id"],
        "field_filters": [
            RecordFieldFilterDescriptor(field="name", operator="contains_ci"),
            RecordFieldFilterDescriptor(field="target_id", operator="equals"),
        ],
    }
    payload.update(overrides)
    return RecordSelectionTypeCapabilities(**payload)


def _record(target_id: int, name: str = "Bronze Age", **overrides: Any) -> ReconciliationRecord:
    payload: dict[str, Any] = {
        "id": f"{ID_BASE}feature_type/{target_id}",
        "target_id": target_id,
        "type": "feature_type",
        "name": name,
        "fields": {},
    }
    payload.update(overrides)
    return ReconciliationRecord(**payload)


class FakeSelectionClient:
    """Controllable stand-in for the Authority Service selection calls."""

    def __init__(
        self,
        *,
        version: int = 1,
        types: list[RecordSelectionTypeCapabilities] | None = None,
        candidates: list[ReconciliationCandidate] | None = None,
        details: ReconciliationRecord | None = None,
        records: list[ReconciliationRecord] | None = None,
        completeness: str = "complete",
        failure: Exception | None = None,
        manifest: dict[str, Any] | None = None,
    ) -> None:
        self.version = version
        self.types = types if types is not None else [_capabilities()]
        self.candidates = candidates or []
        self.details = details
        self.records = records or []
        self.completeness = completeness
        self.failure = failure
        self.manifest = manifest
        self.capability_calls: list[bool] = []
        self.search_calls: list[tuple[str, str, int, dict[str, str] | None]] = []
        self.details_calls: list[tuple[str, int]] = []
        self.list_calls: list[str] = []

    def _raise_if_failed(self) -> None:
        if self.failure is not None:
            raise self.failure

    async def get_record_selection_capabilities(self, *, fresh: bool = False):
        self.capability_calls.append(fresh)
        self._raise_if_failed()
        return self.version, list(self.types)

    async def search_records(self, record_type: str, query: str, limit: int, context: dict[str, str] | None = None):
        self.search_calls.append((record_type, query, limit, context))
        self._raise_if_failed()
        return list(self.candidates)

    async def get_record_details(self, record_type: str, target_id: int):
        self.details_calls.append((record_type, target_id))
        self._raise_if_failed()
        if self.details is None:
            raise RecordSelectionNotFoundError("No record exists for the requested identifier.")
        return self.details

    async def list_records(self, record_type: str):
        self.list_calls.append(record_type)
        self._raise_if_failed()
        return list(self.records), self.completeness

    async def get_service_manifest(self, *, fresh: bool = False):  # pylint: disable=unused-argument
        if self.manifest is not None:
            return self.manifest
        raise AssertionError("The manifest should not be requested for this scenario")


def _default_manifest() -> dict[str, Any]:
    return {
        "defaultTypes": [{"id": "feature_type", "name": "Feature type"}],
        "reconciliation": {"supportedTypes": ["feature_type"]},
        "extend": {"property_settings": []},
    }


async def _create_project(client, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path)
    response = await client.post(
        "/api/v1/projects",
        json={
            "name": PROJECT,
            "data_provider_code": "test-provider",
            "provider_schema": "schema-one",
            "entities": {
                "site": {
                    "type": "fixed",
                    "public_id": "site_id",
                    "keys": ["site_code"],
                    "columns": ["system_id", "site_id", "site_code", "site_name"],
                    "values": [[1, None, "A", "Uppsala"], [2, None, "B", "Lund"]],
                }
            },
        },
    )
    assert response.status_code == 201, response.text


def _write_catalog(tmp_path, service_type: str | None = "feature_type") -> Path:
    remote: dict[str, Any] = {} if service_type is None else {"service_type": service_type}
    catalog = {
        "version": "3.0",
        "service_url": "http://localhost:8000",
        "entities": {"site": {"site_name": {"remote": remote, "mapping": []}}},
    }
    path = tmp_path / PROJECT / CATALOG_PATH[0]
    path.write_text(yaml.safe_dump(catalog, sort_keys=False), encoding="utf-8")
    return path


def _install_service(monkeypatch, fake_client, tmp_path) -> None:
    async def dependency() -> ReconciliationService:
        return ReconciliationService(config_dir=Path(tmp_path), reconciliation_client=fake_client)  # type: ignore[arg-type]

    monkeypatch.setitem(app.dependency_overrides, reconciliation_endpoints.get_reconciliation_service, dependency)


BASE = f"/api/v1/projects/{PROJECT}/reconciliation/site/site_name/selection"


class TestSelectionCapabilitiesRoute:
    """Capability discovery is versioned, fresh, and fixed to the stored type."""

    def setup_method(self) -> None:
        _reset_services()

    def teardown_method(self) -> None:
        _reset_services()

    async def test_returns_versioned_capabilities_for_the_configured_type(self, authorized_client, tmp_path, monkeypatch) -> None:
        await _create_project(authorized_client, tmp_path, monkeypatch)
        _write_catalog(tmp_path)
        fake = FakeSelectionClient(version=3)
        _install_service(monkeypatch, fake, tmp_path)

        response = await authorized_client.get(f"{BASE}/capabilities")

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["version"] == 3
        assert body["type"]["type"] == "feature_type"
        assert body["type"]["search_supported"] is True
        assert body["type"]["browse_max_rows"] == 500
        assert body["type"]["display_fields"][0]["name"] == "name"
        assert fake.capability_calls == [True]
        assert not fake.search_calls and not fake.list_calls

    async def test_reports_an_unadvertised_type_as_unsupported(self, authorized_client, tmp_path, monkeypatch) -> None:
        await _create_project(authorized_client, tmp_path, monkeypatch)
        _write_catalog(tmp_path)
        _install_service(monkeypatch, FakeSelectionClient(types=[_capabilities(type="country")]), tmp_path)

        response = await authorized_client.get(f"{BASE}/capabilities")

        assert response.status_code == 400, response.text
        assert response.json()["detail"]["error_code"] == "RECORD_SELECTION_UNSUPPORTED"

    async def test_reports_a_specification_without_a_service_type(self, authorized_client, tmp_path, monkeypatch) -> None:
        await _create_project(authorized_client, tmp_path, monkeypatch)
        _write_catalog(tmp_path, service_type=None)
        _install_service(monkeypatch, FakeSelectionClient(), tmp_path)

        response = await authorized_client.get(f"{BASE}/capabilities")

        assert response.status_code == 400, response.text
        assert response.json()["detail"]["error_code"] == "RECORD_SELECTION_UNSUPPORTED"

    @pytest.mark.parametrize(
        ("failure", "status_code", "error_code"),
        [
            (RecordSelectionProtocolError("bad payload"), 500, "RECORD_SELECTION_INVALID_RESPONSE"),
            (RecordSelectionUnavailableError("offline"), 503, "RECORD_SELECTION_UNAVAILABLE"),
            (RecordSelectionUnsupportedError("not enabled"), 400, "RECORD_SELECTION_UNSUPPORTED"),
        ],
    )
    async def test_maps_service_failures_to_distinct_error_codes(
        self, authorized_client, tmp_path, monkeypatch, failure, status_code, error_code
    ) -> None:
        await _create_project(authorized_client, tmp_path, monkeypatch)
        _write_catalog(tmp_path)
        _install_service(monkeypatch, FakeSelectionClient(failure=failure), tmp_path)

        response = await authorized_client.get(f"{BASE}/capabilities")

        assert response.status_code == status_code, response.text
        assert response.json()["detail"]["error_code"] == error_code

    async def test_requires_authentication(self, authorized_client, tmp_path, monkeypatch) -> None:
        await _create_project(authorized_client, tmp_path, monkeypatch)
        _write_catalog(tmp_path)
        _install_service(monkeypatch, FakeSelectionClient(), tmp_path)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as anonymous:
            response = await anonymous.get(f"{BASE}/capabilities")

        assert response.status_code == 401, response.text


class TestSelectionSearchRoute:
    """Search keeps ranked and exact lookups distinct and never falls back on bad syntax."""

    def setup_method(self) -> None:
        _reset_services()

    def teardown_method(self) -> None:
        _reset_services()

    async def test_ranked_search_adapts_candidates_and_applies_the_advertised_cap(self, authorized_client, tmp_path, monkeypatch) -> None:
        await _create_project(authorized_client, tmp_path, monkeypatch)
        _write_catalog(tmp_path)
        fake = FakeSelectionClient(
            candidates=[
                ReconciliationCandidate(id=f"{ID_BASE}feature_type/11", name="Bronze Age", score=91.5),
                ReconciliationCandidate(id=f"{ID_BASE}location/12", name="Wrong type", score=88.0),
            ]
        )
        _install_service(monkeypatch, fake, tmp_path)

        response = await authorized_client.post(f"{BASE}/search", json={"query": "bronze", "limit": 100})

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["mode"] == "ranked"
        assert [item["target_id"] for item in body["items"]] == [11]
        assert body["items"][0]["score"] == 91.5
        assert body["items"][0]["name"] == "Bronze Age"
        assert body["items"][0]["id"] == f"{ID_BASE}feature_type/11"
        assert fake.search_calls == [("feature_type", "bronze", 25, None)]
        assert not fake.details_calls

    async def test_search_without_a_limit_uses_the_advertised_maximum(self, authorized_client, tmp_path, monkeypatch) -> None:
        await _create_project(authorized_client, tmp_path, monkeypatch)
        _write_catalog(tmp_path)
        fake = FakeSelectionClient()
        _install_service(monkeypatch, fake, tmp_path)

        response = await authorized_client.post(f"{BASE}/search", json={"query": "bronze", "limit": 5})

        assert response.status_code == 200, response.text
        assert response.json()["items"] == []
        assert fake.search_calls == [("feature_type", "bronze", 5, None)]

    async def test_declared_context_is_forwarded_as_a_ranking_hint(self, authorized_client, tmp_path, monkeypatch) -> None:
        await _create_project(authorized_client, tmp_path, monkeypatch)
        _write_catalog(tmp_path)
        manifest = _default_manifest()
        manifest["extend"]["property_settings"] = [{"name": "period", "entity_types": ["feature_type"]}]
        fake = FakeSelectionClient(manifest=manifest)
        _install_service(monkeypatch, fake, tmp_path)

        response = await authorized_client.post(
            f"{BASE}/search",
            json={"query": "bronze", "limit": 10, "context": {"period": "Bronze Age"}},
        )

        assert response.status_code == 200, response.text
        assert fake.search_calls == [("feature_type", "bronze", 10, {"period": "Bronze Age"})]

    async def test_undeclared_context_property_is_rejected(self, authorized_client, tmp_path, monkeypatch) -> None:
        await _create_project(authorized_client, tmp_path, monkeypatch)
        _write_catalog(tmp_path)
        fake = FakeSelectionClient(manifest=_default_manifest())
        _install_service(monkeypatch, fake, tmp_path)

        response = await authorized_client.post(
            f"{BASE}/search",
            json={"query": "bronze", "context": {"period": "Bronze Age"}},
        )

        assert response.status_code == 400, response.text
        assert not fake.search_calls

    async def test_exact_identifier_lookup_returns_one_typed_record(self, authorized_client, tmp_path, monkeypatch) -> None:
        await _create_project(authorized_client, tmp_path, monkeypatch)
        _write_catalog(tmp_path)
        fake = FakeSelectionClient(details=_record(42, "Exact record"))
        _install_service(monkeypatch, fake, tmp_path)

        response = await authorized_client.post(f"{BASE}/search", json={"query": "id: 42"})

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["mode"] == "exact"
        assert [item["target_id"] for item in body["items"]] == [42]
        assert fake.details_calls == [("feature_type", 42)]
        assert not fake.search_calls

    async def test_unknown_identifier_returns_no_record(self, authorized_client, tmp_path, monkeypatch) -> None:
        await _create_project(authorized_client, tmp_path, monkeypatch)
        _write_catalog(tmp_path)
        fake = FakeSelectionClient(details=None)
        _install_service(monkeypatch, fake, tmp_path)

        response = await authorized_client.post(f"{BASE}/search", json={"query": "id: 987654"})

        assert response.status_code == 200, response.text
        assert response.json() == {"mode": "exact", "items": []}
        assert not fake.search_calls

    @pytest.mark.parametrize("query", ["id:", "id: abc", "id: 1.5", "id: 0", "id: -3", "id: 9999999999999"])
    async def test_malformed_identifier_is_an_input_error_without_fuzzy_fallback(
        self, authorized_client, tmp_path, monkeypatch, query
    ) -> None:
        await _create_project(authorized_client, tmp_path, monkeypatch)
        _write_catalog(tmp_path)
        fake = FakeSelectionClient(details=_record(1))
        _install_service(monkeypatch, fake, tmp_path)

        response = await authorized_client.post(f"{BASE}/search", json={"query": query})

        assert response.status_code == 400, response.text
        assert response.json()["detail"]["error_code"] == "RECORD_SELECTION_INVALID_INPUT"
        assert not fake.search_calls
        assert not fake.details_calls

    async def test_non_ascii_digits_are_not_accepted_as_an_identifier(self, authorized_client, tmp_path, monkeypatch) -> None:
        await _create_project(authorized_client, tmp_path, monkeypatch)
        _write_catalog(tmp_path)
        fake = FakeSelectionClient(details=_record(1))
        _install_service(monkeypatch, fake, tmp_path)

        response = await authorized_client.post(f"{BASE}/search", json={"query": "id: ٤٢"})

        assert response.status_code == 400, response.text
        assert response.json()["detail"]["error_code"] == "RECORD_SELECTION_INVALID_INPUT"

    async def test_numeric_text_without_the_id_prefix_stays_ranked_search(self, authorized_client, tmp_path, monkeypatch) -> None:
        await _create_project(authorized_client, tmp_path, monkeypatch)
        _write_catalog(tmp_path)
        fake = FakeSelectionClient()
        _install_service(monkeypatch, fake, tmp_path)

        response = await authorized_client.post(f"{BASE}/search", json={"query": "42"})

        assert response.status_code == 200, response.text
        assert response.json()["mode"] == "ranked"
        assert fake.search_calls == [("feature_type", "42", 25, None)]

    @pytest.mark.parametrize(
        ("capability_overrides", "query"),
        [
            ({"search_supported": False}, "bronze"),
            ({"identifier_search_supported": False}, "id: 42"),
        ],
    )
    async def test_unadvertised_capabilities_are_rejected(
        self, authorized_client, tmp_path, monkeypatch, capability_overrides, query
    ) -> None:
        await _create_project(authorized_client, tmp_path, monkeypatch)
        _write_catalog(tmp_path)
        fake = FakeSelectionClient(types=[_capabilities(**capability_overrides)], details=_record(42))
        _install_service(monkeypatch, fake, tmp_path)

        response = await authorized_client.post(f"{BASE}/search", json={"query": query})

        assert response.status_code == 400, response.text
        assert response.json()["detail"]["error_code"] == "RECORD_SELECTION_UNSUPPORTED"
        assert not fake.search_calls and not fake.details_calls

    async def test_unavailable_service_is_distinct_from_an_empty_result(self, authorized_client, tmp_path, monkeypatch) -> None:
        await _create_project(authorized_client, tmp_path, monkeypatch)
        _write_catalog(tmp_path)
        fake = FakeSelectionClient(failure=RecordSelectionUnavailableError("offline"))
        _install_service(monkeypatch, fake, tmp_path)

        response = await authorized_client.post(f"{BASE}/search", json={"query": "bronze"})

        assert response.status_code == 503, response.text
        assert response.json()["detail"]["error_code"] == "RECORD_SELECTION_UNAVAILABLE"

    async def test_invalid_upstream_candidate_list_is_a_protocol_error(self, authorized_client, tmp_path, monkeypatch) -> None:
        await _create_project(authorized_client, tmp_path, monkeypatch)
        _write_catalog(tmp_path)
        fake = FakeSelectionClient(failure=RecordSelectionInvalidRequestError("bad request"))
        _install_service(monkeypatch, fake, tmp_path)

        response = await authorized_client.post(f"{BASE}/search", json={"query": "bronze"})

        assert response.status_code == 400, response.text
        assert response.json()["detail"]["error_code"] == "RECORD_SELECTION_INVALID_INPUT"

    async def test_search_does_not_write_the_catalog(self, authorized_client, tmp_path, monkeypatch) -> None:
        await _create_project(authorized_client, tmp_path, monkeypatch)
        path = _write_catalog(tmp_path)
        original = path.read_bytes()
        _install_service(monkeypatch, FakeSelectionClient(candidates=[]), tmp_path)

        assert (await authorized_client.post(f"{BASE}/search", json={"query": "bronze"})).status_code == 200
        assert path.read_bytes() == original


class TestSelectionBrowseRoute:
    """Browse returns a verified complete list or an explicit failure."""

    def setup_method(self) -> None:
        _reset_services()

    def teardown_method(self) -> None:
        _reset_services()

    async def test_returns_a_complete_list(self, authorized_client, tmp_path, monkeypatch) -> None:
        await _create_project(authorized_client, tmp_path, monkeypatch)
        _write_catalog(tmp_path)
        fake = FakeSelectionClient(records=[_record(1, "Bronze Age"), _record(2, "Iron Age")])
        _install_service(monkeypatch, fake, tmp_path)

        response = await authorized_client.get(f"{BASE}/browse")

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["completeness"] == "complete"
        assert [item["target_id"] for item in body["items"]] == [1, 2]
        assert all(item["score"] is None for item in body["items"])
        assert fake.list_calls == ["feature_type"]
        assert not fake.search_calls

    async def test_too_large_list_is_reported_without_partial_items(self, authorized_client, tmp_path, monkeypatch) -> None:
        await _create_project(authorized_client, tmp_path, monkeypatch)
        _write_catalog(tmp_path)
        fake = FakeSelectionClient(failure=RecordSelectionTooLargeError("The list exceeds the configured row limit."))
        _install_service(monkeypatch, fake, tmp_path)

        response = await authorized_client.get(f"{BASE}/browse")

        assert response.status_code == 409, response.text
        assert response.json()["detail"]["error_code"] == "RECORD_SELECTION_TOO_LARGE"
        assert "items" not in response.json()

    async def test_unadvertised_browse_is_rejected_before_the_list_request(self, authorized_client, tmp_path, monkeypatch) -> None:
        await _create_project(authorized_client, tmp_path, monkeypatch)
        _write_catalog(tmp_path)
        fake = FakeSelectionClient(types=[_capabilities(browse_supported=False)])
        _install_service(monkeypatch, fake, tmp_path)

        response = await authorized_client.get(f"{BASE}/browse")

        assert response.status_code == 400, response.text
        assert response.json()["detail"]["error_code"] == "RECORD_SELECTION_UNSUPPORTED"
        assert not fake.list_calls

    @pytest.mark.parametrize(
        "record",
        [
            _record(1, "Wrong type", type="country"),
            _record(1, "Mismatched URI", id=f"{ID_BASE}feature_type/2"),
            ReconciliationRecord(id=f"{ID_BASE}feature_type/1", target_id=None, type="feature_type", name="No ID"),
        ],
    )
    async def test_records_that_do_not_match_the_type_are_invalid_responses(self, authorized_client, tmp_path, monkeypatch, record) -> None:
        await _create_project(authorized_client, tmp_path, monkeypatch)
        _write_catalog(tmp_path)
        _install_service(monkeypatch, FakeSelectionClient(records=[record]), tmp_path)

        response = await authorized_client.get(f"{BASE}/browse")

        assert response.status_code == 500, response.text
        assert response.json()["detail"]["error_code"] == "RECORD_SELECTION_INVALID_RESPONSE"

    async def test_an_incomplete_list_is_not_accepted(self, authorized_client, tmp_path, monkeypatch) -> None:
        await _create_project(authorized_client, tmp_path, monkeypatch)
        _write_catalog(tmp_path)
        _install_service(monkeypatch, FakeSelectionClient(records=[_record(1)], completeness="partial"), tmp_path)

        response = await authorized_client.get(f"{BASE}/browse")

        assert response.status_code == 500, response.text
        assert response.json()["detail"]["error_code"] == "RECORD_SELECTION_INVALID_RESPONSE"

    async def test_browse_does_not_write_the_catalog(self, authorized_client, tmp_path, monkeypatch) -> None:
        await _create_project(authorized_client, tmp_path, monkeypatch)
        path = _write_catalog(tmp_path)
        original = path.read_bytes()
        _install_service(monkeypatch, FakeSelectionClient(records=[_record(1)]), tmp_path)

        assert (await authorized_client.get(f"{BASE}/browse")).status_code == 200
        assert path.read_bytes() == original
