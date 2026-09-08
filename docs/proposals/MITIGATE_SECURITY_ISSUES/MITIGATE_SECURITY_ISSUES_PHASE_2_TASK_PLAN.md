# Task Plan: Phase 2 — Constrain Filesystem And Project Configuration Access

## Phase Summary

- Status: In progress
- Proposal: [MITIGATE_SECURITY_ISSUES.md](./MITIGATE_SECURITY_ISSUES.md) (design §3 "Enforce filesystem boundaries")
- Parent phase plan: [MITIGATE_SECURITY_ISSUES_PHASE_TASK_PLAN.md](./MITIGATE_SECURITY_ISSUES_PHASE_TASK_PLAN.md) (Phase 2)
- Completed authorization design: [CENTRALIZED_AUTHORIZATION_SYSTEM.md](./done/CENTRALIZED_AUTHORIZATION_SYSTEM.md)
- Related follow-up: [SERVER_OWNED_RESOURCE_IDENTIFIERS.md](./SERVER_OWNED_RESOURCE_IDENTIFIERS.md)
- Goal: prevent API input and project configuration from selecting or writing arbitrary server files by confining every file read, write, download, upload, and directive to approved server-owned roots

**Focus**

- Define approved server-owned roots for projects, uploads, backups, temporary files, and generated output.
- Add one shared path-resolution and containment guard used before every file access.
- Apply the guard to execution `target`, ingester `source` and `output_folder`, project names, `@include`, and `@load` inputs.
- Reject absolute paths, traversal, symlink escapes, and time-of-check/time-of-use changes.
- Replace client-selected output destinations with server-generated paths where the product contract permits.
- Decide the disposition of raw YAML mutation and record it.

**Acceptance Criteria**

- [ ] The download endpoint cannot return files outside the approved output root.
- [ ] Execution and ingester operations cannot create or overwrite files outside their assigned roots.
- [ ] `@include`/`@load` directive resolution cannot escape the project or approved data roots.
- [ ] Absolute paths, traversal, and symlink escapes are rejected with clear, non-sensitive errors.
- [ ] Client-supplied output destinations are removed or constrained to server-generated paths where the product contract permits.
- [ ] Symlink and time-of-check/time-of-use cases are covered by tests.

## Work Breakdown

### 1. define approved roots and a shared containment guard

**Objective**

Provide one documented root set and one containment helper that every file access uses.

**Tasks**

- [x] Document the approved root set (projects, global shared data, uploads, backups, temporary files, generated output) and per-environment values in the configuration and operations documentation.
- [x] Implement a shared path guard that resolves a path, requires it to remain inside the intended approved root (for example `resolve().is_relative_to(root)`), and rejects absolute inputs and traversal before any open or create.
- [x] Resolve symlinks before authorization or access and reject paths whose resolved target escapes the approved root.
- [x] Route existing file access through the guard: entity and data-source file resolution (`FilePathResolver` in `backend/app/utils/file_path_resolver.py`), project file browsing (`FileManager` in `backend/app/services/project/file_manager.py`), and upload/metadata paths.
- [x] Add unit tests for traversal, absolute paths, symlinks, missing parents, and project-name variants.

**Completion Criteria**

A single documented root registry and containment guard exist, every listed file-access path uses the guard, and the guard's unit tests pass.

### 2. Confine Execution Outputs And Downloads

**Objective**

Close the arbitrary file read and write paths through execution and download.

**Tasks**

- [x] Review `resolve_output_target` in `backend/app/services/execute_service.py` and the download resolution in `backend/app/api/v1/endpoints/execute.py`; confirm every read and write resolves beneath the project's managed output directory.
- [x] Close the arbitrary file download finding so no endpoint returns any readable file selected by a client-supplied path.
- [x] Keep or extend server-generated output naming and identifiers (for example timestamped file targets) so clients cannot choose output destinations.
- [x] Add tests for traversal, absolute paths, symlinks, cross-project output references, and time-of-check/time-of-use changes.

**Completion Criteria**

The download endpoint returns only files inside the approved output root, execution writes stay confined to the project output directory, and the focused tests pass.

### 3. Confine Project Files, Uploads, Backups, And YAML Directives

**Objective**

Ensure uploads, backups, project file downloads, and configuration directives cannot escape approved roots.

**Tasks**

- [ ] Confine project uploads, upload listing, file metadata, and data-source configuration file browsing to the global or project approved roots and reject traversal.
- [ ] Confine backup listing, backup restore, and project file download to the authorized project directory and reject absolute or traversal names.
- [ ] Ensure `@include`/`@load` directive resolution (`backend/app/services/directive_validator.py` and raw project YAML handling in `backend/app/api/v1/endpoints/projects.py`) cannot escape the project or approved data roots.
- [ ] Decide the disposition of raw YAML mutation: restrict it to authorized operation or remove it until its directive and persistence behavior is authorized, and record the decision.
- [ ] Add tests for uploads, backups, downloads, and directives covering traversal, absolute paths, symlinks, and cross-project references.

**Completion Criteria**

No project-file, upload, backup, download, or directive path can escape its approved root, and the raw YAML disposition is recorded.

### 4. Apply Boundaries To Ingester Paths Or Keep Ingesters Disabled

**Objective**

Prevent ingester source and destination inputs from selecting arbitrary server files.

**Tasks**

- [ ] Record that the ingester API remains disabled until its source, project, output-folder, and database boundaries are secured (parent phase scope).
- [ ] Add or confirm containment checks for ingester `source` and `output_folder` inputs on any path that remains enabled or is re-enabled.
- [ ] Add tests or documented disablement evidence for ingester file and database access paths.

