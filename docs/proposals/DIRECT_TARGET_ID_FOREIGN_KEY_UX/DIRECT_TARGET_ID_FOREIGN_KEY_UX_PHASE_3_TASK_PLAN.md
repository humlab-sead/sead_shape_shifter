# Direct Target-ID Foreign Key UX — Phase 3 Task Plan

Source proposal: [DIRECT_TARGET_ID_FOREIGN_KEY_UX.md](./DIRECT_TARGET_ID_FOREIGN_KEY_UX.md)
Source phase plan: [DIRECT_TARGET_ID_FOREIGN_KEY_UX_PHASE_PLAN.md](./DIRECT_TARGET_ID_FOREIGN_KEY_UX_PHASE_PLAN.md)

## Phase Summary

**Phase:** Phase 3 — Add the Direct target IDs selector and its states

**Goal:** Let authors select and clear eligible direct target-model IDs in the entity editor, with distinct missing, unresolved, and resolved states, conflict handling, and no side effects on project foreign keys or dependencies.

**Readiness:** Validated. Every target below was verified in the current working tree, and no unresolved decision changes the implementation.

**Constraints and dependencies:**

- Frontend only. The Phase 1 route, response models, and service are already implemented and must not change. The Phase 2 map preservation in `EntityFormDialog.vue` is the write path this phase extends.
- The selector reads the Phase 1 contract `GET /api/v1/projects/{name}/target-model-direct-foreign-keys/{entity_name}` for the dialog's current entity name.
- Offer every relationship the contract returns. Do not inspect `formData.columns` and do not duplicate Core conformance checks.
- Selecting a target writes `foreign_key_value_sources.<target> = 'public_id'`. Clearing deletes only that entry. Never create or edit `foreign_keys` or `depends_on`.
- Only eligible `public_id` entries appear selected. Explicit `system_id` and stale entries stay visible and are preserved unchanged; removal stays possible through the YAML tab.
- Depends on Phase 1 (metadata contract) and Phase 2 (map round-trip), both present in the working tree.

**Phase criteria:** `PH3-AC-1`–`PH3-AC-5` (sources `P-AC-1`, `P-AC-3`, `P-AC-5`, `P-AC-6`, `P-AC-7`).

- [x] `PH3-AC-1` With no resolved target model, the selector cannot add any direct-ID entry.
- [x] `PH3-AC-2` Every compatible relationship is selectable even when its target ID column is not produced.
- [x] `PH3-AC-3` Selecting and clearing a target changes only its own entry and creates no project FK link or dependency.
- [x] `PH3-AC-4` Missing, unresolved, and resolved states are distinguishable, and project-FK conflicts are disabled with an explanation.
- [x] `PH3-AC-5` Only eligible `public_id` entries appear selected, while `system_id` and stale entries remain visible and preserved.

## Repository Findings

**Repository basis:** branch `direct-target-id-foreign-key-ux`, commit `2a17adf9`, planning date 2026-11-09. Uncommitted Phase 1 and Phase 2 changes are present and are the basis for this plan. Unrelated pending changes (`src/transforms/dsl.py`, advisor proposal documents) do not touch Phase 3 targets.

