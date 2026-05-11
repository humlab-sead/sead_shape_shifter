# Title

Restructure AI/ML Instruction Architecture for Scoped, Feature-Oriented Guidance

## Status

* **Complete** — all delivery items done
* Scope: Repository-wide AI/ML instruction organization
* Goal: Improve AI-assisted development quality while reducing instruction noise and token consumption

### Completed

* `copilot-instructions.md` reduced from 120 to 53 lines
* `features/` subdirectory created under `.github/instructions/`
* `applyTo` added to all doc-specific instruction files (design, operations, user-guide, testing, development)
* Frontmatter added to `diagrams.instructions.md` (`description:` only — no `applyTo`, intentionally broad)
* Decided against a `docs/` subdirectory for doc-specific instructions (closed set, low churn)
* All feature instruction files created:
  * `features/target-model.instructions.md` ✓
  * `features/entities.instructions.md` ✓
  * `features/transforms.instructions.md` ✓
  * `features/execution.instructions.md` ✓
  * `features/validation.instructions.md` ✓
  * `features/specifications.instructions.md` ✓
  * `features/loaders.instructions.md` ✓
  * `features/materialization.instructions.md` ✓
  * `features/reconciliation.instructions.md` ✓
  * `features/graph.instructions.md` ✓
  * `features/ingesters.instructions.md` ✓ (moved from `.github/instructions/`)
