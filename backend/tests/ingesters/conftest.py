"""Test fixtures and utilities for ingester tests."""

import pytest

from backend.app.ingesters import IngesterConfig
from backend.app.ingesters.registry import Ingesters


@pytest.fixture(scope="session", autouse=True)
def discover_ingesters():
    """Discover ingesters before running tests (session-scoped, runs once)."""
    if not Ingesters._initialized:
        Ingesters.discover(search_paths=["ingesters"])
    yield


@pytest.fixture
def basic_ingester_config() -> IngesterConfig:
    """Provide a basic ingester configuration for testing."""
    return IngesterConfig(
        host="localhost",
        port=5432,
        dbname="test_db",
        user="test_user",
        password="test_password",
        submission_name="test_submission",
        data_types="test",
    )


@pytest.fixture
def ingester_config_with_extras() -> IngesterConfig:
    """Provide an ingester configuration with extra options."""
    return IngesterConfig(
        host="localhost",
        port=5432,
        dbname="test_db",
        user="test_user",
        submission_name="test_submission",
        data_types="test",
        extra={
            "ignore_columns": ["date_updated", "*_uuid"],
            "custom_option": "value",
        },
    )
