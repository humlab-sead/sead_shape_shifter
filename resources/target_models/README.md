# Target Models

This folder contains target model specification files for the SEAD database.
This README is the authoritative record of the standard target model's current
completeness state. Last verified 2026-11-12 against the source declared by the
target-model completeness investigation (`docs/investigations/sead-target-model-completeness/`,
now closed; see its `findings.md` for how the investigation resolved).

`sead_standard_model.yml` (version 2.8.0) is the shared standard target model.
`sead_superset_model.yml` is a symlink to it, so both names resolve to one file.

## Current status (verified 2026-11-12)

Measured against the declared source of truth below:

| Measure | Value |
|---|---|
| Model entities | 136 (135 declare a `target_table`; `abundance_element_group` declares none) |
| Source-of-truth tables (effective surface) | 150 |
| Mapped by a model entity | 133 |
| Unmapped (candidate gaps) | 17 — listed in [TARGET_MODEL_COVERAGE_REVIEW.md](../../docs/proposals/TARGET_MODEL_PROJECT_REQUIREMENTS/TARGET_MODEL_COVERAGE_REVIEW.md) |
| Model `target_table` values absent from the source | 0 |

### Source of truth

`docs/investigations/sead-target-model-completeness/columns.csv` — a current run
of `exported-columns.sql` (same folder) against `sead_staging`, declared by the
maintainer on 2026-11-10. Rerun that query read-only against `sead_staging` to
refresh the surface. Earlier surfaces (the `docs/sead/01_tables.sql` dump, the
136-table filtered import snapshot) are historical context only.

### Exclusions from the completeness surface

- Tables dropped by the export query filters (`tbl_aggregate*`, `tbl_mcr%`,
  `tbl_tephra%`, `tbl_isotope%`, `tbl_updates_log`) are pending deprecation or
  unused: tables of no interest to the standard target model, never counted as gaps.
- Tables ending in `colours` or `images` are excluded by decision (2026-11-10):
  `tbl_colours`, `tbl_sample_colours`, `tbl_sample_group_images`,
  `tbl_sample_images`, `tbl_site_images`, `tbl_taxa_images`. The model's `colour`
  and `sample_colour` entities remain in the YAML; whether to remove them is an
  open question for the coverage-boundary proposal (issue #532).

### Known model gaps and project-configuration follow-up (verified 2026-11-12)

- The model now represents the optional `site` to `site_type` relationship through
  the `site_site_type` entity mapped to `tbl_site_site_types`. Some project
  configurations, including arbodat-rebecka, still declare `site.site_type_id`
  directly; this model-only update did not migrate those configurations.
- `site` also omits the `site_uuid` and `site_location_accuracy` columns that
  `tbl_sites` declares. Neither is an FK; both are unmodelled columns.
- Seven FKs imply a column absent from the target table: six analysis-value/range
  entities reference `value_qualifier_symbol`, but their real FK column is the text
  `qualifier` / `low_qualifier` / `high_qualifier` (referencing
  `tbl_value_qualifier_symbols.symbol`); `value_qualifier_symbol` → `value_qualifier`
  has the real column `cardinal_qualifier_id`.
- No automated check compares the model to the schema source. The
  coverage-boundary proposal (issue #532, `scripts/target_model_coverage.py`) is
  not implemented.

### Foreign-key consistency (verified 2026-11-10)

Every foreign key that `columns.csv` declares for a modelled table is present in
the model, and every FK column the model declares has a matching FK entity. The
2026-11-12 audit checked 135 modelled tables and reported zero foreign-key problems.
The 2026-11-10 pass resolved ten dangling references: it added the missing
`property_type_group` and `site_preservation_status` entities, added the
`site.site_preservation_status_id`, `method.unit_id`, `dataset.updated_dataset_id`,
`property_type.property_type_group_id`, `dating_material.geochron_id` and
`dating_material.taxon_id` columns, and declared the missing FKs to `unit`,
`contact`, `citation`, `geochronology` and `taxa`. Re-run the audit after adding
entities: it compares `columns.csv` FK rows against the model's `foreign_keys`
declarations.

## Documents in this folder

| File | Purpose | Status |
|---|---|---|
| `sead_standard_model.yml` | The standard target model | Current |
| `sead_superset_model.yml` | Symlink to the standard model | Current |

The review notes, gap triage, and conditional-FK inventory moved on 2026-11-12 to
[docs/proposals/TARGET_MODEL_PROJECT_REQUIREMENTS/archive/](../../docs/proposals/TARGET_MODEL_PROJECT_REQUIREMENTS/archive/).
Open model and Shape Shifter work is now tracked by
[Target Model Project Requirements](../../docs/proposals/TARGET_MODEL_PROJECT_REQUIREMENTS/TARGET_MODEL_PROJECT_REQUIREMENTS.md);
the current coverage state is recorded in
[TARGET_MODEL_COVERAGE_REVIEW.md](../../docs/proposals/TARGET_MODEL_PROJECT_REQUIREMENTS/TARGET_MODEL_COVERAGE_REVIEW.md).