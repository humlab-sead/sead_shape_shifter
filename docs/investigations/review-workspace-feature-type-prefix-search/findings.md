# Investigation findings: Review workspace feature-type prefix search

**Brief:** User reports that `sampl` returns no feature-type results, `sample` returns one, and `samples` returns two. They expect “Samples taken by” (ID 4) and “Samples processed by” (ID 3) for all three queries.
**Status:** Conclusive for the current search behavior and its cause; onset in the user's deployed environment is unknown.
**Environment / baseline:** Shape Shifter branch `reconciliation-search-and-browse-ux-fixes` at `694c1c35`; Authority Service branch `classifier-fuzzy-reconciliation-tier-2` at `6c284cee`; investigation run 2026-11-23. Both worktrees were clean before testing.

## Executive summary

The review workspace sends search text to the Authority Service's ranked classifier search. Feature-type search compares the query with the entire normalized label using PostgreSQL `similarity()` and discards results below `0.30`. The shorter prefixes score below that cutoff for one or both labels, so the result count increases as the query becomes longer.

I reproduced the reported result counts and scores with the generated SQL and the two reported labels in a disposable, network-isolated PostgreSQL container. The frontend keeps every item returned by the backend; it does not filter out the missing results. The behavior differs from the older prefix-suggestion endpoint, which remains a separate API. No source code was changed during the initial investigation.

## Verified observations and reproduction

Using the existing test fixture's PostgreSQL bootstrap and `schema/generated/feature_type.sql`, I replaced the fixture labels with “Samples taken by” (ID 4) and “Samples processed by” (ID 3), then called `authority.fuzzy_feature_type(query, 10)` for each query:

| Query | Returned results |
| --- | --- |
| `sampl` | None |
| `sample` | “Samples taken by” — 33.33 |
| `samples` | “Samples taken by” — 47.06; “Samples processed by” — 38.1 |

This reproduces the reported counts and the two displayed scores. It uses synthetic rows, not a connection to the deployed Authority Service or its database.

## Evidence ledger

| ID | Observation or test | Source | Result | Assessment |
| --- | --- | --- | --- | --- |
| E1 | The workspace trims the query, calls `searchSelection`, and assigns the returned `items` directly to `searchResults`. The result list renders that array. | `frontend/src/components/reconciliation/ReconciliationWorkspace.vue:249,933,945,951` | No client-side filtering explains the missing labels. | Verified |
| E2 | Shape Shifter forwards the search text to `ReconciliationClient.search_records`, which posts to `/reconcile` with `X-Record-Selection: interactive`. | `backend/app/services/reconciliation/service.py:1637,1695`; `backend/app/clients/reconciliation_client.py:497,511,512,513,514` | The ranked search reaches the Authority Service with the user's query. | Verified |
| E3 | The interactive Authority endpoint calls the registered strategy's `find_candidates`; the configured classifier uses its generated fuzzy search. | `sead_authority_service/src/api/router.py:143,146`; `sead_authority_service/src/record_selection.py:371,378,379`; `sead_authority_service/src/strategies/configured_classifier.py:55,65` | Feature-type search uses the generated fuzzy-search path. | Verified |
| E4 | The generated feature-type function compares the complete normalized label with the query using `similarity()` and applies a `0.30` label threshold. Candidate scores are `name_sim * 100`. | `sead_authority_service/schema/generated/feature_type.sql:33,66,67`; `sead_authority_service/config/config.yml:9`; `sead_authority_service/src/strategies/query.py:132`; `sead_authority_service/src/strategies/configured_classifier.py:153` | Short prefixes can fall below the threshold even when the label starts with those characters. | Verified |
| E5 | A separate configured-classifier suggestion method performs prefix matching. Its test checks the `left(norm_label, char_length(query)) = query` predicate. | `sead_authority_service/src/strategies/configured_classifier.py:51,53`; `sead_authority_service/src/strategies/query.py:138`; `sead_authority_service/tests/strategies/test_configured_classifier.py:187,192` | The prefix behavior exists, but it is not the review workspace's ranked-search endpoint. | Verified |
| E6 | The Search and Browse plan describes ranked text search and records that short fragments can score below the configured label threshold. The Phase 3 task plan says the old dialog used prefix suggestions and the workspace switches to the new search API. | `docs/proposals/done/RECONCILIATION_SEARCH_AND_BROWSE/RECONCILIATION_SEARCH_AND_BROWSE.md:78,133`; `RECONCILIATION_SEARCH_AND_BROWSE_PHASE_3_TASK_PLAN.md:102`; `RECONCILIATION_SEARCH_AND_BROWSE_PHASE_4_TASK_PLAN.md:49` | The difference is consistent with the implemented search-contract change, rather than a new frontend rendering defect. | Verified |

## Timeline or causal chain

- The Authority Service's bounded interactive search was added in commit `1f3f1b8` on 2026-11-19.
- The Shape Shifter review workspace was added in commit `fde6d253` on 2026-11-20. Its Phase 3 task plan describes replacing the prior prefix-suggestion request with the new ranked-search request.
- The user’s report establishes the current symptom, but there is no deployment record or captured response from an earlier version. The first affected deployed version cannot be established from the available evidence.

