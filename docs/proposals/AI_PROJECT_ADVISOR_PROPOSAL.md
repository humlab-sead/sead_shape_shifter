# AI Project Advisor Proposal

**Date:** March 15, 2026  
**Status:** Feature proposal  
**Scope:** Project-level advisory chat for Shape Shifter, with a clear understanding of SEAD as the downstream system

---

## Executive Summary

This proposal describes an **AI Project Advisor** for Shape Shifter.

The advisor is not meant to be a generic chatbot. It should help users understand a Shape Shifter project, explain validation and
dependency problems, review modeling choices, and suggest next steps before any project configuration is changed.

The advisor needs two kinds of input:

1. The current Shape Shifter project state.
2. The SEAD concepts that affect project design, especially identity, reconciliation, tracked entities, shared metadata, SIMS, and
   the SEAD Authoritative Service.

The safest rollout is phased:

1. Start with a read-only advisor that explains existing project issues.
2. Add structured proposal generation after the explanation workflow is reliable.
3. Add approval-based change application only after proposals can be validated and reviewed.

---

## Problem Statement

Users working on larger projects currently need to connect several pieces of information manually:

1. Shape Shifter YAML rules.
2. Current validation and dependency results.
3. The structure and quality of the source data.
4. Reconciliation requirements.
5. SEAD target-system requirements.
6. SIMS identity rules.
7. External service behavior already used by Shape Shifter, especially the SEAD Authoritative Service used for reconciliation.

This creates common problems:

1. A YAML change can be valid for Shape Shifter but still be a poor fit for SEAD.
2. Users may mix up tracked entities, shared metadata, and child values.
3. Users may not know whether a foreign key represents ownership or association.
4. A modeling choice may create identity or reconciliation problems later.
5. The editor can report errors, but it does not always explain them in domain terms.

The advisor should help close that gap.

Shape Shifter already has much of the structured context an advisor would need:

1. Project YAML loading and saving.
2. API-to-Core conversion, including directive resolution.
3. Structural validation.
4. Data validation.
5. Dependency graph analysis.
6. Preview and materialization services.
7. Reconciliation workflows.
8. Suggestion and auto-fix patterns.
9. Project-level session handling.

What is missing is a feature that turns those results into useful answers, such as:

1. "Why is this entity failing validation?"
2. "Should this be a fixed entity or a sourced entity?"
3. "How should I model this relationship so it can be ingested into SEAD cleanly?"
4. "Is this a tracked entity, shared metadata, or a child value?"
5. "What would SIMS expect for identity allocation here?"

---

## Product Principle: Grounded SEAD-Aware Advisor

The advisor must be a **grounded project advisor**, not a free-form assistant.

"Grounded" means the advisor answers from known project data and curated rules. It should not invent project state, YAML fields, or
SEAD policy.

The advisor needs three kinds of input.

### 1. Project Context

This comes from the active project and current editor or runtime state:

1. Raw YAML.
2. Resolved Core project.
3. Selected entity YAML.
4. Structural validation results.
5. Data validation results.
6. Dependency graph and cycle details.
7. Preview and materialization summaries.
8. Task and note context when relevant.

### 2. Shape Shifter Domain Knowledge

This is curated knowledge from active Shape Shifter documentation and rules:

1. YAML configuration rules.
2. Three-tier identity conventions.
3. Dependency and foreign-key modeling patterns.
4. Directive behavior.
5. Validation rules.
6. Reconciliation workflow expectations.

### 3. SEAD Target-System Knowledge

This is curated, versioned knowledge about SEAD and the related services around it:

1. Tracked entities versus shared metadata.
2. Identity terminology and responsibilities.
3. Ownership versus association.
4. Reconciliation expectations.
5. Provider identity versus official SEAD identity.
6. SIMS responsibilities versus Shape Shifter responsibilities.
7. SEAD Authoritative Service responsibilities versus Shape Shifter responsibilities.
8. How reconciliation, authority lookup, and identity allocation fit together.

This third input is essential. The advisor should answer not only "how do I write this YAML?" but also "is this a good SEAD model?"

---

## SEAD/SIMS Knowledge Requirements

The advisor should treat the following topics as core rules when it gives advice.

### Stable Identity Is Layered Above SEAD Relational IDs

The SEAD identity docs describe several kinds of identity:

1. SEAD internal relational identity.
2. Stable SEAD UUID identity.
3. Provider keys.
4. Business keys.
5. Authority keys.

The advisor must not suggest that SEAD integer keys are suitable as public identities.

### SIMS Owns Identity Allocation, Not Shape Shifter

The SEAD identity docs draw this line:

