# Project Data Provider Scope — Phase 3 Task Plan

## Phase Summary

**Phase:** 3, Provider-Scoped Change Request Integration. **Goal:** make Change Request validation and ingestion use the authorized saved project's provider-schema pair, fixed SEAD provider row, and declared business keys, and record the effective SIMS scope and run ID in the result and bundle.

**Readiness: Validated.** The [proposal](./PROJECT_DATA_PROVIDER_SCOPE.md) and [Phase 3 plan](./PROJECT_DATA_PROVIDER_SCOPE_PHASE_PLAN.md) now require one operator-reconciled fixed `data_provider` row per project and use `EntityConfig.keys` as the only business-key declaration. The transformed delivery must pass key validation before any SIMS call. The implementation tasks below include provider-ID verification, stable key serialization, and review of each enabled provider schema. If repository state contradicts these contracts, stop and report the conflict before changing the design.

**Dependencies:** Phase 1 registry lookup and Phase 2 project binding, whose completed checks are recorded in the [Phase 2 task plan](./PROJECT_DATA_PROVIDER_SCOPE_PHASE_2_TASK_PLAN.md). Phase 3 must review each enabled provider schema's declared keys before SIMS is used. Existing `sead-change-request:*` identities and project assignments remain Phase 4 cutover decisions.

Sources: [proposal](./PROJECT_DATA_PROVIDER_SCOPE.md) (`P-AC-4` through `P-AC-7`) and [phase plan](./PROJECT_DATA_PROVIDER_SCOPE_PHASE_PLAN.md) (Phase 3, `VM-4`, `VM-5`). Preserve `provider://<provider-code>/<provider-schema>` as the full scope name, lookup-only target `data_provider`, and exactly one provider row and one submission row per bundle.

Acceptance criteria:

1. [x] `PH3-AC-1` (from `P-AC-4`): the saved pair selects the SIMS scope, the authorized saved project supplies the fixed provider row, caller-supplied project/provider/schema/scope values cannot override them, and the response and manifest contain the effective scope and run ID.
2. [x] `PH3-AC-2` (from `P-AC-5`): a missing or unregistered saved pair fails before an identity request, file write, or target-database access.
3. [x] `PH3-AC-3` (from `P-AC-6`): the authorized project's one fixed provider row supplies an operator-reconciled ID that matches its provider code in SEAD before SIMS; the bundle emits one lookup-only provider row.
4. [x] `PH3-AC-4` (from `P-AC-7`): `EntityConfig.keys` supplies tracked business keys and a deterministic `business_id`; absent, blank, duplicate, or incompatible keys block all SIMS calls, and changed key meaning requires a new schema code or explicit identity migration.

## Repository Findings

**Repository basis:** branch `project-data-provider-scope`, commit `3917cba3`, planning date 2026-10-18. Phase 2 code was inspected before and after its commit; no uncommitted implementation changes remain. This revision updates the existing untracked Phase 3 draft. Graphify was used for navigation; the findings below were checked in source, tests, project data, and the sibling authority-service configuration. The focused baseline run passed with three skipped tests; new Phase 3 cases do not exist yet.

