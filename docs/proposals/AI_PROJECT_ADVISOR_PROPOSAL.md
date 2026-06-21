# AI Project Advisor Proposal

**Date:** March 15, 026  
**Status:** Feature proposal  
**Scope:** Project-scoped advisory chat for Shape Shifter with explicit SEAD target-system knowledge

---

## Executive Summary

This proposal describes an **AI Project Advisor** for Shape Shifter.

The feature is not a generic chatbot. It is a grounded advisory workflow that helps users understand project YAML, diagnose validation and dependency problems, reason about modeling choices, and receive safe, explainable suggestions before any configuration is changed.

The key requirement is that the advisor must know **both**:

1. the current Shape Shifter project state, and
2. the relevant target-system concepts for SEAD, especially identity, reconciliation, tracked entities, shared metadata, and the boundaries to external SEAD-side services such as SIMS and the SEAD Authoritative Service.

This proposal recommends a phased implementation that starts as a **read-only grounded advisor** and only later grows into **proposal generation** and then carefully controlled **change application**.

---

## Problem Statement

Users working on non-trivial projects must currently bridge several knowledge layers manually:

1. Shape Shifter YAML semantics,
2. current validation and dependency state,
3. source-data characteristics,
4. reconciliation expectations,
5. SEAD target-system expectations,
6. evolving SIMS identity concepts,
7. external service behavior already used by Shape Shifter, especially the SEAD Authoritative Service used for reconciliation.

That fragmentation creates predictable failure modes:

1. users may make locally valid YAML changes that are conceptually wrong for SEAD,
2. users may confuse tracked entities with shared metadata or owned child structures,
3. users may not understand when a foreign key relationship is modeling ownership versus association,
4. users may not understand when a modeling choice creates downstream identity or reconciliation problems,
5. the editor can report errors, but it does not yet explain them in domain terms.

The advisor should reduce that gap.

Shape Shifter already has much of the structured context an advisor would need:

1. project YAML loading and saving,
2. API/Core conversion with directive resolution,
3. structural validation,
4. data validation,
5. dependency graph analysis,
6. preview and materialization services,
7. reconciliation workflows,
8. suggestion and auto-fix patterns,
9. project-scoped session handling.

What is missing is a feature that can turn those signals into a user-facing conversation such as:

1. "Why is this entity failing validation?"
2. "Should this be a fixed entity or a sourced entity?"
3. "How should I model this relationship so it will ingest cleanly into SEAD?"
4. "Is this a tracked entity, shared metadata, or a value-like child structure?"
5. "What would SIMS expect for identity allocation here?"

---

## Product Principle: Grounded SEAD-aware Advisor

The advisor must be a **grounded project advisor**, not a free-form general-purpose assistant.

Grounding comes from three distinct knowledge planes:

### 1. Project Context

Derived from the active project and current editor/runtime state:

1. raw YAML,
2. resolved Core project,
3. selected entity YAML,
4. structural validation results,
5. data validation results,
6. dependency graph and cycle information,
7. preview/materialization signals,
8. task and note context when relevant.

### 2. Shape Shifter Domain Knowledge

Curated knowledge from active Shape Shifter documentation and rules:

1. YAML configuration semantics,
2. three-tier identity conventions,
3. dependency and foreign-key modeling patterns,
4. directive behavior,
5. validation rules,
6. reconciliation workflow expectations.

### 3. SEAD Target-System Knowledge

Curated, versioned knowledge about downstream SEAD concepts and the wider SEAD service ecosystem:

1. tracked entities versus shared metadata,
2. identity terminology,
3. ownership versus association,
4. reconciliation expectations,
5. provider identity versus canonical SEAD identity,
6. SIMS responsibilities versus Shape Shifter responsibilities,
7. SEAD Authoritative Service responsibilities versus Shape Shifter responsibilities,
8. interactions between reconciliation, authority lookup, and identity allocation.

This third plane is essential. The advisor should not only answer "how do I write YAML for this" but also "is this a sound representation for SEAD".

---

## SEAD/SIMS Knowledge Requirements

The advisor should treat the following as first-class concepts when generating advice.

