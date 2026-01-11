import abc
import importlib
import os
from typing import Any

from loguru import logger
from psycopg import Connection

from backend.app.ingesters.sead.utility import Registry


class BaseUploader(abc.ABC):
    @abc.abstractmethod
    def upload(self, connection: Connection, source: str | Any, submission_id: int) -> None:
        pass

    @abc.abstractmethod
    def extract(self, connection: Connection, submission_id: int) -> None:
        pass


class NullUploader(BaseUploader):
    def upload(self, connection: Connection, source: str | Any, submission_id: int) -> None:  # pylint: disable=unused-argument
        raise ValueError("No uploader specified")

    def extract(self, connection: Connection, submission_id: int) -> None:  # pylint: disable=unused-argument
        raise ValueError("No uploader specified")


class UnknownUploader(BaseUploader):

    def upload(self, connection: Connection, source: str | Any, submission_id: int) -> None:  # pylint: disable=unused-argument
        raise ValueError("Invalid uploader specified")

    def extract(self, connection: Connection, submission_id: int) -> None:  # pylint: disable=unused-argument
        raise ValueError("Invalid uploader specified")


class UploaderRegistry(Registry[type[BaseUploader]]):

    items: dict[str, type[BaseUploader]] = {}

    @classmethod
    def get(cls, key: str) -> type[BaseUploader]:
        return cls.items.get(key, UnknownUploader)


Uploaders: UploaderRegistry = UploaderRegistry()  # pylint: disable=invalid-name


__all__ = []
current_dir: str = os.path.dirname(__file__)
for filename in os.listdir(current_dir):
    if filename.endswith(".py") and filename != "__init__.py":
        module_name: str = filename[:-3]
        __all__.append(module_name)  # type: ignore
        importlib.import_module(f".{module_name}", package=__name__)
