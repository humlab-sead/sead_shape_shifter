# Direct Target-Id Foreign Keys

## Status

- Proposed feature / change request
- Scope: target-model FK format, core conformance, SEAD change-request projection
- Goal: let a foreign key declare that its values are already target public ids, so a project no longer has to declare an entity that exists only to translate `system_id` to `public_id`

## Summary

Add an optional `value_source` attribute to a target-model foreign key. `system_id` remains the default and keeps current behavior. `public_id` states that the FK values are already target public ids, so the project need not declare the referenced entity and the values pass into the change request unchanged.

This removes entities that exist only to translate ids. The user is currently forced to declare and populate such an entity even when the source already carries SEAD ids, and no other entity consumes its attributes.

Related documents:

- [Target Model Guide](../../docs/TARGET_MODEL_GUIDE.md)
- [Conditional Target Model Requirements](done/CONDITIONAL_TARGET_MODEL_REQUIREMENTS/CONDITIONAL_TARGET_MODEL_REQUIREMENTS.md) — the `required_when` rule this attribute composes with
- [Target Model Conditional FK Candidates](../../resources/target_models/TARGET_MODEL_CONDITIONAL_CANDIDATES.md) — candidate inventory, including the `site -> location` gap
- [Advanced FK Validation Modes](future/ADVANCED_FK_VALIDATION_MODES.md), [FK Null-Key Policy Model](future/FK_NULL_KEY_POLICY_MODEL.md) — related deferred work

## Problem

Shape Shifter requires every relationship to use local `system_id` values. That rule is deliberate and documented, but it forces work when a source already supplies target ids.

Concretely: a source column holds SEAD `location_type_id` values. To submit it, the user must still declare a `location_type` entity with `public_id: location_type_id`, provide its rows, satisfy conformance, and link `location_type_id` to `location_type.system_id`. The join performs one conversion: replace each value with the `system_id` of the row carrying that value. When the value is already the SEAD id, the entity carries no information the source did not already have.

The cost is not only configuration lines:

- Project conformance rejects a project that omits the entity, even though the project needs no new rows.
- Identity planning must reconcile or allocate the entity, producing review work with no decision to make.
- Readers cannot tell whether the entity holds real content or exists only for id translation.

This appears whenever a source is already keyed by the target system. Taxonomies, controlled vocabularies, and re-submissions of existing records all hit it.

## Scope

- A declared, optional `value_source` attribute on a target-model foreign key.
- Project conformance behavior when `value_source: public_id` is declared.
- Change-request projection behavior for values supplied as public ids.
- Validation rules for the new attribute and for unresolvable values.
- Documentation updates for the guide, scaffoldable schema reference, and editor schema.

## Non-Goals

