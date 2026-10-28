# Target Model Guided Entity Creation — Phase Plan

Source proposal: [Scaffold Project Entities From an Associated Target Model](TARGET_MODEL_GUIDED_ENTITY_CREATION.md)

## Summary

Deliver the target-model picker in three phases: provide authorized target facts, use them to start an entity draft, then show the remaining requirements and verify the save flow. Each phase has a result that the next phase can use.

## Problem

The Add Entity form starts blank even when the project has a target model. The plan must expose target requirements without treating target output columns or links as source mappings.

## Scope

This plan covers the project-scoped read operation, the existing create form, and validation of the guided workflow. It excludes changes to the full project-template generator, command-line helper, target model, and create-mode Foreign Keys editor.

## Current Position

- `ProjectMapper.to_core()` resolves the project's associated target model for conformance. The raw target-model YAML endpoint is limited to project-local files.
- The create form defaults to `type: entity`, saves through the existing entity-create operation, and disables the Foreign Keys tab before creation.
- The full template generator inserts required target columns and direct FK targets into project fields. The guided form must not reuse those mappings.

## Phase Plan

### Phase 1: Authorized Target Options

**Goal**

Provide the create form with target-model choices and reference information from the associated model.

**Focus**

- Resolve the model through the project mapper under project read authorization. Distinguish no configured model from a configured model that cannot be loaded or parsed.
- Return absent entity names, role and required labels, declared `public_id`, required non-generated columns, and required direct or bridged link paths.
- Keep reference requirements separate from the name and `public_id` used to start the draft; do not accept a browser-supplied model path.

**Depends On**

- The existing project model, mapper, and target-model definitions.

**Outputs**

- A project-scoped read contract for the create form.

**Acceptance Criteria**

- `PH1-AC-1` (from `P-AC-1`) The operation returns every target-model entity absent from the project with its role and required status.
- `PH1-AC-2` (from `P-AC-2`) No configured model and a model load or parse failure produce distinguishable results without changing the project.
- `PH1-AC-3` (from `P-AC-8`) Returned requirements exclude generated columns from the required source-work list and represent `via` links as bridge paths.

**Validation Milestones**

- `VM-1` Confirm `PH1-AC-1`, `PH1-AC-2`, and `PH1-AC-3` for local, shared, inline, absent, missing, and invalid models, including read authorization.

**Task-Plan Handoff**

- Source criteria: `P-AC-1`, `P-AC-2`, `P-AC-8`. Preserve mapper-based resolution, project authorization, and the separation between reference requirements and saved entity fields. No blocking decision remains.

**Readiness**

Ready for a task plan.

### Phase 2: Guided Identity Draft

**Goal**

Let a user select a target entity and start a draft without changing the manual create or save flow.

**Focus**

- Add the clearable picker to create mode and load the Phase 1 options. Keep manual creation usable without a resolved model.
- Fill the exact target name and declared `public_id`. Fix the name while selected; clearing the picker restores manual editing. Protect edited identity fields when selection changes.
- Require an explicit source type choice for a selected entity and restrict selected classifiers to `fixed` or `sql`.
- Keep selection read-only with respect to the project; submit through the existing create action.

**Depends On**

- Phase 1 read contract.

**Outputs**

- A usable guided create draft with the normal save behavior.

**Acceptance Criteria**

- `PH2-AC-1` (from `P-AC-2`) Manual creation remains usable when the picker is absent or reports a configured-model error.
- `PH2-AC-2` (from `P-AC-3`) Selection fills the exact name and declared `public_id`, locks the name, and protects edited identity fields on replacement; clearing selection restores name editing.
- `PH2-AC-3` (from `P-AC-5`) A selected classifier can be saved only with `fixed` or `sql`.
- `PH2-AC-4` (from `P-AC-6`) Selecting an option makes no project write; the existing save action persists the completed form.
- `PH2-AC-5` (from `P-AC-9`) Saving a selected target entity is blocked until the user explicitly selects a Shape Shifter source type; the default `entity` value alone does not satisfy this requirement.

**Validation Milestones**

- `VM-2` Confirm `PH2-AC-1` through `PH2-AC-5` in create mode, including manual fallback, selection changes, explicit source-type selection, classifier type choice, and save timing.

**Task-Plan Handoff**

- Source criteria: `P-AC-2`, `P-AC-3`, `P-AC-5`, `P-AC-6`, `P-AC-9`. Preserve the existing entity-create operation and manual form. Require an explicit source-type choice for every selected target entity; the default `entity` value alone is not sufficient. Restrict selected classifiers to `fixed` or `sql`. Do not enable the Foreign Keys tab in create mode. No blocking decision remains.

**Readiness**

Ready for a task plan.

### Phase 3: Requirements and Completion

**Goal**

Show the target requirements beside the draft and keep the picker accurate after save.

**Focus**

- Display required non-generated columns, direct links, bridge paths, and missing entities as reference information.
- Prevent target facts from populating project `columns`, `foreign_keys`, or `keys`. Leave source columns and joins to the existing editors.
- Refresh candidates after creation and validate the guided workflow through structural and target-model conformance checks.

**Depends On**

- Phase 1 target facts and Phase 2 draft behavior.

**Outputs**

- The complete guided creation flow with requirement guidance and refreshed candidates.

**Acceptance Criteria**

- `PH3-AC-1` (from `P-AC-4`) Selecting an option adds no values to project `columns`, `foreign_keys`, or `keys`; only user-configured values are saved.
- `PH3-AC-2` (from `P-AC-8`) The form shows required non-generated columns and direct or bridged link paths without suggesting a direct FK for a `via` link.
- `PH3-AC-3` (from `P-AC-7`) Existing entities are absent from the options, and a newly saved entity disappears after the list refreshes.
- `PH3-AC-4` (from `P-AC-6`) Requirement display makes no project write; incomplete saved entities report remaining gaps through existing validation.

**Validation Milestones**

- `VM-3` Confirm `PH3-AC-1`, `PH3-AC-2`, `PH3-AC-3`, and `PH3-AC-4` with direct and `via` links, generated columns, a save and refresh, and validation of an incomplete entity.

**Task-Plan Handoff**

- Source criteria: `P-AC-4`, `P-AC-6`, `P-AC-7`, `P-AC-8`. Keep requirements out of saved entity fields and keep joins in the post-create editor. No blocking decision remains.

**Readiness**

Ready for a task plan.

## Cross-Phase Rules

- Read only the associated target model, under project read authorization.
- Preserve manual Add Entity and the existing save behavior.
- Treat target columns and links as requirements to satisfy, not as inferred source mappings.
- Keep the template generator and command-line helper outside this work.

## Validation Strategy

- `VM-1` checks the server contract and model resolution before the picker uses it.
- `VM-2` checks draft behavior and the normal create action before requirement guidance is added.
- `VM-3` checks the complete workflow, candidate refresh, and expected validation gaps after an incomplete save.
