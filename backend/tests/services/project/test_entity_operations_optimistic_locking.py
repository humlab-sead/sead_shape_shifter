"""Tests for entity-level optimistic locking (ETag / compare-and-swap).

Covers:
- compute_entity_etag: stable, content-based, repeatable
- update_entity_by_name_if_match: match → success, mismatch → EntityConflictError
- update_entity_by_name_if_match: missing entity → ResourceNotFoundError
- update_entity_by_name_if_match: calls boundary callback on success
- get_entity_etag_by_name: convenience wrapper
- Fallback (no If-Match header) via unconditional update_entity_by_name is unaffected
"""

from typing import Any
from unittest.mock import MagicMock, call

import pytest

from backend.app.exceptions import EntityConflictError, ResourceNotFoundError
from backend.app.models.project import Project, ProjectMetadata
from backend.app.services.project.entity_operations import EntityOperations, compute_entity_etag

# pylint: disable=redefined-outer-name


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


def _make_ops(
    project: Project,
    *,
    with_boundary: bool = True,
) -> tuple[EntityOperations, MagicMock, MagicMock]:
    """Return (ops, load_mock, save_boundary_mock)."""
    load_mock = MagicMock(return_value=project)
    save_project_mock = MagicMock(return_value=project)

    lock_mock = MagicMock()
    lock_mock.__enter__ = MagicMock(return_value=None)
    lock_mock.__exit__ = MagicMock(return_value=False)
    lock_getter = MagicMock(return_value=lock_mock)

    boundary_mock: MagicMock | None = MagicMock() if with_boundary else None

    ops = EntityOperations(
        project_lock_getter=lock_getter,
        load_project_callback=load_mock,
        save_project_callback=save_project_mock,
        save_entity_boundary_callback=boundary_mock,
    )
    return ops, load_mock, boundary_mock  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# compute_entity_etag
# ---------------------------------------------------------------------------


class TestComputeEntityEtag:
    def test_stable_for_same_dict(self):
        entity = _sample_entity()
        assert compute_entity_etag(entity) == compute_entity_etag(entity)

    def test_stable_regardless_of_insertion_order(self):
        a = {"b": 2, "a": 1}
        b = {"a": 1, "b": 2}
        assert compute_entity_etag(a) == compute_entity_etag(b)

    def test_changes_when_content_changes(self):
        entity = _sample_entity()
        modified = {**entity, "keys": ["other_id"]}
        assert compute_entity_etag(entity) != compute_entity_etag(modified)

    def test_returns_16_char_hex(self):
        tag = compute_entity_etag(_sample_entity())
        assert len(tag) == 16
        assert all(c in "0123456789abcdef" for c in tag)


# ---------------------------------------------------------------------------
# update_entity_by_name_if_match
# ---------------------------------------------------------------------------


