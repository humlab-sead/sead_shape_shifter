# Foreign-Key Link Troubleshooter — Phase 4 Task Plan

Source: [Foreign-Key Link Troubleshooter](FOREIGN_KEY_LINK_TROUBLESHOOTER.md), [Phase 4: Present the bounded comparison](FOREIGN_KEY_LINK_TROUBLESHOOTER_PHASE_PLAN.md). Prerequisites: [Phase 1 task plan](FOREIGN_KEY_LINK_TROUBLESHOOTER_PHASE_1_TASK_PLAN.md), [Phase 2 task plan](FOREIGN_KEY_LINK_TROUBLESHOOTER_PHASE_2_TASK_PLAN.md), [Phase 3 task plan](FOREIGN_KEY_LINK_TROUBLESHOOTER_PHASE_3_TASK_PLAN.md).

## Phase Summary

**Goal:** Let an authorized user open a supported linking warning, inspect the reproduced baseline and key-pair trials, page and filter A-row diagnostics, and discard the trial on close.

**Plan readiness: Validated.** Phase 4 is marked "Requires the Phase 1–3 outputs and their resolved decisions" in the phase plan. Phases 1–3 are implemented and committed. This plan records the remaining presentation decisions: a stateless backend request that recomputes the baseline, a fixed response page cap separate from the computation cap, and a client-side action predicate backed by authoritative server eligibility.

**Dependencies:** Phase 1 warning identity and resolver; Phase 2 `LinkBaselineService` and `LinkBaselineResult`; Phase 3 `LinkTrialService` and `LinkTrialResult`; Project read authorization; the existing validation-panel UI.

**Acceptance criteria**

1. [x] `PH4-AC-1` (from `P-AC-1`) The action opens the identified supported FK with fixed A/B, join type, and constraints; ineligible warnings offer no action.
2. [x] `PH4-AC-2` (from `P-AC-3`, `P-AC-4`) Users can change trial keys, compare baseline and trial results, and page or filter A-row details without changing complete totals.
3. [x] `PH4-AC-3` (from `P-AC-5`) The view displays failures and incomplete results, returns bounded row data only to an authorized reader, and discards trial state on close.

**Fixed decisions**

- The backend request is stateless. Each open or trial request rebuilds the baseline from the current saved project and the warning identity, then runs the requested trial. No server session, cache, or stored trial exists, so closing the view discards the trial by construction.
- Baseline counts and diagnostics always describe the saved FK keys. Trial counts and rows always describe the requested keys. A request that changes keys therefore runs a configured-key trial for the baseline diagnostics and a second trial for the requested keys. When the requested keys equal the saved keys, the two trials are the same run.
- The response page cap is a fixed `page_size` maximum of 500 rows in the request model. It is separate from `LINK_TRIAL_MAX_OUTPUT_ROWS`, which bounds computed rows for each trial.
- The frontend offers the action only for `ROW_COUNT_MISMATCH` messages whose metadata identifies a saved FK and whose `join_type` is `inner` or `left`. The backend remains authoritative: a stale signature or other ineligible state returns `ineligible` with no trial controls.

## Repository Findings

**Repository basis:** `feature/foreign-key-link-troubleshooter` at `ccb33e9c`, inspected 2026-11-02; implementation files were clean, and this task plan was the only untracked file. Graphify was used for navigation and every finding below was verified in source, tests, or configuration.

| Evidence | Finding | Planning implication |
| --- | --- | --- |
| `backend/app/services/link_baseline_service.py::LinkBaselineService.build_baseline`, `LinkBaselineResult` | Reproduced results carry `local_rows`, `remote_rows`, `_saved_project`, and `_foreign_key`. `not_reproduced` results carry counts and current issues but drop the resolved FK context. | Retain the resolved FK for display in stale states, but never return frames or allow a trial unless reproduced. |
| `backend/app/services/link_trial_service.py::LinkTrialService.run_trial`, `LinkTrialResult`, `ARowTrialDiagnostic` | Trials return `complete`, `failed`, or `incomplete`; complete results carry the four totals, selected-link issues, and every A-row diagnostic. Failures carry no totals or rows. | Wrap the service, map its statuses, and paginate/filter `a_rows` without recomputing totals from the page. |
| `backend/app/services/link_trial_service.py::LinkTrialService._validate_key_selection`, `tests/test_data/projects/arbodat/shapeshifter.yml` | Trial keys may use any available link-input column; existing project FKs use `remote_keys: [system_id]`. | Exclude `system_id` from new key choices unless it is part of the configured key pair; preserve configured `system_id` keys in the initial editor options. |
| `src/specifications/constraints.py::ForeignKeyConstraintValidator.validate_after_merge`, `backend/app/services/link_trial_service.py::LinkTrialService.run_trial` | The warning records `join_type: self.fk.how`, and the trial checks `trial_fk.how` directly. A saved FK with an explicit `how: null` is therefore recorded and trialled inconsistently with `resolve_row_count_issue`'s `how or "inner"` default. | Normalize the effective join type in the warning metadata and the trial support/estimate paths so an explicit null behaves as inner end to end. |
| `src/transforms/link_resolution.py::resolve_row_count_issue` | Resolves a `row_count_mismatch` issue to one saved FK by index and signature, or returns a named ineligible status. | The backend request must carry `issue_type`, `local_entity`, and the warning metadata; the frontend must not construct an FK from A/B alone. |
| `backend/app/mappers/validation_mapper.py::ValidationMapper.from_linker_issue` | Converts a core linker `ValidationIssue` to the API `ValidationError` and preserves metadata with `issue_type` and `remote_entity`. | Reuse it for baseline and trial findings; do not create a parallel issue DTO. |
| `backend/app/api/v1/endpoints/preview.py::test_foreign_key_join` | The existing quick Test Join reads limited processed previews and performs an independent left merge. | Do not reuse it for the troubleshooter; the Phase 2/3 services are the parity reference. |
| `backend/app/authorization/dependencies.py::require_project` | Project routes authorize a path `project_name` or `name` for an `Action`; denied callers receive a concealed 404. | Use `require_project(Action.READ)` on the new route and load the project from `authorized_project.resource.locator`. |
| `backend/tests/conftest.py::authorized_client`, `backend/tests/api/test_project_ingester_routes.py::client_for_principal` | Existing fixtures cover an authenticated owner and explicit non-owner principals. | Reuse these patterns for the route authorization tests. |
| `frontend/src/components/validation/ValidationMessageList.vue` | Renders warning rows, expands details on click, and emits `open-entity`. | Add the per-message action and a `troubleshoot` event here; stop click propagation. |
| `frontend/src/components/validation/ValidationPanel.vue` | Uses `validation-message-list` in nine places across tabs, categories, and entity/branch groups. | Forward the new event from every usage, preferably with one `v-on="listEvents"` binding. |
| `frontend/src/views/ProjectDetailView.vue` | Owns `ValidationPanel`, project identity, and modal dialogs. | Own the troubleshooter dialog state and pass the project name down. |
| `frontend/src/types/validation.ts::ValidationError`, `ValidationMetadataValue` | Warning metadata is typed as `string \| number \| boolean \| null \| string[]`. | The candidate predicate must narrow metadata values before use. |
| `backend/app/core/config.py::Settings.LINK_TRIAL_MAX_OUTPUT_ROWS` | The computation cap defaults to 1,000,000 and accepts a positive override. | Keep the Phase 4 page cap separate; do not reuse or rename this setting. |
| `frontend/src/components.d.ts` | Generated by `unplugin-vue-components`. | Regenerate through the frontend build; do not hand-edit. |
| `frontend/node_modules` | Not installed in the planning environment. | Frontend baseline checks are "Not run"; the plan records exact commands for execution. |
| `pyproject.toml` pytest `addopts` | `-qq -rfEx --strict-markers --durations=10 -n auto`; no pass-count summary is printed. | Treat exit code 0 as pass and read failures from `-rfEx`. |

