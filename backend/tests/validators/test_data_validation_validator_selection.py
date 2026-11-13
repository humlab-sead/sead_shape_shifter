"""Tests for selecting which data checks a validation run performs."""

import pandas as pd
import pytest

from backend.app.validators.data_validation_orchestrator import (
    DataValidationOrchestrator,
    TableStoreDataFetchStrategy,
)
from src.model import ShapeShiftProject
from src.table_store import TableStore

SELECTABLE_CODES: frozenset[str] = frozenset({"COLUMN_NOT_FOUND", "NON_UNIQUE_KEYS"})
"""Selectable-check issue codes this duplicate-key fixture produces."""


def _core_project() -> ShapeShiftProject:
    """Build a project with one entity that trips all three selectable checks."""
    return ShapeShiftProject(
        cfg={
            "entities": {
                "orders": {
                    "columns": ["order_code", "missing_column"],
                    "keys": ["order_code"],
                }
            }
        }
    )


def _table_store() -> TableStore:
    """Return duplicate business keys so the uniqueness check has something to report."""
    return TableStore({"orders": pd.DataFrame({"order_code": ["A", "A"]})})


async def _run(validators: list[str] | None) -> set[str]:
    """Run validation for one entity and return its issue codes."""
    orchestrator = DataValidationOrchestrator(fetch_strategy=TableStoreDataFetchStrategy(_table_store()))
    issues = await orchestrator.validate_all_entities(
        core_project=_core_project(),
        project_name="test_project",
        entity_names=["orders"],
        validators=validators,
    )
    return {issue.code for issue in issues}


@pytest.mark.asyncio
async def test_omitted_selection_runs_every_selectable_check():
    """A request that names no checks keeps the previous behaviour."""
    codes = await _run(None)

    assert SELECTABLE_CODES.issubset(codes)


@pytest.mark.asyncio
async def test_unselected_column_check_does_not_run():
    """Leaving the column check out suppresses only its issues."""
    codes = await _run(["natural_key_uniqueness", "non_empty_result"])

    assert "COLUMN_NOT_FOUND" not in codes
    assert "NON_UNIQUE_KEYS" in codes


@pytest.mark.asyncio
async def test_unselected_uniqueness_check_does_not_run():
    """Leaving the uniqueness check out suppresses only its issues."""
    codes = await _run(["column_exists", "non_empty_result"])

    assert "NON_UNIQUE_KEYS" not in codes
    assert "COLUMN_NOT_FOUND" in codes


@pytest.mark.asyncio
async def test_empty_selection_runs_none_of_the_selectable_checks():
    """An explicit empty selection runs no selectable check."""
    codes = await _run([])

    assert not SELECTABLE_CODES & codes


@pytest.mark.asyncio
async def test_unselected_empty_result_check_stops_the_warning_for_an_empty_entity():
    """Switching off the empty-result check removes the warning for an entity with no data."""
    orchestrator = DataValidationOrchestrator(fetch_strategy=TableStoreDataFetchStrategy(TableStore({"orders": pd.DataFrame()})))

    enabled = await orchestrator.validate_all_entities(
        core_project=ShapeShiftProject(cfg={"entities": {"orders": {"columns": ["order_code"]}}}),
        project_name="test_project",
        entity_names=["orders"],
    )
    orchestrator = DataValidationOrchestrator(fetch_strategy=TableStoreDataFetchStrategy(TableStore({"orders": pd.DataFrame()})))
    disabled = await orchestrator.validate_all_entities(
        core_project=ShapeShiftProject(cfg={"entities": {"orders": {"columns": ["order_code"]}}}),
        project_name="test_project",
        entity_names=["orders"],
        validators=["column_exists", "natural_key_uniqueness"],
    )

    assert [issue.code for issue in enabled] == ["EMPTY_RESULT"]
    assert disabled == []
