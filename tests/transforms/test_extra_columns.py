"""
Tests for extra_columns evaluation with interpolated string support.
"""

import pandas as pd
import pytest

from src.transforms.extra_columns import ExtraColumnEvaluator


class TestInterpolationDetection:
    """Test is_interpolated_string() pattern detection."""

    def test_detects_simple_interpolation(self):
        """Single column interpolation is detected."""
        assert ExtraColumnEvaluator.is_interpolated_string("{col}")

    def test_detects_multiple_interpolations(self):
        """Multiple column interpolations are detected."""
        assert ExtraColumnEvaluator.is_interpolated_string("{first} {last}")

    def test_detects_interpolation_with_text(self):
        """Interpolation mixed with literal text is detected."""
        assert ExtraColumnEvaluator.is_interpolated_string("Name: {name}")

    def test_escaped_braces_not_detected(self):
        """Escaped braces {{}} are not detected as interpolation."""
        assert not ExtraColumnEvaluator.is_interpolated_string("{{literal}}")

    def test_constant_string_not_detected(self):
        """Plain string constant is not detected as interpolation."""
        assert not ExtraColumnEvaluator.is_interpolated_string("constant")

    def test_non_string_not_detected(self):
        """Non-string values are not detected as interpolation."""
        assert not ExtraColumnEvaluator.is_interpolated_string(123)
        assert not ExtraColumnEvaluator.is_interpolated_string(None)
        assert not ExtraColumnEvaluator.is_interpolated_string([])

    def test_empty_braces_not_detected(self):
        """Empty braces {} are not valid interpolation."""
        assert not ExtraColumnEvaluator.is_interpolated_string("{}")

    def test_invalid_column_name_not_detected(self):
        """Invalid column names (starting with number) are not detected."""
        assert not ExtraColumnEvaluator.is_interpolated_string("{123invalid}")


class TestDependencyExtraction:
    """Test extract_column_dependencies() column name extraction."""

    def test_extracts_single_column(self):
        """Single column dependency is extracted."""
        result = ExtraColumnEvaluator.extract_column_dependencies("{col}")
        assert result == ["col"]

    def test_extracts_multiple_columns(self):
        """Multiple column dependencies are extracted."""
        result = ExtraColumnEvaluator.extract_column_dependencies("{first} {last}")
        assert result == ["first", "last"]

    def test_preserves_order(self):
        """Column order is preserved."""
        result = ExtraColumnEvaluator.extract_column_dependencies("{z} {a} {m}")
        assert result == ["z", "a", "m"]

    def test_removes_duplicates(self):
        """Duplicate columns appear only once."""
        result = ExtraColumnEvaluator.extract_column_dependencies("{a} {b} {a}")
        assert result == ["a", "b"]

    def test_handles_underscores(self):
        """Column names with underscores are extracted."""
        result = ExtraColumnEvaluator.extract_column_dependencies("{first_name} {last_name}")
        assert result == ["first_name", "last_name"]

    def test_handles_numbers(self):
        """Column names with numbers (not at start) are extracted."""
        result = ExtraColumnEvaluator.extract_column_dependencies("{col1} {col2}")
        assert result == ["col1", "col2"]

    def test_ignores_escaped_braces(self):
        """Escaped braces {{}} are ignored."""
        result = ExtraColumnEvaluator.extract_column_dependencies("{{literal}} {real}")
        assert result == ["real"]

    def test_empty_pattern(self):
        """Pattern with no columns returns empty list."""
        result = ExtraColumnEvaluator.extract_column_dependencies("no columns here")
        assert result == []


class TestBraceEscaping:
    """Test unescape_braces() functionality."""

    def test_unescapes_double_braces(self):
        """Double braces are unescaped to single braces."""
        result = ExtraColumnEvaluator.unescape_braces("{{literal}}")
        assert result == "{literal}"

    def test_unescapes_multiple(self):
        """Multiple escaped braces are all unescaped."""
        result = ExtraColumnEvaluator.unescape_braces("{{a}} and {{b}}")
        assert result == "{a} and {b}"

    def test_leaves_single_braces(self):
        """Single braces are left unchanged."""
        result = ExtraColumnEvaluator.unescape_braces("{normal}")
        assert result == "{normal}"

    def test_mixed_escaped_and_normal(self):
        """Mixed escaped and normal braces are handled correctly."""
        result = ExtraColumnEvaluator.unescape_braces("{{escaped}} {normal}")
        assert result == "{escaped} {normal}"


