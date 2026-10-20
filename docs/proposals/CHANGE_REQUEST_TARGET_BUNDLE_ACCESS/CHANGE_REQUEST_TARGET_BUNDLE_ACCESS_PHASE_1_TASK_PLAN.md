# Phase 1 Task Plan: Make Change Request Bundle Output Exclusive And Traceable

## Phase Summary

**Goal:** Write each Change Request bundle in an exclusive managed run folder, preserve the bundle's internal contract, and return its actual path.

**Readiness: Validated.** [Phase 1](./CHANGE_REQUEST_TARGET_BUNDLE_ACCESS_PHASE_PLAN.md#phase-1-make-bundle-output-exclusive-and-traceable) is marked ready. The output location, run-folder token, collision ordering, cleanup rule, and response contract are fixed by the [proposal](./CHANGE_REQUEST_TARGET_BUNDLE_ACCESS.md). The current code and affected tests were inspected, and focused baseline tests pass.

**Constraints and dependencies:** The [in-memory handoff](../IN_MEMORY_INGESTER_HANDOFF/IN_MEMORY_INGESTER_HANDOFF_PHASE_PLAN.md) is complete. Keep `application:run_ingesters` on both project-only routes and the direct helper until Phase 3. Keep `project:execute`, the strict no-source project request, backend-owned `INGEST_OUTPUT_DIR`, and retired Change Request file input. Phase 2 owns target-sequence and retry-client changes; this phase preserves the current database and SIMS identity behavior apart from choosing one effective run ID before output reservation.

**Source criteria:** `P-AC-2` and the output-path part of `P-AC-5` map to `PH1-AC-1`–`PH1-AC-3`; Phase 1 validation milestones are `VM-1.1` and `VM-1.2`.

1. [x] `PH1-AC-1` (from `P-AC-2`): A successful run writes under `<INGEST_OUTPUT_DIR>/<UTC timestamp>_<SHA-256 digest of run_id>/<bundle_name>`; raw run IDs cannot select paths, and internal bundle names and content stay unchanged.
2. [x] `PH1-AC-2` (from `P-AC-2`): A destination collision stops before any file or SIMS call for that request. Earlier output remains untouched; later failure cleanup affects only output this invocation created.
3. [x] `PH1-AC-3` (from `P-AC-2`, `P-AC-5`): The project-only ingest response reports the actual bundle directory; the effective run ID remains in the response and manifest, including when minted by the server.

## Repository Findings

**Repository basis:** branch `in-memory-ingester-handoff`, commit `010544a0`, planning date 2026-10-20. The working tree was clean before this plan. Graphify's scoped query returned unrelated nodes and `explain` mapped `ProjectIngesterService` to an endpoint reference, so the findings below were verified against current source and tests.

| Evidence | Current behavior | Planning implication |
| --- | --- | --- |
| `backend/app/services/project_ingester_service.py::ProjectIngesterService._create_trusted_config`, `ingest_project_tables`; `backend/app/core/config.py::Settings.INGEST_OUTPUT_DIR` | The project helper already takes the output root from backend settings and passes it in `IngesterConfig`; it maps every ingestion result to `IngestResponse(output_path=None)`. | Reuse the setting. Change the response mapping after the ingester can report the written directory; do not add an output field to the project request. |
| `backend/app/models/ingester.py::ProjectIngesterRequest`, `IngestResponse`; `frontend/src/components/ingester/IngesterForm.vue` | Project requests forbid extra fields and accept optional `submission_context.run_id`; the response already has `output_path`, which the form displays when present. | No project-request or frontend component change is needed for Phase 1. A caller-provided run ID may contain path characters, so hash it for the folder component. |
| `ingesters/sead_change_request/input_resolution.py::resolve_inputs`, `_resolve_submission_context`, `_resolve_run_id`; `ingesters/sead_change_request/ingester.py::_prepare_change_request`, `_ingest_bundle` | Input resolution mints a UUID when no run ID is supplied. `_prepare_change_request` resolves inputs and can call SIMS before `_ingest_bundle` reaches the writer. | Resolve the effective context once before reservation, then pass that same context into preparation. Reserve before any SIMS call and do not mint a second ID for one request. |
| `ingesters/sead_change_request/artifact_writer.py::write_artifact_bundle`; `src/path_resolution.py::resolve_contained_path` | The writer places `<bundle_name>` directly under the supplied root and deletes any existing same-name directory with `shutil.rmtree`. The shared path helper resolves symlinks and checks containment. | Add exclusive run-folder reservation, resolve bundle and payload paths inside that folder, and remove only newly owned incomplete output on failure. Preserve the existing bundle name and generated relative paths. |
| `backend/app/ingesters/protocol.py::IngestionResult.create_success_result`; `ingesters/sead_change_request/ingester.py::_ingest_bundle` | The writer returns a `Path`, but `IngestionResult` has no output-path field; the success message is the only carrier of the path. | Add an optional output path to the result and success factory. Pass the writer's returned path directly to the project response; do not parse the message. |
| `backend/tests/ingesters/test_sead_change_request_ingester.py::test_ingest_overwrites_existing_bundle_deterministically`; `backend/tests/services/test_project_ingester_service.py::test_successful_ingest_writes_only_bundle_under_managed_root` | Tests assert the flat bundle layout, and one test explicitly expects replacement. The project service test checks one bundle under the managed root but not `output_path`. | Replace the overwrite assertion and update path expectations for the enclosing run folder. Keep SQL, manifest, and payload-content checks. |
| `backend/tests/api/test_project_ingester_routes.py`; `backend/tests/ingesters/test_sead_change_request_input_resolution.py`; `backend/tests/ingesters/test_ingester_infrastructure.py` | Route tests cover the interim permission and response forwarding; input-resolution tests cover supplied and server-minted IDs; protocol tests cover other ingesters. | Reuse these suites for the output-path and unchanged-contract regressions. |

## Scope

**In scope:** Change Request table-ingester run-folder reservation, bundle writing and owned-output cleanup, `IngestionResult` and project-only `IngestResponse.output_path`, focused and regression tests, and the ingester's artifact-output documentation.

**Out of scope:** Removing an authorization check, adding or changing `INGEST_OUTPUT_DIR`, changing project request fields, persisting a client run ID, changing SIMS source identity or target-sequence behavior, and changing bundle names, generated SQL, payload paths, or other ingesters' output handling.

## Work Breakdown

### Area 1: Reserve and write an owned run folder

**Objective:** A Change Request ingest reserves a safe destination before identity work and writes only into that destination.

**Affected code:** `ingesters/sead_change_request/ingester.py::_prepare_change_request`, `_ingest_bundle`; `ingesters/sead_change_request/artifact_writer.py::write_artifact_bundle`; existing `ingesters/sead_change_request/input_resolution.py::resolve_inputs` and `src/path_resolution.py::resolve_contained_path` contracts.

**Dependencies:** Completed in-memory table-input path and configured output root. No new decision is required.

**Tasks:**

* [x] `T1.1` **Change:** Select one effective run ID and reserve its directory before ingester preparation can call SIMS.
  * **Target:** `ingesters/sead_change_request/ingester.py::_ingest_bundle`, `_prepare_change_request`; `ingesters/sead_change_request/artifact_writer.py` (proposed run-directory reservation helper).
  * **Current → required:** `_prepare_change_request` resolves inputs, possibly mints an ID, and reaches SIMS before writing. The ingest path must resolve the effective context once, derive `<YYYYMMDDTHHMMSSZ>_<sha256(run_id)>`, and reserve that folder under `config.output_folder` before SIMS identity or Binding Set calls.
  * **Implementation:** Factor pure input resolution from preparation so `_ingest_bundle` can obtain `ResolvedInputs` and pass the same object into the rest of preparation. Take the run timestamp from the UTC clock, not the submission timestamp. Hash the full UTF-8 run ID to a fixed-length hexadecimal path component; keep the raw ID in SIMS and manifest data. Create only the run folder with exclusive semantics; a pre-existing destination returns a structured failed `IngestionResult` with the effective run ID and no output path. Preserve `validate_tables()` without a folder write. Make the clock controllable in tests.
  * **Constraints:** Keep the project helper's trusted root and existing fallback UUID behavior. Do not change Phase 2's target-ID allocation path or Phase 3's permission checks.
  * **Validation:** `V-1`, `V-2`; fixed-time collision, supplied ID containing `/` or `..`, missing-ID fallback, and SIMS fake showing zero calls on collision.
* [x] `T1.2` **Change:** Write the existing bundle inside the reserved run folder without deleting older output.
  * **Target:** `ingesters/sead_change_request/artifact_writer.py::write_artifact_bundle`; `ingesters/sead_change_request/ingester.py::_ingest_bundle`.
  * **Current → required:** The writer removes a same-name bundle and writes directly under the configured root. It must accept the owned run folder, reject an existing bundle within it, and write the unchanged `deploy/`, `revert/`, `verify/`, manifest, and payload layout.
  * **Implementation:** Resolve generated bundle and payload paths relative to the owned folder with `resolve_contained_path`; reject absolute, traversal, or symlink escape. Validate required artifact fields before writing where possible. Remove the unconditional `shutil.rmtree` branch. On every non-success exit after reservation, including preparation, validation, precondition, target collision, render, association, and write failures, clean up only the folder this invocation reserved; never follow or delete a replaced path or unrelated output. Return the completed bundle directory.
  * **Constraints:** Keep `resolve_bundle_name`, manifest `cr_name`, SQL filenames, `\copy` references, and payload bytes unchanged. Other ingesters retain their output behavior.
  * **Validation:** `V-1`, `V-2`; existing-folder marker and checksum preservation, injected write failure after partial output, unsafe payload path, and all deploy strategies.

**Completion evidence:** `VM-1.1` and `VM-1.2` pass for a safe run folder, a collision with no SIMS call, and cleanup limited to owned incomplete output.

### Area 2: Return the written bundle directory

**Objective:** A successful project-only response names the exact directory emitted by the writer.

**Affected code:** `backend/app/ingesters/protocol.py::IngestionResult`; `ingesters/sead_change_request/ingester.py::_ingest_bundle`; `backend/app/services/project_ingester_service.py::ProjectIngesterService.ingest_project_tables`.

**Dependencies:** Area 1 returns the completed bundle path.

**Tasks:**

* [x] `T1.3` **Change:** Carry the writer's path through the ingester result and project response.
  * **Target:** `backend/app/ingesters/protocol.py::IngestionResult`, `create_success_result`; `ingesters/sead_change_request/ingester.py::_ingest_bundle`; `backend/app/services/project_ingester_service.py::ProjectIngesterService.ingest_project_tables`.
  * **Current → required:** The writer returns a `Path`, but the result drops it and the service returns `output_path=None`. Add an optional result path with a default of `None`, set it only after a complete write, and map it to the existing `IngestResponse.output_path` field.
  * **Implementation:** Use the returned bundle directory rather than reconstructing a path from the root, timestamp, or success message. Failed results keep `output_path=None`; the full raw run ID remains in `run_id` and the manifest. Keep `IngestionResult` construction by other ingesters and generic `IngesterService` behavior compatible.
  * **Constraints:** Do not change shared `IngestRequest`, project request models, or the frontend component; it already displays a provided path.
  * **Validation:** `V-2`, `V-3`; direct ingester success and failure, project service mapping, route serialization, and other-ingester result construction.

**Completion evidence:** A project-only success response's `output_path` resolves to the bundle directory that contains its manifest; failures have no path.

### Area 3: Replace legacy output expectations and document the layout

**Objective:** Tests and ingester documentation describe the exclusive run layout and preserve the deploy bundle contract.

**Affected tests and documentation:** `backend/tests/ingesters/test_sead_change_request_artifact_writer.py` (**NEW**); `backend/tests/ingesters/test_sead_change_request_ingester.py`; `backend/tests/services/test_project_ingester_service.py`; `backend/tests/api/test_project_ingester_routes.py`; `ingesters/sead_change_request/README.md`.

**Dependencies:** Areas 1 and 2.

**Tasks:**

* [x] `T1.4` **Test:** Cover writer containment, exclusive reservation, and owned cleanup.
  * **Target:** `backend/tests/ingesters/test_sead_change_request_artifact_writer.py` (**NEW**); `backend/tests/ingesters/test_sead_change_request_ingester.py::test_ingest_overwrites_existing_bundle_deterministically` (replace this expectation).
  * **Current → required:** A repeated ingest currently deletes an earlier same-name bundle. Add a fixed-UTC-time collision case with an existing marker and unchanged bytes, assert no SIMS calls for the colliding request, and verify two different run IDs retain separate bundles on the same day. Check cleanup after an early validation failure and an injected partial write failure; existing output must survive both. Test raw path characters in a caller run ID and a payload path that attempts to leave the bundle.
  * **Implementation:** Use temporary directories and the existing fake SIMS client; do not call a live service. Assert the full run ID remains in manifest data while the directory uses its SHA-256 digest. Update direct-ingester path assertions to locate the bundle inside the run folder without weakening SQL, manifest, or gzip payload checks.
  * **Constraints:** Do not keep an assertion that the old bundle is removed. Keep strategy-specific bundle bytes and generated paths unchanged.
  * **Validation:** `V-1`, `V-2`.
* [x] `T1.5` **Test and document:** Verify response propagation and the unchanged interim gate; describe the new output location.
  * **Target:** `backend/tests/services/test_project_ingester_service.py::test_successful_ingest_writes_only_bundle_under_managed_root`; `backend/tests/api/test_project_ingester_routes.py::test_project_routes_forward_authorized_resource_request_and_response`; `backend/tests/ingesters/test_ingester_infrastructure.py`; `ingesters/sead_change_request/README.md::Artifact Output`.
  * **Current → required:** The service test finds one flat bundle but does not assert `output_path`; the route response stub uses `None`. Make both assert the actual nested bundle path. Document the UTC/digest run folder, unchanged inner bundle name, and response path. Retain the route test that requires both interim permissions.
  * **Implementation:** Add success and failure response assertions, including the server-minted run ID matching SIMS and manifest. Verify the optional `IngestionResult` field does not alter the file-only ingester's result contract.
  * **Constraints:** Phase 1 must not modify the project-only authorization dependency or direct helper gate.
  * **Validation:** `V-2`, `V-3`, `V-4`, `V-5`, `V-6`.

**Completion evidence:** All three phase criteria pass, the package README matches the emitted layout, and focused plus backend regression checks pass.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected result |
| --- | --- | --- | --- |
| `PH1-AC-1` (from `P-AC-2`) | `T1.1`, `T1.2`, `T1.4` | `V-1`, `V-2` | Managed UTC/digest folder and unchanged inner bundle for supplied, unsafe, and server-minted run IDs. |
| `PH1-AC-2` (from `P-AC-2`) | `T1.1`, `T1.2`, `T1.4` | `V-1`, `V-2` | Collision precedes SIMS and file writes; old output survives and failure cleanup touches only owned output. |
| `PH1-AC-3` (from `P-AC-2`, `P-AC-5`) | `T1.1`, `T1.3`, `T1.5` | `V-2`, `V-3` | Actual written directory reaches result and API response; raw effective run ID matches SIMS and manifest. |

## Validation And Testing

The focused baseline passed on 2026-10-20: `rtk uv run pytest backend/tests/ingesters/test_sead_change_request_ingester.py backend/tests/services/test_project_ingester_service.py backend/tests/api/test_project_ingester_routes.py -q` and `rtk uv run pytest backend/tests/ingesters/test_sead_change_request_input_resolution.py backend/tests/ingesters/test_ingester_infrastructure.py -q`. No implementation was changed for this plan.

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
| --- | --- | --- | --- | --- | --- |
| `V-1` | New writer tests in `backend/tests/ingesters/test_sead_change_request_artifact_writer.py` | `rtk uv run pytest backend/tests/ingesters/test_sead_change_request_artifact_writer.py -q` | `PH1-AC-1`, `PH1-AC-2` | Exclusive folder, containment, collision, and owned cleanup cases pass. | Pass: 5 new writer tests pass. |
| `V-2` | Change Request ingest tests in `backend/tests/ingesters/test_sead_change_request_ingester.py` | `rtk uv run pytest backend/tests/ingesters/test_sead_change_request_ingester.py -q` | `PH1-AC-1`–`PH1-AC-3` | Existing artifact-content checks pass with nested layout; old overwrite test is replaced. | Pass: all ingest tests pass, including separate-bundles, collision, and cleanup cases. |
| `V-3` | Project service, route, input-resolution, and protocol regressions | `rtk uv run pytest backend/tests/services/test_project_ingester_service.py backend/tests/api/test_project_ingester_routes.py backend/tests/ingesters/test_sead_change_request_input_resolution.py backend/tests/ingesters/test_ingester_infrastructure.py -q` | `PH1-AC-3`, interim authorization and other-ingester behavior | Response path and run ID match the artifact; supplied and fallback IDs work; interim gate and other results remain unchanged. | Pass: all four suites pass. |
| `V-4` | Python formatting and import order for changed code and tests | `rtk .venv/bin/black --check backend/app/ingesters/protocol.py backend/app/services/project_ingester_service.py ingesters/sead_change_request/ingester.py ingesters/sead_change_request/artifact_writer.py backend/tests/ingesters/test_sead_change_request_artifact_writer.py backend/tests/ingesters/test_sead_change_request_ingester.py backend/tests/services/test_project_ingester_service.py backend/tests/api/test_project_ingester_routes.py`<br>`rtk .venv/bin/isort --check-only backend/app/ingesters/protocol.py backend/app/services/project_ingester_service.py ingesters/sead_change_request/ingester.py ingesters/sead_change_request/artifact_writer.py backend/tests/ingesters/test_sead_change_request_artifact_writer.py backend/tests/ingesters/test_sead_change_request_ingester.py backend/tests/services/test_project_ingester_service.py backend/tests/api/test_project_ingester_routes.py` | Changed Python files | Both checks pass. | Pass: black and isort clean after formatting. |
| `V-5` | Backend regression suite | `rtk uv run pytest backend/tests -q` | Existing backend behavior | No new failures; report environment-dependent skips separately. | 2 pre-existing failures, unrelated to Phase 1: `test_route_inventory_matches_assembled_api_routes` (from-project routes missing from `AUTHORIZATION_ROUTE_INVENTORY.md`, from the merged handoff PR) and `test_both_artifacts_use_sims_submission_id_and_rollback` (needs loopback PostgreSQL). |
| `V-6` | Documentation and whitespace | `rtk make check-doc-links` and `rtk git diff --check` | README and plan links | Links and diff pass. | Pass: `check-doc-links` reports valid links; `git diff --check` is clean. |

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Safe output and effective-run-ID flow | `ingesters/sead_change_request/ingester.py`, `ingesters/sead_change_request/artifact_writer.py` | `T1.1`, `T1.2` | Reservation precedes SIMS; writer never replaces an existing bundle. |
| Written-path result and service mapping | `backend/app/ingesters/protocol.py`, `backend/app/services/project_ingester_service.py` | `T1.3` | Project-only success returns its real bundle directory. |
| Writer and ingest regression tests | `backend/tests/ingesters/test_sead_change_request_artifact_writer.py` (**NEW**), `backend/tests/ingesters/test_sead_change_request_ingester.py` | `T1.4` | Safe output and unchanged artifact contract pass. |
| Response and authorization regression tests | `backend/tests/services/test_project_ingester_service.py`, `backend/tests/api/test_project_ingester_routes.py`, `backend/tests/ingesters/test_ingester_infrastructure.py` | `T1.5` | Response path, unchanged interim gate, and other ingester results pass. |
| Artifact-output documentation | `ingesters/sead_change_request/README.md` | `T1.5` | Documented run folder and returned bundle path match emitted output. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Reserve and write an owned run folder | Done | Completed in-memory handoff | Reservation precedes SIMS; writer rejects a pre-existing bundle. |
| Area 2: Return the written bundle directory | Done | Area 1 | `IngestionResult.output_path` mapped to `IngestResponse.output_path`. |
| Area 3: Replace legacy output expectations and document the layout | Done | Areas 1 and 2 | Overwrite test replaced; README documents the run folder and response path. |

## Definition Of Done

- [x] The implementation agent verifies the repository targets still match this plan; on a material conflict, stop and report the difference rather than changing scope.
- [x] `PH1-AC-1`–`PH1-AC-3` each have passing task and validation results, including `VM-1.1` and `VM-1.2`.
- [x] All work areas and deliverables are complete; earlier bundles and unrelated files survive repeated and failed runs.
- [x] `V-1`–`V-6` pass or any environment-dependent skip is recorded with its limit.
- [x] The bundle name, manifest `cr_name`, SQL names, `\copy` paths, and payload bytes are regression-tested.
- [x] Both project-only routes and direct helper calls still require the interim application action and `project:execute`; Change Request file input remains retired.
- [x] The README and response contract match the written directory, and deviations or follow-up work are recorded.
- [x] No unresolved question affects implementation, correctness, or validation.

## Risks And Open Questions

- **One effective run ID:** Resolving the submission context twice can mint two fallback UUIDs. `T1.1` must pass the same resolved context through reservation, SIMS work, manifest writing, and response construction.
- **Cleanup ownership:** The writer currently deletes a pre-existing bundle. The replacement must distinguish a directory reserved by this invocation from an existing or replaced path before cleanup. `V-1` and `V-2` verify that distinction.
- No blocking decision remains for this phase. Target-sequence allocation and persistent client retry state are Phase 2 work; the interim application action remains in force until Phase 3.
