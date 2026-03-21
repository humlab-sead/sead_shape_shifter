# Tiny DSL For Derived Values In extra_columns

## Status

**✅ Implemented** (March 2026)

- Scope: configuration ergonomics for derived values in `extra_columns`
- Goal: extend the current interpolation-based `extra_columns` feature with a small, safe expression language for common transforms
- Relationship to Proposal 3: this is a concrete follow-on to Proposal 3 in [docs/proposals/COMPLEX_ENTITY_MODELING_ERGONOMICS.md](docs/proposals/COMPLEX_ENTITY_MODELING_ERGONOMICS.md), not as a competing feature
- **Implementation**: Hand-written recursive descent parser in [src/transforms/dsl.py](../../src/transforms/dsl.py)
- **Tests**: 73 comprehensive tests in [tests/transforms/test_dsl.py](../../tests/transforms/test_dsl.py) with 91% coverage
- **Documentation**: DSL syntax documented in [docs/CONFIGURATION_GUIDE.md](../CONFIGURATION_GUIDE.md)

## Summary

Shape Shifter already supports useful derived-value behavior in `extra_columns`.

Today, authors can already express:

1. constants,
2. direct column copies,
3. interpolated strings such as `"{first_name} {last_name}"`,
4. deferred evaluation when referenced columns are only available later in the pipeline.

That means many practical cases are already solved without any new syntax.

The remaining gap is not basic derivation. The gap is that interpolation becomes awkward as soon as authors need lightweight transforms such as:

1. uppercasing,
2. trimming,
3. substring extraction,
4. null coalescing,
5. simple conditional formatting,
6. safe concatenation without hand-encoding every case in SQL.

This proposal recommended introducing a tiny DSL for derived values in `extra_columns`, but only as a small, explicit, safe vocabulary. **This has now been implemented.**

The implementation aligns with Proposal 3 by treating:

1. current interpolated `extra_columns` as the baseline feature,
2. the tiny DSL as the next ergonomics layer above interpolation,
3. arbitrary Python or pandas `eval` expressions as out of scope.

## Why This Matters

Today, authors often have three imperfect options when interpolation is not enough:

1. push the logic down into SQL,
2. create staging columns solely to simplify later interpolation,
3. request a richer feature even when the required transform is conceptually small.

That creates avoidable friction.

For example, building a synthetic identity or label may need only a small amount of logic:

```yaml
extra_columns:
  analysis_entity_value: "{PCODE}|{Fraktion}|{cf}|{RTyp}|{Zust}"
```

That already works well.

But common follow-on cases are harder to express cleanly:

```yaml
extra_columns:
  fullname: "{first_name} {last_name}"
  initials: ???
  normalized_code: ???
  display_name: ???
```

If the only answer is "write more SQL" or "add a future SQL-only computed-columns feature," then the cross-entity value of `extra_columns` is underused.

## Current State

The current implementation in [src/transforms/extra_columns.py](src/transforms/extra_columns.py) already supports:

1. constants,
2. direct column copies,
3. interpolated strings with `{column_name}` placeholders,
4. escaped braces,
5. null-safe evaluation,
6. deferred evaluation when required columns are introduced later.

This is important because it changes the framing of the proposal.

The proposal should not say "Shape Shifter needs expressions in `extra_columns` from scratch."

The correct framing is:

1. `extra_columns` already provides a cross-entity derived-value mechanism,
2. documentation and discoverability have lagged behind implementation,
3. the next useful step is a small transform DSL layered on top of the existing feature.

## Relation To Existing Features

This proposal should be understood relative to two existing transformation mechanisms that already exist in Shape Shifter.

### `translate`

The existing `translate` step is a column-name translation mechanism.

In [src/transforms/translate.py](src/transforms/translate.py), Shape Shifter applies a lookup map to rename columns such as:

1. source column name A -> target column name B,
2. source column name C -> target column name D.

