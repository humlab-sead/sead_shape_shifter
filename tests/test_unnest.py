"""Unit tests for unnest module."""

import pandas as pd
import pytest

from src.arbodat.config_model import TableConfig
from src.arbodat.unnest import unnest


class TestUnnest:
    """Tests for unnest function."""

    def test_unnest_returns_table_when_no_config(self):
        """Test that unnest returns original table when no unnest config."""
        entity = "test_entity"
        table = pd.DataFrame({"col1": [1, 2], "col2": [3, 4]})
        config = {"test_entity": {"columns": ["col1", "col2"]}}
        table_cfg = TableConfig(cfg=config, entity_name=entity)

        result = unnest(entity, table, table_cfg)

        pd.testing.assert_frame_equal(result, table)

    def test_unnest_returns_table_when_already_melted(self):
        """Test that unnest returns table if value_name column already exists."""
        entity = "test_entity"
        table = pd.DataFrame({"id": [1, 2], "value": [3, 4]})
        config = {"test_entity": {"columns": ["id", "value"], "unnest": {"id_vars": ["id"], "var_name": "variable", "value_name": "value"}}}
        table_cfg = TableConfig(cfg=config, entity_name=entity)

        result = unnest(entity, table, table_cfg)

        pd.testing.assert_frame_equal(result, table)

    def test_unnest_raises_when_var_name_missing(self):
        """Test that unnest raises ValueError when var_name is None or empty."""
        entity = "test_entity"
        table = pd.DataFrame({"col1": [1, 2], "col2": [3, 4]})
        config = {"test_entity": {"columns": ["col1", "col2"], "unnest": {"var_name": "", "value_name": "value"}}}

        with pytest.raises(ValueError, match="Invalid unnest configuration"):
            table_cfg = TableConfig(cfg=config, entity_name=entity)
            unnest(entity, table, table_cfg)

    def test_unnest_raises_when_value_name_missing(self):
        """Test that unnest raises ValueError when value_name is None or empty."""
        entity = "test_entity"
        table = pd.DataFrame({"col1": [1, 2], "col2": [3, 4]})
        config = {"test_entity": {"columns": ["col1", "col2"], "unnest": {"var_name": "variable", "value_name": ""}}}

        with pytest.raises(ValueError, match="Invalid unnest configuration"):
            table_cfg = TableConfig(cfg=config, entity_name=entity)
            unnest(entity, table, table_cfg)

    def test_unnest_raises_when_id_vars_missing_from_table(self):
        """Test that unnest raises ValueError when id_vars columns missing."""
        entity = "test_entity"
        table = pd.DataFrame({"col1": [1, 2], "col2": [3, 4]})
        config = {
            "test_entity": {
                "columns": ["col1", "col2"],
                "unnest": {"id_vars": ["missing_col"], "var_name": "variable", "value_name": "value"},
            }
        }
        table_cfg = TableConfig(cfg=config, entity_name=entity)

        with pytest.raises(ValueError, match="missing `id_vars` columns"):
            unnest(entity, table, table_cfg)

    def test_unnest_defers_when_value_vars_missing(self):
        """Test that unnest returns original table when value_vars columns missing."""
        entity = "test_entity"
        table = pd.DataFrame({"id": [1, 2], "col1": [3, 4]})
        config = {
            "test_entity": {
                "columns": ["id", "col1"],
                "unnest": {"id_vars": ["id"], "value_vars": ["col1", "missing_col"], "var_name": "variable", "value_name": "value"},
            }
        }
        table_cfg = TableConfig(cfg=config, entity_name=entity)

        result = unnest(entity, table, table_cfg)

        # Returns original table because missing_col is not in DataFrame
        pd.testing.assert_frame_equal(result, table)

    def test_unnest_basic_melt_no_id_vars(self):
        """Test basic unnest without id_vars."""
        entity = "test_entity"
        table = pd.DataFrame({"col1": [1, 2], "col2": [3, 4]})
        config = {"test_entity": {"columns": ["col1", "col2"], "unnest": {"var_name": "variable", "value_name": "value"}}}
        table_cfg = TableConfig(cfg=config, entity_name=entity)

        result = unnest(entity, table, table_cfg)

        expected = pd.DataFrame({"variable": ["col1", "col1", "col2", "col2"], "value": [1, 2, 3, 4]})
        pd.testing.assert_frame_equal(result, expected)

    def test_unnest_with_id_vars(self):
        """Test unnest with id_vars specified.

        When value_vars is empty, pd.melt() with only id_vars melts all
        non-id columns. However, the current behavior returns empty result.
        """
        entity = "test_entity"
        table = pd.DataFrame({"id": [1, 2], "col1": [10, 20], "col2": [30, 40]})
        config = {
            "test_entity": {"columns": ["id", "col1", "col2"], "unnest": {"id_vars": ["id"], "var_name": "variable", "value_name": "value"}}
        }
        table_cfg = TableConfig(cfg=config, entity_name=entity)

        result = unnest(entity, table, table_cfg)

        # Should melt col1 and col2, keeping id
        expected = pd.DataFrame({"id": [1, 2, 1, 2], "variable": ["col1", "col1", "col2", "col2"], "value": [10, 20, 30, 40]})
        pd.testing.assert_frame_equal(result, expected)

    def test_unnest_with_value_vars(self):
        """Test unnest with value_vars specified."""
        entity = "test_entity"
        table = pd.DataFrame({"id": [1, 2], "col1": [10, 20], "col2": [30, 40], "col3": [50, 60]})
        config = {
            "test_entity": {
                "columns": ["id", "col1", "col2", "col3"],
                "unnest": {"id_vars": ["id"], "value_vars": ["col1", "col2"], "var_name": "variable", "value_name": "value"},
            }
        }
        table_cfg = TableConfig(cfg=config, entity_name=entity)

        result = unnest(entity, table, table_cfg)

        # Melts only col1 and col2 as specified in value_vars
        expected = pd.DataFrame({"id": [1, 2, 1, 2], "variable": ["col1", "col1", "col2", "col2"], "value": [10, 20, 30, 40]})
        pd.testing.assert_frame_equal(result, expected)

    def test_unnest_with_multiple_id_vars(self):
        """Test unnest with multiple id_vars."""
        entity = "test_entity"
        table = pd.DataFrame({"id1": [1, 2], "id2": ["a", "b"], "col1": [10, 20], "col2": [30, 40]})
        config = {
            "test_entity": {
                "columns": ["id1", "id2", "col1", "col2"],
                "unnest": {"id_vars": ["id1", "id2"], "var_name": "variable", "value_name": "value"},
            }
        }
        table_cfg = TableConfig(cfg=config, entity_name=entity)

        result = unnest(entity, table, table_cfg)

        expected = pd.DataFrame(
            {"id1": [1, 2, 1, 2], "id2": ["a", "b", "a", "b"], "variable": ["col1", "col1", "col2", "col2"], "value": [10, 20, 30, 40]}
        )
        pd.testing.assert_frame_equal(result, expected)

    def test_unnest_custom_var_and_value_names(self):
        """Test unnest with custom var_name and value_name."""
        entity = "test_entity"
        table = pd.DataFrame({"col1": [1, 2], "col2": [3, 4]})
        config = {"test_entity": {"columns": ["col1", "col2"], "unnest": {"var_name": "attribute", "value_name": "measurement"}}}
        table_cfg = TableConfig(cfg=config, entity_name=entity)

        result = unnest(entity, table, table_cfg)

        assert "attribute" in result.columns
        assert "measurement" in result.columns
        assert result["attribute"].tolist() == ["col1", "col1", "col2", "col2"]

    def test_unnest_preserves_data_types(self):
        """Test that unnest preserves data types where possible."""
        entity = "test_entity"
        table = pd.DataFrame({"id": [1, 2], "col1": [10, 20], "col2": [30, 40]})
        config = {
            "test_entity": {"columns": ["id", "col1", "col2"], "unnest": {"id_vars": ["id"], "var_name": "variable", "value_name": "value"}}
        }
        table_cfg = TableConfig(cfg=config, entity_name=entity)

        result = unnest(entity, table, table_cfg)

        assert result["id"].dtype == table["id"].dtype

    def test_unnest_empty_table(self):
        """Test unnest with empty DataFrame."""
        entity = "test_entity"
        table = pd.DataFrame({"col1": [], "col2": []})
        config = {"test_entity": {"columns": ["col1", "col2"], "unnest": {"var_name": "variable", "value_name": "value"}}}
        table_cfg = TableConfig(cfg=config, entity_name=entity)

        result = unnest(entity, table, table_cfg)

        assert len(result) == 0
        assert "variable" in result.columns
        assert "value" in result.columns

    def test_unnest_single_column(self):
        """Test unnest with single column."""
        entity = "test_entity"
        table = pd.DataFrame({"col1": [1, 2, 3]})
        config = {"test_entity": {"columns": ["col1"], "unnest": {"var_name": "variable", "value_name": "value"}}}
        table_cfg = TableConfig(cfg=config, entity_name=entity)

        result = unnest(entity, table, table_cfg)

        assert len(result) == 3
        assert result["variable"].unique().tolist() == ["col1"]

    def test_unnest_location_type_example_from_yaml(self):
        """Test unnest with location_type example from arbodat.yml."""
        entity = "location"
        table = pd.DataFrame(
            {
                "Ort": ["Berlin", "Munich"],
                "Kreis": ["Berlin", "Munich"],
                "Land": ["Berlin", "Bavaria"],
                "Staat": ["Germany", "Germany"],
                "FlurStr": ["Main St", "Church St"],
            }
        )
        config = {
            "location_type": {"surrogate_id": "location_type_id", "values": ["Ort", "Kreis", "Land", "Staat", "FlurStr"]},
            "location": {
                "surrogate_id": "location_id",
                "columns": ["Ort", "Kreis", "Land", "Staat", "FlurStr"],
                "unnest": {
                    "value_vars": ["Ort", "Kreis", "Land", "Staat", "FlurStr"],
                    "var_name": "location_type",
                    "value_name": "location_name",
                },
            },
        }
        table_cfg = TableConfig(cfg=config, entity_name=entity)

        result = unnest(entity, table, table_cfg)

        assert "location_type" in result.columns
        assert "location_name" in result.columns
        assert len(result) == 10  # 2 rows * 5 columns
        assert set(result["location_type"].unique()) == {"Ort", "Kreis", "Land", "Staat", "FlurStr"}

    def test_unnest_site_property_example_from_yaml(self):
        """Test unnest with site_property example from arbodat.yml."""
        entity = "site_property"
        table = pd.DataFrame(
            {
                "ProjektNr": [1, 2],
                "Fustel": ["A", "B"],
                "EVNr": [100, 200],
                "FustelTyp?": [True, False],
                "okFustel": [True, True],
                "Limes": ["Yes", "No"],
                "TK": ["5000", "6000"],
            }
        )
        config = {
            "site": {"surrogate_id": "site_id", "keys": ["ProjektNr", "Fustel", "EVNr"]},
            "site_property_type": {"surrogate_id": "site_property_type_id", "values": ["FustelTyp?", "okFustel", "Limes", "TK"]},
            "site_property": {
                "surrogate_id": "site_property_id",
                "columns": ["ProjektNr", "Fustel", "EVNr", "FustelTyp?", "okFustel", "Limes", "TK"],
                "unnest": {
                    "id_vars": ["ProjektNr", "Fustel", "EVNr"],
                    "value_vars": ["FustelTyp?", "okFustel", "Limes", "TK"],
                    "var_name": "site_property_type",
                    "value_name": "site_property_value",
                },
            },
        }
        table_cfg = TableConfig(cfg=config, entity_name=entity)

        result = unnest(entity, table, table_cfg)

        assert "site_property_type" in result.columns
        assert "site_property_value" in result.columns
        assert len(result) == 8  # 2 rows * 4 value_vars
        assert "ProjektNr" in result.columns
        assert "Fustel" in result.columns
        assert "EVNr" in result.columns

    def test_unnest_with_empty_value_vars_list(self):
        """Test with empty value_vars list.

        When value_vars is empty, pd.melt uses all columns except id_vars.
        """
        entity = "test_entity"
        table = pd.DataFrame({"id": [1, 2], "col1": [10, 20], "col2": [30, 40]})
        config = {
            "test_entity": {
                "columns": ["id", "col1", "col2"],
                "unnest": {"id_vars": ["id"], "value_vars": [], "var_name": "variable", "value_name": "value"},
            }
        }
        table_cfg = TableConfig(cfg=config, entity_name=entity)

        result = unnest(entity, table, table_cfg)

        # With empty value_vars, pandas.melt uses all columns except id_vars
        expected = pd.DataFrame({"id": [1, 2, 1, 2], "variable": ["col1", "col1", "col2", "col2"], "value": [10, 20, 30, 40]})
        pd.testing.assert_frame_equal(result, expected)

    def test_unnest_mixed_data_types(self):
        """Test unnest with mixed data types in value columns."""
        entity = "test_entity"
        table = pd.DataFrame({"id": [1, 2], "num_col": [10, 20], "str_col": ["a", "b"]})
        config = {
            "test_entity": {
                "columns": ["id", "num_col", "str_col"],
                "unnest": {"id_vars": ["id"], "value_vars": ["num_col", "str_col"], "var_name": "variable", "value_name": "value"},
            }
        }
        table_cfg = TableConfig(cfg=config, entity_name=entity)

        result = unnest(entity, table, table_cfg)

        # Result should have mixed types in the value column
        assert len(result) == 4
        assert result["value"].dtype == object  # Mixed types become object dtype

    def test_unnest_with_null_values(self):
        """Test unnest handles null values correctly."""
        entity = "test_entity"
        table = pd.DataFrame({"id": [1, 2], "col1": [10, None], "col2": [None, 40]})
        config = {
            "test_entity": {"columns": ["id", "col1", "col2"], "unnest": {"id_vars": ["id"], "var_name": "variable", "value_name": "value"}}
        }
        table_cfg = TableConfig(cfg=config, entity_name=entity)

        result = unnest(entity, table, table_cfg)

        assert len(result) == 4
        # Check that nulls are preserved in the melted data
        assert result["value"].isna().sum() == 2  # Two null values total

    def test_unnest_sample_coordinates_example_from_yaml(self):
        """Test unnest with sample_coordinates example from arbodat.yml."""
        entity = "sample_coordinates"
        table = pd.DataFrame(
            {
                "sample_id": [1, 2],
                "KoordX": [100.5, 200.5],
                "KoordY": [300.5, 400.5],
                "KoordZ": [10.0, 20.0],
                "TiefeBis": [50.0, 60.0],
                "TiefeVon": [0.0, 0.0],
            }
        )
        config = {
            "sample": {"surrogate_id": "sample_id", "keys": ["ProjektNr", "Befu", "ProbNr"]},
            "sample_coordinates": {
                "surrogate_id": "sample_coordinate_id",
                "columns": ["KoordX", "KoordY", "KoordZ", "TiefeBis", "TiefeVon"],
                "unnest": {
                    "id_vars": ["sample_id"],
                    "value_vars": ["KoordX", "KoordY", "KoordZ", "TiefeBis", "TiefeVon"],
                    "var_name": "coordinate_type",
                    "value_name": "coordinate_value",
                },
            },
        }
        table_cfg = TableConfig(cfg=config, entity_name=entity)

        result = unnest(entity, table, table_cfg)

        assert "coordinate_type" in result.columns
        assert "coordinate_value" in result.columns
        assert len(result) == 10  # 2 rows * 5 coordinates
        assert set(result["coordinate_type"].unique()) == {"KoordX", "KoordY", "KoordZ", "TiefeBis", "TiefeVon"}