| Evidence | Finding | Planning implication |
| -------- | ------- | -------------------- |
| `backend/app/api/v1/endpoints/projects.py::get_project_target_model_direct_foreign_keys` | Phase 1 route `GET /projects/{name}/target-model-direct-foreign-keys/{entity_name}` is registered with `project:read` and returns the contract for any entity name. | The dialog can read metadata before an entity exists in the project, so create mode and manual name entry work. |
| `backend/app/models/project.py::TargetModelDirectForeignKeysResponse`, `::TargetModelDirectForeignKeyOption` | Responses are `{ state: 'not_configured' | 'unresolvable' | 'resolved', relationships: [{ target_entity, public_id, target_table }] }`. | Mirror these exact field names in the frontend client and the selector labels. |
| `backend/app/services/target_model_entity_options_service.py::TargetModelEntityOptionsService.get_direct_foreign_keys` | Returns `resolved` with an empty list when the named entity is absent from the model, and never raises for unconfigured or unresolvable models. | The UI needs a neutral empty state distinct from missing and unresolved states. |
| `frontend/src/api/projects.ts::projectsApi.getTargetModelEntityOptions` | Existing typed client method and response interfaces for the picker. | Add the new interfaces and method beside it; do not change the picker client. |
| `frontend/src/api/__tests__/projects.test.ts` | Mocks `apiRequest` and asserts exact method and URL for each client method. | Add focused tests for the new method with the same assertion style. |
| `frontend/src/components/entities/EntityFormDialog.vue::FormData.foreign_key_value_sources` | Phase 2 added `Record<string, unknown>` to form state and preserves it through parse, hydration, and serialization. | The selector reads and writes this field only. |
| `frontend/src/components/entities/EntityFormDialog.vue::buildEntityConfigFromFormData` | The serializer emits `foreign_key_value_sources` when non-empty and is the single path for save, YAML output, preview, and dirty tracking. | A selector change automatically participates in save and dirty state; no serializer change is required. |
| `frontend/src/components/entities/EntityFormDialog.vue::buildFormDataFromEntity`, `::resetTargetModelEntityState`, `::loadTargetModelEntityOptions` | Edit hydration fills `name`; create mode resets and loads picker options on dialog open and clears them on close/destroy. | Add a separate metadata reset and request-id guard beside this pattern. |
| `frontend/src/components/entities/EntityFormDialog.vue::formData.foreign_keys` | Project links are normalized objects carrying `entity`, `local_keys`, `remote_keys`. | Conflict detection compares `foreign_key.entity` with `target_entity`. |
| `frontend/src/components/entities/EntityFormDialog.vue::handleTargetEntitySelection` | Create-mode target selection assigns `formData.name` and `formData.public_id`. | Watching `formData.name` is sufficient to refresh metadata after a picker selection. |
| `frontend/src/components/entities/EntityFormDialog.vue::handleForeignKeysUpdate` | Relationship edits refresh form validity so Save enables. | The selector lives in the Basic tab inside the form, so no separate validity refresh is needed. |
| `frontend/node_modules/vuetify/lib/composables/list-items.js::transformItem` | `itemProps` defaults to the item's `props` key, so `{ title, value, props: { disabled, subtitle } }` reaches `v-list-item`. | Per-choice disabled state and explanation can be expressed in the `items` array without a custom renderer. |
| `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts::childStubs.VSelect` | The stub exposes `modelValue`, `label`, `items`, and `disabled` and passes items through untouched. | Tests can assert disabled state and item metadata directly, and can emit `update:modelValue` to exercise selection. |
| `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts::vi.mock('@/api')` | The mocked `api.projects` object contains only `getTargetModelEntityOptions`. | Add `getTargetModelDirectForeignKeys` to the mock and a default resolved response in `beforeEach`. |

## Scope

**In scope**

- Typed frontend client for the Phase 1 direct-FK contract in `frontend/src/api/projects.ts`.
- Client tests in `frontend/src/api/__tests__/projects.test.ts`.
- Metadata loading, state derivation, selection handling, conflict detection, and preserved-entry display in `frontend/src/components/entities/EntityFormDialog.vue`.
- The **Direct target IDs** multi-select in the Basic tab, after the produced-column controls.
- Dialog component tests in `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts`.

**Out of scope**

- Backend models, routes, services, Core, conformance, the change-request ingester, and `docs/AUTHORIZATION_ROUTE_INVENTORY.md`.
- The missing-entity picker (`getTargetModelEntityOptions`) and its behavior.
- Validation navigation for a missing output column (Phase 4).
- Removing stale entries through the selector. The YAML tab remains the removal path.
- Documentation updates; Phase 5 covers alignment with shipped behavior.

**Affected layers:** frontend API client, entity dialog component, frontend tests. No backend, Core, schema, or documentation change.

## Work Breakdown

### Area 1: Add the typed direct-FK client

**Objective:** The dialog can request direct-FK metadata for a project entity through a typed client method that returns the backend payload unchanged.

**Affected code:** `frontend/src/api/projects.ts` (existing file); `frontend/src/api/__tests__/projects.test.ts` (existing file).

