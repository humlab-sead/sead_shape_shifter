import os
from pathlib import Path

import dotenv
import pytest
from loguru import logger

from backend.app.core.config import Settings
from backend.app.models.data_source import DataSourceConfig
from backend.app.services.data_source_service import DataSourceService
from src.loaders.driver_metadata import DriverSchema, DriverSchemaRegistry
from src.utility import find_parent_with

project_root: Path = find_parent_with(Path(__file__), "pyproject.toml")


@pytest.mark.asyncio
async def test_postgresql_connection(self, settings: Settings):

    dotenv.load_dotenv(project_root / "input/.env")

    schema: DriverSchema | None = DriverSchemaRegistry.get("postgresql")
    logger.info(f"PostgreSQL Schema: {schema}")

    required_vars = ["SEAD_HOST", "SEAD_PORT", "SEAD_DBNAME", "SEAD_USER"]
    missing_vars = [v for v in required_vars if v not in os.environ]

    assert not missing_vars, f"Required environment variables not set: {', '.join(missing_vars)}"

    pg_config = DataSourceConfig(
        name="test_postgres",
        driver="postgresql",  # type: ignore
        host=os.environ["SEAD_HOST"],
        port=int(os.environ["SEAD_PORT"]),
        database=os.environ["SEAD_DBNAME"],
        username=os.environ["SEAD_USER"],
        **{},
    )

    service = DataSourceService(settings.CONFIGURATIONS_DIR)

    result = await service.test_connection(pg_config)

    assert result.success, f"Connection failed: {result.message}"


async def test_access_connection(settings: Settings) -> None:

    schema: DriverSchema | None = DriverSchemaRegistry.get("access")
    logger.info(f"Access Schema: {schema}")

    # Find an actual Access database file
    input_dir: Path = project_root / "input"
    mdb_files = list(input_dir.glob("*.mdb"))

    if not mdb_files:
        logger.warning("No .mdb files found in input/ directory")
        return

    mdb_file = mdb_files[0]
    logger.info(f"Using Access database: {mdb_file}")

    access_config = DataSourceConfig(
        name="test_access", driver="ucanaccess", filename=str(mdb_file), options={"ucanaccess_dir": "lib/ucanaccess"}, **{}  # type: ignore
    )

    service = DataSourceService(settings.CONFIGURATIONS_DIR)

    result = await service.test_connection(access_config)
    assert result.success, f"Connection failed: {result.message}"


async def test_existing_data_sources(settings: Settings):
    """Test connections to existing configured data sources."""

    service = DataSourceService(settings.CONFIGURATIONS_DIR)

    data_sources: list[DataSourceConfig] = service.list_data_sources()

    results = {}

    for ds in data_sources:

        try:
            result = await service.test_connection(ds)

            if result.metadata:
                logger.info(f"  Metadata: {result.metadata}")

            results[ds.name] = result.success
        except Exception as e:  # pylint: disable=broad-except
            logger.error(f"  Error: {e}")
            logger.exception(e)
            results[ds.name] = False

        assert results[ds.name], f"Connection test failed for data source '{ds.name}'"
