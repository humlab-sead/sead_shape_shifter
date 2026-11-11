"""Tests for the project direct target-model foreign key route."""

import pytest
import yaml

from backend.app.core.config import settings
from backend.app.services import project_service, yaml_service

ROUTE = "/api/v1/projects/test_project/target-model-direct-foreign-keys"


@pytest.fixture(name="reset_services")
def _reset_services(monkeypatch):
    """Reset services that retain project paths between requests."""
    monkeypatch.setattr(project_service, "_project_service", None)
    monkeypatch.setattr(yaml_service, "_yaml_service", None)


def _target_model() -> dict:
    return {
        "model": {"name": "Test Model", "version": "1"},
        "entities": {
            "source_entity": {
                # The source declares no target ID column, so eligible relationships are
                # returned even though the source does not currently produce the ID.
                "columns": {"source_name": {"required": True}},
                "foreign_keys": [
                    {"entity": "required_target", "required": True},
                    {"entity": "optional_target"},
                    {"entity": "already_present"},
                    {"entity": "via_target", "via": "bridge", "required": True},
                    {"entity": "public_id_only"},
                ],
            },
            "required_target": {"public_id": "required_target_id", "target_table": "required_target"},
            "optional_target": {"public_id": "optional_target_id", "target_table": "optional_target"},
            "already_present": {"public_id": "already_present_id", "target_table": "already_present"},
            "via_target": {"public_id": "via_target_id", "target_table": "via_target"},
            "bridge": {"public_id": "bridge_id"},
            "public_id_only": {"public_id": "public_id_only_id"},
        },
    }


async def _create_project(client) -> None:
    response = await client.post(
        "/api/v1/projects",
        json={
            "name": "test_project",
            "data_provider_code": "test-provider",
            "provider_schema": "schema-one",
            "entities": {"source_entity": {}, "already_present": {}},
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
async def test_returns_eligible_direct_relationships_without_changing_project_yaml(
    tmp_path,
    monkeypatch,
    reset_services,  # pylint: disable=unused-argument
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

    response = await authorized_client.get(f"{ROUTE}/source_entity")
    after_yaml = await authorized_client.get("/api/v1/projects/test_project/raw-yaml")

    assert response.status_code == 200, response.text
    assert response.json() == {
        "state": "resolved",
        "relationships": [
            {"target_entity": "already_present", "public_id": "already_present_id", "target_table": "already_present"},
            {"target_entity": "optional_target", "public_id": "optional_target_id", "target_table": "optional_target"},
            {"target_entity": "required_target", "public_id": "required_target_id", "target_table": "required_target"},
        ],
    }
    assert original_yaml.json() == after_yaml.json()


async def test_includes_target_picker_omits_and_excludes_ineligible_targets(
    tmp_path,
    monkeypatch,
    reset_services,  # pylint: disable=unused-argument
    authorized_client,
) -> None:
    projects_dir = tmp_path / "projects"
    target_models_dir = tmp_path / "shared" / "target-models"
    monkeypatch.setattr(settings, "PROJECTS_DIR", projects_dir)
    monkeypatch.setattr(settings, "GLOBAL_TARGET_MODEL_DIR", target_models_dir)
    await _create_project(authorized_client)
    await _configure_model(authorized_client, projects_dir, target_models_dir, "local")

    relationships_response = await authorized_client.get(f"{ROUTE}/source_entity")
    picker_response = await authorized_client.get("/api/v1/projects/test_project/target-model-entities")

    assert relationships_response.status_code == 200, relationships_response.text
    assert picker_response.status_code == 200, picker_response.text

    relationship_targets = [relationship["target_entity"] for relationship in relationships_response.json()["relationships"]]
    # `already_present` is configured in the project, so the picker omits it while the new
    # route still lists it. `via_target` and `public_id_only` are not direct-eligible.
    assert relationship_targets == ["already_present", "optional_target", "required_target"]
    assert "already_present" not in [option["name"] for option in picker_response.json()["entities"]]
    assert "via_target" not in relationship_targets
    assert "public_id_only" not in relationship_targets


async def test_returns_unconfigured_state_when_project_has_no_target_model(
    tmp_path,
    monkeypatch,
    reset_services,  # pylint: disable=unused-argument
    authorized_client,
) -> None:
    monkeypatch.setattr(settings, "PROJECTS_DIR", tmp_path / "projects")
    await _create_project(authorized_client)

    response = await authorized_client.get(f"{ROUTE}/source_entity")

    assert response.status_code == 200
    assert response.json() == {"state": "not_configured", "relationships": []}


async def test_returns_resolved_empty_state_for_unknown_entity(
    tmp_path,
    monkeypatch,
    reset_services,  # pylint: disable=unused-argument
    authorized_client,
) -> None:
    projects_dir = tmp_path / "projects"
    target_models_dir = tmp_path / "shared" / "target-models"
    monkeypatch.setattr(settings, "PROJECTS_DIR", projects_dir)
    monkeypatch.setattr(settings, "GLOBAL_TARGET_MODEL_DIR", target_models_dir)
    await _create_project(authorized_client)
    await _configure_model(authorized_client, projects_dir, target_models_dir, "local")

    response = await authorized_client.get(f"{ROUTE}/unknown_entity")

    assert response.status_code == 200, response.text
    assert response.json() == {"state": "resolved", "relationships": []}


@pytest.mark.parametrize(
    ("reference", "model_yaml"),
    [
        ("@load: missing-model.yml", None),
        ("@load: invalid-model.yml", "model: {}\nentities: {}\n"),
        ("@load: malformed-model.yml", "model: [broken\n"),
    ],
)
async def test_returns_unresolvable_state_for_configured_model_failures(
    tmp_path,
    monkeypatch,
    reset_services,  # pylint: disable=unused-argument
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

    response = await authorized_client.get(f"{ROUTE}/source_entity")
    picker_response = await authorized_client.get("/api/v1/projects/test_project/target-model-entities")

    assert response.status_code == 200, response.text
    assert response.json() == {"state": "unresolvable", "relationships": []}
    assert str(tmp_path) not in response.text
    assert "invalid-model.yml" not in response.text
    assert "malformed-model.yml" not in response.text
    assert "missing-model.yml" not in response.text
    assert picker_response.status_code == 400
