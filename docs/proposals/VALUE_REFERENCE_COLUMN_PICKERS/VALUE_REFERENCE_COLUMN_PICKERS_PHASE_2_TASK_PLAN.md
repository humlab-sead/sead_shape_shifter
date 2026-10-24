# Value Reference Column Pickers — Phase 2 Task Plan

## Phase Summary

**Phase:** [Phase 2: Resolve requested references from drafts](VALUE_REFERENCE_COLUMN_PICKERS_PHASE_PLAN.md#phase-2-resolve-requested-references-from-drafts)

**Source proposal:** [Make `@value` References Usable in Column Pickers](VALUE_REFERENCE_COLUMN_PICKERS.md)

**Readiness:** Validated. The phase plan's condition is met: [Phase 1](VALUE_REFERENCE_COLUMN_PICKERS_PHASE_1_TASK_PLAN.md) records the confirmed field set and completed form-preservation checks.

**Goal:** Return ordered column names, or one local unresolved reason, for a requested simple `@value` reference in the current unsaved entity draft. Offer filtered entity-property choices without letting an unrelated broken reference suppress valid choices.

**Constraints and dependencies:** Preserve raw API/YAML directive text and the existing full `ProjectMapper.to_core()` behavior. Resolve directives only through the mapper's API-to-Core path, with the same file roots and environment-variable rules. Do not save the draft. Phase 2 supplies a backend contract for Phases 3 and 4; it does not add editor controls or saved-project validation.

**Acceptance criteria**

1. [x] `PH2-AC-1` (from `P-AC-3`): A requested reference returns ordered strings from the unsaved draft or a local unresolved reason; an unrelated missing or circular reference does not block a valid result.
2. [x] `PH2-AC-2` (from `P-AC-2`): Eligible entity properties are checked independently, and a manually entered full path can be checked without relying on the project-wide path list.
3. [x] `PH2-AC-3` (from `P-AC-7`): Read requests enforce project authorization and do not persist the draft or alter normal full-project conversion.

**Phase milestone:** `VM-2` covers draft changes, ordered and nested results, wrong types, requested-path and unrelated failures, authorization, and unchanged full conversion through `V-1`–`V-4`.

## Repository Findings

**Repository basis:** Branch `value-reference-column-pickers`, commit `a4b19529`, planning date 2026-10-24. The untracked phase plan was read as the source document; no other uncommitted changes were present before this task plan. Graphify supplied navigation, and the findings below were checked in source and tests. The existing focused baseline passed: 54 tests in mapper, column-availability, and Core directive files, plus 16 mapper file-path and authorization tests. The focused Ruff check passed.

| Source | Verified behavior | Planning implication |
| --- | --- | --- |
| `backend/app/mappers/project_mapper.py::ProjectMapper.to_core_dict`, `to_core` | API-to-Core conversion preserves a raw dict first, then transforms every entity, resolves the whole directive tree, and validates the mapping sidecar. `to_api_config` and `to_core_dict` keep directives raw. | Add an explicit editor-only branch to `to_core`; leave the default branch unchanged. A broken unrelated entity, directive, or sidecar must not enter requested-reference resolution. |
| `src/configuration/resolve.py::resolve_directives`, `ReferenceResolver` | Full resolution deep-copies the tree, resolves `@include`, `@load`, and environment variables, then resolves all `@value` references. List-item references flatten resolved lists. A missing simple path can remain raw, an expression can skip a missing operand, and a cycle can recurse. | Reuse the existing directive rules for visited dependencies, but detect missing paths, cycles, and unresolved dependencies explicitly in the scoped path; never return a partial list. Do not change the full resolver's behavior in this phase. |
| `backend/app/services/stage_aware_column_service.py::get_column_availability`, `backend/app/api/v1/endpoints/columns.py::get_stage_aware_column_availability` | The existing read endpoint copies the loaded `Project`, applies `entity_draft`, and calls full `to_core`. Its output is operation-specific column suggestions. | Reuse the draft-copy pattern, but keep reference completion and inspection in a separate service and response contract. Do not replace stage-aware ordinary suggestions. |
| `backend/app/services/directive_validator.py::DirectiveValidator`, `backend/app/api/v1/endpoints/directives.py` | The saved-project validator looks up raw values; `/valid-directives` lists paths without checking that they resolve to string lists. | Do not use either as the source of typed draft candidates. Keep their current contracts for existing callers. |
| `backend/app/authorization/dependencies.py::require_project`, `backend/app/api/v1/api.py` | Project routes authorize with `require_project(Action.READ)` and use the authorized resource locator. New endpoint modules are registered in `api_router`. | Protect both new POST read routes before loading a project and register their router. |
| `docs/proposals/VALUE_REFERENCE_COLUMN_PICKERS/VALUE_REFERENCE_COLUMN_PICKERS_PHASE_1_TASK_PLAN.md` | The confirmed in-scope fields are keys, non-fixed columns, FK local/remote keys, unnest ID/value variables, deduplication columns, and drop-empty columns. Fixed Entity Columns stay excluded. | The new response is usable by those fields; this phase does not change their form storage or add a picker to Fixed Entity Columns. |

## Scope

**In scope:** A mapper-owned, read-only way to resolve one simple full path and its nested dependencies; independent string-list checks for entity-property candidates; filtered completion of `entities.<name>.<property>`; validation of a complete manually entered `@value:` path, including another supported path such as one under `options`; typed API results and authorization; tests for those contracts.

**Out of scope:** Frontend completion, inspection, stale-response handling, replacement, conflict annotations, saved-project reference errors, legacy `+` expression editing, changes to `/valid-directives`, and changes to stage-aware ordinary column suggestions. A legacy expression may occur inside a requested dependency and must follow existing resolution order, but it is not a completion choice or a direct inspection target in this phase.

**Affected contracts:** Two new POST read endpoints under `/api/v1/projects/{project_name}/entities/{entity_name}/column-references/`; `ProjectMapper.to_core()` gains an optional editor-reference argument while existing calls retain full conversion. The API keeps raw directive strings and returns columns only after the mapper checks the requested path. No migration or stored-format change is needed.

## Work Breakdown

### Area 1: Resolve one path through the mapper

**Objective:** One requested path resolves from a copied project with ordered values, while unrelated configuration stays untouched.

**Affected code:** `src/configuration/resolve.py::ResolutionContext`, `resolve_directives`, `ReferenceResolver`; `backend/app/mappers/project_mapper.py::ProjectMapper.to_core`; `tests/configuration/test_requested_reference.py` (`NEW`); `backend/tests/mappers/test_project_mapper_requested_reference.py` (`NEW`).

**Dependencies:** Phase 1's confirmed field set; no other Phase 2 area.

**Tasks**

* [x] `T1.1` **Implement:** Add a scoped reference resolver that follows only the requested path and its dependencies.
  * **Target:** `src/configuration/resolve.py` (new scoped helper and typed failure); `tests/configuration/test_requested_reference.py` (`NEW`).
  * **Current → required:** `resolve_directives` walks the whole tree and `ReferenceResolver` can leave a missing path raw or skip a missing expression operand → a requested lookup either resolves completely or reports a classified missing, circular, or dependency failure.
  * **Implementation:** Accept the raw configuration and one complete path; work on a copy. Traverse path segments with the existing supported dotted-path behavior, track visited reference paths for cycles, and resolve only reached `@include`, `@load`, environment, and `@value` values. Reuse the existing list flattening and expression ordering rules for reached values. Detect missing operands and residual directives in the requested dependency chain; return no partial value. Use the existing `ResolutionContext` settings, allowed roots, and allowed variables for any reached file or environment directive. Keep the existing full `resolve_directives` entry point and results unchanged.
  * **Constraints:** An unrelated bad `@value`, missing file, or cycle is not read. Do not convert a dependency failure into a guessed or shortened list; do not bypass path confinement.
  * **Validation:** `V-1`: a direct list, nested chain, list-item flattening, and supported expression dependency preserve order; requested missing/circular/file failures are local; unrelated failures do not matter; the input remains unchanged.

* [x] `T1.2` **Update:** Expose the scoped resolver as an editor-only mode of `ProjectMapper.to_core()`.
  * **Target:** `backend/app/mappers/project_mapper.py::ProjectMapper.to_core`; `backend/tests/mappers/test_project_mapper_requested_reference.py` (`NEW`).
  * **Current → required:** Every `to_core()` call transforms and resolves the full project and validates its sidecar → an optional requested path produces a read-only `ShapeShiftProject` with that value resolved while unrelated values may remain raw. Calls without the option continue through the current full path.
  * **Implementation:** Add a keyword-only requested-path argument. Build the same raw Core dict via `to_core_dict`, pass the current project filename, project-root fallback, shared allowed roots, env prefix/file, and allowed variables to the scoped helper, and replace only the selected value in the copied dict. Keep editor-only output separate from execution callers; skip whole-project entity transformation and sidecar validation in this branch because neither is required to inspect a column-list property. Keep the default branch unchanged.
  * **Constraints:** Do not mutate the supplied `Project` or saved data. A reached file directive uses the same confinement rules as full conversion. Do not call the full-project resolver as a fallback after a scoped failure.
  * **Validation:** `V-2`: editor mode resolves the requested path despite unrelated invalid content, preserves the project and raw source, and applies allowed-root rules; default `to_core()` still resolves valid references and raises its existing errors for invalid full conversion.

**Completion evidence:** A mapper call for `entities.child.keys` resolves a draft-dependent list with original order while a missing or cyclic reference elsewhere remains raw and causes no failure.

### Area 2: Check full paths and produce filtered choices

**Objective:** Backend logic shares one typed list check between direct inspection and completion, evaluating each candidate independently.

**Affected code:** `backend/app/services/column_reference_service.py` (`NEW`); `backend/tests/services/test_column_reference_service.py` (`NEW`); existing `ProjectService.load_project`, `Project.model_copy`.

**Dependencies:** Area 1.

**Tasks**

* [x] `T2.1` **Implement:** Resolve a complete simple `@value:` directive against the submitted entity draft.
  * **Target:** `backend/app/services/column_reference_service.py` (`NEW`); `backend/tests/services/test_column_reference_service.py` (`NEW`).
  * **Current → required:** `DirectiveValidator.validate_directive` returns a raw value from the saved project → a draft-aware check returns either `resolved` with ordered `columns: list[str]` or `unresolved` with the original path, a stable reason code, and a plain-language reason.
  * **Implementation:** Load with `ProjectService.load_project`, deep-copy the API model, replace `entities[entity_name]` with `entity_draft`, and call `ProjectMapper.to_core()` in editor mode for the requested simple path. Require an actual list whose every item is a string; keep order and duplicates, and accept an empty list as a valid list result. Distinguish malformed input, missing path, cycle, dependency failure, and wrong result type. A failed check has no `columns` result. Accept a full manually entered supported path even when completion does not suggest it.
  * **Constraints:** Preserve raw directive text; never save the draft. Do not expose an exception traceback or partial data in a failed result. Direct legacy `+` expressions are outside the simple-reference result contract.
  * **Validation:** `V-3`: changed draft values supersede saved values; nested and mixed lists keep order; scalar, non-string-list, missing, cyclic, and malformed inputs return local reasons; `options` paths can be checked manually; the loaded model remains unchanged.

* [x] `T2.2` **Implement:** Complete entity and property prefixes using independent requested-path checks.
  * **Target:** `backend/app/services/column_reference_service.py` (`NEW`); `backend/tests/services/test_column_reference_service.py` (`NEW`).
  * **Current → required:** `/valid-directives` offers untyped project-wide paths → completion offers progressively filtered `@value: entities.<name>.<property>` choices only when the property resolves to a string list.
  * **Implementation:** Parse the typed `@value` prefix, narrow entity names and property names before resolving property candidates, then call `T2.1` for each remaining complete property path. Return stable full directive strings for root, entity, and eligible property stages. Exclude the exact edited-field path when supplied; use an optional preferred entity to order relevant FK choices first while retaining other valid entities. Skip each failed or wrong-type property independently. Do not scan `options` or other arbitrary paths for suggestions; direct validation still accepts them.
  * **Constraints:** Do not interpret directives in the UI, call `/valid-directives`, or turn incomplete source-column candidates into hard errors. A broken property in one entity cannot suppress another entity's valid choice.
  * **Validation:** `V-3`: prefixes progressively narrow results; `keys` and `columns` appear when eligible; `public_id`, dict, mixed-type lists, self-reference, and broken properties do not; a preferred entity leads without hiding other matches.

**Completion evidence:** Completion returns a valid property from the draft after excluding an unrelated cyclic or missing property, and the same full path passes the direct check with ordered columns.

### Area 3: Publish authorized read contracts and regressions

**Objective:** Authorized HTTP callers can request completion and one-reference resolution without changing the saved project.

**Affected code:** `backend/app/models/column_reference.py` (`NEW`); `backend/app/api/v1/endpoints/column_references.py` (`NEW`); `backend/app/api/v1/api.py`; `backend/tests/api/v1/test_column_references.py` (`NEW`); `backend/tests/authorization/test_cross_resource_access.py`.

**Dependencies:** Areas 1 and 2.

**Tasks**

* [x] `T3.1` **Implement:** Add typed completion and resolution POST endpoints.
  * **Target:** `backend/app/models/column_reference.py` (`NEW`); `backend/app/api/v1/endpoints/column_references.py` (`NEW`); `backend/app/api/v1/api.py::api_router`.
  * **Current → required:** No draft-aware reference HTTP contract exists → `POST /projects/{project_name}/entities/{entity_name}/column-references/resolve` accepts `entity_draft` and `directive`, and `POST .../column-references/complete` accepts `entity_draft`, `prefix`, optional `edited_field_path`, and optional `preferred_entity`.
  * **Implementation:** Define Pydantic request/response models in `backend/app/models/column_reference.py`: resolution includes the requested directive/path, `resolved` or `unresolved` status, ordered columns only on success, and a stable reason code/message only on failure; completion returns full candidate directive strings. Apply `require_project(Action.READ)` on both routes, pass `authorized_project.resource.locator` to the service, and register the router. Return a local unresolved result for a bad requested reference; retain normal 404 for inaccessible/missing projects and normal request-model errors for invalid bodies.
  * **Constraints:** These POST methods are read-only. Keep the existing `/validate-directive`, `/valid-directives`, and `/column-availability` routes and response shapes intact.
  * **Validation:** `V-4`: both routes return typed responses, preserve a draft-only change, and reject inaccessible projects before loading their contents.

* [x] `T3.2` **Test:** Lock in draft isolation, authorization, and full-conversion parity at HTTP and mapper levels.
  * **Target:** `backend/tests/api/v1/test_column_references.py` (`NEW`); `backend/tests/authorization/test_cross_resource_access.py::test_authenticated_principal_cannot_cross_user_resource_boundaries`; `backend/tests/mappers/test_project_mapper_requested_reference.py` (`NEW`); generated `graphify-out/graph.json` if the required update changes it.
  * **Current → required:** Existing route tests cover column availability and other protected resources → new tests cover both reference routes and the optional mapper mode without weakening those contracts.
  * **Implementation:** Create an authorized project through `POST /api/v1/projects`, submit a changed child draft, query completion and resolution, then GET the saved entity and assert it is unchanged. Add both POST routes to the cross-resource denial cases and assert concealed 404 responses. Compare default `to_core()` output and failure behavior with the existing mapper tests, including a valid nested reference and an unrelated broken reference. Refresh Graphify after the code changes and review generated-file changes.
  * **Constraints:** Use the async `authorized_client` fixture for protected route tests. Do not write a project YAML directly as the way to register a resource.
  * **Validation:** `V-2`, `V-4`, `V-6`: focused tests, existing API/auth regressions, and the broader backend/Core suite.

**Completion evidence:** The two routes return draft-derived results for authorized readers; denied readers receive 404; a subsequent GET returns the original saved entity; default full conversion is unchanged.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
| --- | --- | --- | --- |
| `PH2-AC-1` (from `P-AC-3`) | `T1.1`, `T1.2`, `T2.1`, `T3.2` | `V-1`, `V-2`, `V-3`, `V-4` | Ordered draft columns or a local unresolved reason; unrelated missing/circular/file failures do not block valid resolution. |
| `PH2-AC-2` (from `P-AC-2`) | `T2.1`, `T2.2`, `T3.1` | `V-3`, `V-4` | Filtered eligible properties and independently checked manual full paths, without `/valid-directives`. |
| `PH2-AC-3` (from `P-AC-7`) | `T1.2`, `T2.1`, `T3.1`, `T3.2` | `V-2`, `V-3`, `V-4`, `V-6` | Read authorization, unchanged saved project, and unchanged normal full conversion. |

## Validation And Testing

Run commands from the repository root. The planning baseline covered existing tests; execution outcomes for all planned checks are recorded below. `V-1`–`V-4` fulfill `VM-2`.

| ID | Check and target | Command or method | Covers | Expected result | Baseline | Execution result |
| --- | --- | --- | --- | --- | --- | --- |
| `V-1` | Scoped resolver cases in `tests/configuration/test_requested_reference.py` (`NEW`), plus existing resolver and confinement cases | `rtk uv run pytest -p no:cacheprovider tests/configuration/test_requested_reference.py tests/configuration/test_utility.py tests/configuration/test_directive_path_confinement.py -q` | `PH2-AC-1`, `VM-2` | Direct, nested, mixed-list, and expression-dependency order passes; requested missing/circular/unresolved/file failures return no partial result; unrelated failures are ignored; file-root confinement and input immutability hold. | Not run for `NEW` file; existing resolver/confinement tests passed in focused baseline. | Pass: 26 tests. |
| `V-2` | Mapper mode and default behavior in `backend/tests/mappers/test_project_mapper_requested_reference.py` (`NEW`) and existing mapper tests | `rtk uv run pytest -p no:cacheprovider backend/tests/mappers/test_project_mapper_requested_reference.py backend/tests/mappers/test_config_mapper.py backend/tests/mappers/test_project_mapper_file_path_integration.py -q` | `PH2-AC-1`, `PH2-AC-3`, `VM-2` | Editor mode isolates the request and preserves allowed roots; default conversion, file mapping, and sidecar behavior retain their current results. | Not run for `NEW` file; existing mapper tests passed in the focused baselines. | Pass: 46 tests. |
| `V-3` | Service results in `backend/tests/services/test_column_reference_service.py` (`NEW`) | `rtk uv run pytest -p no:cacheprovider backend/tests/services/test_column_reference_service.py -q` | `PH2-AC-1`, `PH2-AC-2`, `PH2-AC-3`, `VM-2` | Draft overrides saved values; wrong types and failed dependencies give local reasons; prefixes and edited-field exclusion filter choices; manual supported paths work; loaded project is unchanged. | Not run: test file is planned `NEW`. | Pass: 10 tests. |
| `V-4` | New routes, existing column route, and project authorization | `rtk uv run pytest -p no:cacheprovider backend/tests/api/v1/test_column_references.py backend/tests/api/v1/test_columns.py backend/tests/authorization/test_cross_resource_access.py -q` | `PH2-AC-1`–`PH2-AC-3`, `VM-2` | Authorized completion and resolution return draft-derived JSON; saved entity stays unchanged; missing or denied project returns 404; existing column API remains compatible. | Not run for `NEW` file; existing column and cross-resource tests passed in focused baselines. | Pass: 10 tests. |
| `V-5` | Python formatting and lint for changed areas | `rtk uv run ruff check src/configuration/resolve.py backend/app backend/tests tests/configuration/test_requested_reference.py`; `rtk uv run black --check src/configuration/resolve.py backend/app backend/tests tests/configuration/test_requested_reference.py`; `rtk uv run isort --check-only src/configuration/resolve.py backend/app backend/tests tests/configuration/test_requested_reference.py` | Changed Python files | No new lint, formatting, or import-order errors. | Focused Ruff check passed on the existing affected application files; Black and isort not run during planning. | Pass: Ruff, Black, and isort. |
| `V-6` | Backend/Core regression suite and generated graph refresh | `rtk uv run pytest -p no:cacheprovider tests/configuration backend/tests -q`; after code changes, `GRAPHIFY_VIZ_NODE_LIMIT=0 ~/.local/bin/graphify update .` | Existing behavior and repository graph rule | Tests pass; Graphify update succeeds and its changed generated files are reviewed. | Not run: focused baselines were proportionate for planning; no code was changed, so no graph update was needed. | Suite has 3 baseline Arbodat failures; Graphify update succeeded. See execution note below. |

**Execution note:** `V-6` failed the three existing Arbodat tests `test_composite_project_specification_is_satisfied_by`, `test_data_validation_orchestrator`, and `test_access_database_csv_workflow`. The same three test IDs failed at starting commit `1b929e5e` in a detached worktree; the first reported the same missing `site_location` value columns (`Kreis`, `Land`, `Ort`, and `Staat`). The failures come from the Arbodat fixture/data path and are outside this phase. The graph update completed without extraction-loss warnings. It refreshed `graphify-out/graph.json`, `GRAPH_REPORT.md`, the callflow HTML, and label metadata. The route inventory document was updated because it requires synchronization when API routes change; its parity check passes.

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Requested-path resolver and local failures | `src/configuration/resolve.py` | `T1.1` | Only visited dependencies resolve; full resolver still behaves as before. |
| Scoped resolver tests (`NEW`) | `tests/configuration/test_requested_reference.py` | `T1.1` | `V-1` passes with order, isolation, failure, and confinement cases. |
| Editor-only mapper mode | `backend/app/mappers/project_mapper.py` | `T1.2` | `V-2` proves optional scope and default-path parity. |
| Mapper contract tests (`NEW`) | `backend/tests/mappers/test_project_mapper_requested_reference.py` | `T1.2`, `T3.2` | Draft-independent scope and normal conversion cases pass. |
| Draft-aware reference service (`NEW`) | `backend/app/services/column_reference_service.py` | `T2.1`, `T2.2` | Direct checks and filtered candidates share one list-type rule. |
| Service tests (`NEW`) | `backend/tests/services/test_column_reference_service.py` | `T2.1`, `T2.2` | `V-3` passes for full paths, prefixes, independent failures, and no mutation. |
| Request/response models (`NEW`) | `backend/app/models/column_reference.py` | `T3.1` | Typed success, unresolved, and completion schemas appear in OpenAPI. |
| Authorized route module (`NEW`) | `backend/app/api/v1/endpoints/column_references.py` | `T3.1` | Both POST routes enforce project read access. |
| Router registration | `backend/app/api/v1/api.py` | `T3.1` | Both routes are reachable under `/api/v1`. |
| Route contract tests (`NEW`) | `backend/tests/api/v1/test_column_references.py` | `T3.2` | `V-4` proves JSON contract and saved-project isolation. |
| Cross-resource denial coverage | `backend/tests/authorization/test_cross_resource_access.py` | `T3.2` | Both routes conceal unauthorized projects with 404. |
| Generated graph index, if changed by the required update | `graphify-out/graph.json` | `T3.2` | Graphify update succeeds; generated output changes are reviewed. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Requested path through mapper | Done | Phase 1 complete | `T1.1`–`T1.2` complete; `V-1` and `V-2` pass. |
| Area 2: Full path and choices | Done | Area 1 | `T2.1`–`T2.2` complete; `V-3` passes. |
| Area 3: Authorized HTTP contracts | Done | Areas 1–2 | `T3.1`–`T3.2` complete; `V-4` and route inventory parity pass. `V-6` reproduces the same three Arbodat failures at baseline commit. |

## Definition Of Done

* [x] `PH2-AC-1`–`PH2-AC-3` each have passing task and validation results for `VM-2`.
* [x] Areas 1–3 and every required deliverable are complete; the generated graph is refreshed after code changes.
* [x] `V-1`–`V-6` pass, or any pre-existing quality failure is recorded with a before/after comparison.
* [x] Ordered values, nested dependencies, missing/circular paths, wrong types, allowed file roots, and unrelated-failure isolation are covered by regression tests.
* [x] Both routes require project read access, the submitted draft is not persisted, and default full conversion keeps its existing behavior.
* [x] API schemas and the generated graph match the implementation; no stored-format or migration change is introduced.
* [x] Deviations and follow-up work are recorded, and no unresolved question affects implementation or validation.

If implementation finds a repository contract that conflicts with this verified plan, stop and report the source and test result before changing the design or expanding scope.

## Risks And Open Questions

The current full resolver can leave missing simple paths raw and can skip a missing legacy-expression operand. The scoped helper must detect those cases in reached dependencies while preserving default full-project behavior. A cyclic requested dependency must stop through explicit visited-path tracking; an unrelated cycle must never be traversed. These are implementation risks covered by `V-1` and `V-2`, not open design decisions.
