"""Unit tests for fixed module."""

import pandas as pd
import pytest

from src.arbodat.config_model import TableConfig
from src.arbodat.loaders.fixed_loader import FixedLoader


class TestCreateFixedTable:
    """Tests for await FixedLoader().load function."""

    @pytest.mark.asyncio
    async def test_raises_when_not_fixed_data(self):
        """Test that await FixedLoader().load raises ValueError when entity is not fixed data."""
        entity = "test_entity"
        config = {"test_entity": {"type": "data", "columns": ["col1"]}}  # Not fixed
        table_cfg = TableConfig(cfg=config, entity_name=entity)

        with pytest.raises(ValueError, match="is not configured as fixed data"):
            await FixedLoader().load(entity, table_cfg)

    @pytest.mark.asyncio
    async def test_raises_when_no_values(self):
        """Test that await FixedLoader().load raises ValueError when no values defined."""
        entity = "test_entity"
        config = {"test_entity": {"type": "fixed", "columns": ["col1"], "values": []}}
        table_cfg = TableConfig(cfg=config, entity_name=entity)

        with pytest.raises(ValueError, match="has no values defined"):
            await FixedLoader().load(entity, table_cfg)

    @pytest.mark.asyncio
    async def test_raises_when_no_surrogate_name_and_no_columns(self):
        """Test raises ValueError when single column config has no surrogate_name and no columns."""
        entity = "test_entity"
        config = {"test_entity": {"type": "fixed", "values": ["val1", "val2"]}}
        table_cfg = TableConfig(cfg=config, entity_name=entity)

        with pytest.raises(ValueError, match="must have a surrogate_name or one column defined"):
            await FixedLoader().load(entity, table_cfg)

    @pytest.mark.asyncio
    async def test_single_column_with_surrogate_name(self):
        """Test create fixed table with single column using surrogate_name."""
        entity = "location_type"
        config = {"location_type": {"type": "fixed", "surrogate_name": "location_type", "values": ["Ort", "Kreis", "Land", "Staat"]}}
        table_cfg = TableConfig(cfg=config, entity_name=entity)

        result: pd.DataFrame = await FixedLoader().load(entity, table_cfg)

        assert len(result) == 4
        assert "location_type" in result.columns
        assert result["location_type"].tolist() == ["Ort", "Kreis", "Land", "Staat"]

    @pytest.mark.asyncio
    async def test_single_column_with_surrogate_name_and_surrogate_id(self):
        """Test creates fixed table with surrogate_id added."""
        entity = "location_type"
        config = {
            "location_type": {
                "type": "fixed",
                "surrogate_id": "location_type_id",
                "surrogate_name": "location_type",
                "values": ["Ort", "Kreis", "Land"],
            }
        }
        table_cfg = TableConfig(cfg=config, entity_name=entity)

        result: pd.DataFrame = await FixedLoader().load(entity, table_cfg)

        assert len(result) == 3
        assert "location_type" in result.columns
        assert "location_type_id" in result.columns
        assert result["location_type_id"].tolist() == [1, 2, 3]
        assert result["location_type"].tolist() == ["Ort", "Kreis", "Land"]

    @pytest.mark.asyncio
    async def test_single_column_from_columns_list(self):
        """Test create fixed table using single column from columns list."""
        entity = "test_entity"
        config = {"test_entity": {"type": "fixed", "columns": ["type_name"], "values": ["Type1", "Type2", "Type3"]}}
        table_cfg = TableConfig(cfg=config, entity_name=entity)

        result: pd.DataFrame = await FixedLoader().load(entity, table_cfg)

        assert len(result) == 3
        assert "type_name" in result.columns
        assert result["type_name"].tolist() == ["Type1", "Type2", "Type3"]

    @pytest.mark.asyncio
    async def test_single_column_with_surrogate_id_no_surrogate_name(self):
        """Test single column with surrogate_id but no surrogate_name uses column name."""
        entity = "test_entity"
        config = {"test_entity": {"type": "fixed", "surrogate_id": "type_id", "columns": ["type_name"], "values": ["Type1", "Type2"]}}
        table_cfg = TableConfig(cfg=config, entity_name=entity)

        result: pd.DataFrame = await FixedLoader().load(entity, table_cfg)

        assert len(result) == 2
        assert "type_name" in result.columns
        assert "type_id" in result.columns
        assert result["type_id"].tolist() == [1, 2]

    @pytest.mark.asyncio
    async def test_multiple_columns_with_list_of_lists(self):
        """Test create fixed table with multiple columns from list of lists."""
        entity = "coordinate_method_dimensions"
        config = {
            "coordinate_method_dimensions": {
                "type": "fixed",
                "columns": ["coordinate_type", "limit_lower", "limit_upper"],
                "values": [["KoordX", None, None], ["KoordY", None, None], ["KoordZ", 0.0, 100.0]],
            }
        }
        table_cfg = TableConfig(cfg=config, entity_name=entity)

        result: pd.DataFrame = await FixedLoader().load(entity, table_cfg)

        assert len(result) == 3
        assert list(result.columns) == ["coordinate_type", "limit_lower", "limit_upper"]
        assert result["coordinate_type"].tolist() == ["KoordX", "KoordY", "KoordZ"]
        assert pd.isna(result.iloc[0]["limit_lower"])
        assert result.iloc[2]["limit_lower"] == 0.0

    @pytest.mark.asyncio
    async def test_multiple_columns_with_surrogate_id(self):
        """Test multiple columns with surrogate_id added."""
        entity = "test_entity"
        config = {
            "test_entity": {
                "type": "fixed",
                "surrogate_id": "id",
                "columns": ["name", "code"],
                "values": [["First", "A"], ["Second", "B"], ["Third", "C"]],
            }
        }
        table_cfg = TableConfig(cfg=config, entity_name=entity)

        result: pd.DataFrame = await FixedLoader().load(entity, table_cfg)

        assert len(result) == 3
        assert "id" in result.columns
        assert "name" in result.columns
        assert "code" in result.columns
        assert result["id"].tolist() == [1, 2, 3]
        assert result["name"].tolist() == ["First", "Second", "Third"]
        assert result["code"].tolist() == ["A", "B", "C"]

    @pytest.mark.asyncio
    async def test_raises_when_values_not_list_of_lists_for_multiple_columns(self):
        """Test raises ValueError when values is not list of lists for multiple columns."""
        entity = "test_entity"
        config = {"test_entity": {"type": "fixed", "columns": ["col1", "col2"], "values": ["val1", "val2"]}}  # Should be list of lists
        table_cfg = TableConfig(cfg=config, entity_name=entity)

        with pytest.raises(ValueError, match="must have values as a list of lists"):
            await FixedLoader().load(entity, table_cfg)

    @pytest.mark.asyncio
    async def test_raises_when_row_length_mismatch(self):
        """Test raises ValueError when row length doesn't match columns length."""
        entity = "test_entity"
        config = {
            "test_entity": {"type": "fixed", "columns": ["col1", "col2", "col3"], "values": [["a", "b", "c"], ["d", "e"]]}
        }  # Missing one value
        table_cfg = TableConfig(cfg=config, entity_name=entity)

        with pytest.raises(ValueError, match="has mismatched number of columns and values"):
            await FixedLoader().load(entity, table_cfg)

    @pytest.mark.asyncio
    async def test_site_property_type_example_from_yaml(self):
        """Test site_property_type example from arbodat.yml."""
        entity = "site_property_type"
        config = {
            "site_property_type": {
                "type": "fixed",
                "surrogate_id": "site_property_type_id",
                "surrogate_name": "site_property_type",
                "values": ["Limes", "FustelTyp?", "okFustel", "TK", "EVNr"],
            }
        }
        table_cfg = TableConfig(cfg=config, entity_name=entity)

        result: pd.DataFrame = await FixedLoader().load(entity, table_cfg)

        assert len(result) == 5
        assert "site_property_type" in result.columns
        assert "site_property_type_id" in result.columns
        assert result["site_property_type_id"].tolist() == [1, 2, 3, 4, 5]
        assert result["site_property_type"].tolist() == ["Limes", "FustelTyp?", "okFustel", "TK", "EVNr"]

    @pytest.mark.asyncio
    async def test_location_type_example_from_yaml(self):
        """Test location_type example from arbodat.yml."""
        entity = "location_type"
        config = {
            "location_type": {
                "type": "fixed",
                "surrogate_id": "location_type_id",
                "surrogate_name": "location_type",
                "columns": ["location_type"],
                "values": ["Ort", "Kreis", "Land", "Staat", "FlurStr"],
            }
        }
        table_cfg = TableConfig(cfg=config, entity_name=entity)

        result: pd.DataFrame = await FixedLoader().load(entity, table_cfg)

        assert len(result) == 5
        assert "location_type_id" in result.columns
        assert "location_type" in result.columns
        assert result["location_type_id"].tolist() == [1, 2, 3, 4, 5]

    @pytest.mark.asyncio
    async def test_empty_columns_list_uses_surrogate_name(self):
        """Test that empty columns list falls back to using surrogate_name."""
        entity = "test_entity"
        config = {"test_entity": {"type": "fixed", "surrogate_name": "name", "columns": [], "values": ["A", "B", "C"]}}
        table_cfg = TableConfig(cfg=config, entity_name=entity)

        result: pd.DataFrame = await FixedLoader().load(entity, table_cfg)

        assert len(result) == 3
        assert "name" in result.columns
        assert result["name"].tolist() == ["A", "B", "C"]

    @pytest.mark.asyncio
    async def test_single_value(self):
        """Test create fixed table with single value."""
        entity = "test_entity"
        config = {"test_entity": {"type": "fixed", "surrogate_name": "value", "values": ["OnlyOne"]}}
        table_cfg = TableConfig(cfg=config, entity_name=entity)

        result: pd.DataFrame = await FixedLoader().load(entity, table_cfg)

        assert len(result) == 1
        assert result["value"].tolist() == ["OnlyOne"]

    @pytest.mark.asyncio
    async def test_numeric_values(self):
        """Test create fixed table with numeric values."""
        entity = "test_entity"
        config = {"test_entity": {"type": "fixed", "surrogate_id": "id", "surrogate_name": "level", "values": [1, 2, 3, 5, 10]}}
        table_cfg = TableConfig(cfg=config, entity_name=entity)

        result: pd.DataFrame = await FixedLoader().load(entity, table_cfg)

        assert len(result) == 5
        assert result["level"].tolist() == [1, 2, 3, 5, 10]
        assert result["id"].tolist() == [1, 2, 3, 4, 5]

    @pytest.mark.asyncio
    async def test_mixed_type_values(self):
        """Test create fixed table with mixed type values."""
        entity = "test_entity"
        config = {"test_entity": {"type": "fixed", "columns": ["value"], "values": [1, "two", 3.0, None]}}
        table_cfg = TableConfig(cfg=config, entity_name=entity)

        result: pd.DataFrame = await FixedLoader().load(entity, table_cfg)

        assert len(result) == 4
        assert result["value"].tolist()[0] == 1
        assert result["value"].tolist()[1] == "two"
        assert result["value"].tolist()[2] == 3.0
        assert pd.isna(result["value"].tolist()[3])

    @pytest.mark.asyncio
    async def test_multiple_columns_with_none_values(self):
        """Test multiple columns with None values."""
        entity = "test_entity"
        config = {
            "test_entity": {
                "type": "fixed",
                "columns": ["col1", "col2", "col3"],
                "values": [["A", None, 1], [None, "B", None], ["C", "D", 3]],
            }
        }
        table_cfg = TableConfig(cfg=config, entity_name=entity)

        result: pd.DataFrame = await FixedLoader().load(entity, table_cfg)

        assert len(result) == 3
        assert pd.isna(result.iloc[0]["col2"])
        assert pd.isna(result.iloc[1]["col1"])
        assert pd.isna(result.iloc[1]["col3"])

    @pytest.mark.asyncio
    async def test_surrogate_id_column_order(self):
        """Test that surrogate_id is added as a new column."""
        entity = "test_entity"
        config = {"test_entity": {"type": "fixed", "surrogate_id": "id", "columns": ["name", "value"], "values": [["A", 1], ["B", 2]]}}
        table_cfg = TableConfig(cfg=config, entity_name=entity)

        result: pd.DataFrame = await FixedLoader().load(entity, table_cfg)

        # Surrogate ID is added by add_surrogate_id which appends it
        assert "id" in result.columns
        assert "name" in result.columns
        assert "value" in result.columns

    @pytest.mark.asyncio
    async def test_large_value_list(self):
        """Test create fixed table with large number of values."""
        entity = "test_entity"
        config = {"test_entity": {"type": "fixed", "surrogate_id": "id", "surrogate_name": "number", "values": list(range(1, 101))}}
        table_cfg = TableConfig(cfg=config, entity_name=entity)

        result: pd.DataFrame = await FixedLoader().load(entity, table_cfg)

        assert len(result) == 100
        assert result["id"].tolist() == list(range(1, 101))
        assert result["number"].tolist() == list(range(1, 101))

    @pytest.mark.asyncio
    async def test_special_characters_in_values(self):
        """Test values with special characters."""
        entity = "test_entity"
        config = {
            "test_entity": {
                "type": "fixed",
                "surrogate_name": "text",
                "values": ["Normal", "With spaces", "With-dash", "With_underscore", "With.dot"],
            }
        }
        table_cfg = TableConfig(cfg=config, entity_name=entity)

        result: pd.DataFrame = await FixedLoader().load(entity, table_cfg)

        assert len(result) == 5
        assert "With spaces" in result["text"].values
        assert "With-dash" in result["text"].values

    @pytest.mark.asyncio
    async def test_unicode_values(self):
        """Test values with unicode characters."""
        entity = "test_entity"
        config = {"test_entity": {"type": "fixed", "surrogate_name": "text", "values": ["Ö", "ä", "ü", "ß", "é"]}}
        table_cfg = TableConfig(cfg=config, entity_name=entity)

        result: pd.DataFrame = await FixedLoader().load(entity, table_cfg)

        assert len(result) == 5
        assert result["text"].tolist() == ["Ö", "ä", "ü", "ß", "é"]

    @pytest.mark.asyncio
    async def test_boolean_values(self):
        """Test create fixed table with boolean values."""
        entity = "test_entity"
        config = {"test_entity": {"type": "fixed", "columns": ["flag", "name"], "values": [[True, "Yes"], [False, "No"], [True, "Maybe"]]}}
        table_cfg = TableConfig(cfg=config, entity_name=entity)

        result: pd.DataFrame = await FixedLoader().load(entity, table_cfg)

        assert len(result) == 3
        assert result["flag"].tolist() == [True, False, True]
        assert result["name"].tolist() == ["Yes", "No", "Maybe"]

    @pytest.mark.asyncio
    async def test_coordinate_method_dimensions_example_from_yaml(self):
        """Test coordinate_method_dimensions example with multiple columns and nulls."""
        entity = "coordinate_method_dimensions"
        config = {
            "coordinate_method_dimensions": {
                "type": "fixed",
                "surrogate_id": "coordinate_method_dimension_id",
                "columns": ["coordinate_type", "limit_lower", "limit_upper", "dimension_id", "method_id"],
                "values": [["KoordX", None, None, None, None], ["KoordY", None, None, None, None], ["KoordZ", None, None, None, None]],
            }
        }
        table_cfg = TableConfig(cfg=config, entity_name=entity)

        result: pd.DataFrame = await FixedLoader().load(entity, table_cfg)

        assert len(result) == 3
        assert "coordinate_method_dimension_id" in result.columns
        assert result["coordinate_method_dimension_id"].tolist() == [1, 2, 3]
        assert result["coordinate_type"].tolist() == ["KoordX", "KoordY", "KoordZ"]
        assert all(pd.isna(result["limit_lower"]))
        assert all(pd.isna(result["dimension_id"]))

    @pytest.mark.asyncio
    async def test_two_column_table(self):
        """Test create fixed table with exactly two columns."""
        entity = "test_entity"
        config = {
            "test_entity": {
                "type": "fixed",
                "columns": ["dimension_id", "dimension_name"],
                "values": [[1, "Width"], [2, "Height"], [3, "Depth"]],
            }
        }
        table_cfg = TableConfig(cfg=config, entity_name=entity)

        result: pd.DataFrame = await FixedLoader().load(entity, table_cfg)

        assert len(result) == 3
        assert list(result.columns) == ["dimension_id", "dimension_name"]
        assert result["dimension_id"].tolist() == [1, 2, 3]
        assert result["dimension_name"].tolist() == ["Width", "Height", "Depth"]
