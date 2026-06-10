"""Integration tests for ingester API endpoints."""

from fastapi.testclient import TestClient
from httpx import Response

from backend.app.main import app
from backend.app.models.ingester import IngestRequest, IngestResponse, ValidateRequest, ValidateResponse
from backend.app.services.ingester_runtime import (
    SeadChangeRequestReconciliationAdapter,
    SeadChangeRequestSimsAdapter,
    SeadChangeRequestTargetCollisionChecker,
)
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
            assert "infos" in data
            assert "pending_confirmation_report" in data
            assert isinstance(data["errors"], list)
            assert isinstance(data["warnings"], list)
            assert isinstance(data["infos"], list)

    def test_validate_passes_submission_context_and_deploy_strategy_to_service(self, monkeypatch):
        """Validate route should preserve change-request payload fields when calling the service."""
        captured: dict[str, str | ValidateRequest] = {}

        async def fake_validate(key: str, request: ValidateRequest) -> ValidateResponse:
            captured["key"] = key
            captured["request"] = request
            return ValidateResponse(
                is_valid=True,
                errors=[],
                warnings=[],
                infos=[],
                pending_confirmation_report=None,
            )

        monkeypatch.setattr(IngesterService, "validate", staticmethod(fake_validate))

        response = client.post(
            "/api/v1/ingesters/sead_change_request/validate",
            json={
                "source": "/tmp/input.xlsx",
                "config": {"ignore_columns": ["date_updated"]},
                "submission_context": {
                    "submission_name": "bugs_delivery_1",
                    "project_name": "pilot_bugs",
                    "timestamp": "2026-06-01T09:15",
                    "datatype": "bugs",
                    "identifier": "PILOT_BUGS",
                    "description": "Pilot bugs change package",
                    "issue_number": "455",
                    "author": "SEAD Operator",
                },
                "deploy_strategy": "copy_csv",
            },
        )

        assert response.status_code == 200
        assert captured["key"] == "sead_change_request"

        request: ValidateRequest | str = captured["request"]

        assert isinstance(request, ValidateRequest)

        assert request.submission_context is not None
        assert request.submission_context["project_name"] == "pilot_bugs"
        assert request.submission_context["identifier"] == "PILOT_BUGS"
        assert request.deploy_strategy == "copy_csv"

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

        # Will fail (file doesn't exist) but should return a structured ingestion response
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "message" in data
        assert "error_details" in data
        assert "deploy_artifact" in data
        assert "pending_confirmation_report" in data
        assert data["success"] is False

    def test_ingest_passes_submission_context_and_deploy_strategy_to_service(self, monkeypatch):
        """Ingest route should preserve change-request payload fields when calling the service."""
        captured: dict[str, str | IngestRequest] = {}

        async def fake_ingest(key: str, request: IngestRequest) -> IngestResponse:
            captured["key"] = key
            captured["request"] = request
            return IngestResponse(
                success=True,
                records_processed=2,
                message="ok",
                submission_id=11,
                output_path="output/pilot-bugs-001",
                error_details=None,
                deploy_artifact=None,
                pending_confirmation_report=None,
            )

        monkeypatch.setattr(IngesterService, "ingest", staticmethod(fake_ingest))

        response: Response = client.post(
            "/api/v1/ingesters/sead_change_request/ingest",
            json={
                "source": "/tmp/input.xlsx",
                "config": {"ignore_columns": ["date_updated"]},
                "submission_name": "bugs_delivery_1",
                "data_types": "bugs",
                "output_folder": "output",
                "do_register": False,
                "explode": False,
                "submission_context": {
                    "submission_name": "bugs_delivery_1",
                    "project_name": "pilot_bugs",
                    "timestamp": "2026-06-01T09:15",
                    "datatype": "bugs",
                    "identifier": "PILOT_BUGS",
                    "description": "Pilot bugs change package",
                    "issue_number": "455",
                    "author": "SEAD Operator",
                },
                "deploy_strategy": "copy_csv",
            },
        )

        assert response.status_code == 200
        assert captured["key"] == "sead_change_request"

        request: IngestRequest | str = captured["request"]
        assert isinstance(request, IngestRequest)

        assert request.submission_name == "bugs_delivery_1"
        assert request.data_types == "bugs"
        assert request.submission_context is not None
        assert request.submission_context["project_name"] == "pilot_bugs"
        assert request.submission_context["identifier"] == "PILOT_BUGS"
        assert request.deploy_strategy == "copy_csv"


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

    def test_service_create_config_injects_sead_change_request_runtime_clients(self):
        """SEAD change request runtime clients should be injected at the backend service boundary."""
        config = IngesterService._create_config({"custom_param": "value"}, key="sead_change_request")

        assert config.extra is not None
        assert isinstance(config.extra["sims_client"], SeadChangeRequestSimsAdapter)
        assert isinstance(config.extra["reconciliation_client"], SeadChangeRequestReconciliationAdapter)

    def test_service_create_config_preserves_explicit_runtime_clients(self):
        """Explicitly supplied runtime clients should not be overwritten by backend injection."""
        explicit_sims_client = object()
        explicit_reconciliation_client = object()

        config = IngesterService._create_config(
            {
                "sims_client": explicit_sims_client,
                "reconciliation_client": explicit_reconciliation_client,
            },
            key="sead_change_request",
        )

        assert config.extra is not None
        assert config.extra["sims_client"] is explicit_sims_client
        assert config.extra["reconciliation_client"] is explicit_reconciliation_client

    def test_service_create_config_injects_collision_checker_when_database_config_present(self):
        """SEAD change request config should inject a DB-backed collision checker when DB config is available."""
        config = IngesterService._create_config(
            {
                "database": {"host": "localhost", "port": 5432, "dbname": "test_db", "user": "test_user"},
            },
            key="sead_change_request",
        )

        assert config.extra is not None
        assert isinstance(config.extra["collision_checker"], SeadChangeRequestTargetCollisionChecker)

    def test_service_create_config_preserves_submission_context_and_deploy_strategy(self):
        """SEAD change request config should pass submission context and deploy strategy through to ingester extras."""
        config = IngesterService._create_config(
            {
                "submission_name": "bugs_delivery_1",
                "data_types": "bugs",
                "submission_context": {
                    "submission_name": "bugs_delivery_1",
                    "project_name": "pilot_bugs",
                    "timestamp": "2026-06-01T09:15",
                    "datatype": "bugs",
                    "identifier": "pilot-bugs-001",
                    "issue_number": "455",
                },
                "deploy_strategy": "copy_csv",
            },
            key="sead_change_request",
        )

        assert config.submission_name == "bugs_delivery_1"
        assert config.data_types == "bugs"
        assert config.extra is not None
        assert config.extra["deploy_strategy"] == "copy_csv"
        assert config.extra["submission_context"]["project_name"] == "pilot_bugs"
        assert config.extra["submission_context"]["identifier"] == "pilot-bugs-001"
