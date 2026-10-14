# Conditional Target Model Requirements — Phase 1 Task Plan

## Phase Summary

**Goal:** Accept `foreign_keys[].required_when: {has_new_rows: <source entity>}` and report that a project-only check must wait for reconciliation.

**Readiness:** Validated. [Phase 1](CONDITIONAL_TARGET_MODEL_REQUIREMENTS_PHASE_PLAN.md#phase-1-format-and-project-only-result) is ready; the targets and validation commands below were verified against the repository. Follow the decisions in the [proposal](CONDITIONAL_TARGET_MODEL_REQUIREMENTS.md). `VM-1` is the phase validation milestone.

**Acceptance checklist**

1. [x] `PH1-AC-1` (from `P-AC-1`): Valid conditional FKs parse; unknown or non-owning sources, targets without `public_id`, and mixed `required`/`required_when` declarations are rejected.
2. [x] `PH1-AC-2` (from `P-AC-2`): Project-only conformance reports the condition as awaiting reconciliation and emits no error caused solely by that condition.
3. [x] `PH1-AC-3` (from `P-AC-6`): Existing static entity, column, and FK requirement results are unchanged; focused parity tests pass. The broad corpus command retains two pre-existing failures, detailed below.
4. [x] `PH1-AC-4` (from `P-AC-5`, tooling portion): The generated schema reference and editor schema accept and describe the new condition.

The Phase 2 reconciled-row checks depend on this parsed contract. They are outside this plan.

## Repository Findings

**Repository basis:** Branch `conditional-target-model-requirements`, commit `d7c75b16`, planned 2026-10-14. Uncommitted changes were considered. The proposal directory is untracked; the superset model, review log, and temporary entity files also have user changes. This plan leaves them untouched. Graphify pointed to the core conformance validator and backend adapter; current source and tests confirmed that path, with no conflicting graph finding.

| Verified source | Finding and implication |
| --- | --- |
| `src/target_model/models.py::ForeignKeySpec` | The model forbids extra keys and has `required: bool = False`; it cannot parse `required_when`. A strict nested condition model is needed. Detect explicit `required` using Pydantic's `model_fields_set`, since an omitted field also reads as `False`. |
| `src/target_model/spec_validator.py::TargetModelSpecValidator.validate` | It checks unknown FK targets after parsing. Add cross-entity checks for the named source, ownership, and target `public_id`; keep specific machine-readable issue codes. |
| `src/target_model/conformance.py::TargetModelConformanceValidator.validate` | Registered rules can have their severity overridden to `error`. An awaiting-reconciliation result must stay informational despite that mechanism. The existing required-entity, required-column, FK, and induced-requirement checks read only static `required` fields. |
| `backend/app/validators/target_model_validator.py::TargetModelValidator.validate`; `backend/app/mappers/validation_mapper.py::ValidationMapper.from_conformance_issue`; `backend/app/services/validation_service.py::ValidationService.validate_target_model` | The adapter parses and checks the spec before conformance; the mapper preserves severity; the service already puts `info` issues in `ValidationResult.info` and determines `is_valid` from errors. Verify this path with tests before changing production backend code. |
| `frontend/src/views/ProjectDetailView.vue::mergedValidationResult`; `frontend/src/components/validation/ValidationPanel.vue`; `frontend/src/components/validation/ValidationMessageList.vue` | The view merges `info`, but the panel builds its visible messages from errors and warnings only. The message list also styles every non-error as a warning. Show deferred information distinctly so the project result does not appear fully checked. |
| `scripts/generate_schemas.py::SCHEMA_CONFIG`; `frontend/src/composables/useMonacoYamlIntelligence.ts`; `src/target_model/schema_reference.py::MODEL_ORDER` | The editor JSON schema and Markdown reference derive from `TargetModel`. Monaco uses the JSON schema for completion with schema validation disabled. A new nested condition model must appear in the reference's model order and description. |
| `tests/target_model/test_models.py`, `tests/target_model/test_spec_validator.py`, `tests/model/test_target_model_conformance.py`, `backend/tests/validators/test_target_model_validator.py`, `backend/tests/services/test_validation_service.py`, `frontend/src/components/validation/__tests__/ValidationPanel.test.ts` | Existing test files cover each layer. The core conformance file includes `test_core_legacy_mode_matches_existing_fixture` and static FK/column/induced-requirement cases for parity. |

## Scope

**In scope:** The FK condition's strict YAML/Pydantic format and semantic checks; an informational project-only result; backend result propagation; display of that result in the validation panel; generated schema artifacts and focused regression cases.

**Out of scope:** Reconciliation or change-request enforcement, row-value checks, target projection, the user guide, a general condition language, and activation in `resources/target_models/sead_superset_model.yml`. Do not change the meaning of any existing static `required` flag.

The condition names the entity that owns the direct FK. A `via` bridge cannot supply a column on that source entity, so the strict Phase 1 contract rejects `required_when` with `via`. The target's `public_id` identifies the eventual FK column; Phase 1 does not require that column in project configuration or data.

## Work Breakdown

### Area 1: Parse and validate the FK condition

**Objective:** Accept the one supported condition shape and reject invalid declarations before conformance runs.

**Affected code:** `src/target_model/models.py::ForeignKeySpec` and a new nested condition model in that file; `src/target_model/spec_validator.py::TargetModelSpecValidator.validate`; `tests/target_model/test_models.py`; `tests/target_model/test_spec_validator.py`; `backend/tests/validators/test_target_model_validator.py`.

**Dependencies:** Proposal contract only.

- [x] `T1.1` **Add the strict condition field.**
  - **Target:** `src/target_model/models.py::ForeignKeySpec` and a **NEW symbol** for its nested `required_when` model; `tests/target_model/test_models.py`.
  - **Current → required:** Extra FK keys fail parsing → accept only an object containing `has_new_rows: <entity name>`, while rejecting malformed values and unknown condition keys.
  - **Implementation:** Make the nested model strict and describe the condition's reconciled-insert timing in Pydantic field descriptions so generated schemas explain it. Preserve the existing default and serialization of static `required`.
  - **Validation:** `V-1`; assert valid parse and round trip, plus malformed object, missing `has_new_rows`, wrong value type, and unknown nested key failures.
- [x] `T1.2` **Reject conflicting or unresolvable FKs.**
  - **Target:** `src/target_model/spec_validator.py::TargetModelSpecValidator.validate`; `tests/target_model/test_spec_validator.py`; `backend/tests/validators/test_target_model_validator.py`.
  - **Current → required:** Only an unknown FK target is checked → reject an unknown source, a source other than the owning entity, a conditional `via` bridge, a target without `public_id`, and any explicitly supplied `required` alongside `required_when` (including `required: false`).
  - **Implementation:** Use `foreign_key.model_fields_set` for the explicit-field conflict. Keep parsing errors as `INVALID_TARGET_MODEL` through the backend adapter and semantic failures as specific spec issue codes; do not run project conformance when the spec is invalid.
  - **Validation:** `V-1`, `V-2`; assert each invalid declaration is rejected and a valid one reaches conformance.

**Completion evidence:** Valid conditional YAML parses; every invalid shape or cross-entity declaration fails with a precise parse location or spec issue code.

### Area 2: Report the project-only result without changing static checks

**Objective:** Return one distinguishable awaiting-reconciliation result for each applicable conditional FK, with no conditional missing-lookup, missing-link, or missing-column error.

**Affected code:** `src/target_model/conformance.py::TargetModelConformanceValidator.validate`; `tests/model/test_target_model_conformance.py`; `backend/tests/validators/test_target_model_validator.py`; `backend/tests/services/test_validation_service.py`.

**Dependencies:** Area 1.

- [x] `T2.1` **Emit a deferred informational result.**
  - **Target:** `src/target_model/conformance.py::TargetModelConformanceValidator.validate`; `tests/model/test_target_model_conformance.py`.
  - **Current → required:** No conditional rule is represented → report a stable `CONDITIONAL_FK_AWAITING_RECONCILIATION` info issue naming source and target when the project contains the source entity. An absent source has no applicable conditional FK. The message must say that final insert decisions are unavailable in project conformance.
  - **Implementation:** Keep this status informational even if `options.validation.severity_overrides` names the rule; do not route it through code that can promote it to an error. Leave static validators' `required` checks intact. Use no data loading or provisional row counts.
  - **Validation:** `V-3`, `V-5`; test source present with lookup/link/column omitted, source absent, a project with the link, a severity override, and static checks on the same model. Assert no condition-only `MISSING_*` result and no condition-only error.
- [x] `T2.2` **Verify the backend result contract.**
  - **Target:** `backend/tests/validators/test_target_model_validator.py`; `backend/tests/services/test_validation_service.py`.
  - **Current → required:** The adapter and service support info in general → prove the new condition remains `info`, appears in `ValidationResult.info`, and leaves `is_valid=True` when there are no independent errors. Preserve `is_valid=False` for a separate static error.
  - **Implementation:** Add focused adapter and service cases; change `backend/app/validators/target_model_validator.py`, `backend/app/mappers/validation_mapper.py`, or `backend/app/services/validation_service.py` only if a test shows the existing propagation fails.
  - **Validation:** `V-2`, `V-4`.

**Completion evidence:** Core and backend report the same deferred condition; a separate static failure still fails validation.

### Area 3: Show deferred status in the validation panel

**Objective:** A person running target-model validation can see that the conditional check has not yet run.

**Affected code:** `frontend/src/components/validation/ValidationPanel.vue`; `frontend/src/components/validation/ValidationMessageList.vue`; their existing test files.

**Dependencies:** Area 2's info code and message.

- [x] `T3.1` **Display informational validation messages.**
  - **Target:** `frontend/src/components/validation/ValidationPanel.vue`; `frontend/src/components/validation/ValidationMessageList.vue`; `frontend/src/components/validation/__tests__/ValidationPanel.test.ts`; `frontend/src/components/validation/__tests__/ValidationMessageList.test.ts`.
  - **Current → required:** The view preserves `info`, but the panel hides it and the message list would give it a warning icon → include info in visible messages and counts or labels, render it with an info style, and identify the awaiting condition without presenting it as a passed check or an error.
  - **Implementation:** Keep `ValidationResult.is_valid` semantics and existing error/warning counts. Ensure the All Issues, category/entity grouping, and clipboard path can expose the info result; use the existing result contract from `ProjectDetailView.vue`.
  - **Validation:** `V-6`; test an info-only result and a mixed static-error/deferred result, including visible message text and severity treatment.

**Completion evidence:** An info-only condition is visible and clearly pending while the validation result remains valid.

### Area 4: Synchronize generated schema tooling

**Objective:** Both generated artifacts describe the accepted syntax and match their source model.

**Affected code:** `src/target_model/schema_reference.py::MODEL_ORDER` and `SECTION_INTROS`; `scripts/generate_schemas.py`; `tests/target_model/test_schema_reference.py`; generated `docs/TARGET_MODEL_SCHEMA_REFERENCE.md` and `frontend/src/schemas/targetModelSchema.json`.

**Dependencies:** Area 1.

- [x] `T4.1` **Generate and check schema artifacts.**
  - **Target:** `src/target_model/schema_reference.py::MODEL_ORDER` and `SECTION_INTROS`; `scripts/generate_schemas.py`; `tests/target_model/test_schema_reference.py`; `docs/TARGET_MODEL_SCHEMA_REFERENCE.md`; `frontend/src/schemas/targetModelSchema.json`.
  - **Current → required:** The generated schemas have no `required_when` → include its nested `has_new_rows` path and explanation in both outputs.
  - **Implementation:** Register the new nested model in the reference generator. Generate target-model artifacts from Pydantic's validation schema so they describe accepted YAML and retain the FK definitions. Run `make generate-target-model-schema-reference` and `make generate-schemas`; review generated diffs so unrelated schemas do not change. The editor schema supplies completion, while backend parsing and spec validation enforce cross-entity rules.
  - **Validation:** `V-1`, `V-7`; check reference paths, JSON schema structure and descriptions, and both sync commands.

**Completion evidence:** The generated reference and editor JSON schema contain the condition and both sync checks pass.

## Acceptance-Criteria Coverage

| Criterion | Tasks | Checks | Expected evidence |
| --- | --- | --- | --- |
| `PH1-AC-1` ← `P-AC-1` | `T1.1`, `T1.2` | `V-1`, `V-2` | Valid model parses; invalid shape, source, target, bridge, or mixed declaration fails. |
| `PH1-AC-2` ← `P-AC-2` | `T2.1`, `T2.2`, `T3.1` | `V-3`, `V-4`, `V-6` | Info result reaches API and UI; condition alone creates no error. |
| `PH1-AC-3` ← `P-AC-6` | `T1.1`, `T2.1`, `T2.2` | `V-3`, `V-4`, `V-5` | Static entity, column, FK, and induced results match existing behavior. |
| `PH1-AC-4` ← `P-AC-5` (tooling only) | `T1.1`, `T4.1` | `V-1`, `V-7` | Generated reference and editor schema describe the same strict condition. |

## Validation And Testing

Baseline checks ran on commit `d7c75b16` before implementation. The full core corpus and validation-service checks already had failures. Results below distinguish those failures from focused checks for this change.

| ID | Command or method | Expected result | Baseline | After implementation |
| --- | --- | --- | --- | --- |
| `V-1` | `rtk .venv/bin/pytest -q tests/target_model/test_models.py tests/target_model/test_spec_validator.py tests/target_model/test_schema_reference.py` | Valid condition and round trip succeed; malformed, unknown, non-owning, bridged, missing-`public_id`, and explicit mixed declarations fail; reference paths are present. | Pass: 22 tests. | Pass: 33 tests, including a dump/load regression that preserves conditional-FK semantics. |
| `V-2` | `rtk .venv/bin/pytest -q backend/tests/validators/test_target_model_validator.py` | Parse failures report `INVALID_TARGET_MODEL`; semantic failures retain specific spec codes; valid condition reaches deferred conformance. | Pass: 21 tests. | Pass: 22 tests. |
| `V-3` | `rtk .venv/bin/pytest -q tests/model/test_target_model_conformance.py` | Source-present condition is info only, even with missing lookup/link/column or severity override; source-absent condition is inactive; static results stay unchanged. | Fail: the two Arbodat corpus tests listed in `V-5`. | Fail: the same two baseline failures. Focused condition, override, absence, static parity, and legacy fixture checks pass (5 tests). |
| `V-4` | `rtk .venv/bin/pytest -q backend/tests/services/test_validation_service.py` | Deferred issue is in `info`; `is_valid` is true without independent errors and false with one. | Fail: four general `validate_project` tests listed below. | Fail: the same four baseline failures. `rtk .venv/bin/pytest -q backend/tests/services/test_validation_service.py -k TestValidateTargetModel` passes all 6 target-model service cases, including info-only and independent static-error results. |
| `V-5` | `rtk .venv/bin/pytest -q tests/model/test_target_model_conformance.py tests/target_model/test_spec_files.py` | Existing `test_core_legacy_mode_matches_existing_fixture`, static required/induced cases, and shipped target models keep their current results. | Fail: `test_core_conformance_reports_known_gaps_for_full_arbodat_project` and `test_core_conformance_current_corpus_issue_families_are_stable`. | Fail: those same two baseline failures; `tests/target_model/test_spec_files.py` passes all 4 tests. |
| `V-6` | `rtk proxy pnpm --dir frontend test:run src/components/validation/__tests__/ValidationPanel.test.ts src/components/validation/__tests__/ValidationMessageList.test.ts` | Info-only and mixed results are visible; info has its own style; existing error/warning display still works. | Pass: 7 tests. | Pass: 9 tests. |
| `V-7` | `rtk make check-target-model-schema-reference` and `rtk make check-schemas`; inspect the `ForeignKeySpec` section of `frontend/src/schemas/targetModelSchema.json` | Generated artifacts match Pydantic; `required_when.has_new_rows` and its timing description are present. | Pass: both checks. | Pass: both checks; the editor schema retains the full FK definition and includes the condition. Both generated outputs use Pydantic's validation schema so they describe accepted YAML. The reference also lists nested `model` and `naming` fields revealed by following direct schema references. |
| `V-8` | `rtk .venv/bin/black --check src/target_model/models.py src/target_model/spec_validator.py src/target_model/conformance.py src/target_model/schema_reference.py scripts/generate_schemas.py tests/target_model/test_models.py tests/target_model/test_spec_validator.py tests/model/test_target_model_conformance.py backend/tests/validators/test_target_model_validator.py backend/tests/services/test_validation_service.py`; `rtk .venv/bin/isort --check-only src/target_model/models.py src/target_model/spec_validator.py src/target_model/conformance.py src/target_model/schema_reference.py scripts/generate_schemas.py tests/target_model/test_models.py tests/target_model/test_spec_validator.py tests/model/test_target_model_conformance.py backend/tests/validators/test_target_model_validator.py backend/tests/services/test_validation_service.py`; `rtk proxy pnpm --dir frontend exec vue-tsc --noEmit`; `rtk proxy pnpm --dir frontend exec eslint src/components/validation/ValidationPanel.vue src/components/validation/ValidationMessageList.vue` | Changed Python and Vue files meet repository formatting, type, and lint rules. | Pass: formatting, imports, and type check; ESLint exits 0 with 5 existing Prettier warnings. | Pass: formatting, imports, and type check; ESLint exits 0 with the same 5 warnings and no errors. |

The four baseline `V-4` failures are `test_validate_valid_configuration`, `test_validate_project_with_foreign_key`, `test_validate_single_entity`, and `test_complex_valid_configuration`. The changed test counts are from the full commands above; the focused commands are supplemental evidence, not substitutes for failed full checks.

Use a small inline conditional model in the existing tests. Keep the existing static fixture `tests/test_data/specs/sead_standard_model.yml` unchanged. No migration or external data access is needed for Phase 1.

## Deliverables

| Deliverable | Producing tasks | Completion evidence |
| --- | --- | --- |
| `src/target_model/models.py` | `T1.1` | Strict conditional field parses and exports schema descriptions. |
| `src/target_model/spec_validator.py` | `T1.2` | All invalid cross-entity cases report specific issues. |
| `src/target_model/conformance.py` | `T2.1` | Deferred issue remains info; static checks retain behavior. |
| `tests/target_model/test_models.py`; `tests/target_model/test_spec_validator.py` | `T1.1`, `T1.2` | Positive and negative format tests pass. |
| `tests/model/test_target_model_conformance.py` | `T2.1` | Deferred and static parity cases pass. |
| `backend/tests/validators/test_target_model_validator.py`; `backend/tests/services/test_validation_service.py` | `T1.2`, `T2.2` | Adapter and service preserve code, severity, and valid status. |
| `frontend/src/components/validation/ValidationPanel.vue`; `frontend/src/components/validation/ValidationMessageList.vue`; their `__tests__/ValidationPanel.test.ts` and `__tests__/ValidationMessageList.test.ts` | `T3.1` | Deferred info is visible with distinct presentation. |
| `src/target_model/schema_reference.py`; `scripts/generate_schemas.py`; `tests/target_model/test_schema_reference.py`; `docs/TARGET_MODEL_SCHEMA_REFERENCE.md`; `frontend/src/schemas/targetModelSchema.json` | `T4.1` | Reference test and both artifact sync checks pass. |

No new file is required by the plan. Backend production files are test targets, not expected edits; add them to deliverables only if `T2.2` finds a propagation defect.

## Progress Tracker

| Area | Status | Dependency |
| --- | --- | --- |
| Area 1 — FK format and spec validation | Done | Proposal contract |
| Area 2 — Project-only result and backend contract | Done | Area 1 |
| Area 3 — Validation panel | Done | Area 2 |
| Area 4 — Generated schemas | Done | Area 1 |

## Definition Of Done

- [x] `PH1-AC-1`–`PH1-AC-4` and `VM-1` have the task and check results listed above.
- [x] Every area and deliverable is complete; baseline failures in `V-3`–`V-5` are recorded with their impact.
- [x] Conditional results remain informational before reconciliation, including under severity overrides; static error results are covered by focused parity tests.
- [x] Existing required entity, column, FK, and induced-requirement results match the focused legacy and parity tests; the two broader corpus expectations remain baseline failures.
- [x] Generated editor schema and Markdown reference are synchronized; the JSON diff adds only target-model condition schema, and the reference adds its condition plus nested paths previously omitted by reference traversal.
- [x] No Phase 2 enforcement or active superset-model change has entered this phase.
- [x] The baseline failures are documented; no unresolved question affects implementation or validation.
