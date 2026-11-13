"""Authorization and request-validation tests for the integrity troubleshooter API."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.api.v1.endpoints.integrity_troubleshooter import get_integrity_troubleshooter_service
from backend.app.core.config import settings
from backend.app.main import app
from backend.app.models.integrity_troubleshooter import (
    IntegrityTroubleshootKeys,
    IntegrityTroubleshootRelationship,
    IntegrityTroubleshootResponse,
    IntegrityTroubleshootRows,
    IntegrityTroubleshootValue,
    IntegrityTroubleshootValuePage,
    encode_key_token,
)
from backend.app.services import project_service
from backend.app.services.integrity_troubleshooter_service import IntegrityTroubleshooterContextResult

REQUEST = {
    "issue_type": "FK_DATA_INTEGRITY",
    "local_entity": "orders",
    "metadata": {"fk_index": 0, "fk_signature": "saved-signature", "orphan_count": 1},
}


@pytest.fixture(name="project_client")
async def _project_client(authorized_client: AsyncClient) -> AsyncIterator[AsyncClient]:
    """Create one authorized project for endpoint tests."""
    project_service._project_service = None
    response = await authorized_client.post(
        "/api/v1/projects",
        json={
            "name": "test_project",
            "data_provider_code": "test-provider",
            "provider_schema": "schema-one",
            "entities": {
                "orders": {
                    "type": "fixed",
                    "columns": ["order_code"],
                    "values": [["O1"]],
                }
            },
        },
    )
    assert response.status_code == 201, response.text
    yield authorized_client
    project_service._project_service = None


def install_service_override(monkeypatch, response: IntegrityTroubleshootResponse) -> Mock:
    """Return a service mock installed as the endpoint dependency."""
    service = Mock()
    service.inspect = AsyncMock(return_value=response)
    service.read_context = AsyncMock(return_value=IntegrityTroubleshooterContextResult(state="unavailable"))
    service.close_context = AsyncMock(return_value=True)
    monkeypatch.setitem(app.dependency_overrides, get_integrity_troubleshooter_service, lambda: service)
    return service


def response_model() -> IntegrityTroubleshootResponse:
    """Build one public response that exercises values and selected rows."""
    return IntegrityTroubleshootResponse(
        status="reproduced",
        reason="reproduced",
        message="Current data matches the warning.",
        relationship=IntegrityTroubleshootRelationship(
            local_entity="orders",
            remote_entity="customers",
            fk_index=0,
            join_type="left",
        ),
        configured_keys=IntegrityTroubleshootKeys(local_keys=["customer_code"], remote_keys=["code"]),
        recorded_orphan_count=1,
        current_orphan_count=1,
        values=IntegrityTroubleshootValuePage(
            distinct_value_count=1,
            values=[IntegrityTroubleshootValue(key_values=["A"], local_row_count=1, token=encode_key_token(("A",)))],
        ),
        selected=IntegrityTroubleshootRows(
            status="selected",
            key_values=["A"],
            total_row_count=1,
            columns=["customer_code", "order_code"],
            rows=[{"customer_code": "A", "order_code": "O1"}],
        ),
        context_id="context-one",
        expires_at=datetime.fromisoformat("2026-01-01T00:15:00Z").replace(tzinfo=UTC),
    )


def client_for_principal(principal_id: str | None) -> AsyncClient:
    """Create an ASGI client authenticated as the requested principal."""

    async def authenticated_app(scope, receive, send) -> None:
        if scope["type"] == "http" and principal_id is not None:
            scope.setdefault("state", {})["authenticated_user"] = principal_id
        await app(scope, receive, send)

    return AsyncClient(
        transport=ASGITransport(app=authenticated_app),
        base_url="http://testserver",
        headers={settings.TRUSTED_PROXY_AUTH_HEADER: principal_id or ""},
    )


@pytest.mark.asyncio
async def test_authorized_request_forwards_locator_and_request_fields(project_client, monkeypatch) -> None:
    expected = response_model()
    service = install_service_override(monkeypatch, expected)

    response = await project_client.post("/api/v1/projects/test_project/integrity-troubleshooter", json=REQUEST)

    assert response.status_code == 200, response.text
    assert response.json() == expected.model_dump(mode="json")
    service.inspect.assert_awaited_once_with(
        project_name="test_project",
        issue_type="FK_DATA_INTEGRITY",
        local_entity="orders",
        metadata=REQUEST["metadata"],
        selected_value_token=None,
        owner_principal_id="test-user",
        project_locator="test_project",
    )


@pytest.mark.asyncio
async def test_selected_value_request_forwards_the_token(project_client, monkeypatch) -> None:
    token = encode_key_token(("A",))
    body = {**REQUEST, "selected_value_token": token}
    service = install_service_override(monkeypatch, response_model())

    response = await project_client.post("/api/v1/projects/test_project/integrity-troubleshooter", json=body)

    assert response.status_code == 200, response.text
    service.inspect.assert_awaited_once_with(
        project_name="test_project",
        issue_type="FK_DATA_INTEGRITY",
        local_entity="orders",
        metadata=REQUEST["metadata"],
        selected_value_token=token,
        owner_principal_id="test-user",
        project_locator="test_project",
    )


@pytest.mark.asyncio
async def test_page_request_reads_the_owned_context_without_reopening_it(project_client, monkeypatch) -> None:
    expected = response_model()
    service = install_service_override(monkeypatch, expected)
    service.read_context = AsyncMock(return_value=IntegrityTroubleshooterContextResult(state="found", response=expected))
    token = encode_key_token(("A",))

    response = await project_client.post(
        "/api/v1/projects/test_project/integrity-troubleshooter/context-one/page",
        json={"selected_value_token": token},
    )

    assert response.status_code == 200, response.text
    assert response.json() == expected.model_dump(mode="json")
    service.read_context.assert_awaited_once_with(
        context_id="context-one",
        owner_principal_id="test-user",
        project_locator="test_project",
        selected_value_token=token,
    )
    service.inspect.assert_not_awaited()


@pytest.mark.asyncio
async def test_expired_page_context_returns_recoverable_gone_response(project_client, monkeypatch) -> None:
    service = install_service_override(monkeypatch, response_model())
    service.read_context = AsyncMock(return_value=IntegrityTroubleshooterContextResult(state="expired"))

    response = await project_client.post(
        "/api/v1/projects/test_project/integrity-troubleshooter/context-one/page",
        json={},
    )

    assert response.status_code == 410
    assert response.json()["detail"]["reason"] == "context_expired"


@pytest.mark.asyncio
async def test_unknown_page_context_returns_the_same_stale_response(project_client, monkeypatch) -> None:
    service = install_service_override(monkeypatch, response_model())

    response = await project_client.post(
        "/api/v1/projects/test_project/integrity-troubleshooter/context-one/page",
        json={},
    )

    assert response.status_code == 410
    assert response.json()["detail"]["reason"] == "context_expired"
    assert response.json()["detail"]["recoverable"] is True
    service.read_context.assert_awaited_once()


@pytest.mark.asyncio
async def test_close_releases_the_owned_context(project_client, monkeypatch) -> None:
    service = install_service_override(monkeypatch, response_model())

    response = await project_client.delete(
        "/api/v1/projects/test_project/integrity-troubleshooter/context-one",
    )

    assert response.status_code == 204
    service.close_context.assert_awaited_once_with(
        context_id="context-one",
        owner_principal_id="test-user",
        project_locator="test_project",
    )


@pytest.mark.parametrize(
    "body",
    [
        {key: value for key, value in REQUEST.items() if key != "issue_type"},
        {key: value for key, value in REQUEST.items() if key != "metadata"},
        {key: value for key, value in REQUEST.items() if key != "local_entity"},
        {**REQUEST, "selected_value_token": "not-a-valid-token"},
    ],
)
@pytest.mark.asyncio
async def test_invalid_request_shapes_return_422_without_running_service(project_client, monkeypatch, body: dict) -> None:
    service = install_service_override(monkeypatch, response_model())

    response = await project_client.post("/api/v1/projects/test_project/integrity-troubleshooter", json=body)

    assert response.status_code == 422
    service.inspect.assert_not_awaited()


@pytest.mark.parametrize(
    "body",
    [
        REQUEST,
        {**REQUEST, "selected_value_token": encode_key_token(("A",))},
    ],
)
@pytest.mark.asyncio
async def test_principal_without_project_read_gets_concealed_404(
    project_client,  # pylint: disable=unused-argument
    monkeypatch,
    body: dict,
) -> None:
    service = install_service_override(monkeypatch, response_model())

    async with client_for_principal("unrelated-user") as client:
        response = await client.post("/api/v1/projects/test_project/integrity-troubleshooter", json=body)

    assert response.status_code == 404
    assert response.json()["detail"] == "Resource not found"
    service.inspect.assert_not_awaited()


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("post", "/api/v1/projects/test_project/integrity-troubleshooter/context-one/page", {}),
        ("delete", "/api/v1/projects/test_project/integrity-troubleshooter/context-one", None),
    ],
)
@pytest.mark.asyncio
async def test_context_routes_require_project_read(
    project_client,  # pylint: disable=unused-argument
    monkeypatch,
    method: str,
    path: str,
    body: dict | None,
) -> None:
    service = install_service_override(monkeypatch, response_model())

    async with client_for_principal("unrelated-user") as client:
        response = await getattr(client, method)(path, json=body) if body is not None else await getattr(client, method)(path)

    assert response.status_code == 404
    assert response.json()["detail"] == "Resource not found"
    service.inspect.assert_not_awaited()
    service.read_context.assert_not_awaited()
    service.close_context.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_project_returns_404_without_running_service(authorized_client, monkeypatch) -> None:
    service = install_service_override(monkeypatch, response_model())

    response = await authorized_client.post("/api/v1/projects/missing_project/integrity-troubleshooter", json=REQUEST)

    assert response.status_code == 404
    assert response.json()["detail"] == "Resource not found"
    service.inspect.assert_not_awaited()
