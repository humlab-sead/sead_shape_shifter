# Phase Plan: Critical Security Mitigations

## Phase Summary

- Status: In progress — only the phase 0 containment and assessment work remains open
- Proposal: [MITIGATE_SECURITY_ISSUES.md](./MITIGATE_SECURITY_ISSUES.md)
- Review record: [SECURITY_CHECK.md](./SECURITY_CHECK.md)
- Goal: Enforce nginx-authenticated identity in FastAPI and remove the highest-severity file, database, configuration, and secret-access paths before restoring shared or production use

**Acceptance Criteria**

Completion requires that sensitive API operations demand a verified nginx-authenticated identity and an application-side authorization decision; that the API cannot read or write files outside approved server-owned roots; that PostgreSQL and DuckDB execution reject destructive, multi-statement, external-file, extension-loading, and network-capable operations; that client responses disclose no secrets, connection details, SQL, or sensitive filesystem paths; and that production exposure, credentials, database grants, and mounted files are verified on the exact release commit.

## Work Breakdown

### Phase 0: Contain Exposure And Assess Impact

**Objective**

Prevent further access while the application controls are being implemented.

**Description**

Containment and assessment while the application controls were being built: restrict or disable public access to the backend port and the risky endpoints (execution, raw YAML mutation, arbitrary data-source creation, ingesters), protect the Swagger, OpenAPI, Redoc, and documentation routes, inventory the deployed environment variables, credentials, `.pgpass` mounts, and data directories, rotate credentials that may have been reachable, and review application, proxy, database, and container logs.

**Task record**

Not started, and no separate task plan exists for this phase. The firewall, log review, mount, and credential checks that overlap this scope are assigned to the operations team in [DEPLOYMENT_VERIFICATION_HANDOFF.md](./DEPLOYMENT_VERIFICATION_HANDOFF.md).

**Completion Criteria**

The service is not reachable by untrusted users, or the exposure is controlled by a documented temporary access restriction. Potentially exposed credentials and relevant logs have been assessed.

### Phase 1: Enforce Nginx Identity, Authorization, And CORS Controls

**Objective**

Ensure that sensitive operations require the verified identity authenticated by nginx and an application-side authorization decision.

**Description**

The nginx-to-FastAPI identity contract was documented, nginx strips client-supplied identity values and passes only the verified identity, and FastAPI enforces that identity at the application boundary, including routes outside `api_router`. Requests that bypass the trusted proxy path are rejected by container and network controls as well as application checks, health checks stay public only where deployment health checks need them, project editing sessions are separated from authenticated identity with session ownership verified, and CORS is restricted to configured trusted origins. The conditional CSRF task was withdrawn because the deployment does not authenticate API requests with cookies, and native application authentication is recorded as future work.

**Task record**

[CENTRALIZED_AUTHORIZATION_SYSTEM.md](./done/CENTRALIZED_AUTHORIZATION_SYSTEM.md) and its [task plan](./done/CENTRALIZED_AUTHORIZATION_SYSTEM_TASK_PLAN.md) are the record of the authorization work; no separate phase-1 task plan exists. The remaining upload, output, backup, and operation identifier work is tracked in [SERVER_OWNED_RESOURCE_IDENTIFIERS.md](../future/SERVER_OWNED_RESOURCE_IDENTIFIERS.md).

**Completion Criteria**

Requests without a verified nginx identity receive `401` or `403` for every sensitive route. Authenticated users cannot access another user or team's resources. Direct backend access is blocked. Unapproved origins cannot make credentialed requests.

### Phase 2: Constrain Filesystem And Project Configuration Access

**Objective**

Prevent API input and project configuration from selecting arbitrary server files or destinations.

**Description**

Approved roots for projects, uploads, backups, temporary files, and generated output, with path resolution and containment checks before every read, write, download, upload, and directory creation. The checks cover the execution `target`, ingester `source` and `output_folder`, project names, and the `@include` and `@load` directives; absolute paths, traversal, and symlink escapes are rejected, and client-selected output destinations were replaced with server-generated paths where the product contract permits. Raw YAML mutation is restricted until its directive and persistence behavior is authorized.

**Task record**

[MITIGATE_SECURITY_ISSUES_PHASE_2_TASK_PLAN.md](./done/MITIGATE_SECURITY_ISSUES_PHASE_2_TASK_PLAN.md) — complete. Ingester source and destination boundaries are deferred from that plan to [INGESTER_FILESYSTEM_BOUNDARIES.md](../CHANGE_REQUEST_INGESTER/INGESTER_FILESYSTEM_BOUNDARIES.md).

