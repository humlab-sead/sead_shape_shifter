# Centralized Authorization System

## Status

- Proposed sub-proposal / not yet approved
- Parent proposal: [Mitigate Security Issues](./MITIGATE_SECURITY_ISSUES.md)
- Task plan: [Centralized Authorization System Task Plan](./CENTRALIZED_AUTHORIZATION_SYSTEM_TASK_PLAN.md)
- Related future work: [Native Application Authentication](../future/NATIVE_APPLICATION_AUTHENTICATION.md)
- Phase: Phase 1 — Enforce Nginx Identity, Authorization, And CORS Controls

## Summary

Shape Shifter should use one application authorization system to decide whether an authenticated identity may perform an action on a resource. FastAPI dependencies should enforce the decision before endpoint work begins, and sensitive services and background operations should receive an authorized resource rather than relying only on route checks.

The system should start with project roles, application roles, and explicit grants for shared data sources. Project-owned resources such as uploads, generated outputs, backups, tasks, and project queries inherit project access. Schema and shared-query access inherit shared-data-source access. Application logs and ingester administration require application roles.

Authentication and authorization remain separate. Phase 1 continues to trust the verified identity supplied by nginx. A future native authentication mechanism may replace that identity provider without changing authorization rules, grants, or resource ownership.

## Problem

The trusted-proxy middleware can establish who made a request, and the session dependency can reject a session used by a different identity. Neither mechanism establishes which projects, shared data sources, outputs, backups, logs, queries, tasks, or ingester operations that identity may access.

Adding independent checks to each endpoint would duplicate policy, produce inconsistent status codes, and make new endpoints easy to expose accidentally. Route-only checks would also be insufficient for service calls and background operations that continue after the initiating request.

## Scope

This proposal covers:

- a stable principal derived from the authenticated identity,
- project roles, application roles, and shared-data-source grants,
- centralized authorization decisions for resource and action pairs,
- FastAPI dependencies for early enforcement,
- service and background-operation enforcement for sensitive work,
- ownership rules for project child resources,
- audit records for authorization-sensitive actions,
- route inventory, policy, operations, and developer documentation,
- migration rules for existing projects and deployments.

## Non-Goals

- Implementing native login, credentials, tokens, account recovery, or multi-factor authentication.
- Treating CORS, project sessions, filesystem checks, or SQL validation as authorization.
- Storing authorization grants in user-editable project YAML.
- Defining row-level database permissions inside external data sources.
- Enabling ingester operations before their filesystem, database, and destination restrictions are complete.

## Current Position

- Nginx supplies a verified identity to FastAPI through the trusted proxy contract.
- FastAPI rejects protected requests without that identity when proxy authentication is enabled.
- Project sessions record the authenticated identity and reject use by a different identity.
- Project metadata has no owner, team, role, or grant model.
- Shared data-source, schema, query, task, output, backup, log, and ingester endpoints do not share a resource authorization policy.
- Long-running operation records do not have required principal and project ownership fields.

## Terms

- **Principal:** the stable application identity used for authorization. In Phase 1 this is derived from the verified nginx identity.
- **Action:** an operation such as `read`, `edit`, `execute`, `delete`, `manage`, or `read_logs`.
- **Resource:** the protected object identified by a type and stable ID, such as a project or shared data source.
- **Grant:** a persistent assignment of a role to a principal for a resource.
- **Application role:** a role whose scope is the complete deployment, such as `operator` or `admin`.
- **Authorized resource:** a value returned after a successful authorization decision and passed to endpoint or service code.

## Proposed Design

### 1. Policy model

Use these initial project roles:

| Role | Allowed work |
|---|---|
| `viewer` | Read project configuration, project files, schemas, task status, and completed results |
| `editor` | Viewer work plus modify projects, uploads, mappings, task state, and other project configuration |
| `executor` | Viewer work plus previews, validation runs, queries, reconciliation, materialization, and exports |
| `owner` | All project work, including deletion and grant management |

Use these initial application roles:

| Role | Allowed work |
|---|---|
| `operator` | Manage shared data sources and approved ingester operations |
| `admin` | Manage application roles and read application logs; includes operator work |

