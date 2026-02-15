from __future__ import annotations

import base64
import functools
import importlib
import io
import os
import pkgutil
import re
import zlib
from datetime import datetime
from os.path import abspath, basename, dirname, join, splitext
from typing import TYPE_CHECKING, Any, Callable, Generic, Literal, Self, TypeVar, overload

import pandas as pd
import yaml
from jinja2 import Environment, Template
from loguru import logger
from sqlalchemy import Engine, create_engine

# Import centralized logging setup from src.utility
from src.utility import setup_logging

if TYPE_CHECKING:
    from .submission import Submission


def pascal_to_snake_case(s: str) -> str:
    """
    Converts a string from PascalCase to snake_case.
    """
    return re.sub(r"(?<!^)(?=[A-Z])", "_", s).lower()


def snake_to_pascal_case(s: str) -> str:
    return "".join(part.capitalize() for part in s.split("_"))


def import_sub_modules(module_folder: str) -> Any:
    __all__ = []
    # current_dir: str = os.path.dirname(__file__)
    for filename in os.listdir(module_folder):
        if filename.endswith(".py") and filename != "__init__.py":
            module_name: str = filename[:-3]
            __all__.append(module_name)
            importlib.import_module(f".{module_name}", package=__name__)


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
    """Gets element from dict using multiple possible "dot" paths."""
    if path is None or not data:
        return default

    d = None
    for p in path:
        d = dotget(data, p)

        if d is not None:
            return d

    return d or default


def dotexists(data: dict, *paths: str) -> bool:
    """Checks if any of the given dot paths exist in the dict."""
    for path in paths:
        if dotget(data, path, default="@@") != "@@":
            return True
    return False


def dotexpand(path: str) -> list[str]:
    """Expands dot paths with ',' and ':'."""
    paths: list[str] = []
    for p in path.replace(" ", "").split(","):
        if not p:
            continue
        if ":" in p:
            paths.extend([p.replace(":", "."), p.replace(":", "_")])
        else:
            paths.append(p)
    return paths


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
    for key, value in os.environ.items():
        if lower_key:
            key = key.lower()
        if key.startswith(prefix.lower()):
            dotset(data, key[len(prefix) + 1 :].replace("_", ":"), value)
    return data


# R = TypeVar("R", dict[str, Any], list[Any], str)


# def replace_env_vars(data: R) -> R:
#     """Replaces recursively values in `data` that match `${ENV_VAR}` with os.getenv("ENV_VAR", "")"""
#     if isinstance(data, dict):
#         return {k: replace_env_vars(v) for k, v in data.items()}  # type: ignore[return-value]
#     if isinstance(data, list):
#         return [replace_env_vars(i) for i in data]  # type: ignore[return-value]
#     if isinstance(data, str) and data.startswith("${") and data.endswith("}"):
#         env_var: str = data[2:-1]
#         return os.getenv(env_var, "")  # type: ignore[return-value]
#     return data


def log_decorator(enter_message: str | None = "Entering", exit_message: str | None = "Exiting", level: int | str = "INFO"):
    """Decorator to log entry and exit of a function."""

    def decorator(func):

        if __debug__:
            return func

        @functools.wraps(func)
        def wrapper(*args, **kwargs):

            if not (enter_message or exit_message):
                return func(*args, **kwargs)

            if enter_message:
                logger.log(level, f"{enter_message} ({func.__name__})")
            result = func(*args, **kwargs)
            if exit_message:
                logger.log(level, f"{exit_message} ({func.__name__})")
            return result

        return wrapper

    return decorator


# def load_sql_from_file(identifier: str) -> str:
#     sql_path: str = join(dirname(abspath(__file__)), "sql", identifier + ".sql")
#     if not os.path.exists(sql_path):
#         return
#     with open(sql_path, "r") as file:
#         return file.read()


def load_json_from_file(identifier: str) -> str:
    sql_path: str = join(dirname(abspath(__file__)), "json", identifier + ".json")
    with open(sql_path, "r", encoding="utf-8") as file:
        return file.read()


def upload_dataframe_to_postgres(df: pd.DataFrame, table_name: str, db_uri: str) -> None:
    """
    Uploads a pandas DataFrame to a PostgreSQL database.

    Parameters:
    df (pd.DataFrame): The DataFrame to upload.
    table_name (str): The name of the table to upload the DataFrame to.
    db_uri (str): The URI of the PostgreSQL database.
    """
    engine: Engine = create_engine(db_uri)

    df.to_sql(table_name, engine, schema="public", if_exists="fail", index=False)


