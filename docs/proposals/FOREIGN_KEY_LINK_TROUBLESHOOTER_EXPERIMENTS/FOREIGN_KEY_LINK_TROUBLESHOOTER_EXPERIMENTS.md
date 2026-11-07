# Foreign-Key Link Troubleshooter Experiments

## Status

- Approved follow-up change request; not implemented
- Scope: fixed-input snapshots with trial keys, inner/left joins, limited constraints, refresh, and reset
- Goal: let users understand how link settings affect rows and validation without changing the saved project
- Extends: [Foreign-Key Link Troubleshooter](../done/FOREIGN_KEY_LINK_TROUBLESHOOTER/FOREIGN_KEY_LINK_TROUBLESHOOTER.md). Its original acceptance criteria remain unchanged.
- Delivery: [Foreign-Key Link Troubleshooter Experiments Phase Plan](./FOREIGN_KEY_LINK_TROUBLESHOOTER_EXPERIMENTS_PHASE_PLAN.md).

## Summary

Keep the pre-link A input and processed B input in a temporary server-side context for up to 15 minutes. Every trial within that time re-links the same inputs, so a settings change recomputes only the join. After expiry, the next operation needing those inputs refreshes the context and baseline through warning reproduction, clears the previous trial, and tells the user the inputs were refreshed. Return complete totals and bounded exception groups in one response and page them in the browser. Reset restores the current baseline immediately.

## Problem

The current troubleshooter only permits key-pair changes. Users cannot explore why a left join retains unmatched rows or how null-key settings affect matches.

Rebuilding the baseline for every request causes two more problems. Source changes can enter a comparison, so a difference cannot be attributed to trial settings. And each page of A-row diagnostics repeats the replay, so browsing costs as much as computing.

A troubleshooting view should explain why rows are wrong. Listing every A row buries the exceptions that need attention.

## Scope

- Preserve the existing supported-warning entry point, saved-FK identification, and baseline reproduction checks.
- Hold A/B inputs and original resolved configuration fixed within each 15-minute snapshot; refresh the baseline and clear trials when it expires.
- Edit trial key pairs, choose inner or left join, and control `allow_null_keys` and `null_keys_equal` only.
- Compare baseline and current-trial totals and link-specific findings; return unmatched and multiply matched A rows as bounded groups.
- Restore original settings and results with Reset to baseline.
- Keep all operations read-only and all experiment data temporary.

## Non-Goals

- Revising the original proposal or its acceptance criteria.
- Changing A/B entities, earlier links, pipeline stages, or source data.
- Right, outer, or cross joins; broader constraint editing; new validation semantics.
- Saving or promoting trial settings, persistent experiments, trial history, or export.
- General-purpose result browsing: the view shows exception groups, not a paged listing of every A row.
- Cell-by-cell output comparison or downstream pipeline validation.

## Current Behavior

The [baseline service](../../../backend/app/services/link_baseline_service.py) already retains the inputs the comparison needs: the pre-link local frame as A and the processed remote frame as B. The [trial service](../../../backend/app/services/link_trial_service.py) already re-links deep copies of those frames with a modified FK configuration, so changing keys recomputes only the join and never re-normalizes.

That retention ends with the request. The [coordinating service](../../../backend/app/services/link_troubleshooter_service.py) rebuilds the baseline on every call, including paging and row-filter changes, so the next page repeats the replay. The request model carries `page`, `page_size`, and `row_filter`, and the response returns one server-sliced page.

The [client composable](../../../frontend/src/composables/useLinkTroubleshooter.ts) clears the result on each request. Its existing `reset()` clears the whole dialog context; it is not a user-facing restoration of baseline settings and results.

## Proposed Design

### Fixed inputs and baseline

After reproducing the selected warning, create a temporary server-side context addressed by an opaque identifier. For 15 minutes from creation, retain the pre-link A input, processed B input, the resolved configuration needed to execute the selected link, original FK settings, and the baseline diagnostic result. Do not retain full joined outputs.

Warning reproduction and the configured-key diagnostic trial are separate steps, and the diagnostic trial can fail, be blocked, or exceed its row limit. Reproduction alone is enough to create a context. An incomplete baseline is retained as explicitly incomplete, with no baseline totals or exception groups, instead of blocking the dialog; trials still run against the retained inputs.

