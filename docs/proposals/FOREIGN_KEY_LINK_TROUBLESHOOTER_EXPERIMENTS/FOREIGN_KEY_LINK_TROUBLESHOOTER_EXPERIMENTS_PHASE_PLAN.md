# Foreign-Key Link Troubleshooter Experiments — Phase Plan

Source: [Foreign-Key Link Troubleshooter Experiments](./FOREIGN_KEY_LINK_TROUBLESHOOTER_EXPERIMENTS.md).

## Summary

Extend the existing link troubleshooter in three phases: retain one authorized, fixed-input baseline for up to 15 minutes; run bounded trials and return complete comparisons; then switch the dialog to local exception browsing, automatic baseline refresh after expiry, and immediate reset. Preserve the existing warning eligibility and reproduction checks. An experiment never changes a saved project.

## Problem

Today, each trial and page request rebuilds the baseline, so source changes can enter a comparison and browsing repeats the replay. Only trial key pairs can be changed, and the server pages A rows rather than returning bounded exception groups.

## Scope

This plan covers temporary in-process contexts with 15-minute snapshots, refreshed baselines, inner/left and supported null-key trials, complete comparison totals with bounded exception detail, browser-only paging, reset, and the coordinated API contract change.

It does not cover other join types or constraints, editing earlier pipeline stages, saving trials, full result browsing, downstream validation, or the integrity inspector.

## Current Position

- The source proposal is approved but not implemented.
- The baseline service already produces the pre-link A and processed B frames; the trial service re-links copies through the production linker within one request.
- The coordinating service rebuilds the baseline on each request. The API accepts `page`, `page_size`, and `row_filter` and returns a server-sliced page.
- The client clears its result while requesting another response; its current `reset()` closes out dialog state rather than restoring the baseline. The backend's existing in-process state already requires one Uvicorn worker.

## Phase Plan

### Phase 1: Fixed-Input Snapshot Context

**Goal**

Keep the reproduced link inputs and original settings fixed, authorized, and resource-bounded for a 15-minute snapshot.

**Focus**

- Open a context only after the selected warning reproduces. Retain the A/B inputs, resolved link configuration, and baseline diagnostic status without retaining joined outputs.
- Allow an explicitly incomplete baseline when configured-key diagnostics fail, exceed limits, or are not run; keep trial execution available.
- Enforce user/project ownership and current read access on every operation. Expire each snapshot 15 minutes after creation, remove abandoned contexts periodically, and allow best-effort cleanup on Close.
- Bound retained A/B input size and estimate the peak memory for copies and materialized AB before merging; report `ProjectedBudgetExceeded` when the configurable limit (100 MiB by default) is exceeded. Keep the existing join-row limit; defer separate concurrent-computation admission.

**Depends On**

- Existing warning eligibility, saved-FK identification, and reproduction checks.
- Configurable 100 MiB default budget and the approved per-computation peak rule for inputs, copies, and joins, specified below.

**Outputs**

- A context identifier and fixed baseline state for later trials; explicit incomplete, expired, and projected-budget outcomes.

**Acceptance Criteria**

- `PH1-AC-1` (from `P-AC-1`) Opening creates a context only after reproduction, and retained inputs and original configuration remain fixed until its 15-minute expiry.
- `PH1-AC-2` (from `P-AC-10`) Failed, incomplete, or skipped configured-key diagnostics still permit opening and report an incomplete baseline without totals or groups.
- `PH1-AC-3` (from `P-AC-7`) Every context operation enforces ownership and current read access; expiry prevents use of the old inputs and periodic cleanup removes abandoned contexts.
- `PH1-AC-4` (from `P-AC-7`) Retained inputs and projected peak memory are checked against the configured limit (100 MiB by default) before joining; excess work reports `ProjectedBudgetExceeded` without complete metrics.

**Validation Milestones**

- `VM-1` Verify warning eligibility, fixed inputs despite source changes before expiry, and incomplete-baseline opening (`PH1-AC-1`, `PH1-AC-2`).
- `VM-2` Verify cross-user and revoked access, expiration, abandoned-context cleanup, and projected-budget rejection for inputs, copies, and joins (`PH1-AC-3`, `PH1-AC-4`).

**Task-Plan Handoff**

- Source: `P-AC-1`, `P-AC-7`, `P-AC-10`. Preserve single-worker, in-process storage and existing join-row limits; do not add persistence or log row values. The TTL is fixed at 15 minutes with periodic expiry and best-effort Close. Use one backend setting for retained-input and per-computation peak checks, defaulting to 100 MiB (`100 * 1024 * 1024` bytes). Reuse the production/null-aware join row preflight and measure actual A/B row widths; include selected B columns, copied frames, and merge intermediates. Project peak as retained A/B bytes + four times A/B input bytes + three times the larger estimated production or diagnostic join output. Handle empty frames and variable-width columns conservatively; the estimate is not a strict peak-memory guarantee. A separate concurrent-admission cap is out of scope.

**Readiness**

Ready for a task plan.

### Phase 2: Production Trials and Bounded Comparison Contract

**Goal**

Compare original and trial link behavior on the same snapshot inputs without rerunning normalization.

**Focus**

- Apply ordered key pairs, inner/left join choice, and only `allow_null_keys` and `null_keys_equal` to independent partial configuration copies. Preserve inherited versus explicit values and production default resolution.
- Return complete totals and link findings only for completed trials. Report blocked, invalid, or oversized trials without success-shaped partial totals; do not mutate retained inputs or saved state.
- Replace server paging with deterministic, separately bounded unmatched and multiply matched A-row groups, complete counts, and explicit truncation of rows, key values, and findings under an aggregate detail budget.

