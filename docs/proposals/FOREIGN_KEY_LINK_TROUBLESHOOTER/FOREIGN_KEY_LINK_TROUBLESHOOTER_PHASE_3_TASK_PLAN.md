# Foreign-Key Link Troubleshooter — Phase 3 Task Plan

Source: [Foreign-Key Link Troubleshooter](FOREIGN_KEY_LINK_TROUBLESHOOTER.md), [Phase 3: Calculate trials and A-row diagnostics](FOREIGN_KEY_LINK_TROUBLESHOOTER_PHASE_PLAN.md). Prerequisite: [Phase 2 task plan](FOREIGN_KEY_LINK_TROUBLESHOOTER_PHASE_2_TASK_PLAN.md).

## Phase Summary

**Goal:** Compare key-pair-only trials on the reproduced link inputs and explain each A row's matches, losses, and expansion.

**Plan readiness: Validated.** Phase 2 is committed. The approved budget counts estimated output rows for both the production merge and diagnostic left merge, using production key coercion and null behavior. The backend setting `LINK_TRIAL_MAX_OUTPUT_ROWS` defaults to `1,000,000` and is configurable through `SHAPE_SHIFTER_LINK_TRIAL_MAX_OUTPUT_ROWS`. A result exactly at the limit is allowed; a larger estimate returns `incomplete` with a reason and no totals or row details.

**Acceptance criteria**

1. [x] `PH3-AC-1` (from `P-AC-3`) Valid alternative key pairs use baseline A and B and return link-only results without changing fixed FK settings or saved data.
2. [x] `PH3-AC-2` (from `P-AC-4`) Each reported A row has an identity or temporary input position, ordered keys, match status, remote match count under the resolved null policy, and output-row contribution. Complete totals separately count input A, output, unmatched A, and multiply matched A, including cancelling loss and expansion.
3. [x] `PH3-AC-3` (from `P-AC-5`) Missing or incompatible keys and constraint violations fail clearly; a comparison exceeding the computation limit never reports complete totals.

**Fixed constraints:** Inner and left joins only; A/B, join type, constraints, and saved project remain unchanged. Baseline and trial use the same pre-link A and processed B. No API route, browser flow, persistent trial, or project-wide validation is part of this phase. `VM-4` and `VM-5` from the phase plan are covered by the checks below.

## Repository Findings

**Repository basis:** `feature/foreign-key-link-troubleshooter` at `168e8149`, inspected 2026-11-02. At the validated planning baseline, the Phase 2 service and tests were tracked and clean, and this task plan was the only untracked file. Existing Graphify output supplied navigation and was checked against current source and tests.

| Evidence | Finding | Planning implication |
| --- | --- | --- |
| `backend/app/services/link_baseline_service.py::LinkBaselineService.build_baseline`, `LinkBaselineResult` | Reproduced results alone carry `local_rows` and `remote_rows`; failures have no input frames. The service maps and resolves the saved FK privately, then discards that context. | Gate trials on `status == "reproduced"` and make the resolved Core project/FK available to the trial code in memory without a second, possibly different project load. Do not serialize frames or Core config. |
| `src/transforms/link_resolution.py::resolve_row_count_issue`, `src/model.py::ForeignKeyConfig` | Saved FK identity includes index and a signature of ordered keys, join type, deferral, and constraints; `local_keys` and `remote_keys` use `unique`. | Keep the original FK untouched. Validate ordered, nonempty pairs before constructing an independent trial FK; do not silently discard repeated selections or infer an FK from A/B alone. |
| `src/transforms/link.py::ForeignKeyLinker.link_foreign_key`, `_resolve_fk_runtime_options` | The production linker builds merge columns, coerces keys via its merge helper, resolves lookup-specific null behavior, checks constraints, and collects selected-link issues in its validator. | Use the production linker on frame copies with only the key lists changed. Do not use the quick Test Join, which performs a different merge. Take findings only from the selected trial link. |
| `src/transforms/utility.py::merge_with_nonmatching_null_keys`, `src/specifications/constraints.py::ForeignKeyConstraintValidator` | The helper coerces compatible numeric/string keys and uses distinct null sentinels when matches are prohibited. The validator can raise before or after merging, and a row-count warning depends on net change. | Use the same resolved null policy for a separate, position-preserving diagnostic left merge; do not infer missing A rows from net output counts or from a nullable remote ID. Surface pre/post-merge failures explicitly. |
| `backend/tests/services/test_link_baseline_service.py::run_production`, `tests/transforms/test_link.py::test_null_key_components_match_only_when_null_keys_equal_is_enabled` | Existing fixtures compare actual production links, preceding/deferred FKs, duplicate B rows, and partially null compound keys. | Reuse the production-observation pattern and extend cases to cancelled loss/expansion, both join types, both null policies, invalid selections, and budget boundaries. |
| `backend/app/services/shapeshift_service.py::preview_entity`, `backend/app/utils/caches.py::ShapeShiftCache` | The completed-entity preview can be sampled and cached. | Trial code must not read or write preview/production caches or use their frames for totals. |

