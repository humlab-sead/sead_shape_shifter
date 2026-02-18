from __future__ import annotations

import contextlib
import copy
import io
from abc import abstractmethod
from datetime import datetime
from inspect import isclass
from os.path import join, normpath
from pathlib import Path
from typing import Any

import pandas as pd
import yaml
from dotenv import load_dotenv
from loguru import logger

from src.utility import dget, dotexists, dotset, env2dict, replace_env_vars

from .interface import ConfigLike
from .utility import replace_references

# pylint: disable=too-many-arguments


def yaml_str_join(loader: yaml.Loader, node: yaml.SequenceNode) -> str:
    return "".join([str(i) for i in loader.construct_sequence(node)])


def yaml_path_join(loader: yaml.Loader, node: yaml.SequenceNode) -> str:
    return join(*[str(i) for i in loader.construct_sequence(node)])


def nj(*paths: str) -> str | None:
    return normpath(join(*paths)) if None not in paths else None


def is_config_path(source: Any, raise_if_missing: bool = True) -> bool:
    """Test if the source is a valid path to a configuration file."""
    if not isinstance(source, str):
        return False
    if not source.endswith(".yaml") and not source.endswith(".yml"):
        return False
    if raise_if_missing and not Path(source).exists():
        raise FileNotFoundError(f"Configuration file not found: {source}")
    return True


def is_path_to_existing_file(path: Any) -> bool:
    """Test if the path is a valid path to an existing file."""
    with contextlib.suppress(FileNotFoundError, TypeError):
        return isinstance(path, str) and Path(path).is_file()
    return False


class SafeLoaderIgnoreUnknown(yaml.SafeLoader):  # pylint: disable=too-many-ancestors
    def let_unknown_through(self, node):  # pylint: disable=unused-argument
        """Ignore unknown tags silently"""
        if isinstance(node, yaml.ScalarNode):
            return self.construct_scalar(node)
        if isinstance(node, yaml.SequenceNode):
            return self.construct_sequence(node)
        if isinstance(node, yaml.MappingNode):
            return self.construct_mapping(node)
        return None


SafeLoaderIgnoreUnknown.add_constructor(None, SafeLoaderIgnoreUnknown.let_unknown_through)  # type: ignore
SafeLoaderIgnoreUnknown.add_constructor("!join", yaml_str_join)
SafeLoaderIgnoreUnknown.add_constructor("!jj", yaml_path_join)
SafeLoaderIgnoreUnknown.add_constructor("!path_join", yaml_path_join)


