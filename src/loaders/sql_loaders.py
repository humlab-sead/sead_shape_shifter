import abc
import os
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Generator, Optional

import jaydebeapi
import jpype
import pandas as pd
from loguru import logger
from sqlalchemy import create_engine

from src.extract import add_surrogate_id
from src.utility import create_db_uri as create_pg_uri
from src.utility import dotget

from .base_loader import ConnectTestResult, DataLoader, DataLoaders

if TYPE_CHECKING:
    from src.model import DataSourceConfig, TableConfig


class CoreSchema:
    @dataclass
    class TableMetadata:
        name: str
        schema: Optional[str]
        row_count: Optional[int]
        comment: Optional[str]

        @staticmethod
        def from_dataframe(df: pd.DataFrame) -> dict[str, "CoreSchema.TableMetadata"]:
            """Convert TableMetadata to DataFrame row."""
            return {
                row["table_name"]: CoreSchema.TableMetadata(
                    name=row["table_name"], schema=row.get("schema"), row_count=None, comment=row.get("comment")
                )
                for _, row in df.iterrows()
            }

    @dataclass
    class ColumnMetadata:
        name: str
        data_type: str
        nullable: bool
        default: Optional[str]
        is_primary_key: bool
        max_length: Optional[int]

    @dataclass
    class ForeignKeyMetadata:
        column: str
        referenced_schema: Optional[str]
        referenced_table: str
        referenced_column: str
        constraint_name: Optional[str]

    @dataclass
    class TableSchema:
        table_name: str
        columns: list["CoreSchema.ColumnMetadata"]
        primary_keys: list[str]
        indexes: list[str]
        row_count: Optional[int]
        foreign_keys: list["CoreSchema.ForeignKeyMetadata"]


