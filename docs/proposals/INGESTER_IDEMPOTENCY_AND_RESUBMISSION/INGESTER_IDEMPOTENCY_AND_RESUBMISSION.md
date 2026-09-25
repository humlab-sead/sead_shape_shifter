# Ingester Idempotency And Re-submission For SEAD Change Requests

## Status

- Proposed change; scope and contract decisions remain pending
- Scope: deterministic reruns, partial overlap, and recovery from interrupted SEAD change request runs
- Goal: prevent duplicate target data and ambiguous deploy packages when an accepted submission is repeated or resumed
- Related planning source: [Stronger Idempotency And Re-submission Task Plan](STRONGER_IDEMPOTENCY_AND_RESUBMISSION_TASK_PLAN.md)
- Supporting diagrams: [Stronger Idempotency And Re-submission Design Diagrams](STRONGER_IDEMPOTENCY_AND_RESUBMISSION_TASK_DIAGRAMS.md)

## Summary

Add a durable submission-run record and a preflight comparison step to the SEAD change request ingester. The ingester should validate source duplicates before identity allocation, reuse identity work from compatible retries, and classify each row against prior-run and target state before producing an artifact. Both deploy strategies should use the same row plan and reject stale target assumptions. The key, storage, equivalence, and deployment-acknowledgement contracts must be decided before implementation.

## Problem

The ingester can classify new data, no-op rows, allowed updates, pending review, and blocked rows, but it does not define a durable request identity or resumable run record. A repeated or interrupted request can therefore repeat identity work, while overlapping input can reach artifact generation without a submission-level comparison against prior work.

Target collision checks run before artifact generation, but a target may change after that check. Without deployment-time guards, an artifact can be applied against different target data than the data used to prepare it. Operators also need to distinguish a successful no-op from a blocked request and to see which rows are new, unchanged, updated, or awaiting review.

## Scope

- Exact reruns and partially overlapping re-submissions.
- Duplicate and conflicting rows within one source submission.
- Stable request identity, content comparison, prior-run lookup, and retry checkpoints.
- Concurrent requests that use the same idempotency key.
- Comparison of entities, datasets, bridges, and associations.
- Composition with existing provider lifecycle outcomes and update rules.
- Equivalent inline INSERT and copy-CSV decisions, diagnostics, and deployment guards.
- Operator-visible run summaries and row-level conflict reasons.

## Non-Goals

- Functional rollback or changes to SCCS internals.
- New ownership or approval rules for shared and system-managed data.
- General change detection outside re-submission comparison.
- Replacement of the existing lifecycle outcome model.
- Unrelated verify-script or insert-ordering changes.

## Current Behavior

The ingester already plans rows using target-model metadata, compares configured mutable fields with existing-row baselines, and classifies outcomes as `new_data`, `no_op`, `allowed_update`, `pending_review`, or `blocked`. Its collision checks test target IDs for insertable entity rows and configured unique sets for bridge rows. These checks run before artifact generation. See [planning.py](../../../ingesters/sead_change_request/planning.py), [contracts.py](../../../ingesters/sead_change_request/contracts.py), and [collision_checks.py](../../../ingesters/sead_change_request/collision_checks.py).

The current workflow has no durable idempotency key or run checkpoint in the SEAD change request ingester. Preparation orchestrates identity assignment before outcome classification. With `validate_first`, ingestion prepares once through validation and then prepares again for ingestion. The workflow also associates the change request with SIMS after building the artifact, before the artifact is written and deployed. See [preparation.py](../../../ingesters/sead_change_request/preparation.py) and [ingester.py](../../../ingesters/sead_change_request/ingester.py).

## Proposed Design

### Request Identity And Durable Run State

Use a stable idempotency key to identify a logical submission and a separately defined content fingerprint to detect changed content under that key. Define normalization, excluded operational fields, and comparison rules before implementation; do not treat generated IDs, timestamps, or package values as source identity without an explicit contract.

Persist run ownership and checkpoints in an authoritative store. The record must retain enough information to reuse a compatible Binding Set, target-ID assignments, generated package identity, and completed external side effects. Atomically claim the key before SIMS allocation so concurrent requests cannot allocate independently. The run store owns request and checkpoint state; SEAD target data remains authoritative for rows already deployed.

The store technology, retention period, lease or ownership rules, and exact state names remain open. Provider reconciliation needed to create derived submission rows must also be classified as read-only or moved behind source validation if it can mutate identity state.

### Source And Target Preflight

Normalize comparison values and construct deterministic row keys from accepted target identity metadata before identity allocation or Binding Set mutation. Apply an explicit rule to identical source duplicates; block rows with the same key and conflicting values, incomplete identity metadata, or indeterminate comparisons. Return field- and row-level diagnostics.

After claiming the request key, load any compatible prior checkpoint before allocating identities. Compare planned rows with one documented, consistent target-state read. A target-ID or unique-key match is a comparison candidate, not proof of equivalence. Classify rows as new, no-op, allowed update, pending review, or blocked using the existing provider lifecycle and mutable-field rules. Do not render an artifact when unresolved conflicts make the package unsafe.

### Replay-Safe Artifacts And Completion

