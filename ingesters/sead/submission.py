from __future__ import annotations

import contextlib
import functools
import os

import pandas as pd
from loguru import logger

from .metadata import SchemaService, SeadSchema, Table
from .policies import UpdatePolicies
from .utility import flatten_sets, log_decorator, to_lookups_sql


def load_excel_sheet(reader: pd.ExcelFile, sheet_name: str) -> pd.DataFrame:
    with contextlib.suppress(Exception):
        return reader.parse(sheet_name)
    raise ValueError(f"Could not read sheet {sheet_name} from Excel file")


class Submission:
    """Logic dealing with the submission data"""

    def __init__(self, data_tables: dict[str, pd.DataFrame], schema: SeadSchema) -> None:
        self.data_tables: dict[str, pd.DataFrame] = data_tables
        self.schema: SeadSchema = schema
        self._table_lookup: dict[str, pd.DataFrame] = self._generate_table_lookup(data_tables, schema)

    def _generate_table_lookup(self, data_tables: dict[str, pd.DataFrame], schema: SeadSchema) -> dict[str, pd.DataFrame]:
        """Generates a lookup dictionary mapping table names and excel sheet names to data tables."""
        lookup: dict[str, pd.DataFrame] = data_tables
        for table_name, data in data_tables.items():
            table: Table = schema.get_table(table_name)
            if table.table_name not in data_tables:
                lookup[table.table_name] = data
            if table.excel_sheet not in data_tables:
                lookup[table.excel_sheet] = data
        return lookup

    def __getitem__(self, key: str) -> pd.DataFrame:
        """Get the data table by table name or excel sheet name."""
        if key in self._table_lookup:
            return self._table_lookup[key]
        raise KeyError(f"Table {key} not found in submission data tables or schema")

    def __contains__(self, key: str) -> bool:
        return key in self._table_lookup

    def has_system_id(self, table_name: str) -> bool:
        return table_name in self._table_lookup and "system_id" in self[table_name].columns

    def has_pk_id(self, table_name: str) -> bool:
        return self.schema.get_table(table_name).pk_name in self[table_name].columns

    def is_lookup(self, table_name: str) -> bool:
        return self.schema.get_table(table_name).is_lookup

    def has_new_rows(self, table_name: str) -> bool:
        pk_name: str = self.schema.get_table(table_name).pk_name
        if not self.has_pk_id(table_name):
            raise ValueError(f"Table {table_name}: PK column {pk_name} not found in submission")
        return any(self[table_name][pk_name].isnull())

    @property
    def data_table_names(self) -> list[str]:
        """Returns a list of all table names included in the submission"""
        return list(self.data_tables.keys())

    def get_referenced_keyset(self, schema: SeadSchema, table_name: str) -> set[int]:
        """Returns all unique system ids in `table_name` that are referenced by any foreign key in any other table.
        NOTE: This function assumes PK and FK names are the same."""
        pk_name: str = schema.get_table(table_name).pk_name
        if pk_name is None:
            return set()

        # Find all tables that reference the given table, and have the PK column i the referencing table's data
        fk_tables: list[str] = [
            fk_table
            for fk_table in schema.get_tablenames_referencing(table_name)
            if fk_table in self.data_tables and pk_name in self.data_tables[fk_table].columns
        ]
        # logger.debug(f"   {table_name} is referenced by: {','.join(fk_tables)}")
        referenced_pk_ids: list[set] = [
            set(series.loc[~series.isnull()].tolist()) for series in (self.data_tables[fk_table][pk_name] for fk_table in fk_tables)
        ]
        return set(int(x) for x in functools.reduce(flatten_sets, referenced_pk_ids or [], []))

    @log_decorator(enter_message=" --> loading excel...", exit_message=" --> done loading excel", level="DEBUG")
    @staticmethod
    def load(*, schema: SeadSchema, service: SchemaService, source: str | pd.ExcelFile, apply_policies: bool = True) -> "Submission":
        """Loads the submission file into a SubmissionData object"""

        data_tables: dict[str, pd.DataFrame] = Submission.load_data_tables(source, schema)

        submission: Submission = Submission(data_tables, schema)

        if apply_policies:
            for policy in UpdatePolicies.get_sorted_items():
                policy(schema, submission, service).apply()

        return submission

    @staticmethod
    def load_data_tables(source: str | pd.ExcelFile, schema: SeadSchema) -> dict[str, pd.DataFrame]:
        with pd.ExcelFile(source) if isinstance(source, str) else source as reader:
            data_tables: dict[str, pd.DataFrame] = {
                tablename: load_excel_sheet(reader, data.excel_sheet)
                for tablename, data in schema.items()
                if data.excel_sheet in reader.sheet_names
            }

            logger.debug(f"   read sheets: {','.join(k for k in data_tables)}")

            ignore_sheets: set[str] = set(str(s) for s in reader.sheet_names) - set(data_tables.keys())
            if ignore_sheets:
                logger.debug(f"<red>ignored sheets</red>: {','.join(ignore_sheets)}")

            if "data_table_index" in reader.sheet_names:
                logger.info("ignoring data_table_index found in Excel")
        return data_tables

    def to_csv(self, output_folder: str) -> None:
        """Writes lookup data to an CSV file.
        Lookup tables are identified as having column that begins with "(".
        This column is computed by Excel macros in the input file.
        """
        os.makedirs(f"{output_folder}/csv", exist_ok=True)
        for table_name, data in self.data_tables.items():
            data.to_csv(f"{output_folder}/csv/{table_name}.csv", index=False)
            logger.debug(f" ---> {table_name}.csv written to {output_folder}")

    def to_lookups_sql(self: Submission, filename: str = "lookups_inserts.sql") -> None:
        to_lookups_sql(self, filename)
