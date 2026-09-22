# Phase 3 Task Plan: Validate Migration And Cutover Readiness

## Phase Summary

- **Document type:** Authorization migration and cutover-readiness task plan
- **Plan readiness:** Validated - most Phase 3 execution has already been completed on the test target; the remaining work is release-candidate evidence closeout and the target-content decision.
- **Source proposal:** [Centralized Authorization System](../done/MITIGATE_SECURITY_ISSUES/done/CENTRALIZED_AUTHORIZATION_SYSTEM.md)
- **Source phase plan:** [Centralized Authorization System Cutover Plan](./CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md) - [Phase 3: Validate Migration And Cutover Readiness](./CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md#phase-3-validate-migration-and-cutover-readiness)
- **Prerequisite plans:** [Phase 2 task plan](./done/CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PHASE_2_TASK_PLAN.md) and [Target Environment Configuration Layout task plan](./done/TARGET_ENVIRONMENT_CONFIGURATION_LAYOUT_TASK_PLAN.md)
- **Goal:** Close out test-environment readiness using the evidence already collected, confirm the final release identity, and resolve the target-content decision before treating the environment as ready for its current dataset.
- **Dependencies:** Phase 2 and Phase 2A are complete for the test target. The test-target handoff records migration, reconciliation, authenticated isolation, rollback, firewall, deployment-layout, and in-scope credential-rotation results. Release identity, evidence linkage, backup retention, and target-content disposition are now closed; the remaining item is the Phase 4 handoff owner.
- **Fixed constraints:** Do not change authorization policy during readiness validation. Do not modify project YAML or shared data to manufacture test coverage. Do not claim that absent reviewed content is available. Keep credentials out of logs and evidence files.

### Acceptance Criteria

1. `PH3-AC-1` (from `P-AC-4`) Focused authorization tests and the full backend regression suite pass on the final release candidate. **Status:** complete for the post-merge `dev` release image; both suites passed at the same revision the image was built from, and integrity plus reconciliation pass on the image.
2. `PH3-AC-2` (from `P-AC-5`) The applied manifest reconciles with zero missing administrators, resources, or grants. **Status:** completed for the test target on 2026-09-22.
3. `PH3-AC-3` (from `P-AC-5`) No required resource is unowned and no active locator conflict remains. **Status:** completed for the applied test-target records; the reviewed project and shared-data content is now provisioned, so no resource is unowned or pointing at absent content.
4. `PH3-AC-4` (from `P-AC-2`) Existing projects and shared resources have reviewed initial grants before enforcement. **Status:** complete. All 26 reviewed project locators resolve, all 6 reviewed shared data sources are listed by the application, and reconciliation against the reviewed manifest reports zero missing records.
5. `PH3-AC-5` (from `P-AC-6`) The backup passes integrity checking and its storage location is recorded. **Status:** complete; the retained backup path, checksum, and writable-copy integrity result are recorded.
6. `PH3-AC-6` (from `P-AC-7`) Access checks confirm permitted and denied outcomes for an administrator, a project owner, and a principal without grants. **Status:** complete for the recorded test-target checks; the administrator probe has not been rerun on the release image.

## Repository Findings

**Repository basis:** branch `authorization-system-cutover`; planning date 2026-09-22; existing move and documentation changes in the worktree were left untouched. The focused authorization baseline `uv run pytest backend/tests/authorization -q` passed with one existing skipped test. Shell syntax validation passed for the Phase 3 administration and verification scripts.

| Evidence | Finding | Planning implication |
| --- | --- | --- |
| `backend/tests/authorization/` | The focused authorization suite covers route authentication, dependencies, project access, cross-resource access, mutations, service access, and authorization operations. | Run this suite first on the release candidate and retain its result as `V-1` evidence. |
| `backend/tests/authorization/test_operations.py` | `backup_database`, `restore_database`, `integrity_check`, manifest inspection, dry-run, application, reconciliation, and export behavior have direct tests. | Use the existing operation tests as the regression baseline; add no new implementation unless a release-candidate check exposes a defect. |
| `backend/app/scripts/authorization.py` and `container/scripts/authorization.sh` | The CLI supports `migrate`, `reconcile`, `backup`, `restore`, `integrity-check`, `list-resources`, and `list-grants`; the wrapper runs the CLI inside the deployment container and keeps backups under `DATA_DIR/backups`. | Use the wrapper for target operations and record the manifest counts, backup path, integrity result, and reconciliation result. |
| `container/scripts/verify/run_deployment_verification.sh` | The verification orchestrator has already supported the successful test-target deployment and rollback checks; `--authenticated` records the two-principal isolation check and `--rollback` records restore and image identity. | Use the existing evidence as the baseline and rerun only if the final release identity is different or an evidence field is missing. |
| `container/scripts/verify/verify_authenticated_access.sh` | The check expects two non-administrator principals and two projects, then verifies unauthenticated `401`, allowed `200`, and concealed denied `404` responses through the proxy. | Use real reviewed projects when present; otherwise use the documented temporary-project path only to test enforcement and do not treat it as proof that the reviewed dataset is available. |
| `container/scripts/verify/rollback_exercise.sh` | Rollback restores a recorded image and SQLite backup, runs integrity and reconciliation checks, restarts with `--no-build`, and verifies health and image identity. | Preserve the backup and image identity until readiness acceptance and retain the rollback evidence directory. |
| [TEST_ENVIRONMENT_AUTHORIZATION_CUTOVER_HANDOFF.md](./TEST_ENVIRONMENT_AUTHORIZATION_CUTOVER_HANDOFF.md) | The test target has a three-directory layout, successful import and reconciliation, authenticated isolation, cleanup, rollback, firewall checks, external HTTPS reachability, and in-scope credential rotation. The reviewed projects and shared sources are now provisioned on the target. | Treat this as the primary Phase 3 evidence record. The release-linkage, backup-retention, and content-disposition gaps are closed; the administrator check has not been rerun on the release image. |
| [resources/authorization/test-initial-manifest.yaml](../../../resources/authorization/test-initial-manifest.yaml) | The reviewed manifest contains 3 administrators, 26 project resources with owner grants, and 6 shared-data-source resources with authenticated reader grants. | Compare the exact manifest revision and counts before and after migration; do not silently regenerate it. |
| `Makefile` | `make test` runs core, backend, and ingester suites; `make check-doc-links` validates repository documentation links. | Run the full regression command after the focused suite and run documentation checks when updating evidence. |

## Scope

**In scope**

- Identify and record the release candidate by source commit, image reference, image ID or digest, and configuration revision.
- Run the focused authorization suite and full backend regression suite on the release candidate.
- Inspect the reviewed manifest, perform a dry run, apply the manifest through the configured target wrapper, and reconcile the authorization store.
- Check resource ownership, locator conflicts, administrator assignments, and grant counts against the reviewed inventory.
- Create an integrity-checked authorization database backup in operator-controlled storage and record its path.
- Run unauthenticated, administrator, project-owner, and denied-principal access checks through the configured proxy.
- Preserve command output, timestamps, operator identity, image identity, manifest identity, backup identity, and known limitations in the cutover handoff.

**Out of scope**

- Designing or changing authorization policy, roles, resource locators, or grant assignments.
- Editing project YAML, shared data, or source datasets to make checks pass.
- Production or shared-environment enforcement cutover; those belong to later phases.
- PostgreSQL credential rotation on any PostgreSQL database, including the SEAD database. Decided on 2026-09-22 as an approved exception, so no PostgreSQL rotation check is performed and the pending `sead_ro` `.pgpass` item is closed as declined rather than failed.
- Replacing the existing Podman, systemd, nginx, or authorization implementation.

**Affected components**

- Release candidate image and deployment checkout under the target `container` directory.
- Target `config` and `container-data/state`, `container-data/backups`, and verification evidence directories.
- Authorization CLI, SQLite store, reviewed manifest, proxy access checks, and the Phase 3 evidence section of the cutover handoff.
- Existing backend authorization tests and the full repository regression suite.

## Work Breakdown

### Area 1: Close release-candidate evidence

**Objective:** Tie the already-completed test-target verification to the exact release candidate and fill the remaining regression evidence gap.

**Affected code:** `backend/tests/authorization/`, `backend/tests/`, `Makefile`, target image metadata, and the deployment verification options file.

**Dependencies:** Phase 2 and Phase 2A complete; target-content disposition recorded before final acceptance.

* [x] `T1.1` **Change:** Record and reconcile the post-merge `dev` release candidate identity.
  * **Target:** Existing target deployment record and verification options/evidence directory; update [TEST_ENVIRONMENT_AUTHORIZATION_CUTOVER_HANDOFF.md](./TEST_ENVIRONMENT_AUTHORIZATION_CUTOVER_HANDOFF.md).
  * **Current -> required:** Complete. The release image `shape-shifter:dev` is identified by image ID and source revision, its integrity check passes, and reconciliation against the reviewed manifest reports zero missing records.
  * **Implementation:** Recorded the `dev` image ID, source revision, `GIT_REF`, and manifest checksum, then reran `integrity-check` and `reconcile` on the new image; the baseline `d27b072c` identity is retained as history.
  * **Constraints:** Do not rebuild the current feature branch or claim final release-candidate parity before the post-merge `dev` image exists. Never record credential values.
  * **Validation:** `V-1`, `V-2`.
* [x] `T1.2` **Change:** Run focused authorization regression tests.
  * **Target:** `backend/tests/authorization/`.
  * **Current -> required:** Complete. The focused suite passed at `e38f4bc6` and again on `dev` at `dbff5ab95459652354c040b9d4fec6e2ead94f96`, the revision recorded on the release image, with one skipped test.
  * **Implementation:** Run `uv run pytest backend/tests/authorization -q` and retain the result with the release identity.
  * **Constraints:** Investigate failures against the release candidate; do not weaken tests or update policy to make the suite pass.
  * **Validation:** `V-1`.
* [x] `T1.3` **Change:** Attach the branch baseline full backend regression suite; rerun it for the post-merge `dev` release candidate.
  * **Target:** `backend/tests/`, `Makefile`, and the release candidate environment.
  * **Current -> required:** Complete. The full backend suite passed at `e38f4bc6` and again on `dev` at `dbff5ab95459652354c040b9d4fec6e2ead94f96`, which is the source revision recorded on the release image.
  * **Implementation:** `.venv/bin/pytest backend/tests -q` was rerun on `dev` after the merge; the handoff records the result with the existing skips and one JPype deprecation warning.
  * **Constraints:** Do not claim Phase 3 readiness if a release-related regression remains unexplained.
  * **Validation:** `V-3`.

**Completion evidence:** The release commit, image identity, manifest revision, and configuration revision are recorded; focused authorization tests and the full backend regression suite pass.

### Area 2: Close manifest and target-content evidence

**Objective:** Preserve the completed migration and reconciliation evidence, then decide whether the reviewed inventory is intended for this test target.

**Affected code:** `container/scripts/authorization.sh`, `backend/app/scripts/authorization.py`, `backend/app/authorization/operations.py`, the reviewed manifest, and the target SQLite store.

**Dependencies:** Area 1; the project/shared-data content disposition must be recorded before using `PH3-AC-4` as a passed criterion.

* [ ] `T2.1` **Change:** Confirm the target-content disposition before migration.
  * **Target:** `TEST_ENVIRONMENT_AUTHORIZATION_CUTOVER_HANDOFF.md`, target `config`, target `container-data/projects`, and target `container-data/shared`.
  * **Current -> required:** The reviewed manifest names 26 projects and 6 shared sources that are absent from the target. Record either the approved provisioning source and snapshot or the approved regenerated manifest and its review.
  * **Implementation:** Do not infer ownership or silently alter the manifest. If content is provisioned, verify its locators against the reviewed inventory. If policy is regenerated, rerun Phase 2 review and record the new manifest revision before applying it.
  * **Constraints:** No project YAML or shared data edits are allowed as a test workaround. This task is the execution gate for `PH3-AC-4`.
  * **Validation:** `V-4`.
* [x] `T2.2` **Change:** Run manifest dry-run and count validation.
  * **Target:** Reviewed manifest and target authorization CLI.
  * **Current -> required:** The manifest was dry-run validated and imported with 32 resources, 3 reviewed administrators, and 32 grants; the handoff has to link that result to the selected release candidate and target content disposition.
  * **Implementation:** Preserve the existing dry-run output and compare its manifest checksum and counts with the final handoff. Rerun only if the manifest or release changed.
  * **Constraints:** Dry-run must not mutate the database. Preserve the pre-migration database state and evidence.
  * **Validation:** `V-4`, `V-5`.
* [x] `T2.3` **Change:** Apply and reconcile the manifest.
  * **Target:** Target authorization SQLite store through `container/scripts/authorization.sh` and `backend/app/scripts/authorization.py`.
  * **Current -> required:** The test handoff records successful import, integrity, and zero-missing reconciliation. Phase 3 must link those results to the selected release and state their dataset limitation.
  * **Implementation:** Preserve the existing target evidence. Rerun `integrity-check` and `reconcile` only if the release, manifest, or authorization database changed; capture counts and the existing ownership/conflict result.
  * **Constraints:** Use the deployment user and configured `XDG_RUNTIME_DIR`; do not run against a guessed database path. Stop on any missing or conflicting active record.
  * **Validation:** `V-5`, `V-6`.

**Completion evidence:** The exact manifest passes dry-run, import and reconciliation report the expected counts and zero missing records, and the target store has no unowned reviewed resource or active locator conflict.

### Area 3: Close backup and access evidence

**Objective:** Reuse the completed rollback and proxy checks and record the backup-retention and administrator-access evidence.

**Affected code:** `container/scripts/authorization.sh`, `container/scripts/verify/verify_authenticated_access.sh`, `container/scripts/verify/run_deployment_verification.sh`, `container/scripts/verify/rollback_exercise.sh`, and the target proxy deployment.

**Dependencies:** Areas 1 and 2; two non-administrator test principals and two suitable projects must be available, or the temporary-project limitation must be recorded.

* [x] `T3.1` **Change:** Confirm the retained authorization database backup.
  * **Target:** Target `container-data/backups` and the Phase 3 evidence record.
  * **Current -> required:** The retained readiness backup is identified, checksummed, and passes integrity through the writable-copy procedure used by rollback.
  * **Implementation:** Preserve `authorization-20260922-110641.sqlite3`, its SHA-256 checksum, and its operator-controlled storage path in the handoff.
  * **Constraints:** Do not print database credentials or copy the backup to an uncontrolled location.
  * **Validation:** `V-7`.
* [x] `T3.2` **Change:** Close the access matrix evidence.
  * **Target:** `container/scripts/verify/verify_authenticated_access.sh`, nginx endpoint, two non-administrator principals, and two reviewed projects.
  * **Current -> required:** The test-target script passed with Bruno and Phil, and the separate administrator check returned HTTP 200 for `GET /api/v1/projects`.
  * **Implementation:** Preserve both results in the handoff; retain the temporary-project limitation until `T2.1` is resolved.
  * **Constraints:** Never use a bootstrap administrator as a denied principal. Passwords must be supplied through prompts or environment variables and must not enter evidence logs.
  * **Validation:** `V-8`.
* [x] `T3.3` **Change:** Review the non-mutating deployment verification evidence.
  * **Target:** `container/scripts/verify/run_deployment_verification.sh` and `DATA_DIR/deployment-verification/`.
  * **Current -> required:** The handoff contains successful dated live checks, including loopback health, port containment, authorization integrity, reconciliation, systemd ownership, firewall inspection, external HTTPS, authenticated isolation, and rollback.
  * **Implementation:** Review and link the existing report. Rerun the bundle only if the final release identity or required evidence differs from the recorded run.
  * **Constraints:** Do not include rollback in the read-only run; do not treat a warning about unavailable same-LAN testing as a passed network check unless the accepted exception is recorded.
  * **Validation:** `V-8`, `V-9`.

**Completion evidence:** An integrity-checked backup is retained at a recorded operator-controlled path, and the proxy access matrix records the expected `200`, `401`, and concealed `404` outcomes for the selected principals and resources.

### Area 4: Record test-target readiness and hand off

**Objective:** Consolidate existing test-target evidence and make the remaining limitation explicit so Phase 4 is not started on an ambiguous dataset.

**Affected code:** `docs/proposals/CENTRALIZED_AUTHORIZATION_CUTOVER/TEST_ENVIRONMENT_AUTHORIZATION_CUTOVER_HANDOFF.md`, the deployment-verification evidence directory, and the Phase 4 handoff fields in the master plan.

**Dependencies:** Areas 1-3 complete; no unresolved release, identity, resource, backup, or access-check failure.

* [x] `T4.1` **Change:** Update the cutover handoff with Phase 3 results.
  * **Target:** `docs/proposals/CENTRALIZED_AUTHORIZATION_CUTOVER/TEST_ENVIRONMENT_AUTHORIZATION_CUTOVER_HANDOFF.md`.
  * **Current -> required:** The handoff now contains the Phase 3 release, regression, manifest, reconciliation, backup, access, and target-content evidence; the image-parity and dataset gaps are closed, and the remaining limitations are explicit.
  * **Implementation:** Preserve the recorded release identity, test commands and results, manifest counts, reconciliation result, conflict/ownership result, backup path and integrity result, access matrix, target-content disposition, limitations, and reviewer/date.
  * **Constraints:** Do not record passwords, `.pgpass` contents, or unredacted command output containing secrets.
  * **Validation:** `V-9`, `V-10`.
* [x] `T4.2` **Change:** Confirm Phase 4 handoff readiness.
  * **Target:** Master cutover plan Phase 4 inputs and the Phase 3 handoff.
  * **Current -> required:** Complete. Phase 4 has a stored backup, a matching release identity, the reviewed manifest, access results, and a named rollback decision owner: Roger Mähler, recorded 2026-09-22, who also approves exceptions for unavailable checks.
  * **Implementation:** Each input is linked in the handoff, the rollback owner and exception decisions are named, and the accepted limitations are explicit. The `sead-options` connection and the release-image access checks remain recorded as limitations rather than failures.
  * **Constraints:** An absent target dataset, unexplained test failure, missing backup, or unmatched image identity blocks handoff.
  * **Validation:** `V-10`.

**Completion evidence:** The handoff is self-contained, links every evidence artifact, names the reviewer and rollback owner, and states whether Phase 4 may begin.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
| --- | --- | --- | --- |
| `PH3-AC-1` | `T1.1`, `T1.2`, `T1.3` | `V-1`, `V-2`, `V-3` | Exact release identity is recorded; focused authorization and full backend regression suites pass | Complete: release image revision matches the tested checkout, both suites pass at that revision, and integrity plus reconciliation pass on the release image |
| `PH3-AC-2` | `T2.2`, `T2.3` | `V-5`, `V-6` | Reviewed manifest applies and reconciliation reports zero missing administrators, resources, and grants | Complete for the test target |
| `PH3-AC-3` | `T2.1`, `T2.3` | `V-4`, `V-6` | Resource inventory has no unresolved active locator conflict and every reviewed resource has an owner or reader | Complete for applied records; content scope remains open |
| `PH3-AC-4` | `T2.1`, `T2.3`, `T3.2` | `V-4`, `V-6`, `V-8` | Target content disposition is approved; reviewed projects and shared sources have the recorded grants before enforcement | Complete: all 26 project locators resolve and all 6 shared data sources are listed by `GET /api/v1/data-sources` |
| `PH3-AC-5` | `T3.1` | `V-7` | Backup is integrity-checked, checksummed, retained, and stored at a recorded operator-controlled path | Complete: backup identity, checksum, path, and integrity result recorded |
| `PH3-AC-6` | `T3.2`, `T3.3` | `V-8`, `V-9` | Administrator, owner, denied-principal, and unauthenticated requests return the expected outcomes | Complete for recorded test-target access checks; reviewed-dataset availability remains open |

## Validation And Testing

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
| --- | --- | --- | --- | --- | --- |
| `V-1` | Focused authorization suite | `.venv/bin/pytest backend/tests/authorization -q` | `PH3-AC-1` | All collected tests pass; existing skipped tests remain explained | Passed during planning on 2026-09-22; one test skipped |
| `V-2` | Release identity inspection | `podman image inspect` and `podman container inspect` for the selected image/container; compare source revision label, image ID/digest, checkout revision, and manifest checksum | `PH3-AC-1` | Post-merge `dev` image matches the release candidate and reviewed manifest | `shape-shifter:dev`, image ID `6a487db722883da0eb0c3cfdc00444c07dea1edaf7d59b15643227576acc04a8`, OCI revision `dbff5ab95459652354c040b9d4fec6e2ead94f96` matching the merge commit; manifest checksum unchanged; baseline `d27b072c` retained |
| `V-3` | Full backend regression | `.venv/bin/pytest backend/tests -q` | `PH3-AC-1` | Full backend suite passes with no unexplained release-related failure on the post-merge `dev` image | Passed at `e38f4bc6` and rerun at the post-merge `dev` revision `dbff5ab95459652354c040b9d4fec6e2ead94f96`; existing skips and one JPype deprecation warning |
| `V-4` | Target-content and inventory gate | Compare target project/shared-data locators with [TEST_DEPLOYMENT_RESOURCE_INVENTORY.md](../../../secrets/TEST_DEPLOYMENT_RESOURCE_INVENTORY.md), record provision-or-regenerate decision, and compare against `list-resources --json` | `PH3-AC-3`, `PH3-AC-4` | Every required resource has a reviewed grant, or the approved regenerated manifest replaces the old inventory before migration | Verified: all 26 reviewed project locators resolve to a `shapeshifter.yml` and all 6 reviewed shared data sources are listed by the application; `sead-options` still depends on `SEAD_*` values from `config/backend.env` |
| `V-5` | Manifest dry-run and application | Review the existing CLI dry-run/import output; rerun against `$CONFIG_DIR/authorization-manifest.yaml` only if the manifest or release changed | `PH3-AC-2`, `PH3-AC-3` | Expected administrator/resource/grant counts are applied to the configured store | Complete on the test target; handoff records 32 resources, 3 administrators, and 32 grants |
| `V-6` | Integrity and reconciliation | Review the existing `authorization.sh integrity-check` and reconciliation output; rerun only after a relevant state change | `PH3-AC-2`, `PH3-AC-3`, `PH3-AC-4` | Integrity passes and reconciliation reports zero missing records; no active resource is unowned or conflicting | Complete on 2026-09-22 and rerun on the release image: integrity passed and reconciliation reported zero missing records |
| `V-7` | Backup and backup integrity | Review the rollback restore/integrity evidence, identify the retained backup, and record its checksum/path; create a new backup only if the existing artifact cannot be retained | `PH3-AC-5` | Backup is readable, integrity-checked, recoverable, and retained in operator-controlled storage | `authorization-20260922-110641.sqlite3` and the release-image backup `authorization-20260922-130050.sqlite3` are byte-identical at SHA-256 `9ebf2f22...8b3e`; writable-copy integrity result recorded |
| `V-8` | Authenticated access matrix | Review `verify_authenticated_access.sh` output for Bruno and Phil and the separate administrator probe | `PH3-AC-4`, `PH3-AC-6` | Unauthenticated `401`, allowed `200`, concealed denied `404`, and administrator access match the reviewed grants | Passed: Bruno/Phil isolation plus administrator `GET /api/v1/projects` HTTP 200; reviewed-content scope remains |
| `V-9` | Deployment verification evidence | Review the existing `run_deployment_verification.sh` evidence under `DATA_DIR/deployment-verification/`; rerun only if release identity differs | `PH3-AC-6` | Dated report records health, protected-route denial, authenticated outcomes, and limitations without secrets | Core live checks, rollback, firewall, external HTTPS, and credential rotation passed on 2026-09-22 against the baseline image; the release image answers health but has not repeated the container-level bundle |
| `V-10` | Handoff and Phase 4 readiness review | Manual review of the updated test handoff, evidence directory, backup identity, release identity, and rollback-owner decision; run `scripts/check_doc_links.sh` | All criteria and Phase 4 handoff | Every result is linked, limitations are explicit, and Phase 4 inputs are complete | Not run for this plan; handoff update is a planned deliverable |

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Release-candidate validation record | `TEST_ENVIRONMENT_AUTHORIZATION_CUTOVER_HANDOFF.md` and `DATA_DIR/deployment-verification/` | `T1.1`, `T1.2`, `T1.3`, `T4.1` | Source commit, image identity, tests, and warnings are recorded |
| Applied and reconciled authorization state | Target authorization SQLite store via `container/scripts/authorization.sh` | `T2.2`, `T2.3` | Manifest counts match and reconciliation reports zero missing records |
| Integrity-checked readiness backup | Target `container-data/backups/` and operator-controlled backup record | `T3.1` | Backup checksum, path, integrity result, and retention window are recorded |
| Access-readiness evidence | `DATA_DIR/deployment-verification/` and cutover handoff | `T3.2`, `T3.3` | Administrator, owner, denied-principal, and unauthenticated outcomes are recorded |
| Phase 4 handoff | `TEST_ENVIRONMENT_AUTHORIZATION_CUTOVER_HANDOFF.md` and master cutover plan references | `T4.1`, `T4.2` | Rollback owner, release identity, backup, manifest, and accepted limitations are linked |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Release-candidate evidence closeout | Done | Phase 2 and Phase 2A; merge to `dev` | Release image built from merged `dev`, identified, and rechecked: integrity passed, reconciliation reported zero missing, and a fresh backup matches the baseline backup byte for byte |
| Area 2: Manifest and target-content evidence | Done | Area 1 | Import, integrity, zero-missing reconciliation, all 26 project locators, and all 6 shared data sources verified, including the application's data source listing |
| Area 3: Backup and access evidence | Done | Areas 1-2 | Rollback, backup integrity, owner/denied isolation, administrator access, firewall, HTTPS, and credential rotation passed; the release image has not repeated the container-level bundle |
| Area 4: Test-target readiness handoff | Done | Areas 1-3 | Handoff records the release image, the provisioned content, and the named rollback and exception owner (Roger Mähler). The `sead-options` connection and the release-image access checks remain recorded as limitations |

## Definition Of Done

- [x] `PH3-AC-2` has a dry-run, applied manifest, integrity check, and reconciliation result reporting zero missing records for the test target.
- [x] `PH3-AC-3` has a recorded locator-conflict check and no unowned applied resource for the test target.
- [x] `PH3-AC-1` has focused authorization and full backend regression evidence tied to the post-merge `dev` release candidate.
- [x] `PH3-AC-4` has an approved target-content disposition and reviewed grants for the resources actually subject to enforcement.
- [x] `PH3-AC-5` has the already-tested backup's checksum, storage path, and retention owner recorded.
- [x] `PH3-AC-6` has administrator, project-owner, denied-principal, and unauthenticated access results recorded through the proxy.
- [x] The release identity, manifest revision, configuration revision, and evidence timestamps are recorded together.
- [x] The cutover handoff links every validation result and names the rollback decision owner.
- [x] Documentation links and shell syntax checks pass, and no credentials appear in evidence.
- [x] No unresolved failure or identity mismatch affects Phase 4 readiness.
- [x] The credential-rotation limitation is recorded: the check verifies labels only, PostgreSQL rotation is out of scope by the 2026-09-22 decision, and no rotated value is retained in the repository.

## Risks And Open Questions

- **Two shared data sources depend on configuration.** `bulgaria-arbodat-lookup-options` is accepted by the application even though it declares the `access` driver with no `filename`, and `sead-options` is listed with its `${SEAD_HOST}`, `${SEAD_PORT}`, `${SEAD_DBNAME}`, and `${SEAD_USER}` references stored verbatim. The application resolves those references from `config/backend.env` when the data source is used, so confirm the values and the matching `.pgpass` entry before relying on them.
- **Release drift.** A passing test or reconciliation result is invalid after the image, checkout, manifest, or target configuration changes. Record immutable identity for every run.
- **Administrator-count discrepancy.** The earlier handoff summary reported 2 administrators, while the reviewed manifest, applied role inventory, and detailed handoff facts report 3 (`admin`, `roger`, and `rebecka`). The summary and Phase 3 evidence now use the verified count of 3.
- **Temporary-project access evidence is limited.** The existing Bruno/Phil check proves enforcement and concealment but not access to the reviewed dataset. Keep that distinction in the handoff.
- **Backup retention.** Keep the readiness backup until Phase 4 acceptance or the rollback window closes; record the owner and location.
- **Same-LAN limitation.** The target is a virtual server with no second host on the target LAN. Preserve the accepted exception and compensating loopback, firewall, and external HTTPS checks.

**Open questions**

- Does `sead-options` connect? It is listed with `${SEAD_*}` references stored verbatim, so a successful connection is the only proof that `config/backend.env` and `.pgpass` supply working values. The other five are file-backed and verified by the application's listing.
- Which release will carry the accepted limitations into Phase 4? The rollback and exception owner is named; the remaining question is when the recorded limitations stop being acceptable.
