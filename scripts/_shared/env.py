"""Environment-file helpers shared by the command-line scripts.

Two different policies appear in the scripts, so they stay separate functions:

* :func:`apply_env_files` merges whole files into ``os.environ`` with a
  per-file override flag. The profiling scripts use it to layer a shared test
  environment under a local override file.
* :func:`load_local_env` copies only named keys from one file. The release-note
  generators use it so that provider settings in ``.env`` reach the generators
  without loading unrelated values.
"""

from __future__ import annotations

import os
from collections.abc import Container, Sequence
from pathlib import Path

from dotenv import dotenv_values


def apply_env_files(files: Sequence[tuple[Path, bool]]) -> None:
    """Merge environment files into ``os.environ``.

    Each entry is ``(path, override)``. With ``override`` set, values from that
    file replace values already in the environment; without it, an existing
    value wins. Entries are applied in order, so a later file overrides an
    earlier one. Missing files contribute nothing.
    """
    for path, override in files:
        for name, value in dotenv_values(path).items():
            if value is not None and (override or name not in os.environ):
                os.environ[name] = value


def load_local_env(env_path: Path, allowed_keys: Container[str]) -> None:
    """Copy selected ``KEY=VALUE`` lines from a file into ``os.environ``.

    Reads the file directly instead of using python-dotenv, because an
    environment file in this repository may contain values with spaces or
    surrounding quotes that should be kept as written. Lines that are blank, are
    comments, or hold a key outside ``allowed_keys`` are skipped. A key already
    present in the environment is left alone, so an exported value wins over the
    file. A missing file, or an unreadable one, adds nothing.

    Callers pass their own ``allowed_keys`` so the script keeps stating which
    settings it is willing to read.
    """
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        if key not in allowed_keys or key in os.environ:
            continue

        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]

        os.environ[key] = value
