# Direct Target-ID Foreign Key UX — Phase 1 Task Plan

Source proposal: [DIRECT_TARGET_ID_FOREIGN_KEY_UX.md](./DIRECT_TARGET_ID_FOREIGN_KEY_UX.md)
Source phase plan: [DIRECT_TARGET_ID_FOREIGN_KEY_UX_PHASE_PLAN.md](./DIRECT_TARGET_ID_FOREIGN_KEY_UX_PHASE_PLAN.md)

## Phase Summary

**Phase:** Phase 1 — Read-only direct-FK relationship metadata contract

**Goal:** Return resolved direct target-model foreign-key metadata for one named entity in a project, with distinct unconfigured, unresolvable, and resolved outcomes.

**Readiness:** Validated. All targets below were verified in the current working tree, and no unresolved decision changes the implementation.

**Constraints and dependencies:**

- Read-only. The contract must not write project state, create project `foreign_keys` links, or create dependencies.
- Eligibility is direct-only: the foreign key has no `via`, and the target entity declares both `public_id` and `target_table`.
- The contract must not inspect whether the source currently produces the target ID column. Core conformance remains the only output-column check.
- The existing missing-entity picker route, response model, service method, and its `400` behavior stay unchanged.
- The endpoint accepts an entity name only. It must not require the entity to exist in the project, because the same dialog path supports create mode.
- Backend-only. The typed frontend client, selector UI, and project-FK conflict display belong to Phase 3.

**Phase criteria:** `PH1-AC-1`, `PH1-AC-2`, `PH1-AC-3` (sources `P-AC-1`, `P-AC-2`, `P-AC-3`).

- [x] `PH1-AC-1` Unconfigured and unresolvable target models produce distinct outcomes that never appear as an empty relationship list.
- [x] `PH1-AC-2` A resolved model returns all direct target-model foreign keys for the entity, including optional targets and targets configured in the project, while the existing picker response is unchanged.
- [x] `PH1-AC-3` The contract includes compatible relationships whose target ID column is not currently produced by the source.

## Repository Findings

**Repository basis:** branch `dev`, commit `2a17adf9`, planning date 2026-11-09. Uncommitted changes were present and considered: the proposal and phase plan are untracked, `docs/proposals/README.md` and one advisor proposal are modified, and `src/transforms/dsl.py` is modified. None of those changes touch the Phase 1 targets.

