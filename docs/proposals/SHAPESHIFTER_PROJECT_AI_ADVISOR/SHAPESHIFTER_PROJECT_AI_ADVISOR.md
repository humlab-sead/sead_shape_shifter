# AI Project Advisor

**Date:** March 15, 2026
**Revised:** October 22, 2026
**Status:** Feature proposal
**Scope:** Project-level advisory chat for Shape Shifter, with SEAD as the target system.

This revision separates review scope from evidence access. It defines how each finding is supported and what the Advisor may store, tightens privacy and execution limits, and moves the explanation MVP ahead of investigation tools. The `review-shapeshifter-configuration` skill provides comparison runs, but its answers alone do not prove correctness; maintainer-reviewed fixtures set the expected results. The earlier phase plan and readiness assessment are archived in [archived/](./archived/) and should be rewritten from this proposal.

---

## Summary

The **AI Project Advisor** helps Shape Shifter project authors and data managers understand validation errors, model entities and relationships for SEAD, and assess project risks before execution. It uses current project data and curated SEAD knowledge to explain problems and investigate whether evidence supports a reported problem. Unlike a generic chatbot, it grounds its answers in validation results, dependency graphs, provider bindings, and versioned knowledge-pack rules, and cites those sources.

The [`review-shapeshifter-configuration` skill](../../../.agents/skills/review-shapeshifter-configuration/SKILL.md) shows a useful review workflow. A coding agent can inspect the repository, run validation scripts, and ask a maintainer to resolve ambiguity. Use this workflow to identify Advisor capabilities and build comparison scenarios. Treat skill runs as supporting evidence; maintainer-reviewed fixtures define the expected results.

First define how the Advisor will ground its answers and how those answers will be evaluated. Then build a small evaluation runner and run a time-boxed framework spike. Deliver the explanation MVP and evaluate it with users before adding limited investigation tools and the external MCP adapter. Add generated experiments, proposal generation, and apply only after each passes its safety and evaluation gates.

---

## Problem

Users and AI coding agents working on complex projects currently need to connect several pieces of information to give correct and safe advice:

1. Project configuration rules and valid YAML patterns.
2. Current validation and dependency results.
3. The structure and quality of the source data.
4. Reconciliation requirements.
5. SEAD target-system requirements.
6. SIMS identity rules.
7. External service behavior already used by Shape Shifter, especially the SEAD Authoritative Service used for reconciliation.
8. Deployment state that changes the meaning of a project: provider-registry bindings, materialized entity state, and mapping-sidecar links.

This creates common problems:

1. A YAML change can be valid for Shape Shifter but still be a poor fit for SEAD.
2. Users may mix up tracked entities, shared metadata, and child values.
3. Users may not know whether a foreign key represents ownership or association.
4. A modeling choice may create identity or reconciliation problems later.
5. The editor can report errors, but it does not always explain them in domain terms.
6. An AI coding agent may hallucinate SEAD rules or invent YAML patterns it was not given, because it has no grounded project context.
7. A reported error may be wrong. Validators can report false positives when their assumptions do not match a supported configuration, and the application currently offers no way to check that.
8. A reported error may understate the problem. A check reports what its own comparison observed, which can be a small part of a wider defect in the data.
9. Advice produced in the development environment — by a maintainer or a coding agent running the configuration skill — cannot be reproduced or continued inside the product, and vice versa. The two settings answer the same question with different data.

Users currently need expertise across all these areas to connect the information and give sound advice.

### Available context

Shape Shifter already provides much of the needed context. It can load and save project YAML, convert API models to Core models (including directive resolution), validate projects and data, analyze dependencies, preview and materialize projects, run reconciliation, suggest fixes, and manage project-level sessions.

The current application does not provide two inputs. It cannot inspect framework source, so it cannot explain which check produced a message or whether the check is correct. It also cannot run the pipeline and inspect its stages. Without those results, it cannot show what happened to the data or how far a reported problem extends. Both inputs are needed to move from restating a report to investigating it.

Users have no direct answers to the questions that matter most for project quality:

1. "Why is this entity failing validation?"
2. "Should this be a fixed entity or a sourced entity?"
3. "How should I model this relationship so it can be ingested into SEAD cleanly?"
4. "Is this a tracked entity, shared metadata, or a child value?"
5. "What would SIMS expect for identity allocation here?"
6. "Is this validator complaint actually correct?"

---

## Scope

In scope:

