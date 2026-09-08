# Mitigate Security Issues

## Status

- Proposed security change
- Scope: Backend API, file access, SQL execution, configuration resolution, ingesters, deployment defaults, and security-sensitive tooling
- Goal: Prevent unauthenticated or insufficiently authorized users from reading or writing server files, accessing databases, exposing secrets, or executing unsafe operations
- Completed authorization design: [CENTRALIZED_AUTHORIZATION_SYSTEM.md](./done/CENTRALIZED_AUTHORIZATION_SYSTEM.md)
- Follow-up sub-proposal: [SERVER_OWNED_RESOURCE_IDENTIFIERS.md](./SERVER_OWNED_RESOURCE_IDENTIFIERS.md)
- Authorization task plan: [CENTRALIZED_AUTHORIZATION_SYSTEM_TASK_PLAN.md](./done/CENTRALIZED_AUTHORIZATION_SYSTEM_TASK_PLAN.md)

## Summary

`SECURITY_CHECK.md` records multiple high-severity findings in the Shape Shifter API. The most serious problem is the absence of application authentication and authorization. Several endpoints then accept user-controlled filesystem paths, database connection details, YAML, and SQL.

The review includes live tests against a local deployment and independent verification passes. It was run against `dev` at `f85fad0c`. The current branch is based on that revision and the main vulnerable files are unchanged. The review did not test a production deployment, so production exposure, network controls, database grants, and deployed secrets must still be checked.

This proposal recommends an emergency containment change followed by application-side enforcement of the identity authenticated by nginx, plus strict restrictions on filesystem, database, configuration, and spreadsheet operations. Native authentication inside the application remains a future option.

## Problem

The current API allows an untrusted caller with network access to reach sensitive operations:

- The project-session mechanism is not user authentication. Anyone can create a session, while most routers do not require one.
- The execution download endpoint accepts an arbitrary path and returns any readable file ([`execute.py`](../../../backend/app/api/v1/endpoints/execute.py)).
- File and folder execution targets are resolved and created without confinement to an approved output directory ([`execute_service.py`](../../../backend/app/services/execute_service.py)).
- SQL validation checks the first parsed statement, but the complete query string is passed to the database ([`query_service.py`](../../../backend/app/services/query_service.py)).
- Internal DuckDB queries reach the workspace without the same query guard. DuckDB table functions can read and write local files.
- Data-source testing accepts user-controlled hosts and expands server environment variables. Raw exception messages are returned to clients ([`data_source_service.py`](../../../backend/app/services/data_source_service.py)).
- Raw YAML and `@include`/`@load` directives allow project configuration to influence filesystem reads and workflow behavior ([`projects.py`](../../../backend/app/api/v1/endpoints/projects.py)).
- The container mounts `.pgpass` into the application filesystem ([`docker-compose.yml`](../../../docker/docker-compose.yml)).
- Before Phase 1, CORS defaults allowed broad development-origin patterns while credentials were enabled ([`config.py`](../../../backend/app/core/config.py)).
- Spreadsheet dispatch writes untrusted values as formulas, and the UCanAccess installer downloads an unpinned artifact without checksum verification ([`install-uncanccess.sh`](../../../scripts/install-uncanccess.sh)).

The review also reports an unauthenticated data-source configuration leak, unsafe SQL identifier interpolation, public API documentation and project documentation, log injection, and several data-integrity and operational bugs. The ingester file-read and database-write paths were only partially tested because the current runtime initialization fails before those paths are reached.

## Scope

This proposal covers:

- Authentication, authorization, project ownership, and data-source access control.
- Emergency network containment and production-safe API defaults.
- Safe handling of filesystem paths, uploads, downloads, YAML directives, and execution targets.
- Read-only and single-statement SQL execution, including the internal DuckDB path.
- SSRF prevention and controlled database connection configuration.
- Error-message redaction, secret handling, logging, and audit events.
- Spreadsheet formula neutralization and UCanAccess dependency verification.
- Security regression tests and production verification.

