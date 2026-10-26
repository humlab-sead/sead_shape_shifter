# Change Request Target Bundle Access — Phase Plan

## Summary

This plan sequences the [Change Request target-bundle access proposal](./CHANGE_REQUEST_TARGET_BUNDLE_ACCESS.md) from the completed [in-memory ingester handoff](../../done/IN_MEMORY_INGESTER_HANDOFF/IN_MEMORY_INGESTER_HANDOFF_PHASE_PLAN.md) to a project-only workflow that requires `project:execute` but not `application:run_ingesters`. Safe output and read-only target-database behavior must be validated before the permission changes.

## Problem

Project-only Change Request validation and ingestion already accept normalized tables from an authorized saved project. Both routes and direct helper calls still require the deployment-wide ingester action. The bundle writer can replace an earlier bundle, and preparation can reserve target IDs through a database sequence. Removing the action before those behaviors change would give more project executors access to those side effects.

## Scope

This plan covers exclusive managed bundle output, read-only target-database access during project-only validation and ingestion, stable SIMS identity and operator retry keys, and the final permission change on the two dedicated project-only routes and their helper.

It does not reopen Change Request file input, change the shared file routes or other ingesters, add a caller-selected source or output path, apply generated SQL, or move SEAD Release Cycle review into Shape Shifter.

## Current Position

- The completed handoff provides project-only validate and ingest routes, a guarded composition helper, table input, and a saved-project client path. The routes and helper still enforce `application:run_ingesters` in addition to `project:execute`.
- `INGEST_OUTPUT_DIR` already supplies the backend-owned output root. The Change Request writer currently removes an existing same-name bundle directory, and the project helper returns `output_path=None`.
- Project-only requests accept an optional `run_id`; the server can mint one when absent. The client does not yet retain one across validation, ingestion, and retry. The runtime uses the saved project's provider-schema SIMS scope and declared business keys, but its invalid-key fallback can produce a shared identity value.
- Provider-row confirmation and collision checks use the target connection for reads. The current preparation path can also call a target sequence allocator for non-SIMS entities.

## Phase Plan

### Phase 1: Make bundle output exclusive and traceable

**Goal**

Write complete Change Request bundles in unique managed run folders without replacing earlier output.

**Focus**

- Choose the effective run ID before ingestion, including the server fallback when the request omits it. Use its SHA-256 digest with a UTC timestamp in the run folder name; never use raw caller input as a path component.
- Reserve the run folder exclusively before SIMS identity or Binding Set calls. A collision stops that request before files or SIMS calls; later failures remove only incomplete output owned by that invocation.
- Keep the existing bundle name, manifest `cr_name`, SQL names, and generated `\copy` paths. Carry the written bundle directory through the ingester result to `output_path`.

**Depends On**

- The completed in-memory handoff and configured `INGEST_OUTPUT_DIR` root.

**Outputs**

- A project-only bundle path that does not replace existing output and returns its actual directory, while the interim application permission remains required.

**Acceptance Criteria**

- `PH1-AC-1` (from `P-AC-2`) A successful run writes under `<INGEST_OUTPUT_DIR>/<UTC timestamp>_<SHA-256 digest of run_id>/<bundle_name>`; the raw run ID cannot select a path, and the existing bundle contents and internal names remain unchanged.
- `PH1-AC-2` (from `P-AC-2`) A destination collision stops before any file or SIMS call for that request. Existing directories remain untouched, and a later failure can remove only the current invocation's incomplete output.
- `PH1-AC-3` (from `P-AC-2`, `P-AC-5`) The project-only ingest response reports the bundle directory actually written; the effective run ID remains in the response and manifest, including when the server minted it.

**Validation Milestones**

- `VM-1.1` Successful, repeated, and hostile-run-ID cases confirm the managed layout, unchanged bundle contract, and actual response path (covers `PH1-AC-1`, `PH1-AC-3`).
- `VM-1.2` Collision and later-failure cases confirm no pre-existing output is changed, no SIMS call occurs for a colliding request, and cleanup is limited to that request's incomplete output (covers `PH1-AC-2`).

**Task-Plan Handoff**

- Use `P-AC-2` and the output rules in the proposal's Planning Handoff. Keep `INGEST_OUTPUT_DIR` backend-owned and the strict project-only request unchanged. Preserve the interim application gate; this phase does not grant new access.
- Account for the current writer's replacement behavior and the helper's `output_path=None`. The task plan should verify where the effective run ID is chosen, how early reservation reaches the writer, and how the written path returns to the API.

**Readiness**

Ready for a task plan. No output-location or collision decision remains open.

### Phase 2: Remove target sequence allocation and stabilize retries

**Goal**

Make both project-only operations read-only with respect to the target database and keep SIMS identities stable across retries and later runs.

**Focus**

- Keep provider-row and target-row verification queries; reject unresolved non-SIMS database-sequence IDs rather than calling `nextval` during validation or ingestion. Preserve sequence synchronization in generated deployment SQL.
- Use the saved project's provider-schema SIMS scope and declared business `keys` for stable identity. Invalid tracked keys fail before SIMS work instead of falling back to a shared identity.
- Have the operator client retain one run ID per submission attempt for validation, ingestion, and Binding Set retry; reset it on submission-identity changes or after a successful bundle. Name the ID in pending-confirmation guidance.

