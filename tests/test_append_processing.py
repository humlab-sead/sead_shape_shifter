"""Integration tests for append processing in the normalization pipeline."""

from unittest.mock import patch

import pandas as pd
import pytest

from src.config_model import TablesConfig
from src.normalizer import ArbodatSurveyNormalizer, ProcessState
from tests.decorators import with_test_config

# pylint: disable=no-member, redefined-outer-name


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
    config_dict = {
        "site": {
            "surrogate_id": "site_id",
            "keys": ["site_name"],
            "columns": ["site_name", "latitude", "longitude"],
            "depends_on": [],
            "append": [
                {
                    "source": None,
                    "type": "fixed",
                    "values": [
                        ["Default Site", 0.0, 0.0],
                    ],
                }
            ],
            "append_mode": "all",
        }
    }
    return TablesConfig(entities_cfg=config_dict, options={})


@pytest.fixture
def config_with_sql_append():
    """Create a configuration with SQL append."""
    config_dict = {
        "site": {
            "surrogate_id": "site_id",
            "keys": ["site_name"],
            "columns": ["site_name", "latitude", "longitude"],
            "depends_on": [],
            "append": [
                {
                    "type": "sql",
                    "query": "SELECT 'SQL Site' as site_name, 50.0 as latitude, 15.0 as longitude",
                }
            ],
            "append_mode": "all",
        }
    }
    return TablesConfig(entities_cfg=config_dict, options={})


@pytest.fixture
def config_with_source_append():
    """Create a configuration with source entity append."""
    config_dict = {
        "survey": {
            "surrogate_id": "survey_id",
            "keys": ["survey_name"],
            "columns": ["survey_name", "country"],
            "depends_on": [],
        },
        "site": {
            "surrogate_id": "site_id",
            "keys": ["site_name"],
            "columns": ["site_name", "country"],
            "depends_on": ["survey"],
            "append": [
                {
                    "source": "survey",
                }
            ],
            "append_mode": "all",
        },
    }
    return TablesConfig(entities_cfg=config_dict, options={})


@pytest.fixture
def config_with_distinct_mode():
    """Create a configuration with distinct append mode."""
    config_dict = {
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
                            ["New Site",  48.0,  16.0],
                        ],
                    }
                ],
                "append_mode": "distinct",
            }
    }
    return TablesConfig(entities_cfg=config_dict, options={})


class TestAppendProcessingBasic:
    """Tests for basic append processing functionality."""

    @pytest.mark.asyncio
    @with_test_config
    async def test_append_fixed_data(self, sample_survey_data, config_with_append, test_provider):
        """Test appending fixed data to an entity."""
        normalizer = ArbodatSurveyNormalizer(sample_survey_data)
        normalizer.config = config_with_append
        normalizer.state = ProcessState(config=normalizer.config)

        # Process all entities
        await normalizer.normalize()

        # Get the result from the table store
        result = normalizer.table_store["site"]

        # Should have original 3 rows + 1 appended row
        assert len(result) == 4
        assert "Default Site" in result["site_name"].values
        assert result[result["site_name"] == "Default Site"]["latitude"].iloc[0] == 0.0

    @pytest.mark.asyncio
    @with_test_config
    async def test_append_mode_all(self, sample_survey_data, config_with_append, test_provider):
        """Test append mode 'all' keeps duplicates."""
        normalizer = ArbodatSurveyNormalizer(sample_survey_data)
        normalizer.config = config_with_append
        normalizer.state = ProcessState(config=normalizer.config)

        # Process all entities
        await normalizer.normalize()

        # Get the result from the table store
        result = normalizer.table_store["site"]

        # With append_mode='all', all rows are kept
        assert len(result) == 4

    @pytest.mark.asyncio
    @with_test_config
    async def test_append_mode_distinct(self, sample_survey_data, config_with_distinct_mode, test_provider):
        """Test append mode 'distinct' removes duplicates."""
        normalizer = ArbodatSurveyNormalizer(sample_survey_data)
        normalizer.config = config_with_distinct_mode
        normalizer.state = ProcessState(config=normalizer.config)

        # Process all entities
        await normalizer.normalize()

        # Get the result from the table store
        result = normalizer.table_store["site"]

        # Should deduplicate: 3 original + 1 new (duplicate removed)
        assert len(result) == 4
        assert result["site_name"].value_counts()["Site A"] == 1  # Deduplicated


