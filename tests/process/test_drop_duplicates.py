"""Unit tests for arbodat utility functions."""

import pandas as pd
import pytest

from src.specifications.fd import FunctionalDependencySpecification
from src.transforms.drop import drop_duplicate_rows, drop_empty_rows


def test_drop_duplicate_rows_validates_columns_and_fd_check():
    """drop_duplicate_rows should honor fd_check and skip missing columns."""
    df = pd.DataFrame({"a": [1, 1], "b": [2, 3]})

    # Missing column should return unchanged data
    result: pd.DataFrame = drop_duplicate_rows(df, columns=["missing"], entity_name="e1")
    pd.testing.assert_frame_equal(result, df)

    # FD check should raise when duplicates found on determinant
    with pytest.raises(ValueError, match="fd_check"):
        drop_duplicate_rows(df, columns=["a"], fd_check=True, entity_name="e1")

    # Without fd_check duplicates drop
    deduped: pd.DataFrame = drop_duplicate_rows(df, columns=["a"], fd_check=False, entity_name="e1")
    assert len(deduped) == 1


def test_drop_empty_rows_variants():
    """drop_empty_rows handles list and dict subset behaviors."""
    df = pd.DataFrame({"a": ["", None, "x"], "b": ["", "", None]})

    # list subset drops when both empty
    result = drop_empty_rows(data=df, entity_name="e", subset=["a", "b"])
    assert len(result) == 1
    assert result.iloc[0]["a"] == "x"

    # dict subset replaces specified empties with NA
    df2 = pd.DataFrame({"a": ["keep", "drop"], "b": ["zero", "remove"]})
    filtered = drop_empty_rows(data=df2, entity_name="e", subset={"b": ["remove"]})
    assert len(filtered) == 1
    assert filtered.iloc[0]["a"] == "keep"


class TestFunctionalDependencySpecification:
    """Tests for FunctionalDependencySpecification class."""

    def test_valid_functional_dependency(self):
        """Test with valid functional dependency."""
        df = pd.DataFrame({"key": ["A", "A", "B", "B"], "value": [1, 1, 2, 2]})
        specification = FunctionalDependencySpecification()
        result = specification.is_satisfied_by(df=df, determinant_columns=["key"], raise_error=False)
        assert result is True

    def test_invalid_functional_dependency_raises(self):
        """Test that invalid dependency raises error."""
        df = pd.DataFrame({"key": ["A", "A", "B"], "value": [1, 2, 3]})

        with pytest.raises(ValueError, match="inconsistent non-subset values"):
            specification = FunctionalDependencySpecification()
            specification.is_satisfied_by(df=df, determinant_columns=["key"], raise_error=True)

    def test_invalid_functional_dependency_warns(self):
        """Test that invalid dependency warns when raise_error=False."""
        df = pd.DataFrame({"key": ["A", "A"], "value": [1, 2]})

        specification = FunctionalDependencySpecification()
        result = specification.is_satisfied_by(df=df, determinant_columns=["key"], raise_error=False)
        assert result is False

    def test_no_dependent_columns(self):
        """Test with only determinant columns."""
        df = pd.DataFrame({"key": ["A", "B", "C"]})

        specification = FunctionalDependencySpecification()
        result = specification.is_satisfied_by(df=df, determinant_columns=["key"], raise_error=True)
        assert result is True

    def test_multiple_determinant_columns(self):
        """Test with multiple determinant columns."""
        df = pd.DataFrame({"key1": ["A", "A", "B", "B"], "key2": [1, 2, 1, 2], "value": [10, 20, 30, 40]})

        specification = FunctionalDependencySpecification()
        result = specification.is_satisfied_by(df=df, determinant_columns=["key1", "key2"], raise_error=False)
        assert result is True
