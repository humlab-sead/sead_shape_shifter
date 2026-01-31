"""Integration tests for append feature end-to-end functionality."""

import pandas as pd
import pytest

from src.model import ShapeShiftProject
from src.normalizer import ShapeShifter

# pylint: disable=no-member, redefined-outer-name


class TestAppendIntegration:
    """Test append feature with full normalization pipeline."""

    @pytest.mark.asyncio
    async def test_append_fixed_data(self):
        """Test appending fixed data to entity."""
        # Create a simple survey dataframe
        survey_df = pd.DataFrame(
            {
                "system_id": [1, 2],
                "id": ["a", "b"],
                "name": ["Alice", "Bob"],
                "value": ["100", "200"],
            }
        )

        # Create configuration with append
        cfg = {
            "entities": {
                "survey": {
                    "keys": ["id"],
                    "columns": ["system_id", "id", "name", "value"],
                },
                "test_entity": {
                    "source": "survey",
                    "keys": ["id"],
                    "public_id": "test_id",
                    "columns": ["system_id", "id", "name", "value"],
                    "depends_on": [],
                    "append": [
                        {
                            "type": "fixed",
                            "values": [[3, "c", None, None], [4, "d", None, None]],
                            "columns": ["system_id", "id", "name", "value"],
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
        assert "id" in result.columns
        assert set(result["id"].values) == {"a", "b", "c", "d"}

    @pytest.mark.asyncio
    async def test_append_from_entity_source(self):
        """Test appending data from another entity.

        Demonstrates vertical concatenation (UNION-like behavior):
        - Base entity extracts 2 rows from survey with columns [id, name]
        - Append extracts 2 rows from source_entity with columns [id, category]
        - Result: 4 rows total with columns [id, name, category]
        """
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
                    # Extracts from survey (default_entity)
                    "keys": ["id"],
                    "columns": ["id", "category"],  # Subset: only id and category
                },
                "target_entity": {
                    # Base: extracts from survey (default_entity)
                    "keys": ["id"],
                    "columns": ["id", "name"],  # Subset: only id and name
                    "depends_on": ["source_entity"],
                    "append": [
                        {
                            # Append: extracts from source_entity
                            "source": "source_entity",
                            "columns": ["id", "category"],  # These are the columns in source_entity
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
        result = normalizer.table_store["target_entity"]

        # VERTICAL CONCATENATION BEHAVIOR:
        # Row 1-2: From base (survey → target_entity)
        #   id="1", name="Alice", category=NaN
        #   id="2", name="Bob", category=NaN
        # Row 3-4: From append (survey → source_entity → target_entity)
        #   id="1", name=NaN, category="A"
        #   id="2", name=NaN, category="B"
        assert len(result) == 4
        assert set(result.columns) >= {"id", "name", "category", "system_id"}

        # Verify data structure
        assert result["id"].tolist() == ["1", "2", "1", "2"]
        assert result["name"].tolist()[:2] == ["Alice", "Bob"]  # First 2 rows have names
        assert pd.isna(result["name"].tolist()[2:]).all()  # Last 2 rows have NaN names
        assert pd.isna(result["category"].tolist()[:2]).all()  # First 2 rows have NaN category
        assert result["category"].tolist()[2:] == ["A", "B"]  # Last 2 rows have categories

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
                    "public_id": "test_id",
                    "columns": ["id", "name"],
                    "drop_duplicates": ["id"],
                    "strict_functional_dependency": False,
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

        normalizer: ShapeShifter = ShapeShifter(
            table_store={"survey": survey_df},
            project=ShapeShiftProject(cfg=cfg, filename="test-config.yml"),
            default_entity="survey",
        )
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
                    "public_id": "test_id",
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

        normalizer: ShapeShifter = ShapeShifter(
            table_store={"survey": survey_df},
            project=ShapeShiftProject(cfg=cfg, filename="test-config.yml"),
            default_entity="survey",
        )
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
                    "public_id": "test_id",
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

        normalizer: ShapeShifter = ShapeShifter(
            table_store={"survey": survey_df},
            project=ShapeShiftProject(cfg=cfg, filename="test-config.yml"),
            default_entity="survey",
        )
        # Run normalization
        await normalizer.normalize()

        # Verify results
        result = normalizer.table_store["test_entity"]

        # Should have 4 rows: 1 from survey + 3 from append sources
        assert len(result) == 4
        assert set(result["id"].values) == {"1", "2", "3", "4"}

    @pytest.mark.asyncio
    async def test_append_with_public_id_column(self):
        """Test that public_id column is properly handled in append configurations.

        When public_id is defined:
        1. The column is filtered from append source extractions
        2. After concatenation, the column is added with None values
        3. This avoids 'column not found' warnings and provides proper structure
        """
        # Create survey dataframe - note: no 'target_id' column in source data
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
                    "public_id": "source_id",
                    "columns": ["id", "category"],
                },
                "target_entity": {
                    "keys": ["id"],
                    "public_id": "target_id",  # This column doesn't exist in source!
                    "columns": ["target_id", "id", "name"],  # Includes target_id
                    "depends_on": ["source_entity"],
                    "append": [
                        {
                            "source": "source_entity",
                            "columns": ["source_id", "id", "category"],  # Includes source_id
                        }
                    ],
                },
            }
        }

        normalizer: ShapeShifter = ShapeShifter(
            table_store={"survey": survey_df},
            project=ShapeShiftProject(cfg=cfg, filename="test-config.yml"),
            default_entity="survey",
        )

        await normalizer.normalize()

        result = normalizer.table_store["target_entity"]

        # Verify the structure
        assert len(result) == 4  # 2 base + 2 append

        # Public_id columns should be present and initialized to None
        assert "target_id" in result.columns
        assert result["target_id"].isna().all()  # All None after append

        # Verify data from both sources is present
        assert set(result.columns) >= {"target_id", "id", "name", "category", "system_id"}
        assert result["id"].tolist() == ["1", "2", "1", "2"]

    @pytest.mark.asyncio
    async def test_append_with_align_by_position(self):
        """Test align_by_position renames columns from append source by position.

        When align_by_position is true, columns from the append source are renamed
        to match the parent entity's columns based on their position, enabling
        union of entities with different column names but same structure.
        """
        # Create two survey dataframes with different column names
        survey_df = pd.DataFrame(
            {
                "id": ["1", "2"],
                "name": ["Alice", "Bob"],
                "category": ["A", "B"],
            }
        )

        legacy_df = pd.DataFrame(
            {
                "old_id": ["3", "4"],
                "legacy_name": ["Charlie", "Diana"],
                "type_code": ["C", "D"],
            }
        )

        # Source entity has different column names
        cfg = {
            "entities": {
                "survey": {
                    "keys": ["id"],
                    "columns": ["id", "name", "category"],
                },
                "legacy_survey": {
                    "keys": ["old_id"],
                    "columns": ["old_id", "legacy_name", "type_code"],  # Different names!
                },
                "target_entity": {
                    "keys": ["id"],
                    "columns": ["id", "name", "category"],
                    "depends_on": ["legacy_survey"],
                    "append": [
                        {
                            "source": "legacy_survey",
                            # Don't specify columns - inherit from legacy_survey
                            "align_by_position": True,  # Rename legacy columns to parent's
                        }
                    ],
                },
            }
        }

        normalizer: ShapeShifter = ShapeShifter(
            table_store={"survey": survey_df, "legacy_survey": legacy_df},
            project=ShapeShiftProject(cfg=cfg, filename="test-config.yml"),
            default_entity="survey",
        )

        await normalizer.normalize()

        result = normalizer.table_store["target_entity"]

        # Debug: print result
        print("\n=== Result DataFrame ===")
        print(result)
        print("\n=== Columns ===")
        print(list(result.columns))
        print("\n=== Data types ===")
        print(result.dtypes)

        # Should have 4 rows with aligned columns
        assert len(result) == 4
        assert set(result.columns) >= {"id", "name", "category", "system_id"}

        # First 2 rows from survey (base)
        assert result["id"].tolist()[:2] == ["1", "2"]
        assert result["name"].tolist()[:2] == ["Alice", "Bob"]
        assert result["category"].tolist()[:2] == ["A", "B"]

        # Last 2 rows from legacy_survey (append, renamed)
        assert result["id"].tolist()[2:] == ["3", "4"]
        assert result["name"].tolist()[2:] == ["Charlie", "Diana"]
        assert result["category"].tolist()[2:] == ["C", "D"]

    @pytest.mark.asyncio
    async def test_append_with_column_mapping(self):
        """Test column_mapping explicitly renames specific columns from append source.

        column_mapping provides explicit control over which columns get renamed,
        useful for partial renaming or non-sequential mappings.
        """
        # Create two survey dataframes
        survey_df = pd.DataFrame(
            {
                "id": ["1", "2"],
                "name": ["Alice", "Bob"],
                "category": ["A", "B"],
            }
        )

        legacy_df = pd.DataFrame(
            {
                "old_id": ["3", "4"],
                "person_name": ["Charlie", "Diana"],
                "type_code": ["C", "D"],
            }
        )

        cfg = {
            "entities": {
                "survey": {
                    "keys": ["id"],
                    "columns": ["id", "name", "category"],
                },
                "legacy_survey": {
                    "keys": ["old_id"],
                    "columns": ["old_id", "person_name", "type_code"],  # Mixed names
                },
                "target_entity": {
                    "keys": ["id"],
                    "columns": ["id", "name", "category"],
                    "depends_on": ["legacy_survey"],
                    "append": [
                        {
                            "source": "legacy_survey",
                            # Don't specify columns - inherit from legacy_survey
                            "column_mapping": {  # Explicit mapping
                                "old_id": "id",
                                "person_name": "name",
                                "type_code": "category",
                            },
                        }
                    ],
                },
            }
        }

        normalizer: ShapeShifter = ShapeShifter(
            table_store={"survey": survey_df, "legacy_survey": legacy_df},
            project=ShapeShiftProject(cfg=cfg, filename="test-config.yml"),
            default_entity="survey",
        )

        await normalizer.normalize()

        result = normalizer.table_store["target_entity"]

        # Should have 4 rows with mapped columns
        assert len(result) == 4
        assert set(result.columns) >= {"id", "name", "category", "system_id"}

        # Verify data integrity
        assert result["id"].tolist() == ["1", "2", "3", "4"]
        assert result["name"].tolist() == ["Alice", "Bob", "Charlie", "Diana"]
        assert result["category"].tolist() == ["A", "B", "C", "D"]

    @pytest.mark.asyncio
    async def test_append_align_by_position_column_count_mismatch(self):
        """Test that align_by_position raises error when column counts don't match."""
        survey_df = pd.DataFrame(
            {
                "id": ["1", "2"],
                "name": ["Alice", "Bob"],
                "category": ["A", "B"],
            }
        )

        legacy_df = pd.DataFrame(
            {
                "old_id": ["3", "4"],
                "legacy_name": ["Charlie", "Diana"],
            }
        )

        cfg = {
            "entities": {
                "survey": {
                    "keys": ["id"],
                    "columns": ["id", "name", "category"],
                },
                "legacy_survey": {
                    "keys": ["old_id"],
                    "columns": ["old_id", "legacy_name"],  # Only 2 columns!
                },
                "target_entity": {
                    "keys": ["id"],
                    "columns": ["id", "name", "category"],  # 3 columns!
                    "depends_on": ["legacy_survey"],
                    "append": [
                        {
                            "source": "legacy_survey",
                            # Don't specify columns - inherit from legacy_survey (2 cols)
                            "align_by_position": True,  # Will fail: 2 != 3
                        }
                    ],
                },
            }
        }

        normalizer: ShapeShifter = ShapeShifter(
            table_store={"survey": survey_df, "legacy_survey": legacy_df},
            project=ShapeShiftProject(cfg=cfg, filename="test-config.yml"),
            default_entity="survey",
        )

        # Should raise ValueError due to column count mismatch
        with pytest.raises(ValueError, match="Column count mismatch"):
            await normalizer.normalize()
