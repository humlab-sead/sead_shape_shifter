from __future__ import annotations

import re
from typing import Any, Iterable

import duckdb
import pandas as pd
from loguru import logger

from src.sql_policy import ensure_read_only_sql


class DuckDbWorkspace:
    """Transient DuckDB workspace over Shape Shifter's TableStore.

    DataFrames are registered as DuckDB views. They are not copied into
    DuckDB storage unless you explicitly materialize them. The workspace does
    not load or update persisted DuckDB database state.
    """

    _EXTERNAL_ACCESS_PATTERNS: tuple[re.Pattern[str], ...] = (
        re.compile(
            r"\bread_(?:csv(?:_auto)?|parquet(?:_scan)?|json(?:_auto)?|ndjson(?:_auto)?|text|blob|tsv(?:_auto)?|xlsx|excel)\s*\(",
            re.IGNORECASE,
        ),
        re.compile(r"\b(?:https?|s3|gs|azure|ftp)://", re.IGNORECASE),
    )

    def __init__(self, database: str = ":memory:") -> None:
        self.connection: duckdb.DuckDBPyConnection | None = None

        if database != ":memory:":
            raise ValueError("DuckDB workspace is transient and must use the in-memory database")

        self.database: str = database
        self.connection = duckdb.connect(database=database)
        self._configure_runtime_policy()

        self._registered: set[str] = set()
        self._registered_object_ids: dict[str, int] = {}
        self.register_queue: dict[str, pd.DataFrame] = {}

    def _configure_runtime_policy(self) -> None:
        """Disable DuckDB features that would let untrusted SQL reach files or extensions."""
        for statement in (
            "SET enable_external_access=false",
            "SET allow_unsigned_extensions=false",
            "SET autoload_known_extensions=false",
            "SET allow_community_extensions=false",
        ):
            self.connection.execute(statement)

    def _ensure_transient_sql(self, sql: str) -> None:
        """Reject DuckDB-specific file and network access that is not needed for the internal workspace."""
        lower_sql = sql.lower()
        for pattern in self._EXTERNAL_ACCESS_PATTERNS:
            if pattern.search(lower_sql):
                raise ValueError("DuckDB external file, network, and extension access is not allowed for the internal workspace")

    def _validate_sql(self, sql: str) -> None:
        ensure_read_only_sql(sql)
        self._ensure_transient_sql(sql)

    def close(self) -> None:
        connection = getattr(self, "connection", None)
        if connection is not None:
            try:
                connection.close()
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
        self._validate_sql(sql)
        self.flush()
        return self.connection.execute(sql)

    def query_df(self, sql: str) -> pd.DataFrame:
        self._validate_sql(sql)
        self.flush()
        return self.connection.execute(sql).df()

    def query_scalar(self, sql: str) -> Any:
        self._validate_sql(sql)
        self.flush()
        row: tuple[Any, ...] | None = self.connection.execute(sql).fetchone()

        if row is None:
            return None

        return row[0]

    def explain(self, sql: str) -> pd.DataFrame:
        self._validate_sql(sql)
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
