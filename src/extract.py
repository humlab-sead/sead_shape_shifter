from __future__ import annotations

from typing import Any

import pandas as pd
from loguru import logger

from src.model import TableConfig
from src.transforms.drop import drop_duplicate_rows, drop_empty_rows
from src.transforms.extra_columns import ExtraColumnEvaluator
from src.transforms.replace import apply_replacements
from src.utility import unique

# pylint: disable=line-too-long


class SubsetService:
    """Class for extracting subsets from DataFrames with various options."""

    def __init__(self):
        """Initialize SubsetService with ExtraColumnEvaluator."""
        self.extra_col_evaluator = ExtraColumnEvaluator()

    def get_subset_columns(self, table_cfg: TableConfig) -> list[str]:
        """Get the list of columns to extract from the table configuration.
        Excludes un-nested columns and extra columns from remote FK tables."""
        columns: list[str] = table_cfg.keys_columns_and_fks
        # Ignore columns that will be added via un-nesting
        if table_cfg.unnest:
            columns = [col for col in columns if col not in table_cfg.unnest_columns]
        # Ignore extra columns added when linking remote FK tables
        for fk in table_cfg.foreign_keys:
            if fk.extra_columns:
                columns = [col for col in columns if col not in fk.extra_columns.keys()]
        return columns

    def get_subset(
        self,
        source: pd.DataFrame,
        table_cfg: TableConfig,
        *,
        drop_empty: None | bool | list[str] | dict[str, Any] = None,
        raise_if_missing: bool = True,
    ) -> pd.DataFrame:
        """Return a subset of the source DataFrame with specified columns, optional extra columns, and duplicate handling."""
        if source is None:
            raise ValueError("Source DataFrame must be provided")

        columns: list[str] = unique(self.get_subset_columns(table_cfg))
        column_aliases: dict[str, str] = self._get_source_identity_aliases(table_cfg, columns)
        entity_name: str = table_cfg.entity_name or "unspecified"
        extra_columns: dict[str, str] = table_cfg.extra_columns or {}
        drop_duplicates: bool | list[str] = table_cfg.drop_duplicates if not table_cfg.is_drop_duplicate_dependent_on_unnesting() else False
        replacements: dict[str, dict[Any, Any]] | None = table_cfg.replacements if table_cfg.replacements else None

        if drop_empty is None:
            drop_empty = table_cfg.drop_empty_rows

        return self.get_subset2(
            source,
            columns,
            entity_name=entity_name,
            column_aliases=column_aliases,
            extra_columns=extra_columns,
            drop_duplicates=drop_duplicates,
            fd_check=table_cfg.check_functional_dependency,
            strict_fd_check=table_cfg.strict_functional_dependency,
            replacements=replacements,
            raise_if_missing=raise_if_missing,
            drop_empty=drop_empty,
        )

    def get_subset2(
        self,
        source: pd.DataFrame,
        columns: list[str],
        *,
        entity_name: str | None = None,
        column_aliases: None | dict[str, str] = None,
        extra_columns: None | dict[str, Any] = None,
        drop_duplicates: bool | list[str] = False,
        fd_check: bool = False,
        strict_fd_check: bool = False,
        replacements: dict[str, Any] | None = None,
        raise_if_missing: bool = True,
        drop_empty: bool | list[str] | dict[str, Any] = False,
    ) -> pd.DataFrame:
        """Return a subset of the source DataFrame with specified columns, optional extra columns, and duplicate handling.
        Args:
            source (pd.DataFrame): Source DataFrame.
            columns (list[str]): List of column names to include from source.
            column_aliases (dict[str, str] | None): Output column aliases resolved from source columns.
                Mapping format: {output_column_name: source_column_name}
                Used when a result column should expose a different name than the source column,
                while still behaving like a normal selected column during subsetting.
            extra_columns (dict[str, Any] | None): Extra columns mapping:
                {new_column_name: source_column_name_or_constant}
                - If value is a string matching source column, then copy that column
                - Otherwise: add new column with the constant value
            drop_duplicates (bool | list[str]): Whether to drop duplicates.
                - If True: drop all duplicate rows
                - If list: drop duplicates based on those columns
                - If False: keep all rows
            fd_check (bool): Whether to check functional dependency when dropping duplicates.
            strict_fd_check (bool): Whether to raise an error on FD violation (if fd_check is True).
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
        column_aliases = column_aliases or {}
        extra_columns = extra_columns or {}

        selected_aliases: dict[str, str] = {alias: source_col for alias, source_col in column_aliases.items() if alias in columns}
        extra_source_columns, _ = self.extra_col_evaluator.split_extra_columns(source, extra_columns, case_sensitive=False)

        # Columns we need to read from source to build the result
        required_source_cols: set[str] = {selected_aliases.get(column_name, column_name) for column_name in columns} | set(
            extra_source_columns.values()
        )

        self._check_if_missing_requested_columns(source, entity_name, raise_if_missing, required_source_cols)

        # Extract only columns that exist (in source order)
        columns_to_extract: list[str] = [c for c in source.columns if c in required_source_cols]
        result: pd.DataFrame = source.loc[:, columns_to_extract].copy()

        # Add alias columns that should appear as ordinary selected columns in the result.
        for alias, source_column in selected_aliases.items():
            if source_column in result.columns:
                result[alias] = result[source_column]

        # Use ExtraColumnEvaluator to add extra columns (supports constants, copies, and interpolations)
        if extra_columns:
            result, deferred = self.extra_col_evaluator.evaluate_extra_columns(
                df=result,
                extra_columns=extra_columns,
                entity_name=entity_name,
                defer_missing=True,  # Allow deferring columns that reference missing columns
            )

            # Log deferred columns (they'll be re-evaluated later by normalizer)
            if deferred:
                logger.trace(f"{entity_name}[extract]: Deferred extra_columns evaluation for: {list(deferred.keys())}")

        # Drop helper source columns that weren't explicitly requested
        helper_cols: set[str] = (set(extra_source_columns.values()) | set(selected_aliases.values())) - set(columns)
        if helper_cols:
            result = result.drop(columns=list(helper_cols))

        # Handle duplicate removal
        if drop_duplicates:
            result = drop_duplicate_rows(
                result,
                columns=drop_duplicates,
                entity_name=entity_name,
                fd_check=fd_check,
                strict_fd_check=strict_fd_check,
            )

        result = self._restore_columns_order(result, columns)

        # Drop rows that are completely empty after subsetting
        if drop_empty:
            result = drop_empty_rows(data=result, entity_name=entity_name, subset=None if drop_empty is True else drop_empty)

        if replacements:
            result = apply_replacements(result, replacements=replacements, entity_name=entity_name)

        return result

    def _check_if_missing_requested_columns(
        self, source: pd.DataFrame, entity_name: str, raise_if_missing: bool, all_requested_columns: set[str]
    ) -> None:
        missing: list[str] = [c for c in all_requested_columns if c not in source.columns]
        if missing:
            if raise_if_missing:
                raise ValueError(f"{entity_name}[subsetting]: Columns not found in DataFrame: {missing}")
            logger.warning(f"{entity_name}[subsetting]: Columns not found in DataFrame and will be skipped: {missing}")

    def _restore_columns_order(self, data: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
        """Reorder columns in DataFrame to match specified order."""
        columns_in_result: list[str] = [c for c in columns if c in data.columns] + [c for c in data.columns if c not in columns]
        return data[columns_in_result]

    def _get_source_identity_aliases(self, table_cfg: TableConfig, columns: list[str]) -> dict[str, str]:
        """Expose the source entity's public_id as a selected column backed by source system_id."""
        entity_type: str | None = getattr(table_cfg, "type", None)
        source_entity_name: str | None = getattr(table_cfg, "source", None)
        entities_cfg: dict[str, dict[str, Any]] | None = getattr(table_cfg, "entities_cfg", None)

        if entity_type != "entity" or not source_entity_name or not isinstance(entities_cfg, dict):
            return {}

        if source_entity_name not in entities_cfg:
            return {}

        source_cfg = TableConfig(entities_cfg=entities_cfg, entity_name=source_entity_name)
        source_public_id: str = source_cfg.public_id
        local_public_id: str = getattr(table_cfg, "public_id", "") or ""
        extra_columns: dict[str, Any] = getattr(table_cfg, "extra_columns", {}) or {}

        if not source_public_id or source_public_id not in columns:
            return {}

        if source_public_id == local_public_id:
            return {}

        if source_public_id in extra_columns:
            return {}

        return {source_public_id: source_cfg.system_id}
