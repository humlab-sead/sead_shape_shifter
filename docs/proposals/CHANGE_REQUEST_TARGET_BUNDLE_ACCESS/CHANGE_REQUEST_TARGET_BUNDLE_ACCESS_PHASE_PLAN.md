# Change Request Target Bundle Creation — Phase Plan

## Summary

This plan implements the [Change Request target-bundle proposal](./CHANGE_REQUEST_TARGET_BUNDLE_ACCESS.md) as one focused phase. Any authenticated operator may create the bundle; Shape Shifter keeps output in a managed location and limits target-database access to read-only verification queries. The SEAD Release Cycle remains responsible for downstream quality assurance.

## Problem

Ingester operations currently require `application:run_ingesters`, including Change Request target-bundle creation. The bundle writer removes an existing same-name directory, so each run will instead use a UTC-timestamped folder and fail if that destination already exists. The original no-target-database requirement also needed reconciliation with shipped behavior: provider-row confirmation already requires a read-only target query, and database-sequence allocation for non-SIMS-tracked entities remains out of scope.

## Scope

This plan covers the permission exception for Change Request target-bundle creation, safe output handling, and regression checks that other ingester operations retain their current permission requirement.

It does not cover granular source or project authorization, target-database writes or sequence allocation, or SEAD Release Cycle review.

## Current Position

- The `sead_change_request` ingester writes deploy, revert, and verify SQL files plus a manifest under `IngesterConfig.output_folder`.
- Ingester API operations use the `application:run_ingesters` action.
- The artifact writer removes an existing bundle directory with the same generated name before writing; the proposed timestamped folder and fail-on-collision rule replace this behavior.
- The ingester rejects database-sequence ID generation for SIMS-tracked entities. Phase 1 will not allocate database-sequence IDs for non-SIMS entities either; those IDs must be pre-resolved or generation must reject the affected input.
- The provider-scope cutover requires a read-only target query that confirms the fixed `data_provider` row before SIMS requests, so bundle creation already connects to the target database for verification. The relaxed rule permits this while keeping writes and `nextval` out of generation.
- SIMS replays a batch only for the same scoped `run_id` and payload. The ingester can mint a new `run_id` when one is absent; the entity's configured business `keys` will define stable source identity across later runs.

## Phase Plan

### Phase 1: Allow operators to create Change Request target bundles

**Goal**

Allow any authenticated operator to create a Change Request target bundle without changing authorization for other ingester operations.

**Focus**

- Remove the `application:run_ingesters` requirement only from Change Request target-bundle creation.
- Write each run to a UTC-timestamped folder under an application-managed location; fail on destination collision without modifying existing files.
- Confirm bundle creation runs only read-only verification queries against the target database and performs no writes or sequence allocation.
- Preserve stable, idempotent SIMS identity resolution across retries and runs; do not allocate a fresh ID for a previously resolved source identity.
- Keep downstream review and quality assurance in the SEAD Release Cycle.

**Depends On**

- None; this is a single-phase change.

**Outputs**

- Authenticated operators can create target bundles without the special ingester permission.
- Bundle output and authorization behavior have regression coverage.

**Acceptance Criteria**

- `PH1-AC-1` (from `P-AC-1`) Any authenticated operator can create a Change Request target bundle without `application:run_ingesters`; unauthenticated callers cannot.
- `PH1-AC-2` (from `P-AC-2`) Each run writes to a UTC-timestamped folder under its managed output location. A destination collision fails without modifying existing files, and bundle creation does not overwrite or remove unrelated files.
- `PH1-AC-3` (from `P-AC-3`) Bundle creation limits target-database access to read-only verification queries; it does not modify target rows or consume sequence values.
- `PH1-AC-5` (from `P-AC-5`) Repeating a bundle run for a previously resolved identity based on the entity's configured business `keys` reuses its SIMS target ID; retrying an allocation batch uses the same run ID and payload.
- `PH1-AC-4` (from `P-AC-4`) Other ingester operations retain their existing authorization requirement.

**Validation Milestones**

- `VM-1.1` An authenticated operator without `application:run_ingesters` can create a bundle; an unauthenticated caller is denied (covers `PH1-AC-1`).
- `VM-1.2` Output checks show that each run uses a timestamped managed folder, a destination collision changes nothing, and unrelated files remain unchanged (covers `PH1-AC-2`).
- `VM-1.3` Runtime checks show only read-only verification queries during bundle creation: no target-table write and no `nextval` call (covers `PH1-AC-3`).
- `VM-1.5` Repeated runs with the same configured business keys retain the assigned target ID; retries reuse the persisted run ID and payload (covers `PH1-AC-5`).
- `VM-1.4` Authorization checks show other ingester operations still require `application:run_ingesters` (covers `PH1-AC-4`).

**Task-Plan Handoff**

- Preserve the permission exception only for Change Request target-bundle creation.
- Keep the managed-output, timestamped-folder, fail-on-collision, and read-only target-database requirements.
- Use configured business `keys` for stable SIMS source identity and preserve the run ID and payload for retries; output-folder timestamps are not SIMS idempotency keys.
- Do not move SEAD Release Cycle quality assurance into Shape Shifter.
- Reconsider timestamped folder naming and retention separately under [#550](https://github.com/humlab-sead/sead_shape_shifter/issues/550).
- Decide how bundle generation handles non-SIMS-tracked entities configured for database-sequence IDs, and how every SIMS request uses a stable business identity without consuming new IDs on repeated runs.

**Readiness**

Ready for a task plan.

## Validation Strategy

Validate operator access, timestamped managed output, read-only-only target-database access during bundle creation, stable SIMS IDs across repeated runs, and unchanged authorization for other ingester operations. Keep SQL sequence synchronization in the emitted deployment artifacts distinct from sequence allocation during bundle generation.