**Depends On**

- Phase 1 fixed snapshot inputs, baseline status, authorization, and projected-memory check.
- Decisions on each group's display cap, key-value and findings budget, and inherited-versus-explicit null-setting representation.

**Outputs**

- Trial request/response contract with complete comparison metrics or explicit failure, and bounded exception groups suitable for local paging.

**Acceptance Criteria**

- `PH2-AC-1` (from `P-AC-2`) Trials accept exactly the supported controls, preserve all other FK settings, and reproduce production null defaults when settings are omitted.
- `PH2-AC-2` (from `P-AC-1`, `P-AC-3`) Each trial re-links the retained A/B inputs from one snapshot; baseline and trial totals/findings match production behavior, and incomplete results are never labeled complete.
- `PH2-AC-3` (from `P-AC-4`) Each response reports exact full-input totals and complete exception counts, deterministic bounded groups, and stated row/detail truncation without listing correct A rows.
- `PH2-AC-4` (from `P-AC-8`) Trials leave retained inputs, saved projects, databases, and production caches unchanged.

**Validation Milestones**

- `VM-3` Compare fixed-input production results across join types, compound keys, omitted and explicit null settings, constraint failures, and oversized joins (`PH2-AC-1`, `PH2-AC-2`, `PH2-AC-4`).
- `VM-4` Verify inner-join losses, multiple matches, deterministic group caps, long keys and findings, exact counts, and explicit payload truncation (`PH2-AC-3`).

**Task-Plan Handoff**

- Source: `P-AC-1`–`P-AC-4`, `P-AC-8`. Keep the original link as the comparison baseline; do not bypass production constraints or treat fewer findings as better matching. Set caps, aggregate budget, and null-setting representation before task planning.

**Readiness**

Requires decisions on group caps, payload budget, and inherited-versus-explicit null-setting representation, plus Phase 1's context contract.

### Phase 3: Dialog Controls and Contract Cutover

**Goal**

Make snapshot-based experiments usable in the dialog and move every caller to the context-based, locally paged contract.

**Focus**

- Initialize controls from the current snapshot's original settings. Run only on explicit request; edits invalidate the displayed trial, and responses are tied to submitted settings and snapshot so late results cannot undo newer edits, refresh, or reset.
- When a context-dependent operation finds the snapshot expired, reopen it through warning reproduction. Replace the baseline and controls, clear the old trial, notify the user that inputs were refreshed, and require a new Run trial. If reproduction fails, show that status rather than a stale comparison.
- Page and switch bounded exception groups entirely in the browser. Reset immediately restores the latest received baseline (including an incomplete baseline), original settings, initial diagnostic selection, and clears trial errors without recomputation or extending the TTL.
- Close with best-effort context cleanup and cleared client state. Remove paging fields from requests; document the break for stateless callers in release notes, update the user guide to describe refresh without re-reading on page changes, and name dialog contexts in the single-worker design note.

**Depends On**

- Phase 1 context lifecycle and Phase 2 trial/exception response contract, including their resolved limit and default-setting decisions.

**Outputs**

- Working experiment dialog, updated API callers and documentation, and validated contract cutover.

**Acceptance Criteria**

- `PH3-AC-1` (from `P-AC-5`) Edits invalidate stale trial results; out-of-order responses cannot replace newer settings or undo Reset or refresh.
- `PH3-AC-2` (from `P-AC-6`) Reset restores original controls and the latest received complete or incomplete baseline immediately without replay, clears errors, restores the initial selection, and does not extend the TTL.
- `PH3-AC-3` (from `P-AC-9`) Paging, group switches, and page-size changes make no request; paging fields are absent from the request contract and the change is documented.
- `PH3-AC-4` (from `P-AC-8`) Closing clears client trial state and requests context cleanup without writing saved data or caches.
- `PH3-AC-5` (from `P-AC-1`, `P-AC-7`, `P-AC-10`) After expiry, the next context-dependent operation reopens through warning reproduction, replaces the baseline, clears the trial, and announces the refresh; it does not run the expired request's trial or compare snapshots. Failed reproduction is explicit.

**Validation Milestones**

- `VM-5` Verify editing, in-flight reset, out-of-order responses across refresh, complete/incomplete baseline restoration, refreshed source data, and reproduction failure (`PH3-AC-1`, `PH3-AC-2`, `PH3-AC-5`).
- `VM-6` Verify local browsing without requests or replay, rejection of paging fields, closing cleanup, and updated caller/user documentation (`PH3-AC-3`, `PH3-AC-4`).

**Task-Plan Handoff**

- Source: `P-AC-1`, `P-AC-5`–`P-AC-10`. Preserve the supported-warning entry point and keep reset distinct from expiry and closing. Refresh using the original warning request, not the expired trial; cut over callers and documentation together without a hybrid stateless-paging path.

**Readiness**

Requires the completed Phase 1/2 contracts and their named decisions before task planning.

## Cross-Phase Rules

- Reuse production linking and diagnostics on retained inputs; a trial never becomes the next baseline, and results from different snapshots are never compared.
- Maintain read authorization, per-computation projected-memory and row limits, bounded response size, and explicit failure/incomplete states throughout. Concurrent-admission limits remain deferred.
- Keep the existing caller behavior until the context-based contract and its browser client can cut over together.

## Validation Strategy

Use focused service and API checks for fixed inputs within a snapshot, authorization, expiry, projected-budget rejection, production parity, and payload limits (`VM-1`–`VM-4`). Then validate refresh and dialog races, reset, local paging, close, and contract cutover across backend and frontend (`VM-5`, `VM-6`). Confirm no writes to saved configuration or production caches and document the incompatible request shape before release.
