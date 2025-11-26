import pandas as pd
from loguru import logger


def add_surrogate_id(target: pd.DataFrame, id_name: str) -> pd.DataFrame:
    """Add an integer surrogate ID starting at 1."""
    target = target.reset_index(drop=True).copy()
    target[id_name] = range(1, len(target) + 1)
    return target


def get_subset(
    source: pd.DataFrame,
    columns: list[str],
    drop_duplicates: bool | list[str] = False,
    raise_if_missing: bool = True,
    surrogate_id: str | None = None,
) -> pd.DataFrame:
    """Return data with only the columns that actually exist and drop duplicates if requested."""
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

    if drop_duplicates:
        if isinstance(drop_duplicates, list):
            result = result.drop_duplicates(subset=drop_duplicates)
        else:
            result = result.drop_duplicates()

    if surrogate_id and surrogate_id not in result.columns:
        result = add_surrogate_id(result, surrogate_id)

    return result