## Scope

**In scope:** An internal, read-only trial service, an in-memory Phase 2 context handoff, selected-link counts/findings, A-row diagnostics, explicit invalid/failed/incomplete states, and focused service tests.

**Out of scope:** Routes, authorization wiring, browser filtering/paging, persistence, the general FK editor, and the existing Test Join (Phase 4 or unrelated work). No production pipeline or saved FK configuration changes.

**Affected layers:** `backend/app/core/config.py`, `backend/app/services/`, `backend/tests/services/`, `backend/tests/test_config.py`, and `docs/OPERATIONS.md`. The service may use Core project, FK, merge, and validator types; Core must not depend on backend models. The Phase 4 API must serialize only bounded row details, not the in-memory frames or config.

## Work Breakdown

### Area 1: Hand off reproducible inputs and accept key pairs

**Objective:** A trial has one current resolved saved FK, the same full A/B inputs as its baseline, and only a validated pair of ordered key lists.

**Affected code:** `backend/app/services/link_baseline_service.py::LinkBaselineResult`, `LinkBaselineService.build_baseline`; `backend/app/services/link_trial_service.py` (`NEW`); `backend/tests/services/test_link_trial_service.py` (`NEW`).

**Dependencies:** Phase 2 output is committed; the budget and incomplete-result contract are approved.

**Tasks:**

* [x] `T1.1` **Change:** Expose the resolved Core project and saved FK to internal trial code only when the baseline reproduces; keep existing baseline status/reason and read-only behavior.
  * **Target:** `backend/app/services/link_baseline_service.py::LinkBaselineResult`, `LinkBaselineService.build_baseline`.
  * **Current → required:** Only frames and FK index survive the baseline call → a single-load context sufficient to run the saved FK through the linker without mapping a second project snapshot.
  * **Implementation:** Add private in-memory context to the reproduced result or an equivalent internal return value; never include it in a response model or cache. Continue returning no trial inputs for stale, failed, or ineligible baselines.
  * **Constraints:** Do not change the recorded warning, original project, or its saved FK.
  * **Validation:** `V-1`, `V-4`, `V-6`; test the existing stale and constraint-failed baseline cases.
* [x] `T1.2` **Change:** Validate equally sized, nonempty, ordered, distinct key lists against actual A and B frame columns and construct a copied FK differing only in `local_keys` and `remote_keys`.
  * **Target:** `backend/app/services/link_trial_service.py` (`NEW`).
  * **Current → required:** No trial service exists → invalid selections return a named error and cannot reach the merge; valid selections preserve A/B, `how`, deferral, extra columns, and full constraints.
  * **Implementation:** Accept the reproduced baseline and trial key lists; reject missing, repeated, length-mismatched, or non-string key selections before invoking the linker. Never rewrite the saved configuration or mutate the baseline frames.
  * **Constraints:** Do not treat business `keys` or a remote `public_id` as automatically interchangeable with selected merge columns.
  * **Validation:** `V-1`, `V-4`.

**Completion evidence:** Valid selections reach a copied FK with ordered pairs; invalid or non-reproduced inputs have no successful trial result.

### Area 2: Run the production link and account for each A row

**Objective:** Complete trial counts and selected-link findings agree with the production link, while unmatched and multiply matched rows remain visible independently of net change.

**Affected code:** `backend/app/core/config.py::Settings`, `backend/app/services/link_trial_service.py` (`NEW`), `backend/tests/services/test_link_trial_service.py` (`NEW`), and `backend/tests/test_config.py`.

