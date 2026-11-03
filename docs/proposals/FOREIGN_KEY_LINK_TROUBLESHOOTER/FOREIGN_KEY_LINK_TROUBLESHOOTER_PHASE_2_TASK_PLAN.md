# Foreign-Key Link Troubleshooter — Phase 2 Task Plan

Source: [Foreign-Key Link Troubleshooter](FOREIGN_KEY_LINK_TROUBLESHOOTER.md), [Phase 2: Reproduce the selected link](FOREIGN_KEY_LINK_TROUBLESHOOTER_PHASE_PLAN.md). Prerequisite: [Phase 1 task plan](FOREIGN_KEY_LINK_TROUBLESHOOTER_PHASE_1_TASK_PLAN.md).

## Phase Summary

**Phase:** Phase 2 — Reproduce the selected link.

**Goal:** Produce a read-only baseline for one saved FK using current production link inputs and behavior. Report explicitly when the old warning cannot be reproduced.

**Plan readiness:** Validated. Phase 2 is marked ready in the phase plan; the replay and comparison decisions are fixed there, and the repository targets below have been verified.

**Dependency:** Phase 1's warning-to-saved-FK resolver and linking-pass metadata are present. Do not select an FK by entity pair alone.

**Acceptance criteria**

1. [x] `PH2-AC-1` (from `P-AC-2`) On the same link inputs, baseline counts and link-specific findings agree with the production run for inner and left joins.
2. [x] `PH2-AC-2` (from `P-AC-2`) If current data or execution cannot reproduce the selected warning, the baseline states why and does not present the old warning as a current result.
3. [x] `PH2-AC-3` (from `P-AC-3`) Baseline computation does not change the saved project or cached production data.

**Fixed decisions:** Replay the production pipeline on a temporary entity configuration; do not capture intermediate frames from a normal run. Reuse the production linker for the selected FK. Compare the newly observed warning's counts and recorded pass with the warning that was opened. Do not expose an endpoint, accept trial keys, or persist diagnostic data in this phase.

## Repository Findings

**Repository basis:** `feature/foreign-key-link-troubleshooter` at `a7d5142a`, inspected 2026-11-02; the working tree was clean. The attached phase plan matches the repository copy. Graphify was used for navigation; the following behavior was verified in code and tests. The phase plan's Current Position describes the pre-Phase-1 warning; current code already includes the Phase 1 metadata and resolver.

| Evidence | Finding | Planning implication |
| --- | --- | --- |
| `src/transforms/link_resolution.py::resolve_row_count_issue`, `src/model.py::TableConfig.foreign_keys` | A supported warning resolves to one saved FK by index and signature. `LinkIssueResolution.link_pass` can be `None` even when `status == "resolved"`. | Resolve on the unmodified mapped project first. Require one of `initial`, `after_unnest`, `deferred_retry` before replay; missing/unknown pass is a named non-reproduced outcome, not a guessed stage. |
| `backend/app/services/project_service.py::ProjectService.load_project`, `backend/app/mappers/project_mapper.py::ProjectMapper.to_core` | The service loads an API `Project`; the mapper resolves directives and file paths and validates the mapping sidecar. | Load once, deep-copy the API project, map it through `to_core`, then clone the resolved Core project for the temporary config. Keep its original filename for local files and sidecar reads. Do not run a second, different directive-resolution path. |
| `src/normalizer.py::ShapeShifter.normalize`, `_process_entity`, `_link_deferred_foreign_keys` | Normalization processes dependencies, retries deferred links, and closes its in-memory workspace and loaders in `finally`. `_process_entity` links at `initial`, again after unnest, and during retry; later stages may change rows and add `system_id`/`public_id`. | Run an isolated normalizer on the projected config with fresh `TableStore()`; request both A and B so B is processed even when the target FK is deferred and omitted from the prefix. Do not use the completed A preview as pre-link A without the phase-plan projection. |
| `src/model.py::TableConfig.is_drop_duplicate_dependent_on_unnesting`, `src/normalizer.py::_check_duplicate_keys`, `_drop_empty_rows_if_ready` | Unnest-dependent deduplication can occur after linking. Missing `keys` can fail after a truncated link; `drop_empty_rows` may run before the second link if its columns are available. | Decide deduplication from the **saved** table config before removing unnest. Apply the phase plan's exact stage-specific changes; compare observed counts rather than assuming the projected frame is always equivalent. |
| `src/model.py::TableConfig.depends_on`, `src/model.py::ShapeShiftProject.resolve_target_entities`, `src/process_state.py::ProcessState` | FK and filter dependencies drive execution; deferred FKs are excluded from hard dependencies. | Keep other entities and their dependencies intact. Explicitly include B as a target; no copied or cached B from another run. |
| `src/transforms/link.py::ForeignKeyLinker.link_foreign_key`, `_resolve_fk_runtime_options`, `src/specifications/constraints.py::ForeignKeyConstraintValidator` | The linker handles key coercion, merge setup, null policy, and constraints; the selected validator records before/after shapes and issues. `link_foreign_key` returns a frame but does not put it in `table_store`. | Use a separate linker with the **original saved FK** and fresh replay A/B frames, set its `link_pass`, and read its selected validator's issues. Check link readiness with `ForeignKeyDataSpecification` before calling it. Do not replace the merge with `DataFrame.merge` or the Test Join service. |
| `backend/app/services/shapeshift_service.py::preview_entity`, `preview_entities_batch`; `backend/app/utils/caches.py::ShapeShiftCache` | Preview reuses and writes cached completed frames, sometimes returns limited rows, and its override path is not a production-link input. | Do not call preview, batch preview, `ShapeShiftProjectCache`, or `ShapeShiftCache`; do not seed the replay from cached frames. |
| `tests/process/test_column_availability.py::test_candidates_match_deterministic_normalizer_checkpoints`, `tests/integration/test_circular_dependency.py::test_deferred_link_records_its_linking_pass` | Tests already observe link checkpoints and deferred retries without changing production code. | Reuse their inline fixtures and observation pattern for parity assertions; use complete input frames, not display samples. |

