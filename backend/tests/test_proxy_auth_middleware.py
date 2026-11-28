"""Tests for reverse-proxy identity enforcement."""

import json

import pytest
from loguru import logger
from pydantic import SecretStr
from starlette.types import Message, Receive, Scope, Send

from backend.app.middleware.proxy_auth import ProxyAuthenticationMiddleware


async def _call_middleware(
    path: str,
    headers: dict[str, str],
    *,
    enabled: bool = True,
    groups_enabled: bool = False,
    secret: str | None = None,
) -> list[Message]:
    """Run the middleware with a minimal ASGI request and collect response messages."""
    messages: list[Message] = []

    async def app(scope: Scope, receive: Receive, send: Send) -> None:  # pylint: disable=unused-argument
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
        secret=SecretStr(secret) if secret is not None else None,
    )

    request_headers = [(name.lower().encode(), value.encode()) for name, value in headers.items()]

    async def receive() -> Message:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: Message) -> None:
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


def _response_status(messages: list[Message]) -> int:
    """Return the status code from collected ASGI response messages."""
    return next(message["status"] for message in messages if message["type"] == "http.response.start")


@pytest.mark.asyncio
async def test_proxy_auth_rejects_request_without_identity() -> None:
    messages = await _call_middleware("/private", {})

    assert _response_status(messages) == 401
    assert json.loads(_response_body(messages)) == {"detail": "Authentication required"}


def _response_body(messages: list[Message]) -> bytes:
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


SECRET = "a1" * 32
SIGNED_IN = {"X-Authenticated-User": "alice"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "secret_headers",
    [{}, {"X-Proxy-Secret": ""}, {"X-Proxy-Secret": "wrong" * 13}, {"X-Proxy-Secret": SECRET + "x"}, {"X-Proxy-Secret": "é" * 64}],
    ids=["missing", "empty", "wrong", "one-character-more", "non-ascii"],
)
async def test_proxy_auth_rejects_identity_without_the_proxy_secret(secret_headers: dict[str, str]) -> None:
    messages = await _call_middleware("/private", {**SIGNED_IN, **secret_headers}, secret=SECRET)

    assert _response_status(messages) == 401
    assert json.loads(_response_body(messages)) == {"detail": "Authentication required"}


@pytest.mark.asyncio
async def test_proxy_auth_accepts_identity_with_the_proxy_secret() -> None:
    messages = await _call_middleware("/private", {**SIGNED_IN, "X-Proxy-Secret": SECRET}, secret=SECRET)

    assert _response_status(messages) == 200
    assert json.loads(_response_body(messages))["user"] == "alice"


@pytest.mark.asyncio
async def test_proxy_auth_still_requires_an_identity_with_the_proxy_secret() -> None:
    messages = await _call_middleware("/private", {"X-Proxy-Secret": SECRET}, secret=SECRET)

    assert _response_status(messages) == 401


@pytest.mark.asyncio
@pytest.mark.parametrize(("path", "enabled"), [("/health", True), ("/private", False)])
async def test_proxy_auth_needs_no_secret_on_public_paths_or_when_disabled(path: str, enabled: bool) -> None:
    messages = await _call_middleware(path, {}, enabled=enabled, secret=SECRET)

    assert _response_status(messages) == 200


@pytest.mark.asyncio
async def test_proxy_auth_logs_a_rejection_without_either_value() -> None:
    lines: list[str] = []
    handler = logger.add(lines.append, level="WARNING")
    try:
        await _call_middleware("/private", {**SIGNED_IN, "X-Proxy-Secret": "sent-" * 10}, secret=SECRET)
    finally:
        logger.remove(handler)

    output = "".join(lines)
    assert "proxy secret" in output
    assert SECRET not in output
    assert "sent-" not in output
