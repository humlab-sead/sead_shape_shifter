from typing import Iterator
from unittest.mock import MagicMock

import pandas as pd
import pytest
from dotenv import load_dotenv
from importer.configuration import ConfigStore
from importer.configuration.interface import ConfigLike
from importer.metadata import MockSchemaService, SchemaService, SeadSchema
from importer.submission import Submission

# Import test builders for easy access in tests
from tests.builders import build_column, build_schema, build_table

# pylint: disable=redefined-outer-name

DOTENV_FILENAME = "tests/test_data/.env"
CONFIG_FILENAME = "tests/test_data/config.yml"
ENV_PREFIX = "SEAD_IMPORT"

load_dotenv(DOTENV_FILENAME)


# ============================================================================
# Configuration Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def cfg() -> ConfigLike:
    """Load test configuration - session scoped for integration tests."""
    ConfigStore.get_instance().configure_context(source=CONFIG_FILENAME, env_filename=DOTENV_FILENAME, env_prefix=ENV_PREFIX)
    return ConfigStore.get_instance().config()  # type: ignore[return-value]


@pytest.fixture(scope="function", autouse=True)
def minimal_config():
    """Minimal config for unit tests - auto-used so policies don't fail on ConfigValue.resolve()."""
    store = ConfigStore.get_instance()
    if not store.is_configured("default"):
        store.configure_context(source=CONFIG_FILENAME, env_filename=DOTENV_FILENAME, env_prefix=ENV_PREFIX)
    yield
    # No cleanup - let session fixture manage lifecycle


# ============================================================================
# Full Schema Fixtures (for integration tests)
# ============================================================================


@pytest.fixture(scope="session")
def full_schema_service(cfg: ConfigLike) -> Iterator[SchemaService]:  # pylint: disable=unused-argument
    """Full schema loaded from CSV - session scoped, use for integration tests only."""
    sead_tables: pd.DataFrame = pd.read_csv("tests/test_data/sead_tables.csv")
    sead_columns: pd.DataFrame = pd.read_csv("tests/test_data/sead_columns.csv")
    service: SchemaService = MockSchemaService(sead_tables=sead_tables, sead_columns=sead_columns)
    yield service


@pytest.fixture(scope="session")
def full_schema(
    full_schema_service: SchemaService, cfg: ConfigLike  # pylint: disable=unused-argument
) -> Iterator[SeadSchema]:  # pylint: disable=unused-argument
    """Full SeadSchema - session scoped, use for integration tests only."""
    schema: SeadSchema = full_schema_service.load()
    yield schema


@pytest.fixture(scope="session")
def full_submission(full_schema: SeadSchema, cfg: ConfigLike, full_schema_service: SchemaService) -> Iterator[Submission]:
    """Full submission loaded from Excel - session scoped, use for integration tests only."""
    yield Submission.load(schema=full_schema, source=cfg.get("test:reduced_excel_filename"), service=full_schema_service)


# ============================================================================
# Minimal Fixtures (for unit tests)
# ============================================================================


@pytest.fixture
def mock_service():
    """Mock SchemaService for unit tests - function scoped."""
    service = MagicMock(spec=SchemaService)
    service.get_primary_key_values.return_value = set()
    return service


@pytest.fixture
def minimal_schema():
    """Minimal schema with one test table - function scoped for unit tests."""
    return build_schema(
        [
            build_table(
                table_name="tbl_test",
                pk_name="test_id",
                columns={
                    "test_id": build_column("tbl_test", "test_id", is_pk=True),
                    "name": build_column("tbl_test", "name", data_type="varchar"),
                },
            )
        ]
    )


@pytest.fixture
def two_table_schema():
    """Schema with main table and lookup table - common pattern for unit tests."""
    return build_schema(
        [
            build_table(
                table_name="tbl_main",
                pk_name="main_id",
                columns={
                    "main_id": build_column("tbl_main", "main_id", is_pk=True),
                    "lookup_id": build_column("tbl_main", "lookup_id", is_fk=True, fk_table_name="tbl_lookup"),
                },
            ),
            build_table(
                table_name="tbl_lookup",
                pk_name="lookup_id",
                is_lookup=True,
                columns={
                    "lookup_id": build_column("tbl_lookup", "lookup_id", is_pk=True),
                    "value": build_column("tbl_lookup", "value", data_type="varchar"),
                },
            ),
        ]
    )


# ============================================================================
# Backward Compatibility Aliases
# ============================================================================

# These provide backward compatibility for existing tests
# Gradually migrate tests to use the explicit fixtures above
# service = full_schema_service
# schema = full_schema
# submission = full_submission
