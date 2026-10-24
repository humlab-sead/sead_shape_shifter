# Value Reference Column Pickers — Phase 3 Task Plan

## Phase Summary

**Phase:** [Phase 3: Report saved-project reference errors](VALUE_REFERENCE_COLUMN_PICKERS_PHASE_PLAN.md#phase-3-report-saved-project-reference-errors)

**Source proposal:** [Make `@value` References Usable in Column Pickers](VALUE_REFERENCE_COLUMN_PICKERS.md)

**Readiness:** Validated. [Phase 1](VALUE_REFERENCE_COLUMN_PICKERS_PHASE_1_TASK_PLAN.md) records the field set and storage forms; [Phase 2](VALUE_REFERENCE_COLUMN_PICKERS_PHASE_2_TASK_PLAN.md) is complete, and its independent `ProjectMapper.to_core(..., requested_reference_path=...)` contract is present and covered by passing tests.

**Goal:** Return a separate, located validation error for each invalid saved column-list reference while retaining the raw path or legacy expression text. Keep normal validation results when full resolution succeeds and return a project-resolution error when it fails.

**Constraints and dependencies:** Use the Phase 1 field set and the Phase 2 scoped mapper path. Check raw API/YAML data before full-project resolution. Do not change valid Core resolution, directive syntax, saved YAML, frontend controls, or the Phase 2 completion and preview contracts. A scalar `@value` operand in a supported legacy `+` expression is allowed when the full expression yields a list of strings. Fixed Entity Columns are excluded.

**Acceptance criteria**

1. [x] `PH3-AC-1` (from `P-AC-8`): Missing, unresolved, and wrong-type references in in-scope fields produce errors with their original entity, field location, and path or expression, including legacy operands and list items that would otherwise become plain strings.
2. [x] `PH3-AC-2` (from `P-AC-8`): One invalid reference does not hide others; full-project mapping failure returns collected reference errors plus a project-resolution error, and valid Core resolution is unchanged.
3. [x] `PH3-AC-3` (from `P-AC-1`): The new column-list reference check skips Fixed Entity Columns.

**Phase milestone:** `VM-3` covers both stored forms, both supported legacy expression orders, operand and result types, independent collection, mapping failure, Fixed Entity Columns exclusion, and valid-resolution parity through `V-1`–`V-5`.

## Repository Findings

**Repository basis:** Branch `value-reference-column-pickers`, commit `1ec60fce`, planning date 2026-10-24. The untracked phase plan and unrelated untracked investigation were present and left unchanged. Graphify was used for navigation; the facts below were verified in source and tests. Planning baselines passed: 74 existing validation service/project/API tests and 22 requested-reference/Core/mapper/service tests.

| Source | Verified behavior | Planning implication |
| --- | --- | --- |
| `backend/app/api/v1/endpoints/projects.py::validate_project`; `backend/app/services/validation_service.py::ValidationService.validate_project` | The authorized project route passes raw `entities` to the service. The service resolves the whole configuration before `CompositeProjectSpecification`; it currently catches only `FileNotFoundError` and returns `CONFIG_INCLUDE_NOT_FOUND`. | Scan raw fields first, aggregate reference errors with provider and specification errors, and turn any full-resolution failure into a `ValidationResult` without losing collected errors. Preserve the existing missing-include response code. |
| `backend/app/services/validation_service.py::validate_entity`, `validate_project_data`; `backend/app/api/v1/endpoints/validation.py::validate_entity` | Entity validation calls full `ProjectMapper.to_core()` before `validate_project`, losing raw text or failing before the new check. Data validation calls `validate_project` on raw model data and skips data checks when structural errors exist. | Check raw entity references before that conversion, then retain its existing mapper-backed specification path. Keep entity filtering and skipped-data status behavior. |
| `backend/app/mappers/project_mapper.py::ProjectMapper.to_core`, `to_core_dict`; `backend/app/services/column_reference_service.py::ColumnReferenceService._resolve_path` | The requested-path mapper mode resolves one dotted path and reached dependencies on a copy, skips unrelated failures, and leaves the default full-conversion branch unchanged. It cannot select a list item or FK row with a `[n]` path segment. The column-reference service requires an actual `list[str]` for a simple reference. | Reuse the mapper mode for each saved simple reference or expression operand. Put a legacy expression at a temporary scalar path, or a one-item list at that path when it was saved as a list item, to check its result without indexed lookup. |
| `src/configuration/resolve.py::resolve_requested_reference`, `ReferenceResolver._parse_list_expression` | The scoped resolver detects missing paths and cycles and parses `+` expressions with list literals in either order. The full resolver can leave a missing simple path raw or skip a missing expression operand; it flattens list-item results only when the original item starts with `@value:`. Its expression tokenization is separate from the scoped parser. | Expose the scoped parser's token split for validation without changing full resolution. Check every expression operand independently, then check scalar or list-item result shape under the existing flattening rule. |
| `backend/app/models/validation.py::ValidationError`, `ValidationResult`; `frontend/src/components/validation/ValidationMessageList.vue` | Errors already carry entity, field, message, code, and structural category; `ValidationResult` recalculates counts. The validation panel displays those values. | Reuse the existing response model and panel. Put item indexes in `field` and original text in `message`; no frontend or schema change is needed. |
| `backend/app/models/entity.py`; `src/specifications/entity.py`; Phase 1 task plan | Stored in-scope values occur at `keys`, non-fixed `columns`, FK `local_keys`/`remote_keys`, unnest `id_vars`/`value_vars`, `drop_duplicates`, and `drop_empty_rows`. `drop_duplicates` also accepts a dictionary with `columns`; FK input can be a dictionary before API normalization. | Inspect both scalar and list forms at each field, including supported nested storage, and skip `columns` only when entity `type` is `fixed`. Leave boolean row-operation values alone. |

## Scope

**In scope:** Saved-project structural validation of raw `@value:` values in the confirmed column-list fields; simple reference result-type checks; every `@value` operand and the final result of supported scalar legacy `+` expressions; located error collection; project-resolution failure reporting; entity and data-validation entry-point compatibility; focused service, route, and resolver tests.

**Out of scope:** Draft validation, frontend error annotations, completion UI, preview UI, replacement, arbitrary directives outside the confirmed column-list fields, and changes to the full Core resolver's valid output. Phase 4 and Phase 5 own editor behavior and conflict attribution.

**Affected contracts:** Existing `POST /api/v1/projects/{name}/validate`, `POST /api/v1/projects/{name}/entities/{entity_name}/validate`, and `POST /api/v1/projects/{name}/validate/data` responses remain `ValidationResult`. Reference errors use existing `ValidationError` fields; no migration or new endpoint is required.

## Work Breakdown

### Area 1: Locate raw references and share expression tokenization

**Objective:** Enumerate every saved in-scope reference with its exact entity, field path, and original text before resolution changes the data.

**Affected code:** `src/configuration/resolve.py::resolve_requested_reference`; `backend/app/services/column_list_reference_validation.py` (`NEW`); `tests/configuration/test_requested_reference.py`; `backend/tests/services/test_column_list_reference_validation.py` (`NEW`).

**Dependencies:** Phase 1 field set and Phase 2 requested-path resolver.

**Tasks**

* [x] `T1.1` **Expose:** Move the scoped resolver's existing top-level `+` token split into a pure module-level helper and use it from scoped resolution and saved-reference inspection.
  * **Target:** `src/configuration/resolve.py::resolve_requested_reference` and proposed `split_reference_expression` helper; `tests/configuration/test_requested_reference.py`.
  * **Current → required:** Expression splitting is nested inside one requested-resolution call → validation can inspect the same supported tokens without resolving or rewriting the expression.
  * **Implementation:** Return ordered tokens for balanced, supported list concatenation and an invalid result for malformed syntax. Keep the full resolver's implementation and results unchanged. Classify `@value:` tokens separately from literal-list tokens; do not mistake a literal-first expression for a simple reference.
  * **Constraints:** Preserve whitespace and original expression text for reporting. Do not make the validator depend on `ReferenceResolver._parse_list_expression`, which can skip a missing operand.
  * **Validation:** `V-1`: both token orders, multiple operands, bracket mismatch, and unsupported tokens have explicit assertions; existing scoped-resolution order and failure tests still pass.

* [x] `T1.2` **Implement:** Walk only the confirmed saved column-list fields and record raw reference occurrences.
  * **Target:** `backend/app/services/column_list_reference_validation.py` (`NEW`); `backend/tests/services/test_column_list_reference_validation.py` (`NEW`).
  * **Current → required:** Full resolution erases or changes original strings before specifications run → each scalar or list-item directive retains its entity name, field path (including FK or item index), and text for checking.
  * **Implementation:** Read `entities` without mutation. Visit `keys`, `columns` for non-fixed entities, FK local/remote keys, unnest ID/value variables, `drop_duplicates` or its supported dictionary `columns`, and `drop_empty_rows`. Accept FK list and dictionary storage. Ignore ordinary literal strings, booleans, missing fields, and Fixed Entity Columns. Treat a supported scalar or list-item `+` expression as one occurrence with its ordered reference operands and original storage form.
  * **Constraints:** A malformed surrounding entity or field must not prevent scanning other entities. Do not include other fixed-entity column values or infer references from expanded strings.
  * **Validation:** `V-2`: field-by-field scalar/list matrix, indexed FK and list locations, two legacy orders, dictionary deduplication columns, booleans, and fixed-column exclusion.

**Completion evidence:** A raw project with several references yields one located occurrence per reference-bearing field item, preserving the original text and order.

### Area 2: Check each occurrence independently

**Objective:** Produce structured errors for each bad simple path or legacy expression without letting one failure suppress later checks.

**Affected code:** `backend/app/services/column_list_reference_validation.py` (`NEW`); existing `backend/app/mappers/project_mapper.py::ProjectMapper.to_core` requested-path mode; `backend/tests/services/test_column_list_reference_validation.py` (`NEW`); `backend/tests/mappers/test_project_mapper_requested_reference.py`.

**Dependencies:** Area 1.

**Tasks**

* [x] `T2.1` **Implement:** Check simple reference paths and require `list[str]` results.
  * **Target:** `backend/app/services/column_list_reference_validation.py` (`NEW`); `backend/tests/services/test_column_list_reference_validation.py` (`NEW`).
  * **Current → required:** A missing simple path may remain raw and a list-item reference to a scalar string may look like an ordinary column after full resolution → both produce a located structural error with the original directive.
  * **Implementation:** Build a read-only `Project` snapshot from raw entities/options and the saved source path, then call `ProjectMapper.to_core(snapshot, requested_reference_path=path)` for each occurrence. Use the requested-path result to distinguish missing, circular, or dependency failure from a wrong result type. Accept an empty string list; preserve order and duplicates. Continue after every failed occurrence. Use `COLUMN_REFERENCE_MISSING_PATH`, `COLUMN_REFERENCE_CIRCULAR_REFERENCE`, `COLUMN_REFERENCE_DEPENDENCY_FAILURE`, and `COLUMN_REFERENCE_WRONG_TYPE` as applicable. Set `ValidationError` fields `entity`, indexed `field`, and a message containing the original directive.
  * **Constraints:** Do not call full conversion for individual checks, persist the snapshot, or require unrelated fields to resolve. Reuse mapper file-root and environment rules. Keep `ValidationCategory.STRUCTURAL`.
  * **Validation:** `V-2`, `V-3`: missing path, nested failure, cycle, scalar string, number, mixed list, valid empty/ordered list, multiple invalid fields, and one valid field beside an unrelated broken reference.

* [x] `T2.2` **Implement:** Check every reference operand and the final list type of each supported legacy expression.
  * **Target:** `backend/app/services/column_list_reference_validation.py` (`NEW`); `backend/tests/services/test_column_list_reference_validation.py` (`NEW`); `backend/tests/mappers/test_project_mapper_requested_reference.py`.
  * **Current → required:** Full resolution can skip a missing operand and return a shortened list → each missing or failed operand is reported, and a completed expression is accepted only when its result is a list of strings.
  * **Implementation:** Parse tokens with `T1.1` and resolve each `@value` operand independently through the mapper without requiring it to be a list. Put the original expression at a collision-free temporary key under `options` on a second read-only snapshot: as a scalar when saved as a scalar, or inside a one-item list when saved as a list item. Request that dotted path through the mapper; this also works for FK rows, which the scoped resolver cannot select by index. Require the result to be `list[str]` after the original list-item flattening rule. Report each failed operand with its path and full original expression. Use `COLUMN_REFERENCE_EXPRESSION_INVALID` for malformed syntax and `COLUMN_REFERENCE_WRONG_TYPE` for a completed non-`list[str]` result; avoid repeating an operand failure as a second identical expression error. A scalar string operand is valid when the complete ordered result is a string list.
  * **Constraints:** Do not evaluate expressions in the frontend or change legacy full-resolution behavior. Keep each expression in its original scalar or list-item storage form when checking it.
  * **Validation:** `V-2`, `V-3`: `@value`-first and literal-first order in scalar storage, list-item flattening and non-flattening, valid scalar operand, multiple missing operands, wrong-type final result, malformed expression, and unchanged valid full-mapper output.

**Completion evidence:** Every invalid raw occurrence has a located error; valid simple and legacy expressions produce no new error and resolve to their previous ordered values.

### Area 3: Add errors to saved-project validation

**Objective:** Authorized validation endpoints return collected reference errors with other applicable validation results, even if full-project resolution fails.

**Affected code:** `backend/app/services/validation_service.py::ValidationService.validate_project`, `validate_entity`, `validate_project_data`; `backend/tests/services/test_validation_service.py`; `backend/tests/api/v1/test_projects.py`; `backend/tests/api/v1/test_validation.py`.

**Dependencies:** Areas 1–2.

**Tasks**

* [x] `T3.1` **Integrate:** Run the raw reference check before full-project resolution and merge its errors into `ValidationResult`.
  * **Target:** `backend/app/services/validation_service.py::ValidationService.validate_project`; `backend/tests/services/test_validation_service.py`.
  * **Current → required:** The service resolves first, catches only missing files, and may lose raw reference text or fail before returning a result → reference errors are collected first, normal specification/provider errors are added after successful resolution, and full-resolution failure returns collected errors plus one project-resolution error.
  * **Implementation:** Check a read-only raw snapshot, then run the existing full-resolution/specification path. If resolution fails, return the reference errors, existing independent provider-binding errors, and one project-level error (`entity=None`, `field=None`); preserve `CONFIG_INCLUDE_NOT_FOUND` for missing files and use `PROJECT_RESOLUTION_FAILED` for other resolution failures. Skip checks that need a resolved project. Let `ValidationResult` calculate counts from the merged lists and `is_valid` from all errors.
  * **Constraints:** Keep valid Core resolution and existing warnings unchanged. Do not swallow failures from specification checks after resolution or change the API schema. The current full validation path resolves directly in this service; add no second direct resolver call for individual references.
  * **Validation:** `V-3`, `V-4`: two independent invalid references plus a normal structural error; missing include plus reference errors; other full-resolution failure plus reference errors; valid configuration parity and count consistency.

* [x] `T3.2` **Update:** Check raw entity references before full mapper conversion and verify all authorized validation results.
  * **Target:** `backend/app/services/validation_service.py::validate_entity`, `validate_project_data`; `backend/tests/services/test_validation_service.py`; `backend/tests/api/v1/test_projects.py`; `backend/tests/api/v1/test_validation.py`.
  * **Current → required:** Entity validation maps first, while data validation already checks raw data → both return the new located errors before any conversion can erase them, and data validation skips row checks when structural errors exist.
  * **Implementation:** In `validate_entity`, inspect `ProjectMapper.to_core_dict(project)` before its existing full `ProjectMapper.to_core(project)` call. Preserve the mapper-backed `validate_project(core_project.cfg)` specification results and merge the raw reference errors once; if full conversion fails, return those errors plus a project-resolution error. Filter merged entity errors and project-level errors as today. `validate_project_data` already passes raw model data to `validate_project`; verify it skips the orchestrator when the new errors appear. In route tests, create the saved project with `POST /api/v1/projects`, store the test references through the existing entity update API, and assert HTTP 200 with the same `ValidationResult` shape and original text. Do not add a new route.
  * **Constraints:** A failed reference check must not write the project. Keep existing valid entity and data-validation behavior.
  * **Validation:** `V-4`: project, entity, and data validation result contracts; unrelated entity errors excluded by entity filtering; failed mapping returned as JSON rather than HTTP 500; saved project unchanged.

**Completion evidence:** The project validation panel receives located errors through the existing result model. Project and entity validation return all applicable reference errors, valid entity validation keeps its mapper-backed checks, and data validation skips row checks for an invalid saved project.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
| --- | --- | --- | --- |
| `PH3-AC-1` (from `P-AC-8`) | `T1.1`, `T1.2`, `T2.1`, `T2.2`, `T3.1` | `V-1`, `V-2`, `V-3`, `V-4` | Scalar and list-item failures, legacy operands, and wrong final types have indexed fields and original path/expression text. |
| `PH3-AC-2` (from `P-AC-8`) | `T2.1`, `T2.2`, `T3.1`, `T3.2` | `V-2`, `V-3`, `V-4`, `V-5` | Independent errors are collected; mapping failure includes a project-resolution error; valid full conversion keeps ordered values. |
| `PH3-AC-3` (from `P-AC-1`) | `T1.2`, `T3.1` | `V-2`, `V-4` | Fixed Entity Columns contribute no new reference error even when they contain `@value:` text. |

## Validation And Testing

Run from the repository root. The `NEW` test file cannot be a planning-baseline pass. `V-1`–`V-4` fulfill `VM-3`.

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
| --- | --- | --- | --- | --- | --- |
| `V-1` | Shared expression tokens and existing scoped resolver in `tests/configuration/test_requested_reference.py` | `rtk uv run pytest -p no:cacheprovider tests/configuration/test_requested_reference.py -q` | `PH3-AC-1`, `VM-3` | New token cases and existing order, missing-path, cycle, file, and confinement cases pass. | Pass: 9 tests before edits; 18 tests after edits. |
| `V-2` | Raw field inventory and fixed exclusion in `backend/tests/services/test_column_list_reference_validation.py` (`NEW`) | `rtk uv run pytest -p no:cacheprovider backend/tests/services/test_column_list_reference_validation.py -q` | `PH3-AC-1`–`PH3-AC-3`, `VM-3` | Exact field locations and original text; scalar/list and legacy forms; independently reported bad paths and types; valid scalar expression operands; no fixed-column errors. | Pass: 12 new tests. |
| `V-3` | Validation aggregation in `backend/tests/services/test_validation_service.py`, with `backend/tests/mappers/test_project_mapper_requested_reference.py` for valid full-conversion parity | `rtk uv run pytest -p no:cacheprovider backend/tests/services/test_validation_service.py backend/tests/mappers/test_project_mapper_requested_reference.py -q` | `PH3-AC-1`, `PH3-AC-2`, `VM-3` | Independent reference and specification errors combine; mapping failures keep collected errors; valid mapper output and counts remain correct. | Pass: 30 tests before edits; 39 tests after edits. Review note: the existing full resolver returns a nested list for a simple list-item reference to a list-valued field, and `NonFixedIdentityColumnsSpecification` then raises `TypeError`. The full resolver was left unchanged as required; scoped list-item checks are covered by `V-2`. |
| `V-4` | Authorized validation routes in `backend/tests/api/v1/test_projects.py` and `backend/tests/api/v1/test_validation.py` | `rtk uv run pytest -p no:cacheprovider backend/tests/api/v1/test_projects.py backend/tests/api/v1/test_validation.py -q` | `PH3-AC-1`–`PH3-AC-3`, `VM-3` | With `authorized_client`, `tmp_path`, and `reset_services`, existing JSON shape and authorization stay intact; project and entity errors retain original text; full-resolution failure is HTTP 200 with errors; invalid data validation is skipped. | Pass: 47 tests before edits; 51 tests after edits. |
| `V-5` | Relevant Core/backend regressions, Python quality, and graph refresh | Run the commands below from the repository root. | `PH3-AC-2`; preservation and repository checks | No regressions or new quality failures; graph update succeeds and generated changes are reviewed. | Pass: combined regression command; Ruff, Black, and isort checks; graph refresh. The graph refresh updated `graph.json`, `GRAPH_REPORT.md`, callflow HTML, and label metadata. |

```bash
rtk uv run pytest -p no:cacheprovider tests/configuration backend/tests/services/test_validation_service.py backend/tests/services/test_column_list_reference_validation.py backend/tests/api/v1/test_projects.py backend/tests/api/v1/test_validation.py backend/tests/mappers/test_project_mapper_requested_reference.py -q
rtk uv run ruff check src/configuration/resolve.py tests/configuration/test_requested_reference.py backend/app/services/validation_service.py backend/app/services/column_list_reference_validation.py backend/tests/services/test_validation_service.py backend/tests/services/test_column_list_reference_validation.py backend/tests/api/v1/test_projects.py backend/tests/api/v1/test_validation.py backend/tests/mappers/test_project_mapper_requested_reference.py
rtk uv run black --check src/configuration/resolve.py tests/configuration/test_requested_reference.py backend/app/services/validation_service.py backend/app/services/column_list_reference_validation.py backend/tests/services/test_validation_service.py backend/tests/services/test_column_list_reference_validation.py backend/tests/api/v1/test_projects.py backend/tests/api/v1/test_validation.py backend/tests/mappers/test_project_mapper_requested_reference.py
rtk uv run isort --check-only src/configuration/resolve.py tests/configuration/test_requested_reference.py backend/app/services/validation_service.py backend/app/services/column_list_reference_validation.py backend/tests/services/test_validation_service.py backend/tests/services/test_column_list_reference_validation.py backend/tests/api/v1/test_projects.py backend/tests/api/v1/test_validation.py backend/tests/mappers/test_project_mapper_requested_reference.py
GRAPHIFY_VIZ_NODE_LIMIT=0 ~/.local/bin/graphify update .
```

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Shared expression token helper | `src/configuration/resolve.py` | `T1.1` | Both supported orders are inspectable; scoped resolution is unchanged. |
| Token and scoped-resolution cases | `tests/configuration/test_requested_reference.py` | `T1.1` | `V-1` passes. |
| Raw saved-reference checks | `backend/app/services/column_list_reference_validation.py` (`NEW`) | `T1.2`, `T2.1`, `T2.2` | Every in-scope occurrence is checked independently and reported with original text. |
| Reference-check tests | `backend/tests/services/test_column_list_reference_validation.py` (`NEW`) | `T1.2`, `T2.1`, `T2.2` | `V-2` covers storage, types, expression operands, and fixed exclusion. |
| Saved validation aggregation | `backend/app/services/validation_service.py` | `T3.1`, `T3.2` | Raw checks precede full resolution on all three validation entry points. |
| Service and HTTP regression tests | `backend/tests/services/test_validation_service.py`; `backend/tests/api/v1/test_projects.py`; `backend/tests/api/v1/test_validation.py` | `T3.1`, `T3.2` | `V-3` and `V-4` pass. |
| Mapper expression parity cases | `backend/tests/mappers/test_project_mapper_requested_reference.py` | `T2.2` | `V-3` proves both valid expression orders and default full conversion. |
| Updated generated graph, if changed by the required update | `graphify-out/graph.json` | `T3.2` | `V-5` graph update succeeds; changed generated output is reviewed. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Raw references and tokens | Done | Phases 1–2 | `T1.1` and `T1.2` complete; `V-1` and `V-2` pass. |
| Area 2: Independent checks | Done | Area 1 | `T2.1` and `T2.2` complete; `V-2` and `V-3` pass. |
| Area 3: Validation integration | Done | Areas 1–2 | `T3.1` and `T3.2` complete; `V-3`–`V-5` pass. Full-resolver list-item behavior noted in `V-3`. |

## Definition Of Done

* [x] `PH3-AC-1`–`PH3-AC-3` each have passing task and validation results for `VM-3`.
* [x] Areas 1–3 and every required deliverable are complete.
* [x] `V-1`–`V-5` pass, or a pre-existing failure is recorded with a before/after comparison.
* [x] Scalar and list-item paths, both legacy expression orders, scalar operands, wrong result types, missing/circular dependencies, and Fixed Entity Columns have regression coverage.
* [x] Project and entity validation return original text and location; mapping failure returns collected errors plus a project-resolution error; data validation skips row checks when structural errors exist.
* [x] Valid Core resolution, saved YAML, authorization, `ValidationResult` counts, and the existing missing-include error code remain unchanged; generated graph output is refreshed after code changes.
* [x] Deviations and follow-up work are documented, and no unresolved question affects implementation or validation.

If implementation finds a repository contract that conflicts with this verified plan, stop and report the source and test result before changing the design or expanding scope.

## Risks And Open Questions

The full resolver can leave a missing simple path raw and skip a missing expression operand. The new pre-resolution check must use the stricter requested-path contract for diagnosis while leaving the full resolver's valid output alone. The existing `validate_entity` conversion runs before raw validation and must be reordered; route and service tests guard against losing other entity validation results. These are implementation risks covered by `V-2`–`V-4`, not open design decisions.
