# Deployment-Time Staging Phase Plan

## Summary

Sequence the [Deployment-Time Staging proposal](./DEPLOYMENT_TIME_STAGING.md) from reviewed aggregate ownership through a shared deployment-time ID mapping flow, then promote it only after both bundle strategies and Sqitch deployment are validated. The existing direct-to-target output remains authoritative until staging passes those checks.

## Problem

The ingester reserves non-SIMS sequence IDs during bundle generation and writes resolved parent IDs into child FKs before rendering SQL. It cannot yet preserve local relationships while SEAD allocates aggregate-child IDs at deployment.

## Scope

This plan covers model-driven aggregate-child eligibility, staging and FK resolution, inline-INSERT and copy-CSV parity, and transactional Sqitch validation. It does not change SIMS identity rules, remove read-only generation-time collision checks, or solve repeated imports, resubmissions, or existing-row updates. Only one generated bundle per submission is handed to the Release Cycle.

## Current Position

- The [target-model review](../../../../resources/target_models/TARGET_MODEL_REVIEW_20261013.md) is in progress; aggregate ownership and the eligible-entity inventory are not final.
- The ingester currently reserves database-sequence IDs during preparation. Inline-INSERT emits static inserts, while copy-CSV loads directly into target tables. Neither strategy maps deployment-generated IDs back to local parent references.
- Generation-time collision checks inspect projected target IDs and derived-bridge unique sets. They remain quality-of-service diagnostics, not a guarantee against duplicate imports.
- The proposal specifies normal transactional, registry-aware Sqitch deployment; this staging behavior is not implemented yet.

## Phase Plan

### Phase 1: Establish Aggregate And Target-ID Eligibility

**Goal**

Define which model-derived children can safely receive deployment-time IDs.

**Focus**

- Use the completed target-model review and shared effective-identity rules to derive children whose `aggregate_parent` chain reaches one tracked root; do not maintain an entity allowlist or infer ownership from role or FK shape.
- Validate the candidate inventory against deployed sequence or identity metadata, including unsupported or missing ID generators and invalid parent chains.
- Establish the schema and dependency conditions required before either bundle strategy can use staging.

**Depends On**

- Completion of the target-model review's aggregate-ownership decisions and access to a representative deployed SEAD schema.

**Outputs**

- Reviewed, derived eligibility inventory and supported/unsupported ID-generation contract for staging.

**Acceptance Criteria**

- `PH1-AC-1` (from `P-AC-10`) Each candidate is derived from effective `child` identity and a unique effective `tracked` root; invalid chains are rejected without a hard-coded allowlist.
- `PH1-AC-2` (from `P-AC-9`, `P-AC-10`) A missing or unsupported target ID generator and an unsupported dependency cycle are identified before the entity is enabled for insertion.

**Validation Milestones**

- `VM-1` The reviewed model and representative deployed schema yield a reproducible candidate inventory and explicit unsupported-case results (`PH1-AC-1`, `PH1-AC-2`).

**Task-Plan Handoff**

- Source: `P-AC-9`, `P-AC-10`; preserve tracked-root SIMS identities and reject ambiguous ownership. Blocking input: finish the model review and verify deployed schema metadata before deciding enabled entities.

**Readiness**

Requires completed aggregate-ownership decisions in the target-model review and a representative deployed schema before a task plan can fix the eligibility and validation scope.

### Phase 2: Resolve IDs And FKs Through Inline Staging

**Goal**

Prove deployment-time ID allocation and local-to-target FK mapping with one staged inline-INSERT bundle.

**Focus**

- Stage submitted `system_id` and local FK values separately from resolved IDs and target FKs; include known references and SIMS-assigned IDs in a unique deployment-local map.
- Allocate supported child IDs during deployment, resolve multi-row and multi-level relationships without row-order or payload matching, and insert in dependency order.
- Reject duplicate or ambiguous mappings, missing required FKs, and unsupported generation before commit. Keep sequence allocation out of bundle generation.

**Depends On**

- Phase 1's reviewed eligibility and target-ID contract.

**Outputs**

- A validated shared ID-resolution flow exercised through inline staging; direct-to-target remains the fallback for behavior not yet proven.

**Acceptance Criteria**

