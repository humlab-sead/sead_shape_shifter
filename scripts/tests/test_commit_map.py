from __future__ import annotations

from pathlib import Path

import pytest

from scripts._shared.commit_map import COMMIT_MAP_PATH, load_commit_map, translate_commit

OLD_HASH = "a" * 40
NEW_HASH = "b" * 40


def write_map(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "commit_map.txt"
    path.write_text(content, encoding="utf-8")
    return path


def test_translate_commit_returns_new_hash_for_mapped_commit(tmp_path: Path) -> None:
    path = write_map(tmp_path, f"# header\n\n{OLD_HASH} {NEW_HASH}\n")

    assert translate_commit(OLD_HASH, path) == NEW_HASH


def test_translate_commit_returns_unmapped_hash_unchanged(tmp_path: Path) -> None:
    path = write_map(tmp_path, f"{OLD_HASH} {NEW_HASH}\n")

    assert translate_commit("c" * 40, path) == "c" * 40


def test_load_commit_map_returns_empty_map_for_missing_file(tmp_path: Path) -> None:
    assert not load_commit_map(tmp_path / "missing.txt")


def test_load_commit_map_rejects_malformed_line(tmp_path: Path) -> None:
    path = write_map(tmp_path, f"{OLD_HASH}\n")

    with pytest.raises(ValueError, match=":1: expected"):
        load_commit_map(path)


def test_committed_commit_map_translates_a_known_pre_rewrite_merge_commit() -> None:
    # Merge commit of PR #785 as GitHub recorded it before the 2026-11-23 rewrite.
    assert translate_commit("64409bf54e716e5c39f4112e9ea6db1d732042c7") == "c4e54960f29cd4407fd8077dd65866c3bbd1ebda"
    assert COMMIT_MAP_PATH.is_file()