## Scope

**In scope**

- An internal backend service that loads and maps the saved project, resolves the warning, constructs the temporary Core config, replays dependencies and the two link participants, and returns a typed in-memory baseline result.
- Counts, link-specific findings, an explicit reproduction status/reason, and full replay inputs for later trials **only when reproduced**.
- Tests for each linking pass, preceding FKs, distinct and repeated A/B links, stale warnings, unavailable inputs, and read-only behavior.
- A contract test that fails if a new stage after the last `_process_entity` linking call is not represented in the projection rules.

**Out of scope**

- Trial key changes, per-A-row matching diagnostics, response-size limits, authorization route, API DTOs, frontend, general FK editor, and the quick Test Join (Phases 3–4).
- Altering `ShapeShifter`, `ForeignKeyLinker`, project persistence, or preview/cache behavior just to obtain a baseline.

**Affected layers:** a new service and service tests in `backend/`, plus a Core pipeline contract test in `tests/process/`. The service may import Core models and linker; Core must not import backend code. No user-facing documentation is needed before Phase 4.

## Work Breakdown

### Area 1: Project one saved link into a temporary replay

**Objective:** An independent full-pipeline run yields A at the selected link stage and B processed by that same run, without changing the saved configuration.

**Affected code:** `backend/app/services/link_baseline_service.py` (`NEW`); `backend/tests/services/test_link_baseline_service.py` (`NEW`).

**Dependencies:** Phase 1.

**Tasks:**

* [x] `T1.1` **Change:** Add `LinkBaselineService` with an async baseline method accepting `project_name`, `issue_type`, `local_entity`, and issue metadata; inject `ProjectService`. Load and deep-copy the API `Project`, call `ProjectMapper.to_core`, and call `resolve_row_count_issue` on that unmodified resolved Core project. Keep resolution failures distinct from replay failures. Reject absent or unknown `link_pass` explicitly.
  * **Target:** `backend/app/services/link_baseline_service.py` (`NEW`).
  * **Current → required:** Only the saved-FK resolver exists; no baseline service. Do not call `ProjectMapper.to_core_dict` alone or modify a cached/project-service object.
  * **Validation:** `V-1`, `V-3`, `V-4`.