**Dependencies:** None.

**Tasks:**

- [x] `T1.1` **Change:** Add the direct-FK response types and client method.
  - **Target:** `frontend/src/api/projects.ts`, beside `TargetModelEntityOptionsResponse` and `projectsApi.getTargetModelEntityOptions`.
  - **Current → required:** The client exposes only the missing-entity picker contract. Add the direct-FK contract.
  - **Implementation:**
    - Add `export type TargetModelDirectForeignKeysState = 'not_configured' | 'unresolvable' | 'resolved'`.
    - Add `export interface TargetModelDirectForeignKeyOption { target_entity: string; public_id: string; target_table: string }`.
    - Add `export interface TargetModelDirectForeignKeysResponse { state: TargetModelDirectForeignKeysState; relationships: TargetModelDirectForeignKeyOption[] }`.
    - Add `getTargetModelDirectForeignKeys: async (name: string, entityName: string): Promise<TargetModelDirectForeignKeysResponse>` that calls `apiRequest` with `method: 'GET'` and `url: \`/projects/${name}/target-model-direct-foreign-keys/${encodeURIComponent(entityName)}\``.
    - Return the response without reshaping it.
  - **Constraints:** Do not modify `TargetModelEntityOption`, `TargetModelEntityOptionsResponse`, or `getTargetModelEntityOptions`. Follow the existing object-literal client style.
  - **Validation:** `V-1`.

- [x] `T1.2` **Change:** Add client tests for the new method.
  - **Target:** `frontend/src/api/__tests__/projects.test.ts`, beside `describe('getTargetModelEntityOptions')`.
  - **Current → required:** No test covers the direct-FK method.
  - **Implementation:**
    - Import `TargetModelDirectForeignKeysResponse`.
    - `it('should fetch direct target-model foreign keys for one entity')`: mock a resolved payload with two relationships; assert the exact call `{ method: 'GET', url: '/projects/test-project/target-model-direct-foreign-keys/location' }` and that the result deep-equals the payload.
    - `it('should return a non-resolved direct-FK state without reshaping it')`: mock `{ state: 'not_configured', relationships: [] }`; assert the result deep-equals the payload.
    - `it('should encode the entity name in the direct-FK URL')`: call with `location type`; assert the URL contains `location%20type`.
    - `it('should reject when the direct-FK request fails')`: mock a rejected `apiRequest`; assert the method rejects with the same error.
  - **Constraints:** Reuse the file's existing `vi.mocked(apiRequest)` pattern. Do not change picker tests.
  - **Validation:** `V-1`.

**Completion evidence:** The new method returns resolved and non-resolved payloads unchanged and encodes the entity name.

### Area 2: Load metadata and derive selector state in the dialog

**Objective:** The dialog holds the current entity's direct-FK metadata, derives one UI state, and computes selectable items, selected values, conflicts, and preserved entries without touching project links.

**Affected code:** `frontend/src/components/entities/EntityFormDialog.vue` (existing file; new imports, state, computed values, and functions).

**Dependencies:** Area 1 types.

**Tasks:**

- [x] `T2.1` **Change:** Add request state, a reset function, and a debounced loader.
  - **Target:** `frontend/src/components/entities/EntityFormDialog.vue`, in the script setup near `targetModelEntityOptions` state and `resetTargetModelEntityState`.
  - **Current → required:** The dialog loads only picker options. Add read-only metadata for the current entity name.
  - **Implementation:**
    - Extend `import type { TargetModelEntityOption } from '@/api/projects'` with `TargetModelDirectForeignKeysResponse`.
    - Import `useDebounceFn` from `@vueuse/core`.
    - Add `directForeignKeys = ref<TargetModelDirectForeignKeysResponse | null>(null)`, `directForeignKeysLoading = ref(false)`, `directForeignKeysError = ref<string | null>(null)`, and `let directForeignKeysRequestId = 0`.
    - Add `resetDirectForeignKeyState()` that increments `directForeignKeysRequestId`, clears the three refs, and leaves `formData` untouched.
    - Add `async function loadDirectForeignKeys(): Promise<void>`: read `formData.value.name.trim()`; return through the reset path when the dialog is closed or the name is blank; otherwise increment the request id, set loading, call `api.projects.getTargetModelDirectForeignKeys(props.projectName, entityName)`, drop stale responses with the request-id and `props.modelValue` guard, store the response, and on failure store `Direct target IDs could not be loaded.` in `directForeignKeysError`. Keep the existing `console.error` style used by `loadTargetModelEntityOptions`.
    - Create `const debouncedLoadDirectForeignKeys = useDebounceFn(loadDirectForeignKeys, 300)`.
    - Add `watch([() => props.modelValue, () => formData.value.name], ...)` with `immediate: true`: reset when closed or blank, otherwise call `void debouncedLoadDirectForeignKeys()`.
    - Call `resetDirectForeignKeyState()` from `onUnmounted` beside `targetModelEntityOptionsRequestId += 1`.
  - **Constraints:** Read-only. The watcher must not write `formData`. Do not alter `loadTargetModelEntityOptions`, `handleTargetEntitySelection`, or the picker request id. Use the Phase 1 route only.
  - **Validation:** `V-2`, `V-4`.

