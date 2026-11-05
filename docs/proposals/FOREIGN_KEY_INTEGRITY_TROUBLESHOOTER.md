# Foreign-Key Integrity Troubleshooter

## Status

- Proposed follow-up change request; not implemented
- Scope: `FK_DATA_INTEGRITY` warnings for one saved foreign key, read-only inspection of the local values that have no match in the remote entity
- Goal: let users see the values and local rows behind a "not found in" count, and know which saved link produced it
- Extends: [Foreign-Key Link Troubleshooter](done/FOREIGN_KEY_LINK_TROUBLESHOOTER/FOREIGN_KEY_LINK_TROUBLESHOOTER.md), which is approved and implemented for row-count warnings
- Separate from: [Foreign-Key Link Troubleshooter Experiments](FOREIGN_KEY_LINK_TROUBLESHOOTER_EXPERIMENTS/FOREIGN_KEY_LINK_TROUBLESHOOTER_EXPERIMENTS.md), which decides how trial settings are compared against a fixed baseline

## Summary

An `FK_DATA_INTEGRITY` warning reports that N local foreign-key values have no match in the remote entity, but names neither the saved link nor the rows that carry those values. Add the same "Troubleshoot link" action to this warning, resolved through the saved-FK identity the troubleshooter already uses, and open a read-only view of the distinct unmatched values with the local rows that carry them.

Do not reuse the key-pair trial controls. Changing keys does not create a missing parent value.

## Problem

Verified in [`src/validators/data_validators.py`](../../src/validators/data_validators.py): `ForeignKeyIntegrityValidator` builds the issue with `code="FK_DATA_INTEGRITY"`, the fixed field `foreign_keys[].entity`, an empty metadata dict, and a message that embeds at most ten sample values with a trailing `, ...`. The count exists only as text.

Two consequences follow.

An entity can hold several foreign keys, so the warning does not say which saved link raised it. Locating the link means reading the project YAML and matching the remote entity name by hand.

The count is `347` while the sample is truncated after ten values. Users can read the first few values but cannot reach the rest, cannot see how many local rows each value covers, and cannot see the surrounding row that would tell them whether the value is wrong or the link points at the wrong remote key. In the reported case — 347 values such as `spelt/emmer`, `träkol`, `al/hassel?` against `taxa_tree_master` — the values are free-text taxa names, so the surrounding sample, site, or context is what makes the value judgeable.

The link troubleshooter already answers this question for row-count warnings, and it is offered only for `ROW_COUNT_MISMATCH`. Two gates hard-code that code: the frontend candidate check in [`frontend/src/utils/linkTroubleshooter.ts`](../../frontend/src/utils/linkTroubleshooter.ts) and `resolve_row_count_issue` in [`src/transforms/link_resolution.py`](../../src/transforms/link_resolution.py). The baseline service additionally requires recorded before and after row counts, which this warning does not have.

## Scope

- Structured identity and facts on the `FK_DATA_INTEGRITY` issue, so one saved foreign key can be resolved.
- Eligibility rules for offering the action on this warning and for refusing it.
- A read-only inspection that recomputes the warning and shows its distinct unmatched values and bounded local rows.
- One new endpoint and one shared dialog shell beside the existing troubleshooter.

## Non-Goals

- Suggesting corrections, mapping values to valid parents, or calling the reconciliation service.
- Editing source data, project configuration, or saving inspection results.
- Changing key pairs, join type, or constraints for this warning.
- Auto-fix behavior of any kind.
- Extending the same treatment to `FK_REMOTE_EMPTY`, `FK_ALL_NULL`, or type-compatibility warnings.
- Changing the reported `field` value on the existing issue. That correction is already recorded separately in [`docs/investigations/fk-data-integrity-field/findings.md`](../investigations/fk-data-integrity-field/findings.md).
- Changing the shipped row-count troubleshooter's request, response, or behavior.

## Current Behavior

