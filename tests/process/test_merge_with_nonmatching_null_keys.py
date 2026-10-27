"""Unit tests for nonmatching-null merges and related helpers in src/transforms/utility.py."""

import pandas as pd
import pytest

from src.transforms.utility import merge_with_nonmatching_null_keys

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _df(data: dict) -> pd.DataFrame:
    return pd.DataFrame(data)


# ===========================================================================
# Basic merge behavior (no null-key match prevention or coercion)
# ===========================================================================


class TestBasicMerge:

    def test_inner_merge_matching_rows(self):
        left = _df({"id": [1, 2, 3], "val": ["a", "b", "c"]})
        right = _df({"id": [2, 3, 4], "label": ["B", "C", "D"]})

        result = merge_with_nonmatching_null_keys(left, right, left_on=["id"], right_on=["id"], how="inner")

        assert list(result["id"]) == [2, 3]
        assert list(result["label"]) == ["B", "C"]

    def test_left_merge_preserves_unmatched_rows(self):
        left = _df({"id": [1, 2, 3], "val": ["a", "b", "c"]})
        right = _df({"id": [2, 3], "label": ["B", "C"]})

        result = merge_with_nonmatching_null_keys(left, right, left_on=["id"], right_on=["id"], how="left")

        assert len(result) == 3
        assert pd.isna(result.loc[result["id"] == 1, "label"].iloc[0])

    def test_cross_merge_bypasses_coercion_and_null_key_match_prevention(self):
        left = _df({"x": [1, 2]})
        right = _df({"y": ["a", "b"]})

        result = merge_with_nonmatching_null_keys(left, right, how="cross")

        assert len(result) == 4  # 2 × 2

    def test_no_left_on_right_on_falls_through_to_pd_merge(self):
        """When left_on/right_on are absent, delegates straight to pd.merge."""
        left = _df({"key": [1, 2], "val": ["a", "b"]})
        right = _df({"key": [1, 2], "extra": ["x", "y"]})

        result = merge_with_nonmatching_null_keys(left, right, on="key", how="inner")

        assert list(result["val"]) == ["a", "b"]


# ===========================================================================
# Prevent null keys from matching (sentinel-based handling)
# ===========================================================================


class TestNonmatchingNullKeysMerge:

    def test_nulls_in_left_key_do_not_match_nulls_in_right_key(self):
        left = _df({"lid": [1, None, 3], "val": ["a", "b", "c"]})
        right = _df({"rid": [1, None, 3], "label": ["A", "B", "C"]})

        result = merge_with_nonmatching_null_keys(
            left,
            right,
            prevent_null_key_matches=True,
            left_on=["lid"],
            right_on=["rid"],
            how="inner",
        )

        # Only rows with lid=1 and lid=3 should match; nulls must not match each other
        assert len(result) == 2
        assert set(result["lid"].dropna().tolist()) == {1.0, 3.0}

    def test_nonmatching_null_left_merge_keeps_unmatched_nulls(self):
        left = _df({"lid": [1, None], "val": ["a", "b"]})
        right = _df({"rid": [1], "label": ["A"]})

        result = merge_with_nonmatching_null_keys(
            left,
            right,
            prevent_null_key_matches=True,
            left_on=["lid"],
            right_on=["rid"],
            how="left",
        )

        assert len(result) == 2
        # The null-id row from left must still appear, with NaN label
        null_row = result[result["lid"].isna()]
        assert len(null_row) == 1
        assert pd.isna(null_row["label"].iloc[0])

    def test_allow_null_keys_true_prevents_null_key_matches(self):
        """allow_null_keys=True permits nulls without matching them across merge sides."""
        left = _df({"lid": [1, None]})
        right = _df({"rid": [1, None]})

        result = merge_with_nonmatching_null_keys(
            left,
            right,
            allow_null_keys=True,
            left_on=["lid"],
            right_on=["rid"],
            how="inner",
        )

        assert len(result) == 1
        assert result["lid"].iloc[0] == 1.0

    def test_no_nulls_takes_fast_path(self):
        """Without nulls in keys, the helper uses pd.merge directly."""
        left = _df({"id": [1, 2, 3]})
        right = _df({"id": [1, 2, 3], "label": ["A", "B", "C"]})

        result = merge_with_nonmatching_null_keys(
            left,
            right,
            prevent_null_key_matches=True,
            left_on=["id"],
            right_on=["id"],
            how="inner",
        )

        assert len(result) == 3

    def test_temp_sentinel_columns_are_dropped_from_result(self):
        left = _df({"id": [1, None]})
        right = _df({"id": [1, None]})

        result = merge_with_nonmatching_null_keys(
            left,
            right,
            prevent_null_key_matches=True,
            left_on=["id"],
            right_on=["id"],
            how="left",
        )

        sentinel_cols = [c for c in result.columns if "__nullsafe" in c or "__ss_null" in c]
        assert sentinel_cols == []

    def test_mismatched_key_counts_raises(self):
        left = _df({"a": [1], "b": [2]})
        right = _df({"x": [1]})

        with pytest.raises(ValueError, match="Mismatched merge key counts"):
            merge_with_nonmatching_null_keys(
                left,
                right,
                prevent_null_key_matches=True,
                left_on=["a", "b"],
                right_on=["x"],
                how="inner",
            )


