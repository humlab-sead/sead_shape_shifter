import abc
from typing import TYPE_CHECKING

import pandas as pd

from src.utility import Registry

if TYPE_CHECKING:
    from src.config_model import DataSourceConfig, TableConfig


# pylint: disable=unused-argument


class DataLoader(abc.ABC):

    def __init__(self, data_source: "DataSourceConfig | None" = None) -> None:
        self.data_source: "DataSourceConfig | None" = data_source

    @abc.abstractmethod
    async def load(self, entity_name: str, table_cfg: "TableConfig") -> pd.DataFrame:
        pass


class DataLoaderRegistry(Registry):

    items: dict[str, type[DataLoader]] = {}


DataLoaders: DataLoaderRegistry = DataLoaderRegistry()  # pylint: disable=invalid-name
