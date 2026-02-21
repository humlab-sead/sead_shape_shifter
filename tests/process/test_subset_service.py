from __future__ import annotations

import copy

import pandas as pd
import pytest

from src.extract import SubsetService
from src.model import TableConfig

ENTITY_NAME = "test_entity"

BASE_ENTITY_CFG: dict[str, object] = {
    "columns": ["id"],
    "keys": [],
    "drop_duplicates": False,
    "drop_empty_rows": False,
    "extra_columns": {},
    "replacements": {},
    "check_functional_dependency": False,
    "strict_functional_dependency": False,
}


def build_table_config(**overrides: object) -> TableConfig:
    """Return a fresh TableConfig for the test entity with optional overrides."""
    entity_cfg = copy.deepcopy(BASE_ENTITY_CFG)
    entity_cfg.update(overrides)
    return TableConfig(entities_cfg={ENTITY_NAME: entity_cfg}, entity_name=ENTITY_NAME)


def test_get_subset_raises_when_columns_missing() -> None:
    service = SubsetService()
    df = pd.DataFrame({"present": [1, 2]})
    table_cfg = build_table_config(columns=["missing"])

    with pytest.raises(ValueError, match="Columns not found"):
        service.get_subset(source=df, table_cfg=table_cfg)


def test_get_subset_skips_missing_columns_when_requested() -> None:
    service = SubsetService()
    df = pd.DataFrame({"present": [1, 2], "other": [10, 20]})
    table_cfg = build_table_config(columns=["present", "missing"])

    result = service.get_subset(source=df, table_cfg=table_cfg, raise_if_missing=False)

    assert list(result.columns) == ["present"]
    assert result["present"].tolist() == [1, 2]


def test_get_subset_resolves_extra_columns_case_insensitive() -> None:
    service = SubsetService()
    df = pd.DataFrame({"ID": [1, 2], "VALUE": ["foo", "bar"]})
    table_cfg = build_table_config(columns=["ID"], extra_columns={"value_copy": "value"})

    result = service.get_subset(source=df, table_cfg=table_cfg)

    assert "value_copy" in result.columns
    assert result["value_copy"].tolist() == ["foo", "bar"]


def test_get_subset_adds_constant_extra_column() -> None:
    service = SubsetService()
    df = pd.DataFrame({"id": [1, 2]})
    table_cfg = build_table_config(columns=["id"], extra_columns={"constant_flag": True})

    result = service.get_subset(source=df, table_cfg=table_cfg)

    assert result["constant_flag"].tolist() == [True, True]


def test_get_subset_drops_all_duplicates_when_enabled() -> None:
    service = SubsetService()
    df = pd.DataFrame({"id": [1, 1, 2], "value": [10, 10, 20]})
    table_cfg = build_table_config(columns=["id", "value"], drop_duplicates=True)

    result = service.get_subset(source=df, table_cfg=table_cfg)

    assert len(result) == 2
    assert result["id"].tolist() == [1, 2]


def test_get_subset_drops_duplicates_by_subset_columns() -> None:
    service = SubsetService()
    df = pd.DataFrame({"id": [1, 1, 2], "value": [10, 11, 20]})
    table_cfg = build_table_config(columns=["id", "value"], drop_duplicates=["id"])

    result = service.get_subset(source=df, table_cfg=table_cfg)

    assert len(result) == 2
    assert result["value"].tolist() == [10, 20]


def test_get_subset_drops_empty_rows_when_all_columns_empty() -> None:
    service = SubsetService()
    df = pd.DataFrame({"id": [pd.NA, 2, 3], "value": [pd.NA, "x", ""]})
    table_cfg = build_table_config(columns=["id", "value"], drop_empty_rows=True)

    result = service.get_subset(source=df, table_cfg=table_cfg)

    assert len(result) == 2
    assert result["id"].tolist() == [2, 3]
    assert result["value"].iloc[0] == "x"
    assert pd.isna(result["value"].iloc[1])


def test_get_subset_drops_empty_rows_for_subset_columns() -> None:
    service = SubsetService()
    df = pd.DataFrame({"id": [1, 2, 3], "value": ["x", "", None]})
    table_cfg = build_table_config(columns=["id", "value"])

    result = service.get_subset(source=df, table_cfg=table_cfg, drop_empty=["value"])

    assert len(result) == 1
    assert result["id"].iloc[0] == 1
    assert result["value"].iloc[0] == "x"


