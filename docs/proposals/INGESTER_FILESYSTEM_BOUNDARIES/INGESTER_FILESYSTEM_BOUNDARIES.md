# Proposal: Secure Ingester Filesystem And Destination Access

## Status

- Proposed change
- Scope: source files, project references, output and temporary paths, and database destinations used by ingester operations
- Goal: prevent an authorized ingester caller from selecting unrelated server files or destinations

## Summary

The centralized authorization cutover added an `application:run_ingesters` requirement to validation and ingestion routes. That role gate does not authorize the specific source, project, output, or database selected for a run. The general filesystem-hardening work explicitly deferred these ingester checks, and the security-hardening follow-up carries them as planned work.

Define approved resource references and enforce their authorization and containment in every execution path. Keep an operation unavailable until its required checks are in place.

## Problem

The validation and ingestion request models accept a source path. Ingestion also accepts an output folder, and the configuration can carry database connection details. The service passes the source to the registered ingester and builds its configuration without a common source, output, or database-destination check. An operator authorized to run ingesters can therefore reach inputs and destinations that the role gate alone does not constrain. Direct service or background calls must not bypass these checks.

The earlier security review demonstrated a connection to a requester-selected scratch database when its test harness initialized the ingester configuration store. That test did not establish normal runtime availability; the report separately recorded an initialization failure. It could not verify file-read or database-write effects without a SEAD clearing-house database. These results show the need for maintained tests, not proof that every ingester path is currently exploitable. See [SECURITY_CHECK.md](../done/MITIGATE_SECURITY_ISSUES/SECURITY_CHECK.md#L73) and the current [authorization route inventory](../../AUTHORIZATION_ROUTE_INVENTORY.md).

## Scope

- Define approved source, project, output, temporary, and database resources for each supported ingester operation.
- Authorize the referenced project, source, and destination as applicable before use.
- Confine file reads, writes, and cleanup to server-approved roots.
- Restrict database access to named, server-managed destinations.
- Apply the same checks to HTTP, service, and background entry points.
- Keep operations unavailable when any required check is missing.

## Non-Goals

- Replacing or weakening the existing `application:run_ingesters` action.
- Redesigning the centralized authorization policy or ingester transformation behavior.
- Repeating general filesystem and SQL hardening already covered by the security-hardening work.

## Current Behavior

Both validation and ingestion routes declare `require_application_action(Action.RUN_INGESTERS)`. The request models still represent sources and output folders as strings, and the service passes the source directly to the ingester. The route-level action check does not establish resource-specific authorization or path containment. See the [route](../../../backend/app/api/v1/endpoints/ingesters.py), [request models](../../../backend/app/models/ingester.py), and [service](../../../backend/app/services/ingester_service.py).

The completed filesystem-hardening plan marks ingester source and destination boundaries as deferred. The centralized authorization cutover likewise classified the routes and recorded enforcement follow-up; it did not implement source, project, database, or destination authorization. The separate follow-up plan includes ingester path and database constraints in its Phase 4 acceptance criteria: [Phase 2 record](../done/MITIGATE_SECURITY_ISSUES/done/MITIGATE_SECURITY_ISSUES_PHASE_2_TASK_PLAN.md#L128), [authorization cutover task plan](../done/CENTRALIZED_AUTHORIZATION_CUTOVER/done/CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PHASE_1_TASK_PLAN.md#L55), and [security-hardening follow-up](../SECURITY_HARDENING_FOLLOWUP/SECURITY_HARDENING_FOLLOWUP_PHASE_PLAN.md#L212).

## Proposed Design

### Use approved resource references

Do not treat a client-supplied filesystem path or database connection as authorization. Prefer uploaded content or an opaque reference to a server-managed source. Resolve each reference to an approved resource and authorize it for the operation before access. Use named, server-managed database destinations instead of request-supplied hosts, ports, database names, or credentials.

### Confine file access

Assign each enabled operation an approved source root and server-generated output and temporary roots. Resolve paths beneath the assigned root, reject traversal and symlink escapes, and prevent a path from being redirected between validation and use. Restrict cleanup to files created for that operation. Do not accept caller-selected output paths unless they are converted to a validated resource beneath the assigned root.

### Enforce checks at execution

Keep `application:run_ingesters` as the application-level gate. In addition, authorize each project, source, and destination used by an operation. Enforce these checks in the service or operation layer so direct calls and background execution receive the same protection as HTTP requests. Pass validated resource objects or handles to the ingester rather than unvalidated request strings.

If an operation cannot meet its required authorization, path, and destination checks, deny it through both the API and direct application entry points until it can.

## Risks And Tradeoffs

- Replacing raw paths and connection settings with uploads or server-managed references changes the request contract and may require updates to operator workflows and clients.
- Restricting output roots may require migration of existing scripts that expect caller-selected directories.
- Keeping incomplete operations unavailable delays ingester use, but avoids treating the application role as permission to access arbitrary resources.

## Testing And Validation

- Test unauthenticated, unauthorized, and authorized calls for each enabled operation; verify the action gate and resource checks independently.
- Test traversal, absolute paths, symlink escapes, and attempted path replacement for every source, output, and temporary file operation.
- Test that output and cleanup cannot affect files outside the assigned operation root.
- Test that callers cannot select unapproved database destinations or another project's resources.
- Exercise checks through routes, direct service calls, and any background entry points. Assert filesystem and database effects, not only response codes.
- Confirm incomplete operations fail before opening files or connecting to destinations.

## Acceptance Criteria

- `P-AC-1` Each enabled ingester operation documents its source, project, output, temporary, and database resources, with the applicable authorization requirement and approved destination.
- `P-AC-2` No enabled operation reads or writes outside its assigned filesystem roots, including through traversal, absolute paths, symlinks, or path replacement.
- `P-AC-3` Each operation can access only an authorized project and source and a server-managed, approved database destination.
- `P-AC-4` HTTP, direct service, and background entry points enforce the same checks; an operation missing any required check is denied before side effects.
- `P-AC-5` Maintained regression tests verify allowed and denied access, path escape attempts, destination restrictions, and absence of unauthorized filesystem or database effects.

## Planning Handoff

- Preserve the existing `application:run_ingesters` gate; it supplements rather than replaces resource authorization.
- Keep incomplete operations unavailable until their source, project, output, temporary, and database checks are implemented and tested.
- Use the security-hardening follow-up's Phase 4 criterion `PH4-AC-3` as the linked security requirement; a task plan should map this proposal's acceptance criteria to operation-level work and validation.
- Decide during planning whether each source is supplied as uploaded content or a server-managed reference, and define approved roots and database destinations per deployment.
- Validation must prove that denied requests cause no file or database side effects and that existing authorized workflows still work with approved references.

## Final Recommendation

Implement resource authorization, path containment, and server-managed database selection for each enabled ingester operation. Keep any operation that lacks those checks unavailable, regardless of the caller's `run_ingesters` role.