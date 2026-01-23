import abc
from typing import Any

import pandas as pd

from pathlib import Path

from src.utility import Registry

# pylint: disable=unused-argument


class Transformer(abc.ABC):

    def is_satisfied(self, data: pd.DataFrame, columns: list[str] | str, **opts) -> bool:
        return True

    def apply(self, data: pd.DataFrame, columns: list[str] | str, **opts) -> pd.DataFrame:
        return data


class TransformerRegistry(Registry):

    items: dict[str, type["Transformer"]] = {}


Transformers: TransformerRegistry = TransformerRegistry().scan(__name__, str(Path(__file__).parent))  # pylint: disable=invalid-name


class TranslateTransformer(abc.ABC):
    """Given a mapping dict, transform values in specified columns."""

    def apply(
        self, data: pd.DataFrame, columns: list[str] | str, *, mapping: dict[Any, Any], **opts  # pylint: disable=unused-argument
    ) -> pd.DataFrame:
        df: pd.DataFrame = data.copy()
        for col in [columns] if isinstance(columns, str) else columns:
            df[col] = df[col].map(mapping).fillna(df[col])
        return df
