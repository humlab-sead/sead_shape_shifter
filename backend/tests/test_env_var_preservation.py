"""Test that environment variables are preserved in data source listings."""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest
import yaml

from backend.app.models.data_source import DataSourceConfig
from backend.app.services.data_source_service import DataSourceService


def test_list_data_sources_preserves_env_vars():
    """Verify that env vars like ${SEAD_HOST} are preserved when listing data sources."""

    # Create a temporary YAML config file with env vars
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        config_content = {
            "options": {
                "data_sources": {
                    "test_db": {
                        "driver": "postgresql",
                        "options": {
                            "host": "${TEST_HOST}",
                            "port": "${TEST_PORT}",
                            "database": "${TEST_DB}",
                            "username": "${TEST_USER}",
                        },
                    }
                }
            }
        }
        yaml.dump(config_content, f)
        config_path = Path(f.name)

    try:
        # Create mock config that points to our temp file
        mock_config = Mock()
        mock_config.filename = str(config_path)
        mock_config.get.return_value = {}

        # Create service
        service = DataSourceService(mock_config)

        # List data sources - should preserve env vars
        data_sources = service.list_data_sources()

        assert len(data_sources) == 1
        ds = data_sources[0]
        assert ds.name == "test_db"
        assert ds.options is not None

        # Verify env vars are preserved (not resolved)
        assert ds.options["host"] == "${TEST_HOST}"
        assert ds.options["port"] == "${TEST_PORT}"
        assert ds.options["database"] == "${TEST_DB}"
        assert ds.options["username"] == "${TEST_USER}"

        print("✓ Environment variables preserved in listing")

    finally:
        # Clean up
        config_path.unlink()


def test_list_data_sources_with_include():
    """Test that @include directives are followed to read raw data."""

    # Create temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create included data source file (like sead-options.yml)
        sead_options_path = tmpdir_path / "sead-options.yml"
        with open(sead_options_path, "w", encoding="utf-8") as f:
            yaml.dump(
                {
                    "driver": "postgres",
                    "options": {
                        "host": "${SEAD_HOST}",
                        "port": "${SEAD_PORT}",
                        "dbname": "${SEAD_DBNAME}",
                        "username": "${SEAD_USER}",
                    },
                },
                f,
            )

        # Create main config file with @include
        main_config_path = tmpdir_path / "main.yml"
        with open(main_config_path, "w", encoding="utf-8") as f:
            f.write(
                """options:
  data_sources:
    sead: "@include: sead-options.yml"
"""
            )

        # Create mock config
        mock_config = Mock()
        mock_config.filename = str(main_config_path)
        mock_config.get.return_value = {}

        # Create service
        service = DataSourceService(mock_config)

        # List data sources
        data_sources = service.list_data_sources()

        assert len(data_sources) == 1
        ds: DataSourceConfig = data_sources[0]
        assert ds.name == "sead"
        assert ds.options is not None

        # Verify env vars from included file are preserved
        assert ds.options["host"] == "${SEAD_HOST}"
        assert ds.options["port"] == "${SEAD_PORT}"
        assert ds.options["dbname"] == "${SEAD_DBNAME}"
        assert ds.options["username"] == "${SEAD_USER}"

        print("✓ Environment variables preserved from @include files")


@pytest.mark.asyncio
async def test_env_vars_resolved_during_connection_test():
    """Verify that env vars ARE resolved when testing connections."""

    # Set test env vars
    os.environ["TEST_CONN_HOST"] = "localhost"
    os.environ["TEST_CONN_PORT"] = "5432"

    try:
        # Create a temporary YAML config file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            config_content = {
                "options": {
                    "data_sources": {
                        "test_db": {
                            "driver": "postgresql",
                            "options": {
                                "host": "${TEST_CONN_HOST}",
                                "port": "${TEST_CONN_PORT}",
                                "database": "testdb",
                                "username": "testuser",
                            },
                        }
                    }
                }
            }
            yaml.dump(config_content, f)
            config_path = Path(f.name)

        try:
            # Create mock config
            mock_config = Mock()
            mock_config.filename = str(config_path)
            mock_config.get.return_value = {}

            # Create service
            service = DataSourceService(mock_config)

            # Get the data source
            data_sources = service.list_data_sources()
            assert len(data_sources) == 1
            ds: DataSourceConfig = data_sources[0]
            assert ds.options is not None

            # Verify env vars are NOT resolved in listing
            assert ds.options["host"] == "${TEST_CONN_HOST}"
            assert ds.options["port"] == "${TEST_CONN_PORT}"

            # Now test connection - env vars should be resolved
            # (Connection will fail, but we're testing env var resolution)
            result = await service.test_connection(ds)

            # If the error message contains the resolved values, env vars were resolved
            # (We expect connection to fail since there's no actual DB, but that's OK)
            assert not result.success  # Connection should fail
            # Error message should contain resolved host, not ${TEST_CONN_HOST}
            assert "${TEST_CONN_HOST}" not in result.message

            print("✓ Environment variables resolved during connection test")

        finally:
            config_path.unlink()
    finally:
        del os.environ["TEST_CONN_HOST"]
        del os.environ["TEST_CONN_PORT"]


if __name__ == "__main__":
    test_list_data_sources_preserves_env_vars()
    test_list_data_sources_with_include()
    import asyncio

    asyncio.run(test_env_vars_resolved_during_connection_test())
    print("\n✓ All tests passed!")
