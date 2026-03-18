# Lookup FK Null-Key Default Behavior

## Status

- Proposed feature / change request
- Scope: core FK validation, merge behavior, documentation, frontend terminology
- Goal: define a sensible default behavior for alternative-key FK joins when key columns contain `NULL` / `NaN`
- Tracking issues: #357, #353, #356, #354, #355

## Summary

The current default treats null FK join keys as a hard error unless `allow_null_keys` is enabled. That is understandable for strict identity joins, but it is unintuitive for business-key lookup joins where users usually expect "unresolved link" rather than "invalid join."

The core reason for this change is not null handling in general. It is to align the default behavior of lookup-style FK enrichment joins with user expectations:

1. keep the local row,
2. do not invent a match,
3. leave the FK unresolved.

This proposal covers only the narrow runtime and UX change needed for that lookup-style enrichment case.

Broader user-facing null-key policy design is intentionally out of scope for this document and can be proposed later if this narrower change proves insufficient.

`NULL` / `NaN` must be treated with SQL-like semantics: null never equals null.

## Decision Summary

The decision in this proposal is whether to fix the immediate lookup-join default problem with a narrow behavioral change now.

This proposal does **not** decide the long-term user-facing policy model for all null-key handling cases.

The recommended decision is:

1. approve the narrow Phase 1 behavior change for lookup-style FK enrichment joins,
2. treat broader explicit policy design as future work,
3. proceed only if the implementation explicitly separates validation policy from merge semantics and treats the change as a behavioral compatibility change.

## Scope

This proposal is in scope for:

1. lookup-style FK enrichment joins that use alternative keys to resolve a remote identity,
2. the narrow default behavior change for that case,
3. the runtime, validation, documentation, and frontend wording changes needed to support that behavior.

## Out Of Scope

This proposal is not in scope for:

1. a new general-purpose FK policy field,
2. a final user-facing model for all missing-key strategies,
3. changing the default behavior for all foreign key joins,
4. designing the full long-term replacement for `allow_null_keys`.

## Problem

### Current Behavior

- Pre-merge validation raises on any null values in FK key columns when `allow_null_keys` is `false`.
- The merge helper in [src/transforms/utility.py](src/transforms/utility.py) has null-safe merge mechanics, but they are currently only activated when `allow_null_keys` is `true`.
- The user-facing control is the `allow_null_keys` flag, which is technically accurate but harder to understand in the common case of lookup-style FK resolution.

### Two Separate Concerns

This proposal touches two distinct concerns that are currently coupled:

1. **Validation policy**: whether null values in FK key columns should be treated as a validation error.
2. **Merge semantics**: whether null key values participate in matching, and if not, what happens to the local row.

Those are not the same decision. A user may want null keys to be tolerated without wanting `NULL` to match `NULL`. Any implementation should define both axes explicitly.

### Why This Is Confusing

For joins on alternative key columns, users typically think in terms of this question:

"If one part of the alternative key is missing, should the row fail, disappear, or just remain unresolved?"

That is a business rule question. The current checkbox exposes an implementation detail instead.

## Desired Default Behavior

For lookup-style FK joins that use alternative keys to resolve the remote `system_id`, the recommended default behavior is:

1. If the local alternative key contains `NULL` / `NaN`, the row should not match any remote row.
2. The row should be preserved.
3. The resolved FK value should remain empty / null.
4. Remote rows with incomplete key values should not be considered valid matches.
5. The system may warn or report unresolved relationships, but should not fail by default.

This default is intended only for lookup-style FK enrichment joins. It is not intended as a new global default for all foreign key joins.

This is consistent with relational null semantics and easy to explain in the manual:

"Missing alternative key values mean the foreign key cannot be resolved, so the row is kept and the foreign key remains empty."

## Proposal

Keep the current model shape, but redefine the default behavior for alternative-key FK lookup so missing key values mean "unresolved link" rather than "error".

The user-facing explanation would become:

"When alternative join keys are missing, Shape Shifter keeps the row and leaves the foreign key unresolved."

### What Changes