class SqlLoader(DataLoader):
    """Loader for fixed data entities."""

    def __init__(self, data_source: "DataSourceConfig") -> None:
        super().__init__(data_source=data_source)

    @property
    def db_uri(self) -> str:
        return self.create_db_uri()

    @abc.abstractmethod
    def create_db_uri(self) -> str:
        pass

    def driver_name(self) -> str:
        return self.data_source.driver if self.data_source else "unknown"

    def options(self) -> dict[str, Any]:
        return self.data_source.options if self.data_source else {}

    async def load(self, entity_name: str, table_cfg: "TableConfig") -> pd.DataFrame:

        if table_cfg.type != "sql":
            raise ValueError(f"Entity '{entity_name}' is not configured as fixed SQL data")

        data: pd.DataFrame = await self.read_sql(sql=table_cfg.query)  # type: ignore[arg-type]

        if not table_cfg.keys_and_columns and table_cfg.auto_detect_columns:
            table_cfg.columns = list(data.columns)

        if table_cfg.check_column_names:
            if set(data.columns) != set(table_cfg.keys_and_columns):
                raise ValueError(f"Data for entity '{entity_name}' has different columns compared to configuration")
        else:
            data.columns = table_cfg.keys_and_columns

        if table_cfg.surrogate_id:
            data = add_surrogate_id(data, table_cfg.surrogate_id)

        return data

    async def read_sql(self, sql: str) -> pd.DataFrame:
        """Read SQL query into a DataFrame using the provided connection."""
        with create_engine(url=self.db_uri).begin() as connection:
            data: pd.DataFrame = pd.read_sql_query(sql=sql, con=connection)  # type: ignore[arg-type]
        return data

    @abc.abstractmethod
    async def get_tables(self, **kwargs) -> dict[str, "CoreSchema.TableMetadata"]:
        pass

    @abc.abstractmethod
    async def get_table_schema(self, table_name: str, **kwargs) -> CoreSchema.TableSchema:
        pass

    def get_test_query(self, table_name: str, limit: int) -> str:
        """Get a test query for the data source, if applicable."""
        return f"select * from {table_name} limit {limit} ;"

    @abc.abstractmethod
    async def execute_scalar_sql(self, sql: str) -> Any:
        """Read SQL query that returns a single scalar value."""

    async def get_table_row_count(self, table_name: str, schema: Optional[str] = None) -> Optional[int]:
        """Get approximate row count for a table."""
        try:
            qualified_table: str = f'"{schema}"."{table_name}"' if schema else f'"{table_name}"'
            query: str = f"SELECT COUNT(*) as count FROM {qualified_table}"
            return await self.execute_scalar_sql(query)
        except Exception as e:  # pylint: disable=broad-except
            logger.warning(f"Could not get row count for {table_name}: {e}")
        return None

    async def test_connection(self) -> ConnectTestResult:
        """Test database connection by attempting to load a simple query.

        Args:
            config: Database data source configuration

        Returns:
            Test result
        """
        from src.model import TableConfig  # Avoid circular import;  pylint: disable=import-outside-toplevel

        start_time: float = time.time()
        result: ConnectTestResult = ConnectTestResult.create_empty()
        try:
            tables: dict[str, CoreSchema.TableMetadata] = await self.get_tables()

            if not tables:
                elapsed_ms = int((time.time() - start_time) * 1000)
                return ConnectTestResult(
                    success=True,
                    message="Connected successfully (no tables found)",
                    connection_time_ms=elapsed_ms,
                    metadata={"table_count": 0},
                )

            first_table: str = next(iter(tables.keys()))
            test_query: str = self.get_test_query(table_name=first_table, limit=10)

            elapsed_ms = int((time.time() - start_time) * 1000)
            result.success = True
            result.connection_time_ms = elapsed_ms
            result.message = f"Connected successfully (found {len(tables)} tables"

            # Create mock table config with simple test query
            test_table_cfg: TableConfig = TableConfig(
                cfg={
                    "test": {
                        "surrogate_id": "test_id",
                        "type": "sql",
                        "keys": [],
                        "columns": [],
                        "source": None,
                        "query": test_query,
                        "data_source": self.data_source.name if self.data_source else None,
                        "auto_detect_columns": True,
                    }
                },
                entity_name="test",
            )

            df: pd.DataFrame = await self.load(entity_name="test", table_cfg=test_table_cfg)

            elapsed_ms = int((time.time() - start_time) * 1000)
            result.metadata.update({"table_count": len(tables)})
            result.message += f", returned {len(df)} rows)"

        except Exception as e:  # pylint: disable=broad-except
            elapsed_ms = int((time.time() - start_time) * 1000)
            result.success = False
            result.message = f"Connection failed: {str(e)}"
            result.connection_time_ms = elapsed_ms
            result.metadata = {}

        return result


