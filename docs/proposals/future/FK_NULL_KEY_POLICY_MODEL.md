# FK Null-Key Policy Model

## Status

- Future proposal / not yet approved
- Scope: possible Phase 2 follow-up to [FK_LOOKUP_NULL_KEY_DEFAULT_BEHAVIOR.md](done/FK_LOOKUP_NULL_KEY_DEFAULT_BEHAVIOR.md)
- Goal: decide whether Shape Shifter needs an explicit user-facing policy model for missing foreign-key join values

## Purpose

This document is a placeholder for a possible future proposal.

It exists to separate the broader policy-design discussion from the current Phase 1 lookup-join behavior change in [FK_LOOKUP_NULL_KEY_DEFAULT_BEHAVIOR.md](done/FK_LOOKUP_NULL_KEY_DEFAULT_BEHAVIOR.md).

No implementation is proposed here yet.

## Why This Is Separate

The current Phase 1 proposal solves one narrow problem:

1. lookup-style FK enrichment joins with missing alternative-key parts should keep the local row,
2. null values should not invent a match,
3. the FK should remain unresolved.

That does not automatically answer the broader design question of whether all missing-key behaviors should be expressed through an explicit policy field.

This future proposal would answer that broader question.

## Candidate Problem Statement

If Shape Shifter needs more than one narrowly targeted default, the current boolean-oriented model around `allow_null_keys` may become too implicit.

At that point, the system may need an explicit policy model that lets users choose how missing key values behave in a clearer and more portable way.

## Candidate Scope

If this proposal is developed, it would likely cover:

1. whether to introduce a field such as `missing_key_behavior`,
2. what policy values should be supported,
3. how policy semantics relate to validation and merge behavior,
4. how existing `allow_null_keys` configurations should migrate,
5. how the frontend should expose the policy.

## Out Of Scope For Now

This document does not currently define:

1. a final schema,
2. migration rules,
3. implementation tasks,
4. issue breakdown,
5. acceptance criteria for code changes.

## Candidate Questions To Answer

1. Is a dedicated policy field actually needed after Phase 1 lands?
2. Should missing-key behavior be modeled as `error | no_match | drop_row`, or something else?
3. Should policy be global, per-FK, or partly inferred from join semantics?
4. How should omitted values versus explicit strict settings be represented?
5. Should `allow_null_keys` be deprecated, retained, or mapped into the new model?
6. How should the UI explain the policy without exposing unnecessary implementation details?

## Trigger For Reopening This Topic

This future proposal should be revisited only if one or more of the following becomes true:

1. users need broader control than the Phase 1 lookup-join behavior provides,
2. additional null-handling cases appear that cannot be expressed clearly with the current model,
3. Phase 1 implementation reveals repeated ambiguity around `allow_null_keys`,
4. migration or UX concerns justify a cleaner explicit policy model.

## Relationship To Phase 1

The Phase 1 proposal should be implemented in a way that does not block this future work.

In particular, Phase 1 should:

1. keep validation policy and merge semantics separable internally,
2. avoid spreading heuristic behavior across unrelated components,
3. preserve a path toward a future explicit policy model if needed.
