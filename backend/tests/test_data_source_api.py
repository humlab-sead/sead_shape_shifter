"""
Integration tests for Data Source API endpoints

Tests the complete REST API including request/response handling, validation, and error cases.
"""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from backend.app.api.dependencies import get_data_source_service
from backend.app.main import app
from backend.app.models.data_source import (
    DataSourceConfig,
    DataSourceStatus,
    DataSourceTestResult,
    DataSourceType,
)
from backend.app.services.data_source_service import DataSourceService

# pylint: disable=redefined-outer-name, unused-argument


@pytest.fixture
def mock_service() -> MagicMock:
    """Create mock schema service."""
    service = MagicMock(spec=DataSourceService)
    return service


@pytest.fixture
def client(mock_service):
    """Create test client with mocked data source service."""

    def override_get_data_source_service():
        return mock_service

    app.dependency_overrides[get_data_source_service] = override_get_data_source_service
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestListDataSources:
    """Tests for GET /api/v1/data-sources endpoint."""

    def test_list_data_sources_success(self, client, mock_service):
        """Should return list of data sources."""
        mock_service.list_data_sources.return_value = [
            DataSourceConfig(
                name="sead", driver=DataSourceType.POSTGRESQL, host="localhost", port=5432, database="sead", username="user", **{}
            ),
            DataSourceConfig(name="arbodat", driver=DataSourceType.ACCESS, filename="arbodat.mdb", **{}),
        ]

        response = client.get("/api/v1/data-sources")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "sead"
        assert data[0]["driver"] == "postgresql"
        assert data[1]["name"] == "arbodat"
        assert data[1]["driver"] == "access"

    def test_list_data_sources_empty(self, client, mock_service):
        """Should return empty list when no data sources configured."""
        mock_service.list_data_sources.return_value = []

        response = client.get("/api/v1/data-sources")

        assert response.status_code == 200
        assert response.json() == []

    def test_list_data_sources_error(self, client, mock_service):
        """Should return 500 on service error."""
        mock_service.list_data_sources.side_effect = Exception("Database error")

        response = client.get("/api/v1/data-sources")

        assert response.status_code == 500
        assert "Failed to list data sources" in response.json()["detail"]


