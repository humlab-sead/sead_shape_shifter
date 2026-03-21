# Proposal: Complex Entity Modeling Ergonomics

## Summary

This proposal captures feature additions and feature changes that would make complex target-schema modeling easier in Shape Shifter, especially scenarios where:

- one target concept is a shared parent across multiple branches
- one branch produces fact rows
- another entity is a lookup referenced by the fact rows
- current `append` support is powerful enough to express the model, but only through synthetic columns and downstream cleanup rules

The Arbodat `analysis_entity` / `relative_dating` / `relative_ages` scenario is the motivating example.

## Problem

Shape Shifter can currently express complex target models, but certain patterns are awkward to author and easy to get wrong.

In the Arbodat relative-dating case, the desired target model is:

- `analysis_entity` as a shared parent
- `relative_ages` as a lookup table
- `relative_dating` as a fact table referencing both the shared parent and the lookup

The current feature set required the project to use a workaround pattern:

- create a staging entity for one branch
- use `append` to merge branch rows into a single parent entity
- invent synthetic discriminator and identity columns such as `analysis_entity_type` and `analysis_entity_value`
- add defensive filters in downstream entities that only make sense for one branch
- encode some identity logic inside SQL rather than in configuration-level transformations

This works, but it has costs:

- higher configuration complexity
- more hidden intent
- easier semantic mistakes around lookup versus fact roles
- more downstream null-handling and cleanup rules
- reduced readability for users editing YAML directly

## Goals

- Make shared-parent multi-branch models easier to declare
- Make fact versus lookup intent explicit in configuration
- Reduce the need for synthetic identity columns created only to satisfy `append`
- Reduce downstream cleanup rules caused by branch mixing
- Improve readability and maintainability of complex YAML projects
- Preserve explanatory comments when YAML is edited and saved

## Non-Goals

- Replace the existing `append` mechanism
- Add target-system-specific hardcoding into the core normalization pipeline
- Remove the ability to model these patterns with existing generic primitives

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

Today the model has to simulate this through generic `append` and synthetic columns. A first-class merged parent would:

- make branch structure explicit
- allow validation per branch before merge
- allow the merged entity to expose a stable parent identity without custom SQL concatenation tricks
- better communicate author intent in the YAML itself

### Expected Behavior

- Each branch produces rows independently
- Shape Shifter validates branch-local keys and schema before merge
- Branch identity is retained as metadata or an explicit branch discriminator
- The merged parent gets one public ID space after concatenation

## Proposal 2: Explicit Fact-to-Lookup Mapping

Add a declarative way to express that a fact entity references a lookup based on a raw source column.

Illustrative shape:

```yaml
relative_dating:
  type: fact
  source: relative_dating_source
  lookup_refs:
    - raw_column: ArchDat
      lookup_entity: relative_ages
      lookup_key: archdat
```

### Why

The difficult part in the relative-dating scenario was that:

- `relative_ages` is the lookup
- `relative_dating` is the fact table

That distinction is currently implicit. When it is not expressed explicitly, it is easy to model the fact entity as if it were the lookup itself.

### Expected Behavior

- Validation warns when a fact entity appears to use the lookup public ID as its own public ID
- The lookup link is described once, declaratively
- The same model can later support coverage checks such as “all raw fact values must be resolvable in the lookup”

## Proposal 3: Better Derived-Value Ergonomics

Clarify and extend derived-value support without conflating two different concepts:

- `extra_columns` is already a cross-entity feature and works for any entity type
- a future `computed_columns` feature, if introduced, would more naturally be SQL-specific

Today, Shape Shifter already supports useful derived-column behavior through interpolated `extra_columns`, for example building a synthetic key such as:

```yaml
extra_columns:
  analysis_entity_type: abundance
  analysis_entity_value: "{PCODE}|{Fraktion}|{cf}|{RTyp}|{Zust}"
```

That means the exact Arbodat workaround did not strictly require a brand-new feature. However, the current capability is under-documented, limited in expression power, and easy to overlook because it is described under `extra_columns` rather than as an explicit derived-value facility.

Illustrative shape:

```yaml
extra_columns:
  analysis_entity_type: abundance
  analysis_entity_value: "{PCODE}|{Fraktion}|{cf}|{RTyp}|{Zust}"
```

Possible future SQL-specific extension:

```yaml
computed_columns:
  analysis_entity_type: "'abundance'"
  analysis_entity_value: concat_ws('|', PCODE, Fraktion, cf, RTyp, Zust)
```

