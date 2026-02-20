from collections.abc import ItemsView, Iterator, KeysView, ValuesView
from dataclasses import asdict, dataclass, field
from fnmatch import fnmatch
from functools import cached_property
from typing import Any, cast

# pylint: disable=no-member
import pandas as pd
from pandas._typing import Dtype

from src.configuration.resolve import ConfigValue

from .utility import camel_case_name, load_dataframe_from_postgres

DTYPE_MAPPING: dict[str, Dtype] = {
    # identifiers
    "uuid": "string",
    # integers
    "smallint": "Int16",
    "integer": "Int32",
    "int": "Int32",
    "bigint": "Int64",
    # numeric / floating
    "real": "Float32",
    "double precision": "Float64",
    "numeric": "Float64",
    "decimal": "Float64",
    # boolean
    "boolean": "boolean",
    "bool": "boolean",
    # text / character
    "character varying": "string",
    "varchar": "string",
    "character": "string",
    "char": "string",
    "text": "string",
    # date / time
    "date": "datetime64[ns]",
    "timestamp": "datetime64[ns]",
    "timestamp without time zone": "datetime64[ns]",
    "timestamp with time zone": "datetime64[ns, UTC]",
    "time": "string",  # pandas has no native time-only dtype
    # json
    "json": "object",
    "jsonb": "object",
    # binary
    "bytea": "object",
    # arrays (usually end up as Python lists)
    "integer[]": "object",
    "text[]": "object",
}


@dataclass
class Column:
    table_name: str
    column_name: str
    xml_column_name: str  # Note: pending deprecation
    position: int
    data_type: str
    numeric_precision: int
    numeric_scale: int
    character_maximum_length: int
    is_nullable: bool
    is_pk: bool
    is_fk: bool
    fk_table_name: str | None
    fk_column_name: str | None
    class_name: str

    def __contains__(self, key: str) -> bool:
        return key in self.__dict__

    def __getitem__(self, key: str) -> Any:
        return self.__dict__[key]

    def keys(self) -> list[str]:
        return list(self.asdict().keys())

    def values(self) -> list[str]:
        return list(self.asdict().values())

    def asdict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def camel_case_column_name(self) -> str:
        return camel_case_name(self.column_name)


@dataclass
class Table:
    table_name: str
    pk_name: str
    java_class: str
    excel_sheet: str
    is_lookup: bool
    is_new: bool = field(default=False)
    is_unknown: bool = field(default=False)
    columns: dict[str, Column] = field(default_factory=dict)

    def __contains__(self, key: str) -> bool:
        return key in self.columns

    def __getitem__(self, key: str) -> Column | dict[str, Column]:
        if key == "columns":
            return self.columns
        return self.columns[key]

    def __iter__(self) -> Iterator[Column]:
        return iter(self.columns.values())

    def __len__(self) -> int:
        return len(self.columns)

    def get_column(self, column_name: str) -> Column | None:
        return self.columns.get(column_name)

    def keys(self) -> list[str]:
        return list(asdict(self).keys())

    def values(self) -> list[Column]:
        return list(asdict(self).values())

    def column_names(self, skip_nullable: bool = False) -> list[str]:
        return sorted(c.column_name for c in self.columns.values() if not (skip_nullable and c.is_nullable))

    def nullable_column_names(self) -> list[str]:
        return sorted(c.column_name for c in self.columns.values() if c.is_nullable)


