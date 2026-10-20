# Proposal: Allow Project Executors To Create Change Request Target Bundles

## Status

- Proposed change; the in-memory handoff is complete, but this permission change is not implemented
- Scope: project-only Change Request validation and target-bundle creation without a caller-supplied source file
- Goal: let an authenticated principal holding `project:execute` on a saved project validate and create its Change Request target bundle without `application:run_ingesters`, for downstream review by the SEAD Release Cycle
- Completed prerequisite: the [in-memory ingester handoff](../IN_MEMORY_INGESTER_HANDOFF/IN_MEMORY_INGESTER_HANDOFF_PHASE_PLAN.md) added the project-only routes, helper, table input, and saved-project client path. Both routes and direct helper calls still require `application:run_ingesters`.

## Summary

Allow an authenticated principal holding `project:execute` on a saved project to use its project-only Change Request validation and bundle-creation routes without `application:run_ingesters`. The completed [in-memory handoff](../IN_MEMORY_INGESTER_HANDOFF/IN_MEMORY_INGESTER_HANDOFF.md) supplies normalized tables without a caller source path. Keep the project authorization check, make bundle output exclusive within the managed root, and limit target-database access during both operations to read-only verification queries. The SEAD Release Cycle remains responsible for downstream quality assurance.

## Problem

The project-only Change Request routes already normalize an authorized saved project in memory and accept no source or output path. Both validation and bundle creation require `project:execute` on that project plus the deployment-wide `application:run_ingesters` action. They share preparation checks, and validation is part of the operator workflow. The second permission limits this project-bound file-generation workflow more than its effects warrant once output replacement and target sequence allocation are removed.

## Scope

- Allow an authenticated principal holding `project:execute` on a saved project to use the dedicated `sead_change_request/from-project/validate` and `sead_change_request/from-project/ingest` routes without `application:run_ingesters`.
- Keep the existing `project:execute` requirement on both routes and the direct helper's authorized-project check.
- Write the bundle only to an application-managed output location.
- Limit target-database access in this operation to read-only verification queries.
- Leave the shared file routes and other ingesters' authorization unchanged; Change Request file input remains retired.

## Non-Goals

- Changing the `application:run_ingesters` requirement for other ingester operations.
- Removing or relaxing the `project:execute` requirement for this operation, or making bundle creation available to principals without access to the saved project.
- Reopening Change Request workbook input. The shared file routes, service, and ingester reject it; [Ingester Authorization](../INGESTER_AUTHORIZATION_TASKS/INGESTER_AUTHORIZATION_TASKS.md) governs remaining path-based ingesters.
- Adding per-source authorization or a separate bundle-creation permission.
- Changing the completed in-memory normalization or table-input contracts from [IN_MEMORY_INGESTER_HANDOFF](../IN_MEMORY_INGESTER_HANDOFF/IN_MEMORY_INGESTER_HANDOFF.md).
- Moving the SEAD Release Cycle's review or quality-assurance responsibilities into Shape Shifter.
- Implementing granular Change Request ingester security, which can be reconsidered separately.

## Current Behavior

The dedicated `POST /api/v1/ingesters/sead_change_request/from-project/validate` and `/ingest` routes require both `project:execute` and `application:run_ingesters`. [ProjectIngesterService](../../../backend/app/services/project_ingester_service.py) checks the authorized project and the application action again for direct calls. It derives the target model and database connection from trusted project and backend settings and passes normalized tables to the table-capable ingester. `INGEST_OUTPUT_DIR` is already a backend setting and supplies the output root. The service currently returns `output_path=None`; the [bundle writer](../../../ingesters/sead_change_request/artifact_writer.py) removes an existing same-name bundle directory under that root before writing. The shared file routes still require `application:run_ingesters` and reject `sead_change_request` file input. See the [routes](../../../backend/app/api/v1/endpoints/ingesters.py), [request models](../../../backend/app/models/ingester.py), and [settings](../../../backend/app/core/config.py).

## Proposed Design

Remove `application:run_ingesters` from both dedicated project-only routes and the direct helper check, after the output and database rules below apply. Keep their `project:execute` checks and strict project request model. Keep the shared file routes gated and Change Request file input rejected. Validation and ingestion use the same preparation path, so both must meet the read-only target-database rule before the permission changes.

Write each generated bundle under the existing backend-owned `INGEST_OUTPUT_DIR` setting. Relative values resolve against `APPLICATION_ROOT`; an absolute value is an explicit deployment setting. Each run writes to its own UTC-timestamped run folder below that root, with the existing bundle name kept inside it:

```text
<INGEST_OUTPUT_DIR>/<YYYYMMDDTHHMMSSZ>_<run_id_digest>/<bundle_name>/deploy/<bundle_name>.sql
```

The bundle name keeps its current form (`<date>_DML_<datatype>_<identifier>`), so the manifest `cr_name`, the SQL file names, and the paths used by generated `\copy` statements stay the same. Only the enclosing run folder is new, which is why this layout does not change the artifact contract the SEAD Release Cycle consumes.

The run folder name combines the UTC start time with the SHA-256 digest of the effective `run_id`. Project requests accept a caller-supplied run ID without a filename constraint, so its raw value must never become a path component. Choose the effective ID before ingestion and reserve the run folder exclusively before SIMS identity or Binding Set calls. A destination collision then fails before any file or SIMS call for that request. The writer may write only inside the newly reserved folder; on a later failure, it removes only incomplete output created by that invocation. It never deletes or replaces an existing run or bundle.

The project-only request has no `output_folder` field, and the retired Change Request file route cannot supply one to the ingester. Carry the path returned by the bundle writer through `IngestionResult` so `IngestResponse.output_path` names the bundle directory actually written. Resolve generated relative paths within the configured root using [src/path_resolution.py](../../../src/path_resolution.py); never use a caller-controlled destination.

The operator client owns the run ID that a retry depends on. It creates one run ID per submission attempt and reuses that value for validation, ingestion, and any retry after a Binding Set confirmation. An attempt starts when the operator begins a submission or changes the submission name, project, timestamp, datatype, or identifier, and it ends when a bundle is written successfully or the operator starts a new submission. The value lives in the client's ingester store, so leaving the form and returning continues the same attempt instead of starting a new one. The server keeps its current behavior of minting a fallback ID when a caller supplies none, so API callers are unaffected.

Project-only validation and bundle creation may connect to the target database for read-only verification queries only. This covers fixed `data_provider` row confirmation required by the provider-scope cutover ([PROJECT_DATA_PROVIDER_SCOPE](../done/PROJECT_DATA_PROVIDER_SCOPE/PROJECT_DATA_PROVIDER_SCOPE.md)) and target-row collision checks. Neither operation may insert, update, or delete target rows, call `nextval`, or otherwise consume sequence values. Non-SIMS entities requiring database-sequence IDs must have those IDs pre-resolved or fail as unsupported. The SEAD Release Cycle handles review and quality assurance after bundle creation.

## Risks And Tradeoffs

