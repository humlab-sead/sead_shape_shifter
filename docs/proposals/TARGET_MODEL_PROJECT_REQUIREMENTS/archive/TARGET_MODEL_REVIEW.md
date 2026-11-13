# Target Model Review: 2026-11-12

**Model under review:** [sead_standard_model.yml](../../../../resources/target_models/sead_standard_model.yml) (version 2.8.0)
**Status:** In progress; the model and schema snapshot have been compared, but identity, requiredness, and deployment decisions remain open.

The standard and superset model paths resolve to the same YAML file. This review describes that shared model; whether both names are needed remains undecided. The test specifications in `tests/test_data/specs` are symlinks to the resource files, so they use the shared models rather than independent copies.

## Current model and schema snapshot (2026-11-12)

The source of truth for SEAD tables, columns, data types, nullability, and foreign keys is [`columns.csv`](../../../investigations/sead-target-model-completeness/columns.csv), exported from `sead_staging`. Do not use the historical `docs/sead/01_tables.sql` dump to describe the current database schema.

| Check                                            | Current result                                                   |
|--------------------------------------------------|------------------------------------------------------------------|
| Model entities                                   | 136; 135 declare a `target_table`                                |
| Effective source tables                          | 150 of 156 exported tables; six colour/image tables are excluded |
| Mapped source tables                             | 133; 17 remain unmapped                                          |
| Model target tables absent from the source       | 0                                                                |
| Duplicate model `target_table` values            | 0                                                                |
| Target-model specification validation            | 0 issues                                                         |
| Foreign-key audit                                | 0 problems across 135 modelled tables                            |
| Source non-key columns not declared in the model | 17 across 15 entities                                            |
| Model columns absent from their source table     | 1                                                                |
| Mapped column type differences                   | 6                                                                |
| Mapped column nullability differences            | 47                                                               |

The 17 unmapped tables are:

- Taxonomy references: `tbl_imported_taxa_replacements`, `tbl_temperatures`, `tbl_text_biology`, `tbl_text_distribution`, `tbl_text_identification_keys`, and `tbl_years_types`.
- Vocabulary-context bridges: `tbl_sample_description_sample_group_contexts`, `tbl_sample_group_description_type_sampling_contexts`, and `tbl_sample_location_type_sampling_contexts`.
- Subsystem tables: `tbl_ceramics`, `tbl_ceramics_lookup`, `tbl_ceramics_measurements`, `tbl_dendro`, `tbl_dendro_date_notes`, `tbl_dendro_dates`, `tbl_dendro_lookup`, and `tbl_image_types`.

The 17 non-key source columns not declared by modelled entities are `citation.biblio_uuid`, `dataset.dataset_uuid`, `dating_uncertainty.description`, `dimension.dimension_description`, `geochronology.geochron_uuid`, `master_dataset.master_set_uuid`, `method.method_uuid`, `property_type.property_scope`, `property_type.uuid`, `relative_ages.relative_age_uuid`, `sample_group.sample_group_uuid`, `site.site_location_accuracy`, `site.site_uuid`, `value_class.value_class_uuid`, `value_qualifier.qualifier_uuid`, `value_qualifier_symbol.qualifier_uuid`, and `value_type.value_type_uuid`. An omitted source column is not automatically a defect; decide whether each field belongs in the model.

The model column absent from `columns.csv` is `site_location.site_location_id`. It is the model's generated bridge key and is not a column in the source table.

The six declared type differences are `analysis_entity_age.age_range` (`int4range` represented as `string`), `chronology.date_prepared` (source timestamp represented as `date`), and the UUID fields `ecocode_system.ecocode_system_uuid`, `rdb_system.rdb_system_uuid`, `taxa_synonyms.synonym_uuid`, and `taxonomic_order_system.taxonomic_order_system_uuid` (each represented as `string`). Confirm these mappings before changing them.

The 47 nullability differences are:

- The model says **not nullable** while the source allows null: `analysis_boolean_value.value`; `analysis_dating_range.high_value` and `low_value`; `analysis_entity.dataset_id` and `physical_sample_id`; `analysis_integer_range.high_value` and `low_value`; `analysis_integer_value.value`; `analysis_numerical_value.value`; `chronology.chronology_name`; `data_type.data_type_name`; `data_type_group.data_type_group_name`; `dataset.method_id` and `submission_id`; `dating_material.material_dated`; `dating_uncertainty.uncertainty`; `dimension.dimension_abbrev`; `ecocode.ecocode_definition_id` and `taxon_id`; `ecocode_definition.ecocode_group_id` and `name`; `ecocode_group.ecocode_system_id` and `name`; `ecocode_system.name`; `identification_level.identification_level_abbrev` and `identification_level_name`; `location_type.location_type`; `sample_group.site_id`; `sample_group_coordinate.sample_group_position`; `sample_group_note.note`; `sample_group_reference.sample_group_id`; `sample_location.location`; `sample_location_type.location_type`; `season_type.season_type`; `site.site_name`; `site_preservation_status.site_id`; `submission.submission_state_id`; `taxonomic_order.taxon_id` and `taxonomic_order_system_id`; and `value_type_item.name`.
- The model says **nullable** while the source requires a value: `analysis_dating_range.age_type_id`, `data_type.data_type_group_id`, `ecocode_system.ecocode_system_uuid`, `sample_group_sampling_context.sort_order`, `submission.submission_uuid`, `taxonomic_order_system.taxonomic_order_system_uuid`, and `value_qualifier.description`.

These are schema comparisons, not automatic model errors. `ColumnSpec.required` describes whether a project must provide a field; it is separate from target-table nullability. `columns.csv` does not report unique constraints, defaults, sequences, or triggers, so it cannot settle those questions.

## 1. `location`

### Question

