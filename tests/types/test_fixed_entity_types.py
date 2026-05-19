"""Unit tests for fixed entity type coercion.

Tests the strict policy matrix, edge cases, and error handling.
"""

import pandas as pd
import pytest

from src.types.fixed_entity_types import (
    FixedEntityColumnTypeDeclarationError,
    FixedEntityNormalizationWarning,
    FixedEntityShapeValidationError,
    FixedEntityTypeCoercer,
    FixedEntityTypeValidationError,
    format_fixed_entity_normalization_warning,
    infer_fixed_entity_column_type,
)


class TestInferColumnType:
    """Test column type inference from naming convention."""

    def test_id_suffix_inferred_as_int(self) -> None:
        """Columns ending with _id should infer to int."""
        assert infer_fixed_entity_column_type("method_id") is int
        assert infer_fixed_entity_column_type("sample_id") is int
        assert infer_fixed_entity_column_type("system_id") is int
        assert infer_fixed_entity_column_type("sead_method_group_id") is int

    def test_non_id_suffix_inferred_as_string(self) -> None:
        """Columns not ending with _id should infer to string."""
        assert infer_fixed_entity_column_type("method_name") is str
        assert infer_fixed_entity_column_type("description") is str
        assert infer_fixed_entity_column_type("name") is str


class TestCoerceValue:
    """Test strict coercion policy matrix for individual values."""

    def test_integer_type_coercion_policy(self) -> None:
        """Test coercion rules for integer target type."""
        # None → None
        assert FixedEntityTypeCoercer.coerce_value(None, int) == (None, None)

        # Empty string → None
        assert FixedEntityTypeCoercer.coerce_value("", int) == (None, None)
        assert FixedEntityTypeCoercer.coerce_value("  ", int) == (None, None)

        # Integer → Integer (no error)
        assert FixedEntityTypeCoercer.coerce_value(53, int) == (53, None)
        assert FixedEntityTypeCoercer.coerce_value(0, int) == (0, None)
        assert FixedEntityTypeCoercer.coerce_value(-42, int) == (-42, None)

        # String integer → Integer with no error (normalization)
        assert FixedEntityTypeCoercer.coerce_value("53", int) == (53, None)
        assert FixedEntityTypeCoercer.coerce_value("0", int) == (0, None)
        assert FixedEntityTypeCoercer.coerce_value("-42", int) == (-42, None)

        # Float (type) → Error
        result, error = FixedEntityTypeCoercer.coerce_value(53.0, int)
        assert error == "invalid_integer_float_not_allowed"

        # String float → Error (reject float-like strings)
        result, error = FixedEntityTypeCoercer.coerce_value("53.0", int)
        assert error == "invalid_integer_float_format"

        # Invalid integer string → Error
        result, error = FixedEntityTypeCoercer.coerce_value("abc", int)
        assert error == "invalid_integer_format"

        result, error = FixedEntityTypeCoercer.coerce_value("53abc", int)
        assert error == "invalid_integer_format"

        # Boolean → Error (never treat bool as int)
        result, error = FixedEntityTypeCoercer.coerce_value(True, int)
        assert error == "invalid_integer_bool_not_allowed"

        result, error = FixedEntityTypeCoercer.coerce_value(False, int)
        assert error == "invalid_integer_bool_not_allowed"

    def test_string_type_coercion_policy(self) -> None:
        """Test coercion rules for string target type."""
        # Everything becomes string
        assert FixedEntityTypeCoercer.coerce_value("hello", str) == ("hello", None)
        assert FixedEntityTypeCoercer.coerce_value(53, str) == ("53", None)
        assert FixedEntityTypeCoercer.coerce_value(None, str) == (None, None)
        assert FixedEntityTypeCoercer.coerce_value("", str) == (None, None)

    def test_pandas_null_like_values_normalize_to_none(self) -> None:
        """Pandas scalar nulls should be treated as missing values, not typed payloads."""
        assert FixedEntityTypeCoercer.coerce_value(float("nan"), int) == (None, None)
        assert FixedEntityTypeCoercer.coerce_value(pd.NA, "string") == (None, None)
        coerced_value, error = FixedEntityTypeCoercer.coerce_value(pd.NaT, "date")
        assert (coerced_value, error) == (None, None)


