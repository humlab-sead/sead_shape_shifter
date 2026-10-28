"""Tests for missing target-model entity options."""

from unittest.mock import Mock

import pytest

from backend.app.models.project import Project, ProjectMetadata
from backend.app.services.project_service import ProjectService
from backend.app.services.target_model_entity_options_service import TargetModelEntityOptionsService
from backend.app.utils.exceptions import BadRequestError


def _project(target_model: str | dict | None, entity_names: tuple[str, ...] = ()) -> Project:
    return Project(
        metadata=ProjectMetadata(name="test_project", entity_count=len(entity_names), target_model=target_model),
        entities={name: {} for name in entity_names},
    )


def _target_model() -> dict:
    return {
        "model": {"name": "Test Model", "version": "1"},
        "entities": {
            "z_required": {
                "role": "fact",
                "required": True,
                "description": "Required entity",
                "target_table": "target_table",
                "public_id": "target_id",
                "columns": {
                    "generated_key": {"required": True, "generated": True},
                    "source_name": {"required": True},
                    "optional_name": {"required": False},
                },
                "foreign_keys": [
                    {"entity": "trigger", "required": True},
                    {"entity": "destination", "via": "bridge", "required": True},
                    {"entity": "optional_parent"},
                ],
            },
            "a_optional": {"role": None, "required": False},
            "bridge": {"public_id": "bridge_id"},
            "destination": {"public_id": "destination_id"},
            "optional_parent": {},
            "trigger": {
                "public_id": "trigger_id",
                "foreign_keys": [{"entity": "destination", "required_when": {"has_new_rows": "trigger"}}],
            },
            "already_configured": {},
        },
    }


@pytest.fixture
def project_service() -> Mock:
    service = Mock(spec=ProjectService)
    return service


def test_returns_sorted_missing_entities_and_reference_requirements(project_service: Mock) -> None:
    project_service.load_project.return_value = _project(_target_model(), ("already_configured",))
    service = TargetModelEntityOptionsService(project_service)

    response = service.get_entity_options("test_project")

    assert response.configured is True
    assert [option.name for option in response.entities] == [
        "z_required",
        "a_optional",
        "bridge",
        "destination",
        "optional_parent",
        "trigger",
    ]
    required = response.entities[0]
    assert required.role == "fact"
    assert required.required is True
    assert required.description == "Required entity"
    assert required.target_table == "target_table"
    assert required.public_id == "target_id"
    assert required.required_columns == ["source_name"]
    assert [(link.path, link.missing_entities, link.required_when_has_new_rows) for link in required.required_links] == [
        (["bridge", "destination"], ["bridge", "destination"], None),
        (["trigger"], ["trigger"], None),
    ]
    trigger = next(option for option in response.entities if option.name == "trigger")
    assert [(link.path, link.missing_entities, link.required_when_has_new_rows) for link in trigger.required_links] == [
        (["destination"], ["destination"], "trigger")
    ]
    optional = response.entities[1]
    assert optional.role is None
    assert optional.public_id is None
    assert optional.required is False
    project_service.load_project.assert_called_once_with("test_project")
    project_service.save_project.assert_not_called()
    project_service.add_entity.assert_not_called()


def test_returns_explicit_empty_state_when_no_model_is_configured(project_service: Mock) -> None:
    project_service.load_project.return_value = _project(None)
    service = TargetModelEntityOptionsService(project_service)

    response = service.get_entity_options("test_project")

    assert response.model_dump() == {"configured": False, "entities": []}
    project_service.load_project.assert_called_once_with("test_project")


@pytest.mark.parametrize(
    "target_model",
    [
        {},
        {
            "model": {"name": "Invalid Model", "version": "1"},
            "entities": {"broken": {"foreign_keys": [{"entity": "missing"}]}},
        },
    ],
)
def test_rejects_configured_invalid_models(project_service: Mock, target_model: dict) -> None:
    project_service.load_project.return_value = _project(target_model)
    service = TargetModelEntityOptionsService(project_service)

    with pytest.raises(BadRequestError, match="could not be loaded or is invalid"):
        service.get_entity_options("test_project")

    project_service.save_project.assert_not_called()


def test_reports_configured_model_resolution_failure(project_service: Mock, monkeypatch: pytest.MonkeyPatch) -> None:
    project_service.load_project.return_value = _project("@load: missing.yml")
    mapper = Mock(side_effect=FileNotFoundError("/private/project/missing.yml"))
    monkeypatch.setattr(
        "backend.app.services.target_model_entity_options_service.ProjectMapper.to_core",
        mapper,
    )
    service = TargetModelEntityOptionsService(project_service)

    with pytest.raises(BadRequestError, match="could not be loaded or is invalid"):
        service.get_entity_options("test_project")

    mapper.assert_called_once()
    project_service.save_project.assert_not_called()