Roles are additive. For example, a user who must edit and execute receives both `editor` and `executor` unless a later approved policy combines them.

The policy must be declared in one module as explicit role-to-action mappings. Endpoints and services must not reproduce those mappings.

### 2. Persistent grants

Store grants outside project YAML and outside any directory writable through project endpoints. The selected store must support atomic updates, concurrent requests, backup, migration, and lookup by principal and resource.

The logical grant record contains:

```text
principal_id
resource_type
resource_id
role
created_at
created_by
```

Application-role assignments use the same audit requirements. The implementation should access storage through an `AuthorizationRepository` contract so the policy and endpoint dependencies do not depend on one storage technology. The initial storage backend must be selected and documented before implementation begins.

### 3. Central authorization service

An `AuthorizationService` should expose one decision contract equivalent to:

```python
is_allowed(principal, action, resource) -> bool
```

It should also provide checked methods that return an authorized resource or raise the standard denial response. The service owns role expansion, inherited access, application-role checks, and audit context. It does not authenticate the request and does not resolve user-controlled filesystem paths.

Authorization decisions deny access by default when the resource type, action, role, or grant is unknown.

### 4. FastAPI dependencies

Add dependencies for common requirements, including:

- authenticated principal,
- project reader, editor, executor, and owner,
- shared-data-source reader and manager,
- operator,
- administrator.

Project endpoints should receive an authorized project reference instead of relying on an unchecked route string. Data-source, operation, output, and backup dependencies should resolve the server-owned record and authorize it before returning it to endpoint code.

Router-level authentication may remain useful, but resource authorization must be explicit for every sensitive endpoint. A route inventory test should fail when a protected route lacks an authorization declaration.

### 5. Service and background enforcement

Sensitive service operations should accept an authorized resource or authorization context. This protects calls made outside their original route and makes the resource used for authorization the same resource used for the operation.

Long-running operations must record at least:

- the initiating principal,
- the parent project or protected resource,
- the operation type,
- creation and completion timestamps.

Progress, streaming, cancellation, and result access must authorize against that recorded parent resource. An operation ID alone grants no access.

### 6. Resource rules

| Resource or operation | Required authorization |
|---|---|
| List projects | Return only projects readable by the principal |
| Create project | Deployment project-creation permission; creator becomes owner |
| Read project and project child data | Project `viewer` |
| Edit project, uploads, mappings, layouts, or tasks | Project `editor` |
| Execute, preview, validate, query project data, reconcile, or materialize | Project `executor` |
| Delete project, restore backup, or manage project grants | Project `owner` |
| Read or query shared data source | Explicit shared-data-source read grant or approved application role |
| Create, update, or delete shared data source | `operator` |
| Inspect schema or preview table data | Same access as the referenced data source |
| Import shared table into project | Shared-data-source read plus project `editor` |
| Read generated output | Access to its recorded parent project |
| Read application logs | `admin` |
| List public ingester metadata | Authenticated principal, if metadata contains no sensitive values |
| Validate or run an ingester | Approved ingester role plus access to every source, project, and destination |
| Configure or register ingesters | `admin` |

Project sessions do not grant project access. Session creation requires project access, and each later session use must verify both session ownership and current project authorization.

Project references to shared data sources do not grant access to those sources. The principal needs access to both the project and every referenced shared source used by the requested operation.

### 7. Server-owned resource identifiers

Generated outputs, backups, uploads, and operations should be addressed by opaque or constrained identifiers that resolve through server-owned records. Clients must not supply arbitrary filesystem paths as resource identifiers.

Authorization happens before file, connection, or other sensitive configuration is returned. Path containment, SQL restrictions, and destination allowlists remain separate checks after authorization succeeds.

### 8. Response and audit behavior

- Return `401` when no valid authenticated principal exists.
- Return `403` when the principal is known but the action is forbidden.
- Use a consistent `404` policy where hiding resource existence is required.
- Filter list responses instead of returning entries that the principal cannot read.
- Record grant changes, project ownership changes, administrative operations, denied sensitive actions, and high-impact allowed actions.
- Do not place credentials, SQL text, sensitive paths, or secret configuration in authorization audit records.

## Existing Project Migration

