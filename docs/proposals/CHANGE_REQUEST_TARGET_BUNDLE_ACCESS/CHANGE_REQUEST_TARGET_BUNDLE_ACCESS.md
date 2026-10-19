# Proposal: Allow Authorized Operators To Create Change Request Target Bundles

## Status

- Proposed change; implementation is blocked on its dependency
- Scope: Change Request target-bundle creation without a caller-supplied source file
- Goal: let an authenticated principal that holds `project:execute` on an authorized saved project create a target bundle from that project, with no caller-supplied source path, for downstream review by the SEAD Release Cycle
- Blocking dependency: [IN_MEMORY_INGESTER_HANDOFF](../IN_MEMORY_INGESTER_HANDOFF/IN_MEMORY_INGESTER_HANDOFF.md) is still proposed and not implemented. Until it ships, the only bundle route reads a caller-supplied path, which this proposal leaves gated, so no part of this change can be implemented first.

## Summary

Allow an authenticated principal that holds `project:execute` on an authorized saved project to create a Change Request target bundle from that project, with no caller-supplied source file, without the `application:run_ingesters` permission. The route keeps its existing `project:execute` requirement; only the ingester permission is removed. The tables for the composed path come from normalizing the authorized project in memory, as defined in [IN_MEMORY_INGESTER_HANDOFF](../IN_MEMORY_INGESTER_HANDOFF/IN_MEMORY_INGESTER_HANDOFF.md). Shape Shifter writes the bundle to a managed output location. Bundle creation may run read-only verification queries against the target database but must not modify target data or consume sequence values. The SEAD Release Cycle remains responsible for downstream quality assurance.

## Problem

Change Request target-bundle creation produces files for a later release process; it does not update a target database. The operation that needs the relaxed permission also reads no caller-supplied source path: its tables come from normalization of an authorized saved project ([IN_MEMORY_INGESTER_HANDOFF](../IN_MEMORY_INGESTER_HANDOFF/IN_MEMORY_INGESTER_HANDOFF.md)). The route already requires `project:execute` on the saved project named in the request body, so project access is already bound to the run. The ingester permission is a second, deployment-wide gate that does not distinguish this file-generation operation from operations that do update a target database. Keeping it limits this operation more than its effect warrants.

## Scope

- Allow an authenticated principal that holds `project:execute` on an authorized saved project to create a Change Request target bundle from that project, with no caller-supplied source path, without `application:run_ingesters`.
- Keep the existing `project:execute` requirement on the route that serves this operation.
- Write the bundle only to an application-managed output location.
- Limit target-database access in this operation to read-only verification queries.
- Leave authorization for all other ingester operations and for bundle creation from an uploaded source file unchanged.

## Non-Goals

- Changing the `application:run_ingesters` requirement for other ingester operations.
- Removing or relaxing the `project:execute` requirement for this operation, or making bundle creation available to principals without access to the saved project.
- Relaxing the `application:run_ingesters` requirement for bundle creation from a caller-supplied source path. That route keeps its current gate until source path containment is implemented in [INGESTER_AUTHORIZATION_TASKS](../INGESTER_AUTHORIZATION_TASKS/INGESTER_AUTHORIZATION_TASKS.md).
- Adding per-source authorization or a separate bundle-creation permission.
- Implementing the composed in-memory normalization path itself. That work belongs to [IN_MEMORY_INGESTER_HANDOFF](../IN_MEMORY_INGESTER_HANDOFF/IN_MEMORY_INGESTER_HANDOFF.md), and this proposal depends on it.
- Moving the SEAD Release Cycle's review or quality-assurance responsibilities into Shape Shifter.
- Implementing granular Change Request ingester security, which can be reconsidered separately.

## Current Behavior

The ingestion route requires `application:run_ingesters`. For the `sead_change_request` key it also requires `project:execute` on the saved project named in the request body, and answers 404 when the principal has no grant on that project. Its request also carries source and output paths. The ingester permission does not distinguish Change Request target-bundle creation from operations with different effects. See the [ingester route](../../../backend/app/api/v1/endpoints/ingesters.py), [request models](../../../backend/app/models/ingester.py), [authorization dependencies](../../../backend/app/authorization/dependencies.py), and [ingester service](../../../backend/app/services/ingester_service.py).

## Proposed Design

