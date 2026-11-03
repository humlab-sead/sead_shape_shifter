# Foreign-Key Link Troubleshooter

## Status

- Approved feature
- Scope: first edition of a read-only troubleshooter for one configured foreign-key link
- Goal: identify which rows and keys cause a linking warning, and test alternative join keys without changing the project
- Delivery: [Phase plan](FOREIGN_KEY_LINK_TROUBLESHOOTER_PHASE_PLAN.md)

## Summary

Add a troubleshooting action to linking warnings such as `ROW_COUNT_MISMATCH`. It opens the affected A → B link with the configured join as a baseline. Users can try different key pairs and inspect the resulting rows, match failures, and link-specific validation results. Closing the view discards the trial.

## Problem

A warning such as `relative_dating -> relative_ages[linking]: before=114, after=75` reports a net change but does not identify the affected rows. Missing remote matches can remove rows in an inner join, while duplicate remote matches can add rows; both can occur in the same join. Counts alone cannot tell a user whether the keys, source data, or remote data need attention.

## Scope

- Open from a warning that identifies one saved foreign key.
- Support inner and left joins only; do not offer troubleshooting for right, outer, or cross joins in this edition.
- Show A and B as fixed entities, the configured join type and constraints, and editable trial key pairs.
- Show the baseline and trial join results, row-level diagnostics, and validation limited to the A → B link.
- Keep trial state temporary and return only bounded row details to the browser.

## Non-Goals

- Saving or promoting a trial configuration; changing A, B, the join type, or constraints.
- Diagnosing right, outer, or cross joins, which need different row-level explanations.
- Running project-wide validation, editing source data, or repairing missing remote rows.
- Replacing the existing general foreign-key editor or its quick join test.

## Current Behavior

The linker performs the configured join and collects `row_count_mismatch` issues. The issue includes the local and remote entity, counts, and join type, but no identifier for a particular FK when multiple links share those entities and no affected rows. The existing Test Join UI accepts an unsaved FK configuration, but its service uses processed entity previews and an independent left merge, so its counts and null handling need not match the linking warning.

## Proposed Design

### Open and isolate the link

Show a labeled troubleshoot action only for supported linking issues on inner or left joins. Resolve the specific saved FK, not just the entity pair; if the issue cannot identify one unambiguously, do not open a potentially wrong link. Display A and B as locked, and show the saved join type and constraints as read-only. Recompute the baseline against current project data and indicate when it no longer reproduces the original warning.

Use the *input to the selected link* for A, after earlier pipeline steps and earlier FKs but before this FK, and the same processed B data that the linker would consume. Do not join the already-linked output of A, or silently substitute raw source rows or independently sampled entity previews. Reuse the production link setup, key coercion, null-key policy, and relevant constraint checks. A disposable in-memory two-entity setup is acceptable only if it preserves those inputs and behaviors; it must not write a project or replace the production merge with an approximate join.

### Experiment and inspect

Start with the configured key pairs, including compound keys in their configured order. Users may change only the key pairs, choosing columns available at this link step. Run each trial against the same A and B inputs; show explicit errors for missing keys, incompatible inputs, or violated constraints. There is no save action.

Show baseline versus trial counts for input A rows, output rows, unmatched A rows, and A rows with multiple B matches. Provide a paged result table with A row identity (or a temporary input-row position), join-key values, matched/unmatched status, and remote match count; let users focus on unmatched and multiply matched rows. Include the relevant link-specific validation findings. Use a diagnostic join when needed to find rows that an inner join removed; do not infer unmatched count by subtracting output rows from input rows. Determine match status and remote match count using the resolved production null policy: a left-join row retained without a B match is unmatched, while a null-key match permitted by `null_keys_equal` is a match.

Compute counts on complete link inputs when feasible; limiting displayed rows must never silently change the stated totals. Bound expensive joins and returned row data, and report explicitly when a complete comparison cannot be produced. Failed trials must not appear successful.

## Alternatives Considered

- **Add sample rows to warning text:** faster to build, but cannot test another key or reliably account for duplicate matches.
- **Reuse Test Join unchanged:** it is useful for a quick check, but its separate merge and processed previews cannot establish parity with the link that raised this warning.
- **Copy A and B into a disposable project:** possible fallback, but adds setup and can change the link input stage. Prefer direct, isolated reuse of the real linker.

## Risks And Tradeoffs

- Obtaining the exact pre-link A input and B data may require changes to the execution/preview path. A post-link or stale cached preview would give misleading results.
- Joins can expand dramatically when keys are not unique; bound resource use without reporting sample statistics as complete results.
- Row values may be sensitive. Apply the project's read authorization, avoid persistent diagnostic copies, and limit data returned to the user.

## Testing And Validation

Compare baseline counts and link-specific findings with a real linking run using the same inputs. Exercise inner and left joins, `null_keys_equal` enabled and disabled (including partially null compound keys), missing matches, duplicate remote keys, multiple FKs between the same entities, invalid key selections, stale warnings, and join-size limits. Include an inner join where lost A rows and duplicate B matches cancel out in the total; verify both remain visible despite equal input and output row counts. Verify right, outer, and cross joins offer no troubleshoot action. Verify trials do not mutate saved configuration or cached production data, and that displayed rows and totals describe the same input set.

## Acceptance Criteria

- `P-AC-1` A supported linking warning for an inner or left join opens the correct saved FK with A and B locked; ambiguous warnings and right, outer, or cross joins offer no troubleshoot action.
- `P-AC-2` The baseline reproduces the selected link's counts and validation findings on the same inputs, or explicitly reports why it cannot.
- `P-AC-3` Users can try valid alternative key pairs and compare their join results and link-only validation without changing the join type, constraints, or saved project.
- `P-AC-4` For inner and left joins, the result identifies unmatched and multiply matched A rows, their keys, remote match counts under the resolved null policy, and their contribution to the row count; pagination does not alter complete totals.
- `P-AC-5` Invalid or oversized trials return clear failures or incomplete-result notices, and closing the view discards the trial.

## Planning Handoff

- Preserve the production FK merge semantics and use pre-link A and processed B from the same run; do not build diagnostics from post-link previews.
- Limit the action and A-row diagnostics to inner and left joins; right, outer, and cross joins are deferred. Keep A/B, join type, and constraints fixed, with no writes or promotion in this edition. Apply project read authorization and cap response size.
- Use the resolved production null policy for match status and counts, including partially null compound keys. Validate count parity with actual execution, visibility of cancelling loss and expansion, and the absence of project/cache mutations.
- A warning identifies its saved FK by the FK's index in the entity's `foreign_keys` list, checked against a signature of the entity pair, key pairs, join type, deferral, and resolved constraints. The full contract is in [Phase 1 of the phase plan](FOREIGN_KEY_LINK_TROUBLESHOOTER_PHASE_PLAN.md).
- Obtain the selected link's A and B inputs by replaying the production pipeline on a temporary entity config, and report when the warning no longer reproduces. See [Phase 2 of the phase plan](FOREIGN_KEY_LINK_TROUBLESHOOTER_PHASE_PLAN.md#phase-2-reproduce-the-selected-link).

## Final Recommendation

Build the read-only, key-pair-only troubleshooter as an extension of the real linking path. Defer broader editing until users can trust that its baseline matches the warning they opened.
