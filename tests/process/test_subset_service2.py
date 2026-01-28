# tests/process/test_subset_service2.py
# ChatGPT test file for SubsetService
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd
import pytest

from src.extract import SubsetService

# --- Minimal fakes for TableConfig / FK specs (keeps tests independent of your model layer) ---


@dataclass
class FakeFK:
    extra_columns: dict[str, Any] | None = None


@dataclass
class FakeTableConfig:
    keys_columns_and_fks: list[str]
    entity_name: str | None = "ent"
    unnest: bool = False
    unnest_columns: list[str] = field(default_factory=list)
    foreign_keys: list[FakeFK] = field(default_factory=list)

    extra_columns: dict[str, Any] | None = None
    drop_duplicates: bool | list[str] = False

    check_functional_dependency: bool = False
    strict_functional_dependency: bool = True

    drop_empty_rows: bool | list[str] | dict[str, Any] | None = False
    replacements: dict[str, Any] | None = None

    def is_drop_duplicate_dependent_on_unnesting(self) -> bool:
        return False


# --- Tests ---


def test_get_subset_columns_excludes_unnest_and_fk_extra_columns():
    svc = SubsetService()
    cfg = FakeTableConfig(
        keys_columns_and_fks=["id", "name", "unnested_col", "fk_extra"],
        unnest=True,
        unnest_columns=["unnested_col"],
        foreign_keys=[FakeFK(extra_columns={"fk_extra": "whatever"})],
    )

    cols = svc.get_subset_columns(cfg)  # type: ignore[arg-type]
    assert cols == ["id", "name"]


def test_get_subset2_extracts_columns_and_adds_extra_source_and_constant_columns():
    svc = SubsetService()
    df = pd.DataFrame(
        {
            "id": [1, 2],
            "name": ["a", "b"],
            "src": ["S1", "S2"],
            "other": [10, 20],
        }
    )

    out = svc.get_subset2(
        df,
        ["id", "name"],
        entity_name="X",
        extra_columns={"copied": "src", "const": 99},
        raise_if_missing=True,
    )

    assert list(out.columns) == ["id", "name", "copied", "const"]
    assert out["copied"].tolist() == ["S1", "S2"]
    assert out["const"].tolist() == [99, 99]


def test_get_subset2_raise_if_missing_true_raises():
    svc = SubsetService()
    df = pd.DataFrame({"id": [1], "name": ["a"]})

    with pytest.raises(ValueError, match="Columns not found"):
        svc.get_subset2(df, ["id", "missing"], entity_name="X", raise_if_missing=True)


def test_get_subset2_raise_if_missing_false_skips_missing_and_keeps_existing_columns(monkeypatch):
    svc = SubsetService()
    df = pd.DataFrame({"id": [1], "name": ["a"]})

    warnings: list[str] = []
    from loguru import logger as loguru_logger

    sink_id = loguru_logger.add(warnings.append, level="WARNING")
    try:
        out = svc.get_subset2(df, ["id", "missing"], entity_name="X", raise_if_missing=False)
    finally:
        loguru_logger.remove(sink_id)

    assert list(out.columns) == ["id"]  # missing skipped
    assert any("will be skipped" in m.lower() or "columns not found" in m.lower() for m in warnings)


def test_get_subset2_drop_empty_true_drops_rows_all_empty_after_subsetting():
    svc = SubsetService()
    df = pd.DataFrame(
        {
            "a": [None, 1, None],
            "b": [None, None, "x"],
            "c": [123, 456, 789],
        }
    )

    # Subset to only a/b, then drop rows where a/b are all empty => row 0 dropped
    out = svc.get_subset2(
        df,
        ["a", "b"],
        entity_name="X",
        drop_empty=True,
        raise_if_missing=True,
    ).reset_index(drop=True)

    expected = df.loc[[1, 2], ["a", "b"]].reset_index(drop=True)
    assert out.equals(expected)


