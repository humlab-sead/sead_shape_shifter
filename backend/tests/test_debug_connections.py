"""Debug test cases for data source connections.

Run with:
    pytest backend/tests/test_debug_connections.py -v -s

Or debug specific test with breakpoint:
    pytest backend/tests/test_debug_connections.py::test_debug_postgresql_connection -v -s
"""

import os
from pathlib import Path
from unittest.mock import Mock

import pytest

from backend.app import models as api
from backend.app import services as api_services
from backend.app.core.config import Settings
from backend.app.mappers.data_source_mapper import DataSourceMapper
from src import model as core
from src.loaders.driver_metadata import DriverSchema, DriverSchemaRegistry

# pylint: disable=redefined-outer-name, f-string-without-interpolation, no-member


@pytest.fixture
def mock_config():
    """Create a mock configuration object."""
    config = Mock()

    # Mock the data sources configuration
    # This will be loaded from actual config if available, or return empty
    config.get.return_value = {
        "sead": {
            "driver": "postgresql",
            "options": {
                "host": "localhost",
                "port": 5432,
                "database": "sead",
                "username": "postgres",
            },
        },
        "arbodat": {
            "driver": "ucanaccess",
            "options": {
                "filename": "./input/ArchBotDaten.mdb",
                "ucanaccess_dir": "lib/ucanaccess",
            },
        },
    }
    return config


@pytest.fixture(autouse=True)
def ensure_schemas_loaded():
    """Ensure driver schemas are loaded before tests."""
    # Schemas now auto-load from DataLoader classes
    pass


@pytest.mark.asyncio
async def test_debug_postgresql_connection(settings: Settings):
    """Debug PostgreSQL connection with detailed output."""

    ds_config: api.DataSourceConfig = api.DataSourceConfig(
        name="debug_postgres",
        driver="postgresql",  # type: ignore
        host="localhost",
        port=5432,
        database="postgres",
        username="postgres",
        **{},
    )

    print(f"\n--- PostgreSQL Config ---")
    print(f"Config: {ds_config.model_dump(exclude={'password'})}")

    schema: DriverSchema | None = DriverSchemaRegistry.get("postgresql")
    assert schema is not None, "Access driver schema not found"
    print(f"\nDriver Schema: {schema.display_name}")
    print(f"Fields: {[f.name for f in schema.fields]}")

    print(f"\n--- Testing Mapper ---")
    core_config: core.DataSourceConfig = DataSourceMapper.to_core_config(ds_config)
    print(f"Core Config Name: {core_config.name}")
    print(f"Core Config Driver: {core_config.data_source_cfg.get('driver')}")
    print(f"Core Config Keys: {list(core_config.data_source_cfg.get('options', {}).keys())}")

    # Test connection
    print(f"\n--- Testing Connection ---")
    service = api_services.DataSourceService(settings.CONFIGURATIONS_DIR)
    result: api.DataSourceTestResult = await service.test_connection(ds_config)

    print(f"Success: {result.success}")
    print(f"Message: {result.message}")
    print(f"Time: {result.connection_time_ms}ms")
    print(f"Metadata: {result.metadata}")

    # This test is for debugging, don't fail on connection issues
    # assert result.success, f"Connection failed: {result.message}"