| Source | Verified finding | Planning implication |
| --- | --- | --- |
| `backend/app/services/project_provider_binding_service.py::ProjectProviderBindingService.require_registered_pair`; `backend/app/services/data_provider_service.py::DataProviderService.get_scope` | The Phase 2 code can validate a saved pair against the local reviewed registry; the registry returns the full scope name for a pair. | Reuse this local check before any ingester preparation or external request. Do not derive a scope from project name or a target ID. |
| `backend/app/api/v1/endpoints/ingesters.py::validate_data`, `ingest_data`; `backend/app/authorization/dependencies.py::require_project` | Both ingester routes require application `run_ingesters`, but do not authorize a project. `require_project(body_locator=True)` reads a top-level `project_name`; the current Change Request form sends it inside `submission_context`. | Define a trusted project locator in the request or route, require project authorization, then load its saved metadata. Nested submission context alone is not an authorization input. Preserve unrelated ingesters. |
| `backend/app/services/ingester_service.py::IngesterService.validate`, `ingest`, `_create_config`; `backend/app/services/ingester_runtime.py::inject_ingester_runtime_dependencies`, `SeadChangeRequestSimsAdapter._build_scope_name` | Request config and submission context reach the ingester. The runtime accepts `sims_scope_name` from config and otherwise uses `sead-change-request:{project_name}`. | For the Change Request path, construct trusted provider and scope inputs from the saved project and prevent request config or runtime overrides from replacing them. |
| `ingesters/sead_change_request/input_resolution.py::_resolve_submission_context`; `ingesters/sead_change_request/contracts.py::SubmissionContext`; `frontend/src/components/ingester/IngesterForm.vue` | Caller context supplies `project_name` and `data_provider_code`; the UI reads the provider code from selected project metadata but sends it as request data. The context has a run ID, minted when absent. | Backend must replace caller identity values after authorization. Keep one effective run ID through SIMS, response, and manifest. |
| `ingesters/sead_change_request/ingester.py::SeadChangeRequestIngester._add_submission_tables`; `backend/app/services/ingester_runtime.py::SeadChangeRequestReconciliationAdapter.reconcile_entity`; `ingesters/sead_change_request/input_resolution.py::_resolve_source_bundle` | Provider lookup currently calls reconciliation with `data_provider_code`; the adapter chooses a best candidate and extracts a numeric suffix. The stock authority service has no `data_provider` query type. Change Request loads tables from the submitted workbook, not from the project. | Read the fixed row from the authorized saved project, verify its ID/code against SEAD, and pass it separately from caller input. Remove the provider-specific reconciliation call. |
| `ingesters/sead_change_request/submission_tables.py::build_submission_source_bundle`; `data/specs/sead_standard_model.yml` | Submission derivation creates one `data_provider` row and one `submission` row; the target model marks `data_provider` as `lookup-only`, and submitted provider tables are reserved. | Keep the row count and lookup-only contract, using only the trusted fixed row. The workbook remains unable to supply a provider row. |
| `backend/app/services/validation_service.py::ValidationService.validate_project` | Project validation checks the registered pair but has no fixed provider-row structural check. | Add field-specific fixed-row errors without a live target request. |
| `backend/app/models/entity.py::Entity.keys`; `src/model.py::TableConfig.safe_keys`; `src/normalizer.py::ShapeShifter._check_duplicate_keys`; `backend/app/services/ingester_runtime.py::SeadChangeRequestSimsAdapter._build_identity_value` | Ordered `EntityConfig.keys` are in project configuration, but the ingester does not receive them. Core duplicate checking only logs an error, and SIMS serializes every nonempty row field. | Pass ordered keys from the saved project, derive a stable `business_id`, and reject missing or duplicate values for every tracked project entity before any SIMS request. |
| `ingesters/sead_change_request/sql_builder.py::_base_deploy_artifact_metadata`; `ingesters/sead_change_request/artifact_writer.py::write_artifact_bundle`; `backend/app/models/ingester.py::IngestResponse` | The manifest is written from `metadata_artifact`; neither it nor the API response exposes the effective scope and run ID today. | Carry the same trusted values into both outputs and test equality with the SIMS request. |
| `backend/app/mappers/project_mapper.py::ProjectMapper.to_core`; `deployment/container/resources/data-providers/mal.yml`; `data/projects/` | Directives in saved entity keys resolve through `ProjectMapper.to_core()`. The registry has two `mal` pilot schemas, but no checked-in project YAML declares `provider_schema`. | Build trusted key inputs from the mapped saved project. Use synthetic bound projects in Phase 3 tests; existing-project assignments remain Phase 4 work. |

## Scope

**In scope:** project authorization and saved-pair loading for Change Request validate/ingest; preflight for missing pair, fixed provider row, and keys; trusted scope and provider inputs; read-only SEAD ID/code verification; tracked identity key serialization and uniqueness checking before SIMS; response and manifest metadata; focused API, runtime, ingester, bundle, and UI contract tests.

**Out of scope:** creating SEAD provider rows; storing target IDs or SIMS UUIDs in the registry or project metadata; adding a second business-key declaration; redesigning FK linking under issue #507; changing the provider registry; assigning existing project files; migration or abandonment of old project-scoped SIMS identities; production cutover; unrelated ingesters.

## Work Breakdown

These tasks are ready for implementation against the verified targets below. Phase 4 still controls when real projects switch to provider-schema scopes.

### Area 1: Authorize and check the saved project before work

