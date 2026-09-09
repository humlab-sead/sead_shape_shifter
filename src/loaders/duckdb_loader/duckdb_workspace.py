from __future__ import annotations

from typing import Any, Iterable

import duckdb
import pandas as pd
from loguru import logger


class DuckDbWorkspace:
    """Persistent DuckDB workspace over Shape Shifter's TableStore.

    DataFrames are registered as DuckDB views. They are not copied into
    DuckDB storage unless you explicitly materialize them.
    """

    def __init__(self, database: str = ":memory:") -> None:
        self.database: str = database
        self.connection: duckdb.DuckDBPyConnection = duckdb.connect(database=database)

        self._registered: set[str] = set()
        self._registered_object_ids: dict[str, int] = {}
        self.register_queue: dict[str, pd.DataFrame] = {}

    def close(self) -> None:
        if self.connection is not None:
            try:
                self.connection.close()
            except Exception:  # pylint: disable=broad-except
                pass
            self.connection = None  # type: ignore[assignment]

    def __del__(self) -> None:
        self.close()

    def register_entity(self, entity_name: str, df: pd.DataFrame) -> None:
        """Queue an entity DataFrame for registration on the next query."""
        self.register_queue[entity_name] = df

    def _register_entity(self, entity_name: str, df: pd.DataFrame) -> None:
        """Register or re-register an entity DataFrame immediately in DuckDB."""
        object_id: int = id(df)

        if self._registered_object_ids.get(entity_name) == object_id:
            return

        if entity_name in self._registered:
            self.unregister_entity(entity_name)

        logger.trace(f"duckdb: registering entity '{entity_name}' with shape {df.shape}")
        self.connection.register(entity_name, df)

        self._registered.add(entity_name)
        self._registered_object_ids[entity_name] = object_id

    def flush(self) -> None:
        """Drain the registration queue, registering all pending entities."""
        pending, self.register_queue = self.register_queue, {}
        for entity_name, df in pending.items():
            self._register_entity(entity_name, df)

    def unregister_entity(self, entity_name: str) -> None:
        """Unregister an entity if present."""
        self.register_queue.pop(entity_name, None)

        if entity_name not in self._registered:
            return

        logger.trace(f"duckdb: unregistering entity '{entity_name}'")

        try:
            self.connection.unregister(entity_name)
        except duckdb.CatalogException:
            pass

        self._registered.discard(entity_name)
        self._registered_object_ids.pop(entity_name, None)

    def register_many(self, tables: dict[str, pd.DataFrame], only: Iterable[str] | None = None) -> None:
        """Register many tables, optionally restricted to specific names."""
        names: list[str] = list(only) if only is not None else list(tables.keys())

        for name in names:
            if name not in tables:
                raise KeyError(f"DuckDB dependency '{name}' is not available in table_store")

            self.register_entity(name, tables[name])

    def execute(self, sql: str) -> duckdb.DuckDBPyConnection:
        self.flush()
        return self.connection.execute(sql)

    def query_df(self, sql: str) -> pd.DataFrame:
        self.flush()
        return self.connection.execute(sql).df()

    def query_scalar(self, sql: str) -> Any:
        self.flush()
        row: tuple[Any, ...] | None = self.connection.execute(sql).fetchone()

        if row is None:
            return None

        return row[0]

    def explain(self, sql: str) -> pd.DataFrame:
        return self.connection.execute(f"EXPLAIN {sql}").df()

    def list_registered(self) -> list[str]:
        return sorted(self._registered | self.register_queue.keys())

    def materialize_entity(self, entity_name: str, df: pd.DataFrame, *, replace: bool = True) -> None:
        """Copy a DataFrame into DuckDB as a physical table.

        Usually not needed initially. Use this for hot/intermediate entities
        that are queried repeatedly and are expensive to scan from Pandas.
        """
        temp_name: str = f"__df_{entity_name}"
        self.connection.register(temp_name, df)

        try:
            if replace:
                self.connection.execute(f'CREATE OR REPLACE TABLE "{entity_name}" AS SELECT * FROM "{temp_name}"')
            else:
                self.connection.execute(f'CREATE TABLE "{entity_name}" AS SELECT * FROM "{temp_name}"')
        finally:
            self.connection.unregister(temp_name)

        self._registered.add(entity_name)
        self._registered_object_ids[entity_name] = id(df)