## Non-Goals

- Replacing nginx as the current authentication provider with native application authentication. That is future work; this proposal requires FastAPI to enforce the verified identity received from nginx.
- Redesigning the project-session editing model beyond adding authenticated user identity and authorization checks.
- Resolving unrelated correctness findings such as leading-zero coercion, nullable dtype warnings, branch-column collisions, or stale generated documentation.
- Making the ingester API operational as part of the first security change. It must remain disabled or protected until its input and output boundaries are secured.
- Treating CORS as a replacement for authentication or authorization.

## Current Behavior

The API is now configured with an application-wide trusted-proxy identity check when enabled. The deployment authenticates users at nginx and passes `X-Authenticated-User: $remote_user`; Docker publishes the backend port on loopback only, and local Makefile Uvicorn targets also bind to `127.0.0.1`. FastAPI allows the health check without identity, rejects other requests without the trusted identity, and verifies session ownership. Persistent project/team authorization and the remaining capability restrictions are still open.

The review's practical verification reported these results:

| Finding                              | Review status     | Important condition                                                          |
|--------------------------------------|-------------------|------------------------------------------------------------------------------|
| Arbitrary file read and write        | Verified locally  | Requires API reachability and a process user with access to the target path  |
| Multi-statement PostgreSQL execution | Verified locally  | Impact depends on database privileges; tested against PostgreSQL, not SQLite |
| Environment-variable disclosure      | Verified locally  | The disclosed value depends on the deployment environment                    |
| `@include`/`@load` file access       | Verified locally  | Requires a project or configuration path that reaches the directive          |
| Internal DuckDB file read/write      | Verified on `dev` | Requires the `@internal` execution path and readable/writable process paths  |
| CORS origin reflection               | Verified locally  | Becomes more serious when cookie or token authentication is introduced       |
| Ingester database/file operations    | Partial           | Runtime initialization blocked deeper testing                                |
| UCanAccess download                  | Code review       | Clean-machine download was not re-run against SourceForge                    |

## Proposed Design

### 1. Contain the deployment

- Bind development and production services to private interfaces unless public access is explicitly required.
- Restrict the published Docker port with an explicit host address and firewall rules.
- Disable the ingester endpoints, raw YAML mutation, arbitrary data-source creation, and execution endpoints until their authorization and boundary checks are in place.
- Protect or disable Swagger, OpenAPI, Redoc, and the public documentation mount in production.
- Remove application access to `.pgpass` where possible. Use a secret manager or a narrowly scoped connection credential instead.

### 2. Enforce nginx identity and application authorization

The implemented resource authorization model is documented in [CENTRALIZED_AUTHORIZATION_SYSTEM.md](./done/CENTRALIZED_AUTHORIZATION_SYSTEM.md) and its [task plan](./done/CENTRALIZED_AUTHORIZATION_SYSTEM_TASK_PLAN.md). The remaining server-owned identifier work is defined in [SERVER_OWNED_RESOURCE_IDENTIFIERS.md](./SERVER_OWNED_RESOURCE_IDENTIFIERS.md).

- Keep nginx as the current authentication provider. Define how it passes a verified identity to FastAPI, using a trusted header or validated token.
- Add FastAPI middleware or dependencies that reject requests without a verified identity. Strip or reject client-supplied identity headers and trust them only on requests that can come from nginx.
- Require authentication on every state-changing, data-reading, query, execution, file, data-source, schema, reconciliation, task, log, and ingester endpoint. Keep health checks public only if required for orchestration.
- Authorize project access, uploaded files, data sources, and generated outputs by user or team. Do not treat a project session ID as proof of identity.
- Add CSRF protection for cookie-authenticated state-changing requests and set cookies with `HttpOnly`, `Secure`, and an appropriate `SameSite` value.
- Keep the application boundary replaceable so native application authentication can be added later without changing resource authorization rules.

