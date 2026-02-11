import importlib
import os
import pkgutil
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any, Callable, Generic, Literal, Self, TypeVar

import pandas as pd
import yaml
from loguru import logger


def sanitize_column_name(col: Any, index: int, max_length: int = 48) -> str:
    """Convert column name to YAML-friendly format.
    
    Rules:
    - Convert to lowercase
    - Replace spaces with underscores
    - Replace special characters with meaningful names (±, σ, δ, etc.)
    - Remove punctuation (., , ; : etc.)
    - Handle parentheses by replacing with underscores
    - Avoid consecutive underscores
    - Handle None/NaN as "unnamed_N"
    - Skip Excel formulas (starting with "=")
    - Truncate very long names to max_length
    - Final safety: only keep a-z, 0-9, underscore
    
    Args:
        col: Column name (can be str, None, or any type)
        index: Column index for fallback naming
        max_length: Maximum length for column names (default: 48)
        
    Returns:
        Sanitized column name
    """
    # Handle None, NaN, or empty strings
    if col is None or (isinstance(col, float) and pd.isna(col)) or str(col).strip() == "":
        return f"unnamed_{index}"
    
    # Convert to string and trim whitespace
    name: str = str(col).strip()
    
    # Skip Excel formulas (starting with "=") or very long strings (likely formulas)
    # Use a generous threshold - anything over 200 chars is probably a formula
    if name.startswith("=") or len(name) > 200:
        return f"unnamed_{index}"
    
    # Special character replacements (order matters - do specific ones first)
    replacements: dict[str, str] = {
        "±": "plus_minus",
        "δ": "delta",
        "σ": "sigma",
        "μ": "mu",
        "α": "alpha",
        "β": "beta",
        "γ": "gamma",
        "Δ": "delta",
        "Σ": "sigma",
        "π": "pi",
        "°": "degree",
        "º": "degree",
        "%": "percent",
        "#": "num",
        "&": "and",
        "@": "at",
        "$": "dollar",
        "€": "euro",
        "£": "pound",
    }
    
    for char, replacement in replacements.items():
        name = name.replace(char, f"_{replacement}_")
    
    # Replace parentheses and brackets with underscores
    name = re.sub(r"[\(\)\[\]\{\}]", "_", name)
    
    # Remove punctuation (., , ; : ! ? ' " etc.)
    name = re.sub(r"[.,;:!?'\"\\\|\-/]", "", name)
    
    # Replace any remaining whitespace with underscores
    name = re.sub(r"\s+", "_", name)
    
    # Convert to lowercase
    name = name.lower()
    
    # Final safety: remove any remaining non-safe characters
    # Only keep: a-z, 0-9, underscore
    name = re.sub(r"[^a-z0-9_]", "", name)
    
    # Remove consecutive underscores and trim
    name = re.sub(r"_+", "_", name)
    name = name.strip("_")
    
    # Truncate to maximum length if needed
    if len(name) > max_length:
        name = name[:max_length].rstrip("_")
    
    # If name is empty after sanitization, use index
    if not name:
        name = f"unnamed_{index}"
    
    # Ensure it doesn't start with a number (YAML key requirement)
    if name[0].isdigit():
        name = f"col_{name}"
    
    return name


def sanitize_columns(columns: list[Any]) -> list[str]:
    """Sanitize a list of column names, ensuring uniqueness.
    
    Args:
        columns: List of column names (can contain None, duplicates, etc.)
        
    Returns:
        List of sanitized, unique column names
    """
    sanitized: list[str] = [sanitize_column_name(col, i) for i, col in enumerate(columns)]
    
    # Handle duplicates by adding suffixes
    seen: dict[str, int] = {}
    result = []
    
    for col in sanitized:
        if col in seen:
            seen[col] += 1
            result.append(f"{col}_{seen[col]}")
        else:
            seen[col] = 0
            result.append(col)
    
    return result