- [x] `T2.2` **Change:** Add UI-state, item, selection, conflict, and preservation computations plus the selection setter.
  - **Target:** `frontend/src/components/entities/EntityFormDialog.vue`, in the computed section near `selectedTargetEntity` and in the helper section near `normalizeForeignKeyValueSourcesForForm`.
  - **Current → required:** The dialog has no representation of direct-ID choices. Add a single derived state machine and one mutation path.
  - **Implementation:**
    - Define `type DirectTargetIdsUiState = 'idle' | 'loading' | 'not_configured' | 'unresolvable' | 'error' | 'empty' | 'ready'`.
    - `directTargetIdsVisible = computed(() => Boolean(formData.value.name.trim()))`.
    - `directTargetIdsUiState` in this order: `idle` when not visible; `loading` while loading or before a response; `error` when `directForeignKeysError` is set; `not_configured` / `unresolvable` from `directForeignKeys.state`; `ready` when relationships are non-empty; otherwise `empty`.
    - `eligibleDirectTargets = computed(() => new Map(directForeignKeys.value?.relationships.map((relationship) => [relationship.target_entity, relationship]) ?? []))`.
    - `projectForeignKeyTargets = computed(() => new Set(formData.value.foreign_keys.map((fk: any) => fk?.entity).filter((entity): entity is string => typeof entity === 'string')))`.
    - `selectedDirectTargetIds` as a writable computed over `formData.value.foreign_key_value_sources`: return entries whose value is `'public_id'` and whose key is in `eligibleDirectTargets`; the setter must ignore changes unless `directTargetIdsUiState === 'ready'`, copy the current map, add `'public_id'` only for newly requested eligible non-conflicted targets, delete only entries that were previously selected and are absent from the requested set, and assign the copied map back. Never touch `foreign_keys` or `depends_on`.
    - `directForeignKeyItems` as `{ title: \`${relationship.target_entity} (${relationship.public_id})\`, value: relationship.target_entity, props: conflict ? { disabled: true, subtitle: 'A project Foreign Key to this target already exists. Remove it first.' } : {} }`, in the server's sorted order.
    - `preservedValueSourceEntries` as `{ target, value, reason }[]` for every map entry that is not an eligible selected `'public_id'` entry. Reasons: when the state is not `resolved`, `Preserved as written; target-model relationships are not available.`; otherwise `Uses system_id. Preserved as written.` for `system_id`, `Not declared by the target model. Preserved as written.` for an unknown target, and `Unrecognized value source "<value>". Preserved as written.` for anything else. Do not mutate the map to build this list.
  - **Constraints:** Do not filter relationships by `formData.columns`, `columnAvailability`, or `get_target_facing_columns`. Do not create links or dependencies. Keep `system_id` and stale entries in the map. Selected values are strings only.
  - **Validation:** `V-2`, `V-4`.

**Completion evidence:** For a resolved response the dialog derives items, selected values, and preserved entries from the map without changing any other form field.

### Area 3: Render the selector and its states

**Objective:** The Basic tab shows the **Direct target IDs** control with the correct state, conflict explanations, and preserved entries.

