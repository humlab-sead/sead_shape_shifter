# Manifest-Driven Reconciliation Inputs — Phase 2 Task Plan

## Phase Summary

**Phase:** 2 — Consume the Contract Without Losing Saved Mappings. **Readiness:** Validated for implementation. The [phase plan](MANIFEST_DRIVEN_RECONCILIATION_INPUTS_PHASE_PLAN.md#phase-2-consume-the-contract-without-losing-saved-mappings) fixes backend enforcement for saved, YAML, and API-driven specifications. The Phase 1 contract and pilot candidates were verified at the deployed local service; other environments require their own checks. Fixture-based implementation and tests can proceed.

**Goal:** Replace hard-coded editor types and properties with the service's reconciliation contract, preserve existing specifications, and prevent matching with unsupported or unverifiable configuration.

**Sources:** [Approved proposal](MANIFEST_DRIVEN_RECONCILIATION_INPUTS.md) (`P-AC-2`, `P-AC-3`, `P-AC-9`), the linked Phase 2 plan (`VM-3`, `VM-4`), and the [Phase 1 task plan](MANIFEST_DRIVEN_RECONCILIATION_INPUTS_PHASE_1_TASK_PLAN.md). Phase 1 implemented the additive contract in Authority Service source and verified disposable candidate requests. On 2026-11-04, the deployed service at `http://localhost:8024` returned a valid supported-type manifest and nonempty candidates for both pilots. Staging deployment and a minimal-role `location` read grant have not been independently verified. Use fixture manifests for isolated Phase 2 tests; do not claim editor/backend integration from the service check alone.

**Acceptance criteria**

1. [ ] `PH2-AC-1` (from `P-AC-2`): The editor offers only supported types and properties declared for the selected type, without per-type property defaults.
2. [ ] `PH2-AC-2` (from `P-AC-3`): An unavailable or malformed manifest produces a visible error and no fallback; a valid zero-property type remains usable.
3. [ ] `PH2-AC-3` (from `P-AC-9`): Load, save, and type changes do not silently erase saved mappings; unsupported or unverifiable mappings cannot be used for matching until resolved.

## Repository Findings

**Repository basis:** 2026-11-04, Shape Shifter `feature/manifest-driven-reconciliation-inputs` at `60d75ad8`. The existing uncommitted `.vscode/settings.json` change is unrelated and was not considered. Authority Service paths below refer to the sibling repository; no changes there are proposed for Phase 2. Graphify was queried for the editor and matching path, then the findings below were checked against current source.

| Evidence | Finding | Planning implication |
| --- | --- | --- |
| Authority Service `src/metadata.py::get_reconciliation_metadata`, `src/api/model.py::ReconServiceManifest`; GET `http://localhost:8024/is_alive`, GET `/reconcile`, POST `/reconcile` | Source emits and validates `reconciliation.supportedTypes` alongside the OpenRefine fields. The deployed local service returned `alive`, 10 supported IDs, zero properties for `feature_type`, `place_name` for `location`, and nonempty candidate lists (2 and 1, respectively). | Consume the additive contract. Local service availability is verified; do not infer staging or separate minimal-role access from it. |
| `frontend/src/components/reconciliation/SpecificationEditor.vue::loadRemoteTypes`, `onRemoteTypeChange` | Types come from `defaultTypes` with a four-type fallback on error. Property rows come from hard-coded per-type defaults or saved keys. | Validate the required manifest fields, derive the supported options and exact per-type properties, and remove both fallback paths. |
| `SpecificationEditor.vue::save`, `formDataToYaml`, `yamlToFormData`, `validateSpecification` | Form saving sends the current mapping object. YAML serialization omits mappings with empty values; YAML-to-form only replaces mappings when the parsed field exists. Column validation checks local fields, not whether remote properties are still served. | Keep every saved mapping key/value through form and YAML round trips; show unsupported mappings separately from missing local columns. Do not turn a manifest outage into an empty property list. |
| `frontend/src/components/reconciliation/SpecificationsList.vue::isRemoteTypeValid`, `validateSpecification`, `reconcileSpec`; `ReconciliationView.vue::handleAutoReconcile`, `checkServiceHealth`, `saveYaml` | The list considers any non-null remote type valid, its column check does not check served properties, the list can open matching, and the view fetches `defaultTypes` for its count. The YAML tab saves a catalog independently of the form. | Display unknown/unsupported status consistently and do not rely on form-only checks. Avoid reporting OpenRefine-only types as matchable. |
| `frontend/src/api/reconciliation.ts::getManifest`, `frontend/src/stores/reconciliation.ts::getServiceManifest`, `frontend/src/types/reconciliation.ts` | The existing authenticated API and store fetch the raw manifest; its TypeScript return is `any`. | Type and validate the response before deriving client options. Preserve request errors rather than manufacturing a success-shaped fallback. |
| `backend/app/api/v1/endpoints/reconciliation.py::auto_reconcile_entity`, `auto_reconcile_entity_sync`, `suggest_entities`; `backend/app/services/reconciliation/service.py::auto_reconcile_entity`, `ReconciliationQueryService.create` | Both matching routes use saved catalogs; suggestions use the saved type directly. The query builder forwards all saved property IDs, and no path checks the manifest. | Enforce eligibility in the backend before matching or suggestions, including saved/YAML/API specifications; use the editor only for early feedback. |
| `backend/app/services/reconciliation/mapping_manager.py::update_entity_mapping`; `backend/tests/api/v1/test_reconciliation_specifications.py::test_update_specification_preserves_mapping` | The backend replaces metadata on update but preserves existing decisions; catalog and raw YAML paths can save configurations without consulting remote metadata. | Do not reject or strip unsupported saved values on read or save merely because matching is blocked. Preserve the existing decision links. |

## Scope

**In scope:** Manifest validation and derived options; visible error/zero-property/unknown states; preservation through form and YAML edits; backend eligibility for batch matching and suggestions; focused frontend and backend regression tests.

**Out of scope:** Changing Authority Service matching or the OpenRefine contract; choosing pilot business keys, configuring `feature_type` or `location`, live pilot results, export and normalization changes, and Phase 5 developer guidance. Do not alter the `site` review/decision/sidecar behavior.

## Work Breakdown

### Area 1: Consume and validate the manifest

**Objective:** One parsed client contract supplies supported remote types and their declared properties, with a separate error state.

**Affected code:** `frontend/src/types/reconciliation.ts`, `frontend/src/api/reconciliation.ts::getManifest`, `frontend/src/stores/reconciliation.ts::getServiceManifest`, `frontend/src/components/reconciliation/SpecificationEditor.vue::loadRemoteTypes`; `frontend/src/utils/reconciliationManifest.ts` **NEW**.

**Dependencies:** Phase 1's additive manifest shape. Fixture tests can run before deployment; live validation cannot.

**Tasks:**

* [x] `T1.1` **Change:** Type and validate the manifest response before using it as reconciliation options.
  * **Target:** `frontend/src/types/reconciliation.ts`, `frontend/src/api/reconciliation.ts::getManifest`, `frontend/src/utils/reconciliationManifest.ts` **NEW**.
  * **Current → required:** Raw `any` and a `defaultTypes` existence check → explicit validation of `defaultTypes` (unique, nonblank IDs and optional display names), `reconciliation.supportedTypes` (unique, nonblank IDs each resolving to one default type), and `extend.property_settings` (array of nonblank `name` and array of nonblank `entity_types` IDs).
  * **Implementation:** Derive supported labels from `defaultTypes` and properties only when `entity_types` contains the exact selected ID. Return an empty property list for valid metadata with no matching entries; report missing, malformed, or unavailable metadata as an error. Reuse this result wherever the list or view needs compatibility status.
  * **Constraints:** Do not use `defaultTypes` as evidence of matching support or infer service database availability from the manifest. Do not add a per-type client table or fallback.
  * **Validation:** `V-1`: mixed supported/OpenRefine-only types, exact type membership, missing/duplicate IDs, malformed properties, empty supported list, and valid zero-property type.

* [x] `T1.2` **Change:** Replace editor type/property fallback options and display a manifest error.
  * **Target:** `frontend/src/components/reconciliation/SpecificationEditor.vue::loadRemoteTypes`, `onRemoteTypeChange`, and remote-type/property template.
  * **Current → required:** A failed fetch offers built-in types and existing mappings determine available properties → supported types alone are selectable, with current manifest properties shown even when saved keys exist. A failed or invalid response shows a separate error, no fallback, and preserves the saved selection.
  * **Implementation:** Display matching `defaultTypes` names; retain a saved unsupported type as a visible current value, not as a selectable new supported option. Distinguish "no properties declared" from "properties cannot be checked"; do not create empty mappings merely by displaying available rows.
  * **Validation:** `V-2`: unsupported `taxon` excluded from new choices, supported `site` properties and zero-property `feature_type`, missing metadata, and network error with saved values still visible.

**Completion evidence:** Fixture tests identify valid empty metadata and malformed metadata differently; no hard-coded reconciliation type/property defaults remain in the editor.

### Area 2: Preserve and identify saved specifications

**Objective:** Existing type and mapping values survive form/YAML edits while incompatible or unverifiable values are visible.

**Affected code:** `frontend/src/components/reconciliation/SpecificationEditor.vue::validateSpecification`, `onRemoteTypeChange`, `save`, `formDataToYaml`, `yamlToFormData`; `frontend/src/components/reconciliation/SpecificationsList.vue::isRemoteTypeValid`, `validateSpecification`; `frontend/src/components/reconciliation/ReconciliationView.vue::checkServiceHealth`.

**Dependencies:** Area 1's validated contract. Matching eligibility for these values is resolved in Area 3.

**Tasks:**

* [x] `T2.1` **Change:** Preserve saved mapping entries when loading, changing a type, switching to YAML, and saving.
  * **Target:** `SpecificationEditor.vue::onRemoteTypeChange`, `formDataToYaml`, `yamlToFormData`, `save`, and mapping controls.
  * **Current → required:** Saved keys can replace displayed options, YAML serialization filters empty values, and an absent YAML mapping field can leave stale values → display the union of served properties and saved keys; mark saved keys outside the current type as unavailable; preserve every existing key and value until the operator explicitly removes or remaps it. A deliberate YAML deletion must remove that entry rather than resurrecting it.
  * **Implementation:** Keep compatibility as derived display state, not a destructive rewrite of `property_mappings`. Type changes update the status without clearing values. Permit saving unchanged legacy values during a manifest outage, but never label them verified. Keep existing decision mappings in the catalog.
  * **Validation:** `V-2`, `V-3`: load/save, unsupported property and type, type change, failed fetch, YAML/form round trip including empty values and explicit removal, and a valid no-property new specification.

* [x] `T2.2` **Change:** Report supported, unsupported, and unknown status consistently in specification list and view.
  * **Target:** `SpecificationsList.vue::isRemoteTypeValid`, `validateSpecification`, `getValidationStatus`, `validateAllSpecifications`; `ReconciliationView.vue::checkServiceHealth`.
  * **Current → required:** Any configured type appears valid and the view counts `defaultTypes` → status reflects current supported metadata or explicit inability to verify it; the displayed count does not claim OpenRefine-only types are matchable.
  * **Implementation:** Share the Area 1 validation result, surface failures instead of showing the pending state as valid, and retain source-column errors separately from unsupported service properties. Refresh status when specifications or manifest change.
  * **Validation:** `V-3`: unsupported saved type/property, failed manifest, valid zero-property type, and an unchanged `site` specification.

**Completion evidence:** No silent mapping deletion or false "valid configuration" status on load, save, type change, or outage.

### Area 3: Enforce backend eligibility and show client feedback

**Objective:** Candidate requests cannot use unsupported types or properties or an unavailable manifest, without deleting saved configuration.

**Affected code:** `frontend/src/components/reconciliation/ReconciliationView.vue::handleAutoReconcile`, `SpecificationsList.vue::reconcileSpec`; `backend/app/services/reconciliation/service.py::auto_reconcile_entity`, `backend/app/api/v1/endpoints/reconciliation.py::suggest_entities` and the sync/async matching routes.

**Dependencies:** Areas 1–2 and the Phase 1 manifest contract. The backend enforcement decision is recorded in the source phase plan.

**Tasks:**

* [x] `T3.1` **Change:** Enforce backend eligibility before any candidate request.
  * **Target:** `backend/app/services/reconciliation/service.py::auto_reconcile_entity` and `backend/app/api/v1/endpoints/reconciliation.py::suggest_entities`, with a shared service-side manifest check before batch matching or suggestions. The synchronous and asynchronous matching routes already call `auto_reconcile_entity`; verify failure reporting for each.
  * **Current → required:** Saved type and property IDs go straight to the matching client → the selected type must be supported, every saved property ID must be served for it, and manifest errors must stop matching with an explicit error. Empty properties are allowed.
  * **Implementation:** Await the existing `ReconciliationClient.get_service_manifest()` through the injected service client; validate required metadata and reject malformed/unavailable metadata, unsupported types, and unsupported saved property IDs without modifying catalog data. Apply the same rule to suggestions; ensure the asynchronous route reports failure instead of a successful matching result.
  * **Constraints:** Do not add matching logic to the client or reject reads/saves of legacy specifications. Preserve the existing disabled behavior of a specification with no configured `service_type`. Accept a valid supported type with zero declared properties when its mappings are empty.
  * **Validation:** `V-4`: sync/async saved-catalog requests and suggestions cannot reach the client with unsupported/unknown inputs; valid `site` and zero-property type still send candidate queries.

* [x] `T3.2` **Change:** Show a blocking reason at the UI's Find Candidates entry point.
  * **Target:** `ReconciliationView.vue::handleAutoReconcile` and the Find Candidates control; `SpecificationsList.vue::reconcileSpec` if eligibility is displayed in the list.
  * **Current → required:** Candidate search can start without knowing mapping compatibility → unknown/unsupported configurations display the reason and cannot give a success-shaped result; compatible specifications retain the existing review workflow.
  * **Validation:** `V-3`, `V-4`: outage and obsolete mapping are visibly blocked, with no request sent when blocked by the UI; backend failures remain visible to API callers.

**Completion evidence:** Backend enforcement is tested for both matching routes and suggestions, including saved/YAML/API specifications; no blocked request produces a successful matching result.

## Acceptance-Criteria Coverage

| Criterion (source) | Task IDs | Validation IDs | Expected evidence |
| --- | --- | --- | --- |
| `PH2-AC-1` (`P-AC-2`) | `T1.1`, `T1.2` | `V-1`, `V-2` | Only supported IDs and exact manifest properties offered; no per-type defaults. |
| `PH2-AC-2` (`P-AC-3`) | `T1.1`, `T1.2`, `T2.1` | `V-1`, `V-2` | Malformed/outage visible and no fallback; zero-property specification usable. |
| `PH2-AC-3` (`P-AC-9`) | `T2.1`, `T2.2`, `T3.1`, `T3.2` | `V-2`, `V-3`, `V-4` | All saved keys/values retained; unsupported/unknown compatibility blocks matching through the decided path. |

`VM-3` corresponds to `V-1` and `V-2`; `VM-4` corresponds to `V-2`, `V-3`, and `V-4`. The local deployed service is available for integration checks; verify availability separately in any other tested environment.

## Validation And Testing

Planned frontend commands run from the repository root. Frontend dependencies were absent during planning and were installed for implementation validation.

| ID | Check and target | Command or executable method | Covers | Expected result | Baseline (2026-11-04) |
| --- | --- | --- | --- | --- | --- |
| `V-1` | Typed manifest contract in `frontend/src/utils/__tests__/reconciliationManifest.test.ts` **NEW** | `cd frontend && pnpm test:run -- src/utils/__tests__/reconciliationManifest.test.ts` | `PH2-AC-1`, `PH2-AC-2` | Positive, empty, missing, duplicate, malformed and exact-membership fixture assertions pass. | Not run: test is planned and frontend dependencies are absent. |
| `V-2` | Editor behavior in `frontend/src/components/reconciliation/__tests__/SpecificationEditor.test.ts` **NEW** | `cd frontend && pnpm test:run -- src/components/reconciliation/__tests__/SpecificationEditor.test.ts` | `PH2-AC-1`–`PH2-AC-3` | Stub GET manifest with supported `site`/`feature_type`, OpenRefine-only `taxon`, and `site` properties; assert options, zero properties, error, saved values, explicit removal, and no destructive type/YAML changes. | Not run: test is planned and frontend dependencies are absent. |
| `V-3` | Existing list and view tests in `frontend/src/components/reconciliation/__tests__/SpecificationsList.test.ts`, `ReconciliationView.test.ts` (extend with status and matching-block tests) | `cd frontend && pnpm test:run -- src/components/reconciliation/__tests__/SpecificationsList.test.ts src/components/reconciliation/__tests__/ReconciliationView.test.ts` | `PH2-AC-3`, existing `site` UX | Valid/unsupported/unknown states and failed matching are explicit; `site` review and success behavior remain unchanged. | Not run: frontend dependencies are absent. |
| `V-4` | Backend service and protected-route regressions in `backend/tests/services/test_reconciliation_service.py`, `backend/tests/api/v1/test_reconciliation_decisions.py`, `backend/tests/api/v1/test_reconciliation_specifications.py` | `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -p no:cacheprovider backend/tests/services/test_reconciliation_service.py backend/tests/api/v1/test_reconciliation_decisions.py backend/tests/api/v1/test_reconciliation_specifications.py -q` | `PH2-AC-3`, no-type and existing decisions | Malformed/outage/unsupported saved values block batch and suggestion requests, valid zero-property and `site` paths still work, saving does not strip mappings or decisions. | Pass for focused current baseline only: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -p no:cacheprovider backend/tests/services/test_reconciliation_service.py -k 'auto_reconcile_entity_disabled_without_service_type or auto_reconcile_entity_no_queries' backend/tests/api/v1/test_reconciliation_specifications.py -k 'auto_reconcile_entity_disabled_without_service_type or auto_reconcile_entity_no_queries or test_update_specification_preserves_mapping' -q` (3 passed); no new eligibility tests yet. |
| `V-5` | Frontend type check/build and changed-file lint | `cd frontend && pnpm run build && pnpm exec eslint src/types/reconciliation.ts src/api/reconciliation.ts src/utils/reconciliationManifest.ts src/utils/__tests__/reconciliationManifest.test.ts src/components/reconciliation/SpecificationEditor.vue src/components/reconciliation/SpecificationsList.vue src/components/reconciliation/ReconciliationView.vue src/components/reconciliation/__tests__/SpecificationEditor.test.ts src/components/reconciliation/__tests__/SpecificationsList.test.ts src/components/reconciliation/__tests__/ReconciliationView.test.ts` | Type safety and frontend quality | Build and lint pass after implementation. | Not run: frontend dependencies are absent and planned files do not exist. |

Additional validation used `.venv/bin/black --check` and `.venv/bin/isort --check-only` on changed backend Python files; both passed. The protected-route authorization fixture pattern was retained in the new tests.

### Execution Results

| Check | Result | Evidence |
| --- | --- | --- |
| `V-1`–`V-3` | Pass | Focused Vitest run: 4 reconciliation test files, 37 tests passed. |
| `V-4` | Pass | Planned pytest command passed for the reconciliation service, decision routes, and specification routes. |
| `V-5` | Pass with warnings | Frontend type check/build passed. Changed-file ESLint exited successfully with 0 errors and 13 formatting warnings in unrelated existing sections and test helpers; Vite also reported a chunk-size advisory. |

The changed backend Python files pass Black and isort checks. A client-level integration check against `http://localhost:8024` confirmed that the manifest supports `site`; a `site` candidate query for `Uppsala` returned one candidate. Staging and minimal-role behavior remain unverified. Graphify was refreshed with `GRAPHIFY_VIZ_NODE_LIMIT=0 graphify update .`.

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Manifest contract and parser | `frontend/src/types/reconciliation.ts`, `frontend/src/api/reconciliation.ts`, `frontend/src/utils/reconciliationManifest.ts` **NEW** | `T1.1` | Typed, validated options with explicit failure state. |
| Editor and saved-value behavior | `frontend/src/components/reconciliation/SpecificationEditor.vue` | `T1.2`, `T2.1` | Derived choices and intact form/YAML round trips. |
| Status and matching feedback | `frontend/src/components/reconciliation/SpecificationsList.vue`, `ReconciliationView.vue` | `T2.2`, `T3.2` | Unsupported/unknown status shown without erasing data or reporting success. |
| Backend matching rule | `backend/app/services/reconciliation/service.py`, `backend/app/api/v1/endpoints/reconciliation.py` | `T3.1` | Guarded candidate entry points and explicit errors. |
| Frontend tests | `frontend/src/utils/__tests__/reconciliationManifest.test.ts` **NEW**, `frontend/src/components/reconciliation/__tests__/SpecificationEditor.test.ts` **NEW**, `SpecificationsList.test.ts`, `ReconciliationView.test.ts` in the same component test folder | `T1.1`, `T1.2`, `T2.1`, `T2.2`, `T3.2` | `V-1`–`V-3` pass. |
| Backend regressions | `backend/tests/services/test_reconciliation_service.py`, `backend/tests/api/v1/test_reconciliation_decisions.py`, `backend/tests/api/v1/test_reconciliation_specifications.py` | `T3.1` | `V-4` passes, including negative API paths and preservation. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1 — manifest | Complete | Phase 1 contract | `T1.1`–`T1.2` complete; `V-1` and `V-2` pass. |
| Area 2 — saved specifications | Complete | Area 1 | `T2.1`–`T2.2` complete; saved mappings are preserved and compatibility status is visible. |
| Area 3 — matching eligibility | Complete | Areas 1–2 | `T3.1`–`T3.2` complete; `V-3` and `V-4` pass. |

## Definition Of Done

* [x] The enforcement decision is recorded and this plan is Validated for implementation; the Phase 1 contract and pilot candidates were checked on the local deployed service, while other environments need separate verification.
* [x] `PH2-AC-1`–`PH2-AC-3` each have completed task and validation results, not just planned tests.
* [x] All work areas and listed deliverables are complete; `V-1`–`V-5` pass where applicable.
* [x] Saved type and all property keys/values survive load/save/type changes/outage; explicit removal works; matching cannot use unsupported or unverifiable metadata.
* [x] Valid zero-property matching and existing `site` review behavior are regression-tested; catalog saves do not discard operator decisions.
* [x] Client types, backend enforcement, documentation of deviations, and any generated artifacts are synchronized as applicable.
* [x] No unresolved question affects implementation, correctness, or validation. If current source differs from these verified paths or contract assumptions, stop and report the discrepancy rather than redesigning or expanding scope.

## Risks And Open Questions

- **Resolved — matching outside the editor:** Backend service-side preflight must check the manifest for previously saved, raw-YAML, and API-driven specifications before batch matching or suggestions. Editor validation provides early feedback, not authority to bypass the backend. Opening and saving legacy values remain allowed, and a missing service type retains its existing disabled behavior.
- **Phase 1 delivery:** The local deployed service returned the manifest contract and both pilot candidate lists on 2026-11-04. This does not establish that staging was deployed, that a minimal role can read `public.tbl_location_types`, or that Shape Shifter's client works against the service. Record each result separately; retest in the target environment before claiming Phase 2 end-to-end compatibility.
- **Preservation versus enforcement:** Treat unsupported/unknown mappings as saved data, not disposable inputs. A failure to verify compatibility must block matching, not prevent opening or saving the unchanged specification.
