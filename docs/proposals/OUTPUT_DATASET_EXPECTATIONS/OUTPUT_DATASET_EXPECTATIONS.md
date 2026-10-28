# Output Dataset Expectations

## Status

- Proposed change request
- Scope: Check configured metrics on transformed entity output during a full run.
- Goal: Detect output that is structurally valid but unexpectedly empty, incomplete, or different in size.

## Summary

Add opt-in output expectations to project configuration. During a full transformation run, Shape Shifter will measure selected metrics on each entity's completed output and compare them with configured limits. This adds a run-specific check alongside structural, data, and target-model conformance validation.

Start with entity row counts, distinct business-key counts, and row counts grouped by one output column. Report all mismatches as execution validation errors before output is dispatched. If any expectation fails, do not dispatch output from the run.

## Problem

Structural validation checks the project configuration, data validation checks configured data rules, and conformance validation checks a project against its target model. These checks do not assert that a particular run produced the expected amount or distribution of data.

For example, the ArboDat project configuration selects a known set of projects in some entity queries, while other queries do not show the same filter. A project can pass its existing checks while a run produces an unexpected number of sites, datasets, or samples, or omits output for one of the intended projects.

## Scope

- Declare output expectations under `options.output_expectations`.
- Evaluate expectations against complete, transformed entity output during a full run.
- Report each measured value, configured limit, entity, and pass or fail result, including the group value for grouped counts.
- Provide generic count metrics that can express entity totals, key cardinality, and expected group coverage.

## Non-Goals

- Replace structural, data, or target-model conformance validation.
- Validate sample or preview rows against full-output expectations.
- Add arbitrary expressions, SQL metrics, totals across different units, or statistical profiling.
- Infer expected values or thresholds from a previous run.
- Guarantee that a passing metric proves the output is semantically correct.

## Current Behavior

The user guide describes YAML validation, sample and complete data validation, and conformance validation as separate checks. Data validators include column existence, natural-key uniqueness, and non-empty results. The documented workflow does not describe checks that compare metrics from a particular completed transformation run with project-specific expected values.

The core transformation pipeline runs Extract, Filter, Link, Unnest, Translate, and Store. Output expectations need the transformed values, so they should be evaluated after translation and before storage.

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

Structural validation should reject unknown entity names, unavailable grouping columns, unsupported metrics or comparisons, invalid numeric limits, and `min` values greater than `max`. It should also reject `distinct_key_count` for entities without configured keys.

Run these checks only against complete transformed output after translation and before dispatch. The metrics use output already held in memory and require no additional source queries. Evaluate every configured expectation and group, and include each result in the execution result with the expectation name, entity, metric, group value when applicable, measured value, expected limit, and pass or fail status. Treat mismatches as execution validation errors. If any expectation fails, finish reporting the expectation results but do not dispatch any output from the run.

## Alternatives Considered

- **Use existing non-empty and uniqueness validators:** These detect generic data problems but cannot express a project-specific count or expected group coverage.
- **Add arbitrary aggregate expressions:** This could support sums and rates, but requires expression semantics, type handling, and safeguards that are not needed for the initial count-based use cases.
- **Compare with a saved prior run:** This can detect change but requires run identity, baseline storage, and a policy for approving baseline updates. Defer it.

## Risks And Tradeoffs

- Exact counts can become stale as source data changes. Expectations are opt-in, and maintainers must choose exact values or ranges appropriate to their data.
- Business-key counts depend on the configured entity keys accurately representing identity.
- Grouped expectations check only named groups; unexpected groups do not fail the expectation.
- Output is dispatched only after all expectation checks pass. A mismatch therefore prevents dispatch for the run without adding entity-specific or dependent-entity storage rules.
- Counts can detect missing or extra output but cannot establish that the values themselves are correct.

## Testing And Validation

- Test each metric against complete transformed entity output, including empty results, duplicate business keys, missing expected groups, and unconfigured groups.
- Test exact, minimum, maximum, and inclusive range comparisons, as well as invalid configurations.
- Verify that preview or sample output is not used to satisfy a full-output expectation.
- Verify that the execution result includes every expectation result, including all failures and each grouped value.
- Verify that any failed expectation prevents output dispatch for the run.

## Acceptance Criteria

- `P-AC-1` Project configuration can declare named output expectations for an entity using supported metrics and numeric comparisons.
- `P-AC-2` Structural validation reports invalid entity, metric, column, key, and limit declarations before execution.
- `P-AC-3` Supported metrics are measured on complete, translated entity output and not on preview or sample rows.
- `P-AC-4` Execution results report each expectation's measured value, expected limit, entity, and pass or fail status, including the group value for grouped counts.
- `P-AC-5` All configured expectations are evaluated and reported; any failed expectation is an execution validation error that prevents output dispatch for the run.

## Planning Handoff

- Confirmed direction: add an opt-in, run-specific output check rather than extending target-model conformance rules.
- Initial metrics: entity row count, distinct configured business-key count, and row count for explicitly named groups in one output column.
- Preserve the existing pipeline order. Evaluate metrics on complete translated output before the relevant Store operation.
- Evaluate every configured expectation and group, then report all results. Treat mismatches as execution validation errors and withhold output dispatch for the run if any check fails.
- Expected validation: invalid declarations fail structural validation; metric comparisons use full output; execution reports measured and expected values, including group values; failed checks prevent output dispatch.

## Final Recommendation

Approve a first version of opt-in output expectations with the three count-based metrics above. Keep group checks limited to configured values, withhold run output when any expectation fails, and defer arbitrary aggregates and historical run comparisons.
