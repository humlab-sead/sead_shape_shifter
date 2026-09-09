"""Regression tests for @include and @load directive path confinement.

These tests prove that directive file paths cannot escape the approved data
roots passed by the mapper layer. The control under test is
``_resolve_directive_file_path`` in ``src/configuration/resolve.py``, reached
through the public ``resolve_directives`` entry point with ``allowed_roots`` set.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.configuration.resolve import resolve_directives


@pytest.fixture(name="project_root")
def _project_root(tmp_path: Path) -> Path:
    """Create a project directory with a project YAML file used as source_path."""
    root = tmp_path / "projects" / "demo"
    root.mkdir(parents=True)
    (root / "shapeshifter.yml").write_text("metadata:\n  name: demo\n")
    return root


@pytest.fixture(name="shared_root")
def _shared_root(tmp_path: Path) -> Path:
    """Create a second approved root for global shared data."""
    root = tmp_path / "shared"
    root.mkdir()
    return root


@pytest.fixture(name="allowed_roots")
def _allowed_roots(project_root: Path, shared_root: Path) -> tuple[Path, ...]:
    """Return the approved roots passed by the mapper layer."""
    return (project_root, shared_root)


@pytest.fixture(name="source_path")
def _source_path(project_root: Path) -> str:
    """Return the project YAML path used as the directive source_path."""
    return str(project_root / "shapeshifter.yml")


class TestIncludeDirectiveConfinement:
    """@include directives must stay inside an approved root."""

    def test_rejects_absolute_path_outside_approved_roots(self, tmp_path: Path, allowed_roots: tuple[Path, ...], source_path: str) -> None:
        outside = tmp_path / "outside.yml"
        outside.write_text("secret: value\n")

        with pytest.raises(ValueError, match="outside the approved data roots"):
            resolve_directives({"database": f"@include:{outside}"}, source_path=source_path, allowed_roots=allowed_roots)

    def test_rejects_traversal_outside_approved_roots(self, tmp_path: Path, allowed_roots: tuple[Path, ...], source_path: str) -> None:
        (tmp_path / "outside.yml").write_text("secret: value\n")

        with pytest.raises(ValueError, match="outside the approved data roots"):
            resolve_directives({"database": "@include:../../outside.yml"}, source_path=source_path, allowed_roots=allowed_roots)

    def test_rejects_symlink_escape(self, tmp_path: Path, project_root: Path, allowed_roots: tuple[Path, ...], source_path: str) -> None:
        outside_dir = tmp_path / "outside_dir"
        outside_dir.mkdir()
        (outside_dir / "leak.yml").write_text("secret: value\n")
        (project_root / "link").symlink_to(outside_dir, target_is_directory=True)

        with pytest.raises(ValueError, match="outside the approved data roots"):
            resolve_directives({"database": "@include:link/leak.yml"}, source_path=source_path, allowed_roots=allowed_roots)

    def test_allows_relative_path_inside_project(self, project_root: Path, allowed_roots: tuple[Path, ...], source_path: str) -> None:
        (project_root / "included.yml").write_text("driver: sql\n")

        result = resolve_directives({"database": "@include:included.yml"}, source_path=source_path, allowed_roots=allowed_roots)

        assert result == {"database": {"driver": "sql"}}

    def test_allows_path_inside_second_approved_root(self, shared_root: Path, allowed_roots: tuple[Path, ...], source_path: str) -> None:
        (shared_root / "sead-options.yml").write_text("driver: csv\n")

        result = resolve_directives(
            {"options": f"@include:{shared_root / 'sead-options.yml'}"}, source_path=source_path, allowed_roots=allowed_roots
        )

        assert result == {"options": {"driver": "csv"}}


class TestLoadDirectiveConfinement:
    """@load directives must stay inside an approved root."""

    def test_rejects_absolute_path_outside_approved_roots(self, tmp_path: Path, allowed_roots: tuple[Path, ...], source_path: str) -> None:
        outside = tmp_path / "outside.csv"
        outside.write_text("a,b\n1,2\n")

        with pytest.raises(ValueError, match="outside the approved data roots"):
            resolve_directives({"values": f"@load:{outside}"}, source_path=source_path, allowed_roots=allowed_roots)

    def test_rejects_traversal_outside_approved_roots(self, tmp_path: Path, allowed_roots: tuple[Path, ...], source_path: str) -> None:
        (tmp_path / "outside.csv").write_text("a,b\n1,2\n")

        with pytest.raises(ValueError, match="outside the approved data roots"):
            resolve_directives({"values": "@load:../../outside.csv"}, source_path=source_path, allowed_roots=allowed_roots)

    def test_rejects_symlink_escape(self, tmp_path: Path, project_root: Path, allowed_roots: tuple[Path, ...], source_path: str) -> None:
        outside_dir = tmp_path / "outside_dir"
        outside_dir.mkdir()
        (outside_dir / "data.csv").write_text("a,b\n1,2\n")
        (project_root / "link").symlink_to(outside_dir, target_is_directory=True)

        with pytest.raises(ValueError, match="outside the approved data roots"):
            resolve_directives({"values": "@load:link/data.csv"}, source_path=source_path, allowed_roots=allowed_roots)

    def test_allows_relative_path_inside_project(self, project_root: Path, allowed_roots: tuple[Path, ...], source_path: str) -> None:
        (project_root / "data.csv").write_text("a,b\n1,2\n")

        result = resolve_directives({"values": "@load:data.csv"}, source_path=source_path, allowed_roots=allowed_roots)

        assert result == {"values": [{"a": "1", "b": "2"}]}