def rename_last_occurence(data: pd.DataFrame, rename_map: dict[str, str]) -> list[str]:
    """Rename the last occurrence of each source column in rename_map to the new name."""
    target_columns: list[str] = data.columns.tolist()
    for src, new in rename_map.items():
        if src not in target_columns:
            continue
        if new in target_columns:
            continue
        for i in range(len(target_columns) - 1, -1, -1):
            if target_columns[i] == src:
                target_columns[i] = new
                break
    return target_columns


def find_parent_with(path: Path | str, filename: str) -> Path:
    """Get a path relative to the project root."""
    path = Path(path) if isinstance(path, str) else path
    while not (path / filename).exists():
        path = path.parent
    project_root: Path = path
    return project_root


def unique(seq: list[Any] | None) -> list[Any]:
    if seq is None:
        return []
    seen: set[Any] = set()
    gx: Callable[[Any], None] = seen.add
    return [x for x in seq if not (x in seen or gx(x))]


# Global set to track seen log messages (for deduplication)
_seen_messages: set[str] = set()


def filter_once_per_message(record) -> bool:
    """Filter to show each unique message only once during the run."""
    global _seen_messages

    msg = record["message"]
    level_name = record["level"].name
    key: str = f"{level_name}:{msg}"

    if key not in _seen_messages:
        _seen_messages.add(key)
        return True
    return False


def setup_logging(verbose: bool = False, log_file: str | None = None) -> None:
    """Configure loguru logging for CLI/scripts.

    This is for standalone scripts and CLI tools. For the backend API,
    use backend.app.core.logging_config.configure_logging() instead.

    Args:
        verbose: Enable DEBUG level and detailed format
        log_file: Optional file path for logging
    """
    global _seen_messages  # pylint: disable=global-statement

    format_str: str = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )
    _seen_messages = set()
    logger.remove()
    logger.add(
        sys.stderr,
        level="DEBUG" if verbose else "INFO",
        format=format_str if verbose else "<level>{message}</level>",
        filter=filter_once_per_message if not verbose else None,
        colorize=True,
        backtrace=True,
        diagnose=True,
    )

    if log_file:
        logger.add(
            log_file,
            level="DEBUG",
            format=format_str,
            backtrace=True,
            diagnose=True,
            enqueue=True,
        )

    if verbose:
        logger.debug("Verbose logging enabled")


def load_shape_file(filename: str) -> dict[str, tuple[int, int]]:
    df: pd.DataFrame = pd.read_csv(filename, sep="\t")
    truth_shapes: dict[str, tuple[int, int]] = {x["entity"]: (x["num_rows"], x["num_columns"]) for x in df.to_dict(orient="records")}
    return truth_shapes


def normalize_text(text: str) -> str:
    """
    Normalize text to match PostgreSQL's authority.immutable_unaccent(lower(text)).

    Steps:
    1. Convert to lowercase
    2. Remove accents/diacritics using Unicode NFD normalization

    This ensures consistency with PostgreSQL trigram matching and embeddings.
    """
    if not text:
        return ""

    # Step 1: Lowercase
    text = text.lower()

    # Step 2: Remove accents (unaccent equivalent)
    # NFD = Canonical Decomposition (separates base chars from combining diacritics)
    # Filter out combining characters (category 'Mn' = Mark, nonspacing)
    text = unicodedata.normalize("NFD", text)
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")

    return text


def recursive_update(d1: dict, d2: dict) -> dict:
    """
    Recursively updates d1 with values from d2. If a value in d1 is a dictionary,
    and the corresponding value in d2 is also a dictionary, it recursively updates that dictionary.
    """
    for key, value in d2.items():
        if isinstance(value, dict) and key in d1 and isinstance(d1[key], dict):
            recursive_update(d1[key], value)
        else:
            d1[key] = value
    return d1