class TestCoerceFixedEntityValues:
    """Test full coercion pipeline with shape and type validation."""

    def test_shape_validation_is_hard_gate(self) -> None:
        """Shape validation should reject before type coercion."""
        entity_data = {
            "values": [
                [1, 105],  # Wrong: only 2 values
            ]
        }
        columns = ["system_id", "method_id", "name"]

        with pytest.raises(FixedEntityShapeValidationError) as exc:
            FixedEntityTypeCoercer.coerce_fixed_entity_values(
                entity_data, columns, "test_entity"
            )

        assert "row 0 has 2 values; expected 3" in str(exc.value)

    def test_simple_coercion_all_integers(self) -> None:
        """Coerce all-integer fixed entity."""
        entity_data = {
            "values": [
                [1, 105, "name1"],
                [2, 76, "name2"],
            ]
        }
        columns = ["system_id", "method_id", "name"]

        result = FixedEntityTypeCoercer.coerce_fixed_entity_values(
            entity_data, columns, "method"
        )

        assert result == entity_data["values"]

    def test_string_integer_coercion(self) -> None:
        """Coerce string integers to integers (normalization)."""
        entity_data = {
            "values": [
                [1, "105", "name1"],
                [2, "76", "name2"],
            ]
        }
        columns = ["system_id", "method_id", "name"]

        result = FixedEntityTypeCoercer.coerce_fixed_entity_values(
            entity_data, columns, "method"
        )

        # String integers should be coerced to int
        assert result[0][1] == 105
        assert result[1][1] == 76
        assert result[0][2] == "name1"
        assert result[1][2] == "name2"

    def test_mixed_null_and_valid_integers(self) -> None:
        """Coerce mixed null and valid integer values."""
        entity_data = {
            "values": [
                [1, 105, "name1"],
                [2, None, "name2"],
                [3, "", "name3"],  # Empty string becomes None
            ]
        }
        columns = ["system_id", "method_id", "name"]

        result = FixedEntityTypeCoercer.coerce_fixed_entity_values(
            entity_data, columns, "method"
        )

        assert result[1][1] is None
        assert result[2][1] is None

    def test_invalid_string_integer_raises_error(self) -> None:
        """Reject invalid integer string."""
        entity_data = {
            "values": [
                [1, "105", "name1"],
                [2, "abc", "name2"],  # Invalid
            ]
        }
        columns = ["system_id", "method_id", "name"]

        with pytest.raises(FixedEntityTypeValidationError) as exc:
            FixedEntityTypeCoercer.coerce_fixed_entity_values(
                entity_data, columns, "method"
            )

        assert len(exc.value.issues) == 1
        issue = exc.value.issues[0]
        assert issue.row_index == 1
        assert issue.column_index == 1
        assert issue.column_name == "method_id"
        assert issue.raw_value == "abc"
        assert issue.reason == "invalid_integer_format"

    def test_invalid_float_string_raises_error(self) -> None:
        """Reject float-like strings."""
        entity_data = {
            "values": [
                [1, "53.9", "name1"],
            ]
        }
        columns = ["system_id", "method_id", "name"]

        with pytest.raises(FixedEntityTypeValidationError) as exc:
            FixedEntityTypeCoercer.coerce_fixed_entity_values(
                entity_data, columns, "method"
            )

        assert len(exc.value.issues) == 1
        issue = exc.value.issues[0]
        assert issue.reason == "invalid_integer_float_format"

    def test_boolean_in_id_column_raises_error(self) -> None:
        """Reject boolean values in _id columns."""
        entity_data = {
            "values": [
                [1, True, "name1"],
            ]
        }
        columns = ["system_id", "method_id", "name"]

        with pytest.raises(FixedEntityTypeValidationError) as exc:
            FixedEntityTypeCoercer.coerce_fixed_entity_values(
                entity_data, columns, "method"
            )

        assert len(exc.value.issues) == 1
        issue = exc.value.issues[0]
        assert issue.reason == "invalid_integer_bool_not_allowed"

    def test_multiple_errors_collected(self) -> None:
        """Collect all errors before raising."""
        entity_data = {
            "values": [
                [1, "abc", "name1"],
                [2, "105", "name2"],  # Valid
                [3, True, "name3"],  # Invalid bool
            ]
        }
        columns = ["system_id", "method_id", "name"]

        with pytest.raises(FixedEntityTypeValidationError) as exc:
            FixedEntityTypeCoercer.coerce_fixed_entity_values(
                entity_data, columns, "method"
            )

        # Both row 0 and row 2 should have issues
        assert len(exc.value.issues) == 2
        assert exc.value.issues[0].row_index == 0
        assert exc.value.issues[1].row_index == 2

    def test_empty_values_returns_empty_list(self) -> None:
        """Empty or missing values should return empty list."""
        assert (
            FixedEntityTypeCoercer.coerce_fixed_entity_values(
                {"values": None}, ["col1"], "test"
            )
            == []
        )
        assert (
            FixedEntityTypeCoercer.coerce_fixed_entity_values(
                {"values": []}, ["col1"], "test"
            )
            == []
        )

    def test_multicolumn_mixed_types(self) -> None:
        """Test coercion with multiple _id and non-_id columns."""
        entity_data = {
            "values": [
                [1, "105", "method_name", "17"],
                [2, 76, "other_method", None],
            ]
        }
        columns = [
            "system_id",
            "method_id",
            "description",
            "sead_method_group_id",
        ]

        result = FixedEntityTypeCoercer.coerce_fixed_entity_values(
            entity_data, columns, "method"
        )

        # First row: strings coerced to int for _id columns
        assert result[0] == [1, 105, "method_name", 17]
        # Second row: integers stay as is, None stays as None
        assert result[1] == [2, 76, "other_method", None]

    def test_real_world_arbodat_scenario(self) -> None:
        """Reproduce the arbodat mixed-type issue with successful coercion."""
        entity_data = {
            "values": [
                [9, 105, "Sampling"],
                [10, 76, "Collecting"],
                [11, "53", "Processing"],  # String integer gets coerced
            ]
        }
        columns = ["system_id", "method_id", "name"]

        # With the coercer, string integers are normalized successfully
        result = FixedEntityTypeCoercer.coerce_fixed_entity_values(
            entity_data, columns, "method"
        )

        # All method_id values are now integers (including the string "53")
        assert result[0][1] == 105
        assert result[1][1] == 76
        assert result[2][1] == 53  # String was coerced to int
        assert all(isinstance(row[1], int) for row in result)

    def test_negative_integers(self) -> None:
        """Handle negative integers in ID columns (edge case)."""
        entity_data = {
            "values": [
                [1, "-105", "method1"],
                [2, -76, "method2"],
            ]
        }
        columns = ["system_id", "method_id", "name"]

        result = FixedEntityTypeCoercer.coerce_fixed_entity_values(
            entity_data, columns, "method"
        )

        assert result[0][1] == -105
        assert result[1][1] == -76

    def test_zero_integer(self) -> None:
        """Handle zero as valid integer."""
        entity_data = {
            "values": [
                [1, 0, "method1"],
                [2, "0", "method2"],
            ]
        }
        columns = ["system_id", "method_id", "name"]

        result = FixedEntityTypeCoercer.coerce_fixed_entity_values(
            entity_data, columns, "method"
        )

        assert result[0][1] == 0
        assert result[1][1] == 0

    def test_declared_column_type_overrides_inference(self) -> None:
        """Declared column_types should coerce non-_id columns using explicit types."""
        entity_data = {
            "column_types": {"rank": "int"},
            "values": [
                [1, "7", "Sampling"],
            ],
        }
        columns = ["system_id", "rank", "name"]

        result = FixedEntityTypeCoercer.coerce_fixed_entity_values(
            entity_data, columns, "method"
        )

        assert result == [[1, 7, "Sampling"]]

    def test_undeclared_non_id_values_preserve_scalar_types(self) -> None:
        """Undeclared non-_id columns should keep their incoming scalar types."""
        entity_data = {
            "values": [
                [1, "Oak", 12],
                [2, "Pine", 8],
            ],
        }
        columns = ["system_id", "taxon_name", "abundance"]

        result = FixedEntityTypeCoercer.coerce_fixed_entity_values(
            entity_data, columns, "abundance_source"
        )

        assert result == [[1, "Oak", 12], [2, "Pine", 8]]

    def test_declared_date_and_bool_types_are_coerced(self) -> None:
        """Declared bool/date column types should normalize compatible string inputs."""
        entity_data = {
            "column_types": {"is_active": "bool", "created_at": "date"},
            "values": [[1, "true", "2026-05-19"]],
        }
        columns = ["system_id", "is_active", "created_at"]

        result = FixedEntityTypeCoercer.coerce_fixed_entity_values(
            entity_data, columns, "method"
        )

        assert result == [[1, True, "2026-05-19"]]

    def test_invalid_declared_column_type_raises_error(self) -> None:
        """Unsupported declared fixed-entity types should fail fast."""
        entity_data = {
            "column_types": {"rank": "integer"},
            "values": [[1, "7", "Sampling"]],
        }
        columns = ["system_id", "rank", "name"]

        with pytest.raises(FixedEntityColumnTypeDeclarationError) as exc:
            FixedEntityTypeCoercer.coerce_fixed_entity_values(
                entity_data, columns, "method"
            )

        assert "unsupported type 'integer'" in str(exc.value)

    def test_collects_successful_normalization_warnings(self) -> None:
        """Successful coercions should be reported as normalization warnings."""
        entity_data = {
            "values": [[1, "53", "Sampling"]],
        }
        columns = ["system_id", "method_id", "name"]

        result, warnings = FixedEntityTypeCoercer.coerce_fixed_entity_values_with_warnings(
            entity_data,
            columns,
            "method",
        )

        assert result == [[1, 53, "Sampling"]]
        assert warnings == [
            FixedEntityNormalizationWarning(
                entity_name="method",
                row_index=0,
                column_index=1,
                column_name="method_id",
                raw_value="53",
                normalized_value=53,
                expected_type="int",
            )
        ]
        assert format_fixed_entity_normalization_warning(warnings[0]) == (
            "Entity 'method', row 1, column 'method_id': normalized '53' to 53 (int)"
        )
