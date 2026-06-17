from typing import Any, Protocol, Type, runtime_checkable

# pylint: disable=unused-argument


@runtime_checkable
class ConfigLike(Protocol):
    filename: str | None
    data: dict[str, Any]

    def get(self, *keys: str, default: Any | Type[Any] = None, mandatory: bool = False) -> Any: ...
    def exists(self, *keys: str) -> bool: ...
    def update(self, data: tuple[str, Any] | dict[str, Any] | list[tuple[str, Any]]) -> None: ...
    def save(self, updates: dict[str, Any] | None = None) -> None: ...
