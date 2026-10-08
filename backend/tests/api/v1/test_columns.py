"""Tests for column availability endpoints."""

import pytest

from backend.app.services import project_service, validation_service, yaml_service

_PROJECT_ENTITIES = {
    "parent": {
        "type": "entity",
        "public_id": "parent_id",
        "keys": ["parent_key"],
        "columns": ["parent_key", "source_value"],
        "extra_columns": {"derived_value": "source_value"},
    },
    "child": {
        "type": "entity",
        "public_id": "child_id",
        "keys": ["child_key"],
        "columns": ["child_key", "saved_value"],
    },
}


@pytest.fixture(autouse=True)
def reset_column_test_services():
    """Clear service singletons between API tests."""
    project_service._project_service = None
    validation_service._validation_service = None
    yaml_service._yaml_service = None
    yield
    project_service._project_service = None
    validation_service._validation_service = None
    yaml_service._yaml_service = None


async def _create_project(client) -> None:
    response = await client.post("/api/v1/projects", json={"name": "test_project", "entities": _PROJECT_ENTITIES})
    assert response.status_code == 201, response.text


@pytest.mark.asyncio
async def test_post_uses_unsaved_draft_and_returns_operation_and_stage_candidates(authorized_client) -> None:
    await _create_project(authorized_client)
    draft = {
        "type": "entity",
        "public_id": "child_id",
        "keys": ["child_key"],
        "columns": ["child_key", "draft_value", "amount"],
        "foreign_keys": [{"entity": "parent", "local_keys": ["child_key"], "remote_keys": ["parent_key"]}],
        "filters": [{"type": "exists_in", "stage": "after_link", "column": "draft_value"}],
        "unnest": {
            "id_vars": ["child_key"],
            "value_vars": ["amount"],
            "var_name": "measurement_type",
            "value_name": "measurement_value",
        },
    }

    response = await authorized_client.post(
        "/api/v1/projects/test_project/entities/child/column-availability",
        json={"entity_draft": draft, "source_columns": ["known_source"]},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert "draft_value" in body["columns"]
    assert "known_source" in body["columns"]
    assert "saved_value" not in body["columns"]
    for operation in ("business_keys", "replacements", "drop_duplicates", "drop_empty_rows"):
        assert isinstance(body[operation], list)
    assert "child_key" in body["business_keys"]
    assert "derived_value" in body["foreign_keys"][0]["remote_keys"]
    assert "system_id" in body["foreign_keys"][0]["extra_column_sources"]
    assert "amount" in body["foreign_keys"][0]["local_keys_before_unnest"]
    assert "amount" not in body["foreign_keys"][0]["local_keys_after_unnest"]
    assert "after_link" in body["filters"]
    assert "child_key" in body["unnest"]["id_vars"]
    assert "amount" in body["unnest"]["value_vars"]
    assert "value_id" not in body["unnest"]["value_vars"]

    saved_entity = await authorized_client.get("/api/v1/projects/test_project/entities/child")
    assert saved_entity.status_code == 200
    assert saved_entity.json()["entity_data"]["columns"] == ["child_key", "saved_value"]


@pytest.mark.asyncio
async def test_post_returns_404_for_missing_project(authorized_client) -> None:
    response = await authorized_client.post(
        "/api/v1/projects/missing/entities/child/column-availability",
        json={"entity_draft": {"type": "entity", "columns": ["value"]}},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_legacy_get_keeps_flat_response_contract(authorized_client) -> None:
    await _create_project(authorized_client)

    response = await authorized_client.get(
        "/api/v1/projects/test_project/entities/child/columns",
        params={"remote_entity": "parent"},
    )

    assert response.status_code == 200
    assert set(response.json()) == {"local_columns", "remote_columns"}
