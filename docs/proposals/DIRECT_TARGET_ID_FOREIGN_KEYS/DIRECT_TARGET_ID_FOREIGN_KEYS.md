# Direct Target-Id Foreign Keys

## Status

- Proposed feature / change request
- Scope: project FK value declarations, target-model conformance, SEAD change-request validation and projection
- Goal: accept existing target ids in an FK column without requiring a project entity used only to translate those ids

## Summary

Add an explicit `foreign_key_value_sources` declaration to a project entity. A project can select `public_id` for a direct FK already defined by its target model. The target model continues to define the relationship and its requirements; the project declares how its source values are represented. With no declaration, FK values remain local `system_id` values and current behavior is unchanged.

This removes helper entities whose only purpose is to translate an existing SEAD id into a local `system_id`. Each packaged target id must be confirmed against the target database before a change request is accepted.

Related documents:

- [Target Model Guide](../../../docs/TARGET_MODEL_GUIDE.md)
- [Conditional Target Model Requirements](../done/CONDITIONAL_TARGET_MODEL_REQUIREMENTS/CONDITIONAL_TARGET_MODEL_REQUIREMENTS.md) — the `required_when` rule this declaration composes with
- [Target Model Conditional FK Candidates](../../../resources/target_models/TARGET_MODEL_CONDITIONAL_CANDIDATES.md) — candidate inventory, not a count of projects that can drop an entity
- [Advanced FK Validation Modes](../future/ADVANCED_FK_VALIDATION_MODES.md), [FK Null-Key Policy Model](../future/FK_NULL_KEY_POLICY_MODEL.md) — related deferred work

## Problem

Core FK links use a referenced project's local `system_id`. When a source already supplies a SEAD id, a user may have to declare and populate a referenced entity solely to convert that id to a local `system_id`. The entity then enters identity planning even though the source has already identified the target row.

For example, `location.location_type_id` may already contain SEAD `location_type_id` values. The standard target model gives this FK `required_when`, so project-only conformance reports that it awaits reconciliation; it does not currently reject the missing `location_type` entity on that rule alone. Change-request projection still needs a resolved `location_type` table to translate non-null values, and fails when that table is absent. Required FKs can also trigger missing-target and induced-entity conformance errors.

The standard target model is shared by projects with different sources. The value interpretation therefore belongs to each project, while the target model remains the authority for which relationships exist.

## Scope

- A project entity declaration for the value source of a target-model direct FK.
- Structural and project conformance rules for that declaration.
- A resolved value-source handoff to the change-request ingester, target database existence checks, and projection for supplied ids.
- Configuration guide, API model, and editor schema updates for the project declaration.
- The root `AGENTS.md` and `src/AGENTS.md` identity rules, so they distinguish Core FK links from direct target IDs in change-request packages.

## Non-Goals

- Inferring value interpretation from whether the referenced project entity exists.
- Changing the default `system_id` behavior or the Core link algorithm for existing project FKs.
- Changing the Core FK value rule: Core project FK links continue to use local `system_id` values. The `public_id` option applies only when the change-request ingester writes a target-model FK column to a package.
- Mixing `system_id` and `public_id` values in one FK column.
- Accepting an id for a row that will be created by the same change request. Such rows continue to use local `system_id` links.
- Supporting non-integer target public ids, bridge FKs declared with `via`, synthesized bridges, or business-key reconciliation in this change.

## Current Behavior

Verified against the repository:

