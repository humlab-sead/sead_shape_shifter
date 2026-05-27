# Proposal: Sead Change Request Update Handling For Existing Rows

## Status

- Proposed change request
- Decision state: candidate, not accepted
- Scope: define how `sead_change_request` should handle updates to already-existing target rows
- Goal: decide whether and how the ingester should generate update-oriented change packages beyond the Delivery 1 insert-only baseline

## Summary

Delivery 1 deliberately stops at forward inserts.

That closes the direct path for new rows and new associations, but it leaves an important operational gap: projects that need to correct or extend an already-existing target row still have no defined path inside `sead_change_request`.

This proposal defines the next decision surface for that gap. It is intentionally focused on update handling for existing rows rather than bundling rollback, change detection, and every other later-delivery concern into one omnibus follow-up.

## Problem

The current ingester can resolve and reference existing rows, but it cannot express a change to an existing target row.

That creates four practical problems.

1. Operators cannot use the new ingester for correction workflows that need to modify existing SEAD rows.
2. The boundary between reference-only existing rows and update-eligible existing rows is not yet defined.
3. There is no accepted rule for deciding whether a normalized row represents an update, a no-op, or a blocked conflict.
4. The frontend and operator workflow cannot yet explain what will happen when a submission includes changes to existing rows.

## Scope

This proposal covers:

- rules for identifying update candidates among existing target rows
- rules for deciding whether an update is allowed, unnecessary, or blocked
- the output contract for update-oriented change packages when updates are accepted
- the interaction between update handling, idempotency, and operator review

## Non-Goals

- implementing rollback in the same change request
- solving every kind of semantic duplicate detection
- redesigning Delivery 1 insert handling
- designing the full frontend workflow in this document
- changing SCCS internals

## Current Behavior

Today `sead_change_request` treats an existing entity row as reference-only.

That means:

- a populated `public_id` prevents a new insert for that entity row
- the ingester may still emit new bridge or association rows that reference the existing entity
- any change to the existing row's mutable attributes is outside the current contract

This is correct for the closed Delivery 1 baseline, but it is insufficient for a fuller operational replacement of the legacy SEAD path.

## Proposed Design

### 1. Define update handling as an explicit planning state

Update behavior should not be inferred from a row merely having a target ID.

The planning model should distinguish at least these cases for existing rows:

- reference-only existing row
- update candidate row
- no-op existing row
- blocked conflicting row

That keeps update behavior explicit and prevents silent upgrades from reference-only semantics into mutation semantics.

### 2. Require a deterministic comparison boundary

Update eligibility should be decided only against an explicit set of mutable fields.

The ingester should not compare every column blindly. It needs a defined comparison boundary so that identity fields, audit fields, derived fields, and immutable fields do not accidentally trigger updates.

If that comparison boundary is not defined clearly enough for an entity, the row should stay blocked rather than guessing.

### 3. Treat no-op updates differently from real changes

If an existing row matches the accepted mutable-field boundary exactly, the ingester should treat it as a no-op rather than emitting an update.

This matters for idempotency, reruns, and operator trust. A rerun of unchanged content should not create meaningless update statements.

### 4. Block ambiguous or conflicting updates

This CR should prefer safety over convenience.

If the ingester cannot determine whether a difference is allowed, material, or conflicting, it should block the row and emit actionable diagnostics rather than generating a speculative update.

Examples of blocked cases may include:

- multiple competing source values for the same target row in one run
- attempted changes to immutable or identity-defining fields
- missing target metadata for deciding mutability or comparison scope

### 5. Start with a narrow SQL output contract

If this CR is accepted, the first implementation should keep update SQL narrow and explicit.

The initial contract should prefer direct `UPDATE` statements for clearly identified existing rows with accepted mutable-field changes. It should not expand immediately into generalized merge behavior.

## Risks And Tradeoffs

- update handling increases operational power, but it also increases the risk of silent data mutation if planning rules are vague
- a narrow mutable-field boundary is safer, but it may leave some wanted changes unsupported until metadata improves
- blocking ambiguous updates protects data quality, but it may frustrate operators if diagnostics are weak
- update handling may require frontend review affordances later, even if this CR keeps the initial focus on backend rules and artifact generation

## Validation And Acceptance Criteria

- the repository has a documented rule for when an existing row is reference-only, no-op, update-eligible, or blocked
- update handling is defined against an explicit mutable-field boundary rather than implicit full-row comparison
- ambiguous or unsupported update cases are defined as blocked outcomes with diagnostics
- the CR states a narrow initial SQL output contract for accepted updates
- the proposal makes clear what remains out of scope for later work, including rollback and broader change detection

## Final Recommendation

Treat update handling for existing rows as its own next-delivery change request.

It is important enough to deserve a focused decision, and risky enough that it should not be smuggled in under broader “Delivery 2” wording. If accepted, it should be implemented as a narrow, explicit update contract rather than as a generalized mutation engine.