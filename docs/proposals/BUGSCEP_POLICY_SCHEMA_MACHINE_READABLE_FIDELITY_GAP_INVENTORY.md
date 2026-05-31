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
- The `species` related-output graph now also includes mixed create-and-reuse, family-reuse-only, missing-author, and no-data-shortcut scenarios so graph expectations are no longer limited to all-create and all-reuse trees.
- All six executable `species` related-output graph scenarios now carry explicit `row_changed` expectations, so the contract records whether the graph creates a new species row or reuses an existing one.
- `speciesassociation`, `speciesbiology`, `specieskeys`, `speciessynonyms`, and `speciesdistribution` now carry explicit no-write action labels in the existing-error reconciliation paths that are currently executable in fixtures.
- The remaining family work is to extend the same execution-facing contract to adjacent species policies whose reuse or graph behavior still relies on parity-only result kinds.

### 3. Site And Contact Update Family

- `site`
- `sitereferences`
- `datasetcontacts`
- `sitelocations`
- `siteotherproxies`

This group is the best current reference for ordered reconciliation plus persisted list-result side effects.

Current status:

- The simpler reconciliation-only families `speciesassociation`, `speciesbiology`, `specieskeys`, `speciessynonyms`, and `speciesdistribution` now expose explicit `persisted_action` labels for their insert and update write paths across 10 executable fixture slices.
- Four validated action-contract batches now add explicit no-write action labels for `country`, `period`, `lab`, `bibliography`, `mcrnames`, `mcrsummary`, `rdbcode`, `rdbsystem`, `rdb`, `site`, `sitereferences`, `taxanotes`, `taxaseasonality`, `ecocodegroup`, `ecocode_bugs`, `ecocode_koch`, `ecocodedefinition_bugs`, `ecocodedefinition_koch`, and the executable existing-error slices in `speciesassociation`, `speciesbiology`, `specieskeys`, `speciessynonyms`, and `speciesdistribution`.
- `datasetcontacts` supporting-contact fixtures now expose explicit `supporting_action` labels for generated and reused contact rows, and `sample` supporting-dimension fixtures now expose create, update, keep, and delete supporting actions.
- `sitelocations` and `siteotherproxies` now expose explicit `row_changed` expectations across all 10 executable list-output scenarios, so the contract records both row actions and whether the updater path reports a changed row.
- The remaining gap for that class of importer is the rest of the ordered reconciliation corpus that still relies on parity-only `result_kind` values rather than explicit stop or no-write action labels, plus any remaining list-output or graph families that still omit explicit change-state expectations.

### 4. Fossil Analysis-Entity Family

- `fossil`

This policy is the clearest current reference for configuration forks, supporting-output reuse, graph issues, and analysis-entity reuse failure paths.

Current status:

- `fossil` now exposes explicit `supporting_action` labels for supporting-output and related-output graph success paths, including clone-driven dataset creation, dataset reuse, analysis-entity creation, and analysis-entity reuse.
- The three fossil graph-issue scenarios now carry explicit `row_changed` expectations alongside the graph issue payload, so the contract records both the error and whether the Java path still reports a changed row.
- The remaining fossil gap is to decide whether the clone-versus-create distinction needs its own stable action label or whether `supporting_action: create` plus `updated_dataset_id` is the long-term contract.

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
2. Convert the remaining site and contact update behavior from parity-oriented result checks into richer execution contracts where list updates, deletes, graph reuse, and graph issues all carry explicit action semantics.
3. Extend the next graph policies that still rely on parity-only result kinds, graph-issue-only checks, or implicit reuse rules, now that both `species` and `fossil` provide richer graph baselines.
4. Extend explicit reconciliation action labels into the remaining error, guard, and keep-existing paths, then record any concrete divergences or adapter-only boundaries encountered during those slices instead of leaving them in fixture setup or test assumptions.