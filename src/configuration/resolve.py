from __future__ import annotations

import contextlib
import copy
import io
from abc import abstractmethod
from datetime import datetime
from inspect import isclass
from os.path import join, normpath
from pathlib import Path
from typing import Any, Protocol, Type, runtime_checkable

import pandas as pd
import yaml
from dotenv import load_dotenv
from loguru import logger

from src.utility import dget, dotexists, dotset, env2dict, replace_env_vars

from .utility import is_config_path, is_path_to_existing_file, replace_references


def resolve_references(
    data: dict[str, Any],
    *,
    context: str | None = None,
    env_filename: str | None = None,
    env_prefix: str | None = None,
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

    for resolver_cls in [SubConfigResolver, LoadResolver]:
        data = resolver_cls(
            context=context,
            env_filename=env_filename,
            env_prefix=env_prefix,
            source_path=source_path,
        ).resolve(data)

    # Update data based on environment variables with a name that starts with `env_prefix`
    if env_prefix:
        data = env2dict(env_prefix, data)

    # Do a recursive replace of values with pattern "${ENV_NAME}" with value of environment
    data = replace_env_vars(data, env_prefix=env_prefix, try_without_prefix=try_without_prefix)  # type: ignore
    data = replace_references(data)  # type: ignore

    if strict:
        unresolved: list[str] = find_unresolved_directives(data)
        if unresolved:
            paths: str = ", ".join(unresolved[:5])
            extra: str = "" if len(unresolved) <= 5 else f" (and {len(unresolved) - 5} more)"
            raise ValueError(f"Unresolved configuration directives at: {paths}{extra}")

    return data


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
        source_path: str | None = None,
    ) -> None:
        self.context: str | None = context
        self.env_filename: str | None = env_filename
        self.env_prefix: str | None = env_prefix
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

        path_obj = Path(resolved_path)
        if path != resolved_path and not path_obj.is_absolute() and self.env_filename:
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


class SubConfigResolver(BaseResolver):
    """Recursively resolve sub-configurations referenced in the main configuration.

    A sub-config is referenced using the @include: prefix, e.g. "@include:path/to/subconfig.yaml"
    Relative paths are resolved relative to the main configuration folder.
    Sub-configs can themselves reference further sub-configs.

    Example:
        database: "@include:config/database.yml"
        api: "@include:config/api.yml"
    """

    directive: str = "@include"

    def __init__(
        self, context: str | None = None, env_filename: str | None = None, env_prefix: str | None = None, source_path: str | None = None
    ) -> None:
        super().__init__(context=context, env_filename=env_filename, env_prefix=env_prefix, source_path=source_path)

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
            source=filename, context=self.context, env_filename=self.env_filename, env_prefix=self.env_prefix
        ).data
        return self._resolve(loaded_data, Path(filename).parent)


class LoadResolver(BaseResolver):

    directive: str = "@load"

    def __init__(
        self, context: str | None = None, env_filename: str | None = None, env_prefix: str | None = None, source_path: str | None = None
    ) -> None:
        super().__init__(context=context, env_filename=env_filename, env_prefix=env_prefix, source_path=source_path)

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
