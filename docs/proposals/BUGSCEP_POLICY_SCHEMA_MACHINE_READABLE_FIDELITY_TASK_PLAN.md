# Task Plan: BugsCEP Policy Schema Machine-Readable Fidelity Remaining Work

## Phase Summary

- Phase: Raise policy detail to implementation-ready fidelity
- Status: In progress
- Goal: make the BugsCEP policies detailed enough to serve as a build contract for either a Python runtime that implements the policies directly or a Shape Shifter flow plus a BugCEP-specific automatic reconciliation step
- Focus: close the remaining gaps between current policy YAML and actual importer behavior so the policies describe runtime inputs, decision rules, side effects, reconciliation semantics, and output expectations precisely enough to drive implementation work instead of only parity checks

**Acceptance Criteria**

- [ ] The plan defines a common policy-readiness target that supports both end-game options up to the point where they intentionally diverge.
- [ ] Remaining Java-only behavior is classified as either policy detail to add, explicit non-goal, or implementation-specific adapter logic.
- [ ] At least one representative importer family has policy coverage detailed enough to describe end-to-end execution, including reconciliation behavior, postprocess rules, output side effects, and validation expectations.
- [ ] The policy artifacts and fixture corpus are organized so they can be used as implementation inputs, not only as test fixtures.
- [ ] Focused validation passes before `make validate-policy-format` runs.
- [ ] The fidelity proposal and this task plan stay aligned with the new end-game.

## Work Breakdown

### 1. Define Execution-Ready Policy Criteria

**Objective**

Set the minimum policy detail needed before either downstream path can be implemented with confidence.

**Tasks**

- [x] Define the shared requirements that both end-game options need from the policies: source contract, identity rules, reconciliation steps, postprocess behavior, output graph rules, emitted issues, and validation expectations.
- [x] Separate those shared requirements from the option-specific parts: a pure Python execution runtime versus Shape Shifter plus a BugCEP-specific automatic reconciliation step.
- [x] Add an explicit readiness checklist to the companion proposal or phase notes so the team can judge when a policy is detailed enough for implementation.
- [x] Record what remains intentionally outside policy scope and must stay in runtime glue code or adapters.

**Completion Criteria**

There is a written execution-readiness definition that can be applied consistently to importer policies regardless of which downstream implementation path is chosen.

### 2. Close Policy Semantics Gaps

**Objective**

Fill the remaining behavior gaps that still live mainly in Java code, comments, or fixture helpers.

**Tasks**

- [x] Review the current covered importers and list the remaining behavior that is still under-specified for implementation, such as derived values, reconciliation branches, postprocess grouping rules, supporting-output creation rules, and update side effects.
- [ ] Prioritize gaps that block both end-game options first, especially behaviors that affect row identity, matching, range merging, dataset or analysis-entity creation, and update versus insert rules.
- [x] Extend the relevant policy files and fixture conventions only as far as needed to express those behaviors concretely.
- [x] Mark any behavior that cannot or should not move into policy as explicit adapter logic for the Python path or the Shape Shifter reconciliation step.

**Completion Criteria**

The highest-value runtime behaviors that still block implementation are either encoded in policy or explicitly classified as adapter-only logic.

### 3. Prepare Implementation-Oriented Fixtures And Outputs

**Objective**

Turn the current parity corpus into a more implementation-ready reference set.

**Tasks**

- [x] Identify a small representative set of importer families whose fixtures can act as golden reference cases for future implementation work.
- [x] Ensure those fixtures describe not only branch selection but also the concrete result shape expected from execution: row actions, emitted issues, retained rows, supporting outputs, and postprocess outputs.
- [x] Add any missing fixture metadata or expected-output structure needed for a future Python runtime or Shape Shifter adapter to consume the policies as a contract.
- [ ] Keep the result shapes aligned with the current shared contracts such as `resolver_result`, `reconciliation_result`, `postprocess_result`, `postprocess_results`, `graph_result`, `graph_issue`, and `output_result` unless a stronger implementation-facing shape is clearly needed.

**Completion Criteria**

There is a representative policy-plus-fixture subset that can act as a golden execution reference for either implementation path.

### 4. Add Option-Specific Mapping Notes And Decision Checkpoint

**Objective**

Keep both downstream implementation options viable while making the differences explicit.

