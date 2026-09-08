# Phase Task Plan: Critical Security Mitigations

## Phase Summary

- Status: In progress
- Proposal: [MITIGATE_SECURITY_ISSUES.md](./MITIGATE_SECURITY_ISSUES.md)
- Review record: [SECURITY_CHECK.md](./SECURITY_CHECK.md)
- Goal: Enforce nginx-authenticated identity in FastAPI and remove the highest-severity file, database, configuration, and secret-access paths before restoring shared or production use

**Acceptance Criteria**

- [ ] Sensitive API operations require a verified nginx-authenticated identity and application-side authorization.
- [ ] The API cannot read or write files outside approved server-owned roots.
- [ ] PostgreSQL and DuckDB execution reject destructive, multi-statement, external-file, extension-loading, and network-capable operations.
- [ ] Client responses do not disclose secrets, connection details, SQL, or sensitive filesystem paths.
- [ ] Production exposure, credentials, database grants, and mounted files are verified on the exact release commit.

## Work Breakdown

### Phase 0: Contain Exposure And Assess Impact

**Objective**

Prevent further access while the application controls are being implemented.

**Tasks**

- [ ] Restrict or disable public access to the backend port and verify the effective firewall and proxy routes.
- [ ] Disable execution, raw YAML mutation, arbitrary data-source creation, and ingester endpoints where operationally possible.
- [ ] Protect or disable Swagger, OpenAPI, Redoc, and the public documentation mount in shared and production environments.
- [ ] Identify deployed environment variables, database credentials, `.pgpass` mounts, project directories, output directories, and backup directories.
- [ ] Rotate credentials that may have been reachable and record the rotation result.
- [ ] Review application, proxy, database, and container logs for suspicious file, query, data-source, and project activity.

**Completion Criteria**

The service is not reachable by untrusted users, or the exposure is controlled by a documented temporary access restriction. Potentially exposed credentials and relevant logs have been assessed.

### Phase 1: Enforce Nginx Identity, Authorization, And CORS Controls

**Objective**

Ensure that sensitive operations require the verified identity authenticated by nginx and an application-side authorization decision.

**Tasks**

- [x] Document the nginx-to-FastAPI identity contract, including the trusted header or token, failure behavior, and key or header verification.
- [x] Configure nginx to strip client-supplied identity values and pass only the verified identity to FastAPI.
- [x] Enforce the verified identity at the FastAPI application boundary, including routes outside `api_router`.
- [x] Implement the [centralized authorization system](./done/CENTRALIZED_AUTHORIZATION_SYSTEM.md) for projects, shared data sources, logs, schemas, queries, and tasks by following its [completed task plan](./CENTRALIZED_AUTHORIZATION_SYSTEM_TASK_PLAN.md). Track the remaining upload, output, backup, and operation identifier work in [SERVER_OWNED_RESOURCE_IDENTIFIERS.md](./SERVER_OWNED_RESOURCE_IDENTIFIERS.md).
- [x] Reject direct requests that do not come through the trusted nginx path; enforce this with Docker and network controls as well as application checks.
- [x] Keep health checks public only when required by deployment health checks.
- [x] Separate project editing sessions from authenticated identity and verify session ownership.
- [x] Restrict CORS to configured trusted origins; remove broad development-domain defaults from shared and production settings.
- [ ] If cookie authentication is used, add CSRF protection and secure cookie attributes.
- [x] Record [native application authentication](../future/NATIVE_APPLICATION_AUTHENTICATION.md) as future work without making it a dependency for this phase.

**Completion Criteria**

Requests without a verified nginx identity receive `401` or `403` for every sensitive route. Authenticated users cannot access another user or team's resources. Direct backend access is blocked. Unapproved origins cannot make credentialed requests.

### Phase 2: Constrain Filesystem And Project Configuration Access

**Objective**

Prevent API input and project configuration from selecting arbitrary server files or destinations.

**Tasks**

