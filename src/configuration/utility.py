import contextlib
import io
import json
from os.path import join, normpath
from pathlib import Path
from typing import Any

import pandas as pd
import yaml
from loguru import logger


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


def load_yaml_file(source: dict[str, Any] | str) -> dict[str, Any] | None:
    """Load a YAML file into a dictionary or list."""

    if isinstance(source, str):

        if is_yaml_file(source, raise_if_missing=True):
            return yaml.load(Path(source).read_text(encoding="utf-8"), Loader=SafeLoaderIgnoreUnknown)

        return yaml.load(io.StringIO(source), Loader=SafeLoaderIgnoreUnknown)

    if isinstance(source, (dict, list)):
        return source

    return {}


def is_yaml_file(source: Any, raise_if_missing: bool = True) -> bool:
    """Test if the source is a valid path to a YAML file."""
    if not isinstance(source, str):
        return False
    if not source.endswith(".yaml") and not source.endswith(".yml"):
        return False
    if raise_if_missing and not Path(source).exists():
        raise FileNotFoundError(f"YAML file not found: {source}")
    return True


def load_data_file(filename: str, sep: str) -> dict[Any, Any] | list[dict[Any, Any]] | None:
    """Load JSON, CSV, TSV, or Parquet file into a list of dictionaries."""
    loaded_data: dict[Any, Any] | list[dict[Any, Any]] | None = None
    if not is_path_to_existing_file(filename):
        logger.warning(f"file '{filename}' referenced in load directive does not exist")
        return None

    try:
        if filename.lower().endswith("json"):
            loaded_data = json.loads(Path(filename).read_text(encoding="utf-8"))
        elif filename.lower().endswith("yaml") or filename.lower().endswith("yml"):
            loaded_data = load_yaml_file(filename)
        elif filename.lower().endswith(".parquet"):
            loaded_data = pd.read_parquet(filename).to_dict(orient="records")
        else:
            loaded_data = pd.read_csv(filename, sep=sep, dtype=str).to_dict(orient="records")
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.warning(f"file '{filename}' referenced in load directive could not be parsed: {e}")
        return None

    return loaded_data


def is_path_to_existing_file(path: Any) -> bool:
    """Test if the path is a valid path to an existing file."""
    with contextlib.suppress(FileNotFoundError, TypeError):
        return isinstance(path, str) and Path(path).is_file()
    return False
