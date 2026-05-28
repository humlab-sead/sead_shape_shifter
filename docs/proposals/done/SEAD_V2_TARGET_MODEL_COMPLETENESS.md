# Proposal: Complete SEAD v2 Target Model Review

## Status

- Current state: review complete and accepted on the current branch
- Scope: classify remaining SEAD v2 target-model gaps, define the intended completeness boundary for the shared SEAD model, and document the metadata-boundary comparison with `SeadSchema`
- Decision goal: define a near-complete, provider-independent SEAD target model while keeping project-specific Shape Shifter configurations as curated subsets of that larger model

## Tracked Issues

This proposal now carries the detailed scope for these follow-up issues:

- Issue 5: complete the SEAD v2 target-model completeness review
- Issue 6: compare the SEAD target model with the older `SeadSchema` live-schema approach

Current issue state on this branch:

- Issue 5: resolved on the current branch; the reassessment decisions are implemented and the out-of-scope shared-model candidates are recorded explicitly
- Issue 6: resolved on the current branch; the accepted target-model versus `SeadSchema` comparison and recommendation now live in this document

## Summary

The previous completeness note was no longer reliable.

It mixed historical expansion plans with current-state claims and overstated implemented coverage. A direct check against [resources/target_models/sead_superset_model.yml](../../../resources/target_models/sead_superset_model.yml) shows a verified surface of 61 top-level entities in the current model, not the larger phase-based inventory described in the older draft.

Issue 5 should therefore be treated as a review and decision task first.

The immediate job is not to narrow the model to one provider, one project, or one import slice. It is to produce a usable completeness review so later model edits are driven by the current SEAD schema surface and by shared SEAD concepts rather than by an outdated wish list.

The intended target is a close-to-complete SEAD target model.

That shared model should contain almost all current SEAD tables and concepts, independent of any one data provider or data type.

Individual Shape Shifter projects can then use manually curated subsets of that larger target model.

The filtered Issue 6 snapshots are still useful, but they are only one evidence source for the metadata-boundary comparison. They are not the full completeness boundary for the SEAD target model.

## Verified Current Coverage

The current target model already covers a substantial core for Delivery 1 and early SEAD ingestion work.

Verified entity surface in [resources/target_models/sead_superset_model.yml](../../../resources/target_models/sead_superset_model.yml):

- Core and provenance: `location`, `location_type`, `site`, `site_location`, `sample_group`, `sample`, `method`, `dataset`, `master_dataset`, `project`, `project_type`, `project_stage`, `citation`, `contact`, `contact_type`, `dataset_contact`
- Sample and coordinate support: `sample_description_type`, `sample_description`, `sample_type`, `dimension`, `coordinate_method_dimension`, `coordinate_system`, `sample_coordinate`, `alt_ref_type`, `sample_alt_ref`, `sample_dimension`
- Analysis and abundance: `analysis_entity`, `abundance`, `abundance_element`, `abundance_element_group`, `abundance_modification`, `modification_type`, `abundance_property`, `identification_level`, `abundance_ident_level`
- Dating: `age_type`, `relative_age_type`, `chronology`, `dating_uncertainty`, `dating_material`, `relative_ages`, `relative_dating`, `geochronology`, `dating_lab`
- Taxonomy and features: `taxa_tree_master`, `taxa_common_names`, `taxa_synonyms`, `taxa_measured_attributes`, `rdb_system`, `rdb_code`, `rdb`, `feature_type`, `feature`, `sample_feature`
- Classification and measurement support: `method_group`, `data_type`, `unit`, `site_type_group`, `site_type`

This is enough to support the current change-request work, but it is not yet a near-complete SEAD-wide target model.

## Problem

The remaining completeness problem now has three separate parts that should not be conflated.

### 1. Documentation Gaps

The old review document drifted away from the actual YAML model.

Examples:

- it reported a larger entity count than the current file contains
- it described several planned entity additions as already present
- it mixed implementation status, Arbodat-specific needs, and general SEAD backlog into one inventory

That makes it hard to tell whether a gap is real, already solved, or only proposed.

It also makes it hard to tell whether the document is describing the shared SEAD target model or only one project's current subset.

### 2. Target-Model Gaps

Several entity families still appear to be missing from the current model and should remain under active review.

Verified missing candidates from the current YAML include:

- Spatial and site-location support: `sample_group_coordinate`, `site_natgridref`
- Feature and site metadata: `feature_property`, `feature_property_type`, `site_property`, `site_property_type`
- Sample metadata: `sample_horizon`, `sample_location`, `sample_location_type`, `sample_note`
- Sample-group metadata: `sample_group_dimension`, `sample_group_note`, `sample_group_reference`
- Generic analysis values: `analysis_value`, `analysis_categorical_value`, `analysis_boolean_value`, `analysis_integer_value`, `analysis_numerical_value`, `analysis_date_range`, `analysis_note`, `analysis_identifier`