@DataLoaders.register(key="sqlite")
class SqliteLoader(SqlLoader):
    """Loader for SQLite database queries."""

    driver: str = "sqlite"

    def create_db_uri(self) -> str:
        if not self.data_source:
            raise ValueError("Data source configuration is required for SqliteLoader")

        filename: str = (
            dotget(self.data_source.data_source_cfg or {}, "database,filename,dbname", ":memory:")
            or dotget(self.data_source.options or {}, "database,filename,dbname", ":memory:")
            or ":memory:"
        )

        db_uri: str = f"sqlite:///{filename}"
        return db_uri

    async def get_table_schema(self, table_name: str, **kwargs) -> CoreSchema.TableSchema:
        """Get detailed schema for MS Access table."""
        # Get columns using information schema
        columns_query = f"""
            SELECT 
                COLUMN_NAME,
                DATA_TYPE,
                IS_NULLABLE,
                COLUMN_DEFAULT,
                CHARACTER_MAXIMUM_LENGTH
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = '{table_name}'
            ORDER BY ORDINAL_POSITION
        """

        columns_data = await self.read_sql(columns_query)

        try:
            pk_query: str = f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE WHERE TABLE_NAME = '{table_name}'"
            pk_data: pd.DataFrame = await self.read_sql(pk_query)
            primary_keys: list[str] = pk_data["COLUMN_NAME"].tolist() if not pk_data.empty else []
        except Exception:  # pylint: disable=broad-except
            logger.warning(f"Could not determine primary keys for {table_name}")
            primary_keys = []

        # Build columns list
        columns: list[CoreSchema.ColumnMetadata] = []
        for _, row in columns_data.iterrows():
            columns.append(
                CoreSchema.ColumnMetadata(
                    name=row["COLUMN_NAME"],
                    data_type=row["DATA_TYPE"],
                    nullable=row["IS_NULLABLE"] == "YES",
                    default=row.get("COLUMN_DEFAULT"),
                    is_primary_key=row["COLUMN_NAME"] in primary_keys,
                    max_length=row.get("CHARACTER_MAXIMUM_LENGTH"),
                )
            )

        row_count: int | None = await self.get_table_row_count(table_name, schema=None)

        return CoreSchema.TableSchema(
            table_name=table_name,
            columns=columns,
            primary_keys=primary_keys,
            row_count=row_count,
            foreign_keys=[],
            indexes=[],
        )

    async def get_tables(self, **kwargs) -> dict[str, CoreSchema.TableMetadata]:
        """Get tables from SQLite database."""
        query = """
            SELECT name as table_name
            FROM sqlite_master
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """

        data: pd.DataFrame = await self.read_sql(query)

        tables: dict[str, CoreSchema.TableMetadata] = {
            row["table_name"]: CoreSchema.TableMetadata(name=row["table_name"], schema=None, comment=None, row_count=0)
            for _, row in data.iterrows()
        }

        return tables

    async def execute_scalar_sql(self, sql: str) -> Any:
        """Read SQL query that returns a single scalar value."""
        with create_engine(url=self.db_uri).begin() as connection:
            result = connection.execute(sql)  # type: ignore[attr-defined]
            scalar_value = result.scalar()
        return scalar_value


