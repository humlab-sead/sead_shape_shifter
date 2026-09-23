# Handoff: Podman Deployment Verification

**Status:** Closed 2026-09-23 — the release disposition is recorded in [SECURITY_CHECK.md](../../done/MITIGATE_SECURITY_ISSUES/SECURITY_CHECK.md#podman-deployment-verification-record-2026-09-23). The host-log review was completed during the centralized-authorization cutover Phase 5, with the PostgreSQL server log recorded as an approved exception; the credential-rotation item stays resolved as an approved exception. The authenticated-access and rollback exercises were completed on 2026-09-22 during Phase 4 and are recorded below.
**Opened:** 2026-09-16 (extended the same day with the containment and credential-rotation checks that the development plan left open)
**Verification runs:** 2026-09-18 on `humlabsead`; latest run `20260918T210002Z-3878349`
**Source plan:** [MITIGATE_SECURITY_ISSUES_PHASE_5_TASK_PLAN.md](../../done/MITIGATE_SECURITY_ISSUES/done/MITIGATE_SECURITY_ISSUES_PHASE_5_TASK_PLAN.md) (Phase 5, closed)

## Purpose

Assign the deployment checks that the Phase 5 verification run left open to the operations team, and state what each check must produce. The checks confirm that the controls built in Phases 1–4 hold in the release deployment: network exposure, proxy identity handling, secrets, mounts, database grants, logs, and rollback.

The operations team owns this work. The Phase 5 task plan no longer carries it as a definition-of-done item. [CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md](./CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md) Phase 5 still owns the Podman deployment record and the release disposition that consumes these results. The current results do not block deployment to the test release in the test target environment.

## Current State

The test deployment on `humlabsead` was inspected again on 2026-09-18. The latest read-only run used report `deployment-verification-20260918T210002Z-3878349`; its evidence is in `/data/test-shape-shifter.sead.se/container/deployment-verification/20260918T210002Z-3878349`. The earlier 2026-09-15 release identity remains the recorded baseline: commit `95c3d017`, image `localhost/shape-shifter:dev`, digest `sha256:aa320c4c89811306b15ed9fbb43474290a7e75b1becb10deadb2f3840a4d0d90`. Reconfirm the image identity before promoting a different build.

| Check | State |
|---|---|
| Release identity against the running container | Verified |
| Port publication (`127.0.0.1:8012` only; LAN address refused) | Verified |
| Proxy denial without Basic credentials (`401` from nginx) | Verified |
| Unauthenticated protected routes (`401`) | Verified |
| Public health route (`200`, no project, database, or filesystem data) | Verified |
| Single worker, health check, restart policy | Verified |
| Firewall rules | Verified on 2026-09-18 |
| Container mounts, secrets, and environment variables | Verified on 2026-09-18 |
| PostgreSQL grants for the release deployment | Verified on 2026-09-18, including the authorization SQLite store location and permissions |
| Endpoint containment | Verified on 2026-09-18 for execution, raw YAML, data-source creation, and ingester routes |
| Log review (container, proxy, database) | Closed 2026-09-23 in cutover Phase 5: the container log (1598 lines) and the nginx access log (27 lines) returned no matches, and the five nginx error-log candidates were reviewed as non-findings. The PostgreSQL server log was not swept and is an approved exception owned by `super.sead.se`. |
| Credential rotation after the loopback fix | Resolved as an approved exception on 2026-09-22: PostgreSQL credential rotation is out of scope for every PostgreSQL database, including the SEAD database, so the `sead_ro` `.pgpass` credential is not rotated. Previously recorded as a non-blocking GitHub issue. |
| Authenticated access and cross-resource isolation with real principals | Completed 2026-09-22 in the cutover Phase 4: `401` unauthenticated, owner `200`, another principal's project concealed `404`, administrator `200`; the symmetric isolation direction is masked by `project_maintainer` |
| Rollback exercise | Completed 2026-09-22 in the cutover Phase 4: image and authorization database restored, integrity passed, reconciliation zero-missing, health `200` |

## Completed Work

- Two defects found on 2026-09-15 and corrected: the deployed image had been built from `main` instead of `dev`, so it contained no authorization package and returned `200` for unauthenticated requests; and the backend was published on every interface, so `172.18.134.53:8012` reached it directly and bypassed nginx Basic auth. The image was rebuilt with `GIT_REF=dev`, and the deployed compose file now publishes `127.0.0.1:${HOST_PORT:-8012}:8012`.
- The checks marked Verified in the table above, with methods and results.
- The verification scripts are implemented under `container/scripts/verify`; the orchestrator is `container/scripts/verify/run_deployment_verification.sh`. Four read-only runs were recorded on 2026-09-18. The latest run passed firewall, container configuration, PostgreSQL grants, endpoint containment, and container-log review.
- The two latest-run failures are now closed. Credential rotation closed on 2026-09-22 as an approved exception, because PostgreSQL credential rotation was decided out of scope for every PostgreSQL database, including the SEAD database. The host-log review closed on 2026-09-23 in cutover Phase 5: three sources were swept clear and the PostgreSQL server log is an approved exception. The first run also reported transient endpoint-containment and container-log failures; both passed in the three subsequent runs.
- Focused security suites re-run on `95c3d017`.
- PostgreSQL: `scripts/postgres/create-readonly-role.sh` and `scripts/postgres/verify_readonly_role.sql` pass against a disposable PostgreSQL 16 (`NOINHERIT`, no role memberships, no owned objects, no schema `CREATE`). The deployed `sead_ro` account was probed with read-only catalog queries against the live `sead_staging` database on 2026-09-16: 730 of 730 relations readable, no write privilege on any relation, schema and database `CREATE` denied, no `COPY` membership.
- The `rolinherit = t` attribute on the deployed `sead_ro` account was handed to the database administrator on 2026-09-16. It is inert while the account has no memberships. The repository role script creates the role with `NOINHERIT`.

Evidence for all of the above is recorded in [SECURITY_CHECK.md](../../done/MITIGATE_SECURITY_ISSUES/SECURITY_CHECK.md#deployment-verification-record-2026-09-15).

## Key References

| Document | Use |
|---|---|
| [SECURITY_CHECK.md](../../done/MITIGATE_SECURITY_ISSUES/SECURITY_CHECK.md#deployment-verification-record-2026-09-15) | Release identity, checks performed, defects, and limitations from the 2026-09-15 run |
| [SECURITY_CHECK.md](../../done/MITIGATE_SECURITY_ISSUES/SECURITY_CHECK.md#live-read-only-role-verification-2026-09-16) | Database grant checks and results against the live test database |
| [CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md](./CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md#phase-5-verify-podman-deployment-and-update-security-record) | Deployment record and release disposition that consume these results |
| [container/DEPLOYMENT.md](../../../../container/DEPLOYMENT.md) | Build, service install, and proxy setup for the Podman deployment |
| [container/scripts/service.sh](../../../../container/scripts/service.sh) | Service control actions: install, enable, disable, start, stop, restart, status, logs |
| [OPERATIONS.md](../../../OPERATIONS.md#post-deployment-verification) | Current post-deployment verification and [rollback](../../../OPERATIONS.md#rollback) guidance; still written for Docker Compose, so treat the commands as needs-rewrite |

## Next Actions

The verification command and outputs are recorded in the dated run directories under `sead-tools/test-shape-shifter.sead.se/container/deployment-verification`. The current disposition is suitable for deployment to the test release in the test target environment. Both previously tracked items are closed and the release disposition is recorded; the production move and its open questions stay with [PRODUCTION_FLIP_TO_AUTHORIZED_SERVER.md](../../future/PRODUCTION_FLIP_TO_AUTHORIZED_SERVER.md).

- [x] **Firewall rules** — Passed in the latest read-only run.
- [x] **Container configuration re-inspection** — Passed in the latest read-only run.
- [x] **PostgreSQL grants for the release host** — Passed in the latest read-only run.
- [x] **Endpoint containment** — Passed in the latest read-only run.
- [x] **Record the results** — Dated reports and detailed logs are recorded in the deployment-verification output directory.
- [x] **Log review** — Closed 2026-09-23 in cutover Phase 5: three sources were swept with no value-bearing match, and the PostgreSQL server log is an approved exception owned by `super.sead.se`. See [PODMAN_DEPLOYMENT_RECORD.md](./PODMAN_DEPLOYMENT_RECORD.md) *Area 5*.
- [x] **Credential rotation** — Resolved as an approved exception on 2026-09-22: PostgreSQL credential rotation is out of scope for every PostgreSQL database, including the SEAD database, so the `sead_ro` `.pgpass` credential is not rotated.
- [x] **Authenticated access with real principals** — Passed 2026-09-22: proxy `401` unauthenticated, owner `200`, another principal's project concealed `404`, administrator `200`. Both runs are filed as `/data/test-shape-shifter.sead.se/container-data/deployment-verification/phase-4/verify-authenticated-access.log`; see [UAT_READY_AUTHORIZATION_DEPLOYMENT_HANDOFF.md](./done/UAT_READY_AUTHORIZATION_DEPLOYMENT_HANDOFF.md) *Access-check detail*.
- [x] **Rollback exercise** — Passed 2026-09-22 16:48:11: the recorded image and authorization database were restored, integrity passed, reconciliation reported `Missing: 0 resources, 0 administrators, 0 grants`, and health returned `200`. Transcript `container-data/backups/rollback-exercise.log`; see [UAT_READY_AUTHORIZATION_DEPLOYMENT_HANDOFF.md](./done/UAT_READY_AUTHORIZATION_DEPLOYMENT_HANDOFF.md) *Rollback detail*.

## Risks

- **The identity header is trusted from any source.** `ProxyAuthenticationMiddleware` accepts any non-empty `X-Authenticated-User` value and does not check the source address, so any local process on the host can assert an identity, including a bootstrap administrator. The loopback-only binding and nginx overwriting the header cover remote callers. Record this as a limitation until a source-address check, a proxy shared secret, or a Unix socket is added; those are new controls and outside the security project's scope.
- **`make up` starts `IMAGE_NAME`, which can differ from `GIT_REF`.** Read the running container's `org.opencontainers.image.revision` label before recording any result, and record the digest alongside the commit.
- **The recorded digest predates the committed build recipe.** The image labels were committed afterwards in `7c0da4f2`, so confirm the digest of the release build rather than reusing `sha256:aa320c4c…`.
- **The release candidate can change during verification.** Re-run the affected checks after any image, compose, or proxy change; a result does not carry over to a different digest.
- **Missing access blocks the checks.** Host access, firewall access, and database administration evidence are prerequisites, so stop and report when one is unavailable instead of recording a partial result.
- **Rollback freshness.** Keep the backup made for readiness testing available until the release is accepted or the rollback window closes.

## Open Decisions

- Which host and environment carry the release deployment: shared, staging, or production?
- Who owns the rollback decision, and how long does the pre-cutover authorization database backup stay available?
- Does the deployed `sead_ro` account stay a shared, system-wide SEAD account, or does the database administrator create an application-specific read-only account? The database administrator owns this decision.
- Who approves an exception when a check cannot be performed?

## Suggested Follow-Up Documents

- Done 2026-09-23: the Podman deployment record [PODMAN_DEPLOYMENT_RECORD.md](./PODMAN_DEPLOYMENT_RECORD.md) carries these results, and Phase 5 of [CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md](./CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md) is complete.
- Rewrite the [OPERATIONS.md](../../../OPERATIONS.md#post-deployment-verification) post-deployment verification and rollback sections for Podman instead of Docker Compose.
- Done 2026-09-23: the release disposition is recorded in [SECURITY_CHECK.md](../../done/MITIGATE_SECURITY_ISSUES/SECURITY_CHECK.md), and this proposal folder is archived under `docs/proposals/done/`.