**Objective:** Change Request validate and ingest use one authorized project and reject a missing or unregistered saved pair before external or file effects.

**Affected code:** `backend/app/api/v1/endpoints/ingesters.py::validate_data`, `ingest_data`; `backend/app/models/ingester.py::ValidateRequest`, `IngestRequest`; `backend/app/services/ingester_service.py::IngesterService.validate`, `ingest`; `backend/app/services/project_service.py::ProjectService.load_project`; `backend/app/services/project_provider_binding_service.py::ProjectProviderBindingService.require_registered_pair`; `backend/tests/api/test_ingesters.py`; `backend/tests/api/test_sead_change_request_project_scope.py` (**NEW**).

**Dependencies:** validated Phase 2 binding. Use a top-level `project_name` request field with `require_project(body_locator=True)` for Change Request routes; nested submission context is not the authorization locator.

* [x] `T3.1` **Use an authorized saved project for Change Request runs.**
  * **Target:** the endpoint, request, service, and test targets above.
  * **Current → required:** `run_ingesters` alone authorizes the request and nested context controls project/provider values → an authorized top-level project locator selects the saved project; its registered pair, fixed provider row, and resolved ordered keys are checked before ingester clients or target data are used.
  * **Implementation:** retain application `run_ingesters`; require project authorization with the top-level `project_name`, load the saved project, and use `ProjectMapper.to_core()` to resolve key directives. Pass a trusted project description containing the full scope, fixed provider row, and ordered keys to Change Request orchestration. Reject conflicting nested `project_name`, `data_provider_code`, `provider_schema`, and `sims_scope_name`. Leave other ingester keys on their existing contracts.
  * **Constraints:** `src/` cannot import backend services; an unauthorized project must not reveal its metadata. Missing or invalid saved values must cause no SIMS call, target-database call, or bundle write.
  * **Validation:** `V-2` uses `backend/tests/api/test_sead_change_request_project_scope.py` (**NEW**) with two authorized projects and mocks for SIMS, target database, and output writer; tampered and unauthorized requests cannot switch projects, and missing/unregistered pairs leave every mock untouched.

**Completion evidence:** `VM-4` has a recorded authorized/tampered request result and zero effects for invalid saved pairs.

**Recorded result:** `backend/app/authorization/dependencies.py::require_ingester_project` authorizes the top-level `project_name` for `sead_change_request` only; `IngesterService` loads that saved project and injects `TrustedProjectContext`; `_reject_conflicting_identity_inputs` and `_apply_trusted_context` reject nested `project_name`, `data_provider_code`, `provider_schema`, `scope_name`, and a `sims_scope_name` extra. `V-2` passed: 4 new API cases (authorized run, nested project-name tamper, unregistered out-of-band pair, unknown project) plus the runtime scope cases. Tampered and invalid requests created no `SimsClient` and no collision checker, so no SIMS, target-database, or writer effect occurred.

### Area 2: Use the trusted scope and fixed provider ID

**Objective:** the saved pair selects every SIMS scope and the saved fixed provider row supplies an ID/code pair verified against SEAD.

**Affected code:** `backend/app/services/ingester_runtime.py::inject_ingester_runtime_dependencies`, `SeadChangeRequestSimsAdapter._build_scope_name`, `SeadChangeRequestTargetCollisionChecker.row_exists`; `backend/app/services/ingester_service.py::IngesterService._create_config`; `backend/app/services/validation_service.py::ValidationService.validate_project`; `backend/app/services/project_data_provider_service.py` (**NEW**); `ingesters/sead_change_request/ingester.py::SeadChangeRequestIngester._add_submission_tables`; `ingesters/sead_change_request/submission_tables.py::build_submission_source_bundle`; `backend/tests/services/test_project_data_provider_service.py` (**NEW**); `backend/tests/services/test_validation_service.py`; `backend/tests/ingesters/test_sead_change_request_runtime.py`; `backend/tests/ingesters/test_sead_change_request_ingester.py`; `backend/tests/ingesters/test_sead_change_request_submission_tables.py`.

**Dependencies:** Area 1. Use the existing target-database `row_exists` adapter for read-only ID/code verification; absence of target-database configuration blocks the Change Request run.

