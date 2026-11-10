# Direct Target-ID Foreign Key UX Phase Plan

Source proposal: [DIRECT_TARGET_ID_FOREIGN_KEY_UX.md](./DIRECT_TARGET_ID_FOREIGN_KEY_UX.md)

## Summary

Sequence the entity-editor support for direct target IDs into five phases. The backend contract lands first so the dialog has a resolved relationship source. Map preservation lands before the selector so a visual control cannot drop existing declarations. The selector follows, then the actionable missing-column path, then regression verification of preserved behavior.

Each phase produces a result the next phase consumes and stays inside the proposal's non-goals.

## Problem

`foreign_key_value_sources` can be written in project YAML, but the entity dialog has no control for it and rebuilds entity configuration from explicit field lists. Adding a selector without round-trip support would silently drop existing entries. The selector also needs direct-FK metadata that the existing missing-entity picker does not provide.

## Scope

This plan covers the read-only metadata contract, dialog round-trip preservation, the **Direct target IDs** selector, the validation affordance for a missing output column, and regression verification.

It does not cover target-model relationship changes, project or change-request validation semantics, Core link behavior, YAML editor removal, or the existing target-model entity picker's missing-entity behavior.

## Current Position

- YAML authoring of `foreign_key_value_sources` is shipped: `TableConfig.foreign_key_value_sources` accessor in [`src/model.py`](../../../src/model.py), a typed field on the backend `Entity` model, a generated entity-schema entry, change-request ingester consumption, and Core conformance validators in [`src/target_model/conformance.py`](../../../src/target_model/conformance.py).
- Core conformance already reports `DIRECT_FK_OUTPUT_COLUMN_MISSING` for a declared `public_id` source whose target column is absent from `get_target_facing_columns()`.
- The existing [`TargetModelEntityOptionsService`](../../../backend/app/services/target_model_entity_options_service.py) returns only target-model entities absent from the project, with required-link summaries. It exposes no per-entity direct-FK list.
- The entity dialog's form model, YAML parser, saved-entity hydrator, YAML generator, and save payload each use explicit field lists that omit `foreign_key_value_sources`, so the field is dropped on save and on YAML/form switching.
- Validation messages already carry entity and column/field values and can open the entity editor by name, but no action targets an entity's column settings.
- The generated entity schema already documents the field, so YAML editing recognizes it today.

Structural assumption: the entity dialog remains the single edit surface for entity configuration.

## Phase Plan

### Phase 1: Read-only direct-FK relationship metadata contract

**Goal**

Return resolved direct target-model FK metadata for one project entity, with distinct unconfigured, unresolved, and resolved outcomes.

**Focus**

- Add a read-only backend response that returns every direct target-model FK compatible with direct-ID mode for the named entity: no `via`, target declares both `public_id` and `target_table`.
- Include target entity name, `public_id`, and `target_table`, and include optional relationships and targets already present in the project.
- Do not filter on whether the source currently produces the ID column.
- Report unconfigured target model, resolution failure, and a resolved model as separate outcomes.
- Leave the existing missing-entity picker endpoint, response model, and service behavior unchanged.

**Depends On**

- Proposal decisions on direct-ID eligibility and rejected alternatives.
- Current target-model resolution behavior already used by the missing-entity picker.

**Outputs**

- A stable read-only contract the entity dialog can call while editing any project entity.

**Acceptance Criteria**

- `PH1-AC-1` (from `P-AC-1`) Unconfigured and unresolvable target models produce distinct outcomes that never appear as an empty relationship list.
- `PH1-AC-2` (from `P-AC-2`) A resolved model returns all direct target-model FKs for the entity, including optional targets and targets configured in the project, while the existing picker response is unchanged.
- `PH1-AC-3` (from `P-AC-3`) The contract includes compatible relationships whose target ID column is not currently produced by the source.

**Validation Milestones**

- `VM-1` Backend tests cover the three states, optional and already-configured targets, and a relationship whose ID column is not produced; existing picker tests stay green. Covers `PH1-AC-1`–`PH1-AC-3`.

**Task-Plan Handoff**

