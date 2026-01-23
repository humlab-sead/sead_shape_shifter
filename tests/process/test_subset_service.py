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


# ========== Additional coverage: null source, get_subset_columns logic, etc. ==========


def test_get_subset_raises_when_source_is_none() -> None:
    """Test that source=None raises ValueError."""
    service = SubsetService()
    table_cfg = build_table_config(columns=["id"])

    with pytest.raises(ValueError, match="Source DataFrame must be provided"):
        service.get_subset(source=None, table_cfg=table_cfg)


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