# ===========================================================================
# Dtype coercion (object ↔ numeric)
# ===========================================================================


class TestDtypeCoercion:

    def test_string_left_key_coerced_to_match_int_right_key(self):
        """YAML strings like '1'/'17' joining DB int column."""
        left = _df({"group_id": ["1", "17", "1"], "name": ["a", "b", "c"]})
        right = _df({"group_id": [1, 17], "label": ["grp1", "grp17"]})

        result = merge_with_nonmatching_null_keys(left, right, left_on=["group_id"], right_on=["group_id"], how="left")

        assert len(result) == 3
        assert list(result["label"]) == ["grp1", "grp17", "grp1"]

    def test_int_left_key_joins_string_right_key(self):
        """Numeric left, string right — coerces right side."""
        left = _df({"id": [1, 2], "val": ["a", "b"]})
        right = _df({"id": ["1", "2"], "extra": ["x", "y"]})

        result = merge_with_nonmatching_null_keys(left, right, left_on=["id"], right_on=["id"], how="inner")

        assert len(result) == 2

    def test_non_numeric_strings_not_coerced(self):
        """Object key with non-numeric values (real strings) must not be coerced."""
        left = _df({"code": ["A", "B"], "val": [1, 2]})
        right = _df({"code": [1, 2], "label": ["x", "y"]})

        # Coercion of 'A', 'B' to numeric would produce NaN for all rows.
        # The coercion safety guard should reject this, and the merge should
        # still raise (incompatible types) rather than silently drop rows.
        with pytest.raises(Exception):
            merge_with_nonmatching_null_keys(left, right, left_on=["code"], right_on=["code"], how="inner")

    def test_coercion_preserves_null_values(self):
        """Coercion must not inflate NaN counts (safety guard)."""
        left = _df({"id": ["1", None, "3"], "val": ["a", "b", "c"]})
        right = _df({"id": [1, 2, 3], "label": ["A", "B", "C"]})

        result = merge_with_nonmatching_null_keys(left, right, left_on=["id"], right_on=["id"], how="left")

        assert len(result) == 3
        # id=None row should have no label match
        null_row = result[result["id"].isna()]
        assert len(null_row) == 1
        assert pd.isna(null_row["label"].iloc[0])

    def test_both_numeric_no_coercion_needed(self):
        """Both sides numeric — coercion is a no-op and merge works normally."""
        left = _df({"id": [1, 2, 3]})
        right = _df({"id": [2, 3, 4], "label": ["B", "C", "D"]})

        result = merge_with_nonmatching_null_keys(left, right, left_on=["id"], right_on=["id"], how="inner")

        assert len(result) == 2

    def test_both_string_no_coercion_applied(self):
        """Both sides string — coercion is a no-op and merge works normally."""
        left = _df({"code": ["A", "B", "C"]})
        right = _df({"code": ["B", "C", "D"], "label": ["b", "c", "d"]})

        result = merge_with_nonmatching_null_keys(left, right, left_on=["code"], right_on=["code"], how="inner")

        assert list(result["label"]) == ["b", "c"]

    def test_coercion_combined_with_nonmatching_null_keys(self):
        """Dtype coercion and null-key match prevention work together."""
        left = _df({"id": ["1", None, "3"]})
        right = _df({"id": [1, 2, 3], "label": ["A", "B", "C"]})

        result = merge_with_nonmatching_null_keys(
            left,
            right,
            allow_null_keys=True,
            left_on=["id"],
            right_on=["id"],
            how="left",
        )

        assert len(result) == 3
        matched = result.dropna(subset=["label"])
        assert set(matched["label"].tolist()) == {"A", "C"}

    def test_multi_key_coercion(self):
        """Multiple join keys — coercion applied per key pair."""
        left = _df({"a": ["1", "2"], "b": ["10", "20"], "val": ["x", "y"]})
        right = _df({"a": [1, 2], "b": [10, 20], "extra": ["X", "Y"]})

        result = merge_with_nonmatching_null_keys(left, right, left_on=["a", "b"], right_on=["a", "b"], how="inner")

        assert len(result) == 2
        assert list(result["extra"]) == ["X", "Y"]