- `ForeignKeyConfig.generate_link_setup` names an FK column after the referenced entity's `public_id` while supplying its local `system_id` (`src/model.py`).
- `project_target_ids` maps local FK values through the referenced resolved table and casts projected IDs to `Int64` (`ingesters/sead_change_request/target_projection.py`).
- Project conformance has separate direct-FK, induced-required-entity, globally-required-entity, and no-orphan-fact checks (`src/target_model/conformance.py`). Skipping only the direct-FK check would not cover every case.
- The current target database checker is optional. `ingest_tables()` may use it for target collision checks; `validate_tables()` does not use it. The file-based `validate()` and `ingest()` methods reject retired file input (`ingesters/sead_change_request/ingester.py`, `ingesters/sead_change_request/collision_checks.py`).
- The change-request ingester receives a target model through `IngesterConfig.extra`; its current input does not include a project object or per-project FK value-source map (`ingesters/sead_change_request/input_resolution.py`).
- Column nullability validation checks `required: true` with a non-nullable column. The change-request projection also checks required FKs, but `nullable: false` alone does not reject a missing value (`src/target_model/data_validators.py`, `ingesters/sead_change_request/target_projection.py`).
- In the standard target model, `data_provider_id` is the public ID. `data_provider_uuid` is a separate UUID column, not a public-ID FK target (`resources/target_models/sead_standard_model.yml`).
- ArboDat and Strucke project fixtures both reference the standard target model (`tests/test_data/projects/arbodat/shapeshifter.yml`, `tests/test_data/projects/strucke_v5/shapeshifter.yml`).

Assumption: enough projects already carry SEAD ids to justify the new declaration. The candidate inventory identifies eligible relationships but does not measure how many helper entities projects can remove. A pilot will measure that result.

## Proposed Design

### Project declaration

The target model keeps its existing FK declaration. The project entity selects the representation of the values it produces:

```yaml
entities:
  location:
    columns: [system_id, location_type_id, location_name]
    foreign_key_value_sources:
      location_type: public_id
```

The map key is a target entity named by a direct FK on `location` in the resolved target model. Allowed values are `system_id` and `public_id`; an absent entry means `system_id`. `system_id` uses the existing project `foreign_keys` link. `public_id` means the project produces the column named by the target entity's `public_id` directly, without a project FK link to that target. The declaration is project metadata, not a Core join or dependency.

This changes only how the change-request ingester handles the declared output column. Core treats the supplied target ID as ordinary column data: it creates no project FK link or dependency for that declaration, and existing Core FK links still carry local `system_id` values. When building a change-request package, the ingester checks the declared value against the target table and preserves it in the target-model FK column.

The project cannot declare both a Core `foreign_keys` link and `public_id` mode for the same target-model FK. Any nonempty `foreign_key_value_sources` map requires `metadata.target_model`; projects without the map may still omit a target model. A direct-ID entry also requires a direct target-model FK without `via` and a target entity with both `public_id` and `target_table`. The target-model FK remains the authority for `required` and `required_when`.

The API project model and `ProjectMapper` preserve this declaration into Core. The change-request ingester receives a resolved per-entity value-source map in `IngesterConfig.extra`, alongside its target model. A caller using a saved project derives that map from the resolved project rather than re-entering it. A standalone caller may supply the same map explicitly. An absent map means every FK uses the current `system_id` path; the ingester never infers mode from table presence.

### Conformance and scaffolding

For a `public_id` declaration, project conformance checks that the source entity declares the target FK column as an output. It does not require a project entity or link for that FK and reports an informational issue that target ID existence awaits change-request validation. The direct-FK and induced-required-entity checks must both honor the declaration. A valid direct-ID relationship counts as a route to a lookup or classifier for the no-orphan-facts rule.

A target entity marked `required: true` in the target model remains required as a project entity for its own sake. Direct-ID mode does not waive that independent rule. The project scaffold continues to generate the current `system_id` form by default; a project author can replace a helper entity and link with the explicit direct-ID declaration where the target entity is otherwise optional.

### Change-request validation and projection

After identity planning determines which rows will enter the change request, each non-null direct-ID FK value on those rows is checked against the referenced target table and public-ID column in the target database. The lookup is read-only and required by both `validate_tables()` and `ingest_tables()` when there are values to check. Saved-project validation and ingestion use these table-based methods. If the lookup is unavailable, a value is malformed, or no target row exists, validation fails with the source entity, FK column, and offending value. There is no fallback to local `system_id` interpretation. Database constraints remain the final check when the package is deployed.

