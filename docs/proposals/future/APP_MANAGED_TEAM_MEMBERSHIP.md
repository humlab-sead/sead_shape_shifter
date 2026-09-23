# App-Managed Team Membership

## Status

- Draft proposal / not yet approved
- Scope: store principal-to-team membership in the authorization database and authorize against it in addition to trusted-proxy groups
- Goal: let an operator assign people to a team inside Shape Shifter when the deployment cannot supply verified group IDs
- Related: [AUTHORIZATION.md](../../AUTHORIZATION.md), [AUTHORIZATION_ROUTE_INVENTORY.md](../../AUTHORIZATION_ROUTE_INVENTORY.md), [Centralized Authorization System Cutover Plan](../CENTRALIZED_AUTHORIZATION_CUTOVER/CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md), [Authorization Schema Migration Registry](./AUTHORIZATION_SCHEMA_MIGRATION_REGISTRY.md), [Native Application Authentication](./NATIVE_APPLICATION_AUTHENTICATION.md)

## Summary

Add a `team` grant subject whose members are stored in the authorization database. Teams are matched alongside proxy-asserted `group` subjects, and grants keep their current shape, so the authorization decision path does not change.

Do this after the centralized authorization cutover completes. It is not a dependency of the cutover phases and should not be folded into them.

## Problem

A grant can target a group, but nothing in Shape Shifter can add or remove a group member. Membership lives entirely in the identity provider, and the request-time group list comes from a header the trusted proxy asserts.

Two consequences follow:

1. A deployment that authenticates with `auth_basic` and an htpasswd file supplies no group claim, so group grants cannot be used at all. The test deployment is in this state.
2. Where groups are available, every membership change is an identity-provider and nginx change, which is disproportionate for a project-level team.

Operators therefore fall back to one grant per person. That cannot express "this group of people works on these projects without an owner", it duplicates rows per project, and leaving the team means finding and revoking each grant.

## Scope

- Store teams and their members in the authorization SQLite database.
- Add a `team` subject kind that is distinct from the proxy-verified `group` subject.
- Resolve team membership once per request and pass it to the existing grant match.
- Provide `sead-authorization` commands to create, rename, retire, and populate teams.
- Report team membership in `list-grants --effective` with its source.
- Record team and membership changes in the audit log.
- Add a deployment setting that keeps the feature off until it is enabled.
- Extend the authorization schema to the next version through the planned migration registry.

## Non-Goals

- Replacing nginx as the authentication boundary. Identity still arrives through the trusted-proxy header.
- Removing or changing the trusted group header path.
- Managing principal accounts, credentials, or first-login verification.
- Changing resource, grant, role, or inheritance semantics.
- Adding a team administration API or user interface in the first delivery. Each new route needs authorization metadata, an inventory row, and tests, so the interface starts at the command line.
- Migrating identity-provider groups into teams automatically.
- Allowing a team to hold `owner` or a deployment role.

## Current Behavior

- `grant_record` is keyed by `(subject_type, subject_id, resource_id, role)` and `subject_type` is one of `principal`, `group`, or `everyone`.
- Group grants match only against `principal.group_ids`, which is filled in one place: `AuthenticationAdapter.principal_from_request` reads `request.state.authenticated_groups`, which `ProxyAuthenticationMiddleware` sets from the configured header and only when `TRUSTED_PROXY_GROUPS_ENABLED` is enabled. The setting defaults to false.
- `AuthorizationService.is_allowed` passes `principal.group_ids` to `repository.list_matching_grants`, then checks the resource, its ancestors, and the role-to-action table. The decision logic needs no change if a group ID list is supplied.
- `repository.add_grant` rejects `owner` for any non-principal subject.
- Membership review uses `HttpGroupMembershipResolver` through `sead-authorization list-grants --effective`, records `membership_lookup` audit events, and never affects a runtime decision.
- `CURRENT_SCHEMA_VERSION` is 4 and `MINIMUM_SUPPORTED_SCHEMA_VERSION` equals it, so repository initialization accepts only a current database and instructs operators to create a new one for anything older.
- Every protected route must carry `authorization_requirement` metadata and be listed in [AUTHORIZATION_ROUTE_INVENTORY.md](../../AUTHORIZATION_ROUTE_INVENTORY.md); `backend/tests/authorization/test_route_authentication.py::test_route_inventory_matches_assembled_api_routes` compares the documented list with the assembled application.

