from typing import Any
from numpy import isin
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

    extra_columns = extra_columns or {}
    
    source_column_renames: dict[str, str] = {
        source_col: new_name 
        for new_name, source_col in extra_columns.items() 
        if isinstance(source_col, str) and source_col in source.columns
    }
    
    constant_columns: dict[str, Any] = {
        new_name: value 
        for new_name, value in extra_columns.items() 
        if new_name not in [v for v in source_column_renames.values()]
    }

    columns_to_extract: list[str] = columns + list(source_column_renames.keys())

    # Check for missing required columns
    if any(c not in source.columns for c in columns_to_extract):
        missing: list[str] = [c for c in columns_to_extract if c not in source.columns]
        if raise_if_missing:
            raise ValueError(f"Key {surrogate_id}: Columns not found in DataFrame: {missing}")
        else:
            logger.warning(f"Key {surrogate_id}: Columns not found in DataFrame and will be skipped: {missing}")

    # Extract only columns that exist
    columns_to_extract = [c for c in columns_to_extract if c in source.columns]
    result: pd.DataFrame = source[columns_to_extract].copy()

    # Rename columns that were extracted for renaming
    if source_column_renames:
        rename_map: dict[str, str] = {src: new for src, new in source_column_renames.items() if src in result.columns}
        if rename_map:
            result = result.rename(columns=rename_map)

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

    # Add surrogate ID if requested and not present
    if surrogate_id and surrogate_id not in result.columns:
        result = add_surrogate_id(result, surrogate_id)

    return result
