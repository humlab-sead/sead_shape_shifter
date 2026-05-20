# Configurable Fixed-Entity Type Conventions

## Status

- Proposed feature / change request
- Scope: Project-level configuration for implicit fixed-entity column typing
- Goal: Allow projects to define reusable column-type conventions without weakening explicit `column_types` or reintroducing recent runtime regressions

## Summary

This proposal adds project-level configurable type conventions for fixed entities. Today the system already has one built-in convention: columns ending with `_id` default to `int`. That works for foreign keys, but it is hardcoded and cannot express other stable project-specific defaults.

The recommendation is to add ordered project-level conventions for fixed entities only. These conventions act as implicit defaults, not as a replacement for per-entity `column_types`. Precedence remains explicit: `column_types` wins, then project conventions, then the built-in `_id -> int` fallback.

This should be implemented in a way that preserves the recent regression fix: undeclared non-`_id` columns must continue to preserve incoming scalar values unless a project convention or explicit `column_types` declaration says otherwise.

## Problem

Fixed-entity typing currently has two extremes:

- `_id` columns get a built-in convention and strict runtime handling.
- Other columns rely on per-entity `column_types` if a project wants deterministic typing.

That leaves a gap for repeated project-wide patterns such as:

- columns named `abundance` should be integers
- columns ending with `_uuid` should be strings
- other stable naming conventions shared across many fixed entities

Without project-level conventions, teams must repeat the same `column_types` declarations across multiple entities or rely on loose undeclared behavior. That increases duplication and makes type intent harder to maintain.

## Scope

This proposal covers:

- a project-level YAML configuration surface for fixed-entity type conventions
- ordered rule matching with deterministic precedence
- interaction with existing `column_types`
- clear separation between implicit defaults and strict runtime enforcement
- validation rules for convention entries

## Non-Goals

- creating a generic type-convention system for the whole project model
- adding regex-based matching in the first version
- replacing explicit `column_types`
- automatic type inference from observed values
- frontend authoring UX for editing conventions in this iteration

## Current Behavior

Current fixed-entity typing behavior is split across three layers:

- `column_types` provides explicit per-entity typing when declared
- built-in convention infers `*_id` as `int`
- undeclared non-`_id` columns preserve their scalar values at runtime after the recent merged-entity regression fix

This means the system already supports the idea of conventions, but only through one hardcoded rule. The gap is configurability and reuse.

## Proposed Design

### Configuration Shape

Add a project-level section under `options` scoped to fixed entities:

```yaml
options:
  fixed_entity_types:
    conventions:
      - pattern: "*_id"
        type: int
      - pattern: "*_uuid"
        type: string
      - pattern: "abundance"
        type: int
```

Supported type names should match existing fixed-entity types:

- `int`
- `string`
- `float`
- `bool`
- `date`

The proposal intentionally uses `string`, not `str`, to stay consistent with existing `column_types` behavior.

### Matching Rules

Rules are evaluated in order.

- matching uses simple glob semantics
- first match wins
- pattern matching is column-name based
- exact names and wildcard patterns are both allowed

This keeps the configuration readable and predictable. Regex matching can be considered later if there is a concrete need.

### Precedence

Effective type resolution for a fixed-entity column should become:

1. `entity.column_types[column]`
2. first matching project convention
3. built-in fallback for `*_id -> int`
4. otherwise no inferred type

This preserves the current role of `column_types` as the most specific declaration while making project-wide defaults reusable.

### Runtime Enforcement Semantics

The key design constraint is to avoid reintroducing the recent regression where undeclared non-`_id` values were rejected too aggressively.

Recommended rule:

- explicit `column_types` are strict
- configured project conventions are also strict
- built-in `_id -> int` fallback remains strict
- columns with no explicit or convention-based type continue to preserve incoming scalar values

This gives a consistent mental model:

- local explicit type
- project explicit default
- legacy built-in fallback
- otherwise preserve values as provided

### Validation Rules

Convention entries should be validated at load time.

Validation should reject:

- unknown type names
- missing `pattern`
- missing `type`
- non-list `conventions`
- malformed convention entries

