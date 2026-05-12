from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Callable, Iterable, Iterator, Mapping, overload

if TYPE_CHECKING:
    from _typeshed import SupportsKeysAndGetItem

import pandas as pd

TableSetHook = Callable[[str, pd.DataFrame], None]
TableDeleteHook = Callable[[str], None]


class TableStore(dict[str, pd.DataFrame]):
    """Dictionary-like entity store with hooks.

    Hooks fire when an entity DataFrame is assigned/replaced or deleted.

    Important:
        Hooks do not fire on in-place DataFrame mutation, e.g.
        table_store["samples"]["x"] = ...
    """

    def __init__(
        self,
        initial: Mapping[str, pd.DataFrame] | Iterable[tuple[str, pd.DataFrame]] | None = None,
        **kwargs: pd.DataFrame,
    ) -> None:
        super().__init__()

        self._on_set_hooks: list[TableSetHook] = []
        self._on_delete_hooks: list[TableDeleteHook] = []

        self._hooks_suspended: bool = False
        self._pending_set: set[str] = set()
        self._pending_delete: set[str] = set()

        if initial is not None:
            self.update(initial)

        if kwargs:
            self.update(kwargs)

    def add_on_set_hook(self, hook: TableSetHook, *, replay: bool = True) -> None:
        """Register a hook called after an entity is assigned.

        Args:
            hook: Function receiving `(entity_name, dataframe)`.
            replay: If true, immediately call the hook for existing items.
        """
        self._on_set_hooks.append(hook)

        if replay:
            for key, value in self.items():
                hook(key, value)

    def add_on_delete_hook(self, hook: TableDeleteHook) -> None:
        """Register a hook called after an entity is deleted."""
        self._on_delete_hooks.append(hook)

    def __setitem__(self, key: str, value: pd.DataFrame) -> None:
        if not isinstance(value, pd.DataFrame):
            raise TypeError(f"TableStore values must be pandas DataFrames, got {type(value)!r} for key {key!r}")

        super().__setitem__(key, value)

        if self._hooks_suspended:
            self._pending_set.add(key)
            self._pending_delete.discard(key)
            return

        self._emit_set(key, value)

    def __delitem__(self, key: str) -> None:
        super().__delitem__(key)

        if self._hooks_suspended:
            self._pending_delete.add(key)
            self._pending_set.discard(key)
            return

        self._emit_delete(key)

    def pop(self, key: str, default: Any = None) -> pd.DataFrame | Any:
        if key in self:
            value = self[key]
            del self[key]
            return value

        return default

    def clear(self) -> None:
        keys = list(self.keys())
        for key in keys:
            del self[key]

    @overload
    def update(self, other: SupportsKeysAndGetItem[str, pd.DataFrame], **kwargs: pd.DataFrame) -> None: ...
    @overload
    def update(self, other: Iterable[tuple[str, pd.DataFrame]], **kwargs: pd.DataFrame) -> None: ...
    @overload
    def update(self, **kwargs: pd.DataFrame) -> None: ...
    def update(
        self,
        other: SupportsKeysAndGetItem[str, pd.DataFrame] | Mapping[str, pd.DataFrame] | Iterable[tuple[str, pd.DataFrame]] = (),
        **kwargs: pd.DataFrame,
    ) -> None:
        items: dict[str, pd.DataFrame] = dict(other, **kwargs)
        for key, value in items.items():
            self[key] = value

    def setdefault(self, key: str, default: pd.DataFrame | None = None) -> pd.DataFrame:
        if key in self:
            return self[key]

        if default is None:
            default = pd.DataFrame()

        self[key] = default
        return default

    def copy(self) -> "TableStore":
        return TableStore(self)

    def __or__(self, other: Mapping[str, pd.DataFrame]) -> "TableStore":  # type: ignore[override]
        result = TableStore(self)
        result.update(other)
        return result

    def __ror__(self, other: Mapping[str, pd.DataFrame]) -> "TableStore":  # type: ignore[override]
        result = TableStore(other)
        result.update(self)
        return result

    def __ior__(self, other: Mapping[str, pd.DataFrame]) -> "TableStore":  # type: ignore[override]
        self.update(other)
        return self

    @contextmanager
    def batch_update(self) -> Iterator[None]:
        """Temporarily suspend hooks and emit them once after the batch."""
        previous_state = self._hooks_suspended
        self._hooks_suspended = True

        try:
            yield
        finally:
            self._hooks_suspended = previous_state

            if not self._hooks_suspended:
                deleted = list(self._pending_delete)
                changed = list(self._pending_set)

                self._pending_delete.clear()
                self._pending_set.clear()

                for key in deleted:
                    self._emit_delete(key)

                for key in changed:
                    if key in self:
                        self._emit_set(key, self[key])

    def _emit_set(self, key: str, value: pd.DataFrame) -> None:
        for hook in self._on_set_hooks:
            hook(key, value)

    def _emit_delete(self, key: str) -> None:
        for hook in self._on_delete_hooks:
            hook(key)
