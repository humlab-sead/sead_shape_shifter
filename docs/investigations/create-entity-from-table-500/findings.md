# Investigation findings: Create Entity from Table returns HTTP 500

**Brief:** User report and screenshot in this conversation; no separate brief or server trace provided.
**Status:** Partially conclusive
**Environment / baseline:** Local Shape Shifter branch `value-reference-column-pickers`, HEAD `1b929e5e3a307c0c045de435e477877726c680ca`, 2026-10-24. The worktree was already dirty before this investigation. No application source was changed.

## Executive summary

The screenshot confirms that the **Create Entity from Table** action returned HTTP 500 for `tbl_locations`. The dialog had already displayed a generated preview for `public.tbl_locations` with primary key `location_id`. That preview is assembled in the browser after table-schema lookup; clicking **Create Entity** sends a separate request to `POST /projects/{project_name}/entities/generate-from-table`.

The user-provided project YAML confirms that `SEAD` is configured as `@include: ${GLOBAL_DATA_SOURCE_DIR}/sead-options.yml`. This matches the suspected failure condition. The entity-generation service creates its own `SchemaIntrospectionService` using `settings.PROJECTS_DIR`; the schema API used by the dialog instead uses `settings.GLOBAL_DATA_SOURCE_DIR`. The entity service strips `@include:` but does not resolve `${GLOBAL_DATA_SOURCE_DIR}`. A local isolated path check confirmed that this generator configuration looks for the source under the projects directory and misses it. The resulting missing data source is converted to a 500 by the endpoint error handling.