## Proposed Design

### Distinct subject kinds

Keep `group` as the subject for identifiers verified by the trusted proxy, and add `team` for membership maintained in Shape Shifter. A team grant is satisfied only by stored membership; a group grant is satisfied only by the header the proxy asserts. The two never substitute for each other, so no precedence rule is needed and neither source can silently widen the other.

### Data model

Add the next schema version with two tables:

- `team(team_id TEXT PRIMARY KEY, name TEXT NOT NULL, lifecycle_state TEXT NOT NULL, created_at TEXT NOT NULL, created_by TEXT NOT NULL)` with a unique index on `name` where `lifecycle_state = 'active'`.
- `team_member(team_id TEXT NOT NULL REFERENCES team(team_id), principal_id TEXT NOT NULL, created_at TEXT NOT NULL, created_by TEXT NOT NULL, PRIMARY KEY(team_id, principal_id))`.

`grant_record.subject_id` holds `team_id`, so existing grant columns and the primary key are unchanged. The team name is a locator, mirroring how `resource` separates `resource_id` from `locator`. Renaming a team therefore changes only `team.name`, and grants keep working. Retiring a team must not leave grants that point at a subject which can no longer match.

### Request-time resolution

After the adapter builds the principal from the trusted identity header, resolve the principal's team IDs with one indexed query and carry them on the principal. The service matches grants against the principal plus the stored team IDs and the proxy-asserted group IDs. Resolution is additive: a principal with no teams behaves exactly as it does today. App-managed teams are read only when the deployment setting is enabled, so a disabled deployment matches no team grant.

### Policy

A team may hold the same resource roles as a group: `viewer`, `editor`, and `executor`. It may not hold `owner`, which the repository already enforces for non-principal subjects. Deployment roles stay principal-only, so team membership can never widen deployment-wide authority.

### Administration

Start with `sead-authorization` commands for team creation, rename, retirement, member addition and removal, and for listing teams and their members. Every mutation requires an actor and writes an audit event with `subject_type` `team`, the subject ID, and the member principal ID in the details field.

Administrator authority stays principal-based. A team is never the source of administrative rights, so a membership edit cannot lock out administration.

### Review

Extend `list-grants --effective` to resolve team subjects from the local store and report the source of each resolution, keeping the existing output shape for provider lookups. Proxy group membership continues to be reported through the configured membership provider. Both sources are shown; neither is preferred silently.

## Alternatives Considered

### Reuse `group` for app-managed membership

Rejected. It conflates an identifier verified by the proxy with one maintained by the application. A header value would then satisfy a grant whose membership the application believes it controls, and review output could not distinguish a verified claim from a stored row.

### Expand a team into per-principal grants at assignment time

Rejected as the primary design. Leaving a team would require finding and revoking each per-principal grant, and the assignment would be duplicated across every project. This remains a viable lower-cost interim step when no membership storage is wanted.

### Resolve membership from the identity provider on every request

Rejected. It adds a network dependency and a failure mode to each request. The current design deliberately keeps review lookups out of the decision path.

### Keep membership only in the identity provider

Rejected as the only option. It excludes deployments that authenticate without group claims and makes routine team changes an infrastructure task.

## Risks And Tradeoffs

- **Two membership sources.** Operators must know which subject kind a grant uses. Mitigation: distinct subject kind and review output that names the source.
- **Schema change.** `MINIMUM_SUPPORTED_SCHEMA_VERSION` currently equals the current version, so this change must lower the supported baseline and ship a real migration, or existing databases are refused. Sequence it with the [schema migration registry](./AUTHORIZATION_SCHEMA_MIGRATION_REGISTRY.md) work and prove the upgrade keeps existing records.
- **New authority inside the application.** A mistaken or compromised administrator can add members to a team that already holds grants. Mitigation: every change is audited, team management requires `admin`, and `owner` and deployment roles stay principal-only.
- **Unverified member identifiers.** No principal registry exists, so a member row is an unvalidated string, exactly like a grant subject today. A typo creates a member who never matches. Mitigation: review commands list members, and the limitation is recorded rather than hidden.
- **Drift between provider groups and teams.** The same people may reach the same access through two paths. Mitigation: prefer one kind per access pattern and record the choice in the deployment inventory.
- **Review trust.** Stored membership is asserted by the application rather than verified by the proxy, which is weaker evidence. Reporting the source per row keeps that visible.
- **Route surface.** A future API for team administration adds routes that need authorization metadata, inventory rows, and tests. Command-line administration avoids that cost initially.