This list is useful, but it still needs to be grouped into first-slice work, broader SEAD-wide follow-up, and derived or operational schema artifacts that do not need first-class target-model entities.

The current branch has now resolved the earlier deferred shared-model candidates that survived review: `colour` and `sample_colour` are modeled explicitly, `project_type` plus `project_stage` are modeled as controlled vocabularies referenced by `project`, `coordinate_system` is kept in the shared superset, and the taxonomy and ecology slice is now modeled through `taxa_synonyms`, `taxa_measured_attributes`, `rdb_system`, `rdb_code`, and `rdb`.

The branch also records two negative Issue 5 decisions: `dating_period` and `natural_region*` are treated as Arbodat-specific and are not being promoted into the shared SEAD target model.

For Issue 5, keep this broader backlog visible.

For Issue 6, use the filtered `SeadSchema` snapshots as one narrower evidence surface for the metadata-boundary comparison.

On that narrower surface, the strongest first implementation slices are:

- sample and sample-group context additions such as `sample_group_coordinate`, `sample_horizon`, `sample_location`, `sample_location_type`, `sample_note`, `sample_group_dimension`, `sample_group_note`, and `sample_group_reference`
- site and feature property patterns such as `site_natgridref`, `feature_property`, `feature_property_type`, `site_property`, and `site_property_type`
- the generic analysis-value family such as `analysis_value`, typed analysis values, `analysis_note`, and `analysis_identifier`

The current filtered snapshots do not support using `coordinate_system`, `dating_period`, `natural_region*`, `sample_colour`, or `colour` to close Issue 6.

That does not mean all of those concepts belong in the same final category. On the current branch, the broader Issue 5 review keeps `coordinate_system` in the shared target model, while `dating_period` and `natural_region*` are treated as Arbodat-specific rather than shared SEAD-superset requirements.

### 3. Schema-Boundary Decisions

Some gaps may still need special handling, but the default assumption should now be inclusion in the shared SEAD target model unless there is a strong reason to classify the schema surface as derived, operational, or non-domain metadata.

Examples called out in earlier work include `natural_region`, `cultural_group`, `archaeological_period`, and related region-specific concepts. Those may be:

- real core SEAD gaps
- broad shared-model concerns that should be scheduled later rather than discarded
- derived or operational schema concerns that should not be promoted into the shared target model as first-class entities

Issue 5 is not complete until those categories are separated explicitly.

### 4. Metadata-Boundary Comparison

Issue 6 should not be tracked as a separate, context-free note.

It depends directly on the same review work as Issue 5 because the practical question is not only "what is missing from the target model" but also "which schema concepts belong in the near-complete shared SEAD model and which are only operational artifacts".

The current change-request ingester uses the target model in [resources/target_models/sead_superset_model.yml](../../../resources/target_models/sead_superset_model.yml). The older `sead` ingester uses `SeadSchema` in [ingesters/sead/metadata.py](../../../ingesters/sead/metadata.py), which derives metadata from the live SQL schema.

Before more follow-up work grows around the current metadata boundary, this document should make the tradeoffs between those two approaches explicit.

## Gap Classification

The next useful shape for this review is a prioritized decision document.

### High Priority

These gaps are the strongest candidates for near-term target-model work because they are both missing from the current target model and supported by the filtered Issue 6 comparison surface.

- `sample_group_coordinate`, `site_natgridref`
- `sample_horizon`, `sample_location`, `sample_location_type`
- `feature_property`, `feature_property_type`
- `analysis_value` and its typed value family
- `analysis_note`, `analysis_identifier`

### Medium Priority

These gaps matter, but they should follow only after the high-priority spatial, physical-context, and analysis-value gaps are clarified.

- `site_property`, `site_property_type`
- `sample_note`
- `sample_group_dimension`, `sample_group_note`, `sample_group_reference`

### Lower Priority Or Deferred

These gaps remain part of the broader Issue 5 review, but the current filtered Issue 6 evidence does not justify using them as near-term closure items.

- broader SEAD-wide concepts that should be scheduled after the first slices or clarified against the live schema before they are modeled

`abundance_property_type` is no longer kept as a separate target-model candidate in this review. The live schema evidence on the current branch shows `abundance_property` already points to the shared `property_type` table, so a second abundance-only type entity would duplicate the now-implemented property pattern.

`dating_period` and `natural_region*` are also no longer kept as shared-model backlog items in this review. They are treated as Arbodat-specific rather than as required parts of the near-complete SEAD superset.

## Target Model Versus `SeadSchema`

This comparison is the detailed home for Issue 6.

### Source Of Truth

- Target model approach: the YAML model is the explicit source of truth for what Shape Shifter currently understands and validates.
- `SeadSchema` approach: the live SQL schema is the source of truth, which can be attractive for fidelity to a running database but weaker for offline review.

### Drift Risk

- Target model approach: drift risk exists between YAML and the live schema, but the drift is inspectable in version control and can be reviewed deliberately.
- `SeadSchema` approach: drift risk shifts in the other direction because behavior can silently follow whichever schema the runtime database exposes.

