# Direct Target-Id Foreign Keys — Phase 3 Task Plan

## Phase Summary

**Goal:** Deliver the resolved direct-ID declaration through saved-project validation and ingestion, verify real target-database checks, and document the result.

**Readiness:** Validated. [Phase 3](DIRECT_TARGET_ID_FOREIGN_KEYS_PHASE_PLAN.md#phase-3-saved-project-delivery-and-end-to-end-verification) is marked ready. The service, ingester, test entry points, schema generator, and disposable PostgreSQL test convention are verified. The database-dependent milestone requires a non-skipped run during implementation; no disposable database is configured in this planning environment.

**Sources:** [Proposal](DIRECT_TARGET_ID_FOREIGN_KEYS.md) (`P-AC-1`, `P-AC-3`, `P-AC-5`, `P-AC-8`, `P-AC-9`) and [phase plan](DIRECT_TARGET_ID_FOREIGN_KEYS_PHASE_PLAN.md) (`PH3-AC-1`–`PH3-AC-5`, `VM-3`). [Phase 1](DIRECT_TARGET_ID_FOREIGN_KEYS_PHASE_1_TASK_PLAN.md) and [Phase 2](DIRECT_TARGET_ID_FOREIGN_KEYS_PHASE_2_TASK_PLAN.md) have recorded implementation and focused validation results.

**Fixed rules:** Core links continue to carry local `system_id` values. The target model defines the FK and its requirements. The saved-project caller derives the declaration from the resolved project, never from request input. An omitted map keeps the existing path. Direct IDs enter change-request packages only after mandatory target lookup; no supplied ID becomes a reconciliation sidecar link. The default scaffold remains unchanged.

**Acceptance criteria**

1. [x] `PH3-AC-1` (`P-AC-1`): Saved-project callers pass the resolved map; absence retains the `system_id` path.
2. [x] `PH3-AC-2` (`P-AC-5`): Saved validation and ingestion call the table methods; disposable PostgreSQL accepts an existing ID and rejects absent or unverifiable IDs before a package is accepted.
3. [x] `PH3-AC-3` (`P-AC-8`): Existing `system_id` results and diagnostics match the recorded baseline, separating pre-existing failures from new ones.
4. [x] `PH3-AC-4` (`P-AC-9`): The configuration guide, root and Core agent guides, and API/editor descriptions state the delivered declaration, default, and Core/package distinction.
5. [x] `PH3-AC-5` (`P-AC-3`): A representative project records its removable optional-helper count and keeps globally required entities.

## Repository Findings

**Repository basis:** Branch `direct-target-id-foreign-keys`, commit `bf7a6b88`, 2026-10-23. `git status --short` was clean before planning; no uncommitted source changes were considered. Graphify located the project service and ingester, then the files below were checked directly. The phase plan's “Current Position” describes pre-phase behavior; Phase 1 and Phase 2 code is present in this checkout.

| Verified source | Current behavior | Planning consequence |
| --- | --- | --- |
| `backend/app/services/project_ingester_service.py::ProjectIngesterService._load_validated_project`, `_create_trusted_config`, `validate_project_tables`, `ingest_project_tables` | `ProjectMapper.to_core()` resolves the project. Both service methods normalize and call `validate_tables()` or `ingest_tables(validate_first=True)`. Config `extra` has target model and trusted context, but no FK value-source map. | Derive the map once from `core_project.entities` and put it in `extra` before runtime/database injection. Keep the existing authorization and table calls. |
| `src/model.py::TableConfig.foreign_key_value_sources`; `ingesters/sead_change_request/input_resolution.py::_resolve_foreign_key_value_sources` | Core exposes each entity's resolved map; the ingester accepts a per-entity map in `IngesterConfig.extra` and defaults to `{}`. | Copy declared entries, including explicit `system_id`; do not infer mode from a missing table or mutate project data. |
| `src/target_model/conformance.py::ForeignKeyValueSourceConformanceValidator`; `backend/app/validators/target_model_validator.py::TargetModelValidator` | Conformance detects direct-mode link conflicts and missing output columns. The project-ingester service currently runs structural specification checks, not target-model conformance. | For projects declaring `public_id`, reject direct-mode conformance errors before normalization without imposing all conformance results on legacy service calls. Preserve codes in returned error text. |
| `backend/app/api/v1/endpoints/ingesters.py::validate_project_ingester`, `ingest_project_ingester`; `backend/app/models/ingester.py::ProjectIngesterRequest` | The two `/from-project/` routes delegate to the service. Request fields are strict and contain no FK map. File routes for this ingester are retired. | Test both project routes and reject caller attempts to override the saved map; no endpoint or request-field addition is needed. |
| `backend/app/services/ingester_runtime.py::SeadChangeRequestTargetCollisionChecker`; `ingesters/sead_change_request/ingester.py::SeadChangeRequestIngester` | The checker has `target_id_exists()` and `target_id_column_type()`. Both table methods already check packaged direct values; successful ingestion writes a manifest entry for used direct FKs. | Reuse this checker and ingester for the database test; do not add a second lookup path. |
| `backend/tests/services/test_project_ingester_service.py`, `backend/tests/api/test_project_ingester_routes.py` | Existing fake and real-ingester tests cover authorization, normalization, table calls, and bundle creation. The common mock replaces `ProjectMapper.to_core()`, so it cannot alone prove saved declaration delivery. | Add a test using the real mapper on a saved `Project`, plus focused service and route assertions. |
| `backend/tests/ingesters/test_sead_change_request_inline_staging.py`, `test_sead_change_request_submission_sims_integration.py` | Disposable tests use `SEAD_DISPOSABLE_POSTGRES_*`, require a loopback host, and create isolated schema objects. | Follow that guard and cleanup pattern for a direct-FK PostgreSQL test. A skip does not satisfy `VM-3`. |
| `docs/CONFIGURATION_GUIDE.md`; `AGENTS.md`; `src/AGENTS.md`; `backend/app/models/entity.py::Entity.foreign_key_value_sources`; `frontend/src/schemas/entitySchema.json` | The field and generated enum already exist; guides still state every FK value is local and the API description does not explain the package exception. | Update the user/agent descriptions and regenerate the schema from the Pydantic model. |
| `tests/test_data/projects/arbodat/shapeshifter.yml`; `resources/target_models/sead_standard_model.yml` | ArboDat's `location_type` and `method_group` project entities point at optional target entities. `location` does not declare a `location_type_id` output; the helper's fixed target IDs are null. The fixed `method` rows carry null `method_group_id` values. Neither is a confirmed direct-ID removal from the fixture alone. | Use ArboDat for a measured pilot. Count a helper only after verifying non-null source target IDs and that no other project use or global target requirement needs it; report zero if none qualifies. Do not treat the target-model candidate inventory as a project count. |

## Scope

**In scope:** Saved-project map extraction and direct-mode preflight; service and route tests; disposable PostgreSQL validation/ingestion and manifest checks; default-path regression comparison; configuration, API/schema, and agent guidance; one ArboDat pilot count recorded in this plan's execution record.

**Out of scope:** Core FK algorithm, target-model syntax, standalone ingester behavior already delivered in Phase 2, non-integer or `via` FKs, shared-target database writes, scaffold changes, and conversion of the ArboDat fixture itself. The pilot is a measurement, not a migration of that project.

## Work Breakdown

### Area 1: Pass the saved project's declaration to the ingester

**Objective:** Both authorized saved-project calls use the resolved map and reject an invalid direct declaration before normalizing rows.

**Affected code:** `backend/app/services/project_ingester_service.py::ProjectIngesterService`; `backend/tests/services/test_project_ingester_service.py`; `backend/tests/api/test_project_ingester_routes.py`.

**Dependencies:** Phases 1 and 2.

**Tasks:**

* [x] `T1.1` **Pass the resolved map through service config.**
  * **Target:** `backend/app/services/project_ingester_service.py::ProjectIngesterService._create_trusted_config`; `backend/tests/services/test_project_ingester_service.py`.
  * **Current → required:** `extra` omits `foreign_key_value_sources` → it contains a copied per-entity map from `core_project.entities` for `sead_change_request` when a declaration is present.
  * **Implementation:** Read the resolved entity configurations after `ProjectMapper.to_core()`. Preserve explicit `system_id` and `public_id` entries; omit the key for projects with no declarations. Add the map before runtime/database injection. Do not read it from `ProjectIngesterRequest` or raw unresolved project YAML.
  * **Constraints:** Keep trusted provider context, backend-owned connection settings, normalization flags, and existing table-method calls unchanged. Do not create a Core FK link for the map.
  * **Validation:** `V-1`: use a saved `Project` and real `ProjectMapper.to_core()` to assert the map reaches both method configs; assert an absent declaration keeps the prior config shape and results. Check that caller input cannot add a map.
* [x] `T1.2` **Fail saved direct-mode calls on declaration conflicts.**
  * **Target:** `backend/app/services/project_ingester_service.py::ProjectIngesterService._create_trusted_config` and its error handling; `backend/tests/services/test_project_ingester_service.py`.
  * **Current → required:** The service does structural checks only → a saved `public_id` declaration with a Core link or missing target output is rejected before normalization and database work.
  * **Implementation:** Apply the existing direct-mode conformance validator to the resolved project and parsed target model only when a `public_id` entry exists. Return direct-mode issue code, entity, field/column, and message through the existing failed validation/ingestion response paths. Keep normal target-model validation available through its existing endpoint; this service preflight checks only the declared direct relationship.
  * **Constraints:** Do not make legacy projects fail because of unrelated target-model conformance issues or change the request/response models. Treat an invalid saved declaration as an error even if a project disabled the general conformance rule.
  * **Validation:** `V-1`: conflict and missing-column cases fail before `normalize_project`; valid direct and omitted maps continue. Assert failure leaves no output bundle.
* [x] `T1.3` **Prove the complete saved-project call path.**
  * **Target:** `backend/tests/services/test_project_ingester_service.py`; `backend/tests/api/test_project_ingester_routes.py`.
  * **Current → required:** Existing route tests prove service delegation, but not that a saved direct map reaches a real ingester → validation and ingestion run through the table methods using the saved map.
  * **Implementation:** Add a small saved project with an inline target model and a direct `location -> location_type` FK. Mock normalization, SIMS, and the checker at their existing injection points; use the real mapper and ingester. Assert accepted ID reaches the deploy artifact and manifest; absent/nonexistent ID fails through both service responses before bundle acceptance. Extend the authorized route test to prove project-derived data wins over caller input.
  * **Constraints:** Keep route authorization and strict request fields. No workbook input or direct call to retired file methods.
  * **Validation:** `V-1`, `V-2`: assert `validate_tables()`/`ingest_tables()` are reached, error context is retained, accepted manifest names the FK, and failed ingestion creates no bundle.

**Completion evidence:** A saved project supplies the same map to both table methods; direct-mode declaration errors stop before row processing; no-map calls retain their prior config and behavior.

### Area 2: Verify target IDs against disposable PostgreSQL

**Objective:** A real read-only target lookup accepts an existing integer ID and rejects bad or unavailable IDs before a change-request bundle is accepted.

**Affected code:** `backend/tests/ingesters/test_sead_change_request_direct_fk_postgres.py` (`NEW`), using `backend/app/services/ingester_runtime.py::SeadChangeRequestTargetCollisionChecker` and `ingesters/sead_change_request/ingester.py::SeadChangeRequestIngester` without modifying them unless the test exposes a Phase 2 defect.

**Dependencies:** Area 1 for saved-project coverage; Phase 2 ingester behavior.

**Tasks:**

* [x] `T2.1` **Add the real database acceptance and failure test.**
  * **Target:** `backend/tests/ingesters/test_sead_change_request_direct_fk_postgres.py` (`NEW`).
  * **Current → required:** Phase 2 checks use fake target lookups → an isolated PostgreSQL schema proves the actual column-type and row-existence queries and package result.
  * **Implementation:** Reuse the verified `SEAD_DISPOSABLE_POSTGRES_*` loopback guard. Create a unique schema with an integer `location_type_id` target table and a `location` target table; seed one existing target ID and clean the schema in `finally`. Configure a direct `location -> location_type` map, existing identity-assignment test inputs, and the real checker. Call `validate_tables()` and `ingest_tables()` for the seeded ID and an absent integer ID. Read the emitted `manifest.json` and payload for the accepted case; assert no emitted bundle for the rejected case. Make a lookup-unavailable case by removing access to the isolated target relation or using a checker that raises at lookup; assert a failure result, not a fallback to local IDs.
  * **Constraints:** No shared schema or production database writes; validate the host is loopback before connecting. The test must not require a live SIMS service. A skipped database test is incomplete for `VM-3`.
  * **Validation:** `V-3`: non-skipped PostgreSQL run proves the existing ID, absent ID, lookup failure, integer type, manifest source/target/column, and no failed bundle.

**Completion evidence:** The PostgreSQL test passes without skips against a disposable database, and the accepted package preserves the seeded ID.

### Area 3: Align configuration and agent guidance

**Objective:** Users and coding agents can distinguish local Core links from supplied target IDs in a change-request package.

**Affected code and documentation:** `docs/CONFIGURATION_GUIDE.md`; `AGENTS.md`; `src/AGENTS.md`; `backend/app/models/entity.py::Entity.foreign_key_value_sources`; generated `frontend/src/schemas/entitySchema.json`; `tests/scripts/test_generate_schemas.py`; `frontend/src/composables/__tests__/useMonacoYamlIntelligence.test.ts`.

**Dependencies:** Area 1's saved-project behavior.

**Tasks:**

* [x] `T3.1` **Document the project setting and its limits.**
  * **Target:** `docs/CONFIGURATION_GUIDE.md`; `AGENTS.md`; `src/AGENTS.md`.
  * **Current → required:** These guides describe all FK values as local → they explain that Core project links stay local while `foreign_key_value_sources.<target>: public_id` supplies an existing target ID to the change-request package.
  * **Implementation:** Place the field beside entity `foreign_keys` in the guide, give a `location -> location_type` example with the required target-model reference and output `location_type_id`, define the omitted/`system_id` default, eligibility and conflict rules, mandatory integer target lookup, packaged-row null behavior, offline failure, and manifest entry. Qualify the guide's existing “never external IDs” statements to mean Core links. Add the same Core/package distinction to both agent guides. Keep the pre-existing external-ID-as-business-key pattern as a separate valid local-link option.
  * **Constraints:** Do not imply a direct declaration creates a Core dependency or waives globally required target entities. Do not describe the field as a shared target-model setting.
  * **Validation:** `V-4`: inspect example and rules against `Entity`, `TableConfig`, conformance, and ingester tests; run documentation link check.
* [x] `T3.2` **Synchronize API and editor descriptions.**
  * **Target:** `backend/app/models/entity.py::Entity.foreign_key_value_sources`; `frontend/src/schemas/entitySchema.json` (generated); `tests/scripts/test_generate_schemas.py`; `frontend/src/composables/__tests__/useMonacoYamlIntelligence.test.ts`.
  * **Current → required:** The field enum exists but its description does not state the direct package exception → API/OpenAPI and Monaco describe both modes and the default accurately.
  * **Implementation:** Clarify the Pydantic field description, run the verified `make generate-schemas` target, and assert the generated enum/default/description and Monaco registration. Do not hand-edit schema JSON.
  * **Validation:** `V-5`: schema generation check and focused generator/editor tests pass.

**Completion evidence:** Guide, agent rules, API description, and generated editor schema agree about which values are local and which can be direct target IDs.

### Area 4: Compare regressions and measure one project

**Objective:** Preserve default-path behavior and record a project-specific optional-helper count.

**Affected tests and record:** `tests/model/test_target_model_conformance.py`; `tests/target_model/`; `backend/tests/ingesters/`; `backend/tests/services/test_project_ingester_service.py`; this plan's execution record after implementation.

**Dependencies:** Areas 1–3.

**Tasks:**

* [x] `T4.1` **Compare default projects with the baseline.**
  * **Target:** Existing `tests/model/test_target_model_conformance.py::test_core_conformance_reports_known_gaps_for_full_arbodat_project`, `test_core_conformance_current_corpus_issue_families_are_stable`; `tests/target_model/`; `backend/tests/ingesters/`; `backend/tests/services/test_project_ingester_service.py`.
  * **Current → required:** The focused baseline passes, including the two named standard-model tests → omitted and explicit `system_id` declarations keep the same results and direct-mode additions introduce no new default-path issue family.
  * **Implementation:** Add or extend no-map and explicit-`system_id` saved-service assertions where needed. Run the same suites after change and compare any failures with this plan's baseline before treating them as regressions.
  * **Validation:** `V-1`, `V-6`: named corpus tests and ingester/service regression suites pass with the recorded skip policy.
* [x] `T4.2` **Measure the ArboDat optional-helper count.**
  * **Target:** `tests/test_data/projects/arbodat/shapeshifter.yml` and `resources/target_models/sead_standard_model.yml` (read-only pilot inputs); the execution record in this task plan (result only).
  * **Current → required:** The candidate inventory is model-wide and the checked-in ArboDat fixture does not establish usable direct target IDs → record how many project entities can actually be removed for this project, including zero.
  * **Implementation:** Inventory referenced project entities whose target-model entity has `required: false`; for each, verify that the source produces the target `public_id` column with non-null IDs already present in the target database, that the entity has no independent output or other project consumer, and that removing its Core link leaves conformance valid. Use an in-memory project variant; never edit the ArboDat fixture or relabel local `system_id` values as target IDs. Record candidate names, accepted/rejected reasons, before/after helper counts, retained globally required entities, and the final removal count. If the fixture's null `location_type_id` and `method_group_id` values remain the only candidates, record a zero result and the data limitation explicitly.
  * **Validation:** `V-7`: review the inventory against the saved project and target model, run conformance on the in-memory variant where a candidate qualifies, and check each counted ID against the disposable target database. A zero count is a valid measured result when no project-supplied IDs qualify.

**Completion evidence:** Default-path suites match baseline and the execution record names the representative project, qualifying candidates, exclusions, and final helper count.

## Acceptance-Criteria Coverage

| Criterion and source | Task IDs | Validation IDs | Expected result |
| --- | --- | --- | --- |
| `PH3-AC-1` (`P-AC-1`) | `T1.1`, `T1.2`, `T1.3` | `V-1`, `V-2` | Saved map reaches both table methods; absence keeps the local-ID path. |
| `PH3-AC-2` (`P-AC-5`) | `T1.3`, `T2.1` | `V-2`, `V-3` | Service and route calls use table methods; PostgreSQL accepts one ID and rejects absent/unverifiable IDs before bundle acceptance. |
| `PH3-AC-3` (`P-AC-8`) | `T1.1`, `T4.1` | `V-1`, `V-6` | Default results and diagnostic families match baseline. |
| `PH3-AC-4` (`P-AC-9`) | `T3.1`, `T3.2` | `V-4`, `V-5` | Guide, agent rules, API model, and generated editor schema agree. |
| `PH3-AC-5` (`P-AC-3`) | `T4.2` | `V-7` | ArboDat helper count and globally required exclusions are recorded. |

## Validation And Testing

`VM-3` requires passing `V-1`–`V-7`, including a **non-skipped** `V-3`; a skipped disposable database check cannot close the phase. The planning baseline command covering service, routes, Core conformance, target-model, and ingester tests exited 0 on this checkout. The two named ArboDat/corpus conformance tests passed. At planning time, existing disposable-database and SIMS-dependent tests skipped because their services were not configured. Execution results are recorded below.

| ID | Check and target | Command or executable method | Covers | Expected result | Planning baseline |
| --- | --- | --- | --- | --- | --- |
| `V-1` | Saved map/preflight and default parity: `backend/tests/services/test_project_ingester_service.py` | `rtk uv run pytest backend/tests/services/test_project_ingester_service.py -q` | `PH3-AC-1`, `PH3-AC-3` | New real-mapper direct and no-map cases pass; invalid declarations fail before normalization; existing service cases pass. | Pass: existing file passed in combined baseline. New cases not present. |
| `V-2` | Authorized routes and real-ingester service flow: `backend/tests/api/test_project_ingester_routes.py`, `backend/tests/services/test_project_ingester_service.py` | `rtk uv run pytest backend/tests/api/test_project_ingester_routes.py backend/tests/services/test_project_ingester_service.py -q` | `PH3-AC-1`, `PH3-AC-2` | Both routes retain authorization and strict request behavior; accepted/failing saved direct cases reach table methods with contextual results. | Pass: both existing files passed in combined baseline. New cases not present. |
| `V-3` | Real direct-FK lookup: `backend/tests/ingesters/test_sead_change_request_direct_fk_postgres.py` (`NEW`) | Set loopback `SEAD_DISPOSABLE_POSTGRES_HOST`, `_PORT`, `_DB`, `_USER` and optional `_PASSWORD`; run `rtk uv run pytest backend/tests/ingesters/test_sead_change_request_direct_fk_postgres.py -q -m integration` | `PH3-AC-2`, `VM-3` | Seeded ID passes both table methods and appears unchanged in manifest/payload; absent or unavailable ID fails and emits no bundle. Zero skips. | Not run: new file absent and disposable PostgreSQL variables unset. |
| `V-4` | Guide/agent review: `docs/CONFIGURATION_GUIDE.md`, `AGENTS.md`, `src/AGENTS.md` | Review the direct-ID example against target-model and ingester rules; `rtk make check-doc-links` | `PH3-AC-4` | All three files state the Core/package distinction and default; links resolve. | Pass: current link check. Content update pending. |
| `V-5` | API/editor schema: `backend/app/models/entity.py`, `frontend/src/schemas/entitySchema.json`, `tests/scripts/test_generate_schemas.py`, `frontend/src/composables/__tests__/useMonacoYamlIntelligence.test.ts` | `rtk make check-schemas`; `rtk uv run pytest tests/scripts/test_generate_schemas.py -q`; from `frontend/`, `pnpm test:run src/composables/__tests__/useMonacoYamlIntelligence.test.ts` | `PH3-AC-4` | Generated enum/default/description match the API field and Monaco registration. | Pass: schema sync before description change. Focused generator/editor tests not rerun for this plan. |
| `V-6` | Core and ingester regression: `tests/target_model/`, `tests/model/test_target_model_conformance.py`, `backend/tests/ingesters/` | `rtk uv run pytest tests/target_model tests/model/test_target_model_conformance.py backend/tests/ingesters -q` | `PH3-AC-3` | Existing default-path tests pass; compare any failures with the named baseline cases; optional external integration skips remain identified. | Pass: these suites passed in combined baseline; external integration cases skipped. |
| `V-7` | ArboDat pilot: `tests/test_data/projects/arbodat/shapeshifter.yml`, standard target model, and this plan's execution record | Read-only inventory, in-memory conformance comparison for any qualifying removal, database confirmation of counted IDs, and record the before/after count | `PH3-AC-5` | Count and exclusions are explicit; globally required target entities remain. | Not run: pilot requires source-value and target-ID confirmation. |
| `V-8` | Quality and whitespace | `rtk make lint`; `git diff --check` | Changed implementation and docs | Lint and whitespace pass; isolate unrelated pre-existing failures if any. | Not run during read-only planning; `make lint` invokes `tidy`. |

Run `make generate-schemas` before `V-5` after editing the Pydantic description. The exact combined baseline command was `rtk uv run pytest backend/tests/services/test_project_ingester_service.py backend/tests/api/test_project_ingester_routes.py tests/model/test_target_model_conformance.py tests/target_model backend/tests/ingesters -q`.

## Deliverables

| Deliverable | Exact target | Task IDs | Completion result |
| --- | --- | --- | --- |
| Saved-project config and direct preflight | `backend/app/services/project_ingester_service.py::ProjectIngesterService._create_trusted_config` | `T1.1`, `T1.2` | Resolved map is copied; invalid direct declaration stops before normalization. |
| Saved-project and route tests | `backend/tests/services/test_project_ingester_service.py`; `backend/tests/api/test_project_ingester_routes.py` | `T1.1`–`T1.3`, `T4.1` | Both authorized table calls and default parity pass. |
| Disposable PostgreSQL test **NEW** | `backend/tests/ingesters/test_sead_change_request_direct_fk_postgres.py` | `T2.1` | Existing, absent, and unavailable ID cases pass without skips. |
| Configuration and agent guidance | `docs/CONFIGURATION_GUIDE.md`; `AGENTS.md`; `src/AGENTS.md` | `T3.1` | Core local links and direct package values are clearly distinguished. |
| API and generated editor descriptions | `backend/app/models/entity.py::Entity.foreign_key_value_sources`; `frontend/src/schemas/entitySchema.json`; `tests/scripts/test_generate_schemas.py`; `frontend/src/composables/__tests__/useMonacoYamlIntelligence.test.ts` | `T3.2` | Generated schema is synchronized and editor test passes. |
| Pilot result | This plan's execution record; ArboDat fixture and standard target model remain read-only | `T4.2` | Named candidate decisions and before/after optional-helper count are recorded. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: saved-project handoff | Done | Phases 1–2 | Resolved map passes through trusted config; direct declaration errors fail before normalization. |
| Area 2: PostgreSQL check | Done | Area 1, disposable database | `V-3` passed against loopback disposable PostgreSQL with no skips. |
| Area 3: guidance and schema | Done | Area 1 | Guidance, API description, and generated schema agree; checks passed. |
| Area 4: parity and pilot | Done | Areas 1–3 | Regression suites passed; ArboDat pilot measured zero removable helpers. |

## Execution Record

**Completed:** 2026-10-23. The saved-project service now derives the per-entity map from the resolved Core project. The map is sent only to `sead_change_request`; explicit `system_id` entries are retained, and no declaration omits the config key. The existing direct-FK conformance validator rejects conflicts and missing output columns before normalization. Caller-supplied map fields remain rejected by strict route request validation.

| Validation | Result |
| --- | --- |
| `V-1` and `V-2` | Passed. `rtk uv run pytest backend/tests/api/test_project_ingester_routes.py backend/tests/services/test_project_ingester_service.py -q` passed after adding real-mapper saved-project tests for accepted and absent IDs, explicit `system_id`, omitted declarations, preflight failures, and caller-field rejection. Both saved-project methods use the table-based ingester flow. |
| `V-3` | Passed without skips. The new integration test ran against a temporary PostgreSQL 17 Podman container bound to `127.0.0.1:55433`, with a random disposable user/password and isolated schema. ID `42` passed type/existence checks and appeared in the accepted deploy artifact and manifest; absent ID `99999` and an unavailable lookup failed through validation and ingestion with no bundle. The container and schema were removed after the run. |
| `V-4` and `V-5` | Passed. The guide and both agent files describe the Core/package distinction; `rtk make check-doc-links`, `rtk make check-schemas`, five schema-generator tests, and the focused Monaco editor test passed. |
| `V-6` | Passed. The target-model, conformance, and ingester suites passed, including both named corpus tests. Eighteen optional integration cases skipped in this suite because their disposable PostgreSQL or SIMS settings were not configured; the new direct-FK PostgreSQL case was separately run without a skip under `V-3`. |
| `V-7` | Passed. The ArboDat project has two helper-removal candidates in the focused inventory: `location_type` and `method_group`. `location` has no `location_type_id` output and the helper's fixed target IDs are null; `method` rows have null `method_group_id` values. Neither supplies a target ID to verify, so both helpers remain: before `2`, after `2`, removed `0`. The `dimension.method_group_id` value `17` was not counted because it is not a direct declaration and was not checked against the target database; `ecocode_group.ecocode_system_id=1` remains a Core `system_id`, not a target ID. All 13 globally required target entities remain present. No qualifying removal existed for an in-memory conformance variant or target-database check. |
| `V-8` | Passed. `rtk make lint` and `git diff --check` passed. |

**Final scope result:** All eight tasks and all five phase acceptance criteria are complete. The disposable PostgreSQL test used an isolated loopback container; the unrelated `sead-sims-candidate-verification` container was left running.

## Definition Of Done

* [x] `PH3-AC-1`–`PH3-AC-5` have completed task and validation results recorded above.
* [x] Both saved-project methods use the resolved map; unauthorized or caller-supplied changes cannot override it.
* [x] A real disposable PostgreSQL test passes without skips for accepted, absent, and unavailable target IDs; accepted bundle and manifest preserve the direct ID.
* [x] No-map and explicit `system_id` projects match the passing baseline, including both named standard-model conformance tests.
* [x] Configuration guide, agent rules, API description, and generated editor schema agree; scaffold remains local-ID based.
* [x] The ArboDat pilot records its candidate list, excluded/global requirements, and measured removable-helper count, including zero if no source IDs qualify.
* [x] `V-1`–`V-8` pass, or an unrelated pre-existing quality failure is isolated and recorded; any deviation or follow-up is documented.
* [x] No unresolved question affects implementation, correctness, or validation.

If implementation finds that a verified service contract, target model, project value, or test result differs from this plan, stop and report the conflicting source and result before changing the design or scope.
