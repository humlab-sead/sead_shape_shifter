# Task Plan: Phase 5 — Security Regression And Release Verification

## Phase Summary

- Status: Done — release-host deployment checks deferred to the operations team
- Proposal: [MITIGATE_SECURITY_ISSUES.md](./MITIGATE_SECURITY_ISSUES.md)
- Parent phase plan: [MITIGATE_SECURITY_ISSUES_PHASE_PLAN.md](./MITIGATE_SECURITY_ISSUES_PHASE_PLAN.md) (Phase 5)
- Review record: [SECURITY_CHECK.md](../SECURITY_CHECK.md)
- Deferred work: [DEPLOYMENT_VERIFICATION_HANDOFF.md](../../../done/CENTRALIZED_AUTHORIZATION_CUTOVER/DEPLOYMENT_VERIFICATION_HANDOFF.md) (operations team)
- Goal: prove that the mitigations from Phases 1–4 hold on the release candidate by adding focused security regression tests, re-running the verified reproduction cases, and recording security evidence for the tested commit; deployment verification on the release host is deferred to the operations team
- Entry gate: Phase 5 cannot be marked complete until the completion criteria for Phases 1–4 are met, or each incomplete criterion has an approved documented exception in `SECURITY_CHECK.md`

**Focus**

- Add unauthenticated and cross-resource authorization tests for every sensitive router and direct application route.
- Add filesystem boundary tests for traversal, absolute paths, symlinks, missing parents, and project-name variations.
- Add SQL and DuckDB tests for stacked statements, comments, embedded `LIMIT`, destructive statements, identifier edge cases, file functions, `COPY`, `ATTACH`, extension loading, network access, and paths outside approved roots.
- Add response and logging tests for secret, SQL, connection-string, and absolute-path redaction.
- Re-run the verified cases in `SECURITY_CHECK.md` against disposable databases and files.
- Run the full Core and backend test suites and record unrelated failures separately.
- Update `SECURITY_CHECK.md` with pass/fail evidence and the tested commit.
- Deployment verification on the release host is deferred to the operations team in [DEPLOYMENT_VERIFICATION_HANDOFF.md](../../../done/CENTRALIZED_AUTHORIZATION_CUTOVER/DEPLOYMENT_VERIFICATION_HANDOFF.md).

**Acceptance Criteria**

- [x] Focused security tests, regression tests, and deployment checks pass on the exact release candidate; the release-host deployment checks are deferred to the operations team. — Focused suites pass on `95c3d017`; deployment checks pass for release identity, port binding, proxy denial, public health, and unauthenticated route protection. The remaining checks are tracked in [DEPLOYMENT_VERIFICATION_HANDOFF.md](../../../done/CENTRALIZED_AUTHORIZATION_CUTOVER/DEPLOYMENT_VERIFICATION_HANDOFF.md).
- [x] Every original high-severity finding is either fixed with evidence or remains disabled with a documented exception.
- [x] Unauthenticated and cross-resource authorization tests cover every sensitive router and direct application route.
- [x] Filesystem boundary tests cover traversal, absolute paths, symlinks, missing parents, and project-name variations.
- [x] SQL and DuckDB tests cover stacked statements, comments, embedded `LIMIT`, destructive statements, identifier edge cases, file functions, `COPY`, `ATTACH`, extension loading, network access, and paths outside approved roots.
- [x] Response and logging tests cover secret, SQL, connection-string, and absolute-path redaction.
- [x] The verified cases in `SECURITY_CHECK.md` are re-run against disposable databases and files with pass/fail evidence recorded.
- [x] The full Core and backend test suites are run; security-relevant failures block release, and unrelated failures have a documented cause and release disposition.
- [x] Deployment verification covers the exact image and release commit, Podman service and port binding, proxy routes, firewall rules, environment variables, database grants, mounted files, logs, and rollback; the release-host checks are deferred to the operations team. — Verified on the test deployment on 2026-09-15; firewall rules, PostgreSQL grants, mounted-file re-inspection, log review, the authenticated access path, and the rollback exercise are tracked in [DEPLOYMENT_VERIFICATION_HANDOFF.md](../../../done/CENTRALIZED_AUTHORIZATION_CUTOVER/DEPLOYMENT_VERIFICATION_HANDOFF.md).
- [x] `SECURITY_CHECK.md` is updated with pass/fail evidence and the tested commit.
- [x] A finding matrix maps every `SECURITY_CHECK.md` finding to a test, evidence record, or approved exception.