- [ ] Define approved roots for projects, uploads, backups, temporary files, and generated output.
- [ ] Add path resolution and containment checks before every read, write, download, upload, and directory creation.
- [ ] Apply the checks to execution `target`, ingester `source`, ingester `output_folder`, project names, `@include`, and `@load` paths.
- [ ] Reject absolute paths and traversal outside the approved root.
- [ ] Resolve symlinks before authorization and cover symlink and time-of-check/time-of-use cases in tests.
- [ ] Replace client-selected output destinations with server-generated paths where the product contract permits.
- [ ] Restrict or remove raw YAML mutation until its directive and persistence behavior is authorized.

**Completion Criteria**

The download endpoint cannot return arbitrary files. Execution and ingester operations cannot create or overwrite files outside their assigned roots. Directive resolution cannot escape the project or approved data roots.

### Phase 3: Enforce Safe SQL And Database Boundaries

**Objective**

Prevent query endpoints and workflow execution from modifying databases or accessing files through SQL.

**Tasks**

- [ ] Reject more than one non-empty SQL statement instead of returning a warning.
- [ ] Apply one execution policy to query validation, query execution, workflow execution, schema introspection, and `@internal` DuckDB execution.
- [ ] Replace keyword-only checks with a documented read-only SQL policy and reject DDL, DML, `COPY`, `ATTACH`, extension operations, and other side-effecting statements.
- [ ] Correct result-limit enforcement so a user-supplied `LIMIT` cannot bypass the server limit.
- [ ] Replace interpolated SQL identifiers and metadata filters with safe, dialect-aware identifier handling.
- [ ] Configure a dedicated PostgreSQL role with only the required read privileges. Confirm it is not an object owner or member of a write-capable role.
- [ ] Disable DuckDB external access and extension loading for untrusted queries. If controlled file access is required, configure explicit allowed paths and directories.
- [ ] Add resource limits for query duration, result size, memory, and concurrency.

**Completion Criteria**

Stacked statements and destructive SQL fail on every execution path. The application database role cannot alter or destroy production data. DuckDB cannot read or write arbitrary files, access the network, or load extensions from untrusted SQL.

### Phase 4: Restrict Data Sources, Ingesters, And Error Disclosure

**Objective**

Prevent server-side network access and remove secrets from API responses.
Detailed phase-4 work is tracked in [MITIGATE_SECURITY_ISSUES_PHASE_4_TASK_PLAN.md](./MITIGATE_SECURITY_ISSUES_PHASE_4_TASK_PLAN.md).
Ingester-specific route and destination work is tracked in [INGESTER_AUTHORIZATION_TASKS.md](../CHANGE_REQUEST_INGESTER/INGESTER_AUTHORIZATION_TASKS.md).

**Tasks**

- [ ] Replace arbitrary client-supplied database connection settings with named, server-managed data sources.
- [ ] Allow only approved drivers, hosts, ports, schemas, and connection destinations.
- [ ] Add DNS/IP validation and network egress controls for localhost, private ranges, metadata services, and unrelated internal services.
- [ ] Resolve only approved environment-variable names and prevent client-controlled configuration from selecting arbitrary server variables.
- [ ] Preserve database passwords correctly and prevent passwordless fallback where authentication is required.
- [ ] Replace raw exception responses with stable public messages and correlation IDs.
- [ ] Redact credentials, environment values, connection strings, SQL, and sensitive paths from logs and error details.
- [ ] Prevent user-controlled newlines from forging log records.

**Completion Criteria**

Data-source requests cannot probe or connect to unapproved destinations. Error responses and logs do not expose secrets or sensitive implementation details. Ingester disposition and destination-gating work are documented in the dedicated ingester authorization plan.

### Phase 5: Security Regression And Release Verification

**Objective**

Prove that the mitigations hold on the release candidate and in the deployed environment.

**Tasks**

