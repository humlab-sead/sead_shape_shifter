# Proposal: Allow Authorized Operators To Create Change Request Target Bundles

## Status

- Proposed change; implementation is blocked on its dependency
- Scope: Change Request target-bundle creation without a caller-supplied source file
- Goal: let an authenticated principal that holds `project:execute` on an authorized saved project create a target bundle from that project, with no caller-supplied source path, for downstream review by the SEAD Release Cycle
- Blocking dependency: [IN_MEMORY_INGESTER_HANDOFF](../IN_MEMORY_INGESTER_HANDOFF/IN_MEMORY_INGESTER_HANDOFF.md) is still proposed and not implemented. It retires the unused Change Request file input immediately and later supplies the project-only path with mandatory project validation. This permission change starts only after that path exists.

## Summary

Allow an authenticated principal that holds `project:execute` on an authorized saved project to validate and create a Change Request target bundle from that project, with no caller-supplied source file, without the `application:run_ingesters` permission. Remove that permission only from the dedicated project-only routes and their composition helper defined in [IN_MEMORY_INGESTER_HANDOFF](../IN_MEMORY_INGESTER_HANDOFF/IN_MEMORY_INGESTER_HANDOFF.md); keep the routes' `project:execute` requirement and the helper's project-resource guard. The unused Change Request file input is retired separately and immediately. Shape Shifter writes the bundle to a managed output location. Bundle creation may run read-only verification queries against the target database but must not modify target data or consume sequence values. The SEAD Release Cycle remains responsible for downstream quality assurance.

## Problem

Change Request target-bundle creation produces files for a later release process; it does not update a target database. The operation that needs the relaxed permission also reads no caller-supplied source path: its tables come from normalization of an authorized saved project ([IN_MEMORY_INGESTER_HANDOFF](../IN_MEMORY_INGESTER_HANDOFF/IN_MEMORY_INGESTER_HANDOFF.md)). That proposal adds dedicated project-only validation and ingestion routes, initially gated by both `project:execute` and `application:run_ingesters`. The application permission is a second, deployment-wide gate that limits this project operation more than its effect warrants.

## Scope

- Allow an authenticated principal that holds `project:execute` on an authorized saved project to create a Change Request target bundle from that project, with no caller-supplied source path, without `application:run_ingesters`.
- Keep `project:execute` on both project-only routes and retain the helper's project-resource guard; remove `application:run_ingesters` only from those routes and helper.
- Write the bundle only to an application-managed output location.
- Limit target-database access in this operation to read-only verification queries.
- Leave authorization for other ingester operations unchanged. The handoff retires Change Request bundle creation from a caller-supplied file.

## Non-Goals

- Changing the `application:run_ingesters` requirement for other ingester operations.
- Removing or relaxing the `project:execute` requirement for this operation, or making bundle creation available to principals without access to the saved project.
- Reintroducing Change Request bundle creation from a caller-supplied source path after its retirement in the handoff.
- Adding per-source authorization or a separate bundle-creation permission.
- Implementing the composed in-memory normalization path itself. That work belongs to [IN_MEMORY_INGESTER_HANDOFF](../IN_MEMORY_INGESTER_HANDOFF/IN_MEMORY_INGESTER_HANDOFF.md), and this proposal depends on it.
- Moving the SEAD Release Cycle's review or quality-assurance responsibilities into Shape Shifter.
- Implementing granular Change Request ingester security, which can be reconsidered separately.

## Current Behavior

The ingestion route requires `application:run_ingesters`. For the `sead_change_request` key it also requires `project:execute` on the saved project named in the request body, and answers 404 when the principal has no grant on that project. Its request also carries source and output paths. The ingester permission does not distinguish Change Request target-bundle creation from operations with different effects. See the [ingester route](../../../backend/app/api/v1/endpoints/ingesters.py), [request models](../../../backend/app/models/ingester.py), [authorization dependencies](../../../backend/app/authorization/dependencies.py), and [ingester service](../../../backend/app/services/ingester_service.py).

## Proposed Design

Remove `application:run_ingesters` from the dedicated `POST /api/v1/ingesters/sead_change_request/from-project/validate` and `/from-project/ingest` routes and their internal composition helper, as defined by the in-memory handoff. Keep authentication and `project:execute` on both routes, and keep the helper's `AuthorizedResource` guard. The validate route prepares the same saved-project submission that the ingest route turns into a bundle. Both requests exclude a caller source path and arbitrary config. The handoff's `P-AC-11` selects the target model, target connection, project context, and output root without caller overrides. The shared `/{key}/validate` and `/{key}/ingest` routes continue to require `application:run_ingesters` for other ingesters and reject `sead_change_request` file requests regardless of role. Enable the project-only permission exception only when the exclusive managed-output and read-only target-database rules below are in force.