- Source criteria: `P-AC-1`, `P-AC-2`, `P-AC-3`.
- Fixed decisions: eligibility is direct-only with target `public_id` and `target_table`; no column filtering; picker behavior untouched.
- Constraints: read-only, absolute imports, Core stays the authority for output-column validation.
- Blocking questions: none. Route naming and response-model naming are task-plan decisions.

**Readiness**

Ready for a task plan.

### Phase 2: Preserve the complete value-source map through the entity dialog

**Goal**

Make the full `foreign_key_value_sources` map survive parsing, form state, YAML/form switching, saving, and reload without altering any entry.

**Focus**

- Carry the complete map through the YAML parser, saved-entity hydration, form state, YAML generation, and both save paths.
- Preserve explicit `system_id` entries and stale or ineligible entries unchanged unless the user edits them.
- Do not create project `foreign_keys` links or dependencies from the map.
- Keep the existing backend model and mapper round-trip behavior; change them only if a verified defect blocks preservation.

**Depends On**

- Current entity-dialog serialization and raw-field preservation patterns.
- No dependency on Phase 1.

**Outputs**

- A dialog that reads, holds, and writes the map intact before any visual control exists.

**Acceptance Criteria**

- `PH2-AC-1` (from `P-AC-6`) A mixed map containing `public_id`, explicit `system_id`, and stale entries survives YAML→form→YAML, save, and reload with every entry unchanged.
- `PH2-AC-2` (from `P-AC-8`) Preserved entries create no project FK link or dependency, and default `system_id` behavior is unchanged.

**Validation Milestones**

- `VM-2` Frontend tests exercise parse, serialize, and save payloads for a mixed map; a saved entity reloads with identical entries; Core link and dependency counts stay unchanged. Covers `PH2-AC-1`, `PH2-AC-2`.

**Task-Plan Handoff**

- Source criteria: `P-AC-6`, `P-AC-8` (map-preservation part).
- Fixed decisions: only eligible `public_id` entries become selectable in Phase 3; other entries are preserved, not normalized away.
- Constraints: reuse the existing raw-field representation approach; do not introduce Core links.
- Blocking questions: none.

**Readiness**

Ready for a task plan.

### Phase 3: Add the Direct target IDs selector and its states

**Goal**

Let authors select and clear eligible direct target IDs in the entity editor with correct state handling and no side effects.

**Focus**

- Add a multi-select labeled **Direct target IDs** in the Basic section near produced columns, populated from the Phase 1 contract.
- Show a disabled selector with a prompt when no target model is configured, an error when resolution fails, and the selector when a model resolves.
- Offer every compatible relationship regardless of whether the ID column is produced; label choices by target entity and ID column.
- Disable choices that conflict with a project `foreign_keys` link to the same target and explain why.
- Selecting sets `foreign_key_value_sources.<target>` to `public_id`; clearing removes only that entry; stale entries stay visible and preserved; explicit `system_id` entries are not shown as selected.
- Create no project FK link or dependency from a selection.

**Depends On**

- Phase 1 metadata contract.
- Phase 2 map preservation.

**Outputs**

- A working selector whose saved output is the unchanged map plus only user-edited entries.

**Acceptance Criteria**

- `PH3-AC-1` (from `P-AC-1`) With no resolved target model, the selector cannot add any direct-ID entry.
- `PH3-AC-2` (from `P-AC-3`) Every compatible relationship is selectable even when its target ID column is not produced.
- `PH3-AC-3` (from `P-AC-5`) Selecting and clearing a target changes only its own entry and creates no project FK link or dependency.
- `PH3-AC-4` (from `P-AC-7`) Missing, unresolved, and resolved states are distinguishable, and project-FK conflicts are disabled with an explanation.
- `PH3-AC-5` (from `P-AC-6`) Only eligible `public_id` entries appear selected, while `system_id` and stale entries remain visible and preserved.

**Validation Milestones**

- `VM-3` Component tests cover each state, selection and clearing, conflict disabling, choice labels, and display of a mixed map; the saved payload contains no new links. Covers `PH3-AC-1`–`PH3-AC-5`.

**Task-Plan Handoff**