## Testing And Validation

- Repository: the upgrade from the current version keeps resources, grants, deployment roles, and audit events; new tables, keys, and the unique active-name index behave as specified.
- Service: a team grant allows the action for a stored member; a non-member is denied; an inactive resource is denied; `owner` for a team is rejected; a disabled setting denies all team grants.
- Adapter and dependencies: the principal carries stored team IDs; existing route requirement metadata is unchanged.
- Isolation: a header-asserted group ID does not satisfy a team grant, and stored membership does not satisfy a group grant.
- Command line: create, rename, retire, add, and remove write audit events with an actor; `--effective` reports both sources with status.
- Regression: the full authorization suite and the route inventory check pass; a fresh database reports the new version.
- Deployment: enable the feature in the test deployment and confirm access for a member and denial for a non-member before any migrated project depends on a team grant.

## Acceptance Criteria

- `P-AC-1` A team can be created, renamed, retired, and have members added and removed through `sead-authorization`, with the acting principal recorded for every change.
- `P-AC-2` A grant that targets a team allows the action for a stored member and denies it for a principal who is not a member.
- `P-AC-3` A team subject cannot receive `owner`, and no deployment role can be assigned to a team.
- `P-AC-4` A proxy-asserted group ID never satisfies a team grant, and stored team membership never satisfies a group grant.
- `P-AC-5` A database at the current version upgrades without losing resources, grants, deployment roles, or audit events, while a database below the supported baseline still fails with an actionable error.
- `P-AC-6` `list-grants --effective` reports team membership with its source and status, and the review never changes a runtime decision.
- `P-AC-7` When app-managed teams are disabled, team grants permit no access.
- `P-AC-8` A retired or deleted team leaves no grant that can match a live subject.
- `P-AC-9` The full authorization test suite and the route inventory check pass.

## Planning Handoff

Confirmed decisions that constrain implementation:

- The authorization decision path does not change; only the set of subject IDs available to the grant match grows.
- `team` is a separate subject kind from `group`; `grant_record.subject_id` holds the team ID, not the name.
- Administration is command-line first; an API and user interface are later work with their own route inventory rows.
- The feature is disabled by default and is delivered after the cutover, not inside it.

Rules to preserve: deny-by-default, `owner` restricted to principals, no credentials or secrets in audit records, review lookups separate from runtime decisions, and existing grant, resource, and role behavior unchanged.

Expected validation outcomes: the upgraded database keeps its records, member access is allowed, non-member access is denied, the two subject kinds cannot substitute for each other, and the disabled setting denies everything.

Open questions and the phase that must resolve each:

1. Whether `operator` may manage teams or only `admin` may, before the administration phase.
2. Whether retirement revokes a team's grants in the same transaction or keeps them for audit, before the storage phase.
3. Whether the test deployment adopts teams in place of identity-provider groups, before the deployment phase.
4. Whether member rows should record verification after a principal first authenticates, before the review phase.

## Recommended Delivery Order

1. Schema version with the two tables, following the migration registry approach.
2. Request-time team resolution and policy enforcement, including the non-principal `owner` restriction.
3. Command-line administration with audit events.
4. Review output for both membership sources.
5. Documentation updates in `AUTHORIZATION.md` and `OPERATIONS.md`.
6. Optional administration API and user interface, with inventory rows and tests.

## Final Recommendation

Adopt app-managed teams as a subject kind separate from proxy-verified groups, delivered after the cutover, administered from the command line, and disabled until a deployment enables it. Do not reuse `group`, and do not fold the change into the current cutover phases. If only the authoring effort needs reducing now, expand team membership into per-principal grants as an interim step and defer this proposal.