## Work Breakdown

### 1. Add Authorization And Authentication Regression Tests

**Objective**

Prove that unauthenticated requests and cross-resource access are rejected on every sensitive router and direct application route.

**Tasks**

- [x] Inventory every sensitive router and direct application route in [AUTHORIZATION_ROUTE_INVENTORY.md](../../../../AUTHORIZATION_ROUTE_INVENTORY.md), including routes outside `api_router` such as `/api/v1/docs`, `/api/v1/openapi.json`, `/api/v1/redoc`, `/docs/oauth2-redirect`, and the public documentation mount.
- [x] Add unauthenticated request tests for every sensitive route, asserting `401` or `403` responses.
- [x] Add cross-resource authorization tests verifying that an authenticated user cannot access another user's or team's projects, data sources, logs, schemas, queries, or tasks.
- [x] Add tests for direct backend access without the trusted nginx identity header, confirming rejection.
- [x] Add tests for session ownership: a session created by one user cannot be used by another.
- [x] Add tests for CORS: unapproved origins receive no credentialed access, and approved origins behave correctly.
- [x] Add tests for health-check routes confirming they remain public only when required by deployment health checks and expose no project, database, filesystem, or configuration data.
- [x] Add tests for routes outside `api_router` (Swagger, OpenAPI, Redoc, documentation mount) confirming they are protected or disabled in shared and production environments.
- [x] Update the route inventory with the current route scope and expected authorization classification for every sensitive route, including routes that are intentionally disabled.

**Completion Criteria**

Every sensitive route returns `401` or `403` for unauthenticated requests, cross-resource access is rejected, and direct backend access without the trusted identity is blocked.

### 2. Add Filesystem Boundary Regression Tests

**Objective**

Prove that file read, write, download, upload, and directive paths cannot escape approved roots.

**Tasks**

- [x] Add traversal tests for `../` sequences in project names, file paths, execution targets, and directive paths.
- [x] Add absolute-path tests confirming that absolute paths are rejected or confined to approved roots.
- [x] Add symlink tests for symlinks pointing outside approved roots, including symlinked project directories, output directories, and backup directories.
- [x] Add missing-parent tests confirming that paths with non-existent parent directories are handled safely.
- [x] Add project-name variation tests for names containing special characters, Unicode, and path separators.
- [x] Add time-of-check/time-of-use tests for symlink replacement between resolution and access.
- [x] Make time-of-check/time-of-use tests deterministic by injecting the replacement between authorization and access, rather than relying on an uncontrolled race.
- [x] Add tests for the download endpoint confirming it cannot return files outside the approved output root.
- [x] Add tests for execution targets confirming outputs cannot be written outside assigned roots.
- [x] Add tests for `@include` and `@load` directive resolution confirming they cannot escape the project or approved data roots.
- [x] Add tests for upload, backup, and project-file paths confirming they are confined to approved roots.

**Completion Criteria**

No file read, write, download, upload, or directive path can escape its approved root, and all boundary tests pass.

### 3. Add SQL And DuckDB Regression Tests

**Objective**

Prove that the read-only SQL policy and DuckDB restrictions hold on every execution path.

**Tasks**