class Config(ConfigLike):
    """Container for configuration elements."""

    def __init__(
        self,
        *,
        data: dict[str, Any] | None = None,
        context: str = "default",
        filename: str | None = None,
        env_filename: str | None = None,
        env_prefix: str | None = None,
    ) -> None:
        self.data: dict[str, Any] = data or {}
        self.context: str = context
        self.filename: str | None = filename
        self.env_filename: str | None = env_filename
        self.env_prefix: str | None = env_prefix

    def get(self, *keys: str, default: Any | type[Any] = None, mandatory: bool = False) -> Any:
        if self.data is None:
            raise ValueError("Configuration not initialized")

        if mandatory and not self.exists(*keys):
            raise ValueError(f"Missing mandatory key: {'/'.join(keys)}")

        value: Any = dget(self.data, *keys)

        if value is not None:
            return value

        if callable(default) and not isinstance(default, type):
            return default()

        # Allow instance of class to be returned by calling default (parameterless) constructor
        return default() if isclass(default) else default

    def update(self, data: tuple[str, Any] | dict[str, Any] | list[tuple[str, Any]]) -> None:
        if self.data is None:
            self.data = {}
        items = [data] if isinstance(data, tuple) else data.items() if isinstance(data, dict) else data
        for key, value in items:
            dotset(self.data, key, value)

    def save(self, updates: dict[str, Any] | None = None) -> None:
        """Save configuration to the YAML file.

        This method preserves the raw YAML structure including @include:, @value:, and
        environment variables like ${VAR}. It only updates specific sections provided
        in the updates parameter.

        Args:
            updates: Dict of dotted paths to values to update (e.g., {"options:data_sources": {...}})
                    If None, saves self.data as-is (NOT RECOMMENDED for production use)
        """
        if not self.filename:
            raise ValueError("Cannot save configuration: no filename specified")

        file_path = Path(self.filename)

        # Create backup before saving
        if file_path.exists():

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = file_path.parent / f"{file_path.stem}.backup.{timestamp}{file_path.suffix}"
            backup_path.write_text(file_path.read_text(encoding="utf-8"), encoding="utf-8")
            logger.debug(f"Created backup at {backup_path}")

        # Read current raw YAML to preserve structure
        with open(self.filename, "r", encoding="utf-8") as f:
            raw_config = yaml.safe_load(f) or {}

        # Apply updates to raw config
        if updates:
            for key, value in updates.items():
                dotset(raw_config, key, value)
        else:
            # Fallback: save resolved data (will lose directives and env vars)
            logger.warning("Saving resolved configuration - env vars and directives will be expanded!")
            raw_config = self.data

        # Write updated configuration
        with open(self.filename, "w", encoding="utf-8") as f:
            yaml.dump(raw_config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

        logger.info(f"Saved configuration to {self.filename}")

    def exists(self, *keys: str) -> bool:
        return False if self.data is None else dotexists(self.data, *keys)

    def clone(self) -> Config:
        """Create a deep copy of the configuration."""
        return Config(
            data=copy.deepcopy(self.data),
            context=self.context,
            filename=self.filename,
            env_filename=self.env_filename,
            env_prefix=self.env_prefix,
        )

    def resolve(self) -> Config:
        """Resolve configuration directives in self.data."""
        self.data: dict[str, Any] = self.resolve_references(
            self.data,
            context=self.context,
            env_filename=self.env_filename,
            env_prefix=self.env_prefix,
            source_path=self.filename,
            inplace=True,
        )
        return self

    @staticmethod
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
            unresolved: list[str] = Config.find_unresolved_directives(data)
            if unresolved:
                paths: str = ", ".join(unresolved[:5])
                extra: str = "" if len(unresolved) <= 5 else f" (and {len(unresolved) - 5} more)"
                raise ValueError(f"Unresolved configuration directives at: {paths}{extra}")

        return data

    @staticmethod
    def find_unresolved_directives(data: Any, path: str | None = None) -> list[str]:
        """Recursively find unresolved directive strings like @value:, @include:, @load:."""
        tags: list[str] = ["@value:", "@include", "@load"]
        hits: list[str] = []

        if isinstance(data, dict):
            for k, v in data.items():
                next_path = f"{path}.{k}" if path else str(k)
                hits.extend(Config.find_unresolved_directives(v, next_path))
        elif isinstance(data, list):
            for idx, v in enumerate(data):
                next_path = f"{path}[{idx}]" if path else f"[{idx}]"
                hits.extend(Config.find_unresolved_directives(v, next_path))
        elif isinstance(data, str):
            if any(tag in data for tag in tags):
                hits.append(f"{path or '<root>'}: {data}")

        return hits


class ConfigFactory:
    """Factory for creating Config instances."""

    def load(
        self,
        *,
        source: str | dict[str, Any] | ConfigLike | None = None,
        context: str | None = None,
        env_filename: str | None = None,
        env_prefix: str | None = None,
        skip_resolve: bool = False,
    ) -> Config | ConfigLike:

        load_dotenv(dotenv_path=env_filename)

        if isinstance(source, (Config, ConfigLike)):
            return source

        filename: str | None = source if isinstance(source, str) and is_config_path(source, raise_if_missing=False) else None

        if source is None:
            source = {}

        data: dict[str, Any] = (
            (
                yaml.load(
                    Path(source).read_text(encoding="utf-8"),
                    Loader=SafeLoaderIgnoreUnknown,
                )
                if is_config_path(source, raise_if_missing=True)
                else yaml.load(io.StringIO(source), Loader=SafeLoaderIgnoreUnknown)
            )
            if isinstance(source, str)
            else source
        ) or {}

        assert isinstance(data, dict)

        if not skip_resolve:
            data = Config.resolve_references(
                data,
                context=context,
                env_filename=env_filename,
                env_prefix=env_prefix,
                source_path=filename,
            )

        return Config(
            data=data,
            context=context or "default",
            filename=filename,
            env_filename=env_filename,
            env_prefix=env_prefix,
        )


class BaseResolver:
    """Base class for configuration resolvers.

    Resolvers process configuration data to resolve specific directives.
    Example directives include:
        - @include: to include sub-configuration files
        - @load: to load dictionary data from external CSV/TSV-files into the configuration
    """

    directive: str = ""

    def __init__(
        self, context: str | None = None, env_filename: str | None = None, env_prefix: str | None = None, source_path: str | None = None
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
        if path != resolved_path:
            # If the path was changed by env var replacement = treat it as an absolute path
            # (env vars are typically used for absolute paths), otherwise resolve relative to base_path
            resolved_path = str(Path(resolved_path).absolute())

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
        # Resolve environment variables and paths
        filename: str = self._resolve_path(directive_argument, base_path=base_path, raise_if_missing=False)

        loaded_data: dict[str, Any] = (
            ConfigFactory().load(source=filename, context=self.context, env_filename=self.env_filename, env_prefix=self.env_prefix).data
        )
        return self._resolve(loaded_data, Path(filename).parent)


class LoadResolver(BaseResolver):

    directive: str = "@load"

    def __init__(
        self, context: str | None = None, env_filename: str | None = None, env_prefix: str | None = None, source_path: str | None = None
    ) -> None:
        super().__init__(context=context, env_filename=env_filename, env_prefix=env_prefix, source_path=source_path)

    def resolve_directive(self, directive_argument: str, base_path: Path | None) -> Any:
        """Resolve @load: directive with environment variable expansion.

        Supports loading CSV/TSV data from files with env var paths:
        - @load: ${DATA_DIR}/lookup.csv
        - @load: ./data/local.csv

        Args:
            directive_argument: Either a file path or a dotted config path to load options
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

        if not is_path_to_existing_file(filename):
            logger.warning(f"ignoring load directive for path '{directive_argument}' since file '{filename}' does not exist")
            return directive_argument

        try:
            loaded_data: list[dict[Any, Any]] = pd.read_csv(filename, sep=sep, dtype=str).to_dict(orient="records")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"ignoring load directive for path '{directive_argument}' since file '{filename}' could not be parsed: {e}")
            return directive_argument

        return loaded_data
