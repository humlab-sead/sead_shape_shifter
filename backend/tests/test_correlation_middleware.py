"""Tests for correlation ID middleware."""

import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from backend.app.middleware.correlation import (
    CorrelationMiddleware,
    correlation_id_var,
    get_correlation_id,
)

# pylint: disable=redefined-outer-name


class TestGetCorrelationId:
    """Test the get_correlation_id helper function."""

    def test_returns_default_outside_request_context(self):
        """Outside a request context, returns 'no-corr'."""
        assert get_correlation_id() == "no-corr"

    def test_returns_set_value_within_context(self):
        """When ContextVar is explicitly set, returns the set value."""
        token = correlation_id_var.set("test-123")
        try:
            assert get_correlation_id() == "test-123"
        finally:
            correlation_id_var.reset(token)

    def test_resets_to_default_after_context_reset(self):
        """After resetting the ContextVar, returns the default."""
        token = correlation_id_var.set("temporary")
        correlation_id_var.reset(token)
        assert get_correlation_id() == "no-corr"


class TestCorrelationMiddleware:
    """Test the CorrelationMiddleware ASGI middleware."""

    @pytest.fixture
    def app(self):
        """Create a minimal Starlette app with the middleware."""
        captured_ids = []

        async def capture_endpoint(request: Request) -> JSONResponse:  # pylint: disable=unused-argument
            """Endpoint that captures the correlation ID from ContextVar."""
            corr_id = get_correlation_id()
            captured_ids.append(corr_id)
            return JSONResponse({"correlation_id": corr_id})

        starlette_app = Starlette(routes=[Route("/test", capture_endpoint)])
        starlette_app.add_middleware(CorrelationMiddleware)
        return starlette_app, captured_ids

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        starlette_app, _ = app
        return TestClient(starlette_app)

    def test_generates_correlation_id_when_no_header(self, app):
        """Middleware generates an 8-char ID when no header is sent."""
        starlette_app, captured_ids = app
        client = TestClient(starlette_app)

        response = client.get("/test")

        assert response.status_code == 200
        corr_id = response.headers["X-Correlation-ID"]
        assert len(corr_id) == 8
        assert corr_id == captured_ids[0]
        assert corr_id == response.json()["correlation_id"]

    def test_uses_client_provided_correlation_id(self, app):
        """Middleware uses X-Correlation-ID header when provided."""
        starlette_app, captured_ids = app
        client = TestClient(starlette_app)

        response = client.get("/test", headers={"X-Correlation-ID": "my-custom-id"})

        assert response.status_code == 200
        assert response.headers["X-Correlation-ID"] == "my-custom-id"
        assert captured_ids[0] == "my-custom-id"

    def test_response_includes_correlation_id_header(self, client):
        """Response always includes X-Correlation-ID header."""
        response = client.get("/test")
        assert "X-Correlation-ID" in response.headers

    def test_different_requests_get_different_ids(self, app):
        """Each request gets a unique correlation ID."""
        starlette_app, captured_ids = app
        client = TestClient(starlette_app)

        client.get("/test")
        client.get("/test")

        assert len(captured_ids) == 2
        assert captured_ids[0] != captured_ids[1]

    def test_context_is_isolated_between_requests(self, app):
        """ContextVar resets between requests (no leakage)."""
        starlette_app, _ = app
        client = TestClient(starlette_app)

        r1 = client.get("/test", headers={"X-Correlation-ID": "req-1"})
        r2 = client.get("/test", headers={"X-Correlation-ID": "req-2"})

        assert r1.json()["correlation_id"] == "req-1"
        assert r2.json()["correlation_id"] == "req-2"
        # After both requests, default should be restored
        assert get_correlation_id() == "no-corr"
