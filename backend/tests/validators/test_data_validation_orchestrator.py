"""Tests for DataValidationOrchestrator and fetch strategies."""

from unittest.mock import AsyncMock, Mock

import pandas as pd
import pytest

from backend.app.services.shapeshift_service import ShapeShiftService
from backend.app.validators.data_validation_orchestrator import (
    DataValidationOrchestrator,
    PreviewDataFetchStrategy,
    TableStoreDataFetchStrategy,
)


@pytest.mark.asyncio
async def test_table_store_strategy_returns_existing_data():
    """Test TableStoreDataFetchStrategy returns data from provided table_store."""
    table_store = {
        "entity1": pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]}),
        "entity2": pd.DataFrame({"x": [7, 8], "y": [9, 10]}),
    }

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
    table_store = {
        "test_entity": pd.DataFrame({"col1": [1, 2], "col2": [3, 4]}),
    }

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
    table_store = {"entity": pd.DataFrame({"a": [1]})}

    # Inject TableStoreDataFetchStrategy
    strategy = TableStoreDataFetchStrategy(table_store)
    orchestrator = DataValidationOrchestrator(fetch_strategy=strategy)

    # Verify strategy was injected
    assert orchestrator.fetch_strategy is strategy
    assert isinstance(orchestrator.fetch_strategy, TableStoreDataFetchStrategy)