### Stable Identity Is Layered Above SEAD Relational IDs

The SEAD identity docs define a separation between:

1. SEAD internal relational identity,
2. stable SEAD UUID identity,
3. provider keys,
4. business keys,
5. authority keys.

The advisor must avoid advice that assumes SEAD integer keys are suitable public identities.

### SIMS Owns Identity Allocation, Not Shape Shifter

The SEAD identity docs define a boundary where:

1. SIMS owns identity allocation and long-term identity mapping,
2. Shape Shifter owns normalization, reconciliation inputs, and client-side API behavior.

The advisor must therefore avoid implying that Shape Shifter should itself become the canonical identity authority.

### The SEAD Authoritative Service Already Influences Modeling Through Reconciliation

Shape Shifter already calls a SEAD-facing reconciliation service during reconciliation workflows.

The advisor must understand that target-system advice is not limited to export-time ingestion. It is already influenced by an external SEAD service during project design and reconciliation.

The advisor should be able to reason about:

1. what fields and entity types are reconciled against the authoritative service,
2. when a modeling choice improves or weakens reconciliation quality,
3. how reconciliation evidence differs from identity allocation,
4. where authority lookup ends and SIMS-style identity allocation begins.

### Ownership And Association Must Be Distinguished

The SEAD identity design and assessment docs emphasize that not all entity relationships are strict parent-child ownership chains.

That matters directly for modeling advice:

1. some relationships imply ownership and aggregate state,
2. some relationships are associations between independently meaningful entities,
3. some objects are shared metadata requiring reconciliation rather than naïve duplication.

### Tracked Entities And Shared Metadata Must Not Be Collapsed

The identity docs highlight a distinction between:

1. tracked entities with stable identity,
2. shared metadata and classifiers,
3. value objects or owned child structures without independent identity.

The advisor should be able to explain that distinction in practical Shape Shifter terms.

---

## V1 Use Cases

The MVP should answer only three classes of questions:

1. **"Explain this validation error."** — Take a validation message and explain what it means, why it occurred, and what the user can do to fix it.
2. **"Explain this entity and its risks."** — Take a selected entity and summarize its configuration, dependencies, and potential modeling concerns.
3. **"Review project risks before execution."** — Summarize project-level risks, dependency issues, and validation state before the user runs a project.

These three use cases are narrow enough to test thoroughly and broad enough to demonstrate value. Open-ended modeling advice should wait until the knowledge pack and evaluation suite are in place.

Typical V1 prompts:

1. "Explain why this project YAML fails validation."
2. "What risks does this entity have before I run the project?"
3. "Review this `shapeshifter.yml` and explain problems."

---

## Explicit Non-goals

V1 should not:

1. auto-edit YAML without user approval,
2. invent undocumented SEAD policy,
3. act as the identity authority,
4. make destructive changes,
5. silently persist chat-derived project changes,
6. provide broad open-ended modeling advice beyond the three MVP use cases.

Future phases may add:

1. structured proposal generation (YAML patches with explanation),
2. data-to-configuration assistance (source-file exploration and draft YAML),
3. approval-based apply workflow.

These are out of scope for the initial delivery.

---

## Architecture

### Backend

Add a new backend feature area:

1. `backend/app/models/advisor.py` — Request/response Pydantic models.
2. `backend/app/services/advisor_service.py` — Orchestration: receive question, assemble context, call provider, parse response, return structured result.
3. `backend/app/services/advisor_context_service.py` — Deterministic context assembly: load project state, extract validation results, build dependency summary, assemble knowledge pack rules, generate citation IDs.
4. `backend/app/services/llm/` — Provider abstractions (local Ollama, hosted providers).
5. `backend/app/api/v1/endpoints/advisor.py` — Route handler for advisor requests.

The service should follow existing backend layering:

1. API models for request/response,
2. service layer for orchestration,
3. mappers for boundary conversion where needed,
4. no business logic in API DTOs.

### Deterministic vs Model Responsibility

The safety boundary between deterministic system logic and the LLM must be explicit.

**Deterministic code should handle:**

