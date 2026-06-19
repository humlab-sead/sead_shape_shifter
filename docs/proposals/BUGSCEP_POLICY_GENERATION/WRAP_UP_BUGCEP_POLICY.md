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