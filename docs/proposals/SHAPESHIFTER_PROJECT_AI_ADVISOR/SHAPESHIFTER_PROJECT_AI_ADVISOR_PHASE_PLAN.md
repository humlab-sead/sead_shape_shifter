# Shape Shifter Project AI Advisor Phase Plan

See [SHAPESHIFTER_PROJECT_AI_ADVISOR.md](./SHAPESHIFTER_PROJECT_AI_ADVISOR.md) for the full proposal: problem statement, stakeholders, product principles, MVP use cases, architecture, knowledge pack specification, evaluation plan, risks, and glossary.

This plan defines the delivery sequence. It keeps the highest-risk work early — curated knowledge, deterministic context assembly, citation control, redaction, and evaluation — so later user-facing steps do not arrive before the grounding they depend on.

## Pre-Existing Capabilities

Shape Shifter already has project YAML loading, validation, dependency analysis, preview services, reconciliation workflows, project-scoped session handling, target-model guidance, and a bundled SEAD superset target model. These are available as context sources for the advisor and do not need to be built from scratch.

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
- the phase documents which topics are in scope for the MVP and which remain deferred

### Phase 1: Read-Only Backend Advisor API

**Goal**

Deliver a backend advisor that can explain current project issues using grounded project context and curated rules.

**Focus**

- add provider abstraction for local and hosted providers
- build deterministic context assembly from project state, validation, conformance results, dependency summaries, target-model context,
  and selected knowledge-pack rules
- implement redaction, citation ID generation, response parsing, and citation validation
- support the MVP read-only use cases defined in the proposal

**Acceptance Criteria**

- the backend can answer MVP read-only advisor questions without editing YAML
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

- scenario-based evaluation exists for the defined MVP and boundary cases
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
- users can ask the MVP question types and review answers in the frontend
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

The proposal's [Product Principles](./SHAPESHIFTER_PROJECT_AI_ADVISOR.md#product-principles) (grounded, not generative; explicit uncertainty; deterministic code owns factual claims) apply throughout. The following rules are specific to delivery sequencing:

- do not expose write behavior before read-only grounding and evaluation are proven
- expand capability one step at a time: explain, then propose, then apply

## Validation Strategy

The proposal's [Evaluation Plan](./SHAPESHIFTER_PROJECT_AI_ADVISOR.md#evaluation-plan) defines the scenario-based evaluation harness, test categories, and evaluation gates. This section adds phase-sequencing rules for validation:

- validate redaction, citation allow-list behavior, and SEAD/SIMS responsibility boundaries before frontend rollout (Phase 3)
- validate structured proposals against existing schemas and validators before proposal mode is enabled (Phase 4)
- use grouped regression coverage when promoting behavior from read-only explanation to proposal generation and then to apply
- keep approval-mode validation stricter than proposal-mode validation because it changes project state
