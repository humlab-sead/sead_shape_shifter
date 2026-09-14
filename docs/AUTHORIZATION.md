# Authorization

## Purpose

Shape Shifter uses a centralized authorization system to decide whether an authenticated principal may perform an action on a protected resource. Resource records, grants, application roles, and authorization audit events are stored outside project-managed data in the configured SQLite authorization database.

This document describes the implemented policy. Route-by-route coverage and remaining enforcement work are tracked in [CENTRALIZED_AUTHORIZATION_SYSTEM_TASK_PLAN.md](proposals/MITIGATE_SECURITY_ISSUES/done/CENTRALIZED_AUTHORIZATION_SYSTEM_TASK_PLAN.md).

The current route declarations are listed in [AUTHORIZATION_ROUTE_INVENTORY.md](AUTHORIZATION_ROUTE_INVENTORY.md). Routes marked `UNDECLARED` need classification before authorization cutover.

For the authorization SQLite database location and deployment configuration, see [OPERATIONS.md](OPERATIONS.md#authorization-sqlite-store).

## Principals

A principal has these fields:

```text
principal_id
authentication_provider
authenticated_at
```

In the current deployment model, nginx supplies a verified identity header and FastAPI validates it before placing the trimmed value in `request.state.authenticated_user`. The header must be non-empty, contain no control characters, and contain at most 255 characters. The resulting value is used as the case-sensitive `principal_id` for grant lookup. The authentication provider and authentication time provide request context; they do not affect grants.

When trusted-proxy authentication is disabled, only `development` and `test` environments may use `DEVELOPMENT_PRINCIPAL_ID`. Requests without a valid principal receive `401 Authentication required`.

A future authentication provider must preserve existing `principal_id` values or provide a reviewed migration for stored grants. See [NATIVE_APPLICATION_AUTHENTICATION.md](proposals/future/NATIVE_APPLICATION_AUTHENTICATION.md) for the deferred authentication work and the contracts it must preserve.

## Resources And Grants

Each protected resource has a server-owned UUID, resource type, current locator, lifecycle state, and optional parent resource ID. Current resource types are:

| Resource type              | Purpose                                                        |
|----------------------------|----------------------------------------------------------------|
| `project`                  | A project addressed by its current project-name locator        |
| `shared_data_source`       | A shared data source addressed by its current filename locator |
| `project_child`            | A project-owned child resource                                 |
| `shared_data_source_child` | A shared-data-source-owned child resource                      |

A grant assigns a resource role to one typed subject and one resource UUID. Subjects are `principal`, `group`, or authenticated `everyone`. Project names and shared data-source filenames are locators, not authorization identities. Deleting a resource and reusing its locator creates a new UUID, so it cannot inherit old grants.

Direct-principal grants use `principal_id` in legacy manifests or `subject_type: principal` and `subject_id` in typed manifests. Group grants use verified group IDs supplied by the trusted authentication provider. In Phase 1, nginx supplies them through the configured trusted group header, and group matching is disabled unless that source is explicitly enabled. Membership is never inferred from client request fields. `everyone` means every authenticated principal and uses the fixed subject ID `authenticated`; anonymous requests are still denied. Authenticated-`everyone` matching is disabled unless explicitly enabled in deployment configuration.

Resource access is denied unless the resource is active and a policy rule permits the action. A grant on a parent resource applies to its children. For example, a project grant can authorize work on a project child resource. Child grants do not grant access to a parent.

## Resource Roles

| Resource type                                    | Role       | Allowed actions                                      |
|--------------------------------------------------|------------|------------------------------------------------------|
| `project`, `project_child`                       | `viewer`   | `read`                                               |
| `project`, `project_child`                       | `editor`   | `read`, `edit`                                       |
| `project`, `project_child`                       | `executor` | `read`, `execute`                                    |
| `project`, `project_child`                       | `owner`    | `read`, `edit`, `execute`, `delete`, `manage_grants` |
| `shared_data_source`, `shared_data_source_child` | `reader`   | `read`                                               |

Roles are additive. A principal who needs project editing and execution without ownership receives both `editor` and `executor`.

Broad subjects may receive `viewer`, `editor`, or `executor` as approved by operators. They may not receive `owner`: ownership includes deletion and grant management, and a broad owner grant would defeat final-owner protection. Group and everyone grants are evaluated centrally together with direct grants and inherited parent-resource grants. The supported review command is `sead-authorization list-grants`; use `--effective --actor <principal>` to expand group subjects through the configured trusted membership provider. Review results include provider, timestamp, and resolution status. Review failures do not change runtime authorization decisions.

Runtime group matching and operator membership review use separate interfaces. nginx may provide verified group IDs for the current request, but it cannot enumerate all members of a group. Effective review requires a trusted membership lookup URL containing `{group_id}`. The identity provider remains authoritative; SQLite stores grants and review audit events, not group membership. This phase queries the provider directly and does not cache membership snapshots.

## Application Roles

Application roles apply across the deployment and are evaluated before resource grants.

| Role              | Allowed actions                                                     |
|-------------------|---------------------------------------------------------------------|
| `project_creator` | `create_project`                                                    |
| `operator`        | `read_all_shared_sources`, `manage_shared_sources`, `run_ingesters` |
| `admin`           | Every defined application action                                    |

The current actions are `read`, `edit`, `execute`, `delete`, `manage_grants`, `create_project`, `read_logs`, `manage_shared_sources`, `read_all_shared_sources`, `run_ingesters`, `manage_all_grants`, `manage_application_roles`, and `configure_ingesters`.

Application roles do not create resource grants. They permit only their explicitly mapped actions. `admin` permits all defined actions, including resource actions. Unknown resource types, roles, and actions are denied.

## Authorization Decisions

`AuthorizationService` evaluates a principal, action, and server-owned resource record. On success, it returns an authorized resource containing the principal, action, and resource record. Endpoint and service code must use that returned record rather than a client-supplied locator or path.

FastAPI dependencies enforce common checks before protected endpoint code runs:

- `require_project()` resolves and authorizes a project.
- `require_shared_data_source()` resolves and authorizes a shared data source.
- `require_application_action()` authorizes an application role.
- `require_authorized_session()` requires both session ownership and current project authorization.
- `require_operation()` requires operation ownership and current authorization for its recorded project.

A principal needs access to both a project and a shared source when an operation uses a shared source referenced by that project. Project access does not grant shared-source access.

## Denial Behavior

- Missing proxy authentication returns `401 Authentication required`; malformed proxy identities return `401 Invalid authenticated identity`.
- Missing application permissions return `403 Insufficient authorization`.
- Missing or unauthorized resource-addressed project and shared-data-source requests return `404 Resource not found` to conceal resource existence. Session and operation dependencies also conceal unavailable or unauthorized records with `404`.
- List endpoints return only resources readable by the requesting principal.

## Audit Records

The authorization database records grant creation and revocation, application-role creation and revocation, resource lifecycle changes, bootstrap administrator creation, and membership review lookups. Each record contains an event ID, timestamp, actor principal ID, event type, optional resource UUID, action, outcome, optional correlation ID, optional typed subject (`subject_type` and `subject_id`), and optional provider/details fields. Broad grants and membership review results are therefore identifiable in the audit log.

Audit records must not contain credentials, SQL text, sensitive filesystem paths, or secret configuration. They are written through the authorization repository with the associated mutation. Operators can review them with `sead-authorization list-audit-events`, using `--json` for automation; do not query or alter the database directly.

## Current Coverage

Implemented controls cover project resources and project children, shared data-source access, project references to shared sources, and application-log access. The policy is intentionally deny-by-default.

Ingester authorization remains proposed work and is tracked in [INGESTER_AUTHORIZATION_TASKS.md](proposals/CHANGE_REQUEST_INGESTER/INGESTER_AUTHORIZATION_TASKS.md). The route inventory, administration CLI, and core operational procedures are published, but undeclared route classification remains tracked in the centralized authorization task plan.
