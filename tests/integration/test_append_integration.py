"""Integration tests for append feature end-to-end functionality."""

import pandas as pd
import pytest

from src.model import ShapeShiftProject
from src.normalizer import ProcessState, ShapeShifter

# pylint: disable=no-member, redefined-outer-name


class TestAppendIntegration:
    """Test append feature with full normalization pipeline."""

    @pytest.mark.asyncio
    async def test_append_fixed_data(self):
        """Test appending fixed data to entity."""
        # Create a simple survey dataframe
        survey_df = pd.DataFrame(
            {
                "id": ["1", "2"],
                "name": ["Alice", "Bob"],
                "value": ["100", "200"],
            }
        )

        # Create configuration with append
        cfg = {
            "entities": {
                "survey": {
                    "keys": ["id"],
                    "columns": ["id", "name", "value"],
                },
                "test_entity": {
                    "keys": ["id"],
                    "surrogate_id": "test_id",
                    "columns": ["id", "name", "value"],
                    "depends_on": [],
                    "append": [
                        {
                            "type": "fixed",
                            "values": ["3", "4"],
                            "columns": ["id"],
                        }
                    ],
                },
            }
        }

        # Initialize normalizer directly without ConfigStore

        normalizer: ShapeShifter = ShapeShifter(
            table_store={"survey": survey_df},
            project=ShapeShiftProject(cfg=cfg, filename="test-config.yml"),
            default_entity="survey",
        )
        # Run normalization
        await normalizer.normalize()

        # Verify results
        result = normalizer.table_store["test_entity"]

        # Should have 4 rows: 2 from survey + 2 from fixed append
        assert len(result) == 4
        assert "test_id" in result.columns
        assert set(result["id"].values) == {"1", "2", "3", "4"}

    @pytest.mark.asyncio
    async def test_append_from_entity_source(self):
        """Test appending data from another entity."""
        # Create survey dataframe
        survey_df = pd.DataFrame(
            {
                "id": ["1", "2"],
                "name": ["Alice", "Bob"],
                "category": ["A", "B"],
            }
        )

        # Create configuration
        cfg = {
            "entities": {
                "survey": {
                    "keys": ["id"],
                    "columns": ["id", "name", "category"],
                },
                "source_entity": {
                    "keys": ["id"],
                    "surrogate_id": "source_id",
                    "columns": ["id", "category"],
                },
                "target_entity": {
                    "keys": ["id"],
                    "surrogate_id": "target_id",
                    "columns": ["id", "name"],
                    "depends_on": ["source_entity"],
                    "append": [
                        {
                            "source": "source_entity",
                            "columns": ["id", "category"],
                        }
                    ],
                },
            }
        }

        # Initialize normalizer directly without ConfigStore

        normalizer = ShapeShifter.__new__(ShapeShifter)
        normalizer.default_entity = "survey"
        normalizer.table_store = {"survey": survey_df}
        normalizer.project = ShapeShiftProject(cfg=cfg, filename="test-config.yml")
        normalizer.state = ProcessState(config=normalizer.project, table_store=normalizer.table_store, target_entities=None)

        # Run normalization
        await normalizer.normalize()

        # Verify results
        result = normalizer.table_store["target_entity"]

        # Should have 4 rows: 2 from base (id, name) + 2 from append (id, category)
        assert len(result) == 4
        assert "target_id" in result.columns

    @pytest.mark.asyncio
    async def test_append_with_distinct_mode(self):
        """Test append with distinct mode removes duplicates."""
        # Create survey with duplicates
        survey_df = pd.DataFrame(
            {
                "id": ["1", "2", "1"],  # Duplicate id=1
                "name": ["Alice", "Bob", "Alice"],
            }
        )

        # Create configuration with append and distinct mode
        cfg = {
            "entities": {
                "survey": {
                    "keys": ["id"],
                    "columns": ["id", "name"],
                },
                "test_entity": {
                    "keys": ["id"],
                    "surrogate_id": "test_id",
                    "columns": ["id", "name"],
                    "drop_duplicates": ["id"],
                    "append": [
                        {
                            "type": "fixed",
                            "values": ["1"],  # Another duplicate id=1
                            "columns": ["id"],
                        }
                    ],
                    "append_mode": "distinct",
                },
            }
        }

        # Initialize normalizer directly without ConfigStore

        normalizer = ShapeShifter.__new__(ShapeShifter)
        normalizer.default_entity = "survey"
        normalizer.table_store = {"survey": survey_df}
        normalizer.project = ShapeShiftProject(cfg=cfg, filename="test-config.yml")
        normalizer.state = ProcessState(config=normalizer.project, table_store=normalizer.table_store, target_entities=None)

        # Run normalization
        await normalizer.normalize()

        # Verify results
        result = normalizer.table_store["test_entity"]

        # Should have only 2 unique rows after deduplication
        assert len(result) == 2
        assert set(result["id"].values) == {"1", "2"}

    @pytest.mark.asyncio
    async def test_append_with_all_mode(self):
        """Test append with all mode keeps duplicates."""
        # Create survey with duplicates
        survey_df = pd.DataFrame(
            {
                "id": ["1", "2"],
                "name": ["Alice", "Bob"],
            }
        )

        # Create configuration with append and all mode (default)
        cfg = {
            "entities": {
                "survey": {
                    "keys": ["id"],
                    "columns": ["id", "name"],
                },
                "test_entity": {
                    "keys": ["id"],
                    "surrogate_id": "test_id",
                    "columns": ["id", "name"],
                    "append": [
                        {
                            "type": "fixed",
                            "values": ["1"],  # Duplicate id=1
                            "columns": ["id"],
                        }
                    ],
                    "append_mode": "all",
                },
            }
        }

        # Initialize normalizer directly without ConfigStore

        normalizer = ShapeShifter.__new__(ShapeShifter)
        normalizer.default_entity = "survey"
        normalizer.table_store = {"survey": survey_df}
        normalizer.project = ShapeShiftProject(cfg=cfg, filename="test-config.yml")
        normalizer.state = ProcessState(config=normalizer.project, table_store=normalizer.table_store, target_entities=None)

        # Run normalization
        await normalizer.normalize()

        # Verify results
        result = normalizer.table_store["test_entity"]

        # Should have 3 rows: 2 from survey + 1 from append (duplicate allowed)
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_append_multiple_sources(self):
        """Test appending from multiple sources."""
        # Create survey dataframe
        survey_df = pd.DataFrame(
            {
                "id": ["1"],
                "name": ["Alice"],
            }
        )

        # Create configuration with multiple append sources
        cfg = {
            "entities": {
                "survey": {
                    "keys": ["id"],
                    "columns": ["id", "name"],
                },
                "test_entity": {
                    "keys": ["id"],
                    "surrogate_id": "test_id",
                    "columns": ["id", "name"],
                    "append": [
                        {
                            "type": "fixed",
                            "values": ["2"],
                            "columns": ["id"],
                        },
                        {
                            "type": "fixed",
                            "values": ["3"],
                            "columns": ["id"],
                        },
                        {
                            "type": "fixed",
                            "values": ["4"],
                            "columns": ["id"],
                        },
                    ],
                },
            }
        }

        # Initialize normalizer directly without ConfigStore

        normalizer = ShapeShifter.__new__(ShapeShifter)
        normalizer.default_entity = "survey"
        normalizer.table_store = {"survey": survey_df}
        normalizer.project = ShapeShiftProject(cfg=cfg, filename="test-config.yml")
        normalizer.state = ProcessState(config=normalizer.project, table_store=normalizer.table_store, target_entities=None)

        # Run normalization
        await normalizer.normalize()

        # Verify results
        result = normalizer.table_store["test_entity"]

        # Should have 4 rows: 1 from survey + 3 from append sources
        assert len(result) == 4
        assert set(result["id"].values) == {"1", "2", "3", "4"}