| Evidence | Finding | Planning implication |
| -------- | ------- | -------------------- |
| `backend/app/services/target_model_entity_options_service.py::TargetModelEntityOptionsService.get_entity_options` | Loads the API project, returns `configured=False` when `metadata.target_model` is absent, otherwise resolves through `ProjectMapper.to_core`, validates with `TargetModelSpecValidator`, and raises `BadRequestError` for resolution or specification failure. | Extract the resolution block into one private helper so the new method can reuse it without changing picker behavior or error text. |
| `backend/app/models/project.py::TargetModelEntityOptionsResponse` | Existing two-field response (`configured`, `entities`) describes missing entities only. | Add new response models instead of extending this one; do not change the picker payload. |
| `backend/app/api/v1/endpoints/projects.py::get_project_target_model_entities` | Route `GET /api/v1/projects/{name}/target-model-entities` declares `require_project(Action.READ)` and `handle_endpoint_errors`, and constructs `TargetModelEntityOptionsService()` directly. | Follow the same route shape, dependency, and error decorator for the new route. |
| `src/target_model/models.py::ForeignKeySpec`, `::EntitySpec` | `ForeignKeySpec` carries `entity` and optional `via`; `EntitySpec` carries optional `public_id` and `target_table`. | Eligibility can be decided from the parsed model alone. |
| `src/target_model/conformance.py::is_valid_direct_public_id_foreign_key` | Established direct-FK rules: no `via`, target declares `public_id` and `target_table`, no Core link, and the target `public_id` is in `get_target_facing_columns()`. It requires the source entity to exist in the project. | Do not reuse this function. The contract needs the narrower rule set: direct, `public_id`, `target_table`, no project-entity or output-column requirement. |
| `src/target_model/conformance.py::ForeignKeyValueSourceConformanceValidator` | Core reports `DIRECT_FK_OUTPUT_COLUMN_MISSING`, `DIRECT_FK_TARGET_PUBLIC_ID_MISSING`, `DIRECT_FK_TARGET_TABLE_MISSING`, and `DIRECT_FK_CORE_LINK_CONFLICT`. | The contract reports metadata only; it adds no validation and no core-link conflict flag. Phase 3 derives conflicts from the entity's existing project `foreign_keys`. |
| `src/target_model/spec_validator.py::TargetModelSpecValidator` | Rejects unknown foreign-key targets (`UNKNOWN_FOREIGN_KEY_ENTITY`), so a resolved model always names existing target entities. | A missing target spec is defensive code only; no test can reach it through a resolved model. |
| `backend/tests/services/test_target_model_entity_options_service.py` | Mocks `ProjectService` and monkeypatches `backend.app.services.target_model_entity_options_service.ProjectMapper.to_core`. | Keep the resolution helper and the `ProjectMapper.to_core` call inside that module so the existing tests still patch the same path. |
| `backend/tests/api/v1/test_target_model_entity_options.py` | Establishes the API test pattern: `tmp_path` projects directory, `settings` monkeypatching, `reset_services`, `authorized_client`, project creation, and model configuration as local, shared, or inline. | Mirror this pattern in a new API test file for the new route. |
| `backend/tests/authorization/test_route_authentication.py` | Compares documented route requirements in `docs/AUTHORIZATION_ROUTE_INVENTORY.md` with registered routes and route metadata. | A new route requires a matching inventory row, otherwise the authorization suite fails. |
| `docs/AUTHORIZATION_ROUTE_INVENTORY.md` | Projects table lists `target-model-entities`, `target-model-docs`, `target-model-yaml`, and `target-models` as `project:read`. | Add one row for the new route with `project:read`. |
| `frontend/src/api/projects.ts::projectsApi.getTargetModelEntityOptions` | Typed client exists for the picker only. | Out of scope for Phase 1; Phase 3 adds the client method for the new route. |

## Scope

**In scope**

- New response models for the direct-FK contract in `backend/app/models/project.py`.
- One private target-model resolution helper extracted from the existing service method, with unchanged picker behavior.
- New service method that returns the three states and the eligible direct relationships.
- New read-only route `GET /api/v1/projects/{name}/target-model-direct-foreign-keys/{entity_name}` on the projects router.
- Service tests, API tests, cross-resource authorization case, and the route inventory row.

**Out of scope**

- Frontend types, API client, selector component, and conflict display (Phase 3).
- Map preservation in the entity dialog (Phase 2).
- Validation navigation for a missing column (Phase 4).
- Changes to `src/target_model/conformance.py`, the change-request ingester, `foreign_key_value_sources` semantics, or `get_target_facing_columns()`.
- Any change to `TargetModelEntityOptionsResponse`, `TargetModelEntityOptionsService.get_entity_options`, or the picker route's `400` behavior.

**Affected layers:** backend model, backend service, backend route, backend tests, authorization inventory documentation. Core is read only (`src/target_model/models.py` types are consumed, not changed).

## Work Breakdown

### Area 1: Define the direct-FK response contract

**Objective:** A typed, read-only payload that states the target-model outcome and lists eligible direct relationships.

**Affected code:** `backend/app/models/project.py` (existing file; `TargetModelDirectForeignKeyOption` and `TargetModelDirectForeignKeysResponse` are **NEW**).

**Dependencies:** None.

**Tasks:**

