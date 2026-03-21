# Tiny DSL In extra_columns: Implementation Sketch

## Status

**✅ Implemented** (March 2026)

- Scope: implementation approach for the tiny DSL proposed in [docs/proposals/done/INTRODUCE_TINY_DSL_IN_EXTRA_COLUMNS.md](INTRODUCE_TINY_DSL_IN_EXTRA_COLUMNS.md)
- Goal: describe a concrete, low-risk implementation path for extending [src/transforms/extra_columns.py](src/transforms/extra_columns.py)
- **Actual Implementation**: [src/transforms/dsl.py](../../src/transforms/dsl.py) (821 lines, standalone module)
- **Tests**: [tests/transforms/test_dsl.py](../../tests/transforms/test_dsl.py) (73 tests, 91% coverage)
- **Integration**: Used by [src/transforms/extra_columns.py](../../src/transforms/extra_columns.py) via `FormulaEngine`

## Summary

This document turned the tiny-DSL proposal into an implementation-oriented sketch. **The implementation has been completed and follows this design closely.**

The key recommendations were:

1. ✅ keep the DSL user-facing and backend-agnostic,
2. ✅ implement it today on top of pandas because `extra_columns` already operates on pandas `DataFrame` objects,
3. ✅ evaluate expressions primarily as column-oriented `Series` operations,
4. ✅ avoid row-based execution except where a specific helper genuinely requires it,
5. ✅ avoid raw `eval` and avoid exposing pandas syntax directly to users.

In short:

1. ✅ parse a small DSL,
2. ✅ compile it to an internal expression tree,
3. ✅ execute that tree against pandas.

## Implementation vs. Sketch Comparison

**What matches the sketch:**
- Hand-written recursive descent parser ✅
- AST-based expression model (ColumnRef, Literal, FunctionCall) ✅
- Column-based vectorized execution ✅
- Pandas Series operations ✅
- No eval() or exec() ✅
- 6 of 7 suggested functions implemented ✅
- Integration with extra_columns deferred evaluation ✅

**Deviations from sketch:**
- **Separate module**: Implemented in `src/transforms/dsl.py` instead of embedding in `extra_columns.py` (cleaner separation)
- **TokenType enum**: Used proper enum instead of string constants for token types
- **ValidationConfig**: Added explicit configuration for max_depth, max_nodes, max_string_length
- **replace() not implemented**: Deferred to future based on user demand
- **Comprehensive tests**: 73 tests (sketch suggested ~10 cases) with 91% coverage
- **Position tracking**: Tokenizer tracks line/column for better error messages

See [tests/transforms/README_DSL_TESTS.md](../../tests/transforms/README_DSL_TESTS.md) for test coverage details.

## Relationship To Existing Code

The current implementation in [src/transforms/extra_columns.py](src/transforms/extra_columns.py) already supports:

1. constants,
2. direct column copies,
3. interpolated strings,
4. deferred evaluation when dependent columns are not yet available.

That means the DSL should be an extension of the existing evaluator, not a separate parallel subsystem.

Recommended layering:

1. existing constants remain unchanged,
2. existing direct column copies remain unchanged,
3. existing interpolation remains unchanged,
4. strings starting with `=` enter the new DSL path.

## Design Goals

1. Reuse the current `ExtraColumnEvaluator` entry point
2. Keep the DSL syntax independent from pandas internals
3. Execute with vectorized pandas operations wherever possible
4. Integrate with current dependency extraction and deferral logic
5. Produce clear configuration-level error messages
6. Keep the initial helper surface intentionally small

## Non-Goals

1. Add arbitrary Python execution
2. Add arbitrary pandas expression execution
3. Introduce a general-purpose programming language in YAML
4. Rework the entire normalization pipeline
5. Replace `replacements` or `translate`

## Execution Model

### Storage Assumption

Yes, the first implementation should assume pandas is the execution backend.

Reasons:

