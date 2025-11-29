from typing import Any
import pandas as pd
from loguru import logger


def add_surrogate_id(target: pd.DataFrame, id_name: str) -> pd.DataFrame:
    """Add an integer surrogate ID starting at 1."""
    target = target.reset_index(drop=True).copy()
    target[id_name] = range(1, len(target) + 1)
    return target

def check_functional_dependency(df: pd.DataFrame, determinant_columns: list[str], raise_error: bool =True) -> bool:
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
            raise ValueError(msg)
        else:
            logger.warning(msg)

    return len(bad_keys) == 0


def get_subset(
    source: pd.DataFrame,
    columns: list[str],
    extra_columns: None | dict[str, Any] = None,
    drop_duplicates: bool | list[str] = False,
    fd_check: bool = False,
    raise_if_missing: bool = True,
    surrogate_id: str | None = None,
) -> pd.DataFrame:
    """Return data with only the columns that actually exist and drop duplicates if requested.
    Args:
        source (pd.DataFrame): Source DataFrame.
        columns (list[str]): List of column names to include.
        extra_columns (dict[str, Any] | None): Extra columns to add. Values can be column names or constants.
        drop_duplicates (bool | list[str]): Whether to drop duplicates. If list, drop duplicates based on those columns.
        fd_check (bool): Whether to check functional dependency when dropping duplicates.
        raise_if_missing (bool): Whether to raise an error if requested columns are missing.
        surrogate_id (str | None): Name of surrogate ID column to add if not present.
    Returns:
        pd.DataFrame: Resulting DataFrame with requested columns and modifications.
    """
    if source is None:
        raise ValueError("Source DataFrame must be provided")

    if any(c not in source.columns for c in columns):
        missing: list[str] = [c for c in columns if c not in source.columns]
        if raise_if_missing:
            raise ValueError(f"Key {surrogate_id}: Columns not found in DataFrame: {missing}")
        else:
            logger.warning(f"Key {surrogate_id}: Columns not found in DataFrame and will be skipped: {missing}")

    existing: list[str] = [c for c in columns if c in source.columns]
    result: pd.DataFrame = source[existing]

    for c, v in (extra_columns or {}).items():
        result[c] = source[v] if isinstance(v, str) and v in source.columns else v

    if drop_duplicates:
        if isinstance(drop_duplicates, list):
            result = result.drop_duplicates(subset=drop_duplicates)
        if fd_check:
            check_functional_dependency(result, determinant_columns=existing, raise_error=True)
        else:
            result = result.drop_duplicates()


    if surrogate_id and surrogate_id not in result.columns:
        result = add_surrogate_id(result, surrogate_id)

    return result
