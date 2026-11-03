# Output Dataset Expectations

## Status

- Approved change request
- Scope: Check configured metrics on transformed entity output during a full run.
- Goal: Detect output that is structurally valid but unexpectedly empty, incomplete, or different in size.

## Summary

Add opt-in output expectations to project configuration. During a full transformation run, Shape Shifter will measure selected metrics on each entity's completed normalized output and compare them with configured limits. This adds a run-specific check alongside structural, data, and target-model conformance validation.

Start with entity row counts, distinct business-key counts, and row counts grouped by one output column. Report all mismatches as execution validation errors before output is dispatched or project tables are ingested. If any expectation fails, do not write output from the run.

## Problem

Structural validation checks the project configuration, data validation checks configured data rules, and conformance validation checks a project against its target model. These checks do not assert that a particular run produced the expected amount or distribution of data.

For example, the ArboDat project configuration selects a known set of projects in some entity queries, while other queries do not show the same filter. A project can pass its existing checks while a run produces an unexpected number of sites, datasets, or samples, or omits output for one of the intended projects.

## Scope

- Declare output expectations under `options.output_expectations`.
- Evaluate expectations against complete, normalized entity output during full dispatcher and project-table ingestion runs.
- Report each measured value, configured limit, entity, and pass or fail result, including the group value for grouped counts.
- Provide generic count metrics that can express entity totals, key cardinality, and expected group coverage.

## Non-Goals

- Replace structural, data, or target-model conformance validation.
- Validate sample or preview rows against full-output expectations.
- Apply output expectations to entity materialization or partial-entity preview and validation requests.
- Add arbitrary expressions, SQL metrics, totals across different units, or statistical profiling.
- Infer expected values or thresholds from a previous run.
- Guarantee that a passing metric proves the output is semantically correct.

## Current Behavior

The user guide describes YAML validation, sample and complete data validation, and conformance validation as separate checks. Data validators include column existence, natural-key uniqueness, and non-empty results. The documented workflow does not describe checks that compare metrics from a particular completed transformation run with project-specific expected values.

The core transformation pipeline runs Extract, Filter, Link, Unnest, Translate, and Store. In the full dispatcher workflow, optional column translation and foreign-key removal happen after normalization and before the dispatch call. Project-table ingestion also uses normalized tables but does not call the dispatcher. Both routes need a check before their respective output write.

## Proposed Design

Declare output expectations as a list in the existing project `options` section. Each expectation names an entity, metric, optional grouping column, and one comparison: `equals`, `min`, `max`, or both `min` and `max`.

```yaml
options:
  output_expectations:
    - name: expected-site-count
      entity: site
      metric: row_count
      equals: 7
    - name: dataset-count-range
      entity: dataset
      metric: row_count
      min: 10
      max: 15
    - name: sites-by-project
      entity: site
      metric: grouped_row_count
      column: Projekt
      groups:
        "19_0013":
          min: 1
        "19_0014":
          min: 1
```

The initial metric set should be:

- `row_count`: number of rows in the completed entity output.
- `distinct_key_count`: number of distinct combinations of the entity's configured business-key values. It is valid only when the entity declares keys. When keys are unique, this equals `row_count`, so this metric may be redundant with a row-count expectation; it is useful when expected identity cardinality is the requirement.
- `grouped_row_count`: row count for each explicitly configured value of one output column. Each named group is checked independently, and a configured group absent from the output has a count of zero. This metric produces a result per configured group rather than one scalar result. Unconfigured groups are not checked and do not cause failure.

Expectation columns use their configured, pre-translation names, as in the `Projekt` example. Evaluate all metrics on the complete normalized table set before optional foreign-key removal or column translation. Those output options must not change the measured values or the interpretation of a grouping column. Structural validation should reject unknown entity names, grouping columns that cannot be established from the configured output schema, unsupported metrics or comparisons, invalid numeric limits, and `min` values greater than `max`. It should also reject `distinct_key_count` for entities without configured keys. For projects with expectations, enforce these declaration checks before either write path even if optional pre-run validation is disabled.

