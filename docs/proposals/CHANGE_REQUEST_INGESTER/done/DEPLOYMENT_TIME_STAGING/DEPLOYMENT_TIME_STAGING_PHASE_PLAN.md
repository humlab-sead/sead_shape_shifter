# Deployment-Time Staging Phase Plan

## Summary

Sequence the [Deployment-Time Staging proposal](./DEPLOYMENT_TIME_STAGING.md) from reviewed aggregate ownership and target ID generators through a shared staging flow. Prove reference-only ID mappings, locked sequence allocation, FK resolution, and `unique_sets` checks with inline output before validating copy-CSV parity and Sqitch deployment. Current direct-to-target output remains the default during isolated validation.

## Problem

The ingester reserves non-SIMS sequence IDs during bundle generation and writes resolved parent IDs into child FKs before rendering SQL. It cannot yet preserve local relationships while SEAD allocates aggregate-child IDs at deployment.

## Scope

This plan covers model-driven aggregate-child eligibility, reference-only ID mappings in the bundle, staging and FK resolution, deployment-time `unique_sets` checks, locked sequence synchronization, inline-INSERT and copy-CSV parity, and transactional Sqitch validation. A tracked fact root is inserted with its children in the same submission; an existing reconciled root may supply a known ID. The plan does not change SIMS identity rules, extend or replace existing tracked fact aggregates, remove read-only generation-time collision checks for known IDs and fully resolved derived bridges, or solve repeated imports, resubmissions, or existing-row updates. Only one generated bundle per submission is handed to the Release Cycle.

## Current Position

- The [target-model review](../../../../../resources/target_models/TARGET_MODEL_REVIEW_20261013.md) is in progress. Phase 1 recorded the derived aggregate-child inventory, root-row rules, and deployed generator results; role and requiredness decisions for unrelated entities remain open. The model makes `analysis_entity` a child of `dataset`, without SIMS tracked identity.
- The ingester currently reserves database-sequence IDs during preparation. Package assembly drops reference-only rows after projection. Inline-INSERT emits static inserts, while copy-CSV loads directly into target tables. Neither strategy carries reference-only ID mappings or maps deployment-generated IDs back to local references.
- Generation-time collision checks inspect projected target IDs and derived-bridge unique sets against target rows. They do not check duplicates within the submitted bundle and currently reject unresolved child IDs. Staging must retain checks for known values and check complete `unique_sets` after FK resolution, including child facts and derived bridges.
- The proposal specifies normal transactional, registry-aware Sqitch deployment; this staging behavior is not implemented yet.
- The current Change Control tag-deploy path checks Sqitch's result before post-deploy hooks. Phase 3 must validate failure propagation through each supported release path before staging is promoted.
- The existing [Phase 1 task plan](./DEPLOYMENT_TIME_STAGING_PHASE_1_TASK_PLAN.md) records Phase 1 as complete, with `V-1`–`V-7` passed and `VM-1` satisfied.

## Phase Plan

### Phase 1: Establish Aggregate And Target-ID Eligibility

**Goal**

Define which model-derived children can safely receive deployment-time IDs and how their target sequences will be synchronized.

**Focus**

- Review the MVP entities' aggregate-parent assignments and use shared effective-identity rules to derive children with valid, acyclic `aggregate_parent` chains ending at tracked or reconciled roots. For each inserted child, a tracked fact root must be inserted by the same submission or a reconciled root must have a resolved target ID. Do not maintain an entity allowlist or infer ownership from role or FK shape.
- Validate the candidate inventory against deployed sequence or identity metadata, including unsupported or missing ID generators, sequence cache behavior, and invalid parent chains. Resolve each target table to one schema-qualified relation and establish stable-order table locking before sequence synchronization and allocation. The release workflow excludes concurrent writes and independent sequence allocation on affected tables.
- Derive eligibility without requiring `public_id_generation: database_sequence` as an opt-in. New `value_type` roots and the semantic role decision for `value_type_item` remain outside this work; children of an existing `value_type` remain eligible when the root ID is resolved.
- Establish the schema and dependency conditions required before either bundle strategy can use staging.

**Depends On**

- The confirmed `analysis_entity` ownership and child-of-reconciled-parent policy in the proposal. Access to a representative deployed SEAD schema is needed to complete this phase.

**Outputs**

- Reviewed, derived eligibility inventory and supported/unsupported ID-generation contract, including root-row rules, sequence cache checks, and stable-order locking before synchronization.

**Acceptance Criteria**

- `PH1-AC-1` (from `P-AC-10`) Each candidate is derived from effective `child` identity and a valid parent chain ending at a tracked or reconciled root, without an entity allowlist. For each inserted child row, a tracked fact root must be inserted by the same submission or a reconciled root must have a resolved target ID.
- `PH1-AC-2` (from `P-AC-3`, `P-AC-9`, `P-AC-10`) Missing or unsupported generators, unsafe sequence cache behavior, ambiguous target relations, invalid parent chains, and dependency cycles have explicit failure results. The supported contract specifies stable-order table locking before synchronizing an out-of-date sequence or allocating IDs.

