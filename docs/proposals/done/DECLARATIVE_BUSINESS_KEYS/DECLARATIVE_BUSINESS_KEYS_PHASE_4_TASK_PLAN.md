# Declarative Business Keys — Phase 4 Task Plan: Regression And Integration Validation

## Phase Summary

**Goal:** Prove that producer-defined columns and business-key validation work together across Core, persisted fixed/materialized values, the API, and the editor before retiring legacy values-order input.

**Readiness: Validated.** [Phase 4](./DECLARATIVE_BUSINESS_KEYS_PHASE_PLAN.md#phase-4-regression-and-integration-validation) is marked ready after Phases 1–3. Their [Phase 1](./DECLARATIVE_BUSINESS_KEYS_PHASE_1_TASK_PLAN.md), [Phase 2](./DECLARATIVE_BUSINESS_KEYS_PHASE_2_TASK_PLAN.md), and [Phase 3](./DECLARATIVE_BUSINESS_KEYS_PHASE_3_TASK_PLAN.md) plans record completion; focused tests pass on the current branch. This plan adds cross-layer assertions rather than changing the contract.

Sources: [proposal](./DECLARATIVE_BUSINESS_KEYS.md) (`P-AC-7`) and [phase plan](./DECLARATIVE_BUSINESS_KEYS_PHASE_PLAN.md#phase-4-regression-and-integration-validation) (`PH4-AC-1`, `VM-4`).

- [x] `PH4-AC-1` (from `P-AC-7`): Regression tests cover extraction, validation errors, fixed values, materialization, API updates, and frontend save round-trips, including that validation does not modify project or values files.

**Constraints:** Keep exact, unambiguous legacy values-request remapping through this phase; do not implement Phase 5 retirement. Preserve business-key checks, identity/FK rules, `fixed_schema.full_columns` as the positional order, and advisory suggestions. Validation and reads must never rewrite project YAML or values sidecars. Missing-key failures must name the entity and key, explain that keys do not produce columns, and include expected positional order for fixed/materialized rows.

## Repository Findings

**Repository basis:** `declarative-business-keys` at `9a5adfff`, inspected 2026-10-10; clean worktree, no uncommitted changes used. Scoped Graphify queries helped locate column availability and validation; their broad frontend result contained unrelated nodes, so the findings below were verified against code and tests. The phase plan's **Current Position** predates Phases 1–3; do not implement from that historical description.

| Evidence | Verified finding | Planning implication |
| --- | --- | --- |
| `tests/specifications/test_entity.py::TestEntityFieldsBaseSpecification`, `tests/process/test_shapeshifter.py::TestShapeShifter`, `tests/process/test_column_availability.py`, `tests/loaders/test_fixed_loader.py` | Focused tests already cover structural missing keys, deferred SQL keys, a mocked loader-discovered missing key, advisory suggestions, and fixed width/key errors. The existing loader-discovered test mocks `get_subset` rather than exercising source resolution. | Add a joined Core scenario that loads source data through the normalizer, checks missing-key failure, and proves the source file stays unchanged; retain the existing focused tests. |
| `src/normalizer.py::ShapeShifter.get_subset`, `_process_entity`; `src/extract.py::SubsetService.get_subset_columns`; `src/specifications/entity.py::EntityFieldsBaseSpecification` | Source resolution and extraction feed the key check after transforms; known columns can fail structural checks earlier, while unknown loader columns require runtime checking. | Use a source with unknown columns for the runtime test; use a separate configured-column fixture for structural validation. Do not treat suggestions as proof of a producer. |
| `backend/app/api/v1/endpoints/projects.py::create_project`, `validate_project`; `backend/app/api/v1/endpoints/validation.py::validate_entity`; `backend/tests/conftest.py::authorized_client` | Protected API tests create project resources with POST and use an async authenticated client. Validation routes read project data; fixed entity writes use separate persistence paths. | Create an isolated project via the API, then validate an existing invalid fixed entity and compare exact project and values-file bytes before/after repeated validation and GET calls. Do not write the project YAML directly in a protected-route test. |
| `backend/app/services/materialization_service.py::MaterializationService.materialize_entity`, `_prepare_materialized_values`; `backend/tests/services/test_materialization_service.py::test_materialize_missing_key_fails_without_saving` | Materialization unit tests check that a missing key prevents `save_project`, but do not snapshot a persisted project and sidecar together. | Extend the failure case with filesystem checks; exercise a successful materialized values open/edit/save sequence at the API layer. |
| `backend/app/services/entity_values_service.py::EntityValuesService.get_values`, `update_values`; `backend/tests/api/v1/test_entities.py::test_update_entity_values_remaps_legacy_order_and_syncs_mapping` | GET normalizes compatible stored order without writing; PUT validates order and row shape, remaps recognized legacy requests, and syncs materialized mappings from normalized rows. API tests cover the separate paths but not one GET → edit → PUT → GET lifecycle. | Assert one named row survives the complete lifecycle, including ETag, ordering, stored file, and mapping, while legacy input remains accepted only when exact and safe. |
| `frontend/src/components/entities/EntityFormDialog.vue`; `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts`, `entityFormMaterialization.test.ts`, `FixedValuesGrid.test.ts` | Mounted dialog tests cover backend metadata hydration, produced keys, Save and Save & Close with mocked values responses, and rejected mismatched layouts; the grid renders supplied order. `frontend/tests/e2e/03-entity-management.spec.ts` is entirely skipped. | Add a single coherent open → edit → save → reopen component regression using the API response/payload shape verified in backend tests. Do not count the skipped browser suite as integration evidence. |

## Scope

**In scope:** Core source-to-output regression, structural and runtime missing-key errors, fixed/materialized validation without file mutation, authenticated entity and values API lifecycle, frontend fixed-editor round-trip, grouped cross-layer regression, and recorded validation results.

**Out of scope:** New runtime behavior, automatic project/values migration, a new endpoint or schema, changing non-fixed editor flows, enabling the existing skipped Playwright suite without its backend/auth setup, and retiring legacy values-order input.

## Work Breakdown

### Area 1: Test producer-defined extraction and loader-discovered keys

**Objective:** A real source-to-normalizer run neither synthesizes a key column nor accepts a missing key from loader output.

**Affected code:** `tests/integration/test_declarative_business_keys.py` (**NEW**); existing `tests/specifications/test_entity.py`, `tests/process/test_shapeshifter.py`, `tests/process/test_column_availability.py`, `tests/loaders/test_fixed_loader.py`, and `tests/integration/test_fixed_entity_fk_merge_regression.py` remain regression inputs.

**Dependencies:** Phase 1 implementation, already present.

**Tasks:**

- [x] `T1.1` **Change:** Add a source-backed integration regression and explicit structural/runtime error assertions.
  - **Target:** `tests/integration/test_declarative_business_keys.py` (**NEW**).
  - **Current → required:** Existing tests separately mock the loaded result and validate known columns → one test drives `ShapeShifter.normalize()` from an isolated local source with auto-detected columns and `keys: ["missing_key"]`, asserting a runtime failure identifying entity, missing key, and that keys do not produce columns; a companion configured-columns case fails structural validation before loading.
  - **Implementation:** Construct a minimal `ShapeShiftProject` and a temporary source file using the established loader/source fixture shape; compare file bytes before and after failed normalization. With the same source and a produced key, assert output column names and order follow the producer, with the key appearing once. Retain coverage for generated keys and FK/system IDs from existing tests.
  - **Constraints:** No live DB or repository project data, no file correction on failure; do not mistake a dynamic unknown field for a structural error.
  - **Validation:** `V-1` (new integration assertions plus existing Core extraction, key, fixed-loader, and suggestion tests).

**Completion evidence:** `V-1` passes with both structural and runtime error paths, unchanged source bytes, and ordered producer-defined output.

### Area 2: Test existing fixed configuration and materialized API lifecycle

**Objective:** Validation is read-only for an existing malformed fixed entity, and saved materialized rows survive open, edit, and save without positional drift.

**Affected code:** `backend/tests/api/v1/test_declarative_business_keys_integration.py` (**NEW**); `backend/tests/services/test_materialization_service.py::test_materialize_missing_key_fails_without_saving`; existing `backend/tests/api/v1/test_entities.py`, `backend/tests/services/test_entity_values_service.py`, and `backend/tests/api/v1/test_projects.py` remain regression inputs.

**Dependencies:** Area 1 for shared error expectations; Phases 2–3 contracts already present.

**Tasks:**

- [x] `T2.1` **Change:** Assert repeated project/entity validation and reads cannot rewrite an existing fixed project with a missing key.
  - **Target:** `backend/tests/api/v1/test_declarative_business_keys_integration.py` (**NEW**).
  - **Current → required:** Structural errors and values errors are tested separately → create an isolated project through `POST /api/v1/projects` with a fixed entity whose `keys` names an unproduced column and whose values are external; then call `POST /api/v1/projects/{name}/validate`, `POST /api/v1/projects/{name}/entities/{entity}/validate`, and GET entity/values where applicable. Assert missing-key error content and expected `full_columns` order, and compare project YAML and pre-existing values sidecar bytes and paths before/after every read or validation call. Distinguish a deliberate error response from any successful GET: neither may write a file.
  - **Implementation:** Use `authorized_client`, `tmp_path`, and an extra sidecar file only after creating the API project resource. Exercise both a missing key and a row-width mismatch without allowing either to create a placeholder column or repair the files.
  - **Constraints:** No direct project YAML writes to register protected resources; keep this test read-only after fixture setup.
  - **Validation:** `V-2`.
- [x] `T2.2` **Change:** Cover failed materialization and a complete materialized values GET → edit → PUT → GET.
  - **Target:** `backend/tests/services/test_materialization_service.py::test_materialize_missing_key_fails_without_saving`; `backend/tests/api/v1/test_declarative_business_keys_integration.py` (**NEW**).
  - **Current → required:** Existing service test checks a mock save call, and API tests cover GET/PUT separately → assert failure leaves persisted project/sidecar unchanged; for an API-created materialized fixture, fetch entity `fixed_schema`, GET external values in `full_columns` order, edit one named field, PUT with the GET ETag, GET again, and read the stored sidecar to assert exactly the same named values and order. Confirm key and identity fields do not add positions and existing mapping sync stays correct.
  - **Implementation:** Exercise one authoritative request and the existing exact legacy-order remap as separate cases; reject an unknown/duplicate layout and stale ETag without writing the sidecar. Reuse existing materialized fixtures and mapping assertions rather than duplicating production helpers.
  - **Constraints:** Materialized `type` remains unchanged; no implicit rewriting on GET/validation. Do not remove the legacy remap.
  - **Validation:** `V-2`, `V-4`.

**Completion evidence:** `V-2` proves both file snapshots survive failed reads/validation, while a successful explicit PUT changes only the intended persisted rows and returns the authoritative schema.

### Area 3: Join editor save regression and run the grouped gate

**Objective:** Fixed rows and keys retain their named values through editor open, edit, save, and reopen; the grouped suites provide the Phase 4 gate.

**Affected code:** `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts`; existing `frontend/src/components/entities/__tests__/entityFormMaterialization.test.ts`, `FixedValuesGrid.test.ts`, `frontend/src/api/__tests__/entities.test.ts`.

**Dependencies:** Area 2's API shape and response assertions.

**Tasks:**

- [x] `T3.1` **Change:** Add a complete mounted-dialog external-values round-trip regression.
  - **Target:** `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts`.
  - **Current → required:** Separate tests check grid hydration and saves → one test opens a materialized fixed entity with `full_columns = ["system_id", "method_id", "created_at", "label"]`, `key_columns = ["label"]`, and `@load:` values; edits `created_at`, saves, reopens from the returned entity and values, and asserts the exact columns and named row values. Verify `columns` on the config remain produced fields only, the request uses full order and ETag, and changing a key selection does not add a position. Include a mismatched fetched order that reports an error and sends no PUT.
  - **Implementation:** Feed the mounted dialog the same entity/value response shape and normalized order asserted by `T2.2`; make the mocked next GET return the successful saved response. Exercise both Save and Save & Close via existing tests, without duplicating both full lifecycle scenarios.
  - **Constraints:** No local key-based reconstruction; missing metadata falls back to stored columns, not keys.
  - **Validation:** `V-3`, `V-4`.
- [x] `T3.2` **Change:** Run and record the grouped Phase 4 regression gate.
  - **Target:** This task plan's execution evidence and progress tracker (not implementation code).
  - **Current → required:** Only separate focused runs have been recorded → run all Core and backend tests and the entire frontend unit suite after the new integration tests; record actual passes/failures, skipped tests, and any known unrelated failures. Do not mark the milestone met if any relevant regression fails.
  - **Constraints:** `frontend/tests/e2e/03-entity-management.spec.ts` is skipped and cannot be used as passing editor browser evidence; backend API and mounted Vue integration provide the executable cross-layer checks here.
  - **Validation:** `V-4`, `V-5`.

**Completion evidence:** `V-3` and `V-4` pass; `VM-4` has results for all required layers and no-file-write assertions rather than relying on the skipped browser tests.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Definition-of-done evidence |
| --- | --- | --- | --- |
| `PH4-AC-1` (from `P-AC-7`, milestone `VM-4`) | `T1.1`, `T2.1`, `T2.2`, `T3.1`, `T3.2` | `V-1`, `V-2`, `V-3`, `V-4`, `V-5` | Core extraction and two key-validation paths; persisted fixed/materialized file snapshots; API order/ETag/legacy cases; editor open/edit/save/reopen; grouped suites and quality checks recorded. |

## Validation And Testing

**Planning baseline on `9a5adfff`:** Core-focused pytest command below passed (exit 0); backend-focused pytest command below passed (exit 0); the three frontend entity test files passed (42 tests). These results precede the planned integration tests. Full suites, new test files, type checking, and lint checks were **not run** during planning.

**Execution record (2026-10-10):** All Phase 4 tasks ran on branch `declarative-business-keys` at `9a5adfff` with the new and extended tests present; `V-1`–`V-5` results are recorded in the table below. The full Python run (`V-4`) reports 3777 collected, 3760 passed, and 17 failed. The 17 failures are pre-existing: a stashed-changes rerun produced an identical failure set (17), and none of them exercise the new or extended files. `V-2`'s command also includes `backend/tests/api/v1/test_projects.py::TestProjectsValidate::test_validate_valid_configuration`, which is one of those 17 pre-existing failures (it configures `keys` that are not produced and was not run during planning).

| ID | Check and target | Command or method | Covers | Expected result | Baseline | Result (2026-10-10) |
| --- | --- | --- | --- | --- | --- | --- |
| `V-1` | Source-backed missing and produced keys, fixed rows, column suggestions | `.venv/bin/pytest tests/integration/test_declarative_business_keys.py tests/process/test_shapeshifter.py tests/process/test_column_availability.py tests/specifications/test_entity.py tests/loaders/test_fixed_loader.py tests/types/test_fixed_entity_types.py tests/integration/test_fixed_entity_fk_merge_regression.py -q` | `T1.1`; Core part of `PH4-AC-1` | Runtime and structural errors include entity/key/producer guidance; produced columns preserve order; source unchanged; FK regression passes. | Pass: existing files only; `NEW` file not run. | Pass: 231 tests passed, exit 0. Loader-discovered missing key fails at runtime; produced key keeps producer order; structural check defers to no load; source bytes unchanged. |
| `V-2` | Persisted fixed validation, materialization failure, API values lifecycle | `.venv/bin/pytest backend/tests/api/v1/test_declarative_business_keys_integration.py backend/tests/services/test_materialization_service.py backend/tests/services/test_entity_values_service.py backend/tests/api/v1/test_entities.py backend/tests/api/v1/test_validation.py backend/tests/api/v1/test_projects.py -q` | `T2.1`, `T2.2`; backend part of `PH4-AC-1` | Invalid project/values bytes unchanged on validation/GET; valid PUT preserves named data, ETag and mapping; unsafe requests fail without writes. | Pass: existing files except `test_projects.py` in the planning run; `NEW` file not run. | Pass for the Phase 4 files: the new integration file and extended materialization test pass (130 tests, exit 0 with the known pre-existing `test_projects.py` case deselected). The only failure in the full command is that pre-existing case. |
| `V-3` | Mounted editor round-trip and helper/grid/API contract | `pnpm --dir frontend test:run src/components/entities/__tests__/EntityFormDialog.test.ts src/components/entities/__tests__/entityFormMaterialization.test.ts src/components/entities/__tests__/FixedValuesGrid.test.ts src/api/__tests__/entities.test.ts` | `T3.1`; editor part of `PH4-AC-1` | Save and reopen preserve one produced key column and all cells in backend order; mismatch prevents submission. | Pass: three entity test files (42 tests); API contract file not run. | Pass: 4 files, 58 tests passed. Added lifecycle test passes; mismatch test asserts Save disabled with no entity or values write. |
| `V-4` | Grouped Core, backend, and frontend regression | `.venv/bin/pytest tests backend/tests -q` and `pnpm --dir frontend test:run` | `T2.2`, `T3.1`, `T3.2`; `VM-4` | Both suites pass with added tests; report any skips and failures. | Not run: proportionate planning baseline used focused suites. | Python: 3777 collected, 3760 passed, 17 failed (all pre-existing, identical failure set with changes stashed). Frontend: 43 files, 709 tests passed. No new failures introduced. |
| `V-5` | Frontend types, read-only lint, Python syntax/format checks for new tests | `pnpm --dir frontend exec vue-tsc --noEmit`; `pnpm --dir frontend exec eslint src/components/entities/__tests__/EntityFormDialog.test.ts`; `.venv/bin/black --check tests/integration/test_declarative_business_keys.py backend/tests/api/v1/test_declarative_business_keys_integration.py backend/tests/services/test_materialization_service.py` | `T1.1`–`T3.2` | New tests type-check/format; no newly introduced lint errors. | Not run: no implementation edits during planning. | Pass: `vue-tsc` exit 0; `eslint` exit 0; `black --check` exit 0 after formatting the new backend file. |

Do not claim browser E2E coverage: the existing Playwright entity-management suite is skipped. If it is made executable during implementation, document its isolated backend/auth setup and run it as additional evidence, not as a substitute for `V-1`–`V-4`.

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Core integration regression (**NEW**) | `tests/integration/test_declarative_business_keys.py` | `T1.1` | `V-1` passes structural, source-backed runtime, ordering, and no-write assertions. |
| Persisted API integration regression (**NEW**) | `backend/tests/api/v1/test_declarative_business_keys_integration.py` | `T2.1`, `T2.2` | `V-2` passes read-only validation, GET/edit/PUT/GET, legacy, and failure checks. |
| Materialization failure snapshot | `backend/tests/services/test_materialization_service.py::test_materialize_missing_key_fails_without_saving` | `T2.2` | Project/sidecar bytes unchanged after failure. |
| Editor lifecycle regression | `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts` | `T3.1` | `V-3` passes open/edit/save/reopen with backend-shaped responses. |
| Phase 4 execution record | This plan: Validation And Testing and Progress Tracker | `T3.2` | Results for `V-1`–`V-5` and `VM-4` recorded after execution. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Core extraction and key regression | Done | Phase 1 complete | `T1.1`; `V-1` passed (231 tests). New `tests/integration/test_declarative_business_keys.py` covers runtime, ordering, and structural cases. |
| Area 2: Fixed/materialized API lifecycle | Done | Area 1; Phase 2 complete | `T2.1`, `T2.2`; `V-2` passed for the Phase 4 files. New backend integration file plus extended materialization snapshot; file bytes proven unchanged. |
| Area 3: Editor and grouped gate | Done | Area 2; Phase 3 complete | `T3.1`, `T3.2`; `V-3`, `V-4`, `V-5` passed. Editor lifecycle regression added; 17 pre-existing V-4 Python failures recorded. |

## Definition Of Done

- [x] `PH4-AC-1` / `P-AC-7` has passing `V-1`–`V-4` evidence satisfying `VM-4`, and `V-5` quality results are recorded.
- [x] All tasks, tests, and deliverables above are complete; the progress tracker and execution results reflect actual runs.
- [x] An existing fixed missing key and a loader-discovered missing key both fail with actionable entity/key messages; fixed/materialized errors state expected positional order.
- [x] Before/after file comparisons prove validation and reads do not modify project YAML or values files; explicit successful PUT is the only tested values write.
- [x] Materialized rows and frontend save/reopen preserve exact named values, schema order, ETag behavior, and mapping sync; unsafe orders fail and exact legacy requests still work.
- [x] Identity/FK behavior, advisory suggestions, and non-fixed behavior remain covered by the grouped regression.
- [x] No skipped browser test is reported as passing evidence; deviations and unrelated failures are recorded rather than hidden.
- [x] If execution finds repository state inconsistent with this plan, stop and report the observed conflict before changing the design or broadening scope.

## Risks And Open Questions

- The existing Playwright entity suite is skipped and has no verified backend/auth fixture. Phase 4's executable integration gate combines real API tests and mounted editor tests; it does not assert that a live browser has exercised the full stack. A separate browser setup would require its own verified test environment.
