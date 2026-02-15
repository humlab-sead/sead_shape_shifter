"""Test edge cases and error handling in CSV dispatcher."""

import pandas as pd

from ingesters.sead.dispatchers.to_csv import CsvProcessor, _format_value, _to_int_or_none, _to_none
from ingesters.sead.submission import Submission
from ingesters.sead.tests.builders import build_column, build_schema, build_table


class TestHelperFunctions:
    """Test helper functions used by CsvProcessor."""

    def test_to_int_or_none_with_valid_int(self):
        assert _to_int_or_none(42) == 42
        assert _to_int_or_none(42.0) == 42
        assert _to_int_or_none("42") == 42

    def test_to_int_or_none_with_none(self):
        assert _to_int_or_none(None) is None
        assert _to_int_or_none(pd.NA) is None
        assert _to_int_or_none(float("nan")) is None

    def test_to_int_or_none_with_invalid(self):
        # Returns original value if conversion fails
        result = _to_int_or_none("not_a_number")
        assert result == "not_a_number"

    def test_to_none_with_none_values(self):
        assert _to_none(None) is None
        assert _to_none(pd.NA) is None
        assert _to_none(float("nan")) is None

    def test_format_value_with_null(self):
        assert _format_value(None, "java.lang.String") == ""
        assert _format_value(pd.NA, "java.lang.Integer") == ""
        assert _format_value("NULL", "java.lang.String") == ""

    def test_format_value_with_string(self):
        assert _format_value("test", "java.lang.String") == '"test"'
        assert _format_value('test "quoted"', "java.lang.String") == '"test ""quoted"""'

    def test_format_value_with_integers(self):
        assert _format_value(42, "java.lang.Integer") == "42"
        assert _format_value(42.0, "java.lang.Long") == "42"
        assert _format_value(42.5, "java.lang.Short") == "42"

    def test_format_value_with_fk(self):
        assert _format_value(100, "com.sead.database.TblSites") == "100"
        assert _format_value(100.0, "com.sead.database.TblLookup") == "100"

    def test_format_value_with_other_types(self):
        assert _format_value(3.14, "java.lang.Double") == "3.14"
        assert _format_value(True, "java.lang.Boolean") == "True"


