# Proposal: BugsCEP Importer Migration Runtime Decision Spike

## Status

- Proposed change request
- Scope: choose and prove the next implementation path for migrating the BugsCEP importer from Java-held behavior to policy-backed execution
- Goal: use the completed execution-ready policy set as the implementation contract for a focused design spike, then decide whether to continue with a direct Python policy runtime or a Shape Shifter flow plus a BugsCEP-specific automatic reconciliation step

## Summary

The BugsCEP policy-generation and machine-readable fidelity work is complete. All 35 reconciliation policies are now Tier A, execution-ready, and backed by 355 validation tests.

The next phase should stop expanding policy detail as its main goal and instead prove how the policies will be executed. This proposal recommends a short implementation decision phase built around one design spike. The spike should test both candidate implementation paths against the same policy contract and fixture expectations, then recommend one path or explicitly defer the choice if both remain viable.

The decision should be based on execution evidence, not preference. The first proof should use the geochronology golden reference and one site/contact persisted-action slice because together they exercise resolvers, postprocess behavior, related-output graphs, emitted outcomes, supporting outputs, and list-output action contracts.

## Recommendation

Proceed with a Phase 1 design spike before choosing the final runtime path.

Use the completed policy set as the shared implementation contract. Test both candidate paths against the same reference slices. Choose a path only when it can execute both reference slices with fixture-comparable output while keeping importer-specific behavior policy-driven and adapter-only behavior clearly separated. Defer only if both paths pass the same checks and differ mainly on operational or maintainability factors.

## Problem

The Java BugsCEP importer still contains the authoritative runtime behavior. The completed policy work now captures that behavior in machine-readable form, but there is not yet an implementation path that executes the full contract.

The remaining decision is not whether the policies are detailed enough to guide implementation. They are. The remaining decision is how to execute them without creating a second hidden policy system or losing parity with the Java importer.

Two implementation paths remain viable:

- a Python runtime that evaluates the policy contract directly
- a Shape Shifter flow plus a BugsCEP-specific automatic reconciliation step that preserves the same policy behavior

Choosing too early risks optimizing for architecture preference instead of importer parity. Waiting too long risks blocking implementation behind an unresolved option discussion.

## Scope

This proposal covers:

- the implementation decision needed after policy-generation completion
- the evidence required before choosing between the two runtime paths
- the first design spike that should produce that evidence
- the validation references that should anchor the decision
- the handoff documents needed for the next migration phase

## Non-Goals

This proposal does not attempt to:

- reopen broad policy generation or schema-fidelity work
- implement the Python runtime
- implement the Shape Shifter reconciliation path
- replace the Java importer in this phase
- decide all importer-family rollout order
- define production cutover mechanics
- remove or rewrite existing Java importer behavior

## Current Behavior

The completed policy baseline is documented in [BUGSCEP_POLICY_SCHEMA_MACHINE_READABLE_FIDELITY.md](../done/BUGSCEP_POLICY_GENERATION/BUGSCEP_POLICY_SCHEMA_MACHINE_READABLE_FIDELITY.md).

Current state:

- all 35 BugsCEP reconciliation policies are Tier A execution-ready
- 355 validation tests pass
- schema support exists for direct related-output references, structured resolvers, postprocess merge stages, shared emit blocks, and known divergences
- representative fixtures define resolver paths, ordered reconciliation results, supporting outputs, related-output graphs, postprocess results, list-output actions, and explicit action labels
- [BUGSCEP_POLICY_OPTION_MAPPING_NOTES.md](../done/BUGSCEP_POLICY_GENERATION/BUGSCEP_POLICY_OPTION_MAPPING_NOTES.md) keeps both downstream implementation paths open until a real execution-contract mismatch appears

The policy set is now a build contract. The missing piece is an implementation path that can execute that contract and prove parity against Java behavior.

## Proposed Design

### Decision Model

Use a design spike to produce implementation evidence before selecting the runtime path.

The spike should answer one question:

Can a candidate implementation path execute the shared policy contract while keeping policy behavior declared in the policy layer and limiting engine-specific code to adapter, orchestration, and persistence concerns?

A runtime path remains viable only if it can preserve:

- ordered reconciliation and prerequisite guards
- resolver lookup order and fallback behavior
- supporting-output and related-output identity flow
- postprocess retained-row and emitted-row behavior
- structured emitted outcomes
- persisted-action meaning for list-result updaters
- known divergence handling
- adapter-only boundaries

The decision rule is:

- choose a path if it executes both selected reference slices with fixture-comparable output and keeps policy-managed behavior in the policy layer
- defer the choice if both paths pass the same checks and the remaining differences are operational, maintainability, or rollout concerns
- reject a path for this migration if it needs hard-coded importer behavior that duplicates policy semantics outside the policy layer

