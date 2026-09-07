# Task Plan: Centralized Authorization System

## Phase Summary

- Status: In progress
- Proposal: [CENTRALIZED_AUTHORIZATION_SYSTEM.md](./CENTRALIZED_AUTHORIZATION_SYSTEM.md)
- Parent phase: Phase 1 — Enforce Nginx Identity, Authorization, And CORS Controls
- Goal: enforce one documented authorization policy for all Phase 1 protected resources while keeping authentication provider details replaceable

**Acceptance Criteria**

- [ ] The authorization policy, role model, principal contract, stable resource identity, and inheritance rules are approved and documented.
- [x] Resource records, grants, application roles, schema versions, and audit events are stored in a dedicated SQLite database outside user-editable directories.
- [ ] Every sensitive route and background operation has an explicit authorization requirement.
- [ ] Existing projects and shared resources have reviewed initial grants before enforcement cutover.
- [ ] Cross-user, cross-project, cross-source, and role-matrix tests pass.
- [ ] Authorization remains independent of nginx so future native authentication can use the same principal and policy contracts.

## Work Breakdown

### 1. Establish Inventories And Migration Inputs

**Objective**

Produce the reviewed route, resource, and initial-grant inputs required by implementation and cutover.

**Tasks**

- [ ] Inventory projects, shared data sources, uploads, outputs, backups, logs, schemas, queries, tasks, operations, ingesters, documentation routes, and direct application routes.
- [ ] Assign every registered route and background operation its resource type, action, and public or authenticated status.
- [ ] Identify every project and shared-source create, copy, delete, and rename path that must use the resource lifecycle service.
- [ ] Identify service methods that read or mutate protected data and must receive an authorized resource.
- [ ] Define the reviewed initial-administrator and initial-resource-grant manifest format.
- [ ] Inventory deployed projects and shared data sources and prepare initial project-owner and shared-source-access grants without changing project YAML.
- [ ] Confirm that trusted-proxy principal IDs are exact, case-sensitive values and identify any deployment identities that need correction before migration.

**Completion Criteria**

The route and operation inventory covers all registered non-health routes, lifecycle entry points and protected service methods are identified, and the initial migration manifest is ready for review.

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

Ingester authorization tasks are tracked in [INGESTER_AUTHORIZATION_TASKS.md](../CHANGE_REQUEST_INGESTER/INGESTER_AUTHORIZATION_TASKS.md).

**Completion Criteria**

Shared sources, schemas, queries, and logs enforce their documented application and resource roles without disclosing unauthorized resource details.

### 5. Document The Authorization System

**Objective**

Make policy, operations, endpoint protection, and authentication-provider separation maintainable.

**Tasks**