def test_get_subset2_drop_empty_list_only_considers_listed_columns():
    svc = SubsetService()
    df = pd.DataFrame(
        {
            "a": [None, None, "x"],
            "b": [None, "keep", None],
            "c": [1, 2, 3],
        }
    )

    # Extract a,b,c but drop empties based only on a,b => row 0 dropped even though c=1
    out = svc.get_subset2(
        df,
        ["a", "b", "c"],
        entity_name="X",
        drop_empty=["a", "b"],
    )

    assert out.index.tolist() == [1, 2]


def test_get_subset2_replacements_mapping_applies_value_substitution():
    svc = SubsetService()
    df = pd.DataFrame({"a": ["DHDN Zone 3", "EPSG:4326"], "b": [1, 2]})

    out = svc.get_subset2(
        df,
        ["a", "b"],
        entity_name="X",
        replacements={"a": {"DHDN Zone 3": "EPSG:31467"}},
    )

    assert out["a"].tolist() == ["EPSG:31467", "EPSG:4326"]


def test_get_subset2_replacements_scalar_list_blanks_out_and_ffills_legacy_behavior():
    svc = SubsetService()
    df = pd.DataFrame({"a": ["ok", "BAD", None, "keep"], "b": [1, 2, 3, 4]})

    out = svc.get_subset2(
        df,
        ["a", "b"],
        entity_name="X",
        replacements={"a": ["BAD"]},  # blank out BAD then ffill
    )

    # "BAD" -> NA then forward-filled from previous "ok"
    assert out["a"].tolist() == ["ok", "ok", "ok", "keep"]


def test_get_subset2_drop_duplicates_true_drops_exact_duplicates(monkeypatch):
    svc = SubsetService()
    df = pd.DataFrame({"id": [1, 1, 2], "x": ["a", "a", "b"]})

    out = svc.get_subset2(
        df,
        ["id", "x"],
        entity_name="X",
        drop_duplicates=True,
    ).reset_index(drop=True)

    assert len(out) == 2
    assert out.equals(pd.DataFrame({"id": [1, 2], "x": ["a", "b"]}))


def test_get_subset2_drop_duplicates_list_drops_duplicates_on_subset(monkeypatch):
    svc = SubsetService()
    df = pd.DataFrame({"id": [1, 1, 1], "x": ["a", "a", "b"], "y": [10, 10, 20]})

    out = svc.get_subset2(
        df,
        ["id", "x", "y"],
        entity_name="X",
        drop_duplicates=["id", "x"],  # keep first per (id,x)
    )

    assert out.reset_index(drop=True).equals(pd.DataFrame({"id": [1, 1], "x": ["a", "b"], "y": [10, 20]}))


def test_get_subset_calls_get_subset2_with_config_values(monkeypatch):
    svc = SubsetService()
    df = pd.DataFrame({"id": [1, 1], "name": ["a", "a"], "src": ["S1", "S1"]})

    cfg = FakeTableConfig(
        keys_columns_and_fks=["id", "name"],
        entity_name="E",
        extra_columns={"copied": "src"},
        drop_duplicates=True,
        drop_empty_rows=False,
        replacements={"name": {"a": "A"}},
    )

    # Spy on get_subset2 to ensure it’s invoked; then run real method to validate output.
    called: dict[str, Any] = {}

    real = svc.get_subset2

    def spy(*args, **kwargs):
        called["args"] = args
        called["kwargs"] = kwargs
        return real(*args, **kwargs)

    monkeypatch.setattr(svc, "get_subset2", spy)

    out = svc.get_subset(df, cfg)  # type: ignore[arg-type]

    assert "kwargs" in called
    assert called["kwargs"]["entity_name"] == "E"
    assert called["kwargs"]["drop_duplicates"] is True
    assert called["kwargs"]["extra_columns"] == {"copied": "src"}
    assert out["name"].tolist() == ["A"]  # dedup + replacement
    assert out["copied"].tolist() == ["S1"]