This does not appear to be a newly introduced change or a fix already covered by a recent bug. It is a leftover from the directory mismatch tracked in [issue #251](https://github.com/humlab-sead/sead_shape_shifter/issues/251): that fix corrected the shared data-source directory used by the general schema API, but the entity-generator constructor still points at the projects directory. The project configuration now confirms that its `SEAD` source uses this reference form. The exact deployed exception remains unconfirmed because the server response body/log and deployed revision were not supplied.

## Verified observations and reproduction

- The user-provided screenshot shows the selected table `tbl_locations`, preview SQL `SELECT * FROM public.tbl_locations`, key `location_id`, public ID `tbl_locations_id`, and a 500 after clicking **Create Entity**. This is a reported failure, not a live reproduction.
- The user-provided project YAML snapshot confirms `data_sources.SEAD: '@include: ${GLOBAL_DATA_SOURCE_DIR}/sead-options.yml'` (snapshot lines 43-45). The user states that this reference points to the supplied `sead-options.yml`; its connection values are not needed for this path diagnosis.
- The dialog fetches tables and table schema through `schemaApi`, then calls `entitiesApi.generateFromTable` on create ([`CreateEntityFromTableDialog.vue`](../../../frontend/src/components/entities/CreateEntityFromTableDialog.vue#L205), [`CreateEntityFromTableDialog.vue`](../../../frontend/src/components/entities/CreateEntityFromTableDialog.vue#L229), [`CreateEntityFromTableDialog.vue`](../../../frontend/src/components/entities/CreateEntityFromTableDialog.vue#L240)).
- The create request uses `/projects/${projectName}/entities/generate-from-table` ([`entities.ts`](../../../frontend/src/api/entities.ts#L234)). The backend route calls `EntityGeneratorService.generate_from_table()` ([`entities.py`](../../../backend/app/api/v1/endpoints/entities.py#L297)).
- The default `EntityGeneratorService` constructs `SchemaIntrospectionService(settings.PROJECTS_DIR)` ([`entity_generator_service.py`](../../../backend/app/services/entity_generator_service.py#L25)). That service uses its constructor argument as the `DataSourceService` directory ([`schema_service.py`](../../../backend/app/services/schema_service.py#L96)).
- The normal schema API uses `SchemaIntrospectionService(settings.GLOBAL_DATA_SOURCE_DIR)` ([`dependencies.py`](../../../backend/app/api/dependencies.py#L48)). In the local runtime, the directories were different: `data/projects` versus `data/shared/data-sources`.
- For a string project data source, the entity service strips `@include:` and returns the remaining filename/path without resolving it ([`entity_generator_service.py`](../../../backend/app/services/entity_generator_service.py#L110)). `DataSourceService` joins that value to its configured directory and returns `None` when no file is found ([`data_source_service.py`](../../../backend/app/services/data_source_service.py#L33), [`data_source_service.py`](../../../backend/app/services/data_source_service.py#L148)).
- An isolated temporary-directory check confirmed the lookup mismatch: a file in `shared/data-sources/sead-options.yml` existed, while the same source reference looked up under `projects/${GLOBAL_DATA_SOURCE_DIR}/sead-options.yml` did not. No database connection was attempted.
- When the generator's schema service cannot load the data source, `get_table_schema()` raises `SchemaIntrospectionError` ([`schema_service.py`](../../../backend/app/services/schema_service.py#L187)). The endpoint error handler returns domain exceptions as HTTP 500 ([`error_handlers.py`](../../../backend/app/utils/error_handlers.py#L88)).
- The generator service tests passed, but their fixture injects a mocked schema service and therefore does not exercise this default directory wiring ([`test_entity_generator_service.py`](../../../backend/tests/services/test_entity_generator_service.py#L41)).
- No local application log entries matched `tbl_locations` or the generation route. The production/server log and the response JSON for the screenshot were not available.

## Evidence ledger

| ID | Observation or test | Source | Result | Assessment |
| --- | --- | --- | --- | --- |
| E1 | Screenshot shows schema-derived preview and HTTP 500 after create. | User-provided screenshot | `tbl_locations`, `public`, `location_id`, then 500. | Verified as a report |
| E2 | Preview and create use different API paths. | [`CreateEntityFromTableDialog.vue`](../../../frontend/src/components/entities/CreateEntityFromTableDialog.vue#L205), [`entities.ts`](../../../frontend/src/api/entities.ts#L234), [`entities.py`](../../../backend/app/api/v1/endpoints/entities.py#L297) | Schema browsing uses the schema API; create uses the project entity-generation route. | Verified |
| E3 | The generation service's default schema service uses the projects directory. | [`entity_generator_service.py`](../../../backend/app/services/entity_generator_service.py#L25), [`schema_service.py`](../../../backend/app/services/schema_service.py#L99) | The service then searches for filename-based data sources under that directory. | Verified |
| E4 | The general schema API uses the shared data-source directory. | [`dependencies.py`](../../../backend/app/api/dependencies.py#L48), [`config.py`](../../../backend/app/core/config.py#L69) | This explains how table browsing can work while the create route fails to reopen the source. | Verified |
| E5 | A temporary-directory path check reproduced the mismatch. | Isolated `uv run python` check; temporary fixture only | The shared file existed under the global source directory, but the generator-style lookup did not find it. | Verified code behavior |
| E6 | An `@include` value containing `${GLOBAL_DATA_SOURCE_DIR}` is not resolved by the generator's helper. | [`entity_generator_service.py`](../../../backend/app/services/entity_generator_service.py#L110), [`data_source_service.py`](../../../backend/app/services/data_source_service.py#L33) | The raw path is joined to the wrong base directory in the default service. | Verified mechanism; applicability confirmed by supplied project config |
| E7 | Generator unit tests passed with mocked dependencies. | `uv run pytest backend/tests/services/test_entity_generator_service.py -q` | 9 passed. Tests do not construct the default schema service. | Verified, limited coverage |
| E8 | No exact recent GitHub issue for this create-route 500 was found. | Repository issue search; related issues below | The matching create feature is old; nearby reports concern other routes. | Verified search result, not proof no issue exists |
| E9 | The affected project uses a shared-source include with `${GLOBAL_DATA_SOURCE_DIR}`. | User-provided project YAML snapshot, lines 43-45 | The project configuration matches the path form that the default entity-generator lookup fails to resolve. | Verified |

## Timeline or causal chain

1. On 2026-02-05, commit `ab24c2f2` added the generator's default `SchemaIntrospectionService(settings.PROJECTS_DIR)` construction.
2. On 2026-02-16, [issue #251](https://github.com/humlab-sead/sead_shape_shifter/issues/251) documented that schema/data-source services needed `GLOBAL_DATA_SOURCE_DIR`, not `PROJECTS_DIR`. The general schema API now uses the global directory, but the entity generator still uses the older path.
3. On 2026-02-05, [issue #217](https://github.com/humlab-sead/sead_shape_shifter/issues/217) and merged [PR #218](https://github.com/humlab-sead/sead_shape_shifter/pull/218) introduced entity generation from database tables. No later matching issue or fix for this endpoint was found.
4. The separate preview problem in [issue #468](https://github.com/humlab-sead/sead_shape_shifter/issues/468) concerned a mapper-context error in the entity preview flow; commit `b5e41962` changed `ShapeShiftService.preview_entity()`, not the table-generation route.
5. The recent authorization work in [issue #587](https://github.com/humlab-sead/sead_shape_shifter/issues/587), including `e0ff1a8`, changes authorization for SQL column-introspection requests. It does not change `generate-from-table`.
6. Commit `5cf2bd4` on 2026-10-24 allows resolver-approved environment variables in server-managed source configurations. It does not change the generator's directory selection or resolve its raw `@include` filename.

## Root-cause assessment

**Confirmed mechanism:** The current default entity-generation path uses a different data-source directory from the schema API and does not resolve an included source path. The supplied project configuration confirms that its `SEAD` source uses this reference form. This is a strong explanation for the screenshot; the deployed server trace is still needed to confirm the exact exception.

| Hypothesis | Supporting evidence | Contrary evidence / checks | Status |
| --- | --- | --- | --- |
| The create route cannot reopen this project's shared source reference. | The supplied YAML uses `@include: ${GLOBAL_DATA_SOURCE_DIR}/sead-options.yml`; generator default uses `PROJECTS_DIR`; normal schema API uses `GLOBAL_DATA_SOURCE_DIR`; isolated lookup reproduced a miss. | The deployed server version and exception log are unavailable. Inline dictionary configuration would bypass this file lookup, but it is not the configuration supplied here. | Supported hypothesis; very strong fit |
| A recent authorization fix already fixed this 500. | Recent issue #587 contains related SQL introspection authorization work. | Its change is in the query-column introspection route; create uses `require_project(Action.EDIT)` and `EntityGeneratorService`. | Ruled out |
| The recent entity-preview mapper fix covers this failure. | The screenshot includes generated preview YAML. | Preview is computed from a separate schema request; commit `b5e41962` changes the entity preview mapper path, not table generation. | Ruled out |
| A duplicate entity name caused this 500. | The entered name matches the selected table and could already exist. | `ResourceConflictError` is mapped to HTTP 409, not 500 ([`error_handlers.py`](../../../backend/app/utils/error_handlers.py#L77)). | Ruled out for the normal duplicate path |
| The SEAD database/table itself is unavailable. | The create request may load and introspect the source again. | The dialog already had table metadata; no backend trace or live request was available. | Unverified |

## Impact and extent

**Confirmed affected cases:** One user-reported attempt to create an entity from `tbl_locations`; no independent reproduction against the user's deployment.

**Potential wider impact:** The same failure can affect the default create-from-table service for projects whose data source is a filename/string reference stored outside `PROJECTS_DIR`. Inline data-source dictionaries or source files also present under the projects directory may avoid this specific lookup failure. Other causes of 500 remain possible without the server trace.

## Remediation options

| Option | Benefits | Risks / compatibility | Prerequisites / validation |
| --- | --- | --- | --- |
| Route entity generation through the established project/source resolver, or inject the shared-source-aware schema service and normalize `@include` paths consistently. | Uses the same source resolution rules as schema browsing and avoids duplicate path handling. | Must preserve inline dictionaries and project-local source references. | Add a regression test using a project `@include` reference and a temporary shared-source directory; test the POST route through persistence. |
| Capture the failed request's response JSON and correlated backend log before changing code. | Confirms whether this path mismatch is the cause rather than another 500. | Requires access to the deployment logs and the affected project's source reference. | Record the response body, correlation ID, and `data_sources.SEAD` value with credentials redacted. |

**Recommended next step:** Treat this as an unresolved, likely missed call site from the directory-path issue in #251—not as a bug already fixed by the recent preview or authorization changes. Confirm the project's `data_sources.SEAD` reference and the server log. If it is a shared-file reference, implement the source-resolution correction and add a route-level regression test.

**Prevention / regression detection:** Test the default generator wiring, not only service behavior with mocked dependencies. Cover an `@include` shared-source reference, a resolved inline dictionary, and a project-local source. Assert that a missing source produces an actionable error rather than a generic 500.

## Unresolved questions and blockers

- What JSON response body and backend exception correspond to the 500?
- Is the reported UI running the same revision as the local repository state?

The smallest next check is to inspect the failed request's response body and matching backend log entry, and confirm the deployed revision. The supplied `SEAD` source reference already matches the path-resolution defect found in the local code.

## Verification record

- Passed: `uv run pytest backend/tests/services/test_entity_generator_service.py -q` — 9 passed.
- Passed: isolated temporary-directory check showing the generator-style lookup misses a file under the shared-source directory when based on the projects directory.
- Verified: supplied project YAML uses `@include: ${GLOBAL_DATA_SOURCE_DIR}/sead-options.yml` for `SEAD`.
- Inspected current branch history and GitHub issues #217, #218, #251, #468, and #587; no code changes were made.
- Not performed: live reproduction, database access, deployment inspection, or review of the affected project's YAML/server logs.

## References

- [`CreateEntityFromTableDialog.vue`](../../../frontend/src/components/entities/CreateEntityFromTableDialog.vue)
- [`entities.py`](../../../backend/app/api/v1/endpoints/entities.py)
- [`entity_generator_service.py`](../../../backend/app/services/entity_generator_service.py)
- [`schema_service.py`](../../../backend/app/services/schema_service.py)
- [`data_source_service.py`](../../../backend/app/services/data_source_service.py)
- [`dependencies.py`](../../../backend/app/api/dependencies.py)
- [`error_handlers.py`](../../../backend/app/utils/error_handlers.py)
- [Issue #217](https://github.com/humlab-sead/sead_shape_shifter/issues/217)
- [Issue #251](https://github.com/humlab-sead/sead_shape_shifter/issues/251)
- [Issue #468](https://github.com/humlab-sead/sead_shape_shifter/issues/468)
- [Issue #587](https://github.com/humlab-sead/sead_shape_shifter/issues/587)
- [Commit `5cf2bd4`](https://github.com/humlab-sead/sead_shape_shifter/commit/5cf2bd4ebdc59293393d9f6509f8c59c0597fb7d)
- [Commit `e0ff1a8`](https://github.com/humlab-sead/sead_shape_shifter/commit/e0ff1a8ed3f24b25df18510c9ba515992c6256ec)
