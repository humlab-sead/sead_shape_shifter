# Declarative Business Keys — Phase 3 Task Plan: Frontend Adoption

## Phase Summary

**Goal:** Use backend `fixed_schema` for fixed-row order and business-key editing, without adding or ordering columns from `keys`.

**Readiness: Validated.** The [phase plan](DECLARATIVE_BUSINESS_KEYS_PHASE_PLAN.md#phase-3-frontend-adoption) marks Phase 3 ready after Phase 2. [Phase 2's task plan](DECLARATIVE_BUSINESS_KEYS_PHASE_2_TASK_PLAN.md) records all areas and validation complete on this branch; the current schema implementation and focused API tests confirm the dependency. The frontend still derives fixed order from keys and is ready for adoption work.

Sources: [proposal](DECLARATIVE_BUSINESS_KEYS.md) (`P-AC-5`) and [phase plan](DECLARATIVE_BUSINESS_KEYS_PHASE_PLAN.md#phase-3-frontend-adoption) (`PH3-AC-1`, `VM-3`).

- [ ] `PH3-AC-1` (from `P-AC-5`): The frontend uses backend fixed-schema metadata for row order and does not rebuild positional order from keys when metadata is present.

Constraints: preserve `system_id`/`public_id` identity behavior, free-text business-key entry, non-fixed entity editing, existing inline and `@load:` save flows, and the backend's transition support for recognized legacy values requests. No project or values files are rewritten by opening or validating an entity.

## Repository Findings

**Repository basis:** `declarative-business-keys` at `e91e3203`, inspected 2026-10-09. Worktree clean before this document was moved here; no uncommitted changes were used as a basis. `.venv/bin/graphify query` was used for navigation, then findings were checked against source and tests. Its broad query returned unrelated documentation nodes, so it was not treated as evidence for editor behavior.

| Evidence | Verified finding | Planning implication |
| --- | --- | --- |
| `backend/app/api/v1/endpoints/entities.py::_build_entity_response`; `frontend/src/api/entities.ts::FixedSchema`, `EntityResponse`, `EntityValuesResponse` | Entity responses expose optional `fixed_schema` with `full_columns`, `editable_columns`, `identity_columns`, `key_columns`, and `order_source`; external values responses have separate `columns` and positional `values`. | Preserve optional-response compatibility; use all metadata fields and check external values against the authoritative order. No new API endpoint is needed. |
| `backend/app/utils/fixed_schema.py::derive_fixed_schema`, `normalize_fixed_entity`; `docs/proposals/DECLARATIVE_BUSINESS_KEYS/DECLARATIVE_BUSINESS_KEYS_PHASE_2_TASK_PLAN.md` | Phase 2 derives `full_columns` from identity plus stored produced columns without key insertion, persists data-only `entity_data.columns`, and reports `key_columns` separately. `editable_columns` **excludes both identity and key columns**; produced key fields remain in `full_columns`. Phase 2 is recorded Done. | Read produced form columns from `full_columns` minus `identity_columns`, not `editable_columns` alone; use `editable_columns` to identify non-key fields and `key_columns` for key role/editing. No backend change is needed. |
| `backend/app/services/entity_values_service.py::EntityValuesService.get_values`, `_normalize_fixed_request_columns` | Fixed-values GET normalizes stored compatible permutations to the authoritative full order in memory; PUT accepts the exact new order or an exact recognized legacy order and rejects unknown/ambiguous layouts. | The editor should expect `response.columns === fixed_schema.full_columns` for a fixed external-values response, and reject mismatch visibly rather than invent a second legacy mapping. |
| `frontend/src/components/entities/EntityFormDialog.vue::buildFormDataFromEntity`, `loadExternalValuesIfNeeded` | Hydration reads `fixed_schema.full_columns` but recomputes editable columns; external values loading replaces form columns from `response.columns`. | Preserve metadata through both inline and external-values hydration; avoid overwriting metadata order on fetch. |
| `frontend/src/components/entities/EntityFormDialog.vue::fixedValuesColumns`, `buildEntityConfigFromFormData`, `buildDirtySnapshot`, `handleSubmit`, `handleSubmitAndClose`, fixed-column watchers | Grid, YAML/config save, dirty-state snapshot, and both external-values save paths use the locally rebuilt fixed order. The keys watcher inserts missing keys into `formData.columns`; the columns watcher filters keys. | Replace one ordering rule across all consumers; allow keys to be edited without changing produced columns, and ensure row remapping follows actual schema edits only. |
| `frontend/src/components/entities/entityFormMaterialization.ts::buildFixedValuesColumns`, `normalizeFixedValuesRowsForForm`, `remapFixedValuesRowsToColumns`, `getExternalValuesUpdateColumns` | The helper inserts keys into the positional order; the row normalizer assumes that order; external fixed updates select the grid columns. | Remove the key-driven helper and adapt normalization/remapping to backend order without changing values by position inadvertently. |
| `frontend/src/components/entities/FixedValuesGrid.vue::columnDefs`; `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts`, `entityFormMaterialization.test.ts`, `FixedValuesGrid.test.ts` | Grid renders columns in prop order. Dialog tests already mount a `fixed_schema` fixture but do not assert authoritative ordering; helper tests expect keys to add positions. | Test the dialog-to-grid contract and update obsolete helper assertions, rather than changing grid ordering itself. |
| `docs/USER_GUIDE.md` (fixed-entity editor instructions) | User guidance covers editing fixed rows. | Align the fixed-grid/key-editing instructions with the shipped Phase 3 behavior. |

## Scope

**In scope:** fixed-entity editor hydration, key editing, positional grid/inline/external values and save order, fallback for entity responses without `fixed_schema`, focused frontend tests, and corresponding fixed-editor user guidance.

**Out of scope:** backend/Core schema derivation and validation (Phases 1–2), Phase 4's grouped integration/regression run, Phase 5's legacy-request retirement, project-file migration, and changes to foreign-key or non-fixed output rules.

## Work Breakdown

### Area 1: Make backend metadata the editor's fixed schema

**Objective:** Opening an existing fixed entity shows exactly the backend's `full_columns` in the grid and keeps produced/key roles distinct.

**Affected code:** `frontend/src/components/entities/EntityFormDialog.vue::buildFormDataFromEntity`, `loadExternalValuesIfNeeded`, `fixedValuesColumns`; `frontend/src/components/entities/entityFormMaterialization.ts`; `frontend/src/api/entities.ts::FixedSchema`.

**Dependencies:** Phase 2 `fixed_schema` contract (verified). Produced key fields are part of the data columns but are excluded from `editable_columns` metadata; preserve them in the form's produced columns.

**Tasks:**

- [x] `T1.1` **Change:** Hydrate fixed editor roles and positional order from all `fixed_schema` fields when supplied.
  - **Target:** `frontend/src/components/entities/EntityFormDialog.vue::buildFormDataFromEntity`, `fixedValuesColumns`, `loadExternalValuesIfNeeded`; `frontend/src/api/entities.ts::FixedSchema`.
  - **Current → required:** The editor reads `full_columns` once but then derives grid columns from keys and replaces columns on an external fetch → hold backend `full_columns` as the positional order, use `identity_columns` to remove managed fields from the produced form-column list, `key_columns` for selected key roles, and `editable_columns` for the non-key data subset; retain `order_source` without making it a second ordering rule.
  - **Implementation:** Keep one fixed-schema state for the loaded entity and distinguish it from form edits. For `@load:` values, compare the backend-normalized `response.columns` with the active full order; if they differ, show an error and prevent a positional save rather than silently assigning rows to a different layout. Preserve the loaded ETag and materialization directive. Use `full_columns` in the grid, preview/dirty-state, and later save paths; exclude only identity fields from produced form columns so produced keys stay visible.
  - **Constraints:** A produced key belongs to `full_columns` but not the backend's `editable_columns` list; preserve that produced column in the form. `key_columns` describes a role, not an additional row position. Do not infer a missing field from a suggestion or key.
  - **Validation:** `V-1`, `V-2`, `V-3`: deliberately choose metadata order different from both stored columns and key order; assert grid props, visible form fields, key roles, and row cells, including external values.

- [x] `T1.2` **Change:** Provide a conservative transition path for responses without `fixed_schema`.
  - **Target:** `frontend/src/components/entities/EntityFormDialog.vue::buildFormDataFromEntity`, `loadExternalValuesIfNeeded`; `frontend/src/components/entities/entityFormMaterialization.ts::normalizeFixedValuesRowsForForm`.
  - **Current → required:** Missing metadata falls through to a key-ordered grid → derive only from explicitly stored/returned columns and known identity fields, never from `keys`; preserve values when the positional layout is unambiguous and show a load/save error for incompatible row widths or orders instead of guessing. In this case, `entity_data.keys` may supply selected key roles but not positional fields.
  - **Constraints:** Keep existing clients usable during the additive-metadata transition; do not add null-valued fields for absent keys or silently rewrite persisted rows.
  - **Validation:** `V-1`, `V-2`: no-metadata inline and `@load:` fixtures, with matching and mismatched row layouts.

**Completion evidence:** With Phase 2 metadata, opening a fixed entity preserves each metadata role and displays the `full_columns` order even when keys are in a different order; absent metadata never turns keys into columns.

### Area 2: Keep edits and both save paths aligned

**Objective:** Key edits affect key metadata only; positional values remain associated with their column names on open, edit, save, and reopen.

**Affected code:** `frontend/src/components/entities/EntityFormDialog.vue` (fixed watchers, config serialization, save handlers); `frontend/src/components/entities/entityFormMaterialization.ts` (fixed order, row normalization/remapping).

**Dependencies:** Area 1.

**Tasks:**

- [x] `T2.1` **Change:** Remove the keys-to-columns watcher and key-driven order reconstruction.
  - **Target:** `frontend/src/components/entities/EntityFormDialog.vue::fixedValuesColumns`, watchers for `formData.columns` and `formData.keys`; `frontend/src/components/entities/entityFormMaterialization.ts::buildFixedValuesColumns`, `remapFixedValuesRowsToColumns`.
  - **Current → required:** Adding a key adds a produced field/grid position, while removing a column can silently delete a selected key → changing keys alone does not change columns or row values; genuine edits to produced fields or identity remap values by name once.
  - **Implementation:** Derive the in-memory edited layout from identity and produced columns only, seeded by metadata for existing rows; remove/replace the key-based helper. Keep key selection advisory/free-text and let backend validation reject a key not produced. Do not silently remove keys as a side effect of editing columns. Retain `system_id` handling and public-ID identity updates.
  - **Validation:** `V-1`, `V-2`: adding an absent key does not add a grid field or mutate row arrays; reordering/removing a real produced column remaps by name; key also listed as produced column appears once.

- [x] `T2.2` **Change:** Save config and values in their appropriate backend-defined orders.
  - **Target:** `frontend/src/components/entities/EntityFormDialog.vue::buildEntityConfigFromFormData`, `buildDirtySnapshot`, `handleSubmit`, `handleSubmitAndClose`; `frontend/src/components/entities/entityFormMaterialization.ts::getExternalValuesUpdateColumns`.
  - **Current → required:** Fixed config `columns` and both `updateValues` calls use key-ordered full columns → config carries produced data columns (including any produced keys, excluding managed identity) according to the Phase 2 persistence contract, while external `columns` and positional rows use the same active full schema. Inline values and `column_types` retain their matching names/order.
  - **Implementation:** Use one layout for fixed grid, dirty-state comparison, preview, inline values, and both save variants. Preserve `@load:` directive/materialization fields and ETag concurrency handling; do not reinterpret rejected or ambiguous layouts.
  - **Validation:** `V-1`, `V-2`, `V-3`: assert both Save and Save & Close request columns and values, edited-row/name preservation, no spurious dirty state on load, and reopen round-trip.

**Completion evidence:** Editing keys alone changes only keys in the config; fixed values retain their field association after a produced-column edit; both save buttons send an identical authoritative positional order.

### Area 3: Document and validate the frontend contract

**Objective:** Tests and user guidance reflect the adopted Phase 2 schema.

**Affected code:** `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts`, `entityFormMaterialization.test.ts`, `FixedValuesGrid.test.ts`; `docs/USER_GUIDE.md`.

**Dependencies:** Areas 1–2.

**Tasks:**

- [x] `T3.1` **Change:** Replace legacy key-order assertions and add editor contract tests.
  - **Target:** `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts`, `entityFormMaterialization.test.ts`, `FixedValuesGrid.test.ts` (existing files).
  - **Current → required:** Helper tests assert keys add positions and dialog tests cover only fixed column types → assert metadata hydration, distinct key/column roles, grid column order and values, unknown key without column creation, remapping after produced-column edits, both save flows, external values, fallback, and rejection of ambiguous layouts.
  - **Validation:** `V-1`, `V-2`, `V-3`.

- [x] `T3.2` **Change:** Update fixed-editor instructions to distinguish produced columns, keys, and backend row order.
  - **Target:** `docs/USER_GUIDE.md` (existing fixed-entity editor section).
  - **Current → required:** Existing instructions do not explain the new key/column separation → explain that keys select produced fields but do not create grid columns, and that fixed rows follow the displayed backend schema.
  - **Validation:** `V-4`.

**Completion evidence:** Targeted tests exercise `VM-3` and the user guide matches the editor's observed behavior.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Definition-of-done evidence |
| --- | --- | --- | --- |
| `PH3-AC-1` (from `P-AC-5`, milestone `VM-3`) | `T1.1`, `T1.2`, `T2.1`, `T2.2`, `T3.1`, `T3.2` | `V-1`, `V-2`, `V-3`, `V-4` | Metadata order reaches the grid and both save flows unchanged by keys; missing-metadata transition is safe; tests and guidance agree. |

## Validation And Testing

**Baseline on inspected branch:** `pnpm --dir frontend test:run src/components/entities/__tests__/EntityFormDialog.test.ts src/components/entities/__tests__/entityFormMaterialization.test.ts src/components/entities/__tests__/FixedValuesGrid.test.ts` passed (33 tests, three files). `pnpm --dir frontend exec vue-tsc --noEmit` passed. Targeted `eslint` reported 0 errors and 3 existing Prettier warnings in the helper and helper test; `prettier --check` failed on those two files. These checks were run before plan creation; they do **not** validate Phase 3.

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
| --- | --- | --- | --- | --- | --- |
| `V-0` | Phase 2 prerequisite: backend schema contract | Inspect `backend/app/utils/fixed_schema.py::derive_fixed_schema` and run `.venv/bin/pytest backend/tests/services/test_entity_values_service.py backend/tests/api/v1/test_entities.py -q`; confirm full order is identity + produced fields, `editable_columns` excludes keys and identities, produced keys remain in `full_columns`, and GET normalizes safe external values. | Prerequisite for `PH3-AC-1` | Verified Phase 2 output; otherwise stop. | Pass: inspected implementation and both backend test files passed on `e91e3203`. |
| `V-1` | Dialog metadata, editing, Save and Save & Close in `EntityFormDialog.test.ts` | `pnpm --dir frontend test:run src/components/entities/__tests__/EntityFormDialog.test.ts`; fixture: full `['system_id','method_id','created_at','label']`, editable `['created_at']`, identity `['system_id','method_id']`, keys `['label']`, stored data columns `['created_at','label']`, inline `[[1,53,'2026-05-19','Sampling']]`. Assert exact grid order/cells, produced key stays in form columns despite exclusion from `editable_columns`, key-only edits do not add fields, and both save payloads retain row mapping; also test matching `@load:` response columns, ETag and no-metadata/mismatch cases. | `PH3-AC-1`, `VM-3` | New and existing tests pass; unambiguous layouts round-trip, incompatible ones report an error without submitting. | Pass: existing 16 tests; specified new cases not yet present. |
| `V-2` | Helper layout/remap in `entityFormMaterialization.test.ts` | `pnpm --dir frontend test:run src/components/entities/__tests__/entityFormMaterialization.test.ts`; test produced key once, absent key adds nothing, legacy/no-metadata row expansion only for unambiguous stored columns, and remap after data-column reorder. | `PH3-AC-1`, `VM-3` | Row widths and values match the named schema; no key-created columns. | Pass: existing 10 tests currently assert legacy key order. |
| `V-3` | Grid positional rendering and relevant focused regression | `pnpm --dir frontend test:run src/components/entities/__tests__/EntityFormDialog.test.ts src/components/entities/__tests__/entityFormMaterialization.test.ts src/components/entities/__tests__/FixedValuesGrid.test.ts`; assert `FixedValuesGrid` renders supplied order without recomputing keys, including typed cells. | `PH3-AC-1`, `VM-3` | All focused tests pass with new scenarios. | Pass: 33 existing tests; new scenarios not yet present. |
| `V-4` | Type, lint, formatting and user guidance | `pnpm --dir frontend exec vue-tsc --noEmit`; `pnpm --dir frontend exec eslint src/components/entities/EntityFormDialog.vue src/components/entities/entityFormMaterialization.ts src/components/entities/__tests__/EntityFormDialog.test.ts src/components/entities/__tests__/entityFormMaterialization.test.ts`; `pnpm --dir frontend exec prettier --check` on the same four files; compare `docs/USER_GUIDE.md` fixed-editor steps to actual UI and payload tests. | `PH3-AC-1` | Type/lint/format pass and guide matches behavior; record any pre-existing formatting warnings separately rather than broadening scope. | Type pass; lint 0 errors/3 warnings; formatting fail on helper and helper test; guide not checked against new behavior. |

### Phase 3 Execution Evidence

Ran on `declarative-business-keys` after implementation on 2026-10-09. The baselines above are pre-plan and are not Phase 3 evidence.

| ID | Check | Result |
| --- | --- | --- |
| `V-0` | `.venv/bin/pytest backend/tests/services/test_entity_values_service.py backend/tests/api/v1/test_entities.py -q` | Pass: 69 tests. Phase 2 contract confirmed: `full_columns` is identity plus produced fields, `editable_columns` excludes identity and keys, produced keys stay in `full_columns`, and GET normalizes safe external values. No conflict with the plan's assumptions. |
| `V-1` | `pnpm --dir frontend test:run src/components/entities/__tests__/EntityFormDialog.test.ts` | Pass: 23 tests. Added metadata-order hydration, key-without-produced-column, no-metadata fallback, inline produced-column remap, external-value Save and Save & Close round-trips, and ambiguous-layout rejection. |
| `V-2` | `pnpm --dir frontend test:run src/components/entities/__tests__/entityFormMaterialization.test.ts` | Pass: 11 tests. Legacy key-order assertions replaced with key-independent full-order, produced-key-once, and unambiguous legacy-expansion cases. |
| `V-3` | `pnpm --dir frontend test:run src/components/entities/__tests__/EntityFormDialog.test.ts src/components/entities/__tests__/entityFormMaterialization.test.ts src/components/entities/__tests__/FixedValuesGrid.test.ts` | Pass: 42 tests. `FixedValuesGrid` asserted to render the supplied column order. |
| `V-3` (regression) | `pnpm --dir frontend test:run` | Pass: 708 tests across 43 files. |
| `V-4` | `pnpm --dir frontend exec vue-tsc --noEmit` | Pass: exit 0. |
| `V-4` | `pnpm --dir frontend exec eslint` on the five changed frontend files | Pass: 0 errors, 7 warnings, all on pre-existing lines (`remapFixedValuesRowsToColumns` signature and a blank line, helper test line 84, and pre-existing `FixedValuesGrid.test.ts` rows). No new warnings for changed lines. |
| `V-4` | `pnpm --dir frontend exec prettier --check` on the same five files | Fails on `entityFormMaterialization.ts`, `entityFormMaterialization.test.ts`, and `FixedValuesGrid.test.ts` only for pre-existing issues; the changed lines are formatted. |
| `V-4` | `docs/USER_GUIDE.md` fixed-editor guidance | Updated with fixed grid order, business keys vs produced columns, and external-values mismatch behavior. |

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Fixed editor hydration, edits, save flows | `frontend/src/components/entities/EntityFormDialog.vue` | `T1.1`, `T1.2`, `T2.1`, `T2.2` | Grid and both save paths follow backend order without key-created fields. |
| Fixed layout and row helpers | `frontend/src/components/entities/entityFormMaterialization.ts` | `T1.1`, `T1.2`, `T2.1`, `T2.2` | Helpers never insert a key or guess an ambiguous row layout. |
| API contract type (only if Phase 2 changes the response shape) | `frontend/src/api/entities.ts::FixedSchema` | `T1.1` | Frontend type matches the verified Phase 2 response. |
| Focused tests | `frontend/src/components/entities/__tests__/EntityFormDialog.test.ts`, `entityFormMaterialization.test.ts`, `FixedValuesGrid.test.ts` | `T3.1` | `V-1`–`V-3` pass. |
| Fixed-entity editing instructions | `docs/USER_GUIDE.md` | `T3.2` | `V-4` guide check passes. |

No new files are planned.

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Adopt metadata | Done | Phase 2 / `V-0` complete | Fixed grid order and roles hydrate from `fixed_schema`; no-metadata fallback derives identity plus stored columns. |
| Area 2: Align edits and saves | Done | Area 1 | Keys no longer change columns; config saves produced columns and external values use the full order. |
| Area 3: Document and validate | Done | Areas 1–2 | Focused `V-1`–`V-4` evidence recorded above; grouped Phase 4 regression remains open. |

## Definition Of Done

- [x] `V-0` confirms Phase 2's schema and compatibility behavior before frontend implementation starts.
- [x] `PH3-AC-1` / `P-AC-5` has implementation and `V-1`–`V-4` evidence satisfying `VM-3`.
- [x] All areas and deliverables are complete, with tests, types, lint and formatting checked against their recorded baselines.
- [x] Grid, inline values, external values, both save buttons, and the hydrated/remapped layouts preserve the same named positional values, and ETag checks still work. Preview and dirty state reuse the asserted `buildEntityConfigFromFormData`; the full open→edit→save integration run is Phase 4. Non-fixed editing is covered by the passing full frontend suite.
- [x] Key edits do not synthesize columns, a produced key/column overlap is retained once, and unavailable metadata or ambiguous values fail visibly rather than silently shifting rows.
- [x] User guidance reflects shipped behavior; no deviations or follow-up work outside Phase 5's recorded rollout decision.
- [x] Implementation found no conflict with the verified Phase 2 contract (confirmed by `V-0`).

## Risks And Open Questions

- External `response.columns` can disagree with entity metadata despite Phase 2's GET normalization (for example, an older backend); a positional save must be rejected rather than guessed.
