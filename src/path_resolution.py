"""Shared helpers for resolving managed file paths.

These helpers are intentionally framework-neutral so both Core and Backend
can reuse the same path-joining semantics without crossing layer boundaries.
"""

from pathlib import Path
from typing import Literal

FileLocation = Literal["global", "local"]


def resolve_contained_path(path: str | Path, root: str | Path, *, allow_absolute: bool = False) -> Path:
    """Resolve a path and require it to remain inside a managed root.

    Existing symlinks and symlinked parent directories are resolved before the
    containment check. The returned path may not exist yet, which allows the
    same check to protect file creation and file reads.
    """
    requested_path = Path(path)
    if requested_path.is_absolute() and not allow_absolute:
        raise ValueError(f"Absolute paths are not allowed: {path}")

    resolved_root = Path(root).resolve()
    resolved_path = (resolved_root / requested_path).resolve()
    if not resolved_path.is_relative_to(resolved_root):
        raise ValueError(f"Path is outside the managed root: {path}")

    return resolved_path


def resolve_managed_file_path(
    filename: str,
    *,
    location: FileLocation,
    global_root: str | Path | None = None,
    local_root: str | Path | None = None,
) -> Path:
    """Resolve a managed file path against the configured global or local root."""

    if location == "global":
        if global_root is None:
            raise ValueError(f"global_root required for global file resolution: {filename}")
        return resolve_contained_path(filename, global_root)

    if location == "local":
        if local_root is None:
            raise ValueError(f"local_root required for local file resolution: {filename}")
        return resolve_contained_path(filename, local_root)

    raise ValueError(f"Invalid location: {location}. Must be 'global' or 'local'")
