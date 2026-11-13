# Target Model Coverage Review

## Status

- Closed review record, frozen 2026-11-12.
- Scope: the coverage and completeness state of `resources/target_models/sead_standard_model.yml` (version 2.8.0), and the close-out of the three earlier target-model working documents.
- Companion to the [Target Model Project Requirements](TARGET_MODEL_PROJECT_REQUIREMENTS.md) proposal, which now carries the remaining decisions.

This document replaces three working documents that were closed on 2026-11-12. It records what they established and where the remaining work went. It is a snapshot, not a live tracker; refresh it only when a fresh measurement is taken.

## Closed documents

| Closed document | What it held | Remaining work now tracked in |
|---|---|---|
| [TARGET_MODEL_REVIEW.md](archive/TARGET_MODEL_REVIEW.md) | Entity-by-entity review, aggregate-child inventory, root-row rules, deployed ID-generator audit | Proposal sections "Complete the standard model" and "Support the model in Shape Shifter" |
| [TARGET_MODEL_MISSING_ENTITY_CANDIDATES.md](archive/TARGET_MODEL_MISSING_ENTITY_CANDIDATES.md) | Gap triage for tables with no model entity | Proposal section "Complete the standard model" |
| [TARGET_MODEL_CONDITIONAL_CANDIDATES.md](archive/TARGET_MODEL_CONDITIONAL_CANDIDATES.md) | Inventory of 98 conditional-FK candidates, with a 12-pair recommendation | Proposal sections "Complete the standard model" and "Support the model in Shape Shifter" |

The archived copies keep their original findings. Their open items are not restated in full here; the proposal owns them now.

## Coverage snapshot (2026-11-12)

Measured against the declared source of truth, `docs/investigations/sead-target-model-completeness/columns.csv`, exported from `sead_staging`.

| Measure | Value |
|---|---|
| Model entities | 136 (135 declare a `target_table`) |
| Effective source tables | 150 (156 exported, minus 6 `%colours` / `%images` exclusions) |
| Mapped by a model entity | 133 |
| Unmapped | 17 |
| Model `target_table` values absent from the source | 0 |
| Duplicate model `target_table` values | 0 |
| Target-model specification validation | 0 issues |
| Foreign-key audit across 135 modelled tables | 0 problems |

## What remains unmapped

Seventeen source tables have no model entity. All Tier 1 and Tier 2 tables are modelled; the rest are reference and subsystem tables that need an inclusion decision.

- Taxonomy and reference: `tbl_imported_taxa_replacements`, `tbl_temperatures`, `tbl_text_biology`, `tbl_text_distribution`, `tbl_text_identification_keys`, `tbl_years_types`.
- Vocabulary-context bridges: `tbl_sample_description_sample_group_contexts`, `tbl_sample_group_description_type_sampling_contexts`, `tbl_sample_location_type_sampling_contexts`.
- Subsystem tables: `tbl_ceramics`, `tbl_ceramics_lookup`, `tbl_ceramics_measurements`, `tbl_dendro`, `tbl_dendro_date_notes`, `tbl_dendro_dates`, `tbl_dendro_lookup`, `tbl_image_types`.

## Model-to-source differences

These are comparisons, not automatic defects. Column `required` is a project requirement, while nullability is a target-schema property; the two are decided separately.

- 17 non-key source columns, across 15 entities, are not declared by their modelled entity. Most are UUID columns (`dataset.dataset_uuid`, `site.site_uuid`, `method.method_uuid`, and similar).
- One model column is absent from its source table: `site_location.site_location_id`, the model's generated bridge key.
- 6 declared type differences: `analysis_entity_age.age_range` (`int4range` as `string`), `chronology.date_prepared` (timestamp as `date`), and four UUID columns typed `string`.
- 47 nullability differences, split between model-stricter and model-looser.
- 7 foreign keys imply a column that does not exist in the target table: six analysis-value/range entities reference `value_qualifier_symbol` through text columns `qualifier` / `low_qualifier` / `high_qualifier`, and `value_qualifier_symbol` → `value_qualifier` has the real column `cardinal_qualifier_id`.

## Shape Shifter support state

Verified in the current source, not assumed.

- Conditional foreign keys cannot declare `via`. `src/target_model/spec_validator.py` reports `CONDITIONAL_FOREIGN_KEY_VIA_UNSUPPORTED`, so the closest semantic case, `site` → `location` via `site_location`, cannot use the conditional feature.
- `ColumnSpec` in `src/target_model/models.py` has no `default` field, so the model cannot express a target-table default.
- No coverage command exists. `scripts/target_model_coverage.py` from the [coverage-boundary proposal](../SEAD_TARGET_MODEL_COVERAGE_BOUNDARY.md) is not implemented, so these counts are a manual measurement.
- The model's `target_table` values are unqualified. `sead_staging` exposes the same table names in `public` and `clearing_house`, so an unscoped audit cannot resolve them.
- The 2026-10-17 generator audit covers 39 supported children and reports `value_type_item` as unsupported with no ID generator. It predates the current 54-child inventory and has not been refreshed.
- The Change Request Ingester derives `required_fk_columns` from column `required` flags in `ingesters/sead_change_request/target_projection.py`, so relaxing a column's `required` also removes it from the unconditional required-column check.

## Verification basis

- Counts and comparisons: the closed [completeness investigation](../../investigations/sead-target-model-completeness/findings.md) and `resources/target_models/README.md`.
- Foreign-key audit and generator status: the archived [TARGET_MODEL_REVIEW.md](archive/TARGET_MODEL_REVIEW.md), sections "Foreign-key consistency" and "Deployed ID generators".
- Feature restrictions: read from `src/target_model/spec_validator.py`, `src/target_model/models.py`, and `ingesters/sead_change_request/target_projection.py`.
- Not verified in this snapshot: target-table defaults, unique constraints, sequences, and triggers. `columns.csv` does not report them.
