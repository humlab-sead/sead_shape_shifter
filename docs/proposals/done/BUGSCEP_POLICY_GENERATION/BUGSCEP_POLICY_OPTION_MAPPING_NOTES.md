# Working Notes: BugsCEP Policy Option Mapping And Divergence Checkpoint

## Summary

The current policy work still supports two downstream implementation options:

- a Python runtime that executes the policy contract directly
- a Shape Shifter flow plus a BugCEP-specific automatic reconciliation step

This document records how the shared policy contract maps to both options and where the first hard divergence should be declared if it becomes necessary.

## Scope

These notes cover the current implementation-ready policy target only.

They do not choose the runtime now. They define the shared contract both options must satisfy before a choice is forced.

## Shared Policy Contract

Both options need the policies to define the same core behavior:

- source contract and normalization expectations
- ordered reconciliation and prerequisite guards
- resolver-driven lookup behavior
- supporting-output and related-output graph behavior
- postprocess behavior, including retained rows and emitted rows
- emitted issues, warnings, ignored-item outcomes, and known divergences
- persisted-action meaning for list-result updaters

If a behavior changes matching, row identity, retained rows, emitted outcomes, persisted values, or output graph structure, it belongs in the shared policy contract before either runtime should specialize it.

## Mapping To The Python Runtime Option

The Python path maps most directly to the current policy contract.

Working expectation:

- policy source and normalization rules become runtime input contracts
- ordered reconciliation, resolvers, postprocess rules, and emitted outcomes become directly evaluated policy behavior
- supporting-output and related-output graph rules become runtime-managed graph creation or reuse behavior
- persisted-action contracts become explicit runtime update decisions
- adapter logic stays limited to persistence orchestration, caching mechanics, and repository access that do not change the declared policy decisions

This option is strongest when the policies already describe the behavior clearly enough that a runtime can execute it without reading Java helper code.

## Mapping To The Shape Shifter Option

The Shape Shifter path can use the same policy contract, but not all of that behavior maps to standard Shape Shifter stages by itself.

Working expectation:

- source contract and normalization expectations map naturally into extraction and normalization-oriented stages
- declared relationships, supporting outputs, and related-output graphs map naturally into data-shaping and graph-building behavior
- target-side field mapping and persisted row shape map naturally into translation and store-oriented stages
- ordered reconciliation, trace-aware reuse, known BugsCEP update rules, and list-result side effects require a BugCEP-specific automatic reconciliation step that preserves the declared policy behavior

This option remains viable only if that BugCEP-specific step can stay an adapter around the shared policy contract rather than becoming a second hidden policy language.

## First Divergence Checkpoint

Do not declare the two options divergent just because their runtime plumbing differs.

Declare the first hard divergence only if one of these becomes true:

- one option requires policy behavior to be restated in engine-specific control-flow terms
- one option cannot preserve the shared persisted-action contract without adding engine-specific semantics to the policy
- one option cannot execute the geochronology golden reference set or the site/contact persisted-action contracts without reading implementation-specific helper logic
- one option requires supporting-output or graph identity flow that cannot be expressed clearly in the shared policy contract

Until then, keep improving the shared contract rather than choosing a runtime prematurely.

## Current Evidence From Executable Policies

The shared policy contract now has two concrete divergence areas recorded from executable fixture work rather than only from planning notes:

- `created_supporting_rows_mark_updated`
	- Seen in the `datesperiod` and `datescalendar` families.
	- The fixtures now expose explicit `supporting_action` values such as `create`, `update`, `keep`, and `reuse` while preserving the current Java `updated: true` behavior as parity evidence.
	- This strengthens both runtime options because the action contract is now explicit even where the old Java status flag remains ambiguous.
- `replacement_expressed_as_row_actions`
	- Seen in the `sitelocations` and `siteotherproxies` families.
	- The fixtures now expose explicit `persisted_action` values such as `append_new`, `keep_existing`, `mark_for_deletion`, and `stop_before_list_update` while preserving the Java row-by-row replacement shape.
	- This confirms that the shared contract can describe replacement intent without requiring a separate engine-specific replacement primitive.

These two areas are still implementation-relevant, but they no longer force an early runtime decision because they are now named and testable in the shared policy layer.

## Decision Checkpoint

Choose between the two options only after all of the following evidence exists:

- the geochronology family remains readable as a golden execution-reference set
- the site and contact family has explicit persisted-action contracts rather than parity-only labels
- the highest-value known divergences are recorded explicitly
- the first concrete divergence areas are backed by executable fixture expectations instead of planning notes alone
- policy-managed behavior and adapter-only behavior are separated for the families being used as reference slices
- at least one candidate implementation path can explain how it will execute those reference slices without hidden Java helper behavior

If both options still satisfy that evidence, defer the decision.

## Current Recommendation

Keep both options open.

The right near-term work is still shared policy improvement, not runtime selection. The first decision should be forced by a real execution-contract mismatch, not by preference or by the existence of different adapter layers.