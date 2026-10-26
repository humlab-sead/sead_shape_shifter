# Shape Shifter Project AI Advisor Phase Plan

See [SHAPESHIFTER_PROJECT_AI_ADVISOR.md](./SHAPESHIFTER_PROJECT_AI_ADVISOR.md) for the full proposal: problem statement, stakeholders, product principles, MVP use cases, architecture, knowledge pack specification, evaluation plan, risks, and glossary.

This plan defines the delivery sequence. It keeps the highest-risk work early — curated knowledge, deterministic context assembly, citation control, redaction, and evaluation — so later user-facing steps do not arrive before the grounding they depend on. Investigation follows the read-only explanation workflow and its evaluation harness, and every investigation capability is delivered under a read-only constraint before any write behavior is considered.

## Summary

The plan delivers the advisor in nine phases. Phases 0–2 establish the grounding: a curated knowledge pack, a read-only backend advisor, and the evaluation harness that gates later work. Phase 3 adds investigation, so the advisor can read the framework source behind a report and probe the real pipeline against the active project. Phase 4 exposes the advisor in the project UI. Phase 5 adds sandboxed experiment execution, the only tier that runs generated code. Phases 6–8 extend the advisor from explanation to draft proposals, source-data assistance, and finally approval-based application.

Investigation is the significant change from the initial sequencing. It is ordered after the evaluation harness, because the false-positive, scope, and negative-result scenarios are what make investigation trustworthy, and before the frontend, so the UI renders the evidence model once rather than being retrofitted. Sandboxed execution is ordered after the frontend, because it depends on an unresolved isolation decision and should not gate the user-facing surface, and because the evidence model is the same for every tier.

## Problem

A validation message is one check's observation, not a verdict. Explaining it correctly requires confirming that the check is correct and that the reported scope is complete. Without source access and pipeline probing, the advisor can only restate existing output, including false positives and understated severities.

## Scope

In scope: the nine phases below, from the curated knowledge pack through approval-based apply.

Out of scope: general-purpose code execution, IDE-style repository editing, and any change that would make Shape Shifter the identity authority. Investigation stays bounded to answering questions about the active project, under a read-only constraint.

## Current Position

Shape Shifter already has project YAML loading, validation, dependency analysis, preview services, reconciliation workflows, project-scoped session handling, target-model guidance, and a bundled SEAD superset target model. These are available as context sources for the advisor and do not need to be built from scratch.

Three capabilities the advisor needs do not exist yet: framework source retrieval, read-only pipeline probing, and a sandbox for generated experiments. Phase 3 delivers the first two. Phase 5 delivers the third.

## Phase Plan

### Phase 0: Knowledge Foundation

**Goal**

Create the grounded rule set the advisor will rely on before any advisor API is exposed.

**Focus**

- define the knowledge-pack structure, including rule IDs, status, confidence, caveats, and source references
- curate stable Shape Shifter rules, SEAD/SIMS concepts, and SEAD Authoritative Service concepts
- curate target-model guidance and conformance rules from the target-model docs and active target-model specifications
- record unresolved areas explicitly so the advisor can distinguish stable guidance from uncertain guidance

**Depends On**

- no prior phase; this is the entry point

**Outputs**

- a versioned knowledge pack whose rules are citable as `knowledge.pack.*`
- documented in-scope and deferred topics for the MVP

**Acceptance Criteria**

- `PH0-AC-1` (proposal Success Criteria 2) a versioned knowledge pack exists with rule structure, sources, and review metadata
- `PH0-AC-2` (proposal Success Criteria 6) the knowledge pack includes target-model and conformance rules with explicit source references
- `PH0-AC-3` (proposal Success Criteria 4) the knowledge pack distinguishes stable rules from unresolved or provisional rules
- `PH0-AC-4` the phase documents which topics are in scope for the MVP and which remain deferred

**Validation Milestones**

- `VM-1` rule review confirms every rule carries an ID, source, status, and confidence, covering `PH0-AC-1` through `PH0-AC-4`

**Task-Plan Handoff**

- the rule schema in the proposal's [Knowledge Pack Specification](./SHAPESHIFTER_PROJECT_AI_ADVISOR.md#knowledge-pack-specification) is a fixed decision; the pack file format and runtime loading path remain open

**Readiness**

Ready for a task plan.

### Phase 1: Read-Only Backend Advisor API

**Goal**

Deliver a backend advisor that can explain current project issues using grounded project context and curated rules.

**Focus**

