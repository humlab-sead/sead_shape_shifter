# Centralized Authorization System

## Status

- Implemented Phase 1 authorization design; deployment cutover and broader Phase 1 work remain
- Parent proposal: [Mitigate Security Issues](./MITIGATE_SECURITY_ISSUES.md)
- Task plan: [Centralized Authorization System Task Plan](./CENTRALIZED_AUTHORIZATION_SYSTEM_TASK_PLAN.md)
- Related future work: [Native Application Authentication](../future/NATIVE_APPLICATION_AUTHENTICATION.md)
- Phase: Phase 1 — Enforce Nginx Identity, Authorization, And CORS Controls

## Summary

Shape Shifter uses one application authorization system to decide whether an authenticated identity may perform an action on a resource. FastAPI dependencies enforce the decision before endpoint work begins, and sensitive services and background operations receive an authorized resource rather than relying only on route checks.

The system provides project roles, application roles, and explicit grants for shared data sources. Project-owned resources such as uploads, generated outputs, backups, tasks, and project queries inherit project access. Schema and shared-query access inherit shared-data-source access. Application logs and ingester administration require application roles. Resource grants support typed `principal`, `group`, and authenticated `everyone` subjects. A dedicated SQLite database stores resource identities, typed grants, application roles, schema versions, and authorization audit events outside all project-managed directories.

Authentication and authorization remain separate. Phase 1 continues to trust the verified identity supplied by nginx. A future native authentication mechanism may replace that identity provider without changing authorization rules, grants, or resource ownership.

## Problem

The trusted-proxy middleware can establish who made a request, and the session dependency can reject a session used by a different identity. Neither mechanism establishes which projects, shared data sources, outputs, backups, logs, queries, tasks, or ingester operations that identity may access.

Adding independent checks to each endpoint would duplicate policy, produce inconsistent status codes, and make new endpoints easy to expose accidentally. Route-only checks would also be insufficient for service calls and background operations that continue after the initiating request.

## Scope

This proposal covers:

- a stable principal derived from the authenticated identity,
- project roles, application roles, and shared-data-source grants,
- typed principal, group, and authenticated-`everyone` grant subjects,
- trusted group membership review for operator access reports,
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
- Projects and shared data sources use server-owned resource records, typed grants, and centralized role checks.
- Group matching is opt-in and uses verified group IDs from the trusted nginx group source. Authenticated-`everyone` matching is separately opt-in.
- Operators can expand group grants through a configured trusted membership provider. The provider remains authoritative; membership is queried directly and is not cached in SQLite in this phase.
- Remaining work includes route inventory completion, deployment resource review, full regression validation, and enforcement cutover.

## Terms

- **Principal:** the stable application identity used for authorization. In Phase 1 this is derived from the verified nginx identity.
- **Action:** a policy operation such as `read`, `edit`, `execute`, `delete`, `manage_grants`, or `read_logs`.
- **Resource:** the protected object identified by a type and stable ID, such as a project or shared data source.
- **Grant:** a persistent assignment of a role to a typed subject for a resource. Subjects are `principal`, `group`, or authenticated `everyone`.
- **Membership review:** an operator-only lookup that expands a group subject into effective principal IDs for reporting. It does not create grants or change runtime authorization.
- **Application role:** a role whose scope is the complete deployment, such as `operator` or `admin`.
- **Authorized resource:** a value returned after a successful authorization decision and passed to endpoint or service code.
- **Resource record:** a server-owned record that assigns a stable UUID to a protected resource and maps it to its current internal locator, such as a project name or shared-data-source filename.

## Proposed Design

### 1. Policy model

Use these initial project roles:

| Role | Allowed work |
|---|---|
| `viewer` | `read` |
| `editor` | `read`, `edit` |
| `executor` | `read`, `execute` |
| `owner` | `read`, `edit`, `execute`, `delete`, `manage_grants` |

Use these initial application roles:

| Role | Allowed work |
|---|---|
| `project_creator` | `create_project` |
| `operator` | `read_all_shared_sources`, `manage_shared_sources`, `run_ingesters` |
| `admin` | All application actions: operator and project-creator actions plus `manage_all_grants`, `manage_application_roles`, `read_logs`, and `configure_ingesters` |