## Scope

**In scope**

- API request and response models for opening a warning and running a key-pair trial.
- A mapper that serializes statuses, relationship details, totals, findings, bounded A rows, and pagination.
- A backend orchestration service and authorized route.
- A small `LinkBaselineResult` extension that retains resolved FK display context for stale results.
- Frontend types, API client, candidate helper, composable, dialog, validation-list action, and project-view wiring.
- Backend and frontend tests plus generated component typing.

**Out of scope**

- Changing the Phase 2 baseline replay or Phase 3 trial algorithm, except retaining display context for stale results and aligning a missing `how` value with the resolver's inner default in the warning metadata and trial service.
- Saving or promoting a trial; changing A, B, join type, or constraints.
- Right, outer, and cross joins.
- Project-wide validation, the general foreign-key editor, and the quick Test Join.
- A new runtime setting for response size.
- User documentation beyond this task plan.

**Affected layers:** backend models, mappers, services, API endpoint, and tests; frontend types, API client, composables, components, views, utilities, and tests. Core algorithms remain unchanged.

## Work Breakdown

### Area 1: Backend response contract and mapper

**Objective:** One API model and mapper turn the Phase 2/3 results into a bounded, JSON-safe response.

**Affected code:** `backend/app/models/link_troubleshooter.py` (`NEW`), `backend/app/models/__init__.py`, `backend/app/mappers/link_troubleshooter_mapper.py` (`NEW`), `backend/tests/mappers/test_link_troubleshooter_mapper.py` (`NEW`).

**Dependencies:** Phase 2 and Phase 3 result types.

**Tasks:**

* [x] `T1.1` **Change:** Add the troubleshooter API models and export them.
  * **Target:** `backend/app/models/link_troubleshooter.py` (`NEW`); `backend/app/models/__init__.py`.
  * **Current → required:** No troubleshooter DTOs → add:
    * `LinkTroubleshootRequest` with `issue_type: str`, `local_entity: str`, `metadata: dict[str, Any]`, optional `local_keys: list[str] | None`, optional `remote_keys: list[str] | None`, `page: int = Field(default=1, ge=1)`, `page_size: int = Field(default=50, ge=1, le=500)`, and `row_filter: Literal["all", "unmatched", "multiply_matched"] = "all"`.
    * `LinkTroubleshootKeys` with `local_keys: list[str]` and `remote_keys: list[str]`.
    * `LinkTroubleshootRelationship` with `local_entity`, nullable `remote_entity`/`fk_index`/`join_type`/`link_pass`, and `constraints: dict[str, Any]`.
    * `LinkTroubleshootKeyOptions` with `local: list[str]` and `remote: list[str]`.
    * `LinkTroubleshootTotals` with the four integer totals.
    * `LinkTroubleshootBaseline` with nullable `input_a_rows`, `output_rows`, `unmatched_a_rows`, and `multiply_matched_a_rows`, `diagnostic_status: Literal["complete", "failed", "incomplete", "not_run"]`, `diagnostic_reason`, `diagnostic_message`, and `issues: list[ValidationError]`. The diagnostic fields describe the configured-key trial; the issues describe the current baseline link findings.
    * `LinkTroubleshootRow` with `input_position`, `key_values: list[Any]`, `matched`, `remote_match_count`, and `output_row_contribution`.
    * `LinkTroubleshootPagination` with `page`, `page_size`, `filtered_row_count`, `returned_row_count`, and `has_next`.
    * `LinkTroubleshootTrial` with `status: Literal["complete", "failed", "incomplete"]`, `reason`, `message`, `local_keys`, `remote_keys`, nullable `totals`, `issues`, `rows`, and nullable `pagination`.
    * `LinkTroubleshootResponse` with `status: Literal["reproduced", "not_reproduced", "ineligible"]`, `reason`, `message`, nullable `relationship`, `key_options`, `configured_keys`, `baseline`, and `trial`.
  * **Implementation:** Reuse `backend.app.models.validation.ValidationError`. Keep `page_size` at `le=500`; this is the response-size bound. Add the new classes to `backend/app/models/__init__.py` imports and `__all__` if that file maintains one.
  * **Constraints:** Pydantic v2 models only; no DataFrames, core project objects, or private context fields. Do not add a new `Settings` field.
  * **Validation:** `V-1`, `V-3`.

* [x] `T1.2` **Change:** Add the response mapper.
  * **Target:** `backend/app/mappers/link_troubleshooter_mapper.py` (`NEW`).
  * **Current → required:** No troubleshooter mapper → add `LinkTroubleshooterMapper` with:
    * `to_response(*, baseline: LinkBaselineResult, baseline_trial: LinkTrialResult | None, trial: LinkTrialResult | None, relationship: LinkTroubleshootRelationship | None, key_options: LinkTroubleshootKeyOptions | None, configured_keys: LinkTroubleshootKeys | None, trial_local_keys: Sequence[str], trial_remote_keys: Sequence[str], page: int, page_size: int, row_filter: str) -> LinkTroubleshootResponse`.
    * Map the top-level response `status`, `reason`, and `message` from the baseline. Keep requested-trial `failed` and `incomplete` outcomes in `trial.status`; they do not replace the top-level baseline status.
    * A baseline totals helper that fills `input_a_rows`/`output_rows` from `row_count_before`/`row_count_after`, fills `unmatched_a_rows`/`multiply_matched_a_rows` only from a complete **baseline trial**, sets `diagnostic_status`/`diagnostic_reason`/`diagnostic_message` from the baseline trial (`not_run` when it is absent), and maps `baseline.issues` with `ValidationMapper.from_linker_issue`.
    * A trial helper that maps the **requested trial** `complete` totals, maps `trial.issues`, and returns no totals or rows for `failed`/`incomplete`. The trial helper must not copy the baseline trial's rows or totals.
    * A filter-and-page helper over `trial.a_rows` for `all`, `unmatched` (`not matched`), and `multiply_matched` (`remote_match_count > 1`). Set `filtered_row_count` from the full filtered list, `returned_row_count` from the page, and `has_next = page * page_size < filtered_row_count`. A page beyond the last page returns an empty row list and `has_next=False`, not an error.
    * A scalar helper that converts pandas/NumPy scalars with `.item()`, maps `None`, `NaN`, and `pd.NA` to `None`, and stringifies other non-JSON values. Do not call `pd.isna` on list or dict values.
  * **Implementation:** Use `ValidationMapper.from_linker_issue` for every core issue. Type-hint core issues with `TYPE_CHECKING` imports. Keep totals from `LinkTrialResult`, never from the returned page.
  * **Constraints:** The mapper reads only public baseline/trial fields. It never reads `local_rows`, `remote_rows`, `_saved_project`, or `_foreign_key`. It never mutates the trial result.
  * **Validation:** `V-1`.

