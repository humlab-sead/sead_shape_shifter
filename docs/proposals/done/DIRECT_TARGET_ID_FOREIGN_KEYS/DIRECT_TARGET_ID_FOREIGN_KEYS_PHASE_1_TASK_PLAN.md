# Direct Target-Id Foreign Keys — Phase 1 Task Plan

## Phase Summary

**Phase:** [Phase 1: Project declaration and conformance](DIRECT_TARGET_ID_FOREIGN_KEYS_PHASE_PLAN.md#phase-1-project-declaration-and-conformance).\
**Goal:** Accept an explicit FK value source and report what can be checked before change-request validation.\
**Readiness:** Validated. The phase plan marks Phase 1 ready, repository targets and commands were checked, and no design decision remains open.\
**Sources:** [Proposal](DIRECT_TARGET_ID_FOREIGN_KEYS.md) and [phase plan](DIRECT_TARGET_ID_FOREIGN_KEYS_PHASE_PLAN.md).\
**Dependency:** The proposal's fixed declaration and direct-FK eligibility rules. Phase 2 owns database lookup and package projection; Phase 3 owns saved-project ingester handoff and complete guidance.

Phase 1 acceptance criteria (`VM-1` in the phase plan):

1. [x] `PH1-AC-1` (from `P-AC-1`): API and Core preserve `system_id` and `public_id` declarations; direct mode creates no Core FK link or dependency, and omission or `system_id` keeps current linking.
2. [x] `PH1-AC-2` (from `P-AC-2`): Invalid source, relationship, metadata, `via`, and conflicting-link declarations fail with distinct machine-readable direct-mode codes.
3. [x] `PH1-AC-3` (from `P-AC-3`): Valid direct mode allows an optional referenced entity and link to be absent, reports a pending database check, preserves globally required entities, and avoids false FK, induced-entity, and no-orphan-facts errors.
4. [x] `PH1-AC-4` (from `P-AC-9`): The API entity model and editor schema accept the declaration; the scaffold still generates local-ID links.
5. [x] `PH1-AC-5` (from `P-AC-8`): Existing `system_id` conformance results and default-path diagnostics match the recorded baseline.

## Repository Findings

**Repository basis:** `direct-target-id-foreign-keys` at `81e62836`, planned on 2026-10-23. The untracked phase plan from this topic was considered; no implementation changes were present. Graphify located the main types, but its `ProjectMapper` → `ShapeShiftProject` path was ambiguous, so the data flow below was verified in source.

| Source | Verified finding | Planning implication |
|---|---|---|
| `src/model.py::TableConfig.foreign_keys`, `depends_on`, `get_target_facing_columns` | Core dependencies and target-facing FK columns come from project `foreign_keys`; ordinary declared columns can already reach target-facing output. | Add a separate value-source accessor. Do not add direct declarations to Core FK links, dependencies, or generated FK columns. Check the declared output with `get_target_facing_columns()`, including unnest behavior. |
| `backend/app/models/project.py::Project`, `backend/app/mappers/project_mapper.py::ProjectMapper` | Project entities are raw dictionaries. Mapper conversion preserves non-special entity keys; `to_core()` resolves `metadata.target_model` directives. | Add the typed entity field for editor/API schema, and prove raw and typed mapper round trips in tests. Keep directive resolution in `ProjectMapper.to_core()` and the existing mapping path. |
| `src/specifications/project.py::CompositeProjectSpecification`, `backend/app/services/validation_service.py::validate_project` | Structural project checks run on resolved configuration. `SpecificationIssue` supports explicit codes. | Check map shape, allowed modes, and the nonempty-map target-model requirement here; return direct-mode codes through the current API mapping. |
| `backend/app/services/validation_service.py::validate_target_model` | A missing target model, including a missing referenced file, currently returns an empty valid conformance result. | Preserve that behavior for projects without the map. A nonempty direct-ID map must instead fail with a direct-mode code. |
| `src/target_model/conformance.py::TargetModelConformanceValidator` | Registered validators run separately; it assigns one severity to all issues from each validator. | Use distinct error and non-overridable informational validators so a pending database check cannot become an error through severity overrides. |
| `src/target_model/conformance.py::ForeignKeyConformanceValidator`, `InducedRequirementConformanceValidator`, `NoOrphanFactsConformanceValidator` | Required direct FKs, induced targets, and fact paths have separate checks; `RequiredEntityConformanceValidator` independently enforces global requirements. | Exempt only valid direct declarations from the first two missing-link checks. Count direct relationships as fact paths without changing Core link traversal or global requirements. |
| `backend/app/models/entity.py::Entity`, `scripts/generate_schemas.py`, `frontend/src/composables/useMonacoYamlIntelligence.ts` | `entitySchema.json` is generated from `Entity` and supplied to Monaco. `projectSchema.json` uses raw entity dictionaries. | Generate the editor schema from the model, then check schema sync and the Monaco registration. Do not hand-edit generated JSON. |
| `src/target_model/template_generator.py::_generate_entity_stub` | Required target FKs become project `foreign_keys` stubs. | Keep generation unchanged and assert that it emits no direct-ID declaration. |

## Scope

**In scope:** Project declaration access; API entity field and mapper round-trip tests; structural and target-model conformance errors; informational pending-check result; required-FK, induced-entity, and no-orphan-facts handling; generated editor schema; scaffold and default-path regression tests.

**Out of scope:** Ingester configuration, target database access, ID projection, saved-project ingester calls, manifest changes, and the final configuration and agent guides. Those belong to Phases 2 and 3. The shared target-model FK syntax stays unchanged.

## Work Breakdown

### Area 1: Preserve the project declaration

**Objective:** A project can carry the value-source map through API and Core without changing Core FK links; the editor offers the accepted modes.

**Affected code:** `src/model.py::TableConfig`; `backend/app/models/entity.py::Entity`; `backend/app/mappers/project_mapper.py::ProjectMapper` (verify existing pass-through); `scripts/generate_schemas.py::generate_schemas` (existing generator); `frontend/src/schemas/entitySchema.json` (generated); `src/target_model/template_generator.py::_generate_entity_stub` (regression target).

**Dependencies:** None.

**Tasks:**

* [x] `T1.1` **Change:** Expose the per-entity value-source map in Core without treating it as a project link.
  * **Target:** `src/model.py::TableConfig` and `tests/model/test_model.py::TestTableConfig`.
  * **Current → required:** `TableConfig` reads Core `foreign_keys` but has no direct-ID map → it returns the declared map with an empty default; `foreign_keys`, `depends_on`, and generated FK output remain link-based.
  * **Implementation:** Add a typed read-only accessor for `foreign_key_value_sources`. Do not merge its targets into link or dependency properties. Preserve explicit output columns, including the unnest target-facing rules.
  * **Constraints:** Existing Core links still carry local `system_id` values. The accessor must not infer mode from a missing referenced entity.
  * **Validation:** `V-1`: assert omitted, explicit `system_id`, and `public_id` maps; assert no new FK target or dependency and the expected declared output column.

* [x] `T1.2` **Change:** Add the API field and regenerate the editor schema; verify both mapper directions.
  * **Target:** `backend/app/models/entity.py::Entity`; `frontend/src/schemas/entitySchema.json` (generated); `backend/tests/models/test_entity.py::TestEntity`; `backend/tests/mappers/test_project_mapper_nested_models.py::TestProjectMapperNestedModels`; `tests/scripts/test_generate_schemas.py`; `frontend/src/composables/__tests__/useMonacoYamlIntelligence.test.ts`.
  * **Current → required:** The typed `Entity` model and generated schema omit the map; raw project dictionaries already pass through `ProjectMapper` → a typed map accepts only `system_id`/`public_id`, generated schema describes the default, and raw and typed mapper round trips preserve declarations.
  * **Implementation:** Add a `dict` field with allowed literal values and an empty default. Regenerate through the existing schema generator. Test `ProjectMapper.to_api_config()`, `to_core_dict()`, and `to_core()` with inline resolved target metadata; change mapper code only if those tests reveal loss. Verify Monaco receives the generated entity schema.
  * **Constraints:** `Project.entities` remains a raw dictionary and directives remain raw until `ProjectMapper.to_core()`. The editor schema is an autocomplete contract, not the sole validator for saved YAML.
  * **Validation:** `V-1`, `V-4`, `V-5`: assert typed rejection of unknown values, sparse omitted-map serialization, exact map retention, generated enum/default, and editor schema registration.

* [x] `T1.3` **Change:** Lock down the unchanged scaffold result.
  * **Target:** `tests/target_model/test_template_generator.py::test_generate_project_template_for_dating_domain_includes_required_dependency_closure` and `test_generate_project_template_renders_valid_yaml_for_explicit_entity_selection`.
  * **Current → required:** `_generate_entity_stub` emits required local-ID link stubs → generated project YAML still emits those links and no `foreign_key_value_sources` map.
  * **Implementation:** Extend the existing scaffold tests with a required-FK example and assertions for link generation and absence of the new map. Do not change the generator unless a regression is found.
  * **Constraints:** No automatic direct-mode inference from target-model metadata.
  * **Validation:** `V-4`: generated YAML keeps its current local-ID relationship form.

**Completion evidence:** Core and API round trips preserve the map, generated schema matches the typed model, and scaffold output remains local-ID based.

### Area 2: Reject malformed project declarations

**Objective:** Structural validation reports unusable maps and missing target metadata with direct-mode codes while preserving the optional-target-model default.

**Affected code:** `src/specifications/project.py::CompositeProjectSpecification`; `backend/app/services/validation_service.py::validate_target_model`.

**Dependencies:** Area 1's field contract.

**Tasks:**

* [x] `T2.1` **Change:** Validate map structure and the target-model prerequisite in the Core project specification.
  * **Target:** `src/specifications/project.py::CompositeProjectSpecification` and `ForeignKeyValueSourceSpecification` (NEW symbol in existing file); `tests/specifications/test_project.py`.
  * **Current → required:** Structural validation has no rule for this field → a non-map value, unknown mode, or nonempty map without `metadata.target_model` produces a specific code and entity/field context; absent or empty maps do not require a target model.
  * **Implementation:** Register the new specification in `get_default_specifications()`. Use `SpecificationIssue`'s explicit `code` and `field` values, and clear issue state on each run. Leave relationship eligibility to the resolved target-model conformance check in Area 3.
  * **Constraints:** Do not import backend code into Core. Accept the existing resolved target-model representation and leave projects without a map valid when target metadata is absent.
  * **Validation:** `V-2`: assert codes and field context for non-map, invalid mode, missing target model; assert empty/absent map preserves current result.

* [x] `T2.2` **Change:** Keep target-model validation from silently passing when a direct-ID map has no usable model.
  * **Target:** `backend/app/services/validation_service.py::validate_target_model`; `backend/tests/services/test_validation_service.py::TestValidateTargetModel`.
  * **Current → required:** Missing metadata or `@load:` file currently returns valid → only projects with a nonempty direct-ID map receive a direct-mode error; projects without the map keep the existing skip behavior.
  * **Implementation:** Inspect the saved project's raw entity declarations when resolution fails, and inspect the resolved project when metadata is absent. Return a `ValidationResult` with an explicit code rather than an empty result for direct mode; continue to use `ProjectMapper.to_core()` for directive resolution.
  * **Constraints:** Preserve existing missing-target behavior for projects without the map and avoid adding a second directive resolver.
  * **Validation:** `V-2`: assert both missing-metadata and missing-file direct-mode failures, plus the existing no-map skip cases and API code preservation.

**Completion evidence:** Both structural and saved-project target-model validation expose the missing prerequisite as an error; legacy projects without a target model retain their result.

### Area 3: Apply direct-ID conformance

**Objective:** A valid direct FK satisfies relationship checks without a helper project entity and receives an informational pending database-check result.

**Affected code:** `src/target_model/conformance.py::TargetModelConformanceValidator`, `ForeignKeyConformanceValidator`, `InducedRequirementConformanceValidator`, `NoOrphanFactsConformanceValidator`, `RequiredEntityConformanceValidator` (preservation target); `backend/app/validators/target_model_validator.py::TargetModelValidator` (adapter verification).

**Dependencies:** Areas 1 and 2.

**Tasks:**

* [x] `T3.1` **Change:** Validate target-model relationship eligibility and report the deferred target-ID check.
  * **Target:** `src/target_model/conformance.py::TargetModelConformanceValidator`, `ForeignKeyValueSourceConformanceValidator` (NEW symbol), and `DirectForeignKeyPendingCheckValidator` (NEW symbol); `tests/model/test_target_model_conformance.py`; `backend/tests/validators/test_target_model_validator.py`.
  * **Current → required:** No validator reads the map → each map key must name a direct target-model FK. A `public_id` entry additionally needs the target `public_id` and `target_table`, no conflicting Core link, and the FK column in `TableConfig.get_target_facing_columns()`; valid direct declarations report an informational pending target check. Explicit `system_id` keeps existing link checks.
  * **Implementation:** Check every declared target, including optional and conditional FKs. Give invalid cases distinct codes from default-path diagnostics. Use a separate non-overridable info validator so the registry's severity handling cannot promote the pending check. Verify `TargetModelValidator` preserves code, category, and severity through `ValidationMapper`.
  * **Constraints:** `system_id` and omitted entries follow existing checks. Do not validate target existence here or alter the target-model FK definition.
  * **Validation:** `V-3`: assert unknown relationship, missing `public_id`/`target_table`, `via`, conflicting link, absent output column, and a column dropped by unnest fail appropriately; valid optional/required/conditional direct FKs report `info` even with a severity override.

* [x] `T3.2` **Change:** Make existing conformance relationship checks recognize only valid direct declarations.
  * **Target:** `src/target_model/conformance.py::ForeignKeyConformanceValidator`, `InducedRequirementConformanceValidator`, `NoOrphanFactsConformanceValidator`; `tests/model/test_target_model_conformance.py`.
  * **Current → required:** Required and induced checks expect a project entity/link, and the fact-path search requires project tables → a valid direct declaration suppresses only that relationship's missing-link and induced-target errors and counts as a route to a lookup or classifier.
  * **Implementation:** Apply the direct-mode exception at each check without putting direct targets into `TableConfig.foreign_keys` or Core's target-facing link graph. Preserve transitive local-link handling and the independent `RequiredEntityConformanceValidator` result.
  * **Constraints:** Invalid direct declarations must not bypass ordinary checks. `required_when` remains informational before reconciliation, and existing bridge behavior remains unchanged.
  * **Validation:** `V-3`: assert optional referenced entity absent, global required entity still missing, direct fact-to-lookup route accepted, local transitive paths unchanged, bridge rejection, and identical default-path issue families.

**Completion evidence:** Direct-mode conformance reports only relevant pending or invalid-declaration issues while existing `system_id` projects retain their recorded issue results.

## Acceptance-Criteria Coverage

| Criterion and source | Task IDs | Validation IDs | Expected evidence |
|---|---|---|---|
| `PH1-AC-1` (`P-AC-1`) | `T1.1`, `T1.2` | `V-1` | Both representations retain the map; Core links and dependencies are unchanged. |
| `PH1-AC-2` (`P-AC-2`) | `T2.1`, `T2.2`, `T3.1` | `V-2`, `V-3` | Each invalid declaration produces a direct-mode code in its validation entry point. |
| `PH1-AC-3` (`P-AC-3`) | `T3.1`, `T3.2` | `V-3` | Valid direct mode yields a pending info issue and no false relationship issue; global requirements remain. |
| `PH1-AC-4` (`P-AC-9`) | `T1.2`, `T1.3` | `V-4`, `V-5` | Generated schema and Monaco include the map; scaffold retains local links. |
| `PH1-AC-5` (`P-AC-8`) | `T1.1`, `T1.3`, `T3.2` | `V-1`, `V-3`, `V-4` | Current corpus issue codes and scaffold behavior match baseline. |

## Validation And Testing

`VM-1` is complete when `V-1`–`V-5` pass and their results demonstrate all five phase criteria. Baselines below are from this checkout before implementation. The proposal's two previously reported ArboDat/corpus failures both **passed** in the current baseline; treat any later failure as a new regression unless repository state changes.

| ID | Check and exact test targets | Command or method | Covers | Expected result | Baseline |
|---|---|---|---|---|---|
| `V-1` | Core model, typed entity, mapper round trips: `tests/model/test_model.py`, `backend/tests/models/test_entity.py`, `backend/tests/mappers/test_project_mapper_nested_models.py` | `rtk uv run pytest tests/model/test_model.py backend/tests/models/test_entity.py backend/tests/mappers/test_project_mapper_nested_models.py -q` | `PH1-AC-1`, `PH1-AC-5` | Accepted modes and default round-trip; direct map adds no Core link/dependency. | Pass: all three files passed across focused baseline runs. |
| `V-2` | Structural and service errors: `tests/specifications/test_project.py`, `backend/tests/services/test_validation_service.py` | `rtk uv run pytest tests/specifications/test_project.py backend/tests/services/test_validation_service.py -q` | `PH1-AC-2` | Invalid/missing metadata returns direct-mode codes; no-map missing target still passes. | Pass: both files passed in a focused baseline run. |
| `V-3` | Core and API conformance: `tests/model/test_target_model_conformance.py`, `backend/tests/validators/test_target_model_validator.py` | `rtk uv run pytest tests/model/test_target_model_conformance.py backend/tests/validators/test_target_model_validator.py -q` | `PH1-AC-2`, `PH1-AC-3`, `PH1-AC-5` | Direct eligibility, info severity, required/global/orphan behavior, and default issue families match expected results. | Pass: both files passed in a focused baseline run, including the two named corpus tests. |
| `V-4` | Scaffold and generated-schema contract: `tests/target_model/test_template_generator.py`, `tests/scripts/test_generate_schemas.py`, generated `frontend/src/schemas/entitySchema.json` | `rtk uv run pytest tests/target_model/test_template_generator.py tests/scripts/test_generate_schemas.py -q`; `rtk make check-schemas` | `PH1-AC-4`, `PH1-AC-5` | Scaffold keeps project FK links; generated schema matches Pydantic and has the two allowed values. | Pass: test files passed across focused runs; schema check passed. |
| `V-5` | Monaco schema registration: `frontend/src/composables/__tests__/useMonacoYamlIntelligence.test.ts` | From `frontend/`: `pnpm test:run src/composables/__tests__/useMonacoYamlIntelligence.test.ts` | `PH1-AC-4` | Entity editor registers a schema containing the declaration and accepted values. | Pass: one existing test passed. |
| `V-6` | Repository quality gate | `rtk make lint`; `rtk make frontend-lint`; `git diff --check` | All changed files | Formatting, static checks, and whitespace checks pass after implementation. | `make lint` was not run before implementation. |

Regenerate `frontend/src/schemas/entitySchema.json` with the verified `make generate-schemas` target before `V-4`. The target-model and ingester regression suites beyond Phase 1 are assigned to later phase task plans; this phase runs the conformance and scaffold portions that its changes can affect.

## Execution Record

**Executed:** 2026-10-23. All tasks `T1.1`–`T3.2` are complete.

| Validation | Result |
|---|---|
| `V-1` | Pass: Core/API models and mapper tests passed; omitted maps remain sparse and both modes round-trip. |
| `V-2` | Pass: structural specification and validation-service tests passed, including both missing-target-model paths. |
| `V-3` | Pass: Core and API conformance tests passed for direct eligibility, pending info severity, required entities, no-orphan paths, and unchanged corpus issue families. |
| `V-4` | Pass: scaffold/schema tests passed; `rtk make check-schemas` confirmed generated schemas are in sync. |
| `V-5` | Pass: Monaco schema registration test passed with both modes and the empty default. |
| `V-6` | Partial: `rtk make frontend-lint`, `rtk make pylint-changed`, and `git diff --check` passed. `rtk make lint` reached Pylint but failed on two `C1803` findings in unchanged `backend/tests/services/test_file_manager.py:209,221`. The same comparisons are present at `HEAD`; the task's changed Python files pass `pylint-changed`. |

The repository-wide lint failure is pre-existing and unrelated to this phase. The implementation introduces no additional Pylint findings.

## Deliverables

| Deliverable | Exact target | Task IDs | Completion evidence |
|---|---|---|---|
| Core declaration accessor | `src/model.py::TableConfig` | `T1.1` | Accessor returns the map without changing link or dependency results. |
| API declaration field | `backend/app/models/entity.py::Entity` | `T1.2` | Typed field accepts only the two modes. |
| Generated editor schema | `frontend/src/schemas/entitySchema.json` | `T1.2` | Generated file passes schema sync. |
| Structural declaration rule | `src/specifications/project.py::ForeignKeyValueSourceSpecification` (NEW symbol) and `CompositeProjectSpecification` | `T2.1` | Invalid shape or missing target model has explicit codes. |
| Missing-target service result | `backend/app/services/validation_service.py::validate_target_model` | `T2.2` | Direct mode fails when the target model is absent; no-map projects keep current behavior. |
| Direct-mode conformance | `src/target_model/conformance.py::TargetModelConformanceValidator`, `ForeignKeyValueSourceConformanceValidator` (NEW symbol), `DirectForeignKeyPendingCheckValidator` (NEW symbol) | `T3.1` | Eligibility errors and pending info have distinct codes and correct severity. |
| Relationship conformance | `src/target_model/conformance.py::ForeignKeyConformanceValidator`, `InducedRequirementConformanceValidator`, `NoOrphanFactsConformanceValidator` | `T3.2` | Valid direct relationships satisfy only the intended checks. |
| Core and conformance tests | `tests/model/test_model.py`, `tests/model/test_target_model_conformance.py`, `tests/specifications/test_project.py`, `tests/target_model/test_template_generator.py` | `T1.1`, `T1.3`, `T2.1`, `T3.1`, `T3.2` | `V-1`–`V-4` pass. |
| API and service tests | `backend/tests/models/test_entity.py`, `backend/tests/mappers/test_project_mapper_nested_models.py`, `backend/tests/services/test_validation_service.py`, `backend/tests/validators/test_target_model_validator.py` | `T1.2`, `T2.2`, `T3.1` | `V-1`–`V-3` pass. |
| Schema and editor tests | `tests/scripts/test_generate_schemas.py`, `frontend/src/composables/__tests__/useMonacoYamlIntelligence.test.ts` | `T1.2` | `V-4` and `V-5` pass. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
|---|---|---|---|
| Area 1: Preserve the project declaration | Complete | None | API/Core round trips, generated schema, and local-ID scaffold regression passed. |
| Area 2: Reject malformed project declarations | Complete | Area 1 | Structural and service errors passed; no-map projects retain optional-target-model behavior. |
| Area 3: Apply direct-ID conformance | Complete | Areas 1–2 | Eligibility, pending info, relationship checks, global requirements, and baseline corpus tests passed. |

## Definition Of Done

* [x] `PH1-AC-1`–`PH1-AC-5` each have completed task and validation evidence in the coverage table.
* [x] All three work areas and listed deliverables are complete.
* [x] `V-1`–`V-6` pass, or any failure is explained against the recorded baseline before handoff.
* [x] Existing Core link, default conformance, optional-target-model, and scaffold behavior has been regression-tested.
* [x] API model and generated editor schema match; no ingester behavior is claimed as complete in this phase.
* [x] Deviations and follow-up work are recorded, and no unresolved question affects implementation or validation.

If implementation reveals repository behavior that conflicts with a verified finding here, stop that task and report the source and test result before changing the design or expanding scope.
