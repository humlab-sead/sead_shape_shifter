# Project Data Provider Scope — Phase 2 Task Plan

## Phase Summary

**Phase:** 2, Project Binding And Save Rules. **Goal:** give each new project one registered provider-schema pair, allow an existing unbound project to receive its first pair, and prevent application saves from changing an assigned pair.

**Readiness: Validated.** [Phase 2 of the phase plan](./PROJECT_DATA_PROVIDER_SCOPE_PHASE_PLAN.md) is ready. Phase 1 supplies `DataProviderService.get_scope()` and authenticated `GET /api/v1/data-providers`; no Phase 3 provider-ID or business-key decision is needed for this phase. The deployment-host check of the Phase 1 read-only registry mount remains an operational prerequisite before using the picker in a deployed container.

Sources: [proposal](./PROJECT_DATA_PROVIDER_SCOPE.md) (`P-AC-2`, `P-AC-3`, `P-AC-5`) and [phase plan](./PROJECT_DATA_PROVIDER_SCOPE_PHASE_PLAN.md) (Phase 2, `VM-2`, `VM-3`). Keep pair checks local and deterministic. Do not assign pairs to existing checked-in projects in this phase; that is Phase 4.

Acceptance criteria:

1. [x] `PH2-AC-1` (from `P-AC-2`): new projects require one registered provider-schema pair; existing unbound projects can receive an initial pair, and project validation rejects missing or unregistered pairs.
2. [x] `PH2-AC-2` (from `P-AC-3`): multiple projects can use one pair, one provider can have several schemas, and every application save path rejects a changed or removed assigned code or schema before writing.
3. [x] `PH2-AC-3` (from `P-AC-5`): a missing or unregistered pair fails project validation without a SIMS or target-database request.

**Implementation handoff:** if current source or tests differ from the findings below, stop and report the difference before changing the design or expanding scope.

## Repository Findings

**Repository basis:** branch `project-data-provider-scope`, commit `f04a62f7`, planning date 2026-10-18. The working tree was clean; no uncommitted changes were considered. Graphify was used for navigation, then each finding below was checked in current source and tests.

| Source | Finding | Planning implication |
| --- | --- | --- |
| `backend/app/services/data_provider_service.py::DataProviderService.get_scope`; `backend/app/api/v1/endpoints/data_providers.py::list_data_providers` | The complete reviewed directory is checked on lookup; an unknown pair returns `None`. The authenticated list returns provider codes, names, schema codes, and scopes. | Reuse the local lookup for validation and saves and the list for both pickers. A malformed registry is an operational error, not an unregistered-pair result. |
| `backend/app/models/project.py::ProjectMetadata`; `backend/app/mappers/project_mapper.py::ProjectMapper.to_api_config`, `to_core_dict`; `backend/app/services/project_service.py::list_projects` | `data_provider_code` is optional, `provider_schema` is absent, the mapper only round-trips the provider code, and list results omit it. | Keep API fields nullable so legacy files still load, add schema round-trip and list projection, and enforce required values at create/validation/save points. Keep directives raw at the API/YAML layer. |
| `backend/app/services/validation_service.py::ValidationService.validate_project`; `src/specifications/project.py::IsProjectSpecification` | Structural validation checks metadata type but has no registry access. The backend service assembles `ValidationResult`. | Add the registry-backed metadata check in the backend service, with field-specific errors and no SIMS or target-database dependency; do not import backend code into `src/`. |
| `backend/app/services/project/project_operations.py::create_project`, `copy_project`, `update_metadata`; `backend/app/services/project_service.py::save_project`, `save_metadata_boundary` | Create has no pair input. Copy writes a directory before its final save. Metadata replacement omits even the existing provider code. Full save can write a stale `Project` object. | Validate before directory creation/copy or backup, compare proposed metadata with the current file before each write, and preserve both codes in metadata replacement. |
| `backend/app/api/v1/endpoints/projects.py::update_project_raw_yaml`, `restore_backup`; `backend/app/services/yaml_service.py::restore_backup` | Raw YAML creates a backup and writes before loading. Restore creates a backup and copies before reading the restored metadata. | Parse and check candidate metadata against the saved file before either backup or replacement; return a client error without changing the file on rejected requests. |
| `backend/app/api/v1/endpoints/tasks.py::migrate_tasks_to_sidecar`; `backend/app/services/auto_fix_service.py::_rollback`; `backend/app/services/project_service.py::save_options_boundary`, `save_entity_boundary` | Task migration and auto-fix rollback can write `shapeshifter.yml` outside `save_project`. Options and entity boundary saves preserve metadata. Existing entity operations use a non-reentrant per-project `Lock`. | Bring replacement/rollback writes under the same pair check. Test that section-only saves keep both codes. Coordinate read-check-write with the existing project lock without nested deadlock. |
| `frontend/src/components/projects/CreateProjectDialog.vue`; `frontend/src/components/MetadataEditor.vue`; `frontend/src/api/projects.ts`; `frontend/src/types/config.ts` | Creation has only a name; metadata has no pair controls; request and response types lack `provider_schema`. | Add provider/schema pickers for creation and initial assignment, show an assigned pair as fixed, and carry both fields through typed API calls. |
| `scripts/generate_schemas.py`; `frontend/src/schemas/projectSchema.json`; `docs/CONFIGURATION_GUIDE.md`; `docs/USER_GUIDE.md` | The project JSON schema is generated from backend Pydantic models. Current metadata guidance and create steps do not describe a pair. | Regenerate the schema and document creation, first assignment, validation, and fixed values. |