* [x] `T1.2` **Change:** Build the projected Core project from `saved_project.clone()`. On its A entity, keep `foreign_keys[:fk_index]` (the **earlier** links only), never the selected or later FK. Preserve B and every other entity as mapped. Apply the phase plan's stage table exactly:
  * `initial`: remove `unnest`, `after_link` and `after_unnest` filters, and `drop_empty_rows`;
  * `after_unnest`: keep `unnest` and `after_link` filters, remove `after_unnest` filters, keep `drop_empty_rows`;
  * `deferred_retry`: keep `unnest`, both later filter stages, and `drop_empty_rows`;
  * all passes: clear A's `keys`; remove A's `drop_duplicates` for `initial` and `after_unnest` **only** when the saved `TableConfig.is_drop_duplicate_dependent_on_unnesting()` is true; keep it for `deferred_retry`. Preserve extract-stage filters, source configuration, extra columns, and explicit dependencies.
  * **Target:** `backend/app/services/link_baseline_service.py` (`NEW`).
  * **Current → required:** No isolated pre-link replay. Evaluate the deduplication predicate on the saved table **before** editing the clone; filter stages using `normalize_filter_stage` so omitted stages retain their extract default.
  * **Validation:** `V-1`, `V-2`.
* [x] `T1.3` **Test:** Assert exact projected settings for all three passes, prefix order with two different FKs to the same B, explicit and default extract filters, unnest-dependent versus independent deduplication, and unchanged original API/Core objects and filename.
  * **Target:** `backend/tests/services/test_link_baseline_service.py` (`NEW`).
  * **Implementation:** Use an API `Project` from `ProjectMapper.to_api_config` and a minimal config with `keys` that reference a target-FK-produced field; confirm only the cloned target config loses these keys. Add a path/directive case through `ProjectMapper.to_core` without writing any YAML.
  * **Validation:** `V-1`, `V-4`.

**Completion evidence:** `V-1` passes; all three projections preserve the mapped original and earlier FK order.

### Area 2: Reproduce the selected production link

**Objective:** Return current counts and findings from the real link implementation, or an explicit failure/reproduction reason.

**Affected code:** `backend/app/services/link_baseline_service.py` (`NEW`); `backend/tests/services/test_link_baseline_service.py` (`NEW`).

**Dependencies:** Area 1.

**Tasks:**

* [x] `T2.1` **Change:** Run `ShapeShifter(project=projected_project, target_entities={A, B}, table_store=TableStore(), default_entity=projected_project.metadata.default_entity).normalize()` once. Read A and B from this private run; if either is incomplete or absent, return a named non-reproduced reason. Before linking, check selected FK readiness with `ForeignKeyDataSpecification` on replay data using the **projected** project (the saved unnest setting can incorrectly defer a valid `initial` link); reject skipped, deferred, or already-linked targets instead of reporting success. Pass copies of A and B to a new `ForeignKeyLinker(project=saved_project, table_store=private_store)`; set `link_pass` to the recorded value and call its `link_foreign_key(A, saved_fk, B)` directly. Keep the two input frames in the internal result for Phase 3 only when reproduction is proven.
  * **Target:** `backend/app/services/link_baseline_service.py` (`NEW`).
  * **Current → required:** Existing Test Join independently merges sampled **post-link** previews; reuse the real link and constraint checks on full replay inputs. Extra `system_id`/`public_id` columns produced by the replay need not equal pre-link A column-for-column; compare rows, counts, and link findings, not frame schemas.
  * **Constraints:** No mutation of `ShapeShifter`/`ForeignKeyLinker`, no cache reads or writes, and no reuse of `link_entity` on already processed A. The only output is private in-memory data. An invalid link must not appear successful.
  * **Validation:** `V-2`, `V-4`.
* [x] `T2.2` **Change:** Return a typed result that distinguishes `reproduced`, `not_reproduced`, and `ineligible`, with a machine-readable reason, observed before/after row counts, the selected FK identity/pass, and only the selected link's **current** `ValidationIssue` findings. Identify the selected `row_count_mismatch` by index/signature/pass; require its before/after counts and join type to equal the opened warning. If it is absent, differs, or the replay cannot produce inputs, return `not_reproduced` with the specific cause. Do not copy the opened warning into the current findings or return frames as a valid trial input on failure.
  * **Target:** `backend/app/services/link_baseline_service.py` (`NEW`).
  * **Current → required:** No baseline or stale-warning state. Catch and log expected load/normalization/link failures narrowly with their cause; propagate unexpected failures rather than returning a success-shaped empty result.
  * **Validation:** `V-2`, `V-3`.