- Null local alternative keys do not match any remote row.
- The local row is preserved.
- The resolved FK stays null.
- Remote rows with incomplete alternative keys do not participate as valid matches.
- `allow_null_keys` remains in the current model, but this proposal does not attempt to redefine it into a complete long-term policy model.
- This default changes only for the targeted lookup-style FK enrichment case. Non-lookup joins remain on the current strict path.

### Implementation Impact

- Keep the current FK config model in core, backend, and frontend.
- Relax or bypass strict null-key failure in [src/specifications/constraints.py](src/specifications/constraints.py) for the relevant FK lookup case.
- Decouple null-safe merge behavior from `allow_null_keys` in [src/transforms/utility.py](src/transforms/utility.py), because the current helper only enables null-safe matching when `allow_null_keys` is `true`.
- Ensure the runtime semantics are explicit: tolerated null keys must still behave as `no_match`, not as regular pandas merge keys.
- Ensure link behavior preserves the row in the intended workflow, which may require left-join semantics in [src/transforms/link.py](src/transforms/link.py) when the FK is being used for enrichment rather than filtering.
- Update docs and UI wording to explain the behavior in domain terms instead of checkbox terms.

### Implementation Invariant

If this proposal is adopted, the following must hold together:

1. null local key values are not raised as hard errors in the targeted case,
2. null local key values never match null remote key values,
3. unmatched local rows are preserved only when the join semantics allow it,
4. unresolved links remain visibly unresolved in the output.

Changing validation alone is insufficient. The merge path and post-merge expectations must change in tandem.

### Exact Definition of the Special Case

The "alternative-key FK lookup" case should be recognized structurally, not heuristically.

The recommended definition is:

1. The FK is executed through [src/transforms/link.py](src/transforms/link.py) as part of normal foreign key linking.
2. The join type is `left`.
3. The FK is expected to resolve at most one remote row per local row:
  - `cardinality` is `many_to_one` or `one_to_one`, or
  - `require_unique_right` is `true`.
4. The `remote_keys` are not simply the remote identity columns:
  - not just remote `system_id`, and
  - not just remote `public_id`.
5. The link is functioning as FK enrichment: it is intended to populate the local FK target from the remote identity, rather than merely filtering rows.
6. The user has not explicitly requested strict null-key failure.

This keeps the behavior limited to the specific enrichment case the proposal is targeting: using alternative business keys to resolve the remote `system_id` and keep the local row.

Note: `drop_remote_id` is not a reliable discriminator for this case. In the current linker implementation, the remote identity is always selected and renamed into the local result during linking, and `drop_remote_id` only affects a narrower cleanup path when `extra_columns` are also present.

### Why `left` Join Is Required

The desired default behavior is:

1. keep the source row,
2. do not match null to null,
3. leave the FK unresolved.

That is fundamentally left-join behavior. With `inner` joins, "no match" usually implies row loss, which conflicts with the intended default.

### Important Implementation Caveat

The current model treats `allow_null_keys` as a plain boolean with default `false` in both core and backend models:

- [src/model.py](src/model.py)
- [backend/app/models/entity.py](backend/app/models/entity.py)

That means the system currently cannot distinguish:

1. the user explicitly set `allow_null_keys: false`, and
2. the user omitted the field and accepted the default.

If the implementation needs to preserve an explicit strict override, it will need one of these:

1. make `allow_null_keys` tri-state internally (`None | true | false`),
2. preserve whether the field was present in YAML/API input, or
3. introduce a clearer explicit policy field later.

Without that distinction, this behavior remains more implicit because every `false` looks the same at runtime.

### What Does Not Change Under This Proposal

To preserve flexibility for non-lookup joins, the following should remain on the current strict behavior:

1. `inner` joins,
2. joins that act primarily as filtering joins rather than FK enrichment,
3. joins directly on remote identity keys,
4. joins where row preservation is not the intended behavior.

### Review Considerations

- Minimal schema and API churn.
- Lower implementation cost.
- No YAML field migration is required immediately.
- More implicit than a future explicit policy model.
- Behavior depends on join context rather than only on the configuration text.
- Requires a precise definition of when an FK counts as an "alternative-key lookup" case.
- This is still a behavioral default change for existing configurations that currently rely on `allow_null_keys: false` meaning both strict validation and plain merge behavior.
- Frontend defaults and help text currently reinforce the strict interpretation, so UI copy and examples would need to change together with the runtime.

