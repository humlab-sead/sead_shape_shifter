"""
Comprehensive tests for the DSL module (src/transforms/dsl.py).

Tests cover:
- Tokenizer: token recognition, position tracking, error handling
- Parser: valid expressions, AST structure, syntax errors
- Validator: column/function validation, complexity limits
- Evaluator: function implementations, null handling, type conversion
- FormulaEngine: end-to-end integration
- Edge cases: unicode, escaping, special characters
"""

from typing import cast

import pandas as pd
import pytest

from src.transforms.dsl import (
    Call,
    ColumnRef,
    DSLEvaluationError,
    DSLParseError,
    DSLValidationError,
    Expr,
    FormulaEngine,
    FormulaParser,
    FunctionSpec,
    Literal,
    PandasStringBackend,
    SourceSpan,
    Tokenizer,
    TokenType,
    ValidationConfig,
    Validator,
)

# ============================================================================
# Tokenizer Tests
# ============================================================================


class TestTokenizer:
    """Test the tokenizer component."""

    def test_tokenize_simple_formula(self):
        """Tokenize a simple formula with basic tokens."""
        tokenizer = Tokenizer("=upper(col)")
        tokens = tokenizer.tokens

        assert len(tokens) == 6  # EQUAL, NAME, LPAREN, NAME, RPAREN, EOF
        assert tokens[0].type == TokenType.EQUAL
        assert tokens[1].type == TokenType.NAME
        assert tokens[1].value == "upper"
        assert tokens[2].type == TokenType.LPAREN
        assert tokens[3].type == TokenType.NAME
        assert tokens[3].value == "col"
        assert tokens[4].type == TokenType.RPAREN
        assert tokens[5].type == TokenType.EOF

    def test_tokenize_string_literals(self):
        """Tokenize string literals with single and double quotes."""
        tokenizer = Tokenizer('="hello"')
        assert tokenizer.tokens[1].type == TokenType.STRING
        assert tokenizer.tokens[1].value == '"hello"'

        tokenizer = Tokenizer("='world'")
        assert tokenizer.tokens[1].type == TokenType.STRING
        assert tokenizer.tokens[1].value == "'world'"

    def test_tokenize_integer_literals(self):
        """Tokenize integer literals including negative numbers."""
        tokenizer = Tokenizer("=substr(col, 0, 5)")
        assert tokenizer.tokens[5].type == TokenType.INTEGER
        assert tokenizer.tokens[5].value == "0"
        assert tokenizer.tokens[7].type == TokenType.INTEGER
        assert tokenizer.tokens[7].value == "5"

        tokenizer = Tokenizer("=substr(col, -1, 2)")
        assert tokenizer.tokens[5].type == TokenType.INTEGER
        assert tokenizer.tokens[5].value == "-1"

    def test_tokenize_function_with_multiple_args(self):
        """Tokenize function call with multiple comma-separated arguments."""
        tokenizer = Tokenizer("=concat(a, b, c)")
        token_types = [t.type for t in tokenizer.tokens]

        assert TokenType.COMMA in token_types
        assert token_types.count(TokenType.COMMA) == 2

    def test_tokenize_nested_functions(self):
        """Tokenize nested function calls."""
        tokenizer = Tokenizer("=upper(trim(col))")
        token_values = [t.value for t in tokenizer.tokens if t.type == TokenType.NAME]

        assert token_values == ["upper", "trim", "col"]

    def test_tokenize_whitespace_handling(self):
        """Whitespace should be properly ignored."""
        tokenizer = Tokenizer("  =  upper  (  col  )  ")
        token_types = [t.type for t in tokenizer.tokens[:-1]]  # Exclude EOF

        assert token_types == [
            TokenType.EQUAL,
            TokenType.NAME,
            TokenType.LPAREN,
            TokenType.NAME,
            TokenType.RPAREN,
        ]

    def test_tokenize_position_tracking(self):
        """Token positions should be tracked correctly."""
        tokenizer = Tokenizer("=upper(col)")

        # Check EQUAL token position
        assert tokenizer.tokens[0].span.line == 1
        assert tokenizer.tokens[0].span.column == 1

        # Check NAME token position
        assert tokenizer.tokens[1].span.column == 2

    def test_tokenize_error_on_invalid_character(self):
        """Invalid characters should raise DSLParseError."""
        with pytest.raises(DSLParseError, match="Unexpected character"):
            Tokenizer("=upper(col) @")

    def test_tokenize_eof_token_added(self):
        """EOF token should be added at the end."""
        tokenizer = Tokenizer("=col")
        assert tokenizer.tokens[-1].type == TokenType.EOF

    def test_tokenize_empty_string(self):
        """Empty string should produce only EOF token."""
        tokenizer = Tokenizer("")
        assert len(tokenizer.tokens) == 1
        assert tokenizer.tokens[0].type == TokenType.EOF


