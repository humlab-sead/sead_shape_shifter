# Query Filter Engine Selection

## Status

- Deferred proposal (future)
- Scope: `type: query` filter schema, runtime call path, validation, docs, filter editor
- Goal: make pandas query-engine choice explicit when needed, without enabling arbitrary code execution

## Summary

This proposal recommends a narrow extension to `type: query` filters:

- add an optional `engine` field,
- support `engine: python` explicitly,
- keep current behavior unchanged when `engine` is omitted,
- reject inline mini-language patterns such as `query: "python:..."`.

This is a reproducibility and control feature, not a broad new query language.

## Problem

Current behavior in [src/transforms/filter.py](src/transforms/filter.py) calls:

```python
df.query(query)
```

That works for many expressions, but the config cannot explicitly request pandas `engine="python"` in environments where a different engine path is selected or enforced.

## Scope

- Add optional `engine` on `type: query` filters
- Validate allowed values
- Pass configured engine to `DataFrame.query(...)`
- Expose the field through filter schema API and editor metadata
- Document semantics and safety constraints

## Non-Goals

- Arbitrary Python execution from project config
- Prefix-based syntax (`python:...`, `python/...`) embedded inside `query`
- General expression engine design beyond pandas query
- Changes to non-query filter types

## Current Behavior

- Query filters are schema-driven and currently expose only `query` (see [src/transforms/filter.py](src/transforms/filter.py) and [src/transforms/filter_metadata.py](src/transforms/filter_metadata.py)).
- Runtime delegates query parsing and execution to pandas.

## Proposed Design

### Configuration shape

```yaml
filters:
  - type: query
    stage: after_unnest
    engine: python
    query: "value_name.str.contains('ph|loi', na=False)"
```

### Allowed values

Initial recommendation:

- support only `python` as an explicit value,
- treat omitted `engine` as current default behavior.

Rationale: this keeps the feature narrow and directly targets the portability/reproducibility gap without expanding surface area unnecessarily.

### Runtime behavior

Conceptual change:

```python
engine = filter_cfg.get("engine")
if engine:
    filtered_df = df.query(query, engine=engine)
else:
    filtered_df = df.query(query)
```

## Evidence Case (Failing Before / Passing After)

This proposal should only proceed with at least one concrete test case proving value.

Candidate case:

- expression: `"value_name.str.contains('ph|loi', na=False)"`
- forced numexpr path fails for this expression category,
- python engine path succeeds.

In this workspace, a direct pandas check confirms:

- `df.query(expr, engine="numexpr")` fails,
- `df.query(expr, engine="python")` succeeds.

Before this feature, users cannot request `engine: python` from YAML and must rely on environment-dependent defaults.

## Validation And UI Impact

- Extend `query` filter schema metadata with optional `engine`.
- Backend/API should reject unsupported engine values with explicit errors.
- Frontend filter editor can show `engine` as optional select/help text.

## Security And Safety

`engine: python` means pandas query evaluation with pandas' `python` engine.

It does **not** mean arbitrary Python execution from config. This proposal does not introduce `eval`, script hooks, or unrestricted runtime code paths.

## Risks And Tradeoffs

- Small schema/runtime increase for a narrow use case
- Need clear docs to prevent confusion between pandas engine selection and code execution
- Behavior can still vary with pandas version, so tests should pin expectations for selected expressions

## Testing And Validation

### Unit tests

- query filter accepts `engine: python`
- unsupported engine values fail validation
- omitted engine preserves current behavior

### Regression test (required)

- one concrete failing-before/passing-after expression case must be captured
- test should demonstrate why explicit `engine: python` is needed

### API/UI tests

- filter type metadata includes optional `engine`
- editor can round-trip `engine` without mutating `query`

## Acceptance Criteria

- [ ] `type: query` supports optional `engine`
- [ ] `engine: python` is passed to pandas query runtime
- [ ] unsupported engine values fail clearly
- [ ] one concrete failing-before/passing-after test case is included
- [ ] docs state clearly that this is pandas engine selection, not arbitrary code execution

## Final Recommendation

Worth pursuing as a small, low-risk future enhancement if the concrete failing-before/passing-after test remains reproducible across supported environments.

If that evidence cannot be maintained reliably, keep current behavior and drop the proposal.