* [x] `T1.3` **Test:** Cover the mapper contract.
  * **Target:** `backend/tests/mappers/test_link_troubleshooter_mapper.py` (`NEW`).
  * **Current → required:** No mapper tests → add cases for:
    * Reproduced baseline plus complete baseline and requested trials with different keys: baseline totals come from the baseline trial, trial totals and rows come from the requested trial, and the two can differ.
    * Reproduced baseline plus an incomplete or failed baseline trial but a complete requested trial: baseline diagnostics are `None`, `diagnostic_status` is `incomplete`/`failed`, and the requested trial still has totals.
    * Reproduced baseline plus incomplete and failed requested trials: preserve each trial's status, reason, and message; `trial.totals is None`, `rows == []`, and `pagination is None`.
    * Not-reproduced baseline: counts present, `diagnostic_status == "not_run"`, current issues mapped, no trial.
    * Ineligible baseline with no counts: `baseline is None`.
    * `all`, `unmatched`, and `multiply_matched` filters: correct `filtered_row_count`; the page never changes totals; a page beyond the last page is empty.
    * JSON-safe key values for `numpy.int64`, `numpy.float64`, `numpy.bool_`, `None`, `float("nan")`, and `pd.NA`.
    * The serialized response has no DataFrame, project, or foreign-key field.
  * **Constraints:** No database, filesystem, or network.
  * **Validation:** `V-1`.

**Completion evidence:** `V-1` passes; the response contains bounded rows and no private context.

### Area 2: Backend orchestration, display context, and route

**Objective:** An authorized request opens one warning, rebuilds its baseline, runs a trial, and returns the mapped response.

**Affected code:** `backend/app/services/link_baseline_service.py`, `backend/tests/services/test_link_baseline_service.py`, `src/specifications/constraints.py`, `tests/specifications/test_constraints.py`, `backend/app/services/link_trial_service.py`, `backend/tests/services/test_link_trial_service.py`, `backend/app/services/link_troubleshooter_service.py` (`NEW`), `backend/app/api/v1/endpoints/link_troubleshooter.py` (`NEW`), `backend/app/api/v1/api.py`, `backend/tests/services/test_link_troubleshooter_service.py` (`NEW`), `backend/tests/api/v1/test_link_troubleshooter.py` (`NEW`).

**Dependencies:** Area 1; Phase 2 and Phase 3 services.

**Tasks:**

* [x] `T2.1` **Change:** Retain resolved FK display context for stale baselines.
  * **Target:** `backend/app/services/link_baseline_service.py::LinkBaselineService._link`, `_stop`, and their `_result` calls; `backend/tests/services/test_link_baseline_service.py`.
  * **Current → required:** `_saved_project` and `_foreign_key` are set only on reproduced results → set them on every result where the FK resolved, including `warning_not_raised`, `warning_changed`, `remote_entity_not_found`, `missing_link_pass`, `unknown_link_pass`, `missing_warning_counts`, `warning_join_mismatch`, replay failures, and link readiness failures.
  * **Implementation:** Add optional `saved_project` to `_stop` and pass `saved_project`, `fk`, and `resolution` from each call site where they exist. In `_link`, pass `_saved_project=saved_project` and `_foreign_key=fk` to the `warning_not_raised` and `warning_changed` results. Leave `local_rows` and `remote_rows` `None` for every non-reproduced result.
  * **Constraints:** Do not change any `status`, `reason`, or `message`. Do not return frames for stale results. Do not make `LinkTrialService` accept a non-reproduced baseline; its existing guard stays authoritative.
  * **Validation:** `V-4`.

* [x] `T2.2` **Change:** Add the orchestration service.
  * **Target:** `backend/app/services/link_troubleshooter_service.py` (`NEW`).
  * **Current → required:** No service joins the baseline and trial → add `LinkTroubleshooterService` with `__init__(baseline_service: LinkBaselineService | None = None, trial_service: LinkTrialService | None = None)` and `async def run(...) -> LinkTroubleshootResponse`.
  * **Implementation:**
    1. Call `LinkBaselineService.build_baseline` with the project locator, `issue_type`, `local_entity`, and metadata.
    2. If the baseline is not reproduced, build the relationship from the retained FK context when available, set `key_options=None`, `configured_keys` from the FK when available, pass `baseline_trial=None` and `trial=None`, and return the mapped response. Do not run a trial.
    3. If the baseline status is `reproduced`, require `local_rows`, `remote_rows`, `_saved_project`, and `_foreign_key`. If any is missing, use `dataclasses.replace` to set the baseline status to `not_reproduced`, set reason `baseline_context_missing` and a clear message, and set `local_rows`/`remote_rows` to `None`. Then use the non-reproduced response path in step 2 so the mapper receives the corrected status and no trial runs.
    4. Build `configured_keys` from `fk.local_keys`/`fk.remote_keys`. Build `relationship` from `fk.local_entity`, `fk.remote_entity`, `fk.fk_index`, `fk.how or "inner"`, `baseline.link_pass`, and `dict(fk.constraints.data)`. Build `key_options` from the local and remote frame column order, excluding each table's `system_id` column unless it appears in that side's configured keys; preserve first occurrence.
    5. Choose requested keys: when both request lists are `None`, use the saved FK keys; when one is `None`, pass an empty list for that side so the requested trial returns `invalid_keys`.
    6. Run the **baseline trial** with the saved FK keys. If it is `complete` and (`input_a_rows != baseline.row_count_before` or `output_rows != baseline.row_count_after`), replace it with a `failed` result using `dataclasses.replace`, reason `baseline_counts_mismatch`, and no totals or rows. This guards baseline diagnostics only; it does not fail the response.
    7. Choose the requested trial: when the requested key lists equal the saved key lists, reuse the baseline trial; otherwise run `LinkTrialService.run_trial` with the requested keys. For a complete requested trial, require `input_a_rows == baseline.row_count_before`; if not, replace it with a `failed` result, reason `baseline_input_mismatch`, and no totals or rows. Do not compare the requested trial's output count with the baseline output count, because changed keys may legitimately change it.
    8. Map the response with `LinkTroubleshooterMapper.to_response`, passing the baseline trial, the requested trial, the selected trial keys, page, page size, and row filter.
  * **Constraints:** No cache reads or writes; no second project load; no saved-project mutation; no frames or private context in the response. Let unexpected exceptions propagate rather than returning a success-shaped result.
  * **Validation:** `V-2`, `V-5`.