## Scope

**In scope:** API project metadata and create/update contracts; mapper round-trip; local project validation; a shared pair policy used before project YAML writes; create, copy, metadata, raw-YAML, restore, task-migration, and auto-fix rollback checks; the create and metadata UI; generated project schema; relevant tests and user/configuration guidance.

**Out of scope:** editing the reviewed provider registry, assigning pairs to checked-in projects, changing Change Request runtime inputs, SIMS scope use, SEAD provider-ID lookup, key-contract checks, and project-scope cutover. Sidecar-only and target-model-file writes do not change the project metadata pair.

An existing file with no complete pair must remain readable so its initial assignment can be made. Unrelated edits may preserve its exact unbound metadata during the transition to Phase 4; an attempted initial assignment must supply both nonblank codes and match one registered pair. Once both codes are assigned, neither may change or disappear. Direct filesystem edits require repository review and are outside application save enforcement.

## Work Breakdown

### Area 1: Carry the pair and report invalid metadata

**Objective:** API reads and YAML round-trips retain both codes; project validation reports absent, partial, blank, and unregistered pairs on the correct metadata fields.

**Affected code:** `backend/app/models/project.py::ProjectMetadata`; `backend/app/mappers/project_mapper.py::ProjectMapper`; `backend/app/services/project_service.py::list_projects`; `backend/app/services/validation_service.py::ValidationService.validate_project`; `backend/app/services/project_provider_binding_service.py` (**NEW**); `backend/tests/mappers/test_config_mapper.py`; `backend/tests/services/test_validation_service.py`; `backend/tests/services/test_project_provider_binding_service.py` (**NEW**); `backend/tests/api/v1/test_projects.py`.

**Dependencies:** Phase 1 registry service.

* [x] `T2.1` **Round-trip both metadata codes.**
  * **Target:** `backend/app/models/project.py::ProjectMetadata`; `backend/app/mappers/project_mapper.py::ProjectMapper.to_api_config`, `to_core_dict`; `backend/app/services/project_service.py::list_projects`; `backend/tests/mappers/test_config_mapper.py`; `backend/tests/api/v1/test_projects.py`.
  * **Current → required:** schema code is lost and list metadata omits the provider → both codes survive load, API response, list, and save while legacy files still load with null fields.
  * **Implementation:** add nullable `provider_schema`; map it in both directions beside `data_provider_code`; project listing reads only the two additional raw metadata values, without resolving directives or loading entities.
  * **Constraints:** do not add a target `data_provider_id`, scope UUID, or scope name to project metadata. Do not make the Pydantic fields globally required, which would prevent loading unbound projects for initial assignment.
  * **Validation:** `V-1` checks round-trip and legacy load/list behavior.