1. `extra_columns` already receives pandas `DataFrame` objects,
2. the current interpolation path already returns pandas `Series` objects,
3. the relevant tests already exercise this behavior at the pandas level.

However, the DSL should not be defined as "tiny pandas syntax".

It should be defined as a small expression language whose current executor targets pandas.

### Row Based Or Column Based

The DSL should be column-based by default, not row-based.

That means helpers should normally operate on:

1. pandas `Series`,
2. scalar literals,
3. combinations of `Series` and scalar literals.

This is preferred because it:

1. matches pandas naturally,
2. is more efficient than `axis=1` row loops,
3. makes null behavior more consistent,
4. fits the conceptual model of "derive a column" rather than "run code for each row".

Row-based execution should be treated as a special-case fallback only.

## Implemented Syntax Scope

The implemented syntax stays narrow as recommended:

```yaml
extra_columns:
  fullname: "=concat(first_name, ' ', last_name)"
  initials: "=concat(upper(substr(first_name, 0, 1)), upper(substr(last_name, 0, 1)))"
  normalized_code: "=upper(trim(code))"
  label: "=coalesce(display_name, concat(site_name, ' (', country, ')'), 'Unknown')"
```

Implemented grammar supports:

1. ✅ identifiers such as `first_name`
2. ✅ string literals such as `'Unknown'` (supports both single and double quotes)
3. ✅ numeric literals such as `0`, `1`, `10`
4. ✅ boolean literals: `null`, `true`, `false`
5. ✅ function calls such as `upper(code)`
6. ✅ nested function calls

Implemented grammar does not support (as recommended):

1. ❌ infix arithmetic
2. ❌ arbitrary operators
3. ❌ member access
4. ❌ indexing syntax
5. ❌ lambdas
6. ❌ raw pandas expressions

## Implemented Internal Types

Actual internal expression model (from [src/transforms/dsl.py](../../src/transforms/dsl.py)):

```python
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ExprNode:
    pass


@dataclass(frozen=True, slots=True)
class ColumnRef(ExprNode):
    name: str


@dataclass(frozen=True, slots=True)
class Literal(ExprNode):
    value: Any


@dataclass(frozen=True, slots=True)
class FunctionCall(ExprNode):
    name: str
    args: tuple[ExprNode, ...]
```

These nodes proved sufficient for the initial DSL. The actual implementation matches this design exactly.

## Implemented Supporting Types

Actual runtime context (from [src/transforms/dsl.py](../../src/transforms/dsl.py)):

```python
from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True, slots=True)
class DslEvaluationContext:
    df: pd.DataFrame
    entity_name: str
    expression_name: str


@dataclass(frozen=True, slots=True)
class DslFunctionSpec:
    name: str
    min_args: int
    max_args: int | None
```

Actual exception hierarchy:

```python
class DslError(ValueError):
    pass


class DslParseError(DslError):
    pass


class DslUnknownFunctionError(DslError):
    pass


class DslMissingColumnError(DslError):
    pass


class DslArgumentError(DslError):
    pass
```

## Implemented Architecture

The implementation chose a **separate module** approach instead of extending extra_columns.py directly. This provides better separation of concerns.

**Actual implementation** in [src/transforms/dsl.py](../../src/transforms/dsl.py):

```python
# Tokenizer - lexical analysis
class Tokenizer:
    def tokenize(self, text: str) -> list[Token]: ...

# Parser - syntax analysis
class Parser:
    def parse(self, text: str) -> ExprNode: ...
    def parse_expr(self) -> ExprNode: ...
    def parse_function_call(self, name: str) -> FunctionCall: ...
    def parse_literal(self) -> Literal: ...

# Validator - semantic analysis
class Validator:
    def validate(
        self,
        node: ExprNode,
        available_columns: set[str],
        config: ValidationConfig,
    ) -> None: ...

# Backend - execution engine
class PandasStringBackend:
    def evaluate(self, node: ExprNode, df: pd.DataFrame) -> pd.Series | Any: ...

# High-level API
class FormulaEngine:
    def __init__(self, validation_config: ValidationConfig | None = None): ...
    def parse_and_validate(
        self,
        formula: str,
        available_columns: set[str],
    ) -> ExprNode: ...
    def apply_extra_columns(
        self,
        df: pd.DataFrame,
        formulas: dict[str, str],
    ) -> pd.DataFrame: ...
```

