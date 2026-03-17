# Foreign Key Null-Key Default Behavior

## Status

- Proposed feature / change request
- Scope: core FK validation, merge behavior, documentation, frontend terminology
- Goal: define a sensible default behavior for alternative-key FK joins when key columns contain `NULL` / `NaN`

## Summary

Shape Shifter currently treats `NULL` / `NaN` in foreign key join columns as an error unless `allow_null_keys` is enabled.

That behavior is defensible for strict identity joins, but it is less intuitive when a foreign key uses alternative business-key columns only to resolve a remote `system_id`. In that case, users often expect missing key parts to mean "the relationship cannot be resolved" rather than "the entire join is invalid".

This proposal summarizes two design options:

1. Introduce an explicit user-facing policy for missing join keys.
2. Keep `allow_null_keys` internally, but change the default behavior for alternative-key FK lookup so missing keys are treated as unresolved links rather than hard errors.

In both options, `NULL` should be treated semantically as SQL `NULL`: it does not equal anything, including another `NULL`.

## Problem

### Current Behavior

- Pre-merge validation raises on any null values in FK key columns when `allow_null_keys` is `false`.
- The merge helper in [src/transforms/utility.py](src/transforms/utility.py) already has null-safe merge mechanics that ensure null keys never match null keys.
- The user-facing control is the `allow_null_keys` flag, which is technically accurate but harder to understand in the common case of lookup-style FK resolution.

### Why This Is Confusing

For joins on alternative key columns, users typically think in terms of this question:

"If one part of the alternative key is missing, should the row fail, disappear, or just remain unresolved?"

That is a business rule question. The current checkbox exposes an implementation detail instead.

## Desired Default Behavior

For alternative-key FK joins used to resolve the remote `system_id`, the recommended default behavior is:

1. If the local alternative key contains `NULL` / `NaN`, the row should not match any remote row.
2. The row should be preserved.
3. The resolved FK value should remain empty / null.
4. Remote rows with incomplete key values should not be considered valid matches.
5. The system may warn or report unresolved relationships, but should not fail by default.

This is consistent with relational null semantics and easy to explain in the manual:

"Missing alternative key values mean the foreign key cannot be resolved, so the row is kept and the foreign key remains empty."

## Option 1: Explicit Missing-Key Policy

### Summary

Replace the boolean-focused mental model with an explicit FK policy such as:

```yaml
constraints:
  missing_key_behavior: error | no_match | drop_row
```

### Semantics

- `error`: current strict behavior; null key values are validation failures.
- `no_match`: null key values do not match anything; the row is preserved and the FK remains unresolved.
- `drop_row`: rows with incomplete join keys are excluded from the merge input.

### Implementation Impact

- Add a new constraint field in core, backend API models, frontend types, and schema.
- Update pre-merge validation in [src/specifications/constraints.py](src/specifications/constraints.py).
- Potentially update merge and link behavior in [src/transforms/utility.py](src/transforms/utility.py) and [src/transforms/link.py](src/transforms/link.py).
- Replace or supplement the `allow_null_keys` checkbox in the FK editor with a clearer control.
- Update YAML docs, examples, and validation messages.

### Advantages

- Explicit and easy to document.
- Better long-term model if multiple null-handling strategies are needed.
- Avoids hiding policy behind an implementation-focused boolean.

### Disadvantages

- Larger model and API change.
- Requires compatibility/migration decisions for existing YAML.
- More frontend, backend, and documentation work.

## Option 2: Keep `allow_null_keys`, Change the Default for Alternative-Key FK Lookup

### Summary

Keep the current model shape, but redefine the default behavior for alternative-key FK lookup so missing key values mean "unresolved link" rather than "error".

The user-facing explanation would become:

"When alternative join keys are missing, Shape Shifter keeps the row and leaves the foreign key unresolved."

### Semantics

- Null local alternative keys do not match any remote row.
- The local row is preserved.
- The resolved FK stays null.
- Remote rows with incomplete alternative keys do not participate as valid matches.
- `allow_null_keys` remains available for advanced or legacy cases, but is no longer the primary concept in documentation.

### Implementation Impact

- Keep the current FK config model in core, backend, and frontend.
- Relax or bypass strict null-key failure in [src/specifications/constraints.py](src/specifications/constraints.py) for the relevant FK lookup case.
- Reuse null-safe merge mechanics in [src/transforms/utility.py](src/transforms/utility.py).
- Ensure link behavior preserves the row in the intended workflow, which may require left-join semantics in [src/transforms/link.py](src/transforms/link.py) when the FK is being used for enrichment rather than filtering.
- Update docs and UI wording to explain the behavior in domain terms instead of checkbox terms.

### Exact Definition of the Special Case

If Option 2 is adopted, the "alternative-key FK lookup" case should be recognized structurally, not heuristically.

The recommended definition is:

1. The FK is executed through [src/transforms/link.py](src/transforms/link.py) as part of normal foreign key linking.
2. The join type is `left`.
3. The FK is expected to resolve at most one remote row per local row:
  - `cardinality` is `many_to_one` or `one_to_one`, or
  - `require_unique_right` is `true`.
4. The `remote_keys` are not simply the remote identity columns:
  - not just remote `system_id`, and
  - not just remote `public_id`.
5. The resolved remote identity is intended to be retained in the result:
  - `drop_remote_id` is not `true`.
6. The user has not explicitly requested strict null-key failure.

This keeps the behavior limited to the specific enrichment case the proposal is targeting: using alternative business keys to resolve the remote `system_id` and keep the local row.

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

If Option 2 needs to preserve an explicit strict override, the implementation will need one of these:

1. make `allow_null_keys` tri-state internally (`None | true | false`),
2. preserve whether the field was present in YAML/API input, or
3. introduce a clearer explicit policy field later.

Without that distinction, Option 2 becomes more implicit because every `false` looks the same at runtime.

### Advantages

- Minimal schema and API churn.
- Lower implementation cost.
- Backward compatible at the config surface.

### Disadvantages

- More implicit than Option 1.
- Behavior depends on join context rather than only on the configuration text.
- Requires a precise definition of when an FK counts as an "alternative-key lookup" case.

## Key Semantic Rule for Both Options

`NULL` / `NaN` should not match `NULL` / `NaN`.

That means:

- The system should never treat two missing key values as an equal join key.
- The correct default action is unresolved relationship, not successful relationship.

This aligns with SQL semantics and avoids false matches in compound keys.

## Recommendation

Adopt Option 2 first, then evaluate whether Option 1 is needed later.

### Why

- The immediate user problem is about default behavior and terminology, not lack of expressive power.
- Option 2 fixes the common case with smaller implementation risk.
- The current merge helper already supports the desired null-safe matching behavior.
- If additional null-handling modes are needed later, Option 1 can still be introduced as a cleaner long-term model.
- The special case can be defined narrowly enough to avoid turning the behavior into vague "magic".

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
