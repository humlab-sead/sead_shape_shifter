"""Tests for DataSourceMapper."""

import pytest
from pydantic import SecretStr

from backend.app.mappers.data_source_mapper import DataSourceMapper
from backend.app.models.data_source import DataSourceConfig


def test_map_postgresql_config():
    """Test mapping PostgreSQL configuration."""
    api_config = DataSourceConfig(
        name="test_pg",
        driver="postgresql",  # type: ignore
        host="localhost",
        port=5432,
        database="testdb",
        username="testuser",
        # password=SecretStr("testpass"),
        **{},
    )

    core_config = DataSourceMapper.to_core_config(api_config)

    assert core_config.name == "test_pg"
    assert core_config.data_source_cfg["driver"] == "postgresql"

    options = core_config.data_source_cfg["options"]
    assert options["host"] == "localhost"
    assert options["port"] == 5432
    assert options["database"] == "testdb"
    assert options["username"] == "testuser"
    # assert options["password"] == "testpass"


def test_map_postgresql_with_defaults():
    """Test PostgreSQL with default values."""
    api_config = DataSourceConfig(name="test_pg", driver="postgresql", database="testdb", username="testuser", **{})  # type: ignore

    core_config = DataSourceMapper.to_core_config(api_config)

    options = core_config.data_source_cfg["options"]
    assert options["host"] == "localhost"  # Default
    assert options["port"] == 5432  # Default
    assert options["database"] == "testdb"
    assert options["username"] == "testuser"
    assert "password" not in options  # Optional field not provided


def test_map_ucanaccess_config():
    """Test mapping MS Access configuration."""
    api_config = DataSourceConfig(
        name="test_access",
        driver="ucanaccess",  # type: ignore
        filename="./input/test.mdb",
        options={"ucanaccess_dir": "lib/ucanaccess"},
        **{},
    )

    core_config = DataSourceMapper.to_core_config(api_config)

    assert core_config.name == "test_access"
    # Driver is normalized by API model
    assert core_config.data_source_cfg["driver"] in ("ucanaccess", "access")

    options = core_config.data_source_cfg["options"]
    assert options["filename"] == "./input/test.mdb"
    assert options["ucanaccess_dir"] == "lib/ucanaccess"


def test_map_ucanaccess_prefers_options_filename_when_metadata_present():
    """Mapper should ignore YAML filename metadata and use real file path from options."""
    api_config = DataSourceConfig(
        name="test_access",
        driver="ucanaccess",  # type: ignore
        filename="arbodat-data-options.yml",  # metadata from service
        options={"filename": "./input/real-db.mdb", "ucanaccess_dir": "lib/ucanaccess"},
        **{},
    )

    core_config = DataSourceMapper.to_core_config(api_config)

    options = core_config.data_source_cfg["options"]
    assert options["filename"] == "./input/real-db.mdb"
    assert options["ucanaccess_dir"] == "lib/ucanaccess"


def test_map_sqlite_config():
    """Test mapping SQLite configuration."""
    api_config = DataSourceConfig(name="test_sqlite", driver="sqlite", filename="./data/test.db", **{})  # type: ignore

    core_config = DataSourceMapper.to_core_config(api_config)

    assert core_config.name == "test_sqlite"
    assert core_config.data_source_cfg["driver"] == "sqlite"

    options = core_config.data_source_cfg["options"]
    assert options["filename"] == "./data/test.db"


def test_map_csv_config():
    """Test mapping CSV configuration."""
    api_config = DataSourceConfig(
        name="test_csv", driver="csv", filename="./data/test.csv", options={"encoding": "utf-8", "delimiter": ","}, **{}  # type: ignore
    )

    core_config = DataSourceMapper.to_core_config(api_config)

    assert core_config.name == "test_csv"
    assert core_config.data_source_cfg["driver"] == "csv"

    options = core_config.data_source_cfg["options"]
    assert options["filename"] == "./data/test.csv"
    assert options["encoding"] == "utf-8"
    assert options["delimiter"] == ","


def test_missing_required_field():
    """Test error when required field is missing."""
    api_config = DataSourceConfig(
        name="test_pg",
        driver="postgresql",  # type: ignore
        host="localhost",
        **{},
        # Missing required fields: database, username
    )

    with pytest.raises(ValueError, match="Required field missing"):
        DataSourceMapper.to_core_config(api_config)


def test_additional_options_preserved():
    """Test that additional options not in schema are preserved."""
    api_config = DataSourceConfig(
        name="test_pg",
        driver="postgresql",  # type: ignore
        host="localhost",
        database="testdb",
        username="testuser",
        options={
            "custom_option": "custom_value",
            "another_option": 123,
        },
        **{},
    )

    core_config = DataSourceMapper.to_core_config(api_config)

    options = core_config.data_source_cfg["options"]
    assert options["custom_option"] == "custom_value"
    assert options["another_option"] == 123
