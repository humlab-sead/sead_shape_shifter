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


def test_resolve_managed_file_path_preserves_absolute(tmp_path: Path) -> None:
    absolute_file = tmp_path / "absolute.csv"

    resolved = resolve_managed_file_path(str(absolute_file), location="local", local_root=tmp_path / "ignored")

    assert resolved == absolute_file


def test_resolve_managed_file_path_requires_matching_root() -> None:
    with pytest.raises(ValueError, match="local_root required"):
        resolve_managed_file_path("data.csv", location="local")