# Investigation findings: site batch reconciliation Decimal/float error

- **Brief:** User report and attached log (`Pasted text #1`); no separate brief was supplied
- **Status:** Partially conclusive; code fix implemented and tested locally
- **Environment / baseline:** Shape Shifter `dev` at `4a229bdd`; Authority Service `dev` at `2f71b3b31d143fdbf50f1f5e1436e131ef39451b`. The attached container log reports Python 3.13. Its deployed Authority Service version is not identified.

## Executive summary

The attached log shows the first 50-query reconciliation request completed, then the next 50-query request failed with `unsupported operand type(s) for +: 'decimal.Decimal' and 'float'`. Shape Shifter sends requests in batches of 50, but batching is not the cause.

The checked-out Authority Service contains a matching failure path. Its exact-national-ID site query selects `1.0 AS name_sim`, which PostgreSQL types as `numeric` and Psycopg returns as `Decimal`. When the site strategy applies a geographic or place-name boost, it adds a Python `float` to that score and raises the reported `TypeError`. A focused in-memory reproduction of the scoring operation produced the same error.

The project maps national ID and location properties for `site`, so this path is reachable. I implemented score normalization before the optional boosts, made the SQL exact-match score explicitly `double precision`, and added a regression test. The focused site test suite passes. The log does not include the failed query payload or deployed Authority Service version, so it cannot establish which query in the second batch triggered the error or confirm that the deployed service matches the checked-out revision.

## Verified observations and reproduction