* [x] `T2.3` **Test:** Compare the service baseline with an independent normal production `ShapeShifter.normalize()` on identical full inputs. Observe the actual selected `link_foreign_key` call **in the test only** to record pre-link A, processed B, pass, and the selected validator's complete findings; assert equivalent input-row values in shared columns (the replay may add identity columns), selected issue types/messages/severities/metadata, and before/after counts. Cover inner and left joins, null-match policies (including a partially null compound key), duplicate remote matches, an earlier FK to a different parent, a viable second FK to the same B (the first must drop its added remote ID so production links the second), and links raised at `initial`, `after_unnest`, and `deferred_retry`. Use the existing inline fixed-entity and patched-source patterns; assert no sampling or unrelated FK issues in the result.
  * **Target:** `backend/tests/services/test_link_baseline_service.py` (`NEW`).
  * **Constraints:** No mock of the production merge; a mock source loader is allowed. A warning needs a non-empty constraints block (for example `allow_row_decrease: True`).
  * **Validation:** `V-2`.

**Completion evidence:** `V-2` passes on inner, left, earlier-FK, and deferred cases with actual production counts and link-specific findings.

### Area 3: Reject stale/unavailable baselines and lock the pipeline contract

**Objective:** Failed replay cannot masquerade as a reproduced warning, and future stage changes cannot silently invalidate the projection.

**Affected code:** `backend/tests/services/test_link_baseline_service.py` (`NEW`); `tests/process/test_shapeshifter.py` (existing).

**Dependencies:** Areas 1 and 2.

**Tasks:**

* [x] `T3.1` **Test:** Change the source rows so the selected warning disappears or changes counts; provide a missing source/remote input; pass missing/invalid `link_pass`, an unsupported join, or a stale FK signature. Assert distinct status/reason, no copied old warning, and no successful trial inputs. Include a constraint violation: it must be reported as failed, not as a valid comparison.
  * **Target:** `backend/tests/services/test_link_baseline_service.py` (`NEW`).
  * **Validation:** `V-3`.
* [x] `T3.2` **Test:** Assert that the saved `Project` and its file (where a temporary file fixture is used) are unchanged; patch `ShapeShiftCache.set_dataframe`, `set_table_store`, `fetch_cached_entity_data`, and `ShapeShiftProjectCache.get_project` to reject any calls, and assert replay creates its own `TableStore` and closes its workspace/loaders on both success and failure. Check that the input DataFrames supplied to a subsequent direct link do not mutate any production/cached frames.
  * **Target:** `backend/tests/services/test_link_baseline_service.py` (`NEW`).
  * **Validation:** `V-4`.
* [x] `T3.3` **Test:** Add a structural contract around the post-link portion of `ShapeShifter._process_entity` using its AST/source. Assert the known stage operations and their ordering after the last `_link_entity` against an explicit allowlist already accounted for by the three projection rules (filters, deferred extra columns, deduplication, duplicate-key check, empty-row drop, identity/sidecar work, deferred retry, and final verification/reordering). Fail if a new stage call is inserted there without updating this contract and the projection; do **not** make the test pass by automatically accepting unknown calls.
  * **Target:** `tests/process/test_shapeshifter.py` (existing).
  * **Validation:** `V-4`.

**Completion evidence:** `V-3` and `V-4` pass; a stale warning or failed input never returns a reproduced baseline, and a new unaccounted post-link stage fails the contract.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
| --- | --- | --- | --- |
| `PH2-AC-1` (from `P-AC-2`) | `T1.1`, `T1.2`, `T1.3`, `T2.1`, `T2.2`, `T2.3`, `T3.3` | `V-1`, `V-2`, `V-4`, `V-5` | A and B come from one isolated full run; selected linker counts, pass, and findings match a production run for inner, left, earlier, unnest, and deferred links. |
| `PH2-AC-2` (from `P-AC-2`) | `T1.1`, `T2.1`, `T2.2`, `T3.1` | `V-3`, `V-5` | Absent/different warning or unavailable inputs yield a named non-reproduced reason and no stale issue presented as current. |
| `PH2-AC-3` (from `P-AC-3`) | `T1.1`, `T1.2`, `T2.1`, `T3.2` | `V-1`, `V-4`, `V-5` | Original config and production caches remain unchanged; the replay uses private in-memory tables. |

