"""Authorization and response tests for project-only ingester routes."""

from collections.abc import Iterator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.api.v1.endpoints import ingesters as ingester_endpoints
from backend.app.api.v1.endpoints import projects as project_endpoints
from backend.app.authorization.dependencies import get_authorization_service
from backend.app.authorization.models import Grant, ResourceType
from backend.app.authorization.repository import SQLiteAuthorizationRepository
from backend.app.authorization.service import AuthorizationService
from backend.app.core.config import settings
from backend.app.main import app
from backend.app.models.ingester import IngestResponse, ProjectIngesterRequest, ValidateResponse
from backend.app.services.project_service import ProjectService

VALIDATE_PATH = "/api/v1/ingesters/sead_change_request/from-project/validate"
INGEST_PATH = "/api/v1/ingesters/sead_change_request/from-project/ingest"
PROJECT_REQUEST = {
    "project_name": "project-a",
    "submission_context": {
        "submission_name": "project_a_bugs",
        "timestamp": "2026-10-19T12:00:00",
        "datatype": "bugs",
        "identifier": "PROJECT_A",
    },
}


@pytest.fixture(name="authorization_repository")
def _authorization_repository(tmp_path, monkeypatch) -> Iterator[SQLiteAuthorizationRepository]:
    """Create an isolated authorization store and project directory."""
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()
    repository = SQLiteAuthorizationRepository(tmp_path / "authorization.sqlite3")
    repository.add_application_role("project-admin", "admin", "bootstrap")

    async def get_test_authorization_service() -> AuthorizationService:
        return AuthorizationService(repository)

    previous_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_authorization_service] = get_test_authorization_service
    monkeypatch.setattr(settings, "PROJECTS_DIR", projects_dir)
    monkeypatch.setattr(project_endpoints, "get_project_service", lambda: ProjectService(projects_dir=projects_dir))
    try:
        yield repository
    finally:
        app.dependency_overrides = previous_overrides
        repository.close()


def client_for_principal(principal_id: str | None) -> AsyncClient:
    """Create an ASGI client authenticated as the requested principal."""

    async def authenticated_app(scope, receive, send) -> None:
        if scope["type"] == "http" and principal_id is not None:
            scope.setdefault("state", {})["authenticated_user"] = principal_id
        await app(scope, receive, send)

    return AsyncClient(transport=ASGITransport(app=authenticated_app), base_url="http://testserver")


async def create_project(name: str = "project-a") -> None:
    """Register a project through the public project endpoint."""
    async with client_for_principal("project-admin") as client:
        response = await client.post(
            "/api/v1/projects",
            json={
                "name": name,
                "data_provider_code": "test-provider",
                "provider_schema": "schema-one",
                "entities": {},
            },
        )
    assert response.status_code == 201


def install_project_ingester_stub(monkeypatch, **methods: AsyncMock) -> Mock:
    """Replace the project helper dependency with asynchronous method stubs."""
    service = Mock()
    for name, method in methods.items():
        setattr(service, name, method)
    monkeypatch.setitem(app.dependency_overrides, ingester_endpoints.get_project_ingester_service, lambda: service)
    return service


@pytest.mark.parametrize("path,method_name", [(VALIDATE_PATH, "validate_project_tables"), (INGEST_PATH, "ingest_project_tables")])
@pytest.mark.parametrize(
    "principal_id,expected_status",
    [
        (None, 401),
        ("project-executor", 403),
        ("project-operator", 404),
        ("project-viewer", 404),
    ],
)
async def test_project_routes_require_authentication_and_both_permissions(
    authorization_repository: SQLiteAuthorizationRepository,
    monkeypatch,
    path: str,
    method_name: str,
    principal_id: str | None,
    expected_status: int,
) -> None:
    """Deny unauthenticated callers and callers missing either required permission."""
    await create_project()
    resource = authorization_repository.get_resource_by_locator(ResourceType.PROJECT, "project-a")
    assert resource is not None
    now = datetime.now(UTC)
    authorization_repository.add_grant(Grant("project-executor", resource.resource_id, "executor", now, "bootstrap"))
    authorization_repository.add_grant(Grant("project-viewer", resource.resource_id, "viewer", now, "bootstrap"))
    authorization_repository.add_application_role("project-operator", "operator", "bootstrap")
    authorization_repository.add_application_role("project-viewer", "operator", "bootstrap")

    helper_method = AsyncMock()
    install_project_ingester_stub(monkeypatch, **{method_name: helper_method})
    async with client_for_principal(principal_id) as client:
        response = await client.post(path, json=PROJECT_REQUEST)

    assert response.status_code == expected_status
    helper_method.assert_not_awaited()


