"""Tests for DataValidationOrchestrator and fetch strategies."""

from unittest.mock import AsyncMock, Mock, patch

import pandas as pd
import pytest

from backend.app.services.shapeshift_service import ShapeShiftService
from backend.app.validators.data_validation_orchestrator import (
    DataValidationOrchestrator,
    FullDataFetchStrategy,
    PreviewDataFetchStrategy,
    TableStoreDataFetchStrategy,
)
from src.model import ShapeShiftProject
from src.normalizer import ShapeShifter
from src.table_store import TableStore
from src.validators.data_validators import UnresolvedExtraColumnsValidator, ValidationIssue


@pytest.mark.asyncio
async def test_table_store_strategy_returns_existing_data():
    """Test TableStoreDataFetchStrategy returns data from provided table_store."""
    table_store: TableStore = TableStore(
        {
            "entity1": pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]}),
            "entity2": pd.DataFrame({"x": [7, 8], "y": [9, 10]}),
        }
    )

    strategy = TableStoreDataFetchStrategy(table_store)

    # Test fetching existing entity
    df = await strategy.fetch("any_project", "entity1")
    assert len(df) == 3
    assert list(df.columns) == ["a", "b"]

    # Test fetching another entity
    df2 = await strategy.fetch("any_project", "entity2")
    assert len(df2) == 2
    assert list(df2.columns) == ["x", "y"]

    # Test fetching non-existent entity returns empty DataFrame
    df3 = await strategy.fetch("any_project", "missing")
    assert df3.empty


@pytest.mark.asyncio
async def test_orchestrator_with_table_store_strategy():
    """Test orchestrator with TableStoreDataFetchStrategy injected."""
    # Pre-existing table store
    table_store = TableStore(
        {
            "test_entity": pd.DataFrame({"col1": [1, 2], "col2": [3, 4]}),
        }
    )

    # Mock core project
    mock_core_project = Mock()
    mock_core_project.cfg.get.return_value = {
        "test_entity": {
            "columns": ["col1", "col2"],
            "keys": ["col1"],
        }
    }

    # Inject TableStoreDataFetchStrategy
    strategy = TableStoreDataFetchStrategy(table_store)
    orchestrator = DataValidationOrchestrator(fetch_strategy=strategy)

    # Validate entities
    issues = await orchestrator.validate_all_entities(
        core_project=mock_core_project,
        project_name="test_project",
        entity_names=["test_entity"],
    )

    # Should return domain ValidationIssues (not API models)
    assert isinstance(issues, list)


@pytest.mark.asyncio
async def test_preview_strategy_fetches_from_service():
    """Test PreviewDataFetchStrategy uses preview service."""
    mock_service = Mock(spec=ShapeShiftService)
    mock_result = Mock()
    mock_result.rows = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
    mock_service.preview_entity = AsyncMock(return_value=mock_result)

    strategy = PreviewDataFetchStrategy(mock_service, limit=100)

    df = await strategy.fetch("test_project", "test_entity")

    # Verify service was called correctly
    mock_service.preview_entity.assert_called_once_with(
        project_name="test_project",
        entity_name="test_entity",
        limit=100,
    )

    # Verify DataFrame was created from rows
    assert len(df) == 2
    assert list(df.columns) == ["a", "b"]


@pytest.mark.asyncio
async def test_preview_strategy_handles_empty_results():
    """Test PreviewDataFetchStrategy returns empty DataFrame when no rows."""
    mock_service = Mock(spec=ShapeShiftService)
    mock_result = Mock()
    mock_result.rows = []
    mock_service.preview_entity = AsyncMock(return_value=mock_result)

    strategy = PreviewDataFetchStrategy(mock_service)

    df = await strategy.fetch("test_project", "test_entity")

    assert df.empty


def test_orchestrator_with_injected_strategy():
    """Test orchestrator accepts injected fetch strategy."""
    table_store = TableStore(
        {
            "entity": pd.DataFrame({"a": [1]}),
        }
    )

    # Inject TableStoreDataFetchStrategy
    strategy = TableStoreDataFetchStrategy(table_store)
    orchestrator = DataValidationOrchestrator(fetch_strategy=strategy)

    # Verify strategy was injected
    assert orchestrator.fetch_strategy is strategy
    assert isinstance(orchestrator.fetch_strategy, TableStoreDataFetchStrategy)