Project roles are additive except that `owner` contains all project actions. A principal who must edit and execute without owning the project receives both `editor` and `executor`. Shared data sources have one resource role, `reader`, which permits configuration reads, connection tests, schema inspection, previews, and read-only queries. Separating shared-source query from read access is deferred until the application has a concrete use case that requires the distinction.

The policy is declared in one module as explicit role-to-action mappings. Endpoints and services must not reproduce those mappings. Unknown resource types, actions, and roles are denied. Group matching is disabled until a trusted nginx group source is explicitly configured; authenticated-`everyone` matching is also disabled by default and requires explicit deployment approval. Anonymous requests remain denied, and broad subjects cannot receive `owner`. Group and `everyone` grants are evaluated centrally with direct grants and inherited parent-resource grants.

### 2. Principal contract

The authentication adapter produces a principal with:

```text
principal_id
authentication_provider
authenticated_at
group_ids
```

For trusted-proxy authentication, `principal_id` is the exact trimmed, validated header value. It is case-sensitive and limited to 255 characters. The provider value is audit context and is not part of grant lookup. A future authentication provider must emit the same `principal_id` values or provide an explicit, reviewed grant migration before cutover. The API must not accept a principal ID from request bodies, query parameters, or untrusted headers.

Without trusted-proxy authentication, startup must fail except in the `development` and `test` environments. Development may use one principal configured by the `DEVELOPMENT_PRINCIPAL_ID` setting; there is no implicit anonymous owner or allow-all mode. Tests should inject principals through dependency overrides rather than production configuration.

### 3. Persistence and resource identity

Use a dedicated SQLite database configured by the `AUTHORIZATION_DATABASE_PATH` setting (`SHAPE_SHIFTER_AUTHORIZATION_DATABASE_PATH` in the environment). A relative path resolves under a new application state directory, not under the project, upload, output, log, or shared-data directories. The implementation uses Python's `sqlite3` module, schema-versioned migrations, foreign keys, WAL mode, a busy timeout, and short transactions. This matches the current single-worker deployment without introducing a database framework. A future multi-host deployment must replace the repository implementation; SQLite on a shared network filesystem is not supported.

The database contains these logical records:

```text
resource: resource_id, resource_type, locator, parent_resource_id, lifecycle_state
grant: subject_type, subject_id, resource_id, role, created_at, created_by
application_role: principal_id, role, created_at, created_by
audit_event: event_id, occurred_at, actor_principal_id, event_type, resource_id, action, outcome, correlation_id, subject_type, subject_id, provider, details
schema_version: version, applied_at
```

Top-level projects and shared data sources receive UUID resource IDs. Existing API names remain locators and are resolved to resource records before authorization. Project names and shared-data-source filenames are not authorization identities. Child resources inherit through `parent_resource_id`; outputs, backups, uploads, and operations that have independent API identifiers receive server-owned records or equivalent server-owned records containing the same UUID parent reference.

Create, copy, delete, and any future rename operation must update resource lifecycle state and grants through one lifecycle service. A deleted name cannot transfer grants to a newly created resource with the same name. The service marks a resource unavailable before deleting its files and uses explicit compensation and reconciliation for failures because SQLite and filesystem changes cannot share one transaction.

The grant record contains:

```text
subject_type
subject_id
resource_id
role
created_at
created_by
```

The repository does not store authoritative group membership. Effective membership review uses a provider-neutral resolver and a configured trusted identity authority. The resolver returns the group ID, effective principal IDs, provider, lookup time, and a `resolved`, `unavailable`, or `not_found` status. The initial implementation queries the provider directly; it does not use a SQLite membership snapshot cache. A future cache would be optional, expiring, non-authoritative, and review-only.

Grant changes, resource lifecycle changes, and their audit events are committed atomically when they affect only the authorization database. The implementation accesses storage through an `AuthorizationRepository` contract so policy and endpoint dependencies do not depend on SQLite.

### 4. Central authorization service

An `AuthorizationService` should expose one decision contract equivalent to:

```python
is_allowed(principal, action, resource) -> bool
```