def test_get_subset_applies_mapping_replacements() -> None:
    service = SubsetService()
    df = pd.DataFrame({"id": [1, 2], "status": ["yes", "no"]})
    table_cfg = build_table_config(columns=["id", "status"], replacements={"status": {"yes": "Y", "no": "N"}})

    result = service.get_subset(source=df, table_cfg=table_cfg)

    assert result["status"].tolist() == ["Y", "N"]


def test_get_subset_applies_scalar_replacements_with_forward_fill() -> None:
    service = SubsetService()
    df = pd.DataFrame({"id": [1, 2, 3], "status": ["keep", "drop", "drop"]})
    table_cfg = build_table_config(columns=["id", "status"], replacements={"status": ["drop"]})

    result = service.get_subset(source=df, table_cfg=table_cfg)

    assert result["status"].tolist() == ["keep", "keep", "keep"]


def test_get_subset_applies_advanced_replacements_regex_rule() -> None:
    service = SubsetService()
    df = pd.DataFrame({"id": [1, 2, 3], "coord_sys": ["DHDN Zone 3", "dhdn   zone 3", "EPSG:4326"]})
    table_cfg = build_table_config(
        columns=["id", "coord_sys"],
        replacements={
            "coord_sys": [
                {
                    "match": "regex",
                    "from": r"^dhdn\s+zone\s+3$",
                    "to": "EPSG:31467",
                    "flags": ["ignorecase"],
                    "normalize": ["collapse_ws", "lower"],
                }
            ]
        },
    )

    result = service.get_subset(source=df, table_cfg=table_cfg)

    assert result["coord_sys"].tolist() == ["EPSG:31467", "EPSG:31467", "EPSG:4326"]


def test_get_subset_applies_advanced_replacements_not_regex_rule() -> None:
    service = SubsetService()
    df = pd.DataFrame({"id": [1, 2, 3, 4], "coord_sys": ["EPSG:4326", "epsg:3857", "DHDN Zone 3", None]})
    table_cfg = build_table_config(
        columns=["id", "coord_sys"],
        replacements={
            "coord_sys": [
                {
                    "match": "not_regex",
                    "from": r"^epsg:\d+$",
                    "to": "OTHER",
                    "flags": ["ignorecase"],
                    "normalize": ["strip", "lower"],
                }
            ]
        },
    )

    result = service.get_subset(source=df, table_cfg=table_cfg)

    # Only values NOT matching the regex are replaced; NA stays NA.
    assert result["coord_sys"].tolist() == ["EPSG:4326", "epsg:3857", "OTHER", None]


def test_get_subset_applies_advanced_replacements_map_with_normalize() -> None:
    service = SubsetService()
    df = pd.DataFrame({"id": [1, 2, 3], "status": [" Yes ", "NO", "maybe"]})
    table_cfg = build_table_config(
        columns=["id", "status"],
        replacements={
            "status": [
                {
                    "map": {"yes": "Y", "no": "N"},
                    "normalize": ["strip", "lower"],
                }
            ]
        },
    )

    result = service.get_subset(source=df, table_cfg=table_cfg)

    assert result["status"].tolist() == ["Y", "N", "maybe"]


def test_get_subset_advanced_replacements_diagnostics_do_not_change_output() -> None:
    service = SubsetService()
    df = pd.DataFrame({"id": [1, 2, 3], "status": [" Yes ", "NO", "maybe"]})
    table_cfg = build_table_config(
        columns=["id", "status"],
        replacements={
            "status": [
                {
                    "map": {"yes": "Y", "no": "N"},
                    "normalize": ["strip", "lower"],
                    "report_replaced": True,
                    "report_unmatched": True,
                    "report_top": 5,
                }
            ]
        },
    )

    result = service.get_subset(source=df, table_cfg=table_cfg)

    assert result["status"].tolist() == ["Y", "N", "maybe"]