* [x] `T2.2` **Validate the saved pair locally.**
  * **Target:** `backend/app/services/project_provider_binding_service.py` (**NEW**); `backend/app/services/validation_service.py::ValidationService.validate_project`; `backend/tests/services/test_project_provider_binding_service.py` (**NEW**); `backend/tests/services/test_validation_service.py`; `backend/tests/api/v1/test_projects.py`.
  * **Current → required:** structural validation accepts a project with no pair → validation returns `is_valid=False` and field-specific errors for missing, partial, blank, or unregistered codes; a registered pair passes this check.
  * **Implementation:** use `DataProviderService.get_scope()` against the configured local directory. Check the raw metadata strings before directive resolution so `${ENV_VAR}` and `@...` cannot choose a pair. Merge pair errors with existing structural errors in `ValidationResult`; preserve existing error counts and other checks. Distinguish an unknown pair from an unreadable/invalid registry and return a safe server error for the latter.
  * **Constraints:** no SIMS, reconciliation, or target-database request; keep provider registry access in the backend, not `src/`.
  * **Validation:** `V-1` covers both `POST /api/v1/projects/{name}/validate` and service checks, including no external-client calls.

**Completion evidence:** a loaded project shows both raw codes, mapper round-trip retains them, and project validation fails for each missing or unknown pair with field-specific messages.

### Area 2: Enforce initial assignment and protect normal project saves

**Objective:** creation and metadata editing accept only valid initial assignments; ordinary project saves cannot replace a bound pair.

**Affected code:** `backend/app/api/v1/endpoints/projects.py::ProjectCreateRequest`, `MetadataUpdateRequest`, `create_project`, `update_project_metadata`; `backend/app/services/project/project_operations.py::ProjectOperations`; `backend/app/services/project_service.py::ProjectService`; `backend/app/services/project_provider_binding_service.py` (**NEW**); `backend/tests/services/test_project_service.py`; `backend/tests/services/test_project_service_boundary.py`; `backend/tests/api/v1/test_projects.py`.

**Dependencies:** Area 1's pair policy and metadata round-trip.

* [x] `T2.3` **Require a registered pair when creating or copying a project.**
  * **Target:** `backend/app/api/v1/endpoints/projects.py::ProjectCreateRequest`, `create_project`; `backend/app/services/project_service.py::create_project`, `copy_project`; `backend/app/services/project/project_operations.py::create_project`, `copy_project`; `backend/tests/services/test_project_service.py`; `backend/tests/api/v1/test_projects.py`.
  * **Current → required:** create accepts only a name, and copy can reproduce an unbound source → new and copied projects must begin with one registered pair.
  * **Implementation:** require both fields in the create request and pass them through service and operations to initial YAML metadata. Reject missing, blank, partial, or unregistered values before making a directory or assigning an authorization owner. Copy preserves the source pair and checks it before `shutil.copytree`; an unbound or unregistered source cannot create a new project. Allow two projects to use the same pair and one provider to appear with two schema codes.
  * **Constraints:** keep existing name containment and authorization checks. Treat registry read failure as an operational error with no host path in the API response.
  * **Validation:** `V-2` checks success, shared pairs, distinct schemas, missing/unknown pairs, rejected copy, and absence of a new project directory or authorization resource on failure.
* [x] `T2.4` **Check every candidate metadata write against the current file.**
  * **Target:** `backend/app/services/project_provider_binding_service.py` (**NEW**); `backend/app/services/project_service.py::save_project`, `save_metadata_boundary`; `backend/app/services/project/project_operations.py::update_metadata`; `backend/tests/services/test_project_provider_binding_service.py` (**NEW**); `backend/tests/services/test_project_service.py`; `backend/tests/services/test_project_service_boundary.py`.
  * **Current → required:** full saves can replace metadata from a stale object and metadata boundary saves drop the provider code → both save forms preserve or initially assign the pair and reject any later change/removal before backup, sidecar, or project write.
  * **Implementation:** compare candidate raw metadata to `YamlService.load()` of the current file, not cached `Project` state. For an existing unbound file, allow an unchanged unbound state or one complete registered assignment; reject a new partial state. For a bound file, require exact equality of both codes and a registered current pair. Include both fields in the metadata boundary output. Keep read-check-write coordinated with the per-project lock; account for entity operations that already hold the current non-reentrant lock, so a new guard cannot deadlock them. Invalidate caches only after a successful write.
  * **Constraints:** reject a changed provider and a changed schema independently, including `null` or omission. Keep options/entity boundary saves metadata-preserving and do not rewrite legacy unbound files just to add a pair.
  * **Validation:** `V-3` checks initial assignment, repeated unchanged saves, changed/removed fields, stale cached objects, concurrent save ordering, byte-identical rejected files, and no backup/sidecar write on rejection. It also checks options/entity saves preserve the pair.

