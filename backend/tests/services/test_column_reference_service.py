"""Tests for draft-aware reference resolution and filtered completion."""

from copy import deepcopy
from typing import Any

import pytest

from backend.app.models.column_reference import ColumnReferenceFailureCode
from backend.app.models.project import Project, ProjectMetadata
from backend.app.services.column_reference_service import ColumnReferenceService


class StubProjectService:
    """Return copies of one configured project for service tests."""

    def __init__(self, project: Project) -> None:
        self.project = project

    def load_project(self, project_name: str) -> Project:
        assert project_name == "test_project"
        return self.project.model_copy(deep=True)


def make_service(entities: dict[str, Any], options: dict[str, Any] | None = None) -> tuple[ColumnReferenceService, Project]:
    """Build a service and its original saved project."""
    project = Project(
        metadata=ProjectMetadata(name="test_project", entity_count=len(entities)),
        entities=entities,
        options=options or {},
    )
    return ColumnReferenceService(StubProjectService(project)), project


def test_resolution_uses_draft_values_and_keeps_nested_order_without_mutation() -> None:
    """Use the submitted draft instead of saved values and leave loaded project data unchanged."""
    service, saved_project = make_service(
        {
            "source": {"keys": ["saved"]},
            "middle": {"keys": "@value: entities.source.keys"},
            "child": {"keys": ["before", "@value: entities.middle.keys", "after"]},
        }
    )
    saved_entities = deepcopy(saved_project.entities)

    result = service.resolve_reference(
        "test_project",
        "source",
        {"keys": ["draft-b", "draft-a"]},
        "@value: entities.child.keys",
    )

    assert result.status == "resolved"
    assert result.path == "entities.child.keys"
    assert result.columns == ["before", "draft-b", "draft-a", "after"]
    assert result.reason_code is None
    assert saved_project.entities == saved_entities


@pytest.mark.parametrize(
    ("directive", "expected_code"),
    [
        ("entities.site.keys", ColumnReferenceFailureCode.MALFORMED_INPUT),
        ("@value: entities.site.keys + ['legacy']", ColumnReferenceFailureCode.MALFORMED_INPUT),
        ("@value: entities.missing.keys", ColumnReferenceFailureCode.MISSING_PATH),
        ("@value: entities.first.keys", ColumnReferenceFailureCode.CIRCULAR_REFERENCE),
        ("@value: entities.site.public_id", ColumnReferenceFailureCode.WRONG_RESULT_TYPE),
        ("@value: entities.site.mixed", ColumnReferenceFailureCode.WRONG_RESULT_TYPE),
    ],
)
def test_resolution_returns_a_local_reason_for_bad_references(directive: str, expected_code: ColumnReferenceFailureCode) -> None:
    """Return stable local failures without a columns result."""
    service, _ = make_service(
        {
            "site": {"keys": ["id"], "public_id": "site_id", "mixed": ["id", 4]},
            "first": {"keys": "@value: entities.second.keys"},
            "second": {"keys": "@value: entities.first.keys"},
        }
    )

    result = service.resolve_reference("test_project", "child", {}, directive)

    assert result.status == "unresolved"
    assert result.columns is None
    assert result.reason_code == expected_code
    assert result.reason


def test_resolution_accepts_empty_string_list_and_manual_options_path() -> None:
    """Accept empty lists and complete paths outside the entity completion scope."""
    service, _ = make_service({"site": {"keys": []}}, {"columns": ["option_a", "option_b"]})

    empty_result = service.resolve_reference("test_project", "child", {}, "@value: entities.site.keys")
    options_result = service.resolve_reference("test_project", "child", {}, "@value: options.columns")

    assert empty_result.status == "resolved"
    assert not empty_result.columns
    assert options_result.status == "resolved"
    assert options_result.columns == ["option_a", "option_b"]


def test_completion_narrows_candidates_and_skips_bad_properties_independently() -> None:
    """Offer eligible string lists while omitting the edited field and broken properties."""
    service, _ = make_service(
        {
            "site": {
                "keys": ["site_id"],
                "columns": ["name"],
                "public_id": "site_id",
                "mixed": ["valid", False],
                "broken": "@value: entities.unknown.keys",
                "loop_a": "@value: entities.site.loop_b",
                "loop_b": "@value: entities.site.loop_a",
            },
            "child": {"keys": ["child_id"], "columns": ["child_name"]},
        }
    )

    root = service.complete_references("test_project", "child", {}, "@value")
    entities = service.complete_references("test_project", "child", {}, "@value: entities.", preferred_entity="child")
    properties = service.complete_references(
        "test_project",
        "child",
        {},
        "@value: entities.site.",
        edited_field_path="entities.site.keys",
    )
    filtered = service.complete_references("test_project", "child", {}, "@value: entities.site.ke")

    assert root.candidates == ["@value: entities."]
    assert entities.candidates == ["@value: entities.child.", "@value: entities.site."]
    assert properties.candidates == ["@value: entities.site.columns"]
    assert filtered.candidates == ["@value: entities.site.keys"]


def test_completion_only_accepts_value_prefixes() -> None:
    """Do not offer project-wide or arbitrary-path candidates for unrelated text."""
    service, _ = make_service({"site": {"keys": ["id"]}})

    assert service.complete_references("test_project", "child", {}, "entities.").candidates == []
    assert service.complete_references("test_project", "child", {}, "@value: options.").candidates == []