- Source criteria: `P-AC-1`, `P-AC-3`, `P-AC-5`, `P-AC-6` (display half), `P-AC-7`.
- Fixed decisions: entity-level multi-select, Basic section placement, no filtering by produced column.
- Constraints: no duplicated output-column validation; no picker changes.
- Blocking questions: none.

**Readiness**

Ready for a task plan.

### Phase 4: Make a missing target ID column visible and fixable

**Goal**

Turn the existing missing-output-column conformance result into an actionable path to the affected entity's column settings.

**Focus**

- Confirm the existing conformance issue reports the project entity and exact column under Core's target-facing rules; adjust only where a verified gap exists.
- Provide a direct action from the validation result to the affected entity's column settings with guidance to add the column or remove the direct-ID selection.
- Prefer extending the existing validation-to-entity navigation over adding a parallel route.
- Keep the selector free of duplicated output-column checks.

**Depends On**

- Phase 3 selection behavior.
- Existing conformance validators and validation-message mapping.

**Outputs**

- A validation route from missing column to fix that later validation work can reuse.

**Acceptance Criteria**

- `PH4-AC-1` (from `P-AC-4`) A selected target with no produced ID column yields a validation issue naming the entity and exact column, and exposes an action that opens that entity's column settings.

**Validation Milestones**

- `VM-4` Backend tests assert the issue code, entity, and column; frontend tests assert the action opens the entity editor at column settings. Covers `PH4-AC-1`.

**Task-Plan Handoff**

- Source criteria: `P-AC-4`.
- Fixed decisions: Core owns the check; the UI only surfaces it.
- Constraints: existing validation message fields and existing navigation are the preferred mechanism.
- Blocking questions: none. Exact tab/focus behavior is a task-plan decision that does not change validation semantics.

**Readiness**

Ready for a task plan.

### Phase 5: Compatibility and regression verification

**Goal**

Prove that shipped behavior outside the new selector is unchanged.

**Focus**

- Run the existing suites for the entity form, entity schema and YAML intelligence, target-model picker, Core model and conformance, and change-request ingester.
- Confirm no Core link or dependency is created and `system_id` defaults still apply.
- Confirm YAML-only authoring still works and that the selector reflects existing `public_id` entries after reload.
- Keep the plan and documentation aligned with shipped behavior.

**Depends On**

- Phases 1–4 outputs.

**Outputs**

- Verified preserved behavior and a short record of any intentional deviations.

**Acceptance Criteria**

- `PH5-AC-1` (from `P-AC-8`) Existing YAML editing and schema completions, default `system_id` behavior, Core links, and change-request validation results are unchanged.

**Validation Milestones**

- `VM-5` Grouped regression run across the listed suites reports no new failures, and a project using direct IDs only in YAML still validates and packages as before. Covers `PH5-AC-1`.

**Task-Plan Handoff**

- Source criteria: `P-AC-8`.
- Fixed decisions: regression scope is the existing suites; no new behavior is introduced here.
- Constraints: report deviations rather than fixing unrelated failures.
- Blocking questions: none.

**Readiness**

Ready for a task plan.

## Cross-Phase Rules

- Core conformance and the change-request ingester stay authoritative for validation; the selector must not add a second check.
- A value-source selection never creates a project `foreign_keys` link or dependency.
- Preserve unrecognized or ineligible map entries unless the user explicitly changes them.
- Keep YAML and form editing equivalent: a change that works in one path must work in the other.
- Do not change the existing missing-entity picker contract.
- Validate each phase before starting the next; later phases consume earlier outputs.

## Validation Strategy

- Unit tests for the read-only contract, including state separation and relationship eligibility.
- Dialog tests for parse/serialize/save round-trip of a mixed map.
- Component tests for selector states, selection, clearing, and conflict disabling.
- Validation tests for issue entity, column, and the navigation action.
- Grouped regression across existing entity, schema, picker, Core, and change-request suites.

Exact commands, test files, fixtures, and assertions belong in each phase task plan.

## Final Recommendation

Deliver the contract first, then preservation, then the selector, then the fix path, then regression verification. This order keeps every intermediate state safe to merge: no phase can drop an existing declaration or change Core behavior.
