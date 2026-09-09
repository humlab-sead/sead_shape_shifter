from __future__ import annotations

from typing import Any, ClassVar

import pandas as pd
from loguru import logger

from src.loaders.base_loader import DataLoaders
from src.loaders.driver_metadata import DriverSchema, FieldMetadata
from src.loaders.duckdb_loader.duckdb_workspace import DuckDbWorkspace
from src.loaders.sql_loaders import CoreSchema, SqlLoader
from src.model import DataSourceConfig, TableConfig
from src.table_store import TableStore
from src.transforms.utility import add_system_id


@DataLoaders.register(key=["duckdb", "internal"])
class DuckDbLoader(SqlLoader):
    """SQL loader over Shape Shifter's internal table_store.

    This loader does not connect to an external database. Instead, it queries
    already-resolved entities registered in a persistent DuckDB workspace.
    """

    driver: str = "duckdb"

    schema: ClassVar[DriverSchema | None] = DriverSchema(
        driver="duckdb",
        display_name="DuckDB Internal Workspace",
        description="Query already-resolved Shape Shifter entities using DuckDB SQL",
        category="internal",
        fields=[
            FieldMetadata(
                name="database",
                type="string",
                required=False,
                default=":memory:",
                description="DuckDB database path. Defaults to in-memory.",
                placeholder=":memory:",
            ),
        ],
    )

    def __init__(self, data_source: DataSourceConfig | None, *, workspace: DuckDbWorkspace, table_store: TableStore) -> None:
        super().__init__(data_source=data_source)
        self.workspace: DuckDbWorkspace = workspace
        self.table_store: TableStore = table_store

    @classmethod
    def create(cls, data_source: DataSourceConfig | None, **context: Any) -> "DuckDbLoader":
        return cls(
            data_source=data_source,
            workspace=context["workspace"],
            table_store=context["table_store"],
        )

    def create_db_uri(self) -> str:
        return "duckdb://internal"

    async def load(self, entity_name: str, table_cfg: TableConfig) -> pd.DataFrame:
        """Load an internal DuckDB-derived entity."""
        if not table_cfg.sql_query:
            raise ValueError(f"Entity '{entity_name}' is configured for DuckDB but has no query")

        logger.trace(f"{entity_name}[duckdb]: executing internal DuckDB query")
        data: pd.DataFrame = await self.read_sql(table_cfg.sql_query)

        auto_detect_columns: bool = True
        if table_cfg.auto_detect_columns is not None:
            auto_detect_columns = bool(table_cfg.auto_detect_columns)

        data = self.normalize_query_metadata(table_cfg, data, auto_detect_columns)
        self._validate_columns(table_cfg, data, auto_detect_columns)

        if auto_detect_columns:
            effective_columns: list[str] = table_cfg.safe_columns or list(data.columns)
        else:
            effective_columns = table_cfg.safe_columns
            data.columns = effective_columns

        if table_cfg.system_id and table_cfg.system_id not in data.columns:
            data = add_system_id(data, table_cfg.system_id)

        return data

    async def read_sql(self, sql: str) -> pd.DataFrame:
        self.workspace.register_many(self.table_store)
        return self.workspace.query_df(sql)

    async def execute_scalar_sql(self, sql: str) -> Any:
        return self.workspace.query_scalar(sql)

    async def get_tables(self, **kwargs: Any) -> dict[str, CoreSchema.TableMetadata]:
        return {
            name: CoreSchema.TableMetadata(
                name=name,
                schema="internal",
                row_count=len(df),
                comment="Shape Shifter internal entity",
            )
            for name, df in self.table_store.items()
        }

    async def get_table_schema(self, table_name: str, **kwargs: Any) -> CoreSchema.TableSchema:
        if table_name not in self.table_store:
            raise KeyError(f"Unknown internal entity '{table_name}'")

        df: pd.DataFrame = self.table_store[table_name]

        columns = [
            CoreSchema.ColumnMetadata(
                name=str(column),
                data_type=str(dtype),
                nullable=bool(df[column].isna().any()) if column in df else True,
                default=None,
                is_primary_key=False,
                max_length=None,
            )
            for column, dtype in df.dtypes.items()
        ]

        return CoreSchema.TableSchema(
            table_name=table_name,
            schema_name="internal",
            columns=columns,
            primary_keys=[],
            indexes=[],
            row_count=len(df),
            foreign_keys=[],
        )

    def get_test_query(self, table_name: str, limit: int) -> str:
        return f'SELECT * FROM "{table_name}" LIMIT {limit};'