- [x] `T1.1` **Change:** Add the two response models that describe the contract.
  - **Target:** `backend/app/models/project.py`, beside `TargetModelEntityOptionsResponse`.
  - **Current → required:** The module exposes only the missing-entity option models. Add a contract that reports one of three states plus eligible relationships.
  - **Implementation:**
    - `TargetModelDirectForeignKeyOption` with `target_entity: str`, `public_id: str`, `target_table: str`, each `Field(..., description=...)` naming the target-model fact it carries.
    - `TargetModelDirectForeignKeysResponse` with `state: Literal["not_configured", "unresolvable", "resolved"]` and `relationships: list[TargetModelDirectForeignKeyOption] = Field(default_factory=list)`.
    - Use the existing `Literal` and `Field` imports in the module; do not add imports.
    - Document in the model docstrings that `relationships` is empty only for the two non-resolved states or for a resolved model where the named entity declares no eligible direct foreign key.
  - **Constraints:** No change to `TargetModelEntityOptionsResponse`, `TargetModelEntityOption`, or `TargetModelRequiredLink`. `public_id` and `target_table` are non-optional here because eligibility requires both.
  - **Validation:** `V-1`, `V-3`, `V-5`.

**Completion evidence:** The models import cleanly, appear in the OpenAPI schema for the new route, and serialize to `{"state": ..., "relationships": [...]}`.

### Area 2: Add resolution and relationship selection to the service

**Objective:** The service returns the three contract states and every eligible direct target-model foreign key for the named entity, without touching project state.

**Affected code:** `backend/app/services/target_model_entity_options_service.py::TargetModelEntityOptionsService` (existing file; `_TargetModelResolutionError` is **NEW**; `_resolve_target_model`, `get_direct_foreign_keys`, and `_direct_foreign_keys` are **NEW** members).

**Dependencies:** Area 1 response models.

**Tasks:**

- [x] `T2.1` **Change:** Extract target-model resolution into one helper and keep the existing picker behavior identical.
  - **Target:** `backend/app/services/target_model_entity_options_service.py::TargetModelEntityOptionsService`.
  - **Current → required:** Resolution, the generic warning, and the `BadRequestError` message are inline in `get_entity_options`. Split the resolution step so two callers can share it with different failure handling.
  - **Implementation:**
    - Add a private module-level exception `_TargetModelResolutionError(Exception)`.
    - Add `_resolve_target_model(self, api_project: Project, project_name: str) -> TargetModel` containing the current `ProjectMapper.to_core` call, the mapping check, `TargetModel.model_validate`, `TargetModelSpecValidator().validate`, the existing `logger.warning` calls, and the same `except (FileNotFoundError, OSError, UnicodeError, yaml.YAMLError, ValueError, TypeError)` clause that raises `_TargetModelResolutionError`.
    - `get_entity_options` keeps its `configured=False` early return, then calls the helper inside `try/except _TargetModelResolutionError` and raises `BadRequestError("The configured target model could not be loaded or is invalid")` with the helper exception as the cause.
    - Update the class docstring to "Build read-only target-model options for a project." and the method docstring accordingly.
  - **Constraints:** Preserve the exact HTTP error text, the absence of file paths in responses, the single warning per failure, and the `ProjectMapper.to_core` call location that existing tests monkeypatch. Do not add writes.
  - **Validation:** `V-1`, `V-2`.