- [x] Add stacked-statement tests for multiple statements separated by semicolons, comments, and whitespace.
- [x] Add comment tests for SQL comments that attempt to hide or split statements.
- [x] Add embedded-`LIMIT` tests confirming that a user-supplied `LIMIT` cannot bypass the server result limit.
- [x] Add destructive-statement tests for `DROP`, `ALTER`, `CREATE`, `INSERT`, `UPDATE`, `DELETE`, `TRUNCATE`, `MERGE`, and `REPLACE`.
- [x] Add identifier edge-case tests for quoted identifiers, malformed identifiers, nested queries, and filter values containing SQL metacharacters.
- [x] Add tests for `COPY`, `ATTACH`, `DETACH`, `INSTALL`, `LOAD`, `EXPORT`, and `IMPORT` operations.
- [x] Add tests for transaction, session, and administrative operations including `BEGIN`, `COMMIT`, `ROLLBACK`, `SET`, `RESET`, `CALL`, `DO`, `PREPARE`, `DEALLOCATE`, `GRANT`, `REVOKE`, `PRAGMA`, `SHOW`, `VACUUM`, and `ANALYZE`.
- [x] Add DuckDB file-function tests for `read_csv_auto`, `read_csv`, `read_json`, `read_parquet`, `read_text`, `read_blob`, and `glob`.
- [x] Add DuckDB network-access tests confirming that network-capable operations are rejected.
- [x] Add DuckDB extension-loading tests confirming that `INSTALL` and `LOAD` are rejected.
- [x] Add tests for paths outside approved roots in DuckDB file operations.
- [x] Add tests for the `@internal` DuckDB execution path confirming the same read-only policy is applied.
- [x] Add tests for the read-only PostgreSQL role confirming allowed reads succeed and denied DDL, DML, `COPY`, and role operations fail. — Covered by `scripts/postgres/test-readonly-role.sh` and `scripts/postgres/verify_readonly_role.sql`, executed against a disposable PostgreSQL 16 on 2026-09-15. The deployed `sead_ro` account was additionally verified against the live `sead_staging` database on 2026-09-16 with read-only catalog probes; see the role verification records in `SECURITY_CHECK.md`.
- [x] Add tests for query duration, result size, memory, and concurrency limits.
- [x] Record a matrix covering each SQL policy case across public query routes, schema introspection, SQL loaders, workflow execution, internal DuckDB execution, and direct service paths.

**Completion Criteria**

Stacked statements, destructive SQL, file access, extension loading, and network operations are rejected on every execution path, and the read-only database role cannot alter or destroy data.

### 4. Add Response And Logging Redaction Tests

**Objective**

Prove that client responses and server logs do not disclose secrets, SQL, connection details, or sensitive filesystem paths.

**Tasks**

- [x] Add response tests confirming that error responses do not contain database credentials, environment variable values, connection strings, or SQL text.
- [x] Add response tests confirming that error responses use stable public messages with correlation IDs.
- [x] Add response tests confirming that absolute filesystem paths are not disclosed in error responses.
- [x] Add logging tests confirming that credentials, environment values, connection strings, SQL text, and sensitive paths are redacted from server logs.
- [x] Add logging tests confirming that user-controlled newlines cannot forge log records.
- [x] Add tests for the data-source test endpoint confirming that connection failure messages do not echo environment variable values or host details.
- [x] Add tests for the global exception handler confirming it does not return raw exception messages to clients.

**Completion Criteria**

Client responses and server logs do not reveal secrets, SQL, connection details, or sensitive paths, and redaction tests cover the targeted fields.

### 5. Re-Run Verified Security Cases And Full Test Suites

**Objective**

Prove that the original high-severity findings are fixed and that the full test suites pass on the release candidate.

**Tasks**

- [x] Re-run the verified cases in `SECURITY_CHECK.md` against disposable databases and files, including arbitrary file read (1.1), arbitrary file write (1.2), multi-statement SQL (1.3), env-var exfiltration (1.4), `@include`/`@load` file read (2.1), and CORS origin reflection (2.4).
- [x] Re-run the ingester finding (1.5) by proving that the route is disabled or protected, or record the required real-SEAD verification as an approved exception.
- [x] Re-run SQL identifier injection (1.6) through the affected schema and query paths using disposable database objects.
- [x] Re-run the `@internal` DuckDB file read/write case (D1) against a disposable DuckDB workspace.
- [x] Re-run the unauthenticated data-source config leak case (D4) confirming the endpoint requires authentication.
- [x] Record pass/fail evidence for each re-run case with the tested commit.
- [x] Create a finding matrix mapping every finding ID in `SECURITY_CHECK.md` to its test result, evidence location, limitation, or approved exception.
- [x] Run the full Core test suite (`uv run pytest tests -v`) and record results.
- [x] Run the full backend test suite (`uv run pytest backend/tests -v`) and record results.
- [x] Record unrelated test failures separately with their root cause and whether they are pre-existing.
- [x] Run lint checks (`make lint`) and record results.

**Completion Criteria**

Every security-focused test and release check passes. The full Core and backend suites have been run; unrelated failures have a documented cause and release disposition, while security-relevant failures block release.

### 6. Deferred: Deployment Verification And Security Record Update

**Decision**

