# Handoff: Podman Deployment Verification

**Status:** Open — assigned to the operations team
**Opened:** 2026-09-16
**Source plan:** [MITIGATE_SECURITY_ISSUES_PHASE_5_TASK_PLAN.md](./MITIGATE_SECURITY_ISSUES_PHASE_5_TASK_PLAN.md) (Phase 5)

## Purpose

Assign the deployment checks that the Phase 5 verification run left open to the operations team, and state what each check must produce. The checks confirm that the controls built in Phases 1–4 hold in the release deployment: network exposure, proxy identity handling, secrets, mounts, database grants, logs, and rollback.

The operations team owns this work. The Phase 5 task plan no longer carries it as a definition-of-done item. [CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md](./CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md) Phase 5 still owns the Podman deployment record and the release disposition that consumes these results.

## Current State

The test deployment on `humlabsead` was inspected on 2026-09-15. Release identity was commit `95c3d017`, image `localhost/shape-shifter:dev`, digest `sha256:aa320c4c89811306b15ed9fbb43474290a7e75b1becb10deadb2f3840a4d0d90`.

| Check | State |
|---|---|
| Release identity against the running container | Verified |
| Port publication (`127.0.0.1:8012` only; LAN address refused) | Verified |
| Proxy denial without Basic credentials (`401` from nginx) | Verified |
| Unauthenticated protected routes (`401`) | Verified |
| Public health route (`200`, no project, database, or filesystem data) | Verified |
| Single worker, health check, restart policy | Verified |
| Firewall rules | Not verified |
| Container mounts, secrets, and environment variables | Partly verified — inspected on the container instance that ran before the image change; re-inspection of the current instance is pending |
| PostgreSQL grants for the release deployment | Not verified — the repository role scripts and the shared `sead_ro` account are verified separately (see below); release-host grants and the authorization store location and permissions are open |
| Log review (container, proxy, database) | Not verified |
| Authenticated access and cross-resource isolation with real principals | Not verified |
| Rollback exercise | Not verified |

## Completed Work

- Two defects found on 2026-09-15 and corrected: the deployed image had been built from `main` instead of `dev`, so it contained no authorization package and returned `200` for unauthenticated requests; and the backend was published on every interface, so `172.18.134.53:8012` reached it directly and bypassed nginx Basic auth. The image was rebuilt with `GIT_REF=dev`, and the deployed compose file now publishes `127.0.0.1:${HOST_PORT:-8012}:8012`.
- The checks marked Verified in the table above, with methods and results.
- Focused security suites re-run on `95c3d017`.
- PostgreSQL: `scripts/postgres/create-readonly-role.sh` and `scripts/postgres/verify_readonly_role.sql` pass against a disposable PostgreSQL 16 (`NOINHERIT`, no role memberships, no owned objects, no schema `CREATE`). The deployed `sead_ro` account was probed with read-only catalog queries against the live `sead_staging` database on 2026-09-16: 730 of 730 relations readable, no write privilege on any relation, schema and database `CREATE` denied, no `COPY` membership.
- The `rolinherit = t` attribute on the deployed `sead_ro` account was handed to the database administrator on 2026-09-16. It is inert while the account has no memberships. The repository role script creates the role with `NOINHERIT`.

Evidence for all of the above is recorded in [SECURITY_CHECK.md](./SECURITY_CHECK.md#deployment-verification-record-2026-09-15).

## Key References

| Document | Use |
|---|---|
| [SECURITY_CHECK.md](./SECURITY_CHECK.md#deployment-verification-record-2026-09-15) | Release identity, checks performed, defects, and limitations from the 2026-09-15 run |
| [SECURITY_CHECK.md](./SECURITY_CHECK.md#live-read-only-role-verification-2026-09-16) | Database grant checks and results against the live test database |
| [CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md](./CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md#phase-5-verify-podman-deployment-and-update-security-record) | Deployment record and release disposition that consume these results |
| [container/DEPLOYMENT.md](../../../container/DEPLOYMENT.md) | Build, service install, and proxy setup for the Podman deployment |
| [container/scripts/service.sh](../../../container/scripts/service.sh) | Service control actions: install, enable, disable, start, stop, restart, status, logs |
| [OPERATIONS.md](../../OPERATIONS.md#post-deployment-verification) | Current post-deployment verification and [rollback](../../OPERATIONS.md#rollback) guidance; still written for Docker Compose, so treat the commands as needs-rewrite |

## Next Actions

Record the command and its output for each check, then add the result to the deployment verification record in `SECURITY_CHECK.md`.

- [ ] **Firewall rules** — Confirm the host firewall rejects `8012` from every interface except loopback and that the reverse proxy is the only external entry point. Evidence: firewall listing plus a connection attempt from another host.
- [ ] **Container configuration re-inspection** — Re-inspect the running container for mounts, secrets, and environment variables (names only, no credential values). Confirm credentials appear in neither the image nor the container paths that should not hold them. Evidence: `podman inspect` output.
- [ ] **PostgreSQL grants for the release host** — Record the grant queries and results for the release database, and the authorization SQLite store location, ownership, and file permissions. Evidence: catalog query output plus file listing.
- [ ] **Log review** — Review container, proxy, and database logs for the release window. Confirm logs carry no credentials, connection strings, SQL text, or absolute filesystem paths, and that user-supplied newlines cannot forge a record. Evidence: log excerpts and the searches used.
- [ ] **Authenticated access with real principals** — Through the proxy with a real principal, check the allowed path, a denied path, and cross-resource isolation between two principals. Evidence: request and response pairs.
- [ ] **Rollback exercise** — Restore the recorded image and the authorization database backup, then run the integrity and reconciliation checks. Evidence: restore commands, integrity output, and the resulting service state.
- [ ] **Record the results** — Add the outcomes, the tested commit, the image digest, any limitation, and the exception or failed check to `SECURITY_CHECK.md`. Evidence: updated record with the date and the operator.

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

- Update the Podman deployment record in [CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md](./CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md) Phase 5 from these results.
- Rewrite the [OPERATIONS.md](../../OPERATIONS.md#post-deployment-verification) post-deployment verification and rollback sections for Podman instead of Docker Compose.
- Archive this handoff once the release disposition is recorded in [SECURITY_CHECK.md](./SECURITY_CHECK.md).
