# Declarative Business Keys Phase Plan

## Summary

This plan sequences the implementation described in [the proposal](DECLARATIVE_BUSINESS_KEYS.md). It uses four phases: remove key-driven output selection in Core and add key validation, make one backend fixed schema authoritative for persistence and value conversion, adopt that schema in the frontend, and run regression and integration checks. Retiring the legacy values-order input is deferred to issue #539 because it is cleanup, not a delivery dependency.

The ordering follows the proposal's recommended delivery order. The validation-error content and the compatibility rule are cross-phase rules rather than a delivery step. The rollout period that once gated retiring legacy input support is resolved: the frontend bundled with the backend is the only client that sends fixed-values requests, and it already sends the authoritative order. Retirement is therefore a code-removal cleanup tracked as issue #539, not a delivery phase or a coordinated client transition. Everything else is settled by the proposal.

## Problem

`keys` currently both describes business-key behavior and contributes output columns. That dual role produces inconsistent schemas across Core extraction, SQL ordering, fixed-schema derivation, materialization, and the entity editor. The change must land as a coordinated update across Core, backend, frontend, and saved project data. The only client that sends fixed-values requests is the frontend bundled with the backend, so the transition is limited to that client rather than to independent external clients.

## Scope

This plan covers the Core output-selection and key-validation change, fixed and materialized schema derivation, backend persistence and value conversion, frontend adoption of backend fixed-schema metadata, and the regression and integration checks that gate the change.

It does not change the three-tier identity model, `system_id` or `public_id` meaning, foreign-key join behavior, or business-key checks. It does not add an automatic project or values migration tool and does not restate the proposal's rationale.

## Current Position

- `TableConfig` in `src/model.py` exposes `keys_and_columns`, `get_columns(include_keys=...)`, and `values_column_order`. These place keys before data columns and are the current source of extracted and fixed row order.
- `build_fixed_entity_full_columns` in `src/types/fixed_entity_types.py` inserts keys before data columns. The backend `derive_fixed_schema` and `build_fixed_full_columns` in `backend/app/utils/fixed_schema.py` derive `fixed_schema` from both keys and columns.
- `FixedEntityPersistenceStrategy.normalize_materialized_dataframe` adds a null-valued column for any key absent from materialized data.
- The keys-subset check in `EntityFieldsBaseSpecification` is present but commented out, so keys are not currently validated against produced fields.
- `resolve_column_availability` seeds source candidates from configured keys and `values_column_order`, so a configured key can be suggested without a producer.
- The frontend computes fixed grid order locally from columns, keys, and `public_id`, and its key watcher appends missing keys into the columns list. `fixed_schema` is already typed on entity responses and is additive.
- `EntityValuesService._normalize_fixed_request_columns` recognizes the historical identity/keys/data request order through `build_legacy_fixed_full_columns` and remaps those rows by name before saving. `_normalize_fixed_stored_values` separately reorders any stored column permutation with the same name set when reading, without writing the file.
- Structural and data validation reject business keys that are not produced: keys outside a fixed entity's `full_columns`, duplicate fixed columns, and unproduced keys reported by data validation.
- Proposal decision: `fixed_schema` API work is complete; frontend adoption remains open. Validation must never write project or values files.

## Phase Plan

### Phase 1: Core Output Selection And Key Validation

**Goal**

Make entity output columns come from producers, and make keys references to produced fields rather than sources of columns.

**Focus**

- Remove key-driven column selection and ordering from `keys_and_columns`, `get_columns()`, `values_column_order`, SQL loader column ordering, and subset extraction.
- Re-enable and extend key validation so each key must refer to a field produced by the entity and available at the operation that uses it.
- Apply structural validation when fields are known and runtime validation when a loader discovers fields, using the error content in the cross-phase rules.
- Source business-key suggestions from known source and produced fields instead of configured keys, keeping suggestions advisory and free-text.

**Depends On**

- None. The proposal records the error-content and compatibility decisions as cross-phase rules.

**Outputs**

- Extraction and ordering behavior driven by configured, detected, or explicitly configured producers.
- Structural and runtime key validation with actionable errors, plus corrected suggestion sources.

**Acceptance Criteria**