**Completion evidence:** create/copy never writes an invalid project, and all normal saves leave an assigned pair unchanged, including description-only metadata edits.

### Area 3: Guard direct replacement and recovery paths

**Objective:** raw YAML, backup restore, task migration, and rollback cannot replace a bound pair through a path outside normal project saves.

**Affected code:** `backend/app/api/v1/endpoints/projects.py::update_project_raw_yaml`, `restore_backup`; `backend/app/api/v1/endpoints/tasks.py::migrate_tasks_to_sidecar`; `backend/app/services/auto_fix_service.py::_rollback`; `backend/app/services/project_service.py::ProjectService`; `backend/tests/api/v1/test_projects.py`; `backend/tests/api/v1/test_raw_yaml_sync.py`; `backend/tests/api/v1/test_tasks.py`; `backend/tests/services/test_auto_fix_service.py`.

**Dependencies:** Area 2's guarded write rule.

* [x] `T2.5` **Preflight raw YAML and backup restore.**
  * **Target:** `backend/app/api/v1/endpoints/projects.py::update_project_raw_yaml`, `restore_backup`; `backend/app/services/project_service.py::ProjectService`; `backend/tests/api/v1/test_projects.py`; `backend/tests/api/v1/test_raw_yaml_sync.py`.
  * **Current → required:** both endpoints write first and inspect the result afterward → each parses candidate YAML and compares its metadata with the saved file before backup or replacement.
  * **Implementation:** keep syntax, structure, path-containment, authorization, and data-source-reference checks. Read the selected backup without restoring it; reject malformed YAML, missing metadata, changed/removed codes, or an invalid first assignment before any write. Put preflight and write under the same project lock; force a reload after success. Return a clear client error for a rejected pair.
  * **Constraints:** preserve raw YAML text on successful raw saves and the existing backup-selection rule. A rejected request leaves project bytes, backups, sidecars, and cache unchanged.
  * **Validation:** `V-4` checks valid first assignment and unchanged pair, tampered provider and schema independently, removed fields, malformed backup, no write/backup on rejection, and successful restore of an unchanged bound pair.
* [x] `T2.6` **Close remaining project-file replacement paths.**
  * **Target:** `backend/app/api/v1/endpoints/tasks.py::migrate_tasks_to_sidecar`; `backend/app/services/auto_fix_service.py::apply_fixes`, `_rollback`; `backend/app/services/project_service.py::ProjectService`; `backend/tests/api/v1/test_tasks.py`; `backend/tests/services/test_auto_fix_service.py`.
  * **Current → required:** migration saves a whole YAML document directly, and auto-fix creates a backup before its guarded save and copies a backup directly on rollback → each path checks the pair before any backup, sidecar, or project-file write that could accompany a rejected change.
  * **Implementation:** move task migration's project-file replacement behind the guarded service write and ensure the guard runs before the sidecar write. In `apply_fixes`, check the loaded project's pair against disk before `_create_backup`; recheck at the final save. On rollback, check the backup's pair against the current file before `copy2`; report a failed rollback if it would remove or change a binding. Recheck after acquiring the project lock so stale snapshots cannot overwrite a newer assignment.
  * **Constraints:** keep sidecar task format and auto-fix error reporting. Do not add pair checks to sidecar-only writes or the project-local target-model file.
  * **Validation:** `V-5` checks migration and rollback with matching and mismatched pairs, no partial write on rejection, and existing task/auto-fix behavior.

**Completion evidence:** `VM-3` is met: metadata, raw-YAML, and restore rejections leave both codes and project bytes unchanged; maintenance paths cannot bypass that rule.

### Area 4: Let users choose once and document the rule

**Objective:** the UI selects a registered pair at creation or initial assignment and displays an assigned pair as fixed.