Write each generated bundle under the application-managed `INGEST_OUTPUT_DIR` root introduced by the in-memory handoff. The setting resolves under `APPLICATION_ROOT` the same way the existing project, log, and shared-data directories do. This proposal adds an exclusive UTC-timestamped run folder below that root, with the existing bundle name kept inside it:

```text
<INGEST_OUTPUT_DIR>/<YYYYMMDDTHHMMSSZ>/<bundle_name>/deploy/<bundle_name>.sql
```

The bundle name keeps its current form (`<date>_DML_<datatype>_<identifier>`), so the manifest `cr_name`, the SQL file names, and the paths used by generated `\copy` statements stay the same. Only the enclosing run folder is new, which is why this layout does not change the artifact contract the SEAD Release Cycle consumes.

The run folder name combines the UTC start time with the effective `run_id`, and directory creation is exclusive, so two runs of the same submission on the same day cannot collide. If the destination already exists, bundle creation fails before writing any file and never deletes or replaces an existing directory.

`IngestRequest.output_folder` stays in the shared file request model for other ingesters; the Change Request project-only request has no output path field. The managed root decides the location. `IngestResponse.output_path` returns the bundle directory that was actually written, so a caller can find the timestamped run output. Containment uses the shared helper in [src/path_resolution.py](../../../src/path_resolution.py), the same one project execution output uses.

The operator client owns the run ID that a retry depends on. It creates one run ID per submission attempt and reuses that value for validation, ingestion, and any retry after a Binding Set confirmation. An attempt starts when the operator begins a submission or changes the submission name, project, timestamp, datatype, or identifier, and it ends when a bundle is written successfully or the operator starts a new submission. The value lives in the client's ingester store, so leaving the form and returning continues the same attempt instead of starting a new one. The server keeps its current behavior of minting a fallback ID when a caller supplies none, so API callers are unaffected.

Bundle creation may connect to the target database for read-only verification queries only. This covers the fixed `data_provider` row confirmation required by the provider-scope cutover ([PROJECT_DATA_PROVIDER_SCOPE](../done/PROJECT_DATA_PROVIDER_SCOPE/PROJECT_DATA_PROVIDER_SCOPE.md)) and any target-row collision checks the ingester runs. Bundle creation must not insert, update, or delete target rows, and must not call `nextval` or otherwise consume sequence values; reserving target IDs stays out of generation. The SEAD Release Cycle handles review and quality assurance after bundle creation.

## Risks And Tradeoffs