The system must not make every authenticated user an owner of every existing project. Before authorization enforcement is enabled, deployments must choose and document an initial ownership assignment for each existing project and shared data source.

Migration should:

1. inventory existing protected resources,
2. create explicit initial grants through an administrative process,
3. report resources with no assigned owner,
4. prevent enforcement cutover while unowned required resources remain,
5. support rollback without discarding recorded grants.

Development-only defaults may be supported when proxy authentication is disabled, but they must be explicit, restricted to development settings, and impossible to enable silently in shared or production deployments.

## Documentation Requirements

Implementation is incomplete until these documents are maintained:

1. an authorization model describing principals, roles, actions, resources, inheritance, and deny-by-default behavior,
2. a route authorization inventory listing every sensitive route and required action,
3. deployment instructions for selecting the grant store, assigning initial owners, and performing cutover or rollback,
4. operator instructions for granting, reviewing, and revoking access,
5. developer instructions for protecting a new endpoint or background operation,
6. API behavior for `401`, `403`, concealed `404`, and filtered lists,
7. the authentication-provider contract that explains how nginx identity becomes an authorization principal.

The route inventory should be reviewable against the registered FastAPI routes and should be covered by an automated completeness check.

## Relationship To Native Application Authentication

[Native Application Authentication](../future/NATIVE_APPLICATION_AUTHENTICATION.md) concerns how Shape Shifter establishes identity. This proposal concerns what an established identity may do.

The authorization system must therefore depend on a stable principal contract, not on nginx headers directly. A small authentication adapter should convert the current verified nginx identity into that principal. A future native login, token, passkey, or external identity-provider adapter must produce the same principal contract.

Authorization grants, project ownership, resource identifiers, policy evaluation, service enforcement, and audit records should survive an authentication-provider change. Any future identity migration must define how old principal IDs map to new principal IDs without broadening access.

Native authentication is not a dependency for this proposal or for Phase 1. Conversely, native authentication must not be approved as a replacement for resource authorization.

## Risks And Mitigations

- **Incomplete route coverage:** maintain a route inventory and fail an automated check for undeclared sensitive routes.
- **Policy duplicated in endpoints:** keep role-to-action mappings in the central policy module.
- **Editable ownership data:** store grants outside project YAML and project-managed paths.
- **Access changes during long operations:** record the initiating principal and resource, and define whether revocation cancels active work before implementation.
- **Resource enumeration:** apply one documented `403`/`404` policy and filter list endpoints.
- **Authentication migration broadens access:** use stable principal IDs and require an explicit identity-mapping migration.
- **Development bypass reaches production:** reject unsafe development defaults in shared and production configuration.

## Acceptance Criteria

- [ ] One documented policy maps roles to actions for every protected resource group in Phase 1.
- [ ] Grants and application roles are stored outside user-editable project data through an `AuthorizationRepository` contract.
- [ ] Project, shared-data-source, upload, output, backup, log, schema, query, task, operation, and ingester routes enforce the documented policy.
- [ ] Sensitive services and background operations cannot rely only on possession of a name, path, session ID, or operation ID.
- [ ] Project sessions require both session ownership and current project authorization.
- [ ] Project and shared-resource list endpoints omit unauthorized entries.
- [ ] Existing resources receive explicit reviewed grants before enforcement cutover.
- [ ] Cross-user, cross-project, cross-source, and role-matrix tests pass.
- [ ] The maintained authorization documentation and route inventory match implemented behavior.
- [ ] Replacing nginx authentication does not require changing authorization policy or stored grants.

## Open Questions

1. Which durable store should back `AuthorizationRepository` in the first implementation?
2. Who may create a project, and is that permission an application role or deployment setting?
3. Should project owners be allowed to grant roles directly, or must an administrator approve changes?
4. Should shared-data-source read and query permissions be separate?
5. Which denied requests should return concealed `404` instead of `403`?
6. Does revoking access cancel active operations or only prevent subsequent access to progress and results?

## Recommendation

Approve this sub-proposal as the Phase 1 authorization design. Select the initial grant store and resolve the access-management questions before implementing endpoint checks. Deliver project authorization first, then project child resources, shared data sources with schema and query access, administrative resources, and constrained ingester operations.