Can the model support both direct-ID linking and reconciliation-based linking, including both within one project? Direct-ID rows supply an existing SEAD `location_id`; reconciliation rows use location name and type to identify a candidate and either associate an approved `location_id` or remain unmatched.

### Current specification

- `location` is a required `lookup` entity targeting `tbl_locations`.
- `location_type_id` is non-nullable in the source table and is included with `location_name` in `unique_sets`. Its `ColumnSpec` does not set `required: true`.
- `location` has a conditional FK to `location_type`, with `required_when.has_new_rows: location`.
- `location_type` is not a required entity. Its `location_type` column is required and non-nullable in the model, while `columns.csv` marks the source column nullable.
- `location` omits an explicit `reconciliation` value. Its `lookup` role defaults to `reconcile-exact`.

### Review notes

- These are alternative paths for individual location references, not mutually exclusive project-wide modes:
	1. A fixed or materialized `location` entity can supply an existing SEAD `location_id`. In this path, `location_type_id` need not be supplied because the referenced SEAD row already has its type.
	2. Reconciliation can use `location_name` and `location_type_id` to find a candidate. A user can approve the resulting `location_id`, or no location may be found.
- `location.required: true` requires every project to declare `location`; `location_type.required` is false. The FK requirement is conditional on new `location` rows rather than unconditional for every project.
- The model marks `location_name` as required, but does not mark `location_type_id` as required even though the source column is non-nullable. A new database row needs a `location_type_id`; the current project-column requirement does not express that.
- `location_type.location_type` is required and non-nullable in the model, but the source column is nullable according to `columns.csv`.
- A fixed or materialized `location` entity containing only `location_id` may still conflict with the required entity and column rules. Direct-ID use does not, by itself, waive `location.required` or the `location_name` requirement.
- Entity-level `required: true` means every conforming project must include that entity. FK-level `required: true` means every conforming project must declare the relationship. These are project conformance requirements, not statements that a SEAD row must be newly inserted.
- For the Change Request Ingester MVP, `foreign_keys` affect FK projection and required-FK checks. The current conditional FK is tied to new `location` rows; it is not an unconditional project-wide requirement.
- `unique_sets` records target-side column groups declared unique, but it has no direct effect on Change Request Ingester reconciliation. Therefore, this metadata alone does not make reconciliation depend on `location_type_id`.
- For reconciliation-based rows, `(location_type_id, location_name)` can disambiguate locations that share a name. For direct-ID rows, the ID already identifies the target row.

### Next steps

- [ ] **Decision needed:** Define when projects must declare lookup entities and relationships: when referencing known IDs, reconciling records, or creating records.
- [ ] **Decision needed:** Define how one project can support both paths for an entity, including whether it needs conditional requirements or separate project entities.
- [ ] Decide whether `location_type_id` should be project-required for new `location` rows, while preserving its target nullability and FK.
- [ ] Update conformance requirements for `location` and related classifier/fact-to-lookup relationships to match those decisions. Preserve target-database FK constraints.

### References

- [Target Model Guide](../../../TARGET_MODEL_GUIDE.md)
- [Target Model Specification Format: Identity Columns](../../done/TARGET_MODEL_SPECIFICATION_FORMAT.md)

## 2. `site` and `site_location`

### Observation

For a project that uses only existing, known SEAD `site_id` values, it does not need to include `site_location` just to restate each site's existing location relationship.

### Current specification

- `site` is marked `required: true` and declares a required relationship to `location` via `site_location`.
- `site_location` is separately marked `required: true` and has required FKs to both `site` and `location`.
- The bridge identity is `(site_id, location_id)`. The model also declares `site_location_id` as a generated bridge key; `columns.csv` has no such source column.
- `site.site_name` is required and non-nullable in the model, while the source column is nullable.
- `site` has an optional relationship to `site_type` through `site_site_type`, mapped to `tbl_site_site_types`. The bridge declares the source columns, the `[site_id, site_type_id]` unique set, and conditional FKs to both related entities.
- Existing project configurations, including arbodat-rebecka, still declare `site.site_type_id` directly. This model-only change does not migrate those configurations; they need a separate update to provide `site_site_type` rows.
- The optional `site_preservation_status_id` FK matches the nullable source column. The model omits the source columns `site_uuid` and `site_location_accuracy`.

### Review notes

- The current conformance rules require every project to include `site_location` for the required bridge-mediated relationship, and require the bridge to declare its FK to `location`.
- This makes the project describe the full target-model relationship graph even when it only references existing sites whose site-location links already exist in SEAD.
- As with `location_type`, the target database may require site-location relationships for site records, but that does not mean every project must supply bridge rows when it is not creating or reconciling sites.
- The model now represents the source relationship accurately. The existing project-level direct `site_type_id` mappings remain a separate follow-up.

### Next steps

- [ ] **Decision needed:** Decide whether a project must declare `site_location` when it only references existing sites by `site_id`.
- [ ] Apply the policy from section 1 to the `site` and `site_location` requirements. Preserve the target database's relationship constraints.
- [ ] Migrate project configurations that still provide `site_type_id` on `site` to provide `site_site_type` bridge rows.
- [ ] Decide whether the source `site_uuid` and `site_location_accuracy` columns belong in the model.

## 3. `sample_group`

### Observation

The target model now records uniqueness groups only in `unique_sets`. For `sample_group`, the group is `[site_id, sample_group_name]`, and `sample_group_name` is declared `required: true`.

### Current specification

- `sample_group.unique_sets` includes `[site_id, sample_group_name]`.
- `site_id` and `method_id` are declared required and non-nullable. The source allows `site_id` to be null, so the model is stricter for that column.
- `sample_group_name` is declared required and remains nullable in both the model and source schema.
- `sampling_context_id` is optional and nullable in both the model and `columns.csv`; its FK to `sample_group_sampling_context` is optional.
- The source `sample_group_uuid` column is non-nullable but is not declared in the model.

