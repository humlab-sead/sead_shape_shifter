"""Tests for the SIMS client provider-scope contract registration."""

from typing import Any

import httpx
import pytest

from backend.app.clients.sims_client import SimsClient
from backend.app.models.sims import EntityContractDeclaration, RegisterScopeContractsRequest

SCOPE_NAME = "provider://mal/test-pilot"


def _recording_client(
    payload: dict[str, Any],
    *,
    status_code: int = 200,
    caller: str | None = "shape-shifter",
    token: str | None = "s3cret",
) -> tuple[SimsClient, list[httpx.Request]]:
    """Build a SimsClient whose transport records the outgoing request."""
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(status_code, json=payload)

    client = SimsClient(
        "http://sims.test",
        contract_caller=caller,
        contract_registration_token=token,
    )
    client._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))  # pylint: disable=protected-access
    return client, requests


def _registration_request() -> RegisterScopeContractsRequest:
    return RegisterScopeContractsRequest(
        scope_name=SCOPE_NAME,
        entities=[
            EntityContractDeclaration(entity_type="site", business_keys=["site_name", "country"]),
        ],
        created_by="operator@example.com",
    )


@pytest.mark.asyncio
async def test_registers_contracts_with_caller_headers_and_ordered_keys():
    payload = {
        "scope_name": SCOPE_NAME,
        "scope_uuid": "11111111-1111-1111-1111-111111111111",
        "entities": [
            {"entity_type": "site", "business_keys": ["site_name", "country"], "state": "created"},
        ],
    }
    client, requests = _recording_client(payload)

    registration = await client.register_scope_contracts(_registration_request())

    assert len(requests) == 1
    request = requests[0]
    assert request.method == "POST"
    assert str(request.url) == "http://sims.test/identity/scope-contracts"
    assert request.headers["X-SIMS-Caller"] == "shape-shifter"
    assert request.headers["X-SIMS-Caller-Token"] == "s3cret"
    assert request.content is not None
    assert b'"business_keys":["site_name","country"]' in request.content
    assert registration.scope_name == SCOPE_NAME
    assert registration.entities[0].state == "created"
    assert registration.entities[0].business_keys == ["site_name", "country"]

    await client.close()


@pytest.mark.asyncio
async def test_omits_caller_headers_when_client_has_no_registration_credentials():
    payload = {
        "scope_name": SCOPE_NAME,
        "scope_uuid": "11111111-1111-1111-1111-111111111111",
        "entities": [{"entity_type": "site", "business_keys": ["site_name"], "state": "existing"}],
    }
    client, requests = _recording_client(payload, caller=None, token=None)

    await client.register_scope_contracts(_registration_request())

    assert "X-SIMS-Caller" not in requests[0].headers
    assert "X-SIMS-Caller-Token" not in requests[0].headers

    await client.close()


@pytest.mark.asyncio
async def test_conflict_response_raises_status_error_with_detail():
    payload = {
        "detail": {
            "message": "Business-key contract conflict",
            "conflicts": [
                {
                    "entity_type": "site",
                    "registered": ["site_name", "country"],
                    "submitted": ["site_name"],
                }
            ],
        }
    }
    client, _requests = _recording_client(payload, status_code=409)

    with pytest.raises(httpx.HTTPStatusError) as error:
        await client.register_scope_contracts(_registration_request())

    assert error.value.response.status_code == 409
    assert "Business-key contract conflict" in error.value.response.text

    await client.close()
