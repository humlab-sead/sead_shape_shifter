#!/usr/bin/env python3
"""Quick test of suggestion service logic without API."""

import asyncio

from backend.app.services.suggestion_service import SuggestionService

# pylint: disable=unused-argument


# Mock schema service for testing
class MockSchemaService:
    async def list_tables(self, data_source_name):
        return []

    async def get_table_schema(self, data_source_name, table_name):
        raise Exception("Not implemented")  # pylint: disable=broad-exception-raised


async def test_suggestions():
    """Test suggestion logic without database."""
    service = SuggestionService(MockSchemaService())  # type: ignore

    entities = [
        {"name": "users", "columns": ["user_id", "username", "email"]},
        {"name": "orders", "columns": ["order_id", "user_id", "total"]},
        {"name": "products", "columns": ["product_id", "product_name"]},
        {"name": "order_items", "columns": ["item_id", "order_id", "product_id", "quantity"]},
    ]

    print("Testing suggestion service...")

    for entity in entities:
        print(f"\nAnalyzing: {entity['name']}")
        result = await service.suggest_for_entity(entity=entity, all_entities=entities, data_source_name=None)  # No DB introspection

        print(f"  FK suggestions: {len(result.foreign_key_suggestions)}")
        for fk in result.foreign_key_suggestions:
            print(f"    - {fk.local_keys} → {fk.remote_entity}.{fk.remote_keys} (confidence: {fk.confidence:.2f})")
            print(f"      Reason: {fk.reason}")

        print(f"  Dependencies: {len(result.dependency_suggestions)}")
        for dep in result.dependency_suggestions:
            print(f"    - Depends on: {dep.entity} (confidence: {dep.confidence:.2f})")


if __name__ == "__main__":
    asyncio.run(test_suggestions())
