# Target Model Missing Entity Candidates: 2026-10-26

**Model checked:** [sead_standard_model.yml](sead_standard_model.yml) (version 2.1.0)
**Schema checked:** `docs/sead/01_tables.sql` and `docs/sead/05_constraints.sql`

Method: compared all 137 `create table` names in the schema dump against the 101
`target_table` values declared in the model. 42 schema tables have no entity in the
model. The result list below is grouped by priority, using foreign-key references in
`05_constraints.sql` to decide whether an existing model entity already depends on
the missing table.

## Tier 1 — Referenced by foreign keys from entities already in the model

These missing tables are FK targets of modeled entities, so the model currently has
incomplete or dangling relationships. Adding them fixes references used by `taxa`,
`taxa_synonyms`, `taxa_common_names`, `data_type`, `method`, `abundance_element`,
and `analysis_dating_range`.

| Candidate entity | Table | Reason |
|---|---|---|
| `taxa_tree_genus` | `tbl_taxa_tree_genera` | `taxa.genus_id` and `taxa_synonyms.genus_id` reference it; `taxa` has no genus entity |
| `taxa_tree_family` | `tbl_taxa_tree_families` | FK from `tbl_taxa_tree_genera.order` chain and `taxa_synonyms.family_id` |
| `taxa_tree_order` | `tbl_taxa_tree_orders` | FK from `tbl_taxa_tree_families`; also FKs to `tbl_record_types` |
| `taxa_tree_author` | `tbl_taxa_tree_authors` | FK from `tbl_taxa_tree_master.author_id` and `taxa_synonyms.author_id` |
| `record_type` | `tbl_record_types` | FK from `method`, `abundance_element`, and (if added) `site_other_records` and `taxa_tree_orders` |
| `data_type_group` | `tbl_data_type_groups` | FK from `data_type.data_type_group_id`; `data_type` declares no parent today |
| `language` | `tbl_languages` | FK from `taxa_common_names.language_id` |
| `season` | `tbl_seasons` | FK from `analysis_dating_range.season_id` and `tbl_taxa_seasonality` |
| `season_type` | `tbl_season_types` | FK from `tbl_seasons.season_type_id` |

Related correction: the model's `site` entity declares a `site_type_id` column, but
`tbl_sites` has no such column in the schema dump. The site-to-site-type relationship
is the bridge table `tbl_site_site_types` (with `is_primary_type` and `confidence_code`
columns). The model should add a `site_site_type` bridge entity, in the style of
`site_location`, and drop the direct column from `site`.

## Tier 2 — Clear data-capture entities, likely in clearinghouse scope

Fact or bridge entities that carry submitted research data. Decide scope, then model.

| Candidate entity | Table | Notes |
|---|---|---|
| `analysis_entity_age` | `tbl_analysis_entity_ages` | Dating facts on analysis entities; FKs to `analysis_entity` and `chronology` (both modeled); has a generated `age_range` column |
| `analysis_entity_dimension` | `tbl_analysis_entity_dimensions` | Mirrors `analysis_value_dimension`, which is already modeled |
| `analysis_entity_prep_method` | `tbl_analysis_entity_prep_methods` | Bridge: analysis_entity to method |
| `measured_value` | `tbl_measured_values` | Fact on analysis_entity |
| `measured_value_dimension` | `tbl_measured_value_dimensions` | Child of measured_value, same pattern as other dimension tables |
| `geochron_reference` | `tbl_geochron_refs` | Bridge geochronology to citation |
| `relative_age_reference` | `tbl_relative_age_refs` | Bridge relative_ages to citation |
| `sample_group_description` | `tbl_sample_group_descriptions` | Counterpart to `sample_description`, which is modeled |
| `sample_group_description_type` | `tbl_sample_group_description_types` | Classifier for the above |
| `lithology` | `tbl_lithology` | Stratigraphic description attached to a sample group |
| `site_reference` | `tbl_site_references` | Site to citation bridge, parallel to `sample_group_reference` |
| `site_other_record` | `tbl_site_other_records` | Site-level misc record with uuid; FKs to citation and record_type |
| `site_preservation_status` | `tbl_site_preservation_status` | Site condition and threat facts; FK to contact |
| `dataset_method` | `tbl_dataset_methods` | Bridge dataset to method; `dataset` also carries a single `method_id` FK |
| `dataset_submission` | `tbl_dataset_submissions` | Legacy submission tracking; may be superseded by the newer `submission` entity — decide before modeling |
| `dataset_submission_type` | `tbl_dataset_submission_types` | Classifier for the above |

## Tier 3 — Taxonomy enrichment and reference data, probably out of scope

Low priority for the clearinghouse flow. Include only if a project needs them.

- `species_association` / `species_association_type` — `tbl_species_associations`, `tbl_species_association_types`
- `taxa_reference_specimen` — `tbl_taxa_reference_specimens`
- `taxa_seasonality` — `tbl_taxa_seasonality`; would also require `activity_type` (`tbl_activity_types`) and `season`
- `taxonomy_note` — `tbl_taxonomy_notes`
- `taxonomic_order_biblio` — `tbl_taxonomic_order_biblio`
- `text_biology`, `text_distribution`, `text_identification_key` — `tbl_text_biology`, `tbl_text_distribution`, `tbl_text_identification_keys`
- `imported_taxa_replacement` — `tbl_imported_taxa_replacements`; internal ETL bookkeeping
- `temperatures` — `tbl_temperatures`; climate proxy data, likely legacy
- `years_type` — `tbl_years_types`; small vocabulary, no FK references found in the dump
- Vocabulary-context bridges: `sample_description_sample_group_context`
  (`tbl_sample_description_sample_group_contexts`),
  `sample_group_description_type_sampling_context`
  (`tbl_sample_group_description_type_sampling_contexts`),
  `sample_location_type_sampling_context`
  (`tbl_sample_location_type_sampling_contexts`)

## Reverse-direction finding

The model references 6 tables that are absent from `docs/sead/01_tables.sql`:

- `tbl_data_providers`
- `tbl_submission_states`
- `tbl_submissions`
- `tbl_submission_task_types`
- `tbl_submission_tasks`
- `tbl_feature_properties`

These are presumably newer clearinghouse tables not yet reflected in the schema dump.
Confirm the dump is current; in particular `feature_property` has no backing table in
the schema documents.

## Suggested next steps

1. Add the 9 Tier 1 entities to `sead_standard_model.yml`, and correct the `site` /
   `site_type` relationship to use a `site_site_type` bridge.
2. Decide clearinghouse scope for the Tier 2 entities, then model the accepted ones.
3. Refresh `docs/sead/01_tables.sql` and `05_constraints.sql` so the six newer tables
   appear in the schema dump.
