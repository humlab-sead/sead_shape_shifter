"""Tests for query API endpoint authorization wiring."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.app.api.dependencies import get_data_source_service
from backend.app.api.v1.endpoints.query import get_query_service, query_reader_dependency
from backend.app.authorization.models import Action, AuthorizedResource, Principal, ResourceRecord, ResourceType
from backend.app.main import app
from backend.app.models.data_source import DataSourceConfig
from backend.app.models.query import QueryResult


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
        username="user",
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
    return service


@pytest.fixture
def client(mock_data_source_service: MagicMock, mock_query_service: MagicMock):
    """Create a test client with query dependencies overridden."""

    def override_get_data_source_service():
        return mock_data_source_service

    def override_get_query_service():
        return mock_query_service

    def override_get_readable_source():
        principal = Principal("alice", "test", datetime.now(UTC))
        return AuthorizedResource(principal, Action.READ, ResourceRecord(uuid4(), ResourceType.SHARED_DATA_SOURCE, "authorized-source"))

    app.dependency_overrides[get_data_source_service] = override_get_data_source_service
    app.dependency_overrides[get_query_service] = override_get_query_service
    app.dependency_overrides[query_reader_dependency] = override_get_readable_source
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_execute_query_uses_authorized_shared_source(client, mock_data_source_service: MagicMock, mock_query_service: MagicMock) -> None:
    response = client.post("/api/v1/data-sources/requested-source/query/execute", json={"query": "SELECT id FROM table1"})

    assert response.status_code == 200
    mock_data_source_service.load_data_source.assert_called_once_with("authorized-source", strict=True)
    mock_query_service.execute_query.assert_awaited_once()


def test_introspect_query_columns_uses_authorized_shared_source(
    client, mock_data_source_service: MagicMock, mock_query_service: MagicMock
) -> None:
    response = client.post("/api/v1/data-sources/requested-source/query/columns", json={"query": "SELECT id FROM table1"})

    assert response.status_code == 200
    assert response.json() == {"columns": ["id"]}
    mock_data_source_service.load_data_source.assert_called_once_with("authorized-source", strict=True)
    mock_query_service.introspect_query_columns.assert_awaited_once()