That is useful, but it is not a derived-value feature.

It does not:

1. create new columns from existing values,
2. transform a value like `"abc"` into `"ABC"`,
3. combine multiple columns into one label,
4. apply string functions such as trim, substring, or coalesce.

So the tiny DSL is not a replacement for `translate`. It operates at a different level:

1. `translate` renames columns,
2. the tiny DSL derives new column values.

### `replacements`

The existing `replacements` feature is closer in spirit, but still solves a narrower problem.

As implemented in [src/transforms/replace.py](src/transforms/replace.py) and documented in [docs/CONFIGURATION_GUIDE.md](docs/CONFIGURATION_GUIDE.md), `replacements` is primarily a value-normalization and find-and-replace mechanism.

It is useful for things like:

1. mapping one known value to another,
2. blanking or filling specific values,
3. applying rule-based normalization to values already present in a column.

But `replacements` still operates on an existing column value rather than expressing a derived value from multiple inputs.

For example, `replacements` is a good fit for:

1. `"DHDN Zone 3" -> "EPSG:31467"`,
2. normalizing a code list,
3. correcting known legacy values.

It is not the natural place for:

1. `fullname = concat(first_name, ' ', last_name)`,
2. `initials = concat(upper(substr(first_name, 0, 1)), upper(substr(last_name, 0, 1)))`,
3. `label = coalesce(display_name, concat(site_name, ' (', country, ')'), 'Unknown')`.

So the intended separation is:

1. `translate` for renaming columns,
2. `replacements` for replacing or normalizing existing values,
3. `extra_columns` plus a tiny DSL for deriving new values.

That separation keeps each feature conceptually narrow instead of overloading one mechanism to do three different jobs.

## Problem

Interpolation is intentionally simple, but there is a usability cliff between:

1. values that are expressible as constants or `{column}` interpolation,
2. values that require even a modest transform.

That cliff creates several problems:

1. authors must fall back to SQL for transforms that are conceptually configuration-level,
2. cross-entity derived-value workflows become uneven because SQL-heavy solutions only help SQL-backed entities,
3. more logic gets duplicated across queries instead of living in the normalization configuration,
4. the temptation grows to introduce unsafe raw-expression escape hatches,
5. the feature becomes harder to validate and preview consistently.

## Goals

1. Keep `extra_columns` usable across all entity types
2. Add a small amount of expression power for common transforms
3. Preserve the current interpolation syntax as the simplest path
4. Keep the feature safe, explicit, and predictable
5. Make derived values easier to validate, preview, and document

## Non-Goals

1. Replace the current interpolation-based `extra_columns` behavior
2. Introduce arbitrary Python execution
3. Introduce arbitrary pandas execution
4. Turn `extra_columns` into a general-purpose programming language
5. Make this SQL-only

## Implementation Summary

**This proposal has been implemented as of March 2026.**

The implementation follows the recommendations from Proposal 3:

1. ✅ Plain interpolation remains exactly as it was
2. ✅ Tiny DSL marker (`=`) added for friendly derived expressions
3. ✅ DSL compiles into a safe internal transform plan (AST-based)
4. ✅ Only whitelisted operations are evaluated (6 functions)
5. ✅ No raw `expr:` or raw `eval` exposure

### Implementation Architecture

**Parser**: Hand-written recursive descent parser in [src/transforms/dsl.py](../../src/transforms/dsl.py) (821 lines)
- Zero dependencies beyond Python stdlib + pandas
- 4 production rules, 7 token types
- Builds typed AST (Abstract Syntax Tree)

**Security**:
- No eval() or exec() usage
- Whitelisted function set only
- Bounded complexity (max_depth=20, max_nodes=500)
- Validated column references

**Backend**: PandasStringBackend with vectorized Series operations
- All functions implemented as safe pandas operations
- Proper null handling (pd.NA propagation)
- Type-safe execution

