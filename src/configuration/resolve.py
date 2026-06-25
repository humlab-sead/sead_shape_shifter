from __future__ import annotations

import copy
import re
from abc import abstractmethod
from pathlib import Path
from typing import Any, cast

import pandas as pd
from loguru import logger

from src.utility import dget, dotexists, env2dict, replace_env_vars

from .utility import is_config_path, is_path_to_existing_file, replace_references


def resolve_references(
    data: dict[str, Any],
    *,
    context: str | None = None,
    env_filename: str | None = None,
    env_prefix: str | None = None,
    runtime_root: str | Path | None = None,
    application_root_env_var: str = "APPLICATION_ROOT",
    source_path: str | None = None,
    inplace: bool = False,
    strict: bool = False,
    try_without_prefix: bool = True,
) -> dict[str, Any]:
    """Resolve configuration directives in the provided data dictionary.

    Note: This method does NOT mutate the input data parameter.
    It creates a deep copy to ensure the original remains unchanged.

    Environment variables are expected to already be loaded in os.environ.
    The env_filename parameter is kept for backward compatibility but not used.
    """
    if not inplace:
        data = copy.deepcopy(data)

    resolved_runtime_root = _resolve_runtime_root(runtime_root, env_prefix, application_root_env_var)

    for resolver_cls in [SubConfigResolver, LoadResolver]:
        data = resolver_cls(
            context=context,
            env_filename=env_filename,
            env_prefix=env_prefix,
            runtime_root=resolved_runtime_root,
            application_root_env_var=application_root_env_var,
            source_path=source_path,
        ).resolve(data)

    # Update data based on environment variables with a name that starts with `env_prefix`
    if env_prefix:
        data = env2dict(env_prefix, data)

    # Do a recursive replace of values with pattern "${ENV_NAME}" with value of environment
    data = cast(
        dict[str, Any],
        _replace_env_vars_with_runtime_paths(
            data,
            env_prefix=env_prefix,
            runtime_root=resolved_runtime_root,
            application_root_env_var=application_root_env_var,
            try_without_prefix=try_without_prefix,
        ),
    )
    data = replace_references(data)  # type: ignore

    if strict:
        unresolved: list[str] = find_unresolved_directives(data)
        if unresolved:
            paths: str = ", ".join(unresolved[:5])
            extra: str = "" if len(unresolved) <= 5 else f" (and {len(unresolved) - 5} more)"
            raise ValueError(f"Unresolved configuration directives at: {paths}{extra}")

    return data


def _resolve_runtime_root(runtime_root: str | Path | None, env_prefix: str | None, application_root_env_var: str) -> Path | None:
    """Return the base directory for env-derived relative paths."""
    if runtime_root:
        return Path(runtime_root).resolve()

    application_root = replace_env_vars(f"${{{application_root_env_var}}}", env_prefix=env_prefix or "", try_without_prefix=True)
    return Path(application_root).resolve() if application_root else None


def _is_path_env_var(env_var_name: str, env_prefix: str | None, application_root_env_var: str) -> bool:
    """Return True when an environment variable is expected to contain a path."""
    normalized_prefix = (env_prefix or "").rstrip("_")
    normalized_name = env_var_name
    if normalized_prefix and normalized_name.startswith(f"{normalized_prefix}_"):
        normalized_name = normalized_name[len(normalized_prefix) + 1 :]

    normalized_name = normalized_name.upper()
    return normalized_name == application_root_env_var.upper() or normalized_name.endswith(("_DIR", "_PATH", "_FILE", "_FILENAME"))


def _replace_env_vars_with_runtime_paths(
    data: dict[str, Any] | list[Any] | str,
    *,
    env_prefix: str | None,
    runtime_root: Path | None,
    application_root_env_var: str,
    try_without_prefix: bool,
) -> dict[str, Any] | list[Any] | str:
    """Replace environment variables and anchor path-like values to runtime_root."""
    if isinstance(data, dict):
        return {
            key: _replace_env_vars_with_runtime_paths(
                value,
                env_prefix=env_prefix,
                runtime_root=runtime_root,
                application_root_env_var=application_root_env_var,
                try_without_prefix=try_without_prefix,
            )
            for key, value in data.items()
        }
    if isinstance(data, list):
        return [
            _replace_env_vars_with_runtime_paths(
                value,
                env_prefix=env_prefix,
                runtime_root=runtime_root,
                application_root_env_var=application_root_env_var,
                try_without_prefix=try_without_prefix,
            )
            for value in data
        ]
    if not isinstance(data, str):
        return data

    def replacer(match: re.Match[str]) -> str:
        env_var_name = match.group(1)
        resolved_value = replace_env_vars(
            match.group(0),
            env_prefix=env_prefix or "",
            try_without_prefix=try_without_prefix,
        )
        if not resolved_value:
            return resolved_value
        if (
            runtime_root is not None
            and _is_path_env_var(env_var_name, env_prefix, application_root_env_var)
            and not Path(resolved_value).is_absolute()
        ):
            return str((runtime_root / resolved_value).resolve())
        return resolved_value

    return re.sub(r"\$\{([^}]+)\}", replacer, data)


