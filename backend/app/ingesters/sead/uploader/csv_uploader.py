import os
from typing import Any

import pandas as pd
from psycopg import Connection
from sqlalchemy import TEXT

from backend.app.ingesters.sead.utility import get_connection_uri, log_decorator

from . import BaseUploader, Uploaders


@Uploaders.register(key="csv")
class CsvUploader(BaseUploader):
    """Upload submission file to database using CSV files directly into staging tables."""

    def __init__(self, *, source: str = "./csv_files", target_schema: str = "clearing_house") -> None:
        self.source: str = source
        self.target_schema: str = target_schema

    @log_decorator(enter_message=" ---> uploading CSV submission...", exit_message=" ---> CSV submission uploaded", level="DEBUG")
    def upload(
        self,
        connection: Connection,
        source: str | Any,
        submission_id: int,  # pylint: disable=unused-argument
    ) -> None:
        if not isinstance(source, str) and not os.path.isdir(source):
            raise ValueError("Source must be an existing folder path")

        for key in ["tables", "columns", "records", "recordvalues"]:
            table_name: str = f"temp_submission_upload_{key}"
            filename: str = os.path.join(self.source, f"{key}.csv")
            self.csv_to_db(connection, filename, self.target_schema, table_name)

    @log_decorator(enter_message=" ---> extracting submission...", exit_message=" ---> submission extracted", level="DEBUG")
    def extract(self, connection: Connection, submission_id: int) -> None:
        """Extraction not needed since these CSV files are uploaded into staging tables."""
        with connection.cursor() as cursor:
            cursor.callproc("clearing_house.fn_extract_csv_upload_to_staging_tables", (submission_id,))  # type: ignore

    def csv_to_db(self, connection: Any, filename: str, target_schema: str, target_table: str) -> None:
        """Using the csv files created by to_csv, import the data into the PostgreSQL database using psycopg"""
        if not os.path.isfile(filename):
            raise ValueError(f"CSV file not found: {filename}")

        uri: str = get_connection_uri(connection)
        data: pd.DataFrame = pd.read_csv(filename, sep="\t", na_values="NULL", keep_default_na=True, dtype=str)
        data.to_sql(
            target_table,
            uri,
            schema=target_schema,
            if_exists="replace",
            index=False,
            dtype={column_name: TEXT for column_name in data.columns},
        )
