# Task Plan: Centralized Authorization System

## Phase Summary

- Status: Closed — implementation complete and archived
- Completed proposal: [CENTRALIZED_AUTHORIZATION_SYSTEM.md](./CENTRALIZED_AUTHORIZATION_SYSTEM.md)
- Follow-up plan: [CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md](../CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md)
- Deferred path-identity work: [SERVER_OWNED_RESOURCE_IDENTIFIERS.md](../SERVER_OWNED_RESOURCE_IDENTIFIERS.md)
- Parent phase: Phase 1 — Enforce Nginx Identity, Authorization, And CORS Controls
- Goal: enforce one documented authorization policy for all Phase 1 protected resources while keeping authentication provider details replaceable

**Acceptance Criteria**

- [x] The authorization policy, role model, principal contract, stable resource identity, and inheritance rules are approved and documented.
- [x] Resource records, grants, application roles, schema versions, and audit events are stored in a dedicated SQLite database outside user-editable directories.
- Final classification of every sensitive route and background operation, and reviewed initial grants for existing projects and shared resources, are owned by the separate [CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md](../CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md).
- [x] Cross-user, cross-project, cross-source, and role-matrix tests pass in the focused authorization suite.
- [x] Authorization remains independent of nginx so future native authentication can use the same principal and policy contracts.

## Work Breakdown

### Follow-up: Authorization Cutover

The implementation task plan is complete. Deployment inventory, final route classification, initial grants, readiness validation, enforcement cutover, and rollback are owned by the separate [CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md](../CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md).

### 2. Implement Authorization Foundation

**Objective**

Provide one deny-by-default authorization decision path.

**Tasks**

- [x] Add typed principal, action, resource-reference, role, grant, and authorized-resource models.
- [x] Add the `AuthorizationRepository` contract and SQLite implementation using foreign keys, WAL mode, a busy timeout, and short transactions.
- [x] Add schema-versioned migrations for resources, grants, application roles, and audit events.
- [x] Add generation-specific UUID resource records, lifecycle states, parent relationships, and unique active locator constraints.
- [x] Implement the central role-to-action policy and inherited resource rules.
- [x] Implement `AuthorizationService` checks and standard denial handling.
- [x] Add the authentication adapter that converts verified nginx identity into a stable principal.
- [x] Add atomic audit records for grant, application-role, and resource-lifecycle mutations.
- [x] Add bootstrap administration, last-owner protection, and last-admin protection.
- [x] Add dry-run, migration, backup, restore, integrity-check, and resource-reconciliation commands.
- [x] Reject missing production administrators, development principals outside development or test, and authorization database paths inside user-editable directories.

**Completion Criteria**

Unit-tested authorization decisions can load persistent grants, deny unknown combinations, return an authorized resource without depending on nginx-specific fields, and preserve authorization identity across delete and name reuse.

### 3. Enforce Project And Child-Resource Access

**Objective**

Protect projects and everything whose ownership derives from a project.

**Tasks**

- [x] Add FastAPI dependencies for project viewer, editor, executor, and owner requirements.
- [x] Filter project listings by readable grants.
- [x] Assign the creator as owner when project creation is allowed.
- [x] Require source `viewer` and `project_creator` access when copying a project, and assign a new resource UUID and owner to the copy.
- [x] Require project authorization before creating or reusing an editing session.
- [x] Require both session ownership and current project authorization for later session use.
- [x] Apply project checks to the primary project management and project file lifecycle routes, including project reads, metadata updates, raw YAML updates, backup restore, project layout reads/writes, and project file uploads.
- [x] Apply inherited checks to entities, columns, directives, validation, preview, mapping, reconciliation, materialization, task state, and execution routes. All project-scoped child-resource operations now require project authorization before accessing project data.
- [x] Replace client-supplied output and backup paths with server-resolved resource identifiers.
- [x] Record the principal and parent project on long-running operations and authorize progress, streaming, cancellation, and result access.
- [x] Route project creation, copying, deletion, and any future rename through the resource lifecycle service with compensation and reconciliation for filesystem failures.

**Completion Criteria**

A principal cannot list, read, edit, execute, delete, restore, download, or monitor another project or its child resources without the required grant.

### 4. Enforce Shared And Administrative Resource Access

**Objective**

Protect shared data, database operations, and logs.

