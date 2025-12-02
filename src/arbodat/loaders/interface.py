import abc
import pandas as pd

from src.arbodat.config_model import TableConfig


class DataLoader(abc.ABC):

    @abc.abstractmethod
    async def load(self, entity_name: str, table_cfg: TableConfig) -> pd.DataFrame:
        pass