* [x] `T2.3` **Change:** Add the authorized route and register it.
  * **Target:** `backend/app/api/v1/endpoints/link_troubleshooter.py` (`NEW`); `backend/app/api/v1/api.py`.
  * **Current → required:** No troubleshooter route → add `POST /projects/{project_name}/link-troubleshooter` with `response_model=LinkTroubleshootResponse`, `require_project(Action.READ)`, and `@handle_endpoint_errors`.
  * **Implementation:** Add `get_link_troubleshooter_service() -> LinkTroubleshooterService` as a dependency factory. The endpoint receives `LinkTroubleshootRequest`, awaits `service.run(...)`, and passes `authorized_project.resource.locator` as `project_name`. Register the router in `backend/app/api/v1/api.py` with tag `link-troubleshooter`.
  * **Constraints:** No business logic in the endpoint; do not use the raw path value for loading. Pydantic handles invalid page/page-size values as 422. `require_project` returns 404 for a missing or unauthorized project. Return 200 for `ineligible` or `not_reproduced` baselines and for failed or incomplete trials; keep trial outcomes in the nested `trial.status`. Reserve HTTP errors for request shape, authorization, and unexpected failures.
  * **Validation:** `V-3`.

* [x] `T2.4` **Test:** Cover orchestration behavior end to end.
  * **Target:** `backend/tests/services/test_link_troubleshooter_service.py` (`NEW`).
  * **Current → required:** No orchestration tests → add:
    * Patched baseline/trial tests for: configured keys default, alternative keys, unequal or missing keys, non-reproduced baseline, missing baseline context, complete/incomplete/failed baseline and requested trials, baseline count-mismatch guard, requested-trial input guard, key options excluding unconfigured `system_id` columns while retaining configured ones, pagination/filter counts, and no response frames.
    * A configured FK whose remote key is `system_id`: retain `system_id` in `key_options.remote`, initialize from the configured pair, and successfully run that pair.
    * An invalid requested-key pair still returns the configured-key baseline diagnostics and a `failed` trial with `invalid_keys`; it must not hide the baseline result.
    * A configured-key request runs one trial and reuses it for baseline and trial. An alternative-key request runs the configured-key trial for baseline diagnostics plus a second trial for the requested keys; the two output counts may differ.
    * A case where the configured-key baseline trial is `incomplete` but an alternative requested trial is `complete`: baseline diagnostics are unavailable and the requested trial totals are present.
    * Real end-to-end cases using the fixed-entity project pattern from `backend/tests/services/test_link_baseline_service.py` and `backend/tests/services/test_link_trial_service.py`: one inner join and one left join; a configured-key trial with matching baseline counts; an alternative key pair with different baseline and trial output counts; a stale signature returning `ineligible`; an over-limit setting returning `incomplete`; paging/filtering with unchanged totals.
    * Read-only checks: patch `ShapeShiftCache.set_dataframe`, `set_table_store`, `fetch_cached_entity_data`, and `ShapeShiftProjectCache.get_project` to raise, and assert a project snapshot is unchanged after a real call.
  * **Constraints:** Do not mock the production merge in the real end-to-end cases. Use a low `LINK_TRIAL_MAX_OUTPUT_ROWS` for the over-limit case. Do not allocate an oversized join.
  * **Validation:** `V-2`, `V-5`.

* [x] `T2.5` **Test:** Cover route authorization and request validation.
  * **Target:** `backend/tests/api/v1/test_link_troubleshooter.py` (`NEW`).
  * **Current → required:** No route tests → add:
    * Authorized request returns 200 and the mapped payload; the service receives the authorized locator, issue identity, keys, page, page size, and filter.
    * `ineligible` and `not_reproduced` baseline responses return 200 with no trial. Failed and incomplete trial responses return 200 with nested `trial.status`, reason, and message, and with no totals, rows, or pagination.
    * Missing `issue_type`, missing `metadata`, `page=0`, `page_size=0`, and `page_size=501` return 422.
    * A principal without project read returns 404 and the service is not called.
    * A missing project returns 404.
  * **Implementation:** Use `authorized_client` from `backend/tests/conftest.py` for the owner path and the `client_for_principal` pattern from `backend/tests/api/test_project_ingester_routes.py` for the denied path. Override `get_link_troubleshooter_service` with a mock for the wiring test.
  * **Constraints:** Do not require real source data for the wiring cases; use the real service only if a small fixed-entity project is needed.
  * **Validation:** `V-3`, `V-5`.

* [x] `T2.6` **Change:** Align the test-run metadata's join type with the effective default.
  * **Target:** `src/specifications/constraints.py::ForeignKeyConstraintValidator.validate_after_merge`; `tests/specifications/test_constraints.py`.
  * **Current → required:** `row_count_mismatch` metadata records `join_type: self.fk.how`, which is `None` for a saved FK with an explicit `how: null` → record `self.fk.how or "inner"`, matching how the linker and `resolve_row_count_issue` treat a missing join type.
  * **Implementation:** Change only the `row_count_mismatch` metadata value. Leave the message, counts, `column_count_mismatch`, and the FK without-constraints early return unchanged. Add regression cases for a saved FK with an explicit `how: null` and one with no `how` key.
  * **Constraints:** Inner and left links keep their existing values; this is not a new join mode.
  * **Validation:** `V-2`, `V-4`.

* [x] `T2.7` **Change:** Align the trial service's join-type handling for a missing `how` value.
  * **Target:** `backend/app/services/link_trial_service.py::LinkTrialService.run_trial` and `_estimate_output_rows`; `backend/tests/services/test_link_trial_service.py`.
  * **Current → required:** `trial_fk.how` is checked directly, so a saved FK with an explicit `how: null` is rejected as unsupported and estimated as a left join → resolve `join_type = trial_fk.how or "inner"` once, use it for the support check and the output-row estimate, and keep `_diagnose_a_rows`'s `fk.how == "left"` behavior (which already treats `None` as inner).
  * **Implementation:** Mirror `resolve_row_count_issue`'s `how or "inner"` rule. Do not change the saved FK, its identity signature, or the trial's fixed constraints.
  * **Constraints:** This is a consistency fix, not a new join mode; right, outer, and cross joins remain unsupported.
  * **Validation:** `V-2`, `V-4`.

**Completion evidence:** `V-2`, `V-3`, `V-4`, and `V-5` pass; the route is authorized, the response is bounded, and no state is written.

### Area 3: Frontend types, API, helper, and composable

**Objective:** The frontend can build a troubleshooter request from a warning, call the route, and manage loading, errors, paging, and reset.

**Affected code:** `frontend/src/types/linkTroubleshooter.ts` (`NEW`), `frontend/src/types/index.ts`, `frontend/src/api/linkTroubleshooter.ts` (`NEW`), `frontend/src/utils/linkTroubleshooter.ts` (`NEW`), `frontend/src/composables/useLinkTroubleshooter.ts` (`NEW`), `frontend/src/composables/index.ts`, and the matching `__tests__` files (`NEW`).

**Dependencies:** Area 2's request and response contract.

**Tasks:**