The first delivery accepts integer target public ids. The database column type is checked when a direct-ID value is packaged, because the target model may omit a column specification for its `public_id`. Values are normalized to integer form for comparison and payload typing, but are never remapped through a local entity. A non-integer target public-ID column fails validation with a clear error. The current standard target model provides no verified UUID or string public-ID FK target, so generic support is deferred until one is needed.

For rows selected for insertion, a missing value fails when the target-model FK is `required`, its `required_when` condition applies, or the target FK column declares `nullable: false`. An explicit null selected for an update fails when that column is non-nullable; an untouched FK on an update need not be supplied again. `required_when` retains its insert-based timing. No missing-value or target-existence check is needed for rows excluded from the package.

The package manifest records each FK that used direct target ids. The FK values remain in the packaged row data. This identifies the source of those ids for reviewers without writing artificial reconciliation links to the mapping sidecar.

### Validation rules

- Reject an unknown value source or a declaration for a relationship absent from the target model.
- Reject direct-ID mode without a target model, target `public_id`, or target table.
- Reject direct-ID mode for `via` relationships or a conflicting Core FK link. Reject a non-integer target public-ID column when database validation runs.
- Report these failures with machine-readable codes distinct from existing default-path codes.

## Alternatives Considered

- **Put `value_source` on the shared target-model FK.** Rejected because source representation varies by project. Changing one shared FK to `public_id` would reinterpret values in every project using that model.
- **Copy the target model per project.** Avoids a new project field but duplicates the relationship contract and creates model drift.
- **Infer from referenced entity presence.** Rejected because adding or removing an entity would silently reinterpret existing numeric values.
- **Reuse the project `foreign_keys` list for direct ids.** That list currently creates Core links and dependencies on a project entity. A separate value-source declaration keeps the two operations distinct.
- **Reconcile by business key.** Still requires a referenced project entity and solves a different problem.

## Risks And Tradeoffs

- The declaration adds a project setting and a required database lookup for direct-ID packages. Validation cannot pass offline when packaged direct IDs need an existence check.
- An existing target row may change between validation and deployment. The target database's FK constraint remains the final safeguard.
- A wrong but existing target ID can pass an existence check. Reviewers need to verify the intended reference in the source data; the manifest shows which FKs used supplied IDs.
- The first delivery supports integer public IDs only. A future non-integer target requires a separate type-aware contract rather than an unchecked cast.

## Testing And Validation

- Project configuration: accept both declared value sources and the default; reject an unknown source, unknown relationship, missing target metadata, `via`, and a conflicting Core FK link.
- Conformance: omit an otherwise optional referenced entity without direct-FK or induced-entity errors; retain the globally required-entity rule; count the direct relationship for no-orphan-facts; keep the default scaffold unchanged.
- Change request: pass the resolved map through the saved-project service into `validate_tables()` and `ingest_tables()`; preserve supplied integer IDs; reject a non-integer target column, missing target row, or unavailable lookup through both methods. Confirm that standalone callers can supply the map and that an absent referenced project table is not needed.
- Missing values: cover required, conditional, optional non-nullable, zero-insert, insert, and update cases.
- Regression: existing `system_id` projects produce the same results. Run `tests/target_model/`, `tests/model/test_target_model_conformance.py`, and `backend/tests/ingesters/`. Confirm the previously reported failures in `test_core_conformance_reports_known_gaps_for_full_arbodat_project` and `test_core_conformance_current_corpus_issue_families_are_stable` against the unmodified standard target model before comparing results.
- End-to-end: validate and package one direct-ID change request against a disposable PostgreSQL instance, including the manifest and a nonexistent ID.
- Pilot: count how many helper entities one representative project can remove.

