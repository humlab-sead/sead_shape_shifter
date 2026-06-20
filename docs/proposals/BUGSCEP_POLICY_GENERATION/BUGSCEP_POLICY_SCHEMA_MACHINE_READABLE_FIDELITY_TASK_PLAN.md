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
- [ ] Update `docs/proposals/BUGSCEP_POLICY_GENERATION/BUGSCEP_POLICY_SCHEMA_MACHINE_READABLE_FIDELITY.md` if the coverage statement, non-goals, or recommendation changes under the new end-game.
- [ ] Keep this task plan aligned with the current remaining work instead of repeating completed slice history.

**Completion Criteria**

Focused validation passes first, the broad validation target stays green, and the proposal plus task plan reflect the same implementation-oriented end-game.

## Gap Inventory

This section consolidates the remaining gaps between current policy YAML and implementation-ready contracts. Use it alongside the execution-readiness assessment in the fidelity proposal to prioritize the next slice.

### Priority Gaps

| # | Gap | Why it matters | Policies to close it | Status |
|---|-----|----------------|----------------------|--------|
| 1 | End-to-end identity and supporting-output flow | Both implementation paths need a complete contract for how parent rows, supporting rows, and related outputs share identity and reuse state | `datescalendar`, `datesperiod`, `datesradio`, `fossil`, `species`, `bibliography`, `country`, `rdbcode`, `mcrnames`, `mcrsummary`, `attributes`, `sitereferences`, `period`, `taxanotes`, `lab`, `site`, `rdbsystem`, `rdb`, `samplegroup`, `taxaseasonality` | **Done** — all Tier A policies (24 total) have full coverage; all Tier C policies converted to Tier A 2026-06-20 |
| 2 | Persisted side effects and output result semantics | Implementation needs to know not only which branch fired, but what row actions and side effects must happen | `datasetcontacts`, `sitelocations`, `siteotherproxies`, `sample` | Partial — explicit action labels and `row_changed` expectations added for list outputs and supporting outputs |
| 3 | Helper-derived decision rules hidden in Java behavior | Policies cannot serve as a build contract while important lookup or derivation behavior still depends on Java-only helpers | `lab`, `datesradio`, `datesperiod`, `species`, `datasetcontacts`, `sitelocations`, `siteotherproxies`, `country`, `rdbcode`, `mcrnames`, `mcrsummary`, `attributes`, `sitereferences`, `period`, `taxanotes`, `rdbsystem`, `rdb`, `samplegroup`, `taxaseasonality` | **Done** — 24 policies have structured resolvers including final Tier C conversions (`rdb`, `samplegroup`, `taxaseasonality`) 2026-06-20 |
| 4 | Postprocess and graph behavior as full execution contracts | Downstream implementation needs clearer expectations around retained rows, emitted rows, graph issues, and ordering-sensitive outputs | `datescalendar`, `datesperiod`, `datesradio`, `fossil`, `species` | Partial — Tier A policies have full coverage; `species` graph needs known-divergence documentation |
| 5 | Known divergences and intentional adapter boundaries | Both paths need explicit documentation of what the policy owns, what the adapter owns, and where Java behavior is preserved only for parity | `datescalendar`, `fossil`, `rdb`, `rdbcode`, `site`, `bibliography`, `country`, `mcrnames`, `mcrsummary`, `attributes`, `sitereferences`, `period`, `taxanotes`, `lab`, `rdbsystem`, `samplegroup`, `taxaseasonality` | **Done** — 24 policies have `known_divergences`; 11 policies lack this section (all Tier D) |

### Gap Closure Progress

Each gap tracks which criteria it helps close for the execution-readiness checklist (C1–C6).

**Gap 1: Identity and supporting-output flow**