def test_get_subset_applies_advanced_replacements_blank_out_fill_none() -> None:
    service = SubsetService()
    df = pd.DataFrame({"id": [1, 2, 3], "status": ["keep", "drop", "keep"]})
    table_cfg = build_table_config(
        columns=["id", "status"],
        replacements={
            "status": [
                {
                    "blank_out": ["drop"],
                    "fill": "none",
                }
            ]
        },
    )

    result = service.get_subset(source=df, table_cfg=table_cfg)

    assert result["status"].tolist() == ["keep", pd.NA, "keep"]


def test_get_subset_applies_advanced_replacements_blank_out_fill_constant() -> None:
    service = SubsetService()
    df = pd.DataFrame({"id": [1, 2, 3], "status": ["keep", "drop", None]})
    table_cfg = build_table_config(
        columns=["id", "status"],
        replacements={
            "status": [
                {
                    "blank_out": ["drop"],
                    "fill": {"constant": "UNKNOWN"},
                }
            ]
        },
    )

    result = service.get_subset(source=df, table_cfg=table_cfg)

    assert result["status"].tolist() == ["keep", "UNKNOWN", "UNKNOWN"]


def test_get_subset_applies_advanced_replacements_contains_rule() -> None:
    service = SubsetService()
    df = pd.DataFrame({"id": [1, 2, 3], "note": ["has FOO", "no match", "foo inside"]})
    table_cfg = build_table_config(
        columns=["id", "note"],
        replacements={
            "note": [
                {
                    "match": "contains",
                    "from": "foo",
                    "to": "HAS_FOO",
                    "flags": ["ignorecase"],
                }
            ]
        },
    )

    result = service.get_subset(source=df, table_cfg=table_cfg)

    assert result["note"].tolist() == ["HAS_FOO", "no match", "HAS_FOO"]


def test_get_subset_applies_transform_rule_normalize_all_values() -> None:
    """Test transform rule that applies normalize operations to all values (no match filter)."""
    service = SubsetService()
    df = pd.DataFrame({"id": [1, 2, 3], "name": ["  Alice  ", "BOB", " charlie "]})
    table_cfg = build_table_config(
        columns=["id", "name"],
        replacements={
            "name": [
                {
                    "normalize": ["strip", "lower"],
                }
            ]
        },
    )

    result = service.get_subset(source=df, table_cfg=table_cfg)

    # All values normalized without any filtering
    assert result["name"].tolist() == ["alice", "bob", "charlie"]


def test_get_subset_applies_transform_rule_coerce_all_values() -> None:
    """Test transform rule that coerces all values (no match filter)."""
    service = SubsetService()
    df = pd.DataFrame({"id": [1, 2, 3], "value": ["42", "100", "999"]})
    table_cfg = build_table_config(
        columns=["id", "value"],
        replacements={
            "value": [
                {
                    "coerce": "int",
                }
            ]
        },
    )

    result = service.get_subset(source=df, table_cfg=table_cfg)

    # All values coerced to int
    assert result["value"].dtype == "Int64"
    assert result["value"].tolist() == [42, 100, 999]


def test_get_subset_applies_transform_rule_normalize_and_coerce() -> None:
    """Test transform rule that applies both normalize and coerce to all values."""
    service = SubsetService()
    df = pd.DataFrame({"id": [1, 2, 3], "amount": ["  3.14  ", "2.71", " 1.41 "]})
    table_cfg = build_table_config(
        columns=["id", "amount"],
        replacements={
            "amount": [
                {
                    "normalize": ["strip"],
                    "coerce": "float",
                }
            ]
        },
    )

    result = service.get_subset(source=df, table_cfg=table_cfg)

    # All values normalized and coerced
    assert result["amount"].tolist() == [3.14, 2.71, 1.41]


def test_get_subset_applies_advanced_replacements_startswith_rule() -> None:
    service = SubsetService()
    df = pd.DataFrame({"id": [1, 2, 3], "code": ["ABC123", "abC999", "XABC"]})
    table_cfg = build_table_config(
        columns=["id", "code"],
        replacements={
            "code": [
                {
                    "match": "startswith",
                    "from": "abc",
                    "to": "STARTS_ABC",
                    "flags": ["ignorecase"],
                }
            ]
        },
    )

    result = service.get_subset(source=df, table_cfg=table_cfg)

    assert result["code"].tolist() == ["STARTS_ABC", "STARTS_ABC", "XABC"]


