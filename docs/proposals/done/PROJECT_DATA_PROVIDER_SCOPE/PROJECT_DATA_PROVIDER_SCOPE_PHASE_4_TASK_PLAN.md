# Project Data Provider Scope — Phase 4 Task Plan

## Phase Summary

**Phase:** 4 — Remaining Change Request Development Work.  
**Goal:** close the Change Request entry-point and deploy-strategy validation gaps left after Phase 3.  
**Readiness:** **Validated**. The phase plan marks Phase 4 ready, the affected paths and test seams exist, and this plan chooses the entry-point behavior.

Sources: [proposal](./PROJECT_DATA_PROVIDER_SCOPE.md), [phase plan](./PROJECT_DATA_PROVIDER_SCOPE_PHASE_PLAN.md#phase-4-remaining-change-request-development-work), and [Phase 3 task plan](./PROJECT_DATA_PROVIDER_SCOPE_PHASE_3_TASK_PLAN.md). The [scope cutover](../../CHANGE_REQUEST_INGESTER/CUTOVER_AND_DEPLOYMENT/PROJECT_PROVIDER_SCOPE_CUTOVER.md) is separate operational work.

**Entry-point choice:** exclude `sead_change_request` from the top-level Data Ingestion page and direct operators to the saved project's Dispatch tab. The top-level page has no project selector. Keep other ingesters available there. On the project Dispatch tab, use the open project's locator for Change Request requests and show the project and key requirements before a run.

**Dependencies and constraints:** preserve Phases 1–3: authorized saved-project lookup, the immutable registered pair, fixed provider ID/code verification, ordered `EntityConfig.keys`, no project-name scope fallback, and scope/run metadata. Do not assign live projects, review pilot keys, decide old identity treatment, or enable a project here. `inline_staging` remains a supported backend strategy with an explicit target schema; exposing it in the UI is outside this phase.

**Acceptance criteria**

1. [x] `PH4-AC-1` (from `P-AC-4`) No Change Request validate or ingest route accepts a run without an authorized saved project, including the project-independent Data Ingestion page.
2. [x] `PH4-AC-2` (from `P-AC-5`) A run started without an authorized project, or with an unresolved saved pair, fails before any identity request, file write, or target-database access.
3. [x] `PH4-AC-3` (from `P-AC-4`) Response, in-memory artifact, and emitted manifest agree on effective scope and run ID for `inline_insert`, `copy_csv`, and `inline_staging`.

`VM-6` covers `PH4-AC-1` and `PH4-AC-2`; `VM-7` covers `PH4-AC-3`.

## Repository Findings

**Repository basis:** branch `project-data-provider-scope`, commit `970b40a8`, 2026-10-18 (Europe/Stockholm). The uncommitted proposal, phase plan, and cutover document were read as the current planning inputs; the uncommitted proposals index was left untouched. No implementation files were changed during planning. Graphify was used to locate the ingester service; the behavior below was checked in source and tests.

| Source | Verified finding | Planning implication |
| --- | --- | --- |
| `frontend/src/views/IngesterView.vue`; `frontend/src/components/ingester/IngesterList.vue`; `frontend/src/components/ingester/IngesterForm.vue` | The top-level page renders the whole registered list and the shared form. The form's workflow selector also contains the whole list. | Filter both selectors on this page and prevent a stored Change Request selection from rendering an actionable form. |
| `frontend/src/stores/ingester.ts::fetchIngesters`, `selectIngester` | The shared store keeps `selectedIngester` and may auto-select its first entry. | Reconcile an old or auto-selected Change Request selection when the top-level page mounts or the list changes; do not remove the ingester from the shared registry. |
| `frontend/src/views/ProjectDetailView.vue`; `frontend/src/components/ingester/IngesterForm.vue::buildValidateRequest`, `buildIngestRequest` | The project Dispatch tab renders the same form. The form reads `selectedProject` defaults, but its editable project-name field supplies the top-level authorization locator. | Pass the open project's route locator to the form, show it as fixed for Change Request, and do not dispatch while that project is absent or still loading. |
| `backend/app/authorization/dependencies.py::require_ingester_project`; `backend/app/api/v1/endpoints/ingesters.py::validate_data`, `ingest_data`; `backend/app/services/ingester_service.py::IngesterService._trusted_project_context` | Both HTTP routes require a top-level saved project authorization for `sead_change_request`; missing or inaccessible locators return a concealed 404. The service rejects a missing authorized locator. Other ingesters keep their project-independent path. | Add route tests for both verbs, including nested/config spoofing and zero side effects. Preserve these checks; no new backend request field is needed. |
| `backend/tests/api/test_sead_change_request_project_scope.py` | The real authorized-client path already tests validate success, nested-name conflict, an unregistered saved pair, and an unknown project. It does not cover missing-project or unresolved-pair **ingest** requests. | Extend this file and its recording SIMS/target-checker fixtures instead of creating a second route fixture. |
| `ingesters/sead_change_request/sql_builder.py::InlineStagingDeployStrategy.build_artifact`, `_base_deploy_metadata`, `_base_deploy_artifact_metadata`; `ingesters/sead_change_request/artifact_writer.py::write_artifact_bundle`; `ingesters/sead_change_request/ingester.py::SeadChangeRequestIngester.ingest` | All three strategies use the same metadata builders. The writer copies `metadata_artifact` into `manifest.json`, and ingest returns scope/run from the resolved submission context. | Add parity assertions to the real artifact and output path; production metadata changes are needed only if those assertions find a defect. |
| `backend/tests/ingesters/test_sead_change_request_ingester.py::TestSeadChangeRequestIngesterStaging`; `backend/tests/ingesters/test_sead_change_request_sql_builder.py::test_manifest_records_the_effective_scope_and_run_id`; `backend/tests/ingesters/test_sead_change_request_inline_staging.py` | Staging ingest and single-strategy manifest tests exist. The disposable PostgreSQL staging suite tests SQL execution and can skip without its environment. | Put scope/run parity in ordinary mocked ingester tests, covering all three strategies without a database. Keep the disposable suite separate. |
| `frontend/src/components/ingester/IngesterForm.vue`; `docs/USER_GUIDE.md` | The form shows backend validation errors, but its project-name copy describes an operator override; the guide says the top-level page runs any ingester. | Show the saved-project and blocked-key requirements in the Dispatch form, and correct the top-level page guidance. |

## Scope

**In scope:** top-level ingester availability and stale-selection behavior; project Dispatch form's Change Request locator and requirement text; route regression tests for missing, inaccessible, and unresolved projects; scope/run parity tests for all three strategies; the affected user guide section.

**Out of scope:** registry changes, live project YAML or provider IDs, SIMS scope inventory or migration, per-schema key approval, new deploy strategies, SQL behavior changes, new backend API fields, and UI exposure of `inline_staging`.

**Affected contracts:** the top-level request `project_name` remains the authorized-project locator; `submission_context.project_name` remains submission metadata and cannot select the project. `IngestResponse.scope_name` and `run_id`, in-memory `deploy_artifact.metadata` and `metadata_artifact`, and `manifest.json` must contain the same effective values. Existing non-Change-Request routes and ingesters remain usable without a project.

## Work Breakdown

### Area 1: Make the entry points unambiguous

**Objective:** the top-level page offers only project-independent ingesters, while the project Dispatch tab names its saved project and explains Change Request prerequisites.

**Affected code:** `frontend/src/views/IngesterView.vue`, `frontend/src/components/ingester/IngesterList.vue`, `frontend/src/components/ingester/IngesterForm.vue`, `frontend/src/views/ProjectDetailView.vue`, `frontend/src/components/ingester/__tests__/IngesterForm.test.ts`, `frontend/src/views/__tests__/IngesterView.test.ts` (**NEW**), `docs/USER_GUIDE.md`.

**Dependencies:** Phase 3 route contract; no cutover decision.

* [x] `T4.1` **Exclude Change Request on the top-level page.**
  * **Target:** `IngesterView.vue`, `IngesterList.vue`, `IngesterForm.vue`, and `IngesterView.test.ts` (**NEW**).
  * **Current → required:** both top-level selectors offer `sead_change_request`, and a shared-store selection can survive navigation → neither selector nor the form allows a Change Request validate or ingest action on the project-independent page.
  * **Implementation:** pass an explicit page-level exclusion into the list and form; filter both displayed choices without changing registry data. On mount and whenever ingesters or selection change, choose the first permitted ingester or clear the selection when none remain. Do not render action buttons for a disallowed stale selection. Show a short pointer to Project → Dispatch when Change Request is excluded. Keep non-Change-Request ingesters usable.
  * **Constraints:** do not globally hide `sead_change_request` from the Pinia store, project Dispatch tab, or backend list endpoint.
  * **Validation:** `V-1` covers a fresh visit, a Change Request selection retained from Project → Dispatch, a list containing only Change Request, and another ingester that still validates and ingests.
* [x] `T4.2` **Bind the project Dispatch form and show its requirements.**
  * **Target:** `ProjectDetailView.vue`, `IngesterForm.vue`, `IngesterForm.test.ts`, and `docs/USER_GUIDE.md`.
  * **Current → required:** the open project supplies defaults, but the Change Request project-name field is editable and labeled as an operator override → Change Request uses the open saved project's locator and shows why missing project binding or business keys block a run.
  * **Implementation:** pass the route's `projectName` into the shared form. For Change Request, show that project as fixed, use it for top-level `project_name` and matching submission context, and disable Validate and Dispatch until the matching project is loaded. Keep the server as the authority for registry, fixed-row, and key validation; display its specific error text. Add concise form and guide text for the registered pair, fixed provider row, declared keys, and the blocked-key outcome. State that the top-level page excludes Change Request and directs the operator to Project → Dispatch.
  * **Constraints:** preserve editable submission name, datatype, identifier, and other run metadata; do not require a project for unrelated ingesters.
  * **Validation:** `V-2` checks the route locator, an unloaded or stale project, a backend missing/duplicate-key error, and an ordinary ingester; `V-5` checks guide wording.

**Completion evidence:** the top-level page cannot render a Change Request run form, including after navigation from a project; the project tab sends its fixed saved-project locator and shows actionable validation errors.

### Area 2: Prove both HTTP routes fail closed

**Objective:** direct API callers cannot bypass the saved-project gate, and an unresolved saved pair has no external effects for either validate or ingest.

**Affected code:** `backend/tests/api/test_sead_change_request_project_scope.py`; preservation targets `backend/app/authorization/dependencies.py::require_ingester_project` and `backend/app/services/ingester_service.py::IngesterService._trusted_project_context`.

**Dependencies:** existing Phase 3 fixtures and behavior; independent of Area 1 UI implementation.

* [x] `T4.3` **Extend the authorized-route tests.**
  * **Target:** `backend/tests/api/test_sead_change_request_project_scope.py`.
  * **Current → required:** validate has saved-pair and unknown-project tests; ingest and missing top-level project are not covered → both routes reject absent or unauthorized saved projects, and both reject a missing or unregistered saved pair before external effects.
  * **Implementation:** use the existing `authorized_client`, `_project_payload`, `_validate_payload`, `RecordingSimsClient`, and `RecordingCollisionChecker` fixtures. Add an ingest request body using the route's verified required fields. For each verb, submit no top-level `project_name` while placing a valid-looking name, provider, or scope in nested context/config; submit an unknown or inaccessible locator; then edit the saved pair out of band to be missing or unregistered. Assert the route's concealed 404 for absent/inaccessible projects, structured failure for an unresolved saved pair, and no SIMS resolve, target checker, or artifact directory. Keep a valid authorized request as a positive control and a non-Change-Request request as a regression control.
  * **Constraints:** do not weaken `require_ingester_project` or accept a nested project name as an authorization locator. If a new test exposes a production defect, fix only that gate and its direct test; report any conflict with the Phase 3 contract before changing the design.
  * **Validation:** `V-3` covers `VM-6`, including zero identity, target-database, and file effects on rejected requests.

**Completion evidence:** `V-3` passes for validate and ingest with no mocked external calls or output files on every rejected case.

### Area 3: Cover all deploy strategies' scope and run output

**Objective:** the API result, in-memory artifact, written manifest, and recorded SIMS request identify one effective scope and run for each strategy.

**Affected code:** `backend/tests/ingesters/test_sead_change_request_ingester.py`, `backend/tests/ingesters/test_sead_change_request_sql_builder.py`, `backend/tests/api/test_sead_change_request_project_scope.py`; preservation targets `ingesters/sead_change_request/sql_builder.py::_base_deploy_metadata`, `_base_deploy_artifact_metadata` and `ingesters/sead_change_request/artifact_writer.py::write_artifact_bundle`.

**Dependencies:** existing Phase 3 metadata fields and the authorized route fixture; independent of the UI choice.

* [x] `T4.4` **Assert scope/run parity for `inline_insert`, `copy_csv`, and `inline_staging`.**
  * **Target:** the three existing test files above.
  * **Current → required:** the manifest test uses `inline_insert`, and staging tests check SQL/artifact generation without asserting scope/run equality → each strategy has an ordinary, successful test that compares response, in-memory metadata, on-disk `manifest.json`, and the SIMS resolve request.
  * **Implementation:** extend the existing successful ingester fixture to parameterize the three strategies; give `inline_staging` its required explicit `staging_target_schema` and compatible target model. Capture the effective SIMS scope/run from the recording client, parse the emitted `manifest.json`, and assert nonempty values and equality with `IngestionResult` and both artifact metadata dictionaries. Extend the authorized route fixture to run all three strategies and compare `IngestResponse.scope_name` and `run_id` with that run's artifact, parsed manifest, and captured SIMS request; make its recording client accept and record the association performed by ingest. Keep a wrong or missing staging schema case as a failure check with no artifact. Parameterize the existing `test_manifest_records_the_effective_scope_and_run_id` for the common SQL-builder contract.
  * **Constraints:** use mocked SIMS and target checks; do not require disposable PostgreSQL for `VM-7`. Do not change output SQL or bundle contents merely to add assertions.
  * **Validation:** `V-4` covers `VM-7`, including nonempty equality for each strategy and the staging-schema negative case.

**Completion evidence:** `V-4` passes for all three strategies; a passing assertion compares the parsed written manifest, not only the in-memory `metadata_artifact`.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected result |
| --- | --- | --- | --- |
| `PH4-AC-1` from `P-AC-4` | `T4.1`, `T4.2`, `T4.3` | `V-1`, `V-2`, `V-3` | Top-level page cannot start Change Request; project tab supplies its saved locator; both routes require authorization. |
| `PH4-AC-2` from `P-AC-5` | `T4.2`, `T4.3` | `V-2`, `V-3` | No-project and unresolved-pair failures cause no SIMS, target-database, or file effect. |
| `PH4-AC-3` from `P-AC-4` | `T4.4` | `V-4` | All three strategies agree on nonempty scope/run values across response, artifact, manifest, and SIMS request. |

## Validation And Testing

| ID | Check and target | Command or method | Covers | Expected result | Baseline | Execution |
| --- | --- | --- | --- | --- | --- | --- |
| `V-1` | Top-level exclusion, navigation, and ordinary-ingester regression in `frontend/src/views/__tests__/IngesterView.test.ts` (**NEW**) | `rtk pnpm --dir frontend test:run src/views/__tests__/IngesterView.test.ts` | `PH4-AC-1`, `VM-6` | Change Request is absent from both selectors; a stale selection cannot show action buttons; other ingesters still run. | **Not run:** test file was planned. | **Pass:** 3 tests passed for retained selection, an empty permitted list, and list filtering. |
| `V-2` | Project Dispatch form in `frontend/src/components/ingester/__tests__/IngesterForm.test.ts` | `rtk pnpm --dir frontend test:run src/components/ingester/__tests__/IngesterForm.test.ts` | `PH4-AC-1`, `PH4-AC-2`, `VM-6` | Route project is fixed in both request locations; missing/stale project disables actions; saved-pair and key errors remain visible; unrelated ingester works. | **Pass:** existing 3 tests passed; planned cases were not present. | **Pass:** 6 tests passed for route locator, project-load gating, backend key-error display, and ordinary ingester actions. |
| `V-3` | Both HTTP verbs, authorized and rejected requests in `backend/tests/api/test_sead_change_request_project_scope.py` | `rtk uv run pytest backend/tests/api/test_sead_change_request_project_scope.py -q` | `PH4-AC-1`, `PH4-AC-2`, `VM-6` | Missing, inaccessible, missing-pair, and unregistered-pair requests fail before SIMS, target checking, or writing. A valid project succeeds. | **Pass:** existing tests passed; planned ingest/no-project cases were not present. | **Pass:** validate/ingest authorization and unresolved-pair cases passed with no rejected-case side effects. |
| `V-4` | Three-strategy parity and staging-schema failure in `backend/tests/ingesters/test_sead_change_request_ingester.py`, `backend/tests/ingesters/test_sead_change_request_sql_builder.py`, and `backend/tests/api/test_sead_change_request_project_scope.py` | `rtk uv run pytest backend/tests/ingesters/test_sead_change_request_ingester.py backend/tests/ingesters/test_sead_change_request_sql_builder.py backend/tests/api/test_sead_change_request_project_scope.py -q` | `PH4-AC-3`, `VM-7` | Response, in-memory metadata, parsed manifest, and captured SIMS request match for each strategy; invalid staging schema writes nothing. | **Pass:** current files passed together; the three-strategy equality cases were not present. | **Pass:** all three strategies matched response, artifact metadata, disk manifest, and SIMS request; missing staging schema emitted no artifact. The API test isolates writes under `tmp_path` because `request.output_folder` is not copied into `IngesterConfig.output_folder`; fixing that mapping is outside Phase 4's named deliverables. |
| `V-5` | Frontend quality and user-guide check | `rtk pnpm --dir frontend exec vue-tsc --noEmit`; `rtk pnpm --dir frontend exec eslint src/views/IngesterView.vue src/views/ProjectDetailView.vue src/components/ingester/IngesterList.vue src/components/ingester/IngesterForm.vue src/views/__tests__/IngesterView.test.ts src/components/ingester/__tests__/IngesterForm.test.ts`; review `docs/USER_GUIDE.md` section “Dispatch and Data Ingestion” against both rendered entry points | Documentation and changed frontend code | Types and lint pass; guide names Project → Dispatch for Change Request and explains missing/duplicate keys. | **Not run:** planned files and wording did not exist yet. | **Pass:** type-check, lint, and guide review completed. |

The planning baseline for `V-3` and `V-4` was `rtk uv run pytest backend/tests/api/test_sead_change_request_project_scope.py backend/tests/ingesters/test_sead_change_request_ingester.py backend/tests/ingesters/test_sead_change_request_sql_builder.py -q` (exit 0). The planning baseline for `V-2` was the focused Vitest command above (3 passed). Run focused checks after each area; use `rtk make frontend-test` and `rtk uv run pytest backend/tests/ingesters backend/tests/api/test_ingesters.py backend/tests/api/test_sead_change_request_project_scope.py -q` as the final regression gates. Their full post-change baselines were not run during planning. `make frontend-lint` invokes `eslint --fix`; use the read-only `V-5` lint command for the planning gate.

**Final regression gates:** `rtk make frontend-test` and `rtk uv run pytest backend/tests/ingesters backend/tests/api/test_ingesters.py backend/tests/api/test_sead_change_request_project_scope.py -q` both passed after implementation.

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Project-independent page exclusion and test | `frontend/src/views/IngesterView.vue`; `frontend/src/components/ingester/IngesterList.vue`; `frontend/src/views/__tests__/IngesterView.test.ts` (**NEW**) | `T4.1` | `V-1` passes. |
| Shared form and project Dispatch binding | `frontend/src/components/ingester/IngesterForm.vue`; `frontend/src/views/ProjectDetailView.vue`; `frontend/src/components/ingester/__tests__/IngesterForm.test.ts` | `T4.1`, `T4.2` | `V-1` and `V-2` pass. |
| Entry-point guidance | `docs/USER_GUIDE.md` | `T4.2` | `V-5` review matches the UI. |
| Route rejection and response checks | `backend/tests/api/test_sead_change_request_project_scope.py` | `T4.3`, `T4.4` | `V-3` and `V-4` pass. |
| Strategy artifact and manifest checks | `backend/tests/ingesters/test_sead_change_request_ingester.py`; `backend/tests/ingesters/test_sead_change_request_sql_builder.py` | `T4.4` | `V-4` passes for all three strategies. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Entry points | Done | Phase 3 route contract | `T4.1` and `T4.2` complete; `V-1`, `V-2`, and `V-5` pass. |
| Area 2: HTTP route checks | Done | Phase 3 fixtures | `T4.3` complete; rejected requests have no SIMS, target-checker, or artifact effects (`V-3`). |
| Area 3: Strategy parity | Done | Phase 3 output metadata | `T4.4` complete; all three strategies pass scope/run parity checks (`V-4`). |

## Definition Of Done

* [x] `PH4-AC-1` and `PH4-AC-2` have passing `V-1` through `V-3` results; `VM-6` is recorded.
* [x] `PH4-AC-3` has passing `V-4` results for all three strategies; `VM-7` is recorded.
* [x] All work areas and deliverables are complete, and the top-level page still supports unrelated ingesters.
* [x] Missing or unauthorized saved projects and unresolved saved pairs have zero SIMS, target-database, and file effects in both route tests.
* [x] `V-5` and the final frontend/backend regression gates pass; the user guide matches the two entry points.
* [x] Any deviation or follow-up is recorded, and no unresolved question affects implementation or validation.

If implementation reveals that a verified route, fixture, or metadata contract differs from this plan, stop and report the conflict with a failing check. Do not invent a replacement design or include cutover work in this phase.
