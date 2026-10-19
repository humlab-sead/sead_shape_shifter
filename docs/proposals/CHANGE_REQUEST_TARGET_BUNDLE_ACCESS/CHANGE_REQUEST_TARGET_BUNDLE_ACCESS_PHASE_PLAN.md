# Change Request Target Bundle Creation — Phase Plan

## Summary

This plan implements the [Change Request target-bundle proposal](./CHANGE_REQUEST_TARGET_BUNDLE_ACCESS.md) as one focused phase. An authenticated principal holding `project:execute` on an authorized saved project may create the bundle; Shape Shifter keeps output in a managed location and limits target-database access to read-only verification queries. The SEAD Release Cycle remains responsible for downstream quality assurance. The phase is blocked until [Hand Normalized Tables To The Ingester In Memory](../IN_MEMORY_INGESTER_HANDOFF/IN_MEMORY_INGESTER_HANDOFF.md) ships, because the permission exception applies only to that composed path.

## Problem

Ingester operations currently require `application:run_ingesters`, including Change Request target-bundle creation. The bundle writer removes an existing same-name directory, so each run will instead use a UTC-timestamped folder and fail if that destination already exists. The original no-target-database requirement also needed reconciliation with shipped behavior: provider-row confirmation already requires a read-only target query, and database-sequence allocation for non-SIMS-tracked entities remains out of scope.

## Scope

This plan covers the permission exception for Change Request target-bundle creation, safe output handling, the operator retry key, and regression checks that other ingester operations retain their current permission requirement.

It does not cover per-source authorization, new project authorization beyond the existing `project:execute` check, target-database writes or sequence allocation, or SEAD Release Cycle review.

## Current Position

- The `sead_change_request` ingester currently writes deploy, revert, and verify SQL files plus a manifest under `IngesterConfig.output_folder`. The handoff first provides a backend-owned `INGEST_OUTPUT_DIR` root for project-only runs. Phase 1 applies that root to Change Request bundle writes and adds exclusive per-run folders.
- Ingester API operations use the `application:run_ingesters` action. The current `sead_change_request` file-ingest route also requires `project:execute` on the saved project named in the request body. The handoff retires that file input; its project-only routes keep `project:execute`.
- The header writer removes an existing bundle directory with the same generated name before writing; the proposed exclusive run folder and fail-on-collision rule replace this behavior.
- Bundle output currently lands under the caller-supplied `output_folder`, and the bundle name (`<date>_DML_<datatype>_<identifier>`) also serves as the manifest `cr_name`, the SQL file names, and the paths inside generated `\copy` statements. The managed root therefore adds only a timestamped run folder above the existing bundle directory, so the artifact contract is unchanged.
- The ingester rejects database-sequence ID generation for SIMS-tracked entities. Phase 1 will not allocate database-sequence IDs for non-SIMS entities either; those IDs must be pre-resolved or generation must reject the affected input.
- The provider-scope cutover requires a read-only target query that confirms the fixed `data_provider` row before SIMS requests, so bundle creation already connects to the target database for verification. The relaxed rule permits this while keeping writes and `nextval` out of generation.
- SIMS replays a batch only for the same scoped `run_id` and payload. The ingester can mint a new `run_id` when one is absent; the entity's configured business `keys` will define stable source identity across later runs.

## Phase Plan

### Phase 1: Allow authorized operators to create Change Request target bundles

**Goal**

Allow an authenticated principal holding `project:execute` on an authorized saved project to create a Change Request target bundle without changing authorization for other ingester operations.

**Focus**

- Remove `application:run_ingesters` only from the composed path's dedicated project-only validation and ingest routes and helper. Keep `project:execute` on both routes, the helper's project-resource guard, and the file-route gates for other ingesters. Change Request file input is retired by the handoff.
- Write each run to its own UTC-timestamped run folder under the `INGEST_OUTPUT_DIR` managed root, keeping the existing bundle name inside it; create the folder exclusively and fail on collision without modifying existing files.
- Confirm bundle creation runs only read-only verification queries against the target database and performs no writes or sequence allocation.
- Preserve stable, idempotent SIMS identity resolution across retries and runs; do not allocate a fresh ID for a previously resolved source identity.
- Let the operator client reuse one run ID across validation, ingestion, and retries for the same submission attempt, and mint a new one when the submission identity changes or a bundle has been written.
- Keep downstream review and quality assurance in the SEAD Release Cycle.

**Depends On**

