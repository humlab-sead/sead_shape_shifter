# Conditional Target Model Requirements

## Status

**Proposed change.** Scope: target-model FK requirements and their evaluation for SEAD change requests. Goal: require a lookup, link, and FK value when reconciled rows will be inserted.

## Summary

Add `required_when` to an existing `foreign_keys` entry. `has_new_rows` becomes true only after reconciliation selects at least one source row for insertion. The conditional FK then requires the lookup entity, declared link, and FK column and values on inserted rows. This expresses the `location` → `location_type` rule in one place.

## Problem

The SEAD target model currently marks `location_type`, the FK from `location`, and `location_type_id` as unconditionally required. A submission whose locations all reconcile to existing rows can therefore receive requirement errors even though it inserts no location. The [superset model](../../resources/target_models/sead_superset_model.yml) contains a commented conditional-FK example, but the format cannot parse or enforce it.

## Scope

- A condition on an existing target-model FK that depends on the source entity's reconciled rows selected for insertion.
- The resulting requirement for the FK column and values on those inserted rows.
- Consistent handling in project conformance, change-request validation, schema tooling, and target-model documentation.
- Applying the rule to `location` → `location_type` once the format supports it.

## Non-Goals

- A general expression language or conditions based on arbitrary entities, source rows, or database queries.
- New relationship declarations separate from `foreign_keys`.
- Changing the meaning of existing unconditional `required: true` fields or unrelated column requirements.

## Current Behavior

The [target-model schema](../../src/target_model/models.py) accepts only boolean `required` values for entities, columns, and FKs and rejects unknown fields. [Project conformance](../../src/target_model/conformance.py) checks required columns and links using project configuration; it has no reconciliation result. [Data conformance](../../src/target_model/data_validators.py) checks nulls in `required: true`, non-nullable columns on produced rows. [Target projection](../../ingesters/sead_change_request/target_projection.py) also checks required columns and FKs before the [package builder](../../ingesters/sead_change_request/package_builder.py) selects insert rows. The older SEAD [`Submission.has_new_rows()`](../../ingesters/sead/submission.py) checks for missing PK values before reconciliation, so it cannot determine this condition.

## Proposed Design

Declare the condition on the FK it governs:

```yaml
entities:
  location:
    columns:
      location_type_id:
        type: integer
        nullable: false
    foreign_keys:
      - entity: location_type
        required_when:
          has_new_rows: location
  location_type:
    required: false
```

`has_new_rows` is true when final reconciliation selects at least one row of the named entity for `INSERT`. Existing matches, updates, and blocked rows do not count. In this first version, the named entity must own the FK, and the FK target must declare `public_id` so its column can be identified. An FK may declare either `required: true/false` or `required_when`, not both. The target-model specification validator rejects malformed or conflicting conditions.

When the condition is true, the project must include `location_type` and declare the link; each inserted `location` row must have a non-null, resolvable `location_type_id`. The column name comes from `location_type.public_id`. `nullable: false` still describes the target row constraint. Omit `location_type_id.required: true` in this example: that flag currently requires the column in every project containing `location` and checks values before reconciliation. Also set `location_type.required: false`; otherwise the lookup remains unconditionally required. Other target-model rules still apply when the condition is false.

Project-only conformance cannot determine the reconciled insert decision. It reports the conditional rule as awaiting reconciliation, without treating it as passed or failed. The change-request path evaluates the rule after final reconciliation and reports an error before accepting a package that violates it. Earlier data and projection checks must not enforce this conditional FK on provisional or matched rows. FK projection still resolves any link values actually used by inserted or updated rows.

## Alternatives Considered

- **A separate relationships or requirements section:** duplicates the FK declaration and permits conflicting rules.
- **Trigger on the presence of a `location` entity:** rejects projects whose submitted locations all match existing rows.
- **Keep `location_type_id.required: true`:** retains the unconditional column check and can reject a submission that inserts no location.
- **Repeat the condition on the column:** creates two places that must agree about the same FK requirement.
- **Keep static `required: true`:** cannot express the stated submission-dependent rule.

## Risks And Tradeoffs

Project validation alone cannot give a final answer for conditional rules; its result must say that reconciliation is needed. Current data and projection checks inspect rows that may later match existing records. Their conditional FK checks must use final insert decisions to avoid false positives. Existing unconditional column checks remain unchanged.

## Testing And Validation

Check valid and invalid YAML, project-only deferred results, and change requests with zero or one reconciled `location` row selected for insertion. Include a row that appears new before reconciliation but matches an existing location afterward. Cover missing lookup entities, missing declared links, missing or unresolved FK values, updates, and unchanged behavior for static `required` rules. Confirm the schema reference, editor schema, guide, and active superset example describe the same rule.

## Acceptance Criteria

- `P-AC-1` The strict target-model schema accepts `has_new_rows: location` and rejects an unknown or non-owning entity, a target without `public_id`, or `required` combined with `required_when` on the same FK.
- `P-AC-2` Project-only conformance identifies the conditional rule as awaiting reconciliation; it does not emit missing-lookup, missing-link, or missing-`location_type_id` errors from this conditional requirement.
- `P-AC-3` When reconciliation selects no `location` rows for insertion, this rule does not fail the submission, including when provisional rows match existing locations.
- `P-AC-4` For a reconciled `location` insert, validation rejects a missing `location_type` entity or project link and a missing, null, or unresolved `location_type_id` before package acceptance.
- `P-AC-5` The target-model guide, schema reference, editor schema, and SEAD superset model use the supported syntax and agree on when the condition applies.
- `P-AC-6` Existing unconditional entity, column, and FK requirements retain their current validation results.

## Final Recommendation

Add `required_when: {has_new_rows: location}` to the FK specification and evaluate it only after reconciliation selects insert rows. The conditional FK supplies the requirement for its column and lookup, so the example omits their unconditional `required: true` flags.
