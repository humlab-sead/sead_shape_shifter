import abc
import io

from backend.app.ingesters.sead.utility import Registry

from ..metadata import SeadSchema
from ..submission import Submission


class IDispatcher(abc.ABC):

    def dispatch(
        self,
        target: str,
        schema: SeadSchema,
        submission: Submission,
        table_names: list[str] | None = None,
        extra_names: list[str] | None = None,
    ):
        raise NotImplementedError


class DispatcherRegistry(Registry[type[IDispatcher]]):
    """Registry for dispatcher classes."""

    _registry: dict[str, type[IDispatcher]] = {}


Dispatchers = DispatcherRegistry()  # pylint: disable=invalid-name
