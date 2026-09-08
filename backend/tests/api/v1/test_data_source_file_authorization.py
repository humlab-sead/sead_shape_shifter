"""Authorization tests for data source file listing and Excel metadata endpoints.

Covers the global shared-data file library (operator-only) and project-local
files (require project read access) for:
- GET /api/v1/data-sources/files
- GET /api/v1/data-sources/excel/metadata
"""

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.api.v1.endpoints import data_sources as data_source_endpoints
from backend.app.authorization.dependencies import get_authorization_service
from backend.app.authorization.models import Grant, ResourceRecord, ResourceType
from backend.app.authorization.repository import SQLiteAuthorizationRepository
from backend.app.authorization.service import AuthorizationService
from backend.app.core.config import settings as application_settings
from backend.app.main import app
from backend.app.services.project_service import ProjectService

# pylint: disable=redefined-outer-name, unused-argument

EXCEL_FIXTURE = Path(__file__).resolve().parents[2] / "test_data" / "excel_test.xlsx"


@pytest.fixture
def repository(tmp_path):
    """Create an isolated authorization store with an operator and a project viewer."""
    auth_repository = SQLiteAuthorizationRepository(tmp_path / "authorization.sqlite3")
    auth_repository.add_application_role("operator-user", "operator", "bootstrap")

    alpha = ResourceRecord(uuid4(), ResourceType.PROJECT, "alpha")
    auth_repository.create_resource(alpha)
    auth_repository.add_grant(Grant("alice", alpha.resource_id, "viewer", datetime.now(UTC), "bootstrap"))

    yield auth_repository
    auth_repository.close()


@pytest.fixture
def environment(tmp_path, monkeypatch, repository: SQLiteAuthorizationRepository):
    """Provide an isolated file environment and real authorization checks."""
    global_dir = tmp_path / "shared-data"
    global_dir.mkdir(parents=True, exist_ok=True)
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(application_settings, "GLOBAL_DATA_DIR", global_dir)
    monkeypatch.setattr(application_settings, "PROJECTS_DIR", projects_dir)
    monkeypatch.setattr(application_settings, "APPLICATION_ROOT", tmp_path)

    # Global shared-data file library
    import shutil

    shutil.copy2(EXCEL_FIXTURE, global_dir / "global.xlsx")

    # Project "alpha" with one uploaded file beside shapeshifter.yml
    alpha_dir = projects_dir / "alpha"
    alpha_dir.mkdir(parents=True, exist_ok=True)
    (alpha_dir / "shapeshifter.yml").write_text("metadata:\n  type: project\n", encoding="utf-8")
    shutil.copy2(EXCEL_FIXTURE, alpha_dir / "local.xlsx")

    project_service = ProjectService(projects_dir=projects_dir)
    monkeypatch.setattr(data_source_endpoints, "get_project_service", lambda: project_service)

    async def override_get_authorization_service():
        auth_repository = SQLiteAuthorizationRepository(repository.path)
        try:
            yield AuthorizationService(auth_repository)
        finally:
            auth_repository.close()

    previous_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_authorization_service] = override_get_authorization_service
    yield
    app.dependency_overrides = previous_overrides


def _client_for_principal(principal_id: str | None) -> AsyncClient:
    """Create a client that optionally supplies an authenticated principal."""

    async def authenticated_app(scope, receive, send) -> None:
        if scope["type"] == "http" and principal_id is not None:
            scope.setdefault("state", {})["authenticated_user"] = principal_id
        await app(scope, receive, send)

    return AsyncClient(transport=ASGITransport(app=authenticated_app), base_url="http://testserver")


def _file_names(response) -> list[str]:
    """Return the file names from a file-listing response."""
    return [file["name"] for file in response.json()]


# GET /api/v1/data-sources/files


@pytest.mark.asyncio
async def test_data_source_files_list_requires_authentication(environment) -> None:
    async with _client_for_principal(None) as client:
        response = await client.get("/api/v1/data-sources/files")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_operator_lists_global_data_source_files(environment) -> None:
    async with _client_for_principal("operator-user") as client:
        response = await client.get("/api/v1/data-sources/files")

    assert response.status_code == 200
    assert _file_names(response) == ["global.xlsx"]


@pytest.mark.asyncio
async def test_project_reader_lists_own_project_files_without_global_files(environment) -> None:
    async with _client_for_principal("alice") as client:
        response = await client.get("/api/v1/data-sources/files", params={"project_name": "alpha"})

    assert response.status_code == 200
    assert _file_names(response) == ["local.xlsx"]


@pytest.mark.asyncio
async def test_unprivileged_principal_gets_no_files(environment) -> None:
    async with _client_for_principal("bob") as client:
        response = await client.get("/api/v1/data-sources/files", params={"project_name": "alpha"})

    assert response.status_code == 200
    assert _file_names(response) == []


@pytest.mark.asyncio
async def test_operator_without_project_grant_gets_only_global_files(environment) -> None:
    async with _client_for_principal("operator-user") as client:
        response = await client.get("/api/v1/data-sources/files", params={"project_name": "alpha"})

    assert response.status_code == 200
    assert _file_names(response) == ["global.xlsx"]


# GET /api/v1/data-sources/excel/metadata


@pytest.mark.asyncio
async def test_excel_metadata_requires_authentication(environment) -> None:
    async with _client_for_principal(None) as client:
        response = await client.get("/api/v1/data-sources/excel/metadata", params={"file": "global.xlsx"})

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_excel_metadata_global_requires_operator(environment) -> None:
    async with _client_for_principal("bob") as client:
        response = await client.get("/api/v1/data-sources/excel/metadata", params={"file": "global.xlsx", "location": "global"})

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_excel_metadata_local_requires_project_name(environment) -> None:
    async with _client_for_principal("bob") as client:
        response = await client.get("/api/v1/data-sources/excel/metadata", params={"file": "local.xlsx", "location": "local"})

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_excel_metadata_local_unauthorized_project_is_concealed(environment) -> None:
    async with _client_for_principal("bob") as client:
        response = await client.get(
            "/api/v1/data-sources/excel/metadata",
            params={"file": "local.xlsx", "location": "local", "project_name": "alpha"},
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_operator_reads_global_excel_metadata(environment) -> None:
    async with _client_for_principal("operator-user") as client:
        response = await client.get("/api/v1/data-sources/excel/metadata", params={"file": "global.xlsx", "location": "global"})

    assert response.status_code == 200
    assert isinstance(response.json()["sheets"], list)
    assert response.json()["sheets"]


@pytest.mark.asyncio
async def test_project_reader_reads_own_project_excel_metadata(environment) -> None:
    async with _client_for_principal("alice") as client:
        response = await client.get(
            "/api/v1/data-sources/excel/metadata",
            params={"file": "local.xlsx", "location": "local", "project_name": "alpha"},
        )

    assert response.status_code == 200
    assert isinstance(response.json()["sheets"], list)
    assert response.json()["sheets"]
