# Proposal: Complex Entity Modeling Ergonomics

## Summary

This proposal captures the remaining feature additions and feature changes that would make complex target-schema modeling easier in Shape Shifter, especially scenarios where:

- one target concept is a shared parent across multiple branches
- one branch produces fact rows
- another entity is a lookup referenced by the fact rows
- current `append` support is powerful enough to express the model, but still requires synthetic columns, branch-specific cleanup, and implicit modeling intent

The Arbodat `analysis_entity` / `relative_dating` / `relative_ages` scenario is the motivating example.

The document has been updated to reflect the current baseline: derived branch markers, synthetic labels, and synthetic identifiers can already be expressed directly in `extra_columns` using interpolation and formula expressions. The follow-through work around that baseline is now complete, including stronger validation, clearer preview behavior, better editor guidance, and a documented decision not to introduce a second overlapping derived-value feature at this stage. That means the main remaining ergonomics gap is no longer derived-value creation itself. The harder problem is expressing branch topology, fact-versus-lookup intent, and branch-scoped consumers in a way that is obvious in YAML and easy to validate.

## Current Baseline

Shape Shifter already provides a useful cross-entity derived-value facility in `extra_columns`.

Today authors can use `extra_columns` to define:

- direct column copies
- constant values
- interpolated strings such as `"{PCODE}|{Fraktion}|{cf}|{RTyp}|{Zust}"`
- formula expressions for lightweight transforms when interpolation is not enough

In addition, the completed follow-through work now provides:

- canonical documentation and examples for copy, constant, interpolation, and formula usage
- preflight validation for invalid `extra_columns` expressions and impossible references
- clearer runtime feedback for unresolved deferred derived values
- preview visibility for derived columns and derived-column failures
- editor-side guidance, diagnostics, and low-risk suggestions for common `extra_columns` patterns

That materially changes the framing of this proposal.

The Arbodat-style workaround no longer needs to be described primarily as a missing derived-value feature. Many of the synthetic branch markers and identity columns that previously felt like SQL-only workarounds can now be modeled directly in configuration. The remaining friction is centered on declaration of modeling intent rather than on the ability to compute a value.

## Problem

Shape Shifter can currently express complex target models, but certain patterns are still awkward to author and easy to get wrong.

In the Arbodat relative-dating case, the desired target model is:

- `analysis_entity` as a shared parent
- `relative_ages` as a lookup table
- `relative_dating` as a fact table referencing both the shared parent and the lookup

The current feature set can model this, but the configuration still tends to require a workaround pattern:

- create one or more staging entities for individual branches
- use `append` to merge branch rows into a single parent entity
- invent branch discriminator and branch-local identity columns mainly to satisfy merge behavior
- add defensive filters in downstream entities that only make sense for one branch
- encode branch intent only indirectly through naming, filters, and foreign-key structure

This works, but it has costs:

- higher configuration complexity
- more hidden intent
- easier semantic mistakes around lookup versus fact roles
- more downstream null-handling and cleanup rules
- reduced readability for users editing YAML directly

## Goals

- Make shared-parent multi-branch models easier to declare
- Make fact versus lookup intent explicit in configuration
- Reduce the need for branch discriminator and identity columns whose only purpose is to satisfy `append`
- Reduce downstream cleanup rules caused by branch mixing
- Improve readability and maintainability of complex YAML projects
- Preserve explanatory comments when YAML is edited and saved

## Non-Goals

- Replace the existing `append` mechanism
- Add target-system-specific hardcoding into the core normalization pipeline
- Remove the ability to model these patterns with existing generic primitives
- Introduce a second derived-value system that duplicates what `extra_columns` already covers well

## Proposal 1: First-Class Merged Parent Entities

Add a first-class entity mode for merged parent entities composed from explicit branches.

Illustrative shape:

```yaml
analysis_entity:
  type: merged
  branches:
    - name: abundance
      source: analysis_entity_abundance_branch
      keys: [Projekt, Befu, ProbNr, PCODE, Fraktion, cf, RTyp, Zust]
    - name: relative_dating
      source: analysis_entity_relative_dating_branch
      keys: [Projekt, Befu, ProbNr, ArchDat]
```

### Why

Today the model has to simulate this through generic `append` plus author-managed branch markers and branch-local identity logic. A first-class merged parent would:

- make branch structure explicit
- allow validation per branch before merge
- allow the merged entity to expose a stable parent identity without relying on implicit append conventions
- better communicate author intent in the YAML itself

### Expected Behavior

- Each branch produces rows independently
- Shape Shifter validates branch-local keys and schema before merge
- Branch identity is retained as metadata or as an explicit branch discriminator
- The merged parent gets one public ID space after concatenation

## Proposal 2: Entity Semantic Roles (Fact vs Lookup)

