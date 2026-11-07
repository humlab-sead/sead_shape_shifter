"""Authorization and request-validation tests for link troubleshooter API."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.api.v1.endpoints.link_troubleshooter import get_link_troubleshooter_service
from backend.app.core.config import settings
from backend.app.main import app
from backend.app.models.link_troubleshooter import (
    LinkExperimentContextResponse,
    LinkExperimentTrialResponse,
    LinkTroubleshootBaseline,
    LinkTroubleshootComparison,
    LinkTroubleshootResponse,
    LinkTroubleshootTotals,
    LinkTroubleshootTrial,
)
from backend.app.services import project_service
from backend.app.services.link_troubleshooter_service import LinkExperimentContextResult, LinkExperimentTrialResult

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


# ---------------------------------------------------------------------------
# Retained experiment context routes
# ---------------------------------------------------------------------------

CONTEXT_PATH = "/api/v1/projects/test_project/link-experiment-contexts"
CONTEXT_ITEM_PATH = f"{CONTEXT_PATH}/context-1"
TRIAL_PATH = f"{CONTEXT_ITEM_PATH}/trials"
TRIAL_REQUEST = {
    "local_keys": ["trial_code"],
    "remote_keys": ["trial_value"],
    "how": "left",
    "allow_null_keys": True,
    "null_keys_equal": False,
}
CONTEXT_REQUEST = {
    "issue_type": "row_count_mismatch",
    "local_entity": "orders",
    "metadata": {"fk_index": 0, "link_pass": "initial"},
}


def context_response(*, context_id: str | None = "context-1", status: str = "reproduced") -> LinkExperimentContextResponse:
    """Build one retained-context response for route tests."""
    return LinkExperimentContextResponse(
        context_id=context_id,
        status=status,  # type: ignore[arg-type]
        reason="reproduced",
        message="The retained link inputs are ready.",
        expires_at=datetime(2026, 1, 1, 12, 15, tzinfo=timezone.utc),
        baseline=LinkTroubleshootBaseline(diagnostic_status="incomplete", diagnostic_reason="row_limit_exceeded"),
    )


def trial_response(*, status: str = "complete") -> LinkExperimentTrialResponse:
    """Build one context trial response for route tests."""
    trial = LinkTroubleshootComparison(
        status=status,  # type: ignore[arg-type]
        reason="complete" if status == "complete" else "invalid_keys",
        message="The trial finished.",
        totals=(
            LinkTroubleshootTotals(input_a_rows=3, output_rows=2, unmatched_a_rows=1, multiply_matched_a_rows=0)
            if status == "complete"
            else None
        ),
    )
    return LinkExperimentTrialResponse(
        context_id="context-1",
        expires_at=datetime(2026, 1, 1, 12, 15, tzinfo=timezone.utc),
        local_keys=["trial_code"],
        remote_keys=["trial_value"],
        baseline=LinkTroubleshootBaseline(diagnostic_status="complete"),
        trial=trial,
    )


def install_context_service(monkeypatch, **overrides) -> Mock:
    """Install a context-aware service mock as the endpoint dependency."""
    service = Mock()
    service.open_context = AsyncMock(return_value=overrides.get("open_response", context_response()))
    service.read_context = AsyncMock(
        return_value=overrides.get("read_result", LinkExperimentContextResult(state="found", response=context_response()))
    )
    service.run_context_trial = AsyncMock(
        return_value=overrides.get(
            "trial_result",
            LinkExperimentTrialResult(state="found", response=trial_response()),
        )
    )
    service.close_context = AsyncMock(return_value=overrides.get("closed", True))
    monkeypatch.setitem(app.dependency_overrides, get_link_troubleshooter_service, lambda: service)
    return service


@pytest.mark.asyncio
async def test_open_context_forwards_the_authorized_owner_and_project(project_client, monkeypatch) -> None:
    expected = context_response()
    service = install_context_service(monkeypatch, open_response=expected)

    response = await project_client.post(CONTEXT_PATH, json=CONTEXT_REQUEST)

    assert response.status_code == 200, response.text
    assert response.json() == expected.model_dump(mode="json")
    service.open_context.assert_awaited_once_with(
        project_name="test_project",
        issue_type="row_count_mismatch",
        local_entity="orders",
        metadata=CONTEXT_REQUEST["metadata"],
        owner_principal_id="test-user",
        project_locator="test_project",
    )


@pytest.mark.asyncio
async def test_open_context_without_reproduction_returns_no_identifier(project_client, monkeypatch) -> None:
    expected = context_response(context_id=None, status="not_reproduced")
    service = install_context_service(monkeypatch, open_response=expected)

    response = await project_client.post(CONTEXT_PATH, json=CONTEXT_REQUEST)

    assert response.status_code == 200, response.text
    assert response.json()["context_id"] is None
    assert response.json()["status"] == "not_reproduced"
    service.open_context.assert_awaited_once()


@pytest.mark.asyncio
async def test_read_context_returns_the_retained_baseline(project_client, monkeypatch) -> None:
    expected = context_response()
    service = install_context_service(monkeypatch, read_result=LinkExperimentContextResult(state="found", response=expected))

    response = await project_client.get(CONTEXT_ITEM_PATH)

    assert response.status_code == 200, response.text
    assert response.json() == expected.model_dump(mode="json")
    service.read_context.assert_awaited_once_with(
        context_id="context-1",
        owner_principal_id="test-user",
        project_locator="test_project",
    )


@pytest.mark.asyncio
async def test_read_context_reports_expiry_explicitly(project_client, monkeypatch) -> None:
    install_context_service(monkeypatch, read_result=LinkExperimentContextResult(state="expired"))

    response = await project_client.get(CONTEXT_ITEM_PATH)

    assert response.status_code == 410
    assert response.json()["detail"]["reason"] == "context_expired"


@pytest.mark.asyncio
async def test_read_context_conceals_an_unavailable_identifier(project_client, monkeypatch) -> None:
    service = install_context_service(monkeypatch, read_result=LinkExperimentContextResult(state="unavailable"))

    response = await project_client.get(CONTEXT_ITEM_PATH)

    assert response.status_code == 404
    assert response.json()["detail"] == "Resource not found"
    service.read_context.assert_awaited_once()


@pytest.mark.asyncio
async def test_close_context_returns_no_content(project_client, monkeypatch) -> None:
    service = install_context_service(monkeypatch)

    response = await project_client.delete(CONTEXT_ITEM_PATH)

    assert response.status_code == 204
    service.close_context.assert_awaited_once_with(
        context_id="context-1",
        owner_principal_id="test-user",
        project_locator="test_project",
    )


@pytest.mark.asyncio
async def test_close_context_conceals_an_unknown_identifier(project_client, monkeypatch) -> None:
    service = install_context_service(monkeypatch, closed=False)

    response = await project_client.delete(CONTEXT_ITEM_PATH)

    assert response.status_code == 404
    assert response.json()["detail"] == "Resource not found"
    service.close_context.assert_awaited_once()


@pytest.mark.asyncio
async def test_context_routes_require_project_read_access(
    project_client,  # pylint: disable=unused-argument
    monkeypatch,
) -> None:
    service = install_context_service(monkeypatch)

    async with client_for_principal("unrelated-user") as client:
        opened = await client.post(CONTEXT_PATH, json=CONTEXT_REQUEST)
        read = await client.get(CONTEXT_ITEM_PATH)
        tried = await client.post(TRIAL_PATH, json=TRIAL_REQUEST)
        closed = await client.delete(CONTEXT_ITEM_PATH)

    for response in (opened, read, tried, closed):
        assert response.status_code == 404
        assert response.json()["detail"] == "Resource not found"

    service.open_context.assert_not_awaited()
    service.read_context.assert_not_awaited()
    service.run_context_trial.assert_not_awaited()
    service.close_context.assert_not_awaited()


@pytest.mark.parametrize(
    "body",
    [
        {key: value for key, value in CONTEXT_REQUEST.items() if key != "issue_type"},
        {key: value for key, value in CONTEXT_REQUEST.items() if key != "local_entity"},
        {key: value for key, value in CONTEXT_REQUEST.items() if key != "metadata"},
    ],
)
@pytest.mark.asyncio
async def test_invalid_context_request_returns_422_without_running_service(project_client, monkeypatch, body: dict) -> None:
    service = install_context_service(monkeypatch)

    response = await project_client.post(CONTEXT_PATH, json=body)

    assert response.status_code == 422
    service.open_context.assert_not_awaited()


@pytest.mark.asyncio
async def test_context_trial_forwards_controls_and_the_authorized_owner(project_client, monkeypatch) -> None:
    expected = trial_response()
    service = install_context_service(monkeypatch, trial_result=LinkExperimentTrialResult(state="found", response=expected))

    response = await project_client.post(TRIAL_PATH, json=TRIAL_REQUEST)

    assert response.status_code == 200, response.text
    assert response.json() == expected.model_dump(mode="json")
    service.run_context_trial.assert_awaited_once_with(
        context_id="context-1",
        owner_principal_id="test-user",
        project_locator="test_project",
        local_keys=["trial_code"],
        remote_keys=["trial_value"],
        how="left",
        allow_null_keys=True,
        null_keys_equal=False,
    )


@pytest.mark.asyncio
async def test_context_trial_omitted_controls_are_forwarded_as_inherited(project_client, monkeypatch) -> None:
    service = install_context_service(monkeypatch)

    response = await project_client.post(TRIAL_PATH, json={"local_keys": ["trial_code"], "remote_keys": ["trial_value"]})

    assert response.status_code == 200, response.text
    service.run_context_trial.assert_awaited_once_with(
        context_id="context-1",
        owner_principal_id="test-user",
        project_locator="test_project",
        local_keys=["trial_code"],
        remote_keys=["trial_value"],
        how=None,
        allow_null_keys=None,
        null_keys_equal=None,
    )


@pytest.mark.asyncio
async def test_context_trial_reports_expiry_explicitly(project_client, monkeypatch) -> None:
    install_context_service(monkeypatch, trial_result=LinkExperimentTrialResult(state="expired"))

    response = await project_client.post(TRIAL_PATH, json=TRIAL_REQUEST)

    assert response.status_code == 410
    assert response.json()["detail"]["reason"] == "context_expired"


@pytest.mark.asyncio
async def test_context_trial_conceals_an_unavailable_identifier(project_client, monkeypatch) -> None:
    service = install_context_service(monkeypatch, trial_result=LinkExperimentTrialResult(state="unavailable"))

    response = await project_client.post(TRIAL_PATH, json=TRIAL_REQUEST)

    assert response.status_code == 404
    assert response.json()["detail"] == "Resource not found"
    service.run_context_trial.assert_awaited_once()


@pytest.mark.asyncio
async def test_context_trial_returns_a_failed_payload_without_totals(project_client, monkeypatch) -> None:
    failed = trial_response(status="failed")
    install_context_service(monkeypatch, trial_result=LinkExperimentTrialResult(state="found", response=failed))

    response = await project_client.post(TRIAL_PATH, json=TRIAL_REQUEST)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["trial"]["status"] == "failed"
    assert payload["trial"]["reason"] == "invalid_keys"
    assert payload["trial"]["totals"] is None
    assert payload["trial"]["detail"] is None


@pytest.mark.parametrize(
    "body",
    [
        {"local_keys": ["trial_code"]},
        {"remote_keys": ["trial_value"]},
        {"local_keys": ["trial_code"], "remote_keys": ["trial_value"], "how": "outer"},
        {"local_keys": ["trial_code"], "remote_keys": ["trial_value"], "page": 2},
        {"local_keys": ["trial_code"], "remote_keys": ["trial_value"], "unknown": True},
    ],
)
@pytest.mark.asyncio
async def test_invalid_context_trial_request_returns_422_without_running_a_trial(project_client, monkeypatch, body: dict) -> None:
    service = install_context_service(monkeypatch)

    response = await project_client.post(TRIAL_PATH, json=body)

    assert response.status_code == 422
    service.run_context_trial.assert_not_awaited()
