from typing import Any

import pandas as pd
from loguru import logger

from src.specifications.base import Specification


class FunctionalDependencySpecification(Specification):
    """Specification for checking functional dependencies when dropping duplicates.

    This check is needed because droping duplicates is an important step indata normalization.

    Given a DataFrame with columns [ key-columns..., other-columns...] this specification
    checks that other-columns are functionally dependent on key-columns, i.e., for each unique
    combination of key-columns, the values in other-columns are constant.

    If FD check fails, then we probably have defined the wrong key-columns.

    AI-way of putting it: Note Functional Dependency (FD): In a dataset, a set of columns A functionally
    determines another set of columns B if, for every unique combination of values in A,
    there is exactly one corresponding combination of values in B.

    """

    def check_functional_dependency_original_to_sloq(
        self, *, df: pd.DataFrame, determinant_columns: list[str], raise_error: bool = True
    ) -> bool:
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
            logger.warning(f"[fd_check]: {msg}")

        return len(bad_keys) == 0

    def is_satisfied_by(
        self,
        *,
        df: pd.DataFrame | None = None,
        determinant_columns: list[str] | None = None,
        raise_error: bool = True,
        max_bad_keys: int = 5,
        **kwargs,
    ) -> bool:
        """
        NOTE: ChatGPT-5.2 optimized version of functional dependency check.
        Check functional dependency: for each unique combination of determinant_columns,
        all other columns must be consistent.

        """

        # This is only to silence type checking warnings of override having different signature
        assert df is not None, "DataFrame 'df' must be provided"
        assert determinant_columns is not None, "List of 'determinant_columns' must be provided"

        # Dependent columns = everything else
        dependent_columns: list[str] = [c for c in df.columns if c not in determinant_columns]
        if not dependent_columns:
            return True

        cols: list[str] = determinant_columns + dependent_columns

        # Keep only distinct (determinant + dependent) rows.
        # If a determinant maps to >1 distinct dependent-row, FD is violated.
        distinct: pd.DataFrame = df[cols].drop_duplicates()

        # Count how many distinct dependent-rows each determinant has
        counts: pd.Series[int] = distinct.groupby(determinant_columns, sort=False, dropna=False).size()

        bad: pd.Series[int] = counts[counts > 1]
        if bad.empty:
            return True

        # Compile error message
        bad_keys: list[Any] = bad.index.tolist()
        more_msg: str = "" if len(bad_keys) <= max_bad_keys else f" (showing first {max_bad_keys} of {len(bad_keys)})"
        msg: str = f"inconsistent non-subset values for keys: {bad_keys[:max_bad_keys]}{more_msg}"

        self.add_error(msg, entity=kwargs.get("entity_name"))

        if raise_error:
            raise ValueError(f"[fd_check]: {msg}")

        logger.warning(f"[fd_check]: {msg}")

        return self.has_errors() is False
