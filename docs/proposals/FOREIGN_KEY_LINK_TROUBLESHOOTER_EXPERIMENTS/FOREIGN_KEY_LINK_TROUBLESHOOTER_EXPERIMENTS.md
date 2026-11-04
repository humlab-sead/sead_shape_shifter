# Foreign-Key Link Troubleshooter Experiments

## Status

- Proposed follow-up change request; not implemented
- Scope: fixed-input experiments with trial keys, inner/left joins, limited constraints, and reset
- Goal: let users understand how link settings affect rows and validation without changing the saved project
- Extends: [Foreign-Key Link Troubleshooter](../FOREIGN_KEY_LINK_TROUBLESHOOTER/FOREIGN_KEY_LINK_TROUBLESHOOTER.md). Its original acceptance criteria remain unchanged.

## Summary

Keep one immutable baseline and one current trial in a temporary server-side context. Run both against the same A and B inputs. Allow changes to key pairs, join type, and null-key constraints, then compare complete totals and findings and show a bounded list of problematic A rows. Reset restores the retained baseline immediately.

## Problem

The current troubleshooter only permits key-pair changes. Users cannot explore why a left join retains unmatched rows or how null-key settings affect matches. Rebuilding the baseline for each request also allows source changes to affect the comparison. A useful experiment must attribute differences to trial settings, not to different input data.

## Scope

- Preserve the existing supported-warning entry point, saved-FK identification, and baseline reproduction checks.
- Hold A/B inputs and original resolved configuration fixed for the lifetime of an experiment.
- Edit trial key pairs, choose inner or left join, and control `allow_null_keys` and `null_keys_equal` only.
- Compare baseline and current-trial totals and link-specific findings; inspect unmatched and multiply matched A rows.
- Restore original settings and results with Reset to baseline.
- Keep all operations read-only and all experiment data temporary.

## Non-Goals

- Revising the original proposal or its acceptance criteria.
- Changing A/B entities, earlier links, pipeline stages, or source data.
- Right, outer, or cross joins; broader constraint editing; new validation semantics.
- Saving or promoting trial settings, persistent experiments, trial history, or export.
- General-purpose result paging, cell-by-cell output comparison, or downstream pipeline validation.

## Current Behavior

The [coordinating service](../../../backend/app/services/link_troubleshooter_service.py) rebuilds the baseline for every request, including row filtering and paging. The [trial service](../../../backend/app/services/link_trial_service.py) copies the original FK configuration, changes only the keys, and uses copies of the input frames with the production linker. A raised constraint violation returns a failed trial without complete metrics.

The [client composable](../../../frontend/src/composables/useLinkTroubleshooter.ts) clears the result on each request. Its existing `reset()` clears the whole dialog context; it is not a user-facing restoration of baseline settings and results.

## Proposed Design

### Fixed inputs and baseline

After reproducing the selected warning, create a temporary server-side context addressed by an opaque identifier. Retain the pre-link A input, processed B input, the resolved configuration needed to execute the selected link, original FK settings, baseline totals and findings, and bounded baseline row diagnostics. Do not retain full joined outputs solely for display.

The comparison is always between the original link and the current trial:

$$
AB_{\mathrm{baseline}} = \operatorname{link}(A, B; K_0, J_0, C_0)
$$

$$
AB_{\mathrm{trial}} = \operatorname{link}(A, B; K_t, J_t, C_t)
$$

Here K denotes ordered key pairs, J the join type, and C the constraints. A and B are unchanged. A trial never becomes the next baseline, and later source or configuration changes do not enter an existing experiment. Reopening establishes a new baseline through the existing reproduction checks.

Use independent partial configuration copies and read-only input operations. Retained frames must not be mutated by trials. Do not write to saved projects, databases, or production caches.

### Trial controls and execution

Initialize trial controls from the original settings. Keep the existing key selectors, add an Inner/Left segmented control, and expose only `allow_null_keys` and `null_keys_equal`. Preserve the distinction between an omitted setting and an explicit value; show the effective null behavior resolved by production code. All other constraints remain unchanged.

Use the production linker, key coercion, null handling, and constraint checks. A completed trial returns metrics and findings. A blocked or oversized trial shows its failure or incomplete status without presenting complete metrics. Do not bypass constraints to manufacture results or interpret fewer warnings as proof of better matching.

Begin with explicit Run trial. Editing any setting invalidates the displayed trial until it is rerun; baseline results remain visible. Associate responses with the submitted settings so an older response cannot overwrite a newer trial or a reset. Automatic updates are deferred unless measured execution time supports them; they are not required for acceptance.

### Comparison, exceptions, and reset

Compare input A rows, output rows, unmatched A rows, multiply matched A rows, and link-specific findings. Complete totals always describe the full fixed inputs, never the displayed subset.

Replace general-purpose paging with separate bounded groups for unmatched and multiply matched A rows, using stable input positions, key values, remote match counts, and output-row contributions. For an expected one-to-one relationship, these are the rows needing attention. Multiple matches are still shown when permitted, but are not automatically labeled violations. Unmatched rows remain visible for inner joins even though they are absent from the joined output.