- `PH1-AC-1` (from `P-AC-1`) Keys do not select, create, or reorder extracted output columns; output order follows configured, detected, or explicitly configured producers.
- `PH1-AC-2` (from `P-AC-2`) A key that is not produced fails structural validation when fields are known and fails runtime validation when fields are discovered by a loader.
- `PH1-AC-3` (from `P-AC-6`) Business-key suggestions derive from known produced fields, and incomplete suggestions remain advisory with free-text entry available.

**Validation Milestones**

- `VM-1` Core tests show keys do not add extracted or reorder configured output for auto-detected sources, explicit columns, and generated columns; missing keys fail with the cross-phase error detail; suggestions come from produced fields. Covers `PH1-AC-1`, `PH1-AC-2`, and `PH1-AC-3`.

**Task-Plan Handoff**

- Source criteria: `P-AC-1`, `P-AC-2`, and `P-AC-6`.
- Fixed decisions: keys never create output columns; suggestion lists stay advisory and free-text; structural checks must not claim a dynamic field is missing before the loader runs.
- Blocking questions: none identified.

**Readiness**

Ready for a task plan.

### Phase 2: Fixed Schema, Persistence, And Value Conversion

**Goal**

Make one backend schema, managed identity fields plus produced data columns, authoritative for fixed and materialized rows and for incoming values requests.

**Focus**

- Stop fixed-schema derivation and `build_fixed_entity_full_columns` from adding key positions; set `entity_data.columns` to produced data fields without identity fields and expose `key_columns` as business-role metadata.
- Stop materialization from inventing null-valued key columns and fail missing keys with the expected positional column order.
- Use the single schema for row-width checks, column types, values updates, materialized data, and GET/PUT normalization.
- Accept the new values order, remap the recognized legacy order by column name, and reject duplicate names, unknown orders, and ambiguous widths.

**Depends On**

- Phase 1 Core output-selection rule.

**Outputs**

- `fixed_schema` derived from identity plus produced data columns only.
- Persistence, materialization, and values-update behavior aligned to that schema, including the legacy remap path.

**Acceptance Criteria**

- `PH2-AC-1` (from `P-AC-3`) Fixed and materialized rows use one backend schema of managed identity fields followed by produced data columns; keys add no positions and no null placeholders.
- `PH2-AC-2` (from `P-AC-4`) Missing-key errors for fixed or materialized data include the expected positional column order and do not modify project or values files.
- `PH2-AC-3` (from `P-AC-4`) Values requests accept the new order, remap only the recognized legacy order by column name, and reject duplicate, unknown, or ambiguous payloads.

**Validation Milestones**

- `VM-2` Fixed-entity, materialization, and backend GET/PUT tests confirm one-schema ordering, absent-key failure instead of null columns, actionable positional errors, and accepted or rejected values orders. Covers `PH2-AC-1`, `PH2-AC-2`, and `PH2-AC-3`.

**Task-Plan Handoff**

- Source criteria: `P-AC-3` and `P-AC-4`.
- Fixed decisions: `fixed_schema` stays additive; identity columns lead the full order; the recognized legacy order is per the cross-phase compatibility rule; materialization must not pad keys.
- Blocking questions: none identified.

**Readiness**

Ready for a task plan after Phase 1.

### Phase 3: Frontend Adoption

**Goal**

Use backend `fixed_schema` metadata for fixed row order and key editing, and stop reconstructing order from keys.

**Focus**

- Hydrate the editor from all `fixed_schema` fields and drive fixed grid and save order from `full_columns`.
- Remove local key-based order reconstruction and the behavior that appends missing keys into the columns list.
- Keep save round-trips consistent with the authoritative order, and handle responses without `fixed_schema` during the transition.

**Depends On**

- Phase 2 `fixed_schema` metadata.

**Outputs**

- An entity editor whose fixed order and key editing come from backend metadata.
- Frontend coverage for hydration, grid order, keys that are also produced columns, save round-trips, and the transition fallback.

**Acceptance Criteria**

- `PH3-AC-1` (from `P-AC-5`) The frontend uses backend fixed-schema metadata for row order and does not rebuild positional order from keys when metadata is present.

**Validation Milestones**

- `VM-3` Frontend tests confirm hydration from `fixed_schema`, grid order from `full_columns`, keys that are also produced columns, save round-trips, and the response-without-metadata fallback. Covers `PH3-AC-1`.

**Task-Plan Handoff**

- Source criteria: `P-AC-5`.
- Fixed decisions: backend metadata is authoritative for order when present; key-based reconstruction is removed rather than kept as a second rule.
- Blocking questions: the exact fallback when `fixed_schema` is absent is settled by the cross-phase compatibility rule.