**Tasks**

- [x] Filter shared-data-source listings by readable grants.
- [x] Require operator access for shared-data-source creation, upload, update, deletion, and cache administration, using the resource lifecycle service for create and delete.
- [x] Require shared-data-source access before returning configuration, testing connections, introspecting schemas, previewing tables, or executing queries.
- [x] Require both project and shared-source access when a project references a shared source.
- [x] Require administrator access for viewing or downloading application logs.
- [x] Protect `GET /api/v1/data-sources/files` and `GET /api/v1/data-sources/excel/metadata` so file listing and metadata reads are limited to what the principal is allowed to read. Project-local reads (`location=local` plus `project_name`) must require project access for that project and must not disclose another project's uploaded files.
- [x] Global shared-data file browsing and metadata inspection require the operator role (`application:manage_shared_sources`); project-local reads require read access to the named project. Enforced by per-request context resolution in the endpoint handlers and recorded in [AUTHORIZATION_ROUTE_INVENTORY.md](../../../AUTHORIZATION_ROUTE_INVENTORY.md).
- [x] Reconcile [AUTHORIZATION_ROUTE_INVENTORY.md](../../../AUTHORIZATION_ROUTE_INVENTORY.md) with the registered `data_sources`, `schema`, and `query` routes, replacing every remaining `UNDECLARED` shared-data row (the `/data-sources` list, `/drivers`, `/entity-types`, `/files`, `/excel/metadata`, `POST /tables`, and `POST /tables/schema`) with a declared resource/action or an explicit authenticated-only classification.
- [x] Extend the automated route inventory check so static data-source sub-routes cannot remain silently undeclared, and confirm the check passes against the reconciled inventory.
- [x] Add allowed and denied tests for the newly protected file and metadata routes, including unauthenticated, cross-project, operator, and reader outcomes.

Ingester authorization tasks are tracked in [INGESTER_AUTHORIZATION_TASKS.md](../../CHANGE_REQUEST_INGESTER/INGESTER_AUTHORIZATION_TASKS.md).

**Completion Criteria**

Shared sources, schemas, queries, and logs enforce their documented application and resource roles without disclosing unauthorized resource details.

### 5. Document The Authorization System

**Objective**

Make policy, operations, endpoint protection, and authentication-provider separation maintainable.

**Tasks**

