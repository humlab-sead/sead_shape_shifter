from pathlib import Path
from typing import Any, Protocol

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import PatternFill
from openpyxl.utils.dataframe import dataframe_to_rows
from sqlalchemy import create_engine

from src.configuration.resolve import ConfigValue
from src.model import ShapeShiftConfig, TableConfig
from src.utility import Registry, create_db_uri


class DispatchRegistry(Registry):
    """Registry for data store implementations."""

    items: dict = {}


Dispatchers: DispatchRegistry = DispatchRegistry()  # pylint: disable=invalid-name


class IDispatcher(Protocol):

    def dispatch(self, target: str, data: dict[str, pd.DataFrame]) -> None: ...


class Dispatcher(IDispatcher):
    """Base class for data dispatchers."""

    def __init__(self, cfg: ShapeShiftConfig) -> None:
        self.cfg: ShapeShiftConfig = cfg


@Dispatchers.register(key="csv")
class CSVDispatcher(Dispatcher):
    """Dispatcher for CSV data."""

    def dispatch(self, target: str, data: dict[str, pd.DataFrame]) -> None:
        output_dir = Path(target)
        output_dir.mkdir(parents=True, exist_ok=True)
        for entity_name, table in data.items():
            table.to_csv(output_dir / f"{entity_name}.csv", index=False)


@Dispatchers.register(key="xlsx")
class ExcelDispatcher(Dispatcher):
    """Dispatcher for Excel data."""

    def dispatch(self, target: str, data: dict[str, pd.DataFrame]) -> None:
        with pd.ExcelWriter(target, engine="openpyxl") as writer:
            for entity_name, table in data.items():
                table.to_excel(writer, sheet_name=entity_name, index=False)


@Dispatchers.register(key="openpyxl")
class OpenpyxlExcelDispatcher(Dispatcher):
    """Dispatcher for Excel data using openpyxl."""

    def dispatch(self, target: str, data: dict[str, pd.DataFrame]) -> None:
        wb = Workbook()

        wb.remove(wb.active)  # type: ignore ; openpyxl creates a default sheet

        for entity_name, table in data.items():
            sheet_name: str = self._safe_sheet_name(entity_name, existing=wb.sheetnames)

            ws = wb.create_sheet(title=sheet_name)

            # Write headers + rows
            for r in dataframe_to_rows(table, index=False, header=True):
                ws.append(r)

            # change background color of header row
            self.style_sheet_columns(entity_name, table, ws)
            self.auto_size_columns(ws)

        wb.save(target)

    def style_sheet_columns(self, entity_name, table, ws):
        for cell in ws[1]:
            cell.fill = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")

        columns: list[str] = table.columns.to_list()
        entity_cfg: TableConfig = self.cfg.get_table(entity_name)

        for column in columns:
            # FIXME: Read colors from configuration
            if column in entity_cfg.get_key_columns():
                self.set_column_background_color(column, columns, ws, "#c1eac1")
            elif column == "system_id":
                self.set_column_background_color(column, columns, ws, "#A3A4A9")
            elif column == entity_cfg.surrogate_id:
                self.set_column_background_color(column, columns, ws, "#7a83e6")
            elif column.endswith("_id"):
                self.set_column_background_color(column, columns, ws, "#d4e160")

    def auto_size_columns(self, ws):
        for col in ws.columns:
            max_length = 0
            column = col[0].column_letter  # Get the column name
            for cell in col:
                try:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                except Exception:
                    pass
            adjusted_width = max_length + 2
            ws.column_dimensions[column].width = adjusted_width

    def set_column_background_color(self, column_name: str, columns: list[str], ws, color: str = "D3D3D3") -> None:
        idx: int | None = self.find_column_index(column_name, columns)
        if idx is None:
            return
        for cell in ws[2 : ws.max_row + 1]:
            cell[idx - 1].fill = PatternFill(start_color=color, end_color=color, fill_type="solid")

    def find_column_index(self, column_name: str, columns: list[str]) -> int | None:
        for idx, col in enumerate(columns):
            if col == column_name:
                return idx + 1  # openpyxl uses 1-based indexing
        return None

    @staticmethod
    def _safe_sheet_name(name: str, existing: list[str]) -> str:
        """Make a string safe for Excel sheet titles and unique within the workbook."""
        clean_name: str = OpenpyxlExcelDispatcher._clean_sheet_name(name)
        if clean_name in existing:
            raise ValueError(f"Duplicate sheet name: {name if name == clean_name else f'{name} -> {clean_name}'}")
        return clean_name

    @staticmethod
    def _clean_sheet_name(name: str) -> str:
        # Excel sheet title rules: max 31 chars, cannot contain : \ / ? * [ ]
        return name.translate(str.maketrans({c: "_" for c in r":\/?*[]"})).strip()[:31] or "Sheet"


@Dispatchers.register(key="db")
class DatabaseDispatcher(Dispatcher):
    """Dispatcher for Database data."""

    def dispatch(self, target: str, data: dict[str, pd.DataFrame]) -> None:
        # FIXME: This won't work since configuration no longer resides in ConfigStore
        db_opts: dict[str, Any] = ConfigValue[dict[str, Any]]("options.database").resolve() or {}
        db_url: str = create_db_uri(**db_opts)
        # use pandas to_sql to write dataframes to the database

        engine = create_engine(url=db_url)
        with engine.begin() as connection:
            for entity_name, table in data.items():
                table.to_sql(entity_name, con=connection, if_exists="replace", index=False)
