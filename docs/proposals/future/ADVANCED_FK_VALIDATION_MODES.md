# Proposal: Advanced FK Validation Modes

## Status

- Proposed future change
- Scope: target-model format, core conformance validation, target-model spec validation
- Goal: let target models say whether a required foreign-key relationship must be direct, may be transitive, or must follow one named path

## Summary

Keep the current `via` support and graph-based FK conformance as the default behavior for now, but reserve a future extension for stricter FK modes. This matters because the current validator can prove that some acceptable path exists, but it cannot express whether the target contract requires a direct FK, a specific bridge, or one canonical traversal path.

## Problem

The current conformance engine answers one broad question: can the source entity reach the required target entity through the project's target-facing FK graph?

That is useful for reducing false positives, but it collapses distinctions that may matter later:

- some relationships are only valid when they are direct
- some relationships are only valid through one named intermediary
- some downstream joins, review rules, or documentation depend on a canonical traversal path rather than any reachable path

Without a way to express those distinctions, `required: true` on a foreign key remains intentionally loose.

## Scope

- add optional FK mode attributes to the target-model format
- define how each mode is validated in core conformance
- define spec-level consistency rules for mutually exclusive mode settings

## Non-Goals

- changing the current default FK conformance behavior in the near term
- introducing column-level join-key semantics in the same proposal
- implementing this work before a real target model needs the extra precision

## Current Behavior

Current FK conformance supports two useful patterns:

- direct target presence via the project's target-facing FK graph
- explicit bridge mediation with `via`

This already covers the common many-to-many case and the common transitive-path case. What it does not cover is intent about which path is acceptable.

## Proposed Design

### Candidate mode attributes

```yaml
# Mode 1: Direct FK only
entity_a:
  foreign_keys:
    - entity: entity_b
      direct: true
      required: true

# Mode 2: Bridge-mediated
entity_a:
  foreign_keys:
    - entity: entity_c
      via: bridge_entity
      required: true

# Mode 3: Transitive FK
entity_a:
  foreign_keys:
    - entity: entity_d
      transitive: true
      required: true
      max_depth: 3

# Mode 4: Explicit path constraint
entity_a:
  foreign_keys:
    - entity: entity_e
      path: [intermediary_1, intermediary_2]
      required: true
```

### Intended semantics

- `direct: true`: require the target to appear in the source entity's immediate FK targets
- `via: bridge_name`: require a specific bridge entity between source and target
- `transitive: true`: allow any valid FK chain, optionally capped by `max_depth`
- `path: [...]`: require one exact ordered traversal path

### Spec validation rules

- only one FK mode should be allowed per FK spec
- no mode specified should keep current behavior until a breaking-format decision is made
- `max_depth` should only be valid with `transitive: true`
- `path` entities must be valid entity names in the same target model

## Risks and Tradeoffs

- more expressive FK semantics make the format harder to explain and validate
- transitive and explicit-path checks need stable FK graph access and may add cost
- an overly flexible mode system could turn target models into implementation-specific join plans instead of semantic contracts

## Testing And Validation

- spec-validator coverage for mutually exclusive modes and invalid combinations
- conformance tests for direct-only, bridge-only, transitive, and explicit-path cases
- regression tests proving the current default behavior remains unchanged until the feature is intentionally enabled

## Acceptance Criteria

- the format can express direct, bridge-mediated, transitive, and explicit-path FK intent without ambiguity
- invalid mode combinations are rejected by target-model spec validation
- conformance can distinguish between any-path success and required-path success
- current projects without mode attributes keep existing behavior

## Open Questions

- should the long-term default remain permissive path detection or become direct-only when a mode is omitted?
- should `path` be limited to entity names, or should it eventually support named edge constraints?
- does `max_depth` belong in the format, or is it an implementation detail?

## Final Recommendation

Keep this work out of the current conformance CR. The need is real, but it is a future format-and-validator design question rather than a low-risk follow-up to the current implementation. Revisit it only when a target model needs stricter FK intent than `via` plus broad path detection can express.