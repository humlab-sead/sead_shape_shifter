from typing import Any

import psycopg
from loguru import logger
from psycopg import Connection

from .uploader import BaseUploader, NullUploader, Uploaders
from .utility import log_decorator


class NullConnection:
    def cursor(self):
        raise RuntimeError("No active database connection")

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass


class SubmissionRepository:
    def __init__(self, db_options: dict[str, Any], uploader: str | BaseUploader) -> None:
        self.db_options: dict[str, Any] = db_options
        self.uploader: BaseUploader = uploader if isinstance(uploader, BaseUploader) else (Uploaders.get(uploader) or NullUploader)()
        self.connection: Connection | NullConnection = NullConnection()
        self.timeout_seconds: int = 300

    @log_decorator(enter_message=" ---> extracting submission...", exit_message=" ---> submission extracted", level="DEBUG")
    def extract_to_staging_tables(self, submission_id: int) -> None:
        with self as connection:
            self.uploader.extract(connection=connection, submission_id=submission_id)

    @log_decorator(enter_message=" ---> exploding submission...", exit_message=" ---> submission exploded", level="DEBUG")
    def explode_to_public_tables(self, submission_id: int, p_dry_run: bool = False, p_add_missing_columns: bool = False) -> None:
        """Explode submission into public tables."""
        with self as connection:
            for table_name_underscored in self.get_table_names(submission_id):
                logger.debug(f"   --> Exploding table {table_name_underscored}")
                if p_dry_run:
                    continue

                if p_add_missing_columns:
                    with connection.cursor() as cursor:
                        cursor.callproc(  # type: ignore
                            "clearing_house.fn_add_new_public_db_columns", (submission_id, table_name_underscored)
                        )

                with connection.cursor() as cursor:
                    cursor.callproc(  # type: ignore
                        "clearing_house.fn_copy_extracted_values_to_entity_table",
                        (submission_id, table_name_underscored),
                    )

    @log_decorator(enter_message=" ---> removing submission...", exit_message=" ---> submission removed", level="DEBUG")
    def remove(self, submission_id: int, clear_header: bool = False, clear_exploded: bool = True) -> None:
        """Delete submission from staging tables."""
        logger.info("   --> Cleaning up existing data for submission...")
        with self as connection:
            with connection.cursor() as cursor:
                cursor.callproc("clearing_house.fn_delete_submission", (submission_id, clear_header, clear_exploded))  # type: ignore

    def get_id_by_name(self, name: str) -> int:
        sql: str = "select submission_id from clearing_house.tbl_clearinghouse_submissions " "where submission_name = %s limit 1;"
        with self as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, (name,))
                submission_id: int = cursor.fetchone()[0]  # type: ignore
        return submission_id

    @log_decorator(enter_message=" ---> setting state to pending...", exit_message=" ---> state set to pending", level="DEBUG")
    def set_pending(self, submission_id: int) -> None:
        with self as connection:
            with connection.cursor() as cursor:
                sql: str = """
                    update clearing_house.tbl_clearinghouse_submissions
                        set submission_state_id = %s, status_text = %s
                    where submission_id = %s
                """
                cursor.execute(sql, (2, "Pending", submission_id))

    @log_decorator(enter_message=" ---> registering submission...", exit_message=" ---> submission registered", level="DEBUG")
    def register(self, *, name: str, source_name: str, data_types: str = "") -> int:
        with self as connection:
            with connection.cursor() as cursor:
                sql = """
                    insert into clearing_house.tbl_clearinghouse_submissions(
                        submission_name,
                        source_name,
                        submission_state_id,
                        data_types,
                        upload_user_id,
                        status_text
                    ) values (%s, %s, %s, %s, %s, %s) returning submission_id;
                """
                cursor.execute(sql, (name, source_name, 1, data_types, 4, "New"))
                submission_id: int = cursor.fetchone()[0]  # type: ignore
            return submission_id

    def get_table_names(self, submission_id: int) -> list[str]:
        """Get list of table names in underscored format for a submission.
        NOTE: even though XML format is deprecated, these legacy tables are used for the time being.
        """
        tables_names_sql: str = """
            select distinct t.table_name_underscored
            from clearing_house.tbl_clearinghouse_submission_tables t
            join clearing_house.tbl_clearinghouse_submission_xml_content_tables c
                on c.table_id = t.table_id
            where c.submission_id = %s
        """
        with self as connection:
            with connection.cursor() as cursor:
                cursor.execute(tables_names_sql, (submission_id,))
                table_names: list[tuple[Any, ...]] = cursor.fetchall()
        return [t[0] for t in table_names]

    def __enter__(self) -> Connection:
        if isinstance(self.connection, NullConnection):
            timeout_ms: int = self.timeout_seconds * 1000
            self.connection = psycopg.connect(
                **self.db_options,
                options=f"-c statement_timeout={timeout_ms} -c idle_in_transaction_session_timeout={timeout_ms}",
            )
        return self.connection

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not isinstance(self.connection, NullConnection):
            if exc_type is not None:
                self.connection.rollback()
            else:
                self.connection.commit()
            self.connection.close()
        self.connection = NullConnection()
