"""Regression tests for the application authentication boundary and route inventory."""

import re
from pathlib import Path

import pytest
from fastapi.routing import APIRoute
from httpx import ASGITransport, AsyncClient
from starlette.routing import BaseRoute, Mount, Route

from backend.app.main import app
from backend.app.middleware.proxy_auth import ProxyAuthenticationMiddleware

try:
    # pylint: disable=import-outside-toplevel, ungrouped-imports
    from fastapi.routing import iter_route_contexts as _iter_route_contexts  # type: ignore
except ImportError:  # pragma: no cover - FastAPI below 0.141 flattens app.routes on include
    _iter_route_contexts = None

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ROUTE_INVENTORY = PROJECT_ROOT / "docs" / "AUTHORIZATION_ROUTE_INVENTORY.md"
API_PREFIX = "/api/v1"
PUBLIC_HEALTH_PATH = f"{API_PREFIX}/health"

# The only API path the trusted-proxy middleware serves without an identity.
PUBLIC_API_PATHS: frozenset[str] = frozenset({"/health"})

# API routes that carry no dependency authorization_requirement because the request is not
# addressed to one stored resource. Each path is classified authenticated in
# AUTHORIZATION_ROUTE_INVENTORY.md; keep this set in sync with that document.
AUTHENTICATED_ONLY_API_PATHS: frozenset[str] = frozenset(
    {
        "/docs",  # FastAPI-generated Swagger UI
        "/data-sources",  # response narrowed to shared sources the principal can read
        "/data-sources/drivers",  # non-sensitive driver metadata
        "/data-sources/entity-types",  # non-sensitive entity-type metadata
        "/data-sources/excel/metadata",  # handler narrows global and project-local reads
        "/data-sources/files",  # handler narrows global and project-local reads
        "/data-sources/tables",  # client-supplied configuration introspection
        "/data-sources/tables/schema",  # client-supplied configuration introspection
        "/dispatchers",  # registered output-dispatcher metadata
        "/filters/types",  # filter configuration schemas
        "/help-docs/{doc_path:path}",  # repository documentation, contained under docs/
        "/ingesters",  # registered ingester metadata
        "/logs/{log_type}",  # application and error logs are global
        "/logs/{log_type}/download",  # application and error logs are global
        "/openapi.json",  # FastAPI-generated OpenAPI schema
        "/projects",  # response narrowed to projects the principal can read
        "/reconciliation/health",  # reconciliation service status and configured URL
        "/reconciliation/manifest",  # reconciliation service manifest
        "/redoc",  # FastAPI-generated ReDoc UI
        "/suggestions/analyze",  # client-supplied entity configuration
        "/suggestions/entity",  # client-supplied entity configuration
        "/whats-new",  # release notes published under docs/whats-new/
        "/whats-new/{version}/content",  # release notes published under docs/whats-new/
    }
)

# API routes whose requirement is recorded but not enforced. AUTHORIZATION_ROUTE_INVENTORY.md
# documents them as application:run_ingesters and names INGESTER_AUTHORIZATION_TASKS.md and
# INGESTER_FILESYSTEM_BOUNDARIES.md as the owners of the enforcement and containment work.
ENFORCEMENT_PENDING_API_PATHS: frozenset[str] = frozenset(
    {
        "/ingesters/{key}/ingest",
        "/ingesters/{key}/validate",
    }
)

# Documented non-API and mounted paths that depend on the frontend build state. An API-only
# runtime does not serve them, so the parity check does not require them to exist.
CONDITIONAL_DOCUMENTED_PATHS: frozenset[str] = frozenset({"/", "/assets/*", "/{full_path:path}"})

CLASSIFIED_API_PATHS: frozenset[str] = PUBLIC_API_PATHS | AUTHENTICATED_ONLY_API_PATHS | ENFORCEMENT_PENDING_API_PATHS


def _concrete_path(path: str) -> str:
    """Replace FastAPI path parameters with values suitable for middleware requests."""
    return re.sub(r"\{[^}:]+(?::[^}]+)?\}", "authorization-test", path)


def _assembled_routes() -> list[tuple[BaseRoute, str | None, set[str] | None]]:
    """Read every route from the assembled application with its effective path and methods.

    FastAPI 0.141 holds routers added with ``include_router`` in a lazy container, so
    ``app.routes`` no longer lists the included routes and their stored path omits the include
    prefix. Earlier FastAPI versions add the included routes to ``app.routes`` directly.
    """
    if _iter_route_contexts is None:
        return [(route, route.path, route.methods) for route in app.routes if isinstance(route, (APIRoute, Route))]
    return [(context.route, context.path, context.methods) for context in _iter_route_contexts(app.routes)]


