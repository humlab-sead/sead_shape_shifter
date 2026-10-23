"""Integration tests for ingester API endpoints."""

from collections.abc import Iterator
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from httpx import Response

from backend.app.api.v1.endpoints.ingesters import ingester_operator_dependency, ingester_project_dependency
from backend.app.authorization.models import Principal
from backend.app.ingesters.protocol import IngesterConfig
from backend.app.ingesters.registry import get_ingester_registry
from backend.app.main import app
from backend.app.models.ingester import IngestRequest, ValidateRequest
from backend.app.services.ingester_runtime import (
    SeadChangeRequestReconciliationAdapter,
    SeadChangeRequestSimsAdapter,
    SeadChangeRequestTargetCollisionChecker,
)
from backend.app.services.ingester_service import IngesterService, get_ingester_service
from ingesters.sead_change_request.contracts import CHANGE_REQUEST_FILE_INPUT_RETIRED_MESSAGE

# pylint: disable=redefined-outer-name


@pytest.fixture(autouse=True)
def reset_ingester_registry_state() -> Iterator[None]:
    """Force ingester discovery to run for each test in this module."""
    original_initialized = get_ingester_registry()._initialized
    get_ingester_registry()._initialized = False
    yield
    get_ingester_registry()._initialized = original_initialized


@pytest.fixture
def client() -> Iterator[TestClient]:
    """Create a fresh TestClient so app startup runs inside the test."""
    previous_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[ingester_operator_dependency] = lambda: Principal(
        principal_id="test-operator",
        authentication_provider="test",
        authenticated_at=datetime.now(UTC),
    )
    # The saved-project locator applies only to the SEAD Change Request ingester.
    app.dependency_overrides[ingester_project_dependency] = lambda: None
    with TestClient(app) as test_client:
        try:
            yield test_client
        finally:
            app.dependency_overrides = previous_overrides


class TestIngestersEndpoints:
    """Test ingester API endpoints."""

    def test_list_ingesters(self, client: TestClient):
        """Test GET /api/v1/ingesters endpoint."""
        response = client.get("/api/v1/ingesters")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert all(i["key"] != "sead" for i in data)

        change_request_ingester = next((i for i in data if i["key"] == "sead_change_request"), None)
        assert change_request_ingester is not None
        assert change_request_ingester["name"] == "SEAD Change Request"
        assert change_request_ingester["supported_formats"] == []

    def test_list_ingesters_structure(self, client: TestClient):
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

    def test_validate_missing_ingester(self, client: TestClient):
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

    def test_validate_invalid_request(self, client: TestClient):
        """Test validation with invalid request body."""
        response = client.post(
            "/api/v1/ingesters/sead_change_request/validate",
            json={},  # Missing required 'source' field
        )
        assert response.status_code == 422  # Pydantic validation error

    def test_validate_rejects_retired_change_request_file_input(self, client: TestClient):
        """The shared validate route must reject the retired Change Request file input."""
        with patch("backend.app.api.v1.endpoints.ingesters.get_ingester_service") as mock_ingester_service:
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
                        "issue_identifier": "455",
                        "author": "SEAD Operator",
                    },
                    "deploy_strategy": "copy_csv",
                },
            )

        assert response.status_code == 400
        assert response.json()["detail"] == CHANGE_REQUEST_FILE_INPUT_RETIRED_MESSAGE
        mock_ingester_service.assert_not_called()

    def test_ingest_missing_ingester(self, client: TestClient):
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

    def test_ingest_invalid_request(self, client: TestClient):
        """Test ingestion with invalid request body."""
        response = client.post(
            "/api/v1/ingesters/sead_change_request/ingest",
            json={
                "source": "/path/to/file.xlsx",
                # Missing required fields: submission_name, data_types
            },
        )
        assert response.status_code == 422  # Pydantic validation error

    def test_ingest_rejects_retired_change_request_file_input(self, client: TestClient):
        """The shared ingest route must reject the retired Change Request file input."""
        with patch("backend.app.api.v1.endpoints.ingesters.get_ingester_service") as mock_ingester_service:
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
                        "issue_identifier": "455",
                        "author": "SEAD Operator",
                    },
                    "deploy_strategy": "copy_csv",
                },
            )

        assert response.status_code == 400
        assert response.json()["detail"] == CHANGE_REQUEST_FILE_INPUT_RETIRED_MESSAGE
        mock_ingester_service.assert_not_called()