- project loading and YAML parsing
- schema validation
- dependency graph extraction
- preview summaries
- secret redaction
- context assembly
- citation object generation
- patch validation (when proposals are added)

**The model should handle:**

- explanation in plain language
- prioritization of issues
- user-facing reasoning summaries
- suggested next actions
- draft proposals (future phases)

**The model should not be trusted to:**

- decide whether YAML is valid without validator confirmation
- invent SEAD rules
- apply changes directly
- infer secrets
- override validation results
- reference citation IDs not provided in the assembled context

### Frontend

Add a project-scoped UI surface in the project detail page, preferably:

1. a new `Advisor` tab, or
2. a right-side advisor drawer tied to the active project.

The frontend should reuse current patterns:

1. Pinia store or composable for advisor session state,
2. existing project/session context,
3. API client module in `frontend/src/api/`.

### Provider Abstraction

Do not hardwire one vendor into feature logic.

Use a provider abstraction supporting at least:

1. local model option such as Ollama,
2. hosted provider option,
3. pluggable configuration through backend settings.

This is justified because the repo already contains test-side references to OpenAI, Anthropic, and Ollama configuration.

### Context Redaction and Privacy

The advisor must not send secrets or resolved credentials to a hosted provider. This is a first-class design concern, not an afterthought.

**Redaction rules:**

1. Redact environment-resolved values (e.g., `${ENV_VAR}` expansions that contain credentials).
2. Exclude datasource connection strings, passwords, and tokens from context assembly.
3. Prefer structured summaries over raw YAML when the YAML contains sensitive directives.
4. Support a local-provider-only mode for environments where data must not leave the host.
5. Log all context sent to external providers for audit purposes.

**Context whitelist:**

The context assembler should build input from an explicit whitelist of safe fields rather than sending the full project object. This whitelist includes:

- project name and metadata
- entity names and structural configuration (directives preserved as raw strings, not resolved)
- validation messages and error codes
- dependency graph edges
- knowledge pack rule IDs and text
- citation IDs

---

## Knowledge Pack Specification

The knowledge pack is the most important design element in this proposal. Without curated target-system knowledge, the advisor may be superficially helpful about YAML while giving poor advice about the SEAD domain.

### Rule Schema

Each knowledge-pack rule is a structured document with the following fields:

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Stable identifier, e.g. `sead.identity.sims-owns-allocation` |
| `title` | string | Human-readable name |
| `status` | enum | `stable`, `provisional`, `deprecated` |
| `confidence` | enum | `high`, `medium`, `low` |
| `source` | list[string] | Source documents this rule is derived from |
| `rule` | string | The rule text — what the advisor should enforce or reference |
| `caveats` | list[string] | Known limitations, unresolved areas, or conditions |
| `applies_to` | list[string] | Scopes the rule applies to: `reconciliation`, `export`, `public_id`, `identity modeling`, `foreign keys`, etc. |
| `examples` | list[object] | Optional examples showing correct and incorrect patterns |
| `last_reviewed` | date | Last date the rule was reviewed for accuracy |

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
  but it must not behave as the canonical allocator of long-term SEAD identities.
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

1. Configuration guide
2. AI validation guide
3. Architecture and developer guides
4. Generated `projectSchema.json` and `entitySchema.json` as structural references

**SEAD and SIMS sources:**

1. `sead_identity_system/docs/README.md`
2. `sead_identity_system/docs/REQUIREMENTS.md`
3. `sead_identity_system/docs/SYSTEMS_DESIGN.md`
4. `sead_identity_system/docs/ASSESSMENT.md`

**Reconciliation sources:**

1. Reconciliation workflow documentation
2. Reconciliation setup guide
3. Reconciliation client and service implementation
4. Entity types and service metadata exposed through the existing reconciliation flow

### Curation Rule

The advisor should not treat every lower-level design note as settled truth. The SEAD assessment explicitly identifies unresolved modeling issues, especially around:

1. aggregate assumptions,
2. association versus ownership,
3. canonical identity versus provider identity.

That uncertainty should be captured in the knowledge pack as `confidence` and `caveats` metadata.

### Versioning

The knowledge pack should be versioned so that:

1. advisor responses can cite which pack version they used,
2. rules can be updated when SEAD design documents change,
3. stale rules can be flagged for review.

---

## Context Assembly and Redaction

The advisor should not receive the whole project by default. Instead, the context assembler builds a structured packet with bounded sections.

### Base Context

Included for every question:

1. project name,
2. active tab or selected entity if available,
3. summary of validation state,
4. dependency summary,
5. concise project metadata,
6. structural schema metadata from the generated project and entity JSON schemas.

### Entity Context

Included when the question is entity-focused:

1. selected entity YAML,
2. resolved entity configuration,
3. relevant validation messages,
4. neighboring dependencies,
5. preview summary if available.

### Knowledge Pack Rules

Included as curated guidance rather than raw full-document dumps. Only rules relevant to the current question scope are included, selected by `applies_to` tags and the active entity types.

### Why a Knowledge Pack Is Better Than Dumping Docs

Raw doc injection will eventually become noisy and contradictory. The knowledge pack approach:

1. extracts stable rules from the SEAD docs,
2. cites the source documents used to derive those rules,
3. can be updated intentionally when SEAD design changes,
4. keeps the prompt compact and auditable.

---

## Response and Citation Model

### Response Shape

The advisor response should be structured:

1. answer — direct response to the user's question,
2. reasoning summary — why the advisor reached this conclusion,
3. citations — structured references to evidence used,
4. suggested next actions — concrete follow-up steps,
5. optional proposed YAML changes — in future phases.

### Citation Technical Model

Citations are not free text. They are structured references generated by the deterministic context assembler and returned by the model using only the IDs it was given.

**Citation ID format:**

```
<category>.<scope>.<identifier>
```

**Categories:**

| Category | Example |
|----------|---------|
| `project.entity` | `project.entity.site.keys` |
| `validation.message` | `validation.message.E1023` |
| `dependency.edge` | `dependency.edge.site.sample_group` |
| `sead.rule` | `sead.identity.tracked-entity` |
| `sims.rule` | `sims.boundary.allocation` |
| `reconciliation.rule` | `reconciliation.authoritative-service.supported-types` |
| `knowledge.pack` | `knowledge.pack.sead.identity.sims-owns-allocation` |

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
3. The response parser rejects or flags citation IDs not in the allowed set.
4. Citations are persisted with the chat session so users can review evidence later.
5. The UI renders citations as clickable chips that navigate to the relevant entity, validation message, or knowledge-pack rule.

A vague citation like "SEAD rule" is not sufficient. A useful citation should point to a specific rule ID, validation message, or YAML path.

---

## Evaluation Plan

Before implementation, define an evaluation suite so the advisor's quality can be measured and regressed against.

### Test Categories

| Category | What it checks |
|----------|---------------|
| Validation-error explanation | Can the advisor explain a real validation message in plain language? |
| Dependency-cycle explanation | Can the advisor explain why a cycle exists and how to break it? |
| Tracked/shared/value-object classification | Does the advisor correctly distinguish entity types? |
| SIMS boundary | Does the advisor avoid claiming Shape Shifter allocates canonical identities? |
| Authoritative-service boundary | Does the advisor correctly describe when the authoritative service is involved? |
| YAML patch proposal | (Phase 2) Are proposed patches valid and minimal? |
| Refusal/uncertainty | Does the advisor say "I don't know" rather than inventing rules? |
| Hallucination | Does the advisor avoid inventing SEAD rules or YAML fields? |
| Redaction | Are secrets excluded from context sent to hosted providers? |
| Regression | Do known Shape Shifter projects still produce correct advice? |

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
    - Shape Shifter allocates canonical SEAD UUIDs
  acceptable_citations:
    - sead.rule.tracked-entity
    - reconciliation.rule.authoritative-service.supported-types