- An inferred rule based on whether the referenced entity is declared. The attribute is always explicit; see [Alternatives Considered](#alternatives-considered).
- Removing or weakening the `system_id` default. Existing projects keep current behavior.
- Synthesized bridge entities, column-level conditions, or generalized `required_when`. These attack the same root cause but are separate decisions; see [Related Constructs Not In Scope](#related-constructs-not-in-scope).
- Per-row or mixed interpretation inside one FK column.
- Reconciliation by business key. `keys` behavior is unchanged.

## Current Behavior

Verified against the repository:

- A foreign key column is named after the referenced entity's `public_id` but contains that entity's local `system_id`. `ForeignKeyConfig.generate_link_setup` builds `default_renames = {remote_cfg.system_id: remote_cfg.public_id}` (`src/model.py`).
- The rule is documented as a critical principle: FK columns always contain the parent's `system_id`, never external ids, and external ids are applied as a decoration step through the mapping sidecar (`docs/CONFIGURATION_GUIDE.md`).
- Identity resolution already reads a resolved target id directly from a `public_id` column for rows planned as `REFERENCE_EXISTING` or `UPDATE_EXISTING_CANDIDATE` (`ingesters/sead_change_request/identity_resolution.py`). The "value is already a target id" path therefore exists internally, but only for an entity the project declared.
- Foreign-key projection rewrites FK values through a local map: `_build_remote_id_mapping(remote_table.frame["system_id"], remote_table.resolved_target_ids)` (`ingesters/sead_change_request/target_projection.py`). Values are interpreted as the remote entity's `system_id`.
- The change-request projection pass already receives the target model and iterates `entity_spec.foreign_keys`, so target-model FK attributes are available at that point (`project_target_ids`).
- Project conformance requires the FK target entity to be present, or reachable through the project's target-facing FK graph, and otherwise emits `MISSING_REQUIRED_FOREIGN_KEY_TARGET` (`src/target_model/conformance.py`).
- The strict target-model validator rejects `required_when` combined with `via`, and rejects a conditional FK whose target declares no `public_id` (`src/target_model/spec_validator.py`).

Assumption: sources that already carry SEAD ids are common enough to justify this. The candidate inventory lists 98 eligible FKs, but the count of projects that would drop an entity is not measured. Measuring it is part of validation.

## Proposed Design

### Declaration

Add `value_source` to the target-model `foreign_keys` entry:

```yaml
entities:
  location:
    foreign_keys:
      - entity: location_type
        value_source: public_id
```

Allowed values are `system_id` (default) and `public_id`. Omitting the attribute keeps current behavior.

Declaring it in the target model, not the project, keeps one authority for relationship requirements. The change-request projection pass and the conformance validators already read target-model FKs, and `required_when` established this pattern.

### Behavior when `value_source: public_id`

1. The FK column name still comes from the target entity's `public_id`. The target entity must exist in the target model and declare `public_id`; otherwise validation fails. The target model describes the destination schema, so the entity remains defined even when a project omits it.
2. Project conformance does not require the project to declare the target entity or a link to it. It reports an informational issue that the values are resolved at change-request time, matching the existing `CONDITIONAL_FK_AWAITING_RECONCILIATION` reporting style.
3. Change-request projection treats values in that column as final target ids. It does not rewrite them through the local `system_id` map.
4. Each non-null value must resolve to a known target id. A value that does not resolve emits a diagnostic naming the entity and column and fails before package acceptance. There is no fallback to `system_id` interpretation.
5. `nullable: false` keeps its meaning. A required column with a missing value still fails, under the same rule as today.
6. The attribute composes with `required_when`: inserted rows still require a resolvable value, and the condition still decides when that requirement applies.

### Validation rules

- An unknown `value_source` value is rejected.
- A target entity without `public_id` is rejected for a `value_source: public_id` FK.
- `value_source: public_id` combined with `via` is rejected until bridge behavior is decided; see [Open Questions](#open-questions).
- The attribute is not allowed to appear alongside a conflicting declaration on the same FK.

### Dtypes and provenance

Target ids are not always integers; `data_provider_uuid` is a UUID and several targets use strings. The implementation must not cast to `Int64` unconditionally; it must use the target column type.

Values supplied as public ids come from the source verbatim and are not recorded by reconciliation. The change request should record which values were supplied as ids so a reviewer can trace them, and the mapping sidecar needs a decision about whether it carries a parallel record.

### Related Constructs Not In Scope

`value_source` addresses one instance of a broader pattern: the user declares structure that exists only to satisfy the tool. Three other constructs attack the same root cause and should be considered separately, not folded into this decision.

| Construct | What it would remove |
|---|---|
| Synthesized bridges, for example a declared `site -> location through site_location` relationship | A declared bridge entity plus two FKs plus its conformance obligations |
| `required_when` on columns, not only FKs | Over-required columns such as `location_name` |
| Generalized `required_when` (accept `via`, allow several sources) | The `site -> location` gap, which is currently rejected by the strict contract |

## Alternatives Considered

- **Infer from whether the entity is declared.** The legacy behavior: a declared `B` makes `A.b` a `system_id`, and an undeclared `B` makes `A.b` a `public_id`. Rejected for three reasons. Local `system_id` values are small sequential integers and SEAD public ids are larger integers, so the wrong direction produces plausible IDs and a wrong foreign key in the destination rather than an error. Declaring a previously absent entity would silently reinterpret existing values with no diff. It also replaces a documented invariant with a mode switch that a reader cannot see.
- **Declare on the entity rather than the FK.** Coarser. One target can be referenced by FKs that supply different value kinds, and an entity-level flag cannot express that.
- **Reuse a `public_id_generation`-style opt-in on the target entity.** Wrong direction. That flag reserves new ids from a sequence; this attribute accepts ids that already exist.
- **Rely on reconciliation to match by key.** Does not help. The user still declares the entity, and matching by key is a different operation from accepting a known id.

## Risks And Tradeoffs

- **Silent wrong values.** A user could declare `public_id` and supply local `system_id` values. Mitigation: validate resolution against known target ids where a lookup is available, and fail loudly rather than falling back.
- **Contract weakening.** Allowing public-id values lets a project skip a required entity. Keeping the declaration in the target model preserves one authority, and the change-request validation still rejects unresolvable values.
- **Non-integer ids.** UUID and string targets need type-aware handling; the existing integer cast cannot be reused as is.
- **Provenance and audit.** Bypassed values are not recorded by reconciliation. Without an explicit record, review cannot tell a supplied id from a reconciled one.
- **Interaction surface.** The attribute touches the validator, conformance, and projection, and composes with `required_when`. Sequencing and regression coverage matter more than the size of the change.

## Testing And Validation

- Target-model validation: accepts `value_source` values `system_id` and `public_id`; rejects an unknown value, a target without `public_id`, and `public_id` combined with `via`.
- Project conformance: a project that omits the target entity passes and reports an informational issue; a project that declares the entity and uses `system_id` values is unchanged.
- Change-request projection: supplied ids pass through unchanged; an unresolvable value fails with a diagnostic naming the entity and column; a missing value in a `nullable: false` column fails; a UUID target works.
- Composition: `value_source: public_id` with `required_when` behaves correctly for zero-insert and insert cases.
- Regression: existing suites pass unchanged — `tests/target_model/`, `tests/model/test_target_model_conformance.py`, `backend/tests/ingesters/`. Note that `test_core_conformance_reports_known_gaps_for_full_arbodat_project` and `test_core_conformance_current_corpus_issue_families_are_stable` already fail against the unmodified `resources/target_models/sead_standard_model.yml` and are not caused by this work.
- End-to-end: validate one change request against a disposable PostgreSQL instance, following the approach used by prior target-model work.
- Measure the assumption: count the project entities dropped by a pilot project to confirm the attribute earns its place.

## Acceptance Criteria

- `P-AC-1` A target-model FK accepts `value_source` with values `system_id` and `public_id`; omitting it behaves exactly as `system_id`.
- `P-AC-2` An unknown `value_source` value, a `value_source: public_id` target without `public_id`, and `value_source: public_id` combined with `via` are each rejected with a distinct machine-readable code.
- `P-AC-3` When the target-model FK declares `value_source: public_id`, a project may omit the target entity and any link to it, and project-only conformance reports an informational awaiting-resolution issue instead of a missing-target error.
- `P-AC-4` With `value_source: public_id`, FK values reach the change request unchanged and are not rewritten through the local `system_id` map.
- `P-AC-5` A non-null `value_source: public_id` value that does not resolve to a target id fails before package acceptance with a diagnostic naming the entity and column.
- `P-AC-6` `nullable: false` still fails on a missing value, and `value_source: public_id` composes with `required_when` without changing that rule's insert-based timing.
- `P-AC-7` A UUID and a string FK target are handled without an integer cast, and their values resolve correctly.
- `P-AC-8` Existing projects that declare `system_id` FKs produce identical results; the suites in [Testing And Validation](#testing-and-validation) pass.
- `P-AC-9` The target-model guide, scaffoldable schema reference, and editor schema describe the attribute, its default, and its conformance effect.

## Planning Handoff

**Confirmed decisions**

- The attribute is explicit, never inferred from entity presence.
- It is declared per FK in the target model, which stays the single authority for relationship requirements.
- The default is `system_id` and preserves current behavior exactly.
- Values declared as public ids pass through unchanged; unresolvable values fail loudly with no fallback.
- The target entity remains defined in the target model and must declare `public_id`.

**Constraints and behavior to preserve**

- The `system_id` FK invariant and the `public_id` column-naming rule for the default path.
- Existing diagnostic codes and their messages for the default path.
- `required_when` insert-based timing and its exclusivity with `required`.
- Core project linking stays unchanged for the default path; this attribute is consumed at the target-model and change-request layers.
- No silent substitution between the two interpretations at any point.

**Expected validation outcomes**

- Target-model validation and project conformance produce the outcomes in `P-AC-1` to `P-AC-3`.
- The change-request path produces the outcomes in `P-AC-4` to `P-AC-7`.
- Regression suites stay green, except the two known pre-existing conformance failures.

**Open questions and the phase that must resolve each**

- Whether `value_source: public_id` may combine with `via`, and if so where the value lives when the column is on a bridge — resolve before finalizing the validator, Phase 1.
- How non-integer and UUID target ids are typed and validated — resolve in the phase that implements projection, Phase 2.
- How provenance for supplied ids is recorded, and whether the mapping sidecar needs a parallel record — resolve before the pilot, Phase 2.
- Whether the project may declare the attribute when the target model does not, or whether the target model is the only authority — resolve in Phase 1.

## Open Questions

- Should the attribute name be `value_source`, or does an existing project term fit better (for example one aligned with `identity_tracking` or `public_id_generation`)?
- Do any current sources need both interpretations within one column, which the design deliberately excludes?

## Final Recommendation

Add an explicit, opt-in `value_source: public_id` attribute on target-model foreign keys. It lets a project stop declaring entities that exist only to translate `system_id` to `public_id`, keeps the `system_id` default unchanged, and fails loudly instead of reinterpreting values by inference. Keep the related constructs — synthesized bridges, column-level conditions, and generalized `required_when` — as separate decisions under the same root cause.
