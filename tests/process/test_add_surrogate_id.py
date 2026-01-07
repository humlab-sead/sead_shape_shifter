"""Unit tests for arbodat utility functions."""

import pandas as pd

from src.extract import add_surrogate_id


class TestAddSurrogateId:
    """Tests for add_surrogate_id function."""

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