# ============================================================================
# Parser Tests
# ============================================================================


class TestParser:
    """Test the parser component."""

    def test_parse_simple_column_reference(self):
        """Parse a simple column reference formula."""
        parser = FormulaParser()
        expr = parser.parse("=col")

        assert isinstance(expr, ColumnRef)
        assert expr.name == "col"

    def test_parse_string_literal(self):
        """Parse string literals."""
        parser = FormulaParser()

        expr = parser.parse('="hello"')
        assert isinstance(expr, Literal)
        assert expr.value == "hello"

        expr = parser.parse("='world'")
        assert isinstance(expr, Literal)
        assert expr.value == "world"

    def test_parse_integer_literal(self):
        """Parse integer literals."""
        parser = FormulaParser()

        expr = parser.parse("=42")
        assert isinstance(expr, Literal)
        assert expr.value == 42

        expr = parser.parse("=-10")
        assert isinstance(expr, Literal)
        assert expr.value == -10

    def test_parse_null_literal(self):
        """Parse null literal."""
        parser = FormulaParser()
        expr = parser.parse("=null")

        assert isinstance(expr, Literal)
        assert expr.value is None

    def test_parse_boolean_literals(self):
        """Parse true and false literals."""
        parser = FormulaParser()

        expr = parser.parse("=true")
        assert isinstance(expr, Literal)
        assert expr.value is True

        expr = parser.parse("=false")
        assert isinstance(expr, Literal)
        assert expr.value is False

    def test_parse_function_call_no_args(self):
        """Parse function call with no arguments."""
        parser = FormulaParser()
        expr = parser.parse("=func()")

        assert isinstance(expr, Call)
        assert expr.name == "func"
        assert len(expr.args) == 0

    def test_parse_function_call_one_arg(self):
        """Parse function call with one argument."""
        parser = FormulaParser()
        expr = parser.parse("=upper(col)")

        assert isinstance(expr, Call)
        assert expr.name == "upper"
        assert len(expr.args) == 1
        assert isinstance(expr.args[0], ColumnRef)
        assert expr.args[0].name == "col"

    def test_parse_function_call_multiple_args(self):
        """Parse function call with multiple arguments."""
        parser = FormulaParser()
        expr = parser.parse("=concat(a, b, c)")

        assert isinstance(expr, Call)
        assert expr.name == "concat"
        assert len(expr.args) == 3
        assert all(isinstance(arg, ColumnRef) for arg in expr.args)

    def test_parse_nested_function_calls(self):
        """Parse nested function calls."""
        parser = FormulaParser()
        expr = parser.parse("=upper(trim(col))")

        assert isinstance(expr, Call)
        assert expr.name == "upper"
        assert len(expr.args) == 1

        inner = expr.args[0]
        assert isinstance(inner, Call)
        assert inner.name == "trim"
        assert isinstance(inner.args[0], ColumnRef)

    def test_parse_function_with_mixed_args(self):
        """Parse function with mixed argument types."""
        parser = FormulaParser()
        expr = parser.parse('=concat(col, " - ", "text")')

        assert isinstance(expr, Call)
        assert len(expr.args) == 3
        assert isinstance(expr.args[0], ColumnRef)
        assert isinstance(expr.args[1], Literal)
        assert isinstance(expr.args[2], Literal)

    def test_parse_complex_expression(self):
        """Parse complex nested expression."""
        parser = FormulaParser()
        expr = parser.parse("=concat(upper(substr(first_name, 0, 1)), upper(substr(last_name, 0, 1)))")

        assert isinstance(expr, Call)
        assert expr.name == "concat"
        assert len(expr.args) == 2
        assert all(isinstance(arg, Call) for arg in expr.args)

    def test_parse_error_missing_equals(self):
        """Formula without leading '=' should fail."""
        parser = FormulaParser()
        with pytest.raises(DSLParseError, match="Formula must start with '='"):
            parser.parse("upper(col)")

    def test_parse_error_unexpected_token(self):
        """Unexpected token after expression should fail."""
        parser = FormulaParser()
        with pytest.raises(DSLParseError, match="Unexpected token after expression"):
            parser.parse("=col extra")

    def test_parse_error_unexpected_identifier(self):
        """Unexpected identifier (not null/true/false) is treated as column reference."""
        parser = FormulaParser()
        # Note: Any NAME token that isn't a function call or reserved word is a column ref
        expr = parser.parse("=undefined_column")
        assert isinstance(expr, ColumnRef)
        assert expr.name == "undefined_column"

    def test_parse_error_unclosed_parenthesis(self):
        """Unclosed parenthesis should fail."""
        parser = FormulaParser()
        with pytest.raises(DSLParseError, match="Expected RPAREN"):
            parser.parse("=upper(col")

    def test_parse_error_missing_argument(self):
        """Missing function argument should fail."""
        parser = FormulaParser()
        with pytest.raises(DSLParseError):
            parser.parse("=concat(a,)")

    def test_parse_string_escaping(self):
        """Parse strings with escape sequences."""
        parser = FormulaParser()

        # Test various escape sequences
        expr: Expr = parser.parse(r'="hello\nworld"')
        assert isinstance(expr, Literal)
        assert expr.value == "hello\nworld"

        literal: Literal = cast(Literal, parser.parse(r'="tab\there"'))
        assert literal.value == "tab\there"

        literal: Literal = cast(Literal, parser.parse(r'="quote\"inside"'))
        assert literal.value == 'quote"inside'