- add provider abstraction for local and hosted providers
- build deterministic context assembly from project state, validation, conformance results, dependency summaries, target-model context,
  and selected knowledge-pack rules
- implement redaction, citation ID generation, response parsing, and citation validation
- support the MVP read-only use cases defined in the proposal

**Depends On**

- Phase 0 for the curated rules the context assembler selects from

**Outputs**

- an advisor endpoint that returns a parsed response with allow-listed citations
- a redacted context packet derived from project state and knowledge-pack rules

**Acceptance Criteria**

- `PH1-AC-1` (proposal Success Criteria 1) the backend can answer MVP read-only advisor questions without editing YAML
- `PH1-AC-2` (proposal Success Criteria 8) provider calls use redacted, whitelisted context rather than the full project object
- `PH1-AC-3` (proposal Success Criteria 7) the backend rejects or flags citation IDs that were not provided in the assembled context
- `PH1-AC-4` target-model context is included when the project references a target model
- `PH1-AC-5` (Product Principle 3) validation results, parsing, and context assembly stay in deterministic code

**Validation Milestones**

- `VM-2` an end-to-end request against a real project returns a parsed response with only allow-listed citation IDs, covering `PH1-AC-1` through `PH1-AC-5`

**Task-Plan Handoff**

- the response shape and citation rules in the proposal are fixed decisions; the prompt template, API models, and error behavior remain open and are listed in the implementation readiness assessment

**Readiness**

Ready for a task plan after Phase 0.

### Phase 2: Advisor Evaluation Harness

**Goal**

Prove that the backend advisor is reliable enough to support broader use.

**Focus**

- build the scenario-based evaluation harness described in the proposal
- cover validation explanation, dependency explanation, identity boundaries, hallucination control, and redaction
- use evaluation results to close grounding gaps before frontend rollout

**Depends On**

- Phase 1 for the backend the harness exercises

**Outputs**

- a scenario suite and a recorded pass or fail result for the rollout gate

**Acceptance Criteria**

- `PH2-AC-1` scenario-based evaluation exists for the defined MVP and boundary cases
- `PH2-AC-2` (proposal Success Criteria 3) evaluation covers refusal behavior, citation behavior, and SEAD/SIMS responsibility boundaries
- `PH2-AC-3` the read-only backend passes the evaluation gate required before frontend rollout

**Validation Milestones**

- `VM-3` the scenario suite runs against the Phase 1 backend and passes the rollout gate, covering `PH2-AC-1` through `PH2-AC-3`

**Task-Plan Handoff**

- the proposal's [Evaluation Plan](./SHAPESHIFTER_PROJECT_AI_ADVISOR.md#evaluation-plan) fixes the scenario format and test categories; the harness implementation remains open

**Readiness**

Ready for a task plan after Phase 1.

### Phase 3: Investigation: Source Retrieval And Pipeline Probing

**Goal**

Let the advisor read the framework source behind a report and probe the real pipeline against the active project, read-only.

**Focus**

- add source search and read, so the check, transform, or loader behind a message can be located and cited
- add registry inspection, so the advisor can determine which checks, loaders, and filters run for an entity
- add read-only project load and normalize, and stage inspection for columns, dtypes, row counts, null counts, distinct values, and key uniqueness
- add differential runs and cross-entity scans
- add reference comparison against an authoritative source such as a lookup table or the target model
- introduce the evidence artifact model, with `source.code.*` and `evidence.artifact.*` citation categories
- extend the evaluation harness with false-positive, scope, negative-result, and pre-existing-failure scenarios

**Depends On**

- Phase 1 for the citation and context model that investigation citations extend
- Phase 2 for the harness that gates the new scenario categories

**Outputs**

- the tier 1 and tier 2 investigation tools defined in the proposal
- evidence artifacts recorded, bounded by an explicit `limitations` field
- evaluation scenarios covering false-positive detection, scope discovery, and ruled-out causes

**Acceptance Criteria**

- `PH3-AC-1` the advisor can locate the source that produced a message and cite the file and line
- `PH3-AC-2` the advisor can probe the pipeline read-only and report column, dtype, row, and null state for an entity
- `PH3-AC-3` the advisor can run a differential run and a cross-entity scan
- `PH3-AC-4` every investigation finding carries an evidence artifact that records its inputs and limitations
- `PH3-AC-5` (proposal Success Criteria 8) no project file writes, no database writes, and no mutation of backend caches or session state
- `PH3-AC-6` a ruled-out cause is reported with the same standing as a confirmed defect

**Validation Milestones**

