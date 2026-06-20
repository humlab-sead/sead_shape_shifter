# BugsCEP Policy Session Wrap-Up

## Status

- Historical session checkpoint
- Scope: machine-readable fidelity work for BugsCEP reconciliation policies and fixture-backed parity against current Java behavior
- Goal: resume later without re-discovery
- Repositories: `sead_bugs_import` and `sead_shape_shifter`
- Branches at wrap-up: `dev` in both repositories
- Last full validation: `cd /home/roger/source/sead_bugs_import && make validate-policy-format`
- Last full validation result: passed on 2026-05-29 with 103 tests, 0 failures, 0 errors

## Summary

This session continued the fixture-backed fidelity work rather than broad schema design.

This file now serves as a historical checkpoint for the point where `datescalendar` gained its first supporting-output and related-output graph parity slices. Later work extended the same pattern into `datesperiod`, `datesradio`, `lab`, `bibliography`, `rdbcode`, `speciesdistribution`, `taxanotes`, and `fossil`.

For the current coverage summary and the current recommendation on what to extend next, use [BUGSCEP_POLICY_SCHEMA_MACHINE_READABLE_FIDELITY.md](BUGSCEP_POLICY_SCHEMA_MACHINE_READABLE_FIDELITY.md).

The main result is that `datescalendar` now has executable coverage beyond postprocess merge behavior. It now also has:

- one single supporting-output slice for `relative_age`
- one related-output graph slice for `relative_age`, `dataset`, and `analysis_entity`
- matching Java-side parity tests for both slices

This session also synced the documentation so the current coverage statement now includes:

- `taxanotes` ordered reconciliation
- `datescalendar` supporting-output coverage
- `datescalendar` related-output graph coverage

The current baseline is stable. The narrow new slices passed first, and then the full policy validation target passed.

## What Was Completed Earlier In This Overall Session

The broader session already had working fixture-backed coverage for:

- `datescalendar` postprocess merge and conflict behavior
- `datesradio` resolver behavior
- `datesperiod` resolver behavior
- `lab` country resolver behavior
- `lab` ordered reconciliation
- `bibliography` ordered reconciliation
- `rdbcode` ordered reconciliation
- `speciesdistribution` ordered reconciliation
- `taxanotes` ordered reconciliation
- `datesperiod` dataset supporting-output behavior
- `datesperiod` analysis-entity supporting-output behavior
- `datesperiod` combined related-output graph behavior
- `datesradio` dataset supporting-output behavior
- `datesradio` combined related-output graph behavior
- `fossil` related-output graph behavior including error branches

The harness layer already supported these intent and result shapes before the final wrap-up step:

- `postprocess_merge`
- `postprocess_conflict`
- `resolver_path`
- `reconciliation_path`
- `supporting_output_result`
- `related_output_graph`
- `postprocess_result`
- `resolver_result`
- `reconciliation_result`
- `graph_result`
- `graph_issue`
- `row_changed`

## What Was Added In The Final Work Block

### 1. New `datescalendar` supporting-output slice

Added one fixture scenario for single-date `relative_age` creation in:

- `sead_bugs_import/doc/reconciliation_policies/fixtures/datescalendar.fixture.yml`

Added policy-side harness support in:

- `sead_bugs_import/src/test/java/se/sead/reconciliation/SupportingOutputPolicyHarness.java`
- `sead_bugs_import/src/test/java/se/sead/reconciliation/SupportingOutputPolicyHarnessTest.java`

Added Java-side parity test in:

- `sead_bugs_import/src/test/java/se/sead/bugsimport/datescalendar/converters/RelativeAgeManagerFixtureExecutionTest.java`

### 2. New `datescalendar` related-output graph slice

Added one fixture scenario for create-path graph behavior in:

- `sead_bugs_import/doc/reconciliation_policies/fixtures/datescalendar.fixture.yml`

Added policy-side graph harness support in:

- `sead_bugs_import/src/test/java/se/sead/reconciliation/RelatedOutputPolicyHarness.java`
- `sead_bugs_import/src/test/java/se/sead/reconciliation/RelatedOutputPolicyHarnessTest.java`

Added Java-side parity test in:

- `sead_bugs_import/src/test/java/se/sead/bugsimport/datescalendar/converters/RelativeDateUpdaterForCalendarFixtureExecutionTest.java`

### 3. Validation target update

Added the two new calendar fixture execution tests to:

- `sead_bugs_import/Makefile`

### 4. Documentation sync

Updated the policy authoring guide in:

- `sead_bugs_import/doc/reconciliation_policies/create-policy.instructions.md`

Updated the Shape Shifter fidelity proposal in:

- `sead_shape_shifter/docs/proposals/BUGSCEP_POLICY_GENERATION/BUGSCEP_POLICY_SCHEMA_MACHINE_READABLE_FIDELITY.md`

## Verified State At Wrap-Up

These validations were run and passed:

1. `cd /home/roger/source/sead_bugs_import && sh ./mvnw -q -Dtest=PolicyFormatValidationTest,SupportingOutputPolicyHarnessTest,RelativeAgeManagerFixtureExecutionTest test`
2. `cd /home/roger/source/sead_bugs_import && sh ./mvnw -q -Dtest=PolicyFormatValidationTest,RelatedOutputPolicyHarnessTest,RelativeDateUpdaterForCalendarFixtureExecutionTest test`
3. `cd /home/roger/source/sead_bugs_import && make validate-policy-format`

The final full run reported:

- 103 tests run
- 0 failures
- 0 errors

## Current Best Resume Point

This file is no longer the primary resume document.

If resuming today, start with these files open instead:

1. `sead_shape_shifter/docs/proposals/BUGSCEP_POLICY_GENERATION/BUGSCEP_POLICY_SCHEMA_MACHINE_READABLE_FIDELITY.md`
2. `sead_bugs_import/doc/reconciliation_policies/create-policy.instructions.md`
3. one importer or controller outside the current covered set that has a richer search path, supporting-row updater, or grouped postprocess branch

Reason: `datescalendar` is no longer the newest uncovered surface. The current best next step is to carry the same shared-result approach into one more importer or updater path without reopening broad exploration.

## Recommended Next Steps

### Option A: Extend Another Importer With A Richer Search Or Update Path

This is the recommended next move because the current approach is already proven across the first calendar, radio, period, lab, bibliography, rdbcode, speciesdistribution, taxanotes, and fossil slices.

Prefer one importer that adds at least one of these:

1. a richer ordered `search_chain`
2. another single supporting-row updater
3. another grouped postprocess branch

For that importer:

1. extend the matching policy-side harness only if needed
2. add the matching Java-side execution scenario for the same branch
3. run the same narrow validation first

Suggested narrow command:

```bash
cd /home/roger/source/sead_bugs_import && sh ./mvnw -q -Dtest=PolicyFormatValidationTest,<matching harness test>,<matching Java fixture test> test
```

### Option B: Deepen One Existing Covered Importer Locally

If another importer is not yet chosen, stay local to one already-covered importer and add one nearby unresolved branch.

Good candidates are:

1. another supporting-output keep or update branch
2. one more reconciliation branch under an existing `search_chain`
3. one more related-output graph error branch

Suggested narrow command:

```bash
cd /home/roger/source/sead_bugs_import && sh ./mvnw -q -Dtest=PolicyFormatValidationTest,<matching harness test>,<matching Java fixture test> test
```

### Option C: Return To `datescalendar` Only For A Concrete Missing Branch

`datescalendar` is still a valid target, but only when a specific missing branch is the clearest local next step.

Do not reopen it just because it was the last historical focus.

## Resume Guidance

When resuming, use this execution pattern again:

1. pick one narrow controller or harness branch
2. add one small fixture scenario
3. add one Java parity scenario when a real controller exists
4. run the narrow validation immediately
5. only widen after that passes

