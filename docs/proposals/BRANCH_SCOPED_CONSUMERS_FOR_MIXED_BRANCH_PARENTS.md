# Proposal: Branch-Scoped Consumers For Mixed-Branch Parents

## Status

- **Proposed follow-up**
- **Scope**: project YAML authoring for mixed-branch parent entities
- **Goal**: let downstream entities declare which branch of a mixed parent they consume

## Summary

This proposal focuses on one remaining modeling gap.

Shape Shifter can now build mixed-branch parents cleanly, but downstream entities still need ad hoc filters when they should only read one branch. The proposal adds an explicit way to declare that restriction in YAML and validate it early.

The Arbodat `analysis_entity` case remains the motivating example.

## Problem

Shape Shifter now has the core features needed to build shared-parent models:

- `extra_columns` for lightweight derived values
- source-based append with alignment controls
- `defer_dependency` for cycle breaking
- target-model conformance validation
- first-class merged parent entities

That means the main remaining problem is not parent construction. It is downstream consumption.

When one source entity contains rows from multiple branches, some downstream entities are only valid for one branch. Today that intent is usually expressed indirectly through filters or null checks instead of being declared on the entity itself.

In the Arbodat example, once `analysis_entity` contains both abundance rows and relative-dating rows:

- `dataset` should consume only the abundance-like branch that carries method context
- `abundance_ident_level` should ignore non-abundance rows

The current workaround has costs:

- branch intent is hidden in cleanup filters
- unrelated rows are loaded and discarded later
- validation and review must infer intent from downstream logic
- YAML stays harder to read than the actual model requires

## Scope

This proposal covers:

- explicit branch-scoped consumption on downstream entities
- validation for invalid or ambiguous branch selectors
- preview or editor support that shows the active branch restriction
- optional conformance follow-up if branch scoping should affect diagnostics

## Non-Goals

- new derived-value primitives beyond `extra_columns`
- a new `derived_lookup` entity type
- project-level fact-versus-lookup role declarations
- new parent-construction syntax that overlaps with merged entities
- template or macro systems
- comment-preserving save behavior

## Current Behavior

Mixed-branch parents are already possible and are no longer the hard part.

The remaining gap is that downstream entities read the full parent unless the author adds ordinary filters that happen to simulate branch selection.

Those filters work, but they are a weak substitute for an explicit branch restriction because they do not declare modeling intent clearly.

## Proposed Design

Add an explicit way for a downstream entity to declare that it reads only one logical branch from its source entity.

Two illustrative shapes:

```yaml
dataset:
  source: analysis_entity
  source_branch: abundance
```

```yaml
abundance_ident_level:
  source: analysis_entity
  source_when:
    analysis_entity_type: abundance
```

Recommended direction:

- use `source_when` as the general primitive
- allow `source_branch` only when the source entity exposes stable named branches
- reject configurations that specify both forms unless one is defined as syntactic sugar for the other

Expected behavior:

- rows that do not satisfy the branch restriction are excluded before downstream branch-specific cleanup filters
- validation reports unknown branch names, contradictory selectors, or selectors that reference unavailable columns
- preview and editor UI show that the entity is branch-scoped rather than reading the full parent

## Alternatives Considered

### Keep using ordinary filters

This requires no new feature, but it keeps branch intent implicit and leaves a recurring pattern in ad hoc cleanup logic.

### Add broader branch-aware parent syntax first

This no longer looks like the best next step. Parent construction is already covered well enough by merged entities and source-based append. The remaining problem is downstream intent.

### Add templates or macros instead

Templates would compress repetition, but they would package the workaround rather than make branch semantics explicit.

## Risks And Tradeoffs

- The execution order relative to filters, unnesting, and foreign-key-added columns must stay explicit.
- If both `source_branch` and `source_when` exist, the docs and API must make their relationship obvious.
- Branch-scoped consumers should stay narrow and should not become a second general filtering language.

The tradeoff is still favorable because this is a small feature that addresses a real remaining modeling pain point.

## Testing And Validation

### Unit Tests

- parser and schema coverage for `source_branch` and `source_when`
- validation failures for unknown branches and invalid selector columns
- execution-order tests showing branch scoping runs before downstream cleanup filters

### Integration Tests

- an Arbodat-style mixed-parent example where `dataset` and `abundance_ident_level` consume only one branch
- comparison with the current filter-based workaround to confirm equivalent output with clearer config

### UX And Documentation

- document when to use branch scoping instead of ordinary filters
- show the active branch restriction in preview or editor summaries

## Acceptance Criteria

- [ ] downstream entities can declare a branch restriction with one supported syntax
- [ ] invalid branch restrictions fail validation with explicit messages
- [ ] branch-scoped consumers reduce the need for defensive cleanup filters in the Arbodat-style mixed-parent case
- [ ] docs explain when to use branch scoping instead of ordinary filters
- [ ] preview or editor surfaces make the restriction visible to authors

## Recommended Delivery Order

1. Add one branch-scoping syntax and validation.
2. Apply it to the Arbodat-style mixed-parent example and confirm it replaces cleanup filters cleanly.
3. Expose the restriction in preview and editor views.
4. Add any small conformance follow-up only if real diagnostics still need it.

## Final Recommendation

Pursue branch-scoped consumers as a focused follow-up.

This is the remaining authoring gap that still looks worth adding in core. Other earlier ergonomics gaps should stay closed, deferred, or tracked in separate documents.