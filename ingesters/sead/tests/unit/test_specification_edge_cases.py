"""Additional tests for specification edge cases."""

import pandas as pd
import pytest
from importer.specification import (
    ColumnTypesSpecification,
    ForeignKeyColumnsHasValuesSpecification,
    ForeignKeyExistsAsPrimaryKeySpecification,
    HasPrimaryKeySpecification,
    HasSystemIdSpecification,
    NonNullableColumnHasValueSpecification,
    SpecificationError,
    SubmissionSpecification,
)
from importer.submission import Submission

from tests.builders import build_column, build_schema, build_table


class TestSpecificationEdgeCases:
    """Test edge cases in specification validation."""

    def test_specification_with_empty_table(self):
        """Test that specification handles empty tables correctly."""
        schema = build_schema([build_table("tbl_test", "test_id")])
        data = pd.DataFrame(columns=["system_id", "test_id"])
        submission = Submission(data_tables={"tbl_test": data}, schema=schema)

        spec = SubmissionSpecification(schema=schema, raise_errors=False)
        result = spec.is_satisfied_by(submission)
        # Empty table should pass (no data to validate)
        assert result is True

    def test_has_system_id_with_nulls(self):
        """Test that HasSystemIdSpecification catches NULL system_ids."""
        schema = build_schema([build_table("tbl_test", "test_id")])
        data = pd.DataFrame({"system_id": [1, None, 3], "test_id": [1, 2, 3]})
        submission = Submission(data_tables={"tbl_test": data}, schema=schema)

        spec = HasSystemIdSpecification(schema=schema)
        spec.is_satisfied_by(submission, table_name="tbl_test")

        assert len(spec.errors) > 0
        assert any("missing system id" in err.lower() for err in spec.errors)

    def test_has_system_id_with_duplicates(self):
        """Test that HasSystemIdSpecification catches duplicate system_ids."""
        schema = build_schema([build_table("tbl_test", "test_id")])
        data = pd.DataFrame({"system_id": [1, 1, 2], "test_id": [1, 2, 3]})
        submission = Submission(data_tables={"tbl_test": data}, schema=schema)

        spec = HasSystemIdSpecification(schema=schema)
        spec.is_satisfied_by(submission, table_name="tbl_test")

        assert len(spec.errors) > 0
        assert any("duplicate" in err.lower() for err in spec.errors)

    def test_foreign_key_columns_has_values_with_nullable_fk(self):
        """Test FK validation with nullable foreign keys."""
        schema = build_schema(
            [
                build_table(
                    "tbl_main",
                    "main_id",
                    columns={
                        "main_id": build_column("tbl_main", "main_id", is_pk=True),
                        "nullable_fk": build_column("tbl_main", "nullable_fk", is_fk=True, is_nullable=True, fk_table_name="tbl_lookup"),
                        "system_id": build_column("tbl_main", "system_id"),
                    },
                ),
                build_table("tbl_lookup", "lookup_id", is_lookup=True),
            ]
        )

        # All rows are new (pk is NULL), but nullable FK can be NULL
        data = pd.DataFrame({"system_id": [1, 2], "main_id": [None, None], "nullable_fk": [None, None]})
        submission = Submission(data_tables={"tbl_main": data, "tbl_lookup": pd.DataFrame()}, schema=schema)

        spec = ForeignKeyColumnsHasValuesSpecification(schema=schema)
        spec.is_satisfied_by(submission, table_name="tbl_main")

        # Should pass without errors since FK is nullable
        assert len(spec.errors) == 0
        # May have info or warning about nullable FK, but not an error
        assert len(spec.errors) == 0

    def test_non_nullable_column_has_value_for_existing_records(self):
        """Test that non-nullable validation only applies to new records."""
        schema = build_schema(
            [
                build_table(
                    "tbl_test",
                    "test_id",
                    columns={
                        "test_id": build_column("tbl_test", "test_id", is_pk=True),
                        "required_col": build_column("tbl_test", "required_col", is_nullable=False),
                        "system_id": build_column("tbl_test", "system_id"),
                    },
                )
            ]
        )

        # Existing record (pk > 0) can have NULL in non-nullable column (will be loaded from DB)
        data = pd.DataFrame(
            {
                "system_id": [1],
                "test_id": [42],  # Existing record
                "required_col": [None],  # NULL in non-nullable column
            }
        )
        submission = Submission(data_tables={"tbl_test": data}, schema=schema)

        spec = NonNullableColumnHasValueSpecification(schema=schema)
        spec.is_satisfied_by(submission, table_name="tbl_test")

        # Should pass because it's an existing record
        assert len(spec.errors) == 0

    def test_non_nullable_column_missing_in_new_records(self):
        """Test that new records must have non-nullable columns."""
        schema = build_schema(
            [
                build_table(
                    "tbl_test",
                    "test_id",
                    columns={
                        "test_id": build_column("tbl_test", "test_id", is_pk=True),
                        "required_col": build_column("tbl_test", "required_col", is_nullable=False),
                        "system_id": build_column("tbl_test", "system_id"),
                    },
                )
            ]
        )

        data = pd.DataFrame({"system_id": [1], "test_id": [None], "required_col": [None]})  # New record  # NULL in non-nullable column
        submission = Submission(data_tables={"tbl_test": data}, schema=schema)

        spec = NonNullableColumnHasValueSpecification(schema=schema)
        spec.is_satisfied_by(submission, table_name="tbl_test")

        assert len(spec.errors) > 0
        assert any("null" in err.lower() for err in spec.errors)

    def test_column_types_with_compatible_types(self):
        """Test that type compatibility matrix works correctly."""
        schema = build_schema(
            [
                build_table(
                    "tbl_test",
                    "test_id",
                    columns={
                        "test_id": build_column("tbl_test", "test_id", is_pk=True, data_type="integer"),
                        "system_id": build_column("tbl_test", "system_id", data_type="integer"),
                    },
                )
            ]
        )

        # integer in schema matches int64 in pandas
        data = pd.DataFrame({"system_id": pd.Series([1], dtype="int64"), "test_id": pd.Series([1], dtype="int64")})
        submission = Submission(data_tables={"tbl_test": data}, schema=schema)

        spec = ColumnTypesSpecification(schema=schema)
        spec.is_satisfied_by(submission, table_name="tbl_test")

        # Should have no warnings for compatible types
        assert len([w for w in spec.warnings if "type clash" in w]) == 0

    def test_foreign_key_exists_with_missing_target_table(self):
        """Test FK validation when target table is missing."""
        schema = build_schema(
            [
                build_table(
                    "tbl_main",
                    "main_id",
                    columns={
                        "main_id": build_column("tbl_main", "main_id", is_pk=True),
                        "lookup_id": build_column("tbl_main", "lookup_id", is_fk=True, is_nullable=False, fk_table_name="tbl_lookup"),
                        "system_id": build_column("tbl_main", "system_id"),
                    },
                ),
                build_table("tbl_lookup", "lookup_id", is_lookup=True),
            ]
        )

        # Main table references lookup, but lookup table is missing from submission
        data = pd.DataFrame({"system_id": [1], "main_id": [None], "lookup_id": [100]})
        submission = Submission(data_tables={"tbl_main": data}, schema=schema)

        spec = ForeignKeyExistsAsPrimaryKeySpecification(schema=schema)
        spec.is_satisfied_by(submission, table_name="tbl_main")

        assert len(spec.errors) > 0
        assert any("missing in data" in err.lower() for err in spec.errors)

    def test_specification_messages_merge(self):
        """Test that specification messages can be merged."""
        spec1 = HasSystemIdSpecification(build_schema())
        spec1.error("Error 1")
        spec1.warn("Warning 1")

        spec2 = HasPrimaryKeySpecification(build_schema())
        spec2.error("Error 2")
        spec2.info("Info 1")

        spec1.merge(spec2)

        assert "Error 1" in spec1.errors
        assert "Error 2" in spec1.errors
        assert "Warning 1" in spec1.warnings
        assert "Info 1" in spec1.infos

    def test_specification_error_with_messages_object(self):
        """Test SpecificationError can be created with SpecificationMessages."""
        schema = build_schema([build_table("tbl_test", "test_id")])

        spec = SubmissionSpecification(schema=schema, raise_errors=True)
        spec.error("Test error")

        with pytest.raises(SpecificationError) as exc_info:
            if spec.has_errors():
                raise SpecificationError(spec.messages)

        assert "Test error" in str(exc_info.value.messages)

    def test_specification_error_with_string(self):
        """Test SpecificationError can be created with a string message."""
        with pytest.raises(SpecificationError) as exc_info:
            raise SpecificationError("Simple error message")

        assert len(exc_info.value.messages.errors) == 1
        assert "Simple error message" in exc_info.value.messages.errors[0]
