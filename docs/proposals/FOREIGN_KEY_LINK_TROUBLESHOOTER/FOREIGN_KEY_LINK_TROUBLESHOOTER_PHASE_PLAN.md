# Foreign-Key Link Troubleshooter — Phase Plan

Source: [Foreign-Key Link Troubleshooter](FOREIGN_KEY_LINK_TROUBLESHOOTER.md). This plan sequences the approved proposal's first, read-only edition.

## Summary

Deliver the troubleshooter in four phases: identify the saved link behind a warning, reproduce that link with production inputs and merge behavior, calculate trial results and A-row diagnostics, then expose the bounded comparison in the interface. Each phase produces a result that the next phase can validate against.

## Problem

A linking warning reports the change in row count but cannot show which A rows failed to match or matched several B rows. The existing Test Join uses sampled processed previews and a separate left merge, so its results cannot explain a warning from the production link.

## Scope

This plan covers warnings for one saved inner or left FK, the exact input to that link, read-only trials that change key pairs only, link-specific validation, complete totals where feasible, bounded row details, and the user view. It includes explicit handling for ambiguous warnings, stale baselines, invalid trials, and results too large to compute completely.

It excludes right, outer, and cross joins; changing entities, join type, or constraints; saving trials; project-wide validation; and changes to the existing general FK editor or quick Test Join.

## Current Position

- The proposal is approved. The FK-identity decision is recorded in Phase 1, and the link-input decision is recorded in Phase 2: a temporary entity config replays the production pipeline instead of retaining frames from a normal run.
- Phase 1's FK identity resolution, Phase 2's baseline replay, and Phase 3's trial diagnostics are implemented and committed; their outputs are available to Phase 4.
- The linker applies FKs in sequence, updates A after each link, and can retry deferred links. Its row-count warning includes A, B, before and after counts, and join type, but no FK identifier or affected rows.
- Issue metadata already reaches the API and the browser unchanged, so identifying the FK is a change at the link site, not a new transport path.
- The existing Test Join reads limited processed entity previews and performs its own left merge. The current preview route already uses project read authorization; the troubleshooter must apply the same rule.

## Phase Plan

### Phase 1: Identify an eligible saved link

**Goal**

Make each offered troubleshooting action refer to one supported saved FK.

**Focus**

- Record the saved FK's index and signature in issue metadata, including for repeated links between the same A and B and links retried later in the run.
- Resolve an issue to one saved FK from that metadata, and suppress the action when resolution fails or the join is unsupported.

**Depends On**

- Nothing. The FK-identity decision is recorded in the Task-Plan Handoff below.

**Outputs**

- A warning-to-saved-FK contract and an eligibility result for the later entry point.

**Acceptance Criteria**

- `PH1-AC-1` (from `P-AC-1`) A supported inner or left linking warning resolves to exactly one saved FK, including when several FKs share the same entity pair.
- `PH1-AC-2` (from `P-AC-1`) A warning with no usable FK identity offers no troubleshoot action. That covers missing metadata, an index outside the entity's saved FK list, and a signature that no longer matches the saved FK at that index, as well as right and outer joins. Configuration drift is decided here; a resolved link that no longer reproduces its warning is Phase 2's state.

**Validation Milestones**

- `VM-1` Warning-resolution checks cover repeated entity pairs, deferred retries, missing or inconsistent metadata, a signature mismatch after a configuration edit, and right and outer joins (`PH1-AC-1`, `PH1-AC-2`).

**Task-Plan Handoff**

- Source: `P-AC-1`. Fixed: the action targets a saved FK and must not guess from A and B alone.
- Decision: an issue identifies its FK by `fk_index`, the FK's position in the owning entity's saved `foreign_keys` list, stored in issue metadata. The entry is defined once in the project file, so the index is unique even for two identical A to B entries.
- Decision: metadata also carries a signature of `remote_entity`, `local_keys`, `remote_keys`, `how`, `defer_dependency`, and the resolved constraints block in full, rather than a hand-picked subset. Two entries can agree on entities, keys, and join type while merging differently under null-key, match, cardinality, or row-decrease rules, so a partial signature would pass while pointing at a link that behaves differently.
- Decision: resolution fails only when metadata is missing, `fk_index` is out of range, or the signature does not match the saved FK at that index. Two saved FKs with identical signatures are interchangeable for count diagnostics, so matching more than one resolves rather than rejects.
- Constraint: set the index where `TableConfig.foreign_keys` builds each `ForeignKeyConfig`, not in `link_foreign_key`, so the linker signature and its test doubles stay unchanged. No API DTO change is needed; issue metadata already reaches the browser unchanged.
- Constraint: record which linking pass raised the issue. An entity name in `DeferredLinkingTracker.deferred` alone does not show that this specific link ran in a deferred retry.
- Constraint: `row_count_mismatch` is raised only for FKs with constraints, and cross joins are already excluded, so eligibility has to reject only right and outer joins. `column_count_mismatch` is out of scope.