The former `identity_columns` field and its field-specific required check have been removed. Membership in `unique_sets` does not set a column's `required` flag. Review `nullable` separately; it describes whether the target column may contain null.

### Next steps

- [x] Confirmed against `columns.csv`: `sampling_context_id` is nullable; the model's optional column and FK do not conflict with source nullability.
- [ ] Decide whether the model should continue to require `site_id` for project rows even though the source column is nullable.
- [ ] Decide whether `sample_group_uuid` should be represented in the target model; see section 12.

## 4. `sample_group_reference`

### Observation

This entity represents the association between a sample group and a citation. The current superset declares it as a `bridge`.

### Current specification

- The current role is `bridge`.
- The entity targets `tbl_sample_group_references` and declares `[sample_group_id, biblio_id]` in `unique_sets`.
- It has required FKs to `sample_group` and `citation`, and no other payload columns.
- `aggregate_parent` is `sample_group`.
- `biblio_id` is non-nullable in the source and modelled as required. `sample_group_id` is nullable in `columns.csv`, but the model marks it required and non-nullable.

### Next steps

- [x] Confirmed: `bridge` is the agreed role for this association-table entity.
- [x] Set `sample_group_reference.role` to `bridge`.
- [x] Confirmed: keep `aggregate_parent: sample_group`; it determines child identity behavior independently of the role.
- [ ] Decide whether the project should be required to provide `sample_group_id` even though the source column permits null.

## 5. `sample`

### Post-MVP consideration

A data provider may resubmit a previously submitted sample with new or updated analysis values. The post-MVP release needs to define how the system recognizes that sample across submissions and applies those analysis-value changes.

### Current specification

- `sample` is a required `fact` with `[sample_group_id, sample_name]` in `unique_sets`.
- No explicit `identity_tracking` or `reconciliation` policy is declared. Under current defaults, a `fact` is tracked and allocated an identity.

### Next steps

- ~~[ ]~~ Deferred: ~~Determine whether a provider UUID or another provider-scoped identifier stays stable across sample resubmissions.~~
- [x] Rejected: `(sample_group_id, sample_name)` is not sufficient to recognize a resubmitted sample.
- ~~[ ]~~ Deferred: ~~Define whether resubmissions add, update, or replace analysis values, or require review when values differ.~~
- ~~[ ]~~ Deferred: ~~Define how to retain submission provenance and record changes without creating duplicate samples or losing prior values.~~
- ~~[ ]~~ Deferred: ~~After those decisions, define the sample identity and tracking policy. Keep the current policy until then.~~

## 6. `value_type_item`

### Observation

`value_type` is the aggregate parent of `value_type_item`. A value type can define a categorical specification, such as `color`, whose items are `red`, `green`, and other allowed values. A value item is meaningful within its parent value type rather than as a standalone classifier.

### Current specification

- `value_type_item` has role `classifier` and now declares `aggregate_parent: value_type`.
- It has a required FK to `value_type` and declares `[value_type_id, name]` in `unique_sets`.
- `value_type_id` is non-nullable in both source and model. The source allows `name` to be null, while the model marks it required and non-nullable.

The aggregate-parent relationship is now represented in the model.

### Next steps

- [ ] **Decision needed:** Agree whether an existing role can represent a categorical item scoped to a value-type definition.
- [ ] After role semantics are agreed, select the role for `value_type_item`; add a role only if the existing roles do not express this relationship.

## 7. `sample_horizon`

### Observation

`sample_horizon` records a horizon assignment for a sample. It relates the `sample` fact to the `horizon` classifier and belongs to the sample aggregate.

### Current specification

- `sample_horizon` has `role: fact` and `aggregate_parent: sample`.
- It declares `[physical_sample_id, horizon_id]` in `unique_sets` and has required FKs to `sample` and `horizon`.
- The effective identity resolver infers `identity_tracking: child` from `aggregate_parent`; the `fact` role does not override that child identity.

### Review conclusion

Keep `role: fact` for `sample_horizon`: it represents sample-level metadata, while `aggregate_parent: sample` expresses that its identity is inherited from the sample. This differs from `site_location`, whose purpose is to bridge the `site` and `location` lookup entities. Classify these entities by what their records represent, not only by the presence of multiple foreign keys.

## 8. `method` and `method_group`

### Observation

`method.method_group_id` is a required, non-nullable column, while the FK declaration to `method_group` has `required: false`. This can look contradictory, but the two settings describe different project requirements.

### Current specification

- `method` is a required `classifier` entity with `reconciliation: lookup-extensible`.
- `method_group_id` is marked `required: true` and `nullable: false`, matching the source column.
- The FK from `method` to `method_group` is marked `required: false`; `method_group` itself is also marked `required: false`.
- `method.method_uuid` is non-nullable in `columns.csv` but is not declared in the model.

### Review notes

- A required column means each project `method` must provide `method_group_id`.
- An optional FK means a project is not required to declare `method_group` as a related entity. It may still provide a known group ID directly.
- This is consistent if projects may reference established method groups by ID without supplying or reconciling the group entity. If projects must always model the relationship through `method_group`, the FK should be required.
- A destination-table default could be another reason a project need not provide the value, but the target-model `ColumnSpec` has no `default` field. The current `required: true` declaration still says the project must provide the column; confirm whether `tbl_methods.method_group_id` has a database default and whether this specification should support expressing defaults.

### Next steps

