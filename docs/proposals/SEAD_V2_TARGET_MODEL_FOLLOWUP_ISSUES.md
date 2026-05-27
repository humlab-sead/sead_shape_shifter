# SEAD v2 Target Model Follow-Up Issue Drafts

This document turns the first SEAD v2 target-model follow-up slices into GitHub-ready issue drafts.

These issues are the first implementation tranche toward a near-complete, provider-independent SEAD target model.

They are not a full inventory of all remaining SEAD target-model work.

The shared target model is intended to cover almost all current SEAD tables and concepts.

Individual Shape Shifter projects can then use curated subsets of that larger model.

Detailed proposal home:

- [docs/proposals/SEAD_V2_TARGET_MODEL_COMPLETENESS.md](./SEAD_V2_TARGET_MODEL_COMPLETENESS.md)

Each issue body follows the repository's preferred `Problem`, `Solution`, and `Files` structure.

Current status snapshot:

- Issue 1: open as [#447](https://github.com/humlab-sead/sead_shape_shifter/issues/447)
- Issue 2: open as [#448](https://github.com/humlab-sead/sead_shape_shifter/issues/448)
- Issue 3: open as [#449](https://github.com/humlab-sead/sead_shape_shifter/issues/449)
- Issue 4: open as [#450](https://github.com/humlab-sead/sead_shape_shifter/issues/450)
- Issue 5: open as [#451](https://github.com/humlab-sead/sead_shape_shifter/issues/451)
- Issue 6: open as [#452](https://github.com/humlab-sead/sead_shape_shifter/issues/452)

## Issue 1 [feat(target_model): add sample-context entities](https://github.com/humlab-sead/sead_shape_shifter/issues/447)

Status:

`Open as #447`

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

- `docs/proposals/SEAD_V2_TARGET_MODEL_COMPLETENESS.md`
- `docs/proposals/SEAD_V2_TARGET_MODEL_FOLLOWUP_ISSUES.md`
- `resources/target_models/sead_superset_model.yml`
- `docs/TARGET_MODEL_GUIDE.md`

## Issue 2 [feat(target_model): add sample-group context entities](https://github.com/humlab-sead/sead_shape_shifter/issues/448)

Status:

`Open as #448`

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

- `docs/proposals/SEAD_V2_TARGET_MODEL_COMPLETENESS.md`
- `docs/proposals/SEAD_V2_TARGET_MODEL_FOLLOWUP_ISSUES.md`
- `resources/target_models/sead_superset_model.yml`
- `docs/TARGET_MODEL_GUIDE.md`

## Issue 3 [feat(target_model): add site and feature property entities](https://github.com/humlab-sead/sead_shape_shifter/issues/449)

Status:

`Open as #449`

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

Add explicit site and feature property entities, including the shared property-type pattern needed to represent `feature_property` and `site_property` cleanly.

Keep this issue limited to the property-pattern slice plus `site_natgridref`. Do not mix in sample-context entities or the generic analysis-value family.

Files:

- `docs/proposals/SEAD_V2_TARGET_MODEL_COMPLETENESS.md`
- `docs/proposals/SEAD_V2_TARGET_MODEL_FOLLOWUP_ISSUES.md`
- `resources/target_models/sead_superset_model.yml`
- `docs/TARGET_MODEL_GUIDE.md`

## Issue 4 [feat(target_model): design generic analysis-value family](https://github.com/humlab-sead/sead_shape_shifter/issues/450)

Status:

`Open as #450`

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

- `docs/proposals/SEAD_V2_TARGET_MODEL_COMPLETENESS.md`
- `docs/proposals/SEAD_V2_TARGET_MODEL_FOLLOWUP_ISSUES.md`
- `resources/target_models/sead_superset_model.yml`
- `docs/TARGET_MODEL_GUIDE.md`

## Issue 5 [proposal(target_model): reassess deferred lookup and extension candidates](https://github.com/humlab-sead/sead_shape_shifter/issues/451)

Status:

`Open as #451`

Title:

`proposal(target_model): reassess deferred lookup and extension candidates`

Problem:

Some concepts remain outside the first implementation slices even though they may still belong in the near-complete shared SEAD target model.

The filtered Issue 6 evidence is not broad enough to settle those areas, but that does not make them out of scope for the full target-model plan.

The current deferred set includes:

- `project_type`, `project_stage`
- `taxon_synonyms`, `rdb`, `taxon_measured_attributes`
- `coordinate_system`, `dating_period`, `natural_region*`
- `sample_colour`, `colour`, `abundance_property_type`

If these concepts move forward, they should do so from explicit SEAD-wide model criteria and schema evidence rather than from one project's current subset.

Solution:

Run a separate decision pass for the broader backlog beyond the first implementation slices.

Promote the concepts that belong in the near-complete shared SEAD target model, and separate them from derived tables, operational-only schema elements, and project-level subset choices.

Files:

- `docs/proposals/SEAD_V2_TARGET_MODEL_COMPLETENESS.md`
- `docs/proposals/SEAD_V2_TARGET_MODEL_FOLLOWUP_ISSUES.md`
- `resources/target_models/sead_superset_model.yml`
- `docs/TARGET_MODEL_GUIDE.md`

## Issue 6 [feat(target_model): add value qualifier lookup entities](https://github.com/humlab-sead/sead_shape_shifter/issues/452)

Status:

`Open as #452`

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

- `docs/proposals/SEAD_V2_TARGET_MODEL_COMPLETENESS.md`
- `docs/proposals/SEAD_V2_TARGET_MODEL_FOLLOWUP_ISSUES.md`
- `resources/target_models/sead_superset_model.yml`
- `docs/TARGET_MODEL_GUIDE.md`