### Adapter Boundary

The spike should use the following boundary as a review checklist.

| Policy-managed behavior | Adapter-only behavior |
|---|---|
| Source normalization rules that change matching or persisted values | Source file access and runtime configuration |
| Resolver order, fallback behavior, and emitted resolver outcomes | Repository access and query execution |
| Ordered reconciliation rules, prerequisite guards, and create-versus-update decisions | Persistence orchestration and transaction handling |
| Supporting-output and related-output identity flow | Runtime caching mechanics that do not change decisions |
| Postprocess grouping, retained rows, merge results, and conflict outcomes | Logging, diagnostics transport, and command wiring |
| Persisted-action intent for list-result updaters | Database connection management |
| Known divergence semantics | Test harness setup and fixture loading |

If implementation code changes matching, row identity, emitted outcomes, retained rows, persisted values, or output graph structure, that behavior is policy-managed and must not live only in adapter code.

### Candidate Path 1: Direct Python Policy Runtime

This path executes the policy contract directly.

Expected responsibilities:

- load policy YAML and fixture data
- evaluate source normalization rules, mappings, resolvers, reconciliation rules, postprocess rules, and emitted outcomes
- manage supporting-output and related-output graph behavior
- produce fixture-comparable result objects
- keep adapter logic limited to persistence orchestration, repository access, caching, and runtime plumbing

This path is strongest if the policy contract can be interpreted directly without creating a parallel implementation-specific rule layer.

### Candidate Path 2: Shape Shifter Plus BugsCEP Reconciliation

This path uses Shape Shifter for the parts that map naturally to its pipeline and adds a BugsCEP-specific reconciliation step for importer-specific behavior.

In this proposal, Shape Shifter means the existing Python transformation engine that reads configured sources, shapes rows through the extract, filter, link, unnest, translate, and store pipeline, maps source fields to target fields, and manages relationship-oriented output data. The expected Shape Shifter role is data shaping, mapping, pipeline execution, and output graph handling where those behaviors already fit the shared policy contract.

Expected responsibilities:

- map source and target row shaping into the Shape Shifter pipeline where appropriate
- preserve declared relationships, supporting outputs, and output graph behavior
- implement ordered reconciliation, trace-aware reuse, list-output side effects, and known BugsCEP update behavior in a BugsCEP-specific step
- ensure the BugsCEP step remains an adapter around the shared policy contract rather than becoming a separate policy language

This path is strongest if Shape Shifter can carry the data-shaping work while the reconciliation step preserves the declared policy behavior without duplicating it.

### Phase 1 Design Spike

The first implementation phase should test both paths against the same small but demanding reference set.

The spike should not attempt a full runtime. It should implement only enough execution to prove whether each path can produce fixture-comparable, traceable result objects for the selected slices.

Recommended reference slices:

- geochronology golden reference: validates resolvers, supporting outputs, related-output graph behavior, postprocess behavior, emitted outcomes, and row-change expectations
- site/contact persisted-action reference: validates list-output action contracts such as keep, append, replacement, deletion marking, and stop-before-update behavior

The spike should produce:

- a short implementation note for each candidate path
- a fixture comparison result for each reference slice attempted
- traceable intermediate decisions for source normalization, resolver choices, fallback use, reconciliation rules, supporting-output and related-output references, postprocess results, emitted outcomes, and persisted-action intent where applicable
- a list of policy-contract gaps, if any
- a list of adapter-boundary risks
- a recommendation to choose one path, continue comparing both, or stop because neither path preserves the contract cleanly

A candidate path fails the spike if it:

- requires hard-coded reconciliation branches that duplicate policy semantics
- cannot preserve ordered resolver behavior and fallback outcomes
- cannot represent list-output actions such as keep, append, deletion marking, replacement, or stop-before-update
- cannot produce traceable result objects that can be compared with the fixture result shapes
- moves policy-managed behavior into adapter-only code

### Handoff Documents

The decision phase requires these outputs:

- this implementation decision proposal
- a migration phase plan
- a Phase 1 design-spike task plan
- an implementation checkpoint inventory for all 35 policies/importers
- an adapter-boundary reference that separates policy-managed behavior from adapter-only runtime logic

Recommended locations:

- proposal, phase plan, and task plan: `docs/proposals/BUGSCEP_IMPORTER_MIGRATION_IMPLEMENTATION_DECISION/`
- implementation checkpoint inventory: either this proposal folder or `sead_bugs_import/doc/reconciliation_policies/`
- adapter-boundary reference: either this proposal folder or `sead_bugs_import/doc/reconciliation_policies/`

