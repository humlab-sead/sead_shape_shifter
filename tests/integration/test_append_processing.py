"""Integration tests for append processing in the normalization pipeline."""

from unittest.mock import AsyncMock, patch

import pandas as pd
import pytest

from src.model import ShapeShiftProject
from src.normalizer import ShapeShifter
from tests.decorators import with_test_config

# pylint: disable=no-member, redefined-outer-name, unused-argument


@pytest.fixture
def sample_survey_data():
    """Create sample survey data for testing."""
    return pd.DataFrame(
        {
            "site_name": ["Site A", "Site B", "Site C"],
            "latitude": [45.1, 46.2, 47.3],
            "longitude": [12.1, 13.2, 14.3],
            "country": ["Sweden", "Norway", "Denmark"],
        }
    )


@pytest.fixture
def config_with_append():
    """Create a configuration with append settings."""
    cfg = {
        "entities": {
            "default": {"source": None, "depends_on": []},
            "site": {
                "surrogate_id": "site_id",
                "keys": ["site_name"],
                "columns": ["site_name", "latitude", "longitude"],
                "depends_on": [],
                "append": [
                    {
                        "source": None,
                        "type": "fixed",
                        "values": [["Default Site", 0.0, 0.0]],
                    }
                ],
                "append_mode": "all",
            },
        }
    }
    return ShapeShiftProject(cfg=cfg, filename="test-config.yml")


@pytest.fixture
def config_with_source_append():
    """Create a configuration with source entity append."""
    cfg = {
        "entities": {
            "default": {
                "surrogate_id": "survey_id",
                "keys": ["survey_name"],
                "columns": ["survey_name", "country"],
                "depends_on": [],
            },
            "site": {
                "surrogate_id": "site_id",
                "keys": ["site_name"],
                "columns": ["site_name", "country"],
                "depends_on": ["default"],
                "append": [{"source": "default"}],
                "append_mode": "all",
            },
        }
    }
    return ShapeShiftProject(cfg=cfg, filename="test-config.yml")


@pytest.fixture
def config_with_distinct_mode():
    """Create a configuration with distinct append mode."""
    cfg = {
        "entities": {
            "default": {"source": None, "depends_on": []},
            "site": {
                "surrogate_id": "site_id",
                "keys": ["site_name"],
                "columns": ["site_name", "latitude", "longitude"],
                "depends_on": [],
                "append": [
                    {
                        "type": "fixed",
                        "values": [
                            ["Site A", 45.1, 12.1],
                            ["New Site", 48.0, 16.0],
                        ],
                    }
                ],
                "append_mode": "distinct",
            },
        }
    }
    return ShapeShiftProject(cfg=cfg, filename="test-config.yml")


class TestAppendProcessingBasic:
    """Tests for basic append processing functionality."""

    @pytest.mark.asyncio
    @with_test_config
    async def test_append_fixed_data(self, sample_survey_data, config_with_append, test_provider):  # pylint: disable=unused-argument
        """Test appending fixed data to an entity."""
        table_store = {"default": sample_survey_data.copy()}
        normalizer = ShapeShifter(default_entity="default", project=config_with_append, table_store=table_store)

        await normalizer.normalize()

        result = normalizer.table_store["site"]

        # Should have original 3 rows + 1 appended row
        assert len(result) == 4
        assert "Default Site" in result["site_name"].values
        assert result[result["site_name"] == "Default Site"]["latitude"].iloc[0] == 0.0

    @pytest.mark.asyncio
    @with_test_config
    async def test_append_mode_all(self, sample_survey_data, config_with_append, test_provider):  # pylint: disable=unused-argument
        """Test append mode 'all' keeps duplicates."""
        table_store = {"default": sample_survey_data.copy()}
        normalizer = ShapeShifter(default_entity="default", project=config_with_append, table_store=table_store)

        await normalizer.normalize()

        result = normalizer.table_store["site"]

        assert len(result) == 4

    @pytest.mark.asyncio
    @with_test_config
    async def test_append_mode_distinct(
        self, sample_survey_data, config_with_distinct_mode, test_provider
    ):  # pylint: disable=unused-argument
        """Test append mode 'distinct' removes duplicates."""
        table_store = {"default": sample_survey_data.copy()}
        normalizer = ShapeShifter(default_entity="default", project=config_with_distinct_mode, table_store=table_store)

        await normalizer.normalize()

        result = normalizer.table_store["site"]

        # Should deduplicate: 3 original + 1 new (duplicate removed)
        assert len(result) == 4
        assert result["site_name"].value_counts()["Site A"] == 1  # Deduplicated


