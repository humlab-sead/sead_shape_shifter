# Foreign-Key Integrity Troubleshooter — Phase 3 Task Plan

## Phase Summary

**Phase:** [Phase 3: Present integrity inspection in the shared dialog](./FOREIGN_KEY_INTEGRITY_TROUBLESHOOTER_PHASE_PLAN.md#phase-3-present-integrity-inspection-in-the-shared-dialog)  
**Source:** [Foreign-Key Integrity Troubleshooter](./FOREIGN_KEY_INTEGRITY_TROUBLESHOOTER.md)  
**Readiness:** **Validated.** The phase plan marks Phase 3 ready for a task plan. Phase 2's response and inspection-shape decisions are resolved: the Phase 2 task plan marks its areas Done, the integrity endpoint and response exist, and their targeted tests pass.

Offer read-only inspection for eligible `FK_DATA_INTEGRITY` warnings in the existing validation list and shared dialog. Show current unmatched values and bounded local rows without changing the shipped `ROW_COUNT_MISMATCH` action or trials. This phase implements `VM-3`; Phase 2 supplies the authorized, read-only inspection and fixed paging/selection contract.

**Acceptance criteria**

1. [x] `PH3-AC-1` (from `P-AC-1`): Only integrity warnings with resolvable metadata offer an actionable inspection; unsupported or stale warnings explain why they cannot be inspected.
2. [x] `PH3-AC-2` (from `P-AC-4`, `P-AC-5`): The dialog distinguishes complete and returned counts, supports selecting a value for bounded local rows, and identifies the inspected source and columns.
3. [x] `PH3-AC-3` (from `P-AC-7`): The row-count action, dialog behavior, request, response, and eligibility remain unchanged.

**Constraints:** Do not add edits, auto-fixes, reconciliation, or key-pair trials to integrity inspection. Use the existing endpoint and server-issued value token; keep the integrity response separate from the row-count trial model. The frontend can check warning metadata shape, but only the backend can establish whether the saved link still exists and matches its signature. An apparent candidate can therefore return `ineligible`; show that named refusal rather than presenting it as an inspectable result.

## Repository Findings

**Repository basis:** `feature/foreign-key-integrity-trouble-shooter` at `c05f2d7d`, 2026-11-06; the worktree was clean during inspection. Graphify identified the dialog's callers and tests; code, response models, endpoint, and tests below were checked directly. Phase 2's completed tracker and passing API/service checks establish its dependency; no new API decision is needed.

| Evidence | Verified finding | Planning implication |
| --- | --- | --- |
| [`src/transforms/link_resolution.py::resolve_integrity_issue`](../../../src/transforms/link_resolution.py), [`backend/app/services/integrity_troubleshooter_service.py::IntegrityTroubleshooterService.inspect`](../../../backend/app/services/integrity_troubleshooter_service.py) | The saved FK is checked by entity, integer index, and signature without restricting join type. Refusals include `missing_metadata`, `index_out_of_range`, and `signature_mismatch`; the service returns `ineligible`, `not_reproduced`, or `reproduced` with a reason and message. A changed count can still have **current** values. | Gate only structurally usable warnings in the list; display backend refusals and current results without assuming a frontend shape check proves the link is still valid. Do not hide current values solely because the count changed. |
| [`backend/app/models/integrity_troubleshooter.py::IntegrityTroubleshootRequest`, `IntegrityTroubleshootResponse`](../../../backend/app/models/integrity_troubleshooter.py), [`backend/app/api/v1/endpoints/integrity_troubleshooter.py::run_integrity_troubleshooter`](../../../backend/app/api/v1/endpoints/integrity_troubleshooter.py) | The separate POST `/api/v1/projects/{project_name}/integrity-troubleshooter` accepts `issue_type`, `local_entity`, `metadata`, one-based `page`, and optional `selected_value_token`. The result states `source`, relationship, saved keys, recorded/current orphan counts, a value page, and optional selection. | Add a matching frontend type and API client, not nullable trial fields in the existing row-count contract. Use the same authorized endpoint for paging and selection. |
| [`backend/app/models/integrity_troubleshooter.py::IntegrityTroubleshootValuePage`, `IntegrityTroubleshootRows`](../../../backend/app/models/integrity_troubleshooter.py), [`backend/app/services/integrity_troubleshooter_service.py::IntegrityTroubleshooterService._value_page`](../../../backend/app/services/integrity_troubleshooter_service.py) | Each current page has up to 50 distinct key tuples, `distinct_value_count`, `returned_value_count`, `has_next`, and per-value `local_row_count` and typed token. One selection returns up to 20 rows, `total_row_count`, `returned_row_count`, named columns and `columns_truncated`, or `unavailable` with a reason. Every call recomputes current data. | Use the returned token, not a table index or reconstructed string, for a selection request. Label complete versus returned values and rows separately; show stale-selection refusal and reset selection on page or warning changes. |
| [`frontend/src/utils/linkTroubleshooter.ts::isLinkTroubleshootCandidate`, `toLinkTroubleshootRequest`](../../../frontend/src/utils/linkTroubleshooter.ts), [`frontend/src/components/validation/ValidationMessageList.vue`](../../../frontend/src/components/validation/ValidationMessageList.vue) | The action is currently shown only for row-count warnings with supported passes and inner/left joins. The list emits the original validation message through `troubleshoot`. | Add a separate integrity candidate/request check; do not broaden or weaken the row-count predicate. Keep the existing event and make malformed integrity metadata explain its refusal in the expanded message. |
| [`frontend/src/components/validation/ValidationPanel.vue`](../../../frontend/src/components/validation/ValidationPanel.vue), [`frontend/src/views/ProjectDetailView.vue`](../../../frontend/src/views/ProjectDetailView.vue) | The panel forwards `troubleshoot`; the project view already opens `LinkTroubleshooterDialog` with the selected warning and clears it on close. | Reuse that route to the dialog; no new panel or project-level dialog state is required. |
| [`frontend/src/components/validation/LinkTroubleshooterDialog.vue`](../../../frontend/src/components/validation/LinkTroubleshooterDialog.vue), [`frontend/src/composables/useLinkTroubleshooter.ts`](../../../frontend/src/composables/useLinkTroubleshooter.ts), [`frontend/src/types/linkTroubleshooter.ts`](../../../frontend/src/types/linkTroubleshooter.ts) | The dialog currently opens row-count requests and owns editable trial keys, filters, pages, diagnostics, and findings. The composable resets pending results on a new request or close. | Keep that row-count path intact. Add a kind-specific, read-only integrity body inside the shared shell; do not pass integrity issues through the row-count composable. Guard asynchronous results when changing warnings or closing. |
| [`frontend/src/api/linkTroubleshooter.ts`](../../../frontend/src/api/linkTroubleshooter.ts), [`frontend/src/api/index.ts`](../../../frontend/src/api/index.ts), [`frontend/src/types/index.ts`](../../../frontend/src/types/index.ts) | Frontend calls use `apiRequest` with an encoded project name; types and API services have central exports. | Follow those conventions for the separate integrity client and typed models. |

## Scope

**In scope:** Integrity-only frontend request/response types and API call; structurally checked warning action and local refusal explanation; a read-only integrity body in the shared dialog showing relationship, status, current value pages, and selected local rows; frontend tests and row-count regressions.

**Out of scope:** Backend/Core changes, changes to Phase 2 paging or selection semantics, project edits, repairs, trial settings for integrity, other FK warning kinds, changing the warning's existing `field`, and redesigning the existing dialog or validation panel.

**Affected contracts:** Validation messages carry `code`, `entity`, and metadata (`fk_index`, `fk_signature`, `orphan_count`); the integrity client must use the existing Phase 2 request and response shape. Row-count requests, responses, eligibility, and trial state must remain exactly as shipped. The frontend displays only source-provided columns and rows; it does not fetch another data source directly.

## Work Breakdown

### Area 1: Type and call the existing integrity endpoint

**Objective:** Send warning identity, page, and optional selection through a typed frontend API call without changing the row-count API.

**Affected code:** `frontend/src/types/integrityTroubleshooter.ts` (**NEW**), `frontend/src/types/index.ts`, `frontend/src/api/integrityTroubleshooter.ts` (**NEW**), `frontend/src/api/index.ts`, `frontend/src/api/__tests__/integrityTroubleshooter.test.ts` (**NEW**).

**Dependencies:** Completed Phase 2 response and endpoint; none of this phase's other areas.

**Tasks:**

* [x] `T1.1` **Change:** Define integrity-only request and response types.
  * **Target:** `frontend/src/types/integrityTroubleshooter.ts` (**NEW**) and `frontend/src/types/index.ts`.
  * **Current → required:** Only the row-count trial types exist → types mirror Phase 2's nullable relationship, configured keys, current/recorded counts, value page, selected rows, status/reason/message, and source. Keep tuple values and row cells as `unknown`, tokens as `string`, and request metadata compatible with `ValidationError.metadata`.
  * **Implementation:** Express `reproduced | not_reproduced | ineligible` and `selected | unavailable` as unions; represent `page`, `page_size`, `distinct_value_count`, `returned_value_count`, `has_next`, `local_row_count`, `selected_value_token`, row count/columns/truncation, and null fields explicitly. Export through the existing types index.
  * **Constraints:** Do not add integrity fields to `LinkTroubleshootResponse` or change `ValidationError` transport.
  * **Validation:** `V-1`, `V-5`: type-check the consuming UI and assert exact request/response use in the new API test.
* [x] `T1.2` **Change:** Call the separate authorized integrity route.
  * **Target:** `frontend/src/api/integrityTroubleshooter.ts` (**NEW**), `frontend/src/api/index.ts`, `frontend/src/api/__tests__/integrityTroubleshooter.test.ts` (**NEW**).
  * **Current → required:** The client calls only `/link-troubleshooter` → add `apiRequest` POST to `/projects/${encodeURIComponent(projectName)}/integrity-troubleshooter` and export it alongside (not instead of) the row-count client.
  * **Implementation:** Forward `issue_type: 'FK_DATA_INTEGRITY'`, `local_entity`, warning metadata, one-based `page`, and optional server token without converting its typed key values in the browser.
  * **Constraints:** Every page and selection uses the same protected route; no cached response or unauthenticated direct fetch.
  * **Validation:** `V-1`: test encoded project names, first page, later page, and selected token, including exact URL/body and untouched row-count client.

**Completion evidence:** New typed client returns the separate integrity envelope; the row-count API test still passes.

### Area 2: Offer the action only for supported warning metadata

**Objective:** Show one validation-list entry point for integrity candidates and explain locally uninspectable warnings.

**Affected code:** `frontend/src/utils/linkTroubleshooter.ts`, `frontend/src/utils/__tests__/linkTroubleshooter.test.ts`, `frontend/src/components/validation/ValidationMessageList.vue`, `frontend/src/components/validation/__tests__/ValidationMessageList.test.ts`.

**Dependencies:** Area 1's request type.

**Tasks:**

* [x] `T2.1` **Change:** Check integrity warning metadata independently of row-count eligibility.
  * **Target:** `frontend/src/utils/linkTroubleshooter.ts` and `frontend/src/utils/__tests__/linkTroubleshooter.test.ts`.
  * **Current → required:** `isLinkTroubleshootCandidate` and `toLinkTroubleshootRequest` accept only row-count issues → add integrity-only predicate, request builder, and concrete explanation for malformed local identity, leaving both existing row-count functions' behavior unchanged.
  * **Implementation:** Require `FK_DATA_INTEGRITY`, a nonblank local entity, an integer nonnegative `fk_index`, and a string `fk_signature`; do not require `link_pass` or restrict right/outer joins. Pass the original metadata unchanged. Missing `orphan_count` is an explicit backend `missing_warning_count` outcome, not a fabricated count.
  * **Constraints:** Do not claim to validate the saved signature in the browser; out-of-range index and stale signature are determined by the backend on inspection.
  * **Validation:** `V-2`: test valid identity (including right/outer joins and duplicate remote entity names), missing/invalid index and signature, missing entity, unsupported code, original metadata unchanged, and existing row-count inner/left and unsupported-join cases.
* [x] `T2.2` **Change:** Show the existing action for integrity candidates and an explanation for malformed integrity warnings.
  * **Target:** `frontend/src/components/validation/ValidationMessageList.vue` and `frontend/src/components/validation/__tests__/ValidationMessageList.test.ts`.
  * **Current → required:** Expanded messages show `Troubleshoot link` only for row-count candidates → emit the original integrity candidate using the same `troubleshoot` event, and show a non-actionable reason when a warning lacks usable local metadata.
  * **Implementation:** Keep the existing action label, click behavior, and expanded-row state. Do not offer the action for unrelated warning codes; display the local refusal in the expanded warning rather than suggesting an inspection is available.
  * **Constraints:** Do not call the backend from every list row to preflight saved links. A structurally valid but stale warning is refused in the dialog using the backend's `ineligible` reason.
  * **Validation:** `V-2`: assert candidate emission, local refusal visibility and no action, unrelated warnings unchanged, and existing row-count action/event regression.

**Completion evidence:** Exactly one action appears for each eligible warning; malformed integrity warnings explain why no action is offered; stale saved links are not misrepresented as resolved.

### Area 3: Render a read-only integrity body in the shared dialog

**Objective:** Display the Phase 2 result and bounded, selectable current data while keeping trial controls exclusive to row-count issues.

**Affected code:** `frontend/src/components/validation/IntegrityTroubleshooterBody.vue` (**NEW**), `frontend/src/components/validation/LinkTroubleshooterDialog.vue`, `frontend/src/components/validation/__tests__/IntegrityTroubleshooterBody.test.ts` (**NEW**), `frontend/src/components/validation/__tests__/LinkTroubleshooterDialog.test.ts`.

**Dependencies:** Areas 1 and 2.

**Tasks:**

* [x] `T3.1` **Change:** Add the integrity-only, read-only inspection body.
  * **Target:** `frontend/src/components/validation/IntegrityTroubleshooterBody.vue` (**NEW**) and `frontend/src/components/validation/__tests__/IntegrityTroubleshooterBody.test.ts` (**NEW**).
  * **Current → required:** No frontend consumer of integrity responses exists → open page 1 for the warning, show backend `status`, `reason`, and `message` (including `ineligible` and `not_reproduced`), relationship/entity/index/join/constraints and saved keys when provided, and label `source` as current inspected data.
  * **Implementation:** Show `recorded_orphan_count` only as the warning's recorded count, `current_orphan_count` as current, and `values.distinct_value_count` separately from `values.returned_value_count`; show key tuples, `local_row_count`, page number/size, and navigation based on the returned page and total. Send the selected value's opaque `token` with the current page; show `total_row_count`, `returned_row_count`, named columns, `columns_truncated`, and only response-provided row cells. Show `selected.reason`/`message` for `unavailable` instead of stale rows. Clear the selection when changing page or warning. Surface request errors and clear stale results; ignore late responses after another request or close.
  * **Constraints:** The result may include current values with `not_reproduced`/`count_changed`; render them with a clear current-data label. Never reconstruct a token from display values, infer a count from a truncated page, or show join-trial inputs, save buttons, or auto-fix actions.
  * **Validation:** `V-3`: test reproduced and changed-count current values, unavailable/full-frame refusal, ineligible stale signature, multiple pages (including empty page), composite/null key rendering, correct token selection after paging, 20-row and column-truncation display, `value_no_longer_unmatched`, request failures, and late responses after switching/closing.
* [x] `T3.2` **Change:** Dispatch the shared dialog by warning kind without changing the row-count body.
  * **Target:** `frontend/src/components/validation/LinkTroubleshooterDialog.vue` and `frontend/src/components/validation/__tests__/LinkTroubleshooterDialog.test.ts`.
  * **Current → required:** Every open warning enters the row-count request watcher → mount the integrity body for `FK_DATA_INTEGRITY` candidates, retaining the existing shell, header, close action, and unmodified row-count trial path.
  * **Implementation:** Branch on issue code before building or opening the row-count request. Reset row-count state on close/switch, and unmount/reset integrity state on close/switch so responses cannot cross warning kinds. For a manually opened malformed warning, show its specific refusal without sending either request.
  * **Constraints:** Do not rewrite `useLinkTroubleshooter`, row-count request handling, trials, or `ValidationPanel`/`ProjectDetailView` event wiring.
  * **Validation:** `V-3`, `V-4`: assert integrity open/close/switch and row-count no-trial-leakage; rerun the existing dialog, composable, panel, API, and utility row-count tests unchanged.

**Completion evidence:** `VM-3` shows current values and one bounded selection in the shared dialog; integrity never opens the row-count endpoint or trial UI, and row-count warnings still use their original request and controls.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
| --- | --- | --- | --- |
| `PH3-AC-1` (`P-AC-1`) | `T2.1`, `T2.2`, `T3.1`, `T3.2` | `V-2`, `V-3` | Valid identity gives one action; malformed metadata gives a local reason and no action; stale saved signature/index yields a visible backend `ineligible` reason and no inspectable values. |
| `PH3-AC-2` (`P-AC-4`, `P-AC-5`) | `T1.1`, `T1.2`, `T3.1` | `V-1`, `V-3`, `V-5` | Current/full and returned value counts, per-value row counts, token-selected bounded rows, source, column names, and truncation appear with correct labels. |
| `PH3-AC-3` (`P-AC-7`) | `T1.2`, `T2.1`, `T2.2`, `T3.2` | `V-1`, `V-2`, `V-3`, `V-4`, `V-6` | Same row-count action, request, response, eligibility, join controls, and protected backend endpoint pass existing tests. |

## Validation And Testing

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
| --- | --- | --- | --- | --- | --- |
| `V-1` | New client, `frontend/src/api/__tests__/integrityTroubleshooter.test.ts` (**NEW**), and existing `frontend/src/api/__tests__/linkTroubleshooter.test.ts` | `cd frontend && pnpm exec vitest run src/api/__tests__/integrityTroubleshooter.test.ts src/api/__tests__/linkTroubleshooter.test.ts` | `PH3-AC-2`, `PH3-AC-3` | Encoded project, exact initial/page/selection payloads and endpoint; old row-count payload unchanged. | Pass 2026-11-06: `integrityTroubleshooter.test.ts` (3 tests) and the existing row-count client test pass in the eight-file frontend run (80 tests). |
| `V-2` | Candidate and list tests in `frontend/src/utils/__tests__/linkTroubleshooter.test.ts` and `frontend/src/components/validation/__tests__/ValidationMessageList.test.ts` | `cd frontend && pnpm exec vitest run src/utils/__tests__/linkTroubleshooter.test.ts src/components/validation/__tests__/ValidationMessageList.test.ts` | `PH3-AC-1`, `PH3-AC-3` | Supported integrity warnings emit, invalid ones explain refusal, other warnings and row-count candidates retain existing behavior. | Pass 2026-11-06: utility and list tests pass with the new integrity cases in the eight-file frontend run (80 tests; list file 15 tests). |
| `V-3` | New integrity body test `frontend/src/components/validation/__tests__/IntegrityTroubleshooterBody.test.ts` (**NEW**) and existing dialog test `frontend/src/components/validation/__tests__/LinkTroubleshooterDialog.test.ts` | `cd frontend && pnpm exec vitest run src/components/validation/__tests__/IntegrityTroubleshooterBody.test.ts src/components/validation/__tests__/LinkTroubleshooterDialog.test.ts` | `PH3-AC-1`, `PH3-AC-2`, `PH3-AC-3` | Correct read-only statuses, source, counts, paging, token selection, unavailable/error/reset handling; no integrity trials; row-count dialog still works. | Pass 2026-11-06: new body test (11 tests) and existing dialog test (15 tests) pass. |
| `V-4` | Existing row-count frontend regression: `ValidationPanel`, composable, client, dialog and utility tests | `cd frontend && pnpm exec vitest run src/utils/__tests__/linkTroubleshooter.test.ts src/components/validation/__tests__/ValidationMessageList.test.ts src/components/validation/__tests__/ValidationPanel.test.ts src/components/validation/__tests__/LinkTroubleshooterDialog.test.ts src/composables/__tests__/useLinkTroubleshooter.test.ts src/api/__tests__/linkTroubleshooter.test.ts` | `PH3-AC-3` | Row-count entry, event forwarding, saved keys/trials, filters/paging, request and response remain unchanged. | Pass 2026-11-06: 8 files, 80 tests including the new integrity files; only the expected composable rejection log, no failures. |
| `V-5` | Type, lint and format checks on all changed frontend files | `cd frontend && pnpm exec vue-tsc --noEmit`; `cd frontend && pnpm exec eslint src/types/integrityTroubleshooter.ts src/types/index.ts src/api/integrityTroubleshooter.ts src/api/index.ts src/api/__tests__/integrityTroubleshooter.test.ts src/utils/linkTroubleshooter.ts src/utils/__tests__/linkTroubleshooter.test.ts src/components/validation/ValidationMessageList.vue src/components/validation/__tests__/ValidationMessageList.test.ts src/components/validation/IntegrityTroubleshooterBody.vue src/components/validation/__tests__/IntegrityTroubleshooterBody.test.ts src/components/validation/LinkTroubleshooterDialog.vue src/components/validation/__tests__/LinkTroubleshooterDialog.test.ts`; `cd frontend && pnpm exec prettier --check src/types/integrityTroubleshooter.ts src/api/integrityTroubleshooter.ts src/api/__tests__/integrityTroubleshooter.test.ts src/utils/linkTroubleshooter.ts src/components/validation/ValidationMessageList.vue src/components/validation/IntegrityTroubleshooterBody.vue src/components/validation/LinkTroubleshooterDialog.vue` | All | No new TypeScript, lint, or formatting errors; include other changed frontend files if needed. | Pass 2026-11-06: `vue-tsc --noEmit` clean on the frontend; ESLint and Prettier clean on all 13 changed files. |
| `V-6` | Phase 2 and row-count backend compatibility | `uv run pytest -n 0 backend/tests/api/v1/test_integrity_troubleshooter.py backend/tests/services/test_integrity_troubleshooter_service.py backend/tests/api/v1/test_link_troubleshooter.py -q` | `PH3-AC-3`, Phase 2 dependency | The existing endpoint contracts, protected request, bounded response, and row-count route still pass. | Pass 2026-11-06: 42 tests, exit 0, run with `.venv/bin/python -m pytest`; `uv run pytest` reaches the rtk wrapper, which reported no tests collected. |

All of `V-1` through `V-6` were run after implementation on 2026-11-06; together they cover `VM-3`. No new backend, migration, or generated artifact is planned. The frontend checks do not replace the Phase 2 server-side authorization tests.

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Separate frontend contract | `frontend/src/types/integrityTroubleshooter.ts` (**NEW**), `frontend/src/types/index.ts` | `T1.1` | Types match the Phase 2 request and response; `V-5` passes. |
| Separate API client and test | `frontend/src/api/integrityTroubleshooter.ts` (**NEW**), `frontend/src/api/index.ts`, `frontend/src/api/__tests__/integrityTroubleshooter.test.ts` (**NEW**) | `T1.2` | `V-1` confirms route and payload, including token. |
| Warning eligibility and action | `frontend/src/utils/linkTroubleshooter.ts`, `frontend/src/utils/__tests__/linkTroubleshooter.test.ts`, `frontend/src/components/validation/ValidationMessageList.vue`, `frontend/src/components/validation/__tests__/ValidationMessageList.test.ts` | `T2.1`, `T2.2` | `V-2` confirms candidate, refusal and original event behavior. |
| Read-only integrity view and shared dialog | `frontend/src/components/validation/IntegrityTroubleshooterBody.vue` (**NEW**), `frontend/src/components/validation/__tests__/IntegrityTroubleshooterBody.test.ts` (**NEW**), `frontend/src/components/validation/LinkTroubleshooterDialog.vue`, `frontend/src/components/validation/__tests__/LinkTroubleshooterDialog.test.ts` | `T3.1`, `T3.2` | `V-3` covers current values, rows, refusal and state; `V-4` preserves trials. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Type and call integrity endpoint | Done | Phase 2 (Done) | Contract and route verified. |
| Area 2: Offer supported warning action | Done | Area 1 | Saved-link staleness remains a backend decision. |
| Area 3: Render integrity body | Done | Areas 1–2 | Preserve row-count trial path. |

## Definition Of Done

* [x] `PH3-AC-1` through `PH3-AC-3` each have completed tasks and passing validation (`VM-3`).
* [x] All three areas and listed deliverables are complete; `V-1` through `V-6` pass on the final change.
* [x] A stale or malformed integrity warning explains its refusal; changed/current values and unavailable selections are not presented as saved warning data.
* [x] Complete and returned value/row counts, current full-normalization source, named columns and truncation are visible where the response provides them.
* [x] The shared dialog offers no integrity key trials or edits, and row-count action, request, response, eligibility, and trial behavior pass regression tests unchanged.
* [x] Type checks and lint pass; deviations and follow-up work are recorded, with no unresolved decision affecting implementation or validation.

## Risks And Open Questions

* **Backend-only staleness:** The validation list has no saved-project resolver. It can filter invalid metadata but cannot know whether an otherwise well-formed signature is stale until the authorized inspection call. Display the `ineligible` reason in the dialog and no value/row controls; do not label a local shape check as proof of saved-link eligibility.
* **Current data can change between calls:** Pages are deterministic only for unchanged data. State the response source, clear selected rows when moving pages, use the opaque token for new selections, and show the backend's `value_no_longer_unmatched` refusal if a value changed. No snapshot or fingerprint is part of this phase.
