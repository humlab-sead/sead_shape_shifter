# AI Project Advisor Proposal

**Date:** March 15, 2026  
**Status:** Feature proposal  
**Scope:** Project-level advisory chat for Shape Shifter, with a clear understanding of SEAD as the target system.

---

## Executive Summary

**For** Shape Shifter project authors and data managers **who** need to understand validation errors, model entities for SEAD,
and assess project risks before execution, the **AI Project Advisor** is a grounded, project-scoped chat interface **that**
explains problems using real project state and curated SEAD knowledge. **Unlike** a generic LLM chatbot or raw documentation
search, the Advisor answers from deterministic context — validation results, dependency graphs, and versioned knowledge-pack
rules — and cites its sources.

This proposal describes an **AI Project Advisor** for Shape Shifter.

The advisor is not a generic chatbot. It should help users understand a Shape Shifter project, explain validation and
dependency problems, review modeling choices, and suggest next steps before any project configuration is changed.

The advisor needs two kinds of input:

1. The current Shape Shifter project state.
2. The SEAD concepts that affect project design, especially identity, reconciliation, tracked entities, shared metadata, SIMS, and the SEAD Authoritative Service.

The safest rollout is phased:

1. Start with a read-only advisor that explains existing project issues.
2. Add investigation, so the advisor can read Shape Shifter source and probe the real pipeline to establish whether a reported problem is genuine and what its true scope is.
3. Add structured proposal generation after the explanation and investigation workflows are reliable.
4. Add approval-based change application only after proposals can be validated and reviewed.

---

## Problem Statement

Users and AI coding agents working on complex projects currently need to connect several pieces of information to give correct and safe advice:

1. Project configuration rules and valid YAML patterns.
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
6. An AI coding agent may hallucinate SEAD rules or invent YAML patterns it was not given, because it has no grounded project context.
7. A reported error may be wrong. Validators can report false positives when their assumptions do not match a supported configuration, and no current surface establishes that.
8. A reported error may understate the problem. A check reports what its own comparison observed, which can be a small part of a wider defect in the data.

There is no way to connect these signals without expertise in all seven domains simultaneously.

### Available context

Shape Shifter already has much of the structured context needed to answer these questions:

1. Project YAML loading and saving.
2. API-to-Core conversion, including directive resolution.
3. Structural validation.
4. Data validation.
5. Dependency graph analysis.
6. Preview and materialization services.
7. Reconciliation workflows.
8. Suggestion and auto-fix patterns.
9. Project-level session handling.

Two inputs are missing from that list. The framework source is not available, so nothing can explain which check produced a message or whether that check is correct. The ability to run the pipeline and inspect its stages is not available either, so nothing can report what actually happened to the data or how far a reported problem extends. Both are needed to move from restating a report to resolving it.

That context exists but is not synthesized automatically. Users have no direct answers to the questions that matter most for project quality:

1. "Why is this entity failing validation?"
2. "Should this be a fixed entity or a sourced entity?"
3. "How should I model this relationship so it can be ingested into SEAD cleanly?"
4. "Is this a tracked entity, shared metadata, or a child value?"
5. "What would SIMS expect for identity allocation here?"

---

## Stakeholders and Users

### Primary users

| Role | Needs | Environment |
|------|-------|-------------|
| **Data manager** | Validate project YAML, explain errors in domain terms, assess whether entities will ingest cleanly into SEAD, understand reconciliation requirements | Shape Shifter frontend (project editor), sometimes the CLI |
| **Project configurator** | Model entities correctly, choose between fixed/sql/merged entity types, set up foreign keys that match SEAD expectations, avoid identity and reconciliation mistakes | Shape Shifter frontend, editing `shapeshifter.yml` |
| **AI coding agent** | Grounded project context to avoid hallucinating YAML patterns or SEAD rules, deterministic validation results to cite | Programmatic access through backend API |

### Secondary stakeholders