**Affected code:** `frontend/src/components/entities/EntityFormDialog.vue`, template in the Basic `v-window-item`.

**Dependencies:** Area 2 computations.

**Tasks:**

- [x] `T3.1` **Change:** Add the direct-target-ID form row after the produced-column controls.
  - **Target:** `frontend/src/components/entities/EntityFormDialog.vue`, after the Detected Columns form row and before the Fixed Values Grid block.
  - **Current → required:** The Basic tab ends the produced-column area without a direct-ID control.
  - **Implementation:**
    - Add one `form-row` guarded by `v-if="directTargetIdsVisible"` with `data-testid="direct-target-ids"`.
    - Render `<v-select v-model="selectedDirectTargetIds" label="Direct target IDs" :items="directForeignKeyItems" item-title="title" item-value="value" multiple chips closable-chips :disabled="directTargetIdsUiState !== 'ready'" :loading="directTargetIdsUiState === 'loading'" persistent-placeholder>` for `loading`, `not_configured`, `empty`, and `ready`. Keep the select present but disabled for `not_configured` and `empty`.
    - For `not_configured`, render a caption `Select a target model for this project to configure direct target IDs.`.
    - For `empty`, render a caption `The target model does not declare a direct foreign key for this entity.`.
    - For `unresolvable`, render a `v-alert` with `type="error"`, `variant="tonal"`, `density="compact"` and the text `The project target model could not be resolved. Direct target IDs are unavailable.`; do not render the select for this state.
    - For `error`, render a `v-alert` with `type="error"`, `variant="tonal"`, `density="compact"` and `directForeignKeysError`.
    - For `ready`, render a caption `Sets foreign_key_value_sources.<target> to public_id. Project Foreign Keys are not created.`.
    - After the select or alert, render `preservedValueSourceEntries` in a `data-testid="direct-target-ids-preserved"` block when non-empty: a caption `Preserved value sources` and one line per entry with `<code>{{ entry.target }}</code>: {{ entry.reason }}`.
    - Use existing Vuetify density, variant, and caption classes from the file.
  - **Constraints:** Do not add validation rules for output columns. Do not modify the Relationships tab or `ForeignKeyEditor`. Do not show the row when the entity name is blank.
  - **Validation:** `V-2`, `V-5`.

**Completion evidence:** The Basic tab shows a disabled selector with a prompt, an error, an empty-state prompt, or an enabled selector, plus preserved entries when the map has them.

### Area 4: Component tests for states, selection, conflicts, and preservation

**Objective:** Component tests lock each state, the selection and clearing behavior, conflict disabling, the no-filter rule, and preserved entries.

**Affected code:** `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts` (existing file).

**Dependencies:** Areas 1–3.

**Tasks:**

- [x] `T4.1` **Change:** Extend the mocked API and add a metadata wait helper.
  - **Target:** `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts`, in `mockState`, `vi.mock('@/api')`, and `beforeEach`.
  - **Current → required:** The mock has no direct-FK method, so the component would call an undefined function.
  - **Implementation:**
    - Add `getTargetModelDirectForeignKeys: vi.fn()` to `mockState` and `getTargetModelDirectForeignKeys: mockState.getTargetModelDirectForeignKeys` to the mocked `api.projects`.
    - In `beforeEach`, `mockState.getTargetModelDirectForeignKeys.mockReset()` and `mockResolvedValue({ state: 'resolved', relationships: [] })`.
    - Add `const directFkRelationships = [...]` fixture with `location_type (location_type_id)`, `method (method_id)`, and `weather_type (weather_type_id)`; none of those ID columns are in the `location` entity's `columns`, which covers `PH3-AC-2`.
    - Add `async function waitForDirectForeignKeys(): Promise<void>` that uses `await vi.waitFor(() => expect(mockState.getTargetModelDirectForeignKeys).toHaveBeenCalled())`, then `await flushPromises()` and `await nextTick()`.
    - Add `loading` to the `VSelect` stub's `props` array so pending-state assertions can read it.
  - **Constraints:** Use `vi.waitFor` because the loader is debounced by 300 ms. Do not add fake timers. Do not change the stub's template or remove its existing props.
  - **Validation:** `V-2`.