The frames this needs are already produced and already reused within one request; only their lifetime changes. A settings change re-links retained inputs instead of running normalization again. Expiry ends that snapshot; the next operation requiring it automatically opens a new context through the existing warning reproduction checks. Recompute A, B, the original settings, and baseline together. Do not compare results from different snapshots or rerun a trial submitted against the expired snapshot. Clear its results and tell the user that the inputs were refreshed, without trying to explain what changed.

The comparison is always between the original link and the current trial:

$$
AB_{\mathrm{baseline}} = \operatorname{link}(A, B; K_0, J_0, C_0)
$$

$$
AB_{\mathrm{trial}} = \operatorname{link}(A, B; K_t, J_t, C_t)
$$

Here K denotes ordered key pairs, J the join type, and C the constraints. A and B are unchanged within a snapshot. A trial never becomes the next baseline. Later source or configuration changes enter only after a refresh, which replaces the old baseline and original settings as one unit. If the warning no longer reproduces, report that outcome instead of showing the old comparison.

Use independent partial configuration copies and read-only input operations. Retained frames must not be mutated by trials. Do not write to saved projects, databases, or production caches.

### Trial controls and execution

Initialize trial controls from the original settings. Keep the existing key selectors, add an Inner/Left segmented control, and expose only `allow_null_keys` and `null_keys_equal`. Preserve the distinction between an omitted setting and an explicit value; show the effective null behavior resolved by production code. All other constraints remain unchanged.

Use the production linker, key coercion, null handling, and constraint checks. A completed trial returns metrics and findings. A blocked or oversized trial shows its failure or incomplete status without presenting complete metrics. Do not bypass constraints to manufacture results or interpret fewer warnings as proof of better matching.

Begin with explicit Run trial. Editing any setting invalidates the displayed trial until it is rerun; baseline results remain visible, or are reported as explicitly incomplete when none were retained. Associate responses with the submitted settings and snapshot so an older response cannot overwrite a newer trial, a refreshed baseline, or a reset. Automatic trial updates are deferred unless measured execution time supports them; they are not required for acceptance.

### Comparison, exceptions, and transport

Compare input A rows, output rows, unmatched A rows, multiply matched A rows, and link-specific findings. Complete totals always describe the full inputs of the current snapshot, never a displayed subset.

Return two bounded exception groups: unmatched A rows and multiply matched A rows, each with stable input positions, key values, remote match counts, and output-row contributions. For an expected one-to-one relationship these are the rows needing attention. Multiple matches are shown when permitted but are not labeled violations. Unmatched rows remain visible for inner joins even though they are absent from the joined output. Correct rows are not listed.

Send complete totals and both bounded groups in one response, and page them in the browser. Paging, group switching, and page-size changes send no request. Show each group's complete count and returned count with explicit truncation, and use deterministic input order. Keep only the baseline and current trial, not a history.

Row caps alone do not bound the payload, because key values and findings vary in length. Also bound returned detail with a per-value and aggregate budget, mark shortened or omitted detail as truncated, and keep complete counts and totals exact. The budget must not depend on how many rows happen to be returned.

### Request contract

Opening the dialog creates the context and returns its identifier, the baseline diagnostic status, the available key options, and any baseline totals and groups the context retained. A trial submits that identifier with the trial settings and returns trial totals, groups, and findings. An expired identifier does not run the submitted trial: the client opens a fresh context using the original warning request and shows the new baseline, or reports why reproduction failed. Closing releases the context.

Neither request carries `page`, `page_size`, or `row_filter`. This is a breaking contract change and must be documented in the release notes and for existing stateless callers.

### Reset

Reset to baseline restores the original keys, join type, constraint settings, findings, and the most recently received baseline, including an explicitly incomplete baseline with no totals or groups. It clears trial errors and returns the view to its initial diagnostic selection. Reset does not recompute the baseline or extend the snapshot lifetime; the next server operation refreshes it if expired. Reset must invalidate pending trial responses.

### Context lifecycle and access

The deployed service runs a single uvicorn worker because in-memory `ApplicationState` requires it. An in-process context store follows that existing constraint, so it needs no new dependency and no cross-worker routing. `docs/DESIGN.md` already records the worker requirement; extend that note to name dialog contexts as well as `ApplicationState` and the preview cache, so a later worker increase cannot silently split dialog state.

Scope contexts to the authorized user and project, and check project read access on every operation, including refresh. An identifier alone grants no access. Do not log retained row values.

Use a fixed 15-minute TTL, not extended by requests. Remove expired frames and contexts on access and through periodic cleanup so abandoned dialogs release memory. Closing requests immediate best-effort cleanup; active operations release their references when they finish.

