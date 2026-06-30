# Proposal: Sead Change Request Data Provider Update Scope

## Status

- Accepted change request
- Decision state: accepted on 2026-06-30
- Decision gate: passed with checklist complete
- Scope: define how provider-submitted data may change over time through `sead_change_request`, and which change scenarios must stay allowed, restricted, or blocked
- Goal: create the ownership, history, and workflow rules needed before implementing any provider-visible update path for previously ingested data

## Summary

Data provider data changes over time.

Providers need ways to correct, extend, revise, or supersede data that has already been ingested. The repository therefore needs a clear policy for which changes are allowed, how those changes preserve reviewable history, and which changes must stay under stronger control.

This CR recommends an ownership-first and history-preserving change model. Data providers should be able to correct and version their own data. They should not be able to directly mutate shared classifiers or shared lookups through the same automated path. Shared data changes need stronger review, narrower permissions, or a separate authority workflow.

History should not mean multiple active copies of the same provider-owned record. The rule should be that for a given logical record and point in time, the repository keeps at most one live version, while older versions remain available as history.

The existing-row SQL update path described in [UPDATE_HANDLING_FOR_EXISTING_ROWS.md](./UPDATE_HANDLING_FOR_EXISTING_ROWS.md) is one downstream scenario inside this broader problem. It should not define the problem statement for this CR.

This document is the decision record for the problem and recommendation. The durable lifecycle rules now live in [../../DATA_PROVIDER_SUBMISSION_LIFECYCLE.md](../../DATA_PROVIDER_SUBMISSION_LIFECYCLE.md), and phased delivery planning belongs in [DATA_PROVIDER_SUBMISSION_LIFECYCLE_IMPLEMENTATION_PLAN.md](./DATA_PROVIDER_SUBMISSION_LIFECYCLE_IMPLEMENTATION_PLAN.md).

## Problem

Before this decision gate, the repository lacked an accepted model for how provider-submitted data should evolve after the first ingest.

That is the root problem. The question is not only whether the system can generate `UPDATE` SQL for an existing row. The larger question is how the system should handle provider-owned data that changes over time while preserving history and protecting shared data.

Without that answer, the workflow has no clear rule for several real situations:

- a provider corrects a value that was wrong in an earlier submission
- a provider extends a previously submitted record with new optional data
- a provider replaces an earlier interpretation with a newer one
- a provider changes which shared term their own row should reference
- a provider wants a shared classifier or lookup corrected

Those situations are not the same. They do not carry the same ownership, review, or data-quality risk.

If the repository starts with SQL mechanics alone, it risks mixing together very different cases:

- corrections to provider-owned facts
- corrections to provider-owned descriptive metadata
- changes to references from provider-owned rows into shared lookup or classifier rows
- changes to the shared lookup or classifier rows themselves

Those cases do not carry the same ownership, review, or data-quality risk.

## Scope

This proposal covers:

- ownership categories relevant to update permissions
- the update scenarios a data provider may reasonably need
- the distinction between allowed, restricted, and blocked update scenarios
- the relationship between provider update scope and later SQL-oriented update handling work

## Non-Goals

- defining the full SQL contract for update statements
- designing the full frontend interaction for review, approval, or history browsing
- implementing rollback, delete, or merge behavior in this document
- deciding SCCS internals or database trigger behavior
- replacing curator or administrator workflows for shared authority data

## Current Behavior

The current `sead_change_request` path is mainly insert-oriented and forward-only.

Previously ingested rows are treated as reference-only, even when the ingester can resolve them. That keeps current behavior safe, but it leaves implementation behavior behind the now-accepted policy for provider corrections, revisions, or superseded data.

## Proposed Design

### 1. Use ownership as the first decision rule

Update eligibility should start with row ownership and data role, not just with whether the row already exists.

The repository should distinguish at least these groups:

- provider-owned data: facts, observations, notes, project-scoped metadata, and other rows where the provider is the responsible source
- shared reference data: classifiers, lookups, controlled vocabularies, and other rows reused across providers or projects
- system-managed data: identifiers, audit fields, reconciliation state, derived bridge rows, and other values the workflow should not treat as provider-editable business data

### 2. Allow providers to correct their own data with history

The primary allowed update path should be corrections to provider-owned data.

That should include version control or supersession metadata so the workflow records that a provider corrected an earlier submission rather than silently overwriting history.

That history model should enforce a simple invariant: for the same logical record at the same point in time, there must not be more than one live version. A newer accepted version supersedes the earlier live version instead of leaving both active.

The exact storage model can be decided later, but the policy should be clear now: provider-owned updates are acceptable when they stay within the provider's responsibility and preserve reviewable history.

### 3. Restrict direct mutation of shared data

Shared classifiers and shared lookups should not be treated like provider-owned rows.

Data providers may need to:

- reference an existing shared term
- request a new shared term when no match exists
- report that an existing shared term looks wrong

Those are real workflows, but they should not default to direct automated `UPDATE` statements against already-shared rows. Shared-data corrections need stronger control because one change may affect many providers and many existing records.

