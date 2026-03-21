# Query Filter Engine Selection

## Status

- Proposed feature / change request
- Scope: query filter config model, runtime behavior, validation, documentation, frontend filter editor
- Goal: support advanced pandas query behavior without introducing arbitrary code execution
- Tracking issues: none yet

## Summary

The current `query` filter is already useful and intentionally simple. It delegates directly to pandas `DataFrame.query(...)` and currently assumes the default query engine.

This proposal recommends a small extension: allow users to choose the pandas query engine explicitly through a separate `engine` field.

Recommended shape:

```yaml
filters:
  - type: query
    stage: after_unnest
    engine: python
    query: "value_name.str.contains('ph|loi', na=False)"
```

The proposal explicitly recommends **not** encoding the engine inside the `query` string using forms such as `python:...` or `python/...`.

## Decision Summary

This proposal recommends:

1. keeping `type: query` as a pandas-query-based filter,
2. adding an optional `engine` field with a small allowed value set,
3. treating `engine: python` as pandas `engine="python"`, not arbitrary Python execution,
4. rejecting inline prefixes such as `query: "python:..."` as the primary configuration model,
5. preserving current behavior by default when `engine` is omitted.

## Problem

The current query filter in [src/transforms/filter.py](src/transforms/filter.py) accepts only a single `query` string and passes it to `df.query(query)`.

That works well for simple expressions, but it leaves no clean configuration-level way to request the pandas `python` engine when users need expressions that go beyond the default engine's capabilities.

Users may reasonably want more advanced filtering while staying within the pandas query model.

## Why This Should Not Mean Arbitrary Python

This proposal is only about pandas query engine selection.

It should **not** be interpreted as support for executing arbitrary Python expressions from project configuration.

That distinction matters because arbitrary Python execution would significantly increase:

1. security risk,
2. debugging complexity,
3. validation difficulty,
4. portability concerns,
5. ambiguity about what is and is not supported in project files.

The goal here is a narrow extension to pandas query behavior, not a general code execution feature.

## Why A Separate Field Is Better Than A Prefix

Examples under consideration:

```yaml
query: "python:some expression"
query: "python/some expression"
```

These forms are technically possible, but they are not the best design.

### Problems With Prefix Syntax

1. it hides configuration structure inside a free-text field,
2. it gives one field two meanings,
3. it makes schema-based UI support harder,
4. it makes validation more awkward,
5. it creates a mini-language that must be parsed and documented,
6. it makes future extension less clear if more query options are added later.

### Benefits Of An Explicit Field

An explicit field fits the existing filter architecture better:

```yaml
filters:
  - type: query
    engine: python
    query: "some expression"
```

Benefits:

1. `query` remains only the query expression,
2. the filter schema can describe `engine` cleanly,
3. the frontend editor can render it as a real option,
4. the backend can validate allowed values,
5. documentation remains clearer and more extensible.

## Proposed Model

### Configuration

Extend the `query` filter schema with an optional `engine` field.

Recommended allowed values:

1. `numexpr`
2. `python`

Recommended semantics:

1. if `engine` is omitted, preserve current behavior,
2. if `engine: python`, call pandas query with `engine="python"`,
3. if an unsupported engine is provided, fail validation clearly.

### Example

```yaml
filters:
  - type: query
    engine: python
    query: "value_name.str.contains('ph|loi', na=False)"
```

## Runtime Direction

The runtime change in [src/transforms/filter.py](src/transforms/filter.py) should stay minimal.

Conceptually:

```python
engine = filter_cfg.get("engine")
if engine:
    filtered_df = df.query(query, engine=engine)
else:
    filtered_df = df.query(query)
```

This keeps the feature aligned with the current implementation style.

## Validation And UI Impact

This proposal fits the current schema-driven filter system:

- runtime filter schema in [src/transforms/filter_metadata.py](src/transforms/filter_metadata.py)
- API schema exposure in [backend/app/api/v1/endpoints/filters.py](backend/app/api/v1/endpoints/filters.py)
- frontend filter editor generation from schema metadata

Because of that architecture, an explicit `engine` field is the natural extension point.

If desired, the UI can present the field as an optional select with a short help text such as:

- `numexpr`: default, simpler and often faster
- `python`: more flexible, advanced usage

## Documentation Impact

If approved, the docs should state clearly that:

1. `query` filters still use pandas query syntax,
2. `engine: python` means pandas query with the python engine,
3. this is not arbitrary Python execution,
4. the feature is intended for advanced filtering only.

## Recommendation

Approve a narrow enhancement:

1. add optional `engine` to `type: query`,
2. restrict it to pandas-supported engine values,
3. keep default behavior unchanged,
4. reject prefix-based syntax as the primary model.

## Conclusion

The best extension is not `query: "python:..."`. The best extension is an explicit `engine` field.

That keeps the model clearer, safer, easier to validate, and more consistent with Shape Shifter's schema-driven configuration design.