**Readiness**

Ready for a task plan.

### Phase 2: Reproduce the selected link

**Goal**

Produce a trustworthy baseline for the selected FK before accepting trial keys.

**Focus**

- Obtain A immediately before this FK and the processed B consumed by the linker, including earlier and deferred links, using the temporary-config replay recorded below.
- Reuse production merge setup, key handling, resolved null policy, and relevant constraint checks; distinguish a stale warning from a reproduced one.

**Depends On**

- Phase 1's unambiguous saved-FK contract. The exact link-stage input decision is recorded in this phase's Task-Plan Handoff.

**Outputs**

- A read-only baseline result with production counts, link-specific findings, and an explicit reproduction status.

**Acceptance Criteria**

- `PH2-AC-1` (from `P-AC-2`) On the same link inputs, baseline counts and link-specific findings agree with the production run for inner and left joins.
- `PH2-AC-2` (from `P-AC-2`) If current data or execution cannot reproduce the selected warning, the baseline states why and does not present the old warning as a current result.
- `PH2-AC-3` (from `P-AC-3`) Baseline computation does not change the saved project or cached production data.

**Validation Milestones**

- `VM-2` Compare baseline counts and findings with a production link on the same inputs, including an earlier FK and a deferred link (`PH2-AC-1`).
- `VM-3` A changed-input or unavailable-input case reports a non-reproduced baseline; read-only checks confirm no project or cache mutation (`PH2-AC-2`, `PH2-AC-3`).

**Task-Plan Handoff**

- Source: `P-AC-2`, `P-AC-3`, and the Planning Handoff. Fixed: pre-link A and processed B, production link behavior, no writes.
- Decision: build pre-link A by running the production pipeline on a temporary entity config, not by capturing or retaining frames during a normal run. Production code is unchanged, so this choice can be replaced later without touching the linker or normalizer.
- Decision: the temporary config keeps the saved entity as-is except for the changes below, which reproduce the state at the link that raised the warning.

| Setting | Target `initial` | Target `after_unnest` | Target `deferred_retry` |
| --- | --- | --- | --- |
| `foreign_keys` | entries `0` to `fk_index` | entries `0` to `fk_index` | entries `0` to `fk_index` |
| `unnest` | removed | kept | kept |
| `filters` at stage `after_link` | removed | kept | kept |
| `filters` at stage `after_unnest` | removed | removed | kept |
| `drop_duplicates` | removed when it depends on unnest columns | removed when it depends on unnest columns | kept |
| `drop_empty_rows` | removed | kept | kept |
| `keys` | set to empty | set to empty | set to empty |

- Constraint: `TableConfig.is_drop_duplicate_dependent_on_unnesting()` couples `drop_duplicates` to `unnest`, so evaluate it on the saved config before changing `unnest`. Clear `keys` because `_check_duplicate_keys` runs after the first link and raises when a key column comes from a removed link. Build the config through `ProjectMapper` so directives and environment values resolve as in the saved project.
- Decision: compare baseline counts, link-specific findings, and the recorded `link_pass` against the production link, not column-by-column frames. The truncated run still adds `system_id` and `public_id` after the link stage, so baseline A matches the production link's rows but may carry extra columns.
- Constraint: a contract test must fail when `_process_entity` gains a stage after its last linking call that the temporary-config projection does not handle, so a later pipeline change cannot silently shift the baseline.
- Decision: when the replay does not raise the same `row_count_mismatch` with the same before and after counts, the baseline reports a non-reproduced status and reason instead of the stored warning.
- Follow-up: a general capture mechanism for intermediate entity snapshots is tracked outside this proposal in issue #641.

**Readiness**

Ready for a task plan.

### Phase 3: Calculate trials and A-row diagnostics

**Goal**

Compare alternative key pairs on the baseline inputs and explain row loss and expansion.

**Focus**

- Accept only available A/B key pairs, preserving compound-key order while keeping entities, join type, and constraints fixed.
- Count unmatched A rows and A rows with multiple B matches under the production null policy, including partially null compound keys and inner-join rows removed from output.
- Enforce a configurable output-row limit using preflight estimates for the production join and diagnostic left join; report an explicit incomplete result above the limit.

**Depends On**

- Phase 2's link inputs and baseline behavior; the approved output-row limit and incomplete-result contract.

**Outputs**

