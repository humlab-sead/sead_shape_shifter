# Proposal: BugsCEP Importer Migration Runtime Decision Spike

## Status

- Proposed change request
- Scope: choose and test the next implementation path for moving the BugsCEP importer from Java-owned behavior to policy-driven execution
- Goal: use the finished execution-ready BugsCEP importer policy set as the implementation contract for a focused "design spike", then decide whether to continue with a direct Python policy runtime or a Shape Shifter flow plus a BugsCEP-specific automatic reconciliation step

## Summary

The policy-generation and machine-readable fidelity work for BugsCEP is complete. All 35 reconciliation policies are now Tier A, execution-ready, and covered by 355 validation tests.

The next phase should stop treating policy authoring as the main task. The main task is now proving how those policies will run. This proposal recommends a short decision phase built around one design spike. In this document, a design spike means a small, time-boxed proof-of-concept implementation that tests a risky design question with real code and real outputs before the team commits to a larger build. The spike should test both candidate implementation paths against the same policy contract and the same fixture expectations. It should then recommend one path or clearly state why the decision should stay open a little longer.

The decision should be based on working results, not architecture preference. The first proof should use the geochronology golden reference and one site/contact persisted-action case. Together, those examples cover resolvers, postprocess behavior, related-output graphs, emitted outcomes, supporting outputs, and list-output action contracts.

## Recommendation

Run a Phase 1 design spike before choosing the final runtime path.

Use the completed policy set as the shared implementation contract. Test both candidate paths against the same reference cases. Choose a path only when it can execute both reference cases with fixture-comparable output while keeping importer-specific behavior in the policy contract and limiting adapter code to runtime plumbing. Delay the choice only if both paths pass the same checks and the remaining differences are mostly about operations or maintainability.

## Problem

The Java BugsCEP importer still contains the real runtime behavior. The completed policy work now describes that behavior in machine-readable form, but there is still no implementation path that executes the full contract.

The open question is no longer whether the policies are detailed enough. They are. The open question is how to run them without creating a second hidden rule system or losing parity with the Java importer.

Two implementation paths are still realistic:

- a Python runtime that evaluates the policy contract directly
- a Shape Shifter flow plus a BugsCEP-specific automatic reconciliation step that preserves the same policy behavior

Choosing too early risks picking a path because it looks cleaner on paper. Waiting too long risks blocking implementation with an unresolved design discussion.

## Scope

This proposal covers:

- the implementation decision that comes after policy-generation completion
- the evidence needed before choosing between the two runtime paths
- the first design spike that should produce that evidence
- the validation references that should guide the decision
- the handoff documents needed for the next migration phase

## Non-Goals

This proposal does not attempt to:

- reopen broad policy-generation or schema-fidelity work
- implement the Python runtime
- implement the Shape Shifter reconciliation path
- replace the Java importer in this phase
- decide rollout order for all importers
- define production cutover steps
- remove or rewrite existing Java importer behavior

## Current Behavior

The completed policy baseline is documented in [BUGSCEP_POLICY_SCHEMA_MACHINE_READABLE_FIDELITY.md](../done/BUGSCEP_POLICY_GENERATION/BUGSCEP_POLICY_SCHEMA_MACHINE_READABLE_FIDELITY.md).

Current state:

- all 35 BugsCEP reconciliation policies are Tier A and execution-ready
- 355 validation tests pass
- schema support exists for direct related-output references, structured resolvers, postprocess merge stages, shared emit blocks, and known divergences
- representative fixtures define resolver paths, ordered reconciliation results, supporting outputs, related-output graphs, postprocess results, list-output actions, and explicit action labels
- [BUGSCEP_POLICY_OPTION_MAPPING_NOTES.md](../done/BUGSCEP_POLICY_GENERATION/BUGSCEP_POLICY_OPTION_MAPPING_NOTES.md) keeps both downstream implementation paths open until a real execution-contract mismatch appears

The policy set is now the build contract. What is still missing is an implementation path that can execute that contract and prove parity with Java behavior.

## Proposed Design

### Decision Model

Use a design spike to gather implementation evidence before selecting the runtime path.

The spike should answer one question:

Can a candidate implementation path execute the shared policy contract while keeping business rules in the policy layer and limiting engine-specific code to adapter, orchestration, and persistence work?

A runtime path stays viable only if it can preserve:

