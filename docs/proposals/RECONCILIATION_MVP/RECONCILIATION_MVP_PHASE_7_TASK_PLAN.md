# Reliable Reconciliation Links to Existing SEAD Entities - Phase 7 Task Plan

## Phase Summary

**Phase:** 7 - End-to-End Validation. **Readiness:** Validated for implementation; the live validation and phase completion are gated on verified SIMS adoption of existing `site` rows in the disposable database. The [phase plan](RECONCILIATION_MVP_PHASE_PLAN.md#phase-7-end-to-end-validation) marks this phase ready for a task plan, not already complete.

**Goal:** Prove that reviewed `site` decisions produce the intended normalized IDs, child foreign keys, and change-request results against a database-backed Authority Service and SIMS, including reruns and failures.

**Sources:** [Shape Shifter proposal](RECONCILIATION_MVP.md) (`SS-AC-1`, `SS-AC-8`), [phase plan](RECONCILIATION_MVP_PHASE_PLAN.md) (`VM-14`, `VM-15`), and the [Authority Service contract](https://github.com/humlab-sead/sead_authority_service/blob/main/docs/proposals/RECONCILIATION_IDENTITY_CONTRACT/RECONCILIATION_IDENTITY_CONTRACT.md) (`AS-AC-6`). Existing-site [adoption](https://github.com/humlab-sead/sead_authority_service/blob/main/docs/proposals/SIMS_EXISTING_SITE_ADOPTION.md) is a prerequisite owned by Roger Mähler, not work in this plan.

**Acceptance criteria**

1. [ ] `PH7-AC-1` (from `SS-AC-1`): A reviewed `site` workflow sets the intended `public_id` and foreign-key values; unchanged review, export, and normalization reruns give identical results.
2. [ ] `PH7-AC-2` (from `SS-AC-8`): One database-backed end-to-end test covers success, local-only approval, undecided-row block, rejection, rerun, changed decision, stale link, absent row, and unavailable service.
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
* [ ] `T3.2` **Change:** Record live validation and manual review results without calling a skipped run a pass.
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
| `V-5` | Operator review through the real UI, not just mocked Vue tests | Follow the [V-5 manual review runbook](#v-5-manual-review-runbook) below. It uses backend port `8013` and points Vite at that port. | `PH7-AC-1`, `PH7-AC-2` | Operator sees the same candidate, decisions, failures, and status as the real API; no automatic acceptance. | Not run: no manual browser review was performed; UI validation remains outstanding. |
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
   make serve
   ```

   Keep `PGPASSFILE` set to the temporary mode-600 password file used for the disposable database. Do not copy its password into `.env` or this plan.

   From another terminal, confirm readiness:

   ```bash
   curl -fsS 'http://127.0.0.1:8000/reconcile/readiness?type=site'
   ```

   Continue only if the helper reports the container running and readiness returns `ready: true`.

2. **Start Shape Shifter with isolated local state.** In a Shape Shifter terminal, set:

   ```bash
   export SHAPE_SHIFTER_ENVIRONMENT=development
   export SHAPE_SHIFTER_TRUSTED_PROXY_AUTH_ENABLED=false
   export SHAPE_SHIFTER_DEVELOPMENT_PRINCIPAL_ID=local-developer
   export SHAPE_SHIFTER_AUTHORIZATION_DATABASE_PATH=state/authorization-v5.sqlite3
   export SHAPE_SHIFTER_PROJECTS_DIR=tmp/v5-projects
   export SHAPE_SHIFTER_RECONCILIATION_SERVICE_URL=http://127.0.0.1:8000
   export SHAPE_SHIFTER_SIMS_SERVICE_URL=http://127.0.0.1:8000
   uv run sead-authorization dev-bootstrap
   make BACKEND_PORT=8013 backend-run
   ```

   In another Shape Shifter terminal, start the frontend:

   ```bash
   VITE_API_BASE_URL=http://127.0.0.1:8013 make FRONTEND_PORT=5173 frontend-run
   ```

   Open `http://127.0.0.1:5173`. Keep the Authority Service and Podman database running.

3. **Create a disposable project.** In **Projects → New Project**, choose an already registered provider/schema and a unique project name. Use the `site` fixture shape from `backend/tests/integration/test_site_reconciliation_end_to_end.py`: a fixed `site` entity with `public_id: site_id`, business key `national_site_identifier`, and four rows keyed `accepted`, `local`, `rejected`, and `undecided`. Set each `site_id` to null and each `site_name` to the label for adopted site ID `1`. Obtain the label locally from the disposable database:

   ```bash
   cd /data/roger/source/sead_authority_service
   printf 'SELECT site_id, label FROM authority.site WHERE site_id = 1;\n' \
     | scripts/verify_sims_identity_candidates.sh sql -
   ```

   Configure a reconciliation specification for `site.site_name` with service type `site`. Do not copy the label or credentials into this plan.

4. **Review and export.** Open the project's **Reconcile** tab, then **Configuration**. Open the `site.site_name` specification and select **Reconcile**. In **Reconcile & Review**, confirm the service status is online and click **Find Candidates**. Explicitly accept candidate ID `1` for `accepted`, mark `local` **Local-only**, reject `rejected`, and leave `undecided` proposed. Export to Mapping. Check the sidecar: the accepted link has target ID `1`, owner `(site, site_name)`, and a non-empty `verified_at`; the local-only row has a separate owned approval and no target ID; rejected and undecided have no link or approval.

5. **Check persistence and unchanged export.** Record the SHA-256 hash of the project's `<project-name>-mapping.yml` sidecar. Reload the project, confirm all four decisions persisted, and export again. Expect zero exported or removed links/approvals and the same sidecar hash.

6. **Check outage and recovery.** Change `accepted` to **Reject** and export to remove its link. Accept candidate ID `1` again, but do not export yet. Stop only the Authority Service process with Ctrl+C; leave Shape Shifter and Podman running. Export while the service is down. Record the unverified outcome and reason; confirm the sidecar has `verified_at: null` and the row source shows `reconciliation · unverified`. Restart the Authority Service with `make serve` in its existing environment, confirm readiness returns `ready: true`, and export again. Confirm `verified_at` is populated and the row source shows `reconciliation · verified …`.

7. **Record the result.** Record the date, unique project name, row statuses, export counts, outage reason, and verified/unverified UI and sidecar observations in the execution record. If any observation differs, record V-5 as failed and leave T3.2 incomplete. Do not run ingestion or deploy an artifact. If cleanup is needed, delete only the unique V-5 project.

The Authority Service unit baseline also passed on 2026-10-31: `.venv/bin/pytest -o addopts='' -q tests/api/test_readiness.py tests/api/test_candidate_verification.py tests/identity/test_reconciliation_contract_integration.py` returned **25 passed, 5 skipped**. The five skipped database tests are not evidence of adoption or approved binding. The Phase 5 task plan records a prior helper bootstrap discrepancy; the current disposable database was rechecked after schema deployment and passed the match-function, materialized-site, allocator, and readiness preflights.

**Execution record (2026-10-31; T2.2 and T3.1 complete, Phase 7 still partial):**

| Check | Result |
| --- | --- |
| `V-1` | Passed before implementation: `.venv/bin/pytest -q backend/tests/api/v1/test_reconciliation_decisions.py backend/tests/api/v1/test_reconciliation_export.py backend/tests/ingesters/test_sead_change_request_orchestration.py backend/tests/services/test_project_ingester_service.py tests/process/test_shapeshifter.py`. |
| `V-2` | `346 passed, 6 skipped`: `uv run pytest -o addopts='' -q backend/tests/api/v1/test_reconciliation_decisions.py backend/tests/api/v1/test_reconciliation_export.py backend/tests/ingesters/test_sead_change_request_orchestration.py backend/tests/ingesters/test_sead_change_request_runtime.py backend/tests/services/test_project_ingester_service.py tests/process/test_shapeshifter.py backend/tests/integration/test_site_reconciliation_end_to_end.py backend/tests/ingesters/test_sead_change_request_ingester.py backend/tests/ingesters/test_sead_change_request_input_resolution.py backend/tests/ingesters/test_sead_change_request_identity_resolution.py`. Four opted-in live scenarios and two optional disposable database runtime tests skip when their environment variables are unset; the health-only readiness, owner-handoff, binding, and sequence-reservation unit tests run. |
| `V-3` | **5 passed, zero skipped**: `SIMS_INTEGRATION_DB=1 .venv/bin/pytest -o addopts='' -q -s backend/tests/integration/test_site_reconciliation_end_to_end.py -m integration`, against the helper-owned Podman database at `127.0.0.1:55432/sead_staging` and Authority Service at `http://127.0.0.1:8000`, using a temporary mode-600 `PGPASSFILE`. The output recorded adopted site `site_id=1`, local-only allocation `site_id=6504`, package `sample_group_id=13962`, `method_id=3`, Core child `site_id=10001`, and package child FKs `site_id=1`, `method_id=3`. The suite covered review/export, two offline normalizations, SIMS binding/allocation, transitions, blocked ingestion, outage/recovery, protected manual/unowned links, and health-only readiness. Earlier sequence-ID and adopted-link binding failures are resolved. |
| `V-4` | **5 passed, zero skipped** from the Authority Service root: `SIMS_INTEGRATION_DB=1 .venv/bin/pytest -o addopts='' -q tests/identity/test_reconciliation_contract_integration.py -m integration`, with the documented loopback settings and a temporary mode-600 `PGPASSFILE`. Four FastAPI lifecycle deprecation warnings were reported. |
| `V-5` | **Not run**: no real operator UI review was performed; manual review remains outstanding. |
| `V-6` | Black and isort passed for all 15 changed Python deliverables: `backend/app/services/{ingester_runtime,project_ingester_service}.py`, `ingesters/sead_change_request/{contracts,identity_resolution,ingester,input_resolution,orchestration,preparation}.py`, `src/target_model/models.py`, `backend/tests/services/test_project_ingester_service.py`, `backend/tests/ingesters/test_sead_change_request_{identity_resolution,ingester,orchestration,runtime}.py`, and `backend/tests/integration/test_site_reconciliation_end_to_end.py`. `make check-doc-links` reported valid links; `git diff --check` was clean. |
| `V-7` | Not rerun: per user, the previously reported diagnostics were fixed on the published `pyright-error-fixes` branch and are excluded from this plan. |

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
| Area 3: Cover failures and record the MVP result | In progress | Areas 1-2 | `T3.1` passed: `V-3` covers transitions, absent candidates, blocked ingestion, outage/recovery, protected manual/unowned links, and readiness. `T3.2` remains incomplete because `V-5` manual UI review has not been run. |

## Definition Of Done

* [ ] `PH7-AC-1` has recorded accepted/local-only/rejected/undecided target IDs and both local and target-facing FK values, with identical unchanged reruns (`VM-14`).
* [ ] `PH7-AC-2` has an unskipped database-backed run covering success, approval, blocks, rejection, changed decisions, stale link, absent row, outage, and recovery (`VM-14`).
* [x] `PH7-AC-3` has an unskipped readiness and adopted existing-site binding result, including a health-only failure (`VM-15`).
* [ ] All work areas, the new test, and the validation record are complete; the disposable database and temporary project/artifacts were isolated and cleaned up safely.
* [ ] Targeted regression, Authority integration, manual UI check, formatting, and doc-link results are recorded; no skipped live test is reported as passed.
* [ ] Offline normalization, manual/unowned protection, `system_id` Core links, sidecar ownership, and ingester approval rules retain coverage.
* [ ] Any deviation or follow-up is documented, and no unresolved prerequisite or question affects the MVP result.

## Risks And Open Questions

* **Adoption scope:** The companion adoption proposal remains draft, but this run verified the selected site as materialized in the helper-owned disposable database and confirmed allocator safety. This result applies only to the tested disposable database; it does not establish adoption in another environment.
* **Real-service test isolation:** A successful SIMS resolve creates persistent identities/bindings in the disposable DB. Use unique source keys, scopes, and run IDs; compare the relevant rows across reruns and never point the test at a deployed database. Stop and report if the existing project/target-model contract cannot express the fixture without changing another phase.
