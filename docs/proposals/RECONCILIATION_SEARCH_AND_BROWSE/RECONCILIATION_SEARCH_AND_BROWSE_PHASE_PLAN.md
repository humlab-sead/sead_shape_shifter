# Reconciliation Search and Browse Phase Plan

Source: [approved proposal](./RECONCILIATION_SEARCH_AND_BROWSE.md)

## Summary

Deliver the shared review workspace in four phases: Authority Service retrieval and verification, Shape Shifter decision and export safety, the persistent workspace, and per-type pilot validation. Search, exact-ID lookup, Browse, and export verification are enabled independently for each type.

Contract details that the proposal leaves open must be frozen before the relevant implementation task plan. This plan does not choose those details.

## Problem

Reviewers cannot efficiently inspect target records and save decisions for source rows that have not first been matched. Ranked candidates are not a complete vocabulary, and a saved target reference must not be exported without verifying that the target exists.

## Scope

This plan covers the paired Authority Service and Shape Shifter changes for `feature_type` and `country`, including first-time decisions, atomic saves, the persistent Search/Browse workspace, export verification, and pilot validation.

It excludes target-record creation during review, automatic decisions, server paging, recent-query history, derived application state, and a policy for previously exported unverified links. The latter remains untouched unless a separate policy is approved.

## Current Position

- Shape Shifter has an alternative-search dialog and a review preview, but a decision for a row absent from the catalog is rejected until matching has run. Saving decisions reloads catalog and preview data.
- Authority Service already publishes supported reconciliation types and honors per-query limits. Classifier suggestions use prefix matching; they are not complete browsing.
- Candidate verification currently supports policy-enabled `site`, not the two pilot types. Shape Shifter currently permits an unverified export when verification is unavailable.
- The proposal is approved; the paired deployment, live pilot data, and latency are not yet validated.

## Phase Plan

### Phase 1: Authority Retrieval and Verification

**Goal**

Provide bounded, type-consistent target retrieval and verification without changing batch matching.

**Focus**

- Add the versioned selection capabilities and complete-list and structured-details contracts to Authority Service.
- Support bounded ranked text search and type-scoped exact-ID lookup. Keep autocomplete optional and separate from complete browsing.
- Add opt-in projections and verification for the classifier `feature_type` and the non-classifier `country`; preserve existing `site` verification.

**Depends On**

- Freeze the version-1 capability, record, list, and details schemas; type-specific identifier rules; row and serialized-byte limits; too-large errors; interactive search limits and response budget; and validation diagnostics.
- Resolve how the pilot capabilities can be exercised in a controlled environment before public advertisement.

**Outputs**

- A typed service contract and pilot implementations for Phase 2 and Phase 3 integration.
- Independent capability and verification controls for each pilot type, pending Phase 4 checks.

**Acceptance Criteria**

- `PH1-AC-1` (from `P-AC-3`, `P-AC-10`) The HTTP manifest retains standard OpenRefine fields and `reconciliation.supportedTypes`; the versioned extension exposes same-service discovery and independent text-search, exact-ID, Browse, and export-verification capabilities. Bounded interactive queries honor their declared limits without changing legacy query limits.
- `PH1-AC-2` (from `P-AC-4`, `P-AC-9`) Each enabled list returns all projected items within both limits or an explicit too-large error with no partial items. Unsupported types and service failures are distinguishable from empty results.
- `PH1-AC-3` (from `P-AC-3`, `P-AC-5`, `P-AC-10`) Search, exact-ID lookup, list, details, and verification use the same type-specific URI and positive numeric target ID. Country lookups exclude non-country locations. Verification preserves ordered echoed IDs, the existing numeric `aggregate_id` contract, and site behavior.
- `PH1-AC-4` (from `P-AC-7`, `P-AC-13`) Retrieval and verification do not change target data or SIMS state. Pilot capabilities are not advertised for general use before their Phase 4 checks pass.

**Validation Milestones**