* GitHub issue [#422](https://github.com/humlab-sead/sead_shape_shifter/issues/422) created to track remaining work

---

# Summary

This proposal restructures the current AI/ML instruction system into a layered, path-scoped architecture optimized for GitHub Copilot, Codex, and related assistants.

The proposal introduces:

* a smaller always-on instruction layer
* scoped layer-specific instructions
* targeted feature-oriented instructions
* operational rather than explanatory instruction design

The goal is to improve:

* instruction relevance
* adherence to architecture constraints
* token efficiency
* maintainability of instruction files

---

# Problem

The repository currently contains a growing set of instruction files under `.github/instructions/`.

While already useful, several issues are emerging:

* instruction overlap
* duplicated architectural rules
* unclear granularity
* oversized instruction files
* unnecessary context loading
* increasing maintenance burden

Current files mix:

* documentation rules
* architecture constraints
* feature behavior
* YAML semantics
* workflow guidance

Without structure, the instruction system risks becoming noisy and less effective.

---

# Scope

This proposal covers:

* instruction hierarchy
* feature-level instruction strategy
* instruction granularity guidelines
* context budget optimization
* instruction governance
* migration of existing instructions

---

# Non-Goals

This proposal does not:

* redesign repository architecture
* replace existing documentation
* encode all project knowledge into instructions
* standardize external AI behavior
* create automated instruction tooling

---

# Current Behavior

The repository currently uses:

```text
.github/copilot-instructions.md          ← always-on
.github/instructions/*.instructions.md   ← layer/task-specific
.github/instructions/features/           ← feature-specific (new)
```

Existing scoped instructions include:

* frontend
* Python/backend
* testing
* documentation (design, operations, user-guide, development)
* operations
* configuration/YAML
* diagrams

Feature instructions (all created):

* `features/target-model.instructions.md` ✓
* `features/entities.instructions.md` ✓
* `features/transforms.instructions.md` ✓
* `features/execution.instructions.md` ✓
* `features/validation.instructions.md` ✓
* `features/specifications.instructions.md` ✓
* `features/loaders.instructions.md` ✓
* `features/materialization.instructions.md` ✓
* `features/reconciliation.instructions.md` ✓
* `features/graph.instructions.md` ✓
* `features/ingesters.instructions.md` ✓ (moved from `.github/instructions/`)

The root instruction file currently contains:

* architecture rules
* workflow expectations
* testing guidance
* implementation patterns
* identity system rules

Several instruction files overlap in scope and contain explanatory material better suited for documentation.

---

# Proposed Design

## Instruction Hierarchy

Adopt a four-level hierarchy:

```text
Always-On
  ↓
Layer-Specific
  ↓
Feature-Specific
  ↓
Task-Specific
```

---

## Always-On Instructions

Keep repository-wide instructions extremely small.

Target size:

* 60–100 lines

Always-on instructions should contain only:

* repository map
* core architecture boundaries
* identity system rules
* testing expectations
* references to scoped instructions

Move detailed implementation guidance into scoped files.

---

## Layer-Specific Instructions

Retain broad technical-area instructions:

```text
frontend.instructions.md
python.instructions.md
development.instructions.md
testing.instructions.md
```

These should focus on:

* framework conventions
* architecture boundaries
* testing expectations
* cross-layer interaction rules

Avoid feature-specific behavior in layer instructions.

---

## Feature-Specific Instructions

Introduce targeted feature instructions for high-complexity capabilities.

Candidate files (prioritised by expected AI mistake frequency):

```text
✓ features/target-model.instructions.md
  applyTo: src/target_model/**, backend/app/validators/target_model_validator.py,
           backend/app/services/validation_service.py, tests/model/test_target_model*

✓ features/entities.instructions.md
  applyTo: src/model.py, src/specifications/**, backend/app/services/entity*,
           frontend/src/components/entities/**, tests/model/**

✓ features/transforms.instructions.md
  applyTo: src/transforms/**, tests/test_dispatch*, tests/process/**

✓ features/execution.instructions.md
  applyTo: src/normalizer.py, src/process_state.py, src/workflow.py, src/shapeshift.py,
           tests/process/**, tests/integration/**

✓ features/validation.instructions.md
  applyTo: src/validators/**, backend/app/validators/**, backend/app/services/validation*,
           tests/test_constraints*, backend/tests/test_validation*

✓ features/specifications.instructions.md
  applyTo: src/specifications/**, tests/test_constraints*, tests/project/**

✓ features/loaders.instructions.md
  applyTo: src/loaders/**, backend/app/services/data_source*, backend/app/services/schema*,
           tests/loaders/**

✓ features/materialization.instructions.md
  applyTo: backend/app/services/materialization*, backend/app/api/v1/endpoints/materialization*,
           src/specifications/materialize.py, backend/tests/test_materialization*

✓ features/reconciliation.instructions.md
  applyTo: src/reconciliation/**, backend/app/services/reconciliation*,
           backend/app/clients/reconciliation_client.py, backend/tests/test_reconciliation*

✓ features/graph.instructions.md
  applyTo: frontend/src/composables/useCytoscape.ts, frontend/src/composables/useDependencies.ts,
           frontend/src/components/dependencies/**, frontend/src/utils/graphAdapter.ts,
           frontend/src/utils/taskGraph.ts, frontend/src/config/cytoscapeStyles.ts

✓ features/ingesters.instructions.md  (moved from .github/instructions/)
  applyTo: ingesters/**/*.py, backend/tests/ingesters/**/*.py
```

`dispatch.instructions.md` — **not recommended**. Low complexity, well-tested, registry pattern already covered in `python.instructions.md`.

Feature instructions should focus on:

* invariants
* common failure modes
* architectural boundaries
* required testing
* forbidden shortcuts

Avoid:

* tutorials
* conceptual explanations
* duplicated documentation

---

## Task-Specific Instructions

Keep small task-oriented instructions for:

* diagrams (no `applyTo` — applies whenever a Mermaid diagram is involved, regardless of file)
* GitHub workflow
* proposal writing

Documentation-focused instructions (design, operations, user-guide, testing, development) now use `applyTo: "docs/XYZ.md"` to auto-load only when that specific doc is open. They stay flat in `.github/instructions/` — the set is small and stable, so a `docs/` subdirectory is not warranted.

These should remain narrow and operational.

---

## Instruction Granularity Rules

Create a new instruction file only when:

* AI repeatedly makes mistakes in that area
* the capability has important invariants
* the feature spans multiple layers
* incorrect implementation would be expensive

Avoid creating instructions for:

* small utility modules
* isolated components
* simple CRUD behavior

---

## Path Scoping

VS Code supports two complementary frontmatter mechanisms for scoped instructions:

**`applyTo:`** — path-triggered. The file auto-loads whenever a matching path is open or edited. Reliable and zero always-on cost. Preferred for code and doc files with well-defined paths.

**`description:`** — semantically triggered. VS Code uses it as a hint; the AI may load the file when the task seems relevant, but it is not guaranteed. Suitable for cross-cutting concerns (e.g. diagrams, proposal writing) where no single path captures the scope.

Both can appear in the same frontmatter block.

Example for a feature instruction:

```md
---
applyTo: "src/reconciliation/**,backend/app/services/reconciliation_service.py"
---
```

Use only workspace-relative paths in `applyTo`. Never use absolute paths.

Path scoping reduces:

* irrelevant context loading
* instruction collisions
* unnecessary token usage

---

## Instruction Content Rules

Instruction files should be:

* concise
* operational
* constraint-oriented

Preferred content:

* do/don't rules
* invariants
* anti-patterns
* required tests

Avoid:

* tutorials
* architecture essays
* conceptual documentation

Documentation remains the canonical source for explanations and reference material.

---

## Configuration Instruction Consolidation

Review overlap between:

```text
project-config.instructions.md
shapeshifter-configuration.instructions.md
```

Suggested split:

```text
project-config.instructions.md
```

Use for editing actual project YAML.

```text
configuration-engine.instructions.md
```

Use for Python implementation of:

* schema parsing
* directive resolution
* validation
* config models

---

## AI-Assisted Instruction Generation

Recommended workflow:

```text
Human defines hierarchy and scope
↓
AI drafts concise instruction files
↓
Human trims and validates
↓
Instructions evolve from recurring AI failures
```

Use AI primarily for:

* extracting invariants
* generating scoped rules
* identifying anti-patterns
* distilling documentation

Humans remain responsible for:

* hierarchy design
* scope boundaries
* context budgeting
* governance

---

# Alternatives Considered

## Single Large Instruction File

Rejected because:

* assistants inconsistently apply large instructions
* token usage grows rapidly
* unrelated guidance pollutes tasks

---

## Extremely Fine-Grained Instructions

Rejected because:

* maintenance overhead increases
* overlap becomes difficult to control
* instruction discovery becomes harder

---

# Risks And Tradeoffs

## Increased Maintenance

More instruction files increase maintenance burden.

Mitigation:

* keep files small
* enforce strict scope boundaries
* avoid duplication

---

## Incorrect Scoping

Poor `applyTo` patterns may prevent instruction activation.

Mitigation:

* refine scopes incrementally
* validate with real assistant usage

---

## Drift Between Docs and Instructions

Mitigation:

* instructions should reference docs
* instructions should focus on constraints only

---

# Testing And Validation

Validate the proposal by:

* measuring instruction sizes
* reviewing overlap reduction
* testing Copilot/Codex behavior
* evaluating token/context usage
* tracking recurring AI mistakes

Success indicators:

* smaller root instructions
* improved assistant relevance
* fewer architecture violations
* reduced unnecessary context loading

---

# Acceptance Criteria

The proposal is complete when:

* the root instruction file is significantly reduced
* feature instructions are introduced for major capabilities
* layer and feature scopes are clearly separated
* configuration instruction overlap is reduced
* scoped instructions use path targeting where supported
* instruction files remain concise and operational

---

# Recommended Delivery Order

1. ✓ Reduce always-on instructions
2. ✓ Define hierarchy and directories (`features/` subdirectory)
3. ✓ Add `applyTo` to doc-specific instruction files
4. ✓ Introduce all feature instructions (entities, transforms, execution, validation, specifications, loaders, materialization, reconciliation, graph, ingesters, target-model)
5. ✓ Move `ingesters.instructions.md` into `features/`
6. ✓ Consolidate overlapping configuration instructions
7. ✓ Refine using real AI usage feedback

---

# Final Recommendation

Adopt a layered, scoped instruction architecture optimized for:

* small always-on context
* feature-oriented guidance
* lower token consumption
* reduced overlap
* higher assistant relevance

Use AI to generate concise instruction drafts and extract invariants, but keep hierarchy design, scoping strategy, and context budgeting under human control.
