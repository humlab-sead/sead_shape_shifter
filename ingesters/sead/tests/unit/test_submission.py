import pandas as pd
from importer.metadata import SeadSchema
from importer.specification import SubmissionSpecification
from importer.submission import Submission

# pylint: disable=too-many-statements,unused-argument,redefined-outer-name


class TestSubmission:

    def test_submission_is_created_correctly(self, minimal_schema: SeadSchema):
        data_tables = {"tbl_test": pd.DataFrame({"system_id": [1, 2], "test_id": [1, 2], "name": ["A", "B"]})}
        submission = Submission(data_tables=data_tables, schema=minimal_schema)

        assert submission is not None
        assert submission.data_tables is not None
        assert len(submission.data_tables) > 0
        assert isinstance(submission.data_tables, dict)

    def test_contains(self, minimal_schema: SeadSchema):
        data_tables = {"tbl_test": pd.DataFrame({"system_id": [1], "test_id": [1], "name": ["A"]})}
        submission = Submission(data_tables=data_tables, schema=minimal_schema)

        assert "tbl_test" in submission
        assert "tbl_dummy" not in submission

    def test_exists(self, minimal_schema: SeadSchema):
        data_tables = {"tbl_test": pd.DataFrame({"system_id": [1], "test_id": [1], "name": ["A"]})}
        submission = Submission(data_tables=data_tables, schema=minimal_schema)

        assert "tbl_test" in submission
        assert "tbl_dummy" not in submission

    def test_data_tablenames(self, two_table_schema: SeadSchema):
        data_tables = {
            "tbl_main": pd.DataFrame({"system_id": [1], "main_id": [1], "lookup_id": [100]}),
            "tbl_lookup": pd.DataFrame({"system_id": [100], "lookup_id": [1], "value": ["test"]}),
        }
        submission = Submission(data_tables=data_tables, schema=two_table_schema)

        assert "tbl_main" in submission.data_table_names
        assert "tbl_lookup" in submission.data_table_names

    def test_has_system_id(self, minimal_schema: SeadSchema):
        data_tables = {"tbl_test": pd.DataFrame({"system_id": [1], "test_id": [1], "name": ["A"]})}
        submission = Submission(data_tables=data_tables, schema=minimal_schema)

        assert submission.has_system_id("tbl_test")
        assert not submission.has_system_id("tbl_dummy")

    def test_referenced_keyset(self, two_table_schema: SeadSchema):
        """Test that FK references are correctly identified."""
        data_tables = {
            "tbl_main": pd.DataFrame({"system_id": [1, 2], "main_id": [1, 2], "lookup_id": [100, 101]}),
            "tbl_lookup": pd.DataFrame({"system_id": [100, 101], "lookup_id": [1, 2], "value": ["A", "B"]}),
        }
        submission = Submission(data_tables=data_tables, schema=two_table_schema)

        key_set: set[int] = submission.get_referenced_keyset(two_table_schema, "tbl_lookup")
        assert key_set == {100, 101}

    def test_tables_specifications(self, minimal_schema: SeadSchema):
        # Use compatible dtype (object matches 'varchar' better than string)
        data_tables = {"tbl_test": pd.DataFrame({"system_id": [1], "test_id": [1], "name": ["A"]}, dtype=object)}
        # Convert numeric columns to proper types
        data_tables["tbl_test"]["system_id"] = data_tables["tbl_test"]["system_id"].astype("Int32")
        data_tables["tbl_test"]["test_id"] = data_tables["tbl_test"]["test_id"].astype("Int32")

        submission = Submission(data_tables=data_tables, schema=minimal_schema)

        specification: SubmissionSpecification = SubmissionSpecification(
            schema=minimal_schema, ignore_columns=["date_updated", "*_uuid"], raise_errors=False
        )
        specification.is_satisfied_by(submission)
        assert specification.messages.errors == []