### 3. Enforce filesystem boundaries

- Define server-owned roots for projects, uploads, backups, temporary files, and generated output.
- Resolve paths before access and require that the resolved path is inside the intended root using `is_relative_to()`.
- Reject absolute paths and traversal for API inputs, including `target`, `source`, `output_folder`, `@include`, and `@load`.
- Resolve symlinks before authorization and prevent symlink or time-of-check/time-of-use escapes where files are opened or created.
- Use server-generated output paths rather than accepting arbitrary output destinations from clients.

### 4. Make database and SQL access read-only by default

- Reject every query containing more than one non-empty SQL statement. Do not return a warning while executing the full string.
- Apply the same validation to workflow execution and internal DuckDB queries, not only to query helper endpoints.
- Use a dedicated PostgreSQL role with only the required `CONNECT`, schema, and `SELECT` privileges. Verify that it is not an owner or member of a role that can write or alter production tables.
- Replace SQL identifier interpolation with one shared, dialect-aware quoting helper and validate identifier inputs.
- Correct limit enforcement so user-supplied SQL cannot bypass the result-size limit. Enforce limits at the database or query-plan level where possible.
- For DuckDB, disable external access and extension loading for untrusted queries. If file access is required, configure explicit allowed directories and files, and deny `COPY`, `ATTACH`, file-reading functions, network access, and extension installation.

### 5. Restrict data-source and ingester capabilities

- Replace arbitrary client-supplied database connection settings with named, server-managed connections.
- Allow only approved hosts, ports, drivers, and schemas. Resolve DNS and apply network egress restrictions to prevent access to localhost, private ranges, metadata services, and unrelated internal services.
- Resolve only explicitly approved environment-variable names. Never resolve arbitrary server environment variables from client-controlled configuration.
- Redesign or disable ingester requests that accept a server filesystem path, output folder, or database destination. Accept uploaded content or approved object references instead.
- Preserve and pass database passwords correctly if database access remains supported; never silently fall back to passwordless connections.

### 6. Redact responses and protect generated files

- Return stable, generic error messages and a correlation ID to clients.
- Log detailed diagnostics only on the server, with passwords, environment values, SQL text, connection strings, and sensitive paths redacted.
- Prevent user-controlled newlines from forging log records.
- Convert untrusted spreadsheet values beginning with formula-triggering characters into text before XLSX or CSV dispatch. Add tests for `=`, `+`, `-`, `@`, tabs, and line breaks.
- Pin the UCanAccess release, verify its SHA-256 checksum, fix the temporary-file copy logic, and review the resulting artifact before it enters the image.

## Alternatives Considered

### Reverse-proxy-only authentication

Accepted as the current authentication provider only when combined with application-side identity enforcement. Docker must prevent direct access to the application port, nginx must provide a verified identity, and FastAPI must perform resource authorization. Native application authentication can replace nginx later.

### Native application authentication immediately

Deferred. It provides a stronger long-term boundary but is not required to address the immediate findings if nginx identity is enforced by FastAPI and direct backend access is blocked.

### Relying on SQL text checks alone

Rejected. SQL parsers and keyword checks are not a sufficient security boundary for PostgreSQL or DuckDB. Database privileges, execution-path coverage, DuckDB configuration, resource limits, and network restrictions are required as defense in depth.

### Removing all SQL and file features

Deferred. These features are part of the product workflow, but they must use approved sources and destinations rather than arbitrary client-controlled ones.

## Risks And Tradeoffs

- Authentication and project-level authorization will add setup and may require changes to the frontend session flow.
- Restricting paths and database destinations may break existing projects that rely on absolute paths or user-selected output folders. Migration errors should identify the approved replacement without disclosing sensitive paths.
- Read-only SQL roles may prevent existing workflows that intentionally write to databases. Those workflows need a separate, explicitly authorized service operation rather than a general query endpoint.
- Disabling DuckDB external access may remove undocumented uses of file-reading table functions. Any supported file import must be implemented through a controlled upload or loader path.
- Rotating credentials may interrupt deployments and requires coordinated verification.

