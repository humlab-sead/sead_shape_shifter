"""Tests for SPA catch-all path containment (S1).

The frontend build directory is not present in the test environment, so the
catch-all route is not registered on the app here. These tests exercise
``resolve_spa_file`` directly, which is the single decision the route makes
about which file to serve.
"""

from pathlib import Path

import pytest

from backend.app.main import resolve_spa_file


@pytest.fixture(name="dist_dir")
def dist_dir_fixture(tmp_path: Path) -> Path:
    """Create a fake frontend build directory with an index and one asset."""
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html>index</html>", encoding="utf-8")
    assets = dist / "assets"
    assets.mkdir()
    (assets / "app.js").write_text("console.log(1)", encoding="utf-8")
    # A secret file outside the build directory that must never be served.
    (tmp_path / "secret.txt").write_text("top-secret", encoding="utf-8")
    return dist


def test_serves_existing_file_inside_dist(dist_dir: Path) -> None:
    """A real file under the build directory is served."""
    result = resolve_spa_file("assets/app.js", dist_dir)
    assert result == dist_dir / "assets" / "app.js"


def test_deep_link_falls_back_to_index(dist_dir: Path) -> None:
    """An unknown client-side route returns index.html, not a 404 file."""
    result = resolve_spa_file("projects/42/edit", dist_dir)
    assert result == dist_dir / "index.html"


def test_empty_path_serves_index(dist_dir: Path) -> None:
    """The root path serves index.html."""
    result = resolve_spa_file("", dist_dir)
    assert result == dist_dir / "index.html"


def test_parent_traversal_falls_back_to_index(dist_dir: Path) -> None:
    """A '../' path that escapes the build directory is not served."""
    result = resolve_spa_file("../secret.txt", dist_dir)
    assert result == dist_dir / "index.html"


def test_nested_parent_traversal_falls_back_to_index(dist_dir: Path) -> None:
    """Traversal that re-enters the root after escaping is still rejected."""
    result = resolve_spa_file("assets/../../secret.txt", dist_dir)
    assert result == dist_dir / "index.html"


def test_absolute_path_falls_back_to_index(dist_dir: Path, tmp_path: Path) -> None:
    """An absolute path outside the build directory is not served."""
    result = resolve_spa_file(str(tmp_path / "secret.txt"), dist_dir)
    assert result == dist_dir / "index.html"


def test_symlink_escape_falls_back_to_index(dist_dir: Path, tmp_path: Path) -> None:
    """A symlink inside the build that points outside is not served."""
    link = dist_dir / "assets" / "escape"
    link.symlink_to(tmp_path / "secret.txt")
    result = resolve_spa_file("assets/escape", dist_dir)
    assert result == dist_dir / "index.html"