This pattern worked well throughout the session and kept failures local.

---

## Fidelity Work Changelog

### 2026-06-20: Tier C → Tier A conversions (bibliography, country, rdbcode, mcrnames, mcrsummary, attributes)

Converted 6 Tier C policies to Tier A execution-ready status:

| Policy | Helpers | Resolver Type | Known Divergences |
|--------|---------|---------------|-------------------|
| `bibliography` | 0 | N/A (leaf importer) | `notes_field_not_mapped`, `full_reference_derivation_adapter` |
| `country` | 1 | `resolve_country_type_id` (fixed DB query) | `update_detection_is_no_op`, `country_type_is_fixed_lookup` |
| `rdbcode` | 1 | `resolve_rdb_system_id` (trace lookup) | `duplicate_value_returns_error_carrier`, `rdb_system_resolution_is_trace_based` |
| `mcrnames` | 1 | `resolve_taxon_id` (trace lookup) | `species_resolution_is_trace_based`, `tempcode_field_ignored` |
| `mcrsummary` | 1 | `resolve_taxon_id` (trace lookup) | `species_resolution_is_trace_based`, `update_detection_is_no_op` |
| `attributes` | 1 | `resolve_taxon_id` (trace lookup) | `species_resolution_is_trace_based`, `missing_value_collapse_adapter` |

**Pattern**: All 1-helper policies follow the same conversion pattern:
1. Convert helper to structured resolver (trace_lookup or database_query step)
2. Mark old helper as superseded with `used_by: []`
3. Add `known_divergences` section (at least 2 entries per policy)
4. Update `meta.notes` with conversion date and summary
5. Validate with `make validate-policy-format`

**Schema feature status updates**:
- Feature 2 (Structured resolvers): 8 → 14 policies
- Feature 5 (Known divergences): 10 → 16 policies

**Tier status**:
- Tier A: 9 → 15 policies (43% of 35)
- Tier B: 0 policies (unchanged)
- Tier C: 15 → 9 policies
- Tier D: 11 policies (unchanged)

**Validation**: `make validate-policy-format` — 355 tests, 0 failures, 0 errors

## Worktree Notes

Both repositories already have many unrelated modified and untracked files.

Important constraint for the next session:

- do not reset or broadly clean either worktree
- do not assume all changed files were created in this session
- keep future edits scoped to the active policy slice

At wrap-up time, notable session-relevant modified files included:

- `sead_bugs_import/Makefile`
- `sead_bugs_import/doc/reconciliation_policies/create-policy.instructions.md`
- `sead_bugs_import/doc/reconciliation_policies/fixtures/datescalendar.fixture.yml`
- `sead_bugs_import/src/test/java/se/sead/reconciliation/SupportingOutputPolicyHarness.java`
- `sead_bugs_import/src/test/java/se/sead/reconciliation/SupportingOutputPolicyHarnessTest.java`
- `sead_bugs_import/src/test/java/se/sead/reconciliation/RelatedOutputPolicyHarness.java`
- `sead_bugs_import/src/test/java/se/sead/reconciliation/RelatedOutputPolicyHarnessTest.java`
- `sead_bugs_import/src/test/java/se/sead/bugsimport/datescalendar/converters/RelativeAgeManagerFixtureExecutionTest.java`
- `sead_bugs_import/src/test/java/se/sead/bugsimport/datescalendar/converters/RelativeDateUpdaterForCalendarFixtureExecutionTest.java`
- `sead_shape_shifter/docs/proposals/BUGSCEP_POLICY_GENERATION/BUGSCEP_POLICY_SCHEMA_MACHINE_READABLE_FIDELITY.md`

## Short Resume Prompt

If you want a compact prompt for the next session, use this:

```text
Resume the BugsCEP policy fidelity work from BUGSCEP_POLICY_SCHEMA_MACHINE_READABLE_FIDELITY.md. Pick one uncovered importer or updater path with a richer search, supporting-output, or grouped postprocess branch. Add one fixture scenario plus one matching Java parity case, then run the narrow validator before widening.
```

