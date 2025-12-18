"""
Example demonstrating environment variable resolution in data source configurations.

This shows how the Shape Shifter system handles environment variables like those
in sead-options.yml:

    driver: postgres
    options:
      host: ${SEAD_HOST}
      port: ${SEAD_PORT}
      dbname: ${SEAD_DBNAME}
      username: ${SEAD_USER}

When configurations are loaded via the core (src.configuration framework), environment
variables are automatically resolved. When testing data sources via the API, the
DataSourceService now also resolves these variables before testing connections.

For password management using .pgpass:
- PostgreSQL will automatically use ~/.pgpass if no password is provided
- The connection will succeed without sending a password from the application
- This is the recommended approach for production environments
"""

import asyncio
import os
from unittest.mock import Mock

from backend.app.models.data_source import DataSourceConfig
from backend.app.services.data_source_service import DataSourceService


async def demonstrate_env_var_resolution():
    """Demonstrate environment variable resolution."""

    # Set up example environment variables (in production these would be in your shell)
    os.environ["SEAD_HOST"] = "localhost"
    os.environ["SEAD_PORT"] = "5432"
    os.environ["SEAD_DBNAME"] = "sead_production"
    os.environ["SEAD_USER"] = "sead_user"
    # Note: No SEAD_PASSWORD - using .pgpass file instead

    try:
        # Create mock config service
        mock_config = Mock()
        mock_config.get.return_value = {}
        service = DataSourceService(mock_config)

        # Create data source config with environment variables
        # This mimics what the API would receive from the frontend
        config: DataSourceConfig = DataSourceConfig(
            name="sead",
            driver="postgresql",  # type: ignore
            options={
                "host": "${SEAD_HOST}",
                "port": "${SEAD_PORT}",
                "dbname": "${SEAD_DBNAME}",
                "username": "${SEAD_USER}",
            },
            **{},
        )
        assert config.options is not None
        print("Original config (with env vars):")
        print(f"  Host: {config.options.get('host')}")
        print(f"  Port: {config.options.get('port')}")
        print(f"  Database: {config.options.get('dbname')}")
        print(f"  Username: {config.options.get('username')}")
        print()

        # Resolve environment variables
        resolved = service._resolve_config_env_vars(config)

        assert resolved.options is not None
        print("Resolved config (env vars replaced):")
        print(f"  Host: {resolved.options.get('host')}")
        print(f"  Port: {resolved.options.get('port')}")
        print(f"  Database: {resolved.options.get('dbname')}")
        print(f"  Username: {resolved.options.get('username')}")
        print(f"  Password: {resolved.password or 'Not set (will use .pgpass)'}")
        print()

        print("When you test this connection:")
        print("1. Environment variables are resolved automatically")
        print("2. If no password is set, PostgreSQL will check ~/.pgpass")
        print("3. .pgpass format: hostname:port:database:username:password")
        print("4. Example: localhost:5432:sead_production:sead_user:secret123")
        print()

        # Note: Actual connection test would be done with:
        # result = await service.test_connection(config)
        # The test_connection method now calls _resolve_config_env_vars internally

    finally:
        # Clean up
        del os.environ["SEAD_HOST"]
        del os.environ["SEAD_PORT"]
        del os.environ["SEAD_DBNAME"]
        del os.environ["SEAD_USER"]


if __name__ == "__main__":
    asyncio.run(demonstrate_env_var_resolution())
