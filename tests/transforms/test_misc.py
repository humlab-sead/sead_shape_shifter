"""Unit tests for arbodat utility functions."""

import pandas as pd

from src.utility import (
    rename_last_occurence,
)


class TestRenameLastOccurrence:
    """Test suite for rename_last_occurence helper function."""

    def test_basic_rename_single_occurrence(self):
        """Test renaming a column that appears once."""
        data = pd.DataFrame({"A": [1, 2], "B": [3, 4], "C": [5, 6]})
        result = rename_last_occurence(data, {"B": "B_renamed"})
        expected = ["A", "B_renamed", "C"]
        assert result == expected

    def test_rename_last_when_multiple_occurrences(self):
        """Test that only the LAST occurrence is renamed when column appears multiple times."""
        # Create DataFrame with duplicate column names
        data = pd.DataFrame([[1, 2, 3, 4]], columns=["A", "B", "A", "C"])
        result = rename_last_occurence(data, {"A": "A_last"})
        expected = ["A", "B", "A_last", "C"]
        assert result == expected

    def test_skip_when_source_not_in_columns(self):
        """Test that rename is skipped when source column doesn't exist."""
        data = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
        result = rename_last_occurence(data, {"C": "C_renamed"})
        expected = ["A", "B"]
        assert result == expected

    def test_skip_when_target_already_exists(self):
        """Test that rename is skipped when target name already exists in columns."""
        data = pd.DataFrame({"A": [1, 2], "B": [3, 4], "C": [5, 6]})
        result = rename_last_occurence(data, {"A": "C"})
        expected = ["A", "B", "C"]
        assert result == expected

    def test_multiple_renames_in_single_call(self):
        """Test renaming multiple columns in a single call."""
        data = pd.DataFrame({"A": [1, 2], "B": [3, 4], "C": [5, 6], "D": [7, 8]})
        result = rename_last_occurence(data, {"A": "A_new", "C": "C_new"})
        expected = ["A_new", "B", "C_new", "D"]
        assert result == expected

    def test_empty_dataframe(self):
        """Test with empty DataFrame."""
        data = pd.DataFrame()
        result = rename_last_occurence(data, {"A": "A_renamed"})
        expected = []
        assert result == expected

    def test_empty_rename_map(self):
        """Test with empty rename map."""
        data = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
        result = rename_last_occurence(data, {})
        expected = ["A", "B"]
        assert result == expected

    def test_rename_with_duplicate_occurrences_multiple_sources(self):
        """Test renaming when multiple columns have duplicates."""
        # DataFrame with multiple duplicate columns
        data = pd.DataFrame([[1, 2, 3, 4, 5, 6]], columns=["A", "B", "A", "C", "B", "D"])
        result = rename_last_occurence(data, {"A": "A_last", "B": "B_last"})
        expected = ["A", "B", "A_last", "C", "B_last", "D"]
        assert result == expected

    def test_rename_does_not_modify_dataframe(self):
        """Test that the original DataFrame columns are not modified."""
        data = pd.DataFrame({"A": [1, 2], "B": [3, 4], "C": [5, 6]})
        original_columns = data.columns.tolist()
        rename_last_occurence(data, {"B": "B_renamed"})
        assert data.columns.tolist() == original_columns

    def test_rename_first_occurrence_not_affected(self):
        """Test that earlier occurrences of duplicate columns remain unchanged."""
        data = pd.DataFrame([[1, 2, 3, 4, 5]], columns=["A", "B", "A", "A", "C"])
        result = rename_last_occurence(data, {"A": "A_final"})
        expected = ["A", "B", "A", "A_final", "C"]
        assert result == expected

    def test_rename_with_special_characters_in_names(self):
        """Test renaming columns with special characters."""
        data = pd.DataFrame({"col.1": [1, 2], "col-2": [3, 4], "col_3": [5, 6]})
        result = rename_last_occurence(data, {"col.1": "column_1", "col-2": "column-2"})
        expected = ["column_1", "column-2", "col_3"]
        assert result == expected
