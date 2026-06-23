# Shape Shifter Project AI Advisor Phase Plan

## Summary

This plan defines the delivery sequence for the Shape Shifter Project AI Advisor proposed in
`SHAPESHIFTER_PROJECT_AI_ADVISOR.md`.

The goal is to move from a proposal-backed concept to a grounded project advisor that can explain current project issues, then suggest
changes, and only later support approval-based YAML updates. The phases below keep the highest-risk work early: curated SEAD knowledge,
deterministic context assembly, citation control, redaction, and evaluation.

## Problem

The proposed advisor depends on several pieces that do not exist yet as a validated feature:

- curated Shape Shifter and SEAD knowledge that can be versioned and cited
- deterministic context assembly from project state, validation, and dependency data
- a backend advisor workflow that separates application logic from model behavior
- a frontend advisor surface for project-scoped use
- proposal and apply workflows that remain constrained by validation and approval

Without an explicit phase sequence, later user-facing steps could arrive before the grounding, redaction, citation, and evaluation
work they depend on.

## Scope

This plan covers the implementation sequence for the Shape Shifter Project AI Advisor from knowledge-pack preparation through
approval-based YAML changes.

It includes backend, frontend, proposal-mode, and approval-mode phase boundaries. It does not include staffing, dates, release
scheduling, or a full implementation spec for each subsystem.

## Current Position

- the advisor exists as a proposal, not as an implemented feature
- Shape Shifter already has project YAML loading, validation, dependency analysis, preview services, reconciliation workflows, and
  project-scoped session handling
- target-model guidance, schema reference material, and a bundled SEAD superset target model already exist as conformance sources
- the proposal already defines narrow V1 use cases, explicit non-goals, architecture direction, citation rules, and evaluation goals
- the proposal also identifies a knowledge pack, deterministic context assembly, and redaction as core prerequisites
- the proposal previously held a phased delivery section that is now moved into this separate plan

## Phase Plan

### Phase 0: Knowledge Foundation

**Goal**

Create the grounded rule set the advisor will rely on before any advisor API is exposed.

**Focus**

- define the knowledge-pack structure, including rule IDs, status, confidence, caveats, and source references
- curate stable Shape Shifter rules, SEAD/SIMS concepts, and SEAD Authoritative Service concepts
- curate target-model guidance and conformance rules from the target-model docs and active target-model specifications
- record unresolved areas explicitly so the advisor can distinguish stable guidance from uncertain guidance

**Acceptance Criteria**

- a versioned knowledge pack exists with rule structure, sources, and review metadata
- the knowledge pack includes target-model and conformance rules with explicit source references
- the knowledge pack distinguishes stable rules from unresolved or provisional rules
- the phase documents which topics are in scope for V1 and which remain deferred

### Phase 1: Read-Only Backend Advisor API

**Goal**

Deliver a backend advisor that can explain current project issues using grounded project context and curated rules.

**Focus**

- add provider abstraction for local and hosted providers
- build deterministic context assembly from project state, validation, conformance results, dependency summaries, target-model context,
  and selected knowledge-pack rules
- implement redaction, citation ID generation, response parsing, and citation validation
- support the V1 read-only use cases defined in the proposal

**Acceptance Criteria**

- the backend can answer V1 read-only advisor questions without editing YAML
- provider calls use redacted, whitelisted context rather than the full project object
- the backend rejects or flags citation IDs that were not provided in the assembled context
- target-model context is included when the project references a target model
- the backend behavior keeps validation results, parsing, and context assembly in deterministic code

### Phase 2: Advisor Evaluation Harness

**Goal**

Prove that the backend advisor is reliable enough to support broader use.

**Focus**

- build the scenario-based evaluation harness described in the proposal
- cover validation explanation, dependency explanation, identity boundaries, hallucination control, and redaction
- use evaluation results to close grounding gaps before frontend rollout

**Acceptance Criteria**

- scenario-based evaluation exists for the defined V1 and boundary cases
- evaluation covers refusal behavior, citation behavior, and SEAD/SIMS responsibility boundaries
- the read-only backend passes the evaluation gate required before frontend rollout

### Phase 3: Frontend Advisor Surface

**Goal**

Expose the grounded advisor inside the project UI once the backend workflow is stable.

**Focus**

- add a project-scoped advisor tab or drawer
- add frontend session state and response display using existing project/session patterns
- render citations so users can inspect the project data, validation messages, or rules behind an answer

**Acceptance Criteria**

- the advisor is available from the project detail UI
- users can ask the V1 question types and review answers in the frontend
- citations are visible and link to the relevant project or rule context
- the frontend does not imply that the advisor can edit project YAML in this phase

### Phase 4: Structured Proposal Generation

**Goal**

Expand the advisor from explanation to constrained, reviewable change suggestions.

**Focus**

- add a proposal mode that suggests YAML changes without applying them
- structure proposal output so it can be checked against existing schemas and validators
- expand evaluation to cover proposal quality, proposal validity, and citation completeness

**Acceptance Criteria**

- the advisor can return structured YAML change proposals with supporting citations
- proposal output is validated before it is shown as a valid change suggestion
- proposal-mode evaluation covers patch validity and minimality
- proposal mode remains review-only in this phase

### Phase 5: Data-To-Configuration Assistance

**Goal**

Add source-data exploration that can help draft project configuration from observed input files.

**Focus**

- inspect source files, columns, types, and sample values
- generate candidate entities, relationships, and draft `shapeshifter.yml` content
- use validation feedback to refine the generated configuration suggestions

**Acceptance Criteria**

- the advisor can inspect source-data structure and produce draft configuration suggestions
- generated suggestions are presented as drafts, not as applied project changes
- validation feedback is part of the refinement loop for generated configuration

### Phase 6: Approval-Based Apply

**Goal**

Allow advisor-generated changes to be applied only after proposal mode is stable and user approval is explicit.

**Focus**

- convert validated proposals into concrete YAML changes
- integrate preview, diff, rollback, and conflict handling
- keep approval and validation gates explicit at the point of apply

**Acceptance Criteria**

- no advisor change is applied without explicit approval
- applied changes show a reviewable diff and validation result
- rollback or equivalent recovery behavior is defined for applied changes
- unsupported or invalid changes stay in proposal-only form instead of being applied

## Cross-Phase Rules

- keep the advisor grounded in project context and curated rules rather than free-form model output
- keep validation, parsing, redaction, citation generation, and context assembly in deterministic code
- do not expose write behavior before read-only grounding and evaluation are proven
- treat unresolved SEAD modeling questions as explicit caveats rather than hidden assumptions
- keep local-only operation available where hosted-provider data transfer is not acceptable
- expand capability one step at a time: explain, then propose, then apply

## Validation Strategy

- use scenario-based evaluation as the main gate for advisor behavior and regression coverage
- validate redaction, citation allow-list behavior, and SEAD/SIMS responsibility boundaries before frontend rollout
- validate structured proposals against existing schemas and validators before proposal mode is considered ready
- use grouped regression coverage when promoting behavior from read-only explanation to proposal generation and then to apply
- keep approval-mode validation stricter than proposal-mode validation because it changes project state

## Final Recommendation

Treat the knowledge pack, target-model conformance knowledge, deterministic context assembly, citation control, and evaluation harness
as the delivery-critical path. Frontend rollout should follow backend grounding, and write behavior should follow validated proposal
behavior rather than arriving in parallel.
