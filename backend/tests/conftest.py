
import pytest

from backend.app.core.config import get_settings
from backend.app.ingesters.registry import Ingesters


@pytest.fixture(scope="session", autouse=True)
def discover_ingesters():
    """Discover ingesters before running any tests (session-scoped, runs once).

    This ensures that ingesters are available for both unit and integration tests.
    """
    if not Ingesters._initialized:
        Ingesters.discover(search_paths=["ingesters"])
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
