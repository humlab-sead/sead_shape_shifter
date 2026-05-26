# Proposal: Complete SEAD v2 Target Model Review

## Status

- Current state: rewritten against the current target model
- Scope: classify remaining SEAD v2 target-model gaps for follow-up work
- Decision goal: identify what is missing in documentation, what is missing in the model, and what needs a schema-boundary decision before more model growth

## Summary

The previous completeness note was no longer reliable.

It mixed historical expansion plans with current-state claims and overstated implemented coverage. A direct check against [resources/target_models/sead_standard_model.yml](../../resources/target_models/sead_standard_model.yml) shows a verified surface of 51 top-level entities in the current model, not the larger phase-based inventory described in the older draft.

Issue 5 should therefore be treated as a review and decision task first.

The immediate job is not to add more entities blindly. It is to produce a usable gap classification so later model edits are driven by real SEAD workflows rather than by an outdated wish list.

## Verified Current Coverage

The current target model already covers a substantial core for Delivery 1 and early SEAD ingestion work.

Verified entity surface in [resources/target_models/sead_standard_model.yml](../../resources/target_models/sead_standard_model.yml):

- Core and provenance: `location`, `location_type`, `site`, `site_location`, `sample_group`, `sample`, `method`, `dataset`, `master_dataset`, `project`, `citation`, `contact`, `contact_type`, `dataset_contact`
- Sample and coordinate support: `sample_description_type`, `sample_description`, `sample_type`, `dimension`, `coordinate_method_dimension`, `sample_coordinate`, `alt_ref_type`, `sample_alt_ref`, `sample_dimension`
- Analysis and abundance: `analysis_entity`, `abundance`, `abundance_element`, `abundance_element_group`, `abundance_modification`, `modification_type`, `abundance_property`, `identification_level`, `abundance_ident_level`
- Dating: `age_type`, `relative_age_type`, `chronology`, `dating_uncertainty`, `dating_material`, `relative_ages`, `relative_dating`, `geochronology`, `dating_lab`
- Taxonomy and features: `taxa_tree_master`, `taxa_common_names`, `feature_type`, `feature`, `sample_feature`
- Classification and measurement support: `method_group`, `data_type`, `unit`, `site_type_group`, `site_type`

This is enough to support the current change-request work, but it is not yet a complete SEAD v2 target-model review.

## Problem

The remaining completeness problem now has three separate parts that should not be conflated.

### 1. Documentation Gaps

The old review document drifted away from the actual YAML model.

Examples:

- it reported a larger entity count than the current file contains
- it described several planned entity additions as already present
- it mixed implementation status, Arbodat-specific needs, and general SEAD backlog into one inventory

That makes it hard to tell whether a gap is real, already solved, or only proposed.

### 2. Target-Model Gaps

Several entity families still appear to be missing from the current model and should remain under active review.

Verified missing candidates from the current YAML include:

- Spatial and site-location support: `coordinate_system`, `sample_group_coordinate`, `site_natgridref`
- Dating and period support: `dating_period`
- Feature and site metadata: `feature_property`, `feature_property_type`, `site_property`, `site_property_type`
- Site-region support: `site_natural_region`, `natural_region`, `natural_region_group`
- Sample metadata: `sample_horizon`, `sample_location`, `sample_location_type`, `sample_note`, `sample_colour`, `colour`
- Sample-group metadata: `sample_group_dimension`, `sample_group_note`, `sample_group_reference`
- Taxon and ecology extensions: `taxon_synonyms`, `rdb`, `taxon_measured_attributes`
- Abundance typing: `abundance_property_type`
- Generic analysis values: `analysis_value`, `analysis_categorical_value`, `analysis_boolean_value`, `analysis_integer_value`, `analysis_numerical_value`, `analysis_date_range`, `analysis_note`, `analysis_identifier`
- Project classification: `project_type`, `project_stage`

This list is useful, but it is still only a candidate backlog until each item is tied to an actual validation or ingestion need.

### 3. Schema-Boundary Decisions

Some gaps may not belong in the core SEAD target model at all.

Examples called out in earlier work include `natural_region`, `cultural_group`, `archaeological_period`, and related region-specific or project-specific concepts. Those may be:

- real core SEAD gaps
- valid extension-model concerns
- data-project conveniences that should not be promoted into the shared target model yet

Issue 5 is not complete until those categories are separated explicitly.

## Gap Classification

The next useful shape for this review is a prioritized decision document.

### High Priority

These gaps are the strongest candidates for near-term target-model work because they affect validation of physical context, location context, or commonly expected SEAD relationships.

- `coordinate_system`, `sample_group_coordinate`, `site_natgridref`
- `dating_period`
- `sample_horizon`, `sample_location`, `sample_location_type`
- `feature_property`, `feature_property_type`

### Medium Priority

These gaps matter, but they should follow only after the high-priority spatial, dating, and physical-context gaps are clarified.

- `site_property`, `site_property_type`
- `site_natural_region`, `natural_region`, `natural_region_group`
- `sample_note`, `sample_colour`, `colour`
- `sample_group_dimension`, `sample_group_note`, `sample_group_reference`
- `abundance_property_type`
- `taxon_synonyms`, `rdb`, `taxon_measured_attributes`

### Lower Priority Or Deferred

These gaps are real candidates, but they look broader, more model-shaping, or less urgent for current ingestion validation work.

- `analysis_value` and its typed value family
- `analysis_note`, `analysis_identifier`
- `project_type`, `project_stage`
- extension-like concepts that may belong outside the shared core model until their reuse is proven

## Recommendation

Issue 5 should be closed only when this review supports an implementation decision rather than just restating a backlog.

The next steps should be:

1. Keep [resources/target_models/sead_standard_model.yml](../../resources/target_models/sead_standard_model.yml) as the source of truth for current coverage.
2. Use this document to track only verified missing areas and verified decisions.
3. Separate core-model gaps from extension-model candidates before adding more entities.
4. Promote only the highest-value missing entities into implementation work.

## Acceptance Criteria For Issue 5

Issue 5 should count as complete when all of the following are true:

- this review matches the current YAML model rather than a historical expansion plan
- remaining gaps are grouped into documentation gaps, target-model gaps, and schema-boundary decisions
- the highest-value missing areas are prioritized clearly enough to drive follow-up implementation
- the document is useful as a decision input for future model edits without requiring readers to reverse-engineer stale claims

## References

- [resources/target_models/sead_standard_model.yml](../../resources/target_models/sead_standard_model.yml)
- [docs/TARGET_MODEL_GUIDE.md](../TARGET_MODEL_GUIDE.md)
- [docs/proposals/CHANGE_REQUEST_INGESTER/DELIVERY_1_FOLLOWUP_CR.md](./CHANGE_REQUEST_INGESTER/DELIVERY_1_FOLLOWUP_CR.md)
- [docs/proposals/CHANGE_REQUEST_INGESTER/DELIVERY_1_FOLLOWUP_ISSUES.md](./CHANGE_REQUEST_INGESTER/DELIVERY_1_FOLLOWUP_ISSUES.md)