* [x] `T3.2` **Force the saved provider-schema scope for SIMS.**
  * **Target:** `backend/app/services/ingester_runtime.py::inject_ingester_runtime_dependencies`, `SeadChangeRequestSimsAdapter._build_scope_name`; `backend/app/services/ingester_service.py::IngesterService._create_config`; `backend/tests/ingesters/test_sead_change_request_runtime.py`.
  * **Current → required:** config can override scope and project name supplies a fallback → Change Request SIMS requests use only the registry scope selected by the authorized saved pair.
  * **Implementation:** pass the trusted full scope into the SIMS adapter for both individual and batch resolution, reject caller `sims_scope_name`, and ensure the Change Request path cannot fall back to `sead-change-request:{project_name}`.
  * **Constraints:** `scope_uuid` and `data_provider_id` are never scope inputs; keep the full slash-containing schema code in one scope name.
  * **Validation:** `V-2` checks an exact `provider://mal/<schema>` value for both SIMS request shapes and a tampered scope override.
* [x] `T3.3` **Use the operator-reconciled provider row.**
  * **Target:** `backend/app/services/project_data_provider_service.py` (**NEW**); `backend/app/services/validation_service.py::ValidationService.validate_project`; `backend/app/services/ingester_runtime.py::SeadChangeRequestTargetCollisionChecker.row_exists`; `ingesters/sead_change_request/ingester.py::SeadChangeRequestIngester._add_submission_tables`; `ingesters/sead_change_request/submission_tables.py::build_submission_source_bundle`; `backend/tests/services/test_project_data_provider_service.py` (**NEW**); `backend/tests/services/test_validation_service.py`; `backend/tests/ingesters/test_sead_change_request_ingester.py`; `backend/tests/ingesters/test_sead_change_request_submission_tables.py`.
  * **Current → required:** the current reconciliation call cannot find `data_provider` in the stock authority service → exactly one saved fixed row provides a positive `data_provider_id`, and a read-only target query confirms that ID and the saved provider code identify the same SEAD row before SIMS.
  * **Implementation:** add a backend structural check for `type: fixed`, `public_id: data_provider_id`, `keys: [data_provider_code]`, and exactly one literal row. Require the row code to match saved metadata and its ID to be a positive integer. Return field-specific errors from project validation without a target-database call, and apply the same check to the authorized saved project before ingestion. Use `row_exists` with both ID and code on the target model's `tbl_data_providers`; fail if the database adapter is absent or no row matches. Build one lookup-only provider row from this trusted data and one submission row; reject workbook-supplied provider tables.
  * **Constraints:** no provider row creation; no ID from registry, project metadata, or caller context; keep `lookup-only` target-model behavior. Check the pair before target-database access and the ID/code before SIMS.
  * **Validation:** `V-3` checks zero/two fixed rows, malformed or missing ID, wrong code, missing database adapter, no SEAD match, and exactly one provider and submission row after a valid match. Structural project validation makes no database call, and every invalid ingestion case makes zero SIMS calls.

**Completion evidence:** SIMS receives the bound scope only after the fixed ID/code matches SEAD, and the bundle has one provider row and one submission row.

**Recorded result:** `SeadChangeRequestSimsAdapter._build_scope_name` reads only `SubmissionContext.scope_name` and raises when it is absent, so no `sead-change-request:{project}` fallback remains. `ProjectDataProviderService` (new) provides `fixed_row_errors` (no database call), `require_fixed_row`, and `build_trusted_context`. `SeadChangeRequestIngester._verify_provider_row` calls `row_exists("tbl_data_providers", {data_provider_id, data_provider_code})` and blocks when the checker is absent or returns no match; the previous provider reconciliation call is removed. `V-3` passed, including malformed/missing ID, wrong code, zero and two rows, missing adapter, no SEAD match, and the one-provider-row/one-submission-row bundle.

### Area 3: Enforce the approved keys before identity work

**Objective:** every tracked project entity uses ordered `EntityConfig.keys`, and a failing key validator stops the whole run before SIMS.