1. SIMS owns identity allocation and long-term identity mapping.
2. Shape Shifter owns normalization, reconciliation inputs, and client-side API behavior.

The advisor must not imply that Shape Shifter should become the long-term identity authority.

### The SEAD Authoritative Service Already Affects Modeling

Shape Shifter already calls a SEAD-facing reconciliation service during reconciliation workflows.

This means target-system advice is not only about final export. External SEAD service behavior already affects project design and
reconciliation.

The advisor should be able to explain:

1. Which fields and entity types are reconciled against the authoritative service.
2. When a modeling choice improves or weakens reconciliation quality.
3. How reconciliation data differs from identity allocation.
4. Where authority lookup ends and SIMS-style identity allocation begins.

### Ownership and Association Must Be Kept Separate

The SEAD identity design and assessment docs explain that not every relationship is a strict parent-child ownership relationship.

This matters for modeling advice:

1. Some relationships mean ownership and aggregate state.
2. Some relationships connect independently meaningful entities.
3. Some objects are shared metadata and should be reconciled instead of duplicated.

### Tracked Entities and Shared Metadata Must Not Be Collapsed

The identity docs distinguish between:

1. Tracked entities with stable identity.
2. Shared metadata and classifiers.
3. Child values that do not have independent identity.

The advisor should explain this distinction in practical Shape Shifter terms.

---

## V1 Use Cases

The MVP should answer only three kinds of questions:

1. **Explain this validation error.** Take a validation message and explain what it means, why it happened, and how the user can fix it.
2. **Explain this entity and its risks.** Take a selected entity and summarize its configuration, dependencies, and possible
   modeling problems.
3. **Review project risks before execution.** Summarize project-level risks, dependency issues, and validation state before the user
   runs a project.

These use cases are narrow enough to test well and broad enough to be useful. Open-ended modeling advice should wait until the
knowledge pack and evaluation suite are in place.

Typical V1 prompts:

1. "Explain why this project YAML fails validation."
2. "What risks does this entity have before I run the project?"
3. "Review this `shapeshifter.yml` and explain problems."

---

## Explicit Non-Goals

V1 should not:

1. Edit YAML automatically without user approval.
2. Invent undocumented SEAD policy.
3. Act as the identity authority.
4. Make destructive changes.
5. Save chat-derived project changes silently.
6. Provide broad open-ended modeling advice beyond the three MVP use cases.

Future phases may add:

1. Structured proposal generation, such as YAML patches with explanations.
2. Data-to-configuration help, such as source-file exploration and draft YAML.
3. An approval-based apply workflow.

These are out of scope for the first delivery.

---

## Architecture

### Backend

Add a new backend feature area:

1. `backend/app/models/advisor.py` — Request and response Pydantic models.
2. `backend/app/services/advisor_service.py` — Receives the question, assembles context, calls the provider, parses the response,
   and returns a structured result.
3. `backend/app/services/advisor_context_service.py` — Builds deterministic context from project state, validation results,
   dependency summaries, knowledge-pack rules, and citation IDs.
4. `backend/app/services/llm/` — Provider interfaces and implementations, such as local Ollama and hosted providers.
5. `backend/app/api/v1/endpoints/advisor.py` — Route handler for advisor requests.

The service should follow existing backend layering:

1. API models define request and response shapes.
2. Services handle orchestration.
3. Mappers handle API-to-Core conversion where needed.
4. API DTOs do not contain business logic.

### Deterministic Code vs Model Responsibility

The split between normal application code and the LLM must be explicit.

**Deterministic code should handle:**

- project loading and YAML parsing
- schema validation
- dependency graph extraction
- preview summaries
- secret redaction
- context assembly
- citation object generation
- patch validation when proposal mode is added

**The model should handle:**

- plain-language explanations
- issue prioritization
- user-facing reasoning summaries
- suggested next actions
- draft proposals in future phases

**The model should not be trusted to:**

- decide whether YAML is valid without validator confirmation
- invent SEAD rules
- apply changes directly
- infer secrets
- override validation results
- reference citation IDs that were not provided in the assembled context

### Frontend

Add project-level UI in the project detail page. Two reasonable options are:

1. A new `Advisor` tab.
2. A right-side advisor drawer tied to the active project.

The frontend should reuse current patterns:

1. Pinia store or composable for advisor session state.
2. Existing project and session context.
3. API client module in `frontend/src/api/`.

### Provider Abstraction

Do not hardwire one LLM vendor into the feature logic.

Use a provider abstraction that supports at least:

1. A local model option, such as Ollama.
2. A hosted provider option.
3. Configuration through backend settings.

