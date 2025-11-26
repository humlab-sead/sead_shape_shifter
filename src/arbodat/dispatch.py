from pathlib import Path
from typing import Any, Protocol

import pandas as pd

from src.configuration.resolve import ConfigValue
from src.utility import Registry, create_db_uri


class DispatchRegistry(Registry):
    """Registry for data store implementations."""

    items: dict = {}


Dispatchers: DispatchRegistry = DispatchRegistry()

# Crate a protocol for dispatchers


class Dispatcher(Protocol):
    def dispatch(self, target: str, data: dict[str, pd.DataFrame]) -> None: ...


@Dispatchers.register(key="csv")
class CSVDispatcher(Dispatcher):
    """Dispatcher for CSV data stores."""

    def dispatch(self, target: str, data: dict[str, pd.DataFrame]) -> None:
        output_dir = Path(target)
        output_dir.mkdir(parents=True, exist_ok=True)
        for entity_name, table in data.items():
            table.to_csv(output_dir / f"{entity_name}.csv", index=False)


@Dispatchers.register(key="xlsx")
class ExcelDispatcher(Dispatcher):
    """Dispatcher for Excel data stores."""

    def dispatch(self, target: str, data: dict[str, pd.DataFrame]) -> None:
        with pd.ExcelWriter(target, engine="openpyxl") as writer:
            for entity_name, table in data.items():
                table.to_excel(writer, sheet_name=entity_name, index=False)


@Dispatchers.register(key="db")
class DatabaseDispatcher(Dispatcher):
    """Dispatcher for Database data stores."""

    def dispatch(self, target: str, data: dict[str, pd.DataFrame]) -> None:
        db_opts: dict[str, Any] = ConfigValue[dict[str, Any]]("options.database").resolve() or {}
        db_url: str = create_db_uri(**db_opts)
        # use pandas to_sql to write dataframes to the database
        from sqlalchemy import create_engine

        engine = create_engine(url=db_url)
        with engine.begin() as connection:
            for entity_name, table in data.items():
                table.to_sql(entity_name, con=connection, if_exists="replace", index=False)
