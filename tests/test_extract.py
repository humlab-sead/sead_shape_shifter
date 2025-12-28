"""Tests for src.extract helper functions."""

import pandas as pd
import pytest

from src.extract import SubsetService, add_surrogate_id, drop_duplicate_rows, drop_empty_rows, extract_translation_map, translate


def test_drop_duplicate_rows_validates_columns_and_fd_check():
    """drop_duplicate_rows should honor fd_check and skip missing columns."""
    df = pd.DataFrame({"a": [1, 1], "b": [2, 3]})

    # Missing column should return unchanged data
    result = drop_duplicate_rows(df, columns=["missing"], entity_name="e1")
    pd.testing.assert_frame_equal(result, df)

    # FD check should raise when duplicates found on determinant
    with pytest.raises(ValueError, match="fd_check"):
        drop_duplicate_rows(df, columns=["a"], fd_check=True, entity_name="e1")

    # Without fd_check duplicates drop
    deduped = drop_duplicate_rows(df, columns=["a"], fd_check=False, entity_name="e1")
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


def test_extract_translation_map_missing_keys_warns():
    """Missing required keys yields empty translation map."""
    # keys missing -> empty result
    assert extract_translation_map([{"wrong": "v"}]) == {}

    # valid mapping
    fields = [{"arbodat_field": "Ort", "english_column_name": "location"}]
    assert extract_translation_map(fields) == {"Ort": "location"}


def test_translate_skips_conflicting_columns():
    """Translation should avoid clobbering existing columns."""
    df = pd.DataFrame({"Ort": ["A"], "location": ["orig"]})
    data = {"entity": df}
    translated = translate(data, {"Ort": "location"})
    assert list(translated["entity"].columns) == ["Ort", "location"]
