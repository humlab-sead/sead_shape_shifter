# Staged Filter Execution

## Status

- Proposed feature / change request
- Scope: core filter execution order, config model, validation, documentation, frontend filter editor
- Goal: support filters that depend on columns introduced by unnesting or foreign key linking
- Tracking issues: none yet

## Summary

The current filter feature is intentionally simple: filters run once immediately after extraction and before linking and unnesting.

That makes the feature predictable, but it is too limited for common long-format workflows. In particular, users cannot filter on columns created during unnesting, such as a `Value Name` column produced by melt-style normalization.

This proposal defines a Phase 1 solution only:

1. keep the current `filters` list,
2. add an optional per-filter `stage` field,
3. execute filters in multiple explicit passes during normalization,
4. default filters without `stage` to the current early behavior,
5. add enough validation and UI support to make stage selection understandable.

This solves the immediate unnesting limitation without requiring a broader redesign of the transformation pipeline.

## Decision Summary

The decision in this proposal is to implement a narrow first step: stage-aware filters within the existing `filters` list.

This proposal recommends:

1. approving stage-aware filters as a Phase 1 enhancement,
2. preserving existing behavior by defaulting unspecified filters to the current early stage,
3. using explicit stage selection rather than relying on implicit deferred retry behavior,
4. leaving any broader pipeline redesign as future work outside this document.

### Resolved Decisions

The following design choices are considered settled for this proposal:

1. Filtering on columns created by unnesting is an important supported use case, not an edge case.
2. Execution timing should be explicit in configuration and UI rather than inferred only from missing columns.
3. Backward compatibility for existing `filters` configurations is required.
4. This proposal should align with the current defer/retry design patterns already used for linking and `extra_columns`, but should not copy them as the primary user-facing model.

## Scope

This proposal is in scope for:

1. filters that rely on columns created after extraction,
2. filters that should run after linking or after unnesting,
3. runtime execution changes in [src/normalizer.py](src/normalizer.py),
4. filter config and validation changes in [src/model.py](src/model.py) and related backend models,
5. frontend/editor support for selecting execution stage,
6. documentation updates describing filter timing and column availability.

## Out Of Scope

This proposal is not in scope for:

1. a fully user-orderable transformation pipeline,
2. a complete redesign of all entity transforms into a single generic DSL,
3. an unnest-specific filtering sublanguage,
4. solving every possible post-transform rule problem beyond filtering.

## Problem

### Current Behavior

Filters are applied once, immediately after entity extraction:

- [src/normalizer.py](src/normalizer.py#L156)
- [src/transforms/filter.py](src/transforms/filter.py)
- [docs/CONFIGURATION_GUIDE.md](docs/CONFIGURATION_GUIDE.md#L3073)

The current normalization flow is effectively:

1. extract,
2. filter,
3. deduplicate,
4. link,
5. unnest,
6. relink,
7. later cleanup.

This means filters can only reference columns that already exist immediately after extraction.

### Why This Is A Limitation

Some important columns do not exist until later phases:

1. unnesting creates `var_name` and `value_name` columns,
2. foreign key linking can add local FK columns and extra linked columns,
3. deferred `extra_columns` may only become evaluable after linking or unnesting.

So there are valid filter intents the current system cannot express.

### Concrete Use Case

A single wide source row may contain several value variables that are later transformed into a long representation through unnesting.

Users may want to keep only some of those unnested variable rows, for example by filtering on the generated `Value Name` column.

That is not possible today because the relevant column does not exist when filters run.

## Why Explicit Stages Are Better Than Pure Deferral

Shape Shifter already has defer/retry behavior in two places:

1. foreign key linking can be deferred until required inputs exist in [src/transforms/link.py](src/transforms/link.py),
2. `extra_columns` evaluation can be retried after linking or unnesting in [src/normalizer.py](src/normalizer.py#L238).

That pattern is useful internally, but it is not sufficient as the primary filter model.

Filtering is different from linking because filtering changes row counts and can materially alter downstream behavior. Users need to know when filtering happens, not just that it will happen whenever its inputs become available.

For that reason, deferred execution may still be used internally, but the user-facing design should be explicit stage selection.

## Proposal

Adopt a narrow Phase 1 model: add an optional `stage` field to each filter in the existing `filters` list.

Example shape:

```yaml
filters:
  - type: query
    stage: extract
    query: "sample_code.notnull()"

  - type: query
    stage: after_unnest
    query: "value_name == 'pH'"
```

This proposal deliberately does not introduce:

1. a new filter block structure,
2. a user-orderable pipeline,
3. an unnest-specific filtering mini-language.

The goal is to solve the current limitation with the smallest clear extension to the existing model.

## Proposed Model

### Supported Stages

The initial stage set should be small and explicit:

1. `extract`
2. `after_link`
3. `after_unnest`

Definitions:

1. `extract`: run after extraction and replacement logic, before linking and unnesting.
2. `after_link`: run after the first link pass and deferred `extra_columns` re-evaluation.
3. `after_unnest`: run after unnesting, relinking, and deferred `extra_columns` re-evaluation.

The exact ordering should be documented and treated as stable behavior.

### Default Behavior

If `stage` is omitted, the filter must behave exactly as it does today.

That means:

1. existing projects remain valid,
2. existing projects preserve current behavior,
3. documentation can describe `extract` as the default stage.

### Example Configuration

```yaml
entities:
  measurements:
    columns: [sample_id, ph, loi, conductivity]
    unnest:
      id_vars: [sample_id]
      value_vars: [ph, loi, conductivity]
      var_name: value_name
      value_name: value
    filters:
      - type: query
        stage: after_unnest
        query: "value_name in ['ph', 'loi']"
```

### Query Filter Semantics

This proposal does not require Shape Shifter to parse pandas query expressions in Phase 1.

The `query` filter can keep its current behavior in [src/transforms/filter.py](src/transforms/filter.py):

1. Shape Shifter decides when the filter runs based on `stage`,
2. pandas still evaluates the query string,
3. invalid or impossible query expressions may still fail at runtime.

If stronger pre-runtime validation is needed later, that can be added as follow-up work.

## Runtime Design

The runtime change should be minimal and explicit.

In [src/normalizer.py](src/normalizer.py), normalization should conceptually become:

1. extract entity,
2. run `extract` filters,
3. apply early deduplication only when safe,
4. run first link pass,
5. re-evaluate deferred `extra_columns`,
6. run `after_link` filters,
7. unnest if configured,
8. relink if needed,
9. re-evaluate deferred `extra_columns`,
10. run `after_unnest` filters,
11. apply deferred deduplication,
12. continue with duplicate checks, empty row handling, and identity column handling.

Two constraints matter here:

1. filtering after unnest must happen before any final deduplication that depends on unnested columns,
2. relinking and deferred `extra_columns` re-evaluation must happen before `after_unnest` filters if those filters may reference post-link columns.

## Validation Requirements

Stage-aware filters require stronger validation than the current implementation.

At minimum, validation should check:

1. `stage` is one of the supported values,
2. the selected filter type is supported,
3. the referenced entity exists for cross-entity filters,
4. referenced columns are available at the selected stage,
5. warnings are produced when a filter removes all rows.

Column availability should be stage-aware.

The existing column introspection service already distinguishes:

1. explicit columns,
2. keys,
3. extra columns,
4. unnested columns,
5. foreign key columns,
6. system columns.

Relevant code:

- [backend/app/services/column_introspection_service.py](backend/app/services/column_introspection_service.py)
- [frontend/src/composables/useColumnIntrospection.ts](frontend/src/composables/useColumnIntrospection.ts)

That makes it feasible to drive stage-aware validation and UI guidance without inventing a completely new analysis subsystem.

## Frontend Impact

The filter editor should expose stage as an explicit control.

The UI should:

1. default new filters to `extract`,
2. explain what each stage means,
3. filter or annotate column suggestions by stage,
4. make unnested-only columns visible when `after_unnest` is selected,
5. preserve the current simple experience for users who do not need staged filters.

The filter schema API in [backend/app/api/v1/endpoints/filters.py](backend/app/api/v1/endpoints/filters.py) is already designed to drive dynamic filter forms and can be extended to expose stage metadata if needed.

## Documentation Impact

The filter documentation in [docs/CONFIGURATION_GUIDE.md](docs/CONFIGURATION_GUIDE.md#L3073) currently states that filters run after extraction and before foreign key linking and other transformations.

If this proposal is adopted, the docs must be updated to say:

1. filters can run at multiple defined stages,
2. omitted stage means early execution for backward compatibility,
3. some columns are only available after linking or unnesting,
4. example configurations should show both early and post-unnest filtering.

## Compatibility And Migration

This proposal is designed to be backward compatible.

Compatibility rules:

1. existing `filters` lists remain valid,
2. filters without `stage` behave exactly as they do now,
3. no immediate YAML migration is required,
4. frontend defaults should preserve the current early-stage behavior.

Because this adds new behavior without changing existing defaults, it should be treated as a feature extension rather than a breaking schema change.

## Implementation Notes

If this proposal is approved, the implementation should likely include:

1. adding stage support to the filter config model in core and backend,
2. partitioning filters by stage in [src/transforms/filter.py](src/transforms/filter.py) or a small helper module,
3. updating [src/normalizer.py](src/normalizer.py) to execute filter passes at explicit points,
4. extending validation to understand stage-aware column availability,
5. extending frontend filter editing to expose stage and stage-appropriate column suggestions,
6. updating documentation and examples.

The implementation should avoid scattering stage logic across many components. A small central execution helper is preferable to ad hoc conditionals in multiple places.

## Acceptance Criteria

If this proposal is implemented, the following should hold:

1. an entity can filter on an unnested `var_name` column after unnesting,
2. an entity can filter on columns added by linking when using the appropriate stage,
3. existing filters without explicit stage keep current behavior,
4. validation catches impossible column references for the selected stage,
5. documentation and UI explain filter timing clearly.

## Future Work

Future work may revisit whether the flat-list plus `stage` model should later evolve into a more explicit phased structure.

That question is intentionally out of scope for this proposal. This document only defines the Phase 1 extension described above.