class TestInterpolationEvaluation:
    """Test evaluate_interpolation() actual interpolation."""

    def test_simple_interpolation(self):
        """Simple two-column interpolation works."""
        df = pd.DataFrame({"first": ["John"], "last": ["Doe"]})
        result = ExtraColumnEvaluator.evaluate_interpolation(df, "{first} {last}", "test")
        assert result.iloc[0] == "John Doe"

    def test_interpolation_with_nulls(self):
        """Null values are converted to empty strings."""
        df = pd.DataFrame({"a": [1, None, 3], "b": ["x", "y", None]})
        result = ExtraColumnEvaluator.evaluate_interpolation(df, "{a}-{b}", "test")
        assert result.tolist() == ["1-x", "-y", "3-"]

    def test_interpolation_with_numbers(self):
        """Numeric values are converted to strings."""
        df = pd.DataFrame({"num": [1, 2, 3], "text": ["a", "b", "c"]})
        result = ExtraColumnEvaluator.evaluate_interpolation(df, "{num}:{text}", "test")
        assert result.tolist() == ["1:a", "2:b", "3:c"]

    def test_interpolation_with_literal_text(self):
        """Literal text is preserved."""
        df = pd.DataFrame({"name": ["John"]})
        result = ExtraColumnEvaluator.evaluate_interpolation(df, "Hello, {name}!", "test")
        assert result.iloc[0] == "Hello, John!"

    def test_interpolation_with_escaping(self):
        """Escaped braces are unescaped after interpolation."""
        df = pd.DataFrame({"name": ["John"]})
        result = ExtraColumnEvaluator.evaluate_interpolation(df, "{{name}}: {name}", "test")
        assert result.iloc[0] == "{name}: John"

    def test_raises_on_missing_column(self):
        """ValueError raised if required column missing."""
        df = pd.DataFrame({"a": [1]})
        with pytest.raises(ValueError, match="columns not found"):
            ExtraColumnEvaluator.evaluate_interpolation(df, "{a} {missing}", "test")

    def test_error_message_includes_entity_name(self):
        """Error message includes entity name for context."""
        df = pd.DataFrame({"a": [1]})
        with pytest.raises(ValueError, match="for entity 'person'"):
            ExtraColumnEvaluator.evaluate_interpolation(df, "{missing}", "person")

    def test_multiple_rows(self):
        """Interpolation works correctly for multiple rows."""
        df = pd.DataFrame({"first": ["John", "Jane", "Bob"], "last": ["Doe", "Smith", "Jones"]})
        result = ExtraColumnEvaluator.evaluate_interpolation(df, "{first} {last}", "test")
        assert result.tolist() == ["John Doe", "Jane Smith", "Bob Jones"]

    def test_same_column_multiple_times(self):
        """Same column can be referenced multiple times."""
        df = pd.DataFrame({"val": [5]})
        result = ExtraColumnEvaluator.evaluate_interpolation(df, "{val} + {val}", "test")
        assert result.iloc[0] == "5 + 5"


