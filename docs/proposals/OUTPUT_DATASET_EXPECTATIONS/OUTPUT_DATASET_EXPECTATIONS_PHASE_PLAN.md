# Output Dataset Expectations Phase Plan

Source: [Output Dataset Expectations](OUTPUT_DATASET_EXPECTATIONS.md). This plan sequences the approved change.

## Summary

Deliver opt-in checks on complete normalized entity output before full-run writes. Establish configuration validation and a shared metric result first, then integrate the write gate and reporting into dispatcher execution, the CLI, and project-table ingestion.

## Problem

Existing validation does not compare the size or distribution of a completed run with project-specific expectations. Both full-run write paths need the same check before output can be written.

## Scope

This plan covers `options.output_expectations`, structural declaration checks, three count metrics, full-run reporting, and write prevention for failed expectations. It excludes previews, samples, entity materialization, partial-entity requests, arbitrary aggregates, and historical baselines.

## Current Position

- Project options are available to configuration validation and the core project; output expectations are not yet checked.
- Full dispatcher execution calls the shared workflow; project-table ingestion normalizes separately before passing tables to an ingester.
- Normalization currently applies optional foreign-key removal and column translation before returning tables to the ingester. Measurement must happen before these options on both paths.
- The proposal is approved but not implemented.

## Phase Plan

### Phase 1: Declare And Validate Expectations

**Goal**

Make expectation declarations validatable independently of optional pre-run validation.

**Focus**

- Support named entity expectations, the three supported metrics, grouped values, and exact or inclusive numeric limits under `options.output_expectations`.
- Reject invalid entity, column, key, metric, comparison, or limit declarations before either full-run write path, even when optional validation is off.

**Depends On**

- Approved source proposal.

**Outputs**

- A validated configuration contract available to both full-run paths.

**Acceptance Criteria**

- `PH1-AC-1` (from `P-AC-1`) Valid declarations accept `row_count`, `distinct_key_count`, and `grouped_row_count` with `equals`, `min`, `max`, or an inclusive range.
- `PH1-AC-2` (from `P-AC-2`) Invalid entity, pre-translation grouping column, missing business keys, metric, or numeric limit declarations fail before either write, including when optional pre-run validation is disabled.

**Validation Milestones**

- `VM-1` Valid and invalid declaration checks cover `PH1-AC-1` and `PH1-AC-2`, including disabled optional validation.

**Task-Plan Handoff**

- Source criteria: `P-AC-1`, `P-AC-2`. Preserve configured column names and the separation between mandatory expectation declaration checks and optional pre-run checks. Confirm how the configured output schema establishes grouping columns during task planning.

**Readiness**

Ready for a task plan.

### Phase 2: Measure Complete Normalized Output

**Goal**

Produce all expectation results from the completed table set before output transformations or writes.

**Focus**

- Measure row counts, distinct configured key combinations, and counts for explicitly named groups; use zero for named groups missing from a present table.
- Report each configured check, including absent or incomplete entities with no measured value and a missing-entity reason; keep unconfigured groups out of the result.

**Depends On**

- Phase 1's validated configuration contract.

**Outputs**

- A shared complete-run result set and overall pass/fail decision, available before optional output transformations.

**Acceptance Criteria**

- `PH2-AC-1` (from `P-AC-3`) Metrics use complete normalized tables and configured pre-translation names; foreign-key removal and column translation cannot change the measured values.
- `PH2-AC-2` (from `P-AC-5`) Every configured expectation and named group is evaluated, with an explicit failure and no measurement for an absent or incomplete expected entity.
- `PH2-AC-3` (from `P-AC-4`) Each result includes the name, entity, metric, applicable group, measured value when available, expected limit, status, and failure reason when applicable.

**Validation Milestones**

- `VM-2` Complete and empty tables, duplicate keys, missing and extra groups, and absent or incomplete entities cover `PH2-AC-1`, `PH2-AC-2`, and `PH2-AC-3`; comparisons cover exact and inclusive bounds.

**Task-Plan Handoff**

- Source criteria: `P-AC-3`, `P-AC-4`, `P-AC-5`. Measure once after all required entities finish, before transformations, without additional source queries. Resolve the handling of null key combinations and null group values before defining metric tests.

