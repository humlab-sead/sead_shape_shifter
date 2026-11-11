"""Shared helpers for resolving managed file paths.

These helpers are intentionally framework-neutral so both Core and Backend
can reuse the same path-joining semantics without crossing layer boundaries.
"""

from pathlib import Path
from typing import Literal

from loguru import logger

FileLocation = Literal["global", "local"]


def _first_symlink_between(path: Path, stop: Path) -> Path | None:
    """Return the first symlink at or above ``path``, stopping at ``stop`` (exclusive of walking past it).

    Walks from ``path`` toward its parents and stops once ``stop`` or the filesystem
    root is reached, so symlinks outside the managed root are not reported.
    """
    current: Path = path
    while True:
        if current.is_symlink():
            return current
        if current in (stop, current.parent):
            return None
        current = current.parent


def resolve_contained_path(path: str | Path, root: str | Path, *, allow_absolute: bool = False) -> Path:
    """Resolve a path and require it to remain inside a managed root.

    Existing symlinks and symlinked parent directories are resolved before the
    containment check. The returned path may not exist yet, which allows the
    same check to protect file creation and file reads.

    When a symlink inside the managed root is followed, a warning names the
    symlink and its target. A symlink that points outside the root still fails
    containment, but the warning explains why a file that looks local was rejected.
    """
    requested_path = Path(path)
    if requested_path.is_absolute() and not allow_absolute:
        raise ValueError(f"Absolute paths are not allowed: {path}")

    resolved_root = Path(root).resolve()
    joined_path = resolved_root / requested_path
    resolved_path = joined_path.resolve()
    if resolved_path != joined_path:
        # The resolved path differs from the joined path, which means a symlink
        # was followed (or '..' segments were removed). Report only real symlinks.
        symlink = _first_symlink_between(joined_path, resolved_root)
        if symlink is not None:
            logger.warning(
                f"Path '{path}' under root '{root}' resolves through symlink '{symlink}', "
                f"which points to '{symlink.resolve()}'. "
                "Replace the symlink with a real file or directory copy if this path must stay inside the managed root."
            )
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
