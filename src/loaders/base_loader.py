import abc
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import pandas as pd

from src.utility import Registry

if TYPE_CHECKING:
    from src.model import DataSourceConfig, TableConfig


# pylint: disable=unused-argument


@dataclass
class ConnectTestResult:

    success: bool
    message: str
    connection_time_ms: int
    metadata: dict[str, Any]

    @property
    def connection_time_seconds(self) -> float:
        """Get connection time in seconds."""
        return self.connection_time_ms / 1000.0

    @staticmethod
    def create_empty(success: bool = False) -> "ConnectTestResult":
        return ConnectTestResult(
            success=success,
            message="No test performed",
            connection_time_ms=0,
            metadata={},
        )


class DataLoader(abc.ABC):

    def __init__(self, data_source: "DataSourceConfig | None" = None) -> None:
        self.data_source: "DataSourceConfig | None" = data_source

    @abc.abstractmethod
    async def load(self, entity_name: str, table_cfg: "TableConfig") -> pd.DataFrame:
        pass

    @abc.abstractmethod
    async def test_connection(self) -> ConnectTestResult:
        pass


class DataLoaderRegistry(Registry):

    items: dict[str, type[DataLoader]] = {}


DataLoaders: DataLoaderRegistry = DataLoaderRegistry()  # pylint: disable=invalid-name
