# Stage-Aware Column Suggestions Phase Plan

## Summary

This plan sequences the implementation described in [the proposal](STAGE_AWARE_COLUMN_SUGGESTIONS.md) and grounded by [the column-availability investigation](ENTITY_COLUMN_AVAILABILITY.md). It uses four phases: core resolution, backend exposure, entity-editor integration, and FK integration with legacy-path parity.

The resolver uses declarative source and loader metadata already available without execution. Candidate lists may be incomplete; they remain advisory, and every suggestion control remains free-text.

## Problem

The current backend and frontend derive suggestions from configured names without consistently accounting for the operation's pipeline stage or the unsaved editor draft. The existing FK introspection also assumes an older unnest configuration shape. A shared operation-aware resolver must become the source of suggestions without changing runtime processing or making suggestions a validation rule.

## Scope

This plan covers the core resolver, its draft-aware backend endpoint, and wiring all in-scope entity-editor controls to one debounced response. It includes operation-specific filter candidates while leaving filter fields as text inputs, and it includes replacing or delegating the legacy FK introspection behavior.

It does not change the normalization pipeline, execute loaders or queries to discover columns, change validation rules, or redesign `get_target_facing_columns()`.

## Current Position

- The backend `ColumnIntrospectionService` returns flat categories from the saved project and its unnest extraction does not reflect the current `id_vars` and `value_vars` configuration.
- The entity form builds several independent client-side candidate unions; the FK editor flattens the backend result into a separate list.
- The normalizer applies extraction and `extract` filters before linking, then evaluates deferred extra columns and `after_link` filters. Unnesting is followed by another link pass and `after_unnest` filters; delayed deduplication and `drop_empty_rows` follow. `system_id` assignment occurs later.
- The proposal settles the source-metadata question: use declarative metadata already available, allow it to be absent or incomplete, and never treat omission from suggestions as invalidity.

## Phase Plan

### Phase 1: Core Operation-Aware Resolver

**Goal**

Return operation-specific candidate sets from the current entity draft using known source and loader metadata and the real pipeline stage order.

**Focus**

- Model source/input fields and the relevant extraction, linking, filtering, unnest, cleanup, and identity stages in Python.
- Account for deferred extra columns, filter stages, deduplication timing, and FK order.
- Reflect current unnest outputs and suggest generated `system_id` only after identity assignment.
- When metadata is unavailable, return candidates derivable from known configuration without claiming the result is exhaustive.

**Depends On**

- None.

**Outputs**

- A core resolver contract with operation-specific results, including per-FK candidates and filter-stage candidates.
- Focused resolver tests and controlled comparisons with deterministic pipeline fixtures.

**Acceptance Criteria**

- `PH1-AC-1` (from `P-AC-1`, `P-AC-2`, `P-AC-3`) The resolver returns operation-specific candidates for the modeled stages and uses the current `id_vars`, `value_vars`, `var_name`, and `value_name` unnest shape.
- `PH1-AC-2` (from `P-AC-2`, `P-AC-5`) FK local candidates reflect the FK's link position, and generated `system_id` is excluded before identity assignment and included for processed parent output where applicable.

**Validation Milestones**

- `VM-1` Unit and deterministic fixture comparisons show that operation candidates follow the corresponding pipeline stages, including unnest timing and FK order; covers `PH1-AC-1` and `PH1-AC-2`.

**Task-Plan Handoff**

- Source criteria: `P-AC-1`, `P-AC-2`, `P-AC-3`, and `P-AC-5`.
- Fixed decisions: Python owns stage semantics; use only declarative metadata available without executing loaders or queries; incomplete metadata yields advisory, potentially incomplete candidates.
- Blocking questions: none identified.

**Readiness**

Ready for a task plan.

### Phase 2: Draft-Aware Backend Endpoint

**Goal**

Expose the resolver through one endpoint that evaluates the current unsaved entity draft and selected parent entities.

**Focus**

- Add the proposal's sibling `POST /projects/{project_name}/entities/{entity_name}/column-availability` endpoint without changing the existing GET contract.
- Return operation-specific candidate sets, including filter candidates and per-FK results.
- Resolve FK remote-key and extra-column source candidates from selected parent processed output.
- Keep the legacy service behavior behind the existing GET separate unless it is explicitly delegated as part of the implementation.

**Depends On**

- Phase 1 resolver contract and tests.

**Outputs**

- A draft-aware endpoint response consumable by the frontend composable.
- Backend tests for unsaved draft changes, selected parents, and the current unnest shape.

**Acceptance Criteria**

- `PH2-AC-1` (from `P-AC-4`) The endpoint uses the submitted unsaved draft; FK local candidates reflect link position, and remote-key and extra-column source candidates use the selected parent's processed output.
- `PH2-AC-2` (from `P-AC-3`, `P-AC-7`) The response includes operation-specific and filter-stage candidates and does not emit legacy unnest artifacts in place of current unnest results.

**Validation Milestones**

- `VM-2` Backend endpoint tests verify draft sensitivity, selected-parent results, operation-specific response fields, and current unnest configuration; covers `PH2-AC-1` and `PH2-AC-2`.

**Task-Plan Handoff**

- Source criteria: `P-AC-3`, `P-AC-4`, and `P-AC-7`.
- Fixed decisions: use a sibling POST endpoint; do not add a request body to the existing GET endpoint; parent-derived candidates use processed parent output.
- Blocking questions: none identified.

**Readiness**

Ready for a task plan after Phase 1 outputs are available.

### Phase 3: Shared Entity-Editor Suggestions

**Goal**

Replace the entity form's client-side unions with operation-specific results from one debounced request for the current draft.

**Focus**

- Add a shared composable for the draft-aware endpoint and reuse its response across controls.
- Wire entity columns, business keys, replacements, drop duplicates, drop empty rows, unnest variables, and extra-column source references to their operation-specific candidates.
- Keep candidates as suggestions only; preserve text entry for names not returned by the backend.
- Return filter candidates from the backend but leave filter fields as text inputs.

**Depends On**

- Phase 2 endpoint and response contract.

**Outputs**

- Entity-level controls using one shared, debounced candidate response rather than independent frontend availability unions.
- Frontend tests for request debouncing, control-to-operation mapping, and free-text entry.

**Acceptance Criteria**

- `PH3-AC-1` (from `P-AC-2`, `P-AC-7`) In-scope entity-level controls display the matching operation-specific candidates from one debounced request for the current draft and selected-parent state; the frontend does not infer availability from pipeline stages.
- `PH3-AC-2` (from `P-AC-6`, `P-AC-9`) A name absent from candidates remains enterable, and filter fields are not converted to comboboxes.

**Validation Milestones**

- `VM-3` Frontend tests verify a shared debounced request, correct candidate mapping for entity-level controls, free-text entry, and unchanged filter fields; covers `PH3-AC-1` and `PH3-AC-2`.

**Task-Plan Handoff**

- Source criteria: `P-AC-2`, `P-AC-6`, `P-AC-7`, and `P-AC-9`.
- Fixed decisions: frontend may sort or group response candidates but must not calculate availability; missing suggestions must not block entry or saving.
- Blocking questions: none identified.

**Readiness**

Ready for a task plan after Phase 2 outputs are available.

### Phase 4: FK Integration And Legacy Parity

**Goal**

Move FK selectors onto the shared response and eliminate divergent legacy candidate behavior.

**Focus**

- Wire FK local keys to candidates for that FK's link step.
- Wire FK remote keys and extra-column remote-source selectors to the selected parent's processed output.
- Remove or delegate the old config-only FK introspection calculation so it is no longer a separate source of availability rules.
- Update FK suggestion coverage for the current unnest shape and preserve free-text entry.

**Depends On**

- Phase 3 shared composable and Phase 2 per-FK endpoint results.

**Outputs**

- FK and extra-column remote-source selectors consuming the same operation-aware response as the rest of the editor.
- Parity coverage showing the old flattened suggestions are replaced without restricting valid manual entry.

**Acceptance Criteria**

- `PH4-AC-1` (from `P-AC-2`, `P-AC-4`, `P-AC-5`, `P-AC-8`) FK local selectors reflect FK order, while remote-key and extra-column remote-source selectors use selected-parent processed output, including `system_id` where available.
- `PH4-AC-2` (from `P-AC-3`, `P-AC-6`) The FK suggestion path uses the current unnest configuration shape, no longer relies on the legacy flattened calculation, and still permits fields absent from the candidate list.

**Validation Milestones**

- `VM-4` Frontend and backend regression tests show FK selectors consume the shared operation-specific results, current unnest candidates are used, and free-text values remain accepted; covers `PH4-AC-1` and `PH4-AC-2`.

**Task-Plan Handoff**

- Source criteria: `P-AC-2`, `P-AC-3`, `P-AC-4`, `P-AC-5`, `P-AC-6`, and `P-AC-8`.
- Fixed decisions: one shared request supplies controls; parent remote candidates come from processed output; suggestions remain advisory; replace or delegate the legacy service rather than maintain two availability rules.
- Blocking questions: none identified.

**Readiness**

Ready for a task plan after Phases 2 and 3 outputs are available.

## Cross-Phase Rules

- Keep stage and operation semantics in the Python resolver; do not reproduce them in TypeScript.
- Do not execute loaders or queries to discover columns while editing. Use known declarative metadata and return whatever candidates can be derived when metadata is incomplete.
- Keep every suggestion control free-text. Absence from the list is not a validation error; project validation and execution remain authoritative.
- Preserve runtime pipeline order and the three-tier identity rules. Treat `system_id` as generated output, not a pre-identity source field.
- Keep the current unnest shape authoritative and avoid reviving legacy `value_id` suggestions.

## Validation Strategy

- Validate resolver behavior with operation-level unit tests and controlled comparisons against deterministic pipeline fixtures.
- Validate the backend contract with unsaved drafts, selected parent entities, per-FK context, filter candidates, and current unnest fields.
- Validate the frontend with request debouncing, operation-to-control mapping, current draft updates, free-text entry, and unchanged filter text fields.
- Validate the final migration with regression coverage showing entity and FK suggestions come from the shared response and the legacy flattened computation no longer diverges.

## Final Recommendation

Deliver the shared resolver and endpoint before migrating editor controls. Integrate entity-level selectors first, then FK and extra-column selectors, and close with parity checks for the legacy path and advisory free-text behavior.
