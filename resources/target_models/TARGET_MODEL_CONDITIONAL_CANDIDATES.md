# Target Model Conditional Foreign Key Candidates

**Model scanned:** [sead_standard_model.yml](sead_standard_model.yml)
**Feature:** `foreign_keys[].required_when: {has_new_rows: <source entity>}`
**Generated:** 2026-10-14, by parsing the model with `src.target_model.models.TargetModel` and applying the rules in `src/target_model/spec_validator.py` and [Target Model Guide](../../docs/TARGET_MODEL_GUIDE.md).

This document lists every place in the shared SEAD superset model where the conditional
required feature can be applied. It is an inventory, not a decision record. Applying any
given pair is a separate choice that also depends on whether the source entity can end a
submission with zero inserted rows.

## Eligibility rule

A foreign key (FK) qualifies when it matches the shape of the applied
`location -> location_type` case. All three conditions must hold:

| # | Condition | Enforced by |
|---|-----------|-------------|
| 1 | The FK is direct; it does not declare `via` | `CONDITIONAL_FOREIGN_KEY_VIA_UNSUPPORTED` |
| 2 | The condition names the entity that owns the FK | `CONDITIONAL_FOREIGN_KEY_SOURCE_MISMATCH` |
| 3 | The target entity declares `public_id`, which supplies the FK column name | `CONDITIONAL_FOREIGN_KEY_TARGET_MISSING_PUBLIC_ID` |

The FK must also currently be `required: true`. A conditional FK cannot also declare
`required`, and the target entity's own `required: false` is needed to stop every
conforming project from including that entity.

## Summary

| Group | Count | Description |
|-------|-------|-------------|
| Already converted | 1 | `location -> location_type` |
| Tier 1 | 3 | Target `required: true`, one referrer: full three-edit pattern |
| Tier 2 | 16 | Target already `required: false`, one referrer: FK and column only |
| Tier 3 | 41 | Target `required: true`, multiple referrers: full pattern plus coordination |
| Tier 4 | 38 | Target already `required: false`, multiple referrers: FK and column only |
| **Total eligible** | **98** | Direct `required: true` FKs with a `public_id` on the target |

Scanning the same model also found 45 FKs already declared `required: false`, which need no
change, and 1 FK that declares `via`, which the feature cannot support.

