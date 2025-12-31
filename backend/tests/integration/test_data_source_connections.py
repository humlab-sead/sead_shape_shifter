"""Debug script for testing data source connections.

Run this script to debug connection issues with PostgreSQL and Access databases.

Usage:
    uv run python -m backend.tests.debug_data_source_connections
"""

import os
from pathlib import Path

import dotenv
import pytest
from loguru import logger

from backend.app.core.config import Settings
from backend.app.mappers.data_source_mapper import DataSourceMapper
from backend.app.models.data_source import DataSourceConfig
from src import model as core
from backend.app.services.data_source_service import DataSourceService
from src.loaders.driver_metadata import DriverSchema, DriverSchemaRegistry
from src.utility import find_parent_with

project_root: Path = find_parent_with(Path(__file__), "pyproject.toml")


class TestPostgresConnection:
    """Tests for PostgreSQL data source connection."""

    @pytest.mark.asyncio
    async def test_postgresql_connection(self, settings: Settings):
        """Test PostgreSQL connection."""
        logger.info("=" * 80)
        logger.info("Testing PostgreSQL Connection")
        logger.info("=" * 80)

        dotenv.load_dotenv(project_root / "input/.env")

        # Get schema (auto-loads from classes)
        schema: DriverSchema | None = DriverSchemaRegistry.get("postgresql")
        logger.info(f"PostgreSQL Schema: {schema}")

        # Check if required env vars are set
        required_vars = ["SEAD_HOST", "SEAD_PORT", "SEAD_DBNAME", "SEAD_USER"]
        missing_vars = [v for v in required_vars if v not in os.environ]

        if missing_vars:
            pytest.skip(f"Required environment variables not set: {', '.join(missing_vars)}")

        # Create test config
        pg_config = DataSourceConfig(
            name="test_postgres",
            driver="postgresql",  # type: ignore
            host=os.environ["SEAD_HOST"],
            port=int(os.environ["SEAD_PORT"]),
            database=os.environ["SEAD_DBNAME"],
            username=os.environ["SEAD_USER"],
            **{},
        )

        logger.info(f"Config: {pg_config.model_dump(exclude={'password'})}")

        # Test connection
        service = DataSourceService(settings.CONFIGURATIONS_DIR)

        logger.info("Testing connection...")
        result = await service.test_connection(pg_config)

        logger.info(f"Success: {result.success}")
        logger.info(f"Message: {result.message}")
        logger.info(f"Time: {result.connection_time_ms}ms")
        logger.info(f"Metadata: {result.metadata}")

        # Assert connection was successful
        assert result.success, f"Connection failed: {result.message}"


async def test_access_connection(settings: Settings) -> bool:
    """Test MS Access connection."""
    logger.info("=" * 80)
    logger.info("Testing MS Access Connection")
    logger.info("=" * 80)

    # Get schema (auto-loads from classes)
    schema: DriverSchema | None = DriverSchemaRegistry.get("access")
    logger.info(f"Access Schema: {schema}")

    # Find an actual Access database file
    input_dir: Path = project_root / "input"
    mdb_files = list(input_dir.glob("*.mdb"))

    if not mdb_files:
        logger.warning("No .mdb files found in input/ directory")
        return False

    mdb_file = mdb_files[0]
    logger.info(f"Using Access database: {mdb_file}")

    # Create test config
    access_config = DataSourceConfig(
        name="test_access", driver="ucanaccess", filename=str(mdb_file), options={"ucanaccess_dir": "lib/ucanaccess"}, **{}  # type: ignore
    )

    logger.info(f"Config: {access_config.model_dump()}")

    # Test connection
    service = DataSourceService(settings.CONFIGURATIONS_DIR)

    try:
        logger.info("Testing connection...")
        result = await service.test_connection(access_config)

        logger.info(f"Success: {result.success}")
        logger.info(f"Message: {result.message}")
        logger.info(f"Time: {result.connection_time_ms}ms")
        logger.info(f"Metadata: {result.metadata}")

        return result.success
    except Exception as e:  # pylint: disable=broad-except
        logger.error(f"Connection test failed with exception: {e}")
        logger.exception(e)
        return False


