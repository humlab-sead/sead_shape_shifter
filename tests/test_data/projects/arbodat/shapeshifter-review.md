# ArboDat Configuration Review

**Reviewed:** 2026-10-26
**Project configuration:** [shapeshifter.yml](./shapeshifter.yml)
**Target model:** [sead_standard_model.yml](../../../../resources/target_models/sead_standard_model.yml)

## Summary

The target-model reference resolved during validation. A conformance-only run reproduced the 10 reported conformance issues. Most are missing or mismatched foreign-key declarations; several required target columns are missing because their foreign keys are not declared.

This review records findings from the supplied `--workflow all` output and a conformance-only rerun. It does not change the project configuration. Data warnings from the supplied run may depend on the configured databases and source rows.

## Conformance findings

|     Status     | Entity                     | Finding and cause                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| :-------------: | -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **FIXED** | `relative_dating`        | The project declares `public_id: relative_age_id`, while the target model expects `relative_date_id`. If this is the intended target model, update the project declaration to match.                                                                                                                                                                                                                                                                                                                     |
|      FIXED      | `dataset`                | The target requires foreign-key relationships to `submission` and `data_type`. The project sets `submission_id` and `data_type_id` as extra-column constants, but constants do not declare those relationships. The project also has no `data_type` entity.                                                                                                                                                                                                                                        |
|                | `analysis_entity`        | The target requires a relationship to `dataset` and the resulting `dataset_id` column. Neither is declared. `dataset` currently uses `source: analysis_entity`, so adding a reverse relationship creates a dependency cycle. Derive datasets independently before linking analysis entities, or deliberately use a deferred FK if the cycle is required.                                                                                                                                             |
|                | `abundance_modification` | The target requires an FK to `abundance`, but this entity only declares its FK to `modification_type`. Using `source: abundance` does not declare the target relationship.                                                                                                                                                                                                                                                                                                                             |
|                | `abundance_property`     | The target requires an FK to `abundance`, but this entity only declares its FK to `property_type`. Using `source: abundance` does not declare the target relationship.                                                                                                                                                                                                                                                                                                                                 |
|                | `relative_dating`        | The target requires an FK to `analysis_entity` and the resulting `analysis_entity_id` column. The project instead links to `tmp_analysis_entity_for_relative_dating`, which links to `sample`, not `analysis_entity`. Decide how a dating row maps to an analysis entity before adding this FK; the helper uses sample-level keys, while analysis entities have a finer grain.                                                                                                                     |
|                | `location`               | The target FK to `location_type` is conditional on new location rows. The finding says reconciliation is needed to determine whether the FK applies; it does not establish that the YAML relationship is wrong. In the current conformance code, the issue is created with `info` severity but later receives the FK validator's default `error` severity ([conformance.py](../../../../src/target_model/conformance.py#L482), [severity assignment](../../../../src/target_model/conformance.py#L875)). |

The missing `dataset_id` and `analysis_entity_id` findings follow from the missing FK declarations. They are not necessarily separate columns to add manually.

## Data and structural warnings

### Foreign-key value mismatches

- **`method` → `method_group`:** Every configured `method_group_id` value is null, causing the all-null FK warning. Populate valid local IDs if this mapping is known; otherwise assess whether the optional FK should remain.
- **`sample_group` → `method`:** The configured `method_id: 0` does not match a configured method `system_id`. Use a valid local method ID, or represent the absence according to the FK's null-key policy.
- **`dataset_submission` → `dataset_submission_type`:** The child value is `1`, but the FK joins to `dataset_submission_type_id`, whose configured value is `5`; the parent's `system_id` is `1`. If `1` is intended as the local ID, join to `system_id`.
- **`submission` → `data_provider`:** The submission row uses `DP_CODE`, while project metadata and the fixed provider row use `arbodat-pilot`.
- **`ecocode` → `ecocode_definition`:** The child value comes from `Ökogruppe`, but the FK joins it to the parent's generated `system_id`. The parent business key is `Ökogruppe`; match on that key so Shape Shifter can produce the local FK.

### Empty or missing data

- **`citation`:** The fixed entity has `values: []`, which explains both the structural empty-values warning and empty result.
- **`dating` and `site_natural_region`:** Both are empty after processing. Check source rows and FK matches; the output alone does not distinguish an empty source from rows removed during linking.
- **`dating_period`:** All values in the `ChronoDat` FK column are null in the processed data.
- **`relative_ages`:** The structural warning is triggered because a non-fixed entity declares `system_id` in `columns`. The workbook currently contains 17 positive, unique integer IDs from 1 through 17. Keep them if they are intentional; omit the configured field only if the loader should generate new IDs.

### Processing warnings

- **`contact__append_0`:** The contact entity requests `contact_name` and `contact_type`, but the SQL append selects `[BotBest]` and a `"BotBest"` literal without mapping them to those names. Alias or map the append output columns.
- **SQL entities with unnest:** The `NOT IMPLEMENTED VALIDATION` messages mean the SQL loader skips column validation for unnesting. They do not by themselves establish a configuration error.
- **Join row-count changes:** The logged reductions show that linking changed the number of rows. Inner joins remove unmatched rows; inspect the source keys and parent matches before changing join types, since a left join can retain rows with null FKs.
- **`dataset_contacts` duplicate handling:** The duplicate-removal step requests `contact_id` before it is available and is logged as delayed. Check that the delayed step runs after the contact FK is produced.

## Validation

Conformance-only command:

```bash
rtk uv run python scripts/validate_project.py tests/test_data/projects/arbodat/shapeshifter.yml --workflow conformance --log-level ERROR
```

The run reproduced the reported conformance findings. The broader data warnings above are from the supplied `--workflow all` output and may require access to the configured source databases to investigate further.
