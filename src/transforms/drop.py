from typing import Any, Mapping, Sequence

import pandas as pd
from loguru import logger

from src.specifications.fd import FunctionalDependencySpecification


def missing_columns(df: pd.DataFrame, columns: Sequence[str]) -> set[str]:
    """Return the set of requested columns that are missing from df."""
    cols_set: set[str] = set(columns)
    df_cols: set[str] = set(df.columns)
    return cols_set - df_cols


def drop_duplicate_rows(
    data: pd.DataFrame,
    *,
    columns: bool | list[str] = False,
    entity_name: str | None = None,
    fd_check: bool = False,
    strict_fd_check: bool = True,
) -> pd.DataFrame:
    """Drop duplicate rows from DataFrame."""

    # Case 1: explicitly disabled
    if columns is False:
        return data

    # Case 2: all columns
    if columns is True:
        return data.drop_duplicates(ignore_index=True)

    # Case 3: subset of columns
    columns = list(dict.fromkeys(columns))

    missing: set[str] = missing_columns(data, columns)
    if missing:
        logger.warning(f"{entity_name}[drop_duplicate_rows]: delaying since columns are missing: {missing}")
        return data

    if not columns:
        logger.error(f"{entity_name}[drop_duplicate_rows]: No columns specified; no duplicates will be dropped.")
        return data

    if fd_check:
        specification = FunctionalDependencySpecification()
        # Verify that the functional dependency holds before dropping duplicates
        # Will raise an exception if the FD is violated, and log a warning
        specification.is_satisfied_by(df=data, determinant_columns=columns, entity_name=entity_name, strict=strict_fd_check)

    data = data.drop_duplicates(subset=columns).reset_index(drop=True)
    return data


def drop_empty_rows_obselete(
    *, data: pd.DataFrame, entity_name: str, subset: bool | list[str] | dict[str, Any] | None = None, treat_empty_strings_as_na: bool = True
) -> pd.DataFrame:
    """Drop rows that are completely empty (NaN, None, or empty strings) in the DataFrame or in the specified subset of columns.
    Case if subset is...
         - False         : no rows are dropped.
         - True or None  : all columns are considered for checking emptiness.
         - list of str   : only those columns are considered for checking emptiness.
         - dict          : keys are column names and values are lists of values to consider as empty for that column.
    """

    if subset is False:
        return data

    if isinstance(subset, (list, dict)):
        missing_requested_columns: list[str] = [c for c in subset if c not in data.columns]
        if missing_requested_columns:
            logger.warning(f"{entity_name}[subsetting]: Columns missing for drop_empty_rows: {missing_requested_columns}")
            return data

        # Replace empty strings with NaN only in the subset columns
        data = data.copy()

        if isinstance(subset, dict):
            # Handle dict case: replace specified values with NaN for each column
            for col, empty_values in subset.items():
                data.loc[data[col].isin(empty_values), col] = pd.NA
            subset_columns: list[str] = list(subset.keys())  # type: ignore[assignment]
        else:
            # Handle list case: replace empty strings with NaN in subset columns
            if treat_empty_strings_as_na:
                data[subset] = data[subset].replace("", pd.NA)
            subset_columns = subset

        return data.dropna(subset=subset_columns, how="all")

    # Replace empty strings with NaN in all columns
    if treat_empty_strings_as_na:
        data = data.replace("", pd.NA)
    return data.dropna(how="all")


def drop_empty_rows(
    *,
    data: pd.DataFrame,
    entity_name: str,
    subset: bool | Sequence[str] | Mapping[str, Sequence[Any]] | None = None,
    treat_empty_strings_as_na: bool = True,
) -> pd.DataFrame:
    """Drop rows that are completely empty (NA/None/empty strings) in the DataFrame or a subset.

    subset:
      - False        : do nothing
      - True / None  : consider all columns
      - Sequence[str]: consider only these columns
      - Mapping      : {col: values_to_consider_empty_for_that_col}
    """
    prefix: str = f"{entity_name}" if entity_name else ""

    if subset is False:
        return data

    if subset == []:
        return data

    # ---- Normalize subset columns ----
    if subset is None or subset is True:
        subset_columns: list[str] = list(data.columns)
        subset_kind = "all"
    elif isinstance(subset, Mapping):
        subset_columns = list(subset.keys())
        subset_kind = "dict"
    else:
        subset_columns = list(subset)
        subset_kind = "list"

    # ---- Validate columns ----
    missing: list[str] = [c for c in subset_columns if c not in data.columns]
    if missing:
        logger.warning(f"{prefix}[drop_empty_rows]: columns missing: {missing}")
        return data

    # ---- Dict case ----
    if subset_kind == "dict":
        out = data.copy()

        for col, empty_values in subset.items():  # type: ignore[union-attr]
            if empty_values:
                mask: pd.Series[bool] = out[col].isin(list(empty_values))
                if mask.any():
                    out[col] = out[col].where(~mask, pd.NA)  # type: ignore[arg-type]

        if treat_empty_strings_as_na:
            out[subset_columns] = out[subset_columns].replace("", pd.NA)

        return out.dropna(subset=subset_columns, how="all")

    # ---- List / all columns case ----
    out: pd.DataFrame = data
    if treat_empty_strings_as_na:
        out = data.copy()
        out[subset_columns] = out[subset_columns].replace("", pd.NA)

    return out.dropna(subset=subset_columns, how="all")