- [ ] **Decision needed:** Decide whether a project may provide a known `method_group_id` without declaring the `method_group` entity.
- [ ] **Decision needed:** Confirm whether the target table supplies a default for `method_group_id`.
- [ ] Based on those decisions, align the column, FK, and entity `required` settings with the intended project workflow.
- [ ] If a database default should satisfy a missing value, decide how to represent that behavior in the target-model format.
- `columns.csv` does not include defaults, so the default question cannot be resolved from this schema snapshot.

## 9. `dataset`

### Observation

A dataset groups analytical records. It can be viewed as a `fact` describing an analytical collection, and it may be the aggregate parent of the analyses it contains.

### Current specification

- `dataset` has `role: lookup`, with explicit `identity_tracking: tracked` and `reconciliation: allocate`, plus `synchronize_sequence_after_insert: true`.
- `analysis_entity` has `role: fact` and `aggregate_parent: dataset`, with required FKs to `sample` and `dataset`. Its effective identity is `child`.
- `analysis_value` declares `aggregate_parent: analysis_entity`.
- `dataset` declares FKs to `method`, `master_dataset`, `project`, `submission`, and `data_type` as required; its `citation` and self-reference through `updated_dataset_id` are optional.
- `data_type_id` is non-nullable in both source and model. `master_set_id` and `project_id` are nullable in the source and model, while `method_id` and `submission_id` are nullable in the source but non-nullable in the model.
- `dataset.dataset_uuid` is non-nullable in `columns.csv` but is not declared in the model.
- `analysis_entity.physical_sample_id` and `dataset_id` are nullable in the source but required and non-nullable in the model.

### Review notes

- The required lookup entities are `master_dataset`, `data_provider`, `citation`, and `contact`. Entity requiredness does not make every FK to those lookups required.
- Changing `dataset.role` from `lookup` to `fact` alone would not change its identity behavior because `identity_tracking` and `reconciliation` are explicitly set.
- The model now declares the required dataset relationships listed above; the earlier missing-FK and missing-`required` findings are resolved.
- Project requiredness remains distinct from target nullability. In particular, `method_id` and `submission_id` are required by the model even though the source allows nulls; `master_set_id` and `project_id` are project-required fields whose target columns allow nulls.
- `analysis_entity` must not use SIMS tracked identity. The model now satisfies that: it declares no `identity_tracking` or `reconciliation`, so `aggregate_parent: dataset` resolves it to child identity with no reconciliation strategy.
- Child identity inherits the dataset aggregate, so analysis values, abundances, and their descendants sit under the dataset indirectly. Section 11 records the derived chains.
- `analysis_entity` also links `sample` through a required FK. Under child identity that link references a sample row; it does not give `analysis_entity` its own identity.
- `dataset` is a tracked root even though its role is `lookup`, because both identity fields are explicit. The role no longer decides its identity behavior.

### Review decision

`analysis_entity` must not be a SIMS tracked entity. In the current model it is a `fact` child of `dataset` (`aggregate_parent: dataset`), so its target ID belongs to the dataset aggregate.

### Next steps

- [ ] Define how `analysis_entity`'s separate sample relationship affects uniqueness and resubmission handling.
- [ ] **Decision needed:** Decide whether `dataset` should use the `fact` or `lookup` role. The choice does not change identity while `identity_tracking` and `reconciliation` stay explicit.
- [ ] **Decision needed:** Confirm that the required project relationships for `method`, `master_dataset`, `project`, `submission`, and `data_type` are intentional, especially where the source column is nullable.
- [ ] Decide whether `dataset_uuid` should be represented in the model; see section 12.

## 10. `data_provider` YAML style

### Observation

The `data_provider.columns` entries now use block mappings, consistent with most column specs in this target model.

### Next steps

- [x] Rewrite these column specs as block mappings for consistency and easier scanning. This is a readability change and does not alter the model's meaning.

## 11. Aggregate-child inventory and root-row rules

The inventory below is derived from effective identity and the full `aggregate_parent` chain (`resolve_aggregate_chain`) for model version 2.8.0. It contains 54 valid aggregate children. The chain starts at the child and ends at the root. Section 13 is a historical ID-generator audit and does not cover every child in this current inventory. The deployment-time ID-resolution design and its validation requirements are covered by the [Deployment-Time Staging proposal](../../CHANGE_REQUEST_INGESTER/done/DEPLOYMENT_TIME_STAGING/DEPLOYMENT_TIME_STAGING.md).