- [x] `T2.2` **Change:** Add the contract method and the relationship-selection rule.
  - **Target:** `backend/app/services/target_model_entity_options_service.py::TargetModelEntityOptionsService.get_direct_foreign_keys`, `::_direct_foreign_keys`.
  - **Current → required:** The service exposes only missing-entity options. Add a per-entity, read-only direct-FK listing with state separation.
  - **Implementation:**
    1. `get_direct_foreign_keys(self, project_name: str, entity_name: str) -> TargetModelDirectForeignKeysResponse` loads the project with `self.project_service.load_project(project_name)`.
    2. If `api_project.metadata is None` or `api_project.metadata.target_model is None`, return `state="not_configured"` with no relationships.
    3. Call `_resolve_target_model` inside `try/except _TargetModelResolutionError` and return `state="unresolvable"` with no relationships on failure. Do not raise; the route returns `200` for both non-resolved states.
    4. Return `state="resolved"` with `self._direct_foreign_keys(target_model, entity_name)`.
    5. `_direct_foreign_keys(target_model: TargetModel, entity_name: str) -> list[TargetModelDirectForeignKeyOption]` returns an empty list when `target_model.entities.get(entity_name)` is `None`. Otherwise iterate `entity_spec.foreign_keys`, skip entries with `via`, skip targets whose spec is missing or lacks `public_id` or `target_table`, and emit `TargetModelDirectForeignKeyOption(target_entity=..., public_id=target_spec.public_id, target_table=target_spec.target_table)`.
    6. Deduplicate by `target_entity` so the map key the selector writes is unique, and sort the result by `target_entity` for a stable payload.
    7. Never read `Project.get_table`, `get_target_facing_columns()`, project `foreign_keys`, or `foreign_key_value_sources`.
  - **Constraints:** Read-only; no `save_project`, `add_entity`, or entity mutation. Absolute imports only. Include optional relationships and targets already present in the project. Do not include `via` relationships or targets missing `public_id`/`target_table`.
  - **Validation:** `V-1`, `V-3`, `V-5`.

- [x] `T2.3` **Change:** Extend the service tests for the new method and the preserved picker behavior.
  - **Target:** `backend/tests/services/test_target_model_entity_options_service.py` (existing file).
  - **Current → required:** Tests cover only `get_entity_options`. Add contract tests and keep the existing cases unchanged.
  - **Implementation:**
    - Add a `_direct_fk_target_model()` fixture whose source entity declares: one required direct foreign key with a complete target, one optional direct foreign key with a complete target, one direct foreign key to an entity already configured in the project, one `via` foreign key whose target is complete, one direct foreign key whose target has `public_id` only, and one direct foreign key whose target has `target_table` only.
    - Assert `get_direct_foreign_keys` returns `not_configured` for a project without a target model and an empty relationship list.
    - Assert `unresolvable` for an invalid model (`model: {}` / `entities: {}`) and for a mocked `ProjectMapper.to_core` failure, with an empty relationship list.
    - Assert `resolved` returns exactly the two complete direct targets plus the target already in the project, sorted by `target_entity`, and excludes the `via` target and both incomplete targets.
    - Assert the relationship payload contains `target_entity`, `public_id`, and `target_table`, and nothing else.
    - Assert an unknown `entity_name` under a resolved model returns `resolved` with an empty relationship list.
    - Assert `project_service.save_project`, `add_entity`, and any write helper are not called.
    - Keep the existing picker tests unchanged and green.
  - **Constraints:** Reuse the existing `Mock(spec=ProjectService)` fixture and `_project(...)` helper style. Do not rename existing tests or fixtures.
  - **Validation:** `V-1`, `V-2`.

**Completion evidence:** The service returns all three states with the eligible relationship set, and the existing picker tests pass without modification.

### Area 3: Expose the route and keep authorization documentation aligned

**Objective:** The dialog can call one read-only route for any entity name, and the authorization inventory matches the assembled route table.

**Affected code:** `backend/app/api/v1/endpoints/projects.py` (existing file; `get_project_target_model_direct_foreign_keys` is **NEW**); `backend/tests/api/v1/test_target_model_direct_foreign_keys.py` (**NEW**); `backend/tests/authorization/test_cross_resource_access.py` (existing file); `docs/AUTHORIZATION_ROUTE_INVENTORY.md` (existing file).

**Dependencies:** Areas 1 and 2.

**Tasks:**