def test_get_subset_applies_advanced_replacements_not_startswith_rule() -> None:
    service = SubsetService()
    df = pd.DataFrame({"id": [1, 2, 3, 4], "code": ["ABC123", "abC999", "XABC", None]})
    table_cfg = build_table_config(
        columns=["id", "code"],
        replacements={
            "code": [
                {
                    "match": "not_startswith",
                    "from": "abc",
                    "to": "OTHER",
                    "flags": ["ignorecase"],
                }
            ]
        },
    )

    result = service.get_subset(source=df, table_cfg=table_cfg)

    # Only values NOT starting with abc are replaced; NA stays NA.
    assert result["code"].tolist() == ["ABC123", "abC999", "OTHER", None]


def test_get_subset_applies_advanced_replacements_endswith_rule() -> None:
    service = SubsetService()
    df = pd.DataFrame({"id": [1, 2, 3], "filename": ["file.TXT", "report.txt", "doc.pdf"]})
    table_cfg = build_table_config(
        columns=["id", "filename"],
        replacements={
            "filename": [
                {
                    "match": "endswith",
                    "from": ".txt",
                    "to": "TEXT_FILE",
                    "flags": ["ignorecase"],
                }
            ]
        },
    )

    result = service.get_subset(source=df, table_cfg=table_cfg)

    assert result["filename"].tolist() == ["TEXT_FILE", "TEXT_FILE", "doc.pdf"]


def test_get_subset_applies_advanced_replacements_not_endswith_rule() -> None:
    service = SubsetService()
    df = pd.DataFrame({"id": [1, 2, 3, 4], "filename": ["file.TXT", "report.txt", "doc.pdf", None]})
    table_cfg = build_table_config(
        columns=["id", "filename"],
        replacements={
            "filename": [
                {
                    "match": "not_endswith",
                    "from": ".txt",
                    "to": "OTHER",
                    "flags": ["ignorecase"],
                }
            ]
        },
    )

    result = service.get_subset(source=df, table_cfg=table_cfg)

    # Only values NOT ending with .txt are replaced; NA stays NA.
    assert result["filename"].tolist() == ["file.TXT", "report.txt", "OTHER", None]


def test_get_subset_applies_advanced_replacements_in_rule_ignorecase() -> None:
    service = SubsetService()
    df = pd.DataFrame({"id": [1, 2, 3, 4], "status": ["A", "b", "C", None]})
    table_cfg = build_table_config(
        columns=["id", "status"],
        replacements={
            "status": [
                {
                    "match": "in",
                    "from": ["a", "b"],
                    "to": "X",
                    "flags": ["ignorecase"],
                }
            ]
        },
    )

    result = service.get_subset(source=df, table_cfg=table_cfg)

    assert result["status"].tolist() == ["X", "X", "C", None]


def test_get_subset_applies_advanced_replacements_not_in_rule_ignorecase() -> None:
    service = SubsetService()
    df = pd.DataFrame({"id": [1, 2, 3, 4], "status": ["A", "b", "C", None]})
    table_cfg = build_table_config(
        columns=["id", "status"],
        replacements={
            "status": [
                {
                    "match": "not_in",
                    "from": ["a", "b"],
                    "to": "OTHER",
                    "flags": ["ignorecase"],
                }
            ]
        },
    )

    result = service.get_subset(source=df, table_cfg=table_cfg)

    # Only values NOT in {a,b} are replaced; NA stays NA.
    assert result["status"].tolist() == ["A", "b", "OTHER", None]


def test_get_subset_applies_advanced_replacements_not_contains_does_not_touch_na() -> None:
    service = SubsetService()
    df = pd.DataFrame({"id": [1, 2, 3], "note": ["has foo", "bar", None]})
    table_cfg = build_table_config(
        columns=["id", "note"],
        replacements={
            "note": [
                {
                    "match": "not_contains",
                    "from": "foo",
                    "to": "NO_FOO",
                    "flags": ["ignorecase"],
                }
            ]
        },
    )

    result = service.get_subset(source=df, table_cfg=table_cfg)

    assert result["note"].tolist() == ["has foo", "NO_FOO", None]


