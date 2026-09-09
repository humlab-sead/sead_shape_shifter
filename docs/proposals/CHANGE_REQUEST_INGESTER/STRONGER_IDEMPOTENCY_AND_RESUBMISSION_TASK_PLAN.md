# Task Plan: Stronger Idempotency And Re-submission

## Phase Summary

- Status: Proposed next phase; scope acceptance pending
- Preceding phase: [Sead Change Request Submission Metadata](REFACTOR_SEAD_SUBMISSION_METADATA_TASK_PLAN.md)
- Candidate source: [Sead Change Request Next Delivery Candidates](future/NEXT_DELIVERY_CANDIDATES.md)
- Design diagrams: [Stronger Idempotency And Re-submission Design Diagrams](STRONGER_IDEMPOTENCY_AND_RESUBMISSION_TASK_DIAGRAMS.md)
- Goal: make exact reruns and partially overlapping re-submissions produce deterministic outcomes without duplicate target rows or ambiguous change packages

This plan proposes stronger idempotency and re-submission behavior as the next focused capability after submission metadata. It builds on the implemented lifecycle outcome classification and existing-row update handling. Remaining validation or deployment work in the preceding phase does not block planning of this phase unless it exposes a contract conflict.

**Acceptance Criteria**

- [ ] Exact reruns are identified and complete without duplicate entity, bridge, association, dataset, or submission rows.
- [ ] Partially overlapping re-submissions distinguish unchanged rows, accepted new rows, allowed updates, pending-review rows, and blocked conflicts.
- [ ] Reuse of a submission identifier or other package identity with conflicting content is rejected with actionable diagnostics.
- [ ] Source duplicates are rejected or collapsed by an explicit rule before SIMS allocation, Binding Set mutation, or change-request association.
- [ ] Retries after an interrupted run reuse completed identity work and do not allocate a second set of target IDs.
- [ ] Idempotency decisions are made before SQL or copy artifacts are finalized.
- [ ] Generated artifacts guard the target assumptions used during preflight so stale packages fail instead of silently duplicating or overwriting data.
- [ ] Inline INSERT and copy-CSV strategies produce equivalent decisions and operator-visible outcomes.
- [ ] Existing provider lifecycle rules remain authoritative for no-op, update, review, and blocked outcomes.

## Work Breakdown

### 1. Define The Re-submission Contract

**Objective**

Define the inputs and comparison rules used to recognize an exact rerun, partial overlap, or conflicting re-submission.

**Tasks**

- [ ] Select the stable idempotency key used to identify the same logical submission across runs.
- [ ] Identify the authoritative store and lookup path for prior submission identity, Binding Set identity, target IDs, and applied change requests.
- [ ] Define whether the same idempotency key with changed content is a revision, a conflicting reuse, or an unsupported case.
- [ ] Define which normalized inputs participate in content equivalence and which generated, audit, timestamp, or operational fields are excluded.
- [ ] Define canonical comparison rules for null values, data types, ordering, and equivalent textual or numeric representations.
- [ ] Define row identity for entities and datasets whose target metadata does not provide a complete unique key.
- [ ] Define outcomes for exact rerun, partial overlap, conflicting identity reuse, and indeterminate comparison.
- [ ] Define how the contract composes with existing `new_data`, `no_op`, `allowed_update`, `pending_review`, and `blocked` outcomes.
- [ ] Define when a successful no-op may reuse an existing submission and when no submission row or change package is created.
- [ ] Define retry behavior after failures before confirmation, after allocation, after package generation, and after target deployment.
- [ ] Define the durable run states, transitions, and ownership rules used to resume work and serialize concurrent requests for the same idempotency key.
- [ ] Record the accepted rules in the active proposal or durable ingester documentation before implementation is treated as complete.

**Completion Criteria**

The accepted contract names the idempotency key, authoritative prior-run data, comparison rules, side-effect rules, and outcome for every supported retry point. Unsupported or indeterminate cases map to `blocked` or `pending_review` rather than proceeding silently.

### 2. Validate And Normalize Incoming Rows

**Objective**

Detect source-level duplicates and create deterministic comparison input before any external identity side effects.

**Tasks**