**Completion Criteria**

Ingester operations cannot create or overwrite files outside their assigned roots, or they remain disabled with a recorded exception.

## Progress Tracker

| Area                                            | Status      | Notes                                        |
|-------------------------------------------------|-------------|----------------------------------------------|
| Approved roots and shared containment guard     | Done | Root documentation, shared guard, resolver integration, and escape-case tests are complete |
| Execution outputs and downloads                 | Done | Output and download paths are confined and escape-case tests pass |
| Project files, uploads, backups, and directives | Not started | Includes the raw YAML disposition decision   |
| Ingester boundaries                             | Not started | Ingester remains disabled during this phase  |

## Definition Of Done

- [ ] A documented approved-root registry and one shared containment guard exist and are used by every file access path.
- [ ] The download endpoint cannot return arbitrary files.
- [ ] Execution outputs and ingester writes cannot escape their assigned roots.
- [ ] Uploads, backups, project files, and `@include`/`@load` directives cannot escape approved roots.
- [ ] Absolute, traversal, symlink, and time-of-check/time-of-use escapes are covered by tests.
- [ ] The raw YAML mutation disposition and any retained client-output compatibility boundary are recorded.
- [ ] Focused tests pass and unrelated failures are recorded separately.

## Validation And Testing

- Add file-path unit tests in the existing resolver test area (`backend/tests/utils/test_file_path_resolver.py`) and in the service and API test suites for traversal, absolute paths, symlinks, missing parents, and project-name variants.
- Add endpoint-level tests for download, upload, backup, and directive paths proving escapes are rejected.
- Re-run the documented reproduction cases from [`SECURITY_CHECK.md`](./SECURITY_CHECK.md) for arbitrary file read/write and `@include`/`@load` access against disposable directories only.
- Run the backend test suite and repository lint checks (`make test`, `make lint`) after each area that changes shared behavior.
- Local tests do not establish production network exposure; deployment root and boundary checks remain in the release verification phase.

## Deliverables

| Deliverable | Description | Status | Link |
|---|---|---|---|
| Approved-roots registry            | Documented server-owned roots and per-environment values    | Done | [`docs/OPERATIONS.md`](../../OPERATIONS.md) |
| Containment guard and tests        | Shared path-resolution guard plus unit tests | Done   | `src/path_resolution.py`, `backend/app/utils/file_path_resolver.py` |
| Execution and download confinement | Confined outputs and closed arbitrary download | Done         | `backend/app/services/execute_service.py`, `backend/tests/services/test_execute_service_output_paths.py` |
| Project-file, upload, backup, and directive confinement | Root checks across file endpoints and YAML directives | Not started | `backend/app/services/project/file_manager.py`, `backend/app/api/v1/endpoints/projects.py` |
| Raw YAML disposition record        | Decision on restricting or removing raw YAML mutation  | Not started | TBD                                       |
| Ingester boundary record           | Disablement or containment evidence for ingester paths | Not started | `docs/proposals/CHANGE_REQUEST_INGESTER/` |

## Scope

**In scope**

- Approved-root definitions and the shared containment guard.
- Path confinement for execution targets, downloads, uploads, backups, project files, and YAML directives (`@include`, `@load`).
- Symlink and time-of-check/time-of-use protection.
- Server-generated output destinations and the raw YAML mutation disposition.
- Ingester source and output-folder boundaries while ingesters remain disabled.

**Out of scope**

- Authentication and resource authorization policy, which are delivered by the [centralized authorization system](./done/CENTRALIZED_AUTHORIZATION_SYSTEM_TASK_PLAN.md).
- SQL and DuckDB file-access restrictions, which are owned by Phase 3 of the parent phase plan.
- Network egress and SSRF controls for data sources, which are owned by Phase 4.
- Spreadsheet formula neutralization and UCanAccess hardening, which are owned by the parent proposal.
- Stable server-owned resource identifiers for outputs, backups, uploads, and operations, which are tracked in [SERVER_OWNED_RESOURCE_IDENTIFIERS.md](./SERVER_OWNED_RESOURCE_IDENTIFIERS.md).

## Risks And Mitigations

- **Existing projects use absolute paths or directives that escape approved roots:** provide a migration rule to approved roots and reject unsafe paths with a clear, non-sensitive error.
- **Download, backup, or file-browse clients depend on filenames:** document a compatibility boundary or an explicit break; stable server-owned identifiers are a follow-up rather than this phase.
- **Raw YAML mutation removal changes configuration workflow:** restrict mutation to an authorized operation or keep it disabled until its directive and persistence behavior is authorized, and record the choice.
- **Symlink or time-of-check/time-of-use escapes:** resolve symlinks, re-check containment immediately before open or create, and cover the races in tests.
- **Containment is mistaken for authorization:** path guards do not replace resource authorization, which remains enforced by the centralized authorization system.

## Open Questions

- Which roots are approved in each environment (development, test, shared, production)?
- Should raw YAML mutation be restricted to authorized operation or removed until its behavior is authorized?
- Do any retained client-selected output names need a compatibility boundary before switching to server-generated paths?
- Which existing project configurations rely on absolute paths or directives that must migrate to approved roots?

## Assumptions

- Phase 1 nginx identity and resource authorization are enforced before or alongside this phase by the centralized authorization system.
- Ingesters remain disabled during this phase.
- Path containment is independent of, and does not replace, the server-owned resource identifier follow-up.
- Work is ordered by dependency and risk, not by staffing or release dates.
