# Manifest-Driven Reconciliation Inputs — Phase 3 Task Plan

## Phase Summary

**Phase:** 3 — Validate Label-Only Reconciliation. **Readiness:** Validated for implementation. [Phase 3 of the phase plan](MANIFEST_DRIVEN_RECONCILIATION_INPUTS_PHASE_PLAN.md#phase-3-validate-label-only-reconciliation) is marked ready. This phase proves the existing generic client workflow for a zero-property `feature_type`; it does not select a business key for a real provider or evaluate Authority Service match quality.

**Goal:** With synthetic provider-shaped fixed rows and mocked Authority Service responses, demonstrate candidate review, an explicit operator decision, export by a fixture-local business key, offline normalization, and identical results on an unchanged rerun.

**Sources and dependencies:** [Approved proposal](MANIFEST_DRIVEN_RECONCILIATION_INPUTS.md) (`P-AC-4`), phase plan (`VM-5`, `VM-6`), [Phase 1 task plan](MANIFEST_DRIVEN_RECONCILIATION_INPUTS_PHASE_1_TASK_PLAN.md), and [Phase 2 task plan](MANIFEST_DRIVEN_RECONCILIATION_INPUTS_PHASE_2_TASK_PLAN.md). Phases 1 and 2 have completed their contract and eligibility work. Use a valid *mocked* manifest and candidate/verification responses, not the live service, SIMS, or a shared provider project. Keep matching and candidate verification mocked; acceptance is an explicit API decision and normalization remains offline.

**Acceptance criteria**

1. [x] `PH3-AC-1` (from `P-AC-4`): A mocked zero-property `feature_type` request returns a deterministic candidate, and the accepted decision is exported under the fixture's local key (`VM-5`).
2. [x] `PH3-AC-2` (from `P-AC-4`): Reviewed decisions export by the local business key; normalization and an unchanged rerun produce the intended parent `public_id` and unchanged local `system_id` child links (`VM-6`).

## Repository Findings

**Repository basis:** 2026-11-05, `feature/manifest-driven-reconciliation-inputs` at `5de9cbe0`. The uncommitted changes to `.vscode/settings.json`, the source proposal, and the phase plan were observed; the current, edited proposal and phase plan were used for planning, and none of these existing changes were modified. Graphify was queried for the reconciliation flow; its broad result was narrowed to `ReconciliationService` and checked against the source and tests below.

| Evidence | Finding | Planning implication |
| --- | --- | --- |
| `backend/app/services/reconciliation/service.py::ReconciliationService.ensure_reconciliation_eligibility`, `auto_reconcile_entity`; `backend/tests/services/test_reconciliation_service.py::test_auto_reconcile_entity_accepts_supported_type_with_no_properties` | The backend requires a valid manifest and supported type before matching. The existing `feature_type` unit test proves an empty mapping omits `properties` from the query and creates a proposal, but uses `site` as its local entity and stops before review/export. | Use a real local `feature_type` fixture and a mocked manifest with `reconciliation.supportedTypes: [feature_type]`, a corresponding `defaultTypes` entry, and `extend.property_settings: []`; exercise the whole workflow. |
| `backend/app/services/reconciliation/service.py::ReconciliationQueryService.index_rows`, `create`, `ReconciliationService.get_resolved_source_data`; `src/reconciliation/mapping_model.py::encode_local_key` | Queries use the configured target field as the label, but decisions and candidate lists use the entity's declared business key. Missing or duplicate keys produce row errors. | Declare fixture-only `keys: [fixture_feature_code]`, distinct from `feature_type_name`; use two different codes with the same label to detect accidental label-keying. Do not infer this key from a real provider or use `system_id` as the decision key. |
| `backend/app/api/v1/endpoints/reconciliation.py::create_registry`, `auto_reconcile_entity_sync`, `export_reconciliation_to_mapping`; `backend/app/services/reconciliation/service.py::ReconciliationService.update_mapping`, `export_to_mapping` | The protected API creates a specification, proposes candidates without accepting them, records explicit decisions, verifies accepted candidate URIs at export, and writes committed links to `<project>-mapping.yml`. | Create the test project through `POST /api/v1/projects` with `authorized_client`; mock manifest, batch results, and exact candidate verification. Assert a proposed candidate is not exported before a decision, then accept one key and reject the other through `/mapping`. |
| `backend/tests/api/v1/test_reconciliation_decisions.py::test_duplicate_labels_have_independent_review_actions`, `test_export_verifies_an_accepted_candidate`; `backend/tests/api/v1/test_reconciliation_export.py::test_exported_links_normalize_offline_with_stable_parent_ids_and_child_foreign_keys` | Existing tests provide isolated route/verification and fixed-parent/child normalization patterns, but only for `site`. The separate `backend/tests/integration/test_site_reconciliation_end_to_end.py` requires a disposable database and live Authority Service. | Reuse the isolated patterns, not the live fixture or a copied `site` scenario. A single new offline integration test file can cover `feature_type` without production edits. |
| `src/normalizer.py::ShapeShifter._apply_mapping_sidecar_links`; `src/reconciliation/mapping_model.py::MappingCatalog.committed_links_by_entity`; `src/AGENTS.md` | Only committed links populate the parent's configured `public_id`; child Core foreign keys reference the parent's local `system_id`, not the mapped target ID. | Assert both identity tiers and the unchanged rerun explicitly. Do not test change-request target-ID substitution in this phase. |

## Scope

**In scope:** One new backend integration test module containing a temporary, API-created project with synthetic `feature_type` parent and fixed child rows; mocked manifest, candidate batch, and verification; protected review/export requests; two offline normalization runs; negative evidence that a shared label cannot merge decisions for distinct fixture keys. Reuse existing backend and Core APIs without type-specific client rules.

**Out of scope:** Production changes unless a Phase 3 test exposes a directly related defect (stop and report conflicting repository state before redesigning); real provider key selection or Arbodat fixtures; live database matching, SIMS adoption, change-request packaging, `location` property mapping (Phase 4), grouped `site` parity and documentation changes (Phase 5), or edits to shared project sidecars.

**Affected components:** `backend/tests/integration/` test coverage; existing project creation, reconciliation and export endpoints; `ReconciliationClient` mock points; `ShapeShifter.normalize()` and mapping sidecar as exercised contracts. No new runtime API, config schema, or migration is planned.

## Work Breakdown

### Area 1: Configure and review a label-only classifier

**Objective:** Candidate requests have no `properties`, and two rows with the same search label retain separate keyed review states.

**Affected code:** `backend/tests/integration/test_feature_type_reconciliation_workflow.py` **NEW**; existing `backend/tests/conftest.py::authorized_client`, `backend/app/services/reconciliation/service.py::ReconciliationQueryService.create`, `backend/app/clients/reconciliation_client.py::ReconciliationClient`.

**Dependencies:** Phases 1–2 contract and matching enforcement, already present in this repository.

**Tasks:**

* [x] `T1.1` **Change:** Create an isolated provider-shaped fixture and stub the service contract.
  * **Target:** `backend/tests/integration/test_feature_type_reconciliation_workflow.py` **NEW** (fixture and test setup).
  * **Current → required:** Only a `site` review-to-normalization test exists; the `feature_type` service unit test substitutes `site` rows → an API-created `feature_type` fixed parent with `public_id: feature_type_id`, `keys: [fixture_feature_code]`, `feature_type_name` search column, and two rows such as `(system_id=10001, fixture_feature_code=FT-001, feature_type_name=Trench)` and `(10002, FT-002, Trench)`. Add a fixed child with `depends_on: [feature_type]` and a FK from a local `feature_type_ref` value `10001` to parent `system_id`; its output `feature_type_id` must remain a Core link.
  * **Implementation:** Use `authorized_client` and `tmp_path` for project creation/registration and files; save a `feature_type`/`feature_type_name` specification with empty `property_mappings`. Stub `ReconciliationClient.get_service_manifest` with valid `defaultTypes`, `reconciliation.supportedTypes`, and an empty `extend.property_settings` array. Stub `reconcile_batch` to return a deterministic candidate URI ending in `/feature_type/25` for each query, and stub `verify_candidates` with an `exists` result for that exact URI and `aggregate_id=25`. Isolate backend service singletons as in existing reconciliation route tests. The mocked ID is test data, not evidence of real matching.
  * **Constraints:** Keep the fixture key distinct from the label and `system_id`; no network, real provider YAML, shared sidecar, or target-model uniqueness assumption.
  * **Validation:** `V-1` and `V-3`: project and spec create successfully, manifest is consumed, and candidate verification is deterministic.

* [x] `T1.2` **Change:** Exercise candidate review and explicit decision/export by the local key.
  * **Target:** `backend/tests/integration/test_feature_type_reconciliation_workflow.py` **NEW** (test `test_feature_type_review_export_and_unchanged_rerun`).
  * **Current → required:** Existing feature-type test stops at proposals → call `/auto-reconcile-sync`, inspect the captured `ReconciliationQuery.to_dict()` for `type=feature_type`, `query=Trench`, and **no `properties`**, and assert independent `FT-001` and `FT-002` proposed rows. Confirm proposal alone produces no committed reconciliation link. Accept `FT-001` with candidate URI and target ID 25 through `/mapping`; reject `FT-002`; export via `/export-to-mapping`.
  * **Implementation:** Assert decision states in the saved catalog and preview; the mock verification receives `type=feature_type` and the selected URI. Assert exported sidecar metadata `local_key=fixture_feature_code`, `public_id=feature_type_id`, and exactly one committed, owned, verified link under `FT-001` with target ID 25; no `FT-002` link and no label-keyed link. Retain the saved sidecar bytes for the unchanged-export assertion.
  * **Constraints:** No auto-acceptance, even for a 100% candidate. Candidate verification must be mocked, not skipped; failure must not look like a verified export.
  * **Validation:** `V-1` (`VM-5`) and `V-3`: proposal-before-review, duplicate-label independence, exact verification, and key-based sidecar assertions pass.

**Completion evidence:** `V-1` demonstrates `PH3-AC-1` without live-service access.

### Area 2: Prove offline identities and unchanged rerun

**Objective:** A reviewed target ID changes the parent's public ID only; a second identical run changes neither decisions nor Core child links.

**Affected code:** `backend/tests/integration/test_feature_type_reconciliation_workflow.py` **NEW**; existing `src/normalizer.py::ShapeShifter.normalize`, `_apply_mapping_sidecar_links`, and `backend/app/services/reconciliation/service.py::ReconciliationService.auto_reconcile_entity`, `export_to_mapping`.

**Dependencies:** Area 1 accepted and exported decision.

**Tasks:**

* [x] `T2.1` **Change:** Assert the exported mapping is applied offline and is repeatable.
  * **Target:** `backend/tests/integration/test_feature_type_reconciliation_workflow.py` **NEW** (continuation of `test_feature_type_review_export_and_unchanged_rerun`).
  * **Current → required:** Existing `site` tests check this contract, but no `feature_type` test spans export and normalization → construct a fresh `ShapeShifter` from the isolated project's `shapeshifter.yml`, await `normalize()`, and compare parent rows by `fixture_feature_code`: `FT-001` retains local `system_id=10001` and receives `feature_type_id=25`; `FT-002` retains `system_id=10002` and has no target ID. The child FK named `feature_type_id` equals `10001`, **not** 25.
  * **Implementation:** Repeat candidate matching/export with unchanged source rows and final decisions; assert no newly proposed decision, no additional exported/removed link, unchanged catalog decision statuses and byte-identical sidecar. Normalize with a new instance and compare both parent identity columns and child FK to the first result. Deny `httpx.AsyncClient.request` during normalization, following the existing offline regression test.
  * **Constraints:** Keep child links local even though the FK column and parent `public_id` share the name `feature_type_id`. An unchanged rerun must not overwrite an operator decision or modify a committed sidecar timestamp.
  * **Validation:** `V-2` (`VM-6`) and `V-3`: assert parent and child values, no normalization HTTP, identical repeat results and sidecar.

**Completion evidence:** `V-2` proves `PH3-AC-2` using temporary files and no external service.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
| --- | --- | --- | --- |
| `PH3-AC-1` (`P-AC-4`, `VM-5`) | `T1.1`, `T1.2` | `V-1`, `V-3` | Mocked zero-property query has no `properties`; distinct local keys receive independent proposed decisions; only reviewed `FT-001` exports the verified target ID under its fixture key. |
| `PH3-AC-2` (`P-AC-4`, `VM-6`) | `T1.2`, `T2.1` | `V-2`, `V-3` | Parent `feature_type_id=25` at `FT-001`, `system_id=10001` and child `feature_type_id=10001` remain local; unaccepted row has no target ID; unchanged export and two offline normalization runs agree. |

## Validation And Testing

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
| --- | --- | --- | --- | --- | --- |
| `V-1` | Mocked feature-type candidate review and export in `backend/tests/integration/test_feature_type_reconciliation_workflow.py` **NEW**, including equal labels and different keys | `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -p no:cacheprovider backend/tests/integration/test_feature_type_reconciliation_workflow.py -q` | `PH3-AC-1`, `VM-5` | Stubbed manifest with zero properties; `Trench` queries omit `properties`, both keys remain proposed until reviewed, only accepted `FT-001` verifies and exports under its fixture code. | Pass: `1 passed` on 2026-11-05. |
| `V-2` | Offline normalization, unchanged rerun, and local child FK in the same **NEW** test module | Same command as `V-1`; inspect assertions for both normalization runs and no-network guard. | `PH3-AC-2`, `VM-6` | Target ID 25 on accepted parent only, local child FK 10001 on both runs, unchanged sidecar bytes and decisions after repeated matching/export. | Pass: same module run, `1 passed` on 2026-11-05. |
| `V-3` | Existing backend/Core regressions and new workflow together | `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -p no:cacheprovider backend/tests/integration/test_feature_type_reconciliation_workflow.py backend/tests/services/test_reconciliation_service.py backend/tests/api/v1/test_reconciliation_decisions.py backend/tests/api/v1/test_reconciliation_export.py tests/reconciliation/test_mapping_sidecar.py tests/model/test_foreign_key_identity.py -q` | Both criteria, existing `site` decision/export and identity behavior | All tests pass; no regression in eligibility, manual review, export, or parent/child identity separation. | Pass: `150 passed` on 2026-11-05 (149 existing baseline tests plus the new workflow test). |
| `V-4` | Python test formatting | `.venv/bin/black --check backend/tests/integration/test_feature_type_reconciliation_workflow.py && .venv/bin/isort --check-only backend/tests/integration/test_feature_type_reconciliation_workflow.py` | Quality of **NEW** test module | Both checks pass. | Pass on 2026-11-05 after Black and isort were applied. |

The database-backed `backend/tests/integration/test_site_reconciliation_end_to_end.py` is intentionally excluded: it requires `SIMS_INTEGRATION_DB=1`, a disposable database, and a live service. Phase 1 recorded separate read-only service candidate checks; they do not prove this mocked workflow. No frontend or production code change is planned, so frontend build checks do not apply.

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Isolated classifier fixture, mock service responses, review/export and rerun checks | `backend/tests/integration/test_feature_type_reconciliation_workflow.py` **NEW** | `T1.1`, `T1.2`, `T2.1` | `V-1`–`V-4` pass; temporary project and sidecar are scoped to the test. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1 — configure and review | Done | Phases 1–2 (completed) | `T1.1`, `T1.2` complete. `V-1` and `V-3` pass; the captured queries omit `properties`, both keys stay proposed until reviewed, and only `FT-001` verifies and exports. |
| Area 2 — identities and rerun | Done | Area 1 | `T2.1` complete. `V-2` and `V-3` pass; parent `feature_type_id=25` and child `feature_type_id=10001` are identical on two offline runs, and the rerun leaves decisions and sidecar bytes unchanged. |

## Definition Of Done

* [x] `PH3-AC-1` and `PH3-AC-2` each have completed task evidence and passing `VM-5`/`VM-6` checks (`V-1`–`V-3`).
* [x] Every work area and the **NEW** test deliverable is complete; `V-1`–`V-4` pass.
* [x] The duplicate-label fixture proves the local key, not the label or `system_id`, indexes decisions and exported links; no candidate is automatically accepted.
* [x] The target ID is on the accepted parent's `public_id`, while Core child foreign keys retain the parent's local `system_id`; both results and the exported sidecar stay unchanged on rerun.
* [x] Existing `site` decision/export and offline normalization rules have no regression; no network or shared project files are used by the new test.
* [x] Any deviation or follow-up is documented, and no unresolved decision affects implementation or validation. If current repository contracts differ from the verified targets above, stop and report the discrepancy rather than redesigning or expanding this phase.

## Risks And Open Questions

- **Fixture identity is not provider identity:** `fixture_feature_code` is test-only. It demonstrates key-based behavior but does not choose a real provider key or establish uniqueness in an external dataset.
- **Mocks do not demonstrate match quality:** Stubbed results and candidate verification prove client behavior only. Keep the Phase 1 real-service check separate; do not claim a live workflow from this test.

## Execution Record

Executed on 2026-11-05 against `feature/manifest-driven-reconciliation-inputs` at `5de9cbe0`. The pre-existing edits to `.vscode/settings.json`, the source proposal, and the phase plan were not modified.

| Check | Command | Result |
| --- | --- | --- |
| `V-1`, `V-2` | `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -p no:cacheprovider backend/tests/integration/test_feature_type_reconciliation_workflow.py -q` | Pass: `1 passed` |
| `V-3` | Same pytest command with the five existing reconciliation, sidecar, and identity test files | Pass: `150 passed` |
| `V-4` | `.venv/bin/black --check ... && .venv/bin/isort --check-only ...` | Pass: no changes required after formatting was applied |

Observed behavior in the new test:

- Both `Trench` queries carry `type=feature_type` with no `properties` key; both `FT-001` and `FT-002` stay `proposed` after matching, and no mapping sidecar exists yet.
- Accepting `FT-001` at target ID 25 and rejecting `FT-002` produces exactly one verified, owned link under `FT-001`; `FT-002` and `Trench` have no links.
- The unchanged rerun proposes no decisions and exports nothing, leaving the catalog statuses and sidecar bytes identical.
- Two offline normalization runs give `FT-001 -> system_id 10001, feature_type_id 25` and `FT-002 -> system_id 10002, feature_type_id None`, with the child foreign key `feature_type_id` equal to `10001`.

No production code, configuration, or shared project sidecar was changed.