Phase-plan milestones: `VM-2` is covered by `V-1`, `V-2`, `V-4`; `VM-3` by `V-3`, `V-4`.

## Validation And Testing

Pytest's configured `-qq -n auto` can omit the pass-count line; exit code 0 is a passing run.

| ID | Check and target | Command or method | Covers | Expected result | Baseline (2026-11-02) |
| --- | --- | --- | --- | --- | --- |
| `V-1` | Projection and mapping cases in `backend/tests/services/test_link_baseline_service.py` (`NEW`) | `uv run pytest backend/tests/services/test_link_baseline_service.py` (one run also covers `V-2`–`V-4`) | `PH2-AC-1`, `PH2-AC-3` | Exact rules for all three passes; original mapped/saved project unchanged | Not run: file is new |
| `V-2` | Full-run parity cases in the same new service test | Same focused command as `V-1` | `PH2-AC-1` | Counts, pass, and findings agree for inner/left, earlier and deferred FK | Not run: file is new |
| `V-3` | Stale warning, invalid identity/pass, missing input, and constraint failures in the same new service test | Same focused command as `V-1` | `PH2-AC-2` | Named failure with no old warning presented as current | Not run: file is new |
| `V-4` | Read-only and pipeline contract cases in the new service test and `tests/process/test_shapeshifter.py` | `uv run pytest backend/tests/services/test_link_baseline_service.py tests/process/test_shapeshifter.py` | `PH2-AC-1`, `PH2-AC-3` | No project/cache mutation; unaccounted stage fails contract | Existing `test_shapeshifter.py` passed (exit 0); new tests not run |
| `V-5` | Existing linker, resolver, mapper, and pipeline regressions | `uv run pytest backend/tests/services/test_link_baseline_service.py backend/tests/services/test_shapeshift_service.py backend/tests/mappers/test_project_mapper_nested_models.py tests/transforms/test_link.py tests/transforms/test_link_resolution.py tests/process/test_shapeshifter.py tests/process/test_column_availability.py tests/integration/test_circular_dependency.py tests/model/test_foreign_key_identity.py tests/specifications/test_constraints.py` | All three criteria and existing behavior | Exit 0; existing preview and FK resolution unchanged | All nine existing files passed (exit 0) in two targeted runs; new file not run |
| `V-6` | Formatting, lint, and type check on changed Python files | `uv run black --check backend/app/services/link_baseline_service.py backend/tests/services/test_link_baseline_service.py tests/process/test_shapeshifter.py`; `uv run isort --check-only backend/app/services/link_baseline_service.py backend/tests/services/test_link_baseline_service.py tests/process/test_shapeshifter.py`; `uv run pyright --threads 2 backend/app/services/link_baseline_service.py`; `uv run pylint backend/app/services/link_baseline_service.py backend/tests/services/test_link_baseline_service.py` | Code quality | Exit 0 for each; record any existing lint baseline separately | Not run: new Python files do not exist yet |
| `V-7` | Task-plan links and spelling of relative paths | `scripts/check_doc_links.sh` | Documentation | "Documentation links are valid." | Not run for this new plan |

### Validation Evidence (implementation run, 2026-11-02)

Commands were run from the worktree root with the repository `.venv`.

| ID | Command | Result |
| --- | --- | --- |
| `V-1`–`V-4` | `uv run pytest backend/tests/services/test_link_baseline_service.py tests/process/test_shapeshifter.py` (repo default options) | Exit 0, no failures. Repeated three times with `-p no:randomly`; exit 0 each time. |
| `V-2` | Parity cases cover inner, left, duplicate remote matches, partially null compound key, earlier FK to another entity, second link to the same entity, and links at `initial`, `after_unnest`, and `deferred_retry`. | Each case returns `reproduced` with the production pass, row counts, link findings, and equal shared-column row values. |
| `V-3` | `warning_changed`, `warning_not_raised`, `remote_entity_not_found`, `replay_failed`, `missing_link_pass`, `unknown_link_pass`, `unsupported_join`, `signature_mismatch`, and `constraint_violation` cases. | Each returns the named status/reason, `local_rows is None`, and no copied old warning. |
| `V-4` | Read-only, replay-lifecycle, and post-link contract cases. | Cache methods never called; API and Core project snapshots unchanged; workspace and loaders closed on success and failure. A temporary extra call in `_process_entity` made the contract test fail, and the change was reverted. |
| `V-5` | The full regression command listed for `V-5` | Exit 0, no failures. |
| `V-6` | `black --check`, `isort --check-only`, `pyright --threads 2`, `pylint` | Black, isort, and pylint exit 0 (pylint 10.00/10). Pyright reports only `reportMissingImports` for `pandas` and `loguru`; `backend/app/services/shapeshift_service.py` reports the same two errors, so this is an existing environment baseline, not a new finding. |
| `V-7` | `scripts/check_doc_links.sh` | "Documentation links are valid." |