**Depends On**

- Phase 1 output and effective-run-ID behavior, so retry checks use the same run identity and safe output path.

**Outputs**

- Read-only target-database behavior and a validated retry contract, still behind the interim application permission.

**Acceptance Criteria**

- `PH2-AC-1` (from `P-AC-3`) Project-only validation and ingestion perform only read-only target verification; neither writes target rows nor consumes sequence values, and unresolved database-sequence IDs fail before allocation.
- `PH2-AC-2` (from `P-AC-5`) Within the saved provider-schema scope, repeated runs with the same declared business keys reuse assigned SIMS target IDs; invalid tracked keys fail before identity resolution.
- `PH2-AC-3` (from `P-AC-5`) The client sends one run ID through validation, ingestion, and a retry for an attempt, then uses a new ID when the submission identity changes or a bundle succeeds. Pending-confirmation guidance names the effective ID.

**Validation Milestones**

- `VM-2.1` Project-only validation and ingestion allow required read queries but show no target write or `nextval`; unresolved sequence IDs fail, while generated deployment SQL retains sequence synchronization (covers `PH2-AC-1`).
- `VM-2.2` Same-key later runs, invalid-key input, and same-payload retries confirm scope-bound SIMS identity and one client run ID per attempt (covers `PH2-AC-2`, `PH2-AC-3`).

**Task-Plan Handoff**

- Use `P-AC-3` and `P-AC-5`. Keep the target connection backend-selected, the provider-scope pair bound to the authorized saved project, and the raw run ID as the SIMS retry key. Keep both project-only operations behind `application:run_ingesters` until Phase 3.
- The task plan should verify the current sequence-allocation path in shared preparation and the existing optional `run_id` on the project request. Do not add a new caller database or output option.

**Readiness**

Ready for a task plan after Phase 1 is accepted. No identity or database-access decision remains open.

### Phase 3: Cut over project-only access

**Goal**

Let authenticated project executors validate and create Change Request bundles without the deployment-wide ingester action.

**Focus**

- Remove `application:run_ingesters` from both dedicated project-only routes and the direct helper check only after Phases 1 and 2 pass. Keep the route's `project:execute` dependency and the helper's authorized-resource guard.
- Confirm the shared file routes retain their application action, Change Request file input remains rejected, and other ingesters keep their current authorization.
- Align operator and authorization documentation with the shipped project-only permission rule.

**Depends On**

- Accepted Phase 1 output safeguards and Phase 2 read-only target-database and retry results.

**Outputs**

- The proposal's narrow permission exception, with regression results for denied callers and unaffected routes.

**Acceptance Criteria**

- `PH3-AC-1` (from `P-AC-1`) A principal with `project:execute` on the named saved project can use both project-only routes and the direct helper without `application:run_ingesters`; unauthenticated callers and principals without that project action remain denied.
- `PH3-AC-2` (from `P-AC-1`, `P-AC-4`) Change Request file input remains rejected, while the shared file routes and other ingesters retain their application-action requirement.
- `PH3-AC-3` (from `P-AC-1`, `P-AC-2`, `P-AC-3`, `P-AC-5`) The newly authorized project executor can complete validation and bundle creation using the accepted output, database, SIMS, and retry behavior from Phases 1 and 2.

**Validation Milestones**

- `VM-3.1` Route and direct-helper authorization checks confirm project-executor access, denied unauthenticated or unauthorized calls, and unchanged shared-route behavior (covers `PH3-AC-1`, `PH3-AC-2`).
- `VM-3.2` A project-executor workflow without the application action validates and creates a bundle with safe output, read-only target access, and the same attempt run ID; operator documentation matches that result (covers `PH3-AC-3`).

**Task-Plan Handoff**

- Use `P-AC-1` and `P-AC-4`, plus the accepted Phase 1 and 2 results. Change the dedicated project-only routes and helper, never the shared file-route action dependency. Keep the strict no-source request and authorized-project guard.
- Treat a failure of either safeguard as a cutover block; retain the interim application gate until both are accepted. Keep SEAD Release Cycle review outside this workflow.

**Readiness**

Ready for a task plan after Phases 1 and 2 are accepted. The access rule is fixed; implementation is gated by their validation results.

## Cross-Phase Rules

- Keep `application:run_ingesters` on both project-only routes and the helper until safe output and read-only target access are validated. Keep the shared file-route gate throughout.
- Preserve `project:execute`, the authorized saved-project identity, trusted backend inputs, and retired Change Request file input in every phase.
- Keep raw run IDs in SIMS and run records, never in filesystem components. Keep existing bundle names and generated SQL paths unchanged.
- Treat unsupported sequence-ID cases as explicit failures; do not silently allocate target IDs during bundle generation or validation.

## Validation Strategy

Validate the output contract and collision behavior first (`VM-1.1`–`VM-1.2`), then target-database and SIMS behavior under the existing gate (`VM-2.1`–`VM-2.2`). Remove the application action only after those results pass. Finish with route, helper, client, and unaffected-ingester regression checks (`VM-3.1`–`VM-3.2`). Phase task plans select exact checks and commands.
