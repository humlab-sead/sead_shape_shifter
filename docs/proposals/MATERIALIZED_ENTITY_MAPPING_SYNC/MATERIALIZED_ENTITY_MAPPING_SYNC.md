# Sync Mapping Links After Fixed Entity Saves

## Status

- Proposed follow-up to [Reconciliation Persistence Consolidation](done/RECONCILIATION_PERSISTENCE_CONSOLIDATION.md)
- Scope: Synchronize mapping sidecar links when fixed entity values are saved
- Goal: Apply fixed-row ID changes without disturbing mappings the user did not edit

## Summary

Saving fixed entity rows can change target `public_id` values without updating links in `<project>-mapping.yml`. This affects materialized entities and non-materialized fixed entities that already have a sidecar entry. Compare the previously saved rows with the new rows before saving. Apply the resulting mapping changes and add missing links for saved IDs, while retaining existing links for unchanged rows. Extend the explicit sync endpoint so either eligible entity type can retry the exact changes if the sidecar write fails.

## Problem

Normalization uses committed sidecar links for an entity's `public_id`, even when the saved fixed row contains a blank or older ID. An ordinary row edit can therefore leave a changed ID unapplied if the sidecar is stale. Conversely, rebuilding every manual link from saved rows after an unrelated edit can erase a valid sidecar ID or replace it with an older saved value.

The earlier reconciliation persistence proposal introduced a service that rebuilds manual links from saved materialized rows. External `@load:` value updates call it for materialized entities; inline fixed-row saves do not. Non-materialized fixed entities with an existing sidecar entry also lack automatic synchronization.

## Scope

- Synchronize fixed-row ID and local-key changes for materialized entities and non-materialized fixed entities with an existing sidecar entry.
- Create a sidecar entry for a materialized fixed entity when needed; do not create one for other fixed entities.
- Preserve links and their provenance when the saved row's key and `public_id` are unchanged.
- Define a retryable partial-save response and extend the explicit sync endpoint to accept it for either eligible entity type.

## Non-Goals

- Changing the mapping sidecar schema or normalization link precedence.
- Changing reconciliation export behavior or the reconciliation catalog.
- Synchronizing non-fixed entities as part of ordinary entity edits.
- Adding a separate front-end mapping editor.

## Current Behavior

- `MaterializationService.sync_materialized_entity_mappings()` rebuilds manual links from all saved rows. It drops manual links for blank IDs and gives every rebuilt link a new committed timestamp and actor.
- The sidecar stores one link per local key. Rebuilding a manual link at a key replaces any reconciliation or import link at that key; non-manual links at other keys remain.
- The explicit `PATCH /projects/{project}/mapping/from-materialized/{entity}` endpoint rejects non-materialized entities. The external values update route calls the service after saving `@load:` values, but the service does nothing for non-materialized entities.
- Inline fixed values are saved through the entity update flow without mapping sync. Normalization applies committed sidecar links to any configured entity with a `public_id`, including non-materialized fixed entities.

## Proposed Design

### Detect changes before saving

For an eligible fixed entity, load the previous saved rows and sidecar entry before writing the new rows. Match rows by the entry's `local_key`, or by the default based on `entity.keys` when creating a materialized entry. Validate that the required key and `public_id` columns are present and that row keys are usable and unique. Compare the previous and new **saved** `public_id` values; a difference between a saved value and a sidecar target is not itself an edit.

Build a mapping change set from the comparison:

- If a row keeps the same key and saved `public_id`, retain its existing link, including `source`, `committed_at`, and `created_by`. A blank saved ID does not clear an existing link merely because another field changed.
- Add a manual link for a new row with a non-null `public_id`, or for an existing row whose `public_id` changed to a non-null value. If an unchanged row has a non-null saved ID but no sidecar link, add the missing manual link.
- When an existing row's `public_id` changes to null, delete the link at that key. When a row is removed, delete its link. Treat a local-key change as removal of the old key and addition of the new key; do not silently carry the old link to a different key.
- A blank-to-blank save cannot express an intent to clear a sidecar-only link. Use the existing mapping-link delete operation for that case. Ordinary fixed-row edits do not require a second request.

The sidecar has one link per key. A deliberate non-null ID edit replaces any link at that key with a manual link; a deliberate clear or row removal deletes the link regardless of its source. Reconciliation and import links at untouched keys remain unchanged. If the change set is empty and no entry must be created, do not write the sidecar. If an upsert already matches a manual link, retain its existing timestamp and actor.

Run this operation for inline and external fixed-value saves in the backend. For a materialized entity without an entry, create the entry and seed manual links from non-null saved IDs. For a non-materialized fixed entity without an entry, save its rows without creating a sidecar entry.

### Retry a partial save

The project configuration or external values and the mapping sidecar are separate files. Compute the change set before saving rows, then apply it to the sidecar after the row save only if its version still matches the version read before saving. If the sidecar write fails or its version changed, return a structured partial-save error that says the rows were saved and contains the exact pending changes plus the saved-row and sidecar versions needed for a retry. Do not describe the whole operation as successful.