Allow an authenticated principal that holds `project:execute` on an authorized saved project to create a Change Request target bundle from that project, with no caller-supplied source path, without the `application:run_ingesters` permission. Remove only that ingester permission. Keep the `project:execute` check, and keep the existing gate for other ingester operations and for bundle creation from an uploaded source file.

Write each generated bundle under an application-managed output root provided by a new `INGEST_OUTPUT_DIR` setting. The setting resolves under `APPLICATION_ROOT` the same way the existing project, log, and shared-data directories do, and joins them as a managed directory. Each run writes to its own UTC-timestamped run folder below that root, with the existing bundle name kept inside it:

```text
<INGEST_OUTPUT_DIR>/<YYYYMMDDTHHMMSSZ>/<bundle_name>/deploy/<bundle_name>.sql
```

The bundle name keeps its current form (`<date>_DML_<datatype>_<identifier>`), so the manifest `cr_name`, the SQL file names, and the paths used by generated `\copy` statements stay the same. Only the enclosing run folder is new, which is why this layout does not change the artifact contract the SEAD Release Cycle consumes.

The run folder name combines the UTC start time with the effective `run_id`, and directory creation is exclusive, so two runs of the same submission on the same day cannot collide. If the destination already exists, bundle creation fails before writing any file and never deletes or replaces an existing directory.

`IngestRequest.output_folder` stays in the request model for other ingesters but is ignored for `sead_change_request`; the managed root decides the location. `IngestResponse.output_path` returns the bundle directory that was actually written, so a caller can find the timestamped run output. Containment uses the shared helper in [src/path_resolution.py](../../../src/path_resolution.py), the same one project execution output uses.

The operator client owns the run ID that a retry depends on. It creates one run ID per submission attempt and reuses that value for validation, ingestion, and any retry after a Binding Set confirmation. An attempt starts when the operator begins a submission or changes the submission name, project, timestamp, datatype, or identifier, and it ends when a bundle is written successfully or the operator starts a new submission. The value lives in the client's ingester store, so leaving the form and returning continues the same attempt instead of starting a new one. The server keeps its current behavior of minting a fallback ID when a caller supplies none, so API callers are unaffected.

Bundle creation may connect to the target database for read-only verification queries only. This covers the fixed `data_provider` row confirmation required by the provider-scope cutover ([PROJECT_DATA_PROVIDER_SCOPE](../done/PROJECT_DATA_PROVIDER_SCOPE/PROJECT_DATA_PROVIDER_SCOPE.md)) and any target-row collision checks the ingester runs. Bundle creation must not insert, update, or delete target rows, and must not call `nextval` or otherwise consume sequence values; reserving target IDs stays out of generation. The SEAD Release Cycle handles review and quality assurance after bundle creation.

## Risks And Tradeoffs

