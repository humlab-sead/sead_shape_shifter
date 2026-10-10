"""Tests for draft-aware column candidate resolution."""

from unittest.mock import Mock

from backend.app.models.column_availability import ColumnAvailabilityResponse
from backend.app.models.project import Project, ProjectMetadata
from backend.app.services.project_service import ProjectService
from backend.app.services.stage_aware_column_service import StageAwareColumnService


def _project() -> Project:
    return Project(
        metadata=ProjectMetadata(name="test_project", entity_count=2),
        entities={
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
        },
    )


def test_resolves_submitted_draft_and_selected_parent_output_without_mutating_loaded_project() -> None:
    saved_project: Project = _project()
    project_service = Mock(spec=ProjectService)
    project_service.load_project.return_value = saved_project
    service = StageAwareColumnService(project_service)

    result: ColumnAvailabilityResponse = service.get_column_availability(
        "test_project",
        "child",
        {
            "type": "entity",
            "public_id": "child_id",
            "keys": ["child_key"],
            "columns": ["child_key", "draft_value"],
            "foreign_keys": [{"entity": "parent", "local_keys": ["child_key"], "remote_keys": ["parent_key"]}],
            "extra_columns": {"child_derived": "draft_value"},
        },
    )

    assert "draft_value" in result.columns
    assert "saved_value" not in result.columns
    assert "derived_value" in result.foreign_keys[0].remote_keys
    assert "system_id" in result.foreign_keys[0].remote_keys
    assert result.foreign_keys[0].extra_column_sources == result.foreign_keys[0].remote_keys
    assert saved_project.entities["child"]["columns"] == ["child_key", "saved_value"]


def test_returns_advisory_candidates_for_unknown_parent_and_missing_source_metadata() -> None:
    project_service = Mock(spec=ProjectService)
    project_service.load_project.return_value = _project()
    service = StageAwareColumnService(project_service)

    result: ColumnAvailabilityResponse = service.get_column_availability(
        "test_project",
        "child",
        {
            "type": "entity",
            "columns": ["child_key"],
            "foreign_keys": [{"entity": "unknown", "local_keys": ["child_key"], "remote_keys": ["id"]}],
        },
    )

    assert result.columns == ["child_key"]
    assert result.foreign_keys[0].entity == "unknown"
    assert result.foreign_keys[0].remote_keys == []


def test_does_not_suggest_a_key_without_a_producer() -> None:
    project_service = Mock(spec=ProjectService)
    project_service.load_project.return_value = _project()
    service = StageAwareColumnService(project_service)

    result: ColumnAvailabilityResponse = service.get_column_availability(
        "test_project",
        "child",
        {
            "type": "entity",
            "keys": ["unproduced_key"],
            "columns": ["draft_value"],
        },
    )

    assert result.columns == ["draft_value"]
    assert "unproduced_key" not in result.business_keys
