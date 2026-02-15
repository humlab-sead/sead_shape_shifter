"""Test the CSV dispatcher functionality."""

import tempfile
from pathlib import Path

import pandas as pd

from ingesters.sead.dispatchers.to_csv import CsvProcessor
from ingesters.sead.submission import Submission
from ingesters.sead.tests.builders import build_column, build_schema, build_table


def test_csv_processor_creates_four_files(tmp_path):
    """Test that CsvProcessor creates the 4 required CSV files."""
    # Create minimal schema
    schema = build_schema(
        [
            build_table(
                table_name="tbl_test",
                pk_name="test_id",
                java_class="TblTest",
                columns={
                    "test_id": build_column("tbl_test", "test_id", is_pk=True, class_name="java.lang.Integer"),
                    "name": build_column("tbl_test", "name", data_type="varchar", class_name="java.lang.String"),
                    "system_id": build_column("tbl_test", "system_id", data_type="integer", class_name="java.lang.Integer"),
                },
            )
        ]
    )

    # Create minimal submission
    data = pd.DataFrame({"system_id": [1, 2], "test_id": [None, None], "name": ["Test A", "Test B"]})  # New records

    submission = Submission(data_tables={"tbl_test": data}, schema=schema)  # type: ignore

    processor = CsvProcessor()
    processor.dispatch(target=tmp_path, schema=schema, submission=submission)

    # Check that all 4 CSV files were created
    expected_files = [
        tmp_path / "submission_tables.csv",
        tmp_path / "submission_columns.csv",
        tmp_path / "submission_records.csv",
        tmp_path / "submission_recordvalues.csv",
    ]

    for expected_file in expected_files:
        assert expected_file.exists(), f"Expected file {expected_file} was not created"

    # Verify tables.csv content
    tables_df = pd.read_csv(expected_files[0], sep="\t")
    assert len(tables_df) == 1
    assert tables_df.iloc[0]["table_type"] == "TblTest"
    assert int(tables_df.iloc[0]["record_count"]) == 2

    # Verify records.csv content
    records_df = pd.read_csv(expected_files[2], sep="\t", na_values="NULL", keep_default_na=False)
    assert len(records_df) == 2
    assert all(records_df["class_name"] == "TblTest")


def test_csv_processor_handles_foreign_keys(tmp_path):
    """Test that CsvProcessor correctly handles foreign key relationships."""
    # Create schema with FK relationship
    schema = build_schema(
        [
            build_table(
                table_name="tbl_main",
                pk_name="main_id",
                java_class="TblMain",
                columns={
                    "main_id": build_column("tbl_main", "main_id", is_pk=True, class_name="java.lang.Integer"),
                    "lookup_id": build_column(
                        "tbl_main",
                        "lookup_id",
                        is_fk=True,
                        fk_table_name="tbl_lookup",
                        class_name="TblLookup",
                        data_type="integer",
                    ),
                    "system_id": build_column("tbl_main", "system_id", data_type="integer", class_name="java.lang.Integer"),
                },
            ),
            build_table(
                table_name="tbl_lookup",
                pk_name="lookup_id",
                java_class="TblLookup",
                is_lookup=True,
                columns={
                    "lookup_id": build_column("tbl_lookup", "lookup_id", is_pk=True, class_name="java.lang.Integer"),
                    "value": build_column("tbl_lookup", "value", data_type="varchar", class_name="java.lang.String"),
                    "system_id": build_column("tbl_lookup", "system_id", data_type="integer", class_name="java.lang.Integer"),
                },
            ),
        ]
    )

    # Create submission with FK reference
    lookup_data = pd.DataFrame({"system_id": [100], "lookup_id": [1], "value": ["Lookup Value"]})

    main_data = pd.DataFrame({"system_id": [1], "main_id": [None], "lookup_id": [100]})  # References system_id in lookup table

    submission = Submission(
        data_tables={"tbl_main": main_data, "tbl_lookup": lookup_data},
        schema=schema,
    )

    processor = CsvProcessor()
    processor.dispatch(target=tmp_path, schema=schema, submission=submission)

    # Verify recordvalues.csv contains FK information
    recordvalues_file = tmp_path / "submission_recordvalues.csv"
    recordvalues_df = pd.read_csv(recordvalues_file, sep="\t", na_values="NULL", keep_default_na=False)

    # Find FK column in recordvalues
    fk_rows = recordvalues_df[recordvalues_df["column_name"] == "lookupId"]
    assert len(fk_rows) > 0, "FK column not found in recordvalues"

    # Verify FK has system_id and public_id
    fk_row = fk_rows.iloc[0]
    assert str(int(float(fk_row["fk_system_id"]))) == "100"  # References lookup system_id
    assert str(int(float(fk_row["fk_public_id"]))) == "1"  # Resolved to lookup public_id


def test_csv_processor_format_compatibility():
    """Test that CSV format matches expected output format."""
    # This is a structural test to ensure the CSV files have the correct columns

    # Expected columns for each CSV file type
    expected_columns = {
        "tables": ["table_type", "record_count"],
        "columns": ["table_type", "column_name", "column_type"],
        "records": ["class_name", "system_id", "public_id"],
        "recordvalues": [
            "class_name",
            "system_id",
            "public_id",
            "column_name",
            "column_type",
            "fk_system_id",
            "fk_public_id",
            "column_value",
        ],
    }

    # Create minimal schema and submission
    schema = build_schema(
        [
            build_table(
                table_name="tbl_test",
                pk_name="test_id",
                java_class="TblTest",
                columns={
                    "test_id": build_column("tbl_test", "test_id", is_pk=True, class_name="java.lang.Integer"),
                    "system_id": build_column("tbl_test", "system_id", data_type="integer", class_name="java.lang.Integer"),
                },
            )
        ]
    )

    data = pd.DataFrame(
        {
            "system_id": [1],
            "test_id": [None],
        }
    )

    submission = Submission(data_tables={"tbl_test": data}, schema=schema)  # type: ignore

    with tempfile.TemporaryDirectory() as tmp_dir:

        processor = CsvProcessor()
        processor.dispatch(target=tmp_dir, schema=schema, submission=submission)

        # Check each CSV file has the correct columns
        for file_type, expected_cols in expected_columns.items():
            csv_file = Path(tmp_dir) / f"submission_{file_type}.csv"
            assert csv_file.exists(), f"{csv_file} was not created"

            df = pd.read_csv(csv_file, sep="\t", nrows=0)  # Just read headers
            assert list(df.columns) == expected_cols, f"{file_type}.csv has incorrect columns: {list(df.columns)} != {expected_cols}"