- Closes: C4 (policy-managed vs adapter-only), C6 (readable without Java helpers)
- Done: Tier A policies (`datescalendar`, `datesperiod`, `datesradio`, `fossil`, `species`, `datasetcontacts`, `sample`, `sitelocations`, `siteotherproxies`, `bibliography`, `country`, `rdbcode`, `mcrnames`, `mcrsummary`, `attributes`, `sitereferences`, `period`, `taxanotes`) have complete identity flow with explicit `supporting_action`, `persisted_action`, and `row_changed`. The fossil policy uses `phase: before_parent` on its dataset and analysis_entity related outputs, and references child identity through `related.<name>.<field>` expressions instead of helper calls (Feature 1 conversion, 2026-06-20). The species policy was converted 2026-06-20: all 4 related outputs use `phase: before_parent`, `taxa_genus.family_id` uses `related.taxa_family.family_id`, `taxa_species` uses `related.taxa_genus.genus_id` and `related.taxa_author.author_id`, and parent `taxon_id` uses `related.taxa_species.taxon_id`. The `resolve_bugs_taxonomic_order_system_id` helper was converted to a structured resolver, and `known_divergences` were added for the no-data species shortcut and cascade dependency null propagation. The datasetcontacts policy was converted 2026-06-20: the `resolve_dataset_id_from_countsheet_code` helper was converted to a structured resolver with trace lookup → database query fallback, and `known_divergences` were added for dataset reuse from fossil import and contact string parsing adapter. The sample policy was converted 2026-06-20: three structured resolvers (sample group from countsheet trace, default alternative reference type, default sample type). The sitelocations and siteotherproxies policies were converted 2026-06-20: `resolve_site_id` helper converted to structured resolver with trace lookup and deleted-site guard. Nine Tier C policies were converted in two batches on 2026-06-20: six simple (0-1 helpers) — `bibliography` (no helpers, known_divergences only), `country` (country type ID resolver), `rdbcode` (RDB system ID resolver), `mcrnames` (taxon ID resolver), `mcrsummary` (taxon ID resolver), `attributes` (taxon ID resolver) — and three 2-helper policies — `sitereferences` (site ID + biblio ID), `period` (relative age type ID + location ID), `taxanotes` (taxon ID + biblio ID).
- Remaining: Tier D policies still use helper calls for identity resolution; need conversion to structured resolvers or explicit adapter-only documentation before promotion to Tier C

**Gap 2: Persisted side effects and output result semantics**

- Closes: C2 (concrete result shapes), C3 (explicit action labels)
- Done: `sitelocations`, `siteotherproxies`, `datasetcontacts`, `sample`, `species`, `fossil` have explicit `persisted_action`, `supporting_action`, and `row_changed` labels
- Remaining: Tier D policies have basic reconciliation fixtures but lack explicit action labels on write paths; need `persisted_action` labels for insert, update, keep, and error paths before promotion to Tier C

**Gap 3: Helper-derived decision rules**

- Closes: C4 (policy-managed vs adapter-only), C6 (readable without Java helpers)
- Done: `lab` (country resolver), `datesperiod` (method/uncertainty resolver), `datesradio` (method/uncertainty resolver), `species` (taxonomic-order-system resolver), `datasetcontacts` (dataset ID from countsheet code resolver), `sample` (sample group from countsheet trace resolver, default alternative reference type resolver, default sample type resolver), `sitelocations` (site ID from trace resolver with deleted-site guard), `siteotherproxies` (site ID from trace resolver with deleted-site guard), `country` (country type ID resolver), `rdbcode` (RDB system ID resolver), `mcrnames` (taxon ID resolver), `mcrsummary` (taxon ID resolver), `attributes` (taxon ID resolver) have structured resolvers replacing helper calls
- Remaining: Tier D policies still use helper calls for lookups (e.g., `ecocodegroup` for system ID resolution); need conversion to structured resolvers before promotion to Tier C

**Gap 4: Postprocess and graph behavior**

- Closes: C2 (concrete result shapes), C5 (known divergences)
- Done: `datescalendar` has postprocess merge with conflict handling; `datesperiod`, `datesradio`, `fossil`, `species` have related-output graph fixtures with explicit `row_changed`; `species` has `known_divergences` for no-data species shortcut and cascade dependency null propagation
- Remaining: Tier D policies have no postprocess or graph behavior to exercise

**Gap 5: Known divergences and adapter boundaries**

- Closes: C5 (known divergences recorded)
- Done: 24 policies (`datescalendar`, `datesperiod`, `datesradio`, `sitelocations`, `siteotherproxies`, `species`, `datasetcontacts`, `sample`, `bibliography`, `country`, `rdbcode`, `mcrnames`, `mcrsummary`, `attributes`, `sitereferences`, `period`, `taxanotes`, `lab`, `site`, `rdbsystem`, `rdb`, `samplegroup`, `taxaseasonality`) have `known_divergences` sections
- Remaining: 11 policies lack `known_divergences` sections (all Tier D); need documentation of surprising Java behavior or explicit statement that no divergences exist

### Golden Reference Families

The four families below cover the widest set of shared policy needs and should be the first to reach full execution-readiness.

