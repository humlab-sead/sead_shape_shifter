# Sync Mapping Links After Fixed Entity Saves — Phase Plan

Source: [Sync Mapping Links After Fixed Entity Saves](./MATERIALIZED_ENTITY_MAPPING_SYNC.md).

## Summary

Deliver fixed-entity mapping synchronization in four phases: define the row comparison, coordinate sidecar writes and ordinary saves, make partial saves retryable, then change the administrative rebuild. Each phase has a validation result before work advances to behavior that depends on it.

## Problem

An ordinary fixed-row save can leave committed sidecar links out of step with deliberately edited IDs. Rebuilding all manual links after every save would also replace or remove links that the user did not edit. The delivery sequence must preserve untouched links while handling two save paths and partial writes to separate files.

## Scope

This plan covers fixed-row comparison and validation, mapping sidecar coordination, inline and external value saves, pending results and retry, client handling, and the materialized rebuild. It excludes mapping schema or normalization-precedence changes, automatic mapping-configuration migration, non-fixed save synchronization, and a separate mapping editor.

## Current Position

- The source proposal is marked **Proposed** and records no open behavior questions. This plan sequences its stated design.
- External `@load:` value saves currently invoke the materialized rebuild after saving rows; inline fixed-row saves do not invoke mapping sync.
- The current rebuild replaces manual links from all saved rows. Its default compound-key order comes from `TableConfig.keys`, a set, while `TableConfig.safe_keys` preserves declared order.
- `MappingManager` caches loaded catalogs and saves by atomic replacement. The proposal identifies shared locking, disk-read content versions, and affected-key retry checks as missing.

## Phase Plan

### Phase 1: Define fixed-row changes

**Goal**

Produce a validated, deterministic change set from previously saved and new fixed rows.

**Focus**

- Share the ordered `safe_keys` default between mapping entry creation and materialization paths; keep an existing entry's stored mapping columns authoritative for saves.
- Define fixed-entity eligibility, entry-creation policy, one missing-value rule, and pre-write checks for columns, encoded keys, and changed IDs.
- Compare saved rows by encoded key. Record only additions, deliberate ID changes or clears, row removals, key changes, and missing links for saved non-blank IDs.

**Depends On**

- The source proposal's fixed-row comparison and mapping-configuration decisions.

**Outputs**

- Shared key and missing-value rules, validated row comparisons, and an exact affected-key change set for save-time use.

**Acceptance Criteria**

- `PH1-AC-1` (from `P-AC-3`) `None`, `NaN`, empty, and whitespace-only IDs compare as missing; zero remains a valid target; an invalid changed non-blank ID or unusable row key prevents the row write.
- `PH1-AC-2` (from `P-AC-5`) New default compound keys use declared `safe_keys` order in both entry-creation paths; an existing entry's `local_key` and `public_id` are not rewritten by an ordinary save.
- `PH1-AC-3` (from `P-AC-4`) The change set leaves unchanged rows out, distinguishes deliberate edits from saved-value/sidecar differences, and treats a row key change as removal plus addition.
- `PH1-AC-4` (from `P-AC-2`) Only configured fixed entities qualify; materialized fixed entities may create missing entries, while other fixed entities require an existing entry.

**Validation Milestones**

- `VM-1` Focused comparison and validation checks cover missing values, invalid IDs, duplicate or missing keys, ordered compound keys, and stored mapping columns (`PH1-AC-1`, `PH1-AC-2`).
- `VM-2` Change-set checks cover eligibility, unchanged rows, deliberate edits, and key changes (`PH1-AC-3`, `PH1-AC-4`).

**Task-Plan Handoff**

- Use `P-AC-2` through `P-AC-5` and the Planning Handoff decisions. Identify where both save paths obtain saved rows and mapping entries; preserve sidecar-first normalization and do not design a configuration migration. No behavior decision blocks this phase.

**Readiness**

Ready for a task plan.

### Phase 2: Coordinate sidecar writes and ordinary saves

**Goal**

Apply successful fixed-row changes in the same ordinary save flow while protecting all sidecar writers from lost updates.

**Focus**

- Use the shared per-project lock for the before-image read, row save, and sidecar update, and for every backend writer that reads and writes the sidecar.
- Read exact sidecar bytes from disk for a SHA-256 content version, distinct from the schema version; preserve atomic replacement and refresh or invalidate cached catalogs.
- Apply only affected-key changes through both inline and external saves, preserving untouched links and metadata.

**Depends On**

- Phase 1's validated change set and eligibility rules.

**Outputs**

- Coordinated sidecar writes and a successful save-time sync path for both fixed-value save flows, with row and sidecar versions available to Phase 3.

**Acceptance Criteria**

- `PH2-AC-1` (from `P-AC-7`) All backend sidecar writers use the project lock and disk-read content version; a missing sidecar has a distinct version token; writes are atomic and do not leave stale cached catalogs.
- `PH2-AC-2` (from `P-AC-1`, `P-AC-2`) A successful eligible save applies additions, ID edits or clears, removals, and row key changes without a second ordinary request; non-fixed saves and fixed entities without an eligible entry follow the stated limits.
- `PH2-AC-3` (from `P-AC-4`, `P-AC-6`) Inline and external saves use the same affected-key rules; untouched links retain source and metadata, an empty change set does not write the sidecar, and an already matching manual link retains its metadata.

