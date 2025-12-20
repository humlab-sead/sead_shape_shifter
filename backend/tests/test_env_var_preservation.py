"""Test that environment variables are preserved in data source listings."""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from backend.app.core.config import Settings
from backend.app.models.data_source import DataSourceConfig, DataSourceTestResult
from backend.app.services.data_source_service import DataSourceService


def test_list_data_sources_preserves_env_vars(settings: Settings):
    """Verify that env vars like ${SEAD_HOST} are preserved when listing data sources."""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        config_content = {
            "driver": "postgresql",
            "options": {
                "host": "${TEST_HOST}",
                "port": "${TEST_PORT}",
                "database": "${TEST_DB}",
                "username": "${TEST_USER}",
            },
        }
        yaml.dump(config_content, f)
        cfg_path = Path(f.name)
        cfg_name: str = cfg_path.stem
        cfg_folder: Path = cfg_path.parent
    try:

        service = DataSourceService(cfg_folder)

        ds: DataSourceConfig | None = service.get_data_source(cfg_path)

        assert ds is not None

        assert ds.name == cfg_name
        assert ds.filename == cfg_path.name
        assert ds.options is not None

        # Verify env vars are preserved (not resolved)
        assert ds.options["host"] == "${TEST_HOST}"
        assert ds.options["port"] == "${TEST_PORT}"
        assert ds.options["database"] == "${TEST_DB}"
        assert ds.options["username"] == "${TEST_USER}"

        print("✓ Environment variables preserved in listing")

    finally:
        # Clean up
        cfg_path.unlink()


def test_list_data_sources_with_include():
    """Test that @include directives are followed to read raw data."""

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

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

        service = DataSourceService(tmpdir_path)

        # List data sources
        data_sources = service.list_data_sources()

        assert len(data_sources) == 1
        ds: DataSourceConfig = data_sources[0]
        assert ds.name == "sead-options"
        assert ds.options is not None

        # Verify env vars from included file are preserved
        assert ds.options["host"] == "${SEAD_HOST}"
        assert ds.options["port"] == "${SEAD_PORT}"
        assert ds.options["dbname"] == "${SEAD_DBNAME}"
        assert ds.options["username"] == "${SEAD_USER}"

        print("✓ Environment variables preserved from @include files")


@pytest.mark.asyncio
async def test_env_vars_resolved_during_connection_test(settings: Settings):
    """Verify that env vars ARE resolved when testing connections."""

    # Set test env vars
    os.environ["TEST_CONN_HOST"] = "localhost"
    os.environ["TEST_CONN_PORT"] = "5432"

    try:
        # Create a temporary YAML config file
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a temporary YAML config file in tmpdir
            cfg_path: Path = Path(tmpdir) / "test_conn.yml"

            with open(cfg_path, "w", encoding="utf-8") as f:
                config_content = {
                    "driver": "postgresql",
                    "options": {
                        "host": "${TEST_CONN_HOST}",
                        "port": "${TEST_CONN_PORT}",
                        "database": "testdb",
                        "username": "testuser",
                    },
                }
                yaml.dump(config_content, f)
                cfg_folder: Path = cfg_path.parent
            try:

                service = DataSourceService(cfg_folder)
                data_sources: list[DataSourceConfig] = service.list_data_sources()

                assert len(data_sources) == 1
                ds: DataSourceConfig = data_sources[0]
                assert ds.options is not None

                # Verify env vars are NOT resolved in listing
                assert ds.options["host"] == "${TEST_CONN_HOST}"
                assert ds.options["port"] == "${TEST_CONN_PORT}"

                # Now test connection - env vars should be resolved
                result: DataSourceTestResult = await service.test_connection(ds)

                # If the error message contains the resolved values, env vars were resolved
                # (We expect connection to fail since there's no actual DB, but that's OK)
                assert not result.success  # Connection should fail
                # Error message should contain resolved host, not ${TEST_CONN_HOST}
                assert "${TEST_CONN_HOST}" not in result.message

                print("✓ Environment variables resolved during connection test")

            finally:
                cfg_path.unlink()
    finally:
        del os.environ["TEST_CONN_HOST"]
        del os.environ["TEST_CONN_PORT"]