It should also provide checked methods that resolve a server-owned resource record and return an authorized resource or raise the standard denial response. An authorized resource contains the principal, required action, resource UUID, resource type, current internal locator, and parent resource UUID where applicable. It is valid only for the current request or background-operation snapshot and must not be accepted from API input.

The service owns role expansion, inherited access, application-role checks, and audit context. It does not authenticate the request and does not resolve user-controlled filesystem paths. Services that read or mutate protected data must receive an authorized resource or perform the same central check. Pure computation helpers do not need authorization parameters.

Authorization decisions deny access by default when the resource type, action, role, or grant is unknown.

### 5. FastAPI dependencies and route inventory

Add dependencies for common requirements, including:

- authenticated principal,
- project reader, editor, executor, and owner,
- shared-data-source reader and manager,
- operator,
- administrator.

Project endpoints should receive an authorized project reference instead of relying on an unchecked route string. Data-source, operation, output, and backup dependencies should resolve the server-owned record and authorize it before returning it to endpoint code. Multi-resource operations must request every required authorized resource explicitly.

Authorization dependency factories must attach machine-readable resource and action metadata to their FastAPI dependency. A generated route inventory compares that metadata with all registered API routes. The only public route is the configured health endpoint. The inventory test fails when any other API route lacks an authorization declaration. Static mounts, OpenAPI, and documentation routes must also appear in the inventory and be disabled or protected by the authentication middleware in production.

### 6. Service and background enforcement

Sensitive service operations should accept an authorized resource or authorization context. This protects calls made outside their original route and makes the resource used for authorization the same resource used for the operation.

Long-running operations must record at least:

- the initiating principal,
- the parent project or protected resource,
- the operation type,
- creation and completion timestamps.

Progress, streaming, cancellation, and result access must authorize against that recorded parent resource. An operation ID alone grants no access. Authorization is checked when an operation starts and again for every later control, progress, stream, and result request.

Revocation prevents new work and all later access to progress, cancellation, streams, and results. Work already executing continues under the authorization snapshot recorded at start; automatic cancellation on revocation is not part of Phase 1. An owner or administrator may cancel a running operation through the normal authorized endpoint. This behavior must be visible in audit records and operator documentation.

### 7. Resource rules

| Resource or operation | Required authorization |
|---|---|
| List projects | Return only projects readable by the principal |
| Create project | `project_creator`; creator becomes owner in the same authorization-database transaction that activates the resource record |
| Copy project | Source project `viewer` plus `project_creator`; creator becomes owner of a new resource record |
| Read project and project child data | Project `viewer` |
| Edit project, uploads, mappings, layouts, or tasks | Project `editor` |
| Execute, preview, validate, query project data, reconcile, or materialize | Project `executor` |
| Delete project, restore backup, or manage project grants | Project `owner` |
| Read, test, inspect, preview, or query shared data source | Shared-data-source `reader`, `operator`, or `admin` |
| Create, update, or delete shared data source | `operator` |
| Inspect schema or preview table data | Same access as the referenced data source |
| Import shared table into project | Shared-data-source read plus project `editor` |
| Read generated output | Access to its recorded parent project |
| Read application logs | `admin` |
| List nonsensitive ingester metadata | Authenticated principal |
| Validate or run an ingester | `operator` plus required project access and authorization for every named source and destination |
| Configure or register ingesters | `admin` |

Project sessions do not grant project access. Session creation requires project access, and each later session use must verify both session ownership and current project authorization.

Project references to shared data sources do not grant access to those sources. The principal needs access to both the project and every referenced shared source used by the requested operation.

Project owners may grant and revoke project roles, including `owner`, but may not remove the last owner. Administrators may manage all grants and application roles and may recover an ownerless resource. Operators do not receive project access unless separately granted a project role.

### 8. Server-owned resource identifiers

Generated outputs, backups, uploads, and operations should be addressed by opaque or constrained identifiers that resolve through server-owned records. Clients must not supply arbitrary filesystem paths as resource identifiers.

Authorization happens before file, connection, or other sensitive configuration is returned. Path containment, SQL restrictions, and destination allowlists remain separate checks after authorization succeeds.

### 9. Response and audit behavior