@pytest.mark.parametrize(
    "path,method_name,response_model",
    [
        (
            VALIDATE_PATH,
            "validate_project_tables",
            ValidateResponse(is_valid=True, errors=[], warnings=["Project has warnings"], infos=["Validated"]),
        ),
        (
            INGEST_PATH,
            "ingest_project_tables",
            IngestResponse(
                success=True,
                records_processed=3,
                message="Bundle created",
                submission_id=14,
                output_path=None,
                deploy_artifact={"bundle_files": {"deploy.sql": "SQL"}},
            ),
        ),
    ],
)
async def test_project_routes_forward_authorized_resource_request_and_response(
    authorization_repository: SQLiteAuthorizationRepository,  # pylint: disable=unused-argument
    monkeypatch,
    path: str,
    method_name: str,
    response_model: ValidateResponse | IngestResponse,
) -> None:
    """Forward the fixed ingester key, exact authorized project, typed request, and helper response."""
    await create_project()
    helper_method = AsyncMock(return_value=response_model)
    install_project_ingester_stub(monkeypatch, **{method_name: helper_method})

    async with client_for_principal("project-admin") as client:
        response = await client.post(path, json=PROJECT_REQUEST)

    assert response.status_code == 200
    assert response.json() == response_model.model_dump()
    helper_method.assert_awaited_once()
    ingester_key, authorized_project, request = helper_method.await_args.args
    assert ingester_key == "sead_change_request"
    assert authorized_project.resource.locator == "project-a"
    assert isinstance(request, ProjectIngesterRequest)
    assert request.project_name == "project-a"


@pytest.mark.parametrize("path,method_name", [(VALIDATE_PATH, "validate_project_tables"), (INGEST_PATH, "ingest_project_tables")])
@pytest.mark.parametrize(
    "extra_fields",
    [
        {"source": "/tmp/input.xlsx"},
        {"config": {}},
        {"output_folder": "/tmp/output"},
        {"target_model": "caller.yml"},
        {"database": {"host": "caller"}},
        {"data_provider_code": "caller"},
        {"run_validation": True},
        {"validate_first": False},
        {"submission_context": {**PROJECT_REQUEST["submission_context"], "project_name": "project-a"}},
        {"submission_context": {**PROJECT_REQUEST["submission_context"], "data_provider_code": "caller"}},
    ],
)
async def test_project_routes_reject_file_and_caller_configuration_fields(
    authorization_repository: SQLiteAuthorizationRepository,  # pylint: disable=unused-argument
    monkeypatch,
    path: str,
    method_name: str,
    extra_fields: dict[str, object],
) -> None:
    """Reject source paths and arbitrary fields at both the top level and nested context."""
    await create_project()
    helper_method = AsyncMock()
    install_project_ingester_stub(monkeypatch, **{method_name: helper_method})
    request = {**PROJECT_REQUEST, **extra_fields}

    async with client_for_principal("project-admin") as client:
        response = await client.post(path, json=request)

    assert response.status_code == 422
    helper_method.assert_not_awaited()


@pytest.mark.parametrize(
    "path,method_name",
    [(VALIDATE_PATH, "validate_project_tables"), (INGEST_PATH, "ingest_project_tables")],
)
async def test_project_route_query_body_mismatch_is_concealed_before_project_work(
    authorization_repository: SQLiteAuthorizationRepository,  # pylint: disable=unused-argument
    monkeypatch,
    path: str,
    method_name: str,
) -> None:
    """The helper rejects a query-authorized project that differs from the typed body locator."""
    await create_project()
    await create_project("project-b")
    helper_method = AsyncMock(side_effect=PermissionError("Requested project does not match the authorized project"))
    install_project_ingester_stub(monkeypatch, **{method_name: helper_method})

    async with client_for_principal("project-admin") as client:
        response = await client.post(path, params={"project_name": "project-b"}, json=PROJECT_REQUEST)

    assert response.status_code == 404
    assert response.json()["detail"] == "Resource not found"
    helper_method.assert_awaited_once()
    assert helper_method.await_args is not None
    _, authorized_project, request = helper_method.await_args.args
    assert authorized_project.resource.locator == "project-b"
    assert request.project_name == "project-a"


@pytest.mark.parametrize(
    "path,method_name,response_model",
    [
        (
            VALIDATE_PATH,
            "validate_project_tables",
            ValidateResponse(is_valid=False, errors=["Project specification failed"], warnings=[], infos=[]),
        ),
        (
            INGEST_PATH,
            "ingest_project_tables",
            IngestResponse(
                success=False,
                records_processed=0,
                message="Ingester data validation failed",
                output_path=None,
                error_details="Invalid normalized rows",
                deploy_artifact=None,
            ),
        ),
    ],
)
async def test_project_routes_preserve_project_and_data_validation_failures(
    authorization_repository: SQLiteAuthorizationRepository,  # pylint: disable=unused-argument
    monkeypatch,
    path: str,
    method_name: str,
    response_model: ValidateResponse | IngestResponse,
) -> None:
    """Return helper validation failures through the existing response models unchanged."""
    await create_project()
    helper_method = AsyncMock(return_value=response_model)
    install_project_ingester_stub(monkeypatch, **{method_name: helper_method})

    async with client_for_principal("project-admin") as client:
        response = await client.post(path, json=PROJECT_REQUEST)

    assert response.status_code == 200
    assert response.json() == response_model.model_dump()
    helper_method.assert_awaited_once()