| Entity | Parent chain | Root (effective identity) | Target table | `public_id` |
| --- | --- | --- | --- | --- |
| `analysis_entity` | `analysis_entity -> dataset` | `dataset` (tracked) | `tbl_analysis_entities` | `analysis_entity_id` |
| `analysis_entity_dimension` | `analysis_entity_dimension -> analysis_entity -> dataset` | `dataset` (tracked) | `tbl_analysis_entity_dimensions` | `analysis_entity_dimension_id` |
| `analysis_entity_prep_method` | `analysis_entity_prep_method -> analysis_entity -> dataset` | `dataset` (tracked) | `tbl_analysis_entity_prep_methods` | `analysis_entity_prep_method_id` |
| `abundance` | `abundance -> analysis_entity -> dataset` | `dataset` (tracked) | `tbl_abundances` | `abundance_id` |
| `analysis_value` | `analysis_value -> analysis_entity -> dataset` | `dataset` (tracked) | `tbl_analysis_values` | `analysis_value_id` |
| `geochronology` | `geochronology -> analysis_entity -> dataset` | `dataset` (tracked) | `tbl_geochronology` | `geochron_id` |
| `relative_dating` | `relative_dating -> analysis_entity -> dataset` | `dataset` (tracked) | `tbl_relative_dates` | `relative_date_id` |
| `abundance_modification` | `abundance_modification -> abundance -> analysis_entity -> dataset` | `dataset` (tracked) | `tbl_abundance_modifications` | `abundance_modification_id` |
| `abundance_property` | `abundance_property -> abundance -> analysis_entity -> dataset` | `dataset` (tracked) | `tbl_abundance_properties` | `abundance_property_id` |
| `analysis_boolean_value` | `analysis_boolean_value -> analysis_value -> analysis_entity -> dataset` | `dataset` (tracked) | `tbl_analysis_boolean_values` | `analysis_boolean_value_id` |
| `analysis_categorical_value` | `analysis_categorical_value -> analysis_value -> analysis_entity -> dataset` | `dataset` (tracked) | `tbl_analysis_categorical_values` | `analysis_categorical_value_id` |
| `analysis_dating_range` | `analysis_dating_range -> analysis_value -> analysis_entity -> dataset` | `dataset` (tracked) | `tbl_analysis_dating_ranges` | `analysis_dating_range_id` |
| `analysis_identifier` | `analysis_identifier -> analysis_value -> analysis_entity -> dataset` | `dataset` (tracked) | `tbl_analysis_identifiers` | `analysis_identifier_id` |
| `analysis_integer_range` | `analysis_integer_range -> analysis_value -> analysis_entity -> dataset` | `dataset` (tracked) | `tbl_analysis_integer_ranges` | `analysis_integer_range_id` |
| `analysis_integer_value` | `analysis_integer_value -> analysis_value -> analysis_entity -> dataset` | `dataset` (tracked) | `tbl_analysis_integer_values` | `analysis_integer_value_id` |
| `analysis_note` | `analysis_note -> analysis_value -> analysis_entity -> dataset` | `dataset` (tracked) | `tbl_analysis_notes` | `analysis_note_id` |
| `analysis_numerical_range` | `analysis_numerical_range -> analysis_value -> analysis_entity -> dataset` | `dataset` (tracked) | `tbl_analysis_numerical_ranges` | `analysis_numerical_range_id` |
| `analysis_numerical_value` | `analysis_numerical_value -> analysis_value -> analysis_entity -> dataset` | `dataset` (tracked) | `tbl_analysis_numerical_values` | `analysis_numerical_value_id` |
| `analysis_taxon_count` | `analysis_taxon_count -> analysis_value -> analysis_entity -> dataset` | `dataset` (tracked) | `tbl_analysis_taxon_counts` | `analysis_taxon_count_id` |
| `analysis_value_dimension` | `analysis_value_dimension -> analysis_value -> analysis_entity -> dataset` | `dataset` (tracked) | `tbl_analysis_value_dimensions` | `analysis_value_dimension_id` |
| `dataset_method` | `dataset_method -> dataset` | `dataset` (tracked) | `tbl_dataset_methods` | `dataset_method_id` |
| `dataset_submission` | `dataset_submission -> dataset` | `dataset` (tracked) | `tbl_dataset_submissions` | `dataset_submission_id` |
| `feature_property` | `feature_property -> feature` | `feature` (reconciled) | `tbl_feature_properties` | `feature_property_id` |
| `geochron_reference` | `geochron_reference -> geochronology -> analysis_entity -> dataset` | `dataset` (tracked) | `tbl_geochron_refs` | `geochron_ref_id` |
| `lithology` | `lithology -> sample_group` | `sample_group` (tracked) | `tbl_lithology` | `lithology_id` |
| `measured_value` | `measured_value -> analysis_entity -> dataset` | `dataset` (tracked) | `tbl_measured_values` | `measured_value_id` |
| `measured_value_dimension` | `measured_value_dimension -> measured_value -> analysis_entity -> dataset` | `dataset` (tracked) | `tbl_measured_value_dimensions` | `measured_value_dimension_id` |
| `relative_age_reference` | `relative_age_reference -> relative_ages` | `relative_ages` (reconciled) | `tbl_relative_age_refs` | `relative_age_ref_id` |
| `sample_alt_ref` | `sample_alt_ref -> sample` | `sample` (tracked) | `tbl_sample_alt_refs` | `sample_alt_ref_id` |
| `sample_colour` | `sample_colour -> sample` | `sample` (tracked) | `tbl_sample_colours` | `sample_colour_id` |
| `sample_coordinate` | `sample_coordinate -> sample` | `sample` (tracked) | `tbl_sample_coordinates` | `sample_coordinate_id` |
| `sample_description` | `sample_description -> sample` | `sample` (tracked) | `tbl_sample_descriptions` | `sample_description_id` |
| `sample_dimension` | `sample_dimension -> sample` | `sample` (tracked) | `tbl_sample_dimensions` | `sample_dimension_id` |
| `sample_horizon` | `sample_horizon -> sample` | `sample` (tracked) | `tbl_sample_horizons` | `sample_horizon_id` |
| `sample_location` | `sample_location -> sample` | `sample` (tracked) | `tbl_sample_locations` | `sample_location_id` |
| `sample_note` | `sample_note -> sample` | `sample` (tracked) | `tbl_sample_notes` | `sample_note_id` |
| `sample_group_coordinate` | `sample_group_coordinate -> sample_group` | `sample_group` (tracked) | `tbl_sample_group_coordinates` | `sample_group_position_id` |
| `sample_group_dimension` | `sample_group_dimension -> sample_group` | `sample_group` (tracked) | `tbl_sample_group_dimensions` | `sample_group_dimension_id` |
| `sample_group_note` | `sample_group_note -> sample_group` | `sample_group` (tracked) | `tbl_sample_group_notes` | `sample_group_note_id` |
| `sample_group_reference` | `sample_group_reference -> sample_group` | `sample_group` (tracked) | `tbl_sample_group_references` | `sample_group_reference_id` |
| `site_natgridref` | `site_natgridref -> site` | `site` (reconciled) | `tbl_site_natgridrefs` | `site_natgridref_id` |
| `site_preservation_status` | `site_preservation_status -> site` | `site` (reconciled) | `tbl_site_preservation_status` | `site_preservation_status_id` |
| `site_property` | `site_property -> site` | `site` (reconciled) | `tbl_site_properties` | `site_property_id` |
| `ecocode` | `ecocode -> taxa` | `taxa` (reconciled) | `tbl_ecocodes` | `ecocode_id` |
| `rdb` | `rdb -> taxa` | `taxa` (reconciled) | `tbl_rdb` | `rdb_id` |
| `species_association` | `species_association -> taxa` | `taxa` (reconciled) | `tbl_species_associations` | `species_association_id` |
| `taxa_common_names` | `taxa_common_names -> taxa` | `taxa` (reconciled) | `tbl_taxa_common_names` | `taxon_common_name_id` |
| `taxa_measured_attributes` | `taxa_measured_attributes -> taxa` | `taxa` (reconciled) | `tbl_taxa_measured_attributes` | `measured_attribute_id` |
| `taxa_reference_specimen` | `taxa_reference_specimen -> taxa` | `taxa` (reconciled) | `tbl_taxa_reference_specimens` | `taxa_reference_specimen_id` |
| `taxa_seasonality` | `taxa_seasonality -> taxa` | `taxa` (reconciled) | `tbl_taxa_seasonality` | `seasonality_id` |
| `taxa_synonyms` | `taxa_synonyms -> taxa` | `taxa` (reconciled) | `tbl_taxa_synonyms` | `synonym_id` |
| `taxonomic_order` | `taxonomic_order -> taxa` | `taxa` (reconciled) | `tbl_taxonomic_order` | `taxonomic_order_id` |
| `taxonomy_note` | `taxonomy_note -> taxa` | `taxa` (reconciled) | `tbl_taxonomy_notes` | `taxonomy_notes_id` |
| `value_type_item` | `value_type_item -> value_type` | `value_type` (reconciled) | `tbl_value_type_items` | `value_type_item_id` |