class TestAppendProcessingSQL:
    """Tests for SQL-based append processing."""

    @pytest.mark.asyncio
    @with_test_config
    async def test_append_sql_query(self, sample_survey_data, test_provider):  # pylint: disable=unused-argument
        """Test appending data from SQL query."""

        config_with_sql_append = ShapeShiftProject(
            cfg={
                "entities": {
                    "survey": {
                        "source": None,
                        "columns": ["site_name", "latitude", "longitude", "country"],
                        "depends_on": [],
                    },
                    "site": {
                        "surrogate_id": "site_id",
                        "keys": ["site_name"],
                        "columns": ["site_name", "latitude", "longitude"],
                        "depends_on": [],
                        "append": [
                            {
                                "data_source": "test_sql_source",
                                "type": "sql",
                                "values": "sql: SELECT 'SQL Site' as site_name, 50.0 as latitude, 15.0 as longitude",
                            }
                        ],
                        "append_mode": "all",
                    },
                }
            },
            filename="test-config.yml",
        )
        sub_configs = list(config_with_sql_append.get_table("site").get_sub_table_configs())
        assert len(sub_configs) == 2  # Base + SQL append

        table_store = {"survey": sample_survey_data.copy()}
        normalizer = ShapeShifter(default_entity="survey", project=config_with_sql_append, table_store=table_store)

        sql_result = pd.DataFrame({"site_name": ["SQL Site"], "latitude": [50.0], "longitude": [15.0], "country": ["Sweden"]})

        # Mock resolve_loader to return a mock SQL loader
        mock_loader = AsyncMock()
        mock_loader.load = AsyncMock(return_value=sql_result)

        with patch.object(normalizer.config, "resolve_loader", side_effect=[None, mock_loader]):
            # First config has no loader, second uses mock_loader.
            await normalizer.normalize()
            result: pd.DataFrame = normalizer.table_store["site"]
            assert len(result) == 4
            assert "SQL Site" in result["site_name"].values


class TestAppendProcessingMultiple:
    """Tests for multiple append configurations."""

    @pytest.fixture
    def survey_only_config(self) -> ShapeShiftProject:
        return ShapeShiftProject(
            cfg={
                "entities": {
                    "survey": {"depends_on": []},
                }
            },
            filename="test-config.yml",
        )

    @pytest.mark.asyncio
    @with_test_config
    async def test_multiple_append_items(self, sample_survey_data, test_provider):  # pylint: disable=unused-argument
        """Test appending from multiple sources."""
        cfg = {
            "entities": {
                "survey": {
                    "source": None,
                    "columns": ["site_name", "latitude", "longitude", "country"],
                    "depends_on": [],
                },
                "site": {
                    "surrogate_id": "site_id",
                    "keys": ["site_name"],
                    "columns": ["site_name", "latitude", "longitude"],
                    "depends_on": [],
                    "append": [
                        {"type": "fixed", "values": [["Fixed 1", 10.0, 20.0]]},
                        {"type": "fixed", "values": [["Fixed 2", 30.0, 40.0]]},
                    ],
                    "append_mode": "all",
                },
            }
        }

        config = ShapeShiftProject(cfg=cfg, filename="test-config.yml")
        table_store: dict[str, pd.DataFrame] = {"survey": sample_survey_data}
        normalizer = ShapeShifter(project=config, default_entity="survey", table_store=table_store)

        await normalizer.normalize()

        result: pd.DataFrame = normalizer.table_store["site"]

        # Should have original 3 rows + 2 appended rows
        assert len(result) == 5
        assert "Fixed 1" in result["site_name"].values
        assert "Fixed 2" in result["site_name"].values


class TestAppendProcessingEdgeCases:
    """Tests for edge cases in append processing."""

    @pytest.mark.asyncio
    @with_test_config
    async def test_append_with_empty_main_data(self, test_provider):
        """Test append when main entity returns no data."""
        cfg = {
            "entities": {
                "default": {
                    "source": None,
                    "type": "fixed",
                    "columns": ["site_name", "latitude"],
                    "values": [],
                    "depends_on": [],
                },
                "site": {
                    "source": "default",
                    "type": "fixed",
                    "surrogate_id": "site_id",
                    "keys": ["site_name"],
                    "columns": ["site_name", "latitude"],
                    "values": [],
                    "depends_on": [],
                    "append": [{"type": "fixed", "values": [["Only Site", 50.0]]}],
                    "append_mode": "all",
                },
            }
        }

        config = ShapeShiftProject(cfg=cfg, filename="test-config.yml")
        empty_data = pd.DataFrame(columns=["site_name", "latitude"])
        table_store = {"default": empty_data}
        normalizer = ShapeShifter(project=config, table_store=table_store, default_entity="default")

        await normalizer.normalize()

        result = normalizer.table_store["site"]

        # Should only have the appended row
        assert len(result) == 1
        assert result["site_name"].iloc[0] == "Only Site"

    @pytest.mark.asyncio
    @with_test_config
    async def test_append_preserves_columns(self, sample_survey_data, test_provider):  # pylint: disable=unused-argument
        """Test that append preserves all configured columns."""
        cfg = {
            "entities": {
                "survey": {
                    "source": None,
                    "depends_on": [],
                },
                "site": {
                    "surrogate_id": "site_id",
                    "keys": ["site_name"],
                    "columns": ["site_name", "latitude", "longitude", "country"],
                    "depends_on": [],
                    "append": [
                        {
                            "type": "fixed",
                            "values": [
                                ["Partial Site", 50.0, None, None],  # Missing longitude and country
                            ],
                        }
                    ],
                    "append_mode": "all",
                },
            }
        }

        config = ShapeShiftProject(cfg=cfg, filename="test-config.yml")
        table_store = {"survey": sample_survey_data}
        normalizer = ShapeShifter(default_entity="survey", project=config, table_store=table_store)

        await normalizer.normalize()

        result = normalizer.table_store["site"]

        # Check all columns are present
        assert set(result.columns) >= {"site_name", "latitude", "longitude", "country"}

        # Check that missing values are NaN
        partial_row = result[result["site_name"] == "Partial Site"]
        assert pd.isna(partial_row["longitude"].iloc[0])
        assert pd.isna(partial_row["country"].iloc[0])