**Validation Milestones**

- `VM-1` The reviewed model and representative deployed schema yield a reproducible candidate inventory, root-row eligibility results, generator support results, and locking requirements (`PH1-AC-1`, `PH1-AC-2`).

**Task-Plan Handoff**

- Source: `P-AC-3`, `P-AC-9`, `P-AC-10`; preserve tracked-root SIMS identities, require newly inserted tracked fact roots, allow reconciled roots with known target IDs, and reject ambiguous ownership. Verify deployed generator and cache metadata, table-lock ordering, and the no-concurrent-writes release rule before deciding enabled entities.

**Readiness**

Complete. The [Phase 1 task plan](./DEPLOYMENT_TIME_STAGING_PHASE_1_TASK_PLAN.md) records every area and `V-1`–`V-7` as passed, so `VM-1` is satisfied. The inventory and target-ID contract are recorded in the [target-model review](../../../../../resources/target_models/TARGET_MODEL_REVIEW_20261013.md): section 11 holds the derived chains and root-row rules, and section 13 holds the deployed generator, cache, locking, and clone results. Two results carry into Phase 2 without blocking it: staging has the model's `target_table` names in both `public` and `clearing_house`, and `value_type_item` has no usable ID generator.

### Phase 2: Resolve IDs And FKs Through Inline Staging

**Goal**

Prove deployment-time ID allocation, reference-only mappings, FK resolution, and unique-set validation with one staged inline-INSERT bundle.

**Focus**

- Stage insert rows with local `system_id` and FK values separate from target IDs and FKs. Carry `(entity, system_id, target ID)` records for reference-only rows used by staged FKs, without inserting those rows. Seed the map with known references and SIMS assignments; allow different local references to map to the same existing target row. Never write local IDs to target tables.
- Lock affected tables in stable order, synchronize supported sequences when needed, allocate child IDs during deployment, and resolve multi-row and multi-level relationships without row-order or payload matching.
- After FK resolution, reject duplicate complete `unique_sets` among staged rows or against target rows, including child facts and derived bridges. Reject duplicate or conflicting mappings, missing required FKs, and unsupported generators before target inserts. Keep sequence allocation out of bundle generation, and retain generation-time collision checks only for known IDs and fully resolved derived-bridge sets.

**Depends On**

- Phase 1's reviewed eligibility and target-ID contract.

**Outputs**

- A validated shared staging flow exercised through an isolated inline artifact, including known-reference mappings and deployment-time unique-set checks. The current direct-to-target renderer remains the default until Phase 3 promotion; it is not a fallback for unresolved staged child IDs.

**Acceptance Criteria**

- `PH2-AC-1` (from `P-AC-1`, `P-AC-2`, `P-AC-3`, `P-AC-8`) Inline staging allocates child IDs only at deployment after locking affected tables, retains local IDs and FKs outside target rows, and maps identical-payload rows correctly regardless of input order. Unsupported sequence cache behavior fails before target inserts.
- `PH2-AC-2` (from `P-AC-7`, `P-AC-9`, `P-AC-11`) Duplicate or conflicting mappings, unresolved required FKs, unsupported generators, cycles, and complete `unique_sets` duplicated among staged rows or matching existing target rows fail before target inserts. Generation-time diagnostics remain available for known IDs and fully resolved derived-bridge sets without rejecting unresolved child IDs.
- `PH2-AC-3` (from `P-AC-6`, `P-AC-10`) The inline artifact carries reference-only local-to-target mappings without inserting those rows; different local references may resolve to the same existing target row. Children of resolved reconciled roots and newly inserted tracked fact roots resolve; children of existing tracked fact roots are rejected. Explicit SIMS IDs retain sequence synchronization.

**Validation Milestones**

- `VM-2` Disposable PostgreSQL deployment of leaf, multi-row, multi-level, and existing-reconciled-root inline cases preserves ID/FK mapping, reference-only mappings to a shared existing target row, and prior SIMS behavior. An out-of-date sequence and a competing writer confirm lock behavior (`PH2-AC-1`, `PH2-AC-3`).
- `VM-3` Invalid model, mapping, generator, root-row, and unique-set cases fail before target inserts, including child facts and derived bridges under a generated parent ID; generation-time checks skip only values unavailable until deployment (`PH2-AC-2`, `PH2-AC-3`).

**Task-Plan Handoff**

- Source: `P-AC-1`–`P-AC-3`, `P-AC-6`–`P-AC-11`; use Phase 1's generator, root-row, locking, and cache contract. Carry reference-only mappings, retain local/target FK separation, check complete unique sets after FK resolution, and preserve SIMS and known-ID collision behavior. Treat inline staging as isolated validation until copy-CSV parity and Sqitch validation in Phase 3.

**Readiness**

Ready for a task plan. Phase 1 delivered the reviewed eligibility, root-row rules, generator dispositions, and lock contract, and no additional design decision is identified. Phase 2 must resolve each target table to one schema-qualified relation and treat `value_type_item` as unsupported before writing target rows.

