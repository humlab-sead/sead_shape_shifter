# Working Inventory: BugsCEP Policy Implementation Gaps

## Summary

This inventory identifies the highest-value gaps between the current BugsCEP policy corpus and an implementation-ready policy contract.

It is based on the current validated policy baseline, the fixture-backed comparison coverage already documented in the fidelity proposal, and the importer families that already exercise resolver, reconciliation, postprocess, supporting-output, related-output graph, and main-output list-result behavior.

The purpose of this inventory is to guide the next implementation slices. It is not a replacement for the fidelity proposal or the phase task plan.

## Current Position

The current baseline already covers a broad set of representative policies in `sead_bugs_import`, including:

- ordered reconciliation families such as `lab`, `bibliography`, `country`, `site`, `sitereferences`, `period`, `rdb`, `rdbcode`, `rdbsystem`, `mcrnames`, `mcrsummary`, `taxaseasonality`, `speciesdistribution`, and `taxanotes`
- resolver-driven families such as `datesradio`, `datesperiod`, and `lab`
- grouped postprocess and supporting-output families such as `datescalendar`, `datesperiod`, `datesradio`, `sample`, and `datasetcontacts`
- related-output graph families such as `species`, `datescalendar`, `datesperiod`, `datesradio`, and `fossil`
- main-output list-result families such as `datasetcontacts`, `siteotherproxies`, and `sitelocations`

That gives enough baseline coverage to move from parity-only work toward implementation-readiness work.

## Priority Gaps

### 1. End-To-End Identity And Supporting-Output Flow

**Why this matters**

Both downstream implementation options need a complete policy contract for how parent rows, supporting rows, and related outputs share identity and reuse state.

**What is still under-specified**

- where supporting-output identity must be treated as part of parent-row reconciliation rather than surrounding runtime glue
- which reuse paths are part of declared policy behavior versus repository or cache plumbing
- where parent mappings still depend on helper-style identity flow rather than explicit policy references

**Best current families for closing the gap**

- `datescalendar`
- `datesperiod`
- `datesradio`
- `fossil`
- `species`

### 2. Persisted Side Effects And Output Result Semantics

**Why this matters**

Implementation work needs to know not only which branch fired, but what row actions and side effects must happen.

**What is still under-specified**

- concrete row-action semantics for create, keep, replace, delete, and append behavior
- whether list-result behavior should remain in the current result-object shapes or promote a stronger execution-facing contract
- when updater-specific state transitions are policy-managed behavior versus adapter-only persistence handling

**Best current families for closing the gap**

- `datasetcontacts`
- `sitelocations`
- `siteotherproxies`
- `sample`

### 3. Helper-Derived Decision Rules That Still Hide In Java Behavior

**Why this matters**

The policies cannot serve as a build contract while important lookup or derivation behavior still depends on Java-only helper logic or implicit fixture setup.

**What is still under-specified**

- derived fallback and normalization rules that still live mainly in helper behavior
- guard and fallback paths whose emitted outcomes are only partially described in policy
- policy versus adapter boundaries for calculation or lookup glue that does not change persisted behavior

**Best current families for closing the gap**

- `lab`
- `datesradio`
- `datesperiod`
- `species`

### 4. Postprocess And Graph Behavior As Full Execution Contracts

**Why this matters**

The strongest current policies already describe grouped merge and related-output graph behavior, but downstream implementation still needs clearer expectations around retained rows, emitted rows, graph issues, and ordering-sensitive outputs.

**What is still under-specified**

- when postprocess ordering is part of the contract and not just current Java iteration behavior
- whether related-output graph expectations are complete enough to drive execution without reading manager classes
- where error and issue outcomes need to be treated as first-class execution outputs instead of validation-only evidence

**Best current families for closing the gap**

- `datescalendar`
- `datesperiod`
- `datesradio`
- `fossil`
- `species`

### 5. Known Divergences And Intentional Adapter Boundaries

**Why this matters**

Both implementation paths need explicit documentation of what the policy owns, what the adapter owns, and where current Java behavior is preserved only for parity.

**What is still under-specified**

- which surprising Java behaviors should be carried forward as known divergences
- which runtime mechanics should remain adapter-only for both paths
- which behaviors would mark the first hard divergence between the Python path and the Shape Shifter path

**Best current families for closing the gap**

- `datescalendar`
- `fossil`
- `rdb`
- `rdbcode`
- `site`

## Recommended Golden Reference Families

Start implementation-oriented golden reference work with the families below because together they cover the widest set of shared policy needs.

### 1. Geochronology Family

- `datescalendar`
- `datesperiod`
- `datesradio`

This group already covers resolvers, grouped postprocess behavior, supporting outputs, related-output graphs, emitted issues, and retained-row behavior.

### 2. Taxa Graph Family

- `species`
- `speciesassociation`
- `speciesbiology`
- `specieskeys`
- `speciessynonyms`

This group is the best current reference for related-output graphs, optional supporting outputs, and repository reuse within a multi-node output structure.

Current status:

- `species` now carries explicit `supporting_action` labels in both supporting-output and related-output graph fixtures.
- The remaining family work is to extend the same execution-facing contract to the adjacent species graph policies that still rely on parity-only result kinds.

### 3. Site And Contact Update Family

- `site`
- `sitereferences`
- `datasetcontacts`
- `sitelocations`
- `siteotherproxies`

This group is the best current reference for ordered reconciliation plus persisted list-result side effects.

Current status:

- The simpler reconciliation-only families `speciesassociation`, `speciesbiology`, `specieskeys`, `speciessynonyms`, and `speciesdistribution` now expose explicit `persisted_action` labels for their insert and update write paths across 10 executable fixture slices.
- The remaining gap for that class of importer is error and guard behavior that still relies on parity-only `result_kind` values rather than explicit stop or no-write action labels.

### 4. Fossil Analysis-Entity Family

- `fossil`

This policy is the clearest current reference for configuration forks, supporting-output reuse, graph issues, and analysis-entity reuse failure paths.

## Provisional Adapter-Only Boundaries

Treat the following as adapter-only unless a concrete implementation slice proves they need to move into policy:

- persistence orchestration details that do not change reconciliation or emitted outcomes
- runtime-specific cache implementation details
- batching mechanics that preserve the same declared postprocess and output behavior
- Shape Shifter stage wiring that preserves the same declared decisions and outputs
- Python runtime plumbing that evaluates the same declared decisions and outputs

If any of these mechanics changes matching, row identity, emitted issues, persisted values, retained rows, or output graph structure, it should move back into policy scope.

## Next Recommended Slices

1. Promote the geochronology family to the first golden execution-reference set and confirm that the policies describe end-to-end execution without reading Java helper code.
2. Convert the site and contact update family from parity-oriented result checks into clearer persisted-action contracts.
3. Extend the taxa graph family beyond `species`, starting with the next graph policies that still rely on parity-only result kinds or implicit reuse rules.
4. Extend explicit reconciliation write-action labels into the remaining error and guard paths, then record any concrete divergences or adapter-only boundaries encountered during those slices instead of leaving them in fixture setup or test assumptions.