**Affected code:** `frontend/src/api/data-providers.ts` (**NEW**); `frontend/src/api/index.ts`; `frontend/src/api/projects.ts`; `frontend/src/types/config.ts`; `frontend/src/components/projects/CreateProjectDialog.vue`; `frontend/src/components/MetadataEditor.vue`; `frontend/src/api/__tests__/data-providers.test.ts` (**NEW**); `frontend/src/api/__tests__/projects.test.ts`; `frontend/src/components/projects/__tests__/CreateProjectDialog.test.ts` (**NEW**); `frontend/src/components/__tests__/MetadataEditor.test.ts` (**NEW**); `frontend/src/schemas/projectSchema.json`; `docs/CONFIGURATION_GUIDE.md`; `docs/USER_GUIDE.md`.

**Dependencies:** Areas 1–3 and the Phase 1 read endpoint.

* [x] `T2.7` **Add the provider and schema selectors.**
  * **Target:** `frontend/src/api/data-providers.ts` (**NEW**); `frontend/src/api/index.ts`; `frontend/src/api/projects.ts`; `frontend/src/types/config.ts`; `frontend/src/components/projects/CreateProjectDialog.vue`; `frontend/src/components/MetadataEditor.vue`; `frontend/src/api/__tests__/data-providers.test.ts` (**NEW**); `frontend/src/api/__tests__/projects.test.ts`; `frontend/src/components/projects/__tests__/CreateProjectDialog.test.ts` (**NEW**); `frontend/src/components/__tests__/MetadataEditor.test.ts` (**NEW**).
  * **Current → required:** the create dialog has no provider input and the metadata editor cannot assign or show a pair → both use the authenticated provider list; creation requires a schema from the chosen provider; an unbound existing project can submit one initial pair; a bound project shows both codes as read-only.
  * **Implementation:** type the existing `/data-providers` response and both project request fields. Show provider display name with code and schema code; reset the schema selection when provider changes. Disable the relevant save action and show a useful error if the list cannot load or is empty. Keep an already bound pair visible even if a registry lookup fails; server validation reports the registry problem. Update component change detection and reset state after a successful first assignment.
  * **Constraints:** no free-text scope or target provider ID; the server remains authoritative, including for raw YAML and direct API calls. Do not turn the read endpoint into a mutation API.
  * **Validation:** `V-6` checks request payloads, dependent selection, disabled empty/error state, initial assignment, and fixed display after assignment.
* [x] `T2.8` **Update generated schema and project instructions.**
  * **Target:** `frontend/src/schemas/projectSchema.json`; `docs/CONFIGURATION_GUIDE.md`; `docs/USER_GUIDE.md`.
  * **Current → required:** the schema lacks `provider_schema` and the guides describe creation without a pair → generated schema includes the field and the guides explain registered codes, one-time assignment, validation errors, and fixed display.
  * **Implementation:** run the existing `make generate-schemas` command after updating `ProjectMetadata`. Show the two approved `mal` pilot pairs as examples and say that checked-in legacy projects remain unbound until Phase 4; do not present them as already migrated. Explain that a direct file edit needs repository review.
  * **Constraints:** keep the generated schema's fields nullable for legacy reads; backend creation and validation supply the required-pair rule.
  * **Validation:** `V-7` checks generated-schema parity and the documented create/assignment steps.

**Completion evidence:** a user cannot submit a new project without selecting a registered pair, can assign an unbound project once, and sees a bound pair without editable controls.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected result |
| --- | --- | --- | --- |
| `PH2-AC-1` from `P-AC-2` | `T2.1`, `T2.2`, `T2.3`, `T2.4`, `T2.7`, `T2.8` | `V-1`, `V-2`, `V-3`, `V-6`, `V-7` | New projects and first assignments use registered pairs; missing or unknown pairs fail validation. |
| `PH2-AC-2` from `P-AC-3` | `T2.3`, `T2.4`, `T2.5`, `T2.6`, `T2.7` | `V-2`, `V-3`, `V-4`, `V-5`, `V-6` | Shared pairs and multiple schemas work; all application project-file writes preserve an assigned pair. |
| `PH2-AC-3` from `P-AC-5` | `T2.2` | `V-1` | Validation returns metadata errors from a local lookup and makes no SIMS or target-database request. |

`VM-2` is satisfied by `V-1` through `V-3` and `V-6`. `VM-3` is satisfied by `V-3` through `V-5`.

## Validation And Testing