Bound retained A/B frames and estimate the peak memory needed for copies and materialized AB before each merge, including configured-key diagnostics. Use the existing join-row limit as a separate guard. Reject an input or projected peak above the chosen MB budget with a `ProjectedBudgetExceeded` exception, reported to the user as an explicit failure without partial metrics. The numeric budget and conservative estimation rule must be set before Phase 1 task planning. A separate concurrent-admission limit is deferred; the memory estimate is per computation, not a guarantee against simultaneous requests.

On the next context-dependent operation after expiry, the client establishes a new context and baseline rather than silently replacing either. Show an input-refreshed notice, discard the previous trial, and require a new Run trial. If warning reproduction fails, show that status and do not run the trial. A lost context after a worker restart may require reopening the dialog; durable recovery is out of scope.

## Alternatives Considered

- **Stateless replay on every request:** avoids retained state but cannot guarantee fixed inputs within a comparison when source data changes.
- **Freeze only browser metrics:** keeps the baseline column stable while allowing trials to use different data; not a valid experiment.
- **Return the whole joined output and browse it in the browser:** turns the view into a data browser, hides the exceptions among correct rows, and cannot be bounded; rejected.
- **Keep server-side paging over a retained context:** avoids the contract change but costs a request per page for data the client needs in one piece; deferred.
- **Expose all constraints and full result browsing:** broadens the editor and API without helping the initial comparison; deferred.

## Risks And Tradeoffs

- Retained input frames introduce memory and sensitive-data lifetime concerns. A 15-minute TTL and input budget limit retention; periodic expiry removes data from abandoned dialogs without waiting for another request.
- Peak memory exceeds retained size. Pre-merge byte estimates include input copies and materialized results, but are approximate, especially for variable-width data; explicit rejection limits individual computations, not aggregate concurrent memory. Revisit concurrent admission if measurements show overlapping work is a problem.
- Refresh can replace the baseline when data or configuration has changed. Clearing old trials and showing an input-refreshed notice avoids comparing different snapshots without requiring an explanation of what changed.
- In-process contexts depend on the single-worker deployment. Raising the worker count without shared state would split dialog state.
- Removing server paging is a breaking contract change for existing callers. It must be documented rather than shipped silently.
- Null settings have interacting defaults. Treating omission as `false` can change behavior even before the user runs a trial.
- Bounded exception groups deliberately omit some row details. Complete counts and clear truncation preserve their meaning.
- Bounded detail can weaken the evidence it carries. A truncated key value may be exactly the value the user needs, so truncation must be stated and must not silently shorten a short value.
- Failed trials may have less diagnostic detail than successful ones because production checks can stop execution. This follow-up preserves that behavior.
- The integrity inspector rebuilds its own baseline per request and is outside this proposal. Decide separately whether it shares this context mechanism.

## Testing And Validation

Compare baseline and trial behavior with production linking on identical inputs. Cover inner/left switching, missing and multiple matches, cancelling row loss and expansion, compound keys, null-policy combinations and omitted defaults, constraint failures, and oversized joins. Change source data after context creation: trials before expiry stay on the original inputs; the next context-dependent operation after expiry reproduces the warning, replaces the baseline, and clears the old trial without comparing snapshots.

Exercise reset during an in-flight request, out-of-order responses across refresh, settings edits after a completed trial, deterministic truncation of both exception groups, expiry and abandoned-dialog cleanup, authorization changes, cross-user access attempts, and input and projected-peak budget failures. Verify trials do not mutate retained inputs, saved configuration, or production caches.

Confirm that paging, group switching, and page-size changes issue no request and trigger no replay, and that the API no longer accepts paging fields.

Open a link whose configured-key diagnostic trial fails or exceeds its row limit, and confirm the context opens with an explicitly incomplete baseline, that trials still run, and that Reset returns to that state without recomputation. Repeat after refresh; a warning that no longer reproduces must not yield a trial. Exercise the payload budget with long key values and many findings, confirming that truncation is stated and that counts and totals stay exact.

## Acceptance Criteria

