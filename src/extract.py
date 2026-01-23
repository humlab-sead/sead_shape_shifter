from collections.abc import Mapping
from typing import Any

import pandas as pd
from loguru import logger

from src.transforms.drop import drop_duplicate_rows, drop_empty_rows
from src.model import TableConfig
from src.utility import unique

# pylint: disable=line-too-long



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
        replacements: dict[str, Any] | None = None,
        raise_if_missing: bool = True,
        drop_empty: bool | list[str] | dict[str, Any] = False,
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
            replacements (dict[str, Any] | None): Column-specific value replacement mappings.
                Dictionary where keys are column names and values are dicts mapping old values to new values.
                Replacements are applied after column extraction. Useful for normalizing values,
                converting codes to standard formats, or correcting inconsistent data.
            raise_if_missing (bool): Whether to raise an error if requested columns are missing.
            drop_empty (bool | list[str] | dict[str, Any]): Controls empty row removal.
                - If True: drop rows where all columns are empty
                - If False: keep all rows
                - If list[str]: drop rows where all specified columns are empty
                - If dict[str, Any]: drop rows where specified columns contain the given values
                  (keys are column names, values are lists of values to treat as empty)

        Returns:
            pd.DataFrame: Resulting DataFrame with requested columns and modifications.

        Examples:
            >>> df = pd.DataFrame({'A': [1, 2], 'B': [3, 4], 'C': [5, 6]})
            >>> # Extract A and B, add copy of C to D
            >>> get_subset(df, ['A', 'B'], extra_columns={'D': 'C'})
            >>> # Extract A and B, add constant column D
            >>> get_subset(df, ['A', 'B'], extra_columns={'D': 'constant_value'})
            >>> # Replace values in column A
            >>> get_subset(df, ['A', 'B'], replacements={'A': {1: 10, 2: 20}})
            >>> # Replace coordinate system codes
            >>> get_subset(df, ['site', 'coord_sys'],
            ...            replacements={'coord_sys': {'DHDN Zone 3': 'EPSG:31467'}})
        """
        if source is None:
            raise ValueError("Source DataFrame must be provided")

        entity_name = entity_name or "unspecified"
        columns = unique(columns)
        extra_columns = extra_columns or {}

        extra_source_columns, extra_constant_columns = self._split_extra_columns(source, extra_columns, case_sensitive=False)
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
            result = drop_duplicate_rows(
                result,
                columns=drop_duplicates,
                fd_check=table_cfg.check_functional_dependency,
                entity_name=entity_name,
            )

        result = self._restore_columns_order(result, columns)

        # Drop rows that are completely empty after subsetting
        if drop_empty:
            result = drop_empty_rows(data=result, entity_name=entity_name, subset=None if drop_empty is True else drop_empty)

        if replacements:
            for col, replacement_map in replacements.items():
                if col in result.columns:
                    # `Series.replace(to_replace=<scalar/list>)` previously defaulted to `method="pad"` when `value` was omitted,
                    # but that behavior is deprecated. Support both:
                    # - Mapping: explicit old->new replacements
                    # - Scalar/list: treat as "values to blank out", then forward-fill (legacy pad behavior)
                    if isinstance(replacement_map, Mapping):
                        result[col] = result[col].replace(to_replace=replacement_map)
                    else:
                        result[col] = result[col].replace(to_replace=replacement_map, value=pd.NA).ffill()

        return result

    def _split_extra_columns(
        self, source: pd.DataFrame, extra_columns: dict[str, Any], case_sensitive: bool = False
    ) -> tuple[dict[str, str], dict[str, Any]]:
        """Split extra columns into those that copy existing source columns and those that are constants."""
        source_columns: dict[str, str]
        if not case_sensitive:
            source_columns_lower: dict[str, str] = {col.lower(): col for col in source.columns}
            source_columns = {
                k: source_columns_lower[v.lower()]
                for k, v in extra_columns.items()
                if isinstance(v, str) and v.lower() in source_columns_lower
            }
        else:
            source_columns = {k: v for k, v in extra_columns.items() if isinstance(v, str) and v in source.columns}

        constant_columns: dict[str, Any] = {new_name: value for new_name, value in extra_columns.items() if new_name not in source_columns}

        return source_columns, constant_columns

    def _check_if_missing_requested_columns(
        self, source: pd.DataFrame, entity_name: str, raise_if_missing: bool, all_requested_columns: set[str]
    ) -> None:
        missing_requested_columns: list[str] = [c for c in all_requested_columns if c not in source.columns]
        if missing_requested_columns:
            if raise_if_missing:
                raise ValueError(f"{entity_name}[subsetting]: Columns not found in DataFrame: {missing_requested_columns}")
            logger.warning(f"{entity_name}[subsetting]: Columns not found in DataFrame and will be skipped: {missing_requested_columns}")

    def _restore_columns_order(self, data: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
        """Reorder columns in DataFrame to match specified order."""
        columns_in_result: list[str] = [c for c in columns if c in data.columns] + [c for c in data.columns if c not in columns]
        return data[columns_in_result]