@DataLoaders.register(key=["postgres", "postgresql"])
class PostgresSqlLoader(SqlLoader):
    """Loader for fixed data entities."""

    driver: str = "postgres"

    @property
    def db_opts(self) -> dict[str, Any]:
        """Return cleaned database options."""
        opts: dict[str, Any] = self.data_source.options if self.data_source else {}
        clean_opts: dict[str, Any] = {
            "host": dotget(opts, "host,hostname,dbhost", "localhost"),
            "port": dotget(opts, "port", 5432),
            "user": dotget(opts, "user,username,dbuser", "postgres"),
            "dbname": dotget(opts, "dbname,database", "postgres"),
        }
        return clean_opts

    def create_db_uri(self) -> str:
        if not self.data_source:
            raise ValueError("Data source configuration is required for PostgresSqlLoader")
        return create_pg_uri(**self.db_opts, driver="postgresql+psycopg")

    async def read_sql(self, sql: str) -> pd.DataFrame:
        """Read SQL query into a DataFrame using the provided connection."""
        with create_engine(url=self.db_uri).begin() as connection:
            data: pd.DataFrame = pd.read_sql_query(sql=sql, con=connection)  # type: ignore[arg-type]
        return data

    async def execute_scalar_sql(self, sql: str) -> Any:
        """Read SQL query that returns a single scalar value."""
        with create_engine(url=self.db_uri).begin() as connection:
            result = connection.execute(sql)  # type: ignore[attr-defined]
            scalar_value = result.scalar()
        return scalar_value

    async def get_tables(self, **kwargs) -> dict[str, "CoreSchema.TableMetadata"]:
        """Get tables from PostgreSQL database."""
        schema: str = kwargs.get("schema", "public")

        query: str = f"""
            select 
                table_name,
                table_schema as schema,
                obj_description((quote_ident(table_schema) || '.' || quote_ident(table_name))::regclass) as comment
            from information_schema.tables
            where table_schema = '{schema}'
              and table_type = 'BASE TABLE'
            order by table_name
        """

        data: pd.DataFrame = await self.read_sql(query)

        return CoreSchema.TableMetadata.from_dataframe(data)

    async def get_table_schema(self, table_name: str, **kwargs) -> CoreSchema.TableSchema:
        """Get detailed schema for PostgreSQL table."""
        schema: str = kwargs.get("schema", "public")

        # Get columns
        columns_query: str = f"""
            select column_name, data_type, is_nullable, column_default, character_maximum_length
            from information_schema.columns
            where table_schema = '{schema}'
              and table_name = '{table_name}'
            order by ordinal_position
        """

        columns_data: pd.DataFrame = await self.read_sql(columns_query)

        # Get primary keys
        pk_query: str = f"""
            select a.attname as column_name
            from pg_index i
            join pg_attribute a on a.attrelid = i.indrelid and a.attnum = any(i.indkey)
            where i.indrelid = (
                select oid from pg_class
                where relname = '{table_name}'
                and relnamespace = (select oid from pg_namespace where nspname = '{schema}')
            )
            and i.indisprimary
        """

        pk_data: pd.DataFrame = await self.read_sql(pk_query)
        primary_keys = pk_data["column_name"].tolist() if not pk_data.empty else []

        # Build columns list
        columns = []
        for _, row in columns_data.iterrows():
            max_length = row.get("character_maximum_length")
            # Convert pandas NaN to None for Pydantic
            if pd.isna(max_length):
                max_length = None

            columns.append(
                CoreSchema.ColumnMetadata(
                    name=row["column_name"],
                    data_type=row["data_type"],
                    nullable=row["is_nullable"] == "YES",
                    default=row.get("column_default"),
                    is_primary_key=row["column_name"] in primary_keys,
                    max_length=max_length,
                )
            )

        # Get foreign keys
        fk_query = f"""
            select
                kcu.column_name,
                ccu.table_name AS referenced_table,
                ccu.column_name AS referenced_column,
                ccu.table_schema AS referenced_schema,
                rc.constraint_name AS name
            from information_schema.table_constraints AS tc
            join information_schema.key_column_usage AS kcu
              on tc.constraint_name = kcu.constraint_name
             and tc.table_schema = kcu.table_schema
            join information_schema.constraint_column_usage AS ccu
              on ccu.constraint_name = tc.constraint_name
             and ccu.table_schema = tc.table_schema
            join information_schema.referential_constraints AS rc
              on rc.constraint_name = tc.constraint_name
            where tc.constraint_type = 'FOREIGN KEY'
              and tc.table_schema = '{schema}'
              and tc.table_name = '{table_name}'
        """

        fk_data: pd.DataFrame = await self.read_sql(fk_query)

        foreign_keys = []
        if not fk_data.empty:
            for _, row in fk_data.iterrows():
                foreign_keys.append(
                    CoreSchema.ForeignKeyMetadata(
                        constraint_name=row["name"],
                        column=row["column_name"],
                        referenced_table=row["referenced_table"],
                        referenced_column=row["referenced_column"],
                        referenced_schema=row.get("referenced_schema"),
                    )
                )

        # Get row count
        row_count = await self.get_table_row_count(table_name, schema)

        return CoreSchema.TableSchema(
            table_name=table_name,
            columns=columns,
            primary_keys=primary_keys,
            foreign_keys=foreign_keys,
            row_count=row_count,
            indexes=[],
        )


