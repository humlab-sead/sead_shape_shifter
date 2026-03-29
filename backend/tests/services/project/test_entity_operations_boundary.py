"""Tests for EntityOperations boundary-based save callback wiring.

Verifies that:
- update_entity_by_name calls save_entity_boundary_callback when provided
- add_entity_by_name calls save_entity_boundary_callback when provided
- delete_entity_by_name calls save_entity_boundary_callback(name, entity, None) when provided
- All three fall back to save_project_callback when boundary callback is absent
"""

from typing import Any
from unittest.mock import MagicMock

import pytest

from backend.app.models.project import Project, ProjectMetadata
from backend.app.services.project.entity_operations import EntityOperations

# pylint: disable=redefined-outer-name


def _make_project(entities: dict[str, Any] | None = None) -> Project:
    metadata = ProjectMetadata(
        name="test-project",
        description="test",
        version="1.0.0",
        file_path="/fake/path/shapeshifter.yml",
        entity_count=len(entities or {}),
        created_at=0.0,
        modified_at=0.0,
        is_valid=True,
    )
    return Project(metadata=metadata, entities=entities or {}, options={})


def _sample_entity() -> dict[str, Any]:
    return {
        "type": "entity",
        "keys": ["sample_id"],
        "columns": ["name", "value"],
    }


@pytest.fixture
def project_with_entities() -> Project:
    return _make_project(
        {
            "sample": _sample_entity(),
            "site": {"type": "entity", "keys": ["site_id"], "columns": ["location"]},
        }
    )


def _make_operations(
    load_return: Project,
    *,
    with_boundary: bool,
) -> tuple[EntityOperations, MagicMock, MagicMock]:
    """Return (ops, save_project_mock, save_boundary_mock)."""
    load_mock = MagicMock(return_value=load_return)
    save_project_mock = MagicMock(return_value=load_return)
    lock_mock = MagicMock()
    lock_mock.__enter__ = MagicMock(return_value=None)
    lock_mock.__exit__ = MagicMock(return_value=False)
    lock_getter = MagicMock(return_value=lock_mock)

    save_boundary_mock = MagicMock() if with_boundary else None

    ops = EntityOperations(
        project_lock_getter=lock_getter,
        load_project_callback=load_mock,
        save_project_callback=save_project_mock,
        save_entity_boundary_callback=save_boundary_mock,
    )
    return ops, save_project_mock, save_boundary_mock


# ---------------------------------------------------------------------------
# add_entity_by_name
# ---------------------------------------------------------------------------


class TestAddEntityByNameBoundary:
    def test_calls_boundary_callback_when_provided(self, project_with_entities: Project) -> None:
        ops, save_project, save_boundary = _make_operations(project_with_entities, with_boundary=True)
        new_entity = {"type": "entity", "keys": ["analysis_id"], "columns": ["result"]}
        ops.add_entity_by_name("test-project", "analysis", new_entity)
        save_boundary.assert_called_once()
        call_args = save_boundary.call_args
        assert call_args[0][0] == "test-project"
        assert call_args[0][1] == "analysis"
        assert call_args[0][2] is not None  # dict, not None

    def test_does_not_call_save_project_when_boundary_provided(self, project_with_entities: Project) -> None:
        ops, save_project, save_boundary = _make_operations(project_with_entities, with_boundary=True)
        ops.add_entity_by_name("test-project", "analysis", {"type": "entity", "keys": ["x"]})
        save_project.assert_not_called()

    def test_falls_back_to_save_project_without_boundary(self, project_with_entities: Project) -> None:
        ops, save_project, _ = _make_operations(project_with_entities, with_boundary=False)
        ops.add_entity_by_name("test-project", "analysis", {"type": "entity", "keys": ["x"]})
        save_project.assert_called_once()


# ---------------------------------------------------------------------------
# update_entity_by_name
# ---------------------------------------------------------------------------


class TestUpdateEntityByNameBoundary:
    def test_calls_boundary_callback_when_provided(self, project_with_entities: Project) -> None:
        ops, save_project, save_boundary = _make_operations(project_with_entities, with_boundary=True)
        updated = {"type": "entity", "keys": ["sample_id"], "columns": ["name", "value", "extra"]}
        ops.update_entity_by_name("test-project", "sample", updated)
        save_boundary.assert_called_once()
        call_args = save_boundary.call_args
        assert call_args[0][0] == "test-project"
        assert call_args[0][1] == "sample"
        assert call_args[0][2] is not None

    def test_does_not_call_save_project_when_boundary_provided(self, project_with_entities: Project) -> None:
        ops, save_project, _ = _make_operations(project_with_entities, with_boundary=True)
        ops.update_entity_by_name("test-project", "sample", {"type": "entity", "keys": ["x"]})
        save_project.assert_not_called()

    def test_falls_back_to_save_project_without_boundary(self, project_with_entities: Project) -> None:
        ops, save_project, _ = _make_operations(project_with_entities, with_boundary=False)
        ops.update_entity_by_name("test-project", "sample", {"type": "entity", "keys": ["x"]})
        save_project.assert_called_once()


# ---------------------------------------------------------------------------
# delete_entity_by_name
# ---------------------------------------------------------------------------


class TestDeleteEntityByNameBoundary:
    def test_calls_boundary_callback_with_none(self, project_with_entities: Project) -> None:
        ops, save_project, save_boundary = _make_operations(project_with_entities, with_boundary=True)
        ops.delete_entity_by_name("test-project", "sample")
        save_boundary.assert_called_once()
        call_args = save_boundary.call_args
        assert call_args[0][0] == "test-project"
        assert call_args[0][1] == "sample"
        assert call_args[0][2] is None  # deletion signal

    def test_does_not_call_save_project_when_boundary_provided(self, project_with_entities: Project) -> None:
        ops, save_project, _ = _make_operations(project_with_entities, with_boundary=True)
        ops.delete_entity_by_name("test-project", "sample")
        save_project.assert_not_called()

    def test_falls_back_to_save_project_without_boundary(self, project_with_entities: Project) -> None:
        ops, save_project, _ = _make_operations(project_with_entities, with_boundary=False)
        ops.delete_entity_by_name("test-project", "sample")
        save_project.assert_called_once()