def test_get_subset_applies_advanced_replacements_equals_with_coerce_int() -> None:
    service = SubsetService()
    df = pd.DataFrame({"id": [1, 2, 3, 4], "val": ["1", "2", "x", None]})
    table_cfg = build_table_config(
        columns=["id", "val"],
        replacements={
            "val": [
                {
                    "match": "equals",
                    "from": 2,
                    "to": "TWO",
                    "coerce": "int",
                }
            ]
        },
    )

    result = service.get_subset(source=df, table_cfg=table_cfg)

    assert result["val"].tolist() == ["1", "TWO", "x", None]


def test_get_subset_applies_advanced_replacements_not_equals_with_normalize() -> None:
    service = SubsetService()
    df = pd.DataFrame({"id": [1, 2, 3], "status": [" A ", "b", None]})
    table_cfg = build_table_config(
        columns=["id", "status"],
        replacements={
            "status": [
                {
                    "match": "not_equals",
                    "from": "a",
                    "to": "OTHER",
                    "normalize": ["strip", "lower"],
                }
            ]
        },
    )

    result = service.get_subset(source=df, table_cfg=table_cfg)

    # Only values not equal to "a" (after normalization) are replaced; NA stays NA.
    assert result["status"].tolist() == [" A ", "OTHER", None]


def test_get_subset_applies_advanced_replacements_not_equals_with_coerce_int() -> None:
    service = SubsetService()
    df = pd.DataFrame({"id": [1, 2, 3, 4], "val": ["1", "2", "x", None]})
    table_cfg = build_table_config(
        columns=["id", "val"],
        replacements={
            "val": [
                {
                    "match": "not_equals",
                    "from": 2,
                    "to": "OTHER",
                    "coerce": "int",
                }
            ]
        },
    )

    result = service.get_subset(source=df, table_cfg=table_cfg)

    # With coerce=int, only coercible non-2 values are replaced; non-coercible values remain unchanged.
    assert result["val"].tolist() == ["OTHER", "2", "x", None]


def test_get_subset_applies_advanced_replacements_map_with_coerce_int() -> None:
    service = SubsetService()
    df = pd.DataFrame({"id": [1, 2, 3], "val": ["1", "2", "x"]})
    table_cfg = build_table_config(
        columns=["id", "val"],
        replacements={
            "val": [
                {
                    "map": {1: "ONE"},
                    "coerce": "int",
                }
            ]
        },
    )

    result = service.get_subset(source=df, table_cfg=table_cfg)

    assert result["val"].tolist() == ["ONE", "2", "x"]


def test_get_subset_applies_advanced_replacements_regex_sub_rule() -> None:
    service = SubsetService()
    df = pd.DataFrame({"id": [1, 2], "coord_sys": ["DHDN Zone 3", "DHDN Zone 12"]})
    table_cfg = build_table_config(
        columns=["id", "coord_sys"],
        replacements={
            "coord_sys": [
                {
                    "match": "regex_sub",
                    "from": r"\bZone\s+(\d+)\b",
                    "to": r"Z\1",
                }
            ]
        },
    )

    result = service.get_subset(source=df, table_cfg=table_cfg)

    assert result["coord_sys"].tolist() == ["DHDN Z3", "DHDN Z12"]


def test_get_subset_applies_advanced_replacements_regex_sub_to_null_sets_na() -> None:
    service = SubsetService()
    df = pd.DataFrame({"id": [1, 2, 3], "val": ["keep", "drop-me", "also keep"]})
    table_cfg = build_table_config(
        columns=["id", "val"],
        replacements={
            "val": [
                {
                    "match": "regex_sub",
                    "from": r"drop",
                    "to": None,
                }
            ]
        },
    )

    result = service.get_subset(source=df, table_cfg=table_cfg)

    assert result["val"].tolist() == ["keep", pd.NA, "also keep"]


# ========== Additional coverage: null source, get_subset_columns logic, etc. ==========


def test_get_subset_raises_when_source_is_none() -> None:
    """Test that source=None raises ValueError."""
    service = SubsetService()
    table_cfg = build_table_config(columns=["id"])

    with pytest.raises(ValueError, match="Source DataFrame must be provided"):
        service.get_subset(source=None, table_cfg=table_cfg)  # type: ignore[arg-type]