def find_unresolved_directives(data: Any, path: str | None = None) -> list[str]:
    """Recursively find unresolved directive strings like @value:, @include:, @load:."""
    tags: list[str] = ["@value:", "@include", "@load"]
    hits: list[str] = []

    if isinstance(data, dict):
        for k, v in data.items():
            next_path = f"{path}.{k}" if path else str(k)
            hits.extend(find_unresolved_directives(v, next_path))
    elif isinstance(data, list):
        for idx, v in enumerate(data):
            next_path = f"{path}[{idx}]" if path else f"[{idx}]"
            hits.extend(find_unresolved_directives(v, next_path))
    elif isinstance(data, str):
        if any(tag in data for tag in tags):
            hits.append(f"{path or '<root>'}: {data}")

    return hits


class BaseResolver:
    """Base class for configuration resolvers.

    Resolvers process configuration data to resolve specific directives.
    Example directives include:
        - @include: to include sub-configuration files
        - @load: to load dictionary data from external CSV/TSV-files into the configuration
    """

    directive: str = ""

    def __init__(
        self,
        context: str | None = None,
        env_filename: str | None = None,
        env_prefix: str | None = None,
        runtime_root: str | Path | None = None,
        application_root_env_var: str = "APPLICATION_ROOT",
        source_path: str | None = None,
    ) -> None:
        self.context: str | None = context
        self.env_filename: str | None = env_filename
        self.env_prefix: str | None = env_prefix
        self.application_root_env_var: str = application_root_env_var
        self.runtime_root: Path | None = _resolve_runtime_root(runtime_root, env_prefix, application_root_env_var)
        self.source_path: str | None = source_path
        self.source_folder: Path | None = (
            Path(source_path).parent if source_path and is_config_path(source_path, raise_if_missing=False) else None
        )
        self.data: dict[str, Any] = {}

    def resolve(self, data: dict[str, Any]) -> dict[str, Any]:
        self.data = data
        return self._resolve(data, self.source_folder)

    def _resolve(self, value: Any, base_path: Path | None) -> Any:
        if isinstance(value, dict):
            return {k: self._resolve(v, base_path) for k, v in value.items()}
        if isinstance(value, list):
            return [self._resolve(v, base_path) for v in value]
        if isinstance(value, str) and value.startswith(self.directive):
            directive_argument: str = value[len(self.directive) :].lstrip(":").strip()  # Remove "@include:" prefix
            return self.resolve_directive(directive_argument, base_path)
        return value

    def _resolve_path(self, path: str, base_path: Path | None = None, raise_if_missing: bool = False) -> str:
        """Resolve a file path with environment variable expansion and relative path support.

        Supports partial replacement in paths (e.g., ${DATA_DIR}/subfolder/file.xlsx).

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

        # Step 1: Expand environment variables
        resolved_path: str = replace_env_vars(
            path,
            raise_if_unresolved=raise_if_missing,
            env_prefix=self.env_prefix,  # type: ignore
            try_without_prefix=True,
        )
        is_expanded: bool = resolved_path != path

        path_obj = Path(resolved_path)
        if path_obj.is_absolute():
            return str(path_obj)

        if is_expanded and self.runtime_root is not None:
            return str((self.runtime_root / path_obj).resolve())

        if is_expanded and self.env_filename:
            env_base_path = Path(self.env_filename).resolve().parent
            resolved_path = str(env_base_path / resolved_path)

        # Step 2: Handle absolute vs relative paths
        path_obj = Path(resolved_path)

        if path_obj.is_absolute():
            return str(path_obj)

        # Step 3: Resolve relative paths
        if base_path is not None:
            return str(base_path / resolved_path)

        return resolved_path

    @abstractmethod
    def resolve_directive(self, directive_argument: str, base_path: Path | None) -> dict[str, Any]:
        pass


class IncludeResolver(BaseResolver):
    """Load nested YAML configuration files referenced by @include.

    The directive argument is treated as a config file path. Relative paths are
    resolved against the current configuration file, and included files are
    resolved recursively so their own directives are processed too.

    Example:
        database: "@include:config/database.yml"
        api: "@include:config/api.yml"
    """

    directive: str = "@include"

    def __init__(
        self,
        context: str | None = None,
        env_filename: str | None = None,
        env_prefix: str | None = None,
        runtime_root: str | Path | None = None,
        application_root_env_var: str = "APPLICATION_ROOT",
        source_path: str | None = None,
    ) -> None:
        super().__init__(
            context=context,
            env_filename=env_filename,
            env_prefix=env_prefix,
            runtime_root=runtime_root,
            application_root_env_var=application_root_env_var,
            source_path=source_path,
        )

    def resolve_directive(self, directive_argument: str, base_path: Path | None) -> dict[str, Any]:
        """Resolve @include: directive with environment variable expansion.

        Supports:
        - Environment variables: @include: ${GLOBAL_DATA_SOURCE_DIR}/sead-options.yml
        - Relative paths: @include: ./reconciliation.yml
        - Absolute paths: @include: /abs/path/config.yml

        Args:
            directive_argument: Path after @include: prefix
            base_path: Directory of current file for resolving relative paths

        Returns:
            Loaded configuration dict
        """
        from .config import load_config  # pylint: disable=import-outside-toplevel

        # Resolve environment variables and paths
        filename: str = self._resolve_path(directive_argument, base_path=base_path, raise_if_missing=False)

        loaded_data: dict[str, Any] = load_config(
            source=filename,
            context=self.context,
            env_filename=self.env_filename,
            env_prefix=self.env_prefix,
            runtime_root=self.runtime_root,
            application_root_env_var=self.application_root_env_var,
        ).data
        return self._resolve(loaded_data, Path(filename).parent)


class LoadResolver(BaseResolver):

    directive: str = "@load"

    def __init__(
        self,
        context: str | None = None,
        env_filename: str | None = None,
        env_prefix: str | None = None,
        runtime_root: str | Path | None = None,
        application_root_env_var: str = "APPLICATION_ROOT",
        source_path: str | None = None,
    ) -> None:
        super().__init__(
            context=context,
            env_filename=env_filename,
            env_prefix=env_prefix,
            runtime_root=runtime_root,
            application_root_env_var=application_root_env_var,
            source_path=source_path,
        )

    def resolve_directive(self, directive_argument: str, base_path: Path | None) -> Any:
        """Resolve "@load: argument" directive with environment variable expansion.

        Supports loading CSV/TSV data from files with env var paths:
        - @load: ${DATA_DIR}/lookup.csv
        - @load: ./data/local.csv

        Args:
            directive_argument: Either 1) a file path or 2) a dotted config path to load options
            base_path: Directory of current file for resolving relative paths

        Returns:
            Loaded data as list of dicts, or directive_argument if load fails
        """

        filename: str
        sep: str

        if dotexists(self.data, directive_argument):
            opts: dict[str, Any] = dget(self.data, directive_argument)

            if not isinstance(opts, dict):
                logger.warning(f"ignoring load directive options for path '{directive_argument}' since it's not a dict")
                return directive_argument

            if "filename" not in opts:
                logger.warning(f"ignoring load directive for path '{directive_argument}' since no filename is specified in options")
                return directive_argument

            filename, sep = opts["filename"], opts.get("delimiter", ",")

        else:
            filename, sep = directive_argument, ","

        # Resolve environment variables and relative paths
        filename = self._resolve_path(filename, base_path=base_path, raise_if_missing=False)

        return self.load_file(filename, sep) or directive_argument

    def load_file(self, filename: str, sep: str) -> list[dict[Any, Any]] | None:
        """Load CSV/TSV file into a list of dictionaries."""
        loaded_data: list[dict[Any, Any]] | None = None
        if not is_path_to_existing_file(filename):
            logger.warning(f"file '{filename}' referenced in load directive does not exist")
            return None

        try:
            if filename.lower().endswith(".parquet"):
                loaded_data = pd.read_parquet(filename).to_dict(orient="records")
            else:
                loaded_data = pd.read_csv(filename, sep=sep, dtype=str).to_dict(orient="records")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"file '{filename}' referenced in load directive could not be parsed: {e}")
            return None

        return loaded_data

    def is_load_directive(self, value: Any) -> bool:
        """Check if the value is a load directive string."""
        return isinstance(value, str) and value.startswith(self.directive)