**Integration point** in [src/transforms/extra_columns.py](../../src/transforms/extra_columns.py):

```python
from src.transforms.dsl import FormulaEngine

class ExtraColumnEvaluator:
    def __init__(self):
        self.formula_engine = FormulaEngine()
    
    def evaluate_extra_columns(self, df: pd.DataFrame, extra_columns: dict) -> pd.DataFrame:
        # Separate DSL formulas (starting with '=') from other types
        formulas = {k: v[1:] for k, v in extra_columns.items() if isinstance(v, str) and v.startswith('=')}
        # Apply formulas via FormulaEngine
        if formulas:
            df = self.formula_engine.apply_extra_columns(df, formulas)
        # ... handle other extra_column types ...
```

The separate module approach (`src/transforms/dsl.py`) proved cleaner than embedding in extra_columns.py.

## Implemented Parser Strategy

✅ **Implemented**: Small hand-written recursive-descent parser in [src/transforms/dsl.py](../../src/transforms/dsl.py)

Reasons (validated):

1. ✅ the grammar is intentionally tiny,
2. ✅ dependencies are low (zero external dependencies),
3. ✅ error messages are tailored to YAML users,
4. ✅ avoids parser-generator complexity.

Actual parse flow:

1. ✅ strip the leading `=` (handled by FormulaEngine)
2. ✅ tokenize identifiers, strings, numbers, commas, and parentheses
3. ✅ parse either:
   - literal (null, true, false, string, number),
   - column reference,
   - function call
4. ✅ require end-of-input after parsing

Implemented token types (from `TokenType` enum):

1. ✅ `NAME` (instead of IDENT - more accurate for identifiers and function names)
2. ✅ `STRING`
3. ✅ `INTEGER` (instead of NUMBER - currently only integers supported)
4. ✅ `LPAREN`
5. ✅ `RPAREN`
6. ✅ `COMMA`
7. ✅ `EQUAL` (for potential future use)
8. ✅ `EOF`

Additional features:
- Position tracking (line, column) for better error messages
- Support for both single and double quoted strings
- Reserved word handling (null, true, false)

## Implemented Dependency Extraction

✅ **Implemented**: Dependency extraction happens from the AST, not from string heuristics.

Actual implementation:

```python
def extract_column_references(node: ExprNode) -> set[str]:
    """Extract all column references from an AST."""
    if isinstance(node, ColumnRef):
        return {node.name}
    elif isinstance(node, Literal):
        return set()
    elif isinstance(node, FunctionCall):
        refs = set()
        for arg in node.args:
            refs.update(extract_column_references(arg))
        return refs
    return set()
```

Behavior (matches sketch exactly):

1. ✅ `ColumnRef("first_name")` contributes `first_name`
2. ✅ `Literal("Unknown")` contributes nothing
3. ✅ `FunctionCall(...)` contributes dependencies from all child nodes

This allows the DSL to integrate cleanly with the existing deferred-evaluation model in extra_columns.py.

## Implemented Evaluation Semantics

✅ **Implemented**: Each AST node evaluates to either:

1. ✅ a scalar literal, or
2. ✅ a pandas `Series`.

Function implementations accept a mix of scalar and `Series` inputs and normalize them as needed (via `to_series()` helper).

### Implemented Helper Semantics

#### `concat(...)` ✅ Implemented

Purpose:

1. join a list of values into one string result per row

Actual behavior:

1. ✅ cast non-null values to string
2. ✅ treat null as empty string
3. ✅ return `Series`

#### `upper(value)` and `lower(value)` ✅ Implemented

