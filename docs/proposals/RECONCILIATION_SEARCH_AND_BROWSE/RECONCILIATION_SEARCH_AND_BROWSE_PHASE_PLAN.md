# Reconciliation Search and Browse Phase Plan

Source: [approved proposal](./RECONCILIATION_SEARCH_AND_BROWSE.md)

Related: [Phase 1 task plan](./RECONCILIATION_SEARCH_AND_BROWSE_PHASE_1_TASK_PLAN.md), [Phase 2 frozen save contract](./RECONCILIATION_SEARCH_AND_BROWSE_PHASE_2_CONTRACT.md)

## Summary

Deliver the shared review workspace in four phases: Authority Service retrieval and verification, Shape Shifter decision and export safety, the persistent workspace, and per-type pilot validation. Search, exact-ID lookup, Browse, and export verification are enabled independently for each type.

The Phase 1 contract and initial limits are approved and implemented. The Phase 2 save contract is frozen in the linked contract document. Stale-view detection moved from Phase 2 to Phase 3, so Phase 2 carries no client-supplied catalog precondition and no breaking API change.

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
- The Phase 1 contract and controlled test configuration are approved. Phase 1 is implemented on the Authority Service `reconciliation-search-and-browse` branch at commit `1f3f1b8`, with both pilot capabilities disabled in the shipped configuration. Phase 4 gates remain open.
- The Phase 2 save contract is frozen in [the contract document](./RECONCILIATION_SEARCH_AND_BROWSE_PHASE_2_CONTRACT.md): serialized catalog writes, the batch request and response, save-time source-row validation, the shared local reference validator, and error shapes.
- Stale-view detection, and with it any client-supplied catalog precondition, moved to Phase 3. Existing catalog routes and clients keep their current payloads, so Phase 2 carries no breaking API change.

## Phase Plan

### Phase 1: Authority Retrieval and Verification

**Goal**

Provide bounded, type-consistent target retrieval and verification without changing batch matching.

**Focus**

- Add the versioned selection capabilities and complete-list and structured-details contracts to Authority Service.
- Support bounded ranked text search and type-scoped exact-ID lookup. Keep autocomplete optional and separate from complete browsing.
- Add opt-in projections and verification for the classifier `feature_type` and the non-classifier `country`; preserve existing `site` verification.

**Depends On**

- The approved proposal and version-1 contract recorded in the handoff below.
- Existing reconciliation registrations and candidate-verification protocol.

**Outputs**

- A typed service contract and pilot implementations for Phase 2 and Phase 3 integration.
- Independent capability and verification controls for each pilot type, pending Phase 4 checks.

**Delivered**

