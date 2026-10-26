# Conditional Target Model Requirements — Phase 2 Task Plan

## Phase Summary

**Goal:** Enforce `foreign_keys[].required_when.has_new_rows` using the final change-request row decisions made after reconciliation.

**Readiness:** Validated. The [source proposal](CONDITIONAL_TARGET_MODEL_REQUIREMENTS.md) and [Phase 2](CONDITIONAL_TARGET_MODEL_REQUIREMENTS_PHASE_PLAN.md#phase-2-reconciled-change-request-enforcement) fix the contract and mark this phase Ready. Phase 1's parsed contract and project-only informational result are committed. Repository targets and validation commands below were verified.

**Dependencies:** Phase 1 implementation in commit `e15f73a9`; the conditional FK target must have a `public_id`. Keep active superset-model rules unchanged.

**Validation milestone:** `VM-2`.

**Acceptance checklist**

1. [x] `PH2-AC-1` (from `P-AC-3`): When no source rows are selected for insertion after reconciliation, the condition adds no error, including when provisional rows match existing target rows.
2. [x] `PH2-AC-2` (from `P-AC-4`): An insert fails validation with a clear error when the lookup or project link is missing, the FK column is missing, or an inserted row has a null or unresolved FK value.
3. [x] `PH2-AC-3` (from `P-AC-6`): Existing unconditional entity, column, and FK validation results remain unchanged.
4. [x] `PH2-AC-4` (from `P-AC-5`, guidance portion): The target-model guide explains the reconciliation timing and the conditional FK column requirement.

## Repository Findings

**Repository basis:** Branch `conditional-target-model-requirements`, commit `e15f73a9`, planned 2026-10-14. Uncommitted changes were considered: `resources/target_models/sead_superset_model.yml`, `entities.csv`, `entities.xlsx`, and `resources/target_models/TARGET_MODEL_REVIEW_20261013.md` are existing user changes and are outside this phase.

| Verified source | Finding | Planning implication |
| --- | --- | --- |
| `ingesters/sead_change_request/contracts.py::ChangeRowState`; `ingesters/sead_change_request/package_builder.py::INSERTABLE_ROW_STATES` and `build_change_request_package` | The package inserts rows in `NEWLY_ALLOCATED_ENTITY` or `DERIVED_BRIDGE_ROW` state. `RECONCILED_CLASSIFIER` and `EXISTING_ENTITY` rows are not inserts. The package builder also includes `UPDATE_EXISTING_CANDIDATE` rows based on `PlannedTable.planned_actions`. | Use the same insert-state definition as package creation. Do not activate conditional requiredness from provisional planning actions or from the presence of source rows alone. Treat accepted updates separately from inserts. |
| `ingesters/sead_change_request/preparation.py::prepare_change_request`; `ingesters/sead_change_request/identity_resolution.py::resolve_planned_tables` | Preparation runs identity orchestration and final row-state resolution before `project_target_ids`. Resolution changes matched reconciliation results to `RECONCILED_CLASSIFIER` and unresolved work to `BLOCKED_UNRESOLVED`. | Evaluate `has_new_rows` after identity resolution, using final row states. A blocked row must not trigger the condition, though its existing identity-resolution error remains. |
| `ingesters/sead_change_request/target_projection.py::project_target_ids` | Projection checks static required columns and FKs across resolved frames. It maps FK `system_id` values to target IDs when values are present; a missing lookup table is diagnosed only when a non-null FK needs mapping. Conditional FKs are not currently evaluated here. | On inserts, add conditional lookup, target-facing FK-column, non-null, and resolvable-value checks. Keep existing static checks and FK mapping behavior. Do not require an unused lookup for a zero-insert result. |
| `ingesters/sead_change_request/preparation.py::ResolvedInputs`; `ingesters/sead_change_request/result_builders.py::build_validation_result` and `check_ingestion_preconditions`; `ingesters/sead_change_request/ingester.py::validate` and `ingest` | The change-request ingester receives a `SourceTableBundle` and `TargetModel`, not a `ShapeShiftProject`. Projection diagnostics become validation errors, and ingestion checks them before building a package or writing artifacts. | Inference from the input contract: the ingester cannot inspect the project FK declaration directly, so a missing project link is observed as an absent target-facing FK column in the normalized source table. Return conditional failures through projection diagnostics so both validation and ingestion reject them before package acceptance. |
| `ingesters/sead_change_request/target_projection.py::project_target_ids`; `ingesters/sead_change_request/package_builder.py::_build_update_mask` | Projection currently sees all resolved rows. `EXISTING_ENTITY` alone does not distinguish a reference-only row from an update candidate; `PlannedTable.planned_actions` carries that distinction. | If conditional FK mapping or its unresolved-value diagnostics are limited to packaged rows, pass or reuse planned actions so update candidates retain their projected FK values. Conditional requiredness itself still applies only to insert rows. |
| `docs/TARGET_MODEL_GUIDE.md::Foreign Key Specs` | The guide documents only static `required` and `via` fields. It does not describe `required_when`, reconciliation timing, or the FK-column requirement. `docs/AGENTS.md` names this as the target-model usage guide; no guide-generation or guide-sync check exists. | Update the existing FK section and validate it by review against the tested behavior. Do not change the generated schema reference or editor schema in Phase 2. |
| `backend/tests/ingesters/test_sead_change_request_target_projection.py`; `backend/tests/ingesters/test_sead_change_request_package_builder.py`; `backend/tests/ingesters/test_sead_change_request_ingester.py` | The existing tests cover FK projection, package row selection and updates, validation, ingestion failures, and static required-FK behavior. Baseline runs passed 5 projection tests, 3 package-builder tests, and 51 ingester tests. | Extend these files with insert-state, matched-only, update-projection, pre-package rejection, and static-parity cases; no new test file is needed. |

Graphify's scoped query returned broad documentation nodes, and `graphify path "TargetProjection" "PackageBuilder"` did not find a `PackageBuilder` node. Current source and tests establish the flow above; Graphify did not supply a conflicting finding.

## Scope

**In scope:** Evaluate the conditional FK after reconciliation; require its lookup and target-facing column and validate non-null, resolvable FK values on rows selected for insertion; preserve projection for insert and accepted update rows; return failures before package creation; document the rule in the target-model guide; add focused tests and refresh the code graph.

**Out of scope:** Changes to the Phase 1 YAML contract or project-only informational result; changes to unconditional `required` semantics; activation in `resources/target_models/sead_superset_model.yml`; a general condition language; unrelated target-model, reconciliation, or package behavior; changes to the generated schema reference or editor schema.

The condition is active only when final row states include an insertable row. The missing project-link case is observed as a missing target-facing FK column because the ingester receives normalized tables, not project configuration. The guide must tell users to omit unconditional `required: true` on the lookup and FK column when they intend this conditional behavior.

**Implementation handoff:** If current source, tests, or row-state semantics differ from these findings, stop and report the exact evidence before changing scope. Do not invent replacement behavior.

## Work Breakdown

### Area 1: Enforce the FK requirement from final row decisions

**Objective:** Reject incomplete inserted rows while accepting matched-only submissions and preserving FK values needed by updates.

**Affected code:** `ingesters/sead_change_request/target_projection.py::project_target_ids`; `ingesters/sead_change_request/preparation.py::prepare_change_request`; `ingesters/sead_change_request/contracts.py::ChangeRowState`; `ingesters/sead_change_request/package_builder.py::INSERTABLE_ROW_STATES` and `build_change_request_package`; `ingesters/sead_change_request/result_builders.py::build_validation_result` and `check_ingestion_preconditions`; the existing change-request projection, package-builder, and ingester test files.

**Dependencies:** Phase 1's parsed `required_when` contract; final resolved row states.

- [x] `T2.1` **Gate conditional requirements on inserted rows.**
  - **Target:** `ingesters/sead_change_request/target_projection.py::project_target_ids`; `ingesters/sead_change_request/preparation.py::prepare_change_request`; `backend/tests/ingesters/test_sead_change_request_target_projection.py`.
  - **Current → required:** Projection enforces only static `required` fields and processes all resolved rows → enforce a conditional FK only when its owning source has at least one final insertable row, using the same insert-state definition as `package_builder.INSERTABLE_ROW_STATES`.
  - **Implementation:** For insert rows, report clear diagnostics when the lookup table is absent, the target-facing FK column is absent, a value is null, or a value cannot map to a target ID. Count conditional missing or unresolved values from insert rows only. Do not report conditional FK mapping errors for matched rows that are not selected for the package. A missing project link is represented by the missing target-facing FK column in the bundle. Keep static required-column and FK checks unchanged.
  - **Constraints:** `NEWLY_ALLOCATED_ENTITY` and `DERIVED_BRIDGE_ROW` are insertable; `RECONCILED_CLASSIFIER`, `EXISTING_ENTITY`, and `BLOCKED_UNRESOLVED` are not. A blocked row retains its existing resolution error but does not activate this condition. Do not count provisional rows before reconciliation.
  - **Validation:** `V-1`; cover zero insert rows with absent, null, or unresolved conditional FK values; matched rows; mixed matched/insert rows; missing lookup; missing FK column; null FK values; and unresolved insert-row FK values.
- [x] `T2.2` **Preserve FK projection for packaged updates and reject failures before packaging.**
  - **Target:** `ingesters/sead_change_request/preparation.py::prepare_change_request`; `ingesters/sead_change_request/target_projection.py::project_target_ids`; `ingesters/sead_change_request/package_builder.py::build_change_request_package`; `backend/tests/ingesters/test_sead_change_request_package_builder.py`; `backend/tests/ingesters/test_sead_change_request_ingester.py`.
  - **Current → required:** Projection currently maps present FK values before package selection, and package selection later includes update candidates → map FK values used by inserted and accepted update rows, without making a matched-only non-package row fail the conditional check; conditional diagnostics must reach validation and stop ingestion before package or artifact creation.
  - **Implementation:** Project conditional FK values for insert rows and `UPDATE_EXISTING_CANDIDATE` rows. Use `PlannedTable.planned_actions` as well as resolved row states because update candidates have state `EXISTING_ENTITY`. Keep conditional requiredness limited to insert rows; still report an unresolved FK value used by an update row. Preserve the existing projection-diagnostic error path through `build_validation_result` and `check_ingestion_preconditions`.
  - **Constraints:** Do not turn a condition-only missing lookup, column, or value into a Phase 1 project-conformance error. Keep independent static errors and update package selection unchanged.
  - **Validation:** `V-2`, `V-3`; confirm an update's FK value is projected into its package row, an unresolved FK value used by an update remains an error, invalid insert conditions make validation invalid, `ingest(validate_first=False)` fails before creating artifacts, and existing static required entity, column, and FK results retain their values.

**Completion evidence:** A matched-only request produces no conditional error; an incomplete insert returns a clear validation error before package creation; an accepted update retains its projected FK value; static required-FK diagnostics match baseline.

### Area 2: Explain the conditional FK in the target-model guide

**Objective:** Show how to declare the rule and when it requires an FK value.

**Affected code:** `docs/TARGET_MODEL_GUIDE.md`, `Foreign Key Specs` section.

**Dependencies:** Area 1's verified behavior.

- [x] `T2.3` **Document reconciliation timing and the inserted-row FK requirement.**
  - **Target:** `docs/TARGET_MODEL_GUIDE.md`, `Foreign Key Specs`.
  - **Current → required:** The guide explains static `required` and bridge FKs only → document `required_when: {has_new_rows: <owning entity>}` on a direct FK and explain its result after reconciliation.
  - **Implementation:** Add a `location` to `location_type` example. State that only rows finally selected for insertion activate the condition; matched rows and zero-insert submissions do not. Explain that the target's `public_id` names the source FK column and that inserted rows need a non-null, resolvable value. Explain that the lookup and link must be available when inserts exist, and omit unconditional `required: true` on the lookup and FK column for this conditional rule. Keep the guide consistent with the Phase 1 rule that a conditional FK cannot also declare `required` or use `via`.
  - **Constraints:** Keep the example conceptual and do not activate it in the SEAD superset YAML.
  - **Validation:** `V-5`; review the example and wording against the insert, matched-only, and update cases from `V-1` and `V-2` and confirm the example uses the Phase 1 accepted syntax.

**Completion evidence:** The FK guide describes the same trigger and missing-value outcomes asserted by the tests, without implying that a project-only check can decide insert status.

## Acceptance-Criteria Coverage

| Criterion | Tasks | Checks | Expected evidence |
| --- | --- | --- | --- |
| `PH2-AC-1` ← `P-AC-3` | `T2.1`, `T2.2` | `V-1`, `V-2` | Zero final insert rows, including rows reconciled to existing records, add no conditional requirement error. |
| `PH2-AC-2` ← `P-AC-4` | `T2.1`, `T2.2` | `V-1`, `V-2` | An insert with a missing lookup/link/column or null/unresolved FK value is rejected before package creation. |
| `PH2-AC-3` ← `P-AC-6` | `T2.1`, `T2.2` | `V-2`, `V-3` | Existing static required-entity, column, and FK results remain unchanged. |
| `PH2-AC-4` ← `P-AC-5` (guidance portion) | `T2.3` | `V-5` | The guide states the final-insert trigger and the FK-column/value requirement. |

## Validation And Testing

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
| --- | --- | --- | --- | --- | --- |
| `V-1` | Conditional target projection | `rtk .venv/bin/pytest -q backend/tests/ingesters/test_sead_change_request_target_projection.py` | `PH2-AC-1`, `PH2-AC-2` | Zero-insert matched rows add no conditional requirement or mapping error, even when the conditional FK is absent, null, or unresolved; only inserted rows trigger missing lookup, missing column, null-value, or unresolved-value diagnostics. Mixed rows check inserted rows only. | Pass. Baseline: 5 existing projection tests. After the change the file passed 17 tests (5 pre-existing plus 12 conditional cases). |
| `V-2` | Package selection, ingester validation, and static parity | `rtk .venv/bin/pytest -q backend/tests/ingesters/test_sead_change_request_package_builder.py backend/tests/ingesters/test_sead_change_request_ingester.py` | `PH2-AC-1`–`PH2-AC-3` | Matched-only validation succeeds; incomplete inserts fail validation and ingestion before artifact output; package update candidates retain projected FK values, and unresolved FK values used by updates remain errors; the existing static required-FK failure remains unchanged. Cover `TestBuildChangeRequestPackage.test_includes_update_candidates_when_planned_tables_are_provided` and `TestSeadChangeRequestIngesterIngest.test_ingest_blocks_sample_without_required_fields_or_references`, plus the new conditional cases. | Pass. Baseline: package-builder and ingester files passed separately (3 and 51 tests). After the change the two files passed 58 tests (4 package-builder plus 54 ingester), and the new `test_update_candidate_keeps_projected_conditional_foreign_key_value`, `test_validate_accepts_matched_only_rows_for_conditional_foreign_key`, `test_validate_rejects_inserted_row_without_conditional_foreign_key_value`, and `test_ingest_blocks_inserted_row_without_conditional_foreign_key_value` passed with the pre-existing static cases. |
| `V-3` | Core static conformance regression | `rtk .venv/bin/pytest -q tests/model/test_target_model_conformance.py -k 'test_core_conformance_reports_missing_entity_and_wrong_public_id or test_conditional_foreign_key_does_not_change_static_requirements'` | `PH2-AC-3` | Required entity, column, and FK results match the existing core behavior; the Phase 1 condition does not alter static checks. | Pass. Baseline: 2 focused tests. After the change both focused tests passed. A wider run of `backend/tests/ingesters tests/model` reported only two pre-existing failures, `test_core_conformance_reports_known_gaps_for_full_arbodat_project` and `test_core_conformance_current_corpus_issue_families_are_stable`, which reproduce unchanged in a clean `HEAD` (`e15f73a9`) worktree and are unrelated to this phase. |
| `V-4` | Python formatting and imports | `rtk .venv/bin/black --check ingesters/sead_change_request/target_projection.py ingesters/sead_change_request/preparation.py ingesters/sead_change_request/result_builders.py ingesters/sead_change_request/package_builder.py backend/tests/ingesters/test_sead_change_request_target_projection.py backend/tests/ingesters/test_sead_change_request_package_builder.py backend/tests/ingesters/test_sead_change_request_ingester.py`; `rtk .venv/bin/isort --check-only ingesters/sead_change_request/target_projection.py ingesters/sead_change_request/preparation.py ingesters/sead_change_request/result_builders.py ingesters/sead_change_request/package_builder.py backend/tests/ingesters/test_sead_change_request_target_projection.py backend/tests/ingesters/test_sead_change_request_package_builder.py backend/tests/ingesters/test_sead_change_request_ingester.py`. | All Python changes | Formatting and imports pass. | Pass after formatting. Baseline: Black and isort checks passed on these 7 files. The change added two test files needing Black reformatting; both were reformatted, and the repeat Black and isort checks then reported no changes with all tests still passing. |
| `V-5` | Target-model guide | Manually review `docs/TARGET_MODEL_GUIDE.md` under `Foreign Key Specs` against the Phase 2 example and the behaviors covered by `V-1` and `V-2`. | `PH2-AC-4` | The example parses under the Phase 1 contract and explains the same timing, link, and FK value rules as the tests. | Pass. Baseline: Not run, the guide did not document this condition. The conditional example, including `location_type.public_id`, parses into `TargetModel` with no spec-validation issues, and the guide states the inserted-row trigger, the lookup and link requirement, the `public_id`-derived column, the non-null/resolvable value rule, and the `required` and `via` exclusions. |
| `V-6` | Working diff | `rtk git diff --check -- ingesters/sead_change_request/target_projection.py ingesters/sead_change_request/preparation.py ingesters/sead_change_request/result_builders.py ingesters/sead_change_request/package_builder.py backend/tests/ingesters/test_sead_change_request_target_projection.py backend/tests/ingesters/test_sead_change_request_package_builder.py backend/tests/ingesters/test_sead_change_request_ingester.py docs/TARGET_MODEL_GUIDE.md` | All Phase 2 changed files | No whitespace errors. | Pass: `git diff --check` reported no whitespace errors for the eight Phase 2 files. |
| `V-7` | Code graph | `rtk .venv/bin/graphify update .` | Updated implementation graph | Graphify completes and refreshes its tracked graph outputs after code changes. | Pass: Graphify rebuilt 20773 nodes and 47967 edges and updated `graphify-out/graph.json`, `GRAPH_REPORT.md`, `sead_shape_shifter-callflow.html`, and `.graphify_labels.json`. |

`VM-2` is complete when `V-1`, `V-2`, `V-3`, and `V-5` show the matched-only, insert, update, static-rule, and guide results specified above.

The test baseline used three read-only runs: `backend/tests/ingesters/test_sead_change_request_target_projection.py` (5 passed), `backend/tests/ingesters/test_sead_change_request_package_builder.py` (3 passed), and `backend/tests/ingesters/test_sead_change_request_ingester.py` (51 passed). No baseline failures were observed in these targets. After the change these three files passed 75 tests in total.

**Pre-existing failures outside this phase:** `tests/model/test_target_model_conformance.py::test_core_conformance_reports_known_gaps_for_full_arbodat_project` and `::test_core_conformance_current_corpus_issue_families_are_stable` fail on unchanged conformance output. A clean `HEAD` (`e15f73a9`) worktree reproduces both failures, so they are baseline failures untouched by this phase. A wider `backend/tests` run also reports 12 failures in API, authorization, data-provider, and service tests. The service failures reproduce at `HEAD`; the one extra failure, `test_load_reconciliation_config_creates_empty_if_missing`, comes from the local `.env` value `SHAPE_SHIFTER_RECONCILIATION_SERVICE_URL="http://host.docker.internal:8000"`, which a clean worktree without `.env` does not have. `backend/tests/ingesters` passes in full.

## Deliverables

| Deliverable | Producing tasks | Completion evidence |
| --- | --- | --- |
| `ingesters/sead_change_request/target_projection.py::project_target_ids` | `T2.1`, `T2.2` | Conditional diagnostics use final insert rows; FK values needed by package inserts and updates are projected. |
| `ingesters/sead_change_request/preparation.py::prepare_change_request` | `T2.1`, `T2.2` | Projection receives any planned-row information it needs to preserve update candidates while using resolved insert states. |
| `backend/tests/ingesters/test_sead_change_request_target_projection.py` | `T2.1` | Insert, matched, mixed, missing-lookup, missing-column, null, and unresolved cases pass. |
| `backend/tests/ingesters/test_sead_change_request_package_builder.py`; `backend/tests/ingesters/test_sead_change_request_ingester.py` | `T2.2` | Package updates preserve projected FKs; validation and ingestion reject incomplete inserts before package/artifact output; static behavior remains stable. |
| `docs/TARGET_MODEL_GUIDE.md` | `T2.3` | Conditional FK timing and column/value behavior match tested results. |
| `graphify-out/.graphify_labels.json`; `graphify-out/GRAPH_REPORT.md`; `graphify-out/graph.json`; `graphify-out/sead_shape_shifter-callflow.html` | `T2.1`, `T2.2` | `graphify update .` completes after implementation changes. |

No new implementation or test file is required by this plan.

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1 — Reconciled insert enforcement and package behavior | Done | Phase 1 parsed contract | Conditional diagnostics use final insert states; package update FK projection preserved. |
| Area 2 — Target-model guide | Done | Area 1 behavior | Guide documents the accepted direct-FK condition. |

## Definition Of Done

- [x] `PH2-AC-1`–`PH2-AC-4` and `VM-2` have test or guide-review evidence recorded.
- [x] Both work areas and every deliverable are complete.
- [x] Conditional lookup, link/column, null, and unresolved-value errors occur only when final insert rows activate the condition.
- [x] Matched-only submissions do not receive conditional requirement errors, including when provisional rows reconcile to existing records.
- [x] FK values used by inserted and accepted update rows remain projected.
- [x] Existing unconditional required-entity, required-column, and required-FK results match the baseline tests.
- [x] The guide matches the tested Phase 1 syntax and Phase 2 behavior; the active superset model remains unchanged.
- [x] Required test, formatting, diff, and graph checks pass; the two pre-existing `tests/model/test_target_model_conformance.py` failures are recorded as baseline.
- [x] No unresolved question changes implementation or validation scope.
