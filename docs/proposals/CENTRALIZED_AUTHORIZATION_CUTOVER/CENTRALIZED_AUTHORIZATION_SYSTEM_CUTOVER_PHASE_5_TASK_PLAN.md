# Centralized Authorization System Cutover – Phase 5 Task Plan

- **Source proposal:** [Centralized Authorization System](../done/MITIGATE_SECURITY_ISSUES/done/CENTRALIZED_AUTHORIZATION_SYSTEM.md)
- **Source phase plan:** [Centralized Authorization System Cutover Plan](./CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md) - [Phase 5: Verify Podman Deployment And Update Security Record](./CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md#phase-5-verify-podman-deployment-and-update-security-record)
- **Prerequisite records:** [UAT-ready deployment record](./done/UAT_READY_AUTHORIZATION_DEPLOYMENT_HANDOFF.md), [Podman deployment verification handoff](./DEPLOYMENT_VERIFICATION_HANDOFF.md), [test environment cutover handoff](./TEST_ENVIRONMENT_AUTHORIZATION_CUTOVER_HANDOFF.md)
- **Related, not required:** [Release Cycle Evidence And Locking](../RELEASE_CYCLE_EVIDENCE_AND_LOCKING/README.md). That proposal owns evidence tooling, result locking, and run deltas. This phase uses the scripts that exist and does not wait for it.
- **Goal:** Verify the authorization release in the Podman deployment and record security results for that release.
- **Plan readiness:** Validated. Every command below exists in the repository or in the recorded operator output. The release unit is frozen and its identity is confirmed on the host. One dependency sits outside the plan: whether an operator with the principal passwords is available.
- **Dependencies:** Phases 1–4 complete; the frozen release unit decided; Roger Mähler named as the rollback decision owner.

## Acceptance Criteria

1. `PH5-AC-1` (from `P-AC-9`) The recorded source commit and image digest match the running Podman container.
2. `PH5-AC-2` (from `P-AC-9`) The backend port is published on loopback only, and proxy and firewall checks show no untrusted direct access.
3. `PH5-AC-3` (from `P-AC-9`) Proxy identity-header handling, health behavior, allowed access, denied access, and cross-resource isolation pass after deployment.
4. `PH5-AC-4` (from `P-AC-9`) Secrets, mounts, environment variables, PostgreSQL grants, authorization database placement, and logs meet the approved security rules without credential disclosure.
5. `PH5-AC-5` (from `P-AC-8`) Backup integrity, restore and reconciliation, and application rollback checks pass, or a reviewed exception records the failed check and release disposition.
6. `PH5-AC-6` (from `P-AC-10`) `SECURITY_CHECK.md` records the tested commit, image digest, results, limitations, and approved exceptions for each finding.

## Fixed Constraints

- **The image identity is confirmed and carries a locally computed manifest digest.** Planning assumed a locally built image would have no digest and that the image ID would stand in for one. The host reports `localhost/shape-shifter@sha256:7ff51b2b…`, so no substitute is needed. The identity is the image ID `6a487db7…04a8`, the manifest digest `sha256:7ff51b2b…`, and the OCI `revision` label `dbff5ab9…4f96`. The `localhost/` prefix shows the image was never pushed, so nothing outside the host vouches for the manifest and a digest computed elsewhere is not guaranteed to match; the `revision` label is the identity that travels across hosts. `PH5-AC-1` is satisfied by the commit and the manifest digest, both matching the running container.
- **The release unit is frozen before any check runs.** Record the source commit, image identity, manifest revision and checksum, configuration revision, and deployment target first. Do not rebuild the image, edit the manifest, or change the deployment layout while the phase runs. Reopening the release unit invalidates every result already recorded for it.
- **Results do not carry across image identities.** A result recorded for one image carries no weight for another. Cite a prior result only when the frozen identity matches the one that result was recorded against; otherwise re-run the check.
- **This phase is trimmed to its delta.** Checks whose last result was recorded against the frozen identity are cited, not repeated. Re-running an already-satisfied check is not required by this plan.
- **No new tooling in this phase.** Evidence capture, result locking, and delta reporting belong to the release-cycle proposal. Capture evidence with the existing scripts and explicit redirection into a phase evidence directory.
- **Record identifiers only.** Never record credential values, `.pgpass` contents, or Basic-auth passwords. The authenticated check prompts for passwords; they are never passed as arguments or written to a file.
- **Do not change authorization policy, grants, route classification, or deployment layout.** The deferred cleanups in the Phase 4 record — the orphan `verification-containment-*` resources and the `bulgaria-arbodat-lookup-options` records — stay deferred.
- **Keep the deployment available.** Stop it only inside the approved rollback window, and restore supervision afterwards.

## Repository Findings

**Repository basis:** branch `dev` at `54c05d0d`; planning date 2026-09-22. The deployment under record is the authorization-enabled instance: host `humlabsead`, deployment user `test-shape-shifter.sead.se` (uid/gid 1021), container `shape-shifter` on `127.0.0.1:8012`, proxy `https://test-shape-shifter.sead.se`, data directory `/data/test-shape-shifter.sead.se/container-data`.

| Evidence | Finding | Planning implication |
| --- | --- | --- |
| Host read 2026-09-22 | `make info`, `config/deployment.env`, `sha256sum` on the deployed manifest, and `podman image inspect` returned image ID `6a487db7…04a8`, manifest digest `localhost/shape-shifter@sha256:7ff51b2b…`, OCI revision `dbff5ab9…4f96`, and a deployed manifest checksum identical to the reviewed copy | The frozen release unit equals the image Phase 4 verified, so those results stay citable and this phase keeps its small delta |
| [UAT_READY_AUTHORIZATION_DEPLOYMENT_HANDOFF.md](./done/UAT_READY_AUTHORIZATION_DEPLOYMENT_HANDOFF.md) | Records image `shape-shifter:dev`, image ID `6a487db7…04a8`, revision `dbff5ab9…4f96`, manifest SHA-256 `43c03186…fb90`, 144 audit events, 36 active resources, 53 grants, and a passing rollback exercise at 16:48:11 with reconciliation `Missing: 0 resources, 0 administrators, 0 grants` | These are the results to cite when the frozen image identity matches. The record states an image ID, not a registry digest |
| [DEPLOYMENT_VERIFICATION_HANDOFF.md](./DEPLOYMENT_VERIFICATION_HANDOFF.md) | The 2026-09-18 run `20260918T210002Z-3878349` verified firewall, port publication, proxy denial, container configuration, PostgreSQL grants, authorization database placement, and endpoint containment; the host-log review failed and is tracked as a non-blocking GitHub issue. That run recorded baseline commit `95c3d017` and digest `sha256:aa320c4c…` | Those results describe a different image, so they cannot be cited for the frozen unit. The host-log review is the one security check still open |
| `container/scripts/verify/run_deployment_verification.sh` | Orchestrator. Writes `summary.txt`, one `<check>.log` per check, and a copy of the options file into a timestamped directory under `<DATA_DIR>/deployment-verification/`. Runs firewall, container configuration, PostgreSQL grants, log, credential, and endpoint-containment checks; authenticated access and rollback are opt-in via `--authenticated` and `--rollback` | This is the closest thing to a single capture entry point. It reads no image digest and no authorization inventory |
| `container/scripts/verify/verify_container_config.sh` | Inspects the running container's published ports, mounts, environment variable names, image labels, and image history. It does not read `RepoDigests` | The image identity task cannot be delegated to this script; read the digest explicitly |
| `container/scripts/verify/verify_authenticated_access.sh` | Accepts `--base-url`, `--principal-a`, `--principal-b`, `--project-a`, `--project-b`, `-h`. Has no evidence-directory option, so output must be redirected. The corrected version reads the principals' deployment roles and reports how many isolation directions were verified | Redirecting its output into the phase evidence directory is the whole capture mechanism; no new tooling is needed |
| `container/scripts/verify/rollback_exercise.sh` | Accepts `--image`, `--authorization-backup`, `--manifest`, `--backup-dir`, `--evidence-dir`, `--container-name`, `--host-port`, `--yes`. Leaves the service stopped when a step fails | Rollback evidence can be filed directly. Restore supervision with `make service-restart` afterwards |
| `container/scripts/authorization.sh` | Wrapper for the store CLI: `backup`, `restore`, `import-manifest`, `export-manifest`, `list-audit-events`, `list-resources`, `list-grants`, `list-application-roles`, `integrity-check`, `reconcile` | The authorization evidence set is available and was collected by hand in Phase 4 |
| `container/scripts/deploy/install_nginx_reverse_proxy.sh` | Writes the site to `/etc/nginx/sites-available/<domain>`, symlinks it into `sites-enabled`, then runs `nginx -t` and reloads | The deployed proxy configuration is inspectable at that path, and `nginx -T` prints the effective configuration |
| `container/scripts/deploy/nginx-shape-shifter.conf.template` | Sets `proxy_set_header X-Authenticated-User $remote_user;` | The overwrite behavior that `PH5-AC-3` requires can be confirmed against the deployed site and the effective configuration |
| `backend/app/middleware/proxy_auth.py`, `backend/app/core/config.py` | `ProxyAuthenticationMiddleware` requires a non-empty identity header, whose name is the `TRUSTED_PROXY_AUTH_HEADER` setting (default `X-Authenticated-User`). It does not check the source address | Record the header-overwrite evidence and repeat the standing limitation: a local process can still assert an identity |
| `backend/tests/authorization/test_route_authentication.py` | Enforces parity between the assembled FastAPI routes and `docs/AUTHORIZATION_ROUTE_INVENTORY.md` | Running this module is the executable route-classification check for the frozen revision |
| `docs/proposals/done/MITIGATE_SECURITY_ISSUES/SECURITY_CHECK.md` | Existing security record for this project | The update target for `PH5-AC-6`. Its report structure already carries a tested commit, results, and limitations |
| `docs/OPERATIONS.md` section *Release, Verification, And Rollback* | Documents selecting a ref in `~/config/deployment.env`, `make build`, `make restart`, the fields to record, firewall and container-configuration verification, and rollback | The operator procedures used in this phase are the documented ones |

**Prior runs and what they cover.** Three verification passes exist. The 2026-09-15 and 2026-09-18 passes ran against baseline `95c3d017` with digest `sha256:aa320c4c…`. The 2026-09-22 pass ran against image ID `6a487db7…04a8` with revision `dbff5ab9…4f96` and covered identity, route inventory, resource and grant inventory, audit coverage, access checks, and a rollback exercise. Only the last of these can be cited for a frozen unit equal to that image.

## Scope

**In scope**

- Freezing the release unit and recording its identity.
- Re-running the checks the frozen identity invalidates: exposure, container configuration, PostgreSQL grants and authorization database placement, proxy identity-header handling, access checks, and route classification.
- Recording the image ID, the manifest digest, and the OCI labels as the frozen unit's identity.
- Closing or recording a disposition for the outstanding host-log review.
- Updating `SECURITY_CHECK.md` with the tested commit, identity, results, limitations, and approved exceptions.

**Out of scope**

- Evidence tooling, result locking, and run deltas; owned by [Release Cycle Evidence And Locking](../RELEASE_CYCLE_EVIDENCE_AND_LOCKING/README.md).
- Building or rebuilding the image, changing the deployment layout, or selecting the production Podman service model.
- Authorization policy, grants, route reclassification, and the deferred cleanups.
- The production flip to the authorized server.
- PostgreSQL credential rotation, which is out of scope by decision for every PostgreSQL database.

**Affected components:** the deployment's container and image identity, `/etc/nginx/sites-available/test-shape-shifter.sead.se`, the authorization SQLite store, the systemd user unit, `docs/proposals/done/MITIGATE_SECURITY_ISSUES/SECURITY_CHECK.md`, and a new deployment record in this folder.

## Work Breakdown

### Area 1: Freeze the release unit and record its identity

**Objective:** The release unit is frozen and identified by values that cannot change underneath a recorded result.

**Affected code:** New deployment record in this folder; `<CONFIG_DIR>/deployment.env`; the running container and image.

**Dependencies:** None.

**Tasks:**

* [x] `T5.1` **Change:** Freeze the release unit and record the deployment target.
  * **Target:** Deployment record (`PODMAN_DEPLOYMENT_RECORD.md`, new, in this folder).
  * **Current -> required:** The Phase 4 record captures identity for acceptance; this phase needs identity frozen as a precondition, with the commitment not to rebuild or reconfigure during the phase.
  * **Implementation:** Record the source commit, `GIT_REF`, `IMAGE_NAME`, the manifest path and SHA-256, the configuration directory and data directory, host, deployment user, container name, published port, and proxy hostname. State that the image is not rebuilt and the layout is not changed for the duration of the phase.
  * **Constraints:** Record identifiers only. Do not record credential values.
  * **Validation:** `V-5.1`. Complete 2026-09-22 in [PODMAN_DEPLOYMENT_RECORD.md](./PODMAN_DEPLOYMENT_RECORD.md): the source commit `dbff5ab9…4f96`, the unchanged application code and tests at that revision, the reviewed manifest checksum `43c03186…fb90`, and the deployment target from `make info` and `config/deployment.env` are recorded. The deployed manifest checksum matches the reviewed copy.
* [x] `T5.2` **Change:** Record the immutable image identity.
  * **Target:** Deployment record.
  * **Current -> required:** `PH5-AC-1` requires a source commit and an image digest. No registry is configured, so no manifest digest exists; the identity must be recorded explicitly and its limitation stated.
  * **Implementation:** As the deployment user, read `podman image inspect --format '{{.Id}}'`, `{{json .RepoDigests}}`, and the `org.opencontainers.image.revision`, `.version`, and `.source` labels for the frozen image, and confirm the image ID matches the one the running container uses. Record the image ID, the manifest digest, and the labels, and state that the digest is computed locally because the image was never pushed.
  * **Constraints:** Do not push the image to a registry in this phase. Do not treat a tag as identity. State the digest's local provenance wherever the identity is cited.
  * **Validation:** `V-5.2`. Complete 2026-09-22: the host returned image ID `6a487db7…04a8`, the manifest digest `localhost/shape-shifter@sha256:7ff51b2b…` from `.RepoDigests`, and the OCI `revision` label `dbff5ab9…4f96`; the running container uses the same image ID. `.RepoDigests` was not empty, contrary to the plan's assumption, so no substitute identity is needed. Recorded in [PODMAN_DEPLOYMENT_RECORD.md](./PODMAN_DEPLOYMENT_RECORD.md).

**Completion evidence:** The deployment record states every release-unit field, records the image ID, the manifest digest, and the OCI labels as the identity, and states that the digest was computed locally.

### Area 2: Re-verify exposure, container configuration, and grants

**Objective:** The image-dependent security checks pass against the frozen unit.

**Affected code:** `container/scripts/verify/verify_firewall.sh`, `verify_container_config.sh`, `verify_postgres_grants.sh`, and the orchestrator.

**Dependencies:** Area 1.

**Tasks:**

* [ ] `T5.3` **Change:** Re-verify network exposure and the reverse proxy boundary.
  * **Target:** The frozen deployment.
  * **Current -> required:** Firewall and port publication were last verified on 2026-09-18 against baseline `95c3d017`. The frozen unit is a different image, so those results cannot be cited.
  * **Implementation:** Run `./scripts/verify/verify_firewall.sh` from the deployment user's `container/` directory with `sudo` available for the firewall listing, and record the listener output, the rule listing, and the cross-host result. Confirm the backend is published on loopback only and that the proxy is the only external entry point.
  * **Constraints:** The script is read-only and must not change rules, services, or configuration. Record the output with the date and host.
  * **Validation:** `V-5.3`.
* [ ] `T5.4` **Change:** Re-inspect the container configuration, mounts, secrets, and environment.
  * **Target:** The frozen deployment.
  * **Current -> required:** Container configuration was last verified on 2026-09-18 and its evidence belongs to a different image.
  * **Implementation:** Run `sudo -u test-shape-shifter.sead.se -H bash ./scripts/verify/verify_container_config.sh` and record the published ports, the mount list, the environment variable names, and the image label and history scan. Confirm no credential value appears and no sensitive host path is mounted writable.
  * **Constraints:** Environment variable names only, never values. The script must not change the container, image, or configuration.
  * **Validation:** `V-5.4`.
* [ ] `T5.5` **Change:** Re-verify PostgreSQL grants and the authorization database placement.
  * **Target:** The frozen deployment.
  * **Current -> required:** Grant verification was last run on 2026-09-18 against a different image.
  * **Implementation:** Run `./scripts/verify/verify_postgres_grants.sh --database sead_staging --role sead_ro --schema public --sqlite "$DATA_DIR/state/authorization.sqlite3"` and record the grant results and the store's ownership and mode.
  * **Constraints:** Do not change grants or store permissions.
  * **Validation:** `V-5.5`.
* [ ] `T5.6` **Change:** Run the verification orchestrator for the frozen unit and file its evidence.
  * **Target:** `<DATA_DIR>/deployment-verification/`.
  * **Current -> required:** The orchestrator has not been run against the frozen unit; this is the single capture pass for the check families it owns.
  * **Implementation:** Run `./scripts/verify/run_deployment_verification.sh` with `~/config/deployment-verification.options.yml`, as a sudo-capable operator from the deployment user's `container/` directory. This supersedes the individual runs above when it covers the same checks; keep whichever evidence is complete and record which source each result came from.
  * **Constraints:** Leave the authenticated and rollback phases off here; they are handled in Areas 3 and 4 so their evidence lands in one place.
  * **Validation:** `V-5.6`.

**Completion evidence:** Exposure, container configuration, and grant results are recorded for the frozen unit, or the check that could not run is recorded with its reason.

### Area 3: Confirm proxy identity handling and access behavior

**Objective:** Proxy identity handling is evidenced, and the access checks pass against the frozen unit.

**Affected code:** `/etc/nginx/sites-available/test-shape-shifter.sead.se`, `container/scripts/verify/verify_authenticated_access.sh`, `backend/tests/authorization/test_route_authentication.py`.

**Dependencies:** Area 1.

**Tasks:**

* [ ] `T5.7` **Change:** Confirm the proxy removes and replaces the identity header.
  * **Target:** The deployed nginx site and the effective configuration.
  * **Current -> required:** `PH5-AC-3` requires identity-header handling to be verified. Client identity headers were never recorded as a distinct check; the standing limitation that the middleware trusts any source is recorded but the overwrite itself is not evidenced.
  * **Implementation:** Inspect `/etc/nginx/sites-available/test-shape-shifter.sead.se` and the effective configuration from `sudo nginx -T`. Confirm the site sets `proxy_set_header X-Authenticated-User $remote_user` and that no client-supplied identity header is passed through. Record the relevant configuration lines and the `nginx -t` result.
  * **Constraints:** Read only. Do not reload or change the proxy configuration. Do not record the `htpasswd` path contents.
  * **Validation:** `V-5.7`.
* [ ] `T5.8` **Change:** Re-run the authenticated access check with the corrected script.
  * **Target:** `https://test-shape-shifter.sead.se`.
  * **Current -> required:** Two filed runs used the pre-fix script, and the corrected script was merged in PR #500 and synced but never executed on the host; the Phase 4 record accepts that as residual risk. Running it here closes that risk and supplies `PH5-AC-3` evidence.
  * **Implementation:** Run `container/scripts/verify/verify_authenticated_access.sh` with `--base-url https://test-shape-shifter.sead.se`, the reviewed pair of principals and projects, and the administrator probe for a protected list route. Redirect the output into the phase evidence directory. Confirm unauthenticated `401`, allowed `200`, concealed denied `404`, administrator `200`, and record the principal-scope block and how many isolation directions were verified.
  * **Constraints:** Passwords are prompted, never passed as arguments, never written to a file, and never recorded. Do not grant ownership to make a check pass. Where no reviewed pair can produce a symmetric isolation probe, record that the direction that matters was verified and why the other is masked.
  * **Validation:** `V-5.8`.
* [ ] `T5.9` **Change:** Confirm route classification at the frozen revision.
  * **Target:** `backend/tests/authorization/test_route_authentication.py`.
  * **Current -> required:** The suite passed at the deployed revision on 2026-09-22; `PH5-AC-3` needs the result bound to the frozen revision.
  * **Implementation:** Run `.venv/bin/pytest backend/tests/authorization -q` at the frozen commit and record the result alongside the frozen revision.
  * **Constraints:** A mismatch between the runtime routes and `docs/AUTHORIZATION_ROUTE_INVENTORY.md` blocks the phase. Do not edit the inventory to pass the check.
  * **Validation:** `V-5.9`.

**Completion evidence:** Identity-header handling is evidenced from the deployed configuration, and the access checks return the expected statuses with the principal scope recorded.

### Area 4: Confirm backup, restore, and rollback for the frozen unit

**Objective:** `PH5-AC-5` is satisfied for the frozen unit, either by a matching prior result or by a fresh exercise.

**Affected code:** `container/scripts/authorization.sh`, `container/scripts/verify/rollback_exercise.sh`.

**Dependencies:** Areas 1–2.

**Tasks:**

* [ ] `T5.10` **Change:** Establish the rollback result for the frozen unit.
  * **Target:** The frozen deployment.
  * **Current -> required:** A rollback exercise ran on 2026-09-22 at 16:48:11 with integrity passing and reconciliation zero-missing. Whether it can be cited depends on whether the frozen image identity matches image ID `6a487db7…04a8`.
  * **Implementation:** First compare the frozen identity with the recorded one. On a match, cite the recorded transcript and note the matching identity. On a mismatch, create a fresh backup with `container/scripts/authorization.sh backup` and record its path and checksum, then run `container/scripts/verify/rollback_exercise.sh` with `--image`, `--authorization-backup`, `--manifest`, and `--evidence-dir`, and confirm integrity, reconciliation, image identity, and health. Run `make service-restart` afterwards.
  * **Constraints:** Run the exercise only inside an approved rollback window and with the rollback owner's decision if a step fails. Never verify integrity against the retained backup; verify a copy.
  * **Validation:** `V-5.10`, `V-5.11`.

**Completion evidence:** The deployment record states either the matching prior rollback result or a fresh transcript, with integrity and reconciliation outcomes.

### Area 5: Close the log review and update the security record

**Objective:** Every finding carries a release disposition, and the security record describes the frozen release.

**Affected code:** `container/scripts/verify/verify_logs.sh`, `docs/proposals/done/MITIGATE_SECURITY_ISSUES/SECURITY_CHECK.md`, the phase plan status.

**Dependencies:** Areas 1–4.

**Tasks:**

* [ ] `T5.11` **Change:** Resolve the outstanding host-log review.
  * **Target:** PostgreSQL and container logs.
  * **Current -> required:** The 2026-09-18 run failed the host-log review because the PostgreSQL log could not be read, and candidate matches require operator review. It is tracked as a non-blocking GitHub issue.
  * **Implementation:** Run `container/scripts/verify/verify_logs.sh` with the PostgreSQL log accessible, and review every candidate match it reports. Where access is still unavailable, record an approved exception naming the owner, the reason, and the residual risk.
  * **Constraints:** Never print credential values found in a log; record the location and the finding instead. An unavailable check is an exception, not a pass.
  * **Validation:** `V-5.12`.
* [ ] `T5.12` **Change:** Update the security record and the phase status.
  * **Target:** `docs/proposals/done/MITIGATE_SECURITY_ISSUES/SECURITY_CHECK.md`; `CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md`; the deployment record.
  * **Current -> required:** `PH5-AC-6` requires the security record to carry the tested commit, image digest, results, limitations, and approved exceptions. The phase plan still shows Phase 5 as not started.
  * **Implementation:** Add the Podman deployment result to `SECURITY_CHECK.md` with the tested commit, image identity, each check's result, the limitations, and every approved exception with its owner. Mark Phase 5 complete in the phase plan with a link to the deployment record.
  * **Constraints:** Change only the status and completion statements in the phase plan; do not re-scope it. Do not present a `not run` or excepted check as passed.
  * **Validation:** `V-5.13`.

**Completion evidence:** Every finding has a recorded disposition, and the security record describes the frozen release.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
| --- | --- | --- | --- |
| `PH5-AC-1` | `T5.1`, `T5.2` | `V-5.1`, `V-5.2` | Frozen release unit recorded with the image ID, the manifest digest, and the OCI labels, all matching the running container |
| `PH5-AC-2` | `T5.3`, `T5.6` | `V-5.3`, `V-5.6` | Listener, firewall, and proxy-boundary output for the frozen unit |
| `PH5-AC-3` | `T5.7`, `T5.8`, `T5.9` | `V-5.7`, `V-5.8`, `V-5.9` | Deployed proxy overwrite lines, access-check transcript with principal scope, route-classification result |
| `PH5-AC-4` | `T5.4`, `T5.5`, `T5.11` | `V-5.4`, `V-5.5`, `V-5.12` | Container configuration, grant, and log-review results with no credential values |
| `PH5-AC-5` | `T5.10` | `V-5.10`, `V-5.11` | Matching prior rollback result, or a fresh transcript with integrity and reconciliation outcomes |
| `PH5-AC-6` | `T5.12` | `V-5.13` | `SECURITY_CHECK.md` entry with commit, identity, results, limitations, and exceptions |

## Validation And Testing

| ID | Check and target | Command or method | Covers | Expected result |
| --- | --- | --- | --- | --- |
| `V-5.1` | Release unit recorded | Read `~/config/deployment.env`, the manifest checksum, and the container identity | `PH5-AC-1` | Every release-unit field recorded, with the freeze stated |
| `V-5.2` | Image identity | `podman image inspect --format '{{.Id}}'`, `{{json .RepoDigests}}`, and the OCI `revision`, `version`, and `source` labels as the deployment user | `PH5-AC-1` | Image ID, manifest digest, and labels recorded and matching the running container; the digest stated as locally computed |
| `V-5.3` | Exposure | `./scripts/verify/verify_firewall.sh` | `PH5-AC-2` | Backend on loopback only; no rule exposes the backend port |
| `V-5.4` | Container configuration | `sudo -u test-shape-shifter.sead.se -H bash ./scripts/verify/verify_container_config.sh` | `PH5-AC-4` | Ports, mounts, and environment names recorded; no credential value, no writable sensitive mount |
| `V-5.5` | Grants and store placement | `./scripts/verify/verify_postgres_grants.sh --database sead_staging --role sead_ro --schema public --sqlite "$DATA_DIR/state/authorization.sqlite3"` | `PH5-AC-4` | Read-only grants as approved; store location and mode within the allowed directories |
| `V-5.6` | Orchestrated capture | `./scripts/verify/run_deployment_verification.sh` with `~/config/deployment-verification.options.yml` | `PH5-AC-2`, `PH5-AC-4` | A timestamped run directory with `summary.txt` and one log per check |
| `V-5.7` | Proxy identity handling | `sudo nginx -T` and `/etc/nginx/sites-available/test-shape-shifter.sead.se` | `PH5-AC-3` | `proxy_set_header X-Authenticated-User $remote_user` present; no client header passed through |
| `V-5.8` | Access checks | `container/scripts/verify/verify_authenticated_access.sh --base-url https://test-shape-shifter.sead.se --principal-a/--principal-b --project-a/--project-b`, output redirected to the phase evidence directory | `PH5-AC-3` | Unauthenticated `401`, allowed `200`, concealed denied `404`, administrator `200`, principal scope and isolation-direction count reported |
| `V-5.9` | Route classification | `.venv/bin/pytest backend/tests/authorization -q` at the frozen commit | `PH5-AC-3` | All checks pass; every API route classified and documented |
| `V-5.10` | Backup and integrity | `container/scripts/authorization.sh backup`, then checksum and integrity verification on a copy | `PH5-AC-5` | Backup path and checksum recorded; integrity passes |
| `V-5.11` | Rollback exercise | `container/scripts/verify/rollback_exercise.sh --image --authorization-backup --manifest --evidence-dir` | `PH5-AC-5` | Image and database restored, integrity passes, reconciliation zero-missing, health `200`, or the matching prior transcript is cited |
| `V-5.12` | Log review | `container/scripts/verify/verify_logs.sh` with the PostgreSQL log accessible | `PH5-AC-4` | Every candidate match reviewed, or an approved exception with an owner and reason |
| `V-5.13` | Record review | Manual review of the deployment record and `SECURITY_CHECK.md`, then `scripts/check_doc_links.sh` and `git diff --check` | All criteria | Every finding has a disposition; no credential values; links valid |

## Deliverables

| Deliverable | Description | Status | Link |
| --- | --- | --- | --- |
| Podman deployment record | Frozen release unit, image identity, per-check results, limitations, and dispositions | In progress | [PODMAN_DEPLOYMENT_RECORD.md](./PODMAN_DEPLOYMENT_RECORD.md) (new, this folder) |
| Exposure and configuration evidence | Firewall, container configuration, and grant results for the frozen unit | Not started | Deployment record, and the run directory under `<DATA_DIR>/deployment-verification/` |
| Proxy identity evidence | Deployed proxy overwrite lines and the effective configuration excerpt | Not started | Deployment record |
| Access-check transcript | Corrected-script output with principal scope and isolation-direction count | Not started | Deployment record and the phase evidence directory |
| Rollback disposition | Matching prior result or a fresh transcript with integrity and reconciliation | Not started | Deployment record, and `<DATA_DIR>/backups/` |
| Log-review disposition | Reviewed matches, or an approved exception naming the owner and reason | Not started | Deployment record, and `SECURITY_CHECK.md` |
| Updated security record | Tested commit, image identity, results, limitations, and approved exceptions | Not started | [SECURITY_CHECK.md](../done/MITIGATE_SECURITY_ISSUES/SECURITY_CHECK.md) |
| Phase plan status update | Phase 5 complete, with its result and any exceptions | Not started | [CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md](./CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md) |

## Progress Tracker

| Area | Status | Notes |
| --- | --- | --- |
| Area 1: Freeze the release unit and record its identity | Done | Frozen unit confirmed on the host: image ID `6a487db7…04a8`, manifest digest `sha256:7ff51b2b…`, revision `dbff5ab9…4f96`, deployed manifest checksum `43c03186…fb90`. It equals the unit Phase 4 verified |
| Area 2: Re-verify exposure, container configuration, and grants | Not started | Evidence from 2026-09-18 describes a different image and cannot be cited |
| Area 3: Confirm proxy identity handling and access behavior | Not started | The corrected access-check script has never run on the host |
| Area 4: Confirm backup, restore, and rollback for the frozen unit | Not started | May be satisfied by citing the 2026-09-22 exercise when the image identity matches |
| Area 5: Close the log review and update the security record | Not started | The host-log review is the one security check still open |

## Definition Of Done

- [x] `PH5-AC-1` has the frozen source commit, the image ID, the manifest digest, and the OCI `revision`, `version`, and `source` labels, with the digest stated as locally computed.
- [ ] `PH5-AC-2` has listener, firewall, and proxy-boundary evidence recorded for the frozen unit.
- [ ] `PH5-AC-3` has the deployed proxy overwrite evidenced, the access checks returning the expected statuses, and the route-classification suite passing at the frozen revision.
- [ ] `PH5-AC-4` has container configuration, grant, and log-review results recorded, with no credential value anywhere.
- [ ] `PH5-AC-5` has a rollback result for the frozen unit, or a reviewed exception with an owner.
- [ ] `PH5-AC-6` has `SECURITY_CHECK.md` and the deployment record stating the tested commit, image identity, results, limitations, and approved exceptions.
- [ ] Every check that could not run is recorded as `not run` with a reason, and no such check is presented as passed.
- [ ] `scripts/check_doc_links.sh` and `git diff --check` pass, and the phase plan status reflects the outcome.

## Risks And Open Questions

- **The manifest digest is local evidence only.** No registry is configured: GitHub Container Registry use is paused pending a billing review, and a locally hosted registry with CI/CD builds is under consideration. The `localhost/` repository prefix shows the image was never pushed, so nothing outside the host vouches for the manifest digest, and a digest computed on another host is not guaranteed to match. Cite the OCI `revision` label as the cross-host identity and the manifest digest as evidence about this deployment. Standing up a registry would add provenance; that is a separate decision.
- **The authenticated check needs an operator with the passwords.** Phase 4 closed with the corrected-script re-run skipped for exactly this reason, and the residual risk accepted. If no operator with the passwords is available, the risk carries forward unchanged and must be restated rather than silently dropped.
- **The frozen unit can be reopened.** Any image rebuild, manifest edit, or layout change invalidates every result recorded for it. Reopen deliberately and re-run the invalidated checks; do not verify a moving target.
- **Two evidence locations may both hold results.** The Phase 4 record cites `<DATA_DIR>/deployment-verification/phase-4/`, the orchestrator writes timestamped run directories under `<DATA_DIR>/deployment-verification/`, and the 2026-09-18 run used a different root. Record which source each result came from, and prefer citing a locked artifact over prose.
- **The log review may remain blocked.** PostgreSQL log access was unavailable before. An approved exception is acceptable for `PH5-AC-5`-style findings, but it needs an owner and a reason, not a note that the check was skipped.
- **Route classification is a blocking check.** A mismatch between the runtime routes and the inventory blocks the phase; the inventory is not adjusted to make a check pass.
- **Deliberate non-repetition is a decision, not an omission.** Any check not re-run in this phase must point to the recorded result it relies on and the image identity that result belongs to.
- **Open question:** whether `SECURITY_CHECK.md` remains the right home for the release disposition as more applications adopt this pattern, or whether the release-cycle proposal should define a separate record. This phase uses `SECURITY_CHECK.md` as the phase plan specifies.
