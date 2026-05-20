# Fixed-Entity Type Convention Enhancements

## Status

- Proposed feature / change request
- Scope: Deferred enhancements after the initial project-level fixed-entity convention rollout
- Goal: Decide whether fixed-entity typing should grow beyond project-level defaults without weakening the current explicit and predictable behavior

## Summary

The initial project-level fixed-entity convention feature is now implemented. It adds ordered project-wide defaults, keeps `column_types` as the highest-precedence declaration, and preserves undeclared non-`_id` scalar values.

This follow-up proposal covers the remaining deferred scope:

- entity-scoped convention blocks
- possible target-model-informed typing
- optional lineage visibility in UX
- regex-based matching

The recommendation is not to implement all of these together. The next useful step, if there is real demand, is entity-scoped convention support and a narrow evaluation of target-model-informed typing. UX lineage and regex support should remain deferred unless concrete project needs justify them.

## Problem

The initial implementation intentionally keeps fixed-entity typing narrow and predictable. That is the right default, but it leaves some known follow-up questions unresolved:

- Some projects may want reusable defaults for one fixed entity without making them global.
- Some projects may want to reuse target model type hints to reduce duplication.
- Some users may eventually need visibility into why a type was chosen.
- Some projects may outgrow glob matching and ask for regex support.

These needs are real backlog candidates, but they should not be folded into the initial convention rollout without a separate decision.

## Scope

This proposal covers:

- whether to add entity-scoped fixed-entity convention blocks
- whether target model column type hints should influence fixed-entity typing
- whether the product needs lineage visibility for effective type resolution
- whether regex matching should be added in addition to glob matching

## Non-Goals

- changing the shipped precedence of explicit `column_types`
- weakening strict validation for active declared or convention-based types
- replacing the current project-level convention feature
- expanding this discussion to non-fixed entity types

## Current Behavior

Current fixed-entity type resolution is:

1. `entity.column_types[column]`
2. first matching project convention under `options.fixed_entity_types.conventions`
3. built-in `_id -> int` fallback
4. otherwise no inferred type for undeclared non-`_id` columns

This behavior is implemented across load, validation, persistence, and materialization.

## Proposed Design

### 1. Entity-Scoped Convention Blocks

If additional reuse is needed below the project level, add a separate entity-scoped convention block rather than overloading `column_types`.

Recommended precedence would become:

1. `entity.column_types[column]`
2. first matching entity-scoped convention
3. first matching project convention
4. built-in `_id -> int` fallback
5. otherwise no inferred type

This keeps `column_types` as the explicit override layer while allowing entity-local reusable defaults.

### 2. Target-Model-Informed Typing

Target model specifications already allow column `type` hints, but those hints are informational in v1.

If future work uses target-model typing here, it should do so carefully:

- explicit project and entity declarations must still win
- target model hints should not silently override local configuration
- the mapping between target model types and fixed-entity runtime types must be explicit

The most plausible first use is to seed suggestions or conventions, not to become an unconditional runtime source of truth.

### 3. Lineage Visibility

Type-resolution lineage should remain optional UX, not a core requirement.

If it is added later, it should answer a narrow question clearly:

- declared in `column_types`
- matched by entity-scoped convention
- matched by project convention
- built-in `_id` fallback

This should be added only if users need help diagnosing type outcomes. It is not necessary for the default editing workflow.

### 4. Regex Matching

Glob matching is sufficient for the initial feature.

Regex support should be considered only if there is a concrete pattern that glob rules cannot express cleanly. If added, it should be opt-in and explicit, not a silent expansion of current pattern semantics.

## Alternatives Considered

### 1. Implement all deferred enhancements together

Rejected. It would blur distinct decisions and expand a narrow typing feature into a broader type-system redesign.

### 2. Treat target-model hints as automatic runtime truth

Rejected. That would make local project behavior harder to predict and would weaken explicit configuration ownership.

### 3. Add regex support now as future-proofing

Rejected. There is no clear evidence that glob matching is insufficient today.

## Risks And Tradeoffs

- Entity-scoped conventions add another precedence layer and therefore more cognitive load.
- Target-model-informed typing could create confusion if local declarations and target hints diverge.
- Lineage UX could expose internals that most users do not need.
- Regex support could make matching rules more powerful but less readable.

## Testing And Validation

Any future implementation should include focused tests for:

- precedence between entity-scoped conventions, project conventions, and `column_types`
- target-model-informed behavior when target hints disagree with local declarations
- clear failure modes for invalid regex or malformed convention entries
- UX behavior only when lineage visibility is actually added

## Acceptance Criteria

- [ ] A concrete decision exists for whether entity-scoped conventions should be added
- [ ] A concrete decision exists for whether target model type hints remain advisory or influence fixed-entity typing
- [ ] Any new precedence layer preserves `column_types` as the most explicit override
- [ ] Any added matching mode is documented with clear semantics and validation rules
- [ ] Any new UX scope remains optional and narrowly justified

## Recommended Delivery Order

1. Decide whether entity-scoped conventions solve a real project problem.
2. Decide whether target model type hints should remain advisory or seed local defaults.
3. Revisit lineage UX only if users need help understanding type outcomes.
4. Revisit regex matching only if glob rules prove insufficient.

## Final Recommendation

Keep the shipped project-level convention feature as the stable baseline. Treat entity-scoped conventions and target-model-informed typing as the only likely near-term follow-up candidates, and keep lineage UX and regex support deferred until concrete needs emerge.