| Role | Interest |
|------|----------|
| **SEAD system maintainer** | Projects that conform to the target model and produce clean imports |
| **Researcher (data provider)** | Clear explanations when their submission fails validation or requires re-modeling |
| **Shape Shifter maintainer** | Reduced support burden from configuration questions that the Advisor can answer directly |

### Key user needs

1. "Why did this fail?" — plain-language explanations of validation errors, not raw error codes.
2. "Is this the right entity type?" — guidance on fixed vs. sql vs. merged for a given modeling situation.
3. "Will this work for SEAD?" — conformance checks against the active target model.
4. "What am I missing?" — project-level risk summary before running a full import.
5. "Don't invent answers." — explicit uncertainty when the Advisor lacks enough context.

---

## Product Principles

### Principle 1: Grounded, not generative

The advisor must be a **grounded project advisor**, not a free-form assistant.

"Grounded" means the advisor answers from known project data and curated rules. It should not invent project state, YAML fields, or SEAD policy.

### Principle 2: Explicit uncertainty over confident invention

When the advisor lacks sufficient grounded context to answer a question, it should say so. It should not produce a fluent but invented answer. Refusal and uncertainty are correct behaviors, not failures.

### Principle 3: Deterministic code owns all factual claims

The model explains what the deterministic layer found. It does not decide what is valid, invent rules, or apply changes. Every factual claim in an advisor response must be traceable to a citation ID that the advisor produced, either assembled before the model was called or derived during investigation and recorded as an evidence artifact.

Facts may be derived on demand as well as pre-computed. What this principle forbids is unchanged: the model may not assert a fact it cannot cite, and it may not present its own inference as a deterministic result.

### Principle 4: Reported state is verified before it is explained

A validation message is one check's observation, not a verdict. Before explaining a reported problem as a defect in the project, the advisor should establish that the check is correct and that the reported scope is complete. Where it cannot, it must say the report is unverified rather than restate it as fact.

### Required inputs

The advisor needs four kinds of grounded input to apply these principles.

#### 1. Project Context

This comes from the active project and current editor or runtime state:

1. Raw YAML.
2. Resolved Core project.
3. Selected entity YAML.
4. Structural validation results.
5. Data validation results.
6. Dependency graph and cycle details.
7. Preview and materialization summaries.
8. Task and note context when relevant.

#### 2. Shape Shifter Domain Knowledge

This is curated knowledge from active Shape Shifter documentation and rules:

1. YAML configuration rules.
2. Three-tier identity conventions.
3. Dependency and foreign-key modeling patterns.
4. Directive behavior.
5. Validation rules.
6. Reconciliation workflow expectations.
7. How Shape Shifter applies target-model conformance validation, including what is checked and what error shapes are produced.

#### 3. Target Model Conformance Knowledge

This is curated, versioned knowledge from the target-model guides and the active target-model specification:

1. Target-model structure and semantics.
2. Conformance validation expectations.
3. Required entities, columns, and foreign-key relationships for the active target system.
4. Naming and identity requirements expressed by the target model.
5. The bundled SEAD superset model as a concrete reference example.

#### 4. SEAD Target-System Knowledge

This is curated, versioned knowledge about SEAD and the related services around it:

1. Tracked entities versus shared metadata.
2. Identity terminology and responsibilities.
3. Ownership versus association.
4. Reconciliation expectations.
5. Provider identity versus official SEAD identity.
6. SIMS responsibilities versus Shape Shifter responsibilities.
7. SEAD Authoritative Service responsibilities versus Shape Shifter responsibilities.
8. How reconciliation, authority lookup, and identity allocation fit together.

#### 5. Framework Source and Executable Evidence

This input is the ability to read Shape Shifter source and to probe the pipeline against the active project:

1. Shape Shifter source for the checks, transforms, loaders, and registries the project exercises.
2. The registry contents that determine which checks, filters, and loaders run for an entity.
3. Read-only access to the real pipeline, so an entity can be loaded and normalized and its stages inspected.
4. Captured artifacts from those runs, such as column lists, dtypes, row counts, null counts, and distinct values.