### Testability And Offline Reproducibility

- Target model approach: easier to test deterministically because the metadata is file-based, versioned, and available without a live database.
- `SeadSchema` approach: harder to reproduce offline because tests and review depend more directly on a running schema source.

### SEAD-Specific Output Generation

- Target model approach: better for explicit, curated output generation rules when Shape Shifter needs to generate SEAD-specific artifacts from reviewed metadata.
- `SeadSchema` approach: better when the main need is direct reflection of the current database shape rather than curated modeling decisions.

### Operational Dependency

- Target model approach: lower operational dependency during planning, validation, and review.
- `SeadSchema` approach: tighter dependency on live schema access and on the operational environment matching expectations.

### Review Method

For Issue 6, the comparison was performed against the filtered offline snapshots in [docs/proposals/CHANGE_REQUEST_INGESTER/filtered_import_tables.csv](../CHANGE_REQUEST_INGESTER/filtered_import_tables.csv) and [docs/proposals/CHANGE_REQUEST_INGESTER/filtered_import_columns.csv](../CHANGE_REQUEST_INGESTER/filtered_import_columns.csv), not against an unfiltered live schema dump.

That matters because this review is intended to support a stable target-model decision, not to mirror every runtime table that may exist in a live SEAD database.

The excluded families and tables listed in the Issue 6 plan are therefore part of the method, not just post-hoc cleanup.

### Recommendation

Keep the target model as the current source of truth for `sead_change_request` planning, validation, and artifact generation.

Use the `SeadSchema` comparison as a review tool and as a prompt for finding real metadata gaps, not as a reason to switch the change-request ingester back to live-schema-driven behavior without a separate architecture decision.

## Issue 6 Completion Plan

Issue 6 should now be finished as a short, explicit review process rather than as more open-ended exploration.

### Working Inputs

Use these files as the offline baseline for the live-schema side of the comparison:

- [docs/proposals/CHANGE_REQUEST_INGESTER/import_tables.csv](../CHANGE_REQUEST_INGESTER/import_tables.csv)
- [docs/proposals/CHANGE_REQUEST_INGESTER/import_columns.csv](../CHANGE_REQUEST_INGESTER/import_columns.csv)

The filtered working set initialized on the current branch is:

- [docs/proposals/CHANGE_REQUEST_INGESTER/filtered_import_tables.csv](../CHANGE_REQUEST_INGESTER/filtered_import_tables.csv)
- [docs/proposals/CHANGE_REQUEST_INGESTER/filtered_import_columns.csv](../CHANGE_REQUEST_INGESTER/filtered_import_columns.csv)

These files are snapshots of the outputs from `SchemaService.get_sead_tables()` and `SchemaService.get_sead_columns()` in [ingesters/sead/metadata.py](../../../ingesters/sead/metadata.py).

For this review, ignore table families that should not drive target-model decisions:

- `tbl_ceramic*` because that path is superseded by the `tbl_analysis_values` family
- `tbl_isotope*` because that path is superseded by the `tbl_analysis_values` family
- `tbl_dendro*` because that path is superseded by the `tbl_analysis_values` family
- `tbl_mcr*` because those are live derived tables rather than imported source tables
- `tbl*_images` because image tables are not imported in the current scope

Also ignore these exact tables for Issue 6:

- `tbl_image_types`
- `tbl_colours`
- `tbl_sample_colours`
- `tbl_aggregate_datasets`
- `tbl_aggregate_order_types`
- `tbl_aggregate_sample_ages`
- `tbl_aggregate_samples`

These tables are intentionally outside the current target-model boundary review for `sead_change_request`.

For column-level review, also ignore `date_updated`.

It is a legacy update timestamp and should not influence target-model boundary decisions.

### Step-By-Step Plan

1. Build a filtered live-schema working set from [docs/proposals/CHANGE_REQUEST_INGESTER/import_tables.csv](../CHANGE_REQUEST_INGESTER/import_tables.csv) and [docs/proposals/CHANGE_REQUEST_INGESTER/import_columns.csv](../CHANGE_REQUEST_INGESTER/import_columns.csv).
Remove the deprecated and out-of-scope table families listed above before doing any target-model comparison.
For the column snapshot, also remove `date_updated` before doing any entity-level comparison.

Current branch status: this step is initialized in [docs/proposals/CHANGE_REQUEST_INGESTER/filtered_import_tables.csv](../CHANGE_REQUEST_INGESTER/filtered_import_tables.csv) and [docs/proposals/CHANGE_REQUEST_INGESTER/filtered_import_columns.csv](../CHANGE_REQUEST_INGESTER/filtered_import_columns.csv).

2. Group the remaining live-schema tables into comparison buckets rather than reviewing them one by one.
Use practical buckets such as core provenance, site and location, sample and sample group, feature context, chronology and dating, taxonomy, abundance, analysis values, project metadata, and lookup tables.

