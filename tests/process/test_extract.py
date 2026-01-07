"""Tests for src.extract helper functions."""

import pandas as pd
import pytest

from src.extract import SubsetService, add_surrogate_id
from tests.process.utility import get_subset


class TestGetSubset:
    """Tests for get_subset function."""

    def test_basic_column_extraction(self):
        """Test extracting basic columns."""
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4], "C": [5, 6]})
        result = get_subset(df, ["A", "B"])

        assert list(result.columns) == ["A", "B"]
        assert len(result) == 2

    def test_raises_on_none_source(self):
        """Test that None source raises ValueError."""
        with pytest.raises(ValueError, match="Source DataFrame must be provided"):
            get_subset(None, ["A"])  # type: ignore

    def test_missing_columns_raises_error(self):
        """Test that missing columns raise error by default."""
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})

        with pytest.raises(ValueError, match="Columns not found"):
            get_subset(df, ["A", "C"])

    def test_missing_columns_warns_when_not_raising(self):
        """Test that missing columns warn when raise_if_missing=False."""
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})

        result = get_subset(df, ["A", "C"], raise_if_missing=False)

        assert list(result.columns) == ["A"]
        assert len(result) == 2

    def test_extra_columns_rename_source_column(self):
        """Test add new source column via extra_columns."""
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4], "C": [5, 6]})

        result = get_subset(df, ["A"], extra_columns={"D": "C"})

        assert list(result.columns) == ["A", "C", "D"]
        assert result["D"].tolist() == [5, 6]

    def test_extra_columns_add_constant(self):
        """Test adding constant column via extra_columns."""
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})

        result = get_subset(df, ["A"], extra_columns={"constant": "fixed_value"})

        assert "constant" in result.columns
        assert result["constant"].tolist() == ["fixed_value", "fixed_value"]

    def test_extra_columns_add_numeric_constant(self):
        """Test adding numeric constant column."""
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})

        result = get_subset(df, ["A"], extra_columns={"num": 42})

        assert result["num"].tolist() == [42, 42]

    def test_extra_columns_add_null_constant(self):
        """Test adding null constant column."""
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})

        result = get_subset(df, ["A"], extra_columns={"nullable": None})

        assert result["nullable"].isna().all()

    def test_extra_columns_mixed_reference_and_constant(self):
        """Test mixing extra column with reference and constant addition."""
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4], "C": [5, 6]})

        result = get_subset(df, ["A"], extra_columns={"extra_B": "B", "constant": 100})

        assert list(result.columns) == ["A", "B", "extra_B", "constant"]
        assert result["extra_B"].tolist() == [3, 4]
        assert result["constant"].tolist() == [100, 100]

    def test_extra_columns_nonexistent_source_as_constant(self):
        """Test that non-existent source column name is treated as constant."""
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})

        result = get_subset(df, ["A"], extra_columns={"new_col": "NonExistent"})

        assert "new_col" in result.columns
        assert result["new_col"].tolist() == ["NonExistent", "NonExistent"]

    def test_drop_duplicates_true(self):
        """Test dropping all duplicates."""
        df = pd.DataFrame({"A": [1, 1, 2], "B": [3, 3, 4]})

        result = get_subset(df, ["A", "B"], drop_duplicates=True)

        assert len(result) == 2

    def test_drop_duplicates_by_subset(self):
        """Test dropping duplicates by subset of columns."""
        df = pd.DataFrame({"A": [1, 1, 2], "B": [3, 4, 5]})

        result = get_subset(df, ["A", "B"], drop_duplicates=["A"])

        assert len(result) == 2
        assert result["A"].tolist() == [1, 2]

    def test_drop_duplicates_false(self):
        """Test keeping duplicates when drop_duplicates=False."""
        df = pd.DataFrame({"A": [1, 1, 2], "B": [3, 3, 4]})

        result = get_subset(df, ["A", "B"], drop_duplicates=False)

        assert len(result) == 3

    def test_functional_dependency_check_passes(self):
        """Test functional dependency check with valid data."""
        df = pd.DataFrame({"key": [1, 1, 2, 2], "value": [10, 10, 20, 20]})

        result = get_subset(df, ["key", "value"], drop_duplicates=["key"], fd_check=True)

        assert len(result) == 2

    def test_functional_dependency_check_fails(self):
        """Test functional dependency check with invalid data."""
        df = pd.DataFrame({"key": [1, 1, 2], "value": [10, 20, 30]})

        with pytest.raises(ValueError, match="inconsistent"):
            get_subset(df, ["key", "value"], drop_duplicates=["key"], fd_check=True)

    def test_complex_workflow(self):
        """Test complex workflow with all features."""
        df = pd.DataFrame({"site_name": ["Site A", "Site A", "Site B"], "location": ["Loc1", "Loc1", "Loc2"], "value": [100, 100, 200]})

        result = get_subset(
            df,
            ["site_name", "location"],
            extra_columns={"renamed_val": "value", "type": "survey"},
            drop_duplicates=["site_name", "location"],
        )

        assert len(result) == 2
        assert set(result.columns) == {"site_name", "location", "renamed_val", "type", "value"}
        assert result["renamed_val"].tolist() == [100, 200]
        assert result["type"].tolist() == ["survey", "survey"]

    def test_empty_dataframe(self):
        """Test with empty DataFrame."""
        df = pd.DataFrame({"A": [], "B": []})

        result = get_subset(df, ["A"], extra_columns={"C": 1})

        assert len(result) == 0
        assert "A" in result.columns
        assert "C" in result.columns

    def test_single_row(self):
        """Test with single row DataFrame."""
        df = pd.DataFrame({"A": [1], "B": [2]})

        result = get_subset(df, ["A"], extra_columns={"renamed": "B"})

        assert len(result) == 1
        assert result["renamed"].tolist() == [2]

    def test_preserves_data_types(self):
        """Test that data types are preserved."""
        df = pd.DataFrame({"int_col": [1, 2], "float_col": [1.5, 2.5], "str_col": ["a", "b"]})

        result = get_subset(df, ["int_col", "float_col", "str_col"])

        assert result["int_col"].dtype == df["int_col"].dtype
        assert result["float_col"].dtype == df["float_col"].dtype
        assert result["str_col"].dtype == df["str_col"].dtype

    def test_column_order_preserved(self):
        """Test that column order matches specification."""
        df = pd.DataFrame({"C": [1, 2], "B": [3, 4], "A": [5, 6]})

        result = get_subset(df, ["A", "B", "C"])

        # Order should be A, B, C as requested (not source order)
        assert list(result.columns) == ["A", "B", "C"]

    def test_extra_columns_empty_dict(self):
        """Test that empty extra_columns dict works."""
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})

        result = get_subset(df, ["A"], extra_columns={})

        assert list(result.columns) == ["A"]

    def test_rename_to_same_name(self):
        """Test renaming column to itself (no-op)."""
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})

        result = get_subset(df, ["A"], extra_columns={"B": "B"})

        assert list(result.columns) == ["A", "B"]
        assert result["B"].tolist() == [3, 4]

    def test_boolean_column_values(self):
        """Test with boolean column values."""
        df = pd.DataFrame({"A": [True, False, True], "B": [1, 2, 3]})

        result = get_subset(df, ["A", "B"], drop_duplicates=False)

        assert result["A"].tolist() == [True, False, True]

    def test_with_null_values(self):
        """Test handling of null values."""
        df = pd.DataFrame({"A": [1, None, 3], "B": [4, 5, None]})

        result = get_subset(df, ["A", "B"])

        assert pd.isna(result.iloc[1]["A"])
        assert pd.isna(result.iloc[2]["B"])


def test_add_surrogate_id_starts_at_one():
    df = pd.DataFrame({"v": [10, 20]})
    out = add_surrogate_id(df, "id")
    assert out["id"].tolist() == [1, 2]
    assert out.index.tolist() == [0, 1]


def test_subset_service_replacements_and_extra_columns():
    """SubsetService should add constants, copy columns, and apply replacements."""
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    service = SubsetService()

    result = service.get_subset(
        source=df,
        columns=["a"],
        extra_columns={"copy_b": "b", "const": 99},
        replacements={"a": {1: 100}},
    )

    assert list(result.columns) == ["a", "b", "copy_b", "const"]
    assert result["a"].tolist() == [100, 2]
    assert result["copy_b"].tolist() == [3, 4]
    assert result["const"].tolist() == [99, 99]
