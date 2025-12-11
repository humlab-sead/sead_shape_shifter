import os
from contextlib import contextmanager
from typing import Any, Generator

import jaydebeapi
import jpype
import pandas as pd
from sqlalchemy import create_engine

from src.config_model import TableConfig
from src.extract import add_surrogate_id
from src.utility import create_db_uri, dotget

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

        if len(set(data.columns)) != len(set(table_cfg.keys_and_columns)):
            raise ValueError(f"Fixed data entity '{entity_name}' has different number of columns in configuration")

        if table_cfg.check_column_names:
            if set(data.columns) != set(table_cfg.keys_and_columns):
                raise ValueError(f"Fixed data entity '{entity_name}' has mismatched columns between configuration and SQL result")
        else:
            data.columns = table_cfg.keys_and_columns

        if table_cfg.surrogate_id:
            data = add_surrogate_id(data, table_cfg.surrogate_id)

        return data


class PostgresSqlLoader(SqlLoader):
    """Loader for fixed data entities."""

    driver: str = "postgres"

    def __init__(self, data_source: "DataSourceConfig | None" = None) -> None:
        super().__init__(data_source=data_source)
        db_opts: dict[str, Any] = data_source.options if data_source else {}
        clean_opts: dict[str, Any] = {
            "host": dotget(db_opts, "host,hostname,dbhost", "localhost"),
            "port": dotget(db_opts, "port", 5432),
            "user": dotget(db_opts, "user,username,dbuser", "postgres"),
            "dbname": dotget(db_opts, "dbname,database", "postgres"),
        }
        self.db_opts: dict[str, Any] = clean_opts
        self.db_url: str = create_db_uri(**clean_opts, driver="postgresql+psycopg")

    async def read_sql(self, sql: str) -> pd.DataFrame:
        """Read SQL query into a DataFrame using the provided connection."""
        with create_engine(url=self.db_url).begin() as connection:
            data: pd.DataFrame = pd.read_sql_query(sql=sql, con=connection)  # type: ignore[arg-type]
        return data


class UCanAccessSqlLoader(SqlLoader):
    """Loader for fixed data entities. https://ucanaccess.sourceforge.net/site.html"""

    driver: str = "ucanaccess"

    def __init__(self, data_source: "DataSourceConfig | None" = None) -> None:
        super().__init__(data_source=data_source)
        self.db_opts: dict[str, Any] = data_source.options if data_source else {}
        self.filename: str = self.db_opts.get("filename", "")
        self.ucanaccess_dir: str = self.db_opts.get("ucanaccess_dir", "")
        self.jars: list[str] = self._find_jar_files(self.ucanaccess_dir)

    async def read_sql(self, sql: str) -> pd.DataFrame:
        return self.read_sql_sync(sql)

    def read_sql_sync(self, sql: str) -> pd.DataFrame:
        with self.connection() as conn:
            with self._cursor(conn) as cursor:
                cursor.execute(sql)
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                rows = cursor.fetchall()
                return pd.DataFrame(rows, columns=columns)

    @contextmanager
    def _cursor(self, conn: jaydebeapi.Connection) -> Generator[Any, Any, None]:
        """Context manager for database cursor."""
        cursor = conn.cursor()
        try:
            yield cursor
        finally:
            cursor.close()

    @contextmanager
    def connection(self) -> Generator[jaydebeapi.Connection, Any, None]:
        driver_class = "net.ucanaccess.jdbc.UcanaccessDriver"
        url: str = f"jdbc:ucanaccess://{self.filename}"
        conn: jaydebeapi.Connection = jaydebeapi.connect(driver_class, url, [], self.jars)
        try:
            yield conn
        finally:
            conn.close()

    def _find_jar_files(self, folder: str) -> list[str]:
        """Recursively find all .jar files in the ucanaccess_dir."""
        jar_files: list[str] = []
        for root, _, files in os.walk(folder):
            for file in files:
                if file.lower().endswith(".jar"):
                    jar_files.append(os.path.join(root, file))
        return jar_files

    def _ensure_jvm(self) -> None:
        """Start the JVM once with the correct classpath, if not already started."""
        if jpype.isJVMStarted():
            return

        classpath: str = os.pathsep.join(self.jars)

        jpype.startJVM(jpype.getDefaultJVMPath(), "-ea", f"-Djava.class.path={classpath}")

    def get_queries(self) -> dict[str, str]:
        """Return saved queries from the Access database as {name: sql}."""
        self._ensure_jvm()

        # Use Java's DriverManager directly
        driver_manager = jpype.JClass("java.sql.DriverManager")
        conn = driver_manager.getConnection(f"jdbc:ucanaccess:///{self.filename}")

        try:
            dbio = conn.getDbIO()
            queries = dbio.getQueries()
            result: dict[str, str] = {q.getName(): q.toSQLString() for q in queries}
        finally:
            conn.close()

        return result


class SqlLoaderFactory:
    """Factory for creating SQL data loaders."""

    def create_loader(self, driver: str = "postgres", db_opts: dict[str, Any] | None = None) -> SqlLoader:
        if driver in ("postgresql", "postgres"):
            return PostgresSqlLoader(db_opts=db_opts)
        if driver in ("ucanaccess", "access", "mdb"):
            return UCanAccessSqlLoader(db_opts=db_opts)

        raise ValueError(f"Unsupported SQL driver: {driver}")