@pytest.mark.asyncio
async def test_orchestrator_surfaces_unresolved_extra_columns_in_full_data_mode():
    """Full-data validation should report unresolved deferred extra_columns as structured issues."""
    core_project = ShapeShiftProject(
        cfg={
            "entities": {
                "sample": {
                    "type": "fixed",
                    "public_id": "sample_id",
                    "keys": ["sample_name"],
                    "columns": ["sample_name"],
                    "values": [["Soil"]],
                    "extra_columns": {
                        "sample_label": "=concat(sample_name, ' / ', country_name)",
                    },
                }
            }
        }
    )

    mock_project_service = Mock()
    mock_project_service.load_project.return_value = Mock()

    with patch("backend.app.validators.data_validation_orchestrator.ProjectMapper.to_core", return_value=core_project):
        strategy = FullDataFetchStrategy(mock_project_service)
        orchestrator = DataValidationOrchestrator(fetch_strategy=strategy)

        issues = await orchestrator.validate_all_entities(
            core_project=core_project,
            project_name="test_project",
            entity_names=["sample"],
        )

    unresolved_issues = [issue for issue in issues if issue.code == "EXTRA_COLUMN_UNRESOLVED"]

    assert len(unresolved_issues) == 1
    assert unresolved_issues[0].entity == "sample"
    assert unresolved_issues[0].field == "extra_columns.sample_label"
    assert "Entity 'sample', field 'extra_columns.sample_label':" in unresolved_issues[0].message
    assert "country_name" in unresolved_issues[0].message
    assert "=concat(sample_name, ' / ', country_name)" in unresolved_issues[0].message


@pytest.mark.asyncio
async def test_full_data_validation_with_unresolved_extra_columns():
    """Test full data validation detects unresolved extra_columns.

    This test verifies that the validation system correctly identifies
    extra_columns that reference non-existent columns after normalization.
    """
    # Create a minimal test project with intentionally unresolved extra_columns
    test_config: dict = {
        "metadata": {"name": "test_unresolved", "description": "Test unresolved extra columns"},
        "options": {"data_sources": {}},
        "entities": {
            "test_entity": {
                "type": "fixed",
                "columns": ["col_a", "col_b"],
                "values": [[1, 2], [3, 4]],
                "keys": ["col_a"],
                "public_id": "test_entity_id",
                "extra_columns": {
                    "valid_concat": "=concat(col_a, col_b)",  # Should resolve
                    "invalid_ref": "nonexistent_column",  # Should NOT resolve
                    "invalid_formula": "=upper(missing_col)",  # Should NOT resolve
                },
            }
        },
    }

    project = ShapeShiftProject(cfg=test_config)

    # Run full normalization
    normalizer = ShapeShifter(project)
    await normalizer.normalize()

    # Verify unresolved extra columns were tracked
    assert "test_entity" in normalizer.unresolved_extra_columns, "Should track unresolved extra columns"
    unresolved = normalizer.unresolved_extra_columns["test_entity"]

    print(f"\nUnresolved extra columns: {unresolved}")

    # Verify that the problematic extra_columns are in the unresolved set
    # Note: 'invalid_ref' referring to a plain column name may be handled differently than formulas
    assert len(unresolved) >= 1, f"Expected at least 1 unresolved extra column, found {len(unresolved)}"

    # Create a custom strategy that includes unresolved extra column issues
    class TestDataFetchStrategy(TableStoreDataFetchStrategy):
        """Custom strategy that includes unresolved extra column validation."""

        def __init__(self, table_store: TableStore, unresolved_map: dict[str, dict[str, dict]]) -> None:
            super().__init__(table_store)
            self.unresolved_map = unresolved_map

        async def get_additional_issues(self, project_name: str, entity_name: str) -> list[ValidationIssue]:
            """Return unresolved extra column issues."""

            unresolved_extra_columns = self.unresolved_map.get(entity_name, {})
            return UnresolvedExtraColumnsValidator.validate(unresolved_extra_columns, entity_name)

    # Create validation strategy with unresolved tracking
    strategy = TestDataFetchStrategy(
        table_store=normalizer.table_store,
        unresolved_map=normalizer.unresolved_extra_columns,
    )
    orchestrator = DataValidationOrchestrator(fetch_strategy=strategy)

    # Run validation
    issues: list[ValidationIssue] = await orchestrator.validate_all_entities(
        core_project=project,
        project_name="test_unresolved",
        entity_names=["test_entity"],
    )

    # Print validation issues for debugging
    print(f"\nFound {len(issues)} validation issues:")
    for issue in issues:
        print(f"  - {issue.severity} [{issue.code}] {issue.entity}.{issue.field}: {issue.message}")

    # Verify that unresolved extra column errors were detected
    unresolved_errors = [issue for issue in issues if issue.code == "EXTRA_COLUMN_UNRESOLVED"]

    assert len(unresolved_errors) >= 1, f"Expected unresolved extra column errors, found {len(unresolved_errors)}"

    # Verify error details mention the problematic extra columns
    error_messages = " ".join(issue.message for issue in unresolved_errors)
    assert (
        "invalid_" in error_messages.lower() or "missing" in error_messages.lower()
    ), f"Expected errors to mention missing columns, got: {error_messages}"
