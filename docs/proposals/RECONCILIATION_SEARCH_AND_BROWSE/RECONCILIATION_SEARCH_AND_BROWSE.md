# Search and Browse Target Records During Reconciliation

## Status

- **Proposed feature — draft for review**, updated 2026-11-18 against both repositories’ `dev` branches. No implementation approval is implied.
- **Scope:** One persistent record-selection workspace in Shape Shifter, supported by read-only search, browsing, and record metadata in `sead_authority_service`.
- **Goal:** Let reviewers find an existing record or deliberately mark a row New without first running batch matching, opening repeated dialogs, or reloading the entity after each decision.
- **Document home:** Shape Shifter, `docs/proposals/RECONCILIATION_SEARCH_AND_BROWSE/RECONCILIATION_SEARCH_AND_BROWSE.md`. This document owns the cross-service design; Authority Service work should reference it rather than duplicate the proposal.

Related: [improvement backlog](../RECONCILIATION_IMPROVEMENTS_BACKLOG.md), [concept sketch](https://chatgpt.com/library?file_id=libfile_71ee763abda8819188947370f8458d20&account_id=fa24b0c0-e21b-4786-a140-f1fd02ea3374), [reconciliation MVP](../done/RECONCILIATION_MVP/RECONCILIATION_MVP.md), and [manifest-driven reconciliation](../done/MANIFEST_DRIVEN_RECONCILIATION_INPUTS/MANIFEST_DRIVEN_RECONCILIATION_INPUTS.md). The sketch illustrates the workflow; individual labels and counts are not a fixed UI contract.

## Summary

Add **Search** and **Browse** tabs to a persistent review pane beside the source-row queue. Search accepts the reviewer's own text and optional matching context. Browse lists all eligible records of a supported type, with interactive text filters, declared field filters, sorting, and paging. Both select the same target-record identifiers and save through the same explicit decision flow.

Shape Shifter calls the Authority Service through its backend. Use OpenRefine reconciliation queries for ranked text search, optional entity suggestions for autocomplete, and an additive Authority Service API for complete browsing and structured record details. Shape Shifter does not query target database tables directly.

The proposal absorbs R21 and R26–R31, plus the shared saved-row update in R2 and review entry in R24. It includes the minimum queue, navigation, notes, resume, and unapplied-state behaviour needed by this workspace. The backlog relationship table below identifies the remaining scope of related items.

## Problem

Candidate review is a poor starting point when most source rows describe new records. Reviewers need a quick way to check existing data, choose New when appropriate, and continue. Abbreviations and labels in another language also make the source label unsuitable as a search term: the reviewer may need to replace `Sthlm` with `Stockholm`, or supply an English term for a Swedish label.

For classifiers, reviewers may recognize a value more easily than they can name it. A complete list of tens, hundreds, or a few thousand values can be useful when filtered and sorted interactively. A short ranked candidate list does not establish which values exist or whether the whole vocabulary has been searched.

Separate dialogs, mandatory prior matching, and entity-wide reloads make these activities slow. Direct database access would also create a second place to maintain target schema knowledge and identifier rules.

## Scope

- Shape Shifter: persistent pane, Search/Browse modes, source-row context, basic Needs review queue, keyboard operation, inline notes, explicit accept/New/skip actions, and row updates after confirmed saves.
- Backend support for validated source-row snapshots and first-time decisions without batch matching.
- Authority Service: additive selection capabilities, interactive error reporting, per-type browse configuration, complete listing, declared filters/sorts, structured record details, and stable identifiers shared with reconciliation. Reuse the implemented manifest and per-query limit support; extend existing candidate verification to the pilot types.
- Basic resume state and bounded recent-query history; minimal truthful indication that decisions await export.
- Cross-service compatibility and end-to-end validation.
- Initial delivery for **`feature_type` and `country`**. Enable other types only when their search, browse, identifier, and export contracts pass the same checks. Both types have supported reconciliation registrations on `dev`, but neither has export verification there. Pilot delivery includes that missing support; live data availability and latency remain unverified.

## Non-Goals

- Automatic acceptance, automatic New decisions, automatic translation, or learning aliases from operator queries.
- Creating target records, allocating IDs, or making SIMS calls while searching, browsing, or recording a review decision.
- Changing explicit export, offline normalization, manual-link precedence, or Core foreign-key identity semantics.
- Bulk decisions, batch matching progress/caching, complete audit history, undo, or rollback of exported links.
- Universal database exploration, arbitrary SQL/columns/joins, advanced wildcard syntax, or a mandatory taxonomy tree browser.
- Redesigning all reconciliation configuration or implementing the whole improvement backlog.

## Current Behavior

Source inspection on 2026-11-18 used Shape Shifter `dev` at [c7c95c4](https://github.com/humlab-sead/sead_shape_shifter/commit/c7c95c4d0e821ad20bc2241d86f2d01ecd81241c) and Authority Service `dev` at [5e19232](https://github.com/humlab-sead/sead_authority_service/commit/5e1923281d33419fb1d7379f48f4458f16e1783d). Links below identify those snapshots; a branch name alone is not a deployment guarantee.

| Observed behaviour on `dev` | Consequence for this proposal |
|---|---|
| Shape Shifter’s [alternative-search dialog](https://github.com/humlab-sead/sead_shape_shifter/blob/c7c95c4d0e821ad20bc2241d86f2d01ecd81241c/frontend/src/components/reconciliation/AlternativeSearchDialog.vue) debounces at 400 ms and displays request errors. Its [backend](https://github.com/humlab-sead/sead_shape_shifter/blob/c7c95c4d0e821ad20bc2241d86f2d01ecd81241c/backend/app/api/v1/endpoints/reconciliation.py) still uses suggestions with text, saved type, and ten results, without row-property context. It has no response-version guard or selection invalidation on changed text. | Reuse existing error display and adapters, but replace the dialog loop with one persistent, race-safe Search/Browse workspace. |
| The [decision service](https://github.com/humlab-sead/sead_shape_shifter/blob/c7c95c4d0e821ad20bc2241d86f2d01ecd81241c/backend/app/services/reconciliation/service.py) still rejects a key absent from the catalog with “run matching first”; the [store](https://github.com/humlab-sead/sead_shape_shifter/blob/c7c95c4d0e821ad20bc2241d86f2d01ecd81241c/frontend/src/stores/reconciliation.ts) reloads catalog and preview after saves. Preview requests have version guards, but saves use shared loading state. | First-time decisions, reusable validated rows, row-local saves, and R2 remain new work. |
| The [review view](https://github.com/humlab-sead/sead_shape_shifter/blob/c7c95c4d0e821ad20bc2241d86f2d01ecd81241c/frontend/src/components/reconciliation/ReconciliationView.vue) loads preview when its review tab opens, independently of matching eligibility. However, the [specification-list action](https://github.com/humlab-sead/sead_shape_shifter/blob/c7c95c4d0e821ad20bc2241d86f2d01ecd81241c/frontend/src/components/reconciliation/SpecificationsList.vue) is labelled Find candidates and disabled by matching compatibility. | R24 is partly supported internally; make review entry explicit and available independently in navigation. |
| Authority’s [metadata builder](https://github.com/humlab-sead/sead_authority_service/blob/5e1923281d33419fb1d7379f48f4458f16e1783d/src/metadata.py) and [manifest DTO](https://github.com/humlab-sead/sead_authority_service/blob/5e1923281d33419fb1d7379f48f4458f16e1783d/src/api/model.py) expose and validate `reconciliation.supportedTypes`. Existing [HTTP route tests](https://github.com/humlab-sead/sead_authority_service/blob/5e1923281d33419fb1d7379f48f4458f16e1783d/tests/api/test_router.py) assert the serialized field. | The earlier missing-manifest finding is resolved in source. Preserve this contract and add only the selection-capability extension. |
| Authority [reconciliation](https://github.com/humlab-sead/sead_authority_service/blob/5e1923281d33419fb1d7379f48f4458f16e1783d/src/reconcile.py) now forwards each requested limit, falling back to the configured default. `ReconQuery` accepts 1–500; [tests](https://github.com/humlab-sead/sead_authority_service/blob/5e1923281d33419fb1d7379f48f4458f16e1783d/tests/test_reconcile.py) cover explicit limits and fallback. | The service limit fix is existing behaviour. Remaining work is the interactive request/capability contract and end-to-end checks. |
| [Configured classifiers](https://github.com/humlab-sead/sead_authority_service/blob/5e1923281d33419fb1d7379f48f4458f16e1783d/src/strategies/configured_classifier.py), including `feature_type`, have supported registrations, generated fuzzy/details queries, and normalized label-prefix suggestions. The base strategy still falls back to fuzzy matching for suggestions on other types. [Suggestions](https://github.com/humlab-sead/sead_authority_service/blob/5e1923281d33419fb1d7379f48f4458f16e1783d/src/suggest.py) require two characters and swallow retrieval errors; the HTTP route fixes the limit at ten. | Prefix autocomplete is already available for classifiers; it is neither full-text search nor exhaustive browsing. Preserve its semantics and report failures truthfully on the interactive path. |
| Authority [repositories](https://github.com/humlab-sead/sead_authority_service/blob/5e1923281d33419fb1d7379f48f4458f16e1783d/src/strategies/query.py) support fuzzy/prefix retrieval and per-ID details; the [router](https://github.com/humlab-sead/sead_authority_service/blob/5e1923281d33419fb1d7379f48f4458f16e1783d/src/api/router.py) has no complete record-list or structured record-details API. Base details lookup turns invalid IDs/database errors into `None`. | Complete browsing and structured details remain additive work, including explicit error/not-found distinctions. |
| `POST /reconcile/verify-candidates` and `GET /reconcile/readiness` exist, but their [implementation](https://github.com/humlab-sead/sead_authority_service/blob/5e1923281d33419fb1d7379f48f4458f16e1783d/src/api/candidate_verification.py) supports only policy-enabled `site`. Shape Shifter’s [client](https://github.com/humlab-sead/sead_shape_shifter/blob/c7c95c4d0e821ad20bc2241d86f2d01ecd81241c/backend/app/clients/reconciliation_client.py) rejects `unsupported_type` as a protocol failure. | The route is present; the pilot gap is type coverage. With this source pair, accepted `feature_type`/`country` decisions cannot export successfully while verification is available. Extend verification before pilot acceptance/export is enabled. |
| The [country specification](https://github.com/humlab-sead/sead_authority_service/blob/5e1923281d33419fb1d7379f48f4458f16e1783d/src/resources/country.yml) searches `authority.fuzzy_location(..., 1)` and uses `location_id`; its details query selects from `authority.location` by ID without that type restriction. `country` has a [supported registration](https://github.com/humlab-sead/sead_authority_service/blob/5e1923281d33419fb1d7379f48f4458f16e1783d/src/strategies/country.py), separate from configured classifiers. | The country adapter must enforce the same country subset in list, details, and verification. It must preserve country URIs with numeric location IDs rather than invent a country table or `country_id`. |

Existing source tests were inspected, not executed. Deployed compatibility, actual classifier sizes, and latency remain unverified. The proposal extends the `dev` implementation; it does not repeat resolved manifest/limit work or replace the existing export protocol.

## Proposed Design

### 1. One pane, two ways to find a record

The left queue retains the source label, business key, and review state. The right pane stays open while the active source row changes. It shows read-only source context, a **Search / Browse** switch, target results, optional notes, and persistent decision controls.

| Action | Behaviour |
|---|---|
| Search | Type an expansion, translated term, name, or identifier. The source label is offered as a convenience, not forced into the query. Enter submits immediately; optional typeahead is debounced. |
| Browse | Open a complete type-specific list with an empty filter. Narrow it by literal text and supported field filters; sort and inspect definitions. A browse filter is independent of the ranked search query. |
| Accept selected & next | Save an accepted decision for the active business key and selected target URI; advance after success. |
| Mark New & next | Explicitly save a New/local-only decision. Explain that this approves later new-record handling, not immediate creation. Search is optional. |
| Skip for now | Advance without a decision; retain the row in Needs review and offer return to deferred rows. |

An empty result never marks New. Search failure, no results, loading, and not-yet-searched are distinct states. Choosing New remains available during Authority Service outages when the source-row snapshot is valid.

Switching tabs preserves the active source row and each tab's filters, but clears the selected target unless the same record remains present in the current results. On another source row, clear target selection and old responses; show only that row's own query and note drafts. Retain unsaved work per row or warn before discarding it. Browse filters and sort may persist for the specification. No result is pre-accepted or automatically carried to another row.

Use ordinary keyboard navigation within results. Enter in the text field searches; explicit modified shortcuts perform decisions. Bare-letter grid shortcuts are inactive during text entry, including composition input. Advance follows the visible queue and occurs only after a confirmed save; failures preserve the query, selection, and notes.

### 2. Responsibility and protocol

| Component | Owns |
|---|---|
| Shape Shifter frontend | Source queue, focus, request state, result selection, keyboard operation, and draft/resume state. |
| Shape Shifter backend | Project authorization, saved specification/type resolution, validated review snapshots, Authority calls, record adaptation, decision persistence, and export status. |
| Authority Service | Served target-record set, per-type lookup/list/details, supported filters and sorts, target identifiers, capability metadata, and target database access. |
| SIMS | Its existing downstream identity responsibilities. This workspace makes no resolve, bind, or allocation calls. |

Search uses a single-query OpenRefine `POST /reconcile` request with operator text, configured type, supported property hints, and an effective result limit. Entity suggest is optional for autocomplete, never a required extra request before submitting a search. Keep the type fixed to the specification. Clearly distinguish supported property hints used for ranking from browse filters that strictly restrict results. The current configured classifiers declare no reconciliation properties; do not offer context controls for them unless service support is added. Resolve advertised property IDs through the existing manifest validation.

Only advertise interactive search for bounded, read-only retrieval that meets the agreed response budget. Do not run LLM/RAG reasoning on each keystroke. Types whose existing strategy is too expensive remain unsupported for interactive search until a suitable lookup is supplied; batch matching behaviour stays unchanged.

Browsing and structured details use a versioned additive Authority API. They are not represented as empty fuzzy searches. The OpenRefine 0.2 [suggest contract](https://www.w3.org/community/reports/reconciliation/CG-FINAL-specs-0.2-20230410/#suggest-queries) provides a cursor for suggestions, but does not define this proposal's exhaustive listing, arbitrary field sorting, or browse-filter semantics.

All retrieval is read-only. It neither writes proposals for every result nor changes the mapping sidecar. Browsed records have no invented confidence or `match=true` flag; a reviewer decision is required regardless of how the record was found.

### 3. Capabilities and record-list contract

The Authority Service owns the following **proposed** extension contract, version 1. Paths are recommendations for this proposal, not descriptions of existing routes.

| Interface | Contract |
|---|---|
| `GET /reconcile` | Preserve standard fields and the implemented, explicitly serialized `reconciliation.supportedTypes` extension. Add optional `reconciliation.record_selection` metadata with `version: 1` and a same-service relative `types_path`. |
| `GET /records/types` | Return per-type `search_supported`, `browse_supported`, display columns, supported text fields, typed filters/operators, allowed sorts, default sort, result/page limits, and identifier metadata, including whether existing candidate verification supports the type. Keep matching, browsing, and export-verification support distinct. Absence of a capability means unsupported. |
| `GET /records/{type}` | Accept optional literal `q`, declared filter values, `sort`, `direction`, `page_size`, and opaque `cursor`. Empty `q` lists records. Default page size 50, maximum 200. Reject unsupported fields/operators rather than ignoring them. |
| `GET /records/{type}/details?id=...` | Accept the complete target URI and return a structured record of that exact type, or an explicit not-found/invalid-ID outcome. Do not return executable HTML as the structured details contract. |

Search, browse, and details resolve to the same target-record set and IDs. A record contains `id` (the complete reconciliation URI), `target_id` (the positive numeric target ID supported by the current decision model), `type`, `name`, optional `description`, and declared display `fields`. Names are not identifiers. A shared Authority formatter/parser supplies these values; the Vue pane does not introduce another URI parser. The Shape Shifter backend validates the configured identifier space, exact saved type, and positive numeric ID when adapting and accepting a record. For pilot acceptance, confirm membership through the type-restricted structured details lookup; New decisions do not require that remote call. Its current trailing-number extractor alone does not establish URI/type validity; shared validation must cover legacy and new decision callers. For other types, fetch structured details before enabling acceptance when the standard result lacks the numeric ID or required fields. Every details failure remains visible and blocks the affected acceptance.

List responses contain `items`, `page_size`, `next_cursor`, `has_more`, `total` (exact count after filters), and a declared `completeness` value. Paged listings report `page`; a future explicitly supported complete-set response may report `complete`. Search results remain labelled limited/ranked suggestions, with no claim that a search miss proves absence.

Browse `q` is case-insensitive literal substring matching over the declared text fields, combined with field filters using AND. `%`, `_`, `*`, and similar characters are literal input, not implicit SQL or wildcard syntax. Labels, descriptions, and codes are searchable only where actually provided; aliases are searchable only if supplied and advertised. Default order is label ascending with numeric target ID as a unique tie-breaker; define null placement and collation consistently in server and client responses. Filter/sort changes reset paging.

The first release uses server-side filtering, sorting, and cursor paging for every browsable type. Sorting applies before paging to the entire eligible set. The cursor binds type, filters, sort, and last sort values; reject incompatible or expired cursors. With an unchanged dataset, every eligible record appears exactly once when traversing pages. Lists are live between requests, not transaction snapshots: expose a dataset version when one is available and reset on its change; otherwise disclose that concurrent target edits require refresh. Acceptance and export retain their normal checks.

This deliberately defers an automatic client/server threshold. Complete-set caching is a later optimization, enabled only by an explicit complete response and bounded payload. Filtering a cached first page must never look like filtering the entire classifier.

### 4. Authority Service implementation responsibilities

Add list/details capabilities to the existing registered type and repository system. Browse support is opt-in per type; being present in `config/entities.yml` or having a fuzzy strategy does not by itself make a type browsable. A type declares its list source, projected fields, filters, sorts, and details lookup in service-owned configuration. Use existing connection/configuration facilities and generated schema conventions. Build configured-classifier projections from the existing `table_specs` and generated views; retain their static registry and startup validation. Do not introduce a parallel classifier registry or hand-edit generated SQL. Use a separate adapter for non-classifier types such as `country`.

Only declared identifiers are used in SQL construction; values are parameterized. List, details, search, and export verification must agree about the exposed record set. The new API exposes intended record fields, not arbitrary underlying tables. Unsupported types return a capability error; database timeouts/unavailability return failures, not empty lists. Expose swallowed suggestion/details errors on the interactive path. Preserve implemented per-query reconciliation limits and default fallback; enforce the declared interactive cap without changing legacy queries. Autocomplete may keep a bounded fixed limit if advertised. Do not relabel the existing classifier prefix lookup as substring search.

For `feature_type` and `country`, provide a complete browse projection with at least ID and label, plus description where available. `feature_type` reuses its configured classifier view and `feature_type_id`; `country` uses the country subset of location records, `location_id`, and the existing `/country/{location_id}` URI shape. Enforce country membership in list, structured details, and verification, including a negative fixture for a non-country location ID.

Extend `POST /reconcile/verify-candidates` to both pilots using the same read-only, type-specific existence checks as list/details. Preserve ordered batches, echoed type/URI, existing outcomes, and the positive numeric result field `aggregate_id` expected by Shape Shifter. For these lookups that field carries the target primary key; its legacy name does not require a SIMS aggregate or binding operation. Pilot verification must not depend on SIMS `bind_existing` policy. Keep existing site verification unchanged. `unsupported_type`, malformed replies, and wrong-type IDs remain failures; only genuine service/database unavailability follows the existing unverified-export path. Do not enable pilot acceptance/export based solely on `supportedTypes` or a successful list request. Extend `/reconcile/readiness` only if the new capability contract uses it for pilot readiness; its current site-only coverage is not a universal matching prerequisite.

Synthetic fixtures cover larger lists; do not claim that production classifiers contain thousands of values without measuring them. Other strategies, especially external or LLM-backed ones, can continue to offer their existing batch behaviour without browse support.

### 5. First-time decisions and fast saves in Shape Shifter

Opening a review creates a server-owned snapshot of the authorized specification's normalized source rows, their valid unique encoded business keys, relevant source values, and saved decision versions. Reuse the established source-resolution rules, including another-entity or SQL search sources. No remote matching is required. The snapshot is scoped to principal, project resource, entity, and field, and supplies opaque row tokens; it is bounded, expires, and is invalidated by project/specification changes.

Add a review-decision operation accepting a row token, expected decision version, accepted/rejected/local-only status, selected URI/target ID where relevant, and optional notes. Its final route name and schema are frozen before implementation planning. Validate the token against the server snapshot; do not accept an arbitrary client key or label. Under the project lock, compare the current catalog decision with the expected version, create or update only that key, and return the saved decision and new version. Conflicts are explicit and leave the caller's work intact. Use the shared candidate URI/type/ID validation described above, including for legacy decisions, and preserve export verification. Do not weaken checks for browsed selections.

The snapshot eliminates entity normalization on every save. Source files/configuration and tracked source revisions invalidate it. Unversioned external SQL data is pinned as observed when review opened; changes outside Shape Shifter are not detectable without reloading. Show the snapshot age and Refresh action, and require a fresh snapshot after expiration or an observed input change. This defines what “current source row” means without claiming continuous external-data validation. R22's broader reassessment of historical decisions remains separate.

The decision operation accepts New before any candidate search and without contacting the Authority Service. Invalid/duplicate keys cannot receive a decision. Marking New never clears a conflicting existing public ID or protected manual link silently; use the established export/ingester conflict rules and show the resulting block.

On success, patch the row and affected queue counts from the response. Do not reload the full preview or block unrelated rows. On failure, leave the last confirmed decision intact and preserve drafts. Legacy decision routes remain supported and share validation; existing callers are not required to supply the new snapshot token.

Catalog decisions still require explicit export. Show a backend-derived per-specification application state (`unapplied`, `in_sync`, or `unknown`) by comparing saved decisions with owned sidecar links and New approvals; indicate pending verification separately. Do not infer success from browser drafts or clear status merely because export returned HTTP success. Reuse the existing current-ID provenance and verification indicators and export outcomes. The new application state compares saved decisions with sidecar contents; existing verification icons alone do not provide it. Full counts, conflict dashboards, and retained export reports remain R9/R25 work.

### 6. Request state, persistence, and compatibility

- Debounce typeahead initially at 300 ms; Enter submits immediately and cancels the scheduled duplicate. Ignore unfinished composition input. A type may require explicit submit if it does not advertise interactive lookup.
- Cancel superseded requests where possible and always ignore responses whose project/specification, row, mode, query, or context no longer matches. Clear obsolete target selection immediately. Failed search/browse/details requests remain distinguishable from successful empty results.
- Retain active specification, mode, focused source key, tab-specific filter/sort, and that row's query draft. Keep a maximum of 20 recent query texts per project/specification in browser storage, with Clear history and versioned draft format. Never persist full target collections as if fresh, or restore an old result as a confirmed selection.
- Load optional capabilities independently of legacy manifest parsing. A missing browse extension hides Browse and leaves existing search/candidate review usable. Invalid extension metadata disables the affected extension with an explanation. Remote unavailability does not prevent inspection of saved decisions or locally valid New decisions.
- Model new metadata explicitly in the Authority response DTO and the Shape Shifter adapter. Test actual manifest HTTP output, including required existing extensions, rather than only a metadata-builder dictionary. Service paths must resolve within the configured Authority service, never to caller-selected hosts.
- Keep old reconciliation routes and catalogs readable. Browsing configuration lives in the Authority Service; projects do not acquire database table/column settings. Draft UI state is not a new catalog status or authorization to allocate.

### 7. Backlog ownership and replacement

The following is a proposed disposition on approval. It does not mark issues done or change the backlog automatically. “Absorb” means delivery and acceptance move under this proposal; “partial” leaves the named remainder independent.

| Backlog item | Disposition | Relationship |
|---|---|---|
| R1 Top candidate in grid | Independent | Suggested-candidate speed improvement; no prerequisite for Search/Browse. |
| R2 Saved-row patch | Absorb | Shared save/update mechanism for pane and existing grid. |
| R3 Keyboard review | Partial | Search/Browse focus and decision loop included; broader grid shortcuts remain a follow-up using the same navigation actions. |
| R4 Undo | Independent | Can consume versioned saves later; does not block this proposal. |
| R5 Needs review queue | Partial | Basic membership/counts/navigation included; score sorting, ambiguity categories, and threshold views remain. Remove R1 as a prerequisite for basic queue access. |
| R6 Trusted manual-link picker | Dependent follow-up | Reuse the new picker; immediate trusted sidecar writes remain a separate labelled action and are not introduced here. |
| R7 Notes/reasons | Partial | Optional inline notes included; presets and editing notes across every decision surface remain. |
| R8 Remember context | Partial | Workspace mode, query/filter/sort and focused row included; wider project/grid state restoration remains. |
| R9 Unapplied changes | Partial | Minimal truthful application state and separate verification indication included; detailed counts and full diagnostics remain. |
| R10 Pre-export check | Independent | Preserve its future reuse of export rules; no extra confirmation added to ordinary decisions here. |
| R11 Headers | Independent | Cosmetic grid change, unrelated to the service contract. |
| R12 Query deduplication | Independent | Batch optimization; manual lookup does not wait for it. |
| R13 Matching fingerprints | Independent | Batch candidate reuse; transient review snapshots are not its persisted historical fingerprint model. |
| R14 Batch progress/cancel | Independent | Long-running matching work; interactive request cancellation is included here without adopting the batch job system. |
| R15 Candidate limit | Partial; service forwarding exists | Preserve the implemented per-query limit/default handling. Interactive caps and end-to-end checks belong here; per-specification batch candidate-count configuration remains. |
| R16 Batch decision endpoint | Independent | Single-row versioned saves included; batch API can reuse them later. |
| R17 Bulk actions | Independent | Not required for a fast one-row search/browse loop. |
| R18 Equivalent-query groups | Independent | No propagation of decisions from shared labels or reused query text. |
| R19 Partial/wildcard matching | Partial; classifier prefix lookup exists | Reuse existing prefix autocomplete and add literal substring Browse filtering. Reassess failed-search fixtures against `dev`; fuzzy match-kind ranking and wildcard syntax remain separate. |
| R20 Multilingual aliases | Follow-up extension | Operator-entered translated queries work now; curated aliases and automatic multilingual retrieval remain later service work. |
| R21 Persistent pane | Absorb | This proposal becomes the pane's design owner; legacy candidate review uses the same component/actions. |
| R22 Changed historical inputs | Independent | Must later reuse compatible snapshot/input descriptions, but does not gate first-time decisions or basic resume. |
| R23 Skip/resume | Absorb for this workspace | No new terminal decision status; shared navigation can be reused by grid review. |
| R24 Open saved review | Absorb remaining navigation work | Preserve the review tab’s independent preview loading; remove compatibility gating from review entry and give it a distinct Open/Resume review label. |
| R25 Retained export results | Independent | Reuse selection/navigation actions for repair later; no full export-result redesign here. |
| R26 Search-first workspace | Replace standalone design | Covered by this proposal's Search/Browse pane. |
| R27 Responsive search | Absorb | One request-state implementation also serves browsing and details. |
| R28 Keyboard search/decide/advance | Absorb | Included end to end, with explicit New and failure recovery. |
| R29 Independent text/context | Absorb | Standard search plus declared browse filters; no implicit automatic translation. |
| R30 First-time decisions | Absorb | Server snapshots, validated keys, concurrency checks, and no batch prerequisite. |
| R31 Search history | Absorb | Bounded row drafts and recent terms, independent of target aliases. |
| Browsing, discussed as R32 | New scope here | Not yet a numbered item in the supplied backlog. Do not create a competing standalone design; track service/UI work under this proposal. |

Existing tracking issues can remain separate delivery units linked to this proposal. Cross-service service-contract work needs an Authority Service issue; frontend and review-decision work belongs in Shape Shifter. No issue numbers or implementation owners have been assigned.

## Alternatives Considered

| Alternative | Assessment |
|---|---|
| Query SEAD directly from Shape Shifter | Rejected: duplicates target schema, access, and identifier knowledge in the editor backend. |
| Make every interaction a fuzzy reconciliation query | Rejected for browsing: ranked top-N results cannot promise complete enumeration or global sorting. |
| Use only an extended suggestion endpoint | Useful for autocomplete, but a dedicated list contract makes completeness, supported filters, totals, and paging explicit. |
| Fetch every classifier in full immediately | Deferred: it may be fast for small sets, but type size and row width are unmeasured. Start with one correct server-paged implementation; add explicit complete-set caching after measurement. |
| Require batch matching before every review | Rejected: it preserves the main bottleneck for mostly-new rows and unsuitable source labels. |
| Replace catalogs/export or write trusted manual links | Rejected: record selection should preserve existing human decisions, ownership, and export semantics. |

## Risks And Tradeoffs

- **Paired deployment and type coverage:** `dev` contains the required manifest and verification routes, but verification currently covers only `site`. Extend pilot coverage and test the exact deployed pair before enabling acceptance/export; a supported matching type is not proof of export support.
- **Live target data:** Cursor traversal is stable for unchanged data, not a database snapshot across concurrent edits. Refresh and final export checks remain necessary; versioned target datasets can improve this later.
- **Source freshness:** Review snapshots avoid per-save normalization but cannot detect changes in unversioned external sources immediately. Make snapshot age/refresh visible and reject known-invalidated snapshots.
- **Response time:** Some matching strategies can be expensive. Advertise interactive support only where bounded lookup is available, and measure the pilot before setting a latency promise.
- **Count/filter cost:** Exact filtered totals and substring search require suitable query plans. Keep type opt-in and payloads bounded; do not silently replace an expensive complete count with an inaccurate number.
- **Accidental New decisions:** Fast actions increase speed and mistakes. Use explicit labels and focus-scoped shortcuts, preserve failed work, and keep New distinct from a search miss. Undo remains separate work.

## Testing And Validation

Use API contract checks, paired integration tests with a disposable target database, and browser interaction checks. Extend the existing manifest HTTP, reconciliation-limit, classifier-prefix, and candidate-verification tests rather than treating those implementations as missing. The fixtures must include both pilot types, duplicate target labels with distinct IDs, compound source keys, missing/duplicate source keys, abbreviated/non-English source labels, and 100 source rows of which 90 are intentionally new. A generated 5,000-value classifier exercises paging/filtering/sorting without claiming that a live classifier has that size.

Demonstrate first-time decisions with no prior matching entries, both retrieval modes selecting the same URI, complete unfiltered traversal, filtered totals, stable ties, unsupported filter errors, remote failures, out-of-order responses, keyboard-only operation, stale snapshot/decision conflicts, and legacy-client compatibility. Include classifier prefix-versus-substring examples, malformed/wrong-type URIs with valid numeric suffixes, a non-country location ID, and ordered pilot verification responses. Assert that `unsupported_type` and malformed replies block export, while genuine unavailability retains the existing unverified behaviour. Re-run export/normalization to check actual IDs and New approvals, not just response counts; retrieval must leave SIMS and the target database unchanged.

Record search/browse median and 95th-percentile response times, time/interactions per decision and per New decision, request counts, and preview/normalization invocations. No decision save should trigger entity-wide normalization while its snapshot is valid. Establish the latency budget with the named pilot environment before accepting interactive capability for a type. No performance results or live UI tests have been run for this proposal.

## Acceptance Criteria

- **P-AC-1 — Entry and source identity:** Review opens without Find Candidates. Search text, browse filters, and selected target IDs never change source labels, ordered business keys, or Core `system_id` values.
- **P-AC-2 — Continuous review:** Ten consecutive rows can be searched/browsed, explicitly decided or skipped, and advanced in one pane using keyboard or labelled controls. Save failures preserve drafts and do not advance.
- **P-AC-3 — Search:** Expanded abbreviations and operator-translated labels find expected pilot records through the Authority API; declared context is applied with its advertised semantics; requested bounded result limits are honored.
- **P-AC-4 — Complete browse:** Each pilot type supports empty-filter listing, declared columns, literal text/field filtering, global sorting, exact filtered totals, and complete cursor traversal. A 5,000-row unchanged fixture has no missing/duplicate records, including tied labels.
- **P-AC-5 — Uniform targets:** Search, Browse, details, and export identify the same records. A browsed acceptance has the same URI, numeric target ID, verification requirements, and resulting normalized ID as an equivalent searched acceptance; browse rows do not invent confidence scores. Both pilots pass existing-protocol verification with ordered echoed IDs and matching numeric `aggregate_id`. Wrong identifier spaces/types and non-country location IDs cannot become accepted/exported country links; existing site checks still pass.
- **P-AC-6 — First-time saves:** A valid keyed row with no catalog entry can be accepted or marked New without prior matching. Invalid, duplicate, unauthorized, expired, or known-stale row tokens are rejected; conflicting catalog edits are not overwritten.
- **P-AC-7 — Explicit decisions:** Retrieval creates no catalog decision, sidecar change, target record, or SIMS state. Empty results and failed requests never approve New. A valid New save works during remote-service outage and still requires export before becoming an allocation approval.
- **P-AC-8 — Fast saved-row updates:** Valid-session saves patch only affected review state and perform no entity-wide preview/normalization; failures leave the last confirmed state intact. Expiration/change offers refresh instead of silently accepting an old snapshot.
- **P-AC-9 — Request correctness:** Stale/out-of-order responses cannot appear as current results or enable acceptance. Searching, empty, failed, and unsupported states are distinguishable; literal filter input cannot introduce SQL or wildcard semantics.
- **P-AC-10 — Capability and compatibility:** Actual HTTP manifests expose supported types and versioned selection capabilities without breaking standard OpenRefine fields. Missing/unsupported Browse leaves legacy review available; unadvertised types/filters/sorts are not used. The exact pilot service pair passes the existing manifest/limit checks and extended pilot export-verification checks. Matching support alone does not enable pilot acceptance/export; unsupported verification is never treated as unavailability.
- **P-AC-11 — Resume:** The workspace restores scoped mode/filter/sort/focused key and row query drafts; recent queries are bounded and clearable. Another row or project never inherits an accepted target selection or a decision from that history.
- **P-AC-12 — Export invariants:** Accepted and New decisions remain unapplied until explicit export; application state and verification are not conflated. Manual/unowned link protection, ownership cleanup, offline normalization, and downstream FK semantics remain unchanged.
- **P-AC-13 — Pilot validation:** Both pilot types and the mostly-new/large-list fixtures pass paired integration and keyboard/browser checks, with timing and request-count results recorded for a named environment and no retrieval-time writes.

## Planning Handoff

**Fixed if this proposal is approved:** One cross-service proposal and one shared pane/decision flow; OpenRefine ranked search plus an additive browse API; service-owned target data access; server-side paging first; opt-in per-type capabilities; `feature_type`/`country` pilot; explicit decisions; existing catalogs/export/SIMS responsibilities preserved. Absorbed backlog items must not acquire separate conflicting designs.

**Before service implementation planning:** Freeze the version-1 extension and record/list/details wire schemas, identifier rules, errors, and cursor consistency tests. Reuse the implemented supported-type manifest and query-limit handling. Freeze pilot verification support within the existing wire contract and enforce the country subset consistently. Verify the paired deployment and pilot data availability. Decide the search latency budget on the named environment. This document owns semantics; the Authority Service owns the implemented API/OpenAPI contract.

**Before review-save implementation planning:** Freeze the review-snapshot/row-token and decision-version contracts, bounded session lifetime and invalidation rules, and draft storage format. Preserve project authorization, project locks, single-worker deployment assumptions, and legacy decision compatibility. Do not add persistent historical-input schema as a hidden replacement for R13/R22.

**Before acceptance:** Cover P-AC-1–P-AC-13 across both repositories. Use the backlog table to split delivery issues, and record real output IDs plus no-write checks. Produce a separate phase plan after design review; this document is not an implementation checklist or phase plan.

## Open Questions

1. **Deployment readiness:** Which deployed images correspond to the inspected `dev` snapshots, and when will both pilots have read-only export verification? The manifest and verification routes are present in source; pilot type coverage is the known gap. Resolve and test before enabling pilot acceptance/export. Preserve the distinction between unsupported verification and genuine remote unavailability.
2. **Pilot data and latency:** Confirm the two pilot projections, representative row widths/counts, target database environment, and response-time budget before advertising interactive support. Expand pilot types only through an explicit follow-up decision.
3. **Review-session limits:** Choose idle/absolute expiration, memory bounds, and source-revision providers before backend implementation. External sources without revisions remain explicitly snapshot-based until refresh.
4. **Browse extensions:** Tree navigation and complete-set local caching may be useful later; neither blocks the first complete, filterable table browser.

## Final Recommendation

Approve the shared Search/Browse workspace and paired Authority Service extensions as one feature. Consolidate the absorbed backlog items under this proposal, retain the explicitly listed follow-ups, and validate the pilot against the real service pair before extending type coverage.