3. Map each filtered live-schema bucket to the current target-model entities in [resources/target_models/sead_superset_model.yml](../../../resources/target_models/sead_superset_model.yml).
For each bucket, record one of four outcomes: already covered, partially covered, missing from the target model, or intentionally out of scope for the shared model.

4. Use [docs/proposals/CHANGE_REQUEST_INGESTER/filtered_import_columns.csv](../CHANGE_REQUEST_INGESTER/filtered_import_columns.csv) to check whether the apparent table-level gaps are real entity gaps or only column-level differences.
Do not propose a new target-model entity until the filtered column snapshot shows that the live-schema table carries a distinct business concept rather than only extra operational columns such as legacy XML names or analysis-value-specific structure.

5. Separate true shared-model candidates from derived, operational, or legacy-only schema artifacts.
If a missing concept only exists in deprecated table families, only exists in derived tables, or is tightly tied to a legacy method-specific structure, keep it out of the shared target-model gap list.

6. Rewrite the current candidate-gap lists in this document against the filtered CSV evidence.
Promote only those gaps that still survive the deprecated-table filter and that map to an active imported concept in the remaining live-schema set.

7. Update the `Target Model Versus SeadSchema` comparison with one explicit subsection on review method.
State that the comparison was performed against filtered offline snapshots of `get_sead_tables()` and `get_sead_columns()`, not against an unfiltered live schema dump.

8. Produce a short decision table in this document for the remaining open Issue 6 scope.
Each row should name the live-schema concept or table family, the matching target-model entity if one exists, the decision (`keep in target model`, `candidate target-model addition`, `later shared-model candidate`, or `ignore for Issue 6`), and a one-line reason.

9. Close Issue 6 only after the document contains both parts of the final outcome.
The first part is the filtered comparison method. The second part is a decision-ready list of the live-schema concepts that still justify target-model follow-up.

### Filtered Comparison Buckets

The filtered CSV snapshots are now far enough along to support a bucketed comparison pass.

This is the missing bridge between the filtered inputs and the final Issue 6 decision table.

The current review should use these buckets.

