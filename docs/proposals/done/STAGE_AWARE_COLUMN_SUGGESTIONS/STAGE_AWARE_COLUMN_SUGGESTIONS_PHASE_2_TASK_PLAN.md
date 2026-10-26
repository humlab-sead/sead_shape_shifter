# Phase 2 Task Plan: Draft-Aware Backend Endpoint

## Phase Summary

**Goal:** Expose the Phase 1 resolver through a protected endpoint that evaluates the submitted unsaved entity draft and returns operation-specific column candidates using selected FK parents' processed output.

**Readiness:** Validated. Phase 2 is marked ready in the [phase plan](STAGE_AWARE_COLUMN_SUGGESTIONS_PHASE_PLAN.md), and its Phase 1 dependency is present in the working tree. No unresolved decision changes the endpoint behavior or validation method.

**Dependencies and constraints:** Use `src/column_availability.py::resolve_column_availability` for stage semantics. Convert API projects with `ProjectMapper.to_core()`. Keep the existing GET route and `ColumnIntrospectionService` behavior unchanged. Suggestions remain advisory; do not read sources or execute loaders or queries.

**Source documents:** [proposal](STAGE_AWARE_COLUMN_SUGGESTIONS.md), [phase plan](STAGE_AWARE_COLUMN_SUGGESTIONS_PHASE_PLAN.md), and [Phase 1 task plan](STAGE_AWARE_COLUMN_SUGGESTIONS_PHASE_1_TASK_PLAN.md).

**Phase acceptance criteria**

1. `PH2-AC-1` (from `P-AC-4`): The endpoint evaluates the submitted unsaved entity draft. FK local candidates reflect link position, and remote-key and extra-column source candidates use the selected parent's processed output.
2. `PH2-AC-2` (from `P-AC-3`, `P-AC-7`): The response includes operation-specific and filter-stage candidates and uses current unnest results, not legacy unnest artifacts.

## Repository Findings

**Repository basis:** Branch `stage-aware-column-suggestions`, commit `723bef65`, planning date 2026-10-07. Pre-existing staged Phase 1 additions were considered and left untouched. The Phase 2 task-plan target did not exist.

| Evidence | Finding | Planning implication |
| --- | --- | --- |
| `src/column_availability.py::resolve_column_availability` | Returns operation-keyed candidates, filter-stage candidates, per-FK local and remote candidates, extra-column sources, and current `unnest.id_vars`/`unnest.value_vars`. It accepts `source_columns` and `processed_parent_columns`. | Adapt the resolver's result rather than reimplementing stage rules or flattening results. |
| `src/column_availability.py::_processed_entity_columns` | Uses a parent's final target-facing columns and adds its generated `system_id`; a supplied processed-parent mapping can override the known output columns. | Resolve selected parent outputs through the core resolver, then pass those outputs to the child resolver. |
| `backend/app/api/v1/endpoints/columns.py::get_available_columns` | The existing protected GET returns flat `ColumnAvailability` categories using the saved project and legacy unnest extraction. | Add a sibling POST route; do not alter the GET response or its service. |
| `backend/app/api/v1/api.py::api_router` | `columns.router` is already registered. | No router-registration change is needed. |
| `backend/app/services/project_service.py::ProjectService.load_project` | Loads the saved API `Project` by project name. | Start with the saved project, deep-copy it, and replace the requested entity with the submitted draft. |
| `backend/app/mappers/project_mapper.py::ProjectMapper.to_core` | Converts an API `Project` into `ShapeShiftProject` and resolves mapper-owned paths and directives. | Use this mapper for the copied draft project; do not construct a core project directly in the backend service. |
| `backend/app/models/project.py::Project` | Stores entities as `dict[str, dict[str, Any]]`; it is a Pydantic model. | Keep the request draft flexible and avoid mutating the service's loaded project. |
| `backend/tests/conftest.py::authorized_client` and `backend/tests/api/v1/test_entities.py` | Protected API tests use `authorized_client`; project setup uses `POST /api/v1/projects` and awaits each request. | Follow the existing async API test pattern and create projects through the API. |