- ordered reconciliation and prerequisite guards
- resolver lookup order and fallback behavior
- supporting-output and related-output identity flow
- postprocess retained-row and emitted-row behavior
- structured emitted outcomes
- persisted-action meaning for list-result updaters
- known divergence handling
- adapter-only limits

The decision rule is:

- choose a path if it executes both selected reference cases with fixture-comparable output and keeps policy-managed behavior in the policy layer
- delay the choice if both paths pass the same checks and the remaining differences are mostly about operations, maintainability, or rollout concerns
- reject a path for this migration if it needs hard-coded importer behavior that copies policy meaning outside the policy layer

### Adapter Boundary

Use the following split as a review checklist during the spike.

| Policy-managed behavior                                                               | Adapter-only behavior                                  |
|---------------------------------------------------------------------------------------|--------------------------------------------------------|
| Source normalization rules that change matching or persisted values                   | Source file access and runtime configuration           |
| Resolver order, fallback behavior, and emitted resolver outcomes                      | Repository access and query execution                  |
| Ordered reconciliation rules, prerequisite guards, and create-versus-update decisions | Persistence orchestration and transaction handling     |
| Supporting-output and related-output identity flow                                    | Runtime caching mechanics that do not change decisions |
| Postprocess grouping, retained rows, merge results, and conflict outcomes             | Logging, diagnostics transport, and command wiring     |
| Persisted-action intent for list-result updaters                                      | Database connection management                         |
| Known divergence semantics                                                            | Test harness setup and fixture loading                 |

If implementation code changes matching, row identity, emitted outcomes, retained rows, persisted values, or output graph structure, that behavior belongs in the policy layer and must not exist only in adapter code.

### Candidate Path 1: Direct Python Policy Runtime

This path executes the policy contract directly.

Expected responsibilities:

- load policy YAML and fixture data
- evaluate source normalization rules, mappings, resolvers, reconciliation rules, postprocess rules, and emitted outcomes
- manage supporting-output and related-output graph behavior
- produce fixture-comparable result objects
- keep adapter logic limited to persistence orchestration, repository access, caching, and runtime plumbing

This path is strongest if the policy contract can be interpreted directly without adding a second implementation-specific rule layer.

### Candidate Path 2: Shape Shifter Plus BugsCEP Reconciliation

This path uses Shape Shifter for the parts that already fit its pipeline and adds a BugsCEP-specific reconciliation step for the remaining importer-specific behavior.

In this proposal, Shape Shifter means the existing Python transformation engine that reads configured sources, moves rows through the extract, filter, link, unnest, translate, and store pipeline, maps source fields to target fields, and manages relationship-based output data. Its expected role here is data shaping, field mapping, pipeline execution, and output graph handling where those behaviors already match the shared policy contract.

Expected responsibilities:

- map source and target row shaping into the Shape Shifter pipeline where that is a natural fit
- preserve declared relationships, supporting outputs, and output graph behavior
- implement ordered reconciliation, trace-aware reuse, list-output side effects, and known BugsCEP update behavior in a BugsCEP-specific step
- ensure the BugsCEP step stays an adapter around the shared policy contract rather than becoming a separate rule language

This path is strongest if Shape Shifter can handle the data-shaping work while the reconciliation step still follows the declared policy behavior without copying it somewhere else.

### Phase 1 Design Spike

The first implementation phase should test both paths against the same small but demanding set of reference cases.

The spike should not try to build a full runtime. It should implement only enough behavior to prove whether each path can produce fixture-comparable, traceable result objects for the selected cases.

Recommended reference cases:

- geochronology golden reference: validates resolvers, supporting outputs, related-output graph behavior, postprocess behavior, emitted outcomes, and row-change expectations
- site/contact persisted-action reference: validates list-output action contracts such as keep, append, replacement, deletion marking, and stop-before-update behavior

The spike should produce:

- a short implementation note for each candidate path
- a fixture comparison result for each reference case that was attempted
- traceable intermediate decisions for source normalization, resolver choices, fallback use, reconciliation rules, supporting-output and related-output references, postprocess results, emitted outcomes, and persisted-action intent where applicable
- a list of policy-contract gaps, if any
- a list of adapter-boundary risks
- a recommendation to choose one path, continue comparing both, or stop because neither path preserves the contract cleanly

A candidate path fails the spike if it:

- requires hard-coded reconciliation branches that copy policy meaning
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

The owner and final location for the inventory and adapter-boundary reference are still open decisions. If the next phase is managed mainly from the importer-policy side, place them beside the policy artifacts. If the next phase is managed mainly from Shape Shifter, place them under this proposal folder and link back to the policy directory.