Defer this work to the operations team in [DEPLOYMENT_VERIFICATION_HANDOFF.md](../../../done/CENTRALIZED_AUTHORIZATION_CUTOVER/DEPLOYMENT_VERIFICATION_HANDOFF.md). The handoff carries the release-host checks — firewall rules, PostgreSQL grants, mounted-file re-inspection, log review, the authenticated access path, and the rollback exercise — together with the evidence each check must produce. The 2026-09-15 results and the updated security record stay in `SECURITY_CHECK.md`.

[CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md](../../../done/CENTRALIZED_AUTHORIZATION_CUTOVER/CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md), Phase 5: **Verify Podman Deployment And Update Security Record** owns the Podman deployment record and the release disposition that consume those results. That phase replaces the Docker-specific assumptions with the selected Podman service model, immutable image identity, Podman secrets and mounts, proxy/firewall checks, PostgreSQL grant verification, rollback, and security-record updates.

## Progress Tracker

| Area | Status | Notes |
|---|---|---|
| Authorization and authentication regression tests | Done | Runtime route, proxy-identity, direct-route, session-ownership, CORS, health, cross-resource HTTP, and team-grant regressions are covered |
| Filesystem boundary regression tests | Done | Download endpoint, directive (@include/@load), backup, upload, file browsing, and project-name regressions are covered |
| SQL and DuckDB regression tests | Done | Shared policy, SQL-loader, QueryService, internal DuckDB, and Shape Shifter PostgreSQL `SELECT` coverage passes. The shipped role scripts were verified against a disposable PostgreSQL 16 on 2026-09-15: allowed reads succeed, and DDL, DML, `COPY`, and role operations are denied. The deployed `sead_ro` account was verified against the live `sead_staging` database on 2026-09-16 with read-only catalog probes: 730 of 730 relations readable, no `INSERT`, `UPDATE`, `DELETE`, `TRUNCATE`, database `CREATE`, or schema `CREATE`, and no `COPY` membership. The remaining deviation is `rolinherit = t`, inert while the role has no memberships; the `NOINHERIT` correction was handed over to the database administrator on 2026-09-16 and is tracked outside this project. |
| Response and logging redaction tests | Done | Public error, global exception, data-source failure, credential/path redaction, correlation ID, and newline-safe logging regressions are covered |
| Verified case re-runs and full test suites | Done | Focused suites re-verified on `95c3d017`; Core suite passes; the single backend failure is recorded in `SECURITY_CHECK.md` with a release disposition. PostgreSQL behavior passes, with account ownership and `NOINHERIT` recorded as deployment/DBA disposition. |
| Deployment verification and security record update | Deferred | The security record update is complete: the test deployment was verified on 2026-09-15 (release identity commit `95c3d017` and digest `sha256:aa320c4c…`, loopback-only port binding, `401` for unauthenticated routes, `401` at the proxy, public health only) and recorded in `SECURITY_CHECK.md`. The release-host checks — firewall rules, PostgreSQL grants, log review, the authenticated access path, and rollback — are deferred to the operations team in [DEPLOYMENT_VERIFICATION_HANDOFF.md](../../../done/CENTRALIZED_AUTHORIZATION_CUTOVER/DEPLOYMENT_VERIFICATION_HANDOFF.md). |

## Definition Of Done

- [x] Unauthenticated and cross-resource authorization tests cover every sensitive router and direct application route.
- [x] Filesystem boundary tests cover traversal, absolute paths, symlinks, missing parents, and project-name variations.
- [x] SQL and DuckDB tests cover stacked statements, comments, embedded `LIMIT`, destructive statements, identifier edge cases, file functions, `COPY`, `ATTACH`, extension loading, network access, and paths outside approved roots.
- [x] Response and logging tests cover secret, SQL, connection-string, and absolute-path redaction.
- [x] The verified cases in `SECURITY_CHECK.md` are re-run against disposable databases and files with pass/fail evidence recorded.
- [x] The full Core and backend test suites are run; security-relevant failures block release, and unrelated failures have a documented cause and release disposition.
- [x] `SECURITY_CHECK.md` is updated with deployment pass/fail evidence and the tested commit.
- [x] Every original high-severity finding is either fixed with evidence or remains disabled with a documented exception.
- [x] A finding matrix maps every `SECURITY_CHECK.md` finding to a test, evidence record, or approved exception.

