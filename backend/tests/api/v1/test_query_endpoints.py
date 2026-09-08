"""Tests for query endpoint authorization responses."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.api.dependencies import get_data_source_service
from backend.app.api.v1.endpoints.query import get_query_service
from backend.app.authorization.dependencies import get_authorization_service
from backend.app.authorization.models import Grant, ResourceRecord, ResourceType
from backend.app.authorization.repository import SQLiteAuthorizationRepository
from backend.app.authorization.service import AuthorizationService
from backend.app.main import app
from backend.app.models.data_source import DataSourceConfig
from backend.app.models.query import QueryResult, QueryValidation


@pytest.fixture
def mock_data_source_service() -> MagicMock:
    """Create a mocked data source service."""
    service = MagicMock()
    service.load_data_source.return_value = DataSourceConfig(
        name="authorized-source",
        driver="postgresql",
        host="localhost",
        port=5432,
        database="db",
        dbname=None,
        username="user",
        password=None,
        connection_string=None,
        options=None,
        description=None,
    )
    return service


@pytest.fixture
def mock_query_service() -> MagicMock:
    """Create a mocked query service."""
    service = MagicMock()
    service.execute_query = AsyncMock(
        return_value=QueryResult(
            rows=[{"id": 1}],
            columns=["id"],
            row_count=1,
            execution_time_ms=2,
            is_truncated=False,
            total_rows=1,
        )
    )
    service.introspect_query_columns = AsyncMock(return_value=["id"])
    service.validate_query.return_value = QueryValidation(is_valid=True, errors=[], warnings=[], statement_type="SELECT", tables=[])
    return service


@pytest.fixture
def authorization_repository(tmp_path):
    """Create an isolated authorization store with one readable source."""
    repository = SQLiteAuthorizationRepository(tmp_path / "authorization.sqlite3")
    resource = ResourceRecord(uuid4(), ResourceType.SHARED_DATA_SOURCE, "authorized-source")
    repository.create_resource(resource)
    repository.add_grant(Grant("alice", resource.resource_id, "reader", datetime.now(UTC), "admin"))
    yield repository
    repository.close()


@pytest.fixture
def query_dependencies(
    mock_data_source_service: MagicMock,
    mock_query_service: MagicMock,
    authorization_repository: SQLiteAuthorizationRepository,
):
    """Override query services while retaining the real authorization dependency."""

    def override_get_data_source_service():
        return mock_data_source_service

    def override_get_query_service():
        return mock_query_service

    async def override_get_authorization_service():
        repository = SQLiteAuthorizationRepository(authorization_repository.path)
        try:
            yield AuthorizationService(repository)
        finally:
            repository.close()

    app.dependency_overrides[get_data_source_service] = override_get_data_source_service
    app.dependency_overrides[get_query_service] = override_get_query_service
    app.dependency_overrides[get_authorization_service] = override_get_authorization_service
    yield
    app.dependency_overrides.clear()


def _client_for_principal(principal_id: str | None) -> AsyncClient:
    """Create a client that optionally supplies a trusted-proxy identity."""

    async def authenticated_app(scope, receive, send) -> None:
        if scope["type"] == "http" and principal_id is not None:
            scope.setdefault("state", {})["authenticated_user"] = principal_id
        await app(scope, receive, send)

    return AsyncClient(transport=ASGITransport(app=authenticated_app), base_url="http://testserver")


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("/api/v1/data-sources/authorized-source/query/execute", {"query": "SELECT id FROM table1"}),
        ("/api/v1/data-sources/authorized-source/query/validate", {"query": "SELECT id FROM table1"}),
        ("/api/v1/data-sources/authorized-source/query/columns", {"query": "SELECT id FROM table1"}),
    ],
)
@pytest.mark.asyncio
async def test_query_endpoints_require_authentication(query_dependencies, path: str, payload: dict[str, str]) -> None:
    async with _client_for_principal(None) as client:
        response = await client.post(path, json=payload)

    assert response.status_code == 401


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("/api/v1/data-sources/authorized-source/query/execute", {"query": "SELECT id FROM table1"}),
        ("/api/v1/data-sources/authorized-source/query/validate", {"query": "SELECT id FROM table1"}),
        ("/api/v1/data-sources/authorized-source/query/columns", {"query": "SELECT id FROM table1"}),
    ],
)
@pytest.mark.asyncio
async def test_query_endpoints_conceal_unreadable_sources(query_dependencies, path: str, payload: dict[str, str]) -> None:
    async with _client_for_principal("bob") as client:
        response = await client.post(path, json=payload)

    assert response.status_code == 404
    assert response.json() == {"detail": "Resource not found"}


@pytest.mark.asyncio
async def test_execute_query_uses_authorized_shared_source(
    query_dependencies, mock_data_source_service: MagicMock, mock_query_service: MagicMock
) -> None:
    async with _client_for_principal("alice") as client:
        response = await client.post("/api/v1/data-sources/authorized-source/query/execute", json={"query": "SELECT id FROM table1"})

    assert response.status_code == 200
    mock_data_source_service.load_data_source.assert_called_once_with("authorized-source", strict=True)
    mock_query_service.execute_query.assert_awaited_once()


@pytest.mark.asyncio
async def test_validate_query_uses_authorized_shared_source(query_dependencies, mock_query_service: MagicMock) -> None:
    async with _client_for_principal("alice") as client:
        response = await client.post("/api/v1/data-sources/authorized-source/query/validate", json={"query": "SELECT id FROM table1"})

    assert response.status_code == 200
    mock_query_service.validate_query.assert_called_once_with("SELECT id FROM table1", "authorized-source")


@pytest.mark.asyncio
async def test_introspect_query_columns_uses_authorized_shared_source(
    query_dependencies, mock_data_source_service: MagicMock, mock_query_service: MagicMock
) -> None:
    async with _client_for_principal("alice") as client:
        response = await client.post("/api/v1/data-sources/authorized-source/query/columns", json={"query": "SELECT id FROM table1"})

    assert response.status_code == 200
    assert response.json() == {"columns": ["id"]}
    mock_data_source_service.load_data_source.assert_called_once_with("authorized-source", strict=True)
    mock_query_service.introspect_query_columns.assert_awaited_once()