def test_get_subset_respects_drop_empty_false() -> None:
    """Test that drop_empty=False preserves all rows."""
    service = SubsetService()
    df = pd.DataFrame({"id": [1, pd.NA], "value": [pd.NA, pd.NA]})
    table_cfg = build_table_config(columns=["id", "value"])

    result = service.get_subset(source=df, table_cfg=table_cfg, drop_empty=False)

    assert len(result) == 2


def test_get_subset_drops_empty_rows_with_dict_subset() -> None:
    """Test drop_empty_rows with dict mapping columns to values to treat as empty."""
    service = SubsetService()
    df = pd.DataFrame({"id": [1, 2, 3], "status": ["active", "deleted", "deleted"]})
    table_cfg = build_table_config(columns=["id", "status"])

    result = service.get_subset(source=df, table_cfg=table_cfg, drop_empty={"status": ["deleted"]})

    assert len(result) == 1
    assert result["id"].iloc[0] == 1
    assert result["status"].iloc[0] == "active"


def test_get_subset_skips_drop_empty_for_missing_subset_columns() -> None:
    """Test that missing columns in drop_empty subset are skipped gracefully."""
    service = SubsetService()
    df = pd.DataFrame({"id": [1, 2]})
    table_cfg = build_table_config(columns=["id"])

    # Should not raise; missing columns in drop_empty subset are skipped
    result = service.get_subset(source=df, table_cfg=table_cfg, drop_empty=["missing_col"])

    assert len(result) == 2


def test_get_subset_ignores_replacements_for_missing_columns() -> None:
    """Test that replacements for columns not in result are ignored gracefully."""
    service = SubsetService()
    df = pd.DataFrame({"id": [1, 2]})
    table_cfg = build_table_config(columns=["id"], replacements={"missing_col": {1: 100}})

    result = service.get_subset(source=df, table_cfg=table_cfg)

    assert list(result.columns) == ["id"]
    assert result["id"].tolist() == [1, 2]


def test_get_subset_preserves_column_order() -> None:
    """Test that column order is preserved according to table_cfg columns."""
    service = SubsetService()
    df = pd.DataFrame({"c": [3], "b": [2], "a": [1]})
    table_cfg = build_table_config(columns=["a", "b", "c"])

    result = service.get_subset(source=df, table_cfg=table_cfg)

    assert list(result.columns) == ["a", "b", "c"]


def test_get_subset_appends_extra_columns_at_end() -> None:
    """Test that extra columns are appended after main columns."""
    service = SubsetService()
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4], "c": [5, 6]})
    table_cfg = build_table_config(columns=["a"], extra_columns={"new_col": 99})

    result = service.get_subset(source=df, table_cfg=table_cfg)

    assert list(result.columns) == ["a", "new_col"]
    assert result["new_col"].tolist() == [99, 99]


def test_split_extra_columns_case_sensitive() -> None:
    """Test _split_extra_columns with case_sensitive=True."""
    service = SubsetService()
    df = pd.DataFrame({"ID": [1, 2], "Value": ["x", "y"]})
    extra_cols = {"copy_id": "ID", "constant_col": "static_value"}

    source_cols, constant_cols = service._split_extra_columns(df, extra_cols, case_sensitive=True)

    assert source_cols == {"copy_id": "ID"}
    assert constant_cols == {"constant_col": "static_value"}


def test_split_extra_columns_case_insensitive() -> None:
    """Test _split_extra_columns with case_sensitive=False (default)."""
    service = SubsetService()
    df = pd.DataFrame({"ID": [1, 2], "Value": ["x", "y"]})
    extra_cols = {"copy_id": "id", "copy_value": "value", "const": "not_in_df"}

    source_cols, constant_cols = service._split_extra_columns(df, extra_cols, case_sensitive=False)

    assert source_cols == {"copy_id": "ID", "copy_value": "Value"}
    assert constant_cols == {"const": "not_in_df"}


def test_check_if_missing_requested_columns_raises_by_default() -> None:
    """Test _check_if_missing_requested_columns raises ValueError by default."""
    service = SubsetService()
    df = pd.DataFrame({"a": [1]})

    with pytest.raises(ValueError, match="Columns not found"):
        service._check_if_missing_requested_columns(df, "test_entity", True, {"a", "missing"})