**Affected code:** `backend/app/services/ingester_runtime.py::SeadChangeRequestSimsAdapter._build_identity_value`; `backend/app/services/project_service.py::ProjectService.validate_project_file_write`, `save_metadata_boundary`, `save_entity_boundary`, `save_entity_rename_boundary`; `ingesters/sead_change_request/ingester.py::SeadChangeRequestIngester._prepare_change_request`; `ingesters/sead_change_request/planning.py::plan_table`; `ingesters/sead_change_request/preparation.py::prepare_change_request`; `src/business_keys.py` (**NEW**); `backend/tests/services/test_project_service_boundary.py`; `backend/tests/services/project/test_entity_operations_boundary.py`; `backend/tests/ingesters/test_sead_change_request_runtime.py`; `backend/tests/ingesters/test_sead_change_request_identity_work.py`; `backend/tests/ingesters/test_sead_change_request_ingester.py`; `tests/test_business_keys.py` (**NEW**).

**Dependencies:** Area 1 provides resolved ordered keys from the saved project. Complete provider-schema review before enabling either pilot schema; the review is an entry check, not a second configuration format.

* [x] `T3.4` **Validate and serialize declared business keys before SIMS.**
  * **Target:** the runtime, project-save, ingester, planning, preparation, core helper, and test targets above.
  * **Current → required:** SIMS identity values are built from every nonempty row field and Core only logs duplicate keys → a deterministic `business_id` from the saved project's ordered `EntityConfig.keys` drives tracked SIMS identity values, and any missing, blank, or duplicate key in the complete transformed delivery blocks all SIMS calls.
  * **Implementation:** add a shared serializer that encodes `business_id` as compact UTF-8 JSON shaped `[1, [[column, type, value], ...]]` in declared key order. Use type tags `string`, `number`, `boolean`, `date`, and `datetime`; preserve string case and contents, normalize numbers to decimal text, format dates as ISO text, and convert timezone-aware datetimes to UTC ISO text. Reject null, NaN, blank strings, naive datetimes, and unsupported types. Run the validator on the complete transformed source bundle immediately after input resolution, before the target-database provider check or identity orchestration. Require nonempty keys and present columns for every tracked project entity, and reject duplicate computed values within each entity table. Reject managed `system_id` and target `public_id` as tracked business keys. Compare ordered declarations for overlapping tracked entities in projects bound to the same pair; reject changes through every application save path once the project is bound. Review key meaning before enabling each pilot schema. A key repeated in a later delivery resolves to the same identity, so it is not a validation error by itself.
  * **Constraints:** no second provider-facing key list and no project-name namespace fallback. Keep the computed `business_id` internal to identity work; FK-linking changes remain issue #507. Do not alter lookup-only or derived identities merely to satisfy tracked-key checks.
  * **Validation:** `V-4` uses two deliveries sharing a pair with a repeated stable key, two distinct schema scopes, missing/null/blank keys, duplicate composite values in one delivery, a missing projected key column, a managed-ID key, changed ordered declarations, and a changed non-key field. Every rejected case has zero SIMS calls; stable repeats reuse the same identity.

**Completion evidence:** `VM-5` shows one stable `business_id` per tracked source entity, no SIMS call on failed validation, and no cross-schema identity collision.

**Recorded result:** `src/business_keys.py` (new) encodes `[1, [[column, type, value], ...]]` in declared order with `string`, `number`, `boolean`, `date`, and `datetime` tags and rejects null, NaN, blank, naive datetimes, managed identifiers, and unsupported types. `SeadChangeRequestIngester._validate_business_keys` runs on the complete bundle before `_verify_provider_row` and before SIMS. `ProjectService._validate_business_key_write` and `_validate_entity_key_write` reject key changes on bound projects in the full-save, metadata, entity, and rename paths, and `_shared_pair_key_errors` rejects different declarations for a pair shared by two projects. A repeated key in a later delivery reuses identity because the serialization is value-only. `V-4` passed: 29 core cases plus project-save, runtime, and ingester cases; every rejected case recorded zero SIMS batches.

### Area 4: Record the effective scope and run

**Objective:** the API result and emitted manifest identify the same scope and run ID used in SIMS.

**Affected code:** `ingesters/sead_change_request/contracts.py::SubmissionContext`; `ingesters/sead_change_request/sql_builder.py::_base_deploy_artifact_metadata`; `ingesters/sead_change_request/artifact_writer.py::write_artifact_bundle`; `backend/app/ingesters/protocol.py::IngestionResult`; `backend/app/models/ingester.py::IngestResponse`; `backend/app/services/ingester_service.py::IngesterService.ingest`; `frontend/src/types/ingester.ts`; `frontend/src/components/ingester/IngesterForm.vue`; `backend/tests/ingesters/test_sead_change_request_sql_builder.py`; `backend/tests/ingesters/test_sead_change_request_ingester.py`; `backend/tests/api/test_ingesters.py`; `frontend/src/components/ingester/__tests__/IngesterForm.test.ts`.