- [x] Document principals, roles, actions, resource types, inheritance, and deny-by-default behavior in [AUTHORIZATION.md](../../AUTHORIZATION.md).
- [x] Publish and maintain the route authorization inventory with each route's required resource and action in [AUTHORIZATION_ROUTE_INVENTORY.md](../../AUTHORIZATION_ROUTE_INVENTORY.md).
- [x] Document how to configure the SQLite authorization store in [OPERATIONS.md](../../OPERATIONS.md#authorization-sqlite-store).
- [x] Document initial ownership assignment, enforcement cutover, rollback, backup, and recovery in [OPERATIONS.md](../../OPERATIONS.md#authorization-ownership-and-recovery).
- [ ] Document how operators grant, review, and revoke project and application access. Initial manifest assignment and reconciliation are documented in [OPERATIONS.md](../../OPERATIONS.md#grant-review-and-revocation); ongoing grant-management interfaces remain unimplemented.
- [x] Document how developers protect a new endpoint, service method, and background operation in [DEVELOPMENT.md](../../DEVELOPMENT.md#authorization-for-protected-work).
- [x] Document `401`, `403`, concealed `404`, and filtered-list API behavior in [AUTHORIZATION.md](../../AUTHORIZATION.md#denial-behavior).
- [x] Document audit events and prohibited sensitive audit content in [AUTHORIZATION.md](../../AUTHORIZATION.md#audit-records).
- [x] Document the nginx identity adapter and stable principal contract in [AUTHORIZATION.md](../../AUTHORIZATION.md#principals).
- [x] Document SQLite placement, single-host limits, migration, integrity checking, backup, restore, and resource reconciliation in [OPERATIONS.md](../../OPERATIONS.md#authorization-sqlite-store).
- [x] Document bootstrap, last-owner and last-admin protection, and the explicit development principal in [AUTHORIZATION.md](../../AUTHORIZATION.md) and [OPERATIONS.md](../../OPERATIONS.md#authorization-sqlite-store).
- [x] Cross-link the authorization documentation with [NATIVE_APPLICATION_AUTHENTICATION.md](../future/NATIVE_APPLICATION_AUTHENTICATION.md) and state which contracts a future authentication provider must preserve.

**Completion Criteria**

Maintainers, operators, and API users can find one consistent description of implemented authorization behavior, and the route inventory matches the registered routes.

### 6. Validate Coverage And Cut Over

**Objective**

Prove policy behavior and enable enforcement without unowned resources or hidden bypasses.

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
- [ ] Inventory deployed resources and assign reviewed initial owners and grants.
- [ ] Verify that no required resource is unowned before enforcement cutover.
- [ ] Verify that no project or shared-source locator is missing or conflicts with an active resource record.
- [ ] Run focused backend tests and the full backend regression suite.
- [ ] Record cutover and rollback verification against the exact release commit.

**Completion Criteria**

All protected routes and operations pass the authorization matrix, the route inventory is complete, existing resources have reviewed grants, and deployment cutover and rollback are verified.

### 7. Implement Authorization Administration CLI

**Objective**

Provide a supported command-line interface for operators to inspect and manage authorization state without editing SQLite directly or maintaining a declarative manifest after initial migration.

**Tasks**

- [ ] Add commands to list resources, grants, application roles, and authorization audit events.
- [ ] Add commands to grant and revoke project and shared-data-source roles.
- [ ] Add commands to assign and revoke application roles, including `operator` and `project_creator`.
- [ ] Require an actor principal ID for every mutation and record it in the audit event.
- [ ] Preserve final-project-owner and final-application-administrator protections.
- [ ] Resolve resources by type and active locator, and reject unknown or deleted resources.
- [ ] Provide machine-readable JSON output and human-readable table output.
- [ ] Add `--dry-run` support for all mutation commands.
- [ ] Add confirmation for destructive revocations, with a non-interactive override for controlled automation.
- [ ] Document commands for adding users, granting project access, reviewing access, revoking access, backup, restore, and integrity checks.
- [ ] Add unit and CLI integration tests for allowed mutations, rejected input, audit events, final-assignment protection, and JSON output.

**Completion Criteria**

An operator can safely list current authorization state and grant or revoke supported application and resource roles through repository APIs, with audit records and safeguards enforced.

### 8. Support Group-Based And Wildcard-Style Project Access

**Objective**

Allow a project to grant access to a set of users without creating one grant row per principal, while preserving explicit resource identity, deny-by-default behavior, and protection against overly broad owner permissions.

**Design Direction**

- Represent broad access with typed grant subjects such as `principal`, `group`, and authenticated `everyone`; do not use a literal principal ID such as `*`.
- Resolve group membership from the trusted authentication provider or another verified membership source. Do not infer group membership from client request fields.
- Evaluate matching principal, group, and `everyone` subjects in the central authorization service before applying the role-to-action policy.
- Treat `everyone` as authenticated users only unless an explicit public-access policy is approved. Anonymous requests remain denied by default.
- Do not grant `owner` to `everyone` by default. The current owner role includes deletion and grant management; broad access should normally use `viewer`, `editor`, `executor`, or a separately defined limited role.
- Keep final-owner protection meaningful when broad subjects are introduced. A project must not become unmanageable because its only explicit owner was removed or because a broad grant was revoked.

**Tasks**

- [ ] Approve the subject model, supported membership sources, and whether authenticated `everyone` access is required.
- [x] Extend grant models, SQLite schema, migrations, manifests, reconciliation, backup, restore, and audit records for typed subjects.
- [x] Update authorization policy evaluation and service-level authorization checks to include verified group membership and broad subjects.
- [x] Define which roles may be assigned to groups or `everyone`, with explicit safeguards for `owner`, `delete`, and `manage_grants` actions.
- [x] Add administration commands and review output for typed broad grants.
- [x] Add tests for principal, group, and `everyone` matching; membership changes; denied anonymous access; deleted and reused resources; revocation; inheritance; and final-owner protection.
- [x] Document broad-access grants, their security implications, membership source, audit behavior, and migration or rollback procedure.
- [ ] Integrate a trusted membership lookup so operator review can expand group subjects into effective principals.

**Completion Criteria**

Approved broad-access grants are evaluated centrally, recorded against generation-specific resource UUIDs, auditable, manageable through supported operator workflows, and covered by tests that prevent anonymous access and unsafe wildcard ownership.


## Progress Tracker

| Area | Status | Notes |
|---|---|---|
| Inventories and migration inputs | Not started | Requires proposal approval and deployment resource review |
| Authorization foundation | Done | Typed policy, SQLite repository, stable principal adapter, atomic mutation audit, bootstrap, final-assignment protections, schema initialization, manifest dry-run inspection and application, backup, restore, integrity checks, manifest reconciliation, and production startup guards are implemented |
| Project and child resources | Done | Project and child-resource routes enforce current project authorization. Long-running operations record their principal and stable parent project resource and authorize progress, streaming, cancellation, and result access. Backup restore and execution downloads use server-managed identifiers resolved through project containment checks. Project create, copy, and delete operations register and transition authorization resource records with filesystem operation compensation. |
| Shared and administrative resources | In progress | Shared data source listings now return only sources with readable grants. Shared data source creation, upload, update, deletion, and schema-cache invalidation now require operator access. Create and delete update authorization resource records. Shared source configuration reads, connection tests, named schema introspection, table previews, query execution, and query-column introspection now require shared-source read access. Project data-source connections and project configuration updates require both project edit access and read access to every referenced shared source. Viewing and downloading application logs require the administrator-only `read_logs` action. |
| Authorization documentation | In progress | The implemented principal, role, action, resource, inheritance, response, audit, stable-principal, and deny-by-default rules are documented in [AUTHORIZATION.md](../../AUTHORIZATION.md). Registered routes and their current authorization declarations are published in [AUTHORIZATION_ROUTE_INVENTORY.md](../../AUTHORIZATION_ROUTE_INVENTORY.md). SQLite store configuration, ownership assignment, cutover, rollback, backup, and recovery are documented in [OPERATIONS.md](../../OPERATIONS.md#authorization-sqlite-store). Developer authorization guidance is documented in [DEVELOPMENT.md](../../DEVELOPMENT.md#authorization-for-protected-work). Ongoing grant-management interfaces and their operator documentation remain pending. |
| Validation and cutover | In progress | Policy and dependency matrices cover allowed and denied outcomes for each declared requirement class. Route-wide unauthenticated checks cover every declared protected endpoint; query, administrator log, and operation endpoint matrices exercise concrete protected routes. Cross-user isolation covers projects, project-child outputs and backups, and shared sources; sessions and operations require ownership plus current project access. Concurrent SQLite grant writes, project-creation lifecycle compensation, and an automated sensitive-locator route check are implemented. Remaining storage tests, service checks, deployment inventory, and cutover verification remain. |
| Group and wildcard-style project access | In progress | Typed subjects, SQLite migration, central matching, manifest support, safeguards, operator grant/review/revoke commands, documentation, and focused tests are implemented. Trusted membership lookup for effective-principal review remains. |

## Definition Of Done

- [x] One central policy denies unknown actions, roles, and resources by default.
- [x] Persistent resource records, grants, roles, and audit events cannot be changed through project YAML or project file endpoints.
- [ ] Every Phase 1 protected route and background operation appears in the route inventory and enforces its declared requirement.
- [x] Project sessions do not grant project access.
- [x] Shared-source access is checked separately from project access.
- [ ] Outputs, backups, uploads, and operations resolve through server-owned records rather than arbitrary client paths.
- [ ] Existing projects have reviewed owners, and shared resources have reviewed access grants.
- [x] Resource deletion and name reuse cannot transfer grants to a new resource.
- [x] The final project owner and final application administrator cannot be removed.
- [x] Broad project access uses typed, auditable subjects and cannot grant unsafe owner capabilities to every authenticated user by default.
- [ ] Focused authorization tests and the backend regression suite pass.
- [ ] Operator, developer, deployment, API behavior, and policy documentation matches the delivered system.
- [ ] The stable principal contract and native-authentication relationship are documented and tested independently of nginx-specific request fields.
- [ ] Remaining policy decisions or unsupported cases are recorded explicitly.

## Validation And Testing

- Use unit tests for every role, action, and protected resource type; role expansion; inheritance; deny-by-default behavior; grant persistence; application roles; manifest migration; manifest reconciliation; and production authorization settings. The current focused authorization suite covers these implemented foundation paths.
- Use route-wide HTTP tests for unauthenticated responses on every declared protected route, with policy and dependency matrices for each requirement class. Focused endpoint tests cover query, logs, and operations; focused authorization tests cover project dependency binding, readable project and shared-source filtering, project owner assignment helpers, session ownership plus current project authorization, and the approved `403`/concealed `404` behavior.
- Test list filtering separately from single-resource access. Project and shared-data-source list filtering are covered.
- Test service and background-operation entry points without relying on route dependencies.
- Test grant creation, revocation, concurrent reads and writes, lifecycle compensation, migration, backup, restore, reconciliation, and integrity checks for SQLite.
- Test that revocation blocks new operations and later operation access while an already-running operation retains its recorded authorization snapshot.
- Test typed principal, group, and authenticated-`everyone` subjects, including membership changes, anonymous denial, broad-grant revocation, inheritance, and final-owner protection.
- Run the backend test suite defined by the repository workflow after focused authorization tests pass. The focused authorization, operations, and configuration tests pass; the full backend run did not produce a completion result in the current environment.
- Review the maintained route inventory against the registered FastAPI routes.

## Deliverables

| Deliverable | Description | Status | Link |
|---|---|---|---|
| Approved authorization policy | Roles, actions, resources, inheritance, and response rules | Not started | [CENTRALIZED_AUTHORIZATION_SYSTEM.md](./CENTRALIZED_AUTHORIZATION_SYSTEM.md) |
| Authorization repository | SQLite resource records, grants, application roles, audit events, migrations, manifest operations, backups, restore, integrity checks, and reconciliation outside project-managed data | Done | [authorization repository](../../../backend/app/authorization/repository.py) |
| Authorization enforcement | Dependencies, service checks, operation ownership, and resource resolution | In progress | [authorization dependencies](../../../backend/app/authorization/dependencies.py) |
| Route authorization inventory | Registered API routes and their declared authorization requirements | Done | [AUTHORIZATION_ROUTE_INVENTORY.md](../../AUTHORIZATION_ROUTE_INVENTORY.md) |
| Operator and deployment guide | Initial ownership, cutover, rollback, backup, and recovery | In progress | [OPERATIONS.md](../../OPERATIONS.md#authorization-ownership-and-recovery) |
| Developer guide | Protecting endpoints, services, and background operations | Done | [DEVELOPMENT.md](../../DEVELOPMENT.md#authorization-for-protected-work) |
| Authorization regression suite | Policy, route, service, and cross-resource checks | In progress | [authorization tests](../../../backend/tests/authorization/) |
| Release verification record | Tested release commit, ownership inventory, cutover, and rollback results | Not started | TBD |

## Scope

**In scope**

- The resource authorization work assigned to Phase 1 of the parent security plan.
- Persistent grants, policy decisions, route and service enforcement, documentation, migration, and tests.
- The stable principal contract required to keep authorization independent of the authentication provider.

**Out of scope**

- Native application login, credential storage, token issuance, account recovery, and multi-factor authentication.
- Filesystem containment, SQL safety, secret redaction, and network restrictions except where authorization must compose with those controls.
- Ingester authorization and capability enablement, which are tracked in [INGESTER_AUTHORIZATION_TASKS.md](../CHANGE_REQUEST_INGESTER/INGESTER_AUTHORIZATION_TASKS.md).

## Risks And Mitigations

- **Existing resources lack owners:** require a reviewed inventory and block cutover while required resources remain unowned.
- **Routes escape coverage:** maintain an automated route inventory check.
- **Endpoint and service rules drift:** pass authorized resources to sensitive services and keep role mappings central.
- **Future authentication changes identity values:** use stable principal IDs and require an explicit identity migration.
- **Authorization is mistaken for capability safety:** keep path, SQL, network, and destination restrictions as separate required controls.
- **Filesystem and authorization records diverge:** use lifecycle states, compensation, and an explicit reconciliation command.
- **Deleted names inherit old grants:** attach grants to generation-specific UUIDs, not project names or filenames.
- **SQLite is deployed beyond its limits:** support one application host and replace the repository before multi-host deployment.

## Resolved Decisions

- SQLite backs the first repository and is supported for one application host.
- The `project_creator` application role controls creation; project owners manage project grants; administrators manage all grants and application roles.
- Shared-source read, connection test, schema inspection, preview, and read-only query use one `reader` grant.
- Resource-addressed denial returns concealed `404`; application-scoped denial returns `403`; lists are filtered.
- Revocation blocks new work and later operation access but does not automatically cancel work already executing.
- Direct principal grants are in scope; team and group grants are deferred until authentication supplies verified membership.

## Assumptions

- Phase 1 continues to receive authenticated identity from nginx.
- Work is ordered by technical dependency, not staffing or release dates.
- The Phase 1 deployment uses one application host; the current in-memory session and operation managers already require a single worker.
- Native application authentication remains future work and will adopt the stable principal contract rather than replace authorization policy.