- [x] `T3.1` **Change:** Add the read-only route.
  - **Target:** `backend/app/api/v1/endpoints/projects.py`, next to `get_project_target_model_entities`.
  - **Current → required:** No route exposes per-entity direct-FK metadata.
  - **Implementation:**
    - `@router.get("/projects/{name}/target-model-direct-foreign-keys/{entity_name}", response_model=TargetModelDirectForeignKeysResponse)` with `@handle_endpoint_errors`.
    - `async def get_project_target_model_direct_foreign_keys(name: str,  # pylint: disable=unused-argument, entity_name: str, authorized_project: Annotated[AuthorizedResource, Depends(require_project(Action.READ))]) -> TargetModelDirectForeignKeysResponse`.
    - Return `TargetModelEntityOptionsService().get_direct_foreign_keys(authorized_project.resource.locator, entity_name)`.
    - Add `TargetModelDirectForeignKeysResponse` to the existing `backend.app.models.project` import block; no other import changes.
    - Docstring: "Return direct target-model foreign keys eligible for direct target IDs."
  - **Constraints:** `project:read` only. Do not look up the entity in the project. Do not raise for unconfigured or unresolvable models; those return the state payload. Do not modify the picker route.
  - **Validation:** `V-3`, `V-4`, `V-5`, `V-6`.

- [x] `T3.2` **Change:** Add API tests for the route.
  - **Target:** `backend/tests/api/v1/test_target_model_direct_foreign_keys.py` (**NEW**).
  - **Current → required:** The file does not exist. Add route-level coverage mirroring `backend/tests/api/v1/test_target_model_entity_options.py`.
  - **Implementation:**
    - Reuse the existing pattern: `reset_services` fixture, `authorized_client`, `tmp_path` projects directory, `settings.PROJECTS_DIR` and `settings.GLOBAL_TARGET_MODEL_DIR` monkeypatching, a project created through `POST /api/v1/projects`, and a model configured as local, shared, or inline. Parametrize at least `local` and `shared` for the resolved case.
    - Model fixture: a source entity with a required direct target, an optional direct target, a `via` target, a target already present in the project, and a target with only `public_id`.
    - Assert resolved payload fields and ordering, exclusion of the `via` relationship, inclusion of the optional and already-present targets, and inclusion of a target whose `public_id` column the source entity does not declare.
    - Assert `{"state": "not_configured", "relationships": []}` with status `200` when the project has no target model.
    - Parametrize missing, invalid, and malformed model files and assert `{"state": "unresolvable", "relationships": []}` with status `200`, no filesystem path or filename in the response body, and that `/api/v1/projects/test_project/target-model-entities` still returns `400` for the same project.
    - Assert that a resolved response includes a target entity that the picker omits because it is already configured in the project, proving the picker payload is unchanged for the same project.
    - Capture `GET /api/v1/projects/test_project/raw-yaml` before and after the new call and assert equality.
  - **Constraints:** Use absolute imports and the shared `authorized_client` fixture. Do not duplicate or edit the existing picker test file.
  - **Validation:** `V-3`, `V-4`.

- [x] `T3.3` **Change:** Add the cross-resource authorization case.
  - **Target:** `backend/tests/authorization/test_cross_resource_access.py::test_authenticated_principal_cannot_cross_user_resource_boundaries`.
  - **Current → required:** The `cases` tuple covers `/target-model-entities` but not the new route.
  - **Implementation:** Add `("GET", "/api/v1/projects/alice-project/target-model-direct-foreign-keys/site", None, 404)` to the tuple. The existing loop asserts the concealed `{"detail": "Resource not found"}` body.
  - **Constraints:** Do not change the test's setup, overrides, or other cases.
  - **Validation:** `V-4`.

- [x] `T3.4` **Change:** Record the route in the authorization inventory.
  - **Target:** `docs/AUTHORIZATION_ROUTE_INVENTORY.md`, Projects table.
  - **Current → required:** The table lists the other target-model routes but not the new one, and the route inventory test fails when a registered route is undocumented.
  - **Implementation:** Add `| \`GET\` | \`/api/v1/projects/{name}/target-model-direct-foreign-keys/{entity_name}\` | \`project:read\` |` after the `target-model-entities` row, keeping the existing column alignment.
  - **Constraints:** Change only the Projects table. Do not reorder or reword other rows.
  - **Validation:** `V-4`.

