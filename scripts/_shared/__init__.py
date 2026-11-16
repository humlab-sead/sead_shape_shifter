"""Helpers shared by the repository's command-line scripts.

Import from the concrete module rather than this package, so a script that only
needs the repository root does not pull in the environment-file dependencies:

    from scripts._shared.paths import REPO_ROOT
    from scripts._shared.env import apply_env_files

The folders under ``scripts/`` hold scripts that are run by ``make``, by CI, or
by path inside the project environment.
"""
