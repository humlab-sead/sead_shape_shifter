# Centralized Authorization System Cutover – Phase 4 Task Plan

- **Source proposal:** [Centralized Authorization System](../done/MITIGATE_SECURITY_ISSUES/done/CENTRALIZED_AUTHORIZATION_SYSTEM.md)
- **Source phase plan:** [Centralized Authorization System Cutover Plan](./CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md) - [Phase 4: Execute And Record Enforcement Cutover](./CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md#phase-4-execute-and-record-enforcement-cutover)
- **Prerequisite plans:** [Phase 3 task plan](./done/CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PHASE_3_TASK_PLAN.md), [Phase 2 task plan](./done/CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PHASE_2_TASK_PLAN.md), [Target Environment Configuration Layout task plan](./done/TARGET_ENVIRONMENT_CONFIGURATION_LAYOUT_TASK_PLAN.md)
- **Goal:** Enable the tested release on the named cutover target and preserve a repeatable rollback path, with the release, manifest, backup, and rollback outcome recorded.
- **Plan readiness:** Draft. The repository-side work is verified and executable, but the cutover target is an unresolved external decision. Every `<TARGET_*>` placeholder below resolves from that single decision, so the plan cannot be Validated until it is made.
- **Dependencies:** Phases 1–3 complete for the test target; a release image whose commit is recorded; the readiness backup retained; Roger Mähler named as the rollback decision owner.

## Acceptance Criteria

1. `PH4-AC-1` (from `P-AC-7`) The deployment record identifies the release, manifest, backup, and rollback decision owner.
2. `PH4-AC-2` (from `P-AC-7`) Post-deployment checks confirm expected administrator, owner, and denied-principal behavior.
3. `PH4-AC-3` (from `P-AC-7`) Authorization audit records exist for the migration and later administrative mutations.
4. `PH4-AC-4` (from `P-AC-8`) A rollback restores a valid authorization database, and reconciliation completes afterward.
5. `PH4-AC-5` (from `P-AC-1`, `P-AC-2`) An unclassified route, unowned resource, identity mismatch, or failed check blocks cutover instead of being accepted without review.

## Fixed Constraints

- **Enforcement has no toggle.** It follows from `TRUSTED_PROXY_AUTH_ENABLED`. `backend/app/core/config.py` refuses to start when `ENVIRONMENT=production` and that value is false, and refuses bootstrap when `AUTHORIZATION_BOOTSTRAP_ADMIN_PRINCIPALS` is empty in production. Cutover therefore means deploying a release whose runtime environment satisfies those settings, not flipping a switch.
- **The rollback backup captures state at backup time.** Grants added after the backup are lost on rollback. Take the recorded backup immediately before the cutover window and add no grants during it.
- Do not enable enforcement while any sensitive route or background operation remains unclassified.
- Do not modify project YAML to assign ownership or grants.
- Do not change authorization policy during cutover.
- Keep the readiness backup until the deployment is accepted or the rollback window closes.
- Record unresolved deployment facts as explicit blockers; do not infer principal ownership from filenames, project metadata, or request data.

## Repository Findings

**Repository basis:** branch `dev` at `4a74bc40`; planning date 2026-09-22; working tree clean. The test target's Phase 3 evidence is in [TEST_ENVIRONMENT_AUTHORIZATION_CUTOVER_HANDOFF.md](./TEST_ENVIRONMENT_AUTHORIZATION_CUTOVER_HANDOFF.md) and is the template for the cutover record.

| Evidence | Finding | Planning implication |
| --- | --- | --- |
| `backend/app/core/config.py::Settings._validate` | `TRUSTED_PROXY_AUTH_ENABLED` must be true in production; bootstrap administrators must be non-empty | Confirm both in `<CONFIG_DIR>/backend.env` before deploying, because the application will not start otherwise |
| `backend/app/core/config.py::Settings` | `TRUSTED_PROXY_AUTH_HEADER` (`X-Authenticated-User`), `TRUSTED_PROXY_GROUPS_ENABLED`, `TRUSTED_PROXY_GROUPS_HEADER`, `AUTHORIZATION_ALLOW_AUTHENTICATED_EVERYONE`, `AUTHORIZATION_DATABASE_PATH` | Reuse the test target's verified values; the database path must stay outside project, log, and shared-data directories |
| `backend/app/authorization/operations.py::apply_manifest` | Migration writes administrators, resources, and grants with actor `migration` | Provisioning events appear in the audit trail with actor `migration` |
| `backend/app/authorization/repository.py::_record_audit` | Records `bootstrap_admin_created`, `application_role_created`, `application_role_revoked`, `grant_created`, `grant_revoked`, `resource_lifecycle_changed` | `PH4-AC-3` is checkable through `list-audit-events`, not through log scraping |
| `backend/app/scripts/authorization.py::list_audit_events` | `list-audit-events` supports `--database` and `--json`, emitting `event_id`, `occurred_at`, `actor_principal_id`, `event_type`, `outcome`, `correlation_id`, `details` | Use `--json` and record the event count and actor distribution |
| `backend/app/scripts/authorization.py` | `inspect`, `migrate --dry-run`, `reconcile`, `backup`, `restore`, `integrity-check`, `list-resources`, `list-grants`, `list-audit-events`, `grant`, `revoke`, `grant-application-role`, `revoke-application-role` | All cutover store operations have a CLI entry point |
| `container/scripts/authorization.sh` | Wrapper runs the CLI inside the deployment container; convenience commands `backup`, `restore`, `import-manifest`, `export-manifest`; `--backup-dir` selects the host backup directory | Use the wrapper for target operations; it stages a host manifest into the container because migration reads it twice |
| `container/scripts/verify/rollback_exercise.sh` | Requires `--image`, `--authorization-backup`, `--manifest`; optional `--backup-dir`, `--evidence-dir`, `--container-name`, `--host-port`, `--yes`. Restores image and backup, then verifies integrity, reconciliation, image identity, and health; leaves the service stopped when a step fails | `PH4-AC-4` uses this script rather than a hand-run restore |
| `container/scripts/verify/verify_authenticated_access.sh` | Requires `--base-url`, `--principal-a`, `--principal-b`, `--project-a`, `--project-b`; expects unauthenticated `401`, allowed `200`, concealed denied `404`; requires each project granted to exactly one non-administrator principal | `PH4-AC-2` needs two reviewed projects with owners, or the temporary-project path with its limitation recorded |
| `backend/tests/authorization/test_route_authentication.py` | `test_route_inventory_matches_assembled_api_routes`, `test_route_inventory_matches_direct_and_mounted_routes`, `test_api_routes_are_classified` enforce `docs/AUTHORIZATION_ROUTE_INVENTORY.md` parity | These are the executable blocking checks for `PH4-AC-5` |
| `container/scripts/deploy/deploy_single_environment.sh` | Fetches `container/` for a ref, runs `scripts/setup.sh`, records `GIT_REPO`, `GIT_REF`, `IMAGE_NAME`, `HOST_PORT` in `CONFIG_DIR/deployment.env`; `--no-build` prepares files only | Deploying a recorded release is a two-step sequence so identity is confirmed before the container starts |
| `container/Makefile` | `make info`, `build`, `service-install`, `service-restart`, `service-status`, `healthcheck`, `logs`, `ps` | Service lifecycle and health checks use these targets |
| `container/DEPLOYMENT.md` | Host services must be reached as `host.docker.internal`; the container cannot reach the host's LAN address | Any credential or connection check that targets a host service must use the gateway alias, and host-side success is not evidence for the container |

## Scope

**In scope**

- Recording the cutover input set and freezing the release identity.
- Running the blocking pre-cutover checks.
- Deploying the recorded release with enforcement settings satisfied, provisioning the reviewed manifest, and reconciling.
- Post-deployment access checks and audit-trail review.
- Creating the post-cutover backup and recording integrity.
- Exercising rollback with the recorded image and backup.
- Writing the cutover record and updating the master plan status.

**Out of scope**

- Authorization policy design or grant changes.
- Route reclassification; Phase 1 owns the inventory.
- Deployment-model changes, host-service model selection, and the security record, which belong to Phase 5.
- PostgreSQL credential rotation, which is out of scope by decision.

**Affected components:** target `CONFIG_DIR` and `CONTAINER_DATA_DIR`, the deployment image and service unit, the authorization SQLite store, and the cutover documentation under `docs/proposals/CENTRALIZED_AUTHORIZATION_CUTOVER/`.

## Work Breakdown

### Area 1: Freeze the cutover inputs

**Objective:** The release, manifest, backup, and rollback owner are recorded and immutable before anything on the target changes.

**Affected code:** `<TARGET_CONFIG_DIR>` and the cutover record; no repository code.

**Dependencies:** The target environment decision.

**Tasks:**

* [ ] `T4.1` **Change:** Record the cutover input set against the target.
  * **Target:** Cutover record (new handoff in this folder, marked `NEW`); `<TARGET_CONFIG_DIR>/deployment.env`.
  * **Current → required:** The test target's inputs are recorded, but the target's own release, manifest, backup, and owner are not.
  * **Implementation:** Record the image reference and image ID, the `org.opencontainers.image.revision` label, the manifest path with its SHA-256, the readiness backup path with its SHA-256, and the rollback decision owner (Roger Mähler). Read `make info` for the configured `GIT_REF` and `IMAGE_NAME`.
  * **Constraints:** Record identifiers only; never record credential values or `.pgpass` contents.
  * **Validation:** `V-4.1`, `V-4.2`.
* [ ] `T4.2` **Change:** Confirm the target runtime environment satisfies the production settings validator.
  * **Target:** `<TARGET_CONFIG_DIR>/backend.env`.
  * **Current → required:** Values are unverified for the target; the application refuses to start in production without trusted-proxy authentication and a bootstrap administrator.
  * **Implementation:** Confirm `TRUSTED_PROXY_AUTH_ENABLED=true`, the header names, `TRUSTED_PROXY_GROUPS_ENABLED` where groups are granted, `AUTHORIZATION_BOOTSTRAP_ADMIN_PRINCIPALS`, `AUTHORIZATION_ALLOW_AUTHENTICATED_EVERYONE` where the manifest grants `everyone`/`authenticated`, and that `AUTHORIZATION_DATABASE_PATH` resolves outside project, log, and shared-data directories. Confirm names only when reporting.
  * **Constraints:** Do not change policy or grant values here; this task only confirms settings required for startup.
  * **Validation:** `V-4.3`.

**Completion evidence:** Every cutover input is recorded with an immutable identifier, and the target's startup settings are confirmed.

### Area 2: Run the blocking pre-cutover checks

**Objective:** Prove that no route is unclassified, no resource is unowned, and the audit trail exists before enforcement is enabled.

**Affected code:** `backend/tests/authorization/test_route_authentication.py`, `docs/AUTHORIZATION_ROUTE_INVENTORY.md`, target authorization store.

**Dependencies:** Area 1.

**Tasks:**

* [ ] `T4.3` **Change:** Run the route-inventory and classification checks against the release revision.
  * **Target:** `backend/tests/authorization/test_route_authentication.py`.
  * **Current → required:** The checks pass on `dev`; the release revision must pass them too.
  * **Implementation:** Run `backend/tests/authorization/test_route_authentication.py` at the release revision and retain the result. A runtime route absent from the inventory, or an inventory row absent from the runtime, fails the check.
  * **Constraints:** Do not edit the inventory to pass the check; a mismatch blocks cutover and is recorded as such.
  * **Validation:** `V-4.4`.
* [ ] `T4.4` **Change:** Review resources and grants for unowned or conflicting records.
  * **Target:** Target authorization store through `container/scripts/authorization.sh`.
  * **Current → required:** The test target was reviewed; the cutover target is unreviewed.
  * **Implementation:** Run `list-resources --json` and `list-grants --json`, and confirm every active resource has at least one owner or reader grant, and no active resource has a conflicting locator. Record counts and any exception.
  * **Constraints:** Resolve conflicts by correcting configuration, never by editing project YAML to create ownership.
  * **Validation:** `V-4.5`.
* [ ] `T4.5` **Change:** Confirm the audit trail exists for migration and later mutations.
  * **Target:** Target authorization store through `container/scripts/authorization.sh list-audit-events --json`.
  * **Current → required:** The audit table exists, but the target's event coverage is unverified.
  * **Implementation:** Run `list-audit-events --json` and confirm events with actor `migration` for provisioning, plus any later administrative mutations. Record the event count and the observed `event_type` distribution.
  * **Constraints:** Treat a missing migration audit record as a blocker, not a documentation gap.
  * **Validation:** `V-4.6`.

**Completion evidence:** All three blocking checks pass, or the failing check is recorded as a cutover blocker with its owner.

### Area 3: Execute the cutover and record the state

**Objective:** The recorded release runs on the target with the reviewed manifest applied and enforcement active, and the resulting state is captured.

**Affected code:** Target deployment directories, service unit, authorization store.

**Dependencies:** Areas 1–2.

**Tasks:**

* [ ] `T4.6` **Change:** Deploy the recorded release to the target.
  * **Target:** `<TARGET_HOME>/container`, systemd user unit `shape-shifter`.
  * **Current → required:** The target runs an earlier revision.
  * **Implementation:** Refresh deployment files for the recorded ref, run `make build`, then `make service-install` and `make service-restart`. Capture `make info`, the image ID, and the revision label, and confirm they match the recorded input set from `T4.1`.
  * **Constraints:** Confirm the image identity before accepting the deployment; an unmatched revision stops the cutover. When acting as the deployment user through `sudo -i`, export `XDG_RUNTIME_DIR=/run/user/<uid>` and `DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/<uid>/bus` or `systemctl --user` fails.
  * **Validation:** `V-4.7`.
* [ ] `T4.7` **Change:** Apply the reviewed manifest and reconcile.
  * **Target:** `<TARGET_CONFIG_DIR>/authorization-manifest.yaml`, target authorization store.
  * **Current → required:** The store may not match the reviewed manifest.
  * **Implementation:** Inspect the manifest, apply it with `import-manifest`, then run `reconcile` and `integrity-check`. Record the applied counts and the reconciliation summary.
  * **Constraints:** Do not edit the manifest to make reconciliation pass, and add no grants before the rollback backup is taken.
  * **Validation:** `V-4.8`.
* [ ] `T4.8` **Change:** Run post-deployment access checks.
  * **Target:** Proxy endpoint for the target environment.
  * **Current → required:** Access behavior is unverified on the target.
  * **Implementation:** Run `verify_authenticated_access.sh` with two reviewed projects and their principals, confirming unauthenticated `401`, allowed `200`, and concealed denied `404`. Add the administrator probe for a protected list route. Where reviewed projects have no owner yet, use the temporary-project path and record that it proves enforcement rather than dataset availability.
  * **Constraints:** Do not grant ownership to make a check pass; a denied result that should be allowed is a blocker.
  * **Validation:** `V-4.9`.
* [ ] `T4.9` **Change:** Create the post-cutover backup and record its integrity.
  * **Target:** `<TARGET_DATA_DIR>/backups`.
  * **Current → required:** The readiness backup predates the cutover.
  * **Implementation:** Run `container/scripts/authorization.sh backup`, record the path and SHA-256, and confirm the backup opens and passes an integrity check without being modified in place.
  * **Constraints:** Verify a copy when the check needs a writable database; never open the retained backup directly.
  * **Validation:** `V-4.10`.

**Completion evidence:** The running image revision matches the recorded input set, reconciliation reports zero missing records, access checks return the expected statuses, and a post-cutover backup is recorded.

### Area 4: Exercise rollback

**Objective:** The documented rollback restores a valid authorization database and the release, and the outcome is recorded.

**Affected code:** `container/scripts/verify/rollback_exercise.sh`.

**Dependencies:** Areas 1–3.

**Tasks:**

* [ ] `T4.10` **Change:** Exercise rollback with the recorded image, backup, and manifest.
  * **Target:** `container/scripts/verify/rollback_exercise.sh`, run as the deployment user from `<TARGET_HOME>/container`.
  * **Current → required:** Rollback was exercised on the test target; the cutover target's rollback is unverified.
  * **Implementation:** Run the script with `--image`, `--authorization-backup`, `--manifest`, and `--evidence-dir`, then confirm it restored the image, passed integrity and reconciliation, and returned health `200`. Record the evidence directory. Redeploy the cutover release afterward if the target must keep it.
  * **Constraints:** The script leaves the service stopped when a step fails; do not proceed past a failed rollback without the rollback owner's decision. State the ownership window that the restore discards.
  * **Validation:** `V-4.11`.

**Completion evidence:** Rollback completes with integrity and reconciliation passing, or the failure is recorded with the rollback owner's decision.

### Area 5: Record the cutover and hand off

**Objective:** The cutover outcome, exceptions, and rollback result are recorded, and Phase 5 has its inputs.

**Affected code:** Cutover record document; `docs/proposals/CENTRALIZED_AUTHORIZATION_CUTOVER/CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md`.

**Dependencies:** Areas 1–4.

**Tasks:**

* [ ] `T4.11` **Change:** Write the cutover record and update the plan status.
  * **Target:** The cutover record created in `T4.1`; the master plan status line.
  * **Current → required:** The master plan still shows Phase 4 as not started, and no cutover record exists for the target.
  * **Implementation:** Record the release and image digest, manifest revision and checksum, backup path and checksum, access results, audit-event summary, rollback outcome, exceptions with owners, and the validation results. Update the master plan status to record Phase 4 complete and Phase 5 ready.
  * **Constraints:** Record limitations as limitations; do not present an unverified check as passed. Keep credentials and `.pgpass` contents out of the record.
  * **Validation:** `V-4.12`.

**Completion evidence:** The cutover record is self-contained, every validation result is linked, and the master plan reflects the outcome.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
| --- | --- | --- | --- |
| `PH4-AC-1` | `T4.1`, `T4.7`, `T4.9` | `V-4.1`, `V-4.2`, `V-4.8`, `V-4.10` | Release, manifest, backup, and owner recorded with immutable identifiers |
| `PH4-AC-2` | `T4.8` | `V-4.9` | Administrator, owner, denied-principal, and unauthenticated outcomes recorded |
| `PH4-AC-3` | `T4.5` | `V-4.6` | Migration and mutation audit events recorded with counts and types |
| `PH4-AC-4` | `T4.10` | `V-4.11` | Rollback restores the image and database, integrity passes, reconciliation is zero-missing |
| `PH4-AC-5` | `T4.3`, `T4.4` | `V-4.4`, `V-4.5` | Route inventory and classification checks pass, and no active resource is unowned or conflicting |

## Validation And Testing

| ID | Check and target | Command or method | Covers | Expected result |
| --- | --- | --- | --- | --- |
| `V-4.1` | Release identity | `podman image inspect <image> --format '{{.Id}}'` and the `org.opencontainers.image.revision` label | `PH4-AC-1` | The recorded revision equals the ref that was built |
| `V-4.2` | Configured deployment values | `make info` in `<TARGET_HOME>/container` | `PH4-AC-1` | `GIT_REF` and `IMAGE_NAME` agree with the recorded release |
| `V-4.3` | Startup settings | Inspect the settings validator path in `backend/app/core/config.py::Settings` against `<TARGET_CONFIG_DIR>/backend.env` | `PH4-AC-1` | Trusted-proxy authentication is enabled and a bootstrap administrator is configured |
| `V-4.4` | Route inventory and classification | `.venv/bin/pytest backend/tests/authorization/test_route_authentication.py -q` at the release revision | `PH4-AC-5` | All checks pass; no unclassified or undocumentable route |
| `V-4.5` | Resource ownership | `container/scripts/authorization.sh list-resources --json` and `list-grants --json` | `PH4-AC-5` | Every active resource has a grant; no active locator conflict |
| `V-4.6` | Audit trail | `container/scripts/authorization.sh list-audit-events --json` | `PH4-AC-3` | Migration events with actor `migration` plus later mutation events are present |
| `V-4.7` | Deployed image identity | `podman image inspect` and `podman container inspect` for the running container | `PH4-AC-1` | Running container uses the recorded image and revision |
| `V-4.8` | Manifest application and reconciliation | `import-manifest`, `reconcile`, `integrity-check` through `container/scripts/authorization.sh` | `PH4-AC-1` | Applied counts match the reviewed manifest and reconciliation reports zero missing records |
| `V-4.9` | Post-deployment access checks | `container/scripts/verify/verify_authenticated_access.sh` plus an administrator probe | `PH4-AC-2` | Unauthenticated `401`, allowed `200`, concealed denied `404`, administrator `200` |
| `V-4.10` | Backup and integrity | `container/scripts/authorization.sh backup`, then checksum and integrity verification on a copy | `PH4-AC-1` | Backup recorded with path and checksum, integrity passes |
| `V-4.11` | Rollback exercise | `container/scripts/verify/rollback_exercise.sh --image --authorization-backup --manifest --evidence-dir` | `PH4-AC-4` | Image and database restored, integrity passes, reconciliation zero-missing, health `200` |
| `V-4.12` | Cutover record review | Manual review of the cutover record, then `scripts/check_doc_links.sh` and `git diff --check` | All criteria | Every result linked, limitations explicit, no credential values present |

**Phase milestone mapping:** `VM-4.1` is covered by `V-4.1`, `V-4.2`, `V-4.7`, `V-4.8`, and `V-4.10`; `VM-4.2` by `V-4.6` and `V-4.9`; `VM-4.3` by `V-4.11`; `VM-4.4` by `V-4.4` and `V-4.5`.

## Deliverables

| Deliverable | Description | Status | Link |
| --- | --- | --- | --- |
| Cutover record | Release, manifest, backup, owner, access results, audit summary, rollback outcome, exceptions | Not started | `<TARGET_ENVIRONMENT>_AUTHORIZATION_CUTOVER_HANDOFF.md` (name follows the environment) |
| Blocking-check evidence | Route inventory, ownership, and audit results | Not started | Cutover record |
| Rollback evidence | Transcript directory from the rollback exercise | Not started | `<TARGET_DATA_DIR>/backups/rollback-<timestamp>` |
| Post-cutover backup | Timestamped authorization backup with checksum | Not started | `<TARGET_DATA_DIR>/backups` |
| Master plan status update | Phase 4 complete, Phase 5 ready | Not started | [CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md](./CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md) |

## Progress Tracker

| Area | Status | Notes |
| --- | --- | --- |
| Area 1: Freeze the cutover inputs | Not started | Requires the target environment decision |
| Area 2: Run the blocking pre-cutover checks | Not started | Depends on Area 1 |
| Area 3: Execute the cutover and record the state | Not started | Depends on Areas 1–2 |
| Area 4: Exercise rollback | Not started | Depends on Areas 1–3 |
| Area 5: Record the cutover and hand off | Not started | Depends on Areas 1–4 |

## Definition Of Done

- [ ] `PH4-AC-1` has the release image, revision, manifest revision, backup path and checksum, and rollback owner recorded together.
- [ ] `PH4-AC-2` has post-deployment administrator, owner, denied-principal, and unauthenticated results recorded.
- [ ] `PH4-AC-3` has migration and administrative-mutation audit events recorded with counts and types.
- [ ] `PH4-AC-4` has a rollback result with integrity and reconciliation outcomes, or a recorded rollback-owner decision.
- [ ] `PH4-AC-5` has route-inventory, classification, and ownership check results recorded, with any blocker named.
- [ ] The cutover record links every validation result and states the accepted limitations.
- [ ] `scripts/check_doc_links.sh` and `git diff --check` pass, and no credential values appear in the record.
- [ ] The master plan status reflects the Phase 4 outcome.

## Risks And Open Questions

- **The cutover target is undecided.** This is the only blocker to Validated readiness. It determines `<TARGET_HOME>`, `<TARGET_CONFIG_DIR>`, `<TARGET_DATA_DIR>`, the deployment user, the proxy host, the manifest instance, and the record's filename. Every `<TARGET_*>` placeholder resolves from it.
- **Rollback discards later grants.** The recorded backup captures state at backup time, so ownership and grants added after it are lost on restore. Sequence cutover so no grant is added between the backup and the end of the rollback window.
- **Reviewed projects may have no owners on the target.** `verify_authenticated_access.sh` needs projects each granted to exactly one non-administrator principal. Where the reviewed projects lack owners, the temporary-project path proves enforcement but not dataset availability, and that distinction must be recorded.
- **Host services are reachable only through the gateway alias.** Container-side connection checks to a host database must use `host.docker.internal`; a successful host-side check is not evidence for the container.
- **A failed check must block, not be accepted.** `PH4-AC-5` is explicit: unclassified routes, unowned resources, identity mismatches, and failed checks block cutover rather than being waived in the record.
- **Phase 5 depends on this record.** Its inputs are the release identity, service definition, mounts, exposure, and rollback result, so an incomplete record defers Phase 5 rather than being worked around there.
