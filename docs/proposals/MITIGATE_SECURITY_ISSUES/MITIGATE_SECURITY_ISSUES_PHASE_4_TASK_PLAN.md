# Task Plan: Phase 4 - Restrict Data Sources, Ingesters, And Error Disclosure

## Phase Summary

- Status: In progress
- Proposal: [MITIGATE_SECURITY_ISSUES.md](../MITIGATE_SECURITY_ISSUES.md) (design section 5, Restrict data-source and ingester capabilities)
- Parent phase plan: [MITIGATE_SECURITY_ISSUES_PHASE_TASK_PLAN.md](./MITIGATE_SECURITY_ISSUES_PHASE_TASK_PLAN.md) (Phase 4)
- Related ingester plan: [INGESTER_AUTHORIZATION_TASKS.md](../CHANGE_REQUEST_INGESTER/INGESTER_AUTHORIZATION_TASKS.md)
- Goal: restrict server-side data-source selection and public error disclosure while keeping ingester-specific route and destination work in the dedicated ingester authorization plan.

**Focus**

- Move data-source selection to named server-managed sources and allowlists.
- Restrict environment-variable resolution and network egress to approved destinations.
- Redact secrets and implementation details from public errors and logs.
- Keep ingester disposition and destination gating owned by the dedicated ingester authorization plan.

**Acceptance Criteria**

- [ ] Data-source requests cannot probe or connect to unapproved destinations.
- [ ] Client-controlled configuration cannot select arbitrary server environment variables.
- [ ] Error responses and logs do not expose secrets or sensitive implementation details.
- [ ] Ingester-specific route and destination work is tracked in the dedicated ingester authorization plan, not duplicated here.

## Work Breakdown

### 1. Inventory Data-Source Inputs And Disclosure Surfaces

**Objective**

Identify every route, service, and configuration path that can choose a data source or expose public error details.

**Tasks**

- [x] Classify client-controlled data-source inputs, connection settings, and destination resolution paths.
- [x] Identify approved drivers, hosts, ports, schemas, and environment-variable names.
- [x] Catalog public error paths, server logs, and correlation-id handling.
- [x] Record the ingester-specific disposition and destination-gating tasks as deferred in the dedicated plan.

**Inventory**

- Public data-source routes: `/data-sources`, `/data-sources/drivers`, `/data-sources/entity-types`, `/data-sources/files`, `/data-sources/excel/metadata`, `/data-sources/files` upload, and `/data-sources/{filename}`.
- Query routes that resolve or expose data-source access: `/data-sources/{data_source_name}/query/execute`, `/data-sources/{data_source_name}/query/validate`, and `/data-sources/{data_source_name}/query/columns`.
- Service-layer data-source paths: `backend/app/services/data_source_service.py` for YAML path resolution, load/create/update/delete, and environment-variable substitution.
- Service-layer disclosure surfaces: `backend/app/services/query_service.py` for query validation, execution, timeout, memory, and response-size handling; `backend/app/services/schema_service.py` for schema introspection and table preview; `backend/app/exceptions.py` for structured exception payloads.
- Loader-layer SQL paths: `src/loaders/sql_loaders.py` for read-only SQL enforcement and limit injection, and `src/loaders/duckdb_loader/duckdb_loader.py` for the internal `@internal` DuckDB query path.

**Completion Criteria**

Every supported data-source entry point and public error path has a documented handling rule, and ingester-specific work is redirected to the dedicated plan.

### 2. Enforce Server-Managed Data Sources

**Objective**

Limit data-source selection and resolution to approved server-managed settings.

**Tasks**

- [x] Replace arbitrary client-supplied connection settings with named server-managed sources.
- [x] Allow only approved drivers, hosts, ports, schemas, and destinations.
- [x] Add DNS/IP validation and network egress controls for localhost, private ranges, metadata services, and unrelated internal services.
- [x] Resolve only approved environment-variable names.
- [x] Preserve required database passwords without passwordless fallback.

**Implementation Notes**

- Server-managed validation is centralized in `backend/app/services/data_source_policy.py` and used by the data-source mapper and service.
- Disallowed connection strings, environment-variable names, hosts, and ports fail before a config is persisted or converted to a core data source.
- File-backed sources continue to be resolved through the managed application root, while file containment remains owned by the filesystem-boundary phase.

**Completion Criteria**

Unsupported drivers, hosts, ports, schemas, destinations, and environment variables are rejected, and approved connections still authenticate.

### 3. Remove Sensitive Disclosure

**Objective**

Ensure clients receive stable public error responses while detailed diagnostics stay on the server.

**Tasks**

- [ ] Return generic public messages with correlation IDs.
- [ ] Redact credentials, environment values, connection strings, SQL text, and sensitive paths.
- [ ] Prevent user-controlled newlines from forging log records.
- [ ] Keep detailed diagnostics in server-only logs.

**Completion Criteria**

Public responses and logs do not reveal sensitive data, and redaction tests cover the targeted fields.

### 4. Keep Ingester Work In The Dedicated Plan

**Objective**

Avoid duplicating ingester route disposition and destination-gating work in this phase.