- [ ] Normalize comparison values according to the accepted null, type, and representation rules without changing rendered target values unexpectedly.
- [ ] Build deterministic row keys from target-model identity or unique-set metadata.
- [ ] Detect identical duplicate rows within each incoming entity and apply the accepted collapse or rejection rule.
- [ ] Detect rows that share an identity key but carry conflicting values and block them with field-level diagnostics.
- [ ] Validate references from bridge and association rows after source duplicate handling.
- [ ] Block rows whose identity metadata is incomplete rather than falling back to full-row or target-ID comparison.
- [ ] Complete source duplicate validation before SIMS allocation, Binding Set confirmation, or change-request association.

**Completion Criteria**

Each incoming row has one deterministic comparison key, conflicting source rows are blocked with actionable details, and no external identity state changes before source validation succeeds.

### 3. Add Prior-Run Lookup And Preflight Classification

**Objective**

Classify the incoming submission against prior-run identity and a consistent view of current target data before artifact generation.

**Tasks**

- [ ] Extend preflight checks beyond primary-key collisions and bridge uniqueness to the accepted re-submission contract.
- [ ] Look up the idempotency key and associated prior submission, Binding Set, target IDs, and change request before allocating new identities.
- [ ] Atomically claim or lock an idempotency key before external identity work so concurrent requests cannot allocate independently.
- [ ] Persist resumable checkpoints after identity allocation, package generation, target deployment acknowledgement, and SIMS association.
- [ ] Reuse confirmed identity assignments from a compatible interrupted or completed run.
- [ ] Reject prior-run records whose stored project, provider, target model, or content identity conflicts with the current request.
- [ ] Reuse existing lifecycle comparison and mutable-field rules for rows that resolve to existing target records.
- [ ] Read all required target rows through one documented consistency model and record the target state used for comparison.
- [ ] Treat target-ID or unique-key matches as comparison candidates, not automatic no-ops or collisions.
- [ ] Detect exact target matches only after comparing all fields required by the accepted equivalence rule.
- [ ] Detect partial overlap and retain only accepted new or update-eligible work in the plan.
- [ ] Detect conflicting reuse of package or submission identity and report the conflicting fields and affected rows.
- [ ] Preserve hard-failure behavior for target rows that match an allocated ID but fail the accepted identity or equivalence checks.
- [ ] Stop artifact generation when any unresolved conflict makes the package unsafe to apply.

**Completion Criteria**

The complete row plan contains explicit outcomes and prior-run identity decisions before rendering starts. No row is classified as a no-op from target-ID presence alone, and compatible retries do not allocate replacement target IDs.

### 4. Make Artifact Generation And Deployment Replay-Safe

**Objective**

Ensure both deploy strategies render only the work approved by preflight classification.

**Tasks**

- [ ] Exclude exact-match and no-op rows from generated inserts and updates.
- [ ] Preserve accepted new rows and lifecycle-approved updates in deterministic order.
- [ ] Ensure bridge and association rows are emitted only when their accepted uniqueness rules identify them as new.
- [ ] Prevent an all-no-op rerun from producing a misleading deploy package.
- [ ] Define the artifact or result returned for an all-no-op run.
- [ ] Keep inline INSERT and copy-CSV rendering behavior equivalent.
- [ ] Include re-submission classification counts and reasons in package metadata or the existing diagnostics result.
- [ ] Carry the idempotency key and prior-run linkage in package metadata without treating generated values as comparison inputs.
- [ ] Add deployment-time guards for target IDs, accepted unique keys, and expected existing-row baselines used during preflight.
- [ ] Ensure copy-CSV deployment applies equivalent guards before inserting or updating staged rows.
- [ ] Make stale-target guard failures explicit and atomic so a package cannot be partially applied.
- [ ] Associate the change request with SIMS only once and only at the accepted completion point.

**Completion Criteria**

Replaying accepted input cannot generate duplicate DML or duplicate SIMS association. Both deploy strategies use equivalent target-state guards and represent no-op, partial, blocked, and stale-package outcomes consistently.

### 5. Expose Operator Outcomes

**Objective**

Make re-submission decisions understandable before an operator accepts or downloads a package.

**Tasks**

- [ ] Present exact-rerun, partial-re-submission, and conflicting-identity outcomes through the existing ingester result contract.
- [ ] Show counts for new, unchanged, updated, pending-review, and blocked rows.
- [ ] Provide row-level reasons for blocked conflicts and indeterminate comparisons.
- [ ] Distinguish source duplicate conflicts, prior-run identity conflicts, target-data conflicts, and stale-package deployment failures.
- [ ] Show whether prior identity assignments or an existing submission were reused.
- [ ] Prevent artifact actions when preflight blocks the run.
- [ ] Distinguish a successful no-op from a failed or blocked run.