**Dependencies:** Areas 1–3. Keep one run ID from preparation through output.

* [x] `T3.5` **Expose the effective scope and run ID.**
  * **Target:** the contract, output, API, frontend, and test targets above; `ingesters/sead_change_request/README.md`; `docs/USER_GUIDE.md`.
  * **Current → required:** run ID exists in submission context but response and manifest omit it and the scope → both outputs carry the same effective values as the SIMS request.
  * **Implementation:** propagate the trusted scope and one persisted run ID through the Change Request result, `IngestResponse`, deploy artifact metadata, and `manifest.json`; show the values in the Change Request UI without allowing users to edit scope. Update the user and ingester guides with the required project binding, fixed provider row, declared keys, and emitted values. Preserve existing manifest fields and SQL bundle content.
  * **Constraints:** a run ID is meaningful with its scope; never report request-supplied values as effective values. Do not change other ingester responses beyond optional compatible fields.
  * **Validation:** `V-5` compares API JSON, in-memory artifact, emitted manifest, and the captured SIMS request for equality on scope and run ID, for both inline and copy-CSV strategies.

**Completion evidence:** `VM-5` shows matching scope/run values in each output while the provider and submission rows remain unchanged in count and lookup behavior.

**Recorded result:** `IngestionResult` and `IngestResponse` carry `scope_name` and `run_id`; `_base_deploy_metadata` and `_base_deploy_artifact_metadata` record the same two values, so `manifest.json` matches the response. `IngesterForm.vue` shows both values and sends the authorized project locator as a top-level `project_name`. `V-5` passed on the backend and the frontend (`3 passed`).

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected result |
| --- | --- | --- | --- |
| `PH3-AC-1` from `P-AC-4` | `T3.1`, `T3.2`, `T3.5` | `V-2`, `V-5` | Authorized saved project controls scope and fixed provider inputs; response and manifest match the SIMS scope/run. |
| `PH3-AC-2` from `P-AC-5` | `T3.1`, `T3.4` | `V-2`, `V-4` | Invalid saved pair or key contract stops before identity, target-database, or file effects. |
| `PH3-AC-3` from `P-AC-6` | `T3.3`, `T3.5` | `V-3`, `V-5` | One provider row uses the fixed project's ID only after SEAD confirms its code; no registry, metadata, or caller ID is used. |
| `PH3-AC-4` from `P-AC-7` | `T3.4` | `V-4` | Declared keys produce stable `business_id` values; invalid or incompatible keys block all SIMS calls. |

`VM-4` requires `V-2`; `VM-5` requires `V-3` through `V-5`. `V-2` through `V-5` passed on 2026-10-18; `V-1` remains an operator review before each pilot schema's first live run and `V-6` passed as part of the same run.

