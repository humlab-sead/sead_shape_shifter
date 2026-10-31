# Reliable Reconciliation Links to Existing SEAD Entities - Phase 7 Task Plan

## Phase Summary

**Phase:** 7 - End-to-End Validation. **Readiness:** Validated for implementation; the live validation and phase completion are gated on verified SIMS adoption of existing `site` rows in the disposable database. The [phase plan](RECONCILIATION_MVP_PHASE_PLAN.md#phase-7-end-to-end-validation) marks this phase ready for a task plan, not already complete.

**Goal:** Prove that reviewed `site` decisions produce the intended normalized IDs, child foreign keys, and change-request results against a database-backed Authority Service and SIMS, including reruns and failures.

**Sources:** [Shape Shifter proposal](RECONCILIATION_MVP.md) (`SS-AC-1`, `SS-AC-8`), [phase plan](RECONCILIATION_MVP_PHASE_PLAN.md) (`VM-14`, `VM-15`), and the [Authority Service contract](https://github.com/humlab-sead/sead_authority_service/blob/main/docs/proposals/RECONCILIATION_IDENTITY_CONTRACT/RECONCILIATION_IDENTITY_CONTRACT.md) (`AS-AC-6`). Existing-site [adoption](https://github.com/humlab-sead/sead_authority_service/blob/main/docs/proposals/SIMS_EXISTING_SITE_ADOPTION.md) is a prerequisite owned by Roger Mähler, not work in this plan.

**Acceptance criteria**

1. [ ] `PH7-AC-1` (from `SS-AC-1`): A reviewed `site` workflow sets the intended `public_id` and foreign-key values; unchanged review, export, and normalization reruns give identical results.
2. [ ] `PH7-AC-2` (from `SS-AC-8`): One database-backed end-to-end test covers success, local-only approval, undecided-row block, rejection, rerun, changed decision, stale link, absent row, and unavailable service.
3. [ ] `PH7-AC-3` (from `SS-AC-8`, `AS-AC-6`): A health-only service cannot pass readiness; an approved existing `site` binds through SIMS after adoption.

**Dependencies and constraints:** Use the Phase 2 review, Phase 5 verified export, Phase 6 approvals/ingester rule, and Phase 4 SIMS binding rule. Do not start the live run before the Authority Service's disposable database has the real `site` match function, an existing SEAD site is adopted as `materialized`, and the `site` allocator is above existing IDs. Keep normalization offline, review explicit, existing manual/unowned links protected, and Core child FKs based on local `system_id`; only a declared change-request `foreign_key_value_sources.<target>: public_id` can use a target ID in a package FK.

## Repository Findings

**Repository basis:** Shape Shifter branch `reconciliation-mvp` at `6e8f788e`; Authority Service branch `dev` at `0e2d5e9`; inspected 2026-10-31. The uncommitted phase plan (including the named adoption owner and Phase 7 readiness) was considered. Other uncommitted files were not used as implementation evidence. Graphify was used for navigation; the file-level paths below were checked against current source and tests.

| Verified source | Current behavior | Planning implication |
| --- | --- | --- |
| `backend/app/api/v1/endpoints/reconciliation.py::{auto_reconcile_entity, update_mapping, export_reconciliation_to_mapping}`; `backend/tests/api/v1/{test_reconciliation_decisions,test_reconciliation_export}.py` | The project routes create proposals, persist per-key operator decisions, and export accepted links/local-only approvals. Existing route tests use an authorized, API-created project; export tests stub candidate verification. | Drive the real review and export routes on an isolated project, but do not replace the live Authority Service call with a mock in the end-to-end test. Check export response **and** committed sidecar. |
| `src/normalizer.py::ShapeShifter`; `backend/tests/api/v1/test_reconciliation_export.py::test_exported_links_normalize_offline_with_stable_parent_ids_and_child_foreign_keys` | A committed link changes the site's `site_id`; a local-only approval does not write an ID. The sample's Core `site_id` FK contains the parent's `system_id`, not the SEAD `site_id`. | Assert actual keyed `site_id` and local child FK values on two offline normalizations; separately check target-facing package FKs if a `public_id` source is declared. |
| `backend/app/services/project_ingester_service.py::{validate_project_tables, ingest_project_tables, _attach_local_only_approvals}`; `ingesters/sead_change_request/ingester.py::SeadChangeRequestIngester` | Authorized project ingestion normalizes again, passes committed approvals as trusted metadata, and creates a change-request bundle; missing approvals cannot authorize allocation. | Exercise the saved-project validate/ingest path and inspect generated assignments/artifacts, not only an ingester with hand-built tables. Use separate isolated projects/runs for blocked and successful cases. |
| `backend/app/services/ingester_runtime.py::SeadChangeRequestSimsAdapter`; `backend/app/core/config.py`; `backend/tests/ingesters/{test_sead_change_request_orchestration,test_sead_change_request_direct_fk_postgres}.py` | The adapter calls the configured SIMS URL; target-row checks use PostgreSQL. Reconciled local-only rows allocate only with permitted modes; a declared direct target-ID FK is checked against the target database. | Configure both service URLs and the ingester target connection to the same disposable environment. Assert SIMS-approved existing ID, allocated local-only ID, and package FK independently of the Core FK. |
| Authority Service `src/api/router.py::{reconciliation_readiness, verify_candidates}`; `tests/identity/test_reconciliation_contract_integration.py`; `tests/api/test_readiness.py` | Readiness runs the database-backed `site` match path; the integration test covers real candidate existence and approved-ID binding, but skips without `SIMS_INTEGRATION_DB=1` and its loopback DB configuration. | Require a positive readiness result and a real match before review; explicitly test that health/manifest alone do not satisfy the preflight. Run the existing Authority integration file with its opt-in. |
| Authority Service `scripts/verify_sims_identity_candidates.sh`; `docs/DEVELOPMENT.md` | The helper restores a loopback-only database at `127.0.0.1:55432/sead_staging`; `bootstrap site` adds materialized identities and initializes the allocator, but its preflight rejects inconsistent SIMS/SEAD IDs. | Use the documented helper only against an authorized disposable copy. Verify adoption and allocator results before the live test; stop and report a bootstrap discrepancy rather than repairing or targeting staging/production. |
| `backend/tests/integration/test_reconciliation_client.py`; `backend/tests/conftest.py`; `frontend/src/components/reconciliation/__tests__/{ReconciliationGrid,ReconciliationView}.test.ts` | Existing live-client checks may skip on connection errors; authenticated project tests use `authorized_client`; UI tests use mocked responses. | Add a dedicated opt-in end-to-end test that fails rather than reporting success when prerequisites are missing, plus a manual real-UI check. Do not mistake mocked tests or skipped live checks for `VM-14`. |

## Scope

**In scope:** An isolated `site` project and child-row fixture; one new live cross-service test module; readiness/adoption gate; real API review, export, offline normalization, project-based change-request generation, and sidecar/artifact/DB assertions; a recorded manual UI check and validation results in this plan.

**Out of scope:** Production or staging writes, implementing the separate SIMS adoption proposal, changing service contracts, adding new entity types, changing normalization or the ingester, SEAD cutover, or silently repairing a disposable database that fails preflight.

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

**Affected code:** `backend/tests/integration/test_site_reconciliation_end_to_end.py` (**NEW**); existing route, normalizer, and ingester interfaces above.

**Dependencies:** Area 1; Phase 2, Phase 5, and Phase 6 outputs.

* [x] `T2.1` **Change:** Drive actual per-key decisions and export through the saved project.
  * **Target:** `backend/tests/integration/test_site_reconciliation_end_to_end.py` (**NEW**).
  * **Current → required:** Separate route tests mock verification → create a site fixture with distinct business keys (including two rows with the same search label), a child using a Core FK, and a reconciliation specification using the real `site` service. Auto-reconcile to proposals; explicitly accept the returned candidate URI/ID for one key, mark another local-only, and leave/reject separate keys. Export through the project endpoint.
  * **Implementation:** Assert decision states survive review rerun, accepted `site_id`/URI correspond to the real SEAD row, exported link has correct owner and `verified_at`, local-only has a separate owned approval and no ID link, and rejected/undecided keys have neither. Save catalog and sidecar snapshots, re-export unchanged decisions, and compare effective entries without treating timestamps as IDs.
  * **Constraints:** No auto-accept; do not infer candidate URIs from numeric IDs. Reuse API-created project authorization and version-checked export.
  * **Validation:** `V-2`, `V-3`; acceptance is tied to the intended business key, not the shared label.
* [ ] `T2.2` **Change:** Check two offline normalizations and a real SIMS-backed change-request run.
  * **Target:** `backend/tests/integration/test_site_reconciliation_end_to_end.py` (**NEW**).
  * **Current → required:** Unit tests prove offline linking or mocked SIMS allocation in isolation → run `ShapeShifter.normalize()` twice on the saved project with HTTP disabled for the normalization calls, then invoke authorized project validation/ingestion with real SIMS and disposable target-row checks.
  * **Implementation:** Record keyed `site.public_id` values: accepted equals the verified SEAD `site_id`, local-only stays null until ingester allocation, rejected/undecided stay without an exported ID. Assert child Core `site_id` equals the parent's local `system_id` on both runs. In isolated successful ingester runs, assert SIMS returns/binds the adopted existing ID, allocates a different collision-free ID for the local-only approval, and the generated change-request artifact contains the expected target-facing IDs and child FK values. If a package FK uses an existing target ID, declare `foreign_key_value_sources.<target>: public_id` and assert that lookup against the disposable target succeeds; never compare this package value to the Core FK.
  * **Constraints:** Use separate scope/run IDs for scenarios whose decisions change; replay the same run ID only for the unchanged idempotency case. Do not execute a generated deploy artifact against a non-disposable database.
  * **Validation:** `V-2`, `V-3`, `V-4`; report actual IDs and FK values, not just row counts or mocked responses.

**Completion evidence:** Recorded per-key normalized IDs and local FKs are identical on unchanged reruns; the generated artifact and SIMS outcomes show the adopted existing ID and separately allocated local-only ID.

### Area 3: Cover failures and record the MVP result

**Objective:** Negative and transition cases cannot create unintended links, approvals, SIMS allocations, or successful artifacts.

**Affected code:** `backend/tests/integration/test_site_reconciliation_end_to_end.py` (**NEW**); this task plan for the validation record.

**Dependencies:** Areas 1-2.

* [ ] `T3.1` **Change:** Extend the same test module with isolated transition and failure scenarios.
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
| `PH7-AC-2` (`SS-AC-8`) | `T2.1`, `T2.2`, `T3.1`, `T3.2` | `V-2`, `V-3`, `V-5` | One opted-in end-to-end module executes the positive and all named negative/transition cases without mocking the positive service paths. |
| `PH7-AC-3` (`SS-AC-8`, `AS-AC-6`) | `T1.1`, `T1.2`, `T2.2`, `T3.2` | `V-3`, `V-4` | Health-only readiness rejected, real DB-backed match accepted, adopted `materialized` existing ID bound by SIMS. |

## Validation And Testing

Prepare only a helper-owned disposable database: follow the Authority Service [development procedure](https://github.com/humlab-sead/sead_authority_service/blob/main/docs/DEVELOPMENT.md#disposable-database-for-integration-tests) (`dump --yes`, `setup`, `bootstrap site`, `credentials`) **with authorized source data**. Do not run these commands against staging/production or store credentials in this plan. Configure the documented `SEAD_AUTHORITY_OPTIONS_DATABASE_*` variables for `127.0.0.1:55432/sead_staging`, start the Authority Service with its documented `make serve`, and set the Shape Shifter service/ingest settings to that disposable environment. If bootstrap reports an ID discrepancy, stop and record it; do not repair it in this phase. The new test must check these prerequisites itself after opt-in.

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
| --- | --- | --- | --- | --- | --- |
| `V-1` | Current Shape Shifter review, export, ingester, and offline regression | `.venv/bin/pytest -q backend/tests/api/v1/test_reconciliation_decisions.py backend/tests/api/v1/test_reconciliation_export.py backend/tests/ingesters/test_sead_change_request_orchestration.py backend/tests/services/test_project_ingester_service.py tests/process/test_shapeshifter.py` | Phase dependencies and `PH7-AC-1` regression | Existing behavior preserved; does not by itself prove Phase 7. | Pass (2026-10-31; targeted suite completed). |
| `V-2` | Extend focused regression for new cross-service assertions; `backend/tests/integration/test_site_reconciliation_end_to_end.py` (**NEW**) | Run the `V-1` command again after implementation, plus focused new tests without their live opt-in to confirm they skip only in ordinary collection. | `PH7-AC-1`, `PH7-AC-2` | Existing tests pass; ordinary collection cannot access a live DB. | Not run: new file does not exist. |
| `V-3` | Opted-in end-to-end review/export/normalization/ingest and readiness; `backend/tests/integration/test_site_reconciliation_end_to_end.py` (**NEW**) | From Shape Shifter root, with the documented disposable DB and live Authority Service: `SIMS_INTEGRATION_DB=1 .venv/bin/pytest -o addopts='' -q backend/tests/integration/test_site_reconciliation_end_to_end.py -m integration`. Inspect the pytest summary for **zero skipped** tests. | `PH7-AC-1` to `PH7-AC-3`; `VM-14`, `VM-15` | All named cases pass with actual IDs/FKs; missing adoption, health-only service, or broken matching fails explicitly. | Not run: test and disposable live prerequisites not provisioned for planning. |
| `V-4` | Authority Service real candidate/readiness/approved-binding contract; `tests/identity/test_reconciliation_contract_integration.py` | From Authority Service root with the documented helper-owned DB: `SIMS_INTEGRATION_DB=1 .venv/bin/pytest -o addopts='' -q tests/identity/test_reconciliation_contract_integration.py -m integration`; inspect summary for **zero skipped**. | `PH7-AC-3`; `AS-AC-6`, `VM-15` | Real match, absent candidate, missing-function readiness, adopted-ID binding, and state checks pass. | Not run live: without opt-in, the baseline invocation reported 5 skips. |
| `V-5` | Operator review through the real UI, not just mocked Vue tests | Start Shape Shifter with `make backend-run` and `make frontend-run`, and Authority Service with `make serve` against the disposable DB. In a disposable project, reconcile `site`, review each status, export, reload, repeat, disable/re-enable the service, and verify visible IDs, reasons, and unverified/verified state against the sidecar and `V-3` results. | `PH7-AC-1`, `PH7-AC-2` | Operator sees the same candidate, decisions, failures, and status as the real API; no automatic acceptance. | Not run: live environment not provisioned for planning. |
| `V-6` | Test formatting and task-plan links | After implementation: `uv run black --check backend/tests/integration/test_site_reconciliation_end_to_end.py`; `make check-doc-links`. | Deliverables and documentation | Formatting and local links pass; record any existing unrelated failure separately. | Partial: `make check-doc-links` passed after writing this plan; Black not run because the new test does not yet exist. |

The Authority Service unit baseline also passed on 2026-10-31: `.venv/bin/pytest -o addopts='' -q tests/api/test_readiness.py tests/api/test_candidate_verification.py tests/identity/test_reconciliation_contract_integration.py` returned **25 passed, 5 skipped**. The five skipped database tests are not evidence of adoption or approved binding. The Phase 5 task plan records a prior helper bootstrap discrepancy; recheck it in the chosen disposable database before claiming readiness.

**Execution record (2026-10-31; partial, not an MVP pass):**

| Check | Result |
| --- | --- |
| `V-1` | Passed before implementation: `.venv/bin/pytest -q backend/tests/api/v1/test_reconciliation_decisions.py backend/tests/api/v1/test_reconciliation_export.py backend/tests/ingesters/test_sead_change_request_orchestration.py backend/tests/services/test_project_ingester_service.py tests/process/test_shapeshifter.py`. |
| `V-2` | `144 passed, 3 skipped`: `.venv/bin/pytest -o addopts='' -q backend/tests/api/v1/test_reconciliation_decisions.py backend/tests/api/v1/test_reconciliation_export.py backend/tests/ingesters/test_sead_change_request_orchestration.py backend/tests/services/test_project_ingester_service.py tests/process/test_shapeshifter.py backend/tests/integration/test_site_reconciliation_end_to_end.py`. The three live cases skip without opt-in; the health-only test runs. |
| `V-3` | **Failed (3 passed, 1 failed, zero skipped)**: `SIMS_INTEGRATION_DB=1 .venv/bin/pytest -o addopts='' -q backend/tests/integration/test_site_reconciliation_end_to_end.py -m integration`, with `SEAD_DISPOSABLE_POSTGRES_*`, `SEAD_DISPOSABLE_AUTHORITY_URL`, and a local password-file-equivalent connection set for the helper-owned `127.0.0.1:55432/sead_staging`. `test_adopted_binding_and_local_only_allocation` stops during project validation: `Local-only approval for 'site' key 'local' has an invalid owner`. Export owns this approval as `site.site_name`, while `SeadChangeRequestIngester._validate_local_only_approvals` requires `site.site_id`. No successful SIMS allocation or package ID/FK result was recorded. |
| `V-4` | **Passed (5 passed, zero skipped)** from the Authority Service root: `SIMS_INTEGRATION_DB=1 .venv/bin/pytest -o addopts='' -q tests/identity/test_reconciliation_contract_integration.py -m integration`, with its documented loopback connection configured. This does not resolve the Shape Shifter owner mismatch. |
| `V-5` | **Not run**: no real operator UI review was performed; the end-to-end ingester path is blocked. |
| `V-6` | Passed: `uv run black --check backend/tests/integration/test_site_reconciliation_end_to_end.py` after formatting and `make check-doc-links` (valid local links). |

The helper-owned database had `authority.fuzzy_site(text,integer)`, 3,462 adopted materialized `site` identities, and `site` allocator next ID 6491 above maximum existing site ID 6486. The real readiness endpoint returned `ready: true`; a health-only service with a working manifest failed the test preflight. The review/export test verified accepted target `site_id` **1**, null local-only/rejected/undecided site IDs, and a Core child `site_id` of **10001** (its parent's distinct local `system_id`) on two offline runs. It also checked per-key decisions, unchanged re-export, owner-tagged link/approval, stale-link removal, and an absent candidate. No target-facing package FK or local-only allocated ID has been demonstrated. A uniquely named test provider was created only inside the helper-owned disposable database and removed by fixture teardown.

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Live, opted-in cross-service `site` scenarios and preflight | `backend/tests/integration/test_site_reconciliation_end_to_end.py` (**NEW**) | `T1.1`, `T1.2`, `T2.1`, `T2.2`, `T3.1` | `V-3` passes without skips, real services return expected results, and DB/artifact assertions record IDs/FKs. |
| MVP validation record and progress | `RECONCILIATION_MVP_PHASE_7_TASK_PLAN.md` (this file) | `T3.2` | `V-3` to `V-6` results, actual ID/FK values, adoption gate, and `VM-14`/`VM-15` outcomes are recorded. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Gate the disposable live environment | Done | Phase 4, adoption | `T1.1` and `T1.2` verified: real match, adoption/allocator checks, and health-only rejection; `V-3` preflight and `V-4` passed. |
| Area 2: Exercise review, export, normalization, and binding | Blocked | Area 1; Phases 2, 5, 6 | `T2.1` passed; `T2.2` cannot pass: export owner is `site.site_name`, but ingester requires `site.site_id` for local-only approvals. `V-3` failed before binding/allocation. |
| Area 3: Cover failures and record the MVP result | Blocked | Areas 1-2 | `T3.1` partially covers transitions and absent candidates; outage, protected links, full artifact/DB checks, and `V-5` remain. `T3.2` records partial results, not phase completion. |

## Definition Of Done

* [ ] `PH7-AC-1` has recorded accepted/local-only/rejected/undecided target IDs and both local and target-facing FK values, with identical unchanged reruns (`VM-14`).
* [ ] `PH7-AC-2` has an unskipped database-backed run covering success, approval, blocks, rejection, changed decisions, stale link, absent row, outage, and recovery (`VM-14`).
* [ ] `PH7-AC-3` has an unskipped readiness and adopted existing-site binding result, including a health-only failure (`VM-15`).
* [ ] All work areas, the new test, and the validation record are complete; the disposable database and temporary project/artifacts were isolated and cleaned up safely.
* [ ] Targeted regression, Authority integration, manual UI check, formatting, and doc-link results are recorded; no skipped live test is reported as passed.
* [ ] Offline normalization, manual/unowned protection, `system_id` Core links, sidecar ownership, and ingester approval rules retain coverage.
* [ ] Any deviation or follow-up is documented, and no unresolved prerequisite or question affects the MVP result.

## Risks And Open Questions

* **Adoption gate:** The companion adoption proposal is still marked draft; the helper has a `bootstrap site` operation but may refuse inconsistent existing IDs. Ownership is named in the current phase plan, not proof that the selected disposable DB is adopted. Complete and verify adoption before `V-3`/`V-4`; if it fails, leave the phase incomplete and report the discrepancy.
* **Real-service test isolation:** A successful SIMS resolve creates persistent identities/bindings in the disposable DB. Use unique source keys, scopes, and run IDs; compare the relevant rows across reruns and never point the test at a deployed database. Stop and report if the existing project/target-model contract cannot express the fixture without changing another phase.