- [Hand Normalized Tables To The Ingester In Memory](../IN_MEMORY_INGESTER_HANDOFF/IN_MEMORY_INGESTER_HANDOFF.md), which is still proposed and not implemented. Its `P-AC-6` first retires Change Request file input. It then supplies separate project-only validation and ingest routes, client requests, backend-selected ingester inputs, and a guarded helper that validates the project before ingester work, initially gated by both permissions. This phase cannot start before that proposal's `P-AC-1`, `P-AC-8`, `P-AC-10`, `P-AC-11`, `P-AC-12`, and `P-AC-13` ship; removing `application:run_ingesters` from a caller-path route is not an acceptable substitute.

**Outputs**

- Authenticated project executors can create target bundles without the special ingester permission.
- Bundle output and authorization behavior have regression coverage.

**Acceptance Criteria**

- `PH1-AC-1` (from `P-AC-1`) An authenticated principal holding `project:execute` on an authorized saved project can validate and create a Change Request target bundle through the project-only routes without `application:run_ingesters`; the helper accepts the same authorized project without that application action. Unauthenticated callers and principals without `project:execute` are rejected.
- `PH1-AC-2` (from `P-AC-2`) Each run writes to its own UTC-timestamped run folder under the `INGEST_OUTPUT_DIR` managed root, keeping the existing bundle name inside it. An existing destination fails before any file is written and no existing directory is deleted or replaced; bundle creation does not overwrite or remove unrelated files, and `output_path` returns the written bundle directory.
- `PH1-AC-3` (from `P-AC-3`) Bundle creation limits target-database access to read-only verification queries; it does not modify target rows or consume sequence values.
- `PH1-AC-5` (from `P-AC-5`) Repeating a bundle run for a previously resolved identity based on the entity's configured business `keys` reuses its SIMS target ID. For one submission attempt the operator client reuses a single run ID across validation, ingestion, and retries, mints a new run ID when the submission identity changes or a bundle has been written, and that run ID appears in the response and the bundle manifest.
- `PH1-AC-4` (from `P-AC-4`) Other ingester operations retain their existing authorization requirement.

**Validation Milestones**

- `VM-1.1` An authenticated project executor without `application:run_ingesters` can create a bundle; an unauthenticated caller and a principal without `project:execute` are denied (covers `PH1-AC-1`).
- `VM-1.2` Output checks show that each run uses a UTC-timestamped run folder under `INGEST_OUTPUT_DIR` with the bundle name unchanged inside it, that a destination collision writes nothing and deletes nothing, and that unrelated files remain unchanged (covers `PH1-AC-2`).
- `VM-1.3` Runtime checks show only read-only verification queries during bundle creation: no target-table write and no `nextval` call (covers `PH1-AC-3`).
- `VM-1.5` Repeated runs with the same configured business keys retain the assigned target ID; a client retry reuses the persisted run ID and payload, and a new attempt uses a new run ID (covers `PH1-AC-5`).
- `VM-1.4` Authorization checks show other ingester operations still require `application:run_ingesters` (covers `PH1-AC-4`).

**Task-Plan Handoff**

- Preserve the permission exception only for Change Request target-bundle creation through the composed path, and keep the `project:execute` check.
- Keep the managed-root, UTC-timestamped run folder, exclusive creation, fail-on-collision, and read-only target-database requirements. Keep the bundle name and every path it generates (`cr_name`, SQL file names, `\copy` paths) unchanged.
- Use configured business `keys` for stable SIMS source identity and preserve the run ID and payload for retries; output-folder timestamps are not SIMS idempotency keys.
- Carry the run ID in the operator client: optional `run_id` on the submission context type, the current attempt's value in the ingester store, and the run ID named in the pending-confirmation message.
- Do not move SEAD Release Cycle quality assurance into Shape Shifter.
- Reconsider timestamped folder naming and retention separately under [#550](https://github.com/humlab-sead/sead_shape_shifter/issues/550).
- Decide how bundle generation handles non-SIMS-tracked entities configured for database-sequence IDs, and how every SIMS request uses a stable business identity without consuming new IDs on repeated runs.

**Readiness**

Blocked on [Hand Normalized Tables To The Ingester In Memory](../IN_MEMORY_INGESTER_HANDOFF/IN_MEMORY_INGESTER_HANDOFF.md). The task plan is otherwise ready; revisit this phase after the dependency ships.

## Validation Strategy

Validate project-executor access, timestamped managed output, read-only target-database access during bundle creation, stable SIMS IDs across repeated runs, and unchanged authorization for other ingester operations. Keep SQL sequence synchronization in the emitted deployment artifacts distinct from sequence allocation during bundle generation.