Extend the explicit sync endpoint to accept those changes for materialized entities and non-materialized fixed entities with an existing entry. A retry applies the pending changes without recomputing a diff against the now-saved rows. Check whether the requested changes are already applied before checking versions; if so, return a no-op. Otherwise, reject changed saved rows or sidecar links for the affected keys and require review. Keep the current bodyless materialized rebuild as a separate administrative action. It must refuse to delete or replace committed links solely because saved IDs are blank or older, unless the caller explicitly requests that replacement. It is not the partial-save retry path.

## Alternatives Considered

- **Rebuild all manual links from every saved row.** This can erase a sidecar ID when an unchanged saved row has a blank or older `public_id`, and it rewrites timestamps for unrelated edits.
- **Call the sync endpoint from the front end after saving.** Other clients and direct API callers would still leave stale mappings.
- **Create sidecar entries for every fixed entity.** This duplicates saved IDs for fixed entities that do not use sidecar mappings.
- **Roll back the row save after a sidecar failure.** The two files do not share a transaction, so rollback introduces another write that can fail.

## Risks And Tradeoffs

- Comparing saved rows requires valid, unique local keys. Reject ambiguous changes before writing rows and report which keys need correction.
- A fixed-row ID edit takes precedence over an existing reconciliation or import link at the same key, and a removed row or cleared ID deletes that link. This follows from the one-link-per-key format; the save response should make this effect clear.
- A sidecar-only link beside a blank saved ID needs the explicit link-delete operation to clear it. Resaving the blank row preserves the link.
- A retry needs the pending change set from the partial-save error. If either saved rows or the affected sidecar links changed afterward, reject the retry and require review of the current state.

## Testing And Validation

- Edit a non-ID field in an inline or external fixed row whose saved `public_id` is blank or older than its sidecar target; verify the link and its metadata remain unchanged.
- Add, edit, clear, remove, and change the local key of fixed rows; verify only affected links change and the correct target IDs are used.
- Verify an edited ID replaces a reconciliation or import link at the same key, while links at untouched keys keep their source and metadata.
- Verify materialized entities create a sidecar entry when needed, non-materialized fixed entities synchronize only if an entry exists, and non-fixed saves leave the sidecar alone.
- Verify unchanged saved IDs without links gain missing manual links once, without rewriting them on later saves.
- Simulate a sidecar failure and a concurrent sidecar edit after inline and external row saves; retry the returned change set for both materialized and non-materialized fixed entities. Check repeated retries and version conflicts.
- Verify the bodyless materialized rebuild refuses to replace a committed link with a blank or older saved ID without explicit override.
- Cover single-column and compound local keys, blank IDs, and invalid or duplicate keys.

## Acceptance Criteria

- `P-AC-1` Saving eligible fixed rows applies links for added rows, edited `public_id` values, cleared IDs, removed rows, and changed local keys without a second ordinary save request.
- `P-AC-2` Materialized fixed entities create a sidecar entry when needed; non-materialized fixed entities synchronize only when an entry already exists.
- `P-AC-3` An unchanged row retains its existing sidecar link even when its saved `public_id` is blank or older than the link's target ID. Its source, timestamp, and actor remain unchanged.
- `P-AC-4` A deliberate non-null ID edit replaces any link at that key with a manual link; a deliberate clear or row removal deletes the link at that key. Links at untouched keys remain unchanged regardless of source.
- `P-AC-5` If no link changes and no entry is created, the sidecar is not written. A matching manual upsert does not change its timestamp or actor.
- `P-AC-6` Inline and external fixed-value saves use the same eligibility and change rules; non-fixed saves do not synchronize fixed-entity mappings.
- `P-AC-7` A sidecar failure after a successful row save returns the pending changes and versions. The explicit endpoint retries them for either eligible entity type, rejects intervening edits, and handles repeated application without changing links again.
- `P-AC-8` The bodyless materialized rebuild refuses to delete or replace a committed link merely because the saved row has a blank or older `public_id`, unless the caller explicitly requests that replacement.

## Planning Handoff

**Confirmed decisions**

- Compare previously saved and new rows before persistence; do not infer edits from a difference between saved rows and sidecar targets.
- Apply changes to affected keys and add missing links, preserving every untouched link and its metadata.
- Changed fixed-row IDs and row removals take precedence over any prior link at the affected key.
- Extend the explicit endpoint with a version-checked retry request for both eligible fixed-entity types. Keep its bodyless materialized rebuild separate from retry.

**Behavior to preserve**

- Normalization applies committed sidecar links to `public_id`.
- Materialized entities may create mapping entries; non-materialized fixed entities without an entry do not.
- The mapping sidecar keeps its current one-link-per-key format and manual-link precedence.

**Expected validation outcomes**

- Unrelated fixed-row edits leave sidecar-only IDs and link history intact.
- Only deliberate ID, key, or row changes affect existing links; missing links for saved IDs are added once.
- Partial saves can be retried without using the now-saved rows as a false before-image.

**Open questions**

- None for the proposed behavior. The implementation plan should identify every fixed-value save path and choose the request and response fields for pending changes and version checks.

## Final Recommendation

Synchronize eligible fixed-entity saves using changes computed from previous and new saved rows. Preserve untouched links, apply deliberate row changes at their keys, and make partial sidecar failures retryable through the extended explicit endpoint.