**Baseline results**

- `rtk uv run pytest backend/tests/services/test_column_introspection_service.py backend/tests/api/v1/test_entities.py -q -o addopts=`: 41 passed.

## Scope

**In scope**

- Add typed request and response models for the draft-aware POST endpoint.
- Add a backend service that deep-copies the loaded API project, substitutes the submitted draft, maps it to core, and calls the Phase 1 resolver.
- Supply processed output candidates for the parent entities selected in the submitted draft's foreign keys.
- Add the sibling POST route in `columns.py`, protected by the existing project-read authorization dependency.
- Add focused service and endpoint tests, including a legacy GET contract regression test.

**Out of scope**

- Changing the existing GET route, its response, or `ColumnIntrospectionService`.
- Frontend composables, debouncing, or editor control changes; those belong to Phase 3.
- Runtime availability guarantees, validation changes, source inspection, loader execution, and query execution.
- Changing core operation semantics or the normalization pipeline.

## Work Breakdown

### Area 1: Add The Draft-Aware API And Service

**Objective:** Return the core resolver's operation-specific result for a copied project containing the current entity draft and selected parent outputs.

**Affected code:** `backend/app/models/column_availability.py` (NEW); `backend/app/services/stage_aware_column_service.py` (NEW); `backend/app/api/v1/endpoints/columns.py`.

**Dependencies:** Phase 1 resolver and tests.

**Tasks:**

* [x] `T2.1` **Change:** Define typed request and response models for the endpoint.
  * **Target:** `backend/app/models/column_availability.py` (NEW); result contract in `src/column_availability.py::resolve_column_availability`.
  * **Current → required:** The backend has no request or response model for operation-specific suggestions. Define a request with `entity_draft: dict[str, Any]` and optional known `source_columns`; take selected parent names from the draft's current FK targets. Define response fields matching the resolver result: operation lists, `extra_columns.sources`, stage-keyed `filters`, per-FK results, and `unnest.id_vars`/`unnest.value_vars`.
  * **Implementation:** Use Pydantic models for the nested FK, unnest, extra-column, and response shapes. Preserve the resolver's field names and optional metadata; do not expose a flattened stage union.
  * **Constraints:** Do not make candidate fields required for editing or validation. Use the current resolver-provided `unnest.id_vars` and `unnest.value_vars`; do not derive unnest candidates from the legacy `value_column` convention.
  * **Validation:** `V-2` and `V-4`.
* [x] `T2.2` **Change:** Implement service orchestration for a draft and its selected parents.
  * **Target:** `backend/app/services/stage_aware_column_service.py` (NEW); `ProjectService.load_project`; `ProjectMapper.to_core`; `src/column_availability.py::resolve_column_availability`.
  * **Current → required:** The legacy service analyzes only the saved project. The new service must use the request's current entity draft without changing the saved or cached project.
  * **Implementation:** Load the project using the authorized resource locator, make a deep copy, replace the named entity with `entity_draft`, and convert the copy with `ProjectMapper.to_core()`. For each existing parent selected by the draft's foreign keys, call the resolver for that parent and collect its final `drop_empty_rows` candidates. Pass that mapping and any supplied `source_columns` to the resolver for the draft entity. Leave missing parent output unknown rather than inventing candidates.
  * **Constraints:** Do not mutate the loaded project. Do not duplicate operation or stage rules in the backend. Preserve advisory behavior when source metadata is absent or incomplete.
  * **Validation:** `V-1` and `V-4`.
* [x] `T2.3` **Change:** Add the protected sibling POST route and preserve the legacy GET route.
  * **Target:** `backend/app/api/v1/endpoints/columns.py::router`; existing `get_available_columns`.
  * **Current → required:** The router exposes only the protected GET route. Add `POST /projects/{project_name}/entities/{entity_name}/column-availability` and return the typed response from the new service.
  * **Implementation:** Use `require_project(Action.READ)` and the authorized resource locator, consistent with the existing route. Apply `handle_endpoint_errors` so `ResourceNotFoundError` maps to 404 and domain validation errors map to 400. Leave GET dependencies, service calls, and response model unchanged.
  * **Constraints:** Do not add a request body to GET or change router registration; `columns.router` is already included by `api.py`.
  * **Validation:** `V-2`, `V-3`, and `V-4`.