**Completion Criteria**

An operator can determine whether a rerun changes target data, does nothing, or requires correction or review without inspecting generated SQL.

### 6. Validate Repeated, Interrupted, And Overlapping Runs

**Objective**

Prove the contract through repeated execution and regression coverage.

**Tasks**

- [ ] Add focused tests for exact reruns of insert-only submissions.
- [ ] Add focused tests for exact reruns containing lifecycle-approved updates.
- [ ] Add tests for partial overlap across entities, datasets, bridges, and associations.
- [ ] Add tests for identical and conflicting duplicate rows within one incoming submission.
- [ ] Add tests for conflicting submission or package identity reuse.
- [ ] Add tests for comparison normalization, including null, type, ordering, and equivalent representation cases.
- [ ] Add tests for all-no-op results and blocked artifact suppression.
- [ ] Add tests proving source validation fails before identity allocation or Binding Set mutation.
- [ ] Add retry tests for interruption before confirmation, after allocation, after artifact generation, and after deployment.
- [ ] Add concurrent-run tests proving requests with the same idempotency key cannot allocate or apply independently.
- [ ] Add stale-target tests where data changes between preflight and deployment.
- [ ] Add tests proving target-ID presence alone does not suppress conflicting content.
- [ ] Run equivalent scenarios through inline INSERT and copy-CSV output.
- [ ] Execute first-run, exact-rerun, interrupted-rerun, partial-overlap, and stale-package scenarios against a disposable PostgreSQL database using the accepted upstream submission schema.
- [ ] Verify failed or blocked scenarios leave no partial target writes or duplicate external identity associations.
- [ ] Run the relevant backend, frontend, and target-model regression checks.

**Completion Criteria**

Automated tests and disposable-database runs demonstrate deterministic results for exact reruns, interrupted retries, partial overlap, conflicts, and stale packages without weakening existing lifecycle behavior.

## Progress Tracker

| Area | Status | Notes |
|---|---|---|
| Re-submission contract | Not started | Accept identity, storage, equivalence, and retry rules before implementation. |
| Source validation | Not started | Must complete before external identity side effects. |
| Prior-run lookup and preflight | Not started | Reuse compatible identity work and build on lifecycle classification. |
| Replay-safe artifacts | Not started | Cover inline INSERT, copy CSV, and deployment-time guards. |
| Operator outcomes | Not started | Reuse the existing ingester result workflow. |
| Validation | Not started | Include repeated, interrupted, and stale-package database execution. |

## Definition Of Done

- [ ] Exact reruns complete as successful no-ops without duplicate target data or misleading deploy artifacts.
- [ ] Partial re-submissions emit only accepted new rows and lifecycle-approved updates.
- [ ] Stable idempotency identity and prior-run lookup are persisted and queryable for the required retention period.
- [ ] Identical and conflicting source duplicates follow documented rules before any external identity side effect.
- [ ] Interrupted retries reuse compatible Binding Set and target-ID assignments.
- [ ] Concurrent requests for the same idempotency key are serialized through an atomic claim and durable run states.
- [ ] Conflicting identity reuse and indeterminate comparisons stop artifact generation with actionable diagnostics.
- [ ] Entity, dataset, bridge, and association behavior is covered.
- [ ] Inline INSERT and copy-CSV behavior is equivalent.
- [ ] Deployment-time guards prevent stale packages from partially applying or silently overwriting changed target data.
- [ ] Operator outcomes distinguish no-op, changed, pending-review, and blocked runs.
- [ ] Focused tests and relevant regression checks pass.
- [ ] Repeated, interrupted, partial-overlap, and stale-package database validation succeeds against the accepted upstream schema.
- [ ] Tests confirm blocked and failed attempts do not create duplicate SIMS associations or partial target writes.
- [ ] Active documentation states the stronger guarantee and its remaining limits.
- [ ] Deferred work is recorded without expanding this phase.

## Validation And Testing