- [x] `T4.2` **Change:** Add six component tests beside the Phase 2 value-source tests.
  - **Target:** `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts`, after `omits foreign_key_value_sources from payloads when the entity has none`.
  - **Current → required:** No test exercises the selector.
  - **Implementation:**
    1. `it('renders direct target IDs for a resolved target model and labels each relationship')`: edit `createLocationEntity(mixedValueSources)`; mock resolved with `directFkRelationships`; await `waitForDirectForeignKeys()`; find `VSelect` by label `Direct target IDs`; assert `disabled` is false; assert items include `location_type (location_type_id)`, `method (method_id)`, and `weather_type (weather_type_id)`; assert the `method` item has `props.disabled === true` and a `props.subtitle` explaining the project Foreign Key; assert `location_type` and `weather_type` items are not disabled even though their ID columns are not produced.
    2. `it('disables direct target IDs when the project has no target model')`: mock `{ state: 'not_configured', relationships: [] }`; assert the select is disabled and the wrapper text contains `Select a target model for this project`; emit `update:modelValue` with `['location_type']` and assert `props('modelValue')` remains `[]`.
    3. `it('shows an error when the target model cannot be resolved or the request fails')`: mock `{ state: 'unresolvable', relationships: [] }` and assert the alert text `The project target model could not be resolved.` and that no `VSelect` labelled `Direct target IDs` exists. Then mount a second wrapper with `mockRejectedValue(new Error('boom'))`, await `waitForDirectForeignKeys()`, and assert `Direct target IDs could not be loaded.` is shown.
    4. `it('selects and clears only the requested public_id entry')`: edit `createLocationEntity(mixedValueSources)`; mock resolved with `directFkRelationships`; await `waitForDirectForeignKeys()`; emit `update:modelValue` with `['location_type', 'weather_type']`; emit again with `['weather_type']`; change `Public ID *`, save, and assert the saved map is `{ location_type is absent, method: 'system_id', stale_target: 'public_id', weather_type: 'public_id' }`; assert `foreign_keys` equals `locationForeignKeys` and `depends_on` equals `locationDependsOn`.
    5. `it('keeps only eligible public_id entries selected and preserves the rest')`: edit an entity whose map is `{ method: 'system_id', stale_target: 'public_id' }`; mock resolved with `directFkRelationships`; await `waitForDirectForeignKeys()`; assert the select `modelValue` is `[]`; assert the wrapper text contains `method`, `stale_target`, `Uses system_id.`, and `Not declared by the target model.`; change `Public ID *`, save, and assert both entries are unchanged in the payload.
    6. `it('disables direct target IDs while the metadata request is pending')`: replace the mock with an implementation that returns a promise and captures its resolve function; mount edit mode; `await vi.waitFor(() => expect(mockState.getTargetModelDirectForeignKeys).toHaveBeenCalled())`; assert the select `disabled` and `loading` are true; call the captured resolve with `{ state: 'resolved', relationships: directFkRelationships }`, `await flushPromises()`, and assert the select is enabled.
  - **Constraints:** Reuse `mountEntityFormDialog`, `createLocationEntity`, `mixedValueSources`, `locationForeignKeys`, `locationDependsOn`, `findSelectByLabel`, `setTextFieldValue`, and `mockState`. Do not modify existing tests. Use `expect.objectContaining` for payload assertions.
  - **Validation:** `V-2`.

**Completion evidence:** The six tests fail against the pre-change component and pass after Areas 1–3; all 47 pre-existing dialog tests still pass.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
| --------- | -------- | -------------- | ----------------- |
| `PH3-AC-1` | `T1.1`, `T2.1`, `T2.2`, `T3.1`, `T4.2` | `V-2` | `not_configured` renders a disabled selector; emitting a new value leaves the map unchanged. |
| `PH3-AC-2` | `T1.1`, `T2.2`, `T3.1`, `T4.2` | `V-2` | Items include every returned relationship, including targets whose `public_id` is absent from `formData.columns`. |
| `PH3-AC-3` | `T2.2`, `T3.1`, `T4.2` | `V-2` | Selecting adds one `public_id` entry; clearing deletes one entry; saved `foreign_keys` and `depends_on` are unchanged. |
| `PH3-AC-4` | `T2.1`, `T2.2`, `T3.1`, `T4.2` | `V-2` | Missing, unresolvable, request-failure, empty, and ready states render differently; conflicted items are disabled with a subtitle. |
| `PH3-AC-5` | `T2.2`, `T3.1`, `T4.2` | `V-2` | Selected values contain only eligible `public_id` keys; `system_id` and stale entries appear in the preserved block and survive a save. |

