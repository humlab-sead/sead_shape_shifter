# Target Model Guided Entity Creation — Phase 1 Task Plan

## Phase Summary

- **Phase:** 1 — Authorized Target Options
- **Goal:** Give the Add Entity form a project-scoped, read-authorized list of missing target entities and their requirements.
- **Readiness:** Validated. The phase plan marks Phase 1 ready, the targets and test patterns below exist, and no product decision remains open.

Sources: [proposal](TARGET_MODEL_GUIDED_ENTITY_CREATION.md) and [phase plan](TARGET_MODEL_GUIDED_ENTITY_CREATION_PHASE_PLAN.md), Phase 1. The phase's `VM-1` milestone is covered by `V-1` through `V-4` below.

**Constraints and dependencies:** Use the project's associated model through `ProjectMapper.to_core()` and authorize the project before loading it. Keep target requirements out of project entity fields. This phase provides a read contract only; Phases 2 and 3 consume it.

**Acceptance criteria**

1. [ ] `PH1-AC-1` (from `P-AC-1`): Return every target-model entity absent from the project with its role and required status.
2. [ ] `PH1-AC-2` (from `P-AC-2`): Distinguish no configured model from a model load or parse failure without changing the project.
3. [ ] `PH1-AC-3` (from `P-AC-8`): Exclude generated columns from required source work and represent `via` links as bridge paths.

## Repository Findings

**Repository basis:** Branch `change-request-target-bundle-access`, commit `78f3c16c`, inspected 2026-10-20. The current uncommitted proposal and phase plan were treated as the source documents. Unrelated dirty implementation files and the separate change-request task plan were not used as implementation targets.

| Verified source | Current behavior | Planning implication |
| --- | --- | --- |
| `backend/app/models/project.py::ProjectMetadata`, `Project` | `target_model` is an inline dict, reference string, or `None`; project entities are keyed by name. `TargetModelFileOption` lists files, not model entities. | Add separate response models for target entity options; compare target names with project entity keys. |
| `backend/app/api/v1/endpoints/projects.py::list_project_target_models`, `get_project_target_model_yaml` | Project routes use `require_project(Action.READ)`. The file list offers model references; the raw YAML route handles project-local files only. | Add a distinct GET route for entity options. Do not reuse the raw YAML or file-list response. The projects router is already registered in `backend/app/api/v1/api.py`. |
| `backend/app/mappers/project_mapper.py::ProjectMapper.to_core` | Resolves directives and approved local/shared model paths when converting an API project to Core. | Resolve the associated model here; do not accept a model path in the request or resolve directives in the route. |
| `src/target_model/models.py::TargetModel`, `EntitySpec`, `ColumnSpec`, `ForeignKeySpec` | The model declares role, required status, `public_id`, required/generated columns, and required FK links with optional `via`. | Project only declared target facts. A `via` link needs a two-name path after the selected entity. |
| `src/target_model/spec_validator.py::TargetModelSpecValidator.validate` | Checks target-model consistency after Pydantic parsing. | Reject an invalid configured spec before returning picker options; do not run project conformance to build the list. |
| `backend/app/services/validation_service.py::validate_target_model` | A missing referenced file is silently treated as no model for conformance validation. | The new operation must retain its own explicit error result for a configured missing file. Do not change conformance behavior in this phase. |
| `backend/app/utils/error_handlers.py::handle_endpoint_errors` | Converts `BadRequestError` to HTTP 400 with a safe generic public detail. | Use that existing error path for configured model failures. Phase 2 can display a clear picker message from the failed request; do not expose paths or parser contents. |
| `backend/tests/conftest.py::authorized_client`; `backend/tests/authorization/test_cross_resource_access.py` | Protected route tests use an async authenticated client; cross-user project reads return concealed 404. | Create test projects through POST and verify the new route has the same authorization behavior. |

## Scope

**In scope:** Response models, a backend read service, one project GET route, focused service and route tests, and an authorization regression case. The response contains `configured`, missing target-entity options, identity facts, and requirement facts. The request contains only the authorized project name.

**Out of scope:** Frontend picker and form behavior, entity creation or updates, target-model editing, conformance changes, template generator changes, CLI changes, and a browser-supplied model path.

