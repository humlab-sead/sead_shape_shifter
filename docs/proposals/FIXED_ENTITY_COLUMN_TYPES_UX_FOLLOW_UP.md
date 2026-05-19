# Fixed Entity Column Types UX Follow-Up

## Status

- Proposed feature / change request
- Scope: FixedValuesGrid UX for optional `column_types` on fixed entities
- Goal: Provide safe, discoverable UI controls for explicit column typing without expanding or delaying the core `_id` type-fix rollout

## Summary

This proposal defines a follow-up UX implementation for optional `column_types` in fixed entities. The core fix proposal (`IMPROVE_TYPE_HANDLING_FOR_FIXED_ENTITIES.md`) already addresses urgent backend/frontend `_id` type correctness and allows backend-recognized `column_types` in YAML. This follow-up adds editor UX to view, edit, validate, and persist `column_types` safely.

The recommendation is to ship a minimal but complete UX for explicit type management in FixedValuesGrid: per-column type controls, clear validation feedback, predictable save behavior, and round-trip persistence.

## Problem

The system can support optional `column_types` in YAML, but users currently have no dedicated UI to manage those declarations. Without UX support:

- Users must hand-edit YAML for explicit typing.
- Type intent is hidden while editing rows in FixedValuesGrid.
- Validation outcomes are harder to understand because declared-type context is not visible in the editor.
- Teams may avoid `column_types`, reducing the value of explicit typing where inference is not sufficient.

## Scope

This proposal covers:

- FixedValuesGrid support for viewing and editing per-column explicit types.
- Type options for explicit declarations in UI.
- Precedence behavior between explicit `column_types` and naming inference.
- Inline validation/error display tied to declared type.
- Save/load round-tripping for `column_types`.
- Guardrails to avoid accidental broad schema edits.

## Non-Goals

- Reworking backend coercion policy for `_id` values.
- Replacing the existing core `_id` inference and strict parser logic.
- Advanced data profiling or automatic type detection beyond current conventions.
- Bulk migration of historical YAML files.
- Extending this UX to non-fixed entity types in this iteration.

## Current Behavior

Current state after the core proposal:

- Backend can recognize and enforce optional `column_types` in fixed entities.
- `_id` columns are handled with strict parsing/validation rules.
- FixedValuesGrid does not provide dedicated controls for explicit per-column types.

## Proposed Design

### 1. Data Model Contract

For fixed entities, support this optional field:

```yaml
column_types:
  method_id: int
  method_name: string
```

Allowed type values in this phase:

- `int`
- `string`
- `float`
- `bool`
- `date`

Rules:

- Keys must match entries in `columns`.
- Unknown keys are invalid.
- Omitted `column_types` means inference remains in effect.

### 2. Type Precedence

Evaluation order for each column in FixedValuesGrid:

1. If `column_types[column]` exists, use that declared type.
2. Else use inference (current rules, including `_id` handling).

UI should always show which source is active:

- `Declared: int`
- `Inferred: int`

### 3. FixedValuesGrid Controls

Add one compact type selector per column header.

Selector options:

- `Auto`
- `Integer`
- `String`
- `Float`
- `Boolean`
- `Date`

Behavior:

- `Auto` removes the explicit entry from `column_types`.
- Any non-`Auto` option writes/updates `column_types[column]`.
- If all columns are `Auto`, omit `column_types` from persisted YAML.

### 4. Validation UX

Validation behavior for declared numeric columns should match strict parsing principles from the core fix:

- Invalid edit is rejected.
- Previous value is retained.
- Cell shows inline error state.
- A compact summary can list row/column errors.

For declared non-numeric types, apply equivalent strict checks by declared type where implemented.

### 5. Save and Round-Trip Behavior

On load:

- Parse and render existing `column_types` selectors.

On save:

- Persist explicit declarations as `column_types`.
- Keep YAML minimal (remove empty `column_types`).

Round-trip requirement:

- Load -> edit -> save -> reload preserves semantic meaning and explicit type selections.

### 6. Compatibility

- Existing projects without `column_types` must behave exactly as today.
- Existing inference behavior remains default.
- No migration step is required.

## Alternatives Considered

1. Keep YAML-only management for `column_types`.
- Rejected: low discoverability and high error-proneness.

2. Add read-only badges but no editing controls.
- Rejected: improves visibility but does not solve authoring workflow.

3. Build advanced profiling/autodetect first.
- Deferred: higher complexity than needed for this follow-up.

## Risks And Tradeoffs

- Added UI complexity in an already dense grid.
- More validation states to manage client-side.
- Potential mismatch risk between UI model and YAML serialization.

Mitigations:

- Keep controls compact and column-local.
- Reuse strict parser and validation patterns already adopted for `_id` handling.
- Add round-trip tests and serialization-focused tests.

## Testing And Validation

- Unit tests for selector behavior (`Auto` remove vs explicit type set).
- Unit tests for precedence (declared type overrides inference).
- Unit tests for strict validation behavior under declared numeric types.
- Integration test for YAML round-trip with populated `column_types`.
- Integration test for fallback behavior when `column_types` is absent.
- Manual test in arbodat project verifying visible type state and save/reload consistency.

## Acceptance Criteria

- [ ] FixedValuesGrid exposes per-column type selectors with `Auto` default.
- [ ] Selecting `Auto` removes explicit type for the column.
- [ ] Selecting explicit type persists `column_types[column]`.
- [ ] Declared type always overrides inferred type in grid behavior.
- [ ] Invalid values are rejected with clear inline errors for strict numeric parsing cases.
- [ ] `column_types` is omitted from YAML when effectively empty.
- [ ] `column_types` survives load/save/reload round-trip without loss.
- [ ] Projects without `column_types` retain current behavior unchanged.

## Recommended Delivery Order

1. Implement `column_types` UI state model and serialization hooks.
2. Add column header selectors with `Auto` + explicit type options.
3. Wire declared-type precedence into parsing/validation.
4. Add test coverage for selector behavior, precedence, and round-trip.
5. Run manual verification on arbodat fixed entities.

## Open Questions

- Should `date` validation ship in this follow-up, or be deferred to a later phase?
- Should type selectors be visible for all columns by default, or behind an "Advanced" toggle?
- Should declared-type warnings be grouped per column, per row, or both?

## Final Recommendation

Approve this follow-up as a separate proposal from the urgent `_id` type-fix work. Implement a focused FixedValuesGrid UX for `column_types` that is explicit, strict, and round-trip safe, while preserving inference as the default behavior for existing projects.
