"""Tests for execution output path confinement."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from backend.app.services.execute_service import ExecuteService
from backend.app.services.project_service import ProjectService


@pytest.fixture
def execute_service(tmp_path: Path) -> ExecuteService:
    """Create an execution service with an isolated project root."""
    project_service = MagicMock(spec=ProjectService)
    project_service.projects_dir = tmp_path / "projects"
    return ExecuteService(project_service=project_service)


def test_resolve_output_target_allows_nested_relative_file(execute_service: ExecuteService, tmp_path: Path) -> None:
    """Resolve a nested file target below the project's output directory."""
    target = execute_service.resolve_output_target("project-a", "exports/result.csv", "file")

    assert Path(target) == tmp_path / "projects" / "project-a" / "outputs" / "exports" / "result.csv"


@pytest.mark.parametrize("target", ["../outside.csv", "../project-b/outputs/result.csv"])
def test_resolve_output_target_rejects_traversal_and_cross_project_targets(execute_service: ExecuteService, target: str) -> None:
    """Reject targets that leave the authorized project's output directory."""
    with pytest.raises(ValueError, match="outside the managed root"):
        execute_service.resolve_output_target("project-a", target, "file")


def test_resolve_output_target_rejects_absolute_target(execute_service: ExecuteService, tmp_path: Path) -> None:
    """Reject an absolute output target before it can select another file."""
    with pytest.raises(ValueError, match="relative output name"):
        execute_service.resolve_output_target("project-a", str(tmp_path / "outside.csv"), "file")


def test_resolve_output_target_rejects_symlinked_output_root(execute_service: ExecuteService, tmp_path: Path) -> None:
    """Reject an output directory symlink that points outside the project."""
    project_root = tmp_path / "projects" / "project-a"
    project_root.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    (project_root / "outputs").symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="outside the managed root"):
        execute_service.resolve_output_target("project-a", "result.csv", "file")


def test_resolve_output_target_rejects_symlinked_project_directory(execute_service: ExecuteService, tmp_path: Path) -> None:
    """Reject a project path symlink that points outside the projects root."""
    projects_root = tmp_path / "projects"
    projects_root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (projects_root / "project-a").symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="outside the managed root"):
        execute_service.resolve_output_target("project-a", "result.csv", "file")


def test_resolve_output_target_rechecks_after_parent_directory_creation(
    execute_service: ExecuteService, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reject a parent directory replaced by an external symlink during setup."""
    outside = tmp_path / "outside"
    outside.mkdir()
    swapped_parent = tmp_path / "projects" / "project-a" / "outputs" / "exports"
    original_mkdir = Path.mkdir

    def mkdir_and_swap(path: Path, mode: int = 0o777, parents: bool = False, exist_ok: bool = False) -> None:
        original_mkdir(path, mode=mode, parents=parents, exist_ok=exist_ok)
        if path == swapped_parent:
            if path.is_symlink():
                path.unlink()
            else:
                path.rmdir()
            path.symlink_to(outside, target_is_directory=True)

    monkeypatch.setattr(Path, "mkdir", mkdir_and_swap)

    with pytest.raises(ValueError, match="outside the managed root"):
        execute_service.resolve_output_target("project-a", "exports/result.csv", "file")
