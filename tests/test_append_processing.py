"""Integration tests for append processing in the normalization pipeline."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pandas as pd
import pytest

from src.arbodat.config_model import TableConfig, TablesConfig
from src.arbodat.normalizer import ArbodatSurveyNormalizer


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
        "entities": {
            "site": {
                "surrogate_id": "site_id",
                "keys": ["site_name"],
                "columns": ["site_name", "latitude", "longitude"],
                "append": [
                    {
                        "type": "fixed",
                        "values": [
                            {"site_name": "Default Site", "latitude": 0.0, "longitude": 0.0},
                        ],
                    }
                ],
                "append_mode": "all",
            }
        }
    }
    return TablesConfig(config_dict)


@pytest.fixture
def config_with_sql_append():
    """Create a configuration with SQL append."""
    config_dict = {
        "entities": {
            "site": {
                "surrogate_id": "site_id",
                "keys": ["site_name"],
                "columns": ["site_name", "latitude", "longitude"],
                "append": [
                    {
                        "type": "sql",
                        "query": "SELECT 'SQL Site' as site_name, 50.0 as latitude, 15.0 as longitude",
                    }
                ],
                "append_mode": "all",
            }
        }
    }
    return TablesConfig(config_dict)


@pytest.fixture
def config_with_source_append():
    """Create a configuration with source entity append."""
    config_dict = {
        "entities": {
            "survey": {
                "surrogate_id": "survey_id",
                "keys": ["survey_name"],
                "columns": ["survey_name", "country"],
            },
            "site": {
                "surrogate_id": "site_id",
                "keys": ["site_name"],
                "columns": ["site_name", "country"],
                "append": [
                    {
                        "source": "survey",
                        "columns": {"survey_name": "site_name", "country": "country"},
                    }
                ],
                "append_mode": "all",
            },
        }
    }
    return TablesConfig(config_dict)


@pytest.fixture
def config_with_distinct_mode():
    """Create a configuration with distinct append mode."""
    config_dict = {
        "entities": {
            "site": {
                "surrogate_id": "site_id",
                "keys": ["site_name"],
                "columns": ["site_name", "latitude", "longitude"],
                "append": [
                    {
                        "type": "fixed",
                        "values": [
                            {"site_name": "Site A", "latitude": 45.1, "longitude": 12.1},  # Duplicate
                            {"site_name": "New Site", "latitude": 48.0, "longitude": 16.0},
                        ],
                    }
                ],
                "append_mode": "distinct",
            }
        }
    }
    return TablesConfig(config_dict)


class TestAppendProcessingBasic:
    """Tests for basic append processing functionality."""

    @pytest.mark.asyncio
    async def test_append_fixed_data(self, sample_survey_data, config_with_append):
        """Test appending fixed data to an entity."""
        normalizer = ArbodatSurveyNormalizer(sample_survey_data)
        normalizer.config = config_with_append

        table_cfg = config_with_append.get_table("site")

        # Mock the subset service to return the survey data mapped to site columns
        with patch.object(normalizer.subset_service, "get_subset") as mock_subset:
            mock_subset.return_value = sample_survey_data[["site_name", "latitude", "longitude"]].rename(
                columns={"site_name": "site_name"}
            )

            # Process the site entity
            result = await normalizer.normalize(table_cfg)

            # Should have original 3 rows + 1 appended row
            assert len(result) == 4
            assert "Default Site" in result["site_name"].values
            assert result[result["site_name"] == "Default Site"]["latitude"].iloc[0] == 0.0

    @pytest.mark.asyncio
    async def test_append_mode_all(self, sample_survey_data, config_with_append):
        """Test append mode 'all' keeps duplicates."""
        normalizer = ArbodatSurveyNormalizer(sample_survey_data)
        normalizer.config = config_with_append

        table_cfg = config_with_append.get_table("site")

        with patch.object(normalizer.subset_service, "get_subset") as mock_subset:
            mock_subset.return_value = sample_survey_data[["site_name", "latitude", "longitude"]]

            result = await normalizer.normalize(table_cfg)

            # With append_mode='all', all rows are kept
            assert len(result) == 4

    @pytest.mark.asyncio
    async def test_append_mode_distinct(self, sample_survey_data, config_with_distinct_mode):
        """Test append mode 'distinct' removes duplicates."""
        normalizer = ArbodatSurveyNormalizer(sample_survey_data)
        normalizer.config = config_with_distinct_mode

        table_cfg = config_with_distinct_mode.get_table("site")

        with patch.object(normalizer.subset_service, "get_subset") as mock_subset:
            mock_subset.return_value = sample_survey_data[["site_name", "latitude", "longitude"]]

            result = await normalizer.normalize(table_cfg)

            # Should deduplicate: 3 original + 1 new (duplicate removed)
            assert len(result) == 4
            assert result["site_name"].value_counts()["Site A"] == 1  # Deduplicated


class TestAppendProcessingSQL:
    """Tests for SQL-based append processing."""

    @pytest.mark.asyncio
    async def test_append_sql_query(self, sample_survey_data, config_with_sql_append):
        """Test appending data from SQL query."""
        normalizer = ArbodatSurveyNormalizer(sample_survey_data)
        normalizer.config = config_with_sql_append

        table_cfg = config_with_sql_append.get_table("site")

        sql_result = pd.DataFrame(
            {
                "site_name": ["SQL Site"],
                "latitude": [50.0],
                "longitude": [15.0],
            }
        )

        with patch.object(normalizer.subset_service, "get_subset") as mock_subset:
            with patch.object(normalizer.database_service, "read_sql") as mock_sql:
                mock_subset.return_value = sample_survey_data[["site_name", "latitude", "longitude"]]
                mock_sql.return_value = sql_result

                result = await normalizer.normalize(table_cfg)

                # Should have original 3 rows + 1 SQL row
                assert len(result) == 4
                assert "SQL Site" in result["site_name"].values
                mock_sql.assert_called_once()


class TestAppendProcessingSourceEntity:
    """Tests for source entity-based append processing."""

    @pytest.mark.asyncio
    async def test_append_from_source_entity(self, sample_survey_data, config_with_source_append):
        """Test appending data from another entity."""
        normalizer = ArbodatSurveyNormalizer(sample_survey_data)
        normalizer.config = config_with_source_append

        # Add survey entity to table store
        survey_data = pd.DataFrame(
            {
                "survey_name": ["Survey 1", "Survey 2"],
                "country": ["Finland", "Iceland"],
            }
        )
        normalizer.table_store["survey"] = survey_data

        table_cfg = config_with_source_append.get_table("site")

        with patch.object(normalizer.subset_service, "get_subset") as mock_subset:

            def subset_side_effect(data, cfg):
                # For the main site entity, return empty dataframe
                if cfg.entity_name == "site":
                    return pd.DataFrame(columns=["site_name", "country"])
                return data

            mock_subset.side_effect = subset_side_effect

            result = await normalizer.normalize(table_cfg)

            # Should have data from survey entity mapped to site columns
            assert len(result) == 2
            assert "Survey 1" in result["site_name"].values
            assert "Survey 2" in result["site_name"].values


class TestAppendProcessingMultiple:
    """Tests for multiple append configurations."""

    @pytest.mark.asyncio
    async def test_multiple_append_items(self, sample_survey_data):
        """Test appending from multiple sources."""
        config_dict = {
            "entities": {
                "site": {
                    "surrogate_id": "site_id",
                    "keys": ["site_name"],
                    "columns": ["site_name", "latitude", "longitude"],
                    "append": [
                        {
                            "type": "fixed",
                            "values": [
                                {"site_name": "Fixed 1", "latitude": 10.0, "longitude": 20.0},
                            ],
                        },
                        {
                            "type": "fixed",
                            "values": [
                                {"site_name": "Fixed 2", "latitude": 30.0, "longitude": 40.0},
                            ],
                        },
                    ],
                    "append_mode": "all",
                }
            }
        }

        config = TablesConfig(config_dict)
        normalizer = ArbodatSurveyNormalizer(sample_survey_data)
        normalizer.config = config

        table_cfg = config.get_table("site")

        with patch.object(normalizer.subset_service, "get_subset") as mock_subset:
            mock_subset.return_value = sample_survey_data[["site_name", "latitude", "longitude"]].rename(
                columns={"site_name": "site_name"}
            )

            result = await normalizer.normalize(table_cfg)

            # Should have original 3 rows + 2 appended rows
            assert len(result) == 5
            assert "Fixed 1" in result["site_name"].values
            assert "Fixed 2" in result["site_name"].values


class TestAppendProcessingEdgeCases:
    """Tests for edge cases in append processing."""

    @pytest.mark.asyncio
    async def test_append_with_empty_main_data(self):
        """Test append when main entity returns no data."""
        config_dict = {
            "entities": {
                "site": {
                    "surrogate_id": "site_id",
                    "keys": ["site_name"],
                    "columns": ["site_name", "latitude"],
                    "append": [
                        {
                            "type": "fixed",
                            "values": [
                                {"site_name": "Only Site", "latitude": 50.0},
                            ],
                        }
                    ],
                    "append_mode": "all",
                }
            }
        }

        config = TablesConfig(config_dict)
        empty_data = pd.DataFrame(columns=["site_name", "latitude"])
        normalizer = ArbodatSurveyNormalizer(empty_data)
        normalizer.config = config

        table_cfg = config.get_table("site")

        with patch.object(normalizer.subset_service, "get_subset") as mock_subset:
            mock_subset.return_value = empty_data

            result = await normalizer.normalize(table_cfg)

            # Should only have the appended row
            assert len(result) == 1
            assert result["site_name"].iloc[0] == "Only Site"

    @pytest.mark.asyncio
    async def test_append_preserves_columns(self, sample_survey_data):
        """Test that append preserves all configured columns."""
        config_dict = {
            "entities": {
                "site": {
                    "surrogate_id": "site_id",
                    "keys": ["site_name"],
                    "columns": ["site_name", "latitude", "longitude", "country"],
                    "append": [
                        {
                            "type": "fixed",
                            "values": [
                                {"site_name": "Partial Site", "latitude": 50.0},  # Missing longitude and country
                            ],
                        }
                    ],
                    "append_mode": "all",
                }
            }
        }

        config = TablesConfig(config_dict)
        normalizer = ArbodatSurveyNormalizer(sample_survey_data)
        normalizer.config = config

        table_cfg = config.get_table("site")

        with patch.object(normalizer.subset_service, "get_subset") as mock_subset:
            mock_subset.return_value = sample_survey_data[["site_name", "latitude", "longitude", "country"]]

            result = await normalizer.normalize(table_cfg)

            # Check all columns are present
            assert set(result.columns) >= {"site_name", "latitude", "longitude", "country"}

            # Check that missing values are NaN
            partial_row = result[result["site_name"] == "Partial Site"]
            assert pd.isna(partial_row["longitude"].iloc[0])
            assert pd.isna(partial_row["country"].iloc[0])