def test_check_if_missing_requested_columns_warns_when_not_raising() -> None:
    """Test _check_if_missing_requested_columns warns instead of raising."""
    service = SubsetService()
    df = pd.DataFrame({"a": [1]})

    # Should not raise, just log warning
    service._check_if_missing_requested_columns(df, "test_entity", False, {"a", "missing"})
    # If no exception is raised, test passes


def test_restore_columns_order_with_extra_columns() -> None:
    """Test _restore_columns_order preserves requested order then appends extras."""
    service = SubsetService()
    df = pd.DataFrame({"extra": [1], "c": [2], "a": [3], "b": [4]})
    requested = ["a", "b", "c"]

    result = service._restore_columns_order(df, requested)

    assert list(result.columns) == ["a", "b", "c", "extra"]


def test_get_subset_with_multiple_transformations() -> None:
    """Test get_subset with combined operations: extra_columns, duplicates, empty rows, replacements."""
    service = SubsetService()
    df = pd.DataFrame(
        {
            "id": [1, 1, 2, 3],
            "status": ["active", "active", "active", "old"],
        }
    )
    table_cfg = build_table_config(
        columns=["id", "status"],
        extra_columns={"id_copy": "id"},
        drop_duplicates=["id", "status"],
        replacements={"status": {"old": "archived"}},
    )

    result = service.get_subset(source=df, table_cfg=table_cfg)

    # Duplicates dropped, replacements applied
    assert len(result) == 3
    assert "id_copy" in result.columns
    assert result["status"].iloc[2] == "archived"
    assert result["id_copy"].tolist() == [1, 2, 3]


def test_get_subset_empty_dataframe() -> None:
    """Test get_subset with an empty DataFrame."""
    service = SubsetService()
    df = pd.DataFrame({"id": pd.Series([], dtype=int), "value": pd.Series([], dtype=str)})
    table_cfg = build_table_config(columns=["id", "value"])

    result = service.get_subset(source=df, table_cfg=table_cfg)

    assert len(result) == 0
    assert list(result.columns) == ["id", "value"]


def test_get_subset_with_drop_duplicates_as_dict() -> None:
    """Test get_subset with drop_duplicates as dict with columns."""
    service = SubsetService()
    df = pd.DataFrame({"id": [1, 1, 2], "value": [10, 10, 20]})
    table_cfg = build_table_config(
        columns=["id", "value"],
        drop_duplicates={"columns": ["id", "value"]},
    )

    result = service.get_subset(source=df, table_cfg=table_cfg)

    assert len(result) == 2
    assert result["id"].tolist() == [1, 2]


def test_get_subset_with_drop_duplicates_dict_and_fd_settings() -> None:
    """Test drop_duplicates dict with functional dependency settings."""
    service = SubsetService()
    df = pd.DataFrame({"id": [1, 1, 2], "value": [10, 10, 20]})
    table_cfg = build_table_config(
        columns=["id", "value"],
        drop_duplicates={
            "columns": ["id"],
            "check_functional_dependency": False,
            "strict_functional_dependency": False,
        },
    )

    result = service.get_subset(source=df, table_cfg=table_cfg)

    # Should drop duplicates by id column
    assert len(result) == 2
    # Verify that the FD settings are accessible
    assert table_cfg.check_functional_dependency is False
    assert table_cfg.strict_functional_dependency is False


# ============================================================================
# Interpolated String Tests (New Feature)
# ============================================================================


def test_get_subset_interpolated_string_simple() -> None:
    """Test simple interpolated string in extra_columns."""
    service = SubsetService()
    df = pd.DataFrame({"first": ["John", "Jane"], "last": ["Doe", "Smith"]})
    table_cfg = build_table_config(
        columns=["first", "last"],
        extra_columns={"fullname": "{first} {last}"}
    )

    result = service.get_subset(source=df, table_cfg=table_cfg)

    assert "fullname" in result.columns
    assert result["fullname"].tolist() == ["John Doe", "Jane Smith"]


def test_get_subset_interpolated_string_with_literals() -> None:
    """Test interpolated string mixed with literal text."""
    service = SubsetService()
    df = pd.DataFrame({"username": ["jdoe"], "domain": ["example.com"]})
    table_cfg = build_table_config(
        columns=["username"],
        extra_columns={"email": "{username}@example.com"}
    )

    result = service.get_subset(source=df, table_cfg=table_cfg)

    assert result["email"].iloc[0] == "jdoe@example.com"


