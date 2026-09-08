# Task Plan: Phase 3 — Enforce Safe SQL And Database Boundaries

## Phase Summary

- Status: In progress
- Proposal: [MITIGATE_SECURITY_ISSUES.md](./MITIGATE_SECURITY_ISSUES.md) (design §4 "Make database and SQL access read-only by default")
- Parent phase plan: [MITIGATE_SECURITY_ISSUES_PHASE_TASK_PLAN.md](./MITIGATE_SECURITY_ISSUES_PHASE_TASK_PLAN.md) (Phase 3)
- Goal: ensure every SQL and DuckDB execution path is single-statement, read-only by default, restricted to approved resources, and protected by least-privilege database and runtime controls

**Focus**

- Define one documented SQL policy and apply it to query validation, query execution, workflow execution, schema introspection, and internal DuckDB execution.
- Reject stacked statements, destructive statements, external-file access, extension loading, network-capable operations, and other side-effecting operations.
- Enforce result, duration, memory, and concurrency limits without allowing user SQL to bypass server controls.
- Replace unsafe SQL identifier and metadata-filter interpolation with validated, dialect-aware handling.
- Establish and verify a dedicated PostgreSQL role with only the privileges required by the application.

**Acceptance Criteria**

- [ ] Stacked statements and destructive SQL fail on every execution path.
- [ ] Query validation and execution use the same safe policy for PostgreSQL and DuckDB paths.
- [ ] User-supplied `LIMIT` clauses cannot bypass the server result limit.
- [ ] SQL identifiers and metadata filters cannot alter query structure through interpolation.
- [ ] The application PostgreSQL role cannot alter or destroy production data and is not an owner or member of a write-capable role.
- [ ] DuckDB cannot read or write arbitrary files, access the network, or load extensions from untrusted SQL.
- [ ] Query duration, result size, memory, and concurrency limits are enforced on supported execution paths.

## Work Breakdown

### 1. Define And Centralize The SQL Safety Policy

**Objective**

Provide one explicit policy for permitted read-only SQL and one validation path that every database execution surface uses.

**Tasks**

- [x] Inventory every PostgreSQL and DuckDB execution path, including query helpers, workflow execution, schema introspection, and `@internal` execution.
- [x] Document the permitted statement classes, rejected DDL and DML, rejected transaction and session controls, and rejected external-file, extension, and network operations.
- [x] Implement a shared validation entry point that rejects more than one non-empty statement, including statements separated by comments or whitespace.
- [x] Make query-service callers fail closed when validation rejects a query; do not execute the original query after returning a warning or diagnostic.
- [x] Ensure the same policy is applied before execution in the query service, SQL loaders, DuckDB loader, and DuckDB workspace paths.
- [x] Define stable, non-sensitive public errors for rejected SQL and retain detailed diagnostics only in redacted server-side logs.

**Completion Criteria**

Every identified execution path invokes the same read-only policy, and invalid or side-effecting SQL is rejected before reaching PostgreSQL or DuckDB.

### 2. Secure Query Construction And Result Limits

**Objective**

Prevent query construction from changing SQL structure and enforce server-owned result limits.

**Tasks**

- [ ] Review query construction and metadata filtering for interpolated identifiers, table names, column names, sort fields, and filter values.
- [ ] Add one validated, dialect-aware identifier helper for supported database engines and reject invalid or unsupported identifiers.
- [ ] Use bound parameters for values and preserve the distinction between identifiers and values in every query path.
- [ ] Correct result-limit enforcement so an existing user `LIMIT` cannot bypass the server limit; define behavior for absent, lower, and higher user limits.
- [ ] Enforce result-size limits on rows, serialized response size, or another documented server-owned measure where applicable.
- [ ] Add focused tests for quoted identifiers, malformed identifiers, comments, nested queries, existing `LIMIT` clauses, and filter values containing SQL metacharacters.

**Completion Criteria**

User input cannot alter query structure through identifiers or values, and every supported query path enforces the configured result limit.

### 3. Enforce PostgreSQL Least-Privilege Execution

**Objective**

Ensure the application database identity can perform only the approved read operations.

**Tasks**