## Testing And Validation

- Add unauthenticated and unauthorized tests for every sensitive router, including direct access to documentation and static mounts.
- Add path-boundary tests for traversal, absolute paths, symlinks, non-existent parents, and project-name variations.
- Add SQL tests for stacked statements, comments, quoted strings, embedded `LIMIT`, DDL/DML, identifier edge cases, and PostgreSQL execution with a read-only role.
- Add DuckDB tests proving that file-reading functions, `COPY`, `ATTACH`, extensions, network access, and paths outside the approved roots are rejected.
- Add tests confirming that error responses do not contain passwords, environment values, connection strings, SQL text, or absolute sensitive paths.
- Add CORS tests for approved and unapproved origins, including credentialed requests.
- Add spreadsheet tests that inspect generated cells and verify that untrusted values are stored as text.
- Run the documented reproduction cases from [`SECURITY_CHECK.md`](./SECURITY_CHECK.md) after each mitigation, using disposable databases and files only.
- Before release, verify the deployed image, Docker port binding, reverse proxy, firewall, environment variables, database grants, mounted files, and access logs.

## Acceptance Criteria

- Sensitive API endpoints return `401` or `403` without valid authentication and authorization.
- An authenticated user cannot access another user's project, data source, upload, output, log, or backup.
- File reads and writes are confined to approved server-owned roots, including through YAML directives and DuckDB.
- Multi-statement, destructive, external-file, extension-loading, and network-capable SQL requests are rejected on every execution path.
- Production database credentials used by the application cannot alter or destroy production data unless a separately approved operation explicitly requires it.
- Client responses contain no raw exception text, secrets, connection strings, SQL, or sensitive absolute paths.
- CORS accepts only configured trusted origins and uses credentials only where required.
- Generated spreadsheets cannot execute values supplied as data.
- The UCanAccess artifact is version-pinned and checksum-verified.
- The full security regression suite and the re-verification cases pass on the exact release commit.

## Recommended Delivery Order

1. Contain network exposure, disable unsafe endpoints where possible, rotate potentially exposed credentials, and inspect logs.
2. Enforce the verified nginx identity in FastAPI, add authorization and CSRF protection, and apply production documentation controls.
3. Add filesystem root checks and remove arbitrary client-controlled destinations.
4. Enforce SQL and DuckDB restrictions and establish least-privilege database roles.
5. Restrict data-source and ingester capabilities; then decide whether to re-enable the ingester API.
6. Redact errors and logs, neutralize spreadsheet formulas, and harden the UCanAccess installation.
7. Run the complete regression and deployment verification checklist.

## Open Questions

- What trusted identity header or token will nginx provide to FastAPI, and how will FastAPI verify that requests came from nginx?
- Is the production API reachable directly, or only through a trusted private network or proxy? Direct access must be blocked before proxy identity is trusted.
- Which users and teams should be allowed to access each project and shared data source?
- When should native application authentication replace nginx authentication?
- Which workflows genuinely require database writes, and can those writes use a dedicated service operation?
- Which file-based imports and outputs must remain supported after root confinement?
- Should the ingester API be removed, kept disabled, or redesigned around uploaded content and server-managed destinations?
- Which environment variables and database credentials were present in any deployment that may have been reachable?

## Final Recommendation

Treat the API as unsafe for shared or production use until nginx-authenticated identity is enforced by FastAPI, resource authorization is implemented, direct backend access is blocked, and filesystem, SQL, and secret-redaction controls are complete. Apply the containment and credential-rotation actions immediately, then deliver the remaining controls in the order above. Keep [`SECURITY_CHECK.md`](./SECURITY_CHECK.md) as the verification record and update it with results from the exact release commit. Native application authentication can follow as a separate hardening change.