**Completion evidence:** The route returns the three states for any entity name, the authorization suite passes with the documented inventory row, and the cross-resource case returns the concealed `404`.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
| --------- | -------- | -------------- | ----------------- |
| `PH1-AC-1` | `T1.1`, `T2.1`, `T2.2`, `T2.3`, `T3.1`, `T3.2` | `V-1`, `V-3` | `state` is `not_configured` without a target model, `unresolvable` for load or specification failures, and `resolved` otherwise; neither non-resolved state returns relationships, and no such case returns an empty list instead of a state. |
| `PH1-AC-2` | `T2.2`, `T2.3`, `T3.1`, `T3.2` | `V-1`, `V-2`, `V-3` | Resolved payload contains required, optional, and already-configured direct targets; `via` and incomplete targets are absent; existing picker tests and the picker route response are unchanged. |
| `PH1-AC-3` | `T2.2`, `T2.3`, `T3.2` | `V-1`, `V-3` | A direct target with `public_id` and `target_table` is returned although the source entity does not declare that ID column. |

## Validation And Testing

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
| -- | ---------------- | ----------------- | ------ | --------------- | -------- |
| `V-1` | New service contract tests | `uv run pytest backend/tests/services/test_target_model_entity_options_service.py -v` | `PH1-AC-1`, `PH1-AC-2`, `PH1-AC-3` | New state, filtering, ordering, and no-write cases pass | Pass 2026-11-09: 11 passed with `.venv/bin/python -m pytest ... -n 0 -q` |
| `V-2` | Existing picker regression | `uv run pytest backend/tests/services/test_target_model_entity_options_service.py backend/tests/api/v1/test_target_model_entity_options.py -v` | `PH1-AC-2` | Every pre-existing test passes without edits | Pass 2026-11-09: 19 passed with `.venv/bin/python -m pytest ... -n 0 -q`; no pre-existing test was edited |
| `V-3` | New route tests | `uv run pytest backend/tests/api/v1/test_target_model_direct_foreign_keys.py -v` | `PH1-AC-1`, `PH1-AC-2`, `PH1-AC-3` | Local, shared, and inline models return `resolved`; unconfigured and failing models return the state payload; raw YAML is unchanged | Pass 2026-11-09: 9 passed with `.venv/bin/python -m pytest ... -n 0 -q` |
| `V-4` | Authorization and inventory alignment | `uv run pytest backend/tests/authorization/test_route_authentication.py backend/tests/authorization/test_cross_resource_access.py -v` | Route authorization for all three criteria (supporting check) | Inventory matches registered routes; cross-resource request returns `404` | Pass 2026-11-09: 140 passed with `.venv/bin/python -m pytest ... -n 0 -q` |
| `V-5` | Static types | `uv run pyright backend/app/models/project.py backend/app/services/target_model_entity_options_service.py backend/app/api/v1/endpoints/projects.py` | Implementation correctness | No new errors | Pass 2026-11-09: 0 errors, 0 warnings, 0 informations |
| `V-6` | Lint and formatting | `uv run black --check backend/app backend/tests && uv run pylint backend/app/services/target_model_entity_options_service.py backend/app/api/v1/endpoints/projects.py backend/tests/services/test_target_model_entity_options_service.py backend/tests/api/v1/test_target_model_direct_foreign_keys.py` | Implementation quality | No new findings; line length at most 140 | Partial 2026-11-09: `black --check` passes on all six changed files; repo-wide `black --check` reports the pre-existing, unmodified `backend/app/mappers/link_troubleshooter_mapper.py`; `pylint` scores 10.00/10 |

Negative and boundary cases covered by `V-1` and `V-3`: missing model, invalid model, malformed YAML, mocked resolution failure, unknown entity name, `via` relationship, target without `public_id`, target without `target_table`, and a target whose ID column the source does not produce. Duplicate direct foreign keys to the same target are covered by the deduplication assertion in `V-1`.

### Execution Notes