- The validator compares distinct local key tuples against distinct remote key tuples, dropping nulls unless the link sets `null_keys_equal`. The reported count is the number of distinct unmatched local key combinations, not the number of local rows. For a single-column key it is the number of distinct unmatched values.
- The issue carries `category="data"`, `priority="medium"`, `auto_fixable=False`, and no metadata key that identifies the link.
- `ValidationMapper.from_core_issue` passes metadata through unchanged, so the API and the browser already carry anything the validator sets. This part needs no transport change.
- `DataValidationOrchestrator` loops the resolved entity's `foreign_keys` list and calls the validator for every entry that has an `entity` value. Joins with no `constraints` block are still checked, and the loop does not pass the list index.
- `ForeignKeyConfig` already exposes `fk_index` and `identity_signature`, and `TableConfig.foreign_keys` sets the index when it builds each entry.
- The troubleshooter request, resolver, response models, and row model are shaped for a join: `LinkTroubleshootRow` carries `matched`, `remote_match_count`, and `output_row_contribution`.

## Proposed Design

### Warning identity and facts

The integrity issue records the foreign key it came from, using the same two keys as `row_count_mismatch`: `fk_index`, the entry's position in the owning entity's saved `foreign_keys` list, and `fk_signature`, the entry's `identity_signature`. It also records `orphan_count`.

The orchestrator sets these when it calls the validator, because it already holds the core project and the loop index; the validator stays a pure function over frames and a configuration dictionary. The same metadata reaches the browser without a new transport path.

`orphan_count` in metadata is what makes reproduction checkable. The distinct values themselves stay out of metadata, because the set can be large.

### Eligibility

The action is offered for `FK_DATA_INTEGRITY` issues whose metadata holds an integer `fk_index` and a string `fk_signature`. The backend remains authoritative and resolves the saved link: the local entity must exist, the index must be in range, and the signature must match the entry at that index.

Join type is not checked, because no join is performed. Right and outer joins stay eligible.

The resolver shares the saved-FK lookup with `resolve_row_count_issue` instead of duplicating it, and returns the same named refusal reasons.

### Reproduction

An inspection result is `reproduced` only when the link resolves, both frames can be fetched, and the distinct unmatched count computed now equals the recorded `orphan_count`. Otherwise the result is `not_reproduced` with a named reason, or `ineligible` when the link cannot be resolved.

Count equality is the right test for this warning's claim, which is "N local values have no match". A recomputed count that differs means the claim changed, so the old count must not be presented as current. The values shown in the view are always recomputed, so a set that drifted while keeping its count is displayed as it is now rather than as it was.

Recomputation calls `ForeignKeyIntegrityValidator` and does not reimplement the comparison. The null-handling rule, the `null_keys_equal` branch, and the deduplication of local keys therefore cannot drift from the warning.

### Inspection result

The view answers three questions in this order:

1. Which link — local entity, remote entity, keys, and constraints, read-only.
2. Which values — every distinct unmatched value with the number of local rows that carry it, ordered deterministically, bounded, with the complete count and the returned count shown separately.
3. Which rows — for one selected value, a bounded sample of the local rows that carry it, with the columns used stated in the response.

The source used for both frames is stated in the response. Inspection reuses the authorization and project-loading path of the existing troubleshooter and writes nothing.

### API and interface

A new endpoint, `POST /api/v1/projects/{project_name}/integrity-troubleshooter`, reuses the project-scoped `project:read` rule. Its request carries the issue kind, the local entity, the issue metadata, and the selected value and page. Its response reports status, reason, message, the read-only relationship, the values page, and optionally the selected value's rows.

One response envelope per warning kind, rather than one envelope with trial fields that are always null for this kind. The frontend keeps one dialog shell and one action in the validation list, and renders a kind-specific body.

## Alternatives Considered

- **Extend the existing experiments proposal.** Rejected: a different decision. That document preserves the current supported-warning entry point, and its acceptance criteria assume a reproduced baseline with before and after row counts.
- **Reuse the key-pair trial machinery.** Rejected: no join runs for this warning, changing keys does not create a missing parent value, and `LinkTroubleshootRow` describes join output.
- **Read the values out of the message string.** Rejected: the message is prose, truncated to ten values, and not a contract.
- **One endpoint whose payload depends on the issue kind.** Deferred: fewer routes, but it forces nullable trial and integrity sections into one model and destabilises a shipped response.
- **Show values without local rows.** Rejected for the reported case: a bare taxa string does not tell the user whether the value is wrong.

