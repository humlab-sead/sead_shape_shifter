# Foreign-Key Integrity Troubleshooter — Phase 1 Task Plan

## Phase Summary

**Phase:** [Phase 1: Identify the saved foreign key](./FOREIGN_KEY_INTEGRITY_TROUBLESHOOTER_PHASE_PLAN.md#phase-1-identify-the-saved-foreign-key)  
**Source:** [Foreign-Key Integrity Troubleshooter](./FOREIGN_KEY_INTEGRITY_TROUBLESHOOTER.md)  
**Readiness:** Validated — the phase plan marks Phase 1 ready; the production issue path, saved-FK model, resolver, tests, and validation commands have been verified.

Add saved-FK identity and the distinct unmatched count to each new `FK_DATA_INTEGRITY` issue. Resolve that identity for integrity warnings without applying the row-count join-type restriction. Do not expose a new action or build an inspection endpoint yet: those belong to Phases 3 and 2, respectively.

**Acceptance criteria**

1. [x] `PH1-AC-1` (from `P-AC-1`): New integrity issues identify the exact saved link by index and signature, including two links to the same remote entity; missing or stale identity produces a named refusal.
2. [x] `PH1-AC-2` (from `P-AC-7`): Row-count eligibility and saved-link resolution remain unchanged.

**Dependencies and constraints:** No earlier phase. Preserve the existing `ForeignKeyIntegrityValidator` comparison, warning field/message, pure validator design, the saved FK's list position and `identity_signature`, and the shipped row-count request, response, and frontend behavior. `VM-1` in the phase plan is covered by `V-1` and `V-2` below.

## Repository Findings

**Repository basis:** `dev` at `8f9af77e` on 2026-11-06. The untracked source phase plan was considered; no implementation or test changes were present at planning time. Graphify was used for navigation; the findings below were checked against current source and tests.

| Evidence | Verified finding | Planning implication |
| --- | --- | --- |
| [`src/validators/data_validators.py::ForeignKeyIntegrityValidator.validate`](../../../src/validators/data_validators.py) and [`src/issues.py::CoreIssue`](../../../src/issues.py) | The validator computes `orphan_count` from distinct unmatched keys but only embeds it in prose. `CoreIssue.metadata` is a mutable per-issue dictionary. Other warning codes, including `FK_REMOTE_EMPTY`, are returned on separate paths. | Add the already-computed count to metadata only for `FK_DATA_INTEGRITY`; do not parse the message or repeat the comparison in the orchestrator. |
| [`backend/app/validators/data_validation_orchestrator.py::DataValidationOrchestrator`](../../../backend/app/validators/data_validation_orchestrator.py) | `validate_all_entities` receives the resolved core project and calls `_validate_entity`; the latter loops the resolved FK dictionaries and is the only production caller of `ForeignKeyIntegrityValidator.validate` under `src/`, `backend/app/`, and `scripts/`. It currently has neither the project nor the FK index at the validator call. | Pass the project into `_validate_entity`; enumerate the saved FK list without dropping entries, and attach identity only to integrity issues returned for each entry. Backend and CLI validation both use `validate_all_entities`. |
| [`src/model.py::TableConfig.foreign_keys`](../../../src/model.py) and [`src/model.py::ForeignKeyConfig.identity_signature`](../../../src/model.py) | The saved list assigns each FK its `fk_index`; the signature covers link settings including keys, join type, and constraints, but not the index. | Read the identity from `core_project.get_table(entity_name).foreign_keys[index]`. An index remains necessary even for identical links or links to the same remote entity. |
| [`backend/app/services/validation_service.py::ValidationService`](../../../backend/app/services/validation_service.py) and [`backend/app/mappers/validation_mapper.py::ValidationMapper.from_core_issue`](../../../backend/app/mappers/validation_mapper.py) | The service delegates to the orchestrator and maps resulting domain issues; the mapper passes metadata into the API error unchanged. | Test metadata at the domain and mapper edges; no API DTO, endpoint, or browser transport change is needed in this phase. |
| [`src/transforms/link_resolution.py::resolve_row_count_issue`](../../../src/transforms/link_resolution.py), [`backend/app/services/link_baseline_service.py::LinkBaselineService.build_baseline`](../../../backend/app/services/link_baseline_service.py), and [`frontend/src/utils/linkTroubleshooter.ts::isLinkTroubleshootCandidate`](../../../frontend/src/utils/linkTroubleshooter.ts) | The backend baseline consumes the existing row-count resolver. Its issue-type and join-type checks, and the frontend's `ROW_COUNT_MISMATCH` candidate check, exclude integrity warnings. | Share only saved-link lookup; keep row-count gates and result behavior intact. Defer the integrity UI action and backend inspection to later phases. |
| [`tests/transforms/test_link_resolution.py`](../../../tests/transforms/test_link_resolution.py), [`tests/validators/test_data_validators.py`](../../../tests/validators/test_data_validators.py), [`backend/tests/validators/test_data_validation_orchestrator.py`](../../../backend/tests/validators/test_data_validation_orchestrator.py), and [`backend/tests/mappers/test_validation_mapper.py`](../../../backend/tests/mappers/test_validation_mapper.py) | Existing tests already cover row-count identity/refusal, validator edge cases, injected in-memory fetches, and metadata passthrough. | Extend these suites rather than creating duplicate test files. |

## Scope

**In scope:** Domain issue metadata; backend orchestration of FK validation; Core saved-FK resolution; focused tests for the validator, orchestrator, mapper, and resolver; row-count and frontend candidate regression checks.

**Out of scope:** Fetch strategy changes, recomputation or row inspection, an integrity endpoint or response model, frontend changes, other warning kinds, edits to the warning's existing `field`, and changes to row-count trials. No configuration migration or new file is needed.

## Work Breakdown

### Area 1: Record the warning's count and saved-link identity

**Objective:** A validation run returns integrity issues with `orphan_count`, `fk_index`, and `fk_signature`, including when multiple saved links reference the same entity.

**Affected code:** [`src/validators/data_validators.py::ForeignKeyIntegrityValidator.validate`](../../../src/validators/data_validators.py); [`backend/app/validators/data_validation_orchestrator.py::DataValidationOrchestrator`](../../../backend/app/validators/data_validation_orchestrator.py); existing tests named below. No new files.

**Dependencies:** None.

**Tasks:**

* [x] `T1.1` **Change:** Record the distinct unmatched count in the integrity issue.
  * **Target:** `src/validators/data_validators.py::ForeignKeyIntegrityValidator.validate`.
  * **Current → required:** `orphan_count` appears only in the message → return the same warning with `metadata["orphan_count"]` set from the existing integer count.
  * **Implementation:** Add metadata at the `FK_DATA_INTEGRITY` return path for both null-handling branches. Leave the validator's signature, comparison, message, other issue codes, and pure DataFrame/config input contract unchanged.
  * **Constraints:** Do not attach large value sets or count local rows instead of distinct key combinations.
  * **Validation:** `V-1` in `tests/validators/test_data_validators.py`: duplicate local values yield one distinct orphan; composite keys and `null_keys_equal` yield the validator's count; a matched link yields no issue, and `FK_REMOTE_EMPTY` does not gain integrity metadata. Existing warning field/message remain unchanged.

* [x] `T1.2` **Change:** Attach identity from the saved list to each integrity issue.
  * **Target:** `backend/app/validators/data_validation_orchestrator.py::DataValidationOrchestrator.validate_all_entities` and `_validate_entity`.
  * **Current → required:** The orchestrator calls the validator for each FK without passing its saved index → make the resolved core project available to `_validate_entity`, enumerate its FK dictionaries without reindexing after skipped entries, and attach the matching `ForeignKeyConfig.fk_index` and `identity_signature` to each `FK_DATA_INTEGRITY` result.
  * **Implementation:** Obtain the corresponding `core_project.get_table(entity_name).foreign_keys` entry at the original list position; enrich the validator's issue metadata while retaining its `orphan_count`. Continue to fetch frames through the injected strategy and return ordinary domain issues.
  * **Constraints:** Do not modify the project/FK dictionaries, attach identity to unrelated warnings, or change which FK entries are checked. Preserve behavior for links without a `constraints` block.
  * **Validation:** `V-1` in `backend/tests/validators/test_data_validation_orchestrator.py`: an in-memory project with two links to the same remote entity produces warnings with indices `0` and `1`, signatures equal to the corresponding saved FKs, and correct counts; include a link without constraints and a preceding entry that produces no integrity issue so its successor retains its saved index.

* [x] `T1.3` **Change:** Assert the end-to-end metadata path.
  * **Target:** `tests/validators/test_data_validators.py::TestForeignKeyIntegrityValidator`, `backend/tests/validators/test_data_validation_orchestrator.py`, and `backend/tests/mappers/test_validation_mapper.py`.
  * **Current → required:** Tests assert codes and prose or generic metadata passthrough → assert the exact integer count and saved-link identity through domain validation and `ValidationMapper.to_api_error`.
  * **Implementation:** Use inline DataFrames, `ShapeShiftProject(cfg=...)`, and `TableStoreDataFetchStrategy` as existing tests do; keep direct validator tests independent of backend/project loading.
  * **Constraints:** Older issues without identity must not be retroactively made eligible; do not change transport schemas to pass existing metadata.
  * **Validation:** `V-1`: exact metadata dictionary values at the orchestrator and API mapping edges; no identity on unrelated issue codes.

**Completion evidence:** New integrity issues identify the saved FK and carry a numeric distinct orphan count across domain and API mapping; unaffected issues retain their previous fields and behavior.

### Area 2: Resolve integrity warnings without changing row-count resolution

**Objective:** A Core resolver identifies one saved FK for an integrity warning or returns a named refusal; row-count resolution keeps its current gates.

**Affected code:** [`src/transforms/link_resolution.py::resolve_row_count_issue`](../../../src/transforms/link_resolution.py), existing [`tests/transforms/test_link_resolution.py`](../../../tests/transforms/test_link_resolution.py), and regression-only consumers. No new files.

**Dependencies:** Area 1's identity contract for production warnings; resolver unit tests can use saved-FK metadata directly.

**Tasks:**

* [x] `T2.1` **Change:** Share saved-FK lookup and add integrity-specific resolution.
  * **Target:** `src/transforms/link_resolution.py::resolve_row_count_issue`, `LinkIssueResolution`, and a `resolve_integrity_issue` function in the same file.
  * **Current → required:** Only row-count warnings can reach the saved-FK lookup and all resolved links must use `inner` or `left` joins → reuse a single entity/index/signature lookup for both warning kinds; gate each resolver by its own issue kind and keep the join-type restriction only for row counts.
  * **Implementation:** Preserve existing `entity_not_found`, `missing_metadata`, `index_out_of_range`, and `signature_mismatch` results, including rejection of a boolean index; return a named wrong-kind refusal for non-`FK_DATA_INTEGRITY` issues. Keep `link_pass` handling and `SUPPORTED_JOIN_TYPES` behavior in the row-count path. Return `LinkIssueResolution` with `is_eligible` true only for a resolved saved FK.
  * **Constraints:** No data fetching, backend imports, join execution, or change to the existing resolver signature, statuses, and output for existing inputs. Integrity eligibility uses index and signature, not `orphan_count` or join type; Phase 2 checks count reproduction.
  * **Validation:** `V-1` in `tests/transforms/test_link_resolution.py`: correct first/second and identical saved entries; missing or mistyped index/signature, unknown entity, out-of-range index, edited signature, shifted index, wrong issue kind, and eligible right/outer joins; existing row-count tests still reject right/outer joins.

* [x] `T2.2` **Change:** Add refusal and preservation regression assertions.
  * **Target:** `tests/transforms/test_link_resolution.py`; run existing `backend/tests/services/test_link_baseline_service.py::test_unsupported_join_is_ineligible` and `frontend/src/utils/__tests__/linkTroubleshooter.test.ts` unchanged.
  * **Current → required:** Tests cover row-count but not integrity saved-FK resolution → verify named integrity refusal results and exact row-count outcomes before downstream callers use the shared lookup.
  * **Implementation:** Reuse `build_project`, `saved_fk`, and the existing row-count fixtures; create integrity-warning metadata with the saved index/signature, including an old warning with neither field.
  * **Constraints:** Do not alter frontend candidate logic or the row-count baseline service in this phase.
  * **Validation:** `V-1` for Core resolution and baseline-service checks; `V-2` for unchanged row-count candidate/request behavior in the frontend.

**Completion evidence:** The integrity resolver can be consumed by Phase 2 without accepting stale links or restricting right/outer joins, and the shipped row-count resolver, baseline, and frontend candidate checks pass unchanged.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
| --- | --- | --- | --- |
| `PH1-AC-1` (from `P-AC-1`) | `T1.1`, `T1.2`, `T1.3`, `T2.1`, `T2.2` | `V-1`, `V-3` | Every newly produced integrity issue carries its saved index/signature and distinct orphan count; resolver selects the intended entry or gives a named refusal, including duplicate-entity and right/outer cases. |
| `PH1-AC-2` (from `P-AC-7`) | `T2.1`, `T2.2` | `V-1`, `V-2`, `V-3` | Existing row-count resolver/baseline and frontend candidate/request tests remain green; no row-count interface or join policy changes. |

## Validation And Testing

Run the combined Python command after the implementation; it covers the new assertions and existing regression cases without starting a full suite. Existing inputs and fixtures are in the test files listed above; `T1.1`–`T2.2` specify the required new scenarios and assertions.

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
| --- | --- | --- | --- | --- | --- |
| `V-1` | Domain count, orchestration, mapper, saved-FK resolution, row-count baseline | `rtk uv run pytest -o addopts='' -p no:xdist -q tests/validators/test_data_validators.py backend/tests/validators/test_data_validation_orchestrator.py tests/transforms/test_link_resolution.py backend/tests/mappers/test_validation_mapper.py backend/tests/services/test_link_baseline_service.py::test_unsupported_join_is_ineligible` | `PH1-AC-1`, `PH1-AC-2`, `VM-1` | New and existing tests pass, including negative and duplicate-link cases. | Pass (2026-11-06): 109 tests, 21 new; baseline was 88 existing tests. |
| `V-2` | Shipped row-count candidate and request | `rtk npm --prefix frontend run test:run -- src/utils/__tests__/linkTroubleshooter.test.ts` | `PH1-AC-2`, `VM-1` | Only existing supported row-count warnings remain candidates; request construction remains unchanged. | Pass (2026-11-06): 7 tests. |
| `V-3` | Python types, formatting, imports for the seven affected files | `rtk uv run pyright --threads 2 src/transforms/link_resolution.py src/validators/data_validators.py backend/app/validators/data_validation_orchestrator.py`<br>`rtk uv run black --check src/validators/data_validators.py backend/app/validators/data_validation_orchestrator.py src/transforms/link_resolution.py tests/validators/test_data_validators.py backend/tests/validators/test_data_validation_orchestrator.py tests/transforms/test_link_resolution.py backend/tests/mappers/test_validation_mapper.py`<br>`rtk uv run isort --check-only src/validators/data_validators.py backend/app/validators/data_validation_orchestrator.py src/transforms/link_resolution.py tests/validators/test_data_validators.py backend/tests/validators/test_data_validation_orchestrator.py tests/transforms/test_link_resolution.py backend/tests/mappers/test_validation_mapper.py` | `PH1-AC-1`, `PH1-AC-2` | Zero type errors and no formatting/import changes required. | Pass (2026-11-06): pyright 0 errors; Black 7 unchanged; isort passed. |

The repository's pytest configuration adds `-n` by default; `-o addopts='' -p no:xdist` makes the tested Python command run serially. After implementation changes code, refresh the repository graph as directed by `AGENTS.md`; do not treat graph output as a substitute for tests.

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Integrity count metadata | `src/validators/data_validators.py::ForeignKeyIntegrityValidator.validate` | `T1.1` | `orphan_count` equals distinct unmatched key count. |
| Saved-link issue identity | `backend/app/validators/data_validation_orchestrator.py::DataValidationOrchestrator` | `T1.2` | Two warnings sharing a remote entity identify their own saved entries. |
| Shared lookup and integrity resolver | `src/transforms/link_resolution.py::resolve_row_count_issue`, `resolve_integrity_issue` | `T2.1` | Named integrity refusals and unchanged row-count results. |
| Validator cases | `tests/validators/test_data_validators.py::TestForeignKeyIntegrityValidator` | `T1.3` | Count, composite/null, and unrelated-warning cases pass. |
| Orchestrator cases | `backend/tests/validators/test_data_validation_orchestrator.py` | `T1.3` | Saved index/signature and skipped-entry order cases pass. |
| Mapper metadata case | `backend/tests/mappers/test_validation_mapper.py` | `T1.3` | Domain identity/count reach the API error unchanged. |
| Resolver cases | `tests/transforms/test_link_resolution.py` | `T2.2` | Integrity and row-count resolution cases pass. |

No files are planned as `NEW`. The source proposal and phase plan remain unchanged.

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Record metadata | Done | None | `T1.1`–`T1.3` complete; `V-1` and `V-3` pass. |
| Area 2: Resolve saved FK | Done | Area 1 identity contract | `T2.1`–`T2.2` complete; `V-1`, `V-2`, and `V-3` pass. |

## Definition Of Done

- [x] `PH1-AC-1` and `PH1-AC-2` have passing implementation and validation results (`V-1`–`V-3`).
- [x] All tasks, work areas, and listed deliverables are complete and the progress tracker is updated.
- [x] Validator purity, saved-list positions, distinct counts, mapper passthrough, and named refusals are verified.
- [x] Existing row-count resolver, baseline, frontend candidate/request, and API contract remain unchanged.
- [x] Required Python test, frontend regression, type, formatting, and import checks pass; graph output is refreshed after code changes.
- [x] Any deviation or follow-up is documented; no unresolved question affects this phase's implementation or validation. If repository behavior conflicts with a verified finding above, stop and report the evidence instead of redesigning or widening the phase.