- [x] Document principals, roles, actions, resource types, inheritance, and deny-by-default behavior in [AUTHORIZATION.md](../../../AUTHORIZATION.md).
- [x] Publish and maintain the route authorization inventory with each route's required resource and action in [AUTHORIZATION_ROUTE_INVENTORY.md](../../../AUTHORIZATION_ROUTE_INVENTORY.md).
- [x] Document how to configure the SQLite authorization store in [OPERATIONS.md](../../../OPERATIONS.md#authorization-sqlite-store).
- [x] Document initial ownership assignment, enforcement cutover, rollback, backup, and recovery in [OPERATIONS.md](../../../OPERATIONS.md#authorization-ownership-and-recovery).
- [x] Document how operators grant, review, and revoke project and application access in [OPERATIONS.md](../../../OPERATIONS.md#grant-review-and-revocation).
- [x] Document how developers protect a new endpoint, service method, and background operation in [DEVELOPMENT.md](../../../DEVELOPMENT.md#authorization-for-protected-work).
- [x] Document `401`, `403`, concealed `404`, and filtered-list API behavior in [AUTHORIZATION.md](../../../AUTHORIZATION.md#denial-behavior).
- [x] Document audit events and prohibited sensitive audit content in [AUTHORIZATION.md](../../../AUTHORIZATION.md#audit-records).
- [x] Document the nginx identity adapter and stable principal contract in [AUTHORIZATION.md](../../../AUTHORIZATION.md#principals).
- [x] Document SQLite placement, single-host limits, migration, integrity checking, backup, restore, and resource reconciliation in [OPERATIONS.md](../../../OPERATIONS.md#authorization-sqlite-store).
- [x] Document bootstrap, last-owner and last-admin protection, and the explicit development principal in [AUTHORIZATION.md](../../../AUTHORIZATION.md) and [OPERATIONS.md](../../../OPERATIONS.md#authorization-sqlite-store).
- [x] Cross-link the authorization documentation with [NATIVE_APPLICATION_AUTHENTICATION.md](../../future/NATIVE_APPLICATION_AUTHENTICATION.md) and state which contracts a future authentication provider must preserve.

**Completion Criteria**

Maintainers, operators, and API users can find one consistent description of implemented authorization behavior, and the route inventory matches the registered routes.

### 6. Validate Coverage

**Objective**

Prove policy behavior and implementation coverage without relying on route-only checks.

**Tasks**

- [x] Add policy unit tests for every role, action, and protected resource type.
- [x] Add unauthenticated, unauthorized, and allowed endpoint tests for each sensitive router. Route-wide unauthenticated checks cover every declared protected endpoint; policy and dependency matrices cover the allowed and denied outcomes for each declared requirement class.
- [x] Add cross-user, cross-project, cross-source, session, output, backup, and operation tests. The authorization matrix covers separate users, projects, project-child outputs and backups, and shared sources; session and operation tests cover ownership plus current project access.
- [x] Add tests showing that project access does not imply access to referenced shared sources.
- [x] Add tests for filtered list responses and the approved `403`/`404` behavior.
- [x] Add tests for bootstrap idempotence, last-owner and last-admin protection, deletion and name reuse, and lifecycle compensation.
- [x] Add tests for SQLite migration, concurrent access, transaction rollback, backup, restore, reconciliation, and integrity checks.
- [x] Add service-level tests that bypass route dependencies and still reject unchecked sensitive work.
- [x] Add an automated route inventory check that reports undeclared sensitive locator routes.
- Production route classification, deployment inventory, readiness validation, enforcement cutover, and rollback are owned by the separate [CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md](../CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md).

**Completion Criteria**

Implemented protected routes and operations pass the authorization matrix. Production route completion, reviewed resources, deployment cutover, and rollback are outside this implementation plan and are gated by [CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md](../CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md).

### 7. Implement Authorization Administration CLI

**Objective**

Provide a supported command-line interface for operators to inspect and manage authorization state without editing SQLite directly or maintaining a declarative manifest after initial migration.

**Tasks**

- [x] Add commands to list resources, grants, application roles, and authorization audit events.
- [x] Add commands to grant and revoke project and shared-data-source roles.
- [x] Add commands to assign and revoke application roles, including `operator` and `project_creator`.
- [x] Require an actor principal ID for every mutation and record it in the audit event.
- [x] Preserve final-project-owner and final-application-administrator protections.
- [x] Resolve resources by type and active locator, and reject unknown or deleted resources.
- [x] Provide machine-readable JSON output and human-readable table output.
- [x] Add `--dry-run` support for all mutation commands.
- [x] Add confirmation for destructive revocations, with a non-interactive override for controlled automation.
- [x] Document commands for adding users, granting project access, reviewing access, revoking access, backup, restore, and integrity checks.
- [x] Add unit and CLI integration tests for allowed mutations, rejected input, audit events, final-assignment protection, and JSON output.

**Completion Criteria**

An operator can safely list current authorization state and grant or revoke supported application and resource roles through repository APIs, with audit records and safeguards enforced.

### 8. Support Group-Based And Wildcard-Style Project Access

**Objective**

Allow a project to grant access to a set of users without creating one grant row per principal, while preserving explicit resource identity, deny-by-default behavior, and protection against overly broad owner permissions.

**Design Direction**

- Represent broad access with typed grant subjects such as `principal`, `group`, and authenticated `everyone`; do not use a literal principal ID such as `*`.
- Resolve group membership from the trusted authentication provider or another verified membership source. Do not infer group membership from client request fields.
- Separate runtime group matching from operator membership review. The nginx group header may supply groups for the current request, but it cannot enumerate all members of a group.
- Add a provider-neutral membership resolver that queries the configured trusted identity authority for review. The resolver must return the group, effective principal IDs, provider, lookup time, and a resolved, unavailable, or not-found status.
- Keep the trusted provider authoritative for membership. SQLite stores group grants, not membership rows. This phase does not cache membership snapshots; reconsider a non-authoritative, expiring review cache only if provider availability or review latency creates an operational need.
- Evaluate matching principal, group, and `everyone` subjects in the central authorization service before applying the role-to-action policy.
- Treat `everyone` as authenticated users only unless an explicit public-access policy is approved. Anonymous requests remain denied by default.
- Do not grant `owner` to `everyone` by default. The current owner role includes deletion and grant management; broad access should normally use `viewer`, `editor`, `executor`, or a separately defined limited role.
- Keep final-owner protection meaningful when broad subjects are introduced. A project must not become unmanageable because its only explicit owner was removed or because a broad grant was revoked.

**Tasks**

- [x] Approve the subject model, trusted nginx group-header source, and authenticated `everyone` as an opt-in subject.
- [x] Extend grant models, SQLite schema, migrations, manifests, reconciliation, backup, restore, and audit records for typed subjects, including typed subject identity in audit events.
- [x] Update authorization policy evaluation and service-level authorization checks to include verified group membership and broad subjects.
- [x] Define which roles may be assigned to groups or `everyone`, with explicit safeguards for `owner`, `delete`, and `manage_grants` actions.
- [x] Add administration commands and review output for typed broad grants.
- [x] Add tests for principal, group, and `everyone` matching; membership changes; denied anonymous access; deleted and reused resources; revocation; inheritance; and final-owner protection.
- [x] Document broad-access grants, their security implications, membership source, audit behavior, and migration or rollback procedure.
- [x] Add a provider-neutral trusted membership resolver and an adapter for the configured identity authority. Do not treat the nginx request header as a directory or membership enumeration API.
- [x] Extend the administration CLI with an explicit effective-access review mode, including group expansion, provider and freshness metadata, unresolved-group reporting, strict failure handling, and machine-readable JSON output.
- [x] Audit membership lookup attempts and results without storing credentials or unnecessary directory data. Record the actor, provider, group, timestamp, result, and freshness or error status.
- [x] Decide and document membership caching for review availability. Do not add a SQLite membership snapshot cache in this phase. Reconsider only if provider availability or review latency creates an operational need; any future cache must be non-authoritative, expiring, and must never materialize group membership as individual grant rows.
- [x] Add focused resolver and CLI tests for successful expansion, unavailable and not-found groups, strict mode, JSON output, audit records, and the separation between review lookup and runtime authorization.

**Completion Criteria**

Approved broad-access grants are evaluated centrally, recorded against generation-specific resource UUIDs, auditable, manageable through supported operator workflows, and covered by tests that prevent anonymous access and unsafe wildcard ownership. Operators can review group grants with effective principals and can distinguish current provider results from unavailable or not-found membership data.


## Progress Tracker

| Area | Status | Notes |
|---|---|---|
| Inventories and migration inputs | Done | Implementation inputs are defined and handed off; deployment-resource, principal, and manifest review work belongs to the follow-up cutover plan |
| Authorization foundation | Done | Typed policy, SQLite repository, stable principal adapter, atomic mutation audit, bootstrap, final-assignment protections, schema initialization, manifest dry-run inspection and application, backup, restore, integrity checks, manifest reconciliation, and production startup guards are implemented |
| Project and child resources | Done | Project and child-resource routes enforce current project authorization. Long-running operations record their principal and stable parent project resource and authorize progress, streaming, cancellation, and result access. Backup restore and execution downloads use server-managed identifiers resolved through project containment checks. Project create, copy, and delete operations register and transition authorization resource records with filesystem operation compensation. |
| Shared and administrative resources | Done | Implemented: shared data source listings are filtered by readable grants; creation, upload, update, deletion, and schema-cache invalidation require operator access with resource-record updates on create and delete; shared source reads (configuration, connection tests, schema introspection, table previews, and query execution and columns) require shared-source read access; project data-source connections and project configuration updates require project edit plus read access to every referenced shared source; application logs require the `read_logs` action; `GET /api/v1/data-sources/files` and `GET /api/v1/data-sources/excel/metadata` enforce operator access for global scope and project read for project-local scope. Shared-data route inventory is reconciled with the registered routes and the automated route inventory check covers static data-source sub-routes. Config-driven data-source introspection follow-up and release-level regression are owned by the cutover plan. |
| Authorization documentation | Done | Policy, route inventory, operations, developer guidance, audit behavior, stable-principal rules, and administration CLI workflows are documented. The separate cutover plan owns deployment evidence. |
| Validation | Done | Policy and dependency matrices, route checks for implemented protected routes, cross-user isolation, lifecycle compensation, SQLite concurrency, and focused authorization tests are implemented. Production readiness and cutover are tracked separately. |
| Group and wildcard-style project access | Done | Typed subjects, SQLite migration, central matching, safeguards, membership resolver, effective-access CLI review, audit records, documentation, focused tests, and the no-cache decision are implemented. |

## Definition Of Done

- [x] One central policy denies unknown actions, roles, and resources by default.
- [x] Persistent resource records, grants, roles, and audit events cannot be changed through project YAML or project file endpoints.
- [x] Implemented protected routes and operations have declared authorization requirements; final production classification is tracked in [CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md](../CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md).
- [x] Project sessions do not grant project access.
- [x] Shared-source access is checked separately from project access.
- Outputs, backups, uploads, and operations resolve through server-owned records rather than arbitrary client paths — deferred to [SERVER_OWNED_RESOURCE_IDENTIFIERS.md](../SERVER_OWNED_RESOURCE_IDENTIFIERS.md) as the follow-up completion requirement for the remaining path-identity work.
- [x] The reviewed-manifest workflow supports initial owners and grants; deployment review is tracked in the follow-up cutover plan.
- [x] Resource deletion and name reuse cannot transfer grants to a new resource.
- [x] The final project owner and final application administrator cannot be removed.
- [x] Broad project access uses typed, auditable subjects and cannot grant unsafe owner capabilities to every authenticated user by default.
- [x] Focused authorization tests pass; full backend regression and release validation belong to the follow-up cutover plan.
- [x] Operator, developer, API behavior, policy, and administration documentation matches the delivered implementation.
- [x] The stable principal contract and native-authentication relationship are documented and tested independently of nginx-specific request fields.
- [x] Remaining implementation policy decisions and unsupported cases are recorded explicitly; deployment blockers are tracked in the cutover plan.

## Validation And Testing

- Use unit tests for every role, action, and protected resource type; role expansion; inheritance; deny-by-default behavior; grant persistence; application roles; manifest migration; manifest reconciliation; and production authorization settings. The current focused authorization suite covers these implemented foundation paths.
- Use route-wide HTTP tests for unauthenticated responses on every declared protected route, with policy and dependency matrices for each requirement class. Focused endpoint tests cover query, logs, and operations; focused authorization tests cover project dependency binding, readable project and shared-source filtering, project owner assignment helpers, session ownership plus current project authorization, and the approved `403`/concealed `404` behavior.
- Test list filtering separately from single-resource access. Project and shared-data-source list filtering are covered.
- Test service and background-operation entry points without relying on route dependencies.
- Test grant creation, revocation, concurrent reads and writes, lifecycle compensation, migration, backup, restore, reconciliation, and integrity checks for SQLite.
- Test that revocation blocks new operations and later operation access while an already-running operation retains its recorded authorization snapshot.
- Test typed principal, group, and authenticated-`everyone` subjects, including membership changes, anonymous denial, broad-grant revocation, inheritance, and final-owner protection.
- Test membership review separately from runtime authorization: successful provider expansion, unavailable and not-found groups, freshness reporting, strict CLI failure behavior, JSON output, and the rule that review failures do not silently change authorization decisions.
- Cutover-specific regression, route-inventory, manifest, backup, and deployment checks are defined in [CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md](../CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md).

## Deliverables

| Deliverable | Description | Status | Link |
|---|---|---|---|
| Approved authorization policy | Roles, actions, resources, inheritance, and response rules | Done | [CENTRALIZED_AUTHORIZATION_SYSTEM.md](./CENTRALIZED_AUTHORIZATION_SYSTEM.md) |
| Authorization repository | SQLite resource records, grants, application roles, audit events, migrations, manifest operations, backups, restore, integrity checks, and reconciliation outside project-managed data | Done | [authorization repository](../../../../backend/app/authorization/repository.py) |
| Authorization enforcement | Dependencies, service checks, operation ownership, and resource resolution | Done | [authorization dependencies](../../../../backend/app/authorization/dependencies.py) |
| Route authorization inventory | Registered API routes and their declared authorization requirements | Done | [AUTHORIZATION_ROUTE_INVENTORY.md](../../../AUTHORIZATION_ROUTE_INVENTORY.md) |
| Authorization cutover plan | Ordered route, deployment, readiness, cutover, and rollback phases | Done | [CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md](../CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md) |
| Operator and deployment guide | Initial ownership, cutover, rollback, backup, and recovery | In progress | [OPERATIONS.md](../../../OPERATIONS.md#authorization-ownership-and-recovery) |
| Developer guide | Protecting endpoints, services, and background operations | Done | [DEVELOPMENT.md](../../../DEVELOPMENT.md#authorization-for-protected-work) |
| Authorization regression suite | Focused policy, route, service, and cross-resource checks for implemented routes; release-level regression and sign-off are owned by the cutover plan | Done | [authorization tests](../../../../backend/tests/authorization/) |
| Release verification record | Tested release commit, ownership inventory, cutover, and rollback results | Not started (cutover plan) | [CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md](../CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md) |

## Scope

**In scope**

- The resource authorization work assigned to Phase 1 of the parent security plan.
- Persistent grants, policy decisions, route and service enforcement, documentation, migration, and tests.
- The stable principal contract required to keep authorization independent of the authentication provider.

**Out of scope**

- Native application login, credential storage, token issuance, account recovery, and multi-factor authentication.
- Filesystem containment, SQL safety, secret redaction, and network restrictions except where authorization must compose with those controls.
- Ingester authorization and capability enablement, which are tracked in [INGESTER_AUTHORIZATION_TASKS.md](../../CHANGE_REQUEST_INGESTER/INGESTER_AUTHORIZATION_TASKS.md).

## Risks And Mitigations

- **Existing resources lack owners:** require a reviewed inventory and block cutover while required resources remain unowned.
- **Routes escape coverage:** maintain an automated route inventory check.
- **Endpoint and service rules drift:** pass authorized resources to sensitive services and keep role mappings central.
- **Future authentication changes identity values:** use stable principal IDs and require an explicit identity migration.
- **Authorization is mistaken for capability safety:** keep path, SQL, network, and destination restrictions as separate required controls.
- **Filesystem and authorization records diverge:** use lifecycle states, compensation, and an explicit reconciliation command.
- **Deleted names inherit old grants:** attach grants to generation-specific UUIDs, not project names or filenames.
- **SQLite is deployed beyond its limits:** support one application host and replace the repository before multi-host deployment.
- **Membership provider is unavailable during review:** report the lookup status and error, keep the provider authoritative, and reconsider caching only if availability or review latency becomes an operational problem.

## Resolved Decisions

- SQLite backs the first repository and is supported for one application host.
- The `project_creator` application role controls creation; project owners manage project grants; administrators manage all grants and application roles.
- Shared-source read, connection test, schema inspection, preview, and read-only query use one `reader` grant.
- Resource-addressed denial returns concealed `404`; application-scoped denial returns `403`; lists are filtered.
- Revocation blocks new work and later operation access but does not automatically cancel work already executing.
- Typed principal, group, and authenticated-`everyone` subjects are approved. Group matching is disabled until the trusted nginx group source is explicitly enabled. Authenticated-`everyone` matching is disabled by default and requires explicit deployment configuration; anonymous requests remain denied.
- Runtime group matching and operator membership review are separate concerns. Runtime matching may use verified groups from nginx; effective-principal review requires a trusted membership resolver backed by an identity authority that can enumerate group members.
- SQLite remains authoritative for grants, resources, roles, and authorization audit events. It does not store group membership in this phase. Effective review queries the trusted provider directly; a future cache would be optional, expiring, non-authoritative, and review-only.
- Config-driven data-source introspection routes (`POST /api/v1/data-sources/tables` and `POST /api/v1/data-sources/tables/schema`) remain authenticated-only pending an approved design that resolves the client-supplied config server-side from a registered data source. This follow-up is tracked with the cutover plan rather than treated as a reviewed grant.

## Assumptions

- Phase 1 continues to receive authenticated identity from nginx.
- The configured identity authority exposes a trusted membership lookup for operator review, or an adapter can be added to the authority service that does so. The nginx group header alone cannot provide this capability.
- Membership review queries the trusted provider directly in this phase; no SQLite membership snapshot cache is required for the initial deployment.
- Work is ordered by technical dependency, not staffing or release dates.
- The Phase 1 deployment uses one application host; the current in-memory session and operation managers already require a single worker.
- Native application authentication remains future work and will adopt the stable principal contract rather than replace authorization policy.