* [x] `T3.1` **Change:** Add TypeScript types.
  * **Target:** `frontend/src/types/linkTroubleshooter.ts` (`NEW`); `frontend/src/types/index.ts`.
  * **Current → required:** No troubleshooter types → add `LinkTroubleshootRequest`, `LinkTroubleshootKeys`, `LinkTroubleshootRelationship`, `LinkTroubleshootKeyOptions`, `LinkTroubleshootTotals`, `LinkTroubleshootBaseline`, `LinkTroubleshootRow`, `LinkTroubleshootPagination`, `LinkTroubleshootTrial`, `LinkTroubleshootResponse`, and the status/filter union types.
  * **Implementation:** Mirror the backend field names exactly, including `diagnostic_status`, `diagnostic_reason`, and `diagnostic_message` on `LinkTroubleshootBaseline`. Reuse `ValidationError` and `ValidationMetadataValue` from `@/types`. Export the module from `frontend/src/types/index.ts`.
  * **Constraints:** `key_values` is `unknown[]`; callers must format values for display. No `any` beyond the existing project conventions.
  * **Validation:** `V-9`.

* [x] `T3.2` **Change:** Add the API client.
  * **Target:** `frontend/src/api/linkTroubleshooter.ts` (`NEW`); `frontend/src/api/index.ts`; `frontend/src/api/__tests__/linkTroubleshooter.test.ts` (`NEW`).
  * **Current → required:** No troubleshooter API → add `linkTroubleshooterApi.run(projectName: string, request: LinkTroubleshootRequest): Promise<LinkTroubleshootResponse>` that calls `apiRequest` with method `POST`, URL `/projects/${encodeURIComponent(projectName)}/link-troubleshooter`, and the request as `data`.
  * **Implementation:** Test exact URL encoding and body forwarding, following `frontend/src/api/__tests__/validation.test.ts`. Export the module from `frontend/src/api/index.ts` and add `linkTroubleshooter: linkTroubleshooterApi` to its `api` object.
  * **Constraints:** Use `apiRequest` from `./client`; do not create a new axios instance.
  * **Validation:** `V-7`.

* [x] `T3.3` **Change:** Add the warning-to-request helper.
  * **Target:** `frontend/src/utils/linkTroubleshooter.ts` (`NEW`); `frontend/src/utils/__tests__/linkTroubleshooter.test.ts` (`NEW`).
  * **Current → required:** No candidate rule → add:
    * `isLinkTroubleshootCandidate(message: ValidationError): boolean` that requires `message.code === 'ROW_COUNT_MISMATCH'`, a non-empty `message.entity`, `metadata.fk_index` of type `number`, `metadata.fk_signature` of type `string`, `metadata.link_pass` in `initial|after_unnest|deferred_retry`, and `metadata.join_type` in `inner|left`.
    * `toLinkTroubleshootRequest(message: ValidationError): LinkTroubleshootRequest | null` that returns `null` when the candidate rule fails, otherwise returns `{ issue_type: 'row_count_mismatch', local_entity: message.entity, metadata: message.metadata ?? {} }`.
  * **Implementation:** Narrow metadata values explicitly; do not coerce strings to numbers. Test a valid inner warning, a valid left warning, a missing `fk_index`, a missing signature, an unsupported `join_type`, a non-row-count code, and a null entity.
  * **Constraints:** Pure functions; no API calls; no mutation of the message.
  * **Validation:** `V-7`.

* [x] `T3.4` **Change:** Add the composable.
  * **Target:** `frontend/src/composables/useLinkTroubleshooter.ts` (`NEW`); `frontend/src/composables/index.ts`; `frontend/src/composables/__tests__/useLinkTroubleshooter.test.ts` (`NEW`).
  * **Current → required:** No troubleshooter state → add a composable returning `loading`, `error`, `result`, `localKeys`, `remoteKeys`, `page`, `pageSize`, `rowFilter`, `open(request)`, `run()`, and `reset()`.
  * **Implementation:** `open` sends the request with no key lists, stores the response, stores the request identity (`issue_type`, `local_entity`, `metadata`), and initializes `localKeys`/`remoteKeys` from `configured_keys` when present. `run` merges the stored identity with the current keys, page, page size, and filter. On success, update `result`; do not recompute totals from rows. On failure, set `error` with `formatErrorMessage` and keep the last successful result out of the trial display. `reset` clears result, error, keys, page, filter, and the stored identity. Export from `frontend/src/composables/index.ts`.
  * **Constraints:** No local persistence; no cached trial across dialog instances. Do not auto-run on key edits; the dialog calls `run` explicitly.
  * **Validation:** `V-7`.

**Completion evidence:** `V-7` passes; the helper rejects non-candidates and the composable resets cleanly.

### Area 4: Frontend dialog and validation wiring

**Objective:** A user opens the dialog from a supported warning, inspects and trials keys, and discards the trial on close.

**Affected code:** `frontend/src/components/validation/LinkTroubleshooterDialog.vue` (`NEW`), `frontend/src/components/validation/ValidationMessageList.vue`, `frontend/src/components/validation/ValidationPanel.vue`, `frontend/src/views/ProjectDetailView.vue`, component tests (`NEW` and existing), and `frontend/src/components.d.ts` (generated).

**Dependencies:** Area 3; `ValidationPanel.vue` and `ProjectDetailView.vue`.

**Tasks:**

* [ ] `T4.1` **Change:** Add the dialog.
  * **Target:** `frontend/src/components/validation/LinkTroubleshooterDialog.vue` (`NEW`).
  * **Current → required:** No view → add a `v-dialog` with `modelValue`, `projectName`, and `message` props.
  * **Implementation:**
    * Header shows `local_entity → remote_entity` from `relationship`.
    * Show a loading indicator while an open or trial request runs. On a request failure, show `error.message` and any `error.tips`, and do not present the previous trial as a current result.
    * Relationship section shows A, B, join type, link pass, and constraints as read-only text/chips. Do not render editable A/B/join/constraint inputs.
    * Baseline status alert shows `reproduced`, `not_reproduced`, or `ineligible` with `reason` and `message`. For non-reproduced or ineligible, hide the key editor, run button, and A-row table. In stale states, label any count as a current replay count and never as the opened warning's count.
    * Key editor renders ordered pairs from `key_options.local`/`key_options.remote`, initialized from `configured_keys`. Allow adding/removing pairs. Disable Run trial when either side is empty, a pair has an empty key, or the pair counts differ.
    * Comparison table shows baseline and trial values for input A, output, unmatched A, and multiply matched A. Baseline unmatched/multiply values come from the configured-key baseline trial, never from the requested trial. Show `—` for unavailable values and state that complete totals cover the full link input.
    * When the baseline `diagnostic_status` is `failed` or `incomplete`, show `diagnostic_reason` and `diagnostic_message` next to the baseline counts; a complete requested trial can still show its own totals and rows.
    * Findings list shows baseline and trial issues with severity, message, and suggestion.
    * Trial status alert shows `failed`/`incomplete` with `reason` and `message`; no totals or rows are shown in those states.
    * A-row table shows input position, key values using `trial.local_keys` labels, matched status, remote match count, and output contribution. Filter select (`all`, `unmatched`, `multiply_matched`) and page size select (25/50/100/200) call the server. Reset the page to 1 when the filter changes or a new trial starts. Use `v-pagination` with `length = max(1, ceil(filtered_row_count / page_size))`. Never slice a partial result to change totals.
    * Close button resets the composable. No save, apply, or promote action.
    * Watch `modelValue` and `message`: opening loads the current warning through `toLinkTroubleshootRequest`, and closing resets all trial state. Opening a different warning must not show the previous warning's result. If the helper returns `null`, show a local "this warning cannot be troubleshot" message and do not call the API.
  * **Constraints:** Do not mutate response totals. Do not render raw frame data. Keep A/B/join/constraints fixed. Use the composable's `run` for every page or filter change.
  * **Validation:** `V-8`, `V-11`.