- More principals can create bundles, including bundles that may need correction during the SEAD Release Cycle. The set grows only inside projects where the principal already holds `project:execute`.
- A principal that holds `application:run_ingesters` but no `project:execute` grant on a saved project still cannot create a bundle from it. This change removes the ingester gate without widening project access.
- Managed output paths and the read-only target-database rule keep this operation's side effects limited to the intended files; read-only verification queries add a target-database dependency, so bundle creation fails when the provider-row confirmation cannot run.
- Run folders preserve earlier bundles but accumulate output; [#550](https://github.com/humlab-sead/sead_shape_shifter/issues/550) tracks a future review of this naming and retention choice.
- Ignoring `output_folder` for this ingester is a caller-visible behavior change. A caller that relied on choosing the destination must read `output_path` from the response instead, and the phase must document that in the ingester README.
- A client that loses its attempt state — a page reload, a different browser, or a cleared store — starts a new run ID, so the next submit is a new batch rather than a replay. The outcome is still the one `P-AC-5` describes: SIMS resolves the source identity again and the configured business `keys` return the existing target ID.

## Testing And Validation

- Confirm a principal holding `project:execute` on an authorized saved project but not `application:run_ingesters` can create a target bundle from that project with no caller-supplied source file. Confirm an unauthenticated caller and a principal without `project:execute` are both rejected.
- Confirm bundle creation from a caller-supplied `.xlsx`/`.xls` path still requires `application:run_ingesters`.
- Confirm each run writes to its own UTC-timestamped run folder under `INGEST_OUTPUT_DIR`, with the bundle name and SQL file names unchanged inside it.
- Confirm a destination collision fails before any file is written, that no existing directory is deleted or replaced, and that `output_path` names the written bundle directory.
- Confirm bundle creation does not overwrite or remove unrelated files.
- Confirm bundle creation runs only read-only verification queries against the target database: no target-table write and no sequence allocation (`nextval`) occurs.
- Confirm the client sends one run ID across validation, ingestion, and a retry after a Binding Set confirmation, and mints a new one when the submission identity changes or a bundle has been written.
- Confirm the run ID used for a run appears in the response and the bundle manifest, and that the pending-confirmation message names it.
- Confirm other ingester operations retain their existing authorization requirement.

## Acceptance Criteria

- `P-AC-1` A bundle created from an authorized saved project with no caller-supplied source path — the [in-memory handoff](../IN_MEMORY_INGESTER_HANDOFF/IN_MEMORY_INGESTER_HANDOFF.md) — requires an authenticated principal holding `project:execute` on that project and does not require `application:run_ingesters`. Unauthenticated callers, and principals without `project:execute` on the named project, are rejected. Bundle creation from a caller-supplied source path keeps its current `application:run_ingesters` requirement until source path containment is implemented.
- `P-AC-2` Each run writes to its own UTC-timestamped run folder under the `INGEST_OUTPUT_DIR` managed root, keeping the existing bundle name inside it. Directory creation is exclusive: an existing destination fails before any file is written, and no existing directory is deleted or replaced. Bundle creation cannot overwrite or remove unrelated files, and `output_path` returns the bundle directory that was written.
- `P-AC-3` Bundle creation limits target-database access to read-only verification queries. It does not insert, update, or delete target rows and does not consume sequence values.
- `P-AC-4` Authorization for other ingester operations is unchanged.
- `P-AC-5` Repeated bundle generation for the same stable SIMS source identity reuses its assigned target ID. For one submission attempt, the operator client reuses a single run ID across validation, ingestion, and retries, and mints a new run ID when the submission identity changes or a bundle has been written. That run ID appears in the response and in the bundle manifest.

## Planning Handoff

- Treat [IN_MEMORY_INGESTER_HANDOFF](../IN_MEMORY_INGESTER_HANDOFF/IN_MEMORY_INGESTER_HANDOFF.md) as a blocking dependency, not a parallel workstream. Its `P-AC-1` and `P-AC-8` must ship first. Until then the caller-path route is the only route, and it stays gated; do not remove `application:run_ingesters` from it to satisfy `P-AC-1` early.
- Keep each run's output in its own UTC-timestamped run folder under the `INGEST_OUTPUT_DIR` managed root, with the existing bundle name unchanged inside it; create the run folder exclusively and fail before writing if it exists. Keep the existing `project:execute` check on the saved project, ignore `output_folder` for this ingester, return the written bundle directory in `output_path`, and do not add source authorization or target-database selection for this operation.
- Leave downstream review and quality assurance to the SEAD Release Cycle.
- Reconsider timestamped folder naming and retention under [#550](https://github.com/humlab-sead/sead_shape_shifter/issues/550).
- Keep SIMS identity resolution idempotent by using the entity's configured business `keys` as source identity, and preserve the same run ID and payload when retrying an allocation batch. Preserve deployment-time sequence synchronization in generated SQL.
- Implement the operator retry key in the client: an optional `run_id` on `SubmissionContextInput`, the current attempt's value in the ingester store, and a pending-confirmation message that names the run ID. Do not derive the run ID from the run folder name, and do not mint it per request.
- Do not allocate database-sequence IDs during bundle generation. Non-SIMS-tracked entities that require such IDs must have them pre-resolved before generation or be rejected as unsupported. Bundle generation may run read-only verification queries against the target database but must not modify target data or call `nextval`.
- Phase 4 of the [Security Hardening Follow-up phase plan](../SECURITY_HARDENING_FOLLOWUP/SECURITY_HARDENING_FOLLOWUP_PHASE_PLAN.md) records the same target-database rule: read-only verification queries are allowed, target-row writes and sequence allocation are not. Keep the two documents aligned.

## Final Recommendation

Approve the narrow permission exception for Change Request target-bundle creation. Defer more granular security controls for this operation unless a later review identifies a need for them.