- `VM-1` HTTP contract and compatibility checks confirm manifest serialization, distinct capability flags, bounded limits, and unchanged legacy behavior (`PH1-AC-1`).
- `VM-2` Classifier and country fixtures exercise complete lists, each exceeded limit, empty and failed retrieval, exact IDs, same-ID wrong-type records, country membership, and ordered verification; existing site checks pass (`PH1-AC-2`, `PH1-AC-3`).
- `VM-3` Read-only checks confirm no target or SIMS writes and that unvalidated capabilities remain unadvertised (`PH1-AC-4`).

**Task-Plan Handoff**

- Source criteria: `P-AC-3`–`P-AC-5`, `P-AC-7`, `P-AC-9`, `P-AC-10`, and `P-AC-13`.
- Use service-owned configuration and existing type registrations; preserve classifier prefix semantics, use the country subset and `location_id`, and keep verification independent of SIMS binding policy.
- Blocking decisions: the contract and limits listed under Depends On, and the controlled pre-advertisement test configuration.

**Readiness**

Requires the named contract, limit, and test-configuration decisions before an implementation task plan.

### Phase 2: Atomic Decisions and Verified Export

**Goal**

Save first-time review decisions atomically and require verification before exporting accepted links.

**Focus**

- Add batch saves that resolve and validate authorized current source rows once and conditionally write against a catalog content hash.
- Apply the shared type-aware local reference validator to every accepted-decision writer, catalog replacement, catalog read diagnostics, and export preflight.
- Update existing clients with the hash precondition and retain the existing export protocol, manual-link protections, and New-only outage behavior.

**Depends On**

- Phase 1's frozen identifier and verification contract and implemented verification support for the pilot types.
- Freeze the batch request and response, browser draft format, source-row comparison and diagnostics, catalog-hash read/write contract, and conflict refresh/reapply behavior.

**Outputs**

- Hash-aware catalog operations and an atomic batch decision interface for the workspace.
- Local reference validation and an export gate that refuses unverified accepted links.

**Acceptance Criteria**

- `PH2-AC-1` (from `P-AC-6`, `P-AC-8`) A valid keyed row without a prior catalog entry can be accepted or marked New. A batch resolves source rows once; missing, duplicate, unauthorized, or changed rows reject the entire batch without catalog changes.
- `PH2-AC-2` (from `P-AC-6`, `P-AC-8`) Catalog reads return a content hash; every catalog write, including legacy decision, matching, and whole-catalog replacement writes, requires the current hash. Missing or stale hashes conflict, including concurrent writes to unrelated rows. Success returns saved decisions and the new hash.
- `PH2-AC-3` (from `P-AC-5`, `P-AC-6`) The shared validator checks the URI format and type, positive target ID, and URI/ID agreement on all accepted writes. Invalid existing entries remain visible with repairable row-specific issues; replacements report all invalid accepted references and write nothing. Valid prior manual reconciliations remain reusable.
- `PH2-AC-4` (from `P-AC-5`, `P-AC-7`, `P-AC-10`, `P-AC-12`) Saving does not call details or verify target existence. Before sidecar changes, export validates accepted references and requires successful ordered Authority verification for every accepted link it would write; unsupported types, malformed replies, invalid targets, and outages block the export. Valid New-only saves and exports remain possible during an outage.
- `PH2-AC-5` (from `P-AC-1`, `P-AC-12`) Review decisions do not alter source labels, ordered business keys, or Core `system_id` values. Save and export remain separate; manual/unowned link protection, ownership cleanup, offline normalization, and downstream foreign-key semantics remain unchanged.

**Validation Milestones**

- `VM-4` First-time, compound-key, changed-row, unauthorized-row, duplicate-key, and multi-draft checks demonstrate one source resolution and all-or-nothing saves (`PH2-AC-1`).
- `VM-5` Concurrent and stale decision and JSON/YAML replacement writes conflict; invalid catalog entries remain visible, repairs succeed, and invalid replacements leave the catalog unchanged (`PH2-AC-2`, `PH2-AC-3`).
- `VM-6` Export and normalization checks use actual IDs and New approvals; invalid references, wrong-type or non-country IDs, verification failures, and outages never write unverified accepted links. New-only outage and existing site/manual-link cases remain valid (`PH2-AC-4`, `PH2-AC-5`).