Use an isolated temporary registry containing synthetic provider/schema values for backend tests; use the approved `mal` pairs only for documentation and a direct registry integration check. Existing backend tests that create projects need paired request data and a temporary registry. The create callers found in `backend/tests` are in `api/test_merged_entity_api.py`, `api/v1/test_columns.py`, `test_declarative_business_keys_integration.py`, `test_entities.py`, `test_mapping.py`, `test_projects.py`, `test_raw_yaml_sync.py`, `test_reconciliation_export.py`, `test_reconciliation_specifications.py`, `test_tasks.py`, `test_validation.py`, `authorization/test_project_access.py`, `security/test_filesystem_boundaries.py`, `services/test_project_service.py`, and `services/test_state_management.py` (all under `backend/tests/`). Update shared fixtures in `backend/tests/conftest.py` where useful; keep negative create cases explicitly missing or invalid. Existing validation tests with otherwise valid metadata also need a registered pair.

| ID | Check and target | Command or method | Covers | Expected result | Baseline | Execution result |
| --- | --- | --- | --- | --- | --- | --- |
| `V-1` | Mapper and local validation: `backend/tests/mappers/test_config_mapper.py`, `backend/tests/services/test_validation_service.py`, `backend/tests/services/test_project_provider_binding_service.py` (**NEW**), and validation cases in `backend/tests/api/v1/test_projects.py` | `rtk uv run pytest backend/tests/mappers/test_config_mapper.py backend/tests/services/test_validation_service.py backend/tests/services/test_project_provider_binding_service.py backend/tests/api/v1/test_projects.py -q` | `PH2-AC-1`, `PH2-AC-3` | Both codes round-trip; absent/partial/blank/unregistered values return field errors; registered pairs pass without mocked SIMS or target-database calls; malformed registry fails safely. | Existing mapper, validation, and project API tests passed; new file and cases do not exist yet. | **Pass.** Included in the final focused backend run; pair validation uses only the local registry. |
| `V-2` | Create/copy service and API cases in `backend/tests/services/test_project_service.py` and `backend/tests/api/v1/test_projects.py` | `rtk uv run pytest backend/tests/services/test_project_service.py backend/tests/api/v1/test_projects.py -q` | `PH2-AC-1`, `PH2-AC-2` | Missing, partial, blank, and unknown pairs fail before directory/resource creation; same pair works for two projects; two schemas under one provider remain distinct. | Pass: existing files passed before this plan; new cases do not exist yet. | **Pass.** Included in the final focused backend run. |
| `V-3` | Full and metadata boundary save cases in `backend/tests/services/test_project_provider_binding_service.py` (**NEW**), `backend/tests/services/test_project_service.py`, and `backend/tests/services/test_project_service_boundary.py` | `rtk uv run pytest backend/tests/services/test_project_provider_binding_service.py backend/tests/services/test_project_service.py backend/tests/services/test_project_service_boundary.py -q` | `PH2-AC-1`, `PH2-AC-2` | First assignment works once; provider or schema change/removal fails before any write; unrelated metadata, option, entity, and unchanged-pair saves retain both fields; stale/concurrent saves cannot replace a newer binding. | Existing service and boundary tests passed; new file and cases do not exist yet. | **Pass.** Included in the final focused backend run; stale snapshots and rejected writes preserve project bytes and create no backup. |
| `V-4` | Raw-YAML and restore API cases in `backend/tests/api/v1/test_projects.py` and `backend/tests/api/v1/test_raw_yaml_sync.py` | `rtk uv run pytest backend/tests/api/v1/test_projects.py backend/tests/api/v1/test_raw_yaml_sync.py -q` | `PH2-AC-2` | Valid same-pair writes succeed; tampered or incomplete pair and malformed backup fail before project/backup/sidecar writes; force reload returns the saved pair. | Pass: existing files passed before this plan; new cases do not exist yet. | **Pass.** Provider/schema changes, field removal, malformed backups, and unchanged-pair restores were checked; rejected restores/raw saves left project bytes and backups unchanged. |
| `V-5` | Task migration and auto-fix rollback in `backend/tests/api/v1/test_tasks.py` and `backend/tests/services/test_auto_fix_service.py`; backend regression | `rtk uv run pytest backend/tests/api/v1/test_tasks.py backend/tests/services/test_auto_fix_service.py -q`; then `rtk uv run pytest backend/tests -q` | `PH2-AC-2` and preserved backend behavior | Candidate with mismatched binding causes no project or sidecar change; matching binding and existing task/auto-fix flows pass. Record any environment-dependent failures separately. | Focused existing files passed. Full backend suite not run during planning; Phase 1 recorded one environment-dependent Arbodat data-validation failure. | **Focused pass.** Matching migration, rejected migration, and rejected rollback were tested. Full backend run had one known Arbodat data-validation failure: `tests/test_data/projects/arbodat/translations.tsv` is absent and the resulting expected issue set differs. Other backend tests passed. |
| `V-6` | Frontend API and component tests: `frontend/src/api/__tests__/data-providers.test.ts` (**NEW**), `projects.test.ts`, `frontend/src/components/projects/__tests__/CreateProjectDialog.test.ts` (**NEW**), `frontend/src/components/__tests__/MetadataEditor.test.ts` (**NEW**), plus project store tests | `rtk pnpm --dir frontend test:run src/api/__tests__/data-providers.test.ts src/api/__tests__/projects.test.ts src/components/projects/__tests__/CreateProjectDialog.test.ts src/components/__tests__/MetadataEditor.test.ts src/stores/__tests__/project.test.ts`; `rtk pnpm --dir frontend exec vue-tsc --noEmit` | `PH2-AC-1`, `PH2-AC-2` | Picker uses the registered list, schema depends on provider, create and first assignment send both codes, bound pair is read-only, errors disable assignment, and types compile. | Existing project API/store tests passed (75 tests). New component/API test files do not exist. Type check not run during planning. | **Pass.** Five test files, 82 tests; TypeScript check and ESLint on changed frontend files passed. |
| `V-7` | Generated schema, documentation, and quality checks | `rtk make generate-schemas`; `rtk make check-schemas`; `rtk make lint`; `rtk make frontend-lint`; inspect the metadata examples and create steps in both guides | `T2.8` and delivery quality | Schema is in sync, docs match the server and UI rule, and lint/format checks pass. | `make check-schemas` passed before changes. Generation and lint commands were not run during this read-only planning task because they write files. | **Partial.** Schema generation/parity and `make lint` passed; documentation was checked and changed-file ESLint passed. `make frontend-lint` failed on existing errors in `frontend/playwright.config.ts` and `frontend/public/sprint81-test-helper.js`. |

