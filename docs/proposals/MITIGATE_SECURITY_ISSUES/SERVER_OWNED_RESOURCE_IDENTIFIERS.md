# Server-Owned Resource Identifiers

## Status

- Proposed follow-up to the implemented centralized authorization system
- Parent proposal: [MITIGATE_SECURITY_ISSUES.md](./MITIGATE_SECURITY_ISSUES.md)
- Parent phase task plan: [MITIGATE_SECURITY_ISSUES_PHASE_TASK_PLAN.md](./MITIGATE_SECURITY_ISSUES_PHASE_TASK_PLAN.md)
- Completed authorization design: [CENTRALIZED_AUTHORIZATION_SYSTEM.md](./done/CENTRALIZED_AUTHORIZATION_SYSTEM.md)
- Related implementation plan: [CENTRALIZED_AUTHORIZATION_SYSTEM_TASK_PLAN.md](./done/CENTRALIZED_AUTHORIZATION_SYSTEM_TASK_PLAN.md)
- Related deployment plan: [CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md](./CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md)

## Summary

Replace client-selected filesystem names and paths with server-owned resource records for generated outputs, backups, uploads, and long-running operations. Authorization must resolve the requested resource through its stable server record before endpoint or service code obtains the internal locator.

The existing authorization system provides generation-specific UUIDs, parent relationships, lifecycle states, centralized checks, and project inheritance. This proposal applies those contracts consistently to file and operation resources that currently use constrained filenames, relative paths, or in-memory operation identifiers.

## Problem

The current implementation contains several paths inside approved directories, but containment alone does not establish resource identity. A client can still address an output, backup, or upload by a filename or relative path. Filename reuse, stale references, and cross-project references therefore remain separate concerns from path traversal.

Long-running operations use UUIDs and record their owner and parent project, but the records are currently held in memory. Operation results also need an explicit relationship to server-owned output records so later result access cannot depend on a client-supplied path.

## Scope

- Stable resource records for generated file and folder outputs.
- Stable resource records for project backups.
- Stable resource records for project and shared-data uploads.
- Resource-backed references for long-running operations and their results.
- Parent-resource authorization, lifecycle transitions, stale-reference handling, and filename-reuse protection.
- API response and request changes that keep physical paths internal.
- Focused service, API, lifecycle, and cross-resource tests.

## Non-Goals

- Changing the centralized role and action policy.
- Replacing nginx authentication or adding native application login.
- Removing path containment, symlink checks, SQL restrictions, or destination allowlists. These remain required controls after resource authorization.
- Redesigning unrelated ingester source and destination handling except where it consumes upload or output references.
- Supporting multi-host operation storage while the authorization system remains SQLite-based.

## Current Behavior

- Execution accepts a target string and resolves file and folder targets beneath a project output directory. Downloads accept a relative target and repeat that path resolution.
- Backup listing returns a filename and restore accepts a backup filename scoped to the authorized project directory.
- Upload listing and upload responses expose names and paths. File metadata and data-source configuration accept filenames or relative paths.
- Long-running operation records contain an operation UUID, initiating principal, and stable project resource ID, but the manager stores them in process memory.
- Existing tests cover authorization, containment, project isolation, and operation ownership, but do not establish stable resource identity for all four categories.

## Proposed Design

### Resource types and records

Use generation-specific resource records with stable UUIDs, current internal locators, lifecycle state, and parent resource IDs.

- Outputs are project-child resources. A file or folder output record stores its project parent and internal output locator.
- Backups are project-child resources. A backup record stores its project parent and internal backup locator.
- Project uploads are project-child resources. Shared uploads are shared-data-source-child resources or another explicitly approved shared parent resource type.
- Operations are server-owned records containing the initiating principal, parent protected resource, operation type, timestamps, lifecycle state, and result resource references.

Physical paths remain internal locators. They must never be used as authorization identities or returned as the resource reference used by a later request.

### API contract