# ============================================================================
# Validator Tests
# ============================================================================


class TestValidator:
    """Test the validator component."""

    def test_validate_column_reference_valid(self):
        """Valid column reference should pass validation."""
        allowed_columns = {"first_name", "last_name"}
        functions = {"upper": FunctionSpec("upper", "upper", exact_args=1)}
        validator = Validator(allowed_columns, functions)

        expr = ColumnRef(span=SourceSpan(1, 1, 1, 10), name="first_name")
        validator.validate(expr)  # Should not raise

    def test_validate_column_reference_invalid(self):
        """Invalid column reference should raise DSLValidationError."""
        allowed_columns = {"first_name"}
        validator = Validator(allowed_columns, {})

        expr = ColumnRef(span=SourceSpan(1, 1, 1, 10), name="unknown_col")
        with pytest.raises(DSLValidationError, match="Unknown column 'unknown_col'"):
            validator.validate(expr)

    def test_validate_function_exists(self):
        """Known function should pass validation."""
        functions = {"upper": FunctionSpec("upper", "upper", exact_args=1)}
        validator = Validator(set(), functions)

        expr = Call(
            span=SourceSpan(1, 1, 1, 10),
            name="upper",
            args=[Literal(span=SourceSpan(1, 1, 1, 1), value="hello")],
        )
        validator.validate(expr)  # Should not raise

    def test_validate_function_unknown(self):
        """Unknown function should raise DSLValidationError."""
        functions = {"upper": FunctionSpec("upper", "upper", exact_args=1)}
        validator = Validator(set(), functions)

        expr = Call(
            span=SourceSpan(1, 1, 1, 10),
            name="undefined_func",
            args=[],
        )
        with pytest.raises(DSLValidationError, match="Unknown function 'undefined_func'"):
            validator.validate(expr)

    def test_validate_arity_exact(self):
        """Function with exact argument count should validate."""
        functions = {"upper": FunctionSpec("upper", "upper", exact_args=1)}
        validator = Validator(set(), functions)

        # Correct arg count
        expr = Call(
            span=SourceSpan(1, 1, 1, 10),
            name="upper",
            args=[Literal(span=SourceSpan(1, 1, 1, 1), value="x")],
        )
        validator.validate(expr)  # Should not raise

        # Wrong arg count
        expr = Call(
            span=SourceSpan(1, 1, 1, 10),
            name="upper",
            args=[],
        )
        with pytest.raises(DSLValidationError, match="expects exactly 1 arguments, got 0"):
            validator.validate(expr)

    def test_validate_arity_min_max(self):
        """Function with min/max argument count should validate."""
        functions = {"concat": FunctionSpec("concat", "concat", min_args=1, max_args=10)}
        validator = Validator(set(), functions)

        # Too few
        expr = Call(span=SourceSpan(1, 1, 1, 10), name="concat", args=[])
        with pytest.raises(DSLValidationError, match="expects at least 1 arguments"):
            validator.validate(expr)

        # Too many
        expr = Call(
            span=SourceSpan(1, 1, 1, 10),
            name="concat",
            args=[Literal(span=SourceSpan(1, 1, 1, 1), value=i) for i in range(11)],
        )
        with pytest.raises(DSLValidationError, match="expects at most 10 arguments"):
            validator.validate(expr)

    def test_validate_max_depth(self):
        """Expression exceeding max depth should fail."""
        functions = {"upper": FunctionSpec("upper", "upper", exact_args=1)}
        config = ValidationConfig(max_depth=3)
        validator = Validator(set(), functions, config)

        # Build nested expression: upper(upper(upper(upper(col))))
        expr = ColumnRef(span=SourceSpan(1, 1, 1, 1), name="col")
        for _ in range(4):
            expr = Call(span=SourceSpan(1, 1, 1, 1), name="upper", args=[expr])

        with pytest.raises(DSLValidationError, match="nesting exceeds maximum depth"):
            validator.validate(expr)

    def test_validate_max_nodes(self):
        """Expression exceeding max node count should fail."""
        functions = {"concat": FunctionSpec("concat", "concat", min_args=1)}
        config = ValidationConfig(max_total_nodes=10)
        validator = Validator(set(), functions, config)

        # Build large expression: concat(1, 2, 3, ..., 20)
        args: list[Expr] = [Literal(span=SourceSpan(1, 1, 1, 1), value=i) for i in range(20)]
        expr = Call(span=SourceSpan(1, 1, 1, 1), name="concat", args=args)

        with pytest.raises(DSLValidationError, match="too complex.*exceeds limit"):
            validator.validate(expr)

    def test_validate_max_string_length(self):
        """String literal exceeding max length should fail."""
        config = ValidationConfig(max_string_literal_length=100)
        validator = Validator(set(), {}, config)

        expr = Literal(span=SourceSpan(1, 1, 1, 1), value="x" * 101)
        with pytest.raises(DSLValidationError, match="String literal exceeds maximum length"):
            validator.validate(expr)