async def test_existing_data_sources(settings: Settings):
    """Test connections to existing configured data sources."""
    logger.info("=" * 80)
    logger.info("Testing Existing Data Sources from Configuration")
    logger.info("=" * 80)

    service = DataSourceService(settings.CONFIGURATIONS_DIR)

    # List all configured data sources
    data_sources: list[DataSourceConfig] = service.list_data_sources()
    logger.info(f"Found {len(data_sources)} configured data sources")

    results = {}

    for ds in data_sources:
        logger.info(f"\n--- Testing: {ds.name} ({ds.driver}) ---")
        logger.info(f"Config: {ds.model_dump(exclude={'password'})}")

        try:
            result = await service.test_connection(ds)

            logger.info(f"  Success: {result.success}")
            logger.info(f"  Message: {result.message}")
            logger.info(f"  Time: {result.connection_time_ms}ms")

            if result.metadata:
                logger.info(f"  Metadata: {result.metadata}")

            results[ds.name] = result.success
        except Exception as e:  # pylint: disable=broad-except
            logger.error(f"  Error: {e}")
            logger.exception(e)
            results[ds.name] = False

    return results


async def debug_mapper():
    """Debug the DataSourceMapper."""
    logger.info("=" * 80)
    logger.info("Debugging DataSourceMapper")
    logger.info("=" * 80)

    # Test PostgreSQL mapping
    logger.info("\n--- PostgreSQL Mapping ---")
    pg_config = DataSourceConfig(
        name="test_pg", driver="postgresql", host="localhost", port=5432, database="testdb", username="testuser", **{}  # type: ignore
    )

    logger.info(f"API Config: {pg_config.model_dump(exclude={'password'})}")

    try:
        core_config: core.DataSourceConfig = DataSourceMapper.to_core_config(pg_config)
        logger.info(f"Core Config Name: {core_config.name}")
        logger.info(f"Core Config Driver: {core_config.data_source_cfg.get('driver')}")
        logger.info(f"Core Config Options: {core_config.data_source_cfg.get('options')}")
    except Exception as e:  # pylint: disable=broad-except
        logger.error(f"Mapping failed: {e}")
        logger.exception(e)

    # Test Access mapping
    logger.info("\n--- Access Mapping ---")
    access_config = DataSourceConfig(
        name="test_access",
        driver="ucanaccess",  # type: ignore
        filename="./input/test.mdb",
        options={"ucanaccess_dir": "lib/ucanaccess"},
        **{},
    )

    logger.info(f"API Config: {access_config.model_dump()}")

    try:
        core_config = DataSourceMapper.to_core_config(access_config)
        logger.info(f"Core Config Name: {core_config.name}")
        logger.info(f"Core Config Driver: {core_config.data_source_cfg.get('driver')}")
        logger.info(f"Core Config Options: {core_config.data_source_cfg.get('options')}")
    except Exception as e:  # pylint: disable=broad-except
        logger.error(f"Mapping failed: {e}")
        logger.exception(e)


# async def main():
#     """Run all debug tests."""
#     logger.info("Starting Data Source Connection Debug Tests")
#     logger.info(f"Project Root: {project_root}")
#     logger.info("")

#     # Debug mapper first
#     await debug_mapper()

#     # Test existing data sources
#     logger.info("\n")
#     existing_results = await test_existing_data_sources()

#     # Test PostgreSQL
#     logger.info("\n")
#     pg_success = await test_postgresql_connection()

#     # Test Access
#     logger.info("\n")
#     access_success = await test_access_connection()

#     # Summary
#     logger.info("\n" + "=" * 80)
#     logger.info("SUMMARY")
#     logger.info("=" * 80)

#     if existing_results:
#         logger.info("Existing Data Sources:")
#         for name, success in existing_results.items():
#             status = "✓ PASS" if success else "✗ FAIL"
#             logger.info(f"  {status} - {name}")

#     logger.info(f"\nDirect PostgreSQL Test: {'✓ PASS' if pg_success else '✗ FAIL'}")
#     logger.info(f"Direct Access Test: {'✓ PASS' if access_success else '✗ FAIL'}")

#     # Return exit code
#     all_success = (all(existing_results.values()) if existing_results else True) and pg_success and access_success

#     return 0 if all_success else 1


# if __name__ == "__main__":
#     exit_code = asyncio.run(main())
#     sys.exit(exit_code)