## Risks And Tradeoffs

- Count-only reproduction can accept a stale value set. The displayed values are always recomputed and labelled as current, so the stale claim never appears as a count.
- The warning does not record which data source produced it. If inspection fetches through a different strategy than the validation run, counts can differ and the result reports `not_reproduced`. The response must state the source it used.
- Local row samples expose source data. Keep them bounded, authorized, and limited to declared columns.
- Large orphan sets need deterministic truncation, or the view becomes unreadable and the response unbounded.
- Two warning kinds in one dialog adds a mode branch in the frontend. Share the shell and the API client plumbing; keep the bodies separate.
- The reported `field` stays `foreign_keys[].entity`, which remains misleading after this change. Fixing it is a separate, already-recorded correction.

## Testing And Validation

Cover resolution and refusal: a single link, two links between the same entity pair resolved by index, a stale signature after a configuration edit, an index out of range, missing metadata, and a right or outer join.

Cover reproduction against a production validation run on the same inputs: a matching count, a changed count, an unreachable remote entity, and a link with `null_keys_equal` set. Confirm the inspection count matches the validator's count for the same frames.

Cover the view: complete value count with truncation, per-value local row counts, deterministic order, a selected value's bounded rows, and the stated source and columns.

Cover safety: project read authorization on every call, cross-project refusal, no writes to projects, source data, or caches, and unchanged behavior and response for the existing row-count troubleshooter.

## Acceptance Criteria

- `P-AC-1` An `FK_DATA_INTEGRITY` warning identifies exactly one saved foreign key by index and signature, including when several links share the same entity pair. An unresolvable or unsupported warning offers no action and explains why.
- `P-AC-2` The inspection reports `reproduced` only when the recomputed distinct unmatched count equals the count recorded on the warning. A different count yields `not_reproduced` with a reason and never presents the old count as current.
- `P-AC-3` Recomputation uses `ForeignKeyIntegrityValidator`, so null handling and key deduplication match the warning producing the count.
- `P-AC-4` The view lists every distinct unmatched value with its local row count, shows the complete count separately from the returned count, and truncates deterministically.
- `P-AC-5` Selecting a value returns a bounded sample of the local rows that carry it, and the response states the data source and the columns used.
- `P-AC-6` The inspection is read-only and requires current project read authorization on every call; it does not modify projects, source data, or caches.
- `P-AC-7` The existing row-count troubleshooter's request, response, eligibility, and behavior are unchanged.

## Planning Handoff

- Confirmed: a separate follow-up proposal; a second warning kind in the same dialog; saved-FK identity by `fk_index` and `fk_signature`; count-based reproduction; recomputation through the existing validator; a separate endpoint and response envelope.
- Preserve saved-FK resolution, authorization rules, read-only behavior, bounded responses, and the shipped row-count troubleshooter.
- Before the eligibility phase is ready for task planning, decide where identity metadata is attached and confirm that every path producing `FK_DATA_INTEGRITY` goes through it.
- Before the reproduction phase is ready for task planning, decide which data source inspection uses and how the response states it. If the validation run's source cannot be re-established, `not_reproduced` is the honest result.
- Before the display phase is ready for task planning, decide the per-page cap, the context column set for local rows, and whether values and rows are one response or two. Resolve how a selected value is addressed so paging cannot shift under it.
- Validation must establish count parity with the validator, honest non-reproduction, deterministic bounded output, and no mutation. No phase or task plan is created by this proposal.

## Open Questions

- Should the same treatment extend to `FK_REMOTE_EMPTY`, which shares the validator and the same "nothing to join on" shape?
- Is a count enough for reproduction, or should the warning also record a digest of the distinct unmatched values?

## Final Recommendation

Add integrity warnings to the troubleshooter rather than building a second, separate inspection view. Reuse the saved-FK identity, the resolver, the authorization path, and the request pipeline that already exist; add the metadata, the reproduction rule, and a value-and-row view that the join-shaped trial models deliberately do not fit.