# ============================================================================
# Evaluator Tests (PandasStringBackend)
# ============================================================================


class TestPandasStringBackend:
    """Test the PandasStringBackend evaluator."""

    def test_get_column(self):
        """Get column should return Series."""
        df = pd.DataFrame({"col": ["a", "b", "c"]})
        backend = PandasStringBackend(df)

        result = backend.get_column("col")
        assert isinstance(result, pd.Series)
        pd.testing.assert_series_equal(result, df["col"])

    def test_get_column_missing(self):
        """Get missing column should raise DSLEvaluationError."""
        df = pd.DataFrame({"col": ["a", "b", "c"]})
        backend = PandasStringBackend(df)

        with pytest.raises(DSLEvaluationError, match="Column 'missing' does not exist"):
            backend.get_column("missing")

    def test_literal(self):
        """Literal should return the value unchanged."""
        df = pd.DataFrame({"col": [1, 2, 3]})
        backend = PandasStringBackend(df)

        assert backend.literal("hello") == "hello"
        assert backend.literal(42) == 42
        assert backend.literal(None) is None

    def test_concat_basic(self):
        """Test concat function with basic strings."""
        df = pd.DataFrame({"a": ["hello", "foo"], "b": ["world", "bar"]})
        backend = PandasStringBackend(df)

        result = backend.call("concat", [df["a"], df["b"]], SourceSpan(1, 1, 1, 1))
        expected = pd.Series(["helloworld", "foobar"], dtype="string")
        pd.testing.assert_series_equal(result, expected, check_names=False)

    def test_concat_with_nulls(self):
        """Test concat with null values (treated as empty string)."""
        df = pd.DataFrame({"a": ["hello", None], "b": ["world", "bar"]})
        backend = PandasStringBackend(df)

        result = backend.call("concat", [df["a"], df["b"]], SourceSpan(1, 1, 1, 1))
        expected = pd.Series(["helloworld", "bar"], dtype="string")
        pd.testing.assert_series_equal(result, expected, check_names=False)

    def test_concat_multiple_args(self):
        """Test concat with multiple arguments."""
        df = pd.DataFrame({"a": ["x"], "b": ["y"], "c": ["z"]})
        backend = PandasStringBackend(df)

        result = backend.call("concat", [df["a"], df["b"], df["c"]], SourceSpan(1, 1, 1, 1))
        expected = pd.Series(["xyz"], dtype="string")
        pd.testing.assert_series_equal(result, expected, check_names=False)

    def test_upper_basic(self):
        """Test upper function."""
        df = pd.DataFrame({"col": ["hello", "World", None]})
        backend = PandasStringBackend(df)

        result = backend.call("upper", [df["col"]], SourceSpan(1, 1, 1, 1))
        expected = pd.Series(["HELLO", "WORLD", None], dtype="string")
        pd.testing.assert_series_equal(result, expected, check_names=False)

    def test_lower_basic(self):
        """Test lower function."""
        df = pd.DataFrame({"col": ["HELLO", "World", None]})
        backend = PandasStringBackend(df)

        result = backend.call("lower", [df["col"]], SourceSpan(1, 1, 1, 1))
        expected = pd.Series(["hello", "world", None], dtype="string")
        pd.testing.assert_series_equal(result, expected, check_names=False)

    def test_trim_basic(self):
        """Test trim function."""
        df = pd.DataFrame({"col": ["  hello  ", " world", "test  ", None]})
        backend = PandasStringBackend(df)

        result = backend.call("trim", [df["col"]], SourceSpan(1, 1, 1, 1))
        expected = pd.Series(["hello", "world", "test", None], dtype="string")
        pd.testing.assert_series_equal(result, expected, check_names=False)

    def test_substr_basic(self):
        """Test substr function with basic slicing."""
        df = pd.DataFrame({"col": ["hello", "world", None]})
        backend = PandasStringBackend(df)

        result = backend.call("substr", [df["col"], 0, 3], SourceSpan(1, 1, 1, 1))
        expected = pd.Series(["hel", "wor", None], dtype="string")
        pd.testing.assert_series_equal(result, expected, check_names=False)

    def test_substr_offset(self):
        """Test substr with non-zero start offset."""
        df = pd.DataFrame({"col": ["hello"]})
        backend = PandasStringBackend(df)

        result = backend.call("substr", [df["col"], 2, 3], SourceSpan(1, 1, 1, 1))
        expected = pd.Series(["llo"], dtype="string")
        pd.testing.assert_series_equal(result, expected, check_names=False)

    def test_substr_negative_length_error(self):
        """Test substr with negative length raises error."""
        df = pd.DataFrame({"col": ["hello"]})
        backend = PandasStringBackend(df)

        with pytest.raises(DSLEvaluationError, match="requires non-negative length"):
            backend.call("substr", [df["col"], 0, -1], SourceSpan(1, 1, 1, 1))

    def test_substr_requires_scalar_args(self):
        """Test substr requires scalar integer arguments."""
        df = pd.DataFrame({"col": ["hello"], "pos": [0]})
        backend = PandasStringBackend(df)

        with pytest.raises(DSLEvaluationError, match="requires integer literal arguments"):
            backend.call("substr", [df["col"], df["pos"], 2], SourceSpan(1, 1, 1, 1))

    def test_coalesce_first_non_null(self):
        """Test coalesce returns first non-null value."""
        df = pd.DataFrame(
            {
                "a": [None, None, "x"],
                "b": [None, "y", "z"],
                "c": ["p", "q", "r"],
            }
        )
        backend = PandasStringBackend(df)

        result = backend.call("coalesce", [df["a"], df["b"], df["c"]], SourceSpan(1, 1, 1, 1))
        expected = pd.Series(["p", "y", "x"])
        pd.testing.assert_series_equal(result, expected, check_names=False)

    def test_coalesce_all_null(self):
        """Test coalesce when all values are null."""
        df = pd.DataFrame({"a": [None, None], "b": [None, None]})
        backend = PandasStringBackend(df)

        result = backend.call("coalesce", [df["a"], df["b"]], SourceSpan(1, 1, 1, 1))
        expected = pd.Series([None, None])
        pd.testing.assert_series_equal(result, expected, check_names=False)

    def test_coalesce_with_literals(self):
        """Test coalesce with scalar literal fallback."""
        df = pd.DataFrame({"a": [None, "x", None]})
        backend = PandasStringBackend(df)

        result = backend.call("coalesce", [df["a"], "fallback"], SourceSpan(1, 1, 1, 1))
        expected = pd.Series(["fallback", "x", "fallback"])
        pd.testing.assert_series_equal(result, expected, check_names=False)

    def test_unknown_function_error(self):
        """Test calling unknown function raises error."""
        df = pd.DataFrame({"col": ["a"]})
        backend = PandasStringBackend(df)

        with pytest.raises(DSLEvaluationError, match="No backend implementation for 'unknown'"):
            backend.call("unknown", [], SourceSpan(1, 1, 1, 1))


