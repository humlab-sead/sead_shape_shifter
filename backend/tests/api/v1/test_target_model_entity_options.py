"""Tests for the project target-model entity options route."""

import pytest
import yaml

from backend.app.core.config import settings
from backend.app.services import project_service, yaml_service


@pytest.fixture
def reset_services(monkeypatch):
    """Reset services that retain project paths between requests."""
    monkeypatch.setattr(project_service, "_project_service", None)
    monkeypatch.setattr(yaml_service, "_yaml_service", None)


def _target_model() -> dict:
    return {
        "model": {"name": "Test Model", "version": "1"},
        "entities": {
            "required_target": {
                "role": "fact",
                "required": True,
                "description": "Required target entity",
                "target_table": "target_table",
                "public_id": "target_id",
                "columns": {
                    "generated_key": {"required": True, "generated": True},
                    "source_name": {"required": True},
                },
                "foreign_keys": [
                    {"entity": "parent", "required": True},
                    {"entity": "destination", "via": "bridge", "required": True},
                ],
            },
            "already_present": {},
            "bridge": {"public_id": "bridge_id"},
            "destination": {"public_id": "destination_id"},
            "parent": {"public_id": "parent_id"},
            "trigger": {
                "public_id": "trigger_id",
                "foreign_keys": [{"entity": "destination", "required_when": {"has_new_rows": "trigger"}}],
            },
        },
    }


async def _create_project(client) -> None:
    response = await client.post(
        "/api/v1/projects",
        json={
            "name": "test_project",
            "data_provider_code": "test-provider",
            "provider_schema": "schema-one",
            "entities": {"already_present": {}},
        },
    )
    assert response.status_code == 201, response.text


async def _configure_model(client, projects_dir, target_models_dir, model_location: str) -> None:
    target_model = _target_model()
    if model_location == "local":
        (projects_dir / "test_project" / "target-model.yml").write_text(
            yaml.safe_dump(target_model, sort_keys=False),
            encoding="utf-8",
        )
        response = await client.patch(
            "/api/v1/projects/test_project/metadata",
            json={"target_model": "@load: target-model.yml"},
        )
        assert response.status_code == 200, response.text
    elif model_location == "shared":
        target_models_dir.mkdir(parents=True)
        (target_models_dir / "target-model.yml").write_text(
            yaml.safe_dump(target_model, sort_keys=False),
            encoding="utf-8",
        )
        response = await client.patch(
            "/api/v1/projects/test_project/metadata",
            json={"target_model": "@load: ${GLOBAL_TARGET_MODEL_DIR}/target-model.yml"},
        )
        assert response.status_code == 200, response.text
    else:
        raw_response = await client.get("/api/v1/projects/test_project/raw-yaml")
        assert raw_response.status_code == 200, raw_response.text
        project_yaml = yaml.safe_load(raw_response.json()["yaml_content"])
        project_yaml["metadata"]["target_model"] = target_model
        response = await client.put(
            "/api/v1/projects/test_project/raw-yaml",
            json={"yaml_content": yaml.safe_dump(project_yaml, sort_keys=False)},
        )
        assert response.status_code == 200, response.text


