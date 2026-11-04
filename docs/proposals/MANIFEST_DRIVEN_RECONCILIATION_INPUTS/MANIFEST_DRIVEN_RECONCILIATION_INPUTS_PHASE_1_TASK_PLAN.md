# Manifest-Driven Reconciliation Inputs — Phase 1 Task Plan

## Phase Summary

**Phase:** 1 — Publish a Reconciliation-Specific Manifest Contract. **Readiness:** Validated for implementation; the database-backed milestone remains unverified until the deployment checks below pass.

**Goal:** Publish implemented reconciliation types and accurate property metadata from SEAD Authority Service without replacing its OpenRefine manifest. Verify the two pilot matchers against the database as the service role.

**Sources:** [Approved proposal](MANIFEST_DRIVEN_RECONCILIATION_INPUTS.md) and [Phase 1 of the phase plan](MANIFEST_DRIVEN_RECONCILIATION_INPUTS_PHASE_PLAN.md#phase-1-publish-a-reconciliation-specific-manifest-contract). This phase depends on the proposal's additive contract; it does not depend on the Shape Shifter editor or the pilots' local business keys. `VM-1` maps to `V-1` and `V-2`; `VM-2` maps to `V-3` and `V-4`.

**Acceptance criteria**

1. [ ] `PH1-AC-1` (from `P-AC-2`): Every published supported ID occurs exactly once in `defaultTypes`; the OpenRefine fields remain available and property declarations identify the types they serve.
2. [ ] `PH1-AC-2` (from `P-AC-3`): A supported type with zero properties is valid, while missing or malformed required metadata is distinguishable and rejected.
3. [ ] `PH1-AC-3` (from `P-AC-5`): With deployed schema read access, real `feature_type` and `location` requests return candidates.

## Repository Findings

**Repository basis:** Planning date 2026-11-04. Shape Shifter `dev` at `722c4006`; Authority Service `dev` at `4fb9b22`. The Shape Shifter proposal and phase plan are untracked; Authority Service grant sources and generated deployment SQL are committed in `4fb9b22`. Granting read access to `PUBLIC` is approved, but deployment and service-role access remain unverified. Relative paths below labeled **Authority Service** refer to the sibling `sead_authority_service` repository; all other paths refer to Shape Shifter.

| Evidence | Finding | Planning implication |
| --- | --- | --- |
| Authority Service `src/metadata.py::get_reconciliation_metadata`, `_get_default_types`, `_compile_property_settings` | The GET metadata is built from registered strategies. It emits `defaultTypes` and `extend.property_settings`, but no `reconciliation` section; properties are merged by name and tagged with `entity_types`. | Add the supported-type declaration without changing the existing OpenRefine keys; validate the declared type/property relationship. |
| Authority Service `src/api/router.py::meta`, `src/api/model.py::ReconServiceManifest`, `TypeRef`, `ExtendDescriptor`, `PropertySetting` | GET `/reconcile` passes the metadata through a Pydantic response model. `defaultTypes` currently defaults to `[]` and `extend` is optional; the model has no supported-type contract. | Update both the builder and serialized response shape; make missing required reconciliation metadata an explicit error rather than an omitted field. |
| Authority Service `src/strategies/strategy.py::Strategies`, `src/reconcile.py::reconcile_queries`, `src/strategies/taxon.py::TaxonReconciliationStrategy.find_candidates` | Registration alone does not establish support: the registered `taxon` strategy always returns `[]`. The request path selects strategies from the same registry. | Keep `taxon` in `defaultTypes` for compatibility, but exclude it from the explicit supported set. Audit other registered implementations before publishing their IDs. |
| Authority Service `src/resources/feature_type.yml`, `src/resources/location.yml`, `src/resources/site.yml`; `src/strategies/strategy.py::ReconciliationStrategy._find_candidates`, `src/strategies/location.py`, `src/strategies/site.py` | `feature_type` declares `properties: []`; `location` declares `place_name`; `site` declares five properties. The generic `location` finder searches by query label and ignores submitted `place_name` constraints when filtering or ranking candidates. | Test zero-property and exact type membership; do not claim that mapping `place_name` constrains location matches. Keep `site` as the existing OpenRefine-property regression. |
| Authority Service `schema/create_schema.sh::generate_deploy_sql`, `schema/sql/authority.sql`, `schema/sql/grants.sql`, `schema/__deploy__.sql` (generated) | The schema is dropped/recreated; committed grant SQL is appended after objects in the generator. Read access for `PUBLIC` is approved but has not been verified as deployed. | Verify generated grant order and read access using the *actual service database role*. Never deploy this destructive schema script to shared staging as a smoke test. |
| Authority Service `src/api/candidate_verification.py::get_reconciliation_readiness`; `tests/api/test_readiness.py` | The readiness endpoint is restricted to `site`; it does not check `feature_type` or `location`, and an empty successful query would not prove candidates exist. | Use real POST `/reconcile` requests for both pilot types instead of the readiness endpoint or a healthy manifest. |
| Authority Service `docs/DEVELOPMENT.md` (“Disposable database for integration tests”), `scripts/verify_sims_identity_candidates.sh`, `tests/integration/test_reconcile_integration.py::TestManualDatabaseTesting` | The documented helper prepares a loopback-only Podman database; the existing real-database tests are explicitly skipped and cover `site`, not the pilots. | Use the documented disposable setup plus explicit pilot requests; do not count mocked or skipped tests as live verification. |

## Scope

**In scope:** The Authority Service GET `/reconcile` response model and builder; an auditable set of implemented types; property/type contract checks; focused model, metadata, and route tests; verification of the committed schema-read grants; read-only pilot candidate requests against a disposable database and then staging. Record deployment blockers explicitly.

**Out of scope:** Shape Shifter editor and matching eligibility changes (Phase 2); local keys, operator decisions, export, and normalization (Phases 3–4); `taxon` matcher implementation; SIMS adoption, change-request import, materialization, and modifications to shared staging data. Do not edit the Shape Shifter proposal or phase plan for this phase.

## Work Breakdown

### Area 1: Publish a validated, additive manifest

**Objective:** GET `/reconcile` includes `reconciliation.supportedTypes` while continuing to expose the same OpenRefine keys.

**Affected code:** Authority Service `src/metadata.py::get_reconciliation_metadata`, `_get_default_types`, `_compile_property_settings`; `src/api/model.py::ReconServiceManifest`, `ExtendDescriptor`, `PropertySetting`; `src/api/router.py::meta`. The registered strategies and YAML resources listed in Repository Findings supply the implemented-type and property audit.

**Dependencies:** Approved proposal; no earlier area.

**Tasks:**

* [x] `T1.1` **Change:** Publish an explicit, reviewed list of implemented reconciliation type IDs, separate from the registry-derived OpenRefine list.
  * **Target:** Authority Service `src/metadata.py::get_reconciliation_metadata`, `_get_default_types`; `src/strategies/strategy.py::Strategies` and the registered implementations for the eligibility audit.
  * **Current → required:** All registered IDs appear in `defaultTypes` with no indication of actual matching support → `reconciliation.supportedTypes` contains unique implemented IDs, including the verified `site`, `feature_type`, and `location` implementations and excluding placeholder `taxon`.
  * **Implementation:** Audit each registered strategy's candidate path and resource SQL/external-provider requirements. Encode a deliberate supported-ID declaration in the manifest builder, verify each ID against the registry-generated `defaultTypes`, and keep `defaultTypes` intact. Do not infer implementation from registration, database connectivity, or a nonempty result in one environment; newly registered strategies must not be automatically advertised.
  * **Constraints:** The new field is additive and has a stable array shape, including `[]` when nothing is supported. Preserve `view`, `preview`, `suggest`, `extend`, and the OpenRefine type names.
  * **Validation:** `V-1`, `V-2`: supported IDs unique and present exactly once in `defaultTypes`; `taxon` remains in `defaultTypes` but not in `supportedTypes`.
  * **Result (2026-11-04):** `SUPPORTED_RECONCILIATION_TYPES` in `src/metadata.py` publishes `administrative_region`, `bibliographic_reference`, `country`, `data_type`, `dimension`, `feature_type`, `location`, `method`, `sampling_context`, and `site`. Excluded with a recorded reason: `taxon` (matcher returns `[]`), `geonames` (external GeoNames service), `modification_type` (requires an LLM provider). `_get_supported_types` raises `ValueError` when a declared ID has no `defaultTypes` entry.

* [x] `T1.2` **Change:** Reject invalid required manifest metadata while representing a legitimate empty property list.
  * **Target:** Authority Service `src/api/model.py::ReconServiceManifest`, `ExtendDescriptor`, `PropertySetting`; `src/metadata.py::_compile_property_settings`, `get_reconciliation_metadata`.
  * **Current → required:** `defaultTypes` may silently default to empty and `extend` may be absent → the generated service response contains required valid `defaultTypes`, `reconciliation.supportedTypes`, and `extend.property_settings` arrays.
  * **Implementation:** Add a typed reconciliation descriptor and service-response validation for unique nonblank type IDs, supported IDs resolving to exactly one default type, and property entries with a nonblank `name` and an `entity_types` array of nonblank IDs. Retain `property_settings: []` and a supported type with no matching property entries as valid. Check `site`, `location`, and `feature_type` declarations against their strategy resource metadata and preserve existing OpenRefine fields; report any claimed property behavior not implemented by a matcher rather than silently claiming property-assisted matching.
  * **Constraints:** Validate the service manifest at the producer; Phase 2 owns the client error message and saved-mapping behavior. Do not broaden unrelated API model constraints without tests of their other uses.
  * **Validation:** `V-1`, `V-2`: missing fields, wrong shapes, duplicate or blank IDs, invalid property entries, and unresolved IDs fail; `feature_type` is valid with zero properties; `location` yields only `place_name`.
  * **Result (2026-11-04):** `ReconciliationDescriptor` added; `defaultTypes`, `reconciliation`, `extend`, and `extend.property_settings` are required. Blank/duplicate type IDs, unresolved supported IDs, blank `name`/`label`/`type`, and empty or blank `entity_types` are rejected. An empty `supportedTypes` array and an empty `property_settings` array remain valid.

**Completion evidence:** A serialized GET response has the new contract, its existing OpenRefine fields remain present, and no placeholder type is advertised for matching.

### Area 2: Lock down the contract with tests

**Objective:** Make manifest regressions and zero-property behavior visible before the editor consumes the contract.

**Affected code:** Authority Service `tests/test_metadata.py`, `tests/api/test_model.py`, `tests/api/test_router.py` (all existing).

**Dependencies:** Area 1.

**Tasks:**

* [x] `T2.1` **Change:** Add producer/model/route tests covering the manifest contract and OpenRefine compatibility.
  * **Target:** Authority Service `tests/test_metadata.py::test_compile_property_settings_dedup_and_entity_types`, `tests/api/test_model.py::TestReconServiceManifest`, `tests/api/test_router.py::TestMetaEndpoint`.
  * **Current → required:** Existing tests check OpenRefine metadata only → tests distinguish supported from merely registered types and reject malformed required metadata.
  * **Implementation:** Use mock strategies to verify supported-ID membership and uniqueness; retain assertions for existing `defaultTypes`, `extend.property_settings`, URLs, and property-type membership. Add model tests for missing/invalid arrays and entries, duplicate/blank IDs, and a valid empty supported list. Add a registry-backed `feature_type`/`location` case asserting `[]` versus `["place_name"]`; do not use a mocked `MockStrategy` whose properties are the same for every type as proof of that distinction.
  * **Constraints:** Keep tests isolated from live databases; update existing minimal-model fixtures when fields become required.
  * **Validation:** `V-1`, `V-2`: all positive, negative, and compatibility assertions pass.
  * **Result (2026-11-04):** Added supported-type and builder-failure tests to `tests/test_metadata.py`, required-field and rejection tests to `tests/api/test_model.py`, and live-contract assertions to `tests/api/test_router.py`. The registry-backed case reads the real `FeatureTypeReconciliationStrategy` and `LocationReconciliationStrategy` resources and asserts `[]` versus `["place_name"]`.

**Completion evidence:** Focused model/metadata/API tests pass with explicit OpenRefine and zero-property assertions.

### Area 3: Verify deployed access and real pilot candidates

**Objective:** Both pilot types return candidates through the deployed service as its database role.

**Affected code:** Authority Service `schema/create_schema.sh::generate_deploy_sql`, `schema/sql/grants.sql`, `schema/__deploy__.sql` (generated), `docs/OPERATIONS.md`. The real request path is `src/api/router.py::reconcile` → `src/reconcile.py::reconcile_queries` → registered strategies → `src/strategies/query.py::BaseRepository.fetch_all`.

**Dependencies:** Areas 1–2 and an authorized disposable database with pilot rows; staging check follows disposable validation.

**Tasks:**

* [x] `T3.1` **Change:** Verify the committed deployment grants and service-role read access.
  * **Target:** Authority Service `schema/create_schema.sh::generate_deploy_sql`, `schema/sql/grants.sql`, `schema/__deploy__.sql` (generated), `docs/OPERATIONS.md`.
  * **Current → required:** Grant sources and generated SQL are committed, with read access to `PUBLIC` approved but not verified as deployed → grants execute *after* schema objects are created and the service role can read the match functions and backing views.
  * **Implementation:** Verify that the committed grants retain the approved `PUBLIC` scope in both single-file and `\i` generator paths; refresh the generated SQL only if its source changes. Run the destructive generator only in an isolated disposable checkout: its cleanup replaces `schema/__deploy__.sql` and removes `schema/generated/`. Document how to check the service role's read access and distinguish manifest health from database health. Apply schema changes only to the disposable database through the documented setup; shared-environment deployment must follow its normal approval process.
  * **Constraints:** Never run `schema/create_schema.sh --deploy` against shared staging/production during this plan: `schema/sql/authority.sql` drops the schema. Keep credentials out of the plan and logs.
  * **Validation:** `V-3`: inspect generated placement in both output modes, query schema USAGE, routine EXECUTE, and materialized-view SELECT as the service role, and confirm the candidate endpoint no longer fails on schema permission errors.
  * **Result (2026-11-04):** `PUBLIC` grants retained in `schema/sql/grants.sql`. Both generator modes place grants last, and a regenerated `schema/__deploy__.sql` matches the committed file byte for byte. Deployed with `--no-generate --deploy` to the documented disposable Podman database; `authority` USAGE, routine EXECUTE, and view SELECT are true for a fresh non-owner role.
  * **Result caveat:** `authority.fuzzy_location` is `SECURITY INVOKER` and reads `public.tbl_location_types`, which the approved `authority`-only grants do not cover. A role holding only those grants fails `location` matching with `permission denied for table tbl_location_types`. Guidance added to `docs/OPERATIONS.md`; extending grants to public tables is a separate approval.

* [x] `T3.2` **Change:** Record real candidate and access results for each pilot type.
  * **Target:** Authority Service `src/api/router.py::reconcile` and deployed service; verification recorded in this plan's `V-4` result when executed.
  * **Current → required:** The source proposal records earlier live candidates, but no current Phase 1 request has been run → read-only requests against the completed disposable deployment, followed by staging smoke checks, return nonempty candidate lists for both types.
  * **Implementation:** Use known rows (`Trench` for `feature_type`, `Sweden` for `location`), request no properties for the classifier, check returned type and candidate ID/score, and record HTTP status and environment separately. For staging use only GET manifest and POST match requests, never schema deployment or sidecar export. If the manifest succeeds but a query fails, report the database/grant blocker rather than declaring the type verified.
  * **Constraints:** Do not use the site-only `/reconcile/readiness` response as evidence for either pilot. No write operation on shared staging.
  * **Validation:** `V-3`, `V-4`: both request results are nonempty under the actual deployed role, or the specific blocker is documented.
  * **Result (2026-11-04):** Disposable service, documented runtime role: `feature_type` "Trench" returned 2 candidates (`/feature_type/25` 100%, `/feature_type/41` 58.33%) and `location` "Sweden" returned 1 candidate (`/location/205` 100%). The same requests as a minimal non-owner role returned `feature_type` candidates and HTTP 500 for `location` (the grant-scope finding above). Staging smoke not run: the deployed staging service still runs the pre-change image, and deploying the new contract is a separate approved operation.

**Completion evidence:** A reviewed grant path and real HTTP responses show both pilots working as the deployed service role; staging smoke results or an explicit deployment blocker are recorded.

## Acceptance-Criteria Coverage

| Criterion (source) | Task IDs | Validation IDs | Expected evidence |
| --- | --- | --- | --- |
| `PH1-AC-1` (`P-AC-2`) | `T1.1`, `T1.2`, `T2.1` | `V-1`, `V-2` | Published IDs resolve uniquely in `defaultTypes`, `taxon` stays OpenRefine-only, and existing manifest keys/properties remain available. |
| `PH1-AC-2` (`P-AC-3`) | `T1.2`, `T2.1` | `V-1`, `V-2` | Empty `feature_type` property list passes; missing/malformed required metadata fails. |
| `PH1-AC-3` (`P-AC-5`) | `T3.1`, `T3.2` | `V-3`, `V-4` | Service role has read access and both real pilot requests return candidates. |

## Validation And Testing

Commands in this table run from the **Authority Service** repository. Do not run deployment commands on a shared database. The live checks require an authorized disposable copy and the service configured to use its actual runtime role.

| ID | Check and target | Command or executable method | Covers | Expected result | Baseline (2026-11-04) |
| --- | --- | --- | --- | --- | --- |
| `V-1` | Contract and negative tests in `tests/test_metadata.py`, `tests/api/test_model.py` | `.venv/bin/pytest -p no:cacheprovider tests/test_metadata.py tests/api/test_model.py -q` | `PH1-AC-1`, `PH1-AC-2` | Both valid empty arrays and the zero-property case pass; malformed/missing arrays, duplicate IDs, and invalid property entries fail validation. | Pass (2026-11-04): exit 0, 111 tests, 0 failures, 0 skipped; the new positive and negative cases ran. |
| `V-2` | Serialized GET metadata and OpenRefine regressions in `tests/api/test_router.py`, plus existing `tests/api/test_readiness.py` | `.venv/bin/pytest -p no:cacheprovider tests/test_metadata.py tests/api/test_model.py tests/api/test_router.py tests/api/test_readiness.py -q` | `PH1-AC-1`, `PH1-AC-2`, existing site readiness | GET returns `reconciliation.supportedTypes` while preserving `defaultTypes`, `extend`, URLs, and the existing site checks. | Pass (2026-11-04): exit 0, 143 tests, 0 failures, 0 skipped; GET returns `reconciliation.supportedTypes = [10 IDs]` with `taxon` only in `defaultTypes`. |
| `V-3` | Deployment SQL and service-role access | In an isolated disposable checkout containing the committed grant sources, inspect both `schema/create_schema.sh --single-sql` and `schema/create_schema.sh --no-single-sql` outputs without `--deploy`; verify grants follow schema creation. Never run this generator in the planning working tree. Follow `docs/DEVELOPMENT.md`'s disposable database procedure, deploy only there, then connect *as the service role* and check `has_schema_privilege` on `authority`, `has_function_privilege` on `authority.fuzzy_feature_type(text,integer)` and `authority.fuzzy_location(text,integer,integer[])`, and `has_table_privilege` on their backing views; require successful read-only calls. | `PH1-AC-3` | No `permission denied for schema authority`; routine and view read permissions are true for the configured role. | Pass with one recorded limitation (2026-11-04): both generator modes place grants after all objects, the regenerated artifact matches the committed `schema/__deploy__.sql`, and a fresh non-owner role has `authority` USAGE, routine EXECUTE, and view SELECT. `fuzzy_location` additionally needs `SELECT` on `public.tbl_location_types`; see the `T3.1` result caveat. |
| `V-4` | Real matching and staging smoke test | With the disposable service running, `curl -fsS --json '{"queries":{"q0":{"query":"Trench","type":"feature_type","limit":3},"q1":{"query":"Sweden","type":"location","limit":3}}}' http://127.0.0.1:8000/reconcile`; inspect `q0.result` and `q1.result` for nonempty arrays, correct type IDs, candidate URIs, and scores. Repeat GET `/reconcile` and read-only POST requests against the approved staging URL after deployment; record both statuses and candidate counts without secrets. | `PH1-AC-3` | Both requests return real candidate rows; staging manifest alone is insufficient. | Pass for the disposable environment (2026-11-04): HTTP 200, `q0` 2 candidates (`Trench` 100%, `Wall trench` 58.33%), `q1` 1 candidate (`Sweden` 100%). Staging smoke not run: the staging deployment still runs the pre-change image; deploying the new contract is a separate approved operation. |
| `V-5` | Focused quality checks on changed Python files | `.venv/bin/black --check src/metadata.py src/api/model.py tests/test_metadata.py tests/api/test_model.py tests/api/test_router.py` and `.venv/bin/isort --check-only src/metadata.py src/api/model.py tests/test_metadata.py tests/api/test_model.py tests/api/test_router.py`; use `make check-imports` if imports change. | Quality gate | Formatting and imports pass without rewriting unrelated files. | Pass (2026-11-04): `black --check` and `isort --check-only` exit 0; `scripts/check_imports.py` reports no inconsistencies; `pylint src/metadata.py src/api/model.py` scores 10.00/10. |

The existing `tests/integration/test_reconcile_integration.py::TestManualDatabaseTesting` cases are explicitly skipped and test only `site`; they cannot replace `V-4`.

## Deliverables

| Deliverable | Target (Authority Service) | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Manifest builder | `src/metadata.py::get_reconciliation_metadata` and property helpers | `T1.1`, `T1.2` | Additive, valid supported-type/property output. |
| Response contract | `src/api/model.py::ReconServiceManifest`, reconciliation descriptor **NEW symbol**, related field validators | `T1.2` | Missing/invalid metadata rejected; empty properties accepted. |
| Contract tests | `tests/test_metadata.py`, `tests/api/test_model.py`, `tests/api/test_router.py` | `T2.1` | Positive, negative, and OpenRefine regressions pass. |
| Deployment access | `schema/create_schema.sh`, `schema/sql/grants.sql` (committed) | `T3.1` | Approved grant scope and verified grant order and service-role permissions in disposable DB. |
| Generated deployment artifact | `schema/__deploy__.sql` (existing generated file) | `T3.1` | Generated artifact reflects reviewed source SQL. |
| Operational access guidance | `docs/OPERATIONS.md` | `T3.1` | Describes grant check and why manifest health is not a match check. |
| Real request record | This plan's `V-3`/`V-4` baseline/result entries (update on execution) | `T3.2` | Environment-specific response and privilege results, or a named blocker. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1 — manifest | Done | Approved proposal | `reconciliation.supportedTypes` published for 10 reviewed types; `defaultTypes`, `view`, `preview`, `suggest`, and `extend` unchanged. |
| Area 2 — contract tests | Done | Area 1 | 111 tests in the V-1 files and 143 in the V-2 files pass; the full suite reports 1209 tests, 0 failures, 43 pre-existing skips. |
| Area 3 — deployment and candidates | In progress | Areas 1–2; authorized disposable DB | Grant order and privileges verified; both pilots returned real candidates in the disposable environment. Staging deployment and the `location` grant fix for minimal roles remain outstanding. |

## Definition Of Done

* [x] `PH1-AC-1`, `PH1-AC-2`, and `PH1-AC-3` have actual task and validation results recorded, not just planned assertions.
* [ ] All three areas and listed deliverables are complete; the existing OpenRefine response is regression-tested.
* [ ] `V-1`–`V-5` pass, including negative/empty metadata checks and both database-backed candidate requests.
* [x] Approved `PUBLIC` grants are applied through the approved deployment route and checked as the service role; no destructive deployment was run against shared staging.
* [x] Property declarations, response model, generated SQL, and operational guidance agree with the deployed behavior.
* [x] Any deviation or unresolved deployment blocker is recorded explicitly; do not mark Phase 1 complete with only a healthy manifest.

Two items are carried forward and remain unsatisfied in this phase: the `V-4` staging smoke test waits for the new contract to be deployed through the normal approval path, and `location` matching for a role without `public.tbl_location_types` read access needs a separate grant decision. The disposable checks cover both pilot types and the reviewed grant path.

## Decisions And Risks

- Resolved decision: Authority Service grant files are committed in `4fb9b22`, and read grants to `PUBLIC` are approved. Deployment and effective service-role access still require `V-3`/`V-4`; record any deployment blocker rather than weakening the candidate criterion. Outcome: deployed to the disposable database only, checks passed, and staging deployment is pending its normal approval.
- New finding (2026-11-04): `authority.fuzzy_location` is `SECURITY INVOKER` and reads `public.tbl_location_types`, so the approved `authority`-only grants are not sufficient for `location` matching by a role without public-table read access. `feature_type` is unaffected. Recorded in `docs/OPERATIONS.md`; extending grants to public tables needs its own approval and is not part of Phase 1.
- Supported-type audit (2026-11-04): only the 10 declared types are advertised. `taxon` (placeholder matcher), `geonames` (external service), and `modification_type` (LLM provider) stay in `defaultTypes` and are not published as supported.
- Known limitation: Authority Service advertises `place_name` for `location`, but its generic finder ignores submitted `place_name` values when filtering and ranking candidates. Matching uses the query label; mapping `place_name` does not constrain the results. Phase 1 verifies the property declaration and label-based matching only, not property-aware location matching. Do not extend Phase 1 to implement it or claim it was verified.
- Agreed decision: Other registered strategies have different database and external-provider requirements. Only publish IDs whose matching implementation was checked; if a strategy's status cannot be established from its implementation and tests, leave it unadvertised and record the reason without removing it from `defaultTypes`.
- Agreed handoff rule: Stop and report if registry behavior, the committed deployment grants, or the available disposable database differs from this repository basis. Do not substitute an unreviewed matcher or bypass the deployment approval path.