def load_dataframe_from_postgres(sql: str, db_uri: str, index_col: str | None = None, dtype: Any = None) -> pd.DataFrame:
    """
    Loads a pandas DataFrame from a PostgreSQL database.

    Parameters:
    sql (str): The name of the table to load the DataFrame from.
    db_uri (str): The URI of the PostgreSQL database.
    """
    engine: Engine = create_engine(db_uri)
    sql = sql.replace("%", "%%")
    return pd.read_sql_query(sql, con=engine, index_col=index_col, dtype=dtype)


# def load_sead_data(db_uri: str, sql: str | pd.DataFrame, index: list[str], sortby: list[str] | None = None) -> pd.DataFrame:
#     """Returns a dataframe of tables from SEAD with attributes."""
#     index = index if isinstance(index, list) else [index]
#     sortby = sortby if isinstance(sortby, list) else [sortby] if sortby else None
#     data: pd.DataFrame = (
#         (sql if isinstance(sql, pd.DataFrame) else load_dataframe_from_postgres(sql, db_uri, index_col=None))
#         .set_index(index, drop=False)
#         .rename_axis([f"index_{x}" for x in index])
#         .sort_values(by=sortby if sortby else index)
#     )
#     return data


# def load_sead_columns(db_uri: str, ignore_columns: list[str] | None = None) -> pd.DataFrame:
#     """Returns a dataframe of table columns from SEAD with attributes."""
#     sql: str = "select * from clearing_house.clearinghouse_import_columns"
#     data: pd.DataFrame = load_sead_data(db_uri, sql, ["table_name", "column_name"], ["table_name", "position"])
#     if ignore_columns:
#         columns_to_ignore: list[str] = [
#             c for c in data["column_name"].unique() if any(fnmatch.fnmatch(c, pattern) for pattern in ignore_columns)
#         ]
#         data = data[~data["column_name"].isin(columns_to_ignore)]

#     return data


def flatten(lst: list[Any]) -> list[Any]:
    """
    Flattens a list of lists
    """
    return [item for sublist in lst for item in sublist]


def flatten_sets(x, y) -> set:
    """
    Flattens a set of sets
    """
    return set(list(x) + list(y))


def camel_case_name(undescore_name: str) -> str:
    first, *rest = undescore_name.split("_")
    return first + "".join(word.capitalize() for word in rest)


def compress_and_encode(path: str) -> None:
    """Compress and encode file using zlib and base64."""
    compressed_data: bytes = zlib.compress(path.encode("utf8"))
    encoded: bytes = base64.b64encode(compressed_data)
    uue_filename: str = path + ".gz.uue"
    with io.open(uue_filename, "wb") as outstream:
        outstream.write(encoded)

    gz_filename: str = path + ".gz"
    with io.open(gz_filename, "wb") as outstream:
        outstream.write(compressed_data)


T = TypeVar("T")


class Registry(Generic[T]):
    """Registry for functions or classes."""

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

    def scan(self, module_folder: str) -> Self:
        import_sub_modules(module_folder)
        return self


def _ensure_key_property(cls):
    if not hasattr(cls, "key"):

        def key(self) -> str:
            return getattr(self, "_registry_key", "unknown")

        cls.key = property(key)
    return cls


@overload
def strip_path_and_extension(filename: str) -> str: ...


@overload
def strip_path_and_extension(filename: list[str]) -> list[str]: ...


def strip_path_and_extension(filename: str | list[str]) -> str | list[str]:
    """Remove path and extension from filename(s)."""
    if isinstance(filename, str):
        return splitext(basename(filename))[0]
    return [splitext(basename(x))[0] for x in filename]


def strip_extensions(filename: str | list[str]) -> str | list[str]:
    if isinstance(filename, str):
        return splitext(filename)[0]
    return [splitext(x)[0] for x in filename]


def replace_extension(filename: str, extension: str) -> str:
    if filename.endswith(extension):
        return filename
    base, _ = splitext(filename)
    return f"{base}{'' if extension.startswith('.') else '.'}{extension}"


def path_add_suffix(path: str, suffix: str, new_extension: str | None = None) -> str:
    name, extension = splitext(path)
    return f"{name}{suffix}{extension if new_extension is None else new_extension}"


def path_add_timestamp(path: str, fmt: str = "%Y%m%d%H%M") -> str:
    return path_add_suffix(path, f"_{datetime.now().strftime(fmt)}")


def path_add_date(path: str, fmt: str = "%Y%m%d") -> str:
    return path_add_suffix(path, f"_{datetime.now().strftime(fmt)}")


