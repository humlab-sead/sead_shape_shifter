from typing import Callable

import pandas as pd

TableHook = Callable[[str, pd.DataFrame], None]
DeleteHook = Callable[[str], None]


class TableStore(dict[str, pd.DataFrame]):
    """Store for normalized dataframes. Provides hooks for when tables are added or deleted."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._on_set_hooks: list[TableHook] = []
        self._on_delete_hooks: list[DeleteHook] = []

    def add_on_set_hook(self, hook: TableHook) -> None:
        self._on_set_hooks.append(hook)

    def add_on_delete_hook(self, hook: DeleteHook) -> None:
        self._on_delete_hooks.append(hook)

    def __setitem__(self, key: str, value: pd.DataFrame) -> None:
        super().__setitem__(key, value)

        for hook in self._on_set_hooks:
            hook(key, value)

    def __delitem__(self, key: str) -> None:
        super().__delitem__(key)

        for hook in self._on_delete_hooks:
            hook(key)

    def update(self, *args, **kwargs) -> None:
        items = dict(*args, **kwargs)

        for key, value in items.items():
            self[key] = value

    def __or__(self, other) -> "TableStore":
        result = TableStore(self)
        result.update(other)
        return result

    def __ror__(self, other) -> "TableStore":
        result = TableStore(other)
        result.update(self)
        return result

    def __ior__(self, other) -> "TableStore":
        self.update(other)
        return self
