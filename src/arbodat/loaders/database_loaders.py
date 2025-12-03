from contextlib import contextmanager
import os
from typing import Any, Generator
from os.path import join as jj

import jaydebeapi
import pandas as pd
from sqlalchemy import create_engine

from src.arbodat.config_model import TableConfig
from src.arbodat.utility import add_surrogate_id
from src.utility import create_db_uri

from .interface import DataLoader


class SqlLoader(DataLoader):
    """Loader for fixed data entities."""

    async def read_sql(self, sql: str) -> pd.DataFrame:
        raise NotImplementedError("Subclasses must implement read_sql method")

    async def load(self, entity_name: str, table_cfg: TableConfig) -> pd.DataFrame:

        if not table_cfg.is_sql_data:
            raise ValueError(f"Entity '{entity_name}' is not configured as fixed SQL data")

        data: pd.DataFrame = await self.read_sql(sql=table_cfg.fixed_sql)  # type: ignore[arg-type]
        # for now, columns must match those in the SQL result
        if list(data.columns) != (table_cfg.columns or []):
            raise ValueError(f"Fixed data entity '{entity_name}' has mismatched columns between configuration and SQL result")
        if table_cfg.surrogate_id:
            data = add_surrogate_id(data, table_cfg.surrogate_id)

        return data


class PostgresSqlLoader(SqlLoader):
    """Loader for fixed data entities."""

    driver: str = "postgres"

    def __init__(self, db_opts: dict[str, Any] | None = None) -> None:
        self.db_opts: dict[str, Any] = db_opts or {}
        self.db_url: str = create_db_uri(**self.db_opts, driver="postgresql+psycopg")

    async def read_sql(self, sql: str) -> pd.DataFrame:
        """Read SQL query into a DataFrame using the provided connection."""
        with create_engine(url=self.db_url).begin() as connection:
            data: pd.DataFrame = await pd.read_sql_query(sql=sql, con=connection)  # type: ignore[arg-type]
        return data


class UCanAccessSqlLoader(SqlLoader):
    """Loader for fixed data entities."""

    driver: str = "ucanaccess"

    def __init__(self, db_opts: dict[str, Any] | None = None) -> None:
        self.db_opts: dict[str, Any] = db_opts or {}
        self.filename: str = self.db_opts.get("filename", "")
        self.ucanaccess_dir: str = self.db_opts.get("ucanaccess_dir", "")
        self.jars: list[str] = [
            jj(self.ucanaccess_dir, f) for f in os.listdir(self.ucanaccess_dir) if os.path.isfile(jj(self.ucanaccess_dir, f)) and f.lower().endswith(".jar")
        ]

    async def read_sql(self, sql: str) -> pd.DataFrame:
        with self.access_connection() as conn:
            return pd.read_sql(sql, conn)  # type: ignore[arg-type]

    @contextmanager
    def access_connection(self) -> Generator[jaydebeapi.Connection, Any, None]:
        driver_class = "net.ucanaccess.jdbc.UcanaccessDriver"
        url: str = f"jdbc:ucanaccess://{self.filename}"
        conn: jaydebeapi.Connection = jaydebeapi.connect(driver_class, url, [], self.jars)
        try:
            yield conn
        finally:
            conn.close()


class SqlLoaderFactory:
    """Factory for creating SQL data loaders."""

    def create_loader(self, driver: str = "postgres", db_opts: dict[str, Any] | None = None) -> SqlLoader:
        if driver in ("postgresql", "postgres"):
            return PostgresSqlLoader(db_opts=db_opts)
        if driver == "ucanaccess":
            return UCanAccessSqlLoader(db_opts=db_opts)

        raise ValueError(f"Unsupported SQL driver: {driver}")
