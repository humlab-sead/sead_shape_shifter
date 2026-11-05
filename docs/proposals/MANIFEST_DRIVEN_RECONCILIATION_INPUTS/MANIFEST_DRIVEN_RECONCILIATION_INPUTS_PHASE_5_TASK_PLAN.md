# Manifest-Driven Reconciliation Inputs — Phase 5 Task Plan

> **Later change:** after this phase completed, the two guides referenced below
> (`docs/other/RECONCILIATION_SETUP_GUIDE.md` and `docs/other/RECONCILIATION_WORKFLOW.md`)
> were merged into `docs/other/RECONCILIATION_GUIDE.md`. The statements in this
> record describe the documents as they were during Phase 5.

## Phase Summary

**Phase:** 5 — Validate Grouped Parity and Document Configuration. **Readiness:** Validated for implementation. [Phase 5 of the phase plan](MANIFEST_DRIVEN_RECONCILIATION_INPUTS_PHASE_PLAN.md#phase-5-validate-grouped-parity-and-document-configuration) requires Phases 3 and 4 to complete, and both are complete.

**Goal:** Prove the manifest-driven workflow keeps the `site` MVP, the zero-property `feature_type` pilot, and the property-bearing `location` pilot consistent on review, keyed export, unchanged rerun, and offline parent/child identity; then publish the configuration procedure that the implementation now follows.

**Sources and dependencies:** [Approved proposal](MANIFEST_DRIVEN_RECONCILIATION_INPUTS.md) (`P-AC-1`, `P-AC-4`, `P-AC-7`, `P-AC-8`), phase plan (`VM-9`, `VM-10`), and the completed [Phase 3](MANIFEST_DRIVEN_RECONCILIATION_INPUTS_PHASE_3_TASK_PLAN.md) and [Phase 4](MANIFEST_DRIVEN_RECONCILIATION_INPUTS_PHASE_4_TASK_PLAN.md) task plans. Phases 1–2 supply the manifest contract and eligibility checks; Phases 3–4 supply the two mocked pilot workflows. Phase 5's stated readiness condition ("Requires Phases 3 and 4 to complete") is satisfied: both task plans record completed scope and passing validation. Keep real Authority Service checks separate and read-only; they do not gate this phase's mocked workflow acceptance.

**Acceptance criteria**

1. [x] `PH5-AC-1` (from `P-AC-1`, `P-AC-8`): The `site` workflow and MVP review, sidecar precedence, and offline-normalization rules remain unchanged (`VM-9`).
2. [x] `PH5-AC-2` (from `P-AC-4`): Both pilot outcomes remain identical on unchanged reruns, including target IDs on parent `public_id` columns and local `system_id` Core child links (`VM-9`).
3. [x] `PH5-AC-3` (from `P-AC-7`): The developer guide describes the implemented configuration procedure with a working type pair and distinguishes mocked workflow tests from real service availability checks (`VM-10`).

## Repository Findings

**Repository basis:** 2026-11-05, `feature/manifest-driven-reconciliation-inputs` at `7e42b720`. Uncommitted edits to `.vscode/settings.json`, the source proposal, and the phase plan were observed; the edited proposal and phase plan were used as planning inputs and none of those edits were changed. Graphify was queried for the grouped reconciliation workflow and developer-guide nodes; the findings below were checked against current code, tests, and documentation.

| Evidence | Finding | Planning implication |
| --- | --- | --- |
| `backend/tests/integration/test_feature_type_reconciliation_workflow.py::TestFeatureTypeReconciliationWorkflow::test_feature_type_review_export_and_unchanged_rerun`; `backend/tests/integration/test_location_reconciliation_workflow.py::TestLocationReconciliationWorkflow::test_location_review_export_and_unchanged_rerun` | Phases 3 and 4 each provide one deterministic, self-contained workflow using a temporary API-created project, mocked manifest/candidates/verification, keyed review, sidecar export, unchanged rerun, and two offline normalizations. Each file carries its own constants and helpers. No single test compares the three types together. | Add one **NEW** grouped, parametrized module that covers `site`, `feature_type`, and `location` through the same workflow. Do not modify the Phase 3 or Phase 4 tests; their scenarios remain the pilot reference. |
| `backend/tests/api/v1/test_reconciliation_export.py::test_export_counts_created_and_protected_links_and_skips_noop_writes`; `::test_exported_links_normalize_offline_with_stable_parent_ids_and_child_foreign_keys`; `backend/tests/api/v1/test_reconciliation_decisions.py::test_duplicate_labels_have_independent_review_actions`; `tests/reconciliation/test_mapping_sidecar.py::test_replace_entity_manual_links_replaces_only_manual_links` | Existing tests cover `site` manual-link precedence, sidecar ownership, operator review, and offline parent/child identity. They are route/unit-level and are not grouped with the two pilot workflows. | Keep these tests as the `site` MVP precedence and offline-rule evidence. Run them in the grouped regression command rather than duplicating manual-link setup in the new module. |
| `backend/app/services/reconciliation/service.py::ReconciliationService.ensure_reconciliation_eligibility`; `backend/app/services/reconciliation/service.py::ReconciliationQueryService.create`; `backend/app/clients/reconciliation_client.py::ReconciliationQuery.to_dict` | Matching requires a valid manifest, a supported type, and declared property IDs; each mapped source-column value is sent as `{"pid": <property>, "v": <value>}`. A mapping with no properties produces a query without a `properties` key. | The grouped test can use one mocked manifest shape per case: zero property settings for `feature_type`, and one `place_name` setting for `site` and `location`. Assert property presence and per-row values explicitly. |
| `src/normalizer.py::ShapeShifter.normalize`, `ShapeShifter._apply_mapping_sidecar_links`; `src/reconciliation/mapping_model.py::MappingCatalog.committed_links_by_entity` | Committed sidecar links write the target ID to the parent's configured `public_id`; child Core foreign keys keep the parent's local `system_id`. Normalization is offline. | Assert the parent target ID and the child's local foreign key in every grouped case and compare two offline runs. |
| `docs/DEVELOPMENT.md` (`## Extending the System`); `docs/README.md` | The developer guide is exactly 1800 words, has no reconciliation configuration procedure, and lists only loaders, validators, ingesters, and endpoints under extension guidance. | Add a concise procedure under `## Extending the System`; keep detailed reference material in companion guides to stay under the 2500-word limit. |
| `docs/other/RECONCILIATION_SETUP_GUIDE.md` (`Entity Specification Fields`, `Available Service Types`, `Available Properties (by Entity Type)`, troubleshooting entries) | The guide still describes `remote.service_type` as coming from `defaultTypes`, presents `defaultTypes` entries as usable service types, and hard-codes property lists by type. Those statements contradict `reconciliation.supportedTypes` and `extend.property_settings`. | Correct only the contradictory manifest-support statements. Leave the guide's UI workflow and unrelated configuration content unchanged. |
| `frontend/src/utils/reconciliationManifest.ts::parseReconciliationManifest`, `getReconciliationCompatibility`; `frontend/src/components/reconciliation/SpecificationEditor.vue::availableProperties`, `loadRemoteTypes` | The editor reads supported types from the manifest, derives properties by exact type membership, shows a manifest error, and blocks matching when compatibility is unknown or unsupported. | Documentation must describe this behavior; no frontend code change is planned. |
| `Makefile::check-doc-links`; `scripts/check_doc_links.sh` | Documentation links are checked locally and currently pass. | Run the link check for the two documentation edits. |

## Scope

**In scope:** One new grouped backend integration test module covering `site`, `feature_type`, and `location` with synthetic fixed rows and mocked Authority Service responses; a concise configuration procedure in `docs/DEVELOPMENT.md`; narrow corrections to contradictory manifest-support statements in `docs/other/RECONCILIATION_SETUP_GUIDE.md`.

**Out of scope:** Production runtime changes; frontend changes; edits to the Phase 3 or Phase 4 workflow tests; new manifest fields; live Authority Service or database calls; writes to shared project sidecars; `docs/other/RECONCILIATION_WORKFLOW.md`'s older configuration shape; SIMS adoption, change-request packaging, or materialization. If a grouped case exposes a production contract that contradicts this plan, stop and report it instead of redesigning or widening the phase.

**Affected components:** `backend/tests/integration/` test coverage; `docs/DEVELOPMENT.md`; `docs/other/RECONCILIATION_SETUP_GUIDE.md`. Existing project creation, reconciliation review/export routes, query builder, sidecar exporter, and Core normalizer are exercised but not modified.

## Work Breakdown

### Area 1: Prove grouped parity across the three remote types

**Objective:** One parametrized test runs the same manifest-driven workflow for `site`, `feature_type`, and `location` and shows the same review, keyed-link, rerun, and identity outcomes.

**Affected code:** `backend/tests/integration/test_manifest_driven_reconciliation_grouped_parity.py` **NEW**; existing Phase 3 and Phase 4 workflow tests (pattern and pilot reference, not edited); existing `backend/tests/conftest.py::authorized_client`; existing reconciliation and normalization services (exercised, not edited).

**Dependencies:** Phases 3 and 4 complete; Phases 1–2 manifest contract and eligibility checks present.

**Tasks:**

* [x] `T1.1` **Change:** Create the grouped case table, synthetic fixtures, and deterministic service mocks.
  * **Target:** `backend/tests/integration/test_manifest_driven_reconciliation_grouped_parity.py` **NEW** (module constants, case table, fixtures, mock installer, project and specification helpers).
  * **Current → required:** Only separate `feature_type` and `location` modules exist; neither includes `site`, and no test compares the three → define a `CaseConfig`-style table with three entries:
    - `site`: project `phase5_grouped_site`, entity `site`, local key `fixture_site_code`, target field `site_name`, `public_id: site_id`, property `place_name` from `fixture_place_name`, target ID `101`.
    - `feature_type`: project `phase5_grouped_feature_type`, entity `feature_type`, local key `fixture_feature_code`, target field `feature_type_name`, `public_id: feature_type_id`, no properties, target ID `25`.
    - `location`: project `phase5_grouped_location`, entity `location`, local key `fixture_location_code`, target field `location_name`, `public_id: location_id`, property `place_name` from `fixture_place_name`, target ID `4233`.
  * **Implementation:** For each case, build a parent `type: fixed` entity with `public_id`, `keys: [<local key>]`, columns `[system_id, <public_id>, <local key>, <target field>]` plus the property source column when the case has a property, and two rows with distinct local keys and the shared search label `Trench` (property source values also distinct). Add a fixed `sample` child with `depends_on: [<entity>]`, a local `<entity>_ref` extra column set to the first parent's `system_id`, and a `foreign_keys` entry whose remote key is the parent's `system_id`. Create the project through `POST /api/v1/projects` with `authorized_client`, `tmp_path`, and a monkeypatched `settings.PROJECTS_DIR`. Register the specification through `POST /api/v1/projects/{project}/reconciliation/mapping-registry` with `remote.service_type` set to the case entity and `property_mappings` empty or `{place_name: fixture_place_name}`. Stub `ReconciliationClient.get_service_manifest` with `defaultTypes` containing an OpenRefine-only `taxon` entry plus the case entity, `reconciliation.supportedTypes: [<entity>]`, and `extend.property_settings` empty for `feature_type` or `[{name: "place_name", entity_types: [<entity>]}]` for the other cases. Stub `reconcile_batch` to return one deterministic candidate URI per query ending in the case target ID, and `verify_candidates` to return `exists` with that target ID; capture every `ReconciliationQuery.to_dict()`.
  * **Constraints:** Keep fixture keys distinct from the search label and from `system_id`. Do not use shared project files, real provider YAML, live services, or assume the mocked candidate proves match quality. Reset the project, validation, and YAML service singletons as the Phase 3/4 tests do.
  * **Validation:** `V-1`, `V-2`; project and specification creation succeed for all three cases, and captured queries show the expected type, label, and property shape.

* [x] `T1.2` **Change:** Assert operator review, keyed export, unchanged rerun, and offline identities for every case.
  * **Target:** `backend/tests/integration/test_manifest_driven_reconciliation_grouped_parity.py` **NEW** (parametrized workflow test and assertions).
  * **Current → required:** Pilot tests prove each workflow separately → one parametrized test proves the same contract for all three types and compares outcomes across the two pilots.
  * **Implementation:** Call `/auto-reconcile-sync`; assert `200`, `total == 2`, `proposed == 2`, candidate keys equal the two local keys, and the manifest was consumed. Assert each captured query has the case `type` and the shared `Trench` label. For `feature_type`, assert `properties` is absent; for `site` and `location`, assert exactly one `{"pid": "place_name", "v": <that row's property source value>}` per query and that the property values are the two distinct fixture values, not the shared label. Assert no mapping sidecar exists before review and both catalog decisions are `proposed`. Accept one local key through `/mapping` with the deterministic candidate URI and case target ID; reject the other. Assert the catalog decisions. Export through `/export-to-mapping`; assert `exported == 1`, the verification call received the case entity and candidate URI, and the sidecar has `local_key`, `public_id`, one link keyed by the accepted local key with that target ID, the expected owner, `committed_at`/`verified_at`, and no link keyed by `Trench`. Rerun `/auto-reconcile-sync`; assert `proposed == 0` and unchanged catalog decisions. Export again; assert `exported == 0`, `removed == 0`, and byte-identical sidecar content. Deny `httpx.AsyncClient.request`, normalize twice with fresh `ShapeShifter` instances, and assert for both runs that the accepted parent keeps its original `system_id` and gains the case target ID in `public_id`, the rejected parent has no target ID, and the child foreign key equals the accepted parent's local `system_id` rather than the target ID. Assert both runs return identical parent identities and child links.
  * **Constraints:** No automatic acceptance, even for a 100% mocked candidate. Candidate verification stays mocked but not bypassed. Normalization stays offline. Do not edit the Phase 3 or Phase 4 tests or add a type-specific production rule.
  * **Validation:** `V-1` (`VM-9`), `V-2`, `V-4`; the three cases pass and the `feature_type`/`location` rerun comparisons match.

**Completion evidence:** `V-1` shows one command producing the same reviewed-decision, keyed-link, unchanged-rerun, and local-child-identity results for `site`, `feature_type`, and `location`.

### Area 2: Document the manifest-driven configuration procedure

**Objective:** A developer can configure a reconciliation specification from the manifest without relying on hard-coded type or property lists.

**Affected code:** `docs/DEVELOPMENT.md` (`## Extending the System`); `docs/other/RECONCILIATION_SETUP_GUIDE.md` (`Entity Specification Fields`, `Available Service Types`, `Available Properties (by Entity Type)`, troubleshooting).

**Dependencies:** Areas 1's verified behavior and the Phase 1–4 implementation already present.

**Tasks:**

* [x] `T2.1` **Change:** Add a concise reconciliation-configuration procedure to the developer guide.
  * **Target:** `docs/DEVELOPMENT.md`, new subsection under `## Extending the System`, for example `### Configure a Reconciliation Specification`.
  * **Current → required:** The guide has no reconciliation procedure → document the implemented sequence in no more than about 250 words:
    1. Read `GET /reconcile`; choose an ID from `reconciliation.supportedTypes`; use `defaultTypes` only for the display name, not as a support list.
    2. Derive properties from `extend.property_settings` entries whose `entity_types` contains the selected ID; a valid zero-property type is usable.
    3. In Reconcile → Configuration, select the local entity and search field, select the remote type, declare the entity's business `keys`, and map declared properties to source columns or none.
    4. State that saved mappings not declared for the selected type remain visible but block matching until explicitly removed or remapped; a manifest outage shows an error, keeps saved values, and blocks matching; there is no fallback list.
    5. Verify one real match request, because a manifest entry proves implemented matching, not database access or match quality.
    6. Review and export, then normalize offline; the target ID goes to the parent's `public_id` and child Core foreign keys keep the parent's local `system_id`.
    7. Add a regression test for the new specification.
  * **Implementation:** Use the confirmed `site` pair as the worked example: local entity `site` (for example the Arbodat test project) → remote type `site`, search field `site_name`, business key `[Fustel, EVNr]`, and property examples `place_name` ← `site_name` and `national_id` ← `national_site_identifier`. Label the example as test-project data. Link to [RECONCILIATION_SETUP_GUIDE.md](../../other/RECONCILIATION_SETUP_GUIDE.md) for detailed field reference and to [USER_GUIDE.md](../../USER_GUIDE.md#8-reconciliation-and-mapping) for the operator workflow. Name the mocked workflow tests (`backend/tests/integration/test_feature_type_reconciliation_workflow.py`, `test_location_reconciliation_workflow.py`, and the new grouped module) and state that Phase 1's real service checks are separate availability evidence.
  * **Constraints:** Preserve the document's existing structure. The guide is currently 1800 words; keep the added text concise and the total under 2500 words. Do not describe planned behavior as shipped. Do not claim that `defaultTypes` membership means reconciliation support.
  * **Validation:** `V-3` (`VM-10`); the section names the working pair, covers supported types, properties, business keys, saved-mapping recovery, manifest failure, identity behavior, and the mocked-versus-real distinction.

* [x] `T2.2` **Change:** Correct the contradictory manifest-support statements in the companion setup guide.
  * **Target:** `docs/other/RECONCILIATION_SETUP_GUIDE.md` (`Entity Specification Fields` table row for `remote.service_type`, the `service_type` YAML comment, `#### Available Service Types`, `#### Available Properties (by Entity Type)`, and the troubleshooting entries that say to check a static type or property list).
  * **Current → required:** `remote.service_type` is described as coming from `defaultTypes`; `defaultTypes` entries are presented as usable service types; properties are listed in fixed per-type blocks → say that the usable type list is `reconciliation.supportedTypes`, `defaultTypes` supplies display names only, and properties come from `extend.property_settings` filtered by exact `entity_types` membership.
  * **Implementation:** Replace the static service-type list with the rule plus a short example (for example, `site`, `feature_type`, and `location` are implemented in the current service contract). Replace the hard-coded per-type property lists with the manifest rule and state that a supported type with no property entries is valid. Update the field table and YAML comment to point at `reconciliation.supportedTypes`. In troubleshooting, replace "verify the service type matches available types" with checking `reconciliation.supportedTypes`, and replace property-list checks with `extend.property_settings`.
  * **Constraints:** Do not rewrite the guide's UI workflow, mapping structure, or unrelated configuration shape. Do not add a new static list that will drift from the manifest. Leave `docs/other/RECONCILIATION_WORKFLOW.md` unchanged; its older configuration shape is a separate documentation gap.
  * **Validation:** `V-3`; no section presents `defaultTypes` as a support guarantee or hard-codes a per-type property list as authoritative, and the documentation link check passes.

**Completion evidence:** A developer following `docs/DEVELOPMENT.md` can select a supported type, derive its properties, preserve unsupported saved mappings, and verify the result, and the companion guide no longer contradicts the manifest contract.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
| --- | --- | --- | --- |
| `PH5-AC-1` (`P-AC-1`, `P-AC-8`, `VM-9`) | `T1.1`, `T1.2` | `V-1`, `V-2` | The grouped `site` case passes the same review, keyed sidecar, and offline-identity assertions; existing `site` manual-precedence, decision, sidecar, and normalization tests pass unchanged. |
| `PH5-AC-2` (`P-AC-4`, `VM-9`) | `T1.1`, `T1.2` | `V-1`, `V-2` | `feature_type` and `location` produce no new proposals on rerun, byte-identical sidecars, the same parent target IDs on `public_id`, and unchanged child links to the parent's local `system_id`. |
| `PH5-AC-3` (`P-AC-7`, `VM-10`) | `T2.1`, `T2.2` | `V-3` | The developer guide documents the manifest procedure with a confirmed `site` pair, and the companion guide no longer presents `defaultTypes` or hard-coded properties as authoritative. |

## Validation And Testing

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
| --- | --- | --- | --- | --- | --- |
| `V-1` | Grouped manifest-driven parity in `backend/tests/integration/test_manifest_driven_reconciliation_grouped_parity.py` **NEW** | `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -p no:cacheprovider backend/tests/integration/test_manifest_driven_reconciliation_grouped_parity.py -q` | `PH5-AC-1`, `PH5-AC-2`, `VM-9` | Three cases pass: proposals are not auto-accepted; `feature_type` sends no properties; `site` and `location` send their own `place_name` values; one keyed link per case; unchanged reruns keep decisions and sidecar bytes; both offline runs keep parent target IDs and local child foreign keys identical. | Not run: the file is **NEW**. |
| `V-2` | Grouped regression over the new test and existing `feature_type`/`location`/`site` review, export, sidecar, and identity tests | `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -p no:cacheprovider backend/tests/integration/test_manifest_driven_reconciliation_grouped_parity.py backend/tests/integration/test_feature_type_reconciliation_workflow.py backend/tests/integration/test_location_reconciliation_workflow.py backend/tests/api/v1/test_reconciliation_export.py backend/tests/api/v1/test_reconciliation_decisions.py backend/tests/services/test_reconciliation_service.py tests/reconciliation/test_mapping_sidecar.py tests/model/test_foreign_key_identity.py -q` | `PH5-AC-1`, `PH5-AC-2`, `VM-9`; existing `site` review, manual precedence, sidecar ownership, and offline normalization | All tests pass; the existing `site` manual-link precedence and offline rule are unchanged; the new cases add no regression. | Pass on 2026-11-05 for the seven existing files: 151 tests, exit 0. The expected total after adding three grouped cases is 154. |
| `V-3` | Documentation procedure and link integrity | `make check-doc-links`; review `docs/DEVELOPMENT.md` and `docs/other/RECONCILIATION_SETUP_GUIDE.md` for the required statements; follow the guide once in Reconcile → Configuration against a local backend and manifest and record the result | `PH5-AC-3`, `VM-10` | Links valid; the guide states the supported-type, property, business-key, recovery, failure, and mocked-versus-real rules; the walkthrough selects only a supported type and its declared properties and matches the documented steps. | Link check passes on 2026-11-05. Manual walkthrough not run: it requires a running backend, frontend, and Authority Service. |
| `V-4` | Formatting of the **NEW** test module | `.venv/bin/black --check backend/tests/integration/test_manifest_driven_reconciliation_grouped_parity.py && .venv/bin/isort --check-only backend/tests/integration/test_manifest_driven_reconciliation_grouped_parity.py` | Quality of the new test deliverable | Both checks pass. | Not run: the file is **NEW**. |

Real database-backed candidate checks and any staging smoke check remain separate from `V-1` and `V-2`; they are not acceptance gates for this phase. The existing `backend/tests/integration/test_site_reconciliation_end_to_end.py` is excluded because it requires a disposable database and a live Authority Service.

### Validation Results (2026-11-05)

| ID | Result | Evidence |
| --- | --- | --- |
| `V-1` | Pass | `backend/tests/integration/test_manifest_driven_reconciliation_grouped_parity.py` ran three parametrized cases (`site`, `feature_type`, `location`) in one command; all passed. Each case asserted no automatic acceptance, `feature_type` sending no `properties`, case-specific `place_name` values for `site` and `location`, one keyed sidecar link, `proposed == 0` on rerun with unchanged decisions and byte-identical sidecar, and identical parent `public_id` target IDs plus parent-`system_id` child links across two offline runs. |
| `V-2` | Pass | Baseline before any edit: the seven existing files produced 151 passed. After the change, the same seven files plus the new module produced **154 passed in 3.39s** (exit 0), including the existing `site` manual-link precedence, decision, sidecar-ownership, and foreign-key identity tests. |
| `V-3` | Pass for static checks; manual walkthrough not run | `make check-doc-links` reported `Documentation links are valid.` `docs/DEVELOPMENT.md` gained `### Configure a Reconciliation Specification` (256 words) and totals 2055 words, below the 2500-word limit. `docs/other/RECONCILIATION_SETUP_GUIDE.md` no longer presents `defaultTypes` as a support list or lists properties by type; the corrected sections point at `reconciliation.supportedTypes` and `extend.property_settings`. The interactive Reconcile → Configuration walkthrough was not executed because it requires a running backend, frontend, and Authority Service. |
| `V-4` | Pass | `.venv/bin/black --check ...` and `.venv/bin/isort --check-only ...` both pass on the new module after one formatting pass. |

Follow-up outside this phase's acceptance: `docs/other/RECONCILIATION_SETUP_GUIDE.md` still uses `taxon` in older configuration examples, and `docs/other/RECONCILIATION_WORKFLOW.md` still describes the older configuration shape. Both are unchanged here.

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Grouped parity regression for `site`, `feature_type`, and `location` | `backend/tests/integration/test_manifest_driven_reconciliation_grouped_parity.py` **NEW** | `T1.1`, `T1.2` | `V-1`, `V-2`, and `V-4` pass; three parametrized cases; no live service or shared sidecar writes. |
| Developer configuration procedure | `docs/DEVELOPMENT.md` | `T2.1` | `V-3` passes; the section is concise and the document stays under 2500 words. |
| Corrected manifest-support reference | `docs/other/RECONCILIATION_SETUP_GUIDE.md` | `T2.2` | `V-3` passes; no `defaultTypes` support claim or authoritative hard-coded property list remains. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1 — grouped parity | Done | Phases 3–4 complete | `T1.1`, `T1.2`; `V-1`, `V-2`, `V-4` pass. |
| Area 2 — documentation | Done | Area 1 behavior verified | `T2.1`, `T2.2`; `V-3` static checks pass, manual walkthrough not run. |

## Definition Of Done

* [x] `PH5-AC-1`, `PH5-AC-2`, and `PH5-AC-3` each have task evidence and passing `VM-9`/`VM-10` checks.
* [x] Both work areas and all three deliverables are complete; `V-1`–`V-4` pass or have an explicitly recorded manual result.
* [x] The grouped test uses fixture-only keys, mocks candidate and verification responses, and writes only temporary project and sidecar files.
* [x] `site`, `feature_type`, and `location` each show keyed review, no automatic acceptance, unchanged rerun, parent target ID, and local child foreign keys.
* [x] The developer guide uses a confirmed working `site` pair and distinguishes mocked workflow tests from real service availability checks.
* [x] The companion guide no longer presents `defaultTypes` as a support list or hard-coded per-type properties as authoritative.
* [x] Existing `site` review, manual-link precedence, sidecar ownership, and offline-normalization tests remain green.
* [x] Deviations and follow-up work are documented; no unresolved question affects implementation, correctness, or validation. If current repository contracts differ from the verified targets above, stop and report the discrepancy rather than redesigning or expanding this phase.

## Risks And Open Questions

- **The grouped module repeats the Phase 3/4 harness.** Keep it self-contained and limited to parity assertions. Do not refactor or edit the pilot tests in this phase; a shared harness would be a separate change with its own regression risk.
- **`site` property expectations are mocked.** The grouped test declares `place_name` for `site` in its mock manifest. That proves the client path, not the live property list; Phase 1's real service check remains the availability reference.
- **`docs/DEVELOPMENT.md` is at its target length.** Keep the new procedure to roughly 250 words and move detailed field reference to the companion guide. Exceeding 2500 words would violate the repository documentation guidance.
- **Companion documentation remains uneven.** `docs/other/RECONCILIATION_WORKFLOW.md` still describes an older configuration shape. It is outside this phase's acceptance and should be refreshed separately rather than partially rewritten here.
- **The guide walkthrough needs a running stack.** If a backend, frontend, or manifest service is unavailable during implementation, record the interactive walkthrough as a manual result rather than claiming it passed; static checks against source and the link check still apply.
- **No staging smoke check is required.** A real-service or staging check is optional, read-only, and separate from the mocked workflow acceptance in `V-1` and `V-2`.