@pytest.mark.asyncio
async def test_debug_access_connection(settings: Settings):
    """Debug Access connection with detailed output."""
    # Find an Access database
    input_dir: Path = Path(__file__).parent.parent.parent / "input"
    mdb_files: list[Path] = list(input_dir.glob("*.mdb"))

    if not mdb_files:
        pytest.skip("No .mdb files found in input/ directory")

    mdb_file: Path = mdb_files[0]
    print(f"\n--- Using Access Database ---")
    print(f"File: {mdb_file}")
    print(f"Exists: {mdb_file.exists()}")
    print(f"Size: {mdb_file.stat().st_size if mdb_file.exists() else 'N/A'} bytes")

    # Create config
    ds_cfg: api.DataSourceConfig = api.DataSourceConfig(
        name="debug_access", driver="ucanaccess", filename=str(mdb_file), options={"ucanaccess_dir": "lib/ucanaccess"}, **{}  # type: ignore
    )

    print(f"\n--- Access Config ---")
    print(f"Config: {ds_cfg.model_dump()}")

    # Check schema
    schema: DriverSchema | None = DriverSchemaRegistry.get("ucanaccess")
    assert schema is not None, "Access driver schema not found"

    print(f"\nDriver Schema: {schema.display_name}")
    print(f"Fields: {[f.name for f in schema.fields]}")

    # Test mapper
    print(f"\n--- Testing Mapper ---")
    core_config: core.DataSourceConfig = DataSourceMapper.to_core_config(ds_cfg)
    print(f"Core Config Name: {core_config.name}")
    print(f"Core Config Driver: {core_config.data_source_cfg.get('driver')}")
    print(f"Core Config Keys: {list(core_config.data_source_cfg.get('options', {}).keys())}")

    # Test connection
    print(f"\n--- Testing Connection ---")
    service = api_services.DataSourceService(settings.CONFIGURATIONS_DIR)
    result: api.DataSourceTestResult = await service.test_connection(ds_cfg)

    print(f"Success: {result.success}")
    print(f"Message: {result.message}")
    print(f"Time: {result.connection_time_ms}ms")
    print(f"Metadata: {result.metadata}")

    # This test is for debugging, don't fail on connection issues
    # assert result.success, f"Connection failed: {result.message}"


@pytest.mark.asyncio
async def test_debug_existing_data_sources(settings: Settings):
    """Test all existing configured data sources."""
    service = api_services.DataSourceService(settings.CONFIGURATIONS_DIR)
    data_sources = service.list_data_sources()

    print(f"\n--- Configured Data Sources ---")
    print(f"Found {len(data_sources)} data sources")

    for ds in data_sources:
        print(f"\n=== {ds.name} ({ds.driver}) ===")
        print(f"Config: {ds.model_dump(exclude={'password'})}")

        # Test connection
        try:
            result: api.DataSourceTestResult = await service.test_connection(ds)
            print(f"  Result: {'✓ SUCCESS' if result.success else '✗ FAILED'}")
            print(f"  Message: {result.message}")
            print(f"  Time: {result.connection_time_ms}ms")

            if result.metadata:
                print(f"  Metadata: {result.metadata}")
        except Exception as e:  # pylint: disable=broad-except
            print(f"  Exception: {e}")
            import traceback  # pylint: disable=import-outside-toplevel

            traceback.print_exc()


@pytest.mark.asyncio
async def test_debug_postgresql_with_env_vars(settings: Settings):
    """Test PostgreSQL connection with environment variables (like sead-options.yml)."""

    # Set up environment variables like in sead-options.yml
    os.environ["TEST_SEAD_HOST"] = "localhost"
    os.environ["TEST_SEAD_PORT"] = "5432"
    os.environ["TEST_SEAD_DB"] = "postgres"
    os.environ["TEST_SEAD_USER"] = "postgres"

    try:
        print("\n--- Testing with Environment Variables ---")
        print("This simulates how sead-options.yml uses ${SEAD_HOST}, etc.")
        print()

        # Create config with env var references (like in YAML)
        config: api.DataSourceConfig = api.DataSourceConfig(
            name="test_with_env_vars",
            driver="postgresql",  # type: ignore
            options={
                "host": "${TEST_SEAD_HOST}",
                "port": "${TEST_SEAD_PORT}",
                "database": "${TEST_SEAD_DB}",
                "username": "${TEST_SEAD_USER}",
            },
            **{},
        )
        assert config.options is not None
        print("Original config (with env var references):")
        print(f"  host: {config.options.get('host')}")  # type: ignore
        print(f"  port: {config.options.get('port')}")  # type: ignore
        print(f"  database: {config.options.get('database')}")  # type: ignore
        print(f"  username: {config.options.get('username')}")  # type: ignore
        print()

        # Test connection - env vars should be resolved automatically
        service = api_services.DataSourceService(settings.CONFIGURATIONS_DIR)
        result = await service.test_connection(config)

        print("After resolution (env vars replaced):")
        print(f"  Result: {'✓ SUCCESS' if result.success else '✗ FAILED'}")
        print(f"  Message: {result.message}")
        print(f"  Time: {result.connection_time_ms}ms")

        if not result.success:
            print()
            print("Note: Connection may fail if PostgreSQL isn't running locally")
            print("      or if password authentication is required.")
            print("      Use ~/.pgpass file for password management.")
    finally:
        # Clean up
        del os.environ["TEST_SEAD_HOST"]
        del os.environ["TEST_SEAD_PORT"]
        del os.environ["TEST_SEAD_DB"]
        del os.environ["TEST_SEAD_USER"]