**Contract to implement:** Proposed `GET /api/v1/projects/{name}/target-model-entities` returns HTTP 200 with `{configured: false, entities: []}` only when `metadata.target_model` is absent (`None`). A configured, valid model returns `{configured: true, entities: [...]}`; the list can be empty. A configured model that cannot be resolved, parsed, or passes parsing but fails spec validation returns HTTP 400 through the existing endpoint error handler. Each option has `name`, nullable `role`, `required`, nullable `description`, `target_table`, and `public_id`, plus `required_columns: list[str]` and `required_links: list[{path: list[str], missing_entities: list[str]}]`. A direct link path is `[target]`; a `via` link path is `[bridge, target]`. Paths start after the option's own entity. `missing_entities` contains path members absent from the project. Return only unconditional `required: true` links; `required_when` does not make a link unconditionally required. Sort options by required first, then name; sort column and link lists for stable responses.

## Work Breakdown

### Area 1: Define the target-options response

**Objective:** A typed response keeps target requirements separate from project entity configuration.

**Affected code:** `backend/app/models/project.py` (existing file; proposed `TargetModelRequiredLink`, `TargetModelEntityOption`, `TargetModelEntityOptionsResponse` classes are **NEW**).

**Dependencies:** None.

**Tasks**

- [ ] `T1.1` **Add:** Typed response models for the contract above.
  - **Target:** `backend/app/models/project.py` (**NEW** model classes in an existing file).
  - **Current → required:** The API has a model-file picker DTO but no DTO for missing target entities or their requirements → expose the specified read-only option shape.
  - **Implementation:** Use Pydantic fields with concrete descriptions. Keep `role` nullable as declared by `EntitySpec`; keep link paths and missing names in reference fields. Do not use project `Entity` or project `foreign_keys` models for these target facts.
  - **Constraints:** Preserve existing project serialization and `TargetModelFileOption`; do not add the reference fields to the entity-create payload.
  - **Validation:** `V-1`, `V-2`, `V-5`, `V-6`.

**Completion evidence:** The new Pydantic models serialize the specified option shape without changing existing project responses.

### Area 2: Resolve and project the associated model

**Objective:** The service produces all absent options from the authorized project's associated model and reports configured-model failures.

**Affected code:** `backend/app/services/target_model_entity_options_service.py` (**NEW**); `backend/tests/services/test_target_model_entity_options_service.py` (**NEW**).

**Dependencies:** Area 1.

**Tasks**

- [ ] `T2.1` **Implement:** A read service method accepting a project locator and returning `TargetModelEntityOptionsResponse`.
  - **Target:** `backend/app/services/target_model_entity_options_service.py` (**NEW**).
  - **Current → required:** No service projects an associated target model into missing entity options → load the project with `ProjectService.load_project`, check whether `metadata.target_model is None`, resolve configured models through `ProjectMapper.to_core`, parse with `TargetModel.model_validate`, and check `TargetModelSpecValidator.validate` before projection.
  - **Implementation:** Compare model entity names with `api_project.entities`. For each absent entity, copy only the declared identity and display facts; include columns where `required` is true and `generated` is false; include only unconditional required FK paths. Calculate missing path members from the project entity names. Use deterministic sorting. Convert expected model resolution, YAML, schema, or spec failures to `BadRequestError` with server-side logging; the public route must not reveal file paths or parser text. Do not swallow a configured missing file as an unconfigured model.
  - **Constraints:** No project write, independent file read, second directive resolver, or conformance run. Preserve the mapper's approved-root checks and do not alter `ValidationService.validate_target_model`.
  - **Validation:** `V-1`, `V-2`, `V-4`, `V-5`, `V-6`.
- [ ] `T2.2` **Test:** Service projection and error distinctions.
  - **Target:** `backend/tests/services/test_target_model_entity_options_service.py` (**NEW**).
  - **Current → required:** No focused service tests exist → cover `None` versus configured empty/invalid models; filtering of already present entities; required-first sorting and nullable role/public ID; generated required columns; direct and `via` paths; missing path members; and conditional-only links. Mock `ProjectService.load_project` for unit cases and assert no write method is called.
  - **Constraints:** Keep fixtures small and avoid inferred source columns, joins, or keys.
  - **Validation:** `V-1`.

