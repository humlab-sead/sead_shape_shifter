# Fixed Entity Column Types UX Follow-Up

## Status

- Proposed feature / change request
- Scope: FixedValuesGrid UX for optional `column_types` on fixed entities
- Goal: Provide safe, discoverable UI controls for explicit column typing without expanding or delaying the core `_id` type-fix rollout

## Summary

This proposal defines a follow-up UX implementation for optional `column_types` in fixed entities. The core fix proposal (`IMPROVE_TYPE_HANDLING_FOR_FIXED_ENTITIES.md`) already addresses urgent backend/frontend `_id` type correctness and allows backend-recognized `column_types` in YAML. This follow-up adds editor UX to view, edit, validate, and persist `column_types` safely.

The recommendation is to ship this in a narrow first slice: preserve existing `column_types` through the fixed-entity editor without loss, add explicit UI controls for `int` and `string`, and keep strict client-side validation aligned with the types the grid can validate safely today.

`date`, `float`, and `bool` remain backend-recognized types, but strict client-side editing and validation for those types should be deferred until the grid has explicit parsing and error-state rules for them.

## Problem

The system can support optional `column_types` in YAML, but users currently have no dedicated UI to manage those declarations. Without UX support:

- Users must hand-edit YAML for explicit typing.
- Type intent is hidden while editing rows in FixedValuesGrid.
- Validation outcomes are harder to understand because declared-type context is not visible in the editor.
- Teams may avoid `column_types`, reducing the value of explicit typing where inference is not sufficient.
- The frontend editor does not currently model or serialize `column_types`, so a normal edit/save cycle cannot yet be trusted to preserve existing declarations.

## Scope

This proposal covers:

- frontend state and save/load round-tripping for fixed-entity `column_types`
- FixedValuesGrid support for viewing and editing per-column explicit types.
- Type options for explicit declarations in UI, with an initial editing scope of `int` and `string`
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
- Full client-side editing and validation parity for `float`, `bool`, and `date` in the first implementation slice.
- Exposing or managing project-level type conventions in this iteration.

## Current Behavior

Current state after the core proposal:

- Backend can recognize and enforce optional `column_types` in fixed entities.
- `_id` columns are handled with strict parsing/validation rules.
- FixedValuesGrid does not provide dedicated controls for explicit per-column types.
- The fixed-entity editor does not yet keep `column_types` in frontend form state or write it back during save.
- Grid parsing helpers currently distinguish only integer-like ID columns and string columns.

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

Implementation note:

- Backend support already exists for all allowed type values.
- The initial frontend editing and validation scope should be limited to `int` and `string`.
- Existing `float`, `bool`, and `date` declarations must still survive load/save round-trip unchanged.

### 2. Type Precedence

Evaluation order for each column in FixedValuesGrid:

1. If `column_types[column]` exists, use that declared type.
2. Else use inference (current rules, including `_id` handling).

UI should always show which source is active:

- `Declared: int`
- `Inferred: int`

This proposal is scoped to explicit `column_types` versus existing inference only. If project-level fixed-entity conventions are added later, the UI source labels and precedence text must be extended in a separate change.

### 3. FixedValuesGrid Controls

Add one compact type selector per column header.

Type selectors should be visible for all columns by default.

Selector options in the first implementation slice:

- `Auto`
- `Integer`
- `String`

Behavior:

- `Auto` removes the explicit entry from `column_types`.
- Any non-`Auto` option writes/updates `column_types[column]`.
- If all columns are `Auto`, omit `column_types` from persisted YAML.

Future extension:

- `Float`, `Boolean`, and `Date` can be added once their parsing, validation, and inline error behavior are defined and tested.

### 4. Validation UX

Validation behavior for declared numeric columns should match strict parsing principles from the core fix:

- Invalid edit is rejected.
- Previous value is retained.
- Cell shows inline error state.
- A compact top-level summary groups problems per column, while inline errors remain row/cell-specific.

In the first implementation slice:

- `int` uses strict integer parsing and rejection behavior.
- `string` keeps the current string-or-null behavior.
- `float`, `bool`, and `date` declarations are preserved but do not gain new client-side editing controls or strict validation yet.

Warning presentation model:

- Inline validation remains attached to the specific row/cell where the invalid value occurs.
- The summary area above the grid groups problems per column so users can quickly see which declared type is causing failures.

### 5. Save and Round-Trip Behavior

On load:

- Parse and render existing `column_types` selectors.
- Preserve existing unsupported-yet declarations unchanged in frontend state.

On save:

- Persist explicit declarations as `column_types`.
- Keep YAML minimal (remove empty `column_types`).

Round-trip requirement:

- Load -> edit -> save -> reload preserves semantic meaning and explicit type selections.

### 6. Compatibility

- Existing projects without `column_types` must behave exactly as today.
- Existing inference behavior remains default.
- No migration step is required.

## Implementation Preconditions

Before visible type-editing controls are added, the frontend must first support safe preservation of `column_types`.

Required preconditions:

- Add `column_types` to fixed-entity frontend form state.
- Ensure edit/save round-trip preserves existing declarations unchanged.
- Remove stale `column_types` entries automatically when their columns no longer exist.
- Keep the first implementation slice scoped to explicit `column_types` and current inference only.

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
- Supporting all backend-recognized types in one step would force the frontend to invent parsing behavior that does not exist yet.

Mitigations:

- Keep controls compact and column-local.
- Reuse strict parser and validation patterns already adopted for `_id` handling.
- Add round-trip tests and serialization-focused tests.
- Phase the first implementation around `int` and `string`, and defer `date`/`float`/`bool` editing until their behavior is specified.

## Testing And Validation

- Unit tests for selector behavior (`Auto` remove vs explicit type set).
- Unit tests for precedence (declared type overrides inference).
- Unit tests for strict validation behavior under declared `int` types.
- Unit tests confirming `string` declarations preserve existing non-null string behavior.
- Integration test for YAML round-trip with populated `column_types`.
- Integration test for fallback behavior when `column_types` is absent.
- Integration test confirming pre-existing `date`/`float`/`bool` declarations survive edit/save unchanged.
- Manual test in arbodat project verifying visible type state and save/reload consistency.

## Acceptance Criteria

- [ ] FixedValuesGrid exposes per-column type selectors with `Auto` default.
- [ ] Selecting `Auto` removes explicit type for the column.
- [ ] Selecting explicit type persists `column_types[column]`.
- [ ] Declared type always overrides inferred type in grid behavior.
- [ ] Invalid `int` values are rejected with clear inline errors.
- [ ] `column_types` is omitted from YAML when effectively empty.
- [ ] `column_types` survives load/save/reload round-trip without loss.
- [ ] Existing `date`, `float`, and `bool` declarations survive load/save/reload unchanged.
- [ ] Projects without `column_types` retain current behavior unchanged.

## Recommended Delivery Order

1. Implement `column_types` frontend state model and serialization hooks.
2. Ensure existing declarations round-trip unchanged, including unsupported-yet types.
3. Add column header selectors with `Auto`, `Integer`, and `String`.
4. Wire declared-type precedence into parsing and validation for the first slice.
5. Add test coverage for selector behavior, precedence, preservation, and round-trip.
6. Run manual verification on arbodat fixed entities.

## Open Questions

No open questions remain.

## Final Recommendation

Approve this follow-up as a separate proposal from the urgent `_id` type-fix work, but implement it in a phased way. The first slice should make `column_types` round-trip safe in the frontend, add explicit editing for `int` and `string`, and defer `date` validation and other advanced type editing until the grid has explicit parser and validation rules for them.