def ts_data_path(directory: str, filename: str) -> str:
    return join(directory, f'{datetime.now().strftime("%Y%m%d%H%M")}_{filename}')


def read_yaml(file: Any) -> dict:
    """Read yaml file. Return dict."""
    if isinstance(file, str) and any(file.endswith(x) for x in (".yml", ".yaml")):
        with open(file, "r", encoding="utf-8") as fp:
            return yaml.load(fp, Loader=yaml.FullLoader)
    data: list[dict] = yaml.load(file, Loader=yaml.FullLoader)
    return {} if len(data) == 0 else data[0]


def write_yaml(data: dict, file: str) -> None:
    """Write yaml to file.."""
    with open(file, "w", encoding="utf-8") as fp:
        return yaml.dump(data=data, stream=fp)


def remove_keys_recursively(data: dict[str, Any], keys_to_remove: set[str]) -> dict[str, Any]:
    """
    Recursively removes keys from a dictionary if they exist in keys_to_remove.

    Parameters:
    data (dict): The input dictionary.
    keys_to_remove (set): A set of keys to be removed.
    """
    if not isinstance(data, dict):
        return data

    if not keys_to_remove:
        return data

    keys: list[str] = list(data.keys())
    for key in keys:
        if key in keys_to_remove:
            del data[key]
        elif isinstance(data[key], dict):
            remove_keys_recursively(data[key], keys_to_remove)
    return data


def update_dict_from_yaml(yaml_file: str, data: dict, keep_keys: set[str] | None = None) -> dict:
    """Update dict `data` with values found in `yaml_file`."""
    if yaml_file is None:
        return data
    keep_keys = keep_keys or set()
    options: dict = read_yaml(yaml_file)
    data.update(options)
    return data


def create_db_uri(*, host: str, port: int | str, user: str, dbname: str) -> str:
    """
    Returns the database URI from the environment variables.
    """
    return f"postgresql+psycopg://{user}@{host}:{port}/{dbname}"


def get_connection_uri(connection: Any) -> str:
    conn_info = connection.get_dsn_parameters()
    user: str = conn_info.get("user")
    host: str = conn_info.get("host")
    port: str = conn_info.get("port")
    dbname: str = conn_info.get("dbname")
    uri: str = f"postgresql+psycopg://{user}@{host}:{port}/{dbname}"
    return uri


def to_lookups_sql(submission: Submission, filename: str) -> None:
    """
    This is a utility function to generate SQL inserts of lookup data.
    A SEAD system id is generated for each insert.

    Lookup tables are identified as having columns that begin with "(".
    This column is computed by Excel macros in the input file.

    """

    lookup_sql_template: str = """
    with new_data {{excel_sql_columns}} as (
        values
            {% for row in excel_sql_values %}{{row}}{% if not loop.last %},
            {% endif %}{% endfor %}
        )
        insert into {{table_name}} ({{pk_name}}, {{non_pk_attributes}})
            select
                sead_utility.allocate_system_id(
                    v_submission_identifier,
                    v_change_request_identifier,
                    '{{table_name}}',
                    '{{pk_name}}',
                    new_data.system_id::text,
                    row_to_json(new_data.*)::jsonb
                ) as {{pk_name}}, {{non_pk_attributes}}
            from new_data;

"""

    jinja_env = Environment()
    template: Template = jinja_env.from_string(lookup_sql_template)

    with open(filename, "w", encoding="utf-8") as fp:
        for table_name in submission.data_table_names:

            excel_sql_columns: str | None = next((x for x in submission.data_tables[table_name] if x.startswith("(")), None)  # type: ignore
            if excel_sql_columns:
                pk_name: str = submission.schema[table_name].pk_name
                data = (
                    submission.data_tables[table_name][excel_sql_columns]
                    .str.strip()
                    .str.lstrip("(")
                    .str.rstrip(",")
                    .str.strip()
                    .str.rstrip(")")
                )
                attributes: list[str] = [x.strip() for x in excel_sql_columns.strip().lstrip("(").rstrip(")").split(",")]
                non_pk_attributes = [x for x in attributes if x not in ("system_id", pk_name)]
                data: pd.Series = submission.data_tables[table_name][excel_sql_columns]

                sql_data: str = template.render(
                    table_name=table_name,
                    pk_name=pk_name,
                    excel_sql_columns=excel_sql_columns,
                    excel_sql_values=data[~data.isnull()],
                    non_pk_attributes=", ".join(non_pk_attributes),
                )
                fp.write(sql_data)


def ensure_path(f: str) -> None:
    os.makedirs(dirname(f), exist_ok=True)


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
