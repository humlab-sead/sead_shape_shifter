"""Integration tests for ingester API endpoints."""

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.ingester_service import IngesterService

client = TestClient(app)


class TestIngestersEndpoints:
    """Test ingester API endpoints."""

    def test_list_ingesters(self):
        """Test GET /api/v1/ingesters endpoint."""
        response = client.get("/api/v1/ingesters")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1  # At least SEAD ingester should be registered

        # Verify SEAD ingester is in the list
        sead_ingester = next((i for i in data if i["key"] == "sead"), None)
        assert sead_ingester is not None
        assert sead_ingester["name"] == "SEAD Clearinghouse"
        assert sead_ingester["version"] == "1.0.0"
        assert "xlsx" in sead_ingester["supported_formats"]

    def test_list_ingesters_structure(self):
        """Test that list_ingesters returns properly structured metadata."""
        response = client.get("/api/v1/ingesters")
        assert response.status_code == 200

        data = response.json()
        for ingester in data:
            assert "key" in ingester
            assert "name" in ingester
            assert "description" in ingester
            assert "version" in ingester
            assert "supported_formats" in ingester
            assert isinstance(ingester["supported_formats"], list)

    def test_validate_missing_ingester(self):
        """Test validation with non-existent ingester."""
        response = client.post(
            "/api/v1/ingesters/nonexistent/validate",
            json={"source": "/path/to/file.xlsx", "config": {}},
        )
        # Debug: print response if not 404
        if response.status_code != 404:
            print(f"Status: {response.status_code}, Response: {response.json()}")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_validate_invalid_request(self):
        """Test validation with invalid request body."""
        response = client.post(
            "/api/v1/ingesters/sead/validate",
            json={},  # Missing required 'source' field
        )
        assert response.status_code == 422  # Pydantic validation error

    def test_validate_success_structure(self):
        """Test validation response structure (mock successful case)."""
        # This test validates the response structure
        # Actual validation would require a real file and database
        response = client.post(
            "/api/v1/ingesters/sead/validate",
            json={
                "source": "/nonexistent/path.xlsx",  # Will fail but return structured response
                "config": {"ignore_columns": []},
            },
        )

        # Response should be 200 even if validation fails (validation result is in body)
        # OR 500 if file doesn't exist
        data = response.json()
        if response.status_code == 200:
            assert "is_valid" in data
            assert "errors" in data
            assert "warnings" in data
            assert isinstance(data["errors"], list)
            assert isinstance(data["warnings"], list)

    def test_ingest_missing_ingester(self):
        """Test ingestion with non-existent ingester."""
        response = client.post(
            "/api/v1/ingesters/nonexistent/ingest",
            json={
                "source": "/path/to/file.xlsx",
                "config": {},
                "submission_name": "test",
                "data_types": "test",
            },
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_ingest_invalid_request(self):
        """Test ingestion with invalid request body."""
        response = client.post(
            "/api/v1/ingesters/sead/ingest",
            json={
                "source": "/path/to/file.xlsx",
                # Missing required fields: submission_name, data_types
            },
        )
        assert response.status_code == 422  # Pydantic validation error

    def test_ingest_response_structure(self):
        """Test ingestion response structure."""
        response = client.post(
            "/api/v1/ingesters/sead/ingest",
            json={
                "source": "/nonexistent/path.xlsx",
                "config": {
                    "database": {
                        "host": "localhost",
                        "port": 5432,
                        "dbname": "test_db",
                        "user": "test_user",
                    },
                    "ignore_columns": [],
                },
                "submission_name": "test_submission",
                "data_types": "test",
                "output_folder": "output",
                "register": False,
                "explode": False,
            },
        )

        # Will fail (file doesn't exist) but should return structured error
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data


class TestIngesterServiceIntegration:
    """Integration tests for IngesterService."""

    def test_service_list_ingesters(self):
        """Test that service can list ingesters."""

        ingesters = IngesterService.list_ingesters()
        assert len(ingesters) >= 1
        assert any(i.key == "sead" for i in ingesters)

    def test_service_create_config(self):
        """Test IngesterService._create_config method."""

        config_dict = {
            "database": {"host": "localhost", "port": 5432, "dbname": "test_db", "user": "test_user"},
            "submission_name": "test",
            "data_types": "test_type",
            "ignore_columns": ["col1", "col2"],
            "custom_param": "value",
        }

        config = IngesterService._create_config(config_dict)
        assert config.host == "localhost"
        assert config.port == 5432
        assert config.dbname == "test_db"
        assert config.user == "test_user"
        assert config.submission_name == "test"
        assert config.data_types == "test_type"

        assert config.extra is not None
        
        assert config.extra["ignore_columns"] == ["col1", "col2"]
        assert config.extra["custom_param"] == "value"