## Validation And Testing

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
| -- | ---------------- | ----------------- | ------ | --------------- | -------- |
| `V-1` | Direct-FK client tests | `cd frontend && npx vitest run src/api/__tests__/projects.test.ts` | `PH3-AC-1`–`PH3-AC-5` (client contract) | New method tests pass; picker tests unchanged | Pass 2026-11-09: 36 passed |
| `V-2` | Dialog component tests | `cd frontend && npx vitest run src/components/entities/__tests__/EntityFormDialog.test.ts` | `PH3-AC-1`–`PH3-AC-5` | Six new tests pass; all 47 pre-existing tests pass | Pass 2026-11-09: 47 passed |
| `V-3` | Combined frontend regression | `cd frontend && npx vitest run src/api/__tests__/projects.test.ts src/components/entities/__tests__/EntityFormDialog.test.ts` | Preserved client and dialog behavior | Both files pass together | Pass 2026-11-09: 83 passed |
| `V-4` | Frontend types | `cd frontend && npx vue-tsc --noEmit` | Implementation correctness | No diagnostics | Pass 2026-11-09: no diagnostics |
| `V-5` | Formatting and lint | `cd frontend && npx prettier --check src/api/projects.ts src/api/__tests__/projects.test.ts src/components/entities/EntityFormDialog.vue src/components/entities/__tests__/EntityFormDialog.test.ts && npx eslint src/api/projects.ts src/api/__tests__/projects.test.ts src/components/entities/EntityFormDialog.vue src/components/entities/__tests__/EntityFormDialog.test.ts` | Implementation quality | Both pass | Pass 2026-11-09: Prettier clean, ESLint clean |

Negative and boundary cases covered by `V-2`: no target model, unresolvable model, failed request, resolved model with no relationships, conflicted target, `system_id` entry, stale entry, selection and clearing, and a relationship whose ID column is not produced.

### Execution Notes

- Run `npx vitest run <file>` for focused checks. `npm run test:run` is the whole frontend suite and is unnecessary for this phase.
- `vi.waitFor` is required around `mockState.getTargetModelDirectForeignKeys` because the loader is debounced by 300 ms.
- The dialog test baseline is 47 tests because Phase 2 added three; do not treat that as a regression.

### Execution Record (2026-11-09)

All tasks `T1.1`–`T4.2` completed. Post-change results from the implementation run:

| ID | Result | Evidence |
| -- | ------ | -------- |
| `V-1` | Pass | 40 passed (36 baseline + 4 new direct-FK client tests) |
| `V-2` | Pass | 53 passed (47 baseline + 6 new selector tests) |
| `V-3` | Pass | 93 passed across both files |
| `V-4` | Pass | `vue-tsc --noEmit` reported no diagnostics |
| `V-5` | Pass | Prettier reported all files formatted; ESLint reported no issues |
| Extra | Pass | Full frontend suite: 68 files, 1044 tests passed; `ProjectDetailView` and `EntityListCard` dialog tests unchanged |

Implementation deviations from the plan text, all within the authorized scope:

- `directTargetIdsUiState` checks the error state before the pending-response state. The planned order put `loading` first, which would have made the `error` state unreachable because a failed request also leaves `directForeignKeys` unset.
- `waitForDirectForeignKeys` takes the mounted wrapper. Waiting only for the shared mock allowed a debounced call left by an earlier test to satisfy the wait before the current dialog had settled, which produced false failures. The helper now also waits for the current selector to leave its loading state.
- Captions and alerts render as siblings of the selector rather than inside its `#message` slot. The dialog test stub renders only the default slot, so a slotted caption would be invisible to the assertions the plan requires.
- `directTargetIdsVisible` and the loader read the entity name through `currentDirectTargetEntityName()`, which tolerates a cleared name. Some existing dialog paths set `formData.name` to `null` through YAML editing, and a direct `.trim()` raised unhandled rejections from the debounced loader.