- [ ] Add unauthenticated and cross-resource authorization tests for every sensitive router and direct application route.
- [ ] Add filesystem boundary tests for traversal, absolute paths, symlinks, missing parents, and project-name variations.
- [ ] Add SQL tests for stacked statements, comments, embedded `LIMIT`, destructive statements, identifier edge cases, and read-only database roles.
- [ ] Add DuckDB tests for file functions, `COPY`, `ATTACH`, extension loading, network access, and paths outside approved roots.
- [ ] Add response and logging tests for secret, SQL, connection-string, and absolute-path redaction.
- [ ] Re-run the verified cases in `SECURITY_CHECK.md` against disposable databases and files.
- [ ] Run the full Core and backend test suites and record unrelated failures separately.
- [ ] Verify the exact image and release commit, Docker port binding, proxy routes, firewall rules, environment variables, database grants, mounted files, and logs.
- [ ] Update `SECURITY_CHECK.md` with pass/fail evidence and the tested commit.

**Completion Criteria**

Focused security tests, regression tests, and deployment checks pass on the exact release candidate. Every original high-severity finding is either fixed with evidence or remains disabled with a documented exception.

## Progress Tracker

| Area | Status | Notes |
|---|---|---|
| Exposure containment and impact assessment | Not started |  |
| Authentication, authorization, and CORS | In progress | Proxy identity, session ownership, loopback binding, and CORS defaults implemented; resource ACLs remain |
| Filesystem and project configuration boundaries | Not started |  |
| SQL, PostgreSQL, and DuckDB restrictions | Not started |  |
| Data-source and error handling controls | Not started | Ingester-specific disposition and destination gating are tracked in [INGESTER_AUTHORIZATION_TASKS.md](../CHANGE_REQUEST_INGESTER/INGESTER_AUTHORIZATION_TASKS.md) |
| Security regression and release verification | Not started |  |

## Definition Of Done

- [ ] Temporary exposure controls are in place or a documented exception has been approved.
- [ ] FastAPI enforces the verified nginx identity and resource authorization on all sensitive routes, including routes outside the API router.
- [ ] Project, upload, output, backup, temporary, directive, and ingester paths are confined to approved roots.
- [ ] Query validation and execution use the same safe policy on all database and DuckDB paths.
- [ ] Production database access uses a least-privilege role and has been verified against the actual grants.
- [ ] Data-source network destinations are server-managed or explicitly allowlisted.
- [ ] Responses and logs redact secrets, SQL, connection details, and sensitive paths.
- [ ] The original verified reproduction cases fail for the intended security reason.
- [ ] Focused tests and the relevant full test suites pass, with unrelated failures recorded.
- [ ] Deployment verification is complete for the exact release commit.
- [ ] Remaining medium, low, and correctness findings are recorded for follow-up rather than silently treated as fixed.

## Validation And Testing

- Use focused backend tests for authentication, authorization, CORS, path boundaries, SQL policy, DuckDB restrictions, error redaction, and data-source allowlisting.
- Run the Core and backend test suites defined in the repository workflow after each phase that changes shared behavior.
- Use disposable PostgreSQL and DuckDB environments for destructive-query and file-access regression tests.
- Test through the public HTTP routes and through direct service/workflow paths so validation cannot be bypassed by a second execution path.
- Repeat deployment checks after container or proxy changes; local tests do not establish production network exposure.

## Deliverables

| Deliverable | Description | Status | Link |
|---|---|---|---|
| Containment record | Exposure, credential, log, firewall, and proxy assessment | Not started | TBD |
| Access-control implementation | Authentication, authorization, session ownership, CSRF, and CORS controls | In progress | Completed authorization design: [CENTRALIZED_AUTHORIZATION_SYSTEM.md](./done/CENTRALIZED_AUTHORIZATION_SYSTEM.md); follow-up resource identifiers: [SERVER_OWNED_RESOURCE_IDENTIFIERS.md](./SERVER_OWNED_RESOURCE_IDENTIFIERS.md); CSRF and broader controls remain |
| Boundary-control implementation | Filesystem, YAML directive, upload, download, and execution-target restrictions | Not started | TBD |
| Query safety implementation | SQL policy, database role controls, DuckDB restrictions, and resource limits | Not started | TBD |
| Data-source and error handling controls | Server-managed destinations, approved environment-variable resolution, and public error redaction | Not started | TBD |
| Security regression suite | Tests for the verified review cases and bypass paths | Not started | TBD |
| Release verification record | Results for the exact image, commit, and deployed configuration | Not started | TBD |

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
