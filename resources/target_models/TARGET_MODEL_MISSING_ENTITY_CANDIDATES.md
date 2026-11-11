# Target Model Missing Entity Candidates: 2026-10-26 (recounted 2026-11-10)

**Model checked:** [sead_standard_model.yml](sead_standard_model.yml) (version 2.5.0)
**Schema checked (original, 2026-10-26):** `docs/sead/01_tables.sql` and `docs/sead/05_constraints.sql`
**Schema checked (recount, 2026-11-10):** `docs/investigations/sead-target-model-completeness/columns.csv` — the declared source of truth (a run of `exported-columns.sql` against `sead_staging`)

## Recount against the declared source of truth (2026-11-10)

The completeness investigation closed on 2026-11-10 and declared `columns.csv`
(source of truth) the authoritative surface. Recomputing against it, after the
declared exclusions, gives **40 unmapped tables**:

- Effective surface: 150 tables (156 in the export, minus 6 `%colours` / `%images`
  exclusions). 110 mapped, 40 unmapped, 0 out-of-source.
- All Tier 1 entities are now modelled. The 40 remaining gaps are 15 Tier 2
  data-capture tables, 16 Tier 3 reference tables, 8 newer subsystem tables, and the
  `tbl_site_site_types` bridge named under the Tier 1 correction below.
- 9 are new, because the `sead_staging` surface is wider than the 137-table schema
  dump the original 42-gap count used. These are subsystem tables the dump omitted:

| Candidate entity      | Table                       | Note                                                                                               |
|-----------------------|-----------------------------|----------------------------------------------------------------------------------------------------|
| `ceramic`             | `tbl_ceramics`              | Ceramics subsystem fact table                                                                      |
| `ceramic_lookup`      | `tbl_ceramics_lookup`       | Ceramics subsystem lookup                                                                          |
| `ceramic_measurement` | `tbl_ceramics_measurements` | Ceramics subsystem child fact                                                                      |
| `dendro`              | `tbl_dendro`                | Dendrochronology subsystem fact                                                                    |
| `dendro_date`         | `tbl_dendro_dates`          | Dendrochronology subsystem fact                                                                    |
| `dendro_date_note`    | `tbl_dendro_date_notes`     | Dendrochronology subsystem child                                                                   |
| `dendro_lookup`       | `tbl_dendro_lookup`         | Dendrochronology subsystem lookup                                                                  |
| `image_type`          | `tbl_image_types`           | Classifier for the excluded `%images` tables; decide scope with the image exclusion                |
| `property_type_group` | `tbl_property_type_groups`  | **Done (2026-11-10):** modelled as `property_type_group`; `property_type` declares the required FK |

The 9 new tables are subsystem or classifier tables outside the original
clearinghouse scope. Treat them as Tier 3 (scope decision needed) unless a project
needs them. `property_type_group` is now modelled because `property_type` declares
it. The tiered triage below still describes the original 42.

## Original triage against the schema dump (2026-10-26)

Method: compared all 137 `create table` names in the schema dump against the 101
`target_table` values declared in the model. 42 schema tables have no entity in the
model. The result list below is grouped by priority, using foreign-key references in
`05_constraints.sql` to decide whether an existing model entity already depends on
the missing table.

## Tier 1 — Referenced by foreign keys from entities already in the model

**Complete (2026-11-10).** All nine Tier 1 tables are now entities. Each foreign key
is conditional: the parent is required only when the referencing entity gains new
rows (`required_when.has_new_rows`), never for every insert.

| Candidate entity | Table | Reason |
|---|---|---|
| ~~`taxa_tree_genus`~~ | ~~`tbl_taxa_tree_genera`~~ | **Done:** entity `taxa_tree_genus`, conditional FK from `taxa` and `taxa_synonyms`; its `family_id` FK is now declared too |
| ~~`taxa_tree_family`~~ | ~~`tbl_taxa_tree_families`~~ | **Done:** entity `taxa_tree_family`, conditional FKs from `taxa_tree_genus` and `taxa_synonyms`; `order_id` FK to `taxa_tree_order` |
| ~~`taxa_tree_order`~~ | ~~`tbl_taxa_tree_orders`~~ | **Done:** entity `taxa_tree_order`, conditional FKs from `taxa_tree_family`; conditional `record_type` FK |
| ~~`taxa_tree_author`~~ | ~~`tbl_taxa_tree_authors`~~ | **Done:** entity `taxa_tree_author`, conditional FKs from `taxa` and `taxa_synonyms` |
| ~~`record_type`~~ | ~~`tbl_record_types`~~ | **Done:** entity `record_type`, conditional FKs from `method`, `abundance_element`, `taxa_tree_order` |
| ~~`data_type_group`~~ | ~~`tbl_data_type_groups`~~ | **Done:** entity `data_type_group`, conditional FK from `data_type` (which now declares `data_type_group_id`) |
| ~~`language`~~ | ~~`tbl_languages`~~ | **Done:** entity `language`, conditional FK from `taxa_common_names` |
| ~~`season`~~ | ~~`tbl_seasons`~~ | **Done:** entity `season`, conditional FK from `analysis_dating_range`; conditional `season_type` FK |
| ~~`season_type`~~ | ~~`tbl_season_types`~~ | **Done:** entity `season_type`, conditional FK from `season` |

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
| ~~`site_preservation_status`~~ | ~~`tbl_site_preservation_status`~~ | **Done (2026-11-10):** modelled as `site_preservation_status` (fact, aggregate child of `site`); `site.site_preservation_status_id` declares the FK |
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

## Reverse-direction finding (resolved 2026-11-10)

The 2026-10-26 review found 6 model `target_table` values absent from
`docs/sead/01_tables.sql`:

- `tbl_data_providers`
- `tbl_submission_states`
- `tbl_submissions`
- `tbl_submission_task_types`
- `tbl_submission_tasks`
- `tbl_feature_properties`

**Resolved:** all six are present in the declared source of truth (`columns.csv`,
`sead_staging`), so the model has **0 out-of-source target tables**. The five
submission tables are confirmed live (maintainer, 2026-11-10); the finding was
stale schema-dump coverage, not a model error. `tbl_feature_properties` is likewise
present. The pinned `docs/sead/01_tables.sql` dump simply predates these tables.

## Suggested next steps

1. Tier 1 is complete. Next priority is the `site` / `site_type` relationship
   correction: add a `site_site_type` bridge and drop the direct column from `site`.
2. Decide clearinghouse scope for the Tier 2 entities, then model the accepted ones.
   `analysis_dating_range` and `season` already declare `season_id`; the remaining
   Tier 3 dependency `tbl_taxa_seasonality` needs its own scope decision.
3. ~~Refresh `docs/sead/01_tables.sql` and `05_constraints.sql` so the six newer tables
   appear in the schema dump.~~ Superseded (2026-11-10): `columns.csv` against
   `sead_staging` is the declared source of truth; the schema dump is historical
   context only.
4. Fix or re-express the seven qualifier-family FKs (six analysis-value/range
   entities plus `value_qualifier_symbol` → `value_qualifier`) whose implied column
   name does not exist in the target table — see README "Known model defects".
5. Decide whether the model's `colour` / `sample_colour` entities stay, given the
   `%colours` / `%images` exclusion — coordinate with the coverage-boundary
   proposal (issue #532).