This input differs in kind from the first four. Those are curated text, assembled into the prompt. This one is derived: the advisor retrieves source and produces evidence while it works, and both become citations. [Investigation Capability](#investigation-capability) defines how that works and what bounds it.

The target-model and SEAD inputs are both essential. The advisor should answer not only "how do I write this YAML?" but also "does this conform to the target model?" and "is this a good SEAD model?"

---

## Investigation Capability

The advisor's value comes from deriving facts, not only from restating them. The project context and the curated inputs describe what is known. Investigation determines what is true.

### Why narration alone is insufficient

A validation message is one check's observation. Explaining it correctly often requires answering questions the message cannot:

1. **Is the check correct?** Validators can report false positives when their assumptions do not match a supported configuration.
2. **Is the reported scope complete?** A check reports the values its own comparison observed, which can be a small part of a wider defect.
3. **What actually happened to the data?** The message describes the configured rule, not the resulting columns, rows, and types.
4. **Which cause applies?** A message names a symptom, and the causes may sit in different framework stages.

Two patterns from real project work show the difference.

**A false positive.** A check reported that a derived column created by `extra_columns` conflicted with an existing result column. The same column was also listed in `unnest.id_vars`, and the conflict set was built with a helper that includes `id_vars`, so a valid configuration looked invalid. `id_vars` are passthrough inputs that must already exist before unnesting, not outputs. Confirming this required locating the check in source, identifying which column set it built, and running it against a minimal configuration.

**Understated severity.** A foreign key check reported one orphaned value. Investigation showed the entity copied a business code into a foreign key column that was joined against a sequential identity. Eleven distinct values fell inside the identity range and passed validation while resolving to the wrong rows, and only the twelfth fell outside it and was reported. The single low-priority warning was the visible part of a mapping defect that silently mis-assigned most of the entity's rows.

In both cases the useful answer was not "here is what the message means". It was "this message is wrong" or "this message is the smallest part of the problem". Neither conclusion is reachable from the message.

### Capability tiers

| Tier | Capability | New risk | Answers |
|------|------------|----------|---------|
| 1 | Source retrieval | Low | Which code produced this message, and what does it check? |
| 2 | Pipeline probing | Low | What actually happened to the data, and how far does it extend? |
| 3 | Experiment execution | High | Is the check correct, and what is the smallest reproduction? |

Tiers 1 and 2 use existing deterministic services and add no new execution surface. Tier 2 invokes the same loaders, transforms, and validators the application already runs, with parameters. Tier 3 runs generated code and requires a sandbox.

### The investigation loop

Investigation is a loop over the active project, not a single retrieval:

1. **Retrieve.** Find the source that produced the report: the check that raised it, the transform that shaped the data, or the loader that read it.
2. **Hypothesize.** State a specific claim about the cause.
3. **Discriminate.** Design the smallest experiment that separates that claim from its alternatives. Varying one configuration value at a time is usually decisive.
4. **Observe.** Run the project or check in a read-only environment and capture the result.
5. **Record.** Persist the experiment, its inputs, and its output as an evidence artifact.

Every step produces something citable. Retrieval produces a source location; discrimination produces an artifact. The conclusion is then a claim about those citations, not a claim about the model's reasoning.

### Investigation tools

A fixed tool set, not general autonomy.

| Tool | Purpose |
|------|---------|
| Source search and read | Locate the code path behind a message, validation result, or column |
| Registry inspection | Determine which checks, loaders, and filters are registered and run |
| Project load and normalize | Execute the real pipeline against the active project, read-only |
| Stage inspection | Report intermediate state: columns, dtypes, row counts, null counts, distinct values, key uniqueness |
| Differential run | Execute the pipeline with one configuration value changed |
| Cross-entity scan | Apply a check to every entity to test whether a finding is isolated or systemic |
| Reference comparison | Compare produced values against an authoritative source, such as a lookup table or the target model |

### Evidence artifacts

| Field | Description |
|-------|-------------|
| `id` | Stable identifier used in citations |
| `kind` | `source_location`, `pipeline_state`, `differential_result`, `scan_result`, `reference_comparison` |
| `source_refs` | Source files and lines the experiment exercised |
| `inputs` | The project, entity, settings, and any snippet used |
| `output` | The captured result, such as tables, counts, and value lists |
| `conclusion` | The claim the artifact supports or refutes |
| `limitations` | What the experiment did not establish |

`limitations` carries as much weight as `conclusion`. A finding may hold only for the current data snapshot, or only for the entities that were scanned.

### Constraints

1. **No writes.** No project file writes, no database writes, no changes to backend caches or session state.
2. **Read-only data access.** Database access uses a read-only role, as the existing project tooling does.
3. **Isolation.** Tier 3 experiments run in a sandbox with no network access and bounded time and memory.
4. **Reproducibility.** Every artifact records the inputs needed to repeat it.
5. **Explicit failure.** An inconclusive or failed experiment is reported as such, not omitted.

### Negative results are first-class

Much of the value is in refutation: showing that a report is a false positive, that a proposed check would produce more false positives than true ones, or that a failure already existed before a change. The advisor must be able to state "I tested this and it is not the cause" with the same standing as a confirmed defect, and the evaluation suite must test for it.

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

This means target-system advice is not only about final export. External SEAD service behavior already affects project design and reconciliation.

The advisor should be able to explain:

1. Which fields and entity types are reconciled against the authoritative service.
2. When a modeling choice improves or weakens reconciliation quality.
3. How reconciliation data differs from identity allocation.
4. Where authority lookup ends and SIMS-style identity allocation begins.

### The Target Model Is a Conformance Source

The target model is not only supporting documentation. It is the concrete conformance specification for what the project must expose
for the target system.

The advisor should be able to use the active target model to explain:

1. Which entities are required.
2. Which columns and foreign-key relationships are required.
3. Which naming rules and `public_id` expectations apply.
4. Whether a project issue is a Shape Shifter validation problem, a conformance problem, or both.
5. How the bundled SEAD superset model illustrates expected SEAD-oriented structure.

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

## MVP Use Cases

The MVP should answer only three kinds of questions:

| Priority | Use case | Description |
|----------|----------|-------------|
| **P1** | Explain this validation error | Take a validation message and explain what it means, why it happened, and how the user can fix it. |
| **P2** | Explain this entity and its risks | Take a selected entity and summarize its configuration, dependencies, and possible modeling problems. |
| **P3** | Review project risks before execution | Summarize project-level risks, dependency issues, and validation state before the user runs a project. |

These use cases are narrow enough to test well and broad enough to be useful. Open-ended modeling advice should wait until the
knowledge pack and evaluation suite are in place.

P1 and P3 are also where verification matters most. An error explanation is only as good as the report it explains, and a risk review
is only as good as the checks it summarizes. [Investigation Capability](#investigation-capability) is what raises both above restating
existing output.

Typical MVP prompts:

1. "Explain why this project YAML fails validation."
2. "What risks does this entity have before I run the project?"
3. "Review this `shapeshifter.yml` and explain problems."

---

## Explicit Non-Goals

MVP should not:

1. Edit YAML automatically without user approval.
2. Invent undocumented SEAD policy.
3. Act as the identity authority.
4. Make destructive changes.
5. Save chat-derived project changes silently.
6. Provide broad open-ended modeling advice beyond the three MVP use cases.
7. Read framework source, probe the pipeline, or execute code. Investigation is a later phase, and it never extends to modifying the repository or the running service.

Future phases may add:

1. Investigation, so the advisor can read framework source and probe the pipeline against the active project.
2. Structured proposal generation, such as YAML patches with explanations.
3. Data-to-configuration help, such as source-file exploration and draft YAML.
4. An approval-based apply workflow.

These are out of scope for the first delivery. The advisor is not a general code-execution service or an IDE agent. Investigation is bounded to answering questions about the active project.

---

## Architecture

### Backend

Add a new backend feature area:

1. `backend/app/models/advisor.py` — Request and response Pydantic models, including evidence artifacts and citations.
2. `backend/app/services/advisor_service.py` — Receives the question, assembles context, calls the provider, parses the response,
   and returns a structured result.
3. `backend/app/services/advisor_context_service.py` — Builds deterministic context from project state, validation results,
   dependency summaries, knowledge-pack rules, and citation IDs.
4. `backend/app/services/advisor_investigation_service.py` — Runs the investigation loop, selects tools, and records evidence artifacts.
5. `backend/app/services/advisor_source_service.py` — Retrieves framework source locations for checks, transforms, and loaders.
6. `backend/app/services/advisor_sandbox.py` — Executes tier 3 experiments under isolation and returns captured output.
7. `backend/app/services/llm/` — Provider interfaces and implementations, such as local Ollama and hosted providers.
8. `backend/app/api/v1/endpoints/advisor.py` — Route handler for advisor requests.

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
- source retrieval and ranking
- sandbox execution, including isolation, limits, and output capture
- evidence artifact construction
- patch validation when proposal mode is added

**The model should handle:**

- plain-language explanations
- issue prioritization
- user-facing reasoning summaries
- suggested next actions
- choosing which source to read and which experiment to run
- interpreting captured artifacts
- draft proposals in future phases

**The model should not be trusted to:**

- decide whether YAML is valid without validator confirmation
- invent SEAD rules
- apply changes directly
- infer secrets
- override validation results
- reference citation IDs that were not provided in the assembled context or produced as evidence
- execute code outside the sandbox, or select tools outside the fixed investigation set
- present an unrepeated or unscanned experiment as evidence about the whole project

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
- source locations and evidence artifact summaries

**Execution rules:**

Investigation gives the advisor new ways to reach project data, so redaction covers it too.

1. Executed experiments run in a sandbox with no network access.
2. Artifacts may contain project data. An artifact sent to a hosted provider follows the same redaction rules as any other context.
3. Local-provider-only mode also restricts execution to the local host.
4. Artifacts are retained with the session so a user can see exactly what was read and produced.
5. Source retrieval reads framework code only. It does not read the user's data sources.

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
5. `docs/rules/semantic_rules.yml` — machine-readable semantic validation rules with rule IDs, severity, fix suggestions, and agent guidance. Primary source for validation-error explanation and citation ID generation.
6. `.github/skills/shapeshifter-configuration/SKILL.md` — curated YAML authoring rules, entity type selection guidance, and common configuration antipatterns. Use as a knowledge pack source for entity modeling advice; not a runtime integration point.
7. `.github/instructions/shapeshifter-configuration.instructions.md` — compact YAML validation rules covering entity types, identity, foreign keys, dependencies, directives, and high-risk false positives. The skill loads this instruction file; both should be treated as a single curated rule source.

**Target model and conformance sources:**

1. `docs/TARGET_MODEL_GUIDE.md`
2. `docs/TARGET_MODEL_SCHEMA_REFERENCE.md`
3. `resources/target_models/sead_standard_model.yml`
4. The active target-model file referenced by `metadata.target_model` in the project being reviewed

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
4. Summary of conformance state when a target model is present.
5. Dependency summary.
6. Concise project metadata.
7. Active target-model metadata and conformance summary, when present.
8. Structural schema metadata from the generated project and entity JSON schemas.

### Entity Context

Include this when the question is about a specific entity:

1. Selected entity YAML.
2. Resolved entity configuration.
3. Relevant validation messages.
4. Relevant conformance messages, when present.
5. Neighboring dependencies.
6. Preview summary, if available.

### Knowledge Pack Rules

Include curated rules instead of raw document dumps. Select only the rules that match the current question, using `applies_to`
tags and the active entity types.

### Why a Knowledge Pack Is Better Than Dumping Docs

Raw document injection will become noisy and may include conflicting notes. A knowledge pack is better because it:

1. Extracts stable rules from the SEAD docs and target-model sources.
2. Cites the source documents used to create those rules.
3. Can be updated intentionally when SEAD design changes.
4. Keeps the prompt compact and easier to audit.
5. Lets the advisor distinguish between broad SEAD guidance and active target-model conformance requirements.

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
| `source.code`         | `source.code.src.specifications.entity.extra_columns`  |
| `evidence.artifact`   | `evidence.artifact.ev-0007`                            |
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

1. The backend assembles the citation IDs available before calling the model, and adds the IDs of evidence artifacts produced during investigation.
2. The model may only reference citation IDs that appear in that set.
3. The response parser rejects or flags citation IDs that are not in the allowed set.
4. Citations are persisted with the chat session so users can review them later.
5. The UI renders citations as clickable chips that navigate to the relevant entity, validation message, code location, or knowledge-pack rule.

A vague citation like "SEAD rule" is not enough. A useful citation should point to a specific rule ID, validation message, YAML path, source location, or recorded experiment.

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
| False-positive detection                   | Does the advisor identify a validator false positive instead of paraphrasing it?  |
| Severity and scope discovery               | Does the advisor find that a reported problem affects more than it reported?      |
| Discriminating experiment                  | Does the advisor design a run that separates the candidate causes?                |
| Negative result reporting                  | Can the advisor state that a candidate cause was tested and ruled out?            |
| Pre-existing versus introduced failure     | Does the advisor check whether a failure predates a change before attributing it? |
| YAML patch proposal                        | Phase 2: Are proposed patches valid and minimal?                                  |
| Refusal and uncertainty                    | Does the advisor say "I don't know" instead of inventing rules?                   |
| Hallucination                              | Does the advisor avoid inventing SEAD rules or YAML fields?                       |
| Redaction                                  | Are secrets excluded from context sent to hosted providers?                       |
| Sandbox isolation                          | Does execution avoid writes, network access, and unbounded resource use?          |
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

Investigation scenarios additionally require evidence:

```yaml
scenario: reported_conflict_is_a_false_positive
input:
  project_yaml: |
    entities:
      reading_property:
        type: entity
        extra_columns:
          property_group: ReadingProperty
        unnest:
          id_vars: [property_group, reading_id]
          value_vars: [reading_value]
          var_name: property_type
          value_name: property_value
  validation_messages:
    - "extra_columns 'property_group' conflicts with an existing result column"
question: Is this error correct, and how do I fix it?
expected:
  must_mention:
    - id_vars are inputs that survive unnest, not outputs
    - the report is a false positive
  must_not_claim:
    - the configuration must be renamed
  required_evidence:
    - kind: source_location
    - kind: differential_result
  limitations_must_include:
    - the finding applies to the current validator version
```

### Evaluation Gates

1. Phase 1a, the backend API, must pass all scenario tests before Phase 1b, the frontend, begins.
2. Phase 2, proposal generation, must pass YAML patch validation tests before user-facing proposal mode is enabled.
3. Investigation must pass false-positive, scope, and sandbox-isolation scenarios before tier 3 execution is enabled.
4. Each phase should add regression scenarios that cover previous phases.

---

Delivery sequencing is documented in
[SHAPESHIFTER_PROJECT_AI_ADVISOR_PHASE_PLAN.md](./SHAPESHIFTER_PROJECT_AI_ADVISOR_PHASE_PLAN.md).

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

### Risk: Code Execution

Running generated code against a real project adds a failure and security surface: unintended writes, data access, unbounded resource use, and side effects on shared state.

**Mitigation:**

1. Use a closed tool set. All execution goes through the investigation tools, each with a defined input and output shape.
2. Run experiments in a sandbox with no network access and bounded time and memory.
3. Keep execution read-only. No project file writes, no database writes, and no mutation of backend caches or session state.
4. Use a read-only database role, as the existing project tooling does.
5. Record every experiment and its output so behavior can be audited and reproduced.
6. Gate tier 3 execution behind sandbox-isolation scenarios before it is enabled.

### Risk: Experiments Overstate Their Scope

An experiment runs against one project and one data snapshot. A finding may not generalize, and a confident conclusion drawn from a narrow run can mislead as much as an invented one.

**Mitigation:**

1. Require every evidence artifact to record its `limitations`.
2. Require a cross-entity scan before a finding is presented as systemic rather than isolated.
3. Distinguish a value established for one entity from a value established for the project.

---

## Success Criteria

The feature should be considered successful when it can reliably:

1. Explain current project issues using real project data.
2. Give advice that follows Shape Shifter rules.
3. Give advice that respects SEAD service responsibilities, including SIMS and the SEAD Authoritative Service.
4. Clearly distinguish confidence from uncertainty.
5. Review, repair, and author project YAML through explicit proposals in Phase 2 and later.
6. Help users avoid target modeling mistakes.
7. Determine whether a reported problem is real, and how far it extends, before advising on it.
8. Remain safe even when the model is wrong.

---

## Glossary

General Shape Shifter and SEAD terms are defined in [docs/GLOSSARY.md](../../GLOSSARY.md). This glossary defines only terms specific to the AI Project Advisor feature.

| Term | Definition |
|------|------------|
| **Advisor** | The AI Project Advisor feature. A grounded, project-scoped chat interface that explains validation errors, entity risks, and modeling choices using real project data and curated SEAD knowledge. |
| **Citation** | A structured reference embedded in an advisor response. Points to a specific validation message, YAML path, dependency edge, source location, recorded experiment, or knowledge-pack rule. Uses a stable ID format: `<category>.<scope>.<identifier>`. |
| **Context assembly** | The process of building a structured, redacted packet of project data, validation results, dependency summaries, and knowledge-pack rules. This packet is sent to the LLM provider as the basis for an advisor response. |
| **Grounded advisor** | An advisor that answers from known project data and curated rules. It does not invent project state, YAML fields, or SEAD policy. |
| **Evidence artifact** | A record of one executed experiment: what was run, what it produced, the claim it supports or refutes, and its limitations. Identified by `evidence.artifact.<id>` and citable like any other source. |
| **Investigation** | Deriving facts about the active project by reading framework source and probing the real pipeline, rather than only restating pre-computed validation output. See [Investigation Capability](#investigation-capability). |
| **Knowledge pack** | A curated, versioned collection of structured rules about SEAD, SIMS, reconciliation, and target-model conformance. Each rule has an ID, confidence level, source documents, and scope tags. |
| **Pipeline probe** | A read-only execution of the real pipeline, or one stage of it, used to observe columns, dtypes, row counts, and key values. Tier 2: no generated code involved. |
| **Provider abstraction** | A backend interface that supports multiple LLM providers (local Ollama, hosted providers) without hardwiring one vendor into the advisor feature logic. |
| **Sandbox** | The isolated environment for tier 3 experiments, with no network access and bounded time and memory. |
| **Source retrieval** | Locating the framework code behind a message, validation result, or column, so the check that produced it can be read. Tier 1. |

---

## Key Recommendation

Build this feature.

Build it as a **grounded SEAD-aware project advisor**, not as a generic chat client.

The most important design choice is to make target-system knowledge explicit and curated from the start. Without that, the advisor may
explain YAML well while still giving poor advice about the SEAD domain and the external SEAD services that already affect project
behavior.

The next is to let the advisor investigate. An advisor that only explains validation output restates what the user already has,
including any false positive and any understated severity. Reading the source behind a report and probing the real pipeline is what
turns "here is your error" into "here is whether the error is right and what it actually affects".

With both layers in place, the feature has a realistic path:

1. Explain.
2. Investigate.
3. Recommend.
4. Propose.
5. Apply only after approval.