```

### Evaluation Gates

1. Phase 1a (backend API) must pass all scenario tests before Phase 1b (frontend) begins.
2. Phase 2 (proposal generation) must pass YAML patch validation tests before user-facing proposal mode is enabled.
3. Each phase addition should include regression scenarios covering previous phases.

---

## Phased Delivery Plan

### Phase 0: Knowledge Foundation

Before building the advisor API, create a curated knowledge pack containing:

1. stable Shape Shifter modeling rules,
2. stable SEAD/SIMS concepts,
3. stable SEAD Authoritative Service concepts,
4. explicit caveats where the SEAD design is still unsettled.

This is the most important prerequisite for useful advice.

### Phase 1a: Backend-Only Advisor API

Deliver the advisor as a backend service with a test harness, no frontend yet.

**Deliverables:**

1. Provider abstraction (local + hosted)
2. Context assembler with redaction
3. Knowledge pack loader and rule selection
4. Citation ID generation
5. Response parsing and citation validation
6. CLI or script-based test harness for scenario evaluation

**Expected effort:** roughly 1 to 2 focused weeks.

This phase is higher risk than a typical backend endpoint because the context assembly and citation mechanisms need to be reliable before the frontend adds user-facing surface area.

### Phase 1b: Frontend Chat Surface

Add the user-facing advisor UI after the backend API is stable.

**Deliverables:**

1. Advisor tab or drawer in the project detail page
2. Pinia store for session state
3. Citation chip rendering
4. Streaming or non-streaming response display

**Expected effort:** roughly 1 focused week after Phase 1a is complete.

### Phase 2: Structured Proposal Generation

Add a mode that returns explicit suggested changes without applying them.

**Includes:**

1. Schema-guided output using the existing generated JSON schemas as a starting point.
2. YAML patch proposals with citations.
3. Project YAML repair suggestions.
4. Proposal preview UX.
5. Richer evaluation scenarios for proposal quality.

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

Only after proposal mode and data-to-configuration mode are stable, consider approval-based YAML modification.

**Includes:**

1. Proposal-to-change conversion.
2. Preview and rollback integration.
3. Approval workflow.
4. Conflict/version handling.
5. Regression validation.

**Expected effort:** roughly 2 to 4 additional weeks.

---

## Risks and Mitigations

### Risk: Stale or contested SEAD knowledge

The SEAD identity design has unresolved areas. Knowledge-pack rules may become outdated or reflect contested assumptions.

**Mitigation:**

1. Version the knowledge pack.
2. Include `confidence` and `status` metadata on every rule.
3. Make uncertainty visible in advisor responses.
4. Require review when SEAD identity documents change.

### Risk: Advisor becomes trusted more than validators

Users may over-trust fluent explanations and treat advisor output as authoritative.

**Mitigation:**

1. Every YAML proposal must be validated by existing Shape Shifter validators before display.
2. UI should label advice as advisory, not definitive.
3. Applied changes should always show a diff and validation result.

### Risk: Context leakage to hosted providers

Project data sent to external LLM providers may contain sensitive information.

**Mitigation:**

1. Explicit context whitelist (see Context Assembly section).
2. Secret scanning and redaction before provider calls.
3. Provider-specific privacy modes (local-only option).
4. Logging controls for audit trails.

### Risk: Citations become decorative

If the model can invent citation IDs, citations lose trust value.

**Mitigation:**

1. Backend assembles citation IDs before calling the model.
2. Model may only reference citation IDs provided in the assembled context.
3. Response parser rejects unknown citation IDs.

---

## Success Criteria

The feature should be considered successful when it can reliably do the following:

1. Explain current project issues using real project evidence.
2. Give advice that respects Shape Shifter semantics.
3. Give advice that respects SEAD ecosystem boundaries, including SIMS and the SEAD Authoritative Service.
4. Clearly distinguish confidence from uncertainty.
5. Review, repair, and author project YAML through explicit proposals (Phase 2+).
6. Help users avoid downstream modeling mistakes.
7. Remain safe even when the model is wrong.

---

## Key Recommendation

Build this feature.

But build it as a **grounded SEAD-aware project advisor**, not as a generic chat client.

The highest-value design decision is to make target-system knowledge explicit and curated from the start. Without that, the assistant may be superficially helpful about YAML while still giving poor advice about the actual SEAD domain and the external SEAD services that already shape project behavior.

With that knowledge layer in place, the feature has a realistic path from:

1. explain,
2. to recommend,
3. to propose,
4. and only later to apply.