class TestGetDataSource:
    """Tests for GET /api/v1/data-sources/{name} endpoint."""

    def test_get_data_source_success(self, client, mock_service):
        """Should return specific data source."""
        mock_service.get_data_source.return_value = DataSourceConfig(
            name="sead",
            driver=DataSourceType.POSTGRESQL,
            host="localhost",
            port=5432,
            database="sead",
            username="user",
            filename="sead-options.yml",
            **{},
        )

        response = client.get("/api/v1/data-sources/sead-options.yml")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "sead"
        assert data["host"] == "localhost"

    def test_get_data_source_not_found(self, client, mock_service):
        """Should return 404 when data source not found."""
        mock_service.get_data_source.return_value = None

        response = client.get("/api/v1/data-sources/nonexistent.yml")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestCreateDataSource:
    """Tests for POST /api/v1/data-sources endpoint."""

    def test_create_data_source_success(self, client, mock_service):
        """Should create new data source."""
        mock_service.get_data_source.return_value = None  # Doesn't exist yet

        # Mock the created config that will be returned
        created_config = DataSourceConfig(
            name="new_db",
            driver=DataSourceType.POSTGRESQL,
            host="localhost",
            port=5432,
            database="newdb",
            username="user",
            filename="new_db-options.yml",
            **{},
        )
        mock_service.create_data_source.return_value = created_config

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
        assert data["filename"] == "new_db-options.yml"
        mock_service.create_data_source.assert_called_once()

    def test_create_data_source_already_exists(self, client, mock_service):
        """Should return 400 when data source already exists."""
        # Mock that file already exists
        mock_service.get_data_source.return_value = DataSourceConfig(
            name="existing",
            driver=DataSourceType.POSTGRESQL,
            host="localhost",
            port=5432,
            database="db",
            username="user",
            filename="existing-options.yml",
            **{},
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

    def test_create_data_source_invalid_port(self, client, mock_service):
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

    def test_update_data_source_success(self, client, mock_service):
        """Should update existing data source."""
        # Mock getting the existing data source
        mock_service.get_data_source.return_value = DataSourceConfig(
            name="sead",
            driver=DataSourceType.POSTGRESQL,
            host="localhost",
            port=5432,
            database="sead",
            username="user",
            filename="sead-options.yml",
            **{},
        )

        # Mock the update to return updated config
        updated_config = DataSourceConfig(
            name="sead",
            driver=DataSourceType.POSTGRESQL,
            host="newhost",
            port=5433,
            database="sead_updated",
            username="newuser",
            filename="sead-options.yml",
            **{},
        )
        mock_service.update_data_source.return_value = updated_config

        payload = {
            "name": "sead",
            "driver": "postgresql",
            "host": "newhost",
            "port": 5433,
            "database": "sead_updated",
            "username": "newuser",
        }

        response = client.put("/api/v1/data-sources/sead-options.yml", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["host"] == "newhost"
        assert data["port"] == 5433
        assert data["database"] == "sead_updated"

    def test_update_data_source_not_found(self, client, mock_service):
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

        response = client.put("/api/v1/data-sources/nonexistent-options.yml", json=payload)

        assert response.status_code == 404

    def test_update_data_source_invalid_config(self, client, mock_service):
        """Should return 400 when update fails due to invalid configuration."""
        mock_service.get_data_source.return_value = DataSourceConfig(
            name="sead",
            driver=DataSourceType.POSTGRESQL,
            host="localhost",
            port=5432,
            database="sead",
            username="user",
            filename="sead-options.yml",
            **{},
        )
        mock_service.update_data_source.side_effect = Exception("Invalid configuration")

        payload = {
            "name": "sead",
            "driver": "postgresql",
            "host": "localhost",
            "port": 5432,
            "database": "sead",
            "username": "user",
        }

        response = client.put("/api/v1/data-sources/sead-options.yml", json=payload)

        assert response.status_code == 400
        assert "Failed to update data source" in response.json()["detail"]


class TestDeleteDataSource:
    """Tests for DELETE /api/v1/data-sources/{name} endpoint."""

    def test_delete_data_source_success(self, client, mock_service):
        """Should delete data source."""
        from pathlib import Path

        mock_service.get_data_source.return_value = DataSourceConfig(
            name="unused", driver=DataSourceType.CSV, filename="unused-datasource.yml", **{}
        )
        mock_service.delete_data_source.return_value = None

        response = client.delete("/api/v1/data-sources/unused-datasource.yml")

        assert response.status_code == 204
        # Check that delete was called with a Path object
        mock_service.delete_data_source.assert_called_once()
        call_args = mock_service.delete_data_source.call_args[0]
        assert isinstance(call_args[0], Path)
        assert str(call_args[0]) == "unused-datasource.yml"

    def test_delete_data_source_not_found(self, client, mock_service):
        """Should return 404 when data source not found."""
        mock_service.get_data_source.return_value = None

        response = client.delete("/api/v1/data-sources/nonexistent.yml")

        assert response.status_code == 404

    def test_delete_data_source_service_error(self, client, mock_service):
        """Should return 500 when service fails to delete."""
        mock_service.get_data_source.return_value = DataSourceConfig(
            name="error_case",
            driver=DataSourceType.POSTGRESQL,
            host="localhost",
            port=5432,
            database="db",
            username="user",
            filename="error_case-options.yml",
            **{},
        )
        mock_service.delete_data_source.side_effect = Exception("Failed to delete file")

        response = client.delete("/api/v1/data-sources/error_case-options.yml")

        assert response.status_code == 500
        assert "Failed to delete data source" in response.json()["detail"]


class TestTestConnection:
    """Tests for POST /api/v1/data-sources/{name}/test endpoint."""

    def test_test_connection_success(self, client, mock_service):
        """Should test connection successfully."""
        mock_service.get_data_source.return_value = DataSourceConfig(
            name="sead",
            driver=DataSourceType.POSTGRESQL,
            host="localhost",
            port=5432,
            database="sead",
            username="user",
            filename="sead-options.yml",
            **{},
        )

        # Mock async method
        async def mock_test(config: DataSourceConfig) -> DataSourceTestResult:
            return DataSourceTestResult(
                success=True,
                message="Connection successful",
                connection_time_ms=45,
                metadata={"tables": 50},
            )

        mock_service.test_connection = mock_test

        response = client.post("/api/v1/data-sources/sead-options.yml/test")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["connection_time_ms"] == 45

    def test_test_connection_failure(self, client, mock_service):
        """Should return connection test failure."""
        mock_service.get_data_source.return_value = DataSourceConfig(
            name="bad_db",
            driver=DataSourceType.POSTGRESQL,
            host="invalid-host",
            port=5432,
            database="db",
            username="user",
            filename="bad_db-options.yml",
            **{},
        )

        # Mock async method
        async def mock_test(config: DataSourceConfig) -> DataSourceTestResult:
            return DataSourceTestResult(
                success=False,
                message="Connection refused",
                connection_time_ms=0,
                metadata=None,
            )

        mock_service.test_connection = mock_test

        response = client.post("/api/v1/data-sources/bad_db-options.yml/test")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "refused" in data["message"].lower()

    def test_test_connection_not_found(self, client, mock_service):
        """Should return 404 when data source not found."""
        mock_service.get_data_source.return_value = None

        response = client.post("/api/v1/data-sources/nonexistent.yml/test")

        assert response.status_code == 404


class TestGetStatus:
    """Tests for GET /api/v1/data-sources/{name}/status endpoint."""

    def test_get_status_success(self, client, mock_service):
        """Should return data source status."""
        mock_service.get_data_source.return_value = DataSourceConfig(
            name="sead",
            driver=DataSourceType.POSTGRESQL,
            host="localhost",
            port=5432,
            database="sead",
            username="user",
            filename="sead-options.yml",
            **{},
        )
        mock_service.get_status.return_value = DataSourceStatus(
            name="sead",
            is_connected=True,
            last_test_result=DataSourceTestResult(success=True, message="OK", connection_time_ms=30, metadata=None),
            in_use_by_entities=["entity1", "entity2"],
        )

        response = client.get("/api/v1/data-sources/sead-options.yml/status")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "sead"
        assert data["is_connected"] is True
        assert len(data["in_use_by_entities"]) == 2

    def test_get_status_not_found(self, client, mock_service):
        """Should return 404 when data source not found."""
        mock_service.get_data_source.return_value = None

        response = client.get("/api/v1/data-sources/nonexistent.yml/status")

        assert response.status_code == 404
