"""Shared helpers for resolving managed file paths.

These helpers are intentionally framework-neutral so both Core and Backend
can reuse the same path-joining semantics without crossing layer boundaries.
"""

from pathlib import Path
from typing import Literal


FileLocation = Literal["global", "local"]


def resolve_managed_file_path(
    filename: str,
    *,
    location: FileLocation,
    global_root: str | Path | None = None,
    local_root: str | Path | None = None,
) -> Path:
    """Resolve a managed file path against the configured global or local root.

    Absolute filenames are returned unchanged. Relative filenames are joined
    against the root implied by `location`.
    """

    file_path = Path(filename)
    if file_path.is_absolute():
        return file_path

    if location == "global":
        if global_root is None:
            raise ValueError(f"global_root required for global file resolution: {filename}")
        return Path(global_root) / file_path

    if location == "local":
        if local_root is None:
            raise ValueError(f"local_root required for local file resolution: {filename}")
        return Path(local_root) / file_path

    raise ValueError(f"Invalid location: {location}. Must be 'global' or 'local'")