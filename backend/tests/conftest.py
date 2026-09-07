from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.authorization.dependencies import get_authorization_service
from backend.app.authorization.repository import SQLiteAuthorizationRepository
from backend.app.authorization.service import AuthorizationService
from backend.app.core.config import get_settings
from backend.app.core.config import settings as application_settings
from backend.app.ingesters.registry import get_ingester_registry
from backend.app.main import app, lifespan


@pytest.fixture(scope="session", autouse=True)
def discover_ingesters():
    """Discover ingesters before running any tests (session-scoped, runs once).

    This ensures that ingesters are available for both unit and integration tests.
    """
    if not get_ingester_registry()._initialized:
        get_ingester_registry().discover(search_paths=["ingesters"])
    yield


@pytest.fixture
def settings(monkeypatch):

    monkeypatch.setenv("SHAPE_SHIFTER_PROJECT_NAME", "Shape Shifter Configuration Editor")
    monkeypatch.setenv("SHAPE_SHIFTER_VERSION", "0.1.0")
    monkeypatch.setenv("SHAPE_SHIFTER_ENVIRONMENT", "development")
    monkeypatch.setenv("SHAPE_SHIFTER_API_V1_PREFIX", "/api/v1")

    monkeypatch.setenv("SHAPE_SHIFTER_PROJECTS_DIR", "tests/test_data/projects")
    monkeypatch.setenv("SHAPE_SHIFTER_GLOBAL_DATA_DIR", "tests/test_data/projects/shared/shared-data")
    monkeypatch.setenv("SHAPE_SHIFTER_GLOBAL_DATA_SOURCE_DIR", "tests/test_data/projects/shared/data-sources")

    get_settings.cache_clear()  # reset the lru_cache
    cfg = get_settings()
    yield cfg
    get_settings.cache_clear()  # avoid leaking between tests


@pytest.fixture(autouse=True)
def disable_ucanaccess_jvm_startup(monkeypatch) -> None:
    """Disable process-wide runtime initialization in ordinary backend tests."""
    monkeypatch.setattr(application_settings, "UCANACCESS_JVM_STARTUP_ENABLED", False)
    monkeypatch.setattr(application_settings, "LOG_CONFIGURE_ON_STARTUP_ENABLED", False)


@pytest.fixture
async def authorized_client(tmp_path, monkeypatch) -> AsyncIterator[AsyncClient]:
    """Create an authenticated client backed by an isolated authorization store.

    The trusted test principal is a bootstrap administrator and becomes owner
    of resources it creates, so requests exercise the real authorization path.
    """
    principal_id = "test-user"
    authorization_database = tmp_path / "state" / "authorization.sqlite3"
    monkeypatch.setattr(application_settings, "PROJECTS_DIR", tmp_path)
    monkeypatch.setattr(application_settings, "AUTHORIZATION_DATABASE_PATH", authorization_database)

    repository = SQLiteAuthorizationRepository(authorization_database)
    repository.bootstrap_admins([principal_id])
    authorization_service = AuthorizationService(repository)
    previous_overrides = app.dependency_overrides.copy()

    async def override_authorization_service() -> AuthorizationService:
        return authorization_service

    app.dependency_overrides[get_authorization_service] = override_authorization_service

    async def authenticated_app(scope, receive, send) -> None:
        if scope["type"] == "http":
            scope.setdefault("state", {})["authenticated_user"] = principal_id
        await app(scope, receive, send)

    transport = ASGITransport(app=authenticated_app)
    try:
        async with (
            lifespan(app),
            AsyncClient(
                transport=transport,
                base_url="http://testserver",
                headers={application_settings.TRUSTED_PROXY_AUTH_HEADER: principal_id},
            ) as client,
        ):
            yield client
    finally:
        app.dependency_overrides = previous_overrides
        repository.close()