- Return `401` when no valid authenticated principal exists.
- Return `403` when the principal is known but lacks an application-scoped action, such as project creation, log access, shared-source administration, or ingester administration.
- Return `404` for an absent or unauthorized project, shared source, session, operation, output, backup, or upload addressed by identifier. This conceals resource existence and applies to all actions on that resource.
- Filter list responses instead of returning entries that the principal cannot read.
- Record grant changes, project ownership changes, administrative operations, membership review lookups, denied sensitive actions, and high-impact allowed actions.
- Do not place credentials, SQL text, sensitive paths, or secret configuration in authorization audit records.

Audit records are append-only through the application interface. Grant and application-role changes record the actor and correlation ID. Membership review records the actor, group subject, provider, lookup time, result, and error or freshness details without storing credentials or unnecessary directory data. Grant, application-role, resource-lifecycle, administrative, and execution actions fail closed when their required audit event cannot be committed. A failed denial-audit write does not turn a denial into an error or an allowed result. High-volume allowed reads and denied reads are logged through bounded normal request logging rather than the durable authorization audit table.

### 10. Bootstrap and administration

Initial administration uses the deployment-only `AUTHORIZATION_BOOTSTRAP_ADMIN_PRINCIPALS` setting (`SHAPE_SHIFTER_AUTHORIZATION_BOOTSTRAP_ADMIN_PRINCIPALS` in the environment). It is accepted only while the application-role table is empty, creates the listed `admin` assignments transactionally, records bootstrap audit events, and is ignored with a warning after any application role exists. Production startup fails when no administrator exists.

Initial resource registration and grants use an offline administrative command that supports a reviewable manifest and dry-run mode. The administration CLI lists typed grants, grants and revokes project access, and supports explicit effective group review with human-readable or JSON output. Effective review requires an actor and a trusted membership lookup URL; `--strict` reports unresolved groups as a command failure. Runtime APIs allow owners to manage grants for their projects and administrators to manage all grants and application roles. Every mutation enforces last-owner and last-admin protection.

## Existing Project Migration

The system must not make every authenticated user an owner of every existing project. Before authorization enforcement is enabled, deployments must choose and document initial owners for each project and initial access grants for each shared data source.

Migration should:

1. inventory existing protected resources,
2. assign a UUID resource record to each project and shared data source without modifying project YAML,
3. apply explicit initial grants from a reviewed manifest,
4. report projects with no assigned owner, shared sources with no reviewed access decision, and grants with invalid principals,
5. prevent enforcement cutover while required resources remain unregistered or unowned,
6. support idempotent reruns and rollback without discarding recorded grants.

The migration command must offer dry-run, create a database backup before mutation, and emit a summary that contains no secrets. Development uses an explicitly configured principal when proxy authentication is disabled; production cannot use this setting.

## Documentation Requirements

Implementation is incomplete until these documents are maintained:

1. an authorization model describing principals, roles, actions, resources, inheritance, and deny-by-default behavior,
2. a route authorization inventory listing every sensitive route and required action,
3. deployment instructions for configuring SQLite, assigning initial access, and performing cutover or rollback,
4. operator instructions for granting, reviewing, and revoking access,
5. developer instructions for protecting a new endpoint or background operation,
6. API behavior for `401`, `403`, concealed `404`, and filtered lists,
7. the authentication-provider contract that explains how nginx identity becomes an authorization principal,
8. trusted membership review, including provider configuration, lookup failure behavior, and the decision not to cache memberships in SQLite for the initial deployment,
9. SQLite backup, restore, integrity-check, migration, and unsupported multi-host deployment procedures.

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
- **Access changes during long operations:** record the initiating principal and resource, allow already-running work to finish, and block all new work and later operation access after revocation.
- **Resource enumeration:** apply one documented `403`/`404` policy and filter list endpoints.
- **Authentication migration broadens access:** use stable principal IDs and require an explicit identity-mapping migration.
- **Development bypass reaches production:** reject unsafe development defaults in shared and production configuration.
- **Filesystem and authorization records diverge:** route project and shared-source lifecycle changes through one service, deny resources in a transitional state, and provide a reconciliation command that reports and repairs only with explicit operator approval.
- **SQLite is used beyond its deployment limits:** document single-host support, use WAL and short transactions, and replace only the repository implementation before adding multiple application hosts.
- **Name reuse inherits access:** assign generation-specific UUIDs and never attach grants to project names or filenames.
- **Last administrator or owner is removed:** reject mutations that would remove the final active assignment.
- **Membership provider is unavailable during review:** report the lookup status and error, keep the provider authoritative, and do not use review results for runtime authorization. Reconsider a review-only cache only if provider availability or review latency becomes an operational problem.