class TestAppendProcessingSQL:
    """Tests for SQL-based append processing."""

    @pytest.mark.asyncio
    @with_test_config
    async def test_append_sql_query(self, sample_survey_data, config_with_sql_append, test_provider):
        """Test appending data from SQL query."""
        normalizer = ArbodatSurveyNormalizer(sample_survey_data)
        normalizer.config = config_with_sql_append
        normalizer.state = ProcessState(config=normalizer.config)

        sql_result = pd.DataFrame(
            {
                "site_name": ["SQL Site"],
                "latitude": [50.0],
                "longitude": [15.0],
            }
        )

        # Mock SqlLoader to return the SQL result
        with patch("src.normalizer.SqlLoaderFactory") as mock_factory:
            mock_loader = mock_factory.return_value.create_loader.return_value
            mock_loader.load.return_value = sql_result

            # Process all entities
            await normalizer.normalize()

            # Get the result from the table store
            result = normalizer.table_store["site"]

            # Should have original 3 rows + 1 SQL row
            assert len(result) == 4
            assert "SQL Site" in result["site_name"].values


class TestAppendProcessingSourceEntity:
    """Tests for source entity-based append processing."""

    @pytest.mark.asyncio
    @with_test_config
    async def test_append_from_source_entity(self, sample_survey_data, config_with_source_append, test_provider):
        """Test appending data from another entity."""
        # Use survey data that has the columns needed
        survey_data = pd.DataFrame(
            {
                "survey_name": ["Survey 1", "Survey 2"],
                "country": ["Finland", "Iceland"],
            }
        )


        normalizer = ArbodatSurveyNormalizer(survey_data)
        normalizer.config = config_with_source_append
        normalizer.state = ProcessState(config=normalizer.config)

        # Process all entities
        await normalizer.normalize()

        # Get the result from the table store
        result = normalizer.table_store["site"]

        # Should have data from survey entity mapped to site columns
        assert len(result) == 2
        assert "Survey 1" in result["site_name"].values
        assert "Survey 2" in result["site_name"].values


class TestAppendProcessingMultiple:
    """Tests for multiple append configurations."""

    @pytest.mark.asyncio
    @with_test_config
    async def test_multiple_append_items(self, sample_survey_data, test_provider):
        """Test appending from multiple sources."""
        config_dict = {
            "site": {
                "surrogate_id": "site_id",
                "keys": ["site_name"],
                "columns": ["site_name", "latitude", "longitude"],
                "depends_on": [],
                "append": [
                    {
                        "type": "fixed",
                        "values": [
                            ["Fixed 1", 10.0, 20.0],
                        ],
                    },
                    {
                        "type": "fixed",
                        "values": [
                            ["Fixed 2", 30.0, 40.0],
                        ],
                    },
                ],
                "append_mode": "all",
            }
        }

        config = TablesConfig(entities_cfg=config_dict, options={})
        normalizer = ArbodatSurveyNormalizer(sample_survey_data)
        normalizer.config = config
        normalizer.state = ProcessState(config=normalizer.config)

        # Process all entities
        await normalizer.normalize()

        # Get the result from the table store
        result = normalizer.table_store["site"]

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
        config_dict = {
            "site": {
                    "surrogate_id": "site_id",
                    "keys": ["site_name"],
                    "columns": ["site_name", "latitude"],
                    "depends_on": [],
                    "append": [
                        {
                            "type": "fixed",
                            "values": [
                                ["Only Site", 50.0],
                            ],
                        }
                    ],
                    "append_mode": "all",
                }
        }

        config = TablesConfig(entities_cfg=config_dict, options={})
        empty_data = pd.DataFrame(columns=["site_name", "latitude"])
        normalizer = ArbodatSurveyNormalizer(empty_data)
        normalizer.config = config
        normalizer.state = ProcessState(config=normalizer.config)
        normalizer.state = ProcessState(config=normalizer.config)

        # Process all entities
        await normalizer.normalize()

        # Get the result from the table store
        result = normalizer.table_store["site"]

        # Should only have the appended row
        assert len(result) == 1
        assert result["site_name"].iloc[0] == "Only Site"

    @pytest.mark.asyncio
    @with_test_config
    async def test_append_preserves_columns(self, sample_survey_data, test_provider):
        """Test that append preserves all configured columns."""
        config_dict = {
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
                }
        }

        config = TablesConfig(entities_cfg=config_dict, options={})
        normalizer = ArbodatSurveyNormalizer(sample_survey_data)
        normalizer.config = config
        normalizer.state = ProcessState(config=normalizer.config)

        # Process all entities
        await normalizer.normalize()

        # Get the result from the table store
        result = normalizer.table_store["site"]

        # Check all columns are present
        assert set(result.columns) >= {"site_name", "latitude", "longitude", "country"}

        # Check that missing values are NaN
        partial_row = result[result["site_name"] == "Partial Site"]
        assert pd.isna(partial_row["longitude"].iloc[0])
        assert pd.isna(partial_row["country"].iloc[0])