**Completion evidence:** The POST response validates against the typed contract, reflects the submitted draft and selected parent outputs, and the GET route retains its existing flat response.

### Area 2: Test Endpoint Behavior And Compatibility

**Objective:** Verify draft sensitivity, parent output, operation-specific results, and the unchanged legacy route.

**Affected code:** `backend/tests/services/test_stage_aware_column_service.py` (NEW); `backend/tests/api/v1/test_columns.py` (NEW); fixtures in `backend/tests/conftest.py::authorized_client`.

**Dependencies:** Area 1.

**Tasks:**

* [x] `T2.4` **Change:** Test service mapping, copy behavior, draft sensitivity, and selected parent results.
  * **Target:** `backend/tests/services/test_stage_aware_column_service.py` (NEW); `StageAwareColumnService` (NEW).
  * **Current → required:** Existing service tests cover only legacy flat introspection. Add focused tests for the new resolver adapter.
  * **Implementation:** Use a saved project fixture and a differing submitted draft; assert returned candidates reflect the draft and the loaded project remains unchanged. Include a parent with a derived processed column and assert that its processed output and generated `system_id` are available in the child's FK remote-key and extra-column source candidates. Cover an unknown parent or absent source metadata as incomplete advisory results.
  * **Constraints:** Exercise the real `ProjectMapper.to_core()` path with deterministic inline configuration; do not use database, loader, or source-file access.
  * **Validation:** `V-1` and `V-4`.
* [x] `T2.5` **Change:** Test the protected endpoint contract and legacy GET compatibility.
  * **Target:** `backend/tests/api/v1/test_columns.py` (NEW); `columns.router`.
  * **Current → required:** There are no column-route API tests. Verify that the new POST returns typed operation results for the current request while the saved project remains unchanged.
  * **Implementation:** Use `authorized_client`, create the project through `POST /api/v1/projects`, and await every request. Cover a changed unsaved draft; selected parent remote keys and extra-column sources; filter-stage fields; current `id_vars`/`value_vars` behavior with no synthetic `value_id`; a missing-project response; and the existing GET's flat category keys and status.
  * **Constraints:** Do not change existing route behavior to make the new test pass. Keep field suggestions advisory and do not add frontend tests in this phase.
  * **Validation:** `V-2`, `V-3`, and `V-4`.

**Completion evidence:** Focused service and API tests demonstrate both phase criteria, and the GET regression assertions pass alongside them.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
| --- | --- | --- | --- |
| `PH2-AC-1` (from `P-AC-4`) | `T2.1`, `T2.2`, `T2.3`, `T2.4`, `T2.5` | `V-1`, `V-2` | POST uses the submitted draft; FK local candidates retain resolver link order; selected parents' processed output supplies remote-key and extra-column source candidates. |
| `PH2-AC-2` (from `P-AC-3`, `P-AC-7`) | `T2.1`, `T2.3`, `T2.5` | `V-2`, `V-3` | Typed response includes operation and filter-stage fields, uses current unnest candidate lists, and omits legacy artifacts. |