## Future Work

A future proposal may introduce an explicit missing-key policy field if broader user-facing control is needed.

That future work is intentionally not specified here. The only constraint this proposal places on future work is that this implementation should not foreclose a later explicit policy model.

## Key Semantic Rule

`NULL` / `NaN` should not match `NULL` / `NaN`.

That means:

- The system should never treat two missing key values as an equal join key.
- The correct default action is unresolved relationship, not successful relationship.

This aligns with SQL semantics and avoids false matches in compound keys.

## Recommendation

Adopt this Phase 1 proposal.

### Why

- The immediate user problem is about default behavior and terminology, not lack of expressive power.
- This change can fix the common lookup-enrichment case with smaller surface-area change than a full policy redesign.
- The current merge helper contains the building blocks for null-safe matching behavior, but they are not sufficient on their own because they are still tied to `allow_null_keys`.
- The special case can be defined narrowly enough to avoid turning the behavior into vague "magic".
- Non-lookup joins can keep the current strict semantics, preserving flexibility where users really do want nulls to fail fast.

### Reviewer Decision Criteria

Approve this proposal only if the implementation plan commits to all of the following:

1. null-tolerant validation does not imply null-to-null matching,
2. the targeted case is defined structurally and testably,
3. left-join preservation semantics are explicit,
4. docs and frontend wording are updated together with runtime behavior,
5. the change is treated as a behavioral compatibility change,
6. non-lookup joins explicitly remain on the current strict path.

## Implementation Checklist

If this proposal is approved, the implementation should explicitly cover these work items:

### Core Runtime

1. Separate validation policy from merge semantics in the FK handling path.
2. Update [src/specifications/constraints.py](src/specifications/constraints.py) so the targeted lookup case no longer raises on null key parts by default.
3. Update [src/transforms/utility.py](src/transforms/utility.py) so null-safe merge behavior can be enabled independently of `allow_null_keys`.
4. Confirm [src/transforms/link.py](src/transforms/link.py) preserves unresolved rows only in the intended left-join enrichment case.
5. Ensure null local keys never match null remote keys in compound joins.
6. Ensure non-lookup joins are unchanged.

### Configuration and Model Semantics

1. Decide whether explicit `allow_null_keys: false` must remain a strict override.
2. If yes, add an internal distinction between omitted and explicit `false`, or document why that distinction is deferred.
3. Document the exact structural criteria that define the special-case alternative-key lookup behavior.

### Frontend and UX

1. Update FK editor wording in [ForeignKeyEditor.vue](frontend/src/components/entities/ForeignKeyEditor.vue) so it no longer describes the old strict default as the only interpretation.
2. Update frontend schema/help text if the editor or validation UI exposes this behavior.
3. Make sure validation and preview messaging describe unresolved links in domain language rather than implementation language.
4. Make clear in the UI/docs that the new default applies to lookup-style left joins, not all FK joins.

### Documentation

1. Update [docs/CONFIGURATION_GUIDE.md](docs/CONFIGURATION_GUIDE.md) to explain the new default behavior precisely.
2. Update examples that currently assume `allow_null_keys: false` always means hard failure.
3. Add one clear example of a left-join alternative-key lookup with missing local key parts and unresolved output.

### Tests

1. Add core tests for null local keys in the targeted alternative-key lookup case.
2. Add tests proving null does not match null in the merge path.
3. Add tests confirming strict behavior still applies outside the targeted case.
4. Add tests for left join preservation versus inner join row loss.
5. Add tests for any explicit override behavior if omitted vs explicit `false` is distinguished.
6. Add tests showing non-lookup joins are unaffected by the new default.

## Suggested Issue Breakdown

If this proposal moves forward, the work can be split into a small set of reviewable issues:

### Issue 1: Define FK null-key runtime semantics (#357)

**Goal**: separate validation policy from merge semantics and document the exact targeted case.

**Scope**:

1. Define the structural criteria for the alternative-key lookup case.
2. Decide how explicit `allow_null_keys: false` should behave.
3. Record the invariants for null handling, unresolved links, and row preservation.

**Primary files**:

