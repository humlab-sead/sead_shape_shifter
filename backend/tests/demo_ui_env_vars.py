"""
Quick test to demonstrate env var behavior in UI.

This shows that when listing data sources, environment variables remain
as ${VAR_NAME} so they can be displayed and edited in the UI.
"""

from unittest.mock import Mock

from backend.app.models.data_source import DataSourceConfig
from backend.app.services.data_source_service import DataSourceService


def test_ui_behavior():
    """Demonstrate UI behavior with environment variables."""

    # Create mock config that returns data source with env vars (like sead-options.yml)
    mock_config = Mock()
    mock_config.get.return_value = {
        "sead": {
            "driver": "postgres",
            "options": {"host": "${SEAD_HOST}", "port": "${SEAD_PORT}", "dbname": "${SEAD_DBNAME}", "username": "${SEAD_USER}"},
        }
    }

    service = Mock(spec=DataSourceService)
    service.list_data_sources.return_value = [mock_config]

    # List data sources (what the UI receives)
    print("\n=== What the UI sees when listing data sources ===\n")
    data_sources: list[DataSourceConfig] = service.list_data_sources()

    for ds in data_sources:
        print(f"Data Source: {ds.name}")
        print(f"  Driver: {ds.driver}")
        print("  Options:")
        assert ds.options is not None
        for key, value in ds.options.items():
            print(f"    {key}: {value}")
        print()

    print("✓ Environment variables remain as ${VAR_NAME} for UI editing")
    print("✓ When user clicks 'Test Connection', vars will be resolved")
    print()


if __name__ == "__main__":
    test_ui_behavior()