**Readiness**

Requires a decision on null-value counting semantics for distinct keys and grouped values.

### Phase 3: Gate Dispatcher Execution And Report CLI Results

**Goal**

Withhold dispatcher output on any failed expectation and expose every result through full execution and CLI runs.

**Focus**

- Use Phase 2 results before dispatcher writes, regardless of optional pre-run validation; report all failures rather than stopping at the first mismatch.
- Include structured results on full execution API success and expectation failure; keep `validation_passed` specific to optional pre-run validation. Make the CLI report results and exit unsuccessfully on mismatch.

**Depends On**

- Phase 2's complete-run result set and resolved null-value semantics.

**Outputs**

- Full dispatcher execution and CLI runs gated and reporting expectation results.

**Acceptance Criteria**

- `PH3-AC-1` (from `P-AC-4`) Full execution responses and CLI runs report every result on success and expectation failure without conflating expectation status with pre-run `validation_passed`.
- `PH3-AC-2` (from `P-AC-5`) A failed check makes full execution fail and prevents dispatcher output even with pre-run validation disabled; the CLI exits unsuccessfully.
- `PH3-AC-3` (from `P-AC-3`) Dispatcher runs use the complete pre-transformation table set, never sampled or preview output.

**Validation Milestones**

- `VM-3` Full-run success and failure with optional validation enabled and disabled cover `PH3-AC-1`, `PH3-AC-2`, and `PH3-AC-3`, including no dispatcher write on mismatch.

**Task-Plan Handoff**

- Source criteria: `P-AC-3`, `P-AC-4`, `P-AC-5`. Preserve the existing pipeline order. Expectation failure is an execution validation error, not a pre-run configuration error; successful checks may proceed through existing dispatch behavior.

**Readiness**

Requires Phase 2's null-value decision and result contract.

### Phase 4: Gate Project-Table Ingestion

**Goal**

Apply the same full-output check and reporting to project-table ingestion without changing preview or validation-only behavior.

**Focus**

- Evaluate the shared results before ingester writes, even when optional output transformations are requested.
- Include all results in ingestion API responses on success and expectation failure; retain existing behavior for requests outside full ingestion scope.

**Depends On**

- Phase 2's shared measurement contract and Phase 3's verified write-gate behavior.

**Outputs**

- Both full-run write paths enforce output expectations and report results.

**Acceptance Criteria**

- `PH4-AC-1` (from `P-AC-4`) Project-table ingestion responses include every expectation result on success and expectation failure, including each configured group.
- `PH4-AC-2` (from `P-AC-5`) Any failed expectation prevents all project-table ingestion writes for that run; absent or incomplete expected entities fail explicitly.
- `PH4-AC-3` (from `P-AC-3`) Ingestion measures complete output before translation or foreign-key removal; previews, samples, materialization, and partial-entity requests do not evaluate full-output expectations.

**Validation Milestones**

- `VM-4` Full ingestion pass/fail checks, optional output transformations, and excluded request types cover `PH4-AC-1`, `PH4-AC-2`, and `PH4-AC-3`; both full-run paths preserve their existing behavior when no expectations are configured.

**Task-Plan Handoff**

- Source criteria: `P-AC-3`, `P-AC-4`, `P-AC-5`. Preserve ingestion's existing downstream validation and write flow after checks pass. No expectation result should be derived from post-transformation tables or validation-only requests.

**Readiness**

Requires Phase 2's null-value decision and the verified contracts from Phases 2 and 3.

## Cross-Phase Rules

- Do not enable a write path until its declaration checks, complete-output measurements, reporting, and no-write-on-failure behavior are validated together.
- Keep expectation results and optional pre-run validation status distinct. Projects without expectations retain their existing full-run behavior.
- Do not treat output write failures after expectations pass as an atomicity guarantee.

## Validation Strategy

Validate configuration independently first (`VM-1`), then metric and result behavior against complete normalized tables (`VM-2`). Validate the dispatcher and CLI gate (`VM-3`) before the ingestion gate (`VM-4`), with regression coverage for output transformations, excluded request types, and projects without expectations.