**Tasks**

- [x] For the Python-runtime option, identify which policy features can map directly to runtime components and which ones still require orchestration or persistence code outside the policies.
- [x] For the Shape Shifter option, identify which policy features map naturally into existing Shape Shifter stages and which ones require a BugCEP-specific automatic reconciliation step before, within, or after the standard flow.
- [x] Record the first hard divergence point between the two options so the team can defer that decision while still improving the shared policy contract.
- [x] Add a decision checkpoint that states what evidence is needed before choosing one implementation path over the other.

**Completion Criteria**

The task plan keeps both options open but makes the boundary between shared policy work and option-specific implementation work explicit.

### 5. Validate And Sync Companion Docs

**Objective**

Ship policy-readiness work only after focused validation passes and the docs describe the same end-game.

**Tasks**

- [x] Run focused validation for the touched policy, fixture, harness, and Java parity areas.
- [x] Run `make validate-policy-format` in `sead_bugs_import` after the narrow checks pass.
- [ ] Update `docs/proposals/BUGSCEP_POLICY_SCHEMA_MACHINE_READABLE_FIDELITY.md` if the coverage statement, non-goals, or recommendation changes under the new end-game.
- [ ] Keep this task plan aligned with the current remaining work instead of repeating completed slice history.

**Completion Criteria**

Focused validation passes first, the broad validation target stays green, and the proposal plus task plan reflect the same implementation-oriented end-game.

## Progress Tracker

| Area | Status | Notes |
|---|---|---|
| Define execution-ready policy criteria | Done | Checklist and adapter-boundary rules are now captured in the companion fidelity proposal. |
| Close policy semantics gaps | In progress | First concrete divergence areas are recorded in the datesperiod, datescalendar, sitelocations, and siteotherproxies policies; `species` now exposes explicit supporting_action labels; five simpler reconciliation families expose explicit write-action labels; the first error-and-guard batch covered `period`, `lab`, `bibliography`, `rdbcode`, `rdbsystem`, `ecocodedefinition_bugs`, `ecocodedefinition_koch`, and `speciesassociation`; the next batch extended explicit no-write actions to `site`, `sitereferences`, `rdb`, `taxaseasonality`, `speciesbiology`, `specieskeys`, `speciessynonyms`, and `speciesdistribution`; and the current slice now extends that same no-write contract to `country`, `mcrnames`, and `taxanotes`. |
| Prepare implementation-oriented fixtures and outputs | In progress | Geochronology graph fixtures carry supporting_action, the site/contact list families carry persisted_action, `species` starts the taxa graph family rollout, 10 reconciliation-only slices carry explicit write-action labels, the no-write contract now covers more of the ordered-reconciliation corpus, and the `species` graph baseline now includes a mixed create-and-reuse related-output scenario instead of only all-create and all-reuse trees. |
| Add option-specific mapping notes and decision checkpoint | Done | The option mapping notes now keep both paths open and define the first divergence checkpoint. |
| Validate and sync companion docs | In progress | Focused validation and `make validate-policy-format` are green for this slice; remaining work is to keep the companion proposal set aligned as more families are upgraded. |

## Definition Of Done

- [ ] A shared execution-readiness checklist exists for BugsCEP policies.
- [ ] The next phase improves policy detail toward implementation readiness, not only broader test-harness execution.
- [ ] Representative policies and fixtures can act as a concrete build contract for either downstream option up to the documented divergence point.
- [ ] Policy-managed behavior and adapter-only behavior are explicitly separated.
- [x] Focused validation passes for the touched areas.
- [ ] `make validate-policy-format` passes after the phase lands.
- [ ] `docs/proposals/BUGSCEP_POLICY_SCHEMA_MACHINE_READABLE_FIDELITY.md` and this task plan both describe the same end-game and remaining work.

## Validation And Testing

- Run focused validation for the touched policy, fixture, harness, and Java parity tests with `sh mvnw -q -Dtest=... test`.
- Run `make validate-policy-format` in `sead_bugs_import` after the narrow checks pass.
- Review updated fixtures to confirm they remain valid policy-backed execution references rather than ad hoc scenario notes.
- Review the updated proposal and task plan together so the documented end-game matches the implementation target.

## Deliverables

