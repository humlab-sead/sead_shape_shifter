# Reliable Reconciliation Links to Existing SEAD Entities — Phase 5 Task Plan

## Phase Summary

**Phase:** 5 — Export Verification. **Readiness:** Validated for implementation. The [phase plan](RECONCILIATION_MVP_PHASE_PLAN.md#phase-5-export-verification) marks this phase ready once Phase 3 owned export and Phase 4 candidate checking are available. Both functional outputs exist; Phase 3's tracker still records an unrelated workspace-wide Pyright failure.

**Sources:** [Shape Shifter proposal](RECONCILIATION_MVP.md#verification-at-export) (`SS-AC-5`), [phase plan](RECONCILIATION_MVP_PHASE_PLAN.md#phase-5-export-verification) (`VM-12`), and the [Authority Service candidate-check contract](https://github.com/humlab-sead/sead_authority_service/blob/main/docs/proposals/RECONCILIATION_IDENTITY_CONTRACT/RECONCILIATION_IDENTITY_CONTRACT.md).

**Acceptance criteria**

1. [ ] `PH5-AC-1` (from `SS-AC-5`): A candidate reported as absent or invalid is not exported, and the operator sees the reason.
2. [ ] `PH5-AC-2` (from `SS-AC-5`): An unavailable service results in an exported link with empty `verified_at`, shown as unverified, and a later re-export can verify it.

**Fixed rules:** Export is the only live check. Send the exact accepted candidate URI to the Authority Service; do not reconstruct it from `target_id` or parse it at export. Manual links are not checked, and normalization stays offline. Verification does not bind an ID or write to SIMS. Preserve the one-worker deployment constraint, project lock, owner-specific cleanup, protected manual/unowned links, and version-checked sidecar saves.

**Decision confirmed for this plan:** Persist the selected candidate URI when accepting a candidate, including one selected by alternative search. Previously saved accepted decisions containing only `target_id` load normally but require re-acceptance before they can be exported; report the affected business keys rather than guessing a URI or treating missing provenance as a service outage. Do not migrate old catalogs or sidecars.

## Repository Findings

**Repository basis:** Branch `reconciliation-mvp`, commit `d003e69c`, inspected 2026-10-31. The working proposal and phase plan contain uncommitted changes, which were considered; their Phase 5 criteria and handoff remain unchanged. Other unrelated worktree changes are not in scope.

| Verified source | Current behavior | Planning implication |
| --- | --- | --- |
| `frontend/src/components/reconciliation/ReconciliationGrid.vue::{acceptCandidate, handleAlternativeAccept, gridRows}`; `frontend/src/types/reconciliation.ts` | The UI reduces a selected candidate URI to a numeric `target_id`; alternative-search results need not be in the saved candidate list. Grid status calls every committed reconciliation link "not checked." | Send and persist the exact selected URI; show verified, unverified, and protected-manual status from the current sidecar. |
| `backend/app/models/reconciliation.py::{DecisionUpdateRequest, ResolvedEntityPair, ExportToMappingResult}`; `src/reconciliation/model.py::ResolvedEntityPair`; `backend/app/mappers/reconciliation_mapper.py::ReconciliationMapper` | An accepted decision requires a numeric ID but has no selected URI. API/domain/YAML round-trips and the export result omit verification details. | Add an optional persisted `candidate_id` for compatibility, require it on new accept actions, clear it on other actions, and add typed per-key export outcomes without removing existing response fields. |
| `backend/app/api/v1/endpoints/reconciliation.py::{get_reconciliation_service, update_mapping, export_reconciliation_to_mapping}`; `backend/app/services/reconciliation/service.py::{update_mapping, export_to_mapping, _export_to_mapping_locked}` | The async route calls synchronous export; export takes the project lock, preserves manual links, detects owner conflicts, removes stale owned links, and writes accepted links with `verified_at=None`. Decision updates currently store only the numeric ID. | Add asynchronous verification outside the lock and recheck catalog/project/sidecar freshness before one protected save. Keep authorization and existing conflicts. |
| `backend/app/clients/reconciliation_client.py::ReconciliationClient`; Authority Service `src/api/{model,router}.py` and `src/candidate_verification.py` | The injected client uses `httpx.AsyncClient` and the configured service base URL. `POST /reconcile/verify-candidates` accepts 1–100 ordered `{type, id}` items, returns `results` with `exists`, `not_found`, `invalid_candidate`, or `unsupported_type`; only `exists` includes `aggregate_id`. Database failure returns 503. | Add a typed client method, batch at 100, check response identity/count/ID, and distinguish actual unavailability from a broken contract. No preliminary health-only check. |
| `backend/app/services/reconciliation/mapping_manager.py::{load_catalog, save_catalog}`; `src/reconciliation/mapping_manager.py::{load_snapshot, save}` | The catalog loads from version-3 YAML and is atomically replaced, but has no snapshot token. The sidecar has a content version and an expected-version save. | Check the catalog's exact content and project configuration again after awaiting HTTP, and reject a changed sidecar/version instead of committing results for stale decisions. |
| `frontend/src/stores/reconciliation.ts::{exportToMapping, loadMappingData}`; `frontend/src/components/reconciliation/ReconciliationView.vue::handleExportToMapping`; `docs/USER_GUIDE.md` | Export feedback only reports link counts; the view loads mapping data on entity selection, not after export. Guide and view say verification is not performed. | Refresh mapping data after export, report key-specific rejected/unverified reasons, and update user guidance. |
| `backend/tests/api/v1/{test_reconciliation_export,test_reconciliation_decisions}.py`; `backend/tests/test_reconciliation_client.py`; `frontend/src/components/reconciliation/__tests__/{ReconciliationGrid,ReconciliationView}.test.ts` | Route, client, decision, and UI tests exist. An old decisions test still expects export to be disabled and feeds it a malformed sidecar. | Replace the obsolete assertion and cover the new contract, replay/race, and operator feedback. |

## Scope

**In scope:** `site` candidate URI provenance through UI, API, domain, mapper, and YAML; typed batch verification; explicit per-key export outcomes; verified/unverified sidecar timestamps and safe re-export/removal; operator status and user guide; focused backend/frontend and disposable-service tests.

**Out of scope:** Checking manual links or SIMS lifecycle, changing normalization or sidecar precedence, bulk acceptance, local-only approval/ingester work (Phase 6), other entity types, retroactive URI inference, and additional authentication or cross-process locking.

## Work Breakdown

### Area 1: Preserve the selected candidate URI

**Objective:** Every new accepted decision carries the exact URI needed for export; older numeric-only decisions remain readable.

**Affected code:** `src/reconciliation/model.py`, `backend/app/models/reconciliation.py`, `backend/app/mappers/reconciliation_mapper.py`, `backend/app/api/v1/endpoints/reconciliation.py`, `backend/app/services/reconciliation/service.py`, `frontend/src/types/reconciliation.ts`, `frontend/src/components/reconciliation/ReconciliationGrid.vue`; tests in `backend/tests/api/v1/test_reconciliation_decisions.py`, `backend/tests/services/test_reconciliation_service.py`, `frontend/src/components/reconciliation/__tests__/ReconciliationGrid.test.ts`.

**Dependencies:** Phase 1 decision catalog and Phase 2 review actions.

* [ ] `T1.1` **Change:** Persist a selected candidate URI on accepted decisions.
  * **Target:** `src/reconciliation/model.py::ResolvedEntityPair`, `backend/app/models/reconciliation.py::{ResolvedEntityPair, DecisionUpdateRequest}`, `backend/app/mappers/reconciliation_mapper.py::ReconciliationMapper`.
  * **Current → required:** Only `target_id` survives API/domain/YAML round-trips → add optional `candidate_id: str | None` holding the exact URI. New accept requests require both `target_id` and a nonempty `candidate_id`; reject and local-only requests carry neither. Existing accepted catalog records without `candidate_id` still load.
  * **Implementation:** Map the field both ways without changing catalog version 3.0. Validate new request status/fields; avoid making the persisted DTO reject legacy accepted records.
  * **Constraints:** Do not recover a URI by matching the numeric tail in saved candidates: IDs can be ambiguous and alternative-search selections may not be saved.
  * **Validation:** `V-1`: both persisted and legacy decisions load correctly; missing new URI and URI on non-accepted actions are rejected.
* [ ] `T1.2` **Change:** Pass the exact selection through both acceptance paths.
  * **Target:** `frontend/src/components/reconciliation/ReconciliationGrid.vue::{persistDecision, acceptCandidate, handleAlternativeAccept}`, `frontend/src/types/reconciliation.ts::DecisionUpdateRequest`, `backend/app/api/v1/endpoints/reconciliation.py::update_mapping`, `backend/app/services/reconciliation/service.py::update_mapping`.
  * **Current → required:** The selected URI is discarded → submit and store it unchanged alongside the numeric ID. Clear it when a decision changes to rejected or local-only; retain existing notes and confidence behavior.
  * **Implementation:** Reuse the current numeric-tail extraction on acceptance, reject a mismatch between submitted URI and `target_id` on the server, and take confidence only from a genuinely matching saved candidate. The selected alternative-search candidate need not be present in that list.
  * **Constraints:** Do not conflate operator-entered manual links (separate mapping endpoint) with accepted candidates; they do not have a candidate URI.
  * **Validation:** `V-1`: both UI selection paths, same-label/different-key decisions, changed decisions, and bad/missing URIs.

**Completion evidence:** The accepted URI survives an API response, a catalog save/reload, and both UI selection paths; an old numeric-only acceptance loads but cannot be mistaken for verified provenance.

### Area 2: Implement the read-only candidate-check client

**Objective:** Obtain a trustworthy ordered result for every accepted URI without changing the existing OpenRefine query flow.

**Affected code:** `backend/app/clients/reconciliation_client.py`, `backend/app/models/reconciliation.py`, `backend/tests/test_reconciliation_client.py`.

**Dependencies:** Phase 4 Authority Service endpoint; Area 1.

* [ ] `T2.1` **Change:** Add a typed async candidate verification method to the injected reconciliation client.
  * **Target:** `backend/app/clients/reconciliation_client.py::ReconciliationClient`, typed request/response models in `backend/app/models/reconciliation.py`; `backend/tests/test_reconciliation_client.py`.
  * **Current → required:** Only OpenRefine candidate search is exposed → POST ordered `{"items":[{"type":"site","id":candidate_id},...]}` to `/reconcile/verify-candidates` through the existing async HTTP client, chunking at 100.
  * **Implementation:** Validate each response's number and order of items, echoed type/URI, outcome, and `aggregate_id` for `exists`; reject a mismatched aggregate ID against the persisted `target_id` before export. Treat connection/timeout and the service's 503 database-unavailable response as unavailability; malformed JSON/results, `unsupported_type`, other HTTP failures, and contract mismatches are explicit export errors, never unverified successes. Return no results on a partially failed protocol batch; do not silently discard items.
  * **Constraints:** Do not use the OpenRefine `/reconcile` response format for this endpoint or make an HTTP request while holding the project lock. Never send an empty batch.
  * **Validation:** `V-2`: 1, 100, and 101 inputs; ordered results, 503/timeout/refused connection, other HTTP errors, malformed/out-of-order/short responses, unsupported type, and mismatched aggregate ID.

**Completion evidence:** Contract tests distinguish absent/invalid candidates, genuine unavailability, and protocol errors without falsely marking any candidate verified.

### Area 3: Verify and reconcile links at export

**Objective:** Commit only the current specification's allowed links, with accurate verification metadata and operator-visible outcomes.

**Affected code:** `backend/app/services/reconciliation/service.py`, `backend/app/api/v1/endpoints/reconciliation.py`, `backend/app/models/reconciliation.py`; tests in `backend/tests/api/v1/{test_reconciliation_export,test_reconciliation_decisions}.py` and `backend/tests/services/test_reconciliation_service.py`.

**Dependencies:** Areas 1–2 and Phase 3 owned export.

* [ ] `T3.1` **Change:** Split export into a locked preflight, unlocked awaited verification, and locked commit.
  * **Target:** `backend/app/services/reconciliation/service.py::{export_to_mapping, _export_to_mapping_locked}`, `backend/app/api/v1/endpoints/reconciliation.py::export_reconciliation_to_mapping`.
  * **Current → required:** Synchronous export writes accepted links without checking SEAD → asynchronously check only accepted candidates not shadowed by protected manual/unowned links, and commit only after freshness checks.
  * **Implementation:** In preflight, validate the specification, candidate URIs, ownership, entity metadata, and current sidecar; capture the catalog/project content and sidecar version. If any exportable accepted decision lacks a URI, return an actionable error listing its encoded business keys before any HTTP or write. Await batch checks without the process-local project lock. Reacquire the lock, reload catalog/project/sidecar and recheck the captured contents, metadata and owner conflicts; on any change return a conflict requiring retry. Save with the sidecar's expected content version. Keep missing-spec and authorization behavior unchanged.
  * **Constraints:** Do not leave a lock held over network I/O or apply a response to a different decision, URI, owner, or project. An explicit stale or protocol error must not mutate the sidecar.
  * **Validation:** `V-3`: changed decision/specification/project or sidecar during the await; deletion or competing owner; protected manual/unowned link; old numeric-only decision; no network call when no accepted candidate needs checking.
* [ ] `T3.2` **Change:** Apply verification outcomes, including on re-export.
  * **Target:** `backend/app/services/reconciliation/service.py::export_to_mapping`, `backend/app/models/reconciliation.py::ExportToMappingResult`, `backend/app/api/v1/endpoints/reconciliation.py::export_reconciliation_to_mapping`.
  * **Current → required:** All newly owned links have null `verified_at`, and accepted owned links with the same ID are skipped → `exists` commits with a UTC verification time; `not_found`/`invalid_candidate` do not export and remove a previously owned link for that key; service unavailability commits with null `verified_at`, even if an earlier export verified the same link.
  * **Implementation:** Add typed per-business-key export outcomes (`verified`, `not_found`, `invalid_candidate`, `unverified`) and reasons while preserving `exported`, `removed`, `skipped_manual`, `entity`, and `field`. Report actual written/removal counts; a no-op re-export of an unchanged verified link may retain its previous verified timestamp, but a change from unverified to verified or verified to unavailable must be saved. Remove stale links for rejected/removed decisions as before. On failure of any verification batch due to genuine unavailability, treat all exportable accepted candidates in that attempt as unverified; on protocol error save nothing.
  * **Constraints:** Never remove or check protected manual/unowned or other-owner links. Do not change sidecar version, offline normalization, or local-only handling. Use a single version-checked save for the resulting sidecar changes.
  * **Validation:** `V-3`: mixed verified/absent/invalid results, removal of a formerly owned link, manual protection, existing verified → unavailable → verified re-export, exact counts, unchanged no-op, and no writes on conflict or malformed response. Replace `test_export_is_disabled_without_modifying_sidecar` in the decisions tests: its 400 expectation predates Phase 3, and its malformed sidecar currently triggers 500.

**Completion evidence:** Export responses and persisted sidecar state agree per key, including after an outage and after a candidate disappears.

### Area 4: Show the result and validate it against a disposable service

**Objective:** Operators can distinguish committed verified, committed unverified, rejected, and protected manual links, and can retry verification.

**Affected code:** `frontend/src/types/reconciliation.ts`, `frontend/src/stores/reconciliation.ts`, `frontend/src/components/reconciliation/{ReconciliationGrid,ReconciliationView}.vue`, `frontend/src/components/reconciliation/__tests__/{ReconciliationGrid,ReconciliationView}.test.ts`, `docs/USER_GUIDE.md`.

**Dependencies:** Area 3.

* [ ] `T4.1` **Change:** Display per-key failures and refresh the mapping status after export.
  * **Target:** `frontend/src/types/reconciliation.ts::{ExportToMappingResult, MappingLink}`, `frontend/src/stores/reconciliation.ts::exportToMapping`, `frontend/src/components/reconciliation/{ReconciliationView,ReconciliationGrid}.vue`.
  * **Current → required:** The view says export does not verify IDs, displays counts only, and leaves loaded sidecar data stale → show absent/invalid keys and reasons, warn about unavailable-service links, refresh the selected entity's sidecar after successful export, and show `verified_at` or unverified status for committed reconciliation links.
  * **Implementation:** Preserve existing count feedback and API error details. Distinguish an old numeric-only decision that requires re-acceptance from service unavailability; show manual links as trusted but not checked. If refresh fails, show an error instead of presenting stale status as current. Keep the unverified state visible for later re-export.
  * **Constraints:** Do not claim that a catalog-only acceptance or a missing sidecar link is verified. Do not show a manual link as an unverified reconciliation candidate.
  * **Validation:** `V-4`: verified timestamp, unavailable then retried status, absent/invalid reason, re-accept instruction, protected manual link, and refresh failure.
* [ ] `T4.2` **Change:** Update user guidance and record implementation checks.
  * **Target:** `docs/USER_GUIDE.md::Reconciliation Workflow`, this task plan's progress tracker and validation results.
  * **Current → required:** The guide says export never checks SEAD → explain explicit export, rejection, unverified links during outages, re-export, and re-acceptance for numeric-only decisions.
  * **Implementation:** Record actual test commands, outcomes, and any deviations in this plan as work completes. Stop and report if repository state or the Authority Service contract conflicts materially with this plan rather than designing a replacement during implementation.
  * **Constraints:** Do not promise that SIMS binding or normalization verifies candidates.
  * **Validation:** `V-4`, `V-5`, `V-6`: documented steps match the tested UI and live outcomes; internal links resolve.

**Completion evidence:** An operator can identify exactly which accepted keys were not exported, which links await verification, and how to retry; a disposable-service run proves both acceptance criteria.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
| --- | --- | --- | --- |
| `PH5-AC-1` (`SS-AC-5`, `VM-12`) | `T1.1`, `T1.2`, `T2.1`, `T3.1`, `T3.2`, `T4.1` | `V-1`, `V-2`, `V-3`, `V-4`, `V-5` | Exact selected URI is checked; absent/invalid candidates have no exported owned link (including an old one) and their business keys and reasons appear to the operator. |
| `PH5-AC-2` (`SS-AC-5`, `VM-12`) | `T2.1`, `T3.1`, `T3.2`, `T4.1`, `T4.2` | `V-2`, `V-3`, `V-4`, `V-5`, `V-6` | An unavailable service leaves an owned link with null `verified_at`, visible as unverified; a later successful export fills it without changing the chosen ID. |

## Validation And Testing

| ID | Check and target | Exact command or method | Covers | Expected result | Baseline (2026-10-31) |
| --- | --- | --- | --- | --- | --- |
| `V-1` | URI persistence and accept actions: `backend/tests/api/v1/test_reconciliation_decisions.py`, `backend/tests/services/test_reconciliation_service.py`, `frontend/src/components/reconciliation/__tests__/ReconciliationGrid.test.ts`; exact URI, alternative search, bad/missing URI, legacy load, status transition | `uv run pytest -o addopts='' -q backend/tests/api/v1/test_reconciliation_decisions.py backend/tests/services/test_reconciliation_service.py` and `cd frontend && pnpm exec vitest run src/components/reconciliation/__tests__/ReconciliationGrid.test.ts` | `PH5-AC-1` | Both selection paths round-trip the exact URI; invalid new accepts fail without changing decisions; legacy data loads. | Fail: in an earlier targeted backend run combining decisions with client/export, 49 passed and 1 obsolete export-disabled test failed (expected 400, got 500 from malformed sidecar). Not run: service and grid tests for this planning baseline. |
| `V-2` | Authority contract: `backend/tests/test_reconciliation_client.py`; ordered response, 100-item boundary, outage and malformed reply | `uv run pytest -o addopts='' -q backend/tests/test_reconciliation_client.py` | Both criteria | Only a genuine availability failure produces an unverified result; unexpected responses fail explicitly. | Pass: client and export baseline together, 41 tests; new candidate-check tests not run. |
| `V-3` | Protected export: `backend/tests/api/v1/test_reconciliation_export.py`, `backend/tests/api/v1/test_reconciliation_decisions.py`, `backend/tests/services/test_reconciliation_service.py`; all four outcomes, re-export, owner/manual, race, stale save, no side effects on failure | `uv run pytest -o addopts='' -q backend/tests/api/v1/test_reconciliation_export.py backend/tests/api/v1/test_reconciliation_decisions.py backend/tests/services/test_reconciliation_service.py` | Both criteria and Phase 3 behavior | Exact output counts and sidecar timestamps/removals; concurrent changes conflict before save; protected links remain. | Pass: export and client baseline together, 41 tests. Fail: adding decisions produced the obsolete 400/500 failure above; service tests not run. |
| `V-4` | Operator display: `frontend/src/components/reconciliation/__tests__/ReconciliationGrid.test.ts`, `frontend/src/components/reconciliation/__tests__/ReconciliationView.test.ts` | `cd frontend && pnpm exec vitest run src/components/reconciliation/__tests__/ReconciliationGrid.test.ts src/components/reconciliation/__tests__/ReconciliationView.test.ts` | Both criteria | Per-key failure/retry messages and fresh sidecar statuses agree; refresh errors are visible. | Pass: view tests, 7 tests; grid tests not run in this baseline. |
| `V-5` | `VM-12`: real Authority Service and helper-owned SEAD database with `authority`/`sead_identity` installed; a real `site` ID, a nonexistent ID, an invalid URI, and an unavailable service | From `../sead_authority_service`, run `scripts/verify_sims_identity_candidates.sh setup` (or `start` if already set up), `bootstrap site` when needed, and `credentials`; configure and start Authority Service against `127.0.0.1:55432/sead_staging` per its `docs/DEVELOPMENT.md`. Configure Shape Shifter's reconciliation service URL to this running service. Export a reviewed existing site, absent site, and invalid URI; stop the service, re-export, restart it, and re-export again. Record request/response, sidecar contents and timestamps, visible UI status, and unchanged SEAD/SIMS rows. | Both criteria | Existing: verified timestamp; absent/invalid: no owned link and a key-specific reason; stopped service: link with null timestamp; recovery: same ID with a timestamp. This must use the live service, not a mock or health-only probe. | Not run: Phase 5 has not been implemented; a skipped or unavailable live service cannot count as a pass. |
| `V-6` | Type, format, documentation and offline regression: touched backend/domain/test files, frontend types/components, `docs/USER_GUIDE.md`, `tests/process/test_shapeshifter.py` | Run independently: `uv run pytest -o addopts='' -q tests/process/test_shapeshifter.py`<br>`uv run black --check src/reconciliation/model.py backend/app/models/reconciliation.py backend/app/mappers/reconciliation_mapper.py backend/app/clients/reconciliation_client.py backend/app/services/reconciliation/service.py backend/app/api/v1/endpoints/reconciliation.py backend/tests/api/v1/test_reconciliation_decisions.py backend/tests/api/v1/test_reconciliation_export.py backend/tests/services/test_reconciliation_service.py backend/tests/test_reconciliation_client.py`<br>`uv run pyright --threads 2 src backend`<br>`cd frontend && pnpm exec vue-tsc --noEmit`<br>`make check-doc-links` | Both criteria and offline/manual behavior | Normalization remains offline; changed files format/type-check; frontend contracts compile; guide links resolve. | Not run as a combined check. Phase 3 recorded a workspace-wide Pyright failure (134 diagnostics, unchanged code in touched files); compare any failures against that baseline, do not misreport a new diagnostic as pre-existing. |

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Candidate URI in decision and round-trip | `src/reconciliation/model.py`, `backend/app/models/reconciliation.py`, `backend/app/mappers/reconciliation_mapper.py` | `T1.1`, `T2.1`, `T3.2` | API/domain/YAML and typed export result round-trip; legacy decisions still load. |
| Decision and protected export endpoints | `backend/app/api/v1/endpoints/reconciliation.py`, `backend/app/services/reconciliation/service.py` | `T1.2`, `T3.1`, `T3.2` | Exact URI persists and asynchronous checks precede a fresh version-checked save. |
| Candidate-check HTTP client | `backend/app/clients/reconciliation_client.py` | `T2.1` | Contract and error-classification tests pass. |
| Operator types, selection and status | `frontend/src/types/reconciliation.ts`, `frontend/src/stores/reconciliation.ts`, `frontend/src/components/reconciliation/ReconciliationGrid.vue`, `frontend/src/components/reconciliation/ReconciliationView.vue` | `T1.2`, `T4.1` | Accepted URI is retained; feedback and refreshed mapping match the response/sidecar. |
| Backend regression tests | `backend/tests/test_reconciliation_client.py`, `backend/tests/api/v1/test_reconciliation_decisions.py`, `backend/tests/api/v1/test_reconciliation_export.py`, `backend/tests/services/test_reconciliation_service.py` | `T1.1`, `T1.2`, `T2.1`, `T3.1`, `T3.2` | `V-1`–`V-3` pass, including the replaced obsolete export-disabled test. |
| Frontend regression tests | `frontend/src/components/reconciliation/__tests__/ReconciliationGrid.test.ts`, `frontend/src/components/reconciliation/__tests__/ReconciliationView.test.ts` | `T1.2`, `T4.1` | `V-4` passes for statuses and retries. |
| User guidance and implementation record | `docs/USER_GUIDE.md`, this task plan | `T4.2` | Guidance matches `VM-12`; tracker contains actual validation results. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Preserve the selected candidate URI | Not started | Phase 1/2 review decisions | User confirmed persist-at-accept and re-accept-for-legacy policy. |
| Area 2: Implement the read-only candidate-check client | Not started | Phase 4; Area 1 | Authority endpoint is implemented; Shape Shifter client is not. |
| Area 3: Verify and reconcile links at export | Not started | Phase 3; Areas 1–2 | Phase 3 owned export exists. |
| Area 4: Show the result and validate it | Not started | Area 3 | Live `VM-12` must pass before completion. |

## Definition Of Done

* [ ] `PH5-AC-1` has `V-1`–`V-5` evidence for URI provenance, rejected candidates, old-link removal, and operator reasons.
* [ ] `PH5-AC-2` has `V-2`–`V-6` evidence for outage, unverified status, and verified re-export.
* [ ] All four work areas and listed deliverables are complete; the disposable-service `VM-12` run is recorded with real requests and sidecar results, not skipped.
* [ ] Ownership/manual protection, sidecar version checks, offline normalization, authorization, and existing response fields retain regression coverage.
* [ ] Targeted tests, frontend type check, formatting, documentation links, and any newly introduced backend diagnostics pass; pre-existing workspace-wide failures are reported accurately.
* [ ] UI/API/domain/YAML contracts and user guidance agree; deviations and remaining work are documented; no unresolved question changes implementation or validation.

## Risks And Open Questions

* **Race between check and commit:** The project lock is process-local, and catalog writes have no version token. Capture and compare the catalog and project contents across the awaited check, recheck conflicts under the lock, and use the sidecar's expected version. Any changed input aborts export and asks the operator to retry.
* **Previously exported invalid link:** Do not leave a formerly owned link effective when a new check reports `not_found` or `invalid_candidate`. Remove it without touching a manual/unowned replacement at that key.
* **Old decisions:** A numeric-only accepted decision cannot be checked safely. Require re-acceptance using the actual candidate, including when alternative search originally supplied it; do not quietly downgrade the failure to unverified. This policy was confirmed before writing the plan.
