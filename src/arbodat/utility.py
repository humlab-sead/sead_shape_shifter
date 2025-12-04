import sys
from typing import Any

import pandas as pd
from loguru import logger


def add_surrogate_id(target: pd.DataFrame, id_name: str) -> pd.DataFrame:
    """Add an integer surrogate ID starting at 1."""
    target = target.reset_index(drop=True).copy()
    target[id_name] = range(1, len(target) + 1)
    return target


def check_functional_dependency(df: pd.DataFrame, determinant_columns: list[str], raise_error: bool = True) -> bool:
    """Check functional dependency: for each unique combination of subset columns,
    the other columns should have consistent values.
    Args:
        df (pd.DataFrame): DataFrame to check.
        determinant_columns (list[str]): List of column names that are checked for functional dependency.
        raise_error (bool): Whether to raise an error if inconsistencies are found.
    Returns:
        bool: True if no inconsistencies are found, otherwise False.
    """

    # The columns that should have consistent values given the determinant columns
    dependent_columns: list[str] = df.columns.difference(determinant_columns).to_list()

    if len(dependent_columns) == 0:
        return True

    bad_keys: list = []
    for keys, group in df.groupby(determinant_columns):
        if (group[dependent_columns].nunique(dropna=False) > 1).any():
            bad_keys.append(keys)

    if bad_keys:
        msg: str = f"inconsistent non-subset values for keys: {bad_keys}"
        if raise_error:
            raise ValueError(f"[fd_check]: {msg}")
        else:
            logger.warning(f"[fd_check]: {msg}")

    return len(bad_keys) == 0


def get_subset(
    source: pd.DataFrame,
    columns: list[str],
    *,
    entity_name: str | None = None,
    extra_columns: None | dict[str, Any] = None,
    drop_duplicates: bool | list[str] = False,
    fd_check: bool = False,
    raise_if_missing: bool = True,
    surrogate_id: str | None = None,
    drop_empty_rows: bool | list[str] = False,
) -> pd.DataFrame:
    """Return a subset of the source DataFrame with specified columns, optional extra columns, and duplicate handling.
    Args:
        source (pd.DataFrame): Source DataFrame.
        columns (list[str]): List of column names to include from source.
        extra_columns (dict[str, Any] | None): Extra columns mapping:
            {new_column_name: source_column_name_or_constant}
            - If value is a string matching source column: extract and rename
            - Otherwise: add new column with the constant value
        drop_duplicates (bool | list[str]): Whether to drop duplicates.
            - If True: drop all duplicate rows
            - If list: drop duplicates based on those columns
            - If False: keep all rows
        fd_check (bool): Whether to check functional dependency when dropping duplicates.
        raise_if_missing (bool): Whether to raise an error if requested columns are missing.
        surrogate_id (str | None): Name of surrogate ID column to add if not already present.
        drop_empty_rows (bool): Whether to drop rows that are completely empty after subsetting.

    Returns:
        pd.DataFrame: Resulting DataFrame with requested columns and modifications.

    Examples:
        >>> df = pd.DataFrame({'A': [1, 2], 'B': [3, 4], 'C': [5, 6]})
        >>> # Extract A and B, rename C to D
        >>> get_subset(df, ['A', 'B'], extra_columns={'D': 'C'})
        >>> # Extract A and B, add constant column D
        >>> get_subset(df, ['A', 'B'], extra_columns={'D': 'constant_value'})
    """
    if source is None:
        raise ValueError("Source DataFrame must be provided")

    entity_name = entity_name or (surrogate_id.rstrip("_id") if surrogate_id else "unspecified")

    extra_columns = extra_columns or {}

    source_column_renames: dict[str, str] = {
        source_col: new_name for new_name, source_col in extra_columns.items() if isinstance(source_col, str) and source_col in source.columns
    }

    constant_columns: dict[str, Any] = {
        new_name: value for new_name, value in extra_columns.items() if new_name not in [v for v in source_column_renames.values()]
    }

    columns_to_extract: list[str] = columns + list(source_column_renames.keys())

    # Check for missing required columns
    if any(c not in source.columns for c in columns_to_extract):
        missing: list[str] = [c for c in columns_to_extract if c not in source.columns]
        if raise_if_missing:
            raise ValueError(f"{entity_name}[subsetting]: Columns not found in DataFrame: {missing}")
        else:
            logger.warning(f"{entity_name}[subsetting]: Columns not found in DataFrame and will be skipped: {missing}")

    # Extract only columns that exist
    columns_to_extract = [c for c in columns_to_extract if c in source.columns]
    result: pd.DataFrame = source[columns_to_extract].copy()

    if source_column_renames:
        # Extra column can be an alias for an existing column, i.e. same column name can exist multiple times,
        # and we only want to rename the last occurrence (the extracted one)
        result.columns = _rename_last_occurence(data=result, rename_map=source_column_renames)

    # Add constant columns
    for col_name, value in constant_columns.items():
        result[col_name] = value

    # Handle duplicate removal
    if drop_duplicates:
        if isinstance(drop_duplicates, list):
            # Check functional dependency BEFORE dropping duplicates
            if fd_check:
                check_functional_dependency(result, determinant_columns=drop_duplicates, raise_error=True)
            result = result.drop_duplicates(subset=drop_duplicates)
        else:
            result = result.drop_duplicates()

    # Drop rows that are completely empty after subsetting
    if drop_empty_rows:
        if isinstance(drop_empty_rows, list):
            result = result.dropna(subset=drop_empty_rows, how="all")
        else:
            result = result.dropna(how="all")

    # Add surrogate ID if requested and not present
    if surrogate_id and surrogate_id not in result.columns:
        result = add_surrogate_id(result, surrogate_id)

    return result


