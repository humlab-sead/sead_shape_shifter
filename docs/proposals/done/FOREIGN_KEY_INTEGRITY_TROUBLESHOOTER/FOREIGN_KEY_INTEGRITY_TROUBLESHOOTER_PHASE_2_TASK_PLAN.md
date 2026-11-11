# Foreign-Key Integrity Troubleshooter — Phase 2 Task Plan

## Phase Summary

**Phase:** [Phase 2: Recompute and inspect unmatched data](./FOREIGN_KEY_INTEGRITY_TROUBLESHOOTER_PHASE_PLAN.md#phase-2-recompute-and-inspect-unmatched-data)  
**Source:** [Foreign-Key Integrity Troubleshooter](./FOREIGN_KEY_INTEGRITY_TROUBLESHOOTER.md)  
**Readiness:** **Validated.** The phase plan marks Phase 2 ready: D1 fixes the current full-normalization source and count comparison, and D2 fixes bounds, columns, response shape, selection, and changed-data behavior. Verified targets and executable validation checks are listed below. `reproduced` does not claim that the original dataset or sample run was replayed.

Return an authorized, read-only integrity result for the saved foreign key, distinguishing a reproduced count from changed or unavailable data. Phase 1's issue identity and saved-link resolver are complete; the existing row-count troubleshooter remains unchanged. This phase covers `VM-2`, not the Phase 3 dialog.

**Acceptance criteria**

1. [x] `PH2-AC-1` (from `P-AC-2`, `P-AC-3`): Reproduction uses the validator's count and null rules; a changed count or unavailable input does not claim reproduction or present an old count as current.
2. [x] `PH2-AC-2` (from `P-AC-4`): Distinct unmatched values have correct local row counts, deterministic order and truncation, and separate complete and returned counts.
3. [x] `PH2-AC-3` (from `P-AC-5`): Selecting a value returns only bounded local rows, with the inspected data source and returned columns stated.
4. [x] `PH2-AC-4` (from `P-AC-6`, `P-AC-7`): Every inspection call requires project read authorization, makes no writes, and leaves the row-count endpoint and response unchanged.

**Dependencies and constraints:** Use Phase 1's `fk_index`, `fk_signature`, and `orphan_count` metadata and `resolve_integrity_issue`. Inspect current full-normalization frames for the saved link and current authorized project through a private, read-only run; use the same normalized frame stage as complete validation. Do not change the existing warning's field, row-count models, eligibility, requests, or response. No frontend action is included in this phase.

## Repository Findings

**Repository basis:** `feature/foreign-key-integrity-trouble-shooter` at `6656d29f`, 2026-11-06. The worktree was clean during inspection. Graphify was used for navigation; the following findings were checked against current code and tests. Phase 1's task tracker marks both areas Done.

| Evidence | Verified finding | Planning implication |
| --- | --- | --- |
| [`src/validators/data_validators.py::ForeignKeyIntegrityValidator.validate`](../../../../src/validators/data_validators.py), [`backend/app/validators/data_validation_orchestrator.py::DataValidationOrchestrator._validate_entity`](../../../../backend/app/validators/data_validation_orchestrator.py) | The validator compares distinct local and remote keys, drops null key parts unless `null_keys_equal` is set, and records the distinct `orphan_count`. It returns no issue for missing keys, no local keys, or a now-clean link; an empty/unjoinable remote key produces `FK_REMOTE_EMPTY`. The orchestrator supplies the fetched frames. | Call the validator for the current count; distinguish a zero/clean result from missing inputs and non-integrity outcomes. Extract any shared value comparison into pure Core code rather than independently implementing incompatible null or deduplication rules. |
| [`src/transforms/link_resolution.py::resolve_integrity_issue`](../../../../src/transforms/link_resolution.py), [`backend/app/services/link_baseline_service.py::LinkBaselineService.build_baseline`](../../../../backend/app/services/link_baseline_service.py) | Phase 1 resolves the saved index/signature without a join-type restriction. The row-count baseline loads the saved project, converts via `ProjectMapper.to_core`, and performs a distinct link-pass replay requiring row-count metadata. | Resolve the integrity link from the authorized saved project, but do not reuse row-count replay, link-pass requirements, or trial models. |
| [`backend/app/services/validation_service.py::ValidationService.validate_project_data`](../../../../backend/app/services/validation_service.py), [`backend/app/validators/data_validation_orchestrator.py::PreviewDataFetchStrategy`, `FullDataFetchStrategy`, `SinglePassDataFetchStrategy`](../../../../backend/app/validators/data_validation_orchestrator.py), [`backend/app/models/validation.py::ValidationResult`](../../../../backend/app/models/validation.py) | Validation can use preview samples (default limit 1000), complete normalization, or single-pass normalization. `ValidationResult.validation_mode` records the run mode; individual issue metadata does not. | D1 chooses current full normalization regardless of the warning's original mode. Compare counts as a current full-data claim, identify that source in the response, and do not claim historical dataset or sample-run equivalence. |
| [`backend/app/services/shapeshift_service.py::ShapeShiftService.normalize_project`](../../../../backend/app/services/shapeshift_service.py), [`backend/app/services/link_baseline_service.py::LinkBaselineService._replay`](../../../../backend/app/services/link_baseline_service.py) | `normalize_project` populates a shared cache and warm table store. The existing row-count replay uses a private `ShapeShifter`/`TableStore`; its tests assert no shared-cache calls and cleanup on failure. | Run full normalization against a private table store, not through the shared-cache service. Verify source and project data remain unchanged and resources close on success and failure. |
| [`backend/app/api/v1/endpoints/link_troubleshooter.py::run_link_troubleshooter`](../../../../backend/app/api/v1/endpoints/link_troubleshooter.py), [`backend/app/authorization/dependencies.py::require_project`](../../../../backend/app/authorization/dependencies.py), [`backend/app/api/v1/api.py`](../../../../backend/app/api/v1/api.py) | The existing POST endpoint uses `require_project(Action.READ)` and passes the authorized locator to its service. The router is registered under API v1. | Add a separate authorized endpoint and integrity-only response model without changing the shipped route. |
| [`backend/tests/api/v1/test_link_troubleshooter.py`](../../../../backend/tests/api/v1/test_link_troubleshooter.py), [`backend/tests/services/test_link_baseline_service.py`](../../../../backend/tests/services/test_link_baseline_service.py), [`tests/validators/test_data_validators.py`](../../../../tests/validators/test_data_validators.py) | Protected-route tests create an API project with `authorized_client`; service tests use in-memory frames; validator tests cover distinct counts, composite keys, and null equality. | Extend these patterns for authorization, count parity, selected values, bounded rows, no writes, and row-count regression. |

## Scope

**In scope:** Pure unmatched-key comparison shared with the existing validator; a backend inspection service for current frames and current counts; an integrity-only request/response contract and route; bounded deterministic value pages and selected local-row samples; focused Core, service, and authorized API tests.

**Out of scope:** The Phase 3 frontend action/dialog, arbitrary key trials, edits or repairs, reconciliation, other FK warning kinds, changing the existing row-count API, and storing source data or inspection results.

**Affected contracts:** `FK_DATA_INTEGRITY` issue metadata and saved-FK resolution are inputs; the new POST `/api/v1/projects/{project_name}/integrity-troubleshooter` is the output. It uses current full normalization and a single response envelope for one fixed-size value page with optional selected rows. Each call recomputes current data; there is no snapshot or cross-request fingerprint. All proposed files are marked `NEW`.

## Work Breakdown

### Area 1: Recompute the saved warning from a read-only source

**Objective:** Resolve the warning and return an honest reproduction status from current authorized data.

**Affected code:** `src/validators/data_validators.py::ForeignKeyIntegrityValidator.validate`; `backend/app/services/validation_service.py::ValidationService.validate_project_data` and `backend/app/validators/data_validation_orchestrator.py` as references for data acquisition; `src/transforms/link_resolution.py::resolve_integrity_issue`; `backend/app/services/integrity_troubleshooter_service.py` (**NEW**); `tests/validators/test_data_validators.py`; `backend/tests/services/test_integrity_troubleshooter_service.py` (**NEW**).

**Dependencies:** Phase 1's saved-link identity and issue count. D1 is resolved: always use current full normalization.

**Tasks:**

* [x] `T1.1` **Change:** Make the validator's unmatched comparison reusable for count and values.
  * **Target:** `src/validators/data_validators.py::ForeignKeyIntegrityValidator.validate` and a pure helper in the same file (**NEW symbol**).
  * **Current → required:** The validator exposes only a count and at most ten message examples → expose the current distinct unmatched keys to the service without duplicating matching rules.
  * **Implementation:** Extract only the comparison logic needed by the validator and inspection, preserving separate `FK_REMOTE_EMPTY` handling, null semantics, composite tuple matching, warning metadata, and the existing message behavior. Do not fetch inside Core. Distinguish invalid/missing inputs from an empty unmatched set.
  * **Validation:** `V-1`: extend `tests/validators/test_data_validators.py` with repeated local keys, composite partially null keys with `null_keys_equal` on/off, clean inputs, missing columns, and empty or all-null remote keys; assert the validator's count and the reusable distinct set agree where comparison is possible.

* [x] `T1.2` **Change:** Build an inspection result for the resolved saved link.
  * **Target:** `backend/app/services/integrity_troubleshooter_service.py` (**NEW**) and `backend/tests/services/test_integrity_troubleshooter_service.py` (**NEW**).
  * **Current → required:** No integrity inspection service exists → load and map the authorized saved project, call `resolve_integrity_issue`, normalize the current project in a private `ShapeShifter`/`TableStore` without shared-cache or source writes, fetch both frames at the same stage as complete validation, and call `ForeignKeyIntegrityValidator.validate`.
  * **Implementation:** Validate `orphan_count` as an integer, not a boolean; map resolver failures to `ineligible` with its named reason. For missing/failed full normalization, missing columns, or `FK_REMOTE_EMPTY`, return `not_reproduced` with a reason, not an empty reproduced result. Set `reproduced` when a current full-data `FK_DATA_INTEGRITY` issue has the recorded distinct count, including when the original warning came from sample validation; this is count equality on current full data, not replay of the original frames. On a clean link treat current count as zero and report `not_reproduced`. Keep current counts separate from the recorded warning count and label current values even if the set changed without changing its size.
  * **Constraints:** Use a fresh saved-project snapshot and private table store rather than the cache-writing `ShapeShiftService.normalize_project` path; handle normalization failures and resource cleanup. Do not expose frames in API models or silently turn absent data into zero.
  * **Validation:** `V-2`: in `backend/tests/services/test_integrity_troubleshooter_service.py` use a saved project and in-memory local/remote data to assert matching, changed, sample-origin matching/nonmatching, and equal-count/different-set cases; missing input, missing metadata, stale signature, `FK_REMOTE_EMPTY`, `null_keys_equal`, right/outer join, no cache writes, and no mutations. Compare the result against complete production validation on the same full-normalization frames.

**Completion evidence:** Service tests show a current count, named refusal/non-reproduction, count parity, and no side effects for the approved source strategy.

### Area 2: Page unmatched values and select bounded local rows

**Objective:** Return every distinct unmatched key across bounded, repeatable value pages and only a bounded sample of rows for an explicit selected key.

**Affected code:** `backend/app/services/integrity_troubleshooter_service.py` (**NEW**); `backend/app/models/integrity_troubleshooter.py` (**NEW**); `backend/tests/services/test_integrity_troubleshooter_service.py` (**NEW**).

**Dependencies:** Area 1; D2 is resolved.

**Tasks:**

* [x] `T2.1` **Change:** Produce deterministically ordered, bounded distinct-value pages.
  * **Target:** `backend/app/services/integrity_troubleshooter_service.py` (**NEW**) and `backend/app/models/integrity_troubleshooter.py` (**NEW**).
  * **Current → required:** The warning message contains only ten example values → return the current unmatched key tuple(s), each with the count of local rows carrying it, a complete distinct-value count, a returned count, and a page/truncation indicator.
  * **Implementation:** Use the shared comparison result to select unmatched keys; count local rows before value deduplication, with the same null handling as the validator. Define a stable total order for mixed and null scalar types, without relying on the validator's unordered sample set. Return 50 distinct values per page at most, with page number, complete distinct count, returned count, and `has_next`. Accept page numbers starting at 1; reject invalid page numbers through the request model and return an empty page beyond the last page. Encode key values for JSON without losing type information needed for selection, and verify the complete count equals the validator's current count. No snapshot or fingerprint is required; only unchanged data must yield stable pages.
  * **Validation:** `V-3`: in `backend/tests/services/test_integrity_troubleshooter_service.py`, exercise duplicate rows, composite/null keys, mixed values, 51 or more distinct keys, the last and beyond-last pages, invalid pages, and repeated requests on unchanged data; assert stable order, complete versus returned counts, per-value row counts, and the 50-value cap. Change the unmatched set between requests and assert each result represents its own current run without asserting cross-request page consistency.

* [x] `T2.2` **Change:** Return bounded rows for a selected unmatched key.
  * **Target:** `backend/app/services/integrity_troubleshooter_service.py` (**NEW**) and `backend/app/models/integrity_troubleshooter.py` (**NEW**).
  * **Current → required:** No local-row context exists → select by a server-issued type-preserving token for the ordered key tuple, never by its position in a value page; return only local rows with that current unmatched key.
  * **Implementation:** Encode each tuple with explicit scalar types and nulls in a deterministic token that can be decoded without stored server state; validate token shape and types and confirm membership in the current unmatched set for this saved FK. Return at most 20 local rows in deterministic order, with the complete matching-row count. Select available saved local keys first, business keys second, then target-facing columns from `TableConfig.get_target_facing_columns()` in their existing order, deduplicated and capped at 20 total; exclude other source and internal columns. State the actual source, returned column names, and whether columns were truncated. If mandatory FK keys alone exceed 20 columns, refuse the row sample with a named reason instead of omitting a key. If a valid selected token no longer names a current unmatched value, return an explicit selected-value-unavailable result with no rows; retain the independently computed current warning status. Do not accept arbitrary entity names or column selections from the token.
  * **Validation:** `V-3`: in `backend/tests/services/test_integrity_troubleshooter_service.py`, select a composite key after changing pages, verify only matching rows and up to 20 allowed columns, check 21 or more matching rows, omitted-column reporting, excess mandatory FK columns, null and mixed-type round trips, tampered/invalid tokens, and a value that becomes matched between requests. Assert a named unavailable selection result with no rows, not a stale sample.

**Completion evidence:** Tests prove bounded pages and row samples, token-based selection independent of page position, explicit changed-selection results, and correct counts and source/column declarations.

### Area 3: Expose the separate protected endpoint and regress row-count behavior

**Objective:** Return the integrity envelope through a project-read-protected endpoint without modifying existing row-count contracts.

**Affected code:** `backend/app/api/v1/endpoints/integrity_troubleshooter.py` (**NEW**); `backend/app/models/integrity_troubleshooter.py` (**NEW**); `backend/app/api/v1/api.py`; `backend/tests/api/v1/test_integrity_troubleshooter.py` (**NEW**); existing row-count tests.

**Dependencies:** Areas 1 and 2.

**Tasks:**

* [x] `T3.1` **Change:** Add the integrity request, response, and endpoint.
  * **Target:** `backend/app/models/integrity_troubleshooter.py` (**NEW**), `backend/app/api/v1/endpoints/integrity_troubleshooter.py` (**NEW**), and `backend/app/api/v1/api.py`.
  * **Current → required:** Only the row-count route exists → register the proposal's separate POST route with `require_project(Action.READ)` and forward only `authorized_project.resource.locator` to the inspection service.
  * **Implementation:** Carry issue kind, local entity, metadata, page (default 1), and an optional server-issued selected-value token; enforce the fixed page and row caps on the server. Return status (`reproduced`, `not_reproduced`, `ineligible`), named reason/message, saved relationship with configured keys/constraints, source identified as current full normalization, complete and returned value counts, value row counts and tokens, page/`has_next`, and optionally the selected-value status, total/returned row counts, rows, column names and truncation flag. Do not reuse `LinkTroubleshootResponse` or include trial fields. Authenticate and authorize every call, including later pages and selected-value requests.
  * **Validation:** `V-4`: in `backend/tests/api/v1/test_integrity_troubleshooter.py` (**NEW**), create a project with `authorized_client`; assert the single authorized response shape, default page and optional rows, current-only selection refusal, invalid page or token `422` without running the service when validation is possible at the model boundary, unauthorized/cross-project/missing-project concealed `404` without a service call, and protection on subsequent page/selection calls.

* [x] `T3.2` **Change:** Prove read-only behavior and row-count compatibility.
  * **Target:** `backend/tests/services/test_integrity_troubleshooter_service.py` (**NEW**) and the existing `backend/tests/api/v1/test_link_troubleshooter.py`, `backend/tests/services/test_link_baseline_service.py`, `backend/tests/services/test_link_troubleshooter_service.py`, and `backend/tests/mappers/test_link_troubleshooter_mapper.py`.
  * **Current → required:** The original route and result work today → retain byte-for-byte response shape for existing test fixtures and make no project, source, or shared-cache writes on any inspection outcome.
  * **Implementation:** Add assertions for project/model/frame snapshots and cache-writing calls to the new service tests. Run the existing row-count suites without changing their models or routes.
  * **Validation:** `V-2`, `V-4`, `V-5`.

**Completion evidence:** Route/authorization tests and row-count regression suites pass with no write operations.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
| --- | --- | --- | --- |
| `PH2-AC-1` (`P-AC-2`, `P-AC-3`) | `T1.1`, `T1.2` | `V-1`, `V-2` | Validator parity, honest changed/unavailable status and current source. |
| `PH2-AC-2` (`P-AC-4`) | `T1.1`, `T2.1` | `V-1`, `V-3` | Every distinct value reachable by 50-value pages for unchanged data, correct complete/returned counts and local row counts. |
| `PH2-AC-3` (`P-AC-5`) | `T2.2`, `T3.1` | `V-3`, `V-4` | Type-preserving selected-key lookup, at most 20 current local rows and 20 declared columns, stated source and column names. |
| `PH2-AC-4` (`P-AC-6`, `P-AC-7`) | `T1.2`, `T3.1`, `T3.2` | `V-2`, `V-4`, `V-5` | Project-read authorization on each call, no writes, unchanged row-count request/response. |

## Validation And Testing

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
| --- | --- | --- | --- | --- | --- |
| `V-1` | Validator parity, `tests/validators/test_data_validators.py` | `uv run pytest -n 0 tests/validators/test_data_validators.py -q` | `PH2-AC-1`, `PH2-AC-2` | Existing warnings preserved; added shared-comparison assertions pass. | Pass: included in the targeted prerequisite run below. |
| `V-2` | Inspection service, `backend/tests/services/test_integrity_troubleshooter_service.py` (**NEW**) | `uv run pytest -n 0 backend/tests/services/test_integrity_troubleshooter_service.py -q` | `PH2-AC-1`, `PH2-AC-4` | Full-data count parity, sample-origin warning comparison, source label, failures, read-only behavior, and resource cleanup pass. | Pass: 20 tests passed, including parity with `ForeignKeyIntegrityValidator` on the same full-normalization frames and a no-shared-cache assertion. |
| `V-3` | Bounded data, same **NEW** service test file | `uv run pytest -n 0 backend/tests/services/test_integrity_troubleshooter_service.py -q` | `PH2-AC-2`, `PH2-AC-3` | 50-value pages, 20-row samples, 20-column cap, typed tokens, stale-selection outcome, and per-request current data pass without a fingerprint. | Pass: covered by the same 20-test service run, including page boundaries, per-value row counts, token selection after paging, and changed-value refusal. |
| `V-4` | Protected API, `backend/tests/api/v1/test_integrity_troubleshooter.py` (**NEW**) | `uv run pytest -n 0 backend/tests/api/v1/test_integrity_troubleshooter.py -q` | `PH2-AC-3`, `PH2-AC-4` | One response envelope, optional selected rows, input rejection, project read and cross-project denial on every call. | Pass: 10 tests passed for forwarding, response shape, `422` model rejection, concealed `404`, and later page/selection protection. |
| `V-5` | Existing Phase 1 and row-count regressions | `uv run pytest -n 0 tests/transforms/test_link_resolution.py backend/tests/validators/test_data_validation_orchestrator.py backend/tests/api/v1/test_link_troubleshooter.py backend/tests/services/test_link_baseline_service.py backend/tests/services/test_link_troubleshooter_service.py backend/tests/mappers/test_link_troubleshooter_mapper.py -q` | `PH2-AC-4`, Phase 1 dependency | Existing resolver, validation, authorization, trial and response tests still pass. | Pass: covered in two completed targeted runs (`rtk uv run pytest -n 0 tests/validators/test_data_validators.py tests/transforms/test_link_resolution.py backend/tests/validators/test_data_validation_orchestrator.py backend/tests/api/v1/test_link_troubleshooter.py -q`; `rtk uv run pytest -n 0 backend/tests/services/test_link_baseline_service.py backend/tests/services/test_link_troubleshooter_service.py backend/tests/mappers/test_link_troubleshooter_mapper.py -q`). |
| `V-6` | Formatting and lint on changed Python files | `uv run black --check src/validators/data_validators.py backend/app/services/integrity_troubleshooter_service.py backend/app/models/integrity_troubleshooter.py backend/app/api/v1/endpoints/integrity_troubleshooter.py backend/app/api/v1/api.py tests/validators/test_data_validators.py backend/tests/services/test_integrity_troubleshooter_service.py backend/tests/api/v1/test_integrity_troubleshooter.py`; `uv run ruff check src/validators/data_validators.py backend/app/services/integrity_troubleshooter_service.py backend/app/models/integrity_troubleshooter.py backend/app/api/v1/endpoints/integrity_troubleshooter.py backend/app/api/v1/api.py tests/validators/test_data_validators.py backend/tests/services/test_integrity_troubleshooter_service.py backend/tests/api/v1/test_integrity_troubleshooter.py` | All | No new formatting/lint errors; include any additional modified Python files in both commands. | Pass: `black --check` reports the 8 files unchanged; `ruff check` reports no issues; `pyright` reports 0 errors on the changed modules and tests. |

`VM-2` requires `V-1` through `V-5` after implementation; run all new and regression suites together for the final check. No migration or generated artifact is planned. Stop and report evidence if implementation-time repository state differs materially from these findings; do not silently substitute a new source strategy or broaden this phase.

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Shared comparison | `src/validators/data_validators.py::ForeignKeyIntegrityValidator.validate` and pure helper (**NEW symbol**) | `T1.1` | Existing warnings and comparison parity tested. |
| Read-only inspection | `backend/app/services/integrity_troubleshooter_service.py` (**NEW**) | `T1.2`, `T2.1`, `T2.2` | Correct statuses, bounded current values/rows, no side effects. |
| Integrity contract | `backend/app/models/integrity_troubleshooter.py` (**NEW**) | `T2.1`, `T2.2`, `T3.1` | Validated bounded requests and distinct response envelope. |
| Protected API | `backend/app/api/v1/endpoints/integrity_troubleshooter.py` (**NEW**); `backend/app/api/v1/api.py` | `T3.1` | Route registered and protected by project read. |
| Focused tests | `tests/validators/test_data_validators.py`; `backend/tests/services/test_integrity_troubleshooter_service.py` (**NEW**); `backend/tests/api/v1/test_integrity_troubleshooter.py` (**NEW**) | `T1.1`, `T1.2`, `T2.1`, `T2.2`, `T3.1`, `T3.2` | `V-1` through `V-4` pass. |
| Regression checks | Existing row-count and Phase 1 test files listed under `V-5` | `T3.2` | `V-5` passes without changing row-count contracts. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Recompute warning | Done | Phase 1 (Done) | D1 fixed to current full normalization. |
| Area 2: Page values and rows | Done | Area 1 | D2 fixes limits, columns, token and current-data behavior. |
| Area 3: Protect endpoint | Done | Areas 1–2 | One endpoint and response envelope for values and optional rows. |

## Definition Of Done

* [x] D1 and D2 are resolved; the phase is ready for this Validated task plan. This does not mark implementation complete.
* [x] `PH2-AC-1` through `PH2-AC-4` each have passing task and validation evidence.
* [x] All work areas and listed deliverables are complete; `V-1` through `V-6` pass.
* [x] A changed set with an equal count is shown as current; missing data never becomes a success-shaped empty result.
* [x] Each inspection call is authorized, bounded, and read-only; the existing row-count contract is regression-tested unchanged.
* [x] No unresolved choice affects implementation, correctness, or validation; deviations and follow-up work are recorded.

## Risks And Open Questions

* **D1 — Resolved:** Inspection uses current full normalization from a private run and states that source in the response. Count equality with `orphan_count` means the warning's numeric claim is reproduced on current full data, even for an original sample-mode warning; it does not prove the original rows or unmatched set are unchanged. An unavailable full run yields `not_reproduced` with a named reason. This clarifies the source-establishment wording in the source proposal's Planning Handoff without changing its count-based acceptance criteria.
* **D2 — Resolved:** Use fixed pages of 50 values, 20 sampled rows for one selected value, and up to 20 available local columns (FK keys, then business keys, then target-facing columns). The same endpoint returns a values page plus optional selected rows. Address the value by a server-issued type-preserving tuple token, not page position. Each call recomputes current data, with no snapshot or fingerprint. Unchanged data has deterministic pages; if data changes between calls, page positions may shift. A value that is no longer unmatched gives a named selection result with no rows. Revisit stronger cross-request paging guarantees only if needed later.
* **Read-only normalization risk:** The private `ShapeShifter` pattern avoids shared cache writes, but verify that configured loaders and transforms make no external writes in the inspection path. An inspection that cannot safely produce full frames must report `not_reproduced`, not fall back silently to a different source.
