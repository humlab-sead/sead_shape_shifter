"""Path resolution utilities for paths that can include environment variables and relative paths."""

import os
import re
from pathlib import Path


class PathResolver:
    """Resolves file paths that can include environment variables and relative paths.

    Resolution priority:
    1. Expand environment variables (${VAR} syntax) using os.getenv()
    2. If path is absolute, return as-is
    3. If path is relative and base_path provided, resolve relative to base_path
    4. Otherwise return path as-is

    Environment variables are resolved using os.getenv().
    """

    @classmethod
    def _expand_env_vars(cls, path: str, raise_if_missing: bool = False) -> str:
        """Expand ${VAR} environment variables in path using os.getenv().

        Unlike replace_env_vars() from src.utility which only handles complete
        variable values, this function handles partial replacements in paths
        like ${GLOBAL_DATA_DIR}/subfolder/file.xlsx.

        Args:
            path: Path string potentially containing ${VAR} references
            raise_if_missing: If True, raises ValueError for missing env vars

        Returns:
            Path with environment variables expanded
            
        Raises:
            ValueError: If raise_if_missing=True and env var is not set
        """
        # First check for missing vars if requested
        if raise_if_missing:
            var_names = re.findall(r"\$\{([^}]+)\}", path)
            missing_vars = [var for var in var_names if var not in os.environ]
            if missing_vars:
                raise ValueError(f"Unresolved environment variables in path '{path}': {', '.join(missing_vars)}")

        def replace_var(match: re.Match) -> str:
            var_name = match.group(1)
            return os.getenv(var_name, "")

        return re.sub(r"\$\{([^}]+)\}", replace_var, path)

    @classmethod
    def resolve(cls, path: str, base_path: Path | None = None, raise_if_missing: bool = False) -> str:
        """Resolve a file path with environment variable expansion and relative path support.

        Supports partial replacement in paths (e.g., ${GLOBAL_DATA_DIR}/subfolder/file.xlsx).

        Args:
            path: Path string potentially containing ${VAR} references
            base_path: Base directory for resolving relative paths
            raise_if_missing: If True, raise ValueError for unresolved env vars

        Returns:
            Resolved absolute path string

        Raises:
            ValueError: If raise_if_missing=True and env var cannot be resolved
        """
        if not path:
            return path

        # Step 1: Expand environment variables (will raise if missing and raise_if_missing=True)
        resolved_path: str = cls._expand_env_vars(path, raise_if_missing=raise_if_missing)

        # Step 2: Handle absolute vs relative paths
        path_obj = Path(resolved_path)

        if path_obj.is_absolute():
            return str(path_obj)

        # Step 3: Resolve relative paths
        if base_path is not None:
            return str(base_path / resolved_path)

        return resolved_path
