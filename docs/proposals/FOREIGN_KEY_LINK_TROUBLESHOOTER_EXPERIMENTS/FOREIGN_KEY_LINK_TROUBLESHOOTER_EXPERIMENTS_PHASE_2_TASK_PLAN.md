# Foreign-Key Link Troubleshooter Experiments — Phase 2 Task Plan

## Phase Summary

**Phase:** 2 — Production Trials and Bounded Comparison Contract. Sources: [approved proposal](./FOREIGN_KEY_LINK_TROUBLESHOOTER_EXPERIMENTS.md), [phase plan, Phase 2](./FOREIGN_KEY_LINK_TROUBLESHOOTER_EXPERIMENTS_PHASE_PLAN.md#phase-2-production-trials-and-bounded-comparison-contract), and [Phase 1 task plan](./FOREIGN_KEY_LINK_TROUBLESHOOTER_EXPERIMENTS_PHASE_1_TASK_PLAN.md).

**Readiness: Validated.** The three decisions the phase plan required are recorded in [Recorded Decisions](#recorded-decisions) as `D1`–`D13` and checked against the current production resolver. Phase 1's context contract is present and its focused tests pass. Every target below is an existing file or a new symbol in an existing file, and every validation row has an executable command, so implementation can start.

**Goal:** Compare the original link and each requested trial on one retained A/B snapshot, using production linking, then return exact full-input totals and findings with bounded exception detail. Preserve the existing stateless request and browser caller until the Phase 3 cutover. `VM-3` covers trial parity and no mutation; `VM-4` covers complete counts and bounded groups.

**Phase acceptance criteria**

1. [x] `PH2-AC-1` (from `P-AC-2`): Accept ordered key pairs, inner/left join choice, and only `allow_null_keys` and `null_keys_equal`; preserve all other FK settings and production defaults when omitted.
2. [x] `PH2-AC-2` (from `P-AC-1`, `P-AC-3`): Re-link one snapshot's retained inputs, keep baseline and trial totals/findings consistent with production behavior, and never label incomplete work complete.
3. [x] `PH2-AC-3` (from `P-AC-4`): Return exact full-input totals and exception counts, deterministic separately bounded unmatched and multiply matched A-row groups, and explicit row/detail truncation without correct A rows.
4. [x] `PH2-AC-4` (from `P-AC-8`): Leave retained inputs, saved projects, databases, and production caches unchanged.

## Repository Findings

**Repository basis:** `feature/foreign-key-link-troubleshooter-experiments` at `92627dc6`, inspected 2026-11-07. The worktree was clean before this document was created. Graphify was queried for the Phase 2 flow; its broad result was checked against the code and tests below.

| Evidence | Verified current behavior | Planning implication |
|---|---|---|
| `backend/app/services/link_experiment_context_store.py::LinkExperimentSnapshot`, `LinkExperimentDiagnostics`, `LinkExperimentContextStore.lookup_context` | Phase 1 retains a reproduced baseline (including A/B, resolved project and FK) and diagnostic status/counts for one owner and project; lookups enforce ownership and fixed expiry. It does not retain bounded baseline exception groups. | Use the stored snapshot, not another replay; retain only bounded baseline detail after diagnostics, if complete. |
| `backend/app/services/link_troubleshooter_service.py::open_context`, `read_context`, `_configured_diagnostics` | Opening runs configured-key diagnostics even when they fail; a context with incomplete diagnostics has no complete counts. There is no context trial operation. | Add a trial operation that looks up the owned context, uses its existing baseline, and leaves incomplete baseline status intact. |
| `backend/app/services/link_trial_service.py::run_trial`, `_diagnose_a_rows` | Deep-copies the saved FK to change only keys, checks output-row and projected-memory limits, links copies via `ForeignKeyLinker`, and calculates per-A match counts and output contributions. It accepts only key pairs, takes `how` and both null settings from the saved FK, and returns a diagnostic for every A row. | Accept only the `D10` tri-state overrides; keep production preflight, validation, and no-partial-totals failure behavior. Select exception rows after complete counts are known and bound both retained and serialized detail. |
| `src/model.py::ForeignKeyConstraints.allow_null_keys_is_explicit`; `src/transforms/link.py::_resolve_fk_runtime_options` | Omitted `allow_null_keys` is distinguishable from explicit `false`; an omitted setting can enable the lookup-enrichment null policy for some left joins. `null_keys_equal` also changes runtime behavior. | Never materialize inherited settings as explicit `false` in the trial FK (`D11`). Report the resolved behavior rather than a synthesized boolean (`D12`). |
| `backend/app/services/link_experiment_context_store.py::prepare_link_merge_keys`, `LinkMergeKeys.runtime_options`, `LinkMergeKeys.join_type` | The backend already receives the production-resolved `ForeignKeyRuntimeOptions` and join type for a candidate FK. | `D12` reads the effective runtime pair from `LinkMergeKeys`; do not re-implement or import the module-private resolver in the backend. |
| `src/model.py::ForeignKeyConstraints`; `tests/model/test_model.py::test_allow_null_keys_explicit_presence` | `allow_null_keys_is_explicit` distinguishes omission from explicit `false`; no equivalent accessor exists for `null_keys_equal`, and the existing omission test lives in `tests/model/test_model.py`. | Add a read-only `null_keys_equal_is_explicit` property for `D12`'s `source` field and extend the existing model test. No behavior change. |
| `src/transforms/link.py::_resolve_link_opts` | Production resolves an absent `how` to `inner`, and the trial service applies the same rule. | `D13` needs no behavior change; the response reports the effective join type with its source. |
| `backend/app/mappers/link_troubleshooter_mapper.py::to_context_response`, `_map_trial`, `_json_safe_scalar`; `backend/app/models/link_troubleshooter.py` | Context baseline includes status and counts but no exception groups; the stateless mapper serializes a server-selected page of A rows. Scalar conversion and issue messages have no aggregate response budget. | Introduce bounded context-response group models and a shared detail budget for rows, key values, and findings. Keep the legacy stateless mapper untouched until cutover. |
| `backend/app/api/v1/endpoints/link_troubleshooter.py`; `backend/app/api/v1/api.py` | Protected open/read/delete routes use `require_project(Action.READ)`, and the link router is already registered. Read returns 410 on expiry and conceals unknown/cross-owner contexts with 404. | Add a protected context trial route to the registered router; use the same owner/project lookup and expiry semantics, never the identifier alone. |
| `backend/tests/services/test_link_trial_service.py`, `test_link_troubleshooter_service.py`, `test_link_experiment_context_store.py`; `backend/tests/mappers/test_link_troubleshooter_mapper.py`; `backend/tests/api/v1/test_link_troubleshooter.py` | Existing tests cover inner/left counts, compound/null keys, invalid/over-limit trials, snapshot access, stateless paging, mapping, and protected routes. | Extend the existing files for the new contract, limits, authorization, and preservation checks. No new test file is needed. |

## Scope

**In scope:** Backend context trial settings, execution and explicit failures, original-baseline and trial exception summaries, bounded response serialization, a protected trial route, and focused service/mapper/API tests. A context-dependent trial must check current project read access and stored owner/project identity. Baseline and trial groups show only A positions with zero or multiple remote matches, with full counts even when detail is omitted. Bounds are 100 rows per group (`D1`), 256 bytes per key value (`D6`), 50 findings and 512 bytes per message (`D7`), and a 256 KiB detail budget per side (`D8`). One read-only Core property is added (`D12`); no link behavior changes.

**Out of scope:** UI controls, local paging implementation, automatic refresh, Reset, removal of the stateless route or its paging fields, saved-project edits, new join/constraint types, changing Core production link semantics, downstream validation, and the integrity inspector. Phase 3 owns the browser and breaking-contract cutover.

## Work Breakdown

The decisions in [Recorded Decisions](#recorded-decisions) unblock all three areas. The targets below are existing files; the trial route and typed context trial contract are **proposed**, not current endpoints or models. If implementation finds a conflicting repository contract, stop and report it rather than inventing a replacement design.

### Area 1: Add controlled trials on retained inputs

**Objective:** An authorized context trial produces a complete production-link result or a named failure, without replay or mutation.

**Affected code:** `backend/app/services/link_trial_service.py::LinkTrialService.run_trial`; `backend/app/services/link_troubleshooter_service.py::LinkTroubleshooterService`; `backend/app/models/link_troubleshooter.py`; `src/model.py::ForeignKeyConstraints`; `backend/tests/services/test_link_trial_service.py`; `backend/tests/services/test_link_troubleshooter_service.py`; `tests/model/test_model.py`.

**Dependencies:** Phase 1 context contract (verified); decisions `D10`–`D13` (recorded).

**Tasks:**

* [x] `T1.1` **Change:** Define a typed context trial request with ordered key pairs and optional `how`, `allow_null_keys`, and `null_keys_equal` overrides that distinguish inherited from explicit values.
  * **Target:** `backend/app/models/link_troubleshooter.py` (proposed context trial request model); `backend/app/services/link_trial_service.py::LinkTrialService.run_trial`.
  * **Current → required:** `run_trial` accepts only `local_keys` and `remote_keys`, and takes `how` and every constraint from the saved FK. It must accept the three `D10` controls and apply them with the `D11` copy rule.
  * **Implementation:** Declare the request model with `extra="forbid"` so unsupported fields fail validation. Treat a missing value as inherit, and an explicit `true`, `false`, or `inner`/`left` as an override. Start from `deepcopy(saved_fk.fk_cfg)`, assign only the overridden keys, and add a `constraints` mapping only when a null control is overridden. Leave inherited entries absent so production resolves them, and reject any join name other than `inner` or `left`.
  * **Constraints:** Preserve every other constraint, `extra_columns`, `drop_remote_id`, link pass, and identity. Never write `false` for an inherited control. No Core behavior change.
  * **Validation:** `V-1`; ordered compound keys, inner/left override, inherit versus explicit `false` and `true` for both controls on a left lookup enrichment, `null_keys_equal: true` combined with an `allow_null_keys` override, and an unsupported request field; compare matches and findings with production linking.
* [x] `T1.2` **Change:** Execute a requested trial against one owned snapshot without reopening it, and report the settings production resolved.
  * **Target:** `backend/app/services/link_troubleshooter_service.py::LinkTroubleshooterService` (proposed context trial operation); `backend/app/services/link_trial_service.py::LinkTrialService.run_trial`, `LinkTrialResult`; `src/model.py::ForeignKeyConstraints`; `backend/app/mappers/link_troubleshooter_mapper.py::_map_context_baseline`.
  * **Current → required:** Only open/read/close use the retained context; the stateless `run` rebuilds the baseline on each request. A context trial must never run on a different snapshot, and no response reports whether a control was inherited or overridden.
  * **Implementation:** Look up the context with principal and project locator before computing; use its `LinkBaselineResult` to re-link independent frame copies. Preserve the configured baseline diagnostic, even if incomplete. Fill `D12`'s per-control `requested`, `source`, and effective values from `LinkMergeKeys.runtime_options` and `LinkMergeKeys.join_type`, which already hold the production-resolved pair, for both the baseline and the trial. Add a read-only `null_keys_equal_is_explicit` property beside `allow_null_keys_is_explicit` so the baseline can report `source`. Reject missing, expired, and cross-owner contexts, keep row, memory, constraint, and preflight checks, and send no complete metrics on a blocked, invalid, oversized, or failed result.
  * **Constraints:** No re-normalization, writes, cache access, or trial history; do not treat fewer findings as better matching. Do not import or call `_resolve_fk_runtime_options` from the backend; it is module-private and already applied by `prepare_link_merge_keys`.
  * **Validation:** `V-1`, `V-2`, `V-5`, `V-6`: assert one reproduction across several trials despite changed sources, identical original baseline, incomplete-baseline trial availability, no trial after expiry, and `source: inherited` versus `explicit` for both the configured baseline and an overridden trial. Extend `tests/model/test_model.py::test_allow_null_keys_explicit_presence` for the new accessor.

**Completion evidence:** The authorized service can run several independent trials on one context and returns named non-success states without partial metrics.

### Area 2: Bound exception detail while preserving exact counts

**Objective:** A completed baseline and trial each report complete totals, findings, and both deterministic, separately capped exception groups in one bounded response.

**Affected code:** `backend/app/services/link_trial_service.py::LinkTrialService._diagnose_a_rows`; `backend/app/services/link_experiment_context_store.py::LinkExperimentDiagnostics`; `backend/app/services/link_troubleshooter_service.py::LinkTroubleshooterService._context_response`; `backend/app/mappers/link_troubleshooter_mapper.py`; `backend/app/models/link_troubleshooter.py`; `backend/app/core/config.py`; `backend/tests/mappers/test_link_troubleshooter_mapper.py`; `backend/tests/services/test_link_experiment_context_store.py`; `backend/tests/test_config.py`.

**Dependencies:** Area 1; decisions `D1`–`D9` (recorded).

**Tasks:**

* [x] `T2.1` **Change:** Keep exact full-input totals and exception counts while selecting deterministic, capped A-row detail.
  * **Target:** `backend/app/services/link_trial_service.py::LinkTrialService._diagnose_a_rows`, `LinkTrialResult`; `backend/app/services/link_experiment_context_store.py::LinkExperimentDiagnostics`.
  * **Current → required:** The diagnostic computes every A-row record and Phase 1 stores only baseline totals. Keep counts independent of output detail, and retain only capped baseline exception rows for later context reads.
  * **Implementation:** Normalize every A row's match count and output contribution, compute both full group counts from that pass, then select at most `LINK_EXPERIMENT_GROUP_ROW_CAP` rows per group in ascending `input_position` order (`D1`, `D3`). Report each group's `total_count`, `returned_count`, key values, remote match count, and output-row contribution. Inner-join unmatched rows contribute zero; left-join unmatched rows contribute one. Retain the same capped detail with the baseline diagnostics instead of a complete per-A listing, and preserve the findings from the production link.
  * **Constraints:** Rows with one match enter neither group. Multiple matches are not labeled violations. Derive counts from the existing key-only diagnostic join rather than a second joined output, and keep row and memory admission checks before merges.
  * **Validation:** `V-2`, `V-3`; cancelling loss and expansion, inner/left unmatched contributions, ascending position order with more rows than the cap, per-group caps applied independently, empty groups, and incomplete baseline with no totals or groups.
* [x] `T2.2` **Change:** Serialize exact metrics and bounded detail with explicit truncation labels.
  * **Target:** `backend/app/models/link_troubleshooter.py` (proposed group and detail models); `backend/app/mappers/link_troubleshooter_mapper.py::to_context_response`, `_map_context_baseline`, and the proposed trial-response mapper; `backend/app/core/config.py`.
  * **Current → required:** The stateless response pages A rows and sends unbounded key and finding text; context responses have no groups. Return both exception groups with `D9`'s truncation labels and no general A-row page.
  * **Implementation:** Add the `D1` setting and the `D5`–`D8` limits. Apply them per side over findings first, then the unmatched group, then the multiply-matched group. Convert values with the existing `_json_safe_scalar`, measure the UTF-8 bytes of that string form, cut at the last whole code point that fits `D6`, and leave a value that already fits unchanged. Report `row_cap_reached` and `budget_exhausted` separately, and keep totals, counts, and truncation metadata outside the budget. Use the existing `ValidationMapper` issue mapping. A non-complete trial or baseline must not acquire success-shaped totals or groups.
  * **Constraints:** Do not leak row values in errors or logs, and add no ellipsis suffix. Preserve the legacy stateless response mapping and its paging fields until Phase 3.
  * **Validation:** `V-3`, `V-6`; long and multibyte keys, values one byte below, exactly at, and one byte above `D6`, more than 50 findings, independent per-group truncation, aggregate exhaustion on one side without affecting the other, JSON-safe nulls, and counts unchanged by truncation.

**Completion evidence:** The complete original baseline and each completed trial expose exact counts plus bounded, labeled exception/finding detail; failed or incomplete work exposes no complete counts.

### Area 3: Expose and verify the context trial contract

**Objective:** A protected context trial endpoint returns the new typed comparison without changing the existing caller.

**Affected code:** `backend/app/api/v1/endpoints/link_troubleshooter.py`, `backend/app/models/link_troubleshooter.py`, `backend/app/mappers/link_troubleshooter_mapper.py`, `backend/tests/api/v1/test_link_troubleshooter.py`, `backend/tests/authorization/test_route_authentication.py`.

**Dependencies:** Areas 1–2 and decisions `D1`–`D13` (recorded).

**Tasks:**

* [x] `T3.1` **Change:** Add a context-scoped trial operation to the existing registered link router.
  * **Target:** `backend/app/api/v1/endpoints/link_troubleshooter.py` (proposed POST trial route); `backend/app/models/link_troubleshooter.py` (proposed trial response); `backend/tests/api/v1/test_link_troubleshooter.py`; `backend/tests/authorization/test_route_authentication.py`.
  * **Current → required:** Open/read/delete are read-protected, but no context trial route exists. Accept the `D10` controls and return complete comparison results, or an explicit non-success status.
  * **Implementation:** Use `require_project(Action.READ)`, forward the authorized principal and locator to the owned-context lookup, and reuse read-context 410 expiry and concealed 404 semantics. Return the retained baseline and the one requested trial tied to that context, including `D12`'s settings report. Reject invalid request shapes and unsupported controls with a validation error before any computation. Add the route to authorization coverage when the route inventory requires it. Keep stateless POST and its response compatible until Phase 3.
  * **Constraints:** No identifier-only access and no bypass of `LinkTroubleshooterService`. Do not re-open automatically after expiry; Phase 3 performs that client workflow.
  * **Validation:** `V-4`, `V-5`; authorized result, revoked read access, cross-owner and wrong-project identifiers, unknown and expired identifiers, invalid join and null controls, unknown request fields, failure payloads, and legacy POST preservation; run the authorization route check.

**Completion evidence:** API, service, and mapper agree on one context-bound trial contract; unauthorized or expired requests never execute a trial.

## Acceptance-Criteria Coverage

| Criterion | Source | Task IDs | Validation IDs | Expected evidence |
|---|---|---|---|---|
| `PH2-AC-1` | `P-AC-2` | `T1.1`, `T1.2`, `T3.1` | `V-1`, `V-4`, `V-6` | Only supported controls accepted; omitted versus explicit null settings match production defaults and are reported with their `source`. |
| `PH2-AC-2` | `P-AC-1`, `P-AC-3` | `T1.2`, `T2.1`, `T3.1` | `V-1`, `V-2`, `V-4` | Trials use one snapshot; production totals/findings agree; failures carry no complete metrics. |
| `PH2-AC-3` | `P-AC-4` | `T2.1`, `T2.2`, `T3.1` | `V-2`, `V-3`, `V-4`, `V-6` | Exact counts; two input-ordered groups capped at `D1` with `D5`–`D8` detail limits and explicit row/detail truncation. |
| `PH2-AC-4` | `P-AC-8` | `T1.2`, `T3.1` | `V-5` | Frames, saved project, and caches remain unchanged; no database writes. |

## Validation And Testing

The commands below are executable from the repository root. Baselines describe **existing** behavior only; planned Phase 2 assertions have not run. Re-run the listed focused tests after implementation; do not count a current pass as acceptance of new behavior.

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
|---|---|---|---|---|---|
| `V-1` | Production parity, controls, null default/explicit policy, constraints, row and memory limits in `backend/tests/services/test_link_trial_service.py` | `rtk .venv/bin/pytest backend/tests/services/test_link_trial_service.py -q` | `PH2-AC-1`, `PH2-AC-2`; `VM-3` | New and existing cases pass; inherit versus explicit values produce the same totals as production linking; unsupported request fields are rejected; no complete metrics on incomplete or failed trials. | Pass: included in focused service/API run; new cases not run (not written). |
| `V-2` | Fixed snapshot, baseline status, parity and exception counts in `backend/tests/services/test_link_troubleshooter_service.py` and `backend/tests/services/test_link_experiment_context_store.py` | `rtk .venv/bin/pytest backend/tests/services/test_link_troubleshooter_service.py backend/tests/services/test_link_experiment_context_store.py -q` | `PH2-AC-2`, `PH2-AC-3`; `VM-3`, `VM-4` | No repeat replay, same original baseline, deterministic exception counts, and no trial against expired/foreign context. | Pass: both existing files passed in focused runs; new cases not run. |
| `V-3` | Group and payload limits in `backend/tests/mappers/test_link_troubleshooter_mapper.py`, plus full-input diagnostics and retained baseline detail in the two service suites | `rtk .venv/bin/pytest backend/tests/mappers/test_link_troubleshooter_mapper.py backend/tests/services/test_link_troubleshooter_service.py backend/tests/services/test_link_trial_service.py -q` | `PH2-AC-3`; `VM-4` | 100 rows per group, 256 bytes per key value, 50 findings and 512 bytes per message, and the 256 KiB per-side budget all hold with explicit truncation labels, correct exact counts, and ascending input order. | Pass: existing files passed separately; new limit cases not run. |
| `V-4` | Trial route contract, authorization and expiry in `backend/tests/api/v1/test_link_troubleshooter.py`, plus route inventory in `backend/tests/authorization/test_route_authentication.py` | `rtk .venv/bin/pytest backend/tests/api/v1/test_link_troubleshooter.py backend/tests/authorization/test_route_authentication.py -q` | `PH2-AC-1`–`PH2-AC-3`; `VM-3`, `VM-4` | Protected route denies unauthorized calls and rejects invalid input; successful payload is typed/bounded. | Not run together: trial route does not exist; existing API tests passed separately; route inventory may have unrelated gaps noted in the Phase 1 plan. |
| `V-5` | Read-only and legacy-caller regression in `backend/tests/services/test_link_troubleshooter_service.py` and `backend/tests/api/v1/test_link_troubleshooter.py` | `rtk .venv/bin/pytest backend/tests/services/test_link_troubleshooter_service.py backend/tests/api/v1/test_link_troubleshooter.py -q` | `PH2-AC-4`; `VM-3` | Assert original DataFrames, saved project and caches unchanged, with read/write spies; existing stateless request still works. | Pass: existing files passed in focused run; new context-trial assertions not run. |
| `V-6` | Setting defaults, bounds, environment override, and the Core explicitness accessor | `rtk .venv/bin/pytest backend/tests/test_config.py tests/model/test_model.py -q` | `PH2-AC-1`, `PH2-AC-3` | `LINK_EXPERIMENT_GROUP_ROW_CAP` defaults to 100, rejects `0` and `1001`, and accepts an environment override; `null_keys_equal_is_explicit` distinguishes omission from explicit `false`. | Not run in this planning pass; Phase 1 recorded passing settings cases in `backend/tests/test_config.py`, and `tests/model/test_model.py` covers the existing `allow_null_keys_is_explicit` cases. New cases not written. |
| `V-7` | Formatting of changed backend and Core files | `rtk .venv/bin/black --check src/model.py backend/app/services/link_trial_service.py backend/app/services/link_troubleshooter_service.py backend/app/services/link_experiment_context_store.py backend/app/models/link_troubleshooter.py backend/app/core/config.py backend/app/mappers/link_troubleshooter_mapper.py backend/app/api/v1/endpoints/link_troubleshooter.py` and `rtk .venv/bin/isort --check-only src/model.py backend/app/services/link_trial_service.py backend/app/services/link_troubleshooter_service.py backend/app/services/link_experiment_context_store.py backend/app/models/link_troubleshooter.py backend/app/core/config.py backend/app/mappers/link_troubleshooter_mapper.py backend/app/api/v1/endpoints/link_troubleshooter.py` | Phase 2 quality | Both checks pass after implementation. | Not run: this phase has no code changes yet. |

## Execution Evidence

Implemented 2026-11-07 on `feature/foreign-key-link-troubleshooter-experiments` at `4cbb0fb4` with only the plan's named deliverables changed.

| Check | Command | Result |
|---|---|---|
| `V-1` | `.venv/bin/pytest backend/tests/services/test_link_trial_service.py -q` | Pass (40 tests). |
| `V-2` | `.venv/bin/pytest backend/tests/services/test_link_troubleshooter_service.py backend/tests/services/test_link_experiment_context_store.py -q` | Pass (54 tests). |
| `V-3` | `.venv/bin/pytest backend/tests/mappers/test_link_troubleshooter_mapper.py backend/tests/services/test_link_troubleshooter_service.py backend/tests/services/test_link_trial_service.py -q` | Pass. |
| `V-4` | `.venv/bin/pytest backend/tests/api/v1/test_link_troubleshooter.py backend/tests/authorization/test_route_authentication.py -q` | Pass for every API trial-route case. Two authorization inventory checks fail on a pre-existing gap: `POST /api/v1/projects/{project_name}/integrity-troubleshooter` is registered but absent from the inventory at `HEAD`, unrelated to this phase. |
| `V-5` | `.venv/bin/pytest backend/tests/services/test_link_troubleshooter_service.py backend/tests/api/v1/test_link_troubleshooter.py -q` | Pass; stateless POST is unchanged and context trials leave frames and saved FK data unchanged. |
| `V-6` | `.venv/bin/pytest backend/tests/test_config.py tests/model/test_model.py -q` | Pass; `LINK_EXPERIMENT_GROUP_ROW_CAP` default/bounds/environment and `null_keys_equal_is_explicit` covered. |
| `V-7` | `.venv/bin/black --check` and `.venv/bin/isort --check-only` on the changed files | Pass. |
| Type check | `uv run pyright` on the changed source files | Pass (0 errors, 0 warnings). |

No follow-up work is required for this phase. The unrelated integrity-route inventory gap is reported rather than fixed because it is outside Phase 2 scope.

## Deliverables

No new files are required by the verified current structure. The proposed endpoint and models are **NEW symbols in existing files**, not existing contracts.

| Deliverable | Target | Task IDs | Completion evidence |
|---|---|---|---|
| Trial control and computation | `backend/app/models/link_troubleshooter.py`, `backend/app/services/link_trial_service.py` | `T1.1`, `T1.2` | Tri-state overrides with production-equivalent resolution and explicit failures. |
| Effective-setting reporting | `src/model.py`, `backend/app/services/link_trial_service.py`, `backend/app/mappers/link_troubleshooter_mapper.py` | `T1.2`, `T2.2` | Baseline and trial report `requested`, `source`, and the resolved runtime pair. |
| Bounds configuration | `backend/app/core/config.py`, `backend/tests/test_config.py` | `T2.2` | Group cap and detail limits configured, bounded, and tested. |
| Context trial orchestration and retained baseline detail | `backend/app/services/link_troubleshooter_service.py`, `backend/app/services/link_experiment_context_store.py` | `T1.2`, `T2.1` | Snapshot reused; complete baseline detail capped; incomplete state preserved. |
| Bounded transport | `backend/app/models/link_troubleshooter.py`, `backend/app/mappers/link_troubleshooter_mapper.py` | `T2.2`, `T3.1` | Exact totals/counts and labeled capped detail on both responses; legacy stateless mapping intact. |
| Protected trial endpoint | `backend/app/api/v1/endpoints/link_troubleshooter.py` | `T3.1` | Authorized, context-bound POST; stateless route intact. |
| Focused tests | `backend/tests/services/test_link_trial_service.py`, `backend/tests/services/test_link_troubleshooter_service.py`, `backend/tests/services/test_link_experiment_context_store.py`, `backend/tests/mappers/test_link_troubleshooter_mapper.py`, `backend/tests/api/v1/test_link_troubleshooter.py`, `backend/tests/authorization/test_route_authentication.py`, `backend/tests/test_config.py`, `tests/model/test_model.py` | `T1.1`–`T3.1` | `V-1`–`V-6` new and regression cases pass. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
|---|---|---|---|
| Area 1: Controlled trials | Done | Phase 1 context available; `D10`–`D13` recorded | `T1.1`, `T1.2` implemented; `V-1`, `V-2`, `V-5`, `V-6` pass. |
| Area 2: Bounded exception detail | Done | Area 1; `D1`–`D9` recorded | `T2.1`, `T2.2` implemented; `V-2`, `V-3`, `V-6` pass. |
| Area 3: Context trial API | Done | Areas 1–2; `D1`–`D13` recorded | `T3.1` implemented; `V-4` route checks pass; pre-existing authorization inventory gap reported below. |

## Definition Of Done

- [x] Record the three named decisions (`D1`–`D13`) and confirm Phase 2 readiness.
- [x] Every `PH2-AC-*` criterion has passing task and validation evidence (`V-1`–`V-6`).
- [x] All three areas and listed deliverables are complete; the existing stateless caller still works.
- [x] Production null handling, constraint checks, row and memory limits, the tri-state override path, and incomplete-baseline behavior have regression tests.
- [x] Counts are full-input exact even when rows, key values or findings are truncated; output includes no correct A rows and marked truncation names its cause (`row_cap_reached` versus `budget_exhausted`).
- [x] Trial and baseline inputs, saved projects, databases, and production caches remain unchanged.
- [x] API models, service, mapper, and auth are consistent; targeted tests and formatting pass.
- [x] Deviations and follow-up work are documented; no unresolved question affects correctness or validation.

## Recorded Decisions

Approved 2026-11-07. These resolve the three blocking questions and were checked against `_resolve_fk_runtime_options`, `_resolve_link_opts`, `prepare_link_merge_keys`, and the existing request paging bounds.

| ID | Decision | Resolution |
|---|---|---|
| `D1` | Rows returned per exception group | 100 rows per group for both groups, from one setting `LINK_EXPERIMENT_GROUP_ROW_CAP` (default 100, `ge=1, le=1000`). |
| `D2` | Baseline versus trial caps | One shared setting. Baseline and trial use identical limits so the two sides stay comparable. |
| `D3` | Which rows survive a cap | Lowest `input_position` first, in input order, for both groups. |
| `D4` | Cap and budget interaction | The row cap is a hard ceiling and the detail budget may cut a list shorter. Report `row_cap_reached` and `budget_exhausted` separately instead of one truncation flag. |
| `D5` | Budget unit | UTF-8 encoded bytes of the scalar's string form, the form `_json_safe_scalar` already returns. |
| `D6` | Per-key-value limit | 256 bytes, cut at the last whole code point that fits. A value already within the limit is never altered. |
| `D7` | Finding limits | 50 findings and 512 bytes per message, per side, with an exact `total_count`. |
| `D8` | Aggregate detail budget | 256 KiB (262,144 bytes) per side, shared by that side's two groups and its findings. Findings are allocated first, then the unmatched group, then the multiply-matched group. Totals, counts, and truncation metadata sit outside the budget. |
| `D9` | Truncation representation | Per side `detail_truncated`; per group `total_count`, `returned_count`, `row_cap`, `row_cap_reached`, `budget_exhausted`; per key value `value`, `truncated`, `original_length` in code points; per findings block `total_count`, `returned_count`, `truncated`. No ellipsis is appended. |
| `D10` | Trial request representation | `how`, `allow_null_keys`, and `null_keys_equal` are each optional: absent inherits the saved FK, while an explicit boolean or `inner`/`left` overrides it. Request models use `extra="forbid"`. |
| `D11` | Applying an override | Deep-copy `saved_fk.fk_cfg`, set the key for an explicit override, remove it for inherit, then let production resolve. Never write `false` for an inherited control. |
| `D12` | Trial response representation | Per control `requested` (`null`, `true`, `false`), `source` (`inherited`, `explicit`), and the resolved runtime pair from `LinkMergeKeys.runtime_options`. Report the pair, not a synthesized `allow_null_keys` boolean, because lookup enrichment is not reproducible from one boolean. |
| `D13` | Join-type reporting | Production already treats an absent `how` as `inner`, so no behavior changes. The response reports the effective join type and its `source`. |

**Residual risks**

- `D5` measures the raw string form, not JSON-escaped bytes, so a value of control characters exceeds the budget proportionally. Accepted and documented, in the same class as the Phase 1 peak-memory estimate.
- `D3` biases retained detail toward early input rows. Broader coverage is a Phase 3 browsing concern, not a server cap change.
- `D8` budgets each side separately, so the worst-case response is two budgets plus exact metadata rather than one budget. Approved because a verbose baseline must not starve the trial the user just ran.

Phase 3 removes stateless paging and implements browser-side controls; do not move that contract cutover into this phase.
