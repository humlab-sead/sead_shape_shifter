# Stage-Aware Column Suggestions For The Entity Editor

## Status

- **Implemented** (branch `stage-aware-column-suggestions`); closes issue [#527](https://github.com/humlab-sead/sead_shape_shifter/issues/527) and fixes issue [#511](https://github.com/humlab-sead/sead_shape_shifter/issues/511)
- Scope: entity-editor column suggestions across the backend introspection service and the frontend entity editor
- Goal: make each editor combobox suggest columns known to be available at that control's pipeline stage

## Summary

Recommend one shared, operation-aware column-availability resolver in the core. It models pipeline stages internally and returns candidate columns for each editor operation through the backend. The frontend uses one response for the current draft instead of maintaining per-control unions. This replaces the backend's config-only FK introspection service and fixes issue [#511](https://github.com/humlab-sead/sead_shape_shifter/issues/511), whose investigation is recorded in [ENTITY_COLUMN_AVAILABILITY.md](ENTITY_COLUMN_AVAILABILITY.md).

## Problem

The entity editor's comboboxes suggest columns that are not actually available at the control's processing stage, or omit columns that are. A user sees a name they cannot use, or must type a valid name by hand because the suggestion is stale or incomplete.

The defect is not a hard block — the controls are free-text — but it misleads users about what a given operation can consume. The investigation shows the bug is present in both suggestion sources:

- the backend `ColumnIntrospectionService` returns configured names without resolving loader output, transformation timing, or the unsaved editor draft; and
- the frontend derives suggestions from several independent static unions of configured fields, none of which track pipeline stage.

The same column can be "configured somewhere" and still not be available at the stage a specific control runs.

## Scope

- One operation-aware resolver for an entity draft plus its source/loader metadata. It uses an explicit internal stage model, including source/input fields, but returns candidates by operation rather than exposing stages as the frontend contract.
- Backend exposure of the resolver through a draft-aware endpoint. The request includes the current unsaved entity draft; foreign-key suggestions account for the selected parent entity and each FK's position and configuration.
- Frontend wiring so the controls consume operation-specific candidates from one shared response:
  - Entity `Columns`, `Business Keys`, `Replacements`, `Drop Duplicates`, `Drop Empty Rows`
  - FK `Local Keys`, `Remote Keys`, and extra-column remote-source selectors
  - Unnest `ID Variables` and `Value Variables`
  - Extra-column source references
- Filter-column candidates in the resolver response, without converting filter text fields to comboboxes in this change.

## Non-Goals

- Making a suggestion a runtime guarantee. Source files and queries can still drift; validation/execution remains the availability authority.
- Changing the normalization pipeline order or the runtime call sequence.
- Changing validation rules or target-model conformance.
- Executing loaders or queries during editing just to enumerate columns.
- Redesigning `get_target_facing_columns()`, which describes the entity's final output and has no stage parameter.

## Current Behavior

Three independent sources feed suggestions today:

1. `ColumnIntrospectionService.get_available_columns()` (backend) returns flat categories (`explicit`, `keys`, `extra`, `unnested`, `foreign_key`, `system`, `directives`) read only from the saved project. Its unnest extraction still assumes the legacy `value_column` shape and emits `value_id`/`value_name`, not the current `id_vars`/`value_vars`/`var_name`/`value_name` shape.
2. `EntityFormDialog.vue` derives several client-side unions (`availableColumns`, `availableColumnsForUnnest`, `availableColumnsForReplacements`, `extraColumnsAvailableColumns`, `mergedAvailableColumns`) by combining configured names. None distinguishes extraction, pre-unnest, post-link, or post-unnest availability.
3. `ForeignKeyEditor.vue` calls the backend service and flattens the result into a single list, so FK local suggestions reflect only the saved project, not unsaved edits.

## Proposed Design

### Core resolver

Add an operation-aware column resolver in `src/`. Given an entity configuration draft and any source/loader metadata already available without execution, it models known source fields and the stages in the normalization sequence documented in the investigation (subset → early extras → replace → entity dedupe → FK link → deferred extras → filters → unnest → delayed dedupe → drop-empty → identity columns). The stage model stays in Python; the resolver returns candidate sets keyed by editor operation.

Use declarative metadata available from the draft, source configuration, or loader schemas; do not inspect sources dynamically or execute loaders or queries to build suggestions. Sources and loaders do not have to provide complete column metadata. When source fields cannot be determined, return the candidates derivable from known configuration and mark no field as invalid merely because it is absent from the suggestions. Candidate lists are advisory and may be incomplete.

Operation context must account for settings that change when a control runs, including deduplication before or after unnest, filter stages, deferred extra columns, and FK link order. Local-key candidates for an FK reflect the columns available at that FK's link step, including output from earlier FKs where applicable. Remote-key and FK extra-column source candidates come from the selected parent entity's processed output.

The public response contains operation-specific results rather than a stage-to-columns map. For example, it can provide separate candidates for `columns`, `business_keys`, `replacements`, `drop_duplicates`, `drop_empty_rows`, unnest `id_vars` and `value_vars`, per-FK `local_keys`, `remote_keys`, and extra-column sources, plus filter-column candidates for each configured filter stage.

Automatically generated `system_id` is suggested only where it is available after identity assignment, including as an FK remote match key for processed parent entities. It is not suggested to operations that run before identity assignment.

### Backend behavior

Add a sibling endpoint, `POST /projects/{project_name}/entities/{entity_name}/column-availability`, that accepts the current entity draft and returns the operation-specific candidate sets. Do not put a request body on the existing GET endpoint. The resolver uses the selected parent entities for FK remote-key and extra-column source suggestions. `ColumnIntrospectionService` either delegates to the resolver or is replaced by it.

### Frontend behavior

Replace the ad-hoc unions in `EntityFormDialog.vue` and the flattened FK suggestions with a shared composable (for example `useColumnAvailability`). It makes one debounced request for each current draft and selected-parent state; all controls consume the corresponding operation-specific results. The frontend may sort or group results but does not compute column availability. Existing suggestion controls remain free-text: a field absent from the candidate list can still be entered and saved. Filter candidates are returned by the backend, but filter fields remain unchanged in this proposal.

### Guardrail

Suggestions stay advisory and may be incomplete when source metadata is unavailable. The editor does not reject a field because it is absent from the candidate list. Real availability continues to be checked during project validation and execution, so a drifted source is still caught there.

## Alternatives Considered

- **Per-control stage logic in the frontend (TypeScript).** Rejected: it duplicates the pipeline's stage knowledge in a second language and will drift from the Python engine.
- **Extend the existing backend service with stage categories while keeping the frontend unions.** Rejected: two sources of truth remain, and the backend still cannot honor the unsaved draft without new input plumbing.
- **Compute all suggestions server-side only at save time.** Rejected: suggestions must reflect the live unsaved draft to be useful while editing.

## Risks And Tradeoffs

- **Backend round-trip cost.** The shared composable sends one debounced request per draft and selected-parent state, rather than one request per control. Cache results by that effective request state where useful.
- **Resolver/pipeline drift.** The resolver models the normalization order. Mitigate with operation-level tests and controlled fixture comparisons against the real pipeline.
- **Migration of the existing FK editor and its tests** from the legacy unnest shape to the current shape.

## Testing And Validation

- Unit tests for operation-specific candidates across source/input fields, unnest, filters, deferred extra columns, deduplication timing, and FK order.
- Controlled fixture tests that compare resolver candidates with columns available at the corresponding pipeline operations when source metadata and inputs are deterministic. Do not require exact equality as a general contract for sources that can drift at runtime.
- Backend endpoint tests for unsaved drafts, selected parents, operation-specific results, and the current `id_vars`/`value_vars`/`var_name`/`value_name` unnest shape.
- Frontend tests that the composable sends one debounced request per draft state, controls consume their operation-specific suggestions, and existing suggestion controls still accept free text.

## Acceptance Criteria

- `P-AC-1` One Python resolver models source/input fields and the relevant pipeline stages internally, and returns operation-specific candidate sets to callers.
- `P-AC-2` Each in-scope control receives candidates for its operation and configuration context, including FK order and configured filter or extra-column stage; the frontend does not infer availability from pipeline stages.
- `P-AC-3` Unnest suggestions reflect the current `id_vars`/`value_vars`/`var_name`/`value_name` shape, with no legacy `value_id`/`value_name` artifacts.
- `P-AC-4` The draft-aware POST endpoint uses the current unsaved entity draft; FK remote-key and extra-column source candidates use the selected parent's processed output, while local-key candidates reflect the FK's link step.
- `P-AC-5` Automatically generated `system_id` is excluded from operations before identity assignment and is available as an FK remote match key for processed parent entities.
- `P-AC-6` All existing suggestion controls remain free-text; a field absent from an incomplete candidate list remains enterable, and project validation or execution remains the authority for actual runtime availability.
- `P-AC-7` The backend returns operation-specific candidates, including filter-column candidates, and one debounced frontend request supplies the controls for the current draft and selected-parent state.
- `P-AC-8` The FK extra-column remote-source selector uses candidates from the selected parent's processed output.
- `P-AC-9` Filter fields are not converted to comboboxes as part of this change.

## Planning Handoff

Confirmed decisions and constraints for a phase plan:

- The resolver in `src/` is the single source of truth for operation and stage semantics; do not mirror availability rules in TypeScript.
- The resolver takes the current entity draft plus source/loader metadata; FK local suggestions honor unsaved edits and FK order.
- Use one debounced backend request per current draft and selected-parent state, not one request per control.
- Preserve the three-tier identity rules. Suggest generated `system_id` only to operations that run after identity assignment, including FK remote matching.
- Use only declarative source/loader metadata already available without execution; metadata may be incomplete or unavailable, and candidate lists remain advisory rather than exhaustive.
- Keep all suggestion controls free-text. A field absent from the candidate list remains enterable; validation and execution stay the availability authority.
- Expected validation outcomes: operation-specific unit coverage and controlled fixture comparisons with the real pipeline.

## Final Recommendation

Build one operation-aware column resolver in the core, expose it through a draft-aware POST endpoint, and route the in-scope entity-editor controls through one shared debounced request. Keep pipeline semantics in Python, existing suggestion controls free-text, and validation/execution as the authority for runtime availability.
