import abc
from re import A
from typing import Any
from src.utility import Registry

import pandas as pd


class TransformerRegistry(Registry):

    items: dict[str, type["Transformer"]] = {}


Transformers: TransformerRegistry = TransformerRegistry()


class Transformer(abc.ABC):

    def apply(self, data: pd.DataFrame, columns: list[str] | str, **opts) -> pd.DataFrame:
        return data


Transformers.register(key="translate")


class TranslateTransformer(abc.ABC):
    """Given a mapping dict, transform values in specified columns."""

    def apply(self, data: pd.DataFrame, columns: list[str] | str, *, mapping: dict[Any, Any], **opts) -> pd.DataFrame:
        df: pd.DataFrame = data.copy()
        for col in [columns] if isinstance(columns, str) else columns:
            df[col] = df[col].map(mapping).fillna(df[col])
        return df