## Conclusion

The session ends at a clean checkpoint.

`datescalendar` is no longer only a postprocess example. It gained the first working supporting-output and related-output graph slices, and later work extended the same approach to several other importer families. The full `make validate-policy-format` target is green in the recorded checkpoint, and the current safe continuation is to extend one more importer or updater path with the same narrow fixture-plus-parity pattern rather than reopening broad analysis.

## Fidelity Work Changelog

This section collects the detailed batch-by-batch completion history from the fidelity proposal and task plan. Use it as the source of truth for what has been implemented. The active proposal and task plan keep only concise status summaries.

### Schema And Harness Features

- Direct related-output references with `before_parent` / `after_parent` phases
- Structured resolvers with ordered steps, trace lookups, database queries, and emitted outcomes
- Grouped postprocess merge stages with partition rules and conflict handling
- Shared `emit` blocks for structured issues, warnings, and flags
- Initial `known_divergences` support for recording policy-versus-Java differences
- Fixture-backed scenario validation with shared result-object comparisons against current Java behavior
- Harness result shapes: `postprocess_merge`, `postprocess_conflict`, `resolver_path`, `reconciliation_path`, `supporting_output_result`, `related_output_graph`, `postprocess_result`, `resolver_result`, `reconciliation_result`, `graph_result`, `graph_issue`, `row_changed`

### Execution-Facing Action Labels — Reconciliation Write Paths

- **First batch:** five simpler reconciliation families with explicit `persisted_action` write-action labels for insert and update paths
- **Second batch:** explicit write-action labels on successful update or create paths for `period`, `country`, and `taxanotes`

### Execution-Facing Action Labels — No-Write And Error Paths

- **First error-and-guard batch:** `period`, `lab`, `bibliography`, `rdbcode`, `rdbsystem`, `ecocodedefinition_bugs`, `ecocodedefinition_koch`, and `speciesassociation`
- **Second no-write batch:** `site`, `sitereferences`, `rdb`, `taxaseasonality`, `speciesbiology`, `specieskeys`, `speciessynonyms`, and `speciesdistribution`
- **Third no-write batch:** `country`, `mcrnames`, and `taxanotes`
- **Trace-hit batch:** explicit no-write trace-hit coverage for `country`, `mcrnames`, `ecocodegroup`, `ecocode_bugs`, and `ecocode_koch`; keep-existing and keep-existing-error semantics for `mcrsummary`
- **Species-text family batch:** explicit no-write action labels for the executable existing-error reconciliation paths in `speciesassociation`, `speciesbiology`, `specieskeys`, `speciessynonyms`, and `speciesdistribution`

### Supporting-Output Action Labels

- **Sample supporting dimensions:** explicit `supporting_action` labels for create, update, keep, and delete supporting actions
- **Datasetcontacts supporting contacts:** explicit `supporting_action` labels for generated and reused contact rows
- **Fossil dataset-analysis-entity family:** explicit `supporting_action` labels across all 10 scenarios with supporting actions on successful graph branches (clone-driven dataset creation, dataset reuse, analysis-entity creation, analysis-entity reuse) and explicit `row_changed` expectations on graph issues

### Related-Output Graph Action Labels

- **Species graph:** explicit `supporting_action` labels in both supporting-output and related-output graph fixtures; mixed create-and-reuse, family-reuse-only, missing-author, and no-data-shortcut scenarios so graph expectations cover more than all-create and all-reuse trees

### Row Changed Expectations — List Outputs

- **Sitelocations and siteotherproxies:** explicit `row_changed` expectations across all 10 executable list-output scenarios, recording both row actions and whether the updater path reports a changed row
- **Datasetcontacts:** explicit `row_changed` expectations across all four executable list-output scenarios, so both the parser path and the updater path carry the same change-state signal