- More principals can create bundles, including bundles that may need correction during the SEAD Release Cycle. The set grows only inside projects where the principal already holds `project:execute`.
- A principal that holds `application:run_ingesters` but no `project:execute` grant on a saved project still cannot create a bundle from it. This change removes the ingester gate without widening project access.
- Managed output paths and the read-only target-database rule limit local and target-database effects. Validation and ingestion still use SIMS identity and Binding Set operations; the permission change does not make them side-effect free. A collision must fail before those calls, but other failures after preparation may leave SIMS state for a retry. Both operations fail when required provider-row confirmation cannot run.
- Run folders preserve earlier bundles but accumulate output; [#550](https://github.com/humlab-sead/sead_shape_shifter/issues/550) tracks a future review of this naming and retention choice.
- The project-only request already excludes `output_folder`; existing callers must read the actual bundle directory from `output_path` once this change ships.
- A client that loses its attempt state — a page reload, a different browser, or a cleared store — starts a new run ID, so the next submit is a new batch rather than a replay. Within the same provider-schema SIMS scope, configured business `keys` should resolve to the existing target ID. The [provider-scope decision](../done/PROJECT_DATA_PROVIDER_SCOPE/PROJECT_DATA_PROVIDER_SCOPE.md) records residual duplicate risk across different scopes.

## Testing And Validation

- Confirm a principal holding `project:execute` on an authorized saved project but not `application:run_ingesters` can validate and create a target bundle through the project-only routes, including a direct helper call. Confirm unauthenticated callers and principals without `project:execute` are rejected.
- Confirm Change Request file input remains rejected at the shared routes, service, and ingester, and other ingesters' file routes still require `application:run_ingesters`.
- Confirm each run writes to its own UTC-timestamped folder with the SHA-256 run ID digest under `INGEST_OUTPUT_DIR`, with the bundle name and SQL file names unchanged inside it. A caller-supplied run ID containing path characters cannot choose another output location.
- Confirm a destination collision fails before any file or SIMS call for that request, no existing directory is deleted or replaced, incomplete output from a later failure is removed only from the invocation's own folder, and `output_path` names the written bundle directory.
- Confirm bundle creation does not overwrite or remove unrelated files.
- Confirm both project-only validation and bundle creation run only read-only verification queries against the target database: no target-table write and no sequence allocation (`nextval`) occurs.
- Confirm the client sends one run ID across validation, ingestion, and a retry after a Binding Set confirmation, and mints a new one when the submission identity changes or a bundle has been written.
- Confirm the run ID used for a run appears in the response and the bundle manifest, and that the pending-confirmation message names it.
- Confirm other ingester operations retain their existing authorization requirement.

## Acceptance Criteria

- `P-AC-1` The dedicated project-only Change Request validation and ingestion routes accept an authenticated principal holding `project:execute` on the named saved project without `application:run_ingesters`; direct helper calls enforce the same project authorization. Unauthenticated callers and principals without that project action are rejected. Change Request file input remains rejected.
- `P-AC-2` Each run writes to its own `<UTC timestamp>_<SHA-256 digest of run_id>` folder under the `INGEST_OUTPUT_DIR` managed root, keeping the existing bundle name inside it. The raw run ID cannot control an output path. A destination collision fails before any file or SIMS call for that request. No existing directory is deleted or replaced; a later failure may remove only output created by that invocation. `output_path` returns the bundle directory that was written.
- `P-AC-3` Project-only validation and bundle creation limit target-database access to read-only verification queries. Neither operation inserts, updates, or deletes target rows or consumes sequence values. Inputs requiring unresolved database-sequence IDs fail before allocation.
- `P-AC-4` Authorization for other ingester operations is unchanged.
- `P-AC-5` Within one provider-schema SIMS scope (`provider://<provider-code>/<provider-schema>` from the saved project's bound pair), repeated bundle generation for the same declared business `keys` reuses the assigned target ID. For one submission attempt, the operator client reuses a single run ID across validation, ingestion, and retries, and mints a new one when the submission identity changes or a bundle has been written. The effective run ID appears in the response and bundle manifest.

## Planning Handoff

- The [in-memory handoff phase plan](../IN_MEMORY_INGESTER_HANDOFF/IN_MEMORY_INGESTER_HANDOFF_PHASE_PLAN.md) records Phases 1–5 complete. Change only its dedicated project-only routes and helper when removing `application:run_ingesters`; keep the `project:execute` checks, strict no-source request, and retired Change Request file input.
- Keep each run's output in its own `<UTC timestamp>_<SHA-256 digest of run_id>` folder under the configured `INGEST_OUTPUT_DIR` root, with the existing bundle name unchanged inside it. The raw run ID remains in SIMS, the response, and the manifest, never in a filesystem component. Choose the effective run ID and reserve the destination before SIMS calls; fail on collision without a SIMS call for that request. Clean only incomplete output owned by the current invocation. Carry the written bundle path from the writer through the ingester result into `output_path`. Do not add caller source, output, or target-database selection to the project-only request.
- Leave downstream review and quality assurance to the SEAD Release Cycle.
- Reconsider timestamped folder naming and retention under [#550](https://github.com/humlab-sead/sead_shape_shifter/issues/550).
- Keep SIMS identity resolution idempotent within the saved project's provider-schema scope by using each entity's configured business `keys` as source identity. Preserve the same run ID and payload when retrying an allocation batch, and fail on invalid tracked business keys rather than using a shared fallback identity. Preserve deployment-time sequence synchronization in generated SQL.
- Implement the operator retry key in the client: use the existing optional `run_id` in `ProjectSubmissionOptions`, hold the current attempt's value in the ingester store, and name the run ID in a pending-confirmation message. Do not derive the run ID from the output folder name or mint it per request.
- Do not allocate database-sequence IDs during project-only validation or bundle generation. Non-SIMS-tracked entities that require such IDs must have them pre-resolved or be rejected as unsupported. Both operations may run read-only verification queries against the target database but must not modify target data or call `nextval`.
- Phase 4 of the [Security Hardening Follow-up phase plan](../SECURITY_HARDENING_FOLLOWUP/SECURITY_HARDENING_FOLLOWUP_PHASE_PLAN.md) records the same target-database rule: read-only verification queries are allowed, target-row writes and sequence allocation are not. Keep the two documents aligned.

## Final Recommendation

Approve the narrow permission exception for the project-only Change Request validation and target-bundle workflow, after its managed-output and read-only database rules are in force. Defer more granular security controls unless a later review identifies a need for them.