| Comparison bucket | Filtered live-schema surface | Current target-model match | Current outcome | Review note |
| --- | --- | --- | --- | --- |
| Core provenance and submission | `tbl_projects`, `tbl_datasets`, `tbl_dataset_masters`, `tbl_dataset_contacts`, `tbl_contacts`, `tbl_contact_types`, `tbl_biblio`, `tbl_methods`, `tbl_method_groups`, `tbl_data_types` | `project`, `dataset`, `master_dataset`, `dataset_contact`, `contact`, `contact_type`, `citation`, `method`, `method_group`, `data_type` | already covered | This bucket largely confirms that the current target model already covers the main provenance backbone used by `sead_change_request`. |
| Site and location core | `tbl_sites`, `tbl_site_locations`, `tbl_locations`, `tbl_location_types`, `tbl_site_types`, `tbl_site_type_groups` | `site`, `site_location`, `location`, `location_type`, `site_type`, `site_type_group` | already covered | The filtered table set supports the current site and location core rather than exposing a missing top-level site model. |
| Site and location extensions | `tbl_site_natgridrefs`, `tbl_site_other_records`, `tbl_site_references` | no direct entity for `site_natgridref`; partial generic coverage through `site` and `site_location` | partially covered | This bucket is where genuine site-context follow-up starts. `tbl_site_natgridrefs` looks like the clearest current candidate. |
| Sample and sample-group core | `tbl_sample_groups`, `tbl_physical_samples`, `tbl_sample_types`, `tbl_sample_descriptions`, `tbl_sample_description_types`, `tbl_sample_dimensions`, `tbl_sample_coordinates`, `tbl_sample_alt_refs`, `tbl_dimensions`, `tbl_coordinate_method_dimensions` | `sample_group`, `sample`, `sample_type`, `sample_description`, `sample_description_type`, `sample_dimension`, `sample_coordinate`, `alt_ref_type`, `sample_alt_ref`, `dimension`, `coordinate_method_dimension` | already covered | The filtered snapshots reinforce that the current model already captures the main sample, description, dimension, and coordinate workflow. |
| Sample and sample-group context extensions | `tbl_sample_group_coordinates`, `tbl_sample_group_dimensions`, `tbl_sample_group_notes`, `tbl_sample_group_references`, `tbl_sample_horizons`, `tbl_sample_locations`, `tbl_sample_location_types`, `tbl_sample_notes` | no direct entities for most of this surface | partially covered | This is one of the strongest follow-up buckets because the remaining gaps are active imported concepts, not deprecated method-specific leftovers. |
| Feature context and generic properties | `tbl_features`, `tbl_feature_types`, `tbl_physical_sample_features`, `tbl_feature_properties`, `tbl_site_properties`, `tbl_property_types` | `feature`, `feature_type`, `sample_feature`; no direct `feature_property`, `site_property`, or shared property-type entity | partially covered | The filtered columns support a reusable property pattern rather than isolated one-off tables, which strengthens the case for a deliberate property-model follow-up. |
| Chronology and dating | `tbl_chronologies`, `tbl_geochronology`, `tbl_dating_labs`, `tbl_dating_material`, `tbl_dating_uncertainty`, `tbl_age_types`, `tbl_relative_age_types`, `tbl_relative_ages`, `tbl_relative_dates` | `chronology`, `geochronology`, `dating_lab`, `dating_material`, `dating_uncertainty`, `age_type`, `relative_age_type`, `relative_ages`, `relative_dating` | already covered | For Issue 6, this bucket mostly confirms current coverage. The earlier `dating_period` candidate is not supported by the filtered snapshot and should stay out of this review surface. |
| Abundance and identification | `tbl_abundances`, `tbl_abundance_elements`, `tbl_abundance_modifications`, `tbl_modification_types`, `tbl_identification_levels`, `tbl_abundance_ident_levels`, `tbl_abundance_properties` | `abundance`, `abundance_element`, `abundance_modification`, `modification_type`, `identification_level`, `abundance_ident_level`, `abundance_property` | already covered | This bucket mostly validates the current abundance model. The remaining question is whether the shared property-type surface should later be modeled more explicitly. |
| Analysis values and typed value families | `tbl_analysis_entities`, `tbl_analysis_values`, `tbl_analysis_boolean_values`, `tbl_analysis_categorical_values`, `tbl_analysis_integer_values`, `tbl_analysis_numerical_values`, `tbl_analysis_dating_ranges`, `tbl_analysis_notes`, `tbl_analysis_identifiers`, `tbl_analysis_value_dimensions`, `tbl_analysis_taxon_counts` | `analysis_entity` exists; the generic analysis-value family does not | partially covered | This is the clearest model gap in the filtered snapshots and the strongest candidate for future target-model growth after the current review closes. |
| Taxonomy and ecology extensions | `tbl_taxa_common_names`, `tbl_taxa_synonyms`, `tbl_taxa_measured_attributes`, `tbl_rdb`, `tbl_rdb_codes`, `tbl_rdb_systems`, `tbl_ecocodes`, `tbl_ecocode_groups`, `tbl_ecocode_systems` | `taxa_tree_master`, `taxa_common_names`, `taxa_synonyms`, `taxa_measured_attributes`, `rdb_system`, `rdb_code`, and `rdb`; the ecocode family is still outside the current model | partially covered | The branch now models the main taxonomy and Red Data Book slice as shared SEAD concepts, while the wider ecocode surface stays outside the current implementation boundary. |
| Project classification and support lookups | `tbl_project_types`, `tbl_project_stages` plus broad support tables such as `tbl_activity_types`, `tbl_record_types`, `tbl_languages`, `tbl_seasons` | `project`, `project_type`, and `project_stage`; most support lookups still have no direct entity need in the current model | already covered | The project classification lookups are now modeled explicitly, while the broader support-table surface can stay outside the current target-model boundary until it has clearer shared-model value. |

### Done Condition For This Plan

Issue 6 is ready to close when this document makes all of the following explicit:

- the comparison input came from the CSV snapshots of `get_sead_tables()` and `get_sead_columns()`
- deprecated `tbl_ceramic*`, `tbl_isotope*`, `tbl_dendro*`, `tbl_mcr*`, and `tbl*_images` families were excluded from the decision surface
- `tbl_image_types`, `tbl_colours`, `tbl_sample_colours`, `tbl_aggregate_datasets`, `tbl_aggregate_order_types`, `tbl_aggregate_sample_ages`, and `tbl_aggregate_samples` were also excluded from the Issue 6 review surface
- `date_updated` was excluded from the column-level review surface
- the remaining live-schema concepts were mapped against the current target model
- the document clearly separates shared-model follow-up from legacy, derived, or operational-only schema artifacts
- the final recommendation still keeps the target model as the active metadata boundary for `sead_change_request`

## Issue 6 Decision Table

This table applies the Issue 6 plan to the current CSV snapshots.

It uses the filtered `get_sead_tables()` and `get_sead_columns()` outputs in [docs/proposals/CHANGE_REQUEST_INGESTER/filtered_import_tables.csv](../CHANGE_REQUEST_INGESTER/filtered_import_tables.csv) and [docs/proposals/CHANGE_REQUEST_INGESTER/filtered_import_columns.csv](../CHANGE_REQUEST_INGESTER/filtered_import_columns.csv), derived from the raw snapshots after excluding the deprecated and out-of-scope table families listed above and the legacy `date_updated` column from column-level review.

