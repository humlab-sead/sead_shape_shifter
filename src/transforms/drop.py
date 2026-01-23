from typing import Any

import pandas as pd
from loguru import logger

from src.specifications.fd import FunctionalDependencySpecification


def drop_duplicate_rows(
    data: pd.DataFrame, columns: bool | list[str] = False, fd_check: bool = False, entity_name: str | None = None
) -> pd.DataFrame:
    """Drop duplicate rows from DataFrame."""
    if columns is False:
        return data

    if not isinstance(columns, list):
        return data.drop_duplicates().reset_index(drop=True)

    if any(c not in data.columns for c in columns):
        missing_requested_columns: set[str] = set(columns).difference(data.columns)
        logger.warning(
            f"{entity_name}[drop_duplicate_rows]: Delaying drop_duplicates because some columns "
            f"are missing from DataFrame: {missing_requested_columns}"
        )
        # raise ValueError(f"Unable to drop_duplicates because some columns are missing from DataFrame: {missing_requested_columns}")
        return data

    columns = [c for c in columns if c in data.columns]
    if not columns:
        logger.error(
            f"{entity_name}[drop_duplicate_rows]: No valid columns specified for drop_duplicates after "
            f"filtering missing columns. No duplicates will be dropped."
        )
        return data
    if fd_check:
        specification = FunctionalDependencySpecification()
        specification.is_satisfied_by(df=data, determinant_columns=columns, raise_error=True)

    data = data.drop_duplicates(subset=columns).reset_index(drop=True)
    return data


def drop_empty_rows(
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
