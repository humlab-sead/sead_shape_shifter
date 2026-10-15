# Deployment-Time Staging Phase Plan

## Summary

Sequence the [Deployment-Time Staging proposal](./DEPLOYMENT_TIME_STAGING.md) from reviewed aggregate ownership through a shared deployment-time ID mapping flow, then promote it only after both bundle strategies and Sqitch deployment are validated. Current direct-to-target output remains the default while staging is validated separately.

## Problem

The ingester reserves non-SIMS sequence IDs during bundle generation and writes resolved parent IDs into child FKs before rendering SQL. It cannot yet preserve local relationships while SEAD allocates aggregate-child IDs at deployment.

## Scope

This plan covers model-driven aggregate-child eligibility, staging and FK resolution, inline-INSERT and copy-CSV parity, and transactional Sqitch validation. It does not change SIMS identity rules, remove read-only generation-time collision checks for known IDs and derived bridges, or solve repeated imports, resubmissions, or existing-row updates. Only one generated bundle per submission is handed to the Release Cycle.

## Current Position

- The [target-model review](../../../../resources/target_models/TARGET_MODEL_REVIEW_20261013.md) is in progress; aggregate ownership and the eligible-entity inventory are not final. The current model makes `analysis_entity` a child of `dataset`, without SIMS tracked identity.
- The ingester currently reserves database-sequence IDs during preparation. Inline-INSERT emits static inserts, while copy-CSV loads directly into target tables. Neither strategy maps deployment-generated IDs back to local parent references.
- Generation-time collision checks inspect projected target IDs and derived-bridge unique sets. The current checks reject unresolved child IDs; they must be narrowed to known IDs when staging is introduced. They remain quality-of-service diagnostics, not a guarantee against duplicate imports.
- The proposal specifies normal transactional, registry-aware Sqitch deployment; this staging behavior is not implemented yet.
- Gate 2 (Change Control failure handling) is resolved for planning by [Change Control issue #459](https://github.com/humlab-sead/sead_change_control/issues/459): the `deploy-staging` change captures Sqitch's exit status directly and checks it before post-deploy hooks. Phase 3 still must validate the release path before staging is promoted.

## Phase Plan

### Phase 1: Establish Aggregate And Target-ID Eligibility

**Goal**

Define which model-derived children can safely receive deployment-time IDs.

**Focus**

- Review the MVP entities' aggregate-parent assignments and use shared effective-identity rules to derive children with valid, acyclic `aggregate_parent` chains ending at tracked or reconciled roots. Each inserted child row must have a resolved root target ID; do not maintain an entity allowlist or infer ownership from role or FK shape.
- Validate the candidate inventory against deployed sequence or identity metadata, including unsupported or missing ID generators and invalid parent chains. Resolve each target table to one schema-qualified relation and establish how an out-of-date sequence is synchronized before allocation.
- Replace generation-time reservation for eligible children without requiring the current `public_id_generation: database_sequence` field as an opt-in. New `value_type` roots and the semantic role decision for `value_type_item` remain outside this work; children of an existing `value_type` are not excluded merely because the root is reconciled.
- Establish the schema and dependency conditions required before either bundle strategy can use staging.

**Depends On**

- The confirmed `analysis_entity` ownership and child-of-reconciled-parent policy in the proposal. Access to a representative deployed SEAD schema is needed to complete this phase.

**Outputs**

- Reviewed, derived eligibility inventory and supported/unsupported ID-generation contract for staging, including resolved reconciled roots and sequence synchronization.

**Acceptance Criteria**

- `PH1-AC-1` (from `P-AC-10`) Each candidate is derived from effective `child` identity and a valid parent chain ending at a tracked or reconciled root; invalid chains are rejected without a hard-coded allowlist. Each inserted child row requires a resolved root target ID.
- `PH1-AC-2` (from `P-AC-3`, `P-AC-9`, `P-AC-10`) A missing or unsupported target ID generator, ambiguous target relation, or dependency cycle is identified before the entity is enabled for insertion; an out-of-date sequence can be advanced without reusing an existing ID.

**Validation Milestones**

- `VM-1` The reviewed model and representative deployed schema yield a reproducible candidate inventory and explicit unsupported-case results (`PH1-AC-1`, `PH1-AC-2`).

**Task-Plan Handoff**

- Source: `P-AC-3`, `P-AC-9`, `P-AC-10`; preserve tracked-root SIMS identities, allow reconciled roots with known target IDs, and reject ambiguous ownership. Review the MVP entities' remaining aggregate-parent assignments and verify deployed schema metadata before deciding enabled entities.

**Readiness**

Ready for a Phase 1 task plan. The `analysis_entity` decision and child-of-reconciled-parent rule are settled. Phase 1 must finish the relevant aggregate-parent review and obtain a representative deployed schema to complete its inventory and generator checks; unrelated target-model role decisions do not block task planning.

### Phase 2: Resolve IDs And FKs Through Inline Staging

**Goal**

Prove deployment-time ID allocation and local-to-target FK mapping with one staged inline-INSERT bundle.

**Focus**

- Stage submitted `system_id` and local FK values separately from resolved IDs and target FKs; include known references and SIMS-assigned IDs in a unique deployment-local map. Never write local `system_id` values to target tables.
- Allocate supported child IDs during deployment, resolve multi-row and multi-level relationships without row-order or payload matching, and insert in dependency order.
- Reject duplicate or ambiguous mappings, missing required FKs, and unsupported generation before commit. Keep sequence allocation out of bundle generation, and allow new child IDs to remain unresolved during generation-time collision checks.

**Depends On**

- Phase 1's reviewed eligibility and target-ID contract.

**Outputs**

- A validated shared ID-resolution flow exercised through an isolated inline staging artifact. The current direct-to-target renderer remains the default until Phase 3 promotion; it is not a fallback for unresolved staged child IDs.

**Acceptance Criteria**

- `PH2-AC-1` (from `P-AC-1`, `P-AC-2`, `P-AC-3`, `P-AC-8`) Inline staging allocates child IDs only at deployment, retains local IDs and FKs outside target rows, and maps identical-payload rows correctly regardless of input order.
- `PH2-AC-2` (from `P-AC-7`, `P-AC-9`) Duplicate or conflicting mappings, unresolved required FKs, unsupported generators, and cycles fail before target rows commit.
- `PH2-AC-3` (from `P-AC-6`, `P-AC-11`) Existing and SIMS-assigned IDs still resolve, explicit SIMS IDs retain sequence synchronization, and generation-time collision diagnostics remain available for known IDs and derived bridges without rejecting new child IDs awaiting deployment.

**Validation Milestones**

- `VM-2` Disposable PostgreSQL deployment of leaf, multi-row, and multi-level inline cases preserves ID/FK mapping and prior ID behavior (`PH2-AC-1`, `PH2-AC-3`).
- `VM-3` Invalid-model, mapping, and target-ID cases leave no partial target rows (`PH2-AC-2`).

**Task-Plan Handoff**

- Source: `P-AC-1`–`P-AC-3`, `P-AC-6`–`P-AC-9`, `P-AC-11`; use Phase 1's supported-entity contract, retain local/target FK separation, and preserve SIMS and known-ID collision behavior. Treat inline staging as isolated validation until copy-CSV parity and Sqitch validation in Phase 3.

**Readiness**

Requires Phase 1's reviewed eligibility and target-ID contract; no additional design decision is identified.

### Phase 3: Reach Bundle Parity And Validate Sqitch Deployment

**Goal**

Support both deploy strategies under the same mapping contract and validate release-time atomicity before promotion.

**Focus**

- Load copy-CSV payloads into staging and share the ID-map, FK resolution, and target-insert semantics proven by inline staging.
- Exercise both strategies through the normal transactional, registry-aware Sqitch path, including error-stop behavior, cleanup, failure, and retry.
- Promote staging for supported submissions as a bundle-level path. Do not mix staged and direct target inserts within an ID/FK dependency graph; reject unsupported schema mechanisms and cycles rather than silently falling back to generation-time ID reservation.
- Validate Change Control's corrected Sqitch failure propagation so a failed change cannot trigger post-deploy hooks or appear successful.

**Depends On**

- Phase 2's validated inline mapping flow, Phase 1's supported-entity contract, and access to the Change Control deploy runner and a disposable deployment database.

**Outputs**

- Validated inline and copy-CSV staging bundles and release-path checks suitable for replacing generation-time child sequence reservation.

**Acceptance Criteria**

- `PH3-AC-1` (from `P-AC-4`, `P-AC-8`) Inline-INSERT and copy-CSV deployments each map every local row to its own generated target ID and valid child FKs for leaf, multi-row, and multi-level cases; sequence values need not match across runs.
- `PH3-AC-2` (from `P-AC-5`, `P-AC-7`, `P-AC-9`) Sqitch deployment reports SQL or copy errors before post-deploy hooks, rolls back target rows and drops temporary tables; retries do not replay an already-deployed change, and unsupported cases fail explicitly.
- `PH3-AC-3` (from `P-AC-1`, `P-AC-6`, `P-AC-11`) Promoted bundles no longer reserve supported child IDs during generation while retaining SIMS identity behavior, sequence synchronization, and generation-time collision diagnostics.

**Validation Milestones**

- `VM-4` Equivalent disposable-database deployment cases pass for both bundle strategies (`PH3-AC-1`).
- `VM-5` Sqitch failure and retry checks confirm atomic target writes, no post-deploy hook after failure, and registry-aware reapplication behavior; sequence gaps after failed deployments are acceptable (`PH3-AC-2`).
- `VM-6` Regression checks confirm no child sequence reservation in generation and no loss of SIMS or collision-check behavior (`PH3-AC-3`).

**Task-Plan Handoff**

- Source: `P-AC-1`, `P-AC-4`–`P-AC-9`, `P-AC-11`; use the Phase 2 mapping contract for both strategies. Preserve one-bundle-per-submission handoff; repeated-import idempotency and existing-row updates remain separate work.

**Readiness**

Requires the Phase 2 inline flow and Phase 1 supported-entity contract to be validated before task planning for promotion.

## Cross-Phase Rules

- Model metadata defines aggregate ownership; the deployed schema defines supported ID generation. Do not guess either from entity names or payload order.
- Keep current direct-to-target behavior as the default until the replacement is validated for both strategies. After promotion, never use direct insertion or generation-time child-ID reservation as a fallback for an unresolved staged child.
- Keep SIMS identity allocation and existing read-only target collision checks separate from deployment-time child-ID allocation. Target constraints remain the final collision safeguard.
- Use normal transactional Sqitch application. Sequence gaps after a failed deployment are acceptable; partial target rows are not.

## Validation Strategy

Validate model and schema eligibility first (`VM-1`), including children of resolved reconciled roots and out-of-date sequences. Then validate isolated and disposable-database mapping behavior for inline staging (`VM-2`, `VM-3`). Compare both strategies on the same relationship cases (`VM-4`), exercise Sqitch failure and retry behavior (`VM-5`), and run regression checks before promotion (`VM-6`). Exact fixtures, assertions, and commands belong in the phase task plans.
