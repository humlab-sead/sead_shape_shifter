# Reconciliation Search and Browse: Phase 2 Task Plan

## Phase Summary

**Goal:** Save first-time review decisions atomically and require successful verification before exporting accepted links.

**Readiness:** Validated against the repository on 2026-11-19. Stale-view detection and the client-supplied catalog precondition moved out of Phase 2, as the revised [save contract](./RECONCILIATION_SEARCH_AND_BROWSE_PHASE_2_CONTRACT.md) and [phase plan](./RECONCILIATION_SEARCH_AND_BROWSE_PHASE_PLAN.md#phase-2-atomic-decisions-and-verified-export) record. That change removes the earlier blocking questions about hash transport, awaiting under the project lock, CLI coordination, and the offline identifier base. The [approved proposal](./RECONCILIATION_SEARCH_AND_BROWSE.md) and the revised contract define the scope and interfaces below.

**Dependencies:** Phase 1 Authority Service verification at commit `1f3f1b8`, the revised Phase 2 contract, project authorization and the per-project lock, and existing catalog and sidecar formats. Preserve the single-worker deployment assumption. No catalog route changes its payload in this phase, so the frontend, the CLI, and existing scripts stay untouched. Do not enable pilot capabilities for general use.

1. [x] `PH2-AC-1` (from `P-AC-6`, `P-AC-8`): Save first-time accepted or New decisions as a batch; resolve source rows once and reject the entire batch for missing, duplicate, unauthorized, or changed rows.
2. [x] `PH2-AC-2` (from `P-AC-6`, `P-AC-8`): Load, change, and save every catalog write under the project lock, including registry create and update, so a concurrent writer's decisions for other rows are never lost. A successful batch returns its saved decisions in request order; a write that cannot be applied leaves the catalog unchanged.
3. [x] `PH2-AC-3` (from `P-AC-5`, `P-AC-6`): Validate accepted URI/type/ID references on every writer, retain invalid legacy entries with row-specific issues, reject invalid replacements atomically, and preserve valid manual decisions.
4. [x] `PH2-AC-4` (from `P-AC-5`, `P-AC-7`, `P-AC-10`, `P-AC-12`): Save without remote existence checks; locally validate and require ordered Authority verification before exporting accepted links. Outages and invalid responses block those exports; valid New-only saves and exports remain available.
5. [x] `PH2-AC-5` (from `P-AC-1`, `P-AC-12`): Preserve source identity, explicit export, manual-link protections, ownership cleanup, offline normalization, and foreign-key behavior.

## Repository Findings

**Repository basis:** Shape Shifter `reconciliation-search-and-browse` at `5727bed84e859d19e50842fd224cae882fa61815`, inspected 2026-11-19. The revised phase plan, contract, proposal amendment, and Phase 1 task plan are part of this change. Authority Service `reconciliation-search-and-browse` is at `1f3f1b8470e44b1d0730fb9d8b00e3318ec588eb`. Graphify was used for navigation and source files were checked directly.

| Evidence | Finding | Planning implication |
|---|---|---|
| `backend/app/services/reconciliation/mapping_manager.py::EntityMappingManager` | Catalogs are mapped through DTOs and saved using a temporary file and `os.replace`. | A failed write leaves the previous catalog intact, so all-or-nothing needs no extra mechanism. |
| `backend/app/services/reconciliation/service.py::auto_reconcile_entity` | Matching merges its proposals into a freshly loaded catalog and skips decisions that are not `proposed`; the no-service-type path saves without the project lock. | A decision saved during matching already survives. Fix the unlocked threshold write; add no precondition. |
| `backend/app/services/project_service.py::ProjectService._get_lock`, `backend/app/services/reconciliation/service.py::get_resolved_source_data` | The project lock is a non-reentrant `threading.Lock`; source resolution awaits preview or SQL loaders. | Resolve source rows before taking the lock and apply decisions inside it, as `export_to_mapping` already does, so no async work runs while the lock is held. |
| `scripts/project/auto_reconcile.py::run_reconciliation` | The CLI calls the writing service directly in its own process; project locks are process-local. | The CLI stays unchanged. Concurrent CLI and server writes remain uncoordinated, which matches current behavior and is recorded as a risk. |
| `backend/app/services/reconciliation/service.py::update_mapping` | A first-time key is rejected and `_extract_id_from_uri` checks only trailing digits. | Add the batch path and a shared type-aware local reference validator. |
| `backend/app/services/reconciliation/resolvers.py`, `backend/app/services/shapeshift_service.py::preview_entity`, `backend/app/utils/caches.py::ShapeShiftCache` | Reconciliation uses the shared preview service. Its warm and entity/dependency caches use a five-minute TTL, project version, and entity configuration, not changes to external source data. | Batch revalidation must bypass cached rows and dependencies; otherwise a changed source row can still appear unchanged. |
| `backend/app/utils/error_handlers.py` | `ValidationError` maps to 400 and `ResourceConflictError` to 409, both with `detail` equal to `{error_type, error_code, message, tips, recoverable, context}`. | Row issues attach as `detail.issues` without changing the envelope. |
| `backend/app/clients/reconciliation_client.py::verify_candidates` | The client checks response count, order, echoed type/URI, and unsupported types. | Preserve the protocol while removing the accepted-link outage fallback. |
| `backend/app/services/reconciliation/service.py::export_to_mapping`, `docs/USER_GUIDE.md`, `docs/other/RECONCILIATION_GUIDE.md` | Export currently writes unverified links on an outage; the guides describe that fallback. | Block those exports before sidecar changes and update the guidance in the implementation change. |

## Scope

- **In scope:** Shape Shifter API, service, and catalog; serialized catalog writes; atomic first-time batch decisions; local reference validation and diagnostics; verified export; tests; and the affected reconciliation guidance.
- **Out of scope:** The persistent Search/Browse workspace, stale-view detection and any client-supplied catalog precondition, server-side review sessions, per-row versions, paging, recent-query history, derived application state, target creation, SIMS allocation, and policy for links exported unverified by earlier versions.
- If current source or tests conflict with a frozen contract, stop and report the evidence; do not silently change the contract or broaden implementation scope.

## Work Breakdown

### Area 1: Serialize Every Catalog Write

**Objective:** Every catalog read-modify-write runs under the project lock, so no writer loses another writer's decisions.

**Affected code:** `backend/app/services/reconciliation/service.py`, `backend/app/services/reconciliation/mapping_manager.py`, and `backend/app/api/v1/endpoints/reconciliation.py`.

**Dependencies:** None.

- [x] `T1.1` **Change:** Move registry create and update behind locked service methods.
	- **Target:** `ReconciliationService`, the `create_registry` and `update_catalog` routes, and `EntityMappingManager.create_entity_mapping` and `update_entity_mapping`.
	- **Current -> required:** Both routes call the manager directly, which loads and rewrites the whole catalog outside the project lock, so a concurrent decision write can be lost.
	- **Implementation:** Add `create_specification` and `update_specification` to `ReconciliationService` that load, mutate, and save inside `self.project_service._get_lock(project_name)`. Keep mapper conversion in the routes and keep the existing already-exists and not-found errors.
	- **Constraints:** No payload, response, or status change. Keep `require_project(Action.EDIT)`, the current catalog shape, and the existing `delete_specification` behavior with its owned-sidecar cleanup.
	- **Validation:** `V-1` holds the lock from another thread and asserts a concurrent registry update cannot observe or save a half-applied catalog.
- [x] `T1.2` **Change:** Take the lock in the matching no-service-type write.
	- **Target:** `ReconciliationService.auto_reconcile_entity`.
	- **Current -> required:** The threshold-only path calls `catalog_manager.save_catalog` outside the lock; the later merge already runs inside it.
	- **Implementation:** Wrap the threshold update and save in `_get_lock`. Leave the merge that preserves decisions whose status is not `proposed` unchanged.
	- **Constraints:** Preserve matching proposals and manual decisions. Do not make matching depend on a client-supplied precondition and do not auto-retry. Leave both matching routes' payloads and the CLI unchanged.
	- **Validation:** `V-1` covers a decision saved during matching and a threshold-only write.

**Completion evidence:** Every catalog writer mutates inside `ProjectService._get_lock`; a concurrent decision write and a registry or matching write each keep the other's changes; no route payload changed.

### Area 2: Validate References And Report Repairable Entries

**Objective:** Use one local, type-aware validator for accepted references while retaining invalid legacy decisions for inspection and repair.

**Affected code:** `backend/app/services/reconciliation/service.py`, `backend/app/models/reconciliation.py`, `backend/app/mappers/reconciliation_mapper.py`, `backend/app/exceptions.py`, and `src/reconciliation/model.py` where a tolerant read representation is needed.

**Dependencies:** None; this area is independent of Area 1. The Authority identifier rules are implemented separately in `sead_authority_service/src/record_identifiers.py`; do not import the other repository's `src` package.

- [x] `T2.1` **Change:** Replace the trailing-integer parser with a shared local reference validator.
	- **Target:** `ReconciliationService._extract_id_from_uri`.
	- **Current -> required:** Any URI ending in digits currently passes the parser. Validate the URI structure, the specification's `remote.service_type`, and the numeric ID.
	- **Implementation:** Require an absolute URI with a scheme and host, no query string or fragment, exactly two trailing path segments (`remote.service_type`, then the ID), a positive ASCII decimal ID within PostgreSQL `integer` range (leading zeros accepted), and `int(id) == target_id`. Do not compare against a configured identifier base.
	- **Constraints:** The validator makes no details, manifest, or existence request, and cannot establish country membership. New-only operations must not depend on any Authority response.
	- **Validation:** `V-2` tests valid pilot and site URIs, leading zeros, wrong type, missing or extra path segments, queries, fragments, Unicode digits, zero, overflow, and ID mismatch.
- [x] `T2.2` **Change:** Keep invalid saved references readable and return row-specific diagnostics.
	- **Target:** Catalog DTO/domain loading and mapping in `backend/app/models/reconciliation.py`, `backend/app/mappers/reconciliation_mapper.py`, `src/reconciliation/model.py`, and `ReconciliationService.get_reconciliation_preview`.
	- **Current -> required:** Some invalid URI/type/ID combinations load without an issue; stricter DTO/domain checks also reject some malformed accepted entries before they can be repaired.
	- **Implementation:** Preserve legacy version `3.0` accepted entries, including missing or blank candidate URIs and invalid IDs, in a read/repair path; show their key-specific issues in the existing preview/read workflow. Keep unchanged invalid entries visible and retain valid manual decisions. Do not weaken validation of new accepted writes or silently discard data.
	- **Constraints:** Preserve the current catalog GET shape. If a tolerant representation cannot preserve a legacy value through the mapper, stop and report the conflict rather than rewriting the catalog.
	- **Validation:** `V-2` reads invalid entries, identifies each affected key, repairs one, and verifies valid prior decisions survive.
- [x] `T2.3` **Change:** Apply reference validation and structured issues to every accepted-decision write and replacement.
	- **Target:** `update_mapping`, registry create/update, `replace_catalog`, the JSON/YAML routes, and reconciliation-specific domain error serialization.
	- **Current -> required:** Legacy writes accept trailing-digit URIs and replacement does not report all invalid accepted references. Invalid submitted references must reject the write with row-specific issues.
	- **Implementation:** Validate each accepted reference that a writer introduces or changes; validate all accepted references in a whole-catalog replacement before any catalog or owned-sidecar change. Return every issue as `detail.issues` with `row_index`, `local_key_value`, `field`, `code`, and `message` in the existing error envelope.
	- **Constraints:** Keep valid prior manual decisions and existing replacement cleanup semantics. Do not contact Authority details or verification endpoints during save.
	- **Validation:** `V-2` exercises legacy decisions, both replacements, multiple invalid rows, repair, and no catalog or sidecar mutation on rejection.

**Completion evidence:** All accepted-write paths share the validator; invalid existing decisions can be inspected and repaired without losing valid decisions.

### Area 3: Save Decision Batches Atomically

**Objective:** Save first-time accepted and New decisions for authorized, unchanged source rows in one catalog write.

**Affected code:** `backend/app/models/reconciliation.py`, `backend/app/api/v1/endpoints/reconciliation.py`, `backend/app/services/reconciliation/service.py`, `backend/app/services/reconciliation/resolvers.py`, `backend/app/services/shapeshift_service.py`, and `src/reconciliation/mapping_model.py::encode_local_key` as an existing key utility.

**Dependencies:** Areas 1 and 2. The batch wire contract and validation order are fixed in contract sections 3-5 and 7.

- [x] `T3.1` **Change:** Expose the authorized batch request, response, and errors.
	- **Target:** Reconciliation API models and `POST /projects/{project_name}/reconciliation/{entity_name}/{target_field}/decisions`.
	- **Current -> required:** Only individual decisions for existing keys are accepted. The batch accepts nonempty, distinct drafts with `accepted` or `local-only` status and returns saved rows and counts in request order.
	- **Implementation:** Map the request and response fields in contract sections 3 and 4. Use `require_project(Action.EDIT)`; return the 400 issue envelope, the 404 unknown-specification response, and the 403 authorization behavior.
	- **Constraints:** Keep draft validation in the service so row issues reach `detail.issues`; a request-model validator must not reject a draft before the service can report which row failed. The route takes no catalog precondition.
	- **Validation:** `V-3` checks the exact response, error envelope, missing specification, and project authorization.
- [x] `T3.2` **Change:** Revalidate the submitted rows once and reject an invalid batch in full.
	- **Target:** `ReconciliationService.get_resolved_source_data`, `ReconciliationQueryService.index_rows`, source resolvers, `ShapeShiftService.preview_entity`, and the new batch service method.
	- **Current -> required:** The existing resolver and ordered-key encoder support preview and matching, but cached target or search rows can hide external source changes. Batch validation must use current rows.
	- **Implementation:** Call `get_resolved_source_data` once, before taking the project lock, with fresh resolution. Bypass the warm store and cached entity and dependency frames for all preview-based sources; retain the SQL loader path. Reject incomplete key indexes, then validate malformed, repeated, absent, or changed rows. Compare every submitted displayed column using contract section 5's JSON, numeric, date, and datetime rules. Aggregate row issues before any write.
	- **Constraints:** Reuse the configured source strategy and encoded ordered business keys; keep ordinary preview caching unchanged and do not trust displayed values as persisted source data. Nothing awaits while `_get_lock` is held. Authorization is project-level; a key outside the resolved source is not an authorized row.
	- **Validation:** `V-3` covers warm and dependency caches, source changes without a project configuration change, compound keys and escaping, multiple issues, duplicate keys, missing and changed columns, numeric/date comparison, one resolver call, and no file changes on failure.
- [x] `T3.3` **Change:** Store the whole valid batch once without exporting it.
	- **Target:** The batch service method, existing mapping-sidecar ownership models, and batch result models.
	- **Current -> required:** The legacy updater cannot create first-time keys. A valid batch creates or updates decisions from server-resolved rows and saves once.
	- **Implementation:** Take `_get_lock` and load the catalog, then validate accepted references with `T2.1` and reject New decisions that conflict with protected manual links or existing public IDs. Apply the decisions to the loaded catalog instead of replacing it. Preserve an existing decision's creation metadata and candidates; initialize new decisions and timestamps as specified. Return batch and post-save specification counts.
	- **Constraints:** Do not call Authority details or verification, alter source labels, keys or `system_id`, or write a sidecar during save. A failed disk write must leave the catalog unchanged.
	- **Validation:** `V-3` checks first-time accepted/New drafts, existing metadata, protected links, source-derived values, one save, write failure, and no sidecar or remote verification calls.

**Completion evidence:** One successful multi-row batch returns the saved decisions and specification counts from a single save; every invalid batch preserves all prior catalog and sidecar content.

### Area 4: Require Verification Before Export

**Objective:** Export accepted links only after successful ordered verification, while retaining New-only outage behavior and existing identity protections.

**Affected code:** `ReconciliationService._prepare_export_to_mapping_locked`, `export_to_mapping`, `_export_to_mapping_locked`, and `ReconciliationClient.verify_candidates`.

**Dependencies:** Area 2 and Phase 1's verification contract. Area 3 supplies the new decisions exercised by the workflow checks.

- [x] `T4.1` **Change:** Fail the whole export before sidecar mutation when an accepted link cannot be verified.
	- **Target:** `backend/app/services/reconciliation/service.py` and `backend/app/clients/reconciliation_client.py`.
	- **Current -> required:** An outage currently exports unverified links, and `not_found` or `invalid_candidate` can remove owned links. Neither path may change the sidecar.
	- **Implementation:** Validate accepted references locally, request verification for every accepted link that would be written, validate count, order, echoes, outcomes and numeric IDs, then recheck catalog/project/sidecar snapshots before the existing write. Treat unsupported types, malformed or mismatched replies, non-country results, missing targets, and outages as failures before cleanup or approval writes.
	- **Constraints:** Preserve the Authority verification request format and existing site behavior. Do not treat a failed or empty response as approval.
	- **Validation:** `V-4` asserts byte-identical sidecars for each failure, including a mixed accepted/New export, and verifies successful links carry actual target IDs and `verified_at`.
- [x] `T4.2` **Change:** Preserve New-only exports, ownership rules, and offline normalization.
	- **Target:** Export preflight and sidecar application in `backend/app/services/reconciliation/service.py`; workflow fixtures in the two existing reconciliation integration tests.
	- **Current -> required:** The existing export protects manual/unowned links and records local-only approvals. These behaviors must survive the verification gate, including when no accepted link needs verification.
	- **Implementation:** Bypass Authority verification for valid New-only saves and exports. Preserve ownership cleanup for explicit operations and do not silently repair, re-verify, or remove previously exported unverified links as a recovery policy. Retain the current snapshot/version conflict checks.
	- **Constraints:** Leave source labels, ordered keys, `system_id`, public-ID application, and downstream foreign-key behavior unchanged. If an operation cannot preserve a legacy unverified link without deciding a recovery policy, stop and report it.
	- **Validation:** `V-4` and `V-5` check New-only outage, manual/unowned and other-owner protection, owned cleanup, prior unverified links, repeated offline normalization, actual IDs, and child foreign keys.

**Completion evidence:** Verification failures produce no sidecar changes; successful verified and New-only exports retain the existing mapping and normalization guarantees.

### Area 5: Update Fixtures, Guidance, And Records

**Objective:** Ship the batch, validator, and export changes with current regression fixtures, accurate user guidance, and a plan that records what was verified.

**Affected code:** `backend/tests/integration/test_feature_type_reconciliation_workflow.py`, `backend/tests/integration/test_location_reconciliation_workflow.py`, `docs/USER_GUIDE.md`, `docs/other/RECONCILIATION_GUIDE.md`, and this plan.

**Dependencies:** Areas 1-4. The persistent workspace remains Phase 3 work.

- [x] `T5.1` **Change:** Update the reconciliation workflow fixtures.
	- **Target:** `backend/tests/integration/test_feature_type_reconciliation_workflow.py` and `backend/tests/integration/test_location_reconciliation_workflow.py`.
	- **Current -> required:** Both fixtures exercise export through the outage fallback, and neither covers a first-time batch save or a `country` specification.
	- **Implementation:** Add first-time accepted and New decisions through the batch route, assert that verified export uses the fixture target IDs, and add a `country` remote-type case using `location_id` to the location workflow. Assert unchanged source keys, `system_id`, and child foreign keys after repeated offline normalization.
	- **Constraints:** Keep the mocked-Authority limitation explicit; these fixtures do not prove a paired deployment. No route payload changed, so existing fixture requests stay valid.
	- **Validation:** `V-5` and `V-7` check the workflows and the Authority contract.
- [x] `T5.2` **Change:** Update the reconciliation guidance.
	- **Target:** `docs/USER_GUIDE.md` and `docs/other/RECONCILIATION_GUIDE.md`.
	- **Current -> required:** The guides say an outage produces an unverified export.
	- **Implementation:** Replace the outage fallback with the verified-export and New-only behavior, and describe batch saving as the way a row with no prior catalog entry receives a decision. Do not describe the Phase 3 workspace as delivered.
	- **Constraints:** Keep the guides aligned with implemented behavior only.
	- **Validation:** `V-8` checks documentation links and consistency.
- [x] `T5.3` **Change:** Record implementation and verification results in this task plan.
	- **Target:** `docs/proposals/RECONCILIATION_SEARCH_AND_BROWSE/RECONCILIATION_SEARCH_AND_BROWSE_PHASE_2_TASK_PLAN.md`.
	- **Current -> required:** Work and acceptance criteria are not started; completed work must have a current tracker and test results.
	- **Implementation:** Record completed task IDs, actual commands and results, remaining risks, and any deviations as each area lands.
	- **Constraints:** Do not mark the phase done while a required check remains open.
	- **Validation:** `V-8` checks the tracker, acceptance coverage, and documentation links.

**Completion evidence:** Fixtures cover first-time batch saves and both pilot types, guidance matches export behavior, and results are recorded without claiming Phase 4 validation.

## Acceptance-Criteria Coverage

| Criterion | Tasks | Validation | Expected evidence |
|---|---|---|---|
| `PH2-AC-1` | `T3.1`, `T3.2`, `T3.3` | `V-3` | `VM-4`: first-time and compound-key batches resolve once; missing, duplicate, unauthorized, or changed rows leave the catalog unchanged. |
| `PH2-AC-2` | `T1.1`, `T1.2`, `T3.3` | `V-1` | `VM-5`: registry, decision, and matching writes are serialized; each keeps the other's changes and a successful batch returns its saved decisions. |
| `PH2-AC-3` | `T2.1`, `T2.2`, `T2.3`, `T3.3` | `V-2`, `V-3` | `VM-5`: invalid references are reported and repairable; invalid replacements change neither file and valid decisions survive. |
| `PH2-AC-4` | `T2.1`, `T3.3`, `T4.1`, `T4.2` | `V-3`, `V-4`, `V-7` | `VM-6`: saves make no existence call; accepted exports require successful ordered verification, while New-only outage operations work. |
| `PH2-AC-5` | `T3.2`, `T3.3`, `T4.2`, `T5.1` | `V-3`, `V-4`, `V-5` | `VM-6`: explicit export, ownership, local identities, actual public IDs, New approvals, offline normalization, and foreign keys remain correct. |

## Validation And Testing

Run Shape Shifter Python commands from its repository root and the Authority command from its repository root. The result notes below record the implementation run on 2026-11-19.

| ID | Check and exact command or method | Expected result and baseline |
|---|---|---|
| `V-1` | `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -n 0 -q -p no:cacheprovider backend/tests/services/test_reconciliation_service.py backend/tests/api/v1/test_reconciliation_specifications.py backend/tests/api/v1/test_reconciliation_decisions.py` | Registry create and update, decision writes, and the threshold-only matching write each load and save inside the project lock. A second writer waits for the held lock, a decision saved during matching survives, and a failed save leaves the catalog byte-identical. **Result: Pass** (2026-11-19); lock assertions implemented and passing. |
| `V-3` | `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -n 0 -q -p no:cacheprovider backend/tests/services/test_reconciliation_service.py backend/tests/services/test_shapeshift_service.py backend/tests/api/v1/test_reconciliation_decisions.py` | Use temporary authorized projects, fixed and compound-key rows, mutable source fixtures, and sidecar snapshots. Warm the preview and dependency caches, change source data without changing project configuration, and assert the batch sees the new value and rejects stale displayed values. Also assert first-time accepted/New success, request order/counts and one resolve/save; malformed, duplicate, absent, changed, protected, unauthorized and disk-failure cases preserve file bytes and report applicable issues. Verify 400/403/404 and no save-time details/verification calls. **Result: Pass** (2026-11-19); batch and fresh-resolution cases implemented and passing. |
| `V-2` | `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -n 0 -q -p no:cacheprovider backend/tests/services/test_reconciliation_service.py backend/tests/api/v1/test_reconciliation_decisions.py backend/tests/api/v1/test_reconciliation_specifications.py` | Exercise URI boundaries on batch, legacy and replacement writers; read and repair invalid legacy entries; reject multiple invalid references with complete row issues and unchanged catalog/sidecar bytes. **Result: Pass** (2026-11-19); validator and repair cases implemented and passing. |
| `V-4` | `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -n 0 -q -p no:cacheprovider backend/tests/api/v1/test_reconciliation_export.py backend/tests/test_reconciliation_client.py` | Replace outage-export and invalid-result cleanup expectations with no-write assertions. Cover ordered success, wrong type/ID, non-country `not_found`, unsupported type, malformed/reordered replies, outage, protected links, prior unverified links, and New-only export. **Result: Pass** (2026-11-19); outage and invalid-result cleanup tests now assert no sidecar write. |
| `V-5` | `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -n 0 -q -p no:cacheprovider backend/tests/integration/test_feature_type_reconciliation_workflow.py backend/tests/integration/test_location_reconciliation_workflow.py` | Through authorized routes and temporary project files, assert first-time decisions for `feature_type` and `country`, explicit verified export, New approvals, fixture target IDs including `location_id`, unchanged source keys and `system_id`, and child foreign keys after repeated offline normalization. **Result: Pass** (2026-11-19); the country case is implemented. Authority is mocked; this does not prove a paired deployment. |
| `V-6` | From the Shape Shifter root run `uv run pyright --threads 2 backend/app/services/reconciliation backend/app/services/shapeshift_service.py backend/app/models/reconciliation.py backend/app/api/v1/endpoints/reconciliation.py`, `.venv/bin/python -m black --check backend/app/services/reconciliation backend/app/services/shapeshift_service.py backend/app/models/reconciliation.py backend/app/api/v1/endpoints/reconciliation.py`, `.venv/bin/python -m isort --check-only --profile black backend/app/services/reconciliation backend/app/services/shapeshift_service.py backend/app/models/reconciliation.py backend/app/api/v1/endpoints/reconciliation.py`, and `.venv/bin/python -m pylint backend/app/services/reconciliation backend/app/services/shapeshift_service.py backend/app/models/reconciliation.py backend/app/api/v1/endpoints/reconciliation.py`. | Non-mutating type, lint, and format checks pass for changed files; include any additional changed Python files. No frontend file changes in this phase. **Result: Pass** (2026-11-19). |
| `V-7` | `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider tests/api/test_candidate_verification.py` in Authority Service. | Phase 1 fixtures retain ordered echoes, site behavior, disabled capabilities, and the mocked non-country `not_found` result. **Result: Pass** (26 tests; one Starlette deprecation warning) on 2026-11-19. No live paired-service test was run. |
| `V-8` | Run `scripts/ci/check_doc_links.sh` from the Shape Shifter root; manually check `docs/other/RECONCILIATION_GUIDE.md`, the task-plan links, tracker, and criteria-to-task/test mappings because the script does not scan those proposal/other documents. | Documentation reflects implemented behavior and all plan references resolve. **Result: Pass** (2026-11-19). Implementation documentation was updated and validated. |

## Deliverables

| Deliverable | Exact target | Tasks | Completion evidence |
|---|---|---|---|
| Catalog API and persistence | `backend/app/models/reconciliation.py`, `backend/app/mappers/reconciliation_mapper.py`, `backend/app/services/reconciliation/mapping_manager.py`, `backend/app/api/v1/endpoints/reconciliation.py` | `T1.1`, `T2.2`, `T2.3`, `T3.1` | Serialized, authorized routes and a readable catalog without transport fields. |
| Decision, validation, and export logic | `backend/app/services/reconciliation/service.py`, `backend/app/services/reconciliation/resolvers.py`, `backend/app/services/shapeshift_service.py`, `backend/app/clients/reconciliation_client.py`, `backend/app/exceptions.py`, and `src/reconciliation/model.py` if needed for tolerant reads | `T1.1`, `T1.2`, `T2.1`, `T2.2`, `T2.3`, `T3.2`, `T3.3`, `T4.1`, `T4.2` | Serialized writes, fresh source validation, repairable diagnostics, one-write batches, and verification-gated export. |
| Backend regressions | `backend/tests/services/test_reconciliation_service.py`, `backend/tests/services/test_shapeshift_service.py`, `backend/tests/api/v1/test_reconciliation_decisions.py`, `backend/tests/api/v1/test_reconciliation_decisions_batch.py` (NEW), `backend/tests/api/v1/test_reconciliation_specifications.py`, `backend/tests/api/v1/test_reconciliation_export.py`, `backend/tests/test_reconciliation_client.py` | `T1.1`, `T1.2`, `T2.1`, `T2.2`, `T2.3`, `T3.1`, `T3.2`, `T3.3`, `T4.1`, `T4.2` | Focused serialization, source freshness, batch, authorization, reference, and export cases pass. |
| Workflow regressions | `backend/tests/integration/test_feature_type_reconciliation_workflow.py`, `backend/tests/integration/test_location_reconciliation_workflow.py` | `T4.2`, `T5.1` | Authorized mocked-service workflows verify IDs, New approvals, offline normalization, and foreign keys. |
| Guidance and tracker | `docs/USER_GUIDE.md`, `docs/other/RECONCILIATION_GUIDE.md`, `docs/proposals/RECONCILIATION_SEARCH_AND_BROWSE/RECONCILIATION_SEARCH_AND_BROWSE_PHASE_2_TASK_PLAN.md` | `T5.2`, `T5.3` | Guidance matches the released behavior and the tracker records actual validation. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
|---|---|---|---|
| 1. Serialize every catalog write | Done | None | `create_specification` and `update_specification` wrap the registry manager calls in `ProjectService._get_lock`; the no-service-type matching write now reloads, updates, and saves under the same lock. |
| 2. Validate references and report repairable entries | Done | None | `reference_validation.py` replaces `_extract_id_from_uri`; batch, legacy decision writes, whole-catalog replacement, preview diagnostics, and export preflight share it. Loads tolerate legacy accepted entries. |
| 3. Save decision batches atomically | Done | Areas 1-2 | `POST .../decisions` resolves source rows once with `fresh=True`, compares displayed columns, and applies every draft in one locked save. Errors carry `detail.issues`. |
| 4. Require verification before export | Done | Areas 2-3 | Accepted links are validated locally, verified in order, and any outage, non-exists outcome, or mismatched reply blocks the export before the sidecar is touched. New-only exports bypass verification. |
| 5. Update fixtures, guidance, and records | Done | Areas 1-4 | Workflow fixtures cover first-time batch decisions for `feature_type` and `country`; the user guides describe verified export and batch saving; this tracker records the results. |

## Implementation Record

Implemented on 2026-11-19 on branch `reconciliation-search-and-browse` (base `5727bed8`). Every `T*` task is complete.

**Validation results**

| ID | Command | Result |
|---|---|---|
| `V-1`, `V-2`, `V-3`, `V-4` | `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider backend/tests/services/test_reconciliation_service.py backend/tests/services/test_shapeshift_service.py backend/tests/api/v1/test_reconciliation_decisions.py backend/tests/api/v1/test_reconciliation_decisions_batch.py backend/tests/api/v1/test_reconciliation_specifications.py backend/tests/api/v1/test_reconciliation_export.py backend/tests/test_reconciliation_client.py` | Pass (exit 0). New cases cover lock-held writes, fresh source resolution, first-time batches, change detection, all-or-nothing rejection, legacy read/repair, replacement rejection, and no-write export failures. The batch route reuses `require_project(Action.EDIT)` unchanged; it conceals an unpermitted project as `404`, like the other reconciliation routes, and adds no authorization path. |
| `V-5` | `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider backend/tests/integration/test_feature_type_reconciliation_workflow.py backend/tests/integration/test_location_reconciliation_workflow.py` | Pass. Adds first-time batch decisions for `feature_type` and a `country` specification keyed on `location_id`; verified export uses fixture target IDs and offline normalization keeps source keys, `system_id`, and child foreign keys. Authority is mocked; this does not prove a paired deployment. |
| `V-6` | `uv run pyright --threads 2 ...`; `.venv/bin/python -m black --check ...`; `.venv/bin/python -m isort --check-only --profile black ...`; `.venv/bin/python -m pylint ...` | Pass: Pyright 0 errors; Black and isort report no changes; pylint 10.00/10 on changed source files. |
| `V-7` | `cd ../sead_authority_service && .venv/bin/python -m pytest -q -p no:cacheprovider tests/api/test_candidate_verification.py` | Pass (26 tests; one Starlette deprecation warning). No live paired-service test was run. |
| `V-8` | `bash scripts/ci/check_doc_links.sh` plus manual review of the two guides and this plan | Pass. Documentation links are valid and the guides describe verified export plus batch saving. |
| Broader regression | `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider backend/tests` | Two pre-existing failures remain: `test_route_inventory_matches_assembled_api_routes` and `test_route_inventory_matches_authorization_metadata` report the `DELETE /api/v1/projects/{project_name}/mapping/{entity_name}` route missing from `docs/AUTHORIZATION_ROUTE_INVENTORY.md`. `git show HEAD` confirms that gap predates this change. All other backend tests pass, including the new `/decisions` route now recorded in the inventory. |

**Acceptance evidence**

| Criterion | Evidence |
|---|---|
| `PH2-AC-1`, `VM-4` | `test_batch_saves_first_time_accepted_and_local_only_decisions`, `test_batch_resolves_source_rows_once_with_fresh_data`, `test_batch_rejects_changed_rows_and_leaves_the_catalog_unchanged`, `test_batch_rejects_duplicate_and_missing_rows`. |
| `PH2-AC-2`, `VM-5` | `TestCatalogWriteSerialization`, `test_batch_runs_its_catalog_write_under_the_project_lock`, `test_registry_create_and_update_hold_the_project_lock`, `test_batch_saves_once_and_leaves_the_catalog_on_write_failure`, existing `test_decision_saved_during_matching_is_not_overwritten`. |
| `PH2-AC-3`, `VM-5` | `test_parse_record_uri_*`, `test_preview_reports_invalid_legacy_accepted_references`, `test_whole_catalog_save_rejects_invalid_accepted_references`, `test_batch_reports_every_invalid_reference`. |
| `PH2-AC-4`, `VM-6` | `test_verification_outage_does_not_write_unverified_links_then_retry_verifies`, `test_not_found_and_invalid_candidates_do_not_change_the_sidecar`, `test_export_does_not_write_an_invalid_candidate_for_a_compound_key`, New-only coverage in `test_export_counts_created_and_protected_links_and_skips_noop_writes`. |
| `PH2-AC-5`, `VM-6` | Workflow fixtures `test_first_time_batch_decisions_and_verified_export` and `test_country_first_time_batch_and_verified_export`, plus `test_exported_links_normalize_offline_with_stable_parent_ids_and_child_foreign_keys`. |

**Deviations**

- Added `backend/tests/api/v1/test_reconciliation_decisions_batch.py` for the batch route rather than extending the already large legacy decision test file.
- Replaced the two export tests that asserted the old outage and invalid-result cleanup behavior with no-write assertions, and added valid candidate URIs to the `sample_recon_config` fixture so whole-catalog replacement exercises valid references.
- Added the `/decisions` route to `docs/AUTHORIZATION_ROUTE_INVENTORY.md`.

## Definition Of Done

- [x] Every `PH2-AC-*` criterion has passing task and validation evidence, including `VM-4` through `VM-6`.
- [x] Every catalog writer runs inside the project lock, so a concurrent write to another business key is never lost.
- [x] No catalog route changes its payload; the frontend, the CLI, and existing scripts are unchanged.
- [x] Invalid legacy decisions remain readable and repairable; accepted-write validation and export verification pass all negative and outage checks.
- [x] Source identity, explicit export, manual/unowned protection, owned cleanup, New approvals, offline normalization, and foreign keys have regression coverage.
- [x] `V-1` through `V-8` pass or have an explicitly approved exception; affected documentation and the tracker reflect actual results.
- [x] Prior unverified links have not been silently repaired or removed, and pilot capabilities remain unadvertised pending Phase 4.
- [x] Any deviation and follow-up is recorded; no unresolved question affects correctness or validation.

## Risks And Open Questions

1. **R1: Same-key last-writer-wins.** Two saves for the same business key are not detected; the later save replaces the earlier decision. Every current decision route already behaves this way, and Phase 3 owns the reviewer warning through `PH3-AC-6`. Detecting it would need per-row revisions or a whole-catalog precondition, which this phase does not add.
2. **R2: Uncoordinated CLI and server writes.** `scripts/project/auto_reconcile.py` runs in its own process, and `ProjectService._get_lock` is process-local. Simultaneous CLI and server writes can still lose a change. That matches current behavior, and the single-worker assumption covers only in-process requests. Closing it needs a cross-process lock and belongs to a separate change.
3. **R3: Validator scope.** Without a configured identifier base, the validator cannot reject a reference whose host differs from the Authority base. Export verification covers that gap: the service receives the type and URI, and a reference that does not resolve to the expected `aggregate_id` blocks the export. Country membership and target existence also stay export-time checks.

The paired Authority/Shape Shifter deployment and live country data are not validated by the mocked workflow tests. Phase 4 owns those pilot and capability-release checks.