This is a sensible choice because the repo already has test-side references to OpenAI, Anthropic, and Ollama configuration.

### Context Redaction and Privacy

The advisor must not send secrets or resolved credentials to a hosted provider. This is a core design requirement.

**Redaction rules:**

1. Redact environment-resolved values, such as `${ENV_VAR}` expansions that contain credentials.
2. Exclude datasource connection strings, passwords, and tokens from context assembly.
3. Prefer structured summaries over raw YAML when the YAML contains sensitive directives.
4. Support a local-provider-only mode for environments where data must not leave the host.
5. Log the context sent to external providers for audit purposes, with secrets already removed.

**Context whitelist:**

The context assembler should use an explicit whitelist of safe fields instead of sending the full project object. This whitelist includes:

- project name and metadata
- entity names and structural configuration, with directives preserved as raw strings
- validation messages and error codes
- dependency graph edges
- knowledge-pack rule IDs and text
- citation IDs

---

## Knowledge Pack Specification

The knowledge pack is the most important design element in this proposal. Without curated SEAD knowledge, the advisor may explain YAML
well while still giving poor SEAD modeling advice.

### Rule Schema

Each knowledge-pack rule is a structured document with these fields:

| Field           | Type         | Description                                                                                     |
|-----------------|--------------|-------------------------------------------------------------------------------------------------|
| `id`            | string       | Stable identifier, e.g. `sead.identity.sims-owns-allocation`                                    |
| `title`         | string       | Human-readable name                                                                             |
| `status`        | enum         | `stable`, `provisional`, `deprecated`                                                           |
| `confidence`    | enum         | `high`, `medium`, `low`                                                                         |
| `source`        | list[string] | Source documents this rule comes from                                                           |
| `rule`          | string       | The rule text the advisor should enforce or reference                                           |
| `caveats`       | list[string] | Known limitations, unresolved questions, or conditions                                          |
| `applies_to`    | list[string] | Scopes such as `reconciliation`, `export`, `public_id`, `identity modeling`, and `foreign keys` |
| `examples`      | list[object] | Optional examples showing correct and incorrect patterns                                        |
| `last_reviewed` | date         | Last date the rule was reviewed for accuracy                                                    |

### Example Rule

```yaml
id: sead.identity.sims-owns-allocation
title: SIMS owns stable identity allocation
status: stable
confidence: high
source:
  - sead_identity_system/docs/SYSTEMS_DESIGN.md
rule: >
  Shape Shifter may prepare reconciliation inputs and consume identity mappings,
  but it must not act as the official allocator of long-term SEAD identities.
caveats:
  - Shape Shifter may still create temporary client-side identifiers during preview or staging.
applies_to:
  - reconciliation
  - export
  - public_id
  - identity modeling
```

### Knowledge Pack Sources

**Shape Shifter sources:**

1. Configuration guide.
2. AI validation guide.
3. Architecture and developer guides.
4. Generated `projectSchema.json` and `entitySchema.json` as structural references.

**SEAD and SIMS sources:**

1. `sead_identity_system/docs/README.md`
2. `sead_identity_system/docs/REQUIREMENTS.md`
3. `sead_identity_system/docs/SYSTEMS_DESIGN.md`
4. `sead_identity_system/docs/ASSESSMENT.md`

**Reconciliation sources:**

1. Reconciliation workflow documentation.
2. Reconciliation setup guide.
3. Reconciliation client and service implementation.
4. Entity types and service metadata exposed through the existing reconciliation flow.

### Curation Rule

The advisor should not treat every low-level design note as final truth. The SEAD assessment identifies unresolved modeling questions,
especially around:

1. Aggregate assumptions.
2. Association versus ownership.
3. Official SEAD identity versus provider identity.

Capture that uncertainty in each rule with `confidence` and `caveats`.

### Versioning

The knowledge pack should be versioned so that:

1. Advisor responses can show which pack version they used.
2. Rules can be updated when SEAD design documents change.
3. Stale rules can be flagged for review.

---

## Context Assembly and Redaction

The advisor should not receive the whole project by default. Instead, the context assembler should build a structured packet with
limited sections.

### Base Context

Include this for every question:

1. Project name.
2. Active tab or selected entity, if available.
3. Summary of validation state.
4. Dependency summary.
5. Concise project metadata.
6. Structural schema metadata from the generated project and entity JSON schemas.

### Entity Context

Include this when the question is about a specific entity:

1. Selected entity YAML.
2. Resolved entity configuration.
3. Relevant validation messages.
4. Neighboring dependencies.
5. Preview summary, if available.