Follow-up work for Phase 4: the selector deliberately performs no output-column check. `DIRECT_FK_OUTPUT_COLUMN_MISSING` remains Core's responsibility, and the navigation from that validation issue to the entity's column settings is Phase 4 scope.

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| ----------- | ------ | -------- | ------------------- |
| Direct-FK client types | `frontend/src/api/projects.ts::TargetModelDirectForeignKeysState`, `::TargetModelDirectForeignKeyOption`, `::TargetModelDirectForeignKeysResponse` | `T1.1` | Types compile and match the backend payload |
| Direct-FK client method | `frontend/src/api/projects.ts::projectsApi.getTargetModelDirectForeignKeys` | `T1.1` | `V-1` passes |
| Client tests | `frontend/src/api/__tests__/projects.test.ts` | `T1.2` | `V-1` passes |
| Metadata loader and state | `frontend/src/components/entities/EntityFormDialog.vue::loadDirectForeignKeys`, `::resetDirectForeignKeyState`, `::directTargetIdsUiState` | `T2.1` | States render from the Phase 1 contract |
| Selection and preservation logic | `frontend/src/components/entities/EntityFormDialog.vue::selectedDirectTargetIds`, `::directForeignKeyItems`, `::preservedValueSourceEntries` | `T2.2` | Only `foreign_key_value_sources` is mutated |
| Selector template | `frontend/src/components/entities/EntityFormDialog.vue` Basic tab row | `T3.1` | Selector and preserved block render for each state |
| Component tests | `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts` | `T4.1`, `T4.2` | `V-2` and `V-3` pass |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| ---- | ------ | ------------ | ----- |
| Area 1: Add the typed direct-FK client | Done | None | `V-1` pass |
| Area 2: Load metadata and derive selector state | Done | Area 1 | `V-2`, `V-4` pass |
| Area 3: Render the selector and its states | Done | Area 2 | `V-2`, `V-5` pass |
| Area 4: Component tests | Done | Areas 1–3 | `V-2`, `V-3` pass |

## Definition Of Done

- [x] Every acceptance criterion has implementation and validation evidence under `V-1`–`V-5`.
- [x] All four work areas and deliverables are complete.
- [x] `V-1`–`V-3` pass with all 47 pre-existing dialog tests and 36 pre-existing client tests unchanged.
- [x] `V-4` reports no diagnostics and `V-5` reports no formatting or lint findings.
- [x] A resolved selector offers every returned relationship, including one whose ID column is not produced.
- [x] Selecting and clearing change only `foreign_key_value_sources`; saved `foreign_keys` and `depends_on` are unchanged.
- [x] `system_id` and stale entries remain in the saved map and are shown with an explanation.
- [x] No backend, Core, schema, picker, or documentation file is modified.
- [x] Deviations and follow-up work for Phase 4 are documented.

## Risks And Open Questions

- **Resolved model with no relationships.** A resolved model that does not declare the entity returns `state: 'resolved'` with an empty list. The UI shows a disabled selector and the neutral `empty` caption, not an error. This follows the Phase 1 contract decision; no fourth state is added.
- **Conflict plus existing selection.** A map entry can be both selected and conflicted with a project `foreign_keys` link. The item stays selected and disabled with the conflict subtitle; the user can remove the direct selection or the project link. No automatic cleanup is performed.
- **Rename during editing.** Metadata is requested for `formData.name`. Renaming an entity in the open dialog makes previously eligible entries fall into the preserved block; they are not dropped. Opening the saved entity with its new name repeats that behavior.
- **Stale removal path.** The selector does not remove stale or `system_id` entries. The YAML tab remains the explicit removal path, which matches the proposal's preservation rule.
- **Request volume.** The loader is debounced by 300 ms and guarded by a request id, so typing a name cannot apply stale responses.