@pytest.mark.parametrize("model_location", ["local", "shared", "inline"])
async def test_returns_target_options_without_changing_project_yaml(
    tmp_path,
    monkeypatch,
    reset_services,
    authorized_client,
    model_location: str,
) -> None:
    projects_dir = tmp_path / "projects"
    target_models_dir = tmp_path / "shared" / "target-models"
    monkeypatch.setattr(settings, "PROJECTS_DIR", projects_dir)
    monkeypatch.setattr(settings, "GLOBAL_TARGET_MODEL_DIR", target_models_dir)
    await _create_project(authorized_client)
    await _configure_model(authorized_client, projects_dir, target_models_dir, model_location)
    original_yaml = await authorized_client.get("/api/v1/projects/test_project/raw-yaml")

    response = await authorized_client.get("/api/v1/projects/test_project/target-model-entities")
    after_yaml = await authorized_client.get("/api/v1/projects/test_project/raw-yaml")

    assert response.status_code == 200, response.text
    assert response.json() == {
        "configured": True,
        "entities": [
            {
                "name": "required_target",
                "role": "fact",
                "required": True,
                "description": "Required target entity",
                "target_table": "target_table",
                "public_id": "target_id",
                "required_columns": ["source_name"],
                "required_links": [
                    {
                        "path": ["bridge", "destination"],
                        "missing_entities": ["bridge", "destination"],
                        "required_when_has_new_rows": None,
                    },
                    {
                        "path": ["parent"],
                        "missing_entities": ["parent"],
                        "required_when_has_new_rows": None,
                    },
                ],
            },
            {
                "name": "bridge",
                "role": None,
                "required": False,
                "description": None,
                "target_table": None,
                "public_id": "bridge_id",
                "required_columns": [],
                "required_links": [],
            },
            {
                "name": "destination",
                "role": None,
                "required": False,
                "description": None,
                "target_table": None,
                "public_id": "destination_id",
                "required_columns": [],
                "required_links": [],
            },
            {
                "name": "parent",
                "role": None,
                "required": False,
                "description": None,
                "target_table": None,
                "public_id": "parent_id",
                "required_columns": [],
                "required_links": [],
            },
            {
                "name": "trigger",
                "role": None,
                "required": False,
                "description": None,
                "target_table": None,
                "public_id": "trigger_id",
                "required_columns": [],
                "required_links": [
                    {
                        "path": ["destination"],
                        "missing_entities": ["destination"],
                        "required_when_has_new_rows": "trigger",
                    },
                ],
            },
        ],
    }
    assert "columns" not in response.json()
    assert "foreign_keys" not in response.json()
    assert "keys" not in response.json()
    assert original_yaml.json() == after_yaml.json()


async def test_returns_unconfigured_state_when_project_has_no_target_model(
    tmp_path,
    monkeypatch,
    reset_services,
    authorized_client,
) -> None:
    monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path / "projects")
    await _create_project(authorized_client)

    response = await authorized_client.get("/api/v1/projects/test_project/target-model-entities")

    assert response.status_code == 200
    assert response.json() == {"configured": False, "entities": []}


@pytest.mark.parametrize(
    ("reference", "model_yaml"),
    [
        ("@load: missing-model.yml", None),
        ("@load: invalid-model.yml", "model: {}\nentities: {}\n"),
        ("@load: malformed-model.yml", "model: [broken\n"),
    ],
)
async def test_returns_safe_bad_request_for_configured_model_failures(
    tmp_path,
    monkeypatch,
    reset_services,
    authorized_client,
    reference: str,
    model_yaml: str | None,
) -> None:
    projects_dir = tmp_path / "projects"
    monkeypatch.setattr(settings, "PROJECTS_DIR", projects_dir)
    await _create_project(authorized_client)
    if model_yaml is not None:
        model_filename = reference.removeprefix("@load: ").strip()
        (projects_dir / "test_project" / model_filename).write_text(model_yaml, encoding="utf-8")
    update_response = await authorized_client.patch(
        "/api/v1/projects/test_project/metadata",
        json={"target_model": reference},
    )
    assert update_response.status_code == 200, update_response.text

    response = await authorized_client.get("/api/v1/projects/test_project/target-model-entities")

    assert response.status_code == 400
    assert str(tmp_path) not in response.text
    assert "invalid-model.yml" not in response.text
    assert "malformed-model.yml" not in response.text
    assert "missing-model.yml" not in response.text


async def test_returns_empty_list_when_all_target_entities_are_in_project(
    tmp_path,
    monkeypatch,
    reset_services,
    authorized_client,
) -> None:
    projects_dir = tmp_path / "projects"
    monkeypatch.setattr(settings, "PROJECTS_DIR", projects_dir)
    await _create_project(authorized_client)
    response = await authorized_client.get("/api/v1/projects/test_project/raw-yaml")
    project_yaml = yaml.safe_load(response.json()["yaml_content"])
    project_yaml["metadata"]["target_model"] = {
        "model": {"name": "Test Model", "version": "1"},
        "entities": {"already_present": {}},
    }
    update_response = await authorized_client.put(
        "/api/v1/projects/test_project/raw-yaml",
        json={"yaml_content": yaml.safe_dump(project_yaml, sort_keys=False)},
    )
    assert update_response.status_code == 200, update_response.text

    options_response = await authorized_client.get("/api/v1/projects/test_project/target-model-entities")

    assert options_response.status_code == 200, options_response.text
    assert options_response.json() == {"configured": True, "entities": []}