| Deliverable | Description | Status | Link |
|---|---|---|---|
| Task plan document | Forward-looking remaining-work plan for implementation-ready policy fidelity | Done | `docs/proposals/BUGSCEP_POLICY_SCHEMA_MACHINE_READABLE_FIDELITY_TASK_PLAN.md` |
| Execution-readiness checklist | Shared criteria for when a policy is detailed enough to drive either implementation path | Done | `docs/proposals/BUGSCEP_POLICY_SCHEMA_MACHINE_READABLE_FIDELITY.md` |
| Policy gap inventory | Ranked list of remaining under-specified behaviors that block implementation | Done | `docs/proposals/BUGSCEP_POLICY_SCHEMA_MACHINE_READABLE_FIDELITY_GAP_INVENTORY.md` |
| Geochronology golden reference set | First named golden execution-reference family and the rules for using it as a shared contract | Done | `docs/proposals/BUGSCEP_POLICY_GOLDEN_REFERENCE_GEOCHRONOLOGY.md` |
| Site and contact persisted-action contracts | Execution-facing contract for append, keep, delete, replace, and prerequisite-stop behavior | Done | `docs/proposals/BUGSCEP_POLICY_PERSISTED_ACTION_CONTRACTS_SITE_CONTACTS.md` |
| Golden reference fixture set | Representative policy-plus-fixture cases suitable for implementation and regression work | In progress | `docs/proposals/BUGSCEP_POLICY_GOLDEN_REFERENCE_GEOCHRONOLOGY.md` |
| Taxa graph contract baseline | First non-geochronology graph family slice with explicit supporting action labels in executable fixtures | Done | `docs/proposals/BUGSCEP_POLICY_SCHEMA_MACHINE_READABLE_FIDELITY_GAP_INVENTORY.md` |
| Reconciliation action baseline | First 10 reconciliation-only slices with explicit persisted_action labels for insert and update write paths, plus broader fixture-backed no-write action labels for error and guard scenarios across ordered-reconciliation and adjacent species-text families | Done | `docs/proposals/BUGSCEP_POLICY_SCHEMA_MACHINE_READABLE_FIDELITY_GAP_INVENTORY.md` |
| Option mapping notes | Notes that map policy capabilities to the Python path and the Shape Shifter plus BugCEP reconciliation path | Done | `docs/proposals/BUGSCEP_POLICY_OPTION_MAPPING_NOTES.md` |
| Divergence evidence baseline | First concrete known-divergence areas recorded in policy and fixture form for the shared contract | Done | `docs/proposals/BUGSCEP_POLICY_OPTION_MAPPING_NOTES.md` |
| Proposal sync | Coverage and recommendation updates in the fidelity proposal if the end-game wording changes | Done | `docs/proposals/BUGSCEP_POLICY_SCHEMA_MACHINE_READABLE_FIDELITY.md` |

## Scope

**In scope**

- raising policy detail toward implementation-ready behavior descriptions
- clarifying what must be in policy versus what can remain adapter logic
- preparing representative fixtures and outputs as golden execution references
- documenting how the shared policy work feeds both downstream implementation options
- focused validation plus the existing `make validate-policy-format` target

**Out of scope**

- building the Python runtime in this phase
- implementing the Shape Shifter plus BugCEP-specific automatic reconciliation flow in this phase
- inventing a general workflow DSL beyond what the proposal already supports
- rewriting completed slice history into this task plan

## Risks And Mitigations

- **Risk:** policy work keeps growing test coverage without making the policies materially more implementable.  
  **Mitigation:** require each new slice to close a named implementation gap or improve the execution-readiness checklist.
- **Risk:** the two end-game options drift apart too early and force duplicate planning.  
  **Mitigation:** focus first on the shared contract both paths need and defer the choice until the first hard divergence is documented.
- **Risk:** some BugsCEP behaviors remain too implicit for either implementation path.  
  **Mitigation:** classify them explicitly as policy detail to add or adapter-only logic instead of leaving them hidden in Java behavior.

## Assumptions

- The current fidelity proposal remains the right umbrella document, but its recommendation may need wording updates to reflect an implementation-oriented end-game.
- The existing validation path remains `sh mvnw -q -Dtest=... test` for focused checks plus `make validate-policy-format` for the broad suite.