## Root-cause assessment

**Confirmed mechanism:** The generated fuzzy function evaluates the query against the whole label and filters on `similarity >= 0.30`. For these labels, `sampl` is below the cutoff for both; `sample` clears it for “Samples taken by” only; `samples` clears it for both. The isolated PostgreSQL reproduction confirms the exact returned labels and scores.

| Hypothesis | Supporting evidence | Contrary evidence / checks | Status |
| --- | --- | --- | --- |
| The frontend discards the labels. | The search result array is assigned and rendered without an additional filter. | The isolated generated-SQL reproduction independently returns the same counts as the UI report. | Ruled out |
| The Authority search threshold causes the different counts. | Generated SQL applies `similarity()` to the full label with a `0.30` cutoff; the isolated reproduction matches the reported outputs. | No contrary evidence found. | Verified |
| The review workspace still uses prefix suggestions. | A separate prefix-suggestion method exists. | The workspace calls ranked search; the implementation plan explicitly separates the two paths. | Ruled out |

## Impact and extent

**Confirmed affected case:** Feature-type ranked search for these two labels and the three reported prefixes.

**Potential wider impact:** Other types using the same generated classifier search can also omit short label prefixes when their full-label similarity is below the configured cutoff. This investigation did not test other types or their live data.

## Remediation options

| Option | Benefits | Risks / compatibility | Prerequisites / validation |
| --- | --- | --- | --- |
| Keep ranked fuzzy search and also admit normalized label-prefix matches below the fuzzy threshold. | Preserves ranked results for expansions and translated terms while returning these prefix matches. Existing similarity scores can remain visible. | Can add low-scoring suggestions for short prefixes; those results must remain suggestions and must not be treated as automatic matches. | Decide the minimum prefix length, then test the exact three queries against generated SQL and the interactive API. |
| Change the review workspace to use prefix suggestions. | Restores prefix behavior directly. | Would make ordinary search unsuitable for non-prefix expansions and translated terms described in the approved Search and Browse design. | Would require revising that search contract and its tests. |
| Lower the label threshold globally. | Could admit more short queries without adding a separate prefix rule. | Broadens fuzzy results for every affected classifier and may add unrelated candidates. | Requires measured false-positive review across supported types. |

**Implemented follow-up (2026-11-23):** The Authority Service now adds literal, case- and accent-insensitive label-substring matches to interactive search for configured classifiers, retains fuzzy-ranked results, deduplicates by target ID, and keeps the best score for each result. Batch reconciliation is unchanged. The change has not been deployed.

**Recommended next step:** Deploy the Authority Service change and verify the three reported queries against the intended environment.

**Prevention / regression detection:** Regression coverage now checks the three reported queries, uppercase matching, a mid-label substring, literal `%` and `_` characters, fuzzy-result retention, duplicate-ID merging, and interactive API output.

## Unresolved questions and blockers

- The first deployed version showing this behavior is unknown; no deployment/version evidence or historical live response was provided.
- The investigation did not measure prefix behavior on other configured classifier types.
- The exact reproduction uses “Samples taken by” as the label, matching the expected result text aside from the reported “taked” typo.

## Verification record

- `cd /data/roger/source/sead_authority_service && rtk uv run pytest -q tests/strategies/test_configured_classifier.py tests/api/test_record_selection.py` — passed (exit status 0).
- Loaded the existing PostgreSQL integration-test bootstrap and generated feature-type SQL into a temporary `postgres:17-alpine` container with networking disabled. Inserted the two reported labels and queried `authority.fuzzy_feature_type` for all three inputs. The output matched the table above; the container was removed afterward.
- After implementation, `rtk uv run pytest -q tests/strategies/test_configured_classifier.py tests/api/test_record_selection.py tests/strategies/test_strategy.py` — passed.
- After implementation, `CLASSIFIER_SQL_INTEGRATION=1 rtk uv run pytest -q tests/strategies/test_classifier_prelimit_integration.py::test_feature_type_substring_search_finds_short_prefixes_and_inner_text` — passed against disposable PostgreSQL.
- After implementation, Black, isort, and pylint checks passed for the modified Python files.
- No production database, deployment, or source data was changed.

## References

- Shape Shifter search implementation: `frontend/src/components/reconciliation/ReconciliationWorkspace.vue`; `backend/app/services/reconciliation/service.py`; `backend/app/clients/reconciliation_client.py`.
- Authority Service matching implementation: `src/record_selection.py`; `src/strategies/configured_classifier.py`; `schema/generated/feature_type.sql`; `config/config.yml`.
- Authority Service tests: `tests/strategies/test_configured_classifier.py`; `tests/strategies/test_classifier_prelimit_integration.py`.
- Search contract and migration notes: `docs/proposals/done/RECONCILIATION_SEARCH_AND_BROWSE/`.