Purpose:

1. case normalization

Actual behavior:

1. ✅ operate on `Series.astype("string")`
2. ✅ preserve nulls (nulls propagate through)

#### `trim(value)` ✅ Implemented

Purpose:

1. whitespace normalization

Actual behavior:

1. ✅ apply string strip operation (`str.strip()`)
2. ✅ preserve nulls (nulls propagate through)

#### `substr(value, start, length)` ✅ Implemented

Purpose:

1. substring extraction

Actual behavior:

1. ✅ use pandas string slicing (`str[start:start+length]`)
2. ✅ support integer start and length only
3. ✅ preserve nulls (nulls propagate through)

#### `coalesce(a, b, ...)` ✅ Implemented

Purpose:

1. first non-null value wins

Actual behavior:

1. ✅ evaluate all args
2. ✅ combine left-to-right using `fillna`
3. ✅ short-circuits once a non-null value is found per row

#### `replace(value, from, to)` ❌ Not Yet Implemented

Purpose:

1. string substitution inside a derived expression

Status: Deferred to future based on user demand. Can be added later if needed.

## Implemented Null Handling

✅ Null behavior is explicit and documented.

Actual implemented rules:

1. ✅ `concat(...)`: null -> empty string
2. ✅ `upper/lower/trim/substr`: preserve nulls (pd.NA propagation)
3. ✅ `coalesce(...)`: first non-null wins
4. ✅ string literals are never null
5. ✅ boolean literals include explicit `null` keyword

This has been tested explicitly in [tests/transforms/test_dsl.py](../../tests/transforms/test_dsl.py) (see TestPandasStringBackend test class).

## Integration With Existing evaluate_extra_columns

Suggested processing order inside `evaluate_extra_columns(...)`:

1. skip already-existing output columns
2. non-string constants
3. DSL expressions starting with `=`
4. interpolated strings using `{column}`
5. case-insensitive direct column copies
6. string constants

Recommended reason for putting DSL before interpolation:

1. `=` is an explicit marker and unambiguous
2. interpolation remains a plain-string feature

Pseudo-flow:

```python
if self.is_dsl_expression(value):
    ast = self.parse_dsl_expression(value)
    dependencies = self.extract_dsl_dependencies(ast)
    missing = set(dependencies) - set(result.columns)
    if missing and defer_missing:
        deferred[new_col] = value
        continue
    if missing:
        raise DslMissingColumnError(...)
    result[new_col] = self.evaluate_dsl_ast(ast, ctx)
    continue
```

## Validation And Errors

Validation errors should be configuration-oriented, not parser-internal.

Good examples:

1. `person[extra_columns]: fullname: unknown function 'concat_ws'`
2. `person[extra_columns]: initials: column not found: 'middle_name'`
3. `person[extra_columns]: label: substr() expects 3 arguments`
4. `person[extra_columns]: code: unexpected token ')'`

Bad examples:

1. raw Python tracebacks
2. pandas internal expression errors
3. generic `SyntaxError` without expression context

## Implemented Test Plan

✅ **73 comprehensive tests** implemented in [tests/transforms/test_dsl.py](../../tests/transforms/test_dsl.py) with **91.39% code coverage**.

Test categories:

1. **TestTokenizer** (10 tests) - Lexical analysis
   - Token recognition
   - Position tracking
   - Error handling
   - Edge cases (unicode, empty strings)

2. **TestParser** (17 tests) - Syntax analysis
   - Function calls
   - Nested expressions
   - Literals (null, true, false, strings, numbers)
   - Column references
   - Error cases

3. **TestValidator** (8 tests) - Semantic analysis
   - Column validation
   - Function whitelist enforcement
   - Complexity limits (depth, node count)
   - String length limits

4. **TestPandasStringBackend** (18 tests) - Function evaluation
   - ✅ All 6 functions tested
   - ✅ Null handling for each function
   - ✅ Type coercion
   - ✅ Edge cases