- Read-only trial results with link-only findings, complete totals when feasible, A-row match details, and explicit failure or incomplete status.

**Acceptance Criteria**

- `PH3-AC-1` (from `P-AC-3`) Valid alternative key pairs run on the baseline A and B inputs and return link-only results without changing fixed FK settings or saved data.
- `PH3-AC-2` (from `P-AC-4`) For inner and left joins, each reported A row has an identity or temporary input position, key values, match status, remote match count under the resolved null policy, and its effect on output rows. Complete totals separately count input A rows, output rows, unmatched A rows, and multiply matched A rows, even when row loss and expansion cancel.
- `PH3-AC-3` (from `P-AC-5`) Missing or incompatible keys and violated constraints fail clearly; work beyond the computation limit does not appear as a successful complete comparison.

**Validation Milestones**

- `VM-4` Compare valid trials and link-only findings with the production merge behavior for both join types and both null policies (`PH3-AC-1`, `PH3-AC-2`).
- `VM-5` Check cancelling loss and expansion, invalid keys, constraint failures, and oversized joins; confirm no trial changes saved or cached data (`PH3-AC-1`–`PH3-AC-3`).

**Task-Plan Handoff**

- Source: `P-AC-3`–`P-AC-5`. Fixed: key-pair-only trials, production null semantics, complete totals only when computed, and no writes.
- Budget decision: estimate complete production and diagnostic output row counts from key frequencies using production key coercion and null behavior. Check both estimates before materializing either merge. Use the backend setting `LINK_TRIAL_MAX_OUTPUT_ROWS`, default `1,000,000`, exposed as `SHAPE_SHIFTER_LINK_TRIAL_MAX_OUTPUT_ROWS`; allow exactly the limit and return `incomplete` with a reason and no totals or row details above it.

**Readiness**

Ready for a task plan.

### Phase 4: Present the bounded comparison

**Goal**

Let a user open a supported warning, inspect baseline and trial results, and discard the trial on close.

**Focus**

- Open the resolved FK with A/B locked, saved join type and constraints visible, and configured key pairs as the initial trial.
- Show baseline versus trial totals, link-specific findings, paged A-row details, and unmatched or multiply matched row filters.
- Apply project read authorization, limit returned row data, and show stale, invalid, and incomplete states explicitly.

**Depends On**

- Phase 1's eligibility result, Phase 2's baseline, and Phase 3's trial and diagnostic results.

**Outputs**

- A read-only troubleshooting view connected to supported linking warnings.

**Acceptance Criteria**

- `PH4-AC-1` (from `P-AC-1`) The action opens the identified supported FK with fixed A/B, join type, and constraints; ineligible warnings offer no action.
- `PH4-AC-2` (from `P-AC-3`, `P-AC-4`) Users can change trial keys, compare baseline and trial results, and page or filter A-row details without changing complete totals.
- `PH4-AC-3` (from `P-AC-5`) The view displays failures and incomplete results, returns bounded row data only to an authorized reader, and discards trial state on close.

**Validation Milestones**

- `VM-6` User-flow checks cover opening the correct FK, locked settings, comparison, filters, paging, and unchanged totals (`PH4-AC-1`, `PH4-AC-2`).
- `VM-7` Access, response-size, stale-warning, failure, incomplete-result, and close/reopen checks confirm the stated behavior (`PH4-AC-3`).

**Task-Plan Handoff**

- Source: `P-AC-1`, `P-AC-3`–`P-AC-5`. Fixed: read-only access, bounded details, no save action, and no action for unsupported joins. The Phase 1–3 result and status contracts are implemented; the Phase 4 task plan fixes stateless requests, the 500-row response cap, and client-side eligibility backed by server eligibility. No blocking phase-level decision remains.

**Readiness**

Ready for a task plan.

## Cross-Phase Rules

- Keep the production linker authoritative for merge and null behavior; the existing Test Join is not a parity reference.
- Use the same link inputs for baseline and trials. A display page or filter must not change totals.
- Derive the link-stage inputs by replaying the pipeline on a temporary config; do not retain or persist frames from a normal run.
- Keep trial data temporary and scoped to an authorized project read. Never write a trial into the project or production cache.
- Treat ambiguous links, unsupported joins, stale baselines, invalid keys, and incomplete computations as explicit states rather than successful results.

## Validation Strategy

Validate warning identity first (`VM-1`), then compare baseline counts and findings with a real link on the same inputs (`VM-2`, `VM-3`). Validate trial semantics and limits before exposing them in the interface (`VM-4`, `VM-5`). Finish with user-flow, authorization, bounded-response, and discard checks (`VM-6`, `VM-7`). Each phase task plan selects the exact tests and data cases for these milestones.