- More principals can create bundles, including bundles that may need correction during the SEAD Release Cycle. The set grows only inside projects where the principal already holds `project:execute`.
- A principal that holds `application:run_ingesters` but no `project:execute` grant on a saved project still cannot create a bundle from it. This change removes the ingester gate without widening project access.
- Managed output paths and the read-only target-database rule keep this operation's side effects limited to the intended files; read-only verification queries add a target-database dependency, so bundle creation fails when the provider-row confirmation cannot run.
- Run folders preserve earlier bundles but accumulate output; [#550](https://github.com/humlab-sead/sead_shape_shifter/issues/550) tracks a future review of this naming and retention choice.
- Project-only callers read the written destination from `output_path`; the retired Change Request file request no longer offers a caller-selected `output_folder`.
- A client that loses its attempt state — a page reload, a different browser, or a cleared store — starts a new run ID, so the next submit is a new batch rather than a replay. The outcome is still the one `P-AC-5` describes: SIMS resolves the source identity again and the configured business `keys` return the existing target ID.

## Testing And Validation

- Confirm a principal holding `project:execute` on an authorized saved project but not `application:run_ingesters` can validate and create a target bundle through the project-only routes without a caller-supplied source file. Confirm an unauthenticated caller and a principal without `project:execute` are both rejected.
- Confirm Change Request bundle creation from a caller-supplied `.xlsx`/`.xls` path is unavailable through routes, services, and direct ingester calls regardless of role. Other ingesters retain their existing permission checks.
- Confirm each run writes to its own UTC-timestamped run folder under `INGEST_OUTPUT_DIR`, with the bundle name and SQL file names unchanged inside it.
- Confirm a destination collision fails before any file is written, that no existing directory is deleted or replaced, and that `output_path` names the written bundle directory.
- Confirm bundle creation does not overwrite or remove unrelated files.
- Confirm bundle creation runs only read-only verification queries against the target database: no target-table write and no sequence allocation (`nextval`) occurs.
- Confirm the client sends one run ID across validation, ingestion, and a retry after a Binding Set confirmation, and mints a new one when the submission identity changes or a bundle has been written.
- Confirm the run ID used for a run appears in the response and the bundle manifest, and that the pending-confirmation message names it.
- Confirm other ingester operations retain their existing authorization requirement.

## Acceptance Criteria

- `P-AC-1` The project-only validation and ingest routes from the [in-memory handoff](../IN_MEMORY_INGESTER_HANDOFF/IN_MEMORY_INGESTER_HANDOFF.md) accept no caller-supplied source path, require an authenticated principal holding `project:execute` on the named saved project, and do not require `application:run_ingesters`. The internal composition helper also stops requiring that application action but retains its project-resource guard. Unauthenticated callers and principals without that project permission are rejected. The retired `sead_change_request` file input stays unavailable; other file routes retain their application permission requirement.
- `P-AC-2` Each run writes to its own UTC-timestamped run folder under the `INGEST_OUTPUT_DIR` managed root, keeping the existing bundle name inside it. Directory creation is exclusive: an existing destination fails before any file is written, and no existing directory is deleted or replaced. Bundle creation cannot overwrite or remove unrelated files, and `output_path` returns the bundle directory that was written.
- `P-AC-3` Bundle creation limits target-database access to read-only verification queries. It does not insert, update, or delete target rows and does not consume sequence values.
- `P-AC-4` Authorization for other ingester operations is unchanged.
- `P-AC-5` Repeated bundle generation for the same stable SIMS source identity reuses its assigned target ID. For one submission attempt, the operator client reuses a single run ID across validation, ingestion, and retries, and mints a new run ID when the submission identity changes or a bundle has been written. That run ID appears in the response and in the bundle manifest.

## Planning Handoff

- Treat [IN_MEMORY_INGESTER_HANDOFF](../IN_MEMORY_INGESTER_HANDOFF/IN_MEMORY_INGESTER_HANDOFF.md) as a blocking dependency. Its `P-AC-6` retires Change Request file input immediately; its `P-AC-1`, `P-AC-8`, `P-AC-10`, `P-AC-11`, `P-AC-12`, and `P-AC-13` must then supply dedicated project-only routes, client requests, trusted inputs, the helper's service authorization guard behind both permissions, and mandatory project validation before ingester work. Reuse its `INGEST_OUTPUT_DIR` root. Remove `application:run_ingesters` only from the project-only routes and helper when this proposal's exclusive output and read-only database rules ship. Keep the helper's project-resource guard and other file-route gates.
- Keep each run's output in its own UTC-timestamped run folder under the `INGEST_OUTPUT_DIR` managed root, with the existing bundle name unchanged inside it; create the run folder exclusively and fail before writing if it exists. Keep the existing `project:execute` check on the saved project, ignore `output_folder` for this ingester, return the written bundle directory in `output_path`, and do not add source authorization or target-database selection for this operation.
- Leave downstream review and quality assurance to the SEAD Release Cycle.
- Reconsider timestamped folder naming and retention under [#550](https://github.com/humlab-sead/sead_shape_shifter/issues/550).
- Keep SIMS identity resolution idempotent by using the entity's configured business `keys` as source identity, and preserve the same run ID and payload when retrying an allocation batch. Preserve deployment-time sequence synchronization in generated SQL.
- Implement the operator retry key in the client: an optional `run_id` on `SubmissionContextInput`, the current attempt's value in the ingester store, and a pending-confirmation message that names the run ID. Preserve the handoff's project-only client requests without `source` and send the run ID through them; keep file-only ingesters on the existing routes. Do not derive the run ID from the run folder name, and do not mint it per request.
- Do not allocate database-sequence IDs during bundle generation. Non-SIMS-tracked entities that require such IDs must have them pre-resolved before generation or be rejected as unsupported. Bundle generation may run read-only verification queries against the target database but must not modify target data or call `nextval`.
- Phase 4 of the [Security Hardening Follow-up phase plan](../SECURITY_HARDENING_FOLLOWUP/SECURITY_HARDENING_FOLLOWUP_PHASE_PLAN.md) records the same target-database rule: read-only verification queries are allowed, target-row writes and sequence allocation are not. Keep the two documents aligned.

## Final Recommendation

Approve the narrow permission exception for Change Request target-bundle creation. Defer more granular security controls for this operation unless a later review identifies a need for them.