If the project contains invalid convention definitions, project loading should fail with a clear configuration error.

## Alternatives Considered

### 1. Generic `options.types.conventions`

Rejected for now. The immediate need is fixed-entity typing. A generic project-wide type system would broaden scope without a clear consumer outside fixed entities.

### 2. Rely Only On `column_types`

Rejected. It keeps behavior explicit, but forces repeated declarations and does not address shared project conventions.

### 3. Treat Conventions As Hints Only

Rejected. If a project deliberately declares a convention such as `abundance -> int`, the runtime should enforce it consistently. Otherwise the configuration becomes descriptive rather than behavioral.

## Risks And Tradeoffs

- Project-level conventions add another precedence layer to fixed-entity typing.
- Misconfigured broad patterns could make validation stricter than a project expects.
- The feature may increase pressure for future frontend support to visualize where a column's effective type came from.

These tradeoffs are acceptable if the semantics stay narrow and explicit.

## Testing And Validation

Implementation should be validated with focused tests for:

- precedence between `column_types`, project conventions, and `_id` fallback
- ordered first-match behavior
- strict enforcement for convention-declared types
- unchanged preservation of undeclared non-`_id` scalar values
- configuration errors for malformed convention definitions

Regression coverage should include the merged-entity case that motivated the recent runtime relaxation.

## Acceptance Criteria

- [ ] Projects can declare ordered fixed-entity type conventions under `options`
- [ ] `column_types` overrides project conventions for the same column
- [ ] The first matching convention determines the effective type
- [ ] Built-in `_id -> int` behavior still works when no explicit declaration overrides it
- [ ] Convention-declared types are enforced consistently at load, validation, and persistence boundaries
- [ ] Undeclared non-`_id` columns still preserve incoming scalar values
- [ ] Invalid convention configuration fails with a clear configuration error

## Recommended Delivery Order

1. Add project model support for fixed-entity type conventions.
2. Implement convention validation and type resolution precedence.
3. Reuse the resolved effective type across load, validation, persistence, and materialization paths.
4. Add focused regression and precedence tests.
5. Update configuration documentation after behavior is merged.

## Future Enhancements

- A later version could add entity-scoped convention blocks for cases where a project-wide rule is too broad. This would complement existing per-entity `column_types`, not replace them. If added, precedence should remain explicit: `column_types` first, then any entity-scoped convention layer, then project-level conventions, then the built-in `_id -> int` fallback.
- A later version could also evaluate whether target model specifications should help drive fixed-entity typing so projects stay DRY. The target model already supports column `type` hints, but they are informational in v1 rather than enforced. Any future design should decide whether those hints are advisory only, whether they can seed conventions, and how they map onto fixed-entity runtime types without overriding explicit project or entity declarations.
- Any UX that exposes type-resolution lineage, such as whether a column type came from `column_types`, a project convention, or the built-in fallback, should also be deferred to a later iteration. It is not necessary for the initial user-facing scope of this feature.
- Regex support should also be deferred to a later iteration. Glob matching is sufficient for the first version unless a concrete project need demonstrates that broader pattern expressiveness is necessary.

## Final Recommendation

Approve a narrow proposal for project-level fixed-entity type conventions. Implement them as ordered implicit defaults for fixed entities only, with explicit precedence over the built-in fallback and no change to the current preservation behavior for undeclared non-`_id` columns.

## Implementation Progress Checklist

- [x] Add project model support for fixed-entity type conventions.
- [x] Implement convention validation and type resolution precedence.
- [x] Reuse the resolved effective type across load, validation, persistence, and materialization paths.
- [x] Add focused regression and precedence tests.
- [x] Update configuration documentation after behavior is merged.
- [x] Produce a follow-up proposal for deferred enhancements such as entity-scoped convention blocks, target-model-informed typing, lineage UX, and regex support.

See [future/FIXED_ENTITY_TYPE_CONVENTION_ENHANCEMENTS.md](future/FIXED_ENTITY_TYPE_CONVENTION_ENHANCEMENTS.md) for the follow-up proposal.