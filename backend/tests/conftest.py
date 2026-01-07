import pytest

from backend.app.core.config import get_settings


@pytest.fixture
def settings(monkeypatch):

    monkeypatch.setenv("SHAPE_SHIFTER_PROJECT_NAME", "Shape Shifter Configuration Editor")
    monkeypatch.setenv("SHAPE_SHIFTER_VERSION", "0.1.0")
    monkeypatch.setenv("SHAPE_SHIFTER_ENVIRONMENT", "development")
    monkeypatch.setenv("SHAPE_SHIFTER_API_V1_PREFIX", "/api/v1")

    monkeypatch.setenv("SHAPE_SHIFTER_CONFIGURATIONS_DIR", "backend/tests/test_data/configurations")
    monkeypatch.setenv("SHAPE_SHIFTER_BACKUPS_DIR", "backend/tests/test_data/backups")

    monkeypatch.setenv("SHAPE_SHIFTER_MAX_ENTITIES_PER_CONFIG", "1000")
    monkeypatch.setenv("SHAPE_SHIFTER_MAX_CONFIG_FILE_SIZE_MB", "10")

    get_settings.cache_clear()  # reset the lru_cache
    cfg = get_settings()
    yield cfg
    get_settings.cache_clear()  # avoid leaking between tests