Only 12 of the 98 eligible pairs are worth changing. The reason is that the condition is
evaluated on the entity that owns the FK, not on the entity it points at; see
[Recommendation](#recommendation).

## The three-edit pattern

The `location -> location_type` change made three edits. A candidate needs the same three
when its target entity is still `required: true`:

1. Remove `required: true` from the FK column, keeping `nullable: false`.
2. Replace the FK's `required: true` with `required_when: {has_new_rows: <source>}`.
3. Set the target entity's `required` to `false`.

When the target entity is already `required: false`, only edits 1 and 2 are needed.

## Tier 0: already converted

| Source (`has_new_rows`) | Target | FK column |
|---|---|---|
| `location` | `location_type` | `location_type_id` |

## Tier 1: exact structural analogues

Target entity is `required: true` and referenced by exactly one parent. These need the full
three-edit pattern and neither relax nor affect any other entity.

| Source (`has_new_rows`) | Owner mode | Target | FK column |
|---|---|---|---|
| `sample` | `allocate` | `sample_type` | `sample_type_id` |
| `dataset` | `allocate` | `master_dataset` | `master_set_id` |
| `submission` | `allocate` | `data_provider` | `data_provider_id` |

## Tier 2: private vocabulary, single referrer

Only the FK and the column carry an unconditional requirement; the target entity is already
`required: false`.

| Source                       | Owner mode  | Target                    | FK column                    |
|------------------------------|-------------|---------------------------|------------------------------|
| `sample_description`         | child       | `sample_description_type` | `sample_description_type_id` |
| `sample_colour`              | child       | `colour`                  | `colour_id`                  |
| `sample_location`            | child       | `sample_location_type`    | `sample_location_type_id`    |
| `sample_horizon`             | child       | `horizon`                 | `horizon_id`                 |
| `dataset`                    | allocate    | `project`                 | `project_id`                 |
| `submission`                 | allocate    | `submission_state`        | `submission_state_id`        |
| `submission_task`            | allocate    | `submission_task_type`    | `submission_task_type_id`    |
| `analysis_categorical_value` | child       | `value_type_item`         | `value_type_item_id`         |
| `abundance_modification`     | derived     | `modification_type`       | `modification_type_id`       |
| `abundance_ident_level`      | derived     | `identification_level`    | `identification_level_id`    |
| `ecocode_group`              | reconciled  | `ecocode_system`          | `ecocode_system_id`          |
| `ecocode_definition`         | reconciled  | `ecocode_group`           | `ecocode_group_id`           |
| `ecocode`                    | child       | `ecocode_definition`      | `ecocode_definition_id`      |
| `taxonomic_order`            | child       | `taxonomic_order_system`  | `taxonomic_order_system_id`  |
| `dataset_contact`            | derived     | `contact_type`            | `contact_type_id`            |
| `feature`                    | reconciled  | `feature_type`            | `feature_type_id`            |

## Tier 3: shared target, full pattern

The target entity is `required: true` but has multiple referrers. Converting one FK does not
relax the others. The target's own `required: true` must also become `false`, and each
remaining parent FK keeps its own choice of unconditional or conditional. Inconsistent
conversion leaves the target unconditionally required, so the relaxation yields nothing.

| Source                        | Owner mode | Target            | FK column            | Target referrers |
|-------------------------------|------------|-------------------|----------------------|------------------|
| `site_location`               | derived    | `site`            | `site_id`            | 4                |
| `site_location`               | derived    | `location`        | `location_id`        | 5                |
| `sample_group`                | allocate   | `site`            | `site_id`            | 4                |
| `sample_group`                | allocate   | `method`          | `method_id`          | 9                |
| `sample_group_coordinate`     | child      | `sample_group`    | `sample_group_id`    | 5                |
| `sample_group_dimension`      | child      | `sample_group`    | `sample_group_id`    | 5                |
| `sample_group_note`           | child      | `sample_group`    | `sample_group_id`    | 5                |
| `sample_group_reference`      | derived    | `sample_group`    | `sample_group_id`    | 5                |
| `sample_group_reference`      | derived    | `citation`        | `biblio_id`          | 9                |
| `sample`                      | allocate   | `sample_group`    | `sample_group_id`    | 5                |
| `sample_description`          | child      | `sample`          | `physical_sample_id` | 10               |
| `sample_colour`               | child      | `sample`          | `physical_sample_id` | 10               |
| `coordinate_method_dimension` | reconciled | `method`          | `method_id`          | 9                |
| `sample_coordinate`           | child      | `sample`          | `physical_sample_id` | 10               |
| `colour`                      | reconciled | `method`          | `method_id`          | 9                |
| `value_class`                 | reconciled | `method`          | `method_id`          | 9                |
| `sample_alt_ref`              | child      | `sample`          | `physical_sample_id` | 10               |
| `sample_dimension`            | child      | `sample`          | `physical_sample_id` | 10               |
| `sample_dimension`            | child      | `method`          | `method_id`          | 9                |
| `sample_location`             | child      | `sample`          | `physical_sample_id` | 10               |
| `sample_note`                 | child      | `sample`          | `physical_sample_id` | 10               |
| `sample_horizon`              | child      | `sample`          | `physical_sample_id` | 10               |
| `horizon`                     | reconciled | `method`          | `method_id`          | 9                |
| `dataset`                     | allocate   | `method`          | `method_id`          | 9                |
| `submission_task`             | allocate   | `contact`         | `contact_id`         | 4                |
| `analysis_entity`             | child      | `sample`          | `physical_sample_id` | 10               |
| `analysis_entity`             | child      | `dataset`         | `dataset_id`         | 2                |
| `analysis_value`              | child      | `analysis_entity` | `analysis_entity_id` | 4                |
| `abundance`                   | child      | `analysis_entity` | `analysis_entity_id` | 4                |
| `taxa_synonyms`               | child      | `citation`        | `biblio_id`          | 9                |
| `rdb_system`                  | reconciled | `citation`        | `biblio_id`          | 9                |
| `rdb_system`                  | reconciled | `location`        | `location_id`        | 5                |
| `rdb`                         | child      | `location`        | `location_id`        | 5                |
| `relative_dating`             | child      | `analysis_entity` | `analysis_entity_id` | 4                |
| `geochronology`               | child      | `analysis_entity` | `analysis_entity_id` | 4                |
| `dataset_contact`             | derived    | `dataset`         | `dataset_id`         | 2                |
| `dataset_contact`             | derived    | `contact`         | `contact_id`         | 4                |
| `site_property`               | child      | `site`            | `site_id`            | 4                |
| `site_natgridref`             | child      | `site`            | `site_id`            | 4                |
| `site_natgridref`             | child      | `method`          | `method_id`          | 9                |
| `sample_feature`              | derived    | `sample`          | `physical_sample_id` | 10               |

## Tier 4: shared target, FK and column only

The target entity is already `required: false`; only the FK and the column carry an
unconditional requirement.

| Source                        | Owner mode | Target                        | FK column                        |
|-------------------------------|------------|-------------------------------|----------------------------------|
| `sample_group_coordinate`     | child      | `coordinate_method_dimension` | `coordinate_method_dimension_id` |
| `sample_group_dimension`      | child      | `dimension`                   | `dimension_id`                   |
| `coordinate_method_dimension` | reconciled | `dimension`                   | `dimension_id`                   |
| `sample_coordinate`           | child      | `coordinate_method_dimension` | `coordinate_method_dimension_id` |
| `value_qualifier_symbol`      | reconciled | `value_qualifier`             | `qualifier_id`                   |
| `value_type_item`             | child      | `value_type`                  | `value_type_id`                  |
| `value_class`                 | reconciled | `value_type`                  | `value_type_id`                  |
| `sample_alt_ref`              | child      | `alt_ref_type`                | `alt_ref_type_id`                |
| `sample_dimension`            | child      | `dimension`                   | `dimension_id`                   |
| `dataset`                     | allocate   | `submission`                  | `submission_id`                  |
| `dataset`                     | allocate   | `data_type`                   | `data_type_id`                   |
| `submission_task`             | allocate   | `submission`                  | `submission_id`                  |
| `analysis_value`              | child      | `value_class`                 | `value_class_id`                 |
| `analysis_note`               | child      | `analysis_value`              | `analysis_value_id`              |
| `analysis_identifier`         | child      | `analysis_value`              | `analysis_value_id`              |
| `analysis_boolean_value`      | child      | `analysis_value`              | `analysis_value_id`              |
| `analysis_categorical_value`  | child      | `analysis_value`              | `analysis_value_id`              |
| `analysis_integer_value`      | child      | `analysis_value`              | `analysis_value_id`              |
| `analysis_integer_range`      | child      | `analysis_value`              | `analysis_value_id`              |
| `analysis_numerical_value`    | child      | `analysis_value`              | `analysis_value_id`              |
| `analysis_numerical_range`    | child      | `analysis_value`              | `analysis_value_id`              |
| `analysis_taxon_count`        | child      | `analysis_value`              | `analysis_value_id`              |
| `analysis_taxon_count`        | child      | `taxa_tree_master`            | `taxon_id`                       |
| `analysis_value_dimension`    | child      | `analysis_value`              | `analysis_value_id`              |
| `analysis_value_dimension`    | child      | `dimension`                   | `dimension_id`                   |
| `analysis_dating_range`       | child      | `analysis_value`              | `analysis_value_id`              |
| `abundance`                   | child      | `taxa_tree_master`            | `taxon_id`                       |
| `abundance_property`          | child      | `property_type`               | `property_type_id`               |
| `abundance_ident_level`       | derived    | `abundance`                   | `abundance_id`                   |
| `taxa_common_names`           | child      | `taxa_tree_master`            | `taxon_id`                       |
| `taxa_measured_attributes`    | child      | `taxa_tree_master`            | `taxon_id`                       |
| `rdb`                         | child      | `taxa_tree_master`            | `taxon_id`                       |
| `ecocode`                     | child      | `taxa_tree_master`            | `taxon_id`                       |
| `taxonomic_order`             | child      | `taxa_tree_master`            | `taxon_id`                       |
| `feature_property`            | child      | `feature`                     | `feature_id`                     |
| `site_property`               | child      | `property_type`               | `property_type_id`               |
| `feature_property`            | child      | `property_type`               | `property_type_id`               |
| `sample_feature`              | derived    | `feature`                     | `feature_id`                     |

## Excluded by the implementation contract

`site -> location` is semantically the closest sibling to the applied case, because both
anchor `location`. It declares `via: site_location`, and the strict contract rejects
`required_when` on a bridge FK. It cannot use this feature without a model change. It is also
the only `via` FK in the model.

The remaining FKs are excluded because they are already `required: false`, so they carry no
unconditional requirement to relax.

## How to prioritise

See [Recommendation](#recommendation) for the verdict. In short:

- Filter by owner mode first. Only an owner that reconciles can end a submission with zero
  inserted rows, so only those pairs benefit. Tier grouping alone does not decide value: most
  Tier 1 pairs have an owner that allocates and are not worth changing.
- Fix Group A directly. It needs two edits per pair and no coordination with other entities.
- Treat Group B as one decision per shared target, because relaxing the target also loosens
  the requirement for every other referrer.
- Leave the remaining pairs alone. Their condition would be permanently true, so the change
  weakens a working check for no gain.

## Recommendation

Only 12 of the 98 eligible pairs are worth changing. The reason is that `required_when` is
evaluated on the entity that owns the FK, not on the entity it points at.

### Deciding rule

The condition becomes true only when final reconciliation selects at least one row of the
named entity for insert. The change therefore only helps when the owner can end a submission
with zero inserted rows while a project that omits the target would still be rejected today.
The owner's effective identity mode, resolved by `src/target_model/effective_identity.py`,
decides this.

| Owner effective mode | Typical roles | Can the owner insert zero rows? | Verdict |
|---|---|---|---|
| `allocate` | tracked facts: `sample`, `dataset`, `submission`, `analysis_entity`, `sample_group` | Only if the change request produces no rows at all | Unreliable; the condition is usually always true |
| `derive` | bridges: `site_location`, `dataset_contact`, `sample_feature` | No; a bridge row is written with its parents | No benefit |
| child | aggregate children: `sample_description`, `analysis_value`, `site_property` | Only if the aggregate root is itself matched | Helps under reconciled roots only |
| `reconciled` | lookups and classifiers: `feature`, `colour`, `value_class`, `method`, `location` | Yes; matching existing rows is the normal path | Worth fixing |

### Worth fixing

Group A is 6 pairs. The target is already `required: false`, so only the FK and the column
change: two edits each, with no coordination.

| Source (`has_new_rows`)       | Target            | Tier |
|-------------------------------|-------------------|------|
| `feature`                     | `feature_type`    | 2    |
| `ecocode_group`               | `ecocode_system`  | 2    |
| `ecocode_definition`          | `ecocode_group`   | 2    |
| `coordinate_method_dimension` | `dimension`       | 4    |
| `value_class`                 | `value_type`      | 4    |
| `value_qualifier_symbol`      | `value_qualifier` | 4    |

Group B is 6 pairs. The owner reconciles, but the target is shared and `required: true`.
These are worth fixing only as one coordinated decision per target, because relaxing the
target also loosens the requirement for every other referrer.

| Source                        | Target     | Target referrers |
|-------------------------------|------------|------------------|
| `coordinate_method_dimension` | `method`   | 9                |
| `colour`                      | `method`   | 9                |
| `value_class`                 | `method`   | 9                |
| `horizon`                     | `method`   | 9                |
| `rdb_system`                  | `citation` | 9                |
| `rdb_system`                  | `location` | 5                |

### Not worth fixing

The remaining 86 pairs have an owner that allocates, derives, or is a child of an allocated
fact, so the condition is permanently true. They keep the same validation outcome while
making the model harder to read. Two of the effects are worse than neutral:

- An always-true condition weakens the check for no gain. The unconditional `required: true`
  column rule is what rejects a row that lacks an FK value, and moving it to a condition that
  never turns off does not strengthen anything.
- Setting the column's `required` flag to false also removes the column from
  `required_fk_columns` in `ingesters/sead_change_request/target_projection.py`, which
  currently exempts it from the generic required-column check. The pair then falls through to
  the conditional projection path instead.

### Check before acting

1. Confirm the owner can ever be inserted. `colour`, `horizon`, `feature`, `value_class`,
   `coordinate_method_dimension`, `value_qualifier_symbol`, `ecocode_group`, and
   `ecocode_definition` are plain lookups and classifiers, not `lookup-extensible`. Under
   `reconcile-exact` or `lookup-only`, unmatched rows are blocked rather than inserted, so the
   condition is effectively always false. That removes the requirement rather than making it
   conditional. This is the correct outcome for a SEAD-owned vocabulary, but it should be a
   deliberate statement. Only `lookup-extensible` owners (`method`, `taxa_tree_master`,
   `abundance_element`) give the literal required-only-when-we-create behaviour, and none of
   them owns a required FK.
2. Re-run validation after each change. `tests/target_model/test_spec_files.py` asserts that
   the superset spec produces no issues, and `tests/model/test_target_model_conformance.py`
   covers the conditional conformance path. Note that
   `test_core_conformance_reports_known_gaps_for_full_arbodat_project` and
   `test_core_conformance_current_corpus_issue_families_are_stable` already fail against the
   unmodified `resources/target_models/sead_standard_model.yml`, and read that file rather
   than the superset file, so they neither cover nor are affected by edits here.

### Feature gap

`site -> location` is the closest semantic sibling to the applied case, because both anchor
`location`, and its owner `site` reconciles, so it would otherwise qualify. It declares
`via: site_location`, and the strict contract rejects `required_when` on a bridge FK. Using
this case requires changing the feature to accept `required_when` with `via`, not changing
the model.

## Regenerating this list

`resources/target_models` is not on any import path, so run the scan from the repository root
with an inline script.

```bash
.venv/bin/python - <<'PY'
import yaml
from pathlib import Path
from src.target_model.models import TargetModel

spec = TargetModel.model_validate(
    yaml.safe_load(Path("resources/target_models/sead_sta_model.yml").read_text())
)
for name, ent in spec.entities.items():
    for fk in ent.foreign_keys:
        if fk.via or fk.required_when is not None or not fk.required:
            continue
        tgt = spec.entities.get(fk.entity)
        print(f"{name} -> {fk.entity} ({tgt.public_id if tgt else None}) [target required={tgt.required if tgt else None}]")
PY
```

## References

- [Target Model Guide](../../docs/TARGET_MODEL_GUIDE.md)
- [Target Model Schema Reference](../../docs/TARGET_MODEL_SCHEMA_REFERENCE.md)
- [Conditional Target Model Requirements](../../docs/proposals/done/CONDITIONAL_TARGET_MODEL_REQUIREMENTS/CONDITIONAL_TARGET_MODEL_REQUIREMENTS.md)
- [Target Model Review 2026-10-13](TARGET_MODEL_REVIEW_20261013.md)