**Dependencies:** Area 1 and the approved pre-merge limit.

**Tasks:**

* [x] `T2.1` **Change:** Run the trial FK with `ForeignKeyLinker.link_foreign_key` on copies of the reproduced A/B frames, using the baseline's saved Core project and linking pass. Return output count and only that linker's validation issues; convert constraint and incompatible-merge errors to named failures without complete totals.
  * **Target:** `backend/app/services/link_trial_service.py` (`NEW`).
  * **Current → required:** Phase 2 links only the configured FK → trial keys are evaluated with identical production merge and constraint rules.
  * **Implementation:** Preserve the original FK and baseline counts separately; obtain the trial count from the linked frame and issues from its selected validator. Do not copy old warning metadata as new findings.
  * **Constraints:** Use neither preview samples nor an independent merge for the authoritative output count.
  * **Validation:** `V-2`, `V-4`, `V-6`.
* [x] `T2.2` **Change:** Derive A-row remote match counts through a diagnostic left join of the full baseline inputs with unique temporary A/B positions and the linker's resolved null policy, then aggregate by A position.
  * **Target:** `backend/app/services/link_trial_service.py` (`NEW`).
  * **Current → required:** The production output omits unmatched A for inner joins → every input A row gets an ordered position, original key values, status, match count, and contribution (`matches` for inner; `max(1, matches)` for left).
  * **Implementation:** Use the production merge helper's coercion/null treatment for narrow key/position data; distinguish a B match by its temporary B position, not its nullable ID. Assert the sum of contributions equals the authoritative linked-frame count; fail explicitly if not. Count unmatched and multiply matched A independently of the net output change.
  * **Constraints:** Never mistake a pandas index or `system_id` duplicated by an earlier link for unique A identity; retain the temporary input position. Diagnostics do not alter source frames or production data.
  * **Validation:** `V-2`, `V-3`, `V-4`.

**Completion evidence:** Actual production output/finding parity and per-position contributions hold for inner and left joins, null-policy variants, duplicate B keys, and cancelling loss/expansion.

### Area 3: Enforce the approved budget and report failures

**Objective:** No oversized or failed comparison is labeled complete.

**Affected code:** `backend/app/services/link_trial_service.py` (`NEW`); `backend/tests/services/test_link_trial_service.py` (`NEW`).

**Dependencies:** Areas 1–2; the approved output-row limit and incomplete-result contract.

**Tasks:**

* [x] `T3.1` **Change:** Enforce the configured output-row budget before materializing either the production or diagnostic join.
  * **Target:** `backend/app/core/config.py::Settings.LINK_TRIAL_MAX_OUTPUT_ROWS`; `backend/app/services/link_trial_service.py` (`NEW`).
  * **Current → required:** No trial computation cap exists → the service estimates complete production and diagnostic output rows before merging and refuses work whose larger estimate exceeds the configured limit.
  * **Implementation:** Count normalized key frequencies using the production key coercion and resolved null behavior. Estimate the full production join and diagnostic left join without expanding joined rows. Use the larger estimate. The positive integer setting defaults to `1,000,000`, is configurable through `SHAPE_SHIFTER_LINK_TRIAL_MAX_OUTPUT_ROWS`, and allows an estimate equal to the limit. An estimate above the limit returns `incomplete` with a reason and no totals or row details.
  * **Constraints:** Check the budget before either merge; do not treat a displayed-row cap or an average duplication score as a complete cardinality estimate.
  * **Validation:** `V-5`, `V-8`.
* [x] `T3.2` **Test:** Assert that invalid pairs, incompatible key dtypes, pre/post-merge constraint violations, and over-budget cases return named failures or the approved incomplete status; successful results alone carry complete totals and A-row details. Verify no saved project, production cache, or baseline frame changes.
  * **Target:** `backend/tests/services/test_link_trial_service.py` (`NEW`).
  * **Current → required:** No trial failure or budget tests exist → exact-below, exact-at, and above-limit cases and read-only behavior are covered.
  * **Constraints:** Use small fixture inputs and a low injected setting for boundary tests; do not allocate an oversized join in the test.
  * **Validation:** `V-4`, `V-5`.

