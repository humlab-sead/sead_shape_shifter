from pathlib import Path

import pytest

from src.path_resolution import resolve_managed_file_path


def test_resolve_managed_file_path_global_relative(tmp_path: Path) -> None:
    global_root = tmp_path / "shared"

    resolved = resolve_managed_file_path("nested/data.csv", location="global", global_root=global_root)

    assert resolved == global_root / "nested" / "data.csv"


def test_resolve_managed_file_path_local_relative(tmp_path: Path) -> None:
    local_root = tmp_path / "projects" / "demo"

    resolved = resolve_managed_file_path("nested/data.csv", location="local", local_root=local_root)

    assert resolved == local_root / "nested" / "data.csv"


def test_resolve_managed_file_path_rejects_absolute(tmp_path: Path) -> None:
    absolute_file = tmp_path / "absolute.csv"

    with pytest.raises(ValueError, match="Absolute paths are not allowed"):
        resolve_managed_file_path(str(absolute_file), location="local", local_root=tmp_path / "ignored")


def test_resolve_managed_file_path_rejects_traversal(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="outside the managed root"):
        resolve_managed_file_path("../outside.csv", location="global", global_root=tmp_path / "shared")


def test_resolve_managed_file_path_rejects_symlink_escape(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    root = tmp_path / "shared"
    root.mkdir()
    (root / "linked").symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="outside the managed root"):
        resolve_managed_file_path("linked/data.csv", location="global", global_root=root)


def test_resolve_managed_file_path_allows_missing_parent_directories(tmp_path: Path) -> None:
    root = tmp_path / "shared"

    resolved = resolve_managed_file_path("new/nested/data.csv", location="global", global_root=root)

    assert resolved == root / "new" / "nested" / "data.csv"
    assert not resolved.exists()


def test_resolve_managed_file_path_requires_matching_root() -> None:
    with pytest.raises(ValueError, match="local_root required"):
        resolve_managed_file_path("data.csv", location="local")