### 4. Separate reference changes from shared-row changes

A provider changing which classifier their own row points to is not the same as changing the classifier row itself.

The first may be an allowed update to provider-owned data. The second is a restricted update to shared reference data.

This distinction should be explicit in later planning and in the frontend language shown to operators.

### 5. Block identity and system-managed mutations

Some updates should stay blocked even if the provider owns the surrounding row.

Examples include:

- changing identity-defining keys after reconciliation has established the target row
- editing system IDs, target IDs, or other system-managed identifiers
- editing audit or process fields that exist to track the workflow itself
- directly editing derived rows when the source rows should be changed instead

## Suggested Scenario Set

The repository should consider at least these scenarios when defining provider-visible change support over time.

The existing-row planning and SQL contract in [UPDATE_HANDLING_FOR_EXISTING_ROWS.md](./UPDATE_HANDLING_FOR_EXISTING_ROWS.md) is one follow-up scenario inside this set, not the umbrella problem statement.

| Scenario | Typical example | Recommended handling |
|----------|-----------------|----------------------|
| Correct provider-owned factual data | A provider fixes a wrong abundance value, date range, measurement, or free-text note in data they submitted earlier | Allow through a version-controlled provider update path |
| Correct provider-owned descriptive metadata | A provider updates their own project description, dataset note, contact link, or submission note | Allow through a version-controlled provider update path |
| Extend provider-owned data | A provider adds missing optional values or new associations to rows they already own | Allow if ownership and validation rules are satisfied |
| Replace an earlier interpretation | A provider revises their own previously submitted statement or classification of their own row | Allow as a tracked supersession or versioned correction, not as silent destructive overwrite |
| Change which shared classifier a provider-owned row references | A sample or observation is reclassified to a different existing term | Allow as an update to the provider-owned row reference, not to the shared classifier row |
| Request a new shared classifier or lookup | No existing term fits, so the provider needs a new controlled value | Restrict to a reviewed add path or separate authority workflow |
| Correct an existing shared classifier or lookup | A provider believes a shared term label, description, or mapping is wrong | Restrict to curator or authority review; do not allow direct provider update SQL |
| Merge, rename, or deprecate shared terms used by multiple providers | Two shared terms should become one, or a term should be retired | Restrict to a dedicated shared-data governance workflow |
| Update another provider's rows | One provider attempts to change facts or metadata owned by a different provider | Block |
| Update identity or audit fields | A submission tries to change IDs, reconciliation keys, or workflow timestamps directly | Block |
| Update derived rows directly | A submission tries to edit a bridge or derived table instead of changing the source rows that produce it | Block or redirect to the owning source rows |

## Risks And Tradeoffs

- provider-owned updates are important for real correction workflows, but they raise the bar for versioning, review, and operator communication
- restricting shared-data updates is safer, but it means some wanted corrections will need a slower reviewed workflow
- a strong ownership model reduces accidental broad mutation, but it may expose gaps in current metadata about who owns which row types
- if the repository treats all existing rows alike, it will either block too much useful correction work or allow unsafe shared-data mutation

## Validation And Acceptance Criteria

- the repository has a documented distinction between provider-owned data, shared reference data, and system-managed data for update decisions
- the proposal defines which provider-visible update scenarios are allowed, restricted, or blocked at a policy level
- the proposal states that provider-owned updates should preserve reviewable history rather than rely on silent overwrite semantics
- the proposal states that for a given logical record and point in time, the repository keeps no more than one live version
- the proposal states that direct mutation of shared classifiers and shared lookups is not the default provider path
- the proposal stands on its own without requiring unnamed delivery or milestone context to explain the problem
- the proposal is positioned clearly as the decision document rather than the long-term specification or delivery plan
- later update-handling work can point to this document as the upstream scope for deciding which existing-row updates are even eligible for SQL generation

## Decision Gate: Acceptance/Revision Checklist

- [x] Ownership-first lifecycle policy is explicit and complete for provider-owned, shared-reference, and system-managed data classes
- [x] Allowed, restricted, and blocked scenario boundaries are explicit and checkable
- [x] History and one-live-version invariants are explicit and usable by downstream implementation plans
- [x] Shared-data governance is separated from default provider-owned update execution
- [x] Existing-row SQL update handling is kept downstream of lifecycle policy acceptance
- [x] Cross-document alignment is updated in lifecycle specification, implementation plan phase entry status, and tracker state

Gate outcome: accepted. No blocking revisions remain.

## Final Recommendation

Do not implement existing-row update handling until the repository accepts an ownership-first provider update scope.

The next safe step is to treat provider-owned corrections and revisions as the primary allowed change class, require history-preserving workflow semantics for those changes, and keep direct shared-data mutation out of the default provider path.

The narrower existing-row update CR in [UPDATE_HANDLING_FOR_EXISTING_ROWS.md](./UPDATE_HANDLING_FOR_EXISTING_ROWS.md) should then be handled as one downstream implementation scenario alongside other accepted provider-change scenarios from this document.