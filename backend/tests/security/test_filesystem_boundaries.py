"""Filesystem boundary regression tests for the backend layer.

These tests prove that file read, write, download, upload, backup, and
directive paths cannot escape their approved roots. They exercise the HTTP
download endpoint, project-name validation, file browsing resolution, and
backup creation with disposable directories.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from httpx import AsyncClient

from backend.app.services import execute_service, project_service
from backend.app.services.project.file_manager import FileManager
from backend.app.services.project.project_utils import ProjectUtils
from backend.app.services.yaml_service import YamlService
from backend.app.utils.exceptions import BadRequestError

# pylint: disable=redefined-outer-name


# ---------------------------------------------------------------------------
# Download endpoint
# ---------------------------------------------------------------------------


@pytest.fixture
def reset_execution_services() -> Iterator[None]:
    """Reset execution service singletons so they read the patched projects dir."""
    execute_service._execute_service = None
    project_service._project_service = None
    yield
    execute_service._execute_service = None
    project_service._project_service = None


@pytest.fixture
async def project_with_outputs(authorized_client, reset_execution_services) -> tuple[AsyncClient, Path]:
    """Create a project and seed its outputs directory."""
    client = authorized_client
    create_response = await client.post("/api/v1/projects", json={"name": "demo", "entities": {}})
    assert create_response.status_code in (200, 201), create_response.text

    # authorized_client points PROJECTS_DIR at its tmp_path; resolve the same way.
    projects_dir = Path(project_service.get_project_service().projects_dir)
    outputs_dir = projects_dir / "demo" / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    (outputs_dir / "result.csv").write_text("a,b\n1,2\n")
    return client, outputs_dir


@pytest.mark.asyncio
async def test_download_endpoint_serves_file_inside_output_root(project_with_outputs) -> None:
    """The download endpoint serves a managed file inside the output root."""
    client, _ = project_with_outputs

    response = await client.get("/api/v1/projects/demo/execute/download", params={"target": "result.csv"})

    assert response.status_code == 200
    assert response.text == "a,b\n1,2\n"


@pytest.mark.asyncio
async def test_download_endpoint_rejects_traversal_target(project_with_outputs, tmp_path: Path) -> None:
    """The download endpoint cannot serve a file outside the output root."""
    client, _ = project_with_outputs
    (tmp_path / "outside.csv").write_text("secret\n")

    response = await client.get("/api/v1/projects/demo/execute/download", params={"target": "../outside.csv"})

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_download_endpoint_rejects_absolute_target(project_with_outputs, tmp_path: Path) -> None:
    """The download endpoint cannot serve an absolute path outside the output root."""
    client, _ = project_with_outputs
    outside = tmp_path / "outside.csv"
    outside.write_text("secret\n")

    response = await client.get("/api/v1/projects/demo/execute/download", params={"target": str(outside)})

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_download_endpoint_rejects_symlinked_file(project_with_outputs, tmp_path: Path) -> None:
    """The download endpoint cannot serve a symlinked file pointing outside the output root."""
    client, outputs_dir = project_with_outputs
    outside = tmp_path / "outside.csv"
    outside.write_text("secret\n")
    (outputs_dir / "leak.csv").symlink_to(outside)

    response = await client.get("/api/v1/projects/demo/execute/download", params={"target": "leak.csv"})

    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Backup confinement
# ---------------------------------------------------------------------------


def test_create_backup_rejects_symlinked_backups_directory(tmp_path: Path) -> None:
    """A backups directory symlinked outside the project must not receive a backup."""
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    project_file = project_dir / "shapeshifter.yml"
    project_file.write_text("metadata:\n  name: demo\n")

    outside = tmp_path / "outside"
    outside.mkdir()
    (project_dir / "backups").symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="outside the managed root"):
        YamlService().create_backup(project_file)

    assert not list(outside.iterdir())


def test_create_backup_writes_inside_project_backups_directory(tmp_path: Path) -> None:
    """A backup is written next to the project file, not outside it."""
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    project_file = project_dir / "shapeshifter.yml"
    project_file.write_text("metadata:\n  name: demo\n")

    backup_path = YamlService().create_backup(project_file)

    assert backup_path.parent == project_dir / "backups"
    assert backup_path.is_file()


# ---------------------------------------------------------------------------
# Project name variations
# ---------------------------------------------------------------------------


@pytest.fixture
def project_utils(tmp_path: Path) -> ProjectUtils:
    """Create project utilities rooted in a disposable directory."""
    return ProjectUtils(projects_dir=tmp_path / "projects")


class TestProjectNameVariations:
    """Project names with special characters must stay inside the projects root."""

    @pytest.mark.parametrize("name", ["археология:проба", "archäologie:probe", "proyecto@fase-1", "project name"])
    def test_special_and_unicode_names_are_accepted(self, project_utils: ProjectUtils, name: str) -> None:
        """Special characters and Unicode are allowed when they cannot escape the root."""
        assert project_utils.validate_project_name(name) == name.replace("/", ":")

    @pytest.mark.parametrize("name", ["foo/..", "foo/../bar", "..", "../outside", "a:b/../c"])
    def test_dot_segment_names_are_rejected(self, project_utils: ProjectUtils, name: str) -> None:
        """Names containing a parent segment are rejected before filesystem access."""
        with pytest.raises(BadRequestError):
            project_utils.validate_project_name(name)

    def test_nested_name_resolves_inside_projects_root(self, project_utils: ProjectUtils, tmp_path: Path) -> None:
        """A validated nested name maps to a path inside the projects root."""
        nested_dir = tmp_path / "projects" / "parent" / "child"
        nested_dir.mkdir(parents=True)
        (nested_dir / "shapeshifter.yml").write_text("metadata:\n  name: child\n")

        project_file = project_utils.ensure_project_exists("parent:child")

        assert project_file == nested_dir / "shapeshifter.yml"
        assert project_file.is_relative_to(tmp_path / "projects")


# ---------------------------------------------------------------------------
# File browsing resolution
# ---------------------------------------------------------------------------


@pytest.fixture
def file_manager(tmp_path: Path) -> FileManager:
    """Create a file manager rooted in a disposable directory."""

    def ensure_project_exists(name: str) -> Path:
        return tmp_path / "projects" / name / "shapeshifter.yml"

    return FileManager(
        projects_root=tmp_path / "projects",
        global_data_dir=tmp_path / "shared" / "shared-data",
        application_root=tmp_path,
        sanitize_project_name_callback=lambda name: name,
        ensure_project_exists_callback=ensure_project_exists,
    )


def test_resolve_path_rejects_traversal(file_manager: FileManager) -> None:
    """File browsing cannot resolve a path above the managed root."""
    with pytest.raises(BadRequestError, match="outside the managed directory"):
        file_manager._resolve_path("../outside.xlsx", "global")


def test_resolve_path_rejects_absolute_path_outside_root(file_manager: FileManager, tmp_path: Path) -> None:
    """File browsing cannot resolve an absolute path outside the managed root."""
    outside = tmp_path / "outside.xlsx"
    outside.write_bytes(b"content")

    with pytest.raises(BadRequestError, match="outside the managed directory"):
        file_manager._resolve_path(str(outside), "global")


def test_resolve_path_rejects_symlink_escape(file_manager: FileManager, tmp_path: Path) -> None:
    """File browsing cannot resolve a symlink that points outside the managed root."""
    global_dir = tmp_path / "shared" / "shared-data"
    global_dir.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "data.xlsx").write_bytes(b"content")
    (global_dir / "link").symlink_to(outside, target_is_directory=True)

    with pytest.raises(BadRequestError, match="outside the managed directory"):
        file_manager._resolve_path("link/data.xlsx", "global")


def test_resolve_path_missing_parent_reports_not_found(file_manager: FileManager) -> None:
    """A path with a missing parent directory is reported as not found, not resolved."""
    with pytest.raises(BadRequestError, match="File not found"):
        file_manager._resolve_path("missing/data.xlsx", "global")
