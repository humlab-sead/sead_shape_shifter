# Reconciliation Search and Browse: Phase 4 Task Plan

## Phase Summary

**Goal:** Validate the paired Search/Browse workflow against one named pilot environment and record a baseline, then advertise each capability only for the pilot types that pass their own checks.

**Readiness:** Validated for implementation on 2026-11-20. The [approved proposal](./RECONCILIATION_SEARCH_AND_BROWSE.md), [Phase 4 in the phase plan](./RECONCILIATION_SEARCH_AND_BROWSE_PHASE_PLAN.md#phase-4-per-type-pilot-and-capability-release), and the frozen [Phase 2 save contract](./RECONCILIATION_SEARCH_AND_BROWSE_PHASE_2_CONTRACT.md) fix the required behavior. Phases 1–3 are implemented: the Authority Service contract at `sead_authority_service` commit `1f3f1b8`, Shape Shifter at commit `7340510f`. The blocking decisions Phase 4 named — a named pilot environment and selected paired images — are settled below.

**Named environment:** `pilot-recon-2026-11-20`. This is the identity `VM-13` records. Its full specification is in [Pilot Environment](#pilot-environment).

**Progress:** Areas 1–5 are complete. The baseline and pilot-only capability decision are recorded in [the Phase 4 baseline](./RECONCILIATION_SEARCH_AND_BROWSE_PHASE_4_BASELINE.md). Raw measurements remain in `/data/roger/pilot-recon/`, outside both repositories.

**Constraints:** Retrieval and review must not write target data or SIMS state. Capability advertisement stays per type and per capability, and a type that fails keeps only its failed capabilities unadvertised. Do not present a working catalog save as proof that a target record exists. Do not change the frozen Phase 1 identifier contract or the Phase 2 save contract to make a measurement pass.

**Acceptance criteria**

1. [x] `PH4-AC-1` (from `P-AC-3`–`P-AC-5`, `P-AC-10`, `P-AC-13`): Each advertised `feature_type` or `country` capability passes its own paired integration and keyboard/browser checks against the selected service pair. Search, exact-ID, Browse, and export readiness remain independent; one unready type does not block a passing type.
2. [x] `PH4-AC-2` (from `P-AC-1`, `P-AC-2`, `P-AC-6`–`P-AC-9`, `P-AC-11`–`P-AC-13`): The pilot covers first-time review, atomic and conflicting saves, resume, outage behavior, real exported IDs and New approvals, and unchanged source identity. Retrieval produces no target or SIMS writes.
3. [x] `PH4-AC-3` (from `P-AC-13`): The named environment records search/browse median and 95th-percentile times, time and interactions per decision and per New decision, request counts, and preview/normalization invocations as the initial baseline, without claiming improvement over the old workflow.

## Pilot Environment

`pilot-recon-2026-11-20` runs on one Linux host as rootless Podman containers. Its runtime state lives outside both repositories in `/data/roger/pilot-recon`.

| Element | Value |
| --- | --- |
| Shape Shifter image | `localhost/shape-shifter:pilot-7340510f`, revision `7340510ffb3d66ed150394605e1803ec196c7a08` |
| Authority Service image | `localhost/sead-authority:pilot-1f3f1b8`, revision `1f3f1b8470e44b1d0730fb9d8b00e3318ec588eb` |
| Data | `sead_pilot_recon`, a snapshot of `sead_staging` created 2026-11-20 |
| Database role | `sead_ro`, read-only for both services |
| Network | Podman network `pilot-net`; Shape Shifter reaches the Authority at `http://pilot-authority:8000` |
| Host ports | Authority `127.0.0.1:8025`, Shape Shifter `127.0.0.1:8026` |
| Startup | `/data/roger/pilot-recon/start-pair.sh` recreates both containers |
| Capability flags | All five enabled for `feature_type` and `country` in the pilot copy of the Authority config only |

Both images are built from published refs, so the pair can be rebuilt. The shipped `config/config.yml` in the Authority repository keeps every pilot flag `false`; enabling them is confined to the pilot's mounted config.

Port `8012`, the deployed instance on this host, is deliberately left alone. The pilot uses `8026`.

## Repository Findings

**Repository basis:** Shape Shifter branch `reconciliation-search-and-browse`, commit `7340510f`; Authority Service branch `reconciliation-search-and-browse`, commit `1f3f1b8`; planning date 2026-11-20. Uncommitted changes were considered: the Phase 3 task plan and `ReconciliationWorkspace.test.ts` carry the VM-9 corroboration added on the same date.

| Evidence | Verified finding | Planning implication |
| --- | --- | --- |
| `sead_authority_service` `src/record_selection.py::collect_browse_list` | Row and byte limits raise `too_large_to_browse` (409) with no partial items. | The limit path is implemented and testable by lowering a limit in the pilot config. Neither pilot list reaches it today. |
| Live pilot `GET /records/feature_type`, `GET /records/country` through Shape Shifter | `feature_type` returns 156 rows and `country` 266, both `completeness: complete`. | Browse is the target vocabulary, not the source queue. Both sit far below 500 rows and 1 MiB, so a limit test must lower a limit rather than rely on live size. |
| Measured browse payload through the backend vs the Authority | The backend projects 156 rows as 32,675 bytes and 266 rows as 38,211 bytes. The Authority alone returns 29,336 and 29,699 bytes for the same rows. | The backend adds `description` and `score` to every item, so the backend figure is the real client-side projection and the larger one. Record the backend figure as the projection size; the Authority figure alone understates it. |
| Live pilot `POST .../selection/search` | Search is case-insensitive and matches substrings as well as prefixes: `idden`, `Mid`, and `MID` all return `Midden`. | Representative queries may include mid-label fragments. Short fragments can score below the configured label threshold, which yields empty results rather than errors. |
| `arbodat-pilot` `location` entity | All place types are present in the source queue (Ort, Kreis, Land, Staat, FlurStr). Only the `Staat` rows can match the `country` type. | The country source queue is realistic but sparse; `VM-12` needs a fixture with deliberate volume rather than this entity. |
| `backend/app/services/reconciliation/resolvers.py::SqlQueryReconciliationSourceResolver.resolve` | A custom query source raises `KeyError: 'recon_temp'` because `TableConfig` indexes `entities_cfg[entity_name]` while the dict is not nested under that name. Its test asserts the crash. | Not a Phase 4 blocker. Pre-existing defect; filtered source specs are unavailable until it is fixed, which belongs to its own change and not this phase. |
| `backend/app/api/v1/endpoints/reconciliation.py::export_reconciliation_to_mapping` | Export validates accepted references locally, verifies them in order against the Authority, and blocks before touching the sidecar. | Export readiness is provable per type without inspecting the sidecar for unverified links. |
| `backend/app/services/reconciliation/service.py::save_decision_batch` | Batch saves resolve source rows once and echo saved decisions in request order with `counts`. | Per-decision interaction counts can be derived from request counts the harness owns. |
| Playwright in `frontend/` | `playwright install chromium` refuses Ubuntu 26.04 and no system browser is installed on this host. | Automated browser runs need a supported runtime, but `PH4-AC-1` does not require automation. Phase 3's browser evidence was produced by a person, so `T4.1` follows the same method. |
| `shape-shifter/logs/app.log` | Contains one `ShapeShift preview for entity` line per preview. A preview request plus one batch save added two lines. | Preview and normalization invocation counts for `PH4-AC-3` are measurable from the log without new instrumentation. |

Measurements below were taken from the live pilot during planning and are recorded so implementation starts from facts, not assumptions:

| Measurement | `feature_type` | `country` |
| --- | --- | --- |
| Complete list rows | 156 | 266 |
| Complete list bytes | 29,336 | 29,699 |
| Search p95, 100 searches after warm-up, no added delay | 68.9 ms | 69.7 ms |
| Search p95, about 100 ms round-trip added | 571.4 ms | 571.0 ms |
| Search p95, about 200 ms round-trip added | 1,070.9 ms | 1,069.8 ms |

The added-delay figures come from `delay_proxy.py` on `pilot-net`. The observed slope is about 5 ms of p95 per 1 ms of round-trip time, which implies the p95 budget is met up to roughly 385 ms round-trip. That envelope, not the loopback number, is the defensible statement.

## Scope

- **In:** Per-type live projection and limit checks, per-type verification and export checks, a repeatable search and decision measurement harness, the `VM-12` pilot fixture, browser-level checks for both types, the recorded `PH4-AC-3` baseline, and the per-type advertisement decision.
- **Out:** Changing the frozen Phase 1 or Phase 2 contracts; enabling pilot capabilities in the shipped Authority configuration; fixing the custom-query source resolver; backlog R33 and R34; a policy for links exported unverified by earlier versions; server paging, recent-query history, and target-record creation during review.

## Work Breakdown

### Area 1: Repeatable measurement harness

**Objective:** One command produces the search and decision measurements `PH4-AC-3` requires, in a named environment, with no manual arithmetic.

**Affected code:** `scripts/pilot/measure_selection.py`, `scripts/pilot/delay_proxy.py`, `scripts/pilot/README.md`, `NEW` `scripts/tests/pilot/test_measure_selection.py`.

**Dependencies:** None.

**Tasks:**

* [x] `T1.1` **Change:** Confirm the search measurement harness.
  * **Target:** `scripts/pilot/measure_selection.py`.
  * **Current → required:** The harness is tracked and reports per-type median, p95, min, max, empty-result and failure counts, and exits non-zero above budget. Required: no further change; run it against the environment as written.
  * **Implementation:** Read labels from `GET .../selection/browse`; build a query mix of whole labels, mid-label fragments, single words, and deliberate non-matches; discard a warm-up prefix; time each `POST .../selection/search`; compute percentiles; write JSON with `--json-out`.
  * **Constraints:** Measure through the Shape Shifter backend only. Do not time the Authority directly, because the Phase 1 constraint excludes direct-Authority timing as gate evidence.
  * **Validation:** `V-1`, `V-2`.

* [x] `T1.2` **Change:** Confirm the latency-injection proxy.
  * **Target:** `scripts/pilot/delay_proxy.py`.
  * **Current → required:** Tracked and working. Required: no further change; use it for the delay runs.
  * **Implementation:** Forwards bytes in both directions with `asyncio`, pausing before each write; logs the effective round trip on startup; takes `--listen`, `--listen-host`, `--upstream`, and `--delay-ms`.
  * **Constraints:** Documentation must state that one-way delay roughly doubles into round-trip time, so recorded labels stay honest. The proxy is measurement tooling and must never be part of a deployed path.
  * **Validation:** `V-3`.

* [x] `T1.3` **Change:** Document the harness and the environment.
  * **Target:** `scripts/pilot/README.md`.
  * **Current → required:** Written. Required: no further change beyond keeping it current with later runs.
  * **Implementation:** Documents the baseline and delay-injected invocations, notes that delay labels are round-trip approximations, and records that container images must be pinned by tag and revision.
  * **Constraints:** Do not duplicate the pilot runtime state, which stays outside the repository.
  * **Validation:** `V-4`.

**Completion evidence:** `python3 scripts/pilot/measure_selection.py --runs 100` against the named environment reports per-type median and p95 and exits zero within budget.

### Area 2: Per-type live projection and limit checks

**Objective:** Each pilot type has recorded projection size and a demonstrated too-large path.

**Affected code:** Pilot Authority config copy only (`/data/roger/pilot-recon/authority/config/config.yml`); no repository source change.

**Dependencies:** Area 1 for command consistency.

**Tasks:**

* [x] `T2.1` **Change:** Record live per-type projection.
  * **Target:** Baseline record under Area 5.
  * **Current → required:** 156 and 266 rows are known; bytes and per-row width are not recorded per type with the method used.
  * **Implementation:** Capture row count, uncompressed UTF-8 byte size of the complete response including its envelope, and `completeness` for both types, through the Shape Shifter backend.
  * **Constraints:** Use the snapshot date in the record; live sizes must not be assumed to match production.
  * **Validation:** `V-5`.

* [x] `T2.2` **Change:** Demonstrate the too-large path per type.
  * **Target:** Pilot `config.yml` `options.record_selection.browse_max_rows`, restored afterwards.
  * **Current → required:** Neither list reaches the 500-row limit, so `too_large_to_browse` has never run. Required: a recorded 409 with no partial items for each type.
  * **Implementation:** Lower `browse_max_rows` below the type's row count, request the complete list, assert 409 `too_large_to_browse` and no items, then repeat for the byte limit and restore both values.
  * **Constraints:** Change the pilot copy only. Restore the configured limits and confirm the list succeeds again before leaving Area 2.
  * **Validation:** `V-6`.

**Completion evidence:** Both types have recorded sizes, and both have a recorded `too_large_to_browse` rejection for rows and for bytes, with limits restored.

### Area 3: Verification and export per type

**Objective:** Export readiness is proven per type, including the refusal path.

**Affected code:** Existing routes; no source change expected.

**Dependencies:** Area 2.

**Tasks:**

* [x] `T3.1` **Change:** Record ordered verification for both types.
  * **Target:** `POST /reconcile/verify-candidates` through the Shape Shifter backend, and `POST .../export-to-mapping`.
  * **Current → required:** `exists`, `not_found`, and `invalid_candidate` have been observed once for the pilot; they are not recorded per type with the export gate.
  * **Implementation:** For each type, save an accepted decision with a real target, one with an unknown ID, and one whose URI carries the other type's path. Export and record the per-key outcomes and whether any sidecar link was written.
  * **Constraints:** Reset the catalog and remove the sidecar afterwards so later checks start clean. Do not leave an accepted decision that fails verification in the pilot.
  * **Validation:** `V-7`.

**Completion evidence:** Each type shows `verified` for the valid link, and the invalid cases block export with no unverified link written.

### Area 4: Pilot fixture and browser checks

**Objective:** Satisfy `VM-12`'s data shape and cover `PH4-AC-1`'s browser half in a supported runtime.

**Affected code:** `NEW` pilot fixture project; no repository source change. Browser checks run in a person's browser, so no harness is built.

**Dependencies:** Areas 2 and 3.

**Tasks:**

* [x] `T4.1` **Change:** Run the browser checks in a reviewer's own browser.
  * **Target:** The pilot at `http://127.0.0.1:8026`, opened by a person.
  * **Current → required:** Phase 3's browser evidence came from a person driving the workspace through a browser, which is the established method in this repository. Required: the same kind of scripted pass, covering both pilot types.
  * **Implementation:** Forward port `8026` to the reviewing workstation, open the pilot, and work through the checklist below for each type. Record pass or fail per line, with the observed behaviour.
  * **Constraints:** `PH4-AC-1` asks for keyboard and browser checks; it does not require automation. Do not block the phase on a headless runner. An automated Playwright container remains a legitimate future improvement but is not a prerequisite.
  * **Validation:** `V-8`.

Browser checklist per type:

Feature type: `feature_type / feature_type_name`
| Check | Expected | Actual |
| --- | --- | --- |
| Open review without Find Candidates | Workspace opens from the specification list |  Pass: Clipboard with a magnifying glass opened the review workspace. |
| Ranked search finds a known label | Expected record returned | Pass: Expected record returned. Searched from `ditch` label, returned `Ditch`. |
| `id: <positive integer>` | Exact record, even when its label lacks the ID | Pass: Expected record returned. Searched for `id: 31`, returned `Ditch`. |
| `id: <non-numeric>` | Visible validation message, no fuzzy fallback | Pass: `id: apa` displayed `Enter 'id:' followed by a positive whole-number target ID, for example 'id: 42'..` |
| Browse filtering with `%`, `_`, `*` | Literal matching, no extra browse request per keystroke | Pass: Characters `%`, `_`, `*` were used for filtering and matched literally. |
| Browse sorting on label and ID | Stable order | Pass: Browse sorting on label and ID maintained a stable order. |
| Keyboard staging and advance through ten rows | Visible focus follows the active row | Pass: Staging (Alt+Enter) increases count + tick, Alt+Down does not increase count|
| Mark one row New | Staged, not saved | Pass: Marked one row as New, count increased and tick appeared. |
| Save decision, then Export | Distinct actions; export reports verification | Pass: Save decision decrease decrease need review count, export reports verified. |
| Reload | Unsaved drafts restored, no target selection restored | Pass: Unsaved drafts were restored, and no target selection was restored. |

Feature type: `country / location / location_name`
| Check | Expected | Actual |
| --- | --- | --- |
| Open review without Find Candidates | Workspace opens from the specification list | Pass: as expected. |
| Ranked search finds a known label | Expected record returned | Pass: as expected. |
| `id: <positive integer>` | Exact record, even when its label lacks the ID | Pass: as expected. |
| `id: <non-numeric>` | Visible validation message, no fuzzy fallback | Pass: as expected. |
| Browse filtering with `%`, `_`, `*` | Literal matching, no extra browse request per keystroke | Pass: as expected. |
| Browse sorting on label and ID | Stable order | Pass: as expected. |
| Keyboard staging and advance through ten rows | Visible focus follows the active row | Pass: as expected. |
| Mark one row New | Staged, not saved | Pass: as expected. |
| Save decision, then Export | Distinct actions; export reports verification | Pass: as expected. |
| Reload | Unsaved drafts restored, no target selection restored | Pass: as expected. |

* [x] `T4.2` **Change:** Build the `VM-12` fixture.
  * **Target:** `NEW` pilot project with 100 source rows per pilot type.
  * **Current → required:** `arbodat-pilot` has 55 feature rows and a sparse country queue. Required: 100 rows, about 90 intentionally New, compound keys, duplicate labels, and source values that can be changed mid-run.
  * **Implementation:** Define a fixture project with a fixed or CSV-backed entity per type, compound keys, some duplicated display labels across distinct keys, and keys stable enough to edit one source value to test change rejection.
  * **Constraints:** Keep the fixture out of the shipped projects directory; it belongs to the pilot environment. Mark rows with placeholder target IDs rather than nulls, because a null `public_id` serializes as `NaN` and fails strict JSON.
  * **Validation:** `V-9`.

* [x] `T4.3` **Change:** Run the end-to-end pilot.
  * **Target:** Named environment.
  * **Current → required:** Individual behaviors are proven; a single paired run covering first-time review, atomic and conflicting saves, resume, outage, real exported IDs, and unchanged source identity is not.
  * **Implementation:** Execute the `VM-12` scenario list against the fixture, restarting the Authority for the outage checks and confirming New-only saves and exports continue.
  * **Constraints:** Record what was observed, including any behavior that did not match. Do not retry a failed save automatically.
  * **Validation:** `V-10`.

**Result:** The run completed on 2026-11-20 against `vm12-fixture`. Every scenario in the list was observed, including one stale-value rejection, one duplicate-key rejection, and one Authority outage with a New-only save and export while it was down. The browser checks for both pilot types passed on 2026-11-21; see `V-8`.

**Completion evidence:** A recorded paired run over 100 rows per type, with browser evidence, including at least one conflict and one outage.

### Area 5: Baseline record and advertisement decision

**Objective:** `PH4-AC-3`'s baseline exists in one place and names which capabilities are advertised.

**Affected code:** `NEW` `docs/proposals/RECONCILIATION_SEARCH_AND_BROWSE/RECONCILIATION_SEARCH_AND_BROWSE_PHASE_4_BASELINE.md`; `docs/proposals/RECONCILIATION_SEARCH_AND_BROWSE/RECONCILIATION_SEARCH_AND_BROWSE_PHASE_PLAN.md`.

**Dependencies:** Areas 1–4.

**Tasks:**

* [x] `T5.1` **Change:** Write the baseline record.
  * **Target:** `NEW` `..._PHASE_4_BASELINE.md`.
  * **Current → required:** Measurements exist in scratch files only. Required: the service pair, environment name, fixture, measurement method, and every measurement `VM-13` names.
  * **Implementation:** Record search and Browse median and p95 per type at loopback and at the delay levels run, decision and New-decision time and interaction counts, request counts, and preview and normalization invocation counts. State the measured round-trip envelope and label the loopback figures as a lower bound.
  * **Constraints:** These are absolute descriptions of this workflow, not a comparison against the previous one. `PH4-AC-3` says "without claiming improvement over the old workflow", so do not measure or report a before/after difference.
  * **Validation:** `V-11`.

How each `VM-13` measurement is taken:

| Measurement | Method |
| --- | --- |
| Search and Browse median and p95 | `V-1` at loopback, and repeated at each delay level |
| Time per decision | Wall clock from staging a decision to the save response, averaged over the run |
| Time per New decision | Same, for rows marked New and exported |
| Interactions per decision | Count of explicit reviewer actions along the keyboard path: focus row, enter query, submit search, stage. The documented shortcut path yields four |
| Interactions per New decision | Same, substituting the New action |
| Request counts | Requests issued per decision and per New decision, counted by the harness |
| Preview and normalization invocations | Count of `ShapeShift preview for entity` lines in `logs/app.log` across the run. Verified measurable: one preview request plus one save added two lines |

* [x] `T5.2` **Change:** Record per-type advertisement.
  * **Target:** The baseline record and the phase plan's Phase 4 section.
  * **Current → required:** The phase plan still reads as not-yet-ready and names the environment as blocking. Required: readiness updated, the environment named, and each capability marked advertised or withheld per type with the reason.
  * **Implementation:** Update the Phase 4 `Readiness` and handoff to record `pilot-recon-2026-11-20`, and list each capability's decision.
  * **Constraints:** Keep the shipped Authority configuration's flags `false`; advertisement is a recorded decision about the pilot, not a change to shipped defaults.
  * **Validation:** `V-12`.

**Completion evidence:** The baseline document answers every `VM-13` item, and the phase plan records the environment and per-capability decisions.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
| --- | --- | --- | --- |
| `PH4-AC-1` | `T2.1`, `T2.2`, `T3.1`, `T4.1`, `T4.3` | `V-5`, `V-6`, `V-7`, `V-8`, `V-10` | Per-type projection, limit, verification, and browser results, with independent advertisement |
| `PH4-AC-2` | `T4.2`, `T4.3` | `V-9`, `V-10` | Paired run over 100 rows covering first-time review, conflicts, resume, outage, real IDs, unchanged source identity, and no retrieval writes |
| `PH4-AC-3` | `T1.1`, `T1.2`, `T5.1` | `V-1`, `V-2`, `V-3`, `V-11` | Baseline document with every required measurement and the measurement method |

## Validation And Testing

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
| --- | --- | --- | --- | --- | --- |
| `V-1` | Search measurement harness | `.venv/bin/python scripts/pilot/measure_selection.py --runs 100 --label pilot-recon-2026-11-20` | `PH4-AC-3` | Per-type median and p95 printed; exit 0 within budget, non-zero above it | Pass: median 59.0 ms and 59.7 ms, p95 68.3 ms and 69.2 ms over 100 runs each on 2026-11-20 from the tracked script, exit 0 |
| `V-2` | Harness negative case | Same command with `--budget-ms 10` | `PH4-AC-3` | Non-zero exit with `FAIL` per type | Pass: exit 1 with `FAIL` for both types; the default budget exits 0 |
| `V-3` | Delay proxy applies delay | Start the proxy at 50 ms one-way and compare a single search against the direct path | `PH4-AC-3` | Measurably slower than direct and still succeeds | Pass: single request 436 ms through the proxy against about 60 ms direct |
| `V-4` | Harness documentation links | `bash scripts/ci/check_doc_links.sh` | Documentation | Links valid | Pass on 2026-11-20 after adding `scripts/pilot/README.md` |
| `V-14` | Harness unit tests | `.venv/bin/python -m pytest scripts/tests/pilot -q` | Tooling correctness | Tests pass | Pass: 17 tests on 2026-11-20 |
| `V-5` | Live projection per type | Browse both types through the backend; record rows, bytes, `completeness` | `PH4-AC-1` | `completeness: complete` with recorded sizes | Pass: 156 rows / 32,675 bytes and 266 rows / 38,211 bytes through the backend; the Authority alone returns 29,336 and 29,699 bytes for the same rows |
| `V-6` | Too-large path per type | Lower `browse_max_rows` below the row count, request the list, then the byte limit, then restore | `PH4-AC-1` | 409 `too_large_to_browse` with no items; list succeeds after restore | Pass: `browse_max_rows: 100` and `browse_max_bytes: 20000` each produced 409 `RECORD_SELECTION_TOO_LARGE` with no items for both types; after restore both lists returned 200 with 156 and 266 items |
| `V-7` | Verification and export per type | Save valid, unknown, and wrong-type decisions; export each | `PH4-AC-1` | `verified` for the valid link; blocked export with no sidecar write for the others | Pass: both types exported one `verified` link; an unknown ID blocked export with `DEPENDENCY_ERROR` and no sidecar; a wrong-type URI was rejected at save with `invalid_reference` before export was reached |
| `V-8` | Browser checks both types | Scripted manual pass in a supported browser against `http://127.0.0.1:8026`, following the `T4.1` checklist | `PH4-AC-1` | Search, exact ID, Browse filter/sort, keyboard staging, New, Save versus Export, and reload behaviour pass for both types | Pass on 2026-11-21: all checklist checks passed for `feature_type` and `country`; no deviations recorded |
| `V-9` | Fixture shape | Assert 100 rows per type, about 90 New, compound keys, duplicate labels | `PH4-AC-2` | Fixture matches the required shape | Pass: 100 rows per type, 10 matchable and 90 New, compound keys of width 2 on both types, six duplicate labels per type across distinct keys |
| `V-10` | Paired end-to-end run | Execute the `VM-12` scenario list | `PH4-AC-1`, `PH4-AC-2` | All scenarios observed, with conflicts and outage recorded | Pass: 100 rows per type reviewed from a blank catalog; 10 accepted and 90 New each; 20 links exported `verified`; 180 New approvals recorded; one `row_changed` and one `duplicate_draft` rejection; Authority outage left search at 503 while New saves and New-only export still succeeded; source identity unchanged |
| `V-11` | Baseline completeness | Review the baseline document against the `VM-13` checklist | `PH4-AC-3` | Every named measurement present with method and environment | Pass on 2026-11-21: baseline records the environment, fixture, Search and Browse medians/p95 at loopback and both delayed RTT levels, decision times, interactions, request counts, and preview/normalization log count |
| `V-12` | Phase plan updated | Review the Phase 4 section | `PH4-AC-1` | Environment named, readiness current, per-capability decisions recorded | Pass on 2026-11-21: Phase 4 names the pilot, links the baseline, records each of the five capability decisions for both types, and keeps shipped flags false |
| `V-13` | No retrieval writes | Compare target table counts and SIMS state before and after a retrieval and review session | `PH4-AC-2` | Counts and state unchanged | Pass: `authority.feature_type` 156, `authority.feature` 2,669, `authority.location` 3,404, `public.tbl_locations` 3,404 before and after; an attempted insert failed with `permission denied for view feature_type`. The snapshot has no SIMS identity tables, so SIMS state was unchanged vacuously |

`V-13` uses the `sead_ro` role, which already makes writes fail rather than succeed. Record the comparison anyway, because `PH4-AC-2` asks for the observation, not only the permission.

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Search measurement harness | `scripts/pilot/measure_selection.py` | `T1.1` | `V-1`, `V-14` pass |
| Latency-injection proxy | `scripts/pilot/delay_proxy.py` | `T1.2` | `V-3` passes |
| Harness documentation | `scripts/pilot/README.md` | `T1.3` | `V-4` passes |
| Harness tests | `scripts/tests/pilot/test_measure_selection.py` | `T1.1`, `T1.2` | `V-14` passes |
| Projection and limit record | Baseline document | `T2.1`, `T2.2` | `V-5`, `V-6` pass |
| Verification and export record | Baseline document | `T3.1` | `V-7` passes |
| Browser harness | Pilot environment, supported container | `T4.1` | `V-8` passes |
| Pilot fixture | Pilot environment project | `T4.2` | `V-9` passes |
| Paired run record | Baseline document | `T4.3` | `V-10` passes |
| Baseline document | `docs/proposals/RECONCILIATION_SEARCH_AND_BROWSE/RECONCILIATION_SEARCH_AND_BROWSE_PHASE_4_BASELINE.md` | `T5.1` | `V-11` passes |
| Phase plan update | `..._PHASE_PLAN.md`, Phase 4 section | `T5.2` | `V-12` passes |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| 1 — Repeatable measurement harness | Done | None | Scripts, guide, and 17 unit tests are tracked; loopback median 59.0 ms and 59.7 ms, p95 68.3 ms and 69.2 ms |
| 2 — Projection and limit checks | Done | Area 1 | 156 rows / 32,675 bytes and 266 rows / 38,211 bytes; both limits rejected both types with 409 and were restored |
| 3 — Verification and export | Done | Area 2 | `verified` for both types; unknown ID blocks export; wrong-type URI rejected at save |
| 4 — Fixture and browser checks | Done | Areas 2–3 | `vm12-fixture` passes its shape check and paired run; browser checklist passed for both types on 2026-11-21 with no deviations |
| 5 — Baseline and advertisement | Done | Areas 1–4 | Baseline and per-capability pilot decisions are recorded; shipped Authority Service flags remain false |

## Definition Of Done

- [x] Every `PH4-AC-*` criterion has implementation and validation evidence, and `V-1`–`V-14` have recorded outcomes.
- [x] Both pilot types have recorded projection, limit, verification, and browser results.
- [x] The paired run covers first-time review, atomic and conflicting saves, resume, outage behavior, real exported IDs, New approvals, and unchanged source identity.
- [x] A retrieval and review session is recorded as producing no target or SIMS writes.
- [x] The baseline document names the service pair, environment, fixture, measurement method, and every `VM-13` measurement.
- [x] Each capability per type is recorded as advertised or withheld with its reason, and the shipped Authority configuration keeps every pilot flag `false`.
- [x] Deviations, withheld capabilities, and follow-up work are documented.
- [x] No unresolved question affects the advertisement decision.

## Risks And Open Questions

- **Round-trip coverage.** The delay proxy models network latency on one host, not an internet path. It does not reproduce packet loss, jitter, or a real WAN hop. The measured envelope of about 385 ms round-trip is the honest claim; a staging-to-staging measurement would replace it and should be recorded when the deployment lands.
- **Country source realism.** The `country` specification's source queue holds every place type from `arbodat-pilot`, of which only the `Staat` rows can match. Filtering to countries needs a custom query source, which fails today with `KeyError: 'recon_temp'`. `VM-12`'s fixture should model country source rows directly rather than depend on that fix.
- **Browser access.** The manual browser checklist passed for both types on 2026-11-21; forwarding port `8026` is no longer a blocker. Automated Playwright still needs a supported browser runtime, but automation is not a phase gate.
- **Per-decision timing.** `PH4-AC-3` asks for time and interactions per decision and per New decision, plus preview and normalization invocation counts. These describe the new workflow only; the phase explicitly excludes a comparison with the previous workflow, so no before/after measurement is planned.
- **Snapshot drift.** `sead_pilot_recon` is a 2026-11-20 copy. Row counts and sizes in the baseline describe that snapshot, not current staging or production.
