# Reliable Reconciliation Links to Existing SEAD Entities - Phase 6 Task Plan

## Phase Summary

**Phase:** 6 - Change-Request Ingester Rule. **Readiness:** Validated for implementation. [Phase 1](RECONCILIATION_MVP_PHASE_1_TASK_PLAN.md) is complete. [Phase 3](RECONCILIATION_MVP_PHASE_3_TASK_PLAN.md) has delivered owned export, cleanup, and offline normalization; its remaining workspace type-check caveat is recorded below. The [phase plan](RECONCILIATION_MVP_PHASE_PLAN.md#phase-6-change-request-ingester-rule) marks Phase 6 ready once those outputs exist.

**Goal:** Export a local-only approval separately from an existing-ID link. Allow the SEAD Change Request ingester to allocate only for an exported approval in an allocation-capable reconciliation mode, and block undecided rows before SIMS work.

**Sources:** [Shape Shifter proposal](RECONCILIATION_MVP.md) (`SS-AC-4`, `SS-AC-7`) and [phase plan](RECONCILIATION_MVP_PHASE_PLAN.md) (`VM-13`). No Authority Service change is required for this phase.

**Acceptance criteria**

1. [ ] `PH6-AC-1` (from `SS-AC-7`): The ingester never selects or passes an unreviewed candidate to SIMS.
2. [ ] `PH6-AC-2` (from `SS-AC-7`): Normalization applies existing-ID links; a non-conflicting pre-linked ID keeps its existing path; rejected and undecided reconciled rows without an ID are blocked.
3. [ ] `PH6-AC-3` (from `SS-AC-4`, `SS-AC-7`): Exported local-only approvals are separate, owner-tagged sidecar entries keyed by the encoded business key. Only their owner can remove stale approvals, and the authorized backend supplies them as trusted ingester metadata without changing `public_id`.
4. [ ] `PH6-AC-4` (from `SS-AC-7`): An exported local-only approval can allocate with `reconcile-exact` or `reconcile-fuzzy`, but cannot allocate with `lookup-only` or `lookup-extensible`.

**Constraints:** Keep the two stores and explicit export. Do not treat `Link(target_id=None)` as an approval, read the decision catalog or `verified_at` from the ingester, add approval columns to normalized data, call a matching service during ingestion, or change Core `system_id` relationships. Keep manual and unowned links protected and sidecar saves version-checked. Existing pre-linked IDs and tracked, child, and derived entity behavior remain supported.

## Repository Findings

**Repository basis:** Branch `reconciliation-mvp`, commit `d003e69c`, inspected 2026-10-31. The uncommitted source proposal and phase plan were used as the requested planning sources. No Phase 6 implementation or test changes were assumed. Graphify has no directed path from `MappingCatalog` to `SeadChangeRequestIngester`; the verified integration path runs through project normalization and `ProjectIngesterService`.

| Verified source | Current behavior | Planning implication |
| --- | --- | --- |
| `src/reconciliation/mapping_model.py::{EntityMapping, Link, LinkOwner, MappingCatalog, encode_local_key}`; `src/reconciliation/mapping_manager.py::{load_snapshot, save}` | Each entity stores links by encoded key; old sidecars have no approval collection. An owned link records its specification and commit time. Saves use a fresh content version and atomic replacement. | Add a separate, typed, owner-tagged approval collection with an empty default for old files; preserve existing link semantics and use the same snapshot/save path. |
| `backend/app/services/reconciliation/service.py::{_export_to_mapping_locked, _remove_owned_mapping_links_locked, delete_specification, replace_catalog}` | Export writes accepted ID links, removes stale owned links, skips local-only decisions, and protects manual/unowned links. Specification deletion and whole-catalog replacement clean owned links under the project lock. | Reconcile both owned entry types in one save; include approvals in every specification-removal path, no-op detection, conflicts, and reported counts. |
| `backend/app/models/reconciliation.py::{ExportToMappingResult, EntityResolutionCatalogDeleteResult}`; `backend/app/api/v1/endpoints/reconciliation.py::export_reconciliation_to_mapping`; `frontend/src/stores/reconciliation.ts::deleteSpecification` | Responses count only links. The store strips `removed_owned_links` from the deletion response before saving catalog state and returns that count; the UI shows link-only messages. | Add approval counts without changing existing link-count meanings or route authorization; update the store to remove both count fields and return both to the UI. |
| `src/normalizer.py::{normalize, _apply_mapping_sidecar_links}`; `tests/process/test_shapeshifter.py` | Normalization loads a sidecar once and applies committed links to `public_id`; a committed link with a null target would write a null ID. | Use the same loaded catalog for approvals at project-to-ingester handoff, but leave the ID-application path unchanged. |
| `backend/app/services/project_ingester_service.py::{validate_project_tables, ingest_project_tables, _create_trusted_config}`; `ingesters/sead_change_request/ingester.py::{validate_tables, ingest_tables}` | Authorized project calls normalize first, then pass table mappings; trusted config is built from saved project data. The table-ingester protocol accepts tables and a diagnostic source name, not approval metadata. | After normalization, attach approvals from its sidecar snapshot to backend-owned `IngesterConfig.extra` for both validation and ingest; do not extend the shared table-ingester protocol or trust request fields. |
| `ingesters/sead_change_request/{input_resolution,preparation,contracts}.py::{resolve_inputs, ResolvedInputs, TrustedProjectContext}`; `ingesters/sead_change_request/ingester.py::_validate_business_keys` | Resolved inputs carry the trusted project's ordered business keys, but no approvals. Key checks run before provider lookup and SIMS calls. | Validate approval shape, owner, project, key encoding, and conflicts with existing IDs before any identity side effect. Missing metadata means no approval, not permission to allocate. |
| `ingesters/sead_change_request/{planning,orchestration,capability_preflight}.py::{plan_table, plan_bundle, orchestrate_identity_assignments, _required_sims_operations}`; `backend/app/services/ingester_runtime.py::inject_ingester_runtime_dependencies` | A missing reconciled `public_id` plans `RECONCILE`; the backend injects a candidate-picking adapter. A miss can allocate for `reconcile-exact`/`reconcile-fuzzy`; lookup modes cannot allocate. | Plan allocation only for a trusted approval and a permitted effective mode. Block every other missing reconciled ID without invoking candidate selection; stop injecting the adapter while retaining tracked-ID allocation and SIMS capability checks. |

## Scope

**In scope:** Sidecar approval schema and owned export/cleanup; additive export/deletion counts and UI messages; authorized project-to-ingester approval transport; fail-closed ingester input, planning, and orchestration; focused tests and user documentation for `site`. Test all four effective reconciliation modes with synthetic entity specifications even though `site` defaults to `reconcile-exact`.

**Out of scope:** Candidate existence verification at export (Phase 5), SIMS adoption of existing `site` rows and live end-to-end rollout (Phase 7), other entity-type rollout, new matching rules, changing the table-ingester protocol for all ingesters, or changing target-model identity policy.

**Affected contracts:** `<project>-mapping.yml`, reconciliation export and specification-deletion responses, the authorized project service's ingester configuration, the ingester's internal resolved input and row-action contracts, frontend reconciliation result types, and tests/docs named below.

## Work Breakdown

### Area 1: Persist and export local-only approvals

**Objective:** One export commits an owner's accepted ID links and local-only approvals without making an approval look like an ID link.

**Affected code:** `src/reconciliation/mapping_model.py::{EntityMapping, LinkOwner, MappingCatalog}`, `backend/app/services/reconciliation/service.py::{_export_to_mapping_locked, _remove_owned_mapping_links_locked}`, `src/reconciliation/mapping_manager.py::save` (reuse, not redesign).

**Dependencies:** Phase 1 decisions and Phase 3 owned export.

**Tasks:**

* [ ] `T1.1` **Change:** Add a typed sidecar collection for committed local-only approvals, separate from `EntityMapping.links`.
  * **Target:** `src/reconciliation/mapping_model.py::EntityMapping` and `MappingCatalog`; `tests/reconciliation/test_mapping_sidecar.py`.
  * **Current -> required:** Only ID links are persisted -> an approval has an encoded key, required specification owner, and explicit committed state; legacy YAML loads with no approvals.
  * **Implementation:** Reuse `LinkOwner` and the sidecar manager's existing serialization/version checks. Do not create a targetless `Link`, change `committed_links_by_entity`, or alter normalization's ID assignment.
  * **Validation:** `V-1`: old fixture, compound key, round-trip, malformed owner, draft/uncommitted entry rejection, and no null-ID application.
* [ ] `T1.2` **Change:** Export and clean approvals together with owned links.
  * **Target:** `backend/app/services/reconciliation/service.py::{_export_to_mapping_locked, _remove_owned_mapping_links_locked, delete_specification, replace_catalog}`; `backend/tests/api/v1/test_reconciliation_export.py`, `backend/tests/api/v1/test_reconciliation_specifications.py`, `backend/tests/services/test_mapping_write_coordination.py`.
  * **Current -> required:** Local-only is ignored -> export adds its approval, replaces its former owned ID link, and removes stale approvals on changed/rejected/deleted decisions and on specification deletion or whole-catalog replacement.
  * **Implementation:** Check claims against other specifications and sidecar entries before mutating; conflict with a manual/unowned link or other owner fails without a write. Reuse the project lock, fresh snapshot, expected version, atomic save, and sidecar-first specification removal. Do not rewrite an unchanged sidecar. Retain the existing partial-failure report when catalog persistence fails.
  * **Validation:** `V-2`: accepted/local-only/rejected transitions, re-export byte equality, owner and protected-link conflicts, compound keys, version conflict, every specification-removal route, and accurate cleanup counts.
* [ ] `T1.3` **Change:** Report approval creation and removal without calling them links.
  * **Target:** `backend/app/models/reconciliation.py::{ExportToMappingResult, EntityResolutionCatalogDeleteResult}`, `backend/app/api/v1/endpoints/reconciliation.py::{export_reconciliation_to_mapping, delete_specification}`, `frontend/src/types/reconciliation.ts`, `frontend/src/stores/reconciliation.ts::deleteSpecification`, `frontend/src/components/reconciliation/{ReconciliationView,SpecificationsList}.vue`, `frontend/src/components/reconciliation/__tests__/{ReconciliationView,SpecificationsList}.test.ts`.
  * **Current -> required:** API and UI report link counts only -> additive approval counts are visible, and existing `exported`, `removed`, `skipped_manual`, and `removed_owned_links` retain their link-only meanings.
  * **Implementation:** Preserve existing response fields and route authorization. Strip both deletion-count fields before assigning catalog state and return both counts to the list view. Show a failure, not success, on conflicts; update the typed UI contract and deletion/export feedback together.
  * **Validation:** `V-2`, `V-5`: exact response shapes, count messages, and protected-link failures.

**Completion evidence:** Old sidecars still parse; accepted IDs remain links; local-only approvals persist without target IDs; repeated export and every deletion path keep owner-specific counts and protected links intact.

### Area 2: Supply trusted approvals to both project operations

**Objective:** Validation and ingestion receive the same committed approvals used with the normalized ID links.

**Affected code:** `backend/app/services/project_ingester_service.py::{validate_project_tables, ingest_project_tables, _create_trusted_config}`, `ingesters/sead_change_request/{input_resolution,preparation,contracts}.py`.

**Dependencies:** Area 1 approval schema.

**Tasks:**

* [ ] `T2.1` **Change:** Attach approvals from the authorized project's normalization snapshot to SEAD Change Request configuration.
  * **Target:** `backend/app/services/project_ingester_service.py::{validate_project_tables, ingest_project_tables}`; `backend/tests/services/test_project_ingester_service.py`, `backend/tests/api/test_project_ingester_routes.py`.
  * **Current -> required:** The project service sends normalized tables but no decision metadata -> after `normalize_project`, both operations pass typed approvals from the same loaded `mapping_catalog` in backend-owned `IngesterConfig.extra`.
  * **Implementation:** Share one helper between the two operations; require the authorized project and sidecar metadata to agree. Do not read a second, possibly different sidecar snapshot, accept approval overrides from the request or `source_name`, or change `TableSourceIngester`.
  * **Validation:** `V-4`: matching authorized project and sidecar, wrong project/forged metadata, missing sidecar, validation/ingest parity, and unchanged non-Change-Request behavior; reject malformed state before SIMS or output writes.
* [ ] `T2.2` **Change:** Validate approval metadata and key-to-row correspondence before planning identity work.
  * **Target:** `ingesters/sead_change_request/input_resolution.py::resolve_inputs`, `ingesters/sead_change_request/preparation.py::ResolvedInputs`, `ingesters/sead_change_request/ingester.py::{_resolve_inputs, _validate_business_keys}`, `backend/tests/ingesters/{test_sead_change_request_input_resolution,test_sead_change_request_ingester}.py`.
  * **Current -> required:** `ResolvedInputs` contains no approvals -> trusted, committed approvals can be matched to reconciled rows by the ordered business key, while missing approval metadata authorizes nothing.
  * **Implementation:** Reject invalid owner/project, mismatched key declaration, absent or duplicate key values, and an approval conflicting with a pre-linked or sidecar-applied ID before provider lookup or any SIMS call. An exported approval with no current row must not allocate a row. Do not consult the unexported decision catalog.
  * **Validation:** `V-3`, `V-4`: single/compound keys, two equal labels with different keys, wrong project, pre-linked-ID conflict, absent row, and no external call on invalid input.

**Completion evidence:** Project validate and ingest apply one authorized approval set; a caller-supplied or stale/invalid approval cannot authorize allocation.

### Area 3: Block unreviewed rows and allocate only by approved mode

**Objective:** A missing reconciled ID cannot trigger a candidate search or SIMS allocation without explicit exported approval.

**Affected code:** `ingesters/sead_change_request/{planning,orchestration,preparation,ingester}.py`, `backend/app/services/ingester_runtime.py`.

**Dependencies:** Area 2 trusted input.

**Tasks:**

* [ ] `T3.1` **Change:** Plan reconciled rows from the effective mode and trusted approval set.
  * **Target:** `ingesters/sead_change_request/planning.py::{plan_table, plan_bundle}`, `ingesters/sead_change_request/ingester.py::_prepare_resolved_inputs`, `backend/tests/ingesters/test_sead_change_request_planning.py`.
  * **Current -> required:** Every missing reconciled ID plans `RECONCILE` -> only approved `reconcile-exact`/`reconcile-fuzzy` rows plan allocation; rejected/undecided and approved lookup-mode rows plan a block with a reason.
  * **Implementation:** Keep existing-ID, tracked, child, derived, database-sequence, and staging behavior outside the pilot unchanged. Make conflicts and plan errors stop before SIMS work, including with validation disabled; do not turn an unapproved miss into `ALLOCATE`.
  * **Validation:** `V-3`: four modes crossed with approval present/absent, non-conflicting existing IDs, contradictory IDs, and tracked/child/derived regression cases.
* [ ] `T3.2` **Change:** Remove the ingester's candidate-picking path for reconciled rows.
  * **Target:** `ingesters/sead_change_request/orchestration.py::orchestrate_identity_assignments`, `ingesters/sead_change_request/preparation.py::prepare_change_request`, `backend/app/services/ingester_runtime.py::{inject_ingester_runtime_dependencies, SeadChangeRequestReconciliationAdapter}`, `backend/tests/ingesters/{test_sead_change_request_orchestration,test_sead_change_request_runtime,test_sead_change_request_ingester}.py`.
  * **Current -> required:** `RECONCILE` invokes an injected matching adapter and may allocate after its miss -> no candidate is selected or sent to SIMS; only the planned, approved allocation sends an allocation request.
  * **Implementation:** Remove the unused adapter injection and candidate-selection behavior, retain the injected SIMS client and its capability/binding rules, and give blocked rows an explicit result in both `validate_tables` and `ingest_tables`. Update existing adapter/miss tests to assert the approved and unapproved paths rather than treating a service miss as operator approval.
  * **Validation:** `V-3`: no reconciliation-client calls, no SIMS request for unapproved/lookup-mode rows, exactly one approved allocation request for a permitted mode, and unchanged tracked allocation and existing-ID handling.

**Completion evidence:** Neither a candidate ranking nor a missing ID alone can produce an approved SIMS identity or a new ID.

### Area 4: Prove preservation and document the operator rule

**Objective:** Demonstrate the full Phase 6 contract without presenting Phase 7's live-service work as completed.

**Affected code:** Existing tests named in `V-1` through `V-5`; `docs/USER_GUIDE.md`.

**Dependencies:** Areas 1-3.

**Tasks:**

* [ ] `T4.1` **Change:** Complete cross-layer regression and update the user guide and this progress tracker.
  * **Target:** `backend/tests/api/v1/test_reconciliation_export.py`, `backend/tests/services/test_project_ingester_service.py`, `backend/tests/ingesters/test_sead_change_request_ingester.py`, `tests/process/test_shapeshifter.py`, `docs/USER_GUIDE.md`, this task plan.
  * **Current -> required:** The guide describes only links and current export behavior -> document separate exported approvals, blocked undecided rows, and permitted modes; show existing ID and Core local FK results remain unchanged on repeated offline normalization.
  * **Implementation:** Keep Authority verification (Phase 5) and real-service SIMS adoption (Phase 7) separate. Run focused contract and regression checks, record exact results, and stop if current code or tests invalidate the plan instead of redesigning Phase 6 during implementation.
  * **Validation:** `V-1` through `V-6`: actual sidecar contents, row states, SIMS call counts, normalized IDs, frontend messages, and quality checks.

**Completion evidence:** `VM-13` demonstrates all four `PH6-AC-*` criteria; user guidance and the tracker describe the shipped behavior.

## Acceptance-Criteria Coverage

| Criterion (source; phase milestone) | Task IDs | Validation IDs | Expected evidence |
| --- | --- | --- | --- |
| `PH6-AC-1` (`SS-AC-7`; `VM-13`) | `T3.1`, `T3.2`, `T4.1` | `V-3`, `V-4` | No candidate selection or unreviewed candidate passed to SIMS on validate or ingest. |
| `PH6-AC-2` (`SS-AC-7`; `VM-13`) | `T2.2`, `T3.1`, `T3.2`, `T4.1` | `V-3`, `V-4`, `V-5` | Existing links and non-conflicting pre-linked IDs resolve; rejected, undecided, and conflicting rows block without allocation. |
| `PH6-AC-3` (`SS-AC-4`, `SS-AC-7`; `VM-13`) | `T1.1`, `T1.2`, `T1.3`, `T2.1`, `T2.2`, `T4.1` | `V-1`, `V-2`, `V-4`, `V-5` | Owner-specific, separate sidecar approvals round-trip, clean up, reach trusted inputs, and never write `public_id`. |
| `PH6-AC-4` (`SS-AC-7`; `VM-13`) | `T2.2`, `T3.1`, `T3.2`, `T4.1` | `V-3`, `V-4` | Approved exact/fuzzy rows may allocate; lookup-only/extensible and unapproved rows never do. |

## Validation And Testing

Use the root `.venv/`; commands run from the repository root unless noted. `rtk` may prefix the commands without changing the check.

| ID | Check and target | Exact command or method | Covers | Expected result | Baseline (2026-10-31) |
| --- | --- | --- | --- | --- | --- |
| `V-1` | Sidecar schema and offline ID application: `tests/reconciliation/test_mapping_sidecar.py`, `tests/process/test_shapeshifter.py`; legacy YAML, valid/invalid approvals, compound keys, unchanged IDs | `.venv/bin/pytest -q tests/reconciliation/test_mapping_sidecar.py tests/process/test_shapeshifter.py` | `PH6-AC-2`, `PH6-AC-3` | Old links parse; approval round-trips independently; no null `public_id` or Core FK change. | Not run (combined command): sidecar file passed in the focused Python baseline; normalization file and new assertions not run. |
| `V-2` | Owned export, cleanup, counts, conflicts: `backend/tests/api/v1/test_reconciliation_export.py`, `backend/tests/api/v1/test_reconciliation_specifications.py`, `backend/tests/services/test_mapping_write_coordination.py` | `.venv/bin/pytest -q backend/tests/api/v1/test_reconciliation_export.py backend/tests/api/v1/test_reconciliation_specifications.py backend/tests/services/test_mapping_write_coordination.py` | `PH6-AC-3` | Acceptance/local-only/rejection and deletion produce correct links, approvals, counts, protected conflicts, and no-op bytes. | Not run (combined command): export and specification files passed in the focused Python baseline; write-coordination file and new assertions not run. |
| `V-3` | Planner/orchestrator and ingestion: `backend/tests/ingesters/{test_sead_change_request_planning,test_sead_change_request_orchestration,test_sead_change_request_ingester,test_sead_change_request_runtime,test_sead_change_request_input_resolution,test_sead_change_request_preflight}.py` | `.venv/bin/pytest -q backend/tests/ingesters/test_sead_change_request_planning.py backend/tests/ingesters/test_sead_change_request_orchestration.py backend/tests/ingesters/test_sead_change_request_ingester.py backend/tests/ingesters/test_sead_change_request_runtime.py backend/tests/ingesters/test_sead_change_request_input_resolution.py backend/tests/ingesters/test_sead_change_request_preflight.py` | `PH6-AC-1`, `PH6-AC-2`, `PH6-AC-4` | Four-mode matrix, approved vs missing approval, trusted keys, no candidate selection; tracked and staging regressions pass. | Pass: all six files passed across three focused baseline commands; the ingester/runtime command reported three skipped tests. |
| `V-4` | Authorized project wiring and failures: `backend/tests/services/test_project_ingester_service.py`, `backend/tests/api/test_project_ingester_routes.py`, `backend/tests/api/test_sead_change_request_project_scope.py` | `.venv/bin/pytest -q backend/tests/services/test_project_ingester_service.py backend/tests/api/test_project_ingester_routes.py backend/tests/api/test_sead_change_request_project_scope.py` | `PH6-AC-1` to `PH6-AC-4` | Project validate and ingest share the same sidecar approvals; unauthorized or forged inputs fail before SIMS/output; other ingesters unchanged. | Not run (combined command): service and Change Request project-scope files passed in focused baselines; project-ingester route file and new assertions not run. |
| `V-5` | Frontend feedback and offline regression: `frontend/src/components/reconciliation/__tests__/{ReconciliationView,SpecificationsList}.test.ts`; `backend/tests/api/v1/test_reconciliation_export.py`, `tests/process/test_shapeshifter.py` | `cd frontend && pnpm exec vitest run src/components/reconciliation/__tests__/ReconciliationView.test.ts src/components/reconciliation/__tests__/SpecificationsList.test.ts` and `.venv/bin/pytest -q backend/tests/api/v1/test_reconciliation_export.py tests/process/test_shapeshifter.py` | `PH6-AC-2`, `PH6-AC-3` | Correct approval/link counts and errors; two offline normalizations keep effective IDs and child FK values. | Pass: UI command, 10 tests; existing export FK test passed in Python baseline. Not run: combined Python command, process file, or planned approval assertions. |
| `V-6` | Formatting, type checking, docs and tracker: changed Python/TS files and `docs/USER_GUIDE.md` | Run independently: `uv run black --check src/reconciliation/mapping_model.py backend/app/services/reconciliation/service.py backend/app/services/project_ingester_service.py backend/app/services/ingester_runtime.py backend/app/models/reconciliation.py backend/app/api/v1/endpoints/reconciliation.py ingesters/sead_change_request`; `uv run pyright --threads 2 src backend`; `cd frontend && pnpm exec vue-tsc --noEmit`; `make check-doc-links`. Run Black on any other modified Python test files as well. | All criteria and contracts | Formatting and frontend/doc checks pass; type errors in changed code are fixed, and pre-existing workspace diagnostics are reported separately rather than called a pass. | Pass: `make check-doc-links` on this plan. Not run: other checks, no Phase 6 code changes. The Phase 3 tracker records 134 workspace Pyright diagnostics; re-establish and compare the baseline during implementation. |

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Approval schema and compatibility tests | `src/reconciliation/mapping_model.py`, `tests/reconciliation/test_mapping_sidecar.py` | `T1.1` | Old YAML and new typed approvals parse, persist, and never become ID links. |
| Export and cleanup contracts | `backend/app/services/reconciliation/service.py`, `backend/app/models/reconciliation.py`, `backend/app/api/v1/endpoints/reconciliation.py`, `backend/tests/api/v1/test_reconciliation_export.py`, `backend/tests/api/v1/test_reconciliation_specifications.py`, `backend/tests/services/test_mapping_write_coordination.py` | `T1.2`, `T1.3` | Idempotent export and all specification removals preserve manual/unowned links and report both entry types. |
| UI response types and messages | `frontend/src/types/reconciliation.ts`, `frontend/src/stores/reconciliation.ts`, `frontend/src/components/reconciliation/ReconciliationView.vue`, `frontend/src/components/reconciliation/SpecificationsList.vue`, `frontend/src/components/reconciliation/__tests__/ReconciliationView.test.ts`, `frontend/src/components/reconciliation/__tests__/SpecificationsList.test.ts` | `T1.3` | Export/deletion counts and failures visible without misleading link totals; catalog state excludes count fields. |
| Authorized approval delivery | `backend/app/services/project_ingester_service.py`, `backend/tests/services/test_project_ingester_service.py`, `backend/tests/api/test_project_ingester_routes.py` | `T2.1` | Both project operations use approvals from the same authorized normalization snapshot. |
| Ingester input contract | `ingesters/sead_change_request/input_resolution.py`, `ingesters/sead_change_request/preparation.py`, `ingesters/sead_change_request/ingester.py`, `backend/tests/ingesters/test_sead_change_request_input_resolution.py` | `T2.2` | Malformed/missing approval metadata cannot authorize allocation; key and ID conflicts fail before SIMS. |
| Row planning and orchestration | `ingesters/sead_change_request/planning.py`, `ingesters/sead_change_request/orchestration.py`, `ingesters/sead_change_request/preparation.py`, `backend/app/services/ingester_runtime.py`, `backend/tests/ingesters/test_sead_change_request_planning.py`, `backend/tests/ingesters/test_sead_change_request_orchestration.py`, `backend/tests/ingesters/test_sead_change_request_runtime.py`, `backend/tests/ingesters/test_sead_change_request_ingester.py` | `T3.1`, `T3.2` | Only approved rows in permitted modes allocate; candidate-picking path removed. |
| Offline regression, user guidance, and progress | `tests/process/test_shapeshifter.py`, `docs/USER_GUIDE.md`, `RECONCILIATION_MVP_PHASE_6_TASK_PLAN.md` (**NEW**) | `T4.1` | Actual IDs/FKs preserved, documentation matches behavior, and task/validation status is recorded. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Persist and export approvals | Not started | Phase 1 and Phase 3 outputs | Establish sidecar format and owner-specific cleanup first. |
| Area 2: Supply trusted approvals | Not started | Area 1 | Reuse the normalization snapshot for both project operations. |
| Area 3: Block and allocate by mode | Not started | Area 2 | Remove candidate selection after trusted input is available. |
| Area 4: Preserve behavior and document | Not started | Areas 1-3 | Validate `VM-13` and update user guidance. |

## Definition Of Done

* [ ] `PH6-AC-1` to `PH6-AC-4` have `VM-13` evidence from `V-1` through `V-5`, including actual sidecar state, normalized IDs, SIMS requests, and blocked row results.
* [ ] Every work area and deliverable is complete; `V-1` through `V-6` are run and results recorded.
* [ ] Manual/unowned links, pre-linked IDs without conflict, tracked allocation, local Core FKs, and offline normalization have regression coverage.
* [ ] API, frontend, sidecar, ingester, and user-guide contracts agree; new errors are explicit, not success-shaped fallbacks.
* [ ] Existing Pyright diagnostics are distinguished from new errors, and deviations/follow-up work are documented.
* [ ] No unresolved question affects correctness or validation; stop and report if the implementation encounters repository behavior that contradicts this plan.

## Risks And Open Questions

* **Snapshot consistency:** Construct trusted approvals from the catalog already loaded by `ShapeShifter.normalize()`, not a later independent sidecar read. A concurrent external edit still requires the existing one-worker/write-version policy.
* **Partial two-file removal:** Removing sidecar approvals before saving the decision catalog can leave decisions present after a catalog failure. Preserve Phase 3's explicit partial-error and retry behavior; never report deletion as fully successful.
* **Mode and type-check baseline:** `site` is the pilot, but mode tests must exercise the other policies without enabling general rollout. Phase 3 recorded a Pyright workspace failure; do not misreport it as a new Phase 6 failure or silently ignore new diagnostics.