class TestExtraColumnsEvaluation:
    """Test evaluate_extra_columns() full evaluation logic."""

    def test_constant_numeric(self):
        """Numeric constant is added."""
        evaluator = ExtraColumnEvaluator()
        df = pd.DataFrame({"a": [1, 2]})
        result, deferred = evaluator.evaluate_extra_columns(df, {"const": 99}, "test")

        assert "const" in result.columns
        assert result["const"].tolist() == [99, 99]
        assert len(deferred) == 0

    def test_constant_string(self):
        """String constant (not matching column) is added."""
        evaluator = ExtraColumnEvaluator()
        df = pd.DataFrame({"a": [1, 2]})
        result, deferred = evaluator.evaluate_extra_columns(df, {"const": "literal"}, "test")

        assert "const" in result.columns
        assert result["const"].tolist() == ["literal", "literal"]
        assert len(deferred) == 0

    def test_column_copy(self):
        """Column copy is created."""
        evaluator = ExtraColumnEvaluator()
        df = pd.DataFrame({"source": [10, 20]})
        result, deferred = evaluator.evaluate_extra_columns(df, {"copy": "source"}, "test")

        assert "copy" in result.columns
        assert result["copy"].tolist() == [10, 20]
        assert len(deferred) == 0

    def test_column_copy_case_insensitive(self):
        """Column copy is case-insensitive."""
        evaluator = ExtraColumnEvaluator()
        df = pd.DataFrame({"Source": [10, 20]})
        result, deferred = evaluator.evaluate_extra_columns(df, {"copy": "source"}, "test")

        assert "copy" in result.columns
        assert result["copy"].tolist() == [10, 20]

    def test_simple_interpolation(self):
        """Simple interpolation is evaluated."""
        evaluator = ExtraColumnEvaluator()
        df = pd.DataFrame({"first": ["John"], "last": ["Doe"]})
        result, deferred = evaluator.evaluate_extra_columns(df, {"fullname": "{first} {last}"}, "test")

        assert "fullname" in result.columns
        assert result["fullname"].iloc[0] == "John Doe"
        assert len(deferred) == 0

    def test_multiple_extra_columns(self):
        """Multiple extra columns are added in one pass."""
        evaluator = ExtraColumnEvaluator()
        df = pd.DataFrame({"a": [1], "b": [2]})
        extra = {"const": 99, "copy": "a", "interp": "{a}-{b}"}
        result, deferred = evaluator.evaluate_extra_columns(df, extra, "test")

        assert list(result.columns) == ["a", "b", "const", "copy", "interp"]
        assert result["const"].iloc[0] == 99
        assert result["copy"].iloc[0] == 1
        assert result["interp"].iloc[0] == "1-2"

    def test_interpolation_missing_column_raises_by_default(self):
        """Interpolation with missing column raises error by default."""
        evaluator = ExtraColumnEvaluator()
        df = pd.DataFrame({"a": [1]})

        with pytest.raises(ValueError, match="columns not found"):
            evaluator.evaluate_extra_columns(df, {"bad": "{missing}"}, "test", defer_missing=False)

    def test_interpolation_missing_column_deferred_when_flag_set(self):
        """Interpolation with missing column is deferred when flag set."""
        evaluator = ExtraColumnEvaluator()
        df = pd.DataFrame({"a": [1]})
        result, deferred = evaluator.evaluate_extra_columns(df, {"later": "{missing}"}, "test", defer_missing=True)

        assert "later" not in result.columns
        assert "later" in deferred
        assert deferred["later"] == "{missing}"

    def test_mixed_evaluation_and_deferral(self):
        """Some columns evaluated, others deferred."""
        evaluator = ExtraColumnEvaluator()
        df = pd.DataFrame({"a": [1]})
        extra = {"const": 99, "good_interp": "{a}", "bad_interp": "{missing}"}
        result, deferred = evaluator.evaluate_extra_columns(df, extra, "test", defer_missing=True)

        assert "const" in result.columns
        assert "good_interp" in result.columns
        assert "bad_interp" not in result.columns
        assert "bad_interp" in deferred

    def test_empty_extra_columns(self):
        """Empty extra_columns dict returns unchanged DataFrame."""
        evaluator = ExtraColumnEvaluator()
        df = pd.DataFrame({"a": [1]})
        result, deferred = evaluator.evaluate_extra_columns(df, {}, "test")

        assert result.equals(df)
        assert len(deferred) == 0

    def test_none_extra_columns(self):
        """None extra_columns returns unchanged DataFrame."""
        evaluator = ExtraColumnEvaluator()
        df = pd.DataFrame({"a": [1]})
        result, deferred = evaluator.evaluate_extra_columns(df, None, "test")

        assert result.equals(df)
        assert len(deferred) == 0