def _rename_last_occurence(data: pd.DataFrame, rename_map: dict[str, str]) -> list[str]:
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


def extract_translation_map(fields_metadata: list[dict[str, str]], from_field: str = "arbodat_field", to_field: str = "english_column_name") -> dict[str, str]:
    """Get translation map from config."""

    if not fields_metadata:
        return {}

    if any(c not in fields_metadata[0] for c in [from_field, to_field]):
        logger.warning(f"[translation] Translation config is missing required keys '{from_field}' and '{to_field}'. Skipping translation.")
        return {}

    translations_map: dict[str, str] = {t[from_field]: t[to_field] for t in fields_metadata if from_field in t and to_field in t}

    return translations_map


def translate(data: dict[str, pd.DataFrame], translations_map: dict[str, str] | None) -> dict[str, pd.DataFrame]:
    """Translate column names using translation from config."""

    if not translations_map:
        return data

    def fx(col: str, columns: list[str]) -> str:
        translated_column: str = translations_map.get(col, col)
        if translated_column in columns:
            return col
        return translated_column

    for entity, table in data.items():
        columns: list[str] = table.columns.tolist()
        table.columns = [fx(col, columns) for col in columns]
        data[entity] = table

    return data


# Global set to track seen log messages (for deduplication)
_seen_messages: set[str] = set()


def filter_once_per_message(record) -> bool:
    """Filter to show each unique message only once during the run."""
    global _seen_messages

    msg = record["message"]
    level_name = record["level"].name
    key = f"{level_name}:{msg}"

    if key not in _seen_messages:
        _seen_messages.add(key)
        return True
    return False


def setup_logging(verbose: bool = False, log_file: str | None = None) -> None:
    """Configure loguru logging with appropriate handlers and filters.

    Args:
        verbose: If True, set log level to DEBUG and show all messages.
                If False, set to INFO and filter duplicate messages.
        log_file: Optional path to log file. If provided, logs are written to file.
    """
    global _seen_messages

    _seen_messages = set()

    level = "DEBUG" if verbose else "INFO"

    logger.remove()

    log_format = (
        (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        )
        if verbose
        else "<level>{message}</level>"
    )

    # Add console handler with filter only if not verbose
    logger.add(
        sys.stderr,
        level=level,
        format=log_format,
        filter=filter_once_per_message if not verbose else None,
        colorize=True,
        enqueue=False,
    )

    # Add file handler if specified (always show all messages in log file)
    if log_file:
        logger.add(
            log_file,
            level="DEBUG",
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                "<level>{message}</level>"
            ),
            enqueue=False,
        )

    if verbose:
        logger.debug("Verbose logging enabled")