**Tasks**

- [ ] Maintain [INGESTER_AUTHORIZATION_TASKS.md](../CHANGE_REQUEST_INGESTER/INGESTER_AUTHORIZATION_TASKS.md) as the owning document for ingester routes, roles, and destination checks.
- [ ] Keep this phase plan limited to data-source and error-disclosure work.
- [ ] Confirm any future ingester source, destination, and registration/write work is added only to the dedicated ingester plan.

**Completion Criteria**

There is a single active plan for ingester authorization and destination-gating work, and phase 4 does not duplicate it.

## Progress Tracker

| Area | Status | Notes |
|---|---|---|
| Data-source inputs and disclosure surfaces | Done | Public data-source routes, service-layer resolution paths, loader paths, and public disclosure surfaces are inventoried |
| Server-managed data sources | Done | Mapper and service validation reject unapproved destinations, environment variables, and custom connection strings |
| Sensitive disclosure removal | Not started | Stable public errors and log redaction required |
| Ingester work deferral | Not started | Tracked in [INGESTER_AUTHORIZATION_TASKS.md](../CHANGE_REQUEST_INGESTER/INGESTER_AUTHORIZATION_TASKS.md) |

## Definition Of Done

- [x] Named server-managed data sources replace arbitrary connection settings and reject unapproved destinations.
- [x] Approved environment variables are the only ones resolved from client-controlled configuration.
- [ ] Public errors and logs redact secrets, SQL, connection strings, and sensitive paths.
- [ ] The ingester disposition and destination-gating work remains tracked in the dedicated ingester authorization plan.
- [x] Focused tests or review cover the data-source allowlists and redaction behavior.

## Validation And Testing

- Unit tests for allowlists, DNS/IP validation, environment-variable resolution, and password handling.
- Route and service tests for blocked destinations and stable error responses.
- Logging tests for newline handling and redaction.
- Review of the dedicated ingester authorization plan to confirm ingester tasks are not duplicated here.

## Deliverables

| Deliverable | Description | Status | Link |
|---|---|---|---|
| Data-source inventory | Routes, services, configuration paths, and approved destinations | Done | [MITIGATE_SECURITY_ISSUES_PHASE_4_TASK_PLAN.md](MITIGATE_SECURITY_ISSUES_PHASE_4_TASK_PLAN.md) |
| Server-managed data-source enforcement | Named sources, allowlists, DNS/IP validation, and egress controls | Done | [backend/app/services/data_source_policy.py](../../../backend/app/services/data_source_policy.py), [backend/app/mappers/data_source_mapper.py](../../../backend/app/mappers/data_source_mapper.py), [backend/app/services/data_source_service.py](../../../backend/app/services/data_source_service.py), [backend/tests/mappers/test_data_source_mapper.py](../../../backend/tests/mappers/test_data_source_mapper.py), [backend/tests/services/test_data_source_service.py](../../../backend/tests/services/test_data_source_service.py) |
| Error disclosure controls | Stable public messages, correlation IDs, and redaction | Not started | TBD |
| Ingester plan cross-reference | Dedicated plan for ingester authorization and destination checks | Not started | [INGESTER_AUTHORIZATION_TASKS.md](../CHANGE_REQUEST_INGESTER/INGESTER_AUTHORIZATION_TASKS.md) |

## Scope

**In scope**

- Named server-managed data sources and approved destination allowlists.
- DNS/IP validation, network egress controls, and approved environment-variable resolution.
- Stable public error messages, correlation IDs, redaction, and newline-safe logging.
- Cross-reference and deferral of ingester route disposition and destination-gating work to the dedicated ingester plan.

**Out of scope**

- Ingester route disposition, source, output-folder, database-destination, and registration/write checks, which are tracked in [INGESTER_AUTHORIZATION_TASKS.md](../CHANGE_REQUEST_INGESTER/INGESTER_AUTHORIZATION_TASKS.md).
- Filesystem boundaries, SQL policy, and DuckDB restrictions, which are owned by earlier phases.
- Changes to the centralized authorization policy or the nginx identity contract.

## Risks And Mitigations

- **Existing clients depend on direct connection settings:** keep a server-managed compatibility boundary or reject unsupported settings with clear, non-sensitive errors.
- **Environment-specific destination rules differ:** document approved hosts, ports, and schemas per environment instead of assuming one global allowlist.
- **Redaction can hide useful diagnostics:** keep detailed traces server-side and use correlation IDs to tie client errors to server logs.
- **Ingester work can drift back into this plan:** keep the dedicated ingester authorization task plan as the only active place for ingester route and destination-gating tasks.

## Open Questions

- Which data-source destinations are approved in each environment?
- Do any retained client-selected connection names need a compatibility boundary before switching to named server-managed sources?
- Should any future ingester source or destination rules require an additional dedicated plan, or will the existing ingester authorization task plan remain the single owner?

## Assumptions

- The ingester feature remains under development and its route and destination-gating work stays in the dedicated ingester authorization task plan.
- Data-source allowlists are defined per deployment environment rather than inferred from client configuration.
- Work is ordered by dependency and risk, not by staffing or release dates.