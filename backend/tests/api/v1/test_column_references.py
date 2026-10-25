"""HTTP contract tests for draft-aware column reference operations."""

import pytest

from backend.app.services import project_service, validation_service, yaml_service


@pytest.fixture(autouse=True)
def reset_column_reference_test_services():
    """Clear service singletons so API tests use each test's project directory."""
    project_service._project_service = None
    validation_service._validation_service = None
    yaml_service._yaml_service = None
    yield
    project_service._project_service = None
    validation_service._validation_service = None
    yaml_service._yaml_service = None


async def _create_project(client) -> None:
    """Create an authorized project through the project API."""
    response = await client.post(
        "/api/v1/projects",
        json={
            "name": "test_project",
            "data_provider_code": "test-provider",
            "provider_schema": "schema-one",
            "entities": {
                "site": {"type": "entity", "public_id": "site_id", "keys": ["saved_site"], "columns": ["saved_name"]},
                "child": {"type": "entity", "keys": ["child_id"], "columns": ["child_name"]},
            },
        },
    )
    assert response.status_code == 201, response.text


@pytest.mark.asyncio
async def test_reference_routes_use_draft_and_do_not_save_it(authorized_client) -> None:
    """Return draft-only values from both routes and preserve the saved entity."""
    await _create_project(authorized_client)
    draft = {"type": "entity", "keys": ["draft_b", "draft_a"], "columns": ["draft_name"]}

    complete_response = await authorized_client.post(
        "/api/v1/projects/test_project/entities/site/column-references/complete",
        json={
            "entity_draft": draft,
            "prefix": "@value: entities.site.",
            "edited_field_path": "entities.child.keys",
            "preferred_entity": "child",
        },
    )
    resolve_response = await authorized_client.post(
        "/api/v1/projects/test_project/entities/site/column-references/resolve",
        json={"entity_draft": draft, "directive": "@value: entities.site.keys"},
    )

    assert complete_response.status_code == 200, complete_response.text
    assert complete_response.json() == {"candidates": ["@value: entities.site.columns", "@value: entities.site.keys"]}
    assert resolve_response.status_code == 200, resolve_response.text
    assert resolve_response.json() == {
        "directive": "@value: entities.site.keys",
        "path": "entities.site.keys",
        "status": "resolved",
        "columns": ["draft_b", "draft_a"],
    }

    saved_entity = await authorized_client.get("/api/v1/projects/test_project/entities/site")
    assert saved_entity.status_code == 200, saved_entity.text
    assert saved_entity.json()["entity_data"]["keys"] == ["saved_site"]
    assert saved_entity.json()["entity_data"]["columns"] == ["saved_name"]


@pytest.mark.asyncio
async def test_reference_routes_replace_the_saved_entity_when_a_draft_renames_it(authorized_client) -> None:
    """Resolve and complete against the renamed draft without keeping the old saved entity."""
    await _create_project(authorized_client)
    draft = {"type": "entity", "keys": ["renamed_id"], "columns": ["renamed_name"]}

    resolve_response = await authorized_client.post(
        "/api/v1/projects/test_project/entities/renamed/column-references/resolve",
        json={
            "entity_draft": draft,
            "directive": "@value: entities.renamed.keys",
            "original_entity_name": "site",
        },
    )
    stale_response = await authorized_client.post(
        "/api/v1/projects/test_project/entities/renamed/column-references/resolve",
        json={
            "entity_draft": draft,
            "directive": "@value: entities.site.keys",
            "original_entity_name": "site",
        },
    )
    complete_response = await authorized_client.post(
        "/api/v1/projects/test_project/entities/renamed/column-references/complete",
        json={
            "entity_draft": draft,
            "prefix": "@value: entities.",
            "original_entity_name": "site",
        },
    )

    assert resolve_response.status_code == 200, resolve_response.text
    assert resolve_response.json()["columns"] == ["renamed_id"]
    assert stale_response.status_code == 200, stale_response.text
    assert stale_response.json()["reason_code"] == "missing_path"
    assert complete_response.status_code == 200, complete_response.text
    assert complete_response.json() == {"candidates": ["@value: entities.child.", "@value: entities.renamed."]}

    saved_entity = await authorized_client.get("/api/v1/projects/test_project/entities/site")
    assert saved_entity.status_code == 200, saved_entity.text
    assert saved_entity.json()["entity_data"]["keys"] == ["saved_site"]


@pytest.mark.asyncio
async def test_resolve_route_returns_typed_local_failure_and_missing_project_is_404(authorized_client) -> None:
    """Return bad references as typed results and keep project lookup concealed."""
    await _create_project(authorized_client)

    unresolved = await authorized_client.post(
        "/api/v1/projects/test_project/entities/site/column-references/resolve",
        json={"entity_draft": {"public_id": "site_id"}, "directive": "@value: entities.site.public_id"},
    )
    missing_project = await authorized_client.post(
        "/api/v1/projects/missing/entities/site/column-references/resolve",
        json={"entity_draft": {}, "directive": "@value: entities.site.keys"},
    )

    assert unresolved.status_code == 200, unresolved.text
    assert unresolved.json() == {
        "directive": "@value: entities.site.public_id",
        "path": "entities.site.public_id",
        "status": "unresolved",
        "reason_code": "wrong_result_type",
        "reason": "The reference must resolve to a list containing only column names.",
    }
    assert missing_project.status_code == 404


@pytest.mark.asyncio
async def test_reference_routes_publish_request_and_response_schemas(authorized_client) -> None:
    """Expose typed request and response models in the generated OpenAPI schema."""
    response = await authorized_client.get("/api/v1/openapi.json")

    assert response.status_code == 200, response.text
    schema = response.json()
    expected_models = {
        "/api/v1/projects/{project_name}/entities/{entity_name}/column-references/resolve": (
            "ColumnReferenceResolveRequest",
            "ColumnReferenceResolveResponse",
        ),
        "/api/v1/projects/{project_name}/entities/{entity_name}/column-references/complete": (
            "ColumnReferenceCompleteRequest",
            "ColumnReferenceCompleteResponse",
        ),
    }

    for path, (request_model, response_model) in expected_models.items():
        operation = schema["paths"][path]["post"]
        request_schema = operation["requestBody"]["content"]["application/json"]["schema"]["$ref"]
        response_schema = operation["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
        assert request_schema.endswith(f"/{request_model}")
        assert response_schema.endswith(f"/{response_model}")
