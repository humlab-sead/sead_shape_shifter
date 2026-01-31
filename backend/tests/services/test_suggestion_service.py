"""Tests for SuggestionService foreign key and dependency logic."""

from unittest.mock import AsyncMock

import pytest

from backend.app.models.data_source import ColumnMetadata, TableMetadata, TableSchema
from backend.app.core.config import settings
from backend.app.services.suggestion_service import SuggestionService


def build_schema(table_name: str, columns: list[ColumnMetadata]) -> TableSchema:
    """Helper to build a TableSchema."""
    return TableSchema(table_name=table_name, columns=columns, primary_keys=[c.name for c in columns if c.is_primary_key], **{})


@pytest.mark.asyncio
async def test_suggest_foreign_keys_with_schema_types() -> None:
    """High-confidence FK suggestion when names, types, and PK align."""
    settings.ENABLE_FK_SUGGESTIONS = True
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
    settings.ENABLE_FK_SUGGESTIONS = True
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
    settings.ENABLE_FK_SUGGESTIONS = True
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


@pytest.mark.asyncio
async def test_get_table_schemas_matches_tables_case_insensitive() -> None:
    """_get_table_schemas should load schemas for matching entities, respecting case-insensitive table names."""
    settings.ENABLE_FK_SUGGESTIONS = True
    schema_service = AsyncMock()
    schema_service.get_tables.return_value = [
        TableMetadata(name="users", schema_name="public", **{}),
        TableMetadata(name="Orders", schema_name=None, **{}),
    ]
    schema_service.get_table_schema.side_effect = lambda ds, table: build_schema(
        table,
        [ColumnMetadata(name="id", data_type="INTEGER", nullable=False, is_primary_key=True, **{})],
    )

    service = SuggestionService(schema_service=schema_service)
    entities = [{"name": "Users", "columns": ["id"]}, {"name": "orders", "columns": ["id"]}, {"name": "skipped", "columns": ["id"]}]

    schemas = await service._get_table_schemas("ds1", entities)  # pylint: disable=protected-access

    assert set(schemas.keys()) == {"Users", "orders"}
    assert schemas["Users"].table_name.lower() == "users"
    assert schema_service.get_table_schema.await_count == 2


@pytest.mark.asyncio
async def test_get_table_schemas_handles_listing_failure() -> None:
    """If table listing fails, no schemas are loaded."""
    settings.ENABLE_FK_SUGGESTIONS = True
    schema_service = AsyncMock()
    schema_service.get_tables.side_effect = Exception("boom")
    schema_service.get_table_schema = AsyncMock()

    service = SuggestionService(schema_service=schema_service)
    schemas = await service._get_table_schemas("ds1", [{"name": "users", "columns": ["id"]}])  # pylint: disable=protected-access

    assert schemas == {}
    assert schema_service.get_table_schema.await_count == 0


def test_find_column_matches_runs_all_strategies() -> None:
    """_find_column_matches should return results from all strategies."""
    settings.ENABLE_FK_SUGGESTIONS = True
    service = SuggestionService(schema_service=AsyncMock())

    matches = service._find_column_matches(  # pylint: disable=protected-access
        local_columns={"user_id", "users_id", "id"},
        remote_columns={"id", "user_id"},
        local_entity="orders",
        remote_entity="Users",
        schemas={},
    )

    match_types = {m["match_type"] for m in matches}
    assert {"exact", "fk_pattern", "entity_pattern"} <= match_types


@pytest.mark.asyncio
async def test_suggest_for_entity_respects_disable_fk_setting() -> None:
    """When FK suggestions are disabled, no FK/dependency suggestions are returned."""
    settings.ENABLE_FK_SUGGESTIONS = False
    service = SuggestionService(schema_service=AsyncMock())

    entity = {"name": "orders", "columns": ["order_id", "customer_id"]}
    all_entities = [entity, {"name": "customers", "columns": ["customer_id", "name"]}]

    result = await service.suggest_for_entity(entity, all_entities)

    assert result.foreign_key_suggestions == []
    assert result.dependency_suggestions == []