**Completion Criteria**

The download endpoint cannot return arbitrary files. Execution and ingester operations cannot create or overwrite files outside their assigned roots. Directive resolution cannot escape the project or approved data roots.

### Phase 3: Enforce Safe SQL And Database Boundaries

**Objective**

Prevent query endpoints and workflow execution from modifying databases or accessing files through SQL.

**Description**

One read-only execution policy now covers query validation, query execution, workflow execution, schema introspection, and `@internal` DuckDB execution, so more than one non-empty statement is rejected instead of warned about, and DDL, DML, `COPY`, `ATTACH`, extension operations, and other side-effecting statements are refused. Result-limit enforcement no longer accepts a user-supplied `LIMIT`, interpolated identifiers and metadata filters were replaced with safe dialect-aware handling, resource limits cover query duration, result size, memory, and concurrency, and DuckDB external access and extension loading are disabled for untrusted queries. The PostgreSQL role carries only the required read privileges.

**Task record**

[MITIGATE_SECURITY_ISSUES_PHASE_3_TASK_PLAN.md](./done/MITIGATE_SECURITY_ISSUES_PHASE_3_TASK_PLAN.md) — complete, with the results in [MITIGATE_SECURITY_ISSUES_PHASE_3_VALIDATION.md](./done/MITIGATE_SECURITY_ISSUES_PHASE_3_VALIDATION.md).

**Completion Criteria**

Stacked statements and destructive SQL fail on every execution path. The application database role cannot alter or destroy production data. DuckDB cannot read or write arbitrary files, access the network, or load extensions from untrusted SQL.

### Phase 4: Restrict Data Sources, Ingesters, And Error Disclosure

**Objective**

Prevent server-side network access and remove secrets from API responses.

**Description**

Arbitrary client-supplied database connection settings were replaced by named, server-managed data sources limited to approved drivers, hosts, ports, schemas, and destinations, with DNS and IP validation plus egress controls for localhost, private ranges, metadata services, and unrelated internal services. Only approved environment-variable names resolve, passwords are preserved without a passwordless fallback, raw exceptions were replaced by stable public messages with correlation IDs, and credentials, environment values, connection strings, SQL, and sensitive paths are redacted from logs and error details. User-controlled newlines can no longer forge log records.

**Task record**

[MITIGATE_SECURITY_ISSUES_PHASE_4_TASK_PLAN.md](./done/MITIGATE_SECURITY_ISSUES_PHASE_4_TASK_PLAN.md) — complete. Ingester route and destination work is tracked in [INGESTER_AUTHORIZATION_TASKS.md](../CHANGE_REQUEST_INGESTER/INGESTER_AUTHORIZATION_TASKS.md).

**Completion Criteria**

Data-source requests cannot probe or connect to unapproved destinations. Error responses and logs do not expose secrets or sensitive implementation details. Ingester disposition and destination-gating work are documented in the dedicated ingester authorization plan.

### Phase 5: Security Regression And Release Verification

**Objective**

Prove that the mitigations hold on the release candidate and in the deployed environment.

**Description**

Focused regression suites now cover unauthenticated and cross-resource authorization on every sensitive route, filesystem boundaries, SQL and DuckDB policy including stacked statements, destructive statements, file functions, extension loading, and the read-only database role, and response and logging redaction. The verified cases in `SECURITY_CHECK.md` were re-run against disposable databases and files, the full Core and backend suites were run with unrelated failures recorded separately, and `SECURITY_CHECK.md` carries the pass/fail evidence, the finding matrix, and the tested commit. Release identity and port binding were verified on the test deployment; the remaining release-host checks — firewall rules, PostgreSQL grants, mounted-file re-inspection, log review, the authenticated access path, and rollback — are deferred to the operations team.

**Task record**

[MITIGATE_SECURITY_ISSUES_PHASE_5_TASK_PLAN.md](./done/MITIGATE_SECURITY_ISSUES_PHASE_5_TASK_PLAN.md) — complete, with the release-host checks in [DEPLOYMENT_VERIFICATION_HANDOFF.md](./DEPLOYMENT_VERIFICATION_HANDOFF.md).

**Completion Criteria**

Focused security tests, regression tests, and deployment checks pass on the exact release candidate. Every original high-severity finding is either fixed with evidence or remains disabled with a documented exception.

## Progress Tracker

