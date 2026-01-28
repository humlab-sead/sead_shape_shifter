import abc
from dataclasses import dataclass
from enum import StrEnum
from turtle import st
from typing import TYPE_CHECKING, Any, ClassVar

import pandas as pd

from src.utility import Registry

if TYPE_CHECKING:
    from src.loaders.driver_metadata import DriverSchema
    from src.model import DataSourceConfig, TableConfig


# pylint: disable=unused-argument


class LoaderType(StrEnum):
    BASE = "base"
    FILE = "file"
    SQL = "sql"
    VALUE = "value"


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
    """Base class for all data loaders.

    Subclasses should define a 'schema' class variable to describe
    their configuration fields for dynamic form generation.
    """

    @classmethod
    def loader_type(cls) -> LoaderType:
        """Get the loader type (e.g., 'file', 'sql', 'value')."""
        return LoaderType.BASE

    # Subclasses can define their schema for configuration metadata
    schema: ClassVar["DriverSchema | None"] = None

    def __init__(self, data_source: "DataSourceConfig | None" = None) -> None:
        self.data_source: "DataSourceConfig | None" = data_source

    @classmethod
    def get_schema(cls) -> "DriverSchema | None":
        """Get loader configuration schema.

        Returns:
            DriverSchema if defined, None otherwise
        """
        return cls.schema

    @abc.abstractmethod
    async def load(self, entity_name: str, table_cfg: "TableConfig") -> pd.DataFrame:
        pass

    @abc.abstractmethod
    async def test_connection(self) -> ConnectTestResult:
        pass


class DataLoaderRegistry(Registry):

    items: dict[str, type[DataLoader]] = {}

    def get_loader_types(self) -> set[str]:
        """Get the set of loader types registered."""
        return {loader_cls.loader_type().value for loader_cls in self.items.values()}

    def get_loader_keys_by_type(self, loader_type: LoaderType) -> set[str]:
        """Get loader keys filtered by loader type."""
        return {cls._registry_key for _, cls in self.items.items() if cls.loader_type() == loader_type}


DataLoaders: DataLoaderRegistry = DataLoaderRegistry()  # pylint: disable=invalid-name