def recursive_filter_dict(
    data: dict[str, Any], filter_keys: set[str], filter_mode: Literal["keep", "exclude"] = "exclude"
) -> dict[str, Any]:
    """
    Recursively filters a dictionary to include only keys in the given set.

    Args:
        D (dict): The dictionary to filter.
        filter_keys (set): The set of keys to keep or exclude.
        filter_mode (str): mode of operation, either 'keep' or 'exclude'.

    Returns:
        dict: A new dictionary containing only the keys in K, with nested dictionaries also filtered.
    """
    if not isinstance(data, dict):
        return data

    return {
        key: (recursive_filter_dict(value, filter_keys=filter_keys, filter_mode=filter_mode) if isinstance(value, dict) else value)
        for key, value in data.items()
        if (key in filter_keys if filter_mode == "keep" else key not in filter_keys)
    }


def dget(data: dict, *path: str, default: Any = None) -> Any:
    if path is None or not data:
        return default

    ps: list[str] = list(path)

    d = None

    for p in ps:
        d = dotget(data, p)

        if d is not None:
            return d

    return d or default


def dotexists(data: dict, *paths: str) -> bool:
    for path in paths:
        if dotget(data, path, default="@@") != "@@":
            return True
    return False


def dotexpand(paths: str | list[str]) -> list[str]:
    """Expands paths with ',' and ':'."""
    if not paths:
        return []
    if not isinstance(paths, (str, list)):
        raise ValueError("dot path must be a string or list of strings")
    paths = paths if isinstance(paths, list) else [paths]
    expanded_paths: list[str] = []
    for p in paths:
        for q in p.replace(" ", "").split(","):
            if not q:
                continue
            if ":" in q:
                expanded_paths.extend([q.replace(":", "."), q.replace(":", "_")])
            else:
                expanded_paths.append(q)
    return expanded_paths


def dotget(data: dict, path: str, default: Any = None) -> Any:
    """Gets element from dict. Path can be x.y.y or x_y_y or x:y:y.
    if path is x:y:y then element is search using borh x.y.y or x_y_y."""

    for key in dotexpand(path):
        d: dict | None = data
        for attr in key.split("."):
            d = d.get(attr) if isinstance(d, dict) else None
            if d is None:
                break
        if d is not None:
            return d
    return default


def dotset(data: dict, path: str, value: Any) -> dict:
    """Sets element in dict using dot notation x.y.z or x:y:z"""

    d: dict = data
    attrs: list[str] = path.replace(":", ".").split(".")
    for attr in attrs[:-1]:
        if not attr:
            continue
        d: dict = d.setdefault(attr, {})
    d[attrs[-1]] = value

    return data


def env2dict(prefix: str, data: dict[str, str] | None = None, lower_key: bool = True) -> dict[str, str]:
    """Loads environment variables starting with prefix into."""
    if data is None:
        data = {}
    if not prefix:
        return data
    if lower_key:
        prefix = prefix.lower()
    for key, value in os.environ.items():
        if lower_key:
            key = key.lower()
        if key.startswith(prefix):
            dotset(data, key[len(prefix) + 1 :].replace("_", ":"), value)
    return data


def import_sub_modules(module_name: str, module_folder: str) -> Any:
    __all__ = []
    sub_modules: list[str] = [
        f.name[:-3] for f in os.scandir(module_folder) if f.is_file() and f.name.endswith(".py") and not f.name.startswith("__")
    ]
    logger.info(f"Importing sub-modules for {module_name}: {', '.join(sub_modules)}")

    for filename in os.listdir(module_folder):
        if filename.endswith(".py") and filename != "__init__.py":
            submodule_name: str = filename[:-3]
            __all__.append(submodule_name)
            importlib.import_module(f"{module_name}.{submodule_name}")


def _ensure_key_property(cls):
    if not hasattr(cls, "key"):

        def key(self) -> str:
            return getattr(self, "_registry_key", "unknown")

        cls.key = property(key)
    return cls


R = TypeVar("R", dict[str, Any], list[Any], str)


def replace_env_vars(data: R) -> R:
    """Replaces recursively values in `data` that match `${ENV_VAR}` with os.getenv("ENV_VAR", "")"""
    if isinstance(data, dict):
        return {k: replace_env_vars(v) for k, v in data.items()}  # type: ignore[return-value]
    if isinstance(data, list):
        return [replace_env_vars(i) for i in data]  # type: ignore[return-value]
    if isinstance(data, str) and data.startswith("${") and data.endswith("}"):
        env_var: str = data[2:-1]
        return os.getenv(env_var, "")  # type: ignore[return-value]
    return data