### Phase 3: Reach Bundle Parity And Validate Sqitch Deployment

**Goal**

Support both deploy strategies under the same mapping and validation contract, then validate release-time atomicity before promotion.

**Focus**

- Load copy-CSV payloads and reference-only ID mappings into staging. Share the locking, sequence allocation, ID-map, FK resolution, complete `unique_sets` checks, and target-insert behavior proven by inline staging.
- Exercise both strategies through normal transactional, registry-aware Sqitch deployment, including SQL and `\copy` error-stop behavior, rollback, temporary-table cleanup, and retry.
- Promote staging for supported submissions as a bundle-level path. Do not mix staged and direct target inserts within an ID/FK dependency graph; reject unsupported schema mechanisms and cycles rather than silently falling back to generation-time ID reservation.
- Validate that the current Change Control tag-deploy path and any other supported release path report Sqitch failures and skip post-deploy hooks after a failed change.

**Depends On**

- Phase 2's validated inline mapping flow, Phase 1's supported-entity contract, and access to the Change Control deploy runner and a disposable deployment database.

**Outputs**

- Validated inline and copy-CSV staging bundles with matching reference mappings and unique-set checks, plus release-path checks suitable for replacing generation-time child sequence reservation.

**Acceptance Criteria**

- `PH3-AC-1` (from `P-AC-4`, `P-AC-6`–`P-AC-8`) Inline-INSERT and copy-CSV deployments preserve the same local-to-target mappings and valid child FKs for leaf, multi-row, multi-level, and reference-only-parent cases. Both reject complete `unique_sets` duplicated among staged rows or matching existing target rows after FK resolution; sequence values need not match across runs.
- `PH3-AC-2` (from `P-AC-5`, `P-AC-7`, `P-AC-9`) Supported release paths report SQL or `\copy` errors before post-deploy hooks, roll back target rows, and drop temporary tables. Sqitch retries consult its registry; unsupported cases fail explicitly.
- `PH3-AC-3` (from `P-AC-1`, `P-AC-3`, `P-AC-6`, `P-AC-10`, `P-AC-11`) Promoted bundles no longer reserve supported child IDs during generation. They retain root eligibility, locked sequence synchronization, SIMS identity behavior, reference-only mappings, and generation-time collision diagnostics for known values.

**Validation Milestones**

- `VM-4` Equivalent disposable-database relationship, reference-only-parent, and unique-set cases pass or fail alike for both bundle strategies (`PH3-AC-1`).
- `VM-5` Supported release paths stop on SQL and `\copy` errors, leave no partial target rows or temporary tables, skip hooks after failure, and use Sqitch's registry on retry; sequence gaps after failure are acceptable (`PH3-AC-2`).
- `VM-6` Regression checks confirm no child sequence reservation during generation and no loss of root eligibility, lock and sequence behavior, SIMS handling, reference mappings, or known-value collision diagnostics (`PH3-AC-3`).

**Task-Plan Handoff**

- Source: `P-AC-1`, `P-AC-3`–`P-AC-11`; use the Phase 2 mapping, locking, and unique-set contract for both strategies. Validate the current Change Control tag-deploy behavior and any other supported release path. Preserve one-bundle-per-submission handoff; repeated-import idempotency and existing-row updates remain separate work.

**Readiness**

Requires the Phase 2 inline flow and Phase 1 supported-entity contract to be validated before task planning for promotion.

## Cross-Phase Rules

- Model metadata defines aggregate ownership; the deployed schema defines supported ID generation. A tracked fact root must be inserted with its children; a reconciled root may already exist with a resolved ID. Do not guess ownership or mappings from entity names or payload order.
- Carry reference-only local-to-target mappings in the bundle for staged FKs, without inserting those rows. Different local references may resolve to the same existing target row.
- Lock affected target tables in stable order before reading their IDs or synchronizing sequences, and hold locks through insertion. Exclude concurrent writes and independent sequence allocation on those tables; fail closed for unsafe sequence cache behavior.
- Keep current direct-to-target behavior as the default until the replacement is validated for both strategies. After promotion, never use direct insertion or generation-time child-ID reservation as a fallback for an unresolved staged child.
- Keep SIMS identity allocation and generation-time read-only checks for known IDs and fully resolved derived-bridge sets. After FK resolution, check `unique_sets` whose columns are all present and non-null against staged and target rows, even without matching target constraints.
- Use normal transactional Sqitch application with error-stop behavior. Sequence gaps after a failed deployment are acceptable; partial target rows and post-deploy hooks after failure are not.

## Validation Strategy

Validate model and schema eligibility first (`VM-1`), including tracked and reconciled root rules, generator support, sequence cache behavior, and stable-order locking. Then validate inline staging on a disposable database (`VM-2`, `VM-3`), including reference-only mappings, unique-set conflicts, and an out-of-date sequence. Compare both strategies on the same relationship and collision cases (`VM-4`), exercise supported Sqitch release paths on failure and retry (`VM-5`), and run regression checks before promotion (`VM-6`). Exact fixtures, assertions, and commands belong in the phase task plans.
