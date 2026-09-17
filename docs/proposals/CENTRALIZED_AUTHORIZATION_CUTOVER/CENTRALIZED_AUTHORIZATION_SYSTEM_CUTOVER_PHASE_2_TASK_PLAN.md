# Phase 2 Task Plan: Review Deployment Resources And Initial Grants

## Phase Summary

- **Source decision document:** [Centralized Authorization System](../done/MITIGATE_SECURITY_ISSUES/done/CENTRALIZED_AUTHORIZATION_SYSTEM.md)
- **Source phase plan:** [Centralized Authorization System Cutover Plan](./CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md) — [Phase 2: Review Deployment Resources And Initial Grants](./CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md#phase-2-review-deployment-resources-and-initial-grants)
- **Goal:** Produce the deployment's authorization inputs — a reviewed resource list, confirmed principal IDs, and an initial administrator-and-grant manifest — without modifying project YAML.
- **Readiness:** Blocked — the phase plan requires named deployment identities and resource owners, and none are recorded in the repository.
- **Dependencies:** Phase 1 complete (route and operation inventory). The phase plan records `Depends On: The Phase 1 inventory`.
- **Constraints:** Do not modify project YAML or other user-editable project data. Do not infer principal ownership from filenames, project metadata, or request data. Keep the authorization policy unchanged. Do not apply or reconcile the manifest in this phase; application and reconciliation belong to Phase 3.

**Blocking decisions** — each must be answered by the deployment owner before any task below can produce a reviewed record. They are open in [DEPLOYMENT_VERIFICATION_HANDOFF.md](./DEPLOYMENT_VERIFICATION_HANDOFF.md):

1. **Deployment host and environment** (shared, staging, or production). It selects which `PROJECTS_DIR` and shared-data directory the inventory covers.
2. **Principal ID values.** The case-sensitive identity values nginx supplies in `X-Authenticated-User` (the configured `TRUSTED_PROXY_AUTH_HEADER`) for every administrator, project owner, and reader. None are recorded in the repository.
3. **Resource owner and reader assignments.** Who owns or reads each deployed project and shared data source, supplied by the deployment owner, never derived from filenames or metadata.

Until all three are supplied, the phase is Blocked and must not be executed against a guessed input set.

**Acceptance Criteria**

1. `PH2-AC-1` (from `P-AC-2`) The reviewed manifest includes every required administrator, project, shared data source, and initial grant.
2. `PH2-AC-2` (from `P-AC-2`) Required resources have one or more reviewed owners or readers before migration.
3. `PH2-AC-3` (from `P-AC-3`) Principal IDs are confirmed against deployment identity values, with corrections recorded before application.
4. `PH2-AC-4` (from `P-AC-2`) Project YAML and other user-editable project data are unchanged by the migration-input process.

## Repository Findings

**Repository basis:** branch `authorization-system-cutover`, planning date 2026-09-17, Phase 1 complete. No deployment identity or resource-owner facts exist in the repository; the findings below record only what the repository implements, not deployment values.

| Evidence | Finding | Planning implication |
| --- | --- | --- |
| `backend/app/authorization/operations.py::inspect_manifest`, `apply_manifest`, `reconcile_manifest`, `_load_validated_manifest` | The manifest is `{administrators: [str], resources: [{resource_type, locator, grants: [...]}]}`. Grants accept a legacy `principal_id` or a typed `subject_type` plus `subject_id`; `everyone` requires `subject_id: "authenticated"` and is rejected unless `AUTHORIZATION_ALLOW_AUTHENTICATED_EVERYONE` is enabled | The manifest must match this schema; `migrate --dry-run` validates it without writing |
| `backend/app/scripts/authorization.py` (`sead-authorization`) | Commands include `migrate [--manifest --dry-run]`, `reconcile <manifest>`, `list-resources [--json]`, `list-grants [--effective --actor]`, `list-application-roles [--json]`, `grant-application-role`, `backup`, `restore`, `integrity-check` | Phase 2 uses `migrate --dry-run` and the `list-*` commands only; applying and reconciling are Phase 3 work |
| `backend/app/authorization/models.py` | `ResourceType`: `project`, `shared_data_source`, `project_child`, `shared_data_source_child`. `ApplicationRole`: `project_creator`, `operator`, `admin` | The manifest covers top-level `project` and `shared_data_source` records; child resources derive at runtime from their parents |
| `docs/AUTHORIZATION.md` (Principals; Resource Roles) | `principal_id` is the trimmed, case-sensitive value of the trusted-proxy identity header. Project roles are `viewer`, `editor`, `executor`, `owner`; the shared-source role is `reader`; broad subjects must not receive `owner` | Identity confirmation compares against the header values nginx actually supplies; direct-principal `owner` grants only |
| `backend/app/core/config.py` | `AUTHORIZATION_DATABASE_PATH` (default `state/authorization.sqlite3`), `AUTHORIZATION_BOOTSTRAP_ADMIN_PRINCIPALS`, `PROJECTS_DIR`, and the shared-data directory resolve the inventory sources | The inventory reads these configured directories on the selected host; bootstrap admins are compared, not invented |
| `backend/app/mappers/project_name_mapper.py::to_api_name`, `backend/app/authorization/dependencies.py::_data_source_locator` | A project locator is the API name derived from the project directory; a shared-data-source locator is the filename stem | The resource list uses these exact locator forms so `require_project` and `require_shared_data_source` lookups match later |
| `DEPLOYMENT_VERIFICATION_HANDOFF.md` (Open Decisions) | Host and environment, rollback owner, the `sead_ro` account, and the exception approver are unresolved; no principal IDs or owners are recorded | Phase 2 is blocked until the host and the identity and owner inputs are named |

## Scope

**In scope**

- The deployment resource list: every deployed project and shared data source, its locator, and its expected lifecycle state.
- The duplicate-or-conflicting-locator check within each resource type, compared against existing authorization records.
- The principal-ID record: administrator, owner, and reader values confirmed against the nginx identity header.
- The initial authorization manifest, authored from the resource list and the principal-ID record and validated with `migrate --dry-run`.
- The manifest review that confirms every administrator, resource, and grant is present, every resource has an owner or reader, and project YAML is unchanged.

**Out of scope**

- Manifest application, database initialization on the target store, and reconciliation — Phase 3.
- Enforcement cutover and rollback — Phases 4–5.
- Authorization policy, role, or action changes.
- Project YAML or other user-editable project-data changes.
- Ingester capability authorization — owned by `INGESTER_AUTHORIZATION_TASKS.md`.

**Affected components:** the deployment's `PROJECTS_DIR` and shared-data directory (read-only), the configured authorization SQLite store (read-only review via `list-*` and `migrate --dry-run`), and new recorded inputs. No application code, project data, or policy changes.

## Work Breakdown

### Area 1: Inventory deployment projects and shared data sources

**Objective:** A reviewed resource list with a locator per entry, no duplicate locator within a resource type, and a recorded conflict with any existing authorization record.

**Blocked on:** blocking decision 1 (deployment host and environment).

* [ ] `T1.1` **Change:** List every deployed project and shared data source with its locator and lifecycle state.
  * **Target:** the selected host's `PROJECTS_DIR` and shared-data directory; output to the new resource-list record (path recorded at execution, see Open Questions).
  * **Current → required:** The repository has no deployment inventory. Required: one entry per `shapeshifter.yml` project and per shared-data-source file.
  * **Implementation:** Walk `PROJECTS_DIR` for `shapeshifter.yml` exactly as `ProjectService.list_projects` does, and derive each project locator with `ProjectNameMapper.to_api_name`. Enumerate the shared-data directory and derive each source locator with the filename-stem rule used by `_data_source_locator`. Record the expected `active` lifecycle state for each entry.
  * **Constraints:** Read-only. Do not edit project or source files. Do not record ownership here.
  * **Validation:** `V-1`.

* [ ] `T1.2` **Change:** Check for duplicate or conflicting locators and compare with existing records.
  * **Target:** the resource-list record; the configured authorization store (`sead-authorization list-resources --json`).
  * **Current → required:** No locator conflict has been checked. Required: no duplicate locator within a type, and every conflict with an existing resource record written down.
  * **Implementation:** Compare the derived locators for duplicates within `project` and within `shared_data_source`. Cross-check the list against `sead-authorization list-resources --json` and record any locator that already exists with a different identity or lifecycle state as a conflict for the reviewer.
  * **Constraints:** Do not infer ownership from locators or metadata. Record conflicts; do not resolve them silently.
  * **Validation:** `V-1`, `V-2`.

**Completion evidence:** The resource list is written, every entry carries a locator and expected state, and no unresolved duplicate or conflict remains unrecorded.

### Area 2: Confirm principal IDs against deployment identities

**Objective:** A signed principal-ID record whose administrator, owner, and reader values match the nginx identity header exactly, with corrections recorded.

**Blocked on:** blocking decision 2 (principal ID values).

* [ ] `T2.1` **Change:** Collect and validate the deployment principal IDs.
  * **Target:** the new principal-ID record.
  * **Current → required:** The repository records no deployment identities. Required: the exact, case-sensitive header values nginx supplies for every administrator, owner, and reader.
  * **Implementation:** The deployment owner supplies each value. Check each against the principal contract in `docs/AUTHORIZATION.md`: non-empty, at most 255 characters, no control characters, and the value used for grant lookup is the trimmed string.
  * **Constraints:** Do not guess, lower-case, or otherwise normalize values. Record the value exactly as the identity header carries it.
  * **Validation:** `V-2`.

* [ ] `T2.2` **Change:** Compare with the bootstrap and existing application roles, and record corrections.
  * **Target:** the principal-ID record; `sead-authorization list-application-roles --json`.
  * **Current → required:** Bootstrap admins (`AUTHORIZATION_BOOTSTRAP_ADMIN_PRINCIPALS`) and any pre-existing `admin` role must agree with the supplied values. Required: each difference recorded as a correction, not applied.
  * **Implementation:** Compare the supplied administrator values with the bootstrap setting and the existing application roles; write any mismatch into the record for review before Phase 3 applies the manifest.
  * **Constraints:** Record corrections only; do not grant or revoke here.
  * **Validation:** `V-2`.

**Completion evidence:** The principal-ID record lists every administrator, owner, and reader value, each passing the identity contract and each correction written down.

### Area 3: Author and review the initial manifest

**Objective:** A manifest that `migrate --dry-run` validates, and a review that confirms every administrator, resource, and grant is present, every resource has an owner or reader, and project YAML is unchanged.

**Blocked on:** Areas 1 and 2.

* [ ] `T3.1` **Change:** Author the initial authorization manifest.
  * **Target:** new manifest file (path recorded at execution; see Open Questions).
  * **Current → required:** No manifest exists. Required: one file matching the validated schema.
  * **Implementation:** Build `{administrators: [...], resources: [{resource_type, locator, grants: [...]}]}` from the Area 1 resource list and the Area 2 principal-ID record. Project grants use direct-principal `owner` (plus `viewer`, `editor`, or `executor` as assigned); shared-source grants use direct-principal `reader`. Do not add child resources, broad-subject `owner` grants, or `everyone` grants unless the deployment owner approves and `AUTHORIZATION_ALLOW_AUTHENTICATED_EVERYONE` is enabled.
  * **Constraints:** Match `_load_validated_manifest` exactly: non-empty string administrators, `resource_type` from `ResourceType`, non-empty stripped `locator`, and grants with a valid `principal_id` (or typed subject) and role.
  * **Validation:** `V-3`.

* [ ] `T3.2` **Change:** Review the manifest, coverage, and project-data immutability.
  * **Target:** the manifest; the resource list; `PROJECTS_DIR` (read-only).
  * **Current → required:** Unreviewed inputs must not reach Phase 3. Required: a dated review naming the reviewer, stating that `migrate --dry-run` passed with the expected counts, that every resource has at least one owner or reader, and that project YAML is byte-identical before and after the phase.
  * **Implementation:** Run `sead-authorization migrate --manifest <manifest> --dry-run` and confirm the printed counts equal the resource list. Cross-check coverage with `sead-authorization list-grants` and the manifest draft so `PH2-AC-2` holds. Capture `git -C <projects-dir> status --porcelain` (or an equivalent hash of the project files) before and after to prove `PH2-AC-4`.
  * **Constraints:** No database writes; the reviewer is named; the manifest applies only in Phase 3.
  * **Validation:** `V-3`, `V-4`, `V-5`.

**Completion evidence:** The manifest validates dry-run, the review records coverage and the unchanged-YAML check, and the resource list, the principal-ID record, and the manifest agree with each other.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
| --- | --- | --- | --- |
| `PH2-AC-1` | `T1.1`, `T3.1`, `T3.2` | `V-1`, `V-3`, `V-4` | The reviewed manifest lists every administrator, project, shared data source, and grant; `migrate --dry-run` reports the matching counts |
| `PH2-AC-2` | `T1.1`, `T3.2` | `V-1`, `V-4` | Every resource has one or more reviewed owner or reader grants |
| `PH2-AC-3` | `T2.1`, `T2.2` | `V-2` | Principal IDs match the nginx header values; corrections are recorded before application |
| `PH2-AC-4` | `T3.2` | `V-5` | Project YAML and user-editable project data are unchanged by the migration-input process |

## Validation And Testing

| ID | Check and target | Command or method | Covers | Expected result |
| --- | --- | --- | --- | --- |
| `V-1` | Resource inventory and locator derivation | Enumerate `PROJECTS_DIR` and the shared-data directory; derive locators; compare with `sead-authorization list-resources --json` | `PH2-AC-1`, `PH2-AC-2` | One entry per resource with a locator and expected `active` state; no duplicate within a type |
| `V-2` | Principal-ID confirmation | Compare supplied header values with the identity contract and `sead-authorization list-application-roles --json` | `PH2-AC-3` | Each value passes the contract and matches, or the mismatch is recorded |
| `V-3` | Manifest schema validation | `sead-authorization migrate --manifest <manifest> --dry-run` | `PH2-AC-1` | Dry run validates and reports the expected administrator and resource counts |
| `V-4` | Manifest coverage review | Manual: each resource has at least one owner or reader grant; every administrator is present | `PH2-AC-1`, `PH2-AC-2` | No unowned resource and no missing administrator |
| `V-5` | Project-data immutability | `git -C <projects-dir> status --porcelain` (or file hashes) before and after the phase | `PH2-AC-4` | Empty diff; no project file changed |

For every check, record the command, its output, and the reviewer in the phase progress record. Do not report a planned check as a current pass. The `V-2` and `V-4` reviews require a named reviewer, matching `VM-2.1` and `VM-2.2`.

## Deliverables

| Deliverable | Description | Status | Link |
| --- | --- | --- | --- |
| Deployment resource list | Every deployed project and shared data source with locator and lifecycle state, plus the conflict check result | Blocked | Recorded at execution |
| Principal-ID record | Administrator, owner, and reader values confirmed against the nginx identity header, with corrections | Blocked | Recorded at execution |
| Initial authorization manifest | `{administrators, resources}` matching `_load_validated_manifest`, validated by `migrate --dry-run` | Blocked | Recorded at execution |
| Manifest review | Dated note naming the reviewer and confirming coverage and unchanged project YAML | Blocked | Recorded with the manifest |

## Progress Tracker

| Area | Status | Notes |
| --- | --- | --- |
| Area 1: Inventory resources | Blocked | Waiting on blocking decision 1: deployment host and environment |
| Area 2: Confirm principal IDs | Blocked | Waiting on blocking decision 2: nginx identity values |
| Area 3: Author and review the manifest | Blocked | Waiting on Areas 1 and 2 |

## Definition Of Done

- [ ] The deployment host and environment are named, and the resource list covers its `PROJECTS_DIR` and shared-data directory.
- [ ] Every administrator, project owner, and reader value is confirmed against the nginx identity header, with corrections recorded.
- [ ] The manifest passes `sead-authorization migrate --manifest <manifest> --dry-run` with counts matching the resource list.
- [ ] Every required resource has at least one owner or reader grant; no resource is unowned.
- [ ] The manifest includes every required administrator, project, shared data source, and initial grant.
- [ ] Project YAML and other user-editable project data are unchanged by the phase.
- [ ] The review note names the reviewer and the date, and every validation command and result is recorded.

## Risks And Open Questions

**Risks**

- **Locator collisions.** A project directory name and a shared-source filename can collide only within their own resource type; the check must still compare against existing records because a reused locator after deletion would create a new UUID rather than inherit old grants.
- **Identity-header trust.** The proxy middleware accepts any non-empty header value from a local process, so the recorded principal IDs must come from the actual nginx configuration, not from a guess (recorded in the handoff risks).
- **Drift between inventory and migration.** The resource list and manifest are snapshots; Phase 3 must apply the reviewed manifest against the same deployment state, and any change between phases must be re-reviewed.
- **`AUTHORIZATION_BOOTSTRAP_ADMIN_PRINCIPALS` drift.** If the deployment sets bootstrap admins that differ from the reviewed manifest, `migrate` would still honour the setting at startup; the correction is recorded here, not left silent.

**Open questions**

- **Manifest and record file location.** The repository stores no manifest today (`resources/config/` contains only `systemd/`). The location for the manifest and the resource and identity records is decided at execution; propose `resources/config/authorization_manifest.json` for the manifest unless the deployment owner records elsewhere.
- **Broad subjects and `everyone` grants.** The plan defaults to direct-principal grants. If the deployment needs group or authenticated-`everyone` grants, the deployment owner must provide the group IDs from the trusted membership provider, and `AUTHORIZATION_ALLOW_AUTHENTICATED_EVERYONE` must be enabled and approved before the manifest includes them.