T = TypeVar("T")


class Registry(Generic[T]):
    items: dict[str, T] = {}

    @classmethod
    def get(cls, key: str) -> T:
        if key not in cls.items:
            raise KeyError(f"preprocessor {key} is not registered")
        return cls.items[key]

    @classmethod
    def register(cls, **args) -> Callable[..., Any]:
        def decorator(fn_or_class):
            key_or_keys: str | list[str] = args.get("key") or fn_or_class.__name__
            keys: list[str] = [key_or_keys] if isinstance(key_or_keys, str) else key_or_keys

            if len(keys) == 0:
                raise ValueError("Registry: key(s) cannot be empty")

            if keys[0] in cls.items:
                raise KeyError(f"Registry: Overriding existing registration for key '{keys[0]}'")

            if args.get("type") == "function":
                fn_or_class = fn_or_class()
            else:
                setattr(fn_or_class, "_registry_key", keys[0])
                setattr(fn_or_class, "_registry_opts", {k: v for k, v in args.items() if k != "key"})

                fn_or_class = _ensure_key_property(fn_or_class)

            for k in keys:
                cls.items[k] = fn_or_class

            fn_or_class = cls.registered_class_hook(fn_or_class, **args)
            return fn_or_class

        return decorator

    @classmethod
    def is_registered(cls, key: str) -> bool:
        return key in cls.items

    @classmethod
    def registered_class_hook(cls, fn_or_class: Any, **args) -> Any:  # pylint: disable=unused-argument
        return fn_or_class

    def scan(self, module_name, module_folder: str) -> Self:
        import_sub_modules(module_name, module_folder)
        return self

    @classmethod
    def unique_items(cls) -> set[T]:
        """Get the set of unique registered items. Same item may be registered under multiple keys."""
        return set(cls.items.values())

    def keys(self) -> set[str]:
        """Get the set of registered keys. This is the first key if an item is registered under multiple keys."""
        return set(getattr(item, "key") for item in self.items.values())


def create_db_uri(*, host: str, port: int | str, user: str, dbname: str, driver: str = "postgresql+psycopg") -> str:
    """
    Builds database URI from the individual config elements.
    """
    return f"{driver}://{user}@{host}:{port}/{dbname}"


def get_connection_uri(connection: Any) -> str:
    conn_info = connection.get_dsn_parameters()
    user: str = conn_info.get("user")
    host: str = conn_info.get("host")
    port: str = conn_info.get("port")
    dbname: str = conn_info.get("dbname")
    uri: str = f"postgresql://{user}@{host}:{port}/{dbname}"
    return uri


def load_resource_yaml(key: str) -> dict[str, Any] | None:
    """Loads a resource YAML file from the resources folder."""

    resource_path: str = os.path.join(os.path.dirname(__file__), "resources", f"{key}.yml")
    if not os.path.exists(resource_path):
        return None

    with open(resource_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve_specification(specification: dict[str, Any] | str | None) -> dict[str, Any]:
    """Resolves a specification which can be either a dict or a resource key string."""
    if isinstance(specification, dict):
        return specification
    if isinstance(specification, str):
        return load_resource_yaml(specification)  # type: ignore
    return {
        "key": "unknown",
        "id_field": "id",
        "label_field": "name",
        "properties": [],
        "property_settings": {},
        "sql_queries": {},
    }


def import_submodules(package_name: str):
    """
    Recursively import all submodules of the given package.

    Example:
        # Inside mypackage/__init__.py
        import_submodules(__name__)
    """
    package = importlib.import_module(package_name)
    package_path = package.__path__  # Namespace packages supported

    for module_info in pkgutil.walk_packages(package_path, prefix=package_name + "."):
        module_name = module_info.name

        if module_name not in globals():
            importlib.import_module(module_name)
