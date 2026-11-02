"""Authorization and request-validation tests for link troubleshooter API."""

from __future__ import annotations

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, Mock

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.api.v1.endpoints.link_troubleshooter import get_link_troubleshooter_service
from backend.app.core.config import settings
from backend.app.main import app
from backend.app.models.link_troubleshooter import (
    LinkTroubleshootBaseline,
    LinkTroubleshootResponse,
    LinkTroubleshootTrial,
)
from backend.app.services import project_service

REQUEST = {
    "issue_type": "row_count_mismatch",
    "local_entity": "orders",
    "metadata": {
        "fk_index": 0,
        "fk_signature": "saved-signature",
        "link_pass": "initial",
        "join_type": "inner",
        "row_count_before": 3,
        "row_count_after": 2,
    },
    "local_keys": ["trial_code"],
    "remote_keys": ["trial_value"],
    "page": 2,
    "page_size": 25,
    "row_filter": "unmatched",
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


def install_service_override(monkeypatch, response: LinkTroubleshootResponse) -> Mock:
    """Return a service mock installed as the endpoint dependency."""
    service = Mock()
    service.run = AsyncMock(return_value=response)
    monkeypatch.setitem(app.dependency_overrides, get_link_troubleshooter_service, lambda: service)
    return service


def response_model(
    *,
    status: str = "reproduced",
    trial: LinkTroubleshootTrial | None = None,
) -> LinkTroubleshootResponse:
    """Build one public response for route tests."""
    return LinkTroubleshootResponse(
        status=status,  # type: ignore[arg-type]
        reason="test-result",
        message="Test response.",
        baseline=LinkTroubleshootBaseline(diagnostic_status="not_run"),
        trial=trial,
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

    response = await project_client.post("/api/v1/projects/test_project/link-troubleshooter", json=REQUEST)

    assert response.status_code == 200, response.text
    assert response.json() == expected.model_dump(mode="json")
    service.run.assert_awaited_once_with(
        project_name="test_project",
        issue_type="row_count_mismatch",
        local_entity="orders",
        metadata=REQUEST["metadata"],
        local_keys=["trial_code"],
        remote_keys=["trial_value"],
        page=2,
        page_size=25,
        row_filter="unmatched",
    )


@pytest.mark.parametrize("status", ["ineligible", "not_reproduced"])
@pytest.mark.asyncio
async def test_baseline_outcomes_return_200_without_a_trial(project_client, monkeypatch, status: str) -> None:
    expected = response_model(status=status)
    service = install_service_override(monkeypatch, expected)

    response = await project_client.post("/api/v1/projects/test_project/link-troubleshooter", json=REQUEST)

    assert response.status_code == 200, response.text
    assert response.json()["status"] == status
    assert response.json()["trial"] is None
    service.run.assert_awaited_once()


@pytest.mark.parametrize("status", ["failed", "incomplete"])
@pytest.mark.asyncio
async def test_trial_failures_return_200_without_partial_details(project_client, monkeypatch, status: str) -> None:
    trial = LinkTroubleshootTrial(
        status=status,  # type: ignore[arg-type]
        reason="row_limit_exceeded" if status == "incomplete" else "invalid_keys",
        message="Trial details are unavailable.",
        local_keys=["trial_code"],
        remote_keys=["trial_value"],
    )
    service = install_service_override(monkeypatch, response_model(trial=trial))

    response = await project_client.post("/api/v1/projects/test_project/link-troubleshooter", json=REQUEST)

    assert response.status_code == 200, response.text
    result = response.json()["trial"]
    assert result["status"] == status
    assert result["reason"] == trial.reason
    assert result["message"] == trial.message
    assert result["totals"] is None
    assert result["rows"] == []
    assert result["pagination"] is None
    service.run.assert_awaited_once()


@pytest.mark.parametrize(
    "body",
    [
        {key: value for key, value in REQUEST.items() if key != "issue_type"},
        {key: value for key, value in REQUEST.items() if key != "metadata"},
        {**REQUEST, "page": 0},
        {**REQUEST, "page_size": 0},
        {**REQUEST, "page_size": 501},
    ],
)
@pytest.mark.asyncio
async def test_invalid_request_shapes_return_422_without_running_service(project_client, monkeypatch, body: dict) -> None:
    service = install_service_override(monkeypatch, response_model())

    response = await project_client.post("/api/v1/projects/test_project/link-troubleshooter", json=body)

    assert response.status_code == 422
    service.run.assert_not_awaited()


@pytest.mark.asyncio
async def test_principal_without_project_read_gets_concealed_404(
    project_client,  # pylint: disable=unused-argument
    monkeypatch,
) -> None:
    service = install_service_override(monkeypatch, response_model())

    async with client_for_principal("unrelated-user") as client:
        response = await client.post("/api/v1/projects/test_project/link-troubleshooter", json=REQUEST)

    assert response.status_code == 404
    assert response.json()["detail"] == "Resource not found"
    service.run.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_project_returns_404_without_running_service(authorized_client, monkeypatch) -> None:
    service = install_service_override(monkeypatch, response_model())

    response = await authorized_client.post("/api/v1/projects/missing_project/link-troubleshooter", json=REQUEST)

    assert response.status_code == 404
    assert response.json()["detail"] == "Resource not found"
    service.run.assert_not_awaited()
