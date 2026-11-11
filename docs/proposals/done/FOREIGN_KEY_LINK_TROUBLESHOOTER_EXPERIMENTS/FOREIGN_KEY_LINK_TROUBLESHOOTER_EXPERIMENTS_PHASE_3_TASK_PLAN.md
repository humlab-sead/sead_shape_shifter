# Foreign-Key Link Troubleshooter Experiments — Phase 3 Task Plan

## Phase Summary

**Phase:** 3 — Dialog Controls and Contract Cutover. Sources: [approved proposal](./FOREIGN_KEY_LINK_TROUBLESHOOTER_EXPERIMENTS.md), [phase plan, Phase 3](./FOREIGN_KEY_LINK_TROUBLESHOOTER_EXPERIMENTS_PHASE_PLAN.md#phase-3-dialog-controls-and-contract-cutover), [Phase 1 task plan](./FOREIGN_KEY_LINK_TROUBLESHOOTER_EXPERIMENTS_PHASE_1_TASK_PLAN.md), and [Phase 2 task plan](./FOREIGN_KEY_LINK_TROUBLESHOOTER_EXPERIMENTS_PHASE_2_TASK_PLAN.md).

**Readiness: Validated.** The phase plan now marks Phase 3 readiness as confirmed. The Phase 1/2 context contracts and the Phase 2 decisions `D1`–`D13` are present, and the focused prerequisite suites pass 150 tests on 2026-11-07 (`test_link_trial_service.py`, `test_link_troubleshooter_service.py`, `test_link_experiment_context_store.py`, `test_link_troubleshooter_mapper.py`, `test_link_troubleshooter.py`). Every target below is an existing file or a named symbol in one, and every validation row has an executable command, so implementation can start.

**Goal:** Replace stateless replay and server paging with the owned snapshot context, explicit trials, browser-only exception browsing, automatic refresh after expiry, immediate Reset to baseline, and best-effort Close. `VM-5` covers controls, reset, and refresh; `VM-6` covers local browsing, cleanup, and contract/documentation cutover.

**Constraints:** Keep supported-warning eligibility and reproduction checks, the 15-minute non-sliding context lifetime, project read authorization, production link behavior, Phase 2 limits and inherited/explicit setting semantics, and read-only operation. Do not change the separate integrity inspector. A trial never becomes the baseline; never compare results from different context IDs.

**Phase acceptance criteria**

1. [x] `PH3-AC-1` (from `P-AC-5`): Edits invalidate stale trial results; out-of-order responses cannot replace newer settings or undo Reset or refresh.
2. [x] `PH3-AC-2` (from `P-AC-6`): Reset immediately restores original controls, the latest received complete or incomplete baseline, and initial diagnostic selection; it clears errors without replay or TTL extension.
3. [x] `PH3-AC-3` (from `P-AC-9`): Paging, group switches, and page-size changes make no request; paging fields are absent from requests and the break is documented.
4. [x] `PH3-AC-4` (from `P-AC-8`): Closing clears client trial state and requests context cleanup without writing saved data or caches.
5. [x] `PH3-AC-5` (from `P-AC-1`, `P-AC-7`, `P-AC-10`): After expiry, the next context-dependent operation reopens through warning reproduction, replaces the baseline, clears the trial, and announces the refresh without rerunning the expired trial. Reproduction failure is explicit.

## Repository Findings

**Repository basis:** `feature/foreign-key-link-troubleshooter-experiments` at `f598e371`, inspected 2026-11-07. The worktree was clean before this plan; no uncommitted implementation changes were used. Graphify was queried for the dialog/context flow, then the files below were inspected directly.

| Evidence | Verified current behavior | Planning implication |
|---|---|---|
| `backend/app/api/v1/endpoints/link_troubleshooter.py`; `backend/app/services/link_troubleshooter_service.py::open_context`, `run_context_trial`, `close_context` | Protected context open, read, trial, and delete routes exist alongside the old stateless POST. Expired reads/trials return 410 with `detail.error_type=LinkExperimentContextExpired` and `detail.reason=context_expired`; unavailable or unauthorized resources do not grant access. | Use the context routes and original warning request to reopen on **410 only**. Never retry the expired trial automatically. Remove the stateless route and service path at coordinated cutover; leave authorization on all context operations. |
| `backend/app/models/link_troubleshooter.py::LinkExperimentContextRequest`, `LinkExperimentTrialRequest`, `LinkExperimentContextResponse`, `LinkExperimentTrialResponse` | Trial requests forbid extra fields and carry optional `how`, `allow_null_keys`, `null_keys_equal` controls. Open requests currently do **not** forbid extras; Pydantic's default ignores unexpected paging keys. Responses carry context ID, fixed expiry, baseline diagnostic status, settings when available, complete totals when successful, and bounded exception groups. | Forbid extras on open as well; test 422 for `page`, `page_size`, `row_filter` on both request shapes. Keep nullable baseline settings because a failed or budget-blocked diagnostic can have none. |
| `backend/app/mappers/link_troubleshooter_mapper.py::to_context_response`, `to_context_trial_response`; `backend/app/services/link_experiment_context_store.py::LinkExperimentDiagnostics` | Complete baselines have exact counts and capped `detail.unmatched`/`detail.multiply_matched`; incomplete baselines have no complete totals or groups. Per-side findings and truncation metadata are separate from totals. | Show full counts alongside **returned** row counts and truncation labels; do not imply that omitted rows were examined locally. Preserve incomplete baselines through Reset and refresh. |
| `backend/app/models/link_troubleshooter.py::LinkTroubleshootRelationship`; `src/model.py::ForeignKeyConstraints` | The context returns saved `configured_keys`, effective `relationship.join_type`, and the saved constraints dictionary even when baseline diagnostics have no `settings`. The two null controls distinguish omission from an explicit value. | Initialize controls from those saved fields and keep an inherited option separate from explicit true/false. Show resolved runtime null behavior from `baseline.settings` or trial settings only when provided; do not invent it for unavailable diagnostics. |
| `frontend/src/api/linkTroubleshooter.ts`; `frontend/src/types/linkTroubleshooter.ts`; `frontend/src/composables/useLinkTroubleshooter.ts` | The only browser API call uses the stateless route. The composable clears results during requests, sends paging fields, and its `reset()` discards the dialog identity instead of restoring the baseline. | Replace the typed client and state model together. Retain the latest context baseline and warning request, guard async completions by request generation and context ID, and make Reset and Close different operations. |
| `frontend/src/components/validation/LinkTroubleshooterDialog.vue`; `frontend/src/utils/linkTroubleshooter.ts`; `frontend/src/views/ProjectDetailView.vue` | Dialog controls edit keys only; paging/filter changes rerun the request. The warning helper checks the existing eligible warning shape. The parent supplies the selected warning via `v-model`; the dialog also hosts a separate integrity body. | Replace only the row-count dialog branch. Keep warning eligibility, header fallback, parent opening/closing behavior, and integrity inspection unchanged. |
| `frontend/src/utils/errors.ts::formatErrorMessage`; `frontend/src/api/client.ts::apiRequest` | The shared formatter can read the structured 410 response nested under `detail`; API calls reject non-2xx responses. | Identify expiry by HTTP 410 **and** its structured reason, not by arbitrary messages or a generic 404; display other failures instead of refreshing silently. |
| `backend/app/models/__init__.py`; `backend/app/api/v1/api.py`; `docs/AUTHORIZATION_ROUTE_INVENTORY.md` | The old paging DTOs are re-exported, the link router is already registered, and the authorization inventory still lists the stateless route. | Remove obsolete DTO exports and inventory row; retain the registered router and its four protected context routes. |
| `docs/USER_GUIDE.md::Troubleshooting a Link`; `docs/DESIGN.md::Constraints and Assumptions`; `docs/whats-new/README.md` | The guide says page changes re-read data; the design note names other in-process state but not dialog contexts. Release notes are generated from the change PR's `User-facing release note` and `Upgrade notes`, not edited in an unassigned version file. | Correct user/design prose; record the breaking stateless API change and replacement routes in those PR sections for release-note generation. Do not guess a release version. |

## Scope

**In scope:** Context-only API and TypeScript contracts, browser API calls, composable lifecycle and race handling, join/null controls, baseline/trial comparison and findings, bounded local exception paging, read-only Close, focused tests, the authorization route inventory, user guide, design note, and the change PR's release/upgrade notes.

**Out of scope:** Production join changes, new constraints or join types, saved configuration updates, database/cache writes, changing Phase 2 caps, durable context recovery, automatic trial updates, full result browsing, downstream validation, integrity inspector changes, and allocating a release number.

## Work Breakdown

These are the tasks for this phase. The phase-plan readiness gate is confirmed. If source behavior differs from these verified targets at implementation time, stop and report the discrepancy rather than redesigning the phase.

### Area 1: Cut over the request contract

**Objective:** The browser and backend expose only context-based row-count troubleshooting, with explicit rejection of paging fields.

**Affected code:** `backend/app/api/v1/endpoints/link_troubleshooter.py`, `backend/app/models/link_troubleshooter.py`, `backend/app/models/__init__.py`, `backend/app/services/link_troubleshooter_service.py`, `backend/app/mappers/link_troubleshooter_mapper.py`, `frontend/src/api/linkTroubleshooter.ts`, `frontend/src/types/linkTroubleshooter.ts`; existing API, mapper, service, and client tests.

**Dependencies:** Phase plan Phase 3 readiness (confirmed 2026-11-07); existing Phase 1/2 context responses.

* [x] `T1.1` **Change:** Remove the stateless route, its replay/paging service/mapper path and obsolete DTO exports; make context-open requests reject extras. **Target:** the five backend files above. **Current → required:** both routes coexist and open ignores unknown paging fields → context routes alone, with 422 and no service call for `page`, `page_size`, or `row_filter` on open and trial. Preserve project read checks, expiry 410, concealed 404, and all shared context response models. **Validation:** `V-1`, `V-4`.
* [x] `T1.2` **Change:** Define context open/trial/close API methods and exact response/control types; remove stateless paging types. **Target:** `frontend/src/api/linkTroubleshooter.ts`, `frontend/src/types/linkTroubleshooter.ts`, `frontend/src/api/__tests__/linkTroubleshooter.test.ts`. **Current → required:** one stateless POST with page fields → POST open using warning identity, POST trial using context ID and settings, DELETE close; represent nullable context IDs, nullable/incomplete baseline settings, `detail` groups, truncation, and optional inherited overrides. Keep encoded project and context IDs, and verify request bodies contain no paging fields. **Validation:** `V-2`, `V-4`.

**Completion evidence:** OpenAPI and client use context operations only; paging fields are rejected, and obsolete server/client symbols are unused.

### Area 2: Make experiment state snapshot-aware

**Objective:** One current baseline and at most one current trial survive local navigation, while controls, expiry, reset, and late responses cannot mix snapshots.

**Affected code:** `frontend/src/composables/useLinkTroubleshooter.ts`, `frontend/src/composables/__tests__/useLinkTroubleshooter.test.ts`, `frontend/src/utils/linkTroubleshooter.ts` (warning request helper), `frontend/src/utils/__tests__/linkTroubleshooter.test.ts`.

**Dependencies:** Area 1 typed client; no change to warning eligibility.

* [x] `T2.1` **Change:** Open a context with the original warning request, retain its latest baseline and ID/expiry, initialize ordered keys and join/null controls from saved settings, and execute trials only on explicit Run. **Target:** `useLinkTroubleshooter.ts`. **Current → required:** every run replays and clears the result → a trial re-links the owned context while baseline remains visible; `null`/inherit stays distinct from explicit false, and incomplete baseline totals remain absent. Invalidate trial and error on any control edit (including in-flight edits), tie accepted responses to submitted controls, context ID, and a monotonically invalidated request generation; do not accept responses after another open, Reset, or Close. **Validation:** `V-2`, `V-3`.
* [x] `T2.2` **Change:** On the structured expiry response from a context-dependent operation, discard that operation, reopen using the original warning request, and replace the old baseline, context, controls, and trial together. **Target:** `useLinkTroubleshooter.ts` and its test file. **Current → required:** request failure only → refresh notice and new baseline, with a new explicit Run required. For non-reproduction or ineligibility, show the returned reason without the old trial; for other 404/403/500/network errors, show the error without treating it as expiry. Guard a late old request/open from overwriting the new state; ensure cleanup of the superseded context is best-effort without discarding the new one. **Validation:** `V-2`, `V-3`.
* [x] `T2.3` **Change:** Implement immediate Reset to baseline and separate Close cleanup. **Target:** `useLinkTroubleshooter.ts` and its test file. **Current → required:** `reset()` destroys identity → Reset restores original controls and the latest received complete **or incomplete** baseline, clears trial errors and local selection, invalidates pending responses, and sends no request or TTL extension; Close clears all state and requests DELETE for its owned context. Report cleanup failures without masking a newer dialog or treating them as successful cleanup. **Validation:** `V-2`, `V-3`.

**Completion evidence:** Deferred-response tests show edits/Reset/refresh/Close cannot be undone, and all retained results belong to the same context ID.

### Area 3: Display controls and bounded exceptions

**Objective:** The row-count dialog shows original versus trial behavior and browses returned exception groups without HTTP requests.

**Affected code:** `frontend/src/components/validation/LinkTroubleshooterDialog.vue`, `frontend/src/components/validation/__tests__/LinkTroubleshooterDialog.test.ts`.

**Dependencies:** Areas 1–2.

* [x] `T3.1` **Change:** Add Inner/Left and inherited/explicit null controls alongside ordered key pairs and explicit Run trial; show saved and effective settings, full baseline/trial counts, separate bounded findings, incomplete/failure states, and refreshed-input notice. **Target:** dialog and component tests. **Current → required:** key-only editor with server-paged trial rows → control changes remove stale trial display immediately while preserving the baseline; trial failure has no complete metrics, and incomplete baseline Reset restores dashes rather than fabricated counts. Keep integrity body and supported-warning entry point unchanged. **Validation:** `V-3`, `V-4`.
* [x] `T3.2` **Change:** Display only unmatched and multiply matched A-row groups from the selected baseline/trial, with input positions, possibly truncated key values, remote match counts and output contributions. **Target:** dialog and component tests. **Current → required:** `all` filter and server page events → browser slice of the returned bounded group; switch side/group, page, or page size locally. Show complete exception count separately from returned count; label `row_cap_reached`, `budget_exhausted`, finding truncation and truncated keys. Empty groups and out-of-range pages should remain readable; no correct A rows. Reset returns to the initial selection. **Validation:** `V-3`, `V-4`.

**Completion evidence:** Dialog and composable tests show no API call or normalization on page/group/size change, and no stale comparison after a control edit.

### Area 4: Validate the cutover and document its impact

**Objective:** Remove stateless route documentation, describe the new workflow, and preserve authorization and integrity behavior.

**Affected code and docs:** `backend/tests/api/v1/test_link_troubleshooter.py`, `backend/tests/services/test_link_troubleshooter_service.py`, `backend/tests/mappers/test_link_troubleshooter_mapper.py`, `backend/tests/authorization/test_route_authentication.py`, `docs/AUTHORIZATION_ROUTE_INVENTORY.md`, `docs/USER_GUIDE.md`, `docs/DESIGN.md`. The change PR body uses the existing `.github/pull_request_template.md`; no versioned release-note file is assigned yet.

**Dependencies:** Areas 1–3.

* [x] `T4.1` **Change:** Replace old stateless-paging expectations with context-only authorization, 410, non-reproduction, incomplete baseline and 422 tests. **Target:** the listed backend tests and inventory. **Current → required:** stateless route assertions and inventory row → no stateless route, four protected context routes, rejected paging fields, and unchanged 404 concealment/owner access. Keep service/mapper parity and bounded-response regression checks. **Validation:** `V-1`, `V-4`.
* [ ] `T4.2` **Change:** Update user/design documentation and author the release/upgrade text in the change PR. **Target:** `docs/USER_GUIDE.md::Troubleshooting a Link`, `docs/DESIGN.md::Constraints and Assumptions`, `docs/AUTHORIZATION_ROUTE_INVENTORY.md`, and the change PR body's **User-facing release note** and **Upgrade notes** sections. **Current → required:** guide says each page re-reads data and single-worker note omits dialog contexts → opening and post-expiry refresh read data, local paging does not, and worker constraint names dialog contexts. Explicitly tell stateless API consumers to migrate from `POST /projects/{project_name}/link-troubleshooter` with paging fields to context open/trial/DELETE; no speculative release version. **Validation:** `V-4`.
  * **Execution note (2026-11-07):** User/design docs and the route inventory are updated. Release/upgrade text is prepared but must be added to the change PR body when that PR is created.

**Completion evidence:** Inventory matches registered routes; docs and tested behavior agree; upgrade guidance still needs the change PR.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
|---|---|---|---|
| `PH3-AC-1` (`P-AC-5`) | `T2.1`, `T2.2`, `T2.3`, `T3.1` | `V-2`, `V-3` | Changed controls and delayed responses never restore stale trials. |
| `PH3-AC-2` (`P-AC-6`) | `T2.3`, `T3.1`, `T3.2` | `V-2`, `V-3` | No-request Reset restores latest complete/incomplete baseline and initial selection. |
| `PH3-AC-3` (`P-AC-9`) | `T1.1`, `T1.2`, `T3.2`, `T4.1`, `T4.2` | `V-1`, `V-2`, `V-3`, `V-4` | Local browsing has zero calls; request fields rejected; breaking change documented. |
| `PH3-AC-4` (`P-AC-8`) | `T2.3`, `T4.1` | `V-2`, `V-3`, `V-4` | Close clears state and attempts owned-context DELETE; no saved-state writes. |
| `PH3-AC-5` (`P-AC-1`, `P-AC-7`, `P-AC-10`) | `T2.1`, `T2.2`, `T3.1`, `T4.1` | `V-1`, `V-2`, `V-3`, `V-4` | 410 refresh reopens original warning, old trial is discarded, failure is explicit. |

## Validation And Testing

| ID | Check and target | Command or executable method | Covers | Expected result | Baseline |
|---|---|---|---|---|---|
| `V-1` | Context-only API/service/mapper regression; `backend/tests/api/v1/test_link_troubleshooter.py`, `backend/tests/services/test_link_troubleshooter_service.py`, `backend/tests/mappers/test_link_troubleshooter_mapper.py` | `.venv/bin/pytest backend/tests/api/v1/test_link_troubleshooter.py backend/tests/services/test_link_troubleshooter_service.py backend/tests/mappers/test_link_troubleshooter_mapper.py -q` | `PH3-AC-3`, `PH3-AC-5` | Old route absent, open/trial paging keys yield 422, authorized context lifecycle and bounded complete/incomplete results pass. | Pass 2026-11-07: 25 API + 14 service + 12 mapper tests pass after the cutover. |
| `V-2` | Client/composable/unit; `frontend/src/api/__tests__/linkTroubleshooter.test.ts`, `frontend/src/composables/__tests__/useLinkTroubleshooter.test.ts`, `frontend/src/utils/__tests__/linkTroubleshooter.test.ts` | `pnpm --dir frontend exec vitest run src/api/__tests__/linkTroubleshooter.test.ts src/composables/__tests__/useLinkTroubleshooter.test.ts src/utils/__tests__/linkTroubleshooter.test.ts` | `PH3-AC-1`, `PH3-AC-2`, `PH3-AC-3`, `PH3-AC-4`, `PH3-AC-5` | Mocked 410, failed re-reproduction, incomplete baseline, late completions, explicit/inherited settings and DELETE are correct; page changes make no call. | Pass 2026-11-07: 53 client, composable, and utility tests pass. |
| `V-3` | Dialog component; `frontend/src/components/validation/__tests__/LinkTroubleshooterDialog.test.ts` | `pnpm --dir frontend exec vitest run src/components/validation/__tests__/LinkTroubleshooterDialog.test.ts` | `PH3-AC-1`–`PH3-AC-5` | Both groups, full vs returned counts, truncation, null controls, Reset, refresh, failed trial and unchanged integrity UI render correctly; no request on local paging. | Pass 2026-11-07: 18 dialog tests pass; 40 neighboring validation/integrity tests also pass. |
| `V-4` | Route authorization, compatibility and type/documentation checks | `.venv/bin/pytest backend/tests/authorization/test_route_authentication.py backend/tests/api/v1/test_link_troubleshooter.py -q`; `pnpm --dir frontend exec vue-tsc --noEmit`; `pnpm --dir frontend exec eslint src/api/linkTroubleshooter.ts src/types/linkTroubleshooter.ts src/composables/useLinkTroubleshooter.ts src/components/validation/LinkTroubleshooterDialog.vue`; inspect registered OpenAPI paths and request schemas, guide/design text, and change PR note/upgrade sections against the shipped routes. | `PH3-AC-3`, `PH3-AC-4`, `PH3-AC-5` | Auth inventory matches context routes, old path absent, typing/lint pass, release note explains the breaking change. | Pass 2026-11-07 for routes, typing, and lint (0 `vue-tsc` errors, 0 ESLint errors, backend lint 10.00/10). Release/upgrade text is prepared but not published because no change PR exists yet. |

After implementation, also run the existing `ValidationMessageList` and `ValidationPanel` component tests to preserve warning gating, plus the neighboring integrity-dialog tests; no new feature scope is implied.

## Deliverables

All planned file targets already exist; there are no `NEW` code or test files. The release-note text is an output of the future change PR, not a versioned file to create now.

| Deliverable | Target | Task IDs | Completion evidence |
|---|---|---|---|
| Context-only API and access inventory | `backend/app/api/v1/endpoints/link_troubleshooter.py`, `backend/app/models/link_troubleshooter.py`, `backend/app/models/__init__.py`, `backend/app/services/link_troubleshooter_service.py`, `backend/app/mappers/link_troubleshooter_mapper.py`, `docs/AUTHORIZATION_ROUTE_INVENTORY.md` | `T1.1`, `T4.1` | Protected context routes only; paging fields rejected. |
| Typed browser client | `frontend/src/api/linkTroubleshooter.ts`, `frontend/src/types/linkTroubleshooter.ts`, `frontend/src/api/__tests__/linkTroubleshooter.test.ts` | `T1.2` | Open/trial/close requests match API schema. |
| Snapshot-aware trial lifecycle | `frontend/src/composables/useLinkTroubleshooter.ts`, `frontend/src/composables/__tests__/useLinkTroubleshooter.test.ts`, `frontend/src/utils/linkTroubleshooter.ts`, `frontend/src/utils/__tests__/linkTroubleshooter.test.ts` | `T2.1`–`T2.3` | Refresh, invalidation, Reset, Close and noncandidate warning checks pass. |
| Experiment dialog | `frontend/src/components/validation/LinkTroubleshooterDialog.vue`, `frontend/src/components/validation/__tests__/LinkTroubleshooterDialog.test.ts` | `T3.1`, `T3.2` | Controls and exception groups work without page requests. |
| Backend regression tests | `backend/tests/api/v1/test_link_troubleshooter.py`, `backend/tests/services/test_link_troubleshooter_service.py`, `backend/tests/mappers/test_link_troubleshooter_mapper.py`, `backend/tests/authorization/test_route_authentication.py` | `T4.1` | `V-1`, `V-4` pass after cutover. |
| User and release documentation | `docs/USER_GUIDE.md`, `docs/DESIGN.md`; future change PR body using `.github/pull_request_template.md` | `T4.2` | Refresh/local paging and API migration accurately described. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
|---|---|---|---|
| Area 1: Request contract | Done | Phase 3 readiness confirmed 2026-11-07 | Stateless route and DTOs removed; paging fields rejected with 422. |
| Area 2: Snapshot-aware state | Done | Area 1 | Context lifecycle, 410 refresh, reset, close, and race guards implemented and tested. |
| Area 3: Dialog | Done | Areas 1–2 | Controls, settings, and local bounded exception browsing implemented and tested. |
| Area 4: Validation and docs | In progress | Areas 1–3 | Tests, inventory, guide, and design note updated; release/upgrade text awaits the change PR. |

## Definition Of Done

- [x] Phase 3 is explicitly marked ready in its source phase plan before implementation; this plan's readiness was updated after confirming the prerequisite suites pass (150 tests, 2026-11-07).
- [x] Every `PH3-AC-*` criterion has passing task and validation evidence for `VM-5` and `VM-6`.
- [x] Areas 1–3 and their deliverables are complete; no stateless paging client or route remains.
- [x] In-flight edits/Reset/Close, 410 refresh, failure to reproduce, incomplete baselines, and local navigation have regression tests.
- [x] Current project access, saved-data/cache immutability, bounded detail and production link behavior are preserved.
- [ ] Type checks, lint, focused backend/frontend tests, and route inventory checks pass; release and upgrade notes explain the breaking API contract. (Checks pass; release/upgrade notes await the change PR.)
- [x] Deviations and follow-up work are documented; no unresolved correctness or validation decision remains.

## Risks And Open Questions

- **Readiness gate (resolved):** The source phase plan now marks Phase 3 ready, and the Phase 1/2 contracts and `D1`–`D13` decisions are in place. No further gate blocks implementation.
- **Unavailable baseline settings:** A rejected configured diagnostic can leave `baseline.settings` null. Use the saved relationship and explicit/omitted constraint fields to initialize controls; do not present a guessed effective null policy. Test projected-budget and invalid-key incomplete baselines before calling the dialog complete.
- **Release-note timing:** Versioned files under `docs/whats-new/` are generated for a release. Record the compatibility break in the future change PR's required release/upgrade sections rather than inventing a version or editing a published release note.