- In this environment `uv run pytest ...` exited without collecting tests and printed `Pytest: No tests collected`. Every test check above was run as `.venv/bin/python -m pytest ... -n 0 -q`, which collects and runs the same files.
- The repo-wide `black --check` failure in `backend/app/mappers/link_troubleshooter_mapper.py` is pre-existing; that file is unmodified by this phase.

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| ----------- | ------ | -------- | ------------------- |
| Response contract | `backend/app/models/project.py::TargetModelDirectForeignKeyOption`, `::TargetModelDirectForeignKeysResponse` | `T1.1` | Models import and serialize as documented |
| Service resolution helper | `backend/app/services/target_model_entity_options_service.py::_TargetModelResolutionError`, `::TargetModelEntityOptionsService._resolve_target_model` | `T2.1` | Existing picker error behavior and warnings unchanged |
| Contract method | `backend/app/services/target_model_entity_options_service.py::TargetModelEntityOptionsService.get_direct_foreign_keys`, `::_direct_foreign_keys` | `T2.2` | Three states and eligible relationship set returned in stable order |
| Service tests | `backend/tests/services/test_target_model_entity_options_service.py` | `T2.3` | `V-1` and `V-2` pass |
| Route | `backend/app/api/v1/endpoints/projects.py::get_project_target_model_direct_foreign_keys` | `T3.1` | `GET /api/v1/projects/{name}/target-model-direct-foreign-keys/{entity_name}` returns the contract |
| API tests | `backend/tests/api/v1/test_target_model_direct_foreign_keys.py` (**NEW**) | `T3.2` | `V-3` passes |
| Cross-resource case | `backend/tests/authorization/test_cross_resource_access.py` | `T3.3` | `V-4` passes with the new case |
| Route inventory | `docs/AUTHORIZATION_ROUTE_INVENTORY.md` | `T3.4` | Inventory test in `V-4` passes |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| ---- | ------ | ------------ | ----- |
| Area 1: Define the direct-FK response contract | Done | None | Added `TargetModelDirectForeignKeyOption` and `TargetModelDirectForeignKeysResponse` |
| Area 2: Add resolution and relationship selection | Done | Area 1 | Shared `_resolve_target_model` helper; picker behavior preserved |
| Area 3: Expose the route and align authorization | Done | Areas 1 and 2 | Route, API tests, cross-resource case, inventory row added |

## Definition Of Done

- [x] Every acceptance criterion has implementation and validation evidence recorded under `V-1`–`V-6`.
- [x] All three work areas and their deliverables are complete.
- [x] `V-1`–`V-4` pass on the changed branch; `V-5` and `V-6` report no new findings.
- [x] The picker route, `TargetModelEntityOptionsResponse`, `get_entity_options`, and existing service and API tests are unchanged and green.
- [x] No write method is called by the new service method or route.
- [x] The route inventory row matches the registered route path and requirement.
- [x] No frontend, conformance, ingester, or `get_target_facing_columns()` file is modified.
- [ ] Deviations and follow-up work for Phase 3 are recorded in the pull request description. Not yet done: no pull request exists for this branch at the time of implementation.

## Risks And Open Questions

- **Neutral empty list for an unknown entity.** A resolved model that does not declare the named entity returns `resolved` with an empty relationship list. This is not a fourth state, by design: the proposal defines three model outcomes. Phase 3 must render a neutral empty state for this case. If the selector needs distinct wording, add an `entity_in_model` flag in Phase 3 rather than inventing a fourth state now.
- **Duplicate direct foreign keys.** A model that declares the same direct target twice is deduplicated by `target_entity` because `foreign_key_value_sources` is keyed by target. The first eligible occurrence wins, and sorting keeps the payload deterministic. No model constraint currently rejects duplicates.
- **Picker semantics differ by design.** The new route returns `200` with a state for unresolvable models, while the picker returns `400`. The difference is intentional: the dialog needs to distinguish states, and the picker's established behavior must not change. Tests in `V-2` and `V-3` pin both behaviors.
- **Inventory drift.** `docs/AUTHORIZATION_ROUTE_INVENTORY.md` is machine-checked. Adding the route without `T3.4` fails `V-4`; this is expected and not a reason to skip the documentation update.
