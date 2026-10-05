# Proposal: Ingester Authorization

## Status

- Proposed change
- Scope: authorization for ingester metadata, validation, execution, configuration, and registration
- Goal: apply application roles and resource authorization without enabling operations that lack source, destination, and containment checks

## Summary

Use the centralized authorization policy for ingester application roles and authorize each project, source, and destination used by an operation. Replace caller-selected paths and destinations with approved resource references. Keep operations unavailable until their authorization and containment checks are implemented and tested.

This proposal complements [Secure Ingester Filesystem And Destination Access](../INGESTER_FILESYSTEM_BOUNDARIES/INGESTER_FILESYSTEM_BOUNDARIES.md), which defines the required path containment and server-managed destination controls.

## Problem

An application role grants permission to run an ingester, but does not authorize the particular project, source, or destination used by that run. The documented ingester request accepts a server file path and output folder, and it has no project locator. A deployment-wide `operator` permission therefore cannot by itself prevent access to another user's project, an unrelated source, or an unapproved destination.

The centralized policy defines `operator` for `run_ingesters` and `admin` for all defined actions, including `configure_ingesters`. The route inventory specifies authenticated access for ingester metadata and `application:run_ingesters` for validation and ingestion. Resource authorization and containment remain separate requirements.

## Scope

- Require an authenticated principal for ingester metadata.
- Require the `operator` role for validation and execution.
- Require the `admin` role for ingester configuration and registration.
- Authorize every project, source, database, and destination used by an enabled operation.
- Apply the same checks to HTTP, service, and background entry points.
- Keep operations unavailable until all required authorization and containment checks are in place.

## Non-Goals

- Replacing the centralized authorization policy or changing its principal contract.
- Repeating filesystem containment and database-destination design covered by the companion proposal.
- Changing ingester transformation behavior or enabling an operation before its required checks exist.

## Current Behavior

The [authorization policy](../../AUTHORIZATION.md) defines deployment roles and the `run_ingesters` and `configure_ingesters` actions. The [route inventory](../../AUTHORIZATION_ROUTE_INVENTORY.md) documents the metadata, validation, and ingestion requirements. It also notes that validation and ingestion requests have no project locator and carry a server file path and output folder. These application-level requirements do not establish authorization for the resources selected by a run.

## Proposed Design

### Apply application roles

Use the existing centralized policy without adding a separate ingester role system:

| Operation | Requirement |
|---|---|
| Read ingester metadata | Authenticated principal |
| Validate or execute an ingester | `operator` (`application:run_ingesters`) |
| Configure or register an ingester | `admin` (`application:configure_ingesters`) |

Apply the requirement at the route and at any service or background entry point that can perform the operation. A request that both executes and performs an admin-only registration must satisfy both requirements; it must not inherit registration permission from `operator`.

### Authorize operation resources

Treat the application role as a necessary but insufficient check. Before reading or writing data, resolve each operation's project, source, database, and destination to an approved resource and authorize the requested action. A project-bound operation requires `project:execute`; an `operator` role does not grant access to every project. A source and destination require their own applicable resource checks.

Do not accept a raw filesystem path or caller-selected database connection as proof of authorization. Use uploaded content or a server-managed resource reference and pass authorized resource records or validated handles to the operation implementation. Apply the companion filesystem proposal's containment checks before any file or database side effect.

Enforce these checks in the service or operation layer as well as at HTTP routes, so direct calls and background work cannot bypass them. Deny an operation before access or side effects whenever a required resource cannot be resolved, authorized, or contained.

### Keep incomplete operations unavailable

Do not enable the current path-based operation merely because the caller has the `operator` role. Keep it disabled until its API inputs, project scope, source, database, and destination have enforceable authorization and containment rules. The replacement API should use approved content or resource references and server-managed destinations.

## Alternatives Considered

- **Use only the application role.** Rejected because `operator` is deployment-wide and does not authorize a specific project, source, or destination.
- **Keep caller-selected paths and add route checks.** Rejected because direct service and background calls could bypass the route, and a role check does not confine filesystem or database access.
- **Remove all ingester routes.** Deferred. The safer default is to keep unsupported operations unavailable while deciding whether their API should be removed or redesigned around approved resources.

## Risks And Tradeoffs

- Requiring approved resource references may change request models and operator workflows.
- Project-scoped authorization requires the API to identify the project affected by a run. Truly project-agnostic operations need an explicitly defined alternative resource policy.
- Keeping operations unavailable until every check is ready delays use, but avoids treating a deployment role as unrestricted access to server resources.

## Testing And Validation

- Test unauthenticated, insufficient-role, and allowed access for every ingester route.
- Verify metadata requires authentication, validation and execution require `operator`, and configuration and registration require `admin`.
- Test project, source, database, and destination authorization, including cross-user, cross-project, and cross-source denials.
- Exercise route, direct service, and background entry points; assert denied operations cause no file or database side effects.
- Verify operations with missing authorization or containment checks remain unavailable, including when invoked directly.

## Acceptance Criteria

- `P-AC-1` Ingester metadata requires an authenticated principal and no deployment role.
- `P-AC-2` Validation and execution require `operator`; configuration and registration require `admin` at every entry point.
- `P-AC-3` Every enabled operation authorizes its applicable project, source, database, and destination before accessing protected data.
- `P-AC-4` Application roles do not substitute for resource authorization, and denied requests cause no protected-data side effects.
- `P-AC-5` Operations lacking required authorization or containment checks remain unavailable through routes, services, and background entry points.
- `P-AC-6` Regression tests cover allowed and denied role decisions, cross-user/project/source access, direct entry points, and disabled-operation behavior.

## Planning Handoff

- Preserve the centralized principal contract and existing `operator`/`admin` action mappings.
- Keep application-role checks separate from authorization of the resources used by each run.
- Reuse the companion filesystem proposal for approved references, containment, and server-managed database destinations; map this proposal's criteria to that work rather than duplicating it.
- Resolve whether each operation is project-scoped and, if so, require a project reference and `project:execute` before enabling it.
- Resolve whether `do_register` is ingester configuration, data registration, or part of execution, and apply the corresponding role before implementation.
- Validate that denied operations fail before file reads, database connections, or writes.

## Open Questions

- Must every ingester execution be tied to a project, or are any operations intentionally project-agnostic?
- What authorization resource represents uploaded content and each approved database or destination?
- Does the `do_register` option perform an admin-only registration, or is it a distinct operation with a different authorization requirement?

## Final Recommendation

Adopt the existing centralized application roles, require separate authorization for every resource an ingester uses, and redesign operation inputs around approved resources. Keep any operation unavailable until its authorization and containment checks are enforced and tested across route, service, and background entry points.