## Validation And Testing

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
| --- | --- | --- | --- | --- | --- |
| `V-1` | Provider-schema enablement review | For each pilot schema before its first live run, inspect the saved project's resolved `EntityConfig.keys`, transformed output, and another delivery when available. Record which tracked entity each ordered key identifies and confirm that repeated values mean the same source entity across deliveries. | `PH3-AC-4` | A schema with project-local or ambiguous keys remains disabled; no second key declaration is created. | Not run: no checked-in project has an assigned provider-schema pair. |
| `V-2` | Authorized and tampered requests in `backend/tests/api/test_sead_change_request_project_scope.py` (**NEW**) and scope behavior in `backend/tests/ingesters/test_sead_change_request_runtime.py` | `rtk uv run pytest backend/tests/api/test_sead_change_request_project_scope.py backend/tests/ingesters/test_sead_change_request_runtime.py -q` | `PH3-AC-1`, `PH3-AC-2`, `VM-4` | Project authorization and saved pair win over nested context and config; invalid pair yields no mocked SIMS, target-db, or writer call. | **Passed** (exit 0, 15 passed, 3 skipped for missing disposable SIMS variables). |
| `V-3` | Fixed provider row and target check in `backend/tests/services/test_project_data_provider_service.py` (**NEW**), `backend/tests/services/test_validation_service.py`, `backend/tests/ingesters/test_sead_change_request_ingester.py`, `backend/tests/ingesters/test_sead_change_request_submission_tables.py`, `backend/tests/ingesters/test_sead_change_request_runtime.py` | `rtk uv run pytest backend/tests/services/test_project_data_provider_service.py backend/tests/services/test_validation_service.py backend/tests/ingesters/test_sead_change_request_ingester.py backend/tests/ingesters/test_sead_change_request_submission_tables.py backend/tests/ingesters/test_sead_change_request_runtime.py -q` | `PH3-AC-3`, `VM-5` | Zero or multiple fixed rows and invalid ID/code fail project validation without database access; missing target adapter or no SEAD match fails before SIMS; one verified row yields one provider and one submission row. | **Passed** (exit 0, 124 passed, 3 skipped). |
| `V-4` | Business-key serializer, project save, and pre-SIMS checks in `tests/test_business_keys.py` (**NEW**), `backend/tests/services/test_project_service_boundary.py`, `backend/tests/services/project/test_entity_operations_boundary.py`, `backend/tests/ingesters/test_sead_change_request_identity_work.py`, `backend/tests/ingesters/test_sead_change_request_runtime.py`, `backend/tests/ingesters/test_sead_change_request_ingester.py` | `rtk uv run pytest tests/test_business_keys.py backend/tests/services/test_project_service_boundary.py backend/tests/services/project/test_entity_operations_boundary.py backend/tests/ingesters/test_sead_change_request_identity_work.py backend/tests/ingesters/test_sead_change_request_runtime.py backend/tests/ingesters/test_sead_change_request_ingester.py -q` | `PH3-AC-2`, `PH3-AC-4`, `VM-5` | Missing, blank, duplicate, managed-ID, or incompatible keys fail with zero SIMS calls; changed non-key fields preserve identity; stable repeats reuse it within a scope. | **Passed** (exit 0, 93 passed, 3 skipped). |
| `V-5` | Response/manifest parity in `backend/tests/api/test_ingesters.py`, `backend/tests/ingesters/test_sead_change_request_sql_builder.py`, `backend/tests/ingesters/test_sead_change_request_ingester.py`, and `frontend/src/components/ingester/__tests__/IngesterForm.test.ts` | `rtk uv run pytest backend/tests/api/test_ingesters.py backend/tests/ingesters/test_sead_change_request_sql_builder.py backend/tests/ingesters/test_sead_change_request_ingester.py -q`; `rtk pnpm --dir frontend test:run src/components/ingester/__tests__/IngesterForm.test.ts` | `PH3-AC-1`, `PH3-AC-3`, `VM-5` | Captured SIMS scope/run equals response, artifact, and manifest; existing bundle row and file contracts hold. | **Passed** (backend exit 0, 119 passed; frontend 3 passed). Only the `inline_insert` and `copy_csv` strategies were exercised; `inline_staging` parity was not asserted. |
| `V-6` | Regression and quality checks | `rtk uv run pytest backend/tests/ingesters backend/tests/api/test_ingesters.py -q`; `rtk make lint`; `rtk make frontend-lint` | Existing ingesters, API, and quality | Unrelated ingesters and both deploy strategies retain their behavior; lint passes. | **Passed**: ingester/API suite exit 0; `black`, `isort`, `ruff`, `pylint` on the changed modules, `generate_target_model_schema_reference.py --check`, and `check_doc_links.sh` all reported no findings; `make frontend-lint` exit 0. Full `backend/tests` and `tests` suites also passed. |

## Deliverables

