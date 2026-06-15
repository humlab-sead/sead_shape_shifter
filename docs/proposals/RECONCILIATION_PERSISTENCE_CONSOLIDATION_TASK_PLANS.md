# Reconciliation Persistence Consolidation — Phase Task Plans

**Proposal**: [RECONCILIATION_PERSISTENCE_CONSOLIDATION.md](RECONCILIATION_PERSISTENCE_CONSOLIDATION.md)  
**Status**: Planning

---

## Phase 0: Mapping Sidecar Schema and Models

### Phase Summary

**Goal**: Define and validate the data model and file I/O layer for `<project>-mapping.yml` before any integration work begins.

**Acceptance Criteria**:

- [x] `MappingCatalog`, `EntityMapping`, `Link`, `Metadata`, `LinkSource`, and `EntityType` Pydantic models are implemented and importable.
- [x] `MappingManager` can load, create, update, and save a `<project>-mapping.yml` file for a given project.
- [x] Sidecar validation rejects entity mappings where `public_id` does not match the entity's configured `public_id`.
- [x] Sidecar validation rejects entity mappings where `local_key` is `system_id`, `public_id`, or any auto-generated column.
- [x] Compound local keys are encoded and decoded correctly using the pipe `|` separator.
- [x] All unit tests pass for schema load/save, validation, and encoding.

---

### Work Breakdown

#### Area 1: Pydantic Models (`src/reconciliation/mapping_model.py`)

**Objective**: Define the full schema as Pydantic v2 models.

- [x] Define `LinkSource` enum: `manual`, `reconciliation`, `import`.
- [x] Define `EntityType` enum: `primary`, `link_entity`, `derived`.
- [x] Define `Link` model with fields: `target_id`, `source`, `confidence`, `created_at`, `committed_at`, `notes`, `created_by`, `reviewed_by`.
- [x] Define `EntityMapping` model with fields: `local_key` (str or list[str]), `public_id`, `entity_type`, `description`, `links`.
- [x] Define `Metadata` model with fields: `created_at`, `updated_at`, `project`.
- [x] Define `MappingCatalog` model with fields: `version`, `metadata`, `entities`.
- [x] Implement `MappingCatalog.get_link()`, `set_link()`, `committed_links_by_entity()`, `draft_links_by_entity()`.
- [x] Implement compound key encoding: join ordered `local_key` values with `|`; handle `<NULL>` for null values; handle `\|` escape for embedded pipes.

**Completion condition**: Models are importable, all fields have correct types and defaults, compound key round-trip encoding is correct.

---

#### Area 2: `MappingManager` (CRUD + Sidecar I/O)

**Objective**: Implement a service class that owns all reads and writes for `<project>-mapping.yml`.

- [x] Implement `MappingManager.load(project_path)`: locate and parse `<project>-mapping.yml`; return empty `MappingCatalog` if file does not exist.
- [x] Implement `MappingManager.save(catalog, project_path)`: write `MappingCatalog` to `<project>-mapping.yml` atomically (write to temp, rename).
- [x] Implement `MappingManager.get_entity(catalog, entity_name)` → `EntityMapping | None`.
- [x] Implement `MappingManager.get_link(catalog, entity_name, local_key_value)` → `Link | None`.
- [x] Implement `MappingManager.set_link(catalog, entity_name, local_key_value, link)` → updates in-memory catalog.
- [x] Implement `MappingManager.delete_link(catalog, entity_name, local_key_value)`.
- [x] Implement `MappingManager.replace_entity_manual_links(catalog, entity_name, links)` → drops all `source="manual"` links for entity, inserts new ones.
- [x] Implement in-memory cache: catalog keyed by project path; invalidate on save.

**Completion condition**: `MappingManager` can be instantiated; load/save round-trip produces identical YAML; cache invalidation works correctly.

---

#### Area 3: Sidecar Validation

**Objective**: Ensure the sidecar file is internally consistent and aligned with the entity configuration before any links are applied.

- [x] Implement `validate_entity_mapping(entity_mapping, entity_config)`: raise `ValidationError` if `entity_mapping.public_id` differs from `entity_config.public_id`.
- [x] Implement `validate_local_key(entity_mapping, entity_config)`: raise `ValidationError` if `local_key` is `system_id`, `public_id`, or any derived/auto column; warn (log) if `local_key` is not in `entity_config.keys`.
- [x] Register validators in the project validation flow so they run at catalog load time.
- [x] Error messages must match the formats specified in REQ #3 and REQ #4.

