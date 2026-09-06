# Task Plan: Centralized Authorization System

## Phase Summary

- Status: Not started
- Proposal: [CENTRALIZED_AUTHORIZATION_SYSTEM.md](./CENTRALIZED_AUTHORIZATION_SYSTEM.md)
- Parent phase: Phase 1 — Enforce Nginx Identity, Authorization, And CORS Controls
- Goal: enforce one documented authorization policy for all Phase 1 protected resources while keeping authentication provider details replaceable

**Acceptance Criteria**

- [ ] The authorization policy, role model, principal contract, and resource inheritance rules are approved and documented.
- [ ] Persistent grants are stored outside user-editable project data.
- [ ] Every sensitive route and background operation has an explicit authorization requirement.
- [ ] Existing projects and shared resources have reviewed initial grants before enforcement cutover.
- [ ] Cross-user, cross-project, cross-source, and role-matrix tests pass.
- [ ] Authorization remains independent of nginx so future native authentication can use the same principal and policy contracts.

## Work Breakdown

### 1. Resolve Policy And Storage Decisions

**Objective**

Approve the rules and storage decisions required before implementation.

**Tasks**

- [ ] Inventory projects, shared data sources, uploads, outputs, backups, logs, schemas, queries, tasks, operations, ingesters, and direct application routes.
- [ ] Assign each route and background operation a resource type and action.
- [ ] Approve project roles, application roles, role-to-action mappings, and inheritance rules.
- [ ] Decide project-creation and grant-management permissions.
- [ ] Select the initial durable grant store and document backup, migration, concurrency, and recovery behavior.
- [ ] Decide the consistent `403` and concealed `404` policy.
- [ ] Decide how access revocation affects active background operations.
- [ ] Define the stable principal ID and the nginx-to-principal adapter contract.

**Completion Criteria**

The policy table, route inventory, storage choice, principal contract, and unresolved security decisions are approved for implementation.

### 2. Implement Authorization Foundation

**Objective**

Provide one deny-by-default authorization decision path.

**Tasks**

- [ ] Add typed principal, action, resource-reference, role, grant, and authorized-resource models.
- [ ] Add the `AuthorizationRepository` contract and selected persistent implementation.
- [ ] Add schema or data migration support for grants and application roles.
- [ ] Implement the central role-to-action policy and inherited resource rules.
- [ ] Implement `AuthorizationService` checks and standard denial handling.
- [ ] Add the authentication adapter that converts verified nginx identity into a stable principal.
- [ ] Add audit records for grant changes, administrative actions, and selected authorization decisions.
- [ ] Reject unsafe development authorization defaults in shared and production configuration.

**Completion Criteria**

Unit-tested authorization decisions can load persistent grants, deny unknown combinations, and return an authorized resource without depending on nginx-specific fields.

### 3. Enforce Project And Child-Resource Access

**Objective**

Protect projects and everything whose ownership derives from a project.

**Tasks**

- [ ] Add FastAPI dependencies for project viewer, editor, executor, and owner requirements.
- [ ] Filter project listings by readable grants.
- [ ] Assign the creator as owner when project creation is allowed.
- [ ] Require project authorization before creating or reusing an editing session.
- [ ] Require both session ownership and current project authorization for later session use.
- [ ] Apply project checks to configuration, entities, columns, directives, validation, preview, mapping, reconciliation, materialization, layout, and target-model routes.
- [ ] Apply inherited checks to uploads, backups, task state, generated outputs, and project operations.
- [ ] Replace client-supplied output and backup paths with server-resolved resource identifiers.
- [ ] Record the principal and parent project on long-running operations and authorize progress, streaming, cancellation, and result access.

**Completion Criteria**

A principal cannot list, read, edit, execute, delete, restore, download, or monitor another project or its child resources without the required grant.

### 4. Enforce Shared And Administrative Resource Access

**Objective**

Protect shared data, database operations, logs, and ingester capabilities.

**Tasks**