Existing targets were verified during planning. New targets are marked `NEW`; if implementation finds that a target cannot support the stated contract, stop and record the conflict before changing the design.

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Trusted project gate and API test | `backend/app/api/v1/endpoints/ingesters.py`; `backend/app/models/ingester.py`; `backend/app/services/ingester_service.py`; `backend/tests/api/test_sead_change_request_project_scope.py` (**NEW**); `backend/tests/api/test_ingesters.py` | `T3.1`, `T3.5` | `V-2`, `V-5` pass. |
| Trusted scope runtime | `backend/app/services/ingester_runtime.py`; `backend/tests/ingesters/test_sead_change_request_runtime.py` | `T3.2`, `T3.4` | `V-2`, `V-4` pass. |
| Fixed provider ID and bundle rows | `backend/app/services/project_data_provider_service.py` (**NEW**); `backend/app/services/validation_service.py`; `backend/app/services/ingester_runtime.py::SeadChangeRequestTargetCollisionChecker.row_exists`; `ingesters/sead_change_request/ingester.py`; `ingesters/sead_change_request/submission_tables.py`; `backend/tests/services/test_project_data_provider_service.py` (**NEW**); `backend/tests/services/test_validation_service.py`; `backend/tests/ingesters/test_sead_change_request_ingester.py`; `backend/tests/ingesters/test_sead_change_request_submission_tables.py` | `T3.3` | `V-3` passes. |
| Declared key enforcement | `src/business_keys.py` (**NEW**); `backend/app/services/project_service.py`; `ingesters/sead_change_request/ingester.py`; `ingesters/sead_change_request/planning.py`; `ingesters/sead_change_request/preparation.py`; `backend/app/services/ingester_runtime.py`; `tests/test_business_keys.py` (**NEW**); `backend/tests/services/test_project_service_boundary.py`; `backend/tests/services/project/test_entity_operations_boundary.py`; `backend/tests/ingesters/test_sead_change_request_identity_work.py` | `T3.4` | `V-4` passes. |
| Scope/run output | `ingesters/sead_change_request/contracts.py`; `ingesters/sead_change_request/sql_builder.py`; `ingesters/sead_change_request/artifact_writer.py`; `backend/app/ingesters/protocol.py`; `frontend/src/types/ingester.ts`; `frontend/src/components/ingester/IngesterForm.vue`; `frontend/src/components/ingester/__tests__/IngesterForm.test.ts`; `backend/tests/ingesters/test_sead_change_request_sql_builder.py` | `T3.5` | `V-5` passes. |
| Updated user and ingester guidance | `ingesters/sead_change_request/README.md`; `docs/USER_GUIDE.md` | `T3.1`, `T3.5` | Instructions describe required authorized project, blocked keys, and emitted scope/run after implementation. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Authorize saved project | Complete | Phase 2 binding | `T3.1` implemented; `V-2` passed. |
| Area 2: Trusted scope and provider ID | Complete | Area 1 | `T3.2` and `T3.3` implemented; `V-2` and `V-3` passed. |
| Area 3: Declared keys | Complete | Area 1 | `T3.4` implemented; `V-4` passed. `V-1` review still precedes each schema's first live run. |
| Area 4: Scope/run output | Complete | Areas 1–3 | `T3.5` implemented; `V-5` passed. |

## Definition Of Done

* [ ] The fixed provider row and resolved keys come only from the authorized saved project; each enabled schema has passed `V-1` review before its first live run.
* [x] `PH3-AC-1` through `PH3-AC-4` have implementation and passing validation results; `VM-4` and `VM-5` are recorded.
* [x] All work areas and final deliverables are complete, including response, manifest, tests, and user guidance.
* [x] No invalid saved pair or invalid declared key causes a SIMS request or bundle write; an invalid pair or key causes no target-database access.
* [x] Existing lookup-only `data_provider`, one-provider-row/one-submission-row, and unrelated-ingester behavior pass regression checks.
* [x] Required quality checks pass; deviations and follow-up work are documented; no decision affecting correctness or validation remains open.

## Risks And Open Questions

1. **Cross-delivery key meaning:** a validator can reject duplicates in one delivery and incompatible declarations across bound projects, but cannot prove that two past deliveries used one key for the same real-world record. Complete `V-1` review before enabling each pilot schema. A repeated value is the same identity by contract.
2. **Manual provider ID:** an operator can enter the wrong SEAD ID. The pre-SIMS read-only ID/code check rejects a mismatch; a missing target connection blocks the run.
3. **Cutover:** do not switch existing projects to the new scope until Phase 4 decides whether their old `sead-change-request:*` identities are migrated or abandoned and assigns approved pairs to those projects.
4. **Remaining operator action:** `V-1` is not a code check. No checked-in project has an assigned provider-schema pair, so the per-schema key review still happens before that schema's first live run. `V-5` asserted parity for `inline_insert` and `copy_csv`; `inline_staging` carries the same metadata fields but has no dedicated parity assertion yet.
