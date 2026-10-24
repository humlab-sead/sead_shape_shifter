"""Tests for draft-only requested-reference mapping."""

from copy import deepcopy
from pathlib import Path

import pytest

from backend.app.core.config import settings
from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.models.project import Project, ProjectMetadata
from src.configuration.resolve import RequestedReferenceResolutionError


def make_project(project_file: Path, entities: dict) -> Project:
    """Create a project model with the given raw entity values."""
    return Project(
        metadata=ProjectMetadata(name="test_project", file_path=str(project_file), entity_count=len(entities)),
        entities=entities,
    )


def test_requested_reference_resolves_only_selected_path_and_preserves_source(tmp_path: Path) -> None:
    """Resolve a requested nested path while leaving unrelated failures raw."""
    project_file = tmp_path / "projects" / "test_project" / "shapeshifter.yml"
    project_file.parent.mkdir(parents=True)
    project_file.write_text("entities: {}", encoding="utf-8")
    project = make_project(
        project_file,
        {
            "source": {"keys": ["id", "site_id"]},
            "middle": {"keys": "@value: entities.source.keys"},
            "child": {"keys": "@value: entities.middle.keys"},
            "broken": {"keys": "@value: entities.missing.keys"},
        },
    )
    original = deepcopy(project.entities)

    core_project = ProjectMapper.to_core(project, requested_reference_path="entities.child.keys")

    assert core_project.cfg["entities"]["child"]["keys"] == ["id", "site_id"]
    assert core_project.cfg["entities"]["broken"]["keys"] == "@value: entities.missing.keys"
    assert project.entities == original


def test_requested_reference_uses_project_and_shared_file_roots(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Allow reached load files from configured roots and reject files outside them."""
    projects_root = tmp_path / "projects"
    project_file = projects_root / "test_project" / "shapeshifter.yml"
    project_file.parent.mkdir(parents=True)
    project_file.write_text("entities: {}", encoding="utf-8")
    shared_data = tmp_path / "shared-data"
    shared_data.mkdir()
    allowed_file = shared_data / "columns.yml"
    allowed_file.write_text("- alpha\n- beta\n", encoding="utf-8")
    outside_file = tmp_path / "outside.yml"
    outside_file.write_text("- hidden\n", encoding="utf-8")
    monkeypatch.setattr(settings, "PROJECTS_DIR", projects_root)
    monkeypatch.setattr(settings, "GLOBAL_DATA_DIR", shared_data)
    monkeypatch.setattr(settings, "GLOBAL_DATA_SOURCE_DIR", tmp_path / "shared-sources")
    monkeypatch.setattr(settings, "GLOBAL_TARGET_MODEL_DIR", tmp_path / "target-models")

    allowed_project = make_project(project_file, {"child": {"keys": f"@load: {allowed_file}"}})
    outside_project = make_project(project_file, {"child": {"keys": f"@load: {outside_file}"}})

    result = ProjectMapper.to_core(allowed_project, requested_reference_path="entities.child.keys")

    assert result.cfg["entities"]["child"]["keys"] == ["alpha", "beta"]
    with pytest.raises(RequestedReferenceResolutionError) as error:
        ProjectMapper.to_core(outside_project, requested_reference_path="entities.child.keys")
    assert error.value.reason_code == "dependency_failure"


def test_default_conversion_still_resolves_nested_references_and_reports_file_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keep normal full conversion behavior when editor-only mode is not requested."""
    projects_root = tmp_path / "projects"
    project_file = projects_root / "test_project" / "shapeshifter.yml"
    project_file.parent.mkdir(parents=True)
    project_file.write_text("entities: {}", encoding="utf-8")
    monkeypatch.setattr(settings, "PROJECTS_DIR", projects_root)
    valid_project = make_project(
        project_file,
        {
            "source": {"keys": ["id", "site_id"]},
            "child": {"keys": "@value: entities.source.keys"},
        },
    )
    broken_project = make_project(
        project_file,
        {
            "child": {"keys": ["id"], "columns": "@include: missing.yml"},
        },
    )

    core_project = ProjectMapper.to_core(valid_project)

    assert core_project.cfg["entities"]["child"]["keys"] == ["id", "site_id"]
    with pytest.raises(FileNotFoundError):
        ProjectMapper.to_core(broken_project)