@DataLoaders.register(key=["ucanaccess", "access"])
class UCanAccessSqlLoader(SqlLoader):
    """Loader for fixed data entities. https://ucanaccess.sourceforge.net/site.html"""

    driver: str = "ucanaccess"

    def __init__(self, data_source: "DataSourceConfig") -> None:
        super().__init__(data_source=data_source)
        opts: dict[str, Any] = data_source.options if data_source else {}
        self.filename: str = opts.get("filename", "")
        self.ucanaccess_dir: str = opts.get("ucanaccess_dir", "")
        self.jars: list[str] = self._find_jar_files(self.ucanaccess_dir)

    def create_db_uri(self) -> str:
        if not self.data_source:
            raise ValueError("Data source configuration is required for UCanAccessSqlLoader")
        return f"jdbc:ucanaccess://{self.filename}"

    async def read_sql(self, sql: str) -> pd.DataFrame:
        return self.read_sql_sync(sql)

    def read_sql_sync(self, sql: str) -> pd.DataFrame:
        with self.connection() as conn:
            with self._cursor(conn) as cursor:
                cursor.execute(sql)
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                rows = cursor.fetchall()
                return pd.DataFrame(rows, columns=columns)

    async def execute_scalar_sql(self, sql: str) -> Any:
        with self.connection() as conn:
            with self._cursor(conn) as cursor:
                cursor.execute(sql)
                result = cursor.fetchone()
                if result:
                    return result[0]
                return None

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

    async def get_tables(self, **kwargs) -> dict[str, CoreSchema.TableMetadata]:
        """Get tables from MS Access database."""
        queries: list[str] = [
            "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'TABLE' ORDER BY TABLE_NAME ",
            "SELECT Name as TABLE_NAME FROM MSysObjects WHERE Type = 1 AND Flags = 0 ORDER BY Name",
        ]

        data: pd.DataFrame | None = None
        for query in queries:
            try:
                data = await self.read_sql(query)
                break
            except Exception as e:  # pylint: disable=broad-except
                print(f"Error executing query: {e}")
                pass

        if data is None:
            return {}

        tables: dict[str, CoreSchema.TableMetadata] = {
            row["TABLE_NAME"]: CoreSchema.TableMetadata(name=row["TABLE_NAME"], schema=None, comment=None, row_count=0)
            for _, row in data.iterrows()
        }

        return tables

    async def get_table_schema(self, table_name: str, **kwargs) -> CoreSchema.TableSchema:
        """Get detailed schema for MS Access table."""
        # Get columns using information schema
        columns_query = f"""
            SELECT 
                COLUMN_NAME,
                DATA_TYPE,
                IS_NULLABLE,
                COLUMN_DEFAULT,
                CHARACTER_MAXIMUM_LENGTH
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = '{table_name}'
            ORDER BY ORDINAL_POSITION
        """

        columns_data = await self.read_sql(columns_query)

        # Get primary keys
        # UCanAccess may not support this reliably, so we try
        try:
            pk_query = f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE WHERE TABLE_NAME = '{table_name}'"
            pk_data = await self.read_sql(pk_query)
            primary_keys = pk_data["COLUMN_NAME"].tolist() if not pk_data.empty else []
        except Exception:  # pylint: disable=broad-except
            logger.warning(f"Could not determine primary keys for {table_name}")
            primary_keys = []

        # Build columns list
        columns = []
        for _, row in columns_data.iterrows():
            columns.append(
                CoreSchema.ColumnMetadata(
                    name=row["COLUMN_NAME"],
                    data_type=row["DATA_TYPE"],
                    nullable=row["IS_NULLABLE"] == "YES",
                    default=row.get("COLUMN_DEFAULT"),
                    is_primary_key=row["COLUMN_NAME"] in primary_keys,
                    max_length=row.get("CHARACTER_MAXIMUM_LENGTH"),
                )
            )

        # Get row count
        row_count = await self.get_table_row_count(table_name, None)

        return CoreSchema.TableSchema(
            table_name=table_name,
            columns=columns,
            primary_keys=primary_keys,
            row_count=row_count,
            foreign_keys=[],
            indexes=[],
        )

    def get_test_query(self, table_name: str, limit: int) -> str:
        """Get a test query for the data source, if applicable."""
        return f"SELECT TOP {limit} * FROM {table_name};"
