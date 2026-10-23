# Authorization

## Purpose

Shape Shifter uses a centralized authorization system to decide whether an authenticated principal may perform an action on a protected resource. Resource records, grants, deployment roles, and authorization audit events are stored outside project-managed data in the configured SQLite authorization database.

This document describes the implemented policy. Route-by-route coverage and the remaining enforcement work are tracked in [AUTHORIZATION_ROUTE_INVENTORY.md](AUTHORIZATION_ROUTE_INVENTORY.md) and sequenced by the [cutover plan](proposals/done/CENTRALIZED_AUTHORIZATION_CUTOVER/CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md).

The current route declarations are listed in [AUTHORIZATION_ROUTE_INVENTORY.md](AUTHORIZATION_ROUTE_INVENTORY.md), which records a requirement for every route. The generic ingester validation and execution rows record `application:run_ingesters`; the saved-project Change Request routes record `project:execute`.

The relationships between subjects, grants, resources, roles, and actions are shown in the [authorization diagrams](DIAGRAMS.md#authorization-model). The `sead-authorization list-resources`, `list-grants`, and `list-application-roles` commands print the relationships recorded in a deployment's authorization database.

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

A grant assigns a resource role to one typed subject and one resource UUID. Subjects are `principal`, `group`, or authenticated `everyone`. Project names and shared data-source filenames are locators, not authorization identities. Deleting a resource and reusing its locator creates a new UUID, so it cannot inherit old grants. A move is not a delete and recreate: `sead-authorization move-resource` changes the locator of an existing resource and keeps its UUID, so its grants continue to apply. See [Moving a resource locator](#moving-a-resource-locator).

Direct-principal grants use `principal_id` in legacy manifests or `subject_type: principal` and `subject_id` in typed manifests. Group grants use verified group IDs supplied by the trusted authentication provider. In Phase 1, nginx supplies them through the configured trusted group header, and group matching is disabled unless that source is explicitly enabled. A site that authenticates with `auth_basic` has no group claim of its own, so the header comes from a membership file; see [NGINX group header](OPERATIONS.md#nginx-group-header). Membership is never inferred from client request fields. `everyone` means every authenticated principal and uses the fixed subject ID `authenticated`; anonymous requests are still denied. Authenticated-`everyone` matching is disabled unless explicitly enabled in deployment configuration.

Resource access is denied unless the resource is active and a policy rule permits the action. A grant on a parent resource applies to its children. For example, a project grant can authorize work on a project child resource. Child grants do not grant access to a parent.

## Moving A Resource Locator

A project locator is derived from its folder path, so moving or renaming a project folder changes its locator. Moving only the folder leaves the old locator active and the grants attached to it, and the new locator resolves to nothing, so only an `admin` can reach the project. Move the authorization resource with the folder.

The supported command is `sead-authorization move-resource`:

```bash
sead-authorization move-resource \
  --resource-type project \
  --from-locator old-name \
  --to-locator arbodat:new-name \
  --actor operator
```

The command requires a free target locator, refuses a source that is not active, and refuses identical locators. It keeps the resource UUID and its grants, and it records a `resource_locator_changed` audit event containing the previous and new locators. Add `--dry-run` to check the move without changing storage.

In a container deployment, `deployment/container/scripts/project.sh move` moves the project folder and updates the locator in one step, rolling the folder back if the authorization change fails:

```bash
deployment/container/scripts/project.sh move --project old-name --to arbodat/new-name
```

Both values accept `/` and `:`. The script requires a running container, because `authorization.sh` runs the command inside it. If the moved project was the active editing project, restart the container after the move so in-memory state does not keep the old locator.

An operator who already moved the folder by hand can call `move-resource` on its own.

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

## Deployment Roles

Deployment roles apply across the deployment and are evaluated before resource grants. A deployment role is not attached to a resource and does not inherit from a parent resource.

| Role                 | Allowed actions                                                     |
|----------------------|---------------------------------------------------------------------|
| `project_creator`    | `create_project`                                                    |
| `operator`           | `read_all_shared_sources`, `manage_shared_sources`, `run_ingesters` |
| `project_maintainer` | `read`, `edit`, `execute`                                           |
| `admin`              | Every defined action                                                |

A principal that should maintain any project without holding a grant for it receives `project_maintainer`. It permits `read`, `edit`, and `execute` on every project and project child resource, so it also covers projects created later without new grants. It does not permit `delete`, `manage_grants`, `manage_all_grants`, `manage_application_roles`, `manage_shared_sources`, `configure_ingesters`, or `read_logs`; use `admin` for those.

The current actions are `read`, `edit`, `execute`, `delete`, `manage_grants`, `create_project`, `read_logs`, `manage_shared_sources`, `read_all_shared_sources`, `run_ingesters`, `manage_all_grants`, `manage_application_roles`, and `configure_ingesters`.

Application and error logs are global, and no project-scoped log exists, so both log routes require an authenticated principal and no deployment role. This policy change was approved on 2026-09-16 and replaces the earlier admin-only rule. The `read_logs` action remains defined, and no route requires it.

Deployment roles do not create resource grants. They permit only their explicitly mapped actions. `admin` permits all defined actions, including resource actions. Unknown resource types, roles, and actions are denied.

The stored `application_role` table, the `application_role_created` and `application_role_revoked` audit event types, and the `sead-authorization` command names keep the earlier `application role` wording. Calling these roles deployment roles does not change stored data.

## Authorization Decisions

`AuthorizationService` evaluates a principal, action, and server-owned resource record. On success, it returns an authorized resource containing the principal, action, and resource record. Endpoint and service code must use that returned record rather than a client-supplied locator or path.

FastAPI dependencies enforce common checks before protected endpoint code runs:

- `require_project()` resolves and authorizes a project.
- `require_shared_data_source()` resolves and authorizes a shared data source.
- `require_application_action()` authorizes a deployment role.
- `require_authorized_session()` requires both session ownership and current project authorization.
- `require_operation()` requires operation ownership and current authorization for its recorded project.

A principal needs access to both a project and a shared source when an operation uses a shared source referenced by that project. Project access does not grant shared-source access.

## Denial Behavior

- Missing proxy authentication returns `401 Authentication required`; malformed proxy identities return `401 Invalid authenticated identity`.
- Missing deployment-role permissions return `403 Insufficient authorization`.
- Missing or unauthorized resource-addressed project and shared-data-source requests return `404 Resource not found` to conceal resource existence. Session and operation dependencies also conceal unavailable or unauthorized records with `404`. The active-project dependency conceals an active project the principal cannot read, and reports a deployment with no active project as `null`.
- List endpoints return only resources readable by the requesting principal.

## Audit Records

The authorization database records grant creation and revocation, deployment-role creation and revocation, resource lifecycle changes, bootstrap administrator creation, and membership review lookups. Each record contains an event ID, timestamp, actor principal ID, event type, optional resource UUID, action, outcome, optional correlation ID, optional typed subject (`subject_type` and `subject_id`), and optional provider/details fields. Broad grants and membership review results are therefore identifiable in the audit log.

Audit records must not contain credentials, SQL text, sensitive filesystem paths, or secret configuration. They are written through the authorization repository with the associated mutation. Operators can review them with `sead-authorization list-audit-events`, using `--json` for automation; do not query or alter the database directly.

## Snapshots And Restores

`sead-authorization export-state` writes the complete stored state to JSON or YAML, and `import-state` replaces the stored records with a snapshot. The file extension selects the format. A snapshot holds every record needed to recreate the database:

| Section | Contents |
|---------|----------|
| `schema_version` | Database schema version the snapshot was written from |
| `resources` | Every resource generation, including inactive ones |
| `grants` | Every typed grant, with `created_at` and `created_by` |
| `application_roles` | Every deployment role, not only `admin` |
| `audit_events` | Audit history, only when `--include-audit` is given |

Resource UUIDs are recorded, so grants keep pointing at the same resources after a restore. Records are sorted and timestamps are written as ISO strings, so a committed snapshot changes only when a stored record changes.

Audit events are excluded by default because they change on every authorization operation and would dominate a version-control diff. A restore from a snapshot without them keeps the existing audit history; a snapshot with them replaces it.

`export-manifest` remains the reviewed-policy format and is not interchangeable with a snapshot: it holds only administrators, active top-level resources, and their grants, and it uses locators instead of UUIDs. Use `export-state` for a backup or a version-controlled record of the deployed state, and `export-manifest` for the policy review that `migrate --manifest` applies.

`import-state` validates the whole snapshot before writing: the schema version must not be newer than the application, resource IDs and active locators must be unique, every grant and parent reference must resolve, and the owner role stays restricted to a principal. It also refuses a snapshot that would leave the deployment without an administrator, or an active project without an owner; see [Editing A Snapshot By Hand](#editing-a-snapshot-by-hand). The replacement runs in one transaction, so a rejected or failed restore leaves the previous records in place. The restore records one `state_restored` audit event with the actor and record counts.

A restore replaces records, so it is not a routine fix for a single wrong grant. Use `grant`, `revoke`, `grant-application-role`, and `revoke-application-role` for individual changes.

### Editing A Snapshot By Hand

An exported snapshot can be edited and imported to change many records at once. Use this for a batch change across many principals or projects, for a change that should be reviewed as a file in version control, or to revert an earlier bulk change. Use the individual commands for one or two records.

An import is refused when the snapshot would leave the deployment without an administrator, or an active project without an owner. That is the same guarantee `revoke` and `revoke-application-role` give for a single change. `--allow-no-admin` and `--allow-unowned-project` accept the condition on purpose, so a deliberate change is possible but a mistake is not silent.

`import-state --dry-run` prints the record-level difference between the snapshot and the stored records rather than only counts. Each line names the record that would be added, removed, or changed:

```text
Dry run: 3 record change(s) in after.yaml:
  - grant            group:editors viewer on project:project-a
  - grant            principal:alice owner on project:project-a
  + grant            principal:alice editor on project:project-a
```

Only access-relevant changes appear. For a grant that means the subject, the resource, and the role, so a changed `created_by` or `created_at` on an otherwise identical grant is not listed. The dry run also reports the administrators and the active projects that would have no owner after the import, and exits non-zero when either condition would occur without the matching opt-in flag.

Two consequences remain for a restore, whichever way it is applied.

- A restore records one `state_restored` event with record counts. It does not record which grant or role changed, so the audit trail shows that a restore happened but not what it altered. The `--dry-run` output is the only record of what changed, so keep it with the change.
- A restore replaces every stored record. A project created between the export and the import loses its authorization record: the project folder stays on disk, its locator resolves to no resource, and only an administrator can reach it. Export immediately before importing.

To change roles and grants by hand, follow these steps. In a deployed environment, run each command as the deployment user through `~/container/scripts/authorization.sh`, for example `./scripts/authorization.sh export-state after.yaml`. The wrapper runs the command inside the container and copies the file across the container boundary. `sead-authorization` is the command name inside the container.

1. Export the current state as the file to return to, and take a binary backup as well.

   ```bash
   sead-authorization export-state before.yaml
   sead-authorization backup before-restore.sqlite3
   ```

   Through the wrapper, `./scripts/authorization.sh backup` takes no destination: it writes a timestamped file to the persistent `backups/` directory.

2. Export the state you will edit and compare the two files, so the intent of each change is written down.

   ```bash
   sead-authorization export-state after.yaml
   diff -u before.yaml after.yaml
   ```

3. Edit `after.yaml`, then review the difference.

   ```bash
   diff -u before.yaml after.yaml
   ```

4. Validate the snapshot without writing it. The command prints each record it would add, remove, or change, and rejects an invalid schema version, duplicate IDs, an unresolved reference, an invalid role for a resource type, or an owner role on a group or `everyone` subject. Role errors name the grant and list the roles allowed for that resource type. It exits non-zero when the snapshot would leave no administrator or an active project without an owner.

   ```bash
   sead-authorization import-state after.yaml --dry-run --actor you@example.org
   ```

5. Confirm the dry run lists the changes you intended, and nothing else. If it reports an administrator or an owned project you did not mean to remove, edit the snapshot rather than reaching for the opt-in flag.

6. Import the snapshot. The command prints the record counts it will write and asks for confirmation before replacing anything; `--yes` skips the prompt.

   ```bash
   sead-authorization import-state after.yaml --actor you@example.org
   ```

7. Export the stored state again and confirm it holds the same records. Export sorts grants by resource, subject type, subject, and role, so a record added at the end of the file returns in its sorted position. Compare the lines rather than the order.

   ```bash
   sead-authorization export-state verify.yaml
   diff -u <(sort after.yaml) <(sort verify.yaml)
   ```

Keep `before.yaml` until the change is verified. Importing it restores the earlier records.

A hand-added grant needs `subject_type`, `subject_id`, `resource_id`, `role`, `created_at`, and `created_by`.

| Field | Rule |
|-------|------|
| `subject_type` | `principal`, `group`, or `everyone` |
| `subject_id` | Principal ID or group ID; `authenticated` for `everyone` |
| `resource_id` | UUID of a resource in the same snapshot |
| `role` | Must exactly match a role allowed for the resource type: `viewer`, `editor`, `executor`, or `owner` for project resources; `reader` for shared data sources. Invalid roles are rejected before any records are written. |
| `created_at` | ISO 8601 timestamp, for example `2026-10-20T09:00:00+00:00` |
| `created_by` | Non-empty principal ID recorded as the creator |

The `owner` role is rejected on a `group` or `everyone` subject, so every project keeps a named principal owner. Granting access to a project that is not yet in the snapshot requires adding its resource first, with a new UUID and `lifecycle_state: active`; see [Moving A Resource Locator](#moving-a-resource-locator) for the case where a project moved rather than was created.

## Current Coverage

Implemented controls cover project resources and project children, shared data-source access, project references to shared sources, and authenticated access to the global application and error logs. The policy is intentionally deny-by-default.

Ingester authorization for the generic file routes enforces `application:run_ingesters`, and the saved-project Change Request routes enforce `project:execute` without a deployment role. The [Security Hardening Follow-up](proposals/SECURITY_HARDENING_FOLLOWUP/SECURITY_HARDENING_FOLLOWUP.md) requires resource authorization and containment before enabling a future generic-route ingester. Every route records a requirement and no row reads `UNDECLARED`. [AUTHORIZATION_ROUTE_INVENTORY.md](AUTHORIZATION_ROUTE_INVENTORY.md) holds the classification together with its dated review, which Phase 1 of the [cutover plan](proposals/done/CENTRALIZED_AUTHORIZATION_CUTOVER/CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md) produced.