### Knowledge Pack Rules

Include curated rules instead of raw document dumps. Select only the rules that match the current question, using `applies_to`
tags and the active entity types.

### Why a Knowledge Pack Is Better Than Dumping Docs

Raw document injection will become noisy and may include conflicting notes. A knowledge pack is better because it:

1. Extracts stable rules from the SEAD docs.
2. Cites the source documents used to create those rules.
3. Can be updated intentionally when SEAD design changes.
4. Keeps the prompt compact and easier to audit.

---

## Response and Citation Model

### Response Shape

The advisor response should be structured:

1. `answer` — direct response to the user's question.
2. `reasoning_summary` — why the advisor reached this conclusion.
3. `citations` — structured references to project data, validation messages, or rules.
4. `suggested_next_actions` — concrete follow-up steps.
5. `proposed_yaml_changes` — optional, and only for future phases.

### Citation Technical Model

Citations are not free text. The deterministic context assembler creates citation IDs, and the model may only use the IDs it was given.

**Citation ID format:**

```text
<category>.<scope>.<identifier>
```

**Categories:**

| Category              | Example                                                |
|-----------------------|--------------------------------------------------------|
| `project.entity`      | `project.entity.site.keys`                             |
| `validation.message`  | `validation.message.E1023`                             |
| `dependency.edge`     | `dependency.edge.site.sample_group`                    |
| `sead.rule`           | `sead.identity.tracked-entity`                         |
| `sims.rule`           | `sims.responsibility.allocation`                       |
| `reconciliation.rule` | `reconciliation.authoritative-service.supported-types` |
| `knowledge.pack`      | `knowledge.pack.sead.identity.sims-owns-allocation`    |

**Citation object shape:**

```json
{
  "id": "validation.message.E1023",
  "category": "validation.message",
  "label": "Missing required key field on entity 'site'",
  "target": "entity.site",
  "yaml_path": "entities.site.keys",
  "clickable": true
}
```

**Citation rules:**

1. The backend assembles all available citation IDs before calling the model.
2. The model may only reference citation IDs that appear in the assembled context.
3. The response parser rejects or flags citation IDs that are not in the allowed set.
4. Citations are persisted with the chat session so users can review them later.
5. The UI renders citations as clickable chips that navigate to the relevant entity, validation message, or knowledge-pack rule.

A vague citation like "SEAD rule" is not enough. A useful citation should point to a specific rule ID, validation message, or YAML path.

---

## Evaluation Plan

Define the evaluation suite before implementation so advisor quality can be measured and checked for regressions.

### Test Categories

| Category                                   | What it checks                                                                    |
|--------------------------------------------|-----------------------------------------------------------------------------------|
| Validation-error explanation               | Can the advisor explain a real validation message in plain language?              |
| Dependency-cycle explanation               | Can the advisor explain why a cycle exists and how to break it?                   |
| Tracked/shared/value-object classification | Does the advisor correctly distinguish entity types?                              |
| SIMS responsibility split                  | Does the advisor avoid claiming that Shape Shifter allocates official identities? |
| Authoritative-service responsibility split | Does the advisor correctly describe when the authoritative service is involved?   |
| YAML patch proposal                        | Phase 2: Are proposed patches valid and minimal?                                  |
| Refusal and uncertainty                    | Does the advisor say "I don't know" instead of inventing rules?                   |
| Hallucination                              | Does the advisor avoid inventing SEAD rules or YAML fields?                       |
| Redaction                                  | Are secrets excluded from context sent to hosted providers?                       |
| Regression                                 | Do known Shape Shifter projects still produce correct advice?                     |

### Scenario-Based Format

Evaluation scenarios use a structured format:

```yaml
scenario: sourced_taxon_with_ambiguous_identity
input:
  project_yaml: |
    entities:
      taxon:
        type: sql
        keys: [scientific_name]
        # No reconciliation configured
  validation_messages: []
question: Should this be reconciled or fixed?
expected:
  must_mention:
    - shared metadata
    - reconciliation
    - authoritative service
  must_not_claim:
    - Shape Shifter allocates official SEAD UUIDs
  acceptable_citations:
    - sead.rule.tracked-entity
    - reconciliation.rule.authoritative-service.supported-types
```

### Evaluation Gates

1. Phase 1a, the backend API, must pass all scenario tests before Phase 1b, the frontend, begins.
2. Phase 2, proposal generation, must pass YAML patch validation tests before user-facing proposal mode is enabled.
3. Each phase should add regression scenarios that cover previous phases.

---

## Phased Delivery Plan

### Phase 0: Knowledge Foundation