## Validation And Testing

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
| --- | --- | --- | --- | --- | --- |
| `V-1` | New service tests in `backend/tests/services/test_stage_aware_column_service.py` (NEW) | `uv run pytest backend/tests/services/test_stage_aware_column_service.py -q` | `PH2-AC-1` | Draft replacement does not mutate the loaded project; selected parent processed output reaches FK remote-key and extra-column source candidates; incomplete metadata stays advisory. | Pass: 2 passed. |
| `V-2` | New endpoint tests in `backend/tests/api/v1/test_columns.py` (NEW) | `uv run pytest backend/tests/api/v1/test_columns.py -q` | `PH2-AC-1`, `PH2-AC-2` | Authorized POST returns draft-sensitive operation, filter, FK, and current unnest results; a missing project returns 404. | Pass: 2 POST tests passed. |
| `V-3` | GET contract assertions in the new endpoint tests | Included in `uv run pytest backend/tests/api/v1/test_columns.py -q` | Existing GET behavior; `PH2-AC-2` | Existing GET remains protected and returns the legacy flat categories without contract changes. | Pass: legacy GET contract test passed. |
| `V-4` | Lint and formatting checks on changed/new Python files | `uv run ruff check backend/app/api/v1/endpoints/columns.py backend/app/models/column_availability.py backend/app/services/stage_aware_column_service.py backend/tests/services/test_stage_aware_column_service.py backend/tests/api/v1/test_columns.py`<br>`uv run black --check backend/app/api/v1/endpoints/columns.py backend/app/models/column_availability.py backend/app/services/stage_aware_column_service.py backend/tests/services/test_stage_aware_column_service.py backend/tests/api/v1/test_columns.py`<br>`uv run isort --check-only backend/app/api/v1/endpoints/columns.py backend/app/models/column_availability.py backend/app/services/stage_aware_column_service.py backend/tests/services/test_stage_aware_column_service.py backend/tests/api/v1/test_columns.py` | `PH2-AC-1`, `PH2-AC-2` | All targeted checks pass without reformatting unrelated files. | Pass: Ruff, Black, and isort checks passed. |
| `V-5` | Existing legacy service and entity API regressions | `uv run pytest backend/tests/services/test_column_introspection_service.py backend/tests/api/v1/test_entities.py -q -o addopts=` | Existing project/entity behavior | Existing tests pass; legacy introspection remains compatible. | Pass: 41 passed. |

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Typed request and response models | `backend/app/models/column_availability.py` (NEW) | `T2.1` | Models represent the resolver's unflattened operation, filter, FK, and unnest result. |
| Draft-aware resolver adapter | `backend/app/services/stage_aware_column_service.py` (NEW) | `T2.2` | Service maps a copied draft project and supplies selected parent processed output to the core resolver. |
| Protected draft-aware endpoint | `backend/app/api/v1/endpoints/columns.py` | `T2.3` | Sibling POST is available and the existing GET contract is unchanged. |
| Service behavior tests | `backend/tests/services/test_stage_aware_column_service.py` (NEW) | `T2.4` | Tests verify draft replacement, no mutation, selected parent outputs, and incomplete metadata. |
| Endpoint and compatibility tests | `backend/tests/api/v1/test_columns.py` (NEW) | `T2.5` | Tests cover endpoint results, errors, and legacy GET response shape. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Add The Draft-Aware API And Service | Done | Phase 1 | Preserve the legacy GET and use the existing registered columns router. |
| Area 2: Test Endpoint Behavior And Compatibility | Done | Area 1 | Use `authorized_client` and API-created projects for protected-route tests. |

## Definition Of Done

- [x] `PH2-AC-1` and `PH2-AC-2` each have implementation and validation evidence.
- [x] Request and response models match the operation-aware resolver contract without flattening results.
- [x] The endpoint uses a copied project with the submitted draft and the selected parents' processed output.
- [x] The loaded project remains unchanged, and unknown candidate metadata remains advisory.
- [x] The legacy GET route behavior and response are regression-tested and unchanged.
- [x] Targeted service, endpoint, lint, and formatting checks pass.
- [x] No frontend, core pipeline, or validation behavior was added to Phase 2.
- [x] Deviations and follow-up work are documented; no unresolved question affects implementation or validation.

## Risks And Open Questions

- Parent source metadata can be incomplete. The endpoint must return only derivable candidates and preserve the core resolver's advisory semantics; validation and execution remain authoritative.
- No blocking questions remain. The entity draft's FK targets identify the selected parents, and the existing core resolver accepts their processed output through `processed_parent_columns`.