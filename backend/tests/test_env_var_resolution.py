"""Test environment variable resolution in data source configurations."""

import os
from unittest.mock import Mock, patch

import pytest

from backend.app.core.config import Settings
from backend.app.models.data_source import DataSourceConfig
from backend.app.services.data_source_service import DataSourceService

# pylint: disable=redefined-outer-name, unused-argument, import-outside-toplevel, no-member


@pytest.fixture
def mock_config():
    """Create a mock configuration object."""
    config = Mock()
    config.get.return_value = {}
    return config


@pytest.fixture
def service(settings: "Settings") -> DataSourceService:
    """Create service with mock config."""
    return DataSourceService(settings.CONFIGURATIONS_DIR)


class TestEnvironmentVariableResolution:
    """Tests for environment variable resolution in data sources."""

    def test_resolve_env_vars_in_dict(self, service):
        """Should resolve environment variables in config dict."""
        from src.utility import replace_env_vars

        # Set test env vars
        os.environ["TEST_HOST"] = "testhost.com"
        os.environ["TEST_PORT"] = "5432"
        os.environ["TEST_DB"] = "testdb"

        try:
            config_dict = {
                "host": "${TEST_HOST}",
                "port": "${TEST_PORT}",
                "database": "${TEST_DB}",
                "username": "user",
                "options": {"param1": "${TEST_HOST}", "param2": "literal_value"},
            }

            resolved = replace_env_vars(config_dict)

            assert resolved is not None

            assert resolved["host"] == "testhost.com"
            assert resolved["port"] == "5432"
            assert resolved["database"] == "testdb"
            assert resolved["username"] == "user"
            assert resolved["options"]["param1"] == "testhost.com"
            assert resolved["options"]["param2"] == "literal_value"
        finally:
            # Clean up
            del os.environ["TEST_HOST"]
            del os.environ["TEST_PORT"]
            del os.environ["TEST_DB"]

    def test_resolve_env_vars_missing_variable(self, service):
        """Should return empty string for missing env vars."""
        from src.utility import replace_env_vars

        config_dict = {"host": "${NONEXISTENT_VAR}", "port": "5432"}

        resolved = replace_env_vars(config_dict)

        # replace_env_vars returns empty string for unresolved vars
        assert resolved["host"] == ""
        assert resolved["port"] == "5432"

    def test_resolve_config_env_vars(self, service):
        """Should resolve environment variables in DataSourceConfig model."""
        # Set test env vars
        os.environ["TEST_PG_HOST"] = "postgres.example.com"
        os.environ["TEST_PG_PORT"] = "5433"
        os.environ["TEST_PG_DB"] = "mydb"
        os.environ["TEST_PG_USER"] = "dbuser"

        try:
            # Store env vars in options dict to avoid Pydantic validation issues
            config = DataSourceConfig(
                name="test_postgres",
                driver="postgresql",  # type: ignore
                options={
                    "host": "${TEST_PG_HOST}",
                    "port": "${TEST_PG_PORT}",
                    "database": "${TEST_PG_DB}",
                    "username": "${TEST_PG_USER}",
                },
                **{},
            )

            resolved = config.resolve_config_env_vars()

            assert resolved is not None
            assert resolved.options is not None

            assert resolved.options["host"] == "postgres.example.com"
            assert resolved.options["port"] == "5433"
            assert resolved.options["database"] == "mydb"
            assert resolved.options["username"] == "dbuser"
        finally:
            # Clean up
            del os.environ["TEST_PG_HOST"]
            del os.environ["TEST_PG_PORT"]
            del os.environ["TEST_PG_DB"]
            del os.environ["TEST_PG_USER"]

    def test_resolve_config_with_options(self, service):
        """Should resolve env vars in options dict."""
        os.environ["TEST_FILENAME"] = "/path/to/file.mdb"
        os.environ["TEST_DIR"] = "/path/to/ucanaccess"

        try:
            config = DataSourceConfig(
                name="test_access",
                driver="ucanaccess",  # type: ignore
                filename="${TEST_FILENAME}",
                options={"ucanaccess_dir": "${TEST_DIR}", "other_param": "literal"},
                **{},
            )

            resolved: DataSourceConfig = config.resolve_config_env_vars()

            assert resolved.filename == "/path/to/file.mdb"
            assert resolved.options["ucanaccess_dir"] == "/path/to/ucanaccess"  # type: ignore
            assert resolved.options["other_param"] == "literal"  # type: ignore
        finally:
            # Clean up
            del os.environ["TEST_FILENAME"]
            del os.environ["TEST_DIR"]

    def test_resolve_config_preserves_password(self, service):
        """Should preserve password SecretStr during resolution."""
        os.environ["TEST_HOST"] = "localhost"

        try:
            config = DataSourceConfig(
                name="test",
                driver="postgresql",  # type: ignore
                host="${TEST_HOST}",
                database="testdb",
                username="user",
                password="secret123",  # type: ignore
                **{},
            )

            resolved = config.resolve_config_env_vars()

            assert resolved is not None

            assert resolved.host == "localhost"
            assert resolved.password is not None
            assert resolved.password.get_secret_value() == "secret123"
        finally:
            del os.environ["TEST_HOST"]

    def test_list_data_sources_keeps_env_vars(self, settings: Settings):
        """Should keep env vars unresolved when listing data sources for UI editing."""
        os.environ["DS_HOST"] = "db.example.com"
        os.environ["DS_DB"] = "production"

        service = DataSourceService(settings.CONFIGURATIONS_DIR)

        try:
            ds_cfg: DataSourceConfig = DataSourceConfig(
                name="prod_db",
                driver="postgresql",  # type: ignore
                host="${DS_HOST}",
                database="${DS_DB}",
                username="produser",
                port=5432,
            )
            with patch.object(service, "get_data_source", return_value=ds_cfg) as _:

                # Mock config to return data source with env vars

                ds_cfg2: DataSourceConfig | None = service.get_data_source("dummy_file.yml")

                assert ds_cfg2 is not None
                assert ds_cfg2.name == "prod_db"
                assert ds_cfg2.host == "${DS_HOST}"
                assert ds_cfg2.database == "${DS_DB}"
        finally:
            del os.environ["DS_HOST"]
            del os.environ["DS_DB"]

    @pytest.mark.asyncio
    async def test_test_connection_resolves_env_vars(self, service):
        """Should resolve env vars before testing connection."""
        from unittest.mock import AsyncMock

        from src.loaders.base_loader import ConnectTestResult

        os.environ["TEST_CONN_HOST"] = "test.db.com"
        os.environ["TEST_CONN_DB"] = "testdb"

        try:
            config = DataSourceConfig(
                name="test",
                driver="postgresql",  # type: ignore
                host="${TEST_CONN_HOST}",
                port=5432,
                database="${TEST_CONN_DB}",
                username="testuser",
                **{},
            )

            # Mock the loader instance and its test_connection method
            mock_loader = AsyncMock()
            mock_loader.test_connection.return_value = ConnectTestResult(
                success=True, message="Mock connection successful", connection_time_ms=10, metadata={}
            )

            # Mock DataLoaders.get where it's imported (in data_source_service)
            with patch("backend.app.services.data_source_service.DataLoaders") as mock_data_loaders:
                # DataLoaders.get returns a class, which when instantiated returns our mock loader
                mock_loader_class = Mock(return_value=mock_loader)
                mock_data_loaders.get.return_value = mock_loader_class

                result = await service.test_connection(config)

                assert result.success, result.message
                assert result.message == "Mock connection successful"

                # Verify DataLoaders.get was called with the correct driver
                mock_data_loaders.get.assert_called_once_with("postgresql")
                # Verify the loader class was instantiated
                mock_loader_class.assert_called_once()
        finally:
            del os.environ["TEST_CONN_HOST"]
            del os.environ["TEST_CONN_DB"]
