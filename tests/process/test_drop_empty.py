import pandas as pd

from tests.process.utility import get_subset


class TestDropEmptyRows:
    """Test suite for drop_empty_rows functionality via get_subset."""

    def test_drop_empty_rows_false_keeps_all_rows(self):
        """Test that drop_empty_rows=False keeps all rows including empty ones."""
        df = pd.DataFrame({"A": [1, None, 3], "B": [None, None, 6]})
        result = get_subset(df, ["A", "B"], drop_empty_rows=False)
        assert len(result) == 3

    def test_drop_empty_rows_true_removes_all_empty(self):
        """Test that drop_empty_rows=True removes completely empty rows."""
        df = pd.DataFrame({"A": [1, None, 3, None], "B": [4, None, 6, ""]})
        result = get_subset(df, ["A", "B"], drop_empty_rows=True)
        assert len(result) == 2  # Only rows with at least one non-empty value

    def test_drop_empty_rows_with_list_checks_subset(self):
        """Test that drop_empty_rows with list only checks specified columns."""
        df = pd.DataFrame({"A": [1, 2, 3], "B": [None, None, 6], "C": [7, 8, 9]})
        result = get_subset(df, ["A", "B", "C"], drop_empty_rows=["B"])
        assert len(result) == 1  # Only row 3 has non-empty B

    def test_drop_empty_rows_dict_with_null_and_empty_string(self):
        """Test drop_empty_rows with dict specifying null and empty string as empty."""
        df = pd.DataFrame({"value": [10, None, 20, 30, 40], "status": ["active", "", "pending", None, "done"]})
        result = get_subset(df, ["value", "status"], drop_empty_rows={"status": [None, ""]})
        # Should drop rows where status is None or ""
        assert len(result) == 3
        assert result["status"].tolist() == ["active", "pending", "done"]

    def test_drop_empty_rows_dict_with_custom_empty_values(self):
        """Test drop_empty_rows with dict specifying custom empty values."""
        df = pd.DataFrame({"amount": [100, 0, 200, -1, 300], "code": ["A", "B", "C", "D", "E"]})
        result = get_subset(df, ["amount", "code"], drop_empty_rows={"amount": [None, "", 0, -1]})
        # Should drop rows where amount is None, "", 0, or -1
        assert len(result) == 3
        assert result["amount"].tolist() == [100, 200, 300]

    def test_drop_empty_rows_dict_multiple_columns(self):
        """Test drop_empty_rows with dict for multiple columns."""
        df = pd.DataFrame({"col1": ["x", None, "z", "", "w"], "col2": [1, 2, None, 4, 0], "col3": ["a", "b", "c", "d", "e"]})
        result = get_subset(df, ["col1", "col2", "col3"], drop_empty_rows={"col1": [None, ""], "col2": [None, 0]})
        # Drops rows where ALL specified columns have their empty values
        # Row 0: col1="x" (not empty), col2=1 (not empty) -> keep
        # Row 1: col1=None (empty), col2=2 (not empty) -> keep
        # Row 2: col1="z" (not empty), col2=None (empty) -> keep
        # Row 3: col1="" (empty), col2=4 (not empty) -> keep
        # Row 4: col1="w" (not empty), col2=0 (empty) -> keep
        # All rows have at least one non-empty column in the dict
        assert len(result) == 5

    def test_drop_empty_rows_dict_drops_when_all_empty(self):
        """Test drop_empty_rows dict drops row only when all specified columns are empty."""
        df = pd.DataFrame({"value1": [None, 100, None, 200], "value2": ["", 300, "", 400]})
        result = get_subset(df, ["value1", "value2"], drop_empty_rows={"value1": [None], "value2": [""]})
        # Row 0: value1=None (empty), value2="" (empty) -> drop
        # Row 1: value1=100 (not empty), value2=300 (not empty) -> keep
        # Row 2: value1=None (empty), value2="" (empty) -> drop
        # Row 3: value1=200 (not empty), value2=400 (not empty) -> keep
        assert len(result) == 2
        assert result["value1"].tolist() == [100, 200]

    def test_drop_empty_rows_dict_treats_values_as_na(self):
        """Test that dict values are treated as NA for dropna operation."""
        df = pd.DataFrame({"category": ["cat1", "unknown", "cat2", "N/A", "cat3"], "amount": [100, 200, 300, 400, 500]})
        result = get_subset(df, ["category", "amount"], drop_empty_rows={"category": [None, "", "unknown", "N/A"]})
        # Should treat "unknown" and "N/A" as empty
        assert len(result) == 3
        assert "unknown" not in result["category"].values
        assert "N/A" not in result["category"].values