**Completion condition**: Validation raises `ValidationError` with the correct message for each invalid configuration; valid configurations pass without error.

---

#### Area 4: Tests

**Objective**: Validate all schema, I/O, and validation behaviour before downstream integration.

- [x] Test `MappingCatalog` creation from a valid YAML fixture; check all fields parse correctly.
- [x] Test `MappingManager` load returns empty catalog when file is absent.
- [x] Test `MappingManager` load/save round-trip: write, reload, compare all fields.
- [x] Test compound key encoding for single key, multi-column key, key with pipe in value, key with null value.
- [x] Test `validate_entity_mapping` raises on `public_id` mismatch, passes on match.
- [x] Test `validate_local_key` raises for `system_id`, `public_id`, and derived columns; warns for key not in `entity_config.keys`.
- [x] Test `replace_entity_manual_links` drops all manual links for entity and inserts new ones; leaves reconciliation links unchanged.

**Completion condition**: All tests pass; coverage covers every validator branch.

---

### Progress Tracker

| Area                        | Status      | Notes |
|-----------------------------|-------------|-------|
| Pydantic models             | Done        |       |
| MappingManager (CRUD + I/O) | Done        |       |
| Sidecar validation          | Done        |       |
| Tests                       | Done        |       |

---

### Definition of Done

- [x] `src/reconciliation/mapping_model.py` contains all models and is importable.
- [x] `MappingManager` load/save round-trip produces byte-identical YAML for the same input.
- [x] Compound key encode/decode handles all edge cases: single, multi-column, null, embedded pipe.
- [x] All validation errors use the message formats from REQ #3 and REQ #4.
- [x] All unit tests pass with no skipped coverage gaps on model, I/O, and validation paths.
- [x] No `src` module imports anything from `backend.app`.

---

### Validation and Testing

- Run `uv run pytest tests/ -v -k mapping_model` (or equivalent) to verify schema and validation.
- Manually verify YAML output format against the reference schema in the proposal.
- Run `make lint` and `make tidy` before completing the phase.

---

### Deliverables

| Deliverable                           | Description                            | Status      |
|---------------------------------------|----------------------------------------|-------------|
| `src/reconciliation/mapping_model.py` | Pydantic models for sidecar schema     | Not started |
| `MappingManager` class                | CRUD and sidecar I/O                   | Not started |
| Sidecar validators                    | `public_id` and `local_key` validation | Not started |
| Unit tests                            | Schema, I/O, validation, encoding      | Not started |

---

### Scope

**In scope**: Pydantic models, file I/O, in-memory cache, compound key encoding, validation at load time.

**Out of scope**: API endpoints, normalization integration, materialized entity sync, frontend changes.

---

### Risks and Mitigations

| Risk                                                     | Mitigation                                                         |
|----------------------------------------------------------|--------------------------------------------------------------------|
| Compound key separator collides with business key values | Document escape rule (`\|`); add explicit test for this case.      |
| Schema design constrains later phases                    | Review the full schema against all three phases before finalising. |

---

## Phase 1: Replace `options.mapping` with Sidecar Storage

### Phase Summary

**Goal**: Wire the sidecar mapping catalog into the normalization pipeline and materialized entity save path, making it the authoritative source for `public_id` resolution.

**Acceptance Criteria**:

- [ ] Normalization reads committed links from `<project>-mapping.yml` and applies them to the `public_id` column before entity storage.
- [ ] `manual` links take precedence over `reconciliation` and `import` links during normalization.
- [ ] Saving a materialized entity replaces all `source="manual"` sidecar links for that entity with the current saved `public_id` values.
- [ ] `MappingService` API exposes list, get, put, and delete link endpoints for the sidecar.
- [ ] `PATCH /projects/{project}/mapping/from-materialized/{entity}` performs a full replace of manual links for the entity from the saved materialized state.
- [ ] `ProjectMapper` validates mapping configuration on project load and raises `ValidationError` on mismatch.
- [ ] Existing entity processing is not broken for entities with no sidecar file.
- [ ] All new and modified paths have tests.