Every listed child declares a direct foreign key to its immediate aggregate parent, and target-model validation reports no missing-parent, cycle, or root-identity issue for this model. Ownership comes from `aggregate_parent`, not from the role: `abundance_modification` is a child `fact`, and `sample_group_reference` is a `bridge` that is still a child of `sample_group`.

### Root-row rules

| Root | Effective identity | Rule for a child row |
| --- | --- | --- |
| `dataset` | tracked (explicit, with `lookup` role) | The dataset root must be inserted by the same submission. A child of an existing dataset is rejected. |
| `sample`, `sample_group` | tracked | The tracked fact root must be inserted by the same submission. A child of an existing tracked fact root is rejected. |
| `feature`, `relative_ages`, `site`, `taxa`, `value_type` | reconciled | The root must have a resolved target ID. A child of an existing reconciled root is allowed; an unresolved root blocks the child. |

- Tracked roots keep their SIMS-assigned IDs. Deployment-time allocation applies to the child's own target sequence, not to the root.
- This work does not create a new `value_type` root. Children of an existing `value_type` remain eligible once its target ID is resolved. The item role decision in section 6 is independent of that eligibility.
- A candidate is not automatically enabled for insertion. The row rule above is enforced per row when staging resolves IDs.

### Derived bridges that are not aggregate children

`abundance_ident_level` has `role: bridge` and no `aggregate_parent`, so it is not an aggregate child and its effective identity is `derived`. It declares required FKs to `abundance` and `identification_level` and the unique set `[abundance_id, identification_level_id]`. Because `abundance` receives a deployment-time ID, `abundance_ident_level` depends on that ID even though it is outside the child derivation. The deployment-time ID map must resolve its `abundance_id` before its rows are inserted or checked.

The current model includes `measured_value` and its `measured_value_dimension` child. The `dendro` tables remain unmapped in the source-coverage inventory above.

### Derived bridges that are not aggregate children

The model has seven `bridge` entities with derived identity and no `aggregate_parent`: `abundance_ident_level`, `dataset_contact`, `sample_feature`, `site_location`, `site_reference`, `site_site_type`, and `taxonomic_order_biblio`. Their IDs are derived from their relationship rows; they are not children in the aggregate inventory. When the deployment-time allocation path applies, `abundance_ident_level` depends on the resolved target ID of its `abundance` row. Section 13's sequence audit is historical.

## 12. Provider-supplied UUIDs as an identity signal

### Observation

Some entities carry UUID columns. `columns.csv` confirms UUID columns in the source, but the model does not represent every one consistently. A provider-supplied UUID may help recognize a resubmission or update, but target-side uniqueness metadata does not itself define provider matching behavior.

This is a general rule for any entity that can receive a data-provider UUID, not a special case for `sample`.

### Current specification

- `data_provider.data_provider_uuid` is typed `uuid` and non-nullable in the model and source. Its model column is not marked `required`, and its current `unique_sets` include `data_provider_code` and `data_provider_name`, not the UUID.
- `submission.submission_uuid` is typed `uuid`, but the model marks it optional and nullable. `columns.csv` marks it non-nullable, and it is not in the model's `unique_sets`.
- `site_other_record.site_other_records_uuid`, `species_association.species_association_uuid`, and `taxonomy_note.taxonomy_notes_uuid` are typed `uuid` and required/non-nullable in both model and source.
- Four source UUID columns are typed `string` in the model: `ecocode_system.ecocode_system_uuid`, `rdb_system.rdb_system_uuid`, `taxa_synonyms.synonym_uuid`, and `taxonomic_order_system.taxonomic_order_system_uuid`.
- Thirteen UUID source columns are omitted from modelled entities: `citation.biblio_uuid`, `dataset.dataset_uuid`, `geochronology.geochron_uuid`, `master_dataset.master_set_uuid`, `method.method_uuid`, `property_type.uuid`, `relative_ages.relative_age_uuid`, `sample_group.sample_group_uuid`, `site.site_uuid`, `value_class.value_class_uuid`, `value_qualifier.qualifier_uuid`, `value_qualifier_symbol.qualifier_uuid`, and `value_type.value_type_uuid`.
- `sample` has no UUID column in the source. Its model unique set is `[sample_group_id, sample_name]`, and it declares no explicit `identity_tracking` or `reconciliation` value.