- `VM-4` false-positive and scope scenarios pass against a real project, covering `PH3-AC-1` through `PH3-AC-6`; this milestone gates Phase 4

**Task-Plan Handoff**

- the tier definitions, investigation tool list, and evidence artifact fields in the proposal are fixed decisions; the source retrieval mechanism and artifact persistence location remain open

**Readiness**

Ready for a task plan after Phase 2. Tiers 1 and 2 add no new execution surface, so no sandbox decision is needed.

### Phase 4: Frontend Advisor Surface

**Goal**

Expose the grounded advisor inside the project UI once the backend workflow is stable.

**Focus**

- add a project-scoped advisor tab or drawer
- add frontend session state and response display using existing project/session patterns
- render citations so users can inspect the project data, validation messages, code locations, and recorded experiments behind an answer
- render evidence artifacts, including each artifact's recorded limitations
- show loading, error, and inconclusive-investigation states

**Depends On**

- Phase 3, so the evidence and source citation model is rendered once rather than retrofitted

**Outputs**

- a project-scoped advisor surface with evidence and citation display

**Acceptance Criteria**

- `PH4-AC-1` the advisor is available from the project detail UI
- `PH4-AC-2` users can ask the MVP question types and review answers in the frontend
- `PH4-AC-3` citations are visible and navigate to the relevant entity, validation message, code location, or knowledge-pack rule
- `PH4-AC-4` evidence artifacts are visible, including their limitations
- `PH4-AC-5` the frontend does not imply that the advisor can edit project YAML in this phase

**Validation Milestones**

- `VM-5` a user can complete the MVP question types in the UI and follow each citation to its source, covering `PH4-AC-1` through `PH4-AC-5`

**Task-Plan Handoff**

- the MVP use cases are fixed; the surface form, streaming decision, citation navigation target, and loading and error states remain open and are listed in the implementation readiness assessment

**Readiness**

Requires the frontend design decisions named in the implementation readiness assessment.

### Phase 5: Sandboxed Experiment Execution

**Goal**

Enable the tier 3 experiments that run generated code, under isolation and read-only bounds.

**Focus**

- add a sandbox with no network access and bounded time and memory
- restrict execution to the fixed investigation tool set, each with a defined input and output shape
- keep execution read-only against the project, the database, and backend caches and session state
- capture and retain artifacts so every experiment can be audited and reproduced
- extend the evaluation harness with sandbox-isolation scenarios

**Depends On**

- Phase 3 for the tool set and the evidence artifact model
- a decision on the isolation mechanism, which is unresolved

**Outputs**

- a sandboxed runner for tier 3 experiments
- isolation scenarios that gate the tier

**Acceptance Criteria**

- `PH5-AC-1` experiments run with no network access and bounded time and memory
- `PH5-AC-2` (proposal Success Criteria 8) an experiment cannot write to project files, the database, or backend caches and session state
- `PH5-AC-3` execution is possible only through the fixed tool set, not through arbitrary code paths
- `PH5-AC-4` every run records an artifact sufficient to reproduce it
- `PH5-AC-5` sandbox-isolation scenarios pass before tier 3 execution is enabled

**Validation Milestones**

- `VM-6` isolation scenarios confirm no writes, no network access, and enforced resource bounds, covering `PH5-AC-1` through `PH5-AC-5`

**Task-Plan Handoff**

- the constraints in the proposal's Investigation Capability section are fixed decisions; the isolation mechanism, resource limits, and artifact retention policy remain open

**Readiness**

Requires a named decision on the isolation mechanism.

### Phase 6: Structured Proposal Generation

**Goal**

Expand the advisor from explanation to constrained, reviewable change suggestions.

**Focus**

- add a proposal mode that suggests YAML changes without applying them
- structure proposal output so it can be checked against existing schemas and validators
- expand evaluation to cover proposal quality, proposal validity, and citation completeness

**Depends On**

- Phase 3, so proposals rest on verified problems rather than restated reports

**Outputs**

- a proposal response shape that carries supporting citations and passes the existing validators

**Acceptance Criteria**

- `PH6-AC-1` the advisor can return structured YAML change proposals with supporting citations
- `PH6-AC-2` (proposal Success Criteria 8) proposal output is validated before it is shown as a valid change suggestion
- `PH6-AC-3` proposal-mode evaluation covers patch validity and minimality
- `PH6-AC-4` proposal mode remains review-only in this phase

**Validation Milestones**

- `VM-7` every proposed patch passes the existing schemas and validators before display, covering `PH6-AC-1` through `PH6-AC-4`