* [x] `T4.2` **Change:** Add the action to validation messages and forward it.
  * **Target:** `frontend/src/components/validation/ValidationMessageList.vue`, `frontend/src/components/validation/ValidationPanel.vue`.
  * **Current → required:** Expanded rows have no troubleshooter action → import `isLinkTroubleshootCandidate` in `ValidationMessageList.vue`; render a `v-btn` labeled "Troubleshoot link" in the expanded row only for candidate messages; emit `troubleshoot` with the full message and use `@click.stop`.
  * **Implementation:** Add `troubleshoot` to the component emits. In `ValidationPanel.vue`, add the `troubleshoot` emit and a `listEvents` object with `'open-entity'` and `troubleshoot`; replace the nine `@open-entity` bindings with `v-on="listEvents"`.
  * **Constraints:** No action for non-candidates. Existing severity, expansion, and `open-entity` behavior stays unchanged.
  * **Validation:** `V-8`.

* [ ] `T4.3` **Change:** Wire the dialog into the project view.
  * **Target:** `frontend/src/views/ProjectDetailView.vue`.
  * **Current → required:** No troubleshooter state → add `troubleshootMessage: Ref<ValidationError | null>` and `showLinkTroubleshooter: Ref<boolean>`. Add `handleTroubleshoot(message)` that sets the message and opens the dialog. Bind `@troubleshoot="handleTroubleshoot"` on `validation-panel`. Render `<link-troubleshooter-dialog v-if="troubleshootMessage" v-model="showLinkTroubleshooter" :project-name="projectName" :message="troubleshootMessage" />` and clear the message when the dialog closes.
  * **Implementation:** Import the dialog explicitly, matching the existing `ValidationPanel` import style.
  * **Constraints:** Do not change other tabs or validation behavior. No save action is added.
  * **Validation:** `V-8`, `V-11`.

* [x] `T4.4` **Test:** Cover the dialog and validation wiring.
  * **Target:** `frontend/src/components/validation/__tests__/LinkTroubleshooterDialog.test.ts` (`NEW`); `frontend/src/components/validation/__tests__/ValidationMessageList.test.ts`; `frontend/src/components/validation/__tests__/ValidationPanel.test.ts`.
  * **Current → required:** No troubleshooter component tests → add:
    * Dialog: reproduced baseline shows locked A/B/join/constraints and configured pairs; no editable relationship inputs and no save action.
    * Dialog: when configured keys include `system_id`, show it as the selected configured key and preserve it when running the initial trial.
    * Dialog: ineligible/not-reproduced baseline shows the reason and no key editor/run button/table.
    * Dialog: complete trial shows baseline-vs-trial totals and rows; changing the filter or page calls the API with the same keys and updates the page; displayed complete totals do not change.
    * Dialog: baseline diagnostics `failed`/`incomplete` with a complete requested trial show the baseline diagnostic reason and the trial totals without substituting trial diagnostics for the baseline.
    * Dialog: failed and incomplete requested trials show their alerts and no totals or rows.
    * Dialog: closing resets and reopening starts from configured keys (no retained trial).
    * Message list: candidate message shows "Troubleshoot link"; non-candidate does not; clicking emits `troubleshoot` with the message and does not collapse the row.
    * Panel: forwards `troubleshoot` from a list row.
  * **Implementation:** Stub `VDialog` to render its default slot inline; mock `@/api/linkTroubleshooter` or `@/composables/useLinkTroubleshooter` for deterministic states; use `flushPromises` after API calls. Follow the Vuetify mounting pattern in `ValidationPanel.test.ts`.
  * **Constraints:** Do not make real network calls. Do not assert implementation-private text that is not user-visible.
  * **Validation:** `V-8`.

* [x] `T4.5` **Change:** Regenerate component typing and verify the build.
  * **Target:** `frontend/src/components.d.ts` (generated).
  * **Current → required:** The generated component map does not include the new dialog → run the frontend build so `unplugin-vue-components` updates the file.
  * **Implementation:** Run `pnpm --dir frontend build` after the component exists. Include the generated diff when the generator changes it.
  * **Constraints:** Do not hand-edit `components.d.ts`.
  * **Validation:** `V-9`.

**Completion evidence:** `V-8`, `V-9`, and `V-11` verify the action, locked relationship, comparison, paging/filtering, statuses, authorization, and discard behavior.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
| --- | --- | --- | --- |
| `PH4-AC-1` (from `P-AC-1`) | `T2.2`, `T2.3`, `T2.6`, `T2.7`, `T3.3`, `T4.2`, `T4.3` | `V-2`, `V-3`, `V-4`, `V-7`, `V-8`, `V-9`, `V-11` | Only inner/left `ROW_COUNT_MISMATCH` messages with FK identity show the action; the response identifies A, B, join type, constraints, and the saved FK; ineligible/stale results show no trial controls. |
| `PH4-AC-2` (from `P-AC-3`, `P-AC-4`) | `T1.1`, `T1.2`, `T2.2`, `T2.7`, `T3.4`, `T4.1` | `V-1`, `V-2`, `V-4`, `V-7`, `V-8`, `V-9`, `V-11` | Users change ordered key pairs; baseline totals come from the saved keys and trial totals from the requested keys; filters and pages come from the server; complete totals do not change with the page. |
| `PH4-AC-3` (from `P-AC-5`) | `T2.1`, `T2.2`, `T2.3`, `T3.2`, `T3.4`, `T4.1` | `V-1`, `V-2`, `V-3`, `V-4`, `V-5`, `V-8`, `V-11` | Failed/incomplete results are explicit and have no totals or rows; the route requires project read; page size is capped at 500; closing the dialog resets all trial state. |

Phase-plan milestones: `VM-6` is covered by `V-1`, `V-2`, `V-3`, `V-4`, `V-7`, `V-8`, `V-9`, and `V-11`; `VM-7` by `V-1`–`V-5`, `V-8`, and `V-11`.

Test and build tasks `T1.3`, `T2.4`, `T2.5`, `T3.1`, `T4.4`, and `T4.5` provide the validation evidence mapped through the `V-*` checks above; they do not add separate criteria.

## Validation And Testing

Run from the worktree root with the repository `.venv`. Pytest's configured `-qq -n auto` can omit the pass-count line; exit code 0 is a passing run. Frontend dependencies were installed from the existing lockfile for this implementation.