**Status: Extracted to standalone proposal**

See [ENTITY_SEMANTIC_ROLES.md](ENTITY_SEMANTIC_ROLES.md) for the complete proposal.

The core issue is making fact-versus-lookup intent explicit to enable better validation. The recommended approach is adding an optional `role` field to entity configuration rather than overloading the existing `type` field.

## Proposal 3: Derived-Value Ergonomics Follow-Through

Derived-value ergonomics was tracked separately in [done/DERIVED_VALUE_ERGONOMICS_FOLLOW_THROUGH.md](done/DERIVED_VALUE_ERGONOMICS_FOLLOW_THROUGH.md) and is now complete.

This umbrella proposal now treats derived values as supporting infrastructure rather than as one of the main unresolved modeling primitives. The follow-through work already delivered the validation, preview visibility, editor guidance, examples, and closure decision that this proposal previously depended on.

For the purposes of this document, the key point is simple: complex-entity modeling should assume that branch markers, synthetic labels, and lightweight synthetic identifiers can be handled through the existing derived-value path, while the harder remaining problems are branch topology, fact-versus-lookup intent, and branch-scoped consumers.

## Proposal 4: Branch-Scoped Consumers

Allow downstream entities to declare that they only consume one branch of a merged parent.

Illustrative shapes:

```yaml
dataset:
  source: analysis_entity
  source_branch: abundance
```

or:

```yaml
abundance_ident_level:
  source: analysis_entity
  source_when:
    analysis_entity_type: abundance
```

### Why

In the Arbodat solution, once `analysis_entity` contained both abundance and relative-dating rows, some downstream consumers needed defensive cleanup:

- `dataset` had to ignore rows with empty `Fraktion`
- `abundance_ident_level` had to filter out non-abundance rows

Branch-scoped consumption would make that intent explicit and reduce accidental null-driven logic.

## Proposal 5: Schema-Aware Append for Heterogeneous Branches

Keep the generic `append` feature, but add a higher-level schema-aware mode for branch merging.

Illustrative shape:

```yaml
analysis_entity:
  type: append
  shared_keys: [Projekt, Befu, ProbNr]
  shared_columns: [analysis_entity_kind, branch_key]
  branches:
    - source: abundance_branch
    - source: relative_dating_branch
```

### Why

Current `append` is flexible, but it is still a low-level union mechanism. A schema-aware variant would:

- define shared versus optional branch columns explicitly
- null-fill branch-only columns automatically
- validate shape mismatches earlier and more clearly

This would make multi-branch parent modeling less error-prone while preserving the existing generic append behavior for simple cases.

## Proposal 6: Target-Schema-Aware Validation

**Status: Extracted to standalone proposal**

See [TARGET_SCHEMA_AWARE_VALIDATION.md](TARGET_SCHEMA_AWARE_VALIDATION.md) for the complete proposal.

The core issue is enabling semantic validation based on target data model requirements (e.g., SEAD Clearinghouse), not just YAML structure. The recommended approach is introducing reusable target model specification files referenced via `@include:`, making Shape Shifter truly generic while providing structure-specific validation when needed.

## Proposal 7: Derived Lookup Helpers

Add a helper for bootstrapping or validating lookup tables directly from fact-driving source columns.

Illustrative shape:

```yaml
relative_ages:
  type: derived_lookup
  source: sample
  key_column: ArchDat
  target_key: archdat
```

### Why

Even when a curated lookup file exists, a derived-lookup helper could still be useful for:

- verifying coverage of all raw source values
- highlighting unmapped or unexpected raw values
- generating a starter lookup artifact during initial project creation

## Proposal 8: Comment-Preserving Save Path

**Status: Extracted to standalone proposal**

See [COMMENT_PRESERVING_SAVE_PATH.md](COMMENT_PRESERVING_SAVE_PATH.md) for the complete proposal.

The core issue is preserving author comments across ordinary save operations so complex modeling rationale is not stripped from YAML during editor round trips. The recommended approach is a comment-preserving persistence path, not a generic entity-level `note` field as a substitute.

## Proposal 9: Reusable Entity Macros or Templates

Add a macro or template mechanism for repeated modeling patterns.

Illustrative shape:

```yaml
templates:
  relative_date_pattern:
    params: [raw_source, raw_column, sample_keys]

entities:
  relative_dating:
    use: relative_date_pattern
    with:
      raw_source: sample
      raw_column: ArchDat
      sample_keys: [Projekt, Befu, ProbNr]
```

### Why

Patterns like these recur:

- lookup plus fact pair
- staged branch plus merged parent
- source table plus derived property table after unnest

Templates would reduce repetition and keep the pattern consistent across projects.

## Prioritized Recommendations

If only a few improvements are pursued next, the recommended order is:

1. first-class merged parent entities
2. branch-scoped consumers
3. explicit fact-to-lookup mapping