**Completion evidence:** Limit-boundary tests prove both joins are bounded and noncomplete results contain no complete-count claim.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Implementation and execution evidence |
| --- | --- | --- | --- |
| `PH3-AC-1` (from `P-AC-3`) | `T1.1`, `T1.2`, `T2.1`, `T3.2` | `V-1`, `V-2`, `V-4`, `V-6` | Baseline context handoff, copied key-only FK, selected-link results, and read-only behavior are covered by 23 trial tests and 96 regression tests; all listed checks pass. |
| `PH3-AC-2` (from `P-AC-4`) | `T2.1`, `T2.2` | `V-2`, `V-3` | Production parity, row-level diagnostics, null policies, and cancellation cases are covered by the 23 passing trial tests. |
| `PH3-AC-3` (from `P-AC-5`) | `T1.2`, `T2.1`, `T3.1`, `T3.2` | `V-4`, `V-5`, `V-8`, `V-9` | Failure and budget behavior pass in the trial tests; all 10 config tests pass; the operations table documents the environment override and default. |

`VM-4`: `V-1`–`V-3`; `VM-5`: `V-3`–`V-6`, `V-8`, `V-9`.

## Validation And Testing

Run from the worktree root with the repository `.venv`; `-o addopts=''` disables the repository-wide parallel pytest default for focused runs.