- `PH2-AC-1` (from `P-AC-1`, `P-AC-2`, `P-AC-3`, `P-AC-8`) Inline staging allocates child IDs only at deployment, retains local IDs and FKs outside target rows, and maps identical-payload rows correctly regardless of input order.
- `PH2-AC-2` (from `P-AC-7`, `P-AC-9`) Duplicate or conflicting mappings, unresolved required FKs, unsupported generators, and cycles fail before target rows commit.
- `PH2-AC-3` (from `P-AC-6`, `P-AC-11`) Existing and SIMS-assigned IDs still resolve, explicit SIMS IDs retain sequence synchronization, and existing generation-time collision diagnostics remain available.

**Validation Milestones**

- `VM-2` Disposable PostgreSQL deployment of leaf, multi-row, and multi-level inline cases preserves ID/FK mapping and prior ID behavior (`PH2-AC-1`, `PH2-AC-3`).
- `VM-3` Invalid-model, mapping, and target-ID cases leave no partial target rows (`PH2-AC-2`).

**Task-Plan Handoff**

- Source: `P-AC-1`–`P-AC-3`, `P-AC-6`–`P-AC-9`, `P-AC-11`; use Phase 1's supported-entity contract, retain local/target FK separation, and preserve SIMS and collision behavior. Do not promote staging until copy-CSV parity and Sqitch validation in Phase 3.

**Readiness**

Requires Phase 1's reviewed eligibility and target-ID contract; no additional design decision is identified.

### Phase 3: Reach Bundle Parity And Validate Sqitch Deployment

**Goal**

Support both deploy strategies under the same mapping contract and validate release-time atomicity before promotion.

**Focus**

- Load copy-CSV payloads into staging and share the ID-map, FK resolution, and target-insert semantics proven by inline staging.
- Exercise both strategies through the normal transactional, registry-aware Sqitch path, including error-stop behavior, cleanup, failure, and retry.
- Promote staging only for supported entities and validated cases; keep unsupported schema mechanisms and cycles as explicit failures rather than silently falling back to generation-time ID reservation.

**Depends On**

- Phase 2's validated inline mapping flow and Phase 1's supported-entity contract.

**Outputs**

- Validated inline and copy-CSV staging bundles and release-path checks suitable for replacing generation-time child sequence reservation.

**Acceptance Criteria**

- `PH3-AC-1` (from `P-AC-4`, `P-AC-8`) Inline-INSERT and copy-CSV deployments each map every local row to its own generated target ID and valid child FKs for leaf, multi-row, and multi-level cases; sequence values need not match across runs.
- `PH3-AC-2` (from `P-AC-5`, `P-AC-7`, `P-AC-9`) Sqitch deployment stops on SQL or copy errors, rolls back target rows and drops temporary tables; retries do not replay an already-deployed change, and unsupported cases fail explicitly.
- `PH3-AC-3` (from `P-AC-1`, `P-AC-6`, `P-AC-11`) Promoted bundles no longer reserve supported child IDs during generation while retaining SIMS identity behavior, sequence synchronization, and generation-time collision diagnostics.

**Validation Milestones**

- `VM-4` Equivalent disposable-database deployment cases pass for both bundle strategies (`PH3-AC-1`).
- `VM-5` Sqitch failure and retry checks confirm atomic target writes and registry-aware reapplication behavior; sequence gaps after failed deployments are acceptable (`PH3-AC-2`).
- `VM-6` Regression checks confirm no child sequence reservation in generation and no loss of SIMS or collision-check behavior (`PH3-AC-3`).

**Task-Plan Handoff**

- Source: `P-AC-1`, `P-AC-4`–`P-AC-9`, `P-AC-11`; use the Phase 2 mapping contract for both strategies. Preserve one-bundle-per-submission handoff; repeated-import idempotency and existing-row updates remain separate work.

**Readiness**

Requires the Phase 2 inline flow and Phase 1 supported-entity contract to be validated before task planning for promotion.

## Cross-Phase Rules

- Model metadata defines aggregate ownership; the deployed schema defines supported ID generation. Do not guess either from entity names or payload order.
- Keep current direct-to-target behavior authoritative until the replacement is validated for both strategies; never silently reserve child IDs during generation as a fallback.
- Keep SIMS identity allocation and existing read-only target collision checks separate from deployment-time child-ID allocation. Target constraints remain the final collision safeguard.
- Use normal transactional Sqitch application. Sequence gaps after a failed deployment are acceptable; partial target rows are not.

## Validation Strategy

Validate model and schema eligibility first (`VM-1`), then isolated and disposable-database mapping behavior for inline staging (`VM-2`, `VM-3`). Compare both strategies on the same relationship cases (`VM-4`), exercise Sqitch failure and retry behavior (`VM-5`), and run regression checks before promotion (`VM-6`). Exact fixtures, assertions, and commands belong in the phase task plans.
