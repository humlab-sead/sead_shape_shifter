import contextlib
import os
from typing import Any

import pandas as pd
from loguru import logger

from ingesters.sead.dispatchers import Dispatchers, IDispatcher
from ingesters.sead.metadata import Column, SeadSchema, Table
from ingesters.sead.submission import Submission


def _to_int_or_none(value: Any) -> int | None:
    """Convert value to int or return None if conversion fails."""
    with contextlib.suppress(Exception):
        if value is None or pd.isna(value):
            return None
        return int(value)
    return value


def _to_none(value: Any) -> None:
    """Convert value to None if it's NaN or None."""
    with contextlib.suppress(Exception):
        if value is None or pd.isna(value):
            return None
    return value


def _format_value(value: Any, data_type: str) -> str:
    """Format value according to its data type for CSV output."""
    if value is None or pd.isna(value) or value == "NULL":
        return ""
    if data_type == "java.lang.String":
        return '"' + str(value).replace('"', '""') + '"'  # escape double quotes
    if data_type in ("java.lang.Integer", "java.lang.Long", "java.lang.Short"):
        return str(int(float(value)))
    if data_type.startswith("com.sead.database."):  # FK values
        return str(int(float(value)))
    return str(value)


@Dispatchers.register(key="csv", target="folder")
class CsvProcessor(IDispatcher):
    """
    Main class that processes the Submission and produces CSV files directly.

    Creates 4 CSV files:
    - tables.csv: table metadata (table_type, record_count)
    - columns.csv: column metadata (table_type, column_name, column_type)
    - records.csv: record metadata (class_name, system_id, public_id)
    - recordvalues.csv: actual data values (class_name, system_id, public_id, column_name, column_type,
        fk_system_id, fk_public_id, column_value)
    """

    def __init__(self, ignore_columns: list[str] | None = None) -> None:
        self.ignore_columns: list[str] = ignore_columns or ["date_updated"]
        self.output_folder: str | None = None
        self.basename: str = "submission"

        # Data collectors
        self.tables_data: list[dict[str, Any]] = []
        self.columns_data: list[dict[str, Any]] = []
        self.records_data: list[dict[str, Any]] = []
        self.recordvalues_data: list[dict[str, Any]] = []

    def _process_table(self, schema: SeadSchema, submission: Submission, table_name: str) -> None:
        """Process a single table and collect data for CSV export."""
        if table_name not in schema:
            raise ValueError(f"Table {table_name}: not found in metadata")

        table: Table = schema[table_name]
        data: pd.DataFrame = submission.data_tables[table_name]

        if data is None or data.shape[0] == 0:
            return

        logger.debug(f"Processing {table_name}...")

        # Add table metadata
        self.tables_data.append({"table_type": table.java_class, "record_count": str(data.shape[0])})

        # Track which columns we've seen for this table
        columns_added: set[str] = set()
        referenced_keyset: set[int] = submission.get_referenced_keyset(schema, table_name)

        # Process each record in the table
        for idx, record in data.iterrows():
            try:
                data_row: dict = record.to_dict()

                public_id: int | None = _to_int_or_none(data_row[table.pk_name] if table.pk_name in data_row else None)
                system_id: int | None = _to_int_or_none(data_row.get("system_id"))

                if public_id is None and system_id is None:
                    logger.warning(f"Table {table_name}: Skipping row since both CloneId and SystemID is NULL")
                    continue

                if system_id is None:
                    system_id = public_id

                referenced_keyset.discard(system_id)  # type: ignore[arg-type]

                # Add record metadata
                self.records_data.append(
                    {
                        "class_name": table.java_class,
                        "system_id": str(system_id) if system_id else "NULL",
                        "public_id": str(public_id) if public_id is not None else "NULL",
                    }
                )

                # If public_id exists, this is just a reference record - skip column values
                if public_id is not None:
                    continue

                # Process columns for this record
                for column_name, column_spec in table.columns.items():
                    if column_name in self.ignore_columns:
                        continue

                    if column_name not in data_row.keys():
                        if not column_spec.is_nullable and not column_name.endswith("_uuid"):
                            logger.warning(f"Table {table_name}, (not nullable) column {column_name} not found in submission")
                        continue

                    # Add column metadata (only once per table)
                    if column_name not in columns_added:
                        self.columns_data.append(
                            {
                                "table_type": table.java_class,
                                "column_name": column_spec.camel_case_column_name,
                                "column_type": column_spec.class_name,
                            }
                        )
                        columns_added.add(column_name)

                    # Process column value
                    if not column_spec.is_fk:
                        self._process_pk_and_non_fk_value(data_row, public_id, system_id, column_spec, table)
                    else:
                        self._process_fk_value(data_row, column_spec, schema, submission, table)

                # Always add clonedId column
                if "clonedId" not in columns_added:
                    self.columns_data.append(
                        {"table_type": table.java_class, "column_name": "clonedId", "column_type": "java.util.Integer"}
                    )
                    columns_added.add("clonedId")

                # Add clonedId value
                self.recordvalues_data.append(
                    {
                        "class_name": table.java_class,
                        "system_id": str(system_id) if system_id else "NULL",
                        "public_id": "NULL" if public_id is None else str(public_id),
                        "column_name": "clonedId",
                        "column_type": "java.util.Integer",
                        "fk_system_id": "NULL",
                        "fk_public_id": "NULL",
                        "column_value": "NULL" if public_id is None else str(public_id),
                    }
                )

                # Add date_updated if present in schema
                if "date_updated" in table.column_names():
                    if "dateUpdated" not in columns_added:
                        self.columns_data.append(
                            {
                                "table_type": table.java_class,
                                "column_name": "dateUpdated",
                                "column_type": "java.util.Date",
                            }
                        )
                        columns_added.add("dateUpdated")

            except Exception as x:
                logger.error(f"CRITICAL FAILURE: Table {table_name}, row {idx}: {x}")
                raise

        # Add referenced records that weren't in the submission
        if len(referenced_keyset) > 0:
            logger.warning(f"Warning: {table_name} has {len(referenced_keyset)} referenced keys not found in submission")
            for key in referenced_keyset:
                self.records_data.append({"class_name": table.java_class, "system_id": str(int(key)), "public_id": str(int(key))})

    def _process_pk_and_non_fk_value(
        self, data_row: dict, public_id: int | None, system_id: int | None, column: Column, table: Table
    ) -> None:
        """Process a primary key or non-foreign-key column value."""
        value: Any = data_row.get(column.column_name)

        if column.is_pk:
            value = int(public_id) if public_id is not None else system_id
        elif _to_none(value) is None:
            value = "NULL"
        else:
            value = str(value)

        formatted_value = _format_value(value, column.class_name)

        self.recordvalues_data.append(
            {
                "class_name": table.java_class,
                "system_id": str(system_id) if system_id else "NULL",
                "public_id": "NULL" if public_id is None else str(public_id),
                "column_name": column.camel_case_column_name,
                "column_type": column.class_name,
                "fk_system_id": "NULL",
                "fk_public_id": "NULL",
                "column_value": formatted_value,
            }
        )

    def _process_fk_value(self, data_row: dict, column: Column, schema: SeadSchema, submission: Submission, table: Table) -> None:
        """Process a foreign key column value."""
        class_name: str = column.class_name
        camel_case_column_name: str = column.camel_case_column_name

        fk_table_spec: Table = schema.get_table(class_name)
        if fk_table_spec is None or fk_table_spec.table_name is None:
            logger.warning(f"Table {column.table_name}, FK column {column.column_name}: unable to resolve FK class {class_name}")
            return

        fk_system_id: int | None = _to_int_or_none(data_row.get(column.column_name))
        system_id: int | None = _to_int_or_none(data_row.get("system_id"))
        public_id: int | None = _to_int_or_none(data_row[table.pk_name] if table.pk_name in data_row else None)

        if fk_system_id is None:
            self.recordvalues_data.append(
                {
                    "class_name": table.java_class,
                    "system_id": str(system_id) if system_id else "NULL",
                    "public_id": "NULL" if public_id is None else str(public_id),
                    "column_name": camel_case_column_name,
                    "column_type": f"com.sead.database.{class_name}",
                    "fk_system_id": "NULL",
                    "fk_public_id": "NULL",
                    "column_value": "NULL",
                }
            )
            return

        # Look up the FK public_id from the referenced table
        fk_public_id: int | None = None
        fk_data_table: pd.DataFrame | None = submission[fk_table_spec.table_name] if fk_table_spec.table_name in submission else None

        if fk_data_table is None:
            fk_public_id = fk_system_id
        else:
            if "system_id" not in fk_data_table.columns:
                logger.warning(
                    f"Table {column.table_name}, FK column {column.column_name}: system_id not found in {fk_table_spec.table_name}"
                )
                fk_public_id = fk_system_id
            else:
                fk_data_row: pd.DataFrame = fk_data_table.loc[(fk_data_table.system_id == fk_system_id)]
                if fk_data_row.empty or len(fk_data_row) != 1:
                    fk_public_id = fk_system_id
                else:
                    pk_col = fk_table_spec.pk_name
                    if pk_col in fk_data_row.columns:
                        fk_public_id = _to_int_or_none(fk_data_row[pk_col].iloc[0])
                    else:
                        fk_public_id = fk_system_id

        class_name_short = class_name.split(".")[-1]

        self.recordvalues_data.append(
            {
                "class_name": table.java_class,
                "system_id": str(system_id) if system_id else "NULL",
                "public_id": "NULL" if public_id is None else str(public_id),
                "column_name": camel_case_column_name,
                "column_type": f"com.sead.database.{class_name_short}",
                "fk_system_id": str(fk_system_id) if fk_system_id else "NULL",
                "fk_public_id": str(fk_public_id) if fk_public_id is not None else "NULL",
                "column_value": "NULL",
            }
        )

    def _write_csv_files(self) -> None:
        """Write collected data to CSV files."""

        if self.output_folder is None:
            raise ValueError("Output folder is not set or does not exist")

        os.makedirs(self.output_folder, exist_ok=True)

        # Write tables.csv
        tables_file = os.path.join(self.output_folder, f"{self.basename}_tables.csv")
        with open(tables_file, "w", encoding="utf-8") as f:
            f.write("table_type\trecord_count\n")
            for row in self.tables_data:
                f.write(f"{row['table_type']}\t{row['record_count']}\n")
        logger.info(f"Written {tables_file}")

        # Write columns.csv
        columns_file = os.path.join(self.output_folder, f"{self.basename}_columns.csv")
        with open(columns_file, "w", encoding="utf-8") as f:
            f.write("table_type\tcolumn_name\tcolumn_type\n")
            for row in self.columns_data:
                f.write(f"{row['table_type']}\t{row['column_name']}\t{row['column_type']}\n")
        logger.info(f"Written {columns_file}")

        # Write records.csv
        records_file = os.path.join(self.output_folder, f"{self.basename}_records.csv")
        with open(records_file, "w", encoding="utf-8") as f:
            f.write("class_name\tsystem_id\tpublic_id\n")
            for row in self.records_data:
                f.write(f"{row['class_name']}\t{row['system_id']}\t{row['public_id']}\n")
        logger.info(f"Written {records_file}")

        # Write recordvalues.csv
        recordvalues_file = os.path.join(self.output_folder, f"{self.basename}_recordvalues.csv")
        with open(recordvalues_file, "w", encoding="utf-8") as f:
            f.write("class_name\tsystem_id\tpublic_id\tcolumn_name\tcolumn_type\tfk_system_id\tfk_public_id\tcolumn_value\n")
            for row in self.recordvalues_data:
                f.write(
                    f"{row['class_name']}\t{row['system_id']}\t{row['public_id']}\t"
                    f"{row['column_name']}\t{row['column_type']}\t{row['fk_system_id']}\t"
                    f"{row['fk_public_id']}\t{row['column_value']}\n"
                )
        logger.info(f"Written {recordvalues_file}")

    def dispatch(
        self,
        target: str,
        schema: SeadSchema,
        submission: Submission,
        table_names: list[str] | None = None,
        extra_names: list[str] | None = None,
    ) -> None:
        """
        Main dispatch method that processes submission and creates CSV files.

        Args:
            schema: SeadSchema metadata
            submission: Submission data to process
            table_names: Optional list of specific tables to process
            extra_names: Optional extra table names (not used in CSV output)
        """
        self.output_folder = target
        tables_to_process: list[str] = list(submission.data_tables.keys()) if table_names is None else table_names

        # Reset collectors
        self.tables_data = []
        self.columns_data = []
        self.records_data = []
        self.recordvalues_data = []

        os.makedirs(self.output_folder or ".", exist_ok=True)

        # Process each table
        for table_name in sorted(tables_to_process):
            self._process_table(schema, submission, table_name)

        # Write all CSV files
        self._write_csv_files()

        logger.info(f"CSV dispatch complete: {len(self.tables_data)} tables, {len(self.records_data)} records")