@pytest.mark.asyncio
async def test_debug_mapper_validation():
    """Debug mapper validation with various configs."""
    print("\n--- Testing Mapper Validation ---")

    # Test 1: PostgreSQL with all fields
    print("\nTest 1: PostgreSQL with all fields")
    pg_full = api.DataSourceConfig(
        name="pg_full", driver="postgresql", host="localhost", port=5432, database="testdb", username="testuser", **{}  # type: ignore
    )

    try:
        cfg_core: core.DataSourceConfig = DataSourceMapper.to_core_config(pg_full)
        print(f"  ✓ Success - Driver: {cfg_core.data_source_cfg.get('driver')}")
        print(f"    Options: {cfg_core.data_source_cfg.get('options')}")
    except Exception as e:  # pylint: disable=broad-except
        print(f"  ✗ Failed: {e}")

    # Test 2: PostgreSQL with minimal fields (no port)
    print("\nTest 2: PostgreSQL without port")
    pg_minimal: api.DataSourceConfig = api.DataSourceConfig(
        name="pg_minimal", driver="postgresql", host="localhost", database="testdb", username="testuser", **{}  # type: ignore
    )

    try:
        cfg_core: core.DataSourceConfig = DataSourceMapper.to_core_config(pg_minimal)
        print(f"  ✓ Success - Driver: {cfg_core.data_source_cfg.get('driver')}")
        print(f"    Options: {cfg_core.data_source_cfg.get('options')}")
        print(f"    Port in options: {'port' in cfg_core.data_source_cfg.get('options', {})}")
    except Exception as e:  # pylint: disable=broad-except
        print(f"  ✗ Failed: {e}")

    # Test 3: Access with filename
    print("\nTest 3: Access with filename")
    access = api.DataSourceConfig(
        name="access_test",
        driver="ucanaccess",  # type: ignore
        filename="./input/test.mdb",
        options={"ucanaccess_dir": "lib/ucanaccess"},
        **{},
    )

    try:
        cfg_core = DataSourceMapper.to_core_config(access)
        print(f"  ✓ Success - Driver: {cfg_core.data_source_cfg.get('driver')}")
        print(f"    Options: {cfg_core.data_source_cfg.get('options')}")
    except Exception as e:  # pylint: disable=broad-except
        print(f"  ✗ Failed: {e}")

    # Test 4: CSV with filename
    print("\nTest 4: CSV with filename")
    csv = api.DataSourceConfig(name="csv_test", driver="csv", filename="./input/test.csv", **{})  # type: ignore

    try:
        cfg_core = DataSourceMapper.to_core_config(csv)
        print(f"  ✓ Success - Driver: {cfg_core.data_source_cfg.get('driver')}")
        print(f"    Options: {cfg_core.data_source_cfg.get('options')}")
    except Exception as e:  # pylint: disable=broad-except
        print(f"  ✗ Failed: {e}")
