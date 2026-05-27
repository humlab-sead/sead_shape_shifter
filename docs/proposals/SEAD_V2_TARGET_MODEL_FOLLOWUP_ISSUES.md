# SEAD v2 Target Model Follow-Up Issue Drafts

This document turns the SEAD v2 target-model follow-up slices into GitHub-ready issue drafts.

Detailed proposal home:

- [docs/proposals/SEAD_V2_TARGET_MODEL_COMPLETENESS.md](./SEAD_V2_TARGET_MODEL_COMPLETENESS.md)

Each issue body follows the repository's preferred `Problem`, `Solution`, and `Files` structure.

Current status snapshot:

- Issue 1: open as [#447](https://github.com/humlab-sead/sead_shape_shifter/issues/447)
- Issue 2: open as [#448](https://github.com/humlab-sead/sead_shape_shifter/issues/448)
- Issue 3: open as [#449](https://github.com/humlab-sead/sead_shape_shifter/issues/449)
- Issue 4: open as [#450](https://github.com/humlab-sead/sead_shape_shifter/issues/450)
- Issue 5: open as [#451](https://github.com/humlab-sead/sead_shape_shifter/issues/451)

## Issue 1 [feat(target_model): add sample-context entities](https://github.com/humlab-sead/sead_shape_shifter/issues/447)

Status:

`Open as #447`

Title:

`feat(target_model): add sample-context entities`

Problem:

The filtered Issue 6 review shows that the current target model covers the main sample core but still lacks explicit entities for several active sample-context concepts.

The clearest missing concepts on the filtered review surface are:

- `sample_horizon`
- `sample_location`
- `sample_location_type`
- `sample_note`

Without these entities, the target model cannot represent the filtered sample-context tables cleanly and instead risks pushing those concepts into generic descriptions or later ad hoc extensions.

Solution:

Add explicit sample-context entities for `sample_horizon`, `sample_location`, `sample_location_type`, and `sample_note`.

Keep this issue limited to sample-level context. Do not mix in sample-group entities, property-pattern work, analysis-value work, or extension candidates.

Files:

- `docs/proposals/SEAD_V2_TARGET_MODEL_COMPLETENESS.md`
- `docs/proposals/SEAD_V2_TARGET_MODEL_FOLLOWUP_ISSUES.md`
- `resources/target_models/sead_standard_model.yml`
- `docs/TARGET_MODEL_GUIDE.md`

## Issue 2 [feat(target_model): add sample-group context entities](https://github.com/humlab-sead/sead_shape_shifter/issues/448)

Status:

`Open as #448`

Title:

`feat(target_model): add sample-group context entities`

Problem:

The filtered Issue 6 review also shows a distinct sample-group context surface that is still missing from the target model.

The clearest missing concepts on that surface are:

- `sample_group_coordinate`
- `sample_group_dimension`
- `sample_group_note`
- `sample_group_reference`

These concepts belong with `sample_group`, but the current model does not represent them explicitly.

Solution:

Add explicit sample-group context entities for `sample_group_coordinate`, `sample_group_dimension`, `sample_group_note`, and `sample_group_reference`.

Keep this issue limited to group-level context tied to `sample_group`. Do not mix in sample-level context already covered by the earlier slice, property-pattern work, or analysis-value work.

Files:

- `docs/proposals/SEAD_V2_TARGET_MODEL_COMPLETENESS.md`
- `docs/proposals/SEAD_V2_TARGET_MODEL_FOLLOWUP_ISSUES.md`
- `resources/target_models/sead_standard_model.yml`
- `docs/TARGET_MODEL_GUIDE.md`

## Issue 3 [feat(target_model): add site and feature property entities](https://github.com/humlab-sead/sead_shape_shifter/issues/449)

Status:

`Open as #449`

Title:

`feat(target_model): add site and feature property entities`

Problem:

The filtered Issue 6 review identifies a reusable property pattern that is present in the live-schema surface but still absent from the target model.

The strongest current candidates are:

- `feature_property_type`
- `feature_property`
- `site_property_type`
- `site_property`
- `site_natgridref`

This is more than a few isolated tables. It is a cross-cutting metadata pattern that needs an explicit target-model shape.

Solution:

Add explicit site and feature property entities, including the shared property-type pattern needed to represent `feature_property` and `site_property` cleanly.

Keep this issue limited to the property-pattern slice plus `site_natgridref`. Do not mix in sample-context entities or the generic analysis-value family.

Files:

- `docs/proposals/SEAD_V2_TARGET_MODEL_COMPLETENESS.md`
- `docs/proposals/SEAD_V2_TARGET_MODEL_FOLLOWUP_ISSUES.md`
- `resources/target_models/sead_standard_model.yml`
- `docs/TARGET_MODEL_GUIDE.md`

## Issue 4 [feat(target_model): design generic analysis-value family](https://github.com/humlab-sead/sead_shape_shifter/issues/450)

Status:

`Open as #450`

Title:

`feat(target_model): design generic analysis-value family`

Problem:

The filtered Issue 6 review shows that `analysis_entity` exists, but the generic analysis-value family is still missing from the target model.

The missing surface includes:

- `analysis_value`
- `analysis_note`
- `analysis_identifier`
- typed value entities such as boolean, categorical, integer, numerical, and dating-range variants

This is the clearest active gap in the filtered review surface, but it also has the highest design impact because it affects how the model represents flexible typed analysis data across multiple workflows.

Solution:

Design and add a generic analysis-value family to the target model, including the core `analysis_value` entity and the smallest necessary set of typed value entities needed to represent the filtered live-schema surface cleanly.

Keep this issue focused on the analysis-value family. Do not mix in taxonomy extensions, project lookups, or unsupported Issue 6 backlog items.

Files:

- `docs/proposals/SEAD_V2_TARGET_MODEL_COMPLETENESS.md`
- `docs/proposals/SEAD_V2_TARGET_MODEL_FOLLOWUP_ISSUES.md`
- `resources/target_models/sead_standard_model.yml`
- `docs/TARGET_MODEL_GUIDE.md`

## Issue 5 [proposal(target_model): reassess deferred lookup and extension candidates](https://github.com/humlab-sead/sead_shape_shifter/issues/451)

Status:

`Open as #451`

Title:

`proposal(target_model): reassess deferred lookup and extension candidates`

Problem:

Some concepts remain visible in the broader Issue 5 backlog, but the filtered Issue 6 evidence does not justify promoting them into immediate core-model work.

The current deferred set includes:

- `project_type`, `project_stage`
- `taxon_synonyms`, `rdb`, `taxon_measured_attributes`

If these concepts move forward, they should do so from explicit use cases rather than from convenience or from historical schema presence alone.

Solution:

Run a separate decision pass for the deferred lookup and extension candidates.

Promote only the concepts that have a concrete validation or ingestion need. Leave unsupported Issue 6 backlog items such as `coordinate_system`, `dating_period`, `natural_region*`, `sample_colour`, `colour`, and `abundance_property_type` out of scope unless new evidence appears.

Files:

- `docs/proposals/SEAD_V2_TARGET_MODEL_COMPLETENESS.md`
- `docs/proposals/SEAD_V2_TARGET_MODEL_FOLLOWUP_ISSUES.md`
- `resources/target_models/sead_standard_model.yml`
- `docs/TARGET_MODEL_GUIDE.md`