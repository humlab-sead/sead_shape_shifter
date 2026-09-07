"""Tests for the authentication-to-principal adapter."""

import pytest
from fastapi import Request
from fastapi.exceptions import HTTPException

from backend.app.authorization.authentication import AuthenticationAdapter


def _request(identity: str | None = None) -> Request:
    request = Request({"type": "http", "method": "GET", "path": "/", "headers": []})
    if identity is not None:
        request.state.authenticated_user = identity
    return request


def test_adapter_preserves_trusted_proxy_identity() -> None:
    principal = AuthenticationAdapter(enabled=True, environment="production").principal_from_request(_request("Alice"))

    assert principal.principal_id == "Alice"
    assert principal.authentication_provider == "trusted-proxy"


def test_adapter_preserves_verified_groups_from_request_state() -> None:
    request = _request("Alice")
    request.state.authenticated_groups = [" editors ", "reviewers"]

    principal = AuthenticationAdapter(enabled=True, environment="production", groups_enabled=True).principal_from_request(request)

    assert principal.group_ids == frozenset({"editors", "reviewers"})


def test_adapter_allows_only_explicit_development_principal() -> None:
    adapter = AuthenticationAdapter(enabled=False, environment="development", development_principal_id="developer")

    assert adapter.principal_from_request(_request()).principal_id == "developer"


@pytest.mark.parametrize(
    "adapter",
    [
        AuthenticationAdapter(enabled=True, environment="production"),
        AuthenticationAdapter(enabled=False, environment="development"),
        AuthenticationAdapter(enabled=False, environment="production", development_principal_id="developer"),
    ],
)
def test_adapter_rejects_missing_identity(adapter: AuthenticationAdapter) -> None:
    with pytest.raises(HTTPException) as error:
        adapter.principal_from_request(_request())

    assert error.value.status_code == 401
