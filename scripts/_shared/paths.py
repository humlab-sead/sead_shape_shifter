"""Repository paths shared by the command-line scripts."""

from __future__ import annotations

from pathlib import Path

# This file lives at scripts/_shared/paths.py, so three parents up is the
# repository root. Deriving it here means a script can move between the
# scripts/ subfolders without changing its own root calculation.
REPO_ROOT: Path = Path(__file__).resolve().parents[2]