1. A project-scoped advisory chat in the Shape Shifter frontend and backend API.
2. A capability model that defines what the Advisor can review and what the MVP includes (see [Capability Model](#capability-model)).
3. Deterministic context assembly, citation control, redaction, and a curated knowledge pack.
4. A clarification step: the Advisor may ask one focused follow-up question to get missing information instead of refusing or guessing.
5. Server-side investigation services. The embedded Advisor calls them in-process through Pydantic AI function tools; authorized development-environment agents can call them through an MCP (Model Context Protocol) adapter.
6. Evaluation of the Advisor against the `review-shapeshifter-configuration` skill workflow on shared scenarios.
7. A handoff process: each investigation artifact carries reproduction details, input versions, and whether exact replay is possible, and can be exported for a development-environment session.

Out of scope (non-goals):

1. Editing YAML automatically without user approval.
2. Inventing undocumented SEAD policy.
3. Acting as the identity authority.
4. Making destructive changes.
5. Saving chat-derived project changes silently.
6. General-purpose code execution or IDE-agent behavior. Investigation is limited to answering questions about the active project.
7. Replacing the development-environment skill workflow. The Advisor and the skill share tools and scenarios; they do not replace each other.

---

## Current Behavior

### The skill workflow is the working reference

The [`review-shapeshifter-configuration` skill](../../../.agents/skills/review-shapeshifter-configuration/SKILL.md) defines the current review workflow:

1. Read the raw YAML and preserve directives.
2. Trace each entity through the pipeline stages.
3. Check the `data_provider_code`/`provider_schema` pair against the deployment's curated provider registry.
4. Inspect materialized `source_state` and mapping-sidecar links.
5. Run `scripts/validate_project.py` with the structural, data, and conformance workflows.
6. Report findings with the commands used and the limits of each check.

The skill can use the full codebase and both sibling repositories, a Python runtime, git history, and validation scripts. It can also ask a maintainer to resolve ambiguity. The current application does not provide all of these resources. The Advisor should bring as much of this capability into Shape Shifter as safety and privacy allow, and provide a clear handoff for the rest.

### What the application provides today

The following is the proposal’s current inventory. Confirm each capability, version, and access path during phase planning.

1. Editor-side validation messages without domain-level explanation.
2. Validation workflows (structural, data, conformance) reachable through `scripts/validate_project.py` and the backend validation service.
3. Provider-binding services (`backend/app/services/project_provider_binding_service.py`) that the editor enforces but never explains.
4. Materialized entities that keep their original configuration in `materialized.source_state`, and a mapping sidecar that can supply public-ID links not visible in raw YAML. Core structural validation does not use those links.
5. The UI and API do not provide access to framework source, pipeline execution, git history, or prior validation results.

---

## Capability Model

The Advisor uses two separate axes. **Scope** says which part of a project it reviews; **goal** says what the user asks it to do. Evidence capabilities list the sources a result can use. They do not add more scopes. For example, deployment state may be available even when source-code access and pipeline execution are not.

### Scope axis

| Scope | What the Advisor reviews |
|-------|--------------------------|
| `S1 entity` | One selected entity and its relevant project relationships |
| `S2 project` | The full project and cross-entity relationships |

### Evidence capabilities

| Capability | Available information |
|------------|-----------------------|
| `E1 project snapshot` | Editor or saved YAML, resolved configuration when available, validation results, dependencies, target-model reference, and selected preview summaries |
| `E2 deployment state` | Authorized provider binding, materialized `source_state`, mapping-sidecar links, and available validation snapshots |
| `E3 framework source` | The checks, transforms, loaders, and registries that produced a result |
| `E4 pipeline probe` | Read-only results from approved loaders and transforms, with bounded row, column, value, and output summaries |
| `E5 controlled experiment` | A differential run or reproduction using an isolated execution mechanism and explicitly supplied inputs |
| `E6 history` | Earlier validation or configuration snapshots, when retained and authorized |

The MVP uses `E1` and, where authorized, `E2`. Later goals declare the evidence they require. Missing evidence narrows the claim and its scope; it does not prevent the Advisor from giving a limited explanation.

### Goal axis

| Goal | Behavior | Example prompt |
|------|----------|----------------|
| `G1 explain` | Plain-language explanation of a message, entity, or dependency | "Why is this entity failing validation?" |
| `G2 verify` | Investigate whether evidence supports or contradicts a report and what scope it demonstrates | "Is this error actually right?" |
| `G3 review` | Find issues across the whole target, not only the reported ones | "Find errors in this project before I run it." |
| `G4 recommend` | Suggest next steps using the target model, conformance results, and project state | "What should I fix or configure next?" |
| `G5 propose` | Return structured, validator-checked YAML changes without applying them | "Fix the FK mapping on this entity." |
| `G6 apply` | Apply an approved proposal with diff, validation, and recovery | "Apply that change." |

### The grid

| | G1 explain | G2 verify | G3 review | G4 recommend | G5 propose | G6 apply |
|---|---|---|---|---|---|---|
| S1 entity | **MVP** | post-MVP | post-MVP | **MVP** | post-MVP | later |
| S2 project | **MVP** | post-MVP | post-MVP | **MVP** | post-MVP | later |

The MVP covers `S1` and `S2` with goals `G1` and `G4`, using `E1` and authorized `E2` context. Entity-level review (`S1` × `G3`) comes later and checks one entity and its direct relationships. Project-level review (`S2` × `G3`) checks issues across entities. Every result must state its scope and the evidence it used.

Verification (`G2`) and review (`G3`) come after the explanation MVP. Each check must name the evidence it needs. For example, validator analysis may need `E3` source code, while a claim about data behavior may need `E4` pipeline results. Proposal (`G5`) and apply (`G6`) come later. Apply is allowed only for an approved proposal based on current evidence, passing validation, and an available recovery path. Current, relevant pipeline results may support a change.

Use the skill workflow to build comparison scenarios for each claimed scope, goal, and evidence combination. Maintainer-reviewed findings and evidence requirements determine correctness. A matching skill conclusion alone is not proof.

---

## Product Principles

### Principle 1: Grounded, not generative

The Advisor answers from known project data and curated rules. It does not invent project state, YAML fields, or SEAD policy.

### Principle 2: Clarify before refusing, refuse before inventing

When context is missing, the Advisor should first ask one focused question that names what is missing. This follows the skill workflow when a file or intent is unclear. Refuse only when no question could supply the missing information. Never guess or invent an answer.

### Principle 3: Separate observations, rules, hypotheses, and conclusions

Deterministic tools report observations, such as validation results, row counts, and configuration values. Curated sources state rules and explain when they apply. The model may suggest hypotheses and interpret cited information, but it must label hypotheses and must not present them as verified conclusions. A citation ID shows that a source was supplied; it does not show that the source supports the claim. Check claim support through maintainer review and evaluation scenarios.

### Principle 4: Preserve reports and qualify each claim

Keep the validator's original result unchanged. With supporting evidence, the Advisor may separately say that a report appears incorrect or that its scope is incomplete. Each finding must include its own support status and scope. One answer may therefore include a measured count, an unchecked validator report, and a tentative explanation. The Advisor can explain what is known without verifying the entire project.

### Principle 5: Application services own tools, adapters expose them

Ordinary Shape Shifter backend services own investigation behavior, project authorization, provider disclosure filtering, resource limits, and evidence-artifact creation. Pydantic AI function tools and the MCP server are thin adapters to those services. The embedded Advisor calls the functions directly; it does not call itself over MCP. External development tools use the MCP adapter. This gives both entry points the same application rules without making MCP part of the embedded call path.

---

## Grounded Context

The Advisor needs five kinds of project and system information to base its answers on evidence.

### 1. Project Context

Project context comes from the active project and current editor or runtime state. It includes raw YAML, the resolved Core project, selected entity YAML, structural and data validation results, dependency graphs and cycle details, preview and materialization summaries, and relevant task or note context.

### 2. Deployment Context

Deployment state can change what a project configuration means. The skill workflow checks:

1. The `data_provider_code`/`provider_schema` pair and its binding in the deployment's curated provider registry. A normal save cannot change the pair or change the resolved ordered Business Keys for an already-bound project. Advice must account for that rule.
2. Materialized entity state: `materialized.source_state` shows whether the entity's current behavior comes from a saved snapshot rather than the visible YAML.
3. Public-ID links in the mapping sidecar. Core structural validation does not check these links, so its results alone may give an incomplete picture of identity in a materialized project.
4. Prior validation snapshots for the project, when the session store retains them (see [Open Questions](#open-questions)).

### 3. Shape Shifter Domain Knowledge

Use current Shape Shifter documentation and rules for YAML configuration, the three-tier identity system, dependencies and foreign keys, directive behavior, validation, reconciliation, and target-model conformance checks.

### 4. Target Model and SEAD Target-System Knowledge

Use versioned knowledge from the target-model guides, the active target-model specification, and SEAD/SIMS design documents. It covers required entities, columns, foreign keys, and names; tracked entities and shared metadata; identity terms; ownership and association; reconciliation; provider identity and official SEAD identity; and the responsibilities of SIMS, the SEAD Authoritative Service, and Shape Shifter.

The Advisor must follow these rules from the SEAD identity and SIMS design documents:

1. **Stable identity sits above SEAD relational IDs.** Do not use SEAD integer keys as public identities.
2. **SIMS allocates identities; Shape Shifter does not.** Shape Shifter prepares reconciliation inputs and uses identity mappings. It must not become the long-term identity authority. Temporary client-side identifiers are allowed during preview or staging.
3. **The SEAD Authoritative Service affects modeling today.** Reconciliation uses this service. The Advisor should explain which entity types are reconciled, how modeling choices affect reconciliation, and where authority lookup ends and identity allocation begins.
4. **Use the target model to check conformance, not just as documentation.** Required entities, columns, foreign keys, names, and `public_id` expectations come from the active target-model specification.
5. **Keep ownership separate from association.** Not every relationship is parent-child ownership. Reconcile shared metadata instead of duplicating it.
6. **Treat tracked entities, shared metadata, and child values as different kinds of data.** Keep them distinct in modeling advice.

### 5. Framework Source and Executable Evidence

After the MVP, the Advisor may read Shape Shifter checks, transforms, loaders, and registries, then inspect approved pipeline paths for the active project. It can cite source locations and captured results, such as column names and types, row counts, null counts, and limited value summaries. These results are created during the investigation. [Investigation Capability](#investigation-capability) defines the access rules and limits.

### Context Manifest

Every assembled context and evidence artifact records a manifest that identifies the inputs used:

- project configuration digest (a hash identifying the exact configuration) and revision, including whether the configuration came from the editor or the saved project;
- Shape Shifter application and relevant validator versions;
- active target-model and knowledge-pack versions;
- validation run ID, timestamp, and result version;
- identifiers and timestamps for available deployment, materialized-data, provider-registry, and mapping-sidecar snapshots;
- source revision and data snapshot identifiers for any investigation.

The Advisor marks a result stale (out of date) when a relevant input changes. It may claim exact reproduction only when it can load the original inputs again. Otherwise, it reports their identifiers and says the result is traceable but cannot be reproduced exactly.

### Knowledge Pack

The knowledge pack contains curated rules instead of copying whole documents into prompts. Each rule cites its sources and is updated through review. This keeps the prompt compact and helps the Advisor distinguish broad SEAD guidance from active target-model requirements.

Each rule is a structured document:

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Stable identifier, e.g. `sead.identity.sims-owns-allocation` |
| `title` | string | Human-readable name |
| `status` | enum | `stable`, `provisional`, `deprecated` |
| `confidence` | enum | `high`, `medium`, `low` |
| `source` | list[string] | Source documents this rule comes from |
| `rule` | string | The rule text the Advisor should enforce or reference |
| `caveats` | list[string] | Known limitations, unresolved questions, or conditions |
| `applies_to` | list[string] | Scopes such as `reconciliation`, `export`, `public_id`, `identity modeling`, `foreign keys` |
| `examples` | list[object] | Optional correct and incorrect patterns |
| `last_reviewed` | date | Last date the rule was reviewed for accuracy |

**Sources:** the configuration guide; the AI validation guide; architecture and developer guides; generated `projectSchema.json` and `entitySchema.json`; `docs/rules/semantic_rules.yml` (machine-readable validation rules with IDs, severities, and fix suggestions — primary source for validation-error explanation and citation IDs); `.agents/skills/review-shapeshifter-configuration/SKILL.md` and `.github/instructions/shapeshifter-configuration.instructions.md` (a single curated rule source for YAML authoring and antipatterns); `docs/TARGET_MODEL_GUIDE.md`, `docs/TARGET_MODEL_SCHEMA_REFERENCE.md`, `resources/target_models/sead_standard_model.yml`, and the active target model; SEAD identity design documents; reconciliation workflow documentation and the reconciliation client implementation.

**Source tracking:** the SEAD identity documents are in `sead_identity_system`, a repository outside this workspace. The knowledge pack must record where and when it fetched each external source. Before release, decide how often to refresh these sources (see [Open Questions](#open-questions)). If a fact has a live runtime source—for example, which entity types the SEAD Authoritative Service reconciles—prefer a read-only call to that source over a copied rule.

**Curation rule:** some parts of the SEAD identity design remain unresolved, including aggregate assumptions, association versus ownership, and official versus provider identity. Record uncertainty in each rule's `confidence` and `caveats` fields. Version the pack so responses can identify which version they used and flag outdated rules.

**Promotion path:** review findings from skill sessions, such as false positives, scope surprises, and new antipatterns. Use approved findings to propose knowledge-pack rules and add evaluation scenarios. This keeps both the pack and the evaluation suite grounded in real investigations.

---

## Investigation Capability

The Advisor reaches its full value when it can investigate the project, not only restate existing results.

### Why narration alone is insufficient

Two patterns from real project work show the difference.

**A false positive.** A check said that a column created by `extra_columns` conflicted with a result column. The same column was also listed in `unnest.id_vars`. The helper that checked for conflicts included `id_vars`, so it treated a valid configuration as invalid. Here, `id_vars` are input columns that pass through unnesting; they are not output columns. To confirm the false positive, a maintainer found the check in source, inspected how it built the column set, and ran a minimal configuration.

**A more serious problem than reported.** A foreign-key check reported one orphaned value. Investigation showed that the entity copied a business code into a foreign-key column that expected a sequential identity. Eleven distinct codes happened to fall within the identity range, so they passed validation but joined to the wrong rows. Only the twelfth code fell outside that range and appeared in the report. One low-priority warning therefore pointed to a mapping defect that silently assigned most rows incorrectly.

In both cases, a useful answer must establish whether the message is wrong or describes only part of the problem. The message alone cannot establish either conclusion.

### Capability tiers

| Tier | Capability | Main risk | Answers |
|------|------------|-----------|---------|
| 1 | Source retrieval | Source disclosure and incorrect project authorization | Which code produced this message, and what does it check? |
| 2 | Approved pipeline probes | Execution cost, data exposure, and loader side effects | What did the approved pipeline path do to this data, and how far does it extend? |
| 3 | Generated experiment execution | Arbitrary-code behavior and dependency compatibility | Is the check correct, and what is the smallest reproduction? |

Every tool call creates a way to access or run something. Authorize each call, limit it to the requested project, and enforce resource limits. Tiers 1 and 2 use approved host functions with fixed arguments and read-only access. Existing services still need these controls. Tier 3 runs generated code and requires isolation. Choose one approach: orchestrate approved host tools, or use an isolated runtime that can run representative Shape Shifter code with its dependencies. Prove the chosen approach before enabling Tier 3.

### The investigation loop

1. **Find the source.** Locate the check that produced the report, or the transform or loader that shaped or read the data.
2. **Form a hypothesis.** State a specific possible cause.
3. **Design a test.** Choose the smallest experiment that can distinguish this cause from alternatives. Changing one configuration value at a time is often enough.
4. **Observe the result.** Run the project or check with read-only access and capture what happened.
5. **Record the test.** Save the inputs, output, and reproduction command in an evidence artifact.

Cite observations and sources. Base each conclusion on those citations, not on the model's internal reasoning.

### Investigation tools

A fixed set of ordinary application service operations, exposed through in-process Pydantic AI function tools and an external MCP adapter (see [Tool Harness](#tool-harness)):

| Tool | Purpose |
|------|---------|
| Source search and read | Locate the code path behind a message, validation result, or column |
| Registry inspection | Determine which checks, loaders, and filters are registered and run |
| Project load and normalize | Execute the real pipeline against the active project, read-only |
| Stage inspection | Report intermediate state: columns, dtypes, row counts, null counts, distinct values, key uniqueness |
| Differential run | Execute the pipeline with one configuration value changed |
| Cross-entity scan | Apply a check to every entity to test whether a finding is isolated or systemic |
| Reference comparison | Compare produced values against an authoritative source, such as a lookup table or the target model |
| Provider-registry inspection | Read the deployment's curated provider and binding state for the project's pair |
| Materialized state read | Read `materialized.source_state` and mapping-sidecar links for the project |
| Validation history | Compare the current validation result against a stored earlier snapshot for the project, to tell a pre-existing failure from an introduced one |

The last three tools add information that the original tool list missed: provider bindings, materialized and sidecar identity state, and earlier validation results. Earlier snapshots are needed to tell whether a problem existed before a change. If no stored snapshot is available, the Advisor must limit its comparison to the current session and say so.

### Evidence artifacts

| Field | Description |
|-------|-------------|
| `id` | Stable identifier used in citations |
| `kind` | `source_location`, `pipeline_state`, `differential_result`, `scan_result`, or `reference_comparison` |
| `context_manifest_id` | The input manifest for this artifact |
| `source_refs` | Source files and lines the experiment exercised |
| `inputs` | Project, entity, settings, data/deployment snapshot identifiers, and any snippet used |
| `output` | Captured result, such as bounded tables, counts, and value summaries |
| `claim_ids` | Findings this artifact supports or refutes |
| `reproduction` | The command or tool call that can repeat the experiment, with whether exact reproduction is still possible |
| `limitations` | What the experiment did not establish |

An artifact records what happened; it does not prove that the validator or tool is correct. Show its `limitations` as clearly as its results. A finding may apply only to one data snapshot or to the entities that were scanned.

### Permission and execution constraints

1. **Project state:** Investigation cannot mutate project configuration, source data, provider bindings, materialized state, or shared runtime state.
2. **Advisor records:** The Advisor may persist conversations, audit metadata, context manifests, citations, and evidence artifacts in a designated store with project-scoped access and an explicit retention policy. This persistence is separate from project and pipeline state.
3. **Caches:** Investigation disables pipeline caches or redirects them to an isolated per-session store; it must not write shared runtime caches.
4. **Data reads:** Approved host tools may use read-only database roles and explicitly approved external sources. Authorization and project scope are checked on every call. Network access is allowed only through these host tools.
5. **Generated code:** Tier 3 code receives no direct filesystem, environment, database, or network access. Any needed data is passed explicitly through approved host tools.
6. **Resource limits:** Set limits for each call's time and memory, database query time and rows, output size, and concurrent work. Also set a total tool-call and pipeline-run budget for each question. Define the exact limits before enabling each probe.
7. **Reproducibility:** Record the inputs, versions, and command needed to repeat each artifact. If the inputs are not saved, mark the result as traceable but not exactly reproducible.
8. **Explicit failure:** Report inconclusive and failed experiments; do not omit them.
9. **Bounded effort:** When the question budget is spent, report what was ruled out, what remains open, and offer a visible continuation choice.
10. **Future apply:** G6 is a separate, explicitly authorized path requiring a current proposal, a visible diff, validation, and a recovery path. Investigation permission never grants apply permission.

### Report negative results

Finding that a suspected cause is not responsible can be as useful as confirming a defect. The Advisor may show that a report is a false positive, that a proposed check would create too many false positives, or that a failure existed before a change. It must report what it tested and ruled out, and the evaluation suite must cover these cases.

---

## Tool Harness

Pydantic AI is the preferred harness: it runs the model/tool cycle and supports typed dependencies, function tools, structured outputs, and MCP integration. LangGraph is the main alternative if the spike shows that the Advisor needs explicit graph steps, resumable investigations, or more control over workflow branches.

### Authoritative application tool services

Ordinary Shape Shifter backend services implement investigation operations. The services, not the agent adapters, enforce application rules:

1. They provide fixed operations for source retrieval, validation, approved pipeline probes, registry and deployment-state reads, and bounded scans.
2. Before each operation, they authenticate the caller and check access to the requested project.
3. They filter results according to provider disclosure rules and enforce per-call and total resource limits.
4. They create evidence artifacts linked to the context manifest.
5. Pydantic AI function tools pass validated model arguments to these services. The functions do not implement authorization, filtering, limits, or artifact creation.
6. The MCP server exposes the same services to authorized external clients. It authenticates each caller and passes trusted caller and project context to the services. Model arguments cannot choose a project or grant access to one.
7. The embedded Advisor calls its Pydantic AI functions in-process. It does not send its own tool calls through MCP.

The application services remain authoritative if the harness or MCP transport changes. Each adapter exposes the same allowed operations, and each service checks caller identity and project access.

### Harness candidates

| Candidate | What it provides | Fit |
|-----------|------------------|-----|
| **Pydantic AI — preferred** | Python agent loop, typed dependencies and function tools, structured output, provider integrations, and MCP toolset/client support ([official documentation](https://ai.pydantic.dev/)) | Fits the Python/Pydantic v2 backend and provides the agent loop and model/provider integrations. The initial spike checks the project's response models, bounded tools backed by Shape Shifter services, selected providers, and MCP integration. |
| **LangGraph — principal alternative** | Graph-based stateful orchestration, durable execution, persistence, streaming, and human-in-the-loop controls ([official overview](https://langchain-ai.github.io/langgraph/)) | Choose this if the Advisor needs explicit workflow graphs, investigations that can pause and resume, or more control over branches and saved state. It adds more workflow structure than the MVP appears to need, so compare it only on features that could change the harness choice. |

MCP is the external tool protocol, not the authoritative tool implementation. The internal service API and the MCP adapter share application services; the embedded Advisor does not require an MCP client/server round trip to use them.

### Framework spike

Run the framework spike first. Keep it separate from the later generated-code sandbox decision. The spike must show that Pydantic AI can:

1. produce the claim-level structured response using the project's Pydantic models;
2. call a small set of bounded function tools backed by ordinary Shape Shifter services and their injected dependencies;
3. call service methods that enforce application authorization and resource limits;
4. integrate the selected local and hosted model providers; and
5. integrate with an MCP client/toolset where needed and demonstrate that an external MCP adapter can call the same application service operations. The embedded Advisor continues to use in-process function tools.

Compare LangGraph only on these requirements and any explicit need for graph-level state or durable workflow. Record the choice and the reason before committing to the tool-loop implementation.

### Generated-code sandbox decision

Decide on generated-code isolation later, in a separate spike. The framework spike does not select or test a sandbox. OSS Monty may run experiments that fit its Python subset, but it has no third-party libraries ([Monty limitations](https://pydantic.dev/docs/monty/reference/alternatives/)). Do not assume it can run Shape Shifter validators. Before enabling Tier 3, show that the chosen approach can run a representative validator with its actual dependencies. Compare this with running approved host tools instead.

## Development-Environment Handoff

The embedded Advisor and a local skill session have different access. The server does not expose general repository or shell access, and a local session does not automatically have access to deployment registry or session data. Authorized MCP tools can provide specific reads, but the two environments still have different permissions. Use this handoff process:

1. **Reproduction details.** Each artifact records its command or tool call, context manifest, and whether the original inputs are still available for exact replay. It can refer to a `scripts/validate_project.py` workflow or an MCP tool call.
2. **Investigation packet.** Export the question, context summary, citations, artifacts, and conclusions so a maintainer can continue the review in the development environment.
3. **Review findings.** Use findings from development-environment sessions to propose knowledge-pack updates and evaluation scenarios, following the review process described above.

---

## Architecture

### Backend

New backend feature area:

1. `backend/app/models/advisor.py` — Request and response models, including claims, citations, evidence artifacts, and application-managed proposal state.
2. `backend/app/services/advisor_service.py` — Authenticates the request, assembles context, invokes the Pydantic AI agent (or the selected harness), parses the structured result, and returns it.
3. `backend/app/services/advisor_context_service.py` — Builds deterministic context from project state, validation results, deployment context, dependency summaries, knowledge-pack rules, and citation IDs.
4. `backend/app/services/advisor_tool_service.py` (or focused ordinary services) — Implements investigation operations and owns project authorization, provider disclosure filtering, resource enforcement, and evidence-artifact creation.
5. `backend/app/services/advisor_investigation_service.py` — Post-MVP: prepares an investigation run, supplies trusted caller context, dependencies, and thin function-tool adapters backed by authoritative tool services, enforces aggregate run/session policy, and persists results. Pydantic AI runs the model/tool cycle; this service does not implement a second agent loop.
6. `backend/app/services/advisor_provider_config.py` — Selects a configured Pydantic AI model/provider and settings. This is a thin application configuration layer, not a duplicate implementation of framework provider adapters.
7. `backend/app/services/advisor_source_service.py` — Post-MVP: retrieves framework source locations for checks, transforms, and loaders through the authoritative tool services.
8. `backend/app/services/advisor_sandbox.py` — Later, post-MVP: runs Tier 3 experiments after a separate sandbox decision.
9. `backend/app/mcp/` — Post-MVP: thin MCP adapter that calls the same authoritative application services as the in-process function tools.
10. `backend/app/services/advisor_proposal_service.py` — Later: stores proposal snapshots and implements deterministic approval, freshness checks, apply, and recovery.
11. `backend/app/api/v1/endpoints/advisor.py` — Route handler for Advisor requests.
12. `backend/app/api/v1/endpoints/advisor_proposals.py` — Later: endpoints to inspect, approve, reject, and apply application-managed proposals.

The service follows existing backend layering: API models define shapes, services enforce application rules, mappers convert, and API DTOs hold no business logic. Domain logic that must be shared with Core stays in `src/`.

### Deterministic Code and Model Responsibility

**Deterministic code handles:** project loading and YAML parsing; schema and data validation; dependency graph extraction; preview summaries; authorized deployment-context reads; secret and sensitive-data policy enforcement; context assembly and manifest creation; citation object generation and allow-list checks; source retrieval; tool authorization and resource limits; sandbox execution and output capture; evidence artifact construction; and, in a future proposal phase, exact diff and digest creation, candidate validation, approval binding, deterministic freshness checks, apply, and recovery.

**The model handles:** plain-language explanations; prioritization; concise summaries of the basis for a claim; suggested next actions; hypotheses; selecting from the fixed investigation tools; interpreting captured artifacts; and draft proposals in future phases. Interpretations must be tied to cited observations or rules and carry a claim-level support status and scope.

**The model must not be trusted to:** decide validity without validator or experiment evidence; invent SEAD rules; change the validator's recorded result; present a disputed interpretation without supporting evidence; authorize or apply changes directly; infer secrets; reference citation IDs not supplied by the deterministic layer; call tools outside the authorized set; or present a limited or unscanned experiment as a whole-project finding.

### Frontend

Add the project-level UI to the project detail page (tab or right-side drawer — open decision). Reuse current frontend patterns: a Pinia store or composable for Advisor session state, existing project and session context, and an API client module in `frontend/src/api/`. The UI must show clarification questions as answerable prompts; each claim's support status and scope; the original validation result separately from the Advisor's interpretation; citations as clickable chips; artifact limitations and stale-context status; investigation progress; and the budget-continuation choice. Future proposals show their stored exact diff, base-configuration digest, validation result, and approval/apply status.

### Provider Configuration

Do not hardwire one LLM vendor. Configure a local model option (such as Ollama) and a hosted provider through backend settings. Keep an application-facing configuration layer that selects the Pydantic AI model/provider and supplies credentials and model options. Use the framework's provider adapters rather than maintaining duplicate provider implementations. The framework spike verifies the providers selected for the first release.

### Context Redaction and Privacy

Provider disclosure rules cover more than credentials. Project names, entity and column names, metadata, validation messages, distinct values, user questions, and tool output may contain sensitive research or operational data. Before implementation, define which data each provider may receive and how conversations, tool calls, logs, and exports are retained.

The context assembler applies an explicit, provider-specific allow-list to the question, conversation history, project context, tool output, and artifacts. It excludes environment-resolved credentials, connection strings, passwords, and tokens; preserves directives as raw strings unless their resolved values are explicitly approved; and supports a local-only mode with no outbound provider calls. Every request and tool call, including in-process calls, checks the caller's authorization for the project.

Logs contain only the minimum metadata needed for operations by default. If outbound request content must be retained for audit, store it in the designated audit store with the same project access controls and retention policy. Routine logs must not create another copy of project context without those controls. The user can review what context and tool outputs were sent and exported.

Treat project text, YAML, source data, and tool output as untrusted input that may contain prompt injection. The model cannot use such text to expand its tool set or permissions. Test cross-project access, untrusted instructions in project content, and provider-specific disclosure rules. Approved host tools may make only the explicit read-only network calls required for their function; generated experiment code has no network access.

### Application-Controlled Proposal and Apply State

A future proposal is an application record, not an agent-run approval token. Store at least the project and proposal IDs, exact diff and its digest, base configuration digest, candidate configuration digest, validation results and version for that candidate, proposer, approval state and approver, timestamps, and apply result. Bind approval to the project, base digest, exact diff, candidate digest, and validation results. Application states include draft, validated, pending approval, approved, rejected, stale, and applied.

The deterministic apply endpoint authenticates the user, rechecks project authorization, verifies that approval covers the stored diff and base digest, and confirms the current saved configuration digest still matches the proposal. It also confirms the validation results cover the candidate digest produced by that exact diff. If the project, diff, or validation changed, mark the proposal stale and require a new proposal and approval. If checks pass, apply the stored diff through the normal project update path and mapper, record the outcome, and provide the defined recovery path.

Pydantic AI approval/deferred-tool features may pause the interaction and collect a user decision. The application records approval against the exact proposal; the framework signal does not authorize the request or replace authentication, project-access checks, freshness checks, or the deterministic apply endpoint. The framework's [production guidance](https://pydantic.dev/docs/ai/production/) explicitly requires endpoint authentication and authorization inside sensitive tool functions; the proposal/apply service remains the authority for this workflow.

### Response Shape

A response contains an `answer`, a bounded `clarification`, or (post-MVP) an `investigation_offer` / `handoff_offer`. It also carries:

- `claims`: individual findings, each with an ID, text, kind (`observation`, `curated_rule`, `hypothesis`, or `conclusion`), support status (`direct`, `rule_supported`, `supported`, `disputed`, `inconclusive`, or `unverified`), scope, citation IDs, and limitations;
- `validation_result`: the original validator result and run identifier, preserved separately from any Advisor interpretation;
- `context_manifest_id`: the project, deployment, source, data, and knowledge versions used;
- `reasoning_summary`: a concise user-facing explanation of how the cited inputs relate to the finding;
- `suggested_next_actions`; and
- `proposal_id`, in future phases only, referring to an application-managed proposal record. The model may draft the exact proposed diff, but the application stores its base digest, validation results, and approval state.

Support and scope are per claim. A response may explain an unchecked report without claiming the whole project was verified. `direct` means a deterministic observation was returned; it does not mean an interpretation of that observation is correct. `disputed` means the Advisor presents evidence against the interpretation in the original report while preserving that report.

### Citation Model

Citations are structured references, not free text. The deterministic context assembler creates citation IDs, and the model may use only IDs it was given or IDs returned by authorized tools.

**Citation ID format:** `<category>.<scope>.<identifier>`

| Category | Example |
|----------|---------|
| `project.entity` | `project.entity.site.keys` |
| `validation.message` | `validation.message.FK_DATA_INTEGRITY.site.run-123.occurrence-02` |
| `dependency.edge` | `dependency.edge.site.sample_group` |
| `source.code` | `source.code.src.specifications.entity.extra_columns` |
| `evidence.artifact` | `evidence.artifact.ev-0007` |
| `provider.binding` | `provider.binding.data_provider_code.provider_schema` |
| `materialized.state` | `materialized.state.taxon.source_state` |
| `sead.rule` | `sead.identity.tracked-entity` |
| `sims.rule` | `sims.responsibility.allocation` |
| `reconciliation.rule` | `reconciliation.authoritative-service.supported-types` |
| `knowledge.pack` | `knowledge.pack.sead.identity.sims-owns-allocation` |

Validation citations retain the validator's stable issue code. When the same issue code occurs more than once, the citation adds the entity, validation run, and occurrence ID so each message can be located without changing the code itself.

**Citation rules:**

1. The backend assembles the allowed IDs before calling the model and adds IDs returned by authorized investigation tools.
2. The response parser rejects IDs outside that set and verifies that each referenced citation exists.
3. Citation existence proves only that a source was supplied. Whether the source supports the associated claim is checked with claim-level evaluation scenarios and maintainer review.
4. Each citation and claim is persisted with the session in the designated store, under its access and retention policy.
5. The UI renders citations as clickable references to the relevant entity, validation occurrence, code location, artifact, or knowledge-pack rule.

## Evaluation Plan

Define the evaluation suite before implementation so Advisor quality can be measured and checked for regressions.

### Test Categories

| Category | What it checks |
|----------|----------------|
| Validation-error explanation | Can the Advisor explain a real validation message in plain language? |
| Dependency-cycle explanation | Can the Advisor explain why a cycle exists and how to break it? |
| Entity and project scope | Does each finding state which entity/project scope and inputs it covers? |
| Claim support and mixed findings | Are observations, rules, hypotheses, and conclusions distinguished with per-claim support and citations? |
| Citation support | Does the cited source support the claim, beyond merely existing in the allow-list? |
| Tracked/shared/value-object classification | Does the Advisor correctly distinguish entity types? |
| SIMS responsibility split | Does the Advisor avoid claiming that Shape Shifter allocates official identities? |
| Authoritative-service responsibility split | Does the Advisor correctly describe when the authoritative service is involved? |
| Provider-binding correctness | Does the Advisor respect registry bindings and the fixed provider pair when advising? |
| Materialized/sidecar awareness | Does the Advisor avoid false identity findings on materialized projects with sidecar links? |
| Clarification instead of refusal | Given an ambiguous question, does the Advisor ask the right bounded question rather than refuse or guess? |
| Stale context | Does the Advisor detect changed configuration, validator, knowledge, or deployment snapshots and label stale findings? |
| Unverified labeling | Does an explanation-only answer preserve the original report and qualify unchecked interpretations? |
| False-positive investigation | Post-MVP: does the Advisor investigate a validator complaint and distinguish evidence from its interpretation? |
| Severity and scope discovery | Post-MVP: does the Advisor find when a reported problem affects more than reported, with evidence for that scope? |
| Discriminating experiment | Post-MVP: does the Advisor design a run that separates candidate causes? |
| Negative result reporting | Post-MVP: can the Advisor state that a candidate cause was tested and ruled out? |
| Pre-existing versus introduced failure | Post-MVP: with retained history, does the Advisor compare snapshots; without it, does it limit its claim to current-session data? |
| Budget and resource limits | Are time, memory, query, row, concurrency, output, and per-question limits enforced and reported? |
| Authorization and injection | Are cross-project access and prompt-injection attempts in project content rejected for in-process and MCP callers? |
| Provider disclosure and retention | Do questions, histories, tool outputs, logs, and exports obey the provider-specific policy? |
| YAML patch proposal | Later: are proposed patches valid and minimal? |
| Refusal and uncertainty | Does the Advisor say it cannot answer when no question can recover the missing input? |
| Hallucination | Does the Advisor avoid inventing SEAD rules or YAML fields? |
| Sandbox isolation and compatibility | Post-MVP: is generated code isolated, and can the chosen execution design reproduce representative validators with required dependencies? |
| Skill comparison | On frozen shared scenarios, does the skill run provide useful comparison evidence for the claimed scope and tools? Maintainer-reviewed expected findings determine correctness. |
| Regression | Do known Shape Shifter projects still produce correct advice? |

### Scenario-Based Format

Each fixture pins the project configuration digest, source revision, validator/application version, target-model and knowledge-pack versions, and any data or deployment snapshot used. Keep those inputs frozen for a run. Expected findings and required evidence are reviewed by a Shape Shifter maintainer; record acceptable alternative conclusions and the claim-level evidence required for each. A fixture must not treat a skill transcript as its correctness oracle.

```yaml
scenario: reported_conflict_is_a_false_positive
fixture:
  source_revision: <commit>
  app_version: <version>
  project_config_digest: <digest>
  target_model_version: <version>
  data_snapshot: <snapshot-id>
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
    - issue_code: EXTRA_COLUMN_CONFLICT
      run_id: run-123
      occurrence_id: occurrence-01
question: Is this error correct, and how do I fix it?
expected_claims:
  - kind: conclusion
    acceptable_conclusions:
      - the report is a false positive for this validator version
    required_citations:
      - source_location
      - differential_result
    scope: this fixture and validator version
    limitations:
      - finding applies only to the pinned validator and input
review:
  expected_findings_approved_by: <maintainer>
  skill_run: supporting_comparison_only
```

MVP scenarios can omit investigation evidence, but must require the preserved validator result, claim scope, support status, and any citations needed for the explanation. Record skill-run provenance (skill revision, repository and fixture versions, available tools, prompt, and reviewer notes) as supporting comparison data. Repeated runs and the minimum pass threshold for each claim category and capability cell are set before rollout; accepted alternatives must be scored consistently.

### Evaluation Gates

1. Define and review frozen MVP fixtures, expected findings, acceptable alternatives, claim-level evidence requirements, and pass thresholds before implementation.
2. Run the minimal evaluation runner against fixtures before the MVP backend is considered ready; keep the runner and fixture versions reproducible.
3. Complete backend MVP scenarios before beginning the frontend user evaluation.
4. Skill runs provide supporting comparison provenance; maintainer-reviewed fixtures, not agreement with a skill conclusion, determine correctness.
5. Investigation must pass false-positive, scope, materialized-awareness, authorization, privacy, resource-limit, and relevant reproducibility scenarios before the corresponding tools are enabled.
6. Add regression fixtures for earlier capabilities when a phase adds new behavior.
7. Findings promoted from development-environment sessions enter the reviewed evaluation suite before the related rule enters the knowledge pack.

## Risks And Tradeoffs

### Risk: Stale or contested SEAD knowledge

The SEAD identity design has unresolved areas, and its source documents live outside this workspace.

**Mitigation:** version the pack; carry `confidence` and `status` on every rule; record source provenance and sync cadence; prefer live read-only calls where a runtime source exists; require review when SEAD identity documents change; promote rules from real investigations through the evaluation gate.

### Risk: Users trust the Advisor more than validators

**Mitigation:** preserve the validator's original result and show the Advisor's separate, claim-level interpretation, support status, scope, and citations. Validate every YAML proposal before display; label advice as advisory; show a diff and validation result before any future apply action.

### Risk: Project data leaks to providers or logs

**Mitigation:** use provider-specific disclosure rules for user questions, history, tool output, project context, logs, and exports; exclude credentials; require local-only mode where needed; authorize every project/tool access; and govern audit records with access and retention controls.

### Risk: Citations exist but do not support claims

**Mitigation:** parser checks establish ID existence only. Review claim-to-source support in frozen scenarios and maintainer review; include acceptable alternatives and limitations in expected results.

### Risk: The tool layer widens the attack surface

Exposing project tools through MCP and in-process calls creates execution paths that can be abused or consume resources.

**Mitigation:** authenticate and authorize every call against project access; treat project content and tool output as untrusted; expose only fixed host tools; enforce query, row, time, memory, concurrency, output, and aggregate budgets; test cross-project isolation and prompt injection. Do not rely on call-count limits alone.

### Risk: Persistence creates an uncontrolled copy of project context

**Mitigation:** separate Advisor conversation/audit/evidence storage from project and pipeline state, set access and retention rules, minimize routine log content, and disable or isolate shared pipeline caches.

### Risk: Harness dependency

Building on an external framework adds a dependency and a version-tracking cost. A custom service loop could also duplicate behavior already provided by the framework.

**Mitigation:** prefer Pydantic AI and use its agent/tool loop; keep authoritative tools and policy in ordinary application services. Compare LangGraph as the principal alternative in the framework spike. Keep the harness behind the application service boundary, and do not build a second model/tool loop in `advisor_investigation_service.py`.

### Risk: Generated code cannot reproduce the application

A restricted interpreter may lack dependencies required by the validator, while a full application runtime needs stronger isolation.

**Mitigation:** demonstrate a representative reproduction with actual dependencies during the sandbox spike. Compare approved-host-tool orchestration with an isolated runtime; do not enable generated experiments until the selected design, limits, and isolation scenarios pass.

### Risk: Approval is mistaken for authorization or applies to stale state

A user approval can refer to a proposal whose diff or base configuration changed, and a framework approval signal is not proof that the caller may change the project.

**Mitigation:** keep proposal and approval state in the application store, bind approval to the exact diff and base configuration digest, and require the deterministic apply endpoint to recheck authentication, project access, approval state, configuration freshness, and validation freshness before applying.

### Risk: Experiments overstate their scope

**Mitigation:** every claim records its scope, manifest, and limitations. A cross-entity scan is required before presenting a systemic finding; a result for one entity remains entity-scoped.

### Tradeoff: Parity is a ceiling, not a floor

Matching the skill on every scenario immediately is impossible at MVP. The grid makes the shortfall explicit and testable per cell, rather than hiding it behind a single "the Advisor is an assistant" claim.

---

## Acceptance Criteria

- `P-AC-1` The MVP answers entity-level and project-level explain and recommend questions (`S1`/`S2` × `G1`/`G4`) using grounded, redacted context, without changing project configuration.
- `P-AC-2` Each claim has a kind, support status, scope, citation IDs, and limitations. The parser rejects unknown citations; validation citations preserve stable issue codes and distinguish duplicate occurrences.
- `P-AC-3` When required input is missing or ambiguous, the Advisor returns a bounded clarification naming the missing input instead of guessing.
- `P-AC-4` Provider-specific disclosure rules cover questions, history, project context, tool output, logs, and exports; local-only mode makes no outbound provider calls.
- `P-AC-5` Context assembly includes authorized provider-binding state, materialized `source_state`, and mapping-sidecar links when present, and records their snapshot identifiers in the context manifest.
- `P-AC-6` The original validation result remains available and separate from the Advisor's interpretation; an unchecked or disputed interpretation is labeled at claim level and scoped to its evidence.
- `P-AC-7` Post-MVP: source retrieval, pipeline probes, differential runs, and scans return artifacts bound to a context manifest, with inputs, scope, limitations, and reproduction status.
- `P-AC-8` Post-MVP: a ruled-out cause is reported with its evidence and scope, as are confirmed defects.
- `P-AC-9` Post-MVP: ordinary Shape Shifter services own investigation operations, caller/project authorization, disclosure filtering, resource enforcement, and artifact creation. Pydantic AI functions and the external MCP server are thin adapters to those services; the embedded Advisor does not call itself over MCP.
- `P-AC-10` Post-MVP: time, memory, query, row, concurrency, output, and per-question limits are enforced; budget exhaustion reports open questions and offers continuation.
- `P-AC-11` Evaluation uses frozen fixtures with maintainer-approved expected findings, acceptable alternatives, per-claim evidence requirements, recorded skill-run provenance, repeated runs, and predeclared pass thresholds. Skill agreement alone does not count as correctness.
- `P-AC-12` Investigation cannot mutate project configuration, source data, provider bindings, materialized state, or shared runtime state. Advisor records are stored only in the designated governed store; pipeline caches are disabled or isolated. G6 uses a separate application-controlled proposal and deterministic apply path.
- `P-AC-13` A session export includes its context manifest, question, claims, citations, artifacts, conclusions, and disclosure/retention handling.
- `P-AC-14` The MVP has a context-size policy that selects relevant entity/project metadata and validation/dependency summaries, omits unnecessary raw rows, identifies truncation, and narrows claims when context is incomplete.
- `P-AC-15` Later proposal/apply support stores the exact diff and digest, base configuration digest, candidate configuration digest, validation results/version, and approval state in the application. A deterministic apply endpoint rechecks authentication, project authorization, approval binding to that exact change, and configuration/validation freshness before applying; stale proposals cannot be applied.
- `P-AC-16` Before tool-loop implementation, the framework spike demonstrates structured answers with project models, bounded service-backed tools and injected dependencies, selected providers, and Pydantic AI MCP toolset/client compatibility. It records Pydantic AI as preferred or explains why LangGraph is required; the embedded Advisor uses in-process tools, and this spike makes no sandbox decision.

## Planning Handoff

**Confirmed decisions:**

1. Review scope and evidence access are separate axes: `S1` entity and `S2` project; evidence capabilities state what inputs are available. MVP covers `S1`/`S2` × `G1`/`G4` with `E1` and authorized `E2`.
2. Claim support and scope are recorded per finding. The original validator result is preserved separately; an Advisor may present a supported dispute without rewriting that result.
3. Citation IDs are assembled deterministically and allow-listed, but ID existence does not prove claim support. Frozen, maintainer-reviewed scenarios assess support.
4. Context and artifacts carry a versioned manifest. Exact reproduction is claimed only when inputs are retained.
5. Investigation calls are authorized and resource-bounded. Approved host tools may make explicit read-only calls; generated code has no direct network, filesystem, environment, or database access.
6. Advisor conversation, audit, manifest, citation, and artifact persistence is allowed only in a designated governed store. Project/source/provider/shared runtime mutations remain prohibited during investigation; caches are isolated or disabled.
7. Ordinary backend services are the authoritative tool layer. Pydantic AI function tools and the external MCP adapter call those services; each service enforces caller/project authorization and the shared disclosure, resource, and artifact rules.
8. Pydantic AI is the preferred harness; LangGraph is the principal alternative. The framework spike validates agent loop, model/provider support, structured outputs, bounded service-backed tools, dependencies, and MCP adapters.
9. Generated-code sandbox compatibility is a separate later spike. OSS Monty's third-party-library limitation means it is not assumed to run Shape Shifter validators.
10. G6 apply remains a separate later path requiring an application-managed proposal, exact diff, base digest, current validation, explicit approval, deterministic authorization/freshness checks, and recovery.

**Behavior and contracts to preserve:** API↔Core mapper and directive-resolution rules; existing validation workflows and stable issue codes; provider-binding enforcement; access controls on deployment state; provider-specific disclosure and retention rules.

**Expected validation outcomes:** the minimal fixture runner and reviewed MVP scenarios precede backend delivery; the framework spike precedes tool-loop implementation; backend scenarios precede frontend user evaluation; service-backed tools and the MCP adapter pass authorization, privacy, and resource-limit scenarios; generated experiments follow their separate compatibility and isolation spike.

**Open questions with resolution points:** see [Open Questions](#open-questions).

## Recommended Delivery Order

1. **Grounding foundation and fixtures:** confirm current product capabilities and access paths; curate the knowledge pack and source provenance; define context manifests, provider disclosure policy, and frozen maintainer-reviewed scenarios.
2. **Minimal evaluation runner:** run the fixtures with deterministic expected findings, acceptable alternatives, claim-level evidence requirements, and recorded skill provenance. Set repeat-run and pass thresholds before rollout.
3. **Framework spike:** time-box the Pydantic AI check for project models, structured answers, bounded service-backed tools and injected dependencies, selected providers, and MCP adapter integration. Record whether Pydantic AI is preferred or LangGraph is needed before implementing the tool loop. Do not include a generated-code sandbox decision.
4. **Explanation MVP backend:** implement `E1` and authorized `E2`, claim-level response and citation shapes, context-size policy, redaction, clarification, and preservation of validator results. Require the MVP scenarios to pass.
5. **Minimal frontend and user evaluation:** deliver answer, clarification, scope/support labels, citations, and context completeness indicators; evaluate with users before adding tool loops.
6. **Bounded investigation tools and MCP adapter:** add source retrieval and approved host probes with per-call authorization, snapshot manifests, resource caps, and isolated caches. Confirm client and authentication support. Gate each tool by its scenarios.
7. **Generated-experiment sandbox spike:** independently test whether approved-host-tool orchestration is sufficient or an isolated runtime with Shape Shifter dependencies is needed. Demonstrate representative validator execution and enforce isolation before enabling Tier 3; this decision does not reopen the harness choice.
8. **Proposal generation:** add application-managed proposals only after investigation and evaluation gates pass. Persist the exact diff, base digest, candidate digest, validation result, and approval lifecycle.
9. **Apply:** add a deterministic endpoint that rechecks user/project authorization, approved state, exact diff binding, and configuration/validation freshness before applying. Keep recovery in the application flow. Data-to-configuration assistance may be considered alongside proposals after its scope and privacy rules are defined.

## Open Questions

1. **Current capability inventory:** which listed validation, deployment-state, source, and history paths exist in each supported deployment, and what versions identify them? Resolve during grounding foundation.
2. **Provider disclosure and retention:** which data categories may each provider receive, what audit content is retained, and for how long? Resolve before any provider rollout.
3. **Context manifest:** which source, data, deployment, and configuration snapshots can be retained for exact reproduction, and which can only be referenced? Resolve before investigation tools.
4. **Evaluation standard:** who approves expected findings, acceptable alternatives, repeated-run count, and pass thresholds for each capability? Resolve before implementation.
5. **Harness selection:** does Pydantic AI satisfy the framework spike, or does LangGraph's graph-level orchestration provide a necessary advantage? Resolve before tool-loop work.
6. **Generated-code sandbox:** can the selected isolated runtime reproduce a representative validator with actual dependencies, or are approved host tools sufficient? Resolve separately before enabling Tier 3.
7. **Resource limits:** what concrete time, memory, query, row, concurrency, output, and aggregate limits apply to each probe? Resolve before enabling that probe.
8. **MCP exposure and authorization:** which deployments expose MCP, which clients are supported, and how is project access checked on each call? Resolve before investigation rollout.
9. **Validation history:** does project session storage retain earlier validation results with enough version and snapshot context, or is a governed snapshot store needed? Resolve before history comparisons.
10. **SEAD source sync:** where does the pack fetch `sead_identity_system` and sibling-repository sources, and on what cadence? Which facts need live read-only calls? Resolve during knowledge foundation.
11. **Frontend form:** tab vs. drawer, streaming vs. request-response, citation navigation, artifact display, and stale-context presentation. Resolve before frontend implementation.
12. **Apply recovery:** what rollback or restore mechanism supports an approved change, and how long does approval remain valid for the exact diff and base digest? Resolve before G6.

## Glossary

General Shape Shifter and SEAD terms are defined in [docs/GLOSSARY.md](../../GLOSSARY.md). This glossary defines only terms specific to the AI Project Advisor feature.

| Term | Definition |
|------|------------|
| **Advisor** | The AI Project Advisor feature: a grounded, project-scoped assistant that explains, verifies, reviews, and (later) proposes changes for Shape Shifter projects. |
| **Capability grid** | The scope × goal matrix in [Capability Model](#capability-model); evidence capabilities separately state which inputs a result uses. |
| **Citation** | A structured reference embedded in an Advisor response, using the ID format `<category>.<scope>.<identifier>`. The model may only use IDs the deterministic layer provided. |
| **Context assembly** | Building the provider-approved packet of project, deployment, validation, and knowledge inputs and recording their versions in a context manifest. |
| **Context manifest** | Version and snapshot identifiers for the project, application, target model, knowledge pack, validation, data, and deployment inputs used by a response or artifact. |
| **Evidence artifact** | A record of one executed experiment: what ran, what it produced, the claim it supports or refutes, its limitations, and a reproduction command. |
| **Grounded advisor** | An Advisor that answers from known project data and curated rules, not invented project state, YAML fields, or SEAD policy. |
| **Harness** | The framework that runs the model/tool cycle. Pydantic AI is preferred; LangGraph is the principal alternative pending the framework spike. |
| **Investigation** | Deriving facts about the active project by reading framework source and probing the real pipeline, rather than only restating pre-computed validation output. |
| **Knowledge pack** | A curated, versioned collection of structured rules about SEAD, SIMS, reconciliation, and target-model conformance, each with ID, confidence, sources, and scope tags. |
| **MCP** | Model Context Protocol: an open, vendor-neutral protocol for exposing tools and resources to models. Used here as an external adapter to the same application services used by in-process function tools. |
| **Skill comparison workflow** | The `review-shapeshifter-configuration` skill workflow, used to identify capabilities and provide supporting comparison data; maintainer-reviewed fixtures determine correctness. |
| **Pipeline probe** | A read-only execution of the real pipeline, or one stage, used to observe columns, dtypes, row counts, and key values (tier 2). |
| **Provider configuration** | Application settings that select a local or hosted model provider without hardwiring one vendor. The framework supplies the provider adapters. |
| **Sandbox** | The isolated environment for generated Tier 3 code; it has no direct filesystem, environment, database, or network access and runs under enforced resource limits. |
| **Support status** | The per-claim label describing whether a statement is a direct observation, rule-supported, supported, disputed, inconclusive, or unverified. |

---

## Final Recommendation

Build the Advisor, and state its ambition as the full capability grid rather than as a chat feature.

Three choices carry the design:

1. **Use the skill to map the full capability range.** The `review-shapeshifter-configuration` workflow helps identify useful review capabilities and comparison scenarios. Maintainer-reviewed fixtures, including claim-level evidence and acceptable alternatives, determine correctness; skill-run agreement alone does not.
2. **Prefer Pydantic AI over a custom agent loop.** Its function tools and MCP adapter call ordinary Shape Shifter services, where authorization, disclosure filtering, resource limits, and artifacts are enforced. LangGraph is the principal alternative if the spike establishes a need for explicit graph orchestration.
3. **Keep proposals and apply under application control.** Store the exact diff, base digest, validation results, and approval state. A deterministic endpoint rechecks authorization and freshness before applying; framework approval only coordinates the user interaction.

Delivery order, risks, and open questions above are sufficient to start phase planning from this document.
