"""Tests for reverse-proxy identity enforcement."""

import json
from collections.abc import Callable

import pytest

from backend.app.middleware.proxy_auth import ProxyAuthenticationMiddleware


async def _call_middleware(
    path: str,
    headers: dict[str, str],
    *,
    enabled: bool = True,
    groups_enabled: bool = False,
) -> list[dict]:
    """Run the middleware with a minimal ASGI request and collect response messages."""
    messages: list[dict] = []

    async def app(scope: dict, receive: Callable, send: Callable) -> None:
        body = json.dumps(
            {
                "user": scope.get("state", {}).get("authenticated_user"),
                "groups": scope.get("state", {}).get("authenticated_groups", []),
            }
        ).encode()
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": body})

    middleware = ProxyAuthenticationMiddleware(
        app,
        enabled=enabled,
        header_name="X-Authenticated-User",
        groups_enabled=groups_enabled,
        groups_header_name="X-Authenticated-Groups",
        public_paths={"/health"},
    )

    request_headers = [(name.lower().encode(), value.encode()) for name, value in headers.items()]

    async def receive() -> dict:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict) -> None:
        messages.append(message)

    await middleware(
        {
            "type": "http",
            "method": "GET",
            "path": path,
            "raw_path": path.encode(),
            "headers": request_headers,
            "query_string": b"",
            "scheme": "http",
            "server": ("testserver", 80),
            "client": ("testclient", 123),
            "http_version": "1.1",
        },
        receive,
        send,
    )
    return messages


def _response_status(messages: list[dict]) -> int:
    """Return the status code from collected ASGI response messages."""
    return next(message["status"] for message in messages if message["type"] == "http.response.start")


@pytest.mark.asyncio
async def test_proxy_auth_rejects_request_without_identity() -> None:
    messages = await _call_middleware("/private", {})

    assert _response_status(messages) == 401
    assert json.loads(_response_body(messages)) == {"detail": "Authentication required"}


def _response_body(messages: list[dict]) -> bytes:
    """Return the response body from collected ASGI response messages."""
    return b"".join(message.get("body", b"") for message in messages if message["type"] == "http.response.body")


@pytest.mark.asyncio
async def test_proxy_auth_stores_forwarded_identity() -> None:
    messages = await _call_middleware("/private", {"X-Authenticated-User": "  alice  "})

    assert _response_status(messages) == 200
    assert json.loads(_response_body(messages)) == {"user": "alice", "groups": []}


@pytest.mark.asyncio
async def test_proxy_auth_accepts_groups_only_when_group_source_is_enabled() -> None:
    headers = {"X-Authenticated-User": "alice", "X-Authenticated-Groups": " editors, reviewers "}

    disabled = await _call_middleware("/private", headers)
    enabled = await _call_middleware("/private", headers, groups_enabled=True)

    assert json.loads(_response_body(disabled))["groups"] == []
    assert json.loads(_response_body(enabled))["groups"] == ["editors", "reviewers"]


@pytest.mark.asyncio
async def test_proxy_auth_allows_configured_health_path() -> None:
    messages = await _call_middleware("/health", {})

    assert _response_status(messages) == 200


@pytest.mark.asyncio
async def test_proxy_auth_rejects_invalid_identity() -> None:
    messages = await _call_middleware("/private", {"X-Authenticated-User": "\n"})

    assert _response_status(messages) == 401
    assert json.loads(_response_body(messages)) == {"detail": "Invalid authenticated identity"}


@pytest.mark.asyncio
async def test_proxy_auth_can_be_disabled_for_local_development() -> None:
    messages = await _call_middleware("/private", {}, enabled=False)

    assert _response_status(messages) == 200
    assert json.loads(_response_body(messages)) == {"user": None, "groups": []}