## Alternatives Considered

### Choose The Python Runtime Immediately

This is the most direct option and likely maps cleanly to the current policy contract. It is still too early to choose without proving how persistence, repository lookups, graph outputs, and known divergences behave against the reference cases.

### Choose The Shape Shifter Path Immediately

This aligns the migration with the larger Shape Shifter project. It is still too early to choose because ordered reconciliation and list-output side effects require a BugsCEP-specific step, and that step must not turn into a second hidden rule system.

### Keep Both Options Open Without A Decision Trigger

This avoids early commitment but risks delaying implementation. The better option is to keep both paths open only until the Phase 1 spike produces evidence.

### Continue Policy Fidelity Work Before Implementation

This is no longer the highest-value next step. The policy set is already execution-ready. Further policy changes should come from implementation findings, not from another broad authoring pass.

## Risks And Tradeoffs

- A direct Python runtime may reimplement behavior that Shape Shifter already provides.
- A Shape Shifter path may hide BugsCEP-specific reconciliation behavior inside adapter code if the adapter limit is not enforced.
- Fixture parity may still miss edge cases from real production data.
- Known divergences may be handled inconsistently unless they are classified before broader implementation.
- The runtime choice may drift if the design spike does not end with a clear decision checkpoint.
- Policy schema changes discovered during implementation may create churn unless they are recorded as explicit spike findings.

## Testing And Validation

The Phase 1 spike should validate candidate implementations with layered checks:

- schema and fixture validation for the existing policy set
- fixture comparison for the geochronology golden reference
- fixture comparison for one site/contact persisted-action case
- Java comparison for the same result-object shape where a Java fixture already exists
- traceability review for source normalization, resolver decisions, reconciliation decisions, supporting-output and related-output references, postprocess results, emitted outcomes, and persisted-action intent
- review of adapter-only behavior against the option-mapping notes
- a production-data comparison plan for later phases

Validation should prove behavior, not just parsing. A candidate path should not pass the spike if it can load policy YAML but cannot produce fixture-comparable resolver, reconciliation, supporting-output, related-output graph, postprocess, and list-output results for the selected cases.

## Acceptance Criteria

This proposal is complete when:

- the implementation decision proposal is accepted as the frame for the next phase
- the Phase 1 spike reference cases are named
- the evidence needed to choose or delay a runtime path is explicit
- the two candidate implementation paths are compared against the same shared policy contract
- adapter-only behavior is separated from policy-managed behavior
- follow-up documents are identified for phase sequencing, task execution, implementation tracking, and adapter-boundary control

The Phase 1 decision spike is complete when:

- at least one candidate path executes the selected reference cases or documents why it cannot
- fixture-comparable result objects are produced for the selected cases
- for each selected reference case, the candidate path produces a traceable result object showing source normalization, resolver decisions, reconciliation decisions, supporting-output and related-output references, postprocess results, emitted outcomes, and persisted-action intent where applicable
- policy-contract gaps are recorded as explicit findings
- adapter-boundary risks are recorded
- the team can choose one implementation path or deliberately keep both open with one narrower next test

## Recommended Delivery Order

1. Create this implementation decision proposal.
2. Create the migration phase plan.
3. Create the Phase 1 design-spike task plan.
4. Create the implementation checkpoint inventory for all 35 policies/importers.
5. Create the adapter-boundary reference.
6. Run the Phase 1 spike against the geochronology and site/contact reference cases.
7. Decide whether to continue with the direct Python runtime, continue with Shape Shifter plus BugsCEP reconciliation, or run one more targeted comparison if both paths remain viable.

## Open Questions

- Which BugsCEP database snapshot should be the main production-data comparison set?
- Should implementation tracking live in the Shape Shifter proposal tree, beside the BugsCEP policy files, or in both places?
- Which known divergences are required for parity, which are accepted improvements, and which are still unresolved?
- Can policies be cut over one importer at a time, or does the migration require all 35 policies at once?
- Which runtime layer should own repository access, caching, and persistence orchestration in each candidate path?

## Final Recommendation

Run a Phase 1 design spike before choosing the final runtime path.

Use the completed policy set as the shared implementation contract. Test both candidate paths against the same reference cases. Choose a path only when one option proves it can execute the contract while keeping policy behavior in the policy layer, or when one option shows that the other path would need policy behavior to be restated outside that layer.