### Why these first

These three improvements would remove most of the remaining friction seen in the Arbodat relative-dating scenario:

- merged parent entities remove the need to simulate branch structure through generic append alone
- branch-scoped consumers remove downstream cleanup filters for mixed parent entities
- explicit fact-to-lookup mapping reduces semantic confusion between lookup tables and fact tables

Derived-value ergonomics is no longer in the top three because the current `extra_columns` baseline already covers a substantial part of that earlier gap. The follow-through work is complete and recorded in [done/DERIVED_VALUE_ERGONOMICS_FOLLOW_THROUGH.md](done/DERIVED_VALUE_ERGONOMICS_FOLLOW_THROUGH.md), not a missing primary modeling construct.

## Implementation Strategy

The delivery order below is organized by implementation risk, not only by conceptual value.

### Phase 1: Low-Risk Ergonomic Follow-Through

- ✔️ COMPLETED **Derived-value ergonomics follow-through**
  Dependency: none. This is complete and documented in [done/DERIVED_VALUE_ERGONOMICS_FOLLOW_THROUGH.md](done/DERIVED_VALUE_ERGONOMICS_FOLLOW_THROUGH.md).
- **[Proposal 8: Comment-Preserving Save Path](COMMENT_PRESERVING_SAVE_PATH.md)**
  Dependency: none. This is operationally independent from the modeling proposals and can ship on its own.
- **[Proposal 6: Target-Schema-Aware Validation](TARGET_SCHEMA_AWARE_VALIDATION.md)**
  Dependency: starts with no hard dependency, but Phase 1 should scope the first rules around the current baseline and obvious lookup-versus-fact confusion. Later validation rules should expand after Proposal 4 and Proposal 5 clarify branch-aware intent.

### Phase 2: Branch-Aware Modeling Helpers

- **Proposal 4: Branch-Scoped Consumers**
  Dependency: builds on the now-complete derived-value baseline for authoring branch markers and derived discriminator columns, but does not require any new derived-value feature to exist first.
- **Proposal 5: Schema-Aware Append for Heterogeneous Branches**
  Dependency: independent of Proposal 4 at the implementation level, but the two proposals reinforce each other. Proposal 5 should preferably land before Proposal 1 so branch behavior can be validated in a lighter-weight form first.
- **[Proposal 6: Target-Schema-Aware Validation](TARGET_SCHEMA_AWARE_VALIDATION.md)**
  Dependency: expanded Phase 2 rules should build on Proposal 4 and Proposal 5 so the validator can reason about branch-scoped consumption, mixed-parent entities, and append-driven branch structure with less guesswork.

### Phase 3: First-Class Modeling Constructs

- **Proposal 1: First-Class Merged Parent Entities**
  Dependency: should build on lessons from Proposal 5 and, ideally, Proposal 4. Schema-aware append and branch-scoped consumers provide the lower-risk proving ground for branch semantics before introducing a first-class merged entity type.
- **Proposal 2: Explicit Fact-to-Lookup Mapping**
  Dependency: benefits from [Proposal 6](TARGET_SCHEMA_AWARE_VALIDATION.md), because validation is the main mechanism that turns declarative fact-to-lookup intent into actionable guidance. It does not strictly depend on Proposal 1, but the two proposals complement each other in shared-parent fact models.
- **Proposal 7: Derived Lookup Helpers**
  Dependency: should follow Proposal 2, because lookup derivation or lookup coverage checks are clearer once explicit fact-to-lookup relationships exist.
- **Proposal 9: Reusable Entity Macros or Templates**
  Dependency: should come last. It depends on the stabilization of Proposal 1, Proposal 2, Proposal 4, and Proposal 5; otherwise it risks freezing patterns that are still changing.

## Benefits

- Lower cognitive overhead for complex target schemas
- Fewer configuration workarounds
- Better validation quality for semantic modeling mistakes
- Better readability for authors working directly in YAML
- Better alignment between declared YAML structure and actual modeling intent
- More maintainable projects over time

## Risks

- Higher conceptual surface area if too many new modeling primitives are added at once
- Potential overlap between enhanced `append`, merged-parent entities, and template features
- Need for clear ordering semantics between `extra_columns`, append or merge operations, foreign keys, and unnest
- Risk of introducing overlapping abstractions before simpler branch-aware helpers have been validated in real projects

## Recommendation

Focus the next round of ergonomics work on making branch structure and fact-versus-lookup intent explicit.

The best next investments are:

- branch-aware consumption
- clearer merged-parent modeling
- stronger semantic validation
- [comment-preserving save behavior](COMMENT_PRESERVING_SAVE_PATH.md)

Those changes would materially simplify scenarios like Arbodat relative dating without reopening the now-closed question of how lightweight derived values should be authored.