- [ ] Filter shared-data-source listings by readable grants.
- [ ] Require operator access for shared-data-source creation, upload, update, deletion, and cache administration.
- [ ] Require shared-data-source access before returning configuration, testing connections, introspecting schemas, previewing tables, or executing queries.
- [ ] Require both project and shared-source access when a project references a shared source.
- [ ] Require administrator access for viewing or downloading application logs.
- [ ] Classify ingester metadata, validation, execution, configuration, and registration permissions.
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
- [ ] Document how to select and configure the grant store.
- [ ] Document initial ownership assignment, enforcement cutover, rollback, backup, and recovery.
- [ ] Document how operators grant, review, and revoke project and application access.
- [ ] Document how developers protect a new endpoint, service method, and background operation.
- [ ] Document `401`, `403`, concealed `404`, and filtered-list API behavior.
- [ ] Document audit events and prohibited sensitive audit content.
- [ ] Document the nginx identity adapter and stable principal contract.
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
- [ ] Add service-level tests that bypass route dependencies and still reject unchecked sensitive work.
- [ ] Add an automated route inventory check that reports undeclared sensitive routes.
- [ ] Inventory deployed resources and assign reviewed initial owners and grants.
- [ ] Verify that no required resource is unowned before enforcement cutover.
- [ ] Run focused backend tests and the full backend regression suite.
- [ ] Record cutover and rollback verification against the exact release commit.

**Completion Criteria**

All protected routes and operations pass the authorization matrix, the route inventory is complete, existing resources have reviewed grants, and deployment cutover and rollback are verified.

## Progress Tracker

| Area | Status | Notes |
|---|---|---|
| Policy and storage decisions | Not started | Initial grant store and open policy decisions require approval |
| Authorization foundation | Not started | Depends on approved policy and storage decisions |
| Project and child resources | Not started | Deliver before shared and administrative resources |
| Shared and administrative resources | Not started | Ingester execution also depends on capability restrictions |
| Authorization documentation | Not started | Starts with policy decisions and remains aligned through cutover |
| Validation and cutover | Not started | Requires reviewed initial grants |

## Definition Of Done

- [ ] One central policy denies unknown actions, roles, and resources by default.
- [ ] Persistent grants cannot be changed through project YAML or project file endpoints.
- [ ] Every Phase 1 protected route and background operation appears in the route inventory and enforces its declared requirement.
- [ ] Project sessions do not grant project access.
- [ ] Shared-source access is checked separately from project access.
- [ ] Outputs, backups, uploads, and operations resolve through server-owned records rather than arbitrary client paths.
- [ ] Existing projects and shared resources have reviewed owners and grants.
- [ ] Focused authorization tests and the backend regression suite pass.
- [ ] Operator, developer, deployment, API behavior, and policy documentation matches the delivered system.
- [ ] The stable principal contract and native-authentication relationship are documented and tested independently of nginx-specific request fields.
- [ ] Remaining policy decisions or unsupported cases are recorded explicitly.

## Validation And Testing

- Use unit tests for role expansion, inheritance, deny-by-default behavior, grant persistence, and application roles.
- Use `TestClient` tests for authentication and authorization responses on every sensitive route.
- Test list filtering separately from single-resource access.
- Test service and background-operation entry points without relying on route dependencies.
- Test grant creation, revocation, concurrent reads, migration, backup, and recovery for the selected repository.
- Run the backend test suite defined by the repository workflow after focused authorization tests pass.
- Review the maintained route inventory against the registered FastAPI routes.

## Deliverables

| Deliverable | Description | Status | Link |
|---|---|---|---|
| Approved authorization policy | Roles, actions, resources, inheritance, and response rules | Not started | [CENTRALIZED_AUTHORIZATION_SYSTEM.md](./CENTRALIZED_AUTHORIZATION_SYSTEM.md) |
| Authorization repository | Persistent grants and application roles outside project-managed data | Not started | TBD |
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

## Open Questions

- Which durable store will back the first `AuthorizationRepository` implementation?
- Who may create projects and manage project grants?
- Are shared-source read and query separate permissions?
- Which denied resource lookups return concealed `404`?
- How does access revocation affect an operation already running?

## Assumptions

- Phase 1 continues to receive authenticated identity from nginx.
- Work is ordered by technical dependency, not staffing or release dates.
- Native application authentication remains future work and will adopt the stable principal contract rather than replace authorization policy.
