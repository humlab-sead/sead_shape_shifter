# Phase 2 Task Plan: Review Deployment Resources And Initial Grants

## Phase Summary

- **Source decision document:** [Centralized Authorization System](../../done/MITIGATE_SECURITY_ISSUES/done/CENTRALIZED_AUTHORIZATION_SYSTEM.md)
- **Source phase plan:** [Centralized Authorization System Cutover Plan](../CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md) — [Phase 2: Review Deployment Resources And Initial Grants](../CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md#phase-2-review-deployment-resources-and-initial-grants)
- **Status:** Complete for the test target; the reviewed inputs were applied and reconciled during Phase 3.
- **Goal:** Produce the deployment's authorization inputs — a reviewed resource list, confirmed principal IDs, and an initial administrator-and-grant manifest — without modifying project YAML.
- **Readiness:** Complete for the test target. The host, principal roster, resource owners/readers, and reviewed manifest are recorded in [TEST_DEPLOYMENT_RESOURCE_INVENTORY.md](../../../../secrets/TEST_DEPLOYMENT_RESOURCE_INVENTORY.md) and the [test-environment cutover handoff](../TEST_ENVIRONMENT_AUTHORIZATION_CUTOVER_HANDOFF.md).
- **Dependencies:** Phase 1 complete (route and operation inventory). The phase plan records `Depends On: The Phase 1 inventory`.
- **Constraints:** Do not modify project YAML or other user-editable project data. Do not infer principal ownership from filenames, project metadata, or request data. Keep the authorization policy unchanged. Do not apply or reconcile the manifest in this phase; application and reconciliation belong to Phase 3.

**Previously blocking decisions** — resolved for the test target as recorded in [TEST_DEPLOYMENT_RESOURCE_INVENTORY.md](../../../../secrets/TEST_DEPLOYMENT_RESOURCE_INVENTORY.md):

1. **Deployment host and environment:** resolved as the `test` environment on `humlabsead`, with legacy sources recorded separately from the target mounts.
2. **Principal ID values:** confirmed as the case-sensitive nginx user values, including administrators `admin`, `roger`, and `rebecka`.
3. **Resource owner and reader assignments:** confirmed in the inventory; all 26 projects have one owner grant and all 6 shared data sources have an authenticated reader grant.

The reviewed input set was validated with `migrate --dry-run`, then imported and reconciled during the later cutover. The target currently lacks the reviewed project and shared-data files; deciding whether to provision them or regenerate the policy is an operational follow-up, not an unresolved Phase 2 input decision.

**Acceptance Criteria**

1. `PH2-AC-1` (from `P-AC-2`) The reviewed manifest includes every required administrator, project, shared data source, and initial grant.
2. `PH2-AC-2` (from `P-AC-2`) Required resources have one or more reviewed owners or readers before migration.
3. `PH2-AC-3` (from `P-AC-3`) Principal IDs are confirmed against deployment identity values, with corrections recorded before application.
4. `PH2-AC-4` (from `P-AC-2`) Project YAML and other user-editable project data are unchanged by the migration-input process.

## Repository Findings

**Repository basis:** branch `authorization-system-cutover`, updated 2026-09-22 after the test-target cutover. The deployment inventory and handoff now record the selected host, principal roster, resource owners/readers, manifest review, and live import results.

| Evidence | Finding | Planning implication |
| --- | --- | --- |
| `backend/app/authorization/operations.py::inspect_manifest`, `apply_manifest`, `reconcile_manifest`, `_load_validated_manifest` | The manifest is `{administrators: [str], resources: [{resource_type, locator, grants: [...]}]}`. Grants accept a legacy `principal_id` or a typed `subject_type` plus `subject_id`; `everyone` requires `subject_id: "authenticated"` and is rejected unless `AUTHORIZATION_ALLOW_AUTHENTICATED_EVERYONE` is enabled | The manifest must match this schema; `migrate --dry-run` validates it without writing |
| `backend/app/scripts/authorization.py` (`sead-authorization`) | Commands include `migrate [--manifest --dry-run]`, `reconcile <manifest>`, `list-resources [--json]`, `list-grants [--effective --actor]`, `list-application-roles [--json]`, `grant-application-role`, `backup`, `restore`, `integrity-check` | Phase 2 uses `migrate --dry-run` and the `list-*` commands only; applying and reconciling are Phase 3 work |
| `backend/app/authorization/models.py` | `ResourceType`: `project`, `shared_data_source`, `project_child`, `shared_data_source_child`. `ApplicationRole`: `project_creator`, `operator`, `admin` | The manifest covers top-level `project` and `shared_data_source` records; child resources derive at runtime from their parents |
| `docs/AUTHORIZATION.md` (Principals; Resource Roles) | `principal_id` is the trimmed, case-sensitive value of the trusted-proxy identity header. Project roles are `viewer`, `editor`, `executor`, `owner`; the shared-source role is `reader`; broad subjects must not receive `owner` | Identity confirmation compares against the header values nginx actually supplies; direct-principal `owner` grants only |
| `backend/app/core/config.py` | `AUTHORIZATION_DATABASE_PATH` (default `state/authorization.sqlite3`), `AUTHORIZATION_BOOTSTRAP_ADMIN_PRINCIPALS`, `PROJECTS_DIR`, and the shared-data directory resolve the inventory sources | The inventory reads these configured directories on the selected host; bootstrap admins are compared, not invented |
| `backend/app/mappers/project_name_mapper.py::to_api_name`, `backend/app/authorization/dependencies.py::_data_source_locator` | A project locator is the API name derived from the project directory; a shared-data-source locator is the filename stem | The resource list uses these exact locator forms so `require_project` and `require_shared_data_source` lookups match later |
| [TEST_DEPLOYMENT_RESOURCE_INVENTORY.md](../../../secrets/TEST_DEPLOYMENT_RESOURCE_INVENTORY.md) and [TEST_ENVIRONMENT_AUTHORIZATION_CUTOVER_HANDOFF.md](./TEST_ENVIRONMENT_AUTHORIZATION_CUTOVER_HANDOFF.md) | Test host, nginx principal roster, 26 project owners, 6 shared-source readers, reviewed manifest, and cutover results are recorded | Phase 2 inputs are complete; missing target project content remains a provisioning or policy-regeneration decision |

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

**Affected components:** the legacy source directories and target deployment mounts (read-only during inventory), the configured authorization SQLite store, the reviewed manifest, and the inventory records. Phase 2 did not modify project YAML; manifest application and reconciliation were performed later as Phase 3 work.

## Work Breakdown

### Area 1: Inventory deployment projects and shared data sources

**Objective:** A reviewed resource list with a locator per entry, no duplicate locator within a resource type, and a recorded conflict with any existing authorization record.

**Evidence:** [TEST_DEPLOYMENT_RESOURCE_INVENTORY.md](../../../../secrets/TEST_DEPLOYMENT_RESOURCE_INVENTORY.md), including the 26-project and 6-shared-source inventory and conflict review.

* [x] `T1.1` **Change:** List every migration-source project and shared data source with its locator and lifecycle state.
  * **Target:** the selected host's `PROJECTS_DIR` and shared-data directory; output to the new resource-list record (path recorded at execution, see Open Questions).
  * **Current → required:** The repository had no recorded deployment inventory. Required: one entry per legacy `shapeshifter.yml` project and per shared-data-source file, with the target mount state noted separately.
  * **Implementation:** Walk `PROJECTS_DIR` for `shapeshifter.yml` exactly as `ProjectService.list_projects` does, and derive each project locator with `ProjectNameMapper.to_api_name`. Enumerate the shared-data directory and derive each source locator with the filename-stem rule used by `_data_source_locator`. Record the expected `active` lifecycle state for each entry.
  * **Constraints:** Read-only. Do not edit project or source files. Do not record ownership here.
  * **Validation:** `V-1` — passed; 26 projects and 6 shared data sources were enumerated, with the target content gap recorded.

* [x] `T1.2` **Change:** Check for duplicate or conflicting locators and compare with existing records.
  * **Target:** the resource-list record; the configured authorization store (`sead-authorization list-resources --json`).
  * **Current → required:** No locator conflict has been checked. Required: no duplicate locator within a type, and every conflict with an existing resource record written down.
  * **Implementation:** Compare the derived locators for duplicates within `project` and within `shared_data_source`. Cross-check the list against `sead-authorization list-resources --json` and record any locator that already exists with a different identity or lifecycle state as a conflict for the reviewer.
  * **Constraints:** Do not infer ownership from locators or metadata. Record conflicts; do not resolve them silently.
  * **Validation:** `V-1`, `V-2` — passed; no duplicate or existing-resource conflict was found.

**Completion evidence:** The resource list is recorded in [TEST_DEPLOYMENT_RESOURCE_INVENTORY.md](../../../secrets/TEST_DEPLOYMENT_RESOURCE_INVENTORY.md); every entry carries a locator and expected state, and no unresolved duplicate or conflict remains unrecorded.

### Area 2: Confirm principal IDs against deployment identities

**Objective:** A signed principal-ID record whose administrator, owner, and reader values match the nginx identity header exactly, with corrections recorded.

**Evidence:** The principal roster and administrator decision are recorded in [TEST_DEPLOYMENT_RESOURCE_INVENTORY.md](../../../../secrets/TEST_DEPLOYMENT_RESOURCE_INVENTORY.md); runtime identity behavior was exercised through nginx during the test cutover.

* [x] `T2.1` **Change:** Collect and validate the deployment principal IDs.
  * **Target:** the new principal-ID record.
  * **Current → required:** The repository now records the exact, case-sensitive nginx user values for administrators and grant principals.
  * **Implementation:** The deployment owner supplies each value. Check each against the principal contract in `docs/AUTHORIZATION.md`: non-empty, at most 255 characters, no control characters, and the value used for grant lookup is the trimmed string.
  * **Constraints:** Do not guess, lower-case, or otherwise normalize values. Record the value exactly as the identity header carries it.
  * **Validation:** `V-2` — passed; the roster values match the bootstrap-created nginx users.

* [x] `T2.2` **Change:** Compare with the bootstrap and existing application roles, and record corrections.
  * **Target:** the principal-ID record; `sead-authorization list-application-roles --json`.
  * **Current → required:** Bootstrap admins and application roles agree with the reviewed roster; the three administrators are `admin`, `roger`, and `rebecka`.
  * **Implementation:** Compare the supplied administrator values with the bootstrap setting and the existing application roles; write any mismatch into the record for review before Phase 3 applies the manifest.
  * **Constraints:** Record corrections only; do not grant or revoke here.
  * **Validation:** `V-2` — passed; the inventory records the administrator and deployment-role assignments.

**Completion evidence:** The principal-ID record lists every administrator, owner, and reader value, and records the accepted deployment-role assignments and deferred collaborator grants.

### Area 3: Author and review the initial manifest

**Objective:** A manifest that `migrate --dry-run` validates, and a review that confirms every administrator, resource, and grant is present, every resource has an owner or reader, and project YAML is unchanged.

**Evidence:** [resources/authorization/test-initial-manifest.yaml](../../../../resources/authorization/test-initial-manifest.yaml), the inventory validation record, and the live cutover handoff.

* [x] `T3.1` **Change:** Author the initial authorization manifest.
  * **Target:** new manifest file (path recorded at execution; see Open Questions).
  * **Current → required:** The reviewed manifest is recorded in the repository and was provisioned to the target configuration directory by the operator.
  * **Implementation:** Build `{administrators: [...], resources: [{resource_type, locator, grants: [...]}]}` from the Area 1 resource list and the Area 2 principal-ID record. Project grants use direct-principal `owner` (plus `viewer`, `editor`, or `executor` as assigned); shared-source grants use direct-principal `reader`. Do not add child resources, broad-subject `owner` grants, or `everyone` grants unless the deployment owner approves and `AUTHORIZATION_ALLOW_AUTHENTICATED_EVERYONE` is enabled.
  * **Constraints:** Match `_load_validated_manifest` exactly: non-empty string administrators, `resource_type` from `ResourceType`, non-empty stripped `locator`, and grants with a valid `principal_id` (or typed subject) and role.
  * **Validation:** `V-3` — passed; dry-run reported 32 resources and 3 administrators with no database changes.

* [x] `T3.2` **Change:** Review the manifest, coverage, and project-data immutability.
  * **Target:** the manifest; the resource list; `PROJECTS_DIR` (read-only).
  * **Current → required:** The dated review names the deployment owner, records dry-run counts, confirms grant coverage, and records read-only project-data inspection before the later Phase 3 import.
  * **Implementation:** Run `sead-authorization migrate --manifest <manifest> --dry-run` and confirm the printed counts equal the resource list. Cross-check coverage with `sead-authorization list-grants` and the manifest draft so `PH2-AC-2` holds. Capture `git -C <projects-dir> status --porcelain` (or an equivalent hash of the project files) before and after to prove `PH2-AC-4`.
  * **Constraints:** No database writes; the reviewer is named; the manifest applies only in Phase 3.
  * **Validation:** `V-3`, `V-4`, `V-5` — passed; the reviewed manifest has 26 owner grants, 6 authenticated reader grants, and no project-data mutation was observed.

**Completion evidence:** The manifest validates in dry-run, the review records coverage and unchanged project data, and the resource list, principal roster, and manifest agree. The later handoff records successful import and zero missing records after reconciliation.

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
| `V-1` | Resource inventory and locator derivation | Enumerate the legacy project and shared-data sources; derive locators; compare with the target authorization records | `PH2-AC-1`, `PH2-AC-2` | **Passed 2026-09-20/22:** 26 projects and 6 shared sources are listed; target content absence is recorded |
| `V-2` | Principal-ID confirmation | Compare the supplied nginx user values with the identity contract and recorded application roles | `PH2-AC-3` | **Passed 2026-09-20/22:** administrator, owner, and reader identities are recorded with no unresolved correction |
| `V-3` | Manifest schema validation | `sead-authorization migrate --manifest <manifest> --dry-run` | `PH2-AC-1` | **Passed 2026-09-20:** 32 resources and 3 administrators validated with no database changes |
| `V-4` | Manifest coverage review | Check the reviewed manifest and `list-grants` output | `PH2-AC-1`, `PH2-AC-2` | **Passed 2026-09-22:** 26 project owner grants and 6 authenticated shared-source reader grants cover all 32 resources |
| `V-5` | Project-data immutability | Read-only inventory and before/after project-data inspection | `PH2-AC-4` | **Passed 2026-09-22:** no project YAML or user-editable project data was changed by the input preparation or cutover |

For every check, record the command, its output, and the reviewer in the phase progress record. Do not report a planned check as a current pass. The `V-2` and `V-4` reviews require a named reviewer, matching `VM-2.1` and `VM-2.2`.

## Deliverables

| Deliverable | Description | Status | Link |
| --- | --- | --- | --- |
| Deployment resource list | 26 migration-source projects and 6 shared data sources with locator and lifecycle state, plus the conflict check result | Done | [TEST_DEPLOYMENT_RESOURCE_INVENTORY.md](../../../../secrets/TEST_DEPLOYMENT_RESOURCE_INVENTORY.md) |
| Principal-ID record | Administrator, owner, and reader values confirmed against the nginx identity header, with accepted role decisions | Done | [TEST_DEPLOYMENT_RESOURCE_INVENTORY.md](../../../../secrets/TEST_DEPLOYMENT_RESOURCE_INVENTORY.md) |
| Initial authorization manifest | `{administrators, resources}` matching `_load_validated_manifest`, validated by `migrate --dry-run` | Done | [test-initial-manifest.yaml](../../../../resources/authorization/test-initial-manifest.yaml) |
| Manifest review | Dated note naming the reviewer and confirming coverage and unchanged project YAML | Done | [TEST_DEPLOYMENT_RESOURCE_INVENTORY.md](../../../../secrets/TEST_DEPLOYMENT_RESOURCE_INVENTORY.md) and [test cutover handoff](../TEST_ENVIRONMENT_AUTHORIZATION_CUTOVER_HANDOFF.md) |

## Progress Tracker

| Area | Status | Notes |
| --- | --- | --- |
| Area 1: Inventory resources | Done | 26 projects and 6 shared data sources inventoried; no locator conflict remains |
| Area 2: Confirm principal IDs | Done | Nginx identities, administrators, owners, readers, and deployment roles recorded |
| Area 3: Author and review the manifest | Done | Dry-run passed; coverage and immutability reviewed; later import and reconciliation passed |

## Definition Of Done

- [x] The test deployment host and environment are named, and the resource list covers the migration source and target mount state.
- [x] Every administrator, project owner, and reader value is confirmed against the nginx identity header, with accepted role decisions recorded.
- [x] The manifest passes `sead-authorization migrate --manifest <manifest> --dry-run` with counts matching the resource list.
- [x] Every reviewed resource has at least one owner or reader grant; no reviewed resource is unowned.
- [x] The manifest includes every reviewed administrator, project, shared data source, and initial grant.
- [x] Project YAML and other user-editable project data are unchanged by the phase.
- [x] The inventory and handoff name the reviewer and date, and the validation results are recorded.

## Risks And Open Questions

**Risks**

- **Locator collisions.** A project directory name and a shared-source filename can collide only within their own resource type; the check must still compare against existing records because a reused locator after deletion would create a new UUID rather than inherit old grants.
- **Identity-header trust.** The proxy middleware accepts any non-empty header value from a local process, so the recorded principal IDs must come from the actual nginx configuration, not from a guess (recorded in the handoff risks).
- **Drift between inventory and migration.** The resource list and manifest are snapshots. The 2026-09-22 handoff records that the imported store reconciled with zero missing records; any future project or shared-source change requires a new review.
- **Target content mismatch.** The reviewed manifest names 26 projects and 6 shared data sources that are not currently mounted in the target. The authorization records are valid, but application users cannot access absent content until it is provisioned or the policy is regenerated.
- **`AUTHORIZATION_BOOTSTRAP_ADMIN_PRINCIPALS` drift.** The reviewed administrators are `admin`, `roger`, and `rebecka`; future changes to the bootstrap setting require a new manifest review.

**Open questions**

- **Project and shared-data content disposition.** Decide whether to provision the reviewed legacy content under the target mounts or regenerate the policy for the content the test environment actually holds. This is recorded as operational follow-up in [TEST_ENVIRONMENT_AUTHORIZATION_CUTOVER_HANDOFF.md](../TEST_ENVIRONMENT_AUTHORIZATION_CUTOVER_HANDOFF.md).
- **Deleted-resource retention.** Decide whether deleted lifecycle rows and the associated `@local` grants remain as history or are removed. Current export and reconciliation behavior excludes deleted resources.
