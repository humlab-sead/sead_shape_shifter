"""Test entity preview with unlimited rows."""

import pandas as pd

from backend.app.services.shapeshift_service import PreviewResultBuilder
from src.model import TableConfig


def test_preview_with_limit():
    """Test preview with specified limit."""
    # Create test data
    df = pd.DataFrame({"id": range(100), "name": [f"Item {i}" for i in range(100)]})

    table_store = {"test_entity": df}
    cfg = {
        "test_entity": {
            "source": "test_table",
            "columns": ["id", "name"],
            "keys": ["id"],
        }
    }
    entity_cfg = TableConfig(entities_cfg=cfg, entity_name="test_entity")

    builder = PreviewResultBuilder()
    result = builder.build(entity_name="test_entity", entity_cfg=entity_cfg, table_store=table_store, limit=10, cache_hit=False)

    assert result.total_rows_in_preview == 10
    assert result.estimated_total_rows == 100
    assert len(result.rows) == 10


def test_preview_with_no_limit():
    """Test preview with no limit (all rows)."""
    # Create test data
    df = pd.DataFrame({"id": range(100), "name": [f"Item {i}" for i in range(100)]})

    table_store = {"test_entity": df}
    cfg = {
        "test_entity": {
            "source": "test_table",
            "columns": ["id", "name"],
            "keys": ["id"],
        }
    }
    entity_cfg = TableConfig(entities_cfg=cfg, entity_name="test_entity")

    builder = PreviewResultBuilder()
    result = builder.build(
        entity_name="test_entity", entity_cfg=entity_cfg, table_store=table_store, limit=None, cache_hit=False  # All rows
    )

    assert result.total_rows_in_preview == 100
    assert result.estimated_total_rows == 100
    assert len(result.rows) == 100


def test_preview_limit_larger_than_data():
    """Test preview when limit is larger than available data."""
    # Create test data
    df = pd.DataFrame({"id": range(10), "name": [f"Item {i}" for i in range(10)]})

    table_store = {"test_entity": df}
    cfg = {
        "test_entity": {
            "source": "test_table",
            "columns": ["id", "name"],
            "keys": ["id"],
        }
    }
    entity_cfg = TableConfig(entities_cfg=cfg, entity_name="test_entity")

    builder = PreviewResultBuilder()
    result = builder.build(
        entity_name="test_entity", entity_cfg=entity_cfg, table_store=table_store, limit=100, cache_hit=False  # Larger than data
    )

    assert result.total_rows_in_preview == 10
    assert result.estimated_total_rows == 10
    assert len(result.rows) == 10
