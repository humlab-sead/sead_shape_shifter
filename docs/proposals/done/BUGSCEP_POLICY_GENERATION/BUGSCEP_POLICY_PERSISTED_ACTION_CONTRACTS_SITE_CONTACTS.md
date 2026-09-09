# Working Reference: BugsCEP Site And Contact Persisted-Action Contracts

## Summary

The current site and contact family already proves parity for several list-result behaviors. That is not enough for downstream implementation work.

This document converts the family into a clearer persisted-action contract by naming the row actions and side effects that future runtime work must preserve.

## Scope

This reference covers the update-oriented parts of the current site and contact family:

- `datasetcontacts`
- `sitelocations`
- `siteotherproxies`

It also notes the ordered-reconciliation dependencies that these updaters rely on:

- `site`
- `sitereferences`

This document is intentionally narrower than the full family inventory. It focuses on persisted actions, not every lookup detail.

## Problem

The current shared result objects prove that the right parity branches fire. They do not yet state the persisted-action contract as directly as future implementation work needs.

For these policies, the important question is not only which branch matched. The important question is what must happen to stored rows:

- keep them unchanged
- append new rows
- mark existing rows for deletion
- replace one set of rows with another
- stop before list reconciliation because a prerequisite failed

## Contract Vocabulary

Use the following action language when expanding fixtures or runtime contracts for this family.

- `keep_existing`: the stored row remains unchanged and is part of the final persisted result
- `append_new`: a generated row is inserted alongside retained existing rows
- `mark_for_deletion`: a stored row remains part of the update result but is explicitly marked for deletion
- `replace_set`: the final persisted result is expressed as one or more `mark_for_deletion` actions plus one or more `append_new` actions for the same parent identity
- `stop_before_list_update`: prerequisite failure or generated error rows prevent normal list reconciliation from starting

The current `output_result` comparisons remain useful, but future work should treat these persisted actions as the clearer execution-facing meaning.

## Family Contracts

### `datasetcontacts`

Persisted-action contract:

- resolve the dataset for the countsheet first
- parse site contact strings into generated contact items
- keep stored dataset-contact rows when a generated contact already matches by dataset, contact type, and contact name
- append only the unmatched generated dataset-contact rows
- never delete existing dataset-contact rows in this importer
- never update existing dataset-contact rows in place

Execution meaning:

`datasetcontacts` is append-only. Its contract is closer to `keep_existing` plus `append_new` than to full set replacement.

### `sitelocations`

Persisted-action contract:

- resolve the site first
- expand country and region to the generated location set
- compare the generated set with all stored site-location rows for the site
- keep matching stored rows unchanged
- mark stored rows for deletion when they are no longer present in the generated set
- append generated rows that are missing from the stored set
- treat full replacement as a composed action: `mark_for_deletion` plus `append_new`
- allow `stop_before_list_update` when prerequisite resolution or location expansion returns error carriers instead of a normal generated set

Execution meaning:

`sitelocations` is a full list-reconciliation contract with delete and replace semantics, not an append-only updater.

### `siteotherproxies`

Persisted-action contract:

- resolve the site first
- expand enabled Bugs proxy flags to the generated record-type set
- compare the generated set with all stored site-other-record rows for the site
- keep matching stored rows unchanged
- mark stored rows for deletion when the proxy is no longer enabled
- append generated rows for newly enabled proxy types

Execution meaning:

`siteotherproxies` is also a full list-reconciliation contract, but its generated set comes from enabled proxy flags rather than location expansion.

## Dependency Notes

### `site`

`site` provides the traced site identity that the update-oriented policies rely on. Future implementation work should treat site resolution as a prerequisite contract, not as incidental setup around the list update.

### `sitereferences`

`sitereferences` is not itself a list-result updater in the same way, but it proves the same family pattern that prerequisite resolution and tuple lookup behavior can decide whether downstream persisted work proceeds.

## Execution Rule For Future Runtime Work

For this family, future runtime work should describe and test the final persisted-action set for a parent identity, not only the branch that matched during comparison.

That means a future implementation-facing fixture should be readable as:

- parent identity
- generated candidate set
- stored set before reconciliation
- persisted actions taken
- final logical result after those actions

## Immediate Follow-Up

When this family is promoted beyond parity-oriented checks, the next fixture and policy work should:

1. keep the current shared result objects for continuity
2. add explicit persisted-action wording for append, keep, delete, and replace behavior
3. keep prerequisite-stop behavior separate from normal list reconciliation
4. avoid hiding delete or replace semantics inside generic `update` labels