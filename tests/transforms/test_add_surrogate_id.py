"""Unit tests for add_system_id and add_surrogate_id functions."""

import pandas as pd

from src.transforms.utility import add_surrogate_id, add_system_id


class TestAddSystemId:
    """Tests for add_system_id function with preservation logic."""

    def test_creates_sequential_ids_when_column_missing(self):
        """Test that system_id is created with sequential values starting at 1."""
        df = pd.DataFrame({"name": ["A", "B", "C"]})
        result = add_system_id(df, "system_id")

        assert "system_id" in result.columns
        assert result["system_id"].tolist() == [1, 2, 3]
        assert result.columns[0] == "system_id"  # First column

    def test_preserves_existing_system_id_values(self):
        """Test that existing system_id values are preserved."""
        df = pd.DataFrame({"system_id": [5, 10, 15], "name": ["A", "B", "C"]})
        result = add_system_id(df, "system_id")

        assert result["system_id"].tolist() == [5, 10, 15]
        assert result["name"].tolist() == ["A", "B", "C"]

    def test_fills_null_system_id_with_sequential_values(self):
        """Test that null system_id values are filled with max+1."""
        df = pd.DataFrame({"system_id": [1, None, 3, None], "name": ["A", "B", "C", "D"]})
        result = add_system_id(df, "system_id")

        # Nulls should be filled with 4, 5 (max is 3)
        assert result["system_id"].tolist() == [1, 4, 3, 5]
        assert result["name"].tolist() == ["A", "B", "C", "D"]

    def test_handles_non_sequential_existing_ids(self):
        """Test with non-sequential existing IDs (e.g., 1, 5, 8)."""
        df = pd.DataFrame({"system_id": [1, 5, 8], "name": ["A", "B", "C"]})
        result = add_system_id(df, "system_id")

        assert result["system_id"].tolist() == [1, 5, 8]

    def test_fills_nulls_from_max_value(self):
        """Test that nulls are filled starting from max existing value."""
        df = pd.DataFrame({"system_id": [2, None, 5, None, None], "name": ["A", "B", "C", "D", "E"]})
        result = add_system_id(df, "system_id")

        # Max is 5, nulls should get 6, 7, 8
        assert result["system_id"].tolist() == [2, 6, 5, 7, 8]

    def test_handles_all_null_system_ids(self):
        """Test when all system_id values are null."""
        df = pd.DataFrame({"system_id": [None, None, None], "name": ["A", "B", "C"]})
        result = add_system_id(df, "system_id")

        # Should create sequential values starting at 1
        assert result["system_id"].tolist() == [1, 2, 3]

    def test_custom_id_name(self):
        """Test with custom ID column name."""
        df = pd.DataFrame({"custom_id": [1, None, 3], "name": ["A", "B", "C"]})
        result = add_system_id(df, "custom_id")

        assert result["custom_id"].tolist() == [1, 4, 3]
        assert result.columns[0] == "custom_id"

    def test_preserves_other_columns(self):
        """Test that other columns are preserved unchanged."""
        df = pd.DataFrame({"system_id": [1, None, 3], "name": ["A", "B", "C"], "value": [10, 20, 30]})
        result = add_system_id(df, "system_id")

        assert result["name"].tolist() == ["A", "B", "C"]
        assert result["value"].tolist() == [10, 20, 30]

    def test_resets_index(self):
        """Test that DataFrame index is reset."""
        df = pd.DataFrame({"system_id": [1, 2, 3], "name": ["A", "B", "C"]}, index=[5, 10, 15])
        result = add_system_id(df, "system_id")

        assert result.index.tolist() == [0, 1, 2]
        assert result["system_id"].tolist() == [1, 2, 3]

    def test_empty_dataframe(self):
        """Test with empty DataFrame."""
        df = pd.DataFrame({"name": []})
        result = add_system_id(df, "system_id")

        assert len(result) == 0
        assert "system_id" in result.columns

    def test_converts_to_integer_type(self):
        """Test that system_id column is converted to integer type."""
        df = pd.DataFrame({"system_id": ["1", "2", "3"], "name": ["A", "B", "C"]})
        result = add_system_id(df, "system_id")

        assert result["system_id"].dtype == int
        assert result["system_id"].tolist() == [1, 2, 3]

    def test_handles_mixed_types_with_nulls(self):
        """Test with mixed numeric types and nulls."""
        df = pd.DataFrame({"system_id": [1.0, None, 3.0], "name": ["A", "B", "C"]})
        result = add_system_id(df, "system_id")

        assert result["system_id"].dtype == int
        assert result["system_id"].tolist() == [1, 4, 3]

    def test_places_system_id_as_first_column(self):
        """Test that system_id is placed as first column."""
        df = pd.DataFrame({"name": ["A", "B"], "value": [10, 20], "system_id": [1, 2]})
        result = add_system_id(df, "system_id")

        assert result.columns.tolist() == ["system_id", "name", "value"]


class TestAddSurrogateId:
    """Tests for add_surrogate_id function (backward compatibility alias)."""

    def test_adds_surrogate_id_starting_at_1(self):
        """Test that surrogate ID starts at 1."""
        df = pd.DataFrame({"name": ["A", "B", "C"]})
        result = add_surrogate_id(df, "id")

        assert "id" in result.columns
        assert result["id"].tolist() == [1, 2, 3]

    def test_preserves_existing_data(self):
        """Test that existing data is preserved."""
        df = pd.DataFrame({"name": ["A", "B"], "value": [10, 20]})
        result = add_surrogate_id(df, "id")

        assert result["name"].tolist() == ["A", "B"]
        assert result["value"].tolist() == [10, 20]

    def test_resets_index(self):
        """Test that index is reset."""
        df = pd.DataFrame({"name": ["A", "B", "C"]}, index=[5, 10, 15])
        result = add_surrogate_id(df, "id")

        assert result["id"].tolist() == [1, 2, 3]
        assert result.index.tolist() == [0, 1, 2]

    def test_empty_dataframe(self):
        """Test with empty DataFrame."""
        df = pd.DataFrame({"name": []})
        result = add_surrogate_id(df, "id")

        assert len(result) == 0
        assert "id" in result.columns

    def test_alias_has_same_behavior_as_add_system_id(self):
        """Test that add_surrogate_id is functionally equivalent to add_system_id."""
        df = pd.DataFrame({"id": [1, None, 3], "name": ["A", "B", "C"]})

        result1 = add_system_id(df.copy(), "id")
        result2 = add_surrogate_id(df.copy(), "id")

        pd.testing.assert_frame_equal(result1, result2)