### Row Changed Expectations — Related-Output Graphs

- **Species related-output graphs:** explicit `row_changed` expectations across all six executable scenarios, recording whether the graph creates a new species row or reuses an existing one (including mixed create-and-reuse, family-reuse-only, missing-author, and no-data-shortcut branches)

### Row Changed Expectations — Supporting Outputs

- **Datesperiod and sample:** explicit `row_changed` expectations across the 10 executable supporting-output scenarios for dataset, analysis-entity, and supporting-dimension create, update, keep, and delete paths
- **Datesradio and datescalendar:** explicit `row_changed` expectations across the 10 executable supporting-output scenarios for relative-age, dataset, and analysis-entity create, update, keep, and reuse paths
- **Species supporting outputs:** explicit `row_changed` expectations for family, genus, author, and species creation or reuse, including the no-data shortcut and the missing-author branch
- **Datasetcontacts supporting contacts:** explicit `row_changed` expectations for contact creation and reuse
- **Fossil supporting outputs:** explicit `row_changed` expectations for dataset clone or reuse and for analysis-entity creation or reuse

### Concrete Divergence Areas (From Executable Fixtures)

- **`created_supporting_rows_mark_updated`:** seen in `datesperiod` and `datescalendar`; fixtures expose explicit `supporting_action` values (`create`, `update`, `keep`, `reuse`) while preserving current Java `updated: true` behavior as parity evidence
- **`replacement_expressed_as_row_actions`:** seen in `sitelocations` and `siteotherproxies`; fixtures expose explicit `persisted_action` values (`append_new`, `keep_existing`, `mark_for_deletion`, `stop_before_list_update`) while preserving the Java row-by-row replacement shape

### Documentation Improvements (Post-Fidelity Work)

- **Consolidated status history:** moved batch-by-batch completion notes from the fidelity proposal's status line and the task plan's progress tracker into this changelog section
- **Schema feature status table:** added to the fidelity proposal showing which of the 5 proposed schema features are implemented in `_schema.yml`, which are partially implemented, and which are still planned
- **Execution-readiness assessment:** added concrete classification of all 35 policies into four tiers (A: execution-ready, B: near-ready, C: reconciliation-ready, D: parity-only) with criteria matrix and promotion path
- **Gap inventory consolidation:** merged the standalone gap inventory (`BUGSCEP_POLICY_SCHEMA_MACHINE_READABLE_FIDELITY_GAP_INVENTORY.md`) into the task plan as a dedicated Gap Inventory section, with cross-references from both the fidelity proposal and the original gap inventory file

### Feature 1 Conversion (2026-06-20)

- **Fossil policy uses `phase: before_parent` and `related.<name>.<field>` expressions:** the dataset and analysis_entity related outputs now declare `phase: before_parent`, the analysis_entity `dataset_id` mapping uses `related.dataset.dataset_id` instead of a `generated` field, and the parent abundance row's `analysis_entity_id` mapping uses `related.analysis_entity.analysis_entity_id` instead of the `resolve_fossil_analysis_entity_id` helper call. This is the first policy to exercise Feature 1 (direct related-output references) end-to-end.
- **Helper marked as superseded:** `resolve_fossil_analysis_entity_id` is retained in the helpers section for historical reference but marked as superseded with `used_by: []` and a description explaining the replacement.
- **Two new fixture scenarios:** `analysis_entity_references_dataset_via_related_expression` (happy path) and `analysis_entity_dataset_id_null_when_dataset_missing` (null propagation) exercise the `related.<name>.<field>` expression through the `related_output_graph` intent.
- **Schema feature status updated:** Feature 1 changed from "Planned" to "Implemented" in the fidelity proposal's schema feature status table.

### Feature 1 Conversion — Species Policy (2026-06-20)

