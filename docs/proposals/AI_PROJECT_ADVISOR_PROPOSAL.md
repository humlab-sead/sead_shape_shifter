# AI Project Advisor Proposal

**Date:** March 15, 2026  
**Status:** Feature proposal  
**Scope:** Project-scoped advisory chat for Shape Shifter with explicit SEAD target-system knowledge

---

## Executive Summary

This proposal describes an **AI Project Advisor** for Shape Shifter.

The feature is not a generic chatbot. It is a grounded advisory workflow that helps users:

1. understand Shape Shifter project YAML,
2. diagnose validation and dependency problems,
3. reason about modeling choices,
4. understand downstream implications for SEAD ingestion and identity handling,
5. receive safe, explainable suggestions before any configuration is changed.

The key requirement is that the advisor must know **both**:

1. the current Shape Shifter project state, and
2. the relevant target-system concepts for SEAD, especially identity, reconciliation, tracked entities, shared metadata, and the boundaries to external SEAD-side services such as SIMS and the SEAD Authoritative Service.

This proposal recommends a phased implementation that starts as a **read-only grounded advisor** and only later grows into **proposal generation** and then carefully controlled **change application**.

---

## Why This Feature Makes Sense

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

This is a good fit for Shape Shifter because the project editor is already the place where users think through modeling, dependencies, reconciliation, and export behavior.

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

---

## Core Design Principle

The advisor must be a **grounded project advisor**, not a free-form general-purpose assistant.

Grounding should come from three distinct knowledge planes:

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

## Verified SEAD Ecosystem Knowledge Requirements

The advisor should treat the following as first-class concepts when generating advice.

### Stable Identity Is Layered Above SEAD Relational IDs

The SEAD identity docs define a separation between:

1. SEAD internal relational identity,
2. stable SEAD UUID identity,
3. provider keys,
4. business keys,
5. authority keys.

This means the advisor must avoid advice that assumes SEAD integer keys are suitable public identities.

### SIMS Owns Identity Allocation, Not Shape Shifter

The SEAD identity docs define a boundary where:

1. SIMS owns identity allocation and long-term identity mapping,
2. Shape Shifter owns normalization, reconciliation inputs, and client-side API behavior.

The advisor must therefore avoid implying that Shape Shifter should itself become the canonical identity authority.

### The SEAD Authoritative Service Already Influences Modeling Through Reconciliation

Shape Shifter already calls a SEAD-facing reconciliation service during reconciliation workflows.

That means the advisor must understand that target-system advice is not limited to export-time ingestion. It is already influenced by an external SEAD service during project design and reconciliation.

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

## What The Advisor Should Do

### Read-Only Advisory Use Cases

The initial feature should support questions such as:

1. explain a validation error in plain language,
2. identify the most likely root cause of a dependency or cycle issue,
3. explain what an entity currently represents in the project,
4. suggest whether a relationship should be modeled as a foreign key, append, fixed lookup, or reconciliation step,
5. explain whether a SEAD concept looks like a tracked entity, shared metadata, or value-like child structure,
6. explain when the SEAD Authoritative Service is the right source of truth for matching rather than SIMS,
7. suggest next debugging steps,
8. summarize project risks before execution.

### Proposal Generation Use Cases

The second stage can generate structured suggestions such as:

1. a proposed foreign key definition,
2. a suggested `keys` or `public_id` configuration,
3. candidate entity decomposition,
4. a recommended reconciliation strategy,
5. a YAML patch proposal with explanation.

### Explicitly Out Of Scope For V1

V1 should not:

1. auto-edit YAML without user approval,
2. invent undocumented SEAD policy,
3. act as the identity authority,
4. make destructive changes,
5. silently persist chat-derived project changes.

---

## Proposed Architecture

### Backend

Add a new backend feature area, for example:

1. `backend/app/models/advisor.py`
2. `backend/app/services/advisor_service.py`
3. `backend/app/services/advisor_context_service.py`
4. `backend/app/services/llm/` for provider abstractions
5. `backend/app/api/v1/endpoints/advisor.py`

The service should follow existing backend layering:

1. API models for request/response,
2. service layer for orchestration,
3. mappers for boundary conversion where needed,
4. no business logic in API DTOs.

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

---

## Context Assembly Strategy

The advisor should not receive the whole world by default.

Instead, build a structured context packet with bounded sections.

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

### SEAD Knowledge Pack

Included as curated guidance rather than raw full-document dumps:

1. identity vocabulary,
2. tracked/shared/value-object distinctions,
3. ownership versus association rules,
4. SIMS boundary rules,
5. SEAD Authoritative Service boundary rules,
6. known cautions and unresolved areas.

### Why A Knowledge Pack Is Better Than Dumping Docs

Raw doc injection will eventually become noisy and contradictory.

The advisor should instead use a curated and versioned SEAD knowledge pack that:

1. extracts stable rules from the SEAD docs,
2. cites the source documents used to derive those rules,
3. can be updated intentionally when SEAD design changes,
4. keeps the prompt compact and auditable.

---

## Recommended Knowledge Sources

### Shape Shifter Sources

Use active docs and live project state, especially:

1. configuration guide,
2. AI validation guide,
3. architecture and developer guides,
4. validation results,
5. dependency graph,
6. preview results,
7. generated `projectSchema.json` and `entitySchema.json` as structural references for fields, enums, and nested shapes.

The generated JSON schemas are useful because they give the advisor a compact, machine-friendly view of the allowed project structure.

They should be used for structural grounding and schema-guided output, not as the final authority.

The backend Pydantic models and validation services remain the source of truth for acceptance.

### SEAD And SIMS Sources

Use curated knowledge derived from:

1. `sead_identity_system/docs/README.md`
2. `sead_identity_system/docs/REQUIREMENTS.md`
3. `sead_identity_system/docs/SYSTEMS_DESIGN.md`
4. `sead_identity_system/docs/ASSESSMENT.md`
5. Shape Shifter reconciliation documentation and code describing the SEAD Authoritative Service integration,
6. selected aggregate-model notes only where they are consistent with the higher-level docs.

### Shape Shifter Reconciliation Sources

Use current Shape Shifter sources to ground how the SEAD Authoritative Service is used today:

1. reconciliation workflow documentation,
2. reconciliation setup guide,
3. reconciliation client and service implementation,
4. entity types and service metadata exposed through the existing reconciliation flow.

### Important Curation Rule

The advisor should not blindly trust every lower-level design note as settled truth.

The SEAD assessment explicitly identifies unresolved modeling issues, especially around:

1. aggregate assumptions,
2. association versus ownership,
3. canonical identity versus provider identity.

That uncertainty should be captured in the knowledge pack as confidence and caveat metadata.

---

## Interaction Model

### Recommended V1 Response Shape

The advisor response should be structured, for example:

1. answer,
2. reasoning summary,
3. project evidence used,
4. SEAD ecosystem rules used,
5. suggested next actions,
6. optional proposed YAML changes.

This makes the system easier to trust and test.

### Citation Model

Responses should cite internal evidence categories such as:

1. selected entity,
2. validation result,
3. dependency edge,
4. SEAD rule,
5. SIMS boundary rule,
6. authoritative-service reconciliation rule.

The UI can render those as chips or references rather than raw prompt text.

---

## Safety And Product Constraints

### V1 Should Be Advisory Only

The simplest safe rule is:

1. the advisor may explain,
2. the advisor may recommend,
3. the advisor may propose patches,
4. the advisor may not directly modify the project.

### Proposal Application Must Reuse Existing Safe Write Paths

If the feature later grows into change proposals, those proposals should feed into existing controlled mechanisms:

1. YAML preview,
2. backup creation,
3. explicit apply confirmation,
4. validation rerun after apply.

### Sensitive Data Handling

The advisor must not indiscriminately send secrets or resolved credentials to a hosted provider.

That implies:

1. redact env-resolved secrets,
2. avoid sending datasource credentials,
3. prefer model input assembled from safe structured summaries,
4. support local-provider deployment for sensitive use cases.

---

## Complexity Assessment

### Phase 1: Read-Only Grounded Advisor

Complexity: medium

Includes:

1. backend endpoint,
2. provider abstraction,
3. project context assembler,
4. SEAD knowledge pack,
5. frontend chat panel,
6. streaming or non-streaming response handling,
7. basic tests.

Expected effort: roughly 1 to 2 focused weeks.

### Phase 2: Structured Proposal Generation

Complexity: medium-high

Includes:

1. schema-guided output using the existing generated JSON schemas as a starting point,
2. YAML patch proposals,
3. richer citations,
4. proposal preview UX,
5. more comprehensive evaluation.

Expected effort: roughly 2 to 4 additional weeks.

### Phase 3: Safe Apply Workflow

Complexity: high

Includes:

1. proposal-to-change conversion,
2. preview and rollback integration,
3. approval workflow,
4. conflict/version handling,
5. regression validation.

Expected effort: roughly 2 to 4 additional weeks.

---

## Recommended Delivery Plan

### Phase 0: Knowledge Foundation

Before building the UI, create a curated advisor knowledge asset containing:

1. stable Shape Shifter modeling rules,
2. stable SEAD/SIMS concepts,
3. stable SEAD Authoritative Service concepts,
4. explicit caveats where the SEAD design is still unsettled.

This is the most important prerequisite for useful advice.

### Phase 1: Project Advisor MVP

Deliver a read-only project-scoped advisor that can:

1. answer questions about the current project,
2. explain validation and dependency issues,
3. give SEAD-aware modeling advice,
4. cite the evidence it used.

### Phase 2: Proposal Mode

Add a mode that returns explicit suggested changes without applying them.

### Phase 3: Approval-Based Apply

Only after V2 is stable, consider approval-based YAML modification.

---

## Success Criteria

The feature should be considered successful when it can reliably do the following:

1. explain current project issues using real project evidence,
2. give advice that respects Shape Shifter semantics,
3. give advice that respects SEAD ecosystem boundaries, including SIMS and the SEAD Authoritative Service,
4. clearly distinguish confidence from uncertainty,
5. help users avoid downstream modeling mistakes,
6. remain safe even when the model is wrong.

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