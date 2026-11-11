# Reliable Reconciliation Links to Existing SEAD Entities — Phase 3 Task Plan

## Phase Summary

**Phase:** 3 — Owned Export, Cleanup, and Offline Normalization. **Readiness:** Validated for implementation. The [phase plan](RECONCILIATION_MVP_PHASE_PLAN.md#phase-3-owned-export-cleanup-and-offline-normalization) marks Phase 3 ready; it depends on the Phase 1 decision store, not Phase 2's unfinished review UI. This phase makes accepted decisions into committed, owner-tagged sidecar links and removes only links belonging to a removed decision or specification.

**Sources:** [Shape Shifter proposal](RECONCILIATION_MVP.md) (`SS-AC-4`, `SS-AC-6`) and [phase plan](RECONCILIATION_MVP_PHASE_PLAN.md) (`VM-6`, `VM-7`).

**Acceptance criteria**

1. [x] `PH3-AC-1` (from `SS-AC-4`): Export records the specification owner on each reconciliation link and removes only that owner's stale links, including when its specification is deleted.
2. [x] `PH3-AC-2` (from `SS-AC-4`): Export never removes manual or unowned links and stops on conflicting owners.
3. [x] `PH3-AC-3` (from `SS-AC-6`): Normalization applies committed links offline, preserves precedence, and produces the same `public_id` and foreign-key values on repeated runs.

**Fixed rules:** An owner is `(entity_name, target_field)`; `verified_at` remains empty until Phase 5. An accepted decision must have a target ID; rejected, proposed, and local-only decisions produce no link. Sidecar writes use a fresh snapshot, an expected content version, and atomic replacement under the project lock. An unowned link, regardless of its `source`, is protected like a manual link. Do not change fixed-row sync or add Authority Service calls. The deployment constraint is one backend worker; the lock is process-local.

## Repository Findings

**Repository basis:** Branch `reconciliation-mvp`, commit `315f9acf`, inspected 2026-10-30. The untracked Phase 2 task plan was present but not modified. The source proposal and phase plan were checked against the current code; Phase 2's UI changes are planned, not shipped.

| Verified source | Current behavior | Planning implication |
| --- | --- | --- |
| `src/reconciliation/mapping_model.py::{Link, MappingCatalog, encode_local_key}`; `src/reconciliation/model.py::{EntityResolutionCatalog, EntityResolutionSet}` | Sidecar `Link` has neither owner nor verification time; each entity has one link per encoded key. Decisions already have `local_key_value` and status. | Add optional, structured owner and `verified_at` without changing the sidecar version or rejecting old YAML. Compare decisions by their stored encoded key, never by the search label. |
| `backend/app/services/reconciliation/service.py::{export_to_mapping, _export_to_mapping_locked}`; `backend/app/api/v1/endpoints/reconciliation.py::export_reconciliation_to_mapping` | The authenticated export route obtains the project lock, loads the specification, then intentionally returns 400. Its response model has `exported`, `skipped_manual`, `entity`, and `field`. | Replace the guard with owned export; report stale removals and ownership conflicts explicitly. Preserve authentication, the 404 for a missing specification, and existing response fields. |
| `backend/app/services/mapping_service.py::MappingService`; `src/reconciliation/mapping_manager.py::{load_snapshot, save}` | The mapping service derives an entity's key and `public_id` from the project; a fresh snapshot includes an exact-byte version. `save(expected_version=...)` atomically replaces the sidecar or reports a stale version. | Reuse project/entity metadata and version-checked saves; validate a pre-existing entity mapping's key and `public_id` before writing. Skip the save entirely for an unchanged re-export. |
| `backend/app/services/reconciliation/mapping_manager.py::{delete, save_catalog}`; `backend/app/api/v1/endpoints/reconciliation.py::{delete_catalog, update_entity_mapping_registry, update_entity_resolution_catalog_raw}` | DELETE enforces `force` for nonempty decisions and returns the catalog; both whole-catalog PUT routes can also remove specifications. Catalog writes directly overwrite YAML; neither deletion path cleans the sidecar. | Coordinate every specification-removal path under the project lock. Clean sidecar links first and persist the catalog second, reporting partial failures rather than leaving an orphaned owned link. Preserve the catalog-shaped DELETE response for existing consumers. |
| `frontend/src/api/reconciliation.ts::deleteSpecification`; `frontend/src/stores/reconciliation.ts::deleteSpecification`; `frontend/src/components/reconciliation/{SpecificationsList,ReconciliationView}.vue` | The store assigns the DELETE response to `reconciliationConfig`; the list shows generic deletion success. Export feedback has only exported and skipped counts. | Add the removed count as an extra catalog field on DELETE, pass it through the store, and show both removal and export outcomes without breaking the existing catalog assignment. |
| `backend/app/api/v1/endpoints/mapping.py::_to_link_response`; `backend/app/models/mapping.py::MappingLinkResponse`; `frontend/src/types/reconciliation.ts` | Mapping GET serializes selected link fields, omitting new fields unless explicitly added. Frontend export types match the current response. | Expose optional owner/verification metadata in mapping GET; update export/deletion types and the counts in the view. Phase 2 can build on this contract but is not a prerequisite. |
| `src/normalizer.py::ShapeShifter._apply_mapping_sidecar_links`; `tests/process/test_shapeshifter.py`; `backend/tests/api/v1/test_reconciliation_export.py` | Normalization reads committed sidecar links without network calls, uses encoded keys, and leaves internal relationships on local `system_id`; existing export tests assert the temporary 400. | Replace guard tests with export/cleanup tests and add an offline repeated-run integration case asserting both external `public_id` and downstream local FK values. Keep normalization implementation unchanged unless the test demonstrates a defect. |

## Scope

**In scope:** Backward-compatible sidecar ownership and verification metadata; explicit, idempotent export for one entity/field; conflict checks and owner-specific cleanup after decision rejection/removal or specification deletion; whole-catalog removal routes; count-bearing API responses and existing UI feedback; regression tests and user documentation.

**Out of scope:** Candidate validation against the Authority Service, setting `verified_at`, ingester or SIMS binding changes, local-only export, automatic export on decision update, migrating old unowned links into owned links, changing normalization/fixed-row behavior, and implementing the Phase 2 review UI. Direct hand edits to YAML outside the API are not an atomic operation with sidecar cleanup.

## Work Breakdown

### Area 1: Persist backward-compatible ownership

**Objective:** New links can identify their owning specification without changing the meaning of older links.

**Affected code:** `src/reconciliation/{mapping_model,mapping_manager}.py`, `backend/app/models/mapping.py`, `backend/app/api/v1/endpoints/mapping.py`, `tests/reconciliation/test_mapping_sidecar.py`, `backend/tests/api/v1/test_mapping.py`.

**Dependencies:** Phase 1's keyed decisions and current sidecar model.

* [x] `T1.1` **Change:** Add owner and verification metadata to a sidecar link.
  * **Target:** `src/reconciliation/mapping_model.py::Link` and a typed owner model in the same file; `src/reconciliation/mapping_manager.py::MappingManager.save`.
  * **Current → required:** Only `source` indicates provenance → optional `owner: {entity_name, target_field}` and `verified_at: datetime | None`; absent fields on older links load as `None`.
  * **Implementation:** Require both nonempty owner components when present; keep manual/import and existing reconciliation links valid without an owner. Persist `verified_at: null` for newly owned, unverified links without adding null fields to all legacy links; retain all other link metadata and version `2.0`.
  * **Constraints:** The `owner` records the specification, not the user. An old unowned reconciliation link must not silently acquire ownership on read or during export.
  * **Validation:** `V-1`: round-trip old and new fixtures, assert the persisted owned-link `verified_at: null`, reject partial owners, and confirm old links survive a new owned-link write.
* [x] `T1.2` **Change:** Expose ownership and verification state through mapping GET.
  * **Target:** `backend/app/models/mapping.py::MappingLinkResponse`, `backend/app/api/v1/endpoints/mapping.py::_to_link_response`; `backend/tests/api/v1/test_mapping.py`.
  * **Current → required:** GET drops new fields → optional owner and `verified_at` in both entity and single-link responses.
  * **Implementation:** Map the typed sidecar fields at the API boundary; preserve existing fields and show absent verification as null, not as verified.
  * **Constraints:** Manual PUT remains manual and does not assign an owner or verification time.
  * **Validation:** `V-1`, `V-3`: assert API output for old/manual and new owned links.

**Completion evidence:** Existing sidecars still parse and mapping GET distinguishes owned, unowned, and unverified links.

### Area 2: Export only this specification's accepted links

**Objective:** Explicit export converges one owner's links to its accepted decisions without damaging other links.

**Affected code:** `backend/app/services/reconciliation/service.py`, `backend/app/models/reconciliation.py`, `backend/app/api/v1/endpoints/reconciliation.py`, `backend/tests/api/v1/test_reconciliation_export.py`, `backend/tests/services/test_mapping_write_coordination.py`.

**Dependencies:** Area 1.

* [x] `T2.1` **Change:** Replace the temporary export guard with a version-checked, idempotent reconciliation.
  * **Target:** `ReconciliationService::{export_to_mapping, _export_to_mapping_locked}` in `backend/app/services/reconciliation/service.py`; `backend/tests/api/v1/test_reconciliation_export.py`.
  * **Current → required:** All exports return 400 → load the Phase 1 `version: "3.0"` catalog and a fresh mapping sidecar snapshot under the project lock; create/update committed reconciliation links for accepted decisions and remove only this owner's links no longer accepted.
  * **Implementation:** Use stored `local_key_value` (including compound-key escaping) as the sidecar key and the project entity's ordered business keys and `public_id` as entity metadata. Validate existing sidecar metadata and target ID before mutation; ID `0` is valid. Preserve manual, import, and all unowned entries; skip an accepted decision occupied by a protected link. Reject with a 409 and no changes when a key is owned by a different specification **or** another specification has an accepted claim on the same entity/key. Preflight all keys and conflicts before saving. For changed links, set `source: reconciliation`, `owner` to the current pair, `committed_at`, and `verified_at: null`. Do not replace identical owned links, update their timestamps, or write a no-op snapshot. Save once with the snapshot's expected version; convert a version conflict to an actionable 409.
  * **Constraints:** An unowned reconciliation entry is protected even when the owner now accepts that key. Do not call the Authority Service or export local-only decisions. Re-export after rejection/removal must leave unrelated owners and draft/manual/unowned links untouched.
  * **Validation:** `V-2`, `V-3`: initial export, same-content no-op (bytes/timestamps unchanged), changed target, rejection/removal, local-only, manual/unowned skip, conflicting owner/claims, metadata mismatch, version conflict and missing specification.
* [x] `T2.2` **Change:** Return and display accurate export counts.
  * **Target:** `backend/app/models/reconciliation.py::ExportToMappingResult`, `backend/app/api/v1/endpoints/reconciliation.py::export_reconciliation_to_mapping`, `frontend/src/types/reconciliation.ts::ExportToMappingResult`, `frontend/src/components/reconciliation/ReconciliationView.vue::handleExportToMapping`, `frontend/src/components/reconciliation/__tests__/ReconciliationView.test.ts`.
  * **Current → required:** Response/feedback omit removals → add `removed` while retaining `exported`, `skipped_manual`, `entity`, and `field`.
  * **Implementation:** Define `exported` as created/changed links, `removed` as stale owned links deleted, and `skipped_manual` as accepted links blocked by manual or other unowned links; an identical re-export reports zero writes. Update the frontend notification and tests without claiming that export verified the IDs.
  * **Constraints:** Keep response fields stable for existing clients; never present a 409 or persistence error as a successful export.
  * **Validation:** `V-2`, `V-4`, `V-6`: exact response keys and counts for first, repeated, blocked, and cleanup exports.

**Completion evidence:** Export changes precisely the intended owned keys, returns countable outcomes, and fails closed before any conflicting write.

### Area 3: Clean owned links on every specification removal

**Objective:** Deleting a specification removes its links, reports their count, and cannot leave an owned link orphaned when sidecar cleanup fails.

**Affected code:** `backend/app/services/reconciliation/{service,mapping_manager}.py`, `backend/app/api/v1/endpoints/reconciliation.py`, `backend/app/models/reconciliation.py`, `frontend/src/{api/reconciliation.ts,stores/reconciliation.ts,types/reconciliation.ts}`, `frontend/src/components/reconciliation/SpecificationsList.vue`, `backend/tests/api/v1/test_reconciliation_specifications.py`; `frontend/src/components/reconciliation/__tests__/SpecificationsList.test.ts` (**NEW**).

**Dependencies:** Areas 1–2.

* [x] `T3.1` **Change:** Coordinate DELETE and whole-catalog removals with sidecar cleanup.
  * **Target:** `ReconciliationService` and `EntityMappingManager::{delete, save_catalog}` in `backend/app/services/reconciliation/`; `backend/app/api/v1/endpoints/reconciliation.py::{delete_catalog, update_entity_mapping_registry, update_entity_resolution_catalog_raw}`; `backend/tests/api/v1/test_reconciliation_specifications.py`.
  * **Current → required:** DELETE and catalog PUT/raw can remove a spec without cleaning its links → under the same project lock, compare the old and requested catalog; for each removed `(entity_name, target_field)`, delete only matching owned sidecar links from a fresh snapshot and save it with `expected_version` **before** persisting the new catalog.
  * **Implementation:** Preserve the existing `force=False` refusal for a nonempty DELETE and allow `force=True` to remove both decisions and owned links; an empty-spec DELETE still cleans previously owned links. Route both whole-catalog PUT forms through the same removal coordinator instead of direct `save_catalog`. Remove or refactor direct spec-deletion persistence so an API path cannot bypass cleanup. Use atomic catalog replacement rather than a truncating direct write for these coordinated saves. On a sidecar version conflict return 409 without changing the catalog; on a sidecar write failure, keep the old catalog and return an error. If the later catalog write fails, explicitly report a partial operation (spec still present, owned links already removed) so the operator can retry export or deletion. Do not claim a transaction across two files.
  * **Constraints:** Never delete manual, unowned, or other-owner links. Do not remove links merely because a specification's metadata changes or its decision changes; export remains explicit. Keep the existing raw YAML validation and error reporting.
  * **Validation:** `V-3`: DELETE without/with `force`, empty spec with links, other owners/unowned/manual survival, whole-catalog JSON and raw removal, sidecar version/write failure, catalog write failure and retry; assert both files and status rather than just the HTTP response.
* [x] `T3.2` **Change:** Report the cleanup count without breaking the existing catalog-shaped DELETE response.
  * **Target:** `backend/app/models/reconciliation.py` (DELETE result extending `EntityResolutionCatalog`), `backend/app/api/v1/endpoints/reconciliation.py::delete_catalog`, `frontend/src/api/reconciliation.ts::deleteSpecification`, `frontend/src/stores/reconciliation.ts::deleteSpecification`, `frontend/src/types/reconciliation.ts`, `frontend/src/components/reconciliation/SpecificationsList.vue::performDelete`; `frontend/src/components/reconciliation/__tests__/SpecificationsList.test.ts` (**NEW**).
  * **Current → required:** DELETE returns only the updated catalog and shows generic success → include `removed_owned_links` alongside existing top-level catalog fields, return that count from the store, and show it on successful deletion.
  * **Implementation:** Keep `version`, `service_url`, and `entities` at the response root so `reconciliationConfig` and existing consumers still receive a catalog. Update the API and frontend types; use the actual cleanup count (including zero), not the number of catalog decisions removed. Preserve the existing error notification for a failed delete.
  * **Constraints:** Do not call the deletion successful if either file fails to persist.
  * **Validation:** `V-3`, `V-4`, `V-6`: check exact response shape, catalog assignment, removal count, and failure feedback.

**Completion evidence:** Every API path that removes a specification cleans only its owned links first, and DELETE callers see an accurate removal count.

### Area 4: Prove offline normalization and document the workflow

**Objective:** The exported sidecar produces stable IDs and local FK links, and the guide accurately describes the shipped export.

**Affected code:** `backend/tests/api/v1/test_reconciliation_export.py`, `tests/process/test_shapeshifter.py`, `docs/USER_GUIDE.md`.

**Dependencies:** Areas 1–3.

* [x] `T4.1` **Change:** Test normalization against an actually exported owned sidecar.
  * **Target:** `backend/tests/api/v1/test_reconciliation_export.py`, `tests/process/test_shapeshifter.py`.
  * **Current → required:** Existing tests assert guard 400 or isolated manual sidecar application → export an accepted key through the protected route and run normalization twice with network access disabled.
  * **Implementation:** Include a parent and dependent child with a local `system_id` relationship and an exported parent `public_id`; assert exact parent `public_id` and child's FK equals the parent's **local** `system_id`, not the external ID, on two independently initialized runs. Include committed manual, owned reconciliation, and unowned/draft cases to preserve precedence and ensure catalog-only decisions never apply. Patch external clients to fail if normalization calls them; compare actual output columns and values, not just request counts.
  * **Constraints:** No change to `src/normalizer.py` unless the new regression test shows a Phase 3 defect; preserve the Extract → Filter → Link → Unnest → Translate → Store order.
  * **Validation:** `V-5`: identical IDs/FKs on both offline runs, correct precedence, no unexpected client calls.
* [x] `T4.2` **Change:** Replace the obsolete export-unavailable user guidance and record implementation checks.
  * **Target:** `docs/USER_GUIDE.md::Reconciliation Workflow`, `How Mappings Are Stored`; this plan's progress tracker.
  * **Current → required:** The guide says export is unavailable → explain explicit export, owner-specific re-export/deletion cleanup, protected manual/unowned links, possible conflict, and empty `verified_at` until Phase 5.
  * **Implementation:** Keep the existing note about the currently unfinished review grid until Phase 2 actually ships. Record actual test results and any deviations in this plan during implementation; stop and report if current source or configuration conflicts materially with the plan rather than inventing a replacement design.
  * **Constraints:** Do not promise live checking or a cross-file transaction.
  * **Validation:** `V-6`: docs match tested behavior, links resolve, and frontend/backend contracts type-check.

**Completion evidence:** A real export drives repeatable offline normalization and the user guide no longer claims export is disabled.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
| --- | --- | --- | --- |
| `PH3-AC-1` (`SS-AC-4`, `VM-6`) | `T1.1`, `T2.1`, `T2.2`, `T3.1`, `T3.2` | `V-1`, `V-2`, `V-3`, `V-4` | Owned committed links have empty verification time; stale links are removed on re-export and all specification-removal routes; DELETE reports the exact count. |
| `PH3-AC-2` (`SS-AC-4`, `VM-6`) | `T1.1`, `T2.1`, `T3.1` | `V-1`, `V-2`, `V-3` | Manual/unowned/other-owner links survive, and competing claims return 409 before a write. |
| `PH3-AC-3` (`SS-AC-6`, `VM-7`) | `T1.1`, `T2.1`, `T4.1` | `V-2`, `V-5` | Offline repeated runs have identical actual parent `public_id` and dependent local FK values, with unchanged committed-link precedence. |

## Validation And Testing

| ID | Check and target | Exact command or method | Covers | Expected result | Baseline (2026-10-30) |
| --- | --- | --- | --- | --- | --- |
| `V-1` | Sidecar backward compatibility and mapping GET: `tests/reconciliation/test_mapping_sidecar.py`, `backend/tests/api/v1/test_mapping.py`; old YAML, new owner, null verification, malformed owner | `uv run pytest -o addopts='' -q tests/reconciliation/test_mapping_sidecar.py backend/tests/api/v1/test_mapping.py` | `PH3-AC-1`, `PH3-AC-2` | Old links parse unchanged; new fields round-trip and are visible without falsely marking verified. | Pass: sidecar tests included in a 52-pass selected Core/backend run. Not run: new owner/GET assertions. |
| `V-2` | Protected export: `backend/tests/api/v1/test_reconciliation_export.py`; accepted, rejected, removed, proposed, local-only, encoded keys, no-op, manual/unowned and owner conflicts, missing spec, invalid metadata and version conflict | `uv run pytest -o addopts='' -q backend/tests/api/v1/test_reconciliation_export.py` | `PH3-AC-1`, `PH3-AC-2`, `PH3-AC-3` | One atomic version-checked sidecar update per changed export; no modification for conflict or no-op; counts match actual changes. | Pass: existing temporary-guard tests included in 52-pass run; new export behavior not run. |
| `V-3` | Specification deletion and write ordering: `backend/tests/api/v1/test_reconciliation_specifications.py`, `backend/tests/services/test_mapping_write_coordination.py`, `backend/tests/api/v1/test_mapping.py`; force, JSON/raw removal, two-file failures, other links | `uv run pytest -o addopts='' -q backend/tests/api/v1/test_reconciliation_specifications.py backend/tests/services/test_mapping_write_coordination.py backend/tests/api/v1/test_mapping.py` | `PH3-AC-1`, `PH3-AC-2` | Old catalog retained if sidecar fails; atomic catalog write prevents truncated YAML; partial catalog failure is reported; unaffected links survive. | Pass: specification tests included in 52-pass run. Not run: new cleanup/failure assertions and other two files in this command. |
| `V-4` | Export and deletion UI: `frontend/src/components/reconciliation/__tests__/ReconciliationView.test.ts`, `frontend/src/components/reconciliation/__tests__/SpecificationsList.test.ts` (**NEW**); count-bearing responses and errors | `cd frontend && pnpm exec vitest run src/components/reconciliation/__tests__/ReconciliationView.test.ts src/components/reconciliation/__tests__/SpecificationsList.test.ts` | `PH3-AC-1` | Updated export and deletion notices show actual counts, preserve catalog state, and surface failures. | Pass: existing view file, 3 tests. Not run: planned list test file does not exist. |
| `V-5` | Offline export-to-normalize/FK regression: `backend/tests/api/v1/test_reconciliation_export.py`, `tests/process/test_shapeshifter.py`; two fresh runs with no network | `uv run pytest -o addopts='' -q backend/tests/api/v1/test_reconciliation_export.py tests/process/test_shapeshifter.py` | `PH3-AC-3` | Both runs produce identical parent external `public_id` and child local FK; manual precedence and draft skip remain. | Pass: relevant existing tests included in 52-pass run. Not run: planned end-to-end FK/offline assertion. |
| `V-6` | Type, format, user guidance and links: changed Python/TS files and `docs/USER_GUIDE.md` | `uv run black --check src/reconciliation/mapping_model.py src/reconciliation/mapping_manager.py backend/app/services/reconciliation/service.py backend/app/services/reconciliation/mapping_manager.py backend/app/api/v1/endpoints/reconciliation.py backend/app/api/v1/endpoints/mapping.py backend/app/models/reconciliation.py backend/app/models/mapping.py backend/tests/api/v1/test_reconciliation_export.py backend/tests/api/v1/test_reconciliation_specifications.py backend/tests/api/v1/test_mapping.py backend/tests/services/test_mapping_write_coordination.py tests/reconciliation/test_mapping_sidecar.py tests/process/test_shapeshifter.py && uv run pyright --threads 2 src backend && (cd frontend && pnpm exec vue-tsc --noEmit) && make check-doc-links` | All criteria and contracts | Formatting, type checks, and documentation link check pass after edits; guide agrees with tests. | Not run: planned files/contracts do not yet exist; check after implementation. |

### Implementation Results

* `V-1`: `rtk uv run pytest -o addopts='' -q tests/reconciliation/test_mapping_sidecar.py backend/tests/api/v1/test_mapping.py` — passed, 43 tests.
* `V-2`: `rtk uv run pytest -o addopts='' -q backend/tests/api/v1/test_reconciliation_export.py` — passed, 11 tests.
* `V-3`: `rtk uv run pytest -o addopts='' -q backend/tests/api/v1/test_reconciliation_specifications.py backend/tests/services/test_mapping_write_coordination.py backend/tests/api/v1/test_mapping.py` — passed, 45 tests.
* `V-4`: `cd frontend && rtk pnpm exec vitest run src/components/reconciliation/__tests__/ReconciliationView.test.ts src/components/reconciliation/__tests__/SpecificationsList.test.ts` — passed, 10 tests.
* `V-5`: `rtk uv run pytest -o addopts='' -q backend/tests/api/v1/test_reconciliation_export.py tests/process/test_shapeshifter.py` — passed, 63 tests.
* `V-6`: Black passed with 14 files unchanged; `rtk uv run pyright --threads 2 src backend` failed with 134 workspace diagnostics. The diagnostics in files changed for this phase point to unchanged candidate-handling and existing fixture code, not the new implementation. `cd frontend && rtk pnpm exec vue-tsc --noEmit` and `rtk make check-doc-links` passed.

The initial focused baseline was `rtk uv run pytest -o addopts='' -q backend/tests/api/v1/test_reconciliation_export.py backend/tests/api/v1/test_reconciliation_specifications.py tests/reconciliation/test_mapping_sidecar.py tests/process/test_shapeshifter.py -k 'reconciliation or mapping or sidecar or normalize'`: **52 passed, 38 deselected**. The baseline uses the temporary export guard; it does not demonstrate Phase 3 functionality.

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Typed owned sidecar and tests | `src/reconciliation/mapping_model.py`, `src/reconciliation/mapping_manager.py`, `tests/reconciliation/test_mapping_sidecar.py` | `T1.1` | Old and new YAML round-trip; owned YAML has an empty verification field. |
| Mapping GET contract and tests | `backend/app/models/mapping.py`, `backend/app/api/v1/endpoints/mapping.py`, `backend/tests/api/v1/test_mapping.py` | `T1.2` | Owner and null verification appear in API output. |
| Owned export and counts | `backend/app/services/reconciliation/service.py`, `backend/app/models/reconciliation.py`, `backend/app/api/v1/endpoints/reconciliation.py`, `backend/tests/api/v1/test_reconciliation_export.py` | `T2.1`, `T2.2`, `T4.1` | Export/re-export/conflict/FK tests pass. |
| Coordinated deletion and failure tests | `backend/app/services/reconciliation/mapping_manager.py`, `backend/app/services/reconciliation/service.py`, `backend/app/api/v1/endpoints/reconciliation.py`, `backend/tests/api/v1/test_reconciliation_specifications.py`, `backend/tests/services/test_mapping_write_coordination.py` | `T3.1`, `T3.2` | DELETE and JSON/raw removal clean only owned links and report failures. |
| Frontend contracts and feedback | `frontend/src/types/reconciliation.ts`, `frontend/src/api/reconciliation.ts`, `frontend/src/stores/reconciliation.ts`, `frontend/src/components/reconciliation/ReconciliationView.vue`, `frontend/src/components/reconciliation/SpecificationsList.vue`, `frontend/src/components/reconciliation/__tests__/ReconciliationView.test.ts`, `frontend/src/components/reconciliation/__tests__/SpecificationsList.test.ts` (**NEW**) | `T2.2`, `T3.2` | Counts and errors match API results. |
| Offline normalization regression | `tests/process/test_shapeshifter.py`, `backend/tests/api/v1/test_reconciliation_export.py` | `T4.1` | External IDs and local FK values repeat without network. |
| User guidance and tracker | `docs/USER_GUIDE.md`, this task plan | `T4.2` | Guide accurately describes shipped behavior; completed tasks have recorded checks. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Persist ownership | Complete | Phase 1 decision store | V-1 passed; old links remain compatible and owned/unverified fields round-trip through mapping GET. |
| Area 2: Export accepted links | Complete | Area 1 | V-2 passed; export is keyed, owner-specific, version-checked, and reports changes and protected links. |
| Area 3: Clean on removal | Complete | Areas 1–2 | V-3 and V-4 passed; DELETE and both catalog replacement routes clean owned links and report outcomes. |
| Area 4: Offline regression and docs | Partial | Areas 1–3 | V-5 passed and the guide is updated. V-6 Pyright reports 134 workspace diagnostics; diagnostics in touched files are at unchanged code. |

## Definition Of Done

* [x] `PH3-AC-1` and `PH3-AC-2` pass `VM-6` (`V-1`–`V-4`): owned export/re-export/deletion counts, protected links, conflicting claims, and failure paths.
* [x] `PH3-AC-3` passes `VM-7` (`V-5`): two offline runs show the same external parent IDs and local child FK values.
* [ ] Every work area and deliverable is complete; `V-6` passes and mapping/export/deletion API and frontend types agree.
* [x] Old sidecars, existing `force` behavior, fixed-row sync, manual precedence, project lock, and version-checked saves retain regression coverage.
* [x] User guidance and this tracker reflect the implementation; deviations and necessary follow-ups are recorded; no implementation-blocking decision remains.

## Risks And Open Questions

* **Two files, no transaction:** Sidecar-first deletion prevents an orphaned owned link if cleanup fails, but a later catalog failure can leave the specification present without its exported links. Return an explicit partial error and allow a safe retry; test both files. Atomic replacement of the catalog prevents an additional partial-file failure.
* **External writes and process-local locking:** Hand edits or multiple backend workers are outside the one-worker coordination guarantee. A stale sidecar save must fail rather than overwrite someone else's edit.
* **Other sidecar writers:** Fixed-row sync or an explicit manual upsert may replace an owned link at a key; an unowned or manual replacement remains protected on re-export. No migration or retroactive ownership assignment is permitted.