`VM-2` is supported by passing `V-1` through `V-3` and `V-6`. `VM-3` is supported by passing focused `V-3` through `V-5` checks, including byte-preservation and no-sidecar/no-backup assertions for rejected writes.

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Metadata and local pair policy | `backend/app/models/project.py`; `backend/app/mappers/project_mapper.py`; `backend/app/services/project_provider_binding_service.py` (**NEW**); `backend/app/services/validation_service.py`; `backend/app/services/project_service.py` | `T2.1`, `T2.2`, `T2.4` | `V-1`, `V-3` pass. |
| Creation, copy, and metadata endpoints | `backend/app/api/v1/endpoints/projects.py`; `backend/app/services/project/project_operations.py` | `T2.3`, `T2.4`, `T2.5` | `V-2` through `V-4` pass. |
| Guarded migration and rollback | `backend/app/api/v1/endpoints/tasks.py`; `backend/app/services/auto_fix_service.py` | `T2.6` | `V-5` passes. |
| Backend tests | `backend/tests/conftest.py`; `backend/tests/mappers/test_config_mapper.py`; `backend/tests/services/test_project_provider_binding_service.py` (**NEW**); `backend/tests/services/test_validation_service.py`; `backend/tests/services/test_project_service.py`; `backend/tests/services/test_project_service_boundary.py`; `backend/tests/services/test_auto_fix_service.py`; `backend/tests/api/v1/test_projects.py`; `backend/tests/api/v1/test_raw_yaml_sync.py`; `backend/tests/api/v1/test_tasks.py` | `T2.1`–`T2.6` | Focused checks pass; full backend run has the single Arbodat fixture-data failure recorded under `V-5`. |
| Existing backend create callers | `backend/tests/api/test_merged_entity_api.py`; `backend/tests/api/v1/test_columns.py`; `backend/tests/api/v1/test_declarative_business_keys_integration.py`; `backend/tests/api/v1/test_entities.py`; `backend/tests/api/v1/test_mapping.py`; `backend/tests/api/v1/test_projects.py`; `backend/tests/api/v1/test_raw_yaml_sync.py`; `backend/tests/api/v1/test_reconciliation_export.py`; `backend/tests/api/v1/test_reconciliation_specifications.py`; `backend/tests/api/v1/test_tasks.py`; `backend/tests/api/v1/test_validation.py`; `backend/tests/authorization/test_project_access.py`; `backend/tests/security/test_filesystem_boundaries.py`; `backend/tests/services/test_project_service.py`; `backend/tests/services/test_state_management.py` | `T2.3` | Each intended successful create supplies a registered pair; negative cases retain the intended failure. |
| Frontend API and UI | `frontend/src/api/data-providers.ts` (**NEW**); `frontend/src/api/index.ts`; `frontend/src/api/projects.ts`; `frontend/src/types/config.ts`; `frontend/src/components/projects/CreateProjectDialog.vue`; `frontend/src/components/MetadataEditor.vue` | `T2.7` | `V-6` passes. |
| Frontend tests | `frontend/src/api/__tests__/data-providers.test.ts` (**NEW**); `frontend/src/api/__tests__/projects.test.ts`; `frontend/src/components/projects/__tests__/CreateProjectDialog.test.ts` (**NEW**); `frontend/src/components/__tests__/MetadataEditor.test.ts` (**NEW**); `frontend/src/stores/__tests__/project.test.ts` | `T2.7` | Picker and API behavior are checked in `V-6`. |
| Schema and guidance | `frontend/src/schemas/projectSchema.json`; `docs/CONFIGURATION_GUIDE.md`; `docs/USER_GUIDE.md` | `T2.8` | Schema generation/parity and guide review passed; repository-wide frontend lint remains incomplete under `V-7`. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Metadata and validation | Complete | Phase 1 registry | `V-1` and `V-3` passed. |
| Area 2: Creation and normal saves | Complete | Area 1 | `V-2` and `V-3` passed. |
| Area 3: Replacement and recovery | Complete | Area 2 | Focused `V-4` and `V-5` passed; full suite has the recorded Arbodat fixture-data failure. |
| Area 4: UI and guidance | Complete | Areas 1–3 | `V-6` passed; `V-7` schema/docs/backend checks passed, but repository-wide frontend lint remains blocked by existing unrelated errors. |

