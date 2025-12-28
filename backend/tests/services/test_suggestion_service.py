"""Tests for SuggestionService foreign key and dependency logic."""

from unittest.mock import AsyncMock

import pytest

from backend.app.models.data_source import ColumnMetadata, TableSchema
from backend.app.services.suggestion_service import SuggestionService


def build_schema(table_name: str, columns: list[ColumnMetadata]) -> TableSchema:
    """Helper to build a TableSchema."""
    return TableSchema(table_name=table_name, columns=columns, primary_keys=[c.name for c in columns if c.is_primary_key], **{})


@pytest.mark.asyncio
async def test_suggest_foreign_keys_with_schema_types() -> None:
    """High-confidence FK suggestion when names, types, and PK align."""
    service = SuggestionService(schema_service=AsyncMock())

    entity = {"name": "orders", "columns": ["order_id", "customer_id"]}
    all_entities = [entity, {"name": "customers", "columns": ["customer_id", "name"]}]

    schemas = {
        "orders": build_schema(
            "orders",
            [
                ColumnMetadata(name="order_id", data_type="INTEGER", nullable=False, is_primary_key=True, **{}),
                ColumnMetadata(name="customer_id", data_type="INTEGER", nullable=False, is_primary_key=False, **{}),
            ],
        ),
        "customers": build_schema(
            "customers",
            [ColumnMetadata(name="customer_id", data_type="INTEGER", nullable=False, is_primary_key=True, **{})],
        ),
    }

    suggestions = await service.suggest_foreign_keys(entity, all_entities, schemas)

    assert len(suggestions) >= 1
    top_suggestion = suggestions[0]
    assert top_suggestion.remote_entity == "customers"
    assert top_suggestion.local_keys == ["customer_id"]
    assert top_suggestion.remote_keys == ["customer_id"]
    assert top_suggestion.confidence >= 0.8  # base exact + integer + PK bonus
    assert "[references primary key]" in top_suggestion.reason

    deps = service._infer_dependencies_from_foreign_keys(suggestions)  # pylint: disable=protected-access
    assert len(deps) == 1
    assert deps[0].entity == "customers"


@pytest.mark.asyncio
async def test_suggest_for_entity_handles_schema_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """Schema loading failures fall back to column-based suggestions."""
    service = SuggestionService(schema_service=AsyncMock())
    monkeypatch.setattr(service, "_get_table_schemas", AsyncMock(side_effect=Exception("boom")))

    entity = {"name": "orders", "columns": ["order_id", "customer_id"]}
    all_entities = [entity, {"name": "customers", "columns": ["customer_id", "name"]}]

    result = await service.suggest_for_entity(entity, all_entities, data_source_name="ds1")

    assert len(result.foreign_key_suggestions) == 1  # exact column name match despite schema failure
    assert result.foreign_key_suggestions[0].remote_entity == "customers"
    assert result.dependency_suggestions == []  # confidence threshold not met for dependencies


@pytest.mark.asyncio
async def test_suggest_foreign_keys_string_type_compatibility() -> None:
    """String type compatibility boosts confidence above threshold."""
    service = SuggestionService(schema_service=AsyncMock())

    entity = {"name": "users", "columns": ["email", "user_id"]}
    all_entities = [entity, {"name": "subscribers", "columns": ["email", "subscriber_id"]}]

    schemas = {
        "users": build_schema(
            "users",
            [ColumnMetadata(name="email", data_type="varchar(50)", nullable=False, is_primary_key=False, **{})],
        ),
        "subscribers": build_schema(
            "subscribers",
            [ColumnMetadata(name="email", data_type="text", nullable=False, is_primary_key=False, **{})],
        ),
    }

    suggestions = await service.suggest_foreign_keys(entity, all_entities, schemas)

    assert len(suggestions) == 1
    suggestion = suggestions[0]
    assert suggestion.remote_entity == "subscribers"
    assert suggestion.local_keys == ["email"]
    assert suggestion.remote_keys == ["email"]
    assert suggestion.confidence > 0.5  # base exact + compatible string types
    assert "compatible types" in suggestion.reason
