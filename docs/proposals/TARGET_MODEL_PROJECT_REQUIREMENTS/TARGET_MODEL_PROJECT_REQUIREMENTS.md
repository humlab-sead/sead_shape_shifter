# Target Model Project Requirements

## Status

- Proposed change request — draft for review
- Scope: Project entity and relationship requirements, the remaining standard-model gaps, and the Shape Shifter support those decisions need.
- Goal: Require project declarations for the data and relationships a project supplies, finish the standard model against the live SEAD schema, and make the model's rules checkable by tooling.
- Absorbs: the closed review, gap triage, and conditional-FK inventory described in [TARGET_MODEL_COVERAGE_REVIEW.md](TARGET_MODEL_COVERAGE_REVIEW.md).

## Summary

Two things are undecided. First, when a project must include a target-model entity, declare a link, or supply an FK value. Second, which remaining model changes and Shape Shifter changes are needed to finish the standard model.

Define project requirements from the rows and relationships a project supplies or resolves, not from the full target-model graph. Require a project entity when the project reconciles or creates rows for that entity. Require a project link when FK values are resolved through local `system_id` values. Allow a valid direct target `public_id` for a supported FK without a project lookup entity or Core link. Evaluate conditional FK requirements against the rows selected for insertion, and keep target database constraints in force.

Close the model gaps the same way: give every unmapped table an explicit decision, correct the model where it disagrees with the target schema, and add the missing format and validation support so these rules can be checked rather than inspected by hand.

## Problem

The target model describes target tables, columns, and foreign keys. Project conformance separately checks whether project entities, links, and columns are declared. These checks serve different purposes, but current model settings can make it unclear whether a project needs to represent a relationship that is already present in the target database.

For example, a project that inserts a row with an existing target ID may not need a project entity for the referenced lookup. A project that reconciles or creates rows for that lookup does need an entity for that work. Likewise, a project that only refers to existing sites should not need to reproduce their existing site-location relationship, while a project creating site-location rows must represent that relationship.

The [archived target-model review](archive/TARGET_MODEL_REVIEW.md) identifies these questions for `location` and `location_type`, `site` and `site_location`, and `method` and `method_group`. Without a shared rule, settings such as entity `required`, FK `required`, column `required`, and `required_when` can be applied as if they meant the same thing.

Three working documents carried this work until 2026-11-12: an entity-by-entity review, a gap triage for unmapped tables, and a conditional-FK candidate inventory. Each ended with its own open checklist, and none of them described the code changes required on the Shape Shifter side. They are now closed and their remaining items sit in this proposal; a frozen snapshot of the measured coverage state is in the [coverage review](TARGET_MODEL_COVERAGE_REVIEW.md).

That leaves the second half of the problem. The standard model matches the live schema closely enough to be useful, but not closely enough to trust without manual checking: 17 source tables have no entity, several columns disagree on type or nullability, seven foreign keys name columns that do not exist, and no command measures any of it. Where the model needs a rule the format cannot express — a target-table default, a conditional FK behind a bridge — the limitation is recorded but not decided.

## Scope

- Define project entity and link requirements for target-model lookup, classifier, and bridge entities.
- Distinguish references to existing target rows from reconciling or creating target rows.
- Define how project requirements interact with direct target IDs and conditional FKs.
- Decide the remaining standard-model gaps: unmapped tables, nullability and type differences, and foreign keys that name missing columns.
- Decide the Shape Shifter changes those rules need: conditional FKs behind bridges, target-table defaults, schema qualification, coverage measurement, and deployment-time ID eligibility.
- Apply the rule to the open cases in the [archived target-model review](archive/TARGET_MODEL_REVIEW.md).

## Non-Goals

- Changing target database tables, columns, or FK constraints.
- Changing Core FK links from local `system_id` values to target IDs.
- Extending direct target-ID value sources beyond the existing Change Request Ingester contract, or to bridge FKs using `via`.
- Implementing the coverage command itself; that work belongs to the [coverage-boundary proposal](../SEAD_TARGET_MODEL_COVERAGE_BOUNDARY.md).
- Resolving sample resubmission identity, which stays deferred as recorded in the archived review.
- Including ceramics, dendro, and image subsystem tables in the standard model without a project that needs them.

## Current Behavior

