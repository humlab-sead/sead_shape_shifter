"""Repository paths shared by the command-line scripts."""

from __future__ import annotations

import sys
from pathlib import Path

# This file lives at scripts/_shared/paths.py, so three parents up is the
# repository root. Deriving it here means a script can move between the
# scripts/ subfolders without changing its own root calculation.
REPO_ROOT: Path = Path(__file__).resolve().parents[2]


def add_repository_to_sys_path() -> Path:
    """Put the repository root first on ``sys.path`` and return it.

    Scripts import the ``src`` and ``backend`` packages, which resolve from the
    repository root. A script started by path has only its own directory on
    ``sys.path``, so it calls this before its first project import.

    The call is safe to repeat and does not reorder an existing entry.
    """
    root = str(REPO_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)
    return REPO_ROOT