class TestCsvProcessorEdgeCases:
    """Test edge cases in CsvProcessor."""

    def test_empty_submission(self, tmp_path):
        """Test processing an empty submission."""
        schema = build_schema([build_table("tbl_test", "test_id")])
        submission = Submission(data_tables={}, schema=schema)

        processor = CsvProcessor()
        processor.dispatch(target=tmp_path, schema=schema, submission=submission)

        # Should still create files, but with no data
        tables_file = tmp_path / "submission_tables.csv"
        assert tables_file.exists()

    def test_table_with_no_rows(self, tmp_path):
        """Test processing a table with no rows."""
        schema = build_schema(
            [
                build_table(
                    "tbl_test",
                    "test_id",
                    java_class="TblTest",
                    columns={
                        "test_id": build_column("tbl_test", "test_id", is_pk=True, class_name="java.lang.Integer"),
                        "system_id": build_column("tbl_test", "system_id", class_name="java.lang.Integer"),
                    },
                )
            ]
        )

        data = pd.DataFrame(columns=["system_id", "test_id"])
        submission = Submission(data_tables={"tbl_test": data}, schema=schema)

        processor = CsvProcessor()
        processor.dispatch(target=tmp_path, schema=schema, submission=submission)

        records_file = tmp_path / "submission_records.csv"
        records_df = pd.read_csv(records_file, sep="\t", na_values="NULL", keep_default_na=False)
        assert len(records_df) == 0

    def test_null_values_in_columns(self, tmp_path):
        """Test handling of NULL values in various column types."""
        schema = build_schema(
            [
                build_table(
                    "tbl_test",
                    "test_id",
                    java_class="TblTest",
                    columns={
                        "test_id": build_column("tbl_test", "test_id", is_pk=True, class_name="java.lang.Integer"),
                        "nullable_int": build_column("tbl_test", "nullable_int", is_nullable=True, class_name="java.lang.Integer"),
                        "nullable_str": build_column(
                            "tbl_test",
                            "nullable_str",
                            data_type="varchar",
                            is_nullable=True,
                            class_name="java.lang.String",
                        ),
                        "system_id": build_column("tbl_test", "system_id", class_name="java.lang.Integer"),
                    },
                )
            ]
        )

        data = pd.DataFrame({"system_id": [1], "test_id": [None], "nullable_int": [None], "nullable_str": [None]})
        submission = Submission(data_tables={"tbl_test": data}, schema=schema)

        processor = CsvProcessor()
        processor.dispatch(target=tmp_path, schema=schema, submission=submission)

        recordvalues_file = tmp_path / "submission_recordvalues.csv"
        recordvalues_df = pd.read_csv(recordvalues_file, sep="\t", na_values="NULL", keep_default_na=False)

        # NULL values should be represented as empty strings in CSV
        null_rows = recordvalues_df[recordvalues_df["column_name"].isin(["nullable_int", "nullable_str"])]
        assert all(null_rows["column_value"] == "")

    def test_table_names_parameter(self, tmp_path):
        """Test filtering by table names."""
        schema = build_schema(
            [
                build_table(
                    "tbl_test1",
                    "test1_id",
                    java_class="TblTest1",
                    columns={
                        "test1_id": build_column("tbl_test1", "test1_id", is_pk=True, class_name="java.lang.Integer"),
                        "system_id": build_column("tbl_test1", "system_id", class_name="java.lang.Integer"),
                    },
                ),
                build_table(
                    "tbl_test2",
                    "test2_id",
                    java_class="TblTest2",
                    columns={
                        "test2_id": build_column("tbl_test2", "test2_id", is_pk=True, class_name="java.lang.Integer"),
                        "system_id": build_column("tbl_test2", "system_id", class_name="java.lang.Integer"),
                    },
                ),
            ]
        )

        submission = Submission(
            data_tables={
                "tbl_test1": pd.DataFrame({"system_id": [1], "test1_id": [None]}),
                "tbl_test2": pd.DataFrame({"system_id": [2], "test2_id": [None]}),
            },
            schema=schema,
        )

        processor = CsvProcessor()
        processor.dispatch(target=tmp_path, schema=schema, submission=submission, table_names=["tbl_test1"])

        tables_file = tmp_path / "submission_tables.csv"
        tables_df = pd.read_csv(tables_file, sep="\t")

        # Should only process tbl_test1
        assert len(tables_df) == 1
        assert tables_df.iloc[0]["table_type"] == "TblTest1"

    def test_special_characters_in_strings(self, tmp_path):
        """Test handling of special characters in string values."""
        schema = build_schema(
            [
                build_table(
                    "tbl_test",
                    "test_id",
                    java_class="TblTest",
                    columns={
                        "test_id": build_column("tbl_test", "test_id", is_pk=True, class_name="java.lang.Integer"),
                        "name": build_column("tbl_test", "name", data_type="varchar", class_name="java.lang.String"),
                        "system_id": build_column("tbl_test", "system_id", class_name="java.lang.Integer"),
                    },
                )
            ]
        )

        data = pd.DataFrame(
            {
                "system_id": [1, 2, 3],
                "test_id": [None, None, None],
                "name": ['test "quoted"', "test\ttab", "test\nnewline"],
            }
        )
        submission = Submission(data_tables={"tbl_test": data}, schema=schema)

        processor = CsvProcessor()
        processor.dispatch(target=tmp_path, schema=schema, submission=submission)

        recordvalues_file = tmp_path / "submission_recordvalues.csv"
        recordvalues_df = pd.read_csv(recordvalues_file, sep="\t", na_values="NULL", keep_default_na=False)

        name_rows = recordvalues_df[recordvalues_df["column_name"] == "name"]
        assert len(name_rows) == 3

    def test_mixed_new_and_existing_records(self, tmp_path):
        """Test processing tables with both new records (NULL pk) and existing records (non-NULL pk)."""
        schema = build_schema(
            [
                build_table(
                    "tbl_test",
                    "test_id",
                    java_class="TblTest",
                    columns={
                        "test_id": build_column("tbl_test", "test_id", is_pk=True, class_name="java.lang.Integer"),
                        "name": build_column("tbl_test", "name", data_type="varchar", class_name="java.lang.String"),
                        "system_id": build_column("tbl_test", "system_id", class_name="java.lang.Integer"),
                    },
                )
            ]
        )

        data = pd.DataFrame(
            {
                "system_id": [1, 2, 3],
                "test_id": [None, 42, None],  # Mix of new and existing
                "name": ["New A", "Existing B", "New C"],
            }
        )
        submission = Submission(data_tables={"tbl_test": data}, schema=schema)

        processor = CsvProcessor()
        processor.dispatch(target=tmp_path, schema=schema, submission=submission)

        records_file = tmp_path / "submission_records.csv"
        records_df = pd.read_csv(records_file, sep="\t", na_values="NULL", keep_default_na=False)

        assert len(records_df) == 3
        # Check that existing record has public_id
        existing_record = records_df[records_df["system_id"] == 2]
        if len(existing_record) > 0:
            # CSV may store as string or int depending on pandas reading
            public_id = existing_record.iloc[0]["public_id"]
            assert str(int(float(public_id))) == "42"

    def test_dispatch_creates_directory_if_missing(self, tmp_path):
        """Test that dispatch creates output directory if it doesn't exist."""
        output_dir = tmp_path / "new_folder"
        assert not output_dir.exists()

        schema = build_schema([build_table("tbl_test", "test_id", java_class="TblTest")])
        submission = Submission(data_tables={}, schema=schema)

        processor = CsvProcessor()
        processor.dispatch(target=output_dir, schema=schema, submission=submission)

        assert output_dir.exists()
        assert (output_dir / "submission_tables.csv").exists()