def test_get_subset_interpolated_string_with_nulls() -> None:
    """Test interpolated string handles null values gracefully."""
    service = SubsetService()
    df = pd.DataFrame({"first": ["John", None], "last": [None, "Smith"]})
    table_cfg = build_table_config(
        columns=["first", "last"],
        extra_columns={"fullname": "{first} {last}"}
    )

    result = service.get_subset(source=df, table_cfg=table_cfg)

    assert result["fullname"].tolist() == ["John ", " Smith"]


def test_get_subset_interpolated_string_with_numbers() -> None:
    """Test interpolated string converts numbers to strings."""
    service = SubsetService()
    df = pd.DataFrame({"id": [1, 2], "code": ["A", "B"]})
    table_cfg = build_table_config(
        columns=["id", "code"],
        extra_columns={"label": "Item {id}-{code}"}
    )

    result = service.get_subset(source=df, table_cfg=table_cfg)

    assert result["label"].tolist() == ["Item 1-A", "Item 2-B"]


def test_get_subset_interpolated_string_with_escaping() -> None:
    """Test interpolated string handles escaped braces."""
    service = SubsetService()
    df = pd.DataFrame({"value": ["test"]})
    table_cfg = build_table_config(
        columns=["value"],
        extra_columns={"json": '{{\"key\": \"{value}\"}}'}
    )

    result = service.get_subset(source=df, table_cfg=table_cfg)

    assert result["json"].iloc[0] == '{"key": "test"}'


def test_get_subset_mixed_extra_columns() -> None:
    """Test mixing constants, copies, and interpolations."""
    service = SubsetService()
    df = pd.DataFrame({"a": [1], "b": [2]})
    table_cfg = build_table_config(
        columns=["a"],
        extra_columns={
            "const": 99,
            "copy": "b",
            "interp": "{a}-{b}"
        }
    )

    result = service.get_subset(source=df, table_cfg=table_cfg)

    assert result["const"].iloc[0] == 99
    assert result["copy"].iloc[0] == 2
    assert result["interp"].iloc[0] == "1-2"


def test_get_subset_interpolation_defers_missing_column() -> None:
    """Test that interpolation with missing column is deferred (not an error)."""
    service = SubsetService()
    df = pd.DataFrame({"a": [1]})
    table_cfg = build_table_config(
        columns=["a"],
        extra_columns={"bad": "{missing}"}
    )

    result = service.get_subset(source=df, table_cfg=table_cfg)
    
    # Column with missing dependency should be deferred (not added)
    assert "bad" not in result.columns
    # Source column should be present
    assert "a" in result.columns


def test_get_subset_defers_columns_with_missing_dependencies() -> None:
    """Test that columns with missing dependencies are silently deferred (logged but not added)."""
    service = SubsetService()
    df = pd.DataFrame({"first": ["John"], "last": ["Doe"]})
    table_cfg = build_table_config(
        columns=["first", "last"],
        extra_columns={
            "full_name": "{first} {last}",  # Can evaluate immediately
            "profile": "{first} - {missing_col}",  # Missing column - should defer
        }
    )

    result = service.get_subset(source=df, table_cfg=table_cfg)

    # full_name should be evaluated
    assert "full_name" in result.columns
    assert result["full_name"].iloc[0] == "John Doe"

    # profile should be deferred (missing column) - not added to result
    assert "profile" not in result.columns


def test_get_subset_evaluates_all_when_dependencies_present() -> None:
    """Test that all columns are evaluated when dependencies are present."""
    service = SubsetService()
    df = pd.DataFrame({"first": ["John"], "last": ["Doe"]})
    table_cfg = build_table_config(
        columns=["first", "last"],
        extra_columns={
            "full_name": "{first} {last}",
            "greeting": "Hello {first}",
        }
    )

    result = service.get_subset(source=df, table_cfg=table_cfg)

    # Both columns should be evaluated
    assert "full_name" in result.columns
    assert "greeting" in result.columns
    assert result["full_name"].iloc[0] == "John Doe"
    assert result["greeting"].iloc[0] == "Hello John"

