"""Tests for filter API endpoints."""

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_list_filter_types_returns_all_registered_filters():
    """GET /filters/types should return all registered filter schemas."""
    response = client.get("/api/v1/filters/types")

    assert response.status_code == 200
    data = response.json()

    # Should have both registered filters
    assert "query" in data
    assert "exists_in" in data

    # Verify query filter schema
    query_schema = data["query"]
    assert query_schema["key"] == "query"
    assert query_schema["display_name"] == "Pandas Query"
    assert query_schema["description"] == "Filter rows using Pandas query syntax"
    assert len(query_schema["fields"]) == 1

    query_field = query_schema["fields"][0]
    assert query_field["name"] == "query"
    assert query_field["type"] == "string"
    assert query_field["required"] is True
    assert query_field["placeholder"] == "column_name > 100"

    # Verify exists_in filter schema
    exists_in_schema = data["exists_in"]
    assert exists_in_schema["key"] == "exists_in"
    assert exists_in_schema["display_name"] == "Exists In"
    assert len(exists_in_schema["fields"]) == 4

    # Verify field metadata
    field_names = [f["name"] for f in exists_in_schema["fields"]]
    assert "other_entity" in field_names
    assert "column" in field_names
    assert "other_column" in field_names
    assert "drop_duplicates" in field_names

    # Check entity field has options_source
    entity_field = next(f for f in exists_in_schema["fields"] if f["name"] == "other_entity")
    assert entity_field["type"] == "entity"
    assert entity_field["required"] is True
    assert entity_field["options_source"] == "entities"


def test_filter_schemas_include_all_field_metadata():
    """Filter schemas should include complete field metadata."""
    response = client.get("/api/v1/filters/types")
    data = response.json()

    exists_in_schema = data["exists_in"]
    other_column_field = next(f for f in exists_in_schema["fields"] if f["name"] == "other_column")

    # Verify all metadata is present
    assert other_column_field["name"] == "other_column"
    assert other_column_field["type"] == "column"
    assert other_column_field["required"] is False
    assert other_column_field["description"] == "Column in other entity (defaults to same column name)"
    assert other_column_field["placeholder"] == "column_name"


def test_filter_types_endpoint_is_accessible():
    """Endpoint should be accessible without authentication."""
    response = client.get("/api/v1/filters/types")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"


def test_filter_schema_response_structure():
    """Response should match FilterSchemaResponse model."""
    response = client.get("/api/v1/filters/types")
    data = response.json()

    for schema in data.values():
        # Verify required keys
        assert "key" in schema
        assert "display_name" in schema
        assert "description" in schema
        assert "fields" in schema

        # Verify fields structure
        for field in schema["fields"]:
            assert "name" in field
            assert "type" in field
            assert "required" in field
            assert field["type"] in ["string", "boolean", "entity", "column"]