# ============================================================================
# FormulaEngine Integration Tests
# ============================================================================


class TestFormulaEngine:
    """Test the FormulaEngine end-to-end."""

    def test_evaluate_formula_simple(self):
        """Evaluate simple formula."""
        df = pd.DataFrame({"col": ["hello", "world"]})
        engine = FormulaEngine()

        result = engine.evaluate_formula("=upper(col)", df)
        expected = pd.Series(["HELLO", "WORLD"], dtype="string")
        pd.testing.assert_series_equal(result, expected, check_names=False)

    def test_evaluate_formula_complex(self):
        """Evaluate complex nested formula."""
        df = pd.DataFrame({"first": ["ada", "grace"], "last": ["lovelace", "hopper"]})
        engine = FormulaEngine()

        result = engine.evaluate_formula("=concat(upper(substr(first, 0, 1)), upper(substr(last, 0, 1)))", df)
        expected = pd.Series(["AL", "GH"], dtype="string")
        pd.testing.assert_series_equal(result, expected, check_names=False)

    def test_apply_extra_columns(self):
        """Apply multiple extra_columns formulas to DataFrame."""
        df = pd.DataFrame(
            {
                "first_name": ["Ada", "Grace"],
                "last_name": ["Lovelace", "Hopper"],
            }
        )

        formulas = {
            "fullname": "=concat(first_name, ' ', last_name)",
            "initials": "=concat(substr(first_name, 0, 1), substr(last_name, 0, 1))",
        }

        engine = FormulaEngine()
        result = engine.apply_extra_columns(df, formulas, in_place=False)

        assert "fullname" in result.columns
        assert "initials" in result.columns
        assert result["fullname"].tolist() == ["Ada Lovelace", "Grace Hopper"]
        assert result["initials"].tolist() == ["AL", "GH"]

    def test_apply_extra_columns_in_place(self):
        """Apply extra_columns in place modifies original DataFrame."""
        df = pd.DataFrame({"col": ["a", "b"]})
        formulas = {"upper_col": "=upper(col)"}

        engine = FormulaEngine()
        result = engine.apply_extra_columns(df, formulas, in_place=True)

        assert result is df  # Same object
        assert "upper_col" in df.columns

    def test_compile_validates_columns(self):
        """Compile should validate column references."""
        df = pd.DataFrame({"col": ["a", "b"]})
        engine = FormulaEngine()

        # Valid column
        expr = engine.compile("=upper(col)", df.columns)
        assert isinstance(expr, Call)

        # Invalid column
        with pytest.raises(DSLValidationError, match="Unknown column 'missing'"):
            engine.compile("=upper(missing)", df.columns)

    def test_custom_validation_config(self):
        """FormulaEngine with custom validation config."""
        config = ValidationConfig(max_depth=2)
        engine = FormulaEngine(validation_config=config)

        # Should fail due to low max_depth
        with pytest.raises(DSLValidationError, match="nesting exceeds maximum depth"):
            engine.compile("=upper(upper(upper(col)))", ["col"])

    def test_error_propagation(self):
        """Errors should propagate with appropriate types."""
        df = pd.DataFrame({"col": ["a"]})
        engine = FormulaEngine()

        # Parse error
        with pytest.raises(DSLParseError):
            engine.evaluate_formula("invalid", df)

        # Validation error
        with pytest.raises(DSLValidationError):
            engine.evaluate_formula("=unknown_func()", df)

        # Validation error for unknown column (caught at validation stage)
        with pytest.raises(DSLValidationError):
            engine.evaluate_formula("=missing_col", df)