- Target-model entity `required: true` means every conforming project must include that entity. FK `required: true` means every conforming project must declare the project link. Column `required` controls whether a project must provide that column. These are project conformance requirements, not target database nullability or evidence that a row will be inserted. See the [Target Model Guide](../../../docs/TARGET_MODEL_GUIDE.md).
- A `required_when` FK is evaluated after reconciliation selects rows for insertion. Project-only conformance reports that the result is pending because it cannot know the final insert set.
- The Change Request Ingester can use an explicit `foreign_key_value_sources.<target>: public_id` declaration for a supported direct FK. That relationship does not need a project lookup entity or Core link, but supplied IDs must be checked against the target database. Core FK links continue to use local `system_id` values. See [Direct Target-Id Foreign Keys](../done/DIRECT_TARGET_ID_FOREIGN_KEYS/DIRECT_TARGET_ID_FOREIGN_KEYS.md).
- A valid direct-ID declaration suppresses the reconciliation-pending result for that conditional FK only. It does not waive required values on inserted rows, target-ID checks, an independently required target entity, or another relationship to the same target. See [Direct Target-ID Conditional FK Conformance](../done/DIRECT_TARGET_ID_CONDITIONAL_FK_CONFORMANCE/DIRECT_TARGET_ID_CONDITIONAL_FK_CONFORMANCE.md).
- The direct-ID mode is declared per project entity and target FK. The current contract does not allow mixing `system_id` and `public_id` values in that same FK column.

### Model and support state (verified 2026-11-12)

- The standard model has 136 entities and covers 133 of the 150 effective source tables. Seventeen tables remain unmapped; the model declares no table that the source lacks, and specification validation reports no issues.
- Model-to-source differences remain: 17 undeclared source columns, one model column absent from its source table, 6 type differences, and 47 nullability differences. Seven foreign keys name columns the target table does not have.
- Two rules the model needs are not expressible today: conditional requiredness on a bridge foreign key (`CONDITIONAL_FOREIGN_KEY_VIA_UNSUPPORTED`) and a target-table column default (`ColumnSpec` has no `default` field).
- The coverage counts are a manual measurement. No command compares the model to the schema source yet.

Figures and their sources are in the [coverage review](TARGET_MODEL_COVERAGE_REVIEW.md).

## Proposed Design

### Separate target relationships from project requirements

Keep target-model FKs as declarations of target database relationships. Do not remove a target-model FK merely because a project supplies a target ID directly or does not create relationship rows. A target database FK remains responsible for enforcing referential integrity on stored rows.

Treat project entity presence, project links, and FK values as separate requirements:

- **Project entity:** A project includes an entity when it supplies rows to reconcile or create for that target entity, or when the target model independently marks the entity as required for every conforming project.
- **Project link:** A project declares a link when it uses the local `system_id` path to resolve FK values. An existing target row ID supplied through a valid direct-ID declaration does not need a project lookup entity or Core link for that FK.
- **FK values:** A project supplies values required by the target-model FK rules for rows selected for insertion. A direct target ID must identify an existing target row and pass the target-database check.
- **Relationship or bridge rows:** A project supplies a bridge entity when it creates or reconciles relationship rows. It need not supply bridge rows merely to restate relationships that already exist between target rows.

### Apply conditional requirements after reconciliation

Use `required_when` when the lookup entity, project link, or FK value is needed only if source rows will be inserted. If reconciliation selects no rows for insertion, that conditional requirement does not require the project to supply lookup or relationship rows. If rows are inserted through the local `system_id` path, require the lookup entity and link. If the project instead uses a valid direct target ID for that FK, do not require the project lookup entity or link, but still require and check the FK value.

### Keep independent requirements explicit

An entity-level `required: true` remains an independent project-wide requirement; a direct-ID declaration for one FK does not override it. Use this flag only when every conforming project must include the entity. Do not infer project entity or link requirements solely from a target column being non-nullable or from the existence of a target database FK.

Keep the current project-mode rule: each entity/FK selects one value source. A project that needs both direct IDs and local `system_id` links for different source rows must use separate project entities or another explicitly supported representation; do not infer the mode from row values or whether the lookup entity is present.

### Complete the standard model

Give every unmapped table an explicit outcome instead of leaving it in a triage list:

- Model it when a project needs the data.
- Exclude it deliberately when it is a subsystem table outside the standard scope, and record the exclusion where coverage is measured.
- Defer it with a named condition when a project will need it later.

Apply the same explicit treatment to model-to-source differences. A nullability or type difference is either corrected in the model or accepted with a stated reason. Correct the seven foreign keys that name missing columns: the analysis value and range entities reference `value_qualifier_symbol` through their text `qualifier`, `low_qualifier`, and `high_qualifier` columns, and `value_qualifier_symbol` references `value_qualifier` through `cardinal_qualifier_id`.

Decide the twelve conditional-FK pairs the closed inventory identified as worthwhile, in two groups: six that need only the FK and column change, and six that share a `required: true` target and must be decided together because relaxing the target also loosens every other referrer. Leave the remaining pairs unchanged, because their condition would be permanently true and would weaken an existing check.

