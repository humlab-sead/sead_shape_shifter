# Reconciliation Feature: Document, Issue, and Code Map

**Reviewed:** 2026-10-30  
**Purpose:** Locate the project records and code paths needed to assess the current reconciliation feature.

## Summary

The history starts with feature and UX requests in December 2025 and January 2026. The central persistence redesign is recorded later in the reconciliation persistence consolidation proposal and GitHub issue #465. A newer fixed-row synchronization proposal records an implementation merged in PR #562 and names a remaining cross-process locking limitation. The future improvements proposal remains a placeholder for reconciliation review lifecycle features.

There are two distinct catalogs in the implementation:

- The reconciliation catalog stores reconciliation specifications and match results for review. The backend reconciliation `EntityMappingManager` reads and writes it.
- The mapping sidecar stores links that Core applies to `public_id` during normalization. The Core `MappingManager` reads and writes it.

Results in the reconciliation catalog are not applied during normalization until they are exported to the mapping sidecar.

## User Workflow

1. **Open the project’s Reconciliation view.** Check that the reconciliation service is online and provides the target entity types. The project must have usable data for the entity to reconcile.
2. **Create or edit a specification.** Choose the entity and target field. Configure the source (the entity’s own data, another entity, or a SQL query), remote service type, property mappings, and auto-accept and review thresholds. Correct validation errors, then save the form or YAML.
3. **Select the specification and run auto-reconciliation.** Shape Shifter sends eligible source values and configured properties to the reconciliation service. It classifies matches by the configured thresholds and stores the results in the reconciliation catalog.
4. **Review and adjust results.** In the grid, inspect IDs, confidence, and notes. Depending on the row and available candidates, accept a candidate or search for alternatives. You can also edit an ID or note, bulk accept or reject selected rows, mark a value as Local-Only with an optional reason, and preview the data. Review decisions are saved to the reconciliation catalog.
5. **Export accepted links to Mapping.** Click **Export to Mapping** for the selected entity and target field. The backend copies eligible results into the mapping sidecar, skips links that already have a manual mapping, and reports exported and skipped counts.
6. **Run normalization.** Core reads committed links from the mapping sidecar and applies them to the entity’s `public_id` column. When multiple sources define a link, precedence is manual, reconciliation, then import. Core foreign-key relationships continue to use local `system_id` values.
7. **Maintain links after fixed-entity edits.** Shape Shifter synchronizes relevant fixed-row changes with the mapping sidecar. If rows save but the sidecar update fails, the entity editor shows pending mapping changes; use **Retry mapping** to retry.

### Current UI Details

- The current Reconciliation view calls the synchronous auto-reconcile route and waits for its response before showing result counts. The backend also has asynchronous progress endpoints.
- The auto-reconcile response includes candidate lists, but the current view reloads preview data without passing those lists through, and the preview response does not include candidates. Candidate selection may therefore have no candidate rows after auto-reconciliation; **Alternative Search** fetches candidates separately. This code path is in [ReconciliationView.vue](../../../frontend/src/components/reconciliation/ReconciliationView.vue), [ReconciliationGrid.vue](../../../frontend/src/components/reconciliation/ReconciliationGrid.vue), and [reconciliation service](../../../backend/app/services/reconciliation/service.py).

## Proposal and Documentation Inventory