### Why

This would likely provide the highest immediate value with relatively low conceptual cost.

The goal is not to replace `extra_columns`. The immediate need is to make its current interpolation support explicit and documented. A separate SQL-only `computed_columns` feature would only make sense later if richer SQL-expression ergonomics are needed.

It would:

- reduce SQL-specific identity hacks
- preserve the simple interpolation use case that already works today
- preserve a cross-entity derived-value mechanism that works across `sql`, `entity`, `fixed`, `csv`, and Excel-backed entities
- make derived identity and branch markers easier to read and validate
- reduce repetition across staging entities

It would also address the current gap between implementation and documentation: the code supports interpolated `extra_columns`, but the configuration guide previously described `extra_columns` mainly as copy-or-constant behavior.

### Expected Behavior

- Simple interpolation should remain supported
- Interpolated `extra_columns` should remain available for all entity types
- If a SQL-only `computed_columns` feature is later added, it should run after source extraction but before foreign keys and append/merge operations that depend on it
- SQL expressions should support a limited, explicit transformation vocabulary rather than arbitrary code execution
- Authors should be able to choose between lightweight cross-entity interpolation and richer SQL-specific derived expressions without unnecessary duplication

### Suggested Scope

Short term:

- document interpolated `extra_columns` as a supported pattern
- treat it as the recommended current solution for simple synthetic identifiers and branch markers

Medium term:

- improve validation and preview support for interpolated `extra_columns`
- decide whether a separate SQL-only `computed_columns` feature is needed at all
- if needed, add richer SQL-expression support such as concatenation helpers, trimming, null coalescing, and basic conditional logic

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

Add optional target-schema-aware validation rules that reason about intent, not just structure.

Examples of useful warnings:

- a fact-like entity using a lookup-style public ID name
- an entity named `relative_dating` mapping to `relative_age_id`
- a merged parent missing any branch discriminator or stable branch-local identity
- a child fact table not linked to the intended shared parent

### Why

The relative-dating issue was not a YAML syntax problem. It was a semantic mismatch with the target model. A validator that understands common target-model patterns would catch this earlier.

This could remain optional and be enabled only for projects that want target-aware guidance.

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

Preserve YAML comments across normal load/edit/save operations.

### Why

Complex modeling work often needs local explanation in the YAML file itself. In the current backend save path, explanatory comments are not reliably preserved because YAML is normalized into plain Python objects before being written again.

That means the more complex the modeling workaround, the harder it is to keep the rationale close to the configuration.

This is not the core modeling feature, but it materially affects maintainability.

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

If only a few improvements are pursued, the recommended order is:

1. better derived-value ergonomics
2. first-class merged parent entities
3. branch-scoped consumers

### Why these first

These three features would remove most of the friction seen in the Arbodat relative-dating scenario:

- better derived-value ergonomics remove most SQL hacks for synthetic identities while building on the interpolation support that already exists today
- merged parent entities remove the need to simulate branch structure through generic append alone
- branch-scoped consumers remove downstream cleanup filters for mixed parent entities

## Implementation Strategy

### Phase 1: Low-Risk Ergonomics

- Document interpolated `extra_columns` as the current supported derived-value pattern
- Improve validation, discoverability, and preview support for interpolated `extra_columns`
- Add comment-preserving YAML save behavior
- Add new validations around likely lookup/fact confusion

### Phase 2: Branch-Aware Modeling

- Add branch-scoped consumer support
- Add schema-aware append helpers for heterogeneous branches

### Phase 3: First-Class Modeling Constructs

- Add merged parent entities
- Add explicit fact-to-lookup mapping
- Consider derived lookup helpers and/or template support

## Benefits

- Lower cognitive overhead for complex target schemas
- Fewer configuration workarounds
- Better validation quality for semantic modeling mistakes
- Better readability for authors working directly in YAML
- More maintainable projects over time

## Risks

- Higher conceptual surface area if too many new modeling primitives are added at once
- Potential overlap between enhanced `append` and first-class merged-parent features
- Need for clear ordering semantics between source extraction, computed columns, append/merge, foreign keys, and unnest

## Recommendation

Start with better derived-column ergonomics, branch-aware downstream filtering/consumption, and comment-preserving saves.

Those changes have the best ratio of implementation cost to user value, and they would materially simplify scenarios like Arbodat relative dating even before larger modeling constructs are introduced.
