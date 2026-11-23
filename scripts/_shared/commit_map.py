"""Translates commit hashes recorded before the 2026-11-23 history rewrite.

On 2026-11-23 ``git filter-repo`` removed ``graphify-out/`` from the repository
history. Every commit made after 2026-06-11 got a new hash. GitHub still reports
the old hash as the merge commit of each pull request merged before the rewrite,
so a script that compares those merge commits with ``git rev-list`` output must
translate them first. Hashes that are not in the map, including every commit
made after the rewrite, are returned unchanged.

Uses only the standard library.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

COMMIT_MAP_PATH: Path = Path(__file__).with_name("history_rewrite_commit_map.txt")


@lru_cache(maxsize=None)
def load_commit_map(path: Path = COMMIT_MAP_PATH) -> dict[str, str]:
    """Reads ``old new`` hash pairs from ``path``, one pair per line.

    Blank lines and lines starting with ``#`` are skipped. Returns an empty map
    when the file does not exist. Raises ``ValueError`` for a line that does not
    hold exactly two hashes.
    """
    if not path.is_file():
        return {}

    mapping: dict[str, str] = {}
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) != 2:
            raise ValueError(f"{path}:{line_number}: expected 'old_hash new_hash', got {raw_line!r}")
        old_hash, new_hash = parts
        mapping[old_hash] = new_hash
    return mapping


def translate_commit(commit_hash: str, path: Path = COMMIT_MAP_PATH) -> str:
    """Returns the current hash for a commit recorded before the history rewrite.

    A hash that is not in the map is returned as given.
    """
    return load_commit_map(path).get(commit_hash, commit_hash)
