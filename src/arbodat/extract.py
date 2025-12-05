from turtle import rt
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


class SubsetService:
    """Class for extracting subsets from DataFrames with various options."""

    def get_subset(
        self,
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
                - If value is a string matching source column, then copy that column
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
            >>> # Extract A and B, add copy of C to D
            >>> get_subset(df, ['A', 'B'], extra_columns={'D': 'C'})
            >>> # Extract A and B, add constant column D
            >>> get_subset(df, ['A', 'B'], extra_columns={'D': 'constant_value'})
        """
        if source is None:
            raise ValueError("Source DataFrame must be provided")

        entity_name = entity_name or (surrogate_id.rstrip("_id") if surrogate_id else "unspecified")
        columns = list(set(columns))  # Uniqueify columns
        extra_columns = extra_columns or {}

        extra_source_columns, extra_constant_columns = self._split_extra_columns(source, extra_columns)
        all_requested_columns: set[str] = set(columns).union(extra_source_columns.values())

        self._check_if_missing_requested_columns(source, entity_name, raise_if_missing, all_requested_columns)

        columns_to_extract: list[str] = [c for c in source.columns if c in all_requested_columns]

        # Extract only columns that exist, and uniqueify
        columns_to_extract = [c for c in source.columns if c in columns_to_extract]
        result: pd.DataFrame = source[columns_to_extract].copy()

        # Add extra columns that are copies of existing columns
        for col_name, existing_col_name in extra_source_columns.items():
            result[col_name] = result[existing_col_name]

        # Add constant columns
        for col_name, value in extra_constant_columns.items():
            result[col_name] = value

        # Handle duplicate removal
        if drop_duplicates:
            result = self._drop_duplicates(result, columns=drop_duplicates, fd_check=fd_check, entity_name=entity_name)

        result = self._restore_columns_order(result, columns)

        # Drop rows that are completely empty after subsetting
        if drop_empty_rows:
            result = self._drop_empty_rows(
                data=result, entity_name=entity_name, subset=None if drop_empty_rows is True else drop_empty_rows
            )

        # Add surrogate ID if requested and not present
        if surrogate_id and surrogate_id not in result.columns:
            result = add_surrogate_id(result, surrogate_id)

        return result

    def _split_extra_columns(self, source, extra_columns) -> tuple[dict[str, str], dict[str, Any]]:
        """Split extra columns into those that copy existing source columns and those that are constants."""
        extra_source_columns: dict[str, str] = {k: v for k, v in extra_columns.items() if isinstance(v, str) and v in source.columns}
        extra_constant_columns: dict[str, Any] = {
            new_name: value for new_name, value in extra_columns.items() if new_name not in extra_source_columns
        }

        return extra_source_columns, extra_constant_columns

    def _check_if_missing_requested_columns(
        self, source: pd.DataFrame, entity_name: str, raise_if_missing: bool, all_requested_columns: set[str]
    ) -> None:
        missing_requested_columns: list[str] = [c for c in all_requested_columns if c not in source.columns]
        if missing_requested_columns:
            if raise_if_missing:
                raise ValueError(f"{entity_name}[subsetting]: Columns not found in DataFrame: {missing_requested_columns}")
            else:
                logger.warning(
                    f"{entity_name}[subsetting]: Columns not found in DataFrame and will be skipped: {missing_requested_columns}"
                )

    def _restore_columns_order(self, data: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
        """Reorder columns in DataFrame to match specified order."""
        columns_in_result: list[str] = [c for c in columns if c in data.columns] + [c for c in data.columns if c not in columns]
        return data[columns_in_result]

    def _drop_empty_rows(self, *, data: pd.DataFrame, entity_name: str, subset: list[str] | None = None) -> pd.DataFrame:
        """Drop rows that are completely empty in the DataFrame or in the specified subset of columns."""
        if isinstance(subset, list):
            missing_requested_columns: list[str] = [c for c in subset if c not in data.columns]
            if missing_requested_columns:
                logger.warning(f"{entity_name}[subsetting]: Columns missing for drop_empty_rows: {missing_requested_columns}")
                return data
            return data.dropna(subset=subset, how="all")
        return data.dropna(how="all")

    def _drop_duplicates(
        self, data: pd.DataFrame, columns: bool | list[str] = False, fd_check: bool = False, entity_name: str | None = None
    ) -> pd.DataFrame:
        if not isinstance(columns, list):
            return data.drop_duplicates().reset_index(drop=True)
        if set(columns).difference(data.columns):
            missing_rquested_columns = set(columns).difference(data.columns)
            logger.warning(
                f"{entity_name}[subsetting]: Some columns specified for drop_duplicates are missing from DataFrame and will be ignored: {missing_rquested_columns}"
            )
        columns = [c for c in columns if c in data.columns]
        if not columns:
            logger.warning(
                f"{entity_name}[subsetting]: No valid columns specified for drop_duplicates after filtering missing columns. No duplicates will be dropped."
            )
            return data
        if fd_check:
            check_functional_dependency(data, determinant_columns=columns, raise_error=True)
        data = data.drop_duplicates(subset=columns).reset_index(drop=True)
        return data


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
    """Backward-compatible convenience function to get subset using SubsetService."""
    return SubsetService().get_subset(
        source=source,
        columns=columns,
        entity_name=entity_name,
        extra_columns=extra_columns,
        drop_duplicates=drop_duplicates,
        fd_check=fd_check,
        raise_if_missing=raise_if_missing,
        surrogate_id=surrogate_id,
        drop_empty_rows=drop_empty_rows,
    )


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


def extract_translation_map(
    fields_metadata: list[dict[str, str]], from_field: str = "arbodat_field", to_field: str = "english_column_name"
) -> dict[str, str]:
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