Build one accepted row plan and use it for both inline INSERT and copy-CSV rendering. Exclude no-op rows from DML; retain only accepted new rows and lifecycle-approved updates. Include the idempotency key linkage and outcome counts in package metadata without making generated metadata part of source equivalence. Define a successful all-no-op result that does not emit a misleading deploy package.

Add deployment-time guards for the target IDs, unique keys, and existing-row baselines used during preflight. Inline and copy-CSV deployment must apply equivalent checks and fail atomically when target state is stale. Use supported SQL or package mechanisms without changing SCCS internals. Resolve how deployment acknowledgement reaches the run record before making one-time SIMS change-request association part of completion; do not report a run as applied before that acknowledgement.

### Operator Results

Return counts for new, unchanged, updated, pending-review, and blocked rows. Distinguish source duplicates, prior-run identity conflicts, target-data conflicts, and stale-package failures. Show when existing identity assignments or a prior submission are reused. Block artifact actions for unsafe runs and distinguish successful no-op results from failures.

## Alternatives Considered

- **Rely only on target collision checks:** This does not reuse identity work, distinguish exact reruns from conflicting reuse, or protect against target changes after preflight.
- **Use a submission name or package identifier alone:** These values do not establish that repeated content is equivalent. The contract needs a stable key and separate content comparison.
- **Restart every interrupted request:** This can repeat identity side effects and allocate replacement target IDs, so it does not meet retry requirements.

## Risks And Tradeoffs

- Weak equivalence rules can treat different submissions as reruns; strict rules can reject harmless representation differences. Define normalization and excluded fields explicitly.
- A durable run store adds retention, concurrency, and recovery responsibilities. Its owner and failure behavior must be accepted before implementation.
- Target data can change between preflight and deployment. Guards must cover both strategies and make stale failure atomic.
- Exactly-once SIMS association depends on a reliable deployment acknowledgement and idempotent association behavior. The supported acknowledgement path is not yet known.
- Validation and ingestion currently run preparation separately when `validate_first` is enabled. The implementation must ensure this does not repeat non-idempotent identity work.

## Testing And Validation

Validate first runs, exact reruns, partial overlap, duplicate input, conflicting identity reuse, and all-no-op results. Exercise retries before confirmation, after allocation, after artifact generation, and after deployment, plus concurrent requests sharing one key. Change target rows between preflight and deployment to verify atomic stale-package failure.

Run equivalent scenarios through inline INSERT and copy-CSV strategies. Use focused backend, frontend, and target-model regression tests, and execute repeated-run scenarios against a disposable PostgreSQL database using the accepted upstream submission schema. Verify blocked and failed runs leave no partial target writes or duplicate SIMS associations.

## Acceptance Criteria

- `P-AC-1`: The accepted contract defines the stable idempotency key, content-equivalence rules, normalization, retention, and outcomes for conflicting or indeterminate reuse.
- `P-AC-2`: Identical and conflicting source duplicates are handled by an explicit rule before SIMS allocation, Binding Set mutation, or change-request association.
- `P-AC-3`: A compatible retry reuses confirmed identity assignments, and concurrent requests with one key cannot allocate or apply independently.
- `P-AC-4`: Preflight classifies rows against prior-run and target state while preserving existing lifecycle outcomes; target-ID presence alone never establishes a no-op.
- `P-AC-5`: Both deploy strategies use the same row plan, omit no-op DML, and enforce equivalent atomic guards against stale target state.
- `P-AC-6`: The run is associated with SIMS once at the accepted completion point, based on a supported deployment acknowledgement.
- `P-AC-7`: Operators can distinguish no-op, changed, pending-review, blocked, and stale-package outcomes and see actionable row-level diagnostics.
- `P-AC-8`: Automated tests and disposable-database runs cover exact reruns, partial overlap, interruption, concurrency, duplicate input, and stale packages without partial target writes or duplicate associations.

## Planning Handoff

- Preserve the existing lifecycle outcomes and provider-owned mutable-field rules.
- Treat the run store as authoritative for request identity and checkpoints, and target data as authoritative for deployed rows.
- Resolve the key, content-equivalence, store, retention, concurrency, and all-no-op result contracts before implementation.
- Resolve source-validation ordering around provider reconciliation, deployment-guard representation for both artifact strategies, and the deployment acknowledgement path without changing SCCS internals.
- Map these proposal criteria to phase and task-plan criteria and validation milestones before implementation; the related task plan is linked above.

## Open Questions

1. Which stable field or field set identifies one logical submission, and what changed content under that key is allowed?
2. Which store owns the run record and how long must its identity, checkpoints, and target-ID assignments remain available?
3. Which row identity metadata is sufficient for entities and datasets without a complete unique key?
4. What result should an all-no-op rerun return, and should it create or reuse a submission row?
5. Which target-state consistency model and guard form work for inline INSERT and copy-CSV deployment?
6. What supported SCCS, API, or operator workflow acknowledges deployment before SIMS association?
7. Can provider reconciliation needed for derived submission rows run before duplicate validation without mutating identity state?

## Final Recommendation

Accept the durable-run and preflight direction, but keep implementation blocked on the identity, persistence, comparison, and deployment-acknowledgement contracts. This is the smallest design that can make reruns and retries deterministic while preserving current lifecycle policy and avoiding changes to SCCS internals.