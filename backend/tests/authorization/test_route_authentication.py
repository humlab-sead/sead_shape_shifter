"""Regression tests for the application authentication boundary and route inventory."""

import re
from pathlib import Path

import pytest
from fastapi.routing import APIRoute
from httpx import ASGITransport, AsyncClient
from starlette.routing import Route

from backend.app.main import app
from backend.app.middleware.proxy_auth import ProxyAuthenticationMiddleware

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ROUTE_INVENTORY = PROJECT_ROOT / "docs" / "AUTHORIZATION_ROUTE_INVENTORY.md"
PUBLIC_HEALTH_PATH = "/api/v1/health"


def _concrete_path(path: str) -> str:
    """Replace FastAPI path parameters with values suitable for middleware requests."""
    return re.sub(r"\{[^}:]+(?::[^}]+)?\}", "authorization-test", path)


def _protected_route_paths() -> list[str]:
    """Return every registered HTTP route except the public health check."""
    paths = {
        _concrete_path(route.path)
        for route in app.routes
        if isinstance(route, (APIRoute, Route)) and route.methods and route.path != PUBLIC_HEALTH_PATH
    }
    paths.add("/docs/README.md")
    return sorted(paths)


def _documented_api_routes() -> set[tuple[str, str]]:
    """Read method/path entries from the maintained authorization route inventory."""
    routes: set[tuple[str, str]] = set()
    for line in ROUTE_INVENTORY.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 3:
            continue
        methods, path = cells[0].strip("`"), cells[1].strip("`")
        if not path.startswith("/api/v1/") or methods == "Method":
            continue
        for method in methods.split(","):
            routes.add((method.strip(), path))
    return routes


def _runtime_api_routes() -> set[tuple[str, str]]:
    """Return method/path entries for the assembled FastAPI API routes."""
    routes: set[tuple[str, str]] = set()
    for route in app.routes:
        if not isinstance(route, (APIRoute, Route)) or not route.methods or not route.path.startswith("/api/v1/"):
            continue
        routes.update((method, route.path) for method in route.methods)
    return routes


@pytest.mark.asyncio
@pytest.mark.parametrize("path", _protected_route_paths())
async def test_registered_sensitive_routes_require_proxy_identity(path: str) -> None:
    """Reject every sensitive API and direct application route without proxy identity."""
    protected_app = ProxyAuthenticationMiddleware(
        app,
        enabled=True,
        header_name="X-Authenticated-User",
        public_paths={PUBLIC_HEALTH_PATH},
    )

    async with AsyncClient(transport=ASGITransport(app=protected_app), base_url="http://testserver") as client:
        response = await client.get(path)

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required"}


@pytest.mark.asyncio
async def test_health_check_is_public_without_configuration_details() -> None:
    """Allow health checks without identity while keeping filesystem details private."""
    protected_app = ProxyAuthenticationMiddleware(
        app,
        enabled=True,
        header_name="X-Authenticated-User",
        public_paths={PUBLIC_HEALTH_PATH},
    )

    async with AsyncClient(transport=ASGITransport(app=protected_app), base_url="http://testserver") as client:
        response = await client.get(PUBLIC_HEALTH_PATH)

    assert response.status_code == 200
    assert set(response.json()) == {"status", "version", "environment", "timestamp"}
    assert "projects_dir" not in response.text


@pytest.mark.asyncio
async def test_proxy_identity_reaches_direct_application_routes() -> None:
    """Allow an authenticated principal to reach generated docs and static documentation."""
    protected_app = ProxyAuthenticationMiddleware(
        app,
        enabled=True,
        header_name="X-Authenticated-User",
        public_paths={PUBLIC_HEALTH_PATH},
    )

    async with AsyncClient(
        transport=ASGITransport(app=protected_app),
        base_url="http://testserver",
        headers={"X-Authenticated-User": "test-user"},
    ) as client:
        for path in ("/api/v1/openapi.json", "/api/v1/docs", "/api/v1/redoc", "/docs/README.md"):
            response = await client.get(path)
            assert response.status_code == 200, path


def test_route_inventory_matches_assembled_api_routes() -> None:
    """Keep the maintained API route inventory synchronized with FastAPI registration."""
    documented = _documented_api_routes()
    runtime = _runtime_api_routes()

    assert runtime <= documented, f"Runtime API routes missing from inventory: {sorted(runtime - documented)}"
    assert documented <= runtime, f"Inventory contains unregistered API routes: {sorted(documented - runtime)}"