# ============================================================================
# Edge Cases and Special Scenarios
# ============================================================================


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_unicode_handling(self):
        """Test unicode characters in strings."""
        df = pd.DataFrame({"col": ["café", "naïve", "日本語"]})
        engine = FormulaEngine()

        result = engine.evaluate_formula("=upper(col)", df)
        # Note: behavior depends on pandas string handling
        assert len(result) == 3

    def test_empty_string_handling(self):
        """Test empty strings."""
        df = pd.DataFrame({"col": ["", "a", ""]})
        engine = FormulaEngine()

        result = engine.evaluate_formula("=concat(col, 'x')", df)
        expected = pd.Series(["x", "ax", "x"], dtype="string")
        pd.testing.assert_series_equal(result, expected, check_names=False)

    def test_whitespace_only_strings(self):
        """Test strings with only whitespace."""
        df = pd.DataFrame({"col": ["   ", "\t", "\n"]})
        engine = FormulaEngine()

        result = engine.evaluate_formula("=trim(col)", df)
        expected = pd.Series(["", "", ""], dtype="string")
        pd.testing.assert_series_equal(result, expected, check_names=False)

    def test_very_long_strings(self):
        """Test handling of very long strings."""
        df = pd.DataFrame({"col": ["x" * 1000]})
        engine = FormulaEngine()

        result = engine.evaluate_formula("=upper(col)", df)
        assert len(result[0]) == 1000

    def test_special_characters_in_column_names(self):
        """Test column names with underscores and numbers."""
        df = pd.DataFrame({"col_1": ["a"], "col_2_name": ["b"]})
        engine = FormulaEngine()

        result = engine.evaluate_formula("=concat(col_1, col_2_name)", df)
        expected = pd.Series(["ab"], dtype="string")
        pd.testing.assert_series_equal(result, expected, check_names=False)

    def test_formula_with_literal_strings_containing_quotes(self):
        """Test formulas with string literals containing quotes."""
        df = pd.DataFrame({"col": ["a"]})
        engine = FormulaEngine()

        # Double quotes inside single-quoted string
        result = engine.evaluate_formula("=concat(col, ' says \"hi\"')", df)
        assert result[0] == 'a says "hi"'

        # Single quote inside double-quoted string
        result = engine.evaluate_formula('=concat(col, " it\'s ok")', df)
        assert result[0] == "a it's ok"

    def test_nested_function_calls_depth(self):
        """Test deeply nested function calls."""
        df = pd.DataFrame({"col": ["abc"]})
        engine = FormulaEngine()

        # Should work within default max_depth (20)
        formula = "=" + "upper(" * 10 + "col" + ")" * 10
        result = engine.evaluate_formula(formula, df)
        assert result[0] == "ABC"

    def test_concat_single_argument(self):
        """Test concat with single argument."""
        df = pd.DataFrame({"col": ["hello"]})
        engine = FormulaEngine()

        result = engine.evaluate_formula("=concat(col)", df)
        expected = pd.Series(["hello"], dtype="string")
        pd.testing.assert_series_equal(result, expected, check_names=False)

    def test_coalesce_single_argument(self):
        """Test coalesce with single argument."""
        df = pd.DataFrame({"col": [None, "x"]})
        engine = FormulaEngine()

        result = engine.evaluate_formula("=coalesce(col)", df)
        expected = pd.Series([None, "x"])
        pd.testing.assert_series_equal(result, expected, check_names=False)

    def test_all_nulls_propagation(self):
        """Test null propagation through functions."""
        df = pd.DataFrame({"col": [None, None]})
        engine = FormulaEngine()

        result = engine.evaluate_formula("=upper(col)", df)
        assert result.isna().all()

    def test_mixed_types_coercion(self):
        """Test type coercion in concat."""
        df = pd.DataFrame({"str_col": ["a", "b"], "int_col": [1, 2]})
        engine = FormulaEngine()

        # Integers should be converted to strings
        result = engine.evaluate_formula("=concat(str_col, int_col)", df)
        expected = pd.Series(["a1", "b2"], dtype="string")
        pd.testing.assert_series_equal(result, expected, check_names=False)

    def test_substr_at_boundary(self):
        """Test substr at string boundaries."""
        df = pd.DataFrame({"col": ["abc"]})
        engine = FormulaEngine()

        # Start at end of string
        result = engine.evaluate_formula("=substr(col, 3, 5)", df)
        expected = pd.Series([""], dtype="string")
        pd.testing.assert_series_equal(result, expected, check_names=False)

        # Length longer than string
        result = engine.evaluate_formula("=substr(col, 0, 100)", df)
        expected = pd.Series(["abc"], dtype="string")
        pd.testing.assert_series_equal(result, expected, check_names=False)

    def test_case_sensitivity(self):
        """Test that function and column names are case-sensitive."""
        df = pd.DataFrame({"Col": ["a"], "col": ["b"]})
        engine = FormulaEngine()

        # Function names are case-sensitive
        with pytest.raises(DSLValidationError, match="Unknown function 'UPPER'"):
            engine.compile("=UPPER(col)", df.columns)

        # Column names are case-sensitive
        result = engine.evaluate_formula("=concat(Col, col)", df)
        expected = pd.Series(["ab"], dtype="string")
        pd.testing.assert_series_equal(result, expected, check_names=False)