**Task-Plan Handoff**

- Source criteria: `P-AC-1`, `P-AC-5`–`P-AC-8`, `P-AC-10`, and `P-AC-12`.
- Preserve project authorization, project locks, the single-worker deployment assumption, readable legacy catalogs, and legacy routes. Existing callers must supply the hash; a missing hash is a conflict, not a compatibility fallback.
- Blocking decisions: the save, draft, source-validation, diagnostic, and hash contracts listed under Depends On. Phase 1 verification must be available before integration.

**Readiness**

Requires the named save-contract decisions and Phase 1 output before an implementation task plan.

### Phase 3: Persistent Review Workspace

**Goal**

Let reviewers search or browse, stage explicit decisions, and continue through the source queue in one pane.

**Focus**

- Provide review entry without Find Candidates, a Needs review queue, persistent Search/Browse tabs, notes, keyboard controls, and explicit skip, New, save, and export actions.
- Use the Phase 1 capabilities and Phase 2 batch interface; filter and sort only complete browse lists locally.
- Keep requests race-safe and persist scoped, visibly unsaved drafts and resume state in the browser.

**Depends On**

- Phase 1 retrieval and capability outputs and Phase 2 save/export outputs, including their frozen contracts.

**Outputs**

- A review workspace ready for paired pilot validation.
- Browser drafts and saved-row updates that do not require a full preview reload after each decision.

**Acceptance Criteria**

- `PH3-AC-1` (from `P-AC-1`, `P-AC-2`, `P-AC-8`) Review opens without Find Candidates. Ten consecutive rows can be searched or browsed, staged or skipped, and advanced using keyboard or labelled controls. One successful batch patches affected rows and counts; a failure preserves all drafts and marks none as saved.
- `PH3-AC-2` (from `P-AC-3`, `P-AC-9`) Operator text and advertised context use bounded ranked search; `id: <positive integer>` performs a type-scoped exact lookup. Unknown IDs return no record, malformed `id:` input produces an error without fuzzy fallback, and stale responses cannot appear current or enable acceptance.
- `PH3-AC-3` (from `P-AC-4`, `P-AC-5`, `P-AC-9`) Browse filters and sorts a complete list locally, using literal case-insensitive text, AND field filters, and stable label/ID ordering. It reports oversized lists explicitly. Equivalent search and browse selections retain the same URI and ID, need no extra details request to save, and browse rows have no invented confidence.
- `PH3-AC-4` (from `P-AC-7`, `P-AC-10`, `P-AC-12`) Empty or failed retrieval never approves New. A new workspace requires an Authority response; after opening, saved-decision inspection and valid New-only saves remain available during an outage. Missing Browse capability leaves legacy review usable. Save decision and Export are clearly distinct, without derived application state.
- `PH3-AC-5` (from `P-AC-2`, `P-AC-9`, `P-AC-11`) Browser storage restores scoped focus, mode, filters, sort, queries, and unsaved decision drafts. Another row or project never inherits a draft or confirmed selection. Text entry and composition do not trigger bare-letter decision shortcuts; scheduled and out-of-order requests cannot replace current results.

**Validation Milestones**

- `VM-7` Keyboard and labelled-control checks complete ten rows, including skips, batch success, batch failure, draft retention, and affected-row updates (`PH3-AC-1`).
- `VM-8` Search, exact-ID, complete-list filtering/sorting, wrong-type IDs, literal wildcard characters, unsupported features, remote failures, and out-of-order responses produce the expected results and states (`PH3-AC-2`, `PH3-AC-3`).
- `VM-9` Resume, project/row isolation, text composition, missing-extension, cold-start and already-open outage, and Save/Export checks preserve the stated behavior (`PH3-AC-4`, `PH3-AC-5`).

**Task-Plan Handoff**

