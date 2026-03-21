"""Integration tests for DSL formulas in extra_columns.

Tests the integration between the DSL parser (src/transforms/dsl.py)
and the ExtraColumnEvaluator (src/transforms/extra_columns.py).

Tests verify:
1. DSL formulas are evaluated correctly
2. Deferred evaluation works for missing columns
3. DSL works alongside interpolation and constants
4. Error handling with meaningful messages
5. Processing order (constants → DSL → interpolation → column copy → string)
"""

import pandas as pd
import pytest

from src.transforms.extra_columns import ExtraColumnEvaluator


class TestDSLIntegration:
    """Test DSL formula integration with extra_columns."""

    @pytest.fixture
    def evaluator(self):
        """Create evaluator instance."""
        return ExtraColumnEvaluator()

    @pytest.fixture
    def sample_df(self):
        """Sample DataFrame for testing."""
        return pd.DataFrame(
            {
                "first": ["John", "Jane", "Bob"],
                "last": ["Doe", "Smith", "Johnson"],
                "age": [30, 25, 35],
                "city": ["New York", "Los Angeles", "Chicago"],
            }
        )

    def test_basic_dsl_formula(self, evaluator, sample_df):
        """Test basic DSL formula evaluation."""
        extra_cols = {"initials": "=concat(substr(first, 0, 1), substr(last, 0, 1))"}

        result, deferred = evaluator.evaluate_extra_columns(sample_df, extra_cols, "test")

        assert "initials" in result.columns
        assert list(result["initials"]) == ["JD", "JS", "BJ"]
        assert len(deferred) == 0

    def test_dsl_with_string_functions(self, evaluator, sample_df):
        """Test DSL with string manipulation functions."""
        extra_cols = {
            "upper_first": "=upper(first)",
            "lower_city": "=lower(city)",
            "trimmed": "=trim(first)",
            "initials": "=concat(upper(substr(first, 0, 1)), upper(substr(last, 0, 1)))",
        }

        result, deferred = evaluator.evaluate_extra_columns(sample_df, extra_cols, "test")

        assert list(result["upper_first"]) == ["JOHN", "JANE", "BOB"]
        assert list(result["lower_city"]) == ["new york", "los angeles", "chicago"]
        assert list(result["trimmed"]) == ["John", "Jane", "Bob"]
        assert list(result["initials"]) == ["JD", "JS", "BJ"]

    def test_dsl_with_coalesce(self, evaluator):
        """Test DSL with coalesce function handling nulls."""
        df = pd.DataFrame(
            {
                "first": ["John", None, "Bob"],
                "middle": [None, "Marie", None],
                "last": ["Doe", "Smith", "Johnson"],
            }
        )

        extra_cols = {"display": '=coalesce(first, middle, "Unknown")'}

        result, deferred = evaluator.evaluate_extra_columns(df, extra_cols, "test")

        assert list(result["display"]) == ["John", "Marie", "Bob"]

    def test_dsl_with_numeric_conversion(self, evaluator, sample_df):
        """Test DSL with numeric to string conversion."""
        extra_cols = {
            "age_formatted": '=concat("Age: ", age)',
            "location_info": '=concat(city, " (", age, " years old)")',
        }

        result, deferred = evaluator.evaluate_extra_columns(sample_df, extra_cols, "test")

        assert list(result["age_formatted"]) == ["Age: 30", "Age: 25", "Age: 35"]
        assert list(result["location_info"]) == [
            "New York (30 years old)",
            "Los Angeles (25 years old)",
            "Chicago (35 years old)",
        ]

    def test_dsl_deferred_evaluation(self, evaluator, sample_df):
        """Test DSL formulas are deferred when columns missing."""
        extra_cols = {
            "display": '=concat(first, " ", middle, " ", last)',  # middle doesn't exist
            "valid": "=upper(first)",  # All columns exist
        }

        result, deferred = evaluator.evaluate_extra_columns(sample_df, extra_cols, "test", defer_missing=True)

        # Valid formula evaluated
        assert "valid" in result.columns
        assert list(result["valid"]) == ["JOHN", "JANE", "BOB"]

        # Invalid formula deferred
        assert "display" not in result.columns
        assert "display" in deferred
        assert deferred["display"] == '=concat(first, " ", middle, " ", last)'

    def test_dsl_with_interpolation(self, evaluator, sample_df):
        """Test DSL works alongside interpolation."""
        extra_cols = {
            "dsl_full": "=concat(first, ' ', last)",
            "interp_full": "{first} {last}",
            "dsl_upper": "=upper(first)",
        }

        result, deferred = evaluator.evaluate_extra_columns(sample_df, extra_cols, "test")

        # Both DSL and interpolation work
        assert list(result["dsl_full"]) == ["John Doe", "Jane Smith", "Bob Johnson"]
        assert list(result["interp_full"]) == ["John Doe", "Jane Smith", "Bob Johnson"]
        assert list(result["dsl_upper"]) == ["JOHN", "JANE", "BOB"]

    def test_dsl_with_constants(self, evaluator, sample_df):
        """Test DSL works alongside constants."""
        extra_cols = {
            "country": "US",  # String constant
            "prefix": "Mr.",  # String constant
            "formatted": '=concat(prefix, " ", first, " ", last)',  # DSL using constant
        }

        result, deferred = evaluator.evaluate_extra_columns(sample_df, extra_cols, "test")

        assert all(result["country"] == "US")
        assert all(result["prefix"] == "Mr.")
        assert list(result["formatted"]) == ["Mr. John Doe", "Mr. Jane Smith", "Mr. Bob Johnson"]

    def test_processing_order(self, evaluator, sample_df):
        """Test processing order: constants → DSL → interpolation → column copy → string."""
        extra_cols = {
            "step1_const": "CONSTANT",
            "step2_dsl": "=upper(first)",
            "step3_interp": "{step2_dsl}_{last}",  # Uses DSL result
            "step4_copy": "first",  # Column copy
            "step5_string": "final",
        }

        result, deferred = evaluator.evaluate_extra_columns(sample_df, extra_cols, "test")

        # Constants processed first
        assert all(result["step1_const"] == "CONSTANT")

        # DSL processed second
        assert list(result["step2_dsl"]) == ["JOHN", "JANE", "BOB"]

        # Interpolation processed third (can use DSL results)
        assert list(result["step3_interp"]) == ["JOHN_Doe", "JANE_Smith", "BOB_Johnson"]

        # Column copy processed fourth
        assert list(result["step4_copy"]) == list(sample_df["first"])

        # String constant processed last
        assert all(result["step5_string"] == "final")

    def test_dsl_error_handling(self, evaluator, sample_df):
        """Test DSL error handling with meaningful messages."""
        extra_cols = {"invalid": "=unknown_func(first)"}  # Invalid function

        with pytest.raises(ValueError) as exc_info:
            evaluator.evaluate_extra_columns(sample_df, extra_cols, "test")

        error_msg = str(exc_info.value)
        assert "Error evaluating formula" in error_msg
        assert "invalid" in error_msg
        assert "test" in error_msg
        assert "unknown_func" in error_msg

    def test_dsl_missing_columns_error(self, evaluator, sample_df):
        """Test DSL error when missing columns without defer."""
        extra_cols = {"display": "=concat(first, middle, last)"}  # middle doesn't exist

        with pytest.raises(ValueError) as exc_info:
            evaluator.evaluate_extra_columns(sample_df, extra_cols, "test", defer_missing=False)

        error_msg = str(exc_info.value)
        assert "Error evaluating formula" in error_msg
        assert "display" in error_msg
        assert "middle" in error_msg

    def test_complex_combined_scenario(self, evaluator, sample_df):
        """Test complex scenario with all feature types."""
        extra_cols = {
            # Constants
            "country": "US",
            "department": "Sales",
            # DSL formulas
            "initials": "=concat(upper(substr(first, 0, 1)), upper(substr(last, 0, 1)))",
            "title": "=concat(upper(substr(first, 0, 1)), lower(substr(first, 1, 999)))",
            "location_upper": "=upper(city)",
            # Interpolation (can use DSL results)
            "display_name": "{title} {last}",
            "badge_id": "{initials}_{department}_{country}",
            # Column copy
            "original_name": "first",
            # String constant
            "status": "active",
        }

        result, deferred = evaluator.evaluate_extra_columns(sample_df, extra_cols, "test")

        # Verify all columns added
        expected_cols = set(extra_cols.keys())
        actual_cols = set(c for c in result.columns if c not in sample_df.columns)
        assert actual_cols == expected_cols

        # Spot check values
        assert list(result["initials"]) == ["JD", "JS", "BJ"]
        assert list(result["title"]) == ["John", "Jane", "Bob"]
        assert list(result["display_name"]) == ["John Doe", "Jane Smith", "Bob Johnson"]
        assert list(result["badge_id"]) == ["JD_Sales_US", "JS_Sales_US", "BJ_Sales_US"]

    def test_dsl_formula_detection(self, evaluator):
        """Test is_dsl_formula() detection."""
        assert evaluator.is_dsl_formula("=concat(first, last)")
        assert evaluator.is_dsl_formula("=upper(name)")
        assert evaluator.is_dsl_formula("= trim(value)")  # Space after =

        assert not evaluator.is_dsl_formula("const_value")
        assert not evaluator.is_dsl_formula("{first} {last}")
        assert not evaluator.is_dsl_formula("column_name")
        assert not evaluator.is_dsl_formula("")
        assert not evaluator.is_dsl_formula("equals = value")  # = not at start

    def test_empty_extra_columns(self, evaluator, sample_df):
        """Test with empty extra_columns dict."""
        result, deferred = evaluator.evaluate_extra_columns(sample_df, {}, "test")

        assert result.equals(sample_df)
        assert len(deferred) == 0

    def test_dsl_with_nested_function_calls(self, evaluator, sample_df):
        """Test DSL with deeply nested function calls."""
        extra_cols = {
            "nested": "=upper(trim(concat(substr(first, 0, 1), substr(last, 0, 1))))",
        }

        result, deferred = evaluator.evaluate_extra_columns(sample_df, extra_cols, "test")

        assert list(result["nested"]) == ["JD", "JS", "BJ"]

    def test_dsl_with_null_handling(self, evaluator):
        """Test DSL handles null values correctly."""
        df = pd.DataFrame(
            {
                "first": ["John", None, "Bob"],
                "last": ["Doe", "Smith", None],
            }
        )

        extra_cols = {
            "safe": '=coalesce(first, "N/A")',
            "concat_with_null": "=concat(first, last)",  # May produce NaN or empty
        }

        result, deferred = evaluator.evaluate_extra_columns(df, extra_cols, "test")

        # Coalesce handles nulls
        assert result["safe"].iloc[0] == "John"
        assert result["safe"].iloc[1] == "N/A"
        assert result["safe"].iloc[2] == "Bob"


class TestDSLIntegrationEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.fixture
    def evaluator(self):
        return ExtraColumnEvaluator()

    def test_dsl_with_special_characters_in_strings(self, evaluator):
        """Test DSL with special characters in string literals."""
        df = pd.DataFrame({"name": ["Alice", "Bob"]})

        extra_cols = {
            "quoted": '=concat(name, "\\"s profile")',  # Escaped quotes
            "newline": '=concat(name, "\\n(new)")',  # Newline
        }

        result, deferred = evaluator.evaluate_extra_columns(df, extra_cols, "test")

        assert list(result["quoted"]) == ['Alice"s profile', 'Bob"s profile']
        # Note: actual newline handling depends on DSL implementation

    def test_dsl_with_empty_dataframe(self, evaluator):
        """Test DSL with empty DataFrame."""
        df = pd.DataFrame({"name": []})

        extra_cols = {"upper_name": "=upper(name)"}

        result, deferred = evaluator.evaluate_extra_columns(df, extra_cols, "test")

        assert len(result) == 0
        assert "upper_name" in result.columns

    def test_dsl_case_sensitivity(self, evaluator):
        """Test DSL is case-sensitive for column names."""
        df = pd.DataFrame({"Name": ["Alice"], "name": ["Bob"]})

        extra_cols = {
            "upper_Name": "=upper(Name)",  # Capital N
            "upper_name": "=upper(name)",  # Lowercase n
        }

        result, deferred = evaluator.evaluate_extra_columns(df, extra_cols, "test")

        assert result["upper_Name"].iloc[0] == "ALICE"
        assert result["upper_name"].iloc[0] == "BOB"
