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

from src.utility import dget, dotexists, dotset, env2dict

from .resolve import resolve_directives
from .utility import is_yaml_file, load_yaml_file

# pylint: disable=too-many-arguments, unused-argument


@runtime_checkable
class ConfigLike(Protocol):
    filename: str | None
    data: dict[str, Any]

    def get(self, *keys: str, default: Any | Type[Any] = None, mandatory: bool = False) -> Any: ...
    def exists(self, *keys: str) -> bool: ...
    def update(self, data: tuple[str, Any] | dict[str, Any] | list[tuple[str, Any]]) -> None: ...
    def save(self, updates: dict[str, Any] | None = None) -> None: ...
    def resolve(self, skip_resolve: bool = False) -> ConfigLike: ...


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
        runtime_root: str | Path | None = None,
        application_root_env_var: str = "APPLICATION_ROOT",
    ) -> None:
        self.data: dict[str, Any] = data or {}
        self.context: str = context
        self.filename: str | None = filename
        self.env_filename: str | None = env_filename
        self.env_prefix: str | None = env_prefix
        self.runtime_root: str | Path | None = runtime_root
        self.application_root_env_var: str = application_root_env_var

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

        This method preserves the raw YAML structure including @include:, @load:, @value:, and
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
            runtime_root=self.runtime_root,
            application_root_env_var=self.application_root_env_var,
        )

    def resolve(self, skip_resolve: bool = False) -> Config:
        """Resolve configuration directives in self.data."""
        if not skip_resolve:
            self.data: dict[str, Any] = resolve_directives(
                self.data,
                env_filename=self.env_filename,
                env_prefix=self.env_prefix,
                runtime_root=self.runtime_root,
                application_root_env_var=self.application_root_env_var,
                source_path=self.filename,
                inplace=True,
            )
            if self.env_prefix:
                self.data = env2dict(self.env_prefix, self.data)
        return self


def load_config(
    *,
    source: str | dict[str, Any] | ConfigLike | None = None,
    context: str | None = None,
    env_filename: str | None = None,
    env_prefix: str | None = None,
    runtime_root: str | Path | None = None,
    application_root_env_var: str = "APPLICATION_ROOT",
    skip_resolve: bool = False,
) -> Config | ConfigLike:

    load_dotenv(dotenv_path=env_filename)

    if isinstance(source, (Config, ConfigLike)):
        return source

    filename: str | None = source if isinstance(source, str) and is_yaml_file(source, raise_if_missing=False) else None

    data: dict[str, Any] | str | None = load_yaml_file(source or {})

    assert isinstance(data, dict)

    return Config(
        data=data,
        context=context or "default",
        filename=filename,
        env_filename=env_filename,
        env_prefix=env_prefix,
        runtime_root=runtime_root,
        application_root_env_var=application_root_env_var,
    ).resolve(skip_resolve=skip_resolve)