- Create and list endpoints return opaque resource IDs and metadata needed by the client, not physical paths as identifiers.
- Restore, download, metadata, preview, and other later-use endpoints accept the server-issued resource ID.
- Dependencies resolve the record by UUID, verify its lifecycle state and parent, and return an authorized resource to endpoint and service code.
- A resource ID from another project, a deleted resource ID, or a stale ID after filename reuse returns concealed `404`.
- Execution creates or resolves an output record before returning its reference. Operation results contain output resource references rather than arbitrary target paths.
- Existing filename or relative-path inputs require an explicit migration or compatibility boundary; they must not bypass resource resolution.

### Lifecycle and consistency

- Register a resource before exposing it to the client.
- Mark a resource unavailable before deleting or replacing its backing file.
- Use compensation and reconciliation when filesystem and authorization-database changes cannot be atomic.
- Ensure duplicate filenames receive distinct resource IDs and cannot inherit grants from deleted generations.
- Clean up operation records only after authorized result access is no longer possible, or persist the record until its retention policy expires.
- Keep path containment and symlink checks immediately before filesystem access.

### Operations

Persist operation records if progress, stream, cancellation, or result access must survive process restart. If process durability is explicitly out of scope, document the limitation and still ensure every in-process operation reference resolves through one server-owned record.

Every later operation request must authorize:

1. the operation record and initiating principal;
2. the current parent project or protected resource;
3. the referenced output or other result resource, when present.

Revocation must block new work and later progress, stream, cancellation, and result access according to the established authorization policy.

## Alternatives Considered

### Constrained relative paths only

Rejected as the final design. Containment reduces traversal risk but does not prevent stale references, filename reuse, or ambiguous ownership.

### UUIDs without resource records

Rejected. A UUID without a server-side parent, lifecycle, and locator record cannot enforce ownership or resolve the current internal object safely.

### Keep operation state in memory

Acceptable only for a documented single-process limitation. Persisted records are preferred when operation results or progress must survive restart.

## Risks And Tradeoffs

- Additional records and lifecycle transitions increase implementation and reconciliation work.
- Existing clients must migrate from filenames and relative paths to opaque references.
- Persisting operations requires retention and cleanup rules.
- Filesystem and SQLite changes cannot share one transaction; compensation and reconciliation remain necessary.
- Resource records do not replace path, SQL, symlink, or destination controls.

## Testing And Validation

- Test output creation, download, deletion, cross-project references, stale IDs, filename reuse, and traversal.
- Test backup listing and restore by resource ID, including deleted backups, wrong-parent IDs, and filename reuse.
- Test upload creation, listing, metadata access, and data-source use by resource ID across project and shared parents.
- Test operation ownership, parent authorization, result-resource authorization, revocation, cleanup, and restart behavior if persistence is implemented.
- Test that API responses do not expose sensitive absolute paths or permit client-selected filesystem destinations.
- Run focused backend tests, the full backend suite, and the relevant filesystem-boundary and deployment checks from the parent security plan.

## Acceptance Criteria

- [ ] Outputs, backups, uploads, and operations have server-owned records with stable IDs, lifecycle state, and required parent relationships.
- [ ] Later reads, downloads, restores, metadata operations, and operation results resolve through those records before accessing internal locators.
- [ ] Client requests cannot select arbitrary filesystem paths as resource identities.
- [ ] Deleted resources, stale IDs, cross-parent IDs, and filename reuse cannot disclose or transfer access.
- [ ] Operation progress, streaming, cancellation, and result access enforce both operation ownership and current parent/resource authorization.
- [ ] Physical paths remain internal and are not exposed in resource identifiers or sensitive error responses.
- [ ] Focused isolation, lifecycle, traversal, and regression tests pass.

## Recommended Delivery Order

1. Define resource types, API schemas, lifecycle transitions, and compatibility rules.
2. Implement output and backup records, then update download and restore flows.
3. Implement upload records and replace filename-based metadata and data-source references.
4. Make operation records and result references server-owned, with a documented persistence decision.
5. Add cross-resource, stale-reference, filename-reuse, traversal, and response-disclosure tests.
6. Update the cutover and release evidence once the parent security plan accepts the new contracts.

## Final Recommendation

Adopt server-owned resource identifiers as the completion requirement for the remaining path-identity work. Keep the implemented centralized authorization design closed in `done`; track this narrower follow-up as an independent security sub-proposal under the parent mitigation plan.
