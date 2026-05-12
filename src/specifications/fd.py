from typing import Any

import pandas as pd
from loguru import logger
from pandas.core.groupby.generic import DataFrameGroupBy

from src.exceptions import FunctionalDependencyError
from src.specifications.base import Specification


class FunctionalDependencySpecification(Specification):
    """Specification for checking functional dependencies when dropping duplicates.

    This check is needed because dropping duplicates is an important step in data normalization.

    Given a DataFrame with columns [ key-columns..., other-columns...] this specification
    checks that other-columns are functionally dependent on key-columns, i.e., for each unique
    combination of key-columns, the values in other-columns are constant.

    If FD check fails, then we probably have defined the wrong key-columns.

    AI-way of putting it: Note Functional Dependency (FD): In a dataset, a set of columns A functionally
    determines another set of columns B if, for every unique combination of values in A,
    there is exactly one corresponding combination of values in B.

    """

    def is_satisfied_by(
        self,
        *,
        df: pd.DataFrame | None = None,
        determinant_columns: list[str] | None = None,
        strict: bool = True,
        max_bad_keys: int = 5,
        max_example_rows: int = 3,
        **kwargs,
    ) -> bool:
        """
        Check functional dependency: for each unique combination of determinant_columns,
        all other columns must be consistent.
        """

        assert df is not None, "DataFrame 'df' must be provided"
        assert determinant_columns is not None, "List of 'determinant_columns' must be provided"

        dependent_columns: list[str] = [c for c in df.columns if c not in determinant_columns]
        if not dependent_columns:
            return True

        cols: list[str] = determinant_columns + dependent_columns

        distinct: pd.DataFrame = df[cols].drop_duplicates()

        grouped: DataFrameGroupBy = distinct.groupby(determinant_columns, sort=False, dropna=False)
        counts: pd.Series = grouped.size()

        bad: pd.Series = counts[counts > 1]
        if bad.empty:
            return True

        msg: str = self.compile_error_message(
            max_bad_keys=max_bad_keys,
            bad=bad,
            grouped=grouped,
            determinant_columns=determinant_columns,
            dependent_columns=dependent_columns,
            max_example_rows=max_example_rows,
        )

        self.add_error(msg, entity=kwargs.get("entity_name"))

        if strict:
            raise FunctionalDependencyError(
                f"[fd_check]: {msg}",
                entity_name=kwargs.get("entity_name"),
                determinant_columns=determinant_columns,
                details={"bad_keys": bad.index.tolist(), "max_bad_keys": max_bad_keys},
            )

        logger.error(f"[fd_check]: {msg}")

        return self.has_errors() is False

    def compile_error_message(
        self,
        *,
        max_bad_keys: int,
        bad: pd.Series,
        grouped: DataFrameGroupBy,
        determinant_columns: list[str],
        dependent_columns: list[str],
        max_example_rows: int = 3,
    ) -> str:
        bad_keys: list[Any] = bad.index.tolist()
        more_msg: str = "" if len(bad_keys) <= max_bad_keys else f" (showing first {max_bad_keys} of {len(bad_keys)})"
        lines: list[str] = [f"values vary within keyset: {bad_keys[:max_bad_keys]}{more_msg}"]

        for key in bad_keys[:max_bad_keys]:
            key_tuple = key if isinstance(key, tuple) else (key,)
            group: pd.DataFrame = grouped.get_group(key)
            violating_columns: list[str] = [col for col in dependent_columns if group[col].nunique(dropna=False) > 1]
            example_columns: list[str] = determinant_columns + violating_columns
            examples: pd.DataFrame = group[example_columns].head(max_example_rows)
            lines.append(
                "\n"
                f"key={dict(zip(determinant_columns, key_tuple))}; "
                f"violating_columns={violating_columns}; "
                f"examples:\n{examples.to_string(index=False)}"
            )

        return "\n".join(lines)