| ID | Check and target | Command or method | Covers | Expected result | Baseline (2026-11-02) | Execution result |
| --- | --- | --- | --- | --- | --- | --- |
| `V-1` | Valid/missing/repeated/mismatched ordered keys and non-reproduced baseline in `backend/tests/services/test_link_trial_service.py` (`NEW`) | `.venv/bin/pytest -o addopts='' -q backend/tests/services/test_link_trial_service.py` | `PH3-AC-1`, `PH3-AC-3` | Only valid ordered pairs reach a copied FK and no original frame/config changes | Not run: new file does not exist | **Pass:** 23 focused trial tests, exit 0 |
| `V-2` | Production parity in the same `NEW` file: inner/left, both null policies, partial-null compound keys, duplicate B, and preceding/deferred links using the Phase 2 `run_production` pattern | Same focused command as `V-1` | `PH3-AC-1`, `PH3-AC-2` | Output counts and link-only issues match production; diagnostics match actual A-to-B pairs | Not run: new file does not exist | **Pass:** 23 focused trial tests, exit 0 |
| `V-3` | Cancellation case in the same `NEW` file: two A rows, one unmatched and one with two B matches; repeat for both join types | Same focused command as `V-1` | `PH3-AC-2` | Inner: input 2, output 2, unmatched 1, multiply matched 1; left: input 2, output 3, unmatched 1, multiply matched 1; each row's contribution agrees | Not run: new file does not exist | **Pass:** 23 focused trial tests, exit 0 |
| `V-4` | Invalid/constraint failures and immutability in the same `NEW` file, including nonnumeric strings against numeric keys, strict-null rejection, and no cache calls | Same focused command as `V-1` | `PH3-AC-1`, `PH3-AC-3` | Named failures have no complete totals; saved project, cache, and input frames unchanged | Not run: new file does not exist | **Pass:** 23 focused trial tests, exit 0 |
| `V-5` | Both-join budget checks in the same `NEW` file: below, at, and above the configured output-row limit | Same focused command as `V-1`; assert the exact boundary and that over-limit work does not call either merge | `PH3-AC-3` | Estimates at or below the limit proceed; estimates above it return `incomplete` without totals/details or materializing either merge | Not run: trial service does not exist | **Pass:** 23 focused trial tests, exit 0 |
| `V-6` | Existing baseline, linker, and resolution regressions | `.venv/bin/pytest -o addopts='' -q backend/tests/services/test_link_baseline_service.py tests/transforms/test_link.py tests/transforms/test_link_resolution.py backend/tests/services/test_link_trial_service.py` after implementation; omit the `NEW` file for today's baseline | `PH3-AC-1` and existing behavior | All tests pass | **Pass:** 73 tests in the three existing files, exit 0 (2026-11-02) | **Pass:** 96 tests, exit 0 |
| `V-7` | Formatting and type checking for changed Python | `.venv/bin/black --check backend/app/core/config.py backend/app/services/link_baseline_service.py backend/app/services/link_trial_service.py backend/tests/test_config.py backend/tests/services/test_link_baseline_service.py backend/tests/services/test_link_trial_service.py`; `.venv/bin/isort --check-only backend/app/core/config.py backend/app/services/link_baseline_service.py backend/app/services/link_trial_service.py backend/tests/test_config.py backend/tests/services/test_link_baseline_service.py backend/tests/services/test_link_trial_service.py`; `.venv/bin/pyright --pythonpath .venv/bin/python --threads 2 backend/app/core/config.py backend/app/services/link_baseline_service.py backend/app/services/link_trial_service.py` | Quality | Exit 0; record existing diagnostics separately | Not run: trial service does not exist | **Pass:** Black/isort clean; Pyright 0 errors, 0 warnings, 0 informational diagnostics |
| `V-8` | Runtime setting default, environment override, and positive-value validation in `backend/tests/test_config.py` | `.venv/bin/pytest -o addopts='' -q backend/tests/test_config.py` | `PH3-AC-3` | Default is `1,000,000`; `SHAPE_SHIFTER_LINK_TRIAL_MAX_OUTPUT_ROWS` overrides it; zero or negative values are rejected | **Pass:** 6 existing tests, exit 0 (2026-11-02) | **Pass:** 10 tests, exit 0 |
| `V-9` | Operations documentation for the output-row setting | Confirm the `docs/OPERATIONS.md` runtime-settings table names the exact environment variable and `1,000,000` default | `PH3-AC-3` | Operators can find the override and its default | Not run: setting not implemented | **Pass:** targeted check confirms the variable and default are documented |

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Reproduced baseline's internal trial context | `backend/app/services/link_baseline_service.py::LinkBaselineResult` | `T1.1` | `V-1`, `V-4`, `V-6` |
| Baseline context handoff regression | `backend/tests/services/test_link_baseline_service.py` | `T1.1` | `V-6` |
| Read-only trial, diagnostics, and budget logic | `backend/app/services/link_trial_service.py` (`NEW`) | `T1.2`, `T2.1`, `T2.2`, `T3.1` | `V-1`–`V-5`, `V-7` |
| Trial parity, edge-case, and read-only tests | `backend/tests/services/test_link_trial_service.py` (`NEW`) | `T1.2`, `T2.1`, `T2.2`, `T3.2` | `V-1`–`V-6` |
| Configurable output-row limit | `backend/app/core/config.py::Settings.LINK_TRIAL_MAX_OUTPUT_ROWS` | `T3.1` | `V-7`, `V-8` |
| Output-row setting tests | `backend/tests/test_config.py` | `T3.1`, `T3.2` | `V-8` |
| Operations configuration reference | `docs/OPERATIONS.md` | `T3.1` | `V-9` |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Hand off inputs and accept pairs | Complete | Phase 2 output committed | Baseline handoff and ordered-key validation pass `V-1`, `V-4`, and `V-6` |
| Area 2: Run link and account for A | Complete | Area 1; approved output-row budget | Production parity and per-A diagnostics pass `V-2`–`V-4`, `V-6` |
| Area 3: Enforce budget | Complete | Areas 1–2; approved setting and incomplete-result contract | The configurable `1,000,000`-row default and exact-limit behavior pass `V-5`, `V-8`, and `V-9` |

## Definition Of Done

* [x] Phase 2 output is retained and `PH3-AC-1`–`PH3-AC-3` have passing `T*`/`V-*` evidence.
* [x] All three areas and deliverables are complete; `V-1`–`V-9` pass or deviations are recorded.
* [x] Actual inner/left, null-policy, and constraint behavior remains covered by production parity and regression tests.
* [x] Complete totals never depend on the displayed subset; no trial writes project or production cache data.
* [x] The configurable output-row limit defaults to `1,000,000`, accepts a positive environment override, and is tested below, at, and above the limit.
* [x] Over-limit trials return an incomplete reason without totals or row details.
* [x] No blocking repository discrepancy was found; the production linker and planned scope were preserved.

## Risks And Open Questions

- **Row-count limit is not a byte limit.** The configured cap bounds the number of rows materialized, not memory per row. Keep the Phase 4 response-size limit separate and do not describe this setting as a strict memory limit.