---

### Work Breakdown

#### Area 1: Normalization Pipeline Integration

**Objective**: Read sidecar links during normalization and apply them to `public_id` columns according to the precedence rules in the proposal.

- [x] In `src/normalizer.py`, after project load, call `MappingManager.load(project_path)` and cache the catalog for the run.
- [x] For each entity with a sidecar `EntityMapping`, iterate rows and look up `local_key` value in `catalog.get_link(entity_name, local_key_value)`.
- [x] Apply precedence: use the first committed link found in order `manual` → `reconciliation` → `import`; skip links where `committed_at` is null.
- [x] If no sidecar link exists for a row, leave `public_id` unchanged (existing behavior).
- [x] Remove any reference to `options.mapping` / `LinkToRemoteService` from the normalization path.

**Completion condition**: A project with a valid `<project>-mapping.yml` resolves `public_id` values from sidecar links; a project without the file runs without error.

---

#### Area 2: `ProjectMapper` Validation

**Objective**: Validate sidecar alignment with entity configuration at project load time so errors fail fast.

- [x] In `backend/app/mappers/project_mapper.py`, after resolving entity configs, call `validate_entity_mapping` and `validate_local_key` for each entity that has a sidecar entry.
- [x] Raise `ValidationError` immediately if `public_id` or `local_key` is invalid; do not continue to normalization.
- [x] Ensure validation runs before any sidecar links are applied.

**Completion condition**: A project loaded with a mismatched `public_id` raises `ValidationError` with the correct message; a valid project loads without error.

---

#### Area 3: Materialized Entity Sync (Replace-on-Save)

**Objective**: When a materialized entity is saved, replace all `source="manual"` sidecar links for that entity with the current `public_id` values from the saved rows.

- [x] In `backend/app/services/materialization_service.py`, extend `save_materialized_entity()` to extract all rows where `public_id` is not null.
- [x] For each extracted row, build a `Link` with `source="manual"`, `committed_at=now()`, `created_by` from request context, and `target_id` from the `public_id` value.
- [x] Call `MappingManager.replace_entity_manual_links(catalog, entity_name, extracted_links)`.
- [x] Call `MappingManager.save(catalog, project_path)` to persist.
- [x] Implement `PATCH /projects/{project}/mapping/from-materialized/{entity}` endpoint in `backend/app/api/v1/endpoints/` that triggers the same extraction and replacement.
- [x] Register the endpoint in `backend/app/api/v1/api.py`.

**Completion condition**: After saving a materialized entity, `<project>-mapping.yml` contains exactly the manual links extracted from the saved rows; existing reconciliation/import links for that entity are unchanged.

---

#### Area 4: `MappingService` API Endpoints

**Objective**: Expose sidecar CRUD operations over the REST API.

- [x] Implement `GET /projects/{project}/mapping/{entity}` — returns all links and entity metadata for the entity.
- [x] Implement `GET /projects/{project}/mapping/{entity}/{local_key_value}` — returns a single link.
- [x] Implement `PUT /projects/{project}/mapping/{entity}/{local_key_value}` — creates or updates a single link; sets `source="manual"`, `committed_at=now()`.
- [x] Implement `DELETE /projects/{project}/mapping/{entity}/{local_key_value}` — removes a single link.
- [x] Add Pydantic API request/response models in `backend/app/models/`.
- [x] Register all endpoints in `backend/app/api/v1/api.py`.

**Completion condition**: Each endpoint returns the correct HTTP status and body for valid and invalid inputs; integration tests cover at least the happy path for each endpoint.

---

#### Area 5: Tests

- [x] Test normalization with a sidecar file: verify `public_id` column is populated from sidecar links.
- [x] Test normalization without a sidecar file: verify existing entity behavior is unchanged.
- [x] Test precedence: `manual` link overrides `reconciliation` link for same `local_key_value`.
- [x] Test that draft links (`committed_at=null`) are not applied during normalization.
- [x] Test `save_materialized_entity` replace-on-save: after save, manual links match saved rows; reconciliation links are preserved.
- [x] Test each API endpoint: list, get, put, delete — happy path and missing-entity error cases.
- [x] Test `ProjectMapper` validation raises on invalid sidecar configuration.