| Comparison bucket | Live-schema concept or table family | Current target-model state | Decision | Reason |
| --- | --- | --- | --- | --- |
| Analysis values and typed value families | `tbl_analysis_values` plus typed value tables such as `tbl_analysis_boolean_values`, `tbl_analysis_categorical_values`, `tbl_analysis_integer_values`, `tbl_analysis_numerical_values`, `tbl_analysis_notes`, and `tbl_analysis_identifiers` | `analysis_entity` exists, but the generic analysis-value family is not modeled as target-model entities | candidate target-model addition | This is the clearest active gap in the filtered CSV set and the intended replacement path for deprecated method-specific tables such as `tbl_ceramic*`, `tbl_isotope*`, and `tbl_dendro*`. |
| Sample and sample-group context extensions | `tbl_sample_group_coordinates`, `tbl_sample_locations`, `tbl_sample_location_types`, `tbl_site_natgridrefs` | `sample_coordinate`, `site_location`, `location`, and `location_type` exist, but these more specific imported location concepts are absent | candidate target-model addition | These tables remain in the filtered import set and represent real spatial-context concepts rather than deprecated method-specific structure. |
| Sample and sample-group context extensions | `tbl_sample_horizons`, `tbl_sample_notes` | `sample`, `sample_description`, and `sample_dimension` exist, but these sample-context concepts are not modeled explicitly | candidate target-model addition | These are active imported tables that add material sample context beyond the current generic description coverage. |
| Sample and sample-group context extensions | `tbl_sample_group_dimensions`, `tbl_sample_group_notes`, `tbl_sample_group_references` | `sample_group` exists, but the grouped-dimension, note, and reference surfaces are absent | candidate target-model addition | These are active imported concepts in the filtered CSV set and are a better fit for grouped sampling context than ad hoc free-text extensions. |
| Feature context and generic properties | `tbl_feature_properties`, `tbl_site_properties`, with shared lookup support from `tbl_property_types` | `feature` and `site` exist, but the generic property pattern is not modeled in the current target model | candidate target-model addition | The column snapshots show a consistent property pattern built from `property_type_id` plus `property_value`, which makes this a reusable active concept rather than a one-off legacy table. |
| Project classification and support lookups | `tbl_project_types`, `tbl_project_stages` | `project_type` and `project_stage` are now modeled explicitly and linked from `project` | keep in target model | The branch now models these controlled vocabularies directly, which removes them from the deferred lookup backlog for the shared SEAD superset. |
| Taxonomy and ecology extensions | `tbl_taxa_synonyms`, `tbl_taxa_measured_attributes`, `tbl_rdb`, `tbl_rdb_codes`, `tbl_rdb_systems` | `taxa_synonyms`, `taxa_measured_attributes`, `rdb_system`, `rdb_code`, and `rdb` are now modeled explicitly | keep in target model | The current branch now treats this taxonomy and Red Data Book slice as part of the shared SEAD superset rather than as a deferred extension candidate. |
| Excluded review surface | `tbl_image_types`, `tbl_colours`, `tbl_sample_colours`, `tbl_aggregate_datasets`, `tbl_aggregate_order_types`, `tbl_aggregate_sample_ages`, `tbl_aggregate_samples` | Present in the raw CSV snapshots, but explicitly excluded from the Issue 6 review surface | ignore for Issue 6 | These tables are intentionally outside the current target-model boundary review for `sead_change_request`. |
| Excluded review surface | `tbl_ceramic*`, `tbl_isotope*`, `tbl_dendro*` | Present in the raw CSV snapshots, but explicitly excluded from the Issue 6 review surface | ignore for Issue 6 | These families are superseded by the `tbl_analysis_values` path and should not drive new target-model decisions. |
| Excluded review surface | `tbl_mcr*` | Present in the raw CSV snapshots, but explicitly excluded from the Issue 6 review surface | ignore for Issue 6 | These are live derived tables rather than imported source tables. |
| Excluded review surface | `tbl*_images` | Present in the raw CSV snapshots, but explicitly excluded from the Issue 6 review surface | ignore for Issue 6 | Image tables are not imported in the current scope. |
| Lower Priority Or Deferred | Candidate families mentioned earlier in this proposal but not present in the filtered CSV snapshots, including `coordinate_system`, `dating_period`, and `natural_region*` | `coordinate_system` is now modeled explicitly; `dating_period` and `natural_region*` are intentionally out of scope for the shared superset | ignore for Issue 6 | The filtered offline baseline still does not support using these concepts to close or broaden Issue 6, even though the broader Issue 5 review now keeps `coordinate_system` and rejects the Arbodat-specific candidates. |

## Recommendation

Issues 5 and 6 should be treated as one linked review surface in this proposal.

Issue 5 should be closed only when this review supports an implementation decision rather than just restating a backlog.
Issue 6 should be closed only when this document contains an explicit comparison between the target-model path and the `SeadSchema` path, with a clear recommendation.

The next steps should be:

1. Keep [resources/target_models/sead_superset_model.yml](../../../resources/target_models/sead_superset_model.yml) as the source of truth for current coverage.
2. Use this document to track verified missing areas, verified decisions, and the intended completeness boundary for the shared SEAD model.
3. Separate true shared-model entities from derived or operational schema artifacts before adding more entities.
4. Keep the target model as the active metadata boundary for `sead_change_request` unless a later architecture proposal explicitly changes that decision.
5. Promote the highest-value missing entities into implementation work first without shrinking the broader SEAD-wide completeness backlog to one project's current scope.

## Recommended Follow-Up Order

If follow-up implementation work starts after this review, it should proceed in small slices ordered by change size and reuse value.

These slices are the first tranche of work toward the near-complete SEAD target model. They are not the full completeness inventory.

### 1. Sample And Sample-Group Context First

Tracked by [#447](https://github.com/humlab-sead/sead_shape_shifter/issues/447) and [#448](https://github.com/humlab-sead/sead_shape_shifter/issues/448).

Start with the sample and sample-group context additions that are both clearly supported by the filtered review surface and broadly aligned with the SEAD-wide shared model.

Suggested first slice:

- `sample_horizon`
- `sample_location`
- `sample_location_type`
- `sample_note`
- `sample_group_coordinate`
- `sample_group_dimension`
- `sample_group_note`
- `sample_group_reference`

This slice is a good first step because it extends an existing part of the model rather than introducing a new cross-cutting pattern.

### 2. Site And Feature Property Pattern Second

Tracked by [#449](https://github.com/humlab-sead/sead_shape_shifter/issues/449).

After the sample-context slice, review the shared property pattern for site and feature metadata.

Suggested second slice:

- `feature_property_type`
- `feature_property`
- `site_property_type`
- `site_property`
- `site_natgridref`

This slice is slightly riskier because it introduces a reusable property pattern rather than only adding a few isolated entities.

### 3. Generic Analysis-Value Family Third

Tracked by [#450](https://github.com/humlab-sead/sead_shape_shifter/issues/450).

Treat the analysis-value family as a separate design slice after the simpler context additions are settled.

Suggested third slice:

- `analysis_value`
- `analysis_note`
- `analysis_identifier`
- typed value entities such as boolean, categorical, integer, numerical, and dating-range variants

This slice likely has the highest design impact because it affects how the target model represents flexible typed values across multiple analysis workflows.

### 4. Keep Extensions And Lookups Deferred

Tracked by [#451](https://github.com/humlab-sead/sead_shape_shifter/issues/451).

Use a separate pass for the broader SEAD-wide backlog that does not fit cleanly into the first implementation rounds.

The current branch has already completed that pass for the shared-model candidates that remained after review by promoting `colour`, `sample_colour`, `project_type`, `project_stage`, `coordinate_system`, `taxa_synonyms`, `taxa_measured_attributes`, `rdb_system`, `rdb_code`, and `rdb`.

This pass also records which earlier candidates are not part of the shared superset:

- `dating_period`
- `natural_region*`

The branch also treats `abundance_property_type` as subsumed by the shared `property_type` entity rather than as a separate remaining lookup family.

## Implementation Handoff

When this proposal is used to start model work, each follow-up change should:

- name the exact target-model entities being added
- cite which Issue 6 bucket and decision-table row justified the change
- state whether the slice is part of the shared SEAD superset or only a project-level subset decision
- avoid mixing one bucket's work with another unless the model shape requires it
- keep derived or operational schema artifacts out of the same change set

## Suggested Issue Slices

The follow-up order above can be turned into small tracked issues without reopening the full review.

Use these slices as the default first breakdown.

| Order | Suggested issue title | Target-model scope | Keep out of scope | Done signal |
| --- | --- | --- | --- | --- |
| 1 | [#447 feat(target_model): add sample-context entities](https://github.com/humlab-sead/sead_shape_shifter/issues/447) | `sample_horizon`, `sample_location`, `sample_location_type`, `sample_note` | property-pattern work, analysis-value work, later SEAD-wide backlog slices | The shared target model can represent a major sample-context surface cleanly as part of the broader SEAD superset. |
| 2 | [#448 feat(target_model): add sample-group context entities](https://github.com/humlab-sead/sead_shape_shifter/issues/448) | `sample_group_coordinate`, `sample_group_dimension`, `sample_group_note`, `sample_group_reference` | site and feature properties, analysis-value work, later SEAD-wide backlog slices | The shared target model can represent grouped sampling context with explicit entities tied to `sample_group`. |
| 3 | [#449 feat(target_model): add site and feature property entities](https://github.com/humlab-sead/sead_shape_shifter/issues/449) | `feature_property_type`, `feature_property`, `site_property_type`, `site_property`, `site_natgridref` | sample-context entities already covered by earlier slices, analysis-value work | The shared target model has an explicit reusable property pattern for important site and feature metadata that is still missing from the current YAML. |
| 4 | [#450 feat(target_model): design generic analysis-value family](https://github.com/humlab-sead/sead_shape_shifter/issues/450) | `analysis_value`, `analysis_note`, `analysis_identifier`, typed analysis-value variants | derived method-specific artifacts, project-only subset choices | The shared target model has an agreed shape for generic typed analysis values that can support multiple SEAD data families without forcing provider-specific assumptions into the model. |
| 5 | [#451 proposal(target_model): reassess deferred lookup and extension candidates](https://github.com/humlab-sead/sead_shape_shifter/issues/451) | promote shared candidates such as `coordinate_system`, `taxa_synonyms`, `taxa_measured_attributes`, `rdb`, `rdb_code`, and `rdb_system`; reject Arbodat-specific candidates such as `dating_period` and `natural_region*`; keep abundance properties on the shared `property_type` model | unrelated project-level subset choices and operational-only schema artifacts | The review is done when the branch both promotes the remaining shared SEAD candidates and records which earlier lookup candidates do not belong in the shared superset. |

These issue slices are intentionally narrow.

They preserve the main review decision from Issue 6: use the filtered snapshots to sequence the first slices without treating that comparison surface as the full boundary of the SEAD target model.

## Implementation Plan Table

If this proposal is used as the handoff document for execution, the implementation plan should be read in this order.

| Phase | Focus | Why this comes now | Main risk |
| --- | --- | --- | --- |
| Phase 1 | Sample context | Lowest model-shape risk and strongest fit with existing sample entities | Accidental overlap with later sample-group work |
| Phase 2 | Sample-group context | Extends the same part of the model while keeping the pattern simple | Splitting group-level versus sample-level concepts inconsistently |
| Phase 3 | Site and feature properties | Introduces a reusable pattern after simpler context entities are settled | Over-generalizing the property model too early |
| Phase 4 | Analysis-value family | Highest reuse potential, but also the largest design decision | Pulling too many method-specific assumptions into one generic model |
| Phase 5 | Broader SEAD-wide coverage review | Only after the first cross-cutting gaps are addressed | Mistaking one project's current subset or one filtered comparison surface for the full shared-model boundary |

## GitHub-Ready Issue Drafts

The GitHub-ready issue bodies derived from this proposal are tracked separately in [docs/proposals/SEAD_V2_TARGET_MODEL_FOLLOWUP_ISSUES.md](../SEAD_V2_TARGET_MODEL_FOLLOWUP_ISSUES.md).

The live issues are [#447](https://github.com/humlab-sead/sead_shape_shifter/issues/447), [#448](https://github.com/humlab-sead/sead_shape_shifter/issues/448), [#449](https://github.com/humlab-sead/sead_shape_shifter/issues/449), [#450](https://github.com/humlab-sead/sead_shape_shifter/issues/450), and [#451](https://github.com/humlab-sead/sead_shape_shifter/issues/451).

That file keeps the first implementation slices in a reusable `Problem`, `Solution`, and `Files` format without pretending to be the full SEAD completeness plan.

## Acceptance Criteria

### Issue 5

Issue 5 should count as complete when all of the following are true:

- this review matches the current YAML model rather than a historical expansion plan
- this review states explicitly that the shared target model is intended as a near-complete, provider-independent SEAD superset
- this review distinguishes the shared SEAD target model from project-specific curated subsets
- remaining gaps are grouped into documentation gaps, target-model gaps, and schema-boundary decisions
- the highest-value missing areas are prioritized clearly enough to drive follow-up implementation without collapsing the broader SEAD backlog to one import slice
- the document is useful as a decision input for future model edits without requiring readers to reverse-engineer stale claims

### Issue 6

Issue 6 should count as complete when all of the following are true:

- this document compares the current target-model-driven path with the older `SeadSchema` live-schema path explicitly
- the comparison states that it was run against the filtered CSV snapshots rather than against an unfiltered live schema dump
- the comparison covers source of truth, drift risk, testability, offline reproducibility, SEAD-specific output generation, and operational dependency
- the Issue 6 candidate list is constrained by the filtered review surface without redefining the broader completeness boundary for the SEAD target model
- the recommendation is clear enough to guide future follow-up work without reopening the metadata boundary by accident

## References

- [resources/target_models/sead_superset_model.yml](../../../resources/target_models/sead_superset_model.yml)
- [docs/TARGET_MODEL_GUIDE.md](../../TARGET_MODEL_GUIDE.md)
- [ingesters/sead/metadata.py](../../../ingesters/sead/metadata.py)
- [docs/proposals/SEAD_V2_TARGET_MODEL_FOLLOWUP_ISSUES.md](../SEAD_V2_TARGET_MODEL_FOLLOWUP_ISSUES.md)
- [docs/proposals/CHANGE_REQUEST_INGESTER/DELIVERY_1_FOLLOWUP_CR.md](../CHANGE_REQUEST_INGESTER/DELIVERY_1_FOLLOWUP_CR.md)
- [docs/proposals/CHANGE_REQUEST_INGESTER/DELIVERY_1_FOLLOWUP_ISSUES.md](../CHANGE_REQUEST_INGESTER/DELIVERY_1_FOLLOWUP_ISSUES.md)