- [docs/proposals/FK_LOOKUP_NULL_KEY_DEFAULT_BEHAVIOR.md](docs/proposals/FK_LOOKUP_NULL_KEY_DEFAULT_BEHAVIOR.md)
- [src/model.py](src/model.py)
- [backend/app/models/entity.py](backend/app/models/entity.py)

### Issue 2: Implement core FK null-key behavior (#353)

**Goal**: make the runtime behave as `no_match` for the approved special case without allowing null-to-null matches.

**Scope**:

1. Update pre-merge constraint handling.
2. Decouple null-safe merge behavior from `allow_null_keys`.
3. Confirm left-join unresolved-row preservation works only in the intended case.

**Primary files**:

- [src/specifications/constraints.py](src/specifications/constraints.py)
- [src/transforms/utility.py](src/transforms/utility.py)
- [src/transforms/link.py](src/transforms/link.py)

### Issue 3: Add regression coverage for FK null-key behavior (#356)

**Goal**: prevent regressions in validation, merge semantics, and join behavior.

**Scope**:

1. Add tests for null local key parts in the targeted lookup case.
2. Add tests proving null does not match null.
3. Add tests for strict behavior outside the targeted case.
4. Add tests for left versus inner join outcomes.

**Primary files**:

- [tests/specifications/test_constraints.py](tests/specifications/test_constraints.py)
- [tests/transforms/test_link.py](tests/transforms/test_link.py)
- Relevant model tests if config semantics change

### Issue 4: Update frontend wording and editor behavior (#354)

**Goal**: align the FK editor and validation messaging with the new domain language.

**Scope**:

1. Update FK editor help text.
2. Update schema/help metadata if needed.
3. Review validation and preview messages for unresolved-link terminology.

**Primary files**:

- [frontend/src/components/entities/ForeignKeyEditor.vue](frontend/src/components/entities/ForeignKeyEditor.vue)
- [frontend/src/schemas/entitySchema.json](frontend/src/schemas/entitySchema.json)
- Relevant frontend validation/help components

### Issue 5: Update documentation and examples (#355)

**Goal**: make the new behavior understandable from the docs alone.

**Scope**:

1. Update configuration reference text.
2. Update examples that currently imply strict failure.
3. Add one canonical unresolved-link example.

**Primary files**:

- [docs/CONFIGURATION_GUIDE.md](docs/CONFIGURATION_GUIDE.md)
- [README.md](README.md)
- Existing example YAML files and screenshots as needed

### Suggested Delivery Order

1. Issue 1 first, so the semantics are explicit before code changes.
2. Issue 2 and Issue 3 together or back-to-back, so runtime and tests land as one coherent change.
3. Issue 4 and Issue 5 after or alongside the core change, but before release.

### Current Issue Map

1. #357: define FK null-key runtime semantics
2. #353: implement FK null-key no-match behavior
3. #356: add regression coverage for FK null-key behavior
4. #354: update FK null-key wording in editor and validation UI
5. #355: update FK null-key documentation and examples

### Compatibility Note

This proposal does not change the YAML shape, but it does change the meaning of the current default behavior.

Today:

1. core and backend models default `allow_null_keys` to `false`,
2. new frontend FK editors initialize `allow_null_keys: false`,
3. UI text explains this as a strict default.

So this proposal should be treated as a behavioral compatibility change, not as a purely internal implementation refinement.

## Recommended Near-Term Behavior

For alternative-key joins used to resolve remote `system_id` values:

1. Treat missing local key parts as unresolved links.
2. Do not raise by default.
3. Do not match null to null.
4. Preserve the source row.
5. Leave the FK empty.
6. Warn or report unresolved rows when useful.

In practical terms, this should apply only to the narrow left-join FK enrichment case described above, not to all joins with nullable keys.

## Open Questions

1. Should the system require `how: left` explicitly for this behavior, or infer it for certain FK patterns?
2. Should unresolved-link counts appear in validation results, preview UI, or execution logs?
3. Should remote rows with null alternative keys be warned about explicitly as low-quality lookup targets?
4. Is it acceptable to keep `allow_null_keys` as a boolean for now, or should the implementation first add a way to distinguish omitted vs explicitly false?
5. Should validation policy and merge semantics become separate internal concepts even if the user-facing configuration remains unchanged for now?