- Authority Service commit `1f3f1b8` (pull request [#53](https://github.com/humlab-sead/sead_authority_service/pull/53), open against `dev`) adds `reconciliation.record_selection` version 1 with `GET /records/types`, `GET /records/{type}`, and `GET /records/{type}/details`, marked interactive search on `POST /reconcile`, and pilot verification through `POST /reconcile/verify-candidates`.
- `feature_type` and `country` each expose the five capability flags; the shipped `config/config.yml` sets all of them to `false`.
- Validated by unit tests and a read-only integration round trip against a disposable database; no capability is enabled for general use.

**Acceptance Criteria**

- `PH1-AC-1` (from `P-AC-3`, `P-AC-10`) The HTTP manifest retains standard OpenRefine fields and `reconciliation.supportedTypes`; the versioned extension exposes same-service discovery and independent text-search, exact-ID, Browse, and export-verification capabilities. Bounded interactive queries honor their declared limits without changing legacy query limits.
- `PH1-AC-2` (from `P-AC-4`, `P-AC-9`) Each enabled list returns all projected items within both limits or an explicit too-large error with no partial items. Unsupported types and service failures are distinguishable from empty results.
- `PH1-AC-3` (from `P-AC-3`, `P-AC-5`, `P-AC-10`) Search, exact-ID lookup, list, details, and verification use the same type-specific URI and positive numeric target ID. Country lookups exclude non-country locations. Verification preserves ordered echoed IDs, the existing numeric `aggregate_id` contract, and site behavior.
- `PH1-AC-4` (from `P-AC-7`, `P-AC-13`) Retrieval and verification do not change target data or SIMS state. Pilot capabilities are not advertised for general use before their Phase 4 checks pass.

**Validation Milestones**

- `VM-1` HTTP contract and compatibility checks confirm manifest serialization, distinct capability flags, rejection above the interactive limit, and unchanged legacy behavior (`PH1-AC-1`).
- `VM-2` Classifier and country fixtures exercise complete lists, each exceeded limit, empty and failed retrieval, exact IDs, same-ID wrong-type records, country membership, and ordered verification; existing site checks pass (`PH1-AC-2`, `PH1-AC-3`).
- `VM-3` Read-only checks confirm no target or SIMS writes and that unvalidated capabilities remain unadvertised (`PH1-AC-4`).

**Task-Plan Handoff**

- Source criteria: `P-AC-3`–`P-AC-5`, `P-AC-7`, `P-AC-9`, `P-AC-10`, and `P-AC-13`.
- Use service-owned configuration and existing type registrations; preserve classifier prefix semantics, use the country subset and `location_id`, and keep verification independent of SIMS binding policy.
- **Discovery:** Add `reconciliation.record_selection: {version: 1, types_path: "/records/types"}` to the manifest. `GET /records/types` returns `{types: [...]}`. Each type entry contains `type`, the independent `search_supported`, `identifier_search_supported`, `browse_supported`, `details_supported`, and `export_verification_supported` flags, `id_base`, `id_path`, and the limits and field metadata below. Missing capability flags mean unsupported.
- **Fields and limits:** Initial per-type limits are 500 rows, 1,048,576 bytes for the complete uncompressed UTF-8 JSON response including its envelope, and 50 interactive search results. Advertise them as `browse_max_rows`, `browse_max_bytes`, and `interactive_search_max_results`; use null for a limit when its capability is unsupported. Limits remain configurable independently per type.
- **Field metadata:** `display_fields` is an array of `{name, source, label, value_type, display}` with unique names. `source` is `record` or `fields`; `value_type` is `string`, `integer`, `number`, or `boolean`. `text_filter_fields` and `sort_fields` are arrays of declared field names. `field_filters` contains `{field, operator}` entries using `contains_ci` for literal case-insensitive substring matching or `equals` for exact scalar matching; field filters combine with AND.
- **Records and lists:** A record is `{id, target_id, type, name, description?, fields}` with string URI, type and name, positive integer `target_id`, optional string or null description, and declared scalar or null `fields` values. A successful list returns `{items: [...], completeness: "complete"}`; it rejects filter, sort, and paging parameters. A too-large response contains no items.
- **Details:** `GET /records/{type}/details` accepts exactly one of `id` or `target_id` and returns `{item: record}`. The `id` form uses `details_supported`; the `target_id` form uses `identifier_search_supported`, independently of supplementary URI details.
- **Identifiers:** `id_base` is an absolute URI ending in `/`; `id_path` is the type path segment, `feature_type` or `country` for the pilot. Use the existing site-style parser: compare scheme and host without case sensitivity; reject query strings, fragments, and extra path segments; and accept positive ASCII decimal IDs, including leading zeros. Country IDs are `location_id` values and must belong to the country subset.
- **Interactive search:** `X-Record-Selection: interactive` on `POST /reconcile` requires exactly one query and an explicit positive limit no greater than the advertised cap. Unmarked requests keep existing behavior. Gate each type's interactive search on a 2,000 ms p95 budget measured through the Shape Shifter backend over 100 representative searches after warm-up.
- **Errors and diagnostics:** New Authority errors use `{error: {code, message}}`: 409 `too_large_to_browse`, 404 `record_not_found`, 422 `invalid_request`, `unsupported_type`, `unsupported_capability`, or `search_limit_exceeded`, and 503 `database_unavailable`. Shape Shifter retains its existing error envelope and includes row issues as `{row_index, local_key_value, field, code, message}`. Index, key, and field can be null, but an issue must identify the row by index or key.
- **Controlled testing:** Enable pilot capabilities in an isolated test or staging service pair. Keep each capability unadvertised for general use until its Phase 4 checks pass.
- Blocking decisions: none for Phase 1 task planning. Pilot measurements and the deployed pair remain Phase 4 gates.

**Readiness**

Ready for a task plan.

### Phase 2: Atomic Decisions and Verified Export

**Goal**

Save first-time review decisions atomically and require verification before exporting accepted links.

**Focus**

- Add batch saves that resolve and validate authorized current source rows once and write under the existing per-project lock.
- Apply the shared type-aware local reference validator to every accepted-decision writer, catalog replacement, catalog read diagnostics, and export preflight.
- Close the unlocked registry create and update routes so every catalog write is serialized, while retaining the existing export protocol, manual-link protections, New-only outage behavior, and current client routes.

**Depends On**

- Phase 1's frozen identifier and verification contract and implemented verification support for the pilot types (Authority Service commit `1f3f1b8`).
- The frozen Phase 2 save contract in [the contract document](./RECONCILIATION_SEARCH_AND_BROWSE_PHASE_2_CONTRACT.md): serialized catalog writes, batch request and response, save-time source-row comparison, the shared validator, and error shapes.

**Outputs**

- Serialized catalog writes and an atomic batch decision interface for the workspace.
- Local reference validation and an export gate that refuses unverified accepted links.

**Acceptance Criteria**

- `PH2-AC-1` (from `P-AC-6`, `P-AC-8`) A valid keyed row without a prior catalog entry can be accepted or marked New. A batch resolves source rows once; missing, duplicate, unauthorized, or changed rows reject the entire batch without catalog changes.
- `PH2-AC-2` (from `P-AC-6`, `P-AC-8`) Every catalog write loads, changes, and saves under the project lock, including registry create and update, so a concurrent writer's decisions for other rows are never lost. A successful batch returns its saved decisions in request order; a write that cannot be applied leaves the catalog unchanged.
- `PH2-AC-3` (from `P-AC-5`, `P-AC-6`) The shared validator checks the URI format and type, positive target ID, and URI/ID agreement on all accepted writes. Invalid existing entries remain visible with repairable row-specific issues; replacements report all invalid accepted references and write nothing. Valid prior manual reconciliations remain reusable.
- `PH2-AC-4` (from `P-AC-5`, `P-AC-7`, `P-AC-10`, `P-AC-12`) Saving does not call details or verify target existence. Before sidecar changes, export validates accepted references and requires successful ordered Authority verification for every accepted link it would write; unsupported types, malformed replies, invalid targets, and outages block the export. Valid New-only saves and exports remain possible during an outage.
- `PH2-AC-5` (from `P-AC-1`, `P-AC-12`) Review decisions do not alter source labels, ordered business keys, or Core `system_id` values. Save and export remain separate; manual/unowned link protection, ownership cleanup, offline normalization, and downstream foreign-key semantics remain unchanged.

**Validation Milestones**

- `VM-4` First-time, compound-key, changed-row, unauthorized-row, duplicate-key, and multi-draft checks demonstrate one source resolution and all-or-nothing saves (`PH2-AC-1`).
- `VM-5` Concurrent decision, registry, and matching writes each keep the others' changes; two batches on the same business key leave one decision and a readable catalog; invalid catalog entries remain visible, repairs succeed, and invalid replacements leave the catalog unchanged (`PH2-AC-2`, `PH2-AC-3`).
- `VM-6` Export and normalization checks use actual IDs and New approvals; invalid references, wrong-type or non-country IDs, verification failures, and outages never write unverified accepted links. New-only outage and existing site/manual-link cases remain valid (`PH2-AC-4`, `PH2-AC-5`).

**Task-Plan Handoff**

- Source criteria: `P-AC-1`, `P-AC-5`–`P-AC-8`, `P-AC-10`, and `P-AC-12`.
- Preserve project authorization, project locks, the single-worker deployment assumption, readable legacy catalogs, and legacy routes. No route gains a precondition; resolve and validate source rows before taking the project lock, and apply decisions inside it.
- The batch decision route, save-time validation order, and error shapes are fixed in [the frozen contract](./RECONCILIATION_SEARCH_AND_BROWSE_PHASE_2_CONTRACT.md). Do not re-decide them; raise a contract change if implementation shows one cannot work.
- Replacing `_extract_id_from_uri` with the shared type-aware validator changes accepted-reference handling on legacy routes too. Keep the existing atomicity, side-effect, and ownership behavior around it.
- Stale-view detection and any catalog precondition belong to Phase 3. Do not add them here.

**Readiness**

Ready for a task plan.

### Phase 3: Persistent Review Workspace

**Goal**

Let reviewers search or browse, stage explicit decisions, and continue through the source queue in one pane.

**Focus**

- Provide review entry without Find Candidates, a Needs review queue, persistent Search/Browse tabs, notes, keyboard controls, and explicit skip, New, save, and export actions.
- Use the Phase 1 capabilities and Phase 2 batch interface; filter and sort only complete browse lists locally.
- Keep requests race-safe and persist scoped, visibly unsaved drafts and resume state in the browser.
- Detect a stale view before saving: warn and confirm when a draft would replace a saved decision for the same key that changed since the workspace loaded it, and keep the reviewer's staged decisions when that happens.
- Keep that pre-save comparison client-side and advisory. Per-row expected state on the save contract stays deferred (backlog R33).

**Depends On**

- Phase 1 retrieval and capability outputs (Authority Service commit `1f3f1b8`) and Phase 2 save/export outputs, including their frozen contracts and the serialized catalog writes Phase 2 delivers.

**Outputs**

- A review workspace ready for paired pilot validation.
- Browser drafts and saved-row updates that do not require a full preview reload after each decision.
- A pre-save warning when a draft would replace a decision changed since load, with staged decisions preserved.

**Acceptance Criteria**

- `PH3-AC-1` (from `P-AC-1`, `P-AC-2`, `P-AC-8`) Review opens without Find Candidates. Ten consecutive rows can be searched or browsed, staged or skipped, and advanced using keyboard or labelled controls. One successful batch patches affected rows and counts; a failure preserves all drafts and marks none as saved.
- `PH3-AC-2` (from `P-AC-3`, `P-AC-9`) Operator text and advertised context use bounded ranked search; `id: <positive integer>` performs a type-scoped exact lookup. Unknown IDs return no record, malformed `id:` input produces an error without fuzzy fallback, and stale responses cannot appear current or enable acceptance.
- `PH3-AC-3` (from `P-AC-4`, `P-AC-5`, `P-AC-9`) Browse filters and sorts a complete list locally, using literal case-insensitive text, AND field filters, and stable label/ID ordering. It reports oversized lists explicitly. Equivalent search and browse selections retain the same URI and ID, need no extra details request to save, and browse rows have no invented confidence.
- `PH3-AC-4` (from `P-AC-7`, `P-AC-10`, `P-AC-12`) Empty or failed retrieval never approves New. A new workspace requires an Authority response; after opening, valid New-only saves and exports remain available during an outage. Missing Browse capability leaves legacy review usable. Save decision and Export are clearly distinct, without derived application state. In-workspace saved-decision inspection is deferred to backlog R34.
- `PH3-AC-5` (from `P-AC-2`, `P-AC-9`, `P-AC-11`) Browser storage restores scoped focus, mode, filters, sort, queries, and unsaved decision drafts. Another row or project never inherits a draft or confirmed selection. Text entry and composition do not trigger bare-letter decision shortcuts; scheduled and out-of-order requests cannot replace current results.
- `PH3-AC-6` (from `P-AC-6`, `P-AC-8`) Before a save, the workspace compares each affected key's saved decision with the decision state it loaded, and asks for confirmation when a draft would replace a decision that changed since load; every staged decision survives that warning. A key whose decision the batch does not touch never warns. The comparison is client-side and advisory: no catalog precondition or request field is added, so a decision changed between the comparison and the write is still replaced on a last-writer-wins basis, which backlog item R33 closes. A save is never retried automatically.

**Validation Milestones**

- `VM-7` Keyboard and labelled-control checks complete ten rows, including skips, batch success, batch failure, draft retention, and affected-row updates (`PH3-AC-1`).
- `VM-8` Search, exact-ID, complete-list filtering/sorting, wrong-type IDs, literal wildcard characters, unsupported features, remote failures, and out-of-order responses produce the expected results and states (`PH3-AC-2`, `PH3-AC-3`).
- `VM-9` Resume and scope checks use two controlled projects with the same entity, target field, and business key: stage a draft and select a target in A, open B and confirm neither carries over, then return to A, reload, and confirm A's draft remains. For follow-up runs, reuse pass evidence for unchanged scenarios and check only changed or unverified behavior in one prepared browser session. Text composition, missing-extension, cold-start and already-open outage, and Save/Export checks also preserve the stated behavior (`PH3-AC-4`, `PH3-AC-5`).
- `VM-10` A changed decision for a key in the batch produces a warning with the reviewer's drafts intact, an unrelated concurrent decision produces none, a decision changed after the comparison is replaced without a warning as recorded in R33, and no save retries automatically (`PH3-AC-6`).

**Task-Plan Handoff**

- Source criteria: `P-AC-1`–`P-AC-5`, `P-AC-7`–`P-AC-12`.
- Use the approved 300 ms initial typeahead debounce, immediate Enter submission, explicit decision shortcuts, and versioned browser storage. Never restore a target result as a confirmed selection or persist full target collections as fresh.
- The batch decision endpoint and error shapes come from [the Phase 2 frozen contract](./RECONCILIATION_SEARCH_AND_BROWSE_PHASE_2_CONTRACT.md); Phase 3 consumes them without redesigning the save path. The browser draft format and the advisory pre-save comparison against loaded decisions are Phase 3 decisions. Do not add a catalog precondition, an expected-state request field, or per-row version storage; server-enforced per-row expected state on every decision writer is deferred to [backlog R33](../RECONCILIATION_IMPROVEMENTS_BACKLOG.md).
- Phase 1 retrieval outputs and Phase 2 save and export outputs are prerequisites; the save-contract decisions are already frozen, and no additional workspace design is implied by this plan.

**Readiness**

Requires completed Phase 1 and Phase 2 outputs before an implementation task plan.

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

**Environment**

The pilot environment is named `pilot-recon-2026-11-20`. It pairs the Authority Service at commit `1f3f1b8` with Shape Shifter at commit `7340510f`, both built from published refs and pinned by image tag, against `sead_pilot_recon`, a 2026-11-20 snapshot of `sead_staging` reached through a read-only role. All five capabilities are enabled for `feature_type` and `country` in the pilot's mounted Authority configuration only; the shipped configuration keeps every flag `false`. The pair, ports, and startup command are recorded in [the Phase 4 task plan](./RECONCILIATION_SEARCH_AND_BROWSE_PHASE_4_TASK_PLAN.md#pilot-environment).

The [Phase 4 baseline](./RECONCILIATION_SEARCH_AND_BROWSE_PHASE_4_BASELINE.md) records complete per-type Search and Browse timings at loopback and at approximately 100 ms and 200 ms RTT, the VM-12 decision and request measurements, and the per-capability pilot decisions. Both list limits were exercised and restored; neither list was partially returned.

**Capability Decisions (pilot only)**

| Capability | `feature_type` | `country` | Reason |
| --- | --- | --- | --- |
| `search_supported` | Advertise | Advertise | Search p95 stayed within budget at tested RTTs; browser Search passed (Phase 4 `V-1`, `V-8`). |
| `identifier_search_supported` | Advertise | Advertise | Exact-ID browser checks passed for both types (Phase 4 `V-8`). |
| `browse_supported` | Advertise | Advertise | Complete lists, limit errors, filtering, sorting, and delayed timings passed (Phase 4 `V-5`–`V-8`). |
| `details_supported` | Advertise | Advertise | Read-only URI detail lookups returned the expected records; the [Phase 1 task plan](./RECONCILIATION_SEARCH_AND_BROWSE_PHASE_1_TASK_PLAN.md) covers URI and numeric details. |
| `export_verification_supported` | Advertise | Advertise | Valid IDs verified, and unknown IDs blocked export without a sidecar write (Phase 4 `V-7`, `V-10`). |

**Outputs**

- Recorded pilot results and initial timing/request baseline.
- Independently advertised capabilities for each type that passes its checks; failures remain unadvertised.

**Delivery**

Use [the Phase 4 task plan](./RECONCILIATION_SEARCH_AND_BROWSE_PHASE_4_TASK_PLAN.md) and its [baseline record](./RECONCILIATION_SEARCH_AND_BROWSE_PHASE_4_BASELINE.md). They record the environment, the measurement methods, the per-type checks, and the advertisement decision.

**Acceptance Criteria**

- `PH4-AC-1` (from `P-AC-3`–`P-AC-5`, `P-AC-10`, `P-AC-13`) Each advertised `feature_type` or `country` capability passes its own paired integration and keyboard/browser checks against the selected service pair. Search, exact-ID, Browse, and export readiness remain independent; one unready type does not block a passing type.
- `PH4-AC-2` (from `P-AC-1`, `P-AC-2`, `P-AC-6`–`P-AC-9`, `P-AC-11`–`P-AC-13`) The pilot covers first-time review, atomic and conflicting saves, resume, outage behavior, real exported IDs and New approvals, and unchanged source identity. Retrieval produces no target or SIMS writes.
- `PH4-AC-3` (from `P-AC-13`) The named environment records search/browse median and 95th-percentile times, time and interactions per decision and per New decision, request counts, and preview/normalization invocations as the initial baseline, without claiming improvement over the old workflow.

**Validation Milestones**

- `VM-11` Per-type contract, live projection, limit, latency, verification, and browser results support each advertised capability; failed checks leave only the affected type or capability unadvertised (`PH4-AC-1`).
- `VM-12` A paired end-to-end run includes 100 source rows with 90 intentionally New, compound keys, duplicate labels, source changes, conflicts, outages, exported IDs, normalization, and no-write checks (`PH4-AC-2`).
- `VM-13` The baseline identifies the service pair, environment, fixture, measurement method, and all required timing and request measurements (`PH4-AC-3`).

**Task-Plan Handoff**

- Source criteria: `P-AC-1`–`P-AC-13`. Use the proposal's validation cases and the per-type gates rather than treating successful catalog saves as proof of target existence.
- The environment is named and the paired images are selected; both blocking decisions are settled.
- The [baseline record](./RECONCILIATION_SEARCH_AND_BROWSE_PHASE_4_BASELINE.md) lists the pilot-only decision and evidence for each capability and type. The shipped Authority Service flags remain false.

**Readiness**

The pilot checks and baseline are complete for `pilot-recon-2026-11-20`. Advertise all five capabilities for `feature_type` and `country` in this isolated pilot only. This decision does not authorize general release or change the shipped Authority Service configuration.

## Cross-Phase Rules

- Freeze each contract before planning its implementation; preserve the proposal's fixed semantics rather than replacing them with server-side review sessions or per-row versions.
- Keep capability advertisement opt-in and type-specific. Exercise new capabilities in a controlled configuration until the paired checks pass.
- Serialize catalog writes with the project lock, and add stale-view detection only with the Phase 3 workspace that holds long-lived views. Keep that detection an advisory pre-save warning until backlog R33 adds per-row expected state to the writes. Require verification before exporting accepted links, including existing `site` links; never use an outage fallback for them.
- Save stores catalog decisions; only explicit export updates the sidecar. Retrieval and review do not allocate target IDs or alter SIMS state.
- Do not silently modify links exported unverified by earlier versions. A separate policy is required before recovery or re-export work for those entries.

## Validation Strategy

Use service contract and fixture checks first, then Shape Shifter atomic-write and export regressions, followed by browser interaction and paired integration checks. Validate each advertised capability against its own type and the selected deployment pair. Record failures and keep the affected capability unadvertised; do not defer identity, atomicity, or export verification to a later rollout.