class TestIngesterServiceIntegration:
    """Integration tests for IngesterService."""

    def test_service_list_ingesters(self):
        """Test that service can list ingesters."""

        ingesters = get_ingester_service().list_ingesters()
        assert len(ingesters) >= 1
        assert any(i.key == "sead_change_request" for i in ingesters)

    def test_service_create_config(self):
        """Test IngesterService._create_config method."""

        config_dict = {
            "database": {"host": "localhost", "port": 5432, "dbname": "test_db", "user": "test_user"},
            "submission_name": "test",
            "data_types": "test_type",
            "ignore_columns": ["col1", "col2"],
            "custom_param": "value",
        }

        config: IngesterConfig = get_ingester_service()._create_config(config_dict)
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
        config: IngesterConfig = get_ingester_service()._create_config({"custom_param": "value"}, key="sead_change_request")

        assert config.extra is not None
        assert isinstance(config.extra["sims_client"], SeadChangeRequestSimsAdapter)
        assert isinstance(config.extra["reconciliation_client"], SeadChangeRequestReconciliationAdapter)

    def test_service_create_config_preserves_explicit_runtime_clients(self):
        """Explicitly supplied runtime clients should not be overwritten by backend injection."""
        explicit_sims_client = object()
        explicit_reconciliation_client = object()

        config: IngesterConfig = get_ingester_service()._create_config(
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
        config: IngesterConfig = get_ingester_service()._create_config(
            {
                "database": {"host": "localhost", "port": 5432, "dbname": "test_db", "user": "test_user"},
            },
            key="sead_change_request",
        )

        assert config.extra is not None
        assert isinstance(config.extra["collision_checker"], SeadChangeRequestTargetCollisionChecker)

    def test_service_create_config_preserves_submission_context_and_deploy_strategy(self):
        """SEAD change request config should pass submission context and deploy strategy through to ingester extras."""
        config: IngesterConfig = get_ingester_service()._create_config(
            {
                "submission_name": "bugs_delivery_1",
                "data_types": "bugs",
                "submission_context": {
                    "submission_name": "bugs_delivery_1",
                    "project_name": "pilot_bugs",
                    "timestamp": "2026-06-01T09:15",
                    "datatype": "bugs",
                    "identifier": "pilot-bugs-001",
                    "issue_identifier": "455",
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

    @pytest.mark.asyncio
    async def test_service_validate_rejects_retired_change_request_input_before_preparation(self):
        """The service must stop the retired Change Request input before loading project config."""
        service = IngesterService()
        request = ValidateRequest(source="/tmp/input.xlsx", config={})

        with (
            patch.object(IngesterService, "_trusted_project_context", side_effect=AssertionError("project lookup must not run")),
            patch.object(IngesterService, "_create_config", side_effect=AssertionError("config must not be built")),
        ):
            response = await service.validate("sead_change_request", request)

        assert response.is_valid is False
        assert response.errors == [CHANGE_REQUEST_FILE_INPUT_RETIRED_MESSAGE]

    @pytest.mark.asyncio
    async def test_service_ingest_rejects_retired_change_request_input_before_preparation(self):
        """The service must stop the retired Change Request input before loading project config."""
        service = IngesterService()
        request = IngestRequest(
            source="/tmp/input.xlsx",
            config={},
            submission_name="bugs_delivery_1",
            data_types="bugs",
        )

        with (
            patch.object(IngesterService, "_trusted_project_context", side_effect=AssertionError("project lookup must not run")),
            patch.object(IngesterService, "_create_config", side_effect=AssertionError("config must not be built")),
        ):
            response = await service.ingest("sead_change_request", request)

        assert response.success is False
        assert response.records_processed == 0
        assert response.output_path is None
        assert response.error_details == CHANGE_REQUEST_FILE_INPUT_RETIRED_MESSAGE
