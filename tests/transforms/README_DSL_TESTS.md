# DSL Module Test Documentation

## Overview

Comprehensive test suite for the DSL (Domain-Specific Language) parser and evaluator in `src/transforms/dsl.py`. The DSL provides formula expressions for the `extra_columns` feature, enabling safe string transformations directly in YAML configuration.

## Test Coverage

**73 tests** covering **91.39% of code** (exceeds 85% requirement)

## Test Structure

### 1. Tokenizer Tests (`TestTokenizer`)
Tests the lexical analysis phase that converts source text into tokens.

**Coverage:**
- Basic token recognition (NAME, STRING, INTEGER, etc.)
- Position tracking (line and column numbers)
- Whitespace handling
- String literal quoting (single and double quotes)
- Integer literals (positive and negative)
- Error handling for invalid characters
- EOF token generation

**Key Tests:**
- `test_tokenize_simple_formula` - Basic token sequence
- `test_tokenize_string_literals` - Quote handling
- `test_tokenize_position_tracking` - Span information
- `test_tokenize_error_on_invalid_character` - Error reporting

### 2. Parser Tests (`TestParser`)
Tests the syntax analysis phase that builds an Abstract Syntax Tree (AST).

**Coverage:**
- Column references
- Literals (string, integer, null, boolean)
- Function calls (zero args, one arg, multiple args)
- Nested function calls
- Complex expressions
- Error handling (syntax errors, unclosed parentheses)
- String escape sequences

**Key Tests:**
- `test_parse_simple_column_reference` - Basic AST node
- `test_parse_function_call_multiple_args` - Argument parsing
- `test_parse_nested_function_calls` - Recursive descent
- `test_parse_error_missing_equals` - Required formula prefix
- `test_parse_string_escaping` - Escape sequence handling

### 3. Validator Tests (`TestValidator`)
Tests expression validation against allowed columns, functions, and complexity limits.

**Coverage:**
- Column existence checks
- Function whitelist validation
- Arity validation (exact, min, max arguments)
- Complexity limits (max depth, max nodes, max string length)
- Error messages with source spans

**Key Tests:**
- `test_validate_column_reference_invalid` - Unknown column detection
- `test_validate_function_unknown` - Function whitelist enforcement
- `test_validate_arity_exact` - Argument count validation
- `test_validate_max_depth` - Nesting limit enforcement
- `test_validate_max_nodes` - Complexity bound enforcement

### 4. Evaluator Tests (`TestPandasStringBackend`)
Tests the execution engine that evaluates expressions against pandas DataFrames.

**Coverage:**
- All 6 built-in functions:
  - `concat` - String concatenation
  - `upper` - Uppercase conversion
  - `lower` - Lowercase conversion
  - `trim` - Whitespace removal
  - `substr` - Substring extraction
  - `coalesce` - First non-null value
- Null handling (null propagation, null-safe operations)
- Type conversion (integer to string in concat)
- Scalar and Series operations
- Error handling (missing columns, invalid arguments)

**Key Tests:**
- `test_concat_with_nulls` - Null-safe concatenation
- `test_substr_basic` - Substring slicing
- `test_coalesce_first_non_null` - Null coalescing logic
- `test_trim_basic` - Whitespace handling

### 5. Integration Tests (`TestFormulaEngine`)
Tests the end-to-end API that combines parsing, validation, and evaluation.

**Coverage:**
- Simple formulas
- Complex nested formulas
- Batch application to DataFrames (`apply_extra_columns`)
- In-place vs. copy semantics
- Error propagation (parse, validation, evaluation)
- Custom validation configuration

**Key Tests:**
- `test_evaluate_formula_simple` - End-to-end flow
- `test_evaluate_formula_complex` - Real-world usage
- `test_apply_extra_columns` - Multiple columns at once
- `test_error_propagation` - Error type verification

### 6. Edge Cases (`TestEdgeCases`)
Tests special scenarios and boundary conditions.

**Coverage:**
- Unicode characters
- Empty strings
- Very long strings
- Special characters in column names
- String literals with quotes
- Deeply nested function calls
- Single-argument variadic functions
- All-null data
- Mixed type coercion
- Substring boundary cases
- Case sensitivity

**Key Tests:**
- `test_unicode_handling` - Non-ASCII text
- `test_formula_with_literal_strings_containing_quotes` - Quote escaping
- `test_nested_function_calls_depth` - Deep nesting within limits
- `test_substr_at_boundary` - Edge index handling
- `test_case_sensitivity` - Parser case rules

## Running Tests

```bash
# Run all DSL tests
pytest tests/transforms/test_dsl.py -v

# Run specific test class
pytest tests/transforms/test_dsl.py::TestTokenizer -v

# Run with coverage
pytest tests/transforms/test_dsl.py --cov=src.transforms.dsl --cov-report=term-missing

# Run single test
pytest tests/transforms/test_dsl.py::TestParser::test_parse_nested_function_calls -v
```

## Test Patterns

### Assertion Style
- Use `isinstance()` for type checking AST nodes
- Use `pd.testing.assert_series_equal(..., check_names=False)` for Series comparison
- Use `pytest.raises()` for exception testing with `match` parameter for message validation

### Test Data
- Minimal DataFrames (usually 1-3 rows) for clarity
- Named columns for readability (`first_name`, `last_name` vs. `col1`, `col2`)
- Null values explicitly included in test cases
- Edge values (empty strings, unicode, very long strings)

### Test Naming
- `test_<component>_<scenario>` format
- Descriptive docstrings explaining what is being tested
- Group related tests in classes by component

## Coverage Gaps

The following lines are **intentionally untested**:
- `Lines 784-812, 816` - Demo function (`_demo()`) for manual verification
- `Lines 173-174, 321, 334, 357, 400-401` - Rare error paths (unexpected AST node types, unknown function dispatch)
- `Lines 508, 519, 580-581, 589, 607-608, 616, 643, 672, 679` - Exception edge cases in backend functions

These are either:
- Demo/example code not used in production
- Defensive programming checks that should never execute
- Error paths that require unusual test setup

## Future Extensions

When adding new functions or expression types (see [DSL_EXTENSIBILITY_GUIDE.md](../../docs/proposals/DSL_EXTENSIBILITY_GUIDE.md)):

1. **Update AST** - Add new `Expr` subclass
2. **Update Parser** - Add tokenizer patterns and parser methods
3. **Update Validator** - Add validation rules
4. **Update Evaluator** - Add backend implementation
5. **Add Tests** - Follow the 6-category pattern above

Example test organization for a new feature (e.g., binary operators):
```python
class TestBinaryOperators:
    """Test binary arithmetic operators (+, -, *, /)."""
    
    def test_parse_addition(self):
        """Parse addition expression."""
        # ...
    
    def test_validate_numeric_operands(self):
        """Validate operands are numeric."""
        # ...
    
    def test_evaluate_addition(self):
        """Evaluate addition on Series."""
        # ...
```

## Related Documentation

- [src/transforms/dsl.py](../../src/transforms/dsl.py) - Implementation
- [docs/CONFIGURATION_GUIDE.md](../../docs/CONFIGURATION_GUIDE.md) - User documentation for `extra_columns`
- [docs/proposals/DSL_EXTENSIBILITY_GUIDE.md](../../docs/proposals/DSL_EXTENSIBILITY_GUIDE.md) - Guide for extending the DSL
- [docs/archive/DSL_PARSER_COMPARISON.md](../../docs/archive/DSL_PARSER_COMPARISON.md) - Design decision rationale