- [ ] Identify the required database, schema, table, view, sequence, and function privileges for application reads and introspection.
- [ ] Define the dedicated application role and revoke write, ownership, role-membership, schema-modification, and other unnecessary privileges.
- [ ] Provide the deployment or database migration steps needed to create and maintain the role without embedding credentials in application configuration.
- [ ] Verify the role is not an object owner and is not a member of any write-capable or administrative role.
- [ ] Test representative allowed reads and representative denied DDL, DML, `COPY`, role, transaction-control, and schema-modification operations using the actual role.
- [ ] Record the grants and verification evidence in the release or operations record used by the parent security plan.

**Completion Criteria**

The deployed application role can perform required reads and introspection but cannot modify or destroy production data, and the effective grants are documented and verified.

### 4. Restrict DuckDB External Access And Extensions

**Objective**

Prevent internal DuckDB execution from becoming a file, extension, or network access primitive.

**Tasks**

- [ ] Apply the shared SQL policy to `@internal` DuckDB execution before opening or executing the query.
- [ ] Disable DuckDB external access and extension loading for untrusted queries using the supported runtime configuration.
- [ ] Reject file-reading and file-writing functions, `COPY`, `ATTACH`, extension installation or loading, and network-capable functions on untrusted paths.
- [ ] If supported file access is required, define explicit approved directories and files and route access through the Phase 2 containment rules.
- [ ] Verify that denied operations cannot reach paths outside approved roots, load extensions, or make network requests.
- [ ] Add disposable-file tests for read, write, attach, copy, extension, network, traversal, absolute-path, and symlink cases.

**Completion Criteria**

Untrusted DuckDB execution cannot access arbitrary files, extensions, or networks, while any retained controlled file access is explicitly allowlisted and path-confined.

### 5. Add Query Resource Controls And Regression Evidence

**Objective**

Limit query impact and prove that all database boundaries remain enforced across direct and indirect execution paths.

**Tasks**

- [ ] Define supported limits for query duration, result size, memory, and concurrent executions, including behavior when a limit is exceeded.
- [ ] Implement the limits at the database, DuckDB, service, or worker boundary that can enforce them reliably for each execution path.
- [ ] Ensure cancellations and timeouts release database and DuckDB resources and do not leave partially completed operations available to callers.
- [ ] Add regression tests for all acceptance criteria through public API routes and direct service or workflow entry points.
- [ ] Re-run the SQL and DuckDB reproduction cases from [SECURITY_CHECK.md](./SECURITY_CHECK.md) against disposable databases and files.
- [ ] Record focused test results, known limitations, and any deferred writable workflow in the Phase 3 validation record.

**Completion Criteria**

Supported execution paths enforce resource limits, clean up after cancellation or timeout, and pass the documented SQL and DuckDB security regressions.

## Progress Tracker

| Area | Status | Notes |
|---|---|---|
| Shared SQL safety policy | Done | Shared statement and read-only checks cover the inventoried query, introspection, loader, workflow, and DuckDB workspace paths; public query errors no longer expose SQL or raw backend details |
| Query construction and result limits | Not started | Identifier handling and user `LIMIT` enforcement are open |
| PostgreSQL least-privilege role | Not started | Effective production grants require deployment verification |
| DuckDB external access and extensions | Not started | Controlled file access, if retained, depends on Phase 2 roots |
| Resource controls and regression evidence | Not started | Disposable database and file tests are required |

## Definition Of Done

- [ ] One documented read-only SQL policy rejects stacked, destructive, external-file, extension-loading, and network-capable operations on every supported execution path.
- [x] Query validation cannot return a warning while the rejected or unvalidated query is still executed on the covered query-service, SQL-loader, or DuckDB workspace paths.
- [ ] Identifier construction uses validated dialect-aware handling, values use parameters, and metadata filters cannot alter SQL structure.
- [ ] Server-owned result, duration, memory, and concurrency limits are enforced and cannot be bypassed by user SQL.
- [ ] The application PostgreSQL role has only the required read privileges and has been checked for ownership and inherited write capability.
- [ ] DuckDB external access and extension loading are disabled for untrusted queries; retained file access is explicitly allowed and confined to approved roots.
- [ ] Timeout and cancellation paths release resources and return stable, non-sensitive errors.
- [ ] Focused route, service, workflow, PostgreSQL, and DuckDB tests pass, with unrelated failures recorded separately.
- [ ] The verified security reproduction cases and effective database grants are recorded for the exact release candidate.

## Validation And Testing