class TestDeferredEvaluation:
    """Test deferred evaluation workflow (simulate FK linking)."""

    def test_deferred_then_evaluated(self):
        """Deferred interpolation can be evaluated after columns added."""
        evaluator = ExtraColumnEvaluator()

        # Initial DF (no FK columns yet)
        df = pd.DataFrame({"site_name": ["Site A"]})

        # Attempt interpolation - should defer
        result, deferred = evaluator.evaluate_extra_columns(df, {"info": "{site_name} ({location_name})"}, "site", defer_missing=True)

        assert "info" not in result.columns
        assert "info" in deferred

        # Simulate FK link adding column
        result["location_name"] = "Norway"

        # Re-evaluate deferred
        result, still_deferred = evaluator.evaluate_extra_columns(result, deferred, "site", defer_missing=False)

        assert len(still_deferred) == 0
        assert "info" in result.columns
        assert result["info"].iloc[0] == "Site A (Norway)"

    def test_multiple_deferred_columns(self):
        """Multiple deferred columns can be evaluated together."""
        evaluator = ExtraColumnEvaluator()

        df = pd.DataFrame({"a": [1]})
        extra = {"x": "{b}", "y": "{c}", "z": "{a}"}  # This one works immediately

        result, deferred = evaluator.evaluate_extra_columns(df, extra, "test", defer_missing=True)

        assert "z" in result.columns
        assert len(deferred) == 2

        # Add missing columns
        result["b"] = 2
        result["c"] = 3

        # Re-evaluate
        result, still_deferred = evaluator.evaluate_extra_columns(result, deferred, "test", defer_missing=False)

        assert len(still_deferred) == 0
        assert result["x"].iloc[0] == "2"
        assert result["y"].iloc[0] == "3"

    def test_partial_resolution(self):
        """Some deferred columns resolve, others still missing."""
        evaluator = ExtraColumnEvaluator()

        df = pd.DataFrame({"a": [1]})
        extra = {"x": "{b}", "y": "{c}"}

        result, deferred = evaluator.evaluate_extra_columns(df, extra, "test", defer_missing=True)
        assert len(deferred) == 2

        # Add only one missing column
        result["b"] = 2

        # Re-evaluate with defer_missing=True
        result, still_deferred = evaluator.evaluate_extra_columns(result, deferred, "test", defer_missing=True)

        assert "x" in result.columns  # This one resolved
        assert "y" not in result.columns  # Still missing
        assert len(still_deferred) == 1
        assert "y" in still_deferred


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_dataframe(self):
        """Works on empty DataFrame."""
        evaluator = ExtraColumnEvaluator()
        df = pd.DataFrame(columns=["a"])
        result, deferred = evaluator.evaluate_extra_columns(df, {"const": 99}, "test")

        assert "const" in result.columns
        assert len(result) == 0

    def test_interpolation_on_empty_dataframe(self):
        """Interpolation on empty DataFrame works."""
        evaluator = ExtraColumnEvaluator()
        df = pd.DataFrame(columns=["a", "b"])
        result, deferred = evaluator.evaluate_extra_columns(df, {"x": "{a} {b}"}, "test")

        assert "x" in result.columns
        assert len(result) == 0

    def test_special_characters_in_values(self):
        """Special characters in values are handled."""
        evaluator = ExtraColumnEvaluator()
        df = pd.DataFrame({"name": ["O'Brien", "Smith & Co"]})
        result, deferred = evaluator.evaluate_extra_columns(df, {"full": "Name: {name}"}, "test")

        assert result["full"].tolist() == ["Name: O'Brien", "Name: Smith & Co"]

    def test_unicode_characters(self):
        """Unicode characters are handled."""
        evaluator = ExtraColumnEvaluator()
        df = pd.DataFrame({"city": ["São Paulo", "北京"]})
        result, deferred = evaluator.evaluate_extra_columns(df, {"loc": "City: {city}"}, "test")

        assert result["loc"].tolist() == ["City: São Paulo", "City: 北京"]

    def test_large_dataframe_performance(self):
        """Handles large DataFrames reasonably."""
        evaluator = ExtraColumnEvaluator()
        df = pd.DataFrame({"first": ["Name"] * 10000, "last": ["Test"] * 10000})
        result, deferred = evaluator.evaluate_extra_columns(df, {"full": "{first} {last}"}, "test")

        assert len(result) == 10000
        assert all(result["full"] == "Name Test")

    def test_very_long_interpolation(self):
        """Long interpolation pattern works."""
        evaluator = ExtraColumnEvaluator()
        df = pd.DataFrame({"a": [1], "b": [2], "c": [3], "d": [4]})
        pattern = "{a}-{b}-{c}-{d}-{a}-{b}-{c}-{d}"
        result, deferred = evaluator.evaluate_extra_columns(df, {"long": pattern}, "test")

        assert result["long"].iloc[0] == "1-2-3-4-1-2-3-4"

    def test_column_name_same_as_new_column(self):
        """Can create column with interpolation from non-existent source."""
        evaluator = ExtraColumnEvaluator()
        df = pd.DataFrame({"a": [1]})
        # This creates "a" as an interpolated column (original "a" exists)
        result, deferred = evaluator.evaluate_extra_columns(df, {"b": "{a}"}, "test")

        assert result["b"].iloc[0] == "1"


