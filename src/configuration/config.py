from __future__ import annotations

import contextlib
import io
from abc import abstractmethod
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
    ) -> None:
        self.data: dict[str, Any] = data or {}
        self.context: str = context
        self.filename: str | None = filename

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

    def exists(self, *keys: str) -> bool:
        return False if self.data is None else dotexists(self.data, *keys)


class ConfigFactory:
    """Factory for creating Config instances."""

    def load(
        self,
        *,
        source: str | dict[str, Any] | ConfigLike | None = None,
        context: str | None = None,
        env_filename: str | None = None,
        env_prefix: str | None = None,
    ) -> Config | ConfigLike:

        load_dotenv(dotenv_path=env_filename)

        if isinstance(source, (Config, ConfigLike)):
            return source

        source_path: str | None = source if isinstance(source, str) and is_config_path(source, raise_if_missing=False) else None

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
        )

        # Handle empty YAML files (loads as None)
        if data is None:
            data = {}

        assert isinstance(data, dict)

        # Resolve sub-configurations by loading referenced files recursively

        for resolver_cls in [SubConfigResolver, LoadResolver]:
            data = resolver_cls(context=context, env_filename=env_filename, env_prefix=env_prefix, source_path=source_path).resolve(data)

        # Update data based on environment variables with a name that starts with `env_prefix`
        if env_prefix:
            data = env2dict(env_prefix, data)

        # Do a recursive replace of values with pattern "${ENV_NAME}" with value of environment
        data = replace_env_vars(data)  # type: ignore
        data = replace_references(data)  # type: ignore

        return Config(
            data=data,
            context=context or "default",
            filename=source if isinstance(source, str) and is_config_path(source) else None,
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
        filename: str = directive_argument
        if not Path(filename).is_absolute() and base_path is not None:
            filename = str(base_path / filename)
        loaded_data: dict[str, Any] = (
            ConfigFactory().load(source=filename, context=self.context, env_filename=self.env_filename, env_prefix=None).data
        )
        return self._resolve(loaded_data, Path(filename).parent)


class LoadResolver(BaseResolver):

    directive: str = "@load"

    def __init__(
        self, context: str | None = None, env_filename: str | None = None, env_prefix: str | None = None, source_path: str | None = None
    ) -> None:
        super().__init__(context=context, env_filename=env_filename, env_prefix=env_prefix, source_path=source_path)

    def resolve_directive(self, directive_argument: str, base_path: Path | None) -> Any:

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

        if not Path(filename).is_absolute() and base_path is not None:
            filename = str(base_path / filename)

        if not is_path_to_existing_file(filename):
            logger.warning(f"ignoring load directive for path '{directive_argument}' since file '{filename}' does not exist")
            return directive_argument

        try:
            loaded_data: list[dict[Any, Any]] = pd.read_csv(filename, sep=sep, dtype=str).to_dict(orient="records")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"ignoring load directive for path '{directive_argument}' since file '{filename}' could not be parsed: {e}")
            return directive_argument

        return loaded_data
