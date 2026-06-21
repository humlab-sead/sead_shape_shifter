# Working Reference: BugsCEP Geochronology Golden Execution Set

## Summary

This document promotes the geochronology family to the first golden execution-reference set for BugsCEP policy work.

The goal is not to add a new design. The goal is to name the first policy group that future implementation work must be able to execute from policy and fixture contracts without reading Java helper code to understand the intended behavior.

## Scope

This reference covers the geochronology importer family:

- `datescalendar`
- `datesperiod`
- `datesradio`

It defines what this family already proves, what future runtime work must preserve, and what gaps still remain before the family can be treated as a stable build contract.

It does not replace the underlying policy files or fixture corpus.

## Why This Family Goes First

This family already covers the broadest shared contract needed by both downstream implementation options:

- ordered reconciliation against current SEAD state
- resolver-driven lookup behavior with fallback and emitted outcomes
- supporting-output creation and reuse
- related-output graph behavior
- grouped postprocess behavior with retained-row expectations
- graph issues and validation-facing error results

No other current family combines all of those behaviors as directly.

## Included Policy Roles

### `datescalendar`

Use as the reference for:

- grouped postprocess behavior
- retained-row and emitted-row expectations
- merged range generation versus singleton retention
- supporting `relative_age`, `dataset`, and `analysis_entity` outputs
- related-output graph behavior for relative-date persistence

### `datesperiod`

Use as the reference for:

- trace-first relative-date reconciliation
- resolver-driven method lookup behavior
- dataset and analysis-entity supporting outputs that update in place on traced rows
- dependency-driven `relative_age_id` reuse from the Period importer

### `datesradio`

Use as the reference for:

- trace-first geochronology reconciliation
- lab and uncertainty resolver behavior
- insert-only supporting-output creation for dataset and analysis entity
- field updates on the parent geochronology row without rebuilding the child graph
- emitted issues and flagged outcomes from resolver or validation paths

## Golden Execution Contract

Future runtime work should treat this family as golden only if all of the following are true.

### 1. End-To-End Policy Readability

For each included policy, a reader should be able to explain the full execution path from source row to persisted result using the policy and its fixtures alone:

- inputs and normalization rules
- reconciliation path
- supporting-output generation or reuse
- postprocess or graph behavior
- emitted outcomes
- persisted result shape

### 2. Result Shapes Stay Concrete

The family should keep using explicit result objects rather than branch-only evidence.

The current golden reference expects concrete coverage across these shapes where applicable:

- `resolver_result`
- `reconciliation_result`
- `postprocess_result`
- `postprocess_results`
- `graph_result`
- `graph_issue`

If a future implementation-facing shape is stronger than one of these, it should extend the contract rather than weaken it.

### 3. Supporting-Output Identity Flow Is Explicit

This family is the first place where future runtime work must not rely on hidden helper identity flow.

The contract must make clear:

- when a supporting row is created
- when a supporting row is reused
- when a supporting row is updated in place
- how the parent row obtains the supporting identity

### 4. Postprocess And Graph Behavior Are First-Class

For geochronology work, postprocess and graph behavior are part of the execution contract, not only validation evidence.

That means future work must preserve:

- retained-row behavior
- merge-versus-conflict behavior
- graph issue behavior
- create-versus-keep-versus-update behavior for supporting outputs

## Current Golden Reference Coverage

The current baseline already provides these strong anchors for this family:

- `datescalendar` proves grouped merge behavior, singleton retention, multi-output partition behavior, and relative-age plus dataset plus analysis-entity graph behavior
- `datesperiod` proves method resolution plus dataset and analysis-entity update behavior through the relative-date graph
- `datesradio` proves dating-lab resolution, uncertainty handling, insert-path dataset and analysis-entity creation, and parent-row update behavior on traced rows

Taken together, these policies already cover the richest shared contract in the current corpus.

## Remaining Gaps Before Promotion To Stable Build Contract

This family is the first golden set, but not yet a finished build contract.

The main remaining gaps are:

- clearer policy-owned rules for supporting-output identity flow versus adapter-only persistence mechanics
- clearer documentation of ordering-sensitive postprocess behavior where current Java iteration order still matters
- clearer classification of known divergences where current Java behavior is preserved only for parity
- fixture language that describes the execution contract directly, not only the current shared result-object comparison

## Immediate Use

Use this family first when:

- testing whether a new runtime can execute policy-managed reconciliation behavior without hidden Java helpers
- checking whether adapter logic is leaking policy decisions back into implementation glue
- deciding whether a new schema addition improves the shared contract for both downstream options

If a schema or fixture change makes this family less readable as an execution contract, treat that as a regression even if the parity tests still pass.