- **Species policy uses `phase: before_parent` on all 4 related outputs:** `taxa_family`, `taxa_genus`, `taxa_author`, and `taxa_species` all declare `phase: before_parent`. The dependency chain is: `taxa_genus.family_id` uses `related.taxa_family.family_id`; `taxa_species.genus_id` uses `related.taxa_genus.genus_id` and `taxa_species.author_id` uses `related.taxa_author.author_id`; parent `taxon_id` uses `related.taxa_species.taxon_id`.
- **Helper marked as superseded:** `resolve_species_taxon_id` is retained in the helpers section for historical reference but marked as superseded with `used_by: []` and a description explaining the replacement. `resolve_bugs_taxonomic_order_system_id` is also marked as superseded in helpers (replaced by structured resolver).
- **Structured resolver added:** `resolve_bugs_taxonomic_order_system_id` converted from helper call to structured resolver with `database_query` step. `resolve_import_order_id` kept as helper (used by related-output mapping only, not top-level mapping).
- **Known divergences added:** Two `known_divergences` entries — `no_data_species_shortcut` (Java helper short-circuits normal family/genus/author/species creation) and `genus_family_cascade_dependency` (null propagation through the dependency chain is an implementation detail).
- **Two new fixture scenarios:** `genus_family_id_resolved_via_related_expression` (all-create path) and `species_genus_and_author_resolved_via_related_expressions_when_family_exists` (family-reuse path) exercise the `related.<name>.<field>` expression through the `related_output_graph` intent.
- **Schema feature status updated:** Feature 1 now used in 2 policies (`fossil`, `species`). Feature 2 (structured resolvers) now used in 4 policies (`lab`, `datesperiod`, `datesradio`, `species`). Feature 5 (known divergences) now used in 6 policies.
- **Species promoted to Tier A:** Species policy is now execution-ready with complete identity flow, structured resolver, known divergences, and related-output graph coverage.

### Feature 2 Conversion — Datasetcontacts Policy (2026-06-20)

- **Datasetcontacts policy uses structured resolver for dataset ID:** the `resolve_dataset_id_from_countsheet_code` helper was converted to a structured resolver with 4 ordered steps: `empty_countsheet_code_error` (guard + emit), `trace_lookup` (continue on miss), `no_trace_error` (emit when trace misses), and `dataset_lookup` (database query). The resolver has 2 `emit` blocks: one for empty countsheet code errors and one for missing trace errors.
- **Helper marked as superseded:** `resolve_dataset_id_from_countsheet_code` is retained in the helpers section for historical reference but marked as superseded with `used_by: []` and a description explaining the replacement by the structured resolver.
- **Known divergences added:** Two `known_divergences` entries — `dataset_reuse_from_fossil_import` (dataset rows may be created by the fossil importer; datasetcontacts reuses existing datasets via trace) and `contact_string_parsing_adapter` (the Java `ContactStringParser` extracts contact fields from a free-form string; this parsing logic is adapter-only).
- **Three new fixture scenarios:** `dataset_resolved_via_trace_and_database_lookup` (success path), `dataset_resolver_returns_error_when_no_trace_exists` (trace miss error), and `dataset_resolver_returns_error_for_empty_countsheet_code` (empty code guard) exercise the resolver through the `resolver_path` intent.
- **Schema feature status updated:** Feature 2 (structured resolvers) now used in 5 policies (`lab`, `datesperiod`, `datesradio`, `species`, `datasetcontacts`). Feature 4 (shared emit blocks) now used in 4 policies (`lab`, `datesperiod`, `datesradio`, `datasetcontacts`). Feature 5 (known divergences) now used in 7 policies.
- **Datasetcontacts promoted to Tier A:** Datasetcontacts policy is now execution-ready with structured resolver, known divergences, emit blocks, and resolver path coverage. Tier A now has 6 policies total; Tier B has 3 remaining (`sample`, `sitelocations`, `siteotherproxies`).

### Feature 2 Conversion — Sample Policy (2026-06-20)