## Testing And Validation

- Unit-test every project, shared-source, and application role against every known action, including unknown-value denial.
- Test SQLite migrations, uniqueness, concurrent readers and writers, transaction rollback, backup and restore, lifecycle compensation, and stale-name reuse.
- Test principal validation, explicit development identity, bootstrap idempotence, and last-owner and last-admin protection.
- Test each registered route as unauthenticated, unauthorized, and allowed, with filtered lists and the defined `403`/concealed-`404` behavior.
- Test multi-resource operations with each required grant missing in turn.
- Test service entry points without route dependencies and operation access before and after revocation.
- Test typed principal, group, and authenticated-`everyone` grants, including anonymous denial, broad-role safeguards, membership review success and failure states, strict CLI behavior, JSON output, and membership lookup audit records.
- Compare the generated route inventory with registered FastAPI routes and fail on undeclared non-health routes.
- Run focused authorization tests, the complete backend suite, and deployment backup, restore, cutover, rollback, and database integrity checks.

## Acceptance Criteria

- [ ] One documented policy maps roles to actions for every protected resource group in Phase 1.
- [ ] Resource records, grants, application roles, schema versions, and audit events are stored in the configured SQLite database through an `AuthorizationRepository` contract.
- [ ] Project, shared-data-source, upload, output, backup, log, schema, query, task, operation, and ingester routes enforce the documented policy.
- [ ] Sensitive services and background operations cannot rely only on possession of a name, path, session ID, or operation ID.
- [ ] Project sessions require both session ownership and current project authorization.
- [ ] Project and shared-resource list endpoints omit unauthorized entries.
- [ ] Existing resources receive explicit reviewed grants before enforcement cutover.
- [ ] Cross-user, cross-project, cross-source, and role-matrix tests pass.
- [ ] The maintained authorization documentation and route inventory match implemented behavior.
- [ ] Replacing nginx authentication does not require changing authorization policy or stored grants.
- [ ] Deleting and recreating a project or shared-source name does not transfer grants from the deleted resource.
- [ ] Production startup rejects missing administrators, development-only identities, and an authorization database inside a user-editable directory.
- [ ] Operators can review group grants with effective principals without changing grants or runtime authorization decisions.

## Resolved Decisions

1. SQLite backs the first repository implementation and is supported only for a single application host.
2. The `project_creator` application role controls project creation; the creator becomes owner.
3. Project owners manage project grants subject to last-owner protection; administrators manage all grants and application roles.
4. Shared-source read, connection test, schema inspection, preview, and read-only query use one `reader` grant in Phase 1.
5. Resource-addressed denial returns concealed `404`; application-scoped denial returns `403`; lists are filtered.
6. Revocation blocks new work and later operation access but does not automatically cancel work already executing.
7. Grants use typed `principal`, `group`, and authenticated-`everyone` subjects. Group IDs are accepted only from an explicitly enabled trusted nginx group source; authenticated-`everyone` matching is disabled by default and requires explicit deployment configuration. Broad subjects cannot receive `owner`.
8. Project and shared-source names remain API locators, while generation-specific UUID resource records hold grants and prevent name-reuse inheritance.
9. Operator membership review uses a trusted provider resolver and does not materialize group memberships as individual grants.
10. Membership review queries the trusted provider directly in the initial deployment; SQLite does not cache membership snapshots. A future cache requires a separate decision and must be expiring, non-authoritative, and review-only.

## Recommendation

Treat this sub-proposal as the Phase 1 authorization design for the implemented work. The principal contract, SQLite repository, resource lifecycle records, centralized policy, typed broad-access subjects, trusted membership review, and focused tests are implemented. Complete route and deployment inventories, full regression validation, and cutover verification before enabling the remaining protected Phase 1 surface in production.