**Task-Plan Handoff**

- the review-only constraint is a fixed decision; the proposal response shape remains open

**Readiness**

Ready for a task plan after Phase 3.

### Phase 7: Data-To-Configuration Assistance

**Goal**

Add source-data exploration that can help draft project configuration from observed input files.

**Focus**

- inspect source files, columns, types, and sample values
- generate candidate entities, relationships, and draft `shapeshifter.yml` content
- use validation feedback to refine the generated configuration suggestions

**Depends On**

- Phase 6 for the proposal and validation loop this phase refines

**Outputs**

- source exploration and draft generation

**Acceptance Criteria**

- `PH7-AC-1` the advisor can inspect source-data structure and produce draft configuration suggestions
- `PH7-AC-2` (proposal Success Criteria 8) generated suggestions are presented as drafts, not as applied project changes
- `PH7-AC-3` validation feedback is part of the refinement loop for generated configuration

**Validation Milestones**

- `VM-8` a draft generated from a real source file passes the existing validators, covering `PH7-AC-1` through `PH7-AC-3`

**Task-Plan Handoff**

- the draft-only constraint is a fixed decision; supported source formats remain open

**Readiness**

Ready for a task plan after Phase 6.

### Phase 8: Approval-Based Apply

**Goal**

Allow advisor-generated changes to be applied only after proposal mode is stable and user approval is explicit.

**Focus**

- convert validated proposals into concrete YAML changes
- integrate preview, diff, rollback, and conflict handling
- keep approval and validation gates explicit at the point of apply

**Depends On**

- Phase 6 for validated proposals
- an explicit approval gate, which this phase exists to define

**Outputs**

- an apply path with diff, validation, and recovery behavior

**Acceptance Criteria**

- `PH8-AC-1` (proposal Success Criteria 5) no advisor change is applied without explicit approval
- `PH8-AC-2` applied changes show a reviewable diff and validation result
- `PH8-AC-3` rollback or equivalent recovery behavior is defined for applied changes
- `PH8-AC-4` unsupported or invalid changes stay in proposal-only form instead of being applied

**Validation Milestones**

- `VM-9` an applied change can be reviewed, validated, and reverted, covering `PH8-AC-1` through `PH8-AC-4`

**Task-Plan Handoff**

- the approval requirement is a fixed decision; the recovery mechanism remains open

**Readiness**

Requires a named decision on the recovery and rollback mechanism.

## Cross-Phase Rules

The proposal's [Product Principles](./SHAPESHIFTER_PROJECT_AI_ADVISOR.md#product-principles) (grounded, not generative; explicit uncertainty; deterministic code owns factual claims; reported state is verified before it is explained) apply throughout. The following rules are specific to delivery sequencing:

- do not expose write behavior before read-only grounding and evaluation are proven
- expand capability one step at a time: explain, then investigate, then propose, then apply
- keep every investigation capability read-only; no phase may add a write path to project files, the database, or backend caches and session state
- do not enable a tier of investigation until its evaluation gate passes; tier 3 stays disabled until the sandbox-isolation scenarios pass
- do not present a finding as project-wide until a cross-entity scan supports it, and carry each artifact's `limitations` through to the answer the user sees
- do not let an unresolved decision in one phase block a phase that does not depend on it

## Validation Strategy

The proposal's [Evaluation Plan](./SHAPESHIFTER_PROJECT_AI_ADVISOR.md#evaluation-plan) defines the scenario-based evaluation harness, test categories, and evaluation gates. This section adds phase-sequencing rules for validation:

- validate redaction, citation allow-list behavior, and SEAD/SIMS responsibility boundaries before frontend rollout (Phase 4)
- validate false-positive detection, scope discovery, and negative-result reporting before frontend rollout (Phase 4), because those determine whether an answer can be trusted
- validate sandbox isolation, including no writes, no network access, and enforced resource bounds, before tier 3 execution is enabled (Phase 5)
- validate structured proposals against existing schemas and validators before proposal mode is enabled (Phase 6)
- keep approval-mode validation stricter than proposal-mode validation, because it changes project state
- extend the harness in each phase so later phases inherit the earlier scenarios as regression coverage, and use grouped regression coverage when promoting behavior from read-only explanation to proposal generation and then to apply

## Final Recommendation

Start with Phase 0 and Phase 1 in parallel, since neither depends on an open decision. Defer Phase 5 and Phase 8 to task planning until their named decisions are settled, and treat the frontend decisions in Phase 4 as the next item to close so the user-facing surface is not the critical path.