**Readiness**

Ready for a task plan after Phase 2.

### Phase 4: Regression And Integration Validation

**Goal**

Prove the coordinated change end-to-end across Core, backend, fixed values, materialization, and the editor before retiring legacy input.

**Focus**

- Regression coverage for extraction, validation errors, fixed values, materialization, API values updates, and frontend save round-trips.
- Integration coverage for an existing fixed entity with a missing key, materialized values through open, edit, and save, and a source-backed entity whose key is missing from the loader result.
- Confirm validation reports actionable errors and never rewrites project or values files.

**Depends On**

- Phases 1, 2, and 3 outputs.

**Outputs**

- A passing regression and integration suite covering the changed behavior.
- Evidence that validation does not mutate project or values files.

**Acceptance Criteria**

- `PH4-AC-1` (from `P-AC-7`) Regression tests cover extraction, validation errors, fixed values, materialization, API updates, and frontend save round-trips, including that validation does not modify project or values files.

**Validation Milestones**

- `VM-4` The full regression and integration run confirms the covered behavior and the no-file-write guarantee. Covers `PH4-AC-1`.

**Task-Plan Handoff**

- Source criteria: `P-AC-7`.
- Fixed decisions: legacy input support stays in place through this phase; failures are reported rather than auto-corrected.
- Blocking questions: none identified for the validation work itself.

**Readiness**

Ready for a task plan after Phases 1 through 3.

### Deferred: Legacy Values-Order Retirement

Retiring the legacy fixed-values request-order recognition is tracked as issue #539. It is not a delivery phase and does not block deploying the change:

- The remaining code only accepts *additional* input shapes on top of the authoritative order, so it is backward-compatible and blocks nothing.
- No independent values-request client exists, so there is no rollout to coordinate.
- Removal is a code change, not a data migration: no project or values files are rewritten, and the read-side stored-order normalization in `_normalize_fixed_stored_values` must stay so existing sidecar files remain readable.

The work itself is: drop the `build_legacy_fixed_full_columns` recognition from `_normalize_fixed_request_columns`, remove `build_fixed_entity_legacy_columns` and its wrapper once they have no callers, and replace the tests that assert legacy-order acceptance with tests that assert the same request fails with an error naming the authoritative order.

## Cross-Phase Rules

- Preserve business-key checks, foreign-key identity rules, and the three-tier identity model throughout.
- Use `fixed_schema.full_columns` as the single positional order for fixed rows and external values; do not derive order from keys or suggestions.
- Never infer that a field exists because it appears in `keys` or a suggestion list.
- Validation and reads never write project or values files; existing projects receive the same strict validation as new projects.
- Keep structural checks conservative for loader-discovered fields; the runtime check remains authoritative.
- Keep suggestion lists advisory and keep free-text entry available in every phase.
- Validation errors must name the entity, the missing key, why it is not produced, and, where fixed or materialized values are affected, the expected positional column order.
- Accept and remap only an exact, unambiguous legacy fixed-values order; reject duplicate names, unknown orders, and row widths matching neither accepted layout, and never guess an unsafe mapping. Removing this acceptance is deferred to issue #539.

## Validation Strategy

- Unit tests for the Core output-selection rule, key validation, and suggestion sources.
- Fixed-entity and materialization tests for one-schema ordering, absent-key failure, and positional error detail.
- Backend tests for `fixed_schema` derivation, GET and PUT normalization, exact new order, recognized legacy remap, and rejection of ambiguous payloads.
- Frontend tests for hydration from `fixed_schema`, grid order, keys that are also produced columns, save round-trips, and the no-metadata fallback.
- Integration tests for an existing fixed entity with a missing key, materialized values through open, edit, and save, and a source-backed entity with a loader-discovered missing key.
- A survey of existing project files confirming that none configures a business key that is not produced, supporting the strict-validation cutover.
- A grouped regression at Phase 4; post-retirement regression belongs to issue #539.

Exact commands, test files, fixtures, and assertions belong in the phase task plans.

## Final Recommendation

Sequence the work in the proposal's order. Land the Core rule first, then the fixed-schema and persistence change, then frontend adoption. Apply the error-content and compatibility rules from the start. Run the grouped regression and integration checks before release. Retiring the legacy request-order path is deferred to issue #539, because the remaining acceptance code is backward-compatible cleanup and does not block deploying the change.
