# SEAD v2 Target Model Follow-Up Issue Drafts

This document turns the first SEAD v2 target-model follow-up slices into GitHub-ready issue drafts.

These issues are the first implementation tranche toward a near-complete, provider-independent SEAD target model.

They are not a full inventory of all remaining SEAD target-model work.

The shared target model is intended to cover almost all current SEAD tables and concepts.

Individual Shape Shifter projects can then use curated subsets of that larger model.

Detailed proposal home:

- [docs/proposals/done/SEAD_V2_TARGET_MODEL_COMPLETENESS.md](./SEAD_V2_TARGET_MODEL_COMPLETENESS.md)

Each issue body follows the repository's preferred `Problem`, `Solution`, and `Files` structure.

Current status snapshot:

- Issue 1: open as [#447](https://github.com/humlab-sead/sead_shape_shifter/issues/447); implemented on branch in `6103f693` and `0e6a8233`
- Issue 2: open as [#448](https://github.com/humlab-sead/sead_shape_shifter/issues/448); implemented on branch in `f934760f` and `d8a1ee64`
- Issue 3: open as [#449](https://github.com/humlab-sead/sead_shape_shifter/issues/449); implemented on branch in `4e21a10f` and `fb770680`
- Issue 4: open as [#450](https://github.com/humlab-sead/sead_shape_shifter/issues/450); implemented on branch in `f40f96cf`, `5c02cb34`, and `41adecfe`
- Issue 5: open as [#451](https://github.com/humlab-sead/sead_shape_shifter/issues/451); implemented on branch in `ccc53c66` with promoted shared lookups and explicit out-of-scope decisions
- Issue 6: open as [#452](https://github.com/humlab-sead/sead_shape_shifter/issues/452); implemented on branch in `68d154c0`
- Issue 7: open as [#453](https://github.com/humlab-sead/sead_shape_shifter/issues/453); implemented on branch in `30c01497` and `5c02cb34`

## Issue 1 [feat(target_model): add sample-context entities](https://github.com/humlab-sead/sead_shape_shifter/issues/447)

Status:

`Open as #447; implemented on branch`

Title:

`feat(target_model): add sample-context entities`

Problem:

The broader completeness review shows that the current target model covers the main sample core but still lacks explicit entities for several active sample-context concepts.

The filtered Issue 6 review strengthens the priority of this slice, but it is not the only reason these entities belong in the shared SEAD target model.

The clearest missing concepts on the filtered review surface are:

- `sample_horizon`
- `sample_location`
- `sample_location_type`
- `sample_note`

Without these entities, the shared target model remains incomplete on an important sample-context surface and risks pushing standard SEAD concepts into generic descriptions or later ad hoc extensions.

Solution:

Add explicit sample-context entities for `sample_horizon`, `sample_location`, `sample_location_type`, and `sample_note`.

Keep this issue limited to sample-level context. Do not mix in sample-group entities, property-pattern work, analysis-value work, or broader SEAD backlog slices.

Files:

- `docs/proposals/done/SEAD_V2_TARGET_MODEL_COMPLETENESS.md`
- `docs/proposals/done/SEAD_V2_TARGET_MODEL_FOLLOWUP_ISSUES.md`
- `resources/target_models/sead_superset_model.yml`
- `docs/TARGET_MODEL_GUIDE.md`

## Issue 2 [feat(target_model): add sample-group context entities](https://github.com/humlab-sead/sead_shape_shifter/issues/448)

Status:

`Open as #448; implemented on branch`

Title:

`feat(target_model): add sample-group context entities`

Problem:

The broader completeness review also shows a distinct sample-group context surface that is still missing from the target model.

The filtered Issue 6 review strengthens the priority of this slice, but the rationale for inclusion is broader than that one comparison surface.

The clearest missing concepts on that surface are:

- `sample_group_coordinate`
- `sample_group_dimension`
- `sample_group_note`
- `sample_group_reference`

These concepts belong with `sample_group`, but the current shared model does not represent them explicitly.

Solution:

Add explicit sample-group context entities for `sample_group_coordinate`, `sample_group_dimension`, `sample_group_note`, and `sample_group_reference`.

Keep this issue limited to group-level context tied to `sample_group`. Do not mix in sample-level context already covered by the earlier slice, property-pattern work, or analysis-value work.

Files:

- `docs/proposals/done/SEAD_V2_TARGET_MODEL_COMPLETENESS.md`
- `docs/proposals/done/SEAD_V2_TARGET_MODEL_FOLLOWUP_ISSUES.md`
- `resources/target_models/sead_superset_model.yml`
- `docs/TARGET_MODEL_GUIDE.md`

## Issue 3 [feat(target_model): add site and feature property entities](https://github.com/humlab-sead/sead_shape_shifter/issues/449)

Status:

`Open as #449; implemented on branch`

Title:

`feat(target_model): add site and feature property entities`

Problem:

The broader completeness review identifies a reusable property pattern that is present in the SEAD schema surface but still absent from the target model.

The filtered Issue 6 review makes this a strong early slice, but the underlying need is broader SEAD-wide metadata coverage.

The strongest current candidates are:

- `feature_property_type`
- `feature_property`
- `site_property_type`
- `site_property`
- `site_natgridref`

This is more than a few isolated tables. It is a cross-cutting metadata pattern that needs an explicit shared-model shape.

Solution:

Add the schema-backed property-pattern slice using the shared `property_type` table plus explicit `site_property`, `feature_property`, and `site_natgridref` entities.

Wire the existing `abundance_property` entity to the same shared property-type lookup so the target model no longer leaves that SEAD foreign key untyped.

Keep this issue limited to the property-pattern slice plus `site_natgridref`. Do not mix in sample-context entities or the generic analysis-value family.

Files:

- `docs/proposals/done/SEAD_V2_TARGET_MODEL_COMPLETENESS.md`
- `docs/proposals/done/SEAD_V2_TARGET_MODEL_FOLLOWUP_ISSUES.md`
- `resources/target_models/sead_superset_model.yml`
- `docs/TARGET_MODEL_GUIDE.md`

## Issue 4 [feat(target_model): design generic analysis-value family](https://github.com/humlab-sead/sead_shape_shifter/issues/450)

Status:

`Open as #450; implemented on branch`

Title:

`feat(target_model): design generic analysis-value family`

Problem:

The broader completeness review shows that `analysis_entity` exists, but the generic analysis-value family is still missing from the target model.

The filtered Issue 6 review makes this gap highly visible, but the need is SEAD-wide rather than specific to one provider or one current import slice.

The missing surface includes:

- `analysis_value`
- `analysis_note`
- `analysis_identifier`
- typed value entities such as boolean, categorical, integer, numerical, and dating-range variants

This is one of the clearest active gaps, but it also has the highest design impact because it affects how the model represents flexible typed analysis data across multiple workflows and data families.

Solution:

Design and add a generic analysis-value family to the target model, including the core `analysis_value` entity and the smallest necessary set of typed value entities needed to represent the broader SEAD analysis surface cleanly.

Reuse the shared qualifier lookup family from [#452](https://github.com/humlab-sead/sead_shape_shifter/issues/452) for single-value qualifiers and range-bound qualifiers instead of introducing a separate analysis-only qualifier vocabulary.

Keep this issue focused on the analysis-value family. Do not mix in taxonomy extensions, project lookups, or broader backlog slices that deserve separate design decisions.

Files:

- `docs/proposals/done/SEAD_V2_TARGET_MODEL_COMPLETENESS.md`
- `docs/proposals/done/SEAD_V2_TARGET_MODEL_FOLLOWUP_ISSUES.md`
- `resources/target_models/sead_superset_model.yml`
- `docs/TARGET_MODEL_GUIDE.md`

## Issue 5 [proposal(target_model): reassess deferred lookup and extension candidates](https://github.com/humlab-sead/sead_shape_shifter/issues/451)

Status:

`Open as #451; implemented on branch in ccc53c66`

Title:

`proposal(target_model): reassess deferred lookup and extension candidates`

Problem:

Some concepts remain outside the first implementation slices even though they may still belong in the near-complete shared SEAD target model.

The filtered Issue 6 evidence is not broad enough to settle those areas, but that does not make them out of scope for the full target-model plan.

The current branch resolves the earlier deferred candidates in three ways:

- promote shared SEAD candidates: `coordinate_system`, `taxa_synonyms`, `taxa_measured_attributes`, `rdb`, `rdb_code`, `rdb_system`
- keep `abundance_property_type` covered by the shared `property_type` model instead of adding a second abundance-only lookup family
- reject `dating_period` and `natural_region*` as shared target-model entities because they are treated as Arbodat-specific

Solution:

Run the remaining decision pass for deferred lookup and extension candidates, then either promote them into the shared superset or mark them out of scope explicitly.

The current branch completes that pass for the candidates tracked in this issue by promoting `colour`, `sample_colour`, `project_type`, `project_stage`, `coordinate_system`, `taxa_synonyms`, `taxa_measured_attributes`, `rdb`, `rdb_code`, and `rdb_system` into the shared target model.

It also treats `abundance_property_type` as covered by the shared `property_type` pattern rather than as a separate remaining target-model entity, and it keeps `dating_period` plus `natural_region*` out of the shared superset as Arbodat-specific concepts.

Promote the concepts that belong in the near-complete shared SEAD target model, and separate them from derived tables, operational-only schema elements, and project-level subset choices.

Files:

- `docs/proposals/done/SEAD_V2_TARGET_MODEL_COMPLETENESS.md`
- `docs/proposals/done/SEAD_V2_TARGET_MODEL_FOLLOWUP_ISSUES.md`
- `resources/target_models/sead_superset_model.yml`
- `docs/TARGET_MODEL_GUIDE.md`

## Issue 6 [feat(target_model): add value qualifier lookup entities](https://github.com/humlab-sead/sead_shape_shifter/issues/452)

Status:

`Open as #452; implemented on branch`

Title:

`feat(target_model): add value qualifier lookup entities`

Problem:

The recent sample and sample-group context work exposed a missing shared lookup family rather than a local gap in one entity.

Both `sample_dimension` and `sample_group_dimension` use `qualifier_id`, but the target model still treats that field as an untyped integer because there is no explicit target-model entity for `tbl_value_qualifiers`.

The same lookup family also appears in multiple analysis value and range tables through `tbl_value_qualifier_symbols`.

Without explicit qualifier lookup entities, projects cannot model these references cleanly, and follow-up slices keep accumulating deferred foreign keys that all point to the same shared SEAD vocabulary.

Solution:

Add explicit shared lookup entities for the SEAD value qualifier family, starting with `value_qualifier` and `value_qualifier_symbol`.

Update the target model so sample dimension entities can reference that lookup family explicitly, and document how later analysis-value work should reuse the same qualifier entities instead of inventing a parallel representation.

Keep this issue focused on the shared lookup family and the direct references already present in sample dimension entities. Do not mix in the broader design of the generic analysis-value family.

Files:

- `docs/proposals/done/SEAD_V2_TARGET_MODEL_COMPLETENESS.md`
- `docs/proposals/done/SEAD_V2_TARGET_MODEL_FOLLOWUP_ISSUES.md`
- `resources/target_models/sead_superset_model.yml`
- `docs/TARGET_MODEL_GUIDE.md`

## Issue 7 [feat(target_model): add sampling context and horizon lookups](https://github.com/humlab-sead/sead_shape_shifter/issues/453)

Status:

`Open as #453; implemented on branch`

Title:

`feat(target_model): add sampling context and horizon lookups`

Problem:

The current target model still treats `sample_group.sampling_context_id` and `sample_horizon.horizon_id` as untyped integers even though both columns point to named SEAD lookup tables.

Schema evidence shows that `sampling_context_id` is reused beyond `tbl_sample_groups`, including sample description and sample-location-type context tables. `horizon_id` points to `tbl_horizons`, which carries its own vocabulary fields and a `method_id` reference.

Leaving both columns unmodeled keeps shared SEAD vocabularies hidden inside typed integer columns and blocks clean foreign-key wiring in the sample-context slice.

Solution:

Add explicit target-model lookup entities for the shared context family:

- `sample_group_sampling_context` for `tbl_sample_group_sampling_contexts`
- `horizon` for `tbl_horizons`

Update the direct consumer entities to reference those lookups explicitly, starting with `sample_group` and `sample_horizon`.

Keep this issue focused on the shared lookup entities and the direct foreign keys already present in the current model. Do not mix in broader sample-description extension tables unless they are needed to complete the same lookup family cleanly.

Files:

- `docs/proposals/done/SEAD_V2_TARGET_MODEL_COMPLETENESS.md`
- `docs/proposals/done/SEAD_V2_TARGET_MODEL_FOLLOWUP_ISSUES.md`
- `resources/target_models/sead_superset_model.yml`
- `docs/TARGET_MODEL_GUIDE.md`