The owner and final location for the inventory and adapter-boundary reference remain open decisions. If the next phase is managed from the importer-policy side, place them beside the policy artifacts. If the next phase is managed mainly from Shape Shifter, place them under this proposal folder and link to the policy directory.

## Alternatives Considered

### Choose The Python Runtime Immediately

This is direct and likely maps cleanly to the current policy contract. It is still premature without proving how persistence, repository lookups, graph outputs, and known divergences behave against the golden slices.

### Choose The Shape Shifter Path Immediately

This aligns the migration with the larger Shape Shifter project. It is still premature because ordered reconciliation and list-output side effects require a BugsCEP-specific step that must not become a second hidden policy system.

### Keep Both Options Open Without A Decision Trigger

This avoids premature commitment but risks delaying implementation. The better approach is to keep both options open only until the Phase 1 spike produces evidence.

### Continue Policy Fidelity Work Before Implementation

This is no longer the highest-value next step. The policy set is execution-ready. Further policy changes should come from implementation findings, not from another broad authoring pass.

## Risks And Tradeoffs

- A direct Python runtime may duplicate behavior that Shape Shifter could already provide.
- A Shape Shifter path may hide BugsCEP-specific reconciliation behavior inside adapter code if the boundary is not enforced.
- Fixture parity may still miss production-data edge cases.
- Known divergences may be treated inconsistently unless they are classified before broad implementation.
- The runtime choice may drift if the design spike does not define a clear decision checkpoint.
- Policy schema changes discovered during implementation may create churn unless they are treated as explicit spike findings.

## Testing And Validation

The Phase 1 spike should validate candidate implementations with layered checks:

- schema and fixture validation for the existing policy set
- fixture comparison for the geochronology golden reference
- fixture comparison for one site/contact persisted-action slice
- Java comparison for the same result-object shape where a Java fixture already exists
- traceability review for source normalization, resolver decisions, reconciliation decisions, supporting-output and related-output references, postprocess results, emitted outcomes, and persisted-action intent
- review of adapter-only behavior against the option-mapping notes
- production-data comparison plan for later phases

Validation should prove behavior, not only parsing. A candidate path should not pass the spike if it can load policy YAML but cannot produce fixture-comparable resolver, reconciliation, supporting-output, related-output graph, postprocess, and list-output results for the selected slices.

## Acceptance Criteria

This proposal is complete when:

- the implementation decision proposal is accepted as the next-phase decision frame
- the Phase 1 spike reference slices are named
- the evidence required to choose or defer a runtime path is explicit
- the two candidate implementation paths are compared against the same shared policy contract
- adapter-only behavior is separated from policy-managed behavior
- follow-up documents are identified for phase sequencing, task execution, implementation tracking, and adapter-boundary control

The Phase 1 decision spike is complete when:

- at least one candidate path executes the selected reference slices or documents why it cannot
- fixture-comparable result objects are produced for the selected slices
- for each selected reference slice, the candidate path produces a traceable result object showing source normalization, resolver decisions, reconciliation decisions, supporting-output and related-output references, postprocess results, emitted outcomes, and persisted-action intent where applicable
- policy-contract gaps are recorded as explicit findings
- adapter-boundary risks are recorded
- the team can choose one implementation path or deliberately keep both open with a narrower next test

## Recommended Delivery Order

1. Create this implementation decision proposal.
2. Create the migration phase plan.
3. Create the Phase 1 design-spike task plan.
4. Create the implementation checkpoint inventory for all 35 policies/importers.
5. Create the adapter-boundary reference.
6. Run the Phase 1 spike against the geochronology and site/contact reference slices.
7. Decide whether to continue with the direct Python runtime, continue with Shape Shifter plus BugsCEP reconciliation, or run one more targeted comparison if both paths remain viable.

## Open Questions

- Which BugsCEP database snapshot should be the canonical production-data comparison set?
- Should implementation tracking live in the Shape Shifter proposal tree, beside the BugsCEP policy files, or both?
- Which known divergences are parity-required, policy-improved, or unresolved?
- Can policies be cut over importer by importer, or does the migration require a full 35-policy cutover?
- Which runtime layer owns repository access, caching, and persistence orchestration in each candidate path?

## Final Recommendation

Proceed with a Phase 1 design spike before choosing the final runtime path.

Use the completed policy set as the shared implementation contract. Test both candidate paths against the same reference slices. Choose the path only when one option proves it can execute the contract while keeping policy behavior in the policy layer, or when one option requires policy behavior to be restated outside that layer.