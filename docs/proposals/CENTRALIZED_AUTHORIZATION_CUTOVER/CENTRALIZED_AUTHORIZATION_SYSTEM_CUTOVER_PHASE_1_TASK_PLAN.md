# Phase 1 Task Plan: Complete Route And Operation Inventory

## Phase Summary

- **Source decision document:** [Centralized Authorization System](../done/MITIGATE_SECURITY_ISSUES/done/CENTRALIZED_AUTHORIZATION_SYSTEM.md)
- **Source phase plan:** [Centralized Authorization System Cutover Plan](./CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md) — [Phase 1: Complete Route And Operation Inventory](./CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md#phase-1-complete-route-and-operation-inventory)
- **Goal:** Classify every registered route and background operation that production can reach, and make the route inventory the checked record of that classification.
- **Readiness:** Validated
- **Dependencies:** None. The phase plan records `Depends On: No prior phase` and `Readiness: Ready for a task plan`.
- **Constraints:** Compare against the registered route set, not a hand-maintained list (phase handoff). Ingester capability authorization beyond classification is out of phase scope (phase non-goal) and stays with [INGESTER_AUTHORIZATION_TASKS.md](../CHANGE_REQUEST_INGESTER/INGESTER_AUTHORIZATION_TASKS.md). Do not change authorization policy, grants, or project YAML.

**Acceptance Criteria**

1. `PH1-AC-1` (from `P-AC-1`) No sensitive production route or background operation remains `UNDECLARED`.
2. `PH1-AC-2` (from `P-AC-1`) The inventory records resource type, action, and exposure status for every registered route.
3. `PH1-AC-3` (from `P-AC-1`) Lifecycle entry points and protected service methods have a reviewed authorization owner and requirement.
4. `PH1-AC-4` (from `P-AC-4`) The automated route inventory check passes.

## Repository Findings

**Repository basis:** branch `dev`, commit `c3ee7b07`, planning date 2026-09-16. Uncommitted changes exist in the worktree (the phase plan edit and unrelated in-flight work); no finding below depends on uncommitted content. Authorization baseline: `uv run pytest backend/tests/authorization -q` → 180 passed, 1 skipped.

| Evidence | Finding | Planning implication |
|---|---|---|
| [docs/AUTHORIZATION_ROUTE_INVENTORY.md](../../AUTHORIZATION_ROUTE_INVENTORY.md) | 23 rows carry `UNDECLARED`: 8 public/static/direct-application rows and 15 `/api/v1` rows | All 23 rows need a recorded classification; this file is the maintained artifact to update |
| `backend/tests/authorization/test_route_authentication.py::test_route_inventory_matches_assembled_api_routes` | Compares documented `/api/v1` method/path pairs with the assembled app, but passes while a row stays `UNDECLARED` | A classification check must be added for `PH1-AC-1` and `PH1-AC-4` |
| `backend/tests/authorization/test_dependencies.py::test_static_data_source_subroutes_are_classified` and `AUTHENTICATED_STATIC_DATA_SOURCE_PATHS` | Established pattern: declared metadata **or** an explicit authenticated-only set, currently limited to `/data-sources*` | Extend this pattern to the remaining routes instead of inventing a new mechanism |
| `backend/app/authorization/dependencies.py` | `require_project`, `require_shared_data_source`, `require_application_action`, `require_authorized_session`, `require_operation` attach `authorization_requirement` metadata | Use existing factories; `require_shared_data_source` already resolves a body-supplied locator |
| `backend/app/api/v1/endpoints/sessions.py::create_session` | Performs the `Action.EDIT` project check inline, so the route exposes no metadata and reads `UNDECLARED` | Move the check to a declared dependency; `require_project` resolves only route/query parameters today |
| `backend/app/api/v1/endpoints/projects.py::list_projects` | Filters through `ProjectService.list_authorized_projects` | Classify `authenticated` with a filtering note; no code change |
| `backend/app/api/v1/endpoints/projects.py::get_active_project_name` | Returns the deployment active project name without principal scoping | Design §5 makes `authenticated` the only alternative to public, and §9 concealment applies to identifier-addressed resources; classify `authenticated` |
| `backend/app/main.py` | `/docs` mount when the docs directory exists; `/assets` mount and SPA catch-all only when `frontend/dist` exists; `/` root only when it does not | Documented rows are build-state conditional; the check must tolerate their absence |
| `backend/app/api/v1/endpoints/{suggestions,reconciliation,execute,filters,whats_new,ingesters,help_docs}.py` | Handlers return registry metadata, service health or manifest data, filter schemas, release notes, or repository documentation | Classify `authenticated` |
| `docs/AUTHORIZATION_ROUTE_INVENTORY.md` (`POST /api/v1/data-sources/tables`, `/tables/schema`) | Accepted precedent: client-supplied configuration introspection is authenticated-only with a recorded follow-up | Apply the same disposition to `POST /api/v1/suggestions/analyze` and `/suggestions/entity`, which accept client-supplied entities and an optional `data_source_name` |
| `docs/AUTHORIZATION.md`; `docs/proposals/CHANGE_REQUEST_INGESTER/INGESTER_AUTHORIZATION_TASKS.md` | "Ingester authorization remains proposed work"; that task plan is Not started and its Area 1 is ingester route classification | Record the ingester classification and the enforcement follow-up; add no ingester dependency in this phase |
| `backend/app/services/project_service.py::assign_project_owner`, `backend/app/api/v1/endpoints/projects.py` (`POST /projects`, `POST /projects/{name}/copy`, `DELETE /projects/{name}`), `backend/app/api/v1/endpoints/data_sources.py` (`POST /data-sources`, `DELETE /data-sources/{filename}`) | Create and copy call `AuthorizationService.register_project`; delete and shared-source delete call `transition_resource` with failure rollback to `active`; shared-source create calls `register_shared_data_source` | Lifecycle coverage is present and should be recorded, not changed |
| `backend/app/services/project_service.py` (≈line 593) and `backend/app/services/project/project_operations.py` (≈line 277) | Docstrings say "use rename_project() instead", but no rename method exists; `update_metadata` ignores `new_name` and treats the filename as the project name | No rename path needs a lifecycle check; the stale references mislead reviewers and should be corrected |
| `backend/app/api/v1/endpoints/reconciliation.py::auto_reconcile_entity`; `backend/app/core/operation_manager.py::create_operation` | The only `create_operation` caller records `owner_principal_id` and `project_resource_id` before `asyncio.create_task`; `/operations/{operation_id}/*` uses `require_operation` | Background coverage is present and should be recorded |
| `backend/app/core/state_manager.py` | Session cleanup is the only other `asyncio.create_task` site and has no principal or protected resource | Record it as not authorization-scoped |
| `docs/DEVELOPMENT.md` ("authorization for protected work") | Steps 1–5 require the dependency, the inventory row, and focused allowed/denied tests | Follow the documented procedure for the one code change |

## Scope

**In scope**

- Classification of the 23 `UNDECLARED` rows in [AUTHORIZATION_ROUTE_INVENTORY.md](../../AUTHORIZATION_ROUTE_INVENTORY.md).
- The one code change the classification requires: a declared `project:edit` requirement on `POST /api/v1/sessions`.
- Extension of the automated route check so an unclassified API route fails the suite.
- Inventory sections recording lifecycle entry points and background operations, plus the classification review note.
- Focused tests for the session route declaration, the extended project dependency, and the new check.

**Out of scope**

- Ingester capability authorization (project, source, database, destination): owned by [INGESTER_AUTHORIZATION_TASKS.md](../CHANGE_REQUEST_INGESTER/INGESTER_AUTHORIZATION_TASKS.md). This phase records the classification and the follow-up only.
- Deployment work: manifest preparation (Phase 2), readiness validation (Phase 3), enforcement cutover (Phase 4), Podman verification (Phase 5).
- New authorization policy, roles, or actions; project YAML changes; frontend changes.
- Adding a project rename feature.

**Affected layers:** one backend endpoint, the authorization dependency module, backend tests, and maintained documentation. No `src/` change.

## Work Breakdown

### Area 1: Record A Classification For Every `UNDECLARED` Row

**Objective:** Every previously `UNDECLARED` row states its requirement category and reason, and the session route's declared metadata matches its enforcement.

* [x] `T1.1` **Change:** Declare the session route's `project:edit` requirement through the standard dependency.
  * **Target:** `backend/app/api/v1/endpoints/sessions.py::create_session`; `backend/app/authorization/dependencies.py::require_project`.
  * **Current → required:** `create_session` resolves the project resource and calls `authorization_service.authorize(principal, Action.EDIT, resource)`, then raises `404 Project '<name>' not found`. No dependency carries `authorization_requirement`, so the inventory row reads `UNDECLARED`. Required: the route declares `project:edit` and keeps a concealed `404` for a project the principal cannot edit. `require_project` resolves `project_name` and `name` as route or query parameters, so it cannot read the request-body field this route uses.
  * **Implementation:** Extend `require_project(action, *, body_locator: bool = False)`. When `body_locator` is true and neither parameter resolves, read `project_name` from the parsed JSON body inside a `try` block that tolerates `RuntimeError` and `ValueError`, mirroring `require_shared_data_source`. Keep parameter-first precedence. Register the route with `Depends(require_project(Action.EDIT, body_locator=True))`, use `authorized_project.resource.locator` for the project path lookup, and remove the now-redundant authorization service parameter and inline check. Keep `get_principal()` for the session owner.
  * **Constraints:** `body_locator` defaults to false, so no existing `require_project` caller changes behavior. The denial stays `404`; its detail becomes the shared dependency message `Resource not found`. Update any test that asserts the previous detail string. Do not read the authorization database in handler code.
  * **Validation:** `V-2`, `V-3`; add a route-metadata assertion alongside `backend/tests/authorization/test_dependencies.py::test_project_data_source_connection_requires_project_and_shared_source_access`, and a concealed-`404` case for a principal without edit access.

* [x] `T1.2` **Change:** Record authenticated-only classifications for the non-resource API rows.
  * **Target:** [AUTHORIZATION_ROUTE_INVENTORY.md](../../AUTHORIZATION_ROUTE_INVENTORY.md) rows: `GET /api/v1/help-docs/{doc_path:path}`, `GET /api/v1/projects`, `GET /api/v1/projects/active/name`, `POST /api/v1/suggestions/analyze`, `POST /api/v1/suggestions/entity`, `GET /api/v1/reconciliation/health`, `GET /api/v1/reconciliation/manifest`, `GET /api/v1/dispatchers`, `GET /api/v1/filters/types`, `GET /api/v1/whats-new`, `GET /api/v1/whats-new/{version}/content`.
  * **Current → required:** Each row reads `UNDECLARED`. Required: `authenticated`, with a short note stating the basis.
  * **Implementation:** Replace the requirement cell and add notes: `/projects` returns only projects readable by the principal (`ProjectService.list_authorized_projects`); `/projects/active/name` returns the deployment active project name only and is not identifier-addressed; `/suggestions/analyze` and `/suggestions/entity` introspect client-supplied entity configuration and an optional `data_source_name`, with a recorded follow-up to resolve the source server-side and require shared-source read; the remaining rows return registry metadata, service health or manifest data, filter schemas, release notes, or repository documentation.
  * **Constraints:** Use the requirement terms already defined in the inventory. Do not claim enforcement that the code does not perform; state handler-level behavior in the note.
  * **Validation:** `V-3`, `V-5`.

* [x] `T1.3` **Change:** Record the ingester route classification and its enforcement follow-up.
  * **Target:** [AUTHORIZATION_ROUTE_INVENTORY.md](../../AUTHORIZATION_ROUTE_INVENTORY.md) rows for `GET /api/v1/ingesters`, `POST /api/v1/ingesters/{key}/validate`, `POST /api/v1/ingesters/{key}/ingest`.
  * **Current → required:** All three read `UNDECLARED`. Required: `authenticated` for the metadata list, and `application:run_ingesters` with project, source, and destination authorization for validation and execution, marked as enforcement pending.
  * **Implementation:** Record the required requirement from the design resource rules and add a note naming [INGESTER_AUTHORIZATION_TASKS.md](../CHANGE_REQUEST_INGESTER/INGESTER_AUTHORIZATION_TASKS.md) as the owner of the enforcement work.
  * **Constraints:** Do not add ingester dependencies or change ingester behavior in this phase. Do not describe ingester authorization as implemented.
  * **Validation:** `V-5`.

* [ ] `T1.4` **Change:** Record exposure for the public, generated, and static rows.
  * **Target:** [AUTHORIZATION_ROUTE_INVENTORY.md](../../AUTHORIZATION_ROUTE_INVENTORY.md) rows: `GET, HEAD /api/v1/openapi.json`, `GET, HEAD /api/v1/docs`, `GET, HEAD /docs/oauth2-redirect`, `GET, HEAD /api/v1/redoc`, static mount `/docs/*`, static mount `/assets/*`, `GET /{full_path:path}`, `GET /`.
  * **Current → required:** All eight read `UNDECLARED`. Required: `authenticated`, since trusted-proxy middleware requires an identity for every path except `/api/v1/health`, and each row states its origin and build condition.
  * **Implementation:** Note FastAPI-generated routes, the repository documentation mount, and the three frontend-build-conditional entries. State that these paths are protected by the authentication middleware rather than by a resource dependency.
  * **Constraints:** Do not classify any of these rows `Public`; the health route is the only public path.
  * **Validation:** `V-3`, `V-5`.

**Completion evidence:** The inventory contains no `UNDECLARED` row, and the session route exposes metadata matching its recorded requirement.

### Area 2: Make The Automated Check Enforce Classification

**Objective:** An assembled `/api/v1` route with neither declared metadata nor a documented classification fails the test suite.

* [ ] `T2.1` **Change:** Add the API route classification check.
  * **Target:** `backend/tests/authorization/test_route_authentication.py` (new `test_api_routes_are_classified` and its helper); pattern from `backend/tests/authorization/test_dependencies.py::test_static_data_source_subroutes_are_classified`.
  * **Current → required:** The inventory comparison only checks documented-versus-registered path sets, so a route may stay `UNDECLARED` indefinitely. Required: every assembled `/api/v1` route either exposes `authorization_requirement` metadata or appears in an explicit documented classification set.
  * **Implementation:** Factor the scan into a helper that takes the assembled routes and returns unclassified `METHOD /path` entries. Read requirements from `route.dependant.dependencies` using `getattr(dependency.call, "authorization_requirement", None)`. Add module-level constants `AUTHENTICATED_ONLY_API_PATHS` and `ENFORCEMENT_PENDING_API_PATHS` (the ingester validation and execution rows), each entry carrying a comment with its reason and, for pending rows, the owning follow-up document. Assert the unclassified list is empty and include it in the failure message.
  * **Constraints:** Keep the existing parity assertions and their failure messages. Express paths without the API prefix, matching the existing constant style.
  * **Validation:** `V-3`, `V-4`.

* [ ] `T2.2` **Change:** Extend documented-route parity to non-API and mounted routes.
  * **Target:** `backend/tests/authorization/test_route_authentication.py` (`_documented_api_routes`, `_runtime_api_routes`).
  * **Current → required:** Both helpers filter to paths starting with `/api/v1/`, so `/docs/oauth2-redirect` and the `/docs` and `/assets` mounts are documented but never compared. Required: assembled direct routes and mounts outside the API prefix must appear in the inventory, and every non-conditional documented row must exist in the assembled app.
  * **Implementation:** Add helpers for the non-API `Route` paths and for `starlette.routing.Mount` paths, and add a `CONDITIONAL_DOCUMENTED_PATHS` set for `/assets/*`, `/{full_path:path}`, and `/` so a build without a frontend bundle still passes.
  * **Constraints:** Never fail because the frontend bundle is absent. Keep the existing `/api/v1` comparison intact.
  * **Validation:** `V-3`, `V-5`.

* [ ] `T2.3` **Change:** Add negative coverage for the classification check.
  * **Target:** `backend/tests/authorization/test_route_authentication.py`.
  * **Current → required:** No test proves the check detects an unclassified route. Required: a test that feeds the helper a synthetic route without `authorization_requirement` or a classification entry and asserts the route is reported.
  * **Implementation:** Build the synthetic route with `fastapi.routing.APIRoute` and a `dependant` carrying no authorization metadata; assert the returned list contains the synthetic `METHOD /path`.
  * **Constraints:** Do not weaken or bypass the constants to make the test pass; do not modify production code from the test.
  * **Validation:** `V-4`.

**Completion evidence:** The suite fails for an undeclared synthetic API route and passes for the assembled application and its documented non-API routes.

### Area 3: Record Lifecycle And Background Coverage

**Objective:** The inventory states, for each lifecycle entry point and background operation, its authorization and its lifecycle or operation-record behavior.

* [ ] `T3.1` **Change:** Add a lifecycle and background-operation section to the inventory.
  * **Target:** [AUTHORIZATION_ROUTE_INVENTORY.md](../../AUTHORIZATION_ROUTE_INVENTORY.md) (new section after the route tables, before Maintenance).
  * **Current → required:** The inventory covers routes only; `PH1-AC-3` needs lifecycle entry points and protected service methods recorded. Required: a compact table recording the entry point, its authorization, its lifecycle or operation call, and the evidence location.
  * **Implementation:** Record `POST /projects` (`application:create_project`, `AuthorizationService.register_project` assigns the creator as owner), `POST /projects/{name}/copy` (source `project:read` plus `application:create_project`, `register_project` for the target), `DELETE /projects/{name}` (`project:delete`, `transition_resource` through `deleting`, back to `active` on failure, then `deleted`), `POST /data-sources` (`application:manage_shared_sources`, `register_shared_data_source`), `DELETE /data-sources/{filename}` (`application:manage_shared_sources`, `transition_resource`), the auto-reconcile background operation (`project:edit` at start, `require_operation` for progress, stream, and cancel, with `owner_principal_id` and `project_resource_id` recorded), and the session-cleanup task (no principal or protected resource; not authorization-scoped).
  * **Constraints:** Record the reviewed result that no project rename entry point exists, because `ProjectService.update_metadata` ignores `new_name` and the project name derives from the filename. State findings, not new requirements.
  * **Validation:** `V-6`.

* [ ] `T3.2` **Change:** Correct the stale `rename_project()` references.
  * **Target:** `backend/app/services/project_service.py::update_metadata` docstring, `backend/app/services/project/project_operations.py::update_metadata` docstring, and the `MetadataUpdateRequest.name` description in `backend/app/api/v1/endpoints/projects.py` if it implies renaming.
  * **Current → required:** The docstrings instruct readers to "use rename_project() instead", but no such method exists. Required: state that the project name comes from the filename and that this operation does not rename the project.
  * **Constraints:** Documentation and description text only. Do not add a rename feature or change `update_metadata` behavior.
  * **Validation:** `V-8`.

* [ ] `T3.3` **Change:** Confirm no additional background entry point reaches protected work.
  * **Target:** `backend/app/` (`asyncio.create_task`, `BackgroundTasks`, `run_in_executor`, `operation_manager.create_operation`).
  * **Current → required:** Plan-time inspection found two `create_task` sites (`reconciliation.py::auto_reconcile_entity`, `state_manager` cleanup) and one `create_operation` caller. Required: re-run the search at the reviewed commit and record the method and result in the `T3.1` section.
  * **Implementation:** Record the search terms, the result, and the classification of each hit. Stop and report as a plan conflict if a new entry point appears; do not classify it silently.
  * **Constraints:** No code change. Do not add enforcement for entry points that carry no protected resource.
  * **Validation:** `V-6`, `V-7`.

**Completion evidence:** The inventory lists every lifecycle entry point with its authorization and lifecycle call, the rename absence is recorded, and the background review names its method and result.

### Area 4: Review And Align Maintained Documentation

**Objective:** The classification is reviewed by a named reviewer, and the maintained documentation points at the current record.

* [ ] `T4.1` **Change:** Record the classification review.
  * **Target:** [AUTHORIZATION_ROUTE_INVENTORY.md](../../AUTHORIZATION_ROUTE_INVENTORY.md) review note.
  * **Current → required:** Classifications are unreviewed. Required: a dated note naming the reviewer and stating that the classifications were checked against the design resource rules and the registered route set.
  * **Implementation:** Add the note after the lifecycle section. Reviewer: `TBD`; record the name and date before the note is written. Verify each row against `DESIGN`-level rules in the design document sections 5, 7, and 9, and against the assembled route list from `V-5`.
  * **Constraints:** The reviewer confirms or corrects rows; corrections follow the same terms and note style. A route that cannot be classified without a policy decision is reported and blocked, not guessed.
  * **Validation:** `V-5`.

* [ ] `T4.2` **Change:** Point the authorization coverage note at the current record.
  * **Target:** `docs/AUTHORIZATION.md` ("Current Coverage").
  * **Current → required:** It says undeclared route classification remains tracked in the closed [CENTRALIZED_AUTHORIZATION_SYSTEM_TASK_PLAN.md](../done/MITIGATE_SECURITY_ISSUES/done/CENTRALIZED_AUTHORIZATION_SYSTEM_TASK_PLAN.md). Required: it points at the cutover plan Phase 1 record and states that the inventory carries no `UNDECLARED` row after this phase.
  * **Constraints:** Keep the ingester statement accurate: ingester authorization remains proposed work owned by `INGESTER_AUTHORIZATION_TASKS.md`.
  * **Validation:** `V-9`.

**Completion evidence:** The inventory carries a dated review note with a named reviewer, and `AUTHORIZATION.md` points at the current classification record.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
| --- | --- | --- | --- |
| `PH1-AC-1` | `T1.1`, `T1.3`, `T2.1`, `T2.3` | `V-1`, `V-2`, `V-4` | The inventory has no `UNDECLARED` row; the classification check reports an undeclared synthetic route and passes for the assembled app |
| `PH1-AC-2` | `T1.2`, `T1.4`, `T2.2` | `V-3`, `V-5` | Every assembled API, direct, and mounted route maps to a row stating its requirement and exposure status |
| `PH1-AC-3` | `T3.1`, `T3.2`, `T3.3` | `V-6` | Every lifecycle entry point and background operation has a recorded authorization and lifecycle or operation-record behavior |
| `PH1-AC-4` | `T1.*`, `T2.*`, `T3.*`, `T4.*` | `V-1`, `V-3`, `V-7`, `V-8`, `V-9` | The authorization suite, the full backend suite, and formatting and link checks pass at the reviewed commit |

## Validation And Testing

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
| --- | --- | --- | --- | --- | --- |
| `V-1` | Authorization suite | `uv run pytest backend/tests/authorization -q` | `PH1-AC-1`, `PH1-AC-4` | Pass, including the new classification check | Pass, 180 passed, 1 skipped at `c3ee7b07` |
| `V-2` | Session and state tests | `uv run pytest backend/tests/test_session_authorization.py backend/tests/test_state_manager.py -q` | `PH1-AC-1` | Pass with the session route using the declared dependency | Pass, 38 passed at `c3ee7b07` |
| `V-3` | Inventory parity and classification | `uv run pytest backend/tests/authorization/test_route_authentication.py -q` | `PH1-AC-1`, `PH1-AC-2`, `PH1-AC-4` | Pass for the assembled app; the documented set equals the registered set | Existing parity test passes at `c3ee7b07`; no classification check exists |
| `V-4` | Negative classification case | `uv run pytest backend/tests/authorization/test_route_authentication.py -q -k classified` | `PH1-AC-1` | The helper reports a synthetic undeclared API route | Not run: check does not exist |
| `V-5` | Inventory completeness review | Manual: print the assembled routes with `_assembled_routes()` and compare them with the inventory rows, including the 23 former `UNDECLARED` rows | `PH1-AC-2` | No assembled route lacks a row; no row remains `UNDECLARED`; review note records reviewer and date | Not run: review not yet performed |
| `V-6` | Lifecycle and background review | Manual: inspect the five lifecycle entry points and the background entry points found by the `T3.3` search; compare with the recorded section | `PH1-AC-3` | Each entry point records its authorization, lifecycle or operation call, and evidence location | Not run: review not yet performed |
| `V-7` | Full backend regression | `uv run pytest backend/tests -q` | `PH1-AC-4`, existing behavior | Pass; no regression in route, session, or operation behavior | Not run at plan time |
| `V-8` | Formatting and lint on changed files | `uv run isort --check-only backend/app backend/tests`, `uv run black --check backend/app backend/tests` | Changed Python files | No formatting change required | Not run at plan time |
| `V-9` | Documentation link check | `scripts/check_doc_links.sh` | `PH1-AC-2`, documentation updates | Pass | Pass on 2026-09-16 |

For every check, record the commit, the command output, and the reviewer in the phase progress record. Do not report a planned check as a current pass.

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Route classification record | `docs/AUTHORIZATION_ROUTE_INVENTORY.md` | `T1.2`–`T1.4`, `T4.1` | No `UNDECLARED` row; each row states requirement and exposure; review note present |
| Lifecycle and background section | `docs/AUTHORIZATION_ROUTE_INVENTORY.md` | `T3.1`, `T3.3` | Lifecycle entry points and background operations recorded with evidence locations |
| API route classification check | `backend/tests/authorization/test_route_authentication.py` | `T2.1`–`T2.3` | Suite fails for an undeclared API route; passes for the assembled app |
| Session route declaration | `backend/app/api/v1/endpoints/sessions.py::create_session` | `T1.1` | `project:edit` metadata present; concealed `404` preserved |
| Project dependency body locator | `backend/app/authorization/dependencies.py::require_project` | `T1.1` | Opt-in body locator; existing callers unchanged |
| Active project declaration | `backend/app/api/v1/endpoints/projects.py::get_active_project_name` | `T1.2` | `project:read` metadata present; concealed `404` for an unreadable active project; `null` when no project is active |
| Session and dependency tests | `backend/tests/test_session_authorization.py`, `backend/tests/authorization/test_dependencies.py` | `T1.1` | Declared metadata assertion and concealed-`404` case pass |
| Documentation alignment | `docs/AUTHORIZATION.md`, `backend/app/services/project_service.py`, `backend/app/services/project/project_operations.py`, `backend/app/api/v1/endpoints/projects.py` | `T3.2`, `T4.2` | No reference to a non-existent rename path; coverage note points at the current plan |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Record classifications | Done | None | `T1.1` done at `64d0556a`; `T1.3` done at `e9678693`. `T1.2` and `T1.4` recorded with the rows. `GET /api/v1/projects/active/name` was classified `project:read` through a new `require_active_project` dependency instead of `authenticated`, because the route reports the deployment active project and the principal may not be able to read it. The inventory has no `UNDECLARED` row. `uv run pytest backend/tests/authorization backend/tests/api/v1/test_projects.py` passes |
| Area 2: Enforce classification in the check | Not started | Area 1 (classification sets and inventory rows) | |
| Area 3: Record lifecycle and background coverage | Not started | None | Independent of Areas 1 and 2 |
| Area 4: Review and align documentation | Not started | Areas 1–3 | Reviewer `TBD` |

## Definition Of Done

- [ ] Every phase acceptance criterion has implementation and validation evidence recorded for the reviewed commit.
- [ ] `docs/AUTHORIZATION_ROUTE_INVENTORY.md` contains no `UNDECLARED` row and records lifecycle entry points and background operations.
- [ ] The classification check fails for an undeclared API route and passes for the assembled application.
- [ ] Concealed `404` behavior for the session route and filtered project listing is unchanged, and `body_locator` defaults preserve every other `require_project` caller.
- [ ] Ingester enforcement remains recorded as pending work owned by `INGESTER_AUTHORIZATION_TASKS.md`, and no ingester behavior changed.
- [ ] The inventory review note names the reviewer and date, and `docs/AUTHORIZATION.md` points at the current classification record.
- [ ] Focused tests, the full backend suite, formatting checks, and the documentation link check pass.
- [ ] Follow-up items are recorded: ingester capability authorization, server-side source resolution for `/suggestions/*`, and the removed rename references.
- [ ] No unresolved decision changes implementation, correctness, or validation for this phase.

## Risks And Open Questions

**Risks**

- **Shared dependency blast radius.** `require_project` is used by many routes. The body locator must stay opt-in, and `V-1`, `V-2`, and `V-7` must confirm that existing concealed-`404` behavior is unchanged.
- **The classification check can decay into an allowlist.** New routes could be added to `AUTHENTICATED_ONLY_API_PATHS` without review. Mitigation: every constant entry carries its reason, and the failure message lists unclassified routes so a reviewer sees them.
- **Build-state conditional rows.** The inventory documents `/assets/*`, `/{full_path:path}`, and `/` as conditional on the frontend build. The check must tolerate their absence so an API-only build never fails the suite.
- **Ingester routes stay authentication-only until their own plan lands.** The classification records this; Phase 4 must not treat those routes as protected.

**Open questions**

- **Who reviews and signs the classification?** `TBD` (repository authorization owner). It blocks the `T4.1` review note, not the implementation. Record the name before `V-5`.
- **Should `POST /suggestions/analyze` resolve `data_source_name` server-side and require shared-source read?** Recommended resolution: keep authenticated-only in this phase and record the follow-up, matching the accepted `POST /data-sources/tables` disposition. Changing it requires the schema service to resolve a registered source, which is a separate change.
- **Should `/projects/active/name` conceal the active project name from principals without project read?** Recommended resolution: no in this phase, because the route is not identifier-addressed and the response carries only the deployment active project name. A `null` fallback is a response-contract change for the frontend and should be raised as follow-up if the deployment requires it.

If verified repository state conflicts with this plan during implementation, stop and report the conflict and the evidence instead of redesigning the inventory or broadening the phase.