The log records 7,511 normalized rows, completion of one 50-query batch with 64 candidates, then an HTTP 500 while processing the next 50-query batch. Shape Shifter sets `batch_size = 50`, awaits each batch before continuing, and saves the updated catalog only after all batches complete ([reconciliation service](../../../backend/app/services/reconciliation/service.py#L981), [batch call](../../../backend/app/services/reconciliation/service.py#L998), [catalog save](../../../backend/app/services/reconciliation/service.py#L1063)). Therefore, this failed run does not save the candidates from its first batch.

The project maps `place_name`, `latitude`, `longitude`, and `national_id` for the `site` entity ([reconciliation settings](../../../sead-tools/shape-shifter.sead.se/container-data/projects/Riia_copy_Brunos-Strucke/shapeshifter.reconciliation.yml#L4102)). The project entity defines the corresponding input columns ([site entity](../../../sead-tools/shape-shifter.sead.se/container-data/projects/Riia_copy_Brunos-Strucke/shapeshifter.yml#L237)).

In the checked-out Authority Service, `fetch_site_by_national_id` selects `1.0 AS name_sim` ([site query](https://github.com/humlab-sead/sead_authority_service/blob/2f71b3b31d143fdbf50f1f5e1436e131ef39451b/src/resources/site.yml#L48-L49)). `SiteReconciliationStrategy` uses that query when a national ID is provided, then applies geographic and/or place-name scoring when those properties are present. Both scoring methods add a floating-point boost to `candidate["name_sim"]` ([site strategy](https://github.com/humlab-sead/sead_authority_service/blob/2f71b3b31d143fdbf50f1f5e1436e131ef39451b/src/strategies/site.py#L64-L116)). By comparison, the generated fuzzy-site function declares its `name_sim` result as `double precision` ([generated function](https://github.com/humlab-sead/sead_authority_service/blob/2f71b3b31d143fdbf50f1f5e1436e131ef39451b/schema/generated/site.sql#L44-L50)).

I reproduced the error by passing `Decimal("0.7")` as a candidate score and a float geographic boost through `_apply_geographic_scoring`. The result was exactly:

```text
TypeError: unsupported operand type(s) for +: 'decimal.Decimal' and 'float'
```

## Evidence ledger

| ID | Observation or test | Source | Result | Assessment |
| --- | --- | --- | --- | --- |
| E1 | Reconciliation log | Attached `Pasted text #1`, 2026-11-17 08:50:04–08:50:05 | First 50 queries completed; the next request received HTTP 500 with the Decimal/float addition error. | Verified report |
| E2 | Batch and save order | [service.py](../../../backend/app/services/reconciliation/service.py#L981) | Batches contain 50 queries; catalog save occurs after the batch loop. | Verified in current Shape Shifter checkout |
| E3 | Site query properties | [shapeshifter.reconciliation.yml](../../../sead-tools/shape-shifter.sead.se/container-data/projects/Riia_copy_Brunos-Strucke/shapeshifter.reconciliation.yml#L4102) | The project maps national ID, coordinates, and place name to the site service. | Verified configuration |
| E4 | Exact-ID score type source | [site.yml](https://github.com/humlab-sead/sead_authority_service/blob/2f71b3b31d143fdbf50f1f5e1436e131ef39451b/src/resources/site.yml#L48-L49) | Exact-ID matches use the SQL literal `1.0 AS name_sim`; PostgreSQL types this literal as `numeric`, which Psycopg exposes as `Decimal`. | Verified in checked-out service source; deployed revision unknown |
| E5 | Incompatible arithmetic | [site.py](https://github.com/humlab-sead/sead_authority_service/blob/2f71b3b31d143fdbf50f1f5e1436e131ef39451b/src/strategies/site.py#L82-L116) | Geographic and place-name boosts are floats added to the candidate score. | Verified in checked-out service source |
| E6 | Focused scoring reproduction | One-off `uv run python` diagnostic using `Decimal("0.7")` and a float distance boost | The site scoring method raised the same `TypeError` as the attached log. | Verified mechanism; not a replay of the unavailable request payload |
| E7 | Site strategy tests after the fix | `rtk uv run pytest tests/strategies/test_site.py -q` in the Authority Service checkout | All 41 tests passed, including the Decimal score regression. | Verified |
| E8 | Local fix and formatting checks | Authority Service working tree | Candidate scores are normalized before either boost path, the exact-match SQL literal is explicitly `double precision`, and Black/isort checks pass. | Verified locally; not deployed |

## Timeline or causal chain

1. Shape Shifter builds site queries with the configured, non-null reconciliation properties.
2. The Authority Service receives a site query with a national ID and finds an exact-ID candidate.
3. That SQL query supplies `name_sim` as `1.0`, returned as a `Decimal`.
4. If the query also supplies coordinates or a place name, the site strategy calculates a float boost and adds it to the Decimal score.
5. Python raises `TypeError`; the Authority Service returns HTTP 500 for the batch.
6. Shape Shifter cannot finish the batch loop and does not reach the catalog save.

Steps 1–5 describe a reproducible path in the checked-out source. The attached log does not reveal the failed query ID or its property values, so the exact query-level chain remains unverified.

## Root-cause assessment

**Confirmed code defect:** The exact-national-ID query and site scoring code do not use a consistent numeric type for `name_sim`. The exact-ID SQL returns a `Decimal`, while score boosts are floats. The same arithmetic error is reproducible in the current site scoring method.

| Hypothesis | Supporting evidence | Contrary evidence / checks | Status |
| --- | --- | --- | --- |
| An exact-ID site candidate with a location property triggers the Decimal/float addition | `site.yml` returns `1.0 AS name_sim`; the project maps national ID and location properties; the strategy adds float boosts; the same operation was reproduced. | No request body or query ID was included in the log, and the deployed service version is unknown. | Verified mechanism; supported explanation for the reported run |
| The 50-query batch size causes the type error | The failure occurs on the second batch. | The exception is reproduced by site score arithmetic; batch size only determines which request contains the failing query. | Ruled out as the arithmetic cause |
| The project thresholds are invalid | Project thresholds are `0.95` and `0.7`. | They meet the documented ordering and range; the exception identifies a numeric-type mismatch. | Ruled out |

## Impact and extent

**Confirmed affected case before the local fix:** An exact-national-ID candidate that receives geographic or place-name scoring failed when its database score was a `Decimal`. The fix prevents that mismatch in the current working tree.

**Confirmed effect on the reported batch:** The second batch returns HTTP 500, and the overall Shape Shifter run exits before saving reconciliation results. The first batch's candidates were held in memory and are not saved by this run.

**Potential wider impact:** Other site queries may be unaffected if they use the fuzzy query, whose generated SQL declares `name_sim` as `double precision`, or if no location boost is applied. The available log does not identify how many queries in the failed batch meet the trigger conditions.

## Remediation options

| Option | Benefits | Risks / compatibility | Prerequisites / validation |
| --- | --- | --- | --- |
| Normalize each candidate's `name_sim` to `float` before applying site boosts. Also declare the exact-match SQL value as `1.0::double precision` to match the fuzzy-query result type. | Fixes the current exact-ID mismatch and keeps scoring arithmetic consistent if another query source returns `Decimal`. | No data migration is needed. The conversion retains the score's numeric meaning; unexpected nonnumeric values should still raise an explicit error. | Add a regression test with a Decimal exact-ID score and float location boost; run the site strategy tests and then a full batch against the updated service. |
| Remove the coordinate/place-name property mappings as a temporary workaround. | Avoids the optional boost code for queries without those properties. | Loses location context and is not reliable if any mapped property remains populated. It does not fix the Authority Service defect. | Not recommended except as a controlled diagnostic. |

**Implemented resolution:** In the Authority Service working tree, normalize each candidate's `name_sim` to `float` before applying either optional boost, and explicitly cast the exact-match SQL literal to `double precision`. The regression test supplies a Decimal exact-ID score plus geographic and place-name properties and verifies both boosts complete with a float result.

**Recommended next step:** Deploy the tested Authority Service change through its normal release process, then rerun the project reconciliation and confirm all batches complete and the catalog is saved. Changing Shape Shifter's batch size would only move the failing query to a different batch.

**Prevention / regression detection:** Include Decimal-returning database values in site scoring tests. After the service fix is deployed, rerun the project reconciliation and confirm that all batches complete and the catalog is saved.

## Unresolved questions and blockers

- Which query ID in the second batch failed, and did it contain a matching national ID plus coordinates or a place name?
- Which Authority Service revision was running at `host.docker.internal:8024` when the error occurred?
- The attached log omits the Authority Service traceback and request payload, so the exact failing branch cannot be distinguished between geographic and place-name scoring.

The smallest useful additional diagnostic is a sanitized failed query ID and the presence/absence (not the raw values) of its `national_id`, `latitude`, `longitude`, and `place_name` properties, together with the deployed Authority Service revision.

## Verification record

- `rtk git status --short --branch` in Shape Shifter — `dev`; a pre-existing untracked `docs/proposals/RECONCILIATION_IMPROVEMENTS_BACKLOG.md` was left untouched.
- Authority Service baseline — clean `dev` checkout at `2f71b3b31d143fdbf50f1f5e1436e131ef39451b`; the implementation now leaves three intended files modified.
- `rtk uv run pytest tests/strategies/test_site.py -q` — passed, 41 tests after the fix.
- `rtk uv run black --check src/strategies/site.py tests/strategies/test_site.py` — passed.
- `rtk uv run isort --check-only src/strategies/site.py tests/strategies/test_site.py` — passed.
- `rtk git diff --check` in Authority Service — passed.
- One-off `uv run python` diagnostic invoking `_apply_geographic_scoring` with a Decimal candidate score and float distance boost — reproduced the reported `TypeError`.
- Pylance MCP diagnostics were unavailable because the tool catalog timed out; terminal tests and format checks were used instead.
- `GRAPHIFY_VIZ_NODE_LIMIT=0 ~/.local/bin/graphify update .` in Authority Service — refused to overwrite the existing graph because saved semantic node `docs_design_entities_yml` was missing and the rebuilt graph had 7,337 nodes versus 8,296. No force update was attempted.
- Authority Service source and test files were changed locally; they are not committed or deployed. Project YAML, production state, and databases were not changed. The full batch was not replayed because the deployed service revision and failed query input were not available.

## References

- [Attached reconciliation log](../../../../../.vscode-server/data/agentSessionData/41c1f061-45df-405d-9d53-d613609cfc6a/attachments/0d266397-c04e-43d9-8083-b2c8f9efaad2/Pasted%20text%20%231.txt)
- [Authority Service site query](https://github.com/humlab-sead/sead_authority_service/blob/2f71b3b31d143fdbf50f1f5e1436e131ef39451b/src/resources/site.yml#L48-L49)
- [Authority Service site strategy](https://github.com/humlab-sead/sead_authority_service/blob/2f71b3b31d143fdbf50f1f5e1436e131ef39451b/src/strategies/site.py#L64-L116)
- [Shape Shifter reconciliation service](../../../backend/app/services/reconciliation/service.py#L981)
- [Project site reconciliation settings](../../../sead-tools/shape-shifter.sead.se/container-data/projects/Riia_copy_Brunos-Strucke/shapeshifter.reconciliation.yml#L4102-L4113)