| ID | Check and target | Command or method | Covers | Expected result | Planning baseline (2026-11-02) | Execution result |
| --- | --- | --- | --- | --- | --- | --- |
| `V-1` | Mapper contract in `backend/tests/mappers/test_link_troubleshooter_mapper.py` (`NEW`) | `.venv/bin/pytest -o addopts='' -q backend/tests/mappers/test_link_troubleshooter_mapper.py` | `PH4-AC-2`, `PH4-AC-3` | Statuses, totals, issues, filters, pages, and JSON-safe values match the expected contract; no frames | Not run: file is new | Pass in the combined backend run (131 tests total, exit 0). |
| `V-2` | Orchestration, real inner/left parity, stale/ineligible, incomplete, paging/filter, and read-only cases in `backend/tests/services/test_link_troubleshooter_service.py` (`NEW`) | `.venv/bin/pytest -o addopts='' -q backend/tests/services/test_link_troubleshooter_service.py` | `PH4-AC-1`–`PH4-AC-3` | Only reproduced baselines run trials; statuses and totals are correct; no cache or project mutation | Not run: file is new. Related Phase 2/3/resolution tests passed (76 tests, exit 0); the combined `V-4` set passed (88 tests, exit 0) | Pass in the combined backend run (131 tests total, exit 0). |
| `V-3` | Authorized route, 422 request validation, denied principal, and service wiring in `backend/tests/api/v1/test_link_troubleshooter.py` (`NEW`) | `.venv/bin/pytest -o addopts='' -q backend/tests/api/v1/test_link_troubleshooter.py` | `PH4-AC-1`, `PH4-AC-3` | 200 for an authorized reader; 422 for invalid page/key body; 404 for denied or missing project; denied callers do not reach the service | Not run: file is new | Pass in the combined backend run (131 tests total, exit 0). |
| `V-4` | Stale-context and missing-`how` regressions in `backend/tests/services/test_link_baseline_service.py`, `backend/tests/services/test_link_trial_service.py`, and `tests/specifications/test_constraints.py`, plus existing Phase 2/3 tests | `.venv/bin/pytest -o addopts='' -q backend/tests/services/test_link_baseline_service.py backend/tests/services/test_link_trial_service.py tests/transforms/test_link_resolution.py tests/specifications/test_constraints.py` | `PH4-AC-1`–`PH4-AC-3` | Existing behavior unchanged; stale results retain FK display context but no frames; trials refuse non-reproduced baselines; a saved `how: null` link records `join_type: inner` and trials as inner | Pass: 88 tests, exit 0 (2026-11-02); new stale-context and missing-`how` assertions not run | Pass in the combined backend run (131 tests total, exit 0). |
| `V-5` | Read-only and cache checks within the new service and route tests | Included in `V-2` and `V-3`; patch `ShapeShiftCache.set_dataframe`, `set_table_store`, `fetch_cached_entity_data`, and `ShapeShiftProjectCache.get_project` to raise, and snapshot the saved API/Core project | `PH4-AC-3` | No cache method is called; the saved project is unchanged; frames are not serialized | Not run: new tests | Pass in the combined backend run (131 tests total, exit 0). |
| `V-6` | Python formatting and type checks on changed/new files | Run the exact commands in the block below from the worktree root | Code quality | Exit 0; record any existing diagnostics separately | Not run: Phase 4 changes are not implemented | Black, isort, and Pyright pass. Pylint exits 8 on the pre-existing `R0916` in `LinkTrialService._validate_key_selection` (6 boolean expressions); that method was not changed. |
| `V-7` | Frontend helper, API, and composable tests | `pnpm --dir frontend test:run src/utils/__tests__/linkTroubleshooter.test.ts src/api/__tests__/linkTroubleshooter.test.ts src/composables/__tests__/useLinkTroubleshooter.test.ts` | `PH4-AC-1`–`PH4-AC-3` | Candidate rules, request URL/body, state transitions, error handling, and reset pass | Not run: `frontend/node_modules` is absent | Pass: 11 tests across 3 files. |
| `V-8` | Frontend dialog, message-list, and panel tests | `pnpm --dir frontend test:run src/components/validation/__tests__/LinkTroubleshooterDialog.test.ts src/components/validation/__tests__/ValidationMessageList.test.ts src/components/validation/__tests__/ValidationPanel.test.ts` | `PH4-AC-1`–`PH4-AC-3` | Locked relationship, key editing, totals, server paging/filtering, statuses, action visibility, and reset pass | Not run: `frontend/node_modules` is absent | Pass: 27 tests across 3 files. |
| `V-9` | Frontend type check and build, including generated component typing | `pnpm --dir frontend build` | `PH4-AC-1`–`PH4-AC-3` | `vue-tsc` and the Vite build pass; `components.d.ts` is regenerated without hand edits | Not run: `frontend/node_modules` is absent | Pass: `vue-tsc` and Vite build; generated `components.d.ts` includes `LinkTroubleshooterDialog`. Existing Rollup and chunk-size warnings remain. |
| `V-10` | Frontend lint | `pnpm --dir frontend exec eslint src` (no `--fix`) | Code quality | Exit 0 or only pre-existing findings outside changed files | Not run: `frontend/node_modules` is absent | Pass: exit 0, 0 errors; 12 pre-existing formatting warnings remain in unchanged files. |
| `V-11` | Manual user flow | Run the backend and frontend; open a project with an inner-join `ROW_COUNT_MISMATCH`; open Validation; click "Troubleshoot link"; verify locked A/B/join/constraints, configured keys, baseline totals, key change, trial totals, unmatched/multiple filters, page navigation, stale/ineligible/incomplete states, no save action, and a fresh view after close/reopen | `PH4-AC-1`–`PH4-AC-3` | The flow matches the dialog contract; totals stay fixed across pages; closing discards the trial | Not run: manual | Not run: no live interactive project flow was exercised; automated V-7/V-8 checks passed. |
| `V-12` | Documentation links | `scripts/check_doc_links.sh` | Documentation | "Documentation links are valid." | Pass (2026-11-02) | Pass: "Documentation links are valid." |

V-6 commands (run after the listed files exist):