| Family | Policies | Coverage | Current Tier |
|--------|----------|----------|--------------|
| Geochronology | `datescalendar`, `datesperiod`, `datesradio` | Resolvers, postprocess, supporting outputs, related-output graphs, emitted issues, retained rows, known divergences | A (all execution-ready) |
| Taxa Graph | `species`, `speciesassociation`, `speciesbiology`, `specieskeys`, `speciessynonyms` | Related-output graphs, optional supporting outputs, repository reuse, multi-node output structure, known divergences, structured resolvers | A (species), D (rest) |
| Site And Contact | `site`, `sitereferences`, `datasetcontacts`, `sitelocations`, `siteotherproxies`, `sample` | Ordered reconciliation, persisted list-result side effects, explicit action labels, known divergences, structured resolvers, child supporting outputs | A (all execution-ready) |
| Simple Leaf Importers | `bibliography`, `country`, `rdbcode`, `mcrnames`, `mcrsummary`, `attributes` | Ordered reconciliation, structured resolvers for trace lookups, known divergences, reconciliation fixtures | A (all execution-ready, converted 2026-06-20) |
| Two-Helper Importers | `sitereferences`, `period`, `taxanotes` | Two structured resolvers per policy (trace lookups + database queries), known divergences for trace-based resolution, reconciliation fixtures | A (all execution-ready, converted 2026-06-20) |
| Fossil Analysis-Entity | `fossil` | Configuration forks, supporting-output reuse, graph issues, analysis-entity reuse failure paths | A (execution-ready) |

### Adapter-Only Boundaries

Treat the following as adapter-only unless a concrete implementation slice proves they need to move into policy:

- persistence orchestration details that do not change reconciliation or emitted outcomes
- runtime-specific cache implementation details
- batching mechanics that preserve the same declared postprocess and output behavior
- Shape Shifter stage wiring that preserves the same declared decisions and outputs
- Python runtime plumbing that evaluates the same declared decisions and outputs

If any of these mechanics changes matching, row identity, emitted issues, persisted values, retained rows, or output graph structure, it should move back into policy scope.

### Next Recommended Slices

Based on the gap inventory and execution-readiness tiers:

1. **Promote Tier D to Tier C** — add explicit `persisted_action` labels to reconciliation fixtures for write and error paths for all 11 Tier D policies (`ecocodegroup`, `ecocode_bugs`, `ecocode_koch`, `ecocodedefinition_bugs`, `ecocodedefinition_koch`, `birmbeetledata`, `speciesassociation`, `speciesbiology`, `specieskeys`, `speciessynonyms`, `speciesdistribution`)
2. **Convert Tier D helpers to structured resolvers** — replace helper calls in Tier D policies with structured resolvers (trace lookups, database queries)
3. **Add known_divergences to Tier D** — document Java behavior divergences or explicit statement that no divergences exist
4. **Extend Feature 1** — convert one geochronology policy (`datesperiod` or `datesradio`) to use `phase: before_parent` for a supporting output, further proving the expression language resolves `related.<name>.<field>` correctly

## Progress Tracker