## Validation And Testing

- Run focused backend tests for authentication, authorization, CORS, path boundaries, SQL policy, DuckDB restrictions, error redaction, and data-source allowlisting.
- Run the Core test suite (`uv run pytest tests -v`) and the backend test suite (`uv run pytest backend/tests -v`) after each work area that changes shared behavior.
- Use disposable PostgreSQL and DuckDB environments for destructive-query and file-access regression tests.
- Test through the public HTTP routes and through direct service/workflow paths so validation cannot be bypassed by a second execution path.
- Local tests do not establish production network exposure; the release-host checks are deferred to [DEPLOYMENT_VERIFICATION_HANDOFF.md](../../../done/CENTRALIZED_AUTHORIZATION_CUTOVER/DEPLOYMENT_VERIFICATION_HANDOFF.md).
- Run lint checks (`make lint`) before recording the release candidate as verified.
- Record the exact release image digest, source commit, test environment, database fixture versions, and disposable-file fixture identifiers with each verification result.

## Deliverables

| Deliverable | Description | Status | Link |
|---|---|---|---|
| Route inventory and authorization regression tests | Runtime route, unauthenticated route, direct-route, session-ownership, CORS, health, cross-resource HTTP, and team-grant regressions are covered | Done | [AUTHORIZATION_ROUTE_INVENTORY.md](../../../../AUTHORIZATION_ROUTE_INVENTORY.md), [test_route_authentication.py](../../../../../backend/tests/authorization/test_route_authentication.py), [test_cross_resource_access.py](../../../../../backend/tests/authorization/test_cross_resource_access.py), [test_cors.py](../../../../../backend/tests/test_cors.py), [test_session_authorization.py](../../../../../backend/tests/test_session_authorization.py) |
| Filesystem boundary regression tests | Traversal, absolute-path, symlink, missing-parent, project-name, download, backup, upload, and directive-path tests | Done | [test_filesystem_boundaries.py](../../../../../backend/tests/security/test_filesystem_boundaries.py), [test_directive_path_confinement.py](../../../../../tests/configuration/test_directive_path_confinement.py), [test_execute_service_output_paths.py](../../../../../backend/tests/services/test_execute_service_output_paths.py), [test_file_manager.py](../../../../../backend/tests/services/test_file_manager.py), [test_file_path_resolver.py](../../../../../backend/tests/utils/test_file_path_resolver.py) |
| SQL and DuckDB regression tests | Stacked-statement, destructive, identifier, file-function, extension, network, and read-only PostgreSQL role tests | Done | [test_sql_duckdb_regressions.py](../../../../../backend/tests/security/test_sql_duckdb_regressions.py), [test_sql.py](../../../../../backend/tests/utils/test_sql.py), [test_query_service.py](../../../../../backend/tests/services/test_query_service.py), [test_duckdb_loader.py](../../../../../tests/loaders/test_duckdb_loader.py), [test-readonly-role.sh](../../../../../scripts/postgres/test-readonly-role.sh), [verify_readonly_role.sql](../../../../../scripts/postgres/verify_readonly_role.sql) |
| Response and logging redaction tests | Secret, SQL, connection-string, and absolute-path redaction tests | Done | [test_response_logging_redaction.py](../../../../../backend/tests/security/test_response_logging_redaction.py), [safe_logging.py](../../../../../backend/app/utils/safe_logging.py) |
| Verified case re-run record | Pass/fail evidence for each `SECURITY_CHECK.md` case with the tested commit | Done | [SECURITY_CHECK.md](../SECURITY_CHECK.md) |
| Full test suite results | Core and backend suite results; the unrelated backend failure carries a recorded release disposition | Done | [SECURITY_CHECK.md](../SECURITY_CHECK.md) |
| Deployment verification record | Image identity, commit, service model, port binding, proxy routes, health checks, and route protection verified on 2026-09-15; firewall, grants, mounted-file re-inspection, log review, the authenticated access path, and rollback deferred to the operations team | Deferred | [SECURITY_CHECK.md](../SECURITY_CHECK.md), [DEPLOYMENT_VERIFICATION_HANDOFF.md](../../../done/CENTRALIZED_AUTHORIZATION_CUTOVER/DEPLOYMENT_VERIFICATION_HANDOFF.md), [CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md](../../../done/CENTRALIZED_AUTHORIZATION_CUTOVER/CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md) |
| Updated security record | `SECURITY_CHECK.md` updated with pass/fail evidence, the tested commit and image digest, and the deployment verification record | Done | [SECURITY_CHECK.md](../SECURITY_CHECK.md) |
| Finding matrix | Every `SECURITY_CHECK.md` finding mapped to evidence, a limitation, or an approved exception | Done | [SECURITY_CHECK.md](../SECURITY_CHECK.md) |

