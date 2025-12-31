import pandas as pd

from tests.process.utility import get_subset


class TestReplacements:
    """Test suite for replacements functionality via get_subset."""

    def test_replacements_simple_value_mapping(self):
        """Test simple value replacement in a single column."""
        df = pd.DataFrame({"code": ["A", "B", "C", "D"], "value": [1, 2, 3, 4]})
        result = get_subset(df, ["code", "value"], replacements={"code": {"A": "Alpha", "B": "Beta"}})
        assert result["code"].tolist() == ["Alpha", "Beta", "C", "D"]
        assert result["value"].tolist() == [1, 2, 3, 4]

    def test_replacements_multiple_columns(self):
        """Test replacements in multiple columns."""
        df = pd.DataFrame({"col1": ["x", "y", "z"], "col2": [1, 2, 3], "col3": ["a", "b", "c"]})
        result = get_subset(df, ["col1", "col2", "col3"], replacements={"col1": {"x": "X", "y": "Y"}, "col3": {"a": "A", "c": "C"}})
        assert result["col1"].tolist() == ["X", "Y", "z"]
        assert result["col2"].tolist() == [1, 2, 3]
        assert result["col3"].tolist() == ["A", "b", "C"]

    def test_replacements_coordinate_system_example(self):
        """Test realistic coordinate system replacement example."""
        df = pd.DataFrame(
            {"site_name": ["Site1", "Site2", "Site3"], "coordinate_system": ["DHDN Gauss-Krüger Zone 3", "RGF93 Lambert 93", "Unknown"]}
        )
        result = get_subset(
            df,
            ["site_name", "coordinate_system"],
            replacements={"coordinate_system": {"DHDN Gauss-Krüger Zone 3": "EPSG:31467", "RGF93 Lambert 93": "EPSG:2154"}},
        )
        assert result["coordinate_system"].tolist() == ["EPSG:31467", "EPSG:2154", "Unknown"]

    def test_replacements_none_values(self):
        """Test that replacements work with None/NaN values."""
        df = pd.DataFrame({"status": ["active", None, "inactive", "pending"], "code": [1, 2, 3, 4]})
        result = get_subset(df, ["status", "code"], replacements={"status": {"active": "ACTIVE", "inactive": "INACTIVE"}})
        assert result["status"].tolist()[0] == "ACTIVE"
        assert pd.isna(result["status"].tolist()[1])
        assert result["status"].tolist()[2] == "INACTIVE"
        assert result["status"].tolist()[3] == "pending"

    def test_replacements_numeric_values(self):
        """Test replacements with numeric values."""
        df = pd.DataFrame({"category": [1, 2, 3, 4, 5], "name": ["A", "B", "C", "D", "E"]})
        result = get_subset(df, ["category", "name"], replacements={"category": {1: 10, 2: 20, 3: 30}})
        assert result["category"].tolist() == [10, 20, 30, 4, 5]

    def test_replacements_empty_dict(self):
        """Test that empty replacements dict doesn't change data."""
        df = pd.DataFrame({"col1": ["a", "b", "c"], "col2": [1, 2, 3]})
        result = get_subset(df, ["col1", "col2"], replacements={})
        assert result["col1"].tolist() == ["a", "b", "c"]
        assert result["col2"].tolist() == [1, 2, 3]

    def test_replacements_none_parameter(self):
        """Test that None replacements parameter doesn't change data."""
        df = pd.DataFrame({"col1": ["a", "b", "c"], "col2": [1, 2, 3]})
        result = get_subset(df, ["col1", "col2"], replacements=None)
        assert result["col1"].tolist() == ["a", "b", "c"]
        assert result["col2"].tolist() == [1, 2, 3]

    def test_replacements_column_not_in_result(self):
        """Test that replacements for non-existent columns are safely ignored."""
        df = pd.DataFrame({"col1": ["a", "b", "c"], "col2": [1, 2, 3]})
        result = get_subset(df, ["col1"], replacements={"col2": {1: 10}})  # Only extract col1  # Try to replace col2 (not in result)
        assert "col2" not in result.columns
        assert result["col1"].tolist() == ["a", "b", "c"]

    def test_replacements_with_extra_columns(self):
        """Test replacements work together with extra_columns."""
        df = pd.DataFrame({"code": ["A", "B", "C"], "value": [1, 2, 3]})
        result = get_subset(df, ["code"], extra_columns={"renamed_value": "value"}, replacements={"code": {"A": "Alpha", "B": "Beta"}})
        assert result["code"].tolist() == ["Alpha", "Beta", "C"]
        assert result["renamed_value"].tolist() == [1, 2, 3]

    def test_replacements_preserves_data_types(self):
        """Test that replacements preserve data types appropriately."""
        df = pd.DataFrame({"str_col": ["a", "b", "c"], "int_col": [1, 2, 3], "float_col": [1.1, 2.2, 3.3]})
        result = get_subset(
            df, ["str_col", "int_col", "float_col"], replacements={"str_col": {"a": "A"}, "int_col": {1: 10}, "float_col": {1.1: 11.1}}
        )
        assert result["str_col"].tolist() == ["A", "b", "c"]
        assert result["int_col"].tolist() == [10, 2, 3]
        assert result["float_col"].tolist() == [11.1, 2.2, 3.3]