class TestUpdateEntityByNameIfMatch:
    def test_etag_match_updates_entity(self):
        entity = _sample_entity()
        project = _make_project({"sample": entity})
        ops, load_mock, boundary_mock = _make_ops(project)

        expected_etag = compute_entity_etag(entity)
        updated = {**entity, "columns": ["name", "value", "extra"]}

        ops.update_entity_by_name_if_match("test-project", "sample", updated, expected_etag)

        # Boundary callback should have been called with the saved data
        assert boundary_mock is not None
        boundary_mock.assert_called_once()
        args = boundary_mock.call_args[0]
        assert args[0] == "test-project"
        assert args[1] == "sample"

    def test_etag_mismatch_raises_entity_conflict_error(self):
        entity = _sample_entity()
        project = _make_project({"sample": entity})
        ops, _, _ = _make_ops(project)

        with pytest.raises(EntityConflictError) as exc_info:
            ops.update_entity_by_name_if_match("test-project", "sample", entity, "stale_etag_123456")

        err = exc_info.value
        assert "sample" in str(err.message)
        assert err.context["current_etag"] == compute_entity_etag(entity)
        assert err.context["current_entity"] == entity

    def test_missing_entity_raises_resource_not_found(self):
        project = _make_project({"other": _sample_entity()})
        ops, _, _ = _make_ops(project)

        with pytest.raises(ResourceNotFoundError):
            ops.update_entity_by_name_if_match("test-project", "missing", _sample_entity(), "any_etag")

    def test_correct_etag_calls_boundary_not_save_project(self):
        """When boundary callback is wired, save_project should NOT be called."""
        entity = _sample_entity()
        project = _make_project({"sample": entity})
        load_mock = MagicMock(return_value=project)
        save_project_mock = MagicMock()
        lock_mock = MagicMock()
        lock_mock.__enter__ = MagicMock(return_value=None)
        lock_mock.__exit__ = MagicMock(return_value=False)
        lock_getter = MagicMock(return_value=lock_mock)
        boundary_mock = MagicMock()

        ops = EntityOperations(
            project_lock_getter=lock_getter,
            load_project_callback=load_mock,
            save_project_callback=save_project_mock,
            save_entity_boundary_callback=boundary_mock,
        )

        etag = compute_entity_etag(entity)
        ops.update_entity_by_name_if_match("test-project", "sample", entity, etag)

        boundary_mock.assert_called_once()
        save_project_mock.assert_not_called()

    def test_no_boundary_callback_falls_back_to_save_project(self):
        entity = _sample_entity()
        project = _make_project({"sample": entity})
        load_mock = MagicMock(return_value=project)
        save_project_mock = MagicMock(return_value=project)
        lock_mock = MagicMock()
        lock_mock.__enter__ = MagicMock(return_value=None)
        lock_mock.__exit__ = MagicMock(return_value=False)
        lock_getter = MagicMock(return_value=lock_mock)

        ops = EntityOperations(
            project_lock_getter=lock_getter,
            load_project_callback=load_mock,
            save_project_callback=save_project_mock,
            save_entity_boundary_callback=None,
        )

        etag = compute_entity_etag(entity)
        ops.update_entity_by_name_if_match("test-project", "sample", entity, etag)

        save_project_mock.assert_called_once()

    def test_force_reload_on_every_cas(self):
        """update_entity_by_name_if_match must force-reload from disk (bypass cache)."""
        entity = _sample_entity()
        project = _make_project({"sample": entity})
        load_mock = MagicMock(return_value=project)
        save_project_mock = MagicMock(return_value=project)
        lock_mock = MagicMock()
        lock_mock.__enter__ = MagicMock(return_value=None)
        lock_mock.__exit__ = MagicMock(return_value=False)
        lock_getter = MagicMock(return_value=lock_mock)

        ops = EntityOperations(
            project_lock_getter=lock_getter,
            load_project_callback=load_mock,
            save_project_callback=save_project_mock,
            save_entity_boundary_callback=MagicMock(),
        )

        etag = compute_entity_etag(entity)
        ops.update_entity_by_name_if_match("test-project", "sample", entity, etag)

        # force_reload=True must be passed to load_project_callback
        load_args = load_mock.call_args
        assert load_args.kwargs.get("force_reload") is True or (
            len(load_args.args) >= 2 and load_args.args[1] is True
        )


# ---------------------------------------------------------------------------
# get_entity_etag_by_name
# ---------------------------------------------------------------------------


class TestGetEntityEtagByName:
    def test_returns_etag_for_existing_entity(self):
        entity = _sample_entity()
        project = _make_project({"sample": entity})
        ops, _, _ = _make_ops(project)

        tag = ops.get_entity_etag_by_name("test-project", "sample")
        assert tag == compute_entity_etag(entity)

    def test_raises_for_missing_entity(self):
        project = _make_project({"other": _sample_entity()})
        ops, _, _ = _make_ops(project)

        with pytest.raises(ResourceNotFoundError):
            ops.get_entity_etag_by_name("test-project", "missing")