Run the checks once after all required entities have finished normalization and before any dispatcher or ingester write. The metrics use output already held in memory and require no additional source queries. An expected entity absent from the completed table set, including one marked incomplete, fails each of its configured checks with a missing-entity reason and no measured value; do not treat it as an empty table. Evaluate every other configured expectation and group, including those for present entities with empty tables. Return structured results for every check, with the expectation name, entity, metric, group value when applicable, measured value when available, expected limit, pass or fail status, and failure reason when applicable. Expose the results on full execution and project-table ingestion API responses on both success and expectation failure; the CLI must also report the results and fail the run on a mismatch. A mismatch is an execution validation error, not a pre-run configuration error. Finish reporting all results before withholding dispatch or ingestion for the entire run. On an expectation failure, API execution reports failure regardless of whether optional pre-run validation was enabled; keep pre-run `validation_passed` distinct from the expectation result.

## Alternatives Considered

- **Use existing non-empty and uniqueness validators:** These detect generic data problems but cannot express a project-specific count or expected group coverage.
- **Add arbitrary aggregate expressions:** This could support sums and rates, but requires expression semantics, type handling, and safeguards that are not needed for the initial count-based use cases.
- **Compare with a saved prior run:** This can detect change but requires run identity, baseline storage, and a policy for approving baseline updates. Defer it.

## Risks And Tradeoffs

- Exact counts can become stale as source data changes. Expectations are opt-in, and maintainers must choose exact values or ranges appropriate to their data.
- Business-key counts depend on the configured entity keys accurately representing identity.
- Grouped expectations check only named groups; unexpected groups do not fail the expectation.
- Dispatcher output and project-table ingestion are written only after all expectation checks pass. This does not make downstream writes atomic if a dispatcher or ingester later fails for another reason.
- Counts can detect missing or extra output but cannot establish that the values themselves are correct.

## Testing And Validation

- Test each metric against complete normalized entity output, including empty results, duplicate business keys, missing expected groups, absent or incomplete entities, and unconfigured groups.
- Test exact, minimum, maximum, and inclusive range comparisons, as well as invalid configurations.
- Verify that optional translation and foreign-key removal do not change metric interpretation and that preview or sample output is not used to satisfy a full-output expectation.
- Verify that full execution and ingestion responses include every expectation result, including all failures and each grouped value, independently of optional pre-run validation.
- Verify that any failed expectation prevents dispatcher and project-table ingestion writes for the run, including when pre-run validation is disabled.

## Acceptance Criteria

- `P-AC-1` Project configuration can declare named output expectations for an entity using supported metrics and numeric comparisons.
- `P-AC-2` Structural validation reports invalid entity, metric, column, key, and limit declarations before a full run writes output, even when optional pre-run validation is disabled.
- `P-AC-3` Supported metrics are measured on complete normalized entity output using pre-translation column names, regardless of optional output transformations; preview and sample rows are not used.
- `P-AC-4` Full execution and project-table ingestion API responses report every check's measured value when available, expected limit, entity, metric, group value when applicable, pass or fail status, and failure reason when applicable, on both success and expectation failure. CLI runs report the same results.
- `P-AC-5` All configured expectations are evaluated and reported; an absent or incomplete expected entity fails explicitly. Any failed expectation is an execution validation error that prevents dispatcher output and project-table ingestion writes for the run.

## Planning Handoff

- Confirmed direction: add an opt-in, run-specific output check rather than extending target-model conformance rules.
- Initial metrics: entity row count, distinct configured business-key count, and row count for explicitly named groups in one output column.
- Preserve the existing pipeline order. Use configured column names and measure the complete normalized table set before optional output transformations and before either dispatcher or project-table ingester writes.
- Scope the check to full dispatcher and project-table ingestion runs, not previews, entity materialization, or partial-entity validation. Validate expectation declarations even when optional pre-run validation is disabled.
- Evaluate every configured expectation and group; mark an absent or incomplete expected entity as a failure with no measured value. Report structured results on success and expectation failure through both API routes and CLI, while keeping optional pre-run validation status distinct.
- Expected validation: invalid declarations prevent writes; comparisons use full normalized output; all results are reported; any failed check prevents dispatcher and project-table ingestion writes.

## Final Recommendation

Approve a first version of opt-in output expectations with the three count-based metrics above. Measure the complete normalized output before optional output transformations, keep group checks limited to configured values, and withhold dispatcher and ingester writes when any expectation fails. Defer arbitrary aggregates and historical run comparisons.