```bash
PYTHON_TARGETS=(
  backend/app/models/link_troubleshooter.py
  backend/app/models/__init__.py
  backend/app/mappers/link_troubleshooter_mapper.py
  backend/app/services/link_baseline_service.py
  backend/app/services/link_trial_service.py
  backend/app/services/link_troubleshooter_service.py
  backend/app/api/v1/endpoints/link_troubleshooter.py
  backend/app/api/v1/api.py
  src/specifications/constraints.py
  backend/tests/mappers/test_link_troubleshooter_mapper.py
  backend/tests/services/test_link_baseline_service.py
  backend/tests/services/test_link_trial_service.py
  backend/tests/services/test_link_troubleshooter_service.py
  backend/tests/api/v1/test_link_troubleshooter.py
  tests/specifications/test_constraints.py
)
TYPE_TARGETS=(
  backend/app/models/link_troubleshooter.py
  backend/app/models/__init__.py
  backend/app/mappers/link_troubleshooter_mapper.py
  backend/app/services/link_baseline_service.py
  backend/app/services/link_trial_service.py
  backend/app/services/link_troubleshooter_service.py
  backend/app/api/v1/endpoints/link_troubleshooter.py
  backend/app/api/v1/api.py
  src/specifications/constraints.py
)

.venv/bin/black --check "${PYTHON_TARGETS[@]}"
.venv/bin/isort --check-only "${PYTHON_TARGETS[@]}"
.venv/bin/pyright --pythonpath .venv/bin/python --threads 2 "${TYPE_TARGETS[@]}"
.venv/bin/pylint -j 0 "${TYPE_TARGETS[@]}"
```

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Troubleshooter API models | `backend/app/models/link_troubleshooter.py` (`NEW`), `backend/app/models/__init__.py` | `T1.1` | `V-1`, `V-3` |
| Response mapper | `backend/app/mappers/link_troubleshooter_mapper.py` (`NEW`) | `T1.2` | `V-1` |
| Mapper tests | `backend/tests/mappers/test_link_troubleshooter_mapper.py` (`NEW`) | `T1.3` | `V-1` |
| Stale display context | `backend/app/services/link_baseline_service.py` | `T2.1` | `V-4` |
| Warning join-type metadata | `src/specifications/constraints.py`, `tests/specifications/test_constraints.py` | `T2.6` | `V-2`, `V-4` |
| Missing-`how` trial consistency | `backend/app/services/link_trial_service.py`, `backend/tests/services/test_link_trial_service.py` | `T2.7` | `V-2`, `V-4` |
| Original and trial orchestration | `backend/app/services/link_troubleshooter_service.py` (`NEW`) | `T2.2` | `V-2`, `V-5` |
| Authorized route | `backend/app/api/v1/endpoints/link_troubleshooter.py` (`NEW`), `backend/app/api/v1/api.py` | `T2.3` | `V-3` |
| Orchestration tests | `backend/tests/services/test_link_troubleshooter_service.py` (`NEW`) | `T2.4` | `V-2`, `V-5` |
| Route tests | `backend/tests/api/v1/test_link_troubleshooter.py` (`NEW`) | `T2.5` | `V-3`, `V-5` |
| Frontend types | `frontend/src/types/linkTroubleshooter.ts` (`NEW`), `frontend/src/types/index.ts` | `T3.1` | `V-9` |
| Frontend API client and test | `frontend/src/api/linkTroubleshooter.ts` (`NEW`), `frontend/src/api/index.ts`, `frontend/src/api/__tests__/linkTroubleshooter.test.ts` (`NEW`) | `T3.2` | `V-7` |
| Warning helper and test | `frontend/src/utils/linkTroubleshooter.ts` (`NEW`), `frontend/src/utils/__tests__/linkTroubleshooter.test.ts` (`NEW`) | `T3.3` | `V-7` |
| Composable and test | `frontend/src/composables/useLinkTroubleshooter.ts` (`NEW`), `frontend/src/composables/index.ts`, `frontend/src/composables/__tests__/useLinkTroubleshooter.test.ts` (`NEW`) | `T3.4` | `V-7` |
| Troubleshooter dialog | `frontend/src/components/validation/LinkTroubleshooterDialog.vue` (`NEW`) | `T4.1` | `V-8`, `V-11` |
| Warning action and forwarding | `frontend/src/components/validation/ValidationMessageList.vue`, `frontend/src/components/validation/ValidationPanel.vue` | `T4.2` | `V-8` |
| Project-view wiring | `frontend/src/views/ProjectDetailView.vue` | `T4.3` | `V-8`, `V-11` |
| Component tests | `frontend/src/components/validation/__tests__/LinkTroubleshooterDialog.test.ts` (`NEW`), `ValidationMessageList.test.ts`, `ValidationPanel.test.ts` | `T4.4` | `V-8` |
| Generated component typing | `frontend/src/components.d.ts` (generated) | `T4.5` | `V-9` |

After code changes, refresh the repository knowledge graph with `GRAPHIFY_VIZ_NODE_LIMIT=0 graphify update .`; graph output is not part of this phase's code deliverable. This task plan is the only documentation change during planning.

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Backend response contract and mapper | Done | Phase 2/3 result types | `V-1` passed; mapper contract and bounded JSON-safe response verified. |
| Area 2: Backend orchestration and route | Done | Area 1; Phase 2/3 services | `V-2`–`V-5` passed; `V-6` records one pre-existing Pylint diagnostic. |
| Area 3: Frontend types, API, helper, composable | Done | Area 2 contract | `V-7` and frontend type/build checks passed. |
| Area 4: Frontend dialog and validation wiring | In progress | Area 3; validation panel/view | `V-8`/`V-9` passed; `V-11` and task evidence for `T4.1`/`T4.3` remain outstanding. |

## Definition Of Done

* [x] `PH4-AC-1`, `PH4-AC-2`, and `PH4-AC-3` each have implementation and passing automated validation evidence (`V-1`–`V-9`); the manual `V-11` flow remains unrun.
* [ ] All four work areas and the deliverables table are complete; the progress table shows Done.
* [x] The route requires project read authorization, uses the authorized locator, and returns 404 for denied or missing projects.
* [x] The response page is capped at 500 rows; complete totals come from the full trial, not the page.
* [x] Stale, ineligible, failed, and incomplete states are explicit; no stale warning is presented as a current trial result.
* [x] No trial writes the saved project, production cache, or any server-side session; closing the dialog resets frontend state.
* [x] A/B, join type, and constraints are read-only; no save, apply, or promote action exists.
* [x] Backend and frontend tests pass; the pre-existing Pylint diagnostic is recorded separately.
* [x] `components.d.ts` is regenerated through the build, not hand-edited.
* [x] No unresolved design question affects implementation or correctness; the unrun manual check is recorded in `V-11`.

## Risks And Open Questions

- **Each request replays the pipeline, and alternative-key requests run two trials.** A stateless design avoids server-side trial state and cache risk, but opening, running, paging, and filtering all rebuild the baseline. An alternative-key request also runs the configured-key baseline trial before the requested trial. The output-row limit applies to each trial. If latency becomes a problem, add a bounded in-memory session keyed to the principal, project, and warning identity outside this phase; do that only with a new decision because it reintroduces discard and authorization concerns.
- **Baseline diagnostics can be unavailable when the requested trial is available.** The configured keys can exceed the output-row limit or fail a constraint while an alternative key pair succeeds. The response keeps the baseline counts and reports `diagnostic_status`/`diagnostic_reason`; it must not substitute the requested trial's diagnostics for the baseline.
- **The client-side action predicate cannot detect signature drift.** The frontend shows the action for inner/left warnings with identity metadata; the backend re-resolves against the current saved project and returns `ineligible` with no trial controls when the signature no longer matches. No wrong link is opened. Removing the action entirely for drifted warnings would require a server-computed eligibility flag in the validation payload; defer that unless users report confusion.
- **The page cap bounds row count, not bytes.** Individual key values follow the source data. Do not describe the 500-row page cap as a memory limit.
- **Trial execution is synchronous pandas work in an async route.** The computation cap bounds the work; the existing quick Test Join has the same pattern. If large trials delay other requests, move `run_trial` to a thread pool in a follow-up, not by changing the trial algorithm here.
- **The baseline context extension must remain display-only.** `_saved_project` and `_foreign_key` may be retained for stale results, but `local_rows`/`remote_rows` must stay `None` and `LinkTrialService` must continue to refuse non-reproduced baselines.
- **Manual UI flow remains unverified.** `V-11` was not run; automated helper, component, and build checks passed, but the live project flow still needs manual verification.
- **Implementation handoff:** If verified repository state conflicts with this plan, stop and report the evidence. Do not invent a replacement design or broaden the phase to a saved trial, right/outer/cross joins, or a session store.

**Open questions:** None that change the Phase 4 design.