**Validation Milestones**

- `VM-3` Concurrent-writer and cache checks show serialized sidecar updates and correct content versions (`PH2-AC-1`).
- `VM-4` Successful-save checks through both paths show the required link changes and preservation rules (`PH2-AC-2`, `PH2-AC-3`).

**Task-Plan Handoff**

- Use `P-AC-1`, `P-AC-2`, `P-AC-4`, `P-AC-6`, and `P-AC-7`. Identify every backend sidecar writer before coordinating them; keep row-value changes separate from mapping-configuration changes. Phase 3 must complete the partial-save behavior before save-time sync is considered complete.

**Readiness**

Ready for a task plan after Phase 1's output is available.

### Phase 3: Return pending saves and support retry

**Goal**

Make a saved-row/failed-sidecar outcome explicit and safely retryable for both save paths.

**Focus**

- Return HTTP 200 with the normal save response and a shared pending `mapping_sync` result containing the exact changes, saved-row and sidecar versions, and affected-key preconditions.
- Add the distinct fixed-entity retry operation. Check saved post-write row state and already-applied links first, then use affected-key preconditions when whole-file versions changed.
- Have the client report rows saved with mapping changes pending, offer retry, and show changed-key conflicts for review.

**Depends On**

- Phase 2's coordinated save flow, content versions, and exact change set.

**Outputs**

- A consistent pending response, safe retry path, and client recovery flow for partial saves.

**Acceptance Criteria**

- `PH3-AC-1` (from `P-AC-6`, `P-AC-8`) A sidecar failure or affected-key conflict after either row save returns the same structured pending `mapping_sync` result with `rows_saved: true`; the client does not report a complete failure or complete success.
- `PH3-AC-2` (from `P-AC-7`, `P-AC-8`) Retry applies the supplied changes without recomputing from current rows; unrelated file edits do not block it, changed affected keys return HTTP 409 with those keys, and repeated application is a no-op.
- `PH3-AC-3` (from `P-AC-8`) The client can retry the pending result through the distinct retry endpoint and presents conflicts for review.

**Validation Milestones**

- `VM-5` Sidecar-failure checks through both save paths verify pending fields and saved-row status (`PH3-AC-1`).
- `VM-6` Retry and client checks verify already-applied results, unrelated edits, affected-key conflicts, and user-visible recovery (`PH3-AC-2`, `PH3-AC-3`).

**Task-Plan Handoff**

- Use `P-AC-6` through `P-AC-8`. Carry the pending change set through both response models and the client; use saved post-write rows as retry preconditions, never as a new before-image. No behavior decision blocks this phase.

**Readiness**

Ready for a task plan after Phase 2's output is available.

### Phase 4: Make the materialized rebuild additive

**Goal**

Keep administrative seeding safe by default while retaining an explicit full replacement option.

**Focus**

- Make a bodyless materialized rebuild create a missing entry and add only absent links for non-blank saved IDs.
- Reserve full manual-link replacement for `replace_manual_links: true`, using the same ordered key rules and coordinated sidecar writes.
- Validate the combined save, retry, normalization-preservation, and administrative flows.

**Depends On**

- Phase 1's ordered keys, Phase 2's coordinated writes, and Phase 3's separate retry contract.

**Outputs**

- Additive administrative rebuild with explicit replacement, plus complete validation of the proposal's acceptance criteria.

**Acceptance Criteria**

- `PH4-AC-1` (from `P-AC-9`) A bodyless rebuild adds only absent links and preserves existing links; full manual-link replacement occurs only with `replace_manual_links: true`.
- `PH4-AC-2` (from `P-AC-5`, `P-AC-9`) Rebuild entry creation uses the shared ordered `safe_keys` default, and remains separate from retry's exact pending change set.

**Validation Milestones**

- `VM-7` Administrative checks show additive defaults, explicit replacement, and ordered compound keys (`PH4-AC-1`, `PH4-AC-2`).
- `VM-8` Grouped regression checks confirm the complete `P-AC-1` through `P-AC-9` behavior across both save paths, retry, and rebuild (`PH4-AC-1`, `PH4-AC-2`, and earlier phase criteria).

**Task-Plan Handoff**

- Use `P-AC-5` and `P-AC-9`, plus all earlier phase validation results. Preserve the one-link-per-key format and sidecar-first normalization. No behavior decision blocks this phase.

**Readiness**

Ready for a task plan after Phases 1–3 provide their outputs.

## Cross-Phase Rules

- Keep mapping configuration changes as explicit operations; ordinary row saves use stored mapping columns when an entry exists.
- Preserve untouched links, their source, and their metadata throughout save and rebuild changes.
- Coordinate every backend sidecar writer before treating save-time sync as complete; a partial row/sidecar save must remain visible and retryable.
- Keep administrative rebuild separate from retry: rebuild reads all saved rows, while retry applies the supplied pending changes.

## Validation Strategy

Validate comparison and eligibility rules first (`VM-1`–`VM-2`), then successful writes and writer coordination (`VM-3`–`VM-4`). Exercise partial saves and affected-key retry before client recovery is complete (`VM-5`–`VM-6`). Finish with administrative behavior and grouped regression over all proposal criteria (`VM-7`–`VM-8`). Exact test cases and commands belong in each phase task plan.
