# Manifest-Driven Reconciliation Inputs — Phase 4 Task Plan

## Phase Summary

**Phase:** 4 — Validate Property Mapping Without a Type-Specific Client Change. **Readiness:** Validated for implementation. [Phase 4 of the phase plan](MANIFEST_DRIVEN_RECONCILIATION_INPUTS_PHASE_PLAN.md#phase-4-validate-property-mapping-without-a-type-specific-client-change) is marked ready.

**Goal:** Configure a synthetic `location` specification from a mocked manifest, then prove that its `place_name` source value reaches a mocked candidate request and that reviewed, exported decisions produce stable offline parent and child identities. No production `location` branch is planned.

**Sources and dependencies:** [Approved proposal](MANIFEST_DRIVEN_RECONCILIATION_INPUTS.md) (`P-AC-4`, `P-AC-6`), phase plan (`VM-7`, `VM-8`), and the completed [Phase 3 task plan](MANIFEST_DRIVEN_RECONCILIATION_INPUTS_PHASE_3_TASK_PLAN.md). Phases 1–2 supply the manifest contract and eligibility checks; Phase 3 supplies the reviewed-decision and identity reference. Use temporary synthetic rows and mocked manifest, candidate, and verification responses. Phase 1's real `location` candidate check establishes service availability separately, not the outcome of this client workflow test.

**Acceptance criteria**

1. [x] `PH4-AC-1` (from `P-AC-6`): A mocked `location` manifest configures the declared `place_name` property without a type-specific Shape Shifter code change (`VM-7`).
2. [x] `PH4-AC-2` (from `P-AC-4`): Mocked review, export, normalization, and an unchanged rerun preserve the intended parent target ID and local `system_id` child links (`VM-8`).

## Repository Findings

**Repository basis:** 2026-11-05, `feature/manifest-driven-reconciliation-inputs` at `f058834f`. Uncommitted edits to `.vscode/settings.json`, the source proposal, and the phase plan were observed; the edited proposal and phase plan were used as the current planning inputs, but none of those edits were changed. Graphify was queried for the reconciliation workflow and narrowed to `ReconciliationService`; the findings below were checked against current code and tests.

| Evidence | Finding | Planning implication |
| --- | --- | --- |
| `frontend/src/utils/reconciliationManifest.ts::parseReconciliationManifest`, `getReconciliationCompatibility`; `frontend/src/components/reconciliation/SpecificationEditor.vue::availableProperties`, `loadRemoteTypes` | The parser indexes properties by exact supported type ID; the editor merges manifest properties with saved keys, uses the store's manifest, and has no type-specific `location` branch. Existing editor tests cover `site` properties and a zero-property `feature_type`, not the declared `location` property. | Extend the existing editor test with a mocked `location` manifest and fixture-only source column. Assert `place_name` is offered, an unrelated property is absent, and the selected source column is saved without changing production UI code. |
| `backend/app/services/reconciliation/service.py::ReconciliationService.ensure_reconciliation_eligibility`, `ReconciliationQueryService.create`; `backend/app/clients/reconciliation_client.py::ReconciliationQuery.to_dict` | Backend matching checks supported type and saved property IDs, then turns each mapped source-column value into `{"pid": "place_name", "v": value}` in the request's `properties` array. The business key independently indexes rows and decisions. | Declare `keys: [fixture_location_code]`, a `location_name` search label, and a distinct `fixture_place_name` source column. Assert exact query type, label, property ID, and value for each row, and that unsupported properties remain blocked by existing checks. |
| `backend/tests/integration/test_feature_type_reconciliation_workflow.py::TestFeatureTypeReconciliationWorkflow::test_feature_type_review_export_and_unchanged_rerun`; `backend/app/api/v1/endpoints/reconciliation.py` | Phase 3 creates a fixed parent and child through the authorized project API, mocks manifest/batch/verification calls, reviews decisions through protected routes, exports to a temporary sidecar, and normalizes twice offline. It tests *no* properties. | Follow that integration pattern for `location` in a separate **NEW** file, without extending or rewriting the Phase 3 classifier test. Assert a proposed candidate is not an accepted link. |
| `src/normalizer.py::ShapeShifter._apply_mapping_sidecar_links`; `src/reconciliation/mapping_model.py::MappingCatalog.committed_links_by_entity`; `backend/tests/api/v1/test_reconciliation_export.py` | Committed sidecar links write the target ID to the parent's configured `public_id`; child Core foreign keys retain the parent's local `system_id`. Existing export tests cover the offline rule for `site`. | Test `location_id` on the parent against the *same-named* child FK with different values, and compare the sidecar and normalization results on an unchanged rerun. |

## Scope

**In scope:** An editor component test for manifest-declared `location.place_name`, and one new isolated backend integration test for synthetic fixed `location` parent/child rows, property-bearing mocked requests, explicit review, candidate verification, sidecar export, offline normalization, and unchanged rerun. Fixture-only `fixture_location_code` identifies local rows; `location_name` is the search label; `fixture_place_name` supplies `place_name`. These are test columns, not a real provider schema recommendation.

**Out of scope:** Production changes to introduce a `location` rule; real provider-key selection; live matching or match-quality assessment; shared project sidecars; `site` grouped parity and developer-guide rewrite (Phase 5); SIMS import, adoption, or materialization. If the planned tests expose a conflicting production contract, stop and report it rather than broadening this phase.

**Affected components:** `frontend/src/components/reconciliation/__tests__/` and `backend/tests/integration/`. Existing manifest parser, editor, protected reconciliation routes, query builder, sidecar exporter, and Core normalizer are exercised but not planned for modification. No new runtime API, data migration, or project schema is required.

## Work Breakdown

### Area 1: Configure the declared property in the editor

**Objective:** A valid mocked manifest exposes `location` and only its declared `place_name` property, and the chosen local source column survives save.

**Affected code:** `frontend/src/components/reconciliation/__tests__/SpecificationEditor.test.ts` (existing); `frontend/src/components/reconciliation/SpecificationEditor.vue::availableProperties`, `frontend/src/utils/reconciliationManifest.ts::parseReconciliationManifest` (contracts exercised, not edited).

**Dependencies:** Phase 2 manifest-driven editor behavior, already present.

**Tasks:**

* [x] `T1.1` **Change:** Add a `location` case to the existing editor component tests, not to production type-selection logic.
  * **Target:** `frontend/src/components/reconciliation/__tests__/SpecificationEditor.test.ts` (manifest fixture, local columns, and `location` test).
  * **Current → required:** The existing mocked manifest serves `site.place_name` and zero properties for `feature_type` → include `location` in `defaultTypes` and `reconciliation.supportedTypes`, declare `place_name` for `location`, and test a local `location` specification mapping `place_name: fixture_place_name`.
  * **Implementation:** Give the test project a `location` entity and return `fixture_location_code`, `location_name`, and `fixture_place_name` as available fields. Select the `location` remote type in the component; assert its display name and `place_name` row appear, an unrelated property is absent, the source-field control offers `fixture_place_name`, and save sends `property_mappings: { place_name: 'fixture_place_name' }`. Preserve the existing `site` and zero-property test expectations; use a test-only manifest fixture rather than a hard-coded UI rule.
  * **Constraints:** The local key, label, and property source are three distinct fixture columns. Do not equate `defaultTypes` membership with reconciliation support or infer a provider schema from test data.
  * **Validation:** `V-1` (`VM-7`), `V-4`; expect exactly the declared property for `location` while existing editor and parser cases still pass.

**Completion evidence:** The editor selects `location` and saves its mapped `place_name` source with no production code diff.

### Area 2: Exercise property-bearing review and offline identities

**Objective:** Distinct local keys with a shared search label send distinct `place_name` values, and only an explicit accepted decision creates a stable target-ID link.

**Affected code:** `backend/tests/integration/test_location_reconciliation_workflow.py` **NEW**; existing `backend/tests/integration/test_feature_type_reconciliation_workflow.py` (pattern and identity reference), `backend/app/services/reconciliation/service.py::ReconciliationQueryService.create`, `ReconciliationService.export_to_mapping`, and `src/normalizer.py::ShapeShifter.normalize` (exercised, not edited).

**Dependencies:** Phase 3's completed identity reference; Area 1 confirms the mocked manifest property contract.

**Tasks:**

* [x] `T2.1` **Change:** Create an isolated property-assisted `location` fixture and assert the exact candidate queries.
  * **Target:** `backend/tests/integration/test_location_reconciliation_workflow.py` **NEW** (fixture, mocks, and workflow test setup).
  * **Current → required:** Phase 3's `feature_type` queries contain no properties → create a temporary API-registered fixed `location` with `public_id: location_id`, `keys: [fixture_location_code]`, and two rows with distinct `system_id`/local keys and distinct `fixture_place_name` values but the same `location_name` label. Add a fixed child depending on `location`, linked by the first parent's local `system_id`.
  * **Implementation:** Use `authorized_client`, `tmp_path`, and isolated service singletons as in Phase 3. Stub `ReconciliationClient.get_service_manifest` with `location` in both type lists and `{"name": "place_name", "entity_types": ["location"]}` in `extend.property_settings`; mock `reconcile_batch` and `verify_candidates` with a deterministic `location` candidate URI and target ID (test value `4233`). Register a `location`/`location_name` specification whose only mapping is `place_name: fixture_place_name`; run `/auto-reconcile-sync` and capture `ReconciliationQuery.to_dict()`. Assert each query has `type=location`, the shared label, and exactly its row's `{"pid": "place_name", "v": <distinct source value>}`; verify both fixture keys remain separate proposed decisions and no sidecar link exists yet.
  * **Constraints:** Do not call a live service, reuse shared project files, assume mocked candidate quality, or silently accept a high-scoring candidate. The child FK must be sourced from local `system_id`, not the mocked target ID.
  * **Validation:** `V-2` (`VM-7`, `VM-8`), `V-3`; mismapped or omitted properties and label-keyed decisions must fail the assertions.

* [x] `T2.2` **Change:** Review, verify, export, and compare offline results on an unchanged rerun.
  * **Target:** `backend/tests/integration/test_location_reconciliation_workflow.py` **NEW** (continuation of the workflow test).
  * **Current → required:** No `location` test spans accepted decision to normalized Core links → accept one fixture key through `/mapping` with the mocked `location` candidate URI and target ID, reject the other, preview keyed decisions, and call `/export-to-mapping` with exact mocked candidate verification.
  * **Implementation:** Assert a single owned, verified link under the accepted `fixture_location_code` in the temporary `<project>-mapping.yml`, with metadata `local_key=fixture_location_code` and `public_id=location_id`; assert no link for the rejected key or shared label. Repeat matching and exporting with the same rows and decisions; assert no new proposals or links and byte-identical sidecar content. Run two new `ShapeShifter` instances against the temporary project file while denying HTTP during normalization. Assert the accepted parent's `location_id=4233`, its original `system_id` and the child's `location_id` equal that original local ID rather than `4233`; the rejected parent has no mapped target ID. Compare both runs' parent identities and child links.
  * **Constraints:** Keep review explicit, candidate verification mocked but not bypassed, and normalization offline. Do not change Phase 3's `feature_type` test or the service's matching strategies.
  * **Validation:** `V-2` (`VM-8`), `V-3`, `V-4`; sidecar bytes, decision states, parent IDs, and child FK values stay identical on rerun.

**Completion evidence:** The new test demonstrates the manifest-declared property on the wire and the Phase 3 identity contract for a property-assisted type.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
| --- | --- | --- | --- |
| `PH4-AC-1` (`P-AC-6`, `VM-7`) | `T1.1`, `T2.1` | `V-1`, `V-2`, `V-4` | Editor offers `location.place_name` from the mocked manifest, saves its local source, and the backend sends the per-row value as `pid=place_name`; no `location`-specific production edit. |
| `PH4-AC-2` (`P-AC-4`, `VM-8`) | `T2.1`, `T2.2` | `V-2`, `V-3` | An explicit accepted key yields one verified link and parent target ID 4233; the child FK remains the parent's local `system_id`; unchanged matching, export, and both offline runs agree. |

## Validation And Testing

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
| --- | --- | --- | --- | --- | --- |
| `V-1` | Existing editor and parser tests plus new `location` case in `frontend/src/components/reconciliation/__tests__/SpecificationEditor.test.ts` | `cd frontend && pnpm exec vitest run src/components/reconciliation/__tests__/SpecificationEditor.test.ts src/utils/__tests__/reconciliationManifest.test.ts` | `PH4-AC-1`, `VM-7`; `site` and zero-property regressions | `location` exposes and saves only `place_name` from the manifest, not an unrelated property; all existing tests remain green. | Pass on 2026-11-05 after implementation: 18 tests across both files, including the new `location` case. |
| `V-2` | Mocked `location` review-to-normalization workflow in `backend/tests/integration/test_location_reconciliation_workflow.py` **NEW** | `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -p no:cacheprovider backend/tests/integration/test_location_reconciliation_workflow.py -q` | Both criteria, `VM-7`, `VM-8` | Exact per-key property values in candidate queries; no link without review; one verified keyed link; identical unchanged rerun and two offline parent/child identity results. | Pass on 2026-11-05: 1 test, exit 0. |
| `V-3` | Existing classifier, backend eligibility/export, and Core FK regression tests with the new workflow | `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -p no:cacheprovider backend/tests/integration/test_location_reconciliation_workflow.py backend/tests/integration/test_feature_type_reconciliation_workflow.py backend/tests/services/test_reconciliation_service.py backend/tests/api/v1/test_reconciliation_export.py tests/model/test_foreign_key_identity.py -q` | `PH4-AC-2`, Phase 3 identity reference, existing `site` export | All pass; no regression in manifest eligibility, reviewed export, or local child links. | Pass on 2026-11-05 after implementation: 35 tests across the five files, exit 0. |
| `V-4` | Confirm type-specific runtime files were not edited; check new test formatting, frontend lint and types | `git diff --exit-code f058834f -- frontend/src/components/reconciliation/SpecificationEditor.vue frontend/src/utils/reconciliationManifest.ts backend/app/services/reconciliation/service.py`; `.venv/bin/black --check backend/tests/integration/test_location_reconciliation_workflow.py && .venv/bin/isort --check-only backend/tests/integration/test_location_reconciliation_workflow.py`; `cd frontend && pnpm exec eslint src/components/reconciliation/__tests__/SpecificationEditor.test.ts && pnpm exec vue-tsc --noEmit` | `PH4-AC-1`, quality of both test changes | No type-specific production edits; formatting, lint, and type checks pass. | Pass on 2026-11-05: no production diff; `black`/`isort` clean; `eslint` no issues; `vue-tsc --noEmit` exit 0. Initial type errors in the new test were corrected and re-checked. |

The database-backed `backend/tests/integration/test_site_reconciliation_end_to_end.py` is excluded because it requires a disposable database and live Authority Service. The Phase 1 `location` availability check is separate from this mocked workflow. Phase 5 owns grouped pilot parity and documentation updates.

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Manifest-driven `location` editor regression | `frontend/src/components/reconciliation/__tests__/SpecificationEditor.test.ts` | `T1.1` | `V-1` (18 tests) and frontend checks in `V-4` pass; no runtime edit. |
| Temporary, mocked property-assisted workflow | `backend/tests/integration/test_location_reconciliation_workflow.py` **NEW** | `T2.1`, `T2.2` | `V-2`–`V-4` pass; 1 new test; no network or shared sidecar writes. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1 — configure property | Done | Phase 2 (present) | `T1.1` complete; `V-1` passes with 18 tests. |
| Area 2 — review and identities | Done | Phase 3 (complete), Area 1 contract | `T2.1`/`T2.2` complete; `V-2`/`V-3` pass. |

## Definition Of Done

* [x] `PH4-AC-1` and `PH4-AC-2` have completed task evidence and passing `VM-7`/`VM-8` checks (`V-1`–`V-3`).
* [x] Both work areas and both test deliverables are complete; `V-1`–`V-4` pass.
* [x] The property-bearing query uses `fixture_place_name` rather than the label or fixture key; only an explicit reviewed decision exports a verified link keyed by `fixture_location_code`.
* [x] Parent `location_id` holds the target ID while the child `location_id` holds the parent's local `system_id`, including on the unchanged rerun; normalization makes no HTTP requests.
* [x] The Phase 3 `feature_type` and existing `site` export/identity behaviors remain green; there is no `location`-specific production rule.
* [x] Any deviation or follow-up is documented, with no unresolved question affecting implementation or validation. If repository contracts differ from the verified targets above, stop and report the discrepancy rather than redesigning or expanding this phase.

## Risks And Open Questions

- **Fixture identity is not provider identity:** `fixture_location_code` and `fixture_place_name` are test-only. They verify key separation and property mapping but do not select columns for a real provider.
- **Mocks do not demonstrate match quality:** The deterministic candidate and verification responses prove Shape Shifter behavior only; do not substitute them for Phase 1's real service availability check.