### Review notes

- SIMS records a provider-supplied UUID as a Source Identity value for the entity's Source Scope. It does not adopt the provider UUID as the SIMS tracked UUID; SIMS mints its own tracked UUID. See FR-6 and FR-7 in the SIMS requirements and the UUID intake rule in the SIMS design.
- SIMS keeps provider keys independently of whether the consuming system stores them (FR-9), and it distinguishes provider keys from business keys and authority keys (FR-5). A provider UUID is a provider key. Target-side `unique_sets` do not describe a provider's source business key.
- The `accept_uuid` field in the SIMS `config/identity_policy.yml` is described in the SIMS design as legacy behavior and is not part of the target identity contract. Do not use it to decide whether a provider UUID can be recorded.
- A provider UUID is not a SEAD `public_id`. The `public_id` names the target column and holds the SEAD ID; the provider UUID identifies the provider's own record. Keep the two separate.
- A provider UUID can be a source identity when the provider guarantees that it remains stable across resubmissions. The project's Business Key and SIMS source identity policy describe that use; a target unique set does not.

### Next steps

- [ ] **Decision needed:** Identify which entities receive provider UUIDs and whether each value stays stable across resubmissions.
- [ ] **Decision needed:** Define which key governs when a provider UUID and natural key disagree.
- [ ] Define how stable provider UUIDs are represented in the project's Business Key and SIMS source identity policy. Keep provider matching separate from target `unique_sets`.
- [ ] Decide whether the omitted source UUID columns belong in the model and whether they are business keys or source identities.
- [ ] **Decision needed:** Confirm whether the four UUID columns typed as `string` are intended as UUIDs; align their types with `columns.csv`.
- [ ] Align the model's `data_provider_uuid` and `submission_uuid` requiredness/nullability with the source columns and intended project workflow. Confirm any unique-key decisions separately; `columns.csv` does not report unique constraints.
- [ ] Resolve sample resubmission behavior as part of the post-MVP work in section 5. Keep `sample.unique_sets` and its tracking policy unchanged until that behavior is agreed.

### References

- [Target Model Guide](../../../TARGET_MODEL_GUIDE.md)
- SIMS requirements FR-5 to FR-11, and the Identity Intake Rules in the SIMS design (`sead_authority_service/docs/SIMS/DESIGN.md`).

## 13. Deployed ID generators and locking contract (historical snapshot)

This section records the staging audit captured on 2026-10-17. It has not been refreshed for model version 2.8.0: the current aggregate inventory contains 54 children, while this audit only covers the candidates included at the time. `columns.csv` does not include sequence, default, trigger, or lock information and cannot refresh these results. Do not treat the statuses below as current eligibility for deployment-time ID allocation.

### Method

- Command: `python scripts/review_staging_id_generators.py resources/target_models/sead_standard_model.yml --schema public`.
- Targets: the aggregate-child candidates present in the model during the 2026-10-17 audit; this is not the complete version 2.8.0 inventory in section 11.
- Environment: `sead_staging` on PostgreSQL 18.6, schema `public`, captured 2026-10-17.
- The audit used a `default_transaction_read_only=on` session and did not call `nextval`. The source database was not modified.
- A disposable database (`shifter_phase1_clone_20261017`) was created for sequence and lock checks and dropped afterwards. The `sead_staging` database itself was not changed.

### Schema resolution

The deployed staging database contains the same table names in two schemas: `public` and `clearing_house`. The model's `target_table` values are unqualified, so an unscoped audit reports `ambiguous_relation` for all 40 candidates. That is an explicit failure result, not a generator result.

- `public` holds the live data (for example `tbl_abundances`, about 233,600 rows) and 161 sequences.
- `clearing_house` holds mostly unanalyzed or empty copies and 17 sequences.

The audit results below are scoped to `public`, which is the default search path. Phase 2 must either qualify `target_table` values or pin the deployment `search_path`; otherwise the ambiguity remains.

### Generator results

Statuses use the audit's codes: `supported`, `manual_review`, `unsupported`.

