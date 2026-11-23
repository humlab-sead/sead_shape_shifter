# Reconciliation Search and Browse: Phase 1 Task Plan

## Phase Summary

**Goal:** Add bounded, read-only record selection and verification for `feature_type` and `country` in Authority Service without changing legacy batch matching or `site` verification.

**Readiness:** Validated for implementation. [Phase 1 of the phase plan](./RECONCILIATION_SEARCH_AND_BROWSE_PHASE_PLAN.md#phase-1-authority-retrieval-and-verification) is ready and freezes the version 1 contract, initial limits, and controlled testing. The [approved proposal](./RECONCILIATION_SEARCH_AND_BROWSE.md) owns the cross-service design. This status does not mean that the new API or the deployed pair has passed validation.

**Dependencies:** Existing Authority strategy registrations, generated views and fuzzy functions, and the candidate verification protocol. Phase 2 consumes the pilot verification results; Phase 3 consumes discovery, search, Browse, and details. Phase 4 owns paired validation and general enablement.

1. [ ] `PH1-AC-1` (from `P-AC-3`, `P-AC-10`): The HTTP manifest retains standard OpenRefine fields and `reconciliation.supportedTypes`; versioned same-service discovery reports independent capabilities. Interactive queries honor the advertised cap without changing legacy limits.
2. [ ] `PH1-AC-2` (from `P-AC-4`, `P-AC-9`): An enabled list returns all projected items within both limits or an explicit too-large error with no items. Unsupported types and service failures are distinguishable from empty results.
3. [ ] `PH1-AC-3` (from `P-AC-3`, `P-AC-5`, `P-AC-10`): Search, exact lookup, list, details, and verification agree on the type-specific URI and positive numeric target ID. Country lookups exclude other locations. Verification preserves ordered echoes, numeric `aggregate_id`, and existing site behavior.
4. [ ] `PH1-AC-4` (from `P-AC-7`, `P-AC-13`): Retrieval and verification do not change target data or SIMS state. Pilot capabilities are not advertised for general use before their Phase 4 checks pass.

## Repository Findings

**Repository basis:** 2026-11-19, Shape Shifter `reconciliation-search-and-browse` at `5727bed8` and Authority Service `reconciliation-search-and-browse` at `5e19232`. Used the uncommitted Shape Shifter phase-plan edits supplied in the working tree; Authority was clean. Graphify identified the strategy and client entry points; current code and checked-in SQL supplied the contract and query details.

Paths in the work breakdown, validation commands, and deliverables are relative to the **Authority Service** repository (`../sead_authority_service` from the Shape Shifter root).

| Evidence | Finding | Planning implication |
|---|---|---|
| `main.py::startup`, `src/api/router.py::get_config_dependency`, `src/api/router.py::meta`, `src/metadata.py::get_reconciliation_metadata`, `src/api/model.py::ReconciliationDescriptor` | Both config setup paths validate the classifier registry. The HTTP manifest serializes a typed descriptor and computes `supportedTypes` from registration status. | Validate selection settings alongside existing startup checks. Add discovery to the DTO as well as the builder; do not make matcher support imply selection support. |
| `src/api/router.py::reconcile`, `src/api/model.py::ReconQuery`, `src/reconcile.py::reconcile_queries` | Unmarked requests accept JSON or form-encoded queries, default absent types to `site`, and forward explicit limits from 1 to 500 or the configured default. Ranked candidate URIs use `ReconciliationStrategy.as_candidate`. | Apply the stricter checks only to marked requests. Keep the existing batch dispatch and response format. |
| `config/entities.yml` (`feature_type`), `src/strategies/configured_classifier.py::ConfiguredClassifierStrategy`, `src/utility.py::build_classifier_specification`, `schema/generated/feature_type.sql` | `feature_type` is statically registered. `authority.feature_type` exposes `feature_type_id`, `label`, and `description`; classifier suggestions use normalized label prefixes and the strategy advertises no property hints. | Reuse the registered matcher and generated view. Keep `/suggest/entity` separate. |
| `src/strategies/country.py::CountryReconciliationStrategy`, `src/resources/country.yml`, `schema/generated/location.sql`, `schema/__deploy__.sql` | The country resource passes scalar `1` for the country subset, while both checked-in SQL artifacts declare `fuzzy_location(text, integer, integer[])`. The legacy details SQL is not country-scoped and selects a `description` absent from the checked-in `authority.location` view. | Use the array signature for marked country search and enforce `location_type_id = 1` for list and ID lookups. Do not copy the legacy details SQL or change unmarked country matching. |
| `src/strategies/query.py::BaseRepository`, `src/configuration/setup.py::get_connection` | `fetch_all` and `fetch_one` use the shared connection provider and propagate database errors. Legacy `get_details` catches database errors and returns `None`. Nested connection calls reuse the active transaction. | Use the lower-level fetch methods for new lookups. Exercise real retrieval in a read-only test transaction. |
| `src/api/candidate_verification.py::verify_candidate_batch`, `src/strategies/site.py::SiteRepository.site_exists` | Verification accepts up to 100 items and echoes each in order. Only registered `site` with SIMS `bind_existing` policy uses the existing site existence query. `/reconcile/readiness` is also site-only. | Keep site and its readiness behavior. Extend verification for the pilots separately from SIMS policy; no new readiness route is needed. |
| **Shape Shifter:** `backend/app/clients/reconciliation_client.py::ReconciliationClient` and `backend/app/services/reconciliation/service.py::ReconciliationService` | The client caches raw manifest JSON, uses an unmarked form POST for batch, and checks verification count, order, and echoed values. Export checks numeric `aggregate_id` against the saved target ID. The alternative-search route still uses suggestions. | Preserve those interfaces. Typed extension consumption, interactive request plumbing, and removal of the current unverified export fallback are later work, not Phase 1 changes. |

## Scope

- **In scope:** Authority discovery, marked ranked search, complete lists, structured details and numeric exact lookup, and independent pilot verification. Include API, fixture, and disposable PostgreSQL checks and update the Authority runbook.
- **Out of scope:** Unmarked batch or autocomplete changes, generic exploration of registered tables, filter/sort/paging on the server, migrations or generated SQL edits, and any target or SIMS writes. No Shape Shifter implementation, diagnostic envelope, catalog, sidecar, export policy, UI, or deployment enablement changes. The UI's `id:` parsing and local filtering/sorting are later work.
- If verified repository behavior conflicts with this plan during implementation, stop and report the exact source, test, or runtime result. Do not substitute a different contract or broaden the scope.

## Work Breakdown

### Area 1: Publish versioned discovery with pilot capabilities off by default

**Objective:** A legacy client can read the same manifest, while new consumers can discover independent capabilities for the two pilot types.

**Affected code:** `src/api/model.py`, `src/metadata.py`, `src/api/router.py`, `main.py`, `config/config.yml`, `src/record_selection.py` (**NEW**), and `tests/api/test_router.py`.

**Dependencies:** None beyond the Phase 1 handoff and existing registry.

* [x] `T1.1` **Change:** Add one validated selection policy used by discovery and request dispatch.
  * **Target:** `config/config.yml` (`options:record_selection`); `src/record_selection.py` (**NEW**); `main.py::startup`; `src/api/router.py::get_config_dependency`.
  * **Current → required:** Registration exposes matcher support only. Configure each pilot type independently through `ConfigValue` with separate switches for `search_supported`, `identifier_search_supported`, `browse_supported`, `details_supported`, and `export_verification_supported`.
  * **Implementation:** Missing settings or switches mean disabled. Stock settings leave both pilots off. Default to 500 rows, 1,048,576 uncompressed response bytes, and 50 interactive results; validate positive configured limits and keep the interactive cap within the existing 500-result query model maximum. Validate enabled types against the registered pilot adapters and validate `options:id_base` for enabled types. Do not derive a switch from another switch, `supportedTypes`, or SIMS policy.
  * **Validation:** `V-1`, `V-4`.
* [x] `T1.2` **Change:** Serialize discovery in actual HTTP responses.
  * **Target:** `src/api/model.py::ReconciliationDescriptor` and new DTOs in that file, `src/metadata.py::get_reconciliation_metadata`, `src/api/router.py::meta` and new `GET /records/types`.
  * **Current → required:** Add `reconciliation.record_selection: {version: 1, types_path: "/records/types"}`; preserve all existing manifest fields. Return `{types: [...]}` without querying target data. Register the static discovery route before `GET /records/{type}`.
  * **Implementation:** Entries report `type`, the five flags, `id_base`, `id_path`, `browse_max_rows`, `browse_max_bytes`, and `interactive_search_max_results`. Emit explicit JSON `null` for unsupported limits. Use the strategy ID path, not the table name. Declare ordered `display_fields` (`name`, `source`, `label`, `value_type`, `display`) with unique names, `record` or `fields` sources, and the approved scalar types. Declare `text_filter_fields`, `sort_fields`, and `field_filters` only for projected fields. For both pilots expose name and numeric ID; expose description for `feature_type` only. Advertise name (and feature description) for literal case-insensitive text filtering, `contains_ci` for declared text field filters, `equals` for `target_id`, and name/ID sorting. Field filters combine with AND in the consuming client; these are not SQL controls.
  * **Validation:** `V-1`.

**Completion evidence:** Serialized HTTP discovery is additive; a controlled override can enable one capability for one type without enabling any other capability or changing the legacy type list.

### Area 2: Retrieve the same records by search, list, and exact lookup

**Objective:** Each selected record resolves to the same URI and target ID no matter how it is retrieved.

**Affected code:** `src/record_identifiers.py` (**NEW**), `src/record_selection.py` (**NEW**), `src/strategies/strategy.py`, `src/api/model.py`, `src/api/router.py`, `tests/api/test_router.py`, and `tests/api/test_record_selection.py` (**NEW**).

**Dependencies:** Area 1.

* [x] `T2.1` **Change:** Implement shared identifier rules and read-only pilot projections.
  * **Target:** `src/record_identifiers.py` (**NEW**), `src/strategies/strategy.py::ReconciliationStrategy.as_candidate`, `src/record_selection.py` (**NEW**).
  * **Current → required:** Extract the existing site URI parser semantics from `src/api/candidate_verification.py::_site_id_from_candidate` and the existing candidate URI construction into shared helpers. The formatter must not change unmarked candidate IDs.
  * **Implementation:** Use an absolute `id_base` ending in `/` and the exact type segment. Compare scheme and host without case sensitivity; reject a different base path, wrong type, extra path segments, query strings, and fragments. Accept positive ASCII decimal IDs with leading zeros and emit canonical URIs with integer IDs for projected records. Derive the feature projection from the existing registered classifier and approved `table_specs` columns; read the country projection from `authority.location` with `location_type_id = 1` using `location_id` and `label`. Share one per-type projection and membership rule for list and lookup by ID. Allow only declared SQL identifiers, bind values and limits, and use the existing `BaseRepository.fetch_all`/`fetch_one` connection path. A parsed pilot ID outside the database column's integer range is absent; do not send an overflowing value to SQL. Do not call the legacy `get_details` or catch a database failure as a miss.
  * **Validation:** `V-2`, `V-3`, `V-4`.
* [x] `T2.2` **Change:** Serve complete lists and independent exact-ID and URI details.
  * **Target:** `src/api/router.py` (new `GET /records/{type}` and `GET /records/{type}/details`), `src/api/model.py` (new response DTOs), `src/record_selection.py` (**NEW**).
  * **Current → required:** A record has `id`, `target_id`, `type`, `name`, optional `description`, and declared scalar or null `fields`; no confidence scores. List accepts no query parameters. Details accepts exactly one `id` or `target_id`, including rejecting duplicates and extra parameters; check `details_supported` for URI input and `identifier_search_supported` for numeric input.
  * **Implementation:** Limit the list query to `browse_max_rows + 1`; the extra row proves oversize. If rows fit, serialize `{items: [...], completeness: "complete"}` once, measure the exact uncompressed UTF-8 bytes including the envelope, and return those same bytes. At either limit exactly, return the whole list; above either limit return `409 too_large_to_browse` without `items`. Return `{item: record}` for details. A valid but missing ID returns `404 record_not_found`; a successful empty list returns `200` with empty `items`.
  * **Constraints:** New record and marked-search failures use `{error: {code, message}}`. Use `422 invalid_request`, `unsupported_type` (unregistered type), or `unsupported_capability` (registered type without that capability), and `503 database_unavailable` for database and pool failures; do not expose raw database errors to callers.
  * **Validation:** `V-2`, `V-4`.
* [x] `T2.3` **Change:** Enforce the interactive limit without altering unmarked requests.
  * **Target:** `src/api/router.py::reconcile`, `src/record_selection.py` (**NEW**).
  * **Current → required:** For `X-Record-Selection: interactive`, require exactly one query, an explicit type, nonblank text, and an explicit positive integer limit. Return `422 search_limit_exceeded` for a positive value above the type cap, including values above 500; classify it before legacy model validation. Reject malformed requests as `422 invalid_request` before querying. Use only manifest-declared property hints; neither pilot declares any.
  * **Implementation:** Reuse the `feature_type` classifier ranking and candidate conversion. For marked `country` search, call the checked-in `authority.fuzzy_location(text, integer, integer[])` with the bound country subset `[1]`, then use the registered strategy's candidate conversion. Keep the OpenRefine query-keyed result and its candidate URI; use the shared type-aware parser to check that the URI encodes the same positive ID as the list/details record. Bound returned results by the requested limit. A successful search miss returns an empty result; database or pool failure returns the new 503 envelope. No suggest or LLM/RAG fallback. Do not change `src/reconcile.py`, `src/resources/country.yml`, unmarked errors, or autocomplete.
  * **Validation:** `V-1`, `V-2`, `V-4`.

**Completion evidence:** Both projections round-trip across retrieval paths; boundary requests return the contracted result or error, and the country query runs against the repository's installed SQL signature.

### Area 3: Verify pilot references and document the release gate

**Objective:** Phase 2 can verify pilot references with the existing protocol; the feature stays off in general-use configuration.

**Affected code:** `src/api/candidate_verification.py`, `src/api/router.py::verify_candidates`, `tests/api/test_candidate_verification.py`, `tests/identity/test_reconciliation_contract_integration.py`, and `docs/OPERATIONS.md`.

**Dependencies:** Areas 1 and 2.

* [x] `T3.1` **Change:** Extend ordered batch verification, preserving site behavior.
  * **Target:** `src/api/candidate_verification.py::verify_candidate_batch` and `_site_id_from_candidate` (delegate to the shared parser); `src/api/router.py::verify_candidates` (update its description).
  * **Current → required:** Recognize enabled `feature_type` and `country` without consulting SIMS policy for either. Use the same typed lookup as details, even if exact-ID and URI details are both disabled. Keep policy-gated `site` and `SiteRepository.site_exists` unchanged.
  * **Implementation:** Echo the input type and URI exactly, including case and leading zeros, in request order. Keep `exists` with `entity_type` and positive integer `aggregate_id` equal to the target PK, `not_found` for an absent record or non-country location, `invalid_candidate` for a malformed or wrong-type URI, and `unsupported_type` for a disabled or unsupported type. Retain the 100-item limit, success DTO, legacy verification error shape and HTTP 503 with no partial results, and existing site readiness.
  * **Validation:** `V-3`, `V-4`.
* [x] `T3.2` **Change:** Demonstrate read-only behavior and hand off deployment checks.
  * **Target:** `tests/identity/test_reconciliation_contract_integration.py`; `docs/OPERATIONS.md` under “Reconciliation Readiness and Candidate Verification.”
  * **Current → required:** Add a read-only integration round trip for the two pilots alongside the existing site coverage. Document discovery, per-type switches, limits and errors, and the isolated config override. Record the Authority version/commit and checked contract for Phase 2/3.
  * **Constraints:** No schema or identity-policy change. With the shipped config there are no positive pilot capability flags. Phase 4 must validate the exact deployed pair, actual per-type projection and Browse row/byte behavior, and ordered verification. For each type, time 100 representative searches after warm-up through the Shape Shifter backend; p95 must be at most 2,000 ms before advertising interactive search. No direct-Authority timing substitutes for that check. A failed gate leaves only the affected capability/type disabled.
  * **Validation:** `V-1`, `V-4`, `V-6`.

**Completion evidence:** Ordered mixed-type batches work against read-only data, existing site checks still pass, and the runbook distinguishes isolated testing from Phase 4 enablement.

## Acceptance-Criteria Coverage

| Criterion | Proposal criteria | Tasks | Validation | Expected result |
|---|---|---|---|---|
| `PH1-AC-1` | `P-AC-3`, `P-AC-10` | `T1.1`, `T1.2`, `T2.3` | `VM-1`: `V-1` | Same-service discovery, independent flags, cap enforcement, and unchanged legacy responses. |
| `PH1-AC-2` | `P-AC-4`, `P-AC-9` | `T2.1`, `T2.2` | `VM-2`: `V-2`, `V-4` | Complete lists or explicit errors, measured against the actual response bytes; failure is not empty success. |
| `PH1-AC-3` | `P-AC-3`, `P-AC-5`, `P-AC-10` | `T2.1`, `T2.2`, `T2.3`, `T3.1` | `VM-2`: `V-2`, `V-3`, `V-4` | Stable type and numeric IDs, country exclusion, ordered verification, and unchanged site checks. |
| `PH1-AC-4` | `P-AC-7`, `P-AC-13` | `T1.1`, `T2.1`, `T2.3`, `T3.1`, `T3.2` | `VM-3`: `V-1`, `V-3`, `V-4`, `V-6` | Reads succeed under a read-only transaction; stock config does not enable pilot capabilities. |

## Validation And Testing

Run commands from the Authority Service root. The baseline counts below are from existing tests, not the proposed feature tests.

| ID | Command or method | Cases and expected results | Baseline |
|---|---|---|---|
| `V-1` | `.venv/bin/python -m pytest tests/api/test_model.py tests/api/test_router.py tests/test_reconcile.py tests/test_suggest.py tests/strategies/test_configured_classifier.py` | Extend `tests/api/test_router.py` using `TestClient` and mocked config/repositories: check the real manifest and discovery HTTP JSON with stock defaults, one flag enabled at a time, independently overridden limits, and `null` for unsupported limits. Check a single marked JSON and form request at the cap, above the cap (including >500), missing/zero/non-integer limit, malformed and multiple queries, missing type, and disabled/unregistered types; rejected requests do not query. Preserve unmarked multi-query, fallback and explicit-limit tests, including `test_reconcile_queries_uses_each_validated_limit`, and `test_classifier_suggestions_use_prefix_query`. | Pass for existing tests (combined with `V-3`: 247 passed; 3 deprecation warnings). New cases not run: implementation pending. | Result: 183 passed, 3 warnings. New manifest, discovery, and marked-request cases pass; unmarked multi-query, fallback, and explicit-limit tests are unchanged. |
| `V-2` | `.venv/bin/python -m pytest tests/api/test_record_selection.py` (**NEW**) | Use `tests/conftest.py::ExtendedMockConfigProvider` and cursor fixtures with both pilot projections, duplicate labels with different IDs, an ID present only in the other type, a non-country location, and a multibyte label/description. Check complete and empty lists, row limit exactly and one over with bytes under, byte limit exactly and one over with rows under (measure `len(response.content)`), and 409 without `items`. Check query parameter rejection, exact lookup with an ID absent from its label, URI lookup, leading zeros/case, both/neither/repeated identifiers, zero/non-ASCII/malformed/wrong-type URIs, and 404 for absent IDs, including integers too large for the target column. Search operator-provided expanded or translated text against fixture labels, compare returned URIs with list/details, and distinguish empty search from 503. Inject database/pool failure into search, list and details separately; none returns an empty success. | Not run: new file. | Result: 55 passed. Row and byte boundaries, both projections, leading-zero and wrong-type IDs, 404 for oversized IDs, query-parameter rejection, and per-route failure injection are covered. |
| `V-3` | `.venv/bin/python -m pytest tests/api/test_candidate_verification.py tests/api/test_readiness.py tests/strategies/test_site.py` | Extend `tests/api/test_candidate_verification.py` with mixed pilot/site batches, duplicate items, malformed and wrong-type URIs, a missing ID and a non-country location. Assert exact ordered echoes, numeric `aggregate_id`, and independent opt-in with both details flags off. Assert pilot-only verification does not call SIMS policy, disabled lookups do not hit the database, and a failure after an earlier successful item returns only 503. Keep `test_batch_preserves_order_and_classifies_candidates`, `test_policy_disables_candidate_type_without_database_lookup`, and existing site readiness/misconfiguration/batch-size checks. | Pass for existing tests (part of 247 above). New cases not run: implementation pending. | Result: 74 passed. Mixed pilot/site batches, exact ordered echoes, numeric `aggregate_id`, policy bypass for pilots, disabled lookup without database calls, and 503-without-partials pass. |
| `V-4` | `SIMS_INTEGRATION_DB=1 .venv/bin/python -m pytest -o addopts='' -q tests/identity/test_reconciliation_contract_integration.py -k 'phase1_record_selection or site_match_candidate'` | Add `test_phase1_record_selection_read_only` in the named file. Use the helper-owned `127.0.0.1:55432/sead_staging` fixture and local setup in Authority `docs/DEVELOPMENT.md#disposable-database-for-integration-tests`; do not target staging or production. Assert `to_regprocedure` resolves the array signature; pick labelled feature, country, and non-country rows from the views. Within the shared `get_connection()` context, set `SET TRANSACTION READ ONLY` before any reads and assert `SHOW transaction_read_only` is `on`. Drive marked searches, full lists, both details forms, and mixed verification via `ASGITransport` with controlled config. Assert the real IDs, country exclusion, complete lists within test limits, and unchanged target rows and SIMS counts. Check the existing site round trip separately. | Result: 2 passed, 4 deselected. `test_phase1_record_selection_read_only` and `test_site_match_candidate_and_readiness_round_trip` both pass. The container ran the current generated schema (`authority.fuzzy_location(text,integer,integer[])`, `authority.fuzzy_feature_type(text,integer,double precision,double precision)`), 3462 bootstrapped site identities, 156 feature types, 266 countries, and 3138 non-country locations restored from a fresh source dump; target and SIMS row counts were unchanged after the read-only transaction. The full integration file also passes (6 passed). |
| `V-5` | `.venv/bin/ruff check --no-cache src tests main.py`; run the repo's Black and isort in check mode on changed Python files. | No new lint, formatting, or import violations; do not autofix unrelated files. Review generated OpenAPI for the added routes/DTOs and unchanged legacy manifest/verification response definitions. No generated schema changes. | Pass for scoped Ruff on existing touched files; formatting, broader lint, and new OpenAPI checks not run. | Result: Ruff clean on `src`, `tests`, and `main.py`; Black and isort report no changes; OpenAPI exposes `/records/types`, `/records/{type}`, `/records/{type}/details`, and `RecordSelectionErrorEnvelope`; no generated schema changes. |
| `V-6` | Compare the stock `config/config.yml`, runbook instructions, and actual responses from `V-1` before handoff. | Both pilots default off; any override shown is explicitly isolated. The runbook distinguishes matching readiness from capability release and names the exact paired latency method and per-type Phase 4 checks. | Result: Runbook updated in `docs/OPERATIONS.md`; the shipped config leaves both pilots off and shows an isolated single-switch override. Paired latency measurements remain a Phase 4 gate. |

## Deliverables

| Target | Tasks | Completion result |
|---|---|---|
| `config/config.yml`, `main.py`, `src/record_selection.py` (**NEW**) | `T1.1`, `T2.1`–`T2.3` | Default-off policy and two bounded, read-only adapters. |
| `src/metadata.py`, `src/api/model.py`, `src/api/router.py` | `T1.2`, `T2.2`, `T2.3`, `T3.1` | Typed discovery and retrieval, with unchanged legacy response contracts. |
| `src/record_identifiers.py` (**NEW**), `src/strategies/strategy.py`, `src/api/candidate_verification.py` | `T2.1`, `T3.1` | Shared type-aware URI/ID handling and compatible verification for the two pilot types. |
| `tests/api/test_router.py`, `tests/api/test_record_selection.py` (**NEW**), `tests/api/test_candidate_verification.py`, `tests/identity/test_reconciliation_contract_integration.py` | `T1.1`, `T1.2`, `T2.1`–`T2.3`, `T3.1`, `T3.2` | HTTP contracts, regression coverage, and a real read-only round trip. |
| `docs/OPERATIONS.md` | `T3.2` | Control configuration, response behavior, and Phase 4 prerequisites documented. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
|---|---|---|---|
| 1 — Discovery and policy | Done | Approved contract | Default-off policy, `/records/types`, and the manifest descriptor implemented. `V-1` passes (183 passed). |
| 2 — Retrieval and IDs | Done | Area 1 | Shared URI helpers, feature/country projections, complete lists, details, and marked search implemented. `V-2` passes (55 passed). |
| 3 — Verification and release gate | Done | Areas 1 and 2 | Mixed pilot/site verification and the runbook are implemented; `V-3` passes (74 passed). `V-4` passes against a disposable Podman database (2 selected checks, 6 in the file), so the phase validation is complete. |

## Definition Of Done

- [x] All four phase criteria have the mapped implementation and validation results; update this tracker with actual outcomes.
- [x] `V-1`–`V-5` pass, including the disposable read-only check, unchanged unmarked matching limits and prefix behavior, and site compatibility.
- [x] `V-6` confirms default-off settings and a runbook consistent with the HTTP/OpenAPI contract. No target/SIMS writes, schema changes, or Shape Shifter implementation edits.
- [x] Hand off the tested Authority commit and contract to Phases 2 and 3. Record any follow-up and keep general-use enablement and paired measurements in Phase 4.

**Implementation evidence:** `V-1` 183 passed, `V-2` 55 passed, `V-3` 74 passed, `V-4` 2 selected passed (6 in the file), and the full unit suite reports 1463 passed / 50 skipped. `V-5` is clean for Ruff, Black, isort, and generated OpenAPI. `V-6` is confirmed by the default-off stock config and the updated runbook.

**Handoff:** Authority Service `reconciliation-search-and-browse` commit `1f3f1b8` (`feat(reconciliation): add bounded record selection for pilot types`) on top of `5e19232`, pushed and opened as pull request [#53](https://github.com/humlab-sead/sead_authority_service/pull/53) into `dev`. The phase plan names that commit as the Phase 1 dependency for Phases 2 and 3. No follow-up blocking work is open; general-use enablement and paired latency measurement stay in Phase 4.

## Risks And Open Questions

- **Country schema drift:** The checked-in view and array function, not the legacy resource, define the new adapter's SQL dependencies. If the disposable run or selected deployment differs, record the missing function/view or wrong subset and keep country capabilities off; do not fall back to unscoped location search.
- **Sizing and latency:** No production row counts, serialized sizes, or paired latency results are assumed. Phase 4 must measure each capability independently. This is a rollout gate, not an open Phase 1 contract decision.
