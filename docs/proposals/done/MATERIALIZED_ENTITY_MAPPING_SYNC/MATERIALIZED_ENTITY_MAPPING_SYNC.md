# Sync Mapping Links After Fixed Entity Saves

## Status

- **Implemented** (branch `materialized-entity-mapping-sync`; merged in [PR #562](https://github.com/humlab-sead/sead_shape_shifter/pull/562)).
- Follow-up to [Reconciliation Persistence Consolidation](../RECONCILIATION_PERSISTENCE_CONSOLIDATION.md).
- Scope: Synchronize mapping sidecar links when eligible fixed entity values are saved.
- Goal: Apply fixed-row ID changes without disturbing mappings the user did not edit.
- Validation: phases 1-4 passed their task-plan milestones, including the grouped Core/backend regression over `P-AC-1`-`P-AC-9`, the frontend pending/retry suite, and quality checks.
- Remaining follow-up: the shared project lock is process-local. Deployment with independently writing processes still needs a cross-process file lock before claiming cross-process sidecar serialization. This does not block the implemented single-process behavior.

## Summary

Saving fixed entity rows can change target `public_id` values without updating links in `<project>-mapping.yml`. Compare the previously saved rows with the new rows, then apply only the changes for affected local keys. Preserve untouched links and their provenance. Use a defined blank-value rule, ordered local keys, and a retry contract that checks affected keys while protecting sidecar writes from concurrent updates.

## Problem

Normalization uses committed sidecar links for an entity's `public_id`, even when a saved fixed row contains a blank or older ID. An ordinary row edit can therefore leave a changed ID unapplied if the sidecar is stale. Conversely, rebuilding every manual link from saved rows after an unrelated edit can erase a valid sidecar ID or replace it with an older saved value.

The earlier reconciliation persistence proposal introduced a service that rebuilds manual links from saved materialized rows. External `@load:` value updates call it for materialized entities; inline fixed-row saves do not. Non-materialized fixed entities with an existing sidecar entry also lack automatic synchronization.

## Scope

- Synchronize fixed-row ID and row-key-value changes for entities whose configured type is `fixed`.
- Create a sidecar entry when a materialized fixed entity needs one; do not create one for other fixed entities.
- Preserve links and their provenance when the saved row's key and `public_id` are unchanged.
- Return a structured partial-save result and provide a separate endpoint for retrying its pending mapping changes.
- Keep the bodyless materialized rebuild as an additive administrative operation, with an explicit request option for replacing manual links.

## Non-Goals

- Changing the mapping sidecar schema or normalization link precedence.
- Changing reconciliation export behavior or the reconciliation catalog.
- Synchronizing non-fixed entities as part of ordinary entity edits.
- Automatically migrating mapping configuration when `entity.keys` or `entity.public_id` changes.
- Adding a separate front-end mapping editor.

## Current Behavior

- `MaterializationService.sync_materialized_entity_mappings()` rebuilds manual links from all saved rows. It skips values recognized by `pandas.isna`, but an empty string is not skipped and then fails integer conversion. Every rebuilt link gets a new committed timestamp and actor.
- Replacing manual links removes manual links absent from the new set. A rebuilt manual link at a key replaces a reconciliation or import link at that key; other non-manual links remain.
- `MappingCatalog.version` is the schema version (`"2.0"`), not a content revision. `MappingManager.save()` uses atomic file replacement but has no compare-and-write check, and each manager instance caches loaded catalogs.
- Mapping API defaults use ordered `TableConfig.safe_keys`; materialization sync currently derives defaults from `TableConfig.keys`, which is a set. Compound key order can therefore differ between writers.
- The explicit `PATCH /projects/{project}/mapping/from-materialized/{entity}` endpoint rejects non-materialized entities. The external values route calls the sync service after saving `@load:` values, but the service returns without writing for a non-materialized entity.
- Inline fixed values are saved through the entity update flow without mapping sync. Normalization applies committed sidecar links to any configured entity with a `public_id`, including non-materialized fixed entities.

## Proposed Design

### Eligibility and mapping configuration

Eligibility is based on entity type: only entities with `type: fixed` use save-time sync. Materialization controls entry creation: create a missing entry for a materialized fixed entity, and synchronize a non-materialized fixed entity only when an entry already exists.

When an entry exists, its stored `local_key` and `public_id` remain the mapping configuration used by save-time sync, even if `entity.keys` or `entity.public_id` changes. Row values changing under those stored columns are handled as data changes. Ordinary saves do not infer a configuration migration or rewrite the entry. If a stored mapping column is absent from the rows, reject the save before writing rows. Changing mapping configuration requires a separate, explicit migration; its design is outside this proposal.

When a materialized fixed entity has no entry, derive `local_key` from the ordered `TableConfig.safe_keys`. Use one shared ordered-key helper for mapping API entry creation and materialization sync. Encode compound values in that declared order. Validate that required columns exist and that every row has a usable, unique encoded key before saving.

### Compute changes from saved rows

Load the previously saved rows and sidecar entry before writing the new rows. Match rows using the existing entry's `local_key`, or the ordered default when creating a materialized entry. Compare the previous and new saved `public_id` values; a difference between a saved value and the sidecar target is not itself an edit.

Use `is_missing_fixed_entity_value` as the blank predicate for both snapshots. It treats `None`, `NaN`, empty strings, and whitespace-only strings as missing. Numeric zero is non-blank and is a valid integer target ID. A changed or new non-blank ID must pass fixed-entity ID validation and be convertible to an integer mapping target; otherwise reject the entire row save before persistence and identify the invalid row.

Build a change set by encoded local key:

- If the key and saved `public_id` are unchanged, retain its existing link, including `source`, `committed_at`, and `created_by`. A missing saved ID does not clear a sidecar link during an unrelated edit.
- Add a manual link for a new row with a non-blank ID, a row whose ID changed to a non-blank value, or an unchanged row with a non-blank ID that has no link. If the matching manual link already has the desired target, retain its metadata.
- If an existing row's ID changes from non-blank to missing, delete the link at that key regardless of source. Remove the link for a deleted row. A row key-value change is a removal at the old key plus an addition at the new key; do not move the old link to the new key.
- A missing-to-missing save cannot express an intent to clear a sidecar-only link. Use the mapping-link delete operation for that case.

A deliberate non-blank ID edit replaces any link at the affected key with a manual link. Reconciliation and import links at untouched keys remain unchanged. If the change set is empty and no entry must be created, do not write the sidecar.

### Write and retry mapping changes

Serialize the before-image read, fixed-row save, and sidecar update under the shared per-project lock. All backend sidecar writers, including mapping CRUD and reconciliation export, must use that lock when they read and write the sidecar. Read sidecar bytes from disk while holding the lock; do not use a cached catalog as the compare source. After saving, atomically replace the sidecar and refresh or invalidate the in-memory cache.

Use the SHA-256 hash of the exact sidecar bytes as its content version. This is separate from `MappingCatalog.version`; a missing sidecar has a distinct version token. Return the saved-row version from the row-save path and the sidecar content version in any pending result. Whole-file versions are fast-path checks only. If either file changed, compare the saved row state and link state for each affected key. Reject a retry only when an affected key's saved `public_id` state or sidecar link no longer matches its recorded precondition; unrelated edits elsewhere in either file do not block it.

If rows were saved but a sidecar write fails or an affected key has changed, return HTTP 200 with the normal save response plus a `mapping_sync` object whose status is `pending`. The object contains `rows_saved: true`, the exact pending changes, expected saved-row and sidecar versions, and the affected-key preconditions. Return this same structured field from inline entity updates and external values updates. The client must report that the rows were saved and mapping changes remain pending, and offer retry; it must not report the whole save as failed or fully successful.

Add a distinct `PATCH /projects/{project}/mapping/retry-fixed-entity/{entity}` endpoint that accepts the pending `mapping_sync` object. It does not recompute changes from current rows. Under the project lock, it first checks whether the affected saved rows still match the saved post-write state and whether the requested links are already present. If already applied, return a no-op success. Otherwise, apply the changes only when affected-key preconditions still match. Return HTTP 409 with the changed keys when review is required. A whole-file version mismatch alone is not a conflict.

### Keep the materialized rebuild administrative

Keep `PATCH /projects/{project}/mapping/from-materialized/{entity}` for materialized entities. A bodyless call creates a missing entry using ordered `safe_keys` and adds manual links only for non-blank saved IDs whose keys have no existing link. It preserves every existing link and does not delete or replace links.

An explicit request body with `replace_manual_links: true` opts into the current full manual-link rebuild: replace manual links from saved non-blank IDs and remove manual links not represented by those rows. A generated manual link may replace another source at the same key because the sidecar stores one link per key. Without this option, a blank or older saved ID cannot delete or replace a committed link. Keep this operation separate from retry because it recomputes from all saved rows and serves administrative seeding or repair.

## Alternatives Considered

- **Rebuild all manual links from every saved row after each save.** This can erase a sidecar ID when an unchanged row has a blank or older `public_id`, and rewrites timestamps for unrelated edits.
- **Let saved fixed rows win and use sidecar links only when a saved ID is missing.** This would remove the synchronization step, but it changes normalization precedence and can make a blank or old fixed value override a committed reconciliation or manual link. The proposal preserves sidecar-first precedence.
- **Call the sync endpoint from the front end after saving.** Other clients and direct API callers would still leave stale mappings.
- **Create sidecar entries for every fixed entity.** This duplicates saved IDs for fixed entities that do not use sidecar mappings.
- **Roll back the row save after a sidecar failure.** The two files do not share a transaction, so rollback introduces another write that can fail.

## Risks And Tradeoffs

- Comparing saved rows requires valid, unique local keys. Reject ambiguous or missing keys before writing rows and report the rows that need correction.
- A fixed-row ID edit takes precedence over an existing reconciliation or import link at the same key, and a removed row or cleared ID deletes that link. This follows from the one-link-per-key format; the save response must make this effect clear.
- A sidecar-only link beside a missing saved ID needs the explicit mapping-link delete operation to clear it. Resaving the missing row preserves the link.
- A partial save requires the pending change set from the save response. If an affected row or link changes before retry, require review of the current state. Changes at unrelated keys do not block retry.
- Mapping configuration changes are explicit operations. Save-time sync will not migrate encoded keys when `entity.keys` or `entity.public_id` changes.

## Testing And Validation

- Edit a non-ID field in inline and external fixed rows whose saved ID is missing or older than its sidecar target; verify the link and metadata remain unchanged.
- Add, edit, clear, remove, and change the row key value; verify only affected links change and the correct target IDs are used.
- Verify empty, whitespace-only, `None`, and `NaN` IDs follow the same missing rule; verify zero is accepted and an invalid changed ID prevents the row write.
- Verify an edited ID replaces a reconciliation or import link at the same key, while untouched links keep their source and metadata.
- Verify materialized fixed entities create a sidecar entry when needed, non-materialized fixed entities synchronize only if an entry exists, and non-fixed saves do not synchronize mappings.
- Verify default compound keys use the same declared order through mapping API and materialization paths.
- Simulate a sidecar write failure and an affected-key concurrent edit after inline and external row saves. Verify both return the same pending contract, retry applies the exact changes, repeated retry is a no-op, and unrelated file changes do not cause conflicts.
- Verify the bodyless materialized rebuild adds only absent links, while `replace_manual_links: true` opts into replacement.
- Verify missing stored mapping columns prevent a row save, and edits to `entity.keys` or `entity.public_id` do not rewrite the stored mapping configuration.

## Acceptance Criteria

- `P-AC-1` Saves of fixed entities apply changes for added rows, edited IDs, cleared IDs, removed rows, and row key-value changes without a second ordinary save request.
- `P-AC-2` Materialized fixed entities create a sidecar entry when needed; non-materialized fixed entities synchronize only when an entry already exists; non-fixed entities do not synchronize.
- `P-AC-3` The before/after comparison uses one missing-value predicate for `None`, `NaN`, empty strings, and whitespace-only strings. Zero is non-blank; an invalid changed non-blank ID prevents the row save.
- `P-AC-4` Unchanged rows retain existing sidecar links and metadata even when their saved IDs are missing or older. Deliberate ID edits, clears, and row removals affect only their encoded keys and follow the stated source replacement rules.
- `P-AC-5` Default compound `local_key` values use ordered `TableConfig.safe_keys` through a helper shared by mapping entry creation and materialization sync. Existing mapping configuration is not rewritten by row saves.
- `P-AC-6` Inline and external fixed-value saves use the same eligibility, delta, and partial-save response rules. An empty change set does not write the sidecar; a matching manual upsert retains its metadata.
- `P-AC-7` Sidecar content versions are hashes of bytes read from disk, distinct from the schema version. Sidecar writes and row-save sync use the shared project lock and atomic replacement. Retry uses whole-file versions as fast-path checks and affected-key preconditions as the authoritative conflict check.
- `P-AC-8` A sidecar failure after a successful row save returns HTTP 200 with a structured pending mapping result from both save paths. The client reports the partial save and can retry it through the distinct retry endpoint; changed affected keys return HTTP 409, and repeated application is a no-op.
- `P-AC-9` The bodyless materialized rebuild creates missing entries and adds only absent links. Full manual-link replacement requires `replace_manual_links: true`.

## Planning Handoff

**Confirmed decisions**

- Compare previously saved rows with new rows; do not infer edits from a difference between saved rows and sidecar targets.
- Apply changes only at affected keys and preserve every untouched link and its metadata.
- Use one missing-value predicate and the declared order of `safe_keys` for compound keys.
- Keep row-value changes separate from mapping configuration changes. Do not infer or perform a `local_key` or `public_id` migration during an ordinary row save.
- Use a disk-read sidecar content hash and shared project lock for writes. Use affected-key checks, not a whole-file hash mismatch, to decide retry conflicts.
- Keep administrative rebuild and partial-save retry as separate operations.

**Behavior to preserve**

- Normalization applies committed sidecar links to `public_id`.
- Materialized entities may create mapping entries; non-materialized fixed entities without an entry do not.
- The mapping sidecar keeps its current one-link-per-key format and manual-link precedence.

**Expected validation outcomes**

- Unrelated fixed-row edits leave sidecar-only IDs and link history intact.
- Only deliberate ID, row-key, or row-presence changes affect existing links; missing links for saved IDs are added once.
- Partial saves can be retried without using the now-saved rows as a false before-image or conflicting on unrelated file changes.
- The administrative rebuild cannot replace or remove links unless the caller opts into manual-link replacement.

**Open questions**

- None for the proposed behavior. The implementation plan should identify the shared project-lock access for every sidecar writer and carry the pending change set through both save response models and the client.

## Final Recommendation

Synchronize fixed-entity saves using changes computed from the previously saved and new rows. Preserve untouched links, define missing IDs and key order explicitly, and make partial sidecar failures retryable with per-key checks. Keep administrative rebuilding additive unless the caller explicitly requests replacement.