**Completion condition**: All tests pass; no regression in existing normalization tests.

---

### Progress Tracker

| Area                                       | Status      | Notes |
|--------------------------------------------|-------------|-------|
| Normalization pipeline integration         | Done        |       |
| ProjectMapper validation                   | Done        |       |
| Materialized entity sync (replace-on-save) | Done        |       |
| MappingService API endpoints               | Done        |       |
| Tests                                      | Done        |       |

---

### Definition of Done

- [x] Normalization applies sidecar `public_id` links in the correct precedence order.
- [x] Saving a materialized entity updates `<project>-mapping.yml` with current manual links.
- [x] `PATCH /projects/{project}/mapping/from-materialized/{entity}` performs full manual-link replacement.
- [x] All four CRUD endpoints respond correctly to valid and invalid requests.
- [x] `ProjectMapper` raises `ValidationError` on invalid sidecar configuration at load time.
- [x] All existing normalization tests pass unchanged.
- [x] All new tests pass.
- [x] No `backend.app` imports in `src/`.
- [x] `make lint` and `make tidy` pass.

---

### Validation and Testing

- Run `uv run pytest tests/ -v` to check core normalization tests.
- Run `uv run pytest backend/tests/ -v` to check API endpoint and service tests.
- Manually test save of a materialized entity and inspect the resulting `<project>-mapping.yml`.
- Verify a project with no sidecar file runs without error end-to-end.

---

### Deliverables

| Deliverable                        | Description                                               | Status      |
|------------------------------------|-----------------------------------------------------------|-------------|
| Normalization sidecar integration  | `src/normalizer.py` reads and applies sidecar links       | Not started |
| `ProjectMapper` validation         | Validate sidecar against entity config on load            | Not started |
| `MaterializationService` extension | Replace-on-save logic in `save_materialized_entity()`     | Not started |
| `PATCH from-materialized` endpoint | API endpoint for explicit manual-link replacement         | Not started |
| `MappingService` CRUD endpoints    | List, get, put, delete link endpoints                     | Not started |
| API models                         | Request/response Pydantic models in `backend/app/models/` | Not started |
| Tests                              | Normalization, replace-on-save, CRUD endpoint tests       | Not started |

---

### Scope

**In scope**: Normalization sidecar lookup, replace-on-save from materialized entity, CRUD API endpoints, `ProjectMapper` validation.

**Out of scope**: Reconciliation export to sidecar (Phase 2), frontend mapping UI beyond materialized entity save, advanced lifecycle states.

---

### Risks and Mitigations

| Risk                                                                                                   | Mitigation                                                                           |
|--------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------|
| Normalization pipeline change breaks existing entity processing                                        | Run full normalization test suite before and after; gate on no regression.           |
| Replace-on-save removes manual links the user intended to keep but did not include in the current save | Document behavior clearly; surface a confirmation prompt in the UI in a later phase. |

---

### Open Questions

- Should `MappingManager.load` be called once per normalization run and cached, or once per entity? Decide before implementing the normalization integration to avoid repeated disk reads.

---

## Phase 2: Export Reconciliation Links to Sidecar

### Phase Summary

**Goal**: Allow users to explicitly copy accepted reconciliation links from the reconciliation catalog into the mapping sidecar, making them available to the normalization pipeline.

**Acceptance Criteria**:

- [ ] A new API endpoint copies reconciliation links for an entity/field from the reconciliation catalog into `<project>-mapping.yml` with `source="reconciliation"` and `committed_at` set.
- [ ] Export does not overwrite existing `source="manual"` links in the sidecar.
- [ ] The reconciliation UI exposes an "Export to Mapping" action that calls the endpoint.
- [ ] After export, normalization applies the exported links during the next run.
- [ ] Tests cover export flow, provenance, and no-overwrite behaviour.

---

### Work Breakdown

#### Area 1: Export Endpoint

**Objective**: Implement the backend endpoint that copies reconciliation catalog links to the sidecar.