5. **TestFormulaEngine** (7 tests) - Integration
   - ✅ End-to-end parsing and evaluation
   - ✅ `apply_extra_columns()` integration
   - ✅ Multiple formulas

6. **TestEdgeCases** (13 tests) - Boundary conditions
   - ✅ Unicode support
   - ✅ Empty strings
   - ✅ Case sensitivity
   - ✅ Whitespace handling

Suggested cases (coverage):

1. ✅ simple `concat(...)`
2. ✅ nested `upper(substr(...))`
3. ✅ `coalesce(...)` with nulls
4. ❌ `replace(trim(...), ' ', '_')` - replace() not implemented
5. ✅ literal-only expression
6. ✅ mixed scalar and column arguments
7. ✅ missing dependency deferred (via extra_columns.py integration)
8. ✅ missing dependency error (validator test)
9. ✅ unknown helper name
10. ✅ malformed expression

See [tests/transforms/README_DSL_TESTS.md](../../tests/transforms/README_DSL_TESTS.md) for detailed coverage breakdown.

## Actual Implementation Order (Completed)

1. ✅ added AST types (`ExprNode`, `ColumnRef`, `Literal`, `FunctionCall`)
2. ✅ added `Tokenizer` class with position tracking
3. ✅ added `Parser` class (recursive descent)
4. ✅ added `Validator` class with complexity limits
5. ✅ added `PandasStringBackend` evaluator for 6 functions:
   - ✅ `concat`, `upper`, `lower`, `trim`, `substr`, `coalesce`
6. ✅ added `FormulaEngine` high-level API
7. ✅ integrated with `extra_columns.py` (via `apply_extra_columns`)
8. ✅ added 73 comprehensive tests
9. ✅ added documentation in CONFIGURATION_GUIDE.md
10. ✅ added extensibility guide (../../other/DSL_EXTENSIBILITY_GUIDE.md)
11. ✅ added parser comparison doc (DSL_PARSER_COMPARISON.md)

## Implemented Boundaries For Phase 1

To keep the first version low risk, Phase 1 did not include:

1. ❌ boolean conditions (can be added later)
2. ❌ comparison operators (can be added later)
3. ❌ numeric arithmetic (can be added later)
4. ❌ user-defined functions (intentionally excluded for security)
5. ✅ **NO** raw expression escape hatches (security requirement met)
6. ❌ SQL-specific helpers (can be added later)

**Phase 1 successfully proved** that Shape Shifter can support safe, readable, cross-entity derived-value transforms in `extra_columns`.

For adding new features, see [docs/other/DSL_EXTENSIBILITY_GUIDE.md](../../other/DSL_EXTENSIBILITY_GUIDE.md).

## Conclusion

✅ **Implementation completed successfully** following the recommended path:

1. ✅ Created separate module [src/transforms/dsl.py](../../src/transforms/dsl.py) (cleaner than embedding in extra_columns.py)
2. ✅ Assumes pandas as the execution backend
3. ✅ Evaluates expressions as vectorized column operations
4. ✅ Integrates with the current deferred-evaluation model
5. ✅ Keeps the DSL narrow and intentionally non-Turing-complete

**Results:**
- 821 lines of production code
- 73 comprehensive tests
- 91.39% code coverage
- Zero external dependencies (stdlib + pandas only)
- No eval() or exec() usage
- Clean separation of concerns (tokenizer, parser, validator, backend)
- Extensible design for future enhancements

The implementation fits the current codebase, preserves existing `extra_columns` behavior, and aligns with the broader ergonomics direction in [docs/proposals/COMPLEX_ENTITY_MODELING_ERGONOMICS.md](docs/proposals/COMPLEX_ENTITY_MODELING_ERGONOMICS.md).

**Next steps** for future enhancements:
- Add `replace()` function if user demand emerges
- Add conditional expressions (`if()`) if use cases appear
- Add numeric arithmetic if needed
- Enhance error messages with more context
- Add syntax highlighting in web editor