Before building the advisor API, create a curated knowledge pack containing:

1. Stable Shape Shifter modeling rules.
2. Stable SEAD/SIMS concepts.
3. Stable SEAD Authoritative Service concepts.
4. Explicit caveats where the SEAD design is still unsettled.

This is the most important prerequisite for useful advice.

### Phase 1a: Backend-Only Advisor API

Deliver the advisor as a backend service with a test harness. Do not add the frontend yet.

**Deliverables:**

1. Provider abstraction for local and hosted providers.
2. Context assembler with redaction.
3. Knowledge pack loader and rule selection.
4. Citation ID generation.
5. Response parsing and citation validation.
6. CLI or script-based test harness for scenario evaluation.

**Expected effort:** roughly 1 to 2 focused weeks.

This phase is higher risk than a typical backend endpoint because context assembly and citations need to be reliable before users see
the feature in the frontend.

### Phase 1b: Frontend Chat UI

Add the user-facing advisor UI after the backend API is stable.

**Deliverables:**

1. Advisor tab or drawer in the project detail page.
2. Pinia store for session state.
3. Citation chip rendering.
4. Streaming or non-streaming response display.

**Expected effort:** roughly 1 focused week after Phase 1a is complete.

### Phase 2: Structured Proposal Generation

Add a mode that suggests changes without applying them.

**Includes:**

1. Schema-guided output using the existing generated JSON schemas as a starting point.
2. YAML patch proposals with citations.
3. Project YAML repair suggestions.
4. Proposal preview UI.
5. More evaluation scenarios for proposal quality.

**Expected effort:** roughly 2 to 4 additional weeks.

### Phase 3: Data-To-Configuration Assistance

Add source-data exploration that can propose an initial config file from observed files, columns, types, and sample values.

**Includes:**

1. Source-file discovery and profiling.
2. Column and type summaries.
3. Candidate entity and relationship suggestions.
4. Draft `shapeshifter.yml` generation.
5. Validation-guided refinement.

**Expected effort:** roughly 2 to 4 additional weeks.

### Phase 4: Approval-Based Apply

Only add approval-based YAML changes after proposal mode and data-to-configuration mode are stable.

**Includes:**

1. Proposal-to-change conversion.
2. Preview and rollback integration.
3. Approval workflow.
4. Conflict and version handling.
5. Regression validation.

**Expected effort:** roughly 2 to 4 additional weeks.

---

## Risks and Mitigations

### Risk: Stale or Contested SEAD Knowledge

The SEAD identity design has unresolved areas. Knowledge-pack rules may become outdated or may reflect assumptions that later change.

**Mitigation:**

1. Version the knowledge pack.
2. Include `confidence` and `status` metadata on every rule.
3. Make uncertainty visible in advisor responses.
4. Require review when SEAD identity documents change.

### Risk: Users Trust the Advisor More Than Validators

Users may over-trust fluent explanations and treat advisor output as definitive.

**Mitigation:**

1. Validate every YAML proposal with existing Shape Shifter validators before display.
2. Label advice as advisory in the UI.
3. Always show a diff and validation result before applying changes.

### Risk: Project Data Leaks to Hosted Providers

Project data sent to external LLM providers may contain sensitive information.

**Mitigation:**

1. Use the explicit context whitelist described above.
2. Scan and redact secrets before provider calls.
3. Support provider-specific privacy modes, including a local-only option.
4. Add logging controls for audit trails.

### Risk: Citations Become Decorative

If the model can invent citation IDs, citations lose their value.

**Mitigation:**

1. The backend assembles citation IDs before calling the model.
2. The model may only reference citation IDs provided in the assembled context.
3. The response parser rejects unknown citation IDs.

---

## Success Criteria

The feature should be considered successful when it can reliably:

1. Explain current project issues using real project data.
2. Give advice that follows Shape Shifter rules.
3. Give advice that respects SEAD service responsibilities, including SIMS and the SEAD Authoritative Service.
4. Clearly distinguish confidence from uncertainty.
5. Review, repair, and author project YAML through explicit proposals in Phase 2 and later.
6. Help users avoid downstream modeling mistakes.
7. Remain safe even when the model is wrong.

---

## Key Recommendation

Build this feature.

Build it as a **grounded SEAD-aware project advisor**, not as a generic chat client.

The most important design choice is to make target-system knowledge explicit and curated from the start. Without that, the advisor may
explain YAML well while still giving poor advice about the SEAD domain and the external SEAD services that already affect project
behavior.

With that knowledge layer in place, the feature has a realistic path:

1. Explain.
2. Recommend.
3. Propose.
4. Apply only after approval.
