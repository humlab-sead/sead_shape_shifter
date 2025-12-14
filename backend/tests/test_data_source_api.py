"""
Integration tests for Data Source API endpoints

Tests the complete REST API including request/response handling, validation, and error cases.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from app.main import app
from app.models.data_source import (
    DataSourceConfig,
    DataSourceStatus,
    DataSourceTestResult,
    DataSourceType,
)
from fastapi.testclient import TestClient

client = TestClient(app)


@pytest.fixture
def mock_service():
    """Mock DataSourceService for testing."""
    with patch("app.api.v1.endpoints.data_sources.get_data_source_service") as mock:
        service = Mock()
        mock.return_value = service
        yield service


class TestListDataSources:
    """Tests for GET /api/v1/data-sources endpoint."""

    def test_list_data_sources_success(self, mock_service):
        """Should return list of data sources."""
        mock_service.list_data_sources.return_value = [
            DataSourceConfig(
                name="sead",
                driver=DataSourceType.POSTGRESQL,
                host="localhost",
                port=5432,
                database="sead",
                username="user",
            ),
            DataSourceConfig(
                name="arbodat",
                driver=DataSourceType.ACCESS,
                filename="arbodat.mdb",
            ),
        ]

        response = client.get("/api/v1/data-sources")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "sead"
        assert data[0]["driver"] == "postgresql"
        assert data[1]["name"] == "arbodat"
        assert data[1]["driver"] == "access"

    def test_list_data_sources_empty(self, mock_service):
        """Should return empty list when no data sources configured."""
        mock_service.list_data_sources.return_value = []

        response = client.get("/api/v1/data-sources")

        assert response.status_code == 200
        assert response.json() == []

    def test_list_data_sources_error(self, mock_service):
        """Should return 500 on service error."""
        mock_service.list_data_sources.side_effect = Exception("Database error")

        response = client.get("/api/v1/data-sources")

        assert response.status_code == 500
        assert "Failed to list data sources" in response.json()["detail"]


class TestGetDataSource:
    """Tests for GET /api/v1/data-sources/{name} endpoint."""

    def test_get_data_source_success(self, mock_service):
        """Should return specific data source."""
        mock_service.get_data_source.return_value = DataSourceConfig(
            name="sead",
            driver=DataSourceType.POSTGRESQL,
            host="localhost",
            port=5432,
            database="sead",
            username="user",
        )

        response = client.get("/api/v1/data-sources/sead")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "sead"
        assert data["host"] == "localhost"

    def test_get_data_source_not_found(self, mock_service):
        """Should return 404 when data source not found."""
        mock_service.get_data_source.return_value = None

        response = client.get("/api/v1/data-sources/nonexistent")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestCreateDataSource:
    """Tests for POST /api/v1/data-sources endpoint."""

    def test_create_data_source_success(self, mock_service):
        """Should create new data source."""
        mock_service.get_data_source.return_value = None  # Doesn't exist yet
        mock_service.create_data_source.return_value = None

        payload = {
            "name": "new_db",
            "driver": "postgresql",
            "host": "localhost",
            "port": 5432,
            "database": "newdb",
            "username": "user",
        }

        response = client.post("/api/v1/data-sources", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "new_db"
        mock_service.create_data_source.assert_called_once()

    def test_create_data_source_already_exists(self, mock_service):
        """Should return 400 when data source already exists."""
        mock_service.get_data_source.return_value = DataSourceConfig(
            name="existing",
            driver=DataSourceType.POSTGRESQL,
            host="localhost",
            port=5432,
            database="db",
            username="user",
        )

        payload = {
            "name": "existing",
            "driver": "postgresql",
            "host": "localhost",
            "port": 5432,
            "database": "db",
            "username": "user",
        }

        response = client.post("/api/v1/data-sources", json=payload)

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_create_data_source_invalid_port(self, mock_service):
        """Should return 422 for invalid port number."""
        payload = {
            "name": "bad_db",
            "driver": "postgresql",
            "host": "localhost",
            "port": 99999,  # Invalid
            "database": "db",
            "username": "user",
        }

        response = client.post("/api/v1/data-sources", json=payload)

        assert response.status_code == 422


class TestUpdateDataSource:
    """Tests for PUT /api/v1/data-sources/{name} endpoint."""

    def test_update_data_source_success(self, mock_service):
        """Should update existing data source."""
        mock_service.get_data_source.side_effect = [
            DataSourceConfig(
                name="sead",
                driver=DataSourceType.POSTGRESQL,
                host="localhost",
                port=5432,
                database="sead",
                username="user",
            ),
            None,  # New name doesn't exist
        ]
        mock_service.update_data_source.return_value = None

        payload = {
            "name": "sead_renamed",
            "driver": "postgresql",
            "host": "localhost",
            "port": 5432,
            "database": "sead",
            "username": "user",
        }

        response = client.put("/api/v1/data-sources/sead", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "sead_renamed"

    def test_update_data_source_not_found(self, mock_service):
        """Should return 404 when data source not found."""
        mock_service.get_data_source.return_value = None

        payload = {
            "name": "nonexistent",
            "driver": "postgresql",
            "host": "localhost",
            "port": 5432,
            "database": "db",
            "username": "user",
        }

        response = client.put("/api/v1/data-sources/nonexistent", json=payload)

        assert response.status_code == 404

    def test_update_data_source_rename_conflict(self, mock_service):
        """Should return 400 when renaming to existing name."""
        mock_service.get_data_source.side_effect = [
            DataSourceConfig(
                name="sead",
                driver=DataSourceType.POSTGRESQL,
                host="localhost",
                port=5432,
                database="sead",
                username="user",
            ),
            DataSourceConfig(  # New name already exists
                name="arbodat",
                driver=DataSourceType.ACCESS,
                filename="arbodat.mdb",
            ),
        ]

        payload = {
            "name": "arbodat",  # Trying to rename to existing
            "driver": "postgresql",
            "host": "localhost",
            "port": 5432,
            "database": "sead",
            "username": "user",
        }

        response = client.put("/api/v1/data-sources/sead", json=payload)

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]


class TestDeleteDataSource:
    """Tests for DELETE /api/v1/data-sources/{name} endpoint."""

    def test_delete_data_source_success(self, mock_service):
        """Should delete data source."""
        mock_service.get_data_source.return_value = DataSourceConfig(
            name="unused",
            driver=DataSourceType.CSV,
            filename="test.csv",
        )
        mock_service.get_status.return_value = DataSourceStatus(
            name="unused",
            is_connected=True,
            last_test_result=None,
            in_use_by_entities=[],
        )
        mock_service.delete_data_source.return_value = None

        response = client.delete("/api/v1/data-sources/unused")

        assert response.status_code == 204
        mock_service.delete_data_source.assert_called_once_with("unused")

    def test_delete_data_source_not_found(self, mock_service):
        """Should return 404 when data source not found."""
        mock_service.get_data_source.return_value = None

        response = client.delete("/api/v1/data-sources/nonexistent")

        assert response.status_code == 404

    def test_delete_data_source_in_use(self, mock_service):
        """Should return 400 when data source is in use."""
        mock_service.get_data_source.return_value = DataSourceConfig(
            name="in_use",
            driver=DataSourceType.POSTGRESQL,
            host="localhost",
            port=5432,
            database="db",
            username="user",
        )
        mock_service.get_status.return_value = DataSourceStatus(
            name="in_use",
            is_connected=True,
            last_test_result=None,
            in_use_by_entities=["entity1", "entity2"],
        )

        response = client.delete("/api/v1/data-sources/in_use")

        assert response.status_code == 400
        assert "in use by entities" in response.json()["detail"]


class TestTestConnection:
    """Tests for POST /api/v1/data-sources/{name}/test endpoint."""

    def test_test_connection_success(self, mock_service):
        """Should test connection successfully."""
        mock_service.get_data_source.return_value = DataSourceConfig(
            name="sead",
            driver=DataSourceType.POSTGRESQL,
            host="localhost",
            port=5432,
            database="sead",
            username="user",
        )

        # Mock async method
        async def mock_test():
            return DataSourceTestResult(
                success=True,
                message="Connection successful",
                connection_time_ms=45,
                metadata={"tables": 50},
            )

        mock_service.test_connection = mock_test

        response = client.post("/api/v1/data-sources/sead/test")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["connection_time_ms"] == 45

    def test_test_connection_failure(self, mock_service):
        """Should return connection test failure."""
        mock_service.get_data_source.return_value = DataSourceConfig(
            name="bad_db",
            driver=DataSourceType.POSTGRESQL,
            host="invalid-host",
            port=5432,
            database="db",
            username="user",
        )

        # Mock async method
        async def mock_test():
            return DataSourceTestResult(
                success=False,
                message="Connection refused",
                connection_time_ms=0,
            )

        mock_service.test_connection = mock_test

        response = client.post("/api/v1/data-sources/bad_db/test")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "refused" in data["message"].lower()

    def test_test_connection_not_found(self, mock_service):
        """Should return 404 when data source not found."""
        mock_service.get_data_source.return_value = None

        response = client.post("/api/v1/data-sources/nonexistent/test")

        assert response.status_code == 404


class TestGetStatus:
    """Tests for GET /api/v1/data-sources/{name}/status endpoint."""

    def test_get_status_success(self, mock_service):
        """Should return data source status."""
        mock_service.get_data_source.return_value = DataSourceConfig(
            name="sead",
            driver=DataSourceType.POSTGRESQL,
            host="localhost",
            port=5432,
            database="sead",
            username="user",
        )
        mock_service.get_status.return_value = DataSourceStatus(
            name="sead",
            is_connected=True,
            last_test_result=DataSourceTestResult(
                success=True,
                message="OK",
                connection_time_ms=30,
            ),
            in_use_by_entities=["entity1", "entity2"],
        )

        response = client.get("/api/v1/data-sources/sead/status")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "sead"
        assert data["is_connected"] is True
        assert len(data["in_use_by_entities"]) == 2

    def test_get_status_not_found(self, mock_service):
        """Should return 404 when data source not found."""
        mock_service.get_data_source.return_value = None

        response = client.get("/api/v1/data-sources/nonexistent/status")

        assert response.status_code == 404