## Definition Of Done

* [x] `PH2-AC-1`, `PH2-AC-2`, and `PH2-AC-3` each have passing task and validation results; `VM-2` and `VM-3` are recorded.
* [x] All four work areas and listed deliverables are complete.
* [ ] `V-1` through `V-7` pass, or an environment-dependent check has a specific recorded result and follow-up; required lint and type checks pass. Repository-wide frontend lint did not pass; its existing errors are recorded under `V-7`.
* [x] Rejected saves are verified to leave project bytes, backups, sidecars, and pair values unchanged; existing unrelated project edits remain covered by regression tests.
* [x] API, generated schema, frontend types, pickers, and both guides describe the same two-field contract.
* [x] No Phase 3 ingestion or Phase 4 assignment/cutover behavior has been introduced; any deviation or follow-up is documented.
* [x] No unresolved question affects Phase 2 implementation or validation.

## Risks And Open Questions

1. **Existing test callers:** many backend tests create projects with a name only. Update those fixtures and request payloads to use a temporary registry and valid pair; keep explicit negative tests for missing fields. Do not loosen the runtime creation rule to keep old tests green.
2. **Concurrent saves:** entity mutations already hold a non-reentrant project lock, while raw YAML and restore write directly. The guard must compare the current on-disk metadata and write under coordinated locking without reacquiring the same non-reentrant lock. Verify this with an interleaved-save test.
3. **Recovery ordering:** task migration writes a sidecar before replacing the main file; auto-fix creates a backup before saving and copies a backup directly on rollback. Preflight these operations before any accompanying write; otherwise a rejected pair could still leave a partial side effect.
4. **Deployed registry:** Phase 1 verified compose resolution but did not inspect the mount on a deployment host. Verify the effective read-only mount before enabling the Phase 2 picker in that deployment.