- Focused backend tests for planning, lifecycle composition, collision checks, diagnostics, and artifact rendering.
- Focused frontend tests for no-op, partial, pending-review, and blocked outcomes.
- Target-model tests where uniqueness or submission identity metadata changes.
- Integration tests that run the same normalized input twice and compare outcomes and generated artifacts.
- Integration tests that rerun a submission with a controlled subset of new, unchanged, and changed rows.
- Integration tests that interrupt and retry around external identity and package-generation side effects.
- Integration tests that submit the same idempotency key concurrently.
- Disposable PostgreSQL execution of first run, exact rerun, interrupted rerun, partial re-submission, and stale-package scenarios.
- Existing repository lint, type, build, and regression checks for changed areas.

Exact commands remain `TBD` until implementation identifies the touched test modules and database harness.

## Deliverables

| Deliverable | Description | Status |
|---|---|---|
| Re-submission contract | Accepted identity, equivalence, and outcome rules | Not started |
| Source validation | Deterministic row keys, normalization, and duplicate diagnostics before side effects | Not started |
| Preflight implementation | Prior-run lookup, identity reuse, and target comparison before rendering | Not started |
| Artifact behavior | Guarded, replay-safe inline INSERT and copy-CSV output | Not started |
| Operator diagnostics | Run-level counts and row-level conflict reasons | Not started |
| Validation record | Automated and disposable-database repeated-run results | Not started |
| Documentation update | Stronger guarantee and explicit remaining limits | Not started |

## Scope

**In scope**

- exact reruns of previously accepted submissions
- partially overlapping re-submissions
- duplicates within one incoming submission
- package or submission identity reuse
- retry after interruption at defined processing points
- concurrent requests using the same idempotency key
- target comparison needed to identify no-op and conflicting rows
- entity, dataset, bridge, and association insert behavior
- composition with implemented provider-owned update handling
- equivalent inline INSERT and copy-CSV outcomes
- operator-visible classification and diagnostics

**Out of scope**

- functional rollback
- generalized change detection outside re-submission comparison
- new shared-data ownership or approval rules
- direct provider mutation of shared or system-managed rows
- changes to SCCS internals; deployment guards must use supported SQL or package mechanisms
- replacement of the accepted lifecycle state model
- precise insert ordering unless this phase exposes a concrete failure of deferred constraints
- stronger verify scripts unrelated to replay safety

## Risks And Mitigations

- **Identity rules are too weak:** Different submissions may be treated as reruns. Require explicit stable identity and content-equivalence rules before implementation completion.
- **Identity rules are too strict:** Harmless operational differences may prevent no-op recognition. Exclude generated and operational fields only through documented rules.
- **Target state changes between preflight and deployment:** Generated artifacts may become stale. Encode expected target state in deployment guards and fail atomically rather than silently overwriting changed rows.
- **Retries repeat external side effects:** A failure after SIMS allocation or association may create duplicate identity work. Persist and reuse compatible prior-run identities and make association idempotent.
- **Concurrent requests race before checkpoints exist:** Two workers may allocate against the same key. Claim the key atomically and persist explicit run-state transitions.
- **Source duplicates consume identities:** Duplicate rows may allocate IDs before being rejected. Complete source duplicate checks before external identity work.
- **Overlap logic bypasses lifecycle policy:** A technical match could incorrectly authorize an update. Keep lifecycle ownership and mutable-field rules authoritative.
- **Deploy strategies drift:** Inline and copy-CSV packages may classify the same run differently. Share the row plan and test both renderers with the same scenarios.

## Open Questions

1. Which stable field or field set identifies the same logical submission across reruns?
2. Which system is authoritative for the idempotency key, prior Binding Set, allocated target IDs, and applied change-request status?
3. Does changed content under the same idempotency key represent a revision or a conflicting reuse?
4. Should an all-no-op rerun return metadata-only output, a dedicated no-op result without files, or another existing result form?
5. How long must prior submission identity and comparison data remain queryable?
6. Which target uniqueness rules are sufficiently complete for non-bridge entity and dataset comparison?
7. Which deployment-time guard form works for both inline INSERT and copy-CSV artifacts in SCCS?
8. What target-deployment acknowledgement can move a durable run to the applied state without changing SCCS internals?

## Assumptions

- The submission-metadata phase is finalized for sequencing purposes.
- Stronger idempotency and re-submission behavior is the planning assumption for the next phase; implementation starts after scope acceptance.
- Existing lifecycle classification and update handling remain implemented and authoritative.
- Shared-data requests continue to use current blocked or review-routed behavior until the separate ownership proposal is accepted.