| Area | Status | Notes |
|---|---|---|
| Define execution-ready policy criteria | Done | Checklist and adapter-boundary rules are now captured in the companion fidelity proposal. |
| Close policy semantics gaps | In progress | Execution-facing action labels and `row_changed` expectations added across reconciliation, supporting-output, related-output graph, and list-output families. Detailed batch history: see [WRAP_UP_BUGCEP_POLICY.md](WRAP_UP_BUGCEP_POLICY.md#fidelity-work-changelog). |
| Prepare implementation-oriented fixtures and outputs | In progress | Geochronology, taxa graph, site/contact, and fossil families carry explicit action labels and `row_changed` expectations. Detailed batch history: see [WRAP_UP_BUGCEP_POLICY.md](WRAP_UP_BUGCEP_POLICY.md#fidelity-work-changelog). |
| Add option-specific mapping notes and decision checkpoint | Done | The option mapping notes now keep both paths open and define the first divergence checkpoint. |
| Validate and sync companion docs | In progress | Focused validation is green for the latest slices; `make validate-policy-format` passes. Remaining work: keep the companion proposal set aligned as more families are upgraded. |

## Definition Of Done

- [ ] A shared execution-readiness checklist exists for BugsCEP policies.
- [ ] The next phase improves policy detail toward implementation readiness, not only broader test-harness execution.
- [ ] Representative policies and fixtures can act as a concrete build contract for either downstream option up to the documented divergence point.
- [ ] Policy-managed behavior and adapter-only behavior are explicitly separated.
- [x] Focused validation passes for the touched areas.
- [x] `make validate-policy-format` passes after the phase lands.
- [x] `docs/proposals/BUGSCEP_POLICY_GENERATION/BUGSCEP_POLICY_SCHEMA_MACHINE_READABLE_FIDELITY.md` and this task plan both describe the same end-game and remaining work.

## Validation And Testing

- Run focused validation for the touched policy, fixture, harness, and Java parity tests with `sh mvnw -q -Dtest=... test`.
- Run `make validate-policy-format` in `sead_bugs_import` after the narrow checks pass.
- Review updated fixtures to confirm they remain valid policy-backed execution references rather than ad hoc scenario notes.
- Review the updated proposal and task plan together so the documented end-game matches the implementation target.

## Deliverables

| Deliverable | Description | Status | Link |
|---|---|---|---|
| Task plan document | Forward-looking remaining-work plan for implementation-ready policy fidelity | Done | `docs/proposals/BUGSCEP_POLICY_GENERATION/BUGSCEP_POLICY_SCHEMA_MACHINE_READABLE_FIDELITY_TASK_PLAN.md` |
| Execution-readiness checklist | Shared criteria for when a policy is detailed enough to drive either implementation path | Done | `docs/proposals/BUGSCEP_POLICY_GENERATION/BUGSCEP_POLICY_SCHEMA_MACHINE_READABLE_FIDELITY.md` |
| Policy gap inventory | Ranked list of remaining under-specified behaviors that block implementation | Consolidated | Merged into [Gap Inventory section](#gap-inventory) in this task plan (see also `BUGSCEP_POLICY_SCHEMA_MACHINE_READABLE_FIDELITY_GAP_INVENTORY.md` for historical reference) |
| Geochronology golden reference set | First named golden execution-reference family and the rules for using it as a shared contract | Done | `docs/proposals/BUGSCEP_POLICY_GENERATION/BUGSCEP_POLICY_GOLDEN_REFERENCE_GEOCHRONOLOGY.md` |
| Site and contact persisted-action contracts | Execution-facing contract for append, keep, delete, replace, prerequisite-stop behavior, and explicit list-output change-state expectations | Done | `docs/proposals/BUGSCEP_POLICY_GENERATION/BUGSCEP_POLICY_PERSISTED_ACTION_CONTRACTS_SITE_CONTACTS.md` |
| Golden reference fixture set | Representative policy-plus-fixture cases suitable for implementation and regression work | In progress | `docs/proposals/BUGSCEP_POLICY_GENERATION/BUGSCEP_POLICY_GOLDEN_REFERENCE_GEOCHRONOLOGY.md` |
| Taxa graph contract baseline | First non-geochronology graph family slice with explicit supporting action labels in executable fixtures | Done | `docs/proposals/BUGSCEP_POLICY_GENERATION/BUGSCEP_POLICY_SCHEMA_MACHINE_READABLE_FIDELITY_GAP_INVENTORY.md` |
| Reconciliation action baseline | First 10 reconciliation-only slices with explicit persisted_action labels for insert and update write paths, plus broader fixture-backed no-write action labels for error, guard, and keep-existing scenarios across ordered-reconciliation and adjacent species-text families | Done | `docs/proposals/BUGSCEP_POLICY_GENERATION/BUGSCEP_POLICY_SCHEMA_MACHINE_READABLE_FIDELITY_GAP_INVENTORY.md` |
| Option mapping notes | Notes that map policy capabilities to the Python path and the Shape Shifter plus BugCEP reconciliation path | Done | `docs/proposals/BUGSCEP_POLICY_GENERATION/BUGSCEP_POLICY_OPTION_MAPPING_NOTES.md` |
| Divergence evidence baseline | First concrete known-divergence areas recorded in policy and fixture form for the shared contract | Done | `docs/proposals/BUGSCEP_POLICY_GENERATION/BUGSCEP_POLICY_OPTION_MAPPING_NOTES.md` |
| Proposal sync | Coverage and recommendation updates in the fidelity proposal if the end-game wording changes | Done | `docs/proposals/BUGSCEP_POLICY_GENERATION/BUGSCEP_POLICY_SCHEMA_MACHINE_READABLE_FIDELITY.md` |

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