"""Unit tests for src.transforms.branch.process_merged_branch."""

from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd
import pytest

from src.transforms.branch import process_merged_branch


def make_table_cfg(branches: list[dict], entities_cfg: dict | None = None) -> Mock:
    """Minimal stand-in for TableConfig — only the attributes process_merged_branch reads."""
    return Mock(branches=branches, entities_cfg=entities_cfg or {})


def make_sub_table_cfg(branch_name: str, source: str) -> Mock:
    """Minimal stand-in for a branch sub-TableConfig."""
    return Mock(entity_cfg={"_branch_name": branch_name, "source": source})


# ---------------------------------------------------------------------------
# Discriminator column
# ---------------------------------------------------------------------------


def test_adds_discriminator_column():
    table_cfg = make_table_cfg(branches=[{"source": "src_a"}], entities_cfg={"src_a": {"public_id": "src_a_id"}})
    sub_cfg = make_sub_table_cfg(branch_name="branch_a", source="src_a")
    data = pd.DataFrame({"system_id": [1, 2], "value": ["x", "y"]})

    result = process_merged_branch("my_entity", table_cfg, sub_cfg, data)

    assert "my_entity_branch" in result.columns
    assert list(result["my_entity_branch"]) == ["branch_a", "branch_a"]


def test_discriminator_column_name_uses_entity_argument():
    table_cfg = make_table_cfg(branches=[{"source": "src"}], entities_cfg={"src": {"public_id": "src_id"}})
    sub_cfg = make_sub_table_cfg(branch_name="b", source="src")
    data = pd.DataFrame({"system_id": [1]})

    result = process_merged_branch("analysis_entity", table_cfg, sub_cfg, data)

    assert "analysis_entity_branch" in result.columns


# ---------------------------------------------------------------------------
# FK columns — active branch
# ---------------------------------------------------------------------------


def test_active_branch_fk_populated_from_system_id():
    table_cfg = make_table_cfg(
        branches=[{"source": "src_a"}, {"source": "src_b"}],
        entities_cfg={"src_a": {"public_id": "src_a_id"}, "src_b": {"public_id": "src_b_id"}},
    )
    sub_cfg = make_sub_table_cfg(branch_name="branch_a", source="src_a")
    data = pd.DataFrame({"system_id": [10, 20]})

    result = process_merged_branch("entity", table_cfg, sub_cfg, data)

    assert list(result["src_a_id"]) == [10, 20]
    assert result["src_a_id"].dtype == "Int64"


def test_inactive_branch_fk_is_na():
    table_cfg = make_table_cfg(
        branches=[{"source": "src_a"}, {"source": "src_b"}],
        entities_cfg={"src_a": {"public_id": "src_a_id"}, "src_b": {"public_id": "src_b_id"}},
    )
    sub_cfg = make_sub_table_cfg(branch_name="branch_a", source="src_a")
    data = pd.DataFrame({"system_id": [10, 20]})

    result = process_merged_branch("entity", table_cfg, sub_cfg, data)

    assert result["src_b_id"].isna().all()
    assert result["src_b_id"].dtype == "Int64"


def test_fk_fallback_to_na_array_when_system_id_missing():
    table_cfg = make_table_cfg(branches=[{"source": "src_a"}], entities_cfg={"src_a": {"public_id": "src_a_id"}})
    sub_cfg = make_sub_table_cfg(branch_name="branch_a", source="src_a")
    data = pd.DataFrame({"value": ["x", "y"]})  # no system_id

    result = process_merged_branch("entity", table_cfg, sub_cfg, data)

    assert result["src_a_id"].isna().all()
    assert result["src_a_id"].dtype == "Int64"


# ---------------------------------------------------------------------------
# FK column naming
# ---------------------------------------------------------------------------


def test_fk_column_name_uses_source_public_id():
    table_cfg = make_table_cfg(branches=[{"source": "src_a"}], entities_cfg={"src_a": {"public_id": "my_custom_id"}})
    sub_cfg = make_sub_table_cfg(branch_name="branch_a", source="src_a")
    data = pd.DataFrame({"system_id": [1]})

    result = process_merged_branch("entity", table_cfg, sub_cfg, data)

    assert "my_custom_id" in result.columns


def test_fk_column_name_falls_back_to_source_id_suffix_when_no_public_id():
    table_cfg = make_table_cfg(branches=[{"source": "src_a"}], entities_cfg={"src_a": {}})
    sub_cfg = make_sub_table_cfg(branch_name="branch_a", source="src_a")
    data = pd.DataFrame({"system_id": [1]})

    result = process_merged_branch("entity", table_cfg, sub_cfg, data)

    assert "src_a_id" in result.columns


def test_fk_column_name_falls_back_when_source_not_in_entities_cfg():
    table_cfg = make_table_cfg(branches=[{"source": "unknown_src"}], entities_cfg={})
    sub_cfg = make_sub_table_cfg(branch_name="branch_a", source="unknown_src")
    data = pd.DataFrame({"system_id": [1]})

    result = process_merged_branch("entity", table_cfg, sub_cfg, data)

    assert "unknown_src_id" in result.columns


# ---------------------------------------------------------------------------
# system_id cleanup
# ---------------------------------------------------------------------------


def test_system_id_is_dropped_from_result():
    table_cfg = make_table_cfg(branches=[{"source": "src"}], entities_cfg={"src": {"public_id": "src_id"}})
    sub_cfg = make_sub_table_cfg(branch_name="branch_a", source="src")
    data = pd.DataFrame({"system_id": [1, 2], "col": ["a", "b"]})

    result = process_merged_branch("entity", table_cfg, sub_cfg, data)

    assert "system_id" not in result.columns


def test_no_error_when_system_id_absent():
    table_cfg = make_table_cfg(branches=[{"source": "src"}], entities_cfg={"src": {"public_id": "src_id"}})
    sub_cfg = make_sub_table_cfg(branch_name="branch_a", source="src")
    data = pd.DataFrame({"col": ["a", "b"]})

    result = process_merged_branch("entity", table_cfg, sub_cfg, data)

    assert "system_id" not in result.columns