- Source criteria: `P-AC-1`–`P-AC-5`, `P-AC-7`–`P-AC-12`.
- Use the approved 300 ms initial typeahead debounce, immediate Enter submission, explicit decision shortcuts, and versioned browser storage. Never restore a target result as a confirmed selection or persist full target collections as fresh.
- The Phase 1 and Phase 2 contract decisions and outputs are prerequisites; no additional workspace design is implied by this plan.

**Readiness**

Requires the Phase 1 and Phase 2 contract decisions and completed outputs before an implementation task plan.

### Phase 4: Per-Type Pilot and Capability Release

**Goal**

Validate the paired workflow and advertise only capabilities that pass for each pilot type.

**Focus**

- Test the exact Shape Shifter and Authority Service pair with representative classifier and country data, including live projection and size checks.
- Record the initial workflow baseline in a named environment and gate each type and capability independently.
- Confirm actual export and normalization results and the absence of retrieval-time writes.

**Depends On**

- Phase 1–3 validated outputs, a named pilot environment, and selected service images implementing the approved contracts.
- Per-type live data projection, row and byte measurements, browse-limit behavior, search latency, and verification checks.

**Outputs**

- Recorded pilot results and initial timing/request baseline.
- Independently advertised capabilities for each type that passes its checks; failures remain unadvertised.

**Acceptance Criteria**

- `PH4-AC-1` (from `P-AC-3`–`P-AC-5`, `P-AC-10`, `P-AC-13`) Each advertised `feature_type` or `country` capability passes its own paired integration and keyboard/browser checks against the selected service pair. Search, exact-ID, Browse, and export readiness remain independent; one unready type does not block a passing type.
- `PH4-AC-2` (from `P-AC-1`, `P-AC-2`, `P-AC-6`–`P-AC-9`, `P-AC-11`–`P-AC-13`) The pilot covers first-time review, atomic and conflicting saves, resume, outage behavior, real exported IDs and New approvals, and unchanged source identity. Retrieval produces no target or SIMS writes.
- `PH4-AC-3` (from `P-AC-13`) The named environment records search/browse median and 95th-percentile times, time and interactions per decision and per New decision, request counts, and preview/normalization invocations as the initial baseline, without claiming improvement over the old workflow.

**Validation Milestones**

- `VM-10` Per-type contract, live projection, limit, latency, verification, and browser results support each advertised capability; failed checks leave only the affected type or capability unadvertised (`PH4-AC-1`).
- `VM-11` A paired end-to-end run includes 100 source rows with 90 intentionally New, compound keys, duplicate labels, source changes, conflicts, outages, exported IDs, normalization, and no-write checks (`PH4-AC-2`).
- `VM-12` The baseline identifies the service pair, environment, fixture, measurement method, and all required timing and request measurements (`PH4-AC-3`).

**Task-Plan Handoff**

- Source criteria: `P-AC-1`–`P-AC-13`. Use the proposal's validation cases and the per-type gates rather than treating successful catalog saves as proof of target existence.
- Blocking decisions: name the pilot environment and select the paired service images. Measure actual data and latency; do not assume production list sizes.

**Readiness**

Requires the named pilot environment and paired service images, plus completed Phase 1–3 outputs.

## Cross-Phase Rules

- Freeze each contract before planning its implementation; preserve the proposal's fixed semantics rather than replacing them with server-side review sessions or per-row versions.
- Keep capability advertisement opt-in and type-specific. Exercise new capabilities in a controlled configuration until the paired checks pass.
- Coordinate hash-aware clients with the writer change. Require verification before exporting accepted links, including existing `site` links; never use an outage fallback for them.
- Save stores catalog decisions; only explicit export updates the sidecar. Retrieval and review do not allocate target IDs or alter SIMS state.
- Do not silently modify links exported unverified by earlier versions. A separate policy is required before recovery or re-export work for those entries.

## Validation Strategy

Use service contract and fixture checks first, then Shape Shifter atomic-write and export regressions, followed by browser interaction and paired integration checks. Validate each advertised capability against its own type and the selected deployment pair. Record failures and keep the affected capability unadvertised; do not defer identity, atomicity, or export verification to a later rollout.
