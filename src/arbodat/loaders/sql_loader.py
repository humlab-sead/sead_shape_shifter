from typing import Any

import pandas as pd
from sqlalchemy import create_engine

from src.arbodat.config_model import TableConfig
from src.arbodat.utility import add_surrogate_id
from .interface import DataLoader
from src.configuration.resolve import ConfigValue
from src.utility import create_db_uri


def read_sql(sql: str) -> pd.DataFrame:
    """Read SQL query into a DataFrame using the provided connection."""
    db_opts: dict[str, Any] = ConfigValue[dict[str, Any]]("options.database").resolve() or {}
    db_url: str = create_db_uri(**db_opts, driver="postgresql+psycopg")

    with create_engine(url=db_url).begin() as connection:
        data: pd.DataFrame = pd.read_sql_query(sql=sql, con=connection)  # type: ignore[arg-type]

    return data


class SqlLoader(DataLoader):
    """Loader for fixed data entities."""

    async def load(self, entity_name: str, table_cfg: TableConfig) -> pd.DataFrame:

        if not table_cfg.is_fixed_sql:
            raise ValueError(f"Entity '{entity_name}' is not configured as fixed SQL data")

        data: pd.DataFrame = read_sql(sql=table_cfg.fixed_sql)  # type: ignore[arg-type]
        # for now, columns must match those in the SQL result
        if list(data.columns) != (table_cfg.columns or []):
            raise ValueError(f"Fixed data entity '{entity_name}' has mismatched columns between configuration and SQL result")
        if table_cfg.surrogate_id:
            data = add_surrogate_id(data, table_cfg.surrogate_id)

        return data
