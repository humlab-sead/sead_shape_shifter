"""Helpers shared by the repository's command-line scripts.

The folders under ``scripts/`` hold scripts that are run directly by path, by
``make``, or by CI. Running a script by path does not put the repository root on
``sys.path``, and several scripts read the same environment files. This package
holds those two pieces of plumbing so each script states its own behaviour
instead of repeating it.
"""

from scripts._shared.env import apply_env_files, load_local_env
from scripts._shared.paths import REPO_ROOT, add_repository_to_sys_path

__all__ = ["REPO_ROOT", "add_repository_to_sys_path", "apply_env_files", "load_local_env"]