class SeadSchema:

    def __init__(self, tables: dict[str, Table], source_tables: pd.DataFrame, source_columns: pd.DataFrame) -> None:
        self._tables: dict[str, Table] = dict(tables)  # defensive copy
        self._tables_lookup: dict[str, Table] = (
            self._tables
            | {t.java_class: t for t in self._tables.values()}
            | {t.excel_sheet: t for t in self._tables.values() if t.excel_sheet and t.excel_sheet != t.table_name}
        )
        self.source_tables: pd.DataFrame = source_tables
        self.source_columns: pd.DataFrame = source_columns
        self.foreign_key_aliases: dict[str, str] = {"updated_dataset_id": "dataset_id"}

    def __getitem__(self, key: str) -> Table:
        return self._tables[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._tables)

    def __len__(self) -> int:
        return len(self._tables)

    def __contains__(self, key: str) -> bool:
        return key in self._tables

    def keys(self) -> KeysView[str]:
        return self._tables.keys()

    def values(self) -> ValuesView[Table]:
        return self._tables.values()

    def items(self) -> ItemsView[str, Table]:
        return self._tables.items()

    def get(self, key: str, default: Table | None = None) -> Table | None:
        """Get a table by name, or return default if not found."""
        return self._tables.get(key, default)

    def get_table(self, table_name: str) -> Table:
        """Get a table by name, table type or alias (excel_sheet), or raise KeyError if not found."""
        if table_name in self._tables_lookup:
            return self._tables_lookup[table_name]
        raise KeyError(f"Table {table_name} not found in schema")

    def get_column(self, table_name: str, column_name: str) -> Column:
        table: Table = self.get_table(table_name)
        if column_name not in table.columns:
            raise KeyError(f"Column {column_name} not found in metadata for table {table_name}")
        return table.columns[column_name]

    @cached_property
    def lookup_tables(self) -> list[Table]:
        return [t for t in self.values() if t.is_lookup]

    @cached_property
    def aliased_tables(self) -> list[Table]:
        return [t for t in self.values() if t.excel_sheet != t.table_name]

    @cached_property
    def table_name2excel_sheet(self) -> dict[str, str]:
        return {t: x.excel_sheet for t, x in self.items()}

    @cached_property
    def _foreign_keys(self) -> pd.DataFrame:
        """Returns foreign key columns from SEAD columns (performance only)."""
        return self.source_columns[self.source_columns.is_fk][["table_name", "column_name", "fk_table_name", "class_name"]]

    def get_tablenames_referencing(self, table_name: str) -> list[str]:
        """Returns a list of tablenames referencing the given table"""
        return self._foreign_keys.loc[(self._foreign_keys.fk_table_name == table_name)]["table_name"].tolist()

    def is_fk(self, table_name: str, column_name: str) -> bool:
        if column_name in self.foreign_key_aliases:
            return True
        return self.get_column(table_name, column_name).is_fk

    def is_pk(self, table_name: str, column_name: str) -> bool:
        return self.get_column(table_name, column_name).is_pk

    @cached_property
    def sead_column_dtypes(self) -> dict[str, Dtype]:
        """Returns a dict of table to datatype mappings."""
        column_types: dict[str, Any] = cast(dict[str, Any], self.source_columns.set_index("column_name")["data_type"].to_dict())
        dtypes: dict[str, Dtype] = {k: DTYPE_MAPPING[v] for k, v in column_types.items() if v in DTYPE_MAPPING}
        return dtypes


class SeadSchemaFactory:

    def create(self, sead_tables: pd.DataFrame, sead_columns: pd.DataFrame) -> SeadSchema:
        """Build a SeadSchema from sead_tables and sead_columns dataframes."""

        # Group columns once: table_name -> dataframe of that table's columns
        cols_by_table = dict(tuple(sead_columns.groupby("table_name", sort=False)))
        tables: dict[str, Table] = {}

        # Each row becomes one table definition dict (kwargs for Table)
        for table_name, table_row in sead_tables.to_dict(orient="index").items():

            assert isinstance(table_name, str)

            table_properties: dict[str, Any] = table_row  # type: ignore[arg-type]
            cols_df = cols_by_table.get(table_name)
            if cols_df is None:
                columns: dict[str, Column] = {}
            else:
                rows = cols_df.to_dict(orient="records")
                columns = {str(row["column_name"]): Column(**row) for row in rows}  # type: ignore[arg-type]

            tables[str(table_name)] = Table(columns=columns, **table_properties)  # type: ignore[arg-type]

        return SeadSchema(tables=tables, source_tables=sead_tables, source_columns=sead_columns)


