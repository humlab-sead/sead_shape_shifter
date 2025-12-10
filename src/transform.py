
import abc
from src.utility import Registry

import pandas as pd

class TransformerRegistry(Registry):
    
    items: dict[str, type["Transformer"]] = {}

Transformers: TransformerRegistry = TransformerRegistry()


class Transformer(abc.ABC):

    def apply(self, data: pd.DataFrame, columns: list[str]| str, **opts) -> pd.DataFrame:
        return data

class NoOpTransformer(Transformer):
    pass

Transformers.register(key="geo_split")
class TransformSplitLatLong(Transformer):
    
    def apply(self, data: pd.DataFrame, columns: list[str] | str, **opts) -> pd.DataFrame:
        """Transforms geographical points from 'lat,lon' string format to separate float columns."""
        if isinstance(columns, str):
            columns = [columns]
        
        return data