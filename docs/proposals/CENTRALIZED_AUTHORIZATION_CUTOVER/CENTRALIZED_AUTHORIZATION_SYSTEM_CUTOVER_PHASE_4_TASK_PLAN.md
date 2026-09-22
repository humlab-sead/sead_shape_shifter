# Centralized Authorization System Cutover – Phase 4 Task Plan

- **Source proposal:** [Centralized Authorization System](../done/MITIGATE_SECURITY_ISSUES/done/CENTRALIZED_AUTHORIZATION_SYSTEM.md)
- **Source phase plan:** [Centralized Authorization System Cutover Plan](./CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md) - [Phase 4: Deliver And Record The UAT-Ready Deployment](./CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md#phase-4-deliver-and-record-the-uat-ready-deployment)
- **Prerequisite plans:** [Phase 3 task plan](./done/CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PHASE_3_TASK_PLAN.md), [Phase 2 task plan](./done/CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PHASE_2_TASK_PLAN.md), [Target Environment Configuration Layout task plan](./done/TARGET_ENVIRONMENT_CONFIGURATION_LAYOUT_TASK_PLAN.md)
- **Goal:** Record the authorization-enabled deployment on the new server as ready for user acceptance testing, with its operator procedures exercised and the evidence a user acceptance test needs assembled.
- **Plan readiness:** Validated. The deployment, its host, its paths, and every command below are verified against the repository and the recorded Phase 3 evidence. The production flip is out of scope and owned by [PRODUCTION_FLIP_TO_AUTHORIZED_SERVER.md](../future/PRODUCTION_FLIP_TO_AUTHORIZED_SERVER.md).
- **Dependencies:** Phases 1–3 complete for the test target; the reviewed project and shared-data content provisioned; Roger Mähler named as the rollback decision owner.

## Acceptance Criteria

1. `PH4-AC-1` (from `P-AC-7`) The deployment record identifies the release, manifest, backup, and rollback decision owner.
2. `PH4-AC-2` (from `P-AC-7`) Post-deployment checks confirm expected administrator, owner, and denied-principal behavior.
3. `PH4-AC-3` (from `P-AC-7`) Authorization audit records exist for the migration and later administrative mutations.
4. `PH4-AC-4` (from `P-AC-8`) A rollback restores a valid authorization database, and reconciliation completes afterward.
5. `PH4-AC-5` (from `P-AC-1`, `P-AC-2`) An unclassified route, unowned resource, identity mismatch, or failed check blocks the deployment from being presented for acceptance instead of being accepted without review.

## Fixed Constraints

- **Enforcement has no toggle.** It follows from `TRUSTED_PROXY_AUTH_ENABLED`. `backend/app/core/config.py` refuses to start when `ENVIRONMENT=production` and that value is false, and refuses startup when `AUTHORIZATION_BOOTSTRAP_ADMIN_PRINCIPALS` is empty in production. The new server already runs that configuration, so this phase records and verifies it rather than enabling it.
- **The rollback backup captures state at backup time.** Grants added after the backup are lost on restore. Take the recorded backup immediately before the acceptance window and add no grants during it.
- **The production flip is not part of this phase.** Do not repoint production DNS or the reverse proxy, and do not provision production users.
- Keep the readiness backup until user acceptance testing concludes or the fallback to the old server is no longer available.
- Do not modify project YAML to assign ownership or grants, and do not change authorization policy here.
- Record unresolved facts as explicit blockers; do not infer principal ownership from filenames, project metadata, or request data.

## Repository Findings

**Repository basis:** branch `dev` at `4a74bc40`; planning date 2026-09-22; working tree clean. The deployment under record is the authorization-enabled instance on the new server: host `humlabsead`, deployment user `test-shape-shifter.sead.se`, proxy `https://test-shape-shifter.sead.se`, container `shape-shifter` on `127.0.0.1:8012`.

| Evidence | Finding | Planning implication |
| --- | --- | --- |
| [TEST_ENVIRONMENT_AUTHORIZATION_CUTOVER_HANDOFF.md](./TEST_ENVIRONMENT_AUTHORIZATION_CUTOVER_HANDOFF.md) | Records the release image `shape-shifter:dev` from `dbff5ab9`, zero-missing reconciliation, a backup byte-identical to the readiness backup, 26 of 26 project locators, all 6 shared data sources listed, and a verified `sead-options` connection | This phase records and re-verifies that state for acceptance rather than rebuilding it |
| `backend/app/core/config.py::Settings` | Requires `TRUSTED_PROXY_AUTH_ENABLED=true` in production and a non-empty bootstrap administrator, and rejects an authorization database path inside project, log, or shared-data directories | Confirm these are the values the deployment runs with; the values themselves are already live |
| `backend/app/authorization/operations.py::apply_manifest` | Migration writes administrators, resources, and grants with actor `migration` | Provisioning audit events are identifiable by actor |
| `backend/app/authorization/repository.py::_record_audit` | Records `bootstrap_admin_created`, `application_role_created`, `application_role_revoked`, `grant_created`, `grant_revoked`, `resource_lifecycle_changed` | `PH4-AC-3` is checked against the store, not by scraping logs |
| `backend/app/scripts/authorization.py::list_audit_events` | `list-audit-events --json` emits `event_id`, `occurred_at`, `actor_principal_id`, `event_type`, `outcome`, `correlation_id`, `details` | Record event counts and the `event_type` distribution |
| `container/scripts/authorization.sh` | Runs the CLI inside the deployment container; convenience commands `backup`, `restore`, `import-manifest`, `export-manifest`; `--backup-dir` selects the host backup directory | All store operations have a wrapper entry point; the wrapper stages a host manifest into the container because migration reads it twice |
| `container/scripts/verify/rollback_exercise.sh` | Requires `--image`, `--authorization-backup`, `--manifest`; optional `--backup-dir`, `--evidence-dir`, `--container-name`, `--host-port`, `--yes`; leaves the service stopped when a step fails | Exercise the documented rollback with this script and record the transcript |
| `container/scripts/verify/verify_authenticated_access.sh` | Requires `--base-url`, `--principal-a`, `--principal-b`, `--project-a`, `--project-b`; expects unauthenticated `401`, allowed `200`, concealed denied `404`; needs each project granted to exactly one non-administrator principal | The reviewed projects are now provisioned, so the check can use reviewed projects instead of temporary ones |
| `backend/tests/authorization/test_route_authentication.py` | Enforces parity between the assembled FastAPI routes and `docs/AUTHORIZATION_ROUTE_INVENTORY.md`, and requires every API route to be classified | This is the executable `PH4-AC-5` check |
| `container/DEPLOYMENT.md` | Documents `make info`, `build`, `service-install`, `service-restart`, `healthcheck`, and the `host.docker.internal` requirement for host services | Operator procedures in the evidence pack are the documented ones, not new ones |

## Scope

**In scope**

- Recording the deployment's release, manifest, backup, and owner identity.
- Re-running the blocking pre-acceptance checks against the deployment.
- Re-running access checks with reviewed projects now that the reviewed content is provisioned.
- Exercising the documented backup, restore, and rollback procedures and recording what a rollback discards.
- Assembling the evidence pack for user acceptance testing and recording the deployment result.

**Out of scope**

- Provisioning production users, accounts, or grants.
- Repointing production DNS or the reverse proxy, and any part of the production flip.
- Authoring or executing user acceptance testing.
- Selecting the production Podman service model.
- Authorization policy changes and route reclassification.

**Affected components:** the deployment's `CONFIG_DIR` and `CONTAINER_DATA_DIR`, the authorization SQLite store, the systemd user unit, and the documentation under `docs/proposals/CENTRALIZED_AUTHORIZATION_CUTOVER/`.

## Work Breakdown

### Area 1: Record the deployment identity

**Objective:** The release, manifest, backup, and owner are recorded together from the running deployment.

**Affected code:** Deployment record (`UAT_READY_AUTHORIZATION_DEPLOYMENT_HANDOFF.md`, new, in this folder); `<CONFIG_DIR>` on the new server.

**Dependencies:** None; the deployment exists.

**Tasks:**

* [x] `T4.1` **Change:** Record the release and configuration identity from the running deployment.
  * **Target:** Deployment record (new handoff in this folder, marked `NEW`); `<CONFIG_DIR>/deployment.env`.
  * **Current -> required:** The Phase 3 handoff records identity in prose; the acceptance evidence needs it stated as an input set with commands.
  * **Implementation:** Record `make info` output, the image ID, the `org.opencontainers.image.revision` label, `GIT_REF`, and `IMAGE_NAME`. Confirm the revision matches the commit the focused and full backend suites passed on.
  * **Constraints:** Record identifiers only; never record credential values or `.pgpass` contents.
  * **Validation:** `V-4.1`, `V-4.2`. Re-confirmed 2026-09-22 against the running container: image `shape-shifter:dev`, ID `6a487db7...04a8`, revision `dbff5ab9...4f96`, `GIT_REF=dev`, container port `8012`, uid/gid `1021/1021`.
* [x] `T4.2` **Change:** Record the manifest, backup, and decision owners.
  * **Target:** Deployment record.
  * **Current -> required:** Recorded in the Phase 3 handoff, but not as a single acceptance input set.
  * **Implementation:** Record the manifest path and SHA-256, the readiness backup path and SHA-256, the post-acceptance backup path once taken, the rollback decision owner (Roger Mähler), and the rollback's discard rule.
  * **Constraints:** State the rollback rule explicitly: grants added after the backup are lost on restore.
  * **Validation:** `V-4.3`. Ran 2026-09-22: the deployed manifest's SHA-256 is `43c03186...fb90`, identical to the reviewed manifest in the repository, so the running policy is the reviewed policy.

**Completion evidence:** Every acceptance input has an immutable identifier and a recorded command that produced it.

### Area 2: Re-run the blocking pre-acceptance checks

**Objective:** Confirm no route is unclassified, no resource is unowned, and the audit trail covers migration and later mutations.

**Affected code:** `backend/tests/authorization/test_route_authentication.py`, `docs/AUTHORIZATION_ROUTE_INVENTORY.md`, the deployment's authorization store.

**Dependencies:** Area 1.

**Tasks:**

* [x] `T4.3` **Change:** Run the route-inventory and classification checks at the deployed revision.
  * **Target:** `backend/tests/authorization/test_route_authentication.py`.
  * **Current -> required:** The checks pass on `dev`; the deployed revision's own result is not recorded as acceptance evidence.
  * **Implementation:** Run the focused authorization suite and this module at the deployed revision, and retain the result with the release identity.
  * **Constraints:** A mismatch between the runtime routes and the inventory blocks acceptance; do not edit the inventory to pass the check.
  * **Validation:** `V-4.4`. Ran 2026-09-22: `.venv/bin/pytest backend/tests/authorization` reported 192 passed and 1 skipped, and `git diff --stat dbff5ab9..HEAD -- backend src tests` shows only `container/DEPLOYMENT.md` differing, so the deployed revision's application code and tests are unchanged.
* [x] `T4.4` **Change:** Review resources and grants for unowned or conflicting records.
  * **Target:** Deployment store through `container/scripts/authorization.sh`.
  * **Current -> required:** Reviewed on 2026-09-22 for the applied records; re-run against the current store so the acceptance evidence is current.
  * **Implementation:** Run `list-resources --json` and `list-grants --json`, and confirm every active resource has a grant and no active locator conflicts. Record counts, and explain retained `deleted` rows rather than omitting them.
  * **Constraints:** Resolve conflicts by correcting configuration, never by editing project YAML to create ownership.
  * **Validation:** `V-4.5`. Resource list reviewed 2026-09-22: 36 active resources (30 project, 6 shared data source) and 15 deleted. All 32 reviewed manifest locators are active, and four active `verification-containment-*` projects are not in the manifest. Grant review found 53 grants, every active resource carries at least one, and no grant points at a missing resource, so `PH4-AC-5` holds.
* [x] `T4.5` **Change:** Confirm the audit trail covers migration and later mutations.
  * **Target:** `container/scripts/authorization.sh list-audit-events --json`.
  * **Current -> required:** The audit table exists; its coverage is not recorded as acceptance evidence.
  * **Implementation:** Record the event count, the `event_type` distribution, and confirm events with actor `migration` for provisioning plus any later administrative mutations.
  * **Constraints:** A missing migration audit record blocks acceptance and is not a documentation gap.
  * **Validation:** `V-4.6`. Ran 2026-09-22: 144 events, of which 34 came from actor `migration` (26 owner grants, 6 reader grants, 2 administrator roles) and 2 later ones recorded temporary-project grants. All events are `allowed` mutations; `correlation_id` is null on every event and role events omit the principal, both recorded as limitations.

**Completion evidence:** All three checks pass, or the failing check is recorded as an acceptance blocker with its owner.

### Area 3: Re-verify access and exercise the procedures

**Objective:** Access behavior is confirmed with reviewed projects, and the documented backup, restore, and rollback procedures are shown to work.

**Affected code:** `container/scripts/verify/verify_authenticated_access.sh`, `container/scripts/verify/rollback_exercise.sh`.

**Dependencies:** Areas 1–2.

**Tasks:**

* [x] `T4.6` **Change:** Re-run access checks using reviewed projects.
  * **Target:** Proxy endpoint `https://test-shape-shifter.sead.se`.
  * **Current -> required:** The recorded check used temporary colon-qualified projects because the reviewed content was absent; it is now provisioned.
  * **Implementation:** Run `verify_authenticated_access.sh` with two reviewed projects and their granting principals, and add the administrator probe for a protected list route. Confirm unauthenticated `401`, allowed `200`, and concealed denied `404`.
  * **Constraints:** Do not grant ownership to make a check pass. Where a reviewed project has no owner, use the temporary-project path and record that it proves enforcement rather than dataset availability.
  * **Validation:** `V-4.7`. Run 2026-09-22 with `bruno` and `riia` against `Bruno-Strucke-v2-test` and `Glykou_etal_2021`: unauthenticated `401`, `bruno` on his own project `200`, `bruno` on `Glykou_etal_2021` concealed `404`, `riia` on her own project `200`, `admin` on the project list `200`. The script's `riia` on `Bruno-Strucke-v2-test` probe reports `200` where it expects `404`; that is a test-selection error, not an access defect, because `riia` holds `project_maintainer`, which grants `READ` on every project in `backend/app/authorization/policy.py`, and `AuthorizationService.is_allowed()` consults deployment roles before resource grants. No reviewed pair can supply a well-formed isolation probe: `roger` and `rebecka` hold `admin`, `riia` holds `project_maintainer`, and `bruno` is the only reviewed owner who is not a global reader. The four required outcomes are recorded in the deployment record.
* [ ] `T4.7` **Change:** Exercise backup, restore, and rollback against the deployment.
  * **Target:** `container/scripts/verify/rollback_exercise.sh`, run as the deployment user from `<HOME>/container`.
  * **Current -> required:** Rollback was exercised on 2026-09-22; the acceptance evidence needs a current transcript with the recorded image and backup.
  * **Implementation:** Create a post-acceptance backup with `container/scripts/authorization.sh backup`, record its path and SHA-256, then run the rollback exercise with `--image`, `--authorization-backup`, `--manifest`, and `--evidence-dir`. Record the transcript and confirm integrity, reconciliation, image identity, and health. Redeploy the recorded release afterwards.
  * **Constraints:** The script leaves the service stopped when a step fails; do not proceed past a failed rollback without the rollback owner's decision. Verify a copy when a check needs a writable database, never the retained backup.
  * **Validation:** `V-4.8`, `V-4.9`.

**Completion evidence:** Access checks return the expected statuses with reviewed projects, and the rollback transcript shows integrity and reconciliation passing.

### Area 4: Assemble the acceptance evidence and record the result

**Objective:** A user acceptance test owner can act on the record without reading the Phase 3 archive.

**Affected code:** Deployment record; `docs/proposals/CENTRALIZED_AUTHORIZATION_CUTOVER/CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md`.

**Dependencies:** Areas 1–3.

**Tasks:**

* [ ] `T4.8` **Change:** Assemble the evidence pack.
  * **Target:** Deployment record.
  * **Current -> required:** Phase 3 evidence exists as a completion record; acceptance needs a condensed statement of what is verified, what is not, and how to exercise it.
  * **Implementation:** Record the verified claims with their commands and results, the known limitations (`bulgaria-arbodat-lookup-options` declares no data file; the container reaches host services only as `host.docker.internal`; PostgreSQL credential rotation is out of scope by decision), and the steps a tester follows to exercise the system.
  * **Constraints:** Do not state or imply that user acceptance criteria are owned here, and do not present unverified checks as passed.
  * **Validation:** `V-4.10`.
* [ ] `T4.9` **Change:** Update the phase plan status.
  * **Target:** `CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md`.
  * **Current -> required:** The plan still shows Phase 4 as not started.
  * **Implementation:** Mark Phase 4 complete with its evidence, confirm Phase 5 prerequisites, and leave the production flip reference intact.
  * **Constraints:** Change only the status and completion statements; do not re-scope the plan in this task.
  * **Validation:** `V-4.10`.

**Completion evidence:** The record is self-contained, links every result, states the limitations, and the phase plan reflects the outcome.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
| --- | --- | --- | --- |
| `PH4-AC-1` | `T4.1`, `T4.2`, `T4.7` | `V-4.1`, `V-4.2`, `V-4.3`, `V-4.8` | Release, manifest, backup, and owner recorded with immutable identifiers |
| `PH4-AC-2` | `T4.6` | `V-4.7` | Administrator, owner, denied-principal, and unauthenticated outcomes recorded |
| `PH4-AC-3` | `T4.5` | `V-4.6` | Migration and mutation audit events recorded with counts and types |
| `PH4-AC-4` | `T4.7` | `V-4.8`, `V-4.9` | Rollback restores the image and database, integrity passes, reconciliation is zero-missing |
| `PH4-AC-5` | `T4.3`, `T4.4` | `V-4.4`, `V-4.5` | Route inventory and classification checks pass, and no active resource is unowned or conflicting |

## Validation And Testing

| ID | Check and target | Command or method | Covers | Expected result |
| --- | --- | --- | --- | --- |
| `V-4.1` | Release identity | `podman image inspect <image> --format '{{.Id}}'` and the `org.opencontainers.image.revision` label | `PH4-AC-1` | Recorded revision equals the commit the suites passed on |
| `V-4.2` | Configured values | `make info` in `<HOME>/container` | `PH4-AC-1` | `GIT_REF` and `IMAGE_NAME` agree with the recorded release |
| `V-4.3` | Manifest and backup identity | `sha256sum` on the manifest and the retained backup | `PH4-AC-1` | Both checksums recorded and unchanged from the Phase 3 record |
| `V-4.4` | Route inventory and classification | `.venv/bin/pytest backend/tests/authorization -q` at the deployed revision | `PH4-AC-5` | All checks pass; every API route classified and documented |
| `V-4.5` | Resource ownership | `container/scripts/authorization.sh list-resources --json` and `list-grants --json` | `PH4-AC-5` | Every active resource has a grant; no active locator conflict |
| `V-4.6` | Audit trail | `container/scripts/authorization.sh list-audit-events --json` | `PH4-AC-3` | Migration events with actor `migration` plus later mutation events |
| `V-4.7` | Access checks | `container/scripts/verify/verify_authenticated_access.sh --base-url https://test-shape-shifter.sead.se --principal-a/--principal-b --project-a/--project-b`, plus an administrator probe | `PH4-AC-2` | Unauthenticated `401`, allowed `200`, concealed denied `404`, administrator `200` |
| `V-4.8` | Backup and integrity | `container/scripts/authorization.sh backup`, then checksum and integrity verification on a copy | `PH4-AC-1` | Backup recorded with path and checksum; integrity passes |
| `V-4.9` | Rollback exercise | `container/scripts/verify/rollback_exercise.sh --image --authorization-backup --manifest --evidence-dir` | `PH4-AC-4` | Image and database restored, integrity passes, reconciliation zero-missing, health `200` |
| `V-4.10` | Record review | Manual review of the deployment record, then `scripts/check_doc_links.sh` and `git diff --check` | All criteria | Every result linked, limitations explicit, no credential values present |

`V-4.7` note: the symmetric-isolation probe in `verify_authenticated_access.sh` cannot pass on the reviewed roster, because every reviewed project owner except `bruno` holds a deployment role that grants read. The four required outcomes are met; the probe result and its cause are recorded in the deployment record.

**Phase milestone mapping:** `VM-4.1` is covered by `V-4.1`, `V-4.2`, `V-4.3`, and `V-4.8`; `VM-4.2` by `V-4.6` and `V-4.7`; `VM-4.3` by `V-4.9`; `VM-4.4` by `V-4.4` and `V-4.5`.

## Deliverables

| Deliverable | Description | Status | Link |
| --- | --- | --- | --- |
| Deployment record | Release, manifest, backup, owner, access results, audit summary, rollback outcome, limitations | Not started | `UAT_READY_AUTHORIZATION_DEPLOYMENT_HANDOFF.md` (new, this folder) |
| Blocking-check evidence | Route inventory, ownership, and audit results | Not started | Deployment record |
| Rollback evidence | Transcript directory from the rollback exercise | Not started | `<DATA_DIR>/backups/rollback-<timestamp>` |
| Post-acceptance backup | Timestamped authorization backup with checksum | Not started | `<DATA_DIR>/backups` |
| Phase plan status update | Phase 4 complete, Phase 5 prerequisites confirmed | Not started | [CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md](./CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md) |

## Progress Tracker

| Area | Status | Notes |
| --- | --- | --- |
| Area 1: Record the deployment identity | Done | Identity re-confirmed on the running container; the deployed manifest checksum matches the reviewed manifest |
| Area 2: Re-run the blocking pre-acceptance checks | Done | `T4.3`, `T4.4`, and `T4.5` complete; `PH4-AC-5` holds with no unowned or missing resource |
| Area 3: Re-verify access and exercise the procedures | In progress | `T4.6` complete; `T4.7` outstanding |
| Area 4: Assemble the acceptance evidence and record the result | Not started | Depends on Areas 1–3 |

## Definition Of Done

- [ ] `PH4-AC-1` has the release image, revision, manifest checksum, backup path and checksum, and rollback owner recorded together.
- [x] `PH4-AC-2` has administrator, owner, denied-principal, and unauthenticated results recorded using reviewed projects.
- [ ] `PH4-AC-3` has migration and administrative-mutation audit events recorded with counts and types.
- [ ] `PH4-AC-4` has a rollback transcript with integrity and reconciliation outcomes, or a recorded rollback-owner decision.
- [ ] `PH4-AC-5` has route-inventory, classification, and ownership results recorded, with any blocker named.
- [ ] The evidence pack states what is verified, what is not, and how a tester exercises the system, without claiming ownership of acceptance criteria.
- [ ] `scripts/check_doc_links.sh` and `git diff --check` pass, and no credential values appear in the record.
- [ ] The phase plan status reflects the outcome, and the production flip remains referenced to its own proposal.

## Risks And Open Questions

- **The rollback discards later grants.** The backup captures state at backup time. Sequence any grant change outside the acceptance window, and state the discard rule in the record.
- **Acceptance criteria are owned elsewhere.** This phase supplies evidence, not a pass or fail judgement. Record the distinction so the record is not read as an acceptance decision.
- **Reviewed projects may still lack owners.** If a reviewed project has no granting principal, the access check falls back to temporary projects, which proves enforcement rather than dataset availability, and the record must say so.
- **Host services are reachable only through the gateway alias.** Any deployment-side connection check against a host database must use `host.docker.internal`; a host-side success is not evidence for the container.
- **One data source remains unproven.** `bulgaria-arbodat-lookup-options` is listed by the application but declares no data file. Whether that is intentional is unconfirmed and belongs in the limitations.
- **The production flip has its own owner and questions.** UAT ownership, the DNS and proxy repoint, and user migration are recorded in [PRODUCTION_FLIP_TO_AUTHORIZED_SERVER.md](../future/PRODUCTION_FLIP_TO_AUTHORIZED_SERVER.md), not here.