| Record | What it covers | Status notes |
|---|---|---|
| [Proposal index](../../proposals/README.md) | Current proposal organization. | Lists reconciliation future improvements as a placeholder. The completed persistence consolidation is in done/ but is not listed as a separate reconciliation entry in the index. |
| [Reconciliation Persistence Consolidation](../../proposals/done/RECONCILIATION_PERSISTENCE_CONSOLIDATION.md) | Mapping storage, mapping precedence, materialized-row synchronization, and explicit export from reconciliation results. | Its header still says “Design Review” although the file is under done and issue #465 says the work shipped in v2.1.0. Use it as design history and compare its claims with later code and records. |
| [Persistence Consolidation task plans](../../proposals/done/RECONCILIATION_PERSISTENCE_CONSOLIDATION_TASK_PLANS.md) | Detailed acceptance criteria and implementation breakdown for the sidecar, normalization, materialization sync, APIs, and export. | Status markers conflict: the file says “Planning,” while many tasks are checked and other progress summaries remain unchecked. Do not use its checkboxes alone as the current status. |
| [Materialized Entity Mapping Sync](../../proposals/done/MATERIALIZED_ENTITY_MAPPING_SYNC/MATERIALIZED_ENTITY_MAPPING_SYNC.md) | Follow-up for fixed-row and materialized-entity changes that synchronize mapping sidecar links. | Says implemented, with phases 1–4 passed and merged in [PR #562](https://github.com/humlab-sead/sead_shape_shifter/pull/562). It identifies the process-local project lock as a remaining limitation for writes from independent processes. |
| [Conditional Target Model Requirements](../../proposals/done/CONDITIONAL_TARGET_MODEL_REQUIREMENTS/CONDITIONAL_TARGET_MODEL_REQUIREMENTS.md) | Target-model requirements that depend on reconciliation selecting rows for insertion. | Adjacent to reconciliation execution; useful when assessing validation and change-request generation, rather than the reconciliation UI or match lifecycle. |
| [Reconciliation Future Improvements](../../proposals/RECONCILIATION_FUTURE_IMPROVEMENTS.md) | Draft/committed states, reviewer decisions, audit history, rollback, and translating reconciliation values to sidecar local keys. | Explicitly a placeholder with no finalized scope. |
| [Reconciliation guide](../../other/RECONCILIATION_GUIDE.md) | User workflow, configuration, review, and export context. | Supporting documentation; compare operational details with the newer proposals and code. |

## GitHub Issues and Pull Request

Issue states below were checked on 2026-10-30.

| Issue or PR | State | Relevance |
|---|---|---|
| [#47 — Add a SEAD reconciliation feature](https://github.com/humlab-sead/sead_shape_shifter/issues/47) | Closed | Early feature definition: reconcile selected metadata/lookups and assign target identities. |
| [#21 — Add UX for mapping/reconciling remote entities](https://github.com/humlab-sead/sead_shape_shifter/issues/21) | Closed | Early UX request for assigning remote target IDs to local entities. |
| [#203 — Introduce three-tier identity system](https://github.com/humlab-sead/sead_shape_shifter/issues/203) | Closed | Identity model background: local system IDs, business keys, and target-facing public IDs. |
| [#86](https://github.com/humlab-sead/sead_shape_shifter/issues/86), [#92](https://github.com/humlab-sead/sead_shape_shifter/issues/92), [#94](https://github.com/humlab-sead/sead_shape_shifter/issues/94) | Closed | Early implementation tasks for service URL configuration, service health, and a reconciliation CLI. |
| [#98](https://github.com/humlab-sead/sead_shape_shifter/issues/98), [#99](https://github.com/humlab-sead/sead_shape_shifter/issues/99), [#125](https://github.com/humlab-sead/sead_shape_shifter/issues/125) | Closed | Specification configuration and editing: multiple specifications, project-level editing, and full YAML editing. |
| [#120](https://github.com/humlab-sead/sead_shape_shifter/issues/120), [#122](https://github.com/humlab-sead/sead_shape_shifter/issues/122), [#124](https://github.com/humlab-sead/sead_shape_shifter/issues/124) | Closed | Early UI defects involving service entity counts, alternative search, and extra-column property mappings. |
| [#121 — Dual-mode editing of reconciliation specifications](https://github.com/humlab-sead/sead_shape_shifter/issues/121) | Closed 2026-10-09 | Added form and YAML editing; its follow-up schema issue is #534. |
| [#534 — Reconciliation-aware Monaco schema](https://github.com/humlab-sead/sead_shape_shifter/issues/534) | Closed 2026-10-20 | Corrected schema intelligence for the reconciliation YAML editor. |
| [#465 — Consolidate reconciliation storage](https://github.com/humlab-sead/sead_shape_shifter/issues/465) | Closed 2026-10-20; released in v2.1.0 | Main implementation issue for mapping sidecar storage, fixed-entity synchronization, and export from the reconciliation catalog. Links to the consolidation proposal. |
| [#551 — Evaluate conditional FK requirements after reconciliation](https://github.com/humlab-sead/sead_shape_shifter/issues/551) | Closed 2026-10-26 | Adjacent target-model behavior; its implementation is associated with PR #552 and the Conditional Target Model Requirements proposal. |
| [#592 — Allow materialization of SQL entities without business keys](https://github.com/humlab-sead/sead_shape_shifter/issues/592) | Closed 2026-10-26 | Fixed-entity mapping edge case: a save without business keys should not fail after partially changing project files. |
| [#617 — Export validation/reconciliation reports](https://github.com/humlab-sead/sead_shape_shifter/issues/617) | Open, created 2026-10-28 | Current feature request for reports that show project validation issues and mapping details. |
| [PR #562 — Materialized Entity Mapping Sync](https://github.com/humlab-sead/sead_shape_shifter/pull/562) | Merged | Implementation record for the newer fixed-row synchronization follow-up. This is a pull request, not an issue. |

## Code Map

### Reconciliation Catalog: Specifications, Matches, and Review

| File | Main classes or responsibility |
|---|---|
| [src/reconciliation/model.py](../../../src/reconciliation/model.py) | Core domain types: `ResolutionSource`, `ResolutionTarget`, `ResolvedEntityPair`, `EntityResolutionMetadata`, `EntityResolutionSet`, and `EntityResolutionCatalog`. |
| [src/reconciliation/source_strategy.py](../../../src/reconciliation/source_strategy.py) | `SourceStrategyType` and `ReconciliationSourceStrategy` select whether input comes from the target entity, another project entity, or a SQL query. |
| [backend/app/services/reconciliation/resolvers.py](../../../backend/app/services/reconciliation/resolvers.py) | `ReconciliationSourceResolver` and the target-entity, another-entity, and SQL-query resolver implementations load the rows to reconcile. |
| [backend/app/clients/reconciliation_client.py](../../../backend/app/clients/reconciliation_client.py) | `ReconciliationClient` calls the external OpenRefine-compatible service for matching, suggestions, health, and manifest data. |
| [backend/app/services/reconciliation/service.py](../../../backend/app/services/reconciliation/service.py) | `ReconciliationQueryService` builds requests; `ReconciliationService` coordinates source loading, matching, thresholds, candidate review, catalog persistence, preview, and export. |
| [backend/app/services/reconciliation/mapping_manager.py](../../../backend/app/services/reconciliation/mapping_manager.py) | Backend `EntityMappingManager` loads and saves the reconciliation catalog. Despite its name, it is not the Core mapping-sidecar manager. |
| [backend/app/models/reconciliation.py](../../../backend/app/models/reconciliation.py) and [backend/app/mappers/reconciliation_mapper.py](../../../backend/app/mappers/reconciliation_mapper.py) | API request/response models and conversions between API models and Core reconciliation domain types. |
| [backend/app/api/v1/endpoints/reconciliation.py](../../../backend/app/api/v1/endpoints/reconciliation.py) | HTTP routes for configuration, preview, auto-reconcile, progress, review updates, suggestions, and export-to-mapping. |

Frontend components:

- [ReconciliationView.vue](../../../frontend/src/components/reconciliation/ReconciliationView.vue) coordinates configuration, YAML editing, auto-reconcile, review, and export.
- [stores/reconciliation.ts](../../../frontend/src/stores/reconciliation.ts) holds reconciliation state and actions; [api/reconciliation.ts](../../../frontend/src/api/reconciliation.ts) calls the backend routes; [types/reconciliation.ts](../../../frontend/src/types/reconciliation.ts) defines frontend API types.
- [SpecificationsList.vue](../../../frontend/src/components/reconciliation/SpecificationsList.vue) and [SpecificationEditor.vue](../../../frontend/src/components/reconciliation/SpecificationEditor.vue) manage specifications.
- [ReconciliationGrid.vue](../../../frontend/src/components/reconciliation/ReconciliationGrid.vue), [AlternativeSearchDialog.vue](../../../frontend/src/components/reconciliation/AlternativeSearchDialog.vue), [PreviewMatchedDataDialog.vue](../../../frontend/src/components/reconciliation/PreviewMatchedDataDialog.vue), and [ReconciliationProgressDialog.vue](../../../frontend/src/components/reconciliation/ReconciliationProgressDialog.vue) support review, alternative searches, preview, and progress display.

### Mapping Sidecar: Links Applied by Core

| File | Main classes or responsibility |
|---|---|
| [src/reconciliation/mapping_model.py](../../../src/reconciliation/mapping_model.py) | `MappingCatalog`, `EntityMapping`, `Link`, `LinkSource`, and local-key encode/decode helpers define the mapping sidecar data. |
| [src/reconciliation/mapping_manager.py](../../../src/reconciliation/mapping_manager.py) | Core `MappingManager` loads, validates versions, caches, and saves the `{project}-mapping.yml` sidecar. |
| [src/reconciliation/mapping_validator.py](../../../src/reconciliation/mapping_validator.py) | Checks sidecar public IDs and local keys against an entity’s configuration. |
| [backend/app/mappers/project_mapper.py](../../../backend/app/mappers/project_mapper.py) | Loads and validates sidecar mappings while converting API project configuration into the Core project model. |
| [src/normalizer.py](../../../src/normalizer.py) | `ShapeShifter` loads the sidecar for normalization and applies committed links to `public_id`; precedence is manual, reconciliation, then import. |
| [backend/app/services/mapping_service.py](../../../backend/app/services/mapping_service.py) and [backend/app/api/v1/endpoints/mapping.py](../../../backend/app/api/v1/endpoints/mapping.py) | Backend sidecar operations and HTTP routes for reading, writing, deleting, and retrying mapping links. |

The export route is in `backend/app/api/v1/endpoints/reconciliation.py`. It calls `ReconciliationService.export_to_mapping()`, which copies accepted reconciliation results into the mapping sidecar and skips keys with existing manual links.

### Fixed-Row Saves and Mapping Synchronization

| File | Main classes or responsibility |
|---|---|
| [src/reconciliation/fixed_entity_mapping_changes.py](../../../src/reconciliation/fixed_entity_mapping_changes.py) | Pure Core comparison and update logic: `RowSnapshot`, `LinkUpsert`, `LinkDelete`, `FixedRowChangeSet`, and change-set functions. |
| [src/reconciliation/fixed_entity_mapping_retry.py](../../../src/reconciliation/fixed_entity_mapping_retry.py) | `FixedMappingRetryPlan` checks whether pending changes can be safely retried against current rows and sidecar links. |
| [backend/app/services/fixed_entity_mapping_change_service.py](../../../backend/app/services/fixed_entity_mapping_change_service.py) | Prepares fixed-row changes and reads the mapping configuration used to calculate them. |
| [backend/app/services/fixed_entity_mapping_sync_service.py](../../../backend/app/services/fixed_entity_mapping_sync_service.py) | Applies a prepared change set to a versioned mapping snapshot and reports write conflicts or failures. |
| [backend/app/services/fixed_entity_mapping_retry_service.py](../../../backend/app/services/fixed_entity_mapping_retry_service.py) | Rechecks and retries mapping changes after a partial save. The route is in `backend/app/api/v1/endpoints/mapping.py`. |
| [backend/app/services/project/entity_operations.py](../../../backend/app/services/project/entity_operations.py) | Connects inline fixed-entity row saves to the change and sync services. |
| [backend/app/services/entity_values_service.py](../../../backend/app/services/entity_values_service.py) | Connects external fixed-entity value updates to mapping synchronization. |
| [backend/app/services/materialization_service.py](../../../backend/app/services/materialization_service.py) and [backend/app/api/v1/endpoints/materialization.py](../../../backend/app/api/v1/endpoints/materialization.py) | Materialized-entity mapping sync operations, including the explicit rebuild/sync endpoint. |

### Focused Tests

- Core mapping and change behavior: [tests/reconciliation](../../../tests/reconciliation), including `test_mapping_sidecar.py`, `test_fixed_entity_mapping_changes.py`, and `test_fixed_entity_mapping_retry.py`.
- Reconciliation service and mocked client behavior: [backend/tests/services/test_reconciliation_service.py](../../../backend/tests/services/test_reconciliation_service.py) and [backend/tests/test_reconciliation_client.py](../../../backend/tests/test_reconciliation_client.py). The port-8000 URL construction case remains here because its HTTP request is mocked.
- Live reconciliation service tests: [backend/tests/integration/test_reconciliation_client.py](../../../backend/tests/integration/test_reconciliation_client.py). It contains six tests for health, manifest, batch reconciliation, suggestions, and connection diagnostics; all are marked `integration`.
- Select those live tests with `uv run pytest backend/tests/integration/test_reconciliation_client.py -m integration`. Exclude marked integration tests with `uv run pytest backend/tests -m "not integration"`. The repository's default pytest options do not exclude the integration marker, so a normal test run also collects these tests.
- API and mapping behavior: [backend/tests/api/v1/test_reconciliation_export.py](../../../backend/tests/api/v1/test_reconciliation_export.py), [test_reconciliation_specifications.py](../../../backend/tests/api/v1/test_reconciliation_specifications.py), and [test_mapping.py](../../../backend/tests/api/v1/test_mapping.py).
- Frontend reconciliation view: [ReconciliationView.test.ts](../../../frontend/src/components/reconciliation/__tests__/ReconciliationView.test.ts).

## Suggested Status Review Order

1. Read the [Materialized Entity Mapping Sync proposal](../../proposals/done/MATERIALIZED_ENTITY_MAPPING_SYNC/MATERIALIZED_ENTITY_MAPPING_SYNC.md) and PR #562 for the newest synchronization work.
2. Compare the [Persistence Consolidation proposal](../../proposals/done/RECONCILIATION_PERSISTENCE_CONSOLIDATION.md), its task plans, and issue #465 for the sidecar and export design.
3. Read the [future improvements placeholder](../../proposals/RECONCILIATION_FUTURE_IMPROVEMENTS.md) and open issue #617 for unscoped or newly requested work.
4. Trace the code paths above and use their focused tests to check the implementation claims.