Show each group's complete count and displayed count, with explicit truncation when needed. Use deterministic input order. Changing the displayed group must not rerun the pipeline or join. Keep only the baseline and current trial, not a history.

Reset to baseline restores the original keys, join type, constraint settings, metrics, findings, and bounded row diagnostics. It clears trial errors and returns the view to its initial diagnostic selection. Reset does not recompute the baseline and must invalidate pending trial responses.

### Context lifecycle and access

Scope contexts to the authorized user and project, and check project read access on every operation. An identifier alone grants no access. Apply bounded lifetime, per-context and aggregate resource limits, and best-effort cleanup on close; expiry must handle abandoned dialogs. Do not log retained row values.

An expired, evicted, or unavailable context requires reopening. Never silently replay data or replace the baseline. Worker restarts may end experiments; durable recovery is out of scope. Storage and routing must support the deployed worker arrangement or fail explicitly rather than mixing contexts.

## Alternatives Considered

- **Stateless replay on every request:** avoids retained state but cannot guarantee fixed inputs when source data changes.
- **Freeze only browser metrics:** keeps the baseline column stable while allowing trials to use different data; not a valid experiment.
- **Expose all constraints and full result browsing:** broadens the editor and API without helping the initial comparison; deferred.

## Risks And Tradeoffs

- Retained input frames introduce memory, sensitive-data lifetime, and worker-routing concerns. Expiry and admission limits are required, not optional cleanup.
- Null settings have interacting defaults. Treating omission as `false` can change behavior even before the user runs a trial.
- Bounded exception groups deliberately omit some row details. Complete counts and clear truncation preserve their meaning.
- Failed trials may have less diagnostic detail than successful ones because production checks can stop execution. This follow-up preserves that behavior.

## Testing And Validation

Compare baseline and trial behavior with production linking on identical inputs. Cover inner/left switching, missing and multiple matches, cancelling row loss and expansion, compound keys, null-policy combinations and omitted defaults, constraint failures, and oversized joins. Change source data after context creation and confirm existing experiments remain fixed while reopening performs fresh reproduction checks.

Exercise reset during an in-flight request, out-of-order responses, settings edits after a completed trial, deterministic truncation of both exception groups, expiry, authorization changes, cross-user access attempts, and context limits. Verify trials do not mutate retained inputs, saved configuration, or production caches.

## Acceptance Criteria

- `P-AC-1` An eligible warning creates a context only after baseline reproduction succeeds. Every trial uses its original A/B inputs and baseline settings, metrics, and findings without replaying the pipeline.
- `P-AC-2` Users can change ordered key pairs, inner/left join type, and the two supported null-key constraints. Omitted values retain production default resolution; other FK settings remain unchanged.
- `P-AC-3` Baseline and current-trial totals and findings follow production behavior on the fixed inputs. Invalid, blocked, or oversized trials are explicit and never present incomplete calculations as complete metrics.
- `P-AC-4` The view shows complete unmatched and multiply matched counts with separate bounded, deterministic row groups and explicit truncation. Inner-join losses remain inspectable; displayed subsets do not change totals or rerun the join.
- `P-AC-5` Editing settings invalidates the displayed trial until Run trial completes. Late responses cannot replace a result for newer settings or undo Reset to baseline.
- `P-AC-6` Reset restores original settings and baseline results immediately without recomputation, clears trial errors, and restores the initial diagnostic selection.
- `P-AC-7` Context access requires current project read authorization and user/project ownership. Contexts have bounded lifetime and resource use; expiry or loss requires reopening without silent baseline replacement.
- `P-AC-8` Closing discards client trial state and requests context cleanup. Trials and reset do not mutate retained baseline inputs, saved projects, databases, or production caches.

## Planning Handoff

- Confirmed: separate follow-up; fixed-input server-side context; one baseline and one current trial; null-key controls only; explicit Run trial; exception-focused rows; no saves or new constraint semantics.
- Preserve saved-FK identity, supported-warning eligibility, baseline reproduction, production merge/null behavior, read authorization, computation limits, and bounded responses.
- Before the context-lifecycle phase is ready for task planning, decide storage/routing for deployed workers, expiry, memory accounting, admission limits, and cleanup behavior. Do not add a persistence dependency without evaluating a simpler option.
- Before the controls/diagnostics phase is ready for task planning, decide the display cap per exception group and the representation of inherited versus explicit null settings. Validate that the selected controls reproduce production default resolution.
- Resolve compatibility for existing stateless callers and paged responses before planning the API transition; this proposal does not authorize an undocumented breaking change.
- Validation must establish fixed-input parity, immediate reset, stale-response rejection, bounded exception groups, lifecycle/access limits, and absence of mutation. No phase or task plan is created by this proposal.

## Final Recommendation

Extend the troubleshooter through this follow-up rather than changing the first edition's acceptance criteria. Keep experiments focused: fixed inputs, limited settings, baseline comparison, problematic rows, and immediate reset.