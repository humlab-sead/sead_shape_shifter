from typing import Any
from venv import logger

import pandas as pd

from src.config_model import TableConfig
from src.utility import Registry


class FilterRegistry(Registry):

    items: dict[str, Any] = {}


Filters = FilterRegistry()  # pylint: disable=invalid-name


def apply_filters(
    name: str,
    df: pd.DataFrame,
    cfg: TableConfig,
    data_store: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """Apply post-load filters defined in the entity config."""
    for f in cfg.filters:
        ftype = f.get("type")
        if not ftype:
            logger.warning(f"Filter for entity {name!r} missing 'type' field")
            continue

        filter_cls = Filters.get(ftype)
        if filter_cls is None:
            raise ValueError(f"Unknown filter type for entity {name!r}: {ftype!r}")
        df = filter_cls().apply(df, f, data_store)

    return df


@Filters.register(key="exists_in")
class ExistsInFilter:
    """Filter to keep rows where a column's value exists in another entity's column."""

    key: str = "exists_in"

    def apply(self, df: pd.DataFrame, filter_cfg: dict[str, Any], data_store: dict[str, pd.DataFrame]) -> pd.DataFrame:

        if any(k not in filter_cfg for k in ("column", "other_entity")):
            raise ValueError("Filter 'exists_in' requires 'column' and 'other_entity' parameters")

        column: str = filter_cfg["column"]
        other_entity: str = filter_cfg["other_entity"]
        other_column: str = filter_cfg.get("other_column", column)

        if other_entity not in data_store:
            raise ValueError(f"Filter 'exists_in' references unknown entity: {other_entity!r}")

        other_df: pd.DataFrame = data_store[other_entity]

        values: set[Any] = set(other_df[other_column].unique())
        filtered_df = df[df[column].isin(values)]

        # Optionally drop duplicates
        drop_duplicates_cols = filter_cfg.get("drop_duplicates")
        if drop_duplicates_cols:
            filtered_df: pd.DataFrame = filtered_df.drop_duplicates(subset=drop_duplicates_cols)

        return filtered_df
