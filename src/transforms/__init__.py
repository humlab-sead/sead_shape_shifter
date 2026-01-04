import abc
from pathlib import Path

import pandas as pd

from src.utility import Registry

# pylint: disable=unused-argument


class Transformer(abc.ABC):

    def is_satisfied(self, data: pd.DataFrame, columns: list[str] | str, **opts) -> bool:
        return True

    def apply(self, data: pd.DataFrame, columns: list[str] | str, **opts) -> pd.DataFrame:
        return data


class TransformerRegistry(Registry):

    items: dict[str, type["Transformer"]] = {}


Transformers: TransformerRegistry = TransformerRegistry().scan(__name__, Path(__file__).parent)  # pylint: disable=invalid-name
