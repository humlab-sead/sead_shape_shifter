# Reliable Reconciliation Links to Existing SEAD Entities - Phase 7 Task Plan

## Phase Summary

**Phase:** 7 - End-to-End Validation. **Readiness:** Validated for implementation; the live validation and phase completion are gated on verified SIMS adoption of existing `site` rows in the disposable database. The [phase plan](RECONCILIATION_MVP_PHASE_PLAN.md#phase-7-end-to-end-validation) marks this phase ready for a task plan, not already complete.

**Goal:** Prove that reviewed `site` decisions produce the intended normalized IDs, child foreign keys, and change-request results against a database-backed Authority Service and SIMS, including reruns and failures.

**Sources:** [Shape Shifter proposal](RECONCILIATION_MVP.md) (`SS-AC-1`, `SS-AC-8`), [phase plan](RECONCILIATION_MVP_PHASE_PLAN.md) (`VM-14`, `VM-15`), and the [Authority Service contract](https://github.com/humlab-sead/sead_authority_service/blob/main/docs/proposals/RECONCILIATION_IDENTITY_CONTRACT/RECONCILIATION_IDENTITY_CONTRACT.md) (`AS-AC-6`). Existing-site [adoption](https://github.com/humlab-sead/sead_authority_service/blob/main/docs/proposals/SIMS_EXISTING_SITE_ADOPTION.md) is a prerequisite owned by Roger Mähler, not work in this plan.

**Acceptance criteria**

1. [x] `PH7-AC-1` (from `SS-AC-1`): A reviewed `site` workflow sets the intended `public_id` and foreign-key values; unchanged review, export, and normalization reruns give identical results.
2. [x] `PH7-AC-2` (from `SS-AC-8`): One database-backed end-to-end test covers success, local-only approval, undecided-row block, rejection, rerun, changed decision, stale link, absent row, and unavailable service.
3. [x] `PH7-AC-3` (from `SS-AC-8`, `AS-AC-6`): A health-only service cannot pass readiness; an approved existing `site` binds through SIMS after adoption.

**Dependencies and constraints:** Use the Phase 2 review, Phase 5 verified export, Phase 6 approvals/ingester rule, and Phase 4 SIMS binding rule. Do not start the live run before the Authority Service's disposable database has the real `site` match function, an existing SEAD site is adopted as `materialized`, and the `site` allocator is above existing IDs. Keep normalization offline, review explicit, existing manual/unowned links protected, and Core child FKs based on local `system_id`; only a declared change-request `foreign_key_value_sources.<target>: public_id` can use a target ID in a package FK.

## Repository Findings

**Repository basis:** Shape Shifter branch `reconciliation-mvp` at `6e8f788e`; Authority Service branch `dev` at `0e2d5e9`; inspected 2026-10-31. The uncommitted phase plan (including the named adoption owner and Phase 7 readiness) was considered. This follow-up's uncommitted owner-verification changes are included below; unrelated uncommitted files were excluded. Graphify was used for navigation; the file-level paths below were checked against current source and tests.

| Verified source | Current behavior | Planning implication |
| --- | --- | --- |
| `backend/app/api/v1/endpoints/reconciliation.py::{auto_reconcile_entity, update_mapping, export_reconciliation_to_mapping}`; `backend/tests/api/v1/{test_reconciliation_decisions,test_reconciliation_export}.py` | The project routes create proposals, persist per-key operator decisions, and export accepted links/local-only approvals. Existing route tests use an authorized, API-created project; export tests stub candidate verification. | Drive the real review and export routes on an isolated project, but do not replace the live Authority Service call with a mock in the end-to-end test. Check export response **and** committed sidecar. |
| `src/normalizer.py::ShapeShifter`; `backend/tests/api/v1/test_reconciliation_export.py::test_exported_links_normalize_offline_with_stable_parent_ids_and_child_foreign_keys` | A committed link changes the site's `site_id`; a local-only approval does not write an ID. The sample's Core `site_id` FK contains the parent's `system_id`, not the SEAD `site_id`. | Assert actual keyed `site_id` and local child FK values on two offline normalizations; separately check target-facing package FKs if a `public_id` source is declared. |
| `backend/app/services/project_ingester_service.py::_attach_local_only_approvals`; `ingesters/sead_change_request/contracts.py::TrustedProjectContext`; `ingesters/sead_change_request/ingester.py::_local_only_approval_errors` | The saved-project handoff now checks each committed approval against the reconciliation specification named by its owner and requires a local-only decision for the same encoded key. It passes the verified owner to the ingester, which compares against that owner rather than the target model's `public_id`; committed-approval, business-key, and missing-ID checks remain. | Exercise the saved-project validate/ingest path and inspect generated assignments/artifacts, not only an ingester with hand-built tables. Use separate isolated projects/runs for blocked and successful cases. |
| `backend/app/services/ingester_runtime.py::SeadChangeRequestSimsAdapter`; `backend/app/core/config.py`; `backend/tests/ingesters/{test_sead_change_request_orchestration,test_sead_change_request_direct_fk_postgres}.py` | The adapter calls the configured SIMS URL; target-row checks use PostgreSQL. Reconciled local-only rows allocate only with permitted modes; a declared direct target-ID FK is checked against the target database. | Configure both service URLs and the ingester target connection to the same disposable environment. Assert SIMS-approved existing ID, allocated local-only ID, and package FK independently of the Core FK. |
| Authority Service `src/api/router.py::{reconciliation_readiness, verify_candidates}`; `tests/identity/test_reconciliation_contract_integration.py`; `tests/api/test_readiness.py` | Readiness runs the database-backed `site` match path; the integration test covers real candidate existence and approved-ID binding, but skips without `SIMS_INTEGRATION_DB=1` and its loopback DB configuration. | Require a positive readiness result and a real match before review; explicitly test that health/manifest alone do not satisfy the preflight. Run the existing Authority integration file with its opt-in. |
| Authority Service `scripts/verify_sims_identity_candidates.sh`; `docs/DEVELOPMENT.md` | The helper restores a loopback-only database at `127.0.0.1:55432/sead_staging`; `bootstrap site` adds materialized identities and initializes the allocator, but its preflight rejects inconsistent SIMS/SEAD IDs. | Use the documented helper only against an authorized disposable copy. Verify adoption and allocator results before the live test; stop and report a bootstrap discrepancy rather than repairing or targeting staging/production. |
| `backend/tests/integration/test_reconciliation_client.py`; `backend/tests/conftest.py`; `frontend/src/components/reconciliation/__tests__/{ReconciliationGrid,ReconciliationView}.test.ts` | Existing live-client checks may skip on connection errors; authenticated project tests use `authorized_client`; UI tests use mocked responses. | Add a dedicated opt-in end-to-end test that fails rather than reporting success when prerequisites are missing, plus a manual real-UI check. Do not mistake mocked tests or skipped live checks for `VM-14`. |

## Scope

**In scope:** An isolated `site` project and child-row fixture; one live cross-service test module; readiness/adoption gate; real API review, export, offline normalization, project-based change-request generation, verified local-only approval ownership, and sidecar/artifact/DB assertions; a recorded manual UI check and validation results in this plan.

**Out of scope:** Production or staging writes, implementing the separate SIMS adoption proposal, changing external service contracts, adding new entity types, changing normalization, SEAD cutover, or silently repairing a disposable database that fails preflight.

**Affected contracts/data:** Project YAML, reconciliation catalog, owner-tagged mapping sidecar, `site`/child normalized tables, SIMS binding and allocation results, change-request artifact target IDs/FKs, and Authority Service readiness. All project files, output, and any test database rows must be isolated to the disposable run.

## Work Breakdown

### Area 1: Gate the disposable live environment

**Objective:** A live test either has a working `site` match path, adopted existing ID, and safe allocator, or stops with a specific prerequisite failure.

**Affected code:** `backend/tests/integration/test_site_reconciliation_end_to_end.py` (**NEW**); existing Authority Service helper and tests are read-only prerequisites.

**Dependencies:** Phase 4 service and SIMS rule; completed site adoption in the disposable database.

* [x] `T1.1` **Change:** Add an explicit opt-in fixture for the end-to-end test.
  * **Target:** `backend/tests/integration/test_site_reconciliation_end_to_end.py` (**NEW**).
  * **Current → required:** No cross-service `site` test → use `@pytest.mark.integration`, the existing `SIMS_INTEGRATION_DB` opt-in, an authorized temporary project/output directory, and a loopback-only target guard. Default suite collection may skip without opt-in; an opted-in run must **fail** on missing services, DB, adoption, or credentials.
  * **Implementation:** Point Shape Shifter's `RECONCILIATION_SERVICE_URL`, `SIMS_SERVICE_URL`, and `INGEST_TARGET_*` settings at the same helper-owned environment. Provision the database using the documented Authority helper outside the test; query the disposable SEAD/SIMS data to select a real labeled site and verify its `materialized` identity and allocator. Do not hard-code an ID or use staging/production. Stop on the helper's bootstrap/preflight discrepancy.
  * **Constraints:** Do not create real provider data in an unowned database, log secrets, reset a shared DB, or silently skip after opt-in. Use `authorized_client` and register projects through `POST /api/v1/projects`.
  * **Validation:** `V-1`, `V-3`, `V-4`; an unadopted site or missing match function stops before review.
* [x] `T1.2` **Change:** Reject metadata-only service readiness.
  * **Target:** `backend/tests/integration/test_site_reconciliation_end_to_end.py` (**NEW**).
  * **Current → required:** Health/manifest checks do not prove matching works → preflight requires `GET /reconcile/readiness?type=site` to return HTTP 200 with `ready: true`, then an actual `site` match and candidate check.
  * **Implementation:** Test the same preflight against a health-only/incomplete test service and assert rejection even when `/reconcile` returns metadata; record the reason. Keep the positive path connected to the real Authority Service and let its existing disposable-DB test check the missing-function path.
  * **Constraints:** A stub may demonstrate the negative readiness gate, but never substitute for the positive live service, candidate lookup, or SIMS binding.
  * **Validation:** `V-3`, `V-4`; a health-only service fails and the real service passes.

**Completion evidence:** The opted-in preflight identifies the real `site` candidate, confirms adoption and allocator safety, and fails closed on every missing prerequisite.

### Area 2: Exercise review, export, normalization, and binding

**Objective:** One reviewed existing site and one local-only site have provable, distinct outcomes through the entire workflow.

**Affected code:** `backend/tests/integration/test_site_reconciliation_end_to_end.py` (**NEW**); `backend/app/services/project_ingester_service.py`; `ingesters/sead_change_request/{contracts.py,input_resolution.py,ingester.py}`; focused service and ingester tests; existing route and normalizer interfaces above.

**Dependencies:** Area 1; Phase 2, Phase 5, and Phase 6 outputs.

* [x] `T2.1` **Change:** Drive actual per-key decisions and export through the saved project.
  * **Target:** `backend/tests/integration/test_site_reconciliation_end_to_end.py` (**NEW**).
  * **Current → required:** Separate route tests mock verification → create a site fixture with distinct business keys (including two rows with the same search label), a child using a Core FK, and a reconciliation specification using the real `site` service. Auto-reconcile to proposals; explicitly accept the returned candidate URI/ID for one key, mark another local-only, and leave/reject separate keys. Export through the project endpoint.
  * **Implementation:** Assert decision states survive review rerun, accepted `site_id`/URI correspond to the real SEAD row, exported link has correct owner and `verified_at`, local-only has a separate owned approval and no ID link, and rejected/undecided keys have neither. Save catalog and sidecar snapshots, re-export unchanged decisions, and compare effective entries without treating timestamps as IDs.
  * **Constraints:** No auto-accept; do not infer candidate URIs from numeric IDs. Reuse API-created project authorization and version-checked export.
  * **Validation:** `V-2`, `V-3`; acceptance is tied to the intended business key, not the shared label.
* [x] `T2.2` **Change:** Check two offline normalizations and a real SIMS-backed change-request run.
  * **Target:** `backend/tests/integration/test_site_reconciliation_end_to_end.py` (**NEW**); `backend/app/services/project_ingester_service.py::_attach_local_only_approvals`; `ingesters/sead_change_request/contracts.py::TrustedProjectContext`; `ingesters/sead_change_request/ingester.py::_local_only_approval_errors`; focused service and ingester tests.
  * **Current → required:** A previous live run stopped before SIMS because the export owner is `site.site_name` while the ingester compared it with `site.site_id` → verify the sidecar owner against an existing reconciliation specification and its local-only decision for the same encoded business key, pass that verified owner to the ingester, then run `ShapeShifter.normalize()` twice on the saved project with HTTP disabled for the normalization calls and invoke authorized project validation/ingestion with real SIMS and disposable target-row checks.
  * **Implementation:** Record keyed `site.public_id` values: accepted equals the verified SEAD `site_id`, local-only stays null until ingester allocation, rejected/undecided stay without an exported ID. Assert child Core `site_id` equals the parent's local `system_id` on both runs. The backend must reject an approval whose owner specification is missing or whose key is not currently local-only; the ingester must compare the approval with that verified owner, not with `public_id`. Keep the committed-approval, business-key, and missing-ID checks. In isolated successful ingester runs, assert SIMS returns/binds the adopted existing ID, allocates a different collision-free ID for the local-only approval, and the generated change-request artifact contains the expected target-facing IDs and child FK values. If a package FK uses an existing target ID, declare `foreign_key_value_sources.<target>: public_id` and assert that lookup against the disposable target succeeds; never compare this package value to the Core FK.
  * **Constraints:** Use separate scope/run IDs for scenarios whose decisions change; replay the same run ID only for the unchanged idempotency case. Do not execute a generated deploy artifact against a non-disposable database.
  * **Validation:** `V-2`, `V-3`, `V-4`; report actual IDs and FK values, not just row counts or mocked responses.

**Completion evidence:** The two offline normalizations returned the same IDs and Core FK values. The live run bound adopted `site_id` 1, allocated local-only `site_id` 6504, and generated `sample_group_id` 13962. Its Core child `site_id` was local `system_id` 10001; the package child FKs were adopted `site_id` 1 and `method_id` 3. V-2, V-3, and V-4 passed.

### Area 3: Cover failures and record the MVP result

**Objective:** Negative and transition cases cannot create unintended links, approvals, SIMS allocations, or successful artifacts.

**Affected code:** `backend/tests/integration/test_site_reconciliation_end_to_end.py` (**NEW**); this task plan for the validation record.

**Dependencies:** Areas 1-2.

* [x] `T3.1` **Change:** Extend the same test module with isolated transition and failure scenarios.
  * **Target:** `backend/tests/integration/test_site_reconciliation_end_to_end.py` (**NEW**).
  * **Current → required:** Focused mocked tests cover these cases separately → on real service/DB, assert undecided and rejected rows with missing IDs are blocked before SIMS; accepted-to-rejected or accepted-to-local-only decisions remove only their owner's stale link; subsequent local-only-to-accepted transition removes its owned approval. Re-export a candidate that has disappeared, and retry after service unavailability.
  * **Implementation:** Use a valid-shaped candidate URI for an ID absent from the disposable SEAD table; change a previously accepted key to that absent ID to check removal of its old owned link. Assert `not_found` prevents export, while an unavailable service exports an unverified link with empty `verified_at` and a later re-export verifies a real candidate. Verify protected manual/unowned links remain untouched, no blocked case creates a successful change-request artifact, and no new SIMS allocation is made for rejected/undecided rows.
  * **Constraints:** An unavailable service is not an invalid candidate; a malformed service response is not an outage. Avoid broad DB mutations or a test that relies on an existing site disappearing in a shared database.
  * **Validation:** `V-2`, `V-3`; each state transition has explicit sidecar, response, and SIMS/artifact assertions.
* [x] `T3.2` **Change:** Record live validation and manual review results without calling a skipped run a pass.
  * **Target:** `RECONCILIATION_MVP_PHASE_7_TASK_PLAN.md` (this file).
  * **Current → required:** No Phase 7 validation record → write the executed commands, environment type, selected/allocated IDs and both FK kinds, observed statuses, skips/failures, and any deviation into this plan's tracker and validation table during implementation.
  * **Implementation:** Check the real review UI for candidates/confidence, explicit accept/reject/local-only actions, unresolved/failure display, and verified/unverified link status; capture reproducible results without including copied private SEAD rows or credentials. Confirm `VM-14` and `VM-15` only after both live runs and manual UI check.
  * **Constraints:** Do not alter the phase plan or companion proposals during this planning-only request; if implementation exposes a conflicting source contract, stop and report it rather than inventing a replacement design.
  * **Validation:** `V-3` to `V-6`; a skipped integration test cannot close the phase.

**Completion evidence:** One reproducible test run covers every `PH7-AC-*` scenario, and this plan records actual IDs, FKs, and prerequisite checks.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
| --- | --- | --- | --- |
| `PH7-AC-1` (`SS-AC-1`) | `T2.1`, `T2.2`, `T3.2` | `V-2`, `V-3`, `V-5` | Per-key accepted and local-only normalized IDs, Core child FKs, package target FKs, and unchanged rerun comparisons. |
| `PH7-AC-2` (`SS-AC-8`) | `T2.1`, `T2.2`, `T3.1`, `T3.2` | `V-2`, `V-3`, `V-5`, `V-7` | Unit checks reject stale or mismatched approval ownership; one opted-in end-to-end module executes the positive and all named negative/transition cases without mocking the positive service paths. |
| `PH7-AC-3` (`SS-AC-8`, `AS-AC-6`) | `T1.1`, `T1.2`, `T2.2`, `T3.2` | `V-3`, `V-4` | Health-only readiness rejected, real DB-backed match accepted, adopted `materialized` existing ID bound by SIMS. |

## Validation And Testing

Prepare only a helper-owned disposable database: follow the Authority Service [development procedure](https://github.com/humlab-sead/sead_authority_service/blob/main/docs/DEVELOPMENT.md#disposable-database-for-integration-tests) (`dump --yes`, `setup`, `bootstrap site`, `credentials`) **with authorized source data**. Do not run these commands against staging/production or store credentials in this plan. Configure the documented `SEAD_AUTHORITY_OPTIONS_DATABASE_*` variables for `127.0.0.1:55432/sead_staging`, start the Authority Service with its documented `make serve`, and set the Shape Shifter service/ingest settings to that disposable environment. If bootstrap reports an ID discrepancy, stop and record it; do not repair it in this phase. The new test must check these prerequisites itself after opt-in.

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
| --- | --- | --- | --- | --- | --- |
| `V-1` | Current Shape Shifter review, export, ingester, and offline regression | `.venv/bin/pytest -q backend/tests/api/v1/test_reconciliation_decisions.py backend/tests/api/v1/test_reconciliation_export.py backend/tests/ingesters/test_sead_change_request_orchestration.py backend/tests/services/test_project_ingester_service.py tests/process/test_shapeshifter.py` | Phase dependencies and `PH7-AC-1` regression | Existing behavior preserved; does not by itself prove Phase 7. | Pass (2026-10-31; targeted suite completed). |
| `V-2` | Regression, owner handoff, and sequence reservation | `uv run pytest -o addopts='' -q backend/tests/api/v1/test_reconciliation_decisions.py backend/tests/api/v1/test_reconciliation_export.py backend/tests/ingesters/test_sead_change_request_orchestration.py backend/tests/ingesters/test_sead_change_request_runtime.py backend/tests/services/test_project_ingester_service.py tests/process/test_shapeshifter.py backend/tests/integration/test_site_reconciliation_end_to_end.py backend/tests/ingesters/test_sead_change_request_ingester.py backend/tests/ingesters/test_sead_change_request_input_resolution.py backend/tests/ingesters/test_sead_change_request_identity_resolution.py` | `PH7-AC-1`, `PH7-AC-2` | Existing tests pass; missing specifications, non-local decisions, and unverified owners are rejected; ordinary collection cannot access a live DB. | Pass (2026-10-31: 346 passed, 6 expected opt-in database/live-test skips). |
| `V-3` | Opted-in end-to-end review/export/normalization/ingest and readiness; `backend/tests/integration/test_site_reconciliation_end_to_end.py` (**NEW**) | From Shape Shifter root, with the documented disposable DB and live Authority Service: `SIMS_INTEGRATION_DB=1 .venv/bin/pytest -o addopts='' -q -s backend/tests/integration/test_site_reconciliation_end_to_end.py -m integration`, using the five documented disposable settings and a temporary mode-600 `PGPASSFILE`. Inspect the pytest summary for **zero skipped** tests. | `PH7-AC-1` to `PH7-AC-3`; `VM-14`, `VM-15` | All named cases pass with actual IDs/FKs; missing adoption, health-only service, or broken matching fails explicitly. | Pass (2026-10-31: 5 passed, zero skipped; adopted site 1, local-only site 6504, child `sample_group_id` 13962, `method_id` 3, Core child `site_id` 10001, package child FKs `site_id` 1 and `method_id` 3). |
| `V-4` | Authority Service real candidate/readiness/approved-binding contract; `tests/identity/test_reconciliation_contract_integration.py` | From Authority Service root with the documented helper-owned DB: `SIMS_INTEGRATION_DB=1 .venv/bin/pytest -o addopts='' -q tests/identity/test_reconciliation_contract_integration.py -m integration`; inspect summary for **zero skipped**. | `PH7-AC-3`; `AS-AC-6`, `VM-15` | Real match, absent candidate, missing-function readiness, adopted-ID binding, and state checks pass. | Pass (2026-10-31: 5 passed, zero skipped; four FastAPI lifecycle deprecation warnings). |
| `V-5` | Operator review through the real UI, not just mocked Vue tests | Follow the [V-5 manual review runbook](#v-5-manual-review-runbook) below. It uses backend port `8013` and points Vite at that port; use another `BACKEND_PORT` and the matching `VITE_API_BASE_URL` when `8013` is already taken. | `PH7-AC-1`, `PH7-AC-2` | Operator sees the same candidate, decisions, failures, and status as the real API; no automatic acceptance. | Pass (2026-11-04): operator review in project `v5-manual-review`. Accepted link has `target_id: 1`, owner `(site, site_name)`, and a non-null `verified_at`; `local` has an owned approval and no target ID; `rejected` and `undecided` have neither. A verifier outage exported `verified_at: null` (`reconciliation · unverified`), and a later export verified it. An unchanged re-export reported `exported: 0`, `removed: 0`, both approval counts `0`, and left the sidecar byte-identical. |
| `V-6` | Test formatting, import order, and task-plan links | `.venv/bin/black --check` and `.venv/bin/isort --check-only` on all changed Python deliverables; `make check-doc-links`. | Deliverables and documentation | Formatting, import order, and local links pass; record any existing unrelated failure separately. | Pass (2026-10-31: Black and isort passed for 15 Python files; documentation links are valid). |
| `V-7` | Targeted Python type check for the owner handoff and ingester | `uv run pyright --threads 2 backend/app/services/project_ingester_service.py ingesters/sead_change_request/contracts.py ingesters/sead_change_request/input_resolution.py ingesters/sead_change_request/ingester.py backend/tests/services/test_project_ingester_service.py backend/tests/ingesters/test_sead_change_request_ingester.py` | `PH7-AC-2` | The owner-verification path and its trusted metadata have no type errors. | Not rerun: per user, the previously reported diagnostics were fixed on the published `pyright-error-fixes` branch and are excluded from this plan. |

### V-5 Manual Review Runbook

Use only the helper-owned disposable database and Authority Service. Do not stop, reset, or destroy the Podman database container. V-5 does not run ingestion or deploy a generated artifact.

1. **Start and check the disposable services.** From `/data/roger/source/sead_authority_service`, check the container:

   ```bash
   scripts/verify_sims_identity_candidates.sh status
   ```

   If the container is stopped, resume it without resetting its data:

   ```bash
   scripts/verify_sims_identity_candidates.sh start
   scripts/verify_sims_identity_candidates.sh status
   ```

   If the container is missing or `start` fails, stop here. Do not rerun `setup` or `bootstrap`, or destroy and recreate the container. Resolve the Podman issue and continue only after the helper reports the container running.

   If the Authority Service is not running, start it from the same repository with the disposable database settings:

   ```bash
   export CONFIG_FILE=./config/config.yml
   export SEAD_AUTHORITY_OPTIONS_DATABASE_HOST=127.0.0.1
   export SEAD_AUTHORITY_OPTIONS_DATABASE_PORT=55432
   export SEAD_AUTHORITY_OPTIONS_DATABASE_DBNAME=sead_staging
   export SEAD_AUTHORITY_OPTIONS_DATABASE_USER=postgres
   export PGPASSFILE=./tmp/name-of-temporary-password-file
   make serve
   ```

   Keep `PGPASSFILE` set to the temporary mode-600 password file (pgpass-phase7-v5) used for the disposable database. Do not copy its password into `.env` or this plan.

   From another terminal, confirm readiness:

   ```bash
   curl -fsS 'http://127.0.0.1:8000/reconcile/readiness?type=site'
   ```

    > {"type":"site","ready":true,"reason":null}

   Continue only if the helper reports the container running and readiness returns `ready: true`.

2. **Start Shape Shifter with isolated local state.** In a Shape Shifter terminal, set:

   ```bash
   export SHAPE_SHIFTER_ENVIRONMENT=development
   export SHAPE_SHIFTER_TRUSTED_PROXY_AUTH_ENABLED=false
   export SHAPE_SHIFTER_DEVELOPMENT_PRINCIPAL_ID=local-developer
   export SHAPE_SHIFTER_AUTHORIZATION_DATABASE_PATH=state/authorization-dev.sqlite3
   export SHAPE_SHIFTER_PROJECTS_DIR=tmp/v5-projects
   export SHAPE_SHIFTER_RECONCILIATION_SERVICE_URL=http://127.0.0.1:8000
   export SHAPE_SHIFTER_SIMS_SERVICE_URL=http://127.0.0.1:8000
   # uv run sead-authorization dev-bootstrap
   PYTHONPATH=. uv run python backend/app/scripts/authorization.py dev-bootstrap
   make BACKEND_PORT=8013 backend-run
   ```

   `SHAPE_SHIFTER_AUTHORIZATION_DATABASE_PATH` must stay `state/authorization-dev.sqlite3`. `dev-bootstrap` refuses any other path (`Development bootstrap only writes state/authorization-dev.sqlite3`), and only that path triggers the backend's uninitialized-store warning. V-5 isolation therefore comes from `SHAPE_SHIFTER_PROJECTS_DIR=tmp/v5-projects`, the disposable database, and a unique project name, not from a separate authorization database. Run `dev-bootstrap` before `backend-run`; it is idempotent, ignores a missing projects directory, and V-5 projects created through the API register their own resource record.

   In another Shape Shifter terminal, start the frontend:

   ```bash
   VITE_API_BASE_URL=http://127.0.0.1:8013 make FRONTEND_PORT=5173 frontend-run
   ```

   Open `http://127.0.0.1:5173`. Keep the Authority Service and Podman database running.

3. **Create a disposable project.** Create the project with `POST /api/v1/projects` and send the `site` entity together with its declared business key in that one request. Do not create an empty project in **Projects → New Project** and add the key afterwards: that dialog sends `entities: {}`, and a project bound to a provider-schema pair cannot change its declared `keys` through a later save. See [V-5 business-key rule](#v-5-business-key-rule).

   Use the `site` fixture shape from `backend/tests/integration/test_site_reconciliation_end_to_end.py`: a fixed `site` entity with `public_id: site_id`, business key `national_site_identifier`, and four rows keyed `accepted`, `local`, `rejected`, and `undecided`. Set each `site_id` to null and each `site_name` to the label for adopted site ID `1`. Also declare the fixed `data_provider` entity, because a bound project requires exactly one row whose `data_provider_id` is a positive integer and whose `data_provider_code` matches the bound code. Read the site label locally from the disposable database:

   ```bash
   cd /data/roger/source/sead_authority_service
   printf 'SELECT site_id, label FROM authority.site WHERE site_id = 1;\n' \
     | scripts/verify_sims_identity_candidates.sh sql -
   ```

   The restored database has no provider rows, so create one disposable provider row and use its ID. This mirrors what the Phase 7 integration test does for its own provider code, and the row stays inside the helper-owned disposable database:

   ```bash
   printf "INSERT INTO public.tbl_data_providers (data_provider_id, data_provider_code, data_provider_name)\nSELECT COALESCE(MAX(data_provider_id), 0) + 1, 'mal', 'MAL (V-5 manual review, disposable)'\nFROM public.tbl_data_providers\nRETURNING data_provider_id;\n" \
     | scripts/verify_sims_identity_candidates.sh sql -
   ```

   In development mode without trusted-proxy authentication, the backend authenticates plain requests as `SHAPE_SHIFTER_DEVELOPMENT_PRINCIPAL_ID`, so no header is needed. The request body must be valid JSON: the angle-bracket values below are placeholders, and sending one literally fails with `json_invalid` / `Expecting value`. Substitute the adopted site label, the returned `data_provider_id`, and a unique project name, and use the port your backend actually runs on (`BACKEND_PORT`; the recorded run used `8017`):

   **Request:**

   ```bash
   curl -sS -X POST http://127.0.0.1:8013/api/v1/projects \
     -H 'Content-Type: application/json' \
     -d '{
       "name": "v5-manual-review",
       "data_provider_code": "mal",
       "provider_schema": "archeobotany/mal",
       "entities": {
         "data_provider": {
           "type": "fixed",
           "public_id": "data_provider_id",
           "keys": ["data_provider_code"],
           "columns": ["system_id", "data_provider_id", "data_provider_code"],
           "values": [[1, <provider-id>, "mal"]]
         },
         "site": {
           "type": "fixed",
           "public_id": "site_id",
           "keys": ["national_site_identifier"],
           "columns": ["system_id", "site_id", "national_site_identifier", "site_name"],
           "values": [
             [10001, null, "accepted", "<label>"],
             [10002, null, "local", "<label>"],
             [10003, null, "rejected", "<label>"],
             [10004, null, "undecided", "<label>"]
           ]
         }
       }
     }'
   ```

   Expect HTTP 201. A name that already exists returns HTTP 409 and leaves the old file untouched; delete that project with `DELETE /api/v1/projects/{name}` (HTTP 204) before retrying, because a project saved with the wrong `keys` cannot be corrected in place. Do not copy the label or credentials into this plan.

4. **Add the reconciliation specification, then review and export.** A newly created project has no reconciliation specification, so the **Reconcile → Configuration** tab is empty and shows `No specifications configured` / `Add your first reconciliation specification to get started`. That is the expected state, not a missing step: create the specification now. See [V-5 specification setup](#v-5-specification-setup).

   Click **Add Specification** and set **Entity** = `site`, **Target Field** = `site_name`, **Source Type** = `Entity Preview` (the default), and **Remote Type** = `site`. Keep the default thresholds (**Auto-accept** 95%, **Review** 70%). Leave **Property Mappings** empty. Click **Create**; the button stays disabled until a field changes, and creating the specification writes the project's reconciliation catalog entry immediately. The API equivalent is listed under [V-5 specification setup](#v-5-specification-setup).

   In the specifications table, use the **Reconcile** action (wrench/sparkle icon) on the `site` → `site_name` row to open **Reconcile & Review**. Confirm the service status is online and click **Find Candidates**. Explicitly accept candidate ID `1` for `accepted`, mark `local` **Local-only**, reject `rejected`, and leave `undecided` proposed. Export to Mapping. Check the sidecar: the accepted link has target ID `1`, owner `(site, site_name)`, and a non-empty `verified_at`; the local-only row has a separate owned approval and no target ID; rejected and undecided have no link or approval.

   #### V-5 specification setup

   `frontend/src/components/reconciliation/SpecificationsList.vue` starts from the project's reconciliation catalog, which does not exist yet for a new project, so an empty Configuration tab means exactly one thing: the specification has not been created. Nothing in step 3 creates it.

   * **Entity and Target Field** are required and come from the saved project's entities and their columns. `site_name` is present because the create request in step 3 declares it in `site.columns`. If the Entity list is empty, reload the project first.
   * **Remote Type** is required. The list is loaded from the Shape Shifter backend endpoint `GET /api/v1/reconciliation/manifest` (`backend/app/api/v1/endpoints/reconciliation.py`), which forwards the configured `RECONCILIATION_SERVICE_URL`. When that call fails, the editor falls back to `site`, `taxon`, `location`, `abundance`, so a populated list is not proof that the Authority Service is reachable; use the readiness check from step 1 for that.
   * **Thresholds** default to `auto_accept_threshold` 95% and `review_threshold` 70%. The auto-accept value is a legacy score band and does not accept rows on its own: the model documents it as `retained for compatibility; matching never auto-accepts`, and `auto-reconcile` only creates proposals.
   * **API equivalent** — the same entry the integration test registers, which is useful when the dialog is unavailable. Expect HTTP 201:

     ```bash
     curl -sS -X POST http://127.0.0.1:8017/api/v1/projects/v5-manual-review/reconciliation/mapping-registry \
       -H 'Content-Type: application/json' \
       -d '{"entity_name": "site", "target_field": "site_name", "spec": {"remote": {"service_type": "site"}}}'
     ```

   * **Save the project before review.** `POST .../auto-reconcile` refuses a dirty project with `Project '<name>' has unsaved changes. Save or discard changes before starting reconciliation.`

   #### V-5 business-key rule

   `backend/app/services/project_service.py::_validate_business_key_write` rejects a save that changes an entity's `keys` once the project has a `data_provider_code` and `provider_schema`. Two errors can appear for one save:

   * `An assigned provider-schema pair keeps its declared business keys; change from [] to [...] requires a new provider schema code or an explicit identity migration.` — the entity's keys differ from the saved file.
   * `Project '<name>' shares provider-schema pair '<code>' / '<schema>' and declares different business keys for '<entity>'; a shared scope needs one reviewed key meaning.` — the same comparison run against every project on that pair, which includes the project's own saved file.

   The rule protects the identity scope: a registered pair maps to a SIMS scope name such as `provider://mal/archeobotany/mal`, and business keys are what make a row's identity mean the same thing inside that scope. Creating a project is the only write that may declare the keys, so declare them in the create request. A project already saved with the wrong `keys` cannot be repaired by another save; delete it with `DELETE /api/v1/projects/{name}` and recreate it from the request above.

5. **Check persistence and unchanged export.** Record the SHA-256 hash of the project's `<project-name>-mapping.yml` sidecar, then reload the project, confirm all four decisions persisted, and export again. Expect zero exported or removed links/approvals and the same sidecar hash. See [Where the sidecar is](#where-the-sidecar-is).

   #### Where the sidecar is

   The mapping sidecar is not created with the project. `Export to Mapping` in step 4 creates it, so the file exists only after that export. `src/reconciliation/mapping_manager.py::_sidecar_path` places it in the project directory and names it after that directory, not after the `metadata.name` value:

   ```text
   <projects-dir>/<project-dir-name>/<project-dir-name>-mapping.yml
   ```

   For V-5 the project directory is `<projects-dir>/v5-manual-review`, so with `SHAPE_SHIFTER_PROJECTS_DIR=tmp/v5-projects` the file resolves under `data/`:

   ```text
   /data/roger/source/sead_shape_shifter/data/tmp/v5-projects/v5-manual-review/v5-manual-review-mapping.yml
   ```

   That directory also holds two files the sidecar is not:

   * `shapeshifter.yml` — the project itself.
   * `v5-manual-review-reconciliation.yml` — the reconciliation catalog created by step 4.

   List the directory and hash the sidecar before and after the second export:

   ```bash
   cd /data/roger/source/sead_shape_shifter/data/tmp/v5-projects/v5-manual-review
   ls -la
   shasum -a 256 v5-manual-review-mapping.yml
   ```

   If `v5-manual-review-mapping.yml` is missing, the step 4 export did not write it. Do not record a hash for a missing file and do not continue to step 6; re-run the export and record the outcome instead.

   The hash is expected to repeat because the export writes the sidecar only when a link or approval actually changes (`export_to_mapping` calls `MappingManager.save` inside `if exported or removed or exported_local_only_approvals or removed_local_only_approvals`), and `metadata.updated_at` is only rewritten on that same save. A hash that changes with zero reported counts means the second export wrote something, so inspect `git diff`-style differences or the file timestamps before recording the step as passed.

6. **Check outage and recovery.** Change `accepted` to **Reject** and export to remove its link. Accept candidate ID `1` again, but do not export yet. Stop only the Authority Service process with Ctrl+C; leave Shape Shifter and Podman running. Export while the service is down. Record the unverified outcome and reason; confirm the sidecar has `verified_at: null` and the row source shows `reconciliation · unverified`. Restart the Authority Service with `make serve` in its existing environment, confirm readiness returns `ready: true`, and export again. Confirm `verified_at` is populated and the row source shows `reconciliation · verified …`.

7. **Record the result.** Record the date, unique project name, row statuses, export counts, outage reason, and verified/unverified UI and sidecar observations in the execution record. If any observation differs, record V-5 as failed and leave T3.2 incomplete. Do not run ingestion or deploy an artifact. If cleanup is needed, delete only the unique V-5 project. Deleting the project leaves its `state/authorization-dev.sqlite3` resource record behind; that leftover record is local development data and needs no cleanup for V-5.

The Authority Service unit baseline also passed on 2026-10-31: `.venv/bin/pytest -o addopts='' -q tests/api/test_readiness.py tests/api/test_candidate_verification.py tests/identity/test_reconciliation_contract_integration.py` returned **25 passed, 5 skipped**. The five skipped database tests are not evidence of adoption or approved binding. The Phase 5 task plan records a prior helper bootstrap discrepancy; the current disposable database was rechecked after schema deployment and passed the match-function, materialized-site, allocator, and readiness preflights.

**Execution record (V-1 to V-4 on 2026-10-31; V-5 and T3.2 completed 2026-11-04):**

| Check | Result |
| --- | --- |
| `V-1` | Passed before implementation: `.venv/bin/pytest -q backend/tests/api/v1/test_reconciliation_decisions.py backend/tests/api/v1/test_reconciliation_export.py backend/tests/ingesters/test_sead_change_request_orchestration.py backend/tests/services/test_project_ingester_service.py tests/process/test_shapeshifter.py`. |
| `V-2` | `346 passed, 6 skipped`: `uv run pytest -o addopts='' -q backend/tests/api/v1/test_reconciliation_decisions.py backend/tests/api/v1/test_reconciliation_export.py backend/tests/ingesters/test_sead_change_request_orchestration.py backend/tests/ingesters/test_sead_change_request_runtime.py backend/tests/services/test_project_ingester_service.py tests/process/test_shapeshifter.py backend/tests/integration/test_site_reconciliation_end_to_end.py backend/tests/ingesters/test_sead_change_request_ingester.py backend/tests/ingesters/test_sead_change_request_input_resolution.py backend/tests/ingesters/test_sead_change_request_identity_resolution.py`. Four opted-in live scenarios and two optional disposable database runtime tests skip when their environment variables are unset; the health-only readiness, owner-handoff, binding, and sequence-reservation unit tests run. |
| `V-3` | **5 passed, zero skipped**: `SIMS_INTEGRATION_DB=1 .venv/bin/pytest -o addopts='' -q -s backend/tests/integration/test_site_reconciliation_end_to_end.py -m integration`, against the helper-owned Podman database at `127.0.0.1:55432/sead_staging` and Authority Service at `http://127.0.0.1:8000`, using a temporary mode-600 `PGPASSFILE`. The output recorded adopted site `site_id=1`, local-only allocation `site_id=6504`, package `sample_group_id=13962`, `method_id=3`, Core child `site_id=10001`, and package child FKs `site_id=1`, `method_id=3`. The suite covered review/export, two offline normalizations, SIMS binding/allocation, transitions, blocked ingestion, outage/recovery, protected manual/unowned links, and health-only readiness. Earlier sequence-ID and adopted-link binding failures are resolved. |
| `V-4` | **5 passed, zero skipped** from the Authority Service root: `SIMS_INTEGRATION_DB=1 .venv/bin/pytest -o addopts='' -q tests/identity/test_reconciliation_contract_integration.py -m integration`, with the documented loopback settings and a temporary mode-600 `PGPASSFILE`. Four FastAPI lifecycle deprecation warnings were reported. |
| `V-5` | Real operator UI review has been performed. **Date:** 2026-11-04 **Project name:** v5-manual-review **Result:** Passed **Records:** See execution record below under **V-5 Manual Review Runbook Execution Record**. Step 5's unchanged-export assertion is also recorded there with a re-verified `0`-change export and identical sidecar bytes. |
| `V-6` | Black and isort passed for all 15 changed Python deliverables: `backend/app/services/{ingester_runtime,project_ingester_service}.py`, `ingesters/sead_change_request/{contracts,identity_resolution,ingester,input_resolution,orchestration,preparation}.py`, `src/target_model/models.py`, `backend/tests/services/test_project_ingester_service.py`, `backend/tests/ingesters/test_sead_change_request_{identity_resolution,ingester,orchestration,runtime}.py`, and `backend/tests/integration/test_site_reconciliation_end_to_end.py`. `make check-doc-links` reported valid links; `git diff --check` was clean. |
| `V-7` | Not rerun: per user, the previously reported diagnostics were fixed on the published `pyright-error-fixes` branch and are excluded from this plan. |

### V-5 Manual Review Runbook Execution Record

**Date:** 2026-11-04
**Project name:** v5-manual-review
**Result:** Passed

1. SEAD Authority Service:
  ```log
    INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit) <p/>
    INFO:     Started reloader process [1600684] using StatReload <p>
    INFO:     Started server process [1600688] <p/>
    INFO:     Waiting for application startup. <p/>
    2026-11-04 09:04:22.036 | INFO     | main:startup:20 - Starting up application... <p/>
    2026-11-04 09:04:22 | INFO     | Database connection pool initialized successfully <p/>
    2026-11-04 09:04:22 | INFO     | Config Store initialized successfully. <p/>
    2026-11-04 09:04:22 | INFO     | Application startup completed successfully <p/>
    INFO:     Application startup complete. <p/>
    INFO:     127.0.0.1:49910 - "GET /reconcile/readiness?type=site HTTP/1.1" 200 OK <p/>
  ```
2. Shape Shifter Startup

System started normally with the specified environment variables and backend running on port 8017.

  ```bash
   export SHAPE_SHIFTER_ENVIRONMENT=development
   export SHAPE_SHIFTER_TRUSTED_PROXY_AUTH_ENABLED=false
   export SHAPE_SHIFTER_DEVELOPMENT_PRINCIPAL_ID=local-developer
   export SHAPE_SHIFTER_AUTHORIZATION_DATABASE_PATH=state/authorization-dev.sqlite3
   export SHAPE_SHIFTER_PROJECTS_DIR=tmp/v5-projects
   export SHAPE_SHIFTER_RECONCILIATION_SERVICE_URL=http://127.0.0.1:8000
   export SHAPE_SHIFTER_SIMS_SERVICE_URL=http://127.0.0.1:8000
   # uv run sead-authorization dev-bootstrap
   PYTHONPATH=. uv run python backend/app/scripts/authorization.py dev-bootstrap
   make BACKEND_PORT=8017 backend-run
   ```

Frontend also started normally.

   ```bash
   VITE_API_BASE_URL=http://127.0.0.1:8017 make FRONTEND_PORT=5173 frontend-run
   ```

3. Project Creation

  Project created via API request on backend port `8017`.

   **Request:**

   ```bash
   curl -sS -X POST http://127.0.0.1:8017/api/v1/projects \
     -H 'Content-Type: application/json' \
     -d '{
       "name": "v5-manual-review",
       "data_provider_code": "mal",
       "provider_schema": "archeobotany/mal",
       "entities": {
         "data_provider": {
           "type": "fixed",
           "public_id": "data_provider_id",
           "keys": ["data_provider_code"],
           "columns": ["system_id", "data_provider_id", "data_provider_code"],
           "values": [[1, <provider-id>, "mal"]]
         },
         "site": {
           "type": "fixed",
           "public_id": "site_id",
           "keys": ["national_site_identifier"],
           "columns": ["system_id", "site_id", "national_site_identifier", "site_name"],
           "values": [
             [10001, null, "accepted", "<label>"],
             [10002, null, "local", "<label>"],
             [10003, null, "rejected", "<label>"],
             [10004, null, "undecided", "<label>"]
           ]
         }
       }
     }'
   ```

   **Response:**

```json
  {
      "entities": {
          "data_provider": {
              "type": "fixed",
              "public_id": "data_provider_id",
              "keys": [ "data_provider_code" ],
              "columns": [ "system_id", "data_provider_id", "data_provider_code" ],
              "values": [
                  [ 1, 1, "mal" ]
              ]
          },
          "site": {
              "type": "fixed",
              "public_id": "site_id",
              "keys": [ "national_site_identifier" ],
              "columns": [ "system_id", "site_id", "national_site_identifier", "site_name" ],
              "values": [
                  [ 10001, null, "accepted", "<adopted site 1 label>" ],
                  [ 10002, null, "local", "<adopted site 1 label>" ],
                  [ 10003, null, "rejected", "<adopted site 1 label>" ],
                  [ 10004, null, "undecided", "<adopted site 1 label>" ]
              ]
          }
      },
      "options": {},
      "task_list": null,
      "metadata": {
          "name": "v5-manual-review",
          "type": "shapeshifter-project",
          "description": "Project for v5-manual-review",
          "version": "1.0.0",
          "data_provider_code": "mal",
          "provider_schema": "archeobotany/mal",
          "file_path": "/data/roger/source/sead_shape_shifter/data/tmp/v5-projects/v5-manual-review/shapeshifter.yml",
          "entity_count": 2,
          "created_at": null,
          "modified_at": "2026-11-04T11:29:48.053798+00:00",
          "is_valid": true,
          "default_entity": null,
          "target_model": null
      },
      "load_warnings": [],
      "load_errors": []
  }
```

4. **Add the reconciliation specification, then review and export.** 

```bash
λ curl -sS -X POST http://127.0.0.1:8017/api/v1/projects/v5-manual-review/reconciliation/mapping-registry \
  -H 'Content-Type: application/json' \
  -d '{"entity_name": "site", "target_field": "site_name", "spec": {"remote": {"service_type": "site"}}}'
{"version":"3.0","service_url":"http://127.0.0.1:8000","entities":{"site":{"site_name":{"source":null,"property_mappings":{},"remote":{"service_type":"site","columns":[]},"auto_accept_threshold":0.95,"review_threshold":0.7,"mapping":[]}}}}
```

- **Service status online**: CONFIRMED
- **Reconciliation specification added**: CONFIRMED
- **Find Candidate Matches**: CONFIRMED
- **Export to Mapping**: CONFIRMED
- **Sidecar Check**: CONFIRMED

5. **Check persistence and unchanged export.**

   The mapping sidecar existed after the step 4 export. Its hash immediately after step 4 was:

   ```bash
   λ shasum -a 256 v5-manual-review-mapping.yml
   978e7ba1f032216efd7d3624a3235cc2bc50743afc3429f2c421091714e744b9  v5-manual-review-mapping.yml
   ```

   Reloading the project confirmed all four decisions persisted in `v5-manual-review-reconciliation.yml`: `undecided` = `proposed`, `local` = `local-only`, `rejected` = `rejected`, and `accepted` = `accepted` with `target_id: 1` and `candidate_id: https://w3id.org/sead/id/site/1`.

   The unchanged-decision re-export was re-verified on 2026-11-04 against the same project and backend:

   ```bash
   curl -sS -X POST http://127.0.0.1:8017/api/v1/projects/v5-manual-review/reconciliation/site/site_name/export-to-mapping
   {"exported":0,"removed":0,"exported_local_only_approvals":0,"removed_local_only_approvals":0,
    "skipped_manual":0,"entity":"site","field":"site_name",
    "outcomes":[{"local_key_value":"accepted","outcome":"verified","reason":null}]}
   ```

   The sidecar was byte-identical before and after (`diff` reported no differences), and its SHA-256 stayed:

   ```bash
   λ shasum -a 256 v5-manual-review-mapping.yml
   6ce19dbd352edb4c27e20fc7d529b5d2c0be7b1b9c7303caf13e7f6c8a0ba4d2  v5-manual-review-mapping.yml
   ```

   Final sidecar content for `site` (`local_key: national_site_identifier`, `public_id: site_id`):

   ```yaml
   links:
     accepted:
       target_id: 1
       source: reconciliation
       confidence: 1.0
       owner: {entity_name: site, target_field: site_name}
       verified_at: '2026-11-04T13:48:52.952653Z'
   local_only_approvals:
     local:
       owner: {entity_name: site, target_field: site_name}
   ```

   `rejected` and `undecided` appear in neither `links` nor `local_only_approvals`.

   The earlier record hashed `v5-manual-review-reconciliation.yml`, which is the catalog, not the mapping sidecar; that file legitimately changes when the review writes decisions, so it cannot serve as the idempotency check. The check above uses the sidecar the runbook names.

6. **Check outage and recovery.**

- Change `accepted` to **Reject** and export: CONFIRMED (link removed)

SHA256 checksum after change:
```bash
λ shasum -a 256 v5-manual-review-mapping.yml
b76c9264b225ab4287910e1dfe9c11a964e8842c0b07243877acaf8387009919  v5-manual-review-mapping.yml
```
- Re-accept candidate ID `1` for `accepted` **without exporting**, then stop only the Authority Service: CONFIRMED. That unreported link is what makes the next export write an unverified one.
- Export while service is down: OK with warning:
```txt
1 link(s) exported; 0 stale link(s) removed; 0 local-only approval(s) exported; 0 stale local-only approval(s) removed; 0 protected link(s) skipped. Unverified: accepted: The Authority Service is unavailable; this link was exported without verification. Retry export when it is available.
```
SHA256 checksum after export:
```bash
λ shasum -a 256 v5-manual-review-mapping.yml
266ce38b9eeadcda44fe3560cb42a1e03f205a004bfebd6bf5dc1fc020e4834e  v5-manual-review-mapping.yml
```
- Check has `verified_at: null` in sidecar: CONFIRMED
- Check row source shows `reconciliation · unverified`: CONFIRMED
- Restart the Authority Service with `make serve`: OK
- Confirm readiness returns `ready: true`: CONFIRMED
- Export while service is up: OK
- Check has `verified_at` populated in sidecar: CONFIRMED
- Confirm row source shows `reconciliation · verified`: CONFIRMED

   The verifying export changed the sidecar again because the unverified link gained `verified_at`, which is why this hash differs from the unverified one. The current sidecar is the post-verification file recorded in step 5.

7. **Record the result.** Recorded in this execution record. No ingestion was run and no generated artifact was executed. The V-5 project remains under `data/tmp/v5-projects/v5-manual-review` for inspection and can be removed with `DELETE /api/v1/projects/v5-manual-review`.


**V-5 runbook corrections (2026-11-04):** Step 2 previously exported `SHAPE_SHIFTER_AUTHORIZATION_DATABASE_PATH=state/authorization-v5.sqlite3`, which `dev-bootstrap` rejects with `Development bootstrap only writes state/authorization-dev.sqlite3`. The step now uses the supported `state/authorization-dev.sqlite3` path and relies on `SHAPE_SHIFTER_PROJECTS_DIR`, the disposable database, and a unique project name for isolation. Step 3 previously created an empty project in the UI and then added `site.keys`, which a bound project rejects with `An assigned provider-schema pair keeps its declared business keys` and `a shared scope needs one reviewed key meaning`; the step now creates the project with `POST /api/v1/projects` and declares the entity keys in that request, together with the required fixed `data_provider` row. Step 3 also left `<label>` and `<provider-id>` as literal placeholders, which produces `{"type":"json_invalid","loc":["body",388],"msg":"JSON decode error"}`; the step now identifies the values to substitute, creates a disposable provider row because the restored database has no provider rows, and states the `409` conflict on an existing name. Step 4 previously assumed the `site.site_name` specification already existed, so an empty Configuration tab looked like a missed step; it now states that a new project has no reconciliation catalog entry, names the **Add Specification** fields, records the `POST .../reconciliation/mapping-registry` equivalent, and notes that `auto-reconcile` refuses a dirty project. Step 5 previously named the sidecar without saying where it lives; it now gives the `<projects-dir>/<project-dir-name>/<project-dir-name>-mapping.yml` rule, the resolved V-5 path, the files it must not be confused with, and why the hash is expected to repeat. V-5 has since been executed on 2026-11-04 and its result is recorded above.

After the approved schema deployment, the disposable database passed the `authority.fuzzy_site(text,integer)`, materialized-site, and allocator-safety preflights; the real readiness endpoint returned `ready: true`, and the health-only service failed its readiness check. The final live run bound adopted `site_id` **1**, allocated local-only `site_id` **6504**, and generated child `sample_group_id` **13962**. Both offline normalizations returned accepted `site_id` **1**, kept the local-only ID null before ingestion, and produced Core child `site_id` **10001** (the parent's local `system_id`). The generated package used target-facing child FKs `site_id` **1** and `method_id` **3**. The test keeps the site relationship as a Core link and uses `method_id` for the separate direct `public_id` FK. T3.1 transition, blocked-ingestion, outage/recovery, protected-link, and readiness cases all passed. A uniquely named test provider was created only inside the helper-owned disposable database and removed by fixture teardown.

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Live, opted-in cross-service `site` scenarios and preflight | `backend/tests/integration/test_site_reconciliation_end_to_end.py` (**NEW**) | `T1.1`, `T1.2`, `T2.1`, `T2.2`, `T3.1` | `V-3` passes without skips, real services return expected results, and DB/artifact assertions record IDs/FKs. |
| Verified reconciliation handoff and SIMS-backed package generation | `backend/app/services/project_ingester_service.py`; `backend/app/services/ingester_runtime.py`; `ingesters/sead_change_request/{contracts.py,input_resolution.py,ingester.py,preparation.py,orchestration.py,identity_resolution.py}`; `src/target_model/models.py`; focused tests | `T2.2` | `V-2` covers verified owners and accepted links; `V-3` confirms SIMS binding/allocation, reserved child IDs, and actual artifact FKs. |
| MVP validation record and progress | `RECONCILIATION_MVP_PHASE_7_TASK_PLAN.md` (this file) | `T3.2` | `V-3` to `V-6` results, actual ID/FK values, adoption gate, and `VM-14`/`VM-15` outcomes are recorded. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Gate the disposable live environment | Done | Phase 4, adoption | `T1.1` and `T1.2` verified: real match, adoption/allocator checks, and health-only rejection; `V-3` preflight and `V-4` passed. |
| Area 2: Exercise review, export, normalization, and binding | Done | Area 1; Phases 2, 5, 6 | `T2.1` and `T2.2` passed. `V-2` verifies the owner/specification/decision handoff; `V-3` proves two stable offline normalizations, sequence-backed child ID reservation, adopted-site SIMS binding, local-only allocation, and package FKs. |
| Area 3: Cover failures and record the MVP result | Done | Areas 1-2 | `T3.1` passed: `V-3` covers transitions, absent candidates, blocked ingestion, outage/recovery, protected manual/unowned links, and readiness. `T3.2` passed: `V-5` operator review completed on 2026-11-04 with the outcome recorded in **V-5 Manual Review Runbook Execution Record**. |

## Definition Of Done

* [x] `PH7-AC-1` has recorded accepted/local-only/rejected/undecided target IDs and both local and target-facing FK values, with identical unchanged reruns (`VM-14`).
* [x] `PH7-AC-2` has an unskipped database-backed run covering success, approval, blocks, rejection, changed decisions, stale link, absent row, outage, and recovery (`VM-14`).
* [x] `PH7-AC-3` has an unskipped readiness and adopted existing-site binding result, including a health-only failure (`VM-15`).
* [x] All work areas, the new test, and the validation record are complete; the disposable database and temporary project/artifacts were isolated and cleaned up safely. The V-5 project is intentionally retained under `data/tmp/v5-projects` for inspection and can be deleted with `DELETE /api/v1/projects/v5-manual-review`.
* [x] Targeted regression, Authority integration, manual UI check, formatting, and doc-link results are recorded; no skipped live test is reported as passed.
* [x] Offline normalization, manual/unowned protection, `system_id` Core links, sidecar ownership, and ingester approval rules retain coverage.
* [x] Any deviation or follow-up is documented, and no unresolved prerequisite or question affects the MVP result.

## Risks And Open Questions

* **Adoption scope:** The companion adoption proposal remains draft, but this run verified the selected site as materialized in the helper-owned disposable database and confirmed allocator safety. This result applies only to the tested disposable database; it does not establish adoption in another environment.
* **Real-service test isolation:** A successful SIMS resolve creates persistent identities/bindings in the disposable DB. Use unique source keys, scopes, and run IDs; compare the relevant rows across reruns and never point the test at a deployed database. Stop and report if the existing project/target-model contract cannot express the fixture without changing another phase.
