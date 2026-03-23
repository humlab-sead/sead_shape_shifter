# Proposal: Boundary-Based Project Persistence

## Status

- Proposed feature
- Scope: backend persistence layer, project save boundaries, future editing workflows
- Goal: introduce isolated persistence boundaries for project sections such as `metadata`, `options`, and `entities[entity_name]`

## Summary

Introduce boundary-based project persistence as a platform capability. Instead of treating every save as whole-document regeneration, the persistence layer should be able to reload the current YAML document and merge changes at a small number of stable project boundaries.

The initial boundaries should be:

- `metadata`
- `options`
- `entities[entity_name]`

This is worth doing because it gives the system a cleaner persistence model for several separate needs: comment-preserving save behavior, entity-level optimistic locking, and future collaborative or concurrent editing improvements. The recommendation is to introduce narrow subtree-merge support at those stable boundaries, not a generic update-any-dot-path patch engine.

## Problem

Today Shape Shifter has targeted mutation paths at the API level, but not targeted persistence primitives.

In practice that means:

- an entity editor can update one entity in memory
- metadata and options can be changed independently at the API level
- but persistence still falls back to rebuilding and saving the full project document

That current approach has three limitations:

- it makes comment-preserving save behavior harder because the whole YAML document is effectively regenerated
- it makes isolated compare-and-swap flows harder because persistence does not naturally align with the logical unit being edited
- it raises the blast radius of each save, which is not a good foundation for stronger collaborative behavior later

The core problem is not just YAML formatting. It is that the persistence layer does not yet expose stable write boundaries that match the logical units users actually edit.

## Scope

This proposal covers:

- isolated persistence boundaries for top-level project sections
- save-time reload and subtree merge as the persistence strategy
- backend-oriented persistence capabilities that other features can build on

## Non-Goals

This proposal does not:

- introduce real-time collaboration, CRDT, OT, or auto-merge
- define a generic arbitrary dot-path patch API for all YAML nodes
- require exact byte-for-byte YAML round-tripping
- replace feature-specific proposals such as comment-preserving save or entity optimistic locking

## Current Behavior

The current backend flow effectively does this:

1. load YAML
2. convert it to plain data and API models
3. mutate the relevant part in memory
4. rebuild a full sparse config dict
5. save the whole project again

That is simple and correct for semantics, but it does not give the persistence layer a notion of “replace just this stable project boundary while preserving the rest of the document as much as possible.”

## Proposed Design

Introduce boundary-based persistence helpers that operate on a reloaded YAML document and a semantic target state.

The first implementation should support three stable boundaries:

- `metadata`
- `options`
- `entities[entity_name]`

High-level behavior:

1. load the latest YAML document from disk in a comment-aware form
2. compute the semantic target state from the current API project or entity payload
3. merge only the target boundary into the reloaded document
4. write the merged document atomically

This is intentionally narrower than a general-purpose patch engine. The aim is to provide a small number of persistence operations that align with real editing workflows.

### Why These Boundaries

These boundaries are a good first cut because they are:

- already meaningful in the project model
- stable enough to support conservative merge logic
- directly useful for current editor flows
- sufficient to support other near-term features

### Why Not Generic Dot-Path Updates

A fully generic patch language sounds flexible, but it is a worse first move here.

- YAML comments attach to structure, not just logical paths
- list edits and insertion order quickly become policy questions
- many paths are implementation detail, not stable product boundaries
- a broad patch engine would increase scope without proving product value first

The persistence layer should first learn a few explicit boundaries well.

## Alternatives Considered

### Keep Whole-Project Persistence And Solve Each Feature Separately

This keeps the persistence layer simple, but it forces every feature to work around the same limitation independently.

- comment-preserving save has to fight full-document regeneration
- optimistic locking has to treat whole-project persistence as an unavoidable background behavior
- future collaborative improvements get no cleaner write boundary to build on

### Build A Fully Generic Patch Framework First

This likely overreaches.

- more abstraction than current use cases justify
- more edge cases around lists, comments, and ordering
- higher implementation cost before core user value is proven

## Risks And Tradeoffs

- adds persistence-layer complexity compared with whole-project regeneration
- requires careful merge logic to avoid accidental subtree rewrites
- may still leave some formatting normalization when nodes are newly created or heavily changed

Even with those tradeoffs, this is a better long-term foundation than making every higher-level feature invent its own partial-save strategy.

## Testing And Validation

Validation should focus on boundary-oriented behavior:

- update `metadata` and preserve unrelated document sections
- update `options` and preserve unrelated document sections
- update `entities[entity_name]` and preserve comments and structure elsewhere where practical
- add and remove entities through the entity boundary
- ensure saves remain atomic

## Acceptance Criteria

- the backend can reload the latest YAML and merge changes at `metadata`
- the backend can reload the latest YAML and merge changes at `options`
- the backend can reload the latest YAML and merge changes at `entities[entity_name]`
- the implementation does not depend on a generic dot-path patch engine
- the capability is usable as a foundation for comment-preserving save and entity-level optimistic locking

## Final Recommendation

Promote boundary-based project persistence to a separate platform proposal.

Keep it narrow: explicit subtree merge at `metadata`, `options`, and `entities[entity_name]`.

Then let feature-specific work build on it:

- comment-preserving save uses it to preserve surrounding YAML structure and comments
- entity optimistic locking uses it as the natural persistence boundary for compare-and-swap
- future collaboration features can build on the same stable units of change