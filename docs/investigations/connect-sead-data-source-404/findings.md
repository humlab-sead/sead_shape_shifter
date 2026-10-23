# Investigation findings: CONNECT reports 404 for a new project

**Brief:** User report in this session; no separate investigation brief.
**Status:** Conclusive
**Environment / baseline:** Shape Shifter repository at `24dde7fa168b84042bf636abc92d2ad584d57a52`; Linux. The user's running frontend/backend and project authorization state were not available.

## Executive summary

The supplied Network details identify the failing request as `POST /api/v1/projects/Roger-test/data-sources`, with response `{"detail":"Resource not found"}`. The backend attaches both project-edit and shared-source-read authorization dependencies to this route. There is a concrete parameter collision in the shared-source dependency: the route's path parameter `name` (`Roger-test`) is selected as the data-source reference before the dependency reads `source_filename` from the request body. It then searches for a shared data source named `Roger-test`, not `sead-options`, and returns the same 404 response.

This defect explains why changing the selected source does not help. The user confirms they are project owner and admin, which makes denial by the separate project-edit check unlikely. The fix adds an explicit body-locator mode to the shared-source dependency and enables it for the project connection route. Other routes retain their existing path-parameter lookup.

## Verified observations and reproduction

- The user reports that pressing **CONNECT** while connecting a SEAD source to a new project produces `Error Loading Project` and `Request failed with status code 404`. The report is not an independently reproduced observation.
- The user supplied the failed request: `POST https://shape-shifter.sead.se/api/v1/projects/Roger-test/data-sources`, payload `{"source_name":"sead","source_filename":"${GLOBAL_DATA_SOURCE_DIR}/sead-options.yml"}`, response `{"detail":"Resource not found"}`.
- The user confirms they are owner of project `Roger-test` and are also an admin.
- On the current project detail page, the `Error Loading Project` alert displays `projectError` ([`ProjectDetailView.vue`](../../../frontend/src/views/ProjectDetailView.vue#L74)).
- The Connect component sends the selected source to `projectStore.connectDataSource`; after that succeeds it reloads connected sources and emits `updated` ([`ProjectDataSources.vue`](../../../frontend/src/components/ProjectDataSources.vue#L293)).
- The parent handles `updated` by calling `handleRefresh()`, which sends the project refresh request. A failure is left in `projectStore.error` for the page alert ([`ProjectDetailView.vue`](../../../frontend/src/views/ProjectDetailView.vue#L1581), [`ProjectDetailView.vue`](../../../frontend/src/views/ProjectDetailView.vue#L2472)).
- If the initial connection request itself fails, the Connect component catches it into `connectError` instead and does not emit `updated` ([`ProjectDataSources.vue`](../../../frontend/src/components/ProjectDataSources.vue#L293)).
- The UI builds the source reference from the configured global data-source directory and the source's filename stem ([`ProjectDataSources.vue`](../../../frontend/src/components/ProjectDataSources.vue#L264)). The repository contains `sead-options.yml` and `arbodat-data-options.yml`.
- The backend connection endpoint requires project edit access and shared data-source read access ([`projects.py`](../../../backend/app/api/v1/endpoints/projects.py#L564)). The project refresh endpoint also requires project edit access ([`projects.py`](../../../backend/app/api/v1/endpoints/projects.py#L173)).
- Before the fix, the shared-source dependency resolved `filename or name or data_source_name` before reading `source_filename` from the JSON body. Since this route has a path parameter named `name`, FastAPI supplied `Roger-test` for that dependency parameter. The dependency then looked up that project name as a shared-source locator and raised `404 Resource not found` ([`dependencies.py`](../../../backend/app/authorization/dependencies.py#L110), [`dependencies.py`](../../../backend/app/authorization/dependencies.py#L143)).
- The project connection route now configures the dependency to read `source_filename` from the body before considering any route parameters ([`projects.py`](../../../backend/app/api/v1/endpoints/projects.py#L38), [`dependencies.py`](../../../backend/app/authorization/dependencies.py#L110)).
- The request body filename would resolve to shared-source locator `sead-options`, but the dependency never reaches that value when the path `name` is populated.
- The user's reported owner and admin roles make denial by the route's separate project-edit authorization check unlikely.

## Evidence ledger

| ID | Observation or test | Source | Result | Assessment |
| --- | --- | --- | --- | --- |
| E1 | User supplied the failing CONNECT request and response. | User-provided Network details in this session | `POST /api/v1/projects/Roger-test/data-sources`; response `{"detail":"Resource not found"}`; source filename is `${GLOBAL_DATA_SOURCE_DIR}/sead-options.yml`. | Verified as a report |
| E2 | Project detail displays `projectError` under the exact reported heading. | [`ProjectDetailView.vue`](../../../frontend/src/views/ProjectDetailView.vue#L74) | Connect-dialog errors and project-page errors use different UI state. | Verified |
| E3 | After a successful connection and connected-source reload, the component emits `updated`; the parent then runs the project refresh handler. | [`ProjectDataSources.vue`](../../../frontend/src/components/ProjectDataSources.vue#L293), [`ProjectDetailView.vue`](../../../frontend/src/views/ProjectDetailView.vue#L2472) | A failure in the follow-up refresh can show the reported page-level error after CONNECT. | Verified code path |
| E4 | Project refresh is a `POST /projects/{name}/refresh` and checks project edit permission. | [`projects.ts`](../../../frontend/src/api/projects.ts#L75), [`projects.py`](../../../backend/app/api/v1/endpoints/projects.py#L173) | This is the first candidate request to inspect if the page-level error appeared after the dialog closed. | Supported hypothesis |
| E5 | Before the fix, the shared-source dependency used the route parameter named `name` before request-body `source_filename`. | [`dependencies.py`](../../../backend/app/authorization/dependencies.py#L110), [`projects.py`](../../../backend/app/api/v1/endpoints/projects.py#L564) | For this request, `name` was `Roger-test`; the source filename was ignored and the wrong shared-source locator was checked. | Verified code defect |
| E6 | Authorization checks conceal missing or unauthorized project/shared-source resources as 404. | [`dependencies.py`](../../../backend/app/authorization/dependencies.py#L51), [`dependencies.py`](../../../backend/app/authorization/dependencies.py#L143) | User reports owner and admin access, making denial by the project-edit check unlikely. | Verified code and user-reported access |
| E7 | The regression test supplies `name="project-a"` and an authorized body source through the actual project connection route dependency. | [`test_dependencies.py`](../../../backend/tests/authorization/test_dependencies.py#L193) | It now returns the authorized `source-a` resource, proving the route uses the body locator rather than the project name. | Passed |
| E8 | Focused authorization contract test passed. | `uv run pytest backend/tests/authorization/test_dependencies.py::test_project_data_source_connection_requires_project_and_shared_source_access -q` | 1 test passed; it checks declared route requirements, not the runtime parameter collision. | Verified |

## Timeline or causal chain

1. The Connect action submits `source_filename` to `POST /projects/Roger-test/data-sources`.
2. The route requires edit access to project `Roger-test` and read access to the selected shared source.
3. For the shared-source dependency, FastAPI binds the route's `name` path parameter to the dependency's `name` argument.
4. The dependency chooses `name` (`Roger-test`) before inspecting the request body, then attempts to authorize `Roger-test` as a shared source.
5. When that shared-source resource is not found or readable, the dependency returns `404 {"detail":"Resource not found"}` before the connection handler runs.

The request URL and response are confirmed by the user. The parameter collision and resulting incorrect lookup are confirmed by current source. The user's owner/admin status is consistent with the project-edit check passing and the shared-source dependency causing the reported 404.

## Root-cause assessment

**Confirmed mechanism:** Before the fix, the shared-source authorization dependency read the route's project `name` parameter as if it were a data-source locator. This request's `Roger-test` path value took precedence over the body value `sead-options.yml`, so the permission check looked up the wrong resource and returned 404. The user reports owner and admin access, making denial by the preceding project-edit check unlikely.

| Hypothesis | Supporting evidence | Contrary evidence / checks | Status |
| --- | --- | --- | --- |
| The shared-source dependency mistakes the project route name for the selected source name. | The failing request path contains `Roger-test`; the dependency selected its `name` argument before reading the body; the exact response is its concealed 404. The regression test reproduced and now prevents this behavior. | The deployed authorization store was not inspected, but the reported roles are consistent with project edit access. | Confirmed; fixed in the working tree |
| The request fails first because the user lacks project edit access to `Roger-test`. | The route's project-edit dependency can return the same concealed 404. | User reports being the project owner and an admin. | Unlikely alternative |
| One of the two SEAD source files has invalid connection settings. | The files configure different source types and endpoints. | The failing shared-source authorization runs before the connection handler and before any database connection attempt. | Ruled out as the cause of this 404 |

## Impact and extent

**Confirmed affected cases:** One user-reported attempt connecting a SEAD data source to a new project. The source file and project were not independently inspected in the user's running environment.

**Potential wider impact:** Any caller receiving a concealed authorization 404 for the project or shared data source could see a similar Axios status. No broader impact is established.

## Remediation options

| Option | Benefits | Risks / compatibility | Prerequisites / validation |
| --- | --- | --- | --- |
| Configure the project connection route to authorize its body `source_filename`. | Authorizes the selected shared source (`sead-options`) rather than the project (`Roger-test`). | Other routes retain their existing path-parameter lookup. | Implemented with `body_locator=True`; focused authorization and endpoint tests pass. |
| Confirm the project's authorization record grants the reported owner edit access. | Verifies the preceding authorization check passed. | Do not broaden access unless the stored grant contradicts the reported role. | Check the project authorization record if the issue persists after fixing the parameter collision. |

**Recommended next step:** Deploy the fix after normal review. The running service was not changed or re-tested during this investigation.

**Prevention / regression detection:** Keep the focused regression test with a project path parameter named `name` and a distinct body `source_filename`. Retain tests for path-based shared-source endpoints.

## Unresolved questions and blockers

- Does the deployed backend match the inspected repository revision? The request behavior aligns with this dependency defect, but the running deployment was not inspected.

## Verification record

- Repository source inspection at commit `24dde7fa168b84042bf636abc92d2ad584d57a52`.
- User-provided browser Network details for the failed POST and its response.
- Passed: `uv run pytest backend/tests/authorization/test_dependencies.py -q -n 0 --tb=short` (19 passed, 1 skipped).
- Passed: `uv run pytest backend/tests/authorization backend/tests/api/v1/test_query_endpoints.py backend/tests/api/v1/test_schema_endpoints.py backend/tests/test_data_source_api.py -q -n 0 --tb=short` (passed; 2 skipped).
- Passed: Black and isort checks for the changed Python files; `git diff --check`.
- Passed: Pylance signature compatibility check; all 9 callers remain compatible.
- Passed: `.venv/bin/graphify update . --force`. The initial update was refused because the cached graph node count differed.
- Not performed: live reproduction against the user's Shape Shifter instance or authorization-store inspection.

## References

- [`ProjectDataSources.vue`](../../../frontend/src/components/ProjectDataSources.vue)
- [`ProjectDetailView.vue`](../../../frontend/src/views/ProjectDetailView.vue)
- [`projects.ts`](../../../frontend/src/api/projects.ts)
- [`projects.py`](../../../backend/app/api/v1/endpoints/projects.py)
- [`dependencies.py`](../../../backend/app/authorization/dependencies.py)
- [`test_dependencies.py`](../../../backend/tests/authorization/test_dependencies.py)
- [Issue #587](https://github.com/humlab-sead/sead_shape_shifter/issues/587)