**Testing**: 73 comprehensive tests with 91.39% coverage
- See [tests/transforms/test_dsl.py](../../tests/transforms/test_dsl.py)
- See [tests/transforms/README_DSL_TESTS.md](../../tests/transforms/README_DSL_TESTS.md)

For extensibility guide, see [docs/proposals/DSL_EXTENSIBILITY_GUIDE.md](DSL_EXTENSIBILITY_GUIDE.md).

## Proposed Syntax

Recommended shape:

```yaml
extra_columns:
  fullname: "=concat(first_name, ' ', last_name)"
  initials: "=concat(upper(substr(first_name, 0, 1)), upper(substr(last_name, 0, 1)))"
  normalized_code: "=upper(trim(code))"
  display_name: "=coalesce(site_name, fallback_name, 'Unknown site')"
```

Interpretation rules:

1. non-string values remain constants,
2. plain strings with no DSL marker continue to behave exactly as today,
3. interpolated strings like `"{first} {last}"` continue to work exactly as today,
4. strings starting with `=` are parsed as tiny-DSL expressions.

This keeps the progression simple:

1. constant,
2. copy,
3. interpolation,
4. DSL expression.

## Implemented Function Set

The initial implementation includes 6 whitelisted functions:

1. ✅ `concat(...)` - Concatenate multiple values
2. ✅ `upper(value)` - Convert to uppercase
3. ✅ `lower(value)` - Convert to lowercase  
4. ✅ `trim(value)` - Remove leading/trailing whitespace
5. ✅ `substr(value, start, length)` - Extract substring
6. ✅ `coalesce(a, b, ...)` - Return first non-null value

**Not yet implemented** (possible later helpers):

1. `replace(value, from, to)` - String replacement
2. `if(condition, when_true, when_false)` - Conditional expression
3. `length(value)` - String length
4. `pad_left(value, width, fill)` - Left padding
5. `pad_right(value, width, fill)` - Right padding
6. basic numeric casts if a real use case appears

The initial function set favors string manipulation because that is the most common gap between interpolation and SQL.

For complete syntax and examples, see the **DSL Formula Syntax** section in [docs/CONFIGURATION_GUIDE.md](../CONFIGURATION_GUIDE.md).

## Why Not Raw expr: Or eval

The older notes suggested two escape hatches:

1. `expr:...` for raw pandas expressions,
2. restricted `eval(...)` with a safe namespace.

That is not the direction this proposal should recommend.

Reasons:

1. it expands the attack surface unnecessarily,
2. it complicates debugging and validation,
3. it creates inconsistent semantics across entity types,
4. it encourages power-user shortcuts instead of a stable configuration language,
5. it overlaps poorly with the more deliberate direction in Proposal 3.

If richer, engine-specific expressions are ever needed later, that should be a separate feature with its own execution model and validation rules.

## Expected Behavior

If implemented, the tiny DSL should behave as follows:

1. it runs within the existing `extra_columns` phase rather than introducing a new high-level section,
2. it remains available to any entity type that can already use `extra_columns`,
3. it can participate in deferred evaluation when referenced columns are not yet available,
4. it reports clear validation errors for unknown functions, missing columns, and invalid argument counts,
5. previews should show resolved values the same way current interpolation does,
6. errors should point to the specific `extra_columns.<name>` entry that failed.

## Implementation Phases (Completed)

### Phase 1: Formalize Current Capability ✅

**Completed**:

1. ✅ Current interpolation implementation remains the baseline
2. ✅ Documentation describes constants, copies, interpolation, and deferred evaluation
3. ✅ Validation messages are consistent

The interpolation baseline is preserved and documented.

### Phase 2: Add A Small Parser ✅

**Completed**: Parser for strings beginning with `=` implemented in [src/transforms/dsl.py](../../src/transforms/dsl.py)

The parser:

1. ✅ Parses a tiny function-call grammar
2. ✅ Distinguishes identifiers from string literals (supports both single and double quotes)
3. ✅ Builds an internal AST (typed nodes: FunctionCall, ColumnRef, Literal)
4. ✅ Rejects unsupported syntax early with clear error messages

This is a real recursive descent parser for a narrow grammar, not ad hoc string replacement.

### Phase 3: Compile To Safe Operations ✅

**Completed**: Compiled expressions execute via PandasStringBackend

The implementation:

1. ✅ Does not compile to arbitrary Python source
2. ✅ Does not pass generated source into `eval`
3. ✅ Maps each DSL helper to a known pandas Series operation

All operations are safe, type-checked, and vectorized.

### Phase 4: Integrate With Deferred Evaluation ✅

**Completed**: DSL expressions can reference columns added later in the pipeline

The deferred-evaluation flow is preserved for DSL expressions, maintaining one of the strongest properties of `extra_columns`.

### Phase 5: Validation, Preview, And Tests ✅

**Completed**: Comprehensive test suite with 91% coverage

Tests cover:

1. ✅ Constants
2. ✅ Direct column copies
3. ✅ Interpolation
4. ✅ DSL expressions
5. ✅ Mixed scenarios
6. ✅ Deferred evaluation (via extra_columns.py integration)
7. ✅ Invalid syntax
8. ✅ Unknown helper names
9. ✅ Missing columns

See [tests/transforms/test_dsl.py](../../tests/transforms/test_dsl.py) for details.

## Example Transformations

Examples that justify the DSL without making it overly broad:

```yaml
extra_columns:
  fullname: "=concat(first_name, ' ', last_name)"
  initials: "=concat(upper(substr(first_name, 0, 1)), upper(substr(last_name, 0, 1)))"
  normalized_site_code: "=upper(replace(trim(site_code), ' ', '_'))"
  label: "=coalesce(display_name, concat(site_name, ' (', country, ')'), 'Unknown')"
```

These are precisely the kinds of transforms that exceed simple interpolation, but are too small and routine to justify either arbitrary expression execution or pushing the logic down into entity-specific SQL.

## Tradeoffs

Benefits:

1. improves derived-value ergonomics without abandoning the current model,
2. remains cross-entity rather than SQL-only,
3. reduces unnecessary SQL complexity for small transforms,
4. keeps the feature auditable and validation-friendly.

Costs:

1. introduces a small parser and evaluator to maintain,
2. requires careful error design,
3. needs clear documentation so users know when to use interpolation versus the DSL,
4. may still leave some advanced users wanting richer logic.

That tradeoff is acceptable if the scope stays small.

## Recommendation To Align With Proposal 3

This document should be treated as a concrete refinement of Proposal 3 rather than a separate strategic direction.

Recommended alignment:

1. Proposal 3 remains the umbrella statement about derived-value ergonomics,
2. this proposal becomes the specific implementation candidate for the cross-entity path under Proposal 3,
3. any future SQL-only `computed_columns` feature should remain a separate question,
4. this proposal should not reintroduce raw-expression execution as the default path.

In short:

1. Proposal 3 says what direction to go,
2. this proposal says how to make the cross-entity part of that direction concrete.

## Next Steps

**Implementation is complete.** Future enhancements could include:

1. **Additional functions**: Consider adding `replace()`, `if()`, `length()`, `pad_left()`, `pad_right()` based on user demand
2. **Performance optimization**: Profile and optimize hot paths if needed at scale
3. **Enhanced error messages**: Add more context to syntax error messages (e.g., show column of error)
4. **Editor support**: Consider adding syntax highlighting for DSL formulas in the web editor
5. **Documentation examples**: Expand the CONFIGURATION_GUIDE with more real-world examples

For extending the DSL with new functions or expression types, see [docs/proposals/DSL_EXTENSIBILITY_GUIDE.md](DSL_EXTENSIBILITY_GUIDE.md).