Observations recorded during implementation:

- The replay's local frame carries `system_id` and `public_id`, so `column_count_mismatch` reports different column totals than the production link. The phase plan already expects this; parity compares row-level findings exactly and compares column-count findings by `expected_increase` and `added_columns`.
- The deferred retry case needs an explicit reverse dependency (`customers.depends_on: [orders]`) because entity processing order otherwise depends on set iteration order. This is a test fixture detail, not a pipeline or service change.
- The `__del__` hook of `DuckDbWorkspace` can close an already closed workspace, so lifecycle assertions check that the workspace was closed at least once and that its connection is `None`.

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Read-only baseline and temporary-project projection | `backend/app/services/link_baseline_service.py` (`NEW`) | `T1.1`, `T1.2`, `T2.1`, `T2.2` | `V-1`–`V-4` |
| Projection, production-parity, stale-warning, and cache tests | `backend/tests/services/test_link_baseline_service.py` (`NEW`) | `T1.3`, `T2.3`, `T3.1`, `T3.2` | `V-1`–`V-4` |
| Post-link stage contract test | `tests/process/test_shapeshifter.py` | `T3.3` | `V-4` |

After code changes, refresh the repository knowledge graph with `GRAPHIFY_VIZ_NODE_LIMIT=0 graphify update .`; graph output is not part of this phase's code deliverable. This task plan itself is the only documentation change during planning.

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Project one saved link | Done | Phase 1 | `T1.1`–`T1.3` complete; projection tests pass |
| Area 2: Reproduce the selected link | Done | Area 1 | `T2.1`–`T2.3` complete; parity passes for initial, after-unnest, and deferred-retry links |
| Area 3: Reject stale baselines and lock contract | Done | Areas 1, 2 | `T3.1`–`T3.3` complete; failure reasons and the post-link contract pass |

## Definition Of Done

* [x] `PH2-AC-1`, `PH2-AC-2`, and `PH2-AC-3` each have passing task and validation evidence.
* [x] All three areas and listed deliverables are complete; the progress table shows Done.
* [x] `V-1`–`V-7` pass, or a verified existing quality-check failure is identified separately from new findings.
* [x] Earlier FK, unnest, deferred retry, null policy, and preview behavior remain covered by regressions.
* [x] No saved project, production cache, or API contract is changed by a baseline run.
* [x] Deviations and remaining Phase 3–4 work are recorded here; no unresolved question affects this phase's correctness.

## Risks And Open Questions

- **A replayed frame can contain extra identity columns.** The phase plan explicitly requires parity in counts and link-specific findings, not byte-for-byte frame equality. If added columns affect a validation finding or a join, report a non-reproduced baseline; never silently drop those columns or claim parity.
- **Input data can change without changing row counts.** Phase 1 stored no input fingerprint. Matching the recorded warning counts and pass proves only that the warning reproduces against current data; it does not prove that every source value is unchanged. Show current findings as current, never label the old issue as fresh data.
- **Deferred links depend on processing order.** Requesting both participants and preserving every other entity allows retry logic to run. If a target is skipped, linked at a different pass, or an earlier deferred link changes A differently, the baseline must be non-reproduced rather than falling back to a post-link preview.
- **Implementation handoff:** If source behavior differs from the verified findings (in particular the post-link stage ordering or mapper resolution), stop and record the conflict before implementing. Do not invent a different replay strategy or broaden this phase to an endpoint or a capture mechanism.

**Open questions:** None that change the Phase 2 design. A general intermediate-frame capture mechanism is tracked separately in #641.
