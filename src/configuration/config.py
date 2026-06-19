from __future__ import annotations

import copy
import io
from datetime import datetime
from inspect import isclass
from os.path import join, normpath
from pathlib import Path
from typing import Any, Protocol, Type, runtime_checkable

import yaml
from dotenv import load_dotenv
from loguru import logger

from src.utility import dget, dotexists, dotset

from .resolve import resolve_references
from .utility import is_config_path

# pylint: disable=too-many-arguments, unused-argument


@runtime_checkable
class ConfigLike(Protocol):
    filename: str | None
    data: dict[str, Any]

    def get(self, *keys: str, default: Any | Type[Any] = None, mandatory: bool = False) -> Any: ...
    def exists(self, *keys: str) -> bool: ...
    def update(self, data: tuple[str, Any] | dict[str, Any] | list[tuple[str, Any]]) -> None: ...
    def save(self, updates: dict[str, Any] | None = None) -> None: ...


def yaml_str_join(loader: yaml.Loader, node: yaml.SequenceNode) -> str:
    return "".join([str(i) for i in loader.construct_sequence(node)])


def yaml_path_join(loader: yaml.Loader, node: yaml.SequenceNode) -> str:
    return join(*[str(i) for i in loader.construct_sequence(node)])


def nj(*paths: str) -> str | None:
    return normpath(join(*paths)) if None not in paths else None


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
        self.data: dict[str, Any] = resolve_references(
            self.data,
            context=self.context,
            env_filename=self.env_filename,
            env_prefix=self.env_prefix,
            source_path=self.filename,
            inplace=True,
        )
        return self


def load_config(
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
        data = resolve_references(
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