- [x] Add endpoint `POST /projects/{project}/reconciliation/{entity}/{field}/export-to-mapping` in `backend/app/api/v1/endpoints/`.
- [x] Endpoint reads links from the reconciliation catalog via `EntityMappingManager.load_catalog()` for the specified entity/field.
- [x] For each link in the catalog, build a sidecar `Link` with `source="reconciliation"`, `confidence` from catalog, `committed_at=now()`, `created_by="reconciliation-service"`.
- [x] Before writing, check if an existing sidecar link with `source="manual"` exists for the same `local_key_value`; if so, skip that entry (manual wins).
- [x] Write all non-skipped links into `MappingCatalog` for the entity using `MappingManager.set_link()`.
- [x] Call `MappingManager.save()` to persist to `<project>-mapping.yml`.
- [x] Return a response body: `{ exported: N, skipped_manual: M, entity: "...", field: "..." }`.
- [x] Register the endpoint in `backend/app/api/v1/api.py`.

**Completion condition**: Calling the endpoint populates the sidecar with reconciliation links; manual links for the same keys are not overwritten; the response body counts are correct.

---

#### Area 2: Reconciliation UI — Export Action

**Objective**: Surface the "Export to Mapping" action in the reconciliation panel so users can trigger export without using the API directly.

- [x] Add an "Export to Mapping" button in the reconciliation results panel for each entity/field that has a reconciliation catalog.
- [x] On click, call the export endpoint and display a confirmation message with the count of exported and skipped links.
- [x] Disable the button while export is in progress.
- [x] Show an error message if the endpoint returns a non-2xx response.

**Completion condition**: The button is visible in the reconciliation UI; clicking it calls the correct endpoint; the user sees a confirmation with counts.

---

#### Area 3: Tests

- [ ] Test export endpoint happy path: links are written to sidecar with correct provenance.
- [ ] Test that existing `source="manual"` links are not overwritten by export.
- [ ] Test export for an entity with no reconciliation catalog: endpoint returns an appropriate error or empty result.
- [ ] Test that after export, normalization applies the exported links correctly.
- [ ] Test UI: "Export to Mapping" button is present; confirmation message is shown after success.

**Completion condition**: All tests pass; no overwrite of manual links in any scenario.

---

### Progress Tracker

| Area                            | Status      | Notes |
|---------------------------------|-------------|-------|
| Export endpoint                 | Not started |       |
| Reconciliation UI export action | Not started |       |
| Tests                           | Not started |       |

---

### Definition of Done

- [ ] `POST /projects/{project}/reconciliation/{entity}/{field}/export-to-mapping` endpoint is implemented, registered, and returns correct response body.
- [ ] Manual links in sidecar are never overwritten by export.
- [ ] Exported links have `source="reconciliation"` and a non-null `committed_at`.
- [ ] "Export to Mapping" button is present and functional in the reconciliation UI.
- [ ] After export, normalization applies the exported links during the next run.
- [ ] All tests pass.
- [ ] `make lint` and `make tidy` pass.

---

### Validation and Testing

- Run `uv run pytest backend/tests/ -v` to check export endpoint and no-overwrite behaviour.
- Run `uv run pytest tests/ -v` to verify normalization picks up exported links.
- Manually perform an end-to-end run: reconcile an entity, export links, run normalization, verify `public_id` values are populated.

---

### Deliverables

| Deliverable      | Description                                                       | Status      |
|------------------|-------------------------------------------------------------------|-------------|
| Export endpoint  | `POST .../export-to-mapping` backend endpoint                     | Not started |
| Export UI action | "Export to Mapping" button in reconciliation panel                | Not started |
| Tests            | Export flow, provenance, no-overwrite, normalization verification | Not started |

---

### Scope

**In scope**: Export from reconciliation catalog to sidecar, no-overwrite rule for manual links, UI trigger.

**Out of scope**: Draft/committed lifecycle states, review UI, audit logging, rollback — all deferred to [RECONCILIATION_FUTURE_IMPROVEMENTS.md](RECONCILIATION_FUTURE_IMPROVEMENTS.md).

---

### Risks and Mitigations

| Risk                                                                                  | Mitigation                                                                         |
|---------------------------------------------------------------------------------------|------------------------------------------------------------------------------------|
| Reconciliation catalog link format differs from sidecar `Link` field names            | Map fields explicitly in the export endpoint; add a mapping unit test.             |
| Precedence logic in sidecar is applied only at normalization time, not at export time | Document this clearly; the export endpoint does not need to re-resolve precedence. |