## Acceptance Criteria

- `P-AC-1` A project entity accepts `foreign_key_value_sources` for target-model direct FKs, and saved-project callers pass its resolved map to the change-request ingester. The declaration creates no Core project link or dependency; existing Core FK links continue to carry local `system_id` values. Omission or `system_id` keeps existing Core linking and projection behavior.
- `P-AC-2` Invalid value sources, unknown relationships, missing target metadata, `via`, and conflicting Core FK links fail with machine-readable codes.
- `P-AC-3` A project using `public_id` may omit an otherwise optional referenced entity and link. Conformance reports an informational pending target check, no missing direct-FK or induced-entity error, and no false no-orphan-facts issue; globally required entities remain required.
- `P-AC-4` A direct-ID FK reaches the change request with the same target ID and is never rewritten through the local `system_id` map.
- `P-AC-5` Both `validate_tables()` and `ingest_tables()` reject a packaged direct ID that is malformed, absent from the target table, or unverifiable because the required lookup is unavailable. Saved-project validation and ingestion exercise these methods. The error names the source entity, column, and value where one was supplied.
- `P-AC-6` Missing direct-ID values on inserted rows follow `required`, `required_when`, and `nullable: false`; explicit null updates to non-nullable FK columns fail, and excluded rows do not block the package.
- `P-AC-7` Integer target ids are checked against the target database without a local-entity map; non-integer target public-ID columns fail validation when direct mode is used.
- `P-AC-8` Existing `system_id` projects retain their results and default-path diagnostics, subject to the recorded pre-existing test failures.
- `P-AC-9` The configuration guide, API project model, and editor schema document the declaration and default. `AGENTS.md` and `src/AGENTS.md` state that Core FK links remain `system_id`-based and that direct target IDs apply only to change-request package FK values. The default scaffold still generates local-ID links.
- `P-AC-10` The change-request manifest identifies direct-ID FKs, while the mapping sidecar remains a record of reconciliation links rather than supplied FK values.

## Planning Handoff

**Confirmed decisions**

- The target model defines relationships; each project explicitly selects `public_id` where its source already supplies target ids.
- Direct `public_id` FK values are an output exception for change-request packages only. Core project FK links continue to carry local `system_id` values, and direct-ID declarations create no Core project link or dependency. Update `AGENTS.md` and `src/AGENTS.md` to state this distinction.
- The ingester receives the resolved value-source map in `IngesterConfig.extra`; saved-project callers derive it from the project, and standalone callers may provide it directly.
- The default remains `system_id`. A direct-ID declaration never invokes a Core FK join or reinterprets a local ID by inference.
- Direct IDs must name rows already present in the target database. Lookup is mandatory for packaged values during validation and ingestion; missing lookup fails closed.
- The first delivery supports integer target public IDs and direct FKs only. `via` and non-integer targets are rejected.
- Globally required target entities remain required. Direct mode waives only the need for a helper entity and link for that relationship.

**Constraints and validation to preserve**

- Preserve existing Core link behavior, default-path diagnostics, `required_when` insert timing, and its exclusivity with `required`.
- Make direct-mode conformance consistent across direct-FK, induced-entity, globally-required-entity, and no-orphan-facts checks.
- Validate target existence in `validate_tables()` and `ingest_tables()` before accepting a package; saved-project service calls must exercise both methods. Retain database constraints at deployment.
- Keep the default scaffold and shared target-model interpretation unchanged for existing projects.
- Record the direct-ID declaration in the package manifest; do not create artificial mapping-sidecar links.

There are no blocking design questions for phase planning. The pilot measures the adoption assumption; non-integer IDs and bridge FKs need separate decisions if requested later.

## Final Recommendation

Add an explicit per-project FK value-source declaration for direct target ids. Keep the target model as the relationship authority and preserve local `system_id` links by default. Require a target database existence check before a direct-ID change request passes validation or package acceptance.