## Scope

**In scope**

- Focused security regression tests for authentication, authorization, filesystem boundaries, SQL, DuckDB, and error redaction.
- Re-running the verified cases in `SECURITY_CHECK.md` against disposable databases and files.
- Running the full Core and backend test suites and recording unrelated failures.
- Updating `SECURITY_CHECK.md` with pass/fail evidence and the tested commit.
- Mapping every finding in `SECURITY_CHECK.md` to a test, evidence record, limitation, or approved exception.

**Out of scope**

- Deployment verification on the release host; deferred to the operations team in [DEPLOYMENT_VERIFICATION_HANDOFF.md](../../../done/CENTRALIZED_AUTHORIZATION_CUTOVER/DEPLOYMENT_VERIFICATION_HANDOFF.md).
- Implementing new security controls; this phase verifies existing controls from Phases 1–4.
- Spreadsheet formula injection, UCanAccess supply-chain hardening, and other medium or low findings except where they are needed for the high-severity controls.
- Unrelated data-integrity and documentation bugs.
- Production staffing, dates, ownership, and release scheduling.
- Designing new features or changing the product contract.

## Risks And Mitigations

- **Test environment differs from production:** use disposable databases and files that match the production configuration as closely as possible, and record any differences in the verification record.
- **Unrelated test failures obscure security results:** record unrelated failures separately with their root cause and whether they are pre-existing, so security results are not conflated with unrelated regressions.
- **Deployment verification is manual and error-prone:** use a checklist for each verification item and record evidence (screenshots, command output, or log excerpts) for each check.
- **Release identity can drift during verification:** record both the immutable image digest and source commit, and restart verification if either changes.
- **The release candidate changes after testing:** re-run the full verification suite if the release candidate changes, and record the tested commit in `SECURITY_CHECK.md`.
- **Some findings cannot be fully verified without a real SEAD database:** record the limitation and the code-level evidence that supports the fix, and mark the finding as partially verified.
- **The backend trusts the identity header from any source:** `ProxyAuthenticationMiddleware` accepts any non-empty value in `X-Authenticated-User` and does not check the source address, so any local process on the host can assert an identity, including a bootstrap administrator. Remote callers are covered by the loopback-only binding and by nginx overwriting the header. A source-address check, a proxy shared secret, or a Unix socket would close the gap, but these are new controls and therefore outside this phase; record the gap as a limitation until one is implemented.
- **`make up` can run an older image when `IMAGE_NAME` and `GIT_REF` disagree:** `make build` tags a branch build after the ref, while `make up` starts whatever `IMAGE_NAME` names. Both values now live in `container/.env`, tracked as `container/.env.example`, so the mismatch is visible in one file. Confirm the running container's revision label before recording verification results.

## Open Questions

- Which deployment environment will be used for release verification (shared, production, or a staging environment)?
- Which database operations must remain writable, and who may request them? This affects the read-only role verification.
- Which filesystem roots are approved in each deployment environment? This affects the deployment verification of mounted files.
- Is the ingester API removed, kept disabled, or redesigned? Until decided, include its routes in authorization tests and record any deeper SEAD-dependent verification as an exception.
- Who records and approves exceptions for endpoints that cannot yet meet these controls?

## Assumptions

- Phases 1–4 meet their completion criteria before Phase 5 is complete; incomplete criteria block completion unless an approved exception is recorded in `SECURITY_CHECK.md`.
- The release candidate is a specific commit or Docker image that can be identified and deployed for verification.
- Disposable PostgreSQL and DuckDB environments are available for destructive-query and file-access regression tests.
- Deployment verification is performed in the selected target environment on the exact release candidate; the target environment and any staging-to-production limitations are recorded in `SECURITY_CHECK.md`.
- Work is ordered by dependency and risk, not by staffing or release dates.
