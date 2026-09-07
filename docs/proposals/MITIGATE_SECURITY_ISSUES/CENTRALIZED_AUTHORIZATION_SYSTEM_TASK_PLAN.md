# Task Plan: Centralized Authorization System

## Phase Summary

- Status: Ready for implementation after proposal approval
- Proposal: [CENTRALIZED_AUTHORIZATION_SYSTEM.md](./CENTRALIZED_AUTHORIZATION_SYSTEM.md)
- Parent phase: Phase 1 — Enforce Nginx Identity, Authorization, And CORS Controls
- Goal: enforce one documented authorization policy for all Phase 1 protected resources while keeping authentication provider details replaceable

**Acceptance Criteria**

- [ ] The authorization policy, role model, principal contract, stable resource identity, and inheritance rules are approved and documented.
- [ ] Resource records, grants, application roles, schema versions, and audit events are stored in a dedicated SQLite database outside user-editable directories.
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

- [ ] Add typed principal, action, resource-reference, role, grant, and authorized-resource models.
- [ ] Add the `AuthorizationRepository` contract and SQLite implementation using foreign keys, WAL mode, a busy timeout, and short transactions.
- [ ] Add schema-versioned migrations for resources, grants, application roles, and audit events.
- [ ] Add generation-specific UUID resource records, lifecycle states, parent relationships, and unique active locator constraints.
- [ ] Implement the central role-to-action policy and inherited resource rules.
- [ ] Implement `AuthorizationService` checks and standard denial handling.
- [ ] Add the authentication adapter that converts verified nginx identity into a stable principal.
- [ ] Add atomic audit records for grant, application-role, and resource-lifecycle mutations.
- [ ] Add bootstrap administration, last-owner protection, and last-admin protection.
- [ ] Add dry-run, migration, backup, restore, integrity-check, and resource-reconciliation commands.
- [ ] Reject missing production administrators, development principals outside development or test, and authorization database paths inside user-editable directories.

**Completion Criteria**

Unit-tested authorization decisions can load persistent grants, deny unknown combinations, return an authorized resource without depending on nginx-specific fields, and preserve authorization identity across delete and name reuse.

### 3. Enforce Project And Child-Resource Access

**Objective**

Protect projects and everything whose ownership derives from a project.

**Tasks**

- [ ] Add FastAPI dependencies for project viewer, editor, executor, and owner requirements.
- [ ] Filter project listings by readable grants.
- [ ] Assign the creator as owner when project creation is allowed.
- [ ] Require source `viewer` and `project_creator` access when copying a project, and assign a new resource UUID and owner to the copy.
- [ ] Require project authorization before creating or reusing an editing session.
- [ ] Require both session ownership and current project authorization for later session use.
- [ ] Apply project checks to configuration, entities, columns, directives, validation, preview, mapping, reconciliation, materialization, layout, and target-model routes.
- [ ] Apply inherited checks to uploads, backups, task state, generated outputs, and project operations.
- [ ] Replace client-supplied output and backup paths with server-resolved resource identifiers.
- [ ] Record the principal and parent project on long-running operations and authorize progress, streaming, cancellation, and result access.
- [ ] Route project creation, copying, deletion, and any future rename through the resource lifecycle service with compensation and reconciliation for filesystem failures.

**Completion Criteria**

A principal cannot list, read, edit, execute, delete, restore, download, or monitor another project or its child resources without the required grant.

### 4. Enforce Shared And Administrative Resource Access

**Objective**

Protect shared data, database operations, logs, and ingester capabilities.

**Tasks**

- [ ] Filter shared-data-source listings by readable grants.
- [ ] Require operator access for shared-data-source creation, upload, update, deletion, and cache administration, using the resource lifecycle service for create and delete.
- [ ] Require shared-data-source access before returning configuration, testing connections, introspecting schemas, previewing tables, or executing queries.
- [ ] Require both project and shared-source access when a project references a shared source.
- [ ] Require administrator access for viewing or downloading application logs.
- [ ] Require explicit authenticated access for nonsensitive ingester metadata and `operator` for ingester validation and execution.
- [ ] Require `admin` for ingester configuration and registration.
- [ ] Keep unsafe ingester operations disabled until source, project, database, and destination authorization and containment checks are implemented.
- [ ] Require explicit authorization for every source and destination used by an approved ingester operation.

**Completion Criteria**

Shared sources, schemas, queries, logs, and ingester operations enforce their documented application and resource roles without disclosing unauthorized resource details.

### 5. Document The Authorization System

**Objective**

Make policy, operations, endpoint protection, and authentication-provider separation maintainable.

**Tasks**

- [ ] Document principals, roles, actions, resource types, inheritance, and deny-by-default behavior.
- [ ] Publish and maintain the route authorization inventory with each route's required resource and action.
- [ ] Document how to configure the SQLite authorization store.
- [ ] Document initial ownership assignment, enforcement cutover, rollback, backup, and recovery.
- [ ] Document how operators grant, review, and revoke project and application access.
- [ ] Document how developers protect a new endpoint, service method, and background operation.
- [ ] Document `401`, `403`, concealed `404`, and filtered-list API behavior.
- [ ] Document audit events and prohibited sensitive audit content.
- [ ] Document the nginx identity adapter and stable principal contract.
- [ ] Document SQLite placement, single-host limits, migration, integrity checking, backup, restore, and resource reconciliation.
- [ ] Document bootstrap, last-owner and last-admin protection, and the explicit development principal.
- [ ] Cross-link the authorization documentation with [NATIVE_APPLICATION_AUTHENTICATION.md](../future/NATIVE_APPLICATION_AUTHENTICATION.md) and state which contracts a future authentication provider must preserve.