**Completion evidence:** Service tests show a valid model yields deterministic reference data, an absent model yields the explicit empty state, and configured failures do not appear as the empty state.

### Area 3: Expose the authorized read operation

**Objective:** Clients can fetch the Phase 1 options only after project read authorization.

**Affected code:** `backend/app/api/v1/endpoints/projects.py::router` (existing); `backend/tests/api/v1/test_target_model_entity_options.py` (**NEW**); `backend/tests/authorization/test_cross_resource_access.py` (existing).

**Dependencies:** Areas 1 and 2.

**Tasks**

- [ ] `T3.1` **Add:** `GET /projects/{name}/target-model-entities` to the existing projects router.
  - **Target:** `backend/app/api/v1/endpoints/projects.py::router` (new route function).
  - **Current → required:** Existing routes expose target-model file references and project-local raw YAML, not missing entity options → return the new response model from the service.
  - **Implementation:** Require `AuthorizedResource` through `require_project(Action.READ)`, pass `authorized_project.resource.locator` to the service, and use `@handle_endpoint_errors`. Do not accept a model-path query or body field. The router is already registered, so no `api.py` change is needed.
  - **Constraints:** Keep the operation GET and read-only; preserve the raw YAML endpoint's local-only rule and the model-file list's meaning.
  - **Validation:** `V-2`, `V-3`, `V-4`, `V-5`, `V-6`.
- [ ] `T3.2` **Test:** Project-scoped HTTP behavior and authorization.
  - **Target:** `backend/tests/api/v1/test_target_model_entity_options.py` (**NEW**) and `backend/tests/authorization/test_cross_resource_access.py::test_authenticated_principal_cannot_cross_user_resource_boundaries` (existing).
  - **Current → required:** No route tests cover the new contract → create registered projects through POST, then test local and shared `@load` references, an inline model through raw YAML update, no model, a missing referenced file, an invalid model, and a configured valid model whose entities are all present. Assert HTTP status and response shape, that errors do not expose paths or parser text, that responses omit project `columns`/`foreign_keys`/`keys`, and that project YAML is unchanged by GET. Add the new path to the existing cross-user 404 case.
  - **Constraints:** Use the async `authorized_client` fixture and existing project setup patterns; keep the auth test's concealed `{"detail": "Resource not found"}` result.
  - **Validation:** `V-2`, `V-3`, `V-4`.

**Completion evidence:** Authorized GET returns the planned contract for all model forms; a principal without project read access receives concealed 404 before model data is loaded.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
| --- | --- | --- | --- |
| `PH1-AC-1` → `P-AC-1` | `T1.1`, `T2.1`, `T2.2`, `T3.1`, `T3.2` | `V-1`, `V-2`, `V-3` | Every absent entity appears once with exact name, role, and required flag; present entities do not appear. |
| `PH1-AC-2` → `P-AC-2` | `T2.1`, `T2.2`, `T3.1`, `T3.2` | `V-1`, `V-2`, `V-4` | Absent model gives HTTP 200/`configured: false`; configured missing or invalid model gives HTTP 400; GET leaves project YAML unchanged. |
| `PH1-AC-3` → `P-AC-8` | `T1.1`, `T2.1`, `T2.2`, `T3.2` | `V-1`, `V-2` | Required generated columns are excluded and `via` returns `[bridge, target]`, with absent path members identified. |

## Validation And Testing