class SchemaService:
    """Service class to access metadata information"""

    def __init__(self, db_uri: str, ignore_columns: list[str] | None = None) -> None:
        self.db_uri: str = db_uri
        # Only fall back to ConfigValue if ignore_columns is None (not just empty)
        if ignore_columns is not None:
            self.ignore_columns: list[str] = ignore_columns
        else:
            self.ignore_columns = ConfigValue("options.ignore_columns", default=[]).resolve() or []

    def get_sead_tables(self) -> pd.DataFrame:
        """Returns a dataframe of tables from SEAD with attributes."""
        sql: str = """
            select  table_name,
                    pk_name,
                    java_class,
                    excel_sheet,
                    is_lookup,
                    is_unknown
            from clearing_house.clearinghouse_import_tables
        """
        return self._load_sead_data(sql, ["table_name"])

    def get_sead_columns(self) -> pd.DataFrame:
        """Returns a dataframe of table columns from SEAD with attributes."""
        sql: str = """
            select  table_name,
                    column_name,
                    data_type,
                    xml_column_name,
                    position,
                    numeric_precision,
                    numeric_scale,
                    character_maximum_length,
                    is_nullable,
                    is_pk,
                    is_fk,
                    fk_table_name,
                    fk_column_name,
                    class_name
            from clearing_house.clearinghouse_import_columns
        """
        data: pd.DataFrame = self._load_sead_data(sql, ["table_name", "column_name"], ["table_name", "position"])
        data = self.remove_ignored_columns(data)

        return data

    def remove_ignored_columns(self, data: pd.DataFrame) -> pd.DataFrame:
        if self.ignore_columns:
            columns_to_ignore: list[str] = [
                c for c in data["column_name"].unique() if any(fnmatch(c, pattern) for pattern in self.ignore_columns)
            ]
            data = data[~data["column_name"].isin(columns_to_ignore)]
        return data

    def get_primary_key_values(self, table_name: str, pk_name: str) -> set[int]:
        """Returns all unique primary keys for `table_name` in SEAD."""
        sql: str = f"""
            select distinct {pk_name}
            from {table_name}
        """
        keys: set = set(self._load_sead_data(sql, index=[pk_name]).index)
        return keys

    def _load_sead_data(self, source: str | pd.DataFrame, index: list[str], sortby: list[str] | None = None) -> pd.DataFrame:
        """Returns a dataframe of tables from SEAD with attributes."""
        index = index if isinstance(index, list) else [index]
        sortby = sortby if isinstance(sortby, list) else [sortby] if sortby else None
        data: pd.DataFrame = self._resolve_source(source)
        data = data.set_index(index, drop=False).rename_axis([f"index_{x}" for x in index]).sort_values(by=sortby if sortby else index)
        return data

    def _resolve_source(self, source: str | pd.DataFrame) -> pd.DataFrame:
        if isinstance(source, pd.DataFrame):
            return source
        return load_dataframe_from_postgres(source, self.db_uri, index_col=None)

    def load(self) -> SeadSchema:
        """Loads the SEAD schema from the database."""
        sead_tables: pd.DataFrame = self.get_sead_tables()
        sead_columns: pd.DataFrame = self.get_sead_columns()
        return SeadSchemaFactory().create(sead_tables, sead_columns)


class MockSchemaService(SchemaService):
    """Mock SchemaService for testing purposes."""

    def __init__(self, sead_tables: pd.DataFrame, sead_columns: pd.DataFrame) -> None:
        super().__init__(db_uri="")
        self._sead_tables: pd.DataFrame = self._load_sead_data(sead_tables, ["table_name"], ["table_name"])
        self._sead_columns: pd.DataFrame = self._load_sead_data(sead_columns, ["table_name", "column_name"], ["table_name", "position"])
        self.ignore_columns = ["date_updated", "*_uuid", "(*"]

    def get_sead_tables(self) -> pd.DataFrame:
        return self._sead_tables

    def get_sead_columns(self) -> pd.DataFrame:
        return self._sead_columns
