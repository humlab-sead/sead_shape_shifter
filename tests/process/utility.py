from typing import Any

import pandas as pd

from src.extract import SubsetService


def get_subset(
    source: pd.DataFrame,
    columns: list[str],
    *,
    entity_name: str | None = None,
    extra_columns: None | dict[str, Any] = None,
    drop_duplicates: bool | list[str] = False,
    fd_check: bool = False,
    replacements: dict[str, Any] | None = None,
    raise_if_missing: bool = True,
    drop_empty_rows: bool | list[str] | dict[str, Any] = False,
) -> pd.DataFrame:
    """Backward-compatible convenience function to get subset using SubsetService."""
    return SubsetService().get_subset(
        source=source,
        columns=columns,
        entity_name=entity_name,
        extra_columns=extra_columns,
        drop_duplicates=drop_duplicates,
        fd_check=fd_check,
        replacements=replacements,
        raise_if_missing=raise_if_missing,
        drop_empty=drop_empty_rows,
    )