| ID | Check and target | Command or method | Covers | Expected result | Baseline on 2026-10-20 |
| --- | --- | --- | --- | --- | --- |
| `V-1` | Service unit tests, including error and path cases | `.venv/bin/pytest -q -p no:cacheprovider backend/tests/services/test_target_model_entity_options_service.py` | `PH1-AC-1`–`3` | All planned service cases pass. | Not run: test file is **NEW**. |
| `V-2` | Authorized route integration: local/shared/inline/absent/missing/invalid models, exact response and no write | `.venv/bin/pytest -q -p no:cacheprovider backend/tests/api/v1/test_target_model_entity_options.py` | `PH1-AC-1`–`3` | HTTP 200 or 400 as specified; unchanged YAML; no source mapping fields in option data. | Not run: test file is **NEW**. |
| `V-3` | Cross-user project authorization | `.venv/bin/pytest -q -p no:cacheprovider backend/tests/authorization/test_cross_resource_access.py -k 'test_authenticated_principal_cannot_cross_user_resource_boundaries'` | `PH1-AC-1`, read authorization | New route returns concealed 404 to a principal without project read access. | Pass: existing cross-resource case passed; new path is pending. |
| `V-4` | Mapper and existing target-model route regression | `.venv/bin/pytest -q -p no:cacheprovider backend/tests/mappers/test_project_mapper_file_path_integration.py backend/tests/api/v1/test_projects.py -k 'target_model or target_models'` | `PH1-AC-2`, existing behavior | Local/shared resolution, approved-root rejection, file list, and raw YAML restrictions still pass. | Pass: 6 selected tests. |
| `V-5` | Black formatting check | `.venv/bin/black --check backend/app/models/project.py backend/app/services/target_model_entity_options_service.py backend/app/api/v1/endpoints/projects.py backend/tests/services/test_target_model_entity_options_service.py backend/tests/api/v1/test_target_model_entity_options.py backend/tests/authorization/test_cross_resource_access.py` | Changed Python files | No formatting changes required. | Pass for existing model, route, and authorization files; **NEW** files pending. |
| `V-6` | Ruff lint check | `.venv/bin/ruff check backend/app/models/project.py backend/app/services/target_model_entity_options_service.py backend/app/api/v1/endpoints/projects.py backend/tests/services/test_target_model_entity_options_service.py backend/tests/api/v1/test_target_model_entity_options.py backend/tests/authorization/test_cross_resource_access.py` | Changed Python files | No lint errors. | Pass for existing model and route files; **NEW** files pending. |

The baseline checks were read-only. `V-3`'s baseline confirms the existing concealment behavior, not the planned new path. The proposed test files must be created before `V-1`, `V-2`, `V-5`, or `V-6` can pass in full.

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Response DTOs | `backend/app/models/project.py` (new classes) | `T1.1` | OpenAPI route response has the specified typed fields. |
| Projection service | `backend/app/services/target_model_entity_options_service.py` (**NEW**) | `T2.1` | Returns sorted missing options or the explicit no-model state. |
| Service tests | `backend/tests/services/test_target_model_entity_options_service.py` (**NEW**) | `T2.2` | `V-1` passes. |
| Read route | `backend/app/api/v1/endpoints/projects.py` (new route) | `T3.1` | Read-authorized GET returns the DTO. |
| Route tests | `backend/tests/api/v1/test_target_model_entity_options.py` (**NEW**) | `T3.2` | `V-2` passes. |
| Authorization regression | `backend/tests/authorization/test_cross_resource_access.py` (existing test case) | `T3.2` | `V-3` includes the new path and passes. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Response | Not started | None | Contract fixed above. |
| Area 2: Service | Not started | Area 1 | Uses mapper resolution and target-model parsing. |
| Area 3: Route | Not started | Areas 1–2 | Projects router already registered. |

## Definition Of Done

- [ ] `PH1-AC-1`/`P-AC-1`, `PH1-AC-2`/`P-AC-2`, and `PH1-AC-3`/`P-AC-8` have passing task and validation results in the coverage table.
- [ ] All three work areas and six deliverables are complete; `VM-1` scenarios pass for local, shared, inline, absent, missing, and invalid models.
- [ ] `V-1` through `V-6` pass, including read authorization and existing target-model route and mapper behavior.
- [ ] The response is read-only and contains no inferred project `columns`, `foreign_keys`, or `keys`; existing project data and YAML remain unchanged after GET.
- [ ] The route's response model documents the contract; no migration or generated artifact is needed.
- [ ] Any deviation or follow-up is recorded, and no unresolved question affects implementation or validation.

**Implementation handoff:** If repository state at execution time conflicts with a verified target or contract above, stop and report the conflicting source and its effect before changing the design or widening scope.