- `P-AC-1` An eligible warning opens a context only after baseline reproduction succeeds. Every trial uses its current snapshot's original A/B inputs without re-normalizing; a settings change recomputes only the link. Refresh repeats warning reproduction and replaces A, B, original settings, and baseline together.
- `P-AC-2` Users can change ordered key pairs, inner/left join type, and the two supported null-key constraints. Omitted values retain production default resolution; other FK settings remain unchanged.
- `P-AC-3` Baseline and current-trial totals and findings follow production behavior on the same snapshot inputs. Invalid, blocked, or oversized trials are explicit and never present incomplete calculations as complete metrics.
- `P-AC-4` The response carries complete unmatched and multiply matched counts with separate bounded, deterministic A-row groups and explicit truncation. Inner-join losses remain inspectable, correct rows are not listed, returned subsets do not change totals or rerun the join, and returned key values and findings are bounded by a stated budget and marked as truncated when shortened.
- `P-AC-5` Editing settings invalidates the displayed trial until Run trial completes. Late responses cannot replace a result for newer settings or undo Reset or a refresh.
- `P-AC-6` Reset restores original settings and the most recently received complete or explicitly incomplete baseline immediately without recomputation, clears trial errors, and restores the initial diagnostic selection. It does not extend the snapshot TTL.
- `P-AC-7` Context access requires current project read authorization and user/project ownership. After a fixed 15-minute TTL, the next context-dependent operation refreshes through warning reproduction, explicitly notifies the user, and clears the previous trial without running it against the new baseline. Abandoned contexts are removed periodically. Retained inputs and projected peak memory for copies and materialized AB have explicit MB limits; excess work reports `ProjectedBudgetExceeded` without complete metrics. Concurrent-computation admission is deferred.
- `P-AC-8` Closing discards client trial state and requests context cleanup. Expiry removes abandoned contexts, and active operations release their references when done. Trials and reset do not mutate retained baseline inputs, saved projects, databases, or production caches.
- `P-AC-9` Paging, group switching, and page-size changes are handled in the browser and send no request. The request contract carries no paging fields, and the change is documented for existing callers.
- `P-AC-10` A context opens or refreshes whenever warning reproduction succeeds, even when the configured-key diagnostic trial is failed, incomplete, or not run. Such a baseline is reported as explicitly incomplete with no totals or groups, trials remain available, and Reset restores that state until the next refresh.

## Planning Handoff

- Confirmed: separate follow-up; fixed-input server-side snapshots for 15 minutes each; one current baseline and one current trial; null-key controls only; explicit Run trial; exception-focused rows; no saves or new constraint semantics.
- Confirmed: A/B retention and per-trial re-linking already exist within one request. The phases add context lifetime, transport, and access, not a new computation path.
- Resolved: storage is in-process, matching the single-worker deployment that in-memory `ApplicationState` already requires.
- Resolved: paging is client-side over bounded groups. `page`, `page_size`, and `row_filter` leave the request contract, and the breaking change must be documented.
- Resolved: an incomplete configured-key diagnostic does not block context creation. The context reports the baseline status, and Reset restores whatever baseline was retained.
- Resolved: expiry removes the old context; the next context-dependent operation automatically opens a fresh one through warning reproduction, replaces the baseline, clears old trial results, and announces the refresh without explaining any data differences. It does not run the expired request's trial.
- Resolved: estimate retained inputs and projected peak memory, including materialized AB, before admission; report `ProjectedBudgetExceeded` when over budget. Defer a separate concurrent-admission limit.
- Resolved: `docs/DESIGN.md` already records the single-worker requirement; extend that note to name dialog contexts as well as `ApplicationState` and the preview cache.
- Preserve saved-FK identity, supported-warning eligibility, baseline reproduction, production merge/null behavior, read authorization, computation limits, and bounded responses.
- Before the context-lifecycle phase is ready for task planning, set the MB budget and conservative peak-estimation rule; keep expiry at 15 minutes and use periodic cleanup plus best-effort Close. Do not add a persistence dependency.
- Before the controls/diagnostics phase is ready for task planning, decide the display cap per exception group, the key-value and findings payload budget, and the representation of inherited versus explicit null settings. Validate that the selected controls reproduce production default resolution.
- Update `docs/USER_GUIDE.md`: the dialog reads data on opening and after expiry on the next context-dependent operation, not on page or group changes. The current text says the dialog re-reads on every page change.
- Validation must establish fixed-input parity within snapshots, refresh and trial invalidation, immediate reset, stale-response rejection, client-side paging without a server request, bounded exception groups and payload detail, incomplete-baseline opening, lifecycle/access limits, projected-budget rejection, and absence of mutation.

## Final Recommendation

Extend the troubleshooter through this approved follow-up rather than changing the first edition's acceptance criteria. Keep experiments focused: one fixed snapshot at a time, refreshed after expiry; limited settings, baseline comparison, exception rows only, and immediate reset.