def _protected_route_paths() -> list[str]:
    """Return every registered HTTP route except the public health check."""
    paths = {
        _concrete_path(path)
        for route, path, methods in _assembled_routes()
        if path is not None and methods and path != PUBLIC_HEALTH_PATH and isinstance(route, (APIRoute, Route))
    }
    paths.add("/docs/README.md")
    return sorted(paths)


def _inventory_route_rows() -> list[tuple[str, str]]:
    """Read the method and path cell of every route row in the maintained inventory."""
    rows: list[tuple[str, str]] = []
    for line in ROUTE_INVENTORY.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 3:
            continue
        methods, path = cells[0].strip("`"), cells[1].strip("`")
        if not path.startswith("/") or methods.startswith("-"):
            continue
        rows.append((methods, path))
    return rows


def _documented_api_routes() -> set[tuple[str, str]]:
    """Read method/path entries from the maintained authorization route inventory."""
    routes: set[tuple[str, str]] = set()
    for methods, path in _inventory_route_rows():
        if not path.startswith(f"{API_PREFIX}/"):
            continue
        for method in methods.split(","):
            routes.add((method.strip(), path))
    return routes


def _documented_non_api_paths() -> set[str]:
    """Read documented paths outside the API prefix, such as generated and mounted routes."""
    return {path for _, path in _inventory_route_rows() if not path.startswith(f"{API_PREFIX}/")}


def _runtime_api_routes() -> set[tuple[str, str]]:
    """Return method/path entries for the assembled FastAPI API routes."""
    routes: set[tuple[str, str]] = set()
    for route, path, methods in _assembled_routes():
        if path is None or not methods or not isinstance(route, (APIRoute, Route)):
            continue
        if not path.startswith(f"{API_PREFIX}/"):
            continue
        routes.update((method, path) for method in methods)
    return routes


def _runtime_non_api_paths() -> set[str]:
    """Return assembled direct routes and mounts outside the API prefix."""
    paths = {path for route, path, methods in _assembled_routes() if path is not None and methods and not path.startswith(f"{API_PREFIX}/")}
    paths.update(f"{mount.path.rstrip('/')}/*" for mount in app.routes if isinstance(mount, Mount))
    return paths


def _authorization_requirement(dependency: object) -> dict[str, str] | None:
    """Return authorization metadata attached to a dependency factory."""
    requirement = getattr(dependency, "authorization_requirement", None)
    return requirement if isinstance(requirement, dict) else None


def _unclassified_api_routes(routes: list[tuple[BaseRoute, str | None, set[str] | None]] | None = None) -> list[str]:
    """Return API routes with neither declared authorization metadata nor a documented classification."""
    unclassified: list[str] = []
    for route, path, methods in _assembled_routes() if routes is None else routes:
        if path is None or not methods or not path.startswith(f"{API_PREFIX}/"):
            continue
        if path.removeprefix(API_PREFIX) in CLASSIFIED_API_PATHS:
            continue
        dependant = getattr(route, "dependant", None)
        dependencies = getattr(dependant, "dependencies", ()) if dependant is not None else ()
        if any(_authorization_requirement(dependency.call) is not None for dependency in dependencies):
            continue
        unclassified.append(f"{','.join(sorted(methods))} {path}")
    return sorted(unclassified)


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


def test_route_inventory_matches_direct_and_mounted_routes() -> None:
    """Keep the maintained inventory synchronized with direct routes and mounted paths."""
    documented = _documented_non_api_paths()
    runtime = _runtime_non_api_paths()
    required = documented - CONDITIONAL_DOCUMENTED_PATHS

    assert runtime <= documented, f"Runtime routes outside the API prefix missing from inventory: {sorted(runtime - documented)}"
    assert required <= runtime, f"Inventory lists non-API routes the application does not serve: {sorted(required - runtime)}"


def test_api_routes_are_classified() -> None:
    """Require declared metadata or a documented classification for every assembled API route."""
    unclassified = _unclassified_api_routes()

    assert not unclassified, "Assembled API routes without an authorization classification:\n" + "\n".join(unclassified)


def test_api_classification_check_reports_unclassified_route() -> None:
    """Report an API route that has neither declared metadata nor a documented classification."""

    async def endpoint() -> dict[str, str]:
        return {}

    route = APIRoute(f"{API_PREFIX}/synthetic", endpoint, methods=["POST"])

    unclassified = _unclassified_api_routes([(route, route.path, route.methods)])

    assert unclassified == [f"POST {API_PREFIX}/synthetic"]