| Entity | Qualified relation | Generator | Cache | Status | Reason |
| --- | --- | --- | --- | --- | --- |
| `abundance` | `public.tbl_abundances` | serial | 1 | supported | - |
| `abundance_modification` | `public.tbl_abundance_modifications` | serial | 1 | supported | - |
| `abundance_property` | `public.tbl_abundance_properties` | serial | 1 | supported | - |
| `analysis_boolean_value` | `public.tbl_analysis_boolean_values` | serial | 1 | supported | - |
| `analysis_categorical_value` | `public.tbl_analysis_categorical_values` | serial | 1 | supported | - |
| `analysis_dating_range` | `public.tbl_analysis_dating_ranges` | serial | 1 | supported | - |
| `analysis_entity` | `public.tbl_analysis_entities` | serial | 1 | supported | - |
| `analysis_identifier` | `public.tbl_analysis_identifiers` | serial | 1 | supported | - |
| `analysis_integer_range` | `public.tbl_analysis_integer_ranges` | serial | 1 | supported | - |
| `analysis_integer_value` | `public.tbl_analysis_integer_values` | serial | 1 | supported | - |
| `analysis_note` | `public.tbl_analysis_notes` | serial | 1 | supported | - |
| `analysis_numerical_range` | `public.tbl_analysis_numerical_ranges` | serial | 1 | supported | - |
| `analysis_numerical_value` | `public.tbl_analysis_numerical_values` | serial | 1 | supported | - |
| `analysis_taxon_count` | `public.tbl_analysis_taxon_counts` | serial | 1 | supported | - |
| `analysis_value` | `public.tbl_analysis_values` | serial | 1 | supported | - |
| `analysis_value_dimension` | `public.tbl_analysis_value_dimensions` | serial | 1 | supported | - |
| `ecocode` | `public.tbl_ecocodes` | serial | 1 | supported | - |
| `feature_property` | `public.tbl_feature_properties` | serial | 1 | supported | - |
| `geochronology` | `public.tbl_geochronology` | serial | 1 | supported | - |
| `rdb` | `public.tbl_rdb` | serial | 1 | supported | - |
| `relative_dating` | `public.tbl_relative_dates` | serial | 1 | supported | - |
| `sample_alt_ref` | `public.tbl_sample_alt_refs` | serial | 1 | supported | - |
| `sample_colour` | `public.tbl_sample_colours` | serial | 1 | supported | - |
| `sample_coordinate` | `public.tbl_sample_coordinates` | serial | 1 | supported | - |
| `sample_description` | `public.tbl_sample_descriptions` | serial | 1 | supported | - |
| `sample_dimension` | `public.tbl_sample_dimensions` | serial | 1 | supported | - |
| `sample_group_coordinate` | `public.tbl_sample_group_coordinates` | serial | 1 | supported | - |
| `sample_group_dimension` | `public.tbl_sample_group_dimensions` | serial | 1 | supported | - |
| `sample_group_note` | `public.tbl_sample_group_notes` | serial | 1 | supported | - |
| `sample_group_reference` | `public.tbl_sample_group_references` | serial | 1 | supported | - |
| `sample_horizon` | `public.tbl_sample_horizons` | serial | 1 | supported | - |
| `sample_location` | `public.tbl_sample_locations` | serial | 1 | supported | - |
| `sample_note` | `public.tbl_sample_notes` | serial | 1 | supported | - |
| `site_natgridref` | `public.tbl_site_natgridrefs` | serial | 1 | supported | - |
| `site_property` | `public.tbl_site_properties` | serial | 1 | supported | - |
| `taxa_common_names` | `public.tbl_taxa_common_names` | serial | 1 | supported | - |
| `taxa_measured_attributes` | `public.tbl_taxa_measured_attributes` | serial | 1 | supported | - |
| `taxa_synonyms` | `public.tbl_taxa_synonyms` | serial | 1 | supported | - |
| `taxonomic_order` | `public.tbl_taxonomic_order` | serial | 1 | supported | - |
| `value_type_item` | `public.tbl_value_type_items` | none | - | unsupported | `missing_id_generator` |

- Every supported candidate uses a `nextval` default, increment 1, no cycle, `CACHE 1`, no identity mode, and no enabled INSERT trigger.
- `value_type_item` has no default, no identity mode, and no owned sequence. It cannot receive a deployment-time ID from the target schema as deployed. Keep it disabled for deployment-time allocation until a new ID generator is agreed.

### Locking and synchronization contract

- Lock the union of child-allocation tables and SIMS sequence-synchronization tables by qualified name, in sorted order, with `SHARE ROW EXCLUSIVE` before reading table maxima or changing sequences. Hold the locks through insertion. This matches the current `_render_sequence_synchronization` behavior for SIMS tables.
- `SHARE ROW EXCLUSIVE` conflicts with the `ROW EXCLUSIVE` lock that an insert takes, so it blocks competing writers.
- Table locks do not serialize direct `nextval` calls. Supported sequences must keep `CACHE 1`, and the release workflow must exclude concurrent writes and independent sequence allocation on affected tables. A candidate whose sequence uses a larger cache is unsupported rather than synchronized.
- Phase 2 and Phase 3 inputs: `GENERATED ALWAYS` columns need `OVERRIDING SYSTEM VALUE` for explicit SIMS IDs. No current candidate uses `GENERATED ALWAYS`, and no candidate has an enabled INSERT trigger. Any future candidate that does must be reviewed before it is enabled.

### Disposable clone check

Setup in the disposable database: `tbl_abundance_modifications (abundance_modification_id serial primary key, abundance_id bigint not null)` with one explicit row at ID 100 and its sequence still at `last_value = 1, is_called = false`.

| Step | Result |
| --- | --- |
| Session A: `BEGIN; LOCK TABLE ... IN SHARE ROW EXCLUSIVE MODE;` then read `max(abundance_modification_id)` | `old_max = 100` |
| Session A: `setval(sequence, 100, true)` then `nextval(sequence)` | `allocated = 101`, above the old maximum |
| Session B while A holds the lock: `SET lock_timeout = '1500ms'; LOCK TABLE ... IN ROW EXCLUSIVE MODE` | `ERROR: canceling statement due to lock timeout` (exit status 3) |
| Session B retry after A commits: lock and `INSERT` | Insert succeeds; the row receives the next sequence value |
| Final clone state | 2 rows, `max(abundance_modification_id) = 102` |
| `GENERATED ALWAYS` probe without override | `ERROR: cannot insert a non-DEFAULT value into column "probe_id"` |
| `GENERATED ALWAYS` probe with `OVERRIDING SYSTEM VALUE` | Insert succeeds with the explicit ID |

The clone confirms that synchronizing a stale sequence under `SHARE ROW EXCLUSIVE` yields an unused ID and blocks a competing writer, and that explicit IDs require the identity override.

The target-model review is still in progress. Confirm the remaining role and requiredness decisions, including bridge entities. Re-run the staging ID-generator audit for the current aggregate inventory before treating any candidate as eligible for deployment-time allocation.