class TestIdempotentEvaluation:
    """Test idempotent evaluation (skipping already-evaluated columns)."""

    def test_skips_existing_columns(self):
        """Evaluator skips columns that already exist in DataFrame."""
        evaluator = ExtraColumnEvaluator()
        df = pd.DataFrame({"a": [1, 2], "status": ["active", "inactive"]})

        # Try to add a column that already exists
        result, deferred = evaluator.evaluate_extra_columns(df, {"status": "pending"}, "test")

        # Should skip the existing column (not overwrite)
        assert result["status"].tolist() == ["active", "inactive"]
        assert len(deferred) == 0

    def test_multiple_calls_idempotent(self):
        """Calling evaluate_extra_columns multiple times is idempotent."""
        evaluator = ExtraColumnEvaluator()
        df = pd.DataFrame({"a": [1, 2]})
        extra_columns = {"const": 99, "copy": "a", "interp": "{a}"}

        # First call - should add all columns
        result1, deferred1 = evaluator.evaluate_extra_columns(df, extra_columns, "test")
        assert "const" in result1.columns
        assert "copy" in result1.columns
        assert "interp" in result1.columns
        assert len(deferred1) == 0

        # Second call with same extra_columns - should skip all (idempotent)
        result2, deferred2 = evaluator.evaluate_extra_columns(result1, extra_columns, "test")
        assert result2.equals(result1)  # No changes
        assert len(deferred2) == 0

    def test_partial_evaluation_then_completion(self):
        """After partial evaluation, can complete with same extra_columns dict."""
        evaluator = ExtraColumnEvaluator()
        df = pd.DataFrame({"a": [1, 2]})
        extra_columns = {"const": 99, "from_a": "{a}", "from_both": "{a}-{missing_col}"}  # Will defer (missing_col not available)

        # First call - 2 succeed, 1 deferred
        result1, deferred1 = evaluator.evaluate_extra_columns(df, extra_columns, "test", defer_missing=True)
        assert "const" in result1.columns
        assert "from_a" in result1.columns
        assert "from_both" not in result1.columns
        assert "from_both" in deferred1

        # Add the missing column
        result1["missing_col"] = [10, 20]

        # Second call with FULL extra_columns dict (not just deferred)
        # Should skip existing, evaluate deferred
        result2, deferred2 = evaluator.evaluate_extra_columns(result1, extra_columns, "test", defer_missing=True)
        assert "const" in result2.columns  # Skipped (already exists)
        assert "from_a" in result2.columns  # Skipped (already exists)
        assert "from_both" in result2.columns  # Newly evaluated!
        assert result2["from_both"].tolist() == ["1-10", "2-20"]
        assert len(deferred2) == 0

    def test_skip_count_logged(self):
        """Skipped columns are counted and logged."""
        evaluator = ExtraColumnEvaluator()
        df = pd.DataFrame({"a": [1], "existing": ["old"]})

        # Try to add "existing" (should skip) and "new" (should add)
        result, deferred = evaluator.evaluate_extra_columns(df, {"existing": "new_value", "new": "added"}, "test")

        # existing should be skipped, new should be added
        assert result["existing"].iloc[0] == "old"  # Not overwritten
        assert result["new"].iloc[0] == "added"


class TestVerifyExtraColumns:
    """Test verify_extra_columns method for validation."""

    def test_verify_all_evaluated(self):
        """Test verify returns True when all columns are evaluated."""
        evaluator = ExtraColumnEvaluator()
        df = pd.DataFrame({"a": [1, 2], "from_a": ["1", "2"]})
        extra_columns = {"from_a": "{a}"}

        result = evaluator.verify_extra_columns(df, extra_columns, "test")

        assert result is True

    def test_verify_missing_columns(self):
        """Test verify returns False and logs warning when columns are missing."""
        evaluator = ExtraColumnEvaluator()
        df = pd.DataFrame({"a": [1, 2]})
        extra_columns = {"from_a": "{a}", "from_b": "{b}"}

        # Should return False when columns are missing (warning is logged to stderr)
        result = evaluator.verify_extra_columns(df, extra_columns, "test")

        assert result is False

    def test_verify_no_extra_columns(self):
        """Test verify returns True when no extra_columns configured."""
        evaluator = ExtraColumnEvaluator()
        df = pd.DataFrame({"a": [1, 2]})
        extra_columns = {}

        result = evaluator.verify_extra_columns(df, extra_columns, "test")

        assert result is True

    def test_verify_partial_missing(self):
        """Test verify detects partially missing columns."""
        evaluator = ExtraColumnEvaluator()
        df = pd.DataFrame({"a": [1, 2], "from_a": ["1", "2"]})
        extra_columns = {"from_a": "{a}", "from_b": "{b}", "from_c": "{c}"}

        # Should return False when some columns are missing
        result = evaluator.verify_extra_columns(df, extra_columns, "test")

        assert result is False
