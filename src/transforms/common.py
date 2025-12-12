import abc
from typing import Any

import pandas as pd


class TranslateTransformer(abc.ABC):
    """Given a mapping dict, transform values in specified columns."""

    def apply(
        self, data: pd.DataFrame, columns: list[str] | str, *, mapping: dict[Any, Any], **opts  # pylint: disable=unused-argument
    ) -> pd.DataFrame:
        df: pd.DataFrame = data.copy()
        for col in [columns] if isinstance(columns, str) else columns:
            df[col] = df[col].map(mapping).fillna(df[col])
        return df