- Add unit tests for statement counting, comments, quoted strings, destructive statement classes, identifier validation, parameter binding, and result-limit enforcement.
- Add service and workflow tests proving that validation is applied when execution bypasses the query helper endpoint.
- Add API tests for rejected stacked and destructive SQL and for stable error responses without SQL, connection details, or filesystem paths.
- Use a disposable PostgreSQL database to test allowed reads and denied writes, DDL, `COPY`, ownership, and role-membership assumptions.
- Use disposable DuckDB files and directories to test file functions, `COPY`, `ATTACH`, extension loading, network-capable operations, traversal, absolute paths, and symlinks.
- Test query duration, result size, memory, concurrency, timeout, cancellation, and resource cleanup for each execution path that supports the control.
- Re-run the documented cases from [SECURITY_CHECK.md](./SECURITY_CHECK.md) and preserve pass/fail evidence with the tested commit or image.
- Run the repository’s focused backend and core checks, then the relevant full suites and lint checks according to the development workflow.

## Deliverables

| Deliverable | Description | Status | Link |
|---|---|---|---|
| SQL safety policy | Documented statement and operation policy shared by PostgreSQL and DuckDB execution paths | Done | [docs/SQL_SAFETY_POLICY.md](../../../SQL_SAFETY_POLICY.md) |
| Shared validation and query-construction controls | Central validation, identifier handling, parameter binding, and result-limit enforcement | Not started | TBD |
| PostgreSQL role controls | Least-privilege role setup, grant verification, and disposable-database evidence | Not started | TBD |
| DuckDB restrictions | External-access, extension, network, and controlled-file restrictions with regression tests | Not started | TBD |
| Query resource controls | Duration, result-size, memory, concurrency, cancellation, and cleanup controls | Not started | TBD |
| Phase 3 validation record | Focused tests, reproduction results, known limitations, and exact release evidence | Not started | TBD |

## Scope

**In scope**

- SQL validation and execution in PostgreSQL and DuckDB paths, including indirect workflow and internal execution.
- Read-only database policy, statement restrictions, safe query construction, result limits, and query resource limits.
- PostgreSQL application-role privileges and verification of effective grants.
- DuckDB file, extension, and network restrictions, including controlled use of Phase 2 approved roots if required.
- Security regression tests and release evidence for this phase.

**Out of scope**

- Authentication, resource authorization, and project ownership, which are owned by Phase 1 and the centralized authorization system.
- General filesystem root definitions and non-DuckDB file endpoints, which are owned by Phase 2.
- Data-source host allowlisting, DNS/IP validation, SSRF prevention, and network egress policy for client-selected connections, which are owned by Phase 4.
- Spreadsheet formula neutralization, UCanAccess hardening, and unrelated data-integrity fixes.
- Designing a separate authorized write API; any required writable workflow is an open decision and must not weaken the default read-only query boundary.

## Risks And Mitigations

- **Undocumented writable workflows:** inventory execution paths first; keep general query access read-only and record any required write operation as a separately authorized design.
- **Parser and dialect differences:** define supported SQL dialects and test the policy against the actual PostgreSQL and DuckDB parsers or execution behavior rather than relying on keyword checks alone.
- **Limit enforcement gaps:** enforce limits at more than one layer where needed and test user-supplied `LIMIT`, nested queries, large rows, and cancellation.
- **DuckDB feature loss:** provide controlled loaders or approved file inputs for supported imports instead of restoring unrestricted external SQL access.
- **Deployment drift:** verify effective PostgreSQL grants and DuckDB runtime settings on the exact release image and environment.

## Open Questions

- Which PostgreSQL schemas, tables, views, and introspection operations are required by the current application role?
- Which SQL dialects and statement forms must the shared policy support?
- Which existing workflows genuinely require database writes, and will they receive a separate explicitly authorized operation?
- Is controlled DuckDB file access required after Phase 2 path confinement, or can all supported imports use loaders and uploads?
- Which resource-limit values are appropriate for development, shared, and production environments?
- Where will the exact grant, runtime-setting, and release verification evidence be maintained?

## Assumptions

- Phase 1 authorization is enforced before database and query controls are considered complete.
- Phase 2 approved roots and containment checks are available before controlled DuckDB file access is enabled.
- The application database role is treated as read-only by default; no existing writable behavior is presumed to be required.
- Deployment verification is required because local tests cannot establish effective production grants or runtime restrictions.
- Work is ordered by dependency and risk, not by staffing or release dates.