| Area | Status | Notes |
|---|---|---|
| Exposure containment and impact assessment | Not started | No separate task plan; the firewall, log review, mount, and credential checks that overlap this scope are assigned to the operations team in [DEPLOYMENT_VERIFICATION_HANDOFF.md](./DEPLOYMENT_VERIFICATION_HANDOFF.md) |
| Authentication, authorization, and CORS | Done | Proxy identity, direct-route protection, session ownership, CORS, health disclosure, cross-resource HTTP, and team-grant regressions are covered; implementation recorded in [CENTRALIZED_AUTHORIZATION_SYSTEM_TASK_PLAN.md](./done/CENTRALIZED_AUTHORIZATION_SYSTEM_TASK_PLAN.md) |
| Filesystem and project configuration boundaries | Done | Archived in [MITIGATE_SECURITY_ISSUES_PHASE_2_TASK_PLAN.md](./done/MITIGATE_SECURITY_ISSUES_PHASE_2_TASK_PLAN.md); ingester source and destination boundaries are deferred to [INGESTER_FILESYSTEM_BOUNDARIES.md](../CHANGE_REQUEST_INGESTER/INGESTER_FILESYSTEM_BOUNDARIES.md) |
| SQL, PostgreSQL, and DuckDB restrictions | Done | Archived in [MITIGATE_SECURITY_ISSUES_PHASE_3_TASK_PLAN.md](./done/MITIGATE_SECURITY_ISSUES_PHASE_3_TASK_PLAN.md), with results in [MITIGATE_SECURITY_ISSUES_PHASE_3_VALIDATION.md](./done/MITIGATE_SECURITY_ISSUES_PHASE_3_VALIDATION.md) |
| Data-source and error handling controls | Done | Data-source inventory, server-managed destinations, and public error redaction are complete; detailed work is archived in [MITIGATE_SECURITY_ISSUES_PHASE_4_TASK_PLAN.md](./done/MITIGATE_SECURITY_ISSUES_PHASE_4_TASK_PLAN.md) |
| Security regression and release verification | Done | Phase 5 is complete and archived in [MITIGATE_SECURITY_ISSUES_PHASE_5_TASK_PLAN.md](./done/MITIGATE_SECURITY_ISSUES_PHASE_5_TASK_PLAN.md); the release-host checks are deferred to the operations team in [DEPLOYMENT_VERIFICATION_HANDOFF.md](./DEPLOYMENT_VERIFICATION_HANDOFF.md) |

## Definition Of Done

The plan is done when the temporary exposure controls are in place or an exception is approved. FastAPI must enforce the verified nginx identity and resource authorization on every sensitive route, including routes outside the API router, and project, upload, output, backup, temporary, directive, and ingester paths must be confined to approved roots. Query validation and execution must apply the same safe policy on every database and DuckDB path, and production database access must use a least-privilege role verified against the actual grants. Data-source network destinations must be server-managed or explicitly allowlisted, and responses and logs must redact secrets, SQL, connection details, and sensitive paths. The original verified reproduction cases must fail for the intended security reason, focused tests and the relevant full test suites must pass with unrelated failures recorded, and deployment verification must be complete for the exact release commit. Remaining medium, low, and correctness findings are recorded for follow-up rather than silently treated as fixed.

## Validation And Testing

- Use focused backend tests for authentication, authorization, CORS, path boundaries, SQL policy, DuckDB restrictions, error redaction, and data-source allowlisting.
- Run the Core and backend test suites defined in the repository workflow after each phase that changes shared behavior.
- Use disposable PostgreSQL and DuckDB environments for destructive-query and file-access regression tests.
- Test through the public HTTP routes and through direct service/workflow paths so validation cannot be bypassed by a second execution path.
- Repeat deployment checks after container or proxy changes; local tests do not establish production network exposure.

## Deliverables

| Deliverable | Description | Status | Link |
|---|---|---|---|
| Containment record | Exposure, credential, log, firewall, and proxy assessment | Not started | Overlapping checks are assigned to the operations team in [DEPLOYMENT_VERIFICATION_HANDOFF.md](./DEPLOYMENT_VERIFICATION_HANDOFF.md) |
| Access-control implementation | Authentication, authorization, session ownership, CSRF, and CORS controls | Done | [CENTRALIZED_AUTHORIZATION_SYSTEM.md](./done/CENTRALIZED_AUTHORIZATION_SYSTEM.md), [CENTRALIZED_AUTHORIZATION_SYSTEM_TASK_PLAN.md](./done/CENTRALIZED_AUTHORIZATION_SYSTEM_TASK_PLAN.md); the conditional CSRF task was withdrawn because the deployment does not use cookie authentication, and the resource-identifier follow-up is a separate proposal: [SERVER_OWNED_RESOURCE_IDENTIFIERS.md](../future/SERVER_OWNED_RESOURCE_IDENTIFIERS.md) |
| Boundary-control implementation | Filesystem, YAML directive, upload, download, and execution-target restrictions | Done | [MITIGATE_SECURITY_ISSUES_PHASE_2_TASK_PLAN.md](./done/MITIGATE_SECURITY_ISSUES_PHASE_2_TASK_PLAN.md); ingester boundaries deferred to [INGESTER_FILESYSTEM_BOUNDARIES.md](../CHANGE_REQUEST_INGESTER/INGESTER_FILESYSTEM_BOUNDARIES.md) |
| Query safety implementation | SQL policy, database role controls, DuckDB restrictions, and resource limits | Done | [MITIGATE_SECURITY_ISSUES_PHASE_3_TASK_PLAN.md](./done/MITIGATE_SECURITY_ISSUES_PHASE_3_TASK_PLAN.md), [MITIGATE_SECURITY_ISSUES_PHASE_3_VALIDATION.md](./done/MITIGATE_SECURITY_ISSUES_PHASE_3_VALIDATION.md) |
| Data-source and error handling controls | Server-managed destinations, approved environment-variable resolution, and public error redaction | Done | [MITIGATE_SECURITY_ISSUES_PHASE_4_TASK_PLAN.md](./done/MITIGATE_SECURITY_ISSUES_PHASE_4_TASK_PLAN.md); ingester route work tracked in [INGESTER_AUTHORIZATION_TASKS.md](../CHANGE_REQUEST_INGESTER/INGESTER_AUTHORIZATION_TASKS.md) |
| Security regression suite | Tests for the verified review cases and bypass paths | Done | [MITIGATE_SECURITY_ISSUES_PHASE_5_TASK_PLAN.md](./done/MITIGATE_SECURITY_ISSUES_PHASE_5_TASK_PLAN.md); evidence and the finding matrix are in [SECURITY_CHECK.md](./SECURITY_CHECK.md) |
| Release verification record | Results for the exact image, commit, and deployed configuration | Deferred | [SECURITY_CHECK.md](./SECURITY_CHECK.md) holds the release identity, port binding, proxy, health, and route-protection results; the release-host checks are deferred to the operations team in [DEPLOYMENT_VERIFICATION_HANDOFF.md](./DEPLOYMENT_VERIFICATION_HANDOFF.md) |

## Scope

**In scope**

- The critical and high-severity findings from `SECURITY_CHECK.md`.
- The verified arbitrary file, SQL, DuckDB, configuration, environment-variable, SSRF, and authentication issues.
- Controls needed before shared or production use.

**Out of scope**

- Spreadsheet formula injection, UCanAccess supply-chain hardening, log formatting cleanup, and other medium or low findings except where they are needed for the high-severity controls.
- Unrelated data-integrity and documentation bugs.
- Production staffing, dates, ownership, and release scheduling.

## Risks And Mitigations

- **Existing projects use absolute paths:** provide a migration rule to approved roots and reject unsafe paths with a clear, non-sensitive error.
- **Existing workflows write to databases:** keep general query access read-only and define a separate, explicitly authorized write operation if required.
- **Proxy identity trust:** restrict backend access to nginx, strip spoofable identity headers, and validate the identity contract in FastAPI.
- **Authentication changes frontend behavior:** preserve the current editing workflow only after nginx-authenticated identity and session ownership are established.
- **DuckDB restrictions remove undocumented features:** support file imports through controlled loaders or uploads rather than re-enabling unrestricted SQL file access.
- **The report was not a production penetration test:** require deployment verification and log review before declaring the issue resolved.

## Open Questions

- Which nginx-to-FastAPI identity header or token contract and verification method will be used?
- When should native application authentication replace nginx authentication?
- What is the project and shared-data authorization model?
- Which database operations must remain writable, and who may request them?
- Which filesystem roots are approved in each deployment environment?
- Is the ingester API removed, kept disabled, or redesigned?
- Who records and approves exceptions for endpoints that cannot yet meet these controls?

## Assumptions

- The phases are ordered by risk reduction and dependency, not by staffing or release dates.
- Health checks may remain unauthenticated only if they expose no project, database, filesystem, or configuration data.
- The current `dev` findings remain relevant to this branch because the principal vulnerable files are unchanged.