- **Sample policy uses three structured resolvers:** `resolve_sample_group_id` (trace lookup pattern with empty code guard → trace lookup → no-trace error, 2 emit blocks), `resolve_default_alternative_reference_type_id` (fixed database query for 'Other alternative sample name'), and `resolve_default_sample_type_id` (fixed database query for 'Unspecified'). All three replace the previous helper calls.
- **Helpers marked as superseded:** All three helpers (`resolve_sample_group_id`, `resolve_default_alternative_reference_type_id`, `resolve_default_sample_type_id`) are retained in the helpers section for historical reference but marked as superseded with `used_by: []` and descriptions explaining the replacements.
- **Known divergences added:** Two `known_divergences` entries — `xy_coordinate_error_detection` (X/Y presence adds error but isn't mapped to SEAD; adapter-only data-quality check) and `sample_dimensions_as_supporting_output` (DimensionUpdater manages child rows with create/update/keep/delete semantics using fixed method and dimension IDs).
- **Five new fixture scenarios:** `sample_group_resolved_via_trace_lookup` (success path), `sample_group_resolver_returns_error_for_empty_countsheet_code` (empty code guard), `sample_group_resolver_returns_error_when_no_trace_exists` (trace miss error), `default_alternative_reference_type_resolved_from_database` (fixed lookup), and `default_sample_type_resolved_from_database` (fixed lookup) exercise the resolvers through the `resolver_path` intent.
- **Schema feature status updated:** Feature 2 (structured resolvers) now used in 6 policies (`lab`, `datesperiod`, `datesradio`, `species`, `datasetcontacts`, `sample`). Feature 5 (known divergences) now used in 8 policies.
- **Sample promoted to Tier A:** Sample policy is now execution-ready with three structured resolvers, known divergences, child sample-dimensions output, and resolver path coverage. Tier A now has 7 policies total; Tier B has 2 remaining (`sitelocations`, `siteotherproxies`).

### Feature 2 Conversion — Sitelocations And Siteotherproxies Policies (2026-06-20)

- **Sitelocations policy uses structured resolver for site ID:** the `resolve_site_id` helper was converted to a structured resolver with a single `trace_lookup` step that returns the traced site entity or empty entity. The resolver uses `SiteFromCodeDisallowDeletedSite` which extends `SiteFromTrace` and disallows deleted sites by returning `NO_TRACE` when the latest trace type is `DELETE`.
- **Siteotherproxies policy uses structured resolver for site ID:** same `resolve_site_id` resolver pattern as sitelocations — single `trace_lookup` step with `SiteFromCodeDisallowDeletedSite` trace lookup and deleted-site guard.
- **Helpers marked as superseded:** Both policies retain `resolve_site_id` in the helpers section for historical reference but marked as superseded with `used_by: []` and descriptions explaining the replacement by the structured resolver.
- **Known divergences added:** Both policies already had `known_divergences` for `replacement_expressed_as_row_actions`. Sitelocations added `location_expansion_adapter` (country/region expansion into location candidates is adapter-only). Siteotherproxies added `proxy_flag_expansion_adapter` (boolean proxy flags expanded into SEAD record types is adapter-only).
- **Six new fixture scenarios:** Three per policy — `site_resolved_via_trace_lookup` (success path), `site_resolver_returns_empty_when_no_trace_exists` (trace miss), and `site_resolver_returns_empty_when_site_deleted` (deleted site guard) exercise the resolver through the `resolver_path` intent.
- **Schema feature status updated:** Feature 2 (structured resolvers) now used in 8 policies (`lab`, `datesperiod`, `datesradio`, `species`, `datasetcontacts`, `sample`, `sitelocations`, `siteotherproxies`). Feature 5 (known divergences) now used in 10 policies.
- **Sitelocations and siteotherproxies promoted to Tier A:** Both policies are now execution-ready with structured resolvers, known divergences, one-to-many output with list reconciliation, and resolver path coverage. Tier A now has 9 policies total; Tier B has 0 remaining. All Tier B policies have been promoted to Tier A.