Resolve or explicitly defer each entity decision carried over from the archived review: `location`, `site` and `site_location`, `sample_group`, `sample_group_reference`, `value_type_item`, `method` and `method_group`, `dataset`, and the provider-UUID question.

### Support the model in Shape Shifter

The model rules above need support that does not exist yet. Each item below is a decision this proposal must settle, not an implementation plan:

- **Conditional FK behind a bridge.** `site` → `location` is declared `via: site_location`, and the validator rejects `required_when` on a bridge FK. Either allow the condition on bridge FKs, or record that `site` → `location` stays unconditional and why.
- **Target-table defaults.** `ColumnSpec` has no `default` field. Either add it so a model can state that the target supplies a value, or keep requiring every project to provide the column and drop the default question.
- **Schema qualification.** Model `target_table` values are unqualified while staging exposes the same names in `public` and `clearing_house`. Qualify the model's table names or pin the deployment `search_path`; do not leave resolution ambiguous.
- **Coverage measurement.** Depend on the measurement command from the [coverage-boundary proposal](../SEAD_TARGET_MODEL_COVERAGE_BOUNDARY.md) so counts are reproducible instead of hand-counted.
- **Deployment-time ID eligibility.** Refresh the generator audit for the current aggregate-child inventory, and keep `value_type_item` ineligible until it has a generator.
- **Required-column projection.** The Change Request Ingester derives `required_fk_columns` from column `required` flags, so relaxing a column for a conditional FK also drops it from the unconditional check. Confirm the conditional path still rejects a missing value for those pairs.
- **Project migration.** `site` no longer declares `site_type_id`, so projects that still set it must move to `site_site_type` rows. Provide a conformance message that names the replacement.

## Alternatives Considered

- **Require every project to mirror all target relationships.** Rejected because projects would have to repeat existing target rows and relationships they do not create or reconcile.
- **Infer direct-ID mode from the values or absence of a lookup entity.** Rejected because adding or removing a project entity could silently change how FK values are interpreted. The mode must remain explicit.
- **Use target database nullability and FKs as project inclusion rules.** Rejected because database constraints govern stored rows, while project conformance governs what a project must declare and provide.
- **Allow `required: true` to mean “required only when rows are inserted.”** Rejected because it would change the existing project-wide meaning of the field. Use `required_when` for insert-dependent requirements.
- **Keep the three working documents open.** Rejected because each carried its own open checklist, none covered the Shape Shifter changes, and decisions drifted between them. One decision document plus a frozen measurement is easier to close.
- **Model every remaining source table.** Rejected because ceramics, dendro, and image subsystem tables would add entities that no project supplies. A recorded exclusion measures the same thing without unused model surface.
- **Fix every model-to-source difference immediately.** Rejected because some differences are correct: a range type or a timestamp stored as a simpler type can be the intended model shape. Each difference is decided, not blanket-corrected.

## Risks And Tradeoffs

- A direct target ID can be checked for existence but may still identify the wrong existing row. Project review must confirm that the supplied ID represents the intended target.
- An overly broad direct-ID exemption could hide another relationship or independent entity requirement. Apply the exception per FK and retain all other conformance checks.
- Project-only validation cannot determine which conditional requirements apply before reconciliation. It must report the requirement as pending rather than treating it as passed or failed.
- The current direct-ID contract is limited to supported direct FKs in the Change Request Ingester. Other project processing continues to use the established Core `system_id` link behavior.
- Coverage counts drift unless they are measured. Until the coverage command exists, this document's snapshot ages like the documents it replaced.
- Relaxing a shared `required: true` target loosens the requirement for every other referrer, so the six shared-target pairs must be decided per target rather than per foreign key.
- Adding target-default support changes how projects express required columns and needs a clear rule about which layer supplies the value.
- Deferring an entity decision keeps a question open across releases. Deferrals are acceptable only with a named condition for reopening them.

## Testing And Validation

- Check project conformance for an omitted optional lookup with a valid direct-ID declaration, an omitted lookup with a local `system_id` link, and an independently required target entity.
- Check conditional FKs when reconciliation selects zero rows and at least one row for insertion, with both local-link and valid direct-ID modes.
- Check that direct-ID values are still required when the FK condition applies and that nonexistent target IDs are rejected.
- Check that projects need not provide bridge rows for existing target relationships, but must provide relationship rows and required links when creating or reconciling them.
- Check that Core FK behavior and existing projects using local `system_id` links remain unchanged.
- Review the `location`/`location_type`, `site`/`site_location`, and `method`/`method_group` cases against the agreed rules. Keep unrelated target-schema questions separate.
- Run target-model specification validation and the conformance baseline tests after each model change, and confirm the baseline counts move only as intended.
- Verify every corrected qualifier foreign key against `columns.csv`, and confirm no model foreign key names a column the target table lacks.
- Confirm the mapped count rises and the unmapped count falls as entities are added, using the measurement command rather than a manual count.
- Confirm a project that still declares `site.site_type_id` receives a message that names `site_site_type`.
- Confirm a conditional FK whose column `required` flag was relaxed still rejects a missing value on rows selected for insertion.

## Acceptance Criteria

- `P-AC-1` The target-model guidance distinguishes target database relationships from project entity, link, and FK-value requirements.
- `P-AC-2` A project is not required to include a lookup or classifier entity solely because a target-model FK points to it; the entity remains required when independently marked `required: true`.
- `P-AC-3` A valid direct target-ID declaration removes the project lookup-entity and Core-link requirement for that FK only, while retaining required-value and target-database existence checks.
- `P-AC-4` A conditional FK requires a lookup entity and project link only when reconciliation selects rows for insertion and the project uses the local `system_id` path.
- `P-AC-5` A project need not repeat existing target relationship rows, but must represent relationship rows it will create or reconcile.
- `P-AC-6` The default `system_id` behavior remains unchanged, and the project does not infer a value source from entity presence or FK values.
- `P-AC-7` The reviewed `location`, `site`, and `method` cases are classified using the agreed rules, with unrelated schema questions tracked separately.
- `P-AC-8` The three closed target-model documents have one successor, and every open item they carried is decided here or deferred with a named condition.
- `P-AC-9` Every unmapped source table has one of three recorded outcomes: modelled, deliberately excluded, or deferred with a named condition.
- `P-AC-10` Every model-to-source column difference is corrected or accepted with a stated reason.
- `P-AC-11` No model foreign key names a column absent from its target table.
- `P-AC-12` Conditional FK requiredness is either supported behind a bridge, or the `site` → `location` case is explicitly resolved without it.
- `P-AC-13` Coverage counts are reproducible from a command against the declared source of truth.
- `P-AC-14` Resolution of model `target_table` values against the deployment schema is unambiguous.
- `P-AC-15` Every aggregate child treated as eligible for deployment-time ID allocation has a verified ID generator, or is excluded.
- `P-AC-16` A project that still declares `site.site_type_id` receives a conformance message that names `site_site_type`.
- `P-AC-17` The standard model passes specification validation and the documented conformance tests, with no unintended change to existing project conformance results.

## Planning Handoff

**Confirmed constraints**

- Target-model FKs continue to describe target database relationships.
- Core FK links continue to use local `system_id` values.
- Direct target IDs require an explicit supported declaration and target-database existence checks; the exception applies only to that FK.
- `required: true` remains an independent project-wide entity requirement. `required_when` remains dependent on the final insert set.
- Direct-ID and `system_id` values are not mixed in one entity/FK column.

**Expected validation**

- Project-only conformance distinguishes independent required entities, local links, and valid direct-ID declarations.
- Post-reconciliation validation checks conditional requirements against rows selected for insertion.
- Change Request Ingester validation still rejects missing required FK values and nonexistent direct target IDs.
- Model changes keep target-model specification validation clean, and the mapped and unmapped counts move only as intended.
- Coverage counts come from a command, not from a manual tally.

**Open questions and the phase that must resolve each**

- Whether ceramics, dendro, and image subsystem tables belong in the standard model or a separate subsystem model — resolve before the model-completion phase starts.
- If one logical project needs direct IDs for some source rows and reconciliation/local links for others on the same FK, decide in Phase 1 whether separate project entities are sufficient. Per-row mixed value sources are not supported by the current contract and require a separate design if needed.
- Whether `default` belongs in the target-model format at all, or target defaults stay outside the model — resolve in the Shape Shifter support phase.
- Whether every conforming project must include `site` even when it only references existing sites — resolve with the project-requirement rules.

## Recommended Delivery Order

1. Settle the project-requirement rules and apply them to `location`, `site`, and `method`.
2. Decide the remaining model gaps: unmapped tables, column differences, and the qualifier foreign keys.
3. Add the Shape Shifter support the rules need: bridge conditional FKs, defaults, schema qualification, and required-column projection.
4. Migrate projects to `site_site_type` and confirm the coverage counts from the measurement command.

## Final Recommendation

Adopt project requirements based on the rows and relationships a project supplies or resolves, not on the full target-model graph. Keep target database constraints intact, make direct-ID use explicit, and evaluate conditional requirements only after reconciliation determines which rows will be inserted.

Treat finishing the standard model as the same kind of decision: every remaining table, column difference, and unsupported rule gets an explicit outcome rather than staying in a triage list. Where the model cannot express a rule the project requirements depend on, change Shape Shifter rather than leaving the gap recorded.