**Completion Criteria**

Maintainers, operators, and API users can find one consistent description of implemented authorization behavior, and the route inventory matches the registered routes.

### 6. Validate Coverage And Cut Over

**Objective**

Prove policy behavior and enable enforcement without unowned resources or hidden bypasses.

**Tasks**

- [ ] Add policy unit tests for every role, action, and protected resource type.
- [ ] Add unauthenticated, unauthorized, and allowed endpoint tests for each sensitive router.
- [ ] Add cross-user, cross-project, cross-source, session, output, backup, operation, and ingester tests.
- [ ] Add tests showing that project access does not imply access to referenced shared sources.
- [ ] Add tests for filtered list responses and the approved `403`/`404` behavior.
- [ ] Add tests for bootstrap idempotence, last-owner and last-admin protection, deletion and name reuse, and lifecycle compensation.
- [ ] Add tests for SQLite migration, concurrent access, transaction rollback, backup, restore, reconciliation, and integrity checks.
- [ ] Add service-level tests that bypass route dependencies and still reject unchecked sensitive work.
- [ ] Add an automated route inventory check that reports undeclared sensitive routes.
- [ ] Inventory deployed resources and assign reviewed initial owners and grants.
- [ ] Verify that no required resource is unowned before enforcement cutover.
- [ ] Verify that no project or shared-source locator is missing or conflicts with an active resource record.
- [ ] Run focused backend tests and the full backend regression suite.
- [ ] Record cutover and rollback verification against the exact release commit.

**Completion Criteria**

All protected routes and operations pass the authorization matrix, the route inventory is complete, existing resources have reviewed grants, and deployment cutover and rollback are verified.

## Progress Tracker

| Area | Status | Notes |
|---|---|---|
| Inventories and migration inputs | Not started | Requires proposal approval and deployment resource review |
| Authorization foundation | Not started | Depends on the reviewed inventories and migration manifest |
| Project and child resources | Not started | Deliver before shared and administrative resources |
| Shared and administrative resources | Not started | Ingester execution also depends on capability restrictions |
| Authorization documentation | Not started | Starts with policy decisions and remains aligned through cutover |
| Validation and cutover | Not started | Requires reviewed initial grants |

## Definition Of Done

- [ ] One central policy denies unknown actions, roles, and resources by default.
- [ ] Persistent resource records, grants, roles, and audit events cannot be changed through project YAML or project file endpoints.
- [ ] Every Phase 1 protected route and background operation appears in the route inventory and enforces its declared requirement.
- [ ] Project sessions do not grant project access.
- [ ] Shared-source access is checked separately from project access.
- [ ] Outputs, backups, uploads, and operations resolve through server-owned records rather than arbitrary client paths.
- [ ] Existing projects have reviewed owners, and shared resources have reviewed access grants.
- [ ] Resource deletion and name reuse cannot transfer grants to a new resource.
- [ ] The final project owner and final application administrator cannot be removed.
- [ ] Focused authorization tests and the backend regression suite pass.
- [ ] Operator, developer, deployment, API behavior, and policy documentation matches the delivered system.
- [ ] The stable principal contract and native-authentication relationship are documented and tested independently of nginx-specific request fields.
- [ ] Remaining policy decisions or unsupported cases are recorded explicitly.

## Validation And Testing

- Use unit tests for role expansion, inheritance, deny-by-default behavior, grant persistence, and application roles.
- Use `TestClient` tests for authentication and authorization responses on every sensitive route.
- Test list filtering separately from single-resource access.
- Test service and background-operation entry points without relying on route dependencies.
- Test grant creation, revocation, concurrent reads and writes, lifecycle compensation, migration, backup, restore, reconciliation, and integrity checks for SQLite.
- Test that revocation blocks new operations and later operation access while an already-running operation retains its recorded authorization snapshot.
- Run the backend test suite defined by the repository workflow after focused authorization tests pass.
- Review the maintained route inventory against the registered FastAPI routes.

## Deliverables

| Deliverable | Description | Status | Link |
|---|---|---|---|
| Approved authorization policy | Roles, actions, resources, inheritance, and response rules | Not started | [CENTRALIZED_AUTHORIZATION_SYSTEM.md](./CENTRALIZED_AUTHORIZATION_SYSTEM.md) |
| Authorization repository | SQLite resource records, grants, application roles, audit events, and migrations outside project-managed data | Not started | TBD |
| Authorization enforcement | Dependencies, service checks, operation ownership, and resource resolution | Not started | TBD |
| Route authorization inventory | Maintained list of sensitive routes and required actions | Not started | TBD |
| Operator and deployment guide | Grants, initial ownership, cutover, rollback, backup, and recovery | Not started | TBD |
| Developer guide | Protecting endpoints, services, and background operations | Not started | TBD |
| Authorization regression suite | Policy, route, service, and cross-resource checks | Not started | TBD |
| Release verification record | Tested release commit, ownership inventory, cutover, and rollback results | Not started | TBD |

## Scope

**In scope**

- The resource authorization work assigned to Phase 1 of the parent security plan.
- Persistent grants, policy decisions, route and service enforcement, documentation, migration, and tests.
- The stable principal contract required to keep authorization independent of the authentication provider.

**Out of scope**

- Native application login, credential storage, token issuance, account recovery, and multi-factor authentication.
- Filesystem containment, SQL safety, secret redaction, and network restrictions except where authorization must compose with those controls.
- Enabling an ingester capability that